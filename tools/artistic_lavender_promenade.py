"""Rosewater's site-bound lavender promenade; existing native construction packets.

Reads an authenticated retained checkpoint, never live region files. Preparation
writes finite private plans only. The master admits before/support/place/normal/
full operations and reviews genuine Minecraft photographs separately.
"""
from __future__ import annotations

import argparse
from collections import Counter, deque
import hashlib
import json
from pathlib import Path

from control_room.common import UserError, digest, read_json, utcnow
from tools.playtest import guard
from tools.settlement_attractions import BackupWorld, base
from tools.artistic_materials import require_material_rule

MIB = 1024**2
MAX_OUTPUT = 24*MIB
MAX_TARGETS = 12000
BOUNDS = (1285, -996, 1303, -952)
POSTS = (-995, -990, -984, -979, -974, -969, -964, -959, -953)
AIR = {'minecraft:air', 'minecraft:cave_air', 'minecraft:void_air'}
SOFT = AIR | {'minecraft:short_grass', 'minecraft:tall_grass', 'minecraft:fern',
             'regions_unexplored:grass_sprouts', 'farm_and_charm:wild_carrots',
             'farm_and_charm:wild_barley', 'farm_and_charm:wild_corn'}
GROUND = {'minecraft:grass_block', 'minecraft:dirt', 'minecraft:stone',
          'minecraft:gravel', 'minecraft:sand'}
PAVING = {'minecraft:gravel', 'minecraft:dirt_path', 'minecraft:cobblestone',
          'minecraft:polished_andesite', 'minecraft:stone_brick_stairs',
          'minecraft:mossy_stone_bricks'}
GRAPE = (1297, 67, -958)
SOURCES = (
 'prototype-castle-palace-e6ffcde57520b8cb/prototype.json',
 'prototype-castle-palace-e6ffcde57520b8cb/combined-final-delta.json',
 'prototype-castle-palace-e6ffcde57520b8cb/mount-support-delta.json',
 'artistic-castle-interior-r4-20261027T1701Z/castle-interior.json',
 'artistic-depth-castle-mill-20261027T1900Z/castle-depth.json',
 'artistic-castle-depth-native-parts-20261027T1905Z/castle-depth-native-verify-only.json',
)
WALK_SOURCE = 'castle-garden-arrival-20261027T0952Z/prototype.json'
CAPTURE_VIEWS = (
    ('north-entrance', [1294.5,66,-994.5], [1294.5,73,-961]),
    ('south-entrance', [1294.5,67,-953.5], [1294.5,73,-987]),
    ('central-aisle', [1293.5,66,-978.5], [1294.5,73,-959]),
    ('ceiling-coffers', [1294.5,66,-978.5], [1293.5,78,-974]),
    ('west-gardens', [1279.5,69,-972.5], [1288,71,-974]),
    ('east-gardens', [1308.5,70,-979.5], [1297,73,-978]),
    ('roof-and-castle', [1308.5,90,-970.5], [1289,73,-978]),
)


def decode(plan):
    return {tuple(row[:3]): plan['palette'][row[3]] for row in plan['blocks']}


def floor(z):
    return 65 if z <= -967 else 66


def side_opening(z):
    return z in (-988, -987, -956, -955)


