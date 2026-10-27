"""One shore-fitted quay/shipwright composition for private visual review.

The west-facing site is authored against the actual clean-world shore profile.
This writes bounded plans only: no server calls, world edits or claimed crane
commissioning. Houses never stand on a pile/deck or an interpolated water cell.
"""
from __future__ import annotations

import argparse
from collections import deque
import hashlib
import json
import math
from pathlib import Path
import re

from control_room.common import Layout, REPO, UserError, atomic_write, digest, read_json, utcnow, write_json
from control_room.storage import Storage
from tools.artistic_materials import material_runs, require_material_rule
from tools.artistic_ship import revision_plans
from tools.settlement import Plan


NAME = 'The West Quay and Wren Shipwright'
AIR = 'minecraft:air'
ORIGIN = (1214, 65, -1242)
BOUNDS = (-17, -16, -18, 9, 18, 14)
MAX_POSITIONS = 24_000
MAX_OUTPUT = 16*1024**2
NATURAL_DRY = {'minecraft:grass_block', 'minecraft:dirt', 'minecraft:coarse_dirt',
               'minecraft:sand', 'minecraft:gravel', 'minecraft:stone', 'minecraft:clay'}
REFERENCES = [
    {'url': 'https://www.rmg.co.uk/collections/objects/rmgc-object-108241',
     'use': 'Deptford dockyard depiction, 1775: waterfront stores and work spaces, not copied geometry'},
    {'url': 'https://thedockyard.co.uk/the-collections/historic-buildings/',
     'use': 'Chatham rope-making and dockyard organization; compact invented local workshop'},
    {'url': 'https://mysticseaport.org/explore/village-old/ship-chandlery/',
     'use': 'Later comparative chandlery equipment and practical maritime supplies'},
]


def rect(x1, z1, x2, z2):
    return {(x, z) for x in range(x1, x2+1) for z in range(z1, z2+1)}


def line(a, b):
    n = max(abs(b[0]-a[0]), abs(b[1]-a[1]))
    return [(round(a[0]+(b[0]-a[0])*i/max(n, 1)),
             round(a[1]+(b[1]-a[1])*i/max(n, 1))) for i in range(n+1)]


