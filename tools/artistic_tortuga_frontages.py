"""Twelve individually authored muted Tortuga frontages, not a box array.

Pure recipe geometry first. Placement producers must qualify each fixed parcel,
every current BE, every real walking shoulder and the complete future masks.
Neither a recipe count nor source checks certify native visual acceptance.
"""
from __future__ import annotations
from collections import deque

from control_room.common import UserError
from tools.artistic_west_r2_frontage import Frontage,rect,edge,canonical_joins,key,AIR,VEC
from tools.artistic_materials import require_material_rule
from tools.artistic_salt_petal import POTS


def base(registry,name,main,upper,*,panel='minecraft:gray_terracotta',up='minecraft:brown_terracotta'):
    p=Frontage(registry,(0,63,0));p.owner=name;p.main[name]=set(main);p.levels[name]=[set(main),set(upper)]
    for x,z in main|upper:
        for y in range(1,17):p.put(x,y,z,AIR)
    p.floor(main,0);p.walls(main,0,panel);p.floor(upper,4);p.walls(upper,4,up)
    return p


def third(p,cells,panel='minecraft:gray_terracotta'):
    p.levels[p.owner].append(set(cells));p.floor(cells,8);p.walls(cells,8,panel)


def routes(p,title,ground,up,*,stairs):
    """Routes precede furniture and doors, so neither is silently erased."""
    p.reserve(title+' working passage',[(x,1,z)for x,z in ground])
    p.reserve(title+' home passage',[(x,5,z)for x,z in up])
    p.stair_flight(*stairs,0)


def door(p,x,z,face):
    """Real door plus one-block-deep braced recess and grounded threshold."""
    dx,dz=VEC[face];tx,tz=(1,0)if dz else(0,1)
    inward={'north':'south','south':'north','east':'west','west':'east'}[face]
    for side in(-1,0,1):
        xx,zz=x+dx+side*tx,z+dz+side*tz
        p.put(xx,0,zz,'minecraft:stone_bricks',role='real dry supported threshold')
        p.main[p.owner].add((xx,zz))
        if side:
            for y in(1,2,3):p.put(xx,y,zz,'dawnoftimebuilder:charred_spruce_timber_frame_pillar',axis='y',role='grounded recessed-entry cheek')
            p.put(xx+dx,3,zz+dz,'mythrais:curved_corbel_dark_oak',facing=face,shape=0,role='entry cheek carved support')
        p.beam(xx,4,zz,'x'if tx else'z',wood='dark_oak',role='supported deep entry lintel')
    for y,half in((1,'lower'),(2,'upper')):
        p.put(x,y,z,'mcwdoors:dark_oak_cottage_door',facing=inward,half=half,hinge='left',open=False,powered=False)
    p.entries.append({'owner':p.owner,'door':[x,1,z],'outward':face,'outside_step':[x+dx,0,z+dz]})


def light(p,x,y,z,role):
    p.put(x,y,z,'minecraft:lantern',hanging=True,waterlogged=False,role=role)
    p.put(x,y+1,z,'minecraft:dark_oak_planks',role='actual full-block task-light mount')
    p.supports.append({'detail':[x,y,z],'support':[x,y+1,z],'role':role})


def joists(p,x0,x1,zs,floor=0):
    for z in zs:
        for x in range(x0,x1+1):p.slab(x,floor+3,z,role='visible shallow ceiling joist under actual occupied floor')


def window(p,x,y,z,face,*,width=2,height=2,**kwargs):
    # A continuous framed head is actual architecture behind the projecting
    # eyebrow, including the little return heads at a proud oriel. It is not
    # an unsupported cap in the neighbouring AIR cell.
    tx,tz=(1,0)if face in('north','south')else(0,1)
    for n in range(-1,width+1):
        p.beam(x+n*tx,y+height,z+n*tz,'x'if tx else'z',wood='charred_spruce'if tx else'dark_oak',role='continuous real casement head behind the carved hood')
    p.window(x,y,z,face,width=width,height=height,**kwargs)


def bay_south(p,x,z,y=5,width=2):
    """Occupied proud oriel, with glass returns and full floor/head support."""
    for xx in range(x,x+width+1):
        p.put(xx,y-1,z,'minecraft:dark_oak_planks',role='projecting inhabited window floor')
        for yy in(y,y+1):p.put(xx,yy,z-1,AIR)
    window(p,x,y,z,'south',width=width,height=2)
    window(p,x,y,z-1,'west',width=1,height=2,cut_start=True)
    window(p,x+width,y,z-1,'east',width=1,height=2,cut_start=True)
    for xx in(x,x+width):
        p.put(xx,y-2,z,'mythrais:curved_corbel_dark_oak',facing='south',shape=0,role='real oriel-floor supporting corbel')
        p.beam(xx,y-2,z-1,'x',wood='dark_oak',role='oriel corbel anchored to the actual occupied-floor joist')
        p.supports.append({'detail':[xx,y-2,z],'support':[xx,y-2,z-1],'role':'bay carved support joined to real wall'})


