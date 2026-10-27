"""Owner-authorized replacement with the freshly authored, stopped world.

The discarded world and all prior player files remain private retained history.
They are never merged into the new active save. No downloaded binary or world
data belongs in Git.
"""
from pathlib import Path
import hashlib
import json
import os
import shutil
import time
import zipfile

import nbtlib
import psutil

from control_room.common import Layout, REPO, UserError, atomic_write, digest, read_json, write_json, utcnow
from control_room.backups import Backups
from control_room.pack import verify_installed, validate_pack
from control_room.server import Server
from control_room.storage import Storage, tree_size
from control_room.settings import properties, format_properties
from .playtest import guard


CINEMATIC_FOLDER=Path('paxi/datapacks/awft-settlement-cinematic')
# Pinned Paxi 5.1.3 uses the folder filename directly as PackLocationInfo.id;
# its PackSelectionConfig is required/TOP. This is not a world file/ pack ID.
CINEMATIC_PACK_ID='awft-settlement-cinematic'
CINEMATIC_ZIP_SHA256='c628db0e6c6f222ca56695ec2ff3b081732977704f21701153a55031bfa8ed18'
CINEMATIC_ENTRIES=frozenset({'pack.mcmeta',
    'data/awft/cutscenes/rose_lantern_arrival.json',
    'data/awft/cutscenes/rosewater_palace_replay.json',
    'data/awft/cutscenes/rosewater_lark_replay.json'})
WORLD_DASHBOARD_FILES=('cinematic-first-joins.json','cinematic-executions.json','cinematics.json',
    'last-player-locations.json','atlas-waypoints.json','atlas-landmark-notes.json','atlas-index.json',
    'bridge-atlas-index.json','atlas-returns.json','server-metrics.json','atlas-control.json',
    'official-initialization.json','sleep-rule-initialized')
WORLD_BOUND_DASHBOARD_FILES=('claim-proposals.json','claims-proposals.json','claim-cache.json',
    'claims-cache.json','dashboard-sync.json','world-sync.json')


def world_cinematic_entry(value):
    return str(value).casefold().startswith('file/awft-settlement-cinematic')


def prepare_level(path, cinematic_pack_id=CINEMATIC_PACK_ID):
    if cinematic_pack_id not in (None,CINEMATIC_PACK_ID):
        raise UserError('Only the native-verified Paxi folder ID is admitted')
    level=nbtlib.load(path);data=level['Data'];data.pop('Player',None)
    data['LevelName']=nbtlib.String('A World for Two');data['GameType']=nbtlib.Int(0)
    rules=data.setdefault('GameRules',nbtlib.Compound())
    for name in ('doDaylightCycle','doWeatherCycle'):rules[name]=nbtlib.String('true')
    data['DayTime']=nbtlib.Long(1000)
    packs=data.setdefault('DataPacks',nbtlib.Compound())
    enabled=[str(p) for p in packs.get('Enabled',[])
        if not world_cinematic_entry(p) and str(p)!=cinematic_pack_id]
    if cinematic_pack_id is not None:enabled.append(cinematic_pack_id)
    packs['Enabled']=nbtlib.List[nbtlib.String](enabled)
    packs['Disabled']=nbtlib.List[nbtlib.String]([str(p) for p in packs.get('Disabled',[])
        if not world_cinematic_entry(p) and str(p)!=cinematic_pack_id])
    level.save()


def cinematic_entries(path,expected_sha256):
    """Read a bounded immutable source ZIP; never install it in a world."""
    path=Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size>2*1024**2 or digest(path)!=expected_sha256:
        raise UserError('The reviewed cinematic ZIP differs')
    try:
        with zipfile.ZipFile(path) as archive:
            rows=archive.infolist();names=[r.filename for r in rows if not r.is_dir()]
            if (len(rows)>16 or len(names)!=len(set(names)) or set(names)!=CINEMATIC_ENTRIES
                    or sum(r.file_size for r in rows)>2*1024**2
                    or any(r.filename.startswith(('/', '\\')) or '\\' in r.filename
                        or ':' in r.filename or '..' in r.filename.split('/')
                        or (r.external_attr>>16)&0o170000==0o120000 for r in rows)
                    or archive.testzip()):
                raise UserError('The cinematic source has unsafe or unexpected archive entries')
            return {name:hashlib.sha256(archive.read(name)).hexdigest() for name in sorted(names)}
    except (OSError,zipfile.BadZipFile,RuntimeError) as error:
        raise UserError('The cinematic source archive is unreadable') from error


