"""Eight inhabited, articulated houses on the saved dry north-bank bend.

Original source geometry only. A separate parent-owned native before/place/
normal-shape/strict-verify and actual eye-level review must follow. The accepted
Rose Reach source is read-only; no inventories or block entities are replayed.
"""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import time

from control_room.common import UserError,digest,read_json
from tools.artistic_bridge_refinement import flatten
from tools.artistic_materials import require_material_rule,require_outdoor_rule
from tools.artistic_north_bank_east import (AIR,GROUND,SOFT,NORTH_SOFT,MIB,EastPlan,Lot,
    NorthTerrain,FACES,boundary,house_shell,make_roof,facade_windows,canonical_parts,
    pave,native_payload,preservation,is_tree,base)
from tools.playtest import guard

ROSE_REL='staging/north-bank-rose-reach-1793151923325885400/prototype.json'
ROSE_SHA='831a8e6eb1e757502328d259d0846fff14e325e8ed704dae527cd7fc90cdbc37'

# Shared structural joinery is not a shared house template. Upper footprints,
# roof profiles, working rooms, household stories and street corners differ.
HOUSES=(
 Lot('seabird-ledger','The Seabird Ledger','Customs clerk and household',(1237,-1207),(9,9),2,'south','cropped_sw','saltbox',
     ('minecraft:bricks','dawnoftimebuilder:blue_plastered_stone'),
     ('Customs desk, sea chest and sheltered kitchen','Reader bedroom, herb window and sea-facing tea loggia'),
     'Chamfered brick study, recessed entry with slender hood and a blue loggia above'),
 Lot('three-kestrels','Three Kestrels House','Crew family household',(1248,-1205),(9,11),3,'south','recess_ne','gambrel',
     ('minecraft:stone_bricks','dawnoftimebuilder:yellow_plastered_stone','minecraft:white_terracotta'),
     ('Family supper table and cooking hearth','Children’s shared reading and sleeping room','Set-back attic bedroom opening to a washing terrace'),
     'Three unequal window bays and an actual two-metre set-back top floor with a guarded terrace'),
 Lot('brass-finch','The Brass Finch','Watch and instrument repair',(1266,-1207),(9,9),3,'south','cropped_ne','steep',
     ('minecraft:bricks','minecraft:green_terracotta','dawnoftimebuilder:plastered_stone'),
     ('Clock bench, brass instrument display and customer seat','Clockmaker kitchen, books and supper corner','High-light bedroom, writing desk and roof study'),
     'Narrow copper-seamed carved gable, projecting instrument window and warm clock workshop'),
 Lot('anchor-apple','Anchor & Apple','Fresh produce and provisions',(1281,-1206),(9,11),2,'south','recess_sw','half_hip',
     ('minecraft:stone_bricks','dawnoftimebuilder:red_plastered_stone'),
     ('Recessed produce counter, baskets and sheltered pantry','Shopkeeper apartment with window breakfast and sewing nook'),
     'A genuinely recessed vegetable shop, low hipped end and a flower-framed kitchen bay'),
 Lot('ink-tern','Ink & Tern','Scribe, bindings and household',(1296,-1207),(9,11),3,'south','cropped_nw','cross_gable',
     ('minecraft:bricks','minecraft:cyan_terracotta','dawnoftimebuilder:plastered_stone'),
     ('Ink counter, book repair and two writing desks','Library kitchen and reading salon','West-set-back bedroom and slim private roof gallery'),
     'Angled scribe corner, transverse gable, west upper gallery and actual recessed book alcoves'),
 Lot('reed-resonance','Reed & Resonance','Music and instrument repair',(1312,-1209),(9,11),2,'south','recess_se','gambrel',
     ('minecraft:bricks','dawnoftimebuilder:yellow_plastered_stone'),
     ('Instrument workbench, music shelf and intimate performance corner','Repairer’s household supper, bed and music-reading desk'),
     'A deep instrument window, low sound-board loft and a short supported shopfront hood'),
 Lot('rosemary-court','The Rosemary Court','Gardener household',(1328,-1206),(9,11),2,'south','cropped_nw','saltbox',
     ('minecraft:stone_bricks','dawnoftimebuilder:green_plastered_stone'),
     ('Potting counter, herb pantry and bright gardener kitchen','Flower-window bedroom, seed library and armchair nook'),
     'Terrain-fitted two-course stone foot, contained herb garden, garden oriel and stepped roof'),
 Lot('salt-wind','The Salt-Wind House','Coastal family household',(1350,-1207),(9,11),3,'west','cropped_ne','steep',
     ('minecraft:bricks','dawnoftimebuilder:blue_plastered_stone','minecraft:light_gray_terracotta'),
     ('Sea-chest sitting room, galley and dining corner','Family library and shared bedroom','North-set-back lookout bedroom with a small roof terrace'),
     'A coastal cut corner, narrow vertical sea bay, inset upper room and supported gallery'),
)

