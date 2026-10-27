"""Upgrade only owned helper artifacts in the stopped, private artistic runtime."""
from pathlib import Path
import json
import os
import shutil
import time

import psutil

from control_room.common import Layout, REPO, UserError, digest, read_json, write_json, utcnow
from control_room.pack import validate_pack, verify_installed
from control_room.storage import tree_size
from .playtest import guard
from .artistic_capture import CLIENT


def upgrade(home):
    layout=Layout(home)
    owner=read_json(layout.state/'artistic-owner.json',{})
    if (owner.get('format')!='awft-artistic-stage:1'
            or Path(owner.get('home','')).resolve()!=layout.home
            or not layout.home.is_relative_to(Path(r'D:\A World for Two\staging\world-tests'))):
        raise UserError('Only the owned private artistic runtime is admitted')
    for p in psutil.process_iter(['name','cwd']):
        try:
            if (p.info['name'] or '').lower() in ('java.exe','javaw.exe') and Path(p.cwd()).resolve() in (layout.server,CLIENT):
                raise UserError('Close the owned server and client normally before changing artifacts')
        except psutil.NoSuchProcess:pass
    errors=verify_installed(layout)
    if errors:raise UserError(str(errors))
    lock=read_json(REPO/'catalog/lock.json')
    if validate_pack(REPO/'packwiz',lock):raise UserError('Canonical Packwiz integrity failed')
    previous=read_json(layout.releases/read_json(layout.home/'packwiz/active.json')['version']/'lock.json')
    old={m['slug']:m for m in previous['mods']};new={m['slug']:m for m in lock['mods']}
    changes={slug for slug in set(old)|set(new) if old.get(slug)!=new.get(slug)}
    if not changes or not changes<={'awft-control-bridge','awft-client-presentation'}:
        raise UserError('This operation preserves every gameplay artifact pin')
    maximum=3*tree_size(REPO/'packwiz')+8*1024**2
    if maximum>64*1024**2:raise UserError('Split the manifest upgrade into a bounded step')
    guard(8*1024**2,maximum)
    output=layout.staging/('owned-helper-upgrade-'+str(time.time_ns()));output.mkdir()
    write_json(output/'before.json',{'active':read_json(layout.home/'packwiz/active.json'),
        'installed':read_json(layout.server/'installed.json'),'owner':owner})
    release=layout.releases/lock['version']
    if release.exists():raise UserError('The new immutable runtime release already exists')
    shutil.copytree(REPO/'packwiz',release);write_json(release/'lock.json',lock)
    server_mods=output/'prepared-server-mods';server_mods.mkdir()
    files={}
    root=Layout(Path(r'D:\A World for Two'))
    for m in lock['mods']:
        if m['kind']!='mod' or m['side'] not in ('both','server') or m.get('optional') and not m.get('default',True):continue
        source=root.caches/'mods'/m['filename'] if m['slug'] in changes else layout.server/'mods'/m['filename']
        algorithm=next(a for a in ('sha512','sha256','sha1') if a in m['hashes'])
        if digest(source,algorithm)!=m['hashes'][algorithm]:raise UserError('A server source artifact differs')
        os.link(source,server_mods/m['filename']);files[m['filename']]=digest(source)
    client_mods=output/'prepared-client-mods';client_mods.mkdir()
    changed_old={old[s]['filename'] for s in changes if s in old}
    for f in (CLIENT/'mods').iterdir():
        if f.is_file() and f.name not in changed_old:os.link(f,client_mods/f.name)
    for slug in changes:
        m=new[slug]
        if m['side'] not in ('both','client'):continue
        source=root.caches/'mods'/m['filename']
        if digest(source)!=m['hashes']['sha256']:raise UserError('An owned client source differs')
        shutil.copy2(source,client_mods/m['filename'])
    client_files=[]
    for m in lock['mods']:
        if m['side']=='server' or m.get('optional') and not m.get('default',True):continue
        group={'mod':'mods','shader':'shaderpacks','resourcepack':'resourcepacks'}[m['kind']]
        f=(client_mods if group=='mods' else CLIENT/group)/m['filename']
        algorithm=next(a for a in ('sha512','sha256','sha1') if a in m['hashes'])
        if digest(f,algorithm)!=m['hashes'][algorithm]:raise UserError('The retained client inventory differs')
        client_files.append({'file':group+'/'+f.name,'sha256':digest(f),'size':f.stat().st_size})
    (layout.server/'mods').rename(output/'previous-server-mods');server_mods.rename(layout.server/'mods')
    (CLIENT/'mods').rename(output/'previous-client-mods');client_mods.rename(CLIENT/'mods')
    if (CLIENT/'packwiz').exists():(CLIENT/'packwiz').rename(output/'previous-client-packwiz')
    shutil.copytree(release,CLIENT/'packwiz')
    active={'version':lock['version'],'pack_sha256':digest(release/'pack.toml'),'at':utcnow(),
        'publication':'private artistic candidate; native startup and client checks pending','client_relaunch_required':True}
    write_json(layout.home/'packwiz/active.json',active)
    write_json(layout.server/'installed.json',{'pack_version':lock['version'],'pack_sha256':active['pack_sha256'],
        'neoforge':lock['neoforge'],'at':utcnow(),'files':files,'validation':'Exact retained gameplay pins and owned helper bytes; native checks pending'})
    owned=read_json(CLIENT.parent/'awft-owned.json');owned.update(at=utcnow(),files=client_files,
        source_pack_sha256=active['pack_sha256'],pack_sha256=active['pack_sha256'])
    write_json(CLIENT.parent/'awft-owned.json',owned)
    owner.update(pack_sha256=active['pack_sha256'],updated=utcnow());write_json(layout.state/'artistic-owner.json',owner)
    if verify_installed(layout):raise UserError('Updated server inventory verification failed; retain prior directories')
    result={'at':utcnow(),'version':lock['version'],'pack_sha256':active['pack_sha256'],
        'changed_artifacts':sorted(changes),'server_mods':len(files),'client_artifacts':len(client_files),
        'previous_directories':str(output),'world_mutations':0,'runtime_validation':'pending'}
    write_json(output/'result.json',result);return result


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--home',required=True,type=Path)
    print(json.dumps(upgrade(p.parse_args().home)))
