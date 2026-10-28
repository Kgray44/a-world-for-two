"""Concrete woodland habitat witnesses for the single curated LIFE cohort.

No animal, copied profile, ownership/NoAI value, native request or new population
namespace is created. Town room/POI authority is joined separately by its owner.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import time
from pathlib import Path

from control_room.common import UserError, digest, read_json, utcnow
from tools import artistic_native_tree_pilot as pilot
from tools.artistic_bridge_refinement import encoded
from tools.artistic_south_extent import ExtentTerrain
from tools.artistic_south_forest import AIR, GROUND
from tools.artistic_zipline_catenary import reader_budget
from tools.artistic_forest_understory import settlement_plan
from tools.playtest import guard
from tools.settlement_attractions import base

CURATION_SHA = 'be41097fb361a62fb5b60cc93d33958a8a896048dbacdca72e6c87de8abe74d9'
RETAINED = 'staging/life-inspect-sealed-20261027T200847Z/recipe-01.json'
RETAINED_SHA = '9809731636545398a759cd1c91cbf15c8497dfb1377dbb3a06126c7583ec12b3'
INTENTS = (
    ('woodland-deer-glade', 'naturalist:deer', 'DRY', (1120, -1024), 'grass'),
    ('woodland-seed-bird', 'naturalist:bird', 'AIR', (1144, -944), 'grass'),
    ('woodland-flower-butterfly', 'naturalist:butterfly', 'AIR', (1160, -1048), 'flowers'),
    ('woodland-night-firefly', 'naturalist:firefly', 'AIR', (1040, -1112), 'grass'),
    ('woodland-leafy-enaga', 'crittersandcompanions:shima_enaga', 'AIR', (1120, -816), 'leaves'),
    ('woodland-leaf-ladybug', 'crittersandcompanions:ladybug', 'AIR', (1120, -800), 'leaves'),
    ('woodland-reed-dragonfly', 'crittersandcompanions:dragonfly', 'AIR', (1136, -1024), 'grass'),
    ('woodland-quiet-allay', 'minecraft:allay', 'AIR', (1160, -832), 'grass'),
)
MAX_OUTPUT = 8*1024**2
MAX_SECONDS = 120
CHECKPOINT = '20261028T025401Z-0d7b72'
CHECKPOINT_SHA = 'f22c9e7d3449616c651ce83eae2f2e712974a0b8e9dd8241d7c5eda5f1159045'
SOFT = pilot.NATIVE_SOFT


def field_box(terrain, bounds):
    result = {}
    for x in range(bounds[0], bounds[3]+1):
        for z in range(bounds[2], bounds[5]+1):
            for y in range(bounds[1], bounds[4]+1):
                value = terrain.state(x, y, z)
                if value is None:
                    raise UserError('Every literal habitat volume cell must be saved FULL')
                result[x, y, z] = value
    return result


def dry_site(terrain, anchor, kind, nature, protected):
    x, z = anchor
    column = terrain.column(x, z)
    if column.get('kind') != 'dry' or base(column.get('state', '')) not in pilot.ROOT_SOIL:
        raise UserError('Actual grassy woodland footing required')
    y = column['surface_y']+1
    bounds = [x-3, y-2, z-3, x+3, y+5, z+3]
    if any((xx, zz) in protected for xx in range(x-2, x+3) for zz in range(z-2, z+3)):
        raise UserError('Preserve current mechanisms, routes, fountain, future cable and tree plots')
    field = field_box(terrain, bounds)
    # This is a conservative saved-state screen only. Native model dimensions,
    # collision shapes, spawn placements and normal event hooks are not faked.
    for xx in range(x-1, x+2):
        for zz in range(z-1, z+2):
            for yy in range(y, y+(4 if kind == 'AIR' else 3)):
                if base(field[xx, yy, zz]) not in AIR | SOFT:
                    raise UserError('Retained object/canopy or wet body core; choose another real opening')
    natural = {'grass': 0, 'flowers': 0, 'leaves': 0}
    for value in field.values():
        key = base(value)
        natural['grass'] += int(key in pilot.ROOT_SOIL or key in SOFT)
        natural['flowers'] += int(any(word in key for word in ('flower', 'daisy', 'lupine', 'aster', 'allium', 'poppy')))
        natural['leaves'] += int(key.endswith('_leaves'))
    if natural[nature] < (3 if nature == 'leaves' else 1):
        raise UserError('Actual '+nature+' habitat is not present; do not claim future unplanted scenery')
    site = {'feet': [x+.5, y, z+.5], 'bank_anchor': [x, z],
            'roam_bounds': [x-12, max(48, y-8), z-12, x+13, min(240, y+24), z+13],
            'habitat': {'kind': kind, 'known_bounds': bounds}}
    return site, field, natural


def water_site(terrain, x, z, protected):
    column = terrain.column(x, z)
    if column.get('kind') != 'water':
        raise UserError('Actual retained source-water surface required')
    top = column['surface_y']
    water = [x-2, top-1, z-2, x+2, top, z+2]
    known = [x-3, top-2, z-3, x+3, top+3, z+3]
    if any((xx, zz) in protected for xx in range(x-3, x+4) for zz in range(z-3, z+4)):
        raise UserError('Preserve navigation, machinery, plumbing, cable or future construction water')
    field = field_box(terrain, known)
    for xx in range(x-2, x+3):
        for zz in range(z-2, z+3):
            if any(field[xx, yy, zz] != 'minecraft:water[level=0]' for yy in (top-1, top)):
                raise UserError('A heightmap cannot substitute for contiguous5x5x2 literal source water')
            if base(field[xx, top+1, zz]) not in AIR:
                raise UserError('Retain an actual accessible water surface')
    return {'feet': [x+.5, top-1, z+.5], 'roam_bounds': [x-10, top-5, z-10, x+11, top+4, z+11],
            'habitat': {'kind': 'WATER', 'known_bounds': known, 'water_bounds': water}}, field


def shore_site(terrain, x, z, protected, nodes):
    water_column = terrain.column(x, z)
    top = water_column.get('surface_y')
    if top is None or water_column.get('kind') != 'water':
        raise UserError('Known literal shore water required')
    water = [x-1, top-1, z-1, x+1, top, z+1]
    for dx, dz in ((3, 0), (-3, 0), (0, 3), (0, -3), (4, 0), (-4, 0), (0, 4), (0, -4)):
        sx, sz = (1 if dx > 0 else -1 if dx < 0 else 0), (1 if dz > 0 else -1 if dz < 0 else 0)
        route = []
        for step in range(3):
            xx, zz = x+dx+step*sx, z+dz+step*sz
            col = terrain.column(xx, zz)
            if col.get('kind') != 'dry' or base(col.get('state', '')) not in GROUND:
                break
            if not route and col['surface_y'] not in (top, top+1):
                break
            if route and abs(col['surface_y']+1-route[-1][1]) > 1:
                break
            route.append([xx, col['surface_y']+1, zz])
        if len(route) != 3:
            continue
        occupied = {(xx, zz) for xx in range(x-2, x+3) for zz in range(z-2, z+3)}
        for xx, yy, zz in route:
            occupied.update((xx+ox, zz+oz) for ox in (-1, 0, 1) for oz in (-1, 0, 1))
        if occupied & protected:
            continue
        known = [min(p[0] for p in occupied), top-2, min(p[1] for p in occupied),
                 max(p[0] for p in occupied), top+5, max(p[1] for p in occupied)]
        field = field_box(terrain, known)
        if any(field[xx, yy, zz] != 'minecraft:water[level=0]'
               for xx in range(x-1, x+2) for zz in range(z-1, z+2) for yy in (top-1, top)):
            continue
        if any(base(field[xx, top+1, zz]) not in AIR for xx in range(x-1, x+2) for zz in range(z-1, z+2)):
            continue
        if any(base(field[xx, yy+oy, zz]) not in AIR | SOFT for xx, yy, zz in route for oy in range(3)):
            continue
        anchor = min(nodes, key=lambda p: math.dist(p, (route[0][0], route[0][2])))
        if math.dist(anchor, (route[0][0], route[0][2])) > 16:
            continue
        reeds = sum(any(word in base(value) for word in ('sugar_cane', 'reed', 'cattail')) for value in field.values())
        return {'feet': [route[0][0]+.5, route[0][1], route[0][2]+.5], 'bank_anchor': list(anchor),
                'roam_bounds': [known[0]-5, top-3, known[2]-5, known[3]+6, top+8, known[5]+6],
                'habitat': {'kind': 'SHORE', 'known_bounds': known, 'water_bounds': water, 'shore_path': route}}, field, reeds
    raise UserError('No real gentle dry three-step exit beside the admitted water')


def prepare(home, output):
    home, output = Path(home).resolve(), Path(output).resolve()
    if output.exists() or not output.is_relative_to(home/'staging'):
        raise UserError('New owned private habitat source required')
    reserve = guard(1024**2, MAX_OUTPUT)
    budgets = [reader_budget()]
    current = read_json(home/'dashboard/settlement/backup-receipt.json')
    if current.get('verified') is not True or current.get('id') != CHECKPOINT or current.get('sha256') != CHECKPOINT_SHA:
        raise UserError('Exact post-native-tree checkpoint required for habitats')
    registry = read_json(home/'dashboard/settlement/registry.json')
    curation = pilot.checked(Path(__file__).resolve().parents[1]/'compat/control-bridge/proposals/life-extension/species-habitats.json', CURATION_SHA, 1024**2)
    retained = pilot.checked(home/RETAINED, RETAINED_SHA, 128*1024)
    profiles = {row['entity']: row for row in curation['species']}
    protected, custody, bank = pilot.protected_columns(home, registry)
    # All three original before fields remain kept out, including the pig-owned
    # refused magnolia clearing. A new site is not permission to clear residents.
    for _, species, root in pilot.PLOTS:
        q = pilot.qualifications(home)[species]
        _, box = pilot.envelopes(root, q['relative_write_bounds'])
        for xx in range(box[0]-5, box[3]+6):
            for zz in range(box[2]-5, box[5]+6):
                protected.add((xx, zz))
    known_nodes = set(map(tuple, bank['bank_nodes_xz']))
    soil = [r for r in bank['saved_samples'] if (r['x'], r['z']) in known_nodes and r['kind'] == 'dry']
    water = [r for r in bank['saved_samples'] if r['kind'] == 'water' and 928 <= r['x'] <= 1352 and -1192 <= r['z'] <= -640]
    terrain = ExtentTerrain(home, {'id': CHECKPOINT, 'sha256': CHECKPOINT_SHA, 'verified': True}, registry)
    sites, fields, facts, refusals, used = [], {}, [], [], set()
    started = time.monotonic()
    try:
        for name, entity, kind, desired, nature in INTENTS:
            candidates = sorted(soil, key=lambda r: math.dist((r['x'], r['z']), desired))
            selected = False
            for row in candidates[:32]:
                anchor = row['x'], row['z']
                if anchor in used or math.dist(anchor, desired) > 112:
                    continue
                if time.monotonic()-started > MAX_SECONDS:
                    raise UserError('Finite woodland habitat source reader expired')
                try:
                    site, field, natural = dry_site(terrain, anchor, kind, nature, protected)
                except UserError as error:
                    refusals.append({'species': entity, 'anchor': list(anchor), 'reason': str(error)})
                    continue
                site.update(name=name, entity=entity)
                sites.append(site)
                fields.update(field)
                facts.append({'site': name, 'entity': entity, 'actual_nature_cells': natural,
                              'native_class': profiles[entity]['native_class'], 'native_category': profiles[entity]['native_category']})
                used.add(anchor)
                selected = True
                break
            if not selected:
                facts.append({'site': name, 'entity': entity, 'status': 'UNQUALIFIED in finite actual saved candidates; native request not created'})
        for name, entity, desired in (('woodland-koi-refuge', 'crittersandcompanions:koi_fish', (1160, -1000)),
                                      ('woodland-pondie-refuge', 'fishofthieves:pondie', (1136, -976))):
            found = False
            for row in sorted(water, key=lambda r: math.dist((r['x'], r['z']), desired))[:32]:
                anchor = row['x'], row['z']
                if anchor in used or math.dist(anchor, desired) > 96:
                    continue
                try:
                    site, field = water_site(terrain, *anchor, protected)
                except UserError as error:
                    refusals.append({'species': entity, 'water_center': list(anchor), 'reason': str(error)})
                    continue
                bank_anchor = min(known_nodes, key=lambda p: math.dist(p, anchor))
                if math.dist(bank_anchor, anchor) > 16:
                    continue
                site.update(name=name, entity=entity, bank_anchor=list(bank_anchor))
                sites.append(site)
                fields.update(field)
                used.add(anchor)
                facts.append({'site': name, 'entity': entity, 'actual_source_water_cells': 50,
                              'freshwater_biome_and_predator_acceptance': 'UNKNOWN; native normal spawn/biome and ecology review required'})
                found = True
                break
            if not found:
                facts.append({'site': name, 'entity': entity, 'status': 'UNQUALIFIED literal source-water refuge'})
        duck_found = False
        for row in sorted(water, key=lambda r: math.dist((r['x'], r['z']), (1136, -1000)))[:48]:
            if time.monotonic()-started > MAX_SECONDS:
                raise UserError('Finite exact shore-footprint reader expired')
            # The8m survey is a locator only. Inspect real one-metre offsets;
            # never interpolate a shallow/dry shoreline from a coarse centre.
            selected = None
            for ox, oz in ((0, 0), (2, 0), (-2, 0), (0, 2), (0, -2), (3, 0), (-3, 0), (0, 3), (0, -3)):
                try:
                    selected = shore_site(terrain, row['x']+ox, row['z']+oz, protected, known_nodes)
                    break
                except UserError:
                    continue
            if selected is None:
                refusals.append({'species': 'naturalist:duck', 'water_center': [row['x'], row['z']],
                                 'reason': 'No exact admitted gentle shore in finite1m footprint offsets'})
                continue
            site, field, reeds = selected
            site.update(name='woodland-gentle-duck-shore', entity='naturalist:duck')
            if tuple(site['feet']) in {tuple(other['feet']) for other in sites}:
                continue
            sites.append(site)
            fields.update(field)
            facts.append({'site': site['name'], 'entity': 'naturalist:duck', 'actual_source_water_cells': 18,
                          'actual_dry_exit_steps': 3, 'actual_reed_cells': reeds,
                          'native_shore_behavior_and_botanical_appearance': 'UNKNOWN until normal native admission and real observation'})
            duck_found = True
            break
        if not duck_found:
            facts.append({'site': 'woodland-gentle-duck-shore', 'entity': 'naturalist:duck', 'status': 'UNQUALIFIED real water/dry-exit shore'})
        sources = terrain.snapshot.sources.copy()
        budgets.append(reader_budget())
    finally:
        terrain.close()
    document = {'format': 'awft-life-sites:3', 'seed': registry['seed'], 'world_path': registry['world_path'],
                'population_namespace': retained['population_namespace'], 'sites': sites,
                'source_only': True, 'native_spawn_acceptance': False}
    checkpoint = {'sha256': CHECKPOINT_SHA}
    docs = {'woodland-sites-REVIEW-ONLY.json': encoded(document),
            'habitat-full-field-VERIFY-ONLY.json': encoded(settlement_plan(registry, checkpoint, fields, 'VERIFY ONLY complete actual woodland habitat source boxes'))}
    recipe = {'format': 'awft-fifteen-species-habitat-source:1', 'checkpoint_id': CHECKPOINT, 'checkpoint_sha256': CHECKPOINT_SHA,
              'curation_sha256': CURATION_SHA, 'retained_namespace_source_sha256': RETAINED_SHA,
              'woodland_habitat_facts': facts, 'source_sites_with_literal_fields': len(sites), 'retained_refusals': refusals,
              'town_authority_pending': ['cozys-improved-cats:improved_cat', 'doggytalents:dog', 'minecraft:villager', 'ribbits:ribbit'],
              'shore_route_pending': [] if duck_found else ['naturalist:duck'], 'naturalist_dragonfly_disabled_not_an_alias': True,
              'additional_residents_requested_here': 0, 'planned_fifteen_species_capacity': 15,
              'conservative_native_bee_reserve': 6, 'actual_birch_larch_new_bees_observed': 0,
              'planned_capacity_with_reserved_bees': 21, 'whole_cohort_cap': 64,
              'copied_profiles_ownership_NoAI_or_profession': False, 'native_request_created': False,
              'safety_custody': custody, 'required_next': ['Join actual source-backed4town rooms/POIs and real duck dry-exit shore route',
                  'Rebind after native trees/plant layer; verify complete fields and all-current safety masks',
                  'Use the one existing v3 controller/cohort and actual45 class hashes',
                  'Normal STRUCTURE spawn placement/rules/finalize hooks, native model collision/medium, habitat and ownership gates',
                  'Full stopped saved UUID census, genuine durable intent and native inspection before any seeding',
                  'Real behavior, restart/idempotence, appearance and resource acceptance remain unproved']}
    docs['fifteen-species-source-ledger.json'] = encoded(recipe)
    manifest = {'format': 'awft-woodland-habitat-source-receipt:1', 'source_sha256': digest(Path(__file__)),
                'checkpoint_id': CHECKPOINT, 'checkpoint_sha256': CHECKPOINT_SHA, 'sites': len(sites), 'field_cells': len(fields),
                'native_actions': 0, 'world_writes': 0, 'reserve_guard': reserve, 'reader_budgets': budgets,
                'source_regions': sources, 'files': {name: {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()} for name, raw in docs.items()}}
    docs['manifest.json'] = encoded(manifest)
    if sum(map(len, docs.values())) > MAX_OUTPUT:
        raise UserError('Finite woodland habitat source output exceeded')
    output.mkdir(parents=True, exist_ok=False)
    for name, raw in docs.items():
        (output/name).write_bytes(raw)
    return {'directory': str(output), 'manifest_sha256': hashlib.sha256(docs['manifest.json']).hexdigest(),
            'saved_habitat_sites': len(sites), 'native_actions': 0, 'world_writes': 0}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--home', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    arguments = parser.parse_args()
    print(json.dumps(prepare(arguments.home, arguments.output), indent=2))