def verify_cinematic_folder(folder,expected):
    """Exact entry custody, including absence of extra files or linked inputs."""
    folder=Path(folder)
    if folder.is_symlink() or not folder.is_dir():raise UserError('Canonical raw Paxi cinematic folder is required')
    files={}
    for path in folder.rglob('*'):
        if path.is_symlink():raise UserError('Linked Paxi cinematic inputs are refused')
        if path.is_file():
            if path.stat().st_size>2*1024**2:raise UserError('Paxi cinematic entry exceeds its bound')
            files[path.relative_to(folder).as_posix()]=digest(path)
    if files!=expected:raise UserError('Canonical Paxi folder entries differ from the reviewed cinematic ZIP')
    return files


def retire_world_cinematics(world,retired):
    """Preserve both old and new world-local ZIPs outside the prepared save."""
    removed=[]
    for path in sorted((Path(world)/'datapacks').glob('*')):
        if not path.name.casefold().startswith('awft-settlement-cinematic') or path.suffix.casefold()!='.zip':continue
        if path.is_symlink() or not path.is_file():raise UserError('Unexpected linked/nonfile world cinematic ZIP')
        destination=Path(retired)/path.name
        if destination.exists():raise UserError('Cinematic retirement target already exists')
        path.rename(destination);removed.append(path.name)
    return removed


def retire_world_dashboard(state,previous,identity):
    """Retain rejected-world admissions without granting any fresh authority.

    No staged registry, proof, backup receipt, plan or completion marker is
    rebound to the official world. Its changed world path needs native proofs.
    """
    state,previous=Path(state),Path(previous)
    fields={'handoff_id','target_world','source_stage_world','candidate','pack_sha256'}
    if (set(identity)!=fields or any(not isinstance(v,str) or not v or len(v)>1024 for v in identity.values())
            or any(p.is_symlink() or p.is_junction() for p in (state,previous))):
        raise UserError('Exact unlinked dashboard handoff identity is required')
    state,previous=state.resolve(),previous.resolve()
    if not state.is_dir() or not previous.is_dir() or previous.is_relative_to(state) or state.is_relative_to(previous):
        raise UserError('Private dashboard retirement must be separate from active dashboard data')
    names=['settlement',*WORLD_DASHBOARD_FILES];unbound=[]
    for name in WORLD_BOUND_DASHBOARD_FILES:
        path=state/name
        if not path.exists():continue
        if path.is_symlink() or path.is_junction() or not path.is_file() or path.stat().st_size>1024**2:
            raise UserError('World-bound dashboard input is linked or exceeds its finite metadata bound')
        try:value=read_json(path)
        except (ValueError,OSError):unbound.append(name);continue
        # Pack/client sync and unbound or foreign-world metadata are not ours
        # to retire. Only explicit top-level world identity is sufficient.
        declared=[value.get(k) for k in ('world_path','world') if isinstance(value,dict) and isinstance(value.get(k),str)]
        if any(Path(v).resolve()==Path(identity['target_world']).resolve() for v in declared):names.append(name)
        else:unbound.append(name)
    moves=[]
    for name in names:
        source,destination=state/name,previous/name
        if not source.exists():continue
        if (source.is_symlink() or source.is_junction() or source.resolve().parent!=state
                or destination.exists() or destination.resolve().parent!=previous):
            raise UserError('Dashboard retirement path or private preservation target is unsafe')
        if name=='settlement' and not source.is_dir():raise UserError('Settlement admission namespace must be a real directory')
        moves.append((source,destination))
    for source,destination in moves:source.rename(destination)
    fresh=state/'settlement';fresh.mkdir()
    marker={'format':'awft-settlement-handoff:1','at':utcnow(),'identity':dict(identity),
        'construction_admitted':False,'status':'NO CONSTRUCTION ADMISSION',
        'registry_admitted':False,'backup_receipt_admitted':False,'source_stage_proofs_copied':False,
        'native_verification':'Not performed for the official target world identity',
        'required_before_construction':['Fresh stopped official-world backup',
            'Actual official-world registry export','Exact official-world geometry/native verification',
            'Operation-specific admission with the new identities']}
    write_json(fresh/'handoff-identity.json',marker)
    return {'retired':[p.name for p,_ in moves],
        'preserved_unbound_or_foreign_metadata':unbound,'new_settlement_marker':'settlement/handoff-identity.json',
        'construction_admitted':False,'source_stage_proofs_copied':False}


