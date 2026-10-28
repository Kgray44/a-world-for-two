"""Individually fitted western-spit buildings for the approved pirate-city plan.

Source only. This additive lane owns X968..1099; the inner-West lane is
separate. Earlier placed/queued construction and inventory stay protected.
"""
from __future__ import annotations
import argparse,hashlib,json,time,math,types
from contextlib import contextmanager
from pathlib import Path

from control_room.common import UserError,digest,read_json
from tools import artistic_tortuga_fill as fill
from tools import artistic_tortuga_coast_batches as coast
from tools import artistic_tortuga_west_approved_blocks as previous
from tools.artistic_tortuga_frontages import RECIPES,AIR,POTS,key,base,rect,window,bay_south,light,joists,check
from tools.artistic_west_r2_frontage import canonical_joins,Frontage
from tools.artistic_bridge_refinement import flatten
from tools.artistic_north_bank_east import NorthTerrain,native_payload,GROUND,SOFT,NORTH_SOFT,AIR as VOIDS
from tools.artistic_create_substrate import verify_zinc_factory,qualified_mount
from tools.artistic_zipline_catenary import reader_budget
from tools.playtest import guard

MIB=1024**2
QUEUED=previous.QUEUED+(
 ('staging/tortuga-fill-net-needle-crook-1793212893524565700/manifest.json','345b32431c44cf7df6bb37f03b933dd9c1fd7670dd4e9f70243ec56c99d2ce47'),
 ('staging/tortuga-fill-moon-tackle-returns-1793212899675804500/manifest.json','5e5eb07cf443dc9851875f7bcc0cd8aee849d61dadf3152f76bbec2966ce5486'),
 ('staging/tortuga-fill-chart-window-loft-1793212905634658900/manifest.json','accfeb92b096f3d87ae939f41014a5870d2489f3377c150ac4a150f05ccf99a1'),
)


def short_loft(registry,*,depth=8,trade='fittings',oriel=True):
    """A genuinely small occupied shop, with an internal stair and home.

The short footprint is needed by literal narrow coastal gaps. Its recessed
door, rather than a proud three-post porch, leaves the shared alley clear.
"""
    if depth not in(7,8)or trade not in('fittings','salt','cloth','charts'):raise UserError('Exact small-house composition required')
    m=rect(0,0,4,depth-1)-{(4,depth-1)};u=rect(0,2,4,depth-1)
    p=base(registry,'Short working loft — '+trade,m,u,panel='minecraft:brown_terracotta',up='minecraft:gray_terracotta')
    p.roof((-1,1,5,depth),8,(0,1,2,3,2,1,0),family='dark_oak',hip_south=trade=='cloth')
    p.roof((-1,-1,5,2),4,(0,1,2,3,2,1,0),family='spruce',annex=True)
    p.reserve('Small shop’s actual working aisle',[(2,1,z)for z in range(1,depth-1)]+[(0,1,1),(1,1,1)])
    p.reserve('Small home’s stair-side passage',[(2,5,z)for z in range(2,depth-2)])
    p.stair_flight(3,5,0)
    coast.ties(p,0,4,4,3,'real short-shop ceiling tie');coast.ties(p,0,4,8,depth-3,'small home’s supported tie')
    joists(p,1,3,(3,));joists(p,1,3,(3,depth-2),4)
    window(p,0,1,3,'west',width=2,height=2);window(p,4,1,depth-3,'east',width=1,height=2)
    window(p,0,5,3,'west',width=2)
    if oriel:bay_south(p,1,depth)
    else:window(p,1,5,depth-1,'south',width=2)
    work={'fittings':'minecraft:stonecutter','salt':'minecraft:smoker','cloth':'minecraft:loom','charts':'minecraft:cartography_table'}[trade]
    props={}if trade=='charts'else{'facing':'west'}
    if trade=='salt':props['lit']=False
    p.put(3,1,1,work,role={'fittings':'real small fastener and stone-fitting work station','salt':'real native safe fish-curing hearth','cloth':'real compact sail/cloth weaving station','charts':'real small chart correction and copying station'}[trade],**props)
    p.counter(1,1,3,'east',role='actual small trade-order and repair counter')
    p.put(1,2,3,'farmersdelight:cutting_board',facing='east',waterlogged=False,role='actual preparation and small repair work surface')
    p.put(1,1,depth-2,'minecraft:barrel',facing='up',open=False,role='new native-default trade stock; no fabricated contents')
    coast.wall_shelf(p,1,2,depth-2,'east','backed small-shop order ledgers')
    p.put(1,1,2,'minecraft:dark_oak_planks',role='actual full-depth contained-plant display plinth')
    p.put(1,2,2,POTS[4],role='contained fern on its real full display plinth')
    light(p,2,3,3,'small task lantern over the actual repair counter')
    p.bed(1,5,4)
    p.put(1,5,depth-2,'handcrafted:dark_oak_desk',facing='east',color='brown',waterlogged=False,role='real upper-home household and work accounts')
    p.put(1,6,depth-2,'handcrafted:stackable_book',facing='east',books=3,seed=4,role='actual household books on the little desk')
    p.put(2,5,depth-2,'handcrafted:dark_oak_chair',facing='west',color='brown',waterlogged=False,role='chair facing the real small desk')
    if depth==8:
        p.put(1,5,5,'minecraft:smoker',facing='east',lit=False,role='ordinary safe private-home hearth')
        p.put(3,5,6,'farmersdelight:dark_oak_cabinet',facing='west',open=False,role='actual home pantry beyond the open stair flight')
    light(p,2,7,depth-3,'small private home reading light')
    for z in(0,2):
        for y in(1,2,3):p.put(0,y,z,'dawnoftimebuilder:charred_spruce_timber_frame_pillar',axis='y',role='rooted deep-door cheek within the small main mass')
        p.put(-1,3,z,'mythrais:curved_corbel_dark_oak',facing='west',shape=0,role='small high doorway support')
    for z in(0,1,2):p.beam(0,4,z,'z',wood='dark_oak',role='real recessed-door head')
    for y,half in((1,'lower'),(2,'upper')):p.put(1,y,1,'mcwdoors:dark_oak_cottage_door',facing='east',half=half,hinge='left',open=False,powered=False)
    p.entries.append({'owner':p.owner,'door':[1,1,1],'outward':'west','outside_step':[0,0,1]})
    p.sign(-1,3,1,'west',['Short working loft',trade.title()+' • Home']);p.put(0,3,1,'minecraft:dark_oak_planks')
    p.room('Small '+trade+' workshop',0,(2,1,depth-3),'A real trade station, working counter, backed order shelves, contained plant and native-default stock fit the literal small coastal gap.')
    p.room('Occupied little loft',4,(2,5,3),'A real internal stair serves the usable bed, household accounts desk and facing chair, books and small reading light behind a proud glazed oriel; the longer variant also has a safe hearth and real pantry.')
    canonical_joins(p);return p


