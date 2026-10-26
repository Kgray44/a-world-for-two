"""Owned combined client/server qualification with genuine, phase-labelled samples.

Preparation never launches Minecraft or touches the permanent world. The run is
limited to 30 minutes, a 2 GiB test world, and 8 GiB additional managed D: data.
"""
from __future__ import annotations

import argparse
import contextlib
import json
import os
import re
import shutil
import socket
import subprocess
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path

import psutil

from control_room.client_metrics import ClientMetrics
from control_room.common import GiB, Layout, REPO, UserError, atomic_write, digest, read_json, utcnow, write_json
from control_room.pack import generate_pack, validate_jars, validate_pack
from control_room.settings import format_properties
from control_room.storage import Storage, tree_size
from control_room.web import Application, HTTPServer, make_handler
from .client import prepare as prepare_client


def guard(c_bytes, d_bytes):
    command = ['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
               r'C:\Users\kkids\AppData\Local\AeroStorageWatch\ReserveGuard.ps1',
               '-EstimatedCBytes', str(c_bytes), '-EstimatedDBytes', str(d_bytes)]
    result = subprocess.run(command, capture_output=True, text=True, timeout=30, creationflags=subprocess.CREATE_NO_WINDOW)
    data = json.loads(result.stdout.strip().splitlines()[-1])
    if result.returncode or not data.get('allowed'):
        raise UserError('Combined test storage reserve refused: ' + data.get('reason', 'guard unavailable'))
    return data


def prepare(home, seed='-844223996347473026'):
    parent = Layout(home)
    if not read_json(parent.state / 'eula-acceptance.json', {}).get('accepted'):
        raise UserError('Owner acceptance of Minecraft’s EULA is required for disposable servers')
    reserve = guard(GiB, 8 * GiB)
    lock = read_json(REPO / 'catalog/lock.json')
    errors = validate_pack(REPO / 'packwiz', lock)
    native = validate_jars(lock, parent.caches / 'mods')
    if errors or native['errors']:
        raise UserError('The exact candidate must pass manifest and native dependency checks before preparation')
    ident = time.strftime('%Y%m%dT%H%M%SZ', time.gmtime()) + '-play-' + uuid.uuid4().hex[:6]
    layout = Layout(parent.staging / 'world-tests' / ident)
    if layout.home.exists():
        raise UserError('A playtest must use a new owned directory')
    app = Application(layout.home)
    try:
        settings = layout.settings()
        settings.update(world_budget_gib=2, cache_budget_gib=1, project_budget_gib=6,
                        port=25575, player_names=parent.settings()['player_names'])
        layout.save_settings(settings)
        app.installer.accept_eula(True)
        write_json(layout.state / 'test-owner.json', {'id':ident, 'at':utcnow(), 'purpose':'combined candidate playtest', 'owner_source':str(REPO)})
        # Root library files are immutable installed artifacts. Separate configs,
        # world, logs, native extraction directories and mod copies belong here.
        library_bytes = tree_size(parent.server / 'libraries')
        if library_bytes > GiB:
            raise UserError('Library preparation exceeds this bounded step')
        shutil.copytree(parent.server / 'libraries', layout.server / 'libraries', copy_function=os.link)
        release = layout.releases / lock['version']
        shutil.copytree(REPO / 'packwiz/config', release / 'config')
        generate_pack(release, lock)
        write_json(release / 'lock.json', lock)
        (layout.caches / 'mods').mkdir()
        for mod in lock['mods']:
            if mod['side'] in ('server', 'both') and mod['kind'] == 'mod' and not (mod.get('optional') and not mod.get('default', True)):
                os.link(parent.caches / 'mods' / mod['filename'], layout.caches / 'mods' / mod['filename'])
        app.installer.install_mods(lock, release, print)
        props = app.settings.get_properties()
        props.update({'level-name':(layout.world / 'TestWorld').as_posix(), 'level-seed':seed,
                      'server-port':25575, 'view-distance':6, 'simulation-distance':4,
                      'online-mode':True, 'white-list':True, 'enforce-whitelist':True,
                      'motd':'A World for Two - disposable candidate playtest'})
        atomic_write(app.settings.props_path, format_properties(props))
        for name in ('whitelist.json', 'ops.json'):
            write_json(layout.server / name, read_json(parent.server / name, []))
        client = prepare_client(parent.home, 'KG', 25575)
        receipt = {'format':'awft-combined-playtest:1', 'id':ident, 'at':utcnow(), 'home':str(layout.home),
                   'parent':str(parent.home), 'client':client, 'seed':seed, 'guard':reserve,
                   'pack_sha256':digest(release / 'pack.toml'), 'source_pack_sha256':digest(REPO / 'packwiz/pack.toml'),
                   'minecraft_port':25575, 'dashboard_port':8766, 'native_mod_jars':len(native['jars']),
                   'status':'prepared; no server or client has been launched',
                   'boundaries':['Single licensed local player; remote two-player acceptance remains separate.',
                     'Frame intervals include frame pacing and are not GPU execution times.',
                     'The 30 GiB host reserve monitors managed writers; it is not an OS quota for unrelated processes.']}
        write_json(layout.logs / 'playtest-prepared.json', receipt)
        write_json(parent.state / 'prepared-playtest.json', receipt)
        print(json.dumps({key:receipt[key] for key in ('id','home','native_mod_jars','status')}), flush=True)
        return receipt
    finally:
        app.close()


