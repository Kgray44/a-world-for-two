"""An individually authored cottage court for private native visual review.

This is a separate small composition, not a variant of the rejected town
builders. It shares only plan serialization and strict palette primitives with
Signal Lane. No world/API operations or entity spawning are performed here.
"""
from __future__ import annotations

import argparse
from collections import deque
import hashlib
import json
from pathlib import Path
import re
import subprocess

from control_room.common import UserError, digest, utcnow
from tools.artistic_materials import require_material_rule
from tools.artistic_street import StreetPlan, rectangle, layer, edge, GUARD, MAX_BUNDLE, MIB


ORIGIN = (1094, 67, -1118)
SIZE = (42, 38)
MAIN = 'Rose & Lantern Cottage'
BAKER = 'The Little Honey Oven'
WEAVER = 'Mallow & Thread'
GLASS = 'Rosemary Glasshouse'
BUILDINGS = (MAIN, BAKER, WEAVER, GLASS)
MAIN_GROUND = layer((3, 3, 12, 15), (13, 9, 18, 15), remove=((3, 3), (3, 4), (4, 3)))
MAIN_UPPER = layer((4, 4, 12, 14), (8, 15, 11, 15))
BAKER_GROUND = layer((29, 7, 37, 16), remove=((29, 7), (29, 8), (30, 7), (37, 16)))
WEAVER_GROUND = layer((7, 27, 17, 34), (6, 29, 6, 32), remove=((17, 34),))


class CottagePlan(StreetPlan):
    def __init__(self, registry, origin=ORIGIN):
        super().__init__(registry, origin)
        self.terrain = {}
        self.connections = []
        self.details = []

    def serialize(self, backup_sha256):
        native = super().serialize(backup_sha256)
        ox, oy, oz = self.origin
        native.update(name='Rose & Lantern Court — authored cottage prototype',
                      bounds=[ox, oz, ox+41, oz+37])
        return native


def terrain_samples(p, survey):
    """Use the existing original native ground samples, without publishing seed."""
    samples = survey['samples']
    ox, oy, oz = p.origin
    for x in range(SIZE[0]):
        for z in range(SIZE[1]):
            wx, wz = ox+x, oz+z
            nearest = sorted(samples, key=lambda row: (row['x']-wx)**2+(row['z']-wz)**2)[:4]
            if len(nearest) != 4 or any(row['fluid'] for row in nearest):
                raise UserError('Cottage court requires confirmed land samples around its footprint')
            if any(abs(row['x']-wx) > 16 or abs(row['z']-wz) > 16 for row in nearest):
                raise UserError('Cottage site lies outside its bounded original native survey')
            weights = [1/max(0.25, (row['x']-wx)**2+(row['z']-wz)**2) for row in nearest]
            ground = round(sum(row['y']*w for row, w in zip(nearest, weights))/sum(weights))-oy
            if not -2 <= ground <= 2:
                raise UserError('Cottage slope needs a new authored fit, not automatic terrain flattening')
            p.terrain[x, z] = ground
            # Clear vegetation only in this private prototype. Natural ground is
            # left at the measured height outside designed foundations and paths.
            for y in range(ground+1, 18):
                p.put(x, y, z, 'minecraft:air', priority=0)


def floor_and_foundation(p, cells, floor):
    minx, minz = min(x for x, z in cells), min(z for x, z in cells)
    for x, z in cells:
        for y in range(-3, floor):
            if (z-minz) % 8 == 0:
                material = 'minecraft:chiseled_stone_bricks' if (x-minx) % 8 == 0 else (
                    'minecraft:smooth_stone' if y == -1 else 'minecraft:polished_andesite')
            elif (x-minx) % 4 == 0:
                material = 'minecraft:polished_deepslate' if y == -1 else 'minecraft:cobbled_deepslate'
            else:
                material = 'minecraft:mossy_stone_bricks' if y == -1 else 'minecraft:stone_bricks'
            p.put(x, y, z, material, priority=20)
    p.floor(cells, floor)


