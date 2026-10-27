"""Original saved-ground plaza and pump-fed, gravity fountain proposal.

No live-world reads, native calls, commands, invented flow NBT or entity seeding.
The independent wheel source and elevated header are deliberately construction
AIR. A separate native commissioning step must prove the actual pumped fill,
normal piston shutoff and downstream drain before this is called functional.
"""
from __future__ import annotations

import argparse
from collections import Counter, deque
import hashlib
import json
from pathlib import Path

from control_room.common import UserError, digest, read_json, utcnow
from tools.artistic_materials import require_material_rule, require_outdoor_rule
from tools.playtest import guard
from tools.settlement_attractions import BackupWorld

AIR = 'minecraft:air'
CENTER = (1138, -1127)
SPAWN = (1120, 67, -1130)
HEADER = (1138, 73, -1129)
OUTLET = (1138, 73, -1128)
PISTON = (1138, 73, -1126)
PLUG_OPEN = (1138, 73, -1127)
STOP_LEVER = (1142, 66, -1125)
PUMP = (1140, 66, -1129)
WHEEL = (1145, 66, -1130)
WHEEL_SOURCE = (1145, 69, -1131)
WHEEL_BAFFLE = (1145, 69, -1130)
JET_WITNESSES = ((1135, 68, -1128), (1141, 68, -1128),
                 (1138, 68, -1131), (1138, 68, -1125))
CREATE_SHA = 'ef87fe5709f1ba1f5b8bb20a2925b5afb4669e178fd6d8bf10c167759eefe37a'
MAX_CELLS = 7000
MAX_OUTPUT = 16 * 1024**2
DIR = {'north': (0, 0, -1), 'south': (0, 0, 1), 'east': (1, 0, 0),
       'west': (-1, 0, 0), 'up': (0, 1, 0), 'down': (0, -1, 0)}
SOIL = {'minecraft:' + n for n in ('grass_block', 'dirt', 'coarse_dirt',
        'rooted_dirt', 'stone', 'clay', 'sand', 'gravel')}
SOFT = {AIR, 'minecraft:cave_air', 'minecraft:void_air'} | {'minecraft:' + n
        for n in ('short_grass', 'tall_grass', 'fern', 'large_fern', 'dandelion',
                  'poppy', 'cornflower', 'azure_bluet', 'allium', 'oxeye_daisy')}
SOFT |= {'regions_unexplored:grass_sprouts', 'farm_and_charm:wild_barley',
         'farm_and_charm:wild_carrots', 'farm_and_charm:wild_corn'}
EXCLUSIONS = ('neighborhood-canonical-ridges-20261027T1852Z/court-canonical-full-VERIFY-ONLY.json',
              'neighborhood-canonical-ridges-20261027T1852Z/bramble-canonical-full-VERIFY-ONLY.json')


def key(state):
    return state.split('[', 1)[0]


def rect(x1, z1, x2, z2):
    return {(x, z) for x in range(x1, x2 + 1) for z in range(z1, z2 + 1)}


def octagon(cx, cz, radius, diagonal):
    return {(cx + dx, cz + dz) for dx in range(-radius, radius + 1)
            for dz in range(-radius, radius + 1) if abs(dx) + abs(dz) <= diagonal}


def adjacent(pos):
    return [tuple(pos[i] + d[i] for i in range(3)) for d in DIR.values()]


def state(registry, name, **props):
    schema = registry['blocks'].get(name)
    if schema is None or any(str(v).lower() not in schema.get(k, ()) for k, v in props.items()):
        raise UserError('Unsupported native plaza state: ' + str((name, props)))
    return name + ('[' + ','.join(k + '=' + str(v).lower() for k, v in sorted(props.items())) + ']' if props else '')


def panel(x, z):
    """Three-wide stone panels, true crossing bosses and narrow metal joints."""
    a, b = (x - CENTER[0]) % 4 == 0, (z - CENTER[1]) % 4 == 0
    return ('chipped:inlayed_calcite' if a and b else 'minecraft:polished_andesite' if a
            else 'minecraft:cut_copper' if b else 'minecraft:smooth_sandstone')