def stopped(layout):
    for p in psutil.process_iter(['name','cwd']):
        try:
            if (p.info['name'] or '').lower() in ('java.exe','javaw.exe') and Path(p.cwd()).resolve()==layout.server:
                raise UserError('Stop both dedicated servers normally before the handoff')
        except psutil.NoSuchProcess:pass
    Backups(layout,Storage(layout),Server(layout,Storage(layout)))._unlocked_world()


def deploy(home, stage_home, backup_id, backup_sha256, cinematic_zip, cinematic_sha256, cinematic_config):
    target,stage=Layout(home),Layout(stage_home)
    if target.home!=Path(r'D:\A World for Two') or not stage.home.is_relative_to(target.staging/'world-tests'):
        raise UserError('Only the named official runtime and its owned artistic stage are admitted')
    owner=read_json(stage.state/'artistic-owner.json',{})
    if owner.get('format')!='awft-artistic-stage:1' or Path(owner.get('home','')).resolve()!=stage.home:
        raise UserError('The fresh source is not an owned artistic stage')
    stopped(target);stopped(stage)
    if verify_installed(target) or verify_installed(stage):raise UserError('Installed artifact custody differs')
    lock=read_json(REPO/'catalog/lock.json');active=read_json(stage.home/'packwiz/active.json')
    if validate_pack(REPO/'packwiz',lock) or active['pack_sha256']!=digest(REPO/'packwiz/pack.toml'):
        raise UserError('The exact canonical candidate must match staging')
    source=stage.world/'RosewaterArtistic';old=target.world/'AWorldForTwo'
    if not source.is_dir() or not old.is_dir():raise UserError('Both expected world identities are required')
    size=tree_size(source)+tree_size(stage.server/'config')+tree_size(REPO/'packwiz')
    if size>768*1024**2:raise UserError('Split the handoff into a smaller bounded allocation')
    guard(16*1024**2,2*size+64*1024**2)
    archive=Backups(target,Storage(target),Server(target,Storage(target))).path(backup_id)
    if digest(archive)!=backup_sha256:raise UserError('The retained rejected-world archive changed')
    backup,_=Backups(target,Storage(target),Server(target,Storage(target))).verify_archive(archive)
    expected={r['path']:r for r in backup['files'] if r['path'].startswith('world/AWorldForTwo/')}
    actual={p.relative_to(target.home).as_posix():p for p in old.rglob('*') if p.is_file() and p.name!='session.lock'}
    if set(actual)!=set(expected) or any(digest(p)!=expected[n]['sha256'] for n,p in actual.items()):
        raise UserError('The discarded official save differs from its retained archive; checkpoint it first')
    cine=Path(cinematic_zip).resolve();config=Path(cinematic_config).resolve()
    if (not cine.is_relative_to(target.staging) or cine.stat().st_size>2*1024**2
            or digest(cine)!=cinematic_sha256 or not config.is_relative_to(cine.parent)
            or config.stat().st_size>64*1024):raise UserError('The reviewed cinematic input differs')
    if cinematic_sha256!=CINEMATIC_ZIP_SHA256:raise UserError('Use the final reviewed cinematic ZIP as the canonical folder source')
    cinematic_files=cinematic_entries(cine,cinematic_sha256)
    verify_cinematic_folder(REPO/'packwiz/config'/CINEMATIC_FOLDER,cinematic_files)
    verify_cinematic_folder(stage.releases/active['version']/'config'/CINEMATIC_FOLDER,cinematic_files)
    verify_cinematic_folder(stage.server/'config'/CINEMATIC_FOLDER,cinematic_files)
    out=target.staging/('fresh-artistic-handoff-'+str(time.time_ns()));out.mkdir()
    receipt={'at':utcnow(),'status':'preparing','source_stage':str(stage.home),
        'candidate':active['version'],'pack_sha256':active['pack_sha256'],
        'authority':'Owner expressly discarded tonight world/player changes and requested a fresh artistic rebuild',
        'retained_rejected_world_archive':{'id':backup_id,'sha256':backup_sha256},
        'old_player_progress_merged':False,'interactive_owner_retest':'waived by owner; never recorded as passed'}
    write_json(out/'handoff.json',receipt)
    prepared=out/'prepared-world';prepared.mkdir()
    excluded={'playerdata','advancements','stats','effortlessbuilding','tombstone'}
    copied=[];omitted=[]
    for p in source.rglob('*'):
        if not p.is_file():continue
        rel=p.relative_to(source)
        if p.is_symlink():raise UserError('Linked world inputs are refused')
        if rel.parts[0] in excluded or p.name in ('session.lock','level.dat_old'):
            omitted.append(rel.as_posix());continue
        dest=prepared/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
        if digest(p)!=digest(dest):raise UserError('A copied fresh-world input differs')
        copied.append({'path':rel.as_posix(),'sha256':digest(dest),'bytes':dest.stat().st_size})
    prepare_level(prepared/'level.dat',CINEMATIC_PACK_ID)
    source_level=next(r for r in copied if r['path']=='level.dat')
    source_level.update(source_sha256=source_level['sha256'],sha256=digest(prepared/'level.dat'),
        bytes=(prepared/'level.dat').stat().st_size,
        transformations=['World display name','Survival default','Embedded player omitted',
            'Retire world-local cinematic pack selections; enable native-verified global Paxi pack',
            'Resume daylight/weather cycles and begin at morning'])
    if any((prepared/n).exists() for n in excluded):raise UserError('Player test state reached the new active save')
    retired=out/'retired-staging-cinematics';retired.mkdir()
    retired_cinematics=retire_world_cinematics(prepared,retired)
    retired_paths={'datapacks/'+name for name in retired_cinematics}
    copied=[r for r in copied if r['path'] not in retired_paths];omitted.extend(sorted(retired_paths))
    cfg=out/'prepared-config';shutil.copytree(stage.server/'config',cfg)
    verify_cinematic_folder(cfg/CINEMATIC_FOLDER,cinematic_files)
    mods=out/'prepared-mods';mods.mkdir()
    installed=read_json(stage.server/'installed.json')
    for name,sha in installed['files'].items():
        f=stage.server/'mods'/name
        if digest(f)!=sha:raise UserError('The reviewed staged server JAR changed')
        os.link(f,mods/name)
    release=target.releases/active['version']
    if release.exists():
        if digest(release/'pack.toml')!=active['pack_sha256']:raise UserError('The immutable release differs')
    else:shutil.copytree(stage.releases/active['version'],release)
    verify_cinematic_folder(release/'config'/CINEMATIC_FOLDER,cinematic_files)
    # All resolved rename targets are exact owned descendants on the same volume.
    for p in (old,prepared,target.server/'mods',mods,target.server/'config',cfg):
        if not p.resolve().is_relative_to(target.home):raise UserError('A final rename escaped the runtime')
    # Retire authority before swapping worlds: a hygiene failure must not put
    # the fresh world next to the rejected world's still-active admissions.
    previous_state=out/'previous-dashboard';previous_state.mkdir()
    dashboard_handoff=retire_world_dashboard(target.state,previous_state,{
        'handoff_id':out.name,'target_world':str(old),'source_stage_world':str(source),
        'candidate':active['version'],'pack_sha256':active['pack_sha256']})
    old.rename(out/'discarded-world');prepared.rename(old)
    (target.server/'mods').rename(out/'previous-server-mods');mods.rename(target.server/'mods')
    (target.server/'config').rename(out/'previous-server-config');cfg.rename(target.server/'config')
    tiles=target.server/'squaremap/web/tiles'
    if tiles.exists():tiles.rename(out/'previous-atlas-tiles')
    write_json(target.state/'cinematics.json',read_json(config))
    write_json(target.state/'cinematic-first-joins.json',{})
    props_path=target.server/'server.properties';props=properties(props_path.read_text(encoding='utf-8'))
    props['level-name']=old.as_posix();props['server-port']=25565
    atomic_write(props_path,format_properties(props))
    write_json(target.server/'installed.json',installed|{'at':utcnow(),'validation':'Exact stopped artistic installation; official startup pending'})
    write_json(target.home/'packwiz/active.json',active|{'at':utcnow(),'publication':'Owner-authorized fresh artistic official world'})
    settings=target.settings();settings.update(permanent_world=True,world_created=True);target.save_settings(settings)
    if verify_installed(target):raise UserError('Final installed inventory differs; preserve all handoff directories')
    receipt.update(status='fresh official save installed; startup pending',world=str(old),
        copied_fresh_files=len(copied),excluded_player_files=omitted,retained_discarded_world=str(out/'discarded-world'),
        cinematic_sha256=cinematic_sha256,cinematic_source_zip_installed_in_world=False,
        cinematic_pack_id=CINEMATIC_PACK_ID,cinematic_config_folder=CINEMATIC_FOLDER.as_posix(),
        cinematic_config_entries=cinematic_files,retired_staging_world_cinematics=retired_cinematics,
        dashboard_handoff=dashboard_handoff,server_mods=len(installed['files']))
    write_json(out/'fresh-source-files.json',copied);write_json(out/'handoff.json',receipt)
    write_json(target.state/'artistic-handoff.json',receipt)
    return receipt
