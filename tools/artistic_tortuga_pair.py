"""Two original, furnished Tortuga trades facing one crooked headland lane.

Pure source geometry and exact stopped-save preimages only. No demolition,
native operation, inventory transfer, resident assignment or runtime changes.
"""
from __future__ import annotations

import argparse
from collections import Counter, deque
import hashlib
import json
import math
from pathlib import Path
import time

from control_room.common import UserError, digest, read_json
from tools.artistic_captains_hall import native_payload, rectangle, boundary, VEC
from tools.artistic_fisherman_interior import Byte
from tools.artistic_maritime_depth import admit_owner, key
from tools.artistic_materials import require_material_rule
from tools.artistic_spawn_plaza import state
from tools.artistic_west_r2_frontage import canonical_joins
from tools.playtest import guard
from tools.settlement_attractions import BackupWorld


MIB = 1024**2
AIR = 'minecraft:air'
VOID = {AIR, 'minecraft:cave_air', 'minecraft:void_air'}
SOFT = {'minecraft:short_grass', 'minecraft:tall_grass', 'regions_unexplored:grass_sprouts', 'supplementaries:barnacles'}
GROUND = {'minecraft:gravel', 'minecraft:stone', 'minecraft:andesite', 'minecraft:dirt', 'minecraft:grass_block'}
MAX_OUTPUT = 16*MIB
REFERENCES = (
    ('Captain’s Rest all solid/AIR/routes', 'staging/artistic-captains-rest-1793170982583234800/future-solid-AIR-route-reservation-ONLY.json', 'b4716f849de37fa9b887b5531ff93d53ce3300814f885cc93da11c007a95da54'),
    ('Accepted W3 full', 'staging/west-r2-three-frontage-preview-1793168582590227200/three-frontages-PROPOSAL.json', '336363fd0adeb0043117ce4e3ed68b32d3e7c2305d895daa68a9a027124ff5c9'),
    ('Salt & Petal future hooked florist/home', 'staging/salt-petal-florist-SOURCE-ONLY-1793173324279127400/source-only.json', 'c9c60ac6e4eb60605dbbfa4917b17c8cda66ff1f1a9d7ebf784403a27af305cc'),
    ('Western v2 actual flight/frames/stations', 'staging/zipline-west-v2-source-1793152099836099800/all-v2-RESERVATION-ONLY.json', '92ea594836795a61e00f5cc32290d49d1d47b9fd6eb55aeefc99d527acf8854d'),
)
FOREST = ('staging/forest47-frozen-custody-20261028T0643Z/future-native-fields-RESERVATION-ONLY.json', '8f8aa4cdf7c45618761c6a524858e0f8419e9af6bf4352c26c39c61eca538376')