def low_cordage_shop(registry):
    """A low long workshop, not an empty paved strip or another tall home."""
    depth=13;m=rect(0,0,3,depth-1)
    p=Frontage(registry,(0,63,0));p.owner='The Low Cordage Shop';p.main[p.owner]=set(m);p.levels[p.owner]=[set(m)]
    for x,z in m:
        for y in range(1,9):p.put(x,y,z,AIR)
    p.floor(m,0);p.walls(m,0,'minecraft:gray_terracotta')
    p.roof((0,-1,4,depth),4,(1,2,2,1,0),family='dark_oak',annex=True)
    p.reserve('Real long workshop aisle',[(2,1,z)for z in range(1,depth-1)])
    for z in(3,7,11):coast.ties(p,0,3,4,z,'short supported tie under the low workshop roof')
    joists(p,1,2,(4,8))
    window(p,3,1,3,'east',width=2);window(p,3,1,9,'east',width=2)
    p.put(1,1,1,'minecraft:loom',facing='east',role='real pennant and braided-cloth loom')
    p.put(1,1,2,'minecraft:barrel',facing='up',open=False,role='new native-default cordage supplies, no copied stock')
    for z in(4,5,6):p.counter(1,1,z,'east',role='long real measuring and repair workbench')
    p.put(1,2,5,'farmersdelight:cutting_board',facing='east',waterlogged=False,role='native cordage and cloth cutting surface')
    p.put(1,1,8,'farmersdelight:dark_oak_cabinet',facing='east',open=False,role='actual fixed tool cupboard')
    p.put(1,1,9,'minecraft:crafting_table',role='real rope-fastener fitting bench')
    p.put(1,1,10,'minecraft:barrel',facing='up',open=False,role='ordinary finished-order stock vessel')
    p.put(1,2,10,POTS[0],role='contained small flower on the real full stock barrel')
    coast.wall_shelf(p,1,2,11,'east','backed workshop account books and pattern notes')
    light(p,2,3,3,'small low-workshop entrance task light');light(p,2,3,10,'small light over the actual fitting bench')
    for x in(1,3):
        for y in(1,2,3):p.put(x,y,depth-1,'dawnoftimebuilder:charred_spruce_timber_frame_pillar',axis='y',role='rooted short-end doorway cheek')
        p.put(x,3,depth,'mythrais:curved_corbel_dark_oak',facing='south',shape=0,role='small high short-end door support')
    for x in(1,2,3):p.beam(x,4,depth-1,'x',wood='charred_spruce',role='real recessed short-end lintel')
    for y,half in((1,'lower'),(2,'upper')):p.put(2,y,depth-2,'mcwdoors:dark_oak_cottage_door',facing='north',half=half,hinge='left',open=False,powered=False)
    p.entries.append({'owner':p.owner,'door':[2,1,depth-2],'outward':'south','outside_step':[2,0,depth-1]})
    p.sign(4,3,10,'east',['The Low Cordage','Patterns • Rope']);p.put(3,3,10,'minecraft:dark_oak_planks')
    p.room('Front weaving and measuring workroom',0,(2,1,3),'The real loom and long measuring/cutting workbench occupy the front of one deliberately low workshop; this is a working scene, not an invented separate dwelling.')
    p.room('Rear fitting and finished-order scene',0,(2,1,9),'A real fitting bench, tool cupboard, native-default finished stock, backed accounts, contained flower and small task light serve the rear of the same long workshop.')
    canonical_joins(p);return p


