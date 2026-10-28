"""Three original, tightly interlocking western pirate frontages for native review.

This is a new design, not a recolor or replay of the rejected north-town builder.
Construction remains private/proposed until an exact stopped preimage is admitted.
No world calls, runtime commands, inventory moves or old-house demolition occur.
"""
from __future__ import annotations

import argparse
from collections import Counter, deque
import hashlib
import json
from pathlib import Path
import time

from control_room.common import UserError, digest, read_json
from tools.artistic_spawn_plaza import state
from tools.artistic_materials import material_runs, require_material_rule
from tools.artistic_mill_detail import joined_window_part
from tools.artistic_neighborhood_roofs import ridge_part
from tools.settlement_attractions import properties

AIR = 'minecraft:air'
MIB = 1024**2
LABELS = ('The Bent Wick', 'Widow Finch’s Cooperage', 'The Ragged Sail')
VEC = {'north': (0,-1), 'south': (0,1), 'west': (-1,0), 'east': (1,0)}
MAX_CELLS = 12000
DEFAULT_ORIGIN = (1072,64,-1273)


def rect(x0,z0,x1,z1):
    return {(x,z) for x in range(x0,x1+1) for z in range(z0,z1+1)}


def edge(cells):
    return {q for q in cells if any((q[0]+dx,q[1]+dz) not in cells for dx,dz in VEC.values())}


def key(s):
    return s.split('[',1)[0]