ITEMS={
 'seabird-ledger':('minecraft:paper','minecraft:book','minecraft:compass','minecraft:ink_sac'),
 'three-kestrels':('minecraft:bread','minecraft:apple','minecraft:book','minecraft:string'),
 'brass-finch':('minecraft:clock','minecraft:gold_ingot','minecraft:copper_ingot','minecraft:amethyst_shard'),
 'anchor-apple':('minecraft:apple','minecraft:carrot','minecraft:potato','minecraft:beetroot'),
 'ink-tern':('minecraft:book','minecraft:paper','minecraft:feather','minecraft:ink_sac'),
 'reed-resonance':('minecraft:note_block','minecraft:music_disc_cat','minecraft:string','minecraft:book'),
 'rosemary-court':('minecraft:wheat_seeds','minecraft:flower_pot','minecraft:allium','minecraft:honey_bottle'),
 'salt-wind':('minecraft:spyglass','minecraft:compass','minecraft:nautilus_shell','minecraft:book'),
}

SETBACKS={'three-kestrels':('south',2),'ink-tern':('west',1),'salt-wind':('north',1)}


def forget(p,positions):
    """Change only new source geometry, before any placement or furnishings."""
    for q in positions:
        if p.owners.get(q)!=p.group:raise UserError('A source redesign may not touch another building')
        p.blocks.pop(q,None);p.priority.pop(q,None);p.owners.pop(q,None);p.tags.pop(q,None)


def articulated_shell(p,lot):
    cells,floor,door=house_shell(p,lot)
    for q,tag in list(p.tags.items()):
        if p.owners.get(q)==lot.name:p.tags[q]=tag.replace('Rose Reach','Compass Bend')
    # All three buildings change real upper massing. Old source roof/walls are
    # discarded here, not applied and erased in the world.
    if lot.ident in SETBACKS:
        face,amount=SETBACKS[lot.ident];top=floor+4*(lot.levels-1)
        x0,x1=min(x for x,z in cells),max(x for x,z in cells);z0,z1=min(z for x,z in cells),max(z for x,z in cells)
        inner={q for q in cells if not (face=='south' and q[1]>z1-amount or face=='west' and q[0]<x0+amount or face=='north' and q[1]<z0+amount)}
        reset=[q for q in p.blocks if p.owners[q]==lot.name and q[1]>=top+1]
        forget(p,reset)
        skirt={(x+dx,z+dz) for x,z in cells for dx in (-1,0,1) for dz in (-1,0,1)}
        for x,z in skirt:
            for y in range(top+1,floor+lot.levels*4+9):p.put((x,y,z),'minecraft:air',priority=10)
        for x,z in boundary(inner):
            for dy in (1,2,3):
                post=(x-x0)%3==0 if z in (min(q[1] for q in inner),max(q[1] for q in inner)) else (z-z0)%3==0
                p.put((x,top+dy,z),'minecraft:stripped_dark_oak_log' if post else lot.finish[-1],**({'axis':'y'} if post else {}))
        p.floor(inner,top+4);facade_windows(p,lot,inner,top,lot.levels-1)
        make_roof(p,lot,inner,top+4)
        row=next(r for r in p.rooms if r['building']==lot.ident and r['level']==lot.levels-1)
        row['floor_cells']=[list(q) for q in sorted(inner)];row['actual_setback']={'side':face,'metres':amount}
        terrace=cells-inner
        for x,z in terrace:
            # Only the outer strip is a parapet. Corner posts divide the
            # nine-metre gallery, preserving genuine access and sky opening.
            edge=z==z1 if face=='south' else x==x0 if face=='west' else z==z0
            if edge:
                if (x-x0)%4==0 if face in ('north','south') else (z-z0)%4==0:
                    p.put((x,top+1,z),'minecraft:stripped_oak_log',priority=86,axis='y')
                else:p.put((x,top+1,z),'minecraft:dark_oak_fence',priority=86,north=face in ('west','east'),south=face in ('west','east'),east=face in ('north','south'),west=face in ('north','south'),waterlogged=False)
        # A real door leads onto each gallery, while the right-hand stair
        # stays inside the upper room. This is not an inaccessible roof prop.
        xx,zz=(lot.center[0],max(z for x,z in inner)) if face=='south' else (min(x for x,z in inner),lot.center[1]) if face=='west' else (lot.center[0],min(z for x,z in inner))
        for dy,half in ((1,'lower'),(2,'upper')):p.put((xx,top+dy,zz),'mcwdoors:dark_oak_cottage_door',priority=98,facing={'south':'north','west':'east','north':'south'}[face],half=half,hinge='right',open=False,powered=False)
        row['gallery_door']=[xx,top+1,zz]
    # A deliberately expressed masonry collar breaks the low gardener's
    # sloping foundation vertically; no hills are flattened or filled.
    if lot.ident=='rosemary-court':
        for x,z in cells:
            q=x,floor-2,z
            if q in p.blocks:
                joint=(z-min(b for a,b in cells))%8==7
                key=('minecraft:mossy_stone_bricks' if (x-min(a for a,b in cells))%4==0 else 'minecraft:polished_andesite') if joint else ('minecraft:chiseled_stone_bricks' if (x-min(a for a,b in cells))%4==0 else 'minecraft:andesite')
                p.put(q,key,priority=57)
    return cells,floor,door


