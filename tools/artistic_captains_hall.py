"""One original, fully furnished Captain's Head-inspired north-headland hall.

Pure authored geometry plus explicit saved-checkpoint binding. No native calls,
demolition, runtime edits or borrowed image/schematic assets are performed.
"""
from __future__ import annotations

import argparse
from collections import Counter, deque
import hashlib
import json
import math
from pathlib import Path
import time

from control_room.common import UserError, digest, read_json, utcnow
from tools.artistic_fisherman_interior import Byte, snbt
from tools.artistic_maritime_depth import admit_owner, key
from tools.artistic_materials import require_material_rule
from tools.artistic_spawn_plaza import state
from tools.playtest import guard
from tools.settlement_attractions import BackupWorld


AIR = 'minecraft:air'
VOID = {AIR, 'minecraft:cave_air', 'minecraft:void_air'}
ORIGIN = (1034, 63, -1293)
W3 = 'staging/west-r2-three-frontage-preview-1793168582590227200/three-frontages-PROPOSAL.json'
W3_SHA = '336363fd0adeb0043117ce4e3ed68b32d3e7c2305d895daa68a9a027124ff5c9'
ZIP_MASK = 'staging/zipline-west-v2-source-1793152099836099800/all-v2-RESERVATION-ONLY.json'
ZIP_MASK_SHA = '92ea594836795a61e00f5cc32290d49d1d47b9fd6eb55aeefc99d527acf8854d'
ZIP_MANIFEST_SHA = 'eba3d9d2223f110077926b79736b046713c58531e92d024ad76ed763d742a572'
REFERENCE_SHA = '535bf2c1e639da536d2b16bd52428414f983338f46355fd8e37a55d632dd69da'
MAX_OUTPUT = 16 * 1024**2
SOFT = {'regions_unexplored:grass_sprouts', 'minecraft:short_grass', 'minecraft:tall_grass',
        'supplementaries:barnacles'}
VEC = {'north': (0, -1), 'south': (0, 1), 'west': (-1, 0), 'east': (1, 0)}


def rectangle(x0, z0, x1, z1):
    return {(x, z) for x in range(x0, x1 + 1) for z in range(z0, z1 + 1)}


def boundary(cells):
    return {p for p in cells if any((p[0] + dx, p[1] + dz) not in cells for dx, dz in VEC.values())}


