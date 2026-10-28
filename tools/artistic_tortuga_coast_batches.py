"""Additional hand-composed coastal masses; frozen earlier five stay intact.

Long low working sheds and wide divided homes are actual occupied geometry,
not renamed massing boxes. The original recipe registry is extended only in
this finite source-writing process, with new keys, and restored afterwards.
No Minecraft registry, save, current container or running instance is edited.
"""
from __future__ import annotations
import argparse,hashlib,json,time,html
from contextlib import contextmanager
from pathlib import Path

from control_room.common import UserError,digest,read_json
from tools.artistic_tortuga_frontages import RECIPES,base,rect,door,window,joists,light,bay_south,side_bay,check,POTS,AIR,key
from tools.artistic_west_r2_frontage import canonical_joins
from tools.artistic_tortuga_fill import modeled,prepare,private_home,stopped
from tools.artistic_bridge_refinement import flatten
from tools.artistic_north_bank_east import NorthTerrain
from tools.artistic_zipline_catenary import reader_budget
from tools.playtest import guard

MIB=1024**2
FIVE=(
 ('staging/tortuga-fill-half-tide-hook-1793207406034724900/manifest.json','5f87166f24476b11971400aee2933ff52ca716501f7a392fbbf8355dc09f2547'),
 ('staging/tortuga-fill-tenon-watch-hook-1793207410549902000/manifest.json','13fc29a5b6452fe4611de3fefc7fb8d0e85e4fdae53c0531429360b0b3043c47'),
)
APPROVED=('staging/west-owner-map-CONCEPT-1793208487635073800/concept.json','13ecf315c0be993ef5d37bdbe250b576808622acf66e8598f76a714ccc35b49a')
QUAY_SOURCE=('staging/tortuga-west-ground-R2-1793203969495539000/west-ground-R2-PROPOSAL.json','63bcb33b6e9d9495ad24e8a7cd62e8c2f19110017dfc032cc3041680c0336518')


def ties(p,x0,x1,y,z,role):
    for x in range(x0,x1+1):p.beam(x,y,z,'x',wood='charred_spruce',role=role)


def wall_shelf(p,x,y,z,face,story,*,books=True):
    dx,dz={'north':(0,-1),'east':(1,0),'south':(0,1),'west':(-1,0)}[face]
    if p.blocks.get((x-dx,y,z-dz),AIR)==AIR:raise UserError('A coastal work shelf needs its actual built backing')
    for yy in(y,y+1):
        if p.blocks.get((x,yy,z),AIR)!=AIR:raise UserError('Keep the already authored shelf surface and headroom objects')
    p.shelf(x,y,z,face,books=books)
    p.supports.append({'detail':[x,y,z],'support':[x-dx,y,z-dz],'role':story})


