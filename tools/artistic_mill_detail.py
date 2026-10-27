"""A separate authored finish for the exact placed Copper Wren R2 mill.

This prepares private geometry/preimage files only. It never launches Minecraft,
issues commands, places blocks, commissions machinery or rewrites R2 evidence.
"""
from __future__ import annotations

import argparse
from collections import Counter
import copy
import hashlib
import json
from pathlib import Path
import re

from control_room.common import UserError, digest, read_json, utcnow
from tools.artistic_engineering import DRY_NATURAL, PLANTS, VOID
from tools.artistic_materials import require_material_rule, require_outdoor_rule
from tools.playtest import guard
from tools.settlement_attractions import AIR, BackupWorld, base, properties


ORIGIN = (1310, 67, -1000)
LOCAL_BOUNDS = (-8, -4, -12, 14, 17, 15)
SOURCE_PLAN_SHA = '181e2191572846967c41e77bf5b406d0dddcc484488aa60d6725728ba651b199'
SOURCE_MANIFEST_SHA = '4339bb54a05d9c5a478b471db880c7d80dc1f6c0f25081824c7c54b75f49f408'
PLACED_R3_SHA = 'ff4fe2c333f7a67fc68c0ab90f2ced6666aa3e83d929f0e55b323a9d7c7bcdd8'
JOIN_APIS = {
    'mcw-mcwwindows-2.4.2-mc1.21.1neoforge.jar': '8970c40ec622edd34c9b055226b403af08ab441c77303a6dc625ae18005f8184',
    'mcw-roofs-2.3.2-mc1.21.1neoforge.jar': '25c79def993a24b05b0f8494ee9417717d469bc000d5ed7c219b47dcc3b3e9c8',
}
MAX_OUTPUT = 16*1024**2
MAX_TARGETS = 4000
KINETIC = ('create:', 'overpressure:', 'create_hypertube:', 'railways:')
INVENTORIES = {'minecraft:chest', 'minecraft:barrel', 'minecraft:hopper', 'minecraft:furnace'}


def joined_window_part(above, below, negative_neighbor, positive_neighbor):
    """Pinned ConnectedWindow.WindowState semantics on its NORTH/EAST planes.

    Negative means west for NORTH or north for EAST. Macaw names the positive
    neighbor-only edge ``r``; that is the first cell as our coordinates increase.
    Neighbors are the same actual block identity, not merely another window.
    """
    if any(type(v) is not bool for v in (above, below, negative_neighbor, positive_neighbor)):
        raise UserError('Exact native window neighbor booleans required')
    vertical = 'mid' if above and below else 'top' if below else 'bot' if above else 'single'
    side = 'm' if negative_neighbor and positive_neighbor else 'l' if negative_neighbor else 'r' if positive_neighbor else None
    return vertical+'_'+side if side else {'mid':'middle','top':'top','bot':'bottom','single':'base'}[vertical]


def joined_dormer_top_part(east, west, *, north=False, south=False):
    """Exact pinned RoofTopNew result for these isolated east/west ridges."""
    if any(type(v) is not bool for v in (north,east,south,west)) or north or south:
        raise UserError('The reviewed dormer ridge must remain an isolated east/west line')
    return 'switched_90' if east and west else 'top_end_90' if east else 'top_end_270' if west else 'switched_0'


def decode(plan):
    return {tuple(row[:3]): plan['palette'][row[3]] for row in plan['blocks']}