class Hall:
    def __init__(self, registry, origin=ORIGIN):
        self.registry, self.origin = registry, tuple(origin)
        self.blocks, self.tags, self.roles = {}, {}, {}
        self.body, self.routes, self.approaches = set(), [], []
        self.rooms, self.details, self.lights, self.stations = [], [], [], []
        self.footprint = rectangle(0, 0, 16, 12) | rectangle(17, 3, 24, 12) | rectangle(1, 13, 12, 15)
        self.attachment_supports = []

    def put(self, x, y, z, name, *, role='architecture', replace=False, **props):
        p = x, y, z
        if any(type(v) is not int for v in p) or not (-2 <= x <= 26 and -1 <= z <= 17 and 0 <= y <= 19):
            raise UserError('The one authored hall exceeds its small finite reserve')
        value = state(self.registry, name, **props)
        if p in self.body and name not in VOID:
            raise UserError('Preserve the authored hall walking route: ' + str(p))
        previous = self.blocks.get(p, AIR)
        if previous != AIR and previous != value and not replace:
            raise UserError('Distinct hall details collide: ' + str((p, previous, value)))
        self.blocks[p] = value; self.roles[p] = role
        if replace:
            self.tags.pop(p, None)
        if len(self.blocks) > 12000:
            raise UserError('The single hall source exceeded its finite budget')

    def carve(self, x, y, z):
        self.put(x, y, z, AIR, replace=True, role='architectural opening')

    def route(self, label, cells):
        cells = list(cells)
        for x, feet, z in cells:
            for y in (feet, feet + 1):
                self.carve(x, y, z); self.body.add((x, y, z))
        self.routes.append({'name': label, 'actor_feet_local': [list(v) for v in cells]})

    def log(self, x, y, z, axis, *, replace=False, role='rooted heavy timber'):
        material = {'y': 'minecraft:stripped_dark_oak_log', 'x': 'chipped:reinforced_dark_oak_log',
                    'z': 'chipped:edged_stripped_dark_oak_log'}[axis]
        self.put(x, y, z, material, axis=axis, replace=replace, role=role)

    def slab(self, x, y, z, name='dark_oak', *, half='top', replace=False, role='timber reveal'):
        self.put(x, y, z, 'minecraft:' + name + '_slab', type=half, waterlogged=False, replace=replace, role=role)

    def floor(self, cells, y):
        for x, z in sorted(cells):
            # Real longitudinal sleepers divide broad boards into three-wide
            # strips. There is no colored grid or random block replacement.
            if x % 4 == 0:
                self.put(x, y, z, 'chipped:cross_laced_dark_oak_planks', role='longitudinal floor sleeper')
            else:
                self.put(x, y, z, 'minecraft:dark_oak_planks', role='three-wide dark floorboards')

    def wall(self, cells, bottom, top, panel='minecraft:cyan_terracotta'):
        edge = boundary(cells)
        for x, z in sorted(edge):
            along_x = (x - 1, z) in edge and (x + 1, z) in edge
            post = ((x % 4 == 0) if along_x else (z % 4 == 0)) or not (
                ((x - 1, z) in edge and (x + 1, z) in edge) or
                ((x, z - 1) in edge and (x, z + 1) in edge))
            for y in range(bottom, top + 1):
                if post:
                    self.log(x, y, z, 'y')
                else:
                    self.put(x, y, z, panel, role='recessed muted slate plaster bay')

    def ring(self, cells, y):
        edge = boundary(cells)
        for x, z in sorted(edge):
            axis = 'x' if (x - 1, z) in edge or (x + 1, z) in edge else 'z'
            self.log(x, y, z, axis, replace=True, role='continuous structural floor/eaves band')

    def window(self, x, y, z, face, width=3, height=2):
        dx, dz = VEC[face]; tx, tz = (1, 0) if dz else (0, 1)
        for i in range(width):
            for j in range(height):
                self.put(x + tx * i, y + j, z + tz * i, 'mcwwindows:dark_oak_four_window',
                         facing=face, windowstate='locked', replace=True, role='actual broad dark-timber casement')
        for i in range(-1, width + 1):
            self.log(x + tx * i + dx, y + height, z + tz * i + dz, 'x' if tx else 'z', role='projecting rooted window hood')
        for i in (-1, width):
            self.put(x + tx * i + dx, y + height - 1, z + tz * i + dz,
                     'mythrais:curved_corbel_dark_oak', facing=face, shape=0, role='carved window-hood knee')
        self.details.append({'kind': 'deep casement', 'local': [x, y, z], 'width': width, 'height': height, 'outward': face})

    def door(self, x, z, face, *, pair=False):
        # Native cottage doors have real two-part interaction/collision.
        for n in range(2 if pair else 1):
            for y, half in ((1, 'lower'), (2, 'upper')):
                self.put(x + n, y, z, 'mcwdoors:dark_oak_cottage_door', facing=face, half=half,
                         hinge='left' if n == 0 else 'right', open=False, powered=False,
                         replace=True, role='real hinged entrance')

    def lamp(self, x, y, z, face):
        self.put(x, y, z, 'mcwlights:tavern_wall_lantern', facing=face, role='small low warm wall lantern')
        dx, dz = VEC[face]
        self.attachment_supports.append(((x, y, z), (x - dx, y, z - dz)))
        self.lights.append([x, y, z])

    def standing_lamp(self, x, y, z):
        self.put(x, y, z, 'minecraft:lantern', hanging=False, waterlogged=False, role='human-scale warm lantern')
        self.attachment_supports.append(((x, y, z), (x, y - 1, z)))
        self.lights.append([x, y, z])

    def table(self, x, y, z):
        self.put(x, y, z, 'handcrafted:dark_oak_table', color='none', shape='single', waterlogged=False, role='real styled table')

    def chair(self, x, y, z, face, color='brown'):
        self.put(x, y, z, 'handcrafted:dark_oak_chair', facing=face, color=color, waterlogged=False, role='usable upholstered chair')

    def cup(self, x, y, z):
        self.put(x, y, z, 'handcrafted:wood_cup', role='tabletop drink')

    def barrel(self, x, y, z, title, stacks=()):
        self.put(x, y, z, 'minecraft:barrel', facing='south', open=False, role='new merchant/household storage')
        items = []
        for slot, (item, count) in enumerate(stacks):
            if item not in self.registry['items'] or not 1 <= count <= 16:
                raise UserError('Only small real pinned hall supplies are permitted')
            items.append({'Slot': Byte(slot), 'id': item, 'count': count})
        self.tags[x, y, z] = {'CustomName': json.dumps({'text': title}, separators=(',', ':')), 'Items': items}

    def sign(self, x, y, z, face, lines):
        self.put(x, y, z, 'minecraft:dark_oak_wall_sign', facing=face, waterlogged=False, role='hand-lettered nautical trade notice')
        dx, dz = VEC[face]; self.attachment_supports.append(((x, y, z), (x - dx, y, z - dz)))
        self.tags[x, y, z] = {'is_waxed': True, 'front_text': {'messages': [json.dumps({'text': v}, separators=(',', ':')) for v in lines],
            'color': 'white', 'has_glowing_text': False}}

    def room(self, title, point, contents):
        self.rooms.append({'name': title, 'standing_point_local': list(point), 'authored_contents': contents})


