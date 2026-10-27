"""One authored waterfront street for private, native visual review.

This module does not import the rejected settlement builders. Its ten individual
layer plans, street bends, roof sections and court are one composition, not a
random-house factory. A native plan is not evidence of beauty or a walking test.
There are no API calls, world-file edits, entity spawns or commissioned machines.
"""
from __future__ import annotations

import argparse
from collections import deque
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
import subprocess

from control_room.common import UserError, digest, utcnow
from tools.artistic_materials import require_material_rule


MIB = 1024**2
MAX_BLOCKS = 120_000
MAX_BUNDLE = 16*MIB
GUARD = Path(r'C:\Users\kkids\AppData\Local\AeroStorageWatch\ReserveGuard.ps1')
SIZE = (60, 44)
STREET = ((0, 22), (10, 22), (18, 20), (25, 18), (32, 19), (39, 21), (47, 23), (59, 24))


def rectangle(x1, z1, x2, z2):
    return {(x, z) for x in range(x1, x2+1) for z in range(z1, z2+1)}


def layer(*rects, remove=()):
    return set().union(*(rectangle(*rect) for rect in rects))-set(remove)


def edge(cells):
    return {p for p in cells if any((p[0]+dx, p[1]+dz) not in cells for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)))}


def grade(x):
    return 1 if x >= 45 else 0


def street_z(x):
    for (ax, az), (bx, bz) in zip(STREET, STREET[1:]):
        if ax <= x <= bx:
            return round(az+(bz-az)*(x-ax)/(bx-ax))
    raise UserError('Street sample lies outside the authored composition')


@dataclass(frozen=True)
class Roof:
    bounds: tuple[int, int, int, int]
    axis: str
    profile: tuple[int, ...]
    stairs: str
    hip: bool = False
    offset: int = 0


@dataclass
class Building:
    ident: str
    name: str
    purpose: str
    levels: list[set]
    base: int
    plaster: tuple[str, ...]
    timber: str
    front: str
    door_x: int
    windows: tuple[tuple[int, ...], ...]
    roofs: tuple[Roof, ...]
    program: tuple[str, ...]