class Frontage:
    """Small pure geometry model with explicit routes and authored story objects."""
    def __init__(self, registry, origin=DEFAULT_ORIGIN):
        self.registry, self.origin = registry, tuple(origin)
        self.blocks, self.tags, self.owners, self.floors = {}, {}, {}, {}
        self.main, self.levels, self.routes = {}, {}, []
        self.props, self.supports, self.roof_sections = [], [], []
        self.rooms, self.features, self.entries = [], {}, []
        self.owner = LABELS[0]

    def put(self,x,y,z,name,*,role=None,**props):
        if any(type(v) is not int for v in (x,y,z)) or not (-4<=x<=19 and -2<=z<=25 and -1<=y<=19):
            raise UserError('The small three-frontage source escaped its finite envelope')
        q=(x,y,z);value=state(self.registry,name,**props)
        old=self.blocks.get(q,AIR);other=self.owners.get(q,self.owner)
        if other!=self.owner and key(old)!=AIR and key(value)!=AIR and old!=value:
            raise UserError('Distinct authored masses overlap: '+str((q,other,self.owner)))
        self.blocks[q]=value;self.owners[q]=self.owner;self.tags.pop(q,None)
        if role:self.props.append({'position':list(q),'owner':self.owner,'role':role,'block':key(value)})
        if len(self.blocks)>MAX_CELLS:raise UserError('Finite three-frontage cell budget exceeded')

    def slab(self,x,y,z,wood='dark_oak',*,half='top',role=None):
        self.put(x,y,z,'minecraft:'+wood+'_slab',type=half,waterlogged=False,role=role)

    def stair(self,x,y,z,face,wood='dark_oak',*,half='bottom',role=None):
        self.put(x,y,z,'minecraft:'+wood+'_stairs',facing=face,half=half,shape='straight',waterlogged=False,role=role)

    def beam(self,x,y,z,axis='x',wood='charred_spruce',*,role=None):
        self.put(x,y,z,'dawnoftimebuilder:'+wood+'_beam',axis_x=axis=='x',axis_y=axis=='y',axis_z=axis=='z',bottom=True,waterlogged=False,role=role)

    def floor(self,cells,y):
        self.floors.setdefault((self.owner,y),set()).update(cells)
        # Broad boards run lengthwise between actual narrow joists. Perimeter
        # end-grain and side sleepers have their own coherent construction IDs.
        x0=min(x for x,z in cells)
        for x,z in sorted(cells):
            if (x,z-1) not in cells or (x,z+1) not in cells:
                name='minecraft:dark_oak_planks';props={}
            elif (x-1,z) not in cells or (x+1,z) not in cells:
                name='minecraft:stripped_spruce_wood';props={'axis':'z'}
            elif (x-x0)%4==0:
                name='minecraft:dark_oak_wood';props={'axis':'z'}
            else:name='minecraft:spruce_planks';props={}
            self.put(x,y,z,name,**props)

    def walls(self,cells,floor,panel,*,height=3):
        e=edge(cells)
        x0=min(x for x,z in cells);z0=min(z for x,z in cells)
        for x,z in sorted(e):
            along_x=(x-1,z) in e and (x+1,z) in e
            along_z=(x,z-1) in e and (x,z+1) in e
            post=not(along_x or along_z) or ((x-x0)%4==0 if along_x else (z-z0)%4==0)
            for dy in range(1,height+1):
                if dy%4==0:
                    self.beam(x,floor+dy,z,'x' if along_x else 'z',wood='charred_spruce' if along_x else 'dark_oak')
                elif post:self.put(x,floor+dy,z,'minecraft:stripped_dark_oak_log',axis='y')
                else:self.put(x,floor+dy,z,panel)

    def route(self,name,positions,*,kind='floor'):
        self.routes.append({'id':name,'owner':self.owner,'kind':kind,'positions':[list(q) for q in positions]})

    def reserve(self,name,positions):
        """A room's real two-high circulation is set before furnishing it."""
        positions=list(positions)
        for x,y,z in positions:
            for dy in (0,1):self.put(x,y+dy,z,AIR)
        self.route(name,positions)

    def room(self,title,level,point,story):
        self.rooms.append({'owner':self.owner,'name':title,'floor':level,'standing_point':list(point),'story':story})

    def window(self,x,y,z,face,*,width=2,height=2,hood='beam',cut_start=False):
        dx,dz=VEC[face];tx,tz=(1,0) if dz else (0,1)
        plane='north' if dz else 'east'
        for n in range(width):
            for h in range(height):
                self.put(x+n*tx,y+h,z+n*tz,'mcwwindows:dark_oak_plank_window',facing=plane,part='base')
        # Projected hood and side knees are held by the actual wall head; no
        # waist-high planters intrude into the two-metre alley below them.
        for n in range(0 if cut_start else -1,width+1):
            q=(x+n*tx+dx,y+height,z+n*tz+dz)
            if hood=='slant':
                self.put(*q,'dawnoftimebuilder:charred_spruce_roof_support',facing=face,shape='straight',type='top',waterlogged=False)
            else:self.beam(*q,'x' if tx else 'z',wood='charred_spruce' if tx else 'dark_oak')
            self.supports.append({'detail':list(q),'support':[q[0]-dx,q[1],q[2]-dz],'role':'small supported window eyebrow'})
        for n in ((width,) if cut_start else (-1,width)):
            self.put(x+n*tx+dx,y+height-1,z+n*tz+dz,'mythrais:curved_corbel_dark_oak',facing=face,shape=0)

    def door(self,x,z,face):
        inward={'north':'south','south':'north','west':'east','east':'west'}[face]
        for dy,half in ((1,'lower'),(2,'upper')):
            self.put(x,dy,z,'mcwdoors:dark_oak_cottage_door',facing=inward,half=half,hinge='left',open=False,powered=False)
        dx,dz=VEC[face]
        self.stair(x+dx,0,z+dz,inward,'stone_brick',role='single normal half-step threshold')
        self.entries.append({'owner':self.owner,'door':[x,1,z],'outward':face,'outside_step':[x+dx,0,z+dz]})

    def sign(self,x,y,z,face,lines):
        self.put(x,y,z,'minecraft:dark_oak_wall_sign',facing=face,waterlogged=False,role='waxed hand-lettered trade sign')
        messages=[json.dumps(json.dumps({'text':line,'color':'black'})) for line in (list(lines)+['']*4)[:4]]
        self.tags[x,y,z]='{is_waxed:1b,front_text:{messages:['+','.join(messages)+'],color:"black",has_glowing_text:0b}}'

    def lamp(self,x,y,z,face,role='small supported warm wall lantern'):
        self.put(x,y,z,'mcwlights:tavern_wall_lantern',facing=face,role=role)
        dx,dz=VEC[face];self.supports.append({'detail':[x,y,z],'support':[x-dx,y,z-dz],'role':role})

    def shelf(self,x,y,z,face='east',*,books=False):
        self.put(x,y,z,'handcrafted:dark_oak_shelf',facing=face,shape='single',type=3,role='trade-specific wall storage')
        self.put(x,y+1,z,'handcrafted:stackable_book' if books else 'handcrafted:wood_cup',
                 **({'facing':face,'books':3,'seed':11} if books else {'facing':face,'pieces':3,'waterlogged':False}),
                 role='shipping ledgers' if books else 'small workroom vessels')

    def counter(self,x,y,z,face='east',top='dark_oak_planks',role='work counter'):
        self.put(x,y,z,'handcrafted:dark_oak_counter',facing=face,counter=top,type=1,role=role)

    def table(self,x,y,z,face='north'):
        self.put(x,y,z,'handcrafted:dark_oak_table',color='none',shape='single',waterlogged=False,role='small shared supper/work table')
        dx,dz=VEC[face]
        self.put(x-dx,y,z-dz,'handcrafted:dark_oak_chair',facing=face,color='brown',waterlogged=False,role='usable normal chair')
        self.put(x,y+1,z,'handcrafted:wood_cup',facing=face,pieces=2,waterlogged=False,role='cups left after supper')

    def bed(self,x,y,z,face='north'):
        dx,dz=VEC[face]
        self.put(x,y,z,'minecraft:brown_bed',facing=face,part='foot',occupied=False,role='real usable bed')
        self.put(x+dx,y,z+dz,'minecraft:brown_bed',facing=face,part='head',occupied=False)

    def stair_flight(self,x,start_z,floor):
        path=[]
        for n in range(4):
            z=start_z-n;y=floor+1+n
            for h in (1,2,3):self.put(x,y+h,z,AIR)
            self.stair(x,y,z,'north',role='normal accessible stair flight')
            path.append((x,y+1,z))
        self.put(x,floor+4,start_z-4,'minecraft:dark_oak_planks')
        path.append((x,floor+5,start_z-4));self.route(self.owner+' stair '+str(floor),path,kind='stairs')

    def roof(self,box,base,profile,*,family='dark_oak',hip_south=False,annex=False):
        x0,z0,x1,z1=box
        if len(profile)!=x1-x0+1:raise UserError('An authored roof section needs its actual cross profile')
        material='mcwroofs:'+family+('_lower_roof' if annex else '_roof')
        ridge='mcwroofs:'+family+'_top_roof';peak=max(profile)
        self.roof_sections.append({'owner':self.owner,'bounds_xz':list(box),'eave_y':base,'cross_profile':list(profile),'family':family,'southern_half_hip':hip_south,'actual_annex_level_change':annex})
        for x in range(x0,x1+1):
            for z in range(z0,z1+1):
                rise=profile[x-x0]
                clipped=hip_south and z1-z+1<rise
                if hip_south:rise=min(rise,z1-z+1)
                y=base+rise
                if rise==peak and profile[x-x0]==peak and not annex:
                    self.put(x,y,z,ridge,part='switched_0')
                else:
                    face='east' if x-x0<(x1-x0+1)/2 else 'west'
                    if hip_south and z1-z+1<profile[x-x0]:face='north'
                    covering='mcwroofs:'+family+'_lower_roof' if clipped else material
                    self.put(x,y,z,covering,facing=face,half='bottom',shape='straight')
        # Closed, framed gable heads belong to the roof's actual shape. No
        # bright horizontal structural seams have been introduced to break runs.
        for end in (z0+1,z1-1):
            for x in range(x0+1,x1):
                rise=profile[x-x0]
                if hip_south:rise=min(rise,z1-end+1)
                for dy in range(max(0,rise)):
                    yy=base+dy
                    if (x-x0)%4==0:
                        if dy%4==3:self.beam(x,yy,end,'x')
                        else:self.put(x,yy,end,'minecraft:stripped_dark_oak_log',axis='y')
                    else:self.put(x,yy,end,'chipped:detailed_dark_oak_planks' if dy%4==3 else 'minecraft:gray_terracotta')