def recessed_original(registry,recipe):
    """Run the frozen original with an explicit process-local door composer.

    Copying the function globals avoids editing its module or recipe map.
    Only the NEW source model gets a recessed entry; retained stock and
    every original source byte remain untouched.
    """
    original=RECIPES[recipe]
    def recess(p,x,z,face):
        dx,dz={'north':(0,-1),'east':(1,0),'south':(0,1),'west':(-1,0)}[face]
        tx,tz=(1,0)if dz else(0,1);inward={'north':'south','east':'west','south':'north','west':'east'}[face]
        xx,zz=x-dx,z-dz
        if any(p.blocks.get((xx,y,zz),AIR)!=AIR for y in(1,2)):
            raise UserError('A new recessed door must not replace its already furnished approach')
        for side in(-1,0,1):
            ax,az=x+side*tx,z+side*tz
            if (ax,az)not in p.main[p.owner]:raise UserError('Keep the recessed threshold inside its actual dry main body')
            p.put(ax,0,az,'minecraft:stone_bricks',role='actual grounded recessed-entry threshold')
            if side:
                for y in(1,2,3):p.put(ax,y,az,'dawnoftimebuilder:charred_spruce_timber_frame_pillar',axis='y',role='rooted entry cheek kept inside this new mass')
                p.put(ax+dx,3,az+dz,'mythrais:curved_corbel_dark_oak',facing=face,shape=0,role='small high recessed-entry bracket')
            p.beam(ax,4,az,'x'if tx else'z',wood='charred_spruce'if tx else'dark_oak',role='supported deep recessed-entry head')
        for y,half in((1,'lower'),(2,'upper')):
            p.put(x,y,z,AIR)
            p.put(xx,y,zz,'mcwdoors:dark_oak_cottage_door',facing=inward,half=half,hinge='left',open=False,powered=False)
        p.entries.append({'owner':p.owner,'door':[xx,1,zz],'outward':face,'outside_step':[x,0,z]})
    factory=types.FunctionType(original.__code__,{**original.__globals__,'door':recess},original.__name__,original.__defaults__,original.__closure__)
    p=factory(registry);canonical_joins(p);return p