def upper_home(p,*,bed,desk,chair,hearth,pantry,table,standing,title,chair_face='east'):
    bx,bz=bed;p.bed(bx,5,bz)
    dx,dz=desk;p.put(dx,5,dz,'handcrafted:dark_oak_desk',facing='south',color='brown',waterlogged=False,role='household writing and trade-order desk')
    p.put(dx,6,dz,'handcrafted:stackable_book',facing='south',books=3,seed=13,role='trade accounts and household books')
    cx,cz=chair;p.put(cx,5,cz,'handcrafted:dark_oak_chair',facing=chair_face,color='brown',waterlogged=False,role='real desk chair')
    hx,hz=hearth;p.put(hx,5,hz,'minecraft:smoker',facing='east',lit=False,role='real small cooking hearth')
    px,pz=pantry;p.put(px,5,pz,'farmersdelight:dark_oak_cabinet',facing='east',open=False,role='new native-default household pantry')
    tx,tz=table;p.put(tx,5,tz,'handcrafted:dark_oak_side_table',facing='south',color='none',waterlogged=False,role='small household supper table')
    p.put(tx,6,tz,'handcrafted:wood_cup',facing='south',pieces=2,waterlogged=False,role='cups after supper')
    row=sorted(x for x,z in p.levels[p.owner][1]if z==standing[1])
    for x in row:
        if p.blocks.get((x,8,standing[1]),AIR)==AIR:p.beam(x,8,standing[1],'x',role='real upper-home ceiling tie joining its wall heads')
    light(p,standing[0],7,standing[1],'small warm upper-home reading light')
    p.room(title,4,(*standing[:1],5,standing[1]),'Real stair, bed, reading desk, kitchen hearth, pantry and supper furniture under modeled ceiling ribs.')


def gullwatch(registry):
    """A tall hooked lantern keeper with a low rear instrument niche."""
    m=rect(0,0,6,10)-{(0,0),(0,1),(6,0)};u=(m-{(0,10),(1,10)})|{(3,11),(4,11),(5,11)}
    p=base(registry,'Gullwatch Lantern Home',m,u,up='minecraft:gray_terracotta');third(p,m-{(0,0),(0,1),(0,2),(6,10)})
    p.roof((-1,-1,7,11),12,(0,1,2,3,4,3,2,1,0),family='deepslate')
    p.roof((0,9,3,11),8,(0,1,1,0),family='dark_oak',annex=True)
    routes(p,'Gullwatch',[(4,z)for z in range(3,11)]+[(3,6),(2,6)],[(4,z)for z in range(2,9)]+[(3,6)],stairs=(5,8))
    p.stair_flight(5,8,4);p.reserve('Gullwatch lookout passage',[(4,9,z)for z in range(3,9)])
    window(p,1,1,10,'south');window(p,0,2,5,'west',width=2);bay_south(p,3,11)
    window(p,1,9,10,'south');window(p,6,9,3,'east',width=2)
    joists(p,1,4,(3,7));joists(p,1,4,(3,7),4)
    p.put(1,1,2,'minecraft:cartography_table',role='real coast and lantern-range chart bench');p.shelf(1,2,3,'east',books=True)
    for z in(4,5):p.counter(1,1,z,'east',role='lantern packing and oil work counter')
    p.put(1,2,5,'supplementaries:hourglass',facing='up',light_level=0,waterlogged=False,role='watch-change timer')
    p.put(2,1,8,'minecraft:crafting_table',role='actual lantern fitting station');p.put(1,1,8,'minecraft:barrel',facing='up',open=False,role='new native-default lantern supplies')
    p.put(2,2,8,POTS[4],role='contained fern beside the work bench');light(p,2,3,4,'warm lantern-work light')
    upper_home(p,bed=(1,4),desk=(2,7),chair=(1,7),hearth=(1,8),pantry=(2,8),table=(3,5),standing=(4,6),title='Lantern keeper’s home')
    p.put(1,9,4,'handcrafted:dark_oak_desk',facing='east',color='brown',waterlogged=False,role='occupied high coast-watch writing desk')
    p.put(1,10,4,'supplementaries:globe',facing='east',role='ordinary native decorative navigation globe')
    p.put(2,9,7,'handcrafted:dark_oak_bench',facing='east',shape='single',color='brown',waterlogged=False,role='lookout bench')
    for x in range(0,7):p.beam(x,12,5,'x',role='actual high lookout ceiling tie rooted at wall heads')
    light(p,3,11,5,'small lookout lantern');p.room('Lantern fitting shop',0,(3,1,6),'Charts, oil packing, real tools, stored fittings and a bright task surface.');p.room('High coast-watch study',8,(4,9,6),'A real second stair reaches the globe desk, high casement and lookout seat.')
    door(p,4,10,'south');p.sign(6,3,9,'east',['Gullwatch','Lanterns • Charts']);p.put(5,3,9,'minecraft:dark_oak_planks')
    return p


def tideglass(registry):
    """Broad glass workroom below a stepped, narrower home and deep bay."""
    m=rect(0,0,7,10)-{(0,0),(0,1),(7,10),(6,10)};u=rect(0,1,5,8)|rect(1,9,4,9)
    p=base(registry,'Tideglass Bottle & Chart',m,u,up='minecraft:light_gray_terracotta')
    p.roof((-1,0,6,10),8,(0,1,2,3,3,2,1,0),family='dark_oak')
    p.roof((5,-1,8,10),4,(0,1,1,0),family='spruce',annex=True)
    routes(p,'Tideglass',[(4,z)for z in range(2,11)]+[(3,6),(2,6)],[(4,z)for z in range(2,8)]+[(3,6)],stairs=(5,7))
    window(p,1,1,10,'south',width=2,height=3);window(p,7,1,3,'east',width=3,height=3);bay_south(p,1,10)
    window(p,0,5,3,'west',width=2);joists(p,1,4,(3,7));joists(p,1,4,(3,7),4)
    p.counter(1,1,3,'east',role='bottle washing and chart-tube display');p.counter(1,1,4,'east',role='glass-work display return')
    p.put(1,2,3,'supplementaries:jar',facing='east',light_level=0,waterlogged=False,role='inert bottle/glass display vessel');p.put(1,2,4,'handcrafted:terracotta_bowl',facing='east',pieces=3,waterlogged=False,role='small glass-work sorting bowls')
    p.put(6,1,2,'minecraft:water_cauldron',level=3,role='real contained cleaning water');p.put(6,1,5,'minecraft:crafting_table',role='actual framing and bottle fitting bench')
    p.shelf(2,2,1,'south',books=True);p.put(2,1,8,'handcrafted:dark_oak_drawer',facing='south',shape='single',type=2,role='new native-default chart slips and small fittings');p.put(2,2,8,POTS[2],role='contained pale plumeria at shop window')
    light(p,3,3,4,'warm bottle-shop task lantern');upper_home(p,bed=(1,4),desk=(2,7),chair=(1,7),hearth=(1,8),pantry=(2,8),table=(3,3),standing=(4,6),title='Bottle maker’s tucked home')
    p.room('Deep glass display and workroom',0,(3,1,6),'A tall fancy glass front and low glazed side room hold vessels, rinsing, real fitting tools and a shaded counter.')
    door(p,4,10,'south');p.sign(6,3,8,'east',['Tideglass','Bottles • Chart Tubes']);p.put(5,3,8,'minecraft:dark_oak_planks')
    return p


