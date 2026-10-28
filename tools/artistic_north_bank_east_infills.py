"""The remaining22 original eastern houses, courts and continuous pirate lanes.

Shared timber joints/furniture models do not serialize or stamp a house. Each
authored program has its own plot, massing, roof, storeys, upper subtraction,
palette, rotated room layout, shop stock, corner fittings and doorstep access.
Native/art acceptance is deliberately outside this source-only producer.
"""
from __future__ import annotations
import argparse
from collections import deque
from dataclasses import replace
import hashlib,json,time
from pathlib import Path

from control_room.common import UserError,digest,read_json
from tools.artistic_bridge_refinement import flatten
from tools.artistic_materials import require_material_rule,require_outdoor_rule
from tools.artistic_north_bank_east import (EastPlan,Lot,NorthTerrain,AIR,GROUND,SOFT,NORTH_SOFT,MIB,FACES,
    pave,native_payload,canonical_parts,base)
from tools.artistic_north_bank_east_masterplan import TIDEFOLD,LANTERN_FOLD,EAST_HOOK
from tools.artistic_north_bank_compass_bend import (articulated_shell,furniture_story,frontage,furniture,ITEMS,
    ROSE_REL,ROSE_SHA)
from tools.artistic_north_bank_west import rotate_state
from tools.playtest import guard

COMPASS='staging/north-bank-compass-bend-1793156177505399400/prototype.json'
COMPASS_SHA='cc83762b5e3e8476dc2e26ade1d84c21bca545e937d64938cbf0f43afa393b1e'
# Saved copper/coal ore are unchanged ordinary full-cube vanilla footings,
# not a surface-soil candidate or permission to excavate/replace ore.
RETAINED_FULL_GEOLOGY={'minecraft:copper_ore','minecraft:coal_ore'}