def shell(p):
    main = rectangle(0, 0, 16, 12); annex = rectangle(17, 3, 24, 12)
    p.floor(p.footprint, 0)
    for x, z in main:
        for y in range(1, 12):
            p.put(x, y, z, AIR, role='complete measured interior body')
    for x, z in annex:
        for y in range(1, 6):
            p.put(x, y, z, AIR, role='single-storey annex body')
    p.wall(main, 1, 5); p.wall(main, 7, 11)
    p.wall(annex, 1, 5, 'dawnoftimebuilder:plastered_stone')
    # Both floors are individually divided by genuine timber sleepers.
    upper = rectangle(1, 1, 15, 11) - {(x, z) for x in (13, 14) for z in range(5, 11)}
    p.floor(upper, 6)
    p.ring(main, 6); p.ring(main, 11); p.ring(annex, 6)

    # Two wide, accessible native stairs; stringers provide real support.
    for n, z in enumerate(range(10, 4, -1)):
        for x in (13, 14):
            if n:
                p.put(x, n, z, 'chipped:boxed_dark_oak_planks', role='rooted stair carriage')
            p.put(x, 1 + n, z, 'minecraft:dark_oak_stairs', facing='north', half='bottom',
                  shape='straight', waterlogged=False, role='real two-wide interior stair')
    for z in range(5, 11):
        p.put(12, 7, z, 'minecraft:dark_oak_fence', north=z != 5, south=z != 10,
              east=False, west=False, waterlogged=False, role='upper stairwell safety balustrade')

    # The gable is low, not a giant A-frame. Exact Macaw lower/upper-lower
    # pieces form successive halves of a shallow native tiled slope.
    for x in range(-1, 18):
        d = min(x + 1, 17 - x)
        roof_y = 12 + d // 2
        if x == 8:
            for z in (0, 12):
                for y in range(12, roof_y):
                    p.log(x, y, z, 'y')
            for z in range(-1, 14):
                p.put(x, roof_y + 1, z, 'chipped:nailed_dark_oak_log', axis='z', role='heavy projecting continuous ridge')
                p.put(x, roof_y, z, 'mcwroofs:orange_terracotta_top_roof', part='switched_0', role='native tiled ridge join')
            continue
        material = 'mcwroofs:orange_terracotta_upper_lower_roof' if d % 2 == 0 else 'mcwroofs:orange_terracotta_lower_roof'
        face = 'east' if x < 8 else 'west'
        for z in range(-1, 14):
            p.put(x, roof_y, z, material, facing=face, half='bottom', shape='straight', role='shallow baked-clay main roof')
        if 0 <= x <= 16:
            for z in (0, 12):
                for y in range(12, roof_y):
                    if x % 4 == 0:
                        p.log(x, y, z, 'y')
                    else:
                        p.put(x, y, z, 'minecraft:cyan_terracotta', role='framed upper gable infill')
        # A slim timber bargeboard stays immediately beneath the tile surface.
        for z in (-1, 13):
            p.slab(x, roof_y - 1, z, name='spruce', role='rooted slim gable bargeboard')

    # The compact annex is a real four-sided hip. The front/back clay courses
    # use Dawn's modeled tiles; the side facets use Macaw's matching warm roof.
    # These are distinct construction facets, not a colored checkerboard.
    for x in range(17, 26):
        for z in range(2, 14):
            a, b = min(x - 16, 25 - x), min(z - 2, 13 - z)
            d = min(a, b); y = 6 + d
            if a == b:
                p.slab(x, y, z, name='dark_oak', role='expressed hipped-roof corner seam')
            elif a < b:
                p.put(x, y, z, 'mcwroofs:orange_terracotta_roof', facing='east' if x < 21 else 'west',
                      half='bottom', shape='straight', role='hipped annex side tile facet')
            else:
                p.put(x, y, z, 'dawnoftimebuilder:ochre_roof_tiles_stairs', facing='south' if z < 8 else 'north',
                      half='bottom', shape='straight', waterlogged=False, role='warm hipped annex front/back tile facet')
            if d and p.blocks.get((x, y - 1, z), AIR) == AIR:
                p.slab(x, y - 1, z, name='spruce' if b < a else 'dark_oak', half='top',
                       role='real continuous underside hip rafter/purlin')
    # A supported deep porch, intentionally asymmetrical to the lower annex.
    for x in (1, 12):
        for y in range(1, 6):
            p.log(x, y, 15, 'y')
        p.put(x, 5, 14, 'mythrais:curved_corbel_dark_oak', facing='north', shape=0, role='deep porch carved knee')
    for x in range(1, 13):
        p.log(x, 6, 15, 'x', role='supported porch front crossbeam')
        for z in range(13, 17):
            d = 16 - z
            p.put(x, 7 + d // 2, z, 'mcwroofs:bricks_upper_lower_roof' if d % 2 == 0 else 'mcwroofs:bricks_lower_roof',
                  facing='north', half='bottom', shape='straight', role='weathered tiled deep porch lean-to')
    for x in range(5, 12):
        p.put(x, 1, 15, 'minecraft:spruce_fence', north=False, south=False, east=True,
              west=True, waterlogged=False, role='porch rail turns visitors away from retained natural depression')

    # Real openings and their generous structural heads/recesses.
    p.door(6, 12, 'south', pair=True); p.door(23, 12, 'south')
    for x in (16, 17):
        for z in (4, 5):
            for y in (1, 2):
                p.carve(x, y, z)
    for x in (16, 17):
        for z in (4, 5):
            p.log(x, 3, z, 'z', replace=True, role='heavy two-room opening lintel')
    p.window(2, 2, 0, 'north', 3, 2)
    p.window(10, 2, 0, 'north', 3, 2)
    p.window(0, 2, 4, 'west', 3, 2)
    p.window(0, 8, 3, 'west', 3, 2)
    p.window(2, 8, 12, 'south', 3, 2)
    p.window(10, 8, 12, 'south', 3, 2)
    p.window(2, 8, 0, 'north', 3, 2)
    p.window(10, 8, 0, 'north', 3, 2)
    p.window(18, 2, 12, 'south', 4, 3)
    p.window(24, 2, 6, 'east', 3, 2)

    # Walking reservations are carved now, BEFORE detailed furnishing.
    # Door cells are separate interaction boundaries; never erase real doors.
    p.route('ground main two-wide spine', ((x, 1, z) for x in (6, 7) for z in range(1, 12)))
    p.route('ground stair approach', ((x, 1, 11) for x in range(6, 15)))
    p.route('ground cross-room/annex link', ((x, 1, z) for x in range(6, 22) for z in (4, 5)))
    p.route('annex secondary entry', ((23, 1, z) for z in (10, 11, 13)))
    p.route('upper stair arrival', ((x, 7, z) for x in range(6, 15) for z in (3, 4)))
    p.route('upper two-wide gallery', ((x, 7, z) for x in (10, 11) for z in range(4, 12)))
    p.route('porch entry dogleg clear of natural hollow', ((x, 1, z) for x in (6, 7) for z in (13, 14)))
    p.route('porch left exit', ((x, 1, z) for x in (3, 4) for z in (14, 15, 16)))
    p.route('porch transverse connection', ((x, 1, 14) for x in range(3, 8)))
    return p


