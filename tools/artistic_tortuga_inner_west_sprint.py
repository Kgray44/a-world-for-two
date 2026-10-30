"""Original occupied inner-West Tortuga frontages, source-only city sprint.

No shared recipe file, current world, inventory, controller or runtime is edited.
Actual saved dry lots and the approved whole-city concept constrain every mass.
"""
from __future__ import annotations
from collections import Counter,deque
from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path
import argparse,hashlib,json,math,time
from control_room.common import UserError,digest,read_json,utcnow
from tools import artistic_tortuga_fill as fill
from tools import artistic_tortuga_coast_batches as coast
from tools import artistic_tortuga_west_approved_blocks as approved
from tools.artistic_tortuga_frontages import (
    RECIPES,AIR,POTS,base,rect,door,window,joists,light,upper_home,
    routes,bay_south,side_bay,check,
)
from tools.artistic_west_r2_frontage import Frontage,canonical_joins,key,VEC
from tools.artistic_tortuga_variants import variant_of
from tools.artistic_bridge_refinement import flatten
from tools.artistic_zipline_catenary import reader_budget
from tools.playtest import guard

MIB=1024**2
CHECKPOINT='20261028T180051Z-30624d'
CHECKPOINT_SHA='3cb269d28ae1ccbac882a44d35277d82c83582274abad2f1cf3b41566d3e9b24'
FIELD='staging/tortuga-current-field-1793210749482454300/field-READONLY.json'
FIELD_SHA='0956144ba0891de70f284cea4497539f96d06738db5fcecf07a352f5e7ed16fa'
WEST_FIVE=(
 ('staging/tortuga-fill-net-needle-crook-1793212893524565700/manifest.json','345b32431c44cf7df6bb37f03b933dd9c1fd7670dd4e9f70243ec56c99d2ce47'),
 ('staging/tortuga-fill-moon-tackle-returns-1793212899675804500/manifest.json','5e5eb07cf443dc9851875f7bcc0cd8aee849d61dadf3152f76bbec2966ce5486'),
 ('staging/tortuga-fill-chart-window-loft-1793212905634658900/manifest.json','accfeb92b096f3d87ae939f41014a5870d2489f3377c150ac4a150f05ccf99a1'),
)


def needle_slot(registry):
    """Four-wide, real stair/bed loft above a deep repair room:35m², no box padding."""
    m=rect(0,0,3,7);u=set(m)
    p=base(registry,'The Narrow Needle',m,u,panel='minecraft:brown_terracotta',up='minecraft:gray_terracotta')
    p.roof((-1,-1,4,8),8,(0,1,2,2,1,0),family='dark_oak',hip_south=True)
    p.reserve('Narrow repair counter passage',[(1,1,z)for z in range(2,8)])
    p.reserve('Narrow loft landing and bed approach',[(1,5,z)for z in(3,4,5)])
    p.stair_flight(2,5,0)
    window(p,0,1,2,'west',width=2);window(p,3,1,5,'east',width=1)
    window(p,0,5,3,'west',width=2);window(p,3,5,5,'east',width=1)
    joists(p,1,2,(2,6));joists(p,1,2,(2,6),4)
    p.counter(2,1,1,'west',role='tiny real clothing and rope repair counter')
    p.put(2,2,1,'farmersdelight:cutting_board',facing='west',waterlogged=False,role='actual small repair and cutting surface')
    p.put(2,1,6,'minecraft:smoker',facing='west',lit=False,role='real shared household cooking hearth')
    p.put(2,2,6,'handcrafted:dark_oak_shelf',facing='west',shape='single',type=3,role='small real backed vessel shelf below the ceiling joist')
    p.supports.append({'detail':[2,2,6],'support':[3,2,6],'role':'actual narrow-room wall supports the household shelf'})
    p.bed(1,5,6,face='east')
    p.put(1,5,2,'handcrafted:dark_oak_desk',facing='north',color='brown',waterlogged=False,role='real narrow-loft order and reading desk')
    p.put(1,6,2,'handcrafted:stackable_book',facing='north',books=3,seed=5,role='household orders and personal books')
    p.put(1,5,1,'handcrafted:dark_oak_chair',facing='south',color='brown',waterlogged=False,role='actual chair facing the little reading desk')
    light(p,1,3,3,'small grounded repair-room task lantern');light(p,1,7,4,'little loft lantern')
    door(p,1,7,'south');p.sign(-1,3,5,'west',['Narrow Needle','Repairs • Home']);p.put(0,3,5,'minecraft:dark_oak_planks')
    p.room('Narrow repair and supper room',0,(1,1,4),'Actual repair/cutting surface, backed vessels and a real rear cooking hearth beside a continuous narrow passage.')
    p.room('Small real sleeping and reading loft',4,(1,5,4),'An ordinary stair reaches a real transverse bed, reading desk, facing chair and two deep fancy casements.')
    canonical_joins(p);return p


def long_lodging(registry):
    m=rect(0,0,4,12)-{(0,0),(4,0)};u=rect(0,1,4,11)
    p=base(registry,'The Barnacle Cup',m,u,panel='minecraft:brown_terracotta',up='minecraft:gray_terracotta')
    p.roof((-1,0,5,13),8,(0,1,2,3,2,1,0),family='spruce')
    p.roof((-1,-1,5,2),4,(0,1,2,3,2,1,0),family='dark_oak',annex=True)
    p.reserve('Long crew-lodging common passage',[(2,1,z)for z in range(1,13)])
    p.reserve('Loft sleeping approach',[(2,5,z)for z in range(4,9)])
    p.stair_flight(3,9,0)
    window(p,0,1,3,'west',width=2);window(p,4,1,3,'east',width=2)
    window(p,0,1,9,'west',width=2);window(p,4,5,3,'east',width=2);window(p,0,5,7,'west',width=2)
    joists(p,1,3,(3,7,11));joists(p,1,3,(3,7,10),4)
    for z in(3,4):p.counter(1,1,z,'east',role='crew supper and parcel service counter')
    p.put(1,2,3,'handcrafted:terracotta_bowl',facing='east',pieces=3,waterlogged=False,role='real small serving vessels')
    p.put(1,1,2,'minecraft:barrel',facing='up',open=False,role='new native-default crew supplies')
    p.put(3,1,2,'minecraft:crafting_table',role='working sea-bag and clothes repair bench')
    p.put(1,1,10,'minecraft:smoker',facing='east',lit=False,role='real rear household cooking hearth')
    p.put(3,1,10,'minecraft:water_cauldron',level=3,role='contained washing water beside the rear supper nook')
    p.put(1,1,8,'handcrafted:dark_oak_bench',facing='east',shape='single',color='brown',waterlogged=False,role='crew supper and mending bench')
    coast.wall_shelf(p,1,2,6,'east','backed voyage and household accounts')
    light(p,2,3,4,'small front service lantern');light(p,2,3,10,'rear supper lantern')
    upper_home(p,bed=(1,6),desk=(1,10),chair=(2,10),chair_face='west',hearth=(1,3),pantry=(2,3),table=(1,8),standing=(2,7),title='Crew lodging’s tucked sleeping loft')
    door(p,2,12,'south');p.sign(5,3,10,'east',['Barnacle Cup','Supper • Lodging']);p.put(4,3,10,'minecraft:dark_oak_planks')
    p.room('Long crew service and repair room',0,(2,1,5),'Real supper counter, vessels, stock and repair bench under a low framed roof.')
    p.room('Rear wash and supper nook',0,(2,1,10),'A real contained wash vessel, cookery, seating and household shelf occupy the rear of the narrow lodging.')
    canonical_joins(p);return p


