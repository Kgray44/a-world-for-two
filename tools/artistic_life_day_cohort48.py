"""Separate the unchanged daytime candidates from the held nocturnal firefly.

No world actions. The failed eight-member recipe stays immutable. All seven
remaining identities, habitats, predicates and native gates are preserved.
"""
from __future__ import annotations
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path

from control_room.common import UserError, digest, read_json, utcnow
from tools.artistic_bridge_refinement import encoded
from tools.artistic_first_life_requests48 import (
    CHECKPOINT, CHECKPOINT_SHA, checkpoint, clean_native, complete_receipt,
    ordinary, ref, runtime, write_output,
)
from tools.habitat_life import census
from tools.playtest import guard
from tools.settlement_attractions import BackupWorld

MIB=1024**2
ORIGINAL='staging/first8-LIFE48-inspect-20261028T1421Z'
ORIGINAL_SHA='3c27544389d212ed2317fa11afec7928b65a868a662ab5c0f622edff2bd4068a'
FAILED='dashboard/settlement/habitat-life-result-78e6826f-5090-4d04-94be-75441943a9ed.json'
HELD='c87a9969-2286-571b-b576-b8297a22ec71'


def habitat_bounds(field):
    if not field or any(len(p)!=3 or any(type(v)is not int for v in p)for p in field):
        raise UserError('Literal nonempty full habitat field required')
    bounds=[min(p[0]for p in field),min(p[2]for p in field),max(p[0]for p in field),max(p[2]for p in field)]
    if bounds[2]-bounds[0]>512 or bounds[3]-bounds[1]>512:
        raise UserError('Actual finite native512 habitat bounds exceeded')
    return bounds


def daytime_members(recipe):
    members=recipe['members']; held=[r for r in members if r['uuid']==HELD]
    if len(members)!=8 or len(held)!=1 or held[0]['entity']!='naturalist:firefly':
        raise UserError('Retain exactly the original failed eight and held native firefly identity')
    selected=[deepcopy(r) for r in members if r['uuid']!=HELD]
    if len(selected)!=7 or any(r['entity']=='naturalist:firefly' for r in selected):
        raise UserError('Daytime split must not change identities or substitute nocturnal species')
    return selected


def validate_subset_proofs(verify,inspection,manifest,recipe):
    clean_native(verify);clean_native(inspection)
    if (verify.get('operation')!='verify' or verify.get('plan_sha256')!=manifest['habitat_sha256']
            or verify.get('blocks')!=manifest['habitat_cells']
            or verify.get('status')!='verified actual block identities, orientation, block entities and supplied inventories'):
        raise UserError('Exact genuine complete daytime habitat verification required')
    if (inspection.get('operation')!='inspect' or inspection.get('request_sha256')!=manifest['request_sha256']
            or inspection.get('recipe_sha256')!=manifest['recipe_sha256'] or inspection.get('members')!=7
            or inspection.get('status')!='native habitats inspected; no resident or ledger writes'
            or inspection.get('cleanup_passed') is not True or inspection.get('spawned')!=0
            or inspection.get('intents_written')!=0 or inspection.get('population_authorities_written')!=0
            or inspection.get('world_or_ledger_write_attempted') is not False
            or inspection.get('entity_add_attempted') is not False or inspection.get('NoAI_or_ownership_writes')!=0):
        raise UserError('Genuine successful daytime seven native inspection required')
    seen=inspection.get('observations',[])
    if (len(seen)!=7 or {(r.get('uuid'),r.get('type'),r.get('native_class'))for r in seen}
            !={(r['uuid'],r['entity'],r['native_class'])for r in recipe['members']}
            or any(r.get('new_habitat_currently_admissible') is not True or r.get('spawned') is not False for r in seen)):
        raise UserError('All seven genuine admissibility observations required')