def needlewake(registry):
    """A seamstress's east entry turns under a low, long west work wing."""
    m=rect(0,0,7,9)-{(0,0),(7,0),(7,1),(0,9)};u=rect(2,1,7,8)-{(7,1)}
    p=base(registry,'Needlewake Cloth & Home',m,u,panel='minecraft:brown_terracotta',up='minecraft:gray_terracotta')
    p.roof((1,0,8,9),8,(0,1,2,3,3,2,1,0),family='spruce',hip_south=True)
    p.roof((-1,-1,2,10),4,(0,1,1,0),family='dark_oak',annex=True)
    routes(p,'Needlewake',[(5,z)for z in range(2,9)]+[(x,8)for x in range(3,8)]+[(x,5)for x in range(2,6)],[(5,z)for z in range(2,8)]+[(4,5)],stairs=(6,7))
    window(p,7,1,2,'east',width=2,height=3);window(p,0,1,4,'west',width=3,height=2);window(p,7,5,2,'east',width=2);bay_south(p,3,9)
    joists(p,1,5,(3,7));joists(p,3,5,(3,7),4)
    p.put(1,1,2,'minecraft:loom',facing='east',role='real cloth and pennant loom');p.counter(1,1,4,'east',role='tailoring cutting table')
    p.put(1,2,4,'farmersdelight:cutting_board',facing='east',waterlogged=False,role='real needleworker repair/cutting surface')
    p.put(2,1,2,'farmersdelight:dark_oak_cabinet',facing='south',open=False,role='native-default cloth and tool cabinet');p.put(3,1,2,'minecraft:crafting_table',role='actual seam and fastener work')
    p.shelf(2,2,8,'north',books=True);p.put(1,1,7,'handcrafted:dark_oak_chair',facing='east',color='brown',waterlogged=False,role='tailor’s fitting chair');p.put(3,1,7,POTS[0],role='contained pale shop flower')
    light(p,3,3,4,'warm tailoring task lantern');upper_home(p,bed=(3,4),desk=(3,7),chair=(4,7),chair_face='west',hearth=(6,2),pantry=(3,2),table=(4,3),standing=(5,5),title='Seamstress’s upper home')
    p.room('Low tailoring and fitting room',0,(4,1,6),'A broad side casement lights loom, cutting, fitting chair and order shelves; the east door turns into the shared lane.')
    door(p,7,8,'east');p.sign(7,3,8,'east',['Needlewake','Sails • Stitches']);p.put(6,3,8,'minecraft:dark_oak_planks')
    return p


def netmender(registry):
    """Shallow westwater home with a tall north loft and lower front net bay."""
    m=rect(0,0,7,8)-{(0,0),(0,1),(7,7),(7,8)};u=rect(1,0,6,6)|{(2,7),(3,7),(4,7)}
    p=base(registry,'Net Mender’s Window',m,u,up='minecraft:green_terracotta')
    p.roof((0,-1,7,7),8,(0,1,2,3,3,2,1,0),family='dark_oak')
    p.roof((0,7,6,9),4,(0,1,2,2,2,1,0),family='spruce',annex=True)
    routes(p,'Net Mender',[(4,z)for z in range(2,9)]+[(3,5),(2,5)],[(4,z)for z in range(2,6)],stairs=(5,6))
    window(p,1,1,8,'south',width=2,height=2);window(p,0,1,3,'west',width=2);bay_south(p,2,7)
    joists(p,1,4,(2,6));joists(p,2,4,(2,6),4)
    p.put(1,1,2,'minecraft:loom',facing='east',role='real net and canvas loom');p.counter(1,1,4,'east',role='net-mending and cork fitting worktop')
    p.put(1,2,4,'farmersdelight:cutting_board',facing='east',waterlogged=False,role='real knife/cork cutting surface');p.put(2,1,2,'minecraft:barrel',facing='up',open=False,role='new native-default tackle supplies')
    p.put(2,2,2,'handcrafted:terracotta_bowl',facing='south',pieces=3,waterlogged=False,role='corks and clean small tackle vessels')
    p.shelf(2,2,6,'north',books=True);p.put(1,1,6,POTS[4],role='contained red fern on the old quay work edge')
    light(p,3,3,3,'net-mending task lantern');upper_home(p,bed=(2,3),desk=(2,5),chair=(3,5),chair_face='west',hearth=(5,1),pantry=(4,1),table=(3,2),standing=(4,4),title='Net mender’s crooked loft')
    p.room('Net and cork repair room',0,(3,1,5),'A low sheltered net window lights the real loom and work bench, small tackle storage and a repair ledger.')
    door(p,4,8,'south');p.sign(-1,3,3,'west',['Net Mender','Cork • Canvas']);p.put(0,3,3,'minecraft:dark_oak_planks')
    return p


