"""Author the real dry pirate peninsula; export plans, never touch a world.

The two requested downloaded buildings are reserved, not approximated here.
This original composition is a visual hypothesis until actual Minecraft review.
"""
from __future__ import annotations

import argparse
from collections import Counter, deque
import hashlib
import heapq
import html
import json
from pathlib import Path
import time

from control_room.backups import Backups
from control_room.common import Layout, UserError, digest, read_json, utcnow
from tools.artistic_materials import require_material_rule, require_outdoor_rule
from tools.playtest import guard
from tools.settlement_attractions import BackupWorld


AIR = 'minecraft:air'
MAX_OUTPUT = 32 * 1024**2
MAX_POSITIONS = 70_000
SITE = (1275, -1373, 1354, -1236)
REFERENCES = (
    ('https://joachimcoppens.artstation.com/projects/5XDGyJ',
     'Observed original overview: reversed capstan chandelier, ship ribs, intimate tables and green candle pools.'),
    ('https://sophieingledew.artstation.com/projects/ely5bb',
     'Observed original upper gallery: sea-fort masonry, open balustrade, cushions and a social overlook.'),
    ('https://samwestall2.artstation.com/projects/4bPm5n',
     'Observed original arch/bar sheets: carved curved timber and barrel-supported irregular bar.'),
)
# Exact downloaded works remain parent-owned conversion lanes. No source bytes,
# terrain, entities or guessed replacement geometry from either are included.
RESERVATIONS = (
    {'id': 'evgesha765-pirate-tavern', 'bounds': [1282, -1337, 1309, -1297],
     'size_xz': [28, 41], 'floor_proposal_y': 64, 'height_reserved': 44,
     'source_url': 'https://www.planetminecraft.com/project/pirate-tavern/',
     'original_sha256': 'e73346e4aa01bf9c0cea7a2e4e54b5d6b67f9f6c050b2460e6d9e6afa0301aeb',
     'status': 'RESERVED ONLY; original legacy conversion/crop/3-9 adaptation belongs to parent'},
    {'id': 'shabani1-fishermans-shop', 'bounds': [1314, -1349, 1334, -1316],
     'size_xz': [21, 34], 'rotation_proposal': 90, 'floor_proposal_y': 64, 'height_reserved': 30,
     'source_url': 'https://market.phantom-node.com/post/fishermans-shop-m34wn72u',
     'original_sha256': '2a1ecefcdbba55f86480318107dfd396ba7c98d2731711e811b5cdd0e39b5309',
     'status': 'RESERVED ONLY; exact original rotation/native state conversion belongs to parent'},
)
NATURAL = {'minecraft:'+name for name in (
    'grass_block', 'dirt', 'coarse_dirt', 'rooted_dirt', 'sand', 'red_sand',
    'gravel', 'stone', 'andesite', 'granite', 'diorite', 'clay', 'sandstone',
    'moss_block', 'podzol', 'mud')}
FLOWERS = {'minecraft:'+name for name in (
    'dandelion', 'poppy', 'blue_orchid', 'allium', 'azure_bluet', 'red_tulip',
    'orange_tulip', 'white_tulip', 'pink_tulip', 'oxeye_daisy', 'cornflower',
    'lily_of_the_valley', 'sunflower', 'lilac', 'rose_bush', 'peony', 'pink_petals')}


def plant(state):
    key = state.split('[', 1)[0]
    return (key in FLOWERS or key in {
        'minecraft:short_grass', 'minecraft:tall_grass', 'minecraft:fern',
        'minecraft:large_fern', 'minecraft:dead_bush', 'regions_unexplored:grass_sprouts',
        'vinery:red_grape_bush','vinery:white_grape_bush'}
        or key.startswith('farm_and_charm:wild_'))


def rectangle(x1, z1, x2, z2):
    return {(x, z) for x in range(x1, x2+1) for z in range(z1, z2+1)}


def line(a, b):
    count = max(abs(b[0]-a[0]), abs(b[1]-a[1]))
    return [(round(a[0]+(b[0]-a[0])*n/max(count, 1)),
             round(a[1]+(b[1]-a[1])*n/max(count, 1))) for n in range(count+1)]


def reserved(x, z):
    return any(a <= x <= c and b <= z <= d for a, b, c, d in (r['bounds'] for r in RESERVATIONS))


def dry_detour(p, start, end, bounds):
    """A finite saved-terrain detour around retained roots, not a fill/clear order."""
    houses=set().union(*p.buildings.values());known={}
    def floor(pos):
        if pos in known:return known[pos]
        x,z=pos
        if reserved(x,z) or pos in houses:known[pos]=None;return None
        row=p.coast.ground(x,z)
        if row['kind']!='dry':known[pos]=None;return None
        y=row['y']
        for dy in (1,2):
            state=p.at(x,y+dy,z)
            if state.split('[',1)[0] not in {AIR,'minecraft:cave_air','minecraft:void_air'} and not plant(state):
                known[pos]=None;return None
        known[pos]=y;return y
    if floor(start) is None or floor(end) is None:raise UserError('A dry detour endpoint is obstructed')
    queue=[(0,0,start)];distance={start:0};previous={}
    while queue:
        _,cost,pos=heapq.heappop(queue)
        if cost!=distance.get(pos):continue
        if pos==end:
            result=[end]
            while result[-1]!=start:result.append(previous[result[-1]])
            return result[::-1]
        for dx,dz in ((1,0),(-1,0),(0,1),(0,-1)):
            next_pos=pos[0]+dx,pos[1]+dz
            if not bounds[0]<=next_pos[0]<=bounds[2] or not bounds[1]<=next_pos[1]<=bounds[3]:continue
            y=floor(next_pos)
            if y is None or abs(y-floor(pos))>1:continue
            next_cost=cost+1
            if next_cost>=distance.get(next_pos,100000):continue
            distance[next_pos]=next_cost;previous[next_pos]=pos
            heuristic=abs(next_pos[0]-end[0])+abs(next_pos[1]-end[1])
            heapq.heappush(queue,(next_cost+heuristic,next_cost,next_pos))
        if len(distance)>4096:raise UserError('Saved terrain detour exceeds bounded search')
    raise UserError('No connected dry route around the retained tree/ship-shop reservation')


