"""Future private mill-resume request producer; no native command invocation.

All current native proofs are required inputs, not synthesized by this script.
During the owner preview no request is prepared and no world is read/written.
"""
from __future__ import annotations
import argparse
from datetime import datetime,timezone,timedelta
import json
from pathlib import Path
import re
import tomllib
from zipfile import ZipFile
from contract import (COUNT,MANIFEST_SHA,PARTIAL_SHA,GEOMETRY_SHA,composite,digest,
                      encoded,qualify_partial,qualify_preimage,require_resume_stock)

MIB=1024**2

def completed(path):
    path=Path(path);raw=path.read_bytes();marker=Path(str(path)+'.complete')
    if not 0<len(raw)<=512*1024 or marker.stat().st_size>128 or marker.read_text().strip()!=digest(raw):raise ValueError('Immutable actual native terminal plus exact completion marker required')
    return json.loads(raw),marker

def current_proof(proof,plan_sha,*,now=None):
    now=now or datetime.now(timezone.utc)
    if proof.get('operation')!='verify' or proof.get('plan_sha256')!=plan_sha or proof.get('blocks')!=COUNT or proof.get('failures')!=0 or 'error' in proof or proof.get('status')!='verified actual block identities, orientation, block entities and supplied inventories':raise ValueError('Zero-failure native complete current-preimage proof required')
    started=datetime.fromisoformat(proof['started'].replace('Z','+00:00'));finished=datetime.fromisoformat(proof['finished'].replace('Z','+00:00'))
    if not now-timedelta(minutes=20)<=finished<=now or started>finished:raise ValueError('Fresh ordered actual native proof required')

