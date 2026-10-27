"""Read-only south-bank woodland study and finite original LIFE proposals.

The immutable saved full chunks establish land, never map colors or DH LODs.
This tool emits private survey/recipe evidence, not an executable native plan.
Construction, visual review and a fresh exact preimage precede any LIFE seed.
"""
from __future__ import annotations

import argparse
from collections import Counter, OrderedDict, deque
import hashlib
import json
import math
from pathlib import Path
import uuid
import zlib

from control_room.common import UserError, digest, read_json
from tools.artistic_bridge_refinement import encoded, flatten
from tools.playtest import guard
from tools.settlement_attractions import BackupWorld, MAX_CHUNK, NBTReader, base, unpack_section

MIB = 1024**2
MAX_OUTPUT = 16*MIB
MAX_REGIONS = 2
MAX_STUDY_CELLS = 8192
MAX_CACHED_CHUNKS = 4
STUDY = (1024, -1120, 1392, -832)
STEP = 4
REGIONS = ((2, -3), (2, -2))
AIR = {'minecraft:air', 'minecraft:cave_air', 'minecraft:void_air'}
GROUND = {'minecraft:'+name for name in (
    'grass_block', 'dirt', 'coarse_dirt', 'rooted_dirt', 'podzol', 'mycelium',
    'moss_block', 'mud', 'sand', 'red_sand', 'gravel', 'clay', 'stone', 'granite',
    'andesite', 'diorite', 'calcite', 'tuff', 'snow_block', 'packed_mud')}
GROUND.update({'regions_unexplored:'+name for name in ('peat_dirt', 'silt_dirt')})
SOFT = {'minecraft:'+name for name in (
    'short_grass', 'tall_grass', 'fern', 'large_fern', 'dandelion', 'poppy',
    'cornflower', 'azure_bluet', 'oxeye_daisy', 'allium', 'lily_of_the_valley',
    'blue_orchid', 'pink_petals', 'dead_bush', 'snow', 'vine', 'sugar_cane',
    'brown_mushroom', 'red_mushroom', 'bamboo', 'bamboo_sapling', 'moss_carpet')}
SOFT.update({'regions_unexplored:'+name for name in (
    'grass_sprouts', 'medium_grass', 'small_fern', 'large_fern', 'meadow_sage',
    'fireweed', 'blue_lupine', 'purple_lupine', 'pink_lupine', 'white_lupine')})
SOFT.update({'farm_and_charm:wild_carrots', 'farm_and_charm:wild_barley', 'farm_and_charm:wild_corn'})
NATURAL_TREE_NAMESPACES = {'minecraft', 'regions_unexplored', 'vinery', 'meadow', 'biomesoplenty'}


def is_tree(key):
    namespace, _, name = key.partition(':')
    return namespace in NATURAL_TREE_NAMESPACES and name.endswith(('_log', '_wood', '_leaves'))


