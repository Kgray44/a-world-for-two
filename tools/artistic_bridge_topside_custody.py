"""Exact retained-glue evidence for the new moving topside, NOT an admission.

No entities are retired, created or changed. The existing two glue volumes fit
all106 new cells. Fresh real native custody/readiness remains a separate gate.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

from control_room.common import UserError,digest,utcnow
from tools.artistic_bridge_admission import saved_glue
from tools.artistic_bridge_refinement import flatten,saved_closed_bearings
from tools.artistic_spawn_plaza import payload
from tools.artistic_bridge_topside_ornament import moving_owner
from tools.artistic_quay_prototype import TOPSIDE,TOPSIDE_SHA,bounded,context,exact_preimage,member,write_bundle
from tools.playtest import guard
from tools.settlement_attractions import BackupWorld

MIB=1024**2
BOXES={'north':(1187.,69.,-1172.,1199.,74.,-1143.),
       'south':(1187.,69.,-1143.,1199.,74.,-1115.)}


def exact_glues(rows):
    if len(rows)!=2 or len({r['uuid'] for r in rows})!=2:
        raise UserError('Retain-only study requires exactly two distinct saved authored glues')
    result={}
    for label,box in BOXES.items():
        found=[r for r in rows if tuple(r.get('bounds',()))==box and r.get('entity_id')=='create:super_glue']
        if len(found)!=1:
            raise UserError('Actual current saved glue box differs; do not create or retire anything')
        result[label]=found[0]
    return result


def enclosed(pos,box):
    return all(box[i]<=pos[i] and pos[i]+1<=box[i+3] for i in range(3))


def prepare(home,output):
    reserve=guard(2*MIB,8*MIB)
    home,output,current,registry=context(home,output)
    source_dir=home/TOPSIDE;manifest=bounded(source_dir/'manifest.json')
    if digest(source_dir/'manifest.json')!=TOPSIDE_SHA:
        raise UserError('Frozen original topside source required')
    glues,entity_sources=saved_glue(home,registry,current['id'],current['sha256'])
    owned=exact_glues(glues);old=flatten(member(source_dir,manifest,'before.json'))
    moving={};source_refs=[]
    for label in ('north','south'):
        path=source_dir/(label+'-ornament-PROPOSAL.json')
        plan=member(source_dir,manifest,path.name)
        targets=flatten(plan)
        if len(targets)!=53 or any(moving_owner(q)!=label or not enclosed(q,BOXES[label]) for q in targets):
            raise UserError('Every exact new moving cell must fit its existing glue AABB')
        moving.update({q:old[q] for q in targets})
        source_refs.append({'relative':path.relative_to(home).as_posix(),'sha256':digest(path),'targets':len(targets),'existing_glue_uuid':owned[label]['uuid']})
    snapshot=BackupWorld(home,current,registry)
    try:
        before=exact_preimage(snapshot,moving);closed=saved_closed_bearings(snapshot);sources=snapshot.sources.copy()
    finally:snapshot.close()
    if bounded(home/'dashboard/settlement/backup-receipt.json').get('sha256')!=current['sha256']:
        raise UserError('Checkpoint changed during exact retained-glue read')
    evidence={'format':'awft-retained-glue-saved-census:1','created':utcnow(),'checkpoint_id':current['id'],'checkpoint_sha256':current['sha256'],
              'seed':registry['seed'],'world_path':registry['world_path'],'glues':[dict(owned[k],leaf=k) for k in ('north','south')],
              'saved_closed_bearings':closed,'entity_region_sources':entity_sources,'block_sources':sources,
              'original_moving_plans':source_refs,'new_cells_outside_existing_glue_bounds':0,
              'source_only':True,'construction_forbidden':True,'native_custody_or_motion_acceptance':False,
              'new_glue_created':0,'existing_glue_retired':0,'world_actions':0}
    docs={'current-saved-glue-census-READONLY.json':evidence,
          'moving106-before-VERIFY-ONLY.json':payload(registry,current['sha256'],before,'VERIFY ONLY current106 moving topside preimage',before=True)}
    docs['moving106-before-VERIFY-ONLY.json'].update(verification_only=True,construction_forbidden=True)
    return write_bundle(output,docs,{'format':'awft-retained-glue-next-proof:1','created':utcnow(),'source_sha256':digest(Path(__file__)),
        'checkpoint_id':current['id'],'checkpoint_sha256':current['sha256'],'original_manifest_sha256':TOPSIDE_SHA,'targets':len(before),
        'native_actions':0,'world_writes':0,'construction_forbidden':True,'existing_glue_boxes_unchanged':True,'storage_guard':reserve,
        'next_native_actions':[
            'Parent serializes an empty-world maintenance lease; require current checkpoint/class/pack/world and exact saved census hashes, all reviewed bridge chunks FULL/entity-loaded/ticking.',
            'Read actual bearings and sequencers: both closed/disassembled Angle0/Runningfalse, no attached/moving contraption, both actual sequencers idle, no button held, speed/stress/radio readiness concrete.',
            'READ ONLY inspect both live saved UUIDs, actual exact SuperGlueEntity class/alive/nonpassenger/bounds and complete typed persistent NBT; compare the saved census. Scan finite loaded stage inventory for extra or passenger/moving contraption interference; preserve all on any mismatch.',
            'Run fresh exact106 BEFORE verification and admit only the frozen moving53+53 nonBE target plans after actual retained-glue custody proof; no setup, retirement or glue addition. Verify full real bridge after normal joins.',
            'Rebind exact existing engineering parameters to current backup and actual new complete geometry proof. Invoke COMMISSION ONLY: its actual phase0 does not execute setup/configureRadios and performs two native button-driven signed55-degree open/close cycles.',
            'Retain immutable motion/cleanup receipts, inspect closed disassembly and current glue census, then stopped checkpoint/restart inspection. Normal Create disassembly may replace glue UUIDs, so derive fresh identities rather than reusing old UUID authority.',
            'Actual walking/open river view/night art and vessel-specific mast/hull clearance remain required; source voxel sweep and prior cycles do not qualify them.']})


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('home','output'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();print(json.dumps(prepare(a.home,a.output),indent=2))