def clear_fixture(p,q):
    return tuple(q) not in p.walk and p.priority.get(tuple(q),0)<=90 and base(p.blocks.get(tuple(q),'minecraft:air')) in AIR


def furniture(p,q,key,*,support=None,**props):
    """A rejected optional object stays absent, never replaces another object."""
    if not clear_fixture(p,q):return False
    p.fixture(q,key,support=support,**props);return True


def furniture_story(p,lot,cells,floor,door):
    x0,x1=min(x for x,z in cells),max(x for x,z in cells);z0,z1=min(z for x,z in cells),max(z for x,z in cells)
    entry=z1-3;landing=entry-5;stairx=x1-1
    for level in range(lot.levels-1):
        f=floor+4*level
        for n in range(1,5):
            q=stairx,f+n,entry-n;p.put(q,'minecraft:spruce_stairs',priority=99,facing='north',half='bottom',shape='straight',waterlogged=False)
            for dy in (1,2,3):p.put((q[0],q[1]+dy,q[2]),'minecraft:air',priority=100)
    for level in range(lot.levels):
        f=floor+4*level;record=next(r for r in p.rooms if r['building']==lot.ident and r['level']==level)
        room=set(map(tuple,record['floor_cells']));inside=room-boundary(room)
        lx,rx=min(x for x,z in room),max(x for x,z in room);nz,sz=min(z for x,z in room),max(z for x,z in room)
        axis=lot.center[0]
        aisle={(axis,z) for z in range(nz+1,sz)}
        if level<lot.levels-1:aisle|={(x,entry) for x in range(axis,stairx+1)}
        if level>0:aisle|={(x,landing) for x in range(axis,stairx+1)}
        if lot.face=='west':aisle|={(x,lot.center[1]) for x in range(lx+1,axis+1)}
        for x,z in aisle:
            if (x,z) in inside:
                for dy in (1,2):p.walk.append((x,f+dy,z))
        start=len(p.fixtures)
        # Half-height coffers, lengthwise ribs and little corner brackets leave
        # at least two entire metres free, not a low oversized chandelier.
        for x in range(lx+1,rx):p.put((x,f+3,nz+3),'dawnoftimebuilder:spruce_beam',priority=76,axis_x=True,axis_y=False,axis_z=False,bottom=True,waterlogged=False)
        for z in range(nz+1,min(sz,nz+7)):p.put((axis-1,f+3,z),'dawnoftimebuilder:spruce_support_slab',priority=77,pillar_connection='nothing',waterlogged=False)
        # A different pair of actual wall models serves every interior. These
        # are supported and warm at human scale, with no central fixture bulk.
        for xx,zz,face in ((lx+1,nz+2,'east'),(rx-1,sz-2,'west')):
            back=xx+(-1 if face=='east' else 1),f+3,zz
            if base(p.blocks.get(back,'minecraft:air')) not in AIR:
                furniture(p,(xx,f+3,zz),'mcwlights:bell_wall_lantern',support=back,facing=face)
        # Family table, cup, breakfast and a pair of chairs. Shifted between
        # storeys so the furniture isn't a stacked repeated room.
        tx,tz=(lx+2,nz+3) if level%2==0 else (rx-2,sz-3)
        for q,key,props in (
            ((tx,f+1,tz),'handcrafted:spruce_table',dict(color='none',shape='single',waterlogged=False)),
            ((tx,f+2,tz),'handcrafted:wood_cup',dict(facing='east',pieces=2,waterlogged=False)),
            ((tx-1,f+1,tz),'handcrafted:spruce_chair',dict(facing='east',color='none',waterlogged=False)),
            ((tx,f+1,tz+1),'handcrafted:spruce_chair',dict(facing='north',color='none',waterlogged=False))):
            furniture(p,q,key,support=(q[0],q[1]-1,q[2]),**props)
        # Pantry, ceramic jar, contained flowers and a true wall shelf with
        # objects on it are a substantial ensemble, not one lonely barrel.
        for zz in (nz+4,nz+5):
            q=lx+1,f+1,zz
            furniture(p,q,'handcrafted:spruce_counter',support=(q[0],f,q[2]),facing='east',counter='dark_oak_planks',type='1')
        furniture(p,(lx+1,f+2,nz+4),'handcrafted:berry_jam_jar',support=(lx+1,f+1,nz+4),facing='east',jars=3,waterlogged=False)
        furniture(p,(lx+1,f+2,nz+5),'minecraft:potted_cornflower',support=(lx+1,f+1,nz+5))
        sx,ss=rx-2,nz+2
        work={'seabird-ledger':'minecraft:cartography_table','three-kestrels':'minecraft:smoker','brass-finch':'minecraft:smithing_table','anchor-apple':'minecraft:crafting_table','ink-tern':'minecraft:lectern','reed-resonance':'minecraft:note_block','rosemary-court':'minecraft:composter','salt-wind':'minecraft:loom'}[lot.ident]
        if level:
            work='handcrafted:oak_desk';props=dict(facing='west',color='none',waterlogged=False)
        elif work=='minecraft:smoker':props=dict(facing='south',lit=False)
        elif work=='minecraft:lectern':props=dict(facing='west',has_book=False,powered=False)
        elif work=='minecraft:note_block':props=dict(instrument='harp',note=12,powered=False)
        elif work=='minecraft:composter':props=dict(level=0)
        elif work=='minecraft:loom':props=dict(facing='west')
        else:props={}
        furniture(p,(sx,f+1,ss),work,support=(sx,f,ss),**props)
        if level:furniture(p,(sx,f+2,ss),'handcrafted:stackable_book',support=(sx,f+1,ss),books=3,facing='west',seed=level+3)
        # A cupboard on the opposite side of the aisle has an actual decorated
        # top, while the customer/household seat sits beside the window.
        cx,cz=rx-2,nz+4
        furniture(p,(cx,f+1,cz),'handcrafted:spruce_cupboard',support=(cx,f,cz),facing='west',type='1')
        topkey='supplementaries:globe' if lot.ident in ('seabird-ledger','salt-wind') and not level else 'handcrafted:stackable_book'
        topfields=dict(facing='west',powered=False,rotation=0,waterlogged=False) if topkey=='supplementaries:globe' else dict(books=3,facing='west',seed=level+7)
        furniture(p,(cx,f+2,cz),topkey,support=(cx,f+1,cz),**topfields)
        furniture(p,(rx-2,f+1,nz+6),'handcrafted:spruce_couch',support=(rx-2,f,nz+6),facing='west',color='red' if lot.ident in ('anchor-apple','ink-tern') else 'blue',shape='single',waterlogged=False)
        # Books and real trade stock on separate backed native display models.
        for n,(xx,zz,face) in enumerate(((lx+1,nz+6,'east'),(axis,nz+1,'south'),(rx-1,sz-2,'west'))):
            q=xx,f+2,zz;dx,dz=FACES[face];back=xx-dx,f+2,zz-dz
            if clear_fixture(p,q) and base(p.blocks.get(back,'minecraft:air')) not in AIR:
                p.display(q,ITEMS[lot.ident][(n+level)%4],lot.name+' — '+lot.rooms[level],face)
        # Every household has an actual bed, nightstand, reading candle and
        # luggage. These fit to each real set-back room, not the former mask.
        if level:
            bx,bz=lx+2,sz-3
            for dz,part in ((0,'head'),(1,'foot')):
                furniture(p,(bx,f+1,bz+dz),'handcrafted:spruce_fancy_bed',support=(bx,f,bz+dz),facing='north',part=part,occupied=False,shape='single',color='green' if lot.ident in ('rosemary-court','three-kestrels') else 'blue')
            furniture(p,(bx+1,f+1,bz),'handcrafted:spruce_nightstand',support=(bx+1,f,bz),facing='south')
            furniture(p,(bx+1,f+2,bz),'supplementaries:candle_holder',support=(bx+1,f+1,bz),candles=2,face='floor',facing='north',lit=True,waterlogged=False)
            if lot.ident=='salt-wind' and level==1:
                furniture(p,(lx+2,f+1,nz+1),'dawnoftimebuilder:birch_footstool',support=(lx+2,f,nz+1),facing='east',waterlogged=False)
                furniture(p,(lx+1,f+1,nz+2),'supplementaries:book_pile',support=(lx+1,f,nz+2),books=3,waterlogged=False)
        else:
            # A coherent masonry hearth hood is visibly three-dimensional.
            # Its native smoker is unlit until real players supply fuel/food.
            hx,hz=lx+1,sz-2
            if clear_fixture(p,(hx,f+1,hz)):
                furniture(p,(hx,f+1,hz),'minecraft:smoker',support=(hx,f,hz),facing='east',lit=False)
                p.put((hx,f+2,hz),'minecraft:stone_brick_stairs',priority=82,facing='west',half='top',shape='straight',waterlogged=False)
                furniture(p,(hx+1,f+1,hz),'handcrafted:dark_oak_bench',support=(hx+1,f,hz),facing='north',color='none',shape='single',waterlogged=False)
        record.update(furnishing_objects=len(p.fixtures)-start,circulation_reserved=True,ceiling='Actual half-height coffer ribs and supported wall lamps',
            scene=lot.rooms[level],actual_floor_outline=[list(q) for q in sorted(room)])


