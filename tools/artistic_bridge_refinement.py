"""Original Lanternwater bridge refinement; private proposal, never native action.

Rebuilds the silhouette of the two leaves and their bank architecture from the
exact contained-plant master. Native commissioning evidence never transfers.
"""
from __future__ import annotations

import argparse
from collections import Counter
import copy
import hashlib
import json
import math
from pathlib import Path

from control_room.common import UserError, digest, read_json
from tools.artistic_materials import require_material_rule, require_outdoor_rule
from tools.playtest import guard
from tools.settlement_attractions import BackupWorld, NATURAL, base, properties
from tools.settlement_drawbridge import placed_systems, placed_radios, clearance_estimate, open_angle
from tools.artistic_mill_orientation import saved_chunk

MIB = 1024**2
MAX_OUTPUT = 16*MIB
MASTER_SHA = 'f9b3a7514bc7192f37118937ee500efe179aef45ebb905e8342b55d64a6edcfd'
ROSEBRIDGE_SHA = '9c9b37cea97a69d9f510bfed83b70c072793ebc35fed175ce50b3355506a51f2'
CRAFT_LANE_SHA = 'f155f49910211043c523309a26066fbd70c995f6edab9578950927d5e07a8244'
AIR = 'minecraft:air'
BOUNDS = (1177, 55, -1202, 1230, 88, -1082)
LEAVES = (('north', -1172, 1, 29), ('south', -1116, -1, 28))
BUTTONS = ((1182, 73, -1178), (1182, 73, -1110))
FOOTING_SOLIDS = {'minecraft:'+name for name in (
    'stone', 'andesite', 'diorite', 'granite', 'grass_block', 'dirt', 'coarse_dirt',
    'rooted_dirt', 'sand', 'sandstone', 'gravel', 'clay', 'calcite', 'stone_bricks',
    'chiseled_stone_bricks', 'polished_andesite')}
FOOTING_SOLIDS.update({'chipped:'+name for name in (
    'small_andesite_bricks', 'small_stone_bricks', 'etched_stone_bricks',
    'carved_stone', 'engraved_stone')})
FOOTING_SOLIDS.update({'create:limestone', 'create:zinc_ore'})
CAMERAS = (
    {'name': 'river-clearance-comparison', 'feet': [1168, 64, -1144], 'target': [1193, 73, -1144],
     'yaw': -90.0, 'pitch': -16.4466,
     'reference_image_sha256': '10e329aa31efdb1fe4037b757703d5820c2953a4e9a55e6165d6aff52c9b499d',
     'purpose': 'Exact actual candidate37 river pose; match prior FOV/time/shader separately'},
    {'name': 'north-road', 'feet': [1193, 71, -1183], 'target': [1193, 72, -1138]},
    {'name': 'river-quarter', 'feet': [1165, 83, -1187], 'target': [1196, 73, -1148]},
    {'name': 'south-control-room', 'feet': [1183, 71, -1107], 'target': [1182, 73, -1110]},
    {'name': 'north-machinery', 'feet': [1221, 70, -1183], 'target': [1216, 72, -1172]},
    {'name': 'under-girders', 'feet': [1179, 64, -1158], 'target': [1193, 69, -1147]},
)


def flatten(plan):
    result = {tuple(row[:3]): plan['palette'][row[3]] for row in plan['blocks']}
    if len(result) != len(plan['blocks']):
        raise UserError('Duplicate baseline geometry is not reviewable')
    return result


def encoded(document):
    return (json.dumps(document, ensure_ascii=False, separators=(',', ':'))+'\n').encode()


def leaf_name(pos):
    x, y, z = pos
    if 1187 <= x <= 1198 and 69 <= y <= 74:
        if -1172 <= z <= -1144: return 'north'
        if -1143 <= z <= -1116: return 'south'
    return None