class Plaza:
    def __init__(self, registry, snapshot, *, excluded=None):
        self.registry, self.snapshot = registry, snapshot
        self.excluded = excluded or {}
        self.blocks, self.previous, self.priority, self.owners = {}, {}, {}, {}
        self.routes, self.grounds, self.joints, self.features = {}, {}, [], []
        self.group = 'Plaza'
        self.pipe_nodes, self.open_ports, self.machine_cells = set(), {}, set()
        self.dynamic_water = set()
        self.basin = octagon(*CENTER, 5, 8)

    def actual(self, pos):
        return self.snapshot.state(tuple(pos))

    def at(self, pos):
        return self.blocks.get(tuple(pos), self.actual(pos))

    def put(self, pos, name, *, phase=20, replace=False, **props):
        pos = tuple(pos)
        if len(pos) != 3 or any(type(n) is not int for n in pos):
            raise UserError('Integer plaza coordinates required')
        x, y, z = pos
        if not (1117 <= x <= 1149 and 61 <= y <= 76 and -1138 <= z <= -1108):
            raise UserError('Plaza escaped its finite owned envelope: ' + str(pos))
        old = self.actual(pos)
        if pos in self.snapshot.protected:
            raise UserError('Retain every saved plaza block entity: ' + str(pos))
        value = state(self.registry, name, **props)
        if pos in self.excluded and value != self.excluded[pos]:
            raise UserError('Preserve the complete neighboring composition, including AIR: ' + str(pos))
        if key(old) not in SOIL | SOFT:
            raise UserError('Plaza target contains a retained object/fluid: ' + str((pos, old)))
        if pos in self.blocks and self.blocks[pos] != value:
            if not replace:
                raise UserError('Two new plaza components overlap: ' + str((pos, self.blocks[pos], value)))
            self.joints.append({'pos': list(pos), 'before': self.blocks[pos], 'after': value,
                                'reason': self.group + ' explicit architectural joint'})
        self.blocks[pos], self.previous[pos] = value, old
        self.priority[pos], self.owners[pos] = phase, self.group
        if len(self.blocks) > MAX_CELLS:
            raise UserError('Split the bounded plaza proposal')

    def air(self, pos, **kwargs):
        self.put(pos, AIR, phase=0, **kwargs)

    def ground(self, x, z):
        if (x, z) in self.grounds:
            return self.grounds[x, z]['y']
        for y in range(70, 60, -1):
            old = self.actual((x, y, z))
            if key(old) in SOFT:
                continue
            if key(old) not in SOIL:
                raise UserError('No ordinary saved dry ground: ' + str((x, y, z, old)))
            self.grounds[x, z] = {'y': y, 'state': old}
            return y
        raise UserError('No bounded saved ground in plaza column')

    def surface(self, x, z, y=65, *, name=None, max_cut=0):
        g = self.ground(x, z)
        if not -max_cut <= y - g <= 2:
            raise UserError('Refuse a high artificial platform/terrain cut: ' + str((x, z, g, y)))
        for yy in range(g, y):
            self.put((x, yy, z), panel(x, z), phase=10)
        self.put((x, y, z), name or panel(x, z), phase=12)

    def walk(self, x, z, floor=65):
        self.routes[x, z] = floor
        for y in (floor + 1, floor + 2):
            self.air((x, y, z))

    def stair(self, pos, facing, *, material='minecraft:quartz_stairs', half='bottom', replace=False):
        self.put(pos, material, facing=facing, half=half, shape='straight', waterlogged=False, replace=replace)


def court(p):
    p.group = 'Jointed arrival, shaped court and public walking ring'
    main = octagon(*CENTER, 9, 14)
    machine = rect(1144, -1132, 1146, -1128)
    for x, z in sorted(main - p.basin - machine):
        p.surface(x, z)
        p.walk(x, z)
    # The actual registered spawn has dry soilY65. A small arrival atY66
    # supports feetY67 without moving spawn or leveling the whole district.
    for x, z in sorted(rect(1118, -1132, 1122, -1128)):
        p.surface(x, z, 66)
        p.walk(x, z, 66)
    for x in range(1123, 1131):
        for z in (-1131, -1130):
            p.surface(x, z)
            if x == 1123:
                p.stair((x, 66, z), 'west')
                p.routes[x, z] = 66
                for y in (67, 68):
                    p.air((x, y, z))
            else:
                p.walk(x, z)
    # New path in the actual dry inter-district gap. The neighboring authored
    # clearing starts atY66; the paving below it does not occupy that AIR.
    for z in range(-1118, -1107):
        for x in (1134, 1135):
            p.surface(x, z)
            p.walk(x, z)
    p.features.append('Small raised spawn arrival, descending half steps, jointed octagonal court, clear circumferential promenade and dry-gap path')