def wick(p):
    p.owner=LABELS[0]
    ground=rect(0,1,7,10)-{(0,1),(0,2)}
    upper=ground|rect(0,11,3,11)
    p.main[p.owner]=ground;p.levels[p.owner]=[ground,upper]
    for x,z in ground|upper:
        for y in range(1,12):p.put(x,y,z,AIR)
    for f,cells in ((0,ground),(4,upper)):
        p.floor(cells,f);p.walls(cells,f,'minecraft:gray_terracotta' if f==0 else 'minecraft:light_gray_terracotta')
    # A narrow rear lean-to roof drops one metre, rather than coloring every
    # fourth roof course. Its visible junction creates the irregular silhouette.
    p.roof((-1,0,8,7),8,(0,1,2,3,4,4,3,2,1,0),family='dark_oak')
    p.roof((0,8,7,11),8,(0,1,2,3,3,2,1,0),family='dark_oak',annex=True)
    p.window(1,1,10,'south',hood='slant')
    p.window(1,5,11,'south',hood='beam')
    p.window(0,2,5,'west',hood='slant')
    p.door(5,10,'south')
    # Small braced porch, only one metre deep; the main two-wide bend is sky-open.
    for x in (4,6):
        for y in range(1,4):p.put(x,y,11,'dawnoftimebuilder:charred_spruce_timber_frame_pillar',axis='y')
        p.put(x,3,12,'mythrais:curved_corbel_dark_oak',facing='south',shape=0)
    for x in range(4,7):p.slab(x,4,11)
    p.sign(6,3,10,'south',["The Bent Wick",'Oil • Rope • Wick'])
    p.lamp(3,3,11,'south');p.lamp(1,2,7,'east')
    p.reserve('Wick shop circulation',[(5,1,z) for z in range(4,11)]+[(4,1,6),(3,1,6)])
    p.reserve('Wick upstairs circulation',[(5,5,z) for z in range(4,10)]+[(4,5,6),(3,5,6)])
    for f in (0,4):
        # Exposed half-height joists articulate the actual ceiling; no hanging
        # fixture below normal player head height or giant chandelier is used.
        for z in (3,7):
            for x in range(1,5):p.slab(x,f+3,z,role='exposed shallow ceiling joist')
    p.stair_flight(6,8,0)
    for z in (3,4,5):p.counter(1,1,z,role='oil blending and wick packing bench')
    p.put(2,1,2,'minecraft:crafting_table',role='real repair work station')
    p.put(3,1,2,'minecraft:barrel',facing='up',open=False,role='new empty oil-shop stock barrel')
    p.put(2,2,2,'supplementaries:hourglass',facing='up',light_level=0,waterlogged=False,role='blending timer')
    p.shelf(1,2,8,'east');p.shelf(3,2,2,'south',books=True)
    p.put(2,1,9,'handcrafted:dark_oak_drawer',facing='south',shape='single',type=2,role='wicks and shipping tools')
    p.put(2,2,9,'supplementaries:candle_holder',candles=3,face='floor',facing='south',lit=True,waterlogged=False,role='display of finished candles')
    p.put(3,1,8,'handcrafted:dark_oak_chair',facing='north',color='none',waterlogged=False,role='shopkeeper chair')
    p.bed(1,5,3)
    p.put(2,5,2,'handcrafted:dark_oak_nightstand',facing='south',color='none',waterlogged=False,role='bedside belongings')
    p.put(1,5,8,'minecraft:smoker',facing='east',lit=False,role='real small cooking hearth')
    p.counter(2,5,8,'south');p.put(2,6,8,'farmersdelight:cutting_board',facing='south',waterlogged=False,role='supper preparation')
    p.table(3,5,5,'east');p.shelf(1,6,5,'east',books=True)
    p.put(1,5,7,'farmersdelight:dark_oak_cabinet',facing='east',open=False,role='new empty kitchen pantry')
    p.lamp(1,6,7,'east');p.lamp(3,6,10,'north')
    p.room('Wick and oil workshop',0,(3,1,6),'A narrow packing counter, cups, timer, candle display, tools and repair table face a broad lantern-lit shop window.')
    p.room('Chandler’s upstairs home',4,(3,5,6),'A real bed, bedside storage, small cooking hearth and supper table sit beneath shallow visible joists.')
    p.features[p.owner]=['Bent two-storey footprint with a one-metre upper jetty','Stepped dark-oak roof and lower rear roof, no colored seams','Broad supported fancy shop glazing and braced recessed porch','Two independently furnished reachable rooms']


