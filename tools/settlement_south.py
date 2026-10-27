"""Original contour-fitted Willow Crown district, south/west of the river.

This module creates an independently reviewable native delta.  It never talks to
the server, edits a region file, or replaces the shared ``plan.json``.  Terrain,
registry, prior-construction exclusions and a current verified backup are inputs;
native installation, persistence, machinery and shader review remain separate.
"""
from __future__ import annotations

import argparse
import heapq
import json
import math
import statistics
from dataclasses import dataclass
from pathlib import Path

from control_room.common import Layout, UserError, digest, read_json, utcnow, write_json
from control_room.storage import Storage
from tools.settlement import Plan, beds


CORE = '45e88a165ed60ce438ec5d87094ed476faeebdaa68693ae6d1835a11eeea6aeb'
PORT = '3bcc8f6bdfaf4d4ff44805e9fc5e5dee1b5b8b07d50916dba04af20a67ba72ba'
BRIDGE = 'cc2bd89a14d86fc1de2236e5a4f92ca523d911bc128fcf96f91c1e6101fb8b69'
SECTOR = (864, -1168, 1072, -944)
SURVEY_FILE = 'south-bank-survey-0.6.5.json'


@dataclass(frozen=True)
class Lot:
    name: str
    x: int
    z: int
    width: int
    depth: int
    role: str
    stories: int = 1
    plaster: str = 'minecraft:white_terracotta'
    timber: str = 'spruce'
    roof: str = 'mcwroofs:spruce_roof'


# Individual businesses, purpose and silhouettes rather than duplicated homes.
# These are starting centers for small contour fits, never permission to flatten
# the whole hillside or to move through completed construction.
LOTS = (
    Lot('Tidepath Customs House', 985, -1133, 15, 11, 'customs', 1,
        'minecraft:light_gray_terracotta', 'dark_oak', 'mcwroofs:dark_oak_roof'),
    Lot('The Lantern Netter', 961, -1144, 13, 11, 'netter', 1,
        'minecraft:cyan_terracotta', 'dark_oak'),
    Lot('Juniper Smokehouse', 926, -1147, 17, 13, 'smokehouse', 1,
        'minecraft:bricks', 'spruce', 'mcwroofs:dark_oak_roof'),
    Lot('Saltfolk Cottage', 886, -1155, 15, 11, 'cottage', 2,
        'minecraft:white_terracotta', 'oak', 'mcwroofs:oak_roof'),
    Lot('The Tidepath Stores', 1010, -1136, 17, 13, 'supply', 1,
        'minecraft:yellow_terracotta', 'dark_oak'),
    Lot('Bramble Hearth Bakehouse', 954, -1110, 19, 13, 'bakehouse', 2,
        'minecraft:white_terracotta', 'spruce', 'mcwroofs:dark_oak_roof'),
    Lot('Moss and Mortar Apothecary', 909, -1110, 17, 13, 'apothecary', 2,
        'minecraft:green_terracotta', 'oak', 'mcwroofs:oak_roof'),
    Lot('Fern and Feather Bindery', 990, -1106, 17, 13, 'bindery', 2,
        'minecraft:light_gray_terracotta', 'spruce'),
    Lot('Orchard End Cottage', 869, -1111, 15, 13, 'cottage', 1,
        'minecraft:yellow_terracotta', 'oak', 'mcwroofs:birch_roof'),
    Lot('Bluebell Loom and Linen', 929, -1086, 17, 13, 'weaver', 2,
        'minecraft:blue_terracotta', 'spruce', 'mcwroofs:oak_roof'),
    Lot('Windward Mill Workshop', 983, -1078, 19, 15, 'mill', 2,
        'minecraft:bricks', 'dark_oak', 'mcwroofs:dark_oak_roof'),
    Lot('Hearthside House', 887, -1080, 17, 13, 'cottage', 2,
        'minecraft:white_terracotta', 'spruce', 'mcwroofs:birch_roof'),
    Lot('Clover Kiln Pottery', 942, -1059, 17, 13, 'pottery', 1,
        'minecraft:orange_terracotta', 'oak', 'mcwroofs:oak_roof'),
    Lot('Roseglass Conservatory', 983, -1008, 23, 17, 'conservatory', 1,
        'minecraft:calcite', 'oak', 'mcwroofs:birch_roof'),
    Lot('Willow Crown Guildhall', 937, -1003, 23, 17, 'guildhall', 2,
        'minecraft:white_terracotta', 'dark_oak', 'mcwroofs:dark_oak_roof'),
    Lot('Moorlight Observatory', 888, -999, 17, 15, 'observatory', 2,
        'minecraft:calcite', 'spruce', 'mcwroofs:dark_oak_roof'),
    Lot('Ramble Rose Guesthouse', 1018, -998, 17, 13, 'guesthouse', 2,
        'minecraft:pink_terracotta', 'oak', 'mcwroofs:oak_roof'),
    Lot('The Orchard Press', 913, -980, 17, 13, 'press', 1,
        'minecraft:yellow_terracotta', 'spruce'),
    Lot('Quiet Bell Chapel', 961, -971, 17, 13, 'chapel', 1,
        'minecraft:calcite', 'dark_oak', 'mcwroofs:dark_oak_roof'),
)


def expanded(bounds, amount=0):
    x, z, w, d = bounds
    return {(a, b) for a in range(x-amount, x+w+amount)
            for b in range(z-amount, z+d+amount)}