class TradeHouse:
    def __init__(self, registry, name, origin):
        self.registry, self.name, self.origin = registry, name, tuple(origin)
        self.blocks, self.tags, self.roles = {}, {}, {}
        self.footprint, self.body = set(), set()
        self.routes, self.stairs, self.entries, self.rooms = [], [], [], []
        self.supports, self.lights, self.stations, self.details = [], [], [], []
        self.join_derivations = []

    def put(self, x, y, z, material, *, role='authored architecture', **props):
        if not (-2 <= x <= 9 and 0 <= y <= 16 and -1 <= z <= 13):
            raise UserError('The unique small trade frontage escaped its finite envelope')
        p = x, y, z
        if p in self.body and material not in VOID and not material.endswith('_door'):
            raise UserError('Preserve the exact trade-house walking body: ' + str(p))
        self.blocks[p] = state(self.registry, material, **props)
        self.roles[p] = role; self.tags.pop(p, None)
        if len(self.blocks) > 6000:
            raise UserError('One small furnished trade must remain finite')

    def beam(self, x, y, z, axis, role='rooted dark structural timber'):
        material = {'y': 'minecraft:stripped_dark_oak_log', 'x': 'chipped:reinforced_dark_oak_log', 'z': 'chipped:edged_stripped_dark_oak_log'}[axis]
        self.put(x, y, z, material, axis=axis, role=role)

    def slab(self, x, y, z, wood='dark_oak', role='shallow supported timber detail'):
        self.put(x, y, z, 'minecraft:'+wood+'_slab', type='top', waterlogged=False, role=role)

    def floor(self, cells, y):
        x0 = min(x for x,z in cells)
        for x,z in sorted(cells):
            if (x,z-1) not in cells or (x,z+1) not in cells:
                self.put(x,y,z,'minecraft:dark_oak_planks',role='actual transverse end board')
            elif (x-1,z) not in cells or (x+1,z) not in cells:
                self.put(x,y,z,'minecraft:stripped_spruce_wood',axis='z',role='longitudinal edge sleeper')
            elif (x-x0)%4==0:
                self.put(x,y,z,'chipped:cross_laced_spruce_planks',role='real narrow longitudinal floor joist')
            else:
                self.put(x,y,z,'minecraft:spruce_planks',role='three-wide weathered floorboards')

    def walls(self, cells, low, high, panel):
        edge = boundary(cells)
        x0,z0 = min(x for x,z in cells),min(z for x,z in cells)
        for x,z in sorted(edge):
            along_x = (x-1,z) in edge and (x+1,z) in edge
            along_z = (x,z-1) in edge and (x,z+1) in edge
            post = not (along_x or along_z) or ((x-x0)%4==0 if along_x else (z-z0)%4==0)
            for y in range(low,high+1):
                if post: self.beam(x,y,z,'y')
                elif (y-low)%4==3: self.beam(x,y,z,'x' if along_x else 'z')
                else: self.put(x,y,z,panel,role='deeply framed muted weathered infill')

    def ring(self, cells, y):
        edge = boundary(cells)
        for x,z in sorted(edge):
            axis = 'x' if (x-1,z) in edge or (x+1,z) in edge else 'z'
            self.beam(x,y,z,axis,role='expressed floor and eaves band')

    def reserve(self, title, cells, *, stairs=False):
        cells = list(cells)
        for x,y,z in cells:
            for yy in (y,y+1):
                # A route may include an openable interaction boundary. It
                # never erases either half of an already-authored real door.
                p=x,yy,z
                if not key(self.blocks.get(p,AIR)).endswith('_door'):
                    self.put(*p,AIR,role='explicit two-high walking space')
                self.body.add(p)
        self.routes.append({'name':title,'feet_local':[list(p) for p in cells],'kind':'stairs' if stairs else 'floor'})

    def door(self,x,y,z,face):
        inward={'north':'south','south':'north','west':'east','east':'west'}[face]
        for dy,half in ((0,'lower'),(1,'upper')):
            self.put(x,y+dy,z,'mcwdoors:dark_oak_cottage_door',facing=inward,half=half,hinge='left',open=False,powered=False,role='actual normally openable cottage door')
        self.entries.append({'local':[x,y,z],'outward':face})

    def flight(self,x,start_z):
        for n in range(5):
            z=start_z-n;y=1+n
            for yy in (y+1,y+2,y+3):self.put(x,yy,z,AIR,role='real stair headroom')
            for yy in range(1,y):self.put(x,yy,z,'minecraft:stone_bricks' if yy==1 else 'chipped:boxed_dark_oak_planks',role='stone stair shoe with rooted timber carriage')
            self.put(x,y,z,'minecraft:dark_oak_stairs',facing='north',half='bottom',shape='straight',waterlogged=False,role='genuine five-riser indoor stair')
            self.stairs.append((x,y,z))
        self.reserve('upper stair arrival',[(x,6,start_z-5),(x-1,6,start_z-5)])

    def casement(self,x,y,z,face,width=2,height=2):
        dx,dz=VEC[face];tx,tz=(1,0) if dz else (0,1)
        for i in range(width):
            for j in range(height):
                self.put(x+i*tx,y+j,z+i*tz,'mcwwindows:dark_oak_four_window',facing=face,windowstate='locked',role='real framed casement with depth')
        for i in range(-1,width+1):
            self.beam(x+i*tx+dx,y+height,z+i*tz+dz,'x' if tx else 'z',role='projecting window hood supported by wall head')
        for i in (-1,width):
            self.put(x+i*tx+dx,y+height-1,z+i*tz+dz,'mythrais:curved_corbel_dark_oak',facing=face,shape=0,role='carved casement knee')
        self.details.append({'kind':'deep casement and carved hood','local':[x,y,z],'outward':face,'width':width})

    def lamp(self,x,y,z,face):
        self.put(x,y,z,'mcwlights:tavern_wall_lantern',facing=face,role='small warm supported task lantern')
        dx,dz=VEC[face];self.supports.append(((x,y,z),(x-dx,y,z-dz)))
        self.lights.append((x,y,z))

    def hanging(self,x,y,z):
        self.put(x,y+1,z,'chipped:nailed_dark_oak_log',axis='x',role='real short lamp-bearing ceiling tie')
        self.put(x,y,z,'minecraft:lantern',hanging=True,waterlogged=False,role='low warm real-emission room light')
        self.supports.append(((x,y,z),(x,y+1,z)));self.lights.append((x,y,z))

    def counter(self,x,y,z,face='east',top='dark_oak_planks',role='real counter'):
        self.put(x,y,z,'handcrafted:dark_oak_counter',facing=face,counter=top,type=1,role=role)

    def cup(self,x,y,z,face='south'):
        self.put(x,y,z,'handcrafted:wood_cup',facing=face,pieces=2,waterlogged=False,role='small actual tabletop vessels')

    def shelf(self,x,y,z,face='south'):
        self.put(x,y,z,'handcrafted:dark_oak_shelf',facing=face,shape='single',type=3,role='trade-specific shelf')
        self.put(x,y+1,z,'handcrafted:stackable_book',facing=face,books=3,seed=17,role='household/trade ledgers')

    def barrel(self,x,y,z,title,stacks=()):
        self.put(x,y,z,'minecraft:barrel',facing='up',open=False,role='new small named trade supply barrel')
        for item,count in stacks:
            if item not in self.registry['items'] or not 1<=count<=16:raise UserError('Only registered modest genuine new supplies')
        self.tags[x,y,z]={'CustomName':json.dumps({'text':title},separators=(',',':')),
            'Items':[{'Slot':Byte(i),'id':item,'count':count} for i,(item,count) in enumerate(stacks)]}

    def sign(self,x,y,z,face,lines):
        self.put(x,y,z,'minecraft:dark_oak_wall_sign',facing=face,waterlogged=False,role='readable waxed trade notice')
        dx,dz=VEC[face];self.supports.append(((x,y,z),(x-dx,y,z-dz)))
        self.tags[x,y,z]={'is_waxed':True,'front_text':{'messages':[json.dumps({'text':line},separators=(',',':')) for line in lines], 'color':'white','has_glowing_text':False}}

    def bed(self,x,y,z,face='south'):
        dx,dz=VEC[face]
        self.put(x,y,z,'minecraft:brown_bed',facing=face,part='foot',occupied=False,role='genuine household bed; no resident assigned')
        self.put(x+dx,y,z+dz,'minecraft:brown_bed',facing=face,part='head',occupied=False,role='genuine household bed head')