class Refinement:
    def __init__(self, registry, master, exclusions=(), footing=None, water_y=62):
        self.registry, self.master = registry, master
        self.original = flatten(master)
        self.blocks = dict(self.original)
        self.tags = copy.deepcopy(master['block_entities'])
        self.protected = {tuple(row['pos']) for row in self.tags}
        self.protected.update(pos for pos, state in self.original.items()
                              if base(state).startswith('create:') or base(state) in ('minecraft:stone_button', 'minecraft:potted_flowering_azalea_bush'))
        # Retain real radio/button supports and the existing useful furniture.
        for z in (-1178, -1110):
            self.protected.update((1182, y, z) for y in (70, 71, 72, 73))
        self.protected.update(pos for pos, state in self.original.items() if base(state).startswith('handcrafted:'))
        self.protected.update((x, y-1, z) for x, y, z in tuple(self.protected)
                              if base(self.original.get((x, y, z), '')).endswith('_sign'))
        self.excluded = set().union(*(set(flatten(plan)) for plan in exclusions)) if exclusions else set()
        self.footing = footing or (lambda x, z: 60)
        self.water_y = water_y
        self.groups, self.routes, self.notes = {}, [], []
        self.group = 'fixed masonry'

    def state(self, key, **props):
        schema = self.registry['blocks'].get(key)
        if schema is None or any(str(v).lower() not in schema.get(k, ()) for k, v in props.items()):
            raise UserError('Unregistered exact bridge refinement state: '+key+' '+str(props))
        return key+('['+','.join(k+'='+str(v).lower() for k, v in sorted(props.items()))+']' if props else '')

    def put(self, wx, wy, wz, key, **props):
        pos = wx, wy, wz
        if any(not BOUNDS[i] <= pos[i] <= BOUNDS[i+3] for i in range(3)):
            raise UserError('Refinement escaped its finite bridge envelope')
        value = self.state(key, **props)
        if pos in self.protected and value != self.original.get(pos):
            raise UserError('Preserve exact native machinery, controls, furniture and BE: '+str(pos))
        if pos in self.excluded and value != self.original.get(pos):
            raise UserError('Preserve the fixed rosebridge or another supplied authored footprint: '+str(pos))
        self.blocks[pos] = value
        self.groups.setdefault(self.group, set()).add(pos)

    def clear(self, x, y, z):
        if (x, y, z) not in self.protected:
            self.put(x, y, z, AIR)

    def stair(self, x, y, z, key, facing, half='bottom'):
        self.put(x, y, z, key, facing=facing, half=half, shape='straight', waterlogged=False)

    def stone(self, x, y, z):
        # Actual ashlar piers, string courses and vertical dressed joints.
        masonry = ('chipped:small_andesite_bricks', 'chipped:small_stone_bricks',
                   'chipped:etched_stone_bricks', 'chipped:carved_stone',
                   'minecraft:polished_andesite', 'minecraft:stone_bricks',
                   'minecraft:chiseled_stone_bricks', 'chipped:engraved_stone')
        key = masonry[(2 if x % 4 == 0 else 0)+(1 if z % 4 == 0 else 0)+(4 if y % 4 == 0 else 0)]
        self.put(x, y, z, key)

    def board(self, x, y, z):
        self.put(x, y, z, 'chipped:boxed_spruce_planks' if x % 4 == 0 else
                 'chipped:nailed_dark_oak_planks' if z % 4 == 0 else 'minecraft:spruce_planks')

    def lamp(self, x, y, z, hanging=False):
        self.put(x, y, z, 'minecraft:lantern', hanging=hanging, waterlogged=False)


def articulated_leaves(p):
    for name, pivot, direction, length in LEAVES:
        p.group = name+' complete moving leaf'
        joints = {0, 7, 14, 21, length-1}
        for n in range(length):
            z = pivot+direction*n
            # Same Y71 walk top, half the opaque deck thickness. The root row
            # stays full-block and exactly attached to the existing bearing.
            if n:
                for x in range(1187, 1199):
                    seam = (x-1187) % 4 == 3
                    wood = ('oak' if seam else 'dark_oak') if n % 7 == 0 else ('dark_oak' if seam else 'spruce')
                    p.put(x, 70, z, 'minecraft:'+wood+'_slab', type='top', waterlogged=False)
            # Remove the heavy T posts/caps, V-stair panels and full-depth ribs.
            for x in range(1187, 1199): p.clear(x, 69, z)
            for x in (1187, 1198):
                for y in range(71, 75): p.clear(x, y, z)
                if n in joints:
                    p.put(x, 71, z, 'create:metal_girder', axis='y', x=False, z=False, top=True, bottom=True, waterlogged=False)
                    if n in (7, 21):
                        p.put(x, 72, z, 'minecraft:iron_bars', north=False, south=False, east=False, west=False, waterlogged=False)
                        p.lamp(x, 73, z)
                else:
                    # Pinned mod-native open ironwork, never a painted full wall.
                    p.put(x, 71, z, 'mythrais:wrought_iron_railing_01', facing='west' if x == 1187 else 'east', shape='0')
            # Two slender, segmented bottom chords taper out before the nose.
            if n < length-3:
                for x in (1188, 1197):
                    if n in joints:
                        p.put(x, 69, z, 'createdeco:industrial_iron_sheet_metal', axis='y', east=False, north=False, south=False, west=False)
                    else:
                        p.put(x, 69, z, 'create:metal_girder', axis='z', x=False, z=True, top=False, bottom=False, waterlogged=False)
            if n in joints:
                for x in range(1187, 1199):
                    if x in (1188, 1197) and n < length-3:
                        p.put(x, 69, z, 'createdeco:industrial_iron_sheet_metal', axis='y', east=False, north=False, south=False, west=False)
                    elif x in (1192, 1193):
                        p.put(x, 69, z, 'createdeco:industrial_iron_support', facing='up', waterlogged=False)
                    else:
                        p.put(x, 69, z, 'dawnoftimebuilder:dark_oak_support_beam', axis='x', pillar_connection='nothing', subaxis=False, waterlogged=False)
        # The walking surface and root attachment remain; the physical deck is
        # thinner, so old assembly and collision receipts cannot be reused.
        p.notes.append(name+': articulated ironwork and thin ribs replace the original timber T silhouette; new glue and motion proof required')