def compact_workshop(registry,*,depth=7,kind='lanterns'):
    if (depth,kind)not in((7,'lanterns'),(8,'fittings')):raise UserError('Exact authored coastal workshop required')
    m=rect(0,0,3,depth-1)-{(0,0)}
    p=Frontage(registry,(0,63,0));p.owner='Compact '+kind+' workshop';p.main[p.owner]=set(m);p.levels[p.owner]=[set(m)]
    for x,z in m:
        for y in range(1,9):p.put(x,y,z,AIR)
    p.floor(m,0);p.walls(m,0,'minecraft:brown_terracotta')
    p.roof((-1,-1,4,depth),4,(0,1,2,2,1,0),family='spruce'if kind=='lanterns'else'dark_oak',hip_south=kind=='fittings',annex=True)
    if kind=='fittings':p.put(1,5,depth,'mcwroofs:dark_oak_top_roof',part='switched_0',role='actual raised dark-oak endcap on the stepped half-hip')
    p.reserve('Real compact workroom passage',[(2,1,z)for z in range(1,depth-1)]+[(3,1,3)])
    for z in(2,depth-2):coast.ties(p,0,3,4,z,'real compact workshop ceiling cross-tie')
    joists(p,1,2,(2,))
    window(p,0,1,1,'west',width=2,height=2)
    p.put(1,1,1,'minecraft:crafting_table'if kind=='lanterns'else'minecraft:stonecutter',**({}if kind=='lanterns'else{'facing':'east'}),role='real lantern assembly bench'if kind=='lanterns'else'real small fitting and sharpening station')
    p.put(1,1,2,'farmersdelight:dark_oak_cabinet',facing='east',open=False,role='new native-default trade-tool cupboard')
    p.counter(1,1,3,'east',role='actual small order and repair counter')
    p.put(1,2,3,'handcrafted:wood_cup',facing='east',pieces=3,waterlogged=False,role='real ordinary vessels on the fixed counter')
    p.put(1,1,depth-2,'minecraft:barrel',facing='up',open=False,role='ordinary new native-default finished-order stock')
    p.put(1,2,depth-2,POTS[0],role='contained pale flower on the real full stock barrel')
    coast.wall_shelf(p,1,2,depth-3,'east','backed repair and order accounts')
    if depth==8:p.put(1,1,4,'handcrafted:dark_oak_chair',facing='east',color='brown',waterlogged=False,role='small actual waiting and fitting seat')
    light(p,2,3,3,'small supported practical trade-counter lantern')
    for z in(2,4):
        for y in(1,2,3):p.put(3,y,z,'dawnoftimebuilder:charred_spruce_timber_frame_pillar',axis='y',role='rooted recessed-door cheek inside this low workshop')
        p.put(4,3,z,'mythrais:curved_corbel_dark_oak',facing='east',shape=0,role='small high street-side door bracket')
    for z in(2,3,4):p.beam(3,4,z,'z',wood='dark_oak',role='actual recessed workshop lintel')
    for y,half in((1,'lower'),(2,'upper')):
        p.put(3,y,3,AIR)
        p.put(2,y,3,'mcwdoors:dark_oak_cottage_door',facing='west',half=half,hinge='left',open=False,powered=False)
    p.entries.append({'owner':p.owner,'door':[2,1,3],'outward':'east','outside_step':[3,0,3]})
    p.sign(4,3,depth-2,'east',['Compact workroom',kind.title()+' • Repairs']);p.put(3,3,depth-2,'minecraft:dark_oak_planks')
    p.room('Front '+kind+' assembly scene',0,(2,1,1),'The literal small dry building contains a real native work station, actual tool cupboard and fitted order counter; this is a workroom, not an invented home.')
    p.room('Rear repair and collection scene',0,(2,1,depth-3),'The same useful low workroom has backed order accounts, native-default finished stock, a contained flower and warm task lighting; no courtyard is counted as a building.')
    canonical_joins(p);return p


EXTRA={
 'spit-short-fittings':lambda r:short_loft(r,depth=7,trade='fittings'),
 'spit-short-salt':lambda r:short_loft(r,depth=8,trade='salt'),
 'spit-short-cloth':lambda r:short_loft(r,depth=8,trade='cloth',oriel=False),
 'spit-short-chart':lambda r:short_loft(r,depth=7,trade='charts',oriel=False),
 'spit-low-cordage':low_cordage_shop,
 'spit-recessed-mending':lambda r:recessed_original(r,'mugs-mending'),
 'spit-recessed-fittings':lambda r:fill.rich_workscene(recessed_original(r,'lost-tide'),'lost-tide'),
 'spit-lantern-annex':lambda r:compact_workshop(r,depth=7,kind='lanterns'),
 'spit-fitting-annex':lambda r:compact_workshop(r,depth=8,kind='fittings'),
}


@contextmanager
def source_recipes():
    with coast.source_recipes(),previous.source_recipes():
        if set(EXTRA)&set(RECIPES):raise UserError('Keep every frozen original recipe key')
        RECIPES.update(EXTRA)
        try:yield
        finally:
            for name in EXTRA:RECIPES.pop(name,None)