def bind(*,home,sources,manifest,current_plan,native_current,partial,bridge_jar,candidate,bridge_version,mode,native_inspection=None):
    home=Path(home).resolve();world=home/'world/RosewaterArtistic'
    if not home.is_relative_to(Path('D:/A World for Two/staging/world-tests').resolve()) or home.parent==home or mode not in ('inspect','resume') or not re.fullmatch(r'0\.1\.0-candidate\.\d+',candidate) or not re.fullmatch(r'0\.6\.\d+',bridge_version):raise ValueError('Exact private artistic home/version/operation required')
    from tools.playtest import guard
    reserve=guard(0,4*MIB)
    def reference(path,cap=2*MIB):
        p=Path(path).resolve()
        if not p.is_relative_to(home) or not 0<p.stat().st_size<=cap:raise ValueError('Finite immutable home-owned input required')
        return {'path':p.relative_to(home).as_posix(),'bytes':p.stat().st_size,'sha256':digest(p.read_bytes())}
    source_refs=[reference(p) for p in sources]
    source=composite([Path(p).read_bytes() for p in sources]);manifest_ref=reference(manifest)
    if manifest_ref['sha256']!=MANIFEST_SHA:raise ValueError('Original exact systems/inventory provenance required')
    systems=json.loads(Path(manifest).read_bytes())
    if Path(source['world_path']).resolve()!=world.resolve():raise ValueError('Exact actual artistic world custody required')
    checkpoint_path=home/'dashboard/settlement/backup-receipt.json';backup_ref=reference(checkpoint_path,4096);checkpoint=json.loads(checkpoint_path.read_bytes())
    if checkpoint.get('verified') is not True or not re.fullmatch('[a-f0-9]{64}',checkpoint.get('sha256','')):raise ValueError('Current verified stopped-save receipt required')
    current_ref=reference(current_plan);current=json.loads(Path(current_plan).read_bytes())
    if current.get('backup_sha256')!=checkpoint['sha256']:raise ValueError('Exact current checkpoint preimage required')
    witnessed=qualify_preimage(source,current,systems)
    proof,proof_marker=completed(native_current);current_proof(proof,current_ref['sha256'])
    partial_ref=reference(partial,512*1024)
    if partial_ref['sha256']!=PARTIAL_SHA:raise ValueError('Exact preserved original WAIT_MODE failure required')
    partial_doc,partial_marker=completed(partial);qualify_partial(partial_doc)
    archive=Path(bridge_jar)
    if not 0<archive.stat().st_size<=4*MIB:raise ValueError('Bounded built native bridge required')
    with ZipFile(archive) as jar:
        classes={}
        for name in ('ArtisticEngineeringSupport','NativeMillResumeAttachments'):
            member='worldfortwo/bridge/'+name+'.class'
            if jar.getinfo(member).file_size>256*1024:raise ValueError('Bounded actual helper class required')
            classes[name]=digest(jar.read(member))
        info=tomllib.loads(jar.read('META-INF/neoforge.mods.toml').decode())
        if not any(row.get('modId')=='awft_control_bridge' and row.get('version')==bridge_version for row in info.get('mods',[])):raise ValueError('Actual built bridge version differs')
    configs=[]
    for name in ('overpressure-common.toml','create_hypertube-server.toml','create-server.toml'):
        value=reference(home/'server/config'/name,MIB)
        if not any(row.get('file')==name and row.get('sha256')==value['sha256'] for row in systems['sources']):raise ValueError('Pinned actual native policy changed')
        configs.append(value)
    inspection_ref=inspection_marker_ref=None
    if mode=='resume':
        if native_inspection is None:raise ValueError('A separate fresh actual native inventory inspection is mandatory')
        inspected,marker=completed(native_inspection);require_resume_stock(inspected)
        finished=datetime.fromisoformat(inspected['finished'].replace('Z','+00:00'));now=datetime.now(timezone.utc)
        if not now-timedelta(minutes=20)<=finished<=now or datetime.fromisoformat(inspected['started'].replace('Z','+00:00'))<datetime.fromisoformat(proof['finished'].replace('Z','+00:00')) or inspected.get('candidate')!=candidate or inspected.get('bridge')!=bridge_version or inspected.get('native_class_sha256')!=classes['ArtisticEngineeringSupport'] or inspected.get('native_attachment_class_sha256')!=classes['NativeMillResumeAttachments'] or inspected.get('native_after_plan_sha256')!=current_ref['sha256'] or inspected.get('current_backup_sha256')!=checkpoint['sha256'] or inspected.get('source_geometry_sha256')!=GEOMETRY_SHA:raise ValueError('Inventory inspection is stale or belongs to different actual artifacts/checkpoint/preimage')
        inspection_ref,inspection_marker_ref=reference(native_inspection,512*1024),reference(marker,128)
    elif native_inspection is not None:raise ValueError('Inspection request must not smuggle a resume operation')
    # Stop here on every failed gate. No failed proof causes a directory/request.
    source['backup_sha256']=checkpoint['sha256'];raw_source=encoded(source)
    if len(raw_source)>2*MIB:raise ValueError('Bounded complete source composite required')
    attempt=digest(raw_source+mode.encode()+reference(native_current,512*1024)['sha256'].encode()+(inspection_ref['sha256'].encode() if inspection_ref else b''))
    output=home/'staging'/('mill-resume-source-'+attempt[:16])
    if output.exists():raise ValueError('Retain previous attempt; use a new exact checkpoint/preimage after review')
    output.mkdir();source_path=output/'source-VERIFY-ONLY.json';source_path.write_bytes(raw_source)
    request={'format':'awft-artistic-mill-resume:1','intended_operation':mode,'candidate_version':candidate,'bridge_version':bridge_version,
             'native_class_sha256':classes['ArtisticEngineeringSupport'],'native_attachment_class_sha256':classes['NativeMillResumeAttachments'],'bridge_jar_sha256':digest(archive.read_bytes()),
             'manifest':manifest_ref,'plan':reference(source_path),'source_plans':source_refs,'current_backup':backup_ref,
             'native_after_plan':current_ref,'native_after':reference(native_current,512*1024),'native_after_complete':reference(proof_marker,128),
             'native_partial':partial_ref,'native_partial_complete':reference(partial_marker,128),'configuration':configs,'storage_guard':reserve,
             'authority':'Resume-only actual retained native links/water; two real stocked WEST detectors; no replay of placement, initialization or connection; native operation NOT invoked'}
    if inspection_ref:request.update(native_inventory_inspection=inspection_ref,native_inventory_inspection_complete=inspection_marker_ref)
    raw=encoded(request)
    if len(raw)>128*1024:raise ValueError('Finite request exceeded; retained source proposal only')
    name='mill-resume-'+digest(raw)[:16];destination=home/'dashboard/settlement'/name
    destination.mkdir();(destination/'request.json').write_bytes(raw)
    return {'bundle_name':name,'request_sha256':digest(raw),'request':str(destination/'request.json'),'source_witness':witnessed,'native_operation':'NOT INVOKED'}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('home','manifest','current-plan','native-current','partial','bridge-jar'):p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--sources',type=Path,nargs=3,required=True);p.add_argument('--candidate',required=True);p.add_argument('--bridge-version',required=True)
    p.add_argument('--mode',choices=('inspect','resume'),required=True);p.add_argument('--native-inspection',type=Path)
    print(json.dumps(bind(**vars(p.parse_args())),indent=2))