class Finish:
    def __init__(self, registry, source, manifest, snapshot=None):
        self.registry, self.source, self.manifest, self.snapshot = registry, source, manifest, snapshot
        self.original = decode(source)
        self.blocks, self.previous, self.tags, self.features = {}, {}, {}, []
        self.family, self.groups = 'Mill finish', {}
        self.fixed = {p for p, state in self.original.items() if base(state).startswith(KINETIC) or base(state) in INVENTORIES}
        self.fixed.update(tuple(row['pos']) for row in source.get('block_entities', []))
        for p, state in self.original.items():
            if base(state).startswith(KINETIC):
                # The original cog/tube/drive envelope stays usable, not merely
                # the block centers. No decorative bracket can graze a cog.
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        for dz in (-1, 0, 1):
                            self.fixed.add((p[0]+dx, p[1]+dy, p[2]+dz))
        for x in range(1305, 1310):
            for y in range(67, 74):
                for z in range(-1002, -997):
                    self.fixed.add((x, y, z))
        for row in manifest['routes']:
            for x, y, z in row['standing_positions']:
                for dy in (-1, 0, 1):
                    self.fixed.add((x, y+dy, z))
        self.fixed.update(tuple(p) for p in manifest['systems']['hypertube']['native_collision_cells'])
        self.fixed.update(tuple(p) for p in manifest['systems']['watermill']['water_sources'])
        chest = tuple(manifest['systems']['watermill']['grain_chest'])
        self.fixed.update((chest[0], chest[1]+dy, chest[2]) for dy in (1, 2))

    def world(self, x, y, z):
        return x+ORIGIN[0], y+ORIGIN[1], z+ORIGIN[2]

    def state(self, key, **props):
        schema = self.registry['blocks'].get(key)
        if schema is None:
            raise UserError('Unregistered actual mill finish block '+key)
        for name, value in props.items():
            if str(value).lower() not in schema.get(name, ()):
                raise UserError('Unregistered actual finish property '+key+' '+name+'='+str(value))
        return key+('['+','.join(k+'='+str(v).lower() for k, v in sorted(props.items()))+']' if props else '')

    def put(self, x, y, z, key, **props):
        local = x, y, z
        if any(type(v) is not int or not LOCAL_BOUNDS[n] <= v <= LOCAL_BOUNDS[n+3] for n, v in enumerate(local)):
            raise UserError('Mill finish escaped its bounded authored envelope: '+str(local))
        p = self.world(*local)
        if p in self.fixed:
            raise UserError('Preserve machine, hydraulic seal, cargo, lid or operating route: '+str(local))
        old = self.snapshot.state(p) if self.snapshot else self.original.get(p, AIR)
        if self.snapshot and p in self.snapshot.protected:
            raise UserError('Preserve saved block entity: '+str(local))
        if p in self.original:
            if base(old) != base(self.original[p]):
                raise UserError('The actual saved architectural predecessor changed: '+str(local)+' '+old)
        elif base(old) not in DRY_NATURAL | VOID | PLANTS:
            raise UserError('Preserve unrelated construction, tree or fluid: '+str(local)+' '+old)
        value = self.state(key, **props)
        self.blocks[p], self.previous[p] = value, old
        self.groups.setdefault(self.family, set()).add(p)
        if len(self.blocks) > MAX_TARGETS:
            raise UserError('Split the finite mill finish proposal')

    def box(self, x1, y1, z1, x2, y2, z2, key, **props):
        for x in range(x1, x2+1):
            for y in range(y1, y2+1):
                for z in range(z1, z2+1):
                    self.put(x, y, z, key, **props)

    def footing(self, x, z):
        ground = 0
        if self.snapshot:
            for y in range(0, -4, -1):
                old = self.snapshot.state(self.world(x, y, z))
                if base(old) in VOID | PLANTS:
                    continue
                if base(old) not in DRY_NATURAL:
                    raise UserError('A small wheelhouse post has no dry natural footing: '+str((x, y, z)))
                ground = y
                break
            else:
                raise UserError('Relocate instead of building a deep mill platform')
        for y in range(ground, 1):
            self.put(x, y, z, 'minecraft:mossy_cobblestone' if y == ground else 'minecraft:stone_bricks')

    def window(self, x, y, z, facing, width=3, height=2, wood='dark_oak'):
        if type(width) is not int or type(height) is not int or width<1 or height<1:
            raise UserError('Finite positive window dimensions required')
        for dy in range(height):
            for n in range(width):
                px, pz = (x+n, z) if facing in ('north', 'south') else (x, z+n)
                # Preserve the captured single-column initial parts. Only the
                # horizontal rectangular joins are part of this reviewed fix;
                # do not normalize an unrelated base/bottom lifecycle state.
                part = (('base' if dy==0 else 'top' if dy==height-1 else 'middle') if width==1
                        else joined_window_part(dy<height-1,dy>0,n>0,n<width-1))
                self.put(px, y+dy, pz, 'mcwwindows:'+wood+'_plank_window',
                         facing='north' if facing in ('north', 'south') else 'east', part=part)

    def lamp(self, x, y, z, facing):
        self.put(x, y, z, 'mcwlights:tavern_wall_lantern', facing=facing)