def furnish(p):
    # Ground bar: service aisle, wood-and-slate counter, genuine pantry/cooking,
    # asymmetric bottle/book display, low lamps and a readable chalk notice.
    for z in (6, 7, 8, 9):
        p.put(4, 1, z, 'handcrafted:dark_oak_counter', facing='east', counter='andesite', type=1, role='deep slate serving counter')
    for z in (6, 8):
        p.barrel(1, 1, z, 'Captain\'s Rest pantry', [('minecraft:bread', 6), ('minecraft:potato', 8)])
        p.put(1, 2, z, 'handcrafted:dark_oak_shelf', facing='east', shape='single', type=3, role='small barback shelf')
        p.put(1, 3, z, 'lfpirates:ship_in_bottle', facing='east', waterlogged=False, role='nautical barback specimen')
    p.put(1, 1, 10, 'minecraft:smoker', facing='east', lit=False, role='real manual supper smoker')
    p.put(2, 1, 10, 'minecraft:crafting_table', role='real prep/repair bench')
    p.put(3, 1, 10, 'handcrafted:dark_oak_counter', facing='north', counter='andesite', type=1, role='real waist-high prep counter')
    p.put(3, 2, 10, 'farmersdelight:cutting_board', facing='east', waterlogged=False, role='real clean food prep board')
    p.standing_lamp(4, 2, 6); p.cup(4, 2, 8)
    p.put(4, 2, 9, 'farmersdelight:roast_chicken_block', facing='east', servings=4, role='real small shared supper')
    p.log(1, 4, 7, 'y'); p.sign(2, 4, 7, 'east', ('THE CAPTAIN\'S REST', 'Hot supper & charts', 'Rooms upstairs', 'Mind the tide'))
    p.lamp(1, 3, 1, 'east')
    p.room('The Captain\'s Rest common bar', (3, 1, 7), ['walk-behind counter', 'pantry and real prep stations', 'ship bottles', 'low lamp', 'readable notice'])

    # Several separate human groups, not an empty oversized function room.
    for x, z, color in ((2, 3, 'brown'), (10, 2, 'gray'), (10, 9, 'brown')):
        p.table(x, 1, z); p.cup(x, 2, z)
        p.chair(x - 1, 1, z, 'east', color)
        p.chair(x + 1, 1, z, 'west', color)
        p.approaches.append((x, 1, z + 1 if z != 3 else z - 1))
    p.put(9, 1, 10, 'handcrafted:dark_oak_bench', facing='north', color='brown', shape='single', waterlogged=False, role='separate crew waiting bench')
    p.put(8, 1, 10, 'handcrafted:dark_oak_side_table', facing='north', color='none', waterlogged=False, role='bench-side lamp stand')
    p.standing_lamp(8, 2, 10)
    p.put(10, 1, 7, 'minecraft:cartography_table', role='genuine shared chart workbench')
    p.put(9, 1, 7, 'handcrafted:dark_oak_chair', facing='east', color='gray', waterlogged=False, role='chart-reader seat')
    p.put(10, 2, 7, 'handcrafted:stackable_book', books=2, facing='west', seed=4, role='tide-table display')
    p.room('The harbor common room', (8, 1, 8), ['three distinct table groups', 'waiting bench', 'actual chart table', 'books and supper'])

    # Lower annex: a cozy framed casement bay and a compact practical scullery.
    p.table(20, 1, 9); p.cup(20, 2, 9)
    p.chair(19, 1, 9, 'east', 'brown'); p.chair(21, 1, 9, 'west', 'brown')
    p.put(18, 1, 10, 'handcrafted:dark_oak_couch', facing='east', color='gray', shape='single', waterlogged=False, role='window-recess couch')
    p.barrel(23, 1, 4, 'Galley & lamplighter stores', [('minecraft:coal', 8), ('minecraft:cod', 6), ('minecraft:string', 8)])
    p.put(23, 1, 5, 'minecraft:water_cauldron', level=2, role='contained scullery water')
    p.put(23, 1, 6, 'farmersdelight:dark_oak_cabinet', facing='west', open=False, role='actual scullery cupboard')
    p.put(23, 1, 7, 'farmersdelight:stove', facing='west', lit=False, role='real manual galley stove')
    p.put(23, 2, 7, 'farmersdelight:cooking_pot', facing='west', support='tray', waterlogged=False, role='real galley cooking pot')
    p.put(18, 1, 6, 'handcrafted:dark_oak_side_table', facing='east', color='none', waterlogged=False, role='window dining lamp stand')
    p.standing_lamp(18, 2, 6)
    p.room('The wide-casement supper bay', (20, 1, 7), ['large real framed window', 'couch and actual dining seats', 'usable scullery', 'low warm lamp'])

    # Upper floor: a shared chart/reading hall, two genuine sleeping berths and
    # sheltered small groups. All rooms are reached by the same real staircase.
    for x in (2, 5):
        for dx, part in ((0, 'foot'), (1, 'head')):
            p.put(x + dx, 7, 1, 'minecraft:blue_bed', facing='east', part=part, occupied=False, role='genuine native upstairs bed')
        p.barrel(x, 7, 2, 'Quiet berth locker', [('minecraft:bread', 3), ('minecraft:paper', 4)])
    for x in range(1, 9):
        p.slab(x, 9, 2, name='spruce', half='top', role='short berth canopy/cornice')
    for x in (1, 8):
        p.put(x, 8, 2, 'mythrais:curved_corbel_dark_oak', facing='north', shape=0, role='berth canopy carved knee')
    p.table(7, 7, 7); p.table(8, 7, 7)
    p.put(7, 8, 7, 'handcrafted:stackable_book', books=3, facing='south', seed=6, role='chart archive logbooks')
    p.cup(8, 8, 7)
    p.chair(6, 7, 7, 'east', 'gray'); p.chair(9, 7, 7, 'west', 'gray')
    p.put(2, 7, 9, 'handcrafted:dark_oak_couch', facing='east', color='brown', shape='single', waterlogged=False, role='upper harbor-view reading couch')
    p.table(4, 7, 9); p.put(4, 8, 9, 'handcrafted:stackable_book', books=2, facing='east', seed=9, role='quiet reading books')
    p.chair(5, 7, 9, 'west', 'brown')
    p.put(14, 7, 2, 'handcrafted:dark_oak_side_table', facing='west', color='none', waterlogged=False, role='upper stair night-lamp stand')
    p.standing_lamp(14, 8, 2)
    p.put(2, 7, 7, 'handcrafted:dark_oak_side_table', facing='east', color='none', waterlogged=False, role='reading-lamp stand')
    p.standing_lamp(2, 8, 7)
    p.table(3, 7, 5); p.cup(3, 8, 5)
    p.put(1, 7, 5, 'handcrafted:dark_oak_bench', facing='east', color='brown', shape='single', waterlogged=False, role='separate upper conversation bay')
    p.chair(4, 7, 5, 'west', 'brown')
    p.put(1, 9, 6, 'handcrafted:dark_oak_shelf', facing='east', shape='single', type=3, role='recessed upper room book shelf')
    p.put(1, 10, 6, 'handcrafted:stackable_book', books=3, facing='east', seed=12, role='upper room sea journals')
    p.put(14, 7, 11, 'handcrafted:dark_oak_bench', facing='north', color='gray', shape='single', waterlogged=False, role='sheltered upper south-window bench')
    p.put(13, 7, 11, 'handcrafted:dark_oak_side_table', facing='north', color='none', waterlogged=False, role='upper window-bench side table')
    p.cup(13, 8, 11)
    for y, part in ((7, 'lower'), (8, 'middle'), (9, 'upper')):
        fields = {'colour': 0, 'facing': 'south'}
        if part != 'middle':
            fields['mirrored'] = False
        p.put(4, y, 1, 'mythrais:decorated_column_' + part + '_small_dark_oak', **fields,
              role='carved berth privacy-screen standard')
    for z in (2, 3):
        for y in (7, 8):
            p.put(4, y, z, 'minecraft:dark_oak_trapdoor', facing='east', half='bottom', open=True,
                  powered=False, waterlogged=False, role='thin two-berth privacy screen')
    p.room('Chart loft and quiet berths', (11, 7, 7), ['two real blue beds and private lockers', 'shared chart table', 'separate reading couch', 'actual broad upper casements', 'two warm night lamps'])

    # Shallow coffers and real supported interior brackets throughout the hall.
    for z in (3, 7, 11):
        for x in range(1, 16):
            if (x, 5, z) not in p.body and not (x in (13, 14) and 5 <= z <= 10):
                p.log(x, 5, z, 'x', role='shallow exposed ceiling joist')
        for x, face in ((1, 'east'), (15, 'west')):
            if (x, z) == (1, 7):
                continue  # The actual full notice standard supports this joist.
            p.put(x, 4, z, 'mythrais:curved_corbel_dark_oak', facing=face, shape=0, role='interior joist support bracket')
    for z in (1, 4, 11):
        p.log(15, 3, z, 'y', role='short interior wall lamp standard')
        p.lamp(14, 3, z, 'west')
    return p


