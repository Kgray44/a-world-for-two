"""Bounded passive benchmark capture during a master-coordinated existing session.

Never starts/stops games, changes graphics, moves players or generates terrain.
Native files are identity/freshness checked and repeated snapshots deduplicated.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import json
import math
import os
from pathlib import Path
import shutil
import stat
import subprocess
import time

import psutil

from control_room.common import digest, utcnow
from control_room.metrics import measurement_freshness
from tools.performance_windows import PagingCounters, memory_pressure
from tools.playtest import guard


MAX_OUTPUT = 12 * 1024 * 1024
MASTER = '01a17947-1d00-7fd1-aa5e-d1fb514f8671'


def json_file(path, limit=2 * 1024 * 1024):
    path = Path(path)
    if not path.is_file() or path.is_symlink() or path.is_junction() or path.stat().st_size > limit:
        raise ValueError('Finite ordinary input file required')
    with path.open('rb') as stream:
        raw = stream.read(limit + 1)
    if len(raw) > limit:
        raise ValueError('Input grew beyond its bound')
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError('JSON object required')
    return value


def timestamp(text):
    value = datetime.fromisoformat(text.replace('Z', '+00:00'))
    if value.tzinfo is None:
        raise ValueError('Explicit timestamp timezone required')
    return value.timestamp()


def validate_window(window, now):
    if (window.get('format') != 'awft-passive-performance-window:1'
            or window.get('coordinator_chat') != MASTER or window.get('operation') != 'passive-telemetry'
            or not isinstance(window.get('workload'), str) or not isinstance(window.get('configuration'), str)):
        raise ValueError('Explicit master passive-telemetry window required')
    begin, end = timestamp(window['begins_at']), timestamp(window['expires_at'])
    if not begin <= now < end or end - begin > 1800:
        raise ValueError('Master window is not currently valid or exceeds thirty minutes')
    if (window.get('server_home') != r'D:\A World for Two\staging\world-tests\20261027T053650Z-artistic'
            or window.get('client_root') != r'D:\A World for Two\instances\AWFT_Check_20261026_214756'):
        raise ValueError('Exact existing construction runtime and owner client required')
    if not isinstance(window.get('candidate'), str) or not isinstance(window.get('pack_sha256'), str) or len(window['pack_sha256']) != 64:
        raise ValueError('Exact candidate and pack hash required')
    watches = window.get('watch_directories', {})
    if not isinstance(watches, dict) or len(watches) > 6 or any(not isinstance(k, str) or len(k) > 64 or not isinstance(v, str) for k, v in watches.items()):
        raise ValueError('At most six named bounded metadata watches')
    files = window.get('watch_files', {})
    if not isinstance(files, dict) or len(files) > 12 or any(not isinstance(k, str) or len(k) > 64 or not isinstance(v, str) for k, v in files.items()):
        raise ValueError('At most twelve named file metadata watches')
    return end


def native_snapshot(path, expected, side, now):
    """Authenticate metadata against an existing pinned OS process and its cwd."""
    data = json_file(path)
    if data.get('format') != ('awft-metrics:1' if side == 'server' else 'awft-client-metrics:1'):
        raise ValueError('Native telemetry format differs')
    if data.get('pid') != expected['pid'] or abs(timestamp(data['process_started']) - expected['created']) > 2:
        raise ValueError('Native telemetry belongs to another process generation')
    process = psutil.Process(expected['pid'])
    if (abs(process.create_time() - expected['created']) > .1
            or process.name().lower() not in ('java.exe', 'javaw.exe', 'java')
            or Path(process.cwd()).resolve() != Path(expected['cwd']).resolve()):
        raise ValueError('Native process identity/cwd no longer matches')
    if not measurement_freshness(data.get('at'), now)['current']:
        raise ValueError('Native telemetry is stale or clock-skewed')
    for key, maximum in (('heap_used', 64 * 1024**3), ('heap_max', 64 * 1024**3),
                         ('tps', 1000), ('mspt', 3_600_000)) if side == 'server' else (
                         ('heap_used', 64 * 1024**3), ('heap_max', 64 * 1024**3), ('fps', 1_000_000)):
        value = data.get(key)
        if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= maximum:
            raise ValueError('Invalid native numeric measurement: ' + key)
    if data['heap_used'] > data['heap_max']:
        raise ValueError('Native used heap exceeds maximum heap')
    if side == 'server':
        keys = ('at', 'tps', 'mspt', 'ticks_sampled', 'interval_ms', 'tick_window', 'heap_used', 'heap_max',
                'gc_collections', 'gc_collection_ms', 'loaded_chunks', 'entities', 'dimensions')
    else:
        keys = ('at', 'fps', 'frame_interval_ms', 'heap_used', 'heap_max', 'focused', 'in_world', 'screen')
    result = {key: data.get(key) for key in keys}
    if side == 'server':
        result['players_present'] = len(data['players']) if isinstance(data.get('players'), dict) else None
    result['pid'] = process.pid
    result['rss_bytes'] = process.memory_info().rss
    result['cpu_time_seconds'] = sum(process.cpu_times()[:2])
    result['process_io'] = process.io_counters()._asdict()
    result['process_observed_at'] = utcnow()
    return result


def directory_size(root, seconds=.25, max_entries=10000):
    root = Path(root)
    if not root.is_dir() or root.is_symlink() or root.is_junction():
        return {'complete': False, 'reason': 'Ordinary existing directory unavailable'}
    deadline, pending, total, entries = time.monotonic() + seconds, [root], 0, 0
    while pending:
        with os.scandir(pending.pop()) as children:
            for child in children:
                entries += 1
                if entries > max_entries or time.monotonic() > deadline:
                    return {'complete': False, 'observed_logical_bytes': total, 'reason': 'Bounded metadata scan ended'}
                if child.is_symlink() or (os.name == 'nt' and os.path.isjunction(child.path)):
                    return {'complete': False, 'reason': 'Linked metadata entry refused'}
                if child.is_dir(follow_symlinks=False):
                    pending.append(Path(child.path))
                elif child.is_file(follow_symlinks=False):
                    total += child.stat(follow_symlinks=False).st_size
    return {'complete': True, 'logical_bytes_including_wal': total, 'entries': entries}


def file_size(path):
    """Observe one exact DB/WAL/SHM file, without reading or opening SQLite."""
    path = Path(path)
    try:
        if path.is_symlink() or path.is_junction():
            return {'available': False, 'reason': 'Linked file metadata refused'}
        value = path.stat()
        if not stat.S_ISREG(value.st_mode):
            return {'available': False, 'reason': 'Not an ordinary file'}
        return {'available': True, 'exists': True, 'logical_bytes': value.st_size,
                'modified_ns': value.st_mtime_ns}
    except FileNotFoundError:
        return {'available': True, 'exists': False, 'logical_bytes': 0}
    except OSError as error:
        return {'available': False, 'reason': type(error).__name__}


def gpu_sample():
    command = shutil.which('nvidia-smi')
    if not command:
        return {'available': False, 'reason': 'nvidia-smi unavailable'}
    result = subprocess.run([command, '--query-gpu=index,utilization.gpu,memory.used,memory.total,temperature.gpu,power.draw',
                             '--format=csv,noheader,nounits'], capture_output=True, text=True, timeout=3,
                            creationflags=subprocess.CREATE_NO_WINDOW)
    if result.returncode or len(result.stdout) > 8192:
        return {'available': False, 'reason': 'NVIDIA query failed'}
    rows = []
    for line in result.stdout.splitlines()[:8]:
        values = line.split(',')
        if len(values) != 6:
            return {'available': False, 'reason': 'NVIDIA result shape differs'}
        row = {}
        for name, value in zip(('index', 'utilization_percent', 'vram_mib', 'vram_total_mib', 'temperature_c', 'power_watts'), values):
            try:
                number = float(value)
                row[name] = number if math.isfinite(number) and number >= 0 else None
            except ValueError:
                row[name] = None
        rows.append(row)
    return {'available': bool(rows), 'at': utcnow(), 'scope': 'Whole GPU, shared with other applications', 'gpus': rows}


def describe(values):
    values = sorted(v for v in values if type(v) in (int, float) and math.isfinite(v))
    if not values:
        return {'samples': 0}
    return {'samples': len(values), 'min': values[0], 'mean': sum(values) / len(values),
            'p50': values[math.ceil(len(values) * .5) - 1],
            'p95': values[math.ceil(len(values) * .95) - 1], 'max': values[-1]}


def config_hashes(home, client):
    paths = {'server_dh': home / 'server/config/DistantHorizons.toml',
             'server_seedgen': home / 'server/config/seedgen.json',
             'client_dh': client / '.minecraft/config/DistantHorizons.toml',
             'client_seedgen': client / '.minecraft/config/seedgen.json',
             'client_iris': client / '.minecraft/config/iris.properties',
             'client_options': client / '.minecraft/options.txt'}
    result = {}
    for name, path in paths.items():
        try:
            if path.is_symlink() or not path.is_file() or path.stat().st_size > 256 * 1024:
                raise ValueError('Finite ordinary configuration unavailable')
            result[name] = digest(path)
        except (OSError, ValueError):
            result[name] = None
    return result


def summarize(rows):
    # Capture already removes repeat native timestamps. Never pool percentiles
    # of interval means or window percentiles into an invented per-frame p99.
    servers = [r['server'] for r in rows if r.get('server')]
    clients = [r['client'] for r in rows if r.get('client')]
    gameplay = [c for c in clients if c.get('focused') is True and c.get('in_world') is True and c.get('screen') == 'game']
    windows = [s['tick_window'] for s in servers if isinstance(s.get('tick_window'), dict)
               and s['tick_window'].get('format') == 'awft-tick-window:1']
    frames = [s['frame_interval_ms'] for s in gameplay if isinstance(s.get('frame_interval_ms'), dict)]
    all_frames = [s['frame_interval_ms'] for s in clients if isinstance(s.get('frame_interval_ms'), dict)]
    def maximum(values):
        values = [v for v in values if type(v) in (int, float) and math.isfinite(v) and v >= 0]
        return max(values, default=None)

    def tick_maximum(field):
        return maximum(w[field].get('max') for w in windows if isinstance(w.get(field), dict)
                       and type(w[field].get('observations')) is int and w[field]['observations'] > 0)

    def tick_count(field):
        values = [w.get(field) for w in windows]
        # A missing counter in one retained native window invalidates the total.
        return sum(values) if values and all(type(v) is int and v >= 0 for v in values) else None
    gc_delta = None
    if len(servers) >= 2 and all(type(s.get('gc_collection_ms')) in (int, float) for s in (servers[0], servers[-1])):
        delta = servers[-1]['gc_collection_ms'] - servers[0]['gc_collection_ms']
        gc_delta = delta if delta >= 0 else None
    return {'native_server_snapshots': len(servers), 'native_client_snapshots': len(clients),
            'sampled_window_mean_mspt': describe(s.get('mspt') for s in servers),
            'sampled_tps_estimates': describe(s.get('tps') for s in servers),
            'focused_gameplay_client_snapshots': len(gameplay),
            'sampled_focused_gameplay_fps': describe(s.get('fps') for s in gameplay),
            'gc_collector_elapsed_delta_ms': gc_delta,
            'tick_spike_observations': {'windows': len(windows),
                'max_work_ms': tick_maximum('work_ms'),
                'over_50ms': tick_count('work_over_50ms'),
                'over_100ms': tick_count('work_over_100ms'),
                'over_250ms': tick_count('work_over_250ms'),
                'start_gaps_over_100ms': tick_count('start_gaps_over_100ms'),
                'max_start_gap_ms': tick_maximum('start_gap_ms')},
            'sampled_client_frame_windows': {'windows': len(frames),
                'worst_retained_frame_ms': maximum(f.get('max') for f in frames),
                'worst_window_p95_ms': maximum(f.get('p95') for f in frames),
                'context': 'Screen/focus/world state at export only; transition frames inside a window are not identified',
                'global_frame_percentiles': 'Unavailable; retained window aggregates cannot establish them'},
            'all_client_states_worst_retained_frame_ms': maximum(f.get('max') for f in all_frames),
            'host_physical_available_bytes': describe(r['host']['memory_available_bytes'] for r in rows),
            'windows_commit_headroom_bytes': describe(r['host'].get('windows_memory', {}).get('commit_headroom_bytes') for r in rows),
            'boundary': 'Only observed snapshots/windows. Missing intervals, unfocused/menu frames and unperformed workloads remain unqualified. No gameplay acceptance inferred.'}


def capture(window_path, seconds=60):
    if type(seconds) is not int or not 1 <= seconds <= 600:
        raise ValueError('One to six hundred seconds per passive capture')
    window = json_file(window_path, 65536)
    expires = validate_window(window, time.time())
    home, client = Path(window['server_home']), Path(window['client_root'])
    active = json_file(home / 'packwiz/active.json', 65536)
    if (active.get('version'), active.get('pack_sha256')) != (window['candidate'], window['pack_sha256']):
        raise ValueError('Installed candidate differs from the master window')
    expected = window['processes']
    if (not isinstance(expected, dict) or set(expected) not in ({'server'}, {'server', 'client'})
            or expected['server']['cwd'] != str(home / 'server')
            or ('client' in expected and expected['client']['cwd'] != str(client / '.minecraft'))):
        raise ValueError('Exact server and optional existing-client process/cwd identities required')
    for side in expected:
        if (type(expected[side].get('pid')) is not int or expected[side]['pid'] <= 0
                or type(expected[side].get('created')) not in (int, float)
                or not math.isfinite(expected[side]['created']) or expected[side]['created'] <= 0):
            raise ValueError('Master process generation is incomplete')
    if time.time() + seconds > expires:
        raise ValueError('Capture would exceed the master window')
    reserve = guard(0, 16 * 1024 * 1024)
    output = home / 'staging' / ('terrain-performance-' + str(time.time_ns()))
    output.mkdir()
    (output / 'window.json').write_text(json.dumps(window, indent=2) + '\n', encoding='utf-8')
    paths = {'server': home / 'dashboard/server-metrics.json'}
    if 'client' in expected:
        paths['client'] = client / '.minecraft/awft-client-metrics.json'
    seen, rows, errors, byte_count = {}, [], [], 0
    started, last_guard, last_gpu, last_sizes = time.monotonic(), time.monotonic(), 0, 0
    counters, gpu, sizes = PagingCounters(), None, {}
    psutil.cpu_percent(percpu=True)
    receipt = {'format': 'awft-passive-performance-result:1', 'at': utcnow(), 'candidate': window['candidate'],
               'pack_sha256': window['pack_sha256'], 'configuration': window['configuration'],
               'workload': window['workload'], 'reserve_guard': reserve, 'native_game_actions': 0,
               'source_sha256': digest(Path(__file__)), 'status': 'interrupted',
               'processes': expected, 'client_recording_requested': 'client' in expected,
               'reserve_coverage': 'Owned recorder only; external games/applications and pre-existing writers are not constrained by this monitoring rule.'}
    try:
        with (output / 'samples.jsonl').open('xb') as stream:
            while time.monotonic() - started < seconds:
                loop = time.monotonic()
                if time.time() >= expires:
                    raise ValueError('Master window expired')
                current = json_file(home / 'packwiz/active.json', 65536)
                if (current.get('version'), current.get('pack_sha256')) != (window['candidate'], window['pack_sha256']):
                    raise ValueError('Runtime candidate changed; stop this capture')
                if loop - last_guard >= 240:
                    guard(0, 16 * 1024 * 1024)
                    last_guard = loop
                memory = psutil.virtual_memory()
                row = {'at': utcnow(), 'elapsed_seconds': loop - started,
                       'configuration_sha256': config_hashes(home, client),
                       'host': {'cpu_percent_per_logical_cpu': psutil.cpu_percent(percpu=True),
                                'memory_total_bytes': memory.total, 'memory_available_bytes': memory.available,
                                'windows_memory': memory_pressure(), 'paging': counters.sample(),
                                'drive_free_bytes': {d: psutil.disk_usage(d + ':/').free for d in ('C', 'D')}}}
                if any(free <= 32_212_254_720 for free in row['host']['drive_free_bytes'].values()):
                    raise ValueError('A drive reached the reserve; preserve this recorder checkpoint')
                for side, path in paths.items():
                    try:
                        value = native_snapshot(path, expected[side], side, time.time())
                        if seen.get(side) != value['at']:
                            seen[side] = value['at']
                            row[side] = value
                        else:
                            row[side + '_status'] = 'repeated native timestamp, excluded from summary'
                    except (OSError, ValueError, KeyError, psutil.Error) as error:
                        row[side + '_status'] = type(error).__name__ + ': ' + str(error)[:160]
                if loop - last_gpu >= 5:
                    try:
                        gpu = gpu_sample()
                    except (OSError, subprocess.TimeoutExpired) as error:
                        gpu = {'available': False, 'reason': type(error).__name__}
                    last_gpu = loop
                    row['gpu'] = gpu
                if loop - last_sizes >= 30:
                    sizes = {}
                    for name, path in window.get('watch_directories', {}).items():
                        folder = Path(path).resolve()
                        if not (folder.is_relative_to(home) or folder.is_relative_to(client)):
                            raise ValueError('Metadata watch must remain within the existing runtime/client')
                        sizes[name] = directory_size(folder)
                    row['directory_sizes'] = sizes
                    row['file_sizes'] = {}
                    for name, path in window.get('watch_files', {}).items():
                        target = Path(path)
                        resolved = target.resolve()
                        if not (resolved.is_relative_to(home) or resolved.is_relative_to(client)):
                            raise ValueError('File metadata watch must remain within the existing runtime/client')
                        row['file_sizes'][name] = file_size(target)
                    last_sizes = loop
                raw = (json.dumps(row, allow_nan=False) + '\n').encode()
                if len(raw) > 256 * 1024 or byte_count + len(raw) > MAX_OUTPUT:
                    raise ValueError('Finite recorder output allocation reached')
                stream.write(raw)
                stream.flush()
                byte_count += len(raw)
                rows.append(row)
                delay = min(1.0, seconds - (time.monotonic() - started))
                if delay > 0:
                    time.sleep(delay)
        receipt['status'] = 'bounded passive capture complete'
    except BaseException as error:
        errors.append({'type': type(error).__name__, 'reason': str(error)[:300]})
        raise
    finally:
        counters.close()
        receipt.update(finished_at=utcnow(), elapsed_seconds=time.monotonic() - started,
                       output_bytes=byte_count, errors=errors, summary=summarize(rows))
        receipt['configuration_hashes_unchanged'] = bool(rows) and all(
            r['configuration_sha256'] == rows[0]['configuration_sha256'] for r in rows)
        receipt['configuration_hashes_complete'] = bool(rows) and all(rows[0]['configuration_sha256'].values())
        samples = output / 'samples.jsonl'
        receipt['samples_sha256'] = digest(samples) if samples.exists() else None
        (output / 'result.json').write_text(json.dumps(receipt, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    return {'directory': str(output), 'result_sha256': digest(output / 'result.json'), 'summary': receipt['summary']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--window', required=True, type=Path)
    parser.add_argument('--seconds', type=int, default=60)
    args = parser.parse_args()
    print(json.dumps(capture(args.window, args.seconds), indent=2))