def hip(p,box,base,family='brown_terracotta',end='minecraft:mud_brick_stairs'):
    """Actually four-sided tile facets, seam caps, underside and low carved eaves."""
    x0,z0,x1,z1=box
    for x in range(x0,x1+1):
        for z in range(z0,z1+1):
            a,b=min(x-x0,x1-x),min(z-z0,z1-z);d=min(a,b);y=base+d
            if a==b:
                p.slab(x,y,z,'spruce',role='expressed matching hipped corner seam')
            elif a<b:
                p.put(x,y,z,'mcwroofs:'+family+'_roof',facing='east' if x<(x0+x1)/2 else 'west',half='bottom',shape='straight',role='weathered clay side roof facet')
            else:
                p.put(x,y,z,end,facing='south' if z<(z0+z1)/2 else 'north',half='bottom',shape='straight',waterlogged=False,role='matching short front/back hipped tile facet')
            if d and key(p.blocks.get((x,y-1,z),AIR)) in VOID:
                p.slab(x,y-1,z,'dark_oak' if a<b else 'spruce',role='roof facet real underside purlin')
    p.details.append({'kind':'full hipped roof','box_local':list(box),'base_y':base,'side_family':family,'short_end_facet':end})


def smith(registry):
    p=TradeHouse(registry,'The Crooked Iron',(1013,63,-1294))
    main=rectangle(0,0,7,11)-{(0,z) for z in range(3)}-{(1,0)}
    high=rectangle(3,0,7,10)
    p.footprint=main
    for x,z in main:
        for y in range(1,13):p.put(x,y,z,AIR,role='complete small shop/home interior')
    p.floor(main,0);p.walls(main,1,4,'dawnoftimebuilder:plastered_stone')
    upper=high-{(5,z) for z in range(6,11)}
    p.floor(upper,5);p.walls(high,6,8,'minecraft:gray_terracotta');p.ring(high,5);p.ring(high,9)
    # The two masses share a proper open timber-framed joint, not an appliqué.
    for z in range(4,9):
        for y in (1,2,3):p.put(3,y,z,AIR,role='open forge-to-workshop connection')
    for z in (3,9):
        for y in range(1,5):p.beam(3,y,z,'y')
    for z in range(3,10):p.beam(3,4,z,'z',role='real forge/lodging linking lintel')
    hip(p,(2,-1,8,11),9,'gray_terracotta','dawnoftimebuilder:roofing_slates_stairs')
    hip(p,(-1,2,3,12),5,'brown_terracotta')
    # Narrow full chimney continues from the genuine cold smelting hearth.
    for y in range(2,11):p.put(1,y,5,'minecraft:bricks',role='continuous rooted forge flue')
    for x,z,face in ((0,5,'east'),(2,5,'west'),(1,4,'south'),(1,6,'north')):
        p.put(x,10,z,'minecraft:brick_stairs',facing=face,half='top',shape='straight',waterlogged=False,role='small carved chimney cap')
    p.put(1,11,5,'minecraft:brick_wall',north='none',south='none',east='none',west='none',up=True,waterlogged=False,role='safe open masonry chimney terminal')
    p.casement(7,2,2,'east',2,2);p.casement(7,6,2,'east',2,2)
    p.casement(4,6,0,'north',2,2)
    p.reserve('recessed east entry and smith bench aisle',[(x,1,8) for x in range(6,9)]+[(6,1,z) for z in range(4,11)]+[(x,1,4) for x in range(2,6)])
    p.reserve('forge working aisle',[(2,1,z) for z in range(5,10)]+[(3,1,8),(4,1,9)])
    p.reserve('upper home passage',[(5,6,z) for z in range(1,6)]+[(4,6,4),(6,6,4)])
    p.flight(5,10);p.door(7,1,8,'east')
    p.put(1,1,5,'minecraft:blast_furnace',facing='east',lit=False,role='genuine usable blast furnace; no fake output or forced burning')
    p.put(0,1,6,'minecraft:furnace',facing='east',lit=False,role='genuine second smelting station')
    p.put(1,1,7,'supplementaries:bellows',facing='north',power=0,role='real manually usable bellows beside the forge')
    p.put(1,1,9,'minecraft:water_cauldron',level=3,role='contained genuine quench water; no river plumbing')
    p.put(4,1,8,'minecraft:anvil',facing='north',role='genuine armour/tool repair anvil with clear approach')
    p.put(3,1,10,'minecraft:grindstone',face='floor',facing='north',role='genuine grounded sharpening wheel')
    p.put(4,1,2,'minecraft:smithing_table',role='genuine armourer upgrade bench')
    p.put(6,1,1,'create:brown_toolbox',facing='south',waterlogged=False,role='real new empty portable Create tool storage')
    p.barrel(2,1,10,'The Crooked Iron — ordinary supplies',[('minecraft:coal',8),('minecraft:iron_ingot',4),('minecraft:leather',4)])
    p.counter(4,1,1,'south','andesite',role='repair ledger and tool counter');p.cup(4,2,1)
    p.shelf(6,2,2,'west');p.lamp(6,3,3,'west');p.lamp(8,3,7,'east')
    for x in range(3,8):p.beam(x,9,4,'x',role='full visible upper-home roof tie bearing the lamp')
    p.hanging(2,3,8);p.hanging(5,8,4)
    p.sign(8,3,8,'east',['THE CROOKED IRON','Armour • Repairs','Coal & iron inside','Please quench safely'])
    p.bed(4,6,1);p.put(6,6,1,'handcrafted:dark_oak_nightstand',facing='south',color='none',waterlogged=False,role='smith’s bedside locker')
    p.put(6,6,6,'handcrafted:dark_oak_desk',facing='west',color='none',waterlogged=False,role='upstairs repairs/order desk')
    p.put(6,7,6,'handcrafted:stackable_book',facing='west',books=3,seed=19,role='repair orders and household books')
    p.put(4,6,7,'handcrafted:dark_oak_chair',facing='east',color='brown',waterlogged=False,role='real upstairs reading chair')
    p.put(3,6,7,'minecraft:potted_fern',role='genuine contained loft plant')
    p.barrel(6,6,8,'Smith’s private household linen')
    # Roof and interior relief: shallow coffer ribs, no broad blank ceiling.
    for z in (2,6,10):
        for x in range(4,7):p.slab(x,4,z,'spruce',role='visible shallow coffer under the home floor')
    p.rooms=[{'name':'low forge and quench bay','local_feet':[2,1,8],'contents':'Two native furnaces, real bellows, grounded quench cauldron, tools and warm task light'},
        {'name':'armour/repair workroom','local_feet':[6,1,6],'contents':'Anvil, grindstone, smithing table, real Create toolbox, supply barrel and order counter'},
        {'name':'smith’s actual upstairs home','local_feet':[4,6,4],'contents':'Five-riser stair, bed, private linen, books, desk, reading chair and contained fern'}]
    p.stations=['minecraft:blast_furnace','minecraft:furnace','minecraft:anvil','minecraft:grindstone','minecraft:smithing_table','create:brown_toolbox','supplementaries:bellows']
    p.join_derivations=canonical_joins(p)
    return p