def corner_cooper(registry):
    m=(rect(0,0,5,9)|rect(5,0,8,4))-{(0,0),(8,0)};u=rect(0,1,5,8)
    p=base(registry,'The Crooked Stave',m,u,panel='minecraft:gray_terracotta',up='minecraft:brown_terracotta')
    p.roof((-1,0,6,10),8,(0,1,2,3,3,2,1,0),family='dark_oak')
    p.roof((5,-1,9,5),4,(0,1,2,1,0),family='spruce',annex=True)
    p.reserve('Cooper workroom and low side wing',[(3,1,z)for z in range(2,9)]+[(x,1,3)for x in range(3,9)])
    p.reserve('Cooper upper-home approach',[(3,5,z)for z in range(3,8)])
    p.stair_flight(4,7,0)
    window(p,0,1,3,'west',width=2);window(p,8,1,1,'east',width=2);window(p,0,5,3,'west',width=2)
    bay_south(p,1,9);joists(p,1,4,(3,7));joists(p,1,4,(3,7),4)
    p.put(1,1,2,'minecraft:stonecutter',facing='east',role='real precision fitting station for staves and hoops')
    p.put(2,1,2,'minecraft:crafting_table',role='actual stave and fastener assembly bench')
    for z in(4,5):p.counter(1,1,z,'east',role='long stave fitting and repair bench')
    p.put(1,2,4,'farmersdelight:cutting_board',facing='east',waterlogged=False,role='real repair surface')
    p.put(1,1,7,'minecraft:barrel',facing='up',open=False,role='new native-default small cooper stock')
    p.put(7,1,1,'minecraft:barrel',facing='up',open=False,role='new native-default finishing-room barrel')
    p.put(7,1,2,'minecraft:water_cauldron',level=3,role='contained cask-rinsing water')
    p.put(6,1,1,'handcrafted:dark_oak_bench',facing='south',shape='single',color='brown',waterlogged=False,role='small low-wing repair and waiting seat')
    coast.wall_shelf(p,1,2,6,'east','backed cask measures and order accounts')
    light(p,3,3,4,'actual cooper work lantern');light(p,6,3,3,'little side-wing finishing light')
    upper_home(p,bed=(1,5),desk=(1,7),chair=(2,7),chair_face='west',hearth=(1,3),pantry=(2,3),table=(2,5),standing=(3,5),title='Cooper’s projecting-window home')
    door(p,8,3,'east');p.sign(9,3,4,'east',['Crooked Stave','Casks • Hoops']);p.put(8,3,4,'minecraft:dark_oak_planks')
    p.room('Stave and fitting workshop',0,(3,1,5),'Real precision tools, assembly, long work surface and measures beneath a framed occupied home.')
    p.room('Low cask finishing wing',0,(6,1,3),'Contained rinse water, cask stock, waiting seat and warm light fit a genuinely lower side wing.')
    canonical_joins(p);return p


def paper_rook(registry):
    m=rect(0,0,8,7)-{(0,0),(8,7)};u=rect(0,0,6,6)
    p=base(registry,'The Paper Rook',m,u,panel='minecraft:brown_terracotta',up='minecraft:gray_terracotta')
    p.roof((-1,-1,7,7),8,(0,1,2,3,4,3,2,1,0),family='spruce')
    p.roof((6,-1,9,8),4,(0,1,1,0),family='dark_oak',annex=True)
    p.reserve('Bookbinder’s work and side-entry passage',[(4,1,z)for z in range(2,7)]+
              [(5,1,6),(6,1,6),(6,1,5),(7,1,5),(8,1,5)])
    p.reserve('Bookbinder’s upper landing',[(4,5,z)for z in range(2,6)])
    p.stair_flight(5,5,0)
    window(p,0,1,2,'west',width=2,height=3);window(p,8,1,1,'east',width=2)
    window(p,1,5,0,'north',width=2);window(p,0,5,3,'west',width=2)
    joists(p,1,5,(2,5));joists(p,1,5,(2,5),4)
    p.put(1,1,2,'minecraft:lectern',facing='east',has_book=False,powered=False,role='actual empty public reading lectern')
    p.put(2,1,2,'minecraft:crafting_table',role='real cover-binding and paper assembly bench')
    for z in(3,4):p.counter(1,1,z,'east',role='bookbinding and map-cover work counter')
    p.put(1,2,4,'handcrafted:stackable_book',facing='east',books=3,seed=3,role='real book models awaiting binding')
    coast.wall_shelf(p,1,2,6,'east','backed paper patterns and bookbinding accounts')
    p.put(2,1,6,'handcrafted:dark_oak_drawer',facing='north',shape='single',type=2,role='new native-default paper and binding drawer')
    p.put(2,2,6,POTS[4],role='contained fern on the actual drawer top')
    p.put(7,1,2,'minecraft:cartography_table',role='separate actual chart-cover and map fitting station')
    light(p,3,3,4,'bookbinding task light');light(p,7,3,4,'small chart-work side light')
    upper_home(p,bed=(1,3),desk=(1,5),chair=(2,5),chair_face='west',hearth=(4,1),pantry=(3,1),table=(3,3),standing=(4,4),title='Bookbinder’s compact glazed home')
    door(p,8,5,'east');p.sign(9,3,3,'east',['Paper Rook','Binding • Charts']);p.put(8,3,3,'minecraft:dark_oak_planks')
    p.room('Paper and bookbinding workshop',0,(4,1,4),'Books, actual reading and binding stations, backed patterns and a separate low map-fitting wing.')
    canonical_joins(p);return p