BATCHES={
 'western-spit-ten':{
  'buildings':(
   {'recipe':'kettle-bend','turn':1,'name':'The Crooked Kettle','trade':'Tea • Supper • Home','origin':(1017,63,-1313)},
   {'recipe':'spit-recessed-fittings','turn':3,'name':'Saltwind Fittings','trade':'Boat Fittings • Repairs','origin':(991,63,-1263)},
   {'recipe':'thimble-salt','turn':2,'name':'The Red Thread','trade':'Sea Coats • Stitching','origin':(1025,63,-1267)},
   {'recipe':'coast-kettle-loft','turn':0,'name':'Low Water Kitchen','trade':'Warm Food • Home','origin':(1034,63,-1269)},
   {'recipe':'spit-short-fittings','turn':2,'name':'The Small Ferrule','trade':'Fasteners • Fittings','origin':(1045,63,-1241)},
   {'recipe':'lost-tide','turn':1,'name':'Bent Spar Repairs','trade':'Spars • Joinery • Home','origin':(1069,63,-1248)},
   {'recipe':'spit-recessed-mending','turn':3,'name':'The Seated Needle','trade':'Mending • Tea • Home','origin':(1082,63,-1281)},
   {'recipe':'spit-short-cloth','turn':3,'name':'The Folded Pennant','trade':'Pennants • Cloth • Home','origin':(1091,63,-1246)},
   {'recipe':'spit-lantern-annex','turn':3,'name':'The Oilglass Bench','trade':'Lanterns • Repairs','origin':(1054,63,-1230)},
   {'recipe':'spit-fitting-annex','turn':3,'name':'Sparrow-Key Fittings','trade':'Small Fittings • Repairs','origin':(1063,63,-1230)},
  ),
  'links':(
   ('Crooked Kettle western public threshold',((1015,-1309),(1015,-1309))),
   ('Saltwind east-facing quay threshold',((1002,-1262),(1002,-1262))),
   ('Red Thread eastern shop threshold',((1031,-1266),(1031,-1266))),
   ('Low Water Kitchen western approach',((1032,-1269),(1032,-1269))),
   ('Small Ferrule eastern fitting-shop approach',((1050,-1236),(1050,-1236))),
   ('Bent Spar western service threshold',((1067,-1245),(1067,-1245))),
   ('Seated Needle recessed western threshold',((1080,-1277),(1080,-1277))),
   ('Folded Pennant small southern threshold',((1091,-1241),(1091,-1241))),
   ('Two low workshops share a real two-wide working alley',((1056,-1232),(1065,-1232))),
  ),
  'design':'Ten individually fitted occupied masses on the remaining literal dry western spit: unequal tall homes, L-shaped repair/tea wings, long low fitting shops, a narrow little loft and two distinct one-storey working annexes. Actual small thresholds and one two-wide shared alley serve buildings rather than substitute paving for city footprint. All eight earlier queued construction deltas, retained stocks, accepted town and flight remain protected.',
  'street_views':(
   ('Northern kettle house from its real western threshold',(1015.5,64,-1308.5),(1021,68,-1308)),
   ('Saltwind low fitting house from the eastern quay',(1003.5,64,-1261.5),(997,67,-1260)),
   ('Red Thread actual inland façade',(1032.5,64,-1265.5),(1027,68,-1263)),
   ('Low kitchen from the western work lane',(1032.5,64,-1268.5),(1036,67,-1265)),
   ('Small Ferrule from the eastern threshold',(1051.5,64,-1235.5),(1047,67,-1238)),
   ('Bent Spar repair wing from the real service alley',(1067.5,64,-1244.5),(1074,67,-1244)),
   ('Seated Needle western recessed frontage',(1080.5,64,-1276.5),(1086,68,-1277)),
   ('Folded Pennant southern face',(1091.5,64,-1240.5),(1095,67,-1244)),
   ('Low working annexes from their actual shared alley',(1061.5,64,-1231.5),(1062,66,-1228)),
  ),
 },
}


