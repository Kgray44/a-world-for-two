"""Finite transport plans and arithmetic audits of separately obtained observations.

No native command, write to a save, launch, account action or receipt is generated.
Input completion markers establish file custody, not authentic gameplay by themselves.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path
import re

from control_room.common import UserError

FORMAT = 'awft-native-transport-observation:1'
MILL, ORCHARD = 'Copper Wren Mill', 'Rosewater Orchard Halt'
RECIPES = {'minecraft:wheat', 'create:wheat_flour', 'minecraft:wheat_seeds',
           'minecraft:iron_ingot', 'create:iron_sheet'}
TUBES = ((1312, 71, -1000),) + tuple((1311, 71, z) for z in range(-1000, -1008, -1)) + (
    (1311, 70, -1007), (1311, 69, -1007))
ROLES = frozenset(('starter', 'grain', 'hopper', 'dispatch', 'mill_input',
                   'mill_output', 'chute', 'depot')) | frozenset('tube:'+','.join(map(str, p)) for p in TUBES)
TRANSIT = ROLES - {'starter', 'dispatch', 'mill_output', 'depot'}
ZIPLINE = ((1160,168,-760),(1168,159,-784),(1144,152,-840),(1128,150,-848),
           (1120,147,-864),(1120,146,-880),(1112,142,-920),(1088,132,-968),
           (1064,125,-1008),(1048,116,-1064),(1056,108,-1112),(1048,100,-1176),
           (1048,91,-1232),(1064,86,-1248),(1100,72,-1256))


def _integer(value, low=0, high=1_000_000):
    if type(value) is not int or not low <= value <= high:
        raise UserError('A bounded exact integer is required')
    return value


def _time(value):
    try:
        result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except (TypeError, ValueError, AttributeError) as error:
        raise UserError('An actual timestamp is required') from error
    if result.tzinfo is None:
        raise UserError('Observation timestamps require a time zone')
    return result


def read_observation(path):
    path = Path(path)
    if not path.is_file() or not 0 < path.stat().st_size <= 2*1024**2:
        raise UserError('Finite actual observation JSON required')
    raw = path.read_bytes()
    if len(raw) > 2*1024**2:
        raise UserError('Observation exceeded its bound while reading')
    marker = Path(str(path)+'.complete')
    if not marker.is_file() or marker.stat().st_size != 64 or marker.read_text() != hashlib.sha256(raw).hexdigest():
        raise UserError('Exact immutable native terminal completion marker required')
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise UserError('Duplicate observation keys are ambiguous')
            result[key] = value
        return result
    document = json.loads(raw, object_pairs_hook=unique)
    if not isinstance(document, dict):
        raise UserError('Observation root must be an object')
    return document, hashlib.sha256(raw).hexdigest()


def _context(before, after, *, restart=False, empty=True):
    for observation in (before, after):
        if observation.get('format') != FORMAT or observation.get('world_mutated') is not False or observation.get('owned_tickets') != 0:
            raise UserError('Native observation format and nonmutating collection required')
        if not isinstance(observation.get('players'), list) or empty and observation['players']:
            raise UserError('Coordinated empty-player inventory observations required')
        if not re.fullmatch(r'0\.1\.0-candidate\.\d+', observation.get('candidate', '')) or not re.fullmatch(r'0\.6\.\d+', observation.get('bridge', '')):
            raise UserError('Explicit candidate and bridge identities required')
        if not observation.get('boot_id') or not observation.get('world'):
            raise UserError('Actual JVM observation session and world identity required')
        _integer(observation.get('pid'), 1, 2**32)
        _time(observation.get('process_started'))
    if any(before.get(k) != after.get(k) for k in ('world', 'candidate', 'bridge')):
        raise UserError('Observations belong to different world/artifact identities')
    if _time(after['at']) <= _time(before['at']):
        raise UserError('Ordered observations required')
    if restart == (before['boot_id'] == after['boot_id']):
        raise UserError('A new JVM session is required for restart; one session is required for processing')
    process_same = (before['pid'], before['process_started']) == (after['pid'], after['process_started'])
    if restart == process_same:
        raise UserError('Actual process PID/start identity must change for restart and stay fixed during processing')
    if _integer(after['game_time']) < _integer(before['game_time']):
        raise UserError('Saved game time moved backward')


def _inventory(observation):
    cargo = observation.get('cargo', {})
    if cargo.get('scope') != 'copper_wren_fixed_v1' or cargo.get('complete') is not True or cargo.get('dropped_query_complete') is not True or cargo.get('aliased_transit_objects') is not False:
        raise UserError('Complete declared inventory and dropped-item scope is required')
    stores = cargo.get('stores')
    if not isinstance(stores, list) or len(stores) != len(ROLES):
        raise UserError('Every declared storage and transit location must be present')
    roles, by_role, variants, totals = set(), {}, Counter(), Counter()
    def contents(rows):
        if not isinstance(rows, list) or len(rows) > 54:
            raise UserError('Finite native slot observations required')
        seen, result = set(), Counter()
        for row in rows:
            slot = _integer(row['slot'], 0, 53)
            if slot in seen:
                raise UserError('Duplicate native slot')
            seen.add(slot)
            item, components = row['item'], row['components']
            if not isinstance(item, str) or not re.fullmatch(r'[a-z0-9_.-]+:[a-z0-9_./-]+', item) or not isinstance(components, str) or len(components) > 4096 or type(row.get('plain')) is not bool:
                raise UserError('Exact native item/component identities required')
            count = _integer(row['count'], 1, 999)
            if item in RECIPES and not row['plain']:
                raise UserError('Component-bearing ingredients/products need a separate recipe contract')
            result[item] += count
            variants[item, components, row['plain']] += count
            totals[item] += count
        return result
    for store in stores:
        role = store.get('role')
        if role not in ROLES or role in roles or store.get('available') is not True:
            raise UserError('Missing, duplicate or unavailable native store')
        roles.add(role)
        by_role[role] = contents(store.get('items'))
    dropped = cargo.get('dropped')
    if not isinstance(dropped, list) or len(dropped) > 512:
        raise UserError('Finite complete dropped-item census required')
    entities = set()
    for row in dropped:
        identity = row.get('entity_uuid')
        if not identity or identity in entities:
            raise UserError('Unique actual dropped-item entities required')
        entities.add(identity)
        contents(row.get('items'))
    return totals, variants, by_role, len(dropped)


def reconcile_logistics(before, after, *, equipment_witness=None):
    """Check the pinned recipes and every declared item count, never fixed RNG yield."""
    _context(before, after)
    initial, initial_variants, _, dropped_before = _inventory(before)
    final, final_variants, by_role, dropped_after = _inventory(after)
    delta = Counter({key: final[key]-initial[key] for key in initial.keys() | final.keys()})
    failures = []
    equipment = {}
    if equipment_witness is not None:
        from tools.transport_material_audit import ITEM, document_sha
        witness = equipment_witness
        if (witness.get('format') != 'awft-derived-equipment-debits:1'
            or witness.get('equipment_debits') != {ITEM: 2}
            or witness.get('before_document_sha256') != document_sha(before)
            or witness.get('after_document_sha256') != document_sha(after)
            or any(witness.get(key) != before[key] for key in ('world', 'candidate', 'bridge'))
            or witness.get('process_identity') != {key: before[key] for key in ('pid', 'process_started', 'boot_id')}
            or witness.get('native_actions') != 0 or witness.get('world_writes') != 0
            or witness.get('input_observations_modified') is not False):
            raise UserError('Qualified equipment witness must bind these exact native observations')
        equipment[(ITEM, '{}', True)] = 2
    wheat, flour, seeds = -delta['minecraft:wheat'], delta['create:wheat_flour'], delta['minecraft:wheat_seeds']
    iron, sheets = -delta['minecraft:iron_ingot'], delta['create:iron_sheet']
    if wheat != 16 or iron != 1 or sheets != 1:
        failures.append('Expected genuine consumption of16 wheat and1 ingot, producing1 sheet')
    # Pinned Create wheat recipe: guaranteed1 flour, optional2 extra flour,
    # optional1 seed per wheat. Extra flour must therefore have even parity.
    if not wheat <= flour <= 3*wheat or (flour-wheat) % 2 or not 0 <= seeds <= wheat:
        failures.append('Actual flour/seeds fall outside the pinned stochastic recipe')
    for key in initial_variants.keys() | final_variants.keys():
        if key[0] not in RECIPES and initial_variants[key] - final_variants[key] != equipment.get(key, 0):
            failures.append('Unrelated item/components changed: '+key[0])
    if any(initial_variants[key] - final_variants[key] != amount for key, amount in equipment.items()):
        failures.append('Actual two-item detector installation debit differs from its qualified native custody')
    if any(by_role[role] for role in TRANSIT) or any(row.get('in_transit') is True for row in after['cargo']['stores']):
        failures.append('Actual processing input/transit remains occupied')
    dispatch_delta = by_role['dispatch']['create:wheat_flour'] - _inventory(before)[2]['dispatch']['create:wheat_flour']
    if dispatch_delta != flour or set(by_role['dispatch']) - {'create:wheat_flour'}:
        failures.append('Produced flour did not all reach the filtered dispatch inventory')
    if by_role['depot']['create:iron_sheet'] - _inventory(before)[2]['depot']['create:iron_sheet'] != 1:
        failures.append('The actual press depot did not gain its one sheet')
    if dropped_before or dropped_after:
        failures.append('Dropped goods require explicit reconciliation before a no-loss claim')
    if after['cargo'].get('extractor_filter', {}).get('item') != 'create:wheat_flour':
        failures.append('Native flour filter readback is missing or changed')
    return {'format': 'awft-logistics-arithmetic-audit:1', 'passed': not failures,
            'failures': failures, 'actual_item_deltas': dict(sorted(delta.items())),
            'equipment_installation_debits': equipment_witness,
            'actual_dispatch_flour_delta': dispatch_delta,
            'evidence_scope': 'Arithmetic only. Master must authenticate native capture/artifacts and exclude external item transfers; no transport, multiplayer, performance or owner acceptance.'}


def reconcile_restart(before, after):
    _context(before, after, restart=True)
    initial, variants, _, _ = _inventory(before)
    final, final_variants, _, _ = _inventory(after)
    failures = []
    if variants != final_variants:
        failures.append('Inventory item/component totals differ after the new JVM session')
    def trains(observation):
        rows = observation.get('trains', [])
        result = {row['uuid']: row for row in rows}
        if len(result) != len(rows):
            raise UserError('Duplicate native train identity is ambiguous')
        return result
    before_trains, after_trains = trains(before), trains(after)
    if not before_trains or before_trains.keys() != after_trains.keys():
        failures.append('Actual train UUID set is absent or changed')
    for identity in before_trains.keys() & after_trains.keys():
        for field in ('graph_id', 'carriages', 'seats', 'double_ended', 'schedule_present', 'schedule_cyclic',
                      'schedule_entry', 'schedule_paused', 'schedule_completed', 'native_schedule_snbt',
                      'schedule_condition_progress', 'schedule_condition_context',
                      'forward_conductor', 'backward_conductor'):
            if before_trains[identity].get(field) != after_trains[identity].get(field):
                failures.append('Retained train field differs: '+field)
        for snapshot in (before_trains[identity], after_trains[identity]):
            speed=snapshot.get('speed')
            if not snapshot.get('graph_id') or type(speed) not in (int,float) or not math.isfinite(speed) or abs(speed)>.001:
                failures.append('Parked restart comparison needs the actual graph and stationary speed')
            if snapshot.get('schedule_present') is True and (not snapshot.get('native_schedule_snbt') or any(
                    snapshot.get(field) is None for field in ('schedule_entry','schedule_paused','schedule_completed',
                        'schedule_condition_progress','schedule_condition_context'))):
                failures.append('Actual native schedule content/progress witness missing')
        if after_trains[identity].get('invalid') is not False or after_trains[identity].get('derailed') is not False:
            failures.append('Actual reloaded train is invalid or derailed')
    def links(observation):
        rows = observation.get('tube_links', [])
        if len(rows) != 6 or len({row.get('uuid') for row in rows}) != 6 or any(
            row.get('stored_reciprocal') is not True or not row.get('uuid')
            or row.get('from') != [1331,71,-991+8*n] or row.get('to') != [1331,71,-983+8*n]
            or row.get('distance') != 8 for n, row in enumerate(rows)):
            raise UserError('All six actual stored reciprocal links are required')
        return [(row['uuid'], row['from'], row['to'], row.get('distance')) for row in rows]
    if links(before) != links(after):
        failures.append('Native stored tube-link identity/endpoints differ')
    for observation in (before, after):
        if observation.get('track_graph', {}).get('status') != 'station_nodes_connected':
            failures.append('Native station graph continuity not observed')
        stations = observation.get('stations', [])
        if len(stations) != 2 or len({row.get('station_uuid') for row in stations}) != 2 or [row.get('position') for row in stations] != [[1332,71,-994],[1332,71,-942]] or [row.get('name') for row in stations] != [MILL,ORCHARD] or any(not row.get('station_uuid') or row.get('station_point') is not True or row.get('valid_track') is not True for row in stations):
            failures.append('Both native named station attachments are required')
    if before.get('stations') != after.get('stations'):
        failures.append('Native station snapshot changed; inspect attachment/names/train presence')
    return {'format': 'awft-transport-restart-comparison:1', 'passed': not failures,
            'failures': failures, 'item_totals_before': dict(initial), 'item_totals_after': dict(final),
            'evidence_scope': 'Observed identity/count persistence only. Real riding, filler collision shapes, zipline tracking, clean stop/start provenance and safe arrival need separate proof.'}


def construction_contract():
    changes = []
    for z, old, new in ((-993, 'north', 'south'), (-985, 'south', 'north')):
        changes.append({'position': [1336, 72, z], 'expected_block': 'create:controls',
                        'expected_facing': old, 'proposed_facing': new})
    for z, facing in ((-992, 'north'), (-986, 'south')):
        changes.append({'position': [1336, 72, z], 'expected_block': 'minecraft:air',
                        'proposed_block': 'create:blaze_burner',
                        'proposed_properties': {'blaze': 'smouldering', 'facing': facing}})
    return {'format': 'awft-transport-construction-contract:1', 'world_write_authority': False,
            'status': 'PROPOSED; exact current native preimage and a new composite recovery/assembly contract required',
            'railway': {'mill_station': [1332,71,-994], 'orchard_station': [1332,71,-942],
                        'track_start': [1336,69,-997], 'track_end': [1336,69,-936], 'track_blocks': 62,
                        'station_names': [MILL, ORCHARD], 'conductor_overlay': changes,
                        'conductor_inputs': 'Two genuine plain filled create:blaze_burner items; native item class/hasCapturedBlaze getter and actual two-item debit required. No LIFE actors, captured-blaze NBT or synthetic passengers.',
                        'retained_passenger_seats': [[1336,72,z] for z in (-991,-989,-987)],
                        'scheduled_operation': 'Finite mill/orchard/mill round trip;20second dwell AND1or2 seated players; final zero-player unloading; noncyclic'},
            'hypertube': {'entrances': [[1331,71,-991],[1331,71,-943]],
                          'retained_links': 6, 'retained_filler_cells': 42, 'minimum_native_rpm': 16,
                          'entry': 'WEST input detectors plus actual levers; manual/sneak mode is not emergency stop'},
            'logistics': {'stop_lever': [1310,70,-999], 'starter': [1313,68,-994],
                          'grain': [1315,74,-1000], 'millstone': [1315,71,-1000],
                          'pump': [1313,71,-1000], 'extractor': [1314,71,-1000],
                          'dispatch': [1311,68,-1008], 'press': [1320,70,-1000], 'depot': [1320,68,-1000],
                          'chunk_crossing': 'Pneumatic tube crosses X1312 from chunk82 to81',
                          'recipe': '16wheat produces16..48flour with even excess,0..16seeds;1iron ingot produces1iron sheet'},
            'zipline': {'knots': ZIPLINE, 'native_links_required': 14, 'existing_stock_barrel': [1101,65,-1257],
                        'native_range': 96, 'slack': 16, 'rider_hang': 3.5,
                        'preserve': 'Existing frames/barrel, historical BEFORE ownership, all actual current joins/oxidation, saved FULL5x5neighborhood gate'},
            'acceptance': {key: 'PENDING' for key in ('runtime', 'visual', 'multiplayer', 'restart', 'official_integration', 'owner')},
            'native_actions': 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('plan', 'logistics', 'restart'))
    parser.add_argument('--before', type=Path)
    parser.add_argument('--after', type=Path)
    parser.add_argument('--home', type=Path, help='Owned native home for an optional genuine mill-resume equipment audit')
    parser.add_argument('--native-resume', type=Path, help='Actual successful native mill-resume terminal; never a proposed witness')
    parser.add_argument('--bridge-jar-sha256', help='Master-authenticated deployed bridge digest for the equipment audit')
    args = parser.parse_args()
    if args.operation == 'plan':
        result = construction_contract()
    else:
        if not args.before or not args.after:
            parser.error('Both actual native observation paths are required')
        before, before_sha = read_observation(args.before)
        after, after_sha = read_observation(args.after)
        extra = (args.home, args.native_resume, args.bridge_jar_sha256)
        if any(extra) and (args.operation != 'logistics' or not all(extra)):
            parser.error('Equipment audit requires logistics plus --home, --native-resume and --bridge-jar-sha256 together')
        witness = None
        if all(extra):
            from tools.transport_material_audit import derive_equipment_debits
            witness = derive_equipment_debits(args.home, args.before, args.after, args.native_resume,
                                             expected_bridge_sha256=args.bridge_jar_sha256)
            if witness['before_sha256'] != before_sha or witness['after_sha256'] != after_sha:
                raise UserError('Native observation bytes changed during equipment qualification')
        result = (reconcile_logistics(before, after, equipment_witness=witness)
                  if args.operation == 'logistics' else reconcile_restart(before, after))
        result.update(before_sha256=before_sha, after_sha256=after_sha)
    print(json.dumps(result, indent=2))
    return 0 if result.get('passed', True) else 1


if __name__ == '__main__':
    raise SystemExit(main())