def lost_tide(registry):
    """Narrow three-storey ship joiner with a chamfered north work corner."""
    m=rect(0,0,6,9)-{(0,0),(1,0),(0,1),(6,9)};u=m|{(2,10),(3,10),(4,10)}
    p=base(registry,'The Lost Tide Joiner',m,u,up='minecraft:gray_terracotta');third(p,rect(1,1,6,8)-{(6,8)})
    p.roof((0,0,7,9),12,(0,1,2,3,3,2,1,0),family='deepslate',hip_south=True)
    p.roof((-1,7,4,10),8,(0,1,2,2,1,0),family='dark_oak',annex=True)
    routes(p,'Lost Tide',[(4,z)for z in range(2,10)]+[(3,5),(2,5)],[(4,z)for z in range(2,8)]+[(3,5)],stairs=(5,7))
    p.stair_flight(5,7,4);p.reserve('Lost Tide reading-loft aisle',[(4,9,z)for z in range(2,8)])
    window(p,1,1,9,'south',height=3);window(p,0,1,3,'west',width=2);bay_south(p,2,10)
    window(p,1,9,8,'south');window(p,6,9,3,'east',width=2);joists(p,1,4,(3,6));joists(p,1,4,(3,6),4)
    p.put(1,1,2,'minecraft:stonecutter',facing='east',role='real precision ship fitting station');p.put(2,1,2,'minecraft:crafting_table',role='actual wood/fitting craft table')
    p.counter(1,1,4,'east',role='ship joinery and repair counter');p.put(1,2,4,'farmersdelight:cutting_board',facing='east',waterlogged=False,role='actual repair work surface')
    p.put(1,1,7,'minecraft:barrel',facing='up',open=False,role='new native-default joiner stock');p.shelf(2,2,7,'north',books=True)
    light(p,3,3,4,'joinery work lantern');upper_home(p,bed=(1,4),desk=(2,6),chair=(1,6),hearth=(1,8),pantry=(2,8),table=(3,3),standing=(4,5),title='Ship joiner’s home')
    p.put(2,9,3,'handcrafted:dark_oak_desk',facing='east',color='brown',waterlogged=False,role='ship-plan drafting desk');p.put(2,10,3,'handcrafted:stackable_book',facing='east',books=3,seed=5,role='real model shop shipping books')
    p.put(2,9,6,'handcrafted:dark_oak_bench',facing='east',shape='single',color='brown',waterlogged=False,role='high reading and fitting-view bench')
    for x in range(1,7):p.beam(x,12,4,'x',role='actual high study ceiling tie rooted at wall heads')
    light(p,3,11,4,'small loft reading lantern')
    p.room('Ship joinery workroom',0,(3,1,5),'Real precision/craft stations, tools, workbench and fitting stock occupy the cropped quay workshop.');p.room('High ship-plan study',8,(4,9,5),'Second ordinary stair reaches a lit drafting desk, books, broad windows and reading bench.')
    door(p,4,9,'south');p.sign(6,3,7,'east',['The Lost Tide','Ship Joinery']);p.put(5,3,7,'minecraft:dark_oak_planks')
    return p


def kettle_bend(registry):
    """Low tea/soup room turns around its taller rear domestic gable."""
    m=rect(0,0,8,8)-{(0,0),(0,1),(8,0),(8,8),(7,8)};u=rect(0,1,5,6)|rect(1,7,4,7)
    p=base(registry,'Kettle Bend Supper House',m,u,panel='minecraft:gray_terracotta',up='minecraft:brown_terracotta')
    p.roof((-1,0,6,8),8,(0,1,2,3,3,2,1,0),family='dark_oak',hip_south=True)
    p.roof((5,0,9,9),4,(0,1,2,1,0),family='spruce',annex=True)
    routes(p,'Kettle Bend',[(4,z)for z in range(2,9)]+[(x,7)for x in range(2,8)],[(4,z)for z in range(2,7)]+[(3,5)],stairs=(5,6))
    window(p,1,1,8,'south');window(p,8,1,2,'east',width=3);bay_south(p,1,8)
    joists(p,1,5,(3,6));joists(p,1,4,(3,6),4)
    p.put(1,1,2,'minecraft:smoker',facing='east',lit=False,role='real supper-house cookery hearth');p.counter(1,1,3,'east',role='soup preparation counter')
    p.put(1,2,3,'farmersdelight:cutting_board',facing='east',waterlogged=False,role='actual vegetable preparation');p.put(2,1,2,'farmersdelight:dark_oak_cabinet',facing='south',open=False,role='new native-default food pantry')
    p.table(2,1,6,'east');p.table(6,1,3,'north');p.put(6,1,5,'handcrafted:dark_oak_bench',facing='north',shape='single',color='brown',waterlogged=False,role='sheltered kitchen-window waiting seat')
    p.put(7,1,6,POTS[0],role='contained warm supper-room flower');p.shelf(2,2,1,'south',books=True);light(p,3,3,4,'small practical kitchen lantern')
    upper_home(p,bed=(1,4),desk=(2,5),chair=(1,5),hearth=(1,6),pantry=(2,6),table=(3,2),standing=(4,4),title='Cook’s upper home')
    p.room('Bent supper and tea room',0,(4,1,5),'Two real furniture groups, a practical cooking hearth, working preparation counter and food pantry face the sheltered street.')
    door(p,4,8,'south');p.sign(7,3,6,'east',['Kettle Bend','Soup • Tea']);p.put(6,3,6,'minecraft:dark_oak_planks')
    return p


def side_bay(p,x,z,face,y=5,width=2):
    """A west/east/north occupied oriel with glazed return cheeks."""
    dx,dz=VEC[face];tx,tz=(1,0)if dz else(0,1)
    low='west'if tx else'north';high='east'if tx else'south'
    for n in range(width+1):
        xx,zz=x+n*tx,z+n*tz
        p.put(xx,y-1,zz,'minecraft:dark_oak_planks',role='inhabited projecting side-bay floor')
        for yy in(y,y+1):p.put(xx-dx,yy,zz-dz,AIR)
    window(p,x,y,z,face,width=width,height=2)
    window(p,x-dx,y,z-dz,low,width=1,height=2,cut_start=True)
    window(p,x+width*tx-dx,y,z+width*tz-dz,high,width=1,height=2,cut_start=True)
    for n in(0,width):
        xx,zz=x+n*tx,z+n*tz
        p.put(xx,y-2,zz,'mythrais:curved_corbel_dark_oak',facing=face,shape=0,role='carved side-bay floor support')
        p.beam(xx-dx,y-2,zz-dz,'x'if tx else'z',wood='charred_spruce'if tx else'dark_oak',role='side-bay corbel’s real occupied-floor joist')
        p.supports.append({'detail':[xx,y-2,zz],'support':[xx-dx,y-2,zz-dz],'role':'side-bay carved bracket'})


