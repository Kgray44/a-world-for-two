"""Original local-origin architectural prototypes; never installs or edits a world.

The first gate is actual client screenshots and revision, not a placement count.
Only an explicitly staging-hosted runtime can receive native payloads from CLI.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

from control_room.common import Layout, UserError, atomic_write, digest, read_json, utcnow
from control_room.storage import Storage
from tools.artistic_materials import material_runs, require_material_rule


LIMIT = 160_000
OUTPUT_LIMIT = 16 * 1024**2
AIR = 'minecraft:air'
KINDS = ('castle-gatehouse', 'castle-palace', 'rosebridge')
MASONRY = (
    'chipped:small_calcite_bricks', 'minecraft:polished_diorite',
    'chipped:ornate_calcite_pillar', 'rechiseled:quartz_block_chiseled_pillar',
    'chipped:calcite_bricks', 'chipped:calcite_mini_tiles',
    'chipped:blank_calcite_carving', 'chipped:carved_calcite',
)


def inside(x, z, points):
    hit = False
    for (ax, az), (bx, bz) in zip(points, points[1:] + points[:1]):
        if (az > z) != (bz > z) and x < (bx-ax)*(z-az)/(bz-az)+ax:
            hit = not hit
    return hit


def polygon_cells(points):
    return {(x, z) for x in range(min(x for x, _ in points), max(x for x, _ in points))
            for z in range(min(z for _, z in points), max(z for _, z in points))
            if inside(x+.5, z+.5, points)}


def octagon(x, z, r):
    c = max(1, round(r*.42))
    return [(x-r+c,z-r),(x+r-c,z-r),(x+r,z-r+c),(x+r,z+r-c),
            (x+r-c,z+r),(x-r+c,z+r),(x-r,z+r-c),(x-r,z-r+c)]


class Prototype:
    def __init__(self, registry, kind):
        self.registry = registry; self.kind = kind
        self.blocks = {}; self.terrain = set(); self.features = []; self.rooms = []; self.routes = []; self.cameras = []; self.land_footprints = []; self.footings = []

    def state(self, key, **props):
        native = self.registry['blocks']
        if key not in native:
            raise UserError('Unregistered prototype material: '+key)
        values = {}
        for field, value in props.items():
            value = str(value).lower()
            if field not in native[key] or value not in [str(v).lower() for v in native[key][field]]:
                raise UserError(f'Unregistered prototype state: {key} {field}={value}')
            values[field] = value
        return key + ('['+','.join(f'{k}={v}' for k,v in sorted(values.items()))+']' if values else '')

    def put(self, x, y, z, key, *, context=False, **props):
        xmax,ymax=(80,144) if self.kind=='castle-palace' else (56,120)
        if any(type(v) is not int for v in (x,y,z)) or not -56<=x<=xmax or not -60<=z<=60 or not 48<=y<=ymax:
            raise UserError('Prototype escaped its local reviewed design envelope')
        position = x,y,z; self.blocks[position] = self.state(key,**props)
        if context:self.terrain.add(position)
        else:self.terrain.discard(position)
        if len(self.blocks)>LIMIT:raise UserError('Split the prototype before expanding its footprint')

    def fill(self, x1,y1,z1,x2,y2,z2,key,**props):
        for x in range(x1,x2+1):
            for y in range(y1,y2+1):
                for z in range(z1,z2+1):self.put(x,y,z,key(x,y,z) if callable(key) else key,**props)

    def masonry(self,x,y,z):
        # Deliberate ashlar panels, horizontal string courses, dressed pilasters
        # and end joints. Every material has <=3 in X/Y and <=9 along Z.
        return MASONRY[(1 if y%4==0 else 0)+(2 if x%4==0 else 0)+(4 if z%10==0 else 0)]

    def stone(self,x1,y1,z1,x2,y2,z2):self.fill(x1,y1,z1,x2,y2,z2,self.masonry)

    def paving(self,x,y,z,wood=False):
        if wood:
            keys=('chipped:boxed_spruce_planks','minecraft:spruce_planks','minecraft:stripped_spruce_log','minecraft:oak_planks')
        else:
            keys=('chipped:tiled_calcite','chipped:checkered_calcite_tiles','chipped:bordered_calcite','chipped:blank_calcite_carving')
        key=keys[(1 if x%4==0 else 0)+(2 if z%10==0 else 0)]
        self.put(x,y,z,key,**({'axis':'x'} if key=='minecraft:stripped_spruce_log' else {}))

    def floor(self,cells,y,wood=False):
        for x,z in cells:self.paving(x,y,z,wood)

    def shell(self,points,floor,height,*,wood=False):
        cells=polygon_cells(points);self.floor(cells,floor,wood)
        for x,z in cells:
            edge=any((x+dx,z+dz) not in cells for dx,dz in ((1,0),(-1,0),(0,1),(0,-1)))
            for y in range(floor+1,floor+height+1):
                if not edge:self.put(x,y,z,AIR);continue
                if wood:
                    front=any((x,z+dz) not in cells for dz in (-1,1))
                    side=any((x+dx,z) not in cells for dx in (-1,1))
                    post=(front and x%4==0) or (side and z%4==0) or (front and side)
                    if post:key='minecraft:stripped_dark_oak_log' if (y-floor)%8 else 'minecraft:chiseled_stone_bricks'
                    elif (y-floor)%4==0:key='minecraft:dark_oak_log' if front else 'minecraft:spruce_log'
                    else:key='minecraft:white_terracotta'
                    self.put(x,y,z,key,**({'axis':'y'} if key.endswith('_log') and key.startswith('minecraft:stripped') else {'axis':'x' if key=='minecraft:dark_oak_log' else 'z'} if key.endswith('_log') else {}))
                else:self.put(x,y,z,self.masonry(x,y,z))
        return cells

    def stair(self,x,y,z,facing='north',key='minecraft:cherry_stairs',half='bottom'):
        self.put(x,y,z,key,facing=facing,half=half,shape='straight',waterlogged=False)

    def door(self,x,y,z,facing='south',key='mcwdoors:dark_oak_classic_door'):
        for dy,half in ((0,'lower'),(1,'upper')):
            self.put(x,y+dy,z,key,facing=facing,half=half,hinge='left',open=False,powered=False)

    def gothic(self,x,y,z,facing='south'):
        self.put(x,y,z,'mcwwindows:stone_brick_gothic',facing=facing,open=False,part='base')
        self.put(x,y+1,z,'mcwwindows:stone_brick_gothic',facing=facing,open=False,part='top')

    def pane(self,x,y,z,facing='south',wood='cherry'):
        for dy,part in ((0,'base'),(1,'above')):
            self.put(x,y+dy,z,f'mcwwindows:{wood}_pane_window',facing=facing,part=part,windowstate='closed')

    def broad_window(self,x,y,z,facing='south',height=3,wood=False,frame=None):
        # Native Macaw resizable models use north/east for both sides of their
        # plane, with explicit corner/edge/center pieces. This is real glazed
        # area, not three arrow slits put beside one another.
        key=frame or ('mcwwindows:dark_oak_plank_window' if wood else 'mcwwindows:stone_window')
        for dy in range(height):
            row='bot' if dy==0 else 'top' if dy==height-1 else 'mid'
            for u,col in ((-1,'l'),(0,'m'),(1,'r')):
                wx,wz=(x+u,z) if facing in ('north','south') else (x,z+u)
                self.put(wx,y+dy,wz,key,facing='north' if facing in ('north','south') else 'east',part=row+'_'+col)
        # A proud sill and chamfered head add shadow and depth to the opening.
        normal={'north':(0,-1),'south':(0,1),'west':(-1,0),'east':(1,0)}[facing]
        for u in range(-2,3):
            wx,wz=(x+u,z) if facing in ('north','south') else (x,z+u)
            if not wood:
                if u==0:self.put(wx+normal[0],y-1,wz+normal[1],'chipped:carved_calcite')
                else:self.put(wx+normal[0],y-1,wz+normal[1],'minecraft:smooth_quartz_slab' if facing in ('north','south') else 'minecraft:polished_andesite_slab',type='top',waterlogged=False)
                if abs(u)<=1:
                    self.stair(wx+normal[0],y+height+(1 if u==0 else 0),wz+normal[1],facing,'minecraft:polished_andesite_stairs','top')
            elif abs(u)<=1:
                self.put(wx+normal[0],y-1,wz+normal[1],'mcwwindows:dark_oak_log_parapet',facing=facing,part='flower')
        if wood:
            for u,hinge in ((-2,'left'),(2,'right')):
                wx,wz=(x+u,z) if facing in ('north','south') else (x,z+u)
                # Do not invent a shutter outside the L-shaped lodge wall.
                if self.blocks.get((wx,y,wz),AIR)!=AIR:
                    self.put(wx+normal[0],y,wz+normal[1],'mcwwindows:dark_oak_louvered_shutter',facing=facing,hinge=hinge,open=True)

    def light(self,x,y,z,facing=None):
        if facing:self.put(x,y,z,'mcwlights:tavern_wall_lantern',facing=facing)
        else:self.put(x,y,z,'mcwlights:tavern_lantern',hanging=False,waterlogged=False)

    def rose(self,x,y,z):
        self.put(x,y-1,z,'minecraft:dirt')
        self.put(x,y,z,'minecraft:rose_bush',half='lower');self.put(x,y+1,z,'minecraft:rose_bush',half='upper')

    def seat(self,x,y,z,facing='south',wood='cherry',color='pink'):
        self.put(x,y,z,f'handcrafted:{wood}_bench',facing=facing,color=color,shape='single',waterlogged=False)

    def camera(self,name,position,target,mode='eye'):
        dx,dy,dz=[b-a for a,b in zip(position,target)]
        self.cameras.append({'name':name,'local_position':position,'look_at':target,'mode':mode,
                             'yaw':math.degrees(math.atan2(-dx,dz)),
                             'pitch':-math.degrees(math.atan2(dy,math.hypot(dx,dz)))})


def gable(p,x1,x2,z1,z2,base,roof='mcwroofs:dark_prismarine_roof'):
    half=(x2-x1)//2
    for n in range(half+1):
        for x,facing in ((x1+n,'east'),(x2-n,'west')):
            for z in range(z1,z2+1):
                material=roof if (z-z1)%8 else 'minecraft:dark_prismarine_stairs' if 'prismarine' in roof else 'minecraft:dark_oak_stairs'
                if material.startswith('minecraft:'):p.stair(x,base+n,z,facing,material)
                else:p.put(x,base+n,z,material,facing=facing,half='bottom',shape='straight')
        if n:
            for z in (z1+1,z2-1):
                for x in range(x1+n,x2-n+1):
                    if x%4==0:key='minecraft:chiseled_quartz_block'
                    elif (base+n)%4==0:key='minecraft:quartz_block'
                    else:key='minecraft:pink_terracotta'
                    p.put(x,base+n-1,z,key)
    ridge=(x1+x2)//2
    for z in range(z1,z2+1):
        if (z-z1)%8==0:
            p.put(ridge,base+half+1,z,'minecraft:chiseled_quartz_block');p.put(ridge,base+half+2,z,'minecraft:iron_bars')
        else:p.put(ridge,base+half+1,z,'mcwroofs:dark_prismarine_top_roof',part='top_end_0')


def cornice(p,cx,cz,r,y):
    cells=polygon_cells(octagon(cx,cz,r));inner=polygon_cells(octagon(cx,cz,r-1))
    for x,z in cells-inner:
        key='minecraft:quartz_slab' if abs(z-cz)>=abs(x-cx) else 'minecraft:polished_diorite_slab'
        if r>6 and (x if abs(z-cz)>=abs(x-cx) else z)%8==0:p.put(x,y,z,p.masonry(x,y,z))
        else:p.put(x,y,z,key,type='top',waterlogged=False)


def tower(p,cx,cz,r,floor,height,profile):
    p.shell(octagon(cx,cz,r),floor,height)
    cornice(p,cx,cz,r+1,floor+height+1)
    for level,radius in enumerate(profile):
        cells=polygon_cells(octagon(cx,cz,radius)) if radius else {(cx,cz)}
        inner=polygon_cells(octagon(cx,cz,radius-1)) if radius>1 else set()
        for x,z in cells-inner:
            p.put(x,floor+height+2+level,z,'minecraft:oxidized_cut_copper' if x%4==0 else 'minecraft:dark_prismarine')
    top=floor+height+2+len(profile)
    p.put(cx,top,cz,'minecraft:iron_bars');p.put(cx,top+1,cz,'minecraft:iron_bars')
    for y in (floor+4,floor+13,floor+height-2):
        if y+1>floor+height:continue
        p.gothic(cx-1,y,cz+r-1,'south');p.gothic(cx,y,cz-r,'north')
        p.gothic(cx-r,y,cz,'west');p.gothic(cx+r-1,y,cz-1,'east')
    # Broken string courses and a rose-coloured sill give each stage a purpose.
    cornice(p,cx,cz,r,floor+10)
    return top


def seal_tower_eaves(p,cx,cz,r,floor,height):
    # Full-depth closing soffit: a top slab on an outer ring cannot close the
    # annular gap between the original wall and an overhanging roof.
    outer=polygon_cells(octagon(cx,cz,r+1));inner=polygon_cells(octagon(cx,cz,max(1,r-1)))
    for x,z in outer-inner:p.put(x,floor+height+1,z,p.masonry(x,floor+height+1,z))


def seal_gable_eaves(p,outline,wall_top,roofs,wood=False):
    cells=polygon_cells(outline)
    for x,z in cells:
        if not any((x+dx,z+dz) not in cells for dx,dz in ((1,0),(-1,0),(0,1),(0,-1))):continue
        heights=[base+min(x-left,right-x) for left,right,back,front,base in roofs if left<=x<=right and back<=z<=front]
        if not heights:raise UserError(f'A boundary has no authored roof to join: {x},{z}')
        for y in range(wall_top+1,min(heights)):
            if wood:
                front=any((x,z+dz) not in cells for dz in (-1,1))
                key='minecraft:chiseled_stone_bricks' if (x if front else z)%4==0 else 'minecraft:dark_oak_log' if front else 'minecraft:spruce_log'
                p.put(x,y,z,key,**({'axis':'x' if front else 'z'} if key.endswith('_log') else {}))
            else:p.put(x,y,z,p.masonry(x,y,z))


def pointed_top(x,center,radius,spring,rise):
    return spring+round(rise*math.sqrt(max(0,1-abs(x-center)/radius)))


def gatehouse(p):
    floor=68
    # Narrow inhabited approach: two small, differently proportioned lodges.
    for x in range(-35,36):
        for z in range(-30,48):p.put(x,63,z,'minecraft:grass_block',context=True)
    for z in range(8,46):
        level=64 if z>=28 else min(68,64+(28-z)//2)
        for x in range(-3,4):
            p.stone(x,64,z,x,level-1,z) if level>64 else None
            previous=64 if z+1>=28 else min(68,64+(28-z-1)//2)
            if level>previous:p.stair(x,level,z,'north','minecraft:stone_brick_stairs')
            else:p.paving(x,level,z)
        p.routes.append({'name':'Castle ascent','point':[0,level+1,z]})
    for x in range(-3,4):p.stair(x,64,46,'north','minecraft:stone_brick_stairs')
    p.routes.append({'name':'Lane threshold from native ground','point':[0,65,46]})
    lodges=[('Rosekeeper lodging',[(-21,35),(-8,35),(-8,25),(-13,25),(-13,21),(-21,21)],64,12),
            ('Candlekeeper workshop',[(7,41),(16,41),(16,29),(10,29),(10,27),(7,27)],64,10)]
    for name,outline,y,h in lodges:
        cells=p.shell(outline,y,h,wood=True);p.floor(cells,y+5,wood=True)
        p.land_footprints.append({'name':name,'polygon':outline,'floor':y,'requires':'Dry native land, never river or bridge underspan'})
        left=min(x for x,z in cells);right=max(x for x,z in cells);front=max(z for x,z in cells);back=min(z for x,z in cells)
        gable(p,left-1,right+1,back-1,front+1,y+h+1,'mcwroofs:dark_oak_roof')
        side=right if right<0 else left;facing='east' if side<0 else 'west'
        p.door(side,y+1,front-4,facing,'mcwdoors:dark_oak_cottage_door')
        for sy in (y+2,y+7):
            p.pane(side,sy,front-8,facing,'cherry');p.pane(left+3,sy,front,'south','cherry')
        for n in range(5):
            p.stair(left+2,y+1+n,back+2+n,'south');p.fill(left+2,y+2+n,back+2+n,left+2,y+3+n,back+2+n,AIR)
        p.put(left+4,y+1,back+2,'minecraft:crafting_table');p.put(left+5,y+1,back+2,'minecraft:barrel',facing='south',open=False)
        p.put(left+4,y+6,back+2,'handcrafted:cherry_desk',facing='south',color='none',waterlogged=False)
        p.put(left+4,y+7,back+2,'handcrafted:stackable_book',facing='south',books=2,seed=4)
        p.put(left+5,y+6,back+3,'handcrafted:cherry_chair',facing='west',color='pink',waterlogged=False)
        p.light(side+(1 if side<0 else -1),y+3,front-4,facing)
        p.rooms.append({'name':name,'purpose':'A workshop below a compact inhabited upper room','floor':y,'upper_floor':y+5})
        # A personal stoop and a small garden wall join each inhabited door to
        # the lane; the entry is not a doorway suspended over unworked grass.
        entry_z=front-4
        for ex in range(min(side, -3 if side<0 else 3),max(side,-3 if side<0 else 3)+1):p.paving(ex,y,entry_z)
        for ex in (side+(2 if side<0 else -2),side+(4 if side<0 else -4)):
            p.rose(ex,y+1,entry_z+2)
        p.seat(side+(2 if side<0 else -2),y+1,entry_z-2,facing)
    # An asymmetric L-wing, gate volume and open rose cloister, not a giant keep box.
    wing=[(-31,5),(-15,5),(-15,-11),(-21,-11),(-21,-19),(-31,-19)]
    cells=p.shell(wing,floor,16);p.floor(cells,78,wood=True)
    for x,z in cells:p.stone(x,64,z,x,floor-1,z)
    p.land_footprints.append({'name':'Archive and castle wing','polygon':wing,'floor':floor,'requires':'Dry native land with bounded dressed terrace foundation'})
    gable(p,-32,-14,-13,6,85);gable(p,-32,-20,-20,-8,84)
    # A slender double flue and a rose-window roof lantern interrupt the long
    # slate sweep for architectural reasons, not random roof recolouring.
    for y in range(88,97):
        p.put(-28,y,-8,'minecraft:bricks' if y%4 else 'minecraft:chiseled_stone_bricks')
        p.put(-27,y,-8,'minecraft:bricks' if y%4 else 'minecraft:chiseled_stone_bricks')
    for x in (-28,-27):p.put(x,97,-8,'minecraft:brick_wall',up=True,east='none',west='none',north='none',south='none',waterlogged=False)
    for x in range(-25,-20):
        for z in range(-4,0):
            edge=x in (-25,-21) or z in (-4,-1)
            for y in range(91,94):
                p.put(x,y,z, 'minecraft:chiseled_quartz_block' if (x in (-25,-21) and z in (-4,-1)) else 'minecraft:pink_stained_glass' if edge else AIR)
    for x in (-25,-21):
        for z in (-4,-1):p.put(x,94,z,'minecraft:quartz_slab',type='top',waterlogged=False)
    gable(p,-26,-20,-5,0,94)
    # Gate body: actual vaulted passage below an inhabited gallery.
    p.stone(-6,68,-5,6,86,5);p.fill(-5,79,-4,5,85,4,AIR)
    for x in range(-3,4):
        top=pointed_top(x,0,4,72,5)
        p.fill(x,69,-5,x,min(77,top),6,AIR)
    for x in range(-5,6):
        top=pointed_top(x,0,6,73,6)
        p.put(x,top,6,p.masonry(x,top,6))
        if abs(x)>=4:p.stone(x,69,6,x,top,6)
    for x in (-6,6):
        p.stone(x,68,4,x,80,7)
    # Coffered vault ribs; no portcullis blocks the walking opening.
    for z in (-4,0,4):
        for x in range(-3,4):
            y=min(78,pointed_top(x,0,4,73,5));p.put(x,y,z,p.masonry(x,y,z))
    tower(p,-11,0,5,floor,23,[6,6,5,5,4,4,3,3,2,2,1,0])
    tower(p,10,-3,4,floor,18,[5,5,4,4,3,2,2,1,0])
    for outline in (octagon(-11,0,5),octagon(10,-3,4),[(-6,-5),(7,-5),(7,6),(-6,6)]):
        for x,z in polygon_cells(outline):p.stone(x,64,z,x,67,z)
    gable(p,-7,7,-6,6,87)
    # Real tower/gallery floors and open doors on their common walls.
    p.floor(polygon_cells(octagon(-11,0,4)),78,wood=True)
    p.floor(polygon_cells(octagon(10,-3,3)),78,wood=True)
    for x in range(-15,15):
        if x in range(-6,7) or x in (-15,-7,-6,6,7):p.fill(x,79,-1,x,81,1,AIR)
    for x in range(-5,6):
        for z in range(-4,5):p.paving(x,78,z,wood=True)
    # The practical stair lives in the west wing, leaving a generous entrance hall.
    for n in range(10):
        p.stair(-28,69+n,2-n,'north');p.fill(-28,70+n,2-n,-28,72+n,2-n,AIR)
    for z in (-8,-9):
        for x in (-28,-27):p.paving(x,78,z,wood=True)
    p.fill(-16,69,0,-14,71,2,AIR);p.fill(-16,79,0,-14,81,2,AIR)
    p.door(-15,69,1,'east');p.door(-15,79,1,'east')
    # Deep windows and a small oriel, with coherent panelled stone rather than flat walls.
    for x in (-28,-23,-18):
        p.gothic(x,72,4,'south');p.gothic(x,81,4,'south')
    for z in (-14,-9,-4,1):p.gothic(-31,72,z,'west')
    for x in (-4,0,4):p.gothic(x,81,5,'south')
    for x in range(-4,5):
        for z in (6,7,8):p.paving(x,78,z)
        if x%4!=0:p.put(x,79,8,'mcwfences:railing_quartz_wall',east=True,west=True,north=False,south=False,waterlogged=False)
    for x in (-4,4):p.stone(x,77,6,x,78,7);p.light(x,80,8)
    # Furnished duty room, archive, music/reading gallery and a quiet tower alcove.
    for x in (-29,-28,-27):p.put(x,69,-16,'minecraft:bookshelf')
    p.put(-26,69,-15,'handcrafted:cherry_desk',facing='east',color='none',waterlogged=False)
    p.put(-26,70,-15,'handcrafted:stackable_book',facing='east',books=3,seed=12)
    p.put(-25,69,-15,'handcrafted:cherry_chair',facing='west',color='pink',waterlogged=False)
    for x in (-22,-21,-20):p.put(x,79,-9,'minecraft:bookshelf')
    p.put(-21,79,-6,'handcrafted:cherry_table',color='none',shape='single',waterlogged=False)
    p.put(-21,80,-6,'handcrafted:stackable_book',facing='south',books=2,seed=6)
    p.seat(-23,79,-6,'east');p.seat(-19,79,-6,'west')
    p.put(-22,83,-6,'mcwlights:golden_small_chandelier',lit=True)
    p.seat(-3,79,1);p.seat(3,79,1);p.put(0,79,-3,'minecraft:lectern',facing='south',has_book=False,powered=False)
    p.put(0,84,-1,'mcwlights:golden_chandelier',lit=True)
    p.seat(9,79,-3,'east');p.put(10,79,-4,'handcrafted:cherry_side_table',facing='south',color='none',waterlogged=False)
    p.put(10,80,-4,'minecraft:potted_pink_tulip')
    # An occupied lookout reached by a proper winding stair, rather than an
    # inaccessible empty upper tower. Each turn rises eight blocks, preserving
    # clear headroom above the preceding turn.
    p.floor(polygon_cells(octagon(-11,0,4)),88,wood=True)
    ring=[(x,-2) for x in range(-2,3)]+[(2,z) for z in range(-1,3)]+[(x,2) for x in range(1,-3,-1)]+[(-2,z) for z in range(1,-2,-1)]
    for n in range(20):
        dx,dz=ring[n%len(ring)];nx,nz=ring[(n+1)%len(ring)];y=79+n//2
        facing='east' if nx>dx else 'west' if nx<dx else 'south' if nz>dz else 'north'
        p.fill(-11+dx,y+1,dz,-11+dx,y+3,dz,AIR)
        if n%2==0:p.stair(-11+dx,y,dz,facing)
        else:p.paving(-11+dx,y,dz,wood=True)
    p.put(-11,89,-2,'minecraft:lectern',facing='south',has_book=False,powered=False)
    p.seat(-12,89,2,'north');p.light(-11,91,1)
    p.rooms.extend([{'name':'Guard and correspondence room','floor':68},
                    {'name':'West archive and reading salon','floor':78},
                    {'name':'Gate gallery and rose balcony','floor':78},
                    {'name':'East watch alcove','floor':78}])
    p.rooms.append({'name':'West tower chart lookout','floor':88,'access':'Winding stair from the gallery floor'})
    # Cloister garden: three open bays, a real turn around the water rill, intimate seating.
    garden=polygon_cells([(15,-19),(31,-19),(31,8),(15,8)])
    p.floor(garden,68)
    for x,z in garden:p.stone(x,64,z,x,67,z)
    p.land_footprints.append({'name':'Raised rose cloister','polygon':[(15,-19),(31,-19),(31,8),(15,8)],'floor':68,'requires':'Dry native land; the rill is a deliberate courtyard water feature'})
    for z in range(-19,9):
        p.stone(30,69,z,30,70,z)
        if z%5==0:p.stone(16,69,z,16,74,z)
        for x in (15,16,17):
            p.put(x,75,z,'mcwroofs:dark_prismarine_roof' if z%8 else 'mcwroofs:dark_prismarine_steep_roof',facing='east',half='bottom',shape='straight')
    for z in (-16,-6,4):
        for x in range(20,28):
            p.put(x,68,z,'minecraft:grass_block')
            if x%2==0:p.rose(x,69,z)
        p.seat(28,69,z,'west');p.light(29,71,z)
    for z in range(-15,5):
        p.put(23,68,z,'minecraft:water',level=0)
        for x in (22,24):p.put(x,68,z,'minecraft:polished_diorite_slab',type='top',waterlogged=False)
    for z in (-11,-1):
        for x in (22,23,24):
            p.put(x,68,z,'minecraft:chiseled_quartz_block')
            p.put(x,69,z,'minecraft:cherry_slab',type='bottom',waterlogged=False)
    p.rooms.append({'name':'Rose cloister and narrow reflecting rill','floor':68})
    # Terraced court and two nonidentical foreground pockets, no enormous lawns.
    for x in range(-7,15):
        for z in range(7,19):
            p.stone(x,64,z,x,67,z);p.paving(x,68,z)
    for x in (-9,9):
        for z in range(9,20):
            p.stone(x,65,z,x,68,z)
            if z%4==1:p.rose(x,69,z)
    p.seat(-7,69,13,'east');p.seat(13,69,15,'west')
    for x,z in ((-5,20),(5,20),(-7,8),(13,8)):
        p.stone(x,65,z,x,70,z);p.light(x,71,z)
    for x in range(-3,4):
        for z in range(-5,9):
            p.stone(x,64,z,x,67,z);p.paving(x,68,z)
    p.features.extend(['Stepped town-to-castle reveal','Unequal octagonal towers and roof profiles',
        'Deep pointed entry with coffered ribs','An inhabited upper gallery and balcony',
        'L-shaped archive wing and practical stairs','Quiet rose cloister with crossed water rill'])
    for z in range(-5,8):p.routes.append({'name':'Gate passage','point':[0,69,z]})
    p.camera('Ascending upper-town lane',[1,66,43],[0,84,0])
    p.camera('Gate and rose court',[-4,70,18],[-1,83,0])
    p.camera('West three-quarter silhouette',[-35,76,21],[-3,84,-3],'free')
    p.camera('Vaulted entry',[0,70,4],[0,73,-5])
    p.camera('Gallery over the approach',[1,80,3],[0,69,24])
    p.camera('Cloister detail',[27,70,5],[17,72,-12])
    p.camera('Archive room',[-18,80,-4],[-23,81,-8])
    p.camera('Tower chart alcove',[-13,90,2],[-11,90,-2])


def refine_gatehouse(p):
    """Revision from actual r1 client views, not a replacement shell generator."""
    # The first shot showed almost invisible slit-like glazing. Use complete
    # native resizable window assemblies and shadowed stone heads instead.
    for x in (-28,-23,-18):
        p.broad_window(x,71,4,'south',4);p.broad_window(x,80,4,'south',4)
    for z in (-14,-9,-4,1):
        p.broad_window(-31,71,z,'west',4);p.broad_window(-31,80,z,'west',4)
    for y in (71,80):p.broad_window(-27,y,-19,'north',4)
    for x in (-4,0,4):p.broad_window(x,80,5,'south',3)
    for cx,cz,r,levels in ((-11,0,5,((72,4),(81,4),(89,2))),(10,-3,4,((72,4),(81,3)))):
        for y,height in levels:
            p.broad_window(cx,y,cz+r-1,'south',height)
            p.broad_window(cx,y,cz-r,'north',height)
        p.broad_window(cx-r,73,cz,'west',3)
        p.land_footprints.append({'name':'Inhabited gate tower','polygon':octagon(cx,cz,r),'floor':68,'requires':'Dry native land, never a bridge pier or navigation channel'})
    p.land_footprints.append({'name':'Gate passage and inhabited gallery','polygon':[(-6,-5),(7,-5),(7,6),(-6,6)],'floor':68,'requires':'Dry native land'})
    for side,left,front in ((-9,-21,34),(7,7,40)):
        facing='east' if side<0 else 'west'
        for y in (66,71):
            p.broad_window(side,y,front-8,facing,2,True)
            p.broad_window(left+3,y,front,'south',2,True)
        p.broad_window(side,71,front-2,facing,2,True)
        door_z=front-4
        for x in range(min(side,-3 if side<0 else 3),max(side,-3 if side<0 else 3)+1):
            if x!=side:p.fill(x,65,door_z,x,67,door_z,AIR)
        # An actual bed and domestic shelf make the upper rooms places to live.
        bed_x=left+3
        p.put(bed_x,70,front-2,'minecraft:pink_bed',facing='north',part='foot',occupied=False)
        p.put(bed_x,70,front-3,'minecraft:pink_bed',facing='north',part='head',occupied=False)
        p.put(left+5,70,front-2,'handcrafted:cherry_nightstand',facing='south',color='none',waterlogged=False)
        p.put(left+5,71,front-2,'minecraft:potted_allium')
    # Explicit clearance removes the native meadow growing through the first
    # rendered lane. Planting pockets, benches and door leaves remain outside.
    for z in range(8,47):
        level=64 if z>=28 else min(68,64+(28-z)//2)
        p.fill(-3,level+1,z,3,level+3,z,AIR)
    # The r1 portal framed empty sky because the raised floor ended immediately
    # behind it. A contained garden court and real rear stair now finish that
    # arrival, without pretending the later palace wings already exist.
    court={(x,z) for x in range(-14,15) for z in range(-20,-5) if z<=-8 or abs(x)<=5}
    for x,z in court:
        p.stone(x,60,z,x,67,z);p.paving(x,68,z)
        p.fill(x,69,z,x,71,z,AIR)
    for x in range(-2,3):
        for z in range(-16,-11):
            if abs(x)==2 or z in (-16,-12):p.put(x,69,z,p.masonry(x,69,z))
            else:p.put(x,69,z,'minecraft:water',level=0)
    p.put(0,69,-14,'minecraft:chiseled_quartz_block')
    p.put(0,70,-14,'minecraft:quartz_slab',type='top',waterlogged=False)
    p.put(0,71,-14,'minecraft:potted_pink_tulip')
    for x,z,face in ((-10,-13,'east'),(10,-16,'west'),(-9,-18,'south')):
        p.seat(x,69,z,face);p.rose(x-1,69,z+1);p.light(x+1,71,z+1)
    for n in range(1,10):
        z=-20-n;level=68-n//2
        for x in range(-2,3):
            p.stone(x,60,z,x,level-1,z)
            if n%2:p.stair(x,level,z,'south','minecraft:stone_brick_stairs')
            else:p.paving(x,level,z)
            p.fill(x,level+1,z,x,level+3,z,AIR)
        p.routes.append({'name':'Rear garden stair to the natural upper path','point':[0,level+1,z]})
    for z in range(-20,-5):p.routes.append({'name':'Gate-to-court side promenade','point':[4,69,z]})
    # A real inhabited bay breaks the long archive rectangle in plan as well
    # as elevation. It has an interior window seat on each occupied storey.
    bay=[(-26,4),(-20,4),(-20,7),(-21,8),(-25,8),(-26,7)]
    cells=p.shell(bay,68,16);p.floor(cells,78,wood=True)
    for x,z in cells:p.stone(x,60,z,x,67,z)
    gable(p,-27,-19,3,9,85)
    for y in (71,80):p.broad_window(-23,y,7,'south',4)
    for y in (72,81):p.gothic(-26,y,5,'west')
    for y in (69,79):
        p.fill(-24,y,4,-22,y+3,4,AIR)
        p.seat(-24,y,6,'south')
        p.routes.append({'name':'Archive projecting bay entry','point':[-22,y,5]})
    p.rooms.append({'name':'Projecting archive window bay','floor':78,'purpose':'A deep inhabited window seat, joined to the archive rather than pasted onto its wall'})
    # The western corner becomes a connected study turret, not another empty
    # copy of the gate towers. Its lower mass and roof are deliberately distinct.
    tower(p,-33,-12,3,68,17,[4,3,3,2,2,1,0])
    p.floor(polygon_cells(octagon(-33,-12,2)),78,wood=True)
    for x,z in polygon_cells(octagon(-33,-12,3)):p.stone(x,60,z,x,67,z)
    for y in (69,79):p.fill(-32,y,-12,-30,y+2,-12,AIR)
    p.put(-34,79,-13,'handcrafted:cherry_desk',facing='east',color='none',waterlogged=False)
    p.put(-34,80,-13,'handcrafted:stackable_book',facing='east',books=2,seed=3)
    p.put(-33,79,-13,'handcrafted:cherry_chair',facing='west',color='pink',waterlogged=False)
    p.put(-34,69,-12,'supplementaries:globe_sepia',facing='east',powered=False,rotation=0,waterlogged=False)
    p.light(-33,82,-12)
    p.rooms.append({'name':'Connected west correspondence turret','floor':78,'purpose':'A furnished small writing study above a map alcove'})
    for y,height in ((72,3),(81,3)):p.broad_window(-33,y,-10,'south',height,True)
    # Stepped buttresses, a recessed panel and crowned landings cast real
    # shadows on the otherwise rectangular west and south archive faces.
    for z in (-17,-7,3):
        for y in range(68,84):
            reach=2 if y<74 else 1
            for x in range(-31-reach,-30):p.put(x,y,z,p.masonry(x,y,z))
        p.put(-33,74,z,'minecraft:quartz_slab',type='top',waterlogged=False)
        p.light(-32,80,z,'west')
    for x in (-30,-16):
        for y in range(68,83):
            for z in range(5,7 if y<75 else 6):p.put(x,y,z,p.masonry(x,y,z))
    # Give the large upper room a clear programme: tall bookcase bays, two
    # writing tables, a fireplace salon, window seats and layered woven rugs.
    for start in (-29,-25,-21):
        for x in range(start,start+3):
            for y in range(79,84):p.put(x,y,-10,'minecraft:bookshelf')
    for x in (-30,-26,-22,-18):
        for y in range(79,84):p.put(x,y,-10,'minecraft:chiseled_quartz_block')
        p.put(x,84,-10,'mcwlights:golden_candle_holder',lit=True)
    for x in range(-26,-18):
        for z in range(-5,1):
            key='minecraft:white_carpet' if z in (-5,0) else 'minecraft:red_carpet' if x in (-26,-19) else 'minecraft:yellow_carpet' if x==-22 else 'minecraft:pink_carpet'
            p.put(x,79,z,key)
    for x in range(-23,-20):
        p.put(x,79,-2,'handcrafted:cherry_table',color='none',shape='single',waterlogged=False)
    p.put(-22,80,-2,'handcrafted:stackable_book',facing='south',books=3,seed=5)
    p.put(-21,80,-2,'mcwlights:golden_low_candle_holder',lit=True)
    p.put(-24,79,-2,'handcrafted:cherry_chair',facing='east',color='pink',waterlogged=False)
    p.put(-20,79,-2,'handcrafted:cherry_chair',facing='west',color='pink',waterlogged=False)
    p.put(-30,79,-4,'dawnoftimebuilder:limestone_fireplace',facing='east',horizontal_connection='none',vertical_connection='none',lit=True,waterlogged=False)
    for z in (-5,-3):
        p.stone(-30,79,z,-30,82,z)
    for z in range(-5,-2):p.put(-30,83,z,'minecraft:polished_diorite_slab',type='top',waterlogged=False)
    for x in (-28,-18):
        p.seat(x,79,2,'south')
        for u in (-1,1):
            p.put(x+u,82,3,'mcwwindows:pink_curtain',facing='north',tied='single')
        for u in (-1,0,1):p.put(x+u,84,3,'mcwwindows:golden_curtain_rod',facing='north')
    p.put(-17,79,-8,'handcrafted:cherry_cupboard',facing='west',type=1)
    p.put(-17,80,-8,'minecraft:potted_allium')
    p.put(-18,79,-7,'handcrafted:cherry_shelf',facing='west',shape='single',type=2)
    # An actual door, rather than glass above a wall, reaches the rose balcony.
    p.door(0,79,5,'south','mcwdoors:cherry_classic_door')
    p.fill(0,79,6,0,81,7,AIR)
    # Recompose the cloister: columns lie beside the two-block walking route,
    # real arches span between them, and the water garden has intimate pockets.
    for z in range(-19,9):
        if z%5==0:p.fill(16,69,z,16,74,z,AIR)
        p.stair(18,75,z,'east','minecraft:dark_prismarine_stairs')
        if z%8==0:p.put(18,75,z,'minecraft:chiseled_quartz_block')
    for z in (-15,-10,-5,0,5):
        p.put(18,69,z,'mythrais:arch_pillar_lower_full_stone',colour=0,facing='east')
        for y in range(70,73):p.put(18,y,z,'mythrais:arch_pillar_middle_full_stone',colour=0,facing='east')
        p.put(18,73,z,'mythrais:pillar_capital_01_stone',colour=0,facing='east',mirrored=False)
        p.put(18,74,z,'mythrais:arch_pillar_upper_full_stone',colour=0,facing='east')
    for start in (-15,-10,-5,0):
        for x in (17,18):
            p.stair(x,73,start+1,'north','minecraft:quartz_stairs','top')
            p.stair(x,73,start+4,'south','minecraft:quartz_stairs','top')
            for z in (start+2,start+3):p.put(x,74,z,p.masonry(x,74,z))
    for z in (-17,-7,3):
        p.put(28,69,z,'dawnoftimebuilder:marble_big_flower_pot',waterlogged=False)
        p.put(28,70,z,'minecraft:flowering_azalea')
        p.put(20,69,z,'supplementaries:urn',treasure=False,waterlogged=False)
    for z in range(-18,8):
        if z%8 not in (0,1):p.put(29,69,z,'minecraft:flowering_azalea_leaves',persistent=True,waterlogged=False,distance=1)
    # Seal the defects observed in actual views7/8 while retaining headroom.
    seal_tower_eaves(p,-11,0,5,68,23);seal_tower_eaves(p,10,-3,4,68,18)
    seal_tower_eaves(p,-33,-12,3,68,17)
    seal_gable_eaves(p,[(-31,5),(-15,5),(-15,-11),(-21,-11),(-21,-19),(-31,-19)],84,[(-32,-14,-13,6,85),(-32,-20,-20,-8,84)])
    seal_gable_eaves(p,bay,84,[(-27,-19,3,9,85)])
    seal_gable_eaves(p,[(-21,35),(-8,35),(-8,25),(-13,25),(-13,21),(-21,21)],76,[(-22,-8,20,35,77)],True)
    seal_gable_eaves(p,[(7,41),(16,41),(16,29),(10,29),(10,27),(7,27)],74,[(6,16,26,41,75)],True)
    # Dressed foundations meet the real66--68 ground under every raised part;
    # there is no synthetic grass sheet and no floating floor over a low spot.
    foundation_cells={(x,z) for (x,y,z),state in p.blocks.items() if y==64 and (x,y,z) not in p.terrain and state!=AIR}
    for x,z in foundation_cells:p.stone(x,60,z,x,63,z)
    p.rooms.append({'name':'Rear rose court and reflecting basin','floor':68,'purpose':'A real arrival beyond the gate and a quiet route to the future palace'})
    p.features.extend(['Broad native glazed windows with dressed heads and sills','Lodge shutters, flower boxes and inhabited bedchambers',
                       'Cleared walking lane and connected rear rose court','Projecting inhabited archive bay and connected study turret',
                       'Sealed wall-to-roof soffits','Furnished bookcase and fireplace salon','Arched native-column cloister and urn garden'])
    p.camera('Rear garden court',[11,71,-18],[0,76,-3])
    p.camera('Lodge window and flowerbox',[-4,68,29],[-9,69,26])


def room_record(p,name,polygon,floor,purpose):
    p.rooms.append({'name':name,'polygon':polygon,'floor':floor,'purpose':purpose})


def palace_rug(p,x,z,width,depth,y):
    # Woven long borders and narrow rose/gold fields, never a four-by-four
    # uniform carpet. The direction of each border has its own material.
    for dx in range(width):
        for dz in range(depth):
            key='minecraft:white_carpet' if dz in (0,depth-1) else 'minecraft:red_carpet' if dx in (0,width-1) else 'minecraft:magenta_carpet' if dx%4==0 else 'minecraft:pink_carpet'
            p.put(x+dx,y,z+dz,key)


def palace_seating(p,x,y,z):
    for dx in (-1,0,1):p.put(x+dx,y,z,'handcrafted:cherry_couch',facing='south',color='pink',shape='left' if dx==-1 else 'right' if dx==1 else 'middle',waterlogged=False)
    p.put(x,y,z+2,'handcrafted:cherry_table',color='white',shape='single',waterlogged=False)
    p.put(x,y+1,z+2,'minecraft:potted_pink_tulip');p.seat(x,y,z+4,'north')
    p.light(x-2,y+2,z+1)


def palace_bed(p,x,y,z):
    for dx in (0,1):
        for dz,part in ((0,'foot'),(-1,'head')):
            p.put(x+dx,y,z+dz,'handcrafted:cherry_fancy_bed',facing='north',part=part,color='pink',occupied=False,shape='left' if dx==0 else 'right')
    for dx in (-1,2):
        p.put(x+dx,y,z-1,'handcrafted:cherry_nightstand',facing='south',color='none',waterlogged=False)
        p.put(x+dx,y+1,z-1,'mcwlights:golden_low_candle_holder',lit=True)
        for dz in (-2,1):
            for dy in range(5):p.put(x+dx,y+dy,z+dz,'minecraft:cherry_fence',north=False,south=False,east=False,west=False,waterlogged=False)
    for dx in range(-1,3):
        for dz in range(-2,2):p.put(x+dx,y+5,z+dz,'minecraft:white_wool' if dx in (-1,2) else 'minecraft:pink_wool')


def palace_chandelier(p,x,ceiling,z):
    for y in range(ceiling-3,ceiling):p.put(x,y,z,'minecraft:chain',axis='y',waterlogged=False)
    p.put(x,ceiling-4,z,'mcwlights:golden_chandelier',lit=True)


def palace_shell(p,name,outline,floors,height,roofs):
    cells=p.shell(outline,floors[0],height)
    for x,z in cells:p.stone(x,60,z,x,floors[0]-1,z)
    for floor in floors[1:]:p.floor(cells,floor,wood=True)
    for roof in roofs:gable(p,*roof)
    seal_gable_eaves(p,outline,floors[0]+height,roofs)
    p.land_footprints.append({'name':name,'polygon':outline,'floor':floors[0],'requires':'Fresh native dry-ground admission before placement'})
    return cells


def palace_spire(p,cx,cz,r,floor,height,profile):
    cells=p.shell(octagon(cx,cz,r),floor,height)
    for x,z in cells:p.stone(x,60,z,x,floor-1,z)
    for level,radius in enumerate(profile):
        outer=polygon_cells(octagon(cx,cz,radius)) if radius else {(cx,cz)}
        inner=polygon_cells(octagon(cx,cz,radius-1)) if radius>1 else set()
        for x,z in outer-inner:
            keys=('minecraft:dark_prismarine','minecraft:oxidized_cut_copper','minecraft:weathered_cut_copper','minecraft:waxed_oxidized_cut_copper')
            p.put(x,floor+height+2+level,z,keys[(1 if x%4==0 else 0)+(2 if z%8==0 else 0)])
    top=floor+height+2+len(profile)
    p.put(cx,top,cz,'minecraft:chiseled_quartz_block');p.put(cx,top+1,cz,'minecraft:iron_bars')
    seal_tower_eaves(p,cx,cz,r,floor,height)
    p.land_footprints.append({'name':'Royal structure' if r==10 else 'Grand stair rotunda',
                             'polygon':octagon(cx,cz,r),'floor':floor,
                             'requires':'Fresh native dry-ground admission before placement'})
    return cells,top+1


def palace_stair(p,name,x,y,z,rise,facing,width=3):
    dx,dz={'north':(0,-1),'south':(0,1),'east':(1,0),'west':(-1,0)}[facing]
    for n in range(rise):
        for side in range(-(width//2),width-width//2):
            sx,sz=(x+side,z+dz*n) if dz else (x+dx*n,z+side)
            p.stair(sx,y+1+n,sz,facing,'minecraft:cherry_stairs')
            p.fill(sx,y+2+n,sz,sx,y+4+n,sz,AIR)
        p.routes.append({'name':name,'point':[x+dx*n,y+2+n,z+dz*n]})


def moved_window(p,old,new,facing,height,frame):
    # Retain explicit targets for the misaligned r1 glazing, restoring its
    # backing or air before cutting the real outer boundary. Never silently
    # omit old window/head/sill cells from a native revision.
    backing=p.blocks.copy()
    p.broad_window(*old,facing,height,frame=frame)
    changed={pos for pos,state in p.blocks.items() if backing.get(pos)!=state}
    for pos in changed:p.blocks[pos]=backing.get(pos,AIR);p.terrain.discard(pos)
    p.broad_window(*new,facing,height,frame=frame)


def palace_ornament(p,keep):
    """Inhabited wall depth and textiles, responding to actual r1 room images."""
    edge={q for q in keep if any((q[0]+dx,q[1]+dz) not in keep for dx,dz in ((1,0),(-1,0),(0,1),(0,-1)))}
    for floor in (68,78,88,98):
        for x,z in keep-edge:
            walls=[(dx,dz) for dx,dz in ((1,0),(-1,0),(0,1),(0,-1))
                   if (x+dx,z+dz) in edge and p.blocks.get((x+dx,floor+1,z+dz),AIR).split('[',1)[0] in MASONRY]
            if not walls:continue
            dx,dz=walls[0];face='west' if dx>0 else 'east' if dx<0 else 'north' if dz>0 else 'south'
            for y in (floor+1,floor+2):
                if p.blocks.get((x,y,z),AIR)!=AIR:continue
                if (x if dz else z)%4==0:p.put(x,y,z,p.masonry(x,y,z))
                else:p.put(x,y,z,'minecraft:cherry_trapdoor',facing=face,open=True,half='bottom',powered=False,waterlogged=False)
        # Side drapes frame the glazing instead of covering its middle. Rods
        # are three blocks wide with deliberate mullion gaps between bays.
        for cx in (49,54):
            for side in (-2,2):
                for y in range(floor+3,floor+(6 if floor==98 else 7)):
                    if p.blocks.get((cx+side,y,-32),AIR)==AIR:p.put(cx+side,y,-32,'mcwwindows:pink_curtain',facing='south',tied='single')
            for u in (-1,0,1):p.put(cx+u,floor+(6 if floor==98 else 7),-32,'mcwwindows:golden_curtain_rod',facing='south')
        for z in (-28,-19):
            p.put(60,floor+5,z,'minecraft:pink_wall_banner',facing='west')
            p.put(60,floor+3,z,'mcwlights:wall_lamp',facing='west',dye_color='yellow',lit=True,powered=False)
        p.put(43,floor+5,-18,'minecraft:purple_wall_banner',facing='east')
        p.put(43,floor+3,-18,'mcwlights:wall_lamp',facing='east',dye_color='yellow',lit=True,powered=False)
    # Twin baldaquins give the audience dais an authored royal focal point.
    for cx in (49,54):
        for x in (cx-1,cx+1):
            for y in range(70,74):p.put(x,y,-31,'minecraft:quartz_pillar',axis='y')
            p.put(x,74,-31,'minecraft:chiseled_quartz_block')
        p.put(cx,72,-32,'minecraft:pink_wall_banner',facing='south')
        for x in range(cx-2,cx+3):
            for z in range(-32,-28):p.put(x,75,z,'minecraft:pink_wool' if x%4==0 else 'minecraft:white_wool')
            if x==51:p.put(x,74,-29,'chipped:carved_calcite')
            else:p.stair(x,74,-29,'north','minecraft:quartz_stairs','top')
        for x in (cx-2,cx+2):p.put(x,76,-30,'mcwlights:golden_low_candle_holder',lit=True)
    for x in (44,59):
        p.put(x,69,-28,'chipped:carved_calcite')
        p.put(x,70,-28,'supplementaries:statue',facing='south',lit=False,powered=False,waterlogged=False)
    # A proper framed portal contains the lower music room instead of exposing
    # the back of its roof high inside the main ballroom.
    for x in (48,56):
        p.put(x,69,12,'mythrais:arch_pillar_lower_full_stone',colour=0,facing='north')
        for y in range(70,73):p.put(x,y,12,'mythrais:arch_pillar_middle_full_stone',colour=0,facing='north')
        p.put(x,73,12,'mythrais:pillar_capital_01_stone',colour=0,facing='north',mirrored=False)
    for x in range(49,56):
        p.stair(x,74 if x in (49,55) else 75,12,'south','minecraft:quartz_stairs','top')
    for z in (-1,5):
        p.put(43,69,z,'mythrais:arch_pillar_lower_full_stone',colour=0,facing='east')
        for y in range(70,77):p.put(43,y,z,'mythrais:arch_pillar_middle_full_stone',colour=0,facing='east')
        p.put(43,77,z,'mythrais:pillar_capital_01_stone',colour=0,facing='east',mirrored=False)
        p.put(43,82,z,'mcwlights:wall_lamp',facing='east',dye_color='yellow',lit=True,powered=False)
        p.put(44,73,z,'minecraft:pink_wall_banner',facing='east')
    for x in (49,59):
        # Attached piers provide actual support for these wall mounts and the
        # gallery above. Mounting them two cells inside the wall left air behind.
        p.stone(x,69,-8,x,77,-8)
        p.put(x,72,-7,'minecraft:purple_wall_banner',facing='south')
        p.put(x,75,-7,'mcwlights:wall_lamp',facing='south',dye_color='yellow',lit=True,powered=False)
    # Illuminated pantry shelves, vessels and a proper cooking alcove.
    for z in (-27,-26,-25,-23,-22,-21):
        p.put(74,73,z,'handcrafted:dark_oak_shelf',facing='west',shape='single',type=1)
        p.put(74,74,z,'supplementaries:jar',facing='west',light_level=0,waterlogged=False)
    for x in (67,68):
        p.put(x,69,-31,'handcrafted:dark_oak_cupboard',facing='south',type=1)
        p.put(x,70,-31,'minecraft:potted_allium')
    palace_chandelier(p,69,78,-25)
    for z in (-29,-21,-15):p.put(63,73,z,'mcwlights:wall_lamp',facing='east',dye_color='yellow',lit=True,powered=False)
    for x in (67,71):p.put(x,74,-32,'minecraft:cherry_trapdoor',facing='south',open=True,half='bottom',powered=False,waterlogged=False)
    # Different gable accents and one actual roof-light break the broad roof
    # planes without copying the same dormer onto every slope.
    p.broad_window(52,89,14,'south',3,frame='mcwwindows:cherry_window')
    p.put(52,93,15,'mythrais:clockface_small',facing='south')
    p.gothic(67,88,10,'south')
    for x in range(74,78):
        for z in (-10,-6):
            for y in range(89,94):p.put(x,y,z,p.masonry(x,y,z))
        for z in range(-9,-6):p.fill(x,90,z,x,92,z,AIR)
        for dz in range(-2,3):
            if x==74:p.stair(x,94+(2-abs(dz)),-8+dz,'south' if dz<0 else 'north','minecraft:dark_prismarine_stairs')
            else:p.put(x,94+(2-abs(dz)),-8+dz,'mcwroofs:dark_prismarine_roof',facing='south' if dz<0 else 'north',half='bottom',shape='straight')
    p.broad_window(77,90,-8,'east',3,frame='mcwwindows:diorite_window')
    p.features.extend(['Royal wall panelling, draped glazing and native tapestry lights',
                       'Twin audience canopies and statuary','Framed music portal with roof intrusion removed',
                       'Actual outer-boundary ballroom and service glazing','Pantry shelving and mixed gable/roof-light accents'])


def palace_final_detail(p):
    """Bounded finishing of observed r2 rooms; no added wing or room footprint."""
    def fresh(x,y,z,key,**props):
        if p.blocks.get((x,y,z),AIR)!=AIR:
            raise UserError(f'Decor would replace an occupied room target: {x},{y},{z}')
        p.put(x,y,z,key,**props)
    # Real cloth on the front of the throne backs is visible from the room;
    # the original seat blocks and their interaction remain untouched.
    for x in (49,54):
        p.put(x,71,-31,'minecraft:pink_wool');p.put(x,72,-31,'minecraft:magenta_wool')
        fresh(x,73,-30,'minecraft:purple_wall_banner',facing='south')
        p.put(x,74,-31,'minecraft:chiseled_quartz_block')
    for x in (45,58):
        fresh(x,69,-29,'handcrafted:cherry_bench',facing='east' if x==45 else 'west',color='pink',shape='single',waterlogged=False)
    fresh(46,69,-28,'handcrafted:cherry_table',color='white',shape='single',waterlogged=False)
    fresh(46,70,-28,'mcwlights:golden_low_candle_holder',lit=True)
    for z in (-29,-24):
        fresh(43,74,z,'minecraft:purple_wall_banner',facing='east')
        fresh(43,76,z,'mcwlights:wall_lamp',facing='east',dye_color='yellow',lit=True,powered=False)
    # The dance area stays genuinely open. Framed parquet and a thin woven
    # edge give the floor a purpose without filling it with decorative clutter.
    for x in range(49,62):
        for z in range(-2,10):
            p.paving(x,68,z,wood=True)
            if x in (49,61) or z in (-2,9):
                q=x if z in (-2,9) else z
                if p.blocks.get((x,69,z),AIR)==AIR:p.put(x,69,z,'minecraft:white_carpet' if q%4==0 else 'minecraft:magenta_carpet')
    # A laid refreshment table, cakes, serving dishes and a quiet window seat
    # occupy the margin while preserving the central dancing and exit routes.
    for x in (46,47):
        for z in range(4,9):fresh(x,69,z,'handcrafted:cherry_table',color='white',shape='single',waterlogged=False)
    fresh(46,70,6,'farmersdelight:roast_chicken_block',facing='east',servings=4)
    fresh(47,70,4,'handcrafted:white_plate',facing='south',pieces=3,waterlogged=False)
    fresh(47,70,8,'handcrafted:berry_jam_jar',facing='west',jars=2,waterlogged=False)
    fresh(46,70,4,'mcwlights:golden_low_candle_holder',lit=True)
    fresh(46,70,8,'minecraft:cake',bites=0)
    for z in (5,7):fresh(45,69,z,'handcrafted:cherry_chair',facing='east',color='pink',waterlogged=False)
    fresh(44,69,2,'handcrafted:cherry_bench',facing='east',color='pink',shape='single',waterlogged=False)
    # This clerestory had a second masonry backing plane; clear its actual
    # reveal, then flank it with native hanging velvet panels and gold rods.
    p.fill(51,89,13,53,91,13,AIR)
    for left in (47,57):
        for x in range(left,left+3):
            for y in range(81,86):p.put(x,y,12,'mcwwindows:purple_curtain',facing='north',tied='base_wave' if y==81 else 'none')
            p.put(x,86,12,'mcwwindows:golden_curtain_rod',facing='north')
    # Low reachable work surfaces and ingredient storage accompany the high
    # display shelves. Existing pots, sink, stove, barrels and jars are kept.
    for x in (69,70):
        for z in (-25,-24):fresh(x,69,z,'handcrafted:dark_oak_table',color='none',shape='single',waterlogged=False)
    fresh(69,70,-25,'farmersdelight:cutting_board',facing='south',waterlogged=False)
    fresh(70,70,-25,'farmersdelight:stuffed_pumpkin_block',facing='west',servings=4)
    fresh(69,70,-24,'handcrafted:white_plate',facing='south',pieces=2,waterlogged=False)
    fresh(70,70,-24,'handcrafted:berry_jam_jar',facing='south',jars=3,waterlogged=False)
    for x,key in ((67,'farmersdelight:tomato_crate'),(68,'farmersdelight:onion_crate'),(69,'farmersdelight:cabbage_crate')):
        fresh(x,69,-29,key)
    for z in (-26,-22):fresh(73,70,z,'handcrafted:berry_jam_jar',facing='west',jars=2,waterlogged=False)
    # A supported dormer apron closes the gap between the lower roof surface
    # and the new glazing; this is a detail within the existing roof envelope.
    p.stone(77,88,-10,77,89,-6)
    p.features.extend(['Visible upholstered throne backs and reception-side seating',
                       'Open framed parquet dance floor and usable refreshment table',
                       'True clerestory reveal with velvet panels','Reachable kitchen preparation, feast and produce storage'])


def palace(p):
    """Asymmetric inhabited palace beyond the accepted approach, not a big box."""
    # Distinct masses are drawn before their connections are cut. The main
    # octagonal royal structure rises above a lower rotunda and three broken
    # service/guest roofs; the ballroom has a deliberately lower, broader roof.
    keep,peak=palace_spire(p,52,-23,10,68,35,[11,11,10,10,9,9,8,8,7,7,6,6,5,5,4,4,3,3,2,2,1,0])
    for floor in (78,88,98):p.floor(keep,floor,wood=True)
    for level in (78,88,98):cornice(p,52,-23,11,level)
    keep_upper={pos:state for pos,state in p.blocks.items() if pos[0:3:2] in keep and 69<=pos[1]<=104}
    atrium,_=palace_spire(p,38,-14,7,68,22,[8,8,7,7,6,5,4,3,2,1,0])
    # The upper rotunda floor is a gallery around an actual stairwell.
    for x,z in atrium:
        if abs(x-38)>=4 or z<=-18 or z>=-10:p.paving(x,78,z,wood=True)
    atrium_upper={pos:state for pos,state in p.blocks.items() if (pos[0],pos[2]) in atrium-keep and 79<=pos[1]<=91}
    north=[(21,-35),(39,-35),(39,-32),(44,-32),(44,-22),(31,-22),(31,-25),(21,-25)]
    palace_shell(p,'North guest and household wing',north,[68,78],17,[(20,32,-36,-24,86),(31,45,-36,-21,86)])
    service=[(62,-33),(72,-33),(72,-29),(76,-29),(76,-2),(72,-2),(72,10),(64,10),(64,3),(62,3)]
    palace_shell(p,'Eastern kitchen, service and dining wing',service,[68,78],17,[(61,73,-34,-17,86),(61,77,-30,-13,85),(61,77,-14,-1,87),(61,73,-4,11,86)])
    ballroom=[(43,-9),(61,-9),(61,-4),(68,-4),(68,14),(46,14),(46,9),(42,9),(42,-1)]
    ball_cells=palace_shell(p,'Rose ballroom and music hall',ballroom,[68],17,[(42,62,-10,15,86),(59,69,-5,15,85)])
    for x,z in ball_cells:
        if x<=45 or x>=64 or z<=-6 or z>=11:p.paving(x,78,z,wood=True)
    # A narrow two-level crystal gallery joins the main structure to the ball
    # room. Neither the shell nor the room's internal passage is left implicit.
    gallery=[(49,-15),(56,-15),(56,-8),(49,-8)]
    palace_shell(p,'Crystal artifact gallery',gallery,[68,78],15,[(48,56,-16,-7,84)])
    # Attached walls/roofs stay outside the inhabited host rooms at every floor.
    # Actual images exposed both a royal roof intrusion and a blind hall wall.
    for host in (atrium_upper,keep_upper):
        for pos,state in host.items():p.blocks[pos]=state;p.terrain.discard(pos)
    # Glazing is aligned with usable floors. Windows have separate wide bays,
    # solid mullions, deep sills and arches; diagonal corners remain structural.
    for floor in (68,78,88,98):
        glazing_height=3 if floor==98 else 5
        for u in (-3,2):
            for z,face in ((-33,'north'),(-14,'south')):p.broad_window(52+u,floor+3,z,face,glazing_height,frame='mcwwindows:quartz_window')
            for x,face in ((42,'west'),(61,'east')):p.broad_window(x,floor+3,-23+u,face,glazing_height,frame='mcwwindows:quartz_window')
    for floor in (68,78):
        for z,face in ((-21,'north'),(-8,'south')):p.broad_window(38,floor+3,z,face,5,frame='mcwwindows:diorite_window')
        p.broad_window(31,floor+3,-14,'west',5,frame='mcwwindows:diorite_window')
    for floor in (68,78):
        for x in (25,30,35):p.broad_window(x,floor+3,-35,'north',4,frame='mcwwindows:cherry_window')
        moved_window(p,(75,floor+3,-30),(71,floor+3,-31),'east',4,'mcwwindows:diorite_window')
        p.broad_window(75,floor+3,-25,'east',4,frame='mcwwindows:diorite_window')
        for z in (-19,-13,-7):p.broad_window(75,floor+3,z,'east',4,frame='mcwwindows:diorite_window')
        p.broad_window(71,floor+3,5,'east',4,frame='mcwwindows:cherry_window')
        p.broad_window(68,floor+3,9,'south',4,frame='mcwwindows:cherry_window')
        for x in (49,54,59):p.broad_window(x,floor+3,13,'south',5,frame='mcwwindows:quartz_window')
        p.broad_window(43,floor+3,-4,'west',5,frame='mcwwindows:quartz_window')
        for old_z,new_z in ((2,2),(8,7)):
            moved_window(p,(43,floor+3,old_z),(42,floor+3,new_z),'west',5,'mcwwindows:quartz_window')
    for z in (-12,):
        p.broad_window(49,71,z,'west',4,frame='mcwwindows:cherry_window')
        p.broad_window(55,81,z,'east',3,frame='mcwwindows:cherry_window')
    # A stepped front music bay and projecting conservatory niche give the
    # south face an inhabited plan break rather than pasted flat decoration.
    bay=[(48,13),(57,13),(57,17),(55,19),(50,19),(48,17)]
    ball_envelope={pos:state for pos,state in p.blocks.items() if (pos[0],pos[2]) in ball_cells and pos[1]>=75}
    palace_shell(p,'Music-window performance bay',bay,[68],12,[(47,58,12,20,81)])
    p.broad_window(52,71,18,'south',5,frame='mcwwindows:cherry_window')
    for x in (48,56):p.broad_window(x,71,15,'west' if x==48 else 'east',4,frame='mcwwindows:quartz_window')
    # Image6 exposed the little bay's back gable hanging into the ballroom.
    # Restore the host wall/upper gallery and its roof above the real portal.
    for pos in list(p.blocks):
        if (pos[0],pos[2]) in ball_cells and pos[1]>=75:
            p.blocks[pos]=ball_envelope.get(pos,AIR);p.terrain.discard(pos)
    # Doors and arched connections are carved only after all touching shells.
    for floor in (68,78):
        p.fill(41,floor+1,-19,44,floor+4,-16,AIR)
        p.fill(49,floor+1,-15,54,floor+4,-13,AIR)
        p.fill(50,floor+1,-10,54,floor+4,-8,AIR)
        p.fill(60,floor+1,-25,63,floor+4,-22,AIR)
        p.fill(36,floor+1,-24,40,floor+4,-20,AIR)
        p.fill(63,floor+1,-4,66,floor+4,1,AIR)
    p.fill(31,69,-15,34,73,-13,AIR)
    p.fill(49,69,12,55,74,14,AIR)
    for x in range(20,34):
        for z in (-15,-14,-13):
            p.paving(x,68,z);p.fill(x,69,z,x,71,z,AIR)
    # First and return flights make a real generous grand stair. Upper service
    # stairs wind inside the main structure and have their own clear landing.
    palace_stair(p,'Grand rotunda stair first flight',35,68,-11,5,'north',3)
    for x in range(34,42):
        for z in (-16,-17):p.paving(x,73,z,wood=True)
    palace_stair(p,'Grand rotunda stair return flight',40,73,-15,5,'south',3)
    for x in range(38,44):
        for z in (-10,):p.paving(x,78,z,wood=True)
    ring=[(x,-3) for x in range(-3,4)]+[(3,z) for z in range(-2,4)]+[(x,3) for x in range(2,-4,-1)]+[(-3,z) for z in range(2,-3,-1)]
    for n in range(40):
        dx,dz=ring[n%len(ring)];nx,nz=ring[(n+1)%len(ring)];y=79+n//2
        facing='east' if nx>dx else 'west' if nx<dx else 'south' if nz>dz else 'north'
        p.fill(56+dx,y+1,-21+dz,56+dx,y+3,-21+dz,AIR)
        if n%2==0:p.stair(56+dx,y,-21+dz,facing)
        else:p.paving(56+dx,y,-21+dz,wood=True)
    # Public great hall: twin raised audience seats, a framed processional
    # runner, reception desks and sheltered conversation corners.
    for x in range(47,57):
        for z in range(-31,-27):p.paving(x,69,z)
    for x in (49,54):
        p.put(x,70,-30,'handcrafted:cherry_chair',facing='south',color='white',waterlogged=False)
        for yy in (70,71,72):p.put(x,yy,-31,'minecraft:chiseled_quartz_block')
        p.put(x,73,-31,'minecraft:gold_block')
        p.light(x-1,72,-30)
    palace_rug(p,49,-27,7,10,69)
    for x,z in ((45,-25),(58,-18)):
        p.put(x,69,z,'handcrafted:cherry_desk',facing='north',color='none',waterlogged=False)
        p.put(x,70,z,'handcrafted:stackable_book',facing='south',books=3,seed=7)
        p.put(x,69,z+1,'handcrafted:cherry_chair',facing='north',color='pink',waterlogged=False)
    palace_seating(p,47,69,-20);palace_chandelier(p,52,78,-23)
    # Gallery and salon above the formal hall: bookcase alcoves, working music
    # block, writing desk, paired rose seats and actual exterior viewing bay.
    palace_rug(p,45,-28,7,6,79);palace_seating(p,48,79,-21)
    for x in (45,46,47):
        for y in range(79,83):p.put(x,y,-30,'minecraft:bookshelf')
    p.put(49,79,-30,'xercamusic:piano',facing='south')
    p.put(51,79,-30,'handcrafted:cherry_bench',facing='north',color='pink',shape='single',waterlogged=False)
    p.put(46,79,-16,'handcrafted:cherry_desk',facing='north',color='none',waterlogged=False)
    p.put(46,80,-16,'supplementaries:globe',facing='south',powered=False,rotation=0,waterlogged=False)
    palace_chandelier(p,49,88,-22)
    # The royal suite is a furnished place to stay, not a bed in a vast empty
    # tower. Dressing, wash, fireside sitting and a private study have divisions.
    palace_bed(p,47,89,-27);palace_rug(p,45,-24,7,7,89)
    for x in (59,60):
        for dy,connection in ((0,'bottom'),(1,'middle'),(2,'top')):
            p.put(x,89+dy,-29,'mcwfurnitures:dark_oak_double_wardrobe',facing='west',connection=connection)
    palace_seating(p,47,89,-19)
    p.put(44,89,-23,'dawnoftimebuilder:limestone_fireplace',facing='east',horizontal_connection='none',vertical_connection='none',lit=True,waterlogged=False)
    p.put(46,89,-29,'handcrafted:cherry_desk',facing='south',color='none',waterlogged=False)
    p.put(46,90,-29,'handcrafted:stackable_book',facing='south',books=2,seed=4)
    for x in range(57,61):
        for z in range(-27,-23):
            p.put(x,89,z,p.masonry(x,89,z) if x in (57,60) or z in (-27,-24) else 'minecraft:water',**({} if x in (57,60) or z in (-27,-24) else {'level':0}))
    p.put(57,89,-29,'mcwfurnitures:dark_oak_kitchen_sink',facing='north',water=True)
    palace_chandelier(p,49,98,-24)
    # Observatory/map floor: chart tables, a ring of book alcoves, paired
    # window seats and a clear low-entity viewing room beneath the spire.
    for x in (48,49,50):p.put(x,99,-25,'handcrafted:cherry_table',color='white',shape='single',waterlogged=False)
    p.put(49,100,-25,'supplementaries:globe_sepia',facing='south',powered=False,rotation=0,waterlogged=False)
    for x in (45,46,47):
        for y in (99,100,101):p.put(x,y,-30,'minecraft:bookshelf')
    p.seat(49,99,-16,'north');p.seat(51,99,-16,'north');p.light(50,101,-16)
    p.put(48,99,-20,'minecraft:cartography_table');p.put(47,99,-20,'minecraft:lectern',facing='south',has_book=False,powered=False)
    # Ballroom: dance floor, perimeter viewing gallery, music bay and furnished
    # conversation pockets. The deliberately open dance floor has a clear use.
    for x in range(47,63):
        for z in range(-3,11):p.paving(x,68,z)
    for x,z in ((47,-4),(64,0),(63,8)):
        palace_seating(p,x,69,z)
    for x,z in ((51,1),(58,6)):palace_chandelier(p,x,84,z)
    for x in range(50,56):
        for z in range(14,17):p.paving(x,69,z,wood=True)
    p.put(52,70,16,'xercamusic:piano',facing='north');p.seat(52,70,15,'south')
    for x,z in ((45,-3),(64,7),(51,12)):
        p.put(x,69,z,'dawnoftimebuilder:marble_big_flower_pot',waterlogged=False)
        p.put(x,70,z,'minecraft:flowering_azalea')
    # Distinct service programmes share an honest side corridor and stair.
    for z in range(-30,8):
        for x in (63,64):p.fill(x,69,z,x,72,z,AIR)
    for z in range(-27,-20):
        p.put(73,69,z,'handcrafted:dark_oak_counter',facing='west',counter='calcite',type=1)
    p.put(73,69,-24,'mcwfurnitures:dark_oak_kitchen_sink',facing='west',water=True)
    p.put(70,69,-27,'farmersdelight:stove',facing='west',lit=True)
    p.put(70,70,-27,'farmersdelight:cooking_pot',facing='west',support='tray',waterlogged=False)
    p.put(71,69,-27,'minecraft:furnace',facing='west',lit=False)
    p.put(72,69,-27,'minecraft:smoker',facing='west',lit=False)
    for x in (67,68,69):p.put(x,69,-22,'handcrafted:cherry_table',color='none',shape='single',waterlogged=False)
    p.put(67,70,-22,'handcrafted:white_plate',facing='south',pieces=3,waterlogged=False)
    for z in (-18,-16,-14):
        for y in (69,70):p.put(73,y,z,'minecraft:barrel',facing='west',open=False)
    p.put(70,69,-16,'minecraft:crafting_table');p.put(70,69,-14,'minecraft:smithing_table')
    p.put(71,69,-14,'minecraft:anvil',facing='north')
    palace_stair(p,'Household service stair',66,68,-12,10,'south',2)
    for x in (68,69):
        for z in range(-19,-11):p.put(x,79,z,'handcrafted:cherry_table',color='white',shape='single',waterlogged=False)
    for z in (-18,-15,-12):
        p.put(67,79,z,'handcrafted:cherry_chair',facing='east',color='pink',waterlogged=False)
        p.put(70,79,z,'handcrafted:cherry_chair',facing='west',color='pink',waterlogged=False)
        p.put(68,80,z,'handcrafted:white_plate',facing='east',pieces=1,waterlogged=False)
        p.put(69,80,z,'mcwlights:golden_candle_holder',lit=True)
    palace_seating(p,68,79,1);p.put(70,79,5,'handcrafted:cherry_cupboard',facing='west',type=2)
    # Guest and staff wing: two differently arranged guest rooms upstairs,
    # household workroom and guard/utility room below, with clear gallery link.
    palace_bed(p,24,79,-31);palace_rug(p,23,-28,7,5,79)
    p.put(29,79,-33,'handcrafted:cherry_cupboard',facing='south',type=1)
    p.put(28,80,-33,'minecraft:potted_allium')
    palace_bed(p,35,79,-29);p.seat(37,79,-25,'north')
    p.put(39,79,-30,'handcrafted:cherry_desk',facing='west',color='none',waterlogged=False)
    p.put(39,80,-30,'handcrafted:stackable_book',facing='west',books=2,seed=2)
    for y in range(79,84):
        for z in range(-34,-25):
            if z!=-27:p.put(32,y,z,p.masonry(32,y,z))
    p.door(32,79,-27,'east')
    p.put(24,69,-31,'minecraft:crafting_table');p.put(26,69,-31,'minecraft:stonecutter',facing='south')
    p.put(28,69,-31,'minecraft:loom',facing='south');p.put(28,69,-29,'handcrafted:cherry_cupboard',facing='south',type=2)
    p.put(37,69,-28,'minecraft:smithing_table');p.put(39,69,-28,'minecraft:grindstone',face='floor',facing='south')
    p.put(40,69,-26,'minecraft:barrel',facing='west',open=False)
    palace_chandelier(p,26,85,-30);palace_chandelier(p,37,85,-27)
    # A tiny quiet reflective chamber, with glazed rose windows and paired
    # candlelit seats, occupies the north-east top corner of the household wing.
    p.put(68,79,-30,'minecraft:lectern',facing='south',has_book=False,powered=False)
    p.seat(66,79,-27,'north');p.seat(69,79,-27,'north')
    p.put(68,80,-31,'mcwlights:golden_triple_candle_holder',facing='south',lit=True)
    # A real cellar is carved inside the raised service base, with its own
    # descending stair and two-block headroom rather than an inaccessible tag.
    for x in range(66,75):
        for z in range(-20,-11):
            p.paving(x,64,z);p.fill(x,65,z,x,67,z,AIR)
    for n in range(5):
        for x in (70,71):
            z=-9-n;y=68-n
            p.stair(x,y,z,'south','minecraft:stone_brick_stairs');p.fill(x,y+1,z,x,y+3,z,AIR)
    for z in (-19,-17,-15):p.put(73,65,z,'minecraft:barrel',facing='west',open=False)
    p.put(67,65,-18,'handcrafted:cherry_shelf',facing='east',shape='single',type=2)
    p.put(67,65,-14,'handcrafted:cherry_cupboard',facing='east',type=1)
    p.light(69,67,-18);p.light(72,67,-14)
    # Small hidden study behind an ordinary operable door and a tied drape.
    # Its route is genuinely present; no claimed custom secret-door mechanism.
    for z in range(-31,-26):
        for y in range(79,84):p.put(40,y,z,p.masonry(40,y,z))
    p.door(40,79,-28,'east','mcwdoors:dark_oak_cottage_door')
    p.put(39,80,-28,'mcwwindows:pink_curtain',facing='west',tied='single')
    p.put(42,79,-30,'minecraft:barrel',facing='west',open=False)
    p.put(42,79,-28,'handcrafted:cherry_desk',facing='west',color='none',waterlogged=False)
    p.put(42,80,-28,'handcrafted:stackable_book',facing='west',books=3,seed=11)
    # The adjacent royal window's projecting sill otherwise enters the little
    # room at head height. The secret is a usable room, not merely a door tag.
    p.fill(41,79,-29,41,81,-27,AIR)
    p.light(41,82,-29)
    # A contained winter garden lies beyond the north audience doors, below a
    # private open-air terrace. Rose planters flank a clear two-block promenade.
    for x in range(44,61):
        for z in range(-38,-33):
            p.stone(x,60,z,x,67,z);p.paving(x,68,z)
            edge=x in (44,60) or z in (-38,-34)
            for y in range(69,75):
                key=p.masonry(x,y,z) if (x%4==0 and edge) else 'minecraft:white_stained_glass' if edge else AIR
                p.put(x,y,z,key)
            p.put(x,75,z,p.masonry(x,75,z) if x%4==0 or z%4==0 else 'minecraft:white_stained_glass')
    for x in (46,50,54,58):
        p.put(x,69,-36,'dawnoftimebuilder:marble_big_flower_pot',waterlogged=False)
        p.put(x,70,-36,'minecraft:flowering_azalea')
    p.fill(51,69,-34,53,72,-33,AIR)
    for x in range(48,57):
        for z in range(-36,-33):p.paving(x,88,z)
        if x%4:p.put(x,89,-36,'mcwfences:railing_quartz_wall',east=True,west=True,north=False,south=False,waterlogged=False)
        else:p.put(x,89,-36,'minecraft:chiseled_quartz_block')
    for x in (48,56):
        for z in (-35,-34):
            p.put(x,89,z,'mcwfences:railing_quartz_wall',north=True,south=True,east=False,west=False,waterlogged=False)
        p.put(x,90,-35,'minecraft:potted_pink_tulip')
        p.stair(x,87,-34,'south','minecraft:quartz_stairs','top')
    p.door(52,89,-33,'north','mcwdoors:cherry_classic_door');p.fill(52,89,-35,52,91,-34,AIR)
    # Safe interior balconies: these rails follow the actual floor/void edges.
    # Framed three-panel bays keep deliberate cadence in both orientations.
    def gallery_guard(x,z,axis):
        along=x if axis=='x' else z
        if along%4==0:p.put(x,79,z,p.masonry(x,79,z))
        else:p.put(x,79,z,'mcwfences:railing_quartz_wall',north=axis=='z',south=axis=='z',east=axis=='x',west=axis=='x',waterlogged=False)
    for x in range(46,64):
        for z in (-6,11):gallery_guard(x,z,'x')
    for z in range(-5,11):
        for x in (45,64):gallery_guard(x,z,'z')
    # The rotunda is an asymmetric U around its return stair. Leave its actual
    # upper landing open; frame only edges that overlook the full-height void.
    for x in range(35,42):gallery_guard(x,-18,'x')
    for z in range(-17,-10):
        gallery_guard(34,z,'z')
        if z<=-15:gallery_guard(42,z,'z')
    for x in range(35,39):gallery_guard(x,-10,'x')
    # Artifact niches are native block displays, not invented painting data.
    for floor in (68,78):
        for x,z in ((50,-12),(54,-11)):
            p.put(x,floor+1,z,'handcrafted:cherry_shelf',facing='east' if x==50 else 'west',shape='single',type=1)
            p.put(x,floor+2,z,'minecraft:potted_allium' if x==50 else 'handcrafted:stackable_book',**({} if x==50 else {'facing':'west','books':2,'seed':3}))
    # A terraced rose court and lower garden walk seat the public hall in the
    # natural slope. Its pathways have explicit stairs instead of sheer plinths.
    for x in range(31,44):
        for z in range(-6,15):
            # Window hoods and projecting sills above the garden do not remove
            # its foundation. Only an actual occupied room footprint excludes it.
            if (x,z) in ball_cells:continue
            floor=68 if z<=2 else 66 if z<=7 else 64
            p.stone(x,60,z,x,floor-1,z);p.paving(x,floor,z)
    for x in range(30,44):
        for z in (-1,0,1):p.paving(x,68,z);p.fill(x,69,z,x,71,z,AIR)
    for n in range(9):
        z=2+n;level=68-(n+1)//2
        for x in (36,37,38):
            p.stone(x,60,z,x,level-1,z)
            if n%2==0:p.stair(x,level,z,'north','minecraft:stone_brick_stairs')
            else:p.paving(x,level,z)
            p.fill(x,level+1,z,x,level+3,z,AIR)
    p.fill(42,69,-1,44,72,1,AIR)
    for x,z,y in ((32,5,67),(42,6,67),(33,12,65),(42,12,65)):
        p.put(x,y,z,'dawnoftimebuilder:marble_big_flower_pot',waterlogged=False)
        p.put(x,y+1,z,'minecraft:flowering_azalea');p.seat(x+1,y,z+1,'west')
    for x in range(45,72):
        for z in range(20,24):
            p.stone(x,60,z,x,63,z);p.paving(x,64,z)
    for x in (46,53,60,67):
        p.rose(x,65,22);p.seat(x+2,65,22,'north');p.light(x+1,67,23)
    # West base integration: landscaped stepped terraces, low retaining niches,
    # a real stair from the archive, and stable flowering climber clusters.
    for x in range(-41,-30):
        for z in range(-21,17):
            if any(p.blocks.get((x,y,z),AIR)!=AIR for y in range(65,80)):continue
            p.stone(x,60,z,x,63,z);p.paving(x,64,z)
            p.fill(x,65,z,x,67,z,AIR)
    p.door(-28,69,4,'south','mcwdoors:cherry_classic_door')
    for n in range(9):
        z=5+n;level=68-(n+1)//2
        for x in (-29,-28,-27):
            p.stone(x,60,z,x,level-1,z)
            if n%2==0:p.stair(x,level,z,'north','minecraft:stone_brick_stairs')
            else:p.paving(x,level,z)
            p.fill(x,level+1,z,x,level+3,z,AIR)
    for x in range(-40,-26):
        for z in (13,14,15):p.paving(x,64,z)
    for z in (-17,-7,3,13):
        p.seat(-38,65,z,'west');p.rose(-40,65,z+2);p.light(-39,67,z-1)
        for y in (65,66,67):p.put(-32,y,z,'minecraft:vine',east=True,west=False,north=False,south=False,up=False)
    for z in (-18,-8,2):
        p.put(-34,65,z,'dawnoftimebuilder:marble_big_flower_pot',waterlogged=False)
        p.put(-34,66,z,'minecraft:flowering_azalea')
    palace_ornament(p,keep)
    palace_final_detail(p)
    p.land_footprints.extend([
        {'name':'Royal winter conservatory','polygon':[(44,-38),(61,-38),(61,-33),(44,-33)],'floor':68,'requires':'Dry native land; no river infill'},
        {'name':'West terraced garden','polygon':[(-41,-21),(-30,-21),(-30,17),(-41,17)],'floor':64,'requires':'Dry native bank; outdoor landscape only'},
        {'name':'Ballroom terraced rose court','polygon':[(31,-6),(44,-6),(44,15),(31,15)],'floor':64,'requires':'Dry native land; three levels connected by stairs'}])
    # Explicit purposeful zones and cameras guide inspection, not acceptance.
    programmes=[('Grand reception and twin audience hall',octagon(52,-23,10),68,'Raised twin seats, reception desks, processional runner and salon corners'),
        ('Royal gallery and music salon',octagon(52,-23,10),78,'Books, piano, globe desk and paired conversation seats'),
        ('Royal suite, dressing and wash alcove',octagon(52,-23,10),88,'Canopied couple bed, wardrobes, private study, native fireplace and contained bath'),
        ('Observatory and strategy library',octagon(52,-23,10),98,'Chart tables, native globe, cartography and lectern workstations, window seats for two'),
        ('Grand staircase rotunda',octagon(38,-14,7),68,'Two substantial flights and an open interior gallery'),
        ('Rose ballroom and formal performance hall',ballroom,68,'Dance floor, viewing gallery, music bay and conversation pockets'),
        ('Formal dining and household sitting room',service,78,'Long laid table, chairs, candles and private side salon'),
        ('Royal kitchen',[(66,-29),(75,-29),(75,-20),(66,-20)],68,'Native stove and cooking pot, sink, prep counters, smoker and furnace'),
        ('Pantry, stores and castle utility',[(66,-20),(75,-20),(75,-11),(66,-11)],68,'Barrel storage, crafting, smithing and repair workstations'),
        ('Rose guest chamber',[(22,-34),(32,-34),(32,-25),(22,-25)],78,'Canopy bed, carpet, cabinet and garden-facing window'),
        ('Blue guest and writing chamber',[(33,-32),(43,-32),(43,-23),(33,-23)],78,'A differently oriented canopy bedroom, desk and reading chair'),
        ('Household craft and staff room',north,68,'Loom, stonecutting, workbench and cupboards'),
        ('Guard and service room',[(33,-31),(43,-31),(43,-23),(33,-23)],68,'Repair stations and guarded household access'),
        ('Candle reflection chamber',[(64,-32),(72,-32),(72,-25),(64,-25)],78,'Quiet reading, paired seats and candle focal point'),
        ('Crystal artifact corridor',gallery,68,'A two-level glazed connection with flower and book display niches')]
    programmes.extend([('Cellars and cool pantry',[(66,-20),(75,-20),(75,-12),(66,-12)],64,'Accessible lower store with its own descending service stair'),
        ('Hidden correspondence study',[(40,-31),(43,-31),(43,-27),(40,-27)],78,'Operable cottage door behind a tied curtain, desk and personal storage'),
        ('Royal rose viewing balcony',[(48,-36),(57,-36),(57,-33),(48,-33)],88,'A real door, railings, corbels and two-person open-air view'),
        ('Rose winter conservatory',[(44,-38),(61,-38),(61,-33),(44,-33)],68,'Glazed framed canopy and contained flower planters beside a clear promenade'),
        ('Terraced ballroom rose court',[(31,-6),(44,-6),(44,15),(31,15)],68,'Three planted levels joined by actual stairs and a lower garden walk')])
    for name,outline,floor,purpose in programmes:room_record(p,name,outline,floor,purpose)
    p.features.extend(['Asymmetric four-level octagonal royal structure above lower connected wings',
        'Grand rotunda stair and separate household circulation','Ballroom viewing gallery and projecting music bay',
        'Full royal, guest, formal, kitchen and service programmes','Terraced west garden seats the archive base in the actual slope'])
    p.camera('Full palace arrival',[9,79,23],[47,97,-19],'free')
    p.camera('Royal structure and lower wings',[77,91,26],[49,94,-14],'free')
    p.camera('Grand stair rotunda',[33,70,-12],[40,75,-13])
    p.camera('Twin audience hall',[52,70,-17],[52,73,-30])
    p.camera('Royal canopied chamber',[51,90,-20],[48,92,-28])
    p.camera('Ballroom and music bay',[49,70,0],[54,76,15])
    p.camera('Household kitchen',[68,70,-21],[72,71,-26])
    p.camera('West terraced garden',[-40,66,11],[-28,74,-5])


def bridge_deck(z):return 69+round(5*max(0,1-(abs(z)/49)**1.5))


def bridge(p):
    # A contained water/shore stage for visual comparison, never a proposed real river cut.
    for x in range(-30,31):
        bank=43+round(2*math.sin(x/8))
        for z in range(-55,56):
            p.put(x,60,z,'minecraft:stone',context=True)
            for y in (61,62,63):
                p.put(x,y,z,'minecraft:water' if abs(z)<bank and abs(x)<29 else 'minecraft:dirt' if y<63 else 'minecraft:grass_block',context=True,**({'level':0} if abs(z)<bank and abs(x)<29 else {}))
    arches=[(-32,11,64,5),(0,18,64,7),(32,11,64,5)]
    # The three unequal arches actually remain open; only abutments and cutwater piers occupy water.
    for z in range(-49,50):
        deck=bridge_deck(z);opening=None
        for center,radius,spring,rise in arches:
            if abs(z-center)<radius:
                opening=spring+math.ceil(rise*math.sqrt(1-((z-center)/radius)**2));break
        low=opening if opening is not None else 60
        for x in range(-4,5):
            p.stone(x,low,z,x,deck-1,z)
            if opening:p.fill(x,64,z,x,opening-1,z,AIR)
            previous=bridge_deck(z-1) if z> -49 else deck
            following=bridge_deck(z+1) if z<49 else deck
            if deck>previous:p.stair(x,deck,z,'south','minecraft:stone_brick_stairs')
            elif deck>following:p.stair(x,deck,z,'north','minecraft:stone_brick_stairs')
            else:p.paving(x,deck,z)
        for x in (-5,5):
            p.stone(x,deck-1,z,x,deck,z)
            if z%8==0:
                p.stone(x,deck+1,z,x,deck+2,z);p.light(x,deck+3,z)
            else:p.put(x,deck+1,z,'minecraft:stone_brick_wall',up=False,east='none',west='none',north='low',south='low',waterlogged=False)
        p.routes.append({'name':'Cambered pedestrian promenade','point':[0,deck+1,z]})
    # Proud arch rings at both faces; stepped haunches and a thin pale crown.
    for center,radius,spring,rise in arches:
        for z in range(center-radius+1,center+radius):
            ceiling=spring+math.ceil(rise*math.sqrt(1-((z-center)/radius)**2))
            for x in (-5,5):
                key='minecraft:polished_diorite_stairs' if abs(z-center)<=1 else 'minecraft:polished_andesite_stairs'
                p.stair(x,ceiling,z,'south' if z<center else 'north',key,'top')
                p.put(x,ceiling+1,z,p.masonry(x,ceiling+1,z))
    # Cutwaters have a pointed plan, battered base and a cap outside the main road.
    for center in (-20,20):
        outline=[(-8,center),(-5,center-3),(5,center-3),(8,center),(5,center+3),(-5,center+3)]
        footing=polygon_cells(outline)
        p.footings.append({'name':'Cutwater '+str(center),'cells':footing,'original_bottom':60})
        for x,z in footing:p.stone(x,60,z,x,67,z)
        # One upstream overlook and an opposed downstream bay, never a house under the span.
        side=-1 if center<0 else 1
        bay=[(side*4,center-3),(side*8,center-3),(side*10,center),(side*8,center+3),(side*4,center+3)]
        cells=polygon_cells(bay);height=bridge_deck(center)
        for x,z in cells:
            p.paving(x,height,z)
            edge=any((x+dx,z+dz) not in cells for dx,dz in ((1,0),(-1,0),(0,1),(0,-1)))
            if edge and abs(x)>5:p.put(x,height+1,z,'minecraft:andesite_wall',up=False,east='low',west='low',north='none',south='none',waterlogged=False)
        p.seat(side*7,height+1,center,'east' if side<0 else 'west',wood='dark_oak',color='brown')
    # Dressed newels, small rose niches and lantern brackets make the bridge human-scaled.
    for z in (-44,-28,-12,12,28,44):
        y=bridge_deck(z)
        for x in (-5,5):
            p.stone(x,y,z,x,y+2,z)
            p.put(x,y+3,z,'minecraft:polished_andesite_slab',type='bottom',waterlogged=False)
    for z in (-48,48):
        y=bridge_deck(z)
        for x in (-7,7):
            p.stone(x,63,z,x,y+2,z);p.light(x,y+3,z)
            p.rose(x+(1 if x>0 else -1),64,z)
    for sign in (-1,1):
        for n in range(1,12):
            z=sign*(49+n);height=69-(n+1)//2
            for x in range(-3,4):
                p.stone(x,63,z,x,height-1,z)
                if n%2:p.stair(x,height,z,'north' if sign>0 else 'south','minecraft:stone_brick_stairs')
                else:p.paving(x,height,z)
            p.routes.append({'name':'Stepped bank approach','point':[0,height+1,z]})
    p.features.extend(['Three unequal open stone arches','Cambered continuous pedestrian promenade',
        'Pointed cutwater piers and dressed arch rings','Two opposed pedestrian overlooks',
        'Bridge-only water footprint: no rooms or houses under any arch'])
    p.camera('Water-level arch profile',[-26,66,-8],[0,69,0],'free')
    p.camera('Shoreline three-quarter',[-25,69,46],[0,72,0],'free')
    p.camera('Road approach',[0,71,48],[0,76,0])
    p.camera('Overlook and promenade',[-8,74,-20],[1,74,12])
    p.camera('Elevated three-quarter',[28,88,37],[0,70,0],'free')
    p.camera('Central arch and cutwater',[19,65,-16],[-2,69,-1],'free')


def construct(registry,kind):
    if kind not in KINDS:raise UserError('Choose one representative prototype')
    p=Prototype(registry,kind)
    if kind in ('castle-gatehouse','castle-palace'):
        gatehouse(p);refine_gatehouse(p)
        if kind=='castle-palace':palace(p)
    else:bridge(p)
    # Terrain is a separate disposable display context, not authored architecture.
    architecture={pos:state for pos,state in p.blocks.items() if pos not in p.terrain}
    p.material_violations=material_runs(architecture)
    return p


def rotate_xz(x,z,degrees=0):
    """Clockwise compass turns: native north becomes east at ninety degrees."""
    if degrees not in (0,90,180,270):raise UserError('Use a quarter-turn orientation')
    for _ in range(degrees//90):x,z=-z,x
    return x,z


def rotate_state(p,state,degrees=0):
    """Rotate actual bridge state semantics, then revalidate the native palette.

    Rotation preserves stair left/right handedness and wall connection levels;
    directional property *names* move as well as facing property values.
    """
    if degrees not in (0,90,180,270):raise UserError('Use a quarter-turn orientation')
    key,_,fields=state.partition('[')
    values=dict(part.split('=',1) for part in fields.removesuffix(']').split(',') if part)
    turn=degrees//90;cardinals=('north','east','south','west')
    def direction(value):return cardinals[(cardinals.index(value)+turn)%4] if value in cardinals else value
    rotated={}
    for field,value in values.items():
        target=direction(field)
        if field in ('facing','direction','horizontal_facing'):value=direction(value)
        elif field=='axis' and turn%2 and value in ('x','z'):value='z' if value=='x' else 'x'
        # Vanilla rail shapes are included for a complete directional contract;
        # the current bridge itself has no rail or hidden operating network.
        elif field=='shape' and value in ('north_south','east_west'):
            if turn%2:value='east_west' if value=='north_south' else 'north_south'
        elif field=='shape' and value.startswith('ascending_'):value='ascending_'+direction(value[10:])
        elif field=='shape' and value in ('north_east','north_west','south_east','south_west'):
            pair={direction(v) for v in value.split('_')}
            value=('north' if 'north' in pair else 'south')+'_'+('east' if 'east' in pair else 'west')
        rotated[target]=value
    return p.state(key,**rotated)


def world_point(point,offset=(0,0),y_offset=0,rotation=0):
    x,y,z=point;rx,rz=rotate_xz(x,z,rotation)
    return [rx+offset[0],y+y_offset,rz+offset[1]]


def world_cameras(p,offset=(0,0),y_offset=0,rotation=0):
    result=[]
    for camera in p.cameras:
        position=world_point(camera['local_position'],offset,y_offset,rotation)
        target=world_point(camera['look_at'],offset,y_offset,rotation)
        dx,dy,dz=[b-a for a,b in zip(position,target)]
        result.append({'name':camera['name'],'position':position,'look_at':target,'mode':camera['mode'],
                       'yaw':math.degrees(math.atan2(-dx,dz)),
                       'pitch':-math.degrees(math.atan2(dy,math.hypot(dx,dz)))})
    return result


def admit_bridge_profile(p,profile,offset,y_offset,rotation):
    if p.kind!='rosebridge':raise UserError('The river profile admits only the bridge')
    report=profile.get('report',{});samples=profile.get('samples',[])
    if report.get('status')!='complete' or report.get('failures')!=0 or len(samples)<100:
        raise UserError('Use the completed zero-failure native river profile')
    if any(s.get('source')!='actual generated native chunk surface' for s in samples):raise UserError('A synthetic terrain profile is not bridge admission')
    bank_checks=[]
    for end in (-60,60):
        ex,_,ez=world_point((0,63,end),offset,y_offset,rotation)
        nearby=[s for s in samples if abs(s['x']-ex)<=4 and abs(s['z']-ez)<=4]
        if len(nearby)<9 or any(s.get('fluid') is not False or not ex-4<=s['x']<=ex+4 or abs(s.get('ground_y',s['y'])-(63+y_offset))>1 for s in nearby):
            raise UserError('The complete bridge approach is not supported by dry banks within one block of its end grade')
        bank_checks.append({'local_end':end,'world_center':[ex,ez],'sample_count':len(nearby),
                            'ground_range':[min(s.get('ground_y',s['y']) for s in nearby),max(s.get('ground_y',s['y']) for s in nearby)],'wet_samples':0})
    protected={tuple(be) for sample in samples for be in sample.get('block_entities',[])}
    footing_checks=[]
    for footing in p.footings:
        world=[world_point((x,60,z),offset,y_offset,rotation) for x,z in footing['cells']]
        xmin,xmax=min(v[0] for v in world),max(v[0] for v in world)
        zmin,zmax=min(v[2] for v in world),max(v[2] for v in world)
        nearby=[s for s in samples if xmin-4<=s['x']<=xmax+4 and zmin-4<=s['z']<=zmax+4]
        if len(nearby)<8 or any('ocean_floor_y' not in s for s in nearby):raise UserError('The pier has no bounded native seafloor profile')
        bottom=min(s['ocean_floor_y'] for s in nearby)-2
        if bottom-y_offset<48:raise UserError('The foundation would exceed its reviewed vertical envelope')
        for x,z in footing['cells']:p.stone(x,bottom-y_offset,z,x,footing['original_bottom']-1,z)
        footing_checks.append({'name':footing['name'],'survey_samples':len(nearby),'sampled_seafloor_range':[min(s['ocean_floor_y'] for s in nearby),max(s['ocean_floor_y'] for s in nearby)],
                               'world_foundation_bottom':bottom,'margin_below_minimum_sample':2,
                               'limit':'The native profile is sampled every four blocks; unsampled bed cells are not individually proven.'})
    # The real bank has meadow plants; establish explicit clear headroom rather
    # than relying on neighbour updates to remove them after paving.
    for route in p.routes:
        x,y,z=route['point'];width=4 if abs(z)<=49 else 3
        p.fill(-width,y,z,width,y+2,z,AIR)
    nearest=None
    for (x,y,z),state in p.blocks.items():
        if (x,y,z) in p.terrain:continue
        wx,wy,wz=world_point((x,y,z),offset,y_offset,rotation)
        for bx,by,bz in protected:
            distance=max(abs(wx-bx),abs(wy-by),abs(wz-bz))
            nearest=distance if nearest is None else min(nearest,distance)
            if distance<=1:raise UserError('A bridge target would enter the native block entity protection margin')
    p.material_violations=material_runs({pos:s for pos,s in p.blocks.items() if pos not in p.terrain})
    require_material_rule({pos:s for pos,s in p.blocks.items() if pos not in p.terrain},p.kind)
    return {'status':'SURVEYED BANK ADMISSION; native before/place/after and visual review pending',
            'banks':bank_checks,'footings':footing_checks,'protected_block_entities':len(protected),
            'minimum_chebyshev_distance_to_surveyed_BE':nearest,
            'world_binding':'Parent-supplied native profile in this staging runtime; the report itself contains no world identifier',
            'navigation':'Fixed small-boat arches only. The separate tall-ship bascule corridor remains required.'}


def join_bascule_landing(p,native_plan,offset,y_offset,rotation):
    if p.kind!='rosebridge' or offset!=(1248,-1104) or y_offset!=1 or rotation!=90:
        raise UserError('The reviewed bascule junction has exact site/elevation/orientation requirements')
    other={tuple(row[:3]):native_plan['palette'][row[3]] for row in native_plan['blocks']}
    if other.get((1200,70,-1104),AIR)==AIR or any(other.get((1200,y,-1104),AIR)!=AIR for y in (71,72,73)):
        raise UserError('The main bridge has no matching clear Y70 landing junction')
    trimmed=0
    for pos in list(p.blocks):
        if world_point(pos,offset,y_offset,rotation)[0]<=1200:
            del p.blocks[pos];p.terrain.discard(pos);trimmed+=1
    p.routes=[route for route in p.routes if world_point(route['point'],offset,y_offset,rotation)[0]>1200]
    p.routes.append({'name':'Level junction to the separate bascule landing','point':[0,70,47]})
    current={tuple(world_point(pos,offset,y_offset,rotation)):rotate_state(p,state,rotation)
             for pos,state in p.blocks.items() if pos not in p.terrain}
    shared=current.keys()&other.keys()
    if shared:raise UserError('Keep the two bridge source plans spatially disjoint; shared targets remain: '+str(sorted(shared)[:8]))
    return {'junction':[1200,70,-1104],'rosebridge_first_road_column_x':1201,
            'bascule_owns_x_at_or_west_of':1200,'trimmed_model_cells_including_display_context':trimmed,
            'shared_target_positions':0,'mechanical_or_moving_targets_owned_by_this_plan':0,
            'landing_status':'Planned native bascule interface; parent placement/verification required before connection',
            'changes_in_main_plan':'Open east railing; relocate the southern garden pocket; cede the east abutment face beneath the branch'}


def refine_bridge_bank(p,profile,offset,y_offset,rotation):
    """A low, open planted terrace on the actually dry north/east bank only."""
    if p.kind!='rosebridge' or offset!=(1248,-1104) or y_offset!=1 or rotation!=90:
        raise UserError('The bank garden has one reviewed dry-bank location')
    cells=polygon_cells([(-12,-50),(-9,-49),(-6,-52),(-6,-60),(-11,-60),(-12,-58)])
    samples={(s['x'],s['z']):s for s in profile.get('samples',[])}
    # Admit every footprint point against all surrounding four-metre samples,
    # not a single dry centre while planting over the wet south/east shoreline.
    def admit_cell(x,z):
        wx,_,wz=world_point((x,64,z),offset,y_offset,rotation)
        lo_x=math.floor(wx/4)*4;lo_z=math.floor(wz/4)*4
        corners=[samples.get((sx,sz)) for sx in (lo_x,lo_x+4) for sz in (lo_z,lo_z+4)]
        if any(s is None or s.get('fluid') is not False or not 63<=s.get('ground_y',-100)<=65 for s in corners):
            raise UserError('A bank garden cell lacks a surrounding dry native profile')
    for x,z in cells:admit_cell(x,z)
    before={pos:s for pos,s in p.blocks.items() if pos not in p.terrain}
    for x,z in cells:
        p.stone(x,63,z,x,63,z);p.paving(x,64,z)
        p.fill(x,65,z,x,67,z,AIR)
    # A genuine level branch connects to the existing descending ramp. The
    # ramp's final low step and all nine-block-wide main span remain unchanged.
    for x in range(-7,-2):
        for z in (-58,-59):
            p.paving(x,64,z);p.fill(x,65,z,x,67,z,AIR)
    # The low retaining seat wall ends in planted pockets and dressed urns;
    # there is no opaque hedge across the river view and no new habitation.
    for z in range(-58,-51):
        p.put(-12,64,z,p.masonry(-12,64,z))
        if z%4:p.put(-12,65,z,'minecraft:polished_diorite_slab',type='bottom',waterlogged=False)
        else:p.put(-12,65,z,'chipped:carved_calcite')
    for x,z in ((-10,-52),(-10,-57)):
        p.rose(x,65,z)
        p.put(x+1,65,z+1,'minecraft:potted_white_tulip')
    p.seat(-8,65,-54,'east',wood='dark_oak',color='brown')
    p.put(-9,65,-55,'handcrafted:dark_oak_table',color='none',shape='single',waterlogged=False)
    p.put(-9,66,-55,'minecraft:potted_allium')
    p.put(-8,65,-58,'dawnoftimebuilder:marble_big_flower_pot',waterlogged=False)
    p.put(-8,66,-58,'minecraft:flowering_azalea')
    for x,z in ((-11,-59),(-7,-52)):
        p.put(x,65,z,p.masonry(x,65,z));p.light(x,66,z)
    protected={tuple(be) for s in profile.get('samples',[]) for be in s.get('block_entities',[])}
    changed={pos for pos,s in p.blocks.items() if pos not in p.terrain and before.get(pos)!=s}
    footprint={(x,z) for x,y,z in changed}
    for x,z in footprint:admit_cell(x,z)
    for x,y,z in changed:
        wx,wy,wz=world_point((x,y,z),offset,y_offset,rotation)
        if any(max(abs(wx-bx),abs(wy-by),abs(wz-bz))<=1 for bx,by,bz in protected):
            raise UserError('The bank terrace enters a surveyed block entity margin')
    p.features.extend(['Dry north/east bank rose terrace with an open river view',
                       'Usable ramp branch, low retaining seats, urns and supported garden lanterns'])
    p.routes.append({'name':'Level dry-bank garden branch','point':[-5,65,-58]})
    p.routes.append({'name':'Rose terrace standing pocket','point':[-8,65,-56]})
    p.camera('Dry bank rose terrace',[-11,67,-59],[0,73,-35])
    return {'site':'North/east dry bank only; wet south/east shoreline untouched',
            'authored_footprint_cells':len(footprint),'floor_world_y':65,
            'sample_admission':'All four surrounding four-metre samples are dry and at Y63..65 for every terrace footprint cell',
            'limits':'Sampled profile is planning evidence; parent native before-state/dry-site and traversal review remain required',
            'additional_habitable_rooms':0,'moving_or_mechanical_changes':0}


def payload(p,registry,backup,offset=(0,0),y_offset=0,include_context=False,rotation=0):
    if rotation and p.kind!='rosebridge':raise UserError('Custom castle roof parts require their own native rotation review; only the bridge is rotatable')
    selected={(rotate_xz(x,z,rotation)[0],y,rotate_xz(x,z,rotation)[1]):rotate_state(p,state,rotation)
              for (x,y,z),state in p.blocks.items() if include_context or (x,y,z) not in p.terrain}
    palette=sorted(set(selected.values()));indices={state:i for i,state in enumerate(palette)};ox,oz=offset
    positions=[[x+ox,y+y_offset,z+oz,indices[state]] for (x,y,z),state in sorted(selected.items())]
    return {'format':'awft-native-settlement:1','name':'Artistic prototype: '+p.kind,'created':utcnow(),
        'seed':registry['seed'],'world_path':registry['world_path'],'backup_sha256':backup,
        'bounds':[min(row[0] for row in positions),min(row[2] for row in positions),max(row[0] for row in positions),max(row[2] for row in positions)],
        'palette':palette,'blocks':positions,'block_entities':[],'commands':[],'landmarks':[],
        'validation':'STAGING ONLY. Original local-origin architecture; no artistic or functional acceptance from placement.'}


def prepare(home,kind,x=0,z=0,y_offset=None,include_context=False,rotation=0,previous_plan=None,profile=None,junction_plan=None,bank_landscape=False):
    layout=Layout(Path(home))
    if 'staging' not in [part.lower() for part in layout.home.parts]:
        raise UserError('This authoring lane only binds a separately hosted staging runtime')
    registry_path=layout.state/'settlement/registry.json';backup_path=layout.state/'settlement/backup-receipt.json'
    registry=read_json(registry_path,{});backup=read_json(backup_path,{})
    if not Path(registry.get('world_path','')).resolve().is_relative_to(layout.home) or backup.get('verified') is not True:
        raise UserError('A real staging registry and its verified staging backup receipt are required')
    p=construct(registry,kind)
    y_offset=(4 if kind.startswith('castle-') else 0) if y_offset is None else y_offset
    if type(y_offset) is not int or abs(y_offset)>24:raise UserError('Prototype elevation must be explicit and bounded')
    profile_admission=None
    if kind=='rosebridge' and not include_context:
        if not profile:raise UserError('A real river bridge export requires its fresh native bank/seafloor profile')
        profile_path=Path(profile).resolve()
        if not profile_path.is_relative_to(layout.home):raise UserError('Use the parent-supplied profile in this staging runtime')
        profile_admission=admit_bridge_profile(p,read_json(profile_path,{}),(x,z),y_offset,rotation)
        profile_admission['profile_sha256']=digest(profile_path)
    junction=None
    if junction_plan:
        junction_path=Path(junction_plan).resolve()
        if not junction_path.is_relative_to(layout.staging.resolve()) or include_context:raise UserError('Use an immutable same-stage bascule plan without synthetic landscape')
        joined=read_json(junction_path,{})
        if joined.get('world_path')!=registry['world_path'] or joined.get('seed')!=registry['seed']:raise UserError('The bascule interface belongs to another world')
        junction=join_bascule_landing(p,joined,(x,z),y_offset,rotation)
        junction['bascule_plan_sha256']=digest(junction_path)
        if profile_admission:
            for bank in profile_admission['banks']:
                if bank['local_end']==60:bank['not_emitted']='Dry descending tail replaced by the separately verified level bascule landing'
    bank_admission=None
    if bank_landscape:
        if not profile_admission or not junction or include_context:raise UserError('Bank landscaping requires the surveyed, joined actual bridge')
        bank_admission=refine_bridge_bank(p,read_json(Path(profile),{}),(x,z),y_offset,rotation)
        bank_admission['profile_sha256']=digest(Path(profile))
    require_material_rule({pos:s for pos,s in p.blocks.items() if pos not in p.terrain},kind)
    value=payload(p,registry,backup['sha256'],(x,z),y_offset,include_context,rotation);raw=(json.dumps(value,separators=(',',':'))+'\n').encode()
    predecessor=None;cell_raw=None
    if previous_plan:
        previous_path=Path(previous_plan).resolve()
        if not previous_path.is_relative_to(layout.staging.resolve()):raise UserError('A predecessor must be an immutable plan in this same staging runtime')
        previous=read_json(previous_path,{})
        if previous.get('world_path')!=registry['world_path'] or previous.get('seed')!=registry['seed']:
            raise UserError('The predecessor belongs to a different native world')
        old={tuple(row[:3]):previous['palette'][row[3]] for row in previous['blocks']}
        current={tuple(row[:3]):value['palette'][row[3]] for row in value['blocks']}
        if old.keys()-current.keys():raise UserError('A revision must explicitly retain or clear every predecessor target; silent omissions are refused')
        predecessor={'plan_sha256':digest(previous_path),'targets':len(old),
                     'retained_unchanged':sum(current[pos]==state for pos,state in old.items()),
                     'changed':sum(current[pos]!=state for pos,state in old.items()),
                     'new_targets':len(current.keys()-old.keys()),'silently_removed':0,
                     'before_state':'The parent must verify predecessor custody and inspect new target states; no air or inventory clearance is inferred'}
        cells={'format':'awft-artistic-revision-cells:1','predecessor_sha256':digest(previous_path),
               'target_sha256':hashlib.sha256(raw).hexdigest(),
               'columns':['x','y','z','expected_predecessor_state_or_null','target_state'],
               'null_before_state':'Unknown native state. Must be inspected and admitted by the parent; never interpreted as air.',
               'records':[[*pos,old.get(pos),state] for pos,state in sorted(current.items())]}
        cell_raw=(json.dumps(cells,separators=(',',':'))+'\n').encode()
        predecessor['cells']={'file':'revision-cells.json','sha256':hashlib.sha256(cell_raw).hexdigest(),
                              'records':len(current),'columns':cells['columns']}
    sha=hashlib.sha256(raw).hexdigest();target=layout.staging/('prototype-'+kind+'-'+sha[:16])
    manifest={'format':'awft-artistic-landmark-prototype:1','at':utcnow(),'prototype':kind,
        'plan_sha256':sha,'source_sha256':digest(Path(__file__)),'registry_sha256':digest(registry_path),
        'backup_receipt_sha256':digest(backup_path),'placements':len(value['blocks']),'local_origin_offset':[x,y_offset,z],'rotation_degrees_clockwise':rotation,
        'rooms':p.rooms,'features':p.features,'routes':p.routes,'cameras':p.cameras,'land_footprints':p.land_footprints,
        'predecessor':predecessor,
        'profile_admission':profile_admission,
        'bank_landscape':bank_admission,
        'junction':junction,
        'world_cameras':world_cameras(p,(x,z),y_offset,rotation),
        'world_routes':[dict(route,point=world_point(route['point'],(x,z),y_offset,rotation)) for route in p.routes],
        'display_context_included':include_context,'site_admission':'Not a native terrain proof. Parent must confirm dry land at every inhabited footprint before placement; no habitation in a channel or underspan.',
        'material_violations':p.material_violations,'scope':'Staging prototype, never deployed; graphical review and revision required'}
    meta=(json.dumps(manifest,indent=2)+'\n').encode()
    if target.exists() or len(raw)+len(meta)+len(cell_raw or b'')>OUTPUT_LIMIT:raise UserError('Preserve earlier prototypes or split the bounded output')
    Storage(layout).reserve(OUTPUT_LIMIT,target=target);target.mkdir(parents=True)
    atomic_write(target/'prototype.json',raw);atomic_write(target/'manifest.json',meta)
    if cell_raw is not None:atomic_write(target/'revision-cells.json',cell_raw)
    return {'plan':str(target/'prototype.json'),'sha256':sha,'manifest':str(target/'manifest.json'),'native_action':'Not performed'}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--home',type=Path,required=True)
    parser.add_argument('--prototype',choices=KINDS,required=True);parser.add_argument('--x',type=int,default=0);parser.add_argument('--z',type=int,default=0)
    parser.add_argument('--y-offset',type=int);parser.add_argument('--include-context',action='store_true',help='Only for an explicitly disposable comparison canvas; alters synthetic context land/water')
    parser.add_argument('--rotation',type=int,choices=(0,90,180,270),default=0,help='Clockwise compass rotation; bridge only until native custom roof rotation review')
    parser.add_argument('--previous-plan',type=Path,help='Immutable predecessor in this staging runtime; rejects silently dropped targets')
    parser.add_argument('--profile',type=Path,help='Fresh native bank and seafloor survey required for actual river bridge export')
    parser.add_argument('--junction-plan',type=Path,help='Exact reviewed same-stage bascule plan; trims the western tail and refuses all shared targets')
    parser.add_argument('--bank-landscape',action='store_true',help='Reviewed dry north/east terrace; actual profile and joined bridge required')
    args=vars(parser.parse_args());args['kind']=args.pop('prototype');print(json.dumps(prepare(**args),indent=2))