def designs():
    """Authored outlines in local metres; each upper level is deliberate."""
    return [
        Building('chandler', 'The Copper Lantern', 'Chandler and rope store',
            [layer((2, 8, 9, 19), remove=((2, 19), (2, 18), (3, 19))),
             layer((2, 8, 9, 20)), layer((2, 8, 9, 20), (4, 21, 7, 21))], 0,
            ('minecraft:bricks', 'minecraft:calcite', 'minecraft:calcite'), 'minecraft:stripped_dark_oak_log',
            'south', 6, ((4, 8), (4, 7), (4, 7)),
            (Roof((1, 14, 10, 22), 'z', (0, 1, 2, 3, 4, 4, 3, 2, 1, 0), 'minecraft:dark_oak_stairs'),
             Roof((1, 7, 9, 14), 'x', (0, 1, 2, 3, 3, 2, 1, 0), 'minecraft:dark_oak_stairs', offset=-1)),
            ('Rope and lamp counter', 'Chandler family kitchen', 'Gabled bedroom and sea chest')),
        Building('sailmaker', 'Seven Stitches', 'Sailmaker with tall crew lodgings',
            [layer((11, 6, 18, 16), (17, 15, 19, 17)), layer((11, 6, 18, 17)),
             layer((11, 6, 18, 17)), layer((12, 6, 18, 17))], 0,
            ('minecraft:stone_bricks', 'minecraft:white_terracotta', 'minecraft:white_terracotta', 'minecraft:calcite'),
            'minecraft:stripped_spruce_log', 'south', 14, ((12, 17), (13, 16), (13, 16), (14, 17)),
            (Roof((10, 10, 19, 18), 'z', (0, 2, 3, 4, 4, 4, 4, 3, 2, 0), 'minecraft:deepslate_tile_stairs'),
             Roof((11, 5, 19, 11), 'x', (0, 1, 2, 3, 2, 1, 0), 'minecraft:deepslate_tile_stairs', offset=-1)),
            ('Long cutting bench and canvas bales', 'Sail loft and drying shelves', 'Two crew bunks', 'Upper mariner bedroom')),
        Building('inn', "The Wren's Wake", 'L-plan corner tavern and small inn',
            [layer((21, 7, 28, 15), (27, 7, 32, 11), remove=((21, 15),)),
             layer((21, 7, 28, 16), (27, 7, 32, 12)),
             layer((21, 7, 28, 16), (27, 7, 31, 12))], 0,
            ('minecraft:stone_bricks', 'minecraft:yellow_terracotta', 'minecraft:white_terracotta'),
            'minecraft:stripped_dark_oak_log', 'south', 25, ((23, 27), (23, 26), (23, 26)),
            (Roof((20, 9, 29, 17), 'z', (0, 1, 2, 3, 4, 4, 3, 2, 1, 0), 'minecraft:brick_stairs'),
             Roof((20, 6, 29, 10), 'z', (0, 1, 2, 3, 4, 4, 3, 2, 1, 0), 'minecraft:brick_stairs', offset=-1),
             Roof((27, 6, 33, 13), 'x', (0, 1, 2, 3, 3, 2, 1, 0), 'minecraft:brick_stairs', True)),
            ('Public bar and hearth-side tables', 'Small dining salon and balcony', 'Two guest rooms')),
        Building('fishmonger', 'Tide & Scale', 'Fishmonger beneath an asymmetric saltbox roof',
            [layer((35, 11, 42, 18), remove=((42, 18), (42, 17))),
             layer((35, 11, 42, 19), remove=((42, 19),))], 0,
            ('minecraft:bricks', 'minecraft:cyan_terracotta'), 'minecraft:stripped_oak_log',
            'south', 38, ((36, 40), (36, 40)),
            (Roof((34, 13, 43, 20), 'z', (0, 1, 2, 3, 4, 3, 3, 2, 1, 0), 'minecraft:spruce_stairs'),
             Roof((35, 10, 43, 14), 'x', (0, 1, 2, 1, 0), 'minecraft:spruce_stairs', offset=-1)),
            ('Fish counter and cutting station', 'Fisher family kitchen and beds')),
        Building('harbormaster', 'The Sounding House', 'Stone harbor office with a stepped corner bay',
            [layer((46, 11, 53, 20), (45, 14, 45, 18)),
             layer((46, 11, 53, 21), (45, 14, 45, 18)),
             layer((46, 12, 53, 21), (45, 15, 45, 18))], 1,
            ('minecraft:stone_bricks', 'minecraft:light_gray_terracotta', 'minecraft:calcite'),
            'minecraft:stripped_dark_oak_log', 'south', 49, ((47, 51), (47, 51), (47, 51)),
            (Roof((44, 14, 54, 22), 'z', (0, 1, 2, 3, 4, 4, 4, 3, 2, 1, 0), 'minecraft:deepslate_brick_stairs'),
             Roof((45, 10, 54, 15), 'z', (0, 1, 2, 3, 4, 4, 3, 2, 1, 0), 'minecraft:deepslate_brick_stairs', offset=-1)),
            ('Charts, cargo ledger and real cartography table', 'Harbor clerk living room', 'Watchkeeper bedroom')),
        Building('bookbinder', 'Ink & Bramble', 'Cropped-corner bookshop with a jettied reading room',
            [layer((3, 25, 10, 35), remove=((3, 25), (3, 26), (4, 25))),
             layer((3, 24, 10, 35), (5, 23, 8, 23))], 1,
            ('minecraft:bricks', 'minecraft:calcite'), 'minecraft:stripped_spruce_log',
            'north', 7, ((5, 9), (5, 8)),
            (Roof((2, 28, 11, 36), 'z', (0, 1, 2, 3, 4, 4, 3, 2, 1, 0), 'minecraft:dark_oak_stairs'),
             Roof((3, 22, 11, 29), 'x', (0, 1, 2, 3, 3, 2, 1, 0), 'minecraft:dark_oak_stairs', offset=-1)),
            ('Book binding counter and paper press table', 'Window reading room and private bed')),
        Building('apothecary', 'The Glass Rosemary', 'Green-shuttered herbal shop with a side stair bay',
            [layer((13, 24, 20, 34), (12, 27, 12, 31)),
             layer((13, 23, 20, 34), (12, 27, 12, 31)),
             layer((13, 23, 20, 34), (14, 22, 18, 22))], 0,
            ('minecraft:stone_bricks', 'minecraft:green_terracotta', 'minecraft:white_terracotta'),
            'minecraft:stripped_dark_oak_log', 'north', 16, ((14, 18), (14, 18), (14, 18)),
            (Roof((11, 21, 21, 29), 'z', (0, 1, 2, 3, 4, 5, 4, 3, 2, 1, 0), 'minecraft:brick_stairs'),
             Roof((12, 28, 20, 35), 'x', (0, 1, 2, 3, 3, 2, 1, 0), 'minecraft:brick_stairs', offset=-1)),
            ('Herbal worktop, water cauldron and brewing stand', 'Herbalist kitchen', 'Quiet bedroom above the lane')),
        Building('archhouse', 'Needle Court House', 'Three-storey house over a real courtyard passage',
            [layer((24, 24, 32, 32), (24, 31, 27, 37)),
             layer((24, 23, 32, 32), (24, 31, 27, 37)),
             layer((24, 23, 32, 32), (24, 31, 27, 36))], 0,
            ('minecraft:stone_bricks', 'minecraft:calcite', 'minecraft:light_gray_terracotta'),
            'minecraft:stripped_spruce_log', 'north', 25, ((25, 31), (25, 31), (25, 31)),
            (Roof((23, 22, 33, 30), 'z', (0, 1, 2, 3, 4, 5, 4, 3, 2, 1, 0), 'minecraft:spruce_stairs'),
             Roof((24, 29, 33, 33), 'z', (0, 1, 2, 3, 4, 4, 3, 2, 1, 0), 'minecraft:spruce_stairs', offset=-1),
             Roof((23, 31, 28, 38), 'z', (0, 1, 2, 2, 1, 0), 'minecraft:spruce_stairs', offset=-2)),
            ('Covered alley and cooper repair bench', 'Courtyard-facing family room', 'Sewing room and bedroom')),
        Building('lodging', 'The Blue Thread', 'Narrow sailors house with a deep balcony',
            [layer((37, 26, 44, 37), (39, 25, 42, 25)),
             layer((37, 25, 44, 37), (39, 24, 42, 24))], 0,
            ('minecraft:stone_bricks', 'minecraft:cyan_terracotta'), 'minecraft:stripped_oak_log',
            'north', 40, ((38, 42), (38, 42)),
            (Roof((36, 23, 45, 31), 'z', (0, 1, 2, 3, 3, 3, 3, 2, 1, 0), 'minecraft:dark_oak_stairs'),
             Roof((37, 30, 45, 38), 'x', (0, 1, 2, 3, 4, 3, 2, 1, 0), 'minecraft:dark_oak_stairs', offset=-1)),
            ('Sailors common kitchen and sea chests', 'Two bunks and street window seat')),
        Building('keeper', 'Rose Compass Studio', 'Tall narrow home with a quay-view painter studio',
            [layer((48, 27, 55, 38), remove=((55, 27), (55, 28))),
             layer((47, 26, 55, 38), remove=((55, 26),)),
             layer((48, 26, 55, 38)), layer((49, 27, 55, 37))], 1,
            ('minecraft:bricks', 'minecraft:white_terracotta', 'minecraft:calcite', 'minecraft:light_gray_terracotta'),
            'minecraft:stripped_spruce_log', 'north', 51, ((49, 53), (49, 53), (49, 53), (50, 53)),
            (Roof((47, 25, 56, 33), 'z', (0, 1, 2, 3, 4, 4, 3, 2, 1, 0), 'minecraft:deepslate_tile_stairs'),
             Roof((48, 32, 56, 39), 'x', (0, 1, 2, 3, 3, 2, 1, 0), 'minecraft:deepslate_tile_stairs', offset=-1)),
            ('Painter studio and supplies', 'Small sitting room', 'Family kitchen', 'Upper couple bedroom')),
    ]