def frontage(p,lot,cells,floor):
    """Individual supported small-scale shop windows and domestic edges."""
    p.group=lot.name;face=lot.face;dx,dz=FACES[face];t=(1,0) if dz else (0,1)
    edge=max(z for x,z in cells) if face=='south' else min(x for x,z in cells)
    xx,zz=(lot.center[0]-3,edge) if face=='south' else (edge,lot.center[1]+3)
    # One window box and carved pair of jambs, a real projecting surface at
    # hand level. The door, center lane and upstairs oriel remain unobstructed.
    for u in (0,1):
        x,z=xx+t[0]*u+dx,zz+t[1]*u+dz
        p.put((x,floor+1,z),'minecraft:dark_oak_slab',priority=83,type='top',waterlogged=False)
        p.put((x,floor,z),'mythrais:small_curved_corbel_dark_oak',priority=83,facing=face,shape=0)
        plant=('minecraft:potted_allium' if lot.ident=='rosemary-court' else 'minecraft:potted_blue_orchid' if lot.ident in ('salt-wind','seabird-ledger') else 'minecraft:potted_poppy')
        furniture(p,(x,floor+2,z),plant,support=(x,floor+1,z))
    if lot.ident in ('brass-finch','reed-resonance','anchor-apple','ink-tern'):
        for u in (-1,0,1):
            x,z=lot.center[0]+u,edge+1
            p.put((x,floor+3,z),'minecraft:dark_oak_slab',priority=84,type='top',waterlogged=False)
            if u:
                p.put((x,floor+3,z-1),'mythrais:small_curved_corbel_dark_oak',priority=84,facing='south',shape=0)
    # Narrow roof cornices have distinct cut-outs, brackets and sloped returns;
    # no whole street is roofed over by a massive solid upper jetty.
    roof=floor+lot.levels*4
    for x,z in ((min(a for a,b in cells),min(b for a,b in cells)+2),(max(a for a,b in cells),max(b for a,b in cells)-2)):
        if (x,z) in boundary(cells):p.put((x,roof-1,z),'dawnoftimebuilder:spruce_support_slab',priority=81,pillar_connection='nothing',waterlogged=False)