def cooper(p):
    p.owner=LABELS[1]
    ground=rect(9,3,16,13)-{(16,3),(16,4),(9,13)}
    middle=ground|rect(11,14,14,14)
    top=ground-{(9,3),(10,3)}
    p.main[p.owner]=ground;p.levels[p.owner]=[ground,middle,top]
    for x,z in ground|middle:
        for y in range(1,16):p.put(x,y,z,AIR)
    for f,cells in ((0,ground),(4,middle),(8,top)):
        p.floor(cells,f);p.walls(cells,f,'minecraft:light_gray_terracotta' if f==0 else 'minecraft:brown_terracotta')
    p.roof((8,2,17,14),12,(0,1,2,3,4,4,3,2,1,0),family='deepslate')
    p.window(9,1,5,'west',hood='beam')
    p.window(9,5,7,'west',height=2,width=2,hood='beam')
    p.window(12,5,14,'south',width=2,hood='slant')
    for x in range(11,15):p.slab(x,8,14,role='small supported south-bay roof')
    p.window(9,9,7,'west',width=2,height=2,hood='beam')
    p.door(9,11,'west');p.sign(9,3,10,'west',['Finch’s Cooperage','Hoops • Casks • Repairs'])
    p.lamp(8,3,12,'west');p.lamp(15,2,5,'west')
    for f in (0,4,8):
        p.reserve('Cooper circulation '+str(f),[(14,f+1,z) for z in range(7,12)]+[(x,f+1,11) for x in range(9,14)]+[(12,f+1,10)])
        for z in (6,10):
            for x in range(10,14):p.slab(x,f+3,z,'spruce',role='modeled coffer edge over work/living bay')
    p.stair_flight(15,11,0);p.stair_flight(15,11,4)
    for z in (5,6,7):p.counter(10,1,z,role='cooper’s cask repair and hoop bench')
    p.put(11,1,4,'minecraft:barrel',facing='up',open=False,role='new empty unfinished cask')
    p.put(12,1,4,'minecraft:barrel',facing='up',open=False,role='new empty finished cask')
    p.put(13,1,4,'minecraft:grindstone',face='floor',facing='south',role='real hand-tool sharpening')
    p.put(12,1,6,'minecraft:crafting_table',role='real cooper work table')
    p.put(12,2,6,'supplementaries:jar',facing='west',light_level=0,waterlogged=False,role='glue pot on the repair table')
    p.shelf(10,2,9,'east',books=True);p.shelf(13,2,4,'south')
    p.put(10,1,12,'handcrafted:dark_oak_bench',facing='east',shape='single',color='brown',waterlogged=False,role='customer waiting bench')
    p.counter(10,5,12,'north');p.put(11,5,12,'farmersdelight:dark_oak_cabinet',facing='north',open=False,role='new empty home pantry')
    p.put(10,5,8,'minecraft:furnace',facing='east',lit=False,role='real compact enclosed hearth')
    p.put(10,5,9,'handcrafted:dark_oak_couch',color='brown',facing='east',shape='single',waterlogged=False,role='small fireside reading seat')
    p.table(12,5,8,'north');p.shelf(10,6,5,'east',books=True)
    p.put(12,5,5,'minecraft:bookshelf',role='family’s wall bookcase')
    p.lamp(10,6,7,'east');p.lamp(11,6,4,'south')
    p.bed(10,9,6)
    p.put(11,9,4,'handcrafted:dark_oak_nightstand',facing='south',color='none',waterlogged=False,role='sailor’s bedside locker')
    p.put(12,9,5,'handcrafted:dark_oak_desk',facing='south',color='none',waterlogged=False,role='upper chart and ledger desk')
    p.put(12,10,5,'handcrafted:stackable_book',facing='south',books=2,seed=7,role='shipping and tide ledgers')
    p.put(13,9,5,'handcrafted:dark_oak_chair',facing='west',color='brown',waterlogged=False,role='desk chair')
    p.put(10,9,10,'minecraft:cartography_table',role='real charting work station')
    p.put(10,10,10,'supplementaries:globe_sepia',facing='east',rotation=0,powered=False,waterlogged=False,role='small navigator’s globe')
    p.shelf(10,10,8,'east',books=True);p.lamp(13,10,12,'north')
    p.room('Cooper’s repair room',0,(12,1,10),'Hoop bench, actual casks, sharpening stone, tools, job ledgers and customer bench form one compact workshop.')
    p.room('Finch family parlour',4,(12,5,10),'An enclosed hearth, reading seat, pantry and supper table occupy a visibly separate upper home.')
    p.room('Sailor’s chart attic',8,(12,9,10),'A tucked bed and ledger desk face the taller side casement; charts, globe and books tell the family’s sea-going story.')
    p.features[p.owner]=['Taller narrow mass shifted two metres behind the chandler','West-facing door and supported projecting side bay turn the frontage around the bend','Continuous charcoal roof with high filled gables','Three different reachable trade/home/attic rooms']