def merchant(registry):
    p=TradeHouse(registry,'The Sounding Line',(1024,63,-1292))
    main=rectangle(0,0,6,10)-{(5,10),(6,10)};p.footprint=main
    for x,z in main:
        for y in range(1,13):p.put(x,y,z,AIR,role='complete chart shop and lived-in loft interior')
    p.floor(main,0);p.walls(main,1,4,'minecraft:cyan_terracotta')
    upper=main-{(4,z) for z in range(5,10)}
    p.floor(upper,5);p.walls(main,6,8,'dawnoftimebuilder:plastered_stone');p.ring(main,5);p.ring(main,9)
    hip(p,(-1,-1,7,11),9,'brown_terracotta')
    # The usable upper gallery turns around the SOUTH end, preserving the
    # entire shared narrow west lane and its agreed one-metre high eave edge.
    for x in range(0,5):
        for z in (11,12):p.slab(x,5,z,'spruce',role='real transverse-board two-deep supported upper gallery floor')
        p.put(x,6,12,'minecraft:dark_oak_fence',north=False,south=False,east=x!=4,west=x!=0,waterlogged=False,role='rooted open upper gallery safety railing')
    for x in (0,4):
        p.put(x,4,11,'mythrais:curved_corbel_dark_oak',facing='south',shape=0,role='gallery knee rooted in actual house band')
    p.casement(0,2,1,'west',2,2);p.casement(6,6,2,'east',2,2)
    p.casement(3,6,10,'south',2,2)
    p.reserve('chart shop recessed west entry',[(x,1,6) for x in range(-1,4)]+[(2,1,z) for z in range(2,9)])
    p.reserve('sail workshop cross aisle',[(x,1,8) for x in range(2,4)])
    p.reserve('home upper passage',[(3,6,z) for z in range(2,10)]+[(x,6,5) for x in range(1,4)]+[(x,6,9) for x in (1,2)]+[(1,6,z) for z in (10,11)])
    p.flight(4,9);p.door(0,1,6,'west');p.door(1,6,10,'south')
    for z in (3,4):p.counter(1,1,z,'east','andesite',role='deep chart consultation and sail-order counter')
    p.put(1,2,3,'supplementaries:globe',facing='east',powered=False,rotation=0,waterlogged=False,role='real rotatable navigator’s globe')
    p.put(1,2,4,'handcrafted:stackable_book',facing='east',books=2,seed=21,role='pilot books and ordinary shipping ledgers')
    p.put(4,1,1,'minecraft:cartography_table',role='genuine chart copying/expansion workstation')
    p.put(5,1,7,'minecraft:loom',facing='west',role='genuine canvas/banner weaving workstation')
    p.put(5,1,2,'minecraft:crafting_table',role='genuine sail repair and fitting bench')
    p.barrel(5,1,3,'Sounding Line — charts and canvas',[('minecraft:paper',8),('minecraft:string',8),('minecraft:white_wool',4)])
    p.shelf(5,2,5,'west')
    p.put(1,1,8,'handcrafted:dark_oak_chair',facing='east',color='brown',waterlogged=False,role='customer consultation chair')
    p.counter(1,1,9,'north',role='small customer tea table');p.cup(1,2,9)
    p.put(5,1,4,'farmersdelight:dark_oak_cabinet',facing='west',open=False,role='new empty sail fittings cupboard')
    for x in range(0,7):p.beam(x,9,5,'x',role='real visible upper-home roof tie')
    p.lamp(1,3,7,'east');p.lamp(-1,3,7,'west');p.hanging(3,3,3);p.hanging(2,8,5)
    p.sign(-1,3,6,'west',['THE SOUNDING LINE','Charts • Canvas','Sail repairs upstairs','Ask for a quiet chart'])
    p.bed(1,6,1);p.put(2,6,1,'handcrafted:dark_oak_nightstand',facing='south',color='none',waterlogged=False,role='lived-in bedside locker')
    p.put(1,6,8,'handcrafted:dark_oak_desk',facing='east',color='none',waterlogged=False,role='actual sail-pattern and chart home desk')
    p.put(1,7,8,'handcrafted:stackable_book',facing='east',books=3,seed=9,role='sail patterns and navigation notebooks')
    p.put(2,6,8,'handcrafted:dark_oak_chair',facing='west',color='brown',waterlogged=False,role='usable home desk chair')
    p.put(5,6,1,'minecraft:smoker',facing='west',lit=False,role='genuine compact household cooking hearth')
    p.counter(5,6,2,'west');p.cup(5,7,2,'west')
    p.barrel(5,6,3,'Merchant’s household pantry',[('minecraft:bread',4)])
    p.put(1,6,7,'minecraft:potted_flowering_azalea_bush',role='genuine rooted home flowering pot')
    p.put(1,1,1,'minecraft:potted_blue_orchid',role='real planted trade-window niche')
    for z in (2,7):
        for x in range(1,6):
            if (x,z)!=(4,7):p.slab(x,4,z,'spruce',role='shallow ornamented shop ceiling coffer clear of the real stair')
    for z in (1,8):
        p.put(0,8,z,'mythrais:curved_corbel_dark_oak',facing='east',shape=0,role='loft roof tie carved support')
    p.rooms=[{'name':'navigator’s consultation shop','local_feet':[2,1,4],'contents':'Deep ledgers/globe display, working cartography, customer seat and warm lamps'},
        {'name':'canvas and sail repair return','local_feet':[3,1,8],'contents':'Real loom/crafting, ordinary supply stock, cupboards and clear stair access'},
        {'name':'sailmaker’s lived-in upper home','local_feet':[3,6,7],'contents':'Normal stair, bed, actual kitchen, pantry, desk, books, chair, plants and a real supported balcony'}]
    p.stations=['minecraft:cartography_table','minecraft:loom','minecraft:crafting_table','minecraft:smoker','supplementaries:globe']
    p.join_derivations=canonical_joins(p)
    return p