# Deliberate room/trade/massing combinations. North-facing houses are actually
# rotated, including their asymmetric floor masks and every furniture model;
# there is no pasted north/south facade around an unrotated room.
STYLES={
 'pippins-net':('seabird-ledger',('minecraft:bricks','dawnoftimebuilder:plastered_stone'),('Net-mending shop, fishing table and galley','Mariner bedroom, tea window and private chest'),('minecraft:fishing_rod','minecraft:string','minecraft:cod','minecraft:compass')),
 'marigold-steps':('three-kestrels',('minecraft:stone_bricks','minecraft:yellow_terracotta','dawnoftimebuilder:blue_plastered_stone'),('Three-generation supper, pantry and storytelling seat','Shared family bedroom and reading corner','Set-back elder bedroom and washing gallery'),('minecraft:bread','minecraft:apple','minecraft:book','minecraft:honey_bottle')),
 'blue-quilt':('ink-tern',('minecraft:bricks','dawnoftimebuilder:blue_plastered_stone','minecraft:white_terracotta'),('Cloth cutting, fittings and a quilt display','Family kitchen and linen library','Set-back seamstress bedroom and fine roof gallery'),('minecraft:shears','minecraft:string','minecraft:leather','minecraft:blue_wool')),
 'copper-window':('brass-finch',('minecraft:stone_bricks','dawnoftimebuilder:red_plastered_stone'),('Copperware bench, bright display and customer stools','Trader bedroom, supper and account desk'),('minecraft:copper_ingot','minecraft:gold_nugget','minecraft:amethyst_shard','minecraft:shears')),
 'juniper-son':('rosemary-court',('minecraft:bricks','dawnoftimebuilder:green_plastered_stone'),('Toy-carving workbench, timber samples and little display','Carver household kitchen, toy shelf and bed'),('minecraft:stick','minecraft:wooden_sword','minecraft:honeycomb','minecraft:book')),
 'azure-key':('salt-wind',('minecraft:stone_bricks','minecraft:cyan_terracotta','minecraft:light_gray_terracotta'),('Retired navigator sitting room and galley','Map library, warm table and bedroom','Set-back lookout bedroom and sun gallery'),('minecraft:map','minecraft:compass','minecraft:spyglass','minecraft:book')),
 'roseate-corner':('three-kestrels',('minecraft:bricks','dawnoftimebuilder:red_plastered_stone','dawnoftimebuilder:plastered_stone'),('Family kitchen and pottery-lined sitting corner','Two sleeping nooks and household desk','Unequal set-back roof room and flower gallery'),('minecraft:brick','minecraft:flower_pot','minecraft:book','minecraft:bread')),
 'long-tide':('brass-finch',('minecraft:stone_bricks','dawnoftimebuilder:blue_plastered_stone'),('Marine glass bench, supervised display and tools','Glazier household supper and quiet bedroom'),('minecraft:glass_bottle','minecraft:amethyst_shard','minecraft:spyglass','minecraft:book')),
 'fernhook':('rosemary-court',('minecraft:bricks','dawnoftimebuilder:green_plastered_stone'),('Compact herb kitchen and hooked entrance seat','Flower-window bedroom and morning desk'),('minecraft:wheat_seeds','minecraft:fern','minecraft:apple','minecraft:book')),
 'willow-button':('salt-wind',('minecraft:stone_bricks','minecraft:green_terracotta','dawnoftimebuilder:yellow_plastered_stone'),('Dressmaker loom, cloth displays and fittings','Family supper, linen shelves and shared bedroom','Set-back sewing gallery and quiet bedroom'),('minecraft:shears','minecraft:string','minecraft:leather','minecraft:green_wool')),
 'orchard-key':('ink-tern',('minecraft:bricks','dawnoftimebuilder:green_plastered_stone','minecraft:white_terracotta'),('Herbalist library, seed counter and tea seat','Family herb pantry, dining table and bedroom','Set-back library room and roof gallery'),('minecraft:wheat_seeds','minecraft:allium','minecraft:honey_bottle','minecraft:book')),
 'moth-candle':('seabird-ledger',('minecraft:stone_bricks','dawnoftimebuilder:yellow_plastered_stone'),('Wax bench, candle display and little lamp counter','Candlemaker kitchen, bed and high-light reading corner'),('minecraft:honeycomb','minecraft:candle','minecraft:string','minecraft:book')),
 'honeysuckle-fold':('salt-wind',('minecraft:bricks','minecraft:green_terracotta','dawnoftimebuilder:plastered_stone'),('Loom workshop, textile windows and covered service recess','Weaver family supper and bedroom','Set-back linen room, bed and private gallery'),('minecraft:string','minecraft:white_wool','minecraft:shears','minecraft:book')),
 'starlings-rest':('ink-tern',('minecraft:stone_bricks','dawnoftimebuilder:blue_plastered_stone','minecraft:yellow_terracotta'),('Cargo ledger office, account desk and harbor books','Family kitchen and conversation salon','Set-back bedroom, travel trunks and private gallery'),('minecraft:paper','minecraft:book','minecraft:compass','minecraft:feather')),
 'greycap-terrace':('three-kestrels',('minecraft:bricks','dawnoftimebuilder:plastered_stone'),('Retired harbor-workers kitchen, chess-like tea table and lounge','Quiet bedroom, memory shelf and flower window'),('minecraft:compass','minecraft:book','minecraft:cookie','minecraft:bread')),
 'lantern-watch':('brass-finch',('minecraft:stone_bricks','dawnoftimebuilder:yellow_plastered_stone','minecraft:cyan_terracotta'),('Compact lookout household and instrument shelf','Shared sleeping room and kitchen desk','Inhabited narrow lantern-gable room'),('minecraft:spyglass','minecraft:compass','minecraft:clock','minecraft:book')),
 'driftglass':('brass-finch',('minecraft:bricks','dawnoftimebuilder:blue_plastered_stone'),('Potter workbench, ceramic display and sheltered counter','Narrow household bedroom and window supper'),('minecraft:clay_ball','minecraft:brick','minecraft:flower_pot','minecraft:book')),
 'sea-lavender':('rosemary-court',('minecraft:stone_bricks','dawnoftimebuilder:plastered_stone','minecraft:light_gray_terracotta'),('Flower collector counter, seed library and tea nook','Family supper, sleeping nook and herb shelves','High-light bedroom and flower-window desk'),('minecraft:allium','minecraft:flower_pot','minecraft:wheat_seeds','minecraft:book')),
 'amberwake':('seabird-ledger',('minecraft:bricks','dawnoftimebuilder:yellow_plastered_stone'),('Sea-chest sitting room, galley and sheltered entry','Sailor bedroom, memory shelf and roof desk'),('minecraft:compass','minecraft:nautilus_shell','minecraft:bread','minecraft:book')),
 'turnstone':('three-kestrels',('minecraft:stone_bricks','dawnoftimebuilder:red_plastered_stone','minecraft:green_terracotta'),('Extended-family kitchen and storytelling corner','Shared bedroom, linen and writing seat','Set-back elder room and roof terrace'),('minecraft:bread','minecraft:apple','minecraft:cookie','minecraft:book')),
 'masons-hearth':('brass-finch',('minecraft:bricks','dawnoftimebuilder:plastered_stone'),('Stoneworker samples, workbench and warm sitting room','Mason household supper, bed and reading corner'),('minecraft:brick','minecraft:quartz','minecraft:iron_pickaxe','minecraft:book')),
 'east-hook':('seabird-ledger',('minecraft:stone_bricks','dawnoftimebuilder:blue_plastered_stone'),('Compact captain galley, charts and sheltered entry','Narrow sea-view bedroom and account desk'),('minecraft:map','minecraft:compass','minecraft:spyglass','minecraft:book')),
}
INTENTS=(*TIDEFOLD,*LANTERN_FOLD,*EAST_HOOK)
OPPOSITE={'sw':'ne','se':'nw','nw':'se','ne':'sw'}


