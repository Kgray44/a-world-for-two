"""Authored north-bank extension: measured dry land before any placement.

Read-only saved terrain and original source geometry. Native placement, visual
review, shop residents and acceptance belong to a separate parent-owned stage.
The blue screenshot defines intent; its pixels never become world coordinates.
"""
from __future__ import annotations
import argparse
from collections import Counter,OrderedDict,deque
from dataclasses import dataclass
import hashlib,json,time
from pathlib import Path

from control_room.common import UserError,digest,read_json,utcnow
from tools.artistic_south_extent import ExtentTerrain
from tools.artistic_south_forest import AIR,SOFT,GROUND,is_tree
from tools.artistic_bridge_refinement import flatten
from tools.artistic_maritime_depth import BASES as MARITIME_BASES
from tools.artistic_pirate_spit import RESERVATIONS
from tools.artistic_materials import require_material_rule,require_outdoor_rule
from tools.artistic_mill_detail import joined_window_part
from tools.artistic_neighborhood_roofs import ridge_part
from tools.settlement_attractions import properties
from tools.playtest import guard
from tools.settlement_attractions import BackupWorld,base

MIB=1024**2
NORTH_REGIONS=((1,-3),(2,-3))
STUDY=(960,-1392,1456,-1120)
MAX_SAMPLES=9000
MAX_SECONDS=180
MAX_RAW=128*MIB
MAX_OUTPUT=16*MIB
EAST_STUDY=(1217,-1296,1392,-1120)
NORTH_SOFT={'farm_and_charm:wild_strawberries','farm_and_charm:wild_tomatoes',
            'vinery:red_grape_bush','vinery:white_grape_bush','supplementaries:barnacles'}
SIGNAL=('staging/neighborhood-canonical-ridges-20261027T1852Z/signal-canonical-full-VERIFY-ONLY.json','89df5767701762039fc37e8803509ea5e3862512a35a64f52e9add8cf8f57139')
BRIDGE=('staging/bridge-tower-native-settle-20261027T1823Z/full-verification.json','5500bf6e11c36d4b0dca9bcdeac555b3bf9b600db8763c80d091c1e0194317b0')


