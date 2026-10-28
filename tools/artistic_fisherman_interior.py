"""Furnish the exact imported Shabani1 fisherman shop; saved-source proposals only.

The original litematic/exterior is an immutable private input, never copied into
this source. This module neither opens live region files nor invokes Minecraft.
"""
from __future__ import annotations

import argparse
from collections import deque
import hashlib
import json
from pathlib import Path
import time
import zipfile

from control_room.backups import Backups
from control_room.common import Layout, UserError, digest, read_json, utcnow
from tools.artistic_maritime_depth import admit_owner, key, states
from tools.artistic_materials import require_material_rule
from tools.playtest import guard
from tools.settlement_attractions import BackupWorld


AIR = 'minecraft:air'
VOID = {AIR, 'minecraft:cave_air', 'minecraft:void_air'}
FLOOR = {'minecraft:grass_block', 'minecraft:dirt', 'minecraft:coarse_dirt'}
SOFT = {'minecraft:short_grass', 'minecraft:tall_grass', 'minecraft:lily_of_the_valley',
        'minecraft:fern', 'regions_unexplored:grass_sprouts'}
ROOM = (1319, 63, -1339, 1326, 73, -1329)
SOURCE = 'staging/artistic-requested-originals-rebind-20261027T1810Z/shop-adapted.json'
SOURCE_SHA = '410be015fe8fc26f450dfd8075cb9bd543dcae8de8f52cfb9a60ea68720cb60e'
ORIGINAL_SHA = '2a1ecefcdbba55f86480318107dfd396ba7c98d2731711e811b5cdd0e39b5309'
MAX_OUTPUT = 16 * 1024**2
TAG_APIS = (
    ('caches/mods/FarmersDelight-1.21.1-1.3.4.jar', 3160490,
     '139ad7696462c89c03eea463f805abffa552526c5dadaadae221dd9624cb197c',
     'vectorwing/farmersdelight/common/block/entity/CuttingBoardBlockEntity.class',
     '0eaaf1ca9d00d04cc26466fb8ef05f4acd7508edc4d61f7581949fb273a6df70'),
    ('server/libraries/net/neoforged/neoforge/21.1.262/neoforge-21.1.262-universal.jar', 3554347,
     '4070305f97a08409d9b4e714f619f0ec2d97d29c9939ef43a89d927259942f98',
     'net/neoforged/neoforge/items/ItemStackHandler.class',
     '9d842a44ed64512baca32d64f2726a93d62603dfc46448c71e8fd416dc604122'),
)
DOORS = ((1322, 64, -1340), (1323, 64, -1340),
         (1322, 64, -1328), (1323, 64, -1328))
CAMERAS = (
    {'name': 'fish-shop-south-door', 'feet': [1322.5, 64, -1338.5], 'look_at': [1320.5, 66, -1334.5]},
    {'name': 'fish-shop-service-counter', 'feet': [1323.5, 64, -1335.5], 'look_at': [1320, 66, -1336]},
    {'name': 'fish-shop-cooking-and-stair', 'feet': [1323.5, 64, -1331.5], 'look_at': [1326, 66, -1330]},
    {'name': 'fish-shop-loft', 'feet': [1323.5, 71, -1330.5], 'look_at': [1320, 72, -1330]},
    {'name': 'fish-shop-north-door', 'feet': [1322.5, 64, -1329.5], 'look_at': [1323, 68, -1335]},
)


class Byte(int):
    """Literal native TAG_BYTE, specifically vanilla container Slot fields."""


def snbt(value):
    """Controlled literal data, with distinct vanilla BYTE and NeoForge INT slots."""
    if isinstance(value, Byte):
        if not -128 <= value <= 127:
            raise UserError('Native byte exceeds its finite range')
        return str(int(value)) + 'b'
    if type(value) is bool:
        return '1b' if value else '0b'
    if type(value) is int:
        return str(value)
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, list):
        return '[' + ','.join(snbt(v) for v in value) + ']'
    if isinstance(value, dict) and all(isinstance(k, str) for k in value):
        return '{' + ','.join(json.dumps(k) + ':' + snbt(v) for k, v in value.items()) + '}'
    raise UserError('Only reviewed literal shop furnishing tags are permitted')