class HarborPlan(Plan):
    def __init__(self, registry, survey, backup, origin=ORIGIN):
        self.registry, self.native = registry, registry['blocks']
        self.cx, self.base, self.cz = origin
        self.rotation, self.backup = 0, backup
        self.blocks, self.tags, self.commands, self.landmarks = {}, {}, [], []
        self.features, self.uses, self.owners, self.required_ids = [], {}, {}, set()
        self.zone = NAME
        self.rows = {(row['x'], row['z']): row for row in survey.get('samples', [])}
        if not self.rows or len(self.rows) > 5000:
            raise UserError('A bounded actual native shoreline profile is required')
        report = survey.get('report', {})
        if report.get('status') != 'complete' or report.get('failures') != 0:
            raise UserError('The fresh shoreline survey did not finish successfully')
        if any(row.get('source') != 'actual generated native chunk surface' for row in self.rows.values()):
            raise UserError('Noise estimates are not an actual shoreline survey')
        self.protected = {tuple(pos) for row in self.rows.values() for pos in row.get('block_entities', [])}
        self.dry_foundations, self.piles, self.routes, self.camera_poses = [], [], [], []

    def state(self, key, **properties):
        self.required_ids.add(key)
        if key not in self.native or properties.keys()-self.native.get(key, {}).keys():
            raise UserError('Harbor requires an exact native registered block/property: '+key)
        return super().state(key, **properties)

    def put(self, x, y, z, key, **properties):
        if (any(type(n) is not int for n in (x, y, z)) or not
                (BOUNDS[0] <= x <= BOUNDS[3] and BOUNDS[1] <= y <= BOUNDS[4] and BOUNDS[2] <= z <= BOUNDS[5])):
            raise UserError('Harbor geometry exceeds its finite shore envelope: '+str((x, y, z)))
        wx, wz = self.world(x, z)
        pos = wx, self.base+y, wz
        if pos in self.protected:
            raise UserError('Harbor intersects an existing native block entity: '+str(pos))
        if wx >= 1224:
            raise UserError('The adjacent authored street is a hard exclusion')
        self.blocks[pos] = self.state(key, **properties)
        self.owners[pos] = self.zone
        self.uses.setdefault(key.split(':')[0], set()).add(self.zone)
        if len(self.blocks) > MAX_POSITIONS:
            raise UserError('Harbor exceeds the finite position bound')

    def tag(self, x, y, z, nbt):
        wx, wz = self.world(x, z)
        self.tags[wx, self.base+y, wz] = nbt

    def at(self, x, y, z):
        wx, wz = self.world(x, z)
        return self.blocks.get((wx, self.base+y, wz), AIR)

    def sampled(self, x, z, exact=False):
        wx, wz = self.world(x, z)
        if (wx, wz) in self.rows:
            return self.rows[wx, wz]
        if exact:
            raise UserError('A proposed pile needs its exact actual ocean-floor sounding: '+str((wx, wz)))
        nearest = min(self.rows.values(), key=lambda row: (row['x']-wx)**2+(row['z']-wz)**2)
        if math.hypot(nearest['x']-wx, nearest['z']-wz) > 3:
            raise UserError('Proposed dry footprint lies outside the fresh 4 m survey support')
        return nearest

    def plank(self, x, y, z):
        # Seven-board lengths meet crossbeams; the three-board transverse gores
        # have a dark caulking member. No arbitrary random texture substitution.
        if x % 8 == 0:
            key = 'chipped:stacked_dark_oak_planks' if z % 8 == 0 else 'chipped:detailed_dark_oak_planks'
        elif z % 4 == 0:
            key = 'chipped:nailed_dark_oak_planks'
        else:
            key = 'minecraft:spruce_planks'
        self.put(x, y, z, key)

    def paving(self, x, y, z):
        if x % 4 == 0:
            key = 'minecraft:stone_bricks' if z % 8 else 'minecraft:chiseled_stone_bricks'
        elif z % 8 == 0:
            key = 'minecraft:polished_andesite'
        else:
            key = 'minecraft:andesite'
        self.put(x, y, z, key)

    def pile(self, x, z, deck=-1):
        row = self.sampled(x, z, exact=True)
        bottom = int(row['ocean_floor_y'])-self.base
        if not self.base-16 <= row['ocean_floor_y'] <= self.base+deck:
            raise UserError('Pile depth is unsupported or exceeds the bounded shore design')
        self.piles.append({'world': [row['x'], row['ocean_floor_y'], row['z']],
                           'deck_y': self.base+deck, 'source': 'Exact native first-air-above-floor sounding; no seabed cell replaced'})
        for y in range(bottom, deck):
            key = 'minecraft:dark_oak_log' if (self.base+y) % 8 == 0 else 'minecraft:stripped_dark_oak_log'
            self.put(x, y, z, key, axis='y')

    def walking(self, name, cells, floor=0):
        for x, z in cells:
            for y in (floor+1, floor+2):
                state = self.at(x, y, z).split('[')[0]
                if state not in (AIR, 'minecraft:dark_oak_door'):
                    raise UserError('An authored harbor route is obstructed: '+name+' '+str((x, y, z)))
        self.routes.append({'name': name, 'local_floor_y': floor,
                            'world_feet': [[self.cx+x+.5, self.base+floor+1, self.cz+z+.5] for x, z in cells],
                            'scope': 'Planned two-high clearance; actual native walking remains pending'})

    def material_proof(self):
        proofs = [require_material_rule({pos: state for pos, state in self.blocks.items() if self.owners[pos] == zone}, zone)
                  for zone in sorted(set(self.owners.values()))]
        # Scope boundaries never excuse an uninterrupted >9 run across outdoor
        # paving, retaining work, pier boards or adjacent authored structures.
        if violations := [row for row in material_runs(self.blocks) if row['exceeds_nine']]:
            raise UserError('Complete harbor, including outdoor surfaces, exceeds nine: '+str(violations[:5]))
        self.global_max9 = {'scope': 'Every authored harbor position, including outdoor surfaces',
                            'positions': len(self.blocks), 'material_state_facing_ignored': True,
                            'maximum_allowed_run': 9, 'violations': []}
        return proofs

    def encoded(self):
        palette = sorted(set(self.blocks.values()))
        indices = {state: n for n, state in enumerate(palette)}
        output = {'format': 'awft-native-settlement:1', 'name': NAME, 'created': utcnow(),
                  'seed': self.registry['seed'], 'world_path': self.registry['world_path'],
                  'backup_sha256': self.backup, 'bounds': [min(p[0] for p in self.blocks), min(p[2] for p in self.blocks),
                                                          max(p[0] for p in self.blocks), max(p[2] for p in self.blocks)],
                  'palette': palette, 'blocks': [[*pos, indices[state]] for pos, state in sorted(self.blocks.items())],
                  'block_entities': [{'pos': list(pos), 'nbt': tag} for pos, tag in self.tags.items()],
                  'commands': [], 'landmarks': self.landmarks,
                  'coverage': {key: sorted(value) for key, value in self.uses.items()},
                  'validation': 'Source/staging proposal only. Dry-footprint admission, native supports/walking and graphical review are pending.'}
        raw = (json.dumps(output, separators=(',', ':'), ensure_ascii=False)+'\n').encode('utf-8')
        if len(raw) > MAX_OUTPUT-2*1024**2:
            raise UserError('Harbor plan plus bounded manifest exceeds the finite 16 MiB export allocation')
        return raw

    def save(self, path):
        atomic_write(path, self.encoded().decode('utf-8'))
        return {'path': str(path), 'sha256': digest(path), 'positions': len(self.blocks), 'explicit_nbt_tags': len(self.tags)}