class NorthTerrain(ExtentTerrain):
    """Exactly two authenticated region members and four decoded chunks."""
    def __init__(self,home,receipt,registry):
        self.snapshot=BackupWorld(home,receipt,registry);self.key=None;self.blocks={};self.entities=set();self.unknown={};self.cache=OrderedDict();self.columns=OrderedDict()
        self.statuses={};self.decoded=0;self.started=time.monotonic();self.raw_bytes=0
        records=[]
        for rx,rz in NORTH_REGIONS:
            name=self.snapshot.prefix+f'r.{rx}.{rz}.mca';row=self.snapshot.files.get(name)
            if not row or not 8192<=row['size']<=MAX_RAW or self.snapshot.archive.getinfo(name).file_size!=row['size']:raise UserError('Exact finite saved north-shore MCA member required')
            records.append(((rx,rz),name,row))
        if sum(row['size'] for _,_,row in records)>MAX_RAW:raise UserError('North-shore128MiB raw region limit exceeded')
        for key,name,row in records:
            raw=self.snapshot.archive.read(name)
            if hashlib.sha256(raw).hexdigest()!=row['sha256']:raise UserError('Immutable north-shore region digest differs')
            self.snapshot.regions[key]=raw;self.raw_bytes+=len(raw);self.snapshot.sources.append({'file':Path(name).name,'sha256':row['sha256'],'bytes':len(raw),'role':'Exact stopped north-shore surface study; never live region'})
    def chunk(self,cx,cz):
        if (cx//32,cz//32) not in NORTH_REGIONS:return None
        return super().chunk(cx,cz)
    def check(self):
        if time.monotonic()-self.started>MAX_SECONDS:raise UserError('Finite saved north-bank study expired; no generation/retry fallback')
    def _column(self,x,z):
        row=super()._column(x,z)
        if row['kind']!='retained_object' or base(row['state']) not in NORTH_SOFT or 'waterlogged=true' in row['state']:return row
        plants=[];y=row['surface_y']
        for _ in range(4):
            current=self.state(x,y,z)
            if current is None:return row
            if base(current) in NORTH_SOFT and 'waterlogged=true' not in current and (x,y,z) not in self.entities:plants.append({'position':[x,y,z],'state':current});y-=1;continue
            if base(current) in GROUND and plants:return dict(row,kind='dry',surface_y=y,state=current,ordinary_natural_soft_cover=plants)
            return row
        return row


def measured_land(terrain,bounds=STUDY,step=4):
    if bounds!=STUDY or step!=4:raise UserError('A different screenshot study envelope requires an explicit bounded source revision')
    x0,z0,x1,z1=bounds;rows=[]
    for cx in range(x0//16,x1//16+1):
        for cz in range(z0//16,z1//16+1):
            for x in range(max(x0,cx*16),min(x1,cx*16+15)+1,step):
                for z in range(max(z0,cz*16),min(z1,cz*16+15)+1,step):
                    rows.append(terrain.column(x,z))
                    if len(rows)>MAX_SAMPLES:raise UserError('Finite measured-land sample cap exceeded')
            terrain.check()
    return {'format':'awft-measured-north-shore:1','bounds':list(bounds),'step':step,'samples':rows,
            'counts':dict(Counter(r['kind'] for r in rows)),'unknown_chunks':[[*k,v] for k,v in sorted(terrain.unknown.items())],
            'saved_BEs':[list(p) for p in sorted(terrain.entities)],'sources':terrain.snapshot.sources,
            'raw_MCA_bytes':terrain.raw_bytes,'full_status_counts':dict(Counter(terrain.statuses.values())),
            'authority':'Measurement only; no lot authority from sparse samples, retained objects, water or unknown chunks'}


def dry_footprint(terrain,cells,protected=(),*,max_relief=2):
    """Every main-building column dry/FULL; no screenshot interpolation or infill."""
    protected=set(protected);witness=[]
    if not cells or len(cells)>400:raise UserError('Finite original building outline required')
    for x,z in sorted(cells):
        if (x,z) in protected:raise UserError('Preserve authored land/clearance: '+str((x,z)))
        row=terrain.column(x,z)
        if row['kind']!='dry' or base(row['state']) not in GROUND:raise UserError('Main building would touch water, unknown or retained object: '+str((x,z)))
        if any(p[0]==x and p[2]==z and row['surface_y']-1<=p[1]<=105 for p in terrain.entities):raise UserError('Preserve saved block entity inside the complete proposed foundation/body/roof envelope: '+str((x,z)))
        witness.append({'support':[x,row['surface_y'],z],'state':row['state']})
    heights=[r['support'][1] for r in witness]
    if max(heights)-min(heights)>max_relief:raise UserError('Relocate/terrace the plot rather than flatten its landform')
    return {'actual_dry_columns':witness,'support_y_range':[min(heights),max(heights)],'floor_y':max(heights)+1,
            'status':'Exact saved dry main outline only; complete above-ground preimage, clearances, art and native acceptance still required'}


def preservation(home,registry):
    """Raw authored AIR/solids/BEs plus a one-metre native-model edge skirt."""
    home=Path(home);columns=set();sources=[]
    references=[('Signal Lane',*SIGNAL),('bascule and control towers',*BRIDGE)]
    references.extend((name,relative,sha) for name,(relative,sha) in MARITIME_BASES.items() if name!='flagship')
    for name,relative,sha in references:
        path=home/relative
        if not 0<path.stat().st_size<=4*MIB or digest(path)!=sha:raise UserError('Exact accepted source geometry required: '+name)
        document=read_json(path);document=document.get('physical_plan',document)
        if str(document['seed'])!=str(registry['seed']) or document['world_path']!=registry['world_path']:raise UserError('Accepted source belongs to another world')
        cells=flatten(document);field={(x,z) for x,y,z in cells}
        field.update((row['pos'][0],row['pos'][2]) for row in document.get('block_entities',[]))
        columns.update(field);sources.append({'name':name,'relative':relative,'sha256':sha,'columns':len(field),'protection':'All addressed AIR/solids/BEs, not only roof/lot rectangles'})
    # Exact original imported works have separate parent-owned source custody.
    # Preserve complete existing bounds, not copied replacement geometry.
    for row in RESERVATIONS:
        x0,z0,x1,z1=row['bounds'];columns.update((x,z) for x in range(x0,x1+1) for z in range(z0,z1+1))
    # The actual narrow connector can have several immutable preimage revisions.
    # All bounded authored copies are conservative keep-outs, never acceptance.
    roads=list((home/'staging').glob('*/north-harbor-walk-*.json'))
    if len(roads)>16:raise UserError('Review exact current north-grounds custody before extending')
    for path in roads:
        if not 0<path.stat().st_size<=MIB:raise UserError('Bounded connector source required')
        document=read_json(path)
        if str(document['seed'])!=str(registry['seed']) or document['world_path']!=registry['world_path']:raise UserError('Connector source world differs')
        field={(x,z) for x,y,z in flatten(document)};columns.update(field)
        sources.append({'name':'retained north harbor connector','relative':path.relative_to(home).as_posix(),'sha256':digest(path),'columns':len(field),'protection':'conservative existing path/AIR keep-out'})
    skirt={(x+dx,z+dz) for x,z in columns for dx in (-1,0,1) for dz in (-1,0,1)}
    return skirt,sources


def fine_eastern_land(home,checkpoint_id,checkpoint_sha):
    """Every saved surface column in a finite eastern study, still no lot edits."""
    home=Path(home).resolve();reserve=guard(2*MIB,MAX_OUTPUT)
    current=read_json(home/'dashboard/settlement/backup-receipt.json')
    if current.get('verified') is not True or current.get('id')!=checkpoint_id or current.get('sha256')!=checkpoint_sha:raise UserError('Exact current stopped private checkpoint required')
    registry=read_json(home/'dashboard/settlement/registry.json');protected,provenance=preservation(home,registry)
    terrain=NorthTerrain(home,current,registry);x0,z0,x1,z1=EAST_STUDY;rows=[]
    try:
        for cx in range(x0//16,x1//16+1):
            for cz in range(z0//16,z1//16+1):
                for x in range(max(x0,cx*16),min(x1,cx*16+15)+1):
                    for z in range(max(z0,cz*16),min(z1,cz*16+15)+1):
                        row=terrain.column(x,z);rows.append(dict(row,authored_keepout=(x,z) in protected))
                        if len(rows)>32_000:raise UserError('Finite32k eastern surface field exceeded')
                terrain.check()
        sources=terrain.snapshot.sources;entities=terrain.entities.copy();raw_bytes=terrain.raw_bytes
    finally:terrain.close()
    data={'format':'awft-fine-eastern-north-bank-land:1','checkpoint_id':checkpoint_id,'checkpoint_sha256':checkpoint_sha,
          'bounds':list(EAST_STUDY),'step':1,'samples':rows,'protected_columns_xz':[list(p) for p in sorted(protected) if x0-2<=p[0]<=x1+2 and z0-2<=p[1]<=z1+2],
          'accepted_source_custody':provenance,'saved_BEs':[list(p) for p in sorted(entities)],'sources':sources,'counts':dict(Counter(r['kind'] for r in rows)),
          'actual_dry_unreserved_columns':sum(r['kind']=='dry' and not r['authored_keepout'] for r in rows),
          'raw_MCA_bytes':raw_bytes,'source_sha256':digest(Path(__file__)),'native_actions':0,'world_writes':0,
          'limitations':['Exact saved surface only; full solid/air building envelope and per-lot support/BEs still required','North/east outer screenshot limit is composition intent, not a sampled rectangle authority','All authored geometry/AIR/models retained, river water and unknown remain forbidden main footprints']}
    raw=(json.dumps(data,separators=(',',':'))+'\n').encode()
    if len(raw)>MAX_OUTPUT:raise UserError('Finite eastern field output exceeded')
    output=home/'staging'/('north-bank-eastern-fine-'+str(time.time_ns()));output.mkdir();(output/'fine-land.json').write_bytes(raw)
    return {'folder':str(output),'sha256':hashlib.sha256(raw).hexdigest(),'columns':len(rows),'dry_unreserved_columns':data['actual_dry_unreserved_columns'],'counts':data['counts'],'native_actions':0}


@dataclass(frozen=True)
class Lot:
    ident:str
    name:str
    trade:str
    center:tuple
    size:tuple
    levels:int
    face:str
    outline:str
    roof:str
    finish:tuple
    rooms:tuple
    motif:str


# Each first-quarter house is a separate authored composition. These are not
# randomized styles, rows of cloned shells or an automatic settlement factory.
ROSE_REACH=(
    Lot('compass','The Gilded Compass','Navigator and chartmaker',(1298,-1252),(9,11),3,'south','cropped_sw','cross_gable',
        ('minecraft:bricks','minecraft:white_terracotta','dawnoftimebuilder:blue_plastered_stone'),
        ('Chart counter and instrument repair','Window chart library, tea and household kitchen','Navigator bedroom and roof desk'),
        'A cut-corner brick foot, two-level projecting chart bay, narrow cross-gable and brass globe corner'),
    Lot('pepper','Pepper & Marigold','Spice merchant and household',(1311,-1252),(9,11),3,'south','recess_se','gambrel',
        ('minecraft:stone_bricks','dawnoftimebuilder:yellow_plastered_stone','minecraft:green_terracotta'),
        ('Spice jars and wrapped-goods counter','Domestic hearth, pantry and dining nook','Spice merchant bedroom and linen chest'),
        'An amber gambrel, recessed service corner, green upper bedroom and small herb-window balcony'),
    Lot('coppersmith','Cinder & Pearl','Copperware and small jewelry workshop',(1326,-1252),(9,11),2,'south','cropped_ne','half_hip',
        ('minecraft:bricks','dawnoftimebuilder:red_plastered_stone'),
        ('Copper workbench, display and seated customer corner','Warm artisan apartment and sewing alcove'),
        'A low half-hip with a little dormer, copper-filled work window and carved double jambs'),
    Lot('post','The Flying Post','Harbor letters and courier lodging',(1340,-1243),(9,13),3,'west','recess_nw','steep',
        ('minecraft:stone_bricks','minecraft:cyan_terracotta','dawnoftimebuilder:plastered_stone'),
        ('Parcel counter, letter sorting and quiet public bench','Courier kitchen, charts and shared lounge','Two sleeping nooks and a writing desk'),
        'A west-facing bent-street landmark, steep gable, narrow projecting postal bay and parcel porch'),
    Lot('tea','The Lantern Lark','Tea room and music salon',(1296,-1233),(9,11),2,'north','cropped_nw','saltbox',
        ('minecraft:bricks','dawnoftimebuilder:green_plastered_stone'),
        ('Tea counter, little tables and fireside music seat','Owner apartment with window dining and a daybed'),
        'A tucked-in entrance, asymmetric roof, planted rear bay and several intimate seated corners'),
    Lot('outfitter','Morrow’s Thread','Mariner clothing and canvas goods',(1311,-1233),(9,11),3,'north','recess_sw','cross_gable',
        ('minecraft:stone_bricks','minecraft:yellow_terracotta','minecraft:white_terracotta'),
        ('Cloth counter, fittings and folded clothing display','Tailoring room with cutting bench and domestic pantry','Family beds, travel trunks and a reading seat'),
        'A narrow stepped jetty, paired cloth-window arches and separate older roof over the cutting-room bay'),
    Lot('curios','The Reef Curio','Antiquarian and sea discoveries',(1326,-1233),(9,11),3,'north','cropped_se','steep',
        ('minecraft:bricks','dawnoftimebuilder:blue_plastered_stone','minecraft:light_gray_terracotta'),
        ('Sea curios, books and supervised artifact counter','Collector salon, small kitchen and window shelves','Collector bedroom and attic chart table'),
        'A blue angled corner bay, very narrow attic and illuminated curios behind actual framed windows'),
)

FACES={'north':(0,-1),'south':(0,1),'west':(-1,0),'east':(1,0)}
FLOOR_BOARDS=('minecraft:spruce_planks','minecraft:oak_planks','minecraft:dark_oak_planks')


def outline(lot):
    w,d=lot.size;x0,z0=lot.center[0]-w//2,lot.center[1]-d//2
    cells={(x,z) for x in range(x0,x0+w) for z in range(z0,z0+d)}
    corners={'sw':(x0,z0+d-1,1,-1),'se':(x0+w-1,z0+d-1,-1,-1),
             'nw':(x0,z0,1,1),'ne':(x0+w-1,z0,-1,1)}
    corner=lot.outline.rsplit('_',1)[-1];x,z,dx,dz=corners[corner]
    cut={(x,z),(x+dx,z),(x,z+dz)} if lot.outline.startswith('cropped') else {(x+i*dx,z+j*dz) for i in range(2) for j in range(2)}
    return cells-cut


def boundary(cells):return {p for p in cells if any((p[0]+dx,p[1]+dz) not in cells for dx,dz in FACES.values())}


class EastPlan:
    def __init__(self,registry,fine):
        self.registry=registry;self.fine=fine;self.land={(r['x'],r['z']):r for r in fine['samples']};self.protected=set(map(tuple,fine['protected_columns_xz']))
        self.saved_BEs=set(map(tuple,fine['saved_BEs']));self.blocks={};self.tags={};self.priority={};self.owners={};self.group='lane';self.rooms=[];self.lots=[];self.fixtures=[];self.supports=[];self.walk=[];self.cameras=[];self.cache={}
        self.lava={(r['x'],r['z']) for r in fine['samples'] if base(r.get('state',''))=='minecraft:lava'}
    def state(self,key,**props):
        native=self.registry['blocks'].get(key)
        if native is None:raise UserError('Unregistered actual palette '+key)
        for k,v in props.items():
            if str(v).lower() not in native.get(k,()):raise UserError('Unregistered native state '+key+' '+k+'='+str(v))
        return key+('['+','.join(k+'='+str(v).lower() for k,v in sorted(props.items()))+']' if props else '')
    def put(self,p,key,*,priority=50,**props):
        p=tuple(p);x,y,z=p
        if not EAST_STUDY[0]<=x<=EAST_STUDY[2] or not EAST_STUDY[1]<=z<=EAST_STUDY[3] or not 59<=y<=105:raise UserError('Original extension escaped its reviewed finite reserve')
        if (x,z) in self.protected or p in self.saved_BEs:raise UserError('Preserve accepted architecture/AIR/model or saved BE: '+str(p))
        if priority<self.priority.get(p,-1):return
        value=self.state(key,**props);previous=self.blocks.get(p)
        if previous is not None and previous!='minecraft:air' and value!='minecraft:air' and self.owners.get(p)!=self.group and previous!=value:raise UserError('Two authored lots collide: '+str(p))
        self.blocks[p]=value;self.priority[p]=priority;self.owners[p]=self.group;self.tags.pop(p,None)
        if len(self.blocks)>250_000:raise UserError('Split north-bank quarter at its finite250k positions')
    def floor(self,cells,y,wood='spruce'):
        x0=min(x for x,z in cells);z0=min(z for x,z in cells)
        for x,z in cells:
            # Genuine joists and transverse construction bays, not colored noise.
            key=('minecraft:dark_oak_planks' if (x-x0)%4==0 else 'minecraft:'+wood+'_planks')
            if (z-z0)%8==7:key='minecraft:polished_andesite' if (x-x0)%4==0 else 'minecraft:stripped_oak_wood'
            self.put((x,y,z),key,priority=55,**({'axis':'x'} if key.endswith('_wood') else {}))
    def fixture(self,p,key,*,support=None,**props):
        if tuple(p) in self.walk or self.priority.get(tuple(p),0)>90:raise UserError('Furnishing would obstruct an authored route/stair: '+str((p,key)))
        if support is not None:
            q=tuple(support);row=self.land.get((q[0],q[2]),{});under=self.blocks.get(q,row.get('state','minecraft:air') if row.get('surface_y')==q[1] else 'minecraft:air')
            if base(under) in AIR:raise UserError('Unsupported authored furnishing '+str((p,key)))
        self.put(p,key,priority=90,**props);self.fixtures.append({'room':self.group,'position':list(p),'block':key})
        if support is not None:self.supports.append({'fixture':list(p),'support':list(support)})
    def display(self,p,item,title,face):
        if item not in self.registry['items']:raise UserError('Unknown real display item '+item)
        self.fixture(p,'supplementaries:item_shelf',facing=face,waterlogged=False)
        self.tags[tuple(p)]='{CustomName:'+json.dumps(json.dumps({'text':title}))+',Items:[{Slot:0b,id:'+json.dumps(item)+',count:1}]}'
    def text(self,p,lines,face):
        self.put(p,'minecraft:spruce_wall_sign',priority=95,facing=face,waterlogged=False)
        messages=[json.dumps(json.dumps({'text':v,'color':'black'})) for v in (list(lines)+['']*4)[:4]]
        self.tags[tuple(p)]='{is_waxed:1b,front_text:{messages:['+','.join(messages)+'],color:"black",has_glowing_text:0b}}'


def qualify_lot(p,lot):
    cells=outline(lot);perimeter={(x+dx,z+dz) for x,z in cells for dx in (-1,0,1) for dz in (-1,0,1)}
    proof=dry_footprint(type('SavedField',(),{'entities':p.saved_BEs,'column':lambda _,x,z:p.land.get((x,z),{'kind':'unknown'})})(),perimeter,p.protected)
    if any(max(abs(x-a),abs(z-b))<8 for x,z in perimeter for a,b in p.lava):raise UserError('Keep flammable architecture eight metres from retained native lava')
    return cells,proof


def facade_windows(p,lot,cells,f,level):
    minx,maxx=min(x for x,z in cells),max(x for x,z in cells);minz,maxz=min(z for x,z in cells),max(z for x,z in cells)
    faces=('north','south','west','east')
    for face in faces:
        dx,dz=FACES[face];along=sorted({x if dz else z for x,z in cells})
        for a in (along[2],along[-4]):
            run=[(x,z) for x,z in cells if (x if dz else z)==a];q=(max(run,key=lambda q:q[1]) if face=='south' else min(run,key=lambda q:q[1]) if face=='north' else min(run) if face=='west' else max(run))
            x,z=q;t=(1,0) if dz else (0,1)
            for u in (0,1):
                xx,zz=x+t[0]*u,z+t[1]*u
                if (xx,zz) not in boundary(cells):continue
                for dy in (2,3):p.put((xx,f+dy,zz),'mcwwindows:dark_oak_plank_window',priority=75,facing='north' if dz else 'east',part='base')
    # A small supported upper oriel creates real recess/projection and shade;
    # low shopfronts stay open rather than gaining a hulking solid overhang.
    if level==1:
        face=lot.face;dx,dz=FACES[face];t=(1,0) if dz else (0,1)
        x,z=(lot.center[0],maxz) if face=='south' else (lot.center[0],minz) if face=='north' else (minx,lot.center[1]) if face=='west' else (maxx,lot.center[1])
        for u in (-1,0,1):
            xx,zz=x+t[0]*u+dx,z+t[1]*u+dz
            p.put((xx,f+1,zz),'minecraft:dark_oak_slab',priority=80,type='top',waterlogged=False)
            p.put((xx,f,zz),'mythrais:small_curved_corbel_dark_oak',priority=80,facing=face,shape=0)
            if u<1:
                for dy in (2,3):p.put((xx,f+dy,zz),'mcwwindows:dark_oak_plank_window',priority=80,facing='north' if dz else 'east',part='base')
            else:
                for dy in (2,3):p.put((xx,f+dy,zz),'minecraft:stripped_dark_oak_log',priority=80,axis='y')
            p.put((xx,f+4,zz),'dawnoftimebuilder:spruce_support_slab',priority=80,pillar_connection='nothing',waterlogged=False)


def house_shell(p,lot):
    cells,proof=qualify_lot(p,lot);p.group=lot.name;floor=proof['floor_y'];w,d=lot.size
    x0=min(x for x,z in cells);z0=min(z for x,z in cells);maxx=max(x for x,z in cells);maxz=max(z for x,z in cells)
    skirt={(x+dx,z+dz) for x,z in cells for dx in (-1,0,1) for dz in (-1,0,1)}
    for x,z in skirt:
        for y in range(floor,floor+lot.levels*4+8):p.put((x,y,z),'minecraft:air',priority=10)
    for x,z in cells:
        ground=p.land[x,z]['surface_y']
        for y in range(ground-1,floor):
            material='minecraft:stone_bricks' if (x-x0)%4 else 'minecraft:polished_andesite'
            if (z-z0)%8==7:material='minecraft:mossy_stone_bricks' if (x-x0)%4 else 'minecraft:chiseled_stone_bricks'
            p.put((x,y,z),material,priority=35)
    outside=boundary(cells)
    for level in range(lot.levels):
        f=floor+4*level;p.floor(cells,f)
        for x,z in outside:
            for dy in (1,2,3):
                post=(x-x0)%3==0 if z in (z0,maxz) else (z-z0)%3==0
                p.put((x,f+dy,z),'minecraft:stripped_dark_oak_log' if post else lot.finish[level],priority=50,**({'axis':'y'} if post else {}))
            cap='minecraft:dark_oak_wood' if z in (z0,maxz) else 'minecraft:stripped_oak_wood' if (z-z0)%8==7 else 'minecraft:oak_wood'
            p.put((x,f+4,z),cap,priority=60,axis='x' if z in (z0,maxz) else 'z')
        facade_windows(p,lot,cells,f,level)
        p.rooms.append({'building':lot.ident,'level':level,'floor_y':f,'program':lot.rooms[level],'floor_cells':[list(q) for q in sorted(cells)]})
    p.floor(cells,floor+4*lot.levels)
    # Four three-block-high corner piers with carved feet and real stepped caps.
    for x,z in ((x0,z0),(maxx,z0),(x0,maxz),(maxx,maxz)):
        if (x,z) not in cells:continue
        p.put((x,floor,z),'minecraft:stone_brick_stairs',priority=85,facing='east' if x==x0 else 'west',half='bottom',shape='straight',waterlogged=False)
        for y in (floor+1,floor+2):p.put((x,y,z),'dawnoftimebuilder:chiseled_plastered_stone',priority=85)
    make_roof(p,lot,cells,floor+4*lot.levels)
    face=lot.face;dx,dz=FACES[face]
    door=(lot.center[0],maxz) if face=='south' else (lot.center[0],z0) if face=='north' else (x0,lot.center[1]) if face=='west' else (maxx,lot.center[1])
    for dy,half in ((1,'lower'),(2,'upper')):p.put((door[0],floor+dy,door[1]),'mcwdoors:dark_oak_cottage_door',priority=98,facing={'north':'south','south':'north','east':'west','west':'east'}[face],half=half,hinge='left',open=False,powered=False)
    p.walk.extend((x,floor+dy,z) for x,z in ((door[0]-dx,door[1]-dz),door,(door[0]+dx,door[1]+dz)) for dy in (1,2))
    sx,sz=door[0]+dx,door[1]+dz;p.text((sx,floor+3,sz),(lot.name,lot.trade[:21],'Rose Reach',''),face)
    tangent=(1,0) if dz else (0,1)
    for u in (-3,3,-2,2):
        back=(door[0]+tangent[0]*u,floor+3,door[1]+tangent[1]*u);key=base(p.blocks.get(back,'minecraft:air'))
        if key in (*lot.finish,'minecraft:stripped_dark_oak_log'):
            q=(back[0]+dx,back[1],back[2]+dz);p.fixture(q,'mcwlights:bell_wall_lantern',support=back,facing=face);break
    p.lots.append({'id':lot.ident,'name':lot.name,'trade':lot.trade,'floor_y':floor,'main_footprint':[list(q) for q in sorted(cells)],'dry_proof':proof,'front':face,'door':[door[0],floor+1,door[1]],'motif':lot.motif,'storeys':lot.levels})
    return cells,floor,door


def make_roof(p,lot,cells,base_y):
    x0,maxx=min(x for x,z in cells)-1,max(x for x,z in cells)+1;z0,maxz=min(z for x,z in cells)-1,max(z for x,z in cells)+1
    width=maxx-x0+1;half=width//2
    covering={'cross_gable':'dark_oak','gambrel':'bricks','half_hip':'brown_terracotta','steep':'deepslate','saltbox':'spruce'}[lot.roof]
    for x in range(x0,maxx+1):
        cross=x-x0;rise=min(cross,width-1-cross)
        if lot.roof=='gambrel':rise=min(5,rise+int(rise>1))
        if lot.roof=='saltbox' and cross>half:rise=max(0,rise-1)
        for z in range(z0,maxz+1):
            h=min(rise,min(z-z0,maxz-z)+1) if lot.roof=='half_hip' else rise
            material='stone_bricks' if (z-z0)%8==7 or lot.roof=='half_hip' and z in (z0,maxz) else covering
            if lot.roof=='steep':
                surface='bright_copper' if (z-z0)%8==7 else 'blue_slate' if lot.ident=='post' else 'moss_slate'
                if cross==half:p.put((x,base_y+2*h,z),'minecraft:waxed_cut_copper_slab' if surface=='bright_copper' else 'minecraft:stone_brick_slab',priority=45,type='bottom',waterlogged=False)
                else:
                    for dy,stem in ((0,'roof_low_straight_67_'),(1,'roof_up_67_')):p.put((x,base_y+2*h+dy,z),'mythrais:'+stem+surface,priority=45,facing='east' if cross<half else 'west',half='bottom',shape='straight',waterlogged=False)
            elif cross==half:p.put((x,base_y+h,z),'mcwroofs:'+material+'_top_roof',priority=45,part='switched_0')
            else:p.put((x,base_y+h,z),'mcwroofs:'+material+'_roof',priority=45,facing='east' if cross<half else 'west',half='bottom',shape='straight')
    for z in (z0+1,maxz-1):
        for x in range(x0+1,maxx):
            h=min(x-x0,maxx-x)*(2 if lot.roof=='steep' else 1)
            if lot.roof=='half_hip':h=min(h,min(z-z0,maxz-z)+1)
            for dy in range(h):
                if lot.roof=='steep' and dy in (3,7):p.put((x,base_y+dy,z),'dawnoftimebuilder:dark_oak_beam',priority=44,axis_x=True,axis_y=False,axis_z=False,bottom=True,waterlogged=False)
                else:p.put((x,base_y+dy,z),'minecraft:stripped_spruce_log' if (x-x0)%3==0 else lot.finish[-1],priority=44,**({'axis':'y'} if (x-x0)%3==0 else {}))
    # Small roof interruption, real chimney and coping, never an oversized tower.
    cx,cz=maxx-2,z0+3
    for y in range(base_y+1,base_y+5):p.put((cx,y,cz),'minecraft:bricks',priority=70)
    p.put((cx,base_y+5,cz),'minecraft:stone_brick_slab',priority=70,type='bottom',waterlogged=False)
    if lot.roof=='cross_gable':
        # A genuine transverse dormer/short gable; its roof plane changes axis.
        front=maxz if lot.face=='south' else z0;sign=-1 if lot.face=='south' else 1;xc=lot.center[0]-1
        for x in range(xc-2,xc+3):
            for n,h in enumerate((0,1,2,1,0)):
                z=front+sign*n;y=base_y+2+h
                if n==2:p.put((x,y,z),'mcwroofs:red_terracotta_top_roof',priority=76,part='switched_90')
                else:p.put((x,y,z),'mcwroofs:red_terracotta_roof',priority=76,facing='south' if n<2 else 'north',half='bottom',shape='straight')


TRADE_ITEMS={
    'compass':('minecraft:compass','minecraft:map','minecraft:spyglass','minecraft:paper'),
    'pepper':('minecraft:carrot','minecraft:potato','minecraft:bowl','minecraft:beetroot'),
    'coppersmith':('minecraft:copper_ingot','minecraft:gold_nugget','minecraft:amethyst_shard','minecraft:shears'),
    'post':('minecraft:paper','minecraft:book','minecraft:feather','minecraft:compass'),
    'tea':('minecraft:honey_bottle','minecraft:cookie','minecraft:apple','minecraft:bread'),
    'outfitter':('minecraft:shears','minecraft:string','minecraft:leather','minecraft:white_wool'),
    'curios':('minecraft:prismarine_crystals','minecraft:nautilus_shell','minecraft:book','minecraft:amethyst_shard')}


def furnished_rooms(p,lot,cells,floor,door):
    x0,x1=min(x for x,z in cells),max(x for x,z in cells);z0,z1=min(z for x,z in cells),max(z for x,z in cells)
    entry_z=z1-3;landing_z=entry_z-5
    # Native stairs and their real headroom are reserved before furniture.
    stairs=set()
    for level in range(lot.levels-1):
        f=floor+4*level
        for n in range(1,5):
            q=(x1-1,f+n,entry_z-n);p.put(q,'minecraft:spruce_stairs',priority=99,facing='north',half='bottom',shape='straight',waterlogged=False);stairs.add(q)
            for dy in (1,2,3):p.put((q[0],q[1]+dy,q[2]),'minecraft:air',priority=100)
        for z in (entry_z,landing_z):
            for dy in (1,2):p.walk.append((x1-1,f+dy+(4 if z==landing_z else 0),z))
    for level in range(lot.levels):
        f=floor+4*level;before=len(p.fixtures)
        # A small usable cross-room aisle and the stair approach remain open.
        aisle={(lot.center[0],z) for z in range(z0+1,z1)}
        if level<lot.levels-1:aisle|={(x,entry_z) for x in range(lot.center[0],x1)}
        if level>0:aisle|={(x,landing_z) for x in range(lot.center[0],x1)}
        if lot.face=='west':aisle|={(x,lot.center[1]) for x in range(x0+1,lot.center[0]+1)}
        for x,z in aisle:
            for dy in (1,2):p.walk.append((x,f+dy,z))
        # Sculpted ceiling bays stay in the upper half-block at three metres.
        for x in range(x0+1,x1):p.put((x,f+3,z0+4),'dawnoftimebuilder:spruce_beam',priority=74,axis_x=True,axis_y=False,axis_z=False,bottom=True,waterlogged=False)
        for z in range(z0+1,min(z1,z0+7)):p.put((lot.center[0]-1,f+3,z),'dawnoftimebuilder:spruce_support_slab',priority=75,pillar_connection='nothing',waterlogged=False)
        # Two compact furniture groups, not one empty table in a large room.
        tx,tz=x0+2,z0+3
        p.fixture((tx,f+1,tz),'handcrafted:spruce_table',support=(tx,f,tz),color='none',shape='single',waterlogged=False)
        p.fixture((tx,f+2,tz),'handcrafted:wood_cup',support=(tx,f+1,tz),facing='east',pieces=2,waterlogged=False)
        p.fixture((tx,f+1,tz+1),'handcrafted:spruce_chair',support=(tx,f,tz+1),facing='north',color='none',waterlogged=False)
        p.fixture((tx-1,f+1,tz),'handcrafted:spruce_chair',support=(tx-1,f,tz),facing='east',color='none',waterlogged=False)
        for z in (z0+4,z0+5):
            p.fixture((x0+1,f+1,z),'handcrafted:spruce_counter',support=(x0+1,f,z),facing='east',counter='dark_oak_planks',type='1')
        p.fixture((x0+1,f+2,z0+4),'handcrafted:berry_jam_jar',support=(x0+1,f+1,z0+4),facing='east',jars=2,waterlogged=False)
        p.fixture((x0+1,f+2,z0+5),'handcrafted:terracotta_thin_pot',support=(x0+1,f+1,z0+5))
        # Real wall displays are backed by actual authored solid wall cells.
        for n,z in enumerate((z0+4,z0+5,z0+6)):
            backing=(x0,f+2,z)
            if base(p.blocks.get(backing,'minecraft:air')) not in ('minecraft:stripped_dark_oak_log',*lot.finish):continue
            q=(x0+1,f+2,z)
            if q in {(x0+1,f+2,z0+4),(x0+1,f+2,z0+5)} or q in p.walk:continue
            p.display(q,TRADE_ITEMS[lot.ident][(n+level)%4],lot.name+' — '+lot.rooms[level], 'east')
        p.fixture((x0+1,f+3,z0+4),'mcwlights:bell_wall_lantern',support=(x0,f+3,z0+4),facing='east')
        for x,z,face,back in ((x1-1,z0+1,'west',(x1,f+3,z0+1)),(x0+1,z0+5,'east',(x0,f+3,z0+5))):
            q=(x,f+3,z)
            if q in p.walk or p.priority.get(q,0)>90 or base(p.blocks.get(back,'minecraft:air')) not in (*lot.finish,'minecraft:stripped_dark_oak_log'):continue
            p.fixture(q,'mcwlights:bell_wall_lantern',support=back,facing=face);break
        back=(lot.center[0],f+3,z0)
        if base(p.blocks.get(back,'minecraft:air')) in (*lot.finish,'minecraft:stripped_dark_oak_log'):
            p.display((lot.center[0],f+3,z0+1),TRADE_ITEMS[lot.ident][level%4],lot.name+' — overhead wall display','south')
        # A dedicated trade scene differs materially and spatially by building.
        if level==0:
            sx,sz=x1-2,z0+2
            workstation={'compass':'minecraft:cartography_table','pepper':'minecraft:crafting_table','coppersmith':'minecraft:smithing_table','post':'minecraft:lectern','tea':'minecraft:smoker','outfitter':'minecraft:loom','curios':'minecraft:chiseled_bookshelf'}[lot.ident]
            props={'facing':'west','has_book':False,'powered':False} if workstation=='minecraft:lectern' else {'facing':'west','lit':False} if workstation=='minecraft:smoker' else {'facing':'west'} if workstation in ('minecraft:loom','minecraft:chiseled_bookshelf') else {}
            p.fixture((sx,f+1,sz),workstation,support=(sx,f,sz),**props)
            p.fixture((sx,f+1,sz+3),'handcrafted:spruce_cupboard',support=(sx,f,sz+3),facing='west',type='1')
            if lot.ident=='compass':p.fixture((sx,f+2,sz+3),'supplementaries:globe',support=(sx,f+1,sz+3),facing='west',powered=False,rotation=0,waterlogged=False)
            elif lot.ident=='tea':p.fixture((sx,f+2,sz+3),'handcrafted:yellow_plate',support=(sx,f+1,sz+3),facing='west',pieces=3,waterlogged=False)
            else:p.fixture((sx,f+2,sz+3),'handcrafted:stackable_book',support=(sx,f+1,sz+3),books=3,facing='west',seed=level+1)
        else:
            bx,bz=x0+2,z0+7
            if bz+1<z1 and (bx,bz) not in aisle:
                for dz,part in ((0,'head'),(1,'foot')):p.fixture((bx,f+1,bz+dz),'handcrafted:spruce_fancy_bed',support=(bx,f,bz+dz),facing='north',part=part,occupied=False,shape='single',color='blue' if lot.ident in ('compass','post','curios') else 'green')
                p.fixture((bx+1,f+1,bz),'handcrafted:spruce_nightstand',support=(bx+1,f,bz),facing='south')
                p.fixture((bx+1,f+2,bz),'supplementaries:candle_holder',support=(bx+1,f+1,bz),candles=2,face='floor',facing='north',lit=True,waterlogged=False)
            p.fixture((x1-2,f+1,z0+3),'handcrafted:oak_desk',support=(x1-2,f,z0+3),facing='west',color='none',waterlogged=False)
            p.fixture((x1-2,f+2,z0+3),'handcrafted:stackable_book',support=(x1-2,f+1,z0+3),books=2,facing='west',seed=level+1)
            p.fixture((x1-2,f+1,z0+5),'handcrafted:spruce_couch',support=(x1-2,f,z0+5),facing='west',color='red',shape='single',waterlogged=False)
        p.rooms[-lot.levels+level]['furnishing_objects']=len(p.fixtures)-before
        p.rooms[-lot.levels+level]['circulation_reserved']=True


def canonical_parts(p):
    for pos,prior in list(p.blocks.items()):
        key=base(prior);fields=properties(prior);x,y,z=pos
        if key.startswith('mcwwindows:') and 'part' in fields:
            plane=fields['facing'];negative,positive=((x-1,y,z),(x+1,y,z)) if plane=='north' else ((x,y,z-1),(x,y,z+1))
            same=lambda q:base(p.blocks.get(q,'minecraft:air'))==key
            fields['part']=joined_window_part(same((x,y+1,z)),same((x,y-1,z)),same(negative),same(positive));p.blocks[pos]=p.state(key,**fields)
        elif key.startswith('mcwroofs:') and key.endswith('_top_roof'):
            same=lambda q:base(p.blocks.get(q,'minecraft:air'))==key
            fields['part']=ridge_part(same((x,y,z-1)),same((x+1,y,z)),same((x,y,z+1)),same((x-1,y,z)));p.blocks[pos]=p.state(key,**fields)


ROSE_LANE=((1292,-1240),(1292,-1241),(1298,-1242),(1304,-1243),(1311,-1242),(1318,-1241),(1326,-1242),(1332,-1242),(1334,-1240),(1333,-1234),(1334,-1227))


def pave(p,x,z):
    row=p.land.get((x,z))
    if row is None or row['kind']!='dry' or (x,z) in p.protected:raise UserError('The lane must follow actual dry unreserved land: '+str((x,z)))
    y=row['surface_y'];jointx=(x-1288)%8==7;jointz=(z+1243)%8==7
    key='minecraft:chiseled_stone_bricks' if jointx and jointz else 'minecraft:polished_andesite' if jointx else 'minecraft:mossy_cobblestone' if jointz else 'minecraft:cobblestone'
    p.put((x,y,z),key,priority=20)
    for dy in (1,2):p.put((x,y+dy,z),'minecraft:air',priority=20)
    return x,y,z


def rose_street(p):
    p.group='Rose Reach crooked lane';centers=[]
    for a,b in zip(ROSE_LANE,ROSE_LANE[1:]):
        distance=max(abs(b[0]-a[0]),abs(b[1]-a[1]))
        for n in range(distance+1):centers.append((round(a[0]+(b[0]-a[0])*n/max(1,distance)),round(a[1]+(b[1]-a[1])*n/max(1,distance))))
    columns={(x+dx,z+dz) for x,z in centers for dx in (-1,0,1) for dz in (-1,0,1)}
    for x,z in sorted(columns):
        q=pave(p,x,z)
        for dy in (1,2):p.walk.append((q[0],q[1]+dy,q[2]))
    for lot,row in zip(ROSE_REACH,p.lots):
        p.group=lot.name;dx,dz=FACES[lot.face];x,feet,z=row['door'];floor=feet-1
        outside=p.land[x+dx,z+dz]['surface_y'];rise=floor-outside
        if not 1<=rise<=3:raise UserError('The retained plot needs a separately authored stepped entrance')
        for n in range(1,rise+1):
            xx,zz=x+n*dx,z+n*dz;target=floor-n+1;ground=p.land[xx,zz]['surface_y']
            for y in range(ground+1,target):p.put((xx,y,zz),'minecraft:stone_bricks',priority=97)
            p.put((xx,target,zz),'minecraft:stone_brick_stairs',priority=98,facing={'north':'south','south':'north','east':'west','west':'east'}[lot.face],half='bottom',shape='straight',waterlogged=False)
        p.group='Rose Reach crooked lane'
        # Short, three-wide thresholds connect to the shared bend, never a
        # giant lawn strip or an invisible jump into a floating front door.
        start=(x+(rise+1)*dx,z+(rise+1)*dz);end=min(centers,key=lambda q:abs(q[0]-start[0])+abs(q[1]-start[1]));current=start
        while current!=end:
            side=(1,0) if dz else (0,1)
            for u in (-1,0,1):
                xx,zz=current[0]+side[0]*u,current[1]+side[1]*u;q=pave(p,xx,zz)
                for dy in (1,2):p.walk.append((xx,q[1]+dy,zz))
            if current[0]!=end[0]:current=(current[0]+(1 if end[0]>current[0] else -1),current[1])
            else:current=(current[0],current[1]+(1 if end[1]>current[1] else -1))
    # Seated pockets and two little shop displays leave the center lane clear.
    for x,z,face in ((1289,-1238,'east'),(1331,-1239,'west')):
        ground=p.land[x,z]['surface_y'];p.fixture((x,ground+1,z),'handcrafted:dark_oak_bench',support=(x,ground,z),facing=face,color='none',shape='single',waterlogged=False)
    for x,z in ((1292,-1245),(1317,-1245),(1335,-1233)):
        row=p.land.get((x,z))
        if row is None or row['kind']!='dry' or (x,row['surface_y']+1,z) in p.walk:continue
        y=row['surface_y'];p.put((x,y+1,z),'minecraft:chiseled_stone_bricks')
        p.fixture((x,y+2,z),'minecraft:potted_fern',support=(x,y+1,z))
    p.cameras.extend([{'name':'rose-reach-first-lane','feet':[1292.5,64,-1240.5],'look_at':[1312,71,-1242]},
                      {'name':'post-house-bend','feet':[1333.5,65,-1236.5],'look_at':[1340,76,-1243]},
                      {'name':'chartmaker-room','feet':[1298.5,65,-1248.5],'look_at':[1295,66,-1254]},
                      {'name':'tea-salon','feet':[1296.5,65,-1235.5],'look_at':[1293,66,-1230]}])


def check_quarter(p):
    material=[]
    for lot in ROSE_REACH:material.append(require_material_rule({q:s for q,s in p.blocks.items() if p.owners[q]==lot.name},lot.name+' complete furnished building'))
    require_outdoor_rule(p.blocks,'Rose Reach complete authored ground, roofs, rooms and lane')
    blocked=[(q,p.blocks.get(q)) for q in set(p.walk) if p.blocks.get(q,'minecraft:air')!='minecraft:air' and not any(word in base(p.blocks[q]) for word in ('door','stairs'))]
    if blocked:raise UserError('Actual two-high source route is blocked: '+str(blocked[:8]))
    if any(p.owners.get(q)!=row['room'] or base(p.blocks.get(q,'minecraft:air'))!=row['block'] for row in p.fixtures for q in [tuple(row['position'])]):raise UserError('A furnished object was silently overwritten')
    if min(row.get('furnishing_objects',0) for row in p.rooms)<12:raise UserError('A room is missing its complete lived-in furniture scene')
    return {'complete_building_material_checks':material,'outdoor_nine_cap':True,'fully_furnished_rooms':len(p.rooms),
            'actual_furnishing_objects':len(p.fixtures),'clear_two_high_source_route_cells':len(set(p.walk)),
            'all_main_footprints_saved_dry':True,'native_window_and_roof_parts':'derived from complete final authored same-ID masks',
            'entities':0,'commands':0,'visual_or_native_acceptance':'UNVERIFIED; parent must inspect real floor-level/shader/day/night and walking views'}


def authored_rose_reach(registry,fine):
    p=EastPlan(registry,fine)
    for lot in ROSE_REACH:
        cells,floor,door=house_shell(p,lot);furnished_rooms(p,lot,cells,floor,door)
    rose_street(p)
    canonical_parts(p)
    return p


def native_payload(registry,states,checkpoint_sha,name,*,tags=None):
    palette=sorted(set(states.values()));lookup={s:n for n,s in enumerate(palette)}
    return {'format':'awft-native-settlement:1','name':name,'created':utcnow(),'seed':registry['seed'],'world_path':registry['world_path'],
            'backup_sha256':checkpoint_sha,'bounds':[min(q[0] for q in states),min(q[2] for q in states),max(q[0] for q in states),max(q[2] for q in states)],
            'palette':palette,'blocks':[[*q,lookup[s]] for q,s in sorted(states.items())],
            'block_entities':[{'pos':list(q),'nbt':tag} for q,tag in sorted((tags or {}).items())],'commands':[],'landmarks':[],
            'validation':'PRIVATE SOURCE PROTOTYPE - native preimage/place/normal joins/fullverify and actual floor/shader/art review required'}


def prepare_rose_reach(home,fine_path,checkpoint_id,checkpoint_sha):
    """Bound exact source to a stopped snapshot; writes private plans, never world."""
    home=Path(home).resolve();fine_path=Path(fine_path).resolve()
    if not home.is_relative_to(Path('D:/A World for Two/staging/world-tests').resolve()) or not fine_path.is_relative_to(home/'staging'):raise UserError('Owned private artistic proposal only')
    reserve=guard(4*MIB,64*MIB);current=read_json(home/'dashboard/settlement/backup-receipt.json')
    if current.get('verified') is not True or current.get('id')!=checkpoint_id or current.get('sha256')!=checkpoint_sha:raise UserError('Exact current parent-owned stopped checkpoint required')
    if fine_path.stat().st_size>MAX_OUTPUT:raise UserError('Finite exact eastern saved field required')
    fine=read_json(fine_path)
    if fine.get('format')!='awft-fine-eastern-north-bank-land:1' or fine.get('checkpoint_sha256')!=checkpoint_sha:raise UserError('Fine terrain and stopped checkpoint must match')
    registry=read_json(home/'dashboard/settlement/registry.json');protected,custody=preservation(home,registry)
    if not protected.issuperset(map(tuple,fine['protected_columns_xz'])):raise UserError('Current authored protection changed; rebuild measured field, never shrink exclusions')
    p=authored_rose_reach(registry,fine);proof=check_quarter(p);terrain=NorthTerrain(home,current,registry);before={};supports={}
    try:
        for q,value in sorted(p.blocks.items(),key=lambda row:(row[0][0]//16,row[0][2]//16,row[0][1],row[0][0],row[0][2])):
            actual=terrain.state(*q)
            if actual is None:raise UserError('A complete original source target is not saved FULL: '+str(q))
            if q in terrain.entities or q in p.saved_BEs:raise UserError('Never replace or reload a saved block entity')
            key=base(actual)
            if key not in AIR|SOFT|GROUND|NORTH_SOFT and not is_tree(key):raise UserError('Preserve unknown/manmade current block: '+str((q,actual)))
            if 'waterlogged=true' in actual:raise UserError('Main extension target intersects native water')
            before[q]=actual
            terrain.check()
        for row in p.supports:
            q=tuple(row['support'])
            if q not in p.blocks:
                actual=terrain.state(*q)
                if actual is None or base(actual) not in GROUND:raise UserError('Existing furniture support changed')
                supports[q]=actual
        sources=terrain.snapshot.sources
    finally:terrain.close()
    solids={q:s for q,s in p.blocks.items() if base(s) not in AIR}
    if len(solids)>20_000:raise UserError('Split normal-join targets; never bypass the native20k settle cap')
    documents={'prototype.json':native_payload(registry,p.blocks,checkpoint_sha,'Rose Reach — seven original fully furnished houses and crooked lane',tags=p.tags),
               'before-VERIFY-ONLY.json':native_payload(registry,before,checkpoint_sha,'VERIFY ONLY — exact stopped natural ground/air before Rose Reach'),
               'supports-VERIFY-ONLY.json':native_payload(registry,supports,checkpoint_sha,'VERIFY ONLY — unchanged actual ground supports'),
               'normal-joins-SETTLE-ONLY.json':native_payload(registry,solids,checkpoint_sha,'NORMAL SETTLE ONLY — actual neighbor joins; never place/replay source')}
    documents['normal-joins-SETTLE-ONLY.json'].update(construction_forbidden=True,verification_only=True)
    encoded={name:(json.dumps(doc,separators=(',',':'),ensure_ascii=False)+'\n').encode() for name,doc in documents.items()}
    manifest={'format':'awft-north-bank-east-rose-reach:1','checkpoint_id':checkpoint_id,'checkpoint_sha256':checkpoint_sha,'source_sha256':digest(Path(__file__)),'fine_land_sha256':digest(fine_path),
              'status':'STAGED original geometry only; no native action/art acceptance','buildings':p.lots,'rooms':p.rooms,'furnishings':p.fixtures,'supports':p.supports,
              'source_walk_air_cells':[list(q) for q in sorted(set(p.walk))],'cameras':p.cameras,'checks':proof,'existing_source_protection':custody,'saved_sources':sources,
              'native_entities':0,'commands':0,'old_BEs_replayed':0,'native_actions':0,'reserve':reserve,
              'normal_join_targets':len(solids),'gate':'Parent current native before/support verification, place prototype once, normal native joins on the small solid-only SETTLE artifact, strict expected verification and actual day/night/floor/court walking review before broader quarters',
              'existing_town_threshold':'New lane starts at1292,-1240. A separate exact current AIR/support-reviewed small stair connection to the accepted street is still required; no accepted source/AIR cell is overwritten here.',
              'files':{name:{'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()} for name,raw in encoded.items()}}
    encoded['manifest.json']=(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n').encode()
    if sum(map(len,encoded.values()))>64*MIB:raise UserError('Finite original quarter output exceeded')
    output=home/'staging'/('north-bank-rose-reach-'+str(time.time_ns()));output.mkdir()
    for name,raw in encoded.items():
        with (output/name).open('xb') as stream:stream.write(raw)
    return {'folder':str(output),'manifest_sha256':digest(output/'manifest.json'),'targets':len(p.blocks),'buildings':len(p.lots),'rooms':len(p.rooms),'furnishings':len(p.fixtures),'native_actions':0,'files':manifest['files']}


def diagram(data):
    x0,z0,x1,z1=data['bounds'];scale=2
    out=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{(x1-x0+16)*scale}" height="{(z1-z0+32)*scale}" viewBox="0 0 {x1-x0+16} {z1-z0+32}"><rect width="100%" height="100%" fill="#111820"/>']
    colors={'water':'#23688d','dry':'#9d9a65','retained_object':'#b66d64','unknown':'#1d2330'}
    for r in data['samples']:
        color=colors[r['kind']]
        out.append(f'<rect x="{r["x"]-x0+8}" y="{r["z"]-z0+20}" width="4" height="4" fill="{color}"/>')
    out.append('<g fill="white" font-family="sans-serif" font-size="7"><text x="8" y="10">NORTH UP | saved FULL4m samples | tan=dry blue=water red=retained dark=unknown</text></g></svg>')
    return ''.join(out).encode()


def study(home,checkpoint_id,checkpoint_sha):
    home=Path(home).resolve()
    if not home.is_relative_to(Path('D:/A World for Two/staging/world-tests').resolve()):raise UserError('Private artistic staging only')
    reserve=guard(2*MIB,MAX_OUTPUT);receipt=read_json(home/'dashboard/settlement/backup-receipt.json')
    if receipt.get('verified') is not True or receipt.get('id')!=checkpoint_id or receipt.get('sha256')!=checkpoint_sha:raise UserError('Use the actual current parent-owned stopped checkpoint')
    registry=read_json(home/'dashboard/settlement/registry.json');terrain=NorthTerrain(home,receipt,registry)
    try:data=measured_land(terrain)
    finally:terrain.close()
    data.update(checkpoint_id=checkpoint_id,checkpoint_sha256=checkpoint_sha,source_sha256=digest(Path(__file__)),native_actions=0,world_writes=0)
    raw=(json.dumps(data,separators=(',',':'))+'\n').encode();svg=diagram(data)
    manifest={'format':'awft-north-bank-study-manifest:1','at':utcnow(),'checkpoint_id':checkpoint_id,'checkpoint_sha256':checkpoint_sha,'source_sha256':digest(Path(__file__)),'reserve':reserve,'counts':data['counts'],'MCA_raw_bytes':data['raw_MCA_bytes'],'admitted_regions':NORTH_REGIONS,'files':{'measured-land.json':{'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()},'measured-land.svg':{'bytes':len(svg),'sha256':hashlib.sha256(svg).hexdigest()}},'native_actions':0,'scope':'Screenshot-aligned planning study, not a construction plan or accepted footprint'}
    meta=(json.dumps(manifest,indent=2)+'\n').encode()
    if len(raw)+len(svg)+len(meta)>MAX_OUTPUT:raise UserError('Finite north-bank study output exceeded')
    out=home/'staging'/('north-bank-measured-'+str(time.time_ns()));out.mkdir()
    for name,content in [('measured-land.json',raw),('measured-land.svg',svg),('manifest.json',meta)]:
        with (out/name).open('xb') as stream:stream.write(content)
    return {'folder':str(out),'manifest_sha256':hashlib.sha256(meta).hexdigest(),'counts':data['counts'],'MCA_raw_bytes':data['raw_MCA_bytes'],'native_actions':0}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--home',type=Path,required=True);p.add_argument('--checkpoint-id',required=True);p.add_argument('--checkpoint-sha',required=True);p.add_argument('--mode',choices=('study','fine','quarter'),default='study');p.add_argument('--fine',type=Path)
    args=p.parse_args();base_args=(args.home,args.checkpoint_id,args.checkpoint_sha)
    if args.mode=='quarter':
        if args.fine is None:p.error('--fine is required for the authored quarter')
        result=prepare_rose_reach(args.home,args.fine,args.checkpoint_id,args.checkpoint_sha)
    elif args.mode=='fine':result=fine_eastern_land(*base_args)
    else:result=study(*base_args)
    print(json.dumps(result,indent=2))