def run(home, ident, minutes=30):
    if not re.fullmatch(r'\d{8}T\d{6}Z-play-[a-f0-9]{6}', ident) or not 5 <= minutes <= 30:
        raise UserError('Choose an owned prepared playtest and a 5–30 minute bound')
    parent = Layout(home)
    layout = Layout(parent.staging / 'world-tests' / ident)
    receipt = read_json(layout.logs / 'playtest-prepared.json', {})
    if receipt.get('id') != ident or Path(receipt.get('home', '')).resolve() != layout.home or not (layout.state / 'test-owner.json').is_file():
        raise UserError('No matching owned playtest preparation exists')
    if (layout.logs / 'playtest-result.json').exists():
        raise UserError('This run already has a result. Preserve it and prepare a fresh candidate run.')
    if receipt['source_pack_sha256'] != digest(REPO / 'packwiz/pack.toml'):
        raise UserError('Source candidate changed after preparation; prepare the new candidate separately')
    free_ram = psutil.virtual_memory().available
    if free_ram < 2 * GiB:
        raise UserError(f'Only {free_ram / GiB:.2f} GiB of RAM is available; the combined run cannot start above its 1.5 GiB checkpoint floor.')
    receipt['available_ram_before_launch'] = free_ram
    receipt['recommended_headroom_bytes'] = 14 * GiB
    receipt['launch_authority'] = 'Owner explicitly requested the combined launch after computer-wide RAM cleanup; 8 GiB server and 6 GiB client heaps retained.'
    receipt['run_guard'] = guard(GiB, 8 * GiB)
    for port in (25575, 8766):
        with socket.socket() as probe:
            if probe.connect_ex(('127.0.0.1', port)) == 0:
                raise UserError('The owned test port is already in use: ' + str(port))
    app = Application(layout.home)
    app.metrics.clients = ClientMetrics(parent)
    http = HTTPServer(('127.0.0.1', 8766), make_handler(app))
    thread = threading.Thread(target=http.serve_forever, kwargs={'poll_interval':.5}, daemon=True)
    phase, phase_at, ever_joined, online_before = 'startup', time.monotonic(), False, False
    started = time.monotonic()
    end = started + minutes * 60
    last_guard, last_sizes, sample_at = started, started, None
    initial_size = tree_size(layout.home) + tree_size(Path(receipt['client']['root']))
    server_process, descendants = None, []
    receipt.update(started=utcnow(), status='running', phases=[], startup='pending', stability='pending')
    samples_path = layout.logs / 'playtest-samples.jsonl'
    gpu = shutil.which('nvidia-smi')
    last_gpu, gpu_value = 0, None

    def transition(value):
        nonlocal phase, phase_at
        phase, phase_at = value, time.monotonic()
        receipt['phases'].append({'at':utcnow(), 'phase':phase})
        print('Playtest phase: ' + phase, flush=True)
        write_json(layout.state / 'playtest-phase.json', {'at':utcnow(), 'phase':phase, 'id':ident})

    try:
        app.start()
        thread.start()
        app.server.start(notify=print)
        server_process = psutil.Process(app.server.process.pid)
        receipt['server_pid'] = server_process.pid
        receipt['server_created'] = server_process.create_time()
        prism = Path(os.environ['LOCALAPPDATA']) / 'Programs/PrismLauncher/prismlauncher.exe'
        subprocess.Popen([str(prism), '--launch', receipt['client']['id']], stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW)
        transition('startup')
        print('Server and KG client launch requested. Test dashboard: http://127.0.0.1:8766/', flush=True)
        while time.monotonic() < end:
            now = time.monotonic()
            if not app.server.running():
                raise UserError('The dedicated test server exited; its world and full diagnostics are preserved')
            if psutil.virtual_memory().available < 1.5 * GiB:
                raise UserError('Available RAM fell below 1.5 GiB; ending the owned server test gracefully')
            if now - last_guard >= 240:
                guard(GiB, 4 * GiB)
                last_guard = now
            if now - last_sizes >= 15:
                if tree_size(layout.world) >= 2 * GiB or tree_size(layout.home) + tree_size(Path(receipt['client']['root'])) - initial_size >= 4 * GiB:
                    raise UserError('The disposable test reached its bounded disk allocation')
                last_sizes = now
            descendants = server_process.children(recursive=True)
            sample = app.metrics.latest()
            fresh = False
            with contextlib.suppress(ValueError):
                fresh = -2 <= time.time() - datetime.fromisoformat((sample.get('tick_at') or '').replace('Z','+00:00')).timestamp() <= 15
            online = fresh and bool(sample.get('players'))
            if phase == 'startup':
                if app.server.state == 'online':
                    receipt.update(startup='pass', startup_seconds=round(now-started,3))
                    transition('startup idle; no generation probes')
                elif now-started >= 360:
                    raise UserError('The combined candidate did not finish server startup within six minutes')
            if online and not online_before:
                ever_joined = True
                receipt['licensed_player_join_observed'] = utcnow()
                transition('active player gameplay')
            elif ever_joined and online_before and not online and fresh:
                transition('post-disconnect idle')
            if not ever_joined and phase != 'startup' and now-started >= 900:
                receipt['stability'] = 'No authenticated player joined within the bounded waiting period'
                break
            if phase == 'post-disconnect idle' and now-phase_at >= 300:
                # Deliberate ticket source, labelled separately from both clean idle phases.
                app.server._write('forceload add 2048 2048 2080 2080')
                transition('controlled nine-chunk force-load probe')
            elif phase == 'controlled nine-chunk force-load probe' and now-phase_at >= 60:
                app.server._write('forceload remove 2048 2048 2080 2080')
                transition('extended idle after force-load removal')
            elif phase == 'extended idle after force-load removal' and now-phase_at >= 300:
                receipt['stability'] = 'Completed live join, disconnect, controlled tickets and five-minute unload observation'
                break
            online_before = online if fresh else online_before
            if gpu and now-last_gpu >= 10:
                try:
                    result = subprocess.run([gpu,'--query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu','--format=csv,noheader,nounits'], capture_output=True,text=True,timeout=3,creationflags=subprocess.CREATE_NO_WINDOW)
                    values = result.stdout.splitlines()[0].split(',')
                    gpu_value = dict(zip(('host_gpu_percent','host_vram_used_mib','host_vram_total_mib','host_gpu_temperature_c'), [float(v.strip()) for v in values])) if result.returncode==0 and len(values)==4 else None
                except (OSError,ValueError,IndexError,subprocess.TimeoutExpired):
                    gpu_value = None
                last_gpu = now
            if sample.get('at') != sample_at:
                sample_at = sample.get('at')
                row = {'phase':phase, 'telemetry_fresh':fresh, 'measurement':sample, 'shared_host_gpu':gpu_value}
                raw = json.dumps(row,ensure_ascii=False)
                if len(raw.encode()) > 1024 * 1024 or (samples_path.exists() and samples_path.stat().st_size > 32 * 1024 * 1024):
                    raise UserError('Bounded playtest sample log reached its size limit')
                with samples_path.open('a',encoding='utf-8') as stream:
                    stream.write(raw+'\n')
                if online:
                    print(json.dumps({'phase':phase,'tps':sample.get('tps'),'mspt':sample.get('mspt'),'server_rss':sample.get('server_rss'),'loaded_chunk_holders':sample.get('loaded_chunks'),'clients':[{k:v for k,v in c.items() if k in ('fps','rss','heap_used','in_world','frame_interval_ms')} for c in sample.get('clients',[])]}),flush=True)
            time.sleep(2)
        receipt['licensed_player_join_observed'] = receipt.get('licensed_player_join_observed', False)
        receipt['status'] = 'bounded run finished; evaluate phase samples and gameplay acceptance separately'
    except (Exception, KeyboardInterrupt) as error:
        receipt.update(status='stopped at a preserved checkpoint', error=str(error) or 'operator interruption')
        print('Playtest checkpoint: ' + receipt['error'],flush=True)
    finally:
        if app.server.running():
            try:
                app.server._write('say The disposable test is ending. Saving the test world now.')
                app.server.stop(notify=print)
                receipt['shutdown'] = 'graceful'
            except Exception as error:
                receipt['shutdown'] = 'pending: ' + str(error)
        else:
            receipt['shutdown'] = 'server already exited; inspect lifecycle logs'
        http.shutdown() if thread.is_alive() else None
        http.server_close()
        if not app.server.running():
            app.close()
        else:
            # Keep ownership and console streams alive if a world flush is still busy.
            write_json(layout.logs / 'playtest-checkpoint.json', receipt)
            print('World flush remains active; keeping its owning process and console alive.',flush=True)
            while app.server.running():
                time.sleep(2)
            app.close()
        receipt.update(finished=utcnow(), world_bytes=tree_size(layout.world),
                       owned_server_alive=app.server.running(), descendants_alive=[p.pid for p in descendants if p.is_running()])
        log = layout.logs / 'console.log'
        text = log.read_text(encoding='utf-8',errors='replace') if log.exists() else ''
        receipt['fatal_lifecycle_events'] = [line[:1000] for line in text.splitlines() if re.search(r'Uncaught exception in server thread|Encountered an unexpected exception|ModLoadingException: Loading errors|Exception caught during firing event',line)][-20:]
        if samples_path.exists():
            receipt.update(samples_sha256=digest(samples_path), samples_bytes=samples_path.stat().st_size)
        write_json(layout.logs / 'playtest-result.json', receipt)
        print(json.dumps({k:v for k,v in receipt.items() if k not in ('client','guard','run_guard','phases')}),flush=True)
    return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--home',type=Path,default=Path(r'D:\A World for Two'))
    parser.add_argument('--prepare',action='store_true')
    parser.add_argument('--run')
    parser.add_argument('--minutes',type=int,default=30)
    args = parser.parse_args()
    if args.prepare == bool(args.run):
        parser.error('Choose exactly one of --prepare or --run OWNED_TEST_ID')
    result = prepare(args.home) if args.prepare else run(args.home,args.run,args.minutes)
    raise SystemExit(bool(result.get('error')))