def quay(p):
    p.zone = 'West-facing shore quay'
    # Follow the actual west shore: the bank recedes east near the northern tip.
    centers = []
    for a, b in zip(((8, -16), (6, -12), (6, -8), (4, -4), (3, 0), (1, 4)),
                    ((6, -12), (6, -8), (4, -4), (3, 0), (1, 4))):
        centers.extend(line(a, b))
    floor = set().union(*(rect(max(-1, x-2), z-1, min(9, x+2), z+1) for x, z in centers))
    floor |= rect(2, -8, 9, 1) | rect(0, 1, 3, 8)
    for x, z in sorted(floor):
        p.paving(x, 0, z)
    # A short retaining edge is below the pedestrian surface, not a wall hiding
    # the water. Only sampled-profile support estimates are used at this stage.
    for z in sorted({z for x, z in floor}):
        x = min(x for x, zz in floor if zz == z)
        row = p.sampled(x, z)
        bottom = max(-9, int(row['ocean_floor_y'])-p.base)
        for y in range(bottom, 0):
            key = ('minecraft:polished_basalt' if y % 4 == 0 else
                   'minecraft:stone_bricks' if z % 8 == 0 else 'minecraft:andesite')
            p.put(x, y, z, key, **({'axis': 'y'} if key.endswith('basalt') else {}))
    for x, z in ((7, -15), (4, -5), (3, 2)):
        p.box(x, 1, z, x, 2, z, 'minecraft:stripped_dark_oak_log', axis='y')
        p.put(x, 3, z, 'minecraft:lantern', hanging=False, waterlogged=False)
    # The clean route from the street's exact western endpoint is reserved.
    p.walking('Street to the west quay', [(x, z) for x in range(3, 10) for z in (0, 1)])
    p.walking('Clear east side of cargo shade', [(x, z) for x in (7, 8) for z in range(-12, 2)])
    p.walking('Quay to shipwright double door', [(x, z) for x in (0, 1) for z in range(1, 9)])
    p.landmark('West Quay Arrival', 6, p.base+1, 0, 'Harbor', ['West-facing shore fit', 'Pedestrian connection to the authored street'])