def basin(p):
    p.group = 'Undercut octagonal stone basin and sculpted coping'
    for x, z in sorted(p.basin):
        p.surface(x, z, 64)
        for y in range(65, 76):
            p.air((x, y, z))
    boundary = {(x, z) for x, z in p.basin if any((x+dx, z+dz) not in p.basin
                for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)))}
    for x, z in sorted(p.basin):
        if (x, z) in boundary:
            p.put((x, 65, z), panel(x, z), replace=True)
            dx, dz = x-CENTER[0], z-CENTER[1]
            face = ('east' if dx > 0 else 'west') if abs(dx) >= abs(dz) else ('south' if dz > 0 else 'north')
            if dx == 0 or dz == 0:
                p.put((x, 66, z), 'dawnoftimebuilder:marble_edge', facing=face,
                      half='top', shape='straight', waterlogged=False, replace=True)
            else:
                p.stair((x, 66, z), face, material='rechiseled:quartz_block_bordered_stairs'
                        if (x+z) % 3 else 'minecraft:waxed_cut_copper_stairs', replace=True)
        else:
            p.put((x, 65, z), 'minecraft:water', level=0, phase=100, replace=True)
    # Layered three-wide plinth is independent of the surrounding retained
    # reflecting pool. Molded columns and projecting scroll corbels add relief.
    for y in (65, 66, 67, 68):
        for x, z in sorted(rect(1137, -1128, 1139, -1126)):
            p.put((x, y, z), 'minecraft:chiseled_quartz_block' if y in (65, 68) else
                  'minecraft:waxed_weathered_cut_copper' if y == 67 else 'minecraft:quartz_bricks', replace=True)
    # Real coves beneath the copper ledge: the plinth is not four identical
    # full rectangular layers disguised by a different texture on each row.
    for x, z, face in ((1137, -1128, 'east'), (1139, -1128, 'west'),
                       (1137, -1126, 'east'), (1139, -1126, 'west')):
        p.stair((x, 66, z), face, half='top', replace=True)
        p.put((x, 67, z), 'dawnoftimebuilder:marble_coffer_slab', type='top',
              waterlogged=False, replace=True)
    for x, z, face in ((1134, -1127, 'west'), (1142, -1127, 'east'),
                       (1138, -1132, 'north'), (1138, -1123, 'south')):
        p.put((x, 65, z), 'minecraft:chiseled_quartz_block', replace=True)
        for y in (66, 67):
            p.put((x, y, z), 'dawnoftimebuilder:limestone_sided_column', facing=face,
                  vertical_connection='both' if y == 66 else 'under', waterlogged=False, replace=True)
        p.put((x, 68, z), 'mythrais:corbel_01_full_stone', colour=0, facing=face, replace=True)
        p.put((x, 69, z), 'dawnoftimebuilder:iron_fancy_lantern', facing='up',
              waterlogged=False, replace=True)
    for x, z, face in ((1136, -1126, 'west'), (1140, -1126, 'east')):
        p.put((x, 68, z), 'minecraft:chiseled_stone_bricks', replace=True)
        p.put((x, 69, z), 'dawnoftimebuilder:limestone_gargoyle', facing=face,
              humidity=0, persistent=True, waterlogged=False, replace=True)
    p.features.append('Full sealed basin floor and lower rim, proud stair-profile coping, three-wide tiered plinth, engaged limestone supports and twin carved guardians')


