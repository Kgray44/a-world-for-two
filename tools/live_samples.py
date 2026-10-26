"""Bounded read-only playtest observations; never stops a running game."""
from __future__ import annotations

import argparse
import contextlib
import json
import re
import time
import urllib.request
from datetime import datetime
from pathlib import Path

from control_room.common import REPO, UserError, digest, read_json, utcnow, write_json
from control_room.storage import GiB, Storage
from control_room.common import Layout
import psutil


def fresh_tick(value, now=None):
    if not isinstance(value, str):
        return False
    try:
        return -2 <= (time.time() if now is None else now) - datetime.fromisoformat(value.replace('Z', '+00:00')).timestamp() <= 15
    except (ValueError, TypeError):
        return False


def observe(home: Path, seconds=1800):
    if type(seconds) is not int or not 60 <= seconds <= 1800:
        raise UserError('Choose a bounded observation between one and thirty minutes')
    layout = Layout(home)
    owner = read_json(layout.state / 'test-owner.json', {})
    if owner.get('owner_source') != str(REPO):
        raise UserError('Live sampling requires an owned disposable test')
    identity = read_json(layout.state / 'server-process.json', {})
    process = psutil.Process(identity['pid'])
    if abs(process.create_time() - identity['created']) > .1 or Path(process.cwd()).resolve() != layout.server:
        raise UserError('The server process identity does not match this test')
    storage = Storage(layout)
    storage.reserve(3 * GiB)
    output = layout.logs / ('live-samples-' + datetime.now().strftime('%Y%m%dT%H%M%S') + '.jsonl')
    prepared = read_json(layout.logs / 'playtest-prepared.json', {})
    client = Path(prepared.get('client', {}).get('root', ''))
    owned = read_json(client / 'awft-owned.json', {}) if client.is_absolute() else {}
    client = client if owned.get('format') == 'awft-owned-client:1' and owned.get('root') == str(client) else None
    source = read_json(layout.home / 'packwiz/active.json', {})
    started, next_report, idle_since, ever_online = time.monotonic(), 0, None, False
    rows, errors, finish_reason = 0, [], 'bounded observation elapsed'
    selected = ('at', 'tps', 'mspt', 'tick_at', 'tick_source', 'server_rss', 'server_cpu', 'heap_used', 'heap_max',
                'loaded_chunks', 'entities', 'dimensions', 'host_cpu', 'host_memory_available', 'gc_collections',
                'gc_collection_ms', 'clients', 'atlas_renderer', 'chunk_diagnostics', 'bridge_error')
    try:
        while time.monotonic() - started < seconds:
            storage.checkpoint(3 * GiB)
            try:
                request = urllib.request.Request('http://127.0.0.1:8766/api/metrics')
                with urllib.request.urlopen(request, timeout=4) as response:
                    raw = response.read(2 * 1024 * 1024 + 1)
                if len(raw) > 2 * 1024 * 1024:
                    raise UserError('Metrics response exceeds its bound')
                sample = json.loads(raw)
                row = {key: sample.get(key) for key in selected}
                row['observed_at'] = utcnow()
                fresh = fresh_tick(sample.get('tick_at'))
                players = sample.get('players', {}) if fresh else {}
                row['telemetry_fresh'] = fresh
                row['phase'] = 'playing' if players else 'idle' if fresh else 'telemetry unavailable'
                row['players'] = [{key: p.get(key) for key in ('name', 'dimension', 'x', 'y', 'z', 'game_mode')} for p in players.values()]
                if client:
                    settings = client / '.minecraft/config/iris.properties'
                    if settings.is_file() and settings.stat().st_size <= 8192:
                        row['shader'] = dict(re.findall(r'(?m)^(enableShaders|shaderPack)=(.*)$', settings.read_text()))
                if players:
                    ever_online, idle_since = True, None
                elif fresh and ever_online:
                    idle_since = idle_since or time.monotonic()
                encoded = json.dumps(row, ensure_ascii=False).encode('utf-8') + b'\n'
                if len(encoded) > 256 * 1024 or (output.stat().st_size if output.exists() else 0) + len(encoded) > 16 * 1024 * 1024:
                    finish_reason = 'bounded sample file reached its limit'
                    break
                with output.open('ab') as stream:
                    stream.write(encoded)
                rows += 1
                if time.monotonic() >= next_report:
                    print(json.dumps({key: row.get(key) for key in ('observed_at', 'phase', 'tps', 'mspt', 'loaded_chunks', 'host_memory_available')}), flush=True)
                    next_report = time.monotonic() + 60
                if idle_since is not None and time.monotonic() - idle_since >= 300:
                    finish_reason = 'five minutes of fresh post-disconnect idle observations'
                    break
            except (OSError, ValueError, KeyError) as error:
                if len(errors) < 30:
                    errors.append({'at': utcnow(), 'error': str(error)[:500]})
            time.sleep(5)
    except BaseException as error:
        finish_reason = 'observation interrupted: ' + type(error).__name__
        errors.append({'at': utcnow(), 'error': str(error)[:500]})
        raise
    finally:
        receipt = {'at': utcnow(), 'pack_sha256': source.get('pack_sha256'), 'samples': rows,
            'path': str(output), 'sha256': digest(output) if output.exists() else None, 'errors': errors,
            'finish_reason': finish_reason, 'scope': 'One local licensed player, real server/client samples. Stale telemetry is not an idle phase. Game processes remain running.'}
        write_json(output.with_suffix('.receipt.json'), receipt)
        print(json.dumps(receipt), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--home', required=True, type=Path)
    parser.add_argument('--seconds', type=int, default=1800)
    args = parser.parse_args()
    observe(args.home, args.seconds)