def glazing(p):
    p.family = 'Proper mill windows, shutters and planted sills'
    # The northwestern original aperture surrounds the fixed pneumatic feed.
    # Keep its full inspection glass and the west return unchanged, rather
    # than fitting a partial decorative window through the actual item route.
    for center in (6, 10):
        p.window(center-1, 2, -6, 'north')
    for center in (2, 10):
        p.window(center-1, 2, 10, 'south')
    # Preserve the exact two-wide door; its three-wide glazed transom is a
    # distinct assembly, not the truncated lower half of an imaginary window.
    p.put(5, 2, 10, 'minecraft:stripped_dark_oak_log', axis='y')
    p.window(5, 3, 10, 'south', height=1)
    for x, face in ((0, 'west'), (12, 'east')):
        for z in (-4, 4, 8):
            if x == 0 and z == -4:
                continue
            p.window(x, 2, z, face, width=2, wood='spruce')
    p.window(5, 9, 10, 'south', width=2)
    for x in (9, 11):
        p.put(x, 1, 11, 'mcwwindows:dark_oak_log_parapet', facing='south', part='flower')
    for x, hinge in ((0, 'left'), (4, 'right'), (8, 'left'), (12, 'right')):
        p.put(x, 3, 11, 'mcwwindows:dark_oak_louvered_shutter', facing='south', hinge=hinge, open=True)
    for z in (4, 8):
        p.put(13, 1, z, 'mcwwindows:dark_oak_log_parapet', facing='east', part='flower')
        p.put(13, 2, z-1, 'mcwwindows:spruce_louvered_shutter', facing='east', hinge='left', open=True)
    p.features.append('Native framed 2/3-wide glazing, door transom, attic light, shutters and planted sills')


def ridge(p):
    p.family = 'Physically joined ridge and roof ironwork'
    for z in range(-7, 12):
        seam = z in (2, 10)
        p.put(6, 12, z, 'minecraft:polished_blackstone' if seam else 'minecraft:stripped_spruce_wood', **({} if seam else {'axis':'z'}))
        p.put(6, 13, z, 'minecraft:dark_oak_slab' if seam else 'minecraft:spruce_slab', type='bottom', waterlogged=False)
    p.features.append('Full ridge bearer touches adjacent roof tips and bottom slabs; no half-block daylight seam')


def dormer(p, center, radius, back, base_y):
    p.family = 'Broad ledger dormer' if radius == 2 else 'Small sack-loft dormer'
    left, right = center-radius, center+radius
    for pos, state in list(p.original.items()):
        x, y, z = (pos[n]-ORIGIN[n] for n in range(3))
        if 0 <= x <= back and left <= z <= right and y >= base_y and base(state).startswith('mcwroofs:'):
            p.put(x, y, z, AIR)
    for z in range(left, right+1):
        for y in range(base_y, base_y+3):
            post = z in (left, right)
            p.put(0, y, z, 'minecraft:stripped_dark_oak_log' if post else 'minecraft:smooth_sandstone', **({'axis':'y'} if post else {}))
    for z in (left, right):
        for x in range(1, back+1):
            for y in range(base_y, base_y+3):
                post = x % 3 == 0
                p.put(x, y, z, 'minecraft:stripped_dark_oak_log' if post else 'minecraft:smooth_sandstone', **({'axis':'y'} if post else {}))
    p.window(0, base_y, left+1, 'west', width=2*radius-1, height=2)
    for z in range(left, right+1):
        p.put(0, base_y+2, z, 'minecraft:oak_wood', axis='z')
    # A broad cross-gable needs a real triangle above its window header.
    # The later roof bearer occupies its uppermost center, sealing the join.
    for z in range(left+1, right):
        rise=min(z-(left-1),right+1-z)
        for y in range(base_y+3,base_y+2+rise):
            p.put(0,y,z,'minecraft:smooth_sandstone')
    for z in range(left-1, right+2):
        rise = min(z-(left-1), right+1-z)
        roof_y = base_y+2+rise
        for x in range(-1, back+1):
            if z == center:
                p.put(x, roof_y-1, z, 'minecraft:birch_wood', axis='x')
                p.put(x, roof_y, z, 'mcwroofs:spruce_top_roof',
                      part=joined_dormer_top_part(x<back,x>-1))
            else:
                p.put(x, roof_y, z, 'mcwroofs:spruce_roof', facing='south' if z < center else 'north', half='bottom', shape='straight')
    # Close the raised cheeks/back into the original slope; an opening into
    # the hall remains below, so these are real roof lights, not sealed boxes.
    for z in range(left+1, right):
        top = base_y+2+min(z-left+1, right+1-z)
        for y in range(base_y+2, top):
            p.put(back, y, z, 'minecraft:smooth_sandstone')
    p.features.append(p.family+' with a projecting glazed face, framed cheeks and unequal cross-gable')