def rotate_point(q,center,turn):
    x,y,z=q;cx,cz=center
    if turn==2:return 2*cx-x,y,2*cz-z
    if turn==0:return x,y,z
    raise UserError('This authored infill uses only explicit north/south half-turns')


def house(registry,fine,row):
    alias,finish,rooms,stock=STYLES[row.ident];turn=2 if row.face in ('north','east') else 0
    shape=row.shape
    if turn:shape=shape.rsplit('_',1)[0]+'_'+OPPOSITE[shape.rsplit('_',1)[1]]
    local_face='south' if row.face=='north' else 'west' if row.face=='east' else row.face
    local=Lot(alias,row.name,row.use,row.center,row.size,row.stories,local_face,shape,row.roof,finish,rooms,row.motif)
    if turn:
        def xz(q):x,y,z=rotate_point((q[0],0,q[1]),row.center,2);return x,z
        mapped={'samples':[dict(q,x=xz((q['x'],q['z']))[0],z=xz((q['x'],q['z']))[1]) for q in fine['samples']],
            'saved_BEs':[list(rotate_point(q,row.center,2)) for q in fine['saved_BEs']],
            'protected_columns_xz':[list(xz(q)) for q in fine['protected_columns_xz']]}
    else:mapped=fine
    p=EastPlan(registry,mapped);cells,floor,door=articulated_shell(p,local);furniture_story(p,local,cells,floor,door)
    frontage(p,replace(local,ident='seabird-ledger') if local.face=='west' else local,cells,floor)
    # The palette/fittings are shared native components; each actual shelf's
    # authored stock matches its real trade rather than the furniture recipe.
    old_stock=ITEMS[alias]
    for q,tag in list(p.tags.items()):
        for old,new in zip(old_stock,stock):
            if new not in registry['items']:raise UserError('Unknown authored trade item '+new)
            tag=tag.replace('id:'+json.dumps(old),'id:'+json.dumps(new))
        p.tags[q]=tag.replace('Compass Bend',row.name)
    # Compact rooms receive an additional genuine reading/potting grouping,
    # never a lower circulation standard or a low hanging light.
    for room in p.rooms:
        f=room['floor_y'];field=set(map(tuple,room['floor_cells']));x0=min(x for x,z in field);z0=min(z for x,z in field)
        start=len(p.fixtures)
        for x,z in ((x0+1,z0+1),(x0+2,z0+1)):
            if base(p.blocks.get((x,f,z),'minecraft:air')) not in AIR:
                furniture(p,(x,f+1,z),'dawnoftimebuilder:birch_footstool',support=(x,f,z),facing='east',waterlogged=False)
        if base(p.blocks.get((x0+1,f+1,z0+1),'minecraft:air')) not in AIR:
            furniture(p,(x0+1,f+2,z0+1),'minecraft:potted_allium',support=(x0+1,f+1,z0+1))
        room['furnishing_objects']+=len(p.fixtures)-start
    p.blocks={rotate_point(q,row.center,turn):(s if base(s)=='mcwwindows:dark_oak_plank_window' else rotate_state(registry,s,turn)) if turn else s for q,s in p.blocks.items()}
    # Macaw windows use an axis plane for their joined mask. Half-turns retain
    # that plane; normalize it before deriving the final native neighbor parts.
    for q,s in list(p.blocks.items()):
        if base(s).startswith('mcwwindows:') and 'part=' in s:
            s=s.replace('facing=south','facing=north').replace('facing=west','facing=east');p.blocks[q]=s
    p.owners={rotate_point(q,row.center,turn):v for q,v in p.owners.items()};p.priority={rotate_point(q,row.center,turn):v for q,v in p.priority.items()}
    p.tags={rotate_point(q,row.center,turn):v for q,v in p.tags.items()};p.walk=[rotate_point(q,row.center,turn) for q in p.walk]
    for r in p.rooms:
        r['building']=row.ident
        for key in ('floor_cells','actual_floor_outline'):
            if key in r:r[key]=[[rotate_point((x,0,z),row.center,turn)[i] for i in (0,2)] for x,z in r[key]]
        if 'gallery_door' in r:r['gallery_door']=list(rotate_point(r['gallery_door'],row.center,turn))
    for r in p.fixtures:r['position']=list(rotate_point(r['position'],row.center,turn))
    for r in p.supports:
        r['fixture']=list(rotate_point(r['fixture'],row.center,turn));r['support']=list(rotate_point(r['support'],row.center,turn))
    lot=p.lots[0];lot.update(id=row.ident,front=row.face,door=list(rotate_point(lot['door'],row.center,turn)),
        main_footprint=[[rotate_point((x,0,z),row.center,turn)[i] for i in (0,2)] for x,z in lot['main_footprint']])
    for witness in lot['dry_proof']['actual_dry_columns']:witness['support']=list(rotate_point(witness['support'],row.center,turn))
    lot['source_room_rotation_degrees']=turn*90
    return p