class Interior:
    def __init__(self, registry, snapshot, original):
        self.registry, self.snapshot, self.original = registry, snapshot, dict(original)
        self.blocks, self.before, self.phases, self.tags = {}, {}, {}, {}
        self.supports, self.lights, self.scenes, self.workstations = {}, [], [], []
        self.cleared_plants, self.floor_retained, self.approaches = [], {}, []
        self.phase = 1
        self.body = {(x, y, z) for x in (1322, 1323)
                     for z in range(-1339, -1328) for y in (64, 65)}
        # Service access is an actual one-wide aisle behind the deep counter.
        self.body.update((1320, y, z) for z in range(-1336, -1332) for y in (64, 65))
        self.body.update((1324, y, z) for z in range(-1333, -1328) for y in (64, 65))
        self.body.update((1325, y, z) for z in range(-1331, -1328) for y in (64, 65))
        self.body.update((x, y, -1339) for x in (1324, 1325, 1326) for y in (64, 65))

    def at(self, pos):
        return self.blocks[pos] if pos in self.blocks else self.snapshot.state(pos)

    def state(self, block, **props):
        native = self.registry['blocks'].get(block)
        if native is None:
            raise UserError('Missing actual native shop fitting: ' + block)
        for name, value in props.items():
            if name not in native or str(value).lower() not in native[name]:
                raise UserError('Invalid actual native shop state: ' + block + ' ' + name)
        return block + ('[' + ','.join(k + '=' + str(v).lower() for k, v in sorted(props.items())) + ']' if props else '')

    def put(self, pos, block, *, floor=False, clear=False, **props):
        if any(type(n) is not int for n in pos) or not all(ROOM[i] <= pos[i] <= ROOM[i + 3] for i in range(3)):
            raise UserError('Shop fitting exceeds the measured inner room')
        old = self.snapshot.state(pos)
        if pos in self.snapshot.protected or pos in self.original:
            raise UserError('Preserve every original/player/default block entity and exterior cell: ' + str(pos))
        if floor:
            if pos[1] != 63 or key(old) not in FLOOR:
                raise UserError('Only explicitly measured ordinary soil may become flush indoor flooring')
        elif key(old) not in VOID | SOFT:
            raise UserError('Preserve unknown/player interior progress: ' + str(pos) + ' ' + key(old))
        after = self.state(block, **props)
        if pos in self.body and after != AIR:
            raise UserError('Keep both doorways, central passage and service aisles clear')
        if pos in self.blocks and self.blocks[pos] != after:
            # Only the explicitly cleared native weeds can be replaced by a new
            # fitting. Geometry from another furnishing scene is never erased.
            if self.blocks[pos] != AIR or key(old) not in SOFT:
                raise UserError('Two shop fitting scenes overlap: ' + str(pos))
        self.blocks[pos], self.before[pos], self.phases[pos] = after, old, self.phase
        if clear:
            self.cleared_plants.append(list(pos))
        if len(self.blocks) > 1400:
            raise UserError('Split the small fisherman interior proposal')

    def support(self, pos):
        value = self.at(pos)
        if key(value) in VOID | SOFT | {'minecraft:water', 'minecraft:lava'}:
            raise UserError('A fitting lacks actual retained/new support: ' + str(pos))
        if pos not in self.blocks:
            self.supports[pos] = value

    def on_floor(self, x, y, z, block, **props):
        self.support((x, y - 1, z))
        self.put((x, y, z), block, **props)

    def lamp(self, x, y, z):
        self.on_floor(x, y, z, 'minecraft:lantern', hanging=False, waterlogged=False)
        self.lights.append([x, y, z])

    def stand(self, x, y, z, block='chipped:boxed_spruce_planks'):
        self.on_floor(x, y, z, block)

    def counter(self, x, z):
        self.on_floor(x, 64, z, 'handcrafted:spruce_counter', counter='andesite', facing='east', type=1)

    def chair(self, x, y, z, facing):
        self.on_floor(x, y, z, 'handcrafted:spruce_chair', color='brown', facing=facing, waterlogged=False)

    def table(self, x, y, z):
        self.on_floor(x, y, z, 'handcrafted:spruce_table', color='none', shape='single', waterlogged=False)

    def notice(self, x, y, z, facing, lines):
        dx, dz = {'east': (-1, 0), 'west': (1, 0), 'north': (0, 1), 'south': (0, -1)}[facing]
        self.support((x + dx, y, z + dz))
        self.put((x, y, z), 'minecraft:spruce_wall_sign', facing=facing, waterlogged=False)
        self.tags[x, y, z] = {'front_text': {'messages': [json.dumps({'text': line}, separators=(',', ':')) for line in lines],
            'color': 'white', 'has_glowing_text': False}, 'is_waxed': True}

    def stock(self, pos, name, stacks):
        if key(self.blocks.get(pos, AIR)) != 'minecraft:barrel':
            raise UserError('Stock belongs only to a newly authored barrel')
        items = []
        for slot, (item, count) in enumerate(stacks):
            if item not in self.registry['items'] or not 1 <= count <= 16:
                raise UserError('Stock must use actual pinned items and modest literal counts')
            items.append({'Slot': Byte(slot), 'id': item, 'count': count})
        self.tags[pos] = {'CustomName': json.dumps({'text': name}, separators=(',', ':')), 'Items': items}

    def scene(self, name, details, approaches):
        self.scenes.append({'name': name, 'details': details, 'approaches': [list(v) for v in approaches]})
        self.approaches.extend(approaches)