def gravity_header(p):
    p.group = 'Single-source header, narrow rills and real piston outlet'
    # Diamond floor with four ONE-wide arms: none of the upper liquid is seeded.
    for dx in range(-2, 3):
        for dz in range(-2, 3):
            if abs(dx)+abs(dz) > 2:
                continue
            pos = 1138+dx, 69, -1128+dz
            p.put(pos, panel(pos[0], pos[2]), replace=True)
            p.air((pos[0], 70, pos[2]), replace=True)
    for dx, dz in ((-1, -1), (-1, 1), (1, -1), (1, 1)):
        p.put((1138+dx, 70, -1128+dz), 'minecraft:waxed_cut_copper', replace=True)
    p.put((1138, 68, -1129), 'minecraft:chiseled_quartz_block', replace=True)
    for pos, face in (((1136, 68, -1128), 'west'), ((1140, 68, -1128), 'east'),
                      ((1138, 68, -1130), 'north'), ((1138, 68, -1126), 'south')):
        p.put(pos, 'mythrais:corbel_scroll_centre_stone', facing=face, shape=0, replace=True)
    for x, face in ((1137, 'west'), (1139, 'east')):
        for y in range(69, 72):
            p.put((x, y, -1129), 'dawnoftimebuilder:limestone_sided_column',
                  facing=face, vertical_connection='both',
                  waterlogged=False, replace=True)
        # This actual capital is1.5 blocks wide. Its quarter-block overhang is
        # high above circulation and deliberately frames the narrow crown.
        p.put((x, 72, -1129), 'mythrais:cloverleaf_column_capital_stone',
              colour=0, facing=face, replace=True)
    # Closed header, one outlet on its south wall, pipe-fed only from above.
    p.put((1138, 72, -1129), 'minecraft:chiseled_quartz_block', replace=True)
    for pos in ((1137, 73, -1129), (1139, 73, -1129),
                (1137, 73, -1130), (1138, 73, -1130), (1139, 73, -1130)):
        p.put(pos, 'minecraft:waxed_weathered_cut_copper', replace=True)
    p.air(HEADER, replace=True)
    p.air(OUTLET, replace=True)
    for y in (71, 72):
        p.air((1138, y, -1128), replace=True)
    p.put(PISTON, 'minecraft:sticky_piston', facing='north', extended=False, replace=True)
    p.put(PLUG_OPEN, 'minecraft:chiseled_quartz_block', replace=True)
    for x in (1137, 1139):
        p.put((x, 74, -1129), 'minecraft:waxed_cut_copper', replace=True)
        p.put((x, 74, -1130), 'minecraft:waxed_cut_copper', replace=True)
        p.put((x, 75, -1130), 'supplementaries:statue', facing='west', lit=False,
              powered=False, waterlogged=False, replace=True)
    p.put((1138, 74, -1130), 'dawnoftimebuilder:marble_coffer_slab', type='bottom', waterlogged=False, replace=True)
    p.put((1136, 72, -1129), 'mythrais:corbel_scroll_centre_stone', facing='west', shape=0, replace=True)
    # Its pinned model spans about1.82x1.65 blocks; keep this projecting lancet
    # on the dry west display face, away from header/port and public headroom.
    p.put((1136, 73, -1129), 'mythrais:single_lancet_arch_upper_stone', facing='west',
          colour=0, mirrored=False, replace=True)
    # Source witnesses reserve every falling column. OFF must remove flowing
    # water here by normal updates, while the reflecting pool may retain it.
    for x, _, z in JET_WITNESSES:
        for y in range(66, 71):
            p.air((x, y, z), replace=True)
            p.dynamic_water.add((x, y, z))
    for dx, dz in ((0, 0), (-1, 0), (1, 0), (0, -1), (0, 1),
                   (-2, 0), (2, 0), (0, -2), (0, 2)):
        p.dynamic_water.add((1138+dx, 70, -1128+dz))
    p.dynamic_water.update({HEADER, OUTLET, (1138, 72, -1128), (1138, 71, -1128)})
    p.features.append('Enclosed initially-dry pump-fed header, actual sliding stone plug, four narrow nonsource gravity cascades and sculpted upper bowl')


def controls(p):
    p.group = 'Accessible real STOP lever and enclosed normal redstone riser'
    p.put((1141, 66, -1125), 'minecraft:chiseled_quartz_block', replace=True)
    p.put(STOP_LEVER, 'minecraft:lever', face='wall', facing='east', powered=False, replace=True)
    # Six ordinary torch inversions: powered lever means powered piston/CLOSED.
    p.put((1141, 67, -1125), 'minecraft:redstone_torch', lit=True, replace=True)
    for y in range(68, 74):
        x = 1141 if y % 2 == 0 else 1140
        p.put((x, y, -1125), 'minecraft:waxed_weathered_cut_copper' if y % 2 else
              'minecraft:chiseled_quartz_block', replace=True)
        if y < 73:
            tx = 1140 if x == 1141 else 1141
            p.put((tx, y, -1125), 'minecraft:redstone_wall_torch',
                  facing='west' if tx < x else 'east', lit=(y % 2 == 1), replace=True)
    for x, z in ((1139, -1125), (1139, -1124), (1138, -1124), (1138, -1125)):
        p.put((x, 72, z), 'minecraft:quartz_bricks' if z == -1124 else 'minecraft:waxed_cut_copper', replace=True)
    wires = (((1139, 73, -1125), {'north': 'side', 'south': 'side'}),
             ((1139, 73, -1124), {'north': 'side', 'west': 'side'}),
             ((1138, 73, -1124), {'north': 'side', 'east': 'side'}))
    for pos, ports in wires:
        p.put(pos, 'minecraft:redstone_wire', power=0,
              **{d: ports.get(d, 'none') for d in ('north', 'east', 'south', 'west')}, replace=True)
    # Mojang DiodeBlock reads input at pos.relative(FACING). SOUTH therefore
    # reads the south dust and sends output north into the actual piston.
    p.put((1138, 73, -1125), 'minecraft:repeater', facing='south', delay=1,
          locked=False, powered=False, replace=True)
    p.features.append('Ground-reachable STOP lever, six real torch stages, shaped support bridge and normal repeater into the sticky piston; no wireless NBT or scripted switch')