def briny_hearth(registry):
    """West bread counter, taller rear home, low long east cookhouse wing."""
    m=rect(0,0,7,9)-{(0,0),(1,0),(7,9)};u=rect(0,1,5,8)-{(0,1),(0,2)}
    p=base(registry,'The Briny Hearth',m,u,panel='minecraft:brown_terracotta',up='minecraft:gray_terracotta')
    p.roof((-1,0,6,9),8,(0,1,2,3,3,2,1,0),family='dark_oak')
    p.roof((5,-1,8,9),4,(0,1,1,0),family='spruce',annex=True)
    routes(p,'Briny Hearth',[(4,z)for z in range(2,9)]+[(x,8)for x in range(0,5)],[(4,z)for z in range(2,8)]+[(3,5)],stairs=(5,7))
    window(p,0,1,3,'west',width=3,height=2);window(p,7,1,2,'east',width=2);side_bay(p,-1,4,'west')
    window(p,2,5,8,'south');joists(p,1,4,(3,7));joists(p,1,4,(3,7),4)
    p.put(6,1,2,'minecraft:smoker',facing='west',lit=False,role='real bakery cooking hearth');p.put(6,1,3,'minecraft:furnace',facing='west',lit=False,role='actual second small cooking oven')
    for z in(4,5):p.counter(6,1,z,'west',role='bread and supper preparation bench')
    p.put(6,2,4,'farmersdelight:cutting_board',facing='west',waterlogged=False,role='actual baking/preparation board')
    p.put(1,1,2,'farmersdelight:dark_oak_cabinet',facing='east',open=False,role='new native-default flour and household pantry')
    p.counter(1,1,4,'east',role='bread-order counter behind the fancy work window');p.put(1,2,4,'handcrafted:terracotta_bowl',facing='east',pieces=3,waterlogged=False,role='empty native bakery preparation bowls')
    p.shelf(2,2,1,'south',books=True);p.table(2,1,6,'east');p.put(1,1,7,POTS[0],role='contained pale flower beside the worn bread window');light(p,3,3,4,'warm actual bread-room task lantern')
    upper_home(p,bed=(1,4),desk=(2,6),chair=(1,6),hearth=(1,7),pantry=(2,7),table=(3,3),standing=(4,5),title='Baker’s rear home')
    p.room('Bread counter and cookhouse',0,(4,1,6),'A genuinely low cookhouse, two real ovens, long preparation bench, bowls, food pantry, order counter and supper seat.')
    door(p,0,8,'west');p.sign(-1,3,6,'west',['The Briny Hearth','Bread • Supper']);p.put(0,3,6,'minecraft:dark_oak_planks')
    return p


def quarter_tide(registry):
    """North-facing tiny tavern with a lower enclosed music/supper return."""
    m=rect(0,0,8,9)-{(0,0),(8,0),(0,1),(8,8),(8,9)};u=rect(1,1,6,8)|{(4,0),(5,0)}
    p=base(registry,'Quarter Tide Music & Ale',m,u,panel='minecraft:gray_terracotta',up='minecraft:brown_terracotta')
    p.roof((0,-1,7,9),8,(0,1,2,3,3,2,1,0),family='dark_oak',hip_south=True)
    p.roof((6,0,9,7),4,(0,1,1,0),family='spruce',annex=True)
    routes(p,'Quarter Tide',[(5,z)for z in range(0,8)]+[(x,6)for x in range(2,6)],[(4,z)for z in range(2,8)]+[(3,5)],stairs=(6,7))
    window(p,1,1,0,'north',width=2,height=3);window(p,8,1,2,'east',width=3);side_bay(p,4,-1,'north')
    window(p,1,5,4,'west',width=2);joists(p,1,5,(3,7));joists(p,2,5,(3,7),4)
    for z in(2,3,4):p.counter(1,1,z,'east',role='small working tavern bar and service counter')
    p.put(1,2,3,'handcrafted:wood_cup',facing='east',pieces=3,waterlogged=False,role='mugs on the real service counter')
    p.put(2,1,2,'minecraft:barrel',facing='up',open=False,role='new native-default tavern stock, never copied items');p.shelf(2,2,8,'north',books=True)
    p.table(3,1,4,'east');p.table(7,1,6,'north');p.put(7,1,2,'minecraft:jukebox',has_record=False,role='ordinary empty native music box; no forged disc or playback')
    p.put(3,1,8,'minecraft:smoker',facing='north',lit=False,role='real little tavern kitchen hearth');p.put(1,1,7,POTS[5],role='contained tavern fern')
    light(p,4,3,3,'small warm tavern service lantern');upper_home(p,bed=(2,4),desk=(2,7),chair=(3,7),chair_face='west',hearth=(5,2),pantry=(5,3),table=(3,3),standing=(4,6),title='Innkeeper’s private upper home')
    p.room('Small music and supper tavern',0,(4,1,6),'An intimate real service bar, mugs, two varied tables, music box and cookery instead of a cavernous empty hall.')
    door(p,5,0,'north');p.sign(7,3,-1,'north',['Quarter Tide','Music • Supper']);p.put(7,3,0,'minecraft:dark_oak_planks')
    return p