def current_field(home,checkpoint_id,checkpoint_sha,field_path,field_sha):
    """Subtract construction targets; never turn verification context into land."""
    subset,_=coast.derived_field(home,checkpoint_id,checkpoint_sha,field_path,field_sha)
    data=read_json(subset)
    prior,refs,buildings=previous.construction_targets(home,coast.FIVE+QUEUED)
    blocked={(x,z)for x,y,z in prior if 63<=y<=85}
    data['eligible_columns_READONLY']=[r for r in data['eligible_columns_READONLY']if 968<=r[0]<=1099 and tuple(r[:2])not in blocked]
    # Low outdoor walking may pass below a high existing bracket, but never
    # through a house interior, retained solid, inventory or flight envelope.
    raw=read_json(field_path)
    mains={tuple(q)for b in buildings for q in b['main_columns_xz']}
    walking=[]
    for row in raw['two_high_walk_columns_READONLY']:
        x,z=row[:2]
        if not 968<=x<=1099 or(x,z)in mains:continue
        if any((x,y,z)in prior and(prior[x,y,z]!=AIR or row[y-61]!=AIR)for y in(64,65)):continue
        if(x,63,z)in prior and prior[x,63,z]!=row[2]:continue
        walking.append(row)
    data['two_high_walk_columns_READONLY']=walking
    for b in buildings:data['retained_source_main_footprints']['placed-or-queued '+b['name']]=b['main_columns_xz']
    data.update(western_spit_source_sha256=digest(Path(__file__)),exact_earlier_construction_sources=refs,
       eligible_columns=len(data['eligible_columns_READONLY']),added_buildable_authority_columns=0,
       walking_references_only='Literal saved walking rows below high brackets confer no building or replacement authority')
    return data,prior,refs


def complete_native_joins(registry,states,keep):
    """Independently derive pinned native parts from the full physical mask."""
    from types import SimpleNamespace
    model=SimpleNamespace(registry=registry,blocks={**keep,**states})
    changes=canonical_joins(model)
    new={q:model.blocks[q]for q in states}
    adjacent={(x+dx,y+dy,z+dz)for x,y,z in states for dx,dy,dz in((1,0,0),(-1,0,0),(0,0,1),(0,0,-1),(0,1,0),(0,-1,0))}
    old=[r for r in changes if tuple(r['position'])in keep and tuple(r['position'])in adjacent and tuple(r['position'])not in states]
    return new,old


def public_floor_write(value,observed,source_expected,axes):
    """None means retain/read-only, never newly owned current paving."""
    if value is None or'waterlogged=true'in value or key(value)in('minecraft:water','minecraft:lava'):
        raise UserError('No public floor replacement over water or unknown')
    if source_expected is not None:
        if source_expected!=value:raise UserError('Retained source floor changed; do not replay or replace it')
        if key(value)in VOIDS:raise UserError('An existing AIR reservation is not a real walking floor')
        return None
    if key(value)not in GROUND|VOIDS|SOFT|NORTH_SOFT:
        if value!=observed:raise UserError('Observed public paver changed')
        return None
    return'chipped:small_stone_bricks'if len(axes)>1 else'minecraft:andesite'if'x'in axes else'minecraft:cobblestone'