def construct(p):
    # Clear only measured indoor native weeds, including both halves. No vine,
    # imported prop, old inventory, nest, exterior planting or tree is erased.
    for x in range(1319, 1327):
        for z in range(-1339, -1328):
            for y in (64, 65):
                pos = x, y, z
                if key(p.snapshot.state(pos)) in SOFT:
                    p.put(pos, AIR, clear=True)
            floor = x, 63, z
            if key(p.snapshot.state(floor)) in FLOOR:
                material = ('minecraft:stripped_spruce_log' if z in (-1336, -1332)
                            else 'chipped:cross_laced_spruce_planks' if x in (1322, 1323)
                            else 'chipped:pegged_spruce_planks')
                p.put(floor, material, floor=True, **({'axis': 'x'} if material.endswith('_log') else {}))
            else:
                # Four ordinary retained willow stumps can become honest flush
                # joints. Anything else is a fresh-read refusal, not a clearance.
                if key(p.snapshot.state(floor)) != 'regions_unexplored:willow_log':
                    raise UserError('Unknown interior floor progress must be preserved/reviewed')
                p.floor_retained[floor] = p.snapshot.state(floor)
                p.supports[floor] = p.snapshot.state(floor)

    # A real supported timber mezzanine occupies only the rear four metres.
    # The tall front room/teal roof silhouette and every old window remain.
    for x in (1319, 1326):
        for y in range(64, 69):
            p.put((x, y, -1332), 'chipped:nailed_spruce_log', axis='y')
    for x in range(1319, 1327):
        if x < 1325:
            p.put((x, 69, -1332), 'chipped:carved_stripped_spruce_log', axis='x')
        for z in range(-1332, -1328):
            if not (x >= 1325 and z == -1332):
                p.put((x, 70, z), 'chipped:cross_laced_spruce_planks' if x in (1322, 1323) else 'chipped:pegged_spruce_planks')
    for index, z in enumerate(range(-1338, -1331)):
        y = 64 + index
        for x in (1325, 1326):
            if index:
                p.put((x, y - 1, z), 'chipped:reinforced_spruce_log', axis='z')
            p.put((x, y, z), 'minecraft:spruce_stairs', facing='south', half='bottom', shape='straight', waterlogged=False)
    for x in range(1319, 1325):
        p.put((x, 71, -1332), 'minecraft:dark_oak_fence', north=False, south=False,
              east=x != 1324, west=x != 1319, waterlogged=False)
    # A continuous inner stair rail is a rooted diagonal run, not a floating net.
    for index, z in enumerate(range(-1338, -1332)):
        p.put((1324, 64 + index, z), 'chipped:reinforced_spruce_log', axis='z')
        p.put((1324, 65 + index, z), 'minecraft:spruce_fence', north=False, south=False,
              east=True, west=False, waterlogged=False)

    # Retain the first phase before fixtures replace some cleared weeds. Its
    # explicit AIR writes make phase2's preimage independent of plant decay.
    p.structural = dict(p.blocks)
    p.phase = 2
    # Deep L counter, an actual fish on the cutting board, service aisle behind,
    # specimen mounts and wrapping stock, all below the original windows.
    for z in (-1337, -1336, -1335):
        p.counter(1321, z)
    p.counter(1320, -1337)
    p.stand(1319, 64, -1337)
    p.lamp(1319, 65, -1337)
    p.on_floor(1321, 65, -1336, 'farmersdelight:cutting_board', facing='east', waterlogged=False)
    # Pinned FD1.3.4 loadAdditional reads Inventory; NeoForge21.1.262
    # ItemStackHandler serializes Size/Slot as INT, unlike vanilla BYTE slots.
    p.tags[1321, 65, -1336] = {'Inventory': {'Size': 1, 'Items': [{'Slot': 0, 'id': 'minecraft:salmon', 'count': 1}]},
                              'IsItemCarved': False}
    p.on_floor(1321, 65, -1335, 'handcrafted:blue_glazed_thin_pot')
    p.on_floor(1321, 64, -1334, 'create:depot', waterlogged=False)
    p.workstations.append({'pos': [1321, 64, -1334], 'block': 'create:depot',
        'purpose': 'Real manual catch/parcel staging surface; empty, no powered automation claimed'})
    p.on_floor(1319, 64, -1335, 'minecraft:barrel', facing='east', open=False)
    p.stock((1319, 64, -1335), 'Morning catch & wrapping', [('minecraft:cod', 8), ('minecraft:salmon', 6), ('minecraft:paper', 12)])
    p.stand(1319, 65, -1335)
    p.put((1319, 66, -1335), 'chipped:nailed_spruce_log', axis='y')
    # This is a tabletop specimen mount backed by its own solid standard.
    p.put((1319, 67, -1335), 'chipped:nailed_spruce_log', axis='y')
    p.put((1320, 67, -1335), 'handcrafted:tropical_fish_trophy', facing='east', waterlogged=False)
    p.support((1319, 67, -1335))
    p.notice(1320, 66, -1335, 'east', ('TODAY\'S CATCH', 'Cod & salmon', 'Cleaned to order', 'Bring a basket'))
    p.scene('The tide counter', ['Deep slate-topped L counter and walk-behind service aisle',
        'Actual one-salmon cutting-board stock, native manual Create depot, two modeled fish specimens, wrapping barrel'],
        [(1322, 64, -1336), (1320, 64, -1334)])

    # A compact but real back kitchen. Empty smoker/cooking stations do not burn
    # staged goods while native verification is in progress.
    p.on_floor(1326, 64, -1331, 'minecraft:smoker', facing='west', lit=False)
    p.on_floor(1326, 64, -1330, 'minecraft:water_cauldron', level=2)
    p.on_floor(1326, 64, -1329, 'farmersdelight:spruce_cabinet', facing='west', open=False)
    p.on_floor(1319, 64, -1333, 'minecraft:crafting_table')
    p.on_floor(1325, 64, -1333, 'farmersdelight:stove', facing='west', lit=False)
    p.on_floor(1325, 65, -1333, 'farmersdelight:cooking_pot', facing='west', support='tray', waterlogged=False)
    p.put((1326, 67, -1331), 'handcrafted:kitchen_hood', facing='west', waterlogged=False)
    p.put((1326, 68, -1331), 'handcrafted:kitchen_hood_pipe', facing='west', corner=False, waterlogged=False)
    p.put((1326, 69, -1331), 'chipped:reinforced_spruce_log', axis='y')
    p.lamp(1319, 65, -1333)
    p.workstations.extend({'pos': list(pos), 'block': block, 'purpose': use} for pos, block, use in (
        ((1326, 64, -1331), 'minecraft:smoker', 'Native manual smoking; starts empty and unlit'),
        ((1325, 64, -1333), 'farmersdelight:stove', 'Native cooking heat; starts unlit'),
        ((1325, 65, -1333), 'farmersdelight:cooking_pot', 'Native soup/meal preparation'),
        ((1319, 64, -1333), 'minecraft:crafting_table', 'Real wrapping, hooks and tackle crafting'),
        ((1326, 64, -1330), 'minecraft:water_cauldron', 'Contained manual wash-water; no room flooding'),
        ((1321, 65, -1336), 'farmersdelight:cutting_board', 'Actual native one-fish preparation/display inventory')))
    p.scene('Warm fish prep beneath the loft', ['Smoker, actual FD stove/pot, wash-water, cabinet and crafting bench',
        'Low lantern, modeled hood and real solid termination beneath loft; no exterior chimney/roof cut'],
        [(1324, 64, -1331), (1324, 64, -1329)])

    # A small waiting/supper nook faces the shop activity rather than a blank
    # wall. Cabinets/stock, hooks and reading detail make the other end lived in.
    p.table(1320, 64, -1330)
    p.chair(1319, 64, -1330, 'east')
    p.chair(1321, 64, -1330, 'west')
    p.on_floor(1320, 65, -1330, 'handcrafted:wood_cup')
    p.on_floor(1319, 64, -1329, 'minecraft:barrel', facing='south', open=False)
    p.stock((1319, 64, -1329), 'Tackle, pantry & lamp supplies', [('minecraft:fishing_rod', 1),
        ('minecraft:string', 8), ('minecraft:coal', 8), ('minecraft:potato', 6), ('minecraft:bread', 4),
        ('farmersdelight:iron_knife', 1), ('minecraft:flint_and_steel', 1)])
    p.lamp(1319, 65, -1329)
    p.put((1320, 66, -1332), 'handcrafted:salmon_trophy', facing='east', waterlogged=False)
    p.support((1319, 66, -1332))
    p.put((1320, 67, -1332), 'minecraft:tripwire_hook', facing='east', attached=False, powered=False)
    p.support((1319, 67, -1332))
    p.put((1320, 68, -1332), 'minecraft:tripwire_hook', facing='east', attached=False, powered=False)
    p.support((1319, 68, -1332))
    p.stand(1319, 64, -1339)
    p.lamp(1319, 65, -1339)
    p.scene('A bowl while the catch is cleaned', ['Two actual brown chairs, small wood table and cup',
        'Separate tackle/pantry barrel, warm low lamp and two genuine mounted rope/tackle hooks'],
        [(1321, 64, -1329), (1320, 64, -1331)])

    # Loft: asymmetric net-mending desk/bench, short storage bank and charts.
    # It keeps the stair landing and a two-wide cross-room route empty.
    p.table(1320, 71, -1330)
    p.chair(1319, 71, -1330, 'east')
    p.on_floor(1320, 72, -1330, 'handcrafted:stackable_book', books=2, facing='east', seed=4)
    p.on_floor(1319, 71, -1329, 'minecraft:barrel', facing='south', open=False)
    p.stock((1319, 71, -1329), 'Net-mender\'s loft', [('minecraft:string', 12), ('minecraft:shears', 1),
        ('minecraft:paper', 6), ('minecraft:leather', 2)])
    p.lamp(1319, 72, -1329)
    p.on_floor(1326, 71, -1329, 'handcrafted:spruce_bench', facing='west', color='brown', shape='single', waterlogged=False)
    p.on_floor(1326, 71, -1330, 'handcrafted:spruce_side_table', facing='west', color='none', waterlogged=False)
    p.on_floor(1326, 72, -1330, 'handcrafted:terracotta_cup')
    p.support((1319, 74, -1330))
    p.put((1319, 73, -1330), 'minecraft:chain', axis='y', waterlogged=False)
    p.stand(1324, 71, -1329)
    p.lamp(1324, 72, -1329)
    p.scene('Net-mender\'s eaves', ['Supported rear mezzanine, full-width rooted beam, real two-wide seven-step stair and safety rail',
        'Book/mending desk, actual chair, tackle barrel, separate cushioned resting bench, cup and two close warm lamps'],
        [(1321, 71, -1330), (1323, 71, -1330), (1325, 71, -1329)])
    return p