def moon_rigging(registry):
    """Crooked west doorway below a high glazed navigation room and side hip."""
    m=rect(0,0,6,10)-{(0,0),(0,1),(6,10),(5,10)};u=m|{(0,7),(-1,7),(-1,8),(-1,9)}
    p=base(registry,'Moon in Rigging',m,u,up='minecraft:green_terracotta')
    p.roof((-1,-1,7,10),8,(0,1,2,3,4,3,2,1,0),family='deepslate')
    p.roof((-2,6,2,11),8,(0,1,2,1,0),family='dark_oak',annex=True)
    routes(p,'Moon in Rigging',[(4,z)for z in range(2,10)]+[(x,8)for x in range(0,5)],[(4,z)for z in range(2,9)]+[(3,6)],stairs=(5,8))
    window(p,0,1,3,'west',width=2,height=3);window(p,1,1,10,'south');side_bay(p,-1,7,'west')
    window(p,6,5,3,'east',width=3);joists(p,1,4,(3,7));joists(p,1,4,(3,7),4)
    p.put(1,1,2,'minecraft:cartography_table',role='real navigation and chart work');p.put(2,1,2,'minecraft:crafting_table',role='actual rope and instrument fitting table')
    p.counter(1,1,5,'east',role='navigation instrument and sail-note counter');p.put(1,2,5,'supplementaries:hourglass',facing='up',light_level=0,waterlogged=False,role='real decorative watchglass')
    p.put(1,1,7,'minecraft:barrel',facing='up',open=False,role='new native-default navigation stock');p.shelf(2,2,9,'north',books=True)
    p.put(1,1,9,POTS[7],role='contained blue orchid at the mariner’s tucked wall');light(p,3,3,4,'practical chart-reading lantern')
    upper_home(p,bed=(1,4),desk=(2,7),chair=(1,7),hearth=(1,9),pantry=(2,9),table=(3,3),standing=(4,6),title='Mariner’s crooked oriel home')
    p.room('Navigation and fitting room',0,(3,1,6),'Real chart/fitting stations and watch tools sit below an irregular high navigation-room window.')
    door(p,0,8,'west');p.sign(-1,3,6,'west',['Moon in Rigging','Charts • Fittings']);p.put(0,3,6,'minecraft:dark_oak_planks')
    return p


def keel_quill(registry):
    """Thin east bookshop, stepped upper reading bay and a real second stair."""
    m=rect(0,0,7,10)-{(0,0),(1,0),(7,0),(7,10)};u=rect(1,1,7,9)|{(2,10),(3,10),(4,10)}
    p=base(registry,'Keel & Quill Bookbindery',m,u,up='minecraft:gray_terracotta');third(p,rect(1,1,6,8))
    p.roof((0,0,7,9),12,(0,1,2,3,3,2,1,0),family='dark_oak')
    p.roof((1,8,5,11),8,(0,1,2,1,0),family='spruce',annex=True)
    routes(p,'Keel and Quill',[(4,z)for z in range(2,10)]+[(x,9)for x in range(4,8)],[(4,z)for z in range(2,9)]+[(3,6)],stairs=(5,8))
    p.stair_flight(5,8,4);p.reserve('Keel and Quill high reading aisle',[(4,9,z)for z in range(2,8)])
    window(p,7,1,3,'east',width=2,height=3);window(p,1,1,10,'south');side_bay(p,8,6,'east')
    window(p,1,9,8,'south');window(p,6,9,3,'east',width=2);joists(p,1,4,(3,7));joists(p,1,4,(3,7),4)
    for z in(3,4,5):p.counter(1,1,z,'east',role='bookbinding work and order counter')
    p.put(1,2,4,'handcrafted:stackable_book',facing='east',books=3,seed=4,role='books awaiting binding, ordinary native book models')
    p.put(2,1,2,'minecraft:lectern',facing='east',has_book=False,powered=False,role='ordinary empty native public reading lectern')
    p.shelf(2,2,9,'north',books=True);p.shelf(2,2,1,'south',books=True);p.put(2,1,7,'minecraft:crafting_table',role='actual binding and cover craft table')
    p.put(1,1,8,POTS[5],role='contained bookshop fern');light(p,3,3,4,'warm bookbinding task light')
    upper_home(p,bed=(2,4),desk=(2,7),chair=(3,7),chair_face='west',hearth=(6,2),pantry=(5,2),table=(3,3),standing=(4,6),title='Bookbinder’s upper home')
    p.put(2,9,3,'handcrafted:dark_oak_desk',facing='east',color='brown',waterlogged=False,role='high reading and book-repair desk');p.put(2,10,3,'handcrafted:stackable_book',facing='east',books=3,seed=8,role='high reading-room books')
    p.put(2,9,6,'handcrafted:dark_oak_bench',facing='east',shape='single',color='brown',waterlogged=False,role='real high reading bench')
    for x in range(1,7):p.beam(x,12,5,'x',role='actual high reading-room ceiling tie rooted at wall heads')
    light(p,3,11,5,'small high reading lantern')
    p.room('Bookbinding and public reading counter',0,(4,1,6),'Hand-bound book models, shelves, actual lectern and a working craft bench behind a deep fancy shop casement.');p.room('Upper reading room',8,(4,9,5),'A genuine second stair reaches a high lit writing desk, books, casements and reading bench.')
    door(p,7,9,'east');p.sign(8,3,7,'east',['Keel & Quill','Books • Binding']);p.put(7,3,7,'minecraft:dark_oak_planks')
    return p