def framed_room(p, cells, floor, plaster, timber):
    """Low three-high plaster panels, real openings and separate sill/side plates."""
    outside = edge(cells)
    minx, minz = min(x for x, z in cells), min(z for x, z in cells)
    p.floor(cells, floor)
    for x, z in cells:
        frontal = (x, z-1) not in cells or (x, z+1) not in cells
        lateral = (x-1, z) not in cells or (x+1, z) not in cells
        stile = (frontal and (x-minx) % 3 == 0) or (lateral and (z-minz) % 3 == 0)
        for y in range(floor+1, floor+4):
            material = timber if stile else plaster
            if (x, z) not in outside:
                material = 'minecraft:air'
            p.put(x, y, z, material, priority=50, **({'axis': 'y'} if material == timber else {}))
        if (x, z) in outside:
            material = 'minecraft:dark_oak_planks' if frontal else 'minecraft:dark_oak_wood'
            n = x-minx if frontal else z-minz
            if n % 8 == 0:
                material = 'minecraft:stripped_dark_oak_wood'
            p.put(x, floor+4, z, material, priority=55,
                  **({'axis': 'z'} if material.endswith('_wood') else {}))


def window(p, x, floor, z, facing, wood='birch', wide=True):
    key = 'mcwwindows:'+wood+'_window2'
    axis = (1, 0) if facing in ('north', 'south') else (0, 1)
    for n in range(2 if wide else 1):
        for dy in (2, 3):
            p.put(x+axis[0]*n, floor+dy, z+axis[1]*n, key,
                  priority=65, facing=facing, windowstate='closed')


def door(p, x, floor, z, facing, wood='birch'):
    for half, dy in (('lower', 1), ('upper', 2)):
        p.put(x, floor+dy, z, 'mcwdoors:'+wood+'_cottage_door', priority=85,
              facing=facing, half=half, hinge='left', open=False, powered=False)