def world_blocks(p):
    return {tuple(p.origin[i]+q[i] for i in range(3)):v for q,v in p.blocks.items()}


def validate(p):
    material=require_material_rule(p.blocks,p.name+' — entire original furnished building')
    for q in p.body:
        value=key(p.blocks.get(q,AIR))
        if value not in VOID and not value.endswith('_door'):
            raise UserError('A late detail erases actual circulation')
    for route in p.routes:
        for x,y,z in route['feet_local']:
            if (x,y-1,z) not in p.blocks:continue  # exact retained exterior floor checked when bound
            if key(p.blocks[x,y-1,z]) in VOID:raise UserError('A room route lacks an actual floor')
    for x,y,z in p.stairs:
        if any(key(p.blocks.get((x,yy,z),AIR)) not in VOID for yy in (y+1,y+2)):
            raise UserError('A genuine staircase has obstructed headroom')
    for detail,support in p.supports:
        if key(p.blocks.get(support,AIR)) in VOID:raise UserError('A small fitting lacks a real authored backing')
    solid={q for q,v in p.blocks.items() if key(v) not in VOID}
    roots={(x,0,z) for x,z in p.footprint};pending=deque(roots)
    while pending:
        q=pending.popleft()
        for d in ((1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1)):
            n=tuple(q[i]+d[i] for i in range(3))
            if n in solid and n not in roots:roots.add(n);pending.append(n)
    if solid-roots:raise UserError('A house fitting is unrooted: '+str(sorted(solid-roots)[:8]))
    world=world_blocks(p)
    if any(1021<=x<=1023 and 64<=y<=65 and -1296<=z<=-1280 and key(v) not in VOID for (x,y,z),v in world.items()):
        raise UserError('Keep the crooked shared lane’s complete low walking body')
    return {'material':material,'targets':len(p.blocks),'solids':len(solid),'all_solids_rooted':True,
        'rooms':len(p.rooms),'warm_lamps':len(p.lights),'new_tagged_fixtures':len(p.tags),'canonical_join_derivations':len(p.join_derivations),
        'native_shapes_survival_use_stairs_seating_and_visual_quality':'PENDING; no quality claim from counts or one-axis permission'}