def sail(p):
    p.owner=LABELS[2]
    main=rect(-2,14,6,23)-{(-2,14),(-2,15),(-1,14),(6,23)}
    loft=rect(0,16,4,21)
    p.main[p.owner]=main;p.levels[p.owner]=[main,loft]
    for x,z in main:
        for y in range(1,10):p.put(x,y,z,AIR)
    p.floor(main,0);p.walls(main,0,'chipped:boxed_dark_oak_planks',height=5)
    p.floor(loft,4)
    p.roof((-3,13,7,24),5,(0,1,2,3,4,4,4,3,2,1,0),family='spruce',hip_south=True)
    p.window(6,1,15,'east',width=2,hood='slant')
    p.window(0,1,14,'north',width=3,hood='beam',cut_start=True)
    p.door(6,21,'east');p.sign(6,3,20,'east',['The Ragged Sail','Mending • Canvas • Flags'])
    # One small dormer cuts a real opening into the east roof, rather than a
    # colored patch painted onto the existing slope. Its floor is over headroom.
    for x in range(5,8):
        for z in range(17,21):
            p.put(x,4,z,'minecraft:dark_oak_wood',axis='z')
            for y in range(5,8):p.put(x,y,z,AIR)
    for z in (17,20):
        for x in range(5,8):
            for y in (5,6,7):p.put(x,y,z,'minecraft:stripped_spruce_log',axis='y')
        p.put(7,4,z,'mythrais:curved_corbel_dark_oak',facing='east',shape=0)
    for z,h in ((17,1),(18,2),(19,2),(20,1)):
        for y in range(8,8+h):p.beam(7,y,z,'z',wood='dark_oak')
    p.window(7,6,18,'east',width=2,height=2,hood='slant')
    for x in range(5,9):
        for z,h in ((16,0),(17,1),(18,2),(19,2),(20,1),(21,0)):
            p.put(x,8+h,z,'mcwroofs:spruce_lower_roof',facing='south' if z<=18 else 'north',half='bottom',shape='straight')
    p.reserve('Sail workroom circulation',[(5,1,z) for z in range(17,23)]+[(x,1,22) for x in range(0,6)]+[(2,1,21)])
    p.reserve('Sail loft circulation',[(3,5,z) for z in range(17,22)]+[(2,5,18),(1,5,18)])
    p.stair_flight(4,21,0)
    for x in range(-1,4):p.slab(x,3,17,'spruce',role='shallow workroom ceiling rib')
    for x in (-1,0,1):
        p.counter(x,1,16,'south',role='continuous canvas cutting and stitching table')
    p.put(0,2,16,'farmersdelight:cutting_board',facing='south',waterlogged=False,role='cloth cutting layout board')
    p.put(-1,1,19,'minecraft:loom',facing='east',role='real sail and flag loom')
    p.put(-1,1,20,'farmersdelight:dark_oak_cabinet',facing='east',open=False,role='new empty folded-canvas cabinet')
    p.shelf(-1,2,18,'east');p.shelf(4,2,15,'south',books=True)
    p.put(1,1,19,'handcrafted:dark_oak_table',shape='single',color='none',waterlogged=False,role='separate pattern drawing table')
    p.put(1,1,20,'handcrafted:dark_oak_chair',facing='north',color='brown',waterlogged=False,role='sailmaker’s chair')
    p.put(1,2,19,'handcrafted:stackable_book',facing='east',books=2,seed=5,role='flag patterns and order book')
    p.put(2,1,15,'minecraft:barrel',facing='up',open=False,role='new empty canvas offcut barrel')
    p.put(3,1,15,'handcrafted:dark_oak_chair',facing='south',color='none',waterlogged=False,role='spare work chair')
    p.lamp(5,3,19,'west');p.lamp(-1,2,21,'east')
    p.bed(0,5,20)
    p.put(0,5,17,'handcrafted:dark_oak_nightstand',facing='south',color='none',waterlogged=False,role='sail loft bedside locker')
    p.put(2,5,16,'minecraft:bookshelf',role='low bookcase below the sloping roof')
    p.put(2,6,16,'handcrafted:terracotta_thin_pot',role='quiet glazed keepsake')
    p.lamp(5,6,20,'west')
    p.room('Sail cutting workroom',0,(2,1,21),'A real loom, cutting and pattern tables, canvas cabinet, order shelf, cups and low wall lamps make a fully used workshop.')
    p.room('Sailmaker’s low loft',4,(1,5,18),'A compact reachable sleeping loft, low bookcase and lanterned dormer contrast with the cooper’s tall attic.')
    p.features[p.owner]=['Low chamfered mass turns its door east toward the two-metre alley','Half-hipped warm muted roof and one true small glazed dormer','Sail workshop has actual usable loom and cutting facilities','Low loft and restrained lighting preserve normal player headroom']


def lane(p):
    p.owner='Crooked Wick Bend'
    # The bend is one compact linked street, not a grid rectangle or a lawn.
    # A real retained four-cell pottery barrow sits at x7..10,z18. Two-wide
    # walking bends around it; its post, pots, table and lamp are not erased.
    bend=rect(8,14,9,16)|rect(8,16,12,17)|rect(11,16,12,20)|rect(8,19,12,20)|rect(8,19,9,22)
    paving=rect(-2,11,8,13)|bend|{(9,13),(7,21)}
    clear=rect(-2,12,8,13)|bend|{(9,13)}
    for x,z in sorted(paving):
        drain=(z==13 and x<=3) or (x==12 and 17<=z<=20)
        material='minecraft:cobbled_deepslate' if drain else 'minecraft:andesite'
        p.put(x,-1,z,material)
        for y in (0,1,2):p.put(x,y,z,AIR)
    # Designed junction/end stones; not alternating roof or paving stripes.
    for x,z in ((-2,11),(-2,12),(-2,13),(7,13),(8,13),(8,22),(9,22)):
        p.put(x,-1,z,'minecraft:polished_andesite')
    p.route('Two-wide public L bend',[(x,0,z) for x,z in sorted(clear)],kind='public-two-wide')
    p.features[p.owner]=['Three-wide main turn with a two-wide clear core','Two-wide continuing alley, fronts offset and facing different directions','A narrow proper drainage edge and restrained junction stones replace bare lawn strips']


def canonical_joins(p):
    """Actual pinned window/ridge algorithms on the COMPLETE final mask."""
    field=dict(p.blocks);changes=[]
    for q,value in sorted(field.items()):
        name=key(value);x,y,z=q;props=properties(value)
        if name.startswith('mcwwindows:') and name.endswith('_plank_window'):
            same=lambda other:key(field.get(other,AIR))==name
            neg,pos=((x-1,y,z),(x+1,y,z)) if props['facing']=='north' else ((x,y,z-1),(x,y,z+1))
            props['part']=joined_window_part(same((x,y+1,z)),same((x,y-1,z)),same(neg),same(pos))
        elif name.startswith('mcwroofs:') and name.endswith('_top_roof'):
            props['part']=ridge_part(*(key(field.get(other,AIR))==name for other in ((x,y,z-1),(x+1,y,z),(x,y,z+1),(x-1,y,z))))
        else:continue
        new=state(p.registry,name,**props)
        if new!=value:changes.append({'position':list(q),'before':value,'after':new})
        p.blocks[q]=new
    return changes


