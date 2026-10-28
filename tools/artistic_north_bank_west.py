"""Five original intimate quay shops, source-only until measured plot binding.

No world calls, grid subdivision, terrain leveling, entity spawning or repeated
house template. The eastern/masterplan owner supplies the dry plot/route masks.
"""
from __future__ import annotations

import argparse
from collections import deque
import hashlib
import json
from pathlib import Path

from control_room.common import UserError,digest,read_json,utcnow
from tools.artistic_materials import require_material_rule,require_outdoor_rule
from tools.artistic_spawn_plaza import state,payload,key
from tools.playtest import guard
from tools.settlement_attractions import properties

AIR='minecraft:air'
VOID={AIR,'minecraft:cave_air','minecraft:void_air'}
LABELS={'florist':'Marigold & Tide','smith':'The Rivet & Ember','armoury':'The Black Gull Armoury',
        'shipwright':"The Wren’s Keel",'tavern':'The Lantern Wake'}
PLOTS={'shipwright':(1016,-1266,0),'smith':(1040,-1268,2),'armoury':(1029,-1251,0),
       'tavern':(1056,-1272,2),'florist':(1081,-1249,0)}
RESERVED=((1096,-1268,1120,-1240),(1043,-1237,1053,-1227),(1059,-1253,1069,-1243))
ZIPLINE_MASK='staging/zipline-west-v2-source-1793152099836099800/all-v2-RESERVATION-ONLY.json'
ZIPLINE_MASK_SHA='92ea594836795a61e00f5cc32290d49d1d47b9fd6eb55aeefc99d527acf8854d'


def rect(x0,z0,x1,z1):return{(x,z)for x in range(x0,x1+1)for z in range(z0,z1+1)}


