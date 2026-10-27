"""One authored age-of-sail prototype, prepared only for an isolated staging world.

This is deliberately not a fleet generator or a modification of the rejected
settlement templates. Local coordinates use X athwartships, Z aft and Y above
water. Native placement and genuine graphical review belong to the host.
"""
from __future__ import annotations

import argparse
from collections import deque
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import re

from control_room.common import Layout, REPO, UserError, atomic_write, digest, read_json, utcnow, write_json
from control_room.storage import Storage
from tools.settlement import Plan
from tools.artistic_materials import require_material_rule


NAME = 'Rosewater Lark - artistic recovery prototype'
AIR = 'minecraft:air'
MAX_BLOCKS = 180_000
LOCAL_BOUNDS = (-23, -8, -68, 23, 72, 49)
DECKS = {'hold': -7, 'berth': -2, 'gun': 3, 'weather': 8, 'forecastle': 13, 'quarterdeck': 15}

# Hand-authored waterline stations: a fine forward entry and a much narrower
# transom replace the old nearly constant-width middle and broad square stern.
# These are an original voxel interpretation, not digitized museum coordinates.
STATIONS = ((-44, .3), (-42, 1.8), (-39, 4.0), (-35, 6.8), (-30, 8.8),
            (-24, 10.3), (-16, 11.3), (-6, 11.5), (5, 11.4), (16, 10.8),
            (25, 9.8), (32, 8.4), (37, 7.0), (41, 5.8), (44, 4.7))
SECTIONS = ((-8, .16), (-7, .47), (-6, .72),
            (-5, .86), (-4, .94), (-3, .99), (-2, 1.0), (0, 1.0),
            (2, .98), (4, .95), (6, .91), (8, .86), (11, .80), (15, .74))
SHEER = ((-44, 12), (-39, 11), (-33, 10), (-26, 9), (-20, 8),
         (19, 8), (27, 9), (33, 10), (44, 11))
GUN_STATIONS = (-32, -26, -20, -14, -8, -2, 4, 10, 16, 22, 28, 34)
REFERENCES = (
    {'id': 'RMG-ZAZ3355', 'url': 'https://www.rmg.co.uk/collections/objects/rmgc-object-83146',
     'use': '1756 proposed body, sheer and half-breadth plan for Liverpool (1758); hull/deck organization only'},
    {'id': 'RMG-ZAZ3358', 'url': 'https://www.rmg.co.uk/collections/objects/rmgc-object-83149',
     'use': 'Proposed upper deck, c.1756; deck functions and raised end platforms'},
    {'id': 'RMG-ZAZ3359', 'url': 'https://www.rmg.co.uk/collections/objects/rmgc-object-83150',
     'use': 'Upper/lower decks and fore/aft platforms, 1769 proposal; distinct deck functions'},
    {'id': 'USSCM-decks', 'url': 'https://ussconstitutionmuseum.org/2016/07/14/decks/',
     'use': 'Deck beams/knees and spar/gun/berth/orlop distinction; later frigate comparison, not identical ship'},
)
SEAL_BLOCKS = {'minecraft:dark_oak_planks', 'minecraft:spruce_planks', 'minecraft:birch_planks',
               'minecraft:oak_planks', 'minecraft:oak_log', 'minecraft:oak_wood',
               'minecraft:dark_oak_log', 'minecraft:stripped_spruce_log', 'minecraft:stripped_dark_oak_log',
               'minecraft:stripped_oak_log', 'minecraft:stripped_birch_log', 'minecraft:stripped_oak_wood',
               'minecraft:yellow_terracotta', 'minecraft:blue_terracotta'}
# The real R1 shader views exposed cream frame stations as exterior barcodes.
# R2 retains the authored joints, but uses related timber textures and tones.
TIMBER_FINISH = {
    'minecraft:stripped_birch_log': 'chipped:detailed_dark_oak_planks',
    'minecraft:oak_log': 'chipped:nailed_dark_oak_planks',
    'minecraft:oak_wood': 'chipped:stacked_dark_oak_planks',
    'minecraft:stripped_oak_wood': 'chipped:fine_vertical_dark_oak_planks',
    'minecraft:oak_planks': 'chipped:vertical_dark_oak_planks',
    'minecraft:birch_planks': 'chipped:detailed_spruce_planks',
}
SEAL_BLOCKS.update(TIMBER_FINISH.values())


def interpolate(points, value):
    if value <= points[0][0]:
        return points[0][1]
    for (a, av), (b, bv) in zip(points, points[1:]):
        if value <= b:
            t = (value-a)/(b-a)
            return av+(bv-av)*t
    return points[-1][1]


def sheer(z):
    return round(interpolate(SHEER, z))


def weather_floor(z):
    # The captain's cabin receives a level sole, independently of the rising rail.
    return 10 if z >= 29 else sheer(z)


def halfwidth(z, y):
    if not -44 <= z <= 44 or not -8 <= y <= sheer(z)+1:
        return -1
    # The keel ends before the raked stem and counter. Upper end stations remain
    # visible above water rather than becoming a blunt vertical end-wall.
    if y < -5 and (z < -38+(max(0, -y-5)) or z > 40-max(0, -y-5)):
        return -1
    return max(0, round(interpolate(STATIONS, z)*interpolate(SECTIONS, y)))


def voxel_line(a, b):
    """Face-connected slender rope/spar path, with deterministic endpoints."""
    current = tuple(a)
    yield current
    steps = max(abs(b[i]-a[i]) for i in range(3))
    if not steps:
        return
    for n in range(1, steps+1):
        target = tuple(round(a[i]+(b[i]-a[i])*n/steps) for i in range(3))
        for axis in range(3):
            while current[axis] != target[axis]:
                item = list(current)
                item[axis] += 1 if target[axis] > current[axis] else -1
                current = tuple(item)
                yield current