def construct(registry,origin=DEFAULT_ORIGIN):
    p=Frontage(registry,origin)
    lane(p);wick(p);cooper(p);sail(p)
    p.join_derivations=canonical_joins(p)
    return p


def check(p):
    rules=[]
    for label in LABELS:
        field={q:s for q,s in p.blocks.items() if p.owners[q]==label}
        rules.append(require_material_rule(field,'WEST R2 COMPLETE '+label))
    errors=[]
    for route in p.routes:
        for q in route['positions']:
            x,y,z=q
            for h in (0,1):
                actual=p.blocks.get((x,y+h,z),AIR)
                if actual!=AIR and not key(actual).endswith('_door'):
                    errors.append((route['id'],[x,y+h,z],actual))
            if route['kind']!='stairs':
                floor=p.blocks.get((x,y-1,z),AIR)
                if floor==AIR:errors.append((route['id'],[x,y-1,z],'missing authored walking support'))
    if errors:raise UserError('Preserve real route/headroom: '+str(errors[:12]))
    for row in p.supports:
        backing=p.blocks.get(tuple(row['support']),AIR)
        if backing==AIR:raise UserError('A modeled hood or lamp has no actual authored backing: '+str(row))
    if len(p.rooms)!=7 or len(p.entries)!=3:raise UserError('All three original stories and seven rooms are required')
    return {'material_rules':rules,'actual_cell_count':len(p.blocks),'rooms':len(p.rooms),'three_front_directions':[r['outward'] for r in p.entries],
            'purposeful_story_objects':len(p.props),'route_headroom_checked':sum(len(r['positions']) for r in p.routes),
            'canonical_native_join_expectations':len(p.join_derivations),'source_only':True,'native_walks_rendering_and_owner_acceptance':'PENDING'}


def geometry_digest(p):
    return hashlib.sha256(json.dumps([[*q,s] for q,s in sorted(p.blocks.items())],separators=(',',':')).encode()).hexdigest()


def source_bundle(registry,output,origin=DEFAULT_ORIGIN):
    """A review bundle is NOT admitted to place and contains no saved preimage."""
    from tools.playtest import guard
    reserve=guard(4*MIB,16*MIB);output=Path(output).resolve()
    if output.exists() or not output.is_relative_to(Path('D:/A World for Two/staging').resolve()):raise UserError('New unique private source-review folder required')
    p=construct(registry,origin);proof=check(p)
    ox,oy,oz=p.origin
    manifest={'format':'awft-west-r2-three-frontage-source:1','source_sha256':digest(Path(__file__)),'geometry_sha256':geometry_digest(p),'origin':list(p.origin),
        'building_names':list(LABELS),'building_main_footprints':{k:[[x+ox,z+oz] for x,z in sorted(v)] for k,v in p.main.items()},
        'rooms':p.rooms,'features':p.features,'entries':p.entries,'routes':p.routes,'story_objects':p.props,'supports':p.supports,'roof_sections':p.roof_sections,
        'proof':proof,'hard_preservation':['All original accepted town sections','All actual existing inventories and postvisit human changes','Placed western V2 stations/frames/14-stock barrel and full flight clearance','The full river and bridge navigation envelope'],
        'palette_reason':'Measured dark timber, worn gray masonry and muted plaster of the accepted original small pirate lanes; no periodic bright roof bands',
        'status':'SOURCE REVIEW ONLY — fresh stopped checkpoint, exact dry/support/body and current native before admission, then actual three-building native preview required before replication',
        'reserve_guard':reserve,'native_actions':0,'world_writes':0,'inventory_moved':0,'old_house_demolition':0}
    documents={'source-model-LOCAL-ONLY.json':{'blocks':[[*q,s] for q,s in sorted(p.blocks.items())],'tags':[[*q,s] for q,s in sorted(p.tags.items())],'not_a_native_plan':True},'manifest.json':manifest}
    raw={n:(json.dumps(d,separators=(',',':'))+'\n').encode() for n,d in documents.items()}
    if sum(map(len,raw.values()))>16*MIB:raise UserError('Source-review output allocation exceeded')
    output.mkdir()
    for n,b in raw.items():(output/n).open('xb').write(b)
    return {'folder':str(output),'manifest_sha256':digest(output/'manifest.json'),'geometry_sha256':manifest['geometry_sha256'],'proof':proof,'native_actions':0}