def pier_and_crane(p):
    p.zone = 'Finger pier, cargo apron and hoist'
    deck = rect(-16, -14, 4, -10) | rect(-17, -18, -12, -7) | rect(-10, -16, -3, -8)
    for x, z in sorted(deck):
        p.plank(x, -1, z)
    # Exact 4 m grid soundings, feet above the natural floor, no excavation.
    for x in (-14, -6, 2):
        for z in (-14, -10):
            p.pile(x, z)
        p.box(x, -2, -14, x, -2, -10, 'minecraft:stripped_oak_log', axis='z')
    # A two-wide step joins the lower working pier to the higher shore walk.
    for z in (-12, -11):
        p.put(4, 0, z, 'minecraft:spruce_stairs', facing='east', half='bottom', shape='straight', waterlogged=False)
        p.paving(5, 0, z)
    # Bollards and lamps sit along edges, never in the reserved center passage.
    for x, z in ((-14, -17), (-10, -10), (-2, -14), (2, -10)):
        p.put(x, 0, z, 'minecraft:dark_oak_fence')
        p.put(x, 1, z, 'minecraft:lantern', hanging=False, waterlogged=False)
    for x in (-15, -11, -3):
        p.put(x, 0, -14, 'minecraft:dark_oak_fence')
        p.put(x, 1, -14, 'minecraft:dark_oak_slab', type='top', waterlogged=False)
    # Two-leg timber crane and solid headstock. The physical native pulley is
    # deliberately stopped/uncommissioned; no decorative chain is claimed as a
    # functioning Create rope or an assembled moving ship.
    for z in (-16, -8):
        p.box(-6, 0, z, -6, 7, z, 'minecraft:stripped_spruce_log', axis='y')
        p.box(-6, 7, z, -3, 7, z, 'minecraft:dark_oak_log', axis='x')
    p.box(-6, 8, -16, -6, 8, -8, 'minecraft:stripped_oak_log', axis='z')
    p.box(-14, 8, -12, -5, 8, -12, 'minecraft:oak_log', axis='x')
    p.put(-10, 8, -12, 'chipped:nailed_dark_oak_planks')
    p.put(-13, 7, -12, 'create:rope_pulley', axis='z')
    for z in (-15, -14, -13):
        p.put(-13, 7, z, 'create:shaft', axis='z', waterlogged=False)
    p.put(-13, 7, -16, 'create:hand_crank', facing='north', waterlogged=False)
    # A separate access platform brings the operator within reach of the crank.
    for x, z in sorted(rect(-15, -18, -12, -15)):
        p.plank(x, 5, z)
    for x, z in ((-15, -18), (-15, -15), (-12, -18), (-12, -15), (-15, -17)):
        p.box(x, 0, z, x, 4, z, 'minecraft:stripped_spruce_log', axis='y')
    for y in range(0, 6):
        p.put(-16, y, -17, 'minecraft:ladder', facing='west', waterlogged=False)
    p.put(-13, 0, -11, 'chipped:spruce_crate', facing='south', open=False)
    p.chest(-14, 0, -10, 'Quayside hoist inspection kit', ['create:wrench', 'minecraft:lead', 'minecraft:iron_nugget'])
    p.sign(-14, 0, -9, ['WHARF HOIST', 'Crank / shaft / pulley', 'Commissioning pending', 'No loads overhead'])
    # An outward-facing fish-cleaning bench is separate from the cargo job.
    for x in (-16, -15):
        p.put(x, 0, -8, 'handcrafted:oak_counter', facing='south', counter='spruce_planks', type=1)
    p.put(-16, 1, -8, 'farmersdelight:cutting_board', facing='south', waterlogged=False)
    p.put(-15, 1, -8, 'handcrafted:terracotta_medium_pot')
    p.chest(-16, 0, -7, 'Harbor angler: clean tools and tackle', ['minecraft:fishing_rod', 'minecraft:shears', 'minecraft:bowl'])
    p.walking('Two-wide working-pier passage', [(x, z) for x in range(-12, 4) for z in (-12, -11)], -1)
    p.walking('Two-wide pier step and quay arrival', [(x, z) for x in (4, 5) for z in (-12, -11)])
    p.landmark('Wren Crane and Working Pier', -6, p.base, -11, 'Harbor',
               ['Hand-authored timber crane', 'Exact-sounding piles', 'Fishing and cargo workspaces', 'Functional commissioning remains pending'])