def exterior(p):
    # Corner quoin shoes and projecting collars, rooted against real wall posts.
    for x, z in ((0, 0), (16, 0), (0, 12), (24, 3), (24, 12)):
        out_x = -1 if x == 0 else 1
        for y in (1, 3, 7, 10):
            if x > 16 and y > 5:
                continue
            p.put(x + out_x, y, z, 'mythrais:corbel_scroll_centre_stone',
                  facing='west' if out_x < 0 else 'east', shape=0, role='projecting worn quoin/corbel')
    # Real porch lamps hang safely above walking heads from real supported beams.
    for x, face in ((2, 'east'), (11, 'west')):
        p.log(1 if x == 2 else 12, 3, 15, 'y', replace=True)
        p.lamp(x, 3, 15, face)
    p.log(-1, 5, 10, 'x', role='nautical sign bracket')
    p.log(-2, 5, 10, 'x', role='nautical sign cantilever')
    p.put(-2, 4, 10, 'minecraft:chain', axis='y', waterlogged=False, role='rooted sign suspension')
    p.put(-2, 3, 10, 'minecraft:dark_oak_hanging_sign', rotation=0, attached=False, waterlogged=False, role='actual suspended harbor-hall sign')
    p.tags[-2, 3, 10] = {'is_waxed': True, 'front_text': {'messages': [json.dumps({'text': v}, separators=(',', ':')) for v in (
        'THE CAPTAIN\'S', 'REST', 'Supper & Charts', 'Quiet rooms')], 'color': 'white', 'has_glowing_text': False}}
    for x in (7, 8, 9):
        for y in (11, 12, 13):
            p.put(x, y, 13, 'chipped:crossed_dark_oak_planks', role='projecting carved nautical crest backboard')
    for x in range(6, 11):
        p.log(x, 14, 13, 'x', replace=True, role='supported broad crest hood replaces only its own slim bargeboard ends')
    for x, face in ((6, 'east'), (10, 'west')):
        p.put(x, 13, 13, 'mythrais:curved_corbel_dark_oak', facing=face, shape=0, role='carved crest-hood corner')
    p.put(8, 13, 14, 'minecraft:cyan_wall_banner', facing='south', role='native nautical crest on projecting carved backboard')
    p.tags[8, 13, 14] = {'patterns': [{'pattern': 'minecraft:skull', 'color': 'yellow'},
                                  {'pattern': 'minecraft:border', 'color': 'brown'}]}
    # Actual small rooted planters and face-supported ivy; no floating leaf cubes
    # or growth along an entrance/window. These remain within this one facade.
    for x, z in ((1, 14), (12, 14), (25, 10)):
        p.put(x, 1, z, 'minecraft:potted_flowering_azalea_bush', role='genuine rooted native potted flowering shrub')
    # Two short planted wall niches flank, never cover, the actual broad casement.
    for x in (17, 22):
        p.put(x, 2, 13, 'minecraft:oak_trapdoor', facing='south', half='bottom', open=True,
              powered=False, waterlogged=False, role='projecting planter timber front')
        p.put(x, 1, 13, 'minecraft:moss_block', role='rooted narrow window-garden bed')
        p.put(x, 3, 13, 'minecraft:vine', north=True, south=False, east=False, west=False, up=False,
              role='short rooted facade climber beside glazing')
    p.details.append({'kind': 'reference translation', 'sources': 'Owner-supplied Jamie Read/Rare Captain\'s Head reference; original Minecraft composition, no copied bitmap',
        'features': ['muted slate infill', 'heavy dark timber', 'projecting quoin/corbels', 'shallow gable + lower tiled hip',
                     'deep supported porch', 'broad casement', 'small nautical crest/sign', 'low lamps and restrained planting']})
    return p