def short_watchmaker(registry):
    """A 4x6 occupied watchmaker, a real narrow stair and transverse bed."""
    m=rect(0,0,3,5)
    p=base(registry,'The North Knot',m,m,panel='minecraft:gray_terracotta',up='minecraft:brown_terracotta')
    p.roof((-1,-1,4,6),8,(0,1,2,2,1,0),family='spruce')
    p.reserve('Small watchmaker ground approach',[(1,1,z)for z in(2,3,4,5)])
    p.reserve('Small watchmaker sleeping approach',[(1,5,3),(2,5,1)])
    p.stair_flight(2,5,0)
    window(p,0,1,2,'west',width=2);window(p,3,5,2,'east',width=2)
    window(p,1,5,0,'north',width=1)
    joists(p,1,2,(2,4));joists(p,1,2,(2,4),4)
    p.put(2,1,1,'minecraft:crafting_table',role='actual small clock and rope-fitting workbench')
    p.put(2,2,1,'supplementaries:hourglass',facing='up',light_level=0,waterlogged=False,role='real small model used to time the watch')
    p.put(1,1,1,'minecraft:barrel',facing='up',open=False,role='new native-default small spare fittings stock')
    p.bed(1,5,4,face='east')
    p.put(1,5,2,'handcrafted:dark_oak_desk',facing='north',color='brown',waterlogged=False,role='watchmaker household writing and order desk')
    p.put(1,6,2,'handcrafted:stackable_book',facing='north',books=3,seed=11,role='real household and watch-order books')
    p.put(1,5,1,'handcrafted:dark_oak_chair',facing='south',color='brown',waterlogged=False,role='actual chair facing the writing desk')
    light(p,1,3,3,'little watch-fitting light');light(p,2,7,3,'small sleeping-loft light')
    door(p,1,5,'south');p.sign(-1,3,4,'west',['North Knot','Fittings • Watches']);p.put(0,3,4,'minecraft:dark_oak_planks')
    p.room('Small real watch fitting and stock room',0,(1,1,3),'A real precision repair bench, hourglass and native-default stock occupy the glazed lower room.')
    p.room('Watchmaker’s little sleeping study',4,(1,5,3),'Ordinary stairs reach a real transverse bed, desk, books, facing chair and fancy east casement.')
    canonical_joins(p);return p


def skinny_chart_shop(registry):
    """A genuine one-storey 3x8 chart shop, two usable scenes, no fake loft."""
    m=rect(0,0,2,7)
    p=Frontage(registry,(0,63,0));p.owner='The Chart Sliver';p.main[p.owner]=set(m);p.levels[p.owner]=[set(m)]
    for x,z in m:
        for y in range(1,8):p.put(x,y,z,AIR)
    p.floor(m,0);p.walls(m,0,'minecraft:brown_terracotta')
    p.roof((-1,-1,3,8),4,(0,1,2,1,0),family='dark_oak',hip_south=True)
    p.reserve('Chart sliver public visiting aisle',[(1,1,z)for z in range(2,7)])
    window(p,0,1,2,'west',width=2);window(p,2,1,4,'east',width=2)
    joists(p,1,1,(2,5))
    p.put(1,1,1,'minecraft:cartography_table',role='real chart and coast-note fitting station in the front work bay')
    p.put(1,1,6,'minecraft:barrel',facing='up',open=False,role='new native-default rolled chart and paper storage')
    p.put(1,2,6,'supplementaries:globe',facing='north',role='actual small navigation globe on the rear stock top')
    # Keep the literal public route two high; the back station is approached
    # from z5, not by walking through its barrel.
    p.routes[-1]['positions']=[q for q in p.routes[-1]['positions']if q[2]!=6]
    light(p,1,3,3,'small front chart work light')
    door(p,1,7,'south');p.sign(-1,3,5,'west',['Chart Sliver','Notes • Instruments']);p.put(0,3,5,'minecraft:dark_oak_planks')
    p.room('Front chart fitting alcove',0,(1,1,2),'A real cartography station faces a long fancy casement and close warm task light.')
    p.room('Rear globe and chart-stock nook',0,(1,1,5),'The same genuine narrow workshop has a separately approached globe and native-default chart stock.')
    canonical_joins(p);return p


def spindle_return(registry):
    """Narrow cloth home with an occupied projecting end bay and a low apron."""
    m=rect(0,0,3,7)
    p=base(registry,'Sable Spindle',m,m,panel='minecraft:gray_terracotta',up='minecraft:brown_terracotta')
    p.roof((-1,-1,4,8),8,(0,1,2,3,2,0),family='dark_oak')
    p.reserve('Sable compact loom and mending passage',[(1,1,z)for z in range(2,8)])
    p.reserve('Sable loft doorway and bed approach',[(1,5,z)for z in(3,4,5)])
    p.stair_flight(2,5,0)
    window(p,0,1,2,'west',width=2,height=2);window(p,3,1,5,'east',width=1)
    window(p,0,5,3,'west',width=2);window(p,1,5,7,'south',width=1)
    joists(p,1,2,(2,6));joists(p,1,2,(2,6),4)
    p.put(2,1,1,'minecraft:loom',facing='west',role='real narrow sail cloth and pennant loom')
    p.put(2,1,6,'farmersdelight:dark_oak_cabinet',facing='west',open=False,role='new native-default needleworker tool and cloth cabinet')
    p.put(2,2,6,'handcrafted:terracotta_bowl',facing='west',pieces=3,waterlogged=False,role='real small sorting vessels on the cloth cabinet')
    p.bed(1,5,6,face='east')
    p.put(1,5,2,'handcrafted:dark_oak_desk',facing='north',color='brown',waterlogged=False,role='cloth-order and household reading desk')
    p.put(1,6,2,'handcrafted:stackable_book',facing='north',books=4,seed=9,role='real cloth patterns and household books')
    p.put(1,5,1,'handcrafted:dark_oak_chair',facing='south',color='brown',waterlogged=False,role='actual desk-facing small household chair')
    # A supported sloping high eyebrow and the long recessed paired casement
    # distinguish this occupied seamstress frontage from the repair lodging.
    for z in(2,5):
        p.put(-1,7,z,'mythrais:curved_corbel_dark_oak',facing='west',shape=0,role='carved high seamstress-eave support')
        p.supports.append({'detail':[-1,7,z],'support':[0,7,z],'role':'actual upper wall anchors the high carved eave'})
    light(p,1,3,3,'small loom-work light');light(p,1,7,4,'seamstress sleeping-study light')
    door(p,1,7,'south');p.sign(4,3,6,'east',['Sable Spindle','Cloth • Home']);p.put(3,3,6,'minecraft:dark_oak_planks')
    p.room('Little glazed loom and mending room',0,(1,1,4),'The real loom and contained cloth cabinet face a continuous narrow mending passage and two deep casements.')
    p.room('Seamstress’s reading and sleeping loft',4,(1,5,4),'A native stair reaches a real bed, desk, books and chair below a distinctive asymmetric dark timber roof.')
    canonical_joins(p);return p


