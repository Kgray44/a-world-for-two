"""Bind the unchanged26 relief proposal to the real wet stopped31 save.

No dry replay, native admission, placement, control/pressure/NBT write or entity
action. Fresh native before and parent-reviewed admission remain separate.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path

from control_room.common import UserError, digest, read_json, utcnow
from tools import artistic_fountain_ornament47 as ornament
from tools.artistic_bridge_refinement import encoded
from tools.artistic_bridge_topside_inspection import owned_regular
from tools.artistic_fountain_centerpiece import block_entities, decode, MARS, normal_owned_copper_aging
from tools.artistic_materials import require_material_rule, require_outdoor_rule
from tools.artistic_spawn_plaza import (HEADER,OUTLET,PISTON,PLUG_OPEN,STOP_LEVER,PUMP,WHEEL,
                                      WHEEL_SOURCE,JET_WITNESSES,payload,key)
from tools.artistic_tree_residual_review47 import state_checked
from tools.playtest import guard
from tools.settlement_attractions import BackupWorld

MIB=1024**2
CHECKPOINT='20261028T073257Z-31e541'
CHECKPOINT_SHA='da5ef61fbd1153509ac0b722228045285739667ccb82f6076caa9cd031a4deff'
PROPOSAL='staging/fountain-carved-refinement47-20261028T0657Z'
PROPOSAL_SHA='1136a6131a3d6d45d2c173f321e0e3a0de445d8ec93c3edc49d7ca39675ae629'
BASE='staging/fountain-R5-ACTUAL-DRY575-20261028T062056Z-a92cef/plaza.json'
BASE_SHA='e76adf987d50b30510155c257d4dd3c2d4dfc89ee1816b01908506e90f201ecc'


def ref(home,path):
    path=owned_regular(home,path,16*MIB)
    return {'path':path.relative_to(home).as_posix(),'bytes':path.stat().st_size,'sha256':digest(path)}


def saved_wet_gate(actual):
    def props(pos):
        text=actual[pos];name,_,tail=text.partition('[')
        return name,dict(t.split('=',1) for t in tail[:-1].split(',')) if tail else {}
    if actual[HEADER]!='minecraft:water[level=0]' or actual[WHEEL_SOURCE]!='minecraft:water[level=0]':
        raise UserError('Preserve the actual wet sources; never substitute a dry fountain here')
    if any(key(actual[p])!='minecraft:water' for p in (OUTLET,*JET_WITNESSES)):
        raise UserError('The stopped wet-flow source witness no longer has four water jets')
    lever,lp=props(STOP_LEVER);piston,pp=props(PISTON)
    if (lever!='minecraft:lever' or lp.get('powered')!='false' or piston!='minecraft:sticky_piston'
            or pp.get('facing')!='north' or pp.get('extended')!='false'
            or actual[PLUG_OPEN]!='minecraft:chiseled_quartz_block'):
        raise UserError('Preserve the actual reopened, settled physical gate; never write piston/plug/control states')


def prepare(home,output):
    home,output=Path(home).resolve(),Path(output).resolve()
    if output.exists() or output.parent!=home/'staging':raise UserError('New owned wet binding folder required')
    reserve=guard(2*MIB,8*MIB)
    checkpoint=read_json(home/'dashboard/settlement/backup-receipt.json')
    if checkpoint.get('verified') is not True or (checkpoint.get('id'),checkpoint.get('sha256'))!=(CHECKPOINT,CHECKPOINT_SHA):
        raise UserError('Actual newly stopped31 checkpoint required; never silently use575')
    owner=read_json(home/'dashboard/artistic-owner.json')
    if (owner.get('backup'),owner.get('backup_sha256'))!=(CHECKPOINT,CHECKPOINT_SHA):
        raise UserError('Current artistic owner/checkpoint differs')
    registry=read_json(owned_regular(home,home/'dashboard/settlement/registry.json',16*MIB))
    folder=home/PROPOSAL
    if digest(folder/'manifest.json')!=PROPOSAL_SHA or digest(home/BASE)!=BASE_SHA:
        raise UserError('Immutable photo-led26 proposal and historical full R5 authority required')
    manifest=read_json(folder/'manifest.json')
    def member(name):
        value=manifest['files'][name];p=owned_regular(home,folder/name,8*MIB)
        if p.stat().st_size!=value['bytes'] or digest(p)!=value['sha256']:raise UserError('Immutable ornament member differs')
        return read_json(p)
    addition=decode(member('addition-26-SOURCE-ONLY.json'))
    historical=decode(member('historical575-targets-and-mounts-VERIFY-ONLY.json'))
    base=decode(read_json(home/BASE))
    if len(addition)!=26 or not set(addition)<=base.keys():raise UserError('Exact unchanged26 authored AIR positions required')
    snapshot=BackupWorld(home,checkpoint,registry)
    try:
        actual={p:state_checked(snapshot.state(p),registry) for p in base}
        before={p:actual[p] for p in historical}
        if any(before[p]!='minecraft:air' or p in snapshot.protected for p in addition):
            raise UserError('Current stopped wet target is not empty; no replacement admission')
        if any(before[p]!=historical[p] for p in historical if p not in addition):
            raise UserError('Actual retained solid/slab mount changed; do not reset it')
        for p,s in actual.items():
            old=base[p]
            if key(old)!=key(s) and {key(old),key(s)}!={'minecraft:air','minecraft:water'} and not normal_owned_copper_aging(old,s):
                raise UserError('Nonfluid/nonweathering R5 material changed in the current stopped save')
        saved_wet_gate(actual)
        for n in range(3):
            if actual[1138,75+n,-1129]!=MARS+'[facing=west,multiblock='+str(n)+',waterlogged=false]':
                raise UserError('Preserve all actual native statue parts')
        bes=block_entities(snapshot,set(actual))
        speeds={}
        for pos in (PUMP,WHEEL):
            speed=bes.get(pos,{}).get('Speed')
            if type(speed) not in (int,float) or not math.isfinite(speed) or speed==0:
                raise UserError('Current wet saved kinetic witness must be actual nonzero finite native speed')
            speeds[str(pos)]=speed
        regions=list(snapshot.sources)
    finally:snapshot.close()
    full_after=actual|addition
    if any(full_after[p]!=s for p,s in actual.items() if p not in addition):
        raise UserError('Only the26 reviewed AIR cells may differ from the actual wet save')
    def native(field,label):
        doc=payload(registry,CHECKPOINT_SHA,field,label,before=True)
        doc['validation']='READONLY / SOURCE ONLY actual WET31 binding. No dry full-geometry replay, BE/NBT restoration or native admission.'
        return encoded(doc)
    be_summary=[{'pos':list(p),'actual_saved_native_nbt':value,
                 'observation_only_never_replay':True} for p,value in sorted(bes.items())]
    docs={'ornament26-before-with-mounts-VERIFY-ONLY.json':native(before,'VERIFY ONLY actual wet31 ornament AIR targets and retained mounts'),
          'ornament26-ADDITION-SOURCE-ONLY.json':native(addition,'PROPOSAL ONLY unchanged26 ornament on actual wet31 source'),
          'ornament26-after-with-mounts-VERIFY-ONLY.json':native(before|addition,'VERIFY ONLY prospective26 ornaments and unchanged mounts'),
          'complete-current-WET-before-VERIFY-ONLY.json':native(actual,'VERIFY ONLY actual complete current WET fountain; never replay'),
          'complete-WET-after-ornament-VERIFY-ONLY.json':native(full_after,'VERIFY ONLY prospective full WET fountain plus26; original cells preserved'),
          'retained-saved-native-BEs-OBSERVED-ONLY.json':encoded(be_summary)}
    report={'format':'awft-fountain26-current-wet-binding:1','created':utcnow(),'source_sha256':digest(Path(__file__)),
        'checkpoint_id':CHECKPOINT,'checkpoint_sha256':CHECKPOINT_SHA,'photo_proposal_manifest_sha256':PROPOSAL_SHA,
        'current_saved_fountain_is_wet':True,'actual_dry_checkpoint':False,'old575_is_not_current_preimage_authority':True,
        'new_targets':26,'target_and_mount_witness_cells':len(before),'complete_retained_positions':len(actual),
        'complete_prospective_positions':len(full_after),'observed_saved_speeds':speeds,
        'retained_native_BEs':len(bes),'all_BE_records_observation_only':True,
        'all_retained_positions_unchanged_except_reviewed_AIR':True,
        'material':require_material_rule(full_after,'Full current wet fountain plus26 photo-led reliefs'),
        'outdoor':require_outdoor_rule(full_after,'Current wet plaza plus26 small ornaments'),
        'current_native_admission_created':False,'native_actions':0,'world_or_BE_writes':0,
        'quarantine_untouched':True,'hydraulic_pass_before_ornament':ornament.NATIVE_FUNCTION_SHA,
        'new_hydraulic_or_visual_acceptance':False,'source_regions':regions,'reserve_guard':reserve,
        'required_next':['Fresh actual native exact target/mount proof against this31 source',
            'Parent-reviewed26-only admission with current world/pack provenance',
            'Normal shape settlement and strict new26/retained mount/full wet block verification',
            'Actual current native pipe/kinetic/gate/statue preservation readback and matching day/night photographs'],
        'files':{n:{'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()} for n,raw in docs.items()}}
    docs['manifest.json']=encoded(report)
    if sum(map(len,docs.values()))>8*MIB:raise UserError('Finite wet source binding budget exceeded')
    output.mkdir()
    for name,raw in docs.items():(output/name).write_bytes(raw)
    return {'folder':str(output),'manifest_sha256':hashlib.sha256(docs['manifest.json']).hexdigest(),
            'new_targets':26,'native_actions':0,'current_fountain_is_wet':True}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--home',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    a=parser.parse_args();print(json.dumps(prepare(a.home,a.output),indent=2))
