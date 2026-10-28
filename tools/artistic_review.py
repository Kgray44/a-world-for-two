"""Private staging of a saved world for actual Minecraft artistic review.

Never replaces the official save, supplies account tokens, or qualifies artwork
from placement counts. Immutable JAR/library hardlinks are read-only inputs;
worlds, configs, logs and all other writable state are separate copies.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import socket
import time
import urllib.request
import zipfile
from pathlib import Path

from control_room.backups import Backups
from control_room.common import Layout, REPO, UserError, atomic_write, digest, read_json, utcnow, write_json
from control_room.pack import verify_installed
from control_room.server import Server
from control_room.settings import format_properties, properties
from control_room.storage import Storage, tree_size


def prepare_stage(home, backup_id, expected_sha):
    from .playtest import guard
    guard(128 * 1024**2, 8 * 1024**3)
    parent = Layout(home)
    storage = Storage(parent)
    server = Server(parent, storage)
    if server.running():
        raise UserError('Stop the official save before taking artistic staging inputs')
    if verify_installed(parent):
        raise UserError('The installed mod inventory must match before staging')
    backups = Backups(parent, storage, server)
    archive = backups.path(backup_id)
    if digest(archive) != expected_sha:
        raise UserError('The selected saved-world archive differs')
    manifest, size = backups.verify_archive(archive)
    if size > 512 * 1024**2:
        raise UserError('Saved staging inputs exceed this bounded step')
    for port in (25575, 8766):
        with socket.socket() as probe:
            if probe.connect_ex(('127.0.0.1', port)) == 0:
                raise UserError('The private artistic staging port is already occupied')
    ident = time.strftime('%Y%m%dT%H%M%SZ', time.gmtime()) + '-artistic'
    stage = Layout(parent.staging / 'world-tests' / ident)
    if stage.home.exists():
        raise UserError('Artistic staging must use a new owned directory')
    stage.create()
    receipt = {'format': 'awft-artistic-stage:1', 'id': ident, 'at': utcnow(),
        'home': str(stage.home), 'owner_source': str(REPO), 'backup': backup_id,
        'backup_sha256': expected_sha, 'status': 'preparing',
        'world': 'Separate writable copy, not the official save',
        'minecraft_port': 25575, 'dashboard_port': 8766,
        'acceptance': 'No artistic acceptance; actual native screenshots required'}
    write_json(stage.state / 'artistic-owner.json', receipt)
    try:
        # Verify archive members before this function and extract only its exact,
        # allowlisted managed files into the new, nonlinked staging root.
        with zipfile.ZipFile(archive) as source:
            for member in manifest['files']:
                target = stage.home / member['path']
                target.parent.mkdir(parents=True, exist_ok=True)
                with source.open(member['path']) as stream, target.open('xb') as output:
                    shutil.copyfileobj(stream, output, 1024*1024)
                if digest(target) != member['sha256']:
                    raise UserError('Staged world input hash differs')
        for folder in ('libraries', 'mods'):
            shutil.copytree(parent.server/folder, stage.server/folder, copy_function=os.link)
        # Small, independently writable runtime inputs, never the render cache.
        for folder in ('datapacks', 'emotes', 'tacz', 'moonlight-global-datapacks'):
            source = parent.server/folder
            if source.exists():
                if tree_size(source) > 128 * 1024**2:
                    raise UserError('Optional runtime input exceeds its staging bound')
                shutil.copytree(source, stage.server/folder)
        active = read_json(stage.home/'packwiz/active.json')
        source_release = parent.releases/active['version']
        if tree_size(source_release) > 32 * 1024**2:
            raise UserError('The active manifest exceeds its staging bound')
        shutil.copytree(source_release, stage.releases/active['version'])
        atomic_write(stage.server/'eula.txt', (parent.server/'eula.txt').read_bytes())
        write_json(stage.state/'eula-acceptance.json', read_json(parent.state/'eula-acceptance.json'))
        settings = parent.settings() | {'port': 25575, 'world_budget_gib': 2,
            'cache_budget_gib': 1, 'project_budget_gib': 8, 'permanent_world': False,
            'java': r'C:\Program Files\Java\jdk-21.0.10\bin\java.exe',
            'tunnel_address': '', 'backup_interval_hours': 24}
        stage.save_settings(settings)
        props_path = stage.server/'server.properties'
        props = properties(props_path.read_text(encoding='utf-8'))
        props.update({'level-name': (stage.world/'AWorldForTwo').as_posix(),
            'server-port': 25575, 'server-ip': '127.0.0.1', 'online-mode': True,
            'enable-rcon': False, 'enable-query': False, 'white-list': True,
            'enforce-whitelist': True, 'motd': 'A World for Two - artistic staging'})
        atomic_write(props_path, format_properties(props))
        settlement = stage.state/'settlement'
        write_json(settlement/'backup-receipt.json', {'verified': True,
            'id': backup_id, 'sha256': expected_sha, 'at': utcnow(),
            'scope': 'Exact verified archive used to prepare this separate staging world'})
        receipt.update(status='prepared; no server/client launched',
            pack_sha256=active['pack_sha256'], source_bytes=size,
            independent_world_bytes=tree_size(stage.world))
        write_json(stage.state/'artistic-owner.json', receipt)
        write_json(parent.state/'artistic-stage.json', receipt)
        return receipt
    except BaseException as failure:
        receipt.update(status='failed; partial staging and evidence retained', error=str(failure))
        write_json(stage.state/'artistic-owner.json', receipt)
        raise


def request(home, path, data=None):
    """Exact local staging identity and current-session protection for mutations."""
    stage = Layout(home)
    owner = read_json(stage.state/'artistic-owner.json', {})
    if owner.get('format') != 'awft-artistic-stage:1' or Path(owner.get('home', '')).resolve() != stage.home:
        raise UserError('This is not an owned artistic staging world')
    base = 'http://127.0.0.1:8766/api/'
    if data is None:
        with urllib.request.urlopen(base+path, timeout=15) as response:
            return json.load(response)
    bootstrap = request(home, 'bootstrap')
    if bootstrap.get('app_id') != 'awft-control-room' or Path(bootstrap.get('home', '')).resolve() != stage.home:
        raise UserError('The artistic Control Room identity differs')
    req = urllib.request.Request(base+path, data=json.dumps(data).encode(),
        headers={'Content-Type':'application/json', 'Origin':'http://127.0.0.1:8766',
                 'X-AWFT-CSRF':bootstrap['csrf']})
    with urllib.request.urlopen(req, timeout=20) as response:
        return json.load(response)


def construction_bounds(plan):
    """Match the real SettlementSupport footprint header before sending stdin.

    Admission exceptions occur before that helper starts its terminal journal.
    Catch malformed/oversize source headers here instead of waiting for a
    terminal that the server could not create. Engineering has its own schema.
    """
    bounds=plan.get('bounds')
    if (not isinstance(bounds,list) or len(bounds)!=4
            or any(type(value) is not int for value in bounds)
            or bounds[0]>bounds[2] or bounds[1]>bounds[3]
            or bounds[2]-bounds[0]>512 or bounds[3]-bounds[1]>512):
        raise UserError('Native construction requires four ordered integer bounds, at most512 blocks per span; split a larger source batch')
    return bounds


def construction_header(plan):
    construction_bounds(plan)
    tags=plan.get('block_entities')
    commands=plan.get('commands')
    if (not isinstance(tags,list) or len(tags)>4096 or not isinstance(commands,list)
            or any(not isinstance(command,str) for command in commands)):
        raise UserError('Native construction requires bounded block-entity rows and literal command strings')
    for row in tags:
        if (not isinstance(row,dict) or not isinstance(row.get('pos'),list)
                or len(row['pos'])!=3 or any(type(n) is not int for n in row['pos'])
                or not isinstance(row.get('nbt'),str) or len(row['nbt'])>16384):
            raise UserError('Native block-entity tags must be bounded literal SNBT strings, not JSON objects')


def native(home, command, *, plan_path=None, timeout=300):
    """One serialized native staging action, retaining its real terminal receipt."""
    from .settlement_live import native_read
    import hashlib
    layout=Layout(home)
    if not 1<=timeout<=300 or not command.startswith(('awftbuild ', 'awftengine ')):
        raise UserError('Only bounded artistic staging construction is admitted')
    engineering=command.startswith('awftengine ')
    family='engineering' if engineering else 'settlement'
    folder=layout.state/'settlement'
    metrics=request(home,'metrics')
    status=request(home,'overview')['server']
    if (status['state']!='online' or metrics.get('players')!={}
            or metrics.get('bridge_age_seconds',999)>15
            or status.get('status',{}).get('players',{}).get('online')!=0):
        raise UserError('Artistic construction needs a currently measured empty staging server')
    if plan_path is not None:
        path=Path(plan_path).resolve()
        if not path.is_relative_to(layout.home.parents[2]) or path.stat().st_size>32*1024**2:
            raise UserError('Staging plan path/size differs')
        raw=path.read_bytes(); expected=hashlib.sha256(raw).hexdigest()
        allowed=('awftengine setup '+expected,'awftengine commission '+expected,'awftengine close '+expected) if engineering else ('awftbuild place '+expected,'awftbuild verify '+expected,'awftbuild map '+expected,'awftbuild settle '+expected)
        if command not in allowed:
            raise UserError('Native command must bind the exact source plan')
        plan=json.loads(raw)
        if not engineering:construction_header(plan)
        world=Path(plan['world_path']).resolve()
        if not world.is_relative_to(layout.world) or world.name!='RosewaterArtistic':
            raise UserError('The official world and historical staging copy are never admitted here')
        if plan['backup_sha256']!=read_json(folder/'backup-receipt.json')['sha256']:
            raise UserError('The current verified staging checkpoint differs')
        atomic_write(folder/('engineering-plan.json' if engineering else 'plan.json'),raw)
    before=set(folder.glob(family+'-result-*.json.complete'))
    request(home,'console',{'command':command,'confirmed':True})
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        for marker in set(folder.glob(family+'-result-*.json.complete'))-before:
            path=marker.with_suffix('');raw=path.read_bytes()
            if hashlib.sha256(raw).hexdigest()!=marker.read_text().strip():
                raise UserError('Native terminal receipt hash differs')
            result=json.loads(raw)
            if result.get('operation')!=command.split()[1]:continue
            if plan_path is not None and result.get('plan_sha256')!=expected:continue
            completed = result.get('status') in ('complete',
                'construction actions complete; native verification and restart still required',
                'verified actual block identities, orientation, block entities and supplied inventories',
                'native glue and real sequencer programs configured; operation not yet accepted',
                'two native button-driven open/close cycles passed at the reviewed angle; persistence and ship clearance remain separate',
                'native button returned both previously open spans to closed, disassembled and idle; no program or angle was fabricated',
                'native spans already closed and idle; no input sent')
            completed = completed or result.get('status') == 'existing construction chunks queued through squaremap\'s native update mechanism'
            completed = completed or result.get('status') == 'normal native neighbor shapes reconciled; no source state, inventory or command replay'
            if (not completed
                    or not result.get('finished') or result.get('error') or result.get('failures',0)
                    or result.get('temporary_tickets_remaining',0) or result.get('cleanup_required')):
                raise UserError('Native operation failed; exact receipt retained at '+str(path))
            print(json.dumps({'operation':command.split()[1],'terminal':str(path),'status':result['status']}),flush=True)
            return result
        time.sleep(.5)
    raise UserError('Native action did not finish in time; inspect retained receipts before proceeding')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--home', type=Path, default=Path(r'D:\A World for Two'))
    parser.add_argument('--backup', required=True)
    parser.add_argument('--sha256', required=True)
    args = parser.parse_args()
    print(json.dumps(prepare_stage(args.home, args.backup, args.sha256), indent=2))