def wheelhouse(p):
    p.family = 'Framed hydraulic observation bay outside the unchanged seal'
    for z in (-3, 3):
        p.footing(-6, z)
        p.box(-6, 1, z, -6, 6, z, 'minecraft:stripped_dark_oak_log', axis='y')
    for z in (-2, 2):
        p.box(-6, 1, z, -6, 6, z, 'minecraft:stripped_dark_oak_log', axis='y')
    p.window(-6, 2, -1, 'west')
    p.window(-6, 5, -1, 'west')
    for z in range(-3, 4):
        p.put(-6, 4, z, 'minecraft:spruce_wood', axis='z')
    for z in (-1, 1):
        p.put(-7, 1, z, 'mcwwindows:dark_oak_log_parapet', facing='west', part='flower')
    for z in range(-3, 4):
        rise = 3-abs(z)
        for x in range(-7, 0):
            if z == 0:
                p.put(x, 9, z, 'minecraft:dark_prismarine')
                p.put(x, 10, z, 'minecraft:dark_prismarine_slab', type='bottom', waterlogged=False)
            else:
                p.put(x, 7+rise, z, 'mcwroofs:dark_prismarine_roof', facing='south' if z < 0 else 'north', half='bottom', shape='straight')
        for y in range(7, 7+rise):
            p.put(-6, y, z, 'minecraft:smooth_sandstone')
    p.put(-6, 8, 0, 'minecraft:dark_oak_trapdoor', facing='west', half='bottom', open=True, powered=False, waterlogged=False)
    p.lamp(-7, 4, -2, 'west')
    p.features.append('Low green gable, timber observation frontage and real fancy glazing outside every sealed hydraulic block')