LANE=((1230,-1199),(1237,-1198),(1245,-1197),(1253,-1196),(1262,-1198),(1271,-1197),(1281,-1197),
      (1290,-1198),(1299,-1197),(1307,-1196),(1315,-1196),(1324,-1197),(1333,-1196),(1340,-1196),(1343,-1201),(1343,-1207))
ROSE_JOIN=((1334,-1225),(1334,-1219),(1338,-1216),(1338,-1208),(1337,-1203),(1338,-1197))


def line(nodes):
    out=[]
    for a,b in zip(nodes,nodes[1:]):
        n=max(abs(a[0]-b[0]),abs(a[1]-b[1]))
        out.extend((round(a[0]+(b[0]-a[0])*i/max(1,n)),round(a[1]+(b[1]-a[1])*i/max(1,n))) for i in range(n+1))
    return list(dict.fromkeys(out))


def lane_paver(p,x,z):
    row=p.land.get((x,z),{})
    if row.get('kind')=='dry':return pave(p,x,z)
    # Adopt only an exact existing Rose Reach paver and its already-authored
    # headroom. It is separately verified, never placed or cleared again.
    y=row.get('surface_y');q=x,y,z
    allowed={'minecraft:cobblestone','minecraft:chiseled_stone_bricks','minecraft:polished_andesite','minecraft:mossy_cobblestone'}
    if type(y) is not int or base(p.prior.get(q,'minecraft:air')) not in allowed:
        raise UserError('Preserve retained object or water in the proposed lane: '+str((x,z)))
    for dy in (0,1,2):
        position=x,y+dy,z;value=p.prior.get(position)
        if value is None or dy and base(value) not in AIR:raise UserError('Existing junction lacks exact authored clear headroom')
        p.retained[position]=value
    return q