def low_supper(registry):
    """A low, broad-windowed four-wide cookshop with a seated supper nook."""
    m=rect(0,0,3,5)
    p=Frontage(registry,(0,63,0));p.owner='The Low Kettle';p.main[p.owner]=set(m);p.levels[p.owner]=[set(m)]
    for x,z in m:
        for y in range(1,9):p.put(x,y,z,AIR)
    p.floor(m,0);p.walls(m,0,'minecraft:gray_terracotta')
    p.roof((-1,-1,4,6),4,(0,1,2,2,1,0),family='spruce')
    p.reserve('Low cookshop public approach',[(1,1,z)for z in range(2,6)])
    window(p,0,1,2,'west',width=2);window(p,3,1,1,'east',width=2)
    joists(p,1,2,(2,4))
    p.put(2,1,1,'minecraft:smoker',facing='west',lit=False,role='real small soup and supper cooking hearth')
    p.counter(2,1,2,'west',role='actual small cookshop preparation surface')
    p.put(2,2,2,'farmersdelight:cutting_board',facing='west',waterlogged=False,role='genuine food preparation and cutting surface')
    p.put(2,1,3,'handcrafted:dark_oak_side_table',facing='west',color='none',waterlogged=False,role='real one-person sheltered supper table')
    p.put(2,2,3,'handcrafted:wood_cup',facing='west',pieces=2,waterlogged=False,role='small actual cups on the supper table')
    p.put(2,1,4,'handcrafted:dark_oak_chair',facing='north',color='brown',waterlogged=False,role='real chair facing the supper table')
    light(p,1,3,3,'contained small supper-room light')
    door(p,1,5,'south');p.sign(-1,3,4,'west',['The Low Kettle','Soup • Supper']);p.put(0,3,4,'minecraft:dark_oak_planks')
    p.room('Small practical cookery alcove',0,(1,1,2),'Real cooking and preparation stations sit under a short timber ceiling and fancy working casements.')
    p.room('Sheltered supper nook',0,(1,1,4),'An actual facing chair, table and cups form a small useful second scene at the warm shop front.')
    canonical_joins(p);return p


def tackle_sliver(registry):
    """A very short, intentionally low native-tool and tackle repair shop."""
    m=rect(0,0,2,5)
    p=Frontage(registry,(0,63,0));p.owner='The Tackle Sliver';p.main[p.owner]=set(m);p.levels[p.owner]=[set(m)]
    for x,z in m:
        for y in range(1,8):p.put(x,y,z,AIR)
    p.floor(m,0);p.walls(m,0,'minecraft:brown_terracotta')
    p.roof((-1,-1,3,6),4,(0,1,2,1,0),family='spruce')
    p.reserve('Tackle sliver actual visiting aisle',[(1,1,z)for z in(2,3,5)])
    window(p,0,1,1,'west',width=2);window(p,2,1,2,'east',width=1)
    joists(p,1,1,(2,4))
    p.put(1,1,1,'minecraft:crafting_table',role='actual cork, hook and twine fitting station')
    p.put(1,1,4,'minecraft:barrel',facing='up',open=False,role='new native-default tackle supply and finished-order stock')
    p.put(1,2,4,'handcrafted:terracotta_bowl',facing='south',pieces=3,waterlogged=False,role='real small repair sorting vessels on the stock top')
    light(p,1,3,3,'little native-tool repair light')
    door(p,1,5,'south');p.sign(-1,3,4,'west',['Tackle Sliver','Corks • Repairs']);p.put(0,3,4,'minecraft:dark_oak_planks')
    p.room('Real cork and hook fitting alcove',0,(1,1,2),'A genuine small crafting station and deep casement light the compact front work zone.')
    p.room('Finished-order and vessel niche',0,(1,1,3),'Actual supply stock and sorting vessels form a separately approached rear work niche under a shallow framed ceiling.')
    canonical_joins(p);return p


CUSTOM={'iw-needle-slot':needle_slot,'iw-long-lodging':long_lodging,'iw-corner-cooper':corner_cooper,'iw-paper-rook':paper_rook,
        'iw-short-watch':short_watchmaker,'iw-chart-sliver':skinny_chart_shop,'iw-spindle-return':spindle_return,
        'iw-low-supper':low_supper,'iw-tackle-sliver':tackle_sliver}


@contextmanager
def source_recipes():
    if set(CUSTOM)&set(RECIPES):raise UserError('Never replace a shared recipe')
    original=dict(RECIPES);RECIPES.update(CUSTOM)
    try:yield
    finally:
        RECIPES.clear();RECIPES.update(original)


def checked(home,relative,sha,cap=32*MIB):
    p=home/relative
    if p.is_symlink()or not p.is_file()or not 0<p.stat().st_size<=cap or digest(p)!=sha:raise UserError('Exact immutable city source changed: '+str(relative))
    return read_json(p)


def context(home,checkpoint_id=CHECKPOINT,checkpoint_sha=CHECKPOINT_SHA,field_relative=FIELD,field_sha=FIELD_SHA):
    home=fill.private_home(home);cp=fill.stopped(home,checkpoint_id,checkpoint_sha)
    registry=read_json(home/'dashboard/settlement/registry.json')
    concept=checked(home,coast.APPROVED[0],coast.APPROVED[1])
    field=checked(home,field_relative,field_sha)
    if(field.get('format'),field.get('checkpoint_id'),field.get('checkpoint_sha256'))!=(
        'awft-tortuga-fresh-field:1',checkpoint_id,checkpoint_sha):raise UserError('Genuinely current complete field required; no historical metadata rebind')
    first,refs,_=approved.construction_targets(home,coast.FIVE)
    queued,qrefs,_=approved.construction_targets(home,approved.QUEUED+WEST_FIVE)
    prior={**first,**queued};keep,forest,heritage,oldfields,oldmains,krefs=fill.retained_context(home,registry)
    approved_mass={tuple(p)for row in concept['proposed_buildings']for p in row['cells_xz']}
    lanes={tuple(p)for row in concept['crooked_alley_lines']for seg in row['segments']for p in seg['cells_xz']}
    excluded={(x,z)for x,y,z in prior if 63<=y<=85}
    free={tuple(r[:2])for r in field['eligible_columns_READONLY']if 1100<=r[0]<=1185}
    free=(free&approved_mass)-excluded-lanes-forest
    walkrows={tuple(r[:2]):r for r in field['two_high_walk_columns_READONLY']}
    return home,cp,registry,concept,field,free,walkrows,prior,keep,forest,heritage,refs+qrefs+krefs


def shape(registry,recipe,turn):
    with source_recipes():p=variant_of(RECIPES[recipe](registry),recipe,turn)
    return p