def prepare(home,output):
    home=Path(home).resolve();output=Path(output).absolute()
    reserve=guard(2*MIB,8*MIB);current=checkpoint(home);pins=runtime(home)
    folder=home/ORIGINAL;path=ordinary(home,folder/'manifest.json',MIB)
    if digest(path)!=ORIGINAL_SHA:raise UserError('Original frozen eight-member request must remain immutable')
    old=read_json(path)
    for name,info in old['files'].items():
        actual=ref(home,folder/name)
        if actual['bytes']!=info['bytes']or actual['sha256']!=info['sha256']:raise UserError('Original first8 artifacts changed')
    failed,failed_ref=complete_receipt(home,home/FAILED)
    if (failed.get('request_sha256')!=old['request_sha256'] or failed.get('recipe_sha256')!=old['recipe_sha256']
            or HELD not in failed.get('error','') or failed.get('operation')!='inspect'
            or failed.get('cleanup_passed') is not True or failed.get('cleanup_required') is not False
            or failed.get('spawned')!=0 or failed.get('intents_written')!=0
            or failed.get('population_authorities_written')!=0 or failed.get('world_or_ledger_write_attempted') is not False
            or failed.get('entity_add_attempted') is not False or failed.get('temporary_tickets_remaining')!=0
            or failed.get('pending_shared_futures')!=0):
        raise UserError('Preserve exact failed native inspection, no intents or replacement authority')
    recipe=read_json(folder/'recipe.json');recipe['members']=daytime_members(recipe)
    recipe_sha=hashlib.sha256(encoded(recipe)).hexdigest()
    registry=read_json(home/'dashboard/settlement/registry.json');snapshot=BackupWorld(home,current,registry)
    try:
        field={}
        for row in recipe['members']:
            for x,y,z,state in row['preimage']:
                if snapshot.state((x,y,z))!=state:raise UserError('Preserve every unchanged daytime full habitat preimage')
                field[x,y,z]=state
        census_doc=census(snapshot,recipe['members'],CHECKPOINT_SHA,recipe_sha)
        if not census_doc['all_requested_UUID_absent']:raise UserError('A previously present UUID needs separate custody, never recreate')
        prefix=snapshot.prefix.removesuffix('region/')+'data/awft-life/'
        if any(n.startswith(prefix)for n in snapshot.files):raise UserError('Any durable LIFE authority requires independent budget review')
        sources=snapshot.sources.copy()
    finally:snapshot.close()
    palette=sorted(set(field.values()));indices={v:n for n,v in enumerate(palette)}
    habitat={'format':'awft-native-settlement:1','name':'VERIFY ONLY seven daytime unchanged LIFE habitats',
        'seed':registry['seed'],'world_path':registry['world_path'],'backup_sha256':CHECKPOINT_SHA,
        'bounds':habitat_bounds(field),'palette':palette,'blocks':[[*p,indices[v]]for p,v in sorted(field.items())],
        'block_entities':[],'commands':[],'landmarks':[],'construction_forbidden':True,'verification_only':True}
    def newref(name,value):return {'path':(output/name).relative_to(home).as_posix(),
        'bytes':len(encoded(value)),'sha256':hashlib.sha256(encoded(value)).hexdigest()}
    ready=read_json(folder/'BARE8-only-readiness.json')
    ready.update(approved_recipe_sha256s=[recipe_sha],reviewed_at=utcnow(),
        scope='Only the seven retained daytime candidate habitat fields and typed routes; the nocturnal firefly is HELD for a genuine dark normal habitat/night window',
        flags_apply_only_to_exact_bare_habitat_fields=True,whole_town_or_forest_complete=False,
        source_original_eight_retained=True,original_failed_inspection=failed_ref)
    request=read_json(folder/old['bundle']/'request.json')
    request.update(**pins,recipe=newref('recipe.json',recipe),uuid_census=newref('uuid-census.json',census_doc))
    sha=hashlib.sha256(encoded(request)).hexdigest();bundle='life-'+sha[:16]
    docs={'recipe.json':recipe,'uuid-census.json':census_doc,'habitat-VERIFY-ONLY.json':habitat,
        'BARE7-daytime-only-readiness.json':ready,bundle+'/request.json':request,
        'split-custody.json':{'original_manifest_sha256':ORIGINAL_SHA,'original_native_failed_inspection':failed_ref,
            'no_previous_intents_or_entity_writes':True,'held_nocturnal_uuid':HELD,
            'held_species':'naturalist:firefly','day_member_UUIDs_unchanged':True,'day_habitat_cells_unchanged':True,
            'ordinary_native_spawn_rules_and_position_hooks_unchanged':True,'saved_sources':sources,
            'native_art_AI_behavior_and_actual_daytime_acceptance':False}}
    return write_output(home,output,docs,{'format':'awft-daytime-seven-life48-preparation:1','created':utcnow(),
        'source_sha256':digest(Path(__file__)),'checkpoint_id':CHECKPOINT,'checkpoint_sha256':CHECKPOINT_SHA,
        'recipe_sha256':recipe_sha,'habitat_sha256':hashlib.sha256(encoded(habitat)).hexdigest(),
        'habitat_cells':len(field),'members':7,'operation':'inspect','bundle':bundle,'request_sha256':sha,
        'native_actions':0,'installed':False,'reserve_guard':reserve,
        'command_after_parent_review':f'awftlife inspect {bundle} {sha}'})


