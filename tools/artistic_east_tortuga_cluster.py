"""Furnished eastern Tortuga cluster with real infill and inventory-safe shells.

Three existing houses retain their full current BE contents and room programs.
A new two-level mender, open repair court and produce arcade close the gaps.
Everything is source-only and requires parent-owned native/art review.
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
from tools.artistic_bridge_refinement import flatten
from tools.artistic_captains_hall import native_payload
from tools.artistic_east_tortuga_retrofit import (
    LEDGER, LEDGER_SHA, CELL_SHA, BE_SHA, SOURCE, SOURCE_SHA,
    SOURCE_MANIFEST_SHA, SOURCE_BEFORE_SHA, checked, with_exact_be_tags,
)
from tools.artistic_fisherman_interior import Byte, snbt
from tools.artistic_maritime_depth import admit_owner, key
from tools.artistic_materials import require_material_rule, require_outdoor_rule
from tools.artistic_north_bank_east import preservation
from tools.artistic_north_rebuild_custody import decoded_chunk, typed
from tools.artistic_neighborhood_roofs import ridge_part
from tools.artistic_spawn_plaza import state
from tools.artistic_tortuga_pair import TradeHouse, hip, world_blocks, validate as validate_new_house
from tools.playtest import guard
from tools.settlement_attractions import BackupWorld, properties


MIB=1024**2
AIR='minecraft:air';VOID={AIR,'minecraft:cave_air','minecraft:void_air'}
SOFT={'minecraft:short_grass','minecraft:tall_grass','regions_unexplored:grass_sprouts'}
NATURAL_GROUND={'minecraft:grass_block','minecraft:gravel','minecraft:coarse_dirt','minecraft:dirt','minecraft:rooted_dirt'}
GROUND=NATURAL_GROUND|{'minecraft:stone','minecraft:andesite','minecraft:cobblestone','minecraft:stone_bricks','minecraft:mossy_cobblestone'}
HOUSE_IDS=('three-kestrels','brass-finch','anchor-apple')
BOUNDS=(1243,-1216,1290,-1197)
MAX_OUTPUT=24*MIB
ARCH={'minecraft:bricks','minecraft:stone_brick_slab','minecraft:dark_oak_planks','minecraft:spruce_planks',
      'minecraft:stripped_spruce_log','minecraft:stripped_dark_oak_log','minecraft:dark_oak_wood','minecraft:oak_wood',
      'minecraft:stripped_oak_wood','minecraft:white_terracotta','minecraft:green_terracotta','minecraft:waxed_cut_copper_slab',
      'minecraft:light_gray_terracotta','minecraft:polished_andesite','dawnoftimebuilder:plastered_stone','dawnoftimebuilder:yellow_plastered_stone',
      'dawnoftimebuilder:red_plastered_stone','dawnoftimebuilder:dark_oak_beam'}
JOIN='SAME_ID_STATE_DELTA_NATIVE_SHAPE_OR_HUMAN_ORIGIN_UNPROVEN_PRESERVE'
EXACT='SOURCE_EXACT_UNCHANGED_GEOMETRY'


def in_domain(q):return BOUNDS[0]<=q[0]<=BOUNDS[2] and BOUNDS[1]<=q[2]<=BOUNDS[3]
def box_cells(box):
    return {(x,z) for x in range(box[0],box[2]+1) for z in range(box[1],box[3]+1)}


def custody(home):
    root=home/LEDGER;m=checked(root/'manifest.json',LEDGER_SHA,2*MIB)
    if m['current_BE_count']!=727 or m['rejected_house_count']!=52:raise UserError('Complete unchanged52/727 baseline required')
    rows={};bes={};counts=[]
    for filename,sha,maximum in (('cells-READONLY.jsonl',CELL_SHA,48*MIB),('block-entities-FULL-TYPED-PRIVATE.jsonl',BE_SHA,2*MIB)):
        p=root/filename
        if p.is_symlink() or not 0<p.stat().st_size<=maximum or digest(p)!=sha or m['files'][filename]!={'bytes':p.stat().st_size,'sha256':sha}:
            raise UserError('Exact full private custody member required')
        count=0
        with p.open(encoding='utf-8') as stream:
            for line in stream:
                count+=1
                if len(line)>2*MIB or count>128000:raise UserError('Finite custody stream exceeded')
                row=json.loads(line);q=tuple(row['position'])
                if in_domain(q):(rows if filename.startswith('cells') else bes)[q]=row
        counts.append(count)
    if counts!=[127950,727]:raise UserError('The full custody stream is incomplete')
    return m,rows,bes


class Cluster:
    def __init__(self,registry,before,source,ledger,protected,walk,bed_cells):
        self.registry=registry;self.before=before;self.blocks=dict(before);self.source=source;self.ledger=ledger
        self.protected=protected|bed_cells;self.walk=walk;self.delta={};self.origins={};self.tags={};self.group='shared court'
        self.roles={};self.supports=[];self.retained=[];self.new_roots=set();self.route_cells=set();self.soft_cleared={}

    def put(self,q,material,*,role='original cluster architecture',new=False,ground=False,**props):
        q=tuple(q)
        if q not in self.before:raise UserError('Every construction/context target must have an exact current FULL preimage: '+str(q))
        value=state(self.registry,material,**props);old=self.before[q]
        if self.blocks[q]==value:return
        if q in self.protected:raise UserError('Preserve actual BEs, full supports, fixtures and human beds: '+str(q))
        if q in self.walk and material not in VOID:raise UserError('Preserve the accepted existing circulation: '+str(q))
        row=self.ledger.get(q);expected=self.source.get(q)
        if key(old) in VOID:
            if expected is not None and old!=expected:raise UserError('Current source AIR contains a later change')
            reason='EXACT_CURRENT_FULL_AIR_ADDITION'
        elif new and key(old) in SOFT and q not in self.source:
            reason='BOUNDED_MEASURED_ORDINARY_UNUSED_PLOT_GRASS';self.soft_cleared[q]=old
        elif ground and key(old) in NATURAL_GROUND and (q not in self.source or row and row['classification']==EXACT and old==expected):
            reason='BOUNDED_DRY_NATURAL_NEW_LANE_SURFACE'
        else:
            if not row or row['classification']!=EXACT or old!=row['actual_saved'] or old!=expected:
                raise UserError('Unknown/human/native state change is retained, not treated as removable shell: '+str((q,old)))
            name=key(old)
            if not (name in ARCH or name.startswith(('mcwroofs:','mythrais:roof_','mcwwindows:'))):
                raise UserError('A source match never authorizes furniture/plant/bed removal: '+str((q,name)))
            reason='EXACT_UNCHANGED_OWNED_NON_BE_SHELL'
        self.blocks[q]=value;self.delta[q]=value;self.roles[q]=role
        self.origins[q]={'owner':self.group,'role':role,'reason':reason,'old':old,'new':value}

    def beam(self,q,axis,role='dark actual structural timber'):
        material={'x':'chipped:reinforced_dark_oak_log','y':'minecraft:stripped_dark_oak_log','z':'chipped:edged_stripped_dark_oak_log'}[axis]
        self.put(q,material,axis=axis,role=role)

    def slab(self,q,wood='dark_oak',role='rooted shallow eave/ceiling relief'):
        self.put(q,'minecraft:'+wood+'_slab',type='top',waterlogged=False,role=role)

    def lamp(self,q,face):
        self.put(q,'mcwlights:tavern_wall_lantern',facing=face,role='small supported warm task lantern')
        dx,dz={'north':(0,-1),'south':(0,1),'west':(-1,0),'east':(1,0)}[face]
        self.supports.append((tuple(q),(q[0]-dx,q[1],q[2]-dz)))


def roof_adapter(p):
    class Adapter:
        blocks=p.blocks;details=[]
        def put(self,x,y,z,name,**props):
            q=x,y,z
            if q in p.protected or p.ledger.get(q,{}).get('classification')==JOIN or key(p.before[q])=='dawnoftimebuilder:spruce_support_slab':
                p.retained.append({'position':list(q),'reason':'Keep actual fixture backing/native joint; no inferred ownership of state delta'})
                return
            p.put(q,name,**props)
        def slab(self,x,y,z,wood='dark_oak',role='real roof purlin'):
            self.put(x,y,z,'minecraft:'+wood+'_slab',type='top',waterlogged=False,role=role)
    return Adapter()


def clear_roof(p,lot,base):
    cells=set(map(tuple,lot['main_footprint']));box=(min(x for x,z in cells)-1,min(z for x,z in cells)-1,max(x for x,z in cells)+1,max(z for x,z in cells)+1)
    for q,old in sorted(p.before.items()):
        x,y,z=q
        if not box[0]<=x<=box[2] or not box[1]<=z<=box[3] or y<base or q in p.protected:continue
        name=key(old)
        isroof=name.startswith(('mcwroofs:','mythrais:roof_')) or name=='minecraft:waxed_cut_copper_slab'
        gable=y>base and name in ARCH
        if isroof or gable:
            row=p.ledger.get(q)
            if row and row['classification']==EXACT and old==p.source.get(q):p.put(q,AIR,role='remove only positively unchanged old striped roof/gable')
    return box


def saltbox_halfhip(p,box,base):
    x0,z0,x1,z1=box;middle=(x0+x1)//2
    for x in range(x0,x1+1):
        rise=min(x-x0,x1-x)
        if x>middle:rise=max(0,rise-1)
        for z in range(z0,z1+1):
            h=min(rise,z1-z+1);y=base+h
            if (x,y,z) in p.protected or key(p.before[x,y,z])=='dawnoftimebuilder:spruce_support_slab':continue
            if h<rise:
                p.put((x,y,z),'dawnoftimebuilder:roofing_slates_stairs',facing='north',half='bottom',shape='straight',waterlogged=False,role='real clipped southern hip facet')
            elif x==middle:
                p.put((x,y,z),'mcwroofs:gray_terracotta_top_roof',part='switched_0',role='continuous quiet offset roof ridge')
            else:
                p.put((x,y,z),'mcwroofs:gray_terracotta_roof',facing='east' if x<middle else 'west',half='bottom',shape='straight',role='continuous weathered asymmetric roof slope')
            if h and key(p.blocks[x,y-1,z]) in VOID:p.slab((x,y-1,z),'spruce' if h<rise else 'dark_oak',role='genuine transverse hip-end or longitudinal side purlin')
    for x in range(x0+1,x1):
        rise=min(x-x0,x1-x)-(1 if x>middle else 0)
        for dy in range(1,max(1,rise)):
            q=x,base+dy,z0+1
            if q in p.protected:continue
            if (x-x0)%4==0:p.beam(q,'y',role='real northern attic gable frame')
            else:p.put(q,'minecraft:gray_terracotta',role='recessed soot-grey attic gable')


def refit_existing(p,lots):
    notes=[]
    for lot in lots:
        p.group=lot['name'];base=lot['floor_y']+lot['storeys']*4;box=clear_roof(p,lot,base)
        if lot['id']=='three-kestrels':
            # Retained setback terrace stays open. The new low asymmetric roof
            # follows its real upper room rather than the old box below.
            box=(box[0],box[1],box[2],box[3]-2);saltbox_halfhip(p,box,base)
            palette={'dawnoftimebuilder:yellow_plastered_stone':'minecraft:cyan_terracotta','minecraft:white_terracotta':'minecraft:gray_terracotta'}
            story='Setback family terrace retained; low asymmetrical half-hip, smoky plaster and dark strong eaves replace bright striped gambrel.'
        elif lot['id']=='brass-finch':
            hip(roof_adapter(p),box,base,'gray_terracotta','dawnoftimebuilder:roofing_slates_stairs')
            palette={'minecraft:green_terracotta':'minecraft:gray_terracotta','dawnoftimebuilder:plastered_stone':'minecraft:cyan_terracotta'}
            story='Tall copper-striped67degree canopy becomes a much lower four-sided slate/clay hip; every three-storey instrument/household room remains.'
        else:
            hip(roof_adapter(p),box,base,'brown_terracotta')
            palette={'dawnoftimebuilder:red_plastered_stone':'minecraft:gray_terracotta'}
            story='Four-sided quiet warm clay roof and deeply sheltered produce arcade replace the pale-banded half-hip/red flat frontage.'
        foot=set(map(tuple,lot['main_footprint']))
        for q,old in sorted(p.before.items()):
            if (q[0],q[2]) not in foot or q[1]>=base or q in p.protected:continue
            if key(old) in palette:p.put(q,palette[key(old)],role='muted deeply framed weathered plaster, keeping all furniture backing')
        notes.append({'house':lot['name'],'main_footprint':lot['main_footprint'],'storeys_retained':lot['storeys'],'design':story})
    return notes


def mender(registry):
    """One tiny, real two-level trade/home; deliberately not an old house copy."""
    # The measured retained oak occupiesZ−1203..−1199/Y64..72. The complete
    # new house, jetty and roof stop north of it, leaving a positive tree court.
    p=TradeHouse(registry,'The Bent Needle',(1255,64,-1212))
    main=box_cells((0,0,4,6))-{(0,6)};p.footprint=main
    for x,z in main|{(0,7),(1,7)}:
        for y in range(1,12):p.put(x,y,z,AIR,role='complete real tiny workroom/loft')
    p.floor(main,0);p.walls(main,1,3,'minecraft:gray_terracotta');p.ring(main,4)
    upper=(main|{(0,7),(1,7)})-{(3,z) for z in range(2,6)}
    p.floor(upper,4);p.walls(main,5,7,'minecraft:cyan_terracotta');p.ring(main,8)
    hip(p,(-1,-1,5,8),8,'brown_terracotta')
    for x in (0,1):
        p.put(x,3,7,'mythrais:curved_corbel_dark_oak',facing='south',shape=0,role='small actual loft jetty knee')
        for y in (5,6):p.put(x,y,7,'mcwwindows:dark_oak_four_window',facing='south',windowstate='locked',role='projecting tiny lived-in loft casement')
        p.beam(x,7,7,'x',role='rooted little loft window hood')
    for n in range(4):
        y,z=1+n,5-n
        for yy in (y+1,y+2,y+3):p.put(3,yy,z,AIR,role='real tiny stair headroom')
        for yy in range(1,y):p.put(3,yy,z,'minecraft:stone_bricks' if yy==1 else 'chipped:boxed_dark_oak_planks',role='stone-shod real narrow stair carriage')
        p.put(3,y,z,'minecraft:dark_oak_stairs',facing='north',half='bottom',shape='straight',waterlogged=False,role='genuine four-riser loft stair');p.stairs.append((3,y,z))
    p.reserve('mender customer/work aisle',[(2,1,z) for z in range(1,7)])
    p.reserve('mender real upper landing/home aisle',[(2,5,z) for z in range(1,6)]+[(3,5,1)])
    p.door(2,1,6,'south');p.put(2,0,7,'minecraft:stone_brick_stairs',facing='north',half='bottom',shape='straight',waterlogged=False,role='normal half-step from the two-wide public lane')
    for z in (2,3):p.counter(1,1,z,'east','andesite',role='deep boot/canvas consultation and repair counter')
    p.put(1,1,4,'minecraft:loom',facing='east',role='genuine canvas/banner repair loom')
    p.put(3,1,1,'minecraft:crafting_table',role='genuine needle-and-fitting workbench')
    p.barrel(1,1,1,'The Bent Needle — ordinary trade stock',[('minecraft:string',8),('minecraft:leather',4),('minecraft:paper',4)])
    p.put(1,2,2,'handcrafted:stackable_book',facing='east',books=2,seed=23,role='real repair-order ledgers')
    p.cup(1,2,3,'east');p.put(1,1,5,'minecraft:potted_fern',role='rooted contained workroom green')
    p.bed(1,5,1);p.put(1,5,4,'handcrafted:dark_oak_desk',facing='north',color='none',waterlogged=False,role='real upper sail-pattern desk')
    p.put(1,5,3,'handcrafted:dark_oak_chair',facing='south',color='brown',waterlogged=False,role='usable loft desk chair off the central walk')
    p.put(3,5,6,'minecraft:smoker',facing='west',lit=False,role='genuine small household cooking hearth')
    p.barrel(1,5,5,'Mender’s quiet household pantry',[('minecraft:bread',4)])
    p.cup(1,6,5,'east')
    for x in range(0,5):p.beam(x,8,3,'x',role='real ceiling tie above the loft')
    p.hanging(2,3,3);p.hanging(2,7,3)
    p.lamp(2,3,7,'south');p.sign(3,3,7,'south',['THE BENT NEEDLE','Canvas • Boots','Repairs and patterns','Quiet home above'])
    p.rooms=[{'name':'canvas and boot repair shop','local_feet':[2,1,4],'contents':'Native loom/crafting, deep order counter, real small stock, cups and a contained fern'},
        {'name':'mender’s actual tiny loft home','local_feet':[2,5,3],'contents':'Normal stair, real bed, pattern desk/chair, pantry, cooker and warm lamp'}]
    return p


def new_building(p,house):
    p.group=house.name
    for q,value in world_blocks(house).items():
        name=key(value);props={}
        if '[' in value:props=dict(v.split('=',1) for v in value.split('[',1)[1][:-1].split(','))
        p.put(q,name,new=True,role=house.roles[tuple(q[i]-house.origin[i] for i in range(3))],**props)
    for q,tag in house.tags.items():p.tags[tuple(q[i]+house.origin[i] for i in range(3))]=snbt(tag)
    for q,back in house.supports:p.supports.append((tuple(q[i]+house.origin[i] for i in range(3)),tuple(back[i]+house.origin[i] for i in range(3))))


def projecting_windows(p):
    # Each actual room gains a deep new glazed bow at a specifically measured
    # clear wall segment. Existing lamps/backings and all containers stay.
    for owner,wall_x,outer_x,z0,feet in (
            ('Three Kestrels House',1244,1243,-1209,69),
            ('The Brass Finch',1270,1271,-1210,73)):
        p.group=owner;face='west' if outer_x<wall_x else 'east'
        for z in (z0,z0+1):
            for y in (feet,feet+1):
                p.put((wall_x,y,z),AIR,role='owned exact old wall/glazing opened into a real deep room oriel')
                p.put((outer_x,y,z),'mcwwindows:dark_oak_four_window',facing=face,windowstate='closed',role='real deep openable dark-timber casement')
            p.slab((outer_x,feet-1,z),'dark_oak',role='rooted projecting room-window sill')
        for z in (z0-1,z0+2):
            for y in (feet-1,feet,feet+1):p.beam((outer_x,y,z),'y',role='real carved deep-window cheek')
            p.put((outer_x,feet-2,z),'mythrais:curved_corbel_dark_oak',facing=face,shape=0,role='actual room-oriel lower knee')
        for z in range(z0-1,z0+3):p.beam((outer_x,feet+2,z),'z',role='supported deep casement lintel below the retained eaves')


def shared_workyards(p):
    p.group='Finch Yard — shared open repair court'
    # The actual old bench1273/−1205 and planted plinth1273/−1206 remain;
    # the two-wide entrance runs east of them rather than deleting either.
    for x,z in ((1272,-1208),(1276,-1208),(1272,-1204),(1276,-1204)):
        p.put((x,64,z),'minecraft:stone_bricks',new=True,role='dry grounded shared-yard post shoe');p.new_roots.add((x,64,z))
        for y in range(65,69):p.beam((x,y,z),'y',role='weathered narrow open workshop upright')
    for z in range(-1208,-1203):
        p.beam((1272,68,z),'z');p.beam((1276,68,z),'z')
        for x in range(1271,1277):p.put((x,69+(-1204-z)//3,z),'mcwroofs:gray_terracotta_lower_roof',facing='north',half='bottom',shape='straight',role='real low pitched repair-yard canopy')
    for x in range(1272,1277):p.beam((x,68,-1204),'x',role='full open-front workshop lintel')
    p.put((1272,64,-1207),'minecraft:crafting_table',new=True,role='genuine courtyard instrument/gear workbench')
    p.put((1275,64,-1207),'minecraft:grindstone',face='floor',facing='west',new=True,role='genuine stone-founded courtyard tool sharpening')
    p.put((1275,64,-1206),'create:brown_toolbox',facing='west',waterlogged=False,new=True,role='new real empty portable tool storage')
    p.put((1272,64,-1206),'handcrafted:dark_oak_counter',facing='east',counter='andesite',type=1,new=True,role='real shared repair/copper fitting counter')
    p.put((1272,65,-1206),'handcrafted:wood_cup',facing='east',pieces=2,waterlogged=False,new=True,role='small real workroom cups')
    p.lamp((1273,67,-1208),'east')
    # Apple’s eastern arcade is a distinct low market return, not another
    # closed rectangular house and not a low block in the primary approach.
    p.group='Anchor & Apple — sheltered produce return'
    for z in (-1207,-1203):
        p.put((1287,64,z),'minecraft:stone_bricks',new=True,role='real narrow arcade post shoe');p.new_roots.add((1287,64,z))
        for y in range(65,69):p.beam((1287,y,z),'y')
    for z in range(-1207,-1202):
        p.beam((1287,68,z),'z',role='continuous produce arcade fascia')
        for x in (1286,1287,1288):p.put((x,69+(1287-x)//2,z),'mcwroofs:brown_terracotta_lower_roof',facing='west',half='bottom',shape='straight',role='actual short weathered tiled side-arcade roof')
    for z in (-1206,-1205):p.put((1286,64,z),'handcrafted:dark_oak_counter',facing='east',counter='dark_oak_planks',type=1,new=True,role='real market-depth produce counter')
    p.put((1286,65,-1205),'minecraft:potted_blue_orchid',new=True,role='contained flower on real market sill')
    p.lamp((1288,67,-1203),'east')


def lanes(p):
    p.group='Two-wide crooked mender/repair-yard lanes'
    cells=set()
    # Two metres each side of the new occupied gap, joined by a short northern
    # hook, then open into the existing main street and shared repair court.
    cells|=box_cells((1253,-1213,1254,-1201))
    cells|=box_cells((1260,-1213,1261,-1201))
    cells|=box_cells((1254,-1214,1261,-1213))
    cells|=box_cells((1254,-1204,1261,-1203))
    cells|=box_cells((1274,-1205,1275,-1201))
    cells|=box_cells((1288,-1207,1289,-1203))
    # Preserve the actual mature red-grape bush1288/−1202 and curve the two
    # walking columns east around its planting rather than clearing it.
    cells|=box_cells((1289,-1203,1290,-1201))
    for x,z in sorted(cells):
        for y in (64,65):
            q=x,y,z;old=p.before[q]
            if key(old) not in VOID|SOFT:raise UserError('Retain old trees, pavers/fixtures or human objects rather than pave a route through them: '+str((q,old)))
            p.put(q,AIR,new=True,role='literal two-high new walking body');p.route_cells.add(q)
        q=x,63,z;old=p.before[q]
        if key(old) in NATURAL_GROUND:
            p.put(q,'minecraft:gravel',ground=True,role='measured narrow weathered new lane surface')
        elif key(old) not in GROUND:raise UserError('The whole two-wide new route needs real dry ground: '+str((q,old)))
    return cells


def ridge_expectations(p):
    """Pinned native same-ID cardinal rule, only for the newly authored ridges."""
    changes=[];group=p.group
    for q in list(p.delta):
        value=p.blocks[q];name=key(value)
        if not name.startswith('mcwroofs:') or not name.endswith('_top_roof'):continue
        x,y,z=q;neighbors=((x,y,z-1),(x+1,y,z),(x,y,z+1),(x-1,y,z))
        if any(n not in p.blocks for n in neighbors):raise UserError('A new ridge join lacks exact current/proposed neighboring cells')
        prop=properties(value);prop['part']=ridge_part(*(key(p.blocks[n])==name for n in neighbors))
        wanted=state(p.registry,name,**prop)
        if wanted!=value:
            p.group=p.origins[q]['owner'];p.put(q,name,role='exact native new-ridge end/straight expectation',**prop)
            changes.append({'position':list(q),'before':value,'after':wanted,'neighbors':[list(v) for v in neighbors]})
    p.group=group
    return changes


def prepare(home,checkpoint_id,checkpoint_sha):
    home=Path(home).resolve();reserve=guard(2*MIB,MAX_OUTPUT)
    if home.parent!=Path('D:/A World for Two/staging/world-tests').resolve():raise UserError('Owned private art stage only')
    receipt=read_json(home/'dashboard/settlement/backup-receipt.json');r=read_json(home/'dashboard/settlement/registry.json')
    admit_owner(home,read_json(home/'dashboard/artistic-owner.json'),receipt,checkpoint_id,checkpoint_sha)
    baseline,ledger,old_bes=custody(home);meta=checked(home/SOURCE/'manifest.json',SOURCE_MANIFEST_SHA,4*MIB)
    source_doc=checked(home/SOURCE/'prototype.json',SOURCE_SHA,MIB);checked(home/SOURCE/'before-VERIFY-ONLY.json',SOURCE_BEFORE_SHA,MIB)
    source=flatten(source_doc);lots=[row for row in meta['buildings'] if row['id'] in HOUSE_IDS]
    if len(lots)!=3:raise UserError('The exact three retained eastern houses must be present')
    new=mender(r);new_proof=validate_new_house(new)
    snapshot=BackupWorld(home,receipt,r);started=time.monotonic()
    try:
        wanted=set(ledger)|{(x,y,z) for x in range(BOUNDS[0],BOUNDS[2]+1) for z in range(BOUNDS[1],BOUNDS[3]+1) for y in range(63,96)}
        if len(wanted)>40000:raise UserError('Finite source cluster field exceeded')
        before={q:snapshot.state(q) for q in sorted(wanted)}
        if any(v is None for v in before.values()) or time.monotonic()-started>90:raise UserError('Complete bounded actual FULL cluster field required')
        actual={}
        for cx,cz in {(q[0]//16,q[2]//16) for q in wanted}:
            doc=decoded_chunk(snapshot.regions[cx//32,cz//32],cx,cz)
            for be in doc.get('block_entities',[]):
                q=int(be['x']),int(be['y']),int(be['z'])
                if q in before:actual[q]=be
        if set(actual)!=set(old_bes):raise UserError('New/removed BE in the cluster needs a new explicit custody review; never overwrite it')
        protected=set(actual);fixture={tuple(v['position']) for v in meta['fixtures'] if v.get('room') in {v['name'] for v in lots}}
        protected|=fixture|{tuple(v['support']) for v in meta['supports'] if tuple(v['fixture']) in fixture}
        for q in actual:protected|={(q[0]+dx,q[1]+dy,q[2]+dz) for dx in (-1,0,1) for dy in (-1,0,1) for dz in (-1,0,1)}
        beds={q for q,v in before.items() if key(v).endswith('_bed')};walk=set(map(tuple,meta['walk_body_cells']))
        p=Cluster(r,before,source,ledger,protected,walk,beds)
        notes=refit_existing(p,lots);projecting_windows(p);new_building(p,new);shared_workyards(p);lane_columns=lanes(p);joins=ridge_expectations(p)
        delta=p.delta;after=p.blocks
        if any(q in actual or q in beds for q in delta):raise UserError('Every old BE/bed remains physically untouched')
        if any(after[q]!=before[q] for q in walk&set(after)):raise UserError('No accepted existing walking body changes')
        heritage,heritage_refs=preservation(home,r)
        if {(x,z) for x,y,z in delta}&heritage:raise UserError('Keep accepted original architecture/navigation clear')
        from tools.artistic_west_r2_study import ZIP
        zipdoc=checked(home/ZIP[0],ZIP[1],2*MIB);zc={(v[0]+dx,v[2]+dz) for v in zipdoc['blocks'] for dx in range(-5,6) for dz in range(-5,6)}
        if {(x,z) for x,y,z in delta}&zc:raise UserError('Retain the actual v2 flight/station/frames and five metres')
        supports={}
        new_foot={(x+new.origin[0],z+new.origin[2]) for x,z in new.footprint}
        roots={(x,64,z) for x,z in new_foot}|p.new_roots
        for x,y,z in roots:
            q=x,y-1,z;v=snapshot.state(q)
            if key(v) not in GROUND or key(snapshot.state((x,y-2,z))) in VOID|{'minecraft:water','minecraft:lava'}:raise UserError('A new structure has a wet/void/unsupported dry footing: '+str(q))
            supports[q]=v
        for detail,back in p.supports:
            if key(after[back]) in VOID:raise UserError('A new actual fitting lacks real backing')
        # All retained old complete floors are independent roots. Every NEW
        # solid must connect through real proposed/current structure to them.
        for lot in lots:roots|={(x,lot['floor_y'],z) for x,z in lot['main_footprint'] if key(after[x,lot['floor_y'],z]) not in VOID}
        solid={q for q,v in after.items() if key(v) not in VOID};pending=deque(roots)
        while pending:
            q=pending.popleft()
            for d in ((1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1)):
                n=tuple(q[i]+d[i] for i in range(3))
                if n in solid and n not in roots:roots.add(n);pending.append(n)
        if any(q not in roots for q,v in delta.items() if key(v) not in VOID and q[1]>=64):raise UserError('A new cluster solid is disconnected from actual dry support/retained structure')
        materials=[]
        for lot in lots:
            foot=set(map(tuple,lot['main_footprint']));xx=[v[0] for v in foot];zz=[v[1] for v in foot]
            field={q:v for q,v in after.items() if (q[0],q[2]) in foot and q[1]>=lot['floor_y'] or min(xx)-1<=q[0]<=max(xx)+1 and min(zz)-1<=q[2]<=max(zz)+1 and q[1]>=lot['floor_y']+lot['storeys']*4}
            field.update({q:v for q,v in delta.items() if p.origins[q]['owner']==lot['name']})
            materials.append(require_material_rule(field,lot['name']+' complete retained furnishings plus corrected3D shell'))
        materials.append(new_proof['material'])
        court={q:v for q,v in delta.items() if p.origins[q]['owner'] in ('Finch Yard — shared open repair court','Anchor & Apple — sheltered produce return')}
        materials.append(require_material_rule(court,'Complete new sheltered working court and produce arcade'))
        require_outdoor_rule({q:v for q,v in delta.items() if p.origins[q]['owner']=='Two-wide crooked mender/repair-yard lanes'},'Actual new narrow hooked lanes')
        bdata=[]
        for q,be in sorted(actual.items()):
            value=typed(be);raw=json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
            bdata.append({'pos':list(q),'state':before[q],'full_typed_NBT':value,'sha256':hashlib.sha256(raw).hexdigest(),
                'same_as_historical575':hashlib.sha256(raw).hexdigest()==old_bes[q]['actual_full_typed_NBT_sha256'],'action':'PRESERVE IN PLACE; never in delta'})
        # Export complete actual legacy house/skirt fields and all new authored
        # body/routes/fixtures, not the large read-only qualification cube.
        # That cube is never new authorship or town LIFE placement authority.
        context=set(delta)|set(world_blocks(new))|p.route_cells|set(actual)|set(supports)|(protected&set(before))
        for lot in lots:
            foot=set(map(tuple,lot['main_footprint']));xs=[v[0] for v in foot];zs=[v[1] for v in foot]
            context|={q for q in ledger if min(xs)-1<=q[0]<=max(xs)+1 and min(zs)-1<=q[2]<=max(zs)+1}
        exported_before={q:before[q] for q in context};exported_after={q:after[q] for q in context}
        native_tags={q:be for q,be in actual.items()}
        full=json.loads(with_exact_be_tags(native_payload(r,exported_after,checkpoint_sha,'Complete proposed three-house/mender/court cluster — verification only'),native_tags))
        full['block_entities'].extend({'pos':list(q),'nbt':tag} for q,tag in sorted(p.tags.items()))
        full['not_a_new_town_LIFE_site_authority']=True
        proposal=json.loads(native_payload(r,delta,checkpoint_sha,'One eastern Tortuga density cluster — no old BE replay'))
        proposal['block_entities']=[{'pos':list(q),'nbt':tag} for q,tag in sorted(p.tags.items())]
        docs={
          'cluster-delta-before-VERIFY-ONLY.json':native_payload(r,{q:before[q] for q in delta},checkpoint_sha,'Exact current eastern density delta preimage'),
          'cluster-density-PROPOSAL.json':(json.dumps(proposal,separators=(',',':'))+'\n').encode(),
          'cluster-complete-before-VERIFY-ONLY.json':with_exact_be_tags(native_payload(r,exported_before,checkpoint_sha,'Complete actual retained current house fields and BEs'),native_tags),
          'cluster-complete-after-VERIFY-ONLY.json':(json.dumps(full,separators=(',',':'))+'\n').encode(),
          'retained-dry-ground-VERIFY-ONLY.json':native_payload(r,supports,checkpoint_sha,'Exact retained dry supports; no platform/ocean fill'),
          'retained-old-BEs-FULL-TYPED-PRIVATE.json':(json.dumps({'checkpoint_sha256':checkpoint_sha,'BEs':bdata},separators=(',',':'))+'\n').encode(),
          'exact-shell-and-grass-changes-PRIVATE.json':(json.dumps({'changes':[{'pos':list(q),**v} for q,v in sorted(p.origins.items())]},separators=(',',':'))+'\n').encode()}
        mask=json.loads(native_payload(r,{q:AIR for q in context},checkpoint_sha,'Future actual house/new authored structure/routes reservation; not observed AIR'))
        mask.update(reservation_only=True,not_an_observed_AIR_plan=True);docs['future-solid-AIR-route-reservation-ONLY.json']=(json.dumps(mask,separators=(',',':'))+'\n').encode()
        cameras=[{'name':'kestrels-new-roof-and-retained-terrace','feet':[1248.5,64,-1197.5],'look_at':[1248,75,-1205]},
            {'name':'new-mender-infill-and-oak-court','feet':[1257.5,64,-1203.5],'look_at':[1257,69,-1209]},
            {'name':'new-mender-lived-in-loft','feet':[1257.5,69,-1208.5],'look_at':[1256,69.8,-1210]},
            {'name':'finch-lower-roof-and-working-court','feet':[1274.5,64,-1204.5],'look_at':[1273,67,-1207]},
            {'name':'apple-sheltered-produce-return','feet':[1289.5,64,-1204.5],'look_at':[1286,66,-1205]}]
        for camera in cameras:
            x,y,z=map(math.floor,camera['feet']);coords=[(x,y-1,z),(x,y,z),(x,y+1,z)]
            values=[after[q] if q in after else snapshot.state(q) for q in coords]
            if key(values[0]) in VOID|{'minecraft:water','minecraft:lava'} or any(key(v) not in VOID for v in values[1:]):raise UserError('A future actual camera lacks measured floor/body: '+camera['name'])
            camera['current_or_proposed_floor_body']=[{'pos':list(q),'state':v} for q,v in zip(coords,values)]
            camera['native_collision_and_actual_framebuffer_acceptance']='PENDING parent-owned native view, not a render mockup'
        record={'format':'awft-eastern-tortuga-density-cluster:1','status':'SOURCE ONLY, native appearance/use review pending; not a37-house rollout',
          'source_sha256':digest(Path(__file__)),'checkpoint_id':checkpoint_id,'checkpoint_sha256':checkpoint_sha,
          'whole52_727BE_ledger_sha256':LEDGER_SHA,'original_compass_source_sha256':SOURCE_SHA,'houses':notes,
          'new_mender':{'name':new.name,'origin':list(new.origin),'rooms':new.rooms,'real_stair_steps':[list(v) for v in new.stairs],'proof':new_proof},
          'purposeful_infill':'A real two-level repair/home occupies the9m gap with2m lanes; a separate open instrument workcourt and side produce arcade close the next gaps. No giant platform or rigid house replication.',
          'material_proofs':materials,'delta_cells':len(delta),'full_context_cells':len(context),'read_only_qualification_cells':len(before),'qualification_cube_not_exported_as_authorship':True,
          'retained_old_BEs':len(actual),'retained_BEs_same_historical575':sum(v['same_as_historical575'] for v in bdata),'native_cameras':cameras,'exact_new_ridge_join_derivations':joins,
          'new_literal_tagged_fixtures':len(p.tags),'old_BE_NBT_or_player_items_written':0,'new_two_wide_route_columns':[list(v) for v in sorted(lane_columns)],
          'existing_walk_body_cells_unchanged':len(walk&set(after)),'exact_current_ordinary_grass_cleared':len(p.soft_cleared),'held_original_joints_and_supports':p.retained,
          'origin_classifications':dict(Counter(v['reason'] for v in p.origins.values())),'role_counts':dict(Counter(p.roles.values())),
          'heritage_sources':heritage_refs,'actual_zipline_mask_sha256':ZIP[1],'saved_sources':snapshot.sources,
          'native_actions':0,'world_writes':0,'native_gates':'Fresh full before/BE/class/stock/support/occupancy inspection, parent-admitted one delta, ordinary settles/full native states/NBT and real eye-level/interior/roof/stair/use pictures. No mass propagation before visual acceptance.',
          'reserve_guard':reserve,'files':{name:{'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)} for name,raw in docs.items()}}
        docs['manifest.json']=(json.dumps(record,ensure_ascii=False,indent=2)+'\n').encode()
        if sum(map(len,docs.values()))>MAX_OUTPUT:raise UserError('Finite density-cluster output exceeded')
        guard(2*MIB,MAX_OUTPUT);out=home/'staging'/('eastern-tortuga-density-'+str(time.time_ns()));out.mkdir()
        for name,raw in docs.items():
            with (out/name).open('xb') as stream:stream.write(raw)
        return {'folder':str(out),'manifest_sha256':digest(out/'manifest.json'),'delta':len(delta),'retained_old_BEs':len(actual),'new_tagged_fixtures':len(p.tags),'native_actions':0}
    finally:snapshot.close()


if __name__=='__main__':
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('--home',type=Path,required=True);a.add_argument('--checkpoint-id',required=True);a.add_argument('--checkpoint-sha',required=True)
    args=a.parse_args();print(json.dumps(prepare(args.home,args.checkpoint_id,args.checkpoint_sha),indent=2))