def validate(p):
    # Read all original model cells from the saved checkpoint, rather than
    # restoring stale pre-settle properties or replaying old default BE data.
    complete = {pos: p.snapshot.state(pos) for pos in p.original}
    complete.update(p.blocks)
    material = require_material_rule(complete, 'Exact imported fisherman shop, fully furnished')
    for pos in p.body:
        if key(p.at(pos)) not in VOID:
            raise UserError('Final furniture blocks a central/service walking column: ' + str(pos))
    for door in DOORS:
        if not key(p.snapshot.state(door)).endswith('_door'):
            raise UserError('An original shop entrance is no longer the admitted door')
        p.supports[door] = p.snapshot.state(door)
        p.supports[door[0], door[1] + 1, door[2]] = p.snapshot.state((door[0], door[1] + 1, door[2]))
    for x, feet, z in p.approaches:
        p.support((x, feet - 1, z))
        for y in (feet, feet + 1):
            if key(p.at((x, y, z))) not in VOID:
                raise UserError('A furnished scene lacks a final two-high approach: ' + str((x, y, z)))
    # Each step has exact empty head/body cells above its top, a real adjacent
    # successor and two-wide arrival. This is saved voxel evidence, not a claim
    # about native entity walking or modded furniture collision shapes.
    for index, z in enumerate(range(-1338, -1331)):
        y = 64 + index
        for x in (1325, 1326):
            for dy in (1, 2):
                if key(p.at((x, y + dy, z))) not in VOID:
                    raise UserError('The two-wide loft stair lacks measured headroom')
    for x in (1325, 1326):
        for y in (71, 72):
            if key(p.at((x, y, -1331))) not in VOID:
                raise UserError('Keep the actual loft stair arrival clear')
    # Voxel support paths are a supplemental construction check. Native survival
    # and model-specific support/rotation remain required after real placement.
    solids = {pos for pos, value in p.blocks.items() if key(value) not in VOID}
    roots, queue = set(), deque()
    offsets = ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1))
    for pos in solids:
        for offset in offsets:
            adjacent = tuple(a + b for a, b in zip(pos, offset))
            if adjacent not in p.blocks and key(p.snapshot.state(adjacent)) not in VOID | SOFT | {'minecraft:water', 'minecraft:lava'}:
                roots.add(pos); queue.append(pos); p.supports[adjacent] = p.snapshot.state(adjacent); break
    while queue:
        pos = queue.popleft()
        for offset in offsets:
            neighbor = tuple(a + b for a, b in zip(pos, offset))
            if neighbor in solids and neighbor not in roots:
                roots.add(neighbor); queue.append(neighbor)
    if roots != solids:
        raise UserError('A furnishing cluster has no retained/new structural support path: ' + str(sorted(solids - roots)[:4]))
    if any(pos not in p.blocks or pos in p.snapshot.protected or pos in p.original for pos in p.tags):
        raise UserError('Never apply furnishing tags to existing/default block entities')
    return {'new_target_positions': len(p.blocks), 'new_solid_fittings_and_floors': len(solids),
        'indoor_native_weeds_cleared': len(p.cleared_plants), 'retained_flush_willow_joints': len(p.floor_retained),
        'old_block_entity_tags_replayed': 0, 'new_literal_block_entity_tags': len(p.tags),
        'original_occupied_cells_retained': len(p.original), 'warm_lanterns': len(p.lights),
        'actual_workstation_blocks': len(p.workstations), 'voxel_rooted_new_solids': len(roots),
        'central_two_wide_door_to_door_aisle': 'SAVED SOURCE CLEAR',
        'two_wide_seven_step_loft_access': 'SAVED SOURCE HEADROOM CLEAR; native walking pending',
        'native_survival_light_model_seating_workstation_and_art_acceptance': 'PENDING actual settled game screenshots/use',
        'material': material, 'entities_spawned': 0, 'commands': 0}