def pipework(p):
    p.group = 'Actual Create pump feed and observable jointed riser'
    nodes = {(1139, 66, -1129), (1141, 66, -1129), (1142, 66, -1129)}
    nodes |= {(1142, y, -1129) for y in range(67, 75)}
    nodes |= {(x, 74, -1129) for x in range(1138, 1142)}
    p.pipe_nodes = nodes
    p.open_ports = {(1139, 66, -1129): 'down', (1138, 74, -1129): 'down'}
    for pos in sorted(nodes):
        x, y, z = pos
        glass = x == 1142 and y in (69, 72) or pos == (1141, 66, -1129)
        if glass:
            p.put(pos, 'create:glass_fluid_pipe', axis='x' if y == 66 else 'y',
                  alt=False, waterlogged=False, replace=True)
        else:
            ports = {d: tuple(pos[i]+v[i] for i in range(3)) in nodes | {PUMP}
                     or p.open_ports.get(pos) == d for d, v in DIR.items()}
            p.put(pos, 'create:fluid_pipe', waterlogged=False, **ports, replace=True)
    p.put(PUMP, 'create:mechanical_pump', facing='east', waterlogged=False, replace=True)
    p.put((1140, 66, -1130), 'create:cogwheel', axis='x', waterlogged=False, replace=True)
    for x in range(1141, 1145):
        if x == 1142:
            p.put((x, 66, -1130), 'create:clutch', axis='x', powered=False, replace=True)
        elif x == 1143:
            p.put((x, 66, -1130), 'create:andesite_encased_shaft', axis='x', replace=True)
        else:
            p.put((x, 66, -1130), 'create:shaft', axis='x', waterlogged=False, replace=True)
    p.put(WHEEL, 'create:water_wheel', facing='west', replace=True)
    p.features.append('Real cog-meshed east-facing pump, 15-edge output route, separated intake, glass inspection joints and ordinary wheel/shaft/clutch drive')


def wheelhouse(p):
    p.group = 'Contained wheel niche and carved service canopy'
    for x, z in sorted(rect(1144, -1132, 1146, -1128)):
        p.surface(x, z, 63, max_cut=1)
        for y in range(64, 71):
            p.air((x, y, z), replace=True)
    # Narrow spill chamber; front models remain transparent around the wheel.
    for y in range(64, 70):
        for x in (1144, 1146):
            for z in range(-1132, -1127):
                if (x, y, z) == (1144, 66, -1130):
                    continue
                if x == 1144 and z in (-1130, -1129) and y in (65, 67):
                    p.put((x, y, z), 'mcwwindows:stone_four_window', facing='west',
                          windowstate='locked', replace=True)
                else:
                    p.put((x, y, z), panel(x, z) if y % 3 else
                          'minecraft:cut_copper' if z == -1130 else 'minecraft:chiseled_quartz_block', replace=True)
        for z in (-1132, -1128):
            p.put((1145, y, z), 'minecraft:chiseled_quartz_block' if y % 3 == 0 else
                  'minecraft:waxed_weathered_cut_copper', replace=True)
    for x in range(1144, 1147):
        for z in range(-1132, -1127):
            p.put((x, 70, z), 'minecraft:waxed_cut_copper_slab', type='bottom', waterlogged=False, replace=True)
    for pos in (WHEEL_SOURCE, (1145, 68, -1131), (1145, 67, -1131),
                (1145, 66, -1131), (1145, 65, -1131), (1145, 64, -1131)):
        p.air(pos, replace=True)
        p.dynamic_water.add(pos)
    # R2's open south source face also fed the opposite side of the wheel.
    # A full, non-waterloggable carved keystone spans the two actual sidewalls
    # above its3x3 physical wheel volume. It leaves only the intended north fall.
    p.put(WHEEL_BAFFLE, 'rechiseled:quartz_block_chiseled_pillar', replace=True)
    # Restore exactly the single shaft opening and actual wheel after niche air.
    p.put((1144, 66, -1130), 'create:shaft', axis='x', waterlogged=False, replace=True)
    p.put(WHEEL, 'create:water_wheel', facing='west', replace=True)
    for x, z, face in ((1144, -1132, 'west'), (1146, -1128, 'east')):
        p.put((x, 69, z), 'mythrais:corbel_scroll_centre_stone', facing=face, shape=0, replace=True)
    p.features.append('Independent sealed gravity wheel-drop, ordinary dry commissioning source, framed inspection glass, undercut copper hood and scroll corbels')


