"""Two ordinary Lark supports and a separately dependent prospective Wren ladder.

This module only reads the exact verified6ad3a8 archive and writes private source
proposals. It never connects to Minecraft, writes a save or replays inventories.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
from pathlib import Path

from control_room.common import UserError, digest, read_json
from tools.artistic_ship import ArtisticShip, SEAL_BLOCKS
from tools.grand_harbor_fleet import AIR, canonical, identifier
from tools.grand_harbor_berth import (
    HOME, CHECKPOINT, CHECKPOINT_SHA, checked_checkpoint, native_plan, rotate_point, rotated_state,
)
from tools.playtest import guard
from tools.settlement_attractions import BackupWorld


HELPER_SHA = 'f61f45913a9d60846bdd6a9d04e6f4a049cfdd0129f1a3d6fc2fec4612cc7984'
FLEET_SHA = 'fe4251af7c032257e15f90a428defb5c523bb51fea8bd09a37db43066958119a'
REGISTRY_SHA = '8cfa5ae77e20b8b5c1730b2928c55156557ebecb7e84480142088bda04ef92c4'
REGISTRY_SOURCE = 'staging/fleet-registry-provenance-8cfa5ae7/registry-original.json'
WREN_SOURCE = 'staging/fleet-berth-wren-169d2faf9ba9224f'
WREN_MANIFEST_SHA = '35a1f45207d4b1bef6581b48fb7eb832ed462bc772d9ca893fe755f82e8a69b7'
WREN_AFTER_SHA = '2064645686e03e530d04ba66be8c3074e2617769155bdae5b0dcaca0917d3229'
MAX_OUTPUT = 8*1024**2
TIMBER = 'chipped:stacked_dark_oak_planks'
WHEEL = (1140, 80, -1425)
WHEEL_STATE = 'create:copper_valve_handle[facing=south,waterlogged=false]'
LARK_DECK = (1140, 78, -1426)
LARK_TARGETS = ((1140, 79, -1426), (1140, 80, -1426))
WREN_ORIGIN, WREN_ROTATION = (1000, 63, -1366), 1
WREN_BACKING = (17, 0, 0)
WREN_LADDERS = ((18, 0, 0), (18, 1, 0))
WREN_PLATFORM = (17, 1, 0)
WREN_CLEARANCE = ((18, -1, 0), (18, 2, 0), (18, 3, 0), (17, 2, 0), (17, 3, 0))


def sha(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def states(document):
    if document.get('format') != 'awft-native-settlement:1':
        raise UserError('Exact native source plan required')
    return {tuple(row[:3]): document['palette'][row[3]] for row in document['blocks']}


def saved_state(snapshot, pos):
    value = snapshot.state(pos)
    if value is None:
        raise UserError('Unknown saved access target is never AIR: '+str(pos))
    return value


def build_lark_repair(registry, snapshot, receipt):
    checked_checkpoint(receipt)
    before = {p: saved_state(snapshot, p) for p in (*LARK_TARGETS, LARK_DECK, WHEEL)}
    if before[WHEEL] != WHEEL_STATE or WHEEL not in snapshot.protected:
        raise UserError('Saved Lark wheel state/existing block entity differs; preserve and re-inspect')
    if before[LARK_DECK] != TIMBER:
        raise UserError('Exact connected Lark supporting deck changed')
    for pos in LARK_TARGETS:
        if before[pos] != AIR or pos in snapshot.protected:
            raise UserError('Lark support target is occupied or a block entity: '+str(pos))
    timber = ArtisticShip(registry, (0, 0, 0), 0).state(TIMBER)
    delta = {p: timber for p in LARK_TARGETS}
    return {
        'before': native_plan(registry, before, 'Lark two ordinary supports exact saved BEFORE VERIFY ONLY'),
        'support': native_plan(registry, {LARK_DECK: before[LARK_DECK], WHEEL: before[WHEEL]}, 'Lark retained deck and wheel VERIFY ONLY'),
        'placement': native_plan(registry, delta, 'Lark two ordinary timber support blocks', verify=False),
        'after': native_plan(registry, before | delta, 'Lark connected wheel supports AFTER VERIFY ONLY'),
        'scope': {'ordinary_blocks_added': 2, 'targets': [list(p) for p in LARK_TARGETS],
                  'existing_wheel': list(WHEEL), 'wheel_BE_present_in_saved_chunk': True,
                  'wheel_BE_writes': 0, 'tags_supplied': 0,
                  'native_BE_before_after': 'Master must read the actual existing wheel BE/config before and after. Preserve all fields/inventories; no source tag or inventory replay.',
                  'behavior': 'Uncommissioned architectural wheel; no steering claim',
                  'authority': None},
    }


def build_wren_request(registry, snapshot, receipt, old_after):
    checked_checkpoint(receipt)
    if (old_after.get('backup_sha256') != CHECKPOINT_SHA or old_after.get('commands') != [] or
            old_after.get('world_path') != registry['world_path'] or str(old_after.get('seed')) != str(registry['seed'])):
        raise UserError('Wren dependency belongs to another checkpoint/world or includes commands')
    tags = deepcopy(old_after.get('block_entities', []))
    if len(tags) != 9 or len({tuple(row['pos']) for row in tags}) != 9:
        raise UserError('Exact nine existing Wren block entities required')
    old = states(old_after)
    tag_positions = {tuple(row['pos']) for row in tags}
    transform = lambda pos: rotate_point(pos, WREN_ORIGIN, WREN_ROTATION)
    targets = {transform(WREN_BACKING), *(transform(p) for p in WREN_LADDERS)}
    if targets & tag_positions:
        raise UserError('Prospective ladder would touch existing Wren block entity/inventory')
    for local in (*WREN_LADDERS, WREN_PLATFORM, *WREN_CLEARANCE):
        pos = transform(local)
        if pos in tag_positions:
            raise UserError('Access geometry must preserve all existing Wren block entities')
    # Read every required cell absent from the old fullAFTER from the real archive.
    # Existing source hull cells are prospective and never claimed current.
    needed = targets | {transform(p) for p in (WREN_PLATFORM, *WREN_CLEARANCE)}
    new_current = {p: saved_state(snapshot, p) for p in sorted(needed-old.keys())}
    for pos, value in new_current.items():
        if value != AIR or pos in snapshot.protected:
            raise UserError('New ladder cell/clearance outside Wren fullAFTER is occupied/BE: '+str(pos))
    prospective_before = old | new_current
    for pos in targets:
        if prospective_before[pos] != AIR:
            raise UserError('Prospective Wren ladder target is occupied: '+str(pos))
    platform = transform(WREN_PLATFORM)
    if identifier(prospective_before[platform]) not in SEAL_BLOCKS:
        raise UserError('Wren platform must provide existing full timber backing')
    for local in WREN_CLEARANCE:
        pos = transform(local)
        required = 'minecraft:water[level=0]' if local[1] < 0 else AIR
        if prospective_before[pos] != required:
            raise UserError('Prospective ladder water/headroom/exit clearance differs: '+str(pos))
    timber = ArtisticShip(registry, (0, 0, 0), 0).state(TIMBER)
    ladder = rotated_state('minecraft:ladder[facing=east,waterlogged=false]', registry, WREN_ROTATION)
    delta = {transform(WREN_BACKING): timber}
    delta.update({transform(pos): ladder for pos in WREN_LADDERS})
    updated = prospective_before | delta
    for local in WREN_LADDERS:
        pos = transform(local)
        # South-facing world ladder needs collision directly to its north.
        backing = pos[0], pos[1], pos[2]-1
        if identifier(updated[backing]) not in SEAL_BLOCKS:
            raise UserError('Prospective ladder lacks connected full-block backing')
    dependency = {
        'manifest_source': WREN_SOURCE+'/manifest.json', 'manifest_sha256': WREN_MANIFEST_SHA,
        'old_full_after_sha256': WREN_AFTER_SHA, 'checkpoint_sha256': CHECKPOINT_SHA,
        'authoritative_native_completion': None,
        'requires': 'Master actual Wren placement/settle/fullAFTER native verification, then actual current access targets/BE inventory reads and a current exclusive lease. A prospective template is not a completion receipt.',
    }
    request = {
        'format': 'awft-prospective-access-request:1', 'name': 'Wren water-return ladder',
        'execution_forbidden': True, 'construction_forbidden': True, 'authority': None,
        'dependency': dependency, 'delta': [{'pos': list(p), 'state': state} for p, state in sorted(delta.items())],
        'commands': [], 'block_entities': [], 'entities': [], 'UUIDs': [],
        'requires_authoritative_derivation': 'No executable PLACE emitted. Master may derive only the three ordinary-block states after dependency/current preimages/BE checks pass; preserve all nine existing BE inventories without replay.',
        'old_probe_change': 'Two ladder cells consume old AIR clearance. Verify old fullAFTER before this addon; afterward use the updated fullAFTER instead.',
        'native_boat_boarding': 'UNVERIFIED; source ladder backing/headroom is not actual player or boat acceptance',
    }
    after = native_plan(registry, updated, 'PROSPECTIVE Wren ladder updated fullAFTER VERIFY ONLY', tags=tags)
    before_plan = native_plan(registry, prospective_before, 'PROSPECTIVE Wren ladder fullBEFORE VERIFY ONLY', tags=tags)
    before_plan['prospective_dependency'] = dependency
    after['prospective_dependency'] = dependency
    if before_plan['block_entities'] != tags or after['block_entities'] != tags or delta.keys() & tag_positions:
        raise UserError('Existing Wren block entity tags must remain unchanged')
    return {
        'request': request, 'before': before_plan, 'after': after,
        'new_current': native_plan(registry, new_current, 'Wren new outside-template cells actual6ad3a8 VERIFY ONLY'),
        'support': native_plan(registry, {p: prospective_before[p] for p in needed-targets}, 'PROSPECTIVE Wren platform water and headroom VERIFY ONLY'),
        'scope': {'ordinary_blocks_requested': 3, 'world_delta_positions': [list(p) for p in sorted(delta)],
                  'new_actual_saved_cells_read': len(new_current), 'existing_Wren_BEs_preserved': 9,
                  'existing_BE_tags_sha256': sha(tags), 'prospective_after_BE_tags_sha256': sha(after['block_entities']),
                  'existing_BE_writes': 0, 'executable_placement_emitted': False,
                  'actual_Wren_hull_currently_present': 'NOT ASSERTED', 'native_acceptance': 'UNVERIFIED'},
    }


def prepare(home=HOME, output=None):
    home = Path(home).resolve()
    if home != HOME.resolve():
        raise UserError('Access proposals bind only the existing construction home')
    pins = {'grand_harbor_berth.py': HELPER_SHA, 'grand_harbor_fleet.py': FLEET_SHA}
    for name, pin in pins.items():
        if digest(Path(__file__).with_name(name)) != pin:
            raise UserError('Frozen access helper/source changed')
    receipt = read_json(home/'dashboard/settlement/backup-receipt.json', {})
    checked_checkpoint(receipt)
    reg_path = home/REGISTRY_SOURCE
    if digest(reg_path) != REGISTRY_SHA:
        raise UserError('Historical registry source changed')
    registry = read_json(reg_path)
    folder = home/WREN_SOURCE
    if digest(folder/'manifest.json') != WREN_MANIFEST_SHA or digest(folder/'complete-after-VERIFY-ONLY.json') != WREN_AFTER_SHA:
        raise UserError('Exact approved Wren dependency source changed')
    old_after = read_json(folder/'complete-after-VERIFY-ONLY.json')
    snapshot = BackupWorld(home, receipt, registry)
    try:
        lark = build_lark_repair(registry, snapshot, receipt)
        wren = build_wren_request(registry, snapshot, receipt, old_after)
        sources = snapshot.sources[:]
    finally:
        snapshot.close()
    checked_checkpoint(read_json(home/'dashboard/settlement/backup-receipt.json', {}))
    files = {
        'lark/current-before-VERIFY-ONLY.json': canonical(lark['before']),
        'lark/retained-support-VERIFY-ONLY.json': canonical(lark['support']),
        'lark/two-ordinary-blocks-placement.json': canonical(lark['placement']),
        'lark/complete-after-VERIFY-ONLY.json': canonical(lark['after']),
        'wren/prospective-request-NONEXECUTABLE.json': canonical(wren['request']),
        'wren/current-new-original-cells-VERIFY-ONLY.json': canonical(wren['new_current']),
        'wren/prospective-full-before-VERIFY-ONLY.json': canonical(wren['before']),
        'wren/prospective-support-VERIFY-ONLY.json': canonical(wren['support']),
        'wren/prospective-updated-full-after-VERIFY-ONLY.json': canonical(wren['after']),
    }
    manifest = {
        'format': 'awft-fleet-access-repairs:1', 'checkpoint_id': CHECKPOINT, 'checkpoint_sha256': CHECKPOINT_SHA,
        'source_sha256': digest(Path(__file__)), 'imported_source_hashes': pins,
        'historical_registry_sha256': REGISTRY_SHA,
        'registry_status': 'Historical bridge0.6.29 property export; actual current native palette proof pending master',
        'lark_scope': lark['scope'], 'wren_prospective_scope': wren['scope'], 'wren_dependency': wren['request']['dependency'],
        'saved_region_sources': sources,
        'files': {name: {'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)} for name, raw in files.items()},
        'native_calls': 0, 'world_writes': 0, 'BE_or_inventory_writes': 0,
        'status': 'SOURCE PROPOSALS ONLY; Lark native BEFORE/BE preservation/lease required; Wren additionally depends on actual complete placement/full verification',
        'actual_controls_boat_access_multiplayer_restart': 'UNVERIFIED',
        'storage_monitoring': '30GiB separately on both drives; this monitoring does not constrain external applications or existing writers',
    }
    identity = sha(manifest)
    output = Path(output).resolve() if output else home/'staging'/('fleet-access-'+identity[:16])
    if output.exists() or not output.is_relative_to(home/'staging') or not output.name.startswith('fleet-access-'):
        raise UserError('A unique owned fleet-access output is required')
    files['manifest.json'] = canonical(manifest)
    if sum(map(len, files.values())) > MAX_OUTPUT:
        raise UserError('Access source bundle exceeds8MiB allocation')
    guard(0, MAX_OUTPUT)
    output.mkdir(parents=True, exist_ok=False)
    for name, raw in files.items():
        path = output/name
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as stream:
            stream.write(raw)
    return {'directory': str(output), 'manifest_sha256': digest(output/'manifest.json'),
            'bytes': sum(map(len, files.values())), 'lark_scope': lark['scope'],
            'wren_prospective_scope': wren['scope'], 'native_calls': 0, 'world_writes': 0}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--home', type=Path, default=HOME)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    import json
    print(json.dumps(prepare(args.home, args.output)))