def ropewalk(registry):
    """A genuinely long low sail-work hall, with a shorter rear home gable."""
    m=rect(0,0,6,17)-{(0,0),(0,1),(6,0)};u=rect(0,9,6,17)
    p=base(registry,'The Bent Ropewalk',m,u,panel='minecraft:brown_terracotta',up='minecraft:gray_terracotta')
    p.roof((-1,-1,7,9),4,(0,1,2,3,4,3,2,1,0),family='dark_oak',annex=True)
    p.roof((-1,8,7,18),8,(0,1,2,3,4,3,2,1,0),family='spruce')
    p.reserve('Long working sail-room spine',[(3,1,z)for z in range(1,17)]+[(x,1,7)for x in(1,2)]+[(4,1,16),(5,1,16)])
    p.reserve('Rear home passage and landing',[(4,5,z)for z in range(10,17)]+[(3,5,13)])
    p.stair_flight(5,15,0)
    for z in(4,8,12,16):ties(p,0,6,4,z,'grounded side-wall tie over the actual long working floor')
    ties(p,0,6,8,14,'actual rear-home ceiling tie between wall heads')
    joists(p,1,5,(3,7,11,15));joists(p,1,5,(11,16),4)
    window(p,0,1,3,'west',width=2);window(p,6,1,2,'east',width=3)
    window(p,6,1,11,'east',width=2);window(p,1,1,17,'south',width=2)
    window(p,0,5,11,'west',width=2);window(p,6,5,14,'east',width=2);bay_south(p,1,18)
    p.put(1,1,2,'minecraft:loom',facing='east',role='real sail and pennant weaving loom')
    p.put(2,1,2,'minecraft:barrel',facing='up',open=False,role='new native-default cloth supplies; no invented Items')
    for z in(4,5,6):p.counter(1,1,z,'east',role='long canvas measuring and fitting bench')
    p.put(1,2,5,'farmersdelight:cutting_board',facing='east',waterlogged=False,role='actual canvas cutting/repair surface')
    wall_shelf(p,1,2,6,'east','grounded order-pattern rack')
    p.put(5,1,2,'minecraft:crafting_table',role='real rope and fastener fitting station')
    p.put(5,1,3,'farmersdelight:dark_oak_cabinet',facing='west',open=False,role='native-default workroom tool cupboard')
    p.counter(5,1,5,'west',role='fitting delivery and watchglass counter')
    p.put(5,2,5,'supplementaries:hourglass',facing='up',light_level=0,waterlogged=False,role='ordinary native work-watch timer')
    p.put(5,1,7,'minecraft:barrel',facing='up',open=False,role='new native-default fastener stock')
    p.put(1,1,10,'minecraft:stonecutter',facing='east',role='real native precision fitting station')
    p.counter(1,1,12,'east',role='separate rear sail-repair bench')
    p.put(1,2,12,'farmersdelight:cutting_board',facing='east',waterlogged=False,role='actual rear repair work surface')
    p.put(1,1,14,'farmersdelight:dark_oak_cabinet',facing='east',open=False,role='ordinary native-default pattern cupboard')
    p.put(2,1,14,'minecraft:loom',facing='south',role='second working loom for a different sail panel')
    wall_shelf(p,1,2,13,'east','rear repair ledgers and spare-pattern rack')
    wall_shelf(p,5,2,10,'west','finished-order and fitting ledgers')
    p.put(1,1,16,'handcrafted:dark_oak_bench',facing='east',shape='single',color='brown',waterlogged=False,role='small waiting seat opposite the rear workbench')
    p.put(2,2,2,POTS[4],role='contained fern on actual stock barrel')
    light(p,3,3,4,'small front cutting-room work light');light(p,3,3,12,'small rear workbench task light')
    p.bed(1,5,13)
    p.put(1,5,15,'handcrafted:dark_oak_desk',facing='east',color='brown',waterlogged=False,role='rigger’s real upstairs order desk')
    p.put(1,6,15,'handcrafted:stackable_book',facing='east',books=3,seed=12,role='household and sail-order accounts')
    p.put(2,5,15,'handcrafted:dark_oak_chair',facing='west',color='brown',waterlogged=False,role='properly facing desk chair')
    p.put(5,5,10,'minecraft:smoker',facing='west',lit=False,role='real safe household cooking hearth')
    p.put(5,5,16,'farmersdelight:dark_oak_cabinet',facing='west',open=False,role='new native-default household pantry')
    p.put(3,5,11,'handcrafted:dark_oak_side_table',facing='south',color='none',waterlogged=False,role='small upstairs supper table')
    p.put(3,6,11,'handcrafted:wood_cup',facing='south',pieces=2,waterlogged=False,role='ordinary household cups')
    wall_shelf(p,1,6,14,'east','small personal bookshelf beside the desk')
    light(p,3,7,14,'small upper-home reading lantern')
    door(p,0,7,'west');p.sign(-1,3,10,'west',['The Bent Ropewalk','Canvas • Rigging']);p.put(0,3,10,'minecraft:dark_oak_planks')
    p.room('Long canvas measuring and fitting shop',0,(3,1,5),'Real loom, a long cutting workbench, sorted vessels, tools, timer, patterns and small supported task lights occupy a genuinely long low wing.')
    p.room('Rear sail-repair shop',0,(3,1,13),'A separate precision/repair bench, second loom, backed accounts and waiting seat sit beneath the shorter rear home.')
    p.room('Rigger’s rear home',4,(4,5,13),'Real stair, bed, reading desk and facing chair, kitchen, pantry, supper table and glazed rear oriel.')
    canonical_joins(p);return p