class SavedCoast:
    """Exact columns from the authenticated archive, never interpolation or LODs."""
    def __init__(self, snapshot):
        self.snapshot, self.columns = snapshot, {}

    def ground(self, x, z):
        if (x, z) not in self.columns:
            result = None; trees=[]
            for y in range(112, 55, -1):
                state = self.snapshot.state((x, y, z))
                key = state.split('[', 1)[0]
                if key in {AIR, 'minecraft:cave_air', 'minecraft:void_air'} or plant(state):
                    continue
                # Keep useful existing trees instead of blindly clearing a prism.
                if any(t in key for t in ('leaves', '_log', '_wood')):
                    trees.append({'pos':[x,y,z],'state':state}); continue
                if key == 'minecraft:water' or 'waterlogged=true' in state:
                    result = {'kind': 'water', 'y': y, 'state': state}; break
                if key in NATURAL and y >= 62:
                    result = {'kind': 'dry', 'y': y, 'state': state}; break
                result = {'kind': 'unreviewed', 'y': y, 'state': state}; break
            result=result or {'kind': 'unreviewed', 'y': None, 'state': None}
            result['trees']=trees
            self.columns[x, z] = result
        return self.columns[x, z]

    def require_dry(self, cells, label, floor=None, *, allow_tree_canopy=False):
        rows = []
        for x, z in sorted(cells):
            row = self.ground(x, z)
            if row['kind'] != 'dry' or floor is not None and not 0 <= floor-row['y'] <= 2:
                raise UserError(f'{label} needs actual dry natural ground, without flattening: {(x,z)} {row["kind"]}')
            if row['trees'] and not allow_tree_canopy:
                raise UserError(f'{label} intersects a retained tree; move the authored footprint: {(x,z)}')
            rows.append({'x': x, 'z': z, 'ground_y': row['y'], 'state': row['state']})
        return rows


class SpitPlan:
    def __init__(self, registry, snapshot, backup_sha):
        self.registry, self.snapshot, self.backup_sha = registry, snapshot, backup_sha
        self.coast = SavedCoast(snapshot)
        self.blocks, self.before, self.owners, self.tags = {}, {}, {}, {}
        self.anchors = {}
        self.group = 'lanes'; self.buildings = {}; self.foundations = {}
        self.routes, self.programs, self.details, self.cameras = [], [], [], []

    def state(self, key, **properties):
        native = self.registry['blocks'].get(key)
        if native is None:
            raise UserError('Missing actual native block '+key)
        for name, value in properties.items():
            if name not in native or str(value).lower() not in native[name]:
                raise UserError(f'Unsupported native state {key} {name}={value}')
        return key+('['+','.join(k+'='+str(v).lower() for k,v in sorted(properties.items()))+']' if properties else '')

    def put(self, x, y, z, key, **properties):
        if not (SITE[0] <= x <= SITE[2] and SITE[1] <= z <= SITE[3] and 61 <= y <= 95):
            raise UserError('Authored spit target exceeds its finite envelope: '+str((x,y,z)))
        if reserved(x, z):
            raise UserError('An exact downloaded original owns this reserved footprint: '+str((x,z)))
        # The existing street/harbor stay untouched. The three-step east exit
        # starts at x1284 on independently verified natural ground.
        if x < 1284 and z >= -1267:
            raise UserError('Existing Signal Lane/harbor is an exclusion')
        pos = x, y, z
        if pos not in self.before:
            old = self.snapshot.state(pos)
            if pos in self.snapshot.protected:
                raise UserError('Existing native block entity at new target '+str(pos))
            key_old = old.split('[', 1)[0]
            if key_old not in NATURAL | {AIR, 'minecraft:cave_air', 'minecraft:void_air'} and not plant(old):
                raise UserError('Unreviewed saved object/water at new target '+str(pos)+' '+key_old)
            if key_old in NATURAL and y < self.coast.ground(x,z)['y']-1:
                raise UserError('Do not excavate the spit or river bank')
            self.before[pos] = old
        self.blocks[pos] = self.state(key, **properties); self.owners[pos] = self.group
        if len(self.blocks) > MAX_POSITIONS:
            raise UserError('Split the authored spit into finite proposals')

    def at(self, x, y, z):
        return self.blocks.get((x,y,z), self.snapshot.state((x,y,z)))

    def box(self, x1, y1, z1, x2, y2, z2, key, **properties):
        for x in range(x1, x2+1):
            for y in range(y1, y2+1):
                for z in range(z1, z2+1): self.put(x,y,z,key,**properties)

    def floor(self, cells, y, *, raised=False):
        for x,z in cells:
            if x % 4 == 0:
                key = 'chipped:cross_laced_dark_oak_planks' if z % 8 else 'chipped:crossed_dark_oak_planks'
            elif z % 8 == 0: key = 'chipped:detailed_dark_oak_planks'
            else: key = 'chipped:boxed_dark_oak_planks'
            self.put(x,y,z,key)

    def foundation(self, name, cells, floor):
        self.group = name; self.buildings[name] = set(cells)
        self.foundations[name] = self.coast.require_dry(cells, name, floor)
        for x,z in sorted(cells):
            gy = self.coast.ground(x,z)['y']
            for y in range(gy, floor):
                key = ('minecraft:chiseled_stone_bricks' if x%4==0 and z%4==0 else
                       'minecraft:polished_andesite' if x%4==0 else
                       'minecraft:andesite' if z%4==0 else 'minecraft:stone_bricks')
                self.put(x,y,z,key)
            for y in range(floor+1, 91):
                old = self.snapshot.state((x,y,z))
                if plant(old): self.put(x,y,z,AIR)
        self.floor(cells, floor)

    def post(self, x, y1, z, y2):
        for y in range(y1,y2+1):
            if (y-y1)%4==3: self.put(x,y,z,'minecraft:polished_deepslate')
            else:self.put(x,y,z,'minecraft:stripped_dark_oak_log',axis='y')

    def wall(self, cells, floor, height, plaster):
        edge = {p for p in cells if any((p[0]+dx,p[1]+dz) not in cells for dx,dz in ((1,0),(-1,0),(0,1),(0,-1)))}
        for x,z in sorted(edge):
            along_x=(x-1,z) in edge and (x+1,z) in edge
            along_z=(x,z-1) in edge and (x,z+1) in edge
            # Posts follow each facade's own run; a constant world X divisible
            # by four must not turn an entire side into an unbroken log sheet.
            post_at=(x%4==0 if along_x else z%4==0) or not (along_x or along_z)
            for dy in range(1,height+1):
                if post_at:
                    if dy%4==0:self.put(x,floor+dy,z,'minecraft:polished_deepslate')
                    else:self.put(x,floor+dy,z,'minecraft:stripped_dark_oak_log',axis='y')
                elif dy%4==0:
                    key = 'chipped:cross_laced_dark_oak_planks' if (x-1,z) in cells and (x+1,z) in cells else 'chipped:detailed_dark_oak_planks'
                    self.put(x,floor+dy,z,key)
                else:self.put(x,floor+dy,z,plaster)

    def door(self, x, floor, z, facing='south'):
        for dy,half in [(1,'lower'),(2,'upper')]:
            self.put(x,floor+dy,z,'minecraft:dark_oak_door',half=half,facing=facing,hinge='left',open='false',powered='false')

    def window(self, x, y, z, facing, height=3):
        for n in range(height):
            self.put(x,y+n,z,'mcwwindows:blackstone_brick_gothic',facing=facing,open='false',
                     part='bottom' if n==0 else 'top' if n==height-1 else 'middle')

    def table(self, x, y, z, facing='north', color='green'):
        self.put(x,y,z,'handcrafted:dark_oak_table',color='none',shape='single',waterlogged='false')
        dx,dz = {'north':(0,1),'south':(0,-1),'east':(-1,0),'west':(1,0)}[facing]
        self.put(x+dx,y,z+dz,'handcrafted:dark_oak_chair',facing=facing,color=color,waterlogged='false')
        self.put(x,y+1,z,'supplementaries:goblet',light_level='0',waterlogged='false')

    def shelf(self, x,y,z,facing='east'):
        self.put(x,y,z,'handcrafted:dark_oak_shelf',facing=facing,shape='single',type='3')

    def store(self, x,y,z,title,items=()):
        self.put(x,y,z,'minecraft:barrel',facing='up',open='false')
        values=[]
        for slot,(item,count) in enumerate(items):
            if item not in self.registry.get('items',{}):raise UserError('Unknown native stock item '+item)
            if not 1<=count<=16 or slot>8:raise UserError('Small showcase stock only')
            values.append({'Slot':slot,'id':item,'count':count})
        self.tags[x,y,z]={'Items':values,'CustomName':json.dumps({'text':title})}

    def sign(self,x,y,z,lines,facing='south'):
        self.put(x,y,z,'minecraft:dark_oak_wall_sign',facing=facing,waterlogged='false')
        text=[json.dumps({'text':s}) for s in (*lines,'','','','')[:4]]
        self.tags[x,y,z]={'front_text':{'messages':text,'color':'gold','has_glowing_text':False},'is_waxed':True}

    def route(self,name,points):
        for x,floor,z in points:
            for dy in (1,2):
                state=self.at(x,floor+dy,z).split('[',1)[0]
                if state not in {AIR,'minecraft:cave_air','minecraft:void_air','minecraft:dark_oak_door'}:
                    raise UserError('Authored route blocked: '+name+' '+str((x,floor+dy,z))+' '+state)
        self.routes.append({'name':name,'floor_cells':[list(p) for p in points],
                            'proof':'Planned two-high body clearance only; native walking pending'})

    def program(self,name,at,features):
        self.programs.append({'name':name,'at':list(at),'features':features,'status':'AUTHORED; native interaction/visual acceptance pending'})