class ArtisticShip(Plan):
    def __init__(self, registry, origin=(0, 63, 0), rotation=0, backup='0'*64):
        # Reuse only native state/serialization helpers, never previous geometry.
        self.registry, self.native = registry, registry['blocks']
        self.cx, self.sea, self.cz = origin
        self.rotation = rotation % 4
        self.backup = backup
        self.blocks, self.tags, self.commands, self.landmarks = {}, {}, [], []
        self.protected, self.features, self.uses = set(), [], {}
        self.zone = NAME
        self.ropes, self.rooms, self.guns, self.stairs, self.cameras = set(), [], [], [], []
        self.rope_roles = {}
        self.hatch_clearance = set()
        self.shell_cells = set()
        self.required_ids = set()

    def state(self, key, **properties):
        self.required_ids.add(key)
        if key not in self.native:
            raise UserError('Prototype requires an actual registered block: '+key)
        if unknown := properties.keys()-self.native[key].keys():
            raise UserError('Prototype property does not exist: '+key+' '+','.join(sorted(unknown)))
        # Plan.state rotates facing and axes. Rotate directional connection keys
        # too, otherwise a rotated rope is visually disconnected.
        if self.rotation:
            directions = ('north', 'east', 'south', 'west')
            properties = {(directions[(directions.index(k)+self.rotation) % 4] if k in directions else k): v
                          for k, v in properties.items()}
            if 'rotation' in properties and len(self.native[key].get('rotation', [])) == 16:
                properties['rotation'] = (int(properties['rotation'])+self.rotation*4) % 16
        return super().state(key, **properties)

    def put(self, x, y, z, key, **properties):
        if not all(type(v) is int for v in (x, y, z)):
            raise UserError('Prototype positions must be exact integer voxels')
        if not (LOCAL_BOUNDS[0] <= x <= LOCAL_BOUNDS[3] and
                LOCAL_BOUNDS[1] <= y <= LOCAL_BOUNDS[4] and
                LOCAL_BOUNDS[2] <= z <= LOCAL_BOUNDS[5]):
            raise UserError('Authored ship exceeded its finite local envelope: '+str((x, y, z)))
        if ((x, y, z) in self.shell_cells and y <= 0
                and key not in ('minecraft:birch_planks', 'minecraft:spruce_planks', 'minecraft:dark_oak_planks',
                                'minecraft:oak_planks', 'minecraft:dark_oak_log', 'minecraft:stripped_spruce_log',
                                'minecraft:stripped_dark_oak_log', 'minecraft:yellow_terracotta')):
            raise UserError('Furniture/air must not replace the sealed lower hull: '+str((x, y, z)))
        # Deliberate joinery: fore/aft strakes in <=3-wide gores, seven-block
        # plank lengths and transverse frame stations every eight blocks. This
        # is a consistent construction language, never random palette noise.
        if key in ('minecraft:birch_planks', 'minecraft:spruce_planks', 'minecraft:dark_oak_planks'):
            if z % 8 == 0:
                key = ('minecraft:dark_oak_log' if y % 8 == 0 else 'minecraft:oak_wood') if x % 8 == 0 else ('minecraft:oak_log' if y % 4 == 0 else 'minecraft:stripped_birch_log')
                properties = {'axis': 'x'}
            elif y % 4 == 0 and key != 'minecraft:birch_planks':
                key = 'minecraft:stripped_oak_wood' if x % 4 == 0 else 'minecraft:dark_oak_log'
                properties = {'axis': 'z'}
            elif x % 4 == 0:
                key, properties = 'minecraft:oak_planks', {}
        elif key in ('minecraft:stripped_dark_oak_log', 'minecraft:stripped_spruce_log', 'minecraft:dark_oak_log'):
            axis = properties.get('axis', 'y')
            coordinate = {'x': x, 'y': y, 'z': z}[axis]
            key = ('minecraft:dark_oak_log' if coordinate % 8 == 0 else
                   {'x': 'minecraft:stripped_dark_oak_log', 'y': 'minecraft:stripped_spruce_log', 'z': 'minecraft:stripped_oak_log'}[axis])
            properties = {'axis': axis}
        elif key in ('minecraft:dark_oak_slab', 'minecraft:spruce_slab'):
            if z % 8 == 0:
                key = 'minecraft:jungle_slab' if x % 8 == 0 else 'minecraft:spruce_slab'
            else:
                key = 'minecraft:oak_slab' if x % 4 == 0 else 'minecraft:dark_oak_slab'
        elif key == 'minecraft:birch_fence' and y % 3 == 0:
            key = 'minecraft:dark_oak_fence'
        elif key == 'minecraft:dark_oak_stairs' and z % 8 == 0:
            key = 'minecraft:oak_stairs'
        elif key == 'minecraft:yellow_terracotta':
            if z % 8 == 0:
                key = 'minecraft:oak_wood' if x % 8 == 0 else 'minecraft:oak_log'
                properties = {'axis': 'x'}
            elif x % 4 == 0:
                key = 'minecraft:blue_terracotta'
        if key in TIMBER_FINISH:
            key, properties = TIMBER_FINISH[key], {}
        super().put(x, self.sea+y, z, key, **properties)
        if len(self.blocks) > MAX_BLOCKS:
            raise UserError('Prototype exceeds its bounded native plan size')

    def tag(self, x, y, z, nbt):
        return super().tag(x, self.sea+y, z, nbt)

    def local_state(self, x, y, z):
        wx, wz = self.world(x, z)
        return self.blocks.get((wx, self.sea+y, wz), AIR)

    def rope(self, a, b):
        dominant = max(range(3), key=lambda i: abs(b[i]-a[i]))
        for pos in voxel_line(a, b):
            self.ropes.add(pos)
            self.rope_roles[pos] = dominant

    def spar(self, a, b, material='minecraft:stripped_dark_oak_log'):
        axis = 'x' if abs(b[0]-a[0]) > max(abs(b[1]-a[1]), abs(b[2]-a[2])) else 'y' if abs(b[1]-a[1]) > abs(b[2]-a[2]) else 'z'
        for pos in voxel_line(a, b):
            self.put(*pos, material, axis=axis)

    def finish_ropes(self):
        neighbors = {'west': (-1, 0, 0), 'east': (1, 0, 0), 'down': (0, -1, 0),
                     'up': (0, 1, 0), 'north': (0, 0, -1), 'south': (0, 0, 1)}
        usable = {pos for pos in self.ropes if self.local_state(*pos) == AIR}
        def fixed(other):
            state = self.local_state(*other)
            material = state.split('[')[0]
            return (material in SEAL_BLOCKS or material.endswith('_wool')
                    or material.endswith('_slab') and 'type=double' in state)
        # R1's mixed families actually fell as items. The pinned Farm & Charm
        # class traverses only its own rope and real fixed anchors, up to 256
        # nodes. Never splice it with Supplementaries or decorative buntings.
        # Short horizontal lashings have actual native knot fittings; vertical
        # hanging runs remain rope, because the knot model has no lower arm.
        knots = set()
        for axis in (0, 2):
            starts = sorted(pos for pos in usable if tuple(pos[i]-(i == axis) for i in range(3)) not in usable)
            for start in starts:
                row, current = [], start
                while current in usable:
                    row.append(current)
                    current = tuple(current[i]+(i == axis) for i in range(3))
                last = -1
                while len(row)-last-1 > 3:
                    candidates = [i for i in range(min(len(row)-2, last+4), last, -1)
                                  if i > 0 and (row[i][0], row[i][1]-1, row[i][2]) not in usable]
                    if not candidates:
                        raise UserError('Horizontal lashing needs a proper fairlead, not a dangling knot: '+str(start))
                    last = candidates[0]
                    knots.add(row[last])
        for pos in sorted(usable):
            connections = {}
            for name, delta in neighbors.items():
                other = tuple(pos[i]+delta[i] for i in range(3))
                connections[name] = other in usable or fixed(other)
            if pos in knots:
                self.put(*pos, 'farm_and_charm:rope_knot',
                         **{key: connections[key] for key in ('north', 'south', 'east', 'west')})
            else:
                self.put(*pos, 'farm_and_charm:rope', center_piece=True, rope_knot=False,
                         supporting_rope_knot=False, **connections)
        # Keep the actual 256-visited-node upstream bound. This conservative
        # source check also requires an authored solid/cloth attachment; a
        # floating knot alone never awards this preflight support.
        for start in usable:
            queue, seen, supported = deque([start]), set(), False
            while queue and len(seen) < 256 and not supported:
                pos = queue.popleft()
                if pos in seen:
                    continue
                seen.add(pos)
                for name, delta in neighbors.items():
                    other = tuple(pos[i]+delta[i] for i in range(3))
                    if other in usable:
                        if other not in seen:
                            queue.append(other)
                    elif name != 'down' and fixed(other):
                        supported = True
                        break
            if not supported:
                raise UserError('Rope lacks an authored fixed attachment within the native search bound: '+str(start))
        self.rope_proof = {'family': 'farm_and_charm', 'positions': len(usable),
                           'native_knot_fittings': len(knots), 'anchored_source_graph': True,
                           'native_survival_and_drop_inspection_pending': True}

    def room(self, name, deck, anchor, purpose):
        self.rooms.append({'name': name, 'deck': deck, 'local_anchor': list(anchor),
                           'purpose': purpose})

    def lamp(self, x, y, z):
        # Hanging fixtures need a real ceiling, including the chain between a
        # low hold lamp and its deck beam. Never leave unsupported props.
        for offset in range(1, 5):
            if self.local_state(x, y+offset, z) != AIR:
                for rise in range(1, offset):
                    self.put(x, y+rise, z, 'minecraft:chain', axis='y', waterlogged=False)
                break
        else:
            raise UserError('Hanging lamp lacks a nearby authored ceiling: '+str((x, y, z)))
        self.put(x, y, z, 'minecraft:lantern', hanging=True, waterlogged=False)

    def barrel(self, x, y, z, facing='up'):
        self.put(x, y, z, 'minecraft:barrel', facing=facing, open=False)

    def table(self, x, y, z):
        self.put(x, y, z, 'handcrafted:dark_oak_table', color='none', shape='single', waterlogged=False)

    def chair(self, x, y, z, facing):
        self.put(x, y, z, 'handcrafted:dark_oak_chair', facing=facing, color='none', waterlogged=False)

    def stair(self, x, y, z, facing):
        self.put(x, y, z, 'minecraft:dark_oak_stairs', facing=facing, half='bottom', shape='straight', waterlogged=False)

    def encoded(self):
        if self.protected & self.blocks.keys():
            raise UserError('Prototype intersects protected native block entities')
        palette = sorted(set(self.blocks.values()))
        indices = {state: i for i, state in enumerate(palette)}
        blocks = [[x, y, z, indices[state]] for (x, y, z), state in sorted(self.blocks.items(),
                  key=lambda row: (row[0][0]//16, row[0][2]//16, row[0][1], row[0][0], row[0][2]))]
        output = {'format': 'awft-native-settlement:1', 'name': NAME, 'created': utcnow(),
                  'seed': self.registry['seed'], 'world_path': self.registry['world_path'],
                  'backup_sha256': self.backup,
                  'bounds': [min(p[0] for p in self.blocks), min(p[2] for p in self.blocks),
                             max(p[0] for p in self.blocks), max(p[2] for p in self.blocks)],
                  'palette': palette, 'blocks': blocks,
                  'block_entities': [{'pos': list(pos), 'nbt': tag} for pos, tag in self.tags.items()],
                  'commands': [], 'landmarks': self.landmarks,
                  'coverage': {key: sorted(value) for key, value in self.uses.items()},
                  'validation': 'Isolated artistic prototype only; native collision/water/visual acceptance pending.'}
        raw = json.dumps(output, separators=(',', ':'), ensure_ascii=False)+'\n'
        if len(raw.encode('utf-8')) > 16*1024**2:
            raise UserError('Prototype exceeds its finite serialized plan bound')
        return raw

    def save(self, path):
        atomic_write(path, self.encoded())
        return {'path': str(path), 'sha256': digest(path), 'blocks': len(self.blocks),
                'palette': len(set(self.blocks.values())), 'block_entities': len(self.tags), 'landmarks': len(self.landmarks)}


def hull(p):
    for z in range(-44, 45):
        top = sheer(z)+1
        for y in range(-8, top+1):
            width = halfwidth(z, y)
            for x in range(-width, width+1):
                exposed = (abs(x) == width or any(abs(x) > halfwidth(z+dz, y+dy)
                                                  for dy, dz in ((-1, 0), (0, -1), (0, 1))))
                if exposed:
                    material = 'minecraft:dark_oak_planks' if y < -1 else 'minecraft:spruce_planks'
                    if y in (0, 1, 7):
                        material = 'minecraft:dark_oak_planks'
                    if y == 6:
                        material = 'minecraft:yellow_terracotta'
                    p.put(x, y, z, material)
                    if y <= 0:
                        p.shell_cells.add((x, y, z))
                elif y in (-7, -2, 3) or y == weather_floor(z):
                    p.put(x, y, z, 'minecraft:birch_planks' if y >= 3 else 'minecraft:spruce_planks')
                else:
                    p.put(x, y, z, AIR)
        # Dark exterior wales follow the rising sheer, rather than a ruler line.
        for y in (sheer(z)-4, sheer(z)):
            w = halfwidth(z, y)
            if w < 1:
                continue
            for side in (-1, 1):
                p.put(side*w, y, z, 'minecraft:dark_oak_stairs', facing='west' if side < 0 else 'east',
                      half='top', shape='straight', waterlogged=False)
        # A properly shaped cap rail: dark slab, open railing, intermittent posts.
        w = halfwidth(z, top)
        if w >= 1:
            for side in (-1, 1):
                p.put(side*w, top+1, z, 'minecraft:dark_oak_slab', type='bottom', waterlogged=False)
    # A raked stem, beakhead rails and long rising bowsprit, not a blunt wall.
    p.spar((0, -4, -40), (0, 12, -47))
    p.spar((0, 11, -39), (0, 18, -64), 'minecraft:stripped_spruce_log')
    p.spar((0, 17, -59), (0, 20, -67), 'minecraft:stripped_spruce_log')
    for side in (-1, 1):
        p.spar((side*3, 10, -39), (side, 12, -48))
        p.rope((side*3, 12, -39), (side, 14, -49))
        p.spar((side*2, 7, -41), (side, 10, -48))
    # Restrained ivory/gold figurehead, raised under the sprit.
    for x, y, z in ((0, 12, -48), (0, 13, -49), (0, 14, -49), (0, 15, -49)):
        p.put(x, y, z, 'minecraft:smooth_sandstone')
    p.put(0, 16, -49, 'minecraft:gold_block')
    p.rope((0, 2, -42), (0, 18, -64))
    # Frame bends and knees are visible below; alternating deck work is subdued.
    for z in range(-30, 36, 6):
        for floor in (-2, 3, 8):
            w = halfwidth(z, floor-1)-1
            p.box(-w, floor-1, z, w, floor-1, z, 'minecraft:dark_oak_log', axis='x')
            for side in (-1, 1):
                p.put(side*(w-1), floor-2, z, 'minecraft:dark_oak_stairs',
                      facing='west' if side > 0 else 'east', half='top', shape='straight', waterlogged=False)


def upper_decks(p):
    # Distinct open waist, short forecastle and long raised quarterdeck.
    for z, y in [(z, 13) for z in range(-41, -26)] + [(z, 15) for z in range(22, 44)]:
        w = max(1, round(interpolate(STATIONS, z)*.80))
        for x in range(-w, w+1):
            p.put(x, y, z, 'minecraft:birch_planks')
        for side in (-1, 1):
            p.put(side*w, y+1, z, 'minecraft:dark_oak_fence')
            p.put(side*w, y+2, z, 'minecraft:dark_oak_slab', type='bottom', waterlogged=False)
            if z % 5 == 0:
                p.lamp(side*w, y+1, z)
    # Proper cabin bulkhead with pilasters, paired doors and glazing.
    for x in range(-8, 9):
        for y in range(10, 15):
            p.put(x, y, 28, 'minecraft:dark_oak_planks')
        if x in (-6, -2, 6):
            p.box(x, 11, 28, x, 13, 28, 'minecraft:glass')
            p.put(x, 14, 28, 'minecraft:oak_trapdoor', facing='north', half='top', open=True, powered=False, waterlogged=False)
    p.box(2, 11, 28, 3, 13, 28, AIR)
    # The crown cabin's floor is intentionally level and its stern walls taper.
    for z in range(29, 44):
        w = max(2, round(interpolate(STATIONS, z)*.82))
        p.box(-w, 10, z, w, 10, z, 'minecraft:dark_oak_planks')
        # Rising hull sheer caps must not become low bars across the great
        # cabin's usable headroom. The raised quarterdeck is its real ceiling.
        p.box(-w+1, 11, z, w-1, 14, z, AIR)
        for side in (-1, 1):
            for y in range(11, 15):
                p.put(side*w, y, z, 'minecraft:dark_oak_planks')
            if 32 <= z <= 40:
                p.box(side*w, 12, z, side*w, 13, z, 'minecraft:glass')
    # Convex five-bay transom, tiny gilded pilasters and wing quarter galleries.
    for x in range(-5, 6):
        z = 45 - abs(x)//2
        p.box(x, 10, z, x, 15, z, 'minecraft:dark_oak_planks')
        if x % 2 == 0:
            p.box(x, 11, z, x, 13, z, 'minecraft:glass')
        else:
            p.box(x, 11, z+1, x, 14, z+1, 'minecraft:birch_fence')
        p.put(x, 15, z+1, 'minecraft:dark_oak_stairs', facing='south', half='top', shape='straight', waterlogged=False)
        if x in (-4, 0, 4):
            p.put(x, 16, z, 'minecraft:gold_block')
    for side in (-1, 1):
        for z in range(33, 41):
            x = side*(round(interpolate(STATIONS, z)*.82)+1)
            p.put(x, 10, z, 'minecraft:dark_oak_stairs', facing='east' if side < 0 else 'west', half='top', shape='straight', waterlogged=False)
            p.put(x, 11, z, 'minecraft:birch_fence')
            p.put(x, 12, z, 'minecraft:glass')
            p.put(x, 13, z, 'minecraft:dark_oak_trapdoor', facing='west' if side < 0 else 'east', half='top', open=False, powered=False, waterlogged=False)
        p.lamp(side*5, 14, 43)
    # Two narrow, plausible steep stairways up each raised end.
    for side in (-1, 1):
        for n in range(7):
            x, z, y = side*5, 15+n, 9+n
            p.box(x, 8, z, x, y, z, 'minecraft:dark_oak_planks')
            p.box(x, y+1, z, x, y+2, z, AIR)
            p.stair(x, y, z, 'south')
            p.stairs.append((x, y, z))
        p.put(side*5, 15, 22, 'minecraft:birch_planks')
        for n in range(5):
            x, z, y = side*4, -22-n, 9+n
            p.box(x, 8, z, x, y, z, 'minecraft:dark_oak_planks')
            p.box(x, y+1, z, x, y+2, z, AIR)
            p.stair(x, y, z, 'north')
            p.stairs.append((x, y, z))
    # Waist rail posts, channels/deadeyes, restrained naval blue bulwark accent.
    for side in (-1, 1):
        for z in range(-26, 24):
            w = halfwidth(z, sheer(z)+1)
            if z % 5 == 0:
                p.put(side*w, sheer(z)+2, z, 'minecraft:dark_oak_fence')
            if z in (-26, 0, 22):
                p.put(side*(w-1), sheer(z)+1, z, 'minecraft:blue_terracotta')
    # Wheel, compass platform and aft flag staff.
    p.put(0, 16, 25, 'minecraft:dark_oak_fence')
    p.put(0, 17, 25, 'create:copper_valve_handle', facing='south')
    p.put(-2, 16, 25, 'minecraft:cartography_table')
    p.spar((0, 16, 43), (0, 23, 47), 'minecraft:stripped_spruce_log')
    for z in range(45, 49):
        p.put(1, 21, z, 'minecraft:blue_wool')
        p.put(1, 20, z, 'minecraft:white_wool')


def gun(p, side, z, deck, width, upper=False):
    breech = width-4
    facing = 'east' if side > 0 else 'west'
    for offset in range(4):
        p.put(side*(breech+offset), deck+1, z, 'minecraft:dark_oak_slab', type='double', waterlogged=False)
    for offset, key in enumerate(('cast_iron_cannon_end', 'cast_iron_cannon_chamber',
                                  'cast_iron_cannon_barrel', 'cast_iron_cannon_barrel', 'cast_iron_cannon_barrel')):
        p.put(side*(breech+offset), deck+2, z, 'createbigcannons:'+key, facing=facing)
    for dx in (breech, breech+2):
        for dz in (-1, 1):
            p.put(side*dx, deck+1, z+dz, 'minecraft:dark_oak_trapdoor', facing='north' if dz < 0 else 'south',
                  half='bottom', open=True, powered=False, waterlogged=False)
    if not upper:
        for dz in (0, 1):
            for y in (deck+1, deck+2, deck+3):
                x = side*halfwidth(z+dz, y)
                if dz == 0 and y == deck+2:
                    continue
                p.put(x, y, z+dz, AIR)
            p.put(side*halfwidth(z+dz, deck+4), deck+4, z+dz, 'minecraft:dark_oak_trapdoor',
                  facing=facing, half='top', open=False, powered=False, waterlogged=False)
    # R1's diagonal breeching line crossed carriage wheels and split into
    # unsupported fragments. Keep the native gun/carriage clear; the R2 service
    # bays carry the working gear until a real short tackle is commissioned.
    p.guns.append({'side': 'starboard' if side > 0 else 'port', 'z': z, 'deck': deck,
                   'breech': [side*breech, deck+2, z], 'loaded': False, 'assembled': False})


def interiors(p):
    # Isolated aft magazine: empty sealed display casks, no live explosives.
    for z in range(25, 36):
        w = min(4, halfwidth(z, -6)-1)
        for side in (-1, 1):
            p.box(side*w, -6, z, side*w, -4, z, 'minecraft:dark_oak_planks')
    p.box(-4, -6, 25, 4, -4, 25, 'minecraft:dark_oak_planks')
    p.box(2, -6, 25, 3, -5, 25, AIR)
    for z in (28, 31, 34):
        for x in (-2, 0):
            p.barrel(x, -6, z)
    p.sign(-1, -6, 26, ['MAGAZINE', 'Sealed display casks', 'No live powder', 'Lanterns outside'])
    p.room('Protected powder magazine', 'hold', (2, -7, 29), 'Separate safe casks, no TNT/gunpowder/fire; lamp outside bulkhead')
    # Five coherent cargo clusters leave a two-wide working aisle on starboard.
    for z, width, cargo in ((-27, 2, 'minecraft:hay_block'), (-18, 3, 'chipped:spruce_crate'),
                            (-8, 3, 'minecraft:hay_block'), (15, 3, 'chipped:spruce_crate')):
        for x in range(-5, -5+width):
            for dz in range(3):
                if abs(x) < halfwidth(z+dz, -6):
                    if (x, -6, z+dz) not in p.shell_cells:
                        p.put(x, -6, z+dz, cargo)
                    if dz == 1 and (x, -5, z+dz) not in p.shell_cells:
                        p.put(x, -5, z+dz, cargo)
    for z in (-24, -15, -4, 15, 20):
        p.barrel(5, -6, z)
        p.barrel(5, -6, z+1)
    p.chest(-3, -6, -22, 'Fresh water and dry provisions', ['minecraft:bread', 'minecraft:dried_kelp', 'minecraft:carrot'])
    p.chest(-3, -6, -12, 'Sailmaker: needles, canvas and spare line', ['minecraft:string', 'minecraft:white_wool', 'minecraft:shears'])
    p.chest(-3, -6, 20, 'Carpenter and cooper stores', ['minecraft:iron_axe', 'minecraft:oak_planks', 'minecraft:iron_nugget'])
    p.room('Forward provisions and water', 'hold', (2, -7, -24), 'Casks, tightly stacked feed and food stores')
    p.room('Main hold and sail locker', 'hold', (2, -7, -10), 'Four distinct cargo stacks, lower ceiling and unblocked central working lane')
    p.room('Shipwright repair stores', 'hold', (2, -7, 20), 'Cooper/carpenter chest and spare line beside the magazine bulkhead')
    # Crew hammocks along the curved sides, not in the central passage.
    for side in (-1, 1):
        for index, z in enumerate((-19, -14, -9, -4, 1)):
            x = side*7
            for end in (-1, 2):
                p.box(x, -1, z+end, x, 1, z+end, 'minecraft:dark_oak_fence')
            for dz, part in ((0, 'foot'), (1, 'head')):
                p.put(x, 0, z+dz, 'comforts:hammock_white', facing='south', part=part, occupied=False, waterlogged=False)
            if index % 2 == 0:
                p.barrel(side*8, -1, z)
    # Fold-away mess tables, bowls/plates supplied by useful food chests.
    for z in range(13, 20):
        p.table(-5, -1, z)
        if z % 2:
            p.chair(-7, -1, z, 'east')
            p.chair(-3, -1, z, 'west')
    p.chest(-7, -1, 21, 'Mess ration locker', ['minecraft:bread', 'minecraft:bowl', 'minecraft:cooked_cod'])
    p.room('Crew hammock berths', 'berth', (2, -2, -10), 'Ten anchored two-part hammocks, lockers and a continuous central passage')
    p.room('Crew mess', 'berth', (2, -2, 15), 'A narrow shared table with chairs, ration locker and low framing')
    # Wardroom with private officer berths aft of a pierced bulkhead.
    p.box(-7, -1, 24, 7, 1, 24, 'minecraft:dark_oak_planks')
    p.box(2, -1, 24, 3, 0, 24, AIR)
    for z in (28, 34):
        p.put(-5, -1, z, 'minecraft:blue_bed', facing='north', part='foot', occupied=False)
        p.put(-5, -1, z-1, 'minecraft:blue_bed', facing='north', part='head', occupied=False)
        p.barrel(-4, -1, z)
    p.table(-1, -1, 30)
    p.table(0, -1, 30)
    p.chair(-1, -1, 28, 'south')
    p.chair(0, -1, 32, 'north')
    p.put(5, -1, 29, 'handcrafted:dark_oak_drawer', facing='west', shape='single', type=2)
    p.room('Officers’ berths and wardroom', 'berth', (2, -2, 29), 'Two narrow officer berths and a shared planning table behind a full bulkhead')
    # The galley uses actual unlit appliances, sheltered forward of the main mast.
    for z in (-25, -24, -23):
        p.put(-3, 4, z, 'farmersdelight:spruce_cabinet', facing='east')
    p.put(-3, 4, -26, 'farmersdelight:stove', facing='east', lit=False)
    p.put(-3, 5, -26, 'farmersdelight:cooking_pot', facing='east')
    p.put(-3, 5, -23, 'farmersdelight:cutting_board')
    p.box(-3, 6, -26, -3, 11, -26, 'minecraft:cobblestone_wall')
    p.room('Forward galley', 'gun', (2, 3, -25), 'Cold range, cooking pot, prep board, pantry and a masonry flue')
    for z in GUN_STATIONS:
        w = halfwidth(z, 5)
        for side in (-1, 1):
            gun(p, side, z, 3, w)
    for z in (26, 34):
        w = max(6, round(interpolate(STATIONS, z)*.80))
        for side in (-1, 1):
            gun(p, side, z, 15, w, upper=True)
    p.room('Covered broadside gun deck', 'gun', (2, 3, -8), 'Twenty-four unloaded guns, tackles and a clear two-wide service lane')
    p.chest(-4, 4, 38, 'Navigation office charts', ['minecraft:map', 'minecraft:compass', 'minecraft:feather', 'minecraft:writable_book'])
    p.put(-3, 4, 36, 'minecraft:cartography_table')
    p.chair(-3, 4, 35, 'south')
    p.room('Lower navigation office', 'gun', (2, 3, 37), 'A quieter stern working desk below the great cabin')
    # Great cabin: one side dedicated to a berth, the other to charting and music.
    p.box(-6, 11, 30, -6, 13, 33, 'minecraft:bookshelf')
    p.put(-4, 11, 33, 'minecraft:blue_bed', facing='south', part='foot', occupied=False)
    p.put(-4, 11, 34, 'minecraft:blue_bed', facing='south', part='head', occupied=False)
    p.put(-3, 11, 39, 'handcrafted:dark_oak_desk', facing='north', color='none', waterlogged=False)
    p.put(-2, 12, 39, 'lfpirates:ship_in_bottle', facing='north', waterlogged=False)
    p.put(-2, 11, 39, 'minecraft:cartography_table')
    p.chair(-3, 11, 37, 'south')
    p.put(4, 11, 33, 'handcrafted:dark_oak_couch', facing='west', color='blue', shape='single', waterlogged=False)
    p.put(4, 11, 35, 'handcrafted:dark_oak_side_table', facing='west', color='none', waterlogged=False)
    p.put(4, 12, 35, 'minecraft:candle', candles=2, lit=True, waterlogged=False)
    p.chest(-5, 11, 36, 'Captain’s private dispatches', ['minecraft:spyglass', 'minecraft:clock', 'minecraft:writable_book', 'minecraft:rose_bush'])
    p.box(-1, 11, 33, 0, 11, 38, 'minecraft:blue_carpet')
    p.room('Captain’s great cabin', 'weather', (2, 10, 33), 'Asymmetric private berth, writing desk, model ship and glazed stern gallery')
    p.room('Quarterdeck and helm', 'quarterdeck', (3, 15, 26), 'Raised command deck, wheel, compass and four unloaded light broadside pieces')
    p.room('Forecastle and anchor handling', 'forecastle', (3, 13, -30), 'Windlass, bitts, bell, bowsprit and view back over the waist')
    # Low-level lamps hang under real beams, away from the marked main aisle.
    for floor in (-7, -2, 3):
        for z in (-24, -12, 0, 18, 30):
            p.lamp(-2, floor+3, z)
    p.lamp(0, 14, 34)
    p.lamp(0, 14, 40)


def living_details(p):
    """Purposeful R2 interior groups, authored after viewing all real R1 rooms."""
    # Cargo has dunnage, distinct heights and useful labels. Leave x2/x3 as a
    # continuous working aisle; never use an opaque wall of random containers.
    groups = ((-27, 'provisions'), (-18, 'merchant crates'), (-8, 'sailcloth'), (15, 'repair timber'))
    for z, kind in groups:
        for x in (-5, -4, -3):
            for dz in range(3):
                for y in (-6, -5):
                    if ((x, y, z+dz) in p.shell_cells
                            or abs(x) >= halfwidth(z+dz, y)
                            or p.local_state(x, -7, z+dz) == AIR):
                        continue
                    if kind == 'sailcloth':
                        key = 'chipped:bundled_white_wool' if x != -4 else 'chipped:patched_white_wool'
                        p.put(x, y, z+dz, key)
                    elif kind == 'provisions' and x == -3:
                        p.put(x, y, z+dz, 'supplementaries:sack', open=False, waterlogged=False)
                    elif kind == 'repair timber':
                        p.put(x, y, z+dz, 'minecraft:stripped_spruce_log', axis='z')
                    elif kind == 'provisions':
                        p.barrel(x, y, z+dz, 'south')
                    else:
                        p.put(x, y, z+dz, 'chipped:spruce_crate', facing='south', open=False)
        for x in (-5, -2):
            for dz in (-1, 3):
                if (x, -6, z+dz) not in p.shell_cells and abs(x) < halfwidth(z+dz, -6):
                    p.box(x, -6, z+dz, x, -3, z+dz, 'minecraft:dark_oak_fence')
        # Low rack lintels frame each inventory bay without reducing headroom.
        for dz in (-1, 3):
            p.box(-5, -3, z+dz, -2, -3, z+dz, 'minecraft:dark_oak_slab', type='top', waterlogged=False)
        p.lamp(-3, -3, z+1)
    for z in (-22, -12, -2, 18):
        for dz in (0, 1):
            p.barrel(4, -6, z+dz, 'west')
        p.barrel(4, -5, z, 'west')
        p.put(5, -6, z, 'supplementaries:sack', open=False, waterlogged=False)
    # The sailmaker is interrupted mid-repair: folded cloth, shears locker,
    # a bench and hanging lantern beside the folded-canvas stack.
    p.put(-4, -6, -3, 'minecraft:crafting_table')
    p.put(-4, -5, -3, 'handcrafted:stackable_book', books=2, facing='south', seed=5)
    p.put(-5, -6, -3, 'handcrafted:dark_oak_drawer', facing='east', shape='single', type=3)
    p.chest(-3, -6, -2, 'Sailmaker: repair in progress', ['minecraft:shears', 'minecraft:string', 'minecraft:white_wool'])
    p.sign(-1, -6, -5, ['SAIL LOCKER', 'Dry folded canvas', 'Needles & spare line', 'Keep aisle clear'])
    p.put(-4, -6, 21, 'minecraft:grindstone', face='floor', facing='east')
    p.put(-5, -6, 20, 'minecraft:crafting_table')
    p.put(-5, -5, 20, 'handcrafted:terracotta_thin_pot')
    p.chair(-4, -6, 19, 'south')
    p.sign(-1, -6, 22, ['COOPER & SHIPWRIGHT', 'Adzes, hoops, timber', 'Return borrowed tools', 'Dry stores only'])
    # Crew mess now reads as a meal, with paired crockery and personal lockers.
    for z in (13, 15, 17, 19):
        p.put(-5, 0, z, 'handcrafted:blue_plate', facing='east', pieces=2, waterlogged=False)
    for z in (14, 18):
        p.put(-5, 0, z, 'handcrafted:blue_cup', facing='south', pieces=3, waterlogged=False)
    p.put(-5, 0, 16, 'handcrafted:terracotta_thick_pot')
    for z in (-18, -8, 1):
        p.put(5, -1, z, 'handcrafted:dark_oak_drawer', facing='west', shape='single', type=1)
        p.put(5, 0, z, 'handcrafted:stackable_book', books=2, facing='west', seed=12)
    p.put(-1, -1, 34, 'handcrafted:dark_oak_cupboard', facing='north', type=2)
    p.put(-1, 0, 34, 'handcrafted:stackable_book', books=3, facing='north', seed=21)
    p.put(0, 0, 30, 'handcrafted:blue_plate', facing='north', pieces=2, waterlogged=False)
    # Gun working bays sit between the actual guns, never across their bores or
    # the two-wide route. Rammers/worms are useful stored tools, no live charge.
    for side in (-1, 1):
        for index, z in enumerate((-29, -17, -5, 13, 25)):
            x = side*5
            p.barrel(x, 4, z, 'east' if side < 0 else 'west')
            p.put(x, 5, z, 'handcrafted:terracotta_wide_pot')
            p.box(side*7, 4, z+1, side*7, 5, z+1, 'minecraft:dark_oak_fence')
            p.put(side*7, 6, z+1, 'minecraft:dark_oak_trapdoor', facing='north', half='top', open=False, powered=False, waterlogged=False)
            if index % 2 == 0:
                p.chest(side*5, 4, z+2, 'Gunner: cleaning tools and dry wadding',
                        ['createbigcannons:worm', 'minecraft:stick', 'minecraft:white_wool', 'minecraft:iron_nugget'])
            else:
                p.put(side*5, 4, z+2, 'chipped:spruce_crate', facing='south', open=False)
            p.lamp(side*5, 7, z+1)
    # Forward galley has visible food preparation and a pantry, rather than a
    # lone cold cooker in a black corridor. Heat/fire remains deliberately off.
    p.put(-3, 5, -25, 'handcrafted:blue_plate', facing='east', pieces=4, waterlogged=False)
    p.put(-3, 5, -24, 'handcrafted:terracotta_medium_pot')
    p.put(-4, 4, -22, 'supplementaries:sack', open=False, waterlogged=False)
    p.chest(-3, 4, -21, 'Cook: today’s pantry', ['minecraft:bread', 'minecraft:potato', 'minecraft:bowl', 'minecraft:cooked_cod'])
    p.lamp(-2, 7, -23)
    # A real chart-room group is visible from the unchanged comparison pose.
    # The right-hand x2/x3 route to the stern is intentionally unobstructed.
    for x in (-3, -2, -1):
        for z in (35, 36):
            p.table(x, 11, z)
    p.put(-2, 11, 36, 'minecraft:cartography_table')
    p.put(-3, 12, 35, 'handcrafted:stackable_book', books=3, facing='east', seed=37)
    p.put(-1, 12, 35, 'supplementaries:hourglass', facing='up', light_level=0, waterlogged=False)
    p.chair(-4, 11, 35, 'east')
    p.chair(-2, 11, 38, 'north')
    p.put(-5, 11, 31, 'handcrafted:dark_oak_cupboard', facing='east', type=1)
    p.put(-5, 12, 31, 'handcrafted:dark_oak_cupboard', facing='east', type=2)
    p.put(-6, 13, 35, 'handcrafted:dark_oak_shelf', facing='east', shape='single', type=3)
    p.put(-5, 11, 35, 'handcrafted:dark_oak_drawer', facing='east', shape='single', type=3)
    p.put(-5, 12, 35, 'handcrafted:stackable_book', books=4, facing='east', seed=43)
    p.put(-1, 11, 40, 'handcrafted:dark_oak_side_table', facing='north', color='none', waterlogged=False)
    p.put(-1, 12, 40, 'supplementaries:globe_sepia', facing='north', powered=False, rotation=2, waterlogged=False)
    for z in (36, 37, 38):
        p.put(4, 11, z, 'handcrafted:dark_oak_bench', facing='west', color='blue', shape='single', waterlogged=False)
    p.put(4, 12, 35, 'handcrafted:blue_cup', facing='west', pieces=2, waterlogged=False)
    p.put(-3, 12, 39, 'minecraft:candle', candles=2, lit=True, waterlogged=False)
    # Starboard hanging textile and compact day berth give the cabin a personal
    # blue palette, framed in timber; no six-block bare wall or enormous table.
    for z in (30, 31, 32):
        p.put(6, 14, z, 'minecraft:blue_wool')
    p.put(-4, 11, 32, 'handcrafted:dark_oak_nightstand', facing='east', color='blue', waterlogged=False)
    p.put(-4, 12, 32, 'handcrafted:terracotta_thin_pot')
    p.detail_groups = ['Dunnage-framed provisions, merchant cargo, folded sailcloth and spare timber bays',
                       'Sailmaker repair bench and labelled cooper/shipwright store',
                       'Laid crew mess, personal lockers and officer reading cupboard',
                       'Ten separate gun-service bays with unloaded equipment and cleaning-tool lockers',
                       'Cold galley pantry and visible crockery',
                       'Captain’s chart table, logbooks, hourglass, globe, window bench, cupboard and berth']


def companionways(p):
    # A real two-wide switchback companionway replaces the old vertical-only
    # central access. The different flights occupy separate X lanes.
    p.box(-5, -6, 4, -1, 10, 10, AIR)
    flights = ((-7, (-5, -4), range(5, 10), 'south'),
               (-2, (-2, -1), range(9, 4, -1), 'north'),
               (3, (-5, -4), range(5, 10), 'south'))
    for floor, xs, zs, facing in flights:
        for n, z in enumerate(zs, 1):
            for x in xs:
                y = floor+n
                p.box(x, floor, z, x, y-1, z, 'minecraft:dark_oak_planks')
                p.stair(x, y, z, facing)
                p.stairs.append((x, y, z))
                p.hatch_clearance.update(((x, y+1, z), (x, y+2, z)))
    for y, z in ((-7, 4), (-2, 10), (3, 4), (8, 10)):
        p.box(-5, y, z, 3, y, z, 'minecraft:birch_planks' if y >= 3 else 'minecraft:spruce_planks')
        p.box(-5, y+1, z, 3, y+2, z, AIR)
    # On the gun landing, the lower staircase terminates at z5 beside the exit.
    # Clear landing headroom only, never carve away a stair's support afterward.
    for pos in p.hatch_clearance:
        if p.local_state(*pos) != AIR:
            raise UserError('An authored companionway has obstructed stair headroom: '+str(pos))
    # A second narrow emergency ladder has an attached backing at every level.
    p.box(1, -6, -16, 1, 8, -16, 'minecraft:stripped_dark_oak_log', axis='y')
    for y in range(-6, 9):
        p.put(0, y, -16, 'chipped:metal_ladder' if y in (-2, 3, 8) else 'minecraft:ladder', facing='west', waterlogged=False)
    # Gentle changes of sheer have actual stairs on the two-wide main route.
    for x in (2, 3, 4):
        for z, y, direction in ((-23, 9, 'north'), (-34, 10, 'north'), (24, 9, 'south'), (28, 10, 'south')):
            p.stair(x, y, z, direction)
            p.box(x, y+1, z, x, y+2, z, AIR)


def deck_equipment(p):
    # Windlass: two low bearings, a transverse drum and restrained handspikes.
    for side in (-1, 1):
        p.box(side*3, 14, -34, side*3, 15, -34, 'minecraft:dark_oak_log', axis='y')
    p.box(-2, 15, -34, 2, 15, -34, 'minecraft:stripped_spruce_log', axis='x')
    p.put(0, 16, -34, 'create:copper_valve_handle', facing='up')
    for x in (-2, 2):
        p.box(x, 14, -38, x, 15, -38, 'minecraft:stripped_dark_oak_log', axis='y')
    p.put(-3, 14, -29, 'minecraft:bell', facing='south', attachment='floor', powered=False)
    # A substantial coamed hatch belongs to the cargo-working waist, with
    # individual three-board grating panels and deliberate cross members.
    # The two-wide starboard passage at x3/x4 remains completely outside it.
    for x in range(-6, 1):
        for z in range(-12, -4):
            if x in (-6, 0) or z in (-12, -5):
                p.put(x, 9, z, 'minecraft:dark_oak_slab', type='bottom', waterlogged=False)
            elif x == -3 or z == -8:
                p.put(x, 8, z, 'minecraft:stripped_dark_oak_log', axis='x' if z == -8 else 'z')
            else:
                p.put(x, 8, z, 'minecraft:oak_trapdoor' if x == -4 else 'minecraft:dark_oak_trapdoor',
                      facing='north', half='top', open=False, powered=False, waterlogged=False)
    # A stowed longboat is a small original clinker-like hull, not a summon.
    for z in range(12, 20):
        w = 1 if z in (12, 19) else 2
        p.box(-w, 10, z, w, 10, z, 'minecraft:dark_oak_slab', type='bottom', waterlogged=False)
        for side in (-1, 1):
            p.put(side*w, 11, z, 'minecraft:oak_stairs', facing='east' if side < 0 else 'west', half='bottom', shape='straight', waterlogged=False)
    for z in (14, 17):
        p.box(-1, 11, z, 1, 11, z, 'minecraft:spruce_slab', type='bottom', waterlogged=False)
    for z in (13, 18):
        p.box(-4, 9, z, 2, 9, z, 'minecraft:stripped_dark_oak_log', axis='x')
    # Articulated-looking timber boat booms with explicit separate small pulley.
    # No glue, moving huge hull, entity summoning or functionality claim.
    for z in (10, 19):
        p.spar((9, 9, z), (10, 22, z))
        p.spar((10, 22, z), (18, 20, z+1))
        p.rope((9, 13, z), (17, 20, z+1))
        p.rope((18, 20, z+1), (18, 12, z+1))
        # A solid timber sheave housing gives the single-family hanging fall a
        # real downward sturdy face; the other mod's pulley was no such anchor.
        p.put(18, 19, z+1, 'minecraft:dark_oak_log', axis='x')
    p.put(10, 10, 14, 'create:hand_crank', facing='east', waterlogged=False)
    p.put(11, 10, 14, 'create:shaft', axis='x', waterlogged=False)
    p.put(12, 10, 14, 'create:rope_pulley', axis='x')
    p.room('Tender tackle and boat booms', 'weather', (6, 8, 13), 'Believable structural boat handling; isolated native crank/pulley requires later commissioning')
    # Entry gate and low ship-side steps, not an impossible water-level jump.
    p.box(9, 9, -1, 10, 11, 1, AIR)
    for n in range(7):
        p.stair(11+n, 8-n, 0, 'west')
        p.put(11+n, 7-n, 0, 'minecraft:dark_oak_planks')
    p.box(17, 1, -1, 19, 1, 1, 'minecraft:dark_oak_slab', type='top', waterlogged=False)
    p.room('Boarding ladder and sea landing', 'weather', (8, 8, 0), 'A narrow external stair descends to a tender-height platform; hull gate connects to waist')
    for side in (-1, 1):
        x, z = side*12, -33
        p.spar((x, -4, z), (x, 2, z), 'minecraft:stripped_dark_oak_log')
        p.box(x-2, -3, z, x+2, -3, z, 'minecraft:iron_bars')
        p.put(x-2, -2, z, 'minecraft:iron_bars')
        p.put(x+2, -2, z, 'minecraft:iron_bars')
        p.rope((side*6, 14, -35), (x, 2, z))


def working_deck(p):
    """R3: distinct full-scale deck jobs, rather than a mostly empty platform."""
    # The main capstan stands forward of the cargo hatch. An actual native
    # crank and cog share their vertical axis; anchor hauling is not claimed.
    p.barrel(-5, 9, -18, 'up')
    p.put(-5, 10, -18, 'create:large_cogwheel', axis='y', waterlogged=False)
    p.put(-5, 11, -18, 'create:hand_crank', facing='up', waterlogged=False)
    for x, z, facing in ((-6, -18, 'east'), (-4, -18, 'west'), (-5, -19, 'south'), (-5, -17, 'north')):
        p.put(x, 10, z, 'minecraft:dark_oak_trapdoor', facing=facing, half='top', open=False, powered=False, waterlogged=False)
    for x in (-8, -2):
        p.box(x, 9, -20, x, 10, -20, 'minecraft:stripped_dark_oak_log', axis='y')
        p.put(x, 11, -20, 'minecraft:dark_oak_slab', type='bottom', waterlogged=False)
    p.chest(-8, 9, -17, 'Capstan gang: handspikes and mooring gear', ['minecraft:lead', 'minecraft:stick', 'minecraft:iron_nugget'])
    p.barrel(-8, 9, -19, 'south')
    p.put(-8, 10, -19, 'farm_and_charm:rope_knot', north=False, south=False, east=False, west=False)
    # Three working belaying stations, not rows of disconnected dangling ropes.
    # Each coil fitting rests on its own wood rail/cask in the refitting state.
    for side, start in ((-1, -24), (1, -18), (-1, 0)):
        x = side*8
        for z in range(start, start+7):
            floor = weather_floor(z)
            if z in (start, start+3, start+6):
                p.box(x, floor+1, z, x, floor+2, z, 'minecraft:dark_oak_fence')
                p.put(x, floor+3, z, 'minecraft:dark_oak_slab', type='bottom', waterlogged=False)
            else:
                p.put(x, floor+2, z, 'minecraft:dark_oak_fence')
            if z in (start+1, start+5):
                p.barrel(x-side, floor+1, z, 'up')
                p.put(x-side, floor+2, z, 'farm_and_charm:rope_knot', north=False, south=False, east=False, west=False)
    # Visible pump and water-handling jobs alongside, never in the main route.
    for x, z in ((7, -7), (-8, 14)):
        p.put(x, 9, z, 'create:mechanical_pump', facing='east', waterlogged=False)
        p.put(x+1, 9, z, 'create:hand_crank', facing='east', waterlogged=False)
        p.put(x, 10, z, 'create:fluid_pipe', down=True, up=False, north=False, south=True,
              east=False, west=False, waterlogged=False)
        p.put(x, 9, z+1, 'minecraft:water_cauldron', level=1, boiling=False)
        p.barrel(x-1, 9, z+1, 'south')
        p.chest(x-1, 9, z+2, 'Deck pump: clean buckets and maintenance', ['minecraft:bucket', 'minecraft:copper_ingot', 'create:wrench'])
    # A compact sailmaker's deck job, with canvas on an actual low workbench.
    # Small groups leave working gaps; there is no wall of opaque cargo.
    for z in (-2, -1, 0):
        p.table(-6, 9, z)
    p.put(-6, 10, -2, 'chipped:bundled_white_wool')
    p.put(-6, 10, -1, 'handcrafted:stackable_book', books=2, facing='east', seed=61)
    p.chair(-4, 9, -1, 'west')
    p.chest(-7, 9, 2, 'Deck sailmaker: topsail seam repair', ['minecraft:shears', 'minecraft:string', 'minecraft:white_wool'])
    for x, z, key in ((6, -10, 'chipped:spruce_crate'), (7, -10, 'chipped:spruce_crate'),
                       (6, -11, 'supplementaries:sack'), (6, -19, 'chipped:spruce_crate')):
        p.put(x, 9, z, key, **({'facing': 'south', 'open': False} if key.endswith('crate') else {'open': False, 'waterlogged': False}))
    p.barrel(7, 9, -11, 'up')
    p.put(7, 10, -11, 'farm_and_charm:rope_knot', north=False, south=False, east=False, west=False)
    # The companion is an obvious hatch/hood now, rather than a hole and one
    # unexplained upright. Preserve the complete two-wide stair headroom.
    for z in range(3, 12):
        p.put(-6, 9, z, 'minecraft:dark_oak_slab', type='bottom', waterlogged=False)
    for z in range(3, 9):
        p.put(0, 9, z, 'minecraft:dark_oak_slab', type='bottom', waterlogged=False)
    for x in (-6, 0):
        p.box(x, 9, 12, x, 11, 12, 'minecraft:stripped_dark_oak_log', axis='y')
    for x in range(-6, 1):
        for z in (10, 11, 12):
            p.put(x, 12, z, 'minecraft:dark_oak_slab', type='bottom', waterlogged=False)
    p.box(-6, 10, 9, -6, 11, 10, 'minecraft:glass')
    # The secondary ladder exits flush with the weather deck, with a short
    # coaming. It no longer reads as the lone head-high stump in the camera.
    for z in (-17, -15):
        p.put(0, 9, z, 'minecraft:dark_oak_slab', type='bottom', waterlogged=False)
    p.put(-1, 9, -16, 'minecraft:dark_oak_slab', type='bottom', waterlogged=False)
    # The boat stays between the stairways. Its cradle stops before the reserved
    # x3/x4 route; thwarts, stowed oars and the boat chest make its purpose clear.
    for z in (12, 19):
        p.box(-2, 9, z, 2, 9, z, 'minecraft:dark_oak_log', axis='x')
    for z in (14, 17):
        p.box(-1, 12, z, 1, 12, z, 'minecraft:spruce_slab', type='bottom', waterlogged=False)
    p.box(-3, 11, 13, -3, 11, 19, 'minecraft:dark_oak_fence')
    p.chest(-3, 9, 20, 'Longboat chest: oars and emergency provisions', ['minecraft:oak_boat', 'minecraft:lead', 'minecraft:bread', 'minecraft:compass'])
    # Command station is a group: wheel, binnacle, instrument locker and seats.
    p.barrel(-3, 16, 24, 'up')
    p.put(-3, 17, 24, 'supplementaries:globe_sepia', facing='south', powered=False, rotation=1, waterlogged=False)
    p.put(-2, 16, 27, 'handcrafted:dark_oak_side_table', facing='north', color='none', waterlogged=False)
    p.put(-2, 17, 27, 'supplementaries:hourglass', facing='up', light_level=0, waterlogged=False)
    p.chest(-3, 16, 38, 'Quarterdeck watch: sights and instruments', ['minecraft:spyglass', 'minecraft:compass', 'minecraft:clock'])
    for x in (-2, -1, 0):
        p.put(x, 16, 40, 'handcrafted:dark_oak_bench', facing='north', color='blue', shape='single', waterlogged=False)
    # A two-deep stern walk, two real doors and short knees, connected from the
    # great cabin. This is an accessible balcony, not an unreachable decoration.
    for x in range(-4, 5):
        for z in (46, 47, 48):
            p.put(x, 10, z, 'minecraft:dark_oak_planks')
        p.put(x, 11, 48, 'minecraft:stripped_dark_oak_log' if x in (-4, 0, 4) else 'minecraft:dark_oak_fence',
              **({'axis': 'y'} if x in (-4, 0, 4) else {}))
    for side in (-1, 1):
        for z in (45, 46, 47):
            p.put(side*4, 11, z, 'minecraft:dark_oak_fence')
        p.spar((side*3, 8, 44), (side*3, 10, 47), 'minecraft:stripped_dark_oak_log')
    for x in (0, 1):
        p.box(x, 11, 44, x, 12, 44, AIR)
        for half, y in (('lower', 11), ('upper', 12)):
            p.put(x, y, 45, 'minecraft:dark_oak_door', facing='south', half=half,
                  hinge='left' if x == 0 else 'right', open=False, powered=False)
    p.room('Captain’s stern balcony', 'weather', (2, 10, 47), 'Two-deep stern walk through paired usable doors; native opening/walking pending')
    for pos in p.hatch_clearance:
        if p.local_state(*pos) != AIR:
            raise UserError('Deck fitting intrudes into the two-wide companionway: '+str(pos))
    # Entire waist lane remains two-wide and two-high. Isolated props do not
    # award an exemption from the planned circulation requirement.
    for x in (3, 4):
        for z in range(-21, 24):
            floor = weather_floor(z)
            if any(p.local_state(x, floor+dy, z) != AIR for dy in (1, 2)):
                raise UserError('Deck job blocks the reserved two-wide waist lane: '+str((x, z)))
    p.detail_groups.extend(['Working waist: capstan/bitts, three belaying stations, two pump groups and sail repair bench',
                            'Large panelled cargo hatch, glazed companion hood and flush emergency-ladder coaming',
                            'Stowed longboat, cradle, thwarts, oars and emergency chest',
                            'Quarterdeck instrument/binnacle group and accessible stern balcony'])


def canvas(p, z, yard_y, radius, drop, *, loose, patch=False):
    # Clews are hauled higher than the belly. Cloth breathes aft in two axes;
    # this is neither a rectangle nor a stack of flat billboard sails.
    for x in range(-radius+1, radius):
        u = abs(x)/radius
        hanging = max(2, round(drop*(1-.48*u*u)))
        if not loose:
            hanging = 1+(1 if abs(x) % 5 < 2 else 0)
        for dy in range(1, hanging+1):
            v = dy/max(1, hanging)
            aft = round(3.2*(1-u*u)*math.sin(v*math.pi/2)+.6*math.sin(x/4))
            # Named repair patch and doubled seam, never random block noise.
            repaired = patch and -5 <= x <= -3 and 3 <= dy <= 5
            if dy % 4 == 0:
                key = 'chipped:patched_white_wool' if x % 8 == 0 else 'chipped:bundled_white_wool'
            else:
                key = 'chipped:knitted_white_wool' if x % 4 == 0 else 'minecraft:white_wool'
            if repaired:
                key = 'chipped:patched_light_gray_wool'
            p.put(x, yard_y-dy, z+aft, key)
        clew = (x, yard_y-hanging, z+round(3.2*(1-u*u)))
        if x in (-radius+1, radius-1):
            p.rope((x, yard_y, z), clew)
    # R2's many long clew-to-deck lines made a curtain of angular hanging loops.
    # Keep the local yard/clew attachment; lower running sheets are stowed at
    # authored belaying stations in the present docked/refitting sail state.


def rig(p):
    specs = ((-27, 36, 52, 61, ((33, 15, 7, False), (48, 11, 10, True), (57, 6, 2, False))),
             (2, 40, 57, 67, ((36, 18, 11, True), (53, 13, 12, True), (63, 7, 3, False))),
             (29, 31, 45, 52, ((29, 9, 2, False), (43, 7, 7, True))))
    for index, (z, lower, middle, top, yards) in enumerate(specs):
        # Slight aft rake, black mast bands, trestletrees and tapered topmasts.
        p.spar((0, -7, z), (0, top, z+3), 'minecraft:stripped_spruce_log')
        for y in range(9, lower-3):
            rake = round((y+7)/(top+7)*3)
            p.put(1, y, z+rake, 'minecraft:stripped_dark_oak_log', axis='y')
            if y % 9 == 0:
                p.put(0, y, z+rake, 'minecraft:dark_oak_log', axis='y')
        for cap, span in ((lower, 3), (middle, 1)):
            for x in range(-span, span+1):
                for dz in range(-1, 3):
                    if abs(x)+abs(dz) <= span+1:
                        p.put(x, cap, z+1+dz, 'minecraft:dark_oak_slab', type='top', waterlogged=False)
            p.box(-1, cap+1, z+1, 1, cap+1, z+1, 'minecraft:dark_oak_log', axis='x')
        # The lower forestay bears on a full timber fairlead at the forward
        # edge of the fighting top, rather than the thin side of its slab.
        p.put(0, lower, z, 'minecraft:stripped_spruce_log', axis='x')
        for side in (-1, 1):
            for dz in (-4, 1):
                # Wide lower channels carry distinct shroud feet and deadeyes.
                p.put(side*12, 7, z+dz, 'minecraft:dark_oak_slab', type='top', waterlogged=False)
                p.put(side*12, 8, z+dz, 'minecraft:dark_oak_fence')
                p.rope((side*12, 9, z+dz), (side, lower+1, z+2))
            for y in range(14, lower-1, 8):
                t = (y-9)/(lower-8)
                x = side*round(12-11*t)
                front, rear = round(z-4+6*t), round(z+1+t)
                p.rope((x, y, front), (x, y, rear))
        previous = -62 if index == 0 else specs[index-1][0]
        p.rope((0, lower+2, z+2), (0, 18 if index == 0 else 12, previous))
        if index > 0:
            p.rope((0, top, z+3), (0, specs[index-1][1], previous+1))
        for j, (y, radius, drop, loose) in enumerate(yards):
            p.spar((-radius, y, z), (radius, y, z), 'minecraft:stripped_spruce_log')
            for side in (-1, 1):
                if j < 2:
                    p.rope((side*radius, y, z), (0, min(top, y+8), z+2))
                if j == 0:
                    p.rope((side*radius, y, z), (side*10, 11, z+9))
            canvas(p, z, y, radius, drop, loose=loose, patch=index == 1 and j == 0)
        for x in range(1, 7-index):
            p.put(x, top+1, z+3+(1 if x > 3 else 0), 'minecraft:blue_wool')
    # A restrained triangular mizzen/driver shape, partially brailed forward.
    p.spar((0, 41, 27), (0, 23, 42), 'minecraft:stripped_spruce_log')
    for z in range(30, 41):
        top_y = round(41-(z-27)*1.2)
        for y in range(23, top_y):
            if z > 36 and y < 25:
                continue
            key = ('chipped:patched_white_wool' if z % 8 == 0 else 'chipped:ribbled_white_wool') if y % 4 == 0 else ('chipped:woved_white_wool' if z % 4 == 0 else 'minecraft:white_wool')
            p.put(1+round(math.sin((y-23)/max(1, top_y-23)*math.pi)), y, z, key)
    p.rope((0, 23, 42), (0, 16, 39))


def circulation(p):
    """Conservative block-grid inspection, never native collision/art acceptance."""
    # Enumerate only structural full blocks/stairs as walking support, rather
    # than allowing a route to cheat over furniture or cannon models.
    solids = {'minecraft:birch_planks', 'minecraft:spruce_planks', 'minecraft:dark_oak_planks',
              'minecraft:oak_planks', 'minecraft:oak_log', 'minecraft:oak_wood', 'minecraft:stripped_birch_log',
              'minecraft:stripped_oak_wood',
              'minecraft:dark_oak_log', 'minecraft:stripped_spruce_log', 'minecraft:stripped_dark_oak_log', 'minecraft:stripped_oak_log',
              'minecraft:dark_oak_stairs', 'minecraft:oak_stairs'}
    solids.update(TIMBER_FINISH.values())
    passable = {AIR, 'minecraft:ladder', 'chipped:metal_ladder', 'minecraft:blue_carpet', 'minecraft:dark_oak_door'}
    cells = set()
    for (wx, wy, wz), state in p.blocks.items():
        if state.split('[')[0] not in solids:
            continue
        x, z = wx-p.cx, wz-p.cz
        for _ in range((-p.rotation) % 4):
            x, z = -z, x
        y = wy-p.sea
        if p.local_state(x, y+1, z).split('[')[0] in passable and p.local_state(x, y+2, z).split('[')[0] in passable:
            cells.add((x, y, z))
    origin = (3, 8, 0)
    if origin not in cells:
        raise UserError('The planned weather-deck entry is obstructed')
    queue, reached = deque([origin]), {origin}
    while queue:
        x, y, z = queue.popleft()
        for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            for dy in (-1, 0, 1):
                target = x+dx, y+dy, z+dz
                if target in cells and target not in reached:
                    reached.add(target)
                    queue.append(target)
    missing = [room['name'] for room in p.rooms if tuple(room['local_anchor']) not in reached]
    if missing:
        raise UserError('Prototype has an unreachable room in the conservative block-grid check: '+', '.join(missing))
    return {'rooms_reached': len(p.rooms), 'reachable_support_cells': len(reached),
            'method': 'Two-high structural block grid with max one-block steps; doors treated as interactable when opened; native shapes/walking and visual review pending'}


def lower_hull_seal(p):
    """Closed-shell flood test; native water updates still require inspection."""
    start = (-14, -9, -46)
    sealed = {pos for pos in p.shell_cells if p.local_state(*pos).split('[')[0] in SEAL_BLOCKS}
    queue, seen = deque([start]), {start}
    while queue:
        pos = queue.popleft()
        for delta in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
            nxt = tuple(pos[i]+delta[i] for i in range(3))
            if (nxt in seen or nxt in sealed or not
                    (-14 <= nxt[0] <= 14 and -9 <= nxt[1] <= 0 and -46 <= nxt[2] <= 46)):
                continue
            seen.add(nxt)
            queue.append(nxt)
    for row in p.rooms:
        x, y, z = row['local_anchor']
        if row['deck'] in ('hold', 'berth') and (x, y+1, z) in seen:
            raise UserError('The authored lower hull does not seal '+row['name'])
    return {'method': 'Six-neighbor outside flood against protected full-block shell below sea level',
            'enclosed_low_deck_anchors': sum(row['deck'] in ('hold', 'berth') for row in p.rooms),
            'native_water_updates_pending': True}


def build(registry, origin=(0, 63, 0), rotation=0, backup='0'*64):
    if (not isinstance(origin, (tuple, list)) or len(origin) != 3 or
            any(type(v) is not int for v in origin) or not 20 <= origin[1] <= 200 or
            type(rotation) is not int or rotation not in range(4)):
        raise UserError('Use a finite integer origin and one of four quarter-turn rotations')
    p = ArtisticShip(registry, origin, rotation, backup)
    hull(p)
    upper_decks(p)
    interiors(p)
    living_details(p)
    deck_equipment(p)
    companionways(p)
    working_deck(p)
    rig(p)
    p.finish_ropes()
    review = circulation(p)
    review['rope_attachments'] = p.rope_proof
    review['materials'] = require_material_rule(p.blocks, NAME)
    review['lower_hull_seal'] = lower_hull_seal(p)
    p.features = ['Original station-authored fine-entry hull, tumblehome and rising sheer',
                  'Narrow convex glazed transom, wing galleries and restrained gilding',
                  'Twenty-eight unloaded structural broadside guns, zero entities',
                  'Two-wide switchback companionway and an attached secondary ladder',
                  'Asymmetric furnished captain cabin, crew berths/mess, galley, hold and isolated magazine',
                  'Tapered raked masts, distinct shrouds/ratlines, mostly furled courses and loose drying topsails',
                  'Tender-height boarding stair, stowed longboat and separate uncommissioned tackle',
                  'Authored capstan, pump, belaying, sail-repair and cargo working groups; commissioning pending',
                  'Clear two-wide waist lane, glazed companion hood and accessible stern balcony']
    p.landmark(NAME, 3, p.sea+9, 0, 'Harbor', p.features)
    for name, position, look_at in (
        ('bow', (0, 1, -76), (0, 19, -7)), ('stern', (0, 3, 61), (0, 14, 31)),
        ('broadside', (72, 6, -3), (0, 29, 0)), ('elevated three-quarter', (45, 43, -60), (0, 20, 0)),
        ('main deck', (5, 9, -20), (0, 14, 21)), ('captain cabin', (2, 11, 30), (-2, 12, 40)),
        ('gun deck', (2, 4, -27), (0, 5, 25)), ('hold', (2, -6, -20), (-2, -5, 21))):
        p.cameras.append({'name': name, 'local_position': list(position), 'local_look_at': list(look_at),
                          'required': 'Actual Minecraft screenshot; no rendered mockup substitutes'})
        wx, wz = p.world(position[0], position[2])
        tx, tz = p.world(look_at[0], look_at[2])
        dx, dy, dz = tx-wx, look_at[1]-position[1]-1.62, tz-wz
        p.cameras[-1].update(world_feet=[wx+.5, p.sea+position[1], wz+.5],
                             world_look_at=[tx+.5, p.sea+look_at[1], tz+.5],
                             yaw=round(math.degrees(math.atan2(-dx, dz)), 3),
                             pitch=round(-math.degrees(math.atan2(dy, math.hypot(dx, dz))), 3))
    return p, review


def revision_plans(plan, previous):
    """Exact state-only before/delta views; neither view is a live admission."""
    if (previous.get('format') != 'awft-native-settlement:1'
            or previous.get('world_path') != plan.registry['world_path']
            or str(previous.get('seed')) != str(plan.registry['seed'])
            or previous.get('commands')):
        raise UserError('The previous ship must be a command-free plan for this exact staging world')
    palette = previous.get('palette', [])
    rows = previous.get('blocks', [])
    if not palette or len(palette) > 8192 or not rows or len(rows) > MAX_BLOCKS:
        raise UserError('Previous prototype exceeds the bounded native plan shape')
    old = {}
    for row in rows:
        if (not isinstance(row, list) or len(row) != 4 or any(type(n) is not int for n in row)
                or not 0 <= row[3] < len(palette) or tuple(row[:3]) in old):
            raise UserError('Previous prototype has invalid or duplicate native positions')
        old[tuple(row[:3])] = palette[row[3]]
    changed = {pos: state for pos, state in plan.blocks.items() if old.get(pos, AIR) != state}
    changed.update({pos: AIR for pos in old if pos not in plan.blocks})
    # Reapply the same explicitly authored tags only in this disposable stage.
    # These are not inventory preservation or permanent-world admission rules.
    changed.update({pos: plan.blocks[pos] for pos in plan.tags})
    before, delta = deepcopy(plan), deepcopy(plan)
    before.blocks, before.tags = {pos: old.get(pos, AIR) for pos in changed}, {}
    delta.blocks, delta.tags = changed, {pos: tag for pos, tag in plan.tags.items() if pos in changed}
    return before, delta, {'changed_or_removed_positions': len(changed),
                           'removed_previous_positions': sum(pos not in plan.blocks for pos in old),
                           'new_positions_requiring_native_air_verification': sum(pos not in old for pos in changed),
                           'previous_unstable_rope_scope': [list(pos)+[state] for pos, state in sorted(old.items())
                                                           if pos in changed and state.split('[')[0] in
                                                           ('farm_and_charm:rope', 'supplementaries:rope', 'supplementaries:rope_buntings')],
                           'gate': 'Native verify the complete before plan before applying any delta. No assumed air is accepted without that check.'}


def prepare(home, *, staging_world, origin, rotation=0, survey_path=None,
            previous_plan=None, previous_sha256=None):
    """Write unique private files only. Never connect to a server or apply blocks."""
    layout = Layout(home)
    Storage(layout).reserve(32*1024**2)
    world = Path(staging_world).resolve()
    owner = read_json(layout.state/'artistic-owner.json', {})
    if (not world.is_dir() or not world.is_relative_to(layout.world.resolve())
            or owner.get('format') != 'awft-artistic-stage:1'
            or owner.get('owner_source') != str(REPO) or Path(owner.get('home', '')).resolve() != layout.home
            or not any(p.name == 'staging' for p in layout.home.parents)):
        raise UserError('Prototype requires the explicitly owned isolated artistic staging world')
    directory = layout.state/'settlement'
    registry = read_json(directory/'registry.json')
    if world != Path(registry['world_path']).resolve():
        raise UserError('Native staging registry must name this exact isolated world')
    backup = read_json(directory/'backup-receipt.json', {})
    if not backup.get('verified') or not re.fullmatch('[a-f0-9]{64}', str(backup.get('sha256', ''))):
        raise UserError('A verified source-world backup receipt is required')
    if backup['sha256'] != owner.get('backup_sha256'):
        raise UserError('Artistic staging ownership and verified backup differ')
    registry = deepcopy(registry)
    registry['world_path'] = str(world)
    p, review = build(registry, origin, rotation, backup['sha256'])
    previous, revision = None, None
    if previous_plan:
        previous_plan = Path(previous_plan).resolve()
        if (not previous_plan.is_relative_to(layout.staging) or not previous_plan.is_file()
                or previous_plan.stat().st_size > 16*1024**2
                or not re.fullmatch('[a-f0-9]{64}', str(previous_sha256))
                or digest(previous_plan) != previous_sha256):
            raise UserError('A revision requires the exact immutable previous staging plan and its reviewed SHA-256')
        previous = read_json(previous_plan)
        revision = revision_plans(p, previous)
    soundings = []
    if survey_path:
        survey = read_json(Path(survey_path))
        if str(survey.get('seed')) != str(registry['seed']):
            raise UserError('Staging survey belongs to another seed')
        for row in survey.get('samples', []):
            if 'ocean_floor_y' in row:
                soundings.append({'x': row['x'], 'z': row['z'], 'ocean_floor_y': row['ocean_floor_y']})
    geometry = json.dumps({'blocks': sorted((list(pos), state) for pos, state in p.blocks.items()),
                           'tags': sorted((list(pos), tag) for pos, tag in p.tags.items()),
                           'world_path': str(world), 'backup': backup['sha256'],
                           'previous_plan_sha256': previous_sha256}, separators=(',', ':')).encode()
    identity = hashlib.sha256(geometry).hexdigest()
    output = layout.staging/('artistic-ship-'+identity[:16])
    if output.exists():
        raise UserError('Preserve the immutable prior prototype output; use its existing manifest')
    serialized = [p] + (list(revision[:2]) if revision else [])
    allocation = sum(len(item.encoded().encode('utf-8')) for item in serialized)+2*1024**2
    if allocation > 32*1024**2:
        raise UserError('Combined immutable plans and bounded manifest exceed the reserved 32 MiB allocation')
    output.mkdir()
    result = p.save(output/'prototype.json')
    if revision:
        before, delta, scope = revision
        result.update(previous_plan_sha256=previous_sha256,
                      expected_before=before.save(output/'expected-before.json'),
                      native_delta=delta.save(output/'visual-delta.json'), revision=scope)
    result.update(format='awft-artistic-ship-prototype:1', name=NAME, geometry_sha256=identity,
                  source_sha256=digest(Path(__file__)), origin=list(origin), rotation=rotation,
                  bounded_allocation_bytes=allocation, detail_groups=p.detail_groups,
                  local_bounds=list(LOCAL_BOUNDS), deck_levels=DECKS, rooms=p.rooms, guns=p.guns,
                  circulation=review, cameras=p.cameras, references=list(REFERENCES),
                  sounding_samples=soundings, entities=0, commands=0,
                  status='STAGED SOURCE PLAN ONLY; artistic/native acceptance unverified',
                  deployment_scope='Isolated staging world only. No permanent reconstruction or fleet propagation.',
                  pending=['Host prior-state/depth/overlap admission and native placement in staging',
                           'Actual bow/stern/broadside/three-quarter/deck/cabin/gun/hold screenshots',
                           'Native walking, dry hull, supporting shapes and lighting checks',
                           'Visual critique and geometry revision before any wider fleet or permanent deployment',
                           'Separate usable tender and small hoist functional commissioning'])
    write_json(output/'manifest.json', result)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--home', type=Path, default=Path(r'D:\A World for Two'))
    parser.add_argument('--staging-world', type=Path, required=True)
    parser.add_argument('--origin', type=int, nargs=3, required=True, metavar=('X', 'SEA_Y', 'Z'))
    parser.add_argument('--rotation', type=int, choices=range(4), default=0)
    parser.add_argument('--survey', type=Path)
    parser.add_argument('--previous-plan', type=Path)
    parser.add_argument('--previous-sha256')
    args = parser.parse_args()
    result = prepare(args.home, staging_world=args.staging_world, origin=args.origin,
                     rotation=args.rotation, survey_path=args.survey, previous_plan=args.previous_plan,
                     previous_sha256=args.previous_sha256)
    print(json.dumps({key: result[key] for key in ('path', 'sha256', 'blocks', 'block_entities', 'status', 'expected_before', 'native_delta') if key in result}))