class StreetPlan:
    def __init__(self, registry, origin=(0, 65, 0)):
        self.registry, self.origin = registry, tuple(origin)
        self.blocks, self.tags, self.priority, self.cache = {}, {}, {}, {}
        self.owners = {}
        self.routes, self.lots, self.rooms, self.captures = [], [], [], []
        self.zone = 'Street and waterfront'
        self.uses = {}
        self.navigation = set()

    def state(self, key, **properties):
        token = key, tuple(sorted((name, str(value).lower()) for name, value in properties.items()))
        if token in self.cache:
            return self.cache[token]
        actual = self.registry['blocks'].get(key)
        if actual is None:
            raise UserError('Unregistered prototype block: '+key)
        for name, value in token[1]:
            if name not in actual or value not in {str(v).lower() for v in actual[name]}:
                raise UserError('Invalid native property '+key+' '+name+'='+value)
        state = key+('['+','.join(name+'='+value for name, value in token[1])+']' if token[1] else '')
        self.cache[token] = state
        return state

    def put(self, x, y, z, key, *, priority=50, **properties):
        if not (-2 <= x <= 61 and -3 <= z <= 44 and -5 <= y <= 29):
            raise UserError('Authored geometry escaped its small prototype envelope')
        if not -64 <= self.origin[1]+y < 320:
            raise UserError('Prototype escaped the existing world height')
        pos = x, y, z
        if priority < self.priority.get(pos, -1):
            return
        self.blocks[pos] = self.state(key, **properties)
        self.priority[pos] = priority
        self.owners[pos] = self.zone
        self.tags.pop(pos, None)
        if key != 'minecraft:air':
            self.uses.setdefault(key.split(':')[0], set()).add(self.zone)
        if len(self.blocks) > MAX_BLOCKS:
            raise UserError('Prototype exceeded its finite placement bound')

    def line(self, start, end, key, *, priority=50, **properties):
        delta = tuple(b-a for a, b in zip(start, end))
        steps = max(map(abs, delta))
        for n in range(steps+1):
            pos = tuple(round(a+d*n/max(1, steps)) for a, d in zip(start, delta))
            self.put(*pos, key, priority=priority, **properties)

    def floor(self, cells, y, key='minecraft:spruce_planks', priority=50):
        minx = min(x for x, z in cells)
        minz = min(z for x, z in cells)
        for x, z in cells:
            material = key
            if key == 'minecraft:spruce_planks':
                if (z-minz) % 8 == 0:
                    material = 'minecraft:polished_andesite' if (x-minx) % 8 == 0 else 'minecraft:dark_oak_planks'
                elif (x-minx) % 4 == 0:
                    material = 'minecraft:stripped_oak_wood'
            self.put(x, y, z, material, priority=priority)

    def stock(self, x, y, z, title, items, facing='south'):
        self.put(x, y, z, 'minecraft:chest', priority=90, facing=facing, type='single', waterlogged=False)
        if any(item not in self.registry['items'] for item in items):
            raise UserError('A shop inventory contains an unregistered item')
        entries = ','.join('{Slot:'+str(i)+'b,id:'+json.dumps(item)+',count:1}' for i, item in enumerate(items))
        self.tags[x, y, z] = '{CustomName:'+json.dumps(json.dumps({'text': title}))+',Items:['+entries+']}'

    def sign(self, x, y, z, text, facing):
        self.put(x, y, z, 'minecraft:oak_wall_sign', priority=95, facing=facing, waterlogged=False)
        messages = [json.dumps(json.dumps({'text': line, 'color': 'black'})) for line in (text+['']*4)[:4]]
        self.tags[x, y, z] = '{is_waxed:1b,front_text:{messages:['+','.join(messages)+'],color:"black",has_glowing_text:0b}}'

    def walk(self, ident, cells, floor=0):
        points = []
        for x, z in cells:
            y = floor(x, z) if callable(floor) else floor
            self.navigation.add((x, y+1, z))
            points.append([x+.5, y+1, z+.5])
        self.routes.append({'id': ident, 'local_player_feet': points})

    def serialize(self, backup_sha256):
        palette = sorted(set(self.blocks.values()))
        indexes = {state: i for i, state in enumerate(palette)}
        ox, oy, oz = self.origin
        blocks = [[x+ox, y+oy, z+oz, indexes[state]] for (x, y, z), state in
                  sorted(self.blocks.items(), key=lambda row: ((row[0][0]+ox)//16, (row[0][2]+oz)//16, row[0][1], row[0][0], row[0][2]))]
        return {'format': 'awft-native-settlement:1', 'name': 'Signal Lane — authored waterfront prototype',
                'created': utcnow(), 'seed': self.registry['seed'], 'world_path': self.registry['world_path'],
                'backup_sha256': backup_sha256, 'bounds': [ox-2, oz-3, ox+61, oz+44],
                'palette': palette, 'blocks': blocks,
                'block_entities': [{'pos': [x+ox, y+oy, z+oz], 'nbt': tag} for (x, y, z), tag in sorted(self.tags.items())],
                'commands': [], 'landmarks': [{'name': row['name'], 'dimension': 'minecraft:overworld',
                    'x': ox+row['door'][0], 'y': oy+row['door'][1]+1, 'z': oz+row['door'][2],
                    'category': 'Authored prototype', 'features': row['rooms']} for row in self.lots],
                'coverage': {key: sorted(value) for key, value in self.uses.items()},
                'prototype_only': True, 'validation': 'Authored source and geometry only; native walking, rendering and owner artistic acceptance pending.'}


def foundations(p):
    """Explicit staging-only replacement prism, then a modest quay/land plinth."""
    for x in range(60):
        for z in range(44):
            f = grade(x)
            for y in range(-4, f+1):
                material = 'minecraft:stone_bricks' if z < 3 else 'minecraft:stone'
                if y == f and z >= 3:
                    material = 'minecraft:grass_block'
                p.put(x, y, z, material, priority=1)
            for y in range(f+1, 28):
                p.put(x, y, z, 'minecraft:air', priority=0)
    # Existing water north of this surveyed land site is never filled or invented.
    for x in range(60):
        for z in range(4):
            p.put(x, grade(x), z, 'minecraft:polished_andesite' if x % 8 == 0 else
                  'minecraft:stone_bricks', priority=10)
        # A continuous five-wide lane changes direction rather than using lots.
        cz = street_z(x)
        for z in range(cz-2, cz+3):
            material = 'minecraft:cobblestone' if z in (cz-2, cz+2) else 'minecraft:andesite'
            p.put(x, grade(x), z, material, priority=10)
        if x == 44:
            for z in [*range(4), *range(cz-2, cz+3)]:
                p.put(x, 1, z, 'minecraft:stone_brick_stairs', priority=12,
                      facing='east', half='bottom', shape='straight', waterlogged=False)
    for x in (0, 1, 43, 44, 58, 59):
        for z in range(4, street_z(x)+1):
            p.put(x, grade(x), z, 'minecraft:andesite', priority=10)
    p.walk('signal-lane', [(x, street_z(x)) for x in range(60)], lambda x, z: 1 if x == 44 else grade(x))
    p.walk('quay', [(x, 2) for x in range(60)], lambda x, z: 1 if x == 44 else grade(x))


def shell(p, b):
    p.zone = b.name
    window = ('mcwwindows:stripped_spruce_log_window2' if b.ident in ('apothecary', 'bookbinder')
              else 'mcwwindows:dark_oak_window2' if b.ident in ('chandler', 'inn', 'harbormaster')
              else 'mcwwindows:spruce_four_window')
    for level, cells in enumerate(b.levels):
        f = b.base+level*4
        outside = edge(cells)
        minx, maxx = min(x for x, z in cells), max(x for x, z in cells)
        minz, maxz = min(z for x, z in cells), max(z for x, z in cells)
        p.floor(cells, f)
        for x, z in cells:
            if level == 0:
                for y in range(-3, f):
                    if (z-minz) % 8 == 0:
                        material = 'minecraft:chiseled_stone_bricks' if (x-minx) % 8 == 0 else (
                            'minecraft:smooth_stone' if y == -1 else 'minecraft:polished_andesite')
                    elif (x-minx) % 4 == 0:
                        material = 'minecraft:polished_deepslate' if y == -1 else 'minecraft:cobbled_deepslate'
                    else:
                        material = 'minecraft:mossy_stone_bricks' if y == -1 else 'minecraft:stone_bricks'
                    p.put(x, y, z, material, priority=30)
            for y in range(f+1, f+4):
                material = b.plaster[level] if (x, z) in outside else 'minecraft:air'
                frontal = (x, z-1) not in cells or (x, z+1) not in cells
                lateral = (x-1, z) not in cells or (x+1, z) not in cells
                if (x, z) in outside and ((frontal and (x-minx) % 3 == 0) or
                                         (lateral and (z-minz) % 3 == 0)):
                    material = b.timber
                p.put(x, y, z, material, priority=50, **({'axis': 'y'} if material == b.timber else {}))
            if (x, z) in outside:
                # Front lintels, side plates and stone joint keys have distinct
                # construction roles. Rotating one log state is not a material break.
                frontal = (x, z-1) not in cells or (x, z+1) not in cells
                material = 'minecraft:dark_oak_planks' if frontal else 'minecraft:dark_oak_wood'
                if ((x-minx) if frontal else (z-minz)) % 8 == 0:
                    material = 'minecraft:polished_andesite'
                p.put(x, f+4, z, material, priority=55, **({'axis': 'z'} if material.endswith('_wood') else {}))
        frontz = max(z for x, z in cells) if b.front == 'south' else min(z for x, z in cells)
        for wx in b.windows[level]:
            # Locate each authored bay on its own stepped facade.
            row = [z for x, z in cells if x == wx]
            if not row:
                continue
            wz = max(row) if b.front == 'south' else min(row)
            for dy in (2, 3):
                p.put(wx, f+dy, wz, window, priority=65, facing=b.front, windowstate='closed')
                if wx+1 < maxx:
                    p.put(wx+1, f+dy, wz, window, priority=65, facing=b.front, windowstate='closed')
            exterior = 1 if b.front == 'south' else -1
            for sx in (wx-1, wx+2):
                if minx <= sx <= maxx and sx != b.door_x:
                    p.put(sx, f+2, wz+exterior, 'minecraft:spruce_trapdoor', priority=60,
                          facing=b.front, half='bottom', open=True, powered=False, waterlogged=False)
            if level:
                p.put(wx, f+1, wz+exterior, 'minecraft:spruce_trapdoor', priority=60,
                      facing=b.front, half='top', open=False, powered=False, waterlogged=False)
        # Quay/rear windows and side glazing keep inhabited rooms from being boxes.
        backz = min(z for x, z in cells) if b.front == 'south' else max(z for x, z in cells)
        for wx in (minx+2, maxx-2):
            if (wx, backz) in outside:
                for dy in (2, 3):
                    p.put(wx, f+dy, backz, window, priority=65,
                          facing='north' if b.front == 'south' else 'south', windowstate='closed')
        for wz in sorted({z for x, z in cells})[3:-2:4]:
            if (minx, wz) in outside:
                p.put(minx, f+2, wz, window, priority=65, facing='west', windowstate='closed')
        p.rooms.append({'building': b.ident, 'level': level, 'local_floor_y': f,
                        'program': b.program[level], 'outline': [[x, z] for x, z in sorted(cells)]})
    top = b.base+len(b.levels)*4
    p.floor(b.levels[-1], top)
    for roof in b.roofs:
        roof_section(p, b, roof, top)
    # Jetties bear on visible upturned brackets rather than floating upper boxes.
    outward = 1 if b.front == 'south' else -1
    for x, z in sorted(b.levels[1]-b.levels[0]):
        if (x, z-outward) in b.levels[0]:
            p.put(x, b.base+3, z, 'minecraft:dark_oak_stairs', priority=58,
                  facing='north' if outward == 1 else 'south', half='top', shape='straight', waterlogged=False)


def roof_section(p, b, r, base):
    base += r.offset
    x1, z1, x2, z2 = r.bounds
    width = x2-x1+1 if r.axis == 'z' else z2-z1+1
    if len(r.profile) != width:
        raise UserError('Authored roof section profile does not match '+b.name)
    main = {'minecraft:dark_oak_stairs': 'mcwroofs:dark_oak_roof', 'minecraft:spruce_stairs': 'mcwroofs:spruce_roof',
            'minecraft:brick_stairs': 'mcwroofs:bricks_roof', 'minecraft:deepslate_tile_stairs': 'mcwroofs:deepslate_roof',
            'minecraft:deepslate_brick_stairs': 'mcwroofs:deepslate_roof'}[r.stairs]
    # Rear additions have a different covering, not merely a changed block state.
    # This makes the older annex legible and separates orthogonal material runs.
    if r.axis == 'x':
        main = {'mcwroofs:dark_oak_roof': 'mcwroofs:brown_terracotta_roof',
                'mcwroofs:spruce_roof': 'mcwroofs:dark_oak_roof',
                'mcwroofs:bricks_roof': 'mcwroofs:red_terracotta_roof',
                'mcwroofs:deepslate_roof': 'mcwroofs:stone_bricks_roof'}[main]
    cap = main.removesuffix('_roof')+'_top_roof'
    peak = min((i for i, h in enumerate(r.profile) if h == max(r.profile)), key=lambda i: abs(i-width/2))
    for x in range(x1, x2+1):
        for z in range(z1, z2+1):
            cross = x-x1 if r.axis == 'z' else z-z1
            height = r.profile[cross]
            if r.hip:
                length = z2-z1 if r.axis == 'z' else x2-x1
                along = z-z1 if r.axis == 'z' else x-x1
                height = min(height, min(along, length-along)+1)
            # A hollow shell, with a riser only where the authored gambrel steepens.
            if cross and abs(height-r.profile[cross-1]) > 1:
                p.put(x, base+height-1, z, 'minecraft:deepslate_tiles', priority=40)
            if cross < width//2:
                facing = 'east' if r.axis == 'z' else 'south'
            else:
                facing = 'west' if r.axis == 'z' else 'north'
            if cross == peak:
                p.put(x, base+height, z, cap, priority=42, part='switched_0' if r.axis == 'z' else 'switched_90')
            else:
                p.put(x, base+height, z, main, priority=42, facing=facing, half='bottom', shape='straight')
    # Timber/plaster gable triangles are inset one metre behind the roof edge.
    if not r.hip:
        for n, height in enumerate(r.profile[1:-1], 1):
            for end in ((z1+1, z2-1) if r.axis == 'z' else (x1+1, x2-1)):
                x, z = (x1+n, end) if r.axis == 'z' else (end, z1+n)
                for dy in range(height):
                    material = b.timber if n % 3 == 0 else b.plaster[-1]
                    if dy == 0:
                        material = 'minecraft:dark_oak_planks' if r.axis == 'z' else 'minecraft:dark_oak_wood'
                        if n % 8 == 0:
                            material = 'minecraft:polished_andesite'
                    props = {'axis': 'y'} if material == b.timber else {}
                    if material.endswith('_wood'):
                        props = {'axis': 'z'}
                    p.put(x, base+dy, z, material, priority=44, **props)


def entrance(p, b):
    cells = b.levels[0]
    zz = sorted(z for x, z in cells if x == b.door_x)
    z = max(zz) if b.front == 'south' else min(zz)
    f = b.base
    inward = 'north' if b.front == 'south' else 'south'
    for half, dy in (('lower', 1), ('upper', 2)):
        p.put(b.door_x, f+dy, z, 'mcwdoors:dark_oak_cottage_door', priority=85,
              facing=inward, half=half, hinge='left', open=False, powered=False)
    end = street_z(b.door_x)
    step = 1 if end > z else -1
    approach = []
    for wz in range(z+step, end+step, step):
        for x in range(b.door_x-1, b.door_x+2):
            p.put(x, grade(x), wz, 'minecraft:stone_bricks', priority=15)
        approach.append((b.door_x, wz))
    if f > grade(b.door_x):
        p.put(b.door_x, f, z+step, 'minecraft:stone_brick_stairs', priority=70,
              facing=inward, half='bottom', shape='straight', waterlogged=False)
    p.walk(b.ident+'-door', [(b.door_x, z), *approach],
           lambda x, wz: f if wz in (z, z+step) and f > grade(x) else grade(x))
    # A painted trade sign sits above eye level; the awning stays out of the lane.
    sx = min(x for x, zz in cells)+1
    front = 1 if b.front == 'south' else -1
    p.sign(sx, f+3, z+front, [b.name, b.purpose[:20], '', 'Signal Lane'], b.front)
    if b.ident in ('chandler', 'fishmonger', 'bookbinder', 'inn'):
        for x in range(b.door_x-1, b.door_x+3):
            for dz in (1, 2):
                p.put(x, f+3, z+front*dz, 'minecraft:white_wool' if x % 2 else 'minecraft:brown_wool', priority=61)
    p.lots.append({'id': b.ident, 'name': b.name, 'purpose': b.purpose,
                   'door': [b.door_x, f, z], 'rooms': list(b.program),
                   'storeys': len(b.levels), 'frontage_metres': max(x for x, z in cells)-min(x for x, z in cells)+1,
                   'footprint_square_metres': len(cells), 'roof_sections': len(b.roofs)})


def stairs(p, b):
    # The same local circulation core links individually different floor outlines.
    common = set.intersection(*b.levels)
    inside = set.intersection(*(cells-edge(cells) for cells in b.levels))
    candidates = [(x, z) for x, z in inside if
                  all((x, z-n) in inside and (x-1, z-n) in inside for n in range(5))]
    if not candidates:
        raise UserError('Authored stair core does not fit '+b.name)
    x, start = max(candidates, key=lambda pair: (pair[0], pair[1]))
    for level in range(len(b.levels)-1):
        f = b.base+4*level
        route = []
        for n in range(4):
            z, y = start-n, f+1+n
            for py in range(y+1, y+4):
                p.put(x, py, z, 'minecraft:air', priority=100)
            p.put(x, y, z, 'minecraft:spruce_stairs', priority=101,
                  facing='north', half='bottom', shape='straight', waterlogged=False)
            route.append([x+.5, y+1, z+.5])
        p.put(x, f+4, start-4, 'minecraft:spruce_planks', priority=101)
        route.append([x+.5, f+5, start-4+.5])
        p.routes.append({'id': b.ident+'-stairs-'+str(level), 'local_player_feet': route})
    return x, start


def furnishings(p, b, core):
    """Small rooms with useful equipment, preserving the two-cell stair strip."""
    stairx, start = core
    for level, cells in enumerate(b.levels):
        f = b.base+4*level
        minx, minz = min(x for x, z in cells), min(z for x, z in cells)
        maxx, maxz = max(x for x, z in cells), max(z for x, z in cells)
        room = {(x, z) for x, z in cells-edge(cells) if x < stairx-1}
        if not room:
            raise UserError('No furnished room remains beside the stairs in '+b.name)
        ax = min(x for x, z in room)+1
        az = min(z for x, z in room)+1
        # The rear/side circulation lane remains free for reaching every landing.
        lx, lz = minx+1, maxz-2
        p.put(lx, f+1, lz, 'minecraft:crafting_table', priority=80)
        if level == 0:
            if b.ident in ('chandler', 'sailmaker', 'fishmonger'):
                p.put(lx+1, f+1, lz, 'farmersdelight:cutting_board', priority=80)
                p.put(lx, f+1, lz-1, 'minecraft:barrel', priority=80, facing='up', open=False)
                p.put(lx, f+1, lz-2, 'minecraft:barrel', priority=80, facing='up', open=False)
            elif b.ident in ('bookbinder', 'harbormaster', 'keeper'):
                p.put(lx+1, f+1, lz, 'minecraft:cartography_table', priority=80)
                for sx in range(lx, lx+3):
                    if sx != b.door_x:
                        for dy in (1, 2):
                            p.put(sx, f+dy, minz+1, 'minecraft:bookshelf', priority=80)
            elif b.ident == 'apothecary':
                p.put(lx+1, f+1, lz, 'minecraft:brewing_stand', priority=80)
                p.put(lx, f+1, lz-1, 'minecraft:water_cauldron', priority=80, level=3)
                p.put(lx+1, f+1, lz-1, 'minecraft:potted_fern', priority=80)
            else:
                p.put(lx, f+1, lz-1, 'minecraft:furnace', priority=80, facing='east', lit=False)
                p.put(lx+1, f+1, lz-1, 'farmersdelight:spruce_cabinet', priority=80, facing='south', open=False)
            items = ('minecraft:paper', 'minecraft:string', 'minecraft:leather') if b.ident in ('chandler', 'sailmaker') else (
                    ('minecraft:book', 'minecraft:paper', 'minecraft:ink_sac') if b.ident in ('bookbinder', 'harbormaster', 'keeper')
                    else ('minecraft:wheat', 'minecraft:carrot', 'minecraft:coal'))
            p.stock(lx, f+1, minz+2, b.name+' supplies', items, facing='east')
        else:
            p.put(lx, f+1, minz+1, 'farmersdelight:spruce_cabinet', priority=80, facing='south', open=False)
            if level == len(b.levels)-1:
                bx, bz = minx+2, minz+3
                p.put(bx, f+1, bz, 'minecraft:white_bed', priority=80, facing='north', part='foot', occupied=False)
                p.put(bx, f+1, bz-1, 'minecraft:white_bed', priority=80, facing='north', part='head', occupied=False)
                p.put(minx+1, f+1, minz+1, 'minecraft:bookshelf', priority=80)
                p.stock(minx+1, f+1, maxz-2, b.name+' sea chest', ('minecraft:book', 'minecraft:paper'), facing='east')
        # One proper table/chair pair instead of a room filled with anonymous crates.
        tx, tz = minx+3, minz+4
        if (tx, tz) in room and (tx-1, tz) in room:
            p.put(tx, f+1, tz, 'handcrafted:spruce_table', priority=80, color='none', shape='single', waterlogged=False)
            p.put(tx-1, f+1, tz, 'handcrafted:spruce_chair', priority=80, facing='east', color='none', waterlogged=False)
        p.put(minx+3, f+3, minz+3, 'minecraft:lantern', priority=80, hanging=True, waterlogged=False)
    # Every floor gets the same unobstructed return corridor beside the flight.
    for level in range(len(b.levels)):
        f = b.base+4*level
        for z in range(start-4, start+1):
            for dy in (1, 2):
                p.put(stairx-1, f+dy, z, 'minecraft:air', priority=99)
        p.walk(b.ident+'-landing-'+str(level), [(stairx-1, z) for z in range(start-4, start+1)], f)


def courtyard(p):
    p.zone = 'Needle Court and courtyard passage'
    # A three-wide, genuinely open passage beneath an occupied upper floor.
    for x in range(27, 30):
        for z in range(21, 35):
            p.put(x, 0, z, 'minecraft:stone_bricks', priority=90)
            for y in (1, 2, 3):
                p.put(x, y, z, 'minecraft:air', priority=105)
    for x in range(28, 36):
        for z in range(33, 42):
            p.put(x, 0, z, 'minecraft:stone_bricks' if x == 31 or z == 37 else 'minecraft:andesite', priority=60)
    for x in (28, 35):
        for z in range(34, 42):
            if x == 28 and z in (34, 35, 36):
                continue
            p.put(x, 1, z, 'minecraft:mossy_stone_brick_wall', priority=60, up=True, waterlogged=False)
    for x in range(28, 36):
        p.put(x, 1, 41, 'minecraft:mossy_stone_brick_wall', priority=60, up=True, waterlogged=False)
    for z in range(21, 41):
        for x in (34, 35, 36):
            p.put(x, 0, z, 'minecraft:cobblestone', priority=75)
            for dy in (1, 2):
                p.put(x, dy, z, 'minecraft:air', priority=106)
    for x, z, flower in ((29, 37, 'minecraft:rose_bush'), (33, 39, 'minecraft:peony')):
        p.put(x, 0, z, 'minecraft:grass_block', priority=80)
        p.put(x, 1, z, flower, priority=80, half='lower')
        p.put(x, 2, z, flower, priority=80, half='upper')
    p.line((30, 1, 40), (32, 1, 40), 'minecraft:spruce_stairs', priority=80,
           facing='north', half='bottom', shape='straight', waterlogged=False)
    p.put(31, 1, 36, 'minecraft:barrel', priority=80, facing='up', open=False)
    p.put(31, 2, 36, 'minecraft:potted_flowering_azalea_bush', priority=80)
    p.put(28, 3, 30, 'minecraft:lantern', priority=107, hanging=True, waterlogged=False)
    p.walk('covered-alley', [(28, z) for z in range(20, 36)])
    p.walk('courtyard-return-alley', [(35, z) for z in range(21, 41)])


def small_details(p):
    p.zone = 'Quay and authored street details'
    for x in (2, 20, 34, 57):
        f = grade(x)
        p.line((x, f+1, 0), (x, f+2, 0), 'minecraft:stripped_spruce_log', priority=50, axis='y')
        p.put(x, f+3, 0, 'minecraft:lantern', priority=60, hanging=False, waterlogged=False)
    for x, z in ((4, 5), (16, 4), (28, 4), (50, 5)):
        f = grade(x)
        p.put(x, f+1, z, 'minecraft:barrel', priority=60, facing='up', open=False)
        p.put(x+1, f+1, z, 'minecraft:barrel', priority=60, facing='north', open=False)
        p.put(x, f+2, z, 'minecraft:spruce_trapdoor', priority=62, facing='south', half='bottom', open=False,
              powered=False, waterlogged=False)
    # Limited foliage forms one courtyard vignette; it does not hide bad massing.
    p.line((32, 1, 35), (32, 4, 35), 'minecraft:birch_log', priority=80, axis='y')
    for x in range(30, 35):
        for z in range(33, 38):
            if abs(x-32)+abs(z-35) <= 3:
                p.put(x, 5, z, 'minecraft:birch_leaves', priority=80, persistent=True, distance=1, waterlogged=False)
    for x, z in ((3, 20), (20, 22), (43, 25), (55, 26)):
        f = grade(x)
        p.put(x, f+1, z, 'minecraft:flower_pot', priority=60)
    for b in ('chandler', 'inn', 'apothecary', 'keeper'):
        lot = next(row for row in p.lots if row['id'] == b)
        p.zone = lot['name']
        dx, f, dz = lot['door']
        roof = next(row for row in designs() if row.ident == b)
        cy = roof.base+len(roof.levels)*4+4
        cx, cz = min(x for x, z in roof.levels[-1])+1, min(z for x, z in roof.levels[-1])+2
        p.line((cx, cy-2, cz), (cx, cy+1, cz), 'minecraft:bricks', priority=82)
        p.put(cx, cy+2, cz, 'minecraft:brick_slab', priority=82, type='bottom', waterlogged=False)


def room_connections(p):
    """Find actual planned clear ground-floor paths from each door to its stairs."""
    for b in designs():
        route = next(row for row in p.routes if row['id'] == b.ident+'-landing-0')
        goal = tuple(int(n) for n in (route['local_player_feet'][0][0], route['local_player_feet'][0][2]))
        lot = next(row for row in p.lots if row['id'] == b.ident)
        start = lot['door'][0], lot['door'][2]
        feet = b.base+1
        def clear(cell):
            return cell in b.levels[0] and all(
                p.blocks.get((cell[0], feet+dy, cell[1]), 'minecraft:air').split('[', 1)[0]
                in ('minecraft:air', 'mcwdoors:dark_oak_cottage_door') for dy in (0, 1))
        queue, previous = deque([start]), {start: None}
        while queue and goal not in previous:
            x, z = queue.popleft()
            for cell in ((x-1, z), (x+1, z), (x, z-1), (x, z+1)):
                if cell not in previous and clear(cell):
                    previous[cell] = x, z
                    queue.append(cell)
        if goal not in previous:
            raise UserError('No planned door-to-stair connection in '+b.name)
        cells, cell = [], goal
        while cell is not None:
            cells.append(cell)
            cell = previous[cell]
        p.walk(b.ident+'-shop-circulation', cells[::-1], b.base)


def planned_clearance(p):
    """Check reserved walking cells. This is not native player collision proof."""
    failures = []
    passable = ('minecraft:air', 'mcwdoors:dark_oak_cottage_door', 'minecraft:oak_wall_sign')
    for x, feet, z in sorted(p.navigation):
        for dy in (0, 1):
            state = p.blocks.get((x, feet+dy, z), 'minecraft:air')
            if not any(state == key or state.startswith(key+'[') for key in passable):
                failures.append({'local': [x, feet+dy, z], 'state': state})
    return {'planned_cells': len(p.navigation), 'blocked': failures,
            'scope': 'Two reserved full body cells; planned stairs are listed separately. Native walking still pending.'}


def building_material_checks(p):
    """Check final authored solids for every entire building, including its roof."""
    return [require_material_rule({position: state for position, state in p.blocks.items()
                if p.owners[position] == b.name}, b.name) for b in designs()]


def construct(registry, origin=(0, 65, 0)):
    p = StreetPlan(registry, origin)
    foundations(p)
    buildings = designs()
    for b in buildings:
        shell(p, b)
        entrance(p, b)
        core = stairs(p, b)
        furnishings(p, b, core)
    courtyard(p)
    small_details(p)
    room_connections(p)
    p.captures = [
        {'id': 'street-west', 'feet': [.5, 1, 22.5], 'look_at': [23, 5, 18]},
        {'id': 'inn-bend', 'feet': [24.5, 1, 19.5], 'look_at': [32, 6, 19]},
        {'id': 'covered-alley', 'feet': [28.5, 1, 28.5], 'look_at': [29, 3, 37]},
        {'id': 'quay-frontage', 'feet': [30.5, 1, 2.5], 'look_at': [28, 8, 14]},
        {'id': 'street-east', 'feet': [57.5, 2, 24.5], 'look_at': [36, 5, 21]},
        {'id': 'skyline', 'feet': [31, 24, -2], 'look_at': [31, 8, 22]},
    ]
    return p


def prepare(home, registry_path, destination, backup_sha256, origin):
    """Write a fresh private plan bundle, without admitting or placing it."""
    home, destination = Path(home).resolve(), Path(destination).resolve()
    if home.drive.upper() != 'D:' or not destination.is_relative_to(home/'staging') or destination.exists():
        raise UserError('Use a NEW bounded private D: staging output folder')
    if not re.fullmatch(r'[0-9a-f]{64}', backup_sha256):
        raise UserError('Supply the actual reviewed staging backup SHA-256')
    if Path(registry_path).stat().st_size > 8*MIB:
        raise UserError('Native registry export exceeds this prototype read bound')
    registry = json.loads(Path(registry_path).read_text(encoding='utf-8'))
    world = Path(registry['world_path']).resolve()
    if not world.is_relative_to(home/'staging'):
        raise UserError('This source admits PRIVATE STAGING registry bindings only; official world refused')
    guarded = subprocess.run(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(GUARD),
        '-EstimatedCBytes', '0', '-EstimatedDBytes', str(MAX_BUNDLE)], capture_output=True, text=True,
        creationflags=subprocess.CREATE_NO_WINDOW, check=False)
    receipt = json.loads(guarded.stdout)
    if guarded.returncode or not receipt.get('allowed'):
        raise UserError('The storage reserve refused this finite prototype bundle')
    p = construct(registry, origin)
    clear = planned_clearance(p)
    if clear['blocked']:
        raise UserError('Reserved walk route intersects planned geometry: '+str(clear['blocked'][:12]))
    materials = building_material_checks(p)
    native = p.serialize(backup_sha256)
    encoded = (json.dumps(native, separators=(',', ':'), ensure_ascii=False)+'\n').encode()
    if len(encoded) > 12*MIB:
        raise UserError('Native prototype plan exceeds its finite allocation')
    plan_sha = hashlib.sha256(encoded).hexdigest()
    ox, oy, oz = origin
    manifest = {'format': 'awft-artistic-street:1', 'created': utcnow(), 'plan_sha256': plan_sha,
        'prototype_only': True, 'source_sha256': digest(Path(__file__)), 'registry_sha256': digest(Path(registry_path)),
        'local_origin': list(origin), 'reviewed_staging_backup_sha256': backup_sha256,
        'placements': len(p.blocks), 'block_entities': len(p.tags), 'entity_commands': 0,
        'clear_prism_local': [0, 1, 0, 59, 27, 43], 'lots': p.lots, 'rooms': p.rooms,
        'routes': p.routes, 'planned_clearance': clear, 'material_rule': materials,
        'native_capture_positions': [row|{'world_feet': [ox+row['feet'][0], oy+row['feet'][1], oz+row['feet'][2]],
            'world_look_at': [ox+row['look_at'][0], oy+row['look_at'][1], oz+row['look_at'][2]]} for row in p.captures],
        'mods_used': {key: sorted(value) for key, value in p.uses.items()},
        'technical_status': 'Source/palette/planned clearance only; placement and real walking pending',
        'visual_status': 'UNVERIFIED: genuine native screenshots and artistic review required before broader reconstruction',
        'owner_acceptance': 'not requested or inferred', 'storage_guard': receipt}
    rendered = (json.dumps(manifest, indent=2, sort_keys=True)+'\n').encode()
    if len(encoded)+len(rendered) > MAX_BUNDLE:
        raise UserError('Prototype bundle exceeds finite allocation')
    destination.mkdir(parents=True, exist_ok=False)
    plan_path = destination/('signal-lane-'+plan_sha[:16]+'.json')
    plan_path.write_bytes(encoded)
    (destination/'manifest.json').write_bytes(rendered)
    return {'plan': str(plan_path), 'sha256': plan_sha, 'manifest': str(destination/'manifest.json'),
            'placements': len(p.blocks), 'lots': len(p.lots), 'visual_acceptance': 'pending actual screenshots'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--home', type=Path, default=Path(r'D:\A World for Two'))
    parser.add_argument('--registry', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--backup-sha256', required=True)
    parser.add_argument('--origin', type=int, nargs=3, default=(1224, 65, -1264), metavar=('X', 'Y', 'Z'))
    arguments = parser.parse_args()
    print(json.dumps(prepare(arguments.home, arguments.registry, arguments.output,
                             arguments.backup_sha256, tuple(arguments.origin)), indent=2))