# Specific owner-map programs/centres guide the fitting study. This is not an
# automatic placement authority; the selected actual coordinates are frozen in
# a later explicit source batch and verified again against the stopped save.
PROGRAMS=(
 ('barnacle-cup','The Barnacle Cup','Crew Lodging • Supper',(1105,-1269),('iw-long-lodging','iw-needle-slot')),
 ('net-loft','Nell’s Net Loft','Net Repairs • Home',(1105,-1246),('iw-long-lodging','netmender','iw-spindle-return')),
 ('half-mast','Half Mast Repairs','Fittings • Home',(1110,-1235),('iw-corner-cooper','tideglass','iw-short-watch')),
 ('north-knot','The North Knot','Watches • Household',(1123,-1238),('iw-short-watch','iw-chart-sliver','iw-tackle-sliver')),
 ('sable-spindle','Sable Spindle','Cloth • Family Home',(1137,-1226),('needlewake','iw-spindle-return','iw-short-watch')),
 ('shell-drawer','The Shell Drawer','Coast Notes • Instruments',(1124,-1218),('iw-corner-cooper','tideglass','iw-chart-sliver')),
 ('paper-wren','Paper Wren','Binding • Reading Home',(1134,-1216),('iw-paper-rook','keel-quill','iw-chart-sliver')),
 ('gull-supper','The Gull’s Supper','Cookery • Crew Rooms',(1140,-1207),('briny-hearth','iw-long-lodging','iw-needle-slot')),
 ('small-compass','The Small Compass','Coast Instruments • Home',(1152,-1227),('moon-rigging','gullwatch','iw-short-watch','iw-tackle-sliver')),
 ('sail-return','The Sable Return','Sail Repairs • Home',(1155,-1215),('needlewake','netmender','iw-spindle-return')),
 ('old-tackle','The Old Tackle','Corks • Net Stores',(1173,-1235),('gull-tackle','iw-corner-cooper','iw-tackle-sliver')),
 ('copper-eel','The Copper Eel','Small Fittings • Home',(1173,-1204),('iw-paper-rook','thimble-salt','iw-short-watch')),
 ('lower-lantern','The Lower Lantern','Small Tools • Repairs',(1175,-1197),('gullwatch','iw-needle-slot','thimble-salt','iw-low-supper','iw-tackle-sliver')),
 ('last-barrel','The Last Barrel','Supper • Stores',(1181,-1194),('iw-long-lodging','iw-needle-slot','netmender','iw-low-supper','iw-tackle-sliver')),
)


def outside_anchor(entry,origin):
    x,y,z=entry['outside_step'];dx,dz=VEC[entry['outward']]
    if dx>0:return x+origin[0]+1,z+origin[2]-1
    if dx<0:return x+origin[0]-2,z+origin[2]-1
    if dz>0:return x+origin[0]-1,z+origin[2]+1
    return x+origin[0]-1,z+origin[2]-2


def site_ok(p,origin,free,walkrows,prior,keep,heritage,occupied):
    main={(x+origin[0],z+origin[2])for x,z in p.main[p.owner]}
    if not main<=free or main&occupied:return None
    values={(x+origin[0],y+63,z+origin[2]):s for(x,y,z),s in p.blocks.items()}
    if any(not 1100<=x<=1185 for x,y,z in values):return None
    if any(q in keep or(q[0],q[2])in heritage for q in values):return None
    if any(q in prior and not(s==AIR and prior[q]==AIR)for q,s in values.items()):return None
    entrances=[]
    for entry in p.entries:
        a=outside_anchor(entry,origin);four={(a[0]+dx,a[1]+dz)for dx in(0,1)for dz in(0,1)}
        if not four<=walkrows.keys()or four&(main|occupied):return None
        if any(values.get((x,y,z),AIR)!=AIR or prior.get((x,y,z),AIR)!=AIR or keep.get((x,y,z),AIR)!=AIR
               for x,z in four for y in(64,65)):return None
        entrances.append(a)
    return main,values,entrances


def fit_study(home,output):
    reserve=guard(4*MIB,32*MIB);budgets=[reader_budget()]
    home,cp,registry,concept,field,free,walkrows,prior,keep,forest,heritage,refs=context(home)
    output=Path(output).absolute()
    if output.exists()or output.parent!=home/'staging':raise UserError('New owned fitting study required')
    start=time.monotonic();selected=[];occupied=set();used=Counter();frozen={};refused=[]
    alleys={tuple(p)for row in concept['crooked_alley_lines']for seg in row['segments']for p in seg['centerline_xz']if 1098<=p[0]<=1188}
    model_cache={}
    for program,name,trade,seed,recipes in PROGRAMS:
        candidates=[]
        for recipe in recipes:
            if used[recipe]>=2:continue
            for turn in range(4):
                cache=recipe,turn
                if cache not in model_cache:model_cache[cache]=shape(registry,recipe,turn)
                p=model_cache[cache];m=p.main[p.owner]
                center=(sum(x for x,z in m)/len(m),sum(z for x,z in m)/len(m))
                ax=round(seed[0]-center[0]);az=round(seed[1]-center[1])
                for x in range(ax-7,ax+8):
                    for z in range(az-7,az+8):
                        result=site_ok(p,(x,63,z),free,walkrows,{**prior,**frozen},keep,heritage,occupied)
                        if result is None:continue
                        main,world,entries=result
                        distance=math.dist((x+center[0],z+center[1]),seed)
                        arrival=min((math.dist(a,b)for a in entries for b in alleys),default=30)
                        score=distance*2+arrival+used[recipe]*8+recipes.index(recipe)*2
                        candidates.append((score,x,z,recipe,turn,main,world,entries))
        if not candidates:
            refused.append({'program':program,'seed_xz':list(seed),'reason':'No actual complete dry/clear/protected-safe fit found; no mass shrunk or water filled'});continue
        _,x,z,recipe,turn,main,world,entries=min(candidates,key=lambda r:r[:5])
        selected.append({'program':program,'recipe':recipe,'turn':turn,'name':name,'trade':trade,'origin':[x,63,z],
                         'planned_seed_xz':list(seed),'actual_main_columns':len(main),'external_two_wide_anchors':[list(a)for a in entries]})
        occupied|=main;frozen.update(world);used[recipe]+=1
        if time.monotonic()-start>180:raise UserError('Finite city fitting source180s expired')
        budgets.append(reader_budget())
    doc={'format':'awft-inner-west-fitted-sites-REVIEW-ONLY:1','created':utcnow(),'checkpoint_id':CHECKPOINT,'checkpoint_sha256':CHECKPOINT_SHA,
         'approved_concept_sha256':coast.APPROVED[1],'source_sha256':digest(Path(__file__)),'field_sha256':FIELD_SHA,
         'buildings':selected,'refused_programs':refused,'actual_source_main_columns':len(occupied),'actual_source_targets':len(frozen),
         'main_columns_xz':sorted(map(list,occupied)),'preserved_construction_refs':refs,
         'native_actions':0,'world_writes':0,'native_footings_model_survival_art_walk_acceptance':False,
         'reserve_guard':reserve,'reader_budgets':budgets,'seconds':time.monotonic()-start}
    raw=(json.dumps(doc,separators=(',',':'))+'\n').encode()
    if len(raw)>32*MIB:raise UserError('Finite fitting-study source exceeded')
    output.mkdir();(output/'study.json').write_bytes(raw)
    return {'output':str(output),'study_sha256':digest(output/'study.json'),'buildings':len(selected),'main_columns':len(occupied),
            'source_targets':len(frozen),'refused':len(refused),'native_actions':0}


