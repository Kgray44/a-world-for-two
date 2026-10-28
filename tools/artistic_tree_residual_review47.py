"""Read-only full-field review of one quarantined native47 tree outcome.

Never restores ambient blocks, clears quarantine, retries growth or executes a
native action. Native plans are verification-only current saved witnesses.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path

from control_room.common import UserError, digest, read_json, utcnow
from tools.artistic_bridge_refinement import encoded
from tools.artistic_bridge_topside_inspection import owned_regular
from tools.artistic_forest_understory import settlement_plan
from tools.native_tree_growth import box_volume
from tools.playtest import guard
from tools.settlement_attractions import BackupWorld

MIB=1024**2
CHECKPOINT='20261028T073257Z-31e541'
CHECKPOINT_SHA='da5ef61fbd1153509ac0b722228045285739667ccb82f6076caa9cd031a4deff'
OUTCOME='dashboard/settlement/tree-outcome-0ca76519-a79c-4b26-9695-88194f3527b4.json'
OUTCOME_SHA='0e66aab7885d9d01664289783348dfaae5a7760a4d19377cddc806e3c9be464b'
TERMINAL='dashboard/settlement/tree-growth-result-7d9ed71b-58d3-468b-9c26-f1111d4be161.json'
TERMINAL_SHA='65c389b5a0e9c25d28646c097cd35bce98f8ac653c3ddccc4893015ccb598bb4'
REQUEST_SHA='96b89e0c54a231a5607bd8040b6fdf4ca270a050e9d3172d493ea1686c6253ef'
PLAN_SHA='950fa38c810f4fa26ed4fc6affb8c961bf069b3af96faf365f40ec76ead4939c'
QUARANTINE_SHA='b2c8a01ddba588b87eaeac87e8a6ca442924e52c9728be2fe3283dbaaec1fdc0'
AMBIENT={(1226,62,-1091):('minecraft:water[level=0]','minecraft:ice'),
         (1244,62,-1088):('minecraft:ice','minecraft:water[level=0]')}
OWNED={(1232,64,-1080):('minecraft:tall_grass[half=lower]','regions_unexplored:golden_larch_sapling[stage=1]'),
       (1232,65,-1080):('minecraft:tall_grass[half=upper]','minecraft:air')}


def state_checked(text,registry):
    if not isinstance(text,str) or not 1<=len(text)<=1024:raise UserError('Bounded literal full state required')
    name,sep,tail=text.partition('[')
    if sep and not tail.endswith(']'):raise UserError('Malformed property record')
    tokens=tail[:-1].split(',') if sep else []
    if any(t.count('=')!=1 for t in tokens):raise UserError('One literal property value per record required')
    pairs=[t.split('=',1) for t in tokens]
    props=dict(pairs)
    if len(props)!=len(pairs):raise UserError('Duplicate native property')
    schema=registry['blocks'].get(name)
    if schema is None or set(schema)!=set(props) or any(v not in schema[k] for k,v in props.items()):
        raise UserError('Every property must be present and valid in the actual native registry')
    return name+('['+','.join(k+'='+props[k] for k in sorted(props))+']' if props else '')


def field_checked(doc,registry,bounds):
    palette=doc.get('palette');rows=doc.get('blocks')
    if not isinstance(palette,list) or palette!=sorted(set(palette)) or not 1<=len(palette)<=2048:
        raise UserError('Unique sorted native full-state palette required')
    states=[state_checked(s,registry) for s in palette]
    if any(a!=b for a,b in zip(states,palette)):raise UserError('Native state property order must be canonical')
    if not isinstance(rows,list) or len(rows)!=box_volume(bounds) or len(rows)>131072:
        raise UserError('One complete finite known field required')
    field={}
    for row in rows:
        if not isinstance(row,list) or len(row)!=4 or any(type(n)is not int for n in row):
            raise UserError('Literal integer native coordinate/palette records required')
        p=tuple(row[:3]);index=row[3]
        if p in field or not all(bounds[i]<=p[i]<=bounds[i+3] for i in range(3)) or not 0<=index<len(states):
            raise UserError('Duplicate/outside/invalid native field cell')
        field[p]=states[index]
    return field


def changes(a,b):
    if a.keys()!=b.keys():raise UserError('All captures must cover the same complete coordinates')
    return [{'pos':list(p),'before':a[p],'after':b[p]} for p in sorted(a) if a[p]!=b[p]]


def marked(home,name,expected,cap):
    path=owned_regular(home,home/name,cap)
    marker=owned_regular(home,Path(str(path)+'.complete'),128)
    if digest(path)!=expected or marker.read_text().strip()!=expected:raise UserError('Exact original marked native receipt required')
    return read_json(path)


def reference(home,ref,cap):
    path=owned_regular(home,home/ref['path'],cap)
    if path.stat().st_size!=ref['bytes'] or digest(path)!=ref['sha256']:raise UserError('Actual native request reference differs')
    return read_json(path)


def prepare(home,output):
    home,output=Path(home).resolve(),Path(output).resolve()
    if output.exists() or output.parent!=home/'staging':raise UserError('New private source review output required')
    reserve=guard(2*MIB,16*MIB)
    registry=read_json(owned_regular(home,home/'dashboard/settlement/registry.json',16*MIB))
    checkpoint=read_json(owned_regular(home,home/'dashboard/settlement/backup-receipt.json',4096))
    if checkpoint.get('verified') is not True or (checkpoint.get('id'),checkpoint.get('sha256'))!=(CHECKPOINT,CHECKPOINT_SHA):
        raise UserError('Exact newly stopped post47 quarantine-preserving checkpoint required')
    quarantine=owned_regular(home,home/'dashboard/settlement/tree-growth-quarantine.json',4096)
    if digest(quarantine)!=QUARANTINE_SHA:raise UserError('Original quarantine must remain unchanged')
    flag=read_json(quarantine)
    terminal=marked(home,TERMINAL,TERMINAL_SHA,MIB)
    outcome=marked(home,OUTCOME,OUTCOME_SHA,16*MIB)
    request_path=owned_regular(home,home/('dashboard/settlement/trees-'+REQUEST_SHA[:16]+'/request.json'),128*1024)
    if digest(request_path)!=REQUEST_SHA:raise UserError('Exact original grown-request identity required')
    request=read_json(request_path)
    plan=reference(home,request['plan'],MIB);before=reference(home,request['before'],8*MIB)
    bounds=plan['known_bounds'];write=plan['write_bounds']
    if (request['plan']['sha256']!=PLAN_SHA or flag.get('plan_sha256')!=PLAN_SHA
            or terminal.get('request_sha256')!=REQUEST_SHA or terminal.get('plan_sha256')!=PLAN_SHA
            or terminal.get('outcome_archive_sha256')!=OUTCOME_SHA or terminal.get('failures')!=1
            or terminal.get('cleanup_resources_passed') is not True or terminal.get('cleanup_passed') is not False
            or terminal.get('world_recovery_required') is not True or terminal.get('temporary_tickets_remaining')!=0
            or terminal.get('pending_shared_futures')!=0 or terminal.get('cleanup_errors')!=[]
            or outcome.get('format')!='awft-native-tree-outcome:1'
            or outcome.get('kind')!='FAILED_NATIVE_ATTEMPT_RESIDUAL_REQUIRES_EXACT_REVIEW'
            or outcome.get('construction_forbidden') is not True or outcome.get('entity_nbt_replay_forbidden') is not True
            or outcome.get('source_plan_sha256')!=PLAN_SHA or plan['root']!=[1232,64,-1080]):
        raise UserError('Exact failed transaction, cleanup and unresolved quarantine provenance required')
    captures={name:field_checked(outcome[name],registry,bounds) for name in
              ('before','native_after','after_failed_attempt_restoration')}
    original=field_checked(before,registry,bounds)
    if captures['before']!=original:raise UserError('Outcome BEFORE differs from the authentic request full preimage')
    expected_after={p:s for p,(_,s) in AMBIENT.items()}|{p:s for p,(_,s) in OWNED.items()}
    actual_after={tuple(r['pos']):r['after'] for r in changes(original,captures['native_after'])}
    actual_restored={tuple(r['pos']):r['after'] for r in changes(original,captures['after_failed_attempt_restoration'])}
    if actual_after!=expected_after or actual_restored!={p:s for p,(_,s) in AMBIENT.items()}:
        raise UserError('Preserve any new unexplained residual; do not apply an old two-cell classification')
    if any(original[p]!=pair[0] for p,pair in (AMBIENT|OWNED).items()):raise UserError('Expected full original states differ')
    if any(all(write[i]<=p[i]<=write[i+3] for i in range(3)) for p in AMBIENT):
        raise UserError('Two ambient-compatible changes must lie outside the owned WRITE field')
    if any(outcome.get(k)!=[] for k in ('native_be_before','native_be_after','native_be_after_restoration')):
        raise UserError('Existing/new native BE requires separate typed custody review, never replay')
    snapshot=BackupWorld(home,checkpoint,registry)
    try:
        saved={p:state_checked(snapshot.state(p),registry) for p in original}
        if any(p in snapshot.protected for p in original):raise UserError('Saved BE appeared in this full field; retain it for independent review')
        sources=list(snapshot.sources)
    finally:snapshot.close()
    # Record fresh normal-save drift; never coerce it back to either old phase.
    saved_vs_restored=changes(captures['after_failed_attempt_restoration'],saved)
    docs={'saved-full-field-READONLY-VERIFY-ONLY.json':encoded(settlement_plan(registry,checkpoint,saved,
          'VERIFY ONLY current stopped post47 full field; no ambient rollback or growth authority')),
          'saved-four-changed-cells-READONLY-VERIFY-ONLY.json':encoded(settlement_plan(registry,checkpoint,
          {p:saved[p] for p in AMBIENT|OWNED},'VERIFY ONLY current two restored grass cells and two preserved ice/water phases'))}
    review={'format':'awft-native47-tree-residual-readonly-review:1','created':utcnow(),'checkpoint_id':CHECKPOINT,
        'checkpoint_sha256':CHECKPOINT_SHA,'outcome_sha256':OUTCOME_SHA,'terminal_sha256':TERMINAL_SHA,
        'quarantine_sha256_before':QUARANTINE_SHA,'quarantine_retained':True,
        'complete_typed_state_coordinates_per_capture':len(original),'native_after_differences':changes(original,captures['native_after']),
        'restored_differences':changes(original,captures['after_failed_attempt_restoration']),
        'two_owned_changed_cells_exactly_restored_in_native_capture':True,
        'saved_owned_cells_still_match_original':all(saved[p]==original[p] for p in OWNED),
        'saved_vs_native_restored_drift':saved_vs_restored,'native_BE_rows_all_three_captures':0,
        'perform_bonemeal_calls':terminal['perform_bonemeal_calls'],'native_success_rolls':terminal['native_success_rolls'],
        'bounded_trials':terminal['native_bonemeal_trials'],
        'configured_tree_or_canopy_success_proved':False,'actual_setter_attempt_position_ledger_present_in_archive':False,
        'classification':'Only two unowned water/ice phase transitions remain in the restored capture; compatible with ambient freeze/melt, exact callback origin/timing not captured',
        'ambient_two_cells_are_never_rollback_targets':True,'whole_world_entity_census_claimed':False,
        'native_actions':0,'world_or_BE_entity_inventory_writes':0,'flag_clears_or_growth_retries':0,
        'quarantine_release_authority_created':False,'native_afterfield_and_release_review_pending':True,
        'source_regions':sources,'reserve_guard':reserve,
        'files':{n:{'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()} for n,b in docs.items()}}
    if digest(quarantine)!=QUARANTINE_SHA:raise UserError('Quarantine changed during read-only review; no release is inferred')
    docs['review.json']=encoded(review)
    if sum(map(len,docs.values()))>16*MIB:raise UserError('Finite residual source review budget exceeded')
    output.mkdir()
    for name,raw in docs.items():(output/name).write_bytes(raw)
    return {'folder':str(output),'review_sha256':hashlib.sha256(docs['review.json']).hexdigest(),
            'full_field_cells':len(original),'saved_vs_native_restored_differences':len(saved_vs_restored),
            'quarantine_retained':True,'native_actions':0}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--home',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();print(json.dumps(prepare(args.home,args.output),indent=2))