def furnishings(p):
    p.group = 'Human-scale seating, contained plants and warm sculpted lights'
    for x, z, face in ((1128, -1124, 'east'), (1128, -1122, 'east'),
                       (1148, -1124, 'west'), (1148, -1122, 'west')):
        p.surface(x, z)
        p.routes.pop((x, z), None)
        p.put((x, 66, z), 'handcrafted:dark_oak_bench', facing=face, color='none',
              shape='single', waterlogged=False, replace=True)
    for x, z in ((1128, -1123), (1148, -1123)):
        p.surface(x, z)
        p.routes.pop((x, z), None)
        p.put((x, 66, z), 'handcrafted:dark_oak_side_table', replace=True)
        p.put((x, 67, z), 'handcrafted:wood_cup', facing='south', waterlogged=False, replace=True)
    p.put((1128, 67, -1123), 'handcrafted:golden_wide_pot', replace=True)
    for x, z in ((1129, -1120), (1146, -1120)):
        p.surface(x, z)
        p.routes.pop((x, z), None)
        p.put((x, 66, z), 'rechiseled:quartz_block_chiseled_pillar', replace=True)
        p.put((x, 67, z), 'mcwlights:golden_triple_candle_holder', facing='north', lit=True, replace=True)
    for x, z in ((1129, -1135), (1147, -1136), (1128, -1120), (1147, -1120)):
        p.surface(x, z)
        p.routes.pop((x, z), None)
        p.put((x, 66, z), 'minecraft:chiseled_quartz_block', replace=True)
        p.put((x, 67, z), 'dawnoftimebuilder:limestone_sided_column', facing='west',
              vertical_connection='none', waterlogged=False, replace=True)
        p.put((x, 68, z), 'mcwlights:covered_garden_light', lit=True, powered=False, replace=True)
    for x, z in ((1131, -1134), (1145, -1135), (1131, -1120), (1144, -1119)):
        p.surface(x, z)
        p.routes.pop((x, z), None)
        p.put((x, 66, z), 'dawnoftimebuilder:marble_big_flower_pot', waterlogged=False, replace=True)
        p.put((x, 67, z), 'minecraft:flowering_azalea', replace=True)
    p.features.append('Two asymmetric paired-bench pockets, real cups/tables, contained planted urns, and carved low lantern standards off the walking ring')


def validate(p):
    if p.at(HEADER) != AIR or p.at(WHEEL_SOURCE) != AIR:
        raise UserError('Header and wheel feed MUST remain dry until real native commissioning')
    if key(p.at(WHEEL_BAFFLE)) != 'rechiseled:quartz_block_chiseled_pillar':
        raise UserError('A full source-side baffle must prevent an opposing wheel-face fall')
    if key(p.at(PISTON)) != 'minecraft:sticky_piston' or 'facing=north' not in p.at(PISTON) or 'extended=false' not in p.at(PISTON):
        raise UserError('The ordinary north-facing retracted gate is required')
    if key(p.at(PLUG_OPEN)) != 'minecraft:chiseled_quartz_block' or p.at(OUTLET) != AIR:
        raise UserError('The gate must have one solid plug and a clear one-block travel/outlet')
    if 'facing=south' not in p.at((1138, 73, -1125)):
        raise UserError('The repeater must read its south input and output north to the piston')
    for pos in JET_WITNESSES:
        if p.at(pos) != AIR:
            raise UserError('The upper jet baseline must be genuinely dry')
    high_sources = [pos for pos, s in p.blocks.items() if key(s) == 'minecraft:water' and pos[1] > 65]
    if high_sources:
        raise UserError('No header, jet or wheel-feed water may be seeded in the architecture plan')
    # Exact connected pipe graph, no extra branches, with source/target endpoints.
    start, goal = (1139, 66, -1129), (1138, 74, -1129)
    graph = p.pipe_nodes | {PUMP}
    q, seen = deque([(start, 0)]), {start}
    distance = None
    while q:
        pos, steps = q.popleft()
        if pos == goal:
            distance = steps + 1
        for other in adjacent(pos):
            if other in graph and other not in seen:
                seen.add(other); q.append((other, steps + 1))
    if seen != graph or distance is None or distance > 16:
        raise UserError('The real source-pump-header graph exceeds its pinned range or is disconnected')
    for (x, z), floor in p.routes.items():
        if key(p.at((x, floor, z))) in SOFT | {'minecraft:water'}:
            raise UserError('Plaza route lacks an authored solid floor')
        if any(p.at((x, y, z)) != AIR for y in (floor+1, floor+2)):
            raise UserError('Plaza architecture blocks a protected route: ' + str((x, z, floor)))
    start2 = SPAWN[0], SPAWN[2]
    seen2, q2 = {start2}, deque([start2])
    while q2:
        x, z = q2.popleft()
        for other in ((x-1, z), (x+1, z), (x, z-1), (x, z+1)):
            if other in p.routes and other not in seen2 and abs(p.routes[other]-p.routes[x, z]) <= 1:
                seen2.add(other); q2.append(other)
    if not {(1130, -1127), (1147, -1127), (1134, -1108)} <= seen2:
        raise UserError('The arrival, fountain promenade and new dry-gap connection must connect')
    material = require_material_rule(p.blocks, 'Complete new starting plaza and fountain, all machinery and foundations')
    outdoor = require_outdoor_rule(p.blocks, 'All new plaza surfaces')
    return {'material': material, 'outdoor': outdoor, 'route_columns': len(p.routes),
            'source_to_header_edges_including_intake': distance,
            'initial_header_and_upper_jets_dry': True, 'saved_BE_targets': 0,
            'native_pump_transfer_gate_drain_and_actual_walking': 'PENDING',
            'artistic_acceptance': False}