def divided_house(registry):
    """Wide shallow service house: divided workrooms, two smaller roof masses."""
    m=rect(0,0,12,6)-{(0,0),(12,6),(11,6)}
    u=rect(0,0,5,6)|rect(6,1,11,5)
    p=base(registry,'The Leaning Galley',m,u,panel='minecraft:gray_terracotta',up='minecraft:brown_terracotta')
    p.roof((-1,-1,6,7),8,(0,1,2,3,3,2,1,0),family='dark_oak')
    p.roof((6,0,13,6),8,(0,1,2,2,2,1,0,0),family='spruce')
    p.reserve('Galley front-to-back public service aisle',[(4,1,z)for z in range(1,6)]+[(x,1,3)for x in range(4,11)]+[(6,1,1),(6,1,2)])
    p.reserve('Ordinary upper landing and shared home passage',[(4,5,z)for z in range(1,5)]+[(x,5,2)for x in range(4,10)])
    p.stair_flight(5,5,0)
    for z in(2,4):ties(p,0,5,4,z,'actual western workshop ceiling tie');ties(p,6,12,4,z,'actual eastern service-room ceiling tie')
    ties(p,0,5,8,3,'actual west home ceiling tie');ties(p,6,11,8,3,'actual east home ceiling tie')
    joists(p,1,4,(2,5));joists(p,7,11,(2,5));joists(p,1,4,(2,5),4);joists(p,7,10,(2,4),4)
    window(p,0,1,2,'west',width=2);window(p,12,1,2,'east',width=2)
    window(p,1,1,6,'south',width=2);window(p,8,1,6,'south',width=2)
    window(p,1,5,0,'north',width=2);window(p,8,5,1,'north',width=2)
    bay_south(p,1,7);side_bay(p,12,2,'east')
    for z in(1,2,4):p.counter(1,1,z,'east',role='working service counter and bread preparation return')
    p.put(1,2,2,'handcrafted:terracotta_bowl',facing='east',pieces=3,waterlogged=False,role='actual mixing and serving vessels')
    p.put(2,1,1,'minecraft:barrel',facing='up',open=False,role='ordinary new native-default service stock')
    p.put(2,2,1,'handcrafted:wood_cup',facing='south',pieces=3,waterlogged=False,role='cups on the real stock surface')
    p.put(1,1,5,'farmersdelight:dark_oak_cabinet',facing='east',open=False,role='actual floor-mounted linen/service cupboard')
    wall_shelf(p,1,2,4,'east','working service bills and order ledgers')
    p.put(3,1,5,'handcrafted:dark_oak_table',color='none',shape='single',waterlogged=False,role='small sheltered service-room supper table')
    p.put(2,1,5,'handcrafted:dark_oak_chair',facing='east',color='brown',waterlogged=False,role='real chair opposite the supper table')
    p.put(3,2,5,'handcrafted:wood_cup',facing='south',pieces=2,waterlogged=False,role='cups on the actual little table')
    for x,kind in((8,'smoker'),(9,'furnace')):p.put(x,1,1,'minecraft:'+kind,facing='south',lit=False,role='real native cookhouse hearth')
    p.put(10,1,1,'minecraft:water_cauldron',level=3,role='contained native washing water')
    p.put(11,1,2,'farmersdelight:dark_oak_cabinet',facing='west',open=False,role='native-default food preparation pantry')
    for z in(3,4):p.counter(11,1,z,'west',role='real cookhouse preparation bench')
    p.put(11,2,4,'farmersdelight:cutting_board',facing='west',waterlogged=False,role='actual native preparation board')
    p.put(11,1,1,'farmersdelight:dark_oak_cabinet',facing='west',open=False,role='ordinary floor-supported serving cupboard')
    wall_shelf(p,11,2,1,'west','cookhouse serving-vessel shelf',books=False)
    p.put(8,1,5,'handcrafted:dark_oak_bench',facing='north',shape='single',color='brown',waterlogged=False,role='small crew waiting bench beside the workroom')
    p.put(9,2,1,POTS[0],role='contained pale workroom flower on the safe unlit native hearth')
    light(p,3,3,4,'small practical public-counter task lantern');light(p,9,3,4,'small practical cookhouse task lantern')
    p.bed(1,5,3)
    p.put(1,5,5,'handcrafted:dark_oak_desk',facing='east',color='brown',waterlogged=False,role='first household’s order desk')
    p.put(1,6,5,'handcrafted:stackable_book',facing='east',books=3,seed=9,role='household accounts')
    p.put(2,5,5,'handcrafted:dark_oak_chair',facing='west',color='brown',waterlogged=False,role='properly facing first-home chair')
    p.put(3,5,1,'farmersdelight:dark_oak_cabinet',facing='south',open=False,role='actual first-home pantry below a real wall')
    p.bed(8,5,4,face='east')
    p.put(10,5,2,'handcrafted:dark_oak_desk',facing='north',color='brown',waterlogged=False,role='second household’s little writing desk')
    p.put(10,6,2,'handcrafted:stackable_book',facing='north',books=3,seed=4,role='ordinary personal book models')
    p.put(10,5,3,'handcrafted:dark_oak_chair',facing='north',color='brown',waterlogged=False,role='second-home reading chair at the desk')
    p.put(7,5,4,'handcrafted:dark_oak_side_table',facing='south',color='none',waterlogged=False,role='second-home supper side table')
    p.put(7,6,4,'handcrafted:wood_cup',facing='south',pieces=2,waterlogged=False,role='actual household cups')
    light(p,3,7,3,'small first-home reading light');light(p,9,7,3,'small second-home reading light')
    door(p,6,0,'north');p.sign(9,3,-1,'north',['The Leaning Galley','Supper • Service']);p.put(9,3,0,'minecraft:dark_oak_planks')
    p.room('Small divided service room',0,(4,1,4),'A working counter, service stock, backed orders, drawer and supper seat occupy a wide shallow working frontage.')
    p.room('Real cookhouse and preparation room',0,(9,1,3),'Actual two hearths, contained wash water, food pantry, preparation board, vessel storage and small waiting bench.')
    p.room('First compact upper home',4,(4,5,4),'An ordinary stair reaches the actual bed, desk, facing chair, pantry and proud rear window.')
    p.room('Second upper household',4,(7,5,3),'A separate small writing/bed/supper group fits below a lower second roof mass with a genuine glazed side bay.')
    canonical_joins(p);return p


