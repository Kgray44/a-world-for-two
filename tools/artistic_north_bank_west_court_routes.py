"""Exact dry two-wide connecting lanes, excluding every prior house/BE.

Prior future geometry is an explicit dependency for separate native retained
verification, never represented as observed MCA AIR or a current-world pass.
"""
from __future__ import annotations
import argparse,hashlib,json,time
from collections import deque
from pathlib import Path
from control_room.common import UserError,digest,read_json
from tools.artistic_north_bank_east import NorthTerrain,AIR,GROUND,SOFT,NORTH_SOFT,MIB,base,native_payload
from tools.artistic_bridge_refinement import flatten
from tools.artistic_north_bank_west import ZIPLINE_MASK,ZIPLINE_MASK_SHA
from tools.artistic_north_bank_residual import WEST
from tools.artistic_materials import require_outdoor_rule
from tools.playtest import guard

TEN='staging/additional-court-route-inputs-1793160629865791100/west'
TEN_SHA='2e8241cde4498d794450814d017e559dbb51a460bff08e06431ee20e339b5878'
STREET='staging/west-street-stock-SNBT-fixed-20261028T0317Z/complete-after-VERIFY-ONLY.json'
STREET_SHA='34830b8b5878d9a2a28a3047a210b849b2efa2baf780592eb4ccc234c6520358'


PAVED={'chipped:small_stone_bricks','minecraft:andesite','minecraft:polished_andesite','minecraft:cobblestone','minecraft:mossy_cobblestone','minecraft:chiseled_stone_bricks','minecraft:spruce_planks','chipped:nailed_dark_oak_planks'}
WALK_FLOORS=PAVED|{'minecraft:stone_brick_stairs'}
DECK_FULL={'minecraft:spruce_planks','chipped:nailed_dark_oak_planks','chipped:detailed_dark_oak_planks','chipped:stacked_dark_oak_planks',
    'minecraft:stripped_oak_log','minecraft:stripped_dark_oak_log','minecraft:cobblestone','minecraft:stone_bricks','minecraft:andesite','minecraft:polished_andesite','minecraft:polished_basalt','minecraft:chiseled_stone_bricks'}
ADDITION='staging/west-street-stock-SNBT-fixed-20261028T0317Z/street-and-furniture-PROPOSAL.json'
ADDITION_SHA='bc2c532f77a217c1d67c2c73714d891cbd29e6f1a073f653c185bda68de5d80d'

# Literal dry approach around the saved oak at1216,-1262. This small shared
# harbor connection crosses the former author split, not a water inlet.
TIDE_DRY_CORRIDOR={(x,z) for x in range(1212,1222) for z in (-1266,-1265)}|{(x,z) for x in (1220,1221) for z in range(-1264,-1259)}


def harbor_stairs(terrain,prior,cable):
    """Two normal stair rises on saved dry ground, below the retained quay.

    Every support and three-high body is independently read; the existing
    elevated quay is adopted only by the separate exact source/MCA check.
    No water, leaf, log, authored target or block entity may be overwritten.
    """
    states={};before={};witness={}
    for x in (1220,1221):
        for z in (-1261,-1260):
            q=(x,63,z);actual=terrain.state(*q)
            if actual is None or base(actual) not in GROUND or q in terrain.entities or q in cable:
                raise UserError('Harbor stair requires exact dry natural support '+str(q))
            witness[q]=actual
        states[x,64,-1261]='minecraft:stone_brick_stairs[facing=south,half=bottom,shape=straight,waterlogged=false]'
        states[x,64,-1260]='minecraft:stone_bricks'
        states[x,65,-1260]='minecraft:stone_brick_stairs[facing=south,half=bottom,shape=straight,waterlogged=false]'
        for z,ys in ((-1261,range(65,68)),(-1260,range(66,69))):
            for y in ys:states[x,y,z]='minecraft:air'
    for q,s in states.items():
        actual=terrain.state(*q)
        if q in prior or q in cable or q in terrain.entities or actual is None or base(actual) not in AIR|SOFT|NORTH_SOFT or 'waterlogged=true' in actual:
            raise UserError('Preserve native tree/water/BE/authored stair target '+str((q,actual)))
        before[q]=actual
    return states,before,witness