def construct(registry, snapshot, excluded=None):
    p = Plaza(registry, snapshot, excluded=excluded)
    court(p); basin(p); gravity_header(p); controls(p); pipework(p); wheelhouse(p); furnishings(p)
    validate(p)
    return p


def payload(registry, backup_sha, blocks, name, *, before=False, priority=None):
    palette = sorted(set(blocks.values())); index = {s: i for i, s in enumerate(palette)}
    ordered = sorted(blocks, key=lambda p: ((priority or {}).get(p, 0), p))
    doc = {'format': 'awft-native-settlement:1', 'name': name, 'created': utcnow(),
           'seed': registry['seed'], 'world_path': registry['world_path'], 'backup_sha256': backup_sha,
           'bounds': [min(p[0] for p in blocks), min(p[2] for p in blocks), max(p[0] for p in blocks), max(p[2] for p in blocks)],
           'palette': palette, 'blocks': [[*p, index[blocks[p]]] for p in ordered],
           'block_entities': [], 'commands': [], 'landmarks': [], 'prototype_only': True,
           'validation': 'Bounded source proposal; exact native before/place/settle, pumped commissioning and game art required'}
    if before:
        doc.update(verification_only=True, construction_forbidden=True)
    return doc


def prepare(home, registry_path, backup_id, backup_sha, output):
    home, output = Path(home).resolve(), Path(output).resolve()
    if output.exists() or not output.is_relative_to(home/'staging'):
        raise UserError('A new private immutable plaza proposal folder is required')
    reserve = guard(16*1024**2, 32*1024**2)
    receipt = read_json(home/'dashboard/settlement/backup-receipt.json')
    registry = read_json(registry_path)
    if receipt.get('verified') is not True or (receipt.get('id'), receipt.get('sha256')) != (backup_id, backup_sha):
        raise UserError('Bind the exact current stopped checkpoint')
    if tuple(registry['spawn']) != SPAWN:
        raise UserError('The registered protected spawn differs')
    jar = home/'server/mods/create-1.21.1-6.0.10.jar'
    if digest(jar) != CREATE_SHA:
        raise UserError('Review the actual pinned Create hydraulics again')
    excluded, sources = {}, []
    for relative in EXCLUSIONS:
        path = home/'staging'/relative; doc = read_json(path)
        if doc['world_path'] != registry['world_path'] or str(doc['seed']) != str(registry['seed']):
            raise UserError('The neighboring complete source belongs to another world')
        excluded.update({tuple(row[:3]): doc['palette'][row[3]] for row in doc['blocks']})
        sources.append({'path': str(path), 'sha256': digest(path)})
    snapshot = BackupWorld(home, receipt, registry)
    try:
        p = construct(registry, snapshot, excluded)
        checks = validate(p); saved_sources = snapshot.sources[:]
        full = payload(registry, backup_sha, p.blocks, 'Original sculpted starting plaza and pump-fed fountain', priority=p.priority)
        before = payload(registry, backup_sha, p.previous, 'VERIFY ONLY exact saved plaza preimage', before=True)
        reserved = set(p.blocks)
        # Explicit headroom and visible arrival corridor for the forest planner.
        view = set()
        for n in range(21):
            x = round(1120+(1138-1120)*n/20); z = round(-1130+3*n/20)
            for dx in (-1, 0, 1):
                for y in range(67, 76):
                    view.add((x+dx, y, z))
        reserved |= view | p.dynamic_water
        mask = payload(registry, backup_sha, {pos: AIR for pos in reserved},
                       'RESERVATION ONLY plaza geometry, body/headroom, water and arrival sightline', before=True)
        mask['reservation_only'] = True
        hydraulics = {'pump': list(PUMP), 'pump_facing': 'east', 'pump_rotation_axis': 'x',
            'wheel': list(WHEEL), 'wheel_facing': 'west', 'clutch': [1142, 66, -1130],
            'commission_only_water_source': list(WHEEL_SOURCE), 'header_initial_air': list(HEADER),
            'intake_world_water': [1139, 65, -1129], 'header_open_pipe': [1138, 74, -1129],
            'piston': list(PISTON), 'piston_facing': 'north', 'open_plug': list(PLUG_OPEN),
            'closed_plug_and_outlet': list(OUTLET), 'stop_lever': list(STOP_LEVER),
            'lever_powered_true_means': 'STOP / real extended piston blocks the outlet',
            'jet_witnesses': [list(v) for v in JET_WITNESSES],
            'upper_water_allowlist': [list(v) for v in sorted(p.dynamic_water)],
            'basin_floor_y': 64, 'reflecting_pool_y': 65,
            'normal_backpressure': 'Pump legitimately stops transferring after the enclosed header is a water source; this is not continuous open-pipe throughput.',
            'commission_gate': 'Prove dry header/jets and zero rotation first; seed ONLY independent wheel feed with normal updates; observe real wheel/meshed pump and newly water-filled header, STOP drain, START restart, repeat and restart persistence. Never set kinetic/fluid/flow NBT.'}
    finally:
        snapshot.close()
    manifest = {'format': 'awft-sculpted-starting-plaza:1', 'created': utcnow(),
                'source_sha256': digest(Path(__file__)), 'registry_sha256': digest(Path(registry_path)),
                'checkpoint_id': backup_id, 'checkpoint_sha256': backup_sha,
                'actual_ground': [{'x': x, 'z': z, **v} for (x, z), v in sorted(p.grounds.items())],
                'preserved_neighbor_sources': sources, 'saved_sources': saved_sources,
                'checks': checks, 'features': p.features, 'routes': [[x, y, z] for (x, z), y in sorted(p.routes.items())],
                'explicit_joints': p.joints, 'hydraulics': hydraulics,
                'cameras': [
                    {'name': 'fountain-arrival', 'feet': [1120.5, 67, -1129.5], 'look_at': [1138, 70, -1127]},
                    {'name': 'fountain-west-eye', 'feet': [1128.5, 66, -1126.5], 'look_at': [1138, 70, -1128]},
                    {'name': 'fountain-north-eye', 'feet': [1138.5, 66, -1138], 'look_at': [1138, 70, -1128]},
                    {'name': 'fountain-east-eye', 'feet': [1149, 66, -1127], 'look_at': [1138, 70, -1128]},
                    {'name': 'fountain-south-eye', 'feet': [1138, 66, -1117], 'look_at': [1138, 70, -1128]},
                    {'name': 'fountain-wheel-service', 'feet': [1148, 66, -1134], 'look_at': [1145, 66, -1130]},
                    {'name': 'fountain-crown', 'feet': [1133, 72, -1136], 'look_at': [1138, 72, -1128]},
                    {'name': 'fountain-night-arrival', 'feet': [1120.5, 67, -1129.5], 'look_at': [1138, 70, -1127], 'required_lighting': 'actual night'}],
                'native_actions': 0,
                'world_writes': 0, 'entities': 0, 'inventories_seeded': 0,
                'reserve_guard': reserve, 'files': {}}
    docs = {'plaza.json': full, 'plaza-native-before.json': before,
            'forest-reservation-ONLY.json': mask, 'hydraulics.json': hydraulics}
    raw = {name: (json.dumps(doc, separators=(',', ':'))+'\n').encode() for name, doc in docs.items()}
    for name, content in raw.items():
        manifest['files'][name] = {'sha256': hashlib.sha256(content).hexdigest(), 'bytes': len(content)}
    raw['manifest.json'] = (json.dumps(manifest, indent=2)+'\n').encode()
    if sum(map(len, raw.values())) > MAX_OUTPUT:
        raise UserError('Finite plaza output exceeded before writing')
    output.mkdir()
    for name, content in raw.items():
        (output/name).write_bytes(content)
    sha = hashlib.sha256(raw['manifest.json']).hexdigest()
    (output/'manifest.json.complete').write_text(sha+'\n', encoding='ascii')
    return {'output': str(output), 'manifest_sha256': sha, 'placements': len(p.blocks),
            'changed_positions': sum(v != p.previous[k] for k, v in p.blocks.items()), 'checks': checks}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ('home', 'registry', 'output'):
        parser.add_argument('--'+arg, required=True, type=Path)
    parser.add_argument('--backup-id', required=True); parser.add_argument('--backup-sha256', required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.home, args.registry, args.backup_id, args.backup_sha256, args.output), indent=2))
