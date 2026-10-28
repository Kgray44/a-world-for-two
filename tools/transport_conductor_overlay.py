"""Separate, placement-forbidden conductor-fit proposal for the retained carriage.

Reads pinned saved-source and compile-only API bytes. No native command, item,
entity, receipt marker, captured-blaze NBT or existing recovery change is made.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import zipfile

from control_room.common import UserError, digest, utcnow
from tools.artistic_bridge_refinement import flatten
from tools.artistic_quay_prototype import bounded, write_bundle
from tools.playtest import guard
from tools.transport_saved_inputs import verification_plan

MIB = 1024**2
INPUT_SHA = '82a9c6e9a7017720b1f45ab78a8637572065daf001dd57af26f8e4e57d1a413b'
MILL_SHA = '04a48810770f07261be4d24bbbdc8b7b71f24016f1ec51622c3aebb39cf4ce8a'
CREATE_SHA = 'ef87fe5709f1ba1f5b8bb20a2925b5afb4669e178fd6d8bf10c167759eefe37a'
ITEM_CLASS = 'com.simibubi.create.content.processing.burner.BlazeBurnerBlockItem'
API_CLASSES = {
    'com/simibubi/create/content/processing/burner/BlazeBurnerBlockItem.class': 'a1ab9ac6415911bba80b5e9f60f43155eced3addd55dc2a255d5433a8e55ebed',
    'com/simibubi/create/content/processing/burner/BlazeBurnerBlock.class': '4115d690d1c27d2258a2e886a94e28e0598e575bb3fe5041ef387749c866edba',
    'com/simibubi/create/api/behaviour/interaction/ConductorBlockInteractionBehavior$BlazeBurner.class': '8da5f3f20f1361738c995684ab86209ba4960662a59d7aedb89acb9d406f0d5c',
}
CONTROLS = ((1336,72,-993), (1336,72,-985))
BURNERS = ((1336,72,-992), (1336,72,-986))
SEATS = tuple((1336,72,z) for z in (-991,-989,-987))
BOGEYS = ((1336,70,-992), (1336,70,-986))


def verify_api(path):
    path = Path(path)
    if not path.is_file() or path.is_symlink() or not 0 < path.stat().st_size <= 32*MIB or digest(path) != CREATE_SHA:
        raise UserError('Exact pinned Create6.0.10 compile-only API required')
    with zipfile.ZipFile(path) as jar:
        for member, expected in API_CLASSES.items():
            if jar.getinfo(member).file_size > MIB or hashlib.sha256(jar.read(member)).hexdigest() != expected:
                raise UserError('Pinned native filled-burner/conductor API changed')
    return {'jar_sha256': CREATE_SHA, 'class_sha256': API_CLASSES.copy(),
            'static_semantics': 'withBlaze sets native item capturedBlaze=true; placement maps that getter to SMOULDERING; native conductor accepts heat!=NONE',
            'runtime_exercised': False}


def proposal_from_plan(plan, api):
    states = flatten(plan)
    if len(states) != 7941 or plan.get('construction_forbidden') is not True or plan.get('verification_only') is not True:
        raise UserError('The complete placement-forbidden retained7941 source is required')
    before, after = {}, {}
    for p, old, new in zip(CONTROLS, ('north','south'), ('south','north')):
        expected = f'create:controls[facing={old},open=false,virtual=false,waterlogged=false]'
        if states.get(p) != expected:
            raise UserError('Exact retained outward control preimage changed; do not normalize it')
        before[p] = expected
        after[p] = f'create:controls[facing={new},open=false,virtual=false,waterlogged=false]'
    for p, facing in zip(BURNERS, ('north','south')):
        if states.get(p) != 'minecraft:air':
            raise UserError('Conductor target must be exact source AIR; no existing block or BE replacement')
        before[p] = states[p]
        after[p] = f'create:blaze_burner[blaze=smouldering,facing={facing}]'
    preserved = {}
    for p in SEATS:
        if states.get(p) != 'create:blue_seat[waterlogged=false]':
            raise UserError('Preserve all three actual passenger seats')
        preserved[p] = states[p]
    for p in BOGEYS:
        if states.get(p) != 'create:small_bogey[axis=z,waterlogged=false]':
            raise UserError('Preserve both actual bogeys')
        preserved[p] = states[p]
    for burner, control in zip(BURNERS, CONTROLS):
        if burner[:2] != control[:2] or abs(burner[2]-control[2]) != 1:
            raise UserError('A native block conductor must be immediately adjacent to its control')
    registry = {'seed': plan['seed'], 'world_path': plan['world_path']}
    checkpoint = plan['backup_sha256']
    return {
        'format': 'awft-conductor-fit-source-proposal:1', 'created': utcnow(),
        'source_checkpoint_sha256': checkpoint, 'world_write_authority': False,
        'native_actions': 0, 'world_writes': 0, 'material_debits': 0,
        'status': 'SOURCE ONLY; master must obtain genuine fresh native before-state and material proofs',
        'before': verification_plan(registry, before, checkpoint, 'VERIFY ONLY four exact unmodified carriage cells'),
        'after_proposal': verification_plan(registry, after, checkpoint, 'PROPOSAL ONLY controls plus two normally placed filled burner conductors; never generic place'),
        'preserve': verification_plan(registry, preserved, checkpoint, 'VERIFY ONLY three passenger seats and two bogeys; no changes'),
        'material_requirements': {'item': 'create:blaze_burner', 'count': 2, 'native_item_class': ITEM_CLASS,
                                  'native_hasCapturedBlaze_must_be': True, 'per_stack_components_must_be_empty': True,
                                  'empty_blaze_burner_is_valid': False, 'fuel_required_for_conductor_role': False,
                                  'source_stocking_or_entity_capture_authority': False,
                                  'native_inventory_and_real_two_item_debit': 'MANDATORY; no raw captured-blaze/entity/block-entity NBT and no LIFE animal appropriation'},
        'recovery_boundary': {'existing7941_contract_changed': False, 'existing_resume_accepts_overlay': False,
                              'passenger_seats_after': 3, 'native_block_conductors_expected_after': 2,
                              'deployment': 'Finish the original scoped resume first, or author a separately reviewed composite recovery. If already assembled, preserve real train/contents and use explicit ordinary disassembly/reassembly custody; never replay the old assembly intent.'},
        'native_api_evidence': deepcopy(api),
        'required_native_checks': ['Current four-cell exact states, absent BEs at both AIR targets, clear body/boarding corridor and original seats/bogeys',
                                   'Two actual plain filled-burner items; authentic native item class/hasCapturedBlaze getter and whole stock inventory before/after',
                                   'Ordinary native item placement only, genuine material consumption, SMOULDERING state and no invented BE/fuel data',
                                   'Actual reassembled contraption blockConductors in both directions, three seats, two bogeys, real station/graph attachment',
                                   'Boarding and unfueled burner proximity safety, scheduled return/unloading, restart and KG/Sera passenger tests'],
        'acceptance': {key:'PENDING' for key in ('native_presence','travel','multiplayer','restart','performance','visual','owner')},
    }


def qualify_materials(snapshot):
    """Read-only debit proposal from supplied native observations, never authenticity proof."""
    if snapshot.get('format') != 'awft-native-conductor-materials:1' or snapshot.get('native_item_getters_observed') is not True:
        raise UserError('Actual native material class/getter observations required')
    rows = snapshot.get('slots')
    if not isinstance(rows, list) or len(rows) != 27:
        raise UserError('All27 native stock slots/components must be supplied')
    seen, available, selected = set(), 0, []
    for row in rows:
        slot = row.get('slot')
        if type(slot) is not int or not 0 <= slot < 27 or slot in seen or type(row.get('empty')) is not bool:
            raise UserError('Unique explicit native slot identities/emptiness required')
        seen.add(slot)
        if row['empty']:
            if set(row) != {'slot','empty'}:
                raise UserError('Empty native slot must not conceal item data')
            continue
        if type(row.get('count')) is not int or not 0 < row['count'] <= 999 or not isinstance(row.get('components'), dict) or not isinstance(row.get('item'), str):
            raise UserError('Exact real stock counts/components required')
        if row['item'] == 'create:blaze_burner':
            if row.get('native_item_class') != ITEM_CLASS or row.get('has_captured_blaze') is not True or row['components']:
                raise UserError('A genuine plain native filled-burner item is required; item ID/NBT alone is insufficient')
            take = min(2-available, row['count'])
            if take > 0:
                selected.append({'slot':slot, 'count':take})
                available += take
    if available != 2:
        raise UserError('Two genuine filled-burner items are not available; no item generation or entity capture is authorized')
    return {'proposed_debits': selected, 'all27_before_slots': deepcopy(rows),
            'native_debits_performed': 0, 'world_write_authority': False,
            'requirements': 'Master authenticates the supplied native observation, rechecks all27 slots and exact selected stacks immediately before ordinary placement, and proves only these two real debits afterward.'}


def prepare(home, inputs, output=None):
    home, inputs = Path(home).resolve(), Path(inputs).resolve()
    if home.parent != Path(r'D:\A World for Two\staging\world-tests') or inputs.parent != home/'staging':
        raise UserError('Owned immutable construction-source input only')
    manifest = bounded(inputs/'manifest.json')
    if digest(inputs/'manifest.json') != INPUT_SHA:
        raise UserError('Exact authenticated306 retained-inputs-r2 manifest required')
    path = inputs/'mill-current7941-VERIFY-ONLY.json'
    ref = manifest['files']['mill-current7941-VERIFY-ONLY.json']
    if ref['sha256'] != MILL_SHA or path.stat().st_size != ref['bytes'] or digest(path) != MILL_SHA:
        raise UserError('Exact retained7941 source bytes required')
    plan = bounded(path)
    if plan['backup_sha256'] != manifest['checkpoint_sha256']:
        raise UserError('Immutable source checkpoint bindings differ')
    api = verify_api(home/'server/mods/create-1.21.1-6.0.10.jar')
    proposal = proposal_from_plan(plan, api)
    proposal['source_inputs'] = {'manifest_sha256':INPUT_SHA, 'mill_plan_sha256':MILL_SHA,
                                 'checkpoint_id':manifest['checkpoint_id'], 'current_native_preimage':False}
    if len(json.dumps(proposal, separators=(',',':')).encode()) > 128*1024:
        raise UserError('Finite conductor source proposal exceeds128KiB')
    if output is None:
        return proposal
    output = Path(output).resolve()
    if output.parent != home/'staging' or output.exists():
        raise UserError('A new immediate source-only staging directory is required')
    reserve = guard(0, 4*MIB)
    return write_bundle(output, {'conductor-fit-PROPOSAL.json':proposal},
                        {'format':'awft-conductor-fit-source-bundle:1', 'created':utcnow(),
                         'source_sha256':digest(Path(__file__)), 'world_writes':0, 'native_actions':0,
                         'storage_guard':reserve, 'runtime_acceptance':False})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--home', type=Path, required=True)
    parser.add_argument('--inputs', type=Path, required=True)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    print(json.dumps(prepare(args.home, args.inputs, args.output), indent=2))