def mugs_mending(registry):
    """North-facing L-house wraps a tiny contained green working nook."""
    m=rect(0,0,5,9)|rect(6,4,8,9);m-={(0,0),(0,1),(8,9)};u=rect(1,1,5,8)|rect(6,5,7,7)
    p=base(registry,'Mugs & Mending',m,u,panel='minecraft:brown_terracotta',up='minecraft:gray_terracotta')
    p.roof((0,0,6,9),8,(0,1,2,3,2,1,0),family='dark_oak')
    p.roof((5,3,9,10),4,(0,1,2,1,0),family='spruce',annex=True)
    routes(p,'Mugs and Mending',[(4,z)for z in range(0,9)]+[(x,8)for x in range(4,8)],[(4,z)for z in range(2,8)]+[(3,5)],stairs=(5,7))
    window(p,1,1,0,'north',height=3);window(p,8,1,5,'east',width=2);side_bay(p,2,0,'north')
    window(p,1,5,4,'west',width=2);joists(p,1,4,(3,7));joists(p,2,4,(3,7),4)
    p.put(1,1,2,'minecraft:loom',facing='east',role='actual small mending loom');p.counter(1,1,4,'east',role='repair and stitching counter')
    p.put(1,2,4,'farmersdelight:cutting_board',facing='east',waterlogged=False,role='real cloth-repair cutting surface');p.shelf(2,2,1,'south',books=True)
    p.table(2,1,6,'east');p.put(6,1,5,'minecraft:smoker',facing='south',lit=False,role='real tiny tea and supper hearth')
    p.counter(7,1,5,'south',role='tea-making counter');p.put(7,2,5,'handcrafted:wood_cup',facing='south',pieces=3,waterlogged=False,role='cups ready for ordinary supper')
    p.put(7,1,7,'farmersdelight:dark_oak_cabinet',facing='north',open=False,role='new native-default tea and linen cabinet');p.put(6,1,9,POTS[0],role='contained plumeria in the sheltered working nook')
    light(p,3,3,4,'small warm mending-room lamp');upper_home(p,bed=(2,4),desk=(2,7),chair=(3,7),chair_face='west',hearth=(2,6),pantry=(3,6),table=(3,3),standing=(4,6),title='Mender’s tucked upper home')
    p.room('Tea, stitching and sheltered nook',0,(4,1,6),'A real loom/cutting bench and little tea hearth face separate cozy seating and contained courtyard flowers.')
    door(p,4,0,'north');p.sign(6,3,4,'north',['Mugs & Mending','Tea • Repairs']);p.put(6,3,5,'minecraft:dark_oak_planks')
    return p


def gull_tackle(registry):
    """East low tackle shop and a narrower rear fisher’s sleeping loft."""
    m=rect(0,0,7,8)-{(0,0),(0,1),(7,0),(7,8)};u=rect(0,1,4,7)|{(1,8),(2,8),(3,8)}
    p=base(registry,'Gull Tackle & Twine',m,u,up='minecraft:green_terracotta')
    p.roof((-1,0,5,9),8,(0,1,2,3,2,1,0),family='dark_oak',hip_south=True)
    p.roof((4,-1,8,8),4,(0,1,2,1,0),family='spruce',annex=True)
    routes(p,'Gull Tackle',[(3,z)for z in range(2,8)]+[(x,7)for x in range(3,8)],[(3,z)for z in range(2,7)]+[(2,5)],stairs=(4,6))
    window(p,7,1,2,'east',width=3,height=2);window(p,0,1,3,'west',width=2);bay_south(p,1,8)
    window(p,0,5,3,'west',width=2);joists(p,1,3,(3,6));joists(p,1,3,(3,6),4)
    p.counter(1,1,3,'east',role='tackle and twine packing bench');p.put(1,2,3,'farmersdelight:cutting_board',facing='east',waterlogged=False,role='actual cork and line cutting board')
    p.put(1,1,2,'minecraft:barrel',facing='up',open=False,role='new native-default tackle supplies');p.put(2,1,2,'minecraft:crafting_table',role='real hook and float fitting station')
    p.put(6,1,2,'minecraft:water_cauldron',level=3,role='contained tackle-rinsing water');p.shelf(5,2,6,'north',books=True)
    p.put(1,1,6,'handcrafted:dark_oak_chair',facing='east',color='brown',waterlogged=False,role='angler’s waiting/repair chair');p.put(6,1,6,POTS[7],role='contained blue orchid by the low work window')
    light(p,2,3,4,'small tackle-work lantern');upper_home(p,bed=(1,4),desk=(1,6),chair=(2,6),chair_face='west',hearth=(1,7),pantry=(2,7),table=(2,2),standing=(3,5),title='Fisher’s sheltered sleeping loft')
    p.room('Low tackle packing and fitting shop',0,(3,1,5),'Real fitting/cutting tools, counter, rinsing water, order shelves and an angler’s working seat.')
    door(p,7,7,'east');p.sign(8,3,5,'east',['Gull Tackle','Twine • Fittings']);p.put(7,3,5,'minecraft:dark_oak_planks')
    return p


RECIPES={'gullwatch':gullwatch,'tideglass':tideglass,'needlewake':needlewake,
         'netmender':netmender,'lost-tide':lost_tide,'kettle-bend':kettle_bend,
         'briny-hearth':briny_hearth,'quarter-tide':quarter_tide,'moon-rigging':moon_rigging,
         'keel-quill':keel_quill,'mugs-mending':mugs_mending,'gull-tackle':gull_tackle}