def shaped_banks(p):
    p.group = 'complete shaped bank masonry'
    for north, za, zb in ((True, -1185, -1173), (False, -1115, -1103)):
        center = (za+zb)//2
        for z in range(za, zb+1):
            end = abs(z-center)
            half = 7 if end <= 3 else 6 if end == 4 else 5 if end == 5 else 4
            for x in range(1186, 1201):
                for y in range(60, 70):
                    pos = x, y, z
                    if pos in p.protected: continue
                    if abs(x-1193) > half and pos in p.original and base(p.original[pos]) not in (AIR, 'minecraft:water'):
                        p.put(x, y, z, 'minecraft:water', level=0) if y <= p.water_y else p.put(x, y, z, AIR)
                    elif (abs(x-1193) == half and pos in p.original
                          and base(p.original[pos]) not in (AIR, 'minecraft:water')):
                        p.stone(x, y, z)
            # The old approach floor is retained; new coping follows its curve.
            for x in (1193-half, 1193+half):
                if x in (1186, 1200) and (x, 71, z) not in p.protected:
                    if (z-za) % 4 == 0:
                        p.stone(x, 71, z)
                        p.put(x, 72, z, 'minecraft:stone_brick_slab', type='bottom', waterlogged=False)
                    else:
                        p.put(x, 71, z, 'minecraft:stone_brick_wall', waterlogged=False)
        # A real pointed west cutwater, with stepped shoulders rather than a box.
        for dx, width in ((1, 2), (2, 1), (3, 0)):
            x = 1186-dx
            for dz in range(-width, width+1):
                for y in range(p.footing(x, center+dz), 69):
                    if (x, y, center+dz) not in p.protected: p.stone(x, y, center+dz)
                p.stair(x, 69, center+dz, 'minecraft:polished_andesite_stairs', 'east')
        # Carved recesses in the landward shoulders stop above the waterline.
        for zc in (center-3, center+3):
            for z in range(zc-1, zc+2):
                for y in range(64, 68):
                    if (1186, y, z) not in p.protected: p.put(1186, y, z, AIR)
            p.stair(1186, 68, zc-1, 'minecraft:stone_brick_stairs', 'south', 'top')
            p.stone(1186, 68, zc)
            p.stair(1186, 68, zc+1, 'minecraft:stone_brick_stairs', 'north', 'top')