def build(registry, origin=ORIGIN):
    return exterior(furnish(shell(Hall(registry, origin))))


def validate(p):
    proof = require_material_rule(p.blocks, 'The Captain\'s Rest — complete unique furnished hall')
    for pos in p.body:
        if key(p.blocks.get(pos, AIR)) not in VOID:
            raise UserError('A later facade/furnishing blocks an authored walking route')
    for detail, support in p.attachment_supports:
        if key(p.blocks.get(support, AIR)) in VOID:
            raise UserError('A small hall fitting has no authored support: ' + str((detail, support)))
    for x, y, z in p.approaches:
        for dy in (0, 1):
            if key(p.blocks.get((x, y + dy, z), AIR)) not in VOID:
                raise UserError('A table group has no clear actual approach')
    for n, z in enumerate(range(10, 4, -1)):
        for x in (13, 14):
            for y in (2 + n, 3 + n):
                if key(p.blocks.get((x, y, z), AIR)) not in VOID:
                    raise UserError('The real two-wide upper stair has blocked headroom')
    # Every authored solid must have a face-connected path to its actual
    # ground-founded footprint. This is geometry, not native survival approval.
    solid = {q for q, value in p.blocks.items() if key(value) not in VOID}
    rooted = {(x, 0, z) for x, z in p.footprint}; pending = deque(rooted)
    steps = ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1))
    while pending:
        pos = pending.popleft()
        for offset in steps:
            q = tuple(a + b for a, b in zip(pos, offset))
            if q in solid and q not in rooted:
                rooted.add(q); pending.append(q)
    # Hanging cloth and shallow native modeled projections can be connected by
    # an adjacent support cell; no disconnected solid is silently exempted.
    if solid - rooted:
        raise UserError('A hall detail is disconnected from its real structure: ' + str(sorted(solid - rooted)[:6]))
    return {'material': proof, 'targets': len(p.blocks), 'solid_positions': len(solid),
        'rooted_solid_positions': len(rooted), 'rooms': len(p.rooms), 'warm_lights': len(p.lights),
        'literal_new_stock_and_notice_tags': len(p.tags), 'original_pixel_or_schematic_assets_copied': False,
        'native_art_models_shapes_survival_seating_walk_and_workstation_checks': 'PENDING actual staged Minecraft views/use'}


def native_payload(registry, blocks, sha, name, *, tags=None, placement=False):
    palette = sorted(set(blocks.values())); lookup = {s: i for i, s in enumerate(palette)}
    result = {'format': 'awft-native-settlement:1', 'name': name, 'created': utcnow(),
        'seed': registry['seed'], 'world_path': registry['world_path'], 'backup_sha256': sha,
        'bounds': [min(q[0] for q in blocks), min(q[2] for q in blocks), max(q[0] for q in blocks), max(q[2] for q in blocks)],
        'palette': palette, 'blocks': [[*q, lookup[v]] for q, v in sorted(blocks.items())],
        'block_entities': [{'pos': list(q), 'nbt': snbt(tag)} for q, tag in sorted((tags or {}).items())],
        'commands': [], 'landmarks': [], 'construction_forbidden': not placement}
    return (json.dumps(result, separators=(',', ':'), ensure_ascii=False) + '\n').encode()