def workshop(p):
    p.zone = 'The Wren Shipwright workshop'
    footprint = rect(2, 3, 8, 12)-{(2, 3), (2, 4)}
    # This complete building must stand on native dry land. Coarse survey
    # interpolation does not award admission for the unsampled foundation cells.
    for x, z in sorted(footprint):
        row = p.sampled(x, z)
        if row.get('fluid') or row.get('block') not in NATURAL_DRY or not p.base-2 <= row['ground_y'] <= p.base:
            raise UserError('A workshop foundation has wet/altered/steep native survey support: '+str(p.world(x, z)))
        wx, wz = p.world(x, z)
        p.dry_foundations.append({'x': wx, 'z': wz, 'required_native_top': 'dry natural ground',
                                  'sample_world': [row['x'], row['z']], 'sample_first_air_y': row['ground_y'],
                                  'exact_sample': (wx, wz) in p.rows, 'native_per_cell_admission_pending': True})
        for y in range(int(row['ground_y'])-p.base, 0):
            p.put(x, y, z, 'minecraft:chiseled_stone_bricks' if z == 8 else
                  'minecraft:stone_bricks' if x in (2, 5, 8) else 'minecraft:cobblestone')
        p.plank(x, 0, z)
    boundary = {pos for pos in footprint if any((pos[0]+dx, pos[1]+dz) not in footprint for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)))}
    for x, z in sorted(boundary):
        for y in range(1, 5):
            if x in (2, 5, 8) and z in (3, 6, 9, 12):
                key, props = 'minecraft:stripped_dark_oak_log', {'axis': 'y'}
            elif y == 4:
                key, props = ('minecraft:oak_log', {'axis': 'x'}) if z in (3, 12) else ('minecraft:spruce_log', {'axis': 'z'})
            else:
                key, props = 'minecraft:mud_bricks', {}
            p.put(x, y, z, key, **props)
    for z in (7, 8):
        for half, y in (('lower', 1), ('upper', 2)):
            p.put(2, y, z, 'minecraft:dark_oak_door', facing='west', half=half,
                  hinge='left' if z == 7 else 'right', open=False, powered=False)
    for z in (5, 10):
        for y in (2, 3):
            p.put(2, y, z, 'minecraft:glass')
        p.put(2, 1, z, 'minecraft:dark_oak_trapdoor', facing='west', half='bottom', open=True, powered=False, waterlogged=False)
    for x in (4, 5, 6):
        p.put(x, 2, 12, 'minecraft:glass')
    # A loft covers only the aft half. The forward room retains a tall workshop
    # volume and a hanging fixture from an actual crossbeam.
    for x, z in sorted(rect(3, 9, 7, 11)):
        p.plank(x, 4, z)
    for x in range(3, 8):
        p.put(x, 5, 9, 'minecraft:dark_oak_fence')
    p.put(7, 5, 9, AIR)
    for n in range(4):
        p.put(7, 1+n, 5+n, 'minecraft:spruce_stairs', facing='south', half='bottom', shape='straight', waterlogged=False)
        p.put(7, n, 5+n, 'minecraft:spruce_planks')
    # Asymmetric roof with one transverse repaired seam, a small glazed panel,
    # distinct ridge caps and projecting eaves. No repeated long flat rectangle.
    heights = (0, 1, 2, 3, 4, 4, 3, 2, 1)
    for x, rise in enumerate(heights, 1):
        for z in range(2, 14):
            y = 5+rise
            if x in (5, 6):
                p.put(x, y, z, 'minecraft:dark_oak_slab' if z == 8 else 'minecraft:spruce_slab', type='top', waterlogged=False)
            else:
                # Pinned Macaw models rise toward EAST at their default
                # orientation and have a thin3/16 fascia, unlike the heavy
                # reversed vanilla stair faces seen in the actual R1 view.
                key = 'mcwroofs:dark_oak_planks_roof' if z == 8 else 'mcwroofs:spruce_planks_roof'
                p.put(x, y, z, key, facing='east' if x <= 4 else 'west', half='bottom', shape='straight')
    for z in (3, 12):
        for x in range(3, 8):
            for y in range(5, 5+heights[x-1]):
                p.put(x, y, z, 'minecraft:oak_log' if y == 6 else 'minecraft:mud_bricks', **({'axis': 'x'} if y == 6 else {}))
    p.box(3, 4, 6, 7, 4, 6, 'minecraft:oak_log', axis='x')
    p.put(4, 3, 6, 'minecraft:lantern', hanging=True, waterlogged=False)
    # Interior shop: usable crafting/repair benches and real storage, tools,
    # opened drawings implied by a chart table, with a separate clerical loft.
    p.put(4, 1, 4, 'minecraft:crafting_table')
    p.put(5, 1, 4, 'handcrafted:oak_drawer', facing='south', shape='single', type=3)
    p.put(5, 2, 4, 'handcrafted:stackable_book', books=1, facing='south', seed=9)
    p.put(6, 1, 4, 'minecraft:grindstone', face='floor', facing='south')
    p.put(3, 1, 10, 'handcrafted:oak_counter', facing='east', counter='spruce_planks', type=2)
    p.put(3, 2, 10, 'handcrafted:terracotta_thin_pot')
    p.chest(3, 1, 11, 'Shipwright: adzes, clamps and fastenings', ['minecraft:iron_axe', 'minecraft:iron_nugget', 'minecraft:stick', 'minecraft:shears'])
    p.put(6, 1, 11, 'minecraft:barrel', facing='west', open=False)
    p.put(6, 2, 11, 'supplementaries:sack', open=False, waterlogged=False)
    for z, part in ((10, 'foot'), (11, 'head')):
        p.put(5, 5, z, 'minecraft:blue_bed', facing='south', part=part, occupied=False)
    p.put(3, 5, 10, 'handcrafted:dark_oak_nightstand', facing='east', color='blue', waterlogged=False)
    p.put(3, 6, 10, 'minecraft:candle', candles=2, lit=True, waterlogged=False)
    p.put(7, 5, 11, 'minecraft:cartography_table')
    p.put(7, 6, 11, 'lfpirates:ship_in_bottle', facing='west', waterlogged=False)
    p.walking('Shipwright double entrance and workroom', [(x, z) for x in range(2, 7) for z in (7, 8)])
    p.walking('Shipwright loft landing', [(6, 10), (6, 11)], 4)
    p.landmark('The Wren Shipwright', 4, p.base+1, 7, 'Harbor',
               ['Small dry-land workshop', 'Asymmetric skylit roof', 'Repair benches and tool stores', 'Working loft and private bunk'])