def kettle_loft(registry):
    """A tiny five-wide sea-edge cook/shop with a deeply recessed real door."""
    m=rect(0,0,4,9)-{(4,9)};u=rect(0,2,4,9)
    p=base(registry,'The Tide Stove',m,u,panel='minecraft:brown_terracotta',up='minecraft:gray_terracotta')
    p.roof((-1,1,5,10),8,(0,1,2,3,2,1,0),family='dark_oak')
    p.roof((-1,-1,5,2),4,(0,1,2,3,2,1,0),family='spruce',annex=True)
    p.reserve('Little cookshop passage',[(2,1,z)for z in range(1,9)]+[(1,1,1),(0,1,1)])
    p.reserve('Small upper home passage',[(2,5,z)for z in range(3,9)])
    p.stair_flight(3,7,0)
    ties(p,0,4,4,4,'actual narrow ground-floor ceiling tie');ties(p,0,4,8,6,'actual small-home ceiling tie')
    joists(p,1,3,(3,7));joists(p,1,3,(4,8),4)
    window(p,0,1,4,'west',width=2,height=3);window(p,1,1,9,'south',width=2)
    window(p,0,5,3,'west',width=2);window(p,4,5,3,'east',width=2);bay_south(p,1,10)
    p.put(3,1,1,'minecraft:crafting_table',role='actual little service and fitting bench')
    p.counter(1,1,2,'east',role='small ordinary food/service preparation counter')
    p.put(1,2,2,'farmersdelight:cutting_board',facing='east',waterlogged=False,role='real preparation board')
    p.put(1,1,4,'minecraft:smoker',facing='east',lit=False,role='real safe small cookshop hearth')
    p.put(1,1,6,'minecraft:barrel',facing='up',open=False,role='ordinary new native-default service stock')
    p.put(3,2,1,POTS[4],role='contained little fern on the actual fitting bench')
    p.put(1,1,8,'farmersdelight:dark_oak_cabinet',facing='north',open=False,role='actual floor-mounted service cupboard')
    wall_shelf(p,1,2,6,'east','little cookshop order ledgers')
    p.put(3,1,2,'minecraft:water_cauldron',level=3,role='real contained preparation/rinsing water')
    light(p,2,3,4,'small ordinary preparation task light')
    p.bed(1,5,5)
    p.put(1,5,7,'handcrafted:dark_oak_desk',facing='north',color='brown',waterlogged=False,role='real little upstairs account desk')
    p.put(1,6,7,'handcrafted:stackable_book',facing='north',books=3,seed=6,role='personal and shop books')
    p.put(1,5,6,'handcrafted:dark_oak_chair',facing='south',color='brown',waterlogged=False,role='chair facing its actual desk')
    p.put(3,5,8,'minecraft:smoker',facing='west',lit=False,role='real small private-home hearth')
    p.put(1,5,3,'farmersdelight:dark_oak_cabinet',facing='east',open=False,role='new native-default upper-home pantry')
    p.put(1,5,8,'handcrafted:dark_oak_side_table',facing='south',color='none',waterlogged=False,role='small real household supper table')
    p.put(1,6,8,'handcrafted:wood_cup',facing='south',pieces=2,waterlogged=False,role='ordinary cups on the actual table')
    wall_shelf(p,3,6,7,'west','real backed little household bookshelf')
    light(p,2,7,6,'small private reading light')
    # Keep the whole threshold and its cheeks inside the five-wide main body.
    for z in(0,2):
        for y in(1,2,3):p.put(0,y,z,'dawnoftimebuilder:charred_spruce_timber_frame_pillar',axis='y',role='rooted deep little doorway cheek')
        p.put(-1,3,z,'mythrais:curved_corbel_dark_oak',facing='west',shape=0,role='small high recessed-door support')
    for z in(0,1,2):p.beam(0,4,z,'z',wood='dark_oak',role='real recessed-entry lintel')
    for y,half in((1,'lower'),(2,'upper')):p.put(1,y,1,'mcwdoors:dark_oak_cottage_door',facing='east',half=half,hinge='left',open=False,powered=False)
    p.entries.append({'owner':p.owner,'door':[1,1,1],'outward':'west','outside_step':[0,0,1]})
    p.sign(-1,3,1,'west',['The Tide Stove','Warm Food • Repairs']);p.put(0,3,1,'minecraft:dark_oak_planks')
    p.room('Tiny working cookshop',0,(2,1,5),'A real hearth, preparation board, pantry, wash water, backed order rack and contained window plant fill the narrow working frontage.')
    p.room('Sea-edge cook’s little home',4,(2,5,6),'An actual stair, bed, desk and correctly facing chair, backed books, pantry, supper table and proud glazed rear oriel.')
    canonical_joins(p);return p