def town_lane(p):
    p.group='Compass Bend connected public lanes';centres=line(LANE)+line(ROSE_JOIN)
    for x,z in sorted({(x+dx,z+dz) for x,z in centres for dx in (-1,0,1) for dz in (-1,0,1)}):
        if p.priority.get((x,p.land[x,z]['surface_y']+1,z),0)>=50:raise UserError('An actual public lane would enter a building: '+str((x,z)))
        q=lane_paver(p,x,z)
        for dy in (1,2):p.walk.append((x,q[1]+dy,z))
    # Threshold stairs follow actual retained grades. Branches terminate on
    # the three-wide bend; no isolated house surrounded by a lawn strip.
    for lot,row in zip(HOUSES,p.lots):
        p.group=lot.name;dx,dz=FACES[lot.face];x,feet,z=row['door'];f=feet-1
        rise=f-p.land[x+dx,z+dz]['surface_y']
        if not 1<=rise<=3:raise UserError('A new threshold requires another deliberate grade design')
        for n in range(1,rise+1):
            xx,zz=x+n*dx,z+n*dz;y=f-n+1
            for support in range(p.land[xx,zz]['surface_y']+1,y):p.put((xx,support,zz),'minecraft:stone_bricks',priority=97)
            p.put((xx,y,zz),'minecraft:stone_brick_stairs',priority=98,facing={'south':'north','west':'east'}[lot.face],half='bottom',shape='straight',waterlogged=False)
        p.group='Compass Bend connected public lanes';start=x+(rise+1)*dx,z+(rise+1)*dz
        end=min(centres,key=lambda q:abs(q[0]-start[0])+abs(q[1]-start[1]))
        # The saved dark-cherry tree is retained in its own tiny music court,
        # with an actual eastward dog-leg around its native trunk.
        route=line((start,(1314,start[1]),(1314,end[1]),end)) if lot.ident=='reed-resonance' else line((start,end))
        side=(1,0) if dz else (0,1)
        for a,b in route:
            for u in (-1,0,1):
                xx,zz=a+side[0]*u,b+side[1]*u;q=lane_paver(p,xx,zz)
                for dy in (1,2):p.walk.append((xx,q[1]+dy,zz))
    # The backs of this row are not a dead blank field. Three small work yards
    # and a dog-legged passage knit the row to the existing accepted quarter.
    back=line(((1235,-1215),(1245,-1215),(1261,-1215),(1276,-1215),(1291,-1216),(1308,-1216),(1324,-1216),(1338,-1216)))
    for x,z in back:
        if (x,z) in p.protected:continue
        for dx in (0,1):
            if p.priority.get((x+dx,p.land[x+dx,z]['surface_y']+1,z),0)>=50:continue
            q=lane_paver(p,x+dx,z)
            for dy in (1,2):p.walk.append((q[0],q[1]+dy,q[2]))
    # Street groups occupy verified side pockets, never the two-wide passage.
    for x,z,face in ((1244,-1205,'east'),(1273,-1205,'west'),(1305,-1206,'east'),(1338,-1210,'west')):
        y=p.land[x,z]['surface_y'];p.group='Compass Bend connected public lanes'
        furniture(p,(x,y+1,z),'handcrafted:dark_oak_bench',support=(x,y,z),facing=face,color='none',shape='single',waterlogged=False)
        if clear_fixture(p,(x,y+1,z-1)):
            p.put((x,y+1,z-1),'minecraft:chiseled_stone_bricks',priority=85)
            furniture(p,(x,y+2,z-1),'minecraft:potted_allium',support=(x,y+1,z-1))
    p.cameras.extend([{'name':'compass-bend-west-street','feet':[1234.5,64,-1197.5],'look_at':[1267,72,-1205]},
        {'name':'three-kestrels-gallery','feet':[1248.5,65,-1196.5],'look_at':[1248,74,-1205]},
        {'name':'ink-tern-entry','feet':[1296.5,64,-1196.5],'look_at':[1295,72,-1207]},
        {'name':'instrument-room','feet':[1312.5,65,-1206.5],'look_at':[1309,66,-1210]},
        {'name':'rosemary-kitchen','feet':[1328.5,65,-1202.5],'look_at':[1325,66,-1207]},
        {'name':'rose-to-compass-join','feet':[1338.5,64,-1216.5],'look_at':[1337,73,-1207]}])