def safe_walking(rows,prior,keep,mains,states,first):
    """A future street is never permission to clear an occupied old body."""
    return {q:r for q,r in rows.items()if q not in mains and
            all(states.get((q[0],y,q[1]),AIR)==AIR and prior.get((q[0],y,q[1]),AIR)==AIR and
                keep.get((q[0],y,q[1]),AIR)==AIR for y in(64,65))and
            ((q[0],63,q[1])not in prior or(q[0],63,q[1])in first)}


def private_threshold_path(start,public,rows,states,mains,old_mains,prior,keep,max_steps=8):
    """A short single-actor private threshold, never a width claim for a street.

    Outside the one owned new threshold, every literal floor and both body
    states must already be present/clear in the exact saved field. No extra
    paving, plant clearance, old room entry or mask expansion is inferred.
    """
    def usable(q):
        if q in old_mains or(q in mains and q!=start):return False
        row=rows.get(q)
        if row is None:return False
        if q==start:
            if any(key(row[y-61])not in fill.VOIDS|fill.SOFT|fill.NORTH_SOFT for y in(64,65)):return False
        elif any(row[y-61]!=AIR for y in(64,65)):return False
        x,z=q
        if any(states.get((x,y,z),AIR)!=AIR or prior.get((x,y,z),AIR)!=AIR or keep.get((x,y,z),AIR)!=AIR for y in(64,65)):return False
        floor=states.get((x,63,z),row[2])if q==start else row[2]
        return floor!=AIR and key(floor)in fill.GROUND|{'minecraft:polished_andesite','chipped:small_stone_bricks','minecraft:cobbled_deepslate','minecraft:stone_bricks','minecraft:dark_oak_planks','minecraft:spruce_planks','minecraft:stripped_spruce_wood','minecraft:stripped_dark_oak_log','minecraft:dark_oak_wood'}
    if not usable(start):raise UserError('The private threshold lacks literal floor/body: '+str(start))
    todo=deque([start]);parent={start:None};distance={start:0}
    while todo:
        q=todo.popleft()
        if q in public:
            path=[q]
            while parent[q]is not None:q=parent[q];path.append(q)
            return list(reversed(path))
        if distance[q]>=max_steps:continue
        for dx,dz in((0,-1),(1,0),(0,1),(-1,0)):
            r=q[0]+dx,q[1]+dz
            if r not in parent and usable(r):parent[r]=q;distance[r]=distance[q]+1;todo.append(r)
    raise UserError('No supported short private threshold reaches a real two-wide street: '+str(start))


def public_links(home,buildings,states,mains,walkrows,prior,keep):
    """Connect every new real entrance to a witnessed existing public route."""
    public_floors={};route_docs=[];old_mains=set()
    for rel,sha in coast.FIVE+approved.QUEUED+WEST_FIVE:
        doc=checked(home,rel,sha);route_docs.append(doc)
        old_mains|={tuple(q)for b in doc['buildings']for q in b['main_columns_xz']}
        for row in doc['routes']:
            for x,z in row['columns_xz']:
                q=x,63,z;current=walkrows.get((x,z))
                if q in prior and current is not None and current[2]==prior[q]:public_floors[q]=prior[q]
    walking=safe_walking(walkrows,prior,keep,mains|old_mains,states,public_floors)
    anchors=set()
    for doc in route_docs:
        for row in doc['routes']:
            for q in row['center_line']:
                a=math.floor(q[0]),math.floor(q[2])
                if all((a[0]+dx,a[1]+dz)in walking for dx,dz in((0,0),(1,0),(0,1),(1,1))):anchors.add(a)
    if not anchors:raise UserError('No actual clear old public route anchor; no guessed street connection')
    valid={q for q in walking if all((q[0]+dx,q[1]+dz)in walking for dx,dz in((0,0),(1,0),(0,1),(1,1)))}
    public=set(anchors);todo=deque(anchors)
    while todo:
        x,z=todo.popleft()
        for dx,dz in((1,0),(-1,0),(0,1),(0,-1)):
            q=x+dx,z+dz
            if q in valid and q not in public:public.add(q);todo.append(q)
    links=[];witness=[];private=[]
    for b in buildings:
        entry=b['entries'][0];a=outside_anchor(entry,b['origin']);chosen=None
        personal=[]
        if a not in public:
            step=entry['world_threshold'];start=step[0],step[2]
            # Root reviewed this exact saved23m existing coastal passage;
            # no universal two-wide private-alley rule was requested.
            limit=24 if b['name']=='The Copper Eel'else 8
            personal=private_threshold_path(start,public,walkrows,states,mains,old_mains,prior,keep,max_steps=limit)
            a=personal[-1];private.append({'building':b['name'],'width':1,'centers_xz':[list(q)for q in personal],
                                        'source_max_steps':limit,'outside_owned_threshold_new_world_writes':0,'literal_saved_floor_and_two_AIR_body_outside_owned_threshold':True,'native_walking_acceptance':False})
        # Try only a finite set of nearest genuine route cells. A failed
        # connection does not expand the measured field or remove a fixture.
        for target in sorted(anchors,key=lambda q:(abs(q[0]-a[0])+abs(q[1]-a[1]),q))[:160]:
            try:path=fill.path_to(set(walking),a,target)
            except UserError:continue
            chosen=target,path;break
        if chosen is None:raise UserError('No real two-wide route from '+b['name']+' to the existing public street')
        target,path=chosen
        links.append((b['name']+' — short actual two-wide public connection',(a,target)))
        witness.append({'building':b['name'],'outside_two_wide_anchor':list(a),'existing_public_anchor':list(target),
                        'source_path_centers_xz':[list(q)for q in path],'private_threshold_cells':len(personal),'native_walking_acceptance':False})
    return links,witness,walking,private


