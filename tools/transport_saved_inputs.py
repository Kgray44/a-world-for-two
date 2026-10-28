"""Requalify historical cable body custody and current retained transport inputs.

Only authenticated immutable ZIP members are read. New verification-only source
files go in one immediate H/staging directory. No request, command, native marker,
world, stock, installed configuration or original evidence is changed.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import time

from control_room.common import REPO, UserError, digest, read_json, utcnow
from tools.artistic_bridge_refinement import flatten
from tools.artistic_chain_route_request_r4 import chunk_document
from tools.artistic_north_bank_east import native_payload
from tools.artistic_quay_prototype import bounded, context, write_bundle
from tools.artistic_south_extent import ExtentTerrain
from tools.artistic_south_forest import AIR
from tools.artistic_zipline_catenary import reader_budget, swept_cells
from tools.artistic_zipline_west import CURVES, CURVES_SHA, HANG, NODES, occupied_cells
from tools.artistic_zipline_west_bind_e55 import BASE, GEOMETRY_SHA, MANIFEST_SHA, geometry_digest
from tools.playtest import guard

MIB = 1024**2
HISTORICAL_ID = '20261028T043630Z-e55a8c'
HISTORICAL_SHA = '4384206f639659b09b2d332d2eb058241ca6dc15298f3808745025ed85992fac'
ORIGINAL = 'staging/zipline-west-v2-current-binding-1793166231186395300'
BEFORE_SHA = '685137925d45cfa4b19ada1d2b83803665f2870569c548f6801f158c25d08e6c'
MILL_SOURCES = ('staging/artistic-mill-orientation-r3-20261027T1510Z/mill-quarter.json',
                'staging/artistic-mill-r3-native-joined-20261027T1716Z/mill-detail-native-verify-only.json',
                'staging/artistic-depth-castle-mill-20261027T1900Z/mill-depth.json')
MILL_MANIFEST = 'staging/artistic-mill-orientation-r3-20261027T1510Z/manifest.json'


def _member(folder, manifest, name):
    row = manifest['files'][name]
    path = folder/name
    document = bounded(path, 2*MIB)
    if path.stat().st_size != row['bytes'] or digest(path) != row['sha256']:
        raise UserError('Original frozen source member changed: '+name)
    return document


def _inventory(terrain, position, expected):
    state = terrain.state(*position)
    if state is None or state.split('[', 1)[0] != expected:
        raise UserError('Actual saved stock container differs')
    x, _, z = position
    raw = terrain.snapshot.regions[(x//16//32, z//16//32)]
    doc, chunk_sha = chunk_document(raw, x//16, z//16)
    matches = [row for row in doc.get('block_entities', [])
               if (row.get('x'), row.get('y'), row.get('z')) == position]
    if len(matches) != 1 or matches[0].get('id') != expected:
        raise UserError('Exact saved container BE required')
    be = matches[0]
    if be.get('LootTable'):
        raise UserError('Unresolved loot is not an empty native inventory')
    rows = be.get('Items', [])
    if not isinstance(rows, list) or len(rows) > 27:
        raise UserError('Bounded single-container saved slots required')
    slots = {n: None for n in range(27)}
    for row in rows:
        slot = row.get('Slot')
        if type(slot) is not int or not 0 <= slot < 27 or slots[slot] is not None or type(row.get('count')) is not int or row['count'] < 1:
            raise UserError('Ambiguous saved inventory slot/count')
        slots[slot] = copy.deepcopy(row)
    return {'position': list(position), 'state': state, 'saved_chunk_nbt_sha256': chunk_sha,
            'slots': [{'slot': slot, 'saved_item_nbt': item} for slot, item in slots.items()],
            'scope': 'Actual saved NBT only; fresh full-slot/component native readback is mandatory before any stock/debit operation'}


def _mill_contract():
    path = REPO/'compat/control-bridge/proposals/mill-resume/contract.py'
    spec = importlib.util.spec_from_file_location('transport_retained_mill_contract', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def verification_plan(registry, states, checkpoint_sha, name):
    plan = native_payload(registry, states, checkpoint_sha, name)
    plan.update(construction_forbidden=True, verification_only=True)
    return plan


def complete_body(body, baseline, actual):
    return all(len(scan['body']) == len(body) == 5607 and not any(
        scan[field] for field in ('blocked', 'unknown', 'frame_intersections'))
        for scan in (baseline, actual))


def prepare(home, output, checkpoint_id, checkpoint_sha):
    reserve = guard(4*MIB, 16*MIB)
    home, output, current, registry = context(home, output)
    if (current['id'], current['sha256']) != (checkpoint_id, checkpoint_sha) or 'stopped' not in current.get('scope', '').lower():
        raise UserError('Explicit current verified STOPPED source checkpoint required')
    started = time.monotonic()
    base = home/BASE
    if digest(base/'manifest.json') != MANIFEST_SHA:
        raise UserError('Exact original western source manifest required')
    source_manifest = bounded(base/'manifest.json')
    roles = _member(base, source_manifest, 'source-roles-and-config.json')
    geometry = {}
    for component, expected_sha in roles['component_geometry_sha256'].items():
        values = flatten(_member(base, source_manifest, component+'-DELTA.json'))
        if geometry_digest(values) != expected_sha or geometry.keys() & values.keys():
            raise UserError('Original disjoint physical geometry changed')
        geometry.update(values)
    if len(geometry) != 1163 or geometry_digest(geometry) != GEOMETRY_SHA:
        raise UserError('Exact1163 original frame/station/barrel targets required')
    original_before_path = home/ORIGINAL/'physical1163-before-VERIFY-ONLY.json'
    if digest(original_before_path) != BEFORE_SHA:
        raise UserError('Genuine e55 historical pre-build target identity changed')
    original_before = bounded(original_before_path)
    if original_before.get('backup_sha256') != HISTORICAL_SHA or set(flatten(original_before)) != set(geometry):
        raise UserError('Original BEFORE baseline/target set differs')
    curves_folder = home/CURVES
    if digest(curves_folder/'manifest.json') != CURVES_SHA:
        raise UserError('Exact original native-binary curve manifest required')
    curve_manifest = bounded(curves_folder/'manifest.json')
    if curve_manifest.get('nodes') != [list(p) for p in NODES] or curve_manifest.get('hang_offset_proposed') != HANG:
        raise UserError('Pinned actual curve endpoints/hanging offset differ')
    segments = _member(curves_folder, curve_manifest, 'all-native-curves.json')['segments']
    if len(segments) != 14:
        raise UserError('All14 native curve samples required')
    segment_cells = [swept_cells(row['points'], HANG) for row in segments]
    body = set().union(*segment_cells)
    if len(body) != 5607 or body & occupied_cells(geometry):
        raise UserError('Exact conservative body/physical source occupancy changed')
    historical = {'id': HISTORICAL_ID, 'sha256': HISTORICAL_SHA, 'verified': True}
    budgets, scans = [], {}
    for label, receipt in (('historical_e55', historical), ('current', current)):
        if not 0 < (home/'backups'/(receipt['id']+'.zip')).stat().st_size <= 512*MIB:
            raise UserError('Bounded immutable source archive required')
        terrain = ExtentTerrain(home, receipt, registry)
        try:
            budgets.append(reader_budget())
            states, actual_body, blocked, unknown = {}, {}, [], []
            for index, p in enumerate(sorted(body | geometry.keys())):
                state = terrain.state(*p)
                if p in geometry:
                    if state is None:
                        raise UserError('Unknown saved physical target')
                    states[p] = state
                if p in body:
                    if state is None:
                        unknown.append(list(p))
                    elif state.split('[', 1)[0] not in AIR or p in terrain.entities:
                        blocked.append({'position': list(p), 'state': state})
                    else:
                        actual_body[p] = state
                if index % 256 == 0:
                    budgets.append(reader_budget())
                    if time.monotonic()-started > 120:
                        raise UserError('Finite120second immutable source scan expired; no retry or generation')
            if label == 'historical_e55' and states != flatten(original_before):
                raise UserError('Actual authenticated e55 archive differs from genuine original BEFORE; never relabel')
            frame_intersections = sorted(body & occupied_cells(geometry if label == 'historical_e55' else states))
            body_rows = [{'index': n, 'length': segments[n]['length'], 'cells': len(cells),
                          'blockers': [row for row in blocked if tuple(row['position']) in cells],
                          'unknown': [p for p in unknown if tuple(p) in cells]}
                         for n, cells in enumerate(segment_cells)]
            result = {'states': states, 'body': actual_body, 'body_rows': body_rows,
                      'blocked': blocked, 'unknown': unknown, 'frame_intersections': frame_intersections,
                      'sources': copy.deepcopy(terrain.snapshot.sources)}
            if label == 'current':
                result['chain_stock'] = _inventory(terrain, (1101,65,-1257), 'minecraft:barrel')
                result['mill_stock'] = _inventory(terrain, (1313,68,-994), 'minecraft:chest')
                contract = _mill_contract()
                mill_source = contract.composite([(home/p).read_bytes() for p in MILL_SOURCES])
                manifest_path = home/MILL_MANIFEST
                if digest(manifest_path) != contract.MANIFEST_SHA:
                    raise UserError('Exact retained systems manifest required')
                manifest = bounded(manifest_path)
                mill_states = {p: terrain.state(*p) for p in flatten(mill_source)}
                if any(state is None for state in mill_states.values()):
                    raise UserError('Unknown saved mill preimage; no AIR default')
                mill_plan = verification_plan(registry, mill_states, current['sha256'], 'VERIFY ONLY exact retained7941 mill targets; do not replay placement or stock')
                result['mill_witness'] = contract.qualify_preimage(mill_source, mill_plan, manifest)
                result['mill_plan'] = mill_plan
                result['mill_sources'] = [{'path': p, 'sha256': digest(home/p)} for p in MILL_SOURCES]
                result['sources'] = copy.deepcopy(terrain.snapshot.sources)
                budgets.append(reader_budget())
            scans[label] = result
        finally:
            terrain.close()
    baseline, actual = scans['historical_e55'], scans['current']
    if not complete_body(body, baseline, actual):
        failure = {'status': 'REFUSED; no native verification plan or request emitted',
                   'expected_body_cells': len(body), 'historical_actual_AIR': len(baseline['body']),
                   'current_actual_AIR': len(actual['body']),
                   'historical_blockers': baseline['blocked'], 'current_blockers': actual['blocked'],
                   'historical_unknown': baseline['unknown'], 'current_unknown': actual['unknown'],
                   'historical_frame_intersections': [list(p) for p in baseline['frame_intersections']],
                   'current_frame_intersections': [list(p) for p in actual['frame_intersections']],
                   'native_actions': 0, 'world_writes': 0}
        write_bundle(output, {'REFUSED.json': failure}, {'format': 'awft-transport-source-refusal:1',
            'checkpoint_id': checkpoint_id, 'checkpoint_sha256': checkpoint_sha,
            'source_sha256': digest(Path(__file__)), 'native_actions': 0, 'storage_guard': reserve})
        raise UserError('Preserved incomplete/obstructed body refusal at '+str(output/'REFUSED.json'))
    physical = _member(base, source_manifest, 'physical-frame-source.json')
    physical.update(checkpoint_id=HISTORICAL_ID, checkpoint_sha256=HISTORICAL_SHA,
                    body_segments=baseline['body_rows'], sources=baseline['sources'],
                    all_saved_AIR_clear=not baseline['blocked'] and not baseline['unknown'],
                    physical_frames_clear=not baseline['frame_intersections'],
                    physical_failure=None if not baseline['frame_intersections'] else 'Body intersects original authored frame occupancy',
                    requalification={'at': utcnow(), 'source_sha256': digest(Path(__file__)),
                                     'original_before_path': original_before_path.relative_to(home).as_posix(),
                                     'original_before_sha256': BEFORE_SHA, 'all1163actual_e55_states_equal_original_before': True,
                                     'body_cells_reread_from_authenticated_e55': len(body),
                                     'old93source_unchanged': True, 'new_native_proof_created': False})
    differences = [{'position': list(p), 'original_authored': geometry[p], 'actual_saved': state}
                   for p, state in sorted(actual['states'].items()) if geometry[p] != state]
    empty = [row['slot'] for row in actual['mill_stock']['slots'] if row['saved_item_nbt'] is None]
    if not empty:
        raise UserError('No saved empty starter slot; no item overwrite proposal permitted')
    detector_plan = {'format': 'awft-detector-stock-proposal:1', 'source_checkpoint_id': current['id'],
                     'source_checkpoint_sha256': current['sha256'], 'existing_container': [1313,68,-994],
                     'actual_saved_inventory': actual['mill_stock'], 'proposed_empty_slot': empty[0],
                     'item': 'create_hypertube:redstone_detector_tube_attachment', 'count': 2,
                     'authority': 'SOURCE PROPOSAL ONLY. Master must authorize legitimate creative-construction stock, verify all27 actual native slots/components and this empty slot immediately before one ordinary item replacement.',
                     'native_action_performed': False, 'native_markers_created': False,
                     'post_stock_gate': 'Fresh native awftmill inspect full-slot readback plus exact current7941 verification; then separately bind retained resume. Never synthesize debit/attachment or refund.'}
    docs = {'physical-frame-source-e55-REQUALIFIED.json': physical,
            'zipline-current1163-VERIFY-ONLY.json': verification_plan(registry, actual['states'], current['sha256'], 'VERIFY ONLY actual installed1163 geometry; preserve joins/oxidation and existing stock'),
            'zipline-current-body-VERIFY-ONLY.json': verification_plan(registry, actual['body'], current['sha256'], 'VERIFY ONLY current saved5607 bodyAIR; not riding/native-shape proof'),
            'zipline-current-comparison.json': {'differences': differences, 'matches': 1163-len(differences),
                                               'body_blockers': actual['blocked'], 'body_unknown': actual['unknown'],
                                               'frame_intersections': [list(p) for p in actual['frame_intersections']]},
            'zipline-saved-stock-READ-ONLY.json': actual['chain_stock'],
            'mill-current7941-VERIFY-ONLY.json': actual['mill_plan'],
            'mill-detector-stock-PROPOSAL.json': detector_plan}
    current_now = bounded(home/'dashboard/settlement/backup-receipt.json')
    if (current_now['id'], current_now['sha256']) != (checkpoint_id, checkpoint_sha):
        raise UserError('Current checkpoint advanced; preserve source identity and prepare a new explicit input')
    return write_bundle(output, docs, {'format': 'awft-transport-saved-inputs:1', 'created': utcnow(),
        'source_sha256': digest(Path(__file__)), 'checkpoint_id': checkpoint_id, 'checkpoint_sha256': checkpoint_sha,
        'historical_baseline_id': HISTORICAL_ID, 'historical_baseline_sha256': HISTORICAL_SHA,
        'historical_body_air': len(baseline['body']), 'current_body_air': len(actual['body']),
        'historical_clear': not baseline['blocked'] and not baseline['unknown'] and not baseline['frame_intersections'],
        'current_clear': not actual['blocked'] and not actual['unknown'] and not actual['frame_intersections'],
        'current_physical_differences': len(differences), 'mill_preimage': actual['mill_witness'],
        'mill_source_refs': actual['mill_sources'], 'current_saved_sources': actual['sources'],
        'saved_detector_slot_proposed': empty[0], 'world_writes': 0, 'native_actions': 0,
        'new_JVMs': 0, 'native_proofs_or_markers_created': 0, 'storage_guard': reserve,
        'observed_peak_reader_rss': max(row['owned_reader_rss_bytes'] for row in budgets),
        'limits': 'Immutable saved-source preparation only. Fresh native geometry, all-slot stock, actual loading, debit, rides, restart and owner acceptance remain separate. Monitoring does not constrain other applications.'})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for field in ('home', 'output'):
        parser.add_argument('--'+field, type=Path, required=True)
    parser.add_argument('--checkpoint-id', required=True)
    parser.add_argument('--checkpoint-sha', required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.home, args.output, args.checkpoint_id, args.checkpoint_sha), indent=2))