def construct(registry,fine,rose_cells=None):
    p=EastPlan(registry,fine)
    # Plot footprints protect the whole prior quarter. At the actual existing
    # lane junction only old source AIR can be shared with new source AIR; the
    # current physical preimage below still refuses every old solid/BE write.
    p.prior=dict(rose_cells or {});p.retained={};p.rooms=[]
    for lot in HOUSES:
        cells,floor,door=articulated_shell(p,lot);furniture_story(p,lot,cells,floor,door);frontage(p,lot,cells,floor)
    town_lane(p);canonical_parts(p)
    return p


def check(p):
    materials=[require_material_rule({q:s for q,s in p.blocks.items() if p.owners[q]==lot.name},lot.name+' — complete furnished Compass Bend house') for lot in HOUSES]
    require_outdoor_rule(p.blocks,'Complete Compass Bend buildings, stepped footings, lanes and courtyards')
    bad=[(q,p.blocks.get(q)) for q in set(p.walk) if base(p.blocks.get(q,'minecraft:air')) not in AIR and not any(s in base(p.blocks[q]) for s in ('door','stairs'))]
    if bad:raise UserError('A real two-high circulation cell is blocked: '+str(bad[:8]))
    for fixture in p.fixtures:
        if base(p.blocks.get(tuple(fixture['position']),'minecraft:air'))!=fixture['block']:raise UserError('A furnished model was overwritten: '+str(fixture))
    if min(r['furnishing_objects'] for r in p.rooms)<15:raise UserError('Finish every inhabited room before source handoff')
    return {'complete_buildings_3_9':materials,'outdoor_max9':True,'buildings':len(p.lots),'rooms':len(p.rooms),
        'furnishing_models':len(p.fixtures),'two_high_route_cells':len(set(p.walk)),
        'set_back_upper_footprints':len(SETBACKS),'native_or_visual_acceptance':False}


def encode(value):return (json.dumps(value,separators=(',',':'),ensure_ascii=False)+'\n').encode()