def gothic_tavern(p):
    """The Drowned Rose: authored nave, ribs, galley bay and asymmetric gallery."""
    floor=64
    cells=rectangle(1291,-1290,1312,-1269)|rectangle(1288,-1286,1292,-1278)
    cells-={(1291,-1269),(1312,-1269),(1291,-1290),(1312,-1290)}
    p.foundation('drowned-rose',cells,floor)
    p.wall(cells,floor,9,'minecraft:gray_terracotta')
    # Long, pointed sea-green roof; short plated seams read as structural bays.
    for x in range(1290,1314):
        height=min(x-1290,1313-x)
        for z in range(-1291,-1267):
            if z%4==0:
                key='minecraft:oxidized_cut_copper_stairs'
            else:key='minecraft:dark_prismarine_stairs'
            p.put(x,74+height,z,key,facing='east' if x<=1301 else 'west',half='bottom',shape='straight',waterlogged='false')
    # Filled gables have three-wide carved panels and copper-backed ribs.
    for z in (-1290,-1269):
        for x in range(1291,1313):
            roof=74+min(x-1290,1313-x)
            for y in range(74,roof):
                key='chipped:detailed_dark_oak_planks' if (x-1290)%4==0 else 'minecraft:green_terracotta'
                if (y-74)%4==3:key='minecraft:polished_deepslate' if x%4==0 else 'chipped:cross_laced_dark_oak_planks'
                p.put(x,y,z,key)
    for x in (1291,1312):
        for z in range(-1289,-1269):
            p.put(x,74,z,'minecraft:polished_deepslate' if z%4==0 else 'chipped:detailed_dark_oak_planks')
    # Four visibly curved ship-derived transverse rib frames; no giant flat hall.
    profile=((1292,69),(1293,70),(1294,71),(1295,72),(1296,73),(1297,74),(1298,75),(1299,76),
             (1300,77),(1301,78),(1302,78),(1303,77),(1304,76),(1305,75),(1306,74),(1307,73),(1308,72),(1309,71),(1310,70),(1311,69))
    for z in (-1287,-1282,-1277,-1272):
        p.post(1292,65,z,69);p.post(1311,65,z,69)
        for x,y in profile:
            p.put(x,y,z,'minecraft:dark_oak_stairs',facing='east' if x<1302 else 'west',half='top',shape='straight',waterlogged='false')
            if x in (1295,1308):p.put(x,y-1,z,'minecraft:dark_oak_fence')
        # Wall sconces attach to real solid posts and cast contrasting pools.
        for x,facing in ((1293,'east'),(1310,'west')):
            p.put(x,68,z,'supplementaries:sconce_wall_soul',facing=facing,lit='true',waterlogged='false')
    # Fancy tall pointed windows, observed from nave and sea-facing bays.
    for z in (-1288,-1284,-1280,-1276,-1272):
        p.window(1312,66,z,'east',4)
    for z in (-1288,-1275,-1271):p.window(1291,66,z,'west',4)
    for x in (1295,1299,1304,1308):p.window(x,68,-1290,'north',4)
    p.door(1301,floor,-1269)
    p.door(1302,floor,-1269)
    p.sign(1301,68,-1268,('THE DROWNED ROSE','Ale / charts / music','Gallery and reading nook','Welcome, wayfarer'))
    # Side galley passage and low, broken roof join the smaller bay to the nave.
    for z in range(-1284,-1279):
        for y in range(65,69):p.put(1291,y,z,AIR)
    for x in range(1287,1292):
        for z in range(-1287,-1276):
            p.put(x,71+(x-1287)//2,z,'minecraft:dark_oak_stairs' if z%4 else 'minecraft:oxidized_cut_copper_stairs',facing='east',half='bottom',shape='straight',waterlogged='false')
    # Asymmetric mezzanine with a real five-rise stair and open central void.
    gallery=rectangle(1308,-1288,1310,-1276)|rectangle(1293,-1288,1296,-1280)|rectangle(1297,-1288,1307,-1286)
    p.floor(gallery,69)
    for x,z in gallery:
        if (x-1,z) not in gallery and x>1300 and z%4:
            p.put(x,70,z,'minecraft:iron_bars',east='false',west='false',north='true',south='true',waterlogged='false')
    for n in range(5):
        for x in (1308,1309):p.put(x,65+n,-1271-n,'minecraft:spruce_stairs',facing='north',half='bottom',shape='straight',waterlogged='false')
    # Reversed, stationary capstan chandelier. Native cog models are decor here.
    p.put(1302,74,-1279,'create:large_cogwheel',axis='y',waterlogged='false')
    p.put(1302,73,-1279,'minecraft:barrel',facing='down',open='false')
    for y in range(75,80):p.put(1302,y,-1279,'minecraft:chain',axis='y',waterlogged='false')
    p.put(1302,80,-1279,'chipped:cross_laced_dark_oak_planks')
    for y in range(81,85):p.put(1302,y,-1279,'minecraft:chain',axis='y',waterlogged='false')
    for dx,dz in ((-2,0),(2,0),(0,-2),(0,2)):
        p.put(1302+dx,74,-1279+dz,'minecraft:dark_oak_trapdoor',facing='north',half='top',open='false',powered='false',waterlogged='false')
        p.put(1302+dx,73,-1279+dz,'minecraft:lantern',hanging='true',waterlogged='false')
    # Barrel-backed irregular bar, grouped merchandise, serving aisle and galley.
    for z in range(-1281,-1273):
        p.put(1295,65,z,'minecraft:barrel',facing='east',open='false')
        p.put(1295,66,z,'handcrafted:dark_oak_counter',counter='dark_oak_planks',facing='east',type='1')
        if z%2:p.put(1295,67,z,'supplementaries:goblet',light_level='0',waterlogged='false')
    for z in (-1284,-1282,-1280,-1278):p.shelf(1288,66,z,'east')
    p.put(1289,65,-1284,'farmersdelight:stove',facing='south',lit='false')
    p.put(1289,66,-1284,'farmersdelight:cooking_pot',facing='south',support='none',waterlogged='false')
    p.store(1289,65,-1280,'The Rose pantry',(('minecraft:bread',8),('minecraft:cooked_cod',6),('minecraft:apple',8)))
    p.put(1289,65,-1282,'minecraft:water_cauldron',level='3')
    # Two-person conversation islands, games and a separate music stage.
    for x,z,facing in ((1298,-1273,'north'),(1305,-1274,'north'),(1305,-1281,'west'),(1298,-1285,'south')):
        p.table(x,65,z,facing)
        p.put(x-1,65,z,'handcrafted:dark_oak_side_table',facing='east',color='none',waterlogged='false')
    stage=rectangle(1299,-1288,1305,-1286)
    for x,z in stage:p.put(x,65,z,'chipped:cross_laced_dark_oak_planks' if x%4 else 'chipped:detailed_dark_oak_planks')
    p.put(1304,66,-1287,'xercamusic:piano',facing='south')
    p.put(1300,66,-1287,'handcrafted:dark_oak_chair',facing='south',color='red',waterlogged='false')
    p.put(1302,66,-1289,'minecraft:lectern',facing='south',has_book='false',powered='false')
    # Reading gallery, navigator's nook and view across the open capstan hall.
    p.put(1293,70,-1284,'handcrafted:dark_oak_couch',facing='east',color='green',shape='single',waterlogged='false')
    p.put(1293,70,-1282,'handcrafted:dark_oak_couch',facing='east',color='green',shape='single',waterlogged='false')
    for z in (-1287,-1285,-1283):p.put(1293,71,z,'minecraft:bookshelf')
    p.put(1295,70,-1286,'handcrafted:dark_oak_side_table',facing='south',color='none',waterlogged='false')
    p.put(1295,71,-1286,'supplementaries:globe_sepia',facing='south',powered='false',rotation='0',waterlogged='false')
    p.store(1295,70,-1281,'Charts and reading copies',(('minecraft:book',6),('minecraft:paper',8),('minecraft:compass',1)))
    p.table(1309,70,-1281,'north','red')
    # Furniture-associated rug strips: narrow planks and carpet seams, not a blank floor.
    for z in range(-1283,-1270):
        for x in (1301,1302):
            if p.at(x,65,z).split('[',1)[0] in {AIR,'minecraft:cave_air'}:
                p.put(x,65,z,'minecraft:red_carpet' if z%7 else 'minecraft:brown_carpet')
    # Main aisles are sampled beside the shallow rugs; both exits remain usable.
    p.put(1302,65,-1270,AIR)
    p.route('Drowned Rose central aisle',[(1303,64,z) for z in range(-1284,-1269)]+[(1302,64,-1270),(1302,64,-1269)])
    p.route('Drowned Rose bar service',[(1294,64,z) for z in range(-1284,-1272)])
    p.route('Drowned Rose galley',[ (x,64,-1283) for x in range(1289,1295)])
    p.route('Drowned Rose gallery',[(1309,69,z) for z in range(-1285,-1282)])
    p.route('Drowned Rose gallery stairs',[(1309,65+n,-1271-n) for n in range(5)])
    p.route('Drowned Rose north gallery',[(x,69,-1286) for x in range(1296,1310)])
    p.program('The Drowned Rose',(1302,65,-1279),[
        'Double-height pointed ship-rib nave, barrel-backed curved-service bar and real galley',
        'Reversed capstan chandelier, tall Macaw gothic windows, green sconces and warm lanterns',
        'Five-rise gallery stair, reading nook, navigator table, conversation islands and real piano stage',
        'Original authored Minecraft geometry informed by all three credited artists; no copied assets'])
    p.cameras += [
        {'name':'drowned-rose-entrance','feet':[1301.5,65,-1266.5],'look_at':[1302,70,-1280]},
        {'name':'drowned-rose-bar','feet':[1303.5,65,-1271.5],'look_at':[1295,67,-1278]},
        {'name':'drowned-rose-capstan','feet':[1303.5,65,-1283.5],'look_at':[1302,74,-1279]},
        {'name':'drowned-rose-gallery','feet':[1307.5,70,-1287.5],'look_at':[1302,68,-1277]},
    ]


def net_menders(p):
    cells=rectangle(1277,-1288,1284,-1278)-{(1277,-1288),(1277,-1278)}
    p.foundation('ninth-knot',cells,64);p.wall(cells,64,6,'minecraft:white_terracotta')
    for x in range(1276,1286):
        for z in range(-1289,-1276):
            y=71+min(3,(x-1276)//2)
            p.put(x,y,z,'minecraft:spruce_stairs' if z%4 else 'minecraft:dark_oak_stairs',facing='east',half='bottom',shape='straight',waterlogged='false')
    edge={pos for pos in cells if any((pos[0]+dx,pos[1]+dz) not in cells for dx,dz in ((1,0),(-1,0),(0,1),(0,-1)))}
    for x,z in edge:
        along_x=(x-1,z) in edge and (x+1,z) in edge
        along_z=(x,z-1) in edge and (x,z+1) in edge
        for y in range(71,71+min(3,(x-1276)//2)):
            post_at=(x%4==0 if along_x else z%4==0) or not (along_x or along_z)
            p.put(x,y,z,'minecraft:stripped_dark_oak_log' if post_at else 'minecraft:white_terracotta',**({'axis':'y'} if post_at else {}))
    p.door(1284,64,-1283,'east')
    p.sign(1285,68,-1281,('THE NINTH KNOT','Net / sail repair','Tools and canvas','Please mind the needles'),'east')
    p.window(1277,66,-1284,'west',3);p.window(1281,66,-1288,'north',3)
    for z in (-1286,-1284,-1282):p.put(1279,65,z,'minecraft:loom',facing='east')
    p.put(1281,65,-1286,'handcrafted:dark_oak_table',color='none',shape='single',waterlogged='false')
    p.put(1281,66,-1286,'minecraft:white_carpet')
    p.store(1282,65,-1287,'Net-maker supplies',(('minecraft:string',12),('minecraft:white_wool',8),('minecraft:shears',1)))
    p.shelf(1278,66,-1280,'east')
    p.put(1280,65,-1279,'handcrafted:dark_oak_bench',facing='north',shape='single',color='none',waterlogged='false')
    p.put(1281,68,-1287,'minecraft:lantern',hanging='false',waterlogged='false')
    p.route('Ninth Knot entrance',[(x,64,-1283) for x in range(1280,1285)])
    p.program('The Ninth Knot',(1281,65,-1283),['Net-repair looms, canvas table, stocked sewing tools, window bench and trade shelves'])


def repair_yard(p):
    # The real willow is retained: a tree-shaded hand-work court, not a house
    # over its roots or a generic platform that fills this small shore.
    p.group='east-repair'
    work={(1339,-1330),(1341,-1330),(1343,-1329),(1340,-1323),(1342,-1323)}
    p.coast.require_dry(work,'Willow repair working spots',allow_tree_canopy=True)
    p.put(1339,64,-1330,'minecraft:grindstone',face='floor',facing='south')
    p.put(1341,64,-1330,'minecraft:smithing_table')
    p.store(1343,64,-1329,'Shipwright hand tools',(('minecraft:iron_axe',1),('minecraft:iron_ingot',8),('minecraft:stick',12)))
    p.put(1340,64,-1323,'handcrafted:dark_oak_bench',facing='north',shape='single',color='none',waterlogged='false')
    p.put(1342,64,-1323,'handcrafted:dark_oak_counter',counter='andesite',facing='north',type='1')
    # A little fair-ended workpiece on trestles rather than another big shed.
    for z in range(-1329,-1323):
        for x in (1338,1341):
            if z in (-1328,-1325):p.put(x,64,z,'minecraft:spruce_fence')
        for x in range(1338+(z in (-1329,-1324)),1342-(z in (-1329,-1324))):
            p.put(x,65,z,'minecraft:spruce_slab',type='bottom',waterlogged='false')
    p.program('The Willow Repair Court',(1340,64,-1326),['Retained native willow, sharpening stone, stocked hardware, small fair-ended boat workpiece on real trestles and a shore bench'])


def pilot_tip(p):
    cells=rectangle(1308,-1366,1314,-1360)-{(1308,-1366),(1314,-1366)}
    p.foundation('pilot-tip',cells,64);p.wall(cells,64,5,'minecraft:light_gray_terracotta')
    # The western willow canopy is kept; its side has a flush eave rather than
    # cutting branches to obtain a symmetric one-block roof overhang.
    for x in range(1308,1316):
        for z in range(-1367,-1358):
            p.put(x,70+min(x-1308,1315-x),z,'minecraft:dark_prismarine_stairs' if z%4 else 'minecraft:oxidized_cut_copper_stairs',facing='east' if x<1312 else 'west',half='bottom',shape='straight',waterlogged='false')
    for z in (-1366,-1360):
        for x in range(1309,1314):
            for y in range(70,70+min(x-1308,1315-x)):
                p.put(x,y,z,'minecraft:light_gray_terracotta' if x%4 else 'chipped:cross_laced_dark_oak_planks')
    p.door(1311,64,-1360,'south')
    p.sign(1312,68,-1359,('THE LAST SOUNDING','Pilot charts / shelter','River to the west','Open sea beyond'))
    p.window(1311,66,-1366,'north',3);p.window(1314,66,-1363,'east',3)
    p.put(1309,65,-1364,'minecraft:cartography_table')
    p.put(1309,66,-1364,'supplementaries:globe_sepia',facing='east',rotation='0',powered='false',waterlogged='false')
    p.store(1313,65,-1365,'Pilot sounding kit',(('minecraft:compass',1),('minecraft:paper',8),('minecraft:spyglass',1)))
    p.put(1313,65,-1362,'handcrafted:dark_oak_bench',facing='west',shape='single',color='none',waterlogged='false')
    p.put(1310,68,-1364,'minecraft:lantern',hanging='true',waterlogged='false')
    p.route('Pilot shelter',[(1311,64,z) for z in range(-1364,-1359)])
    p.program('The Last Sounding',(1311,65,-1363),['Small actual-tip pilot shelter, chart worktop, optical/sounding kit and sheltered sea-facing bench'])
    p.cameras += [{'name':'pilot-tip','feet':[1311.5,65,-1357.5],'look_at':[1311,68,-1365]}]


def landscape(p):
    p.group='lanes'
    # Real three-step descent from the saved Signal Lane east exit, not a
    # bridge across the estuary. Existing x1283 stonework is only an anchor.
    for x,y in ((1284,66),(1285,65),(1286,64)):
        for z in range(-1241,-1238):
            p.coast.require_dry({(x,z)},'Signal Lane east stair')
            for fill in range(64,y):p.put(x,fill,z,'minecraft:stone_bricks' if z%4 else 'minecraft:andesite')
            p.put(x,y,z,'minecraft:stone_brick_stairs',facing='west',half='bottom',shape='straight',waterlogged='false')
            for dy in (1,2):
                if plant(p.snapshot.state((x,y+dy,z))):p.put(x,y+dy,z,AIR)
    spine=[(1287,-1240),(1289,-1255),(1288,-1270),(1286,-1275),(1286,-1288),(1291,-1293),
           (1311,-1294),(1311,-1312),(1311,-1334),(1311,-1343),(1311,-1358)]
    paths=[]
    for a,b in zip(spine,spine[1:]):paths+=line(a,b)
    paths+=line((1286,-1283),(1285,-1283))
    paths+=line((1288,-1267),(1302,-1267))
    # Go around the SOUTH of the exact shop reservation, never through a
    # silently skipped slot. The willow and its exposed roots stay eastward.
    paths+=dry_detour(p,(1311,-1314),(1342,-1326),(1310,-1340,1352,-1308))
    walks={}
    house_cells=set().union(*p.buildings.values())
    for x,z in paths:
        if reserved(x,z):raise UserError('A path centre crosses an exact original reservation')
        if (x,z) in house_cells:raise UserError('An authored house blocks the main path centre')
        for dx,dz in ((0,0),(-1,0),(1,0),(0,-1),(0,1)):
            px,pz=x+dx,z+dz;pos=px,pz
            if reserved(*pos):continue
            row=p.coast.ground(*pos)
            if row['kind']!='dry':
                if dx==dz==0:raise UserError('The authored backbone leaves actual dry land: '+str(pos))
                continue
            if pos in house_cells:continue
            gy=row['y']
            # A low existing willow root is crossed as a retained natural step,
            # not cut or replaced with paving. Its exact unchanged state becomes
            # a separate native verification-only anchor.
            root=p.snapshot.state((px,gy+1,pz))
            if root.split('[',1)[0].endswith('_log') and all(
                    p.at(px,gy+dy,pz).split('[',1)[0] in {AIR,'minecraft:cave_air','minecraft:void_air'}
                    or plant(p.at(px,gy+dy,pz)) for dy in (2,3)):
                gy+=1;p.anchors[px,gy,pz]=root
            blocked=any(p.at(px,gy+dy,pz).split('[',1)[0] not in {AIR,'minecraft:cave_air','minecraft:void_air'}
                        and not plant(p.at(px,gy+dy,pz)) for dy in (1,2))
            if blocked:
                if dx==dz==0:raise UserError('Retained object blocks the actual path centre: '+str(pos))
                continue
            key=('minecraft:chiseled_stone_bricks' if px%8==0 else 'minecraft:cobblestone') if pz%7==0 else 'minecraft:andesite' if px%4==0 else 'minecraft:stone_bricks'
            if (px,gy,pz) not in p.anchors:p.put(px,gy,pz,key)
            walks[pos]=gy
            for dy in (1,2):
                if plant(p.snapshot.state((px,gy+dy,pz))):p.put(px,gy+dy,pz,AIR)
    p.walks=walks
    # Threshold steps for houses; no common broad platform fills the peninsula.
    for x,z,facing in ((1301,-1268,'north'),(1302,-1268,'north'),(1285,-1283,'west'),(1311,-1359,'north')):
        p.coast.require_dry({(x,z)},'Door threshold')
        p.put(x,64,z,'minecraft:stone_brick_stairs',facing=facing,half='bottom',shape='straight',waterlogged='false')
        walks[x,z]=64
    # Irregular small court furniture and trade-specific working clusters.
    for x,z in ((1292,-1293),(1297,-1293),(1304,-1293),(1316,-1307),(1338,-1332),(1316,-1353)):
        if reserved(x,z):continue
        if (x,z) in walks or (x+1,z) in walks:continue
        row=p.coast.ground(x,z)
        if row['kind']!='dry' or row['trees']:continue
        y=row['y']+1
        p.put(x,y,z,'minecraft:barrel',facing='up',open='false')
        p.put(x+1,y,z,'minecraft:spruce_trapdoor',facing='north',half='top',open='false',powered='false',waterlogged='false')
        p.details.append({'name':'Cargo/working station','at':[x,y,z],'purpose':'Barrel and supported work surface off the walking line'})
    # Modded seating, native ground planting and light pools make quiet places
    # between frontages. No mob, fake rope item or continuously running machine.
    for x,z,facing in ((1286,-1275,'east'),(1316,-1292,'west'),(1337,-1330,'east'),(1316,-1351,'west')):
        if reserved(x,z):continue
        if (x,z) in walks:continue
        row=p.coast.ground(x,z)
        if row['kind']!='dry' or row['trees']:continue
        y=row['y']+1
        p.put(x,y,z,'handcrafted:dark_oak_bench',facing=facing,shape='single',color='none',waterlogged='false')
        for px,pz in ((x,z+2),(x,z-2)):
            if reserved(px,pz) or p.coast.ground(px,pz)['kind']!='dry':continue
            p.put(px,y,pz,'minecraft:flower_pot');p.put(px,y,pz,'minecraft:potted_fern')
    for x,z in ((1287,-1259),(1286,-1290),(1313,-1293),(1313,-1315),(1313,-1338),(1310,-1354),(1338,-1329)):
        if reserved(x,z):continue
        if (x,z) in walks:continue
        row=p.coast.ground(x,z)
        if row['kind']!='dry' or row['trees']:continue
        y=row['y']+1
        p.put(x,y,z,'minecraft:cobblestone_wall');p.put(x,y+1,z,'minecraft:dark_oak_fence')
        p.put(x,y+2,z,'minecraft:lantern',hanging='false',waterlogged='false')
    p.route('Dry connected spit walk',[(x,y,z) for (x,z),y in sorted(walks.items())])
    p.route('Signal Lane descent',[(1284,66,z) for z in range(-1241,-1238)]+
            [(1285,65,z) for z in range(-1241,-1238)]+[(1286,64,z) for z in range(-1241,-1238)])
    p.cameras += [
        {'name':'spit-court','feet':[1311.5,65,-1293.5],'look_at':[1301,72,-1277]},
        {'name':'spit-northern-lane','feet':[1311.5,64,-1339.5],'look_at':[1311,68,-1358]},
        {'name':'spit-coast-overview','feet':[1278,88,-1328],'look_at':[1308,68,-1318]},
    ]


def validate(p):
    # Recheck AFTER all furniture/planting/lights. Earlier route observations
    # cannot authorize a later decoration that silently closes an alley.
    for route in p.routes:
        for x,y,z in route['floor_cells']:
            floor=p.at(x,y,z).split('[',1)[0]
            if floor in {AIR,'minecraft:cave_air','minecraft:void_air','minecraft:water'}:
                raise UserError('An authored route lacks actual floor support: '+route['name']+' '+str((x,y,z)))
            for dy in (1,2):
                if p.at(x,y+dy,z).split('[',1)[0] not in {AIR,'minecraft:cave_air','minecraft:void_air','minecraft:dark_oak_door'}:
                    raise UserError('Final decoration obstructs '+route['name']+' '+str((x,y+dy,z)))
    # The whole outdoor spine, all three real descent steps and each threshold
    # must form one terrain-following component. Reserved originals are holes.
    floors=dict(p.walks)
    for x,y in ((1284,66),(1285,65),(1286,64)):
        for z in range(-1241,-1238):floors[x,z]=y
    start=(1284,-1240);seen={start};pending=deque([start])
    while pending:
        x,z=pending.popleft()
        for dx,dz in ((1,0),(-1,0),(0,1),(0,-1)):
            pos=x+dx,z+dz
            if pos in floors and pos not in seen and abs(floors[pos]-floors[x,z])<=1:
                seen.add(pos);pending.append(pos)
    if seen!=set(floors):raise UserError('The saved-terrain street proposal has a disconnected or over-steep island')
    proofs=[]
    for name in sorted(p.buildings):
        own={pos:state for pos,state in p.blocks.items() if p.owners[pos]==name}
        proofs.append(require_material_rule(own,name))
    outdoor=require_outdoor_rule(p.blocks,'Complete pirate spit including all authored outdoor surfaces')
    if set(p.tags)-set(p.blocks) or len(p.tags)>64:
        raise UserError('Finite owned block-entity tags required')
    for pos in p.blocks:
        if reserved(pos[0],pos[2]):raise UserError('Exact imported building reservation was overwritten')
    # Every route has dry native support; air clears alone are never a land claim.
    for route in p.routes:
        if not route['floor_cells']:raise UserError('A route has no authored positions')
    return {'buildings':proofs,'outdoors':outdoor,'tagged_block_entities':len(p.tags),
            'outdoor_connected_floor_cells':len(floors),'path_height_step_bound':1,
            'entities':0,'spawn_commands':0,'actual_minecraft_visual_acceptance':'PENDING'}


def tag_snbt(value, path=()):
    """Literal native SNBT, including ContainerHelper's byte-typed Items.Slot.

    Slot must compare equal to the saved byte tag, not merely convert via getByte.
    Modern item count remains an int. All strings retain their exact JSON text.
    """
    if isinstance(value,dict):
        return '{'+','.join(json.dumps(key,ensure_ascii=False)+':'+tag_snbt(item,path+(key,))
                            for key,item in value.items())+'}'
    if isinstance(value,list):
        return '['+','.join(tag_snbt(item,path+(index,)) for index,item in enumerate(value))+']'
    if len(path)>=3 and path[-3]=='Items' and type(path[-2]) is int and path[-1]=='Slot':
        if type(value) is not int or not 0<=value<=127:raise UserError('Native inventory Slot must be a bounded nonnegative byte')
        return str(value)+'b'
    if value is None or not isinstance(value,(str,bool,int,float)):
        raise UserError('Only literal native tag values are supported')
    return json.dumps(value,ensure_ascii=False,allow_nan=False,separators=(',',':'))


def payload(p, states, name, *, tags=False):
    palette=sorted(set(states.values()));lookup={s:n for n,s in enumerate(palette)}
    result={'format':'awft-native-settlement:1','name':name,'created':utcnow(),
            'seed':p.registry['seed'],'world_path':p.registry['world_path'],'backup_sha256':p.backup_sha,
            'bounds':[min(a[0] for a in states),min(a[2] for a in states),max(a[0] for a in states),max(a[2] for a in states)],
            'palette':palette,'blocks':[[*pos,lookup[s]] for pos,s in sorted(states.items())],
            'block_entities':[{'pos':list(pos),'nbt':tag_snbt(tag)}
                              for pos,tag in sorted(p.tags.items()) if tags and pos in states],
            'commands':[],'landmarks':[]}
    return (json.dumps(result,separators=(',',':'),ensure_ascii=False)+'\n').encode()


def prepare(home, checkpoint_id, checkpoint_sha, output=None):
    home=Path(home).resolve();layout=Layout(home)
    if not home.is_relative_to(Path(r'D:\A World for Two\staging\world-tests')):
        raise UserError('Only the separate owned artistic staging home is admitted')
    owner=read_json(home/'dashboard/artistic-owner.json',{});receipt=read_json(home/'dashboard/settlement/backup-receipt.json',{})
    if owner.get('format')!='awft-artistic-stage:1' or Path(owner.get('home','')).resolve()!=home:
        raise UserError('Explicit artistic ownership is required')
    if receipt.get('verified') is not True or (receipt.get('id'),receipt.get('sha256'))!=(checkpoint_id,checkpoint_sha):
        raise UserError('Current stopped checkpoint differs; do not rebind a proposal silently')
    backups=Backups(layout,None,None);archive=backups.path(checkpoint_id)
    if digest(archive)!=checkpoint_sha:raise UserError('Stopped checkpoint archive bytes differ')
    manifest,total=backups.verify_archive(archive)
    if total>512*1024**2 or len(manifest['files'])>4096:raise UserError('Checkpoint exceeds bounded read admission')
    registry=read_json(home/'dashboard/settlement/registry.json')
    snapshot=BackupWorld(home,receipt,registry)
    try:
        p=SpitPlan(registry,snapshot,checkpoint_sha)
        reservation_proofs=[{'id':row['id'],'dry_columns':p.coast.require_dry(rectangle(*row['bounds']),row['id'],64,allow_tree_canopy=True),
                             'tree_conflicts':[v for x,z in rectangle(*row['bounds']) for v in p.coast.ground(x,z)['trees']],
                             'gate':'Reserved soil is dry; original conversion must review trees and exact physical footprint before any placement'} for row in RESERVATIONS]
        gothic_tavern(p);net_menders(p);repair_yard(p);pilot_tip(p);landscape(p)
        proof=validate(p)
        outputs={}
        for group in sorted(set(p.owners.values())):
            after={pos:s for pos,s in p.blocks.items() if p.owners[pos]==group}
            before={pos:p.before[pos] for pos in after}
            outputs[group+'.json']=payload(p,after,group,tags=True)
            outputs[group+'-before.json']=payload(p,before,'Saved exact preimage — '+group)
        if p.anchors:outputs['route-anchors-VERIFY-ONLY.json']=payload(p,p.anchors,'Retained natural route supports — VERIFY ONLY')
        record={'format':'awft-artistic-pirate-spit:1','at':utcnow(),'status':'STAGED ONLY; no native/world operation',
                'checkpoint_id':checkpoint_id,'checkpoint_sha256':checkpoint_sha,
                'sources':snapshot.sources,'registry_sha256':digest(home/'dashboard/settlement/registry.json'),
                'author_source_sha256':digest(Path(__file__)),'bounds':list(SITE),'positions':len(p.blocks),
                'reservations':list(RESERVATIONS),'reservation_admission':reservation_proofs,
                'programs':p.programs,'routes':p.routes,'details':p.details,'cameras':p.cameras,'proof':proof,
                'verification_only_files':['route-anchors-VERIFY-ONLY.json'] if p.anchors else [],
                'foundations':p.foundations,'references':[{'url':u,'observed_use':v} for u,v in REFERENCES],
                'files':{name:{'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)} for name,raw in outputs.items()},
                'native_sequence':'Independently verify each exact before plan, place its paired after plan, verify settled target, then actual client walking and images. No replay or admission bypass.',
                'life':'No entities/spawns. Add life only after all construction and visual corrections.'}
        outputs['manifest.json']=(json.dumps(record,indent=2,ensure_ascii=False)+'\n').encode()
        if sum(map(len,outputs.values()))>MAX_OUTPUT:raise UserError('The complete private bundle exceeds32MiB')
        output=Path(output).resolve() if output else home/'staging'/('artistic-pirate-spit-'+str(time.time_ns()))
        if not output.is_relative_to(home/'staging') or output.exists():raise UserError('A new private staging output folder is required')
        guard(16*1024**2,MAX_OUTPUT)
        output.mkdir(parents=True,exist_ok=False)
        for name,raw in outputs.items():
            with (output/name).open('xb') as stream:stream.write(raw)
        return {'directory':str(output),'manifest_sha256':digest(output/'manifest.json'),'positions':len(p.blocks),
                'files':record['files'],'status':record['status']}
    finally:snapshot.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--home',type=Path,required=True);parser.add_argument('--checkpoint-id',required=True)
    parser.add_argument('--checkpoint-sha',required=True);parser.add_argument('--output',type=Path)
    args=parser.parse_args();print(json.dumps(prepare(args.home,args.checkpoint_id,args.checkpoint_sha,args.output),indent=2))