class Promenade:
    def __init__(self, registry, snapshot, protected=(), walk=None):
        self.registry, self.snapshot = registry, snapshot
        self.protected, self.walk = set(protected), walk or {}
        self.blocks, self.before, self.support, self.retained = {}, {}, {}, {}
        self.phase, self.parts = 'structure', {}
        self.pendants, self.beds, self.seats = [], [], []
        self.route, self.joins = {}, {}

    def state(self, key, **props):
        schema = self.registry['blocks'].get(key)
        if schema is None:
            raise UserError('Missing installed promenade material: '+key)
        # Complete native properties, including defaults, are explicit for all
        # authored states. No assumed shape or neighbour-derived fence state.
        for name, value in props.items():
            if name not in schema or str(value).lower() not in schema[name]:
                raise UserError('Unregistered promenade state: '+str((key, props)))
        if set(props) != set(schema):
            raise UserError('Supply every native property: '+str((key, schema, props)))
        return key+('['+','.join(k+'='+str(v).lower() for k,v in sorted(props.items()))+']' if props else '')

    def actual(self, p):
        return self.snapshot.state(p)

    def at(self, p):
        return self.blocks.get(p, self.actual(p))

    def keep(self, p):
        value = self.actual(p)
        self.retained[p] = value
        return value

    def put(self, x, y, z, key, **props):
        p = x,y,z
        if not (BOUNDS[0] <= x <= BOUNDS[2] and BOUNDS[1] <= z <= BOUNDS[3]
                and 63 <= y <= 80):
            raise UserError('Promenade left its surveyed site: '+str(p))
        value, old = self.state(key, **props), self.actual(p)
        if p in self.blocks and self.blocks[p] != value:
            # Design composition is deliberate; every final target has one
            # phase owner and its original stopped preimage remains unchanged.
            self.parts.setdefault(self.phase,set()).discard(p)
            for points in self.parts.values(): points.discard(p)
        if value == old:
            self.blocks.pop(p,None)
            self.before.pop(p,None)
            self.retained[p] = old
            return
        if p in self.protected or p in self.snapshot.protected:
            raise UserError('Preserve castle or native block entity: '+str((p,old)))
        if p in self.walk:
            raise UserError('Preserve original route exactly: '+str((p,old)))
        if base(old) not in SOFT | GROUND:
            raise UserError('Preserve saved object/water/plant: '+str((p,old)))
        if base(old) in GROUND and y > floor(z)+1:
            raise UserError('No elevated terrain excavation: '+str((p,old)))
        self.blocks[p], self.before[p] = value, old
        self.retained.pop(p,None)
        self.parts.setdefault(self.phase,set()).add(p)
        if len(self.blocks) > MAX_TARGETS:
            raise UserError('Split promenade below the native batch target cap')

    def supported_floor(self, x, z, y, key):
        # Only the top two natural soil layers may be dressed. There is no
        # water filling, gully filling, speculative foundation or deep cut.
        for yy in range(y-1, 62, -1):
            q = x,yy,z
            old = self.actual(q)
            if base(old) in GROUND or q in self.walk and base(old) in PAVING:
                self.support[q] = old
                break
            if base(old) not in SOFT:
                raise UserError('No dry qualified substrate: '+str((q,old)))
            self.put(x,yy,z,'chipped:calcite_bricks')
        else:
            raise UserError('Missing shallow substrate: '+str((x,z)))
        q = x,y,z
        if q in self.walk:
            if self.actual(q) != self.walk[q]:
                raise UserError('Existing walking interface changed: '+str(q))
            self.keep(q)
        else:
            self.put(x,y,z,key)