def walkable_floor(value):
    return base(value) in WALK_FLOORS|DECK_FULL


def compatible_surfaces(left,right):
    """No two-wide path cell or adjacent step may hide a two-block cliff."""
    return len(left)==len(right)==4 and all(abs(a-b)<=1 for a,b in zip(left,right)) and all(
        abs(v[a]-v[b])<=1 for v in (left,right) for a,b in ((0,1),(0,2),(1,3),(2,3)))

def encode(d):return (json.dumps(d,separators=(',',':'),ensure_ascii=False)+'\n').encode()


def paving(a,b):
    return 'minecraft:chiseled_stone_bricks' if a%8==0 and b%8==0 else 'minecraft:polished_andesite' if a%8==0 else 'minecraft:mossy_cobblestone' if b%8==0 else 'minecraft:cobblestone'


def prepare(home,checkpoint_id,checkpoint_sha):
    home=Path(home).resolve();reserve=guard(MIB,16*MIB);receipt=read_json(home/'dashboard/settlement/backup-receipt.json')
    if home.parent!=Path('D:/A World for Two/staging/world-tests').resolve() or receipt.get('verified') is not True or receipt.get('id')!=checkpoint_id or receipt.get('sha256')!=checkpoint_sha:raise UserError('Exact owned stopped route source required')
    registry=read_json(home/'dashboard/settlement/registry.json');prior={};sources=[]
    for relative,expected in ((TEN+'/prototype.json',TEN_SHA),(STREET,STREET_SHA),WEST,('staging/north-bank-western-ten-1793158436435294000/prototype.json','e8c8b3c74175d49c0d512abfcdac0d7e84a7d39f31ee92e8ad352755f2f7e2ef'),('staging/north-bank-western-connections-r2-1793159711602697500/connections.json','b658552ec91b6cd681a3e847dfe9613f51fcf59ca584642a3b184ba7c4e2956a')):
        path=home/relative
        if digest(path)!=expected:raise UserError('Exact retained current/future source dependency changed')
        states=flatten(read_json(path));prior.update(states);sources.append({'path':relative,'sha256':expected,
            'role':'Explicit expected predecessor only; separately native verify retained actual state before this new placement'})
    if digest(home/ADDITION)!=ADDITION_SHA:raise UserError('Exact authored public paving source required')
    r2_path=home/'staging/north-bank-western-connections-r2-1793159711602697500/connections.json'
    if digest(r2_path)!='b658552ec91b6cd681a3e847dfe9613f51fcf59ca584642a3b184ba7c4e2956a':raise UserError('Exact actual authored R2 connecting paving required')
    road=flatten(read_json(home/ADDITION))|flatten(read_json(r2_path));targetcolumns=set()
    for q,s in road.items():
        x,y,z=q
        if not 61<=y<=64 or base(s) not in PAVED:continue
        if all(base(road.get((x,y+d,z),'minecraft:air')) in AIR for d in (1,2)):targetcolumns.add((x,z))
    if not targetcolumns:raise UserError('Explicit prior flat public route supports required')
    cable_path=home/ZIPLINE_MASK
    if digest(cable_path)!=ZIPLINE_MASK_SHA:raise UserError('Exact prospective cable construction body required')
    cable=set(flatten(read_json(cable_path)));lots=read_json(home/TEN/'manifest.json')['lots'];terrain=NorthTerrain(home,receipt,registry)
    # The easternmost western court joins the actual existing harbor deck,
    # not an artificial walk across the inlet. Only authored deck cells whose
    # identities still match the immutable MCA and whose literal two-high body
    # is AIR are admitted. This is observed saved data, distinct from future
    # house/street dependencies above.
    harbor_relative='staging/artistic-harbor-651ac8f3e0f20997/prototype.json'
    harbor_sha='c7b8aae43f63369cd574bbe889556c9823fd27254cfec85b6c06d1a8a8347ca1'
    try:
        if digest(home/harbor_relative)!=harbor_sha:raise UserError('Exact accepted harbor source required')
        observed_deck={}
        for (x,y,z),value in flatten(read_json(home/harbor_relative)).items():
            if not 61<=y<=65 or base(value) not in DECK_FULL:continue
            q=x,y,z
            if terrain.state(*q)!=value or q in terrain.entities:continue
            head={(x,y+d,z):terrain.state(x,y+d,z) for d in (1,2)}
            if any(s is None or base(s) not in AIR or p in terrain.entities for p,s in head.items()):continue
            observed_deck[q]=value;observed_deck.update(head);targetcolumns.add((x,z))
        prior.update(observed_deck)
        sources.append({'path':harbor_relative,'sha256':harbor_sha,'role':'Only authored deck floors + actual complete0d7 AIR bodies read from authenticated MCA; no old harbor source replay','observed_saved_deck_positions':len(observed_deck)})
    except Exception:
        terrain.close();raise
    # Stair roots/body are fresh exact natural preimages, not predecessor
    # expectations. The existing65-high harbor road remains retained.
    try:stair_delta,stair_before,stair_supports=harbor_stairs(terrain,prior,cable)
    except Exception:
        terrain.close();raise
    prior_floors={}
    for (x,y,z),value in prior.items():
        if 61<=y<=65 and walkable_floor(value):prior_floors[x,z]=max(y,prior_floors.get((x,z),y))
    for (x,y,z),value in stair_delta.items():
        if walkable_floor(value):prior_floors[x,z]=max(y,prior_floors.get((x,z),y))
    known={};available_cache={};surface_levels={};delta=dict(stair_delta);retained={};paths=[];original=dict(stair_before)
    def current(q):
        if q not in known:known[q]=terrain.state(*q)
        return known[q]
    def expected(q):return stair_delta[q] if q in stair_delta else prior[q] if q in prior else current(q)
    def available(x,z):
        if (x,z) in available_cache:return available_cache[x,z]
        good=True;levels=[]
        for dx,dz in ((0,0),(1,0),(0,1),(1,1)):
            a,b=x+dx,z+dz
            if not 984<=a<=1224 or not -1320<=b<=-1180:good=False;break
            row=terrain.column(a,b);y=row.get('surface_y',0)
            # Planned source can cover the soil while the immutable snapshot
            # still contains gravel. That is conditional predecessor evidence.
            floor=prior_floors.get((a,b))
            if floor is not None:y=floor
            # The former author split is not a wall across the shared harbor.
            # Beyond1216 only unchanged observed deck or this literal measured
            # shore approach may be used. It does not expand the western lots.
            if a>1216 and (a,b) not in TIDE_DRY_CORRIDOR and any((a,y+d,b) not in observed_deck for d in (0,1,2)):good=False;break
            if row['kind'] not in ('dry','retained_object') or not 61<=y<=65 or base(expected((a,y,b)) or 'unknown') in AIR:good=False;break
            if row['kind']=='retained_object' and floor is None:good=False;break
            levels.append(y)
            for dy in (1,2):
                q=a,y+dy,b;s=expected(q)
                if q in cable or q in terrain.entities or s is None or base(s) not in AIR|SOFT|NORTH_SOFT or 'waterlogged=true' in s:good=False;break
            if not good:break
        available_cache[x,z]=good
        if good:surface_levels[x,z]=tuple(levels)
        return good
    try:
        for lot in lots:
            x,feet,z=lot['exterior_threshold_feet'];start=(x,z);targets=sorted(targetcolumns,key=lambda p:abs(p[0]-x)+abs(p[1]-z))[:96]
            if not available(*start):raise UserError('Actual external threshold lacks a complete two-wide approach for '+lot['id'])
            todo=deque([start]);previous={start:None};targetset=set(targets);end=None
            while todo:
                p=todo.popleft()
                if p in targetset and p!=start:end=p;break
                if len(previous)>20000:break
                for dx,dz in sorted(((1,0),(-1,0),(0,1),(0,-1)),key=lambda d:min(abs(p[0]+d[0]-t[0])+abs(p[1]+d[1]-t[1]) for t in targets[:8])):
                    q=p[0]+dx,p[1]+dz
                    if q in previous or abs(q[0]-x)>90 or abs(q[1]-z)>70 or not available(*q):continue
                    if not compatible_surfaces(surface_levels[p],surface_levels[q]):continue
                    previous[q]=p;todo.append(q)
            if end is None:raise UserError('No complete dry two-wide route to the existing quay for '+lot['id'])
            path=[]
            while end is not None:path.append(end);end=previous[end]
            path.reverse();paths.append({'building':lot['id'],'centres_xz':[list(p) for p in path],'floor_levels_by_centre':[list(surface_levels[p]) for p in path],'width':2,'native_walk_status':'PENDING actual before/predecessor/walking'})
            for x,z in path:
                for dx,dz in ((0,0),(1,0),(0,1),(1,1)):
                    a,b=x+dx,z+dz;row=terrain.column(a,b);y=prior_floors.get((a,b),row['surface_y'])
                    for dy in (0,1,2):
                        q=a,y+dy,b
                        if q in stair_delta:continue
                        if q in prior:
                            retained[q]=prior[q];continue
                        actual=current(q)
                        if actual is None or q in terrain.entities or q in cable or base(actual) not in AIR|GROUND|SOFT|NORTH_SOFT or 'waterlogged=true' in actual:raise UserError('Preserve an actual tree/water/BE/foreign route target '+str((q,actual)))
                        original[q]=actual
                        delta[q]='minecraft:air' if dy else paving(a,b)
            terrain.check()
        saved=terrain.snapshot.sources
    finally:terrain.close()
    if not delta:raise UserError('A real new route must have new exact target cells')
    require_outdoor_rule(delta,'New connected western two-wide alleys and designed drainage joints')
    require_outdoor_rule(prior|delta,'Complete preserved western houses/street plus connected new alleys')
    docs={'connections.json':native_payload(registry,delta,checkpoint_sha,'New exact dry western connecting lanes only; no source replay'),
        'before-VERIFY-ONLY.json':native_payload(registry,original,checkpoint_sha,'VERIFY ONLY: actual unchanged saved natural route targets'),
        'retained-predecessors-VERIFY-ONLY.json':native_payload(registry,retained,checkpoint_sha,'VERIFY ONLY: required actual old shops/street/new houses; expected NOT observed by this producer'),
        'connected-after-VERIFY-ONLY.json':native_payload(registry,retained|delta,checkpoint_sha,'VERIFY ONLY — exact connected future route and unchanged prior source'),
        'harbor-stair-supports-VERIFY-ONLY.json':native_payload(registry,stair_supports,checkpoint_sha,'VERIFY ONLY — unchanged saved dry ground beneath the two-rise harbor approach')}
    raw={n:encode(v) for n,v in docs.items()};manifest={'format':'awft-west-extra-court-connections:1','checkpoint_id':checkpoint_id,'checkpoint_sha256':checkpoint_sha,
        'source_sha256':digest(Path(__file__)),'paths':paths,'new_targets':len(delta),'required_predecessor_targets':len(retained),'prior_sources':sources,
        'explicit_limit':'Future geometry is not observed MCA AIR. Native retained/predecessor verification must pass AFTER those sources are physically placed. This source does not establish that event.',
        'harbor_approach':{'dry_corridor_columns':sorted(map(list,TIDE_DRY_CORRIDOR)),'new_stair_rises':2,'water_or_tree_targets':0,'native_walk_status':'PENDING actual native stair joins and owner traversal'},
        'native_actions':0,'world_writes':0,'native_or_visual_acceptance':False,'saved_sources':saved,'reserve_guard':reserve,
        'files':{n:{'bytes':len(v),'sha256':hashlib.sha256(v).hexdigest()} for n,v in raw.items()}}
    raw['manifest.json']=encode(manifest)
    if sum(map(len,raw.values()))>16*MIB:raise UserError('Finite original lane output exceeded')
    out=home/'staging'/('north-bank-west-extra-court-routes-'+str(time.time_ns()));out.mkdir()
    for n,v in raw.items():(out/n).open('xb').write(v)
    return {'folder':str(out),'manifest_sha256':digest(out/'manifest.json'),'paths':len(paths),'targets':len(delta),'files':manifest['files'],'native_actions':0}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--home',type=Path,required=True);p.add_argument('--checkpoint-id',required=True);p.add_argument('--checkpoint-sha',required=True);a=p.parse_args()
    print(json.dumps(prepare(a.home,a.checkpoint_id,a.checkpoint_sha),indent=2))