def merge(target,source):
    for q,s in source.blocks.items():
        old=target.blocks.get(q)
        if old is not None and old!=s:
            if base(s) in AIR:continue
            if base(old) not in AIR:raise UserError('Two authored infill solids overlap: '+str((q,old,s)))
        target.blocks[q]=s;target.owners[q]=source.owners[q];target.priority[q]=source.priority[q]
        if q in source.tags:target.tags[q]=source.tags[q]
    for key in ('lots','rooms','fixtures','supports','walk'):getattr(target,key).extend(getattr(source,key))


def route_nodes(points):
    result=[]
    for a,b in zip(points,points[1:]):
        n=max(abs(a[0]-b[0]),abs(a[1]-b[1]))
        result.extend((round(a[0]+(b[0]-a[0])*i/max(1,n)),round(a[1]+(b[1]-a[1])*i/max(1,n))) for i in range(n+1))
    return list(dict.fromkeys(result))


def street(p,prior):
    p.group='Continuous eastern village lanes';adopted={};centres=set()
    def available(x,z):
        for dx in (-1,0,1):
            for dz in (-1,0,1):
                a,b=x+dx,z+dz;r=p.land.get((a,b),{})
                if (a,b) in p.protected or r.get('kind') not in ('dry','retained_object'):return False
                y=r.get('surface_y',0)
                if r['kind']=='retained_object' and base(prior.get((a,y,b),'minecraft:air')) not in {'minecraft:cobblestone','minecraft:polished_andesite','minecraft:mossy_cobblestone','minecraft:chiseled_stone_bricks'}:return False
                for dy in (1,2):
                    if base(p.blocks.get((a,y+dy,b),'minecraft:air')) not in AIR:return False
        return True
    def find(start,end):
        # Only a small controlled detour between authored bends/doorsteps.
        margin=8;bounds=min(start[0],end[0])-margin,min(start[1],end[1])-margin,max(start[0],end[0])+margin,max(start[1],end[1])+margin
        todo=deque([start]);previous={start:None}
        while todo:
            q=todo.popleft()
            if q==end:
                path=[]
                while q is not None:path.append(q);q=previous[q]
                return path[::-1]
            if len(previous)>8000:break
            candidates=sorted(((q[0]+dx,q[1]+dz) for dx,dz in FACES.values()),key=lambda c:abs(c[0]-end[0])+abs(c[1]-end[1]))
            for n in candidates:
                if n in previous or not bounds[0]<=n[0]<=bounds[2] or not bounds[1]<=n[1]<=bounds[3] or not available(*n):continue
                previous[n]=q;todo.append(n)
        raise UserError('No actual dry three-wide route between authored junctions '+str((start,end)))
    def lay(nodes):
        path=[]
        for a,b in zip(nodes,nodes[1:]):path.extend(find(a,b))
        centres.update(path)
        for x,z in path:
            for dx in (-1,0,1):
                for dz in (-1,0,1):
                    a,b=x+dx,z+dz;r=p.land[a,b];y=r['surface_y'];q=a,y,b
                    if r['kind']=='retained_object':
                        for dy in (0,1,2):adopted[a,y+dy,b]=prior[a,y+dy,b]
                    else:
                        pave(p,a,b)
                    for dy in (1,2):p.walk.append((a,y+dy,b))
        return path
    # Opposed front doors frame the same lane; no gap is left as an anonymous
    # lawn separating "neighborhood phases". Later rows link through three
    # narrow crooked cross alleys and inhabited back courts.
    paths=(
      ((1230,-1197),(1240,-1197),(1255,-1196),(1272,-1197),(1290,-1197),(1307,-1196),(1324,-1197),(1341,-1196)),
      ((1232,-1176),(1247,-1175),(1262,-1176),(1278,-1175),(1294,-1176),(1310,-1175),(1326,-1176),(1344,-1175)),
      ((1236,-1155),(1250,-1154),(1266,-1155),(1282,-1154),(1298,-1155),(1314,-1154),(1330,-1155),(1344,-1154),(1350,-1152)),
      ((1247,-1197),(1247,-1181),(1247,-1175),(1247,-1163),(1247,-1154)),
      ((1278,-1197),(1278,-1180),(1279,-1175),(1279,-1164),(1279,-1154)),
      ((1341,-1196),(1341,-1181),(1344,-1175),(1344,-1163),(1344,-1154)),
    )
    for path in paths:lay(path)
    for row in p.lots:
        dx,dz=FACES[row['front']];x,feet,z=row['door'];floor=feet-1;rise=floor-p.land[x+dx,z+dz]['surface_y'];p.group=row['name']
        if not 1<=rise<=3:raise UserError('Actual retained threshold needs a separate height design')
        for n in range(1,rise+1):
            a,b=x+n*dx,z+n*dz;y=floor-n+1
            for yy in range(p.land[a,b]['surface_y']+1,y):p.put((a,yy,b),'minecraft:stone_bricks',priority=97)
            p.put((a,y,b),'minecraft:stone_brick_stairs',priority=98,facing={'north':'south','south':'north','west':'east','east':'west'}[row['front']],half='bottom',shape='straight',waterlogged=False)
        start=x+(rise+1)*dx,z+(rise+1)*dz
        targets=sorted(centres,key=lambda q:abs(q[0]-start[0])+abs(q[1]-start[1]))[:6]
        p.group='Continuous eastern village lanes'
        failure=None
        for end in targets:
            try:lay((start,end));failure=None;break
            except UserError as e:failure=e
        if failure:raise failure
    p.retained=adopted


