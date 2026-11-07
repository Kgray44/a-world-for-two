"""Two further rooted botanical layers over exact Tortuga forecast phases.

Uses existing Garden components, saved-state reader and native plan format.
No runtime, world, client, account, configuration or inventory operations.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import time
import zipfile

from control_room.common import UserError, digest, read_json, utcnow
from tools.artistic_botanical import Garden, FACES, STURDY, SOIL, plus, berry_bracket
from tools.artistic_bridge_refinement import flatten
from tools.artistic_ground_stability import GRAVITY, STABLE_NATURAL
from tools.artistic_materials import require_outdoor_rule
from tools.artistic_spawn_plaza import payload, state
from tools.artistic_street import street_z, grade
from tools.artistic_tortuga_east_ground_life import (
    checked, source_masks, CITY, CLEANUP, cleanup_positions, VOIDS, GRAY, PAVERS,
    open_garden_pockets,
)
from tools.artistic_west_lush_streets import leaf_distances, ground_candidate
from tools.artistic_zipline_catenary import reader_budget
from tools.playtest import guard
from tools.settlement_attractions import BackupWorld, properties

MIB = 1024**2
CHECKPOINT = ('20261029T052317Z-89312d',
              'ab64b9e7b4fa0e5dad2b77deb41a6ee8344ad46c6d522a4ef2048116d7e1017a')
BASE = ('staging/night-context-only-corrections-1793257952482356300/ground/manifest.json',
        '7f53c5c3d4468571f7e1378b86e4ea3f6783acd6b2f4c5e8f259987abc8b9cf8')
ENTRY = ('staging/tortuga-entry-spine-source-1793251117614515000/manifest.json',
         'ab973bf4ef867197094721b9c6389f86335c331321b7ebf9881f17e9150f8d1c')
NORTH = (
    ('Original pirate tavern','staging/artistic-requested-originals-rebind-20261027T1810Z/tavern-adapted.json',
     'ffd2160ef519cb94d4d37c83039f6a2f70c70c70bb52495bea3fc6367d3fc789'),
    ('Original fisherman shop','staging/artistic-requested-originals-rebind-20261027T1810Z/shop-adapted.json',
     '410be015fe8fc26f450dfd8075cb9bd543dcae8de8f52cfb9a60ea68720cb60e'),
    ('Drowned Rose','staging/artistic-pirate-spit-byte-slots-1793124362042040500/drowned-rose-VERIFY-ONLY.json',
     'f646d9ed046f603dc4e55c3f564949dba3a45be733dbd8c88ebba9cf48d85486'),
)
CANDIDATES = (
    ('staging/tortuga-second-east-glowberry-candidate-1793251545970989500/glowberries-placement.json',
     '28cc5344f0a0b799232752ee296a4f0a372a2525f211024381c09a0f18b047ca'),
    ('staging/tortuga-northern-landmark-glowberry-candidate-1793252128031116000/manifest.json',
     'ed9e565779df87463fa4cca27690ae5b274556a3c123013d107be94658fdadd6'),
)
LEAVES = {'minecraft:oak_leaves','minecraft:azalea_leaves','minecraft:flowering_azalea_leaves'}
GROUND = GRAY | SOIL | set(PAVERS) | {'minecraft:gravel'}
NATURE_HOLDS = {(1235,72,-1237),(1240,63,-1200)}
MAX_OUTPUT = 32*MIB


def phase_files(home, reference, prefix):
    doc = checked(home, reference); folder = home/Path(reference[0]).parent
    fields = {}
    for suffix in ('before','placement','normal','after'):
        name = prefix+'-'+suffix+'.json'; row = doc['files'][name]; p = folder/name
        if digest(p) != row['sha256'] or p.stat().st_size != row['bytes']:
            raise UserError('Frozen phase changed: '+str(p))
        fields[suffix] = flatten(read_json(p))
    return fields


def area(q):
    x, _, z = q
    if 1224 <= x <= 1283 and -1264 <= z <= -1221:return 'Original Core'
    if z <= -1265 and 1282 <= x <= 1340:return 'Northern landmarks'
    if x <= 1223:return 'Drawbridge approach'
    return 'Eastern city'


def hanging_api(home):
    jars = (
        ('amendments-1.21-2.2.2-neoforge.jar','9c48c7c6ec4f743a4eb4c8e80473c7204e6632287b2c5bfeb370be27482618dc',
         'net/mehvahdjukaar/amendments/common/tile/HangingFlowerPotBlockTile.class'),
        ('moonlight-1.21.1-3.7.2-neoforge.jar','4a9f15108607cc70273f8a0b6eb24e1e99af8eef44bc3ae8681767ca7ce21b0f','net/mehvahdjukaar/moonlight/api/block/MimicBlockTile.class'),
    )
    rows = []
    for name, pin, member in jars:
        p = home/'server/mods'/name
        if not p.is_file() or p.stat().st_size > 4*MIB or (pin and digest(p) != pin):
            raise UserError('Exact bounded hanging-pot API JAR required')
        with zipfile.ZipFile(p) as z: raw = z.read(member)
        if name.startswith('moonlight') and (b'Mimic' not in raw or b'loadAdditional' not in raw or b'saveAdditional' not in raw):
            raise UserError('Pinned Mimic load/save API changed')
        rows.append({'jar':name,'jar_sha256':digest(p),'class':member,
                     'class_sha256':hashlib.sha256(raw).hexdigest()})
    return rows


def prepare(home, output):
    home, output = Path(home).resolve(), Path(output).resolve()
    if home.parent != Path('D:/A World for Two/staging/world-tests').resolve() or output.exists() or not output.is_relative_to(home/'staging'):
        raise UserError('New private artistic source folder required')
    reserve = guard(8*MIB,MAX_OUTPUT); budgets = [reader_budget()]
    if budgets[0]['available_bytes'] <= (1536+192)*MIB:
        raise UserError('Finite192MiB reader allowance would cross the live RAM gate')
    registry = read_json(home/'dashboard/settlement/registry.json')
    canonical = read_json(home/'dashboard/settlement/backup-receipt.json')
    snapshot = BackupWorld(home,{'id':CHECKPOINT[0],'sha256':CHECKPOINT[1],'verified':True},registry)
    ground, green = phase_files(home,BASE,'ground'), phase_files(home,BASE,'greenery')
    clips = phase_files(home,ENTRY,'seven-upper-grass-clips')
    spine = phase_files(home,ENTRY,'readable-pale-main-spine')
    context, written = {}, {}
    for phase in (ground,green,clips,spine):
        for q, v in phase['before'].items():
            if q in written and written[q] != v:
                raise UserError('Forecast phase has a stale prior write: '+str(q))
        context.update(phase['after']); written.update(phase['placement'])
    context.update(written)
    columns,mains,transport,walks,known,refs = source_masks(home)
    for label,relative,pin in NORTH:
        native = flatten(checked(home,(relative,pin))); known.update(native)
        refs.append({'role':label+' accepted backing only','sha256':pin})
    denied = cleanup_positions(checked(home,CLEANUP)) | NATURE_HOLDS
    old_candidates = set(flatten(checked(home,CANDIDATES[0])))
    north_candidate = checked(home,CANDIDATES[1]); candidate_folder = home/Path(CANDIDATES[1][0]).parent
    p = candidate_folder/'north-glowberries-placement.json'
    if digest(p) != north_candidate['files'][p.name]['sha256']:raise UserError('Frozen northern candidate changed')
    old_candidates.update(flatten(read_json(p)))
    denied |= old_candidates
    # Exact source pathways/entries; no blanket wall or guessed room exception.
    reserved_body, door_columns, window_views = set(),set(),set()
    for row in checked(home,CITY)['compounds']:
        ref = row['files']['SOURCE-ONLY']; d = checked(home,(ref['path'],ref['sha256'])); origin = d['origin']
        for route in d.get('routes',[]):
            for p in route.get('feet_local',[]):
                q = tuple(p[i]+origin[i] for i in range(3))
                reserved_body.update((q[0]+dx,q[1]+dy,q[2]+dz) for dx in(-1,0,1) for dz in(-1,0,1) for dy in(0,1,2))
        for e in d.get('entries',[]):
            q = tuple(e['outer_step'][i]+origin[i] for i in range(3))
            door_columns.update((q[0]+dx,q[2]+dz) for dx in range(-3,4) for dz in range(-3,4) if abs(dx)+abs(dz)<=3)
    for q,v in known.items():
        name = v.split('[')[0]
        if '_door' in name and 'trapdoor' not in name:
            door_columns.update((q[0]+dx,q[2]+dz) for dx in range(-3,4) for dz in range(-3,4) if abs(dx)+abs(dz)<=3)
        if 'window' not in name and 'glass' not in name:continue
        facing = properties(v).get('facing'); dirs = (FACES[facing],) if facing in FACES else tuple(FACES.values())
        for n in dirs:
            tangent = (1,0,0) if n[2] else (0,0,1)
            window_views.update(plus(plus(q,n,d),tangent,s)[:1]+(q[1]+dy,)+plus(plus(q,n,d),tangent,s)[2:]
                for d in(-2,-1,1,2) for s in(-1,0,1) for dy in(-1,0,1))
    walk_columns = walks | {(x+dx,z+dz) for x,y,z in spine['placement'] for dx in(-1,0,1) for dz in(-1,0,1)}
    for x in range(60):
        y = 65+grade(x)
        reserved_body.update((x+1224,y+dy,street_z(x)-1264+dz) for dz in(-1,0,1) for dy in(1,2,3))
    excluded_columns=mains|transport
    reserved=denied|reserved_body|window_views
    low_reserved=walk_columns|door_columns
    cache, floor_cache, floor_proofs, upper_cache = {}, {}, {}, {}; began = time.monotonic()
    def current(q):
        if q in cache:return cache[q]
        if time.monotonic()-began > 150:raise UserError('Finite150s botanical source read expired')
        if len(snapshot.chunks)>12:snapshot.chunks.clear()
        snapshot.chunk(q[0]//16,q[2]//16)
        cache[q] = context[q] if q in context else snapshot.state(q)
        if len(cache)%2048==0:budgets.append(reader_budget())
        return cache[q]
    def floor(x,z):
        if (x,z) not in floor_cache:
            floor_cache[x,z]=None
            for y in range(69,59,-1):
                if current((x,y,z)).split('[')[0] not in GROUND:continue
                offset=(x-1000,y-63,z+1270)
                def local(q):return tuple(q[i]+offset[i]for i in range(3))
                field,reason=ground_candidate(lambda q:current(local(q)),1000,-1270,set(),set(),
                    {tuple(q[i]-offset[i]for i in range(3))for q in snapshot.protected},accepted_floor=GROUND)
                if field:
                    floor_cache[x,z]=y;floor_proofs[x,z]={local(q):v for q,v in field.items()};break
        return floor_cache[x,z]
    def blocked(q, low=False):
        x,y,z = q
        if (x,z) not in columns or (x,z) in excluded_columns or q in reserved:return True
        if q in snapshot.protected or any(plus(q,n) in snapshot.protected for n in(*FACES.values(),(0,1,0),(0,-1,0))):return True
        fy = floor(x,z) if low else upper_floor(x,z)
        return fy is None or (low and (x,z) in low_reserved) or (not low and y<fy+4)
    def upper_floor(x,z):
        """Retain planted ground below upper displays; never call it walkable.

        Only the declared earlier botanical cells may occupy the lower body.
        The literal dry substrate and those plants remain exact witnesses.
        """
        if(x,z)not in columns or(x,z)in excluded_columns:return None
        ordinary=floor(x,z)
        if ordinary is not None:return ordinary
        if(x,z)in upper_cache:return upper_cache[x,z]
        upper_cache[x,z]=None
        for y in range(69,59,-1):
            q=(x,y,z)
            if current(q).split('[')[0]not in GROUND:continue
            body={(x,yy,z):forecast.get((x,yy,z),current((x,yy,z)))for yy in range(y+1,y+4)}
            if any(v.split('[')[0]not in VOIDS and p not in green['placement'] and p not in forecast for p,v in body.items()):continue
            proof={q:current(q)}|body
            for yy in range(y-1,y-9,-1):
                p=(x,yy,z);v=current(p);proof[p]=v
                if p in snapshot.protected or'waterlogged=true'in v:break
                if v.split('[')[0]in GRAVITY:continue
                if v.split('[')[0]in STABLE_NATURAL|GROUND:
                    upper_cache[x,z]=y;floor_proofs[x,z]=proof;return y
                break
        return None
    def existing_support(q):
        return q not in denied and q in known and known[q].split('[')[0] in STURDY and current(q).split('[')[0] == known[q].split('[')[0] and q not in snapshot.protected
    api = hanging_api(home)
    all_layers = []; forecast = {}; held = Counter()
    try:
        candidates = {(x+dx,z+dz) for x,y,z in ground['placement'] for dx in range(-3,4) for dz in range(-3,4)} & columns
        floors = {(x,z):floor(x,z) for x,z in sorted(candidates) if (x,z) not in excluded_columns}
        floors = {q:y for q,y in floors.items() if y is not None}
        for layer in (1,2):
            def look(q):return forecast.get(q,current(q))
            g = Garden(registry,look,snapshot.protected,reserved_body|window_views|denied,mains|transport)
            g.previous = {}; tags = {}; scenes = []; chosen = []
            def add(label,items,roots,kind):
                low = any(q[1] <= floors.get((q[0],q[2]),-100)+2 for q in items)
                if any(blocked(q,low=low) or q in g.blocks or (q in forecast) or look(q).split('[')[0] not in VOIDS for q in items):
                    held['retain body/view/plant/BE/earlier layer'] += 1;return False
                if any(q in snapshot.protected for q in roots):return False
                leafy={q:('minecraft:azalea_leaves' if v.split('[')[0]=='minecraft:flowering_azalea_leaves' else v)for q,v in items.items()}
                try:leaf_distances(leafy,lambda q:g.blocks.get(q,look(q)))
                except UserError:held['unknown native log/leaf tag beside proposed frond']+=1;return False
                for q,v in items.items():g.previous[q]=look(q);g.blocks[q]=v
                g.roots.update({q:look(q) for q in roots})
                for q in items:g.roots.update(floor_proofs.get((q[0],q[2]),{}))
                scenes.append({'label':label,'kind':kind,'area':area(next(iter(items))),
                               'targets':[list(q) for q in items],'root_witnesses':[list(q)for q in roots]})
                return True
            if layer == 1:
                # Actual three-clear-column pockets extend existing garden edges,
                # never the pale spine or a doorway. Reuse the original helper.
                class ExactObservedCells:
                    def __contains__(self,q):return True
                b,d,_,rows = open_garden_pockets(registry,'east',floors,look,mains,transport,
                    walk_columns,door_columns,snapshot.protected,ExactObservedCells(),green['placement']|forecast)
                for scene in rows:
                    targets = [tuple(q) for q in scene['targets']]
                    if any(q in denied or q in reserved_body|window_views or (q[0],q[2]) in walk_columns|door_columns for q in targets):continue
                    leafy={q:('minecraft:azalea_leaves' if d[q].split('[')[0]=='minecraft:flowering_azalea_leaves' else d[q])for q in targets}
                    try:leaf_distances(leafy,look)
                    except UserError:held['unknown native log/leaf tag beside proposed urn']+=1;continue
                    for q in targets:g.previous[q]=look(q);g.blocks[q]=d[q]
                    for q in targets:g.roots.update(floor_proofs.get((q[0],q[2]),{}))
                    witness_columns={(q[0],q[2])for q in targets}|set(map(tuple,scene.get('three_clear_columns_beyond',[])))
                    g.roots.update({q:v for q,v in b.items() if q not in targets and(q[0],q[2])in witness_columns})
                    scenes.append({**scene,'kind':'three-clear-column flower/shrub composition','area':area(targets[0])})
            # Hanging ivy follows independent solid masonry/timber returns, with
            # real support at every new segment and gaps around every window.
            if layer == 1:
                seen_columns = set()
                for wall,value in sorted(known.items(),key=lambda r:(r[0][2],r[0][0],r[0][1])):
                    if not existing_support(wall):continue
                    x,y,z = wall
                    for face,n in FACES.items():
                        p = plus(wall,n);fy = upper_floor(p[0],p[2])
                        token = p[0],p[2],face
                        if fy is None or y<fy+4 or y>fy+11 or token in seen_columns:continue
                        if any(abs(p[0]-a)+abs(p[2]-b)<3 for a,b in chosen):continue
                        points=[];roots=[]
                        for dy in range(6):
                            q=plus(p,(0,dy,0));root=plus(q,n,-1)
                            if not existing_support(root) or blocked(q) or look(q).split('[')[0] not in VOIDS or q in g.blocks:break
                            points.append(q);roots.append(root)
                        if len(points)<2:continue
                        flags={s:False for s in('north','south','east','west','up')}
                        flags[{'north':'south','south':'north','east':'west','west':'east'}[face]]=True
                        items={q:state(registry,'minecraft:vine',**flags) for q in points}
                        if add('Window-framing ivy at '+str(p),items,roots,'individually wall-rooted vertical ivy'):
                            chosen.append((p[0],p[2]));seen_columns.add(token)
                        break
            else:
                # A small number of existing-wall-rooted timber knees carry
                # mature berries. New timber/stair IDs cannot join any old
                # same-ID run: all neighbouring cells are literal witnesses.
                bracket_sites=[]
                for wall,v in sorted(known.items(),key=lambda row:(row[0][2],row[0][0],row[0][1])):
                    if len(bracket_sites)>=36:break
                    if v.split('[')[0]=='minecraft:dark_oak_log' or not existing_support(wall) or not existing_support(plus(wall,(0,-1,0))):continue
                    for face,n in FACES.items():
                        tip=plus(wall,n,2);fy=upper_floor(tip[0],tip[2])
                        if fy is None or wall[1]<fy+7 or wall[1]>fy+10:continue
                        if any(abs(tip[0]-x)+abs(tip[2]-z)<7 for x,z in bracket_sites):continue
                        logs=[plus(wall,n,k)for k in(1,2)]
                        knee=plus(logs[0],(0,-1,0));plants=[plus(tip,(0,-k,0))for k in(1,2,3)]
                        points=logs+[knee]+plants
                        if any(blocked(q)or q in g.blocks or look(q).split('[')[0]not in VOIDS for q in points):continue
                        neighbours={plus(q,d)for q in logs+[knee]for d in(*FACES.values(),(0,1,0),(0,-1,0))}-set(points)
                        if any(look(q).split('[')[0]in{'minecraft:dark_oak_log','minecraft:spruce_stairs'}for q in neighbours):continue
                        old=set(g.blocks)
                        try:berry_bracket(g,'Tortuga '+area(tip),wall,face,length=3)
                        except UserError:continue
                        if len(bracket_sites)%3==0:
                            # A deliberate flowering-basket variant of the same
                            # rooted frame. It replaces ONLY this new virtual
                            # berry chain, never an existing world object.
                            for q in plants:
                                g.blocks.pop(q,None);g.previous.pop(q,None);g.owners.pop(q,None)
                            pot=plants[0]
                            g.put('Tortuga '+area(tip),pot,'amendments:hanging_flower_pot',light_level=0)
                            flower=('minecraft:potted_fern','minecraft:potted_allium','minecraft:potted_flowering_azalea_bush')[len(bracket_sites)//3%3]
                            tags[pot]='{Mimic:{Name:'+json.dumps(flower)+'}}'
                            kind='wall-bracket-hung real flowering display'
                        else:kind='supported timber-knee mature berry bracket'
                        new=set(g.blocks)-old;g.roots.update({q:look(q)for q in neighbours})
                        scenes.append({'label':'Wall-rooted carved garden bracket '+str(wall),'kind':kind,
                            'area':area(tip),'targets':[list(q)for q in sorted(new)],'root_witnesses':[list(wall)]})
                        bracket_sites.append((tip[0],tip[2]));break
                # Sculpted small upper fronds extend OUR forecast first-pass
                # garlands, not unknown natural trees or living-growth fields.
                for root,v in sorted(green['placement'].items()):
                    if v.split('[')[0] not in LEAVES or 'persistent=true' not in v:continue
                    fy=upper_floor(root[0],root[2])
                    if fy is None or root[1]<fy+4:continue
                    if any(sum(abs(a-b)for a,b in zip(root,p))<4 for p in chosen):continue
                    tangent=(1,0,0) if any((root[0],root[2]+dz)in mains for dz in(-1,1))else(0,0,1)
                    points=(plus(root,(0,1,0)),plus(plus(root,(0,1,0)),tangent),plus(root,tangent))
                    items={q:state(registry,'minecraft:flowering_azalea_leaves' if i==1 else 'minecraft:oak_leaves',distance=7,persistent=True,waterlogged=False)for i,q in enumerate(points)}
                    if add('Layered flowering eave frond '+str(root),items,[root],'small higher leaf/drape wing'):chosen.append(root)
                # Native hanging pots and mature berry chains share real accepted
                # soffits, but alternate content, height and spacing by frontage.
                used=[]
                for wall,v in sorted(known.items(),key=lambda r:(r[0][2],r[0][0],r[0][1])):
                    x,y,z=wall
                    if(x,z)in excluded_columns or v.split('[')[0]not in STURDY:continue
                    fy=upper_floor(x,z)
                    if fy is None or not fy+5<=y<=fy+13 or not existing_support(wall):continue
                    if any(abs(x-a)+abs(z-b)<2 for a,b in used):continue
                    top=(x,y-1,z)
                    if blocked(top) or top in g.blocks or look(top).split('[')[0] not in VOIDS:continue
                    number=len(used)
                    if number%4==0 and len(tags)<48:
                        flower=('minecraft:potted_fern','minecraft:potted_allium','minecraft:potted_flowering_azalea_bush')[number//4%3]
                        items={top:state(registry,'amendments:hanging_flower_pot',light_level=0)}
                        if add('Native hanging flowering display '+str(top),items,[wall],'native planted hanging flower pot'):
                            tags[top]='{Mimic:{Name:'+json.dumps(flower)+'}}';used.append((x,z))
                    elif number%4==1:
                        items={top:state(registry,'minecraft:lantern',hanging=True,waterlogged=False)}
                        if add('Warm soffit task lantern '+str(top),items,[wall],'small warm hanging lantern'):used.append((x,z))
                    else:
                        length=min(3,y-fy-4);points=[(x,y-1-n,z)for n in range(length)]
                        items={q:state(registry,'minecraft:cave_vines',age=25,berries=True) if i==len(points)-1 else state(registry,'minecraft:cave_vines_plant',berries=True) for i,q in enumerate(points)}
                        if add('Abundant mature berry pendant '+str(top),items,[wall],'mature age25 rooted glowberry chain'):used.append((x,z))
            if not g.blocks:raise UserError('No qualified additional botanical scenes in layer'+str(layer))
            modelled={q:('minecraft:azalea_leaves' if v.split('[')[0]=='minecraft:flowering_azalea_leaves' else v)for q,v in g.blocks.items()}
            for q,distance in leaf_distances(modelled,lambda p:g.blocks.get(p,look(p))).items():
                g.blocks[q]=state(registry,g.blocks[q].split('[')[0],distance=distance,persistent=True,waterlogged=False)
                for n in(*FACES.values(),(0,1,0),(0,-1,0)):
                    other=plus(q,n)
                    if other not in g.blocks:g.roots[other]=look(other)
            before = {q:look(q) for q in set(g.previous)|set(g.roots)}
            delta = {q:v for q,v in g.blocks.items() if v!=before[q]}
            if len(delta)>12000:raise UserError('Split botanical layer over12000 targets')
            rule=require_outdoor_rule(delta,'additional East botanical layer'+str(layer))
            if set(delta)&(reserved_body|window_views|denied|snapshot.protected):raise UserError('Final body/view/BE conflict')
            all_layers.append({'before':before,'delta':delta,'tags':tags,'scenes':scenes,'rule':rule})
            forecast.update(delta)
        saved=list(snapshot.sources)
        poses=[]
        for label,anchor in(('Original Core',(1252,-1244)),('Northern landmarks',(1311,-1293)),
                             ('Eastern city',(1280,-1200)),('Drawbridge approach',(1218,-1220))):
            candidates=sorted((p for p in floors if area((p[0],0,p[1]))==label),key=lambda p:(p[0]-anchor[0])**2+(p[1]-anchor[1])**2)
            for x,z in candidates:
                y=floors[x,z]+1
                if any((forecast.get((x+dx,y+dy,z+dz),current((x+dx,y+dy,z+dz)))).split('[')[0]not in VOIDS
                       for dx in(-1,0,1)for dz in(-1,0,1)for dy in(0,1)):continue
                scenes=[s for layer in all_layers for s in layer['scenes']if s['area']==label]
                target=next((q for s in scenes for q in s['targets']if 5<=abs(q[0]-x)+abs(q[2]-z)<=18 and q[1]>=y+2),None)
                if target is None:continue
                poses.append({'area':label,'feet':[x+.5,y,z+.5],'look_at':[target[0]+.5,target[1]+.5,target[2]+.5],
                    'source_after_three_by_three_two_high_air_and_retained_floor':True,
                    'native_model_render_or_walking_acceptance':False});break
    finally:snapshot.close()
    docs={};layers=[]
    if set(all_layers[0]['delta'])&set(all_layers[1]['delta']):
        raise UserError('The two independent new placement scopes overlap')
    for number,layer in enumerate(all_layers,2):
        old,change,tags=layer['before'],layer['delta'],layer['tags']
        sequential_old=old
        if number==3:
            old=dict(old)
            for q in old.keys()&all_layers[0]['delta'].keys():old[q]=all_layers[0]['before'][q]
            # No new structural/root material in pass3 comes from pass2. Check
            # that omitting pass2 also preserves exact native leaf distances.
            mapped={q:('minecraft:azalea_leaves'if v.split('[')[0]=='minecraft:flowering_azalea_leaves'else v)for q,v in change.items()}
            for q,distance in leaf_distances(mapped,lambda p:change[p]if p in change else old[p]).items():
                if properties(change[q]).get('distance')!=str(distance):
                    raise UserError('Pass3 leaf state actually depends on pass2')
        for suffix,field,verify in(('before',old,True),('placement',change,False),('normal',change,True),('after',old|change,True)):
            priorities={}
            for q,v in field.items():
                name=v.split('[')[0]
                if name in ('minecraft:cave_vines','minecraft:cave_vines_plant'):priorities[q]=500-q[1]
                elif name in SOIL or name.endswith(('_log','_wood','_stairs')):priorities[q]=0
                elif 'half=upper'in v:priorities[q]=101
                else:priorities[q]=100
            d=payload(registry,canonical['sha256'],field,'SOURCE ONLY rich East botanical pass'+str(number)+' '+suffix,before=verify,priority=priorities if not verify else None)
            if suffix in('placement','after'):d['block_entities']=[{'pos':list(q),'nbt':v}for q,v in sorted(tags.items())]
            d.update(construction_forbidden=True,source_observed_checkpoint_id=CHECKPOINT[0],source_observed_checkpoint_sha256=CHECKPOINT[1],
                requires_actual_ground_greenery_entry_completion=True,fresh_native_current_before_required=True,
                earlier_91_glowberry_candidates_reserved_NOT_assumed_placed=True)
            d['independent_new_placement_scope']=True
            docs['pass'+str(number)+'-'+suffix+'.json']=d
        if number==3:
            for suffix,field in(('before',sequential_old),('after',sequential_old|change)):
                d=payload(registry,canonical['sha256'],field,'VERIFY ONLY same pass3 after optional pass2 '+suffix,before=True)
                if suffix=='after':d['block_entities']=[{'pos':list(q),'nbt':v}for q,v in sorted(tags.items())]
                d.update(construction_forbidden=True,source_observed_checkpoint_id=CHECKPOINT[0],source_observed_checkpoint_sha256=CHECKPOINT[1],
                    requires_actual_ground_greenery_entry_completion=True,requires_completed_new_botanical_pass=2,
                    same_unchanged_pass3_placement_and_normal_files=True)
                docs['pass3-after-pass2-'+suffix+'.json']=d
        layers.append({'pass':number,'new_cells':len(change),'new_hanging_pot_BEs':len(tags),
            'scene_counts':dict(Counter(s['kind']for s in layer['scenes'])),
            'area_counts':dict(Counter(s['area']for s in layer['scenes'])),
            'scenes':layer['scenes'],'rule':layer['rule']})
    raw={name:(json.dumps(d,separators=(',',':'))+'\n').encode()for name,d in docs.items()}
    manifest={'format':'awft-two-further-rich-east-botanical-passes:1','created':utcnow(),'source_sha256':digest(Path(__file__)),
        'source_checkpoint_id':CHECKPOINT[0],'source_checkpoint_sha256':CHECKPOINT[1],
        'required_first_phases':[{'path':p,'sha256':s}for p,s in(BASE,ENTRY)],
        'ground_actual_greenery_entry_forecast_only_until_native_markers':True,'layers':layers,
        'doors_windows_three_wide_routes_and_current_machinery_preserved':True,
        'new_passes_have_disjoint_writes_and_no_structural_dependency':True,
        'pass3_context_choice':'Default before/after starts after base ground+green+entry alone. If pass2 is done, use pass3-after-pass2-before/after with the identical pass3 placement/normal.',
        'old91_candidate_targets_not_used':len(old_candidates),'held':dict(held),'saved_sources':saved,
        'no_existing_BE_or_inventory_tag_replay':True,'hanging_pot_api':api,
        'new_pot_NBT_basis':'Pinned Moonlight MimicBlockTile loadAdditional/saveAdditional Mimic compound, native NbtUtils blockstate Name; new FlowerPot content only, no Items/Owner',
        'representative_native_QA_pose_metadata':poses,
        'actual_native_survival_render_collision_walking_and_art_acceptance':False,'native_actions':0,'world_writes':0,
        'reader_peak_RSS_bytes':max(b['owned_reader_rss_bytes']for b in budgets),'reserve_guard':reserve,
        'files':{name:{'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}for name,data in raw.items()}}
    raw['manifest.json']=(json.dumps(manifest,separators=(',',':'))+'\n').encode()
    if sum(map(len,raw.values()))>MAX_OUTPUT:raise UserError('Finite32MiB output exceeded')
    output.mkdir()
    for name,data in raw.items():(output/name).open('xb').write(data)
    return{'folder':str(output),'manifest_sha256':digest(output/'manifest.json'),
           'layers':[{k:v for k,v in row.items()if k not in('scenes','rule')}for row in layers],
           'native_actions':0,'world_writes':0}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--home',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    print(json.dumps(prepare(**vars(p.parse_args())),indent=2))
