"""One fixed contained water-powered Keel Store mill, using Native plans only.

Dry installation and one-source wet activation are deliberately separate. This
is a source author, not a runtime executor, recipe simulator or observer.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import time
import zipfile

from control_room.common import UserError, digest, read_json, utcnow
from tools.artistic_captains_hall import native_payload
from tools.artistic_materials import require_material_rule
from tools.playtest import guard
from tools.settlement_attractions import BackupWorld
from tools.transport_create_shops import AIR, HUMAN, MIB, SOURCE_INDEX, SOURCE_INDEX_SHA, artifact_facts, key, route_body, state

MAX_OUTPUT = 2*MIB
CHIPPED_SHA = '18ac6fd6b30db4922ccc6ee8bea5b113f69587505b7529834f37ace506427291'
CHIPPED_BLOCKS_SHA = '418a0dda53f8d871e6587caabbb2b204db19fef7aa8ad4f1c85b6d29051bd659'
SEAL_PLANK = 'chipped:cross_laced_spruce_planks'
SOURCE = {'path': 'staging/eastern-shared-roofs-rich-source-1793241266230005000/keel-store-SOURCE-ONLY.json',
          'sha256': 'b869a317513d082d197a1bf3c16da4e55b1cedd421e291a8120aba5dd279ece5'}
WHEEL = (1329, 66, -1203)
WATER = (1329, 67, -1204)
MILL = (1325, 65, -1203)
CLUTCH = (1327, 66, -1203)
DRIVE_LEVER = (1327, 66, -1202)
FEED_LEVER = (1325, 67, -1202)
HOPPER = (1325, 66, -1203)
INPUT = (1325, 67, -1203)
SLABS = frozenset(((1329, 67, -1205), (1329, 67, -1201)))
TOP = 'minecraft:mangrove_slab[type=top,waterlogged=false]'
DOUBLE = 'minecraft:mangrove_slab[type=double,waterlogged=false]'
INTERIOR = frozenset((1329, y, z) for y in range(65, 68) for z in range(-1204, -1201))
SIDES = frozenset((x, y, z) for x in (1328, 1330) for y in range(65, 68) for z in range(-1204, -1201))
ENDS = frozenset((1329, y, z) for y in range(65, 68) for z in (-1205, -1201))
BASE_CAP = frozenset((1329, y, z) for y in (64, 68) for z in range(-1204, -1201))
STANDS = ((1326, 65, -1202), (1325, 65, -1201))


def layout(registry):
    def s(name, **props):
        return state(registry, name, **props)
    dry = {q: s('minecraft:glass') for q in SIDES}
    dry.update({q: s('minecraft:polished_blackstone_bricks') for q in ENDS-SLABS})
    dry.update({q: s('minecraft:mangrove_slab', type='double', waterlogged=False) for q in SLABS})
    dry.update({
        WHEEL: s('create:water_wheel', facing='west'),
        (1328, 66, -1203): s('create:gearbox', axis='y'),
        CLUTCH: s('create:clutch', axis='x', powered=True),
        (1326, 66, -1203): s('create:gearbox', axis='z'),
        (1326, 65, -1203): s('create:cogwheel', axis='y', waterlogged=False),
        MILL: s('create:millstone'),
        DRIVE_LEVER: s('minecraft:lever', face='wall', facing='south', powered=True),
        HOPPER: s('minecraft:hopper', facing='down', enabled=False),
        INPUT: s('minecraft:barrel', facing='west', open=False),
        FEED_LEVER: s('minecraft:lever', face='wall', facing='south', powered=True),
    })
    return dry


def geometry(registry, source):
    dry = layout(registry)
    full = {tuple(r[:3]): r[3] for r in source['complete_expected_state_context_ONLY']}
    walking = route_body(source) | {(x, y+dy, z) for x, y, z in STANDS for dy in (0, 1)}
    if set(dry) & walking or INTERIOR & walking:
        raise UserError('The fixed motor/mill must preserve every real shop route and operating body')
    if any(full.get(q) != (TOP if q in SLABS else AIR) for q in dry):
        raise UserError('Only31 source AIR cells and the two exact upper slabs may change')
    if any(full.get(q) != AIR for q in INTERIOR | walking):
        raise UserError('Retain literal source AIR for the full rotating wheel, water and walking volume')
    floor = {(x, 64, z) for x, _, z in set(dry) | set(STANDS)}
    retained = BASE_CAP | floor
    # All six actual wet faces are solid cubes after dry installation. Existing
    # upper slabs at the two end caps gain their missing bottom half; they are
    # not deleted or treated as watertight while half-height.
    if any(full.get(q) != SEAL_PLANK for q in BASE_CAP):
        raise UserError('Exact solid retained basin floor and ceiling are required')
    if any(q not in full or key(full[q]) in {AIR, 'minecraft:water', 'minecraft:lava'} for q in floor):
        raise UserError('Literal retained dry structural footing required')
    context = walking | retained | set(INTERIOR)
    for x, y, z in dry:
        context.update((x+dx, y+dy, z+dz) for dx, dy, dz in
                       ((1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1)))
    return dry, full, walking, retained, context-set(dry)


def derive(registry, source, actual, protected, canonical_sha):
    dry, full, walking, retained, context = geometry(registry, source)
    targets = set(dry) | context
    if set(actual) != targets or any(not isinstance(v, str) for v in actual.values()):
        raise UserError('Every finite current source predecessor/context cell is required')
    if any(any(all(b[i] <= q[i] <= b[i+3] for i in range(3)) for b in HUMAN) for q in targets):
        raise UserError('Owner tube/zipline reservations are excluded')
    if set(dry) & set(protected):
        raise UserError('No existing saved block entity may be rebuilt or inventoried by this proposal')
    if any(actual[q] != (TOP if q in SLABS else AIR) for q in dry):
        raise UserError('Current targets changed; preserve the object and hold this installation')
    if any(actual[q] != AIR for q in walking | INTERIOR):
        raise UserError('Current body/rotation/wet space is no longer clear')
    if any(actual[q] != full[q] for q in retained):
        raise UserError('Retained real floor/ceiling changed; never guess a water seal')
    after = {**actual, **dry}
    wet_static = {q: v for q, v in after.items() if q not in INTERIOR or q == WHEEL}
    wet_static[WATER] = state(registry, 'minecraft:water', level=0)
    def plan(blocks, name, *, place=False):
        return native_payload(registry, blocks, canonical_sha, name, placement=place)
    return {
        'dry-before-VERIFY-ONLY.json': plan(actual, 'Keel Store exact stopped preimage; not a live permission'),
        'retained-seal-and-footing-VERIFY-ONLY.json': plan({q: actual[q] for q in retained}, 'Keel Store retained solid basin ceiling/floor and dry foundations'),
        'dry-hardware-PROPOSAL.json': plan(dry, 'Keel Store contained wheel/gearbox/clutch/real mill; two specific slab bottom-halves added', place=True),
        'dry-normal-joins-SETTLE-ONLY.json': plan(dry, 'Keel Store dry native attachment and redstone reconciliation'),
        'dry-complete-after-VERIFY-ONLY.json': plan(after, 'Keel Store dry empty machine; actual feed-locked hopper and stopped clutch required'),
        'water-before-after-dry-VERIFY-ONLY.json': plan(after, 'VERIFY actual completed dry machine before any water; source is a future condition, not a receipt'),
        'one-water-source-PROPOSAL.json': plan({WATER: wet_static[WATER]}, 'ONE water source only AFTER genuine dry/full/support proof; ordinary bucket preferred', place=True),
        'post-water-stopped-static-VERIFY-ONLY.json': plan(wet_static, 'Actual source and unchanged external seal/walk/drive; interior flowing levels require native observation'),
    }


def seal_artifact_facts(create_jar):
    chipped = Path(create_jar).with_name('chipped-neoforge-1.21.1-4.0.2.jar')
    if digest(chipped) != CHIPPED_SHA:
        raise UserError('Exact installed Chipped artifact required for this retained seal material')
    with zipfile.ZipFile(chipped) as archive:
        raw = archive.read('earth/terrarium/chipped/common/registry/ModBlocks.class')
        if hashlib.sha256(raw).hexdigest() != CHIPPED_BLOCKS_SHA:
            raise UserError('Pinned exact spruce-plank/full Block factory changed')
    return {'jar_sha256': CHIPPED_SHA, 'ModBlocks_class_sha256': CHIPPED_BLOCKS_SHA,
            'retained_exact_material': SEAL_PLANK,
            'primary_factory_facts': 'SPRUCE_PLANKS uses vanilla Blocks.SPRUCE_PLANKS + PLANKS palette + DEFAULT_CREATOR; DEFAULT_CREATOR is vanilla Block constructor; createProperties uses ofFullCopy/noLootTable',
            'native_fluid_seal_test_completed': False}


def prepare(home, checkpoint_id, checkpoint_sha, create_jar):
    home = Path(home).resolve()
    if home.parent != Path(r'D:\A World for Two\staging\world-tests').resolve():
        raise UserError('Declared separate construction source home only')
    if not re.fullmatch(r'\d{8}T\d{6}Z-[a-f0-9]{6}', checkpoint_id):
        raise UserError('An exact stopped recovery checkpoint is required')
    reserve = guard(8*MIB, MAX_OUTPUT)
    receipt = read_json(home/'backups'/(checkpoint_id+'.json'))
    if receipt.get('integrity') != 'verified' or receipt.get('sha256') != checkpoint_sha:
        raise UserError('Immutable recovery companion must agree')
    if digest(home/SOURCE_INDEX) != SOURCE_INDEX_SHA or digest(home/SOURCE['path']) != SOURCE['sha256']:
        raise UserError('Fixed current built39/Keel Store source identity changed')
    source = read_json(home/SOURCE['path'])
    native = read_json(home/'dashboard/settlement/backup-receipt.json')
    if native.get('verified') is not True or not re.fullmatch('[a-f0-9]{64}', native.get('sha256', '')):
        raise UserError('Separate verified canonical Native backup identity required')
    registry = read_json(home/'dashboard/settlement/registry.json')
    facts = artifact_facts(create_jar)
    seal_facts = seal_artifact_facts(create_jar)
    dry, _, _, _, context = geometry(registry, source)
    snapshot = BackupWorld(home, {**receipt, 'id': checkpoint_id, 'verified': True}, registry)
    try:
        actual = {q: snapshot.state(q) for q in sorted(set(dry) | context)}
        raw = derive(registry, source, actual, snapshot.protected, native['sha256'])
        region_sources = list(snapshot.sources)
    finally:
        snapshot.close()
    manifest = {
        'format': 'awft-keel-store-continuous-mill-SOURCE:1', 'created': utcnow(),
        'producer_sha256': digest(Path(__file__)), 'shared_shop_source_sha256': digest(Path(__file__).with_name('transport_create_shops.py')),
        'actual_saved_checkpoint': {'id': checkpoint_id, 'sha256': checkpoint_sha},
        'canonical_native_backup_sha256': native['sha256'], 'retained_current_shop_source': SOURCE,
        'new_dry_cells': len(dry), 'previous_AIR_cells': len(dry)-len(SLABS),
        'exact_existing_upper_slabs_gain_bottom_half_only': [list(q) for q in sorted(SLABS)],
        'existing_inventory_or_BE_targets': 0, 'supplied_Items_or_recipe_products': 0,
        'water_source': list(WATER), 'wet_volume_including_wheel': [list(q) for q in sorted(INTERIOR)],
        'full_six_face_seal': {'sides': [list(q) for q in sorted(SIDES)], 'ends': [list(q) for q in sorted(ENDS)],
                             'retained_floor_ceiling': [list(q) for q in sorted(BASE_CAP)],
                             'shaft_port_is_full_native_gearbox': [1328, 66, -1203]},
        'wheel_model_clearance': 'Full3x3 same-X plane, no pre-existing wood/shelves/joists in its rotation volume',
        'drive': {'wheel': list(WHEEL), 'clutch': list(CLUTCH), 'stop_lever': list(DRIVE_LEVER), 'millstone': list(MILL),
                  'source_expected_speed_abs_if_native_flow_score_nonzero': 8, 'native_RPM_stress_or_flow_observed': False},
        'feed': {'input_barrel': list(INPUT), 'hopper': list(HOPPER), 'feed_stop_lever': list(FEED_LEVER),
                 'actual_locked_hopper_required_after_normal_joins': True, 'max_first_batch_wheat': 16},
        'operating_feet': STANDS, 'installed_artifact_facts': facts, 'retained_seal_factory': seal_facts,
        'material_rule': require_material_rule(dry, 'Keel Store contained continuous mill'),
        'saved_region_sources': region_sources, 'reserve_guard': reserve,
        'files': {n: {'sha256': hashlib.sha256(b).hexdigest(), 'bytes': len(b)} for n, b in raw.items()},
        'required_order': ['fresh actual dry BEFORE/support', 'one dry PLACE', 'normal joins', 'strict full dry AFTER including native stop/feed states',
                           'verify actual dry/seal again', 'one ordinary water bucket/source', 'actual source/unchanged shell/outside-water check',
                           'release actual drive clutch; prove real rotation/stress', 'count wheat into actual barrel',
                           'release actual feed lock; observe hopper/mill processing', 'actual output and full-slot count conservation',
                           'stop feed and drive; actual input exhausted/no drops', 'normal save/restart and actual re-use'],
        'native_actions': 0, 'world_writes': 0, 'runtime_or_observation_framework_added': False,
        'status': 'SOURCE ONLY; dry/wet phases, flow, stress, hopper lock, processing, idle impact and restart remain UNVERIFIED',
    }
    raw['manifest.json'] = (json.dumps(manifest, separators=(',', ':'))+'\n').encode()
    if sum(map(len, raw.values())) > MAX_OUTPUT:
        raise UserError('Finite2MiB source cap exceeded')
    out = home/'staging'/('transport-create-continuous-'+str(time.time_ns()))
    out.mkdir()
    for name, data in raw.items():
        (out/name).open('xb').write(data)
    return {'folder': str(out), 'manifest_sha256': digest(out/'manifest.json'),
            'bytes': sum(map(len, raw.values())), 'dry_cells': len(dry),
            'new_source_water_cells': 1, 'native_actions': 0, 'world_writes': 0}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--home', type=Path, required=True)
    parser.add_argument('--checkpoint-id', required=True)
    parser.add_argument('--checkpoint-sha', required=True)
    parser.add_argument('--create-jar', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.home, args.checkpoint_id, args.checkpoint_sha, args.create_jar), indent=2))