def payload(p, blocks, name, checkpoint_sha, *, tags=False, placement=False):
    if not blocks:
        raise UserError('A native shop member cannot be empty')
    palette = sorted(set(blocks.values())); indices = {v: i for i, v in enumerate(palette)}
    row = {'format': 'awft-native-settlement:1', 'name': name, 'created': utcnow(),
        'seed': p.registry['seed'], 'world_path': p.registry['world_path'], 'backup_sha256': checkpoint_sha,
        'bounds': [min(p[0] for p in blocks), min(p[2] for p in blocks), max(p[0] for p in blocks), max(p[2] for p in blocks)],
        'palette': palette, 'blocks': [[*pos, indices[value]] for pos, value in sorted(blocks.items())],
        'block_entities': [{'pos': list(pos), 'nbt': snbt(tag)} for pos, tag in sorted(p.tags.items()) if pos in blocks] if tags else [],
        'commands': [], 'landmarks': [], 'construction_forbidden': not placement}
    if max(row['bounds'][2] - row['bounds'][0], row['bounds'][3] - row['bounds'][1]) > 512:
        raise UserError('Native shop bounds exceed SettlementSupport admission')
    return (json.dumps(row, ensure_ascii=False, separators=(',', ':')) + '\n').encode()


def native_members(p, checkpoint_sha):
    fixtures = {pos: state for pos, state in p.blocks.items() if p.phases[pos] == 2}
    complete = {pos: p.snapshot.state(pos) for pos in p.original}; complete.update(p.blocks)
    result = {
        'initial-ALL-TARGETS-before.json': payload(p, p.before, 'Fresh initial saved before ALL shop targets', checkpoint_sha),
        '01-flush-floor-supported-loft-stair.json': payload(p, p.structural, 'Shop flush floor, supported loft/stair, exact indoor weeds cleared', checkpoint_sha, placement=True),
        '01-flush-floor-supported-loft-stair-before.json': payload(p, {pos: p.before[pos] for pos in p.structural}, 'Exact fresh saved before first shop phase', checkpoint_sha),
        '02-fish-counter-kitchen-cozy-loft.json': payload(p, fixtures, 'Fish counter, real prep and cozy net-mender loft', checkpoint_sha, tags=True, placement=True),
        '02-EXPECTED-after-phase1-before-phase2.json': payload(p, {pos: p.structural.get(pos, p.before[pos]) for pos in fixtures}, 'EXPECTED only after phase1: before shop fixtures', checkpoint_sha),
        'complete-furnished-shop-VERIFY-ONLY.json': payload(p, complete, 'Original imported fisherman exterior plus full new interior — VERIFY ONLY', checkpoint_sha, tags=True),
        'retained-supports-VERIFY-ONLY.json': payload(p, p.supports, 'Existing shop supports/doors — VERIFY ONLY', checkpoint_sha),
    }
    return result