def prepare(home,fine_path,checkpoint_id,checkpoint_sha):
    home=Path(home).resolve();fine_path=Path(fine_path).resolve()
    if home.parent!=Path('D:/A World for Two/staging/world-tests').resolve() or not fine_path.is_relative_to(home/'staging'):raise UserError('Exact authorized private artistic stage required')
    reserve=guard(4*MIB,64*MIB);current=read_json(home/'dashboard/settlement/backup-receipt.json')
    if current.get('verified') is not True or current.get('id')!=checkpoint_id or current.get('sha256')!=checkpoint_sha:raise UserError('Current actual stopped checkpoint required')
    if fine_path.stat().st_size>16*MIB:raise UserError('Bounded complete eastern field required')
    fine=read_json(fine_path)
    if fine.get('checkpoint_sha256')!=checkpoint_sha:raise UserError('Saved fine field belongs to another checkpoint')
    rose=home/ROSE_REL
    if digest(rose)!=ROSE_SHA:raise UserError('Frozen accepted Rose Reach source changed')
    prior=flatten(read_json(rose));registry=read_json(home/'dashboard/settlement/registry.json')
    p=construct(registry,fine,prior);proof=check(p);terrain=NorthTerrain(home,current,registry);before={};support={};shared_air={}
    try:
        for q,expected in sorted(p.blocks.items(),key=lambda r:(r[0][0]//16,r[0][2]//16,r[0][1],r[0][0],r[0][2])):
            old=terrain.state(*q)
            if old is None or q in terrain.entities:raise UserError('Preserve saved BE or non-FULL target '+str(q))
            if q in prior:
                if base(prior[q]) not in AIR or expected!='minecraft:air' or base(old) not in AIR:raise UserError('Preserve every previous Rose Reach solid/BE: '+str((q,prior[q],expected)))
                shared_air[q]=old
            elif base(old) not in AIR|GROUND|SOFT|NORTH_SOFT or 'waterlogged=true' in old:raise UserError('Preserve water, natural tree, foreign solid or cover: '+str((q,old)))
            before[q]=old;terrain.check()
        # Foundation support is current actual saved geology, not a claimed
        # empty before plan. Preserve at least one unchanged full course below.
        for lot in p.lots:
            for x,z in map(tuple,lot['main_footprint']):
                y=min(q[1] for q in p.blocks if q[0]==x and q[2]==z and p.owners[q]==lot['name'])-1
                q=x,y,z;old=terrain.state(*q)
                if old is None or q in terrain.entities or base(old) not in GROUND:raise UserError('Exact retained dry foundation support required: '+str((q,old)))
                support[q]=old
        for item in p.supports:
            q=tuple(item['support'])
            if q not in p.blocks:
                old=terrain.state(*q)
                if old is None or base(old) not in GROUND:raise UserError('Furniture has no current native ground support')
                support[q]=old
        for q,expected in p.retained.items():
            if terrain.state(*q)!=expected or q in terrain.entities:raise UserError('Existing retained Rose Reach paver/headroom changed')
        sources=terrain.snapshot.sources
    finally:terrain.close()
    # Shared unchanged AIR isn't replayed; it is a separate verification proof.
    states={q:s for q,s in p.blocks.items() if q not in shared_air};tags={q:s for q,s in p.tags.items() if q in states};solids={q:s for q,s in states.items() if base(s) not in AIR}
    if len(solids)>20000:raise UserError('Split solid-only normal shape targets at20k')
    docs={'prototype.json':native_payload(registry,states,checkpoint_sha,'Compass Bend — eight original inhabited 3D houses, courts and connected lanes',tags=tags),
        'before-VERIFY-ONLY.json':native_payload(registry,{q:before[q] for q in states},checkpoint_sha,'VERIFY ONLY — complete actual Compass Bend before state'),
        'supports-VERIFY-ONLY.json':native_payload(registry,support,checkpoint_sha,'VERIFY ONLY — retained actual foundation/fixture supports'),
        'normal-joins-SETTLE-ONLY.json':native_payload(registry,solids,checkpoint_sha,'NORMAL SHAPES ONLY — actual new solid join targets; no NBT replay')}
    docs['normal-joins-SETTLE-ONLY.json'].update(construction_forbidden=True,verification_only=True)
    if p.retained:docs['retained-Rose-Reach-junction-VERIFY-ONLY.json']=native_payload(registry,p.retained,checkpoint_sha,'VERIFY ONLY — existing exact pavers/headroom, never place')
    if shared_air:docs['retained-Rose-Reach-AIR-VERIFY-ONLY.json']=native_payload(registry,shared_air,checkpoint_sha,'VERIFY ONLY — unchanged exact prior authored AIR')
    raw={n:encode(d) for n,d in docs.items()}
    manifest={'format':'awft-north-bank-compass-bend:1','checkpoint_id':checkpoint_id,'checkpoint_sha256':checkpoint_sha,
        'source_sha256':digest(Path(__file__)),'fine_land_sha256':digest(fine_path),'prior_rose_source_sha256':ROSE_SHA,
        'blocks':len(states),'normal_join_targets':len(solids),'buildings':p.lots,'rooms':p.rooms,'fixtures':p.fixtures,'supports':p.supports,
        'walk_body_cells':[list(q) for q in sorted(set(p.walk))],'cameras':p.cameras,'checks':proof,'shared_prior_AIR_unwritten':len(shared_air),
        'saved_sources':sources,'reserve_guard':reserve,'native_actions':0,'source_entities':0,'old_BEs_replayed':0,
        'source_status':'Complete executable original quarter source; native before/place/normal joins/full strict verification and actual art/walk review PENDING',
        'town_continuity':'Three-wide crooked public lane, eight graded thresholds, two-wide back lane and an exact narrow natural-ground connection to placed Rose Reach; no isolated lawn plots',
        'botanical_life':'Contained native potted flowers, window boxes and courtyards included; wider botanical pass remains separate from native resident LIFE',
        'files':{n:{'bytes':len(v),'sha256':hashlib.sha256(v).hexdigest()} for n,v in raw.items()}}
    raw['manifest.json']=encode(manifest)
    if sum(map(len,raw.values()))>64*MIB:raise UserError('Bounded original quarter output exceeded')
    out=home/'staging'/('north-bank-compass-bend-'+str(time.time_ns()));out.mkdir()
    for name,data in raw.items():
        with (out/name).open('xb') as stream:stream.write(data)
    return {'folder':str(out),'manifest_sha256':digest(out/'manifest.json'),'targets':len(states),'buildings':len(p.lots),
        'rooms':len(p.rooms),'furnishings':len(p.fixtures),'checks':proof,'files':manifest['files'],'native_actions':0}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--home',type=Path,required=True);parser.add_argument('--fine',type=Path,required=True)
    parser.add_argument('--checkpoint-id',required=True);parser.add_argument('--checkpoint-sha',required=True);args=parser.parse_args()
    print(json.dumps(prepare(args.home,args.fine,args.checkpoint_id,args.checkpoint_sha),indent=2))