class Shop:
    def __init__(self,registry,kind,width,depth):
        self.registry,self.kind,self.width,self.depth=registry,kind,width,depth
        self.blocks={};self.main=set();self.floors={};self.routes=[];self.features=[];self.work=[];self.tags={}
        self.doors={};self.overhangs=set();self.stairs=[];self.lights=[];self.entries=[]

    def put(self,x,y,z,name,*,replace=False,**props):
        if any(type(v)is not int for v in(x,y,z))or not(-2<=x<=self.width+1 and -2<=z<=self.depth+1 and 0<=y<=16):
            raise UserError('Original shop feature escaped its compact local envelope')
        value=state(self.registry,name,**props);pos=x,y,z;old=self.blocks.get(pos,AIR)
        if old!=AIR and old!=value and not replace:raise UserError('Two authored shop features conflict: '+str((self.kind,pos,old,value)))
        self.blocks[pos]=value

    def floor(self,cells,y=0):
        self.floors.setdefault(y,set()).update(cells)
        if y==0:self.main.update(cells)
        for x,z in sorted(cells):
            name=(('chipped:boxed_dark_oak_planks'if x%4==0 else'chipped:crossed_dark_oak_planks')if z%5==0 else
                  'chipped:cross_laced_dark_oak_planks'if x%4==0 else
                  'chipped:detailed_dark_oak_planks'if z%4==0 else'chipped:boxed_dark_oak_planks')
            self.put(x,y,z,name,replace=True)

    def shell(self,cells,height,panel,*,upper=None):
        self.floor(cells)
        edge={q for q in cells if any((q[0]+dx,q[1]+dz)not in cells for dx,dz in((1,0),(-1,0),(0,1),(0,-1)))}
        for x,z in cells:
            for y in range(1,height+1):self.put(x,y,z,AIR)
        for x,z in edge:
            along_x=(x-1,z)in edge and(x+1,z)in edge
            along_z=(x,z-1)in edge and(x,z+1)in edge
            post=(x%4==0 if along_x else z%4==0)or not(along_x or along_z)
            for y in range(1,height+1):
                if post:
                    self.put(x,y,z,'minecraft:polished_deepslate'if y%4==0 else'minecraft:stripped_dark_oak_log',
                             **({}if y%4==0 else{'axis':'y'}))
                elif y%4==0:self.put(x,y,z,'minecraft:dark_oak_planks')
                else:self.put(x,y,z,upper if upper and y>=5 else panel)
        self.features.append('Three-high framed plaster/brick panels and real corner/ledger joints; no random recolor')

    def stair(self,x,y,z,face,wood='dark_oak',half='bottom',*,replace=False):
        self.put(x,y,z,'minecraft:'+wood+'_stairs',facing=face,half=half,shape='straight',waterlogged=False,replace=replace)

    def slab(self,x,y,z,wood='dark_oak',*,replace=False):
        self.put(x,y,z,'minecraft:'+wood+'_slab',type='top',waterlogged=False,replace=replace)

    def roof(self,x0,x1,z0,z1,start=8,wood='dark_oak'):
        for x in range(x0,x1+1):
            rise=min(x-x0,x1-x)
            for z in range(z0,z1+1):
                material='oxidized_cut_copper'if(z-z0)%4==0 else wood
                self.stair(x,start+rise,z,'east'if x<=(x0+x1)//2 else'west',material)
        # Three-high framed gable panels follow the actual asymmetric roof.
        for z in(z0+1,z1-1):
            for x in range(x0+1,x1):
                top=start+min(x-x0,x1-x)
                for y in range(start,top):
                    if(x-x0)%4==0:
                        name='minecraft:polished_deepslate'if(y-start)%4==3 else'minecraft:stripped_dark_oak_log'
                        props={}if name.endswith('deepslate')else{'axis':'y'}
                    else:name='chipped:detailed_dark_oak_planks'if(y-start)%4==3 else'minecraft:brown_terracotta';props={}
                    self.put(x,y,z,name,replace=True,**props)
        self.features.append('Deep pitched roof with structural copper seams and filled framed gables')

    def doorway(self,x,z=0,*,double=False):
        for xx in range(x,x+2 if double else x+1):
            self.stair(xx,0,z-1,'south','spruce')
            self.main.add((xx,z-1));self.floors.setdefault(0,set()).add((xx,z-1))
            self.entries.append((xx,0,z-1))
            for y in range(1,4):self.put(xx,y,z,AIR,replace=True)
            for y,part in((1,'lower'),(2,'upper')):
                self.put(xx,y,z+1,'minecraft:dark_oak_door',facing='north',half=part,hinge='left'if xx==x else'right',open=False,powered=False,replace=True)
                self.doors[xx,y,z+1]=self.blocks[xx,y,z+1]
            self.slab(xx,3,z+1,replace=True)
            self.routes.append([(xx,0,zz)for zz in range(z-1,z+3)])
        for xx in(x-1,x+2 if double else x+1):
            for y in range(1,4):self.put(xx,y,z+1,'minecraft:stripped_dark_oak_log',axis='y',replace=True)
            self.put(xx,3,z,'mythrais:curved_corbel_dark_oak',facing='north',shape=0,replace=True)
        self.features.append('Recessed normal usable door with carved jambs, high brow and real entry shadow')

    def window(self,x,y,z,face='north',kind='dark_oak',height=2,*,gothic=False,brow=True):
        for n in range(height):
            if gothic:self.put(x,y+n,z,'mcwwindows:blackstone_brick_gothic',facing=face,open=False,
                               part='bottom'if n==0 else'top'if n==height-1 else'middle',replace=True)
            else:self.put(x,y+n,z,'mcwwindows:'+kind+'_window2',facing=face,windowstate='closed',replace=True)
        if brow:
            dx,dz={'north':(0,-1),'south':(0,1),'west':(-1,0),'east':(1,0)}[face]
            ax,az=(1,0)if dz else(0,1)
            for side in(-1,1):
                self.put(x+dx+side*ax,y+height-1,z+dz+side*az,'mythrais:curved_corbel_dark_oak',facing=face,shape=0)
            for side in(-1,0,1):
                self.slab(x+dx+side*ax,y+height,z+dz+side*az)
                self.put(x+dx+side*ax,y-1,z+dz+side*az,'dawnoftimebuilder:limestone_bricks_edge',facing=face,half='top',shape='straight',waterlogged=False)
                self.overhangs.add((x+dx+side*ax,z+dz+side*az))

    def shelf(self,x,y,z,face='east'):
        self.put(x,y,z,'handcrafted:dark_oak_shelf',facing=face,shape='single',type=3)

    def counter(self,x,y,z,face='east',top='dark_oak_planks'):
        self.put(x,y,z,'handcrafted:dark_oak_counter',facing=face,counter=top,type=1)

    def lamp(self,x,y,z,face='north'):
        self.put(x,y,z,'mcwlights:tavern_wall_lantern',facing=face)
        dx,dz={'north':(0,1),'south':(0,-1),'west':(1,0),'east':(-1,0)}[face]
        self.lights.append(((x,y,z),(x+dx,y,z+dz)))

    def table(self,x,y,z,*,chair_face='north',color='brown'):
        self.put(x,y,z,'handcrafted:dark_oak_table',shape='single',color='none',waterlogged=False)
        dx,dz={'north':(0,1),'south':(0,-1),'west':(1,0),'east':(-1,0)}[chair_face]
        self.put(x+dx,y,z+dz,'handcrafted:dark_oak_chair',facing=chair_face,color=color,waterlogged=False)
        self.put(x,y+1,z,'handcrafted:wood_cup',facing=chair_face,pieces=1,waterlogged=False)

    def locker(self,x,y,z,title):
        self.put(x,y,z,'minecraft:barrel',facing='north',open=False)
        self.tags[x,y,z]='{CustomName:'+json.dumps(json.dumps({'text':title}))+',Items:[]}'

    def stair_to_loft(self,x,start_z=1):
        for n in range(4):
            z=start_z+n
            for y in range(n+2,n+4):self.put(x,y,z,AIR,replace=True)
            if n in(1,2):self.put(x,4,z,AIR,replace=True)
            self.stair(x,1+n,z,'south','spruce',replace=True)
            self.stairs.append((x,n+1,z))
        self.routes.append(list(self.stairs[-4:]))
        self.features.append('Real four-rise service stair and separate loft landing, not an inaccessible upper facade')

    def route(self,cells):self.routes.append(list(cells))


def florist(r):
    p=Shop(r,'florist',9,8)
    cells=rect(0,0,6,7)|rect(7,3,8,7)
    p.shell(cells,7,'minecraft:white_terracotta',upper='minecraft:pink_terracotta')
    p.floor(rect(1,5,5,6)|rect(1,1,2,4)|rect(1,0,3,0)|rect(1,-1,3,-1)|{(3,z)for z in range(1,6)}|{(6,5),(6,6)},4)
    p.stair_to_loft(4,start_z=2)
    p.doorway(5)
    # Open the inside return into the stair alcove; the actual outer pilaster
    # and opposite deep jamb still carry the carved entrance hood.
    for y in range(1,4):p.put(4,y,1,AIR,replace=True)
    p.roof(-1,7,-1,8,8,'dark_oak')
    # Lower potting wing is visibly subordinate to the tall shop, not a copy.
    for x in(7,8):
        for z in range(3,9):p.stair(x,6+(8-x),z,'east','spruce',replace=True)
    for x in(1,2,3):
        p.window(x,5,-1,'north','cherry',2,brow=False)
        p.put(x,5,0,AIR,replace=True);p.put(x,6,0,AIR,replace=True)
        p.put(x,7,-1,'minecraft:cherry_slab',type='top',waterlogged=False)
    for x in(1,3):p.put(x,3,-1,'mythrais:curved_corbel_dark_oak',facing='north',shape=0)
    p.overhangs.update((x,-1)for x in(1,2,3))
    for x in(0,4):
        for y in(5,6):p.put(x,y,-1,'minecraft:stripped_dark_oak_log',axis='y')
        p.put(x,7,-1,'minecraft:cherry_stairs',facing='east'if x==0 else'west',half='top',shape='straight',waterlogged=False)
    for z,flower in((2,'potted_dandelion'),(4,'potted_azalea_bush'),(6,'potted_lily_of_the_valley')):
        p.counter(1,1,z);p.put(1,2,z,'minecraft:'+flower)
    p.put(7,1,4,'handcrafted:terracotta_thin_pot');p.put(7,1,6,'handcrafted:golden_medium_pot')
    p.put(6,1,6,'chipped:botanist_workbench');p.work.append({'position':[6,1,6],'use':'Native Chipped botanical station'})
    p.shelf(2,2,6,'north');p.put(2,3,6,'handcrafted:stackable_book',facing='east',books=2,seed=7)
    p.locker(7,1,5,'Marigold & Tide — potting supplies, fill your own stock')
    p.window(0,2,3,'west','cherry',2);p.window(8,2,5,'east','cherry',2)
    p.window(4,5,7,'south','cherry',2)
    p.lamp(5,3,2,'west');p.lamp(2,7,6,'north')
    for z in range(1,6):p.put(3,5,z,'mythrais:wrought_iron_railing_01',facing='east',shape=0)
    for z in(5,6):p.put(6,5,z,'mythrais:wrought_iron_railing_01',facing='east',shape=0)
    p.route([(3,0,z)for z in range(1,7)]+[(4,0,6),(5,0,6)])
    p.route([(x,4,6)for x in range(1,6)]+[(2,4,z)for z in range(1,6)])
    p.features+=['L-shaped potting wing and double-height shop with a wrapping rear/side gallery',
                 'Real accessible one-block projecting cherry oriel on carved corbels, glazed cheeks and shallow coppered roof',
                 'Purposeful potted blooms, glazed display pots, planting bench, ledgers and a warm upper nook']
    return p


def smith(r):
    p=Shop(r,'smith',11,9);cells=rect(0,0,7,8)
    p.shell(cells,5,'minecraft:mud_bricks');p.floor(rect(8,3,10,8))
    p.doorway(4,double=True);p.roof(-1,8,-1,9,6,'spruce')
    for x in(8,10):
        for z in(3,8):
            for y in range(1,5):p.put(x,y,z,'minecraft:polished_deepslate'if y==3 else'minecraft:stripped_spruce_log',**({}if y==3 else{'axis':'y'}))
            p.put(x,4,z,'mythrais:curved_corbel_dark_oak',facing='east',shape=0,replace=True)
    for x in range(8,11):
        for z in range(3,9):p.stair(x,5,z,'east','dark_oak')
    for y in range(1,4):p.put(7,y,5,AIR,replace=True)
    for z in(4,6):p.put(8,3,z,'mythrais:curved_corbel_dark_oak',facing='east',shape=0)
    for y in range(1,4):
        for x in(1,2):p.put(x,y,7,'minecraft:bricks',replace=True)
    p.put(2,1,6,'dawnoftimebuilder:limestone_fireplace',facing='north',horizontal_connection='none',vertical_connection='none',lit=True,waterlogged=False)
    for y in range(4,12):p.put(2,y,7,'minecraft:brick_wall',north='none',south='none',east='none',west='none',up=True,waterlogged=False,replace=True)
    p.put(1,1,5,'minecraft:blast_furnace',facing='east',lit=False)
    p.put(2,1,3,'minecraft:anvil',facing='north');p.put(6,1,6,'minecraft:smithing_table')
    p.put(9,1,4,'minecraft:grindstone',face='floor',facing='north')
    p.counter(9,1,6,'west','andesite');p.put(9,2,6,'create:brown_toolbox',facing='west',waterlogged=False)
    p.locker(6,1,7,'The Rivet & Ember — customer repair orders, empty')
    p.window(0,2,3,'west','blackstone',2);p.window(7,2,1,'east','blackstone',2)
    p.window(5,2,8,'south','blackstone',2)
    p.lamp(3,3,2,'south');p.lamp(6,3,7,'west')
    p.route([(5,0,z)for z in range(1,8)]+[(x,0,5)for x in range(3,10)])
    p.work+=[{'position':[2,1,3],'use':'Native anvil'},{'position':[6,1,6],'use':'Native smithing table'},{'position':[9,1,4],'use':'Native grinding wheel'}]
    p.features+=['Low soot-dark brick forge with a tall off-centre working hearth/chimney',
                 'Asymmetric open sharpening canopy and public repair counter, not a second enclosed house',
                 'Normal anvil, furnace, smithing and grinding stations with clear customer/service aisles']
    return p


def armoury(r):
    p=Shop(r,'armoury',7,8);cells=rect(0,0,6,7)-{(0,0),(6,7)}
    p.shell(cells,7,'minecraft:gray_terracotta',upper='minecraft:red_terracotta')
    p.floor(rect(1,1,5,6),4);p.stair_to_loft(5,start_z=2);p.doorway(3)
    for y in range(1,4):p.put(4,y,1,AIR,replace=True)
    p.roof(-1,7,-1,8,8,'dark_oak')
    p.window(0,2,3,'west',height=3,gothic=True);p.window(6,5,5,'east','dark_oak',2)
    p.window(2,5,0,'north',height=3,gothic=True)
    p.window(3,5,7,'south','dark_oak',2)
    p.counter(1,1,3,'east','deepslate');p.put(1,2,3,'handcrafted:golden_thin_pot')
    p.put(1,1,5,'minecraft:smithing_table');p.locker(5,1,6,'Black Gull — customer armour, empty')
    p.shelf(1,2,6,'east');p.put(1,3,6,'handcrafted:stackable_book',facing='east',books=3,seed=4)
    p.put(1,5,5,'handcrafted:dark_oak_cupboard',facing='east',type=2)
    p.put(1,5,3,'handcrafted:dark_oak_bench',facing='east',shape='single',color='red',waterlogged=False)
    p.put(4,5,6,'minecraft:grindstone',face='floor',facing='north')
    for z in(2,3,4):p.put(4,5,z,'mythrais:wrought_iron_railing_01',facing='east',shape=0)
    for x,z,y,face in((2,2,3,'south'),(4,6,3,'north'),(4,6,6,'north')):p.lamp(x,y,z,face)
    p.route([(3,0,z)for z in range(1,7)]+[(4,0,5),(5,0,5)])
    p.route([(3,4,z)for z in range(1,7)]+[(4,4,5),(5,4,5)])
    p.work.append({'position':[1,1,5],'use':'Native armour repair/upgrading station; no spawned armour-stand entities'})
    p.features+=['Tall narrow chamfered armourer with pointed modded glazing and a red upper workshop',
                 'Separate customer counter, reference shelves, upstairs fitting bench/cupboard and usable sharpening station']
    return p


def shipwright(r):
    p=Shop(r,'shipwright',9,13);cells=rect(0,0,6,8)
    p.shell(cells,5,'minecraft:light_gray_terracotta');p.floor(rect(7,2,8,8)|rect(1,9,7,12))
    p.doorway(3,double=True);p.roof(-1,7,-1,9,6,'dark_oak')
    # Open rear rib bench is a small workpiece, not an assembled vessel/physics claim.
    for z in(9,12):
        for x in(1,7):
            for y in range(1,5):p.put(x,y,z,'minecraft:stripped_spruce_log'if y!=3 else'minecraft:polished_deepslate',**({'axis':'y'}if y!=3 else{}))
    for z in(9,12):
        for x in range(1,8):
            if x in(1,4,7):p.put(x,5,z,'minecraft:stripped_dark_oak_log',axis='x')
            else:p.put(x,5,z,'dawnoftimebuilder:dark_oak_pergola',axis_x=True,axis_y=False,axis_z=False,waterlogged=False)
    for x in(1,4,7):
        for z in(10,11):p.put(x,5,z,'dawnoftimebuilder:dark_oak_pergola',axis_x=False,axis_y=False,axis_z=True,waterlogged=False)
    for z in(9,11):
        for x in(3,5):p.stair(x,1,z,'east'if x==3 else'west','spruce')
        p.slab(4,1,z,'spruce')
    p.put(4,1,10,'minecraft:stripped_oak_log',axis='z')
    p.put(1,1,3,'chipped:carpenters_table');p.counter(1,1,6,'east','spruce_planks')
    p.put(1,2,6,'supplementaries:globe_sepia',facing='east',powered=False,rotation=0,waterlogged=False)
    p.locker(5,1,7,'The Wren’s Keel — timber and customer hardware, empty')
    p.shelf(5,2,5,'west');p.put(5,3,5,'handcrafted:stackable_book',facing='west',books=2,seed=2)
    p.put(7,1,4,'minecraft:loom',facing='west');p.put(7,1,6,'handcrafted:dark_oak_bench',facing='west',shape='single',color='brown',waterlogged=False)
    p.window(0,2,5,'west','dark_oak',2);p.window(6,2,2,'east','dark_oak',2)
    p.window(5,4,8,'south','dark_oak',2,brow=False)
    p.lamp(2,3,2,'south');p.lamp(4,3,7,'north')
    for y,part in((1,'lower'),(2,'upper')):
        p.put(2,y,8,'minecraft:dark_oak_door',facing='south',half=part,hinge='left',open=False,powered=False,replace=True)
        p.doors[2,y,8]=p.blocks[2,y,8]
    p.put(2,3,8,AIR,replace=True)
    p.route([(3,0,z)for z in range(1,8)]+[(2,0,7)]+[(2,0,z)for z in range(8,13)])
    p.work.append({'position':[1,1,3],'use':'Native Chipped carpentry station; static small rib jig stays a workpiece'})
    p.features+=['Long sailmaker/shipwright hall with a projecting side clerks’ alcove and an open rear rib-bench yard',
                 'Modeled timber pergola, small fair-ended workpiece, loftless working scale, charts/ledgers and sail-repair loom']
    return p


def tavern(r):
    p=Shop(r,'tavern',11,11);cells=rect(0,0,10,10)-{(0,0),(10,0),(0,10)}
    p.shell(cells,7,'minecraft:brown_terracotta',upper='minecraft:green_terracotta')
    p.floor(rect(1,6,9,9)|{(x,5)for x in range(1,10)},4);p.stair_to_loft(9);p.doorway(5,double=True)
    p.roof(-1,11,-1,11,8,'dark_oak')
    for x in(2,8):p.window(x,2,0,'north',height=4,gothic=True)
    p.window(0,2,5,'west',height=4,gothic=True);p.window(10,5,8,'east','dark_oak',2)
    p.window(5,5,10,'south','dark_oak',2)
    for z in(3,4,5):p.counter(2,1,z,'east');p.put(2,2,z,'supplementaries:goblet',light_level=0,waterlogged=False)
    p.put(1,1,9,'farmersdelight:stove',facing='north',lit=False)
    p.put(1,2,9,'farmersdelight:cooking_pot',facing='north',support='none',waterlogged=False)
    p.locker(2,1,9,'Lantern Wake pantry — empty until supplied')
    p.table(7,1,4,chair_face='north',color='green');p.table(4,1,8,chair_face='south',color='red')
    p.put(7,1,8,'handcrafted:dark_oak_couch',facing='west',shape='single',color='green',waterlogged=False)
    p.put(8,1,9,'handcrafted:dark_oak_side_table',facing='west',color='none',waterlogged=False)
    p.put(8,2,9,'handcrafted:berry_jam_jar',facing='west',jars=2,waterlogged=False)
    p.shelf(1,2,7,'east');p.put(1,3,7,'handcrafted:stackable_book',facing='east',books=3,seed=9)
    p.put(2,5,8,'handcrafted:dark_oak_bench',facing='south',shape='single',color='brown',waterlogged=False)
    p.put(7,5,8,'minecraft:lectern',facing='west',has_book=False,powered=False)
    p.locker(8,5,9,'Guest ledgers and lost property — empty')
    for x in range(1,9):p.put(x,5,5,'mythrais:wrought_iron_railing_01',facing='north',shape=0)
    for x,y,z,face in((4,3,2,'south'),(7,3,2,'south'),(3,3,9,'north'),(7,6,9,'north')):p.lamp(x,y,z,face)
    # Practical projecting hood and deep alternating bracket feet over the two doors.
    for x in range(4,8):p.slab(x,4,-1,'spruce')
    for x in(4,7):p.put(x,3,-1,'mythrais:curved_corbel_dark_oak',facing='north',shape=0)
    p.route([(6,0,z)for z in range(1,10)]+[(x,0,6)for x in range(3,10)])
    p.route([(6,4,z)for z in range(6,10)]+[(x,4,6)for x in range(3,10)]+[(9,4,5)])
    p.features+=['Compact chamfered inn with double-height pointed-window front parlour and a separate rear gallery',
                 'Deep bracketed porch, real galley, conversational tables, book/ledger nook and complete back service routes',
                 'A new original small tavern; no changes to the beloved existing Drowned Rose interior']
    return p


DESIGNS={'florist':florist,'smith':smith,'armoury':armoury,'shipwright':shipwright,'tavern':tavern}


def validate(p):
    if not p.main or not p.work and p.kind!='tavern':raise UserError('A complete actual shop program/work station is required')
    for pos,support in p.lights:
        if key(p.blocks.get(support,AIR))in VOID or support in p.doors:raise UserError('A wall light has no real solid backing: '+str((p.kind,pos,support)))
    for route in p.routes:
        for x,y,z in route:
            value=p.blocks.get((x,y,z),AIR)
            if key(value)in VOID or((x,z)not in p.floors.get(y,set())and not key(value).endswith('_stairs')):
                raise UserError('A claimed shop route has no actual floor: '+str((p.kind,(x,y,z))))
            for dy in(1,2):
                q=x,y+dy,z;v=p.blocks.get(q,AIR)
                if key(v)not in VOID and p.doors.get(q)!=v:raise UserError('A furnished shop blocks its actual two-high route: '+str((p.kind,q,v)))
    candidates={(x,y,z)for y,rows in p.floors.items()for x,z in rows}|set(p.stairs)
    walk={q for q in candidates if key(p.blocks.get(q,AIR))not in VOID and all(key(p.blocks.get((q[0],q[1]+dy,q[2]),AIR))in VOID or p.doors.get((q[0],q[1]+dy,q[2]))==p.blocks.get((q[0],q[1]+dy,q[2]),AIR) for dy in(1,2))}
    if not p.entries:raise UserError('A normal external threshold is required')
    start=p.entries[0];reached={start};queue=deque([start])
    if start not in walk:raise UserError('Normal threshold is not a clear source entry')
    while queue:
        x,y,z=queue.popleft()
        for dx,dz in((1,0),(-1,0),(0,1),(0,-1)):
            for dy in(-1,0,1):
                q=x+dx,y+dy,z+dz
                if q in walk and q not in reached:reached.add(q);queue.append(q)
    if any(q not in reached for path in p.routes for q in path):raise UserError('A complete source room/gallery route is disconnected from the usable entry: '+p.kind)
    for work in p.work:
        x,y,z=work['position']
        if not any((x+dx,y-1,z+dz)in reached for dx,dz in((1,0),(-1,0),(0,1),(0,-1))):
            raise UserError('A real shop work station has no reachable source standing side: '+p.kind)
    rule=require_material_rule(p.blocks,'COMPLETE '+LABELS[p.kind]+' including roof/interior/projections')
    return {'material_rule':rule,'main_columns':len(p.main),'floors':{str(y):len(v)for y,v in p.floors.items()},
            'program_features':p.features,'route_count':len(p.routes),'source_walk_nodes':len(reached),'source_entry_to_room_and_work_access':True,
            'native_visual_collision_or_interaction_acceptance':False}


def local_plans(registry):
    result={}
    for kind,fn in DESIGNS.items():
        p=fn(registry);result[kind]=(p,validate(p))
    return result


def rotate_xz(x,z,width,depth,turn):
    if turn not in(0,1,2,3):raise UserError('Only an explicit orthogonal street-facing rotation is admitted')
    return((x,z),(depth-1-z,x),(width-1-x,depth-1-z),(z,width-1-x))[turn]


def rotate_state(registry,value,turn):
    name=key(value);props=properties(value);faces=('north','east','south','west');out={}
    for prop,choice in props.items():
        dest=faces[(faces.index(prop)+turn)%4]if prop in faces else prop
        if prop in('facing','horizontal_facing')and choice in faces:choice=faces[(faces.index(choice)+turn)%4]
        if prop=='axis'and choice in('x','z')and turn%2:choice='z'if choice=='x'else'x'
        # A globe's5 animation phases are not a standing sign's16 compass
        # headings. Rotate only the actual registered16-heading property.
        if prop=='rotation'and set(registry['blocks'][name].get(prop,()))=={str(n)for n in range(16)}:
            choice=str((int(choice)+turn*4)%16)
        out[dest]=choice
    return state(registry,name,**out)


def world_blocks(p,origin,floor,turn):
    ox,oz=origin
    return{(ox+rotate_xz(x,z,p.width,p.depth,turn)[0],floor+y,oz+rotate_xz(x,z,p.width,p.depth,turn)[1]):rotate_state(p.registry,value,turn)
           for(x,y,z),value in p.blocks.items()}


def prepare_sites(home,output):
    """Exact1m saved supports/full body, still not masterplan/native authority."""
    from tools.artistic_north_bank_east import NorthTerrain,dry_footprint,preservation,NORTH_SOFT
    from tools.artistic_south_forest import SOFT
    from tools.artistic_maritime_depth import admit_owner
    home,output=Path(home).resolve(),Path(output).resolve()
    if home.parent!=Path(r'D:\A World for Two\staging\world-tests')or output.exists()or output.parent!=home/'staging':
        raise UserError('New immediate owned west-quay proposal output required')
    reserve=guard(4*1024**2,16*1024**2);current=read_json(home/'dashboard/settlement/backup-receipt.json')
    admit_owner(home,read_json(home/'dashboard/artistic-owner.json'),current,current['id'],current['sha256'])
    registry=read_json(home/'dashboard/settlement/registry.json');protected,retained_sources=preservation(home,registry)
    zipline_path=home/ZIPLINE_MASK
    if not 0<zipline_path.stat().st_size<=2*1024**2 or digest(zipline_path)!=ZIPLINE_MASK_SHA:raise UserError('Exact future western zipline XYZ reservation required')
    zipline=read_json(zipline_path)
    if str(zipline.get('seed'))!=str(registry['seed'])or zipline.get('world_path')!=registry['world_path']:raise UserError('Future zipline source belongs to another world')
    reserved_xyz={tuple(row[:3])for row in zipline['blocks']}
    reserved={(x,z)for a,b,c,d in RESERVED for x in range(a,c+1)for z in range(b,d+1)}
    terrain=NorthTerrain(home,current,registry);docs={};lots={};union={};all_routes=[];sources=[]
    try:
        for kind,(ox,oz,turn)in PLOTS.items():
            p=DESIGNS[kind](registry);proof=validate(p)
            main={(ox+rotate_xz(x,z,p.width,p.depth,turn)[0],oz+rotate_xz(x,z,p.width,p.depth,turn)[1])for x,z in p.main}
            try:
                if any(x>1216 for x,z in main):raise UserError('Preserve agreed eastern source lane')
                dry=dry_footprint(terrain,main,protected|reserved,max_relief=2);floor=dry['floor_y']
                blocks=world_blocks(p,(ox,oz),floor,turn);before={}
                # A low, patterned footing fills ONLY actual AIR/soft cover above
                # each retained natural ground. Ground below is never cut/replaced.
                for row in dry['actual_dry_columns']:
                    x,gy,z=row['support']
                    for y in range(gy+1,floor):
                        material=('chipped:small_andesite_bricks'if x%4==0 and z%4==0 else'minecraft:polished_andesite'if x%4==0 else'minecraft:chiseled_stone_bricks'if z%4==0 else'minecraft:stone_bricks')
                        blocks[x,y,z]=state(registry,material)
                if len(blocks)>4000:raise UserError('Finite original shop body exceeded')
                for pos,after in blocks.items():
                    x,y,z=pos
                    if(x,z)in protected|reserved or pos in reserved_xyz or x>1216:raise UserError('Actual solid/AIR/eave target touches another accepted or provisional owner: '+str(pos))
                    actual=terrain.state(x,y,z)
                    if actual is None or pos in terrain.entities:raise UserError('Unknown or saved BE in actual full shop field: '+str(pos))
                    if key(actual)not in VOID|SOFT|NORTH_SOFT:raise UserError('Retain saved tree, water or authored object at shop target: '+str((pos,actual)))
                    before[pos]=actual
                    if pos in union:raise UserError('Two west original shop envelopes overlap: '+str(pos))
                require_material_rule(blocks,'COMPLETE saved-supported '+LABELS[kind])
                tagged=[]
                for(x,y,z),nbt in p.tags.items():
                    tx,tz=rotate_xz(x,z,p.width,p.depth,turn);tagged.append({'pos':[ox+tx,floor+y,oz+tz],'nbt':nbt})
                after=payload(registry,current['sha256'],blocks,'PROPOSAL after current work: '+LABELS[kind]);after['block_entities']=tagged;after['construction_forbidden']=True
                old=payload(registry,current['sha256'],before,'VERIFY ONLY exact '+LABELS[kind]+' saved preimage',before=True);old['construction_forbidden']=True
                docs[kind+'-PROPOSAL.json']=after;docs[kind+'-before.json']=old
                routes=[]
                for path in p.routes:
                    rows=[]
                    for x,y,z in path:
                        tx,tz=rotate_xz(x,z,p.width,p.depth,turn);rows.append([ox+tx,floor+y,oz+tz])
                    routes.append(rows);all_routes.append(rows)
                lots[kind]={'status':'SAVED PROPOSAL ONLY','origin':[ox,floor,oz],'turn_quarters':turn,'actual_dry':dry,'proof':proof,'routes':routes,
                            'primary_threshold':routes[next(i for i,path in enumerate(p.routes)if path[0]in p.entries)][0],
                            'world_building_bounds':[min(q[k]for q in blocks)for k in range(3)]+[max(q[k]for q in blocks)for k in range(3)],
                            'complete_interior_exterior_and_native_photos':'PENDING; source composition is not artistic acceptance'}
                union.update(blocks)
            except UserError as error:
                lots[kind]={'status':'REFUSED; preserve exact failure','origin_xz':[ox,oz],'turn_quarters':turn,'reason':str(error),'world_writes':0}
            terrain.check()
        sources=terrain.snapshot.sources.copy()
    finally:terrain.close()
    if union:
        mask={q:AIR for q in union}
        docs['future-solid-AIR-route-reservation-ONLY.json']=payload(registry,current['sha256'],mask,'RESERVATION ONLY west five shops and full body')
        docs['future-solid-AIR-route-reservation-ONLY.json'].update(verification_only=True,construction_forbidden=True)
    raw={name:(json.dumps(doc,separators=(',',':'))+'\n').encode()for name,doc in docs.items()}
    manifest={'format':'awft-west-quay-saved-proposals:1','created':utcnow(),'source_sha256':digest(Path(__file__)),
              'checkpoint_id':current['id'],'checkpoint_sha256':current['sha256'],'lots':lots,'retained_sources':retained_sources,
              'saved_sources':sources,'shared_reserved_rectangles':list(RESERVED),'agreed_split_x':1216,'native_actions':0,'world_writes':0,
              'future_zipline_reservation':{'relative':ZIPLINE_MASK,'sha256':ZIPLINE_MASK_SHA,'source_only':True,'observed_AIR_authority':False},
              'construction_forbidden':True,'phase':'AFTER current fountain/forest/zipline/firstLIFE and explicit masterplan review; LIFE again only after expansion construction',
              'new_land_flattened_or_water_filled':0,'storage_guard':reserve,'all_five_saved_fields_qualified':all(v['status']=='SAVED PROPOSAL ONLY'for v in lots.values()),
              'next_gates':['Agree exact dense lane/court connections with masterplan owner','Qualify every external threshold and public2..3m approach on actual saved dry1m terrain',
                            'Inspect current main-town preservation, provisional zipline masks and full growth skirts','Review real native preimages/place/settle/full state and inventory proofs after earlier work',
                            'Review eye-level alleys, each exterior and complete furnished room; source counts are not quality','Expand LIFE only after accepted construction'],
              'files':{name:{'bytes':len(value),'sha256':hashlib.sha256(value).hexdigest()}for name,value in raw.items()}}
    raw['manifest.json']=(json.dumps(manifest,indent=2)+'\n').encode()
    if sum(map(len,raw.values()))>16*1024**2:raise UserError('Finite saved west-shop output exceeded')
    if read_json(home/'dashboard/settlement/backup-receipt.json').get('sha256')!=current['sha256']:raise UserError('Checkpoint advanced during the immutable read; retain old proposal inputs and rebind later')
    output.mkdir()
    for name,data in raw.items():(output/name).write_bytes(data)
    return {'output':str(output),'manifest_sha256':digest(output/'manifest.json'),'lots':{k:{'status':v['status'],'reason':v.get('reason')}for k,v in lots.items()},'native_actions':0}


def prepare_local(registry_path,output):
    """Bounded world-unbound originals; no coordinate/ground/preimage fiction."""
    output=Path(output).resolve()
    if output.exists():raise UserError('New local composition output required')
    if output.drive.lower()not in('c:','d:'):raise UserError('An explicitly bounded local C: or D: output is required')
    reserve=guard((20 if output.drive.lower()=='c:'else 4)*1024**2,16*1024**2 if output.drive.lower()=='d:'else 0)
    registry=read_json(registry_path);plans=local_plans(registry)
    docs={}
    for kind,(p,proof)in plans.items():
        docs[kind+'.json']={'format':'awft-original-local-shop:1','name':LABELS[kind],'source_sha256':digest(Path(__file__)),
            'width':p.width,'depth':p.depth,'main_outline':[list(q)for q in sorted(p.main)],
            'blocks':[[*q,v]for q,v in sorted(p.blocks.items())],'block_entities':[{'pos':list(q),'nbt':s}for q,s in p.tags.items()],
            'routes':[[list(q)for q in path]for path in p.routes],'features':p.features,'work_stations':p.work,'proof':proof,
            'world_origin':None,'actual_saved_ground_or_preimage':False,'construction_forbidden':True}
    raw={name:(json.dumps(d,separators=(',',':'))+'\n').encode()for name,d in docs.items()}
    manifest={'format':'awft-west-quay-local-compositions:1','created':utcnow(),'source_sha256':digest(Path(__file__)),
              'registry_sha256':digest(registry_path),'native_actions':0,'world_writes':0,'construction_forbidden':True,
              'plot_authority':'None until actual one-metre dry support/body/source protection and agreed masterplan binding',
              'reserve':reserve,'files':{n:{'bytes':len(v),'sha256':hashlib.sha256(v).hexdigest()}for n,v in raw.items()}}
    raw['manifest.json']=(json.dumps(manifest,indent=2)+'\n').encode()
    if sum(map(len,raw.values()))>16*1024**2:raise UserError('Finite local shop source output exceeded')
    output.mkdir()
    for name,data in raw.items():(output/name).write_bytes(data)
    return {'output':str(output),'manifest_sha256':digest(output/'manifest.json'),'native_actions':0,'world_writes':0}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--registry',type=Path);parser.add_argument('--home',type=Path);parser.add_argument('--output',type=Path,required=True)
    a=parser.parse_args()
    if bool(a.home)==bool(a.registry):parser.error('Choose either exact --home saved binding or --registry local compositions')
    print(json.dumps(prepare_sites(a.home,a.output)if a.home else prepare_local(a.registry,a.output),indent=2))
