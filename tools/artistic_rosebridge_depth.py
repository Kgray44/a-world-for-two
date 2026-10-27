"""Twenty blind fascia recesses; retain the pedestrian bridge's occupied envelope.

This isolated layer never moves a pier, changes a deck/rail/soffit, fills water,
replays an inventory or invokes native placement. Parent owns live admission.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path

from control_room.common import UserError, digest, read_json
from tools.artistic_bridge_refinement import encoded, flatten, payload
from tools.artistic_landmarks import MASONRY, bridge_deck, world_point
from tools.artistic_materials import require_material_rule, require_outdoor_rule
from tools.playtest import guard
from tools.settlement_attractions import BackupWorld, base, properties

MIB=1024**2
BASE_SHA='9c9b37cea97a69d9f510bfed83b70c072793ebc35fed175ce50b3355506a51f2'
STATIONS=(-28,-8,0,8,28)
MAX_OUTPUT=2*MIB
CAMERA={'feet':[1248,65,-1131],'yaw':0.,'pitch':-9.214379,
        'reference_sha256':'a76be37b4d57abd8db3b7829534f5bbc69fb7852f687e6cf87d0da6b01717421'}


def native_stair(registry,face,half):
    key='minecraft:smooth_quartz_stairs'
    values={'facing':face,'half':half,'shape':'straight','waterlogged':'false'}
    schema=registry['blocks'].get(key)
    if schema is None or any(value not in schema.get(name,()) for name,value in values.items()):
        raise UserError('Exact native pale recessed stair palette required')
    return key+'['+','.join(name+'='+value for name,value in sorted(values.items()))+']'


def construct(registry,baseline):
    original=flatten(baseline);blocks=dict(original);changed={};pairs=[]
    protected={tuple(row['pos']) for row in baseline.get('block_entities',[])}
    for station in STATIONS:
        deck=bridge_deck(station)
        for side in (-5,5):
            pair=[]
            for index,y in enumerate((deck-2,deck-1)):
                pos=tuple(world_point((side,y,station),(1248,-1104),1,90))
                if pos in protected or base(original.get(pos,'minecraft:air')) not in MASONRY:
                    raise UserError('Preserve an unreviewed fascia, fixture or non-solid source cell: '+str(pos))
                # Negative-Z face looks north, so its back half rises south;
                # the positive-Z face is the inverse. The inset is external.
                state=native_stair(registry,'south' if side<0 else 'north','bottom' if index==0 else 'top')
                blocks[pos]=changed[pos]=state;pair.append(list(pos))
            pairs.append({'two_cells':pair,'solid_interior_back_half_retained':True,
                          'original_occupied_voxel_envelope_only':True})
    if len(changed)!=20 or set(blocks)!=set(original):raise UserError('Exactly twenty existing occupied fascia cells required')
    if any(blocks[pos]!=state for pos,state in original.items() if pos not in changed):
        raise UserError('A deck, rail, pier, soffit, fixture or water cell changed')
    checks=[require_material_rule(blocks,'complete rose pedestrian crossing, foundations, approaches and garden'),
            require_outdoor_rule(blocks,'complete rose crossing authored outdoor surfaces')]
    return {'original':original,'blocks':blocks,'changed':changed,'pairs':pairs,'material_checks':checks,
            'new_solids_in_air_or_water':0,'moving_mechanism_changes':0,'deck_rails_piers_water_and_soffits_unchanged':True}


def prepare(home,baseline_path,output,checkpoint_id,checkpoint_sha):
    home,baseline_path,output=(Path(value).resolve() for value in (home,baseline_path,output))
    if (output.exists() or not output.is_relative_to(home/'staging')
            or not home.is_relative_to(Path(r'D:\A World for Two\staging\world-tests'))):
        raise UserError('New private artistic-world binding directory required')
    reserve=guard(2*MIB,MAX_OUTPUT)
    if digest(baseline_path)!=BASE_SHA:raise UserError('Exact original placed rose pedestrian crossing required')
    checkpoint=read_json(home/'dashboard/settlement/backup-receipt.json')
    if checkpoint.get('verified') is not True or checkpoint.get('id')!=checkpoint_id or checkpoint.get('sha256')!=checkpoint_sha:
        raise UserError('Exact current verified stopped checkpoint required')
    registry=read_json(home/'dashboard/settlement/registry.json');baseline=read_json(baseline_path)
    if baseline['world_path']!=registry['world_path'] or baseline['seed']!=registry['seed']:
        raise UserError('Rose crossing belongs to another world')
    p=construct(registry,baseline);snapshot=BackupWorld(home,checkpoint,registry)
    try:
        before={pos:snapshot.state(pos) for pos in p['changed']}
        if set(before)&snapshot.protected:raise UserError('A fascia target is an actual saved BE, including default/unwritten state')
        for pos,actual in before.items():
            expected=p['original'][pos]
            if base(actual)!=base(expected) or any(properties(actual).get(k)!=v for k,v in properties(expected).items()):
                raise UserError('Actual saved rose fascia changed; preserve it: '+str((pos,expected,actual)))
        sources=list(snapshot.sources)
    finally:snapshot.close()
    old=payload(baseline,before,checkpoint_sha,'Rose crossing twenty exact before cells VERIFY ONLY')
    old.update(verification_only=True,construction_forbidden=True)
    delta=payload(baseline,p['changed'],checkpoint_sha,'Rose crossing twenty blind fascia recesses DELTA ONLY')
    delta.update(validation='Fresh native before20 pass, then empty-server delta-only placement and after20 verification; no neighboring envelopes modified')
    after=copy.deepcopy(delta);after.update(name='Rose crossing exact twenty after cells VERIFY ONLY',verification_only=True,construction_forbidden=True)
    rollback=copy.deepcopy(old);rollback['name']='Rose crossing exact fascia recovery ONLY - separately reviewed admission required'
    documents={'before.json':old,'delta.json':delta,'after-verification.json':after,'rollback.json':rollback}
    raw={name:encoded(value) for name,value in documents.items()}
    manifest={'format':'awft-rose-crossing-depth-admission:1','source_sha256':digest(Path(__file__)),
              'baseline_sha256':BASE_SHA,'checkpoint_id':checkpoint_id,'checkpoint_sha256':checkpoint_sha,
              'placements':20,'new_solids_in_air_or_water':0,'actual_saved_BEs_targeted_or_replayed':0,
              'deck_stairs_rails_caps_lamps_benches_roses_piers_bed_water_soffits_unchanged':True,
              'normal_pedestrian_junction_and_all_kinetics_untouched':True,'material_checks':p['material_checks'],
              'pairs':p['pairs'],'saved_sources':sources,'reserve_guard':reserve,'comparison_camera':CAMERA,
              'native_actions':False,'files':{name:{'bytes':len(value),'sha256':hashlib.sha256(value).hexdigest()} for name,value in raw.items()},
              'scope':'Fresh native before20/after20 plus actual visual and edge-walking review required; complete bridge3/9 overlay is source evidence, not complete native after verification'}
    raw['manifest.json']=encoded(manifest)
    if sum(map(len,raw.values()))>MAX_OUTPUT:raise UserError('Rose fascia binding exceeds finite allocation')
    output.mkdir(parents=True,exist_ok=False)
    for name,value in raw.items():(output/name).write_bytes(value)
    return {'output':str(output),'placements':20,'files':manifest['files'],'material_checks':p['material_checks']}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('home','baseline-path','output'):parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--checkpoint-id',required=True);parser.add_argument('--checkpoint-sha',required=True)
    print(json.dumps(prepare(**vars(parser.parse_args())),indent=2))