class Terrain:
    """Two authenticated raw regions, four small decoded chunks; no live MCA."""
    def __init__(self, home, receipt, registry):
        self.snapshot = BackupWorld(home, receipt, registry)
        # Known saved full chunks authenticate and load exactly these two regions.
        for cx, cz in ((74, -70), (83, -63)):
            self.snapshot.chunk(cx, cz)
            self.snapshot.chunks.clear()
        if set(self.snapshot.regions) != set(REGIONS):
            raise UserError('The finite south-bank study is restricted to its two known regions')
        self.blocks = {}; self.key = None; self.entities = set(); self.unknown = {};self.cache=OrderedDict();self.columns=OrderedDict()

    def close(self):
        self.snapshot.close()

    def chunk(self, cx, cz):
        key = (cx, cz)
        if key == self.key:
            return None if key in self.unknown else self.blocks
        if key in self.cache:
            self.key=key;self.blocks=self.cache.pop(key);self.cache[key]=self.blocks
            return self.blocks
        if key in self.unknown:
            self.key=key;self.blocks={};return None
        if (cx//32, cz//32) not in REGIONS:
            return None  # Outside the admitted region allocation remains unknown.
        raw = self.snapshot.regions[cx//32, cz//32]
        head = ((cz&31)*32+(cx&31))*4
        location = int.from_bytes(raw[head:head+4], 'big')
        sector, count = location >> 8, location & 255
        self.key, self.blocks = key, {}
        if not sector and not count:
            self.unknown[key] = 'not saved/generated'; return None
        if sector < 2 or not count or (sector+count)*4096 > len(raw):
            raise UserError('Malformed immutable terrain sector')
        offset = sector*4096
        length = int.from_bytes(raw[offset:offset+4], 'big')
        if not 1 < length <= count*4096-4:
            raise UserError('Malformed immutable terrain payload')
        mode, packed = raw[offset+4], raw[offset+5:offset+4+length]
        if mode not in (1, 2, 3):
            raise UserError('External/unsupported terrain compression is not silently unknown')
        if mode == 3:
            decoded = packed
        else:
            decoder = zlib.decompressobj(31 if mode == 1 else 15)
            decoded = decoder.decompress(packed, MAX_CHUNK+1)
            if decoder.unconsumed_tail or not decoder.eof:
                raise UserError('Terrain NBT exceeds its finite allocation or is truncated')
        document = NBTReader(decoded).read()
        if (document.get('xPos'), document.get('zPos')) != key:
            raise UserError('Immutable chunk coordinates differ')
        if document.get('Status') not in ('minecraft:full', 'full'):
            self.unknown[key] = 'saved chunk is not FULL'; return None
        self.blocks = {row['Y']:row for row in document.get('sections', [])}
        self.entities.update((row['x'],row['y'],row['z']) for row in document.get('block_entities', []))
        self.cache[key]=self.blocks
        if len(self.cache)>MAX_CACHED_CHUNKS:self.cache.popitem(last=False)
        return self.blocks

    def state(self, x, y, z):
        sections = self.chunk(x//16, z//16)
        return None if sections is None else unpack_section(sections.get(y//16, {}), x, y, z)

    def column(self, x, z):
        if (x,z) in self.columns:
            value=self.columns.pop((x,z));self.columns[x,z]=value;return value
        value=self._column(x,z);self.columns[x,z]=value
        if len(self.columns)>MAX_STUDY_CELLS:self.columns.popitem(last=False)
        return value

    def _column(self, x, z):
        sections = self.chunk(x//16, z//16)
        if sections is None:
            return {'x':x, 'z':z, 'kind':'unknown'}
        visible = None; canopy = None
        for sy in sorted(sections, reverse=True):
            if sy < -4 or sy > 19:
                continue
            palette = sections[sy].get('block_states', {}).get('palette', [])
            if not palette or all(row['Name'] in AIR for row in palette):
                continue
            for y in range(sy*16+15, sy*16-1, -1):
                state = unpack_section(sections[sy], x, y, z); key = base(state)
                if key in AIR:
                    continue
                if visible is None:
                    visible = [y, state]
                if key == 'minecraft:water' or 'waterlogged=true' in state:
                    return {'x':x,'z':z,'kind':'water','surface_y':y,'state':state,'visible':visible}
                if key in SOFT:
                    continue
                if is_tree(key):
                    if canopy is None:
                        canopy = y
                    continue
                kind = 'dry' if key in GROUND else 'retained_object'
                return {'x':x,'z':z,'kind':kind,'surface_y':y,'state':state,
                        'visible':visible,'existing_canopy_y':canopy}
        return {'x':x,'z':z,'kind':'unknown','reason':'No bounded saved surface'}


def survey(terrain, bounds=STUDY, step=STEP):
    x0,z0,x1,z1 = bounds
    if bounds != STUDY or step != STEP:
        raise UserError('A different survey envelope needs a separate bounded review')
    cells = []
    for cx in range(x0//16, x1//16+1):
        for cz in range(z0//16, z1//16+1):
            for x in range(max(x0,cx*16),min(x1,cx*16+15)+1,step):
                for z in range(max(z0,cz*16),min(z1,cz*16+15)+1,step):
                    cells.append(terrain.column(x,z))
                    if len(cells)>MAX_STUDY_CELLS:
                        raise UserError('Terrain survey exceeded its finite cell allocation')
    return {'format':'awft-saved-south-bank-survey:1','bounds':list(bounds),'sample_step':step,
            'samples':cells,'counts':dict(Counter(row['kind'] for row in cells)),
            'unknown_chunks':[[*key,value] for key,value in sorted(terrain.unknown.items())],
            'saved_block_entities':[list(pos) for pos in sorted(terrain.entities)],
            'sources':terrain.snapshot.sources,'limitations':[
                'Four-block samples establish study geography, not clearance at unsampled cells',
                'Unknown/non-FULL chunks remain unknown; this tool does not generate or discover them',
                'Leaves and native logs are recorded as retained canopy, never cleared for a new tree',
                'Ground classification is a conservative exact-ID allow-list; unknown surfaces are retained']}


def south_component(cells, anchor=(1104,-1072), step=STEP):
    """Connected saved dry samples reachable from a reviewed south-bank anchor."""
    dry = {(row['x'],row['z']):row for row in cells if row['kind']=='dry'}
    if anchor not in dry:
        raise UserError('The exact dry south-bank anchor is absent; do not guess a shore')
    reached = {anchor}; pending = deque([anchor])
    while pending:
        x,z = pending.popleft()
        for other in ((x-step,z),(x+step,z),(x,z-step),(x,z+step)):
            if other in dry and other not in reached:
                reached.add(other);pending.append(other)
    return reached


def exclusions(paths, registry, buffer=5):
    """Every authored cell, including AIR, contributes a protected horizontal skirt."""
    if buffer != 5:
        raise UserError('The reviewed architecture/oriel buffer is five blocks')
    protected = set(); custody = []
    for name,path,expected in paths:
        path=Path(path)
        if not 0 < path.stat().st_size <= 16*MIB or digest(path)!=expected:
            raise UserError('Exact bounded authored exclusion changed: '+name)
        document=read_json(path);document=document.get('physical_plan',document)
        if any(str(document.get(key))!=str(registry[key]) for key in ('seed','world_path')):
            raise UserError('An authored exclusion belongs to another world')
        field=flatten(document)
        columns={(x,z) for x,y,z in field}
        columns.update((row['pos'][0],row['pos'][2]) for row in document.get('block_entities',[]))
        for x,z in columns:
            protected.update((x+dx,z+dz) for dx in range(-buffer,buffer+1) for dz in range(-buffer,buffer+1))
        custody.append({'name':name,'sha256':expected,'all_authored_columns':len(columns),
                        'AIR_routes_and_unwritten_BEs_protected':True})
    return protected,custody


# Original landscape compositions. A zone selects only verified dry cells in
# its connected bank; these ellipses do not grant terrain/edit authority.
ZONES = (
    ('cottage_edge','Magnolia and apple glades',(1100,-1056),(52,39),
     ('magnolia','silver_birch','magnolia','maple'),
     'Small flowering crowns, meadow openings and a clear cottage-to-castle view'),
    ('rosewater','Rosewater mixed canopy',(1224,-920),(92,51),
     ('maple','silver_birch','larch','magnolia','maple'),
     'An irregular broad canopy behind the inhabited castle bank, with fern-rich openings'),
    ('east_reach','Birch and pine reach',(1352,-947),(47,94),
     ('silver_birch','pine','larch','maple'),
     'Higher open crowns and shaded understory outside the mill and its kinetic envelopes'),
)
TREE_MATERIALS = {
    'magnolia':('regions_unexplored:magnolia_log','regions_unexplored:pink_magnolia_leaves'),
    'maple':('regions_unexplored:maple_log','regions_unexplored:red_maple_leaves'),
    'silver_birch':('regions_unexplored:silver_birch_log','regions_unexplored:silver_birch_leaves'),
    'larch':('regions_unexplored:larch_log','regions_unexplored:golden_larch_leaves'),
    'pine':('regions_unexplored:pine_log','regions_unexplored:pine_leaves'),
    'willow':('regions_unexplored:willow_log','regions_unexplored:willow_leaves'),
}
MAX_TREES = 180
MAX_TREE_BLOCKS = 100000
NATIVE_ANIMAL_JAR = ('naturalist-2.0.7-neoforge-1.21.1.jar',
                     '2740593710eba0a917f862e535f3e2ef06c39ccdd6441986da02f9dd4394f03a')
LIFE = {
    'naturalist:deer':('creature',3,'deer.Deer','Panic, player/predator avoidance, grass eating, parent following; no target selector in registered goals'),
    'naturalist:bird':('creature',4,'bird.Bird','Seed eating, flocking, avoidance and natural taming/owner-follow goals; no owner is assigned'),
    'naturalist:butterfly':('ambient',3,'butterfly.Butterfly','Native flower pollination and crop growth goals; flowering clearings outside crops/structures'),
    'naturalist:firefly':('ambient',5,'firefly.Firefly','Native grass hiding and flying wandering; dusk grass margins'),
    'naturalist:duck':('creature',3,'duck.Duck','Panic, swimming, strolling and parent following; native food tag is raw fish, not a guessed seed diet'),
    'naturalist:dragonfly':('ambient',3,'dragonfly.Dragonfly','Native customServerAiStep flight and hover; waterside air clearance required'),
}
VIEW_CORRIDORS = (
    {'id':'cottage-to-castle','points':[[1136,-1076],[1172,-1064],[1214,-1048]],'half_width':5,
     'intent':'Keep the castle approach visible through low meadow, without a broad paved avenue'},
    {'id':'castle-south-glade','points':[[1214,-962],[1214,-920],[1222,-884]],'half_width':6,
     'intent':'An irregular south meadow retains the palace skyline and its inhabited garden outlook'},
)
FUTURE_RESERVATIONS = (
    {'id':'starting-square-fountain-pending-exact-source','bounds':[1104,-1144,1156,-1092],
     'status':'PROVISIONAL NO-PLANT RESERVATION; exact plaza AIR/routes/basin/plumbing/view mask required before final binding'},
)


def number(salt, x, z):
    return int.from_bytes(hashlib.sha256(f'awft-woodland:{salt}:{x}:{z}'.encode()).digest()[:8],'big')


def native_state(registry, key, **fields):
    schema=registry['blocks'].get(key)
    if schema is None:
        raise UserError('Landscape recipe uses an unregistered native block: '+key)
    props={k:str(v).lower() for k,v in fields.items()}
    if any(k not in schema or v not in schema[k] for k,v in props.items()):
        raise UserError('Landscape recipe has an unregistered native property: '+key)
    return key+('['+','.join(k+'='+v for k,v in sorted(props.items()))+']' if props else '')


def tree_shape(registry, kind, height, radius, variant):
    """Connected original trunks/branches and varied crown volumes, local to soil."""
    if kind not in TREE_MATERIALS or not 5<=height<=13 or not 3<=radius<=5:
        raise UserError('Tree recipe exceeds its finite authored profile')
    log,leaves=TREE_MATERIALS[kind];field={}
    def timber(x,y,z,axis):
        extra={}
        if log.endswith('silver_birch_log'):extra['is_base']=False
        if log.endswith('pine_log'):extra.update(is_stripped=False,transition_block=False)
        field[x,y,z]=native_state(registry,log,axis=axis,**extra)
    foliage=native_state(registry,leaves,distance=7,persistent=True,waterlogged=False)
    if kind in ('pine','larch'):
        for y in range(3,height+2):
            r=min(radius,max(0,math.ceil((height+1-y)*radius/max(1,height-2))))
            for x in range(-r,r+1):
                for z in range(-r,r+1):
                    if x*x+z*z<=(r+.25)**2 and not (abs(x)==r and abs(z)==r and r>1):
                        field[x,y,z]=foliage
        for y in range(1,height+1):timber(0,y,0,'y')
        # Low short branches give the conifer a supported profile.
        for dy,dx,dz in ((4,1,0),(5,0,-1),(7,-1,0)):
            if dy<height:timber(dx,dy,dz,'x' if dx else 'z')
    else:
        for dy in range(-3,3):
            r=radius-(1 if dy in (-3,2) else 0)
            ox=((variant>>2)&1) if dy>0 else 0;oz=-((variant>>3)&1) if dy>0 else 0
            for x in range(-r,r+1):
                for z in range(-r,r+1):
                    if x*x+z*z<=(r+.2)**2 and (abs(x)+abs(z)<2*r or dy==0):
                        field[x+ox,height+dy,z+oz]=foliage
        for y in range(1,height+1):timber(0,y,0,'y')
        for dx,dz,start in ((1,0,height-3),(-1,0,height-2),(0,1,height-3),(0,-1,height-1)):
            length=2+(variant&1)
            for n in range(1,length+1):timber(dx*n,start,dz*n,'x' if dx else 'z')
        if kind=='willow':
            for dx,dz in ((radius,0),(-radius,0),(0,radius),(0,-radius)):
                for y in range(height-4,height-1):field[dx,y,dz]=foliage
    return field


def zone_at(x,z):
    ranked=[]
    for ident,name,center,extent,kinds,intent in ZONES:
        score=((x-center[0])/extent[0])**2+((z-center[1])/extent[1])**2
        if score<=1:ranked.append((score,ident))
    return min(ranked)[1] if ranked else 'linking_wood'


def buffered_columns(columns, radius):
    return {(x+dx,z+dz) for x,z in columns for dx in range(-radius,radius+1)
            for dz in range(-radius,radius+1)}


def corridor_columns(corridors=VIEW_CORRIDORS):
    columns=set()
    for row in corridors:
        width=row['half_width']
        for a,b in zip(row['points'],row['points'][1:]):
            steps=max(abs(b[0]-a[0]),abs(b[1]-a[1]))
            for n in range(steps+1):
                center=(round(a[0]+(b[0]-a[0])*n/max(1,steps)),round(a[1]+(b[1]-a[1])*n/max(1,steps)))
                columns.update(buffered_columns({center},width))
    return columns


def tree_admission(terrain, root, field, protected, proposed):
    """Entire crown/root clearance, with no soil fill, tree cutting or water edits."""
    x,g,z=root;columns={(x+dx,z+dz) for dx,dy,dz in field}
    if columns & protected:return None,'authored AIR/solid/route or five-metre skirt'
    if any(not(STUDY[0]<=xx<=STUDY[2] and STUDY[1]<=zz<=STUDY[3]) for xx,zz in columns):
        return None,'crown outside authenticated study'
    for xx,zz in columns:
        if terrain.column(xx,zz)['kind']!='dry':return None,'crown over water, retained object or unknown shore'
    # The complete crown, rather than just its centre, stays five metres from
    # saved objects even if a small object fell between four-block samples.
    for xx,zz in buffered_columns(columns,5):
        kind=terrain.column(xx,zz)['kind']
        if kind=='unknown':return None,'unknown cell in five-metre crown perimeter'
        if kind=='retained_object':return None,'five-metre crown skirt around actual saved object'
    center=terrain.column(x,z)
    if center['kind']!='dry' or center.get('surface_y')!=g or base(center['state']) not in {
            'minecraft:grass_block','minecraft:dirt','minecraft:coarse_dirt','minecraft:rooted_dirt','minecraft:podzol'}:
        return None,'root needs exact dry natural soil'
    for xx,zz in ((x-2,z),(x+2,z),(x,z-2),(x,z+2)):
        row=terrain.column(xx,zz)
        if row['kind']!='dry' or abs(row['surface_y']-g)>2:return None,'steep or wet root collar'
    transformed={(x+dx,g+dy,z+dz):state for (dx,dy,dz),state in field.items()}
    before={}
    for pos,state in transformed.items():
        if pos in proposed:
            if base(proposed[pos]).endswith('_leaves') and base(state).endswith('_leaves'):continue
            return None,'another authored trunk or branch'
        old=terrain.state(*pos)
        if old is None:return None,'unknown saved chunk'
        if base(old) not in AIR|SOFT:return None,'retain existing canopy/object/water'
        before[pos]=old
    return (transformed,before),None


def glade_witness(terrain, center, protected):
    """Saved dry support and headroom witness, not a native animal acceptance."""
    x,z=center;columns=[];plants=Counter();heights=[]
    for dx in range(-2,3):
        for dz in range(-2,3):
            xx,zz=x+dx,z+dz
            if (xx,zz) in protected:return None
            row=terrain.column(xx,zz)
            if row['kind']!='dry' or base(row['state']) not in {
                    'minecraft:grass_block','minecraft:dirt','minecraft:coarse_dirt','minecraft:podzol'}:return None
            g=row['surface_y'];heights.append(g)
            for y in range(g+1,g+4):
                state=terrain.state(xx,y,zz)
                if state is None or base(state) not in AIR|SOFT:return None
                if base(state) not in AIR:plants[base(state)]+=1
            columns.append({'ground':[xx,g,zz],'actual_support':row['state']})
    if max(heights)-min(heights)>1:return None
    return {'center_feet':[x,terrain.column(x,z)['surface_y']+1,z],
            'saved_dry_support_columns':len(columns),'ground_height_range':[min(heights),max(heights)],
            'body_cells_checked':len(columns)*3,'existing_soft_plants':dict(plants),
            'exact_supports':columns,'native_spawn_or_behavior_tested':False,
            'habitat_status':'Saved local geometry witness; current native collision/AI/food validation still required'}


def residents(registry, population_id, glades, witnesses=None):
    """Stable finite proposals only; a world ledger and native habitats gate seeding."""
    try:namespace=uuid.UUID(population_id)
    except (TypeError,ValueError) as exc:raise UserError('One retained population namespace UUID is required') from exc
    result=[]
    schedule=('naturalist:deer','naturalist:bird','naturalist:butterfly','naturalist:firefly')
    for glade in glades:
        entity=schedule[number('resident-kind',*glade)%len(schedule)];category,count,cls,behavior=LIFE[entity]
        if registry.get('entity_categories',{}).get(entity)!=category:
            raise UserError('Native resident category changed: '+entity)
        ident=f'south-woodland-glade-{glade[0]}-{glade[1]}-{entity.split(":")[1]}'
        result.append({'id':ident,'habitat_center_xz':list(glade),'entity':entity,
                       'native_MobCategory':category,'native_class':'com.crispytwig.naturalist.world.entity.animal.'+cls,
                       'behavior_basis':behavior,'maximum_initial_residents':count,
                       'saved_habitat_witness':(witnesses or {}).get(tuple(glade)),
                       'members':[{'uuid':str(uuid.uuid5(namespace,ident+':'+str(i))),
                                   'tags':['awft_life',ident]} for i in range(count)],
                       'native_gate':'Fresh actual 3D dry support/body clearance, existing residents and stable world population ledger; finalizeSpawn natural variant/AI; never assign pet ownership',
                       'NoAI':False,'OwnerUUID_assigned':False,'spawn_executed':False})
    return result


def propose(terrain, study, registry, protected, population_id):
    # Follow the actual cottage/castle dry component. The opposite steep bank is
    # retained, not silently joined across a channel or adopted as more land.
    component=south_component(study['samples']);rows={(r['x'],r['z']):r for r in study['samples']}
    for x,y,z in terrain.entities:protected.update(buffered_columns({(x,z)},5))
    for row in study['samples']:
        if row['kind']=='retained_object':protected.update(buffered_columns({(row['x'],row['z'])},5))
    for row in FUTURE_RESERVATIONS:
        x0,z0,x1,z1=row['bounds']
        protected.update((x,z) for x in range(x0-5,x1+6) for z in range(z0-5,z1+6))
    candidates=sorted(component,key=lambda p:number('spacing',*p))
    glades=[];witnesses={}
    for x,z in candidates:
        if len(glades)>=16:break
        if (x,z) in protected or rows[x,z].get('existing_canopy_y') is not None:continue
        if all((x-gx)**2+(z-gz)**2>=30**2 for gx,gz in glades):
            witness=glade_witness(terrain,(x,z),protected)
            if witness:glades.append((x,z));witnesses[x,z]=witness
    meadow=buffered_columns(glades,7)|corridor_columns()
    new={};before={};trees=[];reject=Counter();centers=[];zones={row[0]:row for row in ZONES}
    for sx,sz in candidates:
        if len(trees)>=MAX_TREES:break
        jitter=number('root',sx,sz);x=sx+(jitter%5)-2;z=sz+((jitter>>4)%5)-2
        if (x,z) in protected or any((x-cx)**2+(z-cz)**2<8**2 for cx,cz in centers):continue
        zone=zone_at(x,z);row=terrain.column(x,z)
        if row['kind']!='dry':reject[row['kind']]+=1;continue
        kinds=zones[zone][4] if zone in zones else ('maple','silver_birch','larch')
        kind=kinds[jitter%len(kinds)];height=(6+jitter%2 if kind=='magnolia' else 9+jitter%4 if kind in ('pine','larch') else 8+jitter%3)
        radius=3 if kind=='magnolia' else 3+jitter%2 if kind in ('pine','larch') else 4+jitter%2
        field=tree_shape(registry,kind,height,radius,jitter)
        admitted,why=tree_admission(terrain,(x,row['surface_y'],z),field,protected|meadow,new)
        if why:reject[why]+=1;continue
        changed,preimage=admitted
        # Leaf overlap adopts the first native tree; no written state is replaced.
        changed={pos:state for pos,state in changed.items() if pos not in new}
        new.update(changed);before.update(preimage);centers.append((x,z))
        trees.append({'id':f'south-tree-{x}-{z}','kind':kind,'zone':zone,'root':[x,row['surface_y'],z],
                      'height':height,'crown_radius':radius,'new_cells':len(changed),
                      'profile_sha256':hashlib.sha256(encoded([[*p,s] for p,s in sorted(changed.items())])).hexdigest()})
        if len(new)>MAX_TREE_BLOCKS:raise UserError('Original forest exceeded its finite block allocation')
    plantings=[]
    for gx,gz in glades:
        for dx,dz in ((-3,-2),(-2,-3),(2,-3),(3,-2),(-4,0),(4,0),(-2,3),(2,3),(0,4)):
            x,z=gx+dx,gz+dz
            if (x,z) in protected:continue
            row=terrain.column(x,z)
            if row['kind']!='dry' or base(row['state']) not in {'minecraft:grass_block','minecraft:dirt','minecraft:podzol'}:continue
            pos=(x,row['surface_y']+1,z)
            old=terrain.state(*pos)
            if old is None or base(old) not in AIR or pos in new:continue
            key='minecraft:fern' if dx*dz<0 else 'minecraft:oxeye_daisy' if gz%3 else 'minecraft:cornflower'
            state=native_state(registry,key);new[pos]=state;before[pos]=old
            plantings.append({'position':list(pos),'state':state,'glade':[gx,gz]})
    # Fern communities sit under/just outside mixed canopies, not only in
    # isolated flower rings. Keep every existing plant and tree unchanged.
    for tree in trees:
        cx,cy,cz=tree['root'];radius=tree['crown_radius']
        for dx,dz in ((-radius-1,-1),(-radius,2),(-2,radius+1),(1,radius),
                      (radius+1,1),(radius,-2),(2,-radius-1),(-1,-radius)):
            x,z=cx+dx,cz+dz
            if (x,z) in protected or (x,z) in meadow:continue
            row=terrain.column(x,z)
            if row['kind']!='dry' or base(row['state']) not in {'minecraft:grass_block','minecraft:dirt','minecraft:podzol'}:continue
            pos=x,row['surface_y']+1,z;old=terrain.state(*pos)
            if old is None or base(old) not in AIR or pos in new:continue
            key='minecraft:fern' if tree['kind'] in ('larch','pine','silver_birch') else 'regions_unexplored:grass_sprouts'
            state=native_state(registry,key);new[pos]=state;before[pos]=old
            plantings.append({'position':list(pos),'state':state,'tree':tree['id']})
    wetbanks=[]
    for x,z in candidates:
        if len(wetbanks)>=10:break
        if (x,z) in protected or any((x-a)**2+(z-b)**2<18**2 for a,b in ((r['bank_xz']) for r in wetbanks)):continue
        row=terrain.column(x,z)
        if row['kind']!='dry' or base(row['state'])!='minecraft:grass_block':continue
        waters=[]
        for dx,dz in ((-4,0),(4,0),(0,-4),(0,4)):
            water=terrain.column(x+dx,z+dz)
            if water['kind']=='water' and base(water['state'])=='minecraft:water' and 'level=0' in water['state']:
                waters.append(water)
        if not waters:continue
        water=min(waters,key=lambda r:(r['x'],r['z']))
        if abs(row['surface_y']-water['surface_y'])>2:continue
        patch=[]
        for dx,dz in ((0,0),(-1,0),(0,1),(1,1),(0,2)):
            xx,zz=x+dx,z+dz
            if (xx,zz) in protected:continue
            ground=terrain.column(xx,zz)
            if ground['kind']!='dry' or base(ground['state'])!='minecraft:grass_block':continue
            pos=xx,ground['surface_y']+1,zz;old=terrain.state(*pos)
            if old is None or base(old) not in AIR or pos in new:continue
            state=native_state(registry,'minecraft:blue_orchid' if dx==0 else 'minecraft:fern')
            new[pos]=state;before[pos]=old;patch.append([*pos,state])
        if patch:wetbanks.append({'bank_xz':[x,z],'saved_water_source':[water['x'],water['surface_y'],water['z']],
            'saved_source_state':water['state'],'bank_ground_y':row['surface_y'],'plants':patch,
            'water_or_channel_geometry_edited':False,'new_aquatic_residents':0})
    animals=residents(registry,population_id,glades,witnesses)
    summaries={}
    for animal in animals:
        name=animal['entity'];witness=animal['saved_habitat_witness'];entry=summaries.setdefault(name,{
            'native_MobCategory':animal['native_MobCategory'],'native_class':animal['native_class'],
            'groups':0,'initial_resident_limit':0,'center_feet':[],'saved_support_columns':0,
            'basis':animal['behavior_basis'],'native_behavior_acceptance':False})
        entry['groups']+=1;entry['initial_resident_limit']+=animal['maximum_initial_residents']
        entry['center_feet'].append(witness['center_feet']);entry['saved_support_columns']+=witness['saved_dry_support_columns']
    for entry in summaries.values():
        points=entry['center_feet'];entry['world_xyz_range']=[[min(p[i] for p in points),max(p[i] for p in points)] for i in range(3)]
    return {'format':'awft-south-woodland-proposal:1','proposal_only':True,'construction_forbidden':True,
            'authored_trees':trees,'native_tree_materials':TREE_MATERIALS,'glades':[list(p) for p in glades],
            'understory_patches':plantings,'wetbank_gardens':wetbanks,'resident_groups':animals,'species_witnesses':summaries,
            'population_namespace':population_id,
            'maximum_initial_residents':sum(g['maximum_initial_residents'] for g in animals),
            'zone_intents':[{'id':i,'name':n,'intent':intent} for i,n,c,e,k,intent in ZONES],
            'canopy_view_corridors':VIEW_CORRIDORS,'future_no_plant_reservations':FUTURE_RESERVATIONS,
            'eligible_connected_dry_samples':len(component),'retained_other_dry_samples':study['counts']['dry']-len(component),
            'tree_rejections':dict(reject),'proposed_geometry':[[*p,s] for p,s in sorted(new.items())],
            'exact_saved_preimages':[[*p,before[p]] for p in sorted(new)],
            'water_cells_changed':0,'terrain_fill_or_flattening':False,'existing_tree_removals':0,
            'native_actions':False,'world_mutated':False,'entity_spawns':0,
            'wetbank_followup':{'native_candidates':['naturalist:duck','naturalist:dragonfly','minecraft:salmon','minecraft:frog'],
                'seeded':False,'gate':'Actual saved/native water depth, shore exit, unobstructed body space and pinned species behavior; no channel fill or blanket aquarium density'},
            'required_next_gates':['Complete explicit authored exclusion custody including all routes and future oriels',
                'New postconstruction verified stopped checkpoint and exact per-cell preimage binding',
                'Parent native placement/identity verification then eye-level shader woodland/path/water review',
                'Pinned native leaf-distance/neighbor updates and plant survival must be derived and strictly checked before an executable plan is admitted',
                'Only after all art/construction and functional gates: separate bounded native LIFE seed with persistent idempotence ledger',
                'Native animal behavior, habitat and active/idle performance observations; no forced chunk loading']}


def write_survey(home, output, checkpoint_id, checkpoint_sha):
    home,output=Path(home).resolve(),Path(output).resolve()
    if output.exists() or not output.is_relative_to(home/'staging'):
        raise UserError('A new owned private survey directory is required')
    reserve=guard(2*MIB,MAX_OUTPUT)
    registry=read_json(home/'dashboard/settlement/registry.json')
    receipt={'id':checkpoint_id,'sha256':checkpoint_sha,'verified':True}
    terrain=Terrain(home,receipt,registry)
    try:
        result=survey(terrain)
    finally:
        terrain.close()
    result.update(checkpoint_id=checkpoint_id,checkpoint_sha256=checkpoint_sha,
                  source_sha256=digest(Path(__file__)),native_actions=False,world_mutated=False)
    raw=encoded(result)
    if len(raw)>MAX_OUTPUT:
        raise UserError('Survey output exceeds its finite allocation')
    output.mkdir(parents=True,exist_ok=False)
    (output/'saved-terrain-survey.json').write_bytes(raw)
    receipt={'survey_sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),
             'counts':result['counts'],'reserve_guard':reserve,
             'maximum_raw_regions':MAX_REGIONS,'maximum_live_decoded_chunks':MAX_CACHED_CHUNKS,
             'memory_bound_bytes':512*MIB,'execution_or_construction_authority':False}
    (output/'receipt.json').write_bytes(encoded(receipt))
    return {'output':str(output),**receipt}


def bind_species_evidence(result,proof):
    if not proof:raise UserError('Exact pinned native class/category provenance is required for resident proposals')
    path=Path(proof['path'])
    if not 0<path.stat().st_size<2*MIB or digest(path)!=proof['sha256']:
        raise UserError('Exact pinned native class/category provenance differs')
    behavior=read_json(path)
    if behavior.get('jar_sha256')!=NATIVE_ANIMAL_JAR[1]:raise UserError('Native species evidence uses a different artifact')
    actual={row['entity_id']:row for row in behavior.get('classes',[])}
    for name,witness in result['species_witnesses'].items():
        row=actual.get(name,{})
        if row.get('class')!=witness['native_class'] or row.get('actual_registry_category')!=witness['native_MobCategory']:
            raise UserError('The actual native species classification witness differs: '+name)
        witness.update(pinned_native_jar=NATIVE_ANIMAL_JAR[0],pinned_native_jar_sha256=NATIVE_ANIMAL_JAR[1],
                       class_inspection_sha256=row['inspection_sha256'],registered_goal_classes=row['registerGoals_new_classes'],
                       native_category_registry_source_sha256=behavior['registry_sha256'])
    result['native_behavior_witness']={'sha256':proof['sha256'],'scope':'Pinned class/registry inspection; native behavior acceptance is not claimed'}


def write_proposal(home,output,checkpoint_id,checkpoint_sha,study_path,index_path,population_id):
    home,output=Path(home).resolve(),Path(output).resolve()
    if output.exists() or not output.is_relative_to(home/'staging'):
        raise UserError('A new owned private proposal directory is required')
    reserve=guard(2*MIB,MAX_OUTPUT)
    study=read_json(study_path);index=read_json(index_path)
    if study.get('checkpoint_id')!=checkpoint_id or study.get('checkpoint_sha256')!=checkpoint_sha:
        raise UserError('Survey and proposal must bind the same immutable source checkpoint')
    registry=read_json(home/'dashboard/settlement/registry.json')
    protected,custody=exclusions([(row['name'],row['path'],row['sha256']) for row in index['plans']],registry)
    protected.update(buffered_columns({tuple(pos[::2]) for pos in study['saved_block_entities']},5))
    terrain=Terrain(home,{'id':checkpoint_id,'sha256':checkpoint_sha,'verified':True},registry)
    try:
        result=propose(terrain,study,registry,protected,population_id)
    finally:
        terrain.close()
    result.update(checkpoint_id=checkpoint_id,checkpoint_sha256=checkpoint_sha,
                  survey_sha256=digest(Path(study_path)),exclusion_index_sha256=digest(Path(index_path)),
                  source_sha256=digest(Path(__file__)),registry_sha256=digest(home/'dashboard/settlement/registry.json'),
                  exclusion_custody=custody,
                  excluded_columns_with_five_metre_skirts=len(protected),
                  current_postconstruction_rebind_pending=True,
                  exact_future_plaza_mask_pending=True)
    bind_species_evidence(result,index.get('native_behavior_witness'))
    raw=encoded(result)
    if len(raw)>MAX_OUTPUT:raise UserError('Proposal exceeds the finite private output allocation')
    output.mkdir(parents=True,exist_ok=False)
    (output/'woodland-proposal.json').write_bytes(raw)
    receipt={'format':'awft-south-woodland-receipt:1','proposal_sha256':hashlib.sha256(raw).hexdigest(),
             'bytes':len(raw),'trees':len(result['authored_trees']),'new_cells':len(result['proposed_geometry']),
             'resident_groups':len(result['resident_groups']),'proposed_initial_residents':result['maximum_initial_residents'],
             'world_or_entity_writes':False,'native_actions':False,'reserve_guard':reserve,
             'maximum_memory_bytes':512*MIB,'maximum_raw_regions':MAX_REGIONS,
             'maximum_decoded_chunks':MAX_CACHED_CHUNKS}
    (output/'receipt.json').write_bytes(encoded(receipt))
    return {'output':str(output),**receipt}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('home','output'):parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--checkpoint-id',required=True);parser.add_argument('--checkpoint-sha',required=True)
    parser.add_argument('--study-path',type=Path);parser.add_argument('--index-path',type=Path);parser.add_argument('--population-id')
    args=vars(parser.parse_args())
    if args['study_path'] or args['index_path'] or args['population_id']:
        if not all(args.get(key) for key in ('study_path','index_path','population_id')):parser.error('Proposal requires all three additional inputs')
        result=write_proposal(**args)
    else:
        for key in ('study_path','index_path','population_id'):args.pop(key)
        result=write_survey(**args)
    print(json.dumps(result,indent=2))
