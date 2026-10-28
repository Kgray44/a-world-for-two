"""Rooted, irregular south-forest ground layers and retained nature-walk bodies.

This is an original plant proposal, not native sapling growth or animal seeding.
Each new flower/fern sits on exact saved soil; no old plant or tree is replaced.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
import time
from pathlib import Path

from control_room.common import UserError, digest, read_json, utcnow
from tools import artistic_native_tree_pilot as pilot
from tools.artistic_bridge_refinement import encoded
from tools.artistic_bridge_refinement import flatten
from tools.artistic_materials import require_outdoor_rule
from tools.artistic_south_extent import ExtentTerrain
from tools.artistic_south_forest import AIR
from tools.artistic_spawn_plaza import state
from tools.artistic_zipline_catenary import reader_budget
from tools.native_tree_growth import native_plan
from tools.playtest import guard
from tools.settlement_attractions import base

MAX_POCKETS = 96
MAX_CANDIDATES = 192
MAX_SECONDS = 120
MAX_OUTPUT = 8*1024**2
SOILS = pilot.ROOT_SOIL
OFFSETS = ((0, 0), (1, 0), (2, 1), (0, 2), (1, 2), (-1, 2), (-2, 1), (-2, 0),
           (-1, -1), (0, -2), (2, -2), (3, -1), (3, 1), (2, 3), (0, 4), (-2, 3),
           (-3, 1), (-4, 0), (-3, -2), (-1, -3), (1, -4), (3, -3), (4, 0), (4, 2))
FLOWERS = ('regions_unexplored:aster', 'minecraft:cornflower', 'regions_unexplored:blue_lupine',
           'regions_unexplored:felicia_daisy', 'minecraft:oxeye_daisy', 'minecraft:allium')


def settlement_plan(registry, checkpoint, field, name, verify=True):
    """Exact generic SettlementSupport contract, separate from tree-only plans."""
    if not field:
        raise UserError('A nonempty bounded native plant field is required')
    bounds = [min(p[0] for p in field), min(p[2] for p in field),
              max(p[0] for p in field), max(p[2] for p in field)]
    if bounds[2]-bounds[0] > 512 or bounds[3]-bounds[1] > 512:
        raise UserError('Generic native SettlementSupport512 footprint exceeded; split coherent pockets')
    doc = native_plan(registry, checkpoint, field, name)
    doc.update(bounds=bounds, verification_only=verify, construction_forbidden=True,
               no_tree_generation_or_animal_spawning=True)
    if not verify:
        doc['validation'] = 'Original rooted low plants on exact saved soil/AIR; current native preflight and real art review required'
    return doc


def protocol_parts(registry, checkpoint, blocks, before, roots, scenes):
    """Partition identical geometry; one12-plant prototype is never replayed."""
    remaining = dict(blocks)
    assigned = []
    for scene in scenes:
        x, z = scene['center_xz']
        possible = {(x+dx, z+dz) for dx, dz in OFFSETS}
        field = {p: value for p, value in remaining.items() if (p[0], p[2]) in possible}
        if len(field) != scene['new_rooted_plants']:
            raise UserError('Exact original pocket ownership cannot be reconstructed; no geometry fitting')
        for p in field:
            del remaining[p]
        assigned.append((scene, field))
    if remaining:
        raise UserError('Unassigned original plant geometry cannot be silently dropped')
    eligible = [(scene, field) for scene, field in assigned if len(field) >= 12]
    if not eligible:
        raise UserError('Original composition has no coherent12-plant prototype')
    scene, chosen = min(eligible, key=lambda row: (row[0]['new_rooted_plants'] != 12,
        math.dist(row[0]['center_xz'], (1120, -1094))))
    prototype = dict(sorted(chosen.items())[:12])
    groups = {'lower-bank': {}, 'inland-ridge': {}}
    for row, field in assigned:
        groups['lower-bank' if row['center_xz'][1] < -912 else 'inland-ridge'].update(field)
    docs, parts = {}, []

    def selected_context(field, source):
        xz = {(p[0], p[2]) for p in field}
        return {p: value for p, value in source.items() if (p[0], p[2]) in xz}

    def emit(label, field, full):
        if not field:
            return
        payloads = {'BEFORE-VERIFY-ONLY': selected_context(field, before), 'DELTA': field,
                    'FULL-VERIFY-ONLY': full, 'RETAINED-SOIL-VERIFY-ONLY': selected_context(field, roots)}
        names = {}
        for suffix, value in payloads.items():
            name = label+'-'+suffix+'.json'
            docs[name] = encoded(settlement_plan(registry, checkpoint, value, label+' '+suffix, suffix != 'DELTA'))
            names[suffix] = name
        parts.append({'label': label, 'new_targets': len(field), 'full_after_targets': len(full), 'files': names})

    emit('prototype12', prototype, prototype)
    for label, full in groups.items():
        emit(label+'-REMAINDER', {p: value for p, value in full.items() if p not in prototype}, full)
    coverage = {p: value for field in groups.values() for p, value in field.items()}
    if coverage != blocks:
        raise UserError('Bounded parts changed the exact original1152-state geometry')
    return docs, parts, {'center_xz': scene['center_xz'], 'targets': len(prototype),
                        'no_replay_in_remainder_deltas': True}


def point_inside(box, p):
    return all(box[i] <= p[i] <= box[i+3] for i in range(3))


def plant_palette(registry, shade, number):
    # Fern-rich shaded islands; taller-looking blue flowers at sunny ridges.
    # No random checkerboard, uniform evergreen stamp, leaf cube or sapling.
    flower = FLOWERS[(number//3) % len(FLOWERS)]
    name = 'minecraft:fern' if shade and number % 4 else flower
    if not shade and number % 5 == 4:
        name = 'minecraft:short_grass'
    return state(registry, name)


def pocket(terrain, registry, center, protected, forbidden, occupied):
    added, roots, before, retained = {}, {}, {}, Counter()
    for number, (dx, dz) in enumerate(OFFSETS):
        x, z = center[0]+dx, center[1]+dz
        if (x, z) in protected:
            retained['protected walking/architecture/zipline column'] += 1
            continue
        column = terrain.column(x, z)
        if column.get('kind') != 'dry' or base(column.get('state', '')) not in SOILS:
            retained['non-soil/retained/wet ground'] += 1
            continue
        root = (x, column['surface_y'], z)
        pos = (x, root[1]+1, z)
        head = (x, root[1]+2, z)
        values = {p: terrain.state(*p) for p in (root, pos, head)}
        if any(value is None for value in values.values()):
            raise UserError('Unknown FULL support/body cell refuses the entire plant pocket')
        if any(p in terrain.entities or p in forbidden for p in values) or pos in occupied:
            retained['BE, protected body or previous pocket'] += 1
            continue
        if base(values[pos]) not in AIR or base(values[head]) not in AIR:
            retained['existing native grass/flower/canopy or object'] += 1
            continue
        roots[root] = values[root]
        before.update(values)
        added[pos] = plant_palette(registry, column.get('existing_canopy_y') is not None, number)
    if len(added) < 4:
        raise UserError('Too little genuine open rooted ground for this coherent pocket; retain its old plants')
    return added, roots, before, dict(retained)


def prepare(home, pilot_manifest, pilot_sha256, output):
    home, output = Path(home).resolve(), Path(output).resolve()
    if output.exists() or not output.is_relative_to(home/'staging'):
        raise UserError('New private understory source folder required')
    reserve = guard(1024**2, MAX_OUTPUT)
    budgets = [reader_budget()]
    review = pilot.checked(pilot_manifest, pilot_sha256, 1024**2)
    if review.get('checkpoint_sha256') != pilot.CHECKPOINT_SHA or len(review.get('plots', [])) != 3:
        raise UserError('Current exact three-pilot source reservation required')
    registry = read_json(home/'dashboard/settlement/registry.json')
    protected, custody, bank = pilot.protected_columns(home, registry)
    # Avoid changing any still-pending native pilot's full before volume.
    for row in review['plots']:
        b = row['known_bounds']
        for x in range(b[0]-5, b[3]+6):
            for z in range(b[2]-5, b[5]+6):
                protected.add((x, z))
    # Authentic saved walk witnesses are retained, never paved from a heightmap.
    walking = []
    forbidden = set()
    for row in bank['walks']:
        if not row.get('nodes_xz'):
            continue
        walking.append({'id': row['id'], 'nodes_xz': row['nodes_xz'],
                        'status': 'Retained source-supported nature route; native walking/art not yet proved',
                        'paving_or_terrain_clearing': False})
        for witness in row.get('exact_support_and_headroom', []):
            p = witness.get('support')
            if p:
                forbidden.update((p[0], p[1]+dy, p[2]) for dy in (1, 2, 3))
    choices = []
    for zone, rows in bank['composition_zones'].items():
        if zone in ('protected', 'rock_or_nonsoil'):
            continue
        for x, y, z in rows:
            if (x, z) not in protected:
                # The centre is the real measured node within an irregular
                # terrain tile, not a grid of planted trees or paving slabs.
                choices.append((x//32, z//32, y, x, z, zone))
    chosen_tiles = set()
    choices.sort(key=lambda row: ((row[0]*13+row[1]*7) % 23, row[1], row[0], row[3]))
    checkpoint = {'id': pilot.CHECKPOINT, 'sha256': pilot.CHECKPOINT_SHA, 'verified': True}
    terrain = ExtentTerrain(home, checkpoint, registry)
    blocks, roots, before, scenes, refusals = {}, {}, {}, [], []
    started = time.monotonic()
    attempts = 0
    try:
        for tx, tz, y, x, z, zone in choices:
            if len(scenes) >= MAX_POCKETS or attempts >= MAX_CANDIDATES:
                break
            if (tx, tz) in chosen_tiles:
                continue
            if time.monotonic()-started > MAX_SECONDS:
                raise UserError('Finite understory source reader expired; no native fallback')
            attempts += 1
            try:
                extra, retained_roots, prior, retained = pocket(terrain, registry, (x, z), protected, forbidden, blocks)
            except UserError as error:
                refusals.append({'center_xz': [x, z], 'reason': str(error)})
                continue
            blocks.update(extra)
            roots.update(retained_roots)
            before.update(prior)
            chosen_tiles.add((tx, tz))
            scenes.append({'center_xz': [x, z], 'zone': zone, 'new_rooted_plants': len(extra),
                           'retained_existing_context': retained})
            if len(scenes) % 12 == 0:
                budgets.append(reader_budget())
        sources = terrain.snapshot.sources.copy()
        budgets.append(reader_budget())
    finally:
        terrain.close()
    if not blocks:
        raise UserError('No fully qualified rooted source pocket; do not substitute floating decoration')
    require_outdoor_rule(blocks, 'Original south-forest low understory batch')
    documents, native_parts, prototype = protocol_parts(registry, checkpoint, blocks, before, roots, scenes)
    # This aggregate is custody data, deliberately NOT an executable native plan.
    documents['aggregate-geometry-REVIEW-ONLY.json'] = encoded({'format': 'awft-rooted-plant-custody:1',
        'proposal': native_plan(registry, checkpoint, blocks, 'Private original aggregate geometry custody'),
        'before': native_plan(registry, checkpoint, before, 'Private original aggregate before custody'),
        'roots': native_plan(registry, checkpoint, roots, 'Private original aggregate soil custody')})
    recipe = {'format': 'awft-rooted-south-forest-understory:1', 'checkpoint_id': pilot.CHECKPOINT,
              'checkpoint_sha256': pilot.CHECKPOINT_SHA, 'reference_direction': 'Lush layered original woodland ground cover; no copied reference artwork',
              'scenes': scenes, 'plants': len(blocks), 'material_counts': dict(Counter(base(s) for s in blocks.values())),
              'nature_walks': walking, 'retained_refusals': refusals, 'all_authored_keepouts': custody,
              'native_pilot_known_fields_preserved': True, 'manual_tree_geometry': 0, 'animals_seeded': 0,
              'native_botanical_appearance_accepted': False, 'construction_forbidden': True,
              'required_next': 'Parent current-native before/support checks, source/art review and a representative real visual batch before propagation'}
    documents['understory-and-walks-REVIEW-ONLY.json'] = encoded(recipe)
    manifest = {'format': 'awft-rooted-forest-understory-source:1', 'created': utcnow(), 'source_sha256': digest(Path(__file__)),
                'checkpoint_id': pilot.CHECKPOINT, 'checkpoint_sha256': pilot.CHECKPOINT_SHA,
                'pilot_manifest_sha256': pilot_sha256, 'plants': len(blocks), 'pockets': len(scenes),
                'generic_native_parts_schema': 2, 'native_parts': native_parts, 'prototype': prototype,
                'reserve_guard': reserve, 'reader_budgets': budgets, 'source_regions': sources,
                'world_writes': 0, 'native_actions': 0, 'files': {name: {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
                                                           for name, raw in documents.items()}}
    documents['manifest.json'] = encoded(manifest)
    if sum(map(len, documents.values())) > MAX_OUTPUT:
        raise UserError('Finite understory source output exceeded')
    output.mkdir(parents=True, exist_ok=False)
    for name, raw in documents.items():
        (output/name).write_bytes(raw)
    return {'directory': str(output), 'manifest_sha256': hashlib.sha256(documents['manifest.json']).hexdigest(),
            'plants': len(blocks), 'pockets': len(scenes), 'native_actions': 0}


def rebind(home, source_manifest, source_sha256, checkpoint_id, checkpoint_sha256, output):
    """Retain the exact authored plant geometry; refresh only actual saved proof."""
    home, source_manifest, output = Path(home).resolve(), Path(source_manifest).resolve(), Path(output).resolve()
    if output.exists() or not output.is_relative_to(home/'staging') or not source_manifest.is_relative_to(home/'staging'):
        raise UserError('Exact owned understory source and new immutable rebound folder required')
    reserve = guard(1024**2, MAX_OUTPUT)
    source = pilot.checked(source_manifest, source_sha256, 1024**2)
    if source.get('format') != 'awft-rooted-forest-understory-source:1' or source.get('world_writes') != 0:
        raise UserError('Original unapplied rooted understory source receipt required')
    current = read_json(home/'dashboard/settlement/backup-receipt.json')
    if current.get('verified') is not True or current.get('id') != checkpoint_id or current.get('sha256') != checkpoint_sha256:
        raise UserError('Exact current verified stopped checkpoint required for plant rebinding')
    registry = read_json(home/'dashboard/settlement/registry.json')
    payloads = {}
    for name, facts in source['files'].items():
        path = source_manifest.parent/name
        if not path.resolve().is_relative_to(source_manifest.parent) or path.stat().st_size != facts['bytes']:
            raise UserError('Original plant member path or size differs')
        payloads[name] = pilot.checked(path, facts['sha256'], MAX_OUTPUT)
    aggregate = payloads.get('aggregate-geometry-REVIEW-ONLY.json')
    old_before = aggregate['before'] if aggregate else payloads['understory-before-VERIFY-ONLY.json']
    actual_before = flatten(old_before)
    checkpoint = {'id': checkpoint_id, 'sha256': checkpoint_sha256, 'verified': True}
    budgets = [reader_budget()]
    terrain = ExtentTerrain(home, checkpoint, registry)
    started = time.monotonic()
    try:
        for index, (pos, expected) in enumerate(sorted(actual_before.items())):
            if time.monotonic()-started > 60:
                raise UserError('Finite exact plant rebind reader expired')
            if terrain.state(*pos) != expected or pos in terrain.entities:
                raise UserError('Retain changed/unknown plant support, target, headroom or BE; no expected-state fitting')
            if index % 1024 == 0:
                budgets.append(reader_budget())
        sources = terrain.snapshot.sources.copy()
    finally:
        terrain.close()
    proposal = aggregate['proposal'] if aggregate else payloads['understory-PROPOSAL.json']
    root_doc = aggregate['roots'] if aggregate else payloads['retained-natural-soil-VERIFY-ONLY.json']
    if any(str(doc.get(k)) != str(registry[k]) for doc in (proposal, old_before, root_doc) for k in ('seed', 'world_path')):
        raise UserError('Original plant geometry belongs to another world')
    blocks, roots = flatten(proposal), flatten(root_doc)
    recipe = payloads['understory-and-walks-REVIEW-ONLY.json']
    documents, native_parts, prototype = protocol_parts(registry, checkpoint, blocks, actual_before, roots, recipe['scenes'])
    documents['aggregate-geometry-REVIEW-ONLY.json'] = encoded({'format': 'awft-rooted-plant-custody:1',
        'proposal': {**proposal, 'backup_sha256': checkpoint_sha256},
        'before': {**old_before, 'backup_sha256': checkpoint_sha256},
        'roots': {**root_doc, 'backup_sha256': checkpoint_sha256}})
    documents['understory-and-walks-REVIEW-ONLY.json'] = encoded({**recipe, 'checkpoint_id': checkpoint_id,
        'checkpoint_sha256': checkpoint_sha256, 'original_geometry_receipt_sha256': source_sha256, 'geometry_reselected': False})
    manifest = {'format': 'awft-rooted-forest-understory-rebound:1', 'created': utcnow(), 'source_sha256': digest(Path(__file__)),
                'checkpoint_id': checkpoint_id, 'checkpoint_sha256': checkpoint_sha256,
                'original_manifest_sha256': source_sha256, 'plants': source['plants'], 'pockets': source['pockets'],
                'generic_native_parts_schema': 2, 'native_parts': native_parts, 'prototype': prototype,
                'exact_current_preimage_cells': len(actual_before), 'geometry_reselected': False,
                'literal_original_geometry_sha256': hashlib.sha256(pilot.canonical([[*p, value] for p, value in sorted(blocks.items())])).hexdigest(),
                'reserve_guard': reserve, 'reader_budgets': budgets, 'source_regions': sources,
                'native_actions': 0, 'world_writes': 0, 'files': {name: {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
                                                            for name, raw in documents.items()}}
    documents['manifest.json'] = encoded(manifest)
    if sum(map(len, documents.values())) > MAX_OUTPUT:
        raise UserError('Finite exact plant rebind output exceeded')
    output.mkdir(parents=True, exist_ok=False)
    for name, raw in documents.items():
        (output/name).write_bytes(raw)
    return {'directory': str(output), 'manifest_sha256': hashlib.sha256(documents['manifest.json']).hexdigest(),
            'plants': source['plants'], 'pockets': source['pockets'], 'geometry_reselected': False,
            'current_saved_preimage_cells': len(actual_before), 'native_actions': 0}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('home', 'pilot-manifest', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--pilot-sha256', required=True)
    arguments = parser.parse_args()
    print(json.dumps(prepare(arguments.home, arguments.pilot_manifest, arguments.pilot_sha256, arguments.output), indent=2))