def construct(registry,fine,prior):
    p=EastPlan(registry,fine)
    for row in INTENTS:merge(p,house(registry,fine,row))
    street(p,prior);canonical_parts(p)
    p.cameras=[{'name':'tidefold-facing-bend','feet':[1254.5,64,-1196.5],'look_at':[1269,73,-1186]},
        {'name':'lantern-fold-court','feet':[1279.5,64,-1175.5],'look_at':[1287,74,-1166]},
        {'name':'east-hook-bend','feet':[1309.5,64,-1154.5],'look_at':[1323,71,-1144]}]
    return p


def check(p):
    checks=[]
    for row in p.lots:checks.append(require_material_rule({q:s for q,s in p.blocks.items() if p.owners[q]==row['name']},row['name']+' complete inhabited infill'))
    require_outdoor_rule(p.blocks,'All22 eastern infills and continuous public lanes')
    blocked=[q for q in set(p.walk) if base(p.blocks.get(q,'minecraft:air')) not in AIR and not any(v in base(p.blocks[q]) for v in ('door','stairs'))]
    if blocked:raise UserError('Actual new route was blocked '+str(blocked[:8]))
    for r in p.fixtures:
        if base(p.blocks.get(tuple(r['position']),'minecraft:air'))!=r['block']:raise UserError('A furnished native model was overwritten')
    return {'material_checks':checks,'outdoor_max9':True,'fully_modeled_buildings':len(p.lots),'inhabited_rooms':len(p.rooms),
        'actual_furnishing_models':len(p.fixtures),'source_body_route_cells':len(set(p.walk)),'native_or_art_acceptance':False}