def checked_tag_apis(home):
    """Refuse changed native inventory serializers before authoring any stock."""
    lock = read_json(Path(__file__).resolve().parents[1] / 'catalog/lock.json')
    if lock.get('neoforge') != '21.1.262':
        raise UserError('The native cutting-board inventory schema needs a fresh API review')
    records = []
    for relative, size, sha, member, member_sha in TAG_APIS:
        path = home.parents[2] / relative
        if path.stat().st_size != size or digest(path) != sha:
            raise UserError('The exact reviewed inventory serializer archive differs')
        with zipfile.ZipFile(path) as archive:
            info = archive.getinfo(member)
            if not 0 < info.file_size < 256 * 1024:
                raise UserError('Native inventory serializer class exceeds its finite bound')
            if hashlib.sha256(archive.read(member)).hexdigest() != member_sha:
                raise UserError('The exact reviewed inventory serializer class differs')
        records.append({'archive': path.name, 'archive_sha256': sha, 'class': member,
                        'class_sha256': member_sha, 'evidence': 'Read-only pinned javap load/save field and numeric-tag instructions; native load/readback pending'})
    return records


def prepare(home, checkpoint_id, checkpoint_sha):
    home = Path(home).resolve()
    if not home.is_relative_to(Path(r'D:\A World for Two\staging\world-tests')):
        raise UserError('The imported shop proposal belongs only to the owned artistic stage')
    owner = read_json(home / 'dashboard/artistic-owner.json', {})
    receipt = read_json(home / 'dashboard/settlement/backup-receipt.json', {})
    admit_owner(home, owner, receipt, checkpoint_id, checkpoint_sha)
    tag_apis = checked_tag_apis(home)
    backups = Backups(Layout(home), None, None)
    archive = backups.path(checkpoint_id)
    if digest(archive) != checkpoint_sha:
        raise UserError('The fresh stopped checkpoint bytes differ')
    index, total = backups.verify_archive(archive)
    if total > 512 * 1024**2 or len(index['files']) > 4096:
        raise UserError('Finite saved checkpoint bound exceeded')
    path = home / SOURCE
    if path.stat().st_size > 1024**2 or digest(path) != SOURCE_SHA:
        raise UserError('The exact imported fisherman owner plan differs')
    row = read_json(path); registry = read_json(home / 'dashboard/settlement/registry.json')
    if (row['seed'], row['world_path']) != (registry['seed'], registry['world_path']):
        raise UserError('The imported owner source belongs to another native world')
    original = {pos: value for pos, value in states(row).items() if key(value) not in VOID}
    if len(original) < 1779 or len(original) > 1900:
        raise UserError('The original shop occupied-cell provenance differs')
    snapshot = BackupWorld(home, receipt, registry)
    try:
        p = construct(Interior(registry, snapshot, original)); proof = validate(p)
        # Complete native verification includes the actual current original
        # cells and both new phases. It is NEVER a replay/placement member.
        outputs = native_members(p, checkpoint_sha)
        manifest = {'format': 'awft-imported-fisherman-interior:1',
            'status': 'STAGED SOURCE ONLY; no native actions/visual or functional acceptance',
            'checkpoint_id': checkpoint_id, 'checkpoint_sha256': checkpoint_sha,
            'source_sha256': digest(Path(__file__)), 'original_owner_plan_sha256': SOURCE_SHA,
            'downloaded_original_sha256': ORIGINAL_SHA, 'original_source_author': 'Shabani1; Phantom Node source page (uploader bahs)',
            'downloaded_original_geometry_in_source_repository': False,
            'room': {'inner_bounds_xyz': list(ROOM), 'ground_actor_feet': 64, 'loft_actor_feet': 71,
                'original_door_positions': [list(v) for v in DOORS], 'floor_policy': 'Flush Y63 ordinary soil only; four saved willow joints retained',
                'exterior_roof_windows_original_blocks_and_default_BEs': 'Preserved; existing tags never replayed'},
            'proof': proof, 'scenes': p.scenes, 'lights': p.lights, 'workstations': p.workstations,
            'native_sources': snapshot.sources, 'native_cameras': CAMERAS,
            'native_inventory_serializer_custody': tag_apis,
            'literal_inventory_types': 'Vanilla barrel Slots are TAG_BYTE; pinned FD/NeoForge cutting-board Inventory Size/Slot are TAG_INT; count is modern TAG_INT',
            'sequence': 'Verify retained supports plus initial-ALL-TARGETS-before and phase1-before; place phase1 only, settle and capture stair/room. Verify phase1 and 02-EXPECTED-after-phase1-before-phase2 against the ACTUAL post-phase1 state, then place phase2 once. Settle and native geometry/vanilla Items verification, plus a separate exact saved/native state-and-NBT witness for FD Inventory, notice/name data and remaining state fields; capture both doors/counter/kitchen/loft/night and walk both aisle and stair. Preserve any mismatch; never replay an already placed phase.',
            'existing_native_verifier_limit': 'SettlementSupport.verify checks block IDs/selected structural properties and supplied top-level Items. It does not certify all connection/state fields, nested FD Inventory, sign text or CustomName; those require actual saved/native readback.',
            'verification_only_files': ['complete-furnished-shop-VERIFY-ONLY.json', 'retained-supports-VERIFY-ONLY.json'],
            'files': {name: {'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)} for name, raw in outputs.items()}}
        outputs['manifest.json'] = (json.dumps(manifest, ensure_ascii=False, indent=2) + '\n').encode()
        if sum(map(len, outputs.values())) > MAX_OUTPUT:
            raise UserError('Finite fisherman interior output budget exceeded')
        guard(1024**2, MAX_OUTPUT)
        output = home / 'staging' / ('artistic-fisherman-interior-' + str(time.time_ns()))
        output.mkdir()
        for name, raw in outputs.items():
            with (output / name).open('xb') as stream:
                stream.write(raw)
        return {'directory': str(output), 'manifest_sha256': digest(output / 'manifest.json'), 'proof': proof, 'files': manifest['files']}
    finally:
        snapshot.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--home', type=Path, required=True)
    parser.add_argument('--checkpoint-id', required=True)
    parser.add_argument('--checkpoint-sha', required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.home, args.checkpoint_id, args.checkpoint_sha), indent=2))
