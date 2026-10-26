"""Update one stopped, owned disposable pair; never promotes a permanent world.

Old managed bytes, configuration and receipts are retained. An integrity-checked
world backup is required before mutation. Partial updates retain a failure receipt.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import time
import zipfile
from pathlib import Path

import psutil

from control_room.backups import Backups
from control_room.common import Layout, REPO, UserError, atomic_write, contained, digest, read_json, utcnow, write_json
from control_room.pack import generate_pack, validate_jars, validate_pack
from control_room.presentation import closed, toml_update
from control_room.server import Server
from control_room.storage import Storage, tree_size
from .playtest import guard


def owned_pair(parent, ident):
    import re
    if not re.fullmatch(r'\d{8}T\d{6}Z-play-[a-f0-9]{6}', ident):
        raise UserError('Choose an exact owned disposable playtest ID')
    home = contained(parent.staging, 'world-tests/' + ident)
    layout = Layout(home)
    owner = read_json(layout.state / 'test-owner.json', {})
    receipt = read_json(layout.logs / 'playtest-prepared.json', {})
    if (owner.get('owner_source') != str(REPO) or owner.get('id') != ident
            or receipt.get('home') != str(home) or receipt.get('parent') != str(parent.home)
            or layout.settings()['permanent_world']):
        raise UserError('Only an explicitly owned disposable pair can be updated')
    instance = contained(parent.home, 'instances/' + receipt['client']['id'])
    client = read_json(instance / 'awft-owned.json', {})
    if client.get('format') != 'awft-owned-client:1' or client.get('root') != str(instance):
        raise UserError('Client ownership does not match the disposable test')
    closed(instance)
    for process in psutil.process_iter(['name']):
        if (process.info['name'] or '').lower() not in ('java.exe', 'javaw.exe', 'java', 'javaw'):
            continue
        try:
            if Path(process.cwd()).resolve() == layout.server:
                raise UserError('Stop the disposable server before updating it')
        except psutil.NoSuchProcess:
            pass
        except psutil.AccessDenied as error:
            raise UserError('Cannot verify that the disposable server is stopped') from error
    return layout, instance, receipt, client


def update(home, ident):
    parent = Layout(home)
    layout, instance, prepared, client = owned_pair(parent, ident)
    storage = Storage(layout)
    lock = read_json(REPO / 'catalog/lock.json')
    errors = validate_pack(REPO / 'packwiz', lock)
    native = validate_jars(lock, parent.caches / 'mods')
    if errors or native['errors']:
        raise UserError('The exact candidate must pass manifest and native dependency checks')
    release = contained(layout.releases, lock['version'])
    if release.exists():
        raise UserError('Use a new immutable candidate version for each disposable update')
    mc = contained(instance, '.minecraft')
    server_receipt = read_json(layout.server / 'installed.json', {})
    actual = {p.name for p in (layout.server / 'mods').glob('*.jar')}
    if actual != set(server_receipt.get('files', {})):
        raise UserError('Unexpected server JARs require review before updating')
    for name, value in server_receipt['files'].items():
        if digest(contained(layout.server, 'mods/' + name)) != value:
            raise UserError('A managed server JAR was changed: ' + name)
    for row in client['files']:
        if digest(contained(mc, row['file'])) != row['sha256']:
            raise UserError('A managed client artifact was changed: ' + row['file'])
    known_client_jars = {row['file'] for row in client['files'] if row['file'].startswith('mods/')}
    if {p.relative_to(mc).as_posix() for p in (mc / 'mods').glob('*.jar')} != known_client_jars:
        raise UserError('Unexpected client JARs require review before updating')
    expected = {}
    for item in lock['mods']:
        if item.get('optional') and not item.get('default', True):
            continue
        path = contained(parent.caches, 'mods/' + item['filename'])
        if path.stat().st_size != item['size'] or any(digest(path, alg) != value for alg, value in item['hashes'].items()):
            raise UserError('Candidate cache differs from its pin: ' + item['filename'])
        expected[item['filename']] = item
    config_bytes = tree_size(REPO / 'packwiz/config')
    backup_bytes = tree_size(layout.world) + tree_size(layout.server / 'config') + 4 * 1024 * 1024
    artifact_bytes = sum(m['size'] for m in expected.values())
    # Full copies would fit this conservative bound; unchanged files are reused.
    allocation = backup_bytes * 2 + artifact_bytes * 2 + config_bytes * 5 + 32 * 1024 * 1024
    if allocation > 3 * 1024**3:
        raise UserError('Split this disposable update; its allocation exceeds 3 GiB')
    reserve = guard(4 * 1024 * 1024, allocation)
    storage.reserve(allocation)
    history = contained(layout.staging, 'update-' + str(time.time_ns()))
    history.mkdir()
    report = {'at': utcnow(), 'previous_pack': prepared['source_pack_sha256'],
        'pack_sha256': digest(REPO / 'packwiz/pack.toml'), 'version': lock['version'],
        'guard': reserve, 'status': 'preparing', 'changes': [], 'preserved': str(history)}
    write_json(history / 'update.json', report)
    def replace(target, raw, label):
        if target.exists() and target.read_bytes() == raw:
            return
        if target.exists():
            old = history / 'previous' / label
            old.parent.mkdir(parents=True, exist_ok=True)
            if not old.exists():
                shutil.copy2(target, old)
        atomic_write(target, raw)
        report['changes'].append(label)
    try:
        server = Server(layout, storage)
        backups = Backups(layout, storage, server)
        backups._unlocked_world()
        # Standard manifest + verification, without automatic retention deletion.
        files = [p for group in (layout.world, layout.server / 'config', layout.server / 'defaultconfigs')
                 for p in group.rglob('*') if p.is_file() and p.name != 'session.lock']
        manifest = {'format': 1, 'files': []}
        path = history / 'pre-update-world.zip'
        with zipfile.ZipFile(path, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=3) as archive:
            for file in files:
                relative = file.relative_to(layout.home).as_posix()
                contained(layout.home, relative)
                manifest['files'].append({'path': relative, 'size': file.stat().st_size, 'sha256': digest(file)})
                archive.write(file, relative)
                storage.checkpoint(allocation)
            archive.writestr('awft-backup.json', json.dumps(manifest))
        backups.verify_archive(path)
        report['world_backup'] = {'path': str(path), 'sha256': digest(path), 'verified': True}
        shutil.copytree(REPO / 'packwiz', release)
        write_json(release / 'lock.json', lock)
        for name in ('installed.json',):
            shutil.copy2(layout.server / name, history / name)
        shutil.copy2(instance / 'awft-owned.json', history / 'awft-owned.json')
        shutil.copy2(layout.home / 'packwiz/active.json', history / 'active.json')
        # Move obsolete managed server JARs aside; preserve all content and history.
        wanted_server = {n:m for n,m in expected.items() if m['kind'] == 'mod' and m['side'] in ('server','both')}
        for name in actual - wanted_server.keys():
            target = contained(layout.server, 'mods/' + name)
            old = history / 'previous/server/mods' / name
            old.parent.mkdir(parents=True, exist_ok=True)
            os.replace(target, old)
        for name, item in wanted_server.items():
            source = parent.caches / 'mods' / name
            target = contained(layout.server, 'mods/' + name)
            if not target.exists() or digest(target) != digest(source):
                replace(target, source.read_bytes(), 'server/mods/' + name)
            cached = layout.caches / 'mods' / name
            if not cached.exists():
                os.link(source, cached)
        wanted_client = {}
        for name, item in expected.items():
            if item['side'] == 'server':
                continue
            folder = {'mod':'mods','shader':'shaderpacks','resourcepack':'resourcepacks'}[item['kind']]
            wanted_client[folder + '/' + name] = item
        for row in client['files']:
            if row['file'] not in wanted_client:
                old = history / 'previous/client' / row['file']
                old.parent.mkdir(parents=True, exist_ok=True)
                os.replace(contained(mc, row['file']), old)
        for relative, item in wanted_client.items():
            target = contained(mc, relative)
            source = parent.caches / 'mods' / item['filename']
            if not target.exists() or digest(target) != digest(source):
                replace(target, source.read_bytes(), 'client/' + relative)
        # Only the known integration payload and title art/layout are replaced.
        # Keep native generated settings, player shader choices and existing tables.
        for source in (REPO / 'packwiz/config').rglob('*'):
            if not source.is_file():
                continue
            relative = source.relative_to(REPO / 'packwiz').as_posix()
            managed = relative.startswith(('config/paxi/', 'config/fancymenu/'))
            for root, label in ((layout.server,'server'),(mc,'client')):
                target = contained(root, relative)
                if managed or not target.exists():
                    replace(target, source.read_bytes(), label + '/' + relative)
        camera = mc / 'config/cinematic-client.toml'
        replace(camera, toml_update(camera.read_text(), 'multiplayer', {'clientOnlyMode':False,'serverHintSeen':True}), 'client/config/cinematic-client.toml')
        old_client_pack = mc / 'packwiz'
        os.replace(old_client_pack, history / 'previous-client-packwiz')
        shutil.copytree(release, old_client_pack)
        # Preserve the disposable Join button's port, independent of public defaults.
        menu = mc / 'config/fancymenu/customization/awft_title.txt'
        import re
        replace(menu, re.sub(rb'(\[action_type:joinserver\]\s*=\s*)[^\r\n]+', lambda m:m[1]+b'127.0.0.1:25575', menu.read_bytes()), 'client/config/fancymenu/customization/awft_title.txt')
        files = {n:digest(layout.server/'mods'/n) for n in wanted_server}
        write_json(layout.server/'installed.json', {'pack_version':lock['version'],'pack_sha256':report['pack_sha256'],
            'neoforge':lock['neoforge'],'at':utcnow(),'files':files,'validation':'Static checks passed; updated candidate runtime pending'})
        write_json(layout.home/'packwiz/active.json', {'version':lock['version'],'pack_sha256':report['pack_sha256'],
            'at':utcnow(),'publication':'local disposable candidate only','client_relaunch_required':True})
        client.update(source_pack_sha256=report['pack_sha256'],pack_sha256=report['pack_sha256'],
            files=[{'file':r,'size':(mc/r).stat().st_size,'sha256':digest(mc/r)} for r in wanted_client], updated=utcnow())
        write_json(instance/'awft-owned.json',client)
        prepared.update(client=client,source_pack_sha256=report['pack_sha256'],pack_sha256=report['pack_sha256'],updated=utcnow(),
            native_mod_jars=len(native['jars']),status='Updated owned candidate; runtime validation pending')
        write_json(layout.logs/'playtest-prepared.json',prepared)
        write_json(parent.state/'prepared-playtest.json',prepared)
        write_json(parent.state/'owned-client.json',client)
        report['status'] = 'updated; saved world preserved, runtime pending'
    except BaseException as error:
        report.update(status='failed; partial state and previous bytes retained', error=str(error))
        raise
    finally:
        write_json(history/'update.json',report)
    print(json.dumps({k:report[k] for k in ('version','pack_sha256','status','preserved')}),flush=True)
    return report


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--home',type=Path,default=Path(r'D:\A World for Two'))
    parser.add_argument('--id',required=True)
    args=parser.parse_args()
    update(args.home,args.id)
