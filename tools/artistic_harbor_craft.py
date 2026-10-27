"""A real cog/tender commissioning proposal and its small shore-fitted landing.

This module writes private staging documents only. No entity command, generic
summon, network call or world writer exists here. A native server integration
must admit and create the actual entities in one server-thread transaction.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import uuid

from control_room.common import Layout, REPO, UserError, atomic_write, digest, read_json, utcnow
from control_room.storage import Storage
from tools.artistic_materials import material_runs, require_material_rule
from tools.settlement import Plan
from tools.settlement_maritime_attractions import (
    AIR, WATER, COG_NAME, COG_POSITION, SMALLSHIPS_SOURCE,
    VANILLA_BOAT_DIMENSIONS, box_cells, cog_boxes, inspect_pins, overlap,
)


NAME = 'Sea Glass landing and working harbor craft'
TENDER_NAME = 'Wren harbor tender'
TENDER_POSITION = (1194.5, 63.1, -1253.5)
BOUND = (1194, 61, -1264, 1201, 67, -1251)
MAX_POSITIONS = 6000
MAX_OUTPUT = 8 * 1024**2
NOTCH = {(1197, 64, -1260): 'minecraft:spruce_planks',
         (1198, 64, -1260): 'chipped:detailed_dark_oak_planks'}
PASSABLE = {AIR, 'minecraft:water'}


def raw(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False)+'\n').encode('utf-8')


def sha(value):
    return hashlib.sha256(raw(value)).hexdigest()


def states(document, registry):
    if (document.get('format') != 'awft-native-settlement:1' or document.get('commands')
            or (document.get('seed'), document.get('world_path')) != (registry['seed'], registry['world_path'])):
        raise UserError('Use exact command-free authored geometry from this staging world')
    result = {}
    for row in document.get('blocks', []):
        if len(row) != 4 or any(type(n) is not int for n in row):
            raise UserError('Invalid existing harbor position')
        x, y, z, i = row
        if (x, y, z) in result or not 0 <= i < len(document['palette']):
            raise UserError('Invalid or duplicate existing harbor position')
        result[x, y, z] = document['palette'][i]
    if not result or len(result) > 100_000:
        raise UserError('Existing geometry exceeds the finite staging input bound')
    return result


def padded(box, margin=.35):
    return tuple(box[n]-margin if n < 3 else box[n]+margin for n in range(6))


def boat_box(position=TENDER_POSITION):
    half = VANILLA_BOAT_DIMENSIONS['width']/2
    x, y, z = position
    return (x-half, y, z-half, x+half, y+VANILLA_BOAT_DIMENSIONS['height'], z+half)


def regions():
    cog = [padded(box) for box in cog_boxes(COG_POSITION, 180)]
    # Passenger clearance is separate from the six native ship-part boxes.
    cog.append((1194.75, 65, -1268, 1198.25, 68, -1260.25))
    departure = [(b[0], b[1], b[2]-8, b[3], b[4], b[5]) for b in cog]
    departure.append((1194, 60, -1278, 1199, 63, -1259))
    tender = [padded(boat_box()), (1193.45, 64, -1254.55, 1195.55, 66.5, -1252.45)]
    tender_departure = [(b[0]-8, b[1], b[2], b[3], b[4], b[5]) for b in tender]
    tender_departure.append((1185, 61, -1255, 1196, 63, -1252))
    return {'cog-berth': cog, 'cog-north-departure': departure,
            'tender-berth': tender, 'tender-west-departure': tender_departure}


class CraftPlan:
    def __init__(self, registry, survey, existing, backup):
        self.registry, self.native, self.rotation = registry, registry['blocks'], 0
        self.existing, self.backup = dict(existing), backup
        self.blocks, self.tags, self.before = {}, {}, {}
        self.protected = {tuple(p) for row in survey.get('samples', []) for p in row.get('block_entities', [])}
        self.samples = {(row['x'], row['z']): row for row in survey.get('samples', [])}
        report = survey.get('report', {})
        if (not self.samples or len(self.samples) > 5000 or report.get('status') != 'complete'
                or report.get('failures') != 0 or any(row.get('source') != 'actual generated native chunk surface'
                                                    for row in self.samples.values())):
            raise UserError('Use the completed actual native west-harbor profile')

    def state(self, key, **properties):
        if key not in self.native or properties.keys()-self.native[key].keys():
            raise UserError('Unregistered native craft block/property: '+key)
        return Plan.state(self, key, **properties)

    def prior(self, pos):
        if pos in self.existing:
            return self.existing[pos]
        x, y, z = pos
        gx, gz = 4*math.floor(x/4), 4*math.floor(z/4)
        keys = {(gx, gz), (gx+4, gz), (gx, gz+4), (gx+4, gz+4)}
        if keys-self.samples.keys():
            raise UserError('A craft check lies beyond the bounded actual marine profile')
        rows = [self.samples[key] for key in keys]
        if (any(not row.get('fluid') or row.get('y') != 63 or row.get('block', '').split('[')[0] != 'minecraft:water'
                for row in rows) or y < max(row['ocean_floor_y'] for row in rows)):
            raise UserError('Do not guess a dry bank, sea plant or seabed; exact native verification is required')
        return WATER if y < 63 else AIR

    def put(self, pos, key, **properties):
        if (len(pos) != 3 or any(type(n) is not int for n in pos)
                or any(not BOUND[n] <= pos[n] <= BOUND[n+3] for n in range(3))):
            raise UserError('The small harbor-craft delta exceeded its reviewed reserve')
        if pos in self.protected:
            raise UserError('An existing block entity is protected')
        desired = self.state(key, **properties)
        previous = self.prior(pos)
        if pos in self.existing and previous != desired and NOTCH.get(pos) != previous:
            raise UserError('Only the two reviewed plain-deck notch cells may replace existing construction')
        self.before[pos] = previous
        if previous != desired:
            self.blocks[pos] = desired

    def final(self, pos):
        if pos in self.blocks:
            return self.blocks[pos]
        return self.prior(pos)


def landing(p):
    for pos, expected in NOTCH.items():
        if p.existing.get(pos) != expected:
            raise UserError('The reviewed two-cell pier corner changed; do not cut another block')
        p.put(pos, AIR)
    # East of the true cog multipart AABBs: a low apron around, rather than
    # through, the existing northern crane upright. Five-point route below.
    for x in range(1199, 1202):
        for z in range(-1263, -1260):
            key = ('chipped:detailed_dark_oak_planks' if x == 1201 else
                   'chipped:nailed_dark_oak_planks' if z == -1263 else 'minecraft:spruce_planks')
            p.put((x, 64, z), key)
    for z in range(-1263, -1259):
        p.put((1201, 63, z), 'minecraft:dark_oak_log', axis='z')
    p.put((1201, 65, -1263), 'minecraft:dark_oak_fence')
    p.put((1201, 66, -1263), 'minecraft:lantern', hanging=False, waterlogged=False)
    p.put((1200, 65, -1261), 'minecraft:barrel', facing='south', open=False)
    p.tags[1200, 65, -1261] = '{CustomName:'+json.dumps(json.dumps({'text':'Sea Glass: shore spares'}))+',Items:[]}'
    # A distinct west-facing tender berth, beyond the cog's body and route.
    for z in range(-1255, -1251):
        p.put((1196, 64, z), 'chipped:nailed_dark_oak_planks' if z == -1254 else 'minecraft:spruce_planks')
    # Water-return ladder is outside the boat envelope and the west launch.
    for y in range(62, 66):
        p.put((1196, y, -1251), 'minecraft:stripped_dark_oak_log', axis='y')
    for y in range(62, 65):
        p.put((1195, y, -1251), 'minecraft:ladder', facing='west', waterlogged=y < 63)
    p.put((1196, 66, -1251), 'minecraft:dark_oak_fence')
    routes = {
        'cog boarding apron': [(1201, 64, -1260), (1201, 64, -1261), (1201, 64, -1262),
                               (1200, 64, -1262), (1199, 64, -1262)],
        'tender boarding edge': [(1197, 64, -1253), (1196, 64, -1253)],
    }
    walking = set()
    for name, cells in routes.items():
        for x, y, z in cells:
            if p.final((x, y, z)).split('[')[0] in PASSABLE:
                raise UserError('The planned landing lacks a real floor: '+name)
            for yy in (y+1, y+2):
                pos = x, yy, z
                if p.final(pos).split('[')[0] != AIR:
                    raise UserError('A landing prop blocks the native boarding approach: '+name)
                walking.add(pos)
    return routes, walking


def document(p, blocks, name, tags=None):
    if not blocks or len(blocks) > MAX_POSITIONS:
        raise UserError('A finite command-free craft plan is required')
    palette = sorted(set(blocks.values()))
    indices = {state: n for n, state in enumerate(palette)}
    return {'format': 'awft-native-settlement:1', 'name': name, 'created': utcnow(),
            'seed': p.registry['seed'], 'world_path': p.registry['world_path'], 'backup_sha256': p.backup,
            'bounds': [min(v[0] for v in blocks), min(v[2] for v in blocks),
                       max(v[0] for v in blocks), max(v[2] for v in blocks)],
            'palette': palette, 'blocks': [[*pos, indices[state]] for pos, state in sorted(blocks.items())],
            'block_entities': [{'pos': list(pos), 'nbt': tag} for pos, tag in (tags or {}).items()],
            'commands': [], 'landmarks': [], 'validation': 'STAGED ONLY; exact native admission remains required'}


def entity_request(registry, name, kind, position):
    ident = uuid.uuid5(uuid.NAMESPACE_URL, 'awft-artistic:'+str(registry['seed'])+':'+name)
    integers = [int.from_bytes(ident.bytes[n:n+4], 'big', signed=True) for n in range(0, 16, 4)]
    cog = kind == 'smallships:cog'
    extra = (',Sail:{State:0b,Color:"white",SailHealth:100f},HullDamage:0f,Sunken:0b,Sinking:0b,locked:0b,Items:[]'
             if cog else '')
    nbt = ('{UUID:[I;'+','.join(map(str, integers))+'],CustomName:'+json.dumps(json.dumps({'text': name}))+
           ',PersistenceRequired:1b,Type:"spruce",Rotation:['+('180f' if cog else '90f')+
           ',0f],Motion:[0d,0d,0d],Tags:["awft_artistic_harbor_craft_v1"]'+extra+'}')
    return {'entity': kind, 'uuid': str(ident), 'name': name, 'position': list(position),
            'yaw': 180 if cog else 90, 'nbt_snbt': nbt, 'wood': 'spruce',
            'ownership': 'Shared unlocked craft; no forged account owner, invulnerability or passenger',
            'creation': 'Native typed server-thread load and add after all same-tick gates; never generic summon',
            'status': 'NOT CREATED; native entity loading, boarding, controls, cargo and restart unverified'}


def proposal(registry, survey, existing_document, backup):
    for key in ('smallships:cog', 'smallships:ship_part', 'minecraft:boat'):
        if key not in registry.get('entities', []):
            raise UserError('A required actual native craft entity is absent: '+key)
    existing = states(existing_document, registry)
    p = CraftPlan(registry, survey, existing, backup)
    p.protected.update(tuple(row['pos']) for row in existing_document.get('block_entities', []))
    routes, walking = landing(p)
    composite = {**existing, **p.blocks}
    material = require_material_rule(p.blocks, NAME)
    if any(row['exceeds_nine'] for row in material_runs(composite)):
        raise UserError('The addition joins an outdoor harbor material run longer than nine')
    clearance = {}
    shapes = regions()
    for boxes in shapes.values():
        for pos in set().union(*(box_cells(box) for box in boxes)):
            state = p.final(pos)
            if pos in p.protected or state.split('[')[0] not in PASSABLE:
                raise UserError('Real craft body, passenger or departure clearance intersects construction: '+str(pos))
            clearance[pos] = state
    # Cog berth as well as departure needs real depth, not just surface water.
    for x in range(1194, 1199):
        for z in range(-1270, -1258):
            for y in (60, 61, 62):
                pos = x, y, z
                if p.prior(pos) != WATER:
                    raise UserError('The conservative three-block cog water column is not available')
                clearance[pos] = WATER
    for pos in walking:
        clearance[pos] = p.final(pos)
    before = {**clearance, **p.before}
    # Before the small deck notch, these exact cells still contain old planks.
    for pos in NOTCH:
        before[pos] = existing[pos]
    physical = document(p, p.blocks, NAME, p.tags)
    verify_before = document(p, before, 'Craft landing exact prior-state check')
    water_air = document(p, clearance, 'Craft water and passenger clearance VERIFY ONLY')
    requests = [entity_request(registry, COG_NAME, 'smallships:cog', COG_POSITION),
                entity_request(registry, TENDER_NAME, 'minecraft:boat', TENDER_POSITION)]
    binding = sha({'seed': registry['seed'], 'world_path': registry['world_path'], 'backup_sha256': backup})
    admission = {'format': 'awft-artistic-craft-admission:1', 'world_binding': binding,
                 'dimension': 'minecraft:overworld', 'maximum_snapshot_age_ticks': 0,
                 'regions': shapes, 'required_water_air_sha256': sha(water_air),
                 'requests': {row['entity']: row['uuid'] for row in requests},
                 'phases': {'cog-create': ['cog-berth', 'cog-north-departure'],
                            'cog-depart': ['cog-berth', 'cog-north-departure'],
                            'tender-create': ['tender-berth', 'tender-west-departure'],
                            'tender-depart': ['tender-berth', 'tender-west-departure']},
                 'query_provider': 'Actual ServerLevel AABBs after every target chunk FULL and entity-ready',
                 'duplicate_custody': 'Actual loaded and persistent/unloaded entity UUID custody; spatial absence alone never authorizes creation',
                 'atomicity': 'All block, AABB, UUID custody checks and typed creation/motion on the same server tick; recheck before each phase',
                 'category_exemptions': [], 'unrecognized_entity_policy': 'Reject pets, boats, dropped items, passengers and all unlisted occupants',
                 'status': 'Native integration and authentic receipts required; fixture tests are not live evidence'}
    output = {'format': 'awft-artistic-harbor-craft-proposal:1', 'name': NAME, 'created': utcnow(),
              'physical_plan': physical, 'entity_requests': requests, 'admission': admission,
              'boarding': {'cog': [1199.5, 65, -1261.5], 'tender': [1196.5, 65, -1253.5],
                           'water_return_ladder': [1195, 62, -1251], 'routes': routes,
                           'instructions': 'Right-click the actual hull from the marked apron; demonstrate native boarding and both users before calling it usable'},
              'departure': {'cog': 'Bow north: first eight blocks north, then inspect water before turning',
                            'tender': 'First eight blocks west into open water; never turn into the pier'},
              'materials': material, 'whole_harbor_max9': 'PASS source geometry, all outdoor blocks included',
              'hoist': 'Not commissioned by this landing. Existing harbor crane remains stopped; no boat retention or lifting claim.',
              'native_world_mutations': 0, 'status': 'STAGED ONLY; no entity, world edit, control or restart acceptance'}
    return output, verify_before, water_air


def admit(contract, snapshot, block_receipt, custody, phase, now_tick):
    """Pure adapter contract for authentic native observations, not an API call."""
    names = contract['phases'].get(phase)
    expected = contract['requests']['smallships:cog' if phase.startswith('cog-') else 'minecraft:boat']
    if (not names or type(now_tick) is not int or type(snapshot.get('game_time')) is not int
            or snapshot.get('game_time') != now_tick
            or snapshot.get('format') != 'awft-native-artistic-craft-occupancy:1'
            or snapshot.get('world_binding') != contract['world_binding']
            or snapshot.get('contract_sha256') != sha(contract)
            or snapshot.get('dimension') != contract['dimension']
            or snapshot.get('all_target_chunks_entity_ready') is not True
            or snapshot.get('regions_scanned') != names):
        raise UserError('Actual same-tick complete native AABB observations are required')
    if (block_receipt.get('format') != 'awft-native-artistic-craft-blocks:1'
            or type(block_receipt.get('game_time')) is not int or block_receipt.get('game_time') != now_tick
            or block_receipt.get('operation') != 'verify' or block_receipt.get('status') != 'complete'
            or type(block_receipt.get('failures')) is not int or block_receipt.get('failures') != 0
            or block_receipt.get('all_target_chunks_full') is not True
            or block_receipt.get('sha256') != contract['required_water_air_sha256']
            or block_receipt.get('world_binding') != contract['world_binding']):
        raise UserError('Actual same-tick exact water/air native verification is required')
    creating = phase.endswith('-create')
    if (custody.get('format') != 'awft-native-artistic-craft-custody:1'
            or type(custody.get('game_time')) is not int or custody.get('game_time') != now_tick
            or custody.get('world_binding') != contract['world_binding']
            or custody.get('loaded_and_persistent_entity_storage_complete') is not True
            or custody.get('uuid') != expected
            or custody.get('matches') != (0 if creating else 1)):
        raise UserError('Moved/unloaded UUID custody must be proven independently of spatial absence')
    rows = snapshot.get('entities')
    if not isinstance(rows, list):
        raise UserError('Native entities are missing')
    boxes = [box for name in names for box in contract['regions'][name]]
    observed, seen = False, set()
    for row in rows:
        bounds = row.get('bounds', [])
        if (len(bounds) != 6 or any(type(v) not in (int, float) or not math.isfinite(v) for v in bounds)
                or any(bounds[n] >= bounds[n+3] for n in range(3))):
            raise UserError('A native entity AABB is invalid')
        try:
            ident = str(uuid.UUID(row.get('uuid', '')))
        except (ValueError, TypeError, AttributeError) as exc:
            raise UserError('A native entity UUID is invalid') from exc
        if ident in seen:
            raise UserError('Native observations must deduplicate entity UUIDs')
        seen.add(ident)
        if not any(overlap(bounds, box) for box in boxes):
            continue
        kind = row.get('entity')
        authorized = not creating and ident == expected and kind == ('smallships:cog' if phase.startswith('cog-') else 'minecraft:boat')
        if authorized:
            observed = True
        elif (not creating and phase == 'cog-depart' and kind == 'smallships:ship_part'
              and row.get('native_parent_uuid') == expected):
            authorized = True
        if not authorized:
            raise UserError('A pet, item, boat or other unauthorized spatial entity blocks commissioning')
    if not creating and not observed:
        raise UserError('The commissioned craft was not actually observed in its launch region')
    return {'phase': phase, 'game_time': now_tick, 'scope': 'Pure admission result; native execution and player acceptance remain separate'}


def prepare(home, *, survey_path, survey_sha256, harbor_plan, harbor_sha256, cache_home,
            extra_survey_path=None, extra_survey_sha256=None):
    layout = Layout(Path(home))
    Storage(layout).reserve(MAX_OUTPUT)
    owner = read_json(layout.state/'artistic-owner.json', {})
    if (owner.get('format') != 'awft-artistic-stage:1' or owner.get('owner_source') != str(REPO)
            or Path(owner.get('home', '')).resolve() != layout.home
            or not any(path.name == 'staging' for path in layout.home.parents)):
        raise UserError('Use the explicitly owned isolated artistic staging home')
    registry = read_json(layout.state/'settlement/registry.json')
    backup = read_json(layout.state/'settlement/backup-receipt.json', {})
    if (not Path(registry['world_path']).resolve().is_relative_to(layout.world.resolve())
            or not backup.get('verified') or owner.get('backup_sha256') != backup.get('sha256')
            or not re.fullmatch('[a-f0-9]{64}', str(backup.get('sha256', '')))):
        raise UserError('The isolated native registry and current verified backup must match staging ownership')
    documents = []
    for path, expected, root in ((Path(survey_path).resolve(), survey_sha256, layout.home),
                                 (Path(harbor_plan).resolve(), harbor_sha256, layout.staging)):
        if not path.is_relative_to(root) or not path.is_file() or path.stat().st_size > 4*1024**2 or digest(path) != expected:
            raise UserError('Use the exact bounded immutable staging survey and completed harbor geometry')
        documents.append(read_json(path))
    if bool(extra_survey_path) != bool(extra_survey_sha256):
        raise UserError('An additional current-world survey needs its exact reviewed SHA')
    survey = documents[0]
    if extra_survey_path:
        path = Path(extra_survey_path).resolve()
        if (not path.is_relative_to(layout.home) or not path.is_file() or path.stat().st_size > 4*1024**2
                or digest(path) != extra_survey_sha256):
            raise UserError('Use the exact bounded native departure extension survey')
        extra = read_json(path)
        # Validate each real survey independently before joining their samples.
        CraftPlan(registry, extra, {}, backup['sha256'])
        merged = {(row['x'], row['z']): row for row in survey['samples']}
        for row in extra['samples']:
            key = row['x'], row['z']
            if key in merged:
                previous = merged[key]
                # The second profile was taken after the authored pier/crane.
                # It extends missing coordinates only: a crane top must never
                # become an inferred seabed or excuse clearing a current block.
                # Every added/clearance cell still needs an exact live probe.
                row = {**previous, 'block_entities': [list(pos) for pos in
                       {tuple(pos) for value in (previous, row) for pos in value.get('block_entities', [])}]}
            merged[key] = row
        survey = {**survey, 'samples': list(merged.values())}
    pins = inspect_pins(Path(cache_home))
    data, before, water_air = proposal(registry, survey, documents[1], backup['sha256'])
    contents = {'proposal.json': raw(data), 'expected-before.json': raw(before), 'water-air-verify-only.json': raw(water_air)}
    if sum(map(len, contents.values()))+1024**2 > MAX_OUTPUT:
        raise UserError('The complete private craft bundle exceeds its finite reserved allocation')
    identity = sha(data)
    output = layout.staging/('artistic-harbor-craft-'+identity[:16])
    if output.exists():
        raise UserError('Preserve the existing immutable craft proposal')
    output.mkdir()
    for name, content in contents.items():
        atomic_write(output/name, content.decode('utf-8'))
    manifest = {'format': 'awft-artistic-harbor-craft:1', 'created': utcnow(), 'source_sha256': digest(Path(__file__)),
                'backup_id': backup.get('id'), 'backup_sha256': backup['sha256'],
                'survey_sha256': survey_sha256, 'extra_survey_sha256': extra_survey_sha256,
                'extra_survey_scope': 'Missing coordinates extend the original marine-floor hypothesis; all overlapping BE observations unioned; exact live verification remains mandatory',
                'harbor_plan_sha256': harbor_sha256,
                'documents': {name: {'sha256': digest(output/name), 'bytes': len(content)} for name, content in contents.items()},
                'physical_positions': len(data['physical_plan']['blocks']), 'explicit_nbt_tags': len(data['physical_plan']['block_entities']),
                'typed_entity_requests': 2, 'commands': 0, 'clearance_positions': len(water_air['blocks']),
                'dependency_inspection': pins, 'official_smallships_source': SMALLSHIPS_SOURCE,
                'camera_poses': [{'name': 'cog boarding from apron', 'world_feet': [1200.5, 65, -1262.5], 'yaw': 90, 'pitch': 5},
                                 {'name': 'tender and return ladder', 'world_feet': [1197.5, 65, -1254.5], 'yaw': 90, 'pitch': 20}],
                'status': 'STAGED ONLY; native integration, placement, creation, controls, multiplayer and restart remain unverified'}
    atomic_write(output/'manifest.json', raw(manifest).decode('utf-8'))
    return {'directory': str(output), 'manifest_sha256': digest(output/'manifest.json'), **manifest}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--home', type=Path, required=True)
    parser.add_argument('--survey', type=Path, required=True)
    parser.add_argument('--survey-sha256', required=True)
    parser.add_argument('--harbor-plan', type=Path, required=True)
    parser.add_argument('--harbor-sha256', required=True)
    parser.add_argument('--cache-home', type=Path, required=True)
    parser.add_argument('--extra-survey', type=Path)
    parser.add_argument('--extra-survey-sha256')
    args = parser.parse_args()
    result = prepare(args.home, survey_path=args.survey, survey_sha256=args.survey_sha256,
                     harbor_plan=args.harbor_plan, harbor_sha256=args.harbor_sha256, cache_home=args.cache_home,
                     extra_survey_path=args.extra_survey, extra_survey_sha256=args.extra_survey_sha256)
    print(json.dumps({key: result[key] for key in ('directory', 'manifest_sha256', 'physical_positions', 'typed_entity_requests', 'status')}))