def shore_work(p):
    p.zone = 'Boat repair ways'
    # An unfinished clinker boat is recognizably different from a whole sailing
    # ship: keel on three actual trestles, open frames, a few attached strakes.
    for z in (5, 9, 13):
        for x in (-5, -2):
            row = p.sampled(x, z)
            if row.get('fluid') or row.get('block') not in NATURAL_DRY:
                raise UserError('Repair trestles must rest on this dry bank')
            for y in range(int(row['ground_y'])-p.base, 0):
                p.put(x, y, z, 'minecraft:cobblestone')
            p.put(x, 0, z, 'minecraft:dark_oak_fence')
        p.box(-5, 1, z, -1, 1, z, 'minecraft:dark_oak_slab', type='top', waterlogged=False)
    # The first actual camera read R1's solid rows of stairs as a flat-roofed
    # stall and its disconnected fence tips as floating debris. This boat has
    # a true tapered sheer, open cavity, connected U frames and partial strakes.
    stations = ((3, 0), (4, 1), (5, 1), (6, 2), (7, 2), (8, 2),
                (9, 2), (10, 2), (11, 2), (12, 1), (13, 1), (14, 0))
    for z, width in stations:
        p.put(-3, 2, z, 'minecraft:spruce_slab' if z != 9 else 'minecraft:dark_oak_slab', type='top', waterlogged=False)
        if width == 0:
            p.box(-3, 3, z, -3, 4, z, 'minecraft:dark_oak_fence')
            continue
        for side in (-1, 1):
            x = -3+side*width
            p.put(x, 2, z, 'minecraft:oak_stairs', facing='east' if side < 0 else 'west', half='bottom', shape='straight', waterlogged=False)
            if side < 0 or z in (4, 5, 11, 12, 13):
                p.put(x, 3, z, 'minecraft:spruce_trapdoor' if z not in (8, 11) else 'minecraft:dark_oak_trapdoor',
                      facing='west' if side < 0 else 'east', half='bottom', open=True, powered=False, waterlogged=False)
        if z in (5, 8, 11):
            p.box(-4, 3, z, -2, 3, z, 'minecraft:dark_oak_slab', type='bottom', waterlogged=False)
            for x in (-5, -1):
                p.box(x, 2, z, x, 4, z, 'minecraft:dark_oak_fence')
    for z in (6, 7, 9, 10):
        for x in (-4, -3, -2):
            p.put(x, 3, z, AIR)
            p.put(x, 4, z, AIR)
    for y in range(int(p.sampled(-5, 3)['ground_y'])-p.base, 1):
        p.put(-5, y, 3, 'minecraft:cobblestone')
    p.put(-5, 1, 3, 'minecraft:crafting_table')
    p.put(-5, 2, 3, 'handcrafted:stackable_book', books=1, facing='west', seed=13)
    # Leaning timber/staves, a stopped native saw and a peg/fastening locker make
    # this a specific boatwright's job, without unsupported item entities.
    for y in range(int(p.sampled(-6, 7)['ground_y'])-p.base, 0):
        p.put(-6, y, 7, 'minecraft:cobblestone')
    p.put(-6, 0, 7, 'create:mechanical_saw', facing='up', axis_along_first=True, flipped=False)
    p.chest(-6, 0, 10, 'Boatwright: frames and seam fastenings', ['minecraft:iron_nugget', 'minecraft:string', 'minecraft:shears'])
    for z in (7, 9):
        row = p.sampled(-7, z)
        if row.get('fluid'):
            raise UserError('The boatwright timber rack needs the dry bank')
        for y in range(int(row['ground_y'])-p.base, 0):
            p.put(-7, y, z, 'minecraft:cobblestone')
        p.box(-7, 0, z, -7, 2, z, 'minecraft:oak_fence')
    p.put(-7, 2, 8, 'minecraft:oak_fence')
    p.put(-6, -1, 10, 'minecraft:cobblestone')
    p.put(-5, -1, 14, 'minecraft:cobblestone')
    p.put(-2, 0, 13, 'minecraft:cobblestone')
    p.put(-2, 1, 13, 'minecraft:barrel', facing='west', open=False)
    p.chest(-5, 0, 14, 'Boatwright: planks, pegs and seam repairs', ['minecraft:spruce_planks', 'minecraft:oak_boat', 'minecraft:iron_axe'])
    # The cargo awaiting a ship is two low coherent groups, not crates in every
    # walking cell. A small canvas shade attaches to real timber uprights.
    p.zone = 'Cargo shade on the paved quay'
    for x, z in ((3, -5), (3, -2), (6, -5), (6, -2)):
        p.box(x, 0, z, x, 3, z, 'minecraft:stripped_spruce_log', axis='y')
    for x, z in sorted(rect(3, -5, 6, -2)):
        p.put(x, 4, z, 'chipped:bundled_white_wool' if z == -3 else 'minecraft:white_wool')
    for x, z in ((4, -4), (5, -4), (4, -3)):
        p.put(x, 1, z, 'chipped:spruce_crate', facing='south', open=False)
    p.put(4, 2, -4, 'supplementaries:sack', open=False, waterlogged=False)
    p.put(5, 1, -3, 'minecraft:barrel', facing='west', open=False)
    p.put(6, 1, -4, 'minecraft:barrel', facing='up', open=False)
    p.sign(6, 2, -4, ['WREN SHIPWRIGHT', 'Repairs on the ways', 'Canvas / spars / cargo', 'West quay to port'])


