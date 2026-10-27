"""Original, terrain-fitted Rosewater Castle refinement plans.

This module prepares an immutable *delta*, never installs it. The old keep,
inventories, beds and furniture remain in place. Changes to a narrow list of
inventory-free castle masonry are recorded with their exact previous state.
Every other completed block, including deliberately empty space, is fixed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

from control_room.common import Layout, UserError, atomic_write, digest, read_json, utcnow
from control_room.storage import Storage
from tools.settlement import Plan


CORE_SHA = '45e88a165ed60ce438ec5d87094ed476faeebdaa68693ae6d1835a11eeea6aeb'
BOUNDS = (1155, -1043, 1290, -919)
OLD_CASTLE = (1187, -1032, 1235, -984)
MAX_BLOCKS = 550_000
MAX_PLAN_BYTES = 32 * 1024**2
MAX_OUTPUT_BYTES = 64 * 1024**2
# Original furnishings are deliberately absent. A bed or fairy table is protected
# even if a future survey happens not to instantiate its block entity.
ADAPTABLE = frozenset({
    'minecraft:air', 'minecraft:stone', 'minecraft:stone_bricks',
    'minecraft:stone_brick_wall', 'minecraft:calcite', 'minecraft:polished_diorite',
    'minecraft:birch_planks', 'minecraft:spruce_planks', 'minecraft:dark_prismarine',
    'minecraft:dark_prismarine_stairs', 'minecraft:glass_pane',
})
PALETTE = {
    'wall': 'chipped:small_calcite_bricks',
    'stone': 'minecraft:stone_bricks',
    'trim': 'rechiseled:quartz_block_chiseled_pillar',
    'floor': 'chipped:tiled_calcite',
    'wood': 'minecraft:cherry_planks',
    'roof': 'mcwroofs:dark_prismarine_roof',
    'rose': 'minecraft:pink_terracotta',
    'rail': 'mcwfences:railing_quartz_wall',
    'pillar': 'chipped:ornate_calcite_pillar',
}


def inside(x, z, bounds):
    return bounds[0] <= x <= bounds[2] and bounds[1] <= z <= bounds[3]


def unpack(plan):
    palette = plan['palette']
    return {(x, y, z): palette[i] for x, y, z, i in plan['blocks']}


def sample_height(samples, x, z, *, fresh=False):
    """Interpolate only locally surveyed columns; never extrapolate a new wing."""
    points = sorted(samples, key=lambda pos: (pos[0]-x)**2 + (pos[1]-z)**2)[:4]
    if not points or math.hypot(points[0][0]-x, points[0][1]-z) > 8:
        raise UserError(f'Castle terrain is not surveyed near {(x, z)}')
    if fresh and any('ground_y' not in samples[pos] for pos in points):
        raise UserError('A fresh native ground_y survey is required for new castle land')
    if points[0] == (x, z):
        row = samples[points[0]]
        return row.get('ground_y', row['y'])
    weights = [1/max(.5, math.hypot(px-x, pz-z))**2 for px, pz in points]
    return round(sum(samples[pos].get('ground_y', samples[pos]['y'])*weight
                     for pos, weight in zip(points, weights))/sum(weights))


class CastlePlan(Plan):
    """World-coordinate delta with immutable exclusions and a masonry audit trail."""
    def __init__(self, registry, survey, natural, backup, completed):
        super().__init__(registry, survey, (1211, -1008), backup, rotation=0)
        self.natural = {(row['x'], row['z']): row for row in natural['samples']}
        self.fixed = {}
        self.owners = {}
        self.old_core = unpack(completed[0][1])
        self.original_tags = set()
        for name, plan in completed:
            for pos, state in unpack(plan).items():
                self.fixed[pos] = state
                self.owners.setdefault(pos, set()).add(name)
            self.original_tags.update(tuple(row['pos']) for row in plan.get('block_entities', []))
        self.protected.update(self.original_tags)
        for row in natural['samples']:
            self.protected.update(tuple(pos) for pos in row.get('block_entities', []))
        self.adaptations = {}
        self.rooms = []
        self.routes = []
        self.basins = []
        self.views = []
        self.terrain = []
        self.height_cache = {}
        self.zone = 'Rosewater Castle'

    def world(self, x, z):
        return x, z

    def height(self, x, z):
        # The new survey correctly sees the old keep's roof. Its natural, pre-core
        # surface must be used when assessing that keep's existing foundations.
        pos = x, z
        if pos not in self.height_cache:
            self.height_cache[pos] = (sample_height(self.natural, x, z) if inside(x, z, OLD_CASTLE)
                                      else sample_height(self.samples, x, z, fresh=True))
        return self.height_cache[pos]

    def state(self, key, **properties):
        if key not in self.native:
            raise UserError('Unregistered castle block ' + key)
        unknown = properties.keys() - self.native[key].keys()
        if unknown:
            raise UserError('Unknown castle block properties for ' + key + ': ' + ', '.join(sorted(unknown)))
        return super().state(key, **properties)

    def put(self, x, y, z, key, **properties):
        pos = x, y, z
        if not inside(x, z, BOUNDS) or not 48 <= y <= 132:
            raise UserError('Castle design exceeded its reviewed bounds: ' + str(pos))
        state = self.state(key, **properties)
        previous = self.fixed.get(pos)
        if previous == state:
            # Preserve the actual old block rather than resetting its native BE.
            self.blocks.pop(pos, None)
            self.tags.pop(pos, None)
            self.adaptations.pop(pos, None)
            return
        if pos in self.protected:
            raise UserError('Castle design would overwrite an existing block entity: ' + str(pos))
        if previous is not None:
            owned_masonry = (inside(x, z, OLD_CASTLE) and 57 <= y <= 100
                             and self.owners[pos] == {'core'}
                             and previous.split('[')[0] in ADAPTABLE)
            if not owned_masonry:
                raise UserError('Castle design intersects fixed completed construction: ' + str(pos))
            self.adaptations.setdefault(pos, {'position': list(pos), 'previous': previous,
                                              'reason': self.zone})
        super().put(x, y, z, key, **properties)

    def tag(self, x, y, z, nbt):
        if (x, y, z) in self.protected or (x, y, z) not in self.blocks:
            raise UserError('Castle NBT must belong to a newly placed, unprotected block')
        super().tag(x, y, z, nbt)

    def room(self, name, bounds, floor, ceiling, purpose, furnishing):
        self.zone = name
        self.rooms.append({'name': name, 'bounds': list(bounds), 'floor': floor,
                           'ceiling': ceiling, 'purpose': purpose, 'furnishings': list(furnishing)})

    def effective(self, pos):
        return self.blocks.get(tuple(pos), self.fixed.get(tuple(pos)))

    def route(self, name, points):
        """Record real standing positions, not decorative navigation promises."""
        self.routes.append({'name': name, 'standing_positions': [list(p) for p in points]})

    def validate(self):
        if not self.blocks or len(self.blocks) > MAX_BLOCKS:
            raise UserError('Castle delta is empty or exceeds its bounded placement count')
        if self.commands:
            raise UserError('Castle plans do not summon entities or issue console commands')
        if self.blocks.keys() & self.protected:
            raise UserError('Castle plan contains an existing block-entity position')
        traversable = {'minecraft:air', 'mcwdoors:cherry_classic_door', 'minecraft:oak_door'}
        for route in self.routes:
            previous = None
            for x, feet, z in route['standing_positions']:
                for dy in (0, 1):
                    state = self.effective((x, feet+dy, z))
                    if state is None or state.split('[')[0] not in traversable:
                        raise UserError(f"Blocked headroom on {route['name']} at {(x, feet+dy, z)}: {state}")
                floor = self.effective((x, feet-1, z))
                if floor is None or floor.split('[')[0] in {'minecraft:air', 'minecraft:water'}:
                    raise UserError(f"Missing walking surface on {route['name']} at {(x, feet-1, z)}")
                if previous is not None:
                    dx, dy, dz = abs(x-previous[0]), abs(feet-previous[1]), abs(z-previous[2])
                    if dx+dz != 1 or dy > 1:
                        raise UserError('Disconnected castle route: ' + route['name'])
                previous = x, feet, z
        for basin in self.basins:
            water = {tuple(p) for p in basin['water_positions']}
            for x, y, z in water:
                for neighbor in ((x-1,y,z), (x+1,y,z), (x,y,z-1), (x,y,z+1), (x,y-1,z)):
                    if neighbor in water:
                        continue
                    state = self.effective(neighbor)
                    if state is None or state.split('[')[0] in {'minecraft:air', 'minecraft:water'}:
                        raise UserError('Rosewater basin has an uncontained edge: ' + str(neighbor))

    def payload(self):
        self.validate()
        palette = sorted(set(self.blocks.values()))
        indices = {state: n for n, state in enumerate(palette)}
        blocks = [[x, y, z, indices[state]] for (x, y, z), state in sorted(
            self.blocks.items(), key=lambda item: (item[0][0]//16, item[0][2]//16,
                                                   item[0][1], item[0][0], item[0][2]))]
        return {'format': 'awft-native-settlement:1', 'name': 'Rosewater Castle: the Rose and Tide Palace',
                'created': utcnow(), 'seed': self.registry['seed'], 'world_path': self.registry['world_path'],
                'backup_sha256': self.backup, 'bounds': list(BOUNDS), 'palette': palette, 'blocks': blocks,
                'block_entities': [{'pos': list(pos), 'nbt': nbt} for pos, nbt in sorted(self.tags.items())],
                'commands': [], 'landmarks': self.landmarks,
                'coverage': {key: sorted(values) for key, values in sorted(self.uses.items())},
                'validation': 'Registry-checked design delta only. Native placement, circulation, lighting, '
                              'furniture behavior, performance and shader visual review remain unverified.'}


def foundation(p, bounds, floor, name, *, finish=None):
    x1, z1, x2, z2 = bounds
    heights = [p.height(x, z) for x in range(x1, x2+1, 4) for z in range(z1, z2+1, 4)]
    if min(heights) < floor-17 or max(heights) > floor+5:
        raise UserError('Castle foundation needs individual terrain review: ' + name)
    p.terrain.append({'name': name, 'bounds': list(bounds), 'floor': floor,
                      'surveyed_ground_range': [min(heights), max(heights)]})
    for x in range(x1, x2+1):
        for z in range(z1, z2+1):
            surface = p.height(x, z)
            edge = x in (x1, x2) or z in (z1, z2)
            for y in range(min(surface-2, floor), floor):
                p.put(x, y, z, 'minecraft:stone_bricks' if edge else 'minecraft:stone')
            p.put(x, floor, z, finish or PALETTE['floor'])


def shell(p, name, bounds, floor, floors, *, wall=PALETTE['wall'], roof=True):
    """Articulated shell; floor spacing is eight blocks, allowing tall rooms."""
    x1, z1, x2, z2 = bounds
    p.zone = name
    ceiling = floor+8*floors
    foundation(p, bounds, floor, name)
    p.box(x1, floor+1, z1, x2, ceiling+2, z2, 'minecraft:air')
    for y in range(floor+1, ceiling+1):
        trim = y == floor+1 or (y-floor) % 8 == 0
        for x in range(x1, x2+1):
            for z in (z1, z2):
                p.put(x, y, z, PALETTE['trim'] if trim else wall)
        for z in range(z1+1, z2):
            for x in (x1, x2):
                p.put(x, y, z, PALETTE['trim'] if trim else wall)
    for n in range(1, floors+1):
        p.box(x1+1, floor+8*n, z1+1, x2-1, floor+8*n, z2-1, PALETTE['wood'])
    # Buttresses and deep recessed window bays break long elevations.
    for z, facing, outside in ((z1, 'north', z1-1), (z2, 'south', z2+1)):
        for x in range(x1+3, x2-1, 6):
            for n in range(floors):
                sy = floor+8*n
                window(p, x, sy+3, z, facing)
                p.put(x, sy+2, outside, 'minecraft:quartz_slab', type='bottom', waterlogged=False)
                p.put(x, sy+3, z+(1 if facing == 'north' else -1), 'mcwwindows:pink_curtain',
                      facing=facing, tied='single')
        for x in (x1, x2):
            p.box(x, floor+1, outside, x, ceiling, outside, PALETTE['pillar'], axis='y')
        p.box(x1, ceiling+1, outside, x2, ceiling+1, outside,
              'mythrais:denticulated_cornice_stone', facing=facing, half='bottom',
              shape='straight', waterlogged=False)
    for x, facing, outside in ((x1, 'west', x1-1), (x2, 'east', x2+1)):
        for z in range(z1+4, z2-2, 7):
            for n in range(floors):
                window(p, x, floor+n*8+3, z, facing)
            p.put(outside, floor+1, z, 'mythrais:buttress_detailing_narrow_base_stone',
                  facing=facing, colour=0, mirrored=False)
            p.box(outside, floor+2, z, outside, ceiling-1, z,
                  'mythrais:buttress_detailing_narrow_middle_stone', facing=facing, colour=0, shape=0)
            p.put(outside, ceiling, z, 'mythrais:buttress_detailing_narrow_top_stone',
                  facing=facing, colour=0, mirrored=False)
    if roof:
        gable(p, bounds, ceiling+2)
    return ceiling


def gable(p, bounds, y, *, width_axis='x'):
    x1, z1, x2, z2 = bounds
    half = ((x2-x1) if width_axis == 'x' else (z2-z1))//2
    for n in range(half+1):
        if width_axis == 'x':
            for x, facing in ((x1+n, 'east'), (x2-n, 'west')):
                p.box(x, y+n, z1-1, x, y+n, z2+1, PALETTE['roof'],
                      facing=facing, half='bottom', shape='straight')
                for z in (z1, z2):
                    if n:
                        p.box(x, y, z, x, y+n-1, z, PALETTE['wall'])
        else:
            for z, facing in ((z1+n, 'south'), (z2-n, 'north')):
                p.box(x1-1, y+n, z, x2+1, y+n, z, PALETTE['roof'],
                      facing=facing, half='bottom', shape='straight')
    if width_axis == 'x':
        p.box(x1+half, y+half+1, z1-1, x1+half, y+half+1, z2+1,
              'minecraft:dark_prismarine_slab', type='bottom', waterlogged=False)


def window(p, x, y, z, facing, height=3):
    for n in range(height):
        p.put(x, y+n, z, 'mcwwindows:quartz_pane_window', facing=facing,
              part='base' if n == 0 else 'above' if n == height-1 else 'middle', windowstate='closed')


def door(p, x, floor, z, facing='north', width=2):
    for n in range(width):
        px, pz = (x+n, z) if facing in ('north', 'south') else (x, z+n)
        p.box(px, floor+1, pz, px, floor+3, pz, 'minecraft:air')
        for half, dy in (('lower', 1), ('upper', 2)):
            p.put(px, floor+dy, pz, 'mcwdoors:cherry_classic_door',
                  facing=facing, half=half, hinge='left' if n == 0 else 'right', open=False, powered=False)


def arch(p, x, y, z, *, axis='x', width=5, height=5):
    """A clear human-sized opening with actual stone jambs and shaped shoulders."""
    for n in range(-width//2+1, width//2+1):
        px, pz = (x+n, z) if axis == 'x' else (x, z+n)
        p.box(px, y+1, pz, px, y+height, pz, 'minecraft:air')
    half = width//2+1
    for side in (-half, half):
        px, pz = (x+side, z) if axis == 'x' else (x, z+side)
        p.box(px, y+1, pz, px, y+height, pz, PALETTE['pillar'], axis='y')
    if axis == 'x':
        p.box(x-half, y+height+1, z, x+half, y+height+1, z, PALETTE['trim'])
        for side, facing in ((-half+1, 'east'), (half-1, 'west')):
            p.put(x+side, y+height, z, 'minecraft:quartz_stairs',
                  facing=facing, half='top', shape='straight', waterlogged=False)
    else:
        p.box(x, y+height+1, z-half, x, y+height+1, z+half, PALETTE['trim'])


def passage(p, name, start, end, *, width=3, material=PALETTE['floor']):
    x1, floor, z1 = start
    x2, end_floor, z2 = end
    if floor != end_floor or (x1 != x2 and z1 != z2):
        raise UserError('Use individually fitted stair flights for an uneven castle passage')
    points = []
    length = abs(x2-x1)+abs(z2-z1)
    dx, dz = (0 if x1 == x2 else 1 if x2 > x1 else -1), (0 if z1 == z2 else 1 if z2 > z1 else -1)
    for n in range(length+1):
        x, z = x1+dx*n, z1+dz*n
        for offset in range(-(width//2), width-width//2):
            px, pz = (x+offset, z) if dz else (x, z+offset)
            p.put(px, floor, pz, material)
            p.box(px, floor+1, pz, px, floor+3, pz, 'minecraft:air')
        points.append((x, floor+1, z))
    p.route(name, points)


def stairs(p, name, x, floor, z, rise, facing, width=3):
    dx, dz = {'north': (0,-1), 'south': (0,1), 'east': (1,0), 'west': (-1,0)}[facing]
    points = [(x-dx, floor+1, z-dz)]
    for n in range(rise):
        px, pz, py = x+dx*n, z+dz*n, floor+n+1
        for offset in range(-(width//2), width-width//2):
            ax, az = (px+offset, pz) if dz else (px, pz+offset)
            p.put(ax, py, az, 'minecraft:quartz_stairs', facing=facing,
                  half='bottom', shape='straight', waterlogged=False)
            p.box(ax, py+1, az, ax, py+3, az, 'minecraft:air')
            p.put(ax, py-1, az, PALETTE['wall'])
        points.append((px, py+1, pz))
    topx, topz = x+dx*rise, z+dz*rise
    for offset in range(-(width//2), width-width//2):
        ax, az = (topx+offset, topz) if dz else (topx, topz+offset)
        p.put(ax, floor+rise, az, PALETTE['floor'])
        p.box(ax, floor+rise+1, az, ax, floor+rise+3, az, 'minecraft:air')
    points.append((topx, floor+rise+1, topz))
    p.route(name, points)


def chandelier(p, x, ceiling, z, small=False):
    p.put(x, ceiling-1, z, 'minecraft:chain', axis='y', waterlogged=False)
    p.put(x, ceiling-2, z, 'mcwlights:golden_small_chandelier' if small else 'mcwlights:golden_chandelier', lit=True)


def chair(p, x, y, z, facing='north', color='pink'):
    p.put(x, y, z, 'handcrafted:cherry_chair', facing=facing, color=color, waterlogged=False)


def table(p, x, y, z, width=2, depth=2, color='white'):
    for dx in range(width):
        for dz in range(depth):
            p.put(x+dx, y, z+dz, 'handcrafted:cherry_table', color=color,
                  shape='single', waterlogged=False)


def sofa(p, x, y, z, facing='north', width=3, color='pink'):
    for dx in range(width):
        p.put(x+dx, y, z, 'handcrafted:cherry_couch', facing=facing, color=color,
              shape='single' if width == 1 else 'left' if dx == 0 else 'right' if dx == width-1 else 'middle',
              waterlogged=False)


def bed(p, x, floor, z, color='pink'):
    for dx in range(2):
        for dz, part in ((0, 'foot'), (-1, 'head')):
            p.put(x+dx, floor+1, z+dz, 'handcrafted:cherry_fancy_bed', color=color, facing='north',
                  occupied=False, part=part, shape='left' if dx == 0 else 'right')
    for dx in (-1, 2):
        p.put(x+dx, floor+1, z-1, 'handcrafted:cherry_nightstand',
              color='none', facing='south', waterlogged=False)
        p.put(x+dx, floor+2, z-1, 'minecraft:candle', candles=1, lit=True, waterlogged=False)
    for dx in (-1, 2):
        for dz in (-2, 1):
            p.box(x+dx, floor+1, z+dz, x+dx, floor+5, z+dz, 'minecraft:cherry_fence')
    p.box(x-1, floor+5, z-2, x+2, floor+5, z+1, 'minecraft:pink_carpet')


def rug(p, bounds, floor, color='pink'):
    x1, z1, x2, z2 = bounds
    for x in range(x1, x2+1):
        for z in range(z1, z2+1):
            # Inlay, rather than a raised collision surface through walking routes.
            p.put(x, floor, z, 'minecraft:'+('white' if x in (x1,x2) or z in (z1,z2) else color)+'_wool')


def fireplace(p, x, floor, z):
    p.box(x-2, floor+1, z, x+2, floor+5, z+2, PALETTE['wall'])
    p.box(x-1, floor+1, z, x+1, floor+3, z+1, 'minecraft:air')
    p.put(x, floor+1, z+1, 'minecraft:campfire', facing='north', lit=True, signal_fire=False, waterlogged=False)
    for dx in (-1, 0, 1):
        p.put(x+dx, floor+1, z, 'minecraft:iron_bars', north=False, south=False,
              east=dx != 1, west=dx != -1, waterlogged=False)
    p.box(x-2, floor+4, z-1, x+2, floor+4, z-1, 'minecraft:quartz_slab', type='bottom', waterlogged=False)
    p.put(x, floor+5, z-1, 'minecraft:potted_red_tulip')


def refine_keep(p):
    p.zone = 'The preserved Rosewater keep'
    for (x, y, z), old in list(p.old_core.items()):
        if not inside(x, z, OLD_CASTLE) or not 68 <= y <= 85 or (x,y,z) in p.protected:
            continue
        if old == 'minecraft:stone_bricks':
            p.put(x, y, z, PALETTE['wall'])
    # Keep the existing two thrones, original royal bed, piano, fairy table, sign
    # and lighting. Carve only documented masonry/air to make their rooms usable.
    p.room('Great Hall and Rose Throne Room', (1202,-1014,1220,-996), 67, 74,
           'Preserved twin thrones and formal audiences', ['existing thrones', 'rose inlay', 'gold chandeliers'])
    p.room('The Old Royal Music Gallery', (1202,-1014,1220,-996), 74, 81,
           'Preserved royal bed, music and intimate reading', ['existing bed', 'existing piano', 'window seats'])
    for x in (1204, 1217):
        table(p, x, 68, -1004, 1, 1)
        p.put(x, 69, -1004, 'minecraft:potted_lily_of_the_valley')
    # Real stairs reach the previously inaccessible first floor, away from the bed.
    passage(p, 'Throne hall east stair approach', (1218,67,-1013), (1218,67,-1011), width=1)
    stairs(p, 'Original keep grand stair', 1218, 67, -1010, 7, 'south', width=2)
    passage(p, 'Music gallery landing', (1218,74,-1003), (1214,74,-1003), width=1)
    # New rear doors lead directly into the cloister court. Existing north entry
    # remains the primary approach from the village.
    passage(p, 'Keep rear garden passage', (1211,67,-996), (1211,67,-984), width=3)
    door(p, 1210, 67, -995, 'south')
    for cx, cz in ((1193,-1023), (1229,-1023), (1193,-993), (1229,-993)):
        old_tower_stair(p, cx, cz)
    # Dress the north entrance without touching its original waxed sign.
    # The original rose rows flank this two-wide entrance; keep their actual
    # stems and both halves rather than clearing them for a wider paving strip.
    passage(p, 'Village approach to original castle gate', (1211,67,-1043), (1211,67,-1016), width=2)
    arch(p, 1211, 67, -1036, width=5, height=6)
    for x in (1206,1216):
        p.box(x, 67, -1037, x, 72, -1037, PALETTE['pillar'], axis='y')
        p.put(x, 73, -1037, 'minecraft:lantern', hanging=False, waterlogged=False)
    p.views.append({'name':'Village approach reveal', 'position':[1211,70,-1042], 'looks_toward':[1224,95,-987]})


def old_tower_stair(p, cx, cz):
    p.zone = 'The four preserved keep towers'
    ring = [(cx-2+i,cz-2) for i in range(4)] + [(cx+2,cz-2+i) for i in range(4)]
    ring += [(cx+2-i,cz+2) for i in range(4)] + [(cx-2,cz+2-i) for i in range(4)]
    points = []
    for n in range(18):
        x,z = ring[n % len(ring)]
        nx,nz = ring[(n+1) % len(ring)]
        facing = 'east' if nx>x else 'west' if nx<x else 'south' if nz>z else 'north'
        y = 68+n
        p.put(x,y,z,'minecraft:quartz_stairs',facing=facing,half='bottom',shape='straight',waterlogged=False)
        p.box(x,y+1,z,x,y+3,z,'minecraft:air')
        points.append((x,y+1,z))
    p.route('Keep tower stair '+str((cx,cz)),points)
    # Each tower has an actual ground doorway facing the inner bailey.
    facing = 'east' if cx < 1211 else 'west'
    wallx = cx+(5 if cx<1211 else -5)
    p.box(wallx,68,cz-1,wallx,70,cz+1,'minecraft:air')
    p.box(min(wallx,cx),68,cz,min(wallx,cx)+abs(wallx-cx),70,cz,'minecraft:air')
    for floor in (73,79,85):
        # Usable lookout/reading landings, with one window on the outer facade.
        x = cx+(-1 if cx<1211 else 1)
        if floor == 85:
            # The original conical roof was solid. Hollow a small top chamber
            # beneath its retained outer shell rather than furnishing solid roof.
            for dx in range(-3,4):
                for dz in range(-3,4):
                    if math.hypot(dx,dz) <= 3.1:
                        p.box(cx+dx,86,cz+dz,cx+dx,88,cz+dz,'minecraft:air')
        chair(p,x,floor+1,cz,'south','white')
        ceiling = 89 if floor == 85 else floor+6
        p.put(cx,ceiling-1,cz,'minecraft:chain',axis='y',waterlogged=False)
        p.put(cx,ceiling-2,cz,'minecraft:lantern',hanging=True,waterlogged=False)
        window(p,cx,floor+2,cz-5,'north',height=2)
        p.room('Keep lookout '+str((cx,cz,floor)),(cx-3,cz-3,cx+3,cz+3),floor,min(89,floor+6),
               'A small reading room and view stop', ['quartz stair', 'reading chair', 'glazed slit'])


def library_wing(p):
    shell(p,'The Moonlit Library',(1160,-1022,1184,-984),67,2)
    # Double-height reading room at the south end; mezzanine remains around it.
    p.box(1165,75,-1007,1178,75,-989,'minecraft:air')
    for z in (-1008,-988):
        p.box(1164,76,z,1179,76,z,PALETTE['rail'],north=True,south=True,east=True,west=True,waterlogged=False)
    for x in (1164,1179):
        p.box(x,76,-1007,x,76,-989,PALETTE['rail'],north=True,south=True,east=True,west=True,waterlogged=False)
    for x in (1162,1182):
        for z in range(-1018,-986,3):
            p.box(x,68,z,x,72,z,'minecraft:bookshelf')
            p.box(x,76,z,x,80,z,'chipped:historical_oak_bookshelf')
    for z in (-1016,-1007,-995):
        table(p,1170,68,z,3,2)
        for x in (1170,1172):
            chair(p,x,68,z-1,'south','white'); chair(p,x,68,z+2,'north','white')
        p.put(1171,69,z,'supplementaries:book_pile',books=3,waterlogged=False)
    sofa(p,1166,68,-988,'north',color='pink')
    fireplace(p,1176,67,-986)
    # Large windows and a shared reading bay overlooking the gully.
    for z in (-1010,-996):
        table(p,1163,76,z,1,1)
        chair(p,1162,76,z,'east','pink')
    p.put(1170,76,-1017,'minecraft:cartography_table')
    p.put(1172,76,-1017,'supplementaries:globe',facing='south',powered=False,rotation=0,waterlogged=False)
    p.put(1175,76,-1017,'handcrafted:cherry_desk',facing='south',color='none',waterlogged=False)
    chair(p,1175,76,-1015,'north','white')
    p.room('Moonlit Library',(1161,-1021,1183,-985),67,83,'Double-height library and reading salon',
           ['book stacks','three reading tables','hearth','shared reading couch','window seats'])
    p.room('Atlas and Letters Gallery',(1165,-1020,1181,-1010),75,83,'Maps, correspondence and quiet study',
           ['cartography table','globe','writing desk','upper reading gallery'])
    # Three-wide stairs are visible from the keep entrance, rather than a ladder.
    passage(p,'West bailey connector',(1183,67,-1010),(1202,67,-1010),width=3)
    stairs(p,'Library grand stair',1168,67,-1012,8,'north')
    passage(p,'Library upper landing',(1168,75,-1020),(1176,75,-1020),width=1)
    chandelier(p,1172,83,-1001); chandelier(p,1172,83,-1015)
    # A six-block descent reaches the vaulted cellar; no inventory is removed.
    p.zone='The Scriptorium Cellars'
    p.box(1162,61,-1004,1176,61,-987,'minecraft:stone_bricks')
    p.box(1162,62,-1004,1176,65,-987,'minecraft:air')
    for z in (-1000,-996,-991):
        for x in (1162,1176):
            p.put(x,62,z,'minecraft:barrel',facing='south',open=False)
    p.chest(1163,62,-988,'Unwritten stories for two',['minecraft:book','minecraft:feather'])
    for x,z in ((1166,-999),(1173,-991)):
        p.put(x,66,z,'minecraft:chain',axis='y',waterlogged=False)
        p.put(x,65,z,'minecraft:lantern',hanging=True,waterlogged=False)
    # A discreet side stair behind the reading stacks reaches a real lower route.
    passage(p,'Cellar lower landing',(1178,61,-1006),(1178,61,-1004),width=1)
    stairs(p,'Library cellar stair',1178,61,-1003,6,'south',width=2)
    passage(p,'Cellar doorway',(1176,61,-1004),(1178,61,-1004),width=1)
    p.room('Scriptorium Cellars',(1162,-1004,1178,-987),61,66,'Quiet archive and stores beneath the library',
           ['sealed barrel stores','small writing chest','discreet stair'])


def ballroom_and_royal_wing(p):
    shell(p,'The Sea Glass Ballroom',(1240,-1028,1272,-995),67,2)
    # Deliberate double-height center, with a genuine walkable upper gallery.
    p.box(1245,75,-1019,1267,75,-999,'minecraft:air')
    rug(p,(1245,-1018,1267,-1000),67,'white')
    for x,z in ((1245,-1019),(1267,-1019),(1245,-999),(1267,-999)):
        p.box(x,68,z,x,81,z,PALETTE['pillar'],axis='y')
    for z in (-1020,-998):
        p.box(1245,76,z,1267,76,z,PALETTE['rail'],north=True,south=True,east=True,west=True,waterlogged=False)
    for x in (1244,1268):
        p.box(x,76,-1019,x,76,-999,PALETTE['rail'],north=True,south=True,east=True,west=True,waterlogged=False)
    for x in (1249,1263):
        chandelier(p,x,83,-1008)
    p.box(1248,68,-999,1264,68,-997,PALETTE['wood'])
    p.put(1252,69,-998,'xercamusic:piano',facing='north')
    chair(p,1252,69,-999,'south','white')
    for x in (1243,1268):
        sofa(p,x,68,-1005,'north',width=2,color='white')
    p.room('Sea Glass Ballroom',(1242,-1020,1270,-997),67,83,'Dancing, music and celebrations',
           ['marble inlay','raised piano stage','two chandeliers','interior viewing galleries','conversation sofas'])
    p.room('Ballroom Reception and Grand Stair',(1241,-1027,1271,-1020),67,83,
           'Formal reception and circulation',['broad paired stair flights','upper gallery'])
    passage(p,'East bailey connector',(1220,67,-1010),(1242,67,-1010),width=3)
    # Reception runs across the north of the ballroom, with two real upper routes.
    passage(p,'Ballroom west reception',(1242,67,-1020),(1242,67,-1024),width=1)
    passage(p,'Ballroom east reception',(1270,67,-1020),(1270,67,-1024),width=1)
    stairs(p,'Ballroom west stair',1243,67,-1024,8,'east',width=3)
    stairs(p,'Ballroom east stair',1269,67,-1024,8,'west',width=3)
    passage(p,'Ballroom upper north gallery',(1251,75,-1024),(1261,75,-1024),width=3)
    shell(p,'The Rose and Tide Royal Wing',(1240,-994,1272,-958),67,2)
    # A central gallery organizes distinct rooms, keeping three-block circulation.
    for floor in (67,75):
        p.box(1256,floor+1,-993,1256,floor+7,-959,PALETTE['wall'])
        for z in (-976,-966):
            p.box(1241,floor+1,z,1255,floor+7,z,PALETTE['wall'])
            p.box(1261,floor+1,z,1271,floor+7,z,PALETTE['wall'])
        passage(p,'Royal gallery '+str(floor),(1259,floor,-997),(1259,floor,-959),width=3)
        for z in (-986,-971,-962):
            door(p,1256,floor,z,'west')
            if z != -986:
                door(p,1261,floor,z,'east')
        door(p,1250,floor,-976,'south')
        door(p,1250,floor,-966,'south')
    # Ground-floor dining and staffed service rooms.
    table(p,1246,68,-988,4,8)
    for z in range(-988,-980,2):
        chair(p,1245,68,z,'east','white');chair(p,1250,68,z,'west','white')
    for x in range(1263,1271):
        p.put(x,68,-991,'farmersdelight:birch_cabinet',facing='south')
        if x%2==0:
            p.put(x,69,-991,'handcrafted:white_crockery_combo',facing='south',waterlogged=False)
    fireplace(p,1267,67,-979)
    p.room('Formal Dining Hall',(1241,-993,1271,-977),67,75,'Formal shared meals, with service access',
           ['long cherry dining table','dining chairs','crockery cabinets','hearth'])
    for x in range(1242,1254):
        p.put(x,68,-973,'farmersdelight:birch_cabinet',facing='south')
    p.put(1244,68,-973,'farmersdelight:stove',facing='south',lit=True)
    p.put(1244,69,-973,'farmersdelight:cooking_pot',facing='south')
    p.put(1248,69,-973,'farmersdelight:cutting_board',facing='south',waterlogged=False)
    table(p,1245,68,-970,4,2)
    p.chest(1263,68,-973,'The Rosewater pantry',['minecraft:bread','minecraft:carrot','minecraft:potato'])
    for x in (1265,1267,1269):
        p.put(x,68,-973,'minecraft:barrel',facing='south',open=False)
    p.room('Royal Kitchens',(1241,-975,1255,-967),67,75,'Working food preparation and castle service',
           ['stove and pot','cutting board','preparation island','cabinet run'])
    p.room('Pantry and Linen Stores',(1262,-975,1271,-967),67,75,'Food and table linen storage',
           ['provision chest','three barrels'])
    p.put(1243,68,-962,'minecraft:crafting_table')
    p.put(1245,68,-962,'minecraft:smithing_table')
    p.put(1247,68,-962,'minecraft:anvil',facing='north')
    p.put(1252,68,-962,'minecraft:barrel',facing='south',open=False)
    p.room('Castle Workshop and Armory',(1241,-965,1255,-959),67,75,'Repairs and empty guard equipment stores',
           ['crafting table','smithing table','anvil','empty storage barrel'])
    bed(p,1264,67,-961,'white')
    p.put(1269,68,-963,'handcrafted:cherry_cupboard',facing='west',type=1)
    p.room('Stewards Chamber',(1262,-965,1271,-959),67,75,'Castle staff accommodation',
           ['bed','wardrobe','service gallery access'])
    # Upstairs is private and intimate, retaining the older royal room in the keep.
    bed(p,1247,75,-988,'pink')
    rug(p,(1244,-985,1252,-979),75,'pink')
    sofa(p,1263,76,-987,'south',width=3,color='white')
    table(p,1265,76,-983,2,1)
    p.put(1265,77,-983,'minecraft:potted_red_tulip')
    p.room('Princess Suite and Private Salon',(1241,-993,1271,-977),75,83,'A shared royal retreat for KG and Sera',
           ['two-wide canopy bed','rose inlay','private sitting room','garden balcony'])
    for x in (1243,1245,1247):
        p.put(x,76,-972,'handcrafted:cherry_cupboard',facing='south',type=1)
    p.put(1252,76,-972,'handcrafted:cherry_desk',facing='south',color='none',waterlogged=False)
    chair(p,1252,76,-970,'north','pink')
    p.room('Dressing Room and Private Study',(1241,-975,1255,-967),75,83,'Clothes, letters and personal reading',
           ['wardrobes','writing desk','quiet chair'])
    basin(p,'The private wash pool',(1264,-973,1270,-969),75)
    p.put(1263,76,-969,'handcrafted:cherry_bench',facing='east',color='white',shape='single',waterlogged=False)
    p.room('Royal Bath',(1262,-975,1271,-967),75,83,'A small fully contained wash pool',
           ['sealed marble basin','changing bench'])
    bed(p,1246,75,-961,'purple')
    p.room('Lavender Guest Chamber',(1241,-965,1255,-959),75,83,'An intimate guest room',
           ['lavender bed','reading light'])
    p.put(1264,76,-962,'minecraft:lectern',facing='south',has_book=False,powered=False)
    p.put(1267,76,-962,'minecraft:bookshelf')
    chair(p,1269,76,-962,'west','white')
    p.room('Cabinet of Curiosities',(1262,-965,1271,-959),75,83,'Owner-filled discoveries and mementos',
           ['empty display lectern','bookcase','viewing chair'])
    for x,z in ((1248,-985),(1265,-985),(1248,-970),(1267,-962)):
        chandelier(p,x,75,z,small=True)
        chandelier(p,x,83,z,small=True)
    # East-facing balcony with two seats, actual doors and an unobstructed view.
    p.zone='The Rosewater sunset balcony'
    p.box(1273,75,-989,1276,75,-978,'minecraft:cherry_planks')
    for z in range(-989,-977):
        p.put(1276,76,z,PALETTE['rail'],east=True,west=True,north=True,south=True,waterlogged=False)
    for z in (-989,-978):
        p.box(1273,76,z,1275,76,z,PALETTE['rail'],east=True,west=True,north=True,south=True,waterlogged=False)
    door(p,1272,75,-984,'east')
    chair(p,1274,76,-982,'east','pink');chair(p,1274,76,-980,'east','pink')
    p.views.append({'name':'Private rose balcony for two','position':[1274,77,-984],'looks_toward':[1290,69,-985]})


def observatory(p):
    cx,cz,r,base,top=1281,-1016,7,67,103
    p.zone='The Star and Tide Observatory'
    for dx in range(-r,r+1):
        for dz in range(-r,r+1):
            distance=math.hypot(dx,dz)
            if distance>r+.2:
                continue
            x,z=cx+dx,cz+dz
            ground=p.height(x,z)
            for y in range(min(ground-1,base),base+1):
                p.put(x,y,z,PALETTE['stone'])
            for y in range(base+1,top+1):
                p.put(x,y,z,PALETTE['wall'] if distance>r-1.3 else 'minecraft:air')
            for floor in (76,85,94,103):
                p.put(x,floor,z,PALETTE['floor'])
    for y in (70,79,88,97):
        for x,z,facing in ((cx,cz-r,'north'),(cx+r,cz,'east'),(cx,cz+r,'south')):
            window(p,x,y,z,facing)
    for level in range(13):
        radius=max(0,r-level*.55)
        for dx in range(-r,r+1):
            for dz in range(-r,r+1):
                distance=math.hypot(dx,dz)
                if radius-1.2<distance<=radius+.2:
                    p.put(cx+dx,104+level,cz+dz,'minecraft:dark_prismarine')
    p.put(cx,117,cz,'minecraft:lightning_rod',facing='up',powered=False,waterlogged=False)
    ring=[(cx-4+i,cz-4) for i in range(8)]+[(cx+4,cz-4+i) for i in range(8)]
    ring += [(cx+4-i,cz+4) for i in range(8)]+[(cx-4,cz+4-i) for i in range(8)]
    positions=[]
    for n in range(36):
        x,z=ring[n%len(ring)];nx,nz=ring[(n+1)%len(ring)]
        facing='east' if nx>x else 'west' if nx<x else 'south' if nz>z else 'north'
        y=68+n
        p.put(x,y,z,'minecraft:quartz_stairs',facing=facing,half='bottom',shape='straight',waterlogged=False)
        p.box(x,y+1,z,x,y+3,z,'minecraft:air')
        positions.append((x,y+1,z))
    p.route('Observatory spiral stair',positions)
    for floor,name in ((67,'Celestial entry'),(76,'Tide chart room'),(85,'Reading tower'),(94,'Astronomers study'),(103,'Star chamber')):
        p.room(name,(cx-5,cz-5,cx+5,cz+5),floor,floor+9,'A usable tower room on the continuous stair',
               ['spiral stair','window view','writing or reading position'])
        p.put(cx,floor+1,cz,'handcrafted:cherry_desk',facing='east',color='none',waterlogged=False)
        chair(p,cx+2,floor+1,cz,'west','white')
        p.put(cx,floor+2,cz,'supplementaries:book_pile',books=2,waterlogged=False)
        chandelier(p,cx,floor+8,cz+2,small=True)
    passage(p,'Observatory entrance',(1270,67,-1016),(1281,67,-1016),width=3)
    p.landmark('Star and Tide Observatory',1281,104,-1016,'Castle',['Real internal spiral stair','Chart rooms','Aerial castle silhouette'])
    p.views.append({'name':'Observatory western village view','position':[1278,105,-1016],'looks_toward':[1120,70,-1120]})


def basin(p,name,bounds,floor):
    x1,z1,x2,z2=bounds
    water=[]
    p.zone=name
    p.box(x1,floor-2,z1,x2,floor-2,z2,'minecraft:quartz_block')
    for x in range(x1,x2+1):
        for z in range(z1,z2+1):
            if x in (x1,x2) or z in (z1,z2):
                p.put(x,floor-1,z,'minecraft:quartz_block')
                p.put(x,floor,z,'minecraft:quartz_block')
            else:
                p.put(x,floor-1,z,'minecraft:water',level=0)
                p.box(x,floor,z,x,floor+2,z,'minecraft:air')
                water.append([x,floor-1,z])
    p.basins.append({'name':name,'water_positions':water,'note':'No elevated spilling water source; solid bottom and rim.'})


def cloister_and_court(p):
    p.zone='The Rose Court'
    foundation(p,(1190,-983,1238,-954),67,'The Rose Court')
    p.box(1190,68,-983,1238,72,-954,'minecraft:air')
    for z in (-982,-957):
        for x in range(1194,1236,7):
            p.box(x,68,z,x,73,z,PALETTE['pillar'],axis='y')
            p.put(x,74,z,'mcwlights:golden_small_chandelier',lit=True)
    # Covered cloisters provide a meaningful loop around a central rose garden.
    for z1,z2 in ((-983,-978),(-959,-954)):
        p.box(1189,75,z1,1238,75,z2,'minecraft:quartz_slab',type='bottom',waterlogged=False)
        for x in range(1194,1236,7):
            arch(p,x,67,-978 if z1==-983 else -959,width=5,height=5)
    for x1,x2 in ((1189,1194),(1233,1238)):
        p.box(x1,75,-977,x2,75,-960,'minecraft:quartz_slab',type='bottom',waterlogged=False)
        for z in (-972,-965):
            arch(p,1194 if x1==1189 else 1233,67,z,axis='z',width=5,height=5)
    # Small scale reflection pool, surrounded by in-ground rose beds and seats.
    basin(p,'Court of the Two Roses',(1208,-973,1220,-965),67)
    for x1,z1,x2,z2 in ((1198,-974,1204,-964),(1225,-974,1230,-964)):
        rose_bed(p,(x1,z1,x2,z2),67)
    chair(p,1209,68,-976,'south','pink');chair(p,1211,68,-976,'south','pink')
    for x,z in ((1198,-979),(1228,-979),(1198,-957),(1228,-957)):
        p.put(x,68,z,'dawnoftimebuilder:marble_big_flower_pot',waterlogged=False)
    passage(p,'Keep to cloister arrival',(1211,67,-984),(1211,67,-978),width=3)
    passage(p,'North cloister promenade',(1193,67,-980),(1236,67,-980),width=3)
    passage(p,'East cloister promenade',(1236,67,-980),(1236,67,-956),width=3)
    passage(p,'South cloister promenade',(1236,67,-956),(1192,67,-956),width=3)
    passage(p,'West cloister promenade',(1192,67,-956),(1192,67,-980),width=3)
    passage(p,'Royal kitchen service connection',(1236,67,-970),(1243,67,-970),width=1)
    p.room('Rose Court Cloister',(1190,-983,1238,-954),67,75,'Sheltered gallery around a reflection garden',
           ['arcaded loop','rose parterres','contained pool','paired garden chairs'])
    p.landmark('The Rose Court',1214,68,-976,'Castle',['Arcaded garden walks','Water and roses','A shared quiet seat'])


def rose_bed(p,bounds,floor):
    x1,z1,x2,z2=bounds
    for x in range(x1,x2+1):
        for z in range(z1,z2+1):
            p.put(x,floor,z,'minecraft:grass_block',snowy=False)
            if x in (x1,x2) or z in (z1,z2):
                p.put(x,floor+1,z,'minecraft:azalea_leaves',distance=1,persistent=True,waterlogged=False)
            elif (x-x1)%3==1 and (z-z1)%3==1:
                p.put(x,floor+1,z,'minecraft:rose_bush',half='lower')
                p.put(x,floor+2,z,'minecraft:rose_bush',half='upper')
            else:
                p.put(x,floor+1,z,'minecraft:pink_tulip')


def wintergarden_and_chapel(p):
    # The gully is retained: this glass garden sits four blocks below the court.
    shell(p,'The Lower Rose Conservatory',(1176,-980,1187,-956),63,1,wall='minecraft:glass',roof=False)
    for dx in range(6):
        for x in (1176+dx,1187-dx):
            p.box(x,72+dx//2,-981,x,72+dx//2,-955,'minecraft:glass')
    rose_bed(p,(1178,-977,1180,-973),63)
    rose_bed(p,(1178,-964,1180,-959),63)
    chair(p,1183,64,-976,'west','white');chair(p,1183,64,-974,'west','white')
    p.put(1181,64,-969,'fairytales:fairy_connection_table')
    p.room('Lower Rose Conservatory',(1177,-979,1186,-957),63,71,'Glass winter roses and a quiet fairy meeting nook',
           ['rose beds','paired chairs','fairy connection table'])
    passage(p,'Conservatory lower walk',(1184,63,-976),(1184,63,-960),width=1)
    passage(p,'Conservatory entrance',(1184,63,-968),(1187,63,-968),width=1)
    stairs(p,'Court to lower wintergarden',1188,63,-968,4,'east',width=3)
    passage(p,'Wintergarden stair court landing',(1192,67,-968),(1193,67,-968),width=1)
    shell(p,'Chapel of the Two Lanterns',(1276,-974,1288,-944),67,1,roof=False)
    gable(p,(1276,-974,1288,-944),77)
    for z in range(-970,-947,5):
        for x in (1279,1284):
            p.put(x,68,z,'handcrafted:cherry_bench',facing='south',color='white',shape='single',waterlogged=False)
    p.box(1279,68,-947,1285,68,-946,PALETTE['trim'])
    p.put(1281,69,-946,'minecraft:lantern',hanging=False,waterlogged=False)
    p.put(1283,69,-946,'minecraft:lantern',hanging=False,waterlogged=False)
    p.put(1282,69,-947,'minecraft:potted_lily_of_the_valley')
    chandelier(p,1282,75,-958,small=True)
    p.room('Chapel of the Two Lanterns',(1277,-973,1287,-945),67,75,'A quiet reflective room for two',
           ['paired lantern shrine','garden-facing windows','cherry pews','flowers'])
    passage(p,'Royal chapel approach',(1270,67,-969),(1282,67,-969),width=1)
    passage(p,'Chapel center aisle',(1282,67,-971),(1282,67,-948),width=1)
    # A small hidden route is discovered from normal circulation, without a command.
    passage(p,'Conservatory hidden side walk',(1185,63,-960),(1185,63,-956),width=1)
    p.chest(1183,64,-958,'A rose for the road',['minecraft:rose_bush','minecraft:book'])


def gate_and_grounds(p):
    p.zone='The Southern Rose Gate'
    foundation(p,(1204,-953,1232,-932),67,'South gate approach')
    p.box(1205,68,-943,1231,84,-932,'minecraft:air')
    for x1,x2 in ((1205,1212),(1224,1231)):
        shell(p,'Rose Gate lodge',(x1,-943,x2,-932),67,2)
    p.box(1213,75,-943,1223,75,-932,PALETTE['floor'])
    p.box(1213,76,-943,1223,83,-943,PALETTE['wall'])
    p.box(1213,76,-932,1223,83,-932,PALETTE['wall'])
    p.box(1213,84,-943,1223,84,-932,PALETTE['wood'])
    arch(p,1218,67,-943,width=7,height=7)
    arch(p,1218,67,-932,width=7,height=7)
    for x in (1208,1227):
        chair(p,x,68,-940,'south','white')
        p.put(x,68,-935,'minecraft:barrel',facing='north',open=False)
    # A staffed guard lodge and an inhabited upper room, not inaccessible turrets.
    passage(p,'Rose gate central avenue',(1218,67,-953),(1218,67,-930),width=3)
    door(p,1212,67,-938,'east');door(p,1224,67,-938,'west')
    stairs(p,'West gate lodge stair',1208,67,-941,8,'south',width=1)
    stairs(p,'East gate lodge stair',1227,67,-941,8,'south',width=1)
    passage(p,'Gatehouse portrait corridor',(1209,75,-938),(1227,75,-938),width=1)
    door(p,1212,75,-938,'east');door(p,1224,75,-938,'west')
    p.room('Rose Gate guard rooms',(1206,-942,1230,-933),67,75,'Welcoming guard lodges and travel stores',
           ['seating','empty storage','real upper stairs'])
    p.room('Gatehouse upper gallery',(1206,-942,1230,-933),75,83,'Portrait promenade above the garden gate',
           ['linked upper chambers','village-facing windows'])
    for x in (1206,1230):
        chandelier(p,x,75,-936,small=True)
        chandelier(p,x,83,-936,small=True)
    chandelier(p,1218,84,-937,small=True)
    # Raised southern garden steps down one block from the natural plateau.
    p.zone='Rosewater formal grounds'
    # The chapel is a separate building. Garden clearance must never erase it.
    foundation(p,(1239,-953,1273,-921),68,'Eastern rose terrace')
    foundation(p,(1274,-941,1288,-921),68,'Gazebo terrace')
    p.box(1239,69,-953,1273,73,-921,'minecraft:air')
    p.box(1274,69,-941,1288,73,-921,'minecraft:air')
    basin(p,'The Rosewater mirror',(1244,-946,1265,-933),68)
    rose_bed(p,(1240,-931,1250,-923),68)
    rose_bed(p,(1267,-946,1273,-936),68)
    for x,z in ((1241,-950),(1269,-949),(1257,-926)):
        p.put(x,69,z,'dawnoftimebuilder:marble_big_flower_pot',waterlogged=False)
    # Paths leave substantial planted areas, with no rectangle of entity exhibits.
    passage(p,'Eastern terrace north walk',(1240,68,-950),(1273,68,-950),width=3)
    passage(p,'Eastern terrace chapel-side walk',(1273,68,-950),(1273,68,-940),width=1)
    passage(p,'Eastern terrace chapel turn',(1273,68,-940),(1285,68,-940),width=3)
    passage(p,'Eastern terrace south walk',(1253,68,-924),(1285,68,-924),width=3)
    passage(p,'Eastern terrace outer walk',(1285,68,-940),(1285,68,-924),width=3)
    for x,z in ((1240,-948),(1262,-948),(1283,-938),(1283,-936),(1275,-922),(1254,-922)):
        p.put(x,69,z,'minecraft:lantern',hanging=False,waterlogged=False)
    # The gazebo frames the garden and castle, with seating arranged for two.
    for x in range(1276,1285):
        for z in range(-934,-925):
            if abs(x-1280)+abs(z+930)<=6:
                p.put(x,68,z,PALETTE['floor'])
    for x,z in ((1277,-933),(1283,-933),(1277,-927),(1283,-927)):
        p.box(x,69,z,x,74,z,'minecraft:cherry_fence')
    for n in range(5):
        p.box(1275+n,75+n//2,-935+n,1285-n,75+n//2,-925-n,'minecraft:dark_prismarine_slab',type='bottom',waterlogged=False)
    chair(p,1279,69,-930,'north','pink');chair(p,1281,69,-930,'north','pink')
    table(p,1280,69,-932,1,1)
    p.put(1280,70,-932,'minecraft:potted_red_tulip')
    p.put(1280,74,-930,'minecraft:lantern',hanging=True,waterlogged=False)
    p.room('The Rosewater Gazebo',(1276,-934,1284,-926),68,75,'A romantic garden pause for KG and Sera',
           ['two chairs','flower table','layered teal canopy'])
    # Court/gate/terrace connections have proper changes of level.
    passage(p,'Gate to rose terrace lower landing',(1218,67,-930),(1237,67,-930),width=3)
    stairs(p,'Rose terrace single rise',1238,67,-930,1,'east',width=3)
    passage(p,'Rose terrace pool west walk',(1240,68,-930),(1241,68,-930),width=1)
    p.landmark('Rosewater Castle',1211,68,-1038,'Castle',
               ['Preserved old keep','Ballroom and royal apartments','Moonlit Library',
                'Usable observatory','Rose cloisters','Conservatory and reflective chapel'])
    p.landmark('Rosewater Gardens',1278,69,-930,'Gardens',['Reflection pool','Rose parterres','A private seat for two'])
    p.views.extend([
        {'name':'Rose court gate frame','position':[1218,70,-929],'looks_toward':[1211,92,-1008]},
        {'name':'Gardens and ballroom sunset','position':[1285,71,-925],'looks_toward':[1230,96,-996]},
    ])


def build(p):
    """Pure plan assembly. The caller still has to save, review and commission it."""
    for key in PALETTE.values():
        p.state(key)
    refine_keep(p)
    library_wing(p)
    ballroom_and_royal_wing(p)
    observatory(p)
    cloister_and_court(p)
    wintergarden_and_chapel(p)
    gate_and_grounds(p)
    return p


def prepare(home, destination=None):
    """Write ONLY content-addressed castle plan/manifest files, never plan.json.

    Requires the fresh native survey, the exact verified old core and current
    verified backup. It does not submit native commands, change configuration,
    replace generic receipt files, or mark any runtime acceptance as passed.
    """
    layout = Layout(Path(home))
    directory = layout.state/'settlement'
    target = directory if destination is None else Path(destination).resolve()
    if not target.is_relative_to(directory.resolve()):
        raise UserError('Castle design outputs must stay in the owned settlement directory')
    if target.suffix.lower() == '.json' or (target.exists() and not target.is_dir()):
        raise UserError('Choose a directory for immutable castle-specific outputs')
    fresh_path = directory/'castle-survey-0.6.5.json'
    fresh = read_json(fresh_path)
    if not fresh or fresh.get('report', {}).get('failures') != 0 or not fresh.get('report', {}).get('finished'):
        raise UserError('The completed native castle-survey-0.6.5.json is required')
    registry_path = directory/'registry.json'
    registry = read_json(registry_path)
    if not registry:
        raise UserError('The official native registry export is required')
    backup_path = directory/'backup-receipt.json'
    backup = read_json(backup_path, {})
    if not backup.get('verified') or len(backup.get('sha256', '')) != 64:
        raise UserError('The current verified complete-world backup receipt is required')
    core_path = directory/('master-'+CORE_SHA+'.json')
    if not core_path.is_file() or digest(core_path) != CORE_SHA:
        raise UserError('The exact immutable original settlement core is required')
    proof = read_json(directory/'core-verification-pass.json', {})
    if proof.get('plan_sha256') != CORE_SHA or proof.get('failures') != 0:
        raise UserError('Preserve the original core native verification receipt')
    natural_paths = sorted(directory.glob('terrain-before-core-*.json'))
    if len(natural_paths) != 1:
        raise UserError('Select the unique original pre-core natural terrain survey first')
    natural = read_json(natural_paths[0])
    completed_paths = [core_path, *sorted(directory.glob('pirate-port-master-*.json')),
                        *sorted(directory.glob('drawbridge-master-*.json'))]
    if len(completed_paths) < 3:
        raise UserError('The completed core, pirate port and drawbridge exclusions are required')
    completed = []
    for path in completed_paths:
        expected = path.stem.rsplit('-',1)[-1]
        if digest(path) != expected:
            raise UserError('An immutable construction master has changed: '+path.name)
        plan = read_json(path)
        if plan.get('seed') != registry['seed'] or plan.get('world_path') != registry['world_path']:
            raise UserError('A construction exclusion belongs to a different official world')
        completed.append(('core' if path == core_path else path.name, plan))
    p = CastlePlan(registry, fresh, natural, backup['sha256'], completed)
    # Keep all historical BE protections. A loaded-chunk survey may report fewer
    # instances later; that cannot revoke an earlier protection.
    protected_sources = [natural_paths[0], fresh_path]
    for path in (directory/'survey-after-core.json', directory/'south-bank-survey-before-ground-filter.json'):
        if path.is_file():
            protected_sources.append(path)
            for row in read_json(path)['samples']:
                p.protected.update(tuple(pos) for pos in row.get('block_entities', []))
    build(p)
    payload = p.payload()
    encoded = (json.dumps(payload, ensure_ascii=False, separators=(',',':'))+'\n').encode('utf-8')
    if len(encoded) > MAX_PLAN_BYTES:
        raise UserError('Split the castle into reviewed phases before native admission')
    sha = hashlib.sha256(encoded).hexdigest()
    plan_path = target/('rosewater-castle-plan-'+sha+'.json')
    manifest_path = target/('rosewater-castle-manifest-'+sha+'.json')
    adaptations = []
    for pos, value in sorted(p.adaptations.items()):
        final = p.blocks.get(pos)
        if final is not None and final != value['previous']:
            adaptations.append(value | {'replacement': final})
    manifest = {
        'format':'awft-castle-design:1', 'at':payload['created'], 'plan_sha256':sha,
        'status':'Design prepared; native placement and full acceptance pending',
        'plan_file':plan_path.name, 'bounds':list(BOUNDS), 'old_castle_adaptation_bounds':list(OLD_CASTLE),
        'placements':len(p.blocks), 'palette':len(payload['palette']), 'block_entities':len(p.tags),
        'entities_summoned':0, 'commands':0, 'rooms':p.rooms, 'routes':p.routes,
        'contained_water_features':p.basins, 'terrain_fitting':p.terrain,
        'suggested_visual_review_positions':p.views, 'coverage':payload['coverage'],
        'adapted_original_masonry':adaptations,
        'protected_existing_block_entities':len(p.protected),
        'preserved_original_features':['old keep and four towers','twin thrones','existing royal bed',
                                       'existing piano','fairy connection table','original waxed castle sign'],
        'sources':{path.name:digest(path) for path in [registry_path,fresh_path,natural_paths[0],
                                                     backup_path,*completed_paths,*protected_sources]},
        'acceptance':{'design_registry':'checked', 'bounded_masonry_exclusions':'checked',
                      'recorded_route_clearance':'checked', 'water_containment':'checked',
                      'native_placement':'pending', 'native_verification':'pending',
                      'full_room_access_and_furniture':'pending', 'restart_persistence':'pending',
                      'shader_visual_review_and_refinement':'pending', 'local_performance':'pending',
                      'cinematic_integration':'pending'},
    }
    manifest_bytes=(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
    if len(encoded)+len(manifest_bytes)>MAX_OUTPUT_BYTES:
        raise UserError('The bounded castle plan plus audit manifest exceeds its disk estimate')
    # The only disk allocation in prepare is these two immutable files. The guard
    # checks both volumes and the actual target drive before their first write.
    Storage(layout).reserve(MAX_OUTPUT_BYTES,target=target)
    target.mkdir(parents=True,exist_ok=True)
    for path,data in ((plan_path,encoded),(manifest_path,manifest_bytes)):
        if path.exists():
            if path.read_bytes()!=data:
                raise UserError('Refusing to replace an existing castle design artifact')
        else:
            atomic_write(path,data)
    return {'plan':str(plan_path),'manifest':str(manifest_path),'sha256':sha,
            'blocks':len(p.blocks),'rooms':len(p.rooms),'routes':len(p.routes),
            'adapted_original_masonry':len(adaptations),'status':'Prepared only; not installed'}


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--home',type=Path,default=Path(r'D:\A World for Two'))
    parser.add_argument('--destination',type=Path)
    args=parser.parse_args()
    print(json.dumps(prepare(args.home,args.destination)),flush=True)