class SouthPlan(Plan):
    """Absolute world-coordinate helpers with immutable completed-block custody."""

    def __init__(self, registry, survey, backup, completed):
        if not survey.get('samples') or any('ground_y' not in row for row in survey['samples']):
            raise UserError('A fresh native ground_y terrain survey is required')
        super().__init__(registry, survey, (976, -1056), backup, rotation=0)
        if self.step > 4:
            raise UserError('South-bank fitting needs a survey step of four blocks or less')
        self.fixed = {}
        self.prior_hashes = []
        for sha, plan in completed:
            self.prior_hashes.append(sha)
            for x, y, z, i in plan['blocks']:
                # Later reviewed delta plans can intentionally adapt public paving;
                # the latest actual state wins while every position stays protected.
                self.fixed[x, y, z] = plan['palette'][i]
        self.fixed_columns = {(x, z) for x, _, z in self.fixed}
        self.lot_columns = set()
        self.lots = []
        self.routes = []
        self.walk_floor = {}
        self.walk_clearance = set()
        self.ground_cache = {}
        self.survey_limits = (min(k[0] for k in self.samples), min(k[1] for k in self.samples),
                              max(k[0] for k in self.samples), max(k[1] for k in self.samples))
        self._valid_nodes = {}
        self.porch_details = set()
        self.porch_walk = {}
        self.material_details = []
        self.zone = 'Willow Crown south-bank district'

    def world(self, x, z):
        return x, z

    def ground(self, x, z):
        if (x, z) not in self.ground_cache:
            if not self.survey_limits[0] <= x <= self.survey_limits[2] or not self.survey_limits[1] <= z <= self.survey_limits[3]:
                raise UserError('A south-bank footprint exceeded the actual surveyed land')
            self.ground_cache[x, z] = super().height(x, z)
        return self.ground_cache[x, z]

    def in_sector(self, x, z, margin=0):
        return SECTOR[0]+margin <= x <= SECTOR[2]-margin and SECTOR[1]+margin <= z <= SECTOR[3]-margin

    def put(self, x, y, z, key, **properties):
        if not self.in_sector(x, z):
            raise UserError('South-bank construction left its reviewed sector: '+str((x, y, z)))
        pos = x, y, z
        if pos in self.fixed:
            if self.state(key, **properties) == self.fixed[pos]:
                return
            raise UserError('South-bank delta intersects completed construction: '+str(pos))
        if pos in self.protected:
            raise UserError('South-bank delta intersects a retained native block entity: '+str(pos))
        if key != 'minecraft:air' and pos in self.walk_clearance:
            raise UserError('Detail obstructs the reviewed walking clearance: '+str(pos))
        super().put(x, y, z, key, **properties)

    def try_detail(self, x, y, z, key, **properties):
        # Landscaping may yield to an existing building/path.  Buildings and
        # route geometry never use this optional-detail path.
        if not self.in_sector(x, z, 1) or (x, z) in self.fixed_columns or (x, z) in self.lot_columns or (x, z) in self.walk_floor:
            return False
        if (x, y, z) in self.protected or (x, y, z) in self.blocks:
            return False
        self.put(x, y, z, key, **properties)
        return True

    def fit(self, lot):
        candidates = []
        occupied = self.fixed_columns | self.lot_columns
        for dx in range(-8, 9, 2):
            for dz in range(-8, 9, 2):
                x, z = lot.x+dx, lot.z+dz
                envelope = expanded((x, z, lot.width, lot.depth), 2)
                # Keep the full roof, front porch and foundation off previous work.
                if any(not self.in_sector(a, b, 1) for a, b in envelope):
                    continue
                if envelope & occupied:
                    continue
                heights = [self.ground(a, b) for a in range(x, x+lot.width, 2)
                           for b in range(z, z+lot.depth, 2)]
                floor = round(statistics.median(heights))
                cut, fill = max(heights)-floor, floor-min(heights)
                if cut > 8 or fill > 9 or min(heights) < 64:
                    continue
                door = x+lot.width//2
                entry = [(a, b) for a in range(door-1, door+2) for b in range(z-4, z-1)]
                entry_floor = max(floor-2, min(floor, round(statistics.median(self.ground(a, b) for a, b in entry))+1))
                if any(not self.in_sector(a, b, 2) or (a, b) in occupied
                       or self.ground(a, b)-entry_floor > 5 or entry_floor-self.ground(a, b) > 6
                       for a, b in entry):
                    continue
                # The survey also lists deep archaeological containers.  Retain
                # their exact positions rather than sterilizing the entire
                # surface column above an untouched underground inventory.
                relevant = {(a, b) for a, yy, b in self.protected
                            if min(min(heights), floor)-2 <= yy <= floor+lot.stories*5+lot.width//2+4}
                if envelope & relevant:
                    continue
                score = cut*3+fill*2+sum(abs(y-floor) for y in heights)/len(heights)+.16*(abs(dx)+abs(dz))
                candidates.append((score, x, z, floor, min(heights), max(heights), entry_floor))
        if not candidates:
            raise UserError('No bounded, protected contour fit for '+lot.name)
        _, x, z, floor, low, high, entry_floor = min(candidates)
        result = {'name': lot.name, 'role': lot.role, 'x': x, 'z': z,
                  'width': lot.width, 'depth': lot.depth, 'floor': floor,
                  'survey_ground_range': [low, high], 'max_sampled_cut': high-floor,
                  'max_sampled_fill': floor-low, 'stories': lot.stories,
                  'rooms': [], 'inventory': [], 'machinery': [],
                  'entrance': [x+lot.width//2, floor+1, z-1],
                  'path_interface': [x+lot.width//2, entry_floor, z-3]}
        self.lot_columns.update(expanded((x, z, lot.width, lot.depth), 1))
        self.lots.append(result)
        return result

    def grounded_floor(self, x, z, w, d, floor, surface='minecraft:spruce_planks'):
        for a in range(x, x+w):
            for b in range(z, z+d):
                ground = self.ground(a, b)
                if floor-ground > 12 or ground-floor > 10:
                    raise UserError('A fitted floor exceeded its reviewed earthwork limit')
                for y in range(min(ground-1, floor-1), floor):
                    border = a in (x, x+w-1) or b in (z, z+d-1)
                    material = 'minecraft:stone_bricks' if border else 'minecraft:stone'
                    if border and y == ground and (a+b) % 5 == 0:
                        material = 'minecraft:mossy_stone_bricks'
                    self.put(a, y, b, material)
                self.put(a, floor, b, surface)

    def inventory(self, lot, x, y, z, title, candidates):
        items = [key for key in candidates if key in self.registry['items']]
        self.chest(x, y, z, title, items[:12])
        lot['inventory'].append({'title': title, 'position': [x, y, z], 'items': items[:12]})


def window(p, x, y, z, facing, wood):
    for dy, part in ((0, 'base'), (1, 'above')):
        p.put(x, y+dy, z, 'mcwwindows:'+wood+'_pane_window', facing=facing, part=part, windowstate='closed')
    if facing in ('north', 'south'):
        for dx, hinge in ((-1, 'left'), (1, 'right')):
            p.put(x+dx, y, z, 'mcwwindows:'+wood+'_louvered_shutter', facing=facing, hinge=hinge, open=True)
        outer = z+(-1 if facing == 'north' else 1)
        p.put(x, y-1, outer, 'supplementaries:flower_box', facing=facing, face='wall', waterlogged=False)
        p.put(x, y, outer, 'minecraft:potted_fern')


def roof(p, x, z, w, d, base, key, wood, *, high=True):
    rise = (w+1)//2 if high else max(3, (w+2)//3)
    for offset in range((w+2)//2):
        y = base+offset if high else base+round(offset*.65)
        for px, facing in ((x-1+offset, 'east'), (x+w-offset, 'west')):
            p.box(px, y, z-1, px, y, z+d, key, facing=facing, half='bottom', shape='straight')
            for pz in (z, z+d-1):
                if y > base:
                    p.box(px, base, pz, px, y-1, pz, 'minecraft:'+wood+'_planks')
    p.box(x+w//2, base+rise-1, z-1, x+w//2, base+rise-1, z+d,
          'minecraft:'+wood+'_slab', type='bottom', waterlogged=False)


def shell(p, spec, lot):
    x, z, w, d, y = lot['x'], lot['z'], lot['width'], lot['depth'], lot['floor']
    p.landmark(spec.name, x+w//2, y+1, z-2, 'South-bank village',
               ['Contour-fitted architecture', 'Purposeful furnished rooms', 'Connected hillside walk'])
    timber = 'minecraft:stripped_'+spec.timber+'_log'
    p.grounded_floor(x, z, w, d, y, 'chipped:boxed_spruce_planks')
    height = spec.stories*5
    # Only the building and its bounded roof clearance are cut; the surrounding
    # hillside and natural shore remain the principal landform.
    p.box(x-1, y+1, z-1, x+w, y+height+(w+1)//2+3, z+d, 'minecraft:air')
    for level in range(1, height+1):
        for px in range(w):
            for pz in (0, d-1):
                beam = px in (0, w-1) or px % 5 == 0 or level % 5 == 0
                p.put(x+px, y+level, z+pz, timber if beam else spec.plaster,
                      axis='x' if level % 5 == 0 else 'y')
        for pz in range(1, d-1):
            for px in (0, w-1):
                beam = pz % 5 == 0 or level % 5 == 0
                p.put(x+px, y+level, z+pz, timber if beam else spec.plaster,
                      axis='z' if level % 5 == 0 else 'y')
    for story in range(spec.stories):
        sy = y+5*story
        if story:
            p.box(x+1, sy, z+1, x+w-2, sy, z+d-2, 'minecraft:'+spec.timber+'_planks')
        for px in range(3, w-2, 5):
            for pz, facing in ((z, 'north'), (z+d-1, 'south')):
                window(p, x+px, sy+2, pz, facing, spec.timber)
        for pz in range(3, d-2, 5):
            for px, facing in ((x, 'west'), (x+w-1, 'east')):
                window(p, px, sy+2, z+pz, facing, spec.timber)
        for px in range(x+3, x+w-2, 5):
            p.box(px, sy+4, z+1, px, sy+4, z+d-2, timber, axis='z')
        p.put(x+w//2, sy+4, z+d//2, 'minecraft:lantern', hanging=True, waterlogged=False)
    p.box(x+1, y+height, z+1, x+w-2, y+height, z+d-2, 'minecraft:'+spec.timber+'_planks')
    roof(p, x, z, w, d, y+height+1, spec.roof, spec.timber,
         high=spec.role not in ('supply', 'weaver', 'netter', 'smokehouse'))
    # Entrance faces the sea; the door is two native halves with real handles.
    door = x+w//2
    for half, dy in (('lower', 1), ('upper', 2)):
        p.put(door, y+dy, z, 'mcwdoors:oak_cottage_door', facing='north',
              half=half, hinge='left', open=False, powered=False)
    p.grounded_floor(door-2, z-3, 5, 3, y, 'minecraft:stone_bricks')
    p.box(door-2, y+1, z-3, door+2, y+3, z-1, 'minecraft:air')
    # Small roofed stoop and grounded side brackets, leaving the approach open.
    for px in (door-2, door+2):
        p.box(px, y+1, z-1, px, y+3, z-1, 'minecraft:'+spec.timber+'_fence')
    p.box(door-2, y+4, z-2, door+2, y+4, z-1,
          'minecraft:'+spec.timber+'_slab', type='bottom', waterlogged=False)
    p.put(door+2, y+2, z-1, 'mcwlights:tavern_wall_lantern', facing='north')
    p.sign(x+1, y+1, z-2, [spec.name, 'Willow Crown', 'A World for Two'])
    p.porch_details.update({(door-2, z-1), (door+2, z-1), (x+1, z-2)})
    entry_floor = lot['path_interface'][1]
    for offset in (1, 2, 3):
        level = max(entry_floor, y-max(0, offset-1))
        for px in range(door-1, door+2):
            p.porch_walk[px, z-offset] = level
    # Chimneys are integrated into an interior hearth, with a modest flue and cap.
    if spec.role not in ('conservatory', 'chapel', 'observatory'):
        p.box(x+2, y+1, z+d-4, x+3, y+height+5, z+d-3, 'minecraft:bricks')
        p.box(x+2, y+height+6, z+d-4, x+3, y+height+6, z+d-3,
              'minecraft:brick_slab', type='bottom', waterlogged=False)
        p.put(x+2, y+1, z+d-5, 'minecraft:smoker', facing='north', lit=False)
    if spec.stories > 1:
        # Five treads reach the upper floor.  Each has three blocks of headroom;
        # a landing is deliberately separated from the furnished upper rooms.
        sx = x+w-3
        for n in range(5):
            p.put(sx, y+1+n, z+3+n, 'minecraft:'+spec.timber+'_stairs',
                  facing='south', half='bottom', shape='straight', waterlogged=False)
            p.box(sx, y+2+n, z+3+n, sx, y+4+n, z+3+n, 'minecraft:air')
        p.put(sx, y+5, z+8, 'minecraft:'+spec.timber+'_planks')
        lot['internal_stairs'] = [[sx, y+1+n, z+3+n] for n in range(5)]
    lot['rooms'].append('Open entrance and circulation to every furnished area')


def table(p, x, y, z, wood='spruce', color='green'):
    p.put(x, y, z, 'handcrafted:'+wood+'_table', color=color)
    p.put(x+1, y, z, 'handcrafted:'+wood+'_table', color=color)
    for px in (x, x+1):
        p.put(px, y, z-1, 'handcrafted:'+wood+'_chair', facing='south')
        p.put(px, y, z+1, 'handcrafted:'+wood+'_chair', facing='north')
    p.put(x, y+1, z, 'minecraft:flower_pot')


def upper_room(p, spec, lot):
    if spec.stories < 2:
        return
    x, z, w, d, y = lot['x'], lot['z'], lot['width'], lot['depth'], lot['floor']+6
    # Partition preserves a four-wide central hall and the stair landing.
    split = x+w//2-1
    p.box(split, y, z+1, split, y+3, z+d-2, 'minecraft:'+spec.timber+'_planks')
    p.box(split, y, z+d-5, split, y+1, z+d-5, 'minecraft:air')
    beds(p, x+3, y, z+5, 'green' if spec.role != 'guesthouse' else 'pink')
    p.put(x+4, y, z+4, 'handcrafted:'+spec.timber+'_nightstand')
    p.put(x+4, y+1, z+4, 'minecraft:candle', candles=1, lit=True, waterlogged=False)
    p.put(x+2, y, z+d-3, 'handcrafted:'+spec.timber+'_desk', facing='north')
    p.put(x+2, y+1, z+d-3, 'supplementaries:book_pile')
    p.put(x+2, y, z+d-4, 'handcrafted:'+spec.timber+'_chair', facing='south')
    p.put(x+w//2+1, y, z+d-3, 'handcrafted:'+spec.timber+'_couch', facing='north', color='green')
    p.put(x+w//2+2, y, z+d-3, 'handcrafted:'+spec.timber+'_couch', facing='north', color='green')
    p.put(x+w//2+1, y, z+d-5, 'handcrafted:'+spec.timber+'_side_table')
    p.put(x+w//2+1, y+1, z+d-5, 'minecraft:potted_red_tulip')
    lot['rooms'] += ['Upstairs bedroom and writing nook', 'Upper sitting room reached by internal stairs']


def furnish(p, spec, lot):
    x, z, w, d, y = lot['x'], lot['z'], lot['width'], lot['depth'], lot['floor']+1
    wood = spec.timber
    role = spec.role
    if role in ('customs', 'bindery', 'observatory', 'guildhall'):
        for px in range(x+3, x+min(w-3, 10)):
            p.put(px, y, z+3, 'handcrafted:'+wood+'_desk', facing='south')
        p.put(x+4, y+1, z+3, 'supplementaries:book_pile')
        p.put(x+5, y, z+5, 'handcrafted:'+wood+'_chair', facing='north')
        for px in range(x+2, x+w-3, 3):
            p.put(px, y, z+d-3, 'minecraft:bookshelf')
            p.put(px, y+1, z+d-3, 'minecraft:bookshelf')
        p.inventory(lot, x+2, y, z+6, 'Charts and correspondence',
                    ['minecraft:map', 'minecraft:compass', 'minecraft:paper', 'minecraft:book',
                     'minecraft:feather', 'minecraft:ink_sac', 'exposure:camera'])
        if role == 'bindery':
            p.put(x+w-5, y, z+d-4, 'minecraft:cartography_table')
            p.put(x+w-5, y, z+d-6, 'minecraft:loom', facing='north')
            lot['rooms'] += ['Book repair and letter-writing counter', 'Charts, shelving and quiet reading room']
        elif role == 'customs':
            p.put(x+w-4, y, z+4, 'minecraft:cartography_table')
            lot['rooms'] += ['Harbor customs counter', 'Cargo manifests and chart desk']
        elif role == 'observatory':
            p.put(x+w//2, y, z+7, 'minecraft:lectern', facing='north', has_book=False, powered=False)
            p.put(x+w-4, y+6, z+d-3, 'supplementaries:globe', facing='north')
            p.inventory(lot, x+w-4, y, z+4, 'The astronomer\'s field case',
                        ['minecraft:spyglass', 'minecraft:clock', 'minecraft:compass', 'minecraft:book'])
            lot['rooms'] += ['Astronomer\'s study', 'Upper chart room and observation windows']
        else:
            table(p, x+w//2, y, z+7, wood)
            p.put(x+w-5, y, z+3, 'xercamusic:piano', facing='south')
            p.put(x+w-5, y, z+5, 'handcrafted:'+wood+'_bench', facing='north')
            lot['rooms'] += ['Guild reception and neighborhood meeting room', 'Playable piano salon', 'Library wall']
    elif role in ('bakehouse', 'smokehouse', 'cottage', 'guesthouse'):
        for px in range(x+2, x+min(w-4, 10)):
            p.put(px, y, z+d-3, 'farmersdelight:spruce_cabinet', facing='north')
        p.put(x+5, y, z+d-3, 'farmersdelight:stove', facing='north', lit=False)
        p.put(x+5, y+1, z+d-3, 'farmersdelight:cooking_pot', facing='north')
        p.put(x+7, y+1, z+d-3, 'farmersdelight:cutting_board')
        table(p, x+4, y, z+5, wood)
        if role == 'smokehouse':
            for px in (x+w-6, x+w-4):
                p.put(px, y, z+d-3, 'minecraft:smoker', facing='north', lit=False)
            p.inventory(lot, x+w-4, y, z+3, 'The smokehouse pantry',
                        ['minecraft:cod', 'minecraft:salmon', 'minecraft:kelp', 'farmersdelight:iron_knife'])
            lot['rooms'] += ['Fish preparation kitchen', 'Two usable smokers and packing bench']
        elif role == 'bakehouse':
            p.put(x+w-5, y, z+d-3, 'farm_and_charm:stove', facing='north', lit=False)
            p.put(x+w-5, y, z+4, 'farm_and_charm:flour_bag')
            p.inventory(lot, x+w-4, y, z+3, 'Flour, fruit and a fresh start',
                        ['minecraft:wheat', 'minecraft:apple', 'minecraft:sugar', 'farmersdelight:wheat_dough'])
            lot['rooms'] += ['Bakery kitchen and mixing counter', 'Communal breakfast room']
        else:
            p.put(x+w-5, y, z+d-4, 'handcrafted:'+wood+'_couch', facing='north', color='green')
            p.put(x+w-4, y, z+d-4, 'handcrafted:'+wood+'_couch', facing='north', color='green')
            p.put(x+w-5, y, z+d-6, 'handcrafted:'+wood+'_side_table')
            if spec.stories == 1:
                beds(p, x+w-5, y, z+4, 'green')
            p.inventory(lot, x+2, y, z+3, 'A guest\'s little welcome',
                        ['minecraft:bread', 'minecraft:book', 'minecraft:paper', 'minecraft:red_tulip'])
            lot['rooms'] += ['Furnished kitchen and dining nook', 'Warm sitting area', 'Bedroom or upstairs guest rooms']
    elif role in ('netter', 'supply', 'weaver', 'pottery'):
        for px in range(x+2, x+w-3):
            p.put(px, y, z+d-3, 'handcrafted:'+wood+'_counter', facing='north')
        for px in (x+2, x+w-4):
            p.put(px, y, z+3, 'chipped:spruce_crate')
            p.put(px, y+1, z+3, 'supplementaries:sack', open=False, waterlogged=False)
        if role in ('netter', 'weaver'):
            p.put(x+w//2, y, z+d-4, 'minecraft:loom', facing='north')
            p.inventory(lot, x+3, y, z+6, 'The craftsperson\'s materials',
                        ['minecraft:string', 'minecraft:white_wool', 'minecraft:lead',
                         'supplementaries:rope', 'minecraft:fishing_rod'])
            lot['rooms'] += ['Loom and mending bench', 'Cloth or net preparation and tidy stores']
        elif role == 'pottery':
            p.put(x+w//2, y, z+d-4, 'minecraft:stonecutter', facing='north')
            p.put(x+w-4, y, z+d-3, 'minecraft:furnace', facing='north', lit=False)
            for px in (x+4, x+7, x+10):
                p.put(px, y+1, z+d-3, 'minecraft:decorated_pot', facing='north', waterlogged=False, cracked=False)
            p.inventory(lot, x+3, y, z+6, 'Clay and glazes',
                        ['minecraft:clay_ball', 'minecraft:brick', 'minecraft:flower_pot', 'minecraft:brush'])
            lot['rooms'] += ['Potter\'s workbench', 'Usable kiln furnace and ceramics display']
        else:
            p.inventory(lot, x+3, y, z+6, 'Little supplies for a long voyage',
                        ['minecraft:torch', 'minecraft:bread', 'minecraft:oak_boat',
                         'minecraft:compass', 'minecraft:leather_boots'])
            lot['rooms'] += ['Village supply counter', 'Travel provisions and crate storage']
    elif role == 'apothecary':
        for px in range(x+2, x+w-3):
            p.put(px, y, z+d-3, 'handcrafted:oak_counter', facing='north')
        for px in (x+3, x+6, x+9):
            p.put(px, y+1, z+d-3, 'supplementaries:jar', facing='north')
        p.put(x+w-4, y, z+3, 'minecraft:brewing_stand', has_bottle_0=False, has_bottle_1=False, has_bottle_2=False)
        p.put(x+w-4, y, z+5, 'minecraft:water_cauldron', level=3)
        table(p, x+4, y, z+5, 'oak')
        p.inventory(lot, x+2, y, z+3, 'The herb gardener\'s kit',
                    ['minecraft:glass_bottle', 'minecraft:poppy', 'minecraft:dandelion',
                     'minecraft:flower_pot', 'minecraft:sweet_berries'])
        lot['rooms'] += ['Herbal preparation counter', 'Brewing corner and consultation table']
    elif role == 'mill':
        p.put(x+4, y, z+4, 'create:millstone')
        p.put(x+7, y, z+4, 'create:depot', waterlogged=False)
        p.put(x+10, y, z+4, 'minecraft:crafting_table')
        p.put(x+13, y, z+4, 'minecraft:smithing_table')
        for px in (x+3, x+6, x+9):
            p.put(px, y, z+d-4, 'chipped:spruce_crate')
        p.put(x+4, y+1, z+4, 'create:chute', facing='down', shape='window', waterlogged=False)
        p.inventory(lot, x+3, y, z+7, 'Windward mill commissioning kit',
                    ['create:shaft', 'create:cogwheel', 'create:large_cogwheel', 'create:gearbox',
                     'create:hand_crank', 'minecraft:wheat'])
        lot['rooms'] += ['Milling and logistics work floor', 'Smithing and maintenance bench', 'Upstairs planning room']
        lot['machinery'].append({'position': [x+4, y, z+4], 'type': 'Create millstone with input chute and nearby depot',
                                 'state': 'Unpowered installation; native commissioning and recipe routing pending'})
    elif role == 'press':
        p.put(x+w//2, y, z+4, 'vinery:apple_press', facing='north')
        for px in range(x+3, x+w-3, 4):
            p.put(px, y, z+d-3, 'vinery:spruce_wine_rack_big', facing='north')
        table(p, x+4, y, z+8, 'spruce', 'red')
        p.inventory(lot, x+2, y, z+4, 'Orchard press starter basket',
                    ['minecraft:apple', 'minecraft:glass_bottle', 'minecraft:sugar', 'vinery:apple_cider'])
        lot['rooms'] += ['Usable apple press and bottle storage', 'Two-person orchard tasting nook']
    elif role == 'chapel':
        for pz in (z+4, z+7, z+10):
            for px in (x+3, x+w-5):
                p.put(px, y, pz, 'handcrafted:dark_oak_bench', facing='south')
                p.put(px+1, y, pz, 'handcrafted:dark_oak_bench', facing='south')
        for pz in range(z+1, z+d-2):
            p.put(x+w//2, y, pz, 'minecraft:red_carpet')
        p.put(x+w//2, y, z+d-3, 'minecraft:lectern', facing='north', has_book=False, powered=False)
        p.put(x+w//2-2, y, z+d-3, 'minecraft:candle', candles=3, lit=True, waterlogged=False)
        p.put(x+w//2+2, y, z+d-3, 'minecraft:candle', candles=3, lit=True, waterlogged=False)
        # Small pointed bellcote changes the skyline without summoning an entity.
        p.box(x+w//2-1, y+8, z+d//2, x+w//2+1, y+12, z+d//2, 'minecraft:stone_bricks')
        p.put(x+w//2, y+11, z+d//2, 'minecraft:bell', facing='north', attachment='single_wall', powered=False)
        lot['rooms'] += ['Quiet chapel with clear central aisle', 'Reading lectern and warm candle alcoves']
    elif role == 'conservatory':
        # A long glazed arcade replaces selected plaster bays and opens a real
        # plant room.  Closed contained planters avoid irrigation overflow.
        for px in range(x+2, x+w-2):
            for pz in (z, z+d-1):
                p.box(px, y+1, pz, px, y+2, pz, 'minecraft:glass_pane')
        for a in (x+3, x+w-5):
            for b in range(z+4, z+d-3):
                p.put(a, y, b, 'supplementaries:planter', extended=False, waterlogged=False)
                p.put(a, y+1, b, 'minecraft:azalea' if b % 2 else 'minecraft:flowering_azalea')
        table(p, x+w//2-1, y, z+d//2, 'oak', 'pink')
        p.put(x+w//2, y, z+d-3, 'handcrafted:oak_couch', facing='north', color='pink')
        p.inventory(lot, x+2, y, z+3, 'Roseglass gardener\'s basket',
                    ['minecraft:rose_bush', 'minecraft:pink_tulip', 'minecraft:bone_meal',
                     'minecraft:flower_pot', 'minecraft:shears'])
        lot['rooms'] += ['Glazed botanical arcade and planters', 'Garden tea room and secluded reading couch']
    upper_room(p, spec, lot)


def valid_walk_node(p, node):
    if node in p._valid_nodes:
        return p._valid_nodes[node]
    x, y, z = node
    valid = p.in_sector(x, z, 2)
    if valid:
        for a in range(x-1, x+2):
            for b in range(z-1, z+2):
                if (a, b) in p.fixed_columns or (a, b) in p.lot_columns or (a, b) in p.porch_details:
                    valid = False
                    break
                ground = p.ground(a, b)
                if ground-y > 5 or y-ground > 6:
                    valid = False
                    break
                if any((a, yy, b) in p.protected or (a, yy, b) in p.tags
                       for yy in range(min(ground-1, y-1), y+4)):
                    valid = False
                    break
            if not valid:
                break
    p._valid_nodes[node] = valid
    return valid


def walk_route(p, start, end, name):
    """Finite 3D A*: cardinal walking steps, no teleport, ladders or tall jumps."""
    if not valid_walk_node(p, start) or not valid_walk_node(p, end):
        raise UserError('Walking endpoint has no safe three-wide clearance: '+name+' '+str((start, end)))
    frontier = [(0., start)]
    costs = {start: 0.}
    parents = {}
    visits = 0
    while frontier:
        _, current = heapq.heappop(frontier)
        if current == end:
            nodes = [end]
            while nodes[-1] != start:
                nodes.append(parents[nodes[-1]])
            nodes.reverse()
            p.routes.append({'name': name, 'nodes': nodes, 'width': 3,
                             'max_center_step': max((abs(a[1]-b[1]) for a, b in zip(nodes, nodes[1:])), default=0)})
            return nodes
        visits += 1
        if visits > 160_000:
            raise UserError('Bounded hillside path search exhausted: '+name)
        x, y, z = current
        for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            a, b = x+dx, z+dz
            if not p.in_sector(a, b, 2):
                continue
            for dy in (0, 1, -1):
                nxt = a, y+dy, b
                if not valid_walk_node(p, nxt):
                    continue
                earth = abs(p.ground(a, b)-nxt[1])
                cost = costs[current]+1.+abs(dy)*.5+earth*.18
                if cost >= costs.get(nxt, float('inf')):
                    continue
                costs[nxt] = cost
                parents[nxt] = current
                heuristic = (abs(a-end[0])+abs(b-end[2]))*1.12+abs(nxt[1]-end[1])*.65
                heapq.heappush(frontier, (cost+heuristic, nxt))
    raise UserError('No grounded, walkable hillside connection: '+name)


def nearest_open(p, x, z, radius=10):
    candidates = []
    for dx in range(-radius, radius+1):
        for dz in range(-radius, radius+1):
            a, b = x+dx, z+dz
            if not p.in_sector(a, b, 2):
                continue
            y = p.ground(a, b)
            if valid_walk_node(p, (a, y, b)):
                candidates.append((abs(dx)+abs(dz), abs(dx), abs(dz), a, y, b))
    if not candidates:
        raise UserError('No protected hillside path anchor near '+str((x, z)))
    return tuple(min(candidates)[-3:])


def circulation(p):
    anchors = [(1007, -1141), (978, -1136), (978, -1114), (978, -1089),
               (966, -1065), (959, -1042), (969, -1020), (976, -1004),
               (977, -982), (986, -959)]
    main = [nearest_open(p, x, z) for x, z in anchors]
    all_nodes = []
    for n, (a, b) in enumerate(zip(main, main[1:]), 1):
        all_nodes.extend(walk_route(p, a, b, 'Bramble Steps promenade '+str(n)))
    for lot in p.lots:
        x, y, z = lot['path_interface']
        # The porch is five wide and is a permitted interface, while the actual
        # building envelope remains forbidden to the path search.
        start = x, y, z
        choices = sorted(set(all_nodes), key=lambda v: abs(v[0]-x)+abs(v[2]-z)+abs(v[1]-y))
        target = choices[0]
        nodes = walk_route(p, start, target, 'Doorway to '+lot['name'])
        all_nodes.extend(nodes)
        lot['connected_to_promenade'] = True
    # Expand each reviewed center line to a three-wide paved walk.  At a crossing
    # the higher of adjacent grades wins; propagation keeps neighboring walking
    # blocks within a single block, and the native stair faces the higher neighbor.
    p.walk_floor.update(p.porch_walk)
    for route in p.routes:
        for n, (x, y, z) in enumerate(route['nodes']):
            other = route['nodes'][min(n+1, len(route['nodes'])-1)] if n+1 < len(route['nodes']) else route['nodes'][max(0, n-1)]
            cross_x = 0 if other[0] != x else 1
            cross_z = 1 if other[0] != x else 0
            for offset in (-1, 0, 1):
                a, b = x+cross_x*offset, z+cross_z*offset
                p.walk_floor[a, b] = max(y, p.walk_floor.get((a, b), y))
    for _ in range(20):
        changed = False
        for (x, z), y in list(p.walk_floor.items()):
            highest = max((p.walk_floor.get((x+dx, z+dz), y) for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1))), default=y)
            if highest-y > 1:
                p.walk_floor[x, z] = highest-1
                changed = True
        if not changed:
            break
    else:
        raise UserError('Walking grade propagation failed to converge')
    for (x, z), y in sorted(p.walk_floor.items()):
        ground = p.ground(x, z)
        if ground-y > 6 or y-ground > 8:
            raise UserError('Walking earthwork exceeded its bounded cut/fill budget')
        if (x, z) in p.fixed_columns or ((x, z) in p.lot_columns and (x, z) not in p.porch_walk):
            raise UserError('Walking width intersects a retained structure')
        for yy in range(min(ground-1, y-1), y):
            p.put(x, yy, z, 'minecraft:stone_bricks' if yy < y-1 else 'minecraft:andesite')
        higher = [(dx, dz) for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1))
                  if p.walk_floor.get((x+dx, z+dz), y) == y+1]
        if higher:
            dx, dz = higher[0]
            facing = {(1, 0): 'east', (-1, 0): 'west', (0, 1): 'south', (0, -1): 'north'}[dx, dz]
            p.put(x, y, z, 'minecraft:stone_brick_stairs', facing=facing, half='bottom', shape='straight', waterlogged=False)
        else:
            p.put(x, y, z, 'mcwpaths:andesite_flagstone')
        for yy in range(y+1, y+4):
            p.put(x, yy, z, 'minecraft:air')
            p.walk_clearance.add((x, yy, z))
    for route in p.routes:
        route['installed_center_nodes'] = [[x, p.walk_floor[x, z], z] for x, _, z in route['nodes']]


def landscaping(p):
    p.zone = 'Willow Crown terraced gardens and tiny discoveries'
    # The paths do not cover the whole land.  Grounded little planting pockets,
    # coherent low stone edges and repeated shrubs stitch buildings to the hill.
    flowers = ['minecraft:poppy', 'minecraft:cornflower', 'minecraft:white_tulip',
               'minecraft:pink_tulip', 'minecraft:oxeye_daisy']
    for index, lot in enumerate(p.lots):
        x, z, w, d = lot['x'], lot['z'], lot['width'], lot['depth']
        for side in (-3, w+2):
            for off in range(3, d-1, 3):
                a, b = x+side, z+off
                if not p.in_sector(a, b, 2):
                    continue
                y = p.ground(a, b)
                if p.try_detail(a, y, b, 'minecraft:moss_block'):
                    p.try_detail(a, y+1, b, flowers[(index+off) % len(flowers)])
        # A small side garden wall is grounded column by column rather than a
        # hanging level strip across a slope.
        for off in range(2, w-1):
            a, b = x+off, z+d+2
            if not p.in_sector(a, b, 2):
                continue
            y = p.ground(a, b)
            if off % 4:
                p.try_detail(a, y+1, b, 'minecraft:mossy_stone_brick_wall',
                             up=True, north='none', south='none', east='low', west='low', waterlogged=False)
    # A small number of low-cost lanterns outside the clear walking corridor.
    for n, ((x, z), y) in enumerate(sorted(p.walk_floor.items())):
        if n % 71:
            continue
        for dx, dz in ((2, 0), (-2, 0), (0, 2), (0, -2)):
            a, b = x+dx, z+dz
            if not p.in_sector(a, b, 2) or (a, b) in p.walk_floor or (a, b) in p.lot_columns or (a, b) in p.fixed_columns:
                continue
            gy = p.ground(a, b)
            if p.try_detail(a, gy+1, b, 'minecraft:stone_bricks'):
                for yy in (gy+2, gy+3):
                    p.try_detail(a, yy, b, 'minecraft:spruce_fence')
                p.try_detail(a, gy+4, b, 'minecraft:lantern', hanging=False, waterlogged=False)
                break
    romantic_gazebo(p)
    pocket_orchard(p)
    p.landmark('Bramble Steps and Willow Crown', 977, p.ground(977, -1088)+1, -1088,
               'South-bank village', ['Coastal businesses', 'Contour-fitted hillside homes',
                                      'Connected stair promenade', 'Upper village and roseglass garden'])


def romantic_gazebo(p):
    # A deliberately small stone-and-rose lookout, fitted away from house roofs.
    candidates = [(1013, -957), (1027, -955), (1047, -963), (1017, -974)]
    for cx, cz in candidates:
        footprint = {(x, z) for x in range(cx-5, cx+6) for z in range(cz-5, cz+6) if abs(x-cx)+abs(z-cz) <= 8}
        if footprint & (p.lot_columns | p.fixed_columns | set(p.walk_floor)):
            continue
        if any(not p.in_sector(x, z, 2) for x, z in footprint):
            continue
        floor = round(statistics.median(p.ground(x, z) for x, z in footprint))
        if max(abs(p.ground(x, z)-floor) for x, z in footprint) > 6:
            continue
        p.zone = 'Two Wishes Rose Lookout'
        for x, z in footprint:
            for yy in range(min(p.ground(x, z)-1, floor-1), floor):
                p.put(x, yy, z, 'minecraft:stone_bricks')
            p.put(x, floor, z, 'minecraft:polished_andesite')
            p.box(x, floor+1, z, x, floor+7, z, 'minecraft:air')
        for dx, dz in ((-4, -3), (4, -3), (-4, 3), (4, 3)):
            p.box(cx+dx, floor+1, cz+dz, cx+dx, floor+4, cz+dz, 'minecraft:oak_fence')
        for x, z in footprint:
            if abs(x-cx)+abs(z-cz) <= 7:
                p.put(x, floor+5+max(0, 3-max(abs(x-cx), abs(z-cz))), z,
                      'minecraft:oak_slab', type='bottom', waterlogged=False)
        for dx in (-1, 1):
            p.put(cx+dx, floor+1, cz+2, 'handcrafted:oak_chair', facing='north')
        p.put(cx, floor+1, cz+2, 'handcrafted:oak_side_table')
        p.put(cx, floor+2, cz+2, 'minecraft:potted_red_tulip')
        p.put(cx, floor+4, cz, 'minecraft:lantern', hanging=True, waterlogged=False)
        p.landmark('Two Wishes Rose Lookout', cx, floor+1, cz, 'Romantic overlook',
                   ['Two seats above the coast', 'Rose-tinted evening view', 'Small personal note chest'])
        p.chest(cx-3, floor+1, cz+2, 'For the little notes you leave each other',
                [i for i in ('minecraft:paper', 'minecraft:book', 'minecraft:feather', 'minecraft:ink_sac')
                 if i in p.registry['items']])
        return
    raise UserError('No bounded protected contour fit for the romantic lookout')


def pocket_orchard(p):
    # Modded apple foliage does not spawn a ticking creature; small trees vary
    # with the existing ground and leave a broad gap between canopies.
    p.zone = 'The pocket orchard and secret path'
    for cx, cz in ((879, -1035), (893, -1038), (878, -1020), (905, -1024)):
        footprint = {(cx+dx, cz+dz) for dx in range(-3, 4) for dz in range(-3, 4)}
        if footprint & (p.lot_columns | p.fixed_columns | set(p.walk_floor)) or any(not p.in_sector(x, z, 2) for x, z in footprint):
            continue
        y = p.ground(cx, cz)
        p.box(cx, y+1, cz, cx, y+4, cz, 'vinery:apple_log', axis='y')
        for dy, radius in ((3, 2), (4, 3), (5, 2)):
            for dx in range(-radius, radius+1):
                for dz in range(-radius, radius+1):
                    if abs(dx)+abs(dz) > radius+1 or dx == dz == 0:
                        continue
                    p.put(cx+dx, y+dy, cz+dz, 'vinery:apple_leaves', persistent=True, distance=1, waterlogged=False)
    # A small reachable reward tucked beside a normal path, not buried in stone.
    for route in p.routes:
        if 'Clover Kiln' not in route['name']:
            continue
        for x, _, z in route['nodes'][2:-2]:
            for dx, dz in ((3, 0), (-3, 0)):
                a, b = x+dx, z+dz
                if not p.in_sector(a, b, 2) or (a, b) in p.lot_columns | p.fixed_columns | set(p.walk_floor):
                    continue
                y = p.ground(a, b)
                if abs(y-p.walk_floor.get((x, z), y)) <= 1:
                    p.chest(a, y+1, b, 'A little hillside discovery',
                            [i for i in ('minecraft:amethyst_shard', 'minecraft:cookie', 'minecraft:book') if i in p.registry['items']])
                    p.material_details.append({'type': 'reachable small discovery chest', 'position': [a, y+1, b]})
                    return


def construct(registry, survey, backup, completed, previous_surveys=()):
    p = SouthPlan(registry, survey, backup, completed)
    for previous in previous_surveys:
        for row in previous.get('samples', []):
            p.protected.update(tuple(pos) for pos in row.get('block_entities', []))
    fitted = [(spec, p.fit(spec)) for spec in LOTS]
    for spec, lot in fitted:
        shell(p, spec, lot)
        furnish(p, spec, lot)
    circulation(p)
    landscaping(p)
    if p.protected & p.blocks.keys() or p.fixed.keys() & p.blocks.keys():
        raise UserError('Final south-bank custody collision')
    for lot in p.lots:
        for inventory in lot['inventory']:
            position = tuple(inventory['position'])
            if not p.blocks.get(position, '').startswith('minecraft:chest') or position not in p.tags:
                raise UserError('A furnishing or path overwrote a planned inventory: '+inventory['title'])
    return p


def prepare(home):
    layout = Layout(home)
    # Finite maximum for the unique plan, manifest and archived prior plan; the
    # caller must additionally satisfy the host's independent per-drive guard.
    Storage(layout).reserve(96*1024**2)
    directory = layout.state/'settlement'
    status = read_json(directory/'status.json', {})
    if not status.get('finished'):
        raise UserError('Let the current native survey/construction operation finish first')
    backup = read_json(directory/'backup-receipt.json', {})
    if not backup.get('verified') or len(backup.get('sha256', '')) != 64:
        raise UserError('A current verified complete world backup receipt is required')
    completed = []
    for prefix, sha in (('master-', CORE), ('pirate-port-master-', PORT), ('drawbridge-master-', BRIDGE)):
        path = directory/(prefix+sha+'.json')
        if not path.is_file() or digest(path) != sha:
            raise UserError('Completed-construction input hash changed: '+path.name)
        completed.append((sha, read_json(path)))
    previous = [read_json(path) for path in directory.glob('terrain-before-core-*.json')]
    previous += [read_json(path) for path in directory.glob('*survey*.json')
                 if path.name not in ('survey.json', SURVEY_FILE)]
    survey_path = directory/SURVEY_FILE
    survey = read_json(survey_path)
    p = construct(read_json(directory/'registry.json'), survey, backup['sha256'], completed, previous)
    target = directory/'south-bank-plan.json'
    if target.exists():
        archived = directory/('south-bank-plan-'+digest(target)+'.json')
        if not archived.exists():
            target.rename(archived)
    result = p.save(target)
    result.update(at=utcnow(), phase='south-west bank Willow Crown expansion',
                  status='Generated native delta only; placement, persistence, functionality and shader review pending',
                  input_survey=survey_path.name, survey_sha256=digest(survey_path),
                  exclusion_plans=p.prior_hashes, reviewed_sector=list(SECTOR),
                  lots=p.lots, circulation=p.routes,
                  walkable_columns=len(p.walk_floor), walkable_headroom=3,
                  walk_surface=[[x, y, z] for (x, z), y in sorted(p.walk_floor.items())],
                  material_details=p.material_details,
                  mod_coverage={k: sorted(v) for k, v in p.uses.items()},
                  limits={'maximum_placements': 550000, 'lot_cut_blocks': 10,
                          'lot_fill_blocks': 12, 'path_cut_blocks': 6, 'path_fill_blocks': 8,
                          'persistent_entities_added': 0, 'permanent_chunk_tickets_added': 0})
    write_json(directory/'south-bank-manifest.json', result)
    print(json.dumps({k: result[k] for k in ('path', 'sha256', 'blocks', 'palette', 'block_entities', 'landmarks', 'walkable_columns', 'status')}), flush=True)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--home', type=Path, default=Path(r'D:\A World for Two'))
    prepare(parser.parse_args().home)