def build(registry, survey, backup='0'*64, origin=ORIGIN):
    if tuple(origin) != ORIGIN:
        raise UserError('This composition is bound to the reviewed west-bank coast; relocation needs a new shoreline design')
    p = HarborPlan(registry, survey, backup, origin)
    quay(p)
    pier_and_crane(p)
    workshop(p)
    shore_work(p)
    proof = p.material_proof()
    # Routes are checked again against the final composite, after all props.
    for route in p.routes:
        for wx, wy, wz in route['world_feet']:
            for y in (int(wy), int(wy)+1):
                state = p.blocks.get((int(wx), y, math.floor(wz)), AIR).split('[')[0]
                if state not in (AIR, 'minecraft:dark_oak_door'):
                    raise UserError('A later detail obstructed the harbor route: '+route['name'])
    for name, feet, target in (
        ('quay and street connection', (1196, 68, -1270), (1219, 68, -1244)),
        ('working pier at eye level', (1200, 65, -1253), (1221, 68, -1244)),
        ('shipwright exterior', (1208, 66, -1241), (1219, 69, -1234)),
        ('shipwright workroom', (1217, 66, -1235), (1220, 67, -1238)),
        ('shipwright loft', (1220, 70, -1232), (1217, 70, -1232)),
        ('repair ways close view', (1207, 66, -1229), (1214, 68, -1235))):
        dx, dy, dz = target[0]-feet[0], target[1]-feet[1]-1.62, target[2]-feet[2]
        p.camera_poses.append({'name': name, 'world_feet': [feet[0]+.5, feet[1], feet[2]+.5],
                               'yaw': round(math.degrees(math.atan2(-dx, dz)), 3),
                               'pitch': round(-math.degrees(math.atan2(dy, math.hypot(dx, dz))), 3)})
    return p, proof


