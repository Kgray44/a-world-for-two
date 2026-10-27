"""Original Lanternwater pirate-port architecture; expands the existing real settlement.

All IDs/properties come from the installed native registry. No downloaded schematic,
film asset, permanent chunk loader, hostile mob or explosive is used. A completed
core block is an exclusion, including its air clearance and existing inventories.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from control_room.common import Layout, UserError, digest, read_json, write_json, utcnow
from control_room.storage import Storage
from tools.settlement import Plan, beds, furniture


class PortPlan(Plan):
    def __init__(self, registry, survey, center, backup, core, rotation=2):
        super().__init__(registry, survey, center, backup, rotation)
        self.fixed = {(x, y, z): core['palette'][i] for x, y, z, i in core['blocks']}
        self.lots = []
        self.zone = 'Lanternwater pirate quarter'

    def put(self, x, y, z, key, **properties):
        wx, wz = self.world(x, z)
        position = wx, y, wz
        if position in self.fixed:
            if self.state(key, **properties) == self.fixed[position]:
                return
            raise UserError('The pirate expansion intersects completed core construction: ' + str(position))
        if position in self.protected:
            raise UserError('The pirate expansion intersects an existing block entity: ' + str(position))
        return super().put(x, y, z, key, **properties)

    def quay_put(self, x, y, z, key, **properties):
        """A connecting boardwalk yields to the original pier; buildings never do."""
        wx, wz = self.world(x, z)
        if (wx, y, wz) in self.fixed:
            return
        self.put(x, y, z, key, **properties)

    def pile_deck(self, x, z, w, d, floor):
        # Sparse timber piles rather than filling the estuary with a solid foundation.
        for px in range(x, x + w):
            for pz in range(z, z + d):
                self.put(px, floor, pz, 'minecraft:spruce_planks')
        for px in sorted({x, x+w-1, x+w//2}):
            for pz in sorted({z, z+d-1, z+d//2}):
                self.box(px, floor-13, pz, px, floor-1, pz, 'minecraft:stripped_dark_oak_log', axis='y')
        for pz in (z, z+d-1):
            self.box(x, floor-1, pz, x+w-1, floor-1, pz, 'minecraft:dark_oak_log', axis='x')
        self.lots.append({'name': self.zone, 'local_bounds': [x, z, x+w-1, z+d-1], 'floor': floor})


def wall_window(p, x, y, z, facing, shutters=True):
    for dy in (0, 1):
        p.put(x, y+dy, z, 'mcwwindows:dark_oak_pane_window', facing=facing,
              part='base' if dy == 0 else 'above', windowstate='closed')
    if facing in ('north', 'south'):
        for dx, hinge in ((-1, 'left'), (1, 'right')):
            if shutters:
                p.put(x+dx, y, z, 'mcwwindows:spruce_louvered_shutter', facing=facing, hinge=hinge, open=True)
        outer = z + (1 if facing == 'south' else -1)
        p.put(x, y-1, outer, 'minecraft:spruce_trapdoor', facing=facing, half='top', open=False, waterlogged=False)
        p.put(x, y, outer, 'minecraft:potted_fern')


def gable(p, x, z, w, d, base, material='mcwroofs:dark_oak_roof'):
    half = (w+1)//2
    for n in range(half+1):
        for px, facing in ((x-1+n, 'east'), (x+w-n, 'west')):
            p.box(px, base+n, z-1, px, base+n, z+d, material,
                  facing=facing, half='bottom', shape='straight')
            if n:
                for pz in (z, z+d-1):
                    p.box(px, base, pz, px, base+n-1, pz, 'minecraft:dark_oak_planks')
    ridge = x+w//2
    p.box(ridge, base+half, z-1, ridge, base+half, z+d, 'minecraft:dark_oak_slab', type='bottom', waterlogged=False)


def port_house(p, name, x, z, w, d, *, floor=66, stories=2,
               plaster='minecraft:white_terracotta', roof='mcwroofs:dark_oak_roof', balcony=True):
    p.landmark(name, x+w//2, floor+1, z+d+1, 'Pirate port',
               ['Original pirate-port architecture', 'Furnished rooms', 'Covered waterfront entrance'])
    p.pile_deck(x, z, w, d, floor)
    h = 5*stories
    p.box(x, floor+1, z, x+w-1, floor+h+w//2+3, z+d-1, 'minecraft:air')
    for dy in range(1, h+1):
        for px in range(w):
            for pz in (0, d-1):
                beam = px in (0, w-1) or px % 6 == 0 or dy % 5 == 0
                # Coherent salt-weathered masonry only at the foundation corners.
                block = 'minecraft:stripped_dark_oak_log' if beam else plaster
                if dy == 1 and min(px, w-1-px) < 3 and not beam:
                    block = 'minecraft:mossy_stone_bricks'
                p.put(x+px, floor+dy, z+pz, block, axis='x' if dy % 5 == 0 else 'y')
        for pz in range(1, d-1):
            for px in (0, w-1):
                beam = pz % 6 == 0 or dy % 5 == 0
                p.put(x+px, floor+dy, z+pz, 'minecraft:stripped_dark_oak_log' if beam else plaster,
                      axis='z' if dy % 5 == 0 else 'y')
    for story in range(stories):
        sy = floor+story*5
        if story:
            p.box(x+1, sy, z+1, x+w-2, sy, z+d-2, 'chipped:boxed_spruce_planks')
        for px in range(3, w-2, 6):
            for pz, facing in ((z, 'north'), (z+d-1, 'south')):
                wall_window(p, x+px, sy+2, pz, facing)
        for pz in range(3, d-2, 6):
            for px, facing in ((x, 'west'), (x+w-1, 'east')):
                wall_window(p, px, sy+2, z+pz, facing, shutters=False)
        for px in range(x+3, x+w-2, 6):
            p.box(px, sy+4, z+1, px, sy+4, z+d-2, 'minecraft:dark_oak_log', axis='z')
        for pz in (z+4, z+d-5):
            p.put(x+w//2, sy+4, pz, 'minecraft:lantern', hanging=True, waterlogged=False)
    p.box(x+1, floor+h, z+1, x+w-2, floor+h, z+d-2, 'minecraft:spruce_planks')
    gable(p, x, z, w, d, floor+h+1, roof)
    # Stone chimney breaks the roof silhouette and is grounded inside the house.
    p.box(x+2, floor+1, z+2, x+3, floor+h+5, z+3, 'minecraft:bricks')
    p.box(x+2, floor+h+6, z+2, x+3, floor+h+6, z+3, 'minecraft:brick_slab', type='bottom', waterlogged=False)
    door = x+w//2
    for dx in (0, 1):
        for half, dy in (('lower', 1), ('upper', 2)):
            p.put(door+dx, floor+dy, z+d-1, 'mcwdoors:dark_oak_western_door',
                  facing='south', half=half, hinge='left' if dx == 0 else 'right', open=False, powered=False)
    # Covered entrance/upper balcony, with visible brackets and a water-facing rail.
    p.pile_deck(x+1, z+d, w-2, 4, floor)
    for px in (x+1, x+w-2):
        p.box(px, floor+1, z+d+3, px, floor+4, z+d+3, 'minecraft:dark_oak_fence')
        p.put(px+(-1 if px == x+1 else 1), floor+3, z+d+3,
              'mcwlights:tavern_wall_lantern', facing='west' if px == x+1 else 'east')
    p.box(x+1, floor+5, z+d, x+w-2, floor+5, z+d+3, 'minecraft:spruce_slab', type='top', waterlogged=False)
    if stories > 1 and balcony:
        for px in range(x+1, x+w-1):
            p.put(px, floor+6, z+d+3, 'mcwfences:dark_oak_horse_fence')
        for pz in range(z+d, z+d+3):
            for px in (x+1, x+w-2):
                p.put(px, floor+6, pz, 'mcwfences:dark_oak_horse_fence')
        p.box(door, floor+6, z+d-1, door, floor+7, z+d-1, 'minecraft:air')
        p.put(x+3, floor+6, z+d+1, 'handcrafted:dark_oak_chair', facing='south')
        p.put(x+4, floor+6, z+d+1, 'handcrafted:dark_oak_side_table')
        p.put(x+4, floor+7, z+d+1, 'minecraft:potted_red_tulip')
    if stories > 1:
        for n in range(5):
            p.put(x+w-3, floor+1+n, z+3+n, 'minecraft:dark_oak_stairs',
                  facing='south', half='bottom', shape='straight', waterlogged=False)
            p.box(x+w-3, floor+2+n, z+3+n, x+w-3, floor+4+n, z+3+n, 'minecraft:air')
        p.put(x+w-3, floor+5, z+8, 'minecraft:spruce_planks')
    p.sign(door-3, floor+1, z+d+1, [name, 'Lanternwater', 'A harbor for wanderers'])
    for px in (door, door+1):
        p.put(px, floor-1, z+d+4, 'minecraft:dark_oak_stairs',
              facing='north', half='bottom', shape='straight', waterlogged=False)
    return floor


def seating(p, x, y, z, color='brown'):
    p.put(x, y, z, 'handcrafted:dark_oak_table', color=color)
    p.put(x+1, y, z, 'handcrafted:dark_oak_table', color=color)
    for px in (x, x+1):
        for pz, facing in ((z-1, 'south'), (z+1, 'north')):
            p.put(px, y, pz, 'handcrafted:dark_oak_chair', facing=facing)
    p.put(x, y+1, z, 'minecraft:flower_pot')


def tavern(p):
    x, z, w, d, y = -56, 35, 25, 23, 66
    port_house(p, 'The Crooked Compass', x, z, w, d, floor=y,
               plaster='minecraft:yellow_terracotta')
    # A low side kitchen and terrace interrupt the main block, rather than another box.
    p.zone = 'The Crooked Compass'
    p.pile_deck(x-10, z+5, 10, 14, y)
    p.box(x-10, y+1, z+5, x-1, y+7, z+18, 'minecraft:air')
    for px in range(x-10, x):
        for pz in (z+5, z+18):
            p.box(px, y+1, pz, px, y+4, pz, 'minecraft:dark_oak_planks')
    for pz in range(z+5, z+19):
        p.box(x-10, y+1, pz, x-10, y+4, pz, 'minecraft:dark_oak_planks')
    for n in range(11):
        p.box(x-10+n, y+5+n//4, z+4, x-10+n, y+5+n//4, z+19,
              'minecraft:spruce_slab', type='bottom', waterlogged=False)
    p.box(x, y+1, z+11, x, y+3, z+13, 'minecraft:air')
    for px in range(x-8, x-1):
        p.put(px, y+1, z+7, 'farmersdelight:spruce_cabinet', facing='south')
    p.put(x-7, y+1, z+7, 'farmersdelight:stove', facing='south', lit=True)
    p.put(x-7, y+2, z+7, 'farmersdelight:cooking_pot', facing='south')
    p.put(x-4, y+2, z+7, 'farmersdelight:cutting_board')
    p.chest(x-8, y+1, z+15, 'The galley pantry', ['farmersdelight:iron_knife', 'minecraft:potato', 'minecraft:cod'])
    for px in range(x+3, x+13):
        p.put(px, y+1, z+5, 'handcrafted:dark_oak_counter', facing='south')
        if px % 2:
            p.put(px, y+1, z+7, 'mcwfurnitures:dark_oak_stool_chair')
    for px in (x+5, x+8, x+11):
        p.put(px, y+2, z+5, 'supplementaries:jar', facing='south')
        p.put(px, y+1, z+2, 'vinery:dark_oak_wine_rack_big', facing='south')
    p.put(x+15, y+1, z+3, 'xercamusic:piano', facing='south')
    p.put(x+15, y+1, z+5, 'handcrafted:dark_oak_bench', facing='north')
    for px, pz in ((x+4, z+13), (x+13, z+13), (x+7, z+19)):
        seating(p, px, y+1, pz)
    for pz in range(z+8, z+21):
        p.put(x+18, y+1, pz, 'minecraft:red_carpet')
    # Three modest upstairs guest rooms, a common reading area and open circulation.
    for px in (x+8, x+16):
        p.box(px, y+6, z+1, px, y+9, z+11, 'minecraft:spruce_planks')
        p.box(px, y+6, z+9, px, y+7, z+9, 'minecraft:air')
    for px, color in ((x+4, 'red'), (x+12, 'blue'), (x+20, 'green')):
        beds(p, px, y+6, z+7, color)
        p.put(px+1, y+6, z+6, 'handcrafted:dark_oak_nightstand')
        p.put(px+1, y+7, z+6, 'minecraft:candle', candles=1, lit=True, waterlogged=False)
    p.put(x+4, y+6, z+15, 'handcrafted:dark_oak_couch', facing='south')
    p.put(x+6, y+6, z+15, 'handcrafted:dark_oak_couch', facing='south')
    p.put(x+4, y+6, z+13, 'supplementaries:book_pile')
    p.put(x+11, y+6, z+16, 'minecraft:jukebox')
    p.chest(x+12, y+6, z+16, 'An evening in port', ['minecraft:music_disc_cat', 'minecraft:book', 'minecraft:feather'])
    p.put(x+w//2, y+8, z+d+4, 'treasure2:skull_and_crossbones', facing='south', waterlogged=False)


def chandlery(p):
    x, z, y = -98, 29, 65
    port_house(p, 'Bramble and Brine Chandlery', x, z, 19, 19, floor=y,
               stories=1, plaster='minecraft:light_gray_terracotta')
    p.zone = 'Bramble and Brine Chandlery'
    for px in range(x+3, x+14):
        p.put(px, y+1, z+4, 'handcrafted:dark_oak_counter', facing='south')
    for px in (x+3, x+7, x+11):
        p.put(px, y+2, z+4, 'minecraft:lantern', hanging=False, waterlogged=False)
    for px in (x+3, x+6, x+9, x+12):
        p.put(px, y+1, z+8, 'chipped:spruce_crate')
        p.put(px, y+2, z+8, 'supplementaries:sack', open=False, waterlogged=False)
    p.chest(x+3, y+1, z+13, 'Ropes, rigging and repairs', ['supplementaries:rope', 'minecraft:lead', 'minecraft:lantern', 'minecraft:white_wool'])
    p.chest(x+10, y+1, z+13, 'Dress for a sea voyage', tuple(k for k in p.registry['items']
            if k.startswith(('lfpirates:', 'treasures_of_the_dead:', 'pirateguns:'))
            and any(w in k for w in ('hat', 'cutlass', 'coat', 'flintlock')))[:12])
    p.put(x+12, y+2, z+4, 'lfpirates:ship_in_bottle', facing='south', waterlogged=False)


def shipwright(p):
    x, z, y = -118, 63, 65
    port_house(p, 'Old Salt Shipwrights', x, z, 29, 19, floor=y, stories=1,
               plaster='minecraft:dark_oak_planks', roof='mcwroofs:spruce_roof')
    p.zone = 'Old Salt Shipwrights'
    p.box(x+10, y+1, z+18, x+18, y+4, z+18, 'minecraft:air')
    for px in range(x+3, x+12):
        p.put(px, y+1, z+4, 'handcrafted:dark_oak_desk', facing='south')
    for px, block in ((x+15, 'minecraft:stonecutter'), (x+18, 'minecraft:smithing_table'),
                      (x+21, 'minecraft:anvil')):
        p.put(px, y+1, z+4, block, facing='south')
    p.put(x+4, y+1, z+12, 'smallships:dockyard', facing='south')
    p.chest(x+5, y+1, z+12, 'The shipwright\'s starter kit', ['smallships:spruce_cog', 'smallships:dark_oak_galleon', 'minecraft:oak_boat'])
    # An unfinished clinker hull in a dry cradle is scenic architecture, not a ship entity.
    for n in range(13):
        radius = max(1, min(3, n, 12-n))
        p.put(x+16, y+1, z+9+n//2, 'minecraft:dark_oak_log', axis='z')
        for dx in (-radius, radius):
            p.put(x+16+dx, y+2, z+9+n//2, 'minecraft:spruce_stairs',
                  facing='east' if dx < 0 else 'west', half='bottom', shape='straight', waterlogged=False)
    for px in (x+4, x+8):
        p.box(px, y+1, z+7, px, y+3, z+7, 'chipped:dark_oak_crate')


def warehouse_and_loft(p):
    x, z, y = -57, 95, 65
    port_house(p, 'The Tidebond Warehouse', x, z, 25, 19, floor=y,
               plaster='minecraft:bricks', roof='mcwroofs:spruce_roof')
    p.zone = 'The Tidebond Warehouse'
    for px in (x+4, x+8, x+17, x+20):
        for pz in (z+5, z+10, z+14):
            p.put(px, y+1, pz, 'rechiseled:dark_oak_planks_crate')
            if pz == z+5:
                p.put(px, y+2, pz, 'chipped:spruce_barrel', facing='up', open=False)
    p.chest(x+3, y+1, z+16, 'Harbor cargo manifest', ['minecraft:paper', 'minecraft:compass', 'minecraft:book'])
    for px in (x+4, x+10, x+16):
        p.put(px, y+6, z+4, 'handcrafted:dark_oak_cupboard', facing='south', type=1)
    p.put(x+12, y+6, z+13, 'handcrafted:dark_oak_desk', facing='north')
    p.put(x+12, y+7, z+13, 'supplementaries:book_pile')
    # The crane is deliberately static, unloaded and decorative until commissioned.
    cx, cz = -66, 112
    p.box(cx, y-10, cz, cx, y+12, cz, 'minecraft:dark_oak_log', axis='y')
    p.box(cx, y+12, cz, cx+10, y+12, cz, 'minecraft:dark_oak_log', axis='x')
    p.box(cx+9, y+6, cz, cx+9, y+11, cz, 'minecraft:chain', axis='y', waterlogged=False)
    p.put(cx+9, y+5, cz, 'chipped:spruce_crate')
    x, z = -96, 94
    port_house(p, 'Needle and North Sail Loft', x, z, 19, 17, floor=y,
               plaster='minecraft:light_blue_terracotta', roof='mcwroofs:dark_oak_roof')
    p.zone = 'Needle and North Sail Loft'
    p.box(x+3, y+1, z+3, x+10, y+1, z+6, 'handcrafted:dark_oak_table')
    for px in (x+3, x+7, x+11):
        p.put(px, y+1, z+10, 'minecraft:loom', facing='south')
    p.chest(x+3, y+1, z+13, 'Canvas, colors and quiet work', ['minecraft:white_wool', 'minecraft:blue_dye', 'minecraft:string', 'minecraft:shears'])
    for px in range(x+3, x+13):
        for pz in range(z+4, z+9):
            p.put(px, y+6, pz, 'minecraft:white_carpet')
    beds(p, x+5, y+6, z+13, 'cyan')
    p.put(x+8, y+6, z+12, 'handcrafted:dark_oak_nightstand')


def captains_and_cottages(p):
    x, z, y = 24, 37, 67
    port_house(p, 'The Captains\' Chart House', x, z, 23, 23, floor=y,
               plaster='minecraft:white_terracotta', roof='mcwroofs:dark_oak_roof')
    p.zone = 'The Captains\' Chart House'
    p.box(x+4, y+1, z+8, x+12, y+1, z+11, 'handcrafted:dark_oak_table', color='blue')
    p.put(x+8, y+2, z+9, 'supplementaries:globe', facing='south', powered=False, rotation=0, waterlogged=False)
    p.put(x+11, y+2, z+9, 'lfpirates:ship_in_bottle', facing='south', waterlogged=False)
    for pz in range(z+5, z+17):
        p.put(x+1, y+1, pz, 'minecraft:bookshelf')
    for px in (x+5, x+11):
        p.put(px, y+1, z+15, 'handcrafted:dark_oak_desk', facing='north')
        p.put(px, y+1, z+16, 'handcrafted:dark_oak_chair', facing='north')
    p.chest(x+4, y+1, z+18, 'For KG and Sera: the next horizon', ['minecraft:compass', 'minecraft:spyglass', 'minecraft:map', 'minecraft:book', 'minecraft:feather'])
    p.put(x+4, y+6, z+4, 'minecraft:cartography_table')
    p.put(x+7, y+6, z+4, 'treasures_of_the_dead:skull_merchant_table', facing='south')
    p.put(x+12, y+6, z+4, 'treasure2:pirate_chest', facing='south', discovered=True, waterlogged=False)
    beds(p, x+4, y+6, z+13, 'blue')
    p.put(x+5, y+6, z+12, 'handcrafted:dark_oak_nightstand')
    p.put(x+8, y+6, z+14, 'handcrafted:dark_oak_couch', facing='south')
    for name, px, pz, w, d, floor, wall in [
        ('The Sea Glass Rooms', 64, 29, 13, 17, 68, 'minecraft:cyan_terracotta'),
        ('The Copper Kettle', 83, 44, 15, 19, 68, 'minecraft:orange_terracotta'),
        ('The Netmender\'s House', 65, 72, 13, 17, 65, 'minecraft:white_terracotta'),
    ]:
        port_house(p, name, px, pz, w, d, floor=floor, stories=2, plaster=wall)
        p.zone = name
        seating(p, px+3, floor+1, pz+9, color='cyan' if 'Glass' in name else 'brown')
        p.put(px+3, floor+1, pz+4, 'farmersdelight:spruce_cabinet', facing='south')
        p.put(px+5, floor+1, pz+4, 'minecraft:smoker', facing='south', lit=False)
        beds(p, px+4, floor+6, pz+11, 'light_blue')
        p.put(px+5, floor+6, pz+10, 'handcrafted:dark_oak_nightstand')
        p.put(px+3, floor+6, pz+4, 'handcrafted:dark_oak_cupboard', facing='south', type=1)


def boardwalk(p, points, y=65, width=3):
    for (ax, az), (bx, bz) in zip(points, points[1:]):
        length = max(abs(bx-ax), abs(bz-az), 1)
        for n in range(length+1):
            x = round(ax+(bx-ax)*n/length)
            z = round(az+(bz-az)*n/length)
            for dx in range(-(width//2), width//2+1):
                for dz in range(-(width//2), width//2+1):
                    p.quay_put(x+dx, y, z+dz, 'minecraft:spruce_planks')
                    for dy in (1, 2, 3):
                        p.quay_put(x+dx, y+dy, z+dz, 'minecraft:air')
            if n % 9 == 0:
                for dx in (-width//2-1, width//2+1):
                    for py in range(y-12, y+1):
                        p.quay_put(x+dx, py, z, 'minecraft:dark_oak_log', axis='y')
    # Railings are placed only on the waterside quays, not across streets/doorways.


def street_life(p):
    p.zone = 'Lanternwater quays and market'
    # The original center pier is retained; these give it two distinct neighborhoods.
    for points in [
        [(-13, 24), (-21, 27), (-70, 27), (-108, 25)],
        [(-15, 64), (-37, 65), (-76, 57), (-110, 58)],
        [(-16, 88), (-38, 88), (-71, 88), (-119, 89)],
        [(-21, 120), (-60, 120), (-105, 120)],
        [(-74, 26), (-74, 57), (-74, 87), (-74, 120)],
        [(-22, 26), (-21, 64), (-20, 89), (-22, 120)],
    ]:
        boardwalk(p, points, y=65)
    for points in [
        [(15, 28), (49, 28), (78, 24), (105, 29)],
        [(14, 67), (48, 67), (78, 67), (105, 69)],
        [(15, 100), (50, 100), (82, 98), (105, 101)],
        [(54, 29), (54, 67), (54, 98)],
        [(105, 29), (105, 68), (105, 100)],
    ]:
        boardwalk(p, points, y=67)
    # Gradual transitions down to the original pier (deck Y64), away from its signs.
    for side in (-1, 1):
        for n in range(10):
            x = side*(4+n)
            y = 64+(n//4 if side == 1 else min(1, n//4))
            for z in range(23, 27):
                p.quay_put(x, y, z, 'minecraft:spruce_slab', type='top', waterlogged=False)
    # Merchant stalls frame a small, irregular open market, leaving walking space.
    for x, z, color in [(19, 82, 'red'), (38, 83, 'blue'), (-17, 73, 'green')]:
        y = 67 if x > 0 else 65
        p.pile_deck(x, z, 7, 7, y)
        for px in (x, x+6):
            for pz in (z, z+6):
                p.box(px, y+1, pz, px, y+4, pz, 'minecraft:spruce_fence')
        for px in range(7):
            for pz in range(8):
                p.put(x+px, y+5+(1 if pz in (3, 4) else 0), z-1+pz,
                      'minecraft:'+('white' if px % 2 else color)+'_wool')
        for px in range(x+1, x+6):
            p.put(px, y+1, z+2, 'minecraft:barrel', facing='south', open=False)
        p.put(x+1, y+1, z+5, 'supplementaries:sack', open=False, waterlogged=False)
        p.put(x+5, y+1, z+5, 'chipped:spruce_crate')
        if color == 'blue':
            p.chest(x+2, y+1, z+5, 'Fresh from the tide', tuple(k for k in p.registry['items']
                    if k.startswith(('fishofthieves:', 'aquaculture:', 'oceansdelight:'))
                    and any(w in k for w in ('fishing_rod', 'bait', 'knife')))[:9])
    # Limited warm pools of light; no permanent particles or constantly ticking lights.
    for x, z, y in [(-72, 30, 65), (-73, 68, 65), (-73, 119, 65), (-21, 92, 65),
                     (-111, 88, 65), (54, 32, 67), (54, 70, 67), (102, 98, 67), (17, 99, 67)]:
        p.lantern(x, y, z)
    for x, z, y in [(-18, 50, 65), (-73, 79, 65), (54, 54, 67)]:
        p.box(x, y+1, z, x, y+7, z, 'minecraft:dark_oak_fence')
        for n in range(1, 10):
            p.put(x+n, y+7-round(2*math.sin(n/10*math.pi)), z,
                  'supplementaries:rope', east=True, west=True, knot=False,
                  down=False, up=False, north=False, south=False, waterlogged=False)
        p.box(x+10, y+1, z, x+10, y+7, z, 'minecraft:dark_oak_fence')
        p.put(x+5, y+4, z, 'minecraft:lantern', hanging=True, waterlogged=False)
    p.sign(-18, 66, 28, ['Lanternwater', 'The Pirate Quarter', 'Tavern - Shipwrights', 'Sails - Charts - Fishing'])
    p.landmark('Lanternwater Pirate Quarter', -21, 66, 64, 'Pirate port',
               ['Two waterfront neighborhoods', 'Lantern-lit quays', 'Fish market', 'Pirate town atmosphere'])


def build_port(home):
    layout = Layout(home)
    Storage(layout).reserve(96*1024**2)
    directory = layout.state/'settlement'
    status = read_json(directory/'status.json', {})
    if not status.get('finished'):
        raise UserError('Let the current native construction/survey operation finish first')
    core = read_json(directory/'master-45e88a165ed60ce438ec5d87094ed476faeebdaa68693ae6d1835a11eeea6aeb.json')
    proof = read_json(directory/'core-verification-pass.json', {})
    if proof.get('failures') != 0 or proof.get('plan_sha256') != '45e88a165ed60ce438ec5d87094ed476faeebdaa68693ae6d1835a11eeea6aeb':
        raise UserError('The existing core must retain its exact successful verification receipt')
    backup = read_json(directory/'backup-receipt.json')
    if not backup.get('verified'):
        raise UserError('A verified complete world backup is required')
    p = PortPlan(read_json(directory/'registry.json'), read_json(directory/'survey.json'),
                 (1120, -1120), backup['sha256'], core)
    # Keep the union: an unloaded chunk may expose fewer instantiated block
    # entities on a later survey. A new survey never revokes an earlier exclusion.
    for previous in directory.glob('terrain-before-core-*.json'):
        for row in read_json(previous)['samples']:
            p.protected.update(tuple(pos) for pos in row.get('block_entities', []))
    street_life(p)
    tavern(p)
    chandlery(p)
    shipwright(p)
    warehouse_and_loft(p)
    captains_and_cottages(p)
    target = directory/'pirate-port-plan.json'
    if target.exists():
        previous = directory/('pirate-port-plan-'+digest(target)+'.json')
        if not previous.exists():
            target.rename(previous)
    result = p.save(target)
    result.update(at=utcnow(), phase='pirate port expansion', lots=p.lots,
                  status='Design generated against native registry and completed core exclusions; not installed')
    write_json(directory/'pirate-port-manifest.json', result)
    print(json.dumps(result), flush=True)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--home', type=Path, default=Path(r'D:\A World for Two'))
    build_port(parser.parse_args().home)