EXTRA={'coast-ropewalk':ropewalk,'coast-divided-house':divided_house,'coast-kettle-loft':kettle_loft}


@contextmanager
def source_recipes():
    """No replacement of old recipes and no persistent global registry drift."""
    if set(EXTRA)&set(RECIPES):raise UserError('Do not replace or silently change an original frozen recipe')
    RECIPES.update(EXTRA)
    try:yield
    finally:
        for key in EXTRA:RECIPES.pop(key,None)


BATCHES={
 'bent-ropewalk-coast':{
  'buildings':({'recipe':'coast-ropewalk','turn':1,'name':'The Bent Ropewalk','trade':'Canvas • Rigging • Repairs','origin':(1161,63,-1210)},),
  'links':(('Short actual north-facing ropewalk service approach',((1170,-1212),(1167,-1212))),),
  'design':'One genuinely long low working frontage with a shorter occupied rear home, rather than another narrow tall house. The three useful rooms are fully furnished and every stair/light/shelf has actual geometry.',
  'street_views':(('Long ropewalk north face',(1167.5,64,-1211.5),(1170,67,-1206)),),
 },
 'leaning-galley-hook':{
  'buildings':({'recipe':'coast-divided-house','turn':2,'name':'The Leaning Galley','trade':'Supper • Service • Rooms','origin':(1124,63,-1229)},),
  'links':(('Tiny dry inland working lane outside the wide divided house',((1129,-1221),(1126,-1221))),),
  'design':'A shallow wide cook/service house divided into two inhabited upper households, with different roof masses, an occupied rear oriel and a glazed side bay. The real door faces the dry inland side, preserving the waterline beyond the opposite wall.',
  'street_views':(('Wide galley inland frontage',(1128.5,64,-1220.5),(1131,68,-1226)),),
 },
 'tide-stove-west-quay':{
  'buildings':({'recipe':'coast-kettle-loft','turn':2,'name':'The Tide Stove','trade':'Warm Food • Repairs','origin':(983,63,-1280)},),
  'links':(('Shared actual open-workshop and cookshop threshold',((988,-1272),(988,-1272))),),
  'design':'A very small deeply recessed five-wide sea-edge shop/home faces the retained inner quay; no main floor is allowed in the water and the rear upper oriel is a supported small projection.',
  'street_views':(('Small cookshop east front',(989.5,64,-1277.5),(985,67,-1277)),),
 },
}