def admitted_before(pos,old,foundation,below,protected):
    if old is None or protected:raise UserError('Preserve unknown cells and every saved default/inventoried block entity')
    if foundation:
        if key(old) not in {'minecraft:gravel'}|VOID|SOFT or below is None or key(below) not in GROUND:
            raise UserError('A small house foundation lacks real dry solid support: '+str(pos))
    elif key(old) not in VOID|SOFT:
        raise UserError('Do not overwrite any native/player/old authored object: '+str(pos)+' '+key(old))


def prepare(home,checkpoint_id,checkpoint_sha):
    home=Path(home).resolve();reserve=guard(2*MIB,MAX_OUTPUT)
    if home.parent!=Path('D:/A World for Two/staging/world-tests').resolve():raise UserError('Owned private stage only')
    receipt=read_json(home/'dashboard/settlement/backup-receipt.json');owner=read_json(home/'dashboard/artistic-owner.json')
    admit_owner(home,owner,receipt,checkpoint_id,checkpoint_sha)
    registry=read_json(home/'dashboard/settlement/registry.json')
    houses=[smith(registry),merchant(registry)];proofs=[validate(p) for p in houses]
    protected=set();custody=[]
    for label,rel,sha in REFERENCES:
        path=home/rel
        if path.is_symlink() or not 0<path.stat().st_size<=8*MIB or digest(path)!=sha:raise UserError('Retain exact accepted/future neighbor: '+label)
        doc=read_json(path);cells={tuple(row[:3]) for row in doc['blocks']};protected.update(cells)
        custody.append({'name':label,'path':rel,'sha256':sha,'cells':len(cells),'all_solid_AIR_routes_preserved':True})
    path=home/FOREST[0]
    if path.is_symlink() or path.stat().st_size>4*MIB or digest(path)!=FOREST[1]:raise UserError('Retain the complete current native-tree field reservation')
    tree_columns=set(map(tuple,read_json(path)['all_growth_excluded_columns_xz']))
    snapshot=BackupWorld(home,receipt,registry);outputs={};reservation={};records=[];started=time.monotonic()
    try:
        for p,proof in zip(houses,proofs):
            after=world_blocks(p);tags={tuple(p.origin[i]+q[i] for i in range(3)):v for q,v in p.tags.items()}
            if protected.intersection(after):raise UserError('The new pair overlaps exact existing/future authored cells')
            if {(x,z) for x,y,z in after}&tree_columns:raise UserError('Preserve complete reviewed native tree fields')
            before,supports={},{}
            for q in after:
                if time.monotonic()-started>120:raise UserError('Finite stopped-save trade-pair reader expired')
                old=snapshot.state(q);local=tuple(q[i]-p.origin[i] for i in range(3));foundation=local[1]==0 and (local[0],local[2]) in p.footprint
                below=(q[0],q[1]-1,q[2]);support=snapshot.state(below) if foundation else None
                admitted_before(q,old,foundation,support,q in snapshot.protected)
                before[q]=old
                if foundation:supports[below]=support
            for route in p.routes:
                for x,y,z in route['feet_local']:
                    local_floor=(x,y-1,z)
                    if local_floor in p.blocks:continue
                    q=tuple(p.origin[i]+local_floor[i] for i in range(3));v=snapshot.state(q)
                    if key(v) not in GROUND:raise UserError('An exterior trade threshold lacks real retained dry ground')
                    supports[q]=v
            stem='crooked-iron' if p.name=='The Crooked Iron' else 'sounding-line'
            for suffix,field,label,nbt in (
                ('before-VERIFY-ONLY',before,'Exact current untouched trade-site preimage',None),
                ('PROPOSAL',after,p.name+' original fully furnished Tortuga frontage',tags),
                ('complete-VERIFY-ONLY',after,p.name+' full new geometry/tags',tags),
                ('retained-supports-VERIFY-ONLY',supports,'Exact actual retained dry supports/thresholds',None)):
                outputs[stem+'-'+suffix+'.json']=native_payload(registry,field,checkpoint_sha,label,tags=nbt)
            reservation.update({q:AIR for q in after})
            w=lambda q:[p.origin[i]+q[i] for i in range(3)]
            records.append({'name':p.name,'origin':list(p.origin),'proof':proof,'rooms':p.rooms,'entries':[dict(row,world=w(row['local'])) for row in p.entries],
                'walking_routes':p.routes,'stairs_local':[list(q) for q in p.stairs],'working_native_station_types':p.stations,
                'details':p.details,'native_join_derivations':p.join_derivations,'role_counts':dict(Counter(p.roles.values())),
                'one_block_dry_masonry_shoes':[list(q) for q,v in before.items() if q[1]==p.origin[1] and key(v) in VOID|SOFT],
                'existing_BEs_or_inventories_changed':0})
        outputs['future-pair-solid-AIR-route-reservation-ONLY.json']=native_payload(registry,reservation,checkpoint_sha,'Future two original trade frontages; not observed AIR or growth authority')
        mask=json.loads(outputs['future-pair-solid-AIR-route-reservation-ONLY.json']);mask.update(reservation_only=True,not_an_observed_AIR_plan=True)
        outputs['future-pair-solid-AIR-route-reservation-ONLY.json']=(json.dumps(mask,separators=(',',':'))+'\n').encode()
        cameras=[{'name':'opposite-crooked-trades','feet':[1022.5,64,-1280.5],'look_at':[1021.5,69,-1288]},
            {'name':'smith-working-room','feet':[1019.5,64,-1287.5],'look_at':[1015,65,-1287]},
            {'name':'smith-home','feet':[1017.5,69,-1289.5],'look_at':[1017,70,-1292]},
            {'name':'merchant-chart-counter','feet':[1026.5,64,-1286.5],'look_at':[1025,65,-1289]},
            {'name':'merchant-home-gallery','feet':[1027.5,69,-1287.5],'look_at':[1025,70,-1288]}]
        merged={q:v for p in houses for q,v in world_blocks(p).items()}
        for row in cameras:
            x,y,z=map(math.floor,row['feet']);positions=[(x,y-1,z),(x,y,z),(x,y+1,z)]
            values=[merged[q] if q in merged else snapshot.state(q) for q in positions]
            if key(values[0]) in VOID|{'minecraft:water','minecraft:lava'} or any(key(v) not in VOID for v in values[1:]):raise UserError('A proposed camera lacks real floor/body: '+row['name'])
            row['saved_or_proposed_floor_body']=[{'pos':list(q),'state':v,'source':'new authored geometry' if q in merged else 'current stopped save'} for q,v in zip(positions,values)]
            row['native_pose_and_view']='PENDING actual framebuffer/collision review'
        record={'format':'awft-tortuga-trade-pair:1','checkpoint_id':checkpoint_id,'checkpoint_sha256':checkpoint_sha,
            'source_sha256':digest(Path(__file__)),'status':'SOURCE ONLY; no native placement or native/art acceptance',
            'design':'Two individually composed crooked trades opposite one narrow lane; muted heavy timber/masonry/plaster, lower forge hip, tall repair home, merchant hip/gallery, intimate furnished scenes',
            'buildings':records,'native_cameras':cameras,'neighbor_custody':custody,'native_tree_field_reservation_sha256':FOREST[1],
            'saved_sources':snapshot.sources,'private_saved_default_or_inventoried_BEs_preserved':True,'native_actions':0,'world_writes':0,
            'quay_lane_contract':'No new solid in X1021..1023/Y64..65/Z-1296..-1280. Exact ground/route expansion remains South lane.',
            'normal_workstations':'Real registered cold stations and modest new supplies; operation/output/trading/seating pending normal native use, not fabricated',
            'native_gates':'Fresh occupancy + exact before/support verification; parent-only admitted copy/one placement; native settle/full state/NBT and real exterior/interior/stair/use views',
            'reserve_guard':reserve,'files':{name:{'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)} for name,raw in outputs.items()}}
        outputs['manifest.json']=(json.dumps(record,ensure_ascii=False,indent=2)+'\n').encode()
        if sum(map(len,outputs.values()))>MAX_OUTPUT:raise UserError('Finite new trade-pair output exceeded')
        guard(2*MIB,MAX_OUTPUT);output=home/'staging'/('tortuga-trade-pair-'+str(time.time_ns()));output.mkdir()
        for name,raw in outputs.items():
            with (output/name).open('xb') as stream:stream.write(raw)
        return {'folder':str(output),'manifest_sha256':digest(output/'manifest.json'),'buildings':[{k:v for k,v in row.items() if k in ('name','origin','entries')} for row in records],
            'targets':sum(len(p.blocks) for p in houses),'native_actions':0,'files':record['files']}
    finally:snapshot.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--home',type=Path,required=True)
    parser.add_argument('--checkpoint-id',required=True);parser.add_argument('--checkpoint-sha',required=True)
    args=parser.parse_args();print(json.dumps(prepare(args.home,args.checkpoint_id,args.checkpoint_sha),indent=2))