def porch_and_chimney(p):
    p.family = 'Sheltered mill threshold and small double flue'
    for x in (4, 9):
        p.box(x, 1, 13, x, 3, 13, 'minecraft:stripped_dark_oak_log', axis='y')
    for x in range(4, 10):
        p.put(x, 3, 13, 'minecraft:dark_oak_wood', axis='x')
        for z in range(10, 14):
            p.put(x, 4+(13-z)//2, z, 'mcwroofs:dark_oak_roof', facing='south', half='bottom', shape='straight')
    for x in (5, 8):
        p.put(x, 1, 13, 'mcwwindows:dark_oak_log_parapet', facing='south', part='flower')
    p.lamp(4, 3, 14, 'south')
    p.put(9, 3, 14, 'minecraft:oak_wall_sign', facing='south', waterlogged=False)
    texts=[json.dumps(json.dumps({'text':v,'color':'dark_green'})) for v in ['COPPER WREN','Flour & iron','Mind the working aisle','Tea by the ledger']]
    p.tags[p.world(9, 3, 14)]='{is_waxed:1b,front_text:{messages:['+','.join(texts)+'],color:"brown",has_glowing_text:0b}}'
    for y in range(8, 15):
        for z in (4, 5):
            p.put(10, y, z, 'minecraft:bricks' if y not in (10, 13) else 'minecraft:polished_andesite')
    for z in (4, 5):
        p.put(10, 15, z, 'minecraft:brick_wall', north='low' if z == 5 else 'none', south='low' if z == 4 else 'none', east='none', west='none', up=True, waterlogged=False)
    p.features.append('Two-post shaded porch keeps both walking columns open; capped double flue punctuates the other roof plane')


def interior(p):
    p.family = 'Supported task lighting and inhabited craft edges'
    for z in (-4, 3, 8):
        for x in range(13):
            p.put(x, 6, z, 'minecraft:polished_andesite' if x == 6 else 'minecraft:dark_oak_wood', **({} if x == 6 else {'axis':'x'}))
        for x, facing in ((1, 'west'), (11, 'east')):
            if (x,z)==(1,-4):
                continue  # The fixed pneumatic overhead feed owns this corner.
            p.put(x, 5, z, 'minecraft:dark_oak_stairs', facing=facing, half='top', shape='straight', waterlogged=False)
    for x, z in ((3, 3), (9, -4)):
        p.put(x, 5, z, 'mcwlights:iron_chandelier', lit=True)
    for x in (2, 10):
        for y in range(5, 9):
            p.put(x, y, 9, 'minecraft:chain', axis='y', waterlogged=False)
    for x, z, facing in ((1, 4, 'east'), (1, 8, 'east'), (11, -4, 'west'), (11, 8, 'west')):
        p.lamp(x, 4, z, facing)
    for x in (9, 10, 11):
        p.put(x, 1, -5, 'handcrafted:oak_counter', facing='south', counter='spruce_planks', type=1)
    p.put(9, 2, -5, 'handcrafted:wood_plate', facing='south', pieces=3, waterlogged=False)
    p.put(10, 2, -5, 'handcrafted:terracotta_thin_pot')
    p.put(11, 2, -5, 'handcrafted:wood_cup', facing='south')
    p.put(1, 1, 3, 'handcrafted:spruce_cupboard', facing='east', type=1)
    p.put(1, 1, 4, 'handcrafted:oak_counter', facing='east', counter='spruce_planks', type=1)
    p.put(1, 2, 4, 'handcrafted:terracotta_medium_pot')
    p.put(1, 4, 3, 'handcrafted:spruce_shelf', facing='east', shape='single', type=3)
    p.put(1, 5, 3, 'handcrafted:wood_cup', facing='east')
    p.put(10, 1, 4, 'handcrafted:oak_cupboard', facing='east', type=2)
    p.put(9, 1, -3, 'handcrafted:terracotta_medium_pot')
    # A ledger-side rest alcove belongs at the room edge, leaving the central
    # doorway and every machine operating column exactly as commissioned.
    p.put(1, 1, 6, 'handcrafted:oak_bench', color='brown', facing='east', shape='single', waterlogged=False)
    p.put(1, 1, 7, 'handcrafted:spruce_side_table', color='none', facing='east', waterlogged=False)
    p.put(1, 2, 7, 'handcrafted:terracotta_bowl', facing='east', pieces=2, waterlogged=False)
    p.put(1, 3, 6, 'handcrafted:spruce_shelf', facing='east', shape='single', type=2)
    p.put(1, 4, 6, 'handcrafted:stackable_book', books=3, facing='east', seed=13)
    p.put(11, 3, -5, 'handcrafted:oak_shelf', facing='west', shape='single', type=1)
    p.put(11, 4, -5, 'handcrafted:stackable_book', books=2, facing='west', seed=7)
    p.box(3, 1, 3, 5, 1, 5, 'minecraft:brown_carpet')
    p.features.append('Strapped trusses, supported task lamps, reachable tea/repair counters, under-stair cupboard and a book-lined ledger rest alcove')


def construct(registry, source, manifest, snapshot=None):
    p=Finish(registry,source,manifest,snapshot)
    glazing(p);ridge(p);wheelhouse(p);dormer(p,-3,2,4,8);dormer(p,6,1,3,8)
    porch_and_chimney(p);interior(p)
    validate(p)
    return p


def validate(p):
    if set(p.blocks)&p.fixed:
        raise UserError('An architectural target entered a protected operating envelope')
    composed=p.original|p.blocks
    building={pos:state for pos,state in composed.items() if 1302<=pos[0]<=1324 and -1012<=pos[2]<=-985}
    def inspection_glass(pos):
        x,y,z=(pos[n]-ORIGIN[n] for n in range(3))
        return (1305<=pos[0]<=1309 and 67<=pos[1]<=73 and -1002<=pos[2]<=-998) or (y in (2,3) and ((1<=x<=3 and z==-6) or (x==0 and z in (-4,-3))))
    if any(base(state)=='minecraft:glass' and not inspection_glass(pos) for pos,state in building.items()):
        raise UserError('A house glass opening still lacks a genuine fancy window')
    for z in range(-7,12):
        if base(composed.get(p.world(6,12,z),AIR)) in VOID or 'type=bottom' not in composed.get(p.world(6,13,z),''):
            raise UserError('The joined ridge has a daylight gap')
    for z in (-4,-3,-2):
        if base(composed.get(p.world(0,11,z),AIR)) in VOID:
            raise UserError('The broad dormer gable has a daylight gap')
    return {'building_material_rule':require_material_rule(building,'Composed complete Copper Wren mill and hydraulic observation bay'),
            'outdoor_nine_rule':require_outdoor_rule(composed,'Complete R2 quarter plus R3 authored finish'),
            'protected_targets':0,'protected_cells':len(p.fixed),'saved_be_changes':0,
            'source_only':'Native preimage, placement, lighting/window models and artistic acceptance remain pending'}


def payload(p,states,backup_sha,name,tags=False):
    palette=sorted(set(states.values()));index={s:n for n,s in enumerate(palette)}
    return {'format':'awft-native-settlement:1','name':name,'created':utcnow(),
            'seed':p.registry['seed'],'world_path':p.registry['world_path'],'backup_sha256':backup_sha,
            'bounds':[min(v[0] for v in states),min(v[2] for v in states),max(v[0] for v in states),max(v[2] for v in states)],
            'palette':palette,'blocks':[[*pos,index[state]] for pos,state in sorted(states.items())],
            'block_entities':[{'pos':list(pos),'nbt':tag} for pos,tag in sorted(p.tags.items())] if tags else [],
            'commands':[],'landmarks':[],'validation':'STAGED ARCHITECTURAL DELTA ONLY; native before/after and graphical review required'}


def prepare(home,registry_path,source_path,manifest_path,backup_id,backup_sha,output):
    home,registry_path,source_path,manifest_path,output=map(lambda x:Path(x).resolve(),(home,registry_path,source_path,manifest_path,output))
    if not home.is_relative_to(Path(r'D:\A World for Two\staging\world-tests')) or not output.is_relative_to(home/'staging') or output.exists():
        raise UserError('Separate artistic world and NEW private output required')
    if not re.fullmatch(r'\d{8}T\d{6}Z-[a-f0-9]{6}',backup_id) or not re.fullmatch('[a-f0-9]{64}',backup_sha):
        raise UserError('Explicit current stopped checkpoint required')
    if digest(source_path)!=SOURCE_PLAN_SHA or digest(manifest_path)!=SOURCE_MANIFEST_SHA:
        raise UserError('Exact native-placed immutable R2 architectural predecessor required')
    if any(p.stat().st_size>8*1024**2 for p in (registry_path,source_path,manifest_path)):
        raise UserError('Finite actual registry and immutable architectural inputs required')
    admission=guard(4*1024**2,MAX_OUTPUT)
    registry,source,manifest=read_json(registry_path),read_json(source_path),read_json(manifest_path)
    if any(source.get(k)!=registry.get(k) for k in ('seed','world_path')) or not Path(registry['world_path']).resolve().is_relative_to(home/'world'):
        raise UserError('Actual artistic world and registry identity differ')
    receipt=read_json(home/'dashboard/settlement/backup-receipt.json')
    if receipt.get('verified') is not True or receipt.get('id')!=backup_id or receipt.get('sha256')!=backup_sha:
        raise UserError('Rebind details to the parent-reviewed current checkpoint, including post-commission state')
    snapshot=BackupWorld(home,receipt,registry)
    try:
        p=construct(registry,source,manifest,snapshot)
        sources=list(snapshot.sources)
    finally:snapshot.close()
    documents={}
    def encode(name,value):
        raw=(json.dumps(value,separators=(',',':'),ensure_ascii=False)+'\n').encode();documents[name]=raw
        return hashlib.sha256(raw).hexdigest()
    delta=encode('mill-detail.json',payload(p,p.blocks,backup_sha,'Copper Wren R3 architectural finish',True))
    before=encode('native-before.json',payload(p,p.previous,backup_sha,'VERIFY ONLY - exact saved R3 mill preimage'))
    details={'format':'awft-artistic-mill-detail:1','created':utcnow(),'source_sha256':digest(Path(__file__)),
             'predecessor_plan_sha256':SOURCE_PLAN_SHA,'predecessor_manifest_sha256':SOURCE_MANIFEST_SHA,
             'registry_sha256':digest(registry_path),'checkpoint_id':backup_id,'checkpoint_sha256':backup_sha,
             'plan_sha256':delta,'before_sha256':before,'placements':len(p.blocks),'new_block_entities':len(p.tags),
             'previous_states':[{'pos':list(pos),'old':p.previous[pos],'new':state} for pos,state in sorted(p.blocks.items())],
             'features':p.features,'feature_counts':{k:len(v) for k,v in p.groups.items()},'checks':validate(p),'sources':sources,
             'block_counts':dict(Counter(base(v) for v in p.blocks.values())),'reserve_guard':admission,
             'cameras':[{'name':'Roof, porch and observation bay','eye':[1296,77,-981],'look_at':[1314,75,-999]},
                        {'name':'Bright machine hall','eye':[1317,70,-992],'look_at':[1315,72,-1000]},
                        {'name':'Lived-in ledger and craft edges','eye':[1318,70,-1003],'look_at':[1313,69,-992]},
                        {'name':'Framed sealed wheelhouse','eye':[1297,73,-1007],'look_at':[1306,71,-1000]}],
             'native_admission':'Must rebind after R2 commissioning; no old proof is transferred to this geometry',
             'commands':0,'world_mutation_performed':False,'status':'STAGED ONLY; actual native and visual review pending'}
    manifest_sha=encode('manifest.json',details)
    if sum(map(len,documents.values()))>MAX_OUTPUT:raise UserError('Finite private output bound exceeded')
    output.mkdir(parents=True,exist_ok=False)
    for name,raw in documents.items():(output/name).write_bytes(raw)
    return {'manifest':str(output/'manifest.json'),'manifest_sha256':manifest_sha,'plan_sha256':delta,
            'before_sha256':before,'placements':len(p.blocks),'bytes':sum(map(len,documents.values())),'native_action':'Not performed'}


def corrected_placed_states(registry, original, r2_source):
    """Derive only the reviewed automatic parts, preserving all other geometry."""
    before=decode(original);composed=decode(r2_source)|before
    corrected=copy.deepcopy(original);changes=[]
    for row in corrected['blocks']:
        pos=tuple(row[:3]);prior=original['palette'][row[3]];key=base(prior)
        if key not in ('mcwwindows:dark_oak_plank_window','mcwwindows:spruce_plank_window','mcwroofs:spruce_top_roof'):
            continue
        fields=properties(prior)
        if 'part' not in fields:
            raise UserError('An exact original automatic-part property is required')
        x,y,z=pos
        same=lambda q:base(composed.get(q,AIR))==key
        if key.startswith('mcwwindows:'):
            facing=fields.get('facing')
            if facing not in ('north','east'):
                raise UserError('Unreviewed native window plane')
            negative,positive=((x-1,y,z),(x+1,y,z)) if facing=='north' else ((x,y,z-1),(x,y,z+1))
            if not same(negative) and not same(positive):
                continue  # Preserve the separately observed single-column parts.
            part=joined_window_part(same((x,y+1,z)),same((x,y-1,z)),same(negative),same(positive))
        else:
            part=joined_dormer_top_part(same((x+1,y,z)),same((x-1,y,z)),
                north=same((x,y,z-1)),south=same((x,y,z+1)))
        if part==fields['part']:
            continue
        schema=registry['blocks'].get(key,{})
        if part not in schema.get('part',()):
            raise UserError('The exact native joined part is not registered')
        fields['part']=part
        value=key+'['+','.join(k+'='+v for k,v in sorted(fields.items()))+']'
        if value not in corrected['palette']:
            corrected['palette'].append(value)
        row[3]=corrected['palette'].index(value)
        changes.append({'pos':list(pos),'before':prior,'after':value,
                        'changed_properties':['part'],'same_block_identity':True})
    if corrected['block_entities']!=original['block_entities'] or corrected['commands']!=original['commands']:
        raise UserError('Native join correction must retain all original tag and command expectations')
    return corrected,changes


def verify_saved_joined_states(plan,snapshot):
    """Require every original supplied property; omitted defaults stay omitted."""
    for pos,expected in decode(plan).items():
        actual=snapshot.state(pos)
        if base(expected)!=base(actual):
            raise UserError('Saved R3 block identity differs at '+str(pos))
        supplied=properties(expected);observed=properties(actual)
        for key,value in supplied.items():
            if observed.get(key)!=value:
                raise UserError('Saved R3 supplied property differs at '+str(pos)+' '+key)


def prepare_joined_verification(home,registry_path,source_path,manifest_path,placed_plan,backup_id,backup_sha,output):
    """Emit verification only for the exact already-placed native R3 finish.

    It never produces a replacement placement delta or replays its inventories,
    fluids, connections or block-entity data. A native verifier remains required.
    """
    home,registry_path,source_path,manifest_path,placed_plan,output=map(lambda x:Path(x).resolve(),
        (home,registry_path,source_path,manifest_path,placed_plan,output))
    if (not home.is_relative_to(Path(r'D:\A World for Two\staging\world-tests'))
            or not placed_plan.is_relative_to(home/'staging') or not output.is_relative_to(home/'staging') or output.exists()):
        raise UserError('Separate artistic home, immutable placed input and new private output required')
    if (digest(placed_plan)!=PLACED_R3_SHA or digest(source_path)!=SOURCE_PLAN_SHA
            or digest(manifest_path)!=SOURCE_MANIFEST_SHA):
        raise UserError('The exact reviewed placed R3 and original R2 inputs are required')
    if any(p.stat().st_size>8*1024**2 for p in (registry_path,source_path,manifest_path,placed_plan)):
        raise UserError('Finite original geometry and native registry inputs required')
    admission=guard(4*1024**2,MAX_OUTPUT)
    for name,sha in JOIN_APIS.items():
        if digest(home/'server/mods'/name)!=sha:
            raise UserError('Pinned native join API differs: '+name)
    receipt=read_json(home/'dashboard/settlement/backup-receipt.json')
    if receipt.get('verified') is not True or receipt.get('id')!=backup_id or receipt.get('sha256')!=backup_sha:
        raise UserError('Current parent-reviewed stopped checkpoint required for native joined-state verification')
    registry,original,r2,manifest=map(read_json,(registry_path,placed_plan,source_path,manifest_path))
    if any(original.get(k)!=registry.get(k) or r2.get(k)!=registry.get(k) for k in ('seed','world_path')):
        raise UserError('Original placed geometry and actual registry world differ')
    corrected,changes=corrected_placed_states(registry,original,r2)
    kinds=Counter(base(row['before']) for row in changes)
    if (len(corrected['blocks'])!=516 or len(changes)!=63
            or sum(n for key,n in kinds.items() if key.startswith('mcwwindows:'))!=54
            or kinds['mcwroofs:spruce_top_roof']!=9):
        raise UserError('The reviewed correction is exactly 54 window and 9 ridge parts at the original 516 positions')
    # Material IDs, positions, orientations, inventories and the original sign
    # expectation are unchanged. The normal complete-building check still runs.
    p=Finish(registry,r2,manifest);p.blocks=decode(corrected)
    checks=validate(p)
    snapshot=BackupWorld(home,receipt,registry)
    try:
        verify_saved_joined_states(corrected,snapshot)
        sources=snapshot.sources.copy()
    finally:snapshot.close()
    corrected.update(name='VERIFY ONLY - exact placed R3 native Macaw joined parts',created=utcnow(),
        backup_sha256=backup_sha,
        validation='VERIFY ONLY. Already placed R3; no construction replay. Every supplied state and original tag expectation must be verified natively.')
    raw=(json.dumps(corrected,separators=(',',':'),ensure_ascii=False)+'\n').encode()
    failed=home/'dashboard/settlement/settlement-result-685728bd-d776-4bc6-97ec-8d30f66a9694.json'
    if not failed.is_file() or failed.stat().st_size>512*1024:
        raise UserError('Retain the original bounded failed native verification receipt')
    details={'format':'awft-mill-native-joined-verification:1','created':utcnow(),
        'source_sha256':digest(Path(__file__)),'original_placed_plan_sha256':PLACED_R3_SHA,
        'original_r2_plan_sha256':SOURCE_PLAN_SHA,'original_r2_manifest_sha256':SOURCE_MANIFEST_SHA,
        'registry_sha256':digest(registry_path),'checkpoint_id':backup_id,'checkpoint_sha256':backup_sha,
        'native_apis':JOIN_APIS,'plan_sha256':hashlib.sha256(raw).hexdigest(),
        'positions':516,'part_corrections':63,'window_corrections':54,'roof_corrections':9,
        'block_identity_changes':0,'position_changes':0,'orientation_changes':0,
        'original_block_entity_expectations_retained':True,'placement_payload_emitted':False,
        'changes':changes,'checks':checks,'saved_sources':sources,'reserve_guard':admission,
        'original_failed_native_verification':{'file':failed.relative_to(home).as_posix(),'sha256':digest(failed)},
        'partial_mill_state':'Six existing native tube links and water sources are preserved. No feed or train was performed. Full R2 commissioning must not replay; any resume must explicitly bind this R3 geometry.',
        'native_action':'None. Saved-state agreement is not a native verification or visual acceptance.'}
    meta=(json.dumps(details,separators=(',',':'),ensure_ascii=False)+'\n').encode()
    if len(raw)+len(meta)>MAX_OUTPUT:
        raise UserError('Finite joined verification output exceeded')
    output.mkdir(parents=True,exist_ok=False)
    (output/'mill-detail-native-verify-only.json').write_bytes(raw)
    (output/'joined-state-manifest.json').write_bytes(meta)
    return {'output':str(output),'verify_plan_sha256':hashlib.sha256(raw).hexdigest(),
            'manifest_sha256':hashlib.sha256(meta).hexdigest(),'positions':516,'part_corrections':63,
            'native_actions':0,'placement_payload_emitted':False}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('home','registry','source','manifest','output'):parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--backup-id',required=True);parser.add_argument('--backup-sha256',required=True)
    parser.add_argument('--placed-plan',type=Path,help='Already placed immutable R3: emit native verification only, never another placement delta')
    a=parser.parse_args()
    result=(prepare_joined_verification(a.home,a.registry,a.source,a.manifest,a.placed_plan,a.backup_id,a.backup_sha256,a.output)
            if a.placed_plan else prepare(a.home,a.registry,a.source,a.manifest,a.backup_id,a.backup_sha256,a.output))
    print(json.dumps(result,indent=2))