def paved_public_quay(home,receipt,registry):
    """Retained paved walking only; never construction or clearing authority."""
    if digest(home/QUAY_SOURCE[0])!=QUAY_SOURCE[1]:raise UserError('Exact actual R2 public-quay delta required')
    expected=flatten(read_json(home/QUAY_SOURCE[0]));reader_budget();terrain=NorthTerrain(home,receipt,registry);rows=[]
    try:
        for x,z in((988,-1272),(988,-1271),(989,-1272),(989,-1271)):
            values=[terrain.state(x,y,z)for y in(63,64,65)]
            if expected.get((x,63,z))!='minecraft:cobblestone'or values!=['minecraft:cobblestone',AIR,AIR]:raise UserError('Retain the exact actual cobbled public threshold and clear body')
            if any((x,y,z)in terrain.entities for y in(62,63,64,65)):raise UserError('No public walking proof over a current BE')
            rows.append([x,z,*values])
        sources=terrain.snapshot.sources;budget=reader_budget()
    finally:terrain.close()
    return rows,{'source_delta':QUAY_SOURCE[0],'source_delta_sha256':QUAY_SOURCE[1],'saved_sources':sources,'reader_budget':budget,
                 'purpose':'Existing literal cobbled public walking surface only; no building authority, no AIR clear, no existing inventory replay'}


