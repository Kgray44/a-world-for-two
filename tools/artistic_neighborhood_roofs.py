"""Canonical pinned Macaw ridge parts from complete original neighbor masks.

Verification/normal-neighbor-settle inputs only. No geometry, inventory,
orientation or source placement is replayed; failed native receipts survive.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path

from control_room.common import UserError,digest,read_json
from tools.artistic_bridge_refinement import encoded,flatten,payload
from tools.playtest import guard
from tools.settlement_attractions import base,properties

MIB=1024**2
PINNED_JAR='mcw-roofs-2.3.2-mc1.21.1neoforge.jar'
PINNED_SHA='25c79def993a24b05b0f8494ee9417717d469bc000d5ed7c219b47dcc3b3e9c8'
SOURCE_FULLS={
    'signal':'b5cb15a2b2fc0766f24f3497217ad15c39102ce01733a4e656c2715a232a0676',
    'court':'4e28423fe4358bfe152c4e91d08024d495113993148fe92eecdada05dc7ce259',
    'bramble':'4c028b761db2f08c10d6fb190e9db11a5391917661d54d66ef0b8802d35b7029',
}
# Index bits are N=1,E=2,S=4,W=8, SAME actual block identity, same Y.
# Derived from pinned RoofTopNew.StairState/getRoofPart, not observed failures.
PARTS=('switched_0','top_end_0','top_end_90','top_outer_90',
       'top_end_180','switched_0','top_outer_180','three_way_0',
       'top_end_270','top_outer_0','switched_90','three_way_270',
       'top_outer_270','three_way_180','three_way_90','four_way')


def ridge_part(north,east,south,west):
    if any(type(value) is not bool for value in (north,east,south,west)):
        raise UserError('Exact same-block cardinal neighbor booleans required')
    return PARTS[int(north)+2*int(east)+4*int(south)+8*int(west)]


def derive(registry,original):
    field=flatten(original);corrected=copy.deepcopy(original);changes=[];ridges={}
    for row in corrected['blocks']:
        pos=tuple(row[:3]);before=original['palette'][row[3]];key=base(before)
        if not(key.startswith('mcwroofs:') and key.endswith('_top_roof')):continue
        x,y,z=pos
        neighbors=[(x,y,z-1),(x+1,y,z),(x,y,z+1),(x-1,y,z)]
        mask=[base(field.get(other,'minecraft:air'))==key for other in neighbors]
        part=ridge_part(*mask);fields=properties(before)
        if set(fields)!={'part'}:raise UserError('Unexpected native ridge properties; preserve structure')
        if part not in registry['blocks'].get(key,{}).get('part',()):
            raise UserError('Derived canonical ridge part is not actually registered')
        fields['part']=part;after=key+'[part='+part+']';ridges[pos]=after
        if after==before:continue
        if after not in corrected['palette']:corrected['palette'].append(after)
        row[3]=corrected['palette'].index(after)
        changes.append({'position':list(pos),'before':before,'after':after,
                        'same_id_cardinal_mask':dict(zip(('north','east','south','west'),mask)),
                        'neighbor_positions':[list(other) for other in neighbors]})
    actual=flatten(corrected)
    if set(actual)!=set(field) or any(base(actual[pos])!=base(value) for pos,value in field.items()):
        raise UserError('Canonical parts must not change any block identity or position')
    if corrected['block_entities']!=original['block_entities'] or corrected['commands']!=original['commands']:
        raise UserError('Canonical ridge expectations must preserve every original NBT and command')
    corrected.update(verification_only=True,construction_forbidden=True)
    return corrected,changes,ridges


def prepare(home,compositions,output,checkpoint_id,checkpoint_sha):
    home,compositions,output=(Path(value).resolve() for value in (home,compositions,output))
    if output.exists() or not output.is_relative_to(home/'staging'):
        raise UserError('New private verification-only output required')
    reserve=guard(2*MIB,8*MIB)
    current=read_json(home/'dashboard/settlement/backup-receipt.json')
    if current.get('verified') is not True or current.get('id')!=checkpoint_id or current.get('sha256')!=checkpoint_sha:
        raise UserError('Exact current verified checkpoint required')
    registry=read_json(home/'dashboard/settlement/registry.json');raw={};details={}
    jar=home/'server/mods'/PINNED_JAR
    if not jar.is_file() or jar.stat().st_size>32*MIB or digest(jar)!=PINNED_SHA:raise UserError('Exact bounded pinned native roof API required')
    for name,expected in SOURCE_FULLS.items():
        path=compositions/(name+'-full-verification.json')
        if digest(path)!=expected:raise UserError('Exact immutable full composition differs: '+name)
        original=read_json(path)
        if original['seed']!=registry['seed'] or original['world_path']!=registry['world_path']:
            raise UserError('Original composition belongs to another world')
        corrected,changes,ridges=derive(registry,original)
        corrected['backup_sha256']=checkpoint_sha
        settle=payload(corrected,ridges,checkpoint_sha,name+' ridge-only NORMAL SETTLE/VERIFY; NEVER PLACE')
        settle.update(verification_only=True,construction_forbidden=True)
        raw[name+'-canonical-full-VERIFY-ONLY.json']=encoded(corrected)
        raw[name+'-ridges-SETTLE-ONLY.json']=encoded(settle)
        details[name]={'source_sha256':expected,'unchanged_positions':len(original['blocks']),
                       'canonical_part_changes':len(changes),'ridge_targets':len(ridges),'changes':changes,
                       'strict_material_ID_and_orientation_inventory_unchanged':True}
    if {name:row['canonical_part_changes'] for name,row in details.items()}!={'signal':47,'court':14,'bramble':28}:
        raise UserError('Exact reviewed complete-mask correction inventory changed')
    report={'format':'awft-neighborhood-canonical-ridges:1','source_sha256':digest(Path(__file__)),
            'checkpoint_id':checkpoint_id,'checkpoint_sha256':checkpoint_sha,'native_roof_api':{'file':PINNED_JAR,'sha256':digest(jar),
            'class':'com.mcwroofs.kikoz.objects.roofs.RoofTopNew','methods':['StairState','getRoofPart','updateShape']},
            'signal_failed_native_receipt_preserved':'settlement-result-2588309c-ac0e-4785-a08f-ca52072487ab.json',
            'basis':'Complete original same-ID cardinal masks and pinned native algorithm; never copying actual mismatches into expected states',
            'districts':details,'native_actions':False,'reserve_guard':reserve,
            'files':{name:{'bytes':len(value),'sha256':hashlib.sha256(value).hexdigest()} for name,value in raw.items()},
            'gate':'Parent normal native ridge settling if needed, then strict canonical full verification; no geometry/state/NBT placement replay or broad verifier exemption'}
    raw['derivation.json']=encoded(report)
    if sum(map(len,raw.values()))>8*MIB:raise UserError('Canonical ridge evidence exceeds allocation')
    output.mkdir(parents=True,exist_ok=False)
    for name,value in raw.items():(output/name).write_bytes(value)
    return {'output':str(output),'districts':{k:{n:v[n] for n in ('canonical_part_changes','ridge_targets','unchanged_positions')} for k,v in details.items()},'files':report['files']}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('home','compositions','output'):parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--checkpoint-id',required=True);parser.add_argument('--checkpoint-sha',required=True)
    print(json.dumps(prepare(**vars(parser.parse_args())),indent=2))
