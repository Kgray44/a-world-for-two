"""Three concrete saved-field sapling reviews; no native command or growth request.

The normal/rare envelopes are sealed primary-source derivations authenticated
against the actual43 descriptor receipt. A future parent-owned runtime must bind
its own compiled guard hashes, fresh checkpoint and narrowly truthful readiness.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import time
import zipfile
from pathlib import Path

from control_room.common import UserError, digest, read_json, utcnow
from tools.artistic_bridge_refinement import encoded
from tools.artistic_south_extent import ExtentTerrain
from tools.artistic_south_forest import AIR, GROUND, exclusions
from tools.artistic_whole_bank_forest import protection as legacy_protection
from tools.artistic_zipline_catenary import reader_budget
from tools.native_tree_growth import collect_known, envelopes, native_plan, protect_envelope
from tools.playtest import guard
from tools.settlement_attractions import base

MIB = 1024**2
MAX_OUTPUT = 16*MIB
MAX_SECONDS = 90
CHECKPOINT = '20261028T022348Z-3c15d0'
CHECKPOINT_SHA = '0ae2cd00d57269b35d15ecc96a6d9d7e2c44f88f8e39d3ec5522cee4037229e8'
V2_SOURCE_CHECKPOINT_SHA = 'ec13e5399acd12d65290f70663b381d68103b45287e9421dedbc1ac62d86afac'
NATIVE_CANDIDATE = '0.1.0-candidate.45'
NATIVE_BRIDGE = '0.6.31'
NATIVE_JAR_SHA = 'd5126437fb6e041d9a6f2bb021cb81f9721092b76399fc34156ccd111a02e815'
R3 = Path('D:/A World for Two/staging/native-tree-envelopes-20261028T0007Z-r3')
R3_SHA = 'ee9a28c1d9ecca96622e65feb098fa7f5536ec797c15fea9fd13253442f9325d'
DESCRIBE = 'dashboard/settlement/tree-growth-result-08258b13-86b9-401a-aaf3-b33725c1ed00.json'
DESCRIBE_SHA = '8c767ba8505846eeb4e305d4691e853cd48461d3d7ff5591f9dbfa45c44a3cc5'
BEE_R2 = Path('D:/A World for Two/staging/native44-tree-bee-r2-20261028T0040Z/source-freeze.json')
BEE_R2_SHA = 'b1ccf527d98a3ade55d7f084083409063050eaf5dea0349ecdce816f01effd81'
BANK = 'staging/whole-bank-forest-1793142176587217900'
BANK_MANIFEST_SHA = 'd79c83cf12eb3f01de27e40752bd01655cd41de75de16251f31f1b615ad46484'
V2 = 'staging/zipline-west-v2-source-1793152099836099800/future-v2-growth-and-construction-reservation.json'
V2_SHA = '72ad9665eb2e5b75d54cf3acee6ad4b012f7b82b62ab5547115bc7d1e69af9a0'
EXTRA = (
    ('Placed Rose Reach including protected AIR', 'staging/north-bank-rose-reach-1793151923325885400/prototype.json',
     '831a8e6eb1e757502328d259d0846fff14e325e8ed704dae527cd7fc90cdbc37'),
    ('Future bridge topside and ten-wide walking body', 'staging/artistic-bridge-topside-20261028T0128Z/future-reservation-ONLY.json',
     'd6d6963d437d89824b012274b06f6b36600c82ca4acc1fe713e0ab4a3a3a657c'),
    ('Future five western shops and connected routes', 'staging/north-bank-west-five-final-20261028T0200Z/future-solid-AIR-route-reservation-ONLY.json',
     'c5236daf51002d6297f72e56c3b49561f0ccb2b91de301b2c5a02d9d443be17a'),
    ('Future six-paver lane connector', 'staging/north-bank-six-paver-connector-1793152430034475900/six-paver-connector.json',
     'aec6cb1d5e21614b987c35b749e9ee25b30ba611196287856d9ae9505ed633e2'),
    ('Actual Compass Bend all solid/AIR/routes', 'staging/north-bank-compass-bend-1793156177505399400/prototype.json',
     'cc83762b5e3e8476dc2e26ade1d84c21bca545e937d64938cbf0f43afa393b1e'),
    ('Actual eastern22 all solid/AIR/routes', 'staging/north-bank-eastern22-1793157301590833400/prototype.json',
     '956b58ce5a68a008fb7e3e099962c3f51712af604072a77fd2f81d6b7668375c'),
)
PLOTS = (
    ('birch-meadow', 'minecraft:birch_sapling', (1080, 67, -1088)),
    ('magnolia-glade', 'regions_unexplored:magnolia_sapling', (1080, 67, -1144)),
    ('larch-bank', 'regions_unexplored:larch_sapling', (1032, 66, -1128)),
)
NATIVE_SOFT = {'minecraft:'+n for n in (
    'short_grass', 'tall_grass', 'fern', 'large_fern', 'dandelion', 'poppy',
    'cornflower', 'oxeye_daisy', 'allium', 'azure_bluet', 'lily_of_the_valley',
    'blue_orchid', 'dead_bush', 'snow')}
NATIVE_SOFT.add('regions_unexplored:grass_sprouts')
ROOT_SOIL = {'minecraft:'+n for n in ('grass_block', 'dirt', 'coarse_dirt', 'rooted_dirt', 'podzol', 'moss_block', 'mycelium')}


def checked(path, expected, cap):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or not 0 < path.stat().st_size <= cap or digest(path) != expected:
        raise UserError('Exact bounded source member differs: '+path.name)
    return read_json(path)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()


def qualifications(home, root=R3):
    seal = checked(root/'source-freeze.json', R3_SHA, MIB)
    receipt = checked(root/'receipt.json', seal['qualification_receipt_sha256'], MIB)
    native = checked(home/DESCRIBE, DESCRIBE_SHA, 2*MIB)
    if (receipt.get('qualification_count') != 9 or receipt.get('actual_describe_sha256') != DESCRIBE_SHA
            or native.get('operation') != 'describe' or native.get('failures') != 0
            or native.get('cleanup_passed') is not True or native.get('temporary_tickets_remaining') != 0
            or native.get('pending_shared_futures') != 0):
        raise UserError('Nine sealed qualifications and actual clean native43 describe receipt required')
    values = {}
    for _, sapling, _ in PLOTS:
        name = sapling.replace(':', '--')+'.json'
        q = checked(root/name, receipt['files'][name]['sha256'], 128*1024)
        if (q.get('sapling') != sapling or q.get('all_reachable_features_reviewed') is not True
                or q.get('native_descriptor_sha256') != native['native_descriptor_sha256s'][sapling]
                or hashlib.sha256(canonical(q['derivation'])).hexdigest() != q['derivation_sha256']
                or q['relative_write_bounds'] != q['derivation']['relative_write_bounds']):
            raise UserError('Native descriptor, complete variant envelope or derivation identity differs')
        values[sapling] = q
    checked(BEE_R2, BEE_R2_SHA, MIB)
    return values


def protected_columns(home, registry):
    columns, custody = legacy_protection(home, registry)
    extra, facts = exclusions([(name, home/path, sha) for name, path, sha in EXTRA], registry)
    columns.update(extra)
    custody.extend(facts)
    bank_meta = checked(home/BANK/'manifest.json', BANK_MANIFEST_SHA, MIB)
    bank = checked(home/BANK/'composition.json', bank_meta['proposal_sha256'], 4*MIB)
    columns.update(map(tuple, bank['walking_whole_growth_skirt_xz']))
    v2 = checked(home/V2, V2_SHA, 4*MIB)
    if (v2.get('route_id') != 'rosewater-cliff-western-town-v2' or v2.get('native_plan') is not False
            or v2.get('growth_authority') is not False or v2.get('checkpoint_sha256') != V2_SOURCE_CHECKPOINT_SHA):
        raise UserError('Exact unbuilt western v2 route/frame/station/approach reservation required')
    columns.update(map(tuple, v2['all_growth_excluded_columns_xz']))
    # Forestry/woodland only. North-town façade gardens use their explicit
    # architectural owner authority instead of borrowing this tree permission.
    from tools.artistic_dense_canopies import north_partition, NORTH_MASK_SHA
    north, partition = north_partition(home, registry)
    columns.update(north)
    custody.append({'name': 'All actual1m northern connected land, including unbuilt infill, plus5m',
                    'sha256': NORTH_MASK_SHA, 'north_south_components_disjoint': True})
    custody.extend(({'name': 'Whole-bank source walking bodies plus five-metre skirt', 'sha256': bank_meta['proposal_sha256']},
                    {'name': 'Western v2 flight, frame, stations and authored cliff approach', 'sha256': V2_SHA,
                     'superseded_v1_masks_are_not_used': True}))
    if len(columns) > 200000:
        raise UserError('Native finite protection table exceeded')
    return columns, custody, bank


def review_plot(terrain, registry, checkpoint, q, root, protected):
    root = tuple(root)
    write, known = envelopes(root, q['relative_write_bounds'])
    relative_known = [known[i]-root[i % 3] for i in range(6)]
    if relative_known != q['derivation']['relative_known_bounds']:
        raise UserError('Complete R3 read/physics perimeter changed')
    protect_envelope(write, protected)
    column = terrain.column(root[0], root[2])
    if column.get('kind') != 'dry' or column.get('existing_canopy_y') is not None or column.get('surface_y') != root[1]-1:
        raise UserError('Root must be immediately above the actual bare saved dry ground')

    class Adapter:
        @property
        def protected(self):
            return terrain.entities

        def state(self, position):
            return terrain.state(*position)

    field, soil = collect_known(Adapter(), known, write, root)
    if any(all(known[i] <= p[i] <= known[i+3] for i in range(3)) for p in terrain.entities):
        raise UserError('Preserve all existing BEs throughout the complete read/physics perimeter')
    if base(field[root]) not in AIR | NATIVE_SOFT or base(field[root[0], root[1]-1, root[2]]) not in ROOT_SOIL:
        raise UserError('Native sapling root needs actual replaceable ground cover and retained dirt-family support')
    for p, state in field.items():
        if not all(write[i] <= p[i] <= write[i+3] for i in range(3)):
            continue
        key = base(state)
        if key in ('minecraft:water', 'minecraft:lava', 'minecraft:dirt_path') or 'waterlogged=true' in state:
            raise UserError('Native root/crown volume must preserve channels, wet ground and existing paths')
        if p[1] >= root[1] and key not in AIR | NATIVE_SOFT and not (p[1] <= root[1]+2 and key in GROUND):
            raise UserError('Preserve crop, native furnishing or other obstruction in potential growth volume')
    return field, {'root': list(root), 'write_bounds': write, 'known_bounds': known, 'known_cells': len(field),
                   'ground_id_counts': soil, 'saved_root_state': field[root],
                   'saved_support_state': field[root[0], root[1]-1, root[2]],
                   'native_bee_nest_possible': q['native_bee_nest_possible'],
                   'reserved_native_bee_slots': 3 if q['native_bee_nest_possible'] else 0,
                   'reserved_native_nest_slots': 1 if q['native_bee_nest_possible'] else 0,
                   'current_runtime_rebinding_required': True, 'native_growth_tested': False}


def prepare(home, output):
    home, output = Path(home).resolve(), Path(output).resolve()
    if output.exists() or not output.is_relative_to(home/'staging'):
        raise UserError('New private pilot folder below the owned staging home required')
    reserve = guard(MIB, MAX_OUTPUT)
    started = time.monotonic()
    budgets = [reader_budget()]
    registry = read_json(home/'dashboard/settlement/registry.json')
    checkpoint = {'id': CHECKPOINT, 'sha256': CHECKPOINT_SHA, 'verified': True}
    current = read_json(home/'dashboard/settlement/backup-receipt.json')
    if current.get('verified') is not True or any(current.get(key) != checkpoint[key] for key in ('id', 'sha256')):
        raise UserError('The exact newly stopped pilot checkpoint is required; no stale source replay')
    qvalues = qualifications(home)
    protected, custody, bank = protected_columns(home, registry)
    bank_nodes = set(map(tuple, bank['bank_nodes_xz']))
    if any((root[0], root[2]) not in bank_nodes for _, _, root in PLOTS):
        raise UserError('Each pilot is on the measured continuous south-bank component')
    docs = {}
    plots = []
    terrain = ExtentTerrain(home, checkpoint, registry)
    try:
        for ident, sapling, root in PLOTS:
            if time.monotonic()-started > MAX_SECONDS:
                raise UserError('Finite saved pilot reader expired; no automatic retry')
            budgets.append(reader_budget())
            q = qvalues[sapling]
            field, facts = review_plot(terrain, registry, checkpoint, q, root, protected)
            plan = {'format': 'awft-native-tree-plan:1', 'seed': registry['seed'], 'world_path': registry['world_path'],
                    'saplings': [sapling], 'root': list(root), 'write_bounds': facts['write_bounds'], 'known_bounds': facts['known_bounds']}
            docs[ident+'/tree-plan.json'] = encoded(plan)
            docs[ident+'/tree-before-VERIFY-ONLY.json'] = encoded(native_plan(registry, checkpoint, field,
                'VERIFY ONLY - '+ident+' complete saved normal/rare crown, deep roots and physics/read perimeter'))
            docs[ident+'/native-qualification.json'] = encoded(q)
            plots.append({'id': ident, 'sapling': sapling, **facts,
                          'native_descriptor_sha256': q['native_descriptor_sha256'], 'derivation_sha256': q['derivation_sha256'],
                          'tree_plan_sha256': hashlib.sha256(docs[ident+'/tree-plan.json']).hexdigest()})
        sources = terrain.snapshot.sources.copy()
        raw_mca = terrain.raw_bytes
        budgets.append(reader_budget())
    finally:
        terrain.close()
    mask = {'format': 'awft-native-tree-protection:1', 'seed': registry['seed'], 'world_path': registry['world_path'],
            'minimum_buffer_blocks': 5, 'includes_latest_plaza_routes_and_walks': True,
            'columns': [list(p) for p in sorted(protected)], 'custody': custody,
            'source_checkpoint_sha256': CHECKPOINT_SHA, 'future_masks_are_not_placed_evidence': True}
    docs['tree-protection.json'] = encoded(mask)
    recipe = {'format': 'awft-three-native-sapling-pilot:1', 'created': utcnow(), 'checkpoint_id': CHECKPOINT,
              'checkpoint_sha256': CHECKPOINT_SHA, 'plots': plots, 'scope': 'Three bare reviewed plots; not whole-world construction acceptance',
              'exclusion_custody': custody, 'native43_descriptor_receipt_sha256': DESCRIBE_SHA,
              'sealed_nine_species_R3_sha256': R3_SHA, 'required_native_bee_R2_source_sha256': BEE_R2_SHA,
              'reserved_native_bee_slots': sum(p['reserved_native_bee_slots'] for p in plots),
              'reserved_native_nest_slots': sum(p['reserved_native_nest_slots'] for p in plots),
              'bee_slots_are_capacity_not_spawn_counts': True, 'native_saplings_or_trees_placed': 0, 'animals_seeded': 0,
              'native_generation_request_created': False, 'construction_ready_document_created': False,
              'required_next_gates': ['Parent-owned actual45 compiled tree/scope/guard/bee class identity',
                  'Fresh current checkpoint, unchanged exact saved fields and all-current masks',
                  'Truthful plot-scoped construction/function/art readiness, not a whole-town completion claim',
                  'Native Level hook witness, fresh actual descriptor equality and complete native before admission',
                  'One unforced native sapling attempt transaction at a time; retain actual outcome and bee census',
                  'Normal restart, actual native tree appearance and habitat review before wider growth or LIFE']}
    docs['pilot-recipe-REVIEW-ONLY.json'] = encoded(recipe)
    manifest = {'format': 'awft-three-native-sapling-pilot-receipt:1', 'created': utcnow(), 'source_sha256': digest(Path(__file__)),
                'checkpoint_id': CHECKPOINT, 'checkpoint_sha256': CHECKPOINT_SHA, 'status': 'SAVED SOURCE REVIEW ONLY',
                'plots': plots, 'source_regions': sources, 'MCA_raw_bytes': raw_mca, 'reserve_guard': reserve,
                'reader_budgets': budgets, 'native_actions': 0, 'world_writes': 0, 'growth_authority': False,
                'native_class_hashes_pending': True, 'files': {name: {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
                                                          for name, raw in docs.items()}}
    docs['manifest.json'] = encoded(manifest)
    if sum(map(len, docs.values())) > MAX_OUTPUT:
        raise UserError('Finite pilot output budget exceeded')
    output.mkdir(parents=True, exist_ok=False)
    for name, raw in docs.items():
        path = output/name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    return {'directory': str(output), 'manifest_sha256': hashlib.sha256(docs['manifest.json']).hexdigest(),
            'plots': [{'id': p['id'], 'root': p['root'], 'known_cells': p['known_cells']} for p in plots],
            'native_actions': 0, 'world_writes': 0}


def owned_ref(home, path):
    original = Path(path)
    path = original.resolve()
    if original.is_symlink() or not path.is_relative_to(home) or not path.is_file():
        raise UserError('Native requests may reference ordinary files inside their exact owned stage only')
    return {'path': path.relative_to(home).as_posix(), 'bytes': path.stat().st_size, 'sha256': digest(path)}


def runtime_pins(home):
    """Read installed actual45 bytes only; loading/activation is a native gate."""
    active = read_json(home/'packwiz/active.json')
    installed = read_json(home/'server/installed.json')
    if (active.get('version') != NATIVE_CANDIDATE or installed.get('pack_version') != NATIVE_CANDIDATE
            or active.get('pack_sha256') != installed.get('pack_sha256')):
        raise UserError('Matching installed private45 pack custody required')
    jar = home/'server/mods'/('awft-control-bridge-'+NATIVE_BRIDGE+'.jar')
    if not jar.is_file() or jar.is_symlink() or not 0 < jar.stat().st_size <= MIB or digest(jar) != NATIVE_JAR_SHA:
        raise UserError('Exact compiled actual45 bridge JAR required; do not fabricate native class pins')
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
                raise UserError('Bounded actual45 native class required')
            classes[key] = hashlib.sha256(archive.read(member)).hexdigest()
    return {'candidate_version': NATIVE_CANDIDATE, 'bridge_version': NATIVE_BRIDGE,
            'pack_sha256': active['pack_sha256'], 'compiled_jar': owned_ref(home, jar),
            'classes': classes, 'native_activation_proved_by_this_read': False}


def bind_requests(home, source_manifest, source_sha256, output, reviews=None):
    """Bind real class hashes now; require explicit per-plot review to emit grow.

    Without reviews only a binding receipt is emitted. No placeholder command or
    request can be installed accidentally. This function never creates approval.
    """
    home, source_manifest, output = Path(home).resolve(), Path(source_manifest).resolve(), Path(output).resolve()
    if output.exists() or not output.is_relative_to(home/'staging') or not source_manifest.is_relative_to(home/'staging'):
        raise UserError('New owned output and immutable private source bundle required')
    reserve = guard(MIB, 2*MIB)
    source = checked(source_manifest, source_sha256, MIB)
    if (source.get('format') != 'awft-three-native-sapling-pilot-receipt:1' or source.get('checkpoint_id') != CHECKPOINT
            or source.get('checkpoint_sha256') != CHECKPOINT_SHA or source.get('world_writes') != 0):
        raise UserError('Exact current three-plot review receipt required')
    current = read_json(home/'dashboard/settlement/backup-receipt.json')
    if current.get('verified') is not True or current.get('sha256') != CHECKPOINT_SHA or current.get('id') != CHECKPOINT:
        raise UserError('Current stopped receipt changed; recollect every saved pilot cell')
    pins = runtime_pins(home)
    folder = source_manifest.parent
    refs = {}
    for name, facts in source['files'].items():
        path = folder/name
        if not path.resolve().is_relative_to(folder) or path.stat().st_size != facts['bytes']:
            raise UserError('Pilot member path/size custody differs')
        checked(path, facts['sha256'], MAX_OUTPUT)
        refs[name] = owned_ref(home, path)
    docs = {}
    requests = []
    if reviews is not None:
        if set(reviews) != {p['id'] for p in source['plots']}:
            raise UserError('Exactly three independently reviewed plot approvals required')
        for plot in source['plots']:
            ident = plot['id']
            approval_path = Path(reviews[ident]).resolve()
            approval_ref = owned_ref(home, reviews[ident])
            if not 0 < approval_ref['bytes'] <= 128*1024:
                raise UserError('Bounded explicit plot readiness required')
            approval = read_json(approval_path)
            if (approval.get('approval_scope') != 'one-exact-saved-tree-plot'
                    or approval.get('checkpoint_sha256') != CHECKPOINT_SHA
                    or approval.get('tree_plan_sha256') != plot['tree_plan_sha256']
                    or any(approval.get(k) is not True for k in ('construction_complete', 'functional_commissioning_complete', 'visual_corrections_reviewed'))):
                raise UserError('Truthful exact plot-scoped readiness is required; no generic or whole-world approval fallback')
            request = {'format': 'awft-native-trees:1', 'allowed_operation': 'grow',
                       **{k: pins[k] for k in ('candidate_version', 'bridge_version', 'pack_sha256')},
                       **{k: v for k, v in pins['classes'].items() if k.startswith('native_')},
                       'checkpoint_sha256': CHECKPOINT_SHA,
                       'current_backup': owned_ref(home, home/'dashboard/settlement/backup-receipt.json'),
                       'plan': refs[ident+'/tree-plan.json'], 'before': refs[ident+'/tree-before-VERIFY-ONLY.json'],
                       'protection': refs['tree-protection.json'], 'qualification': refs[ident+'/native-qualification.json'],
                       'construction_ready': approval_ref}
            raw = encoded(request)
            sha = hashlib.sha256(raw).hexdigest()
            bundle = 'trees-'+sha[:16]
            docs[bundle+'/request.json'] = raw
            requests.append({'plot': ident, 'bundle': bundle, 'request_sha256': sha,
                             'installation_or_native_actions': False})
    receipt = {'format': 'awft-three-native-sapling-binding:1', 'created': utcnow(), 'source_manifest_sha256': source_sha256,
               'source_generator_sha256': digest(Path(__file__)), 'checkpoint_sha256': CHECKPOINT_SHA,
               'runtime': pins, 'requests': requests, 'generation_requests_created': bool(requests),
               'approval_created': False, 'installed': False, 'native_actions': 0, 'reserve_guard': reserve,
               'note': 'Request preparation is not installed hook, native growth, restart or visual acceptance'}
    docs['binding-receipt.json'] = encoded(receipt)
    if sum(map(len, docs.values())) > 2*MIB:
        raise UserError('Finite class binding/request output budget exceeded')
    output.mkdir(parents=True, exist_ok=False)
    for name, raw in docs.items():
        target = output/name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
    return {'directory': str(output), 'binding_sha256': hashlib.sha256(docs['binding-receipt.json']).hexdigest(),
            'generation_requests_created': bool(requests), 'native_actions': 0}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--home', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    arguments = parser.parse_args()
    print(json.dumps(prepare(arguments.home, arguments.output), indent=2))