def thimble_salt(registry):
    """A genuinely smaller hooked seamstress home beside the broad glass shop.

The door is recessed INSIDE the six-wide body so its real porch cheeks never
pinch the shared two-wide lane. A little occupied west oriel hangs above it.
"""
    m=rect(0,0,5,7)-{(0,0),(0,1),(5,0)}
    p=base(registry,'Thimble & Salt',m,m,panel='minecraft:gray_terracotta',up='minecraft:brown_terracotta')
    p.roof((-1,-1,6,8),8,(0,1,2,3,3,2,1,0),family='dark_oak')
    routes(p,'Thimble and Salt',[(3,z)for z in range(2,7)]+[(x,5)for x in range(0,4)],[(3,z)for z in range(2,7)],stairs=(4,6))
    window(p,5,1,2,'east',width=2,height=2);window(p,1,1,7,'south',width=2,height=2)
    side_bay(p,-1,2,'west');window(p,1,5,7,'south',width=2);joists(p,1,3,(2,6));joists(p,1,3,(2,6),4)
    p.put(1,1,2,'minecraft:loom',facing='east',role='real compact cloth and sail-repair loom')
    p.put(2,1,2,'minecraft:crafting_table',role='actual needleworker fitting table');p.put(2,2,2,POTS[0],role='contained pale shop flower on the real table')
    p.counter(1,1,4,'east',role='compact stitching and fitting counter');p.put(1,2,4,'farmersdelight:cutting_board',facing='east',waterlogged=False,role='real stitching-work cutting board')
    p.put(1,1,6,'farmersdelight:dark_oak_cabinet',facing='north',open=False,role='new native-default cloth and tool cabinet');p.shelf(1,2,6,'north',books=True)
    light(p,2,3,3,'warm close tailoring task lantern');upper_home(p,bed=(1,4),desk=(2,6),chair=(1,6),hearth=(1,2),pantry=(2,2),table=(2,4),standing=(3,5),title='Seamstress’s small oriel home')
    # One-block-deep actual recess, full floor and cheek framing remain inside
    # the main outline; the lane receives no low post, stair or planter.
    for z in(4,6):
        for y in(1,2,3):p.put(0,y,z,'dawnoftimebuilder:charred_spruce_timber_frame_pillar',axis='y',role='contained grounded recessed-entry cheek')
        p.put(-1,3,z,'mythrais:curved_corbel_dark_oak',facing='west',shape=0,role='small high porch-recess carving')
    for z in range(4,7):p.beam(0,4,z,'z',wood='dark_oak',role='actual recessed-entry lintel')
    for y,half in((1,'lower'),(2,'upper')):p.put(1,y,5,'mcwdoors:dark_oak_cottage_door',facing='east',half=half,hinge='left',open=False,powered=False)
    p.entries.append({'owner':p.owner,'door':[1,1,5],'outward':'west','outside_step':[0,0,5]})
    p.sign(-1,3,1,'west',['Thimble & Salt','Cloth • Repairs']);p.put(0,3,1,'minecraft:dark_oak_planks')
    p.room('Compact cloth and sail-repair room',0,(3,1,5),'Real loom, fitting/cutting tools and native-default cloth cabinet in a warm little shop with a fully recessed door.')
    return p


RECIPES['thimble-salt']=thimble_salt


def check(p):
    material=require_material_rule(p.blocks,p.owner+' — complete floors/roofs/interior')
    for entry in p.entries:
        x,y,z=entry['door']
        for dy,half in((0,'lower'),(1,'upper')):
            s=p.blocks.get((x,y+dy,z),AIR)
            if not key(s).endswith('_door')or'half='+half not in s:raise UserError('Both actual native door halves must survive')
    for route in p.routes:
        for x,y,z in route['positions']:
            if route['kind']=='stairs':continue
            for h in(0,1):
                s=p.blocks.get((x,y+h,z),AIR)
                if s!=AIR and not key(s).endswith('_door'):raise UserError('Real walking passage obstructed: '+str((p.owner,route['id'],x,y+h,z,s)))
            if p.blocks.get((x,y-1,z),AIR)==AIR:raise UserError('Walking point lacks literal floor: '+str((p.owner,x,y,z)))
    for row in p.supports:
        if p.blocks.get(tuple(row['support']),AIR)==AIR:raise UserError('Projection or light lacks its actual authored support: '+str((p.owner,row)))
    floor_objects={'minecraft:smoker','minecraft:furnace','minecraft:barrel','minecraft:crafting_table','minecraft:cartography_table','minecraft:water_cauldron','minecraft:lectern','minecraft:loom','minecraft:stonecutter','minecraft:jukebox'}
    for q,s in p.blocks.items():
        x,y,z=q
        ident=key(s)
        floor_fixture=ident in floor_objects or ident.endswith('_bed')or ident.startswith(('handcrafted:','farmersdelight:'))and not any(word in ident for word in('shelf','shelves','stackable_book','bowl','cup','cutting_board'))
        if floor_fixture and y in(1,5,9)and y//4<len(p.levels[p.owner])and(x,z)in edge(p.levels[p.owner][y//4]):raise UserError('Furnish the real interior; do not replace a shell wall with floor furniture: '+str((p.owner,q,s)))
        if key(s).startswith(('minecraft:potted_','fishofthieves:potted_'))and p.blocks.get((x,y-1,z),AIR)==AIR:raise UserError('Contained plant lacks its literal sill/floor')
        if ident.endswith('_wall_sign'):
            face=next(value.split('=',1)[1]for value in s.split('[',1)[1][:-1].split(',')if value.startswith('facing='));dx,dz=VEC[face]
            if p.blocks.get((x-dx,y,z-dz),AIR)==AIR:raise UserError('A trade sign requires its actual authored wall/post')
    for room in p.rooms:
        x,y,z=room['standing_point']
        if any(p.blocks.get((x,y+h,z),AIR)!=AIR for h in(0,1))or p.blocks.get((x,y-1,z),AIR)==AIR:raise UserError('The actual furnished scene needs a real clear supported visiting point')
    canonical_joins(p)
    if not p.entries or len(p.rooms)<2:raise UserError('A real entry and at least two useful furnished scenes are required')
    return {'name':p.owner,'targets':len(p.blocks),'main_columns':len(p.main[p.owner]),'rooms':len(p.rooms),'storeys':len(p.levels[p.owner]),
            'surviving_purposeful_objects':len({tuple(r['position'])for r in p.props if key(p.blocks.get(tuple(r['position']),AIR))==r['block']}),
            'material':material,'source_only':True,'native_visual_walk_survival_acceptance':'PENDING'}