def control_pavilion(p, z, name):
    p.group = name+' complete control pavilion'
    # Bankward west lookouts; the east small-bridge junction remains untouched.
    cells = {(x, dz) for x in range(1179, 1187) for dz in range(-4, 5)
             if not (x in (1179, 1186) and abs(dz) == 4)}
    for x, dz in sorted(cells):
        wz = z+dz
        for y in range(71, 82): p.clear(x, y, wz)
        if (x, 70, wz) not in p.protected: p.board(x, 70, wz)
        edge = any((x+dx, dz+oz) not in cells for dx, oz in ((1, 0), (-1, 0), (0, 1), (0, -1)))
        if edge:
            for y in range(71, 82):
                if (x, y, wz) in p.protected: continue
                corner = x in (1179, 1186) or abs(dz) == 4 and x in (1180, 1185)
                if y in (74, 77, 81):
                    p.put(x, y, wz, 'chipped:stacked_dark_oak_planks' if x % 4 == 0 or dz % 4 == 0 else 'minecraft:dark_oak_log', **({} if x % 4 == 0 or dz % 4 == 0 else {'axis': 'x'}))
                elif corner:
                    p.put(x, y, wz, 'minecraft:stripped_dark_oak_log' if y not in (74, 80) else 'chipped:nailed_dark_oak_planks', **({'axis': 'y'} if y not in (74, 80) else {}))
                else:
                    p.put(x, y, wz, 'minecraft:smooth_sandstone')
        # The gallery is a real floor, with a deliberate two-wide stair opening.
        stair_opening = x >= 1184 and -3 <= dz <= 1 or x == 1183 and dz in (1, 2)
        if not edge and not stair_opening: p.board(x, 76, wz)
    for x in (1180, 1185):
        for dz in (-3, 3):
            for y in range(p.footing(x, z+dz), 70): p.stone(x, y, z+dz)
    # A six-rise L stair avoids both the bank button and real radio.
    for i in range(4):
        for x in (1184, 1185): p.stair(x, 71+i, z-3+i, 'minecraft:dark_oak_stairs', 'south')
    for i in range(2):
        for dz in (1, 2): p.stair(1183-i, 75+i, z+dz, 'minecraft:dark_oak_stairs', 'west')
    for y, half in ((71, 'lower'), (72, 'upper')):
        p.put(1186, y, z+3, 'mcwdoors:dark_oak_classic_door', facing='east', half=half, hinge='left', open=False, powered=False)
    # Large proper modded windows replace slit-like facade punctuation.
    for side in (1179, 1186):
        for dz, column in ((-1, 'r'), (0, 'l')):
            for y, row in ((78, 'bot'), (79, 'top')):
                p.put(side, y, z+dz, 'mcwwindows:dark_oak_plank_window', facing='east', part=row+'_'+column)
    for y, row in ((72, 'bot'), (73, 'top'), (78, 'bot'), (79, 'top')):
        for x, column in ((1182, 'r'), (1183, 'l')):
            p.put(x, y, z-4, 'mcwwindows:dark_oak_plank_window', facing='north', part=row+'_'+column)
    # A steep copper cap and dark lower eaves produce a distinct two-stage roof.
    for step in range(5):
        for x in range(1178+step, 1188-step):
            for dz in range(-5+step, 6-step):
                if x not in (1178+step, 1187-step) and abs(dz) != 5-step: continue
                facing = 'east' if x == 1178+step else 'west' if x == 1187-step else 'south' if dz < 0 else 'north'
                key = 'minecraft:deepslate_tile_stairs' if step == 0 else 'minecraft:waxed_weathered_cut_copper_stairs'
                if step == 0 and x in (1182, 1183) and abs(dz) == 5:
                    key = 'minecraft:waxed_weathered_cut_copper_stairs'
                # Upright copper ribs at real roof corners divide the long eaves.
                if abs(dz) in (1, 4) and x in (1178+step, 1187-step):
                    p.put(x, 82+step, z+dz, 'minecraft:waxed_exposed_cut_copper_slab', type='bottom', waterlogged=False)
                else: p.stair(x, 82+step, z+dz, key, facing)
    p.put(1182, 87, z, 'minecraft:lightning_rod', facing='up', powered=False, waterlogged=False)
    # Human-scale control-room stories, kept clear of both native controls.
    p.put(1180, 71, z+1, 'handcrafted:dark_oak_desk', facing='east', color='none', waterlogged=False)
    p.put(1180, 72, z+1, 'minecraft:flower_pot')
    p.put(1180, 71, z, 'handcrafted:dark_oak_chair', facing='south', color='none', waterlogged=False)
    p.put(1180, 77, z-2, 'minecraft:bookshelf')
    p.put(1180, 78, z-2, 'minecraft:bookshelf')
    p.put(1181, 77, z-2, 'minecraft:cartography_table')
    p.put(1181, 78, z-2, 'minecraft:candle', candles=3, lit=True, waterlogged=False)
    p.lamp(1183, 75, z+2, hanging=True)
    p.lamp(1181, 81, z, hanging=True)
    p.routes.append({'name': name+' native button access', 'feet': [[x, 71, z+3] for x in range(1182, 1190)]+[[1182, 71, z+2], [1182, 71, z+1]],
                     'claim': 'Planned accessible control route; native walking and model-clearance validation pending'})


def wheel_caps(p):
    p.group = 'complete bank wheel housings'
    for pivot in (-1172, -1116):
        # Roof-only steel/copper hoods leave every water cell, wheel and shaft.
        for n in range(3):
            for x, face in ((1222+n, 'east'), (1228-n, 'west')):
                for dz in range(-3, 4):
                    key = 'minecraft:waxed_exposed_cut_copper_stairs' if dz == 0 else 'minecraft:waxed_weathered_cut_copper_stairs'
                    p.stair(x, 74+n, pivot+dz, key, face)
        for x in (1222, 1228):
            for dz in (-3, 3):
                for y in range(71, 74):
                    if (x, y, pivot+dz) not in p.protected: p.stone(x, y, pivot+dz)