def build(p):
    # Nine-wide pale central paving, with the existing two-wide walking spine
    # and its actual half-step retained byte-for-state as a read-only inlay.
    for z in range(-996,-951):
        f = floor(z)
        for x in range(1287,1302):
            if (x,z) in {(1287,-988),(1288,-988),(1289,-988),
                         (1287,-987),(1288,-987),(1289,-987)}:
                continue  # Original west-facing court stairs remain intact.
            key = ('chipped:bordered_calcite' if x in (1287,1289,1299,1301)
                   else 'chipped:checkered_calcite_tiles' if z in POSTS
                   else 'chipped:blank_calcite_carving' if x in (1292,1295)
                   else 'chipped:tiled_calcite')
            p.supported_floor(x,z,f,key)
            if z == -967 and x not in (1296,1297):
                # Extend the real original south-facing half-step across the
                # widened aisle; never place a full-block jump at that rise.
                p.put(x,f,z,'create:cut_calcite_stairs',facing='south',half='bottom',
                      shape='straight',waterlogged=False)
            for yy in range(f+1,f+4):
                q = x,yy,z
                if q == GRAPE:
                    p.keep(q)
                elif q in p.walk:
                    p.keep(q)
                elif base(p.actual(q)) in SOFT:
                    if base(p.actual(q)) not in AIR: p.put(x,yy,z,'minecraft:air')
                elif base(p.actual(q)) in GROUND and yy == f+1:
                    p.put(x,yy,z,'minecraft:air')
                else:
                    raise UserError('Unreviewed obstruction in widened aisle: '+str((q,p.actual(q))))
    # Deep stepped footings, banded shafts and projecting capitals. All eighteen
    # columns support both sides of the complete roof, rather than a facade.
    for z in POSTS:
        f = floor(z)
        for x in (1288,1300):
            for xx in range(x-1,x+2):
                for zz in range(z-1,z+2):
                    if not -996 <= zz <= -952: continue
                    if xx in (1290,1298): continue
                    p.put(xx,floor(zz)+1,zz,'chipped:carved_purpur_block')
            for y in range(f+2,75):
                key = ('chipped:ornate_purpur_block_pillar' if y in (f+2,72)
                       else 'chipped:purpur_block_pillar' if y <= 71 else 'chipped:pink_terracotta_pillar')
                p.put(x,y,z,key,**({'axis':'y'} if key != 'chipped:purpur_block_pillar' else {}))
            for xx,zz in ((x-1,z),(x+1,z),(x,z-1),(x,z+1)):
                if -996 <= zz <= -952:
                    p.put(xx,74,zz,'chipped:carved_purpur_block')
            for xx in range(x-1,x+2):
                for zz in range(z-1,z+2):
                    if -996 <= zz <= -952:p.put(xx,75,zz,'chipped:purpur_block_mini_tiles')
            # Inward corbel pair, followed by a complete crossbeam at Y76.
            inward = 1 if x == 1288 else -1
            p.put(x+inward,73,z,'minecraft:purpur_stairs',facing='west' if inward==1 else 'east',
                  half='top',shape='straight',waterlogged=False)
            p.put(x+2*inward,75,z,'minecraft:purpur_stairs',facing='west' if inward==1 else 'east',
                  half='top',shape='straight',waterlogged=False)
        for x in range(1288,1301):
            p.put(x,76,z,'chipped:purpur_block_bricks' if x in (1288,1300) else 'chipped:pink_terracotta_tiles')
    # Both longitudinal beams, side clerestory pattern, recessed coffers and a
    # fully tiled weathering layer. Long uninterrupted flat undersides are absent.
    for z in range(-996,-951):
        for x in (1288,1300):
            p.put(x,76,z,'chipped:purpur_block_bricks')
            if z not in POSTS and not any(abs(z-v)==1 for v in POSTS):
                p.put(x,74,z,'chipped:purpur_block_mini_tiles')
        for x in range(1287,1302):
            p.put(x,78,z,'chipped:purpur_block_scales' if z in POSTS
                  else 'chipped:purpur_block_mini_tiles' if (x-1287)%4==0
                  else 'chipped:tiled_purpur_block')
            if x in (1287,1301):
                p.put(x,77,z,'minecraft:purpur_stairs',facing='east' if x==1287 else 'west',
                      half='top',shape='straight',waterlogged=False)
            elif z not in POSTS and x in (1291,1297):
                p.put(x,77,z,'chipped:pink_terracotta_tile')
        # Low articulated cornice tops finish the entire exterior roof perimeter.
        if z in POSTS:
            for x in (1287,1301):p.put(x,79,z,'minecraft:purpur_slab',type='bottom',waterlogged=False)
    # Arches have a stepped four-metre clear side opening with genuine connected
    # spandrels above. Native stair properties are independently predictable.
    for a,b in zip(POSTS,POSTS[1:]):
        for x in (1288,1300):
            for z in range(a+1,b):
                edge = min(z-a,b-z)
                if edge <= 2:
                    p.put(x,73+edge,z,'minecraft:purpur_stairs',facing='north' if z-a<=b-z else 'south',
                          half='top',shape='straight',waterlogged=False)
    p.phase = 'lights'
    for n,(a,b) in enumerate(zip(POSTS,POSTS[1:])):
        z = (a+b)//2
        for j,x in enumerate((1290,1294,1298)):
            length = (3,5,4)[(n+j)%3]
            p.put(x,77,z,'chipped:carved_amethyst_block')
            p.put(x,76,z,'minecraft:chain',axis='y',waterlogged=False)
            for y in range(76-length,76):p.put(x,y,z,'minecraft:end_rod',facing='down')
            p.pendants.append({'attachment':[x,77,z],'rods':length,'bottom_y':76-length,
                               'clear_blocks_below':76-length-floor(z)-1})
    p.phase = 'gardens'
    # Two-metre-deep raised soil beds, rooted paired lilacs, variable bush
    # heights and supported climbing foliage. The existing tree edge is retained.
    for side,xs in (('west',(1286,1287)),('east',(1301,1302))):
        for z in range(-995,-952):
            if side_opening(z) or side=='west' and z<=-984:
                continue
            if side=='east' and -965<=z<=-954:
                continue  # The retained tree and its complete canopy remain.
            f=floor(z)
            for x in xs:
                q=(x,f+1,z)
                # No imported owner object or existing leaf is cleared for a bed.
                if base(p.actual(q)) not in SOFT or q in p.protected:continue
                if q in p.blocks and base(p.blocks[q]) not in AIR:continue
                p.supported_floor(x,z,f,'chipped:purpur_block_bricks')
                p.put(x,f+1,z,'minecraft:dirt')
                if (z+2*x)%5==0:
                    p.put(x,f+2,z,'minecraft:lilac',half='lower')
                    p.put(x,f+3,z,'minecraft:lilac',half='upper')
                elif (z+x)%3==0:
                    p.put(x,f+2,z,'regions_unexplored:purple_lupine')
                elif (z+x)%4==0:
                    p.put(x,f+2,z,'regions_unexplored:lavender_wisteria_shrub',half='lower')
                    p.put(x,f+3,z,'regions_unexplored:lavender_wisteria_shrub',half='upper')
                else:
                    p.put(x,f+2,z,'minecraft:flowering_azalea' if (z+x)%2 else 'minecraft:azalea')
                p.beds.append([x,f+1,z])
            # A complete outer retaining lip encloses each raised bed. The
            # occupied inner edge uses the actual column bases/low ledges.
            outer=1285 if side=='west' else 1303
            q=outer,f+1,z
            if base(p.actual(q)) in SOFT and q not in p.protected:
                p.supported_floor(outer,z,f,'chipped:purpur_block_bricks')
                p.put(outer,f+1,z,'chipped:carved_purpur_block')
                p.put(outer,f+2,z,'minecraft:purpur_slab',type='bottom',waterlogged=False)
            # Pale front ledge and layered leafy climbing frames are on the
            # column line, outside the continuous central walking reservation.
            frame=1288 if side=='west' else 1300
            if min(abs(z-v) for v in POSTS)>1:
                p.put(frame,f+1,z,'chipped:purpur_block_bricks')
                p.put(frame,f+2,z,'minecraft:purpur_slab',type='top',waterlogged=False)
                crown=min(f+6+(z%2),73)
                inward=1 if side=='west' else -1
                for y in range(f+3,crown+1):
                    p.put(frame,y,z,'minecraft:flowering_azalea_leaves' if (y+z)%3 else 'minecraft:azalea_leaves',
                          distance=7,persistent=True,waterlogged=False)
                    # A second leafy plane gives each hedge actual volume,
                    # while the nine-wide principal aisle stays untouched.
                    if f+4<=y<crown:
                        p.put(frame+inward,y,z,'regions_unexplored:lavender_wisteria_leaves',
                              distance=7,persistent=True,waterlogged=False)
    # Supported trailing glowberry greenery stays above the side beds, away
    # from the pedestrian body volume. Native attached vines require normal
    # placement survival and light readback during the master's actual run.
    for x in (1287,1301):
        for z in (-982,-977,-972,-967):
            p.put(x,77,z,'chipped:purpur_block_mini_tiles')
            for y in (76,75):p.put(x,y,z,'minecraft:cave_vines_plant',berries=True)
            p.put(x,74,z,'minecraft:cave_vines',age=25,berries=True)
    # Two small castle-facing seating bays have their own supported floors and
    # flowers, opening inward at gaps between the columns.
    p.phase='seating'
    for z in (-981,-962):
        for xx in (1285,1286,1287):
            for zz in range(z-1,z+2):
                f=floor(zz)
                p.supported_floor(xx,zz,f,'chipped:checkered_calcite_tiles')
                for y in (f+1,f+2,f+3):
                    # Remove only earlier source-authored plants from this same
                    # composition; the saved world is still independently gated.
                    p.put(xx,y,zz,'minecraft:air')
        f=floor(z)
        p.put(1285,f+1,z,'handcrafted:cherry_bench',color='pink',facing='east',
              shape='single',waterlogged=False)
        p.put(1285,f+1,z+1,'handcrafted:cherry_side_table',color='pink',facing='east',waterlogged=False)
        p.put(1285,f+2,z+1,'minecraft:potted_allium')
        p.seats.append({'bench':[1285,f+1,z],'view':'west-facing castle garden bay, seat faces the promenade'})
    p.beds=[q for q in p.beds if p.at(tuple(q))=='minecraft:dirt'
            and base(p.at((q[0],q[1]+1,q[2]))) in {'minecraft:lilac','minecraft:azalea',
            'minecraft:flowering_azalea','regions_unexplored:purple_lupine','regions_unexplored:lavender_wisteria_shrub'}]
    return p