def roof(p, bounds, axis, profile, base, material, plaster, timber):
    """One explicitly drawn short hollow section; no solid roof wedges."""
    x1, z1, x2, z2 = bounds
    width = x2-x1+1 if axis == 'z' else z2-z1+1
    if len(profile) != width:
        raise UserError('Authored cottage roof profile mismatch')
    peak = min((i for i, value in enumerate(profile) if value == max(profile)), key=lambda i: abs(i-width/2))
    cap = material.removesuffix('_roof')+'_top_roof'
    for x in range(x1, x2+1):
        for z in range(z1, z2+1):
            n = x-x1 if axis == 'z' else z-z1
            if n == peak:
                p.put(x, base+profile[n], z, cap, priority=45,
                      part='switched_0' if axis == 'z' else 'switched_90')
            else:
                facing = ('east' if n < width//2 else 'west') if axis == 'z' else (
                    'south' if n < width//2 else 'north')
                p.put(x, base+profile[n], z, material, priority=45,
                      facing=facing, half='bottom', shape='straight')
    for n, height in enumerate(profile[1:-1], 1):
        for end in ((z1+1, z2-1) if axis == 'z' else (x1+1, x2-1)):
            x, z = (x1+n, end) if axis == 'z' else (end, z1+n)
            for dy in range(height):
                key = timber if n % 3 == 0 else plaster
                if dy == 0:
                    key = 'minecraft:dark_oak_planks' if axis == 'z' else 'minecraft:dark_oak_wood'
                    if n % 8 == 0:
                        key = 'minecraft:stripped_dark_oak_wood'
                props = {'axis': 'y'} if key == timber else {'axis': 'z'} if key.endswith('_wood') else {}
                p.put(x, base+dy, z, key, priority=44, **props)


def stair(p, x, start, floor, label):
    route = []
    for n in range(4):
        z, y = start-n, floor+1+n
        for dy in (1, 2):
            p.put(x, y+dy, z, 'minecraft:air', priority=100)
        p.put(x, y, z, 'minecraft:spruce_stairs', priority=101,
              facing='north', half='bottom', shape='straight', waterlogged=False)
        route.append([x+.5, y+1, z+.5])
    p.put(x, floor+4, start-4, 'minecraft:spruce_planks', priority=101)
    for level in (0, 1):
        f = floor+level*4
        for z in range(start-4, start+1):
            for dy in (1, 2):
                p.put(x-1, f+dy, z, 'minecraft:air', priority=99)
        p.walk(label+'-landing-'+str(level), [(x-1, z) for z in range(start-4, start+1)], f)
    p.routes.append({'id': label+'-stairs', 'local_player_feet': route})


def lamp(p, x, y, z, facing):
    p.put(x, y, z, 'mcwlights:bell_wall_lantern', priority=82, facing=facing)


def room(p, name, level, floor, cells, program):
    p.rooms.append({'building': name, 'level': level, 'local_floor_y': floor,
                    'program': program, 'outline': [list(cell) for cell in sorted(cells)]})


def couple_cottage(p):
    p.zone = MAIN
    floor_and_foundation(p, MAIN_GROUND, 1)
    framed_room(p, MAIN_GROUND, 1, 'minecraft:white_terracotta', 'minecraft:stripped_oak_log')
    framed_room(p, MAIN_UPPER, 5, 'minecraft:calcite', 'minecraft:stripped_oak_log')
    p.floor(MAIN_UPPER, 9)
    roof(p, (2, 2, 13, 10), 'z', (0, 1, 2, 3, 4, 4, 4, 4, 3, 2, 1, 0), 9,
         'mcwroofs:green_terracotta_roof', 'minecraft:calcite', 'minecraft:stripped_oak_log')
    roof(p, (3, 9, 13, 16), 'z', (0, 1, 2, 3, 4, 4, 4, 3, 2, 1, 0), 8,
         'mcwroofs:green_terracotta_roof', 'minecraft:calcite', 'minecraft:stripped_oak_log')
    roof(p, (12, 8, 19, 16), 'x', (0, 1, 2, 3, 3, 3, 2, 1, 0), 5,
         'mcwroofs:brown_terracotta_roof', 'minecraft:white_terracotta', 'minecraft:stripped_oak_log')
    door(p, 10, 1, 15, 'north')
    for wx in (5, 14, 17):
        window(p, wx, 1, 15, 'south', wide=wx != 17)
    window(p, 3, 1, 8, 'west', 'oak')
    window(p, 7, 5, 4, 'north')
    window(p, 4, 5, 8, 'west', 'oak')
    # Proper two-wide balcony with a real upstairs opening and load brackets.
    p.floor(rectangle(8, 15, 12, 17), 5, priority=60)
    p.put(12, 5, 15, 'minecraft:stripped_dark_oak_wood', priority=65, axis='x')
    door(p, 10, 5, 15, 'north')
    for x in (8, 12):
        for z in (16, 17):
            p.put(x, 6, z, 'mcwfences:oak_picket_fence', priority=70, waterlogged=False)
    for x in range(9, 12):
        p.put(x, 6, 17, 'mcwfences:oak_picket_fence', priority=70, waterlogged=False)
    for x in (8, 12):
        p.put(x, 4, 16, 'minecraft:oak_stairs', priority=65,
              facing='north', half='top', shape='straight', waterlogged=False)
    lamp(p, 12, 4, 16, 'south')
    stair(p, 11, 12, 1, 'couple')
    # Kitchen occupies the lower side wing; hearth and real food preparation.
    for x in range(14, 18):
        p.put(x, 2, 10, 'farmersdelight:birch_cabinet', priority=80, facing='south', open=False)
    p.put(16, 2, 10, 'farmersdelight:stove', priority=82, facing='south', lit=True)
    p.put(15, 3, 10, 'farmersdelight:cutting_board', priority=82)
    p.stock(17, 2, 13, 'Rose & Lantern pantry', ('minecraft:bread', 'minecraft:carrot', 'minecraft:apple'), 'west')
    p.put(15, 2, 13, 'handcrafted:oak_table', priority=80, color='none', shape='single', waterlogged=False)
    p.put(14, 2, 13, 'handcrafted:oak_chair', priority=80, facing='east', color='none', waterlogged=False)
    p.put(16, 2, 13, 'handcrafted:oak_chair', priority=80, facing='west', color='none', waterlogged=False)
    p.put(15, 3, 13, 'handcrafted:wood_plate', priority=82, facing='south', pieces=2, waterlogged=False)
    for z in (6, 7):
        p.put(5, 2, z, 'handcrafted:oak_couch', priority=80, facing='east', shape='single', color='green', waterlogged=False)
    p.put(6, 2, 9, 'handcrafted:oak_side_table', priority=80)
    p.put(6, 3, 9, 'handcrafted:stackable_book', priority=82, books=2, facing='east', seed=19)
    p.put(7, 2, 6, 'handcrafted:green_cushion', priority=80)
    # Two actual sleeping places, wardrobe, writing desk and small private chest.
    for x in (6, 7):
        for part, z in (('head', 6), ('foot', 7)):
            p.put(x, 6, z, 'handcrafted:oak_fancy_bed', priority=80,
                  facing='north', part=part, shape='single', color='pink', occupied=False)
    p.put(5, 6, 11, 'handcrafted:oak_desk', priority=80, facing='west', color='none', waterlogged=False)
    p.put(6, 6, 11, 'handcrafted:oak_chair', priority=80, facing='west', color='none', waterlogged=False)
    p.stock(5, 6, 12, 'A little corner for two', ('minecraft:book', 'minecraft:paper', 'minecraft:rose_bush'))
    lamp(p, 5, 8, 12, 'east')
    p.put(6, 4, 8, 'mcwlights:copper_small_chandelier', priority=82)
    p.lots.append({'id': 'couple', 'name': MAIN, 'door': [10, 1, 15],
                   'rooms': ['Hearth sitting room', 'Side-wing working kitchen', 'Couple bedroom and balcony']})
    room(p, MAIN, 0, 1, MAIN_GROUND, 'Hearth sitting room and lower kitchen wing')
    room(p, MAIN, 1, 5, MAIN_UPPER, 'Couple bedroom, writing corner and real balcony door')
    p.connections += [('couple', MAIN_GROUND, 1, (10, 15), (10, 8)),
                      ('couple-balcony', MAIN_UPPER, 5, (10, 15), (10, 8))]


def honey_oven(p):
    p.zone = BAKER
    floor_and_foundation(p, BAKER_GROUND, 0)
    framed_room(p, BAKER_GROUND, 0, 'minecraft:yellow_terracotta', 'minecraft:stripped_birch_log')
    loft = rectangle(30, 8, 36, 15)
    p.floor(loft, 4)
    roof(p, (28, 6, 38, 14), 'z', (0, 1, 2, 3, 3, 3, 3, 3, 2, 1, 0), 5,
         'mcwroofs:bricks_roof', 'minecraft:yellow_terracotta', 'minecraft:stripped_birch_log')
    roof(p, (29, 13, 37, 17), 'x', (0, 1, 2, 1, 0), 4,
         'mcwroofs:white_terracotta_roof', 'minecraft:yellow_terracotta', 'minecraft:stripped_birch_log')
    door(p, 29, 0, 12, 'east', 'oak')
    window(p, 29, 0, 9, 'west', 'oak')
    window(p, 32, 0, 7, 'north')
    window(p, 37, 0, 10, 'east')
    stair(p, 35, 14, 0, 'bakehouse')
    for x in (31, 32):
        p.put(x, 1, 8, 'farmersdelight:birch_cabinet', priority=80, facing='south', open=False)
    p.put(33, 1, 8, 'farmersdelight:stove', priority=80, facing='south', lit=True)
    p.put(31, 2, 8, 'farmersdelight:cutting_board', priority=82)
    p.put(32, 2, 8, 'handcrafted:terracotta_plate', priority=82, facing='south', pieces=3, waterlogged=False)
    p.stock(31, 1, 14, 'Honey Oven ingredients', ('minecraft:wheat', 'minecraft:honey_bottle', 'minecraft:bread'))
    p.put(31, 1, 11, 'handcrafted:birch_table', priority=80, color='none', shape='single', waterlogged=False)
    p.put(32, 1, 11, 'handcrafted:birch_chair', priority=80, facing='west', color='none', waterlogged=False)
    p.put(31, 5, 10, 'minecraft:white_bed', priority=80, facing='north', part='head', occupied=False)
    p.put(31, 5, 11, 'minecraft:white_bed', priority=80, facing='north', part='foot', occupied=False)
    lamp(p, 30, 3, 13, 'west')
    p.lots.append({'id': 'bakehouse', 'name': BAKER, 'door': [29, 0, 12],
                   'rooms': ['Small real kitchen and bread counter', 'Baker sleeping loft']})
    room(p, BAKER, 0, 0, BAKER_GROUND, 'Bread counter, ingredient chest and working stove')
    room(p, BAKER, 1, 4, loft, 'Small sleeping loft under the roof')
    p.connections += [('bakehouse', BAKER_GROUND, 0, (29, 12), (34, 10))]


def weaver(p):
    p.zone = WEAVER
    floor_and_foundation(p, WEAVER_GROUND, 0)
    framed_room(p, WEAVER_GROUND, 0, 'minecraft:white_terracotta', 'minecraft:stripped_spruce_log')
    roof(p, (6, 26, 14, 35), 'x', (0, 1, 2, 3, 3, 3, 3, 2, 1, 0), 4,
         'mcwroofs:dark_oak_roof', 'minecraft:white_terracotta', 'minecraft:stripped_spruce_log')
    roof(p, (13, 26, 18, 34), 'z', (0, 1, 2, 2, 1, 0), 3,
         'mcwroofs:green_terracotta_roof', 'minecraft:white_terracotta', 'minecraft:stripped_spruce_log')
    door(p, 11, 0, 27, 'south', 'oak')
    window(p, 8, 0, 27, 'north', 'oak')
    window(p, 14, 0, 27, 'north')
    window(p, 7, 0, 30, 'west', 'oak')
    p.put(8, 1, 32, 'minecraft:loom', priority=80, facing='north')
    p.put(9, 1, 32, 'handcrafted:spruce_table', priority=80, color='none', shape='single', waterlogged=False)
    p.put(10, 1, 32, 'handcrafted:spruce_chair', priority=80, facing='west', color='none', waterlogged=False)
    p.stock(15, 1, 32, 'Mallow & Thread dyes', ('minecraft:pink_dye', 'minecraft:string', 'minecraft:white_wool'))
    p.put(15, 1, 29, 'minecraft:pink_bed', priority=80, facing='south', part='head', occupied=False)
    p.put(15, 1, 30, 'minecraft:pink_bed', priority=80, facing='south', part='foot', occupied=False)
    lamp(p, 12, 3, 28, 'north')
    p.lots.append({'id': 'weaver', 'name': WEAVER, 'door': [11, 0, 27],
                   'rooms': ['Small loom workshop and cottage sleeping nook']})
    room(p, WEAVER, 0, 0, WEAVER_GROUND, 'Real loom, dye chest and warm sleeping nook')
    p.connections += [('weaver', WEAVER_GROUND, 0, (11, 27), (11, 31))]


def glasshouse(p):
    p.zone = GLASS
    cells = rectangle(31, 27, 37, 34)
    floor_and_foundation(p, cells, 0)
    for x, z in cells:
        if (x, z) not in edge(cells):
            continue
        for y in (1, 2, 3):
            front = z in (27, 34)
            key = 'mcwwindows:birch_window2' if front else 'mcwwindows:oak_window2'
            stile = x in (31, 34, 37) if front else z in (27, 30, 34)
            if stile:
                p.put(x, y, z, 'minecraft:stripped_birch_log', priority=50, axis='y')
            else:
                p.put(x, y, z, key, priority=50,
                      facing='north' if z == 27 else 'south' if z == 34 else 'west' if x == 31 else 'east',
                      windowstate='closed')
    # Glazed leaded roof bays are separated by actual rafters, not random pixels.
    for x in range(30, 39):
        for z in range(26, 36):
            y = 4+min(x-30, 38-x, 3)
            key = 'chipped:clear_leaded_glass'
            if z in (26, 30, 35):
                key = 'minecraft:birch_planks'
            elif x in (30, 34, 38):
                key = 'minecraft:stripped_oak_wood'
            p.put(x, y, z, key, priority=55, **({'axis': 'z'} if key.endswith('_wood') else {}))
    door(p, 34, 0, 27, 'south', 'birch')
    for x in (32, 36):
        for z in range(29, 33):
            p.put(x, 1, z, 'supplementaries:planter', priority=75, extended=False, waterlogged=False)
            p.put(x, 2, z, 'minecraft:fern' if z % 2 else 'minecraft:allium', priority=80)
    p.stock(35, 1, 33, 'Rosemary Glasshouse seeds', ('minecraft:wheat_seeds', 'minecraft:torchflower_seeds', 'minecraft:bone_meal'))
    p.lots.append({'id': 'glasshouse', 'name': GLASS, 'door': [34, 0, 27],
                   'rooms': ['Working seed storage, potting benches and intimate greenhouse']})
    room(p, GLASS, 0, 0, cells, 'Seed chest and planted potting benches')
    p.connections += [('glasshouse', cells, 0, (34, 27), (34, 32))]


def path(p, label, points, floor=0, width=2):
    cells = set()
    authored_rooms = MAIN_GROUND | BAKER_GROUND | WEAVER_GROUND | rectangle(31, 27, 37, 34)
    for (ax, az), (bx, bz) in zip(points, points[1:]):
        n = max(abs(bx-ax), abs(bz-az))
        side = (0, 1) if abs(bx-ax) >= abs(bz-az) else (1, 0)
        for i in range(n+1):
            x, z = round(ax+(bx-ax)*i/max(n, 1)), round(az+(bz-az)*i/max(n, 1))
            for offset in range(width):
                xx, zz = x+side[0]*offset, z+side[1]*offset
                # Broad garden approaches meet real one-wide cottage doors;
                # they must not carve a second doorway through the facade.
                if (xx, zz) in authored_rooms and any(
                    p.blocks.get((xx, floor+dy, zz), 'minecraft:air').split('[', 1)[0]
                    not in ('minecraft:air', 'mcwdoors:oak_cottage_door', 'mcwdoors:birch_cottage_door') for dy in (1, 2)):
                    continue
                cells.add((xx, zz))
                p.put(xx, floor-1, zz, 'minecraft:stone', priority=10)
                p.put(xx, floor, zz, 'minecraft:gravel' if zz % 8 else 'minecraft:andesite', priority=15)
                for dy in (1, 2):
                    if not p.blocks.get((xx, floor+dy, zz), '').startswith('mcwdoors:'):
                        p.put(xx, floor+dy, zz, 'minecraft:air', priority=90)
    p.walk(label, sorted(cells), floor)


def garden(p):
    p.zone = 'Shared cottage court and garden'
    path(p, 'west-garden-entry', [(0, 20), (10, 20), (16, 18), (24, 19), (29, 22), (34, 24)])
    path(p, 'bakehouse-approach', [(24, 19), (26, 15), (28, 12), (29, 12)])
    path(p, 'weaver-approach', [(16, 18), (16, 23), (11, 25), (11, 27)])
    path(p, 'glasshouse-approach', [(29, 22), (34, 24), (34, 27)])
    path(p, 'couple-approach', [(10, 20), (10, 16)])
    p.put(10, 1, 16, 'minecraft:stone_brick_stairs', priority=95,
          facing='north', half='bottom', shape='straight', waterlogged=False)
    p.navigation.discard((10, 1, 16))
    p.navigation.discard((11, 1, 16))
    p.put(11, 1, 16, 'minecraft:stone_brick_stairs', priority=95,
          facing='north', half='bottom', shape='straight', waterlogged=False)
    p.walk('couple-stoop', [(10, 16), (10, 15)], 1)
    # Intimate pond in an authored irregular outline, never a broad square pool.
    pond = layer((20, 23, 24, 26), (21, 22, 23, 27), remove=((20, 23), (24, 26)))
    for x, z in pond:
        p.put(x, -2, z, 'minecraft:clay', priority=45)
        p.put(x, -1, z, 'minecraft:water', priority=45, level=0)
        p.put(x, 0, z, 'minecraft:air', priority=45)
    for x, z in edge(pond):
        for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            xx, zz = x+dx, z+dz
            if (xx, zz) not in pond:
                p.put(xx, -1, zz, 'minecraft:stone_bricks', priority=46)
    # Small two-wide garden bridge. It is not the separate commissioned drawbridge.
    for x in range(18, 27):
        for z in (24, 25):
            p.put(x, 0, z, 'minecraft:oak_planks', priority=65)
        for z in (23, 26):
            p.put(x, 1, z, 'mcwfences:oak_picket_fence', priority=65, waterlogged=False)
    p.walk('pond-footbridge', [(x, z) for x in range(18, 27) for z in (24, 25)])
    # Shared outdoor kitchen and two actual seats; no expensive ambient entities.
    for x in range(21, 25):
        for z in range(15, 18):
            p.put(x, 0, z, 'minecraft:stone_bricks', priority=35)
    p.put(22, 1, 16, 'farmersdelight:stove', priority=80, facing='south', lit=True)
    p.put(23, 1, 16, 'farmersdelight:birch_cabinet', priority=80, facing='south', open=False)
    p.put(23, 2, 16, 'farmersdelight:cutting_board', priority=82)
    for x, z, face in ((19, 30, 'north'), (21, 30, 'north')):
        p.put(x, 1, z, 'handcrafted:oak_bench', priority=80,
              facing=face, color='none', shape='single', waterlogged=False)
    p.put(20, 1, 30, 'handcrafted:oak_side_table', priority=80)
    p.put(20, 2, 30, 'handcrafted:terracotta_plate', priority=82,
          facing='north', pieces=2, waterlogged=False)
    # Connected low garden boundaries, with deliberate gaps at the walking entries.
    for start, end in (((1, 1, 24), (8, 1, 24)), ((1, 1, 24), (1, 1, 32)),
                       ((22, 1, 34), (29, 1, 34)), ((39, 1, 25), (39, 1, 33))):
        p.line(start, end, 'minecraft:mossy_stone_brick_wall', priority=45, up=True, waterlogged=False)
    for x, z, flower in ((3, 22, 'minecraft:rose_bush'), (7, 23, 'minecraft:lilac'),
                         (18, 31, 'minecraft:peony'), (25, 31, 'minecraft:rose_bush'),
                         (30, 25, 'minecraft:peony'), (38, 28, 'minecraft:lilac')):
        p.put(x, 0, z, 'minecraft:grass_block', priority=40)
        for dy, half in ((1, 'lower'), (2, 'upper')):
            p.put(x, dy, z, flower, priority=75, half=half)
    for x, z in ((2, 18), (18, 19), (27, 29), (38, 24)):
        p.put(x, 1, z, 'mcwlights:covered_garden_light', priority=75, lit=True, powered=False)
    # A small orchard crown frames a view instead of masking the buildings.
    for x, z in ((3, 31), (25, 6)):
        p.line((x, 1, z), (x, 4, z), 'minecraft:cherry_log', priority=60, axis='y')
        for dx in range(-2, 3):
            for dz in range(-2, 3):
                if abs(dx)+abs(dz) <= 3:
                    p.put(x+dx, 5, z+dz, 'minecraft:cherry_leaves', priority=60,
                          persistent=True, distance=1, waterlogged=False)
        p.put(x, 6, z, 'minecraft:cherry_leaves', priority=60,
              persistent=True, distance=1, waterlogged=False)
    p.details += ['Two-place balcony', 'Real two-bed bedroom', 'Working side-wing kitchen',
                  'Pond and two-wide footbridge', 'Three winding approaches', 'Private tea bench',
                  'Two small orchard trees', 'Glazed potting house', 'Useful bread oven and loom']


def connections(p):
    for label, cells, floor, start, goal in p.connections:
        def passable(cell):
            return cell in cells and all(p.blocks.get((cell[0], floor+dy, cell[1]), 'minecraft:air')
                .split('[', 1)[0] in ('minecraft:air', 'mcwdoors:oak_cottage_door', 'mcwdoors:birch_cottage_door')
                for dy in (1, 2))
        queue, prev = deque([start]), {start: None}
        while queue and goal not in prev:
            x, z = queue.popleft()
            for cell in ((x-1, z), (x+1, z), (x, z-1), (x, z+1)):
                if cell not in prev and passable(cell):
                    prev[cell] = x, z
                    queue.append(cell)
        if goal not in prev:
            raise UserError('Cottage circulation has no planned clear connection: '+label)
        route, cell = [], goal
        while cell is not None:
            route.append(cell)
            cell = prev[cell]
        p.walk(label+'-room-connection', route[::-1], floor)


def check(p):
    materials = [require_material_rule({pos: state for pos, state in p.blocks.items()
                 if p.owners[pos] == name}, name) for name in BUILDINGS]
    blocked = []
    for x, y, z in sorted(p.navigation):
        for dy in (0, 1):
            state = p.blocks.get((x, y+dy, z), 'minecraft:air')
            if state.split('[', 1)[0] not in ('minecraft:air', 'mcwdoors:oak_cottage_door', 'mcwdoors:birch_cottage_door'):
                blocked.append({'local': [x, y+dy, z], 'state': state})
    if blocked:
        raise UserError('Cottage planned walking route obstructed: '+str(blocked[:12]))
    for lot in p.lots:
        x, floor, z = lot['door']
        if not all(p.blocks.get((x, floor+dy, z), '').startswith('mcwdoors:') for dy in (1, 2)):
            raise UserError('Authored cottage door was overwritten: '+lot['name'])
    return {'materials': materials, 'reserved_body_cells': len(p.navigation), 'blocked': [],
            'scope': 'Authored source and two-cell planned clearance; no native walking or appearance acceptance.'}


def construct(registry, survey, origin=ORIGIN):
    p = CottagePlan(registry, origin)
    terrain_samples(p, survey)
    couple_cottage(p)
    honey_oven(p)
    weaver(p)
    glasshouse(p)
    garden(p)
    connections(p)
    p.captures = [{'id': 'cottage-court-entry', 'feet': [1, 1, 20.5], 'look_at': [18, 5, 16]},
                  {'id': 'couple-frontage', 'feet': [14, 1, 21], 'look_at': [10, 6, 12]},
                  {'id': 'pond-and-oven', 'feet': [25, 1, 29], 'look_at': [24, 4, 17]},
                  {'id': 'glazed-garden', 'feet': [28, 1, 23], 'look_at': [34, 4, 29]},
                  {'id': 'couple-interior', 'feet': [8, 2, 12], 'look_at': [15, 3, 12]},
                  {'id': 'court-silhouette', 'feet': [22, 19, 39], 'look_at': [20, 5, 18]}]
    return p


def prepare(home, registry_path, survey_path, destination, backup_sha256, origin=ORIGIN):
    home, destination = Path(home).resolve(), Path(destination).resolve()
    if home.drive.upper() != 'D:' or not destination.is_relative_to(home/'staging') or destination.exists():
        raise UserError('Use a NEW bounded private D: staging folder')
    if not re.fullmatch('[0-9a-f]{64}', backup_sha256):
        raise UserError('The actual verified staging backup SHA-256 is required')
    if Path(registry_path).stat().st_size > 8*MIB or Path(survey_path).stat().st_size > 8*MIB:
        raise UserError('Native cottage input exceeds its finite read bound')
    registry = json.loads(Path(registry_path).read_text(encoding='utf-8'))
    survey = json.loads(Path(survey_path).read_text(encoding='utf-8'))
    if not Path(registry['world_path']).resolve().is_relative_to(home/'staging'):
        raise UserError('Private staging registry required; official world refused')
    guard = subprocess.run(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(GUARD),
        '-EstimatedCBytes', '0', '-EstimatedDBytes', str(MAX_BUNDLE)], capture_output=True, text=True,
        creationflags=subprocess.CREATE_NO_WINDOW, check=False)
    reserve = json.loads(guard.stdout)
    if guard.returncode or not reserve.get('allowed'):
        raise UserError('Reserve guard refused this finite cottage bundle')
    p = construct(registry, survey, origin)
    checks = check(p)
    native = p.serialize(backup_sha256)
    data = (json.dumps(native, ensure_ascii=False, separators=(',', ':'))+'\n').encode()
    sha = hashlib.sha256(data).hexdigest()
    ox, oy, oz = origin
    manifest = {'format': 'awft-artistic-cottage-court:1', 'created': utcnow(), 'prototype_only': True,
        'source_sha256': digest(Path(__file__)), 'registry_sha256': digest(Path(registry_path)),
        'original_native_survey_sha256': digest(Path(survey_path)), 'reviewed_staging_backup_sha256': backup_sha256,
        'plan_sha256': sha, 'origin': list(origin), 'placements': len(p.blocks), 'block_entities': len(p.tags),
        'entity_commands': 0, 'rooms': p.rooms, 'lots': p.lots, 'details': p.details,
        'routes': p.routes, 'planned_checks': checks,
        'native_capture_positions': [row|{'world_feet': [ox+row['feet'][0], oy+row['feet'][1], oz+row['feet'][2]],
            'world_look_at': [ox+row['look_at'][0], oy+row['look_at'][1], oz+row['look_at'][2]]} for row in p.captures],
        'mods_used': {key: sorted(value) for key, value in p.uses.items()},
        'storage_guard': reserve, 'technical_status': 'Source only; fine terrain, native placement and walking pending',
        'visual_status': 'UNVERIFIED: real screenshots and artistic iteration required', 'owner_acceptance': 'not inferred'}
    rendered = (json.dumps(manifest, sort_keys=True, indent=2)+'\n').encode()
    if len(data)+len(rendered) > MAX_BUNDLE:
        raise UserError('Cottage bundle exceeded finite allocation')
    destination.mkdir(parents=True, exist_ok=False)
    path = destination/('rose-lantern-court-'+sha[:16]+'.json')
    path.write_bytes(data)
    (destination/'manifest.json').write_bytes(rendered)
    return {'plan': str(path), 'sha256': sha, 'placements': len(p.blocks), 'native_visual_review': 'pending'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--home', type=Path, default=Path(r'D:\A World for Two'))
    parser.add_argument('--registry', type=Path, required=True)
    parser.add_argument('--survey', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--backup-sha256', required=True)
    parser.add_argument('--origin', type=int, nargs=3, default=ORIGIN)
    args = parser.parse_args()
    print(json.dumps(prepare(args.home, args.registry, args.survey, args.output,
                             args.backup_sha256, tuple(args.origin)), indent=2))
