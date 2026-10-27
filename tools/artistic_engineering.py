"""Author a dry-land mill quarter from one immutable artistic-world checkpoint.

No command, world edit, launch, assembly or simulated functional result is issued.
Every physical target and additional commissioning cell has an authenticated
saved-state companion; a fresh native zero-difference admission is still required.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import tomllib
import uuid
import zipfile
from datetime import datetime, timezone

from control_room.common import UserError, digest, read_json, utcnow
from tools.artistic_materials import require_material_rule, require_outdoor_rule
from tools.playtest import guard
from tools.settlement_attractions import (
    AIR, BackupWorld, MOD_FILES, MOD_SHAS, NATURAL, VEGETATION, base, properties,
)


MIB = 1024**2
MAX_OUTPUT = 16*MIB
MAX_POSITIONS = 24000
ORIGIN = (1310, 67, -1000)
LOCAL_BOUNDS = (-7, -4, -12, 29, 14, 68)
WORLD_RESERVE = (1300, 59, -1020, 1340, 85, -928)
SPANS = tuple((9+8*n, 17+8*n) for n in range(6))
VOID = {AIR, 'minecraft:cave_air', 'minecraft:void_air'}
PLANTS = VEGETATION | {'minecraft:'+n for n in (
    'short_grass', 'tall_grass', 'fern', 'large_fern', 'dandelion', 'poppy',
    'cornflower', 'azure_bluet', 'oxeye_daisy', 'allium', 'pink_petals', 'snow')}
DRY_NATURAL = NATURAL - {'minecraft:water'}


def walk_columns(z):
    # A small existing oak shrub at1326/-955 remains in the garden; the
    # two-wide pedestrian path bends around it instead of deleting the leaves.
    return range(16, 20) if z in (42, 48) else (18, 19) if 43 <= z <= 47 else (16, 17)


class Quarter:
    def __init__(self, registry, snapshot, exclusions=(), origin=ORIGIN):
        self.registry, self.snapshot, self.origin = registry, snapshot, tuple(origin)
        self.blocks, self.tags, self.previous, self.clearance = {}, {}, {}, {}
        self.routes, self.rooms, self.cameras, self.sources = [], [], [], []
        self.systems, self.dry_columns, self.groups = {}, {}, {}
        self.group = 'Mill quarter'
        self.fixed = set()
        for name, plan, sha in exclusions:
            if plan.get('world_path') != registry['world_path'] or plan.get('seed') != registry['seed']:
                raise UserError('An authored exclusion belongs to another actual world')
            self.fixed.update(tuple(row[:3]) for row in plan['blocks'])
            self.sources.append({'name': name, 'sha256': sha, 'role': 'Exact authored exclusion, including air'})

    def world(self, pos):
        return tuple(pos[n]+self.origin[n] for n in range(3))

    def state(self, key, **props):
        native = self.registry['blocks'].get(key)
        if native is None:
            raise UserError('Unregistered exact engineering block '+key)
        for name, value in props.items():
            if str(value).lower() not in native.get(name, ()):
                raise UserError('Unregistered engineering property '+key+' '+name+'='+str(value))
        return key+('['+','.join(k+'='+str(v).lower() for k, v in sorted(props.items()))+']' if props else '')

    def put(self, x, y, z, key, *, replace=False, **props):
        local = x, y, z
        if any(type(v) is not int for v in local) or any(not LOCAL_BOUNDS[n] <= local[n] <= LOCAL_BOUNDS[n+3] for n in range(3)):
            raise UserError('Engineering exceeded its finite local envelope: '+str(local))
        pos = self.world(local)
        if any(not WORLD_RESERVE[n] <= pos[n] <= WORLD_RESERVE[n+3] for n in range(3)):
            raise UserError('Engineering escaped the reviewed dry-land reserve')
        if pos in self.fixed:
            raise UserError('Engineering intersects authored construction or reserved air: '+str(pos))
        old = self.snapshot.state(pos)
        if pos in self.snapshot.protected or base(old) not in DRY_NATURAL:
            raise UserError('Preserve saved block entity, water, tree or unreviewed structure: '+str(pos)+' '+old)
        state = self.state(key, **props)
        prior = self.blocks.get(pos)
        if prior is not None and prior not in (AIR, state) and not replace:
            raise UserError('Overlapping authored engineering roles: '+str(local)+' '+prior+' -> '+state)
        self.blocks[pos], self.previous[pos] = state, old
        self.tags.pop(pos, None)
        self.groups.setdefault(self.group, set()).add(pos)
        if len(self.blocks) > MAX_POSITIONS:
            raise UserError('Split the bounded engineering installation')

    def box(self, x1, y1, z1, x2, y2, z2, key, **props):
        for x in range(x1, x2+1):
            for z in range(z1, z2+1):
                for y in range(y1, y2+1):
                    self.put(x, y, z, key, **props)

    def ground(self, x, z):
        wx, _, wz = self.world((x, 0, z))
        if (wx, wz) in self.dry_columns:
            return self.dry_columns[wx, wz]-self.origin[1]
        for y in range(self.origin[1]+14, 55, -1):
            key = base(self.snapshot.state((wx, y, wz)))
            if key in VOID | PLANTS:
                continue
            if key not in DRY_NATURAL or key in {'minecraft:lava'}:
                raise UserError('A foundation is wet, wooded or already authored: '+str((wx, y, wz))+' '+key)
            self.dry_columns[wx, wz] = y
            return y-self.origin[1]
        raise UserError('No shallow authenticated dry foundation')

    def foundation(self, x, z, top=0, *, deck=False):
        ground = self.ground(x, z)
        raised_timber_landing = deck and top == 3
        if ground > top or top-ground > (6 if raised_timber_landing else 4):
            raise UserError('Relocate instead of cutting terrain or making a deep platform: '+str(self.world((x, top, z))))
        for y in range(ground, top):
            # Real panel joints and masonry footings, not state-only rotations.
            if z % 4 == 0:
                material = 'minecraft:polished_deepslate' if x % 4 == 0 else (
                    'minecraft:chiseled_stone_bricks' if z % 8 == 0 else 'minecraft:cobbled_deepslate')
            else:
                material = 'minecraft:polished_andesite' if x % 4 == 0 else 'minecraft:stone_bricks'
            # Authored kinetic shafts run beneath the small station terraces;
            # masonry must surround them, never replace a transmission block.
            if raised_timber_landing:
                # Small open timber station landings, not a filled six-high
                # masonry pedestal. Four-block pier spacing and real beams.
                if x % 4 or z % 4:
                    continue
                material = 'minecraft:stripped_spruce_log' if y < top-1 else 'minecraft:polished_andesite'
            if not base(self.blocks.get(self.world((x, y, z)), '')).startswith('create:'):
                self.put(x, y, z, material, **({'axis': 'y'} if material == 'minecraft:stripped_spruce_log' else {}))
        if base(self.blocks.get(self.world((x, top, z)), '')).startswith('create:'):
            return
        if deck:
            self.plank(x, top, z)
        else:
            if z % 8 == 0:
                material = 'minecraft:polished_deepslate' if x % 4 == 0 else 'minecraft:polished_andesite'
            else:
                material = ('minecraft:mossy_cobblestone' if z % 4 == 0 else 'minecraft:andesite') if x % 4 == 0 else 'minecraft:cobblestone'
            self.put(x, top, z, material)

    def floor(self, x1, z1, x2, z2, top=0, *, deck=False):
        for x in range(x1, x2+1):
            for z in range(z1, z2+1):
                self.foundation(x, z, top, deck=deck)
                self.box(x, top+1, z, x, top+3, z, AIR)
        if deck and top == 3:
            for z in range(z1, z2+1):
                if z % 4:
                    continue
                for x in range(x1, x2+1):
                    if base(self.blocks.get(self.world((x, top-1, z)), '')).startswith('create:'):
                        continue
                    self.put(x, top-1, z, 'minecraft:oak_log' if x % 8 else 'minecraft:polished_andesite',
                             replace=True, **({'axis': 'x'} if x % 8 else {}))

    def plank(self, x, y, z, *, replace=False):
        if z % 8 == 0:
            key, props = ('minecraft:polished_deepslate', {}) if x % 4 == 0 else ('minecraft:oak_log', {'axis': 'x'})
        else:
            key, props = ('minecraft:dark_oak_planks' if x % 4 == 0 else 'minecraft:spruce_planks'), {}
        self.put(x, y, z, key, replace=replace, **props)

    def chest(self, pos, title, items=()):
        self.put(*pos, 'minecraft:chest', replace=True, facing='south', type='single', waterlogged=False)
        rows = []
        for slot, (key, count) in enumerate(items):
            if key not in self.registry['items'] or not 1 <= count <= 64:
                raise UserError('Invalid bounded engineering starter item '+key)
            rows.append('{Slot:'+str(slot)+'b,id:'+json.dumps(key)+',count:'+str(count)+'}')
        self.tags[self.world(pos)] = '{CustomName:'+json.dumps(json.dumps({'text': title}))+',Items:['+','.join(rows)+']}'

    def sign(self, pos, lines):
        self.put(*pos, 'minecraft:oak_sign', replace=True, rotation=8, waterlogged=False)
        values = [json.dumps(json.dumps({'text': text, 'color': 'dark_green'})) for text in (lines+['']*4)[:4]]
        self.tags[self.world(pos)] = '{is_waxed:1b,front_text:{messages:['+','.join(values)+'],color:"brown",has_glowing_text:0b}}'

    def route(self, name, local):
        points = [self.world(p) for p in local]
        for x, y, z in points:
            for dy in (0, 1):
                pos = x, y+dy, z
                state = self.blocks.get(pos, self.snapshot.state(pos))
                if base(state) not in VOID | {'minecraft:oak_door', 'minecraft:dark_oak_door'}:
                    raise UserError('Engineering route has blocked body clearance: '+name+' '+str(pos)+' '+state)
                if pos not in self.blocks:
                    self.clearance[pos] = state
            pos = x, y-1, z
            state = self.blocks.get(pos, self.snapshot.state(pos))
            if base(state) in VOID | {'minecraft:water'}:
                raise UserError('Engineering route has no dry support: '+name+' '+str(pos))
            if pos not in self.blocks:
                self.clearance[pos] = state
        self.routes.append({'name': name, 'standing_positions': [list(p) for p in points]})


def mill_shell(p):
    p.group = 'The Copper Wren watermill'
    p.floor(0, -6, 12, 10, deck=True)
    p.box(0, 1, -6, 12, 11, 10, AIR)
    for x in range(13):
        for z in range(-6, 11):
            if x not in (0, 12) and z not in (-6, 10):
                continue
            for y in range(1, 6):
                if x % 4 == 0 and (z in (-6, 10) or (z+6) % 4 == 0):
                    key, props = 'minecraft:stripped_dark_oak_log', {'axis': 'y'}
                elif y == 5:
                    key, props = ('minecraft:oak_log', {'axis': 'x'}) if z in (-6, 10) else ('minecraft:spruce_log', {'axis': 'z'})
                    if x % 4 == 0 and z in (-6, 10) or (z+6) % 4 == 0 and x in (0, 12):
                        key, props = 'minecraft:polished_andesite', {}
                else:
                    key, props = ('minecraft:mud_bricks' if y == 1 else 'minecraft:calcite'), {}
                p.put(x, y, z, key, **props)
    for x in (2, 6, 10):
        for z in (-6, 10):
            for dx in (-1, 0, 1):
                for y in (2, 3):
                    p.put(x+dx, y, z, 'minecraft:glass', replace=True)
    for z in (-4, 4, 8):
        for x in (0, 12):
            for dz in (0, 1):
                for y in (2, 3):
                    p.put(x, y, z+dz, 'minecraft:glass', replace=True)
    for x in (6, 7):
        for half, y in (('lower', 1), ('upper', 2)):
            p.put(x, y, 10, 'minecraft:oak_door', replace=True, facing='south', half=half,
                  hinge='left' if x == 6 else 'right', open=False, powered=False)
    for x in range(-1, 14):
        rise = min(x+1, 13-x)
        for z in range(-7, 12):
            seam = (z+6) % 8 == 0
            if x == 6:
                p.put(x, 6+rise, z, 'minecraft:dark_oak_slab' if seam else 'minecraft:spruce_slab',
                      type='top', waterlogged=False)
            else:
                p.put(x, 6+rise, z, 'mcwroofs:dark_oak_planks_roof' if seam else 'mcwroofs:spruce_planks_roof',
                      facing='east' if x < 6 else 'west', half='bottom', shape='straight')
        for z in (-6, 10):
            for y in range(6, 6+rise):
                key, props = ('minecraft:dark_oak_planks' if x % 4 == 0 else 'minecraft:calcite'), {}
                if y == 8:
                    key, props = ('minecraft:chiseled_stone_bricks', {}) if x % 4 == 0 else ('minecraft:stripped_oak_log', {'axis': 'x'})
                p.put(x, y, z, key, replace=True, **props)
    for x in (2, 10):
        p.put(x, 4, 9, 'minecraft:lantern', hanging=True, waterlogged=False)
    # Purposeful lived-in work stations: miller's ledger, tea, sack stores and
    # tools occupy perimeter alcoves; the operating aisle remains two blocks wide.
    for x in (2, 3, 4):
        p.put(x, 1, 8, 'handcrafted:oak_counter', facing='north', counter='spruce_planks', type=1)
    p.put(2, 2, 8, 'handcrafted:stackable_book', books=2, facing='north', seed=4)
    p.put(3, 2, 8, 'handcrafted:wood_cup', facing='north')
    p.put(4, 2, 8, 'handcrafted:terracotta_medium_pot')
    p.put(2, 1, 7, 'handcrafted:spruce_chair', facing='south', color='blue', waterlogged=False)
    for x, z in ((2, -4), (10, 8), (10, -4)):
        p.put(x, 1, z, 'minecraft:barrel', facing='up', open=False)
        p.put(x, 2, z, 'supplementaries:sack', open=False, waterlogged=False)
    p.put(9, 1, -4, 'minecraft:crafting_table')
    p.put(10, 1, -3, 'minecraft:grindstone', face='floor', facing='west')
    p.chest((3, 1, 6), 'Miller tools and demonstration stock',
            [('minecraft:wheat', 16), ('minecraft:iron_ingot', 4), ('create:wrench', 1)])
    for x in range(6, 11):
        for z in range(-2, 2):
            p.plank(x, 4, z)
    for n in range(4):
        p.put(10, 1+n, 6-n, 'minecraft:spruce_stairs', facing='north', half='bottom', shape='straight', waterlogged=False)
    for z in (-2, -1, 0, 1):
        p.put(6, 5, z, 'minecraft:spruce_fence')
    p.put(6, 5, 0, AIR, replace=True)
    p.rooms.extend([{'name': 'Miller ledger and tea alcove', 'center': list(p.world((3, 1, 8)))},
                    {'name': 'Grain gallery and real hopper', 'center': list(p.world((8, 5, 0)))},
                    {'name': 'Machine operating aisle', 'center': list(p.world((7, 1, 3)))}])


def mechanisms(p):
    p.group = 'The Copper Wren watermill'
    # A compact closed wheelhouse sits on actual dry ground, clear of the river.
    for x in range(-5, 0):
        for z in range(-2, 3):
            p.foundation(x, z)
    p.box(-5, 1, -2, -1, 6, 2, AIR, replace=True)
    for x in range(-5, 0):
        for z in range(-2, 3):
            if x not in (-5, -1) and z not in (-2, 2):
                continue
            for y in range(1, 7):
                key = 'minecraft:polished_andesite' if x in (-5, -1) and z in (-2, 2) else (
                    'minecraft:chiseled_stone_bricks' if y == 3 else 'minecraft:stone_bricks')
                if x == -5 and -1 <= z <= 1 and y in (2, 3, 5, 6):
                    key = 'minecraft:glass'
                p.put(x, y, z, key)
    for x in (-4, -3, -2):
        p.put(x, 3, 0, 'create:water_wheel', facing='west')
    for x in range(-1, 20):
        key, props = 'create:shaft', {'axis': 'x', 'waterlogged': False}
        if x in (-1, 4, 8, 12, 16):
            key, props = 'create:andesite_encased_shaft', {'axis': 'x'}
        elif x == 0:
            key, props = 'create:clutch', {'axis': 'x', 'powered': True}
        elif x == 3:
            key, props = 'create:cogwheel', {'axis': 'x', 'waterlogged': False}
        elif x in (5, 19):
            key, props = 'create:gearbox', {'axis': 'z'}
        p.put(x, 3, 0, key, replace=True, **props)
    p.put(0, 1, 1, 'minecraft:stone_bricks', replace=True)
    # The real lever is attached directly to the clutch's SOUTH face. A lever
    # one block above-and-forward is diagonal and cannot supply that redstone.
    p.put(0, 3, 1, 'minecraft:lever', replace=True, face='wall', facing='south', powered=True)
    p.put(5, 4, 0, 'create:millstone')
    p.put(5, 5, 0, 'create:chute', facing='down', shape='normal', waterlogged=False)
    p.put(5, 6, 0, 'minecraft:hopper', facing='down', enabled=True)
    p.chest((5, 7, 0), 'Grain input - empty for initial admission')
    p.put(10, 3, 0, 'create:mechanical_press', replace=True, facing='north')
    p.put(10, 1, 0, 'create:depot', waterlogged=False)
    p.put(4, 4, 0, 'overpressure:pneumatic_connection', facing='west', arrow_facing='west', mode='extract', powered=False)
    p.tags[p.world((4, 4, 0))] = '{filter:{id:"create:wheat_flour",count:1}}'
    p.put(3, 4, 0, 'overpressure:item_pump', facing='west', waterlogged=False)
    p.put(2, 4, 0, 'overpressure:pneumatic_tube', east=True, west=True, waterlogged=False)
    p.put(1, 4, 0, 'overpressure:pneumatic_tube', east=True, north=True, waterlogged=False)
    for z in range(-7, 0):
        p.put(1, 4, z, 'overpressure:pneumatic_tube', replace=True, south=True,
              north=z != -7, down=z == -7, waterlogged=False)
    for y in (3, 2):
        p.put(1, y, -7, 'overpressure:pneumatic_tube', up=True, down=True, waterlogged=False)
    p.put(1, 1, -7, 'overpressure:pneumatic_connection', facing='north', arrow_facing='north', mode='insert', powered=False)
    p.floor(0, -10, 5, -8)
    p.chest((1, 1, -8), 'Copper Wren flour dispatch - initially empty')
    for x in (0, 4):
        p.box(x, 1, -10, x, 4, -10, 'minecraft:stripped_spruce_log', axis='y')
    for x in range(0, 6):
        for z in (-10, -9, -8):
            p.put(x, 5, z, 'minecraft:dark_prismarine_slab', type='bottom', waterlogged=False)
    p.sign((3, 1, -9), ['COPPER WREN MILL', 'Real flour dispatch', 'Clutch ON = STOP', 'Commission before use'])
    # The speed-up is a genuine cog mesh, not a forged RPM field.
    for y in (1, 2):
        p.put(19, y, 0, 'create:gearbox' if y == 1 else 'create:shaft', replace=True,
              **({'axis': 'x'} if y == 1 else {'axis': 'y', 'waterlogged': False}))
    p.put(19, 1, 1, 'create:large_cogwheel', axis='z', waterlogged=False)
    p.put(20, 2, 1, 'create:cogwheel', axis='z', waterlogged=False)
    for z in range(2, 58):
        p.put(20, 2, z, 'create:andesite_encased_shaft' if z % 8 == 0 else 'create:shaft', replace=True,
              **({'axis': 'z'} if z % 8 == 0 else {'axis': 'z', 'waterlogged': False}))
    for z in (9, 57):
        for y in (2, 3):
            p.put(21, y, z, 'create:cogwheel', replace=True, axis='z', waterlogged=False)
    p.systems['watermill'] = {
        'wheels': [list(p.world((x, 3, 0))) for x in (-4, -3, -2)],
        'water_sources': [list(p.world((x, 6, -1))) for x in (-4, -3, -2)],
        'clutch': list(p.world((0, 3, 0))), 'stop_lever': list(p.world((0, 3, 1))),
        'millstone': list(p.world((5, 4, 0))), 'grain_chest': list(p.world((5, 7, 0))),
        'press': list(p.world((10, 3, 0))), 'depot': list(p.world((10, 1, 0))),
        'starter_chest': list(p.world((3, 1, 6))), 'initial_water': 'dry', 'initially_stopped': True,
        'run_state': 'not yet demonstrated; native flow, RPM/stress and actual recipes required'}
    p.systems['pneumatic'] = {
        'extractor': list(p.world((4, 4, 0))), 'pump': list(p.world((3, 4, 0))),
        'inserter': list(p.world((1, 1, -7))), 'output_chest': list(p.world((1, 1, -8))),
        'filter': 'create:wheat_flour', 'minimum_input_test': 16,
        'route': 'Millstone side extraction, cog-driven pump, eaved drop to ground-level flour dispatch',
        'run_state': 'Native routing/count conservation and restart not yet demonstrated'}


def transport(p):
    p.group = 'Garden railway and independent walking path'
    # Terraces are only the actual path, ballast and two small platforms.
    for z in range(3, 53):
        for x in walk_columns(z):
            p.foundation(x, z)
            p.box(x, 1, z, x, 3, z, AIR)
    for x in (25, 26, 27):
        for z in range(3, 65):
            p.foundation(x, z, 1)
            p.box(x, 2, z, x, 8, z, AIR)
    for z in range(3, 65):
        p.put(26, 2, z, 'railways:track_dark_oak' if (z+4) % 8 == 0 else 'railways:track_spruce',
              shape='zo', turn=False, waterlogged=False)
    for z in (3, 64):
        for x in (25, 26, 27):
            p.put(x, 3, z, 'minecraft:dark_oak_fence')
            p.put(x, 4, z, 'minecraft:dark_oak_slab', type='top', waterlogged=False)
    for lo, hi in ((2, 12), (53, 63)):
        p.floor(20, lo, 24, hi, 3, deck=True)
        p.box(20, 7, lo, 24, 7, hi, AIR)
        for z in (lo, hi):
            p.put(20, 4, z, 'minecraft:dark_oak_fence')
            p.put(20, 5, z, 'minecraft:lantern', hanging=False, waterlogged=False)
        # Three natural-width steps from the independent walking path.
        if lo == 2:
            for x, y in ((18, 1), (19, 2), (20, 3)):
                for z in (4, 5):
                    p.put(x, y, z, 'minecraft:spruce_stairs', replace=True, facing='east', half='bottom', shape='straight', waterlogged=False)
                    p.box(x, y+1, z, x, y+2, z, AIR, replace=True)
    stations = []
    for name, z, positive in (('Copper Wren Mill', 6, True), ('Rosewater Orchard Halt', 58, False)):
        pos, target = (22, 4, z), (26, 2, z)
        p.put(*pos, 'create:track_station', assembling=False, waterlogged=False)
        ident = uuid.uuid5(uuid.NAMESPACE_URL, 'awft:artistic-engineering:'+str(p.world(pos))+':'+name)
        values = [int.from_bytes(ident.bytes[n:n+4], 'big', signed=True) for n in range(0, 16, 4)]
        p.tags[p.world(pos)] = '{Id:[I;'+','.join(map(str, values))+'],TargetTrack:[I;4,-2,0],Ortho:1b,TargetDirection:'+('1b' if positive else '0b')+'}'
        stations.append({'name': name, 'position': list(p.world(pos)), 'target_track': list(p.world(target)),
                         'target_direction_positive': positive, 'native_target_relative': [4, -2, 0], 'id': str(ident)})
        p.sign((20, 4, z+1), [name, 'Short passenger shuttle', 'Board only at rest', 'Native assembly needed'])
    p.chest((22, 4, 3), 'Railway tools - no automatic schedule',
            [('create:wrench', 1), ('create:super_glue', 1), ('create:schedule', 1)])
    p.group = 'The Wren passenger carriage'
    for x in (25, 26, 27):
        for z in range(7, 16):
            p.plank(x, 4, z)
            p.put(x, 8, z, 'minecraft:dark_prismarine_slab' if z != 7 else 'minecraft:dark_oak_slab', type='bottom', waterlogged=False)
    for z in (8, 14):
        p.put(26, 3, z, 'create:small_bogey', axis='z', waterlogged=False)
    for x in (25, 27):
        for z in (7, 15):
            p.box(x, 5, z, x, 7, z, 'minecraft:spruce_fence')
    for z in (7, 15):
        p.put(26, 5, z, 'create:controls', facing='north' if z == 7 else 'south', open=False, virtual=False, waterlogged=False)
    for z in (9, 11, 13):
        p.put(26, 5, z, 'create:blue_seat', waterlogged=False)
    p.put(25, 4, 10, 'minecraft:spruce_stairs', replace=True, facing='east', half='bottom', shape='straight', waterlogged=False)
    p.group = 'Garden railway and independent walking path'
    for z in range(9, 58, 8):
        if z in (9, 57):
            p.put(21, 4, z, 'create_hypertube:hypertube_entrance', facing='north' if z == 9 else 'south',
                  locked=False, powered=False, waterlogged=False)
        else:
            for y in (1, 2, 3):
                p.put(21, y, z, 'minecraft:polished_andesite', replace=True)
            p.put(21, 4, z, 'create_hypertube:hypertube', north_south=True, east_west=False, up_down=False, waterlogged=False)
    # Native Bezier collision cells are not counterfeited as placed tube blocks.
    tube_cells = set()
    for first, last in SPANS:
        for x in (20, 21, 22):
            for y in (4, 5):
                for z in range(first+1, last):
                    p.put(x, y, z, AIR, replace=True)
                    tube_cells.add(p.world((x, y, z)))
    for z in (9, 57):
        p.put(20, 3, z, 'minecraft:polished_andesite', replace=True)
        p.put(20, 4, z, 'minecraft:lever', face='floor', facing='east', powered=False)
    p.systems['hypertube'] = {
        'entrances': [list(p.world((21, 4, z))) for z in (9, 57)], 'minimum_entrance_rpm': 16,
        'anchors': [list(p.world((21, 4, z))) for z in range(17, 57, 8)],
        'native_span_lengths': [8]*6, 'maximum_native_span': 40, 'gear_ratio': 2,
        'large_cog': list(p.world((19, 1, 1))), 'speedup_small_cog': list(p.world((20, 2, 1))),
        'entrance_drive_cogs': [list(p.world((21, 3, z))) for z in (9, 57)],
        'native_links': [{'from': list(p.world((21, 4, a))), 'from_face': 'south',
                          'to': list(p.world((21, 4, b))), 'to_face': 'north'} for a, b in SPANS],
        'native_collision_cells': [list(v) for v in sorted(tube_cells)],
        'run_state': 'Not connected; native validation, reciprocal links, filler cells and real player travel required'}
    p.systems['railway'] = {
        'track_start': list(p.world((26, 2, 3))), 'track_end': list(p.world((26, 2, 64))),
        'track_blocks': 62, 'station_distance_blocks': 52, 'stations': stations,
        'carriage_glue_min': list(p.world((25, 3, 7))), 'carriage_glue_max': list(p.world((27, 8, 15))),
        'bogeys': [list(p.world((26, 3, z))) for z in (8, 14)],
        'controls': [list(p.world((26, 5, z))) for z in (7, 15)], 'seats': 3,
        'initially_assembled': False, 'native_owner_uuid': str(uuid.uuid5(uuid.NAMESPACE_URL, 'awft:artistic-engineering:railway')),
        'operation': 'On-demand bidirectional scenic shuttle; no loop schedule or forced chunk loading',
        'run_state': 'Native graph/targeting/glue/assembly and passenger driving not demonstrated'}


def gardens_and_routes(p):
    p.group = 'Orchard halt shelter'
    p.floor(12, 55, 18, 62, 3, deck=True)
    p.floor(19, 59, 19, 60, 3, deck=True)
    for n in range(3):
        for x in (16, 17):
            p.foundation(x, 53+n, n)
            p.put(x, 1+n, 53+n, 'minecraft:spruce_stairs', replace=True,
                  facing='south', half='bottom', shape='straight', waterlogged=False)
            p.box(x, 2+n, 53+n, x, 3+n, 53+n, AIR, replace=True)
    for x in (12, 18):
        for z in (55, 62):
            p.box(x, 4, z, x, 7, z, 'minecraft:stripped_oak_log', axis='y')
    for x in range(11, 20):
        for z in range(54, 64):
            y = 8+min(x-11, 19-x)//2
            p.put(x, y, z, 'minecraft:dark_oak_slab' if z == 58 else 'minecraft:spruce_slab', type='bottom', waterlogged=False)
    for x in (13, 14, 15):
        p.put(x, 4, 61, 'handcrafted:spruce_bench', facing='north', color='blue',
              shape='left' if x == 13 else 'right' if x == 15 else 'middle', waterlogged=False)
    p.put(17, 4, 60, 'handcrafted:oak_table', color='none', shape='single', waterlogged=False)
    p.put(17, 5, 60, 'handcrafted:terracotta_medium_pot')
    p.put(15, 7, 56, 'minecraft:lantern', hanging=True, waterlogged=False)
    p.group = 'Mill quarter paths and working yard'
    p.floor(4, 11, 18, 13)
    p.floor(13, 7, 16, 12)
    # A dry-land path joins the castle's existing east approach at x1300.
    p.floor(-7, 11, 3, 12)
    for x, z in ((-6, 13), (14, 12), (18, 24), (18, 40), (18, 52)):
        p.foundation(x, z)
        p.put(x, 1, z, 'minecraft:dark_oak_fence')
        p.put(x, 2, z, 'minecraft:lantern', hanging=False, waterlogged=False)
    for x in (14, 15):
        p.put(x, 1, 8, 'minecraft:grass_block')
        p.put(x, 2, 8, 'minecraft:flowering_azalea')
    p.put(14, 1, 11, 'minecraft:composter', level=0)
    p.sign((11, 1, 12), ['THE COPPER WREN', 'Mill, flour and railway', 'Walkway stays open', 'No idle chunk loading'])
    p.route('Two-wide mill door and ledger approach', [(x, 1, z) for x in (6, 7) for z in range(3, 14)])
    p.route('Mill operating aisle', [(x, 1, z) for x in (7, 8) for z in range(-4, 9)])
    p.route('Mill grain gallery', [(x, 5, z) for x in (8, 9) for z in (-1, 0, 1)])
    p.route('Two-wide castle to mill yard', [(x, 1, z) for x in range(-7, 6) for z in (11, 12)])
    p.route('Independent garden walking bypass', [(x, 1, z) for z in range(3, 53) for x in walk_columns(z)])
    for name, zs in (('North tube safe egress', (6, 7, 8)), ('South tube safe egress', (58, 59, 60))):
        p.route(name, [(21, 4, z) for z in zs])
    for name, zs in (('Mill rail boarding', range(3, 12)), ('Orchard rail boarding', range(54, 63))):
        p.route(name, [(24, 4, z) for z in zs])
    p.cameras = [
        {'name': 'Mill wheel and half-timber arrival', 'eye': list(p.world((-12, 9, 20))), 'look_at': list(p.world((4, 4, 2)))},
        {'name': 'Miller ledger and operating machinery', 'eye': list(p.world((7, 3, 8))), 'look_at': list(p.world((5, 4, 0)))},
        {'name': 'Contained waterwheel and flour dispatch', 'eye': list(p.world((-10, 5, -9))), 'look_at': list(p.world((-2, 3, -1)))},
        {'name': 'Garden railway, tube and walking bypass', 'eye': list(p.world((35, 13, 33))), 'look_at': list(p.world((20, 4, 30)))},
        {'name': 'Orchard halt sheltered seating', 'eye': list(p.world((14, 6, 55))), 'look_at': list(p.world((15, 5, 61)))},
    ]


def validate(p):
    def require(local, key, **props):
        state = p.blocks.get(p.world(local), '')
        if base(state) != key or any(properties(state).get(k) != str(v).lower() for k, v in props.items()):
            raise UserError('Broken genuine engineering component '+str(local)+' '+str(state))
    for x in (-4, -3, -2):
        require((x, 3, 0), 'create:water_wheel', facing='west')
        require((x, 6, -1), AIR)
    require((-1, 3, 0), 'create:andesite_encased_shaft', axis='x')
    full_wall = {'minecraft:stone_bricks', 'minecraft:chiseled_stone_bricks',
                 'minecraft:polished_andesite', 'minecraft:glass', 'create:andesite_encased_shaft'}
    for x in range(-5, 0):
        for z in range(-2, 3):
            if base(p.blocks.get(p.world((x, 0, z)), AIR)) in VOID | {'minecraft:water'}:
                raise UserError('Hydraulic containment floor is open')
            if x in (-5, -1) or z in (-2, 2):
                for y in range(1, 7):
                    if base(p.blocks.get(p.world((x, y, z)), AIR)) not in full_wall:
                        raise UserError('Hydraulic containment wall is open: '+str((x, y, z)))
    require((0, 3, 0), 'create:clutch', powered=True)
    require((0, 3, 1), 'minecraft:lever', face='wall', facing='south', powered=True)
    require((5, 3, 0), 'create:gearbox', axis='z')
    require((5, 4, 0), 'create:millstone')
    require((3, 3, 0), 'create:cogwheel', axis='x')
    require((3, 4, 0), 'overpressure:item_pump', facing='west')
    require((4, 4, 0), 'overpressure:pneumatic_connection', mode='extract', facing='west')
    require((1, 1, -7), 'overpressure:pneumatic_connection', mode='insert', facing='north')
    require((19, 1, 1), 'create:large_cogwheel', axis='z')
    require((20, 2, 1), 'create:cogwheel', axis='z')
    for x in range(1, 20):
        if x in (4, 8, 12, 16):
            require((x, 3, 0), 'create:andesite_encased_shaft', axis='x')
        elif x in (5, 19):
            require((x, 3, 0), 'create:gearbox', axis='z')
        elif x == 3:
            require((x, 3, 0), 'create:cogwheel', axis='x')
        elif x == 10:
            require((x, 3, 0), 'create:mechanical_press', facing='north')
        else:
            require((x, 3, 0), 'create:shaft', axis='x')
    require((19, 2, 0), 'create:shaft', axis='y')
    require((19, 1, 0), 'create:gearbox', axis='x')
    for z in range(2, 58):
        require((20, 2, z), 'create:andesite_encased_shaft' if z % 8 == 0 else 'create:shaft', axis='z')
    for z in (9, 57):
        for y in (2, 3):
            require((21, y, z), 'create:cogwheel', axis='z')
    if 'create:wheat_flour' not in p.tags.get(p.world((4, 4, 0)), ''):
        raise UserError('Missing actual native flour filter')
    for local in ((5, 7, 0), (1, 1, -8)):
        if not p.tags.get(p.world(local), '').endswith('Items:[]}'):
            raise UserError('Powered inventories must begin empty')
    directions = {'north': (0, 0, -1), 'south': (0, 0, 1), 'east': (1, 0, 0),
                  'west': (-1, 0, 0), 'up': (0, 1, 0), 'down': (0, -1, 0)}
    nodes = {pos: state for pos, state in p.blocks.items() if base(state).startswith('overpressure:')}
    edges = {}
    for pos, state in nodes.items():
        attrs, kind = properties(state), base(state)
        faces = [d for d in directions if attrs.get(d) == 'true'] if kind.endswith('pneumatic_tube') else (
            [attrs['facing']] if kind.endswith('item_pump') or attrs.get('mode') == 'extract' else [])
        edges[pos] = []
        for face in faces:
            neighbor = tuple(pos[n]+directions[face][n] for n in range(3))
            if neighbor not in nodes:
                raise UserError('Pneumatic route points at no native neighbor: '+str(pos)+' '+face)
            edges[pos].append(neighbor)
    seen, queue = set(), [p.world((4, 4, 0))]
    while queue:
        pos = queue.pop()
        if pos not in seen:
            seen.add(pos)
            queue.extend(edges[pos])
    if seen != set(nodes) or p.world((1, 1, -7)) not in seen:
        raise UserError('Disconnected native flour route')
    for z in range(9, 58, 8):
        require((21, 4, z), 'create_hypertube:hypertube_entrance' if z in (9, 57) else 'create_hypertube:hypertube')
    for cell in p.systems['hypertube']['native_collision_cells']:
        if p.blocks.get(tuple(cell)) != AIR:
            raise UserError('Native curve collision cells must be explicitly reserved dry air')
    for z in range(3, 65):
        state = p.blocks.get(p.world((26, 2, z)), '')
        if base(state) not in {'railways:track_spruce', 'railways:track_dark_oak'} or properties(state).get('shape') != 'zo':
            raise UserError('The short passenger track is disconnected or wrongly oriented')
    for z in (8, 14):
        require((26, 3, z), 'create:small_bogey', axis='z')
    if (p.systems['railway']['carriage_glue_min'] != list(p.world((25, 3, 7)))
            or p.systems['railway']['carriage_glue_max'] != list(p.world((27, 8, 15)))):
        raise UserError('Train glue custody must exclude track, platforms and tube infrastructure')
    for route in p.routes:
        for x, y, z in route['standing_positions']:
            for dy in (0, 1):
                state = p.blocks.get((x, y+dy, z), p.snapshot.state((x, y+dy, z)))
                if base(state) not in VOID | {'minecraft:oak_door', 'minecraft:dark_oak_door'}:
                    raise UserError('A preserved operating/boarding route is blocked: '+route['name'])
            state = p.blocks.get((x, y-1, z), p.snapshot.state((x, y-1, z)))
            if base(state) in VOID | {'minecraft:water'}:
                raise UserError('A preserved operating/boarding route lost its support')
    building_checks = []
    for name in ('The Copper Wren watermill', 'The Wren passenger carriage', 'Orchard halt shelter'):
        cells = {pos: p.blocks[pos] for pos in p.groups[name]}
        building_checks.append(require_material_rule(cells, name))
    outdoor = require_outdoor_rule(p.blocks, 'Complete authored mill quarter, including foundations, ballast and machines')
    return {'material_rule': building_checks, 'outdoor_nine_rule': outdoor,
            'dry_foundations': len(p.dry_columns), 'routes': len(p.routes),
            'track_blocks': 62, 'native_tube_spans': 6, 'static_source_preflight_only': True}


def construct(registry, snapshot, exclusions=(), origin=ORIGIN):
    p = Quarter(registry, snapshot, exclusions, origin)
    mill_shell(p)
    mechanisms(p)
    transport(p)
    gardens_and_routes(p)
    validate(p)
    return p


def payload(p, states, backup_sha, name, *, include_tags=False):
    palette = sorted(set(states.values()))
    index = {state: n for n, state in enumerate(palette)}
    return {'format': 'awft-native-settlement:1', 'name': name, 'created': utcnow(),
            'seed': p.registry['seed'], 'world_path': p.registry['world_path'], 'backup_sha256': backup_sha,
            'bounds': [min(v[0] for v in states), min(v[2] for v in states), max(v[0] for v in states), max(v[2] for v in states)],
            'palette': palette, 'blocks': [[*pos, index[state]] for pos, state in sorted(states.items())],
            'block_entities': [{'pos': list(pos), 'nbt': tag} for pos, tag in sorted(p.tags.items())] if include_tags else [],
            'commands': [], 'landmarks': [], 'validation': 'STAGED ONLY; native before/after, functional commissioning and visual review pending'}


def prepare(home, registry_path, backup_id, backup_sha, exclude_paths, output):
    home, output, registry_path = Path(home).resolve(), Path(output).resolve(), Path(registry_path).resolve()
    if (not home.is_relative_to(Path(r'D:\A World for Two\staging\world-tests'))
            or not output.is_relative_to(home/'staging') or output.exists()
            or not re.fullmatch(r'\d{8}T\d{6}Z-[a-f0-9]{6}', backup_id)
            or not re.fullmatch('[a-f0-9]{64}', backup_sha)):
        raise UserError('Explicit immutable checkpoint and NEW owned artistic staging output required')
    if not 1 <= len(exclude_paths) <= 16 or any(Path(v).stat().st_size > 8*MIB for v in [registry_path, *exclude_paths]):
        raise UserError('Finite actual registry and exact authored exclusions required')
    admission = guard(4*MIB, MAX_OUTPUT)
    registry = read_json(registry_path)
    if not Path(registry['world_path']).resolve().is_relative_to(home/'world'):
        raise UserError('The registry does not identify this separate artistic world')
    receipt = {'verified': True, 'id': backup_id, 'sha256': backup_sha}
    current = read_json(home/'dashboard/settlement/backup-receipt.json')
    if any(current.get(k) != receipt[k] for k in ('verified', 'id', 'sha256')):
        raise UserError('Rebind to the parent-reviewed current artistic checkpoint')
    sources = []
    for name, sha in zip(MOD_FILES, MOD_SHAS):
        path = home/'server/mods'/name
        if digest(path) != sha:
            raise UserError('Pinned engineering API artifact changed: '+name)
        sources.append({'file': name, 'sha256': sha, 'role': 'Actual pinned native API and recipes'})
    for name in ('overpressure-common.toml', 'create_hypertube-server.toml', 'create-server.toml'):
        path = home/'server/config'/name
        doc = tomllib.loads(path.read_text(encoding='utf-8'))
        if name == 'overpressure-common.toml' and doc.get('pneumaticTubes', {}).get('packagersOnly') is not False:
            raise UserError('Native flour routing requires packagersOnly=false')
        if name == 'create_hypertube-server.toml' and doc.get('Collision Settings', {}).get('tubeCollision') is not True:
            raise UserError('Native tube collision must remain enabled')
        sources.append({'file': name, 'sha256': digest(path), 'role': 'Actual native operating policy'})
    exclusions = [(Path(v).stem, read_json(v), digest(Path(v))) for v in exclude_paths]
    snapshot = BackupWorld(home, receipt, registry)
    try:
        p = construct(registry, snapshot, exclusions)
        sources.extend(snapshot.sources)
        proof = validate(p)
        before = dict(p.previous) | p.clearance
    finally:
        snapshot.close()
    documents = {}
    def encode(name, doc):
        data = (json.dumps(doc, ensure_ascii=False, separators=(',', ':'))+'\n').encode()
        documents[name] = data
        return hashlib.sha256(data).hexdigest()
    plan_sha = encode('mill-quarter.json', payload(p, p.blocks, backup_sha, 'Copper Wren mill quarter - dry installation', include_tags=True))
    before_sha = encode('native-before.json', payload(p, before, backup_sha, 'VERIFY ONLY - exact stopped mill-quarter preimage'))
    sources_state = {tuple(pos): p.state('minecraft:water', level=0) for pos in p.systems['watermill']['water_sources']}
    water_sha = encode('water-activation.json', payload(p, sources_state, backup_sha, 'COMMISSION ONLY - three contained sources'))
    water_before_sha = encode('water-before.json', payload(p, {pos: AIR for pos in sources_state}, backup_sha, 'VERIFY ONLY - installed dry source cells'))
    source_sha = digest(Path(__file__))
    commissioning = {'format': 'awft-artistic-engineering-commission:1', 'status': 'UNCOMMISSIONED',
                     'plan_sha256': plan_sha, 'before_sha256': before_sha, 'source_sha256': source_sha,
                     'checkpoint_id': backup_id, 'checkpoint_sha256': backup_sha,
                     'origin': list(p.origin), 'bounds_xyz': list(WORLD_RESERVE), 'systems': p.systems,
                     'native_before_receipt': None, 'native_after_receipt': None,
                     'candidate_version': None, 'bridge_version': None, 'native_helper_class_sha256': None,
                     'admission': 'Native terminal before/after receipts and exact running helper identity must be supplied by the parent; null is never authority',
                     'required_operations': ['inspect', 'connect-tubes', 'assemble-shuttle', 'activate-water', 'mill-and-dispatch-test', 'stop-and-persist'],
                     'player_acceptance': 'No tube travel, train driving, entity transportation or multiplayer proof yet'}
    commission_sha = encode('commissioning.json', commissioning)
    manifest = {'format': 'awft-artistic-engineering:1', 'created': utcnow(), 'source_sha256': source_sha,
                'registry_sha256': digest(registry_path), 'checkpoint_id': backup_id, 'checkpoint_sha256': backup_sha,
                'origin': list(p.origin), 'bounds_xyz': list(WORLD_RESERVE), 'plan_sha256': plan_sha,
                'before_sha256': before_sha, 'water_sha256': water_sha, 'water_before_sha256': water_before_sha,
                'commissioning_sha256': commission_sha, 'placements': len(p.blocks), 'block_entities': len(p.tags),
                'preconditions': len(before), 'block_counts': dict(Counter(base(v) for v in p.blocks.values())),
                'dry_columns': [{'x': x, 'z': z, 'saved_ground_y': y} for (x, z), y in sorted(p.dry_columns.items())],
                'natural_replacements': dict(Counter(base(v) for pos, v in p.previous.items() if v != p.blocks[pos])),
                'sources': sources+p.sources, 'fixed_exclusion_cells': len(p.fixed), 'saved_block_entities_changed': 0,
                'systems': p.systems, 'rooms': p.rooms, 'routes': p.routes, 'camera_poses': p.cameras,
                'checks': proof, 'reserve_guard': admission, 'new_forced_chunks': 0, 'commands': 0,
                'ownership': 'Separate artistic world, authenticated saved checkpoint; no live mutable region opened; saved BEs and all supplied authored air/solid exclusions preserved',
                'status': 'STAGED ONLY - native installation/commissioning, restart, shader screenshots and visual acceptance pending'}
    manifest_sha = encode('manifest.json', manifest)
    if sum(map(len, documents.values())) > MAX_OUTPUT:
        raise UserError('Bounded engineering output exceeds its admitted allocation')
    output.mkdir(parents=True, exist_ok=False)
    for name, raw in documents.items():
        (output/name).write_bytes(raw)
    return {'manifest': str(output/'manifest.json'), 'manifest_sha256': manifest_sha, 'plan_sha256': plan_sha,
            'before_sha256': before_sha, 'placements': len(p.blocks), 'bytes': sum(map(len, documents.values())),
            'native_activation': 'Not performed'}


def native_proof_times(proof):
    """Return measured, ordered UTC-aware instants, never inferred freshness."""
    try:
        started, finished = (datetime.fromisoformat(proof[key].replace('Z', '+00:00'))
                             for key in ('started', 'finished'))
        if started.tzinfo is None or finished.tzinfo is None or started > finished:
            raise ValueError('Unordered or timezone-free native observation')
    except (KeyError, ValueError, TypeError, AttributeError) as error:
        raise UserError('Native proof has no truthful ordered measured timestamps') from error
    return started, finished


def checked_native_proof(path, expected_sha, count, *, now=None, maximum_age=1200):
    """A retained terminal proof is necessary, never permission to skip live checks."""
    path = Path(path)
    if not 1 <= path.stat().st_size <= 512*1024:
        raise UserError('Native proof exceeds its finite allocation')
    proof = read_json(path)
    marker = path.with_name(path.name+'.complete')
    if not marker.is_file() or not 1 <= marker.stat().st_size <= 128 or marker.read_text().strip() != digest(path):
        raise UserError('Native terminal proof lacks its exact immutable completion marker')
    if (proof.get('operation') != 'verify' or proof.get('plan_sha256') != expected_sha
            or proof.get('blocks') != count or proof.get('failures') != 0 or proof.get('error')
            or proof.get('status') != 'verified actual block identities, orientation, block entities and supplied inventories'):
        raise UserError('Exact zero-failure native verification is required')
    started, finished = native_proof_times(proof)
    current = now or datetime.now(timezone.utc)
    age = (current-finished).total_seconds()
    if age < 0 or started > current:
        raise UserError('Future native proof cannot authorize commissioning')
    if maximum_age is not None and age > maximum_age:
        raise UserError('Reverify the actual native geometry immediately before commissioning')
    return proof, marker


def checked_after_plan(original, after, backup):
    """Permit only a current-checkpoint reference change, no geometry edits."""
    if (backup.get('verified') is not True or not re.fullmatch(r'[a-f0-9]{64}', backup.get('sha256', ''))
            or 'backup_sha256' not in original):
        raise UserError('Exact verified current checkpoint identity required')
    expected = dict(original, backup_sha256=backup['sha256'])
    if after != expected:
        raise UserError('Fresh native verification plan may change only the backup SHA')


def checked_proof_order(before, after):
    if native_proof_times(before)[1] > native_proof_times(after)[0]:
        raise UserError('Native after verification predates its preimage admission')


def bind_commissioning(home, bundle, bridge_jar, candidate, bridge_version, native_before, native_after, native_after_plan):
    """Create one immutable typed request after real parent-owned native checks.

    This writes evidence only. It does not install a bridge, invoke a command,
    activate water, add tickets, open a world or mutate a prior bundle.
    """
    home, bundle = Path(home).resolve(), Path(bundle).resolve()
    if (not home.is_relative_to(Path(r'D:\A World for Two\staging\world-tests'))
            or not bundle.is_relative_to(home/'staging') or not re.fullmatch(r'0\.1\.0-candidate\.\d+', candidate)
            or not re.fullmatch(r'0\.6\.\d+', bridge_version)):
        raise UserError('Exact separate artistic home, candidate and native bridge required')
    admission = guard(4*MIB, MAX_OUTPUT)
    expected = {'plan': '181e2191572846967c41e77bf5b406d0dddcc484488aa60d6725728ba651b199',
                'manifest': '4339bb54a05d9c5a478b471db880c7d80dc1f6c0f25081824c7c54b75f49f408',
                'before': '042d7717761b938bd13150aae2d58483156cd5a243bd8950c7ade247d3ee775a'}
    def reference(path, limit=2*MIB):
        path = Path(path).resolve()
        if not path.is_relative_to(home) or not 0 < path.stat().st_size <= limit:
            raise UserError('Bounded evidence must stay inside this actual artistic home')
        return {'path': path.relative_to(home).as_posix(), 'bytes': path.stat().st_size, 'sha256': digest(path)}
    manifest_path, plan_path = bundle/'manifest.json', bundle/'mill-quarter.json'
    if digest(manifest_path) != expected['manifest'] or digest(plan_path) != expected['plan']:
        raise UserError('This executable helper admits only the exact reviewed R2 physical composition')
    manifest = read_json(manifest_path)
    before = Path(native_before).resolve()
    after = Path(native_after).resolve()
    if any(not p.is_relative_to(home/'dashboard/settlement') for p in (before, after)):
        raise UserError('Actual native proof must originate in this artistic server journal')
    backup = home/'dashboard/settlement/backup-receipt.json'
    current_backup = read_json(backup)
    after_plan = Path(native_after_plan).resolve()
    after_plan_ref = reference(after_plan)
    checked_after_plan(read_json(plan_path), read_json(after_plan), current_backup)
    before_doc, before_marker = checked_native_proof(before, expected['before'], manifest['preconditions'], maximum_age=None)
    after_doc, after_marker = checked_native_proof(after, after_plan_ref['sha256'], manifest['placements'])
    checked_proof_order(before_doc, after_doc)
    archive = Path(bridge_jar).resolve()
    if not 0 < archive.stat().st_size <= 4*MIB:
        raise UserError('The built bridge exceeds its finite API evidence allocation')
    with zipfile.ZipFile(archive) as jar:
        class_name = 'worldfortwo/bridge/ArtisticEngineeringSupport.class'
        if jar.getinfo(class_name).file_size > 256*1024:
            raise UserError('Native helper exceeds its finite code bound')
        native_class = jar.read(class_name)
        metadata = tomllib.loads(jar.read('META-INF/neoforge.mods.toml').decode('utf-8'))
        if not any(row.get('modId') == 'awft_control_bridge' and row.get('version') == bridge_version for row in metadata.get('mods', [])):
            raise UserError('The actual built bridge metadata version differs')
    configs = []
    for name in ('overpressure-common.toml', 'create_hypertube-server.toml', 'create-server.toml'):
        ref = reference(home/'server/config'/name, MIB)
        proof = next((row for row in manifest['sources'] if row.get('file') == name), None)
        if not proof or proof['sha256'] != ref['sha256']:
            raise UserError('The real native configuration differs from the reviewed R2 policy')
        configs.append(ref)
    request = {'format': 'awft-artistic-mill-live:1', 'candidate_version': candidate, 'bridge_version': bridge_version,
               'native_class_sha256': hashlib.sha256(native_class).hexdigest(), 'bridge_jar_sha256': digest(archive),
               'manifest': reference(manifest_path), 'plan': reference(plan_path), 'current_backup': reference(backup, 4096),
               'native_after_plan': after_plan_ref,
               'native_before': reference(before, 512*1024), 'native_before_complete': reference(before_marker, 128),
               'native_after': reference(after, 512*1024), 'native_after_complete': reference(after_marker, 128),
               'configuration': configs, 'storage_guard': admission,
               'authority': 'Exact reviewed R2 only; helper must acquire fresh shared lease, verify current native world and all targets; no operation has been invoked'}
    raw = (json.dumps(request, separators=(',', ':'))+'\n').encode()
    if len(raw) > 128*1024:
        raise UserError('Native request exceeds its bounded admission allocation')
    sha = hashlib.sha256(raw).hexdigest()
    output = home/'dashboard/settlement'/('mill-commission-'+sha[:16])
    output.mkdir(parents=True, exist_ok=False)
    (output/'request.json').write_bytes(raw)
    return {'request': str(output/'request.json'), 'sha256': sha, 'bundle_name': output.name,
            'native_activation': 'Not performed; actual parent-reviewed native command remains necessary'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--home', type=Path, required=True)
    parser.add_argument('--registry', type=Path, required=True)
    parser.add_argument('--backup-id', required=True)
    parser.add_argument('--backup-sha256', required=True)
    parser.add_argument('--exclude', type=Path, nargs='+', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.home, args.registry, args.backup_id, args.backup_sha256, args.exclude, args.output), indent=2))