def qualify_street(home,cp,registry,states,mains,walking,definition,prior,keep,before,full,supports,construction):
    """Read unchanged public pavers as context, not a construction licence.

    The frozen generic building helper deliberately rejects authored pavers
    as construction. This separate source reader retains their exact native
    identities and only proposes paving on actual unowned natural ground.
    """
    lanes,routes=fill.route_geometry(states,mains,{q:r[2:]for q,r in walking.items()},definition)
    zinc=fill.verify_zinc_factory(home);terrain=fill.NorthTerrain(home,cp,registry);seen={};clears=set();began=time.monotonic()
    natural=fill.GROUND|fill.SOFT|fill.NORTH_SOFT|fill.VOIDS
    old_pavers={'minecraft:polished_andesite','chipped:small_stone_bricks','minecraft:cobbled_deepslate','minecraft:andesite','minecraft:cobblestone'}
    try:
        for i,((x,z),axes)in enumerate(sorted(lanes.items())):
            row=walking[x,z];mount=fill.qualified_mount(terrain.state,x,z,zinc)
            if not mount['stable']:raise UserError('Literal saved stable public-street substrate required')
            for xx,yy,zz,value in mount['stack']:
                if(xx,yy,zz)in terrain.entities:raise UserError('No existing block entity may become public street footing')
                supports[xx,yy,zz]=value
            for y in(63,64,65):
                q=x,y,z;actual=terrain.state(*q)
                if actual is None or q in terrain.entities or actual!=row[y-61]or'waterlogged=true'in actual:raise UserError('The actual complete street state differs from its exact current field')
                before[q]=actual;seen[q]=actual
                if y==63:
                    if q in prior or q in keep:
                        if actual!=(prior[q]if q in prior else keep[q]):raise UserError('Retain actual prior public pavers without fitting their expected state')
                        if actual==AIR:raise UserError('A protected AIR floor cannot be paved for a future street')
                        full[q]=actual
                    elif key(actual)in old_pavers:full[q]=actual
                    elif key(actual)in natural:
                        material='chipped:small_stone_bricks'if len(axes)>1 else'minecraft:andesite'if'x'in axes else'minecraft:cobblestone'
                        construction[q]=material;full[q]=material
                    else:raise UserError('No construction over a saved human object or unknown street floor')
                else:
                    if key(actual)not in fill.VOIDS|fill.SOFT|fill.NORTH_SOFT:raise UserError('No clearing an actual solid public walking body')
                    if q in prior or q in keep:
                        if actual!=AIR:raise UserError('Retained body clearance is actual AIR only')
                    elif actual!=AIR:construction[q]=AIR;clears.add(q)
                    full[q]=AIR
            if i%128==0:reader_budget()
            if time.monotonic()-began>45:raise UserError('Bounded45s exact public street reader exceeded')
        sources=terrain.snapshot.sources
    finally:terrain.close()
    return lanes,routes,seen,clears,sources


