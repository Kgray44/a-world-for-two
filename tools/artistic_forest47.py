"""Fresh native-sapling woodland source for candidate47, never a world writer.

Historical46 inputs remain immutable. The four unperformed plots are re-read,
and new plots use all nine sealed normal/rare/mega/deep-root derivations. Runtime
growth, bee custody, actual AABBs, persistence and appearance remain native gates.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import time
import zipfile

from control_room.common import UserError, digest, read_json, utcnow
from tools import artistic_native_tree_pilot as pilot
from tools import artistic_dense_canopies as dense
from tools.artistic_bridge_refinement import encoded
from tools.artistic_bridge_topside_inspection import current_pack, owned_regular
from tools.artistic_forest_understory import settlement_plan
from tools.artistic_south_extent import ExtentTerrain
from tools.artistic_south_forest import exclusions
from tools.artistic_zipline_catenary import reader_budget
from tools.native_tree_growth import SAPLINGS, envelopes, protect_envelope
from tools.playtest import guard

MIB = 1024**2
CHECKPOINT = '20261028T061123Z-575aff'
CHECKPOINT_SHA = '2633518e1a31a262b8f209e33bfeb9d0a15e431b150a98d05334e9c33d9508ad'
CANDIDATE = '0.1.0-candidate.47'
BRIDGE = '0.6.33'
PACK_SHA = 'ea6b4ff61da8ec6c0f8ce39131852c11b824a72ee3b3b9c6abfe195c6801d972'
JAR_BYTES = 562634
JAR_SHA = '25b1642f5d1e07856e43350507166599134c88eeb1632357e3928ad87b24d2cc'
MAX_OUTPUT = 64*MIB
MAX_SECONDS = 240
MAX_FULL_TRIALS = 256
MAX_TRIALS_PER_INTENT = 2122
NEW_SPECIES = SAPLINGS + tuple((
    'minecraft:birch_sapling', 'regions_unexplored:silver_birch_sapling',
    'regions_unexplored:pine_sapling', 'regions_unexplored:larch_sapling',
    'regions_unexplored:golden_larch_sapling')[i % 5] for i in range(24))
REMAINING = tuple(row for row in dense.RESUME46_PLOTS if row[0] in ('copse-115', 'copse-158', 'copse-188', 'copse-206'))
HISTORICAL = (
    ('staging/native-copse12-north-qualified-1793159122599515800/manifest.json',
     'ef2ccea0c12704daeb5c58d9f91c26e096b33413902cdef3311a94572a08633d'),
    ('staging/native-followons-north-qualified-1793159122599515800/manifest.json',
     'c233e75aa3d1646099d30b0bd0dbfd1fa0e0003cb544f7d512ab47805a98ef39'),
    ('staging/native-three-sapling-current3c15-1793155646690190800/manifest.json',
     'e6c0f5bc5d05644f1f5efbc1e86a2805c938a4b4d5e1ffd6935ec5096f07488c'),
    ('staging/native-six-resume46-e55-1793162548528814100/manifest.json',
     '2dc0a8546ae153e95f4d41fd5e22e6cfb4968e2a2d4a3cd2c43dfc5e3017fe80'),
)
EXTRA_MASKS = (
    ('Actually built R5 fountain all2532 targets and protected AIR',
     'staging/artistic-fountain-r5-ACTUAL-DRY45-1793155163050141000/plaza.json',
     'ce85c167a6c3e831bdbb33996d17352c6902329858b4f65d8349ac222f1942be'),
    ('Current admitted western v2 physical stations and thirteen frames',
     'staging/zipline-west-physical-ADMITTED46-1793166585822760500/physical-PLACE-ONCE.json',
     '51e637b7437206b19e7cf5da0194715679f299bf609db59c8a4a534ad8bbbe9f'),
)


def current(home):
    value = read_json(home/'dashboard/settlement/backup-receipt.json')
    if value.get('verified') is not True or (value.get('id'), value.get('sha256')) != (CHECKPOINT, CHECKPOINT_SHA):
        raise UserError('Exact current verified575 checkpoint required; do not rebind old trees silently')
    return value


def runtime_pins(home):
    release, pack_sha = current_pack(home, CANDIDATE)
    if pack_sha != PACK_SHA:
        raise UserError('Exact actual47 release pack required')
    jar = owned_regular(home, home/'server/mods'/('awft-control-bridge-'+BRIDGE+'.jar'), MIB)
    if jar.stat().st_size != JAR_BYTES or digest(jar) != JAR_SHA:
        raise UserError('Exact installed candidate47 helper JAR required')
    classes = {}
    names = {'native_class_sha256': 'worldfortwo/bridge/NativeTreeGrowthSupport.class',
             'native_scope_sha256': 'worldfortwo/bridge/TreeGrowthScope.class',
             'native_guard_sha256': 'worldfortwo/bridge/mixin/NativeTreeGrowthGuardMixin.class',
             'bee_audit_sha256': 'worldfortwo/bridge/TreeBeeAudit.class',
             'bee_facts_sha256': 'worldfortwo/bridge/BeeNestFacts.class'}
    with zipfile.ZipFile(jar) as archive:
        for key, name in names.items():
            member = archive.getinfo(name)
            if not 0 < member.file_size <= 256*1024:
                raise UserError('Bounded actual tree/scope/mixin/bee class required')
            classes[key] = hashlib.sha256(archive.read(member)).hexdigest()
    if classes != pilot.NATIVE_CLASS_PINS:
        raise UserError('Reviewed tree/scope/bee semantics changed; review new source before growth')
    return {'candidate_version': CANDIDATE, 'bridge_version': BRIDGE, 'pack_sha256': PACK_SHA,
            'compiled_jar': pilot.owned_ref(home, jar), 'classes': classes,
            'release_pack': pilot.owned_ref(home, release), 'activation_or_growth_proved': False}


def qualifications(home):
    pilot.qualifications(home)
    seal = pilot.checked(pilot.R3/'source-freeze.json', pilot.R3_SHA, MIB)
    receipt = pilot.checked(pilot.R3/'receipt.json', seal['qualification_receipt_sha256'], MIB)
    native = pilot.checked(home/pilot.DESCRIBE, pilot.DESCRIBE_SHA, 2*MIB)
    result = {}
    for species in SAPLINGS:
        name = species.replace(':', '--')+'.json'
        q = pilot.checked(pilot.R3/name, receipt['files'][name]['sha256'], 128*1024)
        if (q.get('sapling') != species or q.get('all_reachable_features_reviewed') is not True
                or q.get('native_descriptor_sha256') != native['native_descriptor_sha256s'][species]
                or hashlib.sha256(pilot.canonical(q['derivation'])).hexdigest() != q['derivation_sha256']
                or q['relative_write_bounds'] != q['derivation']['relative_write_bounds']):
            raise UserError('Exact native full normal/rare/mega/root descriptor and derivation required')
        result[species] = q
    return result


def protection(home, registry):
    columns, custody, bank = pilot.protected_columns(home, registry)
    inputs = []
    for label, name, expected in EXTRA_MASKS:
        path = owned_regular(home, home/name, 16*MIB)
        actual = digest(path)
        if expected is not None and expected != actual:
            raise UserError('Reviewed current fountain geometry differs')
        if expected is None:
            admission = read_json(home/'staging/zipline-west-physical-ADMITTED46-1793166585822760500/admission.json')
            if admission.get('geometry_targets') != 1163 or admission.get('no_native_cables_or_riding_claim') is not True:
                raise UserError('Exact admitted western v2 physical source required')
        inputs.append((label, path, actual))
    extra, facts = exclusions(inputs, registry)
    columns.update(extra)
    custody.extend(facts)
    north, partition = dense.north_partition(home, registry)
    columns.update(north)
    # The inherited v2 reservation explicitly contains the actual native curve
    # flight/body envelope, all station clearance and the authored cliff walk.
    if not any(f.get('sha256') == pilot.V2_SHA for f in custody):
        raise UserError('Complete v2 flight plus five-metre crown skirt required')
    return columns, custody, bank, partition


def historical_plots(home):
    plots, sources = {}, []
    for name, expected in HISTORICAL:
        path = owned_regular(home, home/name, MIB)
        if digest(path) != expected:
            raise UserError('Exact old native success/false/lost/held source custody differs')
        document = read_json(path)
        for row in document.get('plots', []):
            root = tuple(row['root'])
            if root not in plots:
                plots[root] = row
        sources.append(pilot.owned_ref(home, path))
    if not any(row.get('id') == 'copse-2' for row in plots.values()) or not any(row.get('id') == 'copse-37' for row in plots.values()):
        raise UserError('Held failed/lost plot custody must be explicit')
    return list(plots.values()), sources


def conflict(write, known, rows):
    return any(dense.overlap(write, row['known_bounds']) or dense.overlap(known, row['write_bounds']) for row in rows)


def connection(terrain, row, x, z):
    steps = max(abs(x-row['x']), abs(z-row['z']), 1)
    return all(terrain.column(row['x']+round((x-row['x'])*n/steps),
                              row['z']+round((z-row['z'])*n/steps)).get('kind') == 'dry'
               for n in range(steps+1))


def candidate_rows(bank):
    connected = set(map(tuple, bank['bank_nodes_xz']))
    return [r for r in bank['saved_samples'] if (r['x'], r['z']) in connected and r.get('kind') == 'dry']


def intent_rows(bank, species, ordinal):
    """Irregular contour pockets distributed shoreward through the cliff foot.

    Source candidates are finite distinct measured roots, never repeated native
    attempts. Large rare variants do not get a reduced envelope to fit a glade.
    """
    rows = candidate_rows(bank)
    target_z = (-1104, -1000, -896, -800)[ordinal % 4]
    target_x = (976, 1096, 1224)[(ordinal//4) % 3]
    rows.sort(key=lambda r: (math.hypot(r['x']-target_x, r['z']-target_z),
                             ((r['x']//8)*19+(r['z']//8)*23) % 31, r['x'], r['z']))
    offsets = ((0, 0), (1, -2), (-2, 1), (2, 2), (-1, -1))
    return [(r, r['x']+offsets[i % 5][0], r['z']+offsets[i % 5][1])
            for i, r in enumerate(rows[:MAX_TRIALS_PER_INTENT])]


def quick_field(terrain, root, write):
    """A conservative reject-only screen; successful plots still read every voxel."""
    for x in range(write[0], write[3]+1):
        for z in range(write[2], write[5]+1):
            row = terrain.column(x, z)
            if (row.get('kind') != 'dry' or row.get('existing_canopy_y') is not None
                    or row.get('surface_y', 999) > root[1]+2):
                raise UserError('Whole WRITE column retains canopy/water/cliff/object/unknown')


def prepare(home, output, mode='remaining', count=24):
    home, output = Path(home).resolve(), Path(output).resolve()
    if output.exists() or output.parent != home/'staging' or mode not in ('remaining', 'new') or not 1 <= count <= 24:
        raise UserError('New owned finite forest47 folder and explicit source mode required')
    reserve = guard(2*MIB, MAX_OUTPUT)
    budgets = [reader_budget()]
    checkpoint = current(home)
    registry = read_json(home/'dashboard/settlement/registry.json')
    pins = runtime_pins(home)
    qvalues = qualifications(home)
    protected, custody, bank, partition = protection(home, registry)
    previous, previous_sources = historical_plots(home)
    terrain = ExtentTerrain(home, checkpoint, registry)
    docs, plots, refusals = {}, [], []
    started, full_trials = time.monotonic(), 0
    tried = set()
    remaining_roots = {tuple(r[2]) for r in REMAINING}
    try:
        entities, entity_sources = dense.entity_positions(terrain.snapshot)
        if mode == 'remaining':
            intents = [(ident, species, [(None, root[0], root[2], root[1])]) for ident, species, root in REMAINING]
        else:
            intents = [('south47-'+str(i+1).zfill(2), NEW_SPECIES[i],
                        [(r, x, z, None) for r, x, z in intent_rows(bank, NEW_SPECIES[i], i)])
                       for i in range(min(len(NEW_SPECIES), count+9))]
        for ident, species, choices in intents:
            if mode == 'new' and len(plots) >= count:
                break
            if time.monotonic()-started > MAX_SECONDS or full_trials >= MAX_FULL_TRIALS:
                refusals.append({'id': ident, 'reason': 'Finite saved-source reader budget reached; no retry/generation fallback'})
                break
            found = False
            for measured, x, z, exact_y in choices:
                if (x, z, species) in tried:
                    continue
                tried.add((x, z, species))
                if time.monotonic()-started > MAX_SECONDS or full_trials >= MAX_FULL_TRIALS:
                    break
                try:
                    col = terrain.column(x, z)
                    if col.get('kind') != 'dry':
                        raise UserError('Root is not actual saved dry soil')
                    root = (x, col['surface_y']+1, z)
                    if exact_y is not None and root[1] != exact_y:
                        raise UserError('Historical remaining root ground changed')
                    if measured is not None and not connection(terrain, measured, x, z):
                        raise UserError('Offset root lacks an actual dry connection to the saved south-bank node')
                    q = qvalues[species]
                    write, known = envelopes(root, q['relative_write_bounds'])
                    old = [p for p in previous if mode != 'remaining' or tuple(p['root']) != root]
                    if conflict(write, known, old+plots):
                        raise UserError('Preserve prior successful/failed/lost/held or same-wave complete before field')
                    protect_envelope(write, protected)
                    if mode == 'new':
                        quick_field(terrain, root, write)
                    full_trials += 1
                    field, write, known, context_trees = dense.saved_plot(terrain, q, root, protected, entities)
                except UserError as error:
                    refusals.append({'id': ident, 'species': species, 'root_xz': [x, z], 'reason': str(error)})
                    continue
                plan = {'format': 'awft-native-tree-plan:1', 'seed': registry['seed'], 'world_path': registry['world_path'],
                        'saplings': [species], 'root': list(root), 'write_bounds': write, 'known_bounds': known}
                docs[ident+'/tree-plan.json'] = encoded(plan)
                docs[ident+'/before-VERIFY-ONLY.json'] = encoded(settlement_plan(registry, checkpoint, field,
                    'VERIFY ONLY current575 native normal/rare/mega/root/read field '+ident))
                docs[ident+'/qualification.json'] = encoded(q)
                plots.append({'id': ident, 'species': species, 'root': list(root), 'write_bounds': write,
                    'known_bounds': known, 'known_cells': len(field), 'read_only_retained_tree_cells': context_trees,
                    'all_normal_rare_mega_deep_root_variants_retained': True, 'saved_position_screen_clear': True,
                    'native_live_AABB_admission': False, 'potential_native_bee_slots': 3 if q['native_bee_nest_possible'] else 0,
                    'tree_plan_sha256': hashlib.sha256(docs[ident+'/tree-plan.json']).hexdigest(),
                    'source_candidate_has_not_been_natively_attempted': True})
                budgets.append(reader_budget())
                found = True
                break
            if not found:
                refusals.append({'id': ident, 'species': species, 'status': 'NO QUALIFIED PLOT; preserve failures and full envelopes'})
        sources = terrain.snapshot.sources.copy()
    finally:
        terrain.close()
    if mode == 'remaining' and {tuple(p['root']) for p in plots} != remaining_roots:
        # Retain a failed diagnostic without manufacturing a request-ready four.
        qualified = False
    else:
        qualified = len(plots) == (4 if mode == 'remaining' else count)
    docs['protection.json'] = encoded({'format': 'awft-native-tree-protection:1', 'seed': registry['seed'],
        'world_path': registry['world_path'], 'minimum_buffer_blocks': 5, 'includes_latest_plaza_routes_and_walks': True,
        'columns': [list(p) for p in sorted(protected)], 'custody': custody})
    manifest = {'format': 'awft-forest47-source:1', 'created': utcnow(), 'checkpoint_id': CHECKPOINT,
        'checkpoint_sha256': CHECKPOINT_SHA, 'source_sha256': digest(Path(__file__)), 'mode': mode,
        'requested_plots': 4 if mode == 'remaining' else count, 'qualified_plots': len(plots), 'all_requested_qualified': qualified,
        'plots': plots, 'species_counts': dict(Counter(p['species'] for p in plots)), 'reviewed_species_count': len(qvalues),
        'native_runtime': pins, 'north_partition': partition, 'exclusion_custody': custody,
        'historical_source_custody': previous_sources, 'all_old_plots_reserved_without_replay': True,
        'copse40_success_copse92_natural_false_and_lost_held_followons_not_rerolled': True,
        'field_cohort_pairwise_WRITE_vs_KNOWN_disjoint': True,
        'native_occupancy_bee_descriptor_noescape_cleanup_remain_gates': True,
        'potential_native_bee_slots': sum(p['potential_native_bee_slots'] for p in plots),
        'saved_entities_screened': len(entities), 'saved_entity_sources': entity_sources,
        'source_regions': sources, 'refusals': refusals, 'full_field_trials': full_trials,
        'native_actions': 0, 'world_writes': 0, 'handcrafted_tree_blocks': 0, 'growth_authority': False,
        'generation_requests_created': False, 'plot_readiness_created': False, 'reserve_guard': reserve,
        'reader_budgets': budgets, 'files': {name: {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
                                           for name, raw in docs.items()}}
    docs['manifest.json'] = encoded(manifest)
    if sum(map(len, docs.values())) > MAX_OUTPUT:
        raise UserError('Finite forest47 source allocation exceeded')
    output.mkdir()
    for name, raw in docs.items():
        path = output/name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    return {'directory': str(output), 'manifest_sha256': hashlib.sha256(docs['manifest.json']).hexdigest(),
            'qualified_plots': len(plots), 'all_requested_qualified': qualified, 'species_counts': manifest['species_counts'],
            'native_actions': 0}


def bind_requests(home, source_manifest, source_sha256, output, reviews):
    """Only parent-issued per-plot readiness can create requests; never install."""
    home, source_manifest, output = Path(home).resolve(), Path(source_manifest).resolve(), Path(output).resolve()
    if output.exists() or output.parent != home/'staging' or not source_manifest.is_relative_to(home/'staging'):
        raise UserError('New owned output and source receipt required')
    reserve = guard(MIB, 2*MIB)
    current(home)
    source = pilot.checked(source_manifest, source_sha256, 2*MIB)
    if (source.get('format') != 'awft-forest47-source:1' or source.get('checkpoint_sha256') != CHECKPOINT_SHA
            or source.get('world_writes') != 0 or source.get('reviewed_species_count') != 9):
        raise UserError('Fresh exact forest47 source required')
    pins = runtime_pins(home)
    if source.get('native_runtime') != pins:
        raise UserError('Native installed pack/helper/guard custody changed')
    plots = {p['id']: p for p in source['plots']}
    if not reviews or not set(reviews) <= plots.keys():
        raise UserError('Explicit nonempty parent-reviewed exact plot subset required')
    docs, requests = {}, []
    for ident, path in reviews.items():
        path = owned_regular(home, path, 128*1024)
        ready = read_json(path)
        if (ready.get('approval_scope') != 'one-exact-saved-tree-plot' or ready.get('checkpoint_sha256') != CHECKPOINT_SHA
                or ready.get('tree_plan_sha256') != plots[ident]['tree_plan_sha256']
                or any(ready.get(k) is not True for k in ('construction_complete', 'functional_commissioning_complete', 'visual_corrections_reviewed'))):
            raise UserError('Actual parent-issued bare-plot readiness must match current checkpoint and exact plan')
        refs = {}
        for role, name in (('plan', ident+'/tree-plan.json'), ('before', ident+'/before-VERIFY-ONLY.json'),
                           ('qualification', ident+'/qualification.json'), ('protection', 'protection.json')):
            member = source['files'][name]
            value = owned_regular(home, source_manifest.parent/name, MAX_OUTPUT)
            if value.stat().st_size != member['bytes'] or digest(value) != member['sha256']:
                raise UserError('Exact source field/qualification/protection member changed')
            refs[role] = pilot.owned_ref(home, value)
        request = {'format': 'awft-native-trees:1', 'allowed_operation': 'grow',
            **{k: pins[k] for k in ('candidate_version', 'bridge_version', 'pack_sha256')},
            **{k: v for k, v in pins['classes'].items() if k.startswith('native_')},
            'checkpoint_sha256': CHECKPOINT_SHA, 'current_backup': pilot.owned_ref(home, home/'dashboard/settlement/backup-receipt.json'),
            **refs, 'construction_ready': pilot.owned_ref(home, path)}
        raw = encoded(request)
        sha = hashlib.sha256(raw).hexdigest()
        bundle = 'trees-'+sha[:16]
        docs[bundle+'/request.json'] = raw
        requests.append({'id': ident, 'bundle': bundle, 'sha256': sha})
    receipt = {'format': 'awft-forest47-binding:1', 'source_manifest_sha256': source_sha256,
        'checkpoint_sha256': CHECKPOINT_SHA, 'native_runtime': pins, 'requests': requests,
        'approval_created': False, 'installed': False, 'native_actions': 0, 'reserve_guard': reserve}
    docs['binding-receipt.json'] = encoded(receipt)
    if sum(map(len, docs.values())) > 2*MIB:
        raise UserError('Finite source-only request budget exceeded')
    output.mkdir()
    for name, raw in docs.items():
        path = output/name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    return {'directory': str(output), 'requests': requests, 'binding_sha256': hashlib.sha256(docs['binding-receipt.json']).hexdigest(),
            'installed': False, 'native_actions': 0}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--home', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--mode', choices=('remaining', 'new'), default='remaining')
    parser.add_argument('--count', type=int, default=24)
    args = parser.parse_args()
    print(json.dumps(prepare(args.home, args.output, args.mode, args.count), indent=2))