def seed(home,prepared,output,native_verify,native_inspect):
    home=Path(home).resolve();prepared=Path(prepared).resolve();output=Path(output).absolute()
    reserve=guard(MIB,4*MIB);checkpoint(home);pins=runtime(home)
    manifest=read_json(ordinary(home,prepared/'manifest.json',MIB))
    if manifest.get('format')!='awft-daytime-seven-life48-preparation:1':raise UserError('Exact daytime subset inspection required')
    for name,info in manifest['files'].items():
        actual=ref(home,prepared/name)
        if actual['bytes']!=info['bytes']or actual['sha256']!=info['sha256']:raise UserError('Immutable day preparation changed')
    recipe=read_json(prepared/'recipe.json');request=read_json(prepared/manifest['bundle']/'request.json')
    if any(request.get(k)!=v for k,v in pins.items()):raise UserError('Actual installed48 controller and pack must remain unchanged')
    verify,verify_ref=complete_receipt(home,native_verify);inspection,inspect_ref=complete_receipt(home,native_inspect)
    validate_subset_proofs(verify,inspection,manifest,recipe)
    request.update(allowed_operation='seed',life_ready=ref(home,prepared/'BARE7-daytime-only-readiness.json'),
        native_habitat_verify=verify_ref,habitat_plan=ref(home,prepared/'habitat-VERIFY-ONLY.json'),
        habitat_plan_sha256=manifest['habitat_sha256'])
    sha=hashlib.sha256(encoded(request)).hexdigest();bundle='life-'+sha[:16]
    return write_output(home,output,{bundle+'/request.json':request,'genuine-native-gates.json':{
        'full_habitat_verify':verify_ref,'exact_seven_native_inspect':inspect_ref,'firefly_still_held':True}},
        {'format':'awft-daytime-seven-life48-seed-preparation:1','created':utcnow(),'source_sha256':digest(Path(__file__)),
         'checkpoint_sha256':CHECKPOINT_SHA,'bundle':bundle,'request_sha256':sha,'operation':'seed','native_actions':0,
         'members':7,'reserve_guard':reserve,'command_after_parent_review':f'awftlife seed {bundle} {sha}'})


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('operation',choices=('inspect','seed'))
    for k in ('home','output'):p.add_argument('--'+k,type=Path,required=True)
    for k in ('prepared','native-verify','native-inspect'):p.add_argument('--'+k,type=Path)
    a=p.parse_args()
    if a.operation=='inspect':result=prepare(a.home,a.output)
    else:
        if not all((a.prepared,a.native_verify,a.native_inspect)):p.error('seed needs both genuine native proofs')
        result=seed(a.home,a.prepared,a.output,a.native_verify,a.native_inspect)
    print(json.dumps(result,indent=2))