def validate(p):
    # Continuous six-wide player corridor is mandatory even at the preserved
    # grape niche. Most sections offer the full nine metres between the columns.
    for z in range(-996,-951):
        f=floor(z)
        for x in range(1290,1296):
            p.route[x,f,z]=p.at((x,f,z))
            if base(p.at((x,f,z))) in SOFT:
                raise UserError('Missing clear corridor floor')
            for y in (f+1,f+2,f+3):
                q=x,y,z
                if base(p.at(q)) not in AIR:raise UserError('Player corridor obstruction: '+str(q))
                p.route[q]=p.at(q)
    # Read-only lateral route witnesses include their original floors, two
    # player-body levels and graded stairs, from the castle and south gate.
    for q,value in p.walk.items():
        x,y,z=q
        if 1285<=x<=1298 and side_opening(z) and floor(z)<=y<=71:
            if p.at(q)!=value:raise UserError('Changed existing castle connection: '+str(q))
            p.joins[q]=value
    for q in p.protected:
        if q in p.blocks:raise UserError('Protected source collision')
    if p.blocks.keys() & p.snapshot.protected:raise UserError('Native BE collision')
    if len(p.pendants)!=24 or min(v['clear_blocks_below'] for v in p.pendants)<4:
        raise UserError('Pendant count or walking headroom failed')
    for z in POSTS:
        for x in (1288,1300):
            if any(base(p.at((x,y,z))) in AIR for y in range(floor(z)+1,77)):
                raise UserError('Missing complete support column on one roof side')
    for light in p.pendants:
        x,y,z=light['attachment']
        if base(p.at((x,y,z)))!='chipped:carved_amethyst_block' or base(p.at((x,y-1,z)))!='minecraft:chain':
            raise UserError('Disconnected pendant attachment')
        if any(p.at((x,yy,z))!='minecraft:end_rod[facing=down]' for yy in range(light['bottom_y'],y-1)):
            raise UserError('Missing pendant white rod')
    # Every authored non-air component must join a component rooted in an
    # actual substrate. This catches floating caps, plants, rods and roofs;
    # model appearance and real native survival are separate checks.
    solids={q for q,s in p.blocks.items() if base(s) not in AIR}
    roots={q for q in solids if (q[0],q[1]-1,q[2]) in p.support
           or (q[0],q[1]-1,q[2]) in p.retained and base(p.retained[q[0],q[1]-1,q[2]]) not in AIR}
    seen=set(roots);todo=deque(roots)
    while todo:
        x,y,z=todo.popleft()
        for q in ((x-1,y,z),(x+1,y,z),(x,y-1,z),(x,y+1,z),(x,y,z-1),(x,y,z+1)):
            if q in solids and q not in seen:seen.add(q);todo.append(q)
    if solids-seen:raise UserError('Unconnected decorative component: '+str(sorted(solids-seen)[:10]))
    p.keep(GRAPE)
    material = require_material_rule(p.blocks,'Grand Lavender Promenade')
    return {'length_m':45,'nominal_walk_width_m':9,'continuous_clear_width_m':6,
            'floor_y':[65,66],'ceiling_beam_y':76,'clear_blocks_below_ceiling':[9,10],
            'paired_columns':9,'bay_intervals_m':[b-a for a,b in zip(POSTS,POSTS[1:])],
            'white_pendants':24,'rod_lengths':[3,4,5],
            'rooted_planting_cells':len(p.beds),'seating_bays':2,
            'volumetric_foliage_blocks':sum(base(s).endswith('_leaves') for s in p.blocks.values()),
            'all_authored_solid_components_connected_to_saved_substrate':True,
            'saved_routes_and_grape_retained':True,'native_BEs_replaced':0,
            'material_rule':material,
            'native_placement_and_visual_acceptance':'pending'}