def encode(value):return (json.dumps(value,separators=(',',':'),ensure_ascii=False)+'\n').encode()


def prepare(home,fine_path,checkpoint_id,checkpoint_sha):
    home=Path(home).resolve();fine_path=Path(fine_path).resolve()
    if home.parent!=Path('D:/A World for Two/staging/world-tests').resolve() or not fine_path.is_relative_to(home/'staging'):raise UserError('Owned private original town source only')
    reserve=guard(4*MIB,64*MIB);current=read_json(home/'dashboard/settlement/backup-receipt.json')
    if current.get('verified') is not True or current.get('id')!=checkpoint_id or current.get('sha256')!=checkpoint_sha:raise UserError('Exact actual stopped backup required')
    if fine_path.stat().st_size>16*MIB:raise UserError('Bounded full measured field required')
    fine=read_json(fine_path)
    if fine.get('checkpoint_sha256')!=checkpoint_sha:raise UserError('Actual fine field/checkpoint mismatch')
    prior={};provenance=[]
    for relative,sha in ((ROSE_REL,ROSE_SHA),(COMPASS,COMPASS_SHA)):
        path=home/relative
        if digest(path)!=sha:raise UserError('Exact frozen previous source required')
        prior.update(flatten(read_json(path)));provenance.append({'path':relative,'sha256':sha,'role':'Immutable accepted/previous exact native preimage; preserve all BEs/solids/AIR'})
    registry=read_json(home/'dashboard/settlement/registry.json');p=construct(registry,fine,prior);proof=check(p)
    before={};states={};retained=dict(p.retained);supports={};terrain=NorthTerrain(home,current,registry)
    try:
        for q,s in sorted(p.blocks.items(),key=lambda v:(v[0][0]//16,v[0][2]//16,v[0][1])):
            if q in prior:
                if s!=prior[q]:raise UserError('Preserve every previous source solid or authored AIR '+str((q,s,prior[q])))
                retained[q]=s;continue
            old=terrain.state(*q)
            if old is None or q in terrain.entities or base(old) not in AIR|GROUND|SOFT|NORTH_SOFT or 'waterlogged=true' in old:raise UserError('Preserve actual BE, water, tree or foreign block '+str((q,old)))
            states[q]=s;before[q]=old;terrain.check()
        lowest={}
        for q in states:
            key=p.owners[q],q[0],q[2];lowest[key]=min(lowest.get(key,q[1]),q[1])
        for row in p.lots:
            for x,z in row['main_footprint']:
                y=lowest.get((row['name'],x,z))
                if y is None:continue
                q=x,y-1,z;actual=terrain.state(*q)
                if actual is None or q in terrain.entities or base(actual) not in GROUND|RETAINED_FULL_GEOLOGY:raise UserError('Actual retained full foundation course missing '+str((row['id'],q,actual)))
                supports[q]=actual
        sources=terrain.snapshot.sources
    finally:terrain.close()
    docs={'prototype.json':native_payload(registry,states,checkpoint_sha,'Twenty-two inhabited original eastern infills and connected village lanes',tags={q:v for q,v in p.tags.items() if q in states}),
        'before-VERIFY-ONLY.json':native_payload(registry,before,checkpoint_sha,'VERIFY ONLY — actual complete stopped fields before22 infills'),
        'supports-VERIFY-ONLY.json':native_payload(registry,supports,checkpoint_sha,'VERIFY ONLY — actual unchanged dry geological supports'),
        'retained-previous-town-VERIFY-ONLY.json':native_payload(registry,retained,checkpoint_sha,'VERIFY ONLY — unchanged exact Rose Reach/Compass junctions; never place')}
    solids={q:v for q,v in states.items() if base(v) not in AIR};parts=list(sorted(solids.items()))
    for n,start in enumerate(range(0,len(parts),15000),1):
        d=native_payload(registry,dict(parts[start:start+15000]),checkpoint_sha,'NORMAL SHAPES ONLY — actual22 infill joins batch'+str(n));d.update(construction_forbidden=True,verification_only=True)
        docs['normal-joins-'+str(n)+'-SETTLE-ONLY.json']=d
    raw={n:encode(v) for n,v in docs.items()}
    manifest={'format':'awft-north-bank-eastern22:1','checkpoint_id':checkpoint_id,'checkpoint_sha256':checkpoint_sha,'source_sha256':digest(Path(__file__)),
        'fine_land_sha256':digest(fine_path),'prior_sources':provenance,'buildings':p.lots,'rooms':p.rooms,'fixtures':p.fixtures,'supports':p.supports,'cameras':p.cameras,
        'source_body_routes':[list(q) for q in sorted(set(p.walk))],'checks':proof,'targets':len(states),'retained_previous_source_positions':len(retained),'new_entities':0,'old_BE_or_inventory_replays':0,
        'gate':'Fresh native before/support/retained verification, place new prototype ONCE, bounded normal joins, strict full expected verification and actual floor-level day/night shader/walking review; never use source tests as art acceptance',
        'native_actions':0,'saved_sources':sources,'reserve_guard':reserve,'files':{n:{'bytes':len(v),'sha256':hashlib.sha256(v).hexdigest()} for n,v in raw.items()}}
    raw['manifest.json']=encode(manifest)
    if sum(map(len,raw.values()))>64*MIB:raise UserError('Split finite22-infill output rather than exceeding allocation')
    out=home/'staging'/('north-bank-eastern22-'+str(time.time_ns()));out.mkdir()
    for n,v in raw.items():(out/n).open('xb').write(v)
    return {'folder':str(out),'manifest_sha256':digest(out/'manifest.json'),'targets':len(states),'buildings':len(p.lots),'rooms':len(p.rooms),'furnishings':len(p.fixtures),'checks':proof,'files':manifest['files'],'native_actions':0}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--home',type=Path,required=True);parser.add_argument('--fine',type=Path,required=True)
    parser.add_argument('--checkpoint-id',required=True);parser.add_argument('--checkpoint-sha',required=True);args=parser.parse_args()
    print(json.dumps(prepare(args.home,args.fine,args.checkpoint_id,args.checkpoint_sha),indent=2))