def derived_field(home,checkpoint_id,checkpoint_sha,field_path,field_sha,*,public_quay=False):
    """Only subtract earlier five future targets; never invent observed AIR."""
    home=private_home(home);reserve=guard(0,16*MIB);receipt=stopped(home,checkpoint_id,checkpoint_sha)
    field_path=Path(field_path).resolve()
    if not field_path.is_relative_to(home/'staging')or field_path.stat().st_size>32*MIB or digest(field_path)!=field_sha:raise UserError('Exact bounded current field required')
    data=read_json(field_path)
    if(data.get('checkpoint_id'),data.get('checkpoint_sha256'))!=(checkpoint_id,checkpoint_sha):raise UserError('Do not rebind an old coastal field')
    if digest(home/APPROVED[0])!=APPROVED[1]:raise UserError('Exact owner-reviewed full western concept required')
    concept=read_json(home/APPROVED[0])
    approved={tuple(q)for row in concept['proposed_buildings']for q in row['cells_xz']}
    approved|={tuple(q)for row in concept['crooked_alley_lines']for segment in row['segments']for q in segment['cells_xz']}
    excluded=set();refs=[{'relative':APPROVED[0],'sha256':APPROVED[1],'role':'Owner-reviewed2D full city intent; minor actual door/alley fit still needs parent admission, not Native acceptance'}]
    for rel,sha in FIVE:
        if digest(home/rel)!=sha:raise UserError('Keep exact five earlier frontages and stock-safe routes')
        manifest=read_json(home/rel);p=home/Path(rel).parent/'cluster-PROPOSAL.json'
        if digest(p)!=manifest['files'][p.name]['sha256']:raise UserError('Retain exact earlier source targets')
        states=flatten(read_json(p));excluded|={(x,z)for x,y,z in states if 63<=y<=85}
        for building in manifest['buildings']:
            data['retained_source_main_footprints']['retained latest five '+building['name']]=building['main_columns_xz']
        refs.append({'relative':str(p.relative_to(home)),'sha256':digest(p),'role':'Unplaced or placed earlier target keepout; never observed current AIR'})
    before_build=data['eligible_columns_READONLY'];before_walk=data['two_high_walk_columns_READONLY']
    data['eligible_columns_READONLY']=[r for r in before_build if tuple(r[:2])not in excluded and tuple(r[:2])in approved]
    data['two_high_walk_columns_READONLY']=[r for r in before_walk if tuple(r[:2])not in excluded]
    public=[];public_proof=None;added_walk=0
    if public_quay:
        public,public_proof=paved_public_quay(home,receipt,read_json(home/'dashboard/settlement/registry.json'))
        walking={tuple(r[:2]):r for r in data['two_high_walk_columns_READONLY']}
        added_walk=sum(tuple(r[:2])not in walking for r in public)
        walking.update({tuple(r[:2]):r for r in public});data['two_high_walk_columns_READONLY']=list(walking.values())
    data.update(coastal_subset_source_sha256=digest(Path(__file__)),parent_field={'relative':str(field_path.relative_to(home)),'sha256':field_sha},
      added_buildable_authority_columns=0,added_literal_retained_public_walk_columns=added_walk,subtracted_earlier_target_columns=len(excluded),additional_keepouts=refs,reserve_guard=reserve,
      eligible_columns=len(data['eligible_columns_READONLY']),retained_public_walking_rows=public,retained_public_walking_proof=public_proof)
    raw=(json.dumps(data,separators=(',',':'))+'\n').encode()
    if len(raw)>16*MIB:raise UserError('Finite16MiB subtract-only coastal field cap exceeded')
    out=home/'staging'/('tortuga-coastal-subset-'+str(time.time_ns()));out.mkdir();(out/'field-READONLY.json').open('xb').write(raw)
    return out/'field-READONLY.json',digest(out/'field-READONLY.json')


def prepare_batch(home,checkpoint_id,checkpoint_sha,field_path,field_sha,batch):
    if batch not in BATCHES:raise UserError('An exact manually composed coastal batch is required')
    guard(8*MIB,80*MIB)
    subset,sha=derived_field(home,checkpoint_id,checkpoint_sha,field_path,field_sha,public_quay=batch=='tide-stove-west-quay')
    with source_recipes():
        registry=read_json(Path(home)/'dashboard/settlement/registry.json')
        states,_,_,_=modeled(registry,BATCHES[batch])
        if len(states)+2048>12000:raise UserError('Keep each actual native batch below12K targets, including finite entrance allowance')
        result=prepare(home,checkpoint_id,checkpoint_sha,subset,sha,batch,definition=BATCHES[batch],definition_source=Path(__file__))
    folder=Path(result['folder']);manifest=read_json(folder/'manifest.json')
    if manifest['targets']>12000:raise UserError('Prepared artifact is retained but must never be admitted above12K targets')
    map_bytes=batch_map(manifest,read_json(subset))
    if len(map_bytes)>MIB:raise UserError('Finite1MiB source map cap exceeded')
    (folder/'batch-map-PLAN-ONLY.svg').open('xb').write(map_bytes)
    manifest['files']['batch-map-PLAN-ONLY.svg']={'sha256':hashlib.sha256(map_bytes).hexdigest(),'bytes':len(map_bytes),'tier':'SOURCE PLANNING SCHEMATIC ONLY; actual Native before/after map and photos required'}
    manifest['native_target_cap']=12000;manifest['approved_west_concept']={'relative':APPROVED[0],'sha256':APPROVED[1]}
    (folder/'manifest.json').write_text(json.dumps(manifest,separators=(',',':'))+'\n',encoding='utf-8')
    result['manifest_sha256']=digest(folder/'manifest.json');result['files']=manifest['files']
    return result


