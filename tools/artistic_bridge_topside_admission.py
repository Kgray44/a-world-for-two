"""Admit original106 non-BE ornaments only after current real retained-glue inspection.

Private artifact writer. No command, world/entity/control/glue/setup action.
Old proposals stay forbidden; current marked proofs and actual installed class
bytes are required. A receipt never creates its own placement/motion authority.
"""
from __future__ import annotations
import argparse
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib,json,math,re,tomllib,zipfile
from pathlib import Path

from control_room.common import UserError,digest,utcnow
from tools.artistic_bridge_refinement import flatten
from tools.artistic_bridge_topside_custody import BOXES,enclosed,exact_glues
from tools.artistic_bridge_topside_inspection import CLASS,current_pack,owned_regular
from tools.artistic_bridge_topside_ornament import moving_owner
from tools.artistic_materials import require_material_rule,require_outdoor_rule
from tools.artistic_quay_prototype import TOPSIDE,TOPSIDE_SHA,bounded,context,fresh_proof,member,same_world,write_bundle
from tools.artistic_spawn_plaza import payload
from tools.playtest import guard
from tools.settlement_attractions import BackupWorld

MIB=1024**2
NORTH='509a0105c6b8ee45ed972ae1ff066d8f78649662abc77a383dd5820b0470e3a7'
SOUTH='c7c9a705b7c4e15b51a71e0420108c704cd091103263a8aa0b739bc238b6eba0'


def instant(text):
    try:value=datetime.fromisoformat(text.replace('Z','+00:00'))
    except (AttributeError,TypeError,ValueError)as error:raise UserError('Real native timezone-qualified timestamp required')from error
    if value.tzinfo is None:raise UserError('Native timestamp needs a timezone')
    return value


def check_inspection(proof,request,request_sha,census,checkpoint,before_finished,*,now=None):
    now=now or datetime.now(timezone.utc)
    if (proof.get('operation')!='inspect-retained-current-glue' or proof.get('native_custody_passed')is not True
            or proof.get('new_glue_or_motion_authority')is not False
            or proof.get('no_native_geometry_entity_inventory_glue_control_writes')is not True
            or proof.get('request_sha256')!=request_sha or proof.get('candidate')!=request.get('candidate')
            or proof.get('bridge')!=request.get('bridge')or proof.get('checkpoint_id')!=checkpoint['id']
            or proof.get('checkpoint_sha256')!=checkpoint['sha256']or type(proof.get('strict_preimage_states'))is not int
            or proof['strict_preimage_states']!=106):
        raise UserError('Actual current exact106 retained-glue INSPECT success required')
    if (proof.get('cleanup_required')is not False or proof.get('ticket_release_failures')!=[]
            or any(key in proof for key in ('error','journal_error','lease_cleanup_error'))or proof.get('receipt_blocked',False)is not False):
        raise UserError('Retain failed inspection/publication/cleanup; no admission')
    for key in ('temporary_tickets_remaining','pending_shared_chunk_futures'):
        if type(proof.get(key))is not int or proof[key]!=0:raise UserError('All actual owned resource handles must be clean')
    if 'failures'in proof and proof['failures']!=0:raise UserError('A native failure remains')
    start,end=instant(proof.get('started')),instant(proof.get('finished'))
    if instant(before_finished)>start or start>end or end>now or now-end>timedelta(seconds=300):
        raise UserError('Fresh ordered BEFORE then actual INSPECT receipt required')
    expected={r['uuid']:r for r in census['glues']};exact_glues(census['glues'])
    observed=proof.get('glues')
    if not isinstance(observed,list)or len(observed)!=2 or {r.get('uuid')for r in observed}!=set(expected):
        raise UserError('Exactly the actual saved two glue identities must remain resolved')
    for row in observed:
        saved=expected[row['uuid']]
        if(row.get('native_class')!='com.simibubi.create.content.contraptions.glue.SuperGlueEntity'
                or row.get('bounds')!=saved['bounds']or row.get('canonical_nbt')!=saved['canonical_nbt']
                or row.get('canonical_nbt_sha256')!=saved['canonical_nbt_sha256']):
            raise UserError('Exact current native class/AABB/complete typed NBT custody changed')
    loaded=proof.get('loaded_glue_uuids')
    if not isinstance(loaded,list)or len(loaded)!=2 or set(loaded)!=set(expected):raise UserError('Unknown/extra/unresolved loaded glue')
    for label in ('closed_before','closed_after'):
        rows=proof.get(label)
        if not isinstance(rows,list)or len(rows)!=2 or {tuple(r.get('bearing',[]))for r in rows}!={(1199,70,-1172),(1199,70,-1116)}:
            raise UserError('Both real before/after closed bridge witnesses required')
        for row in rows:
            angle=row.get('angle');speed=row.get('input_rpm');wheel=row.get('wheel_rpm')
            if (type(angle)not in(int,float)or not math.isfinite(angle)or abs((angle+180)%360-180)>.75
                    or row.get('running')is not False or row.get('sequencer_idle')is not True
                    or any(type(v)not in(int,float)or not math.isfinite(v)or v==0 for v in (speed,wheel))):
                raise UserError('Actual closed idle initialized native bridge must remain ready')
    return proof