def prepare(home,checkpoint_id,checkpoint_sha,field_path,field_sha,batch='western-spit-ten'):
    reserve=guard(8*MIB,96*MIB)
    budgets=[reader_budget()]  # A refusal stops before readers or output allocation.
    home=fill.private_home(home);receipt=fill.stopped(home,checkpoint_id,checkpoint_sha)
    field_path=Path(field_path).resolve()
    if not field_path.is_relative_to(home/'staging')or digest(field_path)!=field_sha or field_path.stat().st_size>32*MIB:
        raise UserError('Exact bounded current stopped-save field required')
    source_field=read_json(field_path)
    if(source_field.get('checkpoint_id'),source_field.get('checkpoint_sha256'))!=(checkpoint_id,checkpoint_sha):
        raise UserError('A changed save requires fresh fields and native before proofs, not a hash rebind')
    if batch not in BATCHES:raise UserError('Exact finite individually composed spit batch required')
    out=home/'staging'/('tortuga-western-spit-'+str(time.time_ns()));out.mkdir()
    terrain=None
    try:
        field,prior,prior_refs=current_field(home,checkpoint_id,checkpoint_sha,field_path,field_sha)
        registry=read_json(home/'dashboard/settlement/registry.json')
        with source_recipes():states,tags,buildings,mains=fill.modeled(registry,BATCHES[batch])
        if not 1<=len(buildings)<=12 or len(states)+2048>12000:raise UserError('Finite12K native-target batch cap exceeded')
        free={tuple(r[:2])for r in field['eligible_columns_READONLY']}
        if not mains<=free:raise UserError('No main mass in saved water, existing source, unsupported soil or unknown: '+str(sorted(mains-free)[:10]))
        keep,forest,heritage,_,_,refs=fill.retained_context(home,registry);keep.update(prior)
        overlap=[q for q in states if q in keep or(q[0],q[2])in heritage or not 968<=q[0]<=1099]
        if overlap or mains&forest:raise UserError('Keep every retained/queued construction target, flight and habitat: '+str(overlap[:8]))
        walking={tuple(r[:2]):r[2:]for r in field['two_high_walk_columns_READONLY']}
        lane,routes=fill.route_geometry(states,mains,walking,BATCHES[batch])
        zinc=verify_zinc_factory(home);terrain=NorthTerrain(home,receipt,registry)
        before={};supports={};clearance={};retained_floors={};began=time.monotonic()
        for x,z in sorted(mains|set(lane)):
            col=terrain.column(x,z)
            if(x,z)in mains and(col['kind']!='dry'or col['surface_y']not in(62,63)):
                raise UserError('A complete main floor must be literal low dry land: '+str((x,z,col)))
            mount=qualified_mount(terrain.state,x,z,zinc)
            if not mount['stable']:raise UserError('Stable complete native foundation required: '+str((x,z,mount)))
            for xx,yy,zz,value in mount['stack']:
                if(xx,yy,zz)in terrain.entities:raise UserError('No existing BE may become a new foundation')
                supports[xx,yy,zz]=value
            if(x,z)in lane:
                q=x,63,z;value=terrain.state(*q)
                if q in terrain.entities or value is None or 'waterlogged=true'in value:raise UserError('Retain current water/BE/unknown at a public threshold')
                new_floor=public_floor_write(value,walking[x,z][0],keep.get(q),lane[x,z])
                if new_floor is None:retained_floors[q]=value
                else:states[q]=new_floor
        for i,q in enumerate(sorted(states,key=lambda q:(q[0]//16,q[2]//16,q[1],q[0],q[2]))):
            current=terrain.state(*q)
            if q in keep or q in terrain.entities or current is None or key(current)not in GROUND|VOIDS|SOFT|NORTH_SOFT or'waterlogged=true'in current:
                raise UserError('Keep actual saved objects, water, BEs, canopy and unknown: '+str((q,current)))
            before[q]=current
            if i%256==0:budgets.append(reader_budget())
            if time.monotonic()-began>120:raise UserError('Finite120s stopped-save reader bound exceeded')
        for x,z in lane:
            floor=x,63,z
            if floor in retained_floors:before[floor]=retained_floors[floor]
            for y in(64,65):
                q=x,y,z;current=terrain.state(*q)
                if q in terrain.entities or current is None or key(current)not in VOIDS|SOFT|NORTH_SOFT or'waterlogged=true'in current:
                    raise UserError('A real two-wide public body is obstructed: '+str((q,current)))
                if q in keep:
                    if keep[q]!=AIR or current!=AIR:raise UserError('No clearing or furniture replacement in a retained route')
                elif key(current)not in VOIDS:states[q]=AIR
                before[q]=current;clearance[q]=AIR
        saved=terrain.snapshot.sources;terrain.close();terrain=None
        states,old_join_expectations=complete_native_joins(registry,states,keep)
        outdoor=fill.lane_materials(states,lane,batch+' short real public approaches')
        if len(states)>12000:raise UserError('Retain proposal but refuse native admission above12K targets')
        full={**states,**supports,**clearance,**retained_floors}
        documents={
          'cluster-PROPOSAL.json':native_payload(registry,states,checkpoint_sha,'TORTUGA WESTERN SPIT — ten occupied individual masses',tags=tags),
          'before-VERIFY-ONLY.json':native_payload(registry,before,checkpoint_sha,'VERIFY ONLY — exact saved targets and retained real public approaches'),
          'stable-supports-VERIFY-ONLY.json':native_payload(registry,{**supports,**retained_floors},checkpoint_sha,'VERIFY ONLY — complete stable native substrate and unchanged public pavers'),
          'complete-after-VERIFY-ONLY.json':native_payload(registry,full,checkpoint_sha,'VERIFY ONLY — all new occupied geometry, actual short routes and retained foundations',tags=tags),
          'normal-joins-SETTLE-ONLY.json':native_payload(registry,{q:s for q,s in states.items()if key(s)not in VOIDS},checkpoint_sha,'NORMAL JOINS ONLY — bounded actual neighbor shapes; no old furniture/NBT replay'),
        }
        raw={}
        for name,doc in documents.items():
            if name!='cluster-PROPOSAL.json':doc.update(construction_forbidden=True,verification_only=True)
            raw[name]=(json.dumps(doc,separators=(',',':'))+'\n').encode()
        manifest={'format':'awft-tortuga-western-spit:1','batch':batch,'checkpoint_id':checkpoint_id,'checkpoint_sha256':checkpoint_sha,
          'source_sha256':digest(Path(__file__)),'field_source':str(field_path.relative_to(home)),'field_sha256':field_sha,
          'definition':BATCHES[batch],'buildings':buildings,'rooms':sum(len(b['rooms'])for b in buildings),
          'main_columns':len(mains),'lane_columns':len(lane),'targets':len(states),'native_target_cap':12000,'routes':routes,
          'retained_public_floor_cells':len(retained_floors),'public_floor_replacement_writes':0,'existing_BE_targets':0,
          'read_only_neighbor_part_derivations_NOT_PLACEMENT_AUTHORITY':old_join_expectations,
          'approved_west_concept':{'relative':coast.APPROVED[0],'sha256':coast.APPROVED[1]},'retained_construction_sources':prior_refs,
          'other_preservation_sources':refs,'source_dependency_sha256':{p.name:digest(p)for p in(Path(fill.__file__),Path(coast.__file__),Path(previous.__file__))},
          'raw_saved_sources':saved,'pinned_zinc_factory':zinc,'outdoor_material_rule':outdoor,'reserve_guard':reserve,
          'reader_peak_RSS_bytes':max(b['owned_reader_rss_bytes']for b in budgets),'native_actions':0,'world_writes':0,
          'native_cameras':[v for b in buildings for v in b['scene_views']]+[{'name':n,'feet':list(q),'look_at':list(t),'source_only_native_walk_render_pending':True}for n,q,t in BATCHES[batch]['street_views']],
          'status':'SOURCE + EXACT STOPPED PREIMAGE; fresh Native admission, map, placement/normal-settle/full verification and actual artist review pending',
          'limits':['Ten source masses do not prove entire western coverage','Low workshops have two activity scenes on one floor, not fictitious separate homes','Observed public pavers are verification context only, never construction ownership','Every changed checkpoint requires fresh field/preimage; no silent rebinding','No old stock, container Items, owner, NPC or human data is copied or moved']}
        field_bytes=(json.dumps(field,separators=(',',':'))+'\n').encode()
        raw['field-READONLY.json']=field_bytes
        map_bytes=coast.batch_map(manifest,field)
        if len(map_bytes)>MIB:raise UserError('Finite1MiB source map bound exceeded')
        raw['batch-map-PLAN-ONLY.svg']=map_bytes
        manifest['files']={name:{'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)}for name,data in raw.items()}
        raw['manifest.json']=(json.dumps(manifest,separators=(',',':'))+'\n').encode()
        if sum(map(len,raw.values()))>64*MIB:raise UserError('Finite64MiB final bundle cap exceeded')
        for name,data in raw.items():(out/name).open('xb').write(data)
        return {'folder':str(out),'manifest_sha256':digest(out/'manifest.json'),'buildings':len(buildings),'scenes':manifest['rooms'],
          'main_columns':len(mains),'lane_columns':len(lane),'targets':len(states),'files':manifest['files'],'native_actions':0}
    except Exception as exc:
        (out/'refusal.json').open('x',encoding='utf-8').write(json.dumps({'source_sha256':digest(Path(__file__)),'checkpoint_id':checkpoint_id,'checkpoint_sha256':checkpoint_sha,'reason':type(exc).__name__+': '+str(exc),'native_actions':0,'world_writes':0,'request_emitted':False})+'\n')
        raise UserError(str(exc)+'; preserved '+str(out))from exc
    finally:
        if terrain is not None:terrain.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--home',type=Path,required=True);parser.add_argument('--checkpoint-id',required=True);parser.add_argument('--checkpoint-sha',required=True)
    parser.add_argument('--field',type=Path,required=True);parser.add_argument('--field-sha',required=True);parser.add_argument('--batch',choices=BATCHES,default='western-spit-ten')
    args=parser.parse_args()
    print(json.dumps(prepare(args.home,args.checkpoint_id,args.checkpoint_sha,args.field,args.field_sha,args.batch),indent=2))
