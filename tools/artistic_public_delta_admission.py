"""Admit exactly two reviewed architectural deltas after real native BEFORE.

Private artifact writer only. No Minecraft launch, console or live-world action.
"""
from __future__ import annotations
import argparse
from copy import deepcopy
import json
from pathlib import Path
from control_room.common import UserError,digest,utcnow
from tools.artistic_bridge_refinement import flatten
from tools.artistic_quay_prototype import bounded,context,fresh_proof,member,same_world,write_bundle
from tools.playtest import guard
from tools.showcase_coverage import SNBT

FORMATS={'awft-modeled-west-public-street:1':'street-and-furniture-PROPOSAL.json',
         'awft-drowned-rose-exterior:1':'exterior-PROPOSAL.json'}


def bind(home,prepared,prepared_sha,native_before,output):
    reserve=guard(2*1024**2,8*1024**2)
    home,output,current,registry=context(home,output);prepared,native_before=Path(prepared).resolve(),Path(native_before).resolve()
    if prepared.parent!=home/'staging' or not native_before.is_relative_to(home/'dashboard/settlement'):
        raise UserError('Owned immutable proposal/native receipt paths required')
    source=bounded(prepared/'manifest.json');fmt=source.get('format')
    if digest(prepared/'manifest.json')!=prepared_sha or fmt not in FORMATS:
        raise UserError('Exact reviewed street/exterior manifest required')
    if(source.get('checkpoint_id'),source.get('checkpoint_sha256'))!=(current['id'],current['sha256']):
        raise UserError('Re-read the exact new stopped preimages rather than bypass checkpoint custody')
    before=member(prepared,source,'before-VERIFY-ONLY.json');delta=member(prepared,source,FORMATS[fmt]);after=member(prepared,source,'complete-after-VERIFY-ONLY.json')
    for doc in(before,delta,after):
        same_world(doc,registry)
        if doc.get('backup_sha256')!=current['sha256'] or doc.get('commands')!=[]:raise UserError('No command or stale-world authority may enter this architecture delta')
    if before.get('verification_only') is not True or before.get('construction_forbidden') is not True or before.get('block_entities')!=[]:
        raise UserError('Only an actual verification-only exact preimage can admit the proposed delta')
    if delta.get('construction_forbidden') is not True or delta.get('verification_only'):
        raise UserError('Preserve the original forbidden after proposal')
    a,b,c=flatten(before),flatten(delta),flatten(after)
    if not b or not set(b)<=set(a)or any(c.get(q)!=v for q,v in b.items()):raise UserError('Exact before/delta/full fields do not cover the same physical proposal')
    for row in delta['block_entities']:
        q=tuple(row['pos']);text=row['nbt']
        if not isinstance(text,str)or not 0<len(text)<=16384:raise UserError('Actual SettlementSupport requires a bounded native SNBT string; JSON object tags are refused')
        tag=SNBT(text).read()
        if a.get(q)!='minecraft:air' or not b.get(q,'').startswith('minecraft:barrel[') or tag.get('id')!='minecraft:barrel' or tag.get('Items')!=[]:
            raise UserError('Only the explicitly new source empty barrel inventories may be loaded; preserve every old BE')
    proof,marker=fresh_proof(native_before,digest(prepared/'before-VERIFY-ONLY.json'),len(before['blocks']))
    admitted=deepcopy(delta);admitted.pop('construction_forbidden',None)
    admitted['name']='ADMITTED ONCE after actual native preimage: '+delta['name']
    settle=deepcopy(admitted);settle.update(name='NORMAL SETTLE ONLY admitted street/exterior current blocks; no tag replay',verification_only=True,construction_forbidden=True,block_entities=[])
    return write_bundle(output,{'delta-PLACE-ONCE.json':admitted,'delta-NORMAL-SETTLE-ONLY.json':settle,'complete-after-VERIFY-ONLY.json':after},
        {'format':'awft-admitted-public-architecture-delta:1','created':utcnow(),'source_sha256':digest(Path(__file__)),'proposal_format':fmt,
         'checkpoint_id':current['id'],'checkpoint_sha256':current['sha256'],'prepared_relative':prepared.relative_to(home).as_posix(),'prepared_sha256':prepared_sha,
         'native_before':{'relative':native_before.relative_to(home).as_posix(),'sha256':digest(native_before),'marker_sha256':digest(marker),'finished':proof['finished']},
         'targets':len(b),'source_geometry_changes':0,'old_frozen_artifacts_changed':False,'old_BE_or_inventory_replay':False,
         'native_actions':0,'world_writes':0,'storage_guard':reserve,'next_gate':'Parent exact placement once, normal joins, strict complete native verification; actual walking/eye-level/inside/day/night art and mod interactions remain separate'})


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('home','prepared','native-before','output'):p.add_argument('--'+k,type=Path,required=True)
    p.add_argument('--prepared-sha',required=True)
    a=p.parse_args();print(json.dumps(bind(a.home,a.prepared,a.prepared_sha,a.native_before,a.output),indent=2))
