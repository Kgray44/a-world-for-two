"""Install an owned server-only administration bridge after a verified world backup.

Rejects every gameplay artifact or configuration change. The reviewed client
title-screen layout and exact Tectonic CRLF-to-LF normalization may accompany the
bridge. Tectonic must already have the exact normalized bytes in the live server.
Does not waive or invent
Mod Manager's broader release qualification, and never replaces a saved world.
"""
from __future__ import annotations

import argparse
import os
import shutil
import time
from pathlib import Path

from control_room.backups import Backups
from control_room.common import Layout, REPO, UserError, contained, digest, read_json, utcnow, write_json
from control_room.pack import validate_jars, validate_pack, verify_installed
from control_room.server import Server
from control_room.storage import Storage


def update(home):
    layout=Layout(home);storage=Storage(layout);server=Server(layout,storage)
    if server.running():raise UserError('Stop the official server before changing its administration bridge')
    if not layout.settings()['permanent_world'] or not any(layout.world.rglob('level.dat')):
        raise UserError('This operation needs the existing official world; first provisioning is separate')
    if verify_installed(layout):raise UserError('Installed server has unexpected changes')
    oldactive=read_json(layout.home/'packwiz/active.json')
    oldsource=contained(layout.releases,oldactive['version'])
    old=read_json(oldsource/'lock.json');new=read_json(REPO/'catalog/lock.json')
    if validate_pack(REPO/'packwiz',new) or validate_jars(new,layout.caches/'mods')['errors']:
        raise UserError('Native artifact and manifest checks must pass first')
    def pins(lock):
        return {m['slug']:{k:m.get(k) for k in ('filename','hashes','side','kind','optional','default')}
                for m in lock['mods'] if m['slug']!='awft-control-bridge'}
    if pins(old)!=pins(new) or old['neoforge']!=new['neoforge']:
        raise UserError('This helper permits only the owned server-only bridge to change')
    before=next(m for m in old['mods'] if m['slug']=='awft-control-bridge')
    after=next(m for m in new['mods'] if m['slug']=='awft-control-bridge')
    if before['side']!='server' or after['side']!='server' or after['provider']!='local-build':
        raise UserError('Only the project-owned server-only administration bridge is permitted')
    client_changes=[];byte_normalizations=[]
    for folder in ('config','defaultconfigs'):
        left={p.relative_to(oldsource).as_posix():digest(p) for p in (oldsource/folder).rglob('*') if p.is_file()}
        right={p.relative_to(REPO/'packwiz').as_posix():digest(p) for p in (REPO/'packwiz'/folder).rglob('*') if p.is_file()}
        changed={name for name in left.keys()|right.keys() if left.get(name)!=right.get(name)}
        normalized='config/tectonic.json'
        if normalized in changed:
            before_bytes=(oldsource/normalized).read_bytes()
            after_bytes=(REPO/'packwiz'/normalized).read_bytes()
            if (before_bytes.replace(b'\r\n',b'\n')!=after_bytes or before_bytes==after_bytes or
                digest(layout.server/normalized)!=right[normalized]):
                raise UserError('Tectonic may only normalize line endings to the exact existing server bytes')
            byte_normalizations.append({'file':normalized,'before_sha256':left[normalized],
                'after_sha256':right[normalized],'server_bytes_already_match':True})
            changed.remove(normalized)
        permitted={'config/fancymenu/customization/awft_title.txt'}
        if changed-permitted:raise UserError('Gameplay configuration and world generation cannot change through this helper')
        if changed:
            menu=(REPO/'packwiz/config/fancymenu/customization/awft_title.txt').read_text(encoding='utf-8')
            if ('action_type:joinserver' in menu or menu.count('instance_identifier = mc_titlescreen_multiplayer_button')!=1
                    or 'label = Join Our World' not in menu):
                raise UserError('The reviewed client-only native multiplayer menu change differs')
            client_changes.extend(sorted(changed))
    backups=Backups(layout,storage,server)
    receipt=backups.create(reason='before-owned-construction-bridge',resume=False)
    ident=receipt['id'];backups.verify(ident)
    history=contained(layout.staging,'technical-bridge-update-'+str(time.time_ns()));history.mkdir()
    release=contained(layout.releases,new['version'])
    if release.exists():raise UserError('Choose a fresh immutable release version')
    storage.reserve(after['size']+32*1024**2)
    cached=layout.caches/'mods'/after['filename']
    if cached.stat().st_size!=after['size'] or digest(cached)!=after['hashes']['sha256']:raise UserError('New owned bridge differs from its pin')
    shutil.copytree(REPO/'packwiz',release);write_json(release/'lock.json',new)
    for path in (layout.server/'installed.json',layout.home/'packwiz/active.json'):
        shutil.copy2(path,history/path.name)
    oldjar=contained(layout.server,'mods/'+before['filename'])
    newjar=contained(layout.server,'mods/'+after['filename'])
    if newjar.exists():raise UserError('Unexpected candidate bridge already exists')
    oldjar.rename(history/oldjar.name)
    try:
        shutil.copy2(cached,newjar)
        installed=read_json(layout.server/'installed.json');files=installed['files']
        files.pop(before['filename']);files[after['filename']]=digest(newjar)
        sha=digest(REPO/'packwiz/pack.toml')
        installed.update(files=files,pack_sha256=sha,pack_version=new['version'],at=utcnow(),
            validation='Exact gameplay pins/configuration unchanged. Owned administration bridge updated; runtime checks pending.')
        write_json(layout.server/'installed.json',installed)
        write_json(layout.home/'packwiz/active.json',oldactive|{'version':new['version'],'pack_sha256':sha,'at':utcnow(),'client_relaunch_required':True})
        if verify_installed(layout):raise UserError('Updated installed-byte verification failed')
    except BaseException:
        if newjar.exists():newjar.rename(history/('failed-'+newjar.name))
        shutil.copy2(history/oldjar.name,oldjar)
        shutil.copy2(history/'installed.json',layout.server/'installed.json')
        shutil.copy2(history/'active.json',layout.home/'packwiz/active.json')
        raise
    actual=read_json(layout.backups/(ident+'.json'))
    write_json(layout.state/'settlement/backup-receipt.json',{'verified':True,'id':ident,'sha256':actual['sha256'],
        'at':utcnow(),'scope':'Complete official world and content-bearing configuration; archive hashes verified before construction'})
    result={'at':utcnow(),'version':new['version'],'pack_sha256':sha,'previous':before['version'],
            'bridge':after['version'],'backup':ident,'preserved':str(history),'world':'preserved without replacement; restart required'}
    result['client_only_presentation_files']=client_changes
    result['byte_only_config_normalizations']=byte_normalizations
    write_json(history/'update.json',result)
    print(__import__('json').dumps(result),flush=True)
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--home',type=Path,default=Path(r'D:\A World for Two'))
    update(parser.parse_args().home)