def admit_saved_target(pos, old, *, protected, foundation, below=None):
    """A proposed AIR opening never grants permission to remove an old object."""
    if protected:
        raise UserError('Preserve every saved native/player block entity')
    if foundation:
        if key(old) != 'minecraft:gravel':
            raise UserError('A structural hall floor lacks actual dry measured gravel: ' + str(pos))
        if below is None or key(below) in VOID | {'minecraft:water', 'minecraft:lava'}:
            raise UserError('Do not float a new hall floor above a hidden wet/air cavity')
    elif key(old) not in VOID | SOFT:
        raise UserError('Preserve native authored/unknown/player construction: ' + str(pos) + ' ' + key(old))


def prepare(home, checkpoint_id, checkpoint_sha):
    home = Path(home).resolve()
    if not home.is_relative_to(Path(r'D:\A World for Two\staging\world-tests')):
        raise UserError('The hall belongs only to an explicitly owned artistic staging world')
    owner = read_json(home / 'dashboard/artistic-owner.json', {})
    receipt = read_json(home / 'dashboard/settlement/backup-receipt.json', {})
    admit_owner(home, owner, receipt, checkpoint_id, checkpoint_sha)
    registry = read_json(home / 'dashboard/settlement/registry.json')
    original = home / W3
    if original.stat().st_size > 4 * 1024**2 or digest(original) != W3_SHA:
        raise UserError('The accepted western three-frontage owner source differs')
    w3 = read_json(original)
    if (w3['seed'], w3['world_path']) != (registry['seed'], registry['world_path']):
        raise UserError('The accepted neighboring owner belongs to another world')
    protected = {tuple(row[:3]) for row in w3['blocks']}
    p = build(registry); proof = validate(p)
    world = lambda q: tuple(q[i] + p.origin[i] for i in range(3))
    after = {world(q): value for q, value in p.blocks.items()}
    tags = {world(q): tag for q, tag in p.tags.items()}
    if protected.intersection(after):
        raise UserError('The hall may not overwrite accepted W3 solids/AIR/routes')
    zip_path = home / ZIP_MASK
    zip_manifest = zip_path.parent / 'manifest.json'
    if zip_manifest.stat().st_size > 256 * 1024 or digest(zip_manifest) != ZIP_MANIFEST_SHA:
        raise UserError('The original approved v2 physical-source manifest differs')
    zip_proof = read_json(zip_manifest)
    if zip_proof['files'][zip_path.name] != {'sha256': ZIP_MASK_SHA, 'bytes': 178399}:
        raise UserError('The v2 body/physical mask is not the exact manifest member')
    if zip_path.stat().st_size > 8 * 1024**2 or digest(zip_path) != ZIP_MASK_SHA:
        raise UserError('The exact v2 flight/physical/station reservation differs')
    zip_row = read_json(zip_path)
    zip_columns = {(row[0], row[2]) for row in zip_row['blocks']}
    hall_columns = {(x, z) for x, y, z in after}
    if any((x + dx, z + dz) in zip_columns for x, z in hall_columns for dx in range(-5, 6) for dz in range(-5, 6)):
        raise UserError('The new hall must stay outside the v2 flight/structure reservation and five-metre skirt')
    snapshot = BackupWorld(home, receipt, registry)
    try:
        before, supports = {}, {}
        for q, value in after.items():
            old = snapshot.state(q)
            foundation = q[1] == p.origin[1] and (q[0] - p.origin[0], q[2] - p.origin[2]) in p.footprint
            below = q[0], q[1] - 1, q[2]
            native = snapshot.state(below) if foundation else None
            admit_saved_target(q, old, protected=q in snapshot.protected, foundation=foundation, below=native)
            if foundation:
                supports[below] = native
            before[q] = old
        for route in p.routes:
            for x, y, z in route['actor_feet_local']:
                below = world((x, y - 1, z))
                if below not in after:
                    native = snapshot.state(below)
                    if key(native) != 'minecraft:gravel':
                        raise UserError('An exterior hall walking route lacks measured dry floor')
                    supports[below] = native
        for local, value in p.blocks.items():
            if local[1] == 1 and key(value) not in VOID and (local[0], 0, local[2]) not in p.blocks:
                below = world((local[0], 0, local[2]))
                if key(snapshot.state(below)) != 'minecraft:gravel':
                    raise UserError('An exterior planter needs actual dry retained ground')
                supports[below] = snapshot.state(below)
        # Ground thresholds are literal dry saved surfaces; the porch bends
        # around the retained hollow rather than bridging or flattening it.
        for x, z in ((1037, -1276), (1038, -1276), (1057, -1280)):
            floor = x, 63, z
            if key(snapshot.state(floor)) != 'minecraft:gravel':
                raise UserError('The proposed hall threshold lacks actual dry ground')
            supports[floor] = snapshot.state(floor)
            for y in (64, 65):
                body = x, y, z; old = snapshot.state(body)
                if key(old) not in VOID | SOFT:
                    raise UserError('A fresh saved approach is obstructed')
                supports[body] = old
        masks = dict(after)
        for route in p.routes:
            for x, y, z in route['actor_feet_local']:
                for dy in (0, 1):
                    masks[world((x, y + dy, z))] = AIR
        outputs = {
            'captains-rest-before-VERIFY-ONLY.json': native_payload(registry, before, checkpoint_sha, 'Exact saved headland hall preimage — VERIFY ONLY'),
            'captains-rest-PROPOSAL.json': native_payload(registry, after, checkpoint_sha, 'The Captain\'s Rest — one original reference-led furnished hall', tags=tags, placement=True),
            'captains-rest-complete-VERIFY-ONLY.json': native_payload(registry, after, checkpoint_sha, 'The Captain\'s Rest full geometry/new tags — VERIFY ONLY', tags=tags),
            'dry-ground-supports-VERIFY-ONLY.json': native_payload(registry, supports, checkpoint_sha, 'Actual retained dry floor supports and approach — VERIFY ONLY'),
            'future-solid-AIR-route-reservation-ONLY.json': native_payload(registry, {q: AIR for q in masks}, checkpoint_sha, 'FUTURE reservation only; no observed AIR or planting authority'),
        }
        reservation_name = 'future-solid-AIR-route-reservation-ONLY.json'
        reservation = json.loads(outputs[reservation_name])
        reservation.update(reservation_only=True, not_an_observed_AIR_plan=True)
        outputs[reservation_name] = (json.dumps(reservation, separators=(',', ':')) + '\n').encode()
        cameras = [
            {'name': 'hall-reference-front-wide', 'feet': [1046.5, 64, -1253.5], 'look_at': [1044, 71, -1281]},
            {'name': 'hall-reference-front-close', 'feet': [1052.5, 64, -1274.5], 'look_at': [1044, 70, -1281]},
            {'name': 'hall-west-porch', 'feet': [1032.5, 64, -1275.5], 'look_at': [1040, 68, -1281]},
            {'name': 'hall-ground-common', 'feet': [1040.5, 64, -1283.5], 'look_at': [1038, 66, -1287]},
            {'name': 'hall-casement-supper', 'feet': [1054.5, 64, -1285.5], 'look_at': [1054, 66, -1281]},
            {'name': 'hall-chart-loft', 'feet': [1045.5, 70, -1285.5], 'look_at': [1039, 71, -1287]},
        ]
        for camera in cameras:
            x, feet, z = (math.floor(v) for v in camera['feet'])
            cells = [(x, feet - 1, z), (x, feet, z), (x, feet + 1, z)]
            values = [after.get(q, snapshot.state(q)) for q in cells]
            if key(values[0]) in VOID | {'minecraft:water', 'minecraft:lava'} or any(key(v) not in VOID for v in values[1:]):
                raise UserError('A proposed actor camera lacks measured floor/two-high body clearance: ' + camera['name'])
            camera['source_floor_and_body'] = [{'pos': list(q), 'state': value,
                'role': 'expected new geometry' if q in after else 'current saved state'} for q, value in zip(cells, values)]
            camera['native_pose_collision_and_view_occlusion'] = 'PENDING; saved body evidence is not native camera acceptance'
        record = {'format': 'awft-captains-rest-hall:1', 'status': 'SOURCE ONLY; native visual/use approval pending',
            'checkpoint_id': checkpoint_id, 'checkpoint_sha256': checkpoint_sha, 'source_sha256': digest(Path(__file__)),
            'owner_reference_sha256': REFERENCE_SHA, 'reference_bitmap_copied_or_published': False,
            'accepted_W3_sha256': W3_SHA, 'proof': proof, 'origin': list(p.origin),
            'v2_flight_and_physical_mask_sha256': ZIP_MASK_SHA, 'v2_complete_column_mask_plus_five_metres': 'NO INTERSECTION',
            'rooms': p.rooms, 'details': p.details, 'walking_routes': p.routes, 'native_cameras': cameras,
            'authored_role_counts': dict(Counter(p.roles.values())),
            'native_fitting_support_pairs': [[list(world(a)), list(world(b))] for a, b in p.attachment_supports],
            'private_saved_sources': snapshot.sources,
            'preservation': 'No demolition; no water/void foundations; no old/default BE tags; no original art image copies. The native hollow and all accepted neighbors remain.',
            'native_gates': 'Fresh entity occupancy, before/support checks, placement once, normal settled joins, actual full/NBT readback and real frame/walking/use review. Existing structural verifier alone is not complete state/tag proof.',
            'files': {name: {'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)} for name, raw in outputs.items()}}
        outputs['manifest.json'] = (json.dumps(record, ensure_ascii=False, indent=2) + '\n').encode()
        if sum(map(len, outputs.values())) > MAX_OUTPUT:
            raise UserError('The single hall output exceeds its finite budget')
        guard(1024**2, MAX_OUTPUT)
        output = home / 'staging' / ('artistic-captains-rest-' + str(time.time_ns()))
        output.mkdir()
        for name, raw in outputs.items():
            with (output / name).open('xb') as stream:
                stream.write(raw)
        return {'directory': str(output), 'manifest_sha256': digest(output / 'manifest.json'),
                'proof': {k: v for k, v in proof.items() if k != 'material'}, 'files': record['files']}
    finally:
        snapshot.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--home', type=Path, required=True)
    parser.add_argument('--checkpoint-id', required=True)
    parser.add_argument('--checkpoint-sha', required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.home, args.checkpoint_id, args.checkpoint_sha), indent=2))
