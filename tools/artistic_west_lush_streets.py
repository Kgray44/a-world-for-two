"""Western outdoor paving and layered greenery; private ordinary Native plans.

Only an authenticated stopped archive is read. Existing buildings, objects,
water, machinery and walking bodies are retained. Nothing is installed or run.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import time

from control_room.common import UserError, digest, read_json, utcnow
from tools.artistic_ground_stability import GRAVITY, STABLE_NATURAL
from tools.artistic_spawn_plaza import payload, state
from tools.artistic_bridge_refinement import flatten
from tools.playtest import guard
from tools.settlement_attractions import BackupWorld
from tools.settlement_attractions import properties
from tools.artistic_botanical import SOIL, STURDY, FACES, OPPOSITE
from tools.artistic_materials import require_outdoor_rule

MIB = 1024**2
WEST = (968, -1338, 1185, -1186)
FIRST = (1018, -1277, 1046, -1248)
FIELD = ('staging/tortuga-narrow-workrooms-1793219506153531200/field-READONLY.json',
         'e59a92bbec943588438782c8ed7fdd4ebacc80f422861766e709e2a5aa1b8880')
ZIP = ('staging/zipline-west-v2-source-1793152099836099800/all-v2-RESERVATION-ONLY.json',
       '92ea594836795a61e00f5cc32290d49d1d47b9fd6eb55aeefc99d527acf8854d')
STREET = ('staging/west-street-stock-SNBT-fixed-20261028T0317Z/future-walk-furniture-reservation-ONLY.json',
          '59e708726681c29ef962f632f3572369ec1db0299d58e11b454b6259b09be905')
GRAY = frozenset('minecraft:'+n for n in ('stone','smooth_stone','andesite',
    'polished_andesite','cobblestone','stone_bricks','cobbled_deepslate')) | {'chipped:small_stone_bricks'}
VOIDS = {'minecraft:air','minecraft:cave_air','minecraft:void_air'}
PAVERS = ('chipped:weathered_cobblestone','chipped:small_stone_bricks',
          'chipped:rough_cobblestone','chipped:flat_mossy_cobblestone_tiles',
          'chipped:trodden_bricks')
GROUND_PACKET = ('staging/west-lush-streets-ground-1793237926978573700/manifest.json',
                 '1369a6d7960fe6a162bafe933a7bb8f2eed3a15a853a5744c111ea96bcbe9057')
GRAVEL_PACKET = ('staging/west-lush-streets-gravel-extension-1793238711418866400/manifest.json',
                 '9324d19aeec3dad2ba8573687bece2542db7f7c45593c5440b4c7d5092e25eba')
SHRUBS = ('regions_unexplored:lavender_wisteria_shrub',
          'regions_unexplored:cherry_shrub','regions_unexplored:pink_magnolia_shrub',
          'regions_unexplored:salmon_wisteria_shrub')
FLOWERS = ('regions_unexplored:blue_lupine','regions_unexplored:pink_lupine',
           'regions_unexplored:purple_lupine','regions_unexplored:aster',
           'minecraft:fern','minecraft:allium')
POTS = ('regions_unexplored:potted_pink_lupine','regions_unexplored:potted_blue_lupine',
        'fishofthieves:potted_pink_plumeria','fishofthieves:potted_tropical_monstera',
        'minecraft:potted_fern')
NATIVE_LOGS = {n for n in STURDY if n.startswith('minecraft:') and
              n.endswith(('_log','_wood'))}


def plus(a, b, scale=1):
    return tuple(a[i]+scale*b[i] for i in range(3))


def clear_body(lookup, x, z):
    return all(key(lookup((x,y,z))) in VOIDS for y in (64,65,66))


def leaf_distances(delta, lookup):
    """Normal native leaf-distance relaxation against literal adjacent states.

    No new log/tree is authored. Known saved leaves contribute their genuine
    distance; unknown mod log/stem neighbors refuse rather than guessing tags.
    """
    leaves={p for p,v in delta.items() if key(v) in
            {'minecraft:oak_leaves','minecraft:azalea_leaves'}}
    distances={p:7 for p in leaves}
    dirs=(*FACES.values(),(0,1,0),(0,-1,0))
    for p in leaves:
        for d in dirs:
            q=plus(p,d)
            if q in leaves: continue
            v=lookup(q); n=key(v)
            if n in NATIVE_LOGS: distances[p]=1
            elif 'distance' in properties(v or '') and n.endswith('_leaves'):
                distances[p]=min(distances[p],int(properties(v)['distance'])+1)
            elif n not in VOIDS and n not in NATIVE_LOGS and any(
                    word in n for word in ('_log','_wood','_stem','_hyphae')):
                raise UserError('Unqualified native leaf/log tag beside drape '+str(q))
    for _ in range(7):
        changed=False
        for p in leaves:
            n=min([distances[p]]+[distances.get(plus(p,d),7)+1 for d in dirs])
            if n!=distances[p]: distances[p]=n;changed=True
        if not changed: break
    return distances


def rooted_edge(lookup, x, z, normal, main, transport, walks, doors, entities):
    """A planted wall shoulder, with TWO literal clear columns beyond it."""
    if (x,z) in main|transport|walks|doors or not within((x,z),WEST):
        return None
    floor=lookup((x,63,z))
    if key(floor) not in GRAY|set(PAVERS)|SOIL|{'minecraft:gravel'}:
        return None
    field={(x,63,z):floor}
    for n in (0,1,2):
        xx,_,zz=plus((x,64,z),normal,n)
        if (xx,zz) in main|transport or not clear_body(lookup,xx,zz): return None
        for y in (64,65,66): field[xx,y,zz]=lookup((xx,y,zz))
    # The floor itself is being replaced; its full shape cannot stand in for
    # the actual dry stack BELOW the new soil. Preserve that stack literally.
    for y in range(62,54,-1):
        p=(x,y,z);v=lookup(p);field[p]=v
        if p in entities or v is None or 'waterlogged=true' in v: return None
        if key(v) in GRAVITY: continue
        if key(v) not in STABLE_NATURAL|GRAY|set(PAVERS)|SOIL: return None
        break
    else:return None
    if set(field)&entities:return None
    return field


def compose_greenery(registry, lookup, main, transport, walks, entities, bounds):
    """Layered, physically attached planting around retained facades only."""
    before={};delta={};roles={};priority={};scenes=[];held=Counter()
    doors=set()
    for x in range(bounds[0]-3,bounds[2]+4):
        for z in range(bounds[1]-3,bounds[3]+4):
            v=lookup((x,64,z))
            if '_door[' in (v or '') and 'trapdoor' not in v:
                doors.update((x+dx,z+dz)for dx in range(-3,4)for dz in range(-3,4)
                             if abs(dx)+abs(dz)<=3)
    def add(scene, items, context, layer):
        if not items:return False
        for p,v in items.items():
            actual=lookup(p)
            if p in entities or (p[0],p[2]) in main|transport or p in delta:
                return False
            if p[1]!=63 and key(actual) not in VOIDS:return False
            if p[1]<66 and (p[0],p[2]) in walks|doors:return False
            if p[1]==63 and key(actual) not in GRAY|set(PAVERS)|SOIL|{'minecraft:gravel'}:
                return False
            if not within((p[0],p[2]),bounds):return False
        if set(context)&entities:return False
        before.update(context)
        for p,v in items.items():
            before[p]=lookup(p);delta[p]=v;roles[p]=layer
            priority[p]=0 if p[1]==63 else 2 if key(v)=='minecraft:cave_vines' else 1
        scenes.append({'label':scene,'layer':layer,'targets':[list(p)for p in items]})
        return True
    # Closely spaced low borders are varied by small facade sections, never
    # placed on a door approach or in the literal two-column walking shoulder.
    for x in range(bounds[0],bounds[2]+1):
        for z in range(bounds[1],bounds[3]+1):
            if (x,z)in main|transport:continue
            for face,normal in FACES.items():
                back=plus((x,64,z),normal,-1)
                if (back[0],back[2])not in main or key(lookup(back))not in STURDY:continue
                witness=rooted_edge(lookup,x,z,normal,main,transport,walks,doors,entities)
                if not witness:continue
                family=(x//7+z//6)%4;section=(x+2*z)%5
                root=state(registry,'minecraft:grass_block',snowy=False) if section in(0,1,4) else 'minecraft:rooted_dirt'
                items={(x,63,z):root}
                if section in(0,3):
                    for y,half in((64,'lower'),(65,'upper')):
                        items[x,y,z]=state(registry,SHRUBS[family],half=half)
                    layer='rooted double-height modded shrub border'
                else:
                    items[x,64,z]=state(registry,FLOWERS[(family+section)%len(FLOWERS)])
                    layer='grass-and-soil low flower and fern edge'
                add('Living lower facade edge '+str((x,z)),items,witness,layer)
                break
    # Pots below genuine upper windows add a human-made display layer. A
    # native top stair shelf has two literal full wall cells behind it; both
    # the shelf and flower stay above three clear metres of public headroom.
    for x in range(bounds[0],bounds[2]+1):
        for z in range(bounds[1],bounds[3]+1):
            if (x,z)in main|transport or (x+z)%3==0:continue
            if key(lookup((x,63,z)))not in GRAY|set(PAVERS)|SOIL|{'minecraft:gravel'}:continue
            for face,normal in FACES.items():
                for y in(67,68,69):
                    p=(x,y,z);wall=plus(p,normal,-1);lower=plus(wall,(0,-1,0))
                    window=plus(wall,(0,2,0));pot=plus(p,(0,1,0))
                    if (wall[0],wall[2])not in main or any(key(lookup(q))not in STURDY for q in(wall,lower)):
                        continue
                    if 'window'not in key(lookup(window)):continue
                    items={p:state(registry,'minecraft:dark_oak_stairs',facing=OPPOSITE[face],
                                half='top',shape='straight',waterlogged=False),
                           pot:state(registry,POTS[(x//4+z//5)%len(POTS)])}
                    if add('Contained upper-window flower shelf '+str(p),items,
                            {wall:lookup(wall),lower:lookup(lower),window:lookup(window)},
                            'supported upper-window potted display'):break
                else:continue
                break
    # Side-attached narrow climbers leave the lower two metres entirely clear.
    for x in range(bounds[0],bounds[2]+1):
        for z in range(bounds[1],bounds[3]+1):
            if (x,z)in main|transport or (x+2*z)%4==0:continue
            if key(lookup((x,63,z)))not in GRAY|set(PAVERS)|SOIL|{'minecraft:gravel'}:continue
            for face,normal in FACES.items():
                back=plus((x,66,z),normal,-1)
                if (back[0],back[2])not in main:continue
                run=[]
                for y in range(66,73):
                    p=(x,y,z);wall=plus(p,normal,-1)
                    if key(lookup(p))in VOIDS and key(lookup(wall))in STURDY and wall not in entities:
                        run.append((p,wall))
                    else:
                        if len(run)>=2:break
                        run=[]
                if len(run)<2:continue
                # Each patch follows the real wall, with rhythm gaps rather
                # than turning a whole window facade into a flat green panel.
                run=run[:2+(x+z)%4];items={};context={}
                for p,wall in run:
                    flags={s:False for s in ('north','south','east','west','up')}
                    flags[OPPOSITE[face]]=True
                    above=plus(p,(0,1,0));flags['up']=key(lookup(above))in STURDY
                    items[p]=state(registry,'minecraft:vine',**flags)
                    context[wall]=lookup(wall);context[above]=lookup(above)
                add('Attached ivy on retained '+face+' wall '+str((x,z)),items,context,'wall-supported climbing ivy')
                break
    # Small leaf swags have a real solid wall root and adjacent vanilla log
    # custody, not a fabricated tree trunk or a new roof over the street.
    for x in range(bounds[0],bounds[2]+1):
        for z in range(bounds[1],bounds[3]+1):
            if (x,z)in main|transport or (x+3*z)%5:continue
            if key(lookup((x,63,z)))not in GRAY|set(PAVERS)|SOIL|{'minecraft:gravel'}:continue
            for face,normal in FACES.items():
                tangent=(1,0,0)if normal[2]else(0,0,1)
                for y in (69,70,71):
                    p=(x,y,z);wall=plus(p,normal,-1)
                    timber=key(lookup(wall))
                    if (wall[0],wall[2])not in main or not(timber in NATIVE_LOGS or
                            timber in STURDY and timber.endswith('_planks')):continue
                    items={};context={wall:lookup(wall)}
                    proposed=(p,plus(p,tangent),plus(p,normal))
                    for i,q in enumerate(proposed):
                        if key(lookup(q))not in VOIDS:break
                        name='minecraft:azalea_leaves'if i==1 else'minecraft:oak_leaves'
                        items[q]=state(registry,name,distance=7,persistent=True,waterlogged=False)
                    if len(items)<2:continue
                    try:leaf_distances(items,lookup)
                    except UserError:held['unknown nearby log tag']+=1;continue
                    if add('Timber-rooted short leaf swag '+str(p),items,context,'supported overhead leaf drape'):break
                else:continue
                break
    # Glowberries hang directly from an existing full sturdy soffit. Mature
    # age25 prevents this decorative pendant growing down into a walking body.
    for x in range(bounds[0],bounds[2]+1):
        for z in range(bounds[1],bounds[3]+1):
            if (x,z)in main|transport or (2*x+z)%7:continue
            if key(lookup((x,63,z)))not in GRAY|set(PAVERS)|SOIL|{'minecraft:gravel'}:continue
            for y in (68,69,70,71):
                p=(x,y,z);root=plus(p,(0,1,0))
                if key(lookup(p))in VOIDS and key(lookup(root))in STURDY:
                    add('Warm natural berry pendant '+str(p),
                        {p:state(registry,'minecraft:cave_vines',age=25,berries=True)},
                        {root:lookup(root)},'contained mature glowberry pendant')
                    break
    # Genuine saved neighboring leaf distances are part of the before proof.
    for p,d in leaf_distances(delta,lookup).items():
        delta[p]=state(registry,key(delta[p]),distance=d,persistent=True,waterlogged=False)
        for v in (*FACES.values(),(0,1,0),(0,-1,0)):
            q=plus(p,v)
            if q not in delta:before[q]=lookup(q)
    if any(p in entities or (p[0],p[2])in transport|main for p in delta):
        raise UserError('Botanical composition entered retained building or transport')
    if any(p[1]in(64,65)and(p[0],p[2])in walks|doors for p in delta):
        raise UserError('Botanical composition obstructed an actual protected approach')
    return before,delta,priority,scenes,dict(held),require_outdoor_rule(delta,'Layered outdoor western foliage and planted edges')


def key(value):
    return (value or 'UNKNOWN').split('[',1)[0]


def within(q, bounds):
    return bounds[0] <= q[0] <= bounds[2] and bounds[1] <= q[1] <= bounds[3]


def paving(x, z):
    """Offset masonry courses, short worn joints and distinct warm patios."""
    # Each patio is deliberately local; no blanket terra-cotta city grid.
    if any(within((x,z),b) for b in ((1022,-1276,1037,-1270),
            (1056,-1266,1070,-1255),(1080,-1263,1091,-1251))):
        return PAVERS[4] if (x+2*(z//3)) % 5 not in (0,) else PAVERS[2]
    course = (x+2*(z//3)) % 7
    if course == 0:
        return PAVERS[2]
    if (x+z//4) % 11 == 0:
        return PAVERS[3]
    return PAVERS[0] if course in (1,2) else PAVERS[1]


def protections(home):
    records=[]
    for relative,sha in (FIELD,ZIP,STREET):
        path=home/relative
        if digest(path)!=sha:
            raise UserError('Frozen western building/transport/route custody differs')
        records.append({'relative':relative,'sha256':sha})
    field=read_json(home/FIELD[0]); main=set()
    for cells in field['retained_source_main_footprints'].values():
        main.update(map(tuple,cells))
    zip_cells=flatten(read_json(home/ZIP[0]))
    # Keep every low construction/support/boarding cell and its immediate
    # shoulder. High flight AIR alone is not permission to alter a station.
    transport={(x+dx,z+dz) for x,y,z in zip_cells if y<=67
        for dx in (-1,0,1) for dz in (-1,0,1)}
    # The explicit current owner landing/first rigging bases remain protected
    # even where an older source's final width differs from current saved work.
    for x,z in ((1100,-1256),(1064,-1248),(1048,-1232)):
        transport.update((x+dx,z+dz) for dx in range(-5,6) for dz in range(-6,7))
    walks={(x,z) for x,y,z in flatten(read_json(home/STREET[0])) if 64<=y<=66}
    return main,transport,walks,records


def ground_candidate(lookup, x, z, main, transport, entities, *, accepted_floor=GRAY):
    """A literal exposed outdoor gray full block on a stable dry stack."""
    if not within((x,z),WEST) or (x,z) in main or (x,z) in transport:
        return None,'building or human-transport footprint'
    floor=lookup((x,63,z))
    if key(floor) not in accepted_floor or 'waterlogged=true' in floor:
        return None,'not reviewed exposed gray paving'
    body={ (x,y,z):lookup((x,y,z)) for y in (64,65,66) }
    if any(key(s) not in VOIDS for s in body.values()):
        return None,'retain object, planting, threshold or occupied body'
    stack={}
    for y in range(62,54,-1):
        p=(x,y,z);value=lookup(p);stack[p]=value
        if p in entities or value is None or 'waterlogged=true' in value:
            return None,'unknown, wet or block-entity support'
        if key(value) in GRAVITY:
            continue
        if key(value) not in STABLE_NATURAL|GRAY:
            return None,'unqualified first non-gravity support'
        break
    else:
        return None,'no stable support in finite stack'
    if any(p in entities for p in (*body,(x,63,z))):
        return None,'retain actual block entity'
    return {(x,63,z):floor}|body|stack,None


def write_packet(registry, checkpoint, before, delta, support, label):
    docs={
        'before-VERIFY-ONLY.json':payload(registry,checkpoint['sha256'],before,
            'VERIFY ONLY literal current saved western outdoor ground '+label,before=True),
        'ground-DELTA-PROPOSAL.json':payload(registry,checkpoint['sha256'],delta,
            'Western worn masonry, crossed joints and warm patio '+label),
        'after-VERIFY-ONLY.json':payload(registry,checkpoint['sha256'],before|delta,
            'VERIFY ONLY western paving and retained dry body/support '+label,before=True),
        'normal-joins-SETTLE-ONLY.json':payload(registry,checkpoint['sha256'],delta,
            'NORMAL SETTLE ONLY western paving '+label,before=True),
    }
    for doc in docs.values():
        doc['construction_forbidden']=True
        doc['native_before_and_master_admission_required']=True
    return docs


def prepare(home, checkpoint_id, checkpoint_sha, *, gravel_only=False):
    home=Path(home).resolve()
    if home.parent!=Path('D:/A World for Two/staging/world-tests').resolve():
        raise UserError('Owned artistic staging home required')
    reserve=guard(4*MIB,16*MIB)
    companion=read_json(home/'backups'/(checkpoint_id+'.json'))
    if companion.get('integrity')!='verified' or companion.get('sha256')!=checkpoint_sha:
        raise UserError('Exact retained verified stopped archive required')
    registry=read_json(home/'dashboard/settlement/registry.json')
    for name in PAVERS:
        state(registry,name)
    main,transport,walks,refs=protections(home)
    checkpoint={'id':checkpoint_id,'sha256':checkpoint_sha,'verified':True}
    snapshot=BackupWorld(home,checkpoint,registry)
    rows={};refused=Counter();started=time.monotonic()
    try:
        for cx in range(WEST[0]//16,WEST[2]//16+1):
            for cz in range(WEST[1]//16,WEST[3]//16+1):
                for x in range(max(WEST[0],cx*16),min(WEST[2],cx*16+15)+1):
                    for z in range(max(WEST[1],cz*16),min(WEST[3],cz*16+15)+1):
                        try:
                            field,reason=ground_candidate(snapshot.state,x,z,main,transport,snapshot.protected,
                                accepted_floor={'minecraft:gravel'}if gravel_only else GRAY)
                        except UserError:
                            refused['unavailable saved FULL chunk']+=1;continue
                        if field: rows[x,z]=field
                        else: refused[reason]+=1
                if time.monotonic()-started>90:
                    raise UserError('Bounded western ground study90s exceeded')
        sources=snapshot.sources.copy()
    finally:
        snapshot.close()
    if not rows:
        raise UserError('No exact eligible western outdoor paving found')
    groups={'first-alley':{},'whole-west-remainder':{}}
    for q,field in rows.items():
        groups['first-alley' if within(q,FIRST) else 'whole-west-remainder'][q]=field
    docs={};counts={};palettes={}
    for label,cells in groups.items():
        if not cells:continue
        before={p:s for field in cells.values() for p,s in field.items()}
        delta={(x,63,z):paving(x,z) for x,z in cells}
        for name,doc in write_packet(registry,checkpoint,before,delta,{},label).items():
            docs[label+'-'+name]=doc
        counts[label]=len(delta);palettes[label]=dict(Counter(delta.values()))
    manifest={'format':'awft-west-outdoor-ground-and-lushness:1','created':utcnow(),
        'checkpoint_id':checkpoint_id,'checkpoint_sha256':checkpoint_sha,
        'source_sha256':digest(Path(__file__)),'west_bounds_xz':WEST,'prototype_bounds_xz':FIRST,
        'ground_targets_by_batch':counts,'paver_palette':palettes,'refused_columns':dict(refused),
        'retained_building_main_columns':len(main),'protected_transport_columns':len(transport),
        'known_public_walk_columns_preserved_at_same_grade':len(walks),
        'structures_inventories_entities_water_written':0,'floor_y':63,'body_y':[64,65,66],
        'greenery_passes':'NEXT: rooted edges, contained shrubs/pots and supported vines/leaf drapes; no current planting claim',
        'dependencies':refs,'saved_sources':sources,'reserve_guard':reserve,
        'native_actions':0,'world_writes':0,'artistic_acceptance':False,
        'gravel_only_extension':gravel_only,
        'admission':'Source-only; master must bind current checkpoint then actual Native BEFORE before admitting bounded DELTA; no unknown gray block is written from source inference'}
    raw={name:(json.dumps(doc,separators=(',',':'))+'\n').encode() for name,doc in docs.items()}
    manifest['files']={n:{'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}for n,b in raw.items()}
    raw['manifest.json']=(json.dumps(manifest,separators=(',',':'))+'\n').encode()
    if sum(map(len,raw.values()))>16*MIB:
        raise UserError('Split bounded16MiB source output')
    out=home/'staging'/('west-lush-streets-'+('gravel-extension-'if gravel_only else'ground-')+str(time.time_ns()));out.mkdir()
    for n,b in raw.items():(out/n).open('xb').write(b)
    return {'folder':str(out),'manifest_sha256':digest(out/'manifest.json'),
            'counts':counts,'palette':palettes,'native_actions':0}


def prepare_greenery(home, checkpoint_id, checkpoint_sha):
    home=Path(home).resolve()
    if home.parent!=Path('D:/A World for Two/staging/world-tests').resolve():
        raise UserError('Owned artistic staging home required')
    reserve=guard(4*MIB,32*MIB)
    companion=read_json(home/'backups'/(checkpoint_id+'.json'))
    if companion.get('integrity')!='verified' or companion.get('sha256')!=checkpoint_sha:
        raise UserError('Exact retained verified stopped archive required')
    registry=read_json(home/'dashboard/settlement/registry.json')
    main,transport,walks,refs=protections(home)
    ground={};ground_refs=[]
    for relative,sha in(GROUND_PACKET,GRAVEL_PACKET):
        path=home/relative
        if digest(path)!=sha:raise UserError('Frozen paving dependency changed')
        source=read_json(path)
        for name,row in source['files'].items():
            if not name.endswith('ground-DELTA-PROPOSAL.json'):continue
            p=path.parent/name
            if digest(p)!=row['sha256']:raise UserError('Frozen paving geometry changed')
            part=flatten(read_json(p))
            if set(part)&set(ground):raise UserError('Gray/gravel floor extensions overlap')
            ground.update(part);ground_refs.append({'path':str(p.relative_to(home)),'sha256':row['sha256']})
    checkpoint={'id':checkpoint_id,'sha256':checkpoint_sha,'verified':True}
    canonical=read_json(home/'dashboard/settlement/backup-receipt.json')
    if canonical.get('verified')is not True:raise UserError('Canonical master admission checkpoint is unavailable')
    snapshot=BackupWorld(home,checkpoint,registry);started=time.monotonic()
    docs={};statistics={};compositions={};all_delta={};saved_sources=[]
    try:
        def lookup(p):return all_delta.get(p,ground.get(p,snapshot.state(p)))
        # The first pocket depends only on its already-proposed local paving.
        def first_lookup(p):
            return ground.get(p,snapshot.state(p))if within((p[0],p[2]),FIRST)else snapshot.state(p)
        for label,bounds,held in(('first-lush-alley',FIRST,set()),
                ('whole-west-lush-remainder',WEST,
                 {(x,z)for x in range(FIRST[0]-3,FIRST[2]+4)for z in range(FIRST[1]-3,FIRST[3]+4)})):
            read=first_lookup if label=='first-lush-alley'else lookup
            before,delta,priority,scenes,refused,rule=compose_greenery(
                registry,read,main,transport|held,walks,snapshot.protected,bounds)
            if not delta:raise UserError('No complete supported greenery scenes in '+label)
            if len(delta)>8192:raise UserError('Split western greenery batch above8192 targets')
            for suffix,field,verify in(('before-VERIFY-ONLY.json',before,True),
                    ('greenery-DELTA-PROPOSAL.json',delta,False),
                    ('after-VERIFY-ONLY.json',before|delta,True),
                    ('normal-joins-SETTLE-ONLY.json',delta,True)):
                doc=payload(registry,canonical['sha256'],field,
                    label+' '+suffix+'; exact ordinary botanical composition',
                    before=verify,priority=priority if not verify else None)
                doc.update(construction_forbidden=True,native_before_and_master_admission_required=True,
                    source_observed_checkpoint_id=checkpoint_id,source_observed_checkpoint_sha256=checkpoint_sha,
                    prospective_after_ground=True)
                docs[label+'-'+suffix]=doc
            all_delta.update(delta)
            statistics[label]={'targets':len(delta),'soil_and_grass':sum(p[1]==63 for p in delta),
                'layers':dict(Counter(s['layer']for s in scenes)),
                'blocks':dict(Counter(key(v)for v in delta.values())),
                'refused':refused,'rule':rule}
            compositions[label]=scenes
            if time.monotonic()-started>120:raise UserError('Bounded120s western greenery study exceeded')
        saved_sources=snapshot.sources.copy()
    finally:snapshot.close()
    manifest={'format':'awft-west-layered-lush-streets:1','created':utcnow(),
        'source_sha256':digest(Path(__file__)),'observed_checkpoint_id':checkpoint_id,
        'observed_checkpoint_sha256':checkpoint_sha,'canonical_admission_checkpoint_id':canonical['id'],
        'canonical_admission_backup_sha256':canonical['sha256'],'west_bounds_xz':WEST,
        'first_pocket_bounds_xz':FIRST,'batches':statistics,'compositions':compositions,
        'ground_dependencies':ground_refs,'retained_context':refs,'saved_sources':saved_sources,
        'source_input':'Literal c330 archive, projected ONLY through the exact named paving DELTAs and the prior first-green pocket; fresh Native BEFORE must establish this projected field before any placement',
        'order':['first-alley gray AND gravel paving','first-lush-alley greenery',
                 'remaining gray AND gravel paving','whole-west-lush-remainder greenery'],
        'preserved':'All existing building cells, windows/doors, inventories/BEs, plants, water, human transport, current ground grades and two-high routes',
        'mechanisms_entities_inventory_writes':0,'new_trees':0,'native_actions':0,
        'artistic_acceptance':False,'reserve_guard':reserve,
        'remaining':'Fresh Native before/place/normal neighbor updates/exact after; actual day/night alley views. Whole-West route/ground review remains separate; these are new supported plant scenes, not a completion claim.'}
    raw={n:(json.dumps(d,separators=(',',':'),ensure_ascii=False)+'\n').encode()for n,d in docs.items()}
    manifest['files']={n:{'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)}for n,b in raw.items()}
    raw['manifest.json']=(json.dumps(manifest,separators=(',',':'),ensure_ascii=False)+'\n').encode()
    if sum(map(len,raw.values()))>32*MIB:raise UserError('Split bounded32MiB source output')
    out=home/'staging'/('west-layered-greenery-'+str(time.time_ns()));out.mkdir()
    for n,b in raw.items():(out/n).open('xb').write(b)
    return {'folder':str(out),'manifest_sha256':digest(out/'manifest.json'),
            'batches':{k:{a:b for a,b in v.items()if a in('targets','soil_and_grass','layers')}for k,v in statistics.items()},
            'native_actions':0}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--home',type=Path,required=True)
    parser.add_argument('--checkpoint-id',required=True)
    parser.add_argument('--checkpoint-sha',required=True)
    parser.add_argument('--pass',dest='pass_name',choices=('ground','gravel-extension','greenery'),default='ground')
    args=parser.parse_args()
    result=(prepare_greenery(args.home,args.checkpoint_id,args.checkpoint_sha)if args.pass_name=='greenery'else
        prepare(args.home,args.checkpoint_id,args.checkpoint_sha,gravel_only=args.pass_name=='gravel-extension'))
    print(json.dumps(result,indent=2))