def prepare_from_study(home,study_path,study_sha,*,checkpoint_id,checkpoint_sha,field_path,field_sha,hold_programs=()):
    """Exact stopped-save proposal. No admission, install or native action."""
    guard(8*MIB,96*MIB);reader_budget()
    home=fill.private_home(home);field_path=Path(field_path).absolute()
    if not field_path.is_relative_to(home/'staging'):raise UserError('Exact current field inside private staging required')
    home,cp,registry,concept,field,free,walkrows,prior,keep,forest,heritage,refs=context(home,checkpoint_id,checkpoint_sha,str(field_path.relative_to(home)),field_sha)
    study_path=Path(study_path).absolute()
    if study_path.parent.parent!=home/'staging':raise UserError('Owned private study only')
    study=checked(home,str(study_path.relative_to(home)),study_sha)
    if(study.get('format'),study.get('checkpoint_id'),study.get('checkpoint_sha256'),study.get('approved_concept_sha256'))!=(
        'awft-inner-west-fitted-sites-REVIEW-ONLY:1',CHECKPOINT,CHECKPOINT_SHA,coast.APPROVED[1]):raise UserError('Wrong concept/checkpoint fitting source')
    if set(hold_programs)-{'copper-eel'}:raise UserError('Only the specifically diagnosed Copper coastal-access hold is selectable')
    selected=[row for row in study.get('buildings',[])if row['program']not in hold_programs]
    if not 1<=len(selected)<=12:raise UserError('One finite completely furnished batch of at most12')
    expected={pr:(name,trade)for pr,name,trade,seed,recipes in PROGRAMS};seen=set();occupied=set();frozen={}
    for row in selected:
        program=row['program']
        if program in seen or expected.get(program)!=(row['name'],row['trade']):raise UserError('Duplicated or invented fitted program')
        seen.add(program)
        p=shape(registry,row['recipe'],row['turn'])
        proof=site_ok(p,tuple(row['origin']),free,walkrows,{**prior,**frozen},keep,heritage,occupied)
        if proof is None:raise UserError('Selected complete frontage no longer fits its exact dry/protected source: '+program)
        main,world,_=proof;occupied|=main;frozen.update(world)
    definition={'buildings':[{k:row[k]for k in('recipe','turn','name','trade','origin')}for row in selected],
                'links':(), 'design':'Nine separately fitted intimate frontages occupy current actual dry gaps in the approved inner-West masses; narrow workshops and occupied homes vary height, window depth, roofs, entries and work scenes. Existing accepted architecture is retained.',
                'street_views':()}
    with source_recipes():states,tags,buildings,mains=fill.modeled(registry,definition)
    threshold_clearance={}
    for b in buildings:
        for entry in b['entries']:
            x,_,z=entry['world_threshold'];row=walkrows.get((x,z))
            if row is None:raise UserError('Exact new threshold needs its real saved field')
            for y in(64,65):
                q=x,y,z
                if q not in states:
                    if key(row[y-61])not in fill.VOIDS|fill.SOFT|fill.NORTH_SOFT:raise UserError('A new threshold cannot erase an actual hard object')
                    threshold_clearance[q]=AIR;states[q]=AIR
    links,witness,walking,private=public_links(home,buildings,states,mains,walkrows,prior,keep)
    definition['links']=links
    subset=deepcopy(field)
    subset['eligible_columns_READONLY']=[r for r in field['eligible_columns_READONLY']if tuple(r[:2])in free]
    subset['two_high_walk_columns_READONLY']=[walking[q]for q in sorted(walking)]
    subset.update(approved_concept_sha256=coast.APPROVED[1],exact_prior_construction_refs=refs,
                  added_buildable_authority_columns=0,selected_study_sha256=study_sha,inner_west_only=True)
    raw=(json.dumps(subset,separators=(',',':'))+'\n').encode()
    if len(raw)>16*MIB:raise UserError('Finite16MiB subtract-only street field exceeded')
    field_out=home/'staging'/('inner-west-subtract-only-field-'+str(time.time_ns()));field_out.mkdir()
    field_file=field_out/'field-READONLY.json';field_file.open('xb').write(raw)
    # Qualify the occupied architecture with the original strict building
    # helper; the exact existing street pavers are retained separately below.
    architecture_definition={**definition,'links':()}
    with source_recipes():result=fill.prepare(home,checkpoint_id,checkpoint_sha,field_file,digest(field_file),'inner-west-current-'+str(len(selected)),definition=architecture_definition,definition_source=Path(__file__))
    folder=Path(result['folder']);manifest=read_json(folder/'manifest.json')
    proposal=read_json(folder/'cluster-PROPOSAL.json');before=flatten(read_json(folder/'before-VERIFY-ONLY.json'))
    proposal.update(construction_forbidden=True,verification_only=True)
    (folder/'cluster-PROPOSAL.json').write_text(json.dumps(proposal,separators=(',',':'))+'\n',encoding='utf-8')
    construction=flatten(proposal);full_doc=read_json(folder/'complete-after-VERIFY-ONLY.json');full=flatten(full_doc)
    supports=flatten(read_json(folder/'stable-supports-VERIFY-ONLY.json'))
    lanes,routes,street_observed,street_clears,street_sources=qualify_street(home,cp,registry,states,mains,walking,definition,prior,keep,before,full,supports,construction)
    for q,value in supports.items():
        if q not in construction:full[q]=value
    for(x,y,z),value in threshold_clearance.items():
        actual=walkrows[x,z][y-61]
        if(x,y,z)in prior or(x,y,z)in keep:raise UserError('Retain an old addressed threshold cell')
        before[x,y,z]=actual;construction[x,y,z]=value;full[x,y,z]=value
    # These are already-real small threshold passages, not extra paving or
    # single-wide streets. Preserve their exact full states as proof only.
    for row in private:
        for x,z in row['centers_xz']:
            actual=walkrows[x,z]
            for y in(63,64,65):
                q=x,y,z;value=actual[y-61]
                if q in before and before[q]!=value:raise UserError('The private threshold source disagrees with the actual before field')
                before[q]=value
                if q not in construction:full[q]=value
    retained={}
    for q in set(construction)&set(prior):
        if before[q]!=prior[q]:raise UserError('Existing prior public paver/body differs from the actual stopped save; retain but do not admit')
        if q in frozen and not(construction[q]==prior[q]==AIR):raise UserError('A new main building cannot adopt old construction')
        retained[q]=before[q];construction.pop(q);full[q]=before[q]
    if len(construction)>12000:raise UserError('Retain source but never admit above12K new targets')
    payloads={
      'cluster-PROPOSAL.json':fill.native_payload(registry,construction,checkpoint_sha,'PROPOSAL ONLY — occupied inner-West buildings and real narrow connecting approaches',tags=tags),
      'before-VERIFY-ONLY.json':fill.native_payload(registry,before,checkpoint_sha,'VERIFY ONLY — exact saved construction targets, stable public routes and literal short private thresholds'),
      'stable-supports-VERIFY-ONLY.json':fill.native_payload(registry,supports,checkpoint_sha,'VERIFY ONLY — exact saved architecture and public walking gravity stacks'),
      'complete-after-VERIFY-ONLY.json':fill.native_payload(registry,full,checkpoint_sha,'VERIFY ONLY — complete new occupied frontages, actual gravity stacks and unchanged public route context',tags=tags),
      'normal-joins-SETTLE-ONLY.json':fill.native_payload(registry,{q:s for q,s in construction.items()if s!=AIR or q in threshold_clearance or q in street_clears},checkpoint_sha,'NORMAL JOINS ONLY — addressed new construction and exact new threshold/plant clearance; no old inventories or public paver replay'),
    }
    for name,doc in payloads.items():
        doc.update(construction_forbidden=True,verification_only=True)
        data=(json.dumps(doc,separators=(',',':'))+'\n').encode();(folder/name).write_bytes(data)
        manifest['files'][name]={'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
    (folder/'public-connections-REVIEW-ONLY.json').write_text(json.dumps({'format':'awft-inner-west-public-connections:1','witnesses':witness,'private_thresholds':private,'public_lane_width':2,'retained_prior_cells':len(retained),'observed_or_native_walk_acceptance':False},separators=(',',':'))+'\n',encoding='utf-8')
    manifest.update(routes=routes,lane_columns=len(lanes),definition=definition,real_retained_footing_cells=len(supports))
    maps=coast.batch_map(manifest,subset)
    (folder/'batch-map-PLAN-ONLY.svg').open('xb').write(maps)
    for name in('public-connections-REVIEW-ONLY.json','batch-map-PLAN-ONLY.svg'):
        manifest['files'][name]={'bytes':(folder/name).stat().st_size,'sha256':digest(folder/name)}
    manifest.update(targets=len(construction),source_only=True,construction_forbidden=True,
      fitting_study={'path':str(study_path.relative_to(home)),'sha256':study_sha,'historical_geometry_only':True,'current_preimage_authority':False},retained_prior_construction_refs=refs,
      held_programs=[{'program':program,'reason':'Existing dry single-actor coastal passage measures23m; exceeds this source batch8m private threshold cap. Unchanged original pure geometry retained; no blind public-width claim.'}for program in hold_programs],
      retained_public_cells_verification_only=[list(q)for q in sorted(retained)],actual_current_main_columns=len(mains),
      exact_owned_threshold_clearance=[{'position':list(q),'before':before[q],'after':AIR}for q in sorted(threshold_clearance)],
      street_actual_saved_sources=street_sources,street_observed_cells=len(street_observed),
      outdoor_rule=fill.lane_materials(construction,lanes,'Inner-West narrow public street additions'),
      native_before_supports_admission_joins_fullviews_required=True,
      all_building_geometry_and_named_routes_retained=True,old_construction_replayed=0)
    (folder/'manifest.json').write_text(json.dumps(manifest,separators=(',',':'))+'\n',encoding='utf-8')
    result.update(manifest_sha256=digest(folder/'manifest.json'),targets=len(construction),lane_columns=len(lanes),files=manifest['files'])
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--home',required=True);p.add_argument('--recipes-only',action='store_true');p.add_argument('--study-output');p.add_argument('--prepare-study');p.add_argument('--study-sha')
    p.add_argument('--checkpoint-id');p.add_argument('--checkpoint-sha');p.add_argument('--field');p.add_argument('--field-sha')
    p.add_argument('--hold-program',action='append',default=[])
    a=p.parse_args();home=Path(a.home)
    if a.prepare_study:
        if not all((a.study_sha,a.checkpoint_id,a.checkpoint_sha,a.field,a.field_sha)):p.error('Exact source study and genuinely current checkpoint/field SHAs required')
        print(json.dumps(prepare_from_study(home,a.prepare_study,a.study_sha,checkpoint_id=a.checkpoint_id,checkpoint_sha=a.checkpoint_sha,field_path=a.field,field_sha=a.field_sha,hold_programs=a.hold_program),indent=2));raise SystemExit(0)
    if a.study_output:
        print(json.dumps(fit_study(home,a.study_output),indent=2));raise SystemExit(0)
    registry=read_json(home/'dashboard/settlement/registry.json')
    print(json.dumps({name:check(fn(registry))for name,fn in CUSTOM.items()},indent=2))
