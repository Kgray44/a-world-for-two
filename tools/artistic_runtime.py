"""Upgrade only reviewed artifacts in the stopped, private artistic runtime."""
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


def upgrade(home, *, include_mapping=False, include_chains=False,
            include_living_world=False, include_cozy_pets=False):
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
    permitted={'awft-control-bridge','awft-client-presentation'}
    if include_chains:
        m=new.get('reconnectible-chains',{})
        if ('reconnectible-chains' in old or m.get('project_id')!='5pzBXDS3'
                or m.get('version_id')!='e4yVoAvP' or m.get('side')!='both'
                or m.get('filename')!='connectiblechains-2.4.4+1.21.1-neoforge.jar'
                or m.get('hashes',{}).get('sha256')!='70d9f048e6f358c83b2d35f8a69000ec7827023efcc6d3b75346b4e34238bbd0'):
            raise UserError('Only the exact reviewed new zipline chain backend is admitted')
        permitted.add('reconnectible-chains')
    if include_living_world:
        # Exact reviewed NEW additions only; no update/removal exception.
        approved = {'awft-living-world': ('awft:living-world',
                               '0.2.0',
                               '0.2.0',
                               'awft-living-world-0.2.0.jar',
                               '093b7a487e664c7ef7a8e73c2fb2d2e4dca3f2da17944dd678c0e4dabcd31a70'),
         'chatting-villagers': ('curseforge:1638757',
                                'curseforge:9064041',
                                '1.1.0',
                                'chattingvillagers-neoforge-1.21.1-1.1.0.jar',
                                'a93084403db82eea6ec5069424aca0cedbf8c9592e41d4ab3658299ba34afd5a'),
         'smart-villagers-ai': ('l9oZCCPS',
                                'bGNaqTaL',
                                '2.0.0+neoforge-1.21.1',
                                'smartvillagers-neoforge-1.21.1-2.0.0.jar',
                                'bbfbfacd7210def810dacf36352cc55f2b3169db5fa7befd90888dd9a74c1630')}
        for slug, expected in approved.items():
            m=new.get(slug,{})
            actual=(m.get('project_id'),m.get('version_id'),m.get('version'),
                    m.get('filename'),m.get('hashes',{}).get('sha256'))
            if (slug in old or actual!=expected or m.get('side')!='both' or m.get('kind')!='mod'
                    or m.get('optional',False) is not False or m.get('default',True) is not True):
                raise UserError('Only the exact reviewed new Living World artifacts are admitted')
        permitted.update(approved)
    if include_cozy_pets:
        # Exact reviewed NEW additions only; no update/removal exception.
        approved = {'adorable-hamster-pets': ('LmrhZdK2',
                                   'LyCV3JSL',
                                   '3.7.0-1.21.1+neoforge',
                                   'adorablehamsterpets-3.7.0-1.21.1+neoforge.jar',
                                   '0651244d2aaf4c127ee1818a24910bf6612a33bb3aa078217ee8c695abf2cbc8be118d29ed5e271f8f7ba316f146767b8882800a38713177993444db7df2041a'),
         'aquarius-libs': ('KkHnyaL6',
                           'sPrpmle3',
                           '1.2.0-neoforge-1.21.1-21.1.217',
                           'aquariuslibs-1.2.0-neoforge-1.21.1-21.1.217.jar',
                           '4521e42504e1ecc73aab95895655425eb0914ddb964b242edea77f9bf38c406d63232187212b7cb3295821243599b6ba3d4b21805439aedd0df9f0ed4db9bb42'),
         'patchouli': ('nU0bVIaL',
                       'BIogJv2D',
                       '1.21.1-93-neoforge',
                       'Patchouli-1.21.1-93-NEOFORGE.jar',
                       '0b5c172db9a6eeecb5ca44b359a83548c3a60be7ff313959acdfc1e5b8039736c18e57e947d435b52d06da31159d2d02ea36e5742668dbc826308a4c99e4039f')}
        for slug, expected in approved.items():
            m=new.get(slug,{})
            actual=(m.get('project_id'),m.get('version_id'),m.get('version'),
                    m.get('filename'),m.get('hashes',{}).get('sha512'))
            if (slug in old or actual!=expected or m.get('side')!='both' or m.get('kind')!='mod'
                    or m.get('optional',False) is not False or m.get('default',True) is not True):
                raise UserError('Only the exact reviewed new cozy pets artifacts are admitted')
        permitted.update(approved)
    if include_mapping:
        m=new.get('maphorizons',{});before=old.get('maphorizons',{})
        if (m.get('filename')!='maphorizons-1.1.0-awft.2.jar'
                or m.get('hashes',{}).get('sha256')!='cd5f5a0d41f02d1c720b0ce3f603f0cc3c3f92db02aa8226565b4e394fbc7ef4'
                or before.get('hashes',{}).get('sha256')!='da36054b9d59083481bfe9c946d17a2f0f87705a6d883718b26351848d40ff93'
                or m.get('side')!=before.get('side') or m.get('license',{}).get('id')!='MIT'):
            raise UserError('The exact reviewed mapping repair and predecessor are required')
        permitted.add('maphorizons')
    if not changes or not changes<=permitted:
        raise UserError('Only the explicitly admitted helper, mapping and exact new artifact changes are allowed')
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
    p.add_argument('--include-mapping',action='store_true')
    p.add_argument('--include-chains',action='store_true')
    p.add_argument('--include-living-world',action='store_true')
    p.add_argument('--include-cozy-pets',action='store_true')
    args=p.parse_args()
    print(json.dumps(upgrade(args.home,include_mapping=args.include_mapping,include_chains=args.include_chains,
        include_living_world=args.include_living_world,include_cozy_pets=args.include_cozy_pets)))