def payload(registry, sha, cells, name):
    if not cells:raise UserError('Empty native packet')
    palette=sorted(set(cells.values()));indexes={v:i for i,v in enumerate(palette)}
    return {'format':'awft-native-settlement:1','name':name,'created':utcnow(),
            'world_path':registry['world_path'],'seed':registry['seed'],'backup_sha256':sha,
            'bounds':list(BOUNDS),'palette':palette,
            'blocks':[[*q,indexes[v]] for q,v in sorted(cells.items(),key=lambda row:(row[0][1],row[0][0],row[0][2]))],
            'block_entities':[],'commands':[],'landmarks':[],
            'validation':'SOURCE ONLY: exact native before/support/place/normal/full and actual Minecraft art review required'}


def prepare(home, output, backup_id, backup_sha256):
    home,output=Path(home).resolve(),Path(output).resolve()
    if not home.is_relative_to(Path(r'D:\A World for Two\staging\world-tests')) or output.exists() or not output.is_relative_to(home/'staging'):
        raise UserError('New private staging output in the existing construction home required')
    admission=guard(8*MIB,MAX_OUTPUT)
    registry_path=home/'dashboard/settlement/registry.json'
    registry=read_json(registry_path)
    custody=read_json(home/'dashboard/settlement/backup-receipt.json')
    if custody.get('verified') is not True:
        raise UserError('Existing canonical native custody receipt is required; never replace it')
    protected=set();inputs=[]
    for name in SOURCES+(WALK_SOURCE,):
        path=home/'staging'/name
        if path.stat().st_size>16*MIB:raise UserError('Oversized immutable source')
        value=read_json(path)
        if any(value[k]!=registry[k] for k in ('seed','world_path')):raise UserError('Foreign-world exclusion')
        if name==WALK_SOURCE:walk=decode(value)
        else:protected.update(decode(value))
        inputs.append({'file':name,'sha256':digest(path)})
    receipt={'id':backup_id,'sha256':backup_sha256,'verified':True}
    snapshot=BackupWorld(home,receipt,registry)
    try:
        p=build(Promenade(registry,snapshot,protected,walk));checks=validate(p)
        sources=snapshot.sources.copy()
    finally:snapshot.close()
    docs={};record={}
    def emit(name,value):
        raw=(json.dumps(value,separators=(',',':'),ensure_ascii=False)+'\n').encode()
        docs[name]=raw
        if sum(map(len,docs.values()))>MAX_OUTPUT:raise UserError('Finite promenade output exceeded')
        record[name]={'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}
    final=p.blocks|p.route|p.joins|p.retained
    support=p.support|p.joins|p.retained
    emit('before.json',payload(registry,custody['sha256'],p.before,'VERIFY ONLY: stopped promenade preimage'))
    emit('support.json',payload(registry,custody['sha256'],support,'VERIFY ONLY: retained substrate and castle route interfaces'))
    emit('place.json',payload(registry,custody['sha256'],p.blocks,'Rosewater Grand Lavender Promenade'))
    emit('normal.json',payload(registry,custody['sha256'],p.blocks,'NORMAL NEIGHBOUR SETTLE ONLY: promenade'))
    emit('full.json',payload(registry,custody['sha256'],final,'VERIFY ONLY: complete promenade and protected walking witnesses'))
    emit('manifest.json',{'format':'awft-lavender-promenade:1','at':utcnow(),
         'source_sha256':digest(Path(__file__)),'registry_sha256':digest(registry_path),
         'checkpoint':receipt,'native_custody_receipt':custody,'exclusions':inputs,'saved_sources':sources,'reserve_guard':admission,
         'packets':dict(record),'placements':len(p.blocks),'before_cells':len(p.before),
         'checks':checks,'pendants':p.pendants,'seating':p.seats,
         'required_real_capture_views':[{'name':name,'feet':feet,'look_at':target} for name,feet,target in CAPTURE_VIEWS],
         'required_lighting':['day','sunset','night'],
         'player_scale_photo':'A normal authenticated Minecraft player in third-person at the central aisle; native normal commands and actual camera input only. Do not substitute an armour stand, render or pasted character.',
         'saved_target_histogram':dict(Counter(base(v) for v in p.before.values())),
         'actual_world_writes':0,'native_actions':0,
         'required_master_sequence':['fresh reservation/checkpoint/registry and roster admission',
           'native exact BEFORE','native retained SUPPORT','bounded PLACE','ordinary neighbour settlement',
           'native complete FULL','genuine day/sunset/night/player-scale screenshots; repair defects',
           'retained normal-stop checkpoint for final release'],
         'acceptance':'PREPARED ONLY; NO IN-WORLD OR ARTISTIC ACCEPTANCE'})
    output.mkdir(parents=True,exist_ok=False)
    for name,raw in docs.items():
        with (output/name).open('xb') as stream:stream.write(raw)
    return {'output':str(output),'files':record,'placements':len(p.blocks),'checks':checks,'native_actions':0}


if __name__=='__main__':
    a=argparse.ArgumentParser(description=__doc__)
    a.add_argument('--home',type=Path,required=True);a.add_argument('--output',type=Path,required=True)
    a.add_argument('--backup-id',required=True);a.add_argument('--backup-sha256',required=True)
    print(json.dumps(prepare(**vars(a.parse_args())),indent=2))