def approach_landings(p):
    p.group = 'complete curved approach stairs and landings'
    offsets = (0, 0, 0, 0, -1, -1, -1, -1, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0)
    for north, start in ((True, -1202), (False, -1102)):
        for n, offset in enumerate(offsets):
            z = start+n
            y = min(70, 64+n//2) if north else max(64, 70-n//2)
            center = 1193+offset
            # A seven-wide, slightly turning stair within the existing nine-wide
            # approach. The bankward ends broaden into real waiting landings.
            for x in range(1189, 1198):
                if abs(x-center) <= 3:
                    if n < 12:
                        p.stair(x, y, z, 'minecraft:stone_brick_stairs', 'south' if north else 'north')
                    else:
                        p.stone(x, y, z)
                elif base(p.original.get((x, y, z), AIR)).endswith('_stairs'):
                    p.put(x, y, z, 'minecraft:stone_brick_slab', type='bottom', waterlogged=False)
            for x in (center-4, center+4):
                if (x, y, z) not in p.protected: p.stone(x, y, z)
                if n % 4 == 0:
                    p.stone(x, y+1, z)
                    p.lamp(x, y+2, z)
                else:
                    p.put(x, y+1, z, 'minecraft:stone_brick_wall', waterlogged=False)


def construct(registry, master, exclusions=(), footing=None, water_y=62):
    p = Refinement(registry, master, exclusions, footing, water_y)
    articulated_leaves(p)
    shaped_banks(p)
    control_pavilion(p, -1178, 'North lantern watch')
    control_pavilion(p, -1110, 'South tide watch')
    wheel_caps(p)
    approach_landings(p)
    return p


def validate(p):
    if p.tags != p.master['block_entities']:
        raise UserError('Existing BE payloads must remain exact')
    if any(p.blocks[pos] != p.original[pos] for pos in p.protected):
        raise UserError('A protected existing mechanism or furnishing changed')
    checks = []
    for name, pivot, direction, length in LEAVES:
        cells = {pos: value for pos, value in p.blocks.items() if leaf_name(pos) == name}
        checks.append(require_material_rule(cells, name+' complete moving leaf'))
        for n in range(length):
            z = pivot+direction*n
            for x in range(1187, 1199):
                floor = p.blocks.get((x, 70, z), AIR)
                if n == 0 and floor != p.original.get((x, 70, z)):
                    raise UserError('Preserve the original full bearing attachment row')
                if n and (not base(floor).endswith('_slab') or properties(floor).get('type') != 'top'):
                    raise UserError('Every rebuilt deck bay must retain the Y71 walking top')
            for x in range(1188, 1198):
                for y in range(71, 75):
                    if base(p.blocks.get((x, y, z), AIR)) != AIR:
                        raise UserError('The ten-wide moving traffic corridor is obstructed')
        if any(base(v) != AIR and pos[1] > 73 for pos, v in cells.items()):
            raise UserError('The old high timber caps must actually be removed')
    for group, cells in p.groups.items():
        if 'pavilion' in group:
            checks.append(require_material_rule({pos: p.blocks[pos] for pos in cells}, group))
    checks.append(require_material_rule(p.blocks, 'Complete proposed bridge including inherited lodges and approaches'))
    outdoor = require_outdoor_rule(p.blocks, 'Complete proposed bridge, banks and inherited approaches')
    changed = {pos: value for pos, value in p.blocks.items() if p.original.get(pos) != value}
    moving = {pos: value for pos, value in changed.items() if leaf_name(pos)}
    fixed = {pos: value for pos, value in changed.items() if not leaf_name(pos)}
    if not moving or not fixed or len(changed) > 16000:
        raise UserError('Refinement must be a finite real moving/fixed structural change')
    if any(base(state) not in (AIR, 'minecraft:water') and 1188 <= pos[0] <= 1197
           and -1172 <= pos[2] <= -1116 for pos, state in fixed.items()):
        raise UserError('A new fixed structure intrudes into the nominal channel/leaf strip')
    return {'changed': changed, 'moving': moving, 'fixed': fixed, 'material_checks': checks, 'outdoor_rule': outdoor}


def payload(template, blocks, checkpoint_sha, name, tags=()):
    doc = copy.deepcopy(template)
    doc.update(name=name, backup_sha256=checkpoint_sha, block_entities=list(tags), commands=[], landmarks=[])
    doc['palette'] = sorted(set(blocks.values())); indices = {v: i for i, v in enumerate(doc['palette'])}
    doc['blocks'] = [[*pos, indices[state]] for pos, state in sorted(blocks.items())]
    doc['bounds'] = [min(p[0] for p in blocks), min(p[2] for p in blocks), max(p[0] for p in blocks), max(p[2] for p in blocks)]
    doc['validation'] = 'PROPOSAL ONLY - parent native preimage, reviewed placement, new glue, cycles, restart and shader screenshots required'
    return doc


def same_authored_intent(expected, actual):
    if base(expected) != base(actual): return False
    old, now = properties(expected), properties(actual)
    return all(now.get(key) == value for key, value in old.items()
               if key in ('facing', 'axis', 'half', 'part', 'type', 'hinge'))


def saved_closed_bearings(snapshot):
    witnesses = []
    for z in (-1172, -1116):
        position = (1199, 70, z)
        document = saved_chunk(snapshot, position)
        rows = [row for row in document.get('block_entities', [])
                if tuple(row.get(k) for k in ('x', 'y', 'z')) == position]
        if len(rows) != 1 or rows[0].get('id') != 'create:mechanical_bearing':
            raise UserError('The stopped checkpoint lacks an exact native bridge bearing')
        row = rows[0]; angle = row.get('Angle')
        if (row.get('Running') != 0 or type(angle) not in (int, float)
                or not math.isfinite(angle) or abs(angle) > .001):
            raise UserError('A saved closed/disassembled bearing is required; do not rebuild a moving leaf')
        witnesses.append({'position': list(position), 'saved_running': False, 'saved_angle': angle,
                          'saved_nbt_sha256': hashlib.sha256(json.dumps(row, sort_keys=True, separators=(',', ':')).encode()).hexdigest(),
                          'scope': 'Authenticated stopped-save observation; fresh native attachment/controller/readiness checks remain required'})
    return witnesses


def native_window_expectations(proposal, output):
    """Correct only the 32 authored native horizontal window edge parts.

    The original proposal and failed native receipt stay untouched. These are
    verification files, never a request to replay the placed fixed architecture.
    """
    proposal, output = Path(proposal).resolve(), Path(output).resolve()
    if output.exists() or not output.is_relative_to(Path(r'D:\A World for Two\staging')):
        raise UserError('New private verification-only output required')
    guard(MIB, 2*MIB)
    expected = {'fixed-delta.json': '7dc9ca96dfd0e603268c4a6289b1dbaf6c26656d85e6285a6b55f3990162fbe9',
                'full-verification.json': '824db735a30f7329e5271ae3237d122b8a279279f76b818f4cd8f2ca84bf3bbe'}
    parts = {}
    for center in (-1178, -1110):
        for side in (1179, 1186):
            for dz, suffix in ((-1, 'r'), (0, 'l')):
                for y, row in ((78, 'bot'), (79, 'top')): parts[side, y, center+dz] = row+'_'+suffix
        for y, row in ((72, 'bot'), (73, 'top'), (78, 'bot'), (79, 'top')):
            for x, suffix in ((1182, 'r'), (1183, 'l')): parts[x, y, center-4] = row+'_'+suffix
    if len(parts) != 32: raise UserError('Unexpected authored window inventory')
    documents, geometry = {}, []
    for name, expected_sha in expected.items():
        path = proposal/name
        if digest(path) != expected_sha: raise UserError('Original immutable bridge proposal differs')
        original = read_json(path); doc = copy.deepcopy(original); changed = []
        for row in doc['blocks']:
            pos = tuple(row[:3])
            if pos not in parts: continue
            before = original['palette'][row[3]]; props = properties(before)
            if base(before) != 'mcwwindows:dark_oak_plank_window' or props.get('part', '')[-1:] != ('l' if parts[pos].endswith('r') else 'r'):
                raise UserError('The original authored edge part no longer matches its reviewed pair')
            props['part'] = parts[pos]
            after = base(before)+'['+','.join(k+'='+v for k, v in sorted(props.items()))+']'
            if after not in doc['palette']: raise UserError('A part correction unexpectedly changes the palette inventory')
            row[3] = doc['palette'].index(after)
            changed.append({'position': list(pos), 'before': before, 'after': after})
        if len(changed) != 32 or doc['block_entities'] != original['block_entities']:
            raise UserError('Only the exact 32 parts may change; retain all BE data')
        doc['verification_only'] = True
        output_name = 'fixed-verification.json' if name == 'fixed-delta.json' else name
        documents[output_name] = encoded(doc)
        geometry = changed
    receipt = {'format': 'awft-native-window-part-derivation:1', 'changed_positions': 32,
               'rule': 'Pinned Macaw Window horizontal join: first increasing-coordinate edge is *_r, last is *_l; vertical row remains unchanged',
               'native_failure_preserved': 'settlement-result-53eb2a29-30a9-4fec-8462-26052f7af943.json',
               'changes': geometry, 'materials_positions_and_BEs_unchanged': True, 'runtime_actions': False,
               'files': {name: {'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)} for name, raw in documents.items()}}
    documents['part-derivation.json'] = encoded(receipt)
    output.mkdir(parents=True, exist_ok=False)
    for name, raw in documents.items(): (output/name).write_bytes(raw)
    return dict(receipt, output=str(output))


def prepare(home, master_path, rosebridge_path, output, checkpoint_id, checkpoint_sha, angle=55, craft_path=None):
    home, master_path, rosebridge_path, output = (Path(v).resolve() for v in (home, master_path, rosebridge_path, output))
    angle = open_angle(angle)
    craft_path = Path(craft_path).resolve() if craft_path else home/'staging/craft-lane-placement-20261027T0855/prototype.json'
    if (not home.is_relative_to(Path(r'D:\A World for Two\staging\world-tests')) or output.exists()
            or not output.is_relative_to(home/'staging')):
        raise UserError('New uniquely owned private artistic proposal directory required')
    admission = guard(4*MIB, MAX_OUTPUT)
    if digest(master_path) != MASTER_SHA or digest(rosebridge_path) != ROSEBRIDGE_SHA or digest(craft_path) != CRAFT_LANE_SHA:
        raise UserError('The exact contained bridge master, fixed rosebridge and craft lane are required')
    checkpoint = read_json(home/'dashboard/settlement/backup-receipt.json')
    if checkpoint.get('verified') is not True or checkpoint.get('id') != checkpoint_id or checkpoint.get('sha256') != checkpoint_sha:
        raise UserError('Rebind to the exact current parent-reviewed stopped checkpoint')
    registry = read_json(home/'dashboard/settlement/registry.json')
    master, rose, craft = read_json(master_path), read_json(rosebridge_path), read_json(craft_path)
    for doc in (master, rose, craft):
        if any(str(doc[k]) != str(registry[k]) for k in ('seed', 'world_path')):
            raise UserError('The proposed source belongs to another actual world')
    snapshot = BackupWorld(home, checkpoint, registry)
    try:
        for pos, expected in flatten(master).items():
            if not same_authored_intent(expected, snapshot.state(pos)):
                raise UserError('The actual saved bridge differs from the reviewed master: '+str(pos))
        bearings = saved_closed_bearings(snapshot)
        foundation_columns = {}
        def footing(x, z):
            if (x, z) in foundation_columns: return foundation_columns[x, z]['ground_y']
            for y in range(64, 54, -1):
                state = base(snapshot.state((x, y, z)))
                if state in FOOTING_SOLIDS:
                    foundation_columns[x, z] = {'x': x, 'z': z, 'ground_y': y,
                                                 'saved_structural_support': snapshot.state((x, y, z))}
                    return y
            raise UserError('No shallow saved footing for the bank structure: '+str((x, z)))
        water = [y for y in range(59, 68) if base(snapshot.state((1192, y, -1144))) == 'minecraft:water']
        if not water or max(water) != 62:
            raise UserError('Actual saved navigation water level differs; review the bank design')
        p = construct(registry, master, [rose, craft], footing, max(water))
        proof = validate(p)
        before = {pos: snapshot.state(pos) for pos in proof['changed']}
        if set(before) & snapshot.protected:
            raise UserError('A proposed architectural change targets a saved BE')
        # Only baseline-owned geometry and the explicitly authored west bank and
        # wheel-hood footprints can change. No road/town clearance is inferred.
        for pos, state in before.items():
            if pos not in p.original and base(state) not in NATURAL | {'minecraft:seagrass', 'minecraft:tall_seagrass'}:
                raise UserError('Preserve unrelated saved construction or vegetation: '+str(pos)+' '+state)
        sources = snapshot.sources.copy()
    finally:
        snapshot.close()
    docs = {
        'native-before.json': payload(master, before, checkpoint_sha, 'VERIFY ONLY - exact saved refinement preimage'),
        'rollback.json': payload(master, before, checkpoint_sha, 'ROLLBACK ONLY AFTER REVIEW - exact pre-refinement states; no BE loads'),
        'fixed-delta.json': payload(master, proof['fixed'], checkpoint_sha, 'FIXED BANK REFINEMENT PROPOSAL - no moving-leaf placements'),
        'moving-delta.json': payload(master, proof['moving'], checkpoint_sha, 'MOVING LEAF REBUILD PROPOSAL - new glue and complete native commissioning required'),
        'full-verification.json': payload(master, p.blocks, checkpoint_sha, 'VERIFY ONLY - complete proposed Lanternwater refinement', p.tags),
    }
    docs['full-verification.json']['verification_only'] = True
    geometry_sha = hashlib.sha256(encoded(docs['full-verification.json'])).hexdigest()
    systems = placed_systems(angle)
    for system in systems: system['glue_max'][1] = 73
    docs['engineering-PROPOSAL.json'] = {
        'format': 'awft-native-engineering:1', 'seed': master['seed'], 'world_path': master['world_path'],
        'backup_sha256': checkpoint_sha, 'construction_sha256': geometry_sha, 'open_angle_degrees': angle,
        'systems': systems, 'buttons': [list(v) for v in BUTTONS], 'radios': placed_radios(),
        'clearance_estimate': clearance_estimate(angle),
        'status': 'NOT ADMITTED - a changed physical plan invalidates old glue/cycle/restart/ship-clearance authority'}
    raw = {name: encoded(doc) for name, doc in docs.items()}
    manifest = {
        'format': 'awft-artistic-bridge-refinement:1', 'status': 'PROPOSAL ONLY; no native action or artistic acceptance',
        'source_sha256': digest(Path(__file__)), 'original_contained_master_sha256': MASTER_SHA,
        'fixed_rosebridge_sha256': ROSEBRIDGE_SHA, 'checkpoint_id': checkpoint_id, 'checkpoint_sha256': checkpoint_sha,
        'fixed_craft_lane_sha256': CRAFT_LANE_SHA,
        'files': {name: {'sha256': hashlib.sha256(value).hexdigest(), 'bytes': len(value)} for name, value in raw.items()},
        'changed_positions': len(proof['changed']), 'moving_changed_positions': len(proof['moving']), 'fixed_changed_positions': len(proof['fixed']),
        'existing_BE_payloads_preserved': len(p.tags), 'native_components_changed': 0, 'native_control_positions_changed': 0,
        'groups': {name: len(pos) for name, pos in p.groups.items()}, 'material_checks': proof['material_checks'], 'outdoor_rule': proof['outdoor_rule'],
        'palette_usage': dict(Counter(base(v) for v in proof['changed'].values())), 'saved_sources': sources,
        'saved_closed_bearings': bearings,
        'foundation_columns': list(foundation_columns.values()),
        'saved_replacement_counts': dict(Counter(base(v) for v in before.values())),
        'routes': p.routes, 'cameras': list(CAMERAS), 'structural_changes': p.notes,
        'moving_envelopes': systems, 'navigation': 'No new fixed solid between bank pivot planes in the ten-wide deck/navigation strip; vessel/model-specific transformed collision remains unverified',
        'required_native_contract': ['Authenticated exclusive empty-world maintenance lease and fresh verified backup',
            'Actual native closed/disassembled bearings, idle reversible sequencers, no passengers and zero outstanding temporary tickets',
            'Exact preimage verification for each reviewed delta; preserve controls, shafts, wheels, radios and BE data',
            'Apply fixed changes separately; no old cycle receipt substitutes for a new collision check',
            'Retire only positively identified owned old glue after native closure; never clear arbitrary glue/entities',
            'Place moving delta and verify complete physical identities/orientation/inventories',
            'Admit exact new physical hash and glue envelopes, assemble and inspect actual captured blocks/bounds',
            'Two real button-driven signed open/close cycles at the selected 45..60 degree angle; verify both bank controls and ticket cleanup',
            'Native closed physical verification, stopped checkpoint, restart without setup, repeat two cycles and reverify',
            'Actual shader comparison screenshots, player walking/control access, and vessel-specific navigation before acceptance'],
        'reserve_guard': admission, 'runtime_actions': False,
    }
    raw['manifest.json'] = encoded(manifest)
    if sum(map(len, raw.values())) > MAX_OUTPUT:
        raise UserError('The finite refinement proposal allocation was exceeded')
    output.mkdir(parents=True, exist_ok=False)
    for name, value in raw.items(): (output/name).write_bytes(value)
    return {'output': str(output), 'manifest_sha256': hashlib.sha256(raw['manifest.json']).hexdigest(),
            'full_verification_sha256': geometry_sha, 'changed_positions': len(proof['changed']), 'native_actions': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('home', 'master-path', 'rosebridge-path', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--checkpoint-id', required=True)
    parser.add_argument('--checkpoint-sha', required=True)
    parser.add_argument('--angle', type=int, default=55)
    parser.add_argument('--craft-path', type=Path)
    print(json.dumps(prepare(**vars(parser.parse_args())), indent=2))