def prepare_native_proposal(home,checkpoint_id,checkpoint_sha,origin=DEFAULT_ORIGIN):
    """Admit this ONE source prototype to an immutable stopped-world preimage.

    Existing houses and every current BE are protected even if the house was
    rejected artistically. Only the exact older public pavement may become a
    reviewed floor support; its original gravel preimage is independently bound.
    This does not authorize executing any native plan or moving an inventory.
    """
    from tools.playtest import guard
    from tools.artistic_zipline_catenary import reader_budget
    from tools.artistic_north_bank_east import NorthTerrain, native_payload, preservation, AIR as NATIVE_AIR, SOFT, GROUND, NORTH_SOFT
    from tools.artistic_bridge_refinement import flatten
    from tools.artistic_west_r2_study import ZIP, REJECTED

    home=Path(home).resolve();reserve=guard(4*MIB,24*MIB);budgets=[reader_budget()]
    if home.parent!=Path('D:/A World for Two/staging/world-tests').resolve():raise UserError('Exact private artistic world ancestry required')
    receipt=read_json(home/'dashboard/settlement/backup-receipt.json')
    if receipt.get('verified') is not True or (receipt.get('id'),receipt.get('sha256'))!=(checkpoint_id,checkpoint_sha) or 'stopped' not in receipt.get('scope','').lower():raise UserError('Fresh current verified stopped checkpoint required; never overwrite later human progress')
    registry=read_json(home/'dashboard/settlement/registry.json')
    if Path(registry['world_path']).name!='RosewaterArtistic':raise UserError('Private artistic source only, never permanent-world admission')
    p=construct(registry,origin);ox,oy,oz=p.origin
    field={(x+ox,y+oy,z+oz):s for (x,y,z),s in p.blocks.items()}
    tags={(x+ox,y+oy,z+oz):s for (x,y,z),s in p.tags.items()}
    protected,accepted_sources=preservation(home,registry)
    if any((x,z) in protected for x,y,z in field):raise UserError('Prototype touches an original accepted town/source clearance')
    zpath=home/ZIP[0]
    if digest(zpath)!=ZIP[1]:raise UserError('Retain exact now-placed V2 physical/flight reservation')
    flight=set(flatten(read_json(zpath)))
    if set(field)&flight:raise UserError('Prototype touches placed zipline structure or reserved rider/wire clearance')
    # All rejected houses remain protected during this small preview. Rebuild
    # authority never implies permission to erase a real box or a player item.
    old_houses={}
    for label,rel,sha in REJECTED:
        if digest(home/rel)!=sha:raise UserError('Frozen rejected ownership source changed')
        old_houses.update(flatten(read_json(home/rel)))
    if set(field)&set(old_houses):raise UserError('Preview source would alter a rejected existing house; separate real custody needed')
    old_rel='staging/west-street-stock-SNBT-fixed-20261028T0317Z/'
    refs={'street-and-furniture-PROPOSAL.json':'bc2c532f77a217c1d67c2c73714d891cbd29e6f1a073f653c185bda68de5d80d',
          'before-VERIFY-ONLY.json':'2880d3586e619350b67e0e87e169992dc6aee2195b0a86663493192d2fb2d13a'}
    for name,sha in refs.items():
        if digest(home/old_rel/name)!=sha:raise UserError('Exact existing public-pavement provenance changed')
    old_paving=flatten(read_json(home/old_rel/'street-and-furniture-PROPOSAL.json'))
    old_ground=flatten(read_json(home/old_rel/'before-VERIFY-ONLY.json'))
    allowed_paving={'chipped:small_stone_bricks','minecraft:andesite','minecraft:polished_andesite'}
    terrain=NorthTerrain(home,receipt,registry);before={};supports={};dry={};reviewed_paving=[];footings=[];start=time.monotonic()
    try:
        for label,cells in p.main.items():
            rows=[]
            for x,z in sorted(cells):
                wx,wz=x+ox,z+oz;col=terrain.column(wx,wz);sy=col.get('surface_y');ground=(wx,sy,wz) if sy is not None else (wx,oy-1,wz)
                actual=terrain.state(*ground)
                ordinary=col['kind']=='dry' and sy in (oy-2,oy-1) and key(actual) in GROUND
                historic=(col['kind']=='retained_object' and col['surface_y']==oy-1 and actual==old_paving.get(ground)
                          and key(actual) in allowed_paving and key(old_ground.get(ground,AIR))=='minecraft:gravel')
                if not(ordinary or historic):raise UserError('Keep water, altered terrain or unknown retained columns out of a main footprint: '+str((ground,col)))
                supports[ground]=actual
                rows.append({'support':list(ground),'current_state':actual,'authority':'current natural dry FULL ground' if ordinary else 'same exact authored public paver, original exact before gravel; retain as support'})
                # One shallow masonry skirt/joist support fits the real dry
                # beach relief. Other interior boards span at most three cells
                # between sleepers; the whole beach is never leveled/filled.
                if sy==oy-2:
                    e=edge(cells);x0=min(xx for xx,zz in cells)
                    if (x,z) in e or (x-x0)%4==0:
                        q=(wx,oy-1,wz)
                        if terrain.state(*q)!=AIR or q in terrain.entities:raise UserError('A low dry footing requires actual unchanged AIR above its retained gravel')
                        if (x,z-1) not in cells or (x,z+1) not in cells:material='minecraft:andesite'
                        elif (x,z) in e:material='minecraft:stone_bricks'
                        else:material='minecraft:cobblestone'
                        field[q]=state(registry,material);local=(x,-1,z);p.blocks[local]=field[q];p.owners[local]=label
                        footings.append({'position':list(q),'retained_natural_support':list(ground),'material':material,'role':'one-block supported dry-beach skirt or joist pier'})
            dry[label]=rows
        proof=check(p)
        if set(field)&flight or set(field)&set(old_houses):raise UserError('Terrain-fitted footings must preserve the exact placed zipline and existing houses')
        ordered=sorted(field,key=lambda q:(q[0]//16,q[2]//16,q[1],q[0],q[2]))
        for n,q in enumerate(ordered):
            actual=terrain.state(*q)
            if actual is None:raise UserError('Every addressed body/roof/air column must be saved FULL: '+str(q))
            if q in terrain.entities:raise UserError('Preserve EVERY existing BE and player container, even if state would match: '+str(q))
            if q in old_houses:raise UserError('No current house demolition in first native preview')
            historical_paver=q in old_paving and actual==old_paving[q] and key(actual) in allowed_paving and key(old_ground.get(q,AIR))=='minecraft:gravel'
            if key(actual) not in NATIVE_AIR|SOFT|GROUND|NORTH_SOFT and not historical_paver:
                raise UserError('Preserve real current manmade object/plant/progress: '+str((q,actual)))
            if 'waterlogged=true' in actual or key(actual)=='minecraft:water':raise UserError('No current water may be filled or displaced')
            before[q]=actual
            if historical_paver and field[q]!=actual:reviewed_paving.append({'position':list(q),'before':actual,'after':field[q],'source':'exact rejected-new public pavement, no BE or inventory'})
            if n%512==0:
                budgets.append(reader_budget())
                if time.monotonic()-start>90:raise UserError('Finite source/preimage read exceeded90s')
        # A retained route furnishing above the walking headroom can remain
        # outside our source. Its exact actual support is not silently erased.
        nearby_BEs=[list(q) for q in sorted(terrain.entities) if ox-5<=q[0]<=ox+20 and oz-3<=q[2]<=oz+26]
        sources=terrain.snapshot.sources
    finally:terrain.close()
    documents={'three-frontages-PROPOSAL.json':native_payload(registry,field,checkpoint_sha,'WEST R2 — three tightly interlocking original pirate frontages',tags=tags),
               'before-VERIFY-ONLY.json':native_payload(registry,before,checkpoint_sha,'VERIFY ONLY — complete fresh actual preimage before west R2 preview'),
               'retained-supports-VERIFY-ONLY.json':native_payload(registry,supports,checkpoint_sha,'VERIFY ONLY — retained real dry ground/public-paver supports'),
               'normal-joins-SETTLE-ONLY.json':native_payload(registry,{q:s for q,s in field.items() if key(s)!=AIR},checkpoint_sha,'NORMAL NEIGHBOR SETTLE ONLY — no state or inventory replay')}
    documents['normal-joins-SETTLE-ONLY.json'].update(verification_only=True,construction_forbidden=True)
    documents['before-VERIFY-ONLY.json'].update(verification_only=True,construction_forbidden=True)
    documents['retained-supports-VERIFY-ONLY.json'].update(verification_only=True,construction_forbidden=True)
    manifest={'format':'awft-west-r2-first-native-preview-proposal:1','checkpoint_id':checkpoint_id,'checkpoint_sha256':checkpoint_sha,
        'source_sha256':digest(Path(__file__)),'geometry_sha256':geometry_digest(p),'origin':list(p.origin),'proof':proof,
        'actual_dry_supports':dry,'shallow_dry_beach_footings':footings,'original_accepted_source_custody':accepted_sources,'placed_V2_exact_keepout_sha256':ZIP[1],
        'unchanged_existing_BE_anchors_nearby':nearby_BEs,'existing_BE_or_inventory_writes':0,'existing_house_targets':0,
        'reviewed_rejected_public_pavement_changes':reviewed_paving,'pavement_provenance':refs,
        'features':p.features,'rooms':p.rooms,'entries':p.entries,'planned_routes':p.routes,'roof_sections':p.roof_sections,'story_objects':p.props,
        'preview_cameras':[{'feet':[ox+5.5,oy,oz+12.5],'look_at':[ox+2.5,oy+3,oz+10],'purpose':'bent lane, Wick porch and upper jetty'},
            {'feet':[ox+7.5,oy,oz+16.5],'look_at':[ox+10,oy+6,oz+11],'purpose':'taller Cooper side front and stepped roof behind the bend'},
            {'feet':[ox+8.5,oy,oz+23.5],'look_at':[ox+2.5,oy+4,oz+18],'purpose':'low sailmaker roof and real lanterned dormer opposite the alley'}],
        'raw_saved_sources':sources,'reader_peak_observed_RSS_bytes':max(r['owned_reader_rss_bytes'] for r in budgets),'reserve_guard':reserve,
        'native_actions':0,'world_writes':0,'existing_inventory_moved_or_overwritten':0,
        'limits':['Source and exact saved preimage only; no native construction/render/art claim','Parent must native-verify current before/supports before executing ONE preview','Normal neighbor settle and full strict state/NBT verification follow, then actual inside/street/roof screenshots','Do not replicate before actual visual review; all rejected old batches remain held','No actual house/BE or postvisit player item is touched by this preview']}
    raw={n:(json.dumps(v,separators=(',',':'))+'\n').encode() for n,v in documents.items()}
    manifest['files']={n:{'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)} for n,b in raw.items()}
    raw['manifest.json']=(json.dumps(manifest,separators=(',',':'))+'\n').encode()
    if sum(map(len,raw.values()))>24*MIB:raise UserError('Bounded native-preview proposal allocation exceeded')
    out=home/'staging'/('west-r2-three-frontage-preview-'+str(time.time_ns()));out.mkdir()
    for n,b in raw.items():(out/n).open('xb').write(b)
    return {'folder':str(out),'manifest_sha256':digest(out/'manifest.json'),'files':manifest['files'],'geometry_sha256':geometry_digest(p),
        'cells':len(field),'dry_columns':sum(map(len,dry.values())),'existing_BE_writes':0,'reviewed_old_paver_changes':len(reviewed_paving),'native_actions':0}


if __name__=='__main__':
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('--registry',type=Path);a.add_argument('--output',type=Path)
    a.add_argument('--home',type=Path);a.add_argument('--checkpoint-id');a.add_argument('--checkpoint-sha')
    a.add_argument('--origin',nargs=3,type=int,default=DEFAULT_ORIGIN);args=a.parse_args()
    if args.home:
        if not args.checkpoint_id or not args.checkpoint_sha:a.error('Exact current stopped checkpoint required')
        result=prepare_native_proposal(args.home,args.checkpoint_id,args.checkpoint_sha,args.origin)
    else:
        if not args.registry or not args.output:a.error('Pure source review requires registry and a unique output folder')
        result=source_bundle(read_json(args.registry),args.output,args.origin)
    print(json.dumps(result,indent=2))