def prepare(home, *, survey_path, survey_sha256, previous_plan=None, previous_sha256=None):
    layout = Layout(home)
    Storage(layout).reserve(MAX_OUTPUT)
    owner = read_json(layout.state/'artistic-owner.json', {})
    if (owner.get('format') != 'awft-artistic-stage:1' or owner.get('owner_source') != str(REPO)
            or Path(owner.get('home', '')).resolve() != layout.home
            or not any(path.name == 'staging' for path in layout.home.parents)):
        raise UserError('Harbor export requires the explicitly owned private artistic staging home')
    registry = read_json(layout.state/'settlement'/'registry.json')
    if not Path(registry['world_path']).resolve().is_relative_to(layout.world.resolve()):
        raise UserError('The native registry does not name this isolated staging world')
    backup = read_json(layout.state/'settlement'/'backup-receipt.json', {})
    if (not backup.get('verified') or not re.fullmatch('[a-f0-9]{64}', str(backup.get('sha256', '')))
            or owner.get('backup_sha256') != backup['sha256']):
        raise UserError('Harbor staging requires the current verified owner-bound backup')
    survey_path = Path(survey_path).resolve()
    if (not survey_path.is_relative_to(layout.home) or not survey_path.is_file()
            or survey_path.stat().st_size > 4*1024**2 or digest(survey_path) != survey_sha256):
        raise UserError('Use the exact hash-bound fresh native west-shore profile in this staging home')
    p, materials = build(registry, read_json(survey_path), backup['sha256'])
    raw = p.encoded()
    revision = None
    if previous_plan:
        previous_plan = Path(previous_plan).resolve()
        if (not previous_plan.is_relative_to(layout.staging) or not previous_plan.is_file()
                or previous_plan.stat().st_size > MAX_OUTPUT or digest(previous_plan) != previous_sha256):
            raise UserError('A harbor revision requires the exact immutable previous staging plan and reviewed hash')
        revision = revision_plans(p, read_json(previous_plan))
    serialized = [p]+(list(revision[:2]) if revision else [])
    if sum(len(part.encoded()) for part in serialized)+2*1024**2 > MAX_OUTPUT:
        raise UserError('Combined harbor revision plans and bounded manifest exceed the 16 MiB allocation')
    identity = hashlib.sha256(raw+str(previous_sha256).encode()).hexdigest()
    output = layout.staging/('artistic-harbor-'+identity[:16])
    if output.exists():
        raise UserError('Preserve the immutable harbor prototype already exported')
    output.mkdir()
    path = output/'prototype.json'
    atomic_write(path, raw.decode('utf-8'))
    manifest = {'format': 'awft-artistic-harbor:1', 'status': 'STAGED SOURCE ONLY; NOT ADMITTED OR VISUALLY ACCEPTED',
                'name': NAME, 'created': utcnow(), 'path': str(path), 'sha256': digest(path),
                'source_sha256': digest(Path(__file__)), 'survey_sha256': survey_sha256,
                'backup_sha256': backup['sha256'], 'origin': list(ORIGIN), 'local_bounds': list(BOUNDS),
                'positions': len(p.blocks), 'explicit_nbt_tags': len(p.tags), 'entities': 0, 'commands': 0,
                'materials': materials, 'global_max9': p.global_max9,
                'routes': p.routes, 'piles': p.piles, 'dry_foundation_admission': p.dry_foundations,
                'camera_poses': p.camera_poses, 'references': REFERENCES,
                'hard_exclusions': ['Street starts at X1224; this plan ends X1223',
                                    'No building on water, pier, river channel or bridge span',
                                    'All fresh-profile existing block entities', 'Natural seabed cells below exact pile first-air heights'],
                'pending': ['Exact native before-state verification of all writes and every unsampled dry-foundation cell',
                            'Actual support/depth/walking/furniture/roof inspection',
                            'Real shader screenshots and critique before permanent reconstruction',
                            'Separate stopped-crane collision, power, load retention and safe restart commissioning']}
    if revision:
        before, delta, scope = revision
        manifest.update(previous_plan_sha256=previous_sha256,
                        expected_before=before.save(output/'expected-before.json'),
                        native_delta=delta.save(output/'visual-delta.json'), revision=scope)
    encoded = (json.dumps(manifest, indent=2, ensure_ascii=False)+'\n').encode('utf-8')
    if sum(len(part.encoded()) for part in serialized)+len(encoded) > MAX_OUTPUT:
        raise UserError('Combined harbor bundle exceeds the reserved finite output')
    atomic_write(output/'manifest.json', encoded.decode('utf-8'))
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--home', type=Path, required=True)
    parser.add_argument('--survey', type=Path, required=True)
    parser.add_argument('--survey-sha256', required=True)
    parser.add_argument('--previous-plan', type=Path)
    parser.add_argument('--previous-sha256')
    args = parser.parse_args()
    result = prepare(args.home, survey_path=args.survey, survey_sha256=args.survey_sha256,
                     previous_plan=args.previous_plan, previous_sha256=args.previous_sha256)
    print(json.dumps({key: result[key] for key in ('path', 'sha256', 'positions', 'explicit_nbt_tags', 'status')}))
