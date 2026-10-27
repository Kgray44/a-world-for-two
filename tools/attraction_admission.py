"""Bind a future native hub admission to immutable build and placement evidence.

No native command, Java launch, world reader or installer is present. The future
bridge build/placement receipts must exist first; this never manufactures them.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import zipfile
from datetime import datetime
from pathlib import Path

from control_room.common import Layout, REPO, UserError, atomic_write, contained, digest, read_json, utcnow
from control_room.storage import Storage


MAX_OUTPUT=2*1024**2
MAX_JSON=4*1024**2
NATIVE_SOURCE=REPO/'compat/control-bridge/src/worldfortwo/bridge/AttractionSupport.java'
AUTHORING_SOURCE=REPO/'tools/settlement_attractions.py'
CLASS_FILE='worldfortwo/bridge/AttractionSupport.class'
VERIFIED_STATUS='verified actual block identities, orientation, block entities and supplied inventories'


def checked_json(path,limit=MAX_JSON):
    path=Path(path)
    if path.is_symlink() or path.is_junction() or not path.is_file() or not 0<path.stat().st_size<=limit:
        raise UserError('Missing, linked or oversized admission evidence: '+path.name)
    value=read_json(path)
    if not isinstance(value,dict):raise UserError('Admission evidence must be a JSON object')
    return value


def reference(home,path,expected=None,limit=32*1024**2):
    path=Path(path).absolute();home=Path(home).resolve()
    try:relative=path.relative_to(home).as_posix()
    except ValueError as exc:raise UserError('Admission inputs must remain inside the owned runtime') from exc
    # Inspect the lexical path before resolving away links or Windows junctions.
    path=contained(home,relative)
    if not path.is_file() or not 0<path.stat().st_size<=limit:
        raise UserError('Missing, linked or oversized owned admission input')
    sha=digest(path)
    if expected is not None and sha!=expected:raise UserError('Exact admission input digest differs: '+path.name)
    return {'path':relative,'sha256':sha,'bytes':path.stat().st_size}


def native_receipt(home,path,plan_sha,count):
    ref=reference(home,path,limit=512*1024);row=checked_json(path,512*1024)
    complete=Path(str(path)+'.complete')
    if complete.is_symlink() or not complete.is_file() or complete.stat().st_size>128 or complete.read_text().strip()!=ref['sha256']:
        raise UserError('An immutable native terminal receipt and exact completion marker are required')
    if (row.get('operation')!='verify' or row.get('plan_sha256')!=plan_sha or
        type(row.get('blocks')) is not int or row['blocks']!=count or
        type(row.get('failures')) is not int or row['failures']!=0 or
        row.get('status')!=VERIFIED_STATUS or not row.get('finished') or row.get('error')):
        raise UserError('The exact native placement/custody verification has not passed')
    try:
        started=datetime.fromisoformat(row['started']);finished=datetime.fromisoformat(row['finished'])
        if started.tzinfo is None or finished.tzinfo is None or finished<started:raise ValueError('unordered native receipt')
    except (KeyError,TypeError,ValueError) as exc:raise UserError('Native receipt must carry an ordered UTC execution interval') from exc
    return {'receipt':ref,'complete':reference(home,complete,limit=128)}


def source_path(directory,row,budget):
    name=row.get('file','')
    if Path(name).name!=name or not re.fullmatch(r'[A-Za-z0-9_.-]+\.json',name):
        raise UserError('Unsafe geometry source name')
    candidates=[directory/name]
    # The five original detail source files are retained one level below the
    # settlement directory. This scan is finite and never follows linked dirs.
    children=list(directory.iterdir())
    if len(children)>4096:raise UserError('The owned evidence directory exceeds its bounded scan')
    candidates.extend(child/name for child in children if child.is_dir() and not child.is_symlink() and not child.is_junction())
    candidates=[p for p in candidates if p.is_file() and not p.is_symlink() and not p.is_junction()]
    if len(candidates)>32:raise UserError('Too many ambiguous geometry source candidates')
    matches=[]
    for path in candidates:
        size=path.stat().st_size
        budget[0]+=size
        if not 0<size<=32*1024**2 or budget[0]>128*1024**2:
            raise UserError('Completed geometry exceeds its bounded read budget')
        if digest(path)==row.get('sha256'):matches.append(path)
    if not matches:raise UserError('Missing exact completed geometry: '+name)
    return sorted(matches,key=lambda p:str(p))[0]


def build_envelope(home,hub_manifest,build_receipt,before_receipt,after_receipt):
    """Pure bounded-input authoring; callers separately guard actual output writes."""
    layout=Layout(Path(home));directory=layout.state/'settlement'
    m=checked_json(hub_manifest)
    if (m.get('format')!='awft-settlement-attractions:1' or type(m.get('placements')) is not int or
        not 1<=m['placements']<=45000):
        raise UserError('Use the exact bounded hub manifest')
    manifest_ref=reference(layout.home,hub_manifest,limit=MAX_JSON)
    for key in ('plan_file','preconditions_file'):
        if not isinstance(m.get(key),str) or not re.fullmatch(r'[A-Za-z0-9_.-]+\.json',m[key]):
            raise UserError('Use a simple owned hub plan filename')
    plan_path=Path(hub_manifest).parent/m['plan_file'];before_path=Path(hub_manifest).parent/m['preconditions_file']
    if plan_path.parent!=Path(hub_manifest).parent or before_path.parent!=Path(hub_manifest).parent:
        raise UserError('Hub plan escaped its immutable bundle')
    plan=checked_json(plan_path);before=checked_json(before_path)
    if (plan.get('format')!='awft-native-settlement:1' or before.get('format')!='awft-native-settlement:1' or
        plan.get('commands')!=[] or before.get('commands')!=[] or before.get('block_entities')!=[]):
        raise UserError('Admission never accepts entity commands or BE writes in a prior-state check')
    def states(doc):
        rows,palette=doc.get('blocks'),doc.get('palette')
        if (not isinstance(rows,list) or not 1<=len(rows)<=45000 or not isinstance(palette,list) or
            not 1<=len(palette)<=8192 or any(not isinstance(v,str) or not 1<=len(v)<=1024 for v in palette)):
            raise UserError('Unbounded hub block document')
        result={}
        for row in rows:
            if (not isinstance(row,list) or len(row)!=4 or any(type(v) is not int for v in row) or
                not 0<=row[3]<len(palette) or not 1292<=row[0]<=1320 or not 56<=row[1]<=88 or
                not -1030<=row[2]<=-904):raise UserError('Invalid exact hub block row')
            pos=tuple(row[:3])
            if pos in result:raise UserError('Duplicate hub targets')
            result[pos]=palette[row[3]]
        return result
    targets,previous=states(plan),states(before)
    audit={}
    for row in m.get('expected_previous',[]):
        pos=row.get('position')
        if not isinstance(pos,list) or len(pos)!=3 or any(type(v) is not int for v in pos) or tuple(pos) in audit:
            raise UserError('Duplicate or invalid previous-state audit position')
        audit[tuple(pos)]=row
    if set(targets)!=set(previous) or set(audit)!=set(targets) or len(targets)!=m['placements']:
        raise UserError('Every exact hub target needs its original before-state custody')
    for pos,state in targets.items():
        if audit[pos]['previous']!=previous[pos] or audit[pos]['replacement']!=state:
            raise UserError('The hub previous-state manifest differs')
    for key in ('seed','world_path','backup_sha256'):
        if plan.get(key)!=before.get(key):raise UserError('The hub documents belong to different worlds/backups')
    backup=checked_json(directory/'backup-receipt.json')
    if (backup.get('verified') is not True or backup.get('sha256')!=plan['backup_sha256'] or backup.get('id')!=m.get('backup_id') or
        not re.fullmatch(r'[A-Za-z0-9_-]{1,80}',backup.get('id',''))):
        raise UserError('Reprepare the uninstalled hub against the current verified backup')
    active=checked_json(layout.home/'packwiz/active.json');installed=checked_json(layout.server/'installed.json')
    build=checked_json(build_receipt,256*1024)
    if (build.get('format')!='awft-attraction-native-build:1' or
        build.get('candidate_version')!=active.get('version') or
        build.get('pack_sha256')!=active.get('pack_sha256') or
        installed.get('pack_version')!=active.get('version') or installed.get('pack_sha256')!=active.get('pack_sha256') or
        not isinstance(build.get('candidate_version'),str) or not re.fullmatch(r'[A-Za-z0-9_.+-]{1,100}',build['candidate_version']) or
        not isinstance(build.get('bridge_version'),str) or not build['bridge_version'] or
        not re.fullmatch(r'[a-f0-9]{64}',build.get('pack_sha256',''))):
        raise UserError('The actual future candidate/build/installed pack identities differ')
    if build.get('native_source_sha256')!=digest(NATIVE_SOURCE) or m.get('source_sha256')!=digest(AUTHORING_SOURCE):
        raise UserError('The exact native or frozen authoring source changed')
    bridge=contained(layout.home,build['bridge_jar_file'])
    if bridge.parent!=layout.server/'mods' or bridge.name not in installed.get('files',[]):
        raise UserError('The future native bridge must be an actual installed mod')
    bridge_ref=reference(layout.home,bridge,build.get('bridge_jar_sha256'))
    with zipfile.ZipFile(bridge) as archive:
        if archive.getinfo(CLASS_FILE).file_size>256*1024:raise UserError('Native admission class exceeds its bound')
        class_sha=hashlib.sha256(archive.read(CLASS_FILE)).hexdigest()
    if class_sha!=build.get('attraction_class_sha256'):
        raise UserError('The actual installed native admission class differs')
    geometry=[];geometry_budget=[0]
    for row in m.get('provenance',[]):
        if row.get('native_verification') or row.get('role')=='Completed detail exclusion':
            path=source_path(directory,row,geometry_budget)
            geometry.append(reference(layout.home,path,row['sha256']))
            completed=checked_json(path,32*1024**2)
            rows=completed.get('blocks',[])
            if not isinstance(rows,list) or not 1<=len(rows)<=550000:
                raise UserError('Invalid bounded completed geometry')
            for block in rows:
                if not isinstance(block,list) or len(block)!=4 or any(type(v) is not int for v in block):
                    raise UserError('Malformed completed geometry row')
                if tuple(block[:3]) in targets:raise UserError('Hub intersects completed fixed geometry, including authored air')
    if len(geometry)!=15 or len({v['sha256'] for v in geometry})!=15:
        raise UserError('All ten completed masters and five detail deltas must remain fixed')
    mods=[]
    for row in m.get('provenance',[]):
        if row.get('role')=='Read-only pinned native API/recipe evidence':
            mods.append(reference(layout.home,layout.server/'mods'/row['file'],row['sha256']))
    if len(mods)!=4 or len({r['path'] for r in mods})!=4:
        raise UserError('All four exact native attraction mod dependencies are required')
    sources={'authoring_source.py':AUTHORING_SOURCE.read_bytes(),'AttractionSupport.java':NATIVE_SOURCE.read_bytes()}
    if any(len(raw)>256*1024 for raw in sources.values()):raise UserError('An admission source copy exceeds its bound')
    before_proof=native_receipt(layout.home,before_receipt,m['preconditions_sha256'],len(previous))
    after_proof=native_receipt(layout.home,after_receipt,m['plan_sha256'],len(targets))
    if datetime.fromisoformat(checked_json(before_receipt)['finished'])>datetime.fromisoformat(checked_json(after_receipt)['started']):
        raise UserError('Native before-state verification must precede the completed after-state check')
    envelope={'format':'awft-attraction-admission:1','at':utcnow(),
        'candidate_version':build['candidate_version'],'bridge_version':build['bridge_version'],
        'pack_sha256':active['pack_sha256'],'native_class_sha256':class_sha,
        'hub_manifest':manifest_ref,
        'plan':reference(layout.home,plan_path,m['plan_sha256'],MAX_JSON),
        'preconditions':reference(layout.home,before_path,m['preconditions_sha256'],MAX_JSON),
        'backup_receipt':reference(layout.home,directory/'backup-receipt.json',limit=4096),
        'backup_archive':reference(layout.home,layout.backups/(backup['id']+'.zip'),backup['sha256'],256*1024**2),
        'active_receipt':reference(layout.home,layout.home/'packwiz/active.json',limit=65536),
        'installed_receipt':reference(layout.home,layout.server/'installed.json',limit=1024**2),
        'build_receipt':reference(layout.home,build_receipt,limit=256*1024),'bridge_jar':bridge_ref,
        'geometry':geometry,'native_mods':mods,
        'before_verification':before_proof,'after_verification':after_proof,
        'source_copies':{name:{'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)} for name,raw in sources.items()},
        'permitted_actions':['inspect','admit'],
        'unsupported_actions':['setup','assemble','connect','commission','run'],
        'scope':'Native read-only inspection/admission candidate only; no source or synthetic check proves native execution'}
    return envelope,sources


def prepare(home,hub_manifest,build_receipt,before_receipt,after_receipt):
    layout=Layout(Path(home));value,sources=build_envelope(home,hub_manifest,build_receipt,before_receipt,after_receipt)
    raw=(json.dumps(value,separators=(',',':'),ensure_ascii=False)+'\n').encode()
    sha=hashlib.sha256(raw).hexdigest();output=layout.state/'settlement'/('attraction-admission-'+sha[:16])
    if output.exists():raise UserError('Preserve the previous exact admission bundle')
    if len(raw)+sum(map(len,sources.values()))>MAX_OUTPUT:raise UserError('Admission bundle exceeds its guarded output cap')
    Storage(layout).reserve(MAX_OUTPUT,target=output);output.mkdir(parents=True)
    for name,data in {**sources,'admission.json':raw}.items():atomic_write(output/name,data)
    return {'directory':str(output),'bundle':output.name,'admission_sha256':sha,'native_action':'Not performed'}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ('home','hub_manifest','build_receipt','before_receipt','after_receipt'):
        parser.add_argument('--'+key.replace('_','-'),type=Path,required=True)
    args=parser.parse_args();print(json.dumps(prepare(**vars(args)),indent=2))
