"""Measured follow-on woodland groups after the three native pilot outcomes.

No generated tree geometry, block stamp, native command, seed request or assumed
variant is produced. Each proposed sapling retains the complete sealed R3 field.
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
from tools.artistic_south_forest import AIR, buffered_columns
from tools.artistic_zipline_catenary import reader_budget
from tools.native_tree_growth import envelopes, native_plan
from tools.playtest import guard
from tools.settlement_attractions import base

MAX_SECONDS = 150
MAX_OUTPUT = 16*1024**2
MAX_TRIALS_PER_SITE = 8
INTENTS = (
    ('river-birch-edge', 'Cottage-bank mixed understory', 'regions_unexplored:silver_birch_sapling', (1136, -1056)),
    ('white-blossom-glade', 'Cottage-bank mixed understory', 'regions_unexplored:white_magnolia_sapling', (1160, -1024)),
    ('maple-footwoods', 'Cliff-foot mixed woods', 'regions_unexplored:maple_sapling', (992, -1040)),
    ('pink-blossom-hollow', 'Cliff-foot mixed woods', 'regions_unexplored:pink_magnolia_sapling', (1000, -1080)),
    ('pine-ridge-edge', 'Inland woodland transition', 'regions_unexplored:pine_sapling', (1120, -864)),
    ('golden-larch-ridge', 'Inland woodland transition', 'regions_unexplored:golden_larch_sapling', (1184, -752)),
)


def all_qualifications(home):
    pilot.qualifications(home)  # Authenticate the nine-species seal and actual43 receipt.
    seal = pilot.checked(pilot.R3/'source-freeze.json', pilot.R3_SHA, 1024**2)
    receipt = pilot.checked(pilot.R3/'receipt.json', seal['qualification_receipt_sha256'], 1024**2)
    native = pilot.checked(home/pilot.DESCRIBE, pilot.DESCRIBE_SHA, 2*1024**2)
    result = {}
    for _, _, species, _ in INTENTS:
        name = species.replace(':', '--')+'.json'
        q = pilot.checked(pilot.R3/name, receipt['files'][name]['sha256'], 128*1024)
        if (q.get('all_reachable_features_reviewed') is not True or q.get('sapling') != species
                or q['native_descriptor_sha256'] != native['native_descriptor_sha256s'][species]
                or hashlib.sha256(pilot.canonical(q['derivation'])).hexdigest() != q['derivation_sha256']):
            raise UserError('Exact full normal/rare follow-on qualification required')
        result[species] = q
    return result


def reserved_plot_columns(plots):
    columns = set()
    for plot in plots:
        box = plot['known_bounds']
        columns.update(buffered_columns({(x, z) for x in range(box[0], box[3]+1)
                                         for z in range(box[2], box[5]+1)}, 5))
    return columns


def candidates(bank, qualification, desired, excluded):
    """Finite measured terrain choices; no runtime retry or changed envelope."""
    rows = []
    measured = {(row['x'], row['z']): row for row in bank['saved_samples']}
    radius = max(abs(qualification['relative_write_bounds'][i]) for i in (0, 2, 3, 5))
    for zone, values in bank['composition_zones'].items():
        if zone in ('protected', 'rock_or_nonsoil'):
            continue
        for x, ground, z in values:
            distance = math.dist((x, z), desired)
            if distance > 160:
                continue
            root = (x, ground+1, z)
            write, known = envelopes(root, qualification['relative_write_bounds'])
            if any((xx, zz) in excluded for xx in range(known[0], known[3]+1)
                   for zz in range(known[2], known[5]+1)):
                continue
            neighborhood = [row for (xx, zz), row in measured.items()
                            if abs(xx-x) <= max(radius, 8) and abs(zz-z) <= max(radius, 8)]
            if not neighborhood or any(row.get('kind') != 'dry' or row.get('existing_canopy_y') is not None
                                       for row in neighborhood):
                continue
            relief = max(row['surface_y'] for row in neighborhood)-min(row['surface_y'] for row in neighborhood)
            # Prefer actual modest-contour clearings over a nearer steep cliff.
            # The exact full-field admission remains independent and unchanged.
            rows.append((distance+24*relief, root))
    return [root for _, root in sorted(rows)[:MAX_TRIALS_PER_SITE]]


def prepare(home, pilot_manifest, pilot_sha256, output):
    home, pilot_manifest, output = Path(home).resolve(), Path(pilot_manifest).resolve(), Path(output).resolve()
    if output.exists() or not output.is_relative_to(home/'staging') or not pilot_manifest.is_relative_to(home/'staging'):
        raise UserError('Exact private pilot input and new follow-on output required')
    reserve = guard(1024**2, MAX_OUTPUT)
    before_budget = reader_budget()
    previous = pilot.checked(pilot_manifest, pilot_sha256, 1024**2)
    if (previous.get('checkpoint_id') != pilot.CHECKPOINT or previous.get('checkpoint_sha256') != pilot.CHECKPOINT_SHA
            or len(previous.get('plots', [])) != 3 or previous.get('world_writes') != 0):
        raise UserError('Exact unexecuted three-pilot source receipt required')
    registry = read_json(home/'dashboard/settlement/registry.json')
    qvalues = all_qualifications(home)
    protected, custody, bank = pilot.protected_columns(home, registry)
    occupied = reserved_plot_columns(previous['plots'])
    checkpoint = {'id': pilot.CHECKPOINT, 'sha256': pilot.CHECKPOINT_SHA, 'verified': True}
    started = time.monotonic()
    terrain = ExtentTerrain(home, checkpoint, registry)
    plots, refusals, docs, selected = [], [], {}, []
    try:
        for ident, group, species, desired in INTENTS:
            if time.monotonic()-started > MAX_SECONDS:
                raise UserError('Finite follow-on source selection expired; no native or automatic retry fallback')
            q = qvalues[species]
            found = False
            for root in candidates(bank, q, desired, protected | occupied):
                if time.monotonic()-started > MAX_SECONDS:
                    raise UserError('Finite follow-on saved-field reader expired')
                try:
                    field, facts = pilot.review_plot(terrain, registry, checkpoint, q, root, protected | occupied)
                except UserError as error:
                    refusals.append({'intent': ident, 'root': list(root), 'reason': str(error)})
                    continue
                reader_budget()
                plan = {'format': 'awft-native-tree-plan:1', 'seed': registry['seed'], 'world_path': registry['world_path'],
                        'saplings': [species], 'root': list(root), 'write_bounds': facts['write_bounds'], 'known_bounds': facts['known_bounds']}
                docs[ident+'/tree-plan.json'] = encoded(plan)
                docs[ident+'/tree-before-VERIFY-ONLY.json'] = encoded(native_plan(registry, checkpoint, field,
                    'VERIFY ONLY follow-on '+ident+' complete native R3 field'))
                docs[ident+'/native-qualification.json'] = encoded(q)
                plot = {'id': ident, 'group': group, 'species': species, 'desired_xz': list(desired), **facts,
                        'tree_plan_sha256': hashlib.sha256(docs[ident+'/tree-plan.json']).hexdigest(),
                        'all_reachable_native_variants_retained': True}
                plots.append(plot)
                occupied.update(reserved_plot_columns([plot]))
                selected.append(ident)
                found = True
                break
            if not found:
                refusals.append({'intent': ident, 'status': 'No qualified plot in the finite measured candidate set; do not plant elsewhere automatically'})
        sources = terrain.snapshot.sources.copy()
        after_budget = reader_budget()
    finally:
        terrain.close()
    walks = [{'id': row['id'], 'status': row['status'], 'nodes_xz': row.get('nodes_xz', []),
              'exact_support_and_headroom': row.get('exact_support_and_headroom', []),
              'native_walking_acceptance': False, 'paving_or_clearing_authorized': False}
             for row in bank['walks'] if row.get('nodes_xz')]
    recipe = {'format': 'awft-follow-on-native-forest-groups:1', 'created': utcnow(), 'checkpoint_id': pilot.CHECKPOINT,
              'checkpoint_sha256': pilot.CHECKPOINT_SHA, 'pilot_manifest_sha256': pilot_sha256,
              'groups': [{'name': name, 'plots': [p['id'] for p in plots if p['group'] == name]}
                         for name in dict.fromkeys(row[1] for row in INTENTS)],
              'plots': plots, 'all_six_intents_qualified': len(plots) == len(INTENTS), 'retained_refusals': refusals,
              'nature_walks': walks, 'native_tree_blocks_hand_stamped': 0,
              'understory_direction': ['Irregular ferns, native meadow flowers and low grasses on actual soil, away from body routes',
                  'Keep wildlife glades and shrub margins; no uniform evergreen rows or invented cliff access',
                  'Choose detailed low planting against the actual grown canopy after pilot appearance review'],
              'potential_native_bee_capacity_follow_on': sum(p['reserved_native_bee_slots'] for p in plots),
              'potential_native_bee_capacity_with_three_pilot': sum(p['reserved_native_bee_slots'] for p in plots+previous['plots']),
              'native_growth_or_life_authority': False, 'generation_requests_created': False,
              'required_next': 'Actual three-pilot guard/growth/bee/restart/appearance pass, fresh stopped save and per-plot native admission; this source is not an executable rollout'}
    docs['forest-groups-REVIEW-ONLY.json'] = encoded(recipe)
    docs['future-known-field-reservation-ONLY.json'] = encoded({'format': 'awft-prospective-growth-exclusion:1',
        'checkpoint_sha256': pilot.CHECKPOINT_SHA, 'native_plan': False, 'growth_authority': False,
        'whole_crown_extra_skirt_metres': 5, 'all_growth_excluded_columns_xz': [list(p) for p in sorted(occupied)],
        'scope': 'Three pilot and qualified follow-on complete known fields plus5m; no false AIR or planted-tree claim'})
    manifest = {'format': 'awft-follow-on-forest-source-receipt:1', 'source_sha256': digest(Path(__file__)),
                'checkpoint_id': pilot.CHECKPOINT, 'checkpoint_sha256': pilot.CHECKPOINT_SHA,
                'pilot_manifest_sha256': pilot_sha256, 'native_actions': 0, 'world_writes': 0,
                'qualified_plots': len(plots), 'requested_intents': len(INTENTS), 'plots': plots,
                'source_regions': sources, 'reader_budgets': [before_budget, after_budget], 'reserve_guard': reserve,
                'files': {name: {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()} for name, raw in docs.items()}}
    docs['manifest.json'] = encoded(manifest)
    if sum(map(len, docs.values())) > MAX_OUTPUT:
        raise UserError('Finite follow-on output budget exceeded')
    output.mkdir(parents=True, exist_ok=False)
    for name, raw in docs.items():
        path = output/name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    return {'directory': str(output), 'manifest_sha256': hashlib.sha256(docs['manifest.json']).hexdigest(),
            'qualified_plots': len(plots), 'requested_intents': len(INTENTS), 'native_actions': 0}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('home', 'pilot-manifest', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--pilot-sha256', required=True)
    arguments = parser.parse_args()
    print(json.dumps(prepare(arguments.home, arguments.pilot_manifest, arguments.pilot_sha256, arguments.output), indent=2))
