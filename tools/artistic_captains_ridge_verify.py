"""Additive verification-only native Macaw end joins; never replay the hall."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import time
import zipfile

from control_room.common import UserError, digest, read_json
from tools.artistic_bridge_refinement import encoded, flatten
from tools.artistic_maritime_depth import admit_owner
from tools.artistic_neighborhood_roofs import PINNED_JAR, PINNED_SHA, derive
from tools.playtest import guard
from tools.settlement_attractions import BackupWorld, base


MIB = 1024**2
FULL = 'staging/artistic-captains-rest-1793170982583234800/captains-rest-complete-VERIFY-ONLY.json'
FULL_SHA = 'ffe9498d2b71d4d2ea96e70dac4823b3ca7ef3ed84b8a4d0eab3fdf8c161536f'
FAILURE = 'dashboard/settlement/settlement-result-b015c2f1-cee6-4b50-b3fb-428d94257c16.json'
ROOF = 'mcwroofs:orange_terracotta_top_roof'
EXPECTED = {(1042,79,-1294): 'top_end_180', (1042,79,-1280): 'top_end_0'}


def canonical(registry, original, saved_state):
    field = flatten(original)
    outside = {}
    for (x,y,z), value in field.items():
        if base(value) != ROOF:
            continue
        for p in ((x,y,z-1),(x+1,y,z),(x,y,z+1),(x-1,y,z)):
            if p not in field:
                native = saved_state(p)
                if native is None or base(native) == ROOF:
                    raise UserError('An unwritten native same-roof neighbor needs separate exact custody; never infer AIR')
                outside[p] = native
    corrected, changes, ridges = derive(registry, original)
    actual = {tuple(row['position']): row['after'] for row in changes}
    wanted = {p: ROOF + '[part=' + value + ']' for p,value in EXPECTED.items()}
    if actual != wanted or len(ridges) != 15:
        raise UserError('Only the two independently derived ends of the original fifteen-cell ridge may differ')
    # Native generic derive adds verification_only. Preserve every original
    # metadata field byte-for-value as well; construction_forbidden was true.
    if 'verification_only' not in original:
        corrected.pop('verification_only',None)
    for name in set(original) - {'palette','blocks'}:
        if corrected.get(name) != original[name]:
            raise UserError('Ridge expectations cannot alter original metadata, commands or block-entity tags')
    return corrected, changes, outside


def prepare(home, checkpoint_id, checkpoint_sha):
    home=Path(home).resolve()
    if home.parent != Path('D:/A World for Two/staging/world-tests').resolve():
        raise UserError('The exact owned artistic home is required')
    reserve=guard(MIB,4*MIB)
    receipt=read_json(home/'dashboard/settlement/backup-receipt.json',{})
    admit_owner(home,read_json(home/'dashboard/artistic-owner.json',{}),receipt,checkpoint_id,checkpoint_sha)
    source=home/FULL
    if source.stat().st_size>2*MIB or digest(source)!=FULL_SHA:
        raise UserError('Preserve the exact original 3984-cell full source')
    original=read_json(source)
    if len(original['blocks'])!=3984 or original.get('construction_forbidden') is not True or original['backup_sha256']!=checkpoint_sha:
        raise UserError('Exact current verification-only source/checkpoint is required')
    registry=read_json(home/'dashboard/settlement/registry.json')
    if any(str(original[k])!=str(registry[k]) for k in ('seed','world_path')):
        raise UserError('The original hall belongs to another world')
    jar=home/'server/mods'/PINNED_JAR
    if not jar.is_file() or jar.stat().st_size>32*MIB or digest(jar)!=PINNED_SHA:
        raise UserError('Exact pinned native Macaw roof API required')
    with zipfile.ZipFile(jar) as archive:
        native=archive.read('com/mcwroofs/kikoz/objects/roofs/RoofTopNew.class')
    failure=read_json(home/FAILURE)
    if failure.get('operation')!='verify' or failure.get('plan_sha256')!=FULL_SHA or failure.get('blocks')!=3984 or failure.get('failures')!=2:
        raise UserError('Retain and bind the exact original two-difference native receipt')
    snapshot=BackupWorld(home,receipt,registry)
    try:
        corrected,changes,context=canonical(registry,original,snapshot.state)
        raw=encoded(corrected)
        report={'format':'awft-captains-rest-native-ridge-verification:1','source_sha256':digest(Path(__file__)),
            'checkpoint_id':checkpoint_id,'checkpoint_sha256':checkpoint_sha,'original_full_sha256':FULL_SHA,
            'failed_native_receipt':{'path':FAILURE,'sha256':digest(home/FAILURE)},
            'native_algorithm':{'jar':PINNED_JAR,'sha256':PINNED_SHA,'class':'com.mcwroofs.kikoz.objects.roofs.RoofTopNew',
                'class_sha256':hashlib.sha256(native).hexdigest(),'methods':['StairState','getRoofPart','updateShape','onPlace'],
                'basis':'Native StairState tests SAME block identity at N/E/S/W, same Y. South-only=>top_end_180, north-only=>top_end_0; NS=>switched_0. Source graph plus exact saved unwritten-neighbor context, not failure fitting.'},
            'changes':changes,'unchanged_block_positions_and_IDs':3984,'unchanged_original_block_entity_rows':len(original['block_entities']),
            'unwritten_neighbors':[{'pos':list(p),'saved_state':s} for p,s in sorted(context.items())],
            'native_actions':0,'placement_or_settle_actions':0,'world_inventory_or_geometry_writes':0,
            'required_next':'Parent verifies this NEW full construction-forbidden plan only. Never replay the already placed original proposal.',
            'reserve_guard':reserve,'files':{'captains-rest-native-ridges-FULL-VERIFY-ONLY.json':{'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}}}
        output=home/'staging'/('captains-rest-ridge-verification-'+str(time.time_ns()));output.mkdir()
        (output/'captains-rest-native-ridges-FULL-VERIFY-ONLY.json').write_bytes(raw)
        (output/'derivation.json').write_bytes(encoded(report))
        return {'directory':str(output),'derivation_sha256':digest(output/'derivation.json'),'files':report['files'],'changes':changes}
    finally:
        snapshot.close()


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--home',type=Path,required=True)
    p.add_argument('--checkpoint-id',required=True);p.add_argument('--checkpoint-sha',required=True);a=p.parse_args()
    print(json.dumps(prepare(a.home,a.checkpoint_id,a.checkpoint_sha),indent=2))