def checked_reference(home,ref,limit):
    if not isinstance(ref,dict)or set(ref)!= {'path','bytes','sha256'}:raise UserError('Exact immutable file reference required')
    relative=Path(ref['path'])
    if relative.is_absolute()or '\\'in ref['path']or ':'in ref['path']or any(p in('.', '..')for p in relative.parts):
        raise UserError('No foreign or traversing evidence paths')
    path=owned_regular(home,home/relative,limit)
    if path.stat().st_size!=ref['bytes']or digest(path)!=ref['sha256']:raise UserError('Actual referenced bytes/hash changed')
    return path


def bind(home,study,study_sha,native_before,inspection_request,inspection_receipt,output):
    reserve=guard(4*MIB,16*MIB)
    home,output,current,registry=context(home,output)
    study=Path(study).absolute()
    if study.parent!=home/'staging':raise UserError('Current private study must be immediate staging child')
    sm=bounded(owned_regular(home,study/'manifest.json',MIB))
    if digest(study/'manifest.json')!=study_sha or sm.get('format')!='awft-retained-glue-next-proof:1' or(sm['checkpoint_id'],sm['checkpoint_sha256'])!=(current['id'],current['sha256']):
        raise UserError('Fresh exact current saved106/census study required; historical e55 cannot be silently rebound')
    census=member(study,sm,'current-saved-glue-census-READONLY.json');before=member(study,sm,'moving106-before-VERIFY-ONLY.json')
    same_world(census,registry);same_world(before,registry);exact_glues(census['glues'])
    native_before=owned_regular(home,Path(native_before).absolute(),256*1024)
    if native_before.parent!=home/'dashboard/settlement':raise UserError('Actual owned native BEFORE journal required')
    before_proof,before_marker=fresh_proof(native_before,digest(study/'moving106-before-VERIFY-ONLY.json'),106)
    rp=owned_regular(home,Path(inspection_request).absolute(),128*1024);request=bounded(rp,128*1024);request_sha=digest(rp)
    if rp.name!='request.json'or rp.parent.parent!=home/'dashboard/settlement'or rp.parent.name!='bridge-topside-inspection-'+request_sha[:16]:
        raise UserError('Exact original immutable typed inspection request required')
    if request.get('format')!='awft-retained-bridge-inspection:1':raise UserError('Exact retained native request format required')
    release,pack_sha=current_pack(home,request.get('candidate'))
    if request.get('pack_sha256')!=pack_sha or not re.fullmatch(r'\d+\.\d+\.\d+',request.get('bridge','')):
        raise UserError('Actual new candidate/bridge/release pins required')
    refs={k:checked_reference(home,request[k],256*1024)for k in ('checkpoint','census','preimage','native_before','native_before_complete','north_original','south_original')}
    expected_paths={'checkpoint':home/'dashboard/settlement/backup-receipt.json','census':study/'current-saved-glue-census-READONLY.json',
        'preimage':study/'moving106-before-VERIFY-ONLY.json','native_before':native_before,'native_before_complete':before_marker}
    if any(refs[k]!=v for k,v in expected_paths.items()):raise UserError('Request differs from current exact native study/proof')
    jar=owned_regular(home,home/'server/mods'/('awft-control-bridge-'+request['bridge']+'.jar'),32*MIB)
    installed=bounded(home/'server/installed.json',2*MIB)
    if installed.get('files',{}).get(jar.name)!=digest(jar):raise UserError('Actual installed bridge archive pin differs')
    with zipfile.ZipFile(jar)as archive:
        info=archive.getinfo(CLASS)
        if not 0<info.file_size<=128*1024:raise UserError('Finite actual retained helper class required')
        code=archive.read(info);actual_class_sha=hashlib.sha256(code).hexdigest()
        if actual_class_sha!=request.get('native_class_sha256')or b'packwiz/releases/'not in code:
            raise UserError('Actual new versioned-release helper class required, never the old flat-path R2 class')
        descriptor=archive.getinfo('META-INF/neoforge.mods.toml')
        if not 0<descriptor.file_size<=65536:raise UserError('Finite actual bridge descriptor required')
        meta=tomllib.loads(archive.read(descriptor).decode('utf8'))
        if not any(m.get('modId')=='awft_control_bridge'and m.get('version')==request['bridge']for m in meta.get('mods',[])):
            raise UserError('Actual bridge descriptor/request mismatch')
    ip=owned_regular(home,Path(inspection_receipt).absolute(),256*1024)
    if ip.parent!=home/'dashboard/settlement'or not re.fullmatch(r'bridge-topside-inspection-result-[a-f0-9-]{36}\.json',ip.name):
        raise UserError('Actual native immutable retained-inspection journal required')
    marker=owned_regular(home,ip.with_name(ip.name+'.complete'),128)
    if marker.read_text(encoding='ascii').strip()!=digest(ip):raise UserError('Native immutable inspection completion digest differs')
    proof=bounded(ip,256*1024);check_inspection(proof,request,request_sha,census,current,before_proof['finished'])
    source_dir=home/TOPSIDE;original=bounded(source_dir/'manifest.json')
    if digest(source_dir/'manifest.json')!=TOPSIDE_SHA:raise UserError('Original immutable ornament10055 authority changed')
    changes={}
    for label,expected_sha,key in (('north',NORTH,'north_original'),('south',SOUTH,'south_original')):
        path=source_dir/(label+'-ornament-PROPOSAL.json');plan=member(source_dir,original,path.name);same_world(plan,registry)
        if digest(path)!=expected_sha or refs[key]!=path or plan.get('commands')!=[] or plan.get('block_entities')!=[]:
            raise UserError('Only original command-free53+53 nonBE geometry is admitted')
        cells=flatten(plan)
        if len(cells)!=53 or set(changes)&set(cells)or any(moving_owner(q)!=label or not enclosed(q,BOXES[label])for q in cells):
            raise UserError('Every exact original voxel must remain inside its existing owned glue AABB')
        changes.update(cells)
    if set(changes)!=set(flatten(before))or len(changes)!=106:raise UserError('Exact current106 BEFORE target set required')
    future=member(source_dir,original,'complete-future-VERIFY-ONLY.json');same_world(future,registry)
    positions=set(flatten(future))
    if not set(changes)<=positions or len(positions)>30000:raise UserError('Finite original complete bridge field required')
    snapshot=BackupWorld(home,current,registry)
    try:
        actual={q:snapshot.state(q)for q in sorted(positions)}
        if any(actual[q]!=v for q,v in flatten(before).items())or set(changes)&snapshot.protected:
            raise UserError('Current stopped106 preimage/BE differs; preserve all')
        full=dict(actual);full.update(changes);saved_sources=deepcopy(snapshot.sources)
    finally:snapshot.close()
    checks={'material':require_material_rule(full,'Complete actual bridge plus original106 ornaments'),
            'outdoor':require_outdoor_rule(full,'Complete bridge authored surfaces with original106')}
    fresh_proof(native_before,digest(study/'moving106-before-VERIFY-ONLY.json'),106)
    check_inspection(proof,request,request_sha,census,current,before_proof['finished'])
    if bounded(home/'dashboard/settlement/backup-receipt.json').get('sha256')!=current['sha256']:
        raise UserError('Current checkpoint changed before admission publication')
    admitted=payload(registry,current['sha256'],changes,'ADMITTED ONCE original106 after actual current retained-glue custody')
    settle=deepcopy(admitted);settle.update(name='NORMAL SETTLE ONLY exact admitted106 current blocks',verification_only=True,construction_forbidden=True)
    after=payload(registry,current['sha256'],full,'PROSPECTIVE VERIFY ONLY current complete bridge plus106; native joins/cycles pending',before=True)
    return write_bundle(output,{'moving106-PLACE-ONCE.json':admitted,'moving106-NORMAL-SETTLE-ONLY.json':settle,'complete-after-VERIFY-ONLY.json':after},
        {'format':'awft-admitted-original-moving106-retained-glue:1','created':utcnow(),'source_sha256':digest(Path(__file__)),
         'checkpoint_id':current['id'],'checkpoint_sha256':current['sha256'],'study_sha256':study_sha,'original_manifest_sha256':TOPSIDE_SHA,
         'actual_candidate':request['candidate'],'actual_bridge':request['bridge'],'actual_native_class_sha256':actual_class_sha,
         'actual_bridge_jar_sha256':digest(jar),'actual_pack_sha256':pack_sha,'actual_pack_manifest_relative':release.relative_to(home).as_posix(),
         'inspection_request_sha256':request_sha,'inspection_receipt_sha256':digest(ip),'inspection_marker_sha256':digest(marker),
         'native_before_sha256':digest(native_before),'native_before_marker_sha256':digest(before_marker),'glue_uuids':[r['uuid']for r in census['glues']],
         'targets':106,'complete_after_cells':len(full),'saved_sources':saved_sources,'checks':checks,'all_existing_BE_inventory_control_states_retained':True,
         'new_glue_retirement_setup_entity_or_NBT_actions':0,'native_actions':0,'world_writes':0,'storage_guard':reserve,
         'requires_root_empty_serialized_window_through_placement':True,'native_shape_motion_restart_or_art_acceptance':False,
         'next_gate':'Root stays empty/serialized: PLACE ONCE106, normal joins/full current native verify; retain/review any derived state differences; COMMISSION ONLY two signed55-degree bank-button cycles. Then actual closed census, normal save/restart/current UUID proof. No setup/retire/reglue or old UUID/NBT replay.'})


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('home','study','native-before','inspection-request','inspection-receipt','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--study-sha',required=True);a=p.parse_args()
    print(json.dumps(bind(a.home,a.study,a.study_sha,a.native_before,a.inspection_request,a.inspection_receipt,a.output),indent=2))