def batch_map(manifest,field):
    """Literal planned footprints, not an imitation of a Minecraft image."""
    mains={tuple(q)for b in manifest['buildings']for q in b['main_columns_xz']}
    lanes={tuple(q)for row in manifest['routes']for q in row['columns_xz']}
    points=mains|lanes;x0=min(x for x,z in points)-5;x1=max(x for x,z in points)+5;z0=min(z for x,z in points)-5;z1=max(z for x,z in points)+5
    scale=18;top=85;width=max(640,(x1-x0+1)*scale);height=(z1-z0+1)*scale+top+55
    def rect(x,z,fill,stroke='none'):
        return f'<rect x="{(x-x0)*scale}" y="{top+(z-z0)*scale}" width="{scale}" height="{scale}" fill="{fill}" stroke="{stroke}"/>'
    out=[f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}"><rect width="100%" height="100%" fill="#f4efe4"/>',
      '<g font-family="sans-serif" fill="#282722"><text x="16" y="25" font-size="17">SOURCE PLANNING MAP — NOT A NATIVE SCREENSHOT</text>',
      '<text x="16" y="47" font-size="12">'+html.escape(manifest['cluster']if'cluster'in manifest else manifest['batch'])+' • North is up • Each small cell =1 block</text>',
      '<text x="16" y="66" font-size="11">Gray: retained source footprint • Brown: proposed mass • Gold: short entrance lane • Blank: no dry claim</text></g>']
    dry={tuple(r[:2])for r in field['eligible_columns_READONLY']}|{tuple(r[:2])for r in field['two_high_walk_columns_READONLY']}
    for x,z in sorted(dry):
        if x0<=x<=x1 and z0<=z<=z1:out.append(rect(x,z,'#e1e2d2'))
    for name,cells in field.get('retained_source_main_footprints',{}).items():
        for x,z in cells:
            if x0<=x<=x1 and z0<=z<=z1:out.append(rect(x,z,'#a5a6a0'))
    for x,z in sorted(lanes):out.append(rect(x,z,'#bb9b61','#91733d'))
    for index,b in enumerate(manifest['buildings']):
        cells=set(map(tuple,b['main_columns_xz']))
        for x,z in sorted(cells):out.append(rect(x,z,('#6f5949','#89745b','#60594d')[index%3],'#4a4036'))
        cx=sum(x for x,z in cells)/len(cells);cz=sum(z for x,z in cells)/len(cells)
        out.append(f'<text x="{(cx-x0)*scale}" y="{top+(cz-z0)*scale}" fill="white" text-anchor="middle" font-family="sans-serif" font-size="12">{html.escape(b["name"])}</text>')
        for e in b['entries']:
            x,_,z=e['world_door'];out.append(rect(x,z,'#e5ce8b','#64562e'))
    out.append(f'<text x="16" y="{height-20}" font-family="sans-serif" font-size="12">{manifest["main_columns"]} building columns; {manifest["lane_columns"]} entrance-walk columns. Native geometry, walking and art acceptance pending.</text></svg>')
    return ''.join(out).encode()


if __name__=='__main__':
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('--home',type=Path,required=True);a.add_argument('--checkpoint-id',required=True);a.add_argument('--checkpoint-sha',required=True)
    a.add_argument('--field',type=Path,required=True);a.add_argument('--field-sha',required=True);a.add_argument('--batch',required=True);args=a.parse_args()
    print(json.dumps(prepare_batch(args.home,args.checkpoint_id,args.checkpoint_sha,args.field,args.field_sha,args.batch),indent=2))
