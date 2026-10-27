"""Owner-authorized first provisioning only; never replaces an existing world.

This does not bypass Mod Manager's acceptance gates for updates to saved worlds.
The previous installation and a verified full ZIP remain private recoverable backups.
"""
from __future__ import annotations

import argparse
import os
import shutil
import time
import zipfile
from pathlib import Path

import psutil

from control_room.common import Layout, REPO, UserError, contained, digest, read_json, utcnow, write_json
from control_room.pack import validate_pack, validate_jars, verify_installed
from control_room.settings import format_properties, properties
from control_room.storage import Storage, tree_size, GiB
from .playtest import guard


def initialize(home, fixture_id):
    layout = Layout(home)
    fixture = Layout(contained(layout.staging, 'world-tests/' + fixture_id))
    owner = read_json(fixture.state / 'test-owner.json', {})
    if owner.get('owner_source') != str(REPO) or owner.get('id') != fixture_id:
        raise UserError('Choose the exact owned, stopped reference installation')
    if tree_size(layout.world) != 0 or any(layout.server.rglob('level.dat')):
        raise UserError('An existing permanent world must never be replaced by first provisioning')
    for process in psutil.process_iter(['name']):
        if (process.info['name'] or '').lower() not in ('java.exe','javaw.exe','java','javaw'):
            continue
        try:
            if Path(process.cwd()).resolve() in (layout.server, fixture.server):
                raise UserError('Stop both dedicated servers before first provisioning')
        except psutil.NoSuchProcess:
            pass
        except psutil.AccessDenied as error:
            raise UserError('Cannot verify server shutdown') from error
    lock = read_json(REPO / 'catalog/lock.json')
    source = REPO / 'packwiz'
    sha = digest(source / 'pack.toml')
    if validate_pack(source,lock) or validate_jars(lock,layout.caches/'mods')['errors']:
        raise UserError('The canonical candidate must pass integrity and dependency checks')
    installed = read_json(fixture.server/'installed.json', {})
    if installed.get('pack_sha256') != sha or verify_installed(fixture):
        raise UserError('The reference installation must match the exact canonical candidate')
    if verify_installed(layout):
        raise UserError('The previous installation has unexpected changes; review them first')
    maximum = tree_size(layout.server) * 2 + sum(m['size'] for m in lock['mods']) + 128*1024**2
    if maximum > 4*GiB:
        raise UserError('Split first provisioning into a smaller bounded step')
    reserve = guard(16*1024**2,maximum)
    storage=Storage(layout)
    storage.reserve(maximum)
    checkpoint=contained(layout.staging,'official-initialization-'+str(time.time_ns()))
    checkpoint.mkdir()
    report={'at':utcnow(),'status':'preparing','pack_sha256':sha,'version':lock['version'],
            'world':str(layout.world/'AWorldForTwo'),'previous_world_bytes':0,'guard':reserve,
            'authority':'Owner explicitly requested a clean official world and permanent settlement; further owner playtesting waived.',
            'acceptance':'Additional owner playtesting waived. Untested feature and multiplayer checks remain unverified.'}
    write_json(checkpoint/'initialization.json',report)
    previous_files=[p for p in layout.server.rglob('*') if p.is_file()]
    previous_files += [p for p in (layout.settings_path,layout.home/'packwiz/active.json') if p.is_file()]
    manifest=[{'path':p.relative_to(layout.home).as_posix(),'size':p.stat().st_size,'sha256':digest(p)} for p in previous_files]
    backup=checkpoint/'before-official-world.zip'
    with zipfile.ZipFile(backup,'x',zipfile.ZIP_DEFLATED,compresslevel=1) as archive:
        import json
        for file in previous_files:
            archive.write(file,file.relative_to(layout.home).as_posix())
            storage.checkpoint(maximum)
        archive.writestr('awft-initialization-backup.json',json.dumps({'world_bytes':0,'files':manifest}))
    with zipfile.ZipFile(backup) as archive:
        import hashlib
        if archive.testzip(): raise UserError('The full pre-provisioning backup failed CRC verification')
        for item in manifest:
            with archive.open(item['path']) as stream:
                hasher=hashlib.sha256()
                for block in iter(lambda:stream.read(1024*1024),b''): hasher.update(block)
            if hasher.hexdigest()!=item['sha256']:raise UserError('Backup hash verification failed')
    report['backup']={'path':str(backup),'sha256':digest(backup),'files':len(manifest),'verified':True}
    write_json(checkpoint/'initialization.json',report)
    staged=checkpoint/'prepared-server'
    staged.mkdir()
    shutil.copytree(fixture.server/'libraries',staged/'libraries',copy_function=os.link)
    for group in ('config','defaultconfigs'):
        if (source/group).exists():shutil.copytree(source/group,staged/group)
    (staged/'mods').mkdir()
    for filename,value in installed['files'].items():
        cached=layout.caches/'mods'/filename
        if digest(cached)!=value:raise UserError('Canonical cached JAR changed: '+filename)
        shutil.copy2(cached,staged/'mods'/filename)
    for name in ('eula.txt','whitelist.json','ops.json','banned-players.json','banned-ips.json'):
        path=layout.server/name
        if path.exists():shutil.copy2(path,staged/name)
    props=properties((layout.server/'server.properties').read_text())
    props.update({'level-name':(layout.world/'AWorldForTwo').as_posix(),'server-port':25565,
                  'view-distance':6,'simulation-distance':4,'online-mode':True,'white-list':True})
    (staged/'server.properties').write_text(format_properties(props),encoding='utf-8')
    write_json(staged/'installed.json',installed|{'at':utcnow(),'initial_provisioning':True,
        'validation':'Manifest/native dependencies passed; official startup pending. Further interactive acceptance waived by owner, not recorded as passed.'})
    release=contained(layout.releases,lock['version'])
    if release.exists():
        if digest(release/'pack.toml')!=sha:raise UserError('Immutable release differs')
    else:
        shutil.copytree(source,release)
        write_json(release/'lock.json',lock)
    old=checkpoint/'previous-server'
    assert old.resolve().is_relative_to(checkpoint.resolve()) and staged.resolve().is_relative_to(checkpoint.resolve())
    layout.server.rename(old)
    try:
        staged.rename(layout.server)
        options=layout.settings()
        options.update(permanent_world=True,world_created=False)
        layout.save_settings(options)
        write_json(layout.home/'packwiz/active.json',{'version':lock['version'],'pack_sha256':sha,
            'at':utcnow(),'publication':'owner-authorized initial local permanent world; public client channel pending',
            'client_relaunch_required':True})
        if verify_installed(layout):raise UserError('Provisioned server failed installed-byte verification')
    except BaseException:
        if layout.server.exists():layout.server.rename(checkpoint/'failed-prepared-server')
        old.rename(layout.server)
        for relative in ('dashboard/settings.json','packwiz/active.json'):
            with zipfile.ZipFile(backup) as archive:
                from control_room.common import atomic_write
                atomic_write(contained(layout.home,relative),archive.read(relative))
        raise
    report.update(status='official installation provisioned; new world has not yet been generated',
                  server_jars=len(installed['files']),previous_installation=str(old))
    write_json(checkpoint/'initialization.json',report)
    write_json(layout.state/'official-initialization.json',report)
    print(__import__('json').dumps(report),flush=True)
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--home',type=Path,default=Path(r'D:\A World for Two'))
    parser.add_argument('--from-owned-fixture',required=True)
    args=parser.parse_args()
    initialize(args.home,args.from_owned_fixture)
