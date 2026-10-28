"""Original rooted woodland stair/raised-walk prototype; saved source only."""
from pathlib import Path
from collections import OrderedDict
import argparse,hashlib,heapq,json,math,time
from control_room.common import UserError,digest,read_json
from tools.artistic_south_extent import ExtentTerrain
from tools.artistic_whole_bank_forest import protection
from tools.artistic_south_forest import AIR,SOFT
from tools.artistic_spawn_plaza import state,payload
from tools.artistic_materials import require_outdoor_rule
from tools.playtest import guard

CHECKPOINT='20261027T232720Z-8d0bc0';SHA='9bc10263e655b70468d9aad2a4b6787c7d50068f68b7292ef91e60757d627de8'
BOUNDS=(1000,-1080,1192,-744);START=(1080,65,-1072);GOAL=(1160,160,-757)
SCENIC_WAYPOINTS=((1016,-1040),(1040,-984),(1104,-880))
ROCK={'minecraft:'+s for s in ('stone','andesite','granite','diorite','tuff','calcite','deepslate')}
SAFE=(AIR|SOFT)-{'minecraft:bamboo','minecraft:bamboo_sapling'}
CUT=ROCK|{'minecraft:grass_block','minecraft:dirt','minecraft:coarse_dirt','minecraft:rooted_dirt','minecraft:gravel','minecraft:clay','minecraft:moss_block'}


class CachedTerrain(ExtentTerrain):
    def __init__(self,*args):super().__init__(*args);self.extra=OrderedDict()
    def chunk(self,cx,cz):
        q=cx,cz
        if q in self.extra:self.key=q;self.blocks=self.extra.pop(q);self.extra[q]=self.blocks;return self.blocks
        value=super().chunk(cx,cz)
        if value is not None:
            self.extra[q]=value
            if len(self.extra)>32:self.extra.popitem(last=False)
        return value


def stair_search(t,protected,start=START,goal=GOAL,max_nodes=35_000,prior_body=frozenset(),prior_floors=frozenset()):
    known={};begun=time.monotonic()
    def admit(q):
        if q in known:return known[q]
        x,y,z=q
        if (x,z) in protected or not BOUNDS[0]<=x<=BOUNDS[2] or not BOUNDS[1]<=z<=BOUNDS[3] or not 64<=y<=192:known[q]=None;return None
        row=t.column(x,z)
        retained_path=row.get('state','').split('[',1)[0]=='minecraft:dirt_path'
        if not (row['kind']=='dry' or retained_path) or y<row['surface_y']-1 or retained_path and y!=row['surface_y']+1:known[q]=None;return None
        body=[t.state(x,y+d,z) for d in (0,1,2)]
        cuts=[]
        for d,v in enumerate(body):
            if v is not None and v.split('[',1)[0] in SAFE and 'waterlogged=true' not in v:continue
            if v is not None and v.split('[',1)[0] in CUT and y+d<=row['surface_y'] and row['surface_y']-y<=1 and (x,y+d,z) not in t.entities:cuts.append((x,y+d,z));continue
            known[q]=None;return None
        gap=y-row['surface_y']-1;support=None
        if gap<0:
            anchor=(x,y-2,z);v=t.state(*anchor)
            if v is not None and v.split('[',1)[0] in CUT and anchor not in t.entities:support={'kind':'shallow_fitted_ground_steps','ground':list(anchor),'cells':[]}
        elif gap<=6:
            cells=[(x,yy,z) for yy in range(row['surface_y']+1,y)]
            if any(t.state(*p).split('[',1)[0] not in SAFE or p in t.entities for p in cells):known[q]=None;return None
            support={'kind':'native_ground' if gap==0 else 'short_grounded_pier','ground':[x,row['surface_y'],z],'cells':cells}
        else:
            for dx,dz in ((1,0),(-1,0),(0,1),(0,-1)):
                anchor=x+dx,y-2,z+dz
                if (anchor[0],anchor[2]) in protected:continue
                value=t.state(*anchor)
                if value is not None and value.split('[',1)[0] in ROCK and anchor not in t.entities and t.state(x,y-2,z).split('[',1)[0] in SAFE:
                    support={'kind':'short_rock_face_corbel','native_rock_anchor':list(anchor),'anchor_state':value,'cells':[(x,y-2,z)]};break
        if support is None:known[q]=None;return None
        prospective_solids={(x,y-1,z),*(tuple(p) for p in support['cells'])}
        if prospective_solids&prior_body or {(x,y+d,z) for d in (0,1,2)}&prior_floors:known[q]=None;return None
        known[q]={'node':list(q),'native_ground_y':row['surface_y'],'native_body':body,'support':support,'retained_existing_dirt_path_unchanged':retained_path,'bounded_natural_step_cuts':[list(p) for p in cuts]};return known[q]
    if admit(start) is None or admit(goal) is None:return None,{'status':'UNRESOLVED exact endpoint/support obstruction','expanded':0}
    def h(q):return abs(q[0]-goal[0])+abs(q[2]-goal[2])+abs(q[1]-goal[1])*.6
    pending=[(h(start),0,start)];best={start:0};prior={};expanded=0;closest=(h(start),start)
    while pending:
        _,g,q=heapq.heappop(pending)
        if g!=best[q]:continue
        expanded+=1
        if q==goal:
            nodes=[q]
            while q!=start:q=prior[q];nodes.append(q)
            nodes.reverse();return [admit(q) for q in nodes],{'status':'SOURCE stair/raised-walk route found; no native collision/walking/art acceptance','expanded':expanded}
        if h(q)<closest[0]:closest=h(q),q
        if expanded>max_nodes or time.monotonic()-begun>120:break
        for dx,dz in ((1,0),(-1,0),(0,1),(0,-1)):
            for dy in (0,1,-1):
                other=q[0]+dx,q[1]+dy,q[2]+dz;proof=admit(other)
                if proof is None:continue
                # Reject a tight vertical return through the existing part of
                # this very route. State-space height alone is not clearance.
                ancestor=q;crosses=False
                proposed_solids={(other[0],other[1]-1,other[2]),*(tuple(p) for p in proof['support']['cells'])}
                proposed_body={(other[0],other[1]+d,other[2]) for d in (0,1,2)}
                for _ in range(16):
                    if proposed_solids&{(ancestor[0],ancestor[1]+d,ancestor[2]) for d in (0,1,2)} or (ancestor[0],ancestor[1]-1,ancestor[2]) in proposed_body:crosses=True;break
                    if ancestor not in prior:break
                    ancestor=prior[ancestor]
                if crosses:continue
                cost=g+1+abs(dy)*.7+(0 if proof['support']['kind']=='native_ground' else .8 if proof['support']['kind']=='short_grounded_pier' else 1.2)+len(proof['bounded_natural_step_cuts'])*2
                if cost<best.get(other,math.inf):best[other]=cost;prior[other]=q;heapq.heappush(pending,(cost+h(other),cost,other))
    return None,{'status':'UNRESOLVED finite authored-access search; no floating or terrain-cut fallback','expanded':expanded,'closest_node':list(closest[1]),'remaining_metric':closest[0]}


def prepare(home):
    home=Path(home).resolve()
    if not home.is_relative_to(Path(r'D:\A World for Two\staging\world-tests')):raise UserError('Owned private stopped staging only')
    reserve=guard(1024**2,16*1024**2);registry=read_json(home/'dashboard/settlement/registry.json');protected,custody=protection(home,registry)
    terrain=CachedTerrain(home,{'id':CHECKPOINT,'sha256':SHA,'verified':True},registry)
    blocks={};previous={};supports={};body=set();failure=None;rail_count=lights=0;unrailed=[]
    try:
        # START is the actual natural standing surface, not an assumed65m slab.
        row=terrain.column(START[0],START[2]);start=(START[0],row['surface_y']+1,START[2])
        # Deliberately traverse the measured western toe and ridge, rather than
        # letting a direct goal heuristic repeatedly explore the east valley.
        targets=[]
        for x,z in SCENIC_WAYPOINTS:
            row=terrain.column(x,z)
            if row['kind']!='dry':raise UserError('A measured scenic waypoint is no longer known dry land')
            targets.append((x,row['surface_y']+1,z))
        targets.append(GOAL);nodes=[];legs=[];current=start;prior_body=set();prior_floors=set()
        for target in targets:
            segment,report=stair_search(terrain,protected,current,target,prior_body=prior_body,prior_floors=prior_floors);legs.append(report|{'from':list(current),'to':list(target)})
            if segment is None:nodes=None;break
            nodes.extend(segment if not nodes else segment[1:]);current=target
            for r in segment:
                x,y,z=r['node'];prior_body.update((x,y+d,z) for d in (0,1,2));prior_floors.add((x,y-1,z))
        search={'status':'SOURCE scenic staged route found; native walking/art pending' if nodes else 'UNRESOLVED staged scenic design; no partial placement authority','legs':legs}
        allowed_cuts={tuple(p) for r in (nodes or []) for p in r.get('bounded_natural_step_cuts',[])}
        if len(allowed_cuts)>128:raise UserError('Local natural step cuts exceed128cells; redesign, no broad cliff flattening')
        def put(p,value):
            p=tuple(p)
            if p in blocks and blocks[p]!=value:raise UserError('Authored stairs overlap their own floor/body/support: '+str(p))
            actual=terrain.state(*p)
            if actual is None or p in terrain.entities or not (actual.split('[',1)[0] in SAFE or p in allowed_cuts and actual.split('[',1)[0] in CUT):raise UserError('Preserve existing cliff/tree/object/inventory: '+str(p))
            blocks[p]=value;previous[p]=actual
        if nodes:
            for p in sorted(allowed_cuts):put(p,'minecraft:air')
            for i,r in enumerate(nodes):
                x,y,z=r['node'];q=(x,y,z);nextq=nodes[min(i+1,len(nodes)-1)]['node'];prevq=nodes[max(0,i-1)]['node']
                dx,dz=nextq[0]-x,nextq[2]-z;need_stair=prevq[1]<y or nextq[1]<y
                if prevq[1]<y:dx,dz=x-prevq[0],z-prevq[2]
                elif nextq[1]<y:dx,dz=x-nextq[0],z-nextq[2]
                direction='east' if dx>0 else 'west' if dx<0 else 'south' if dz>0 else 'north'
                if r.get('retained_existing_dirt_path_unchanged'):need_stair=False
                if need_stair and y<=r['native_ground_y']+1:allowed_cuts.add((x,y-1,z))
                if y>r['native_ground_y']+1 or need_stair:
                    value=state(registry,'minecraft:spruce_stairs',facing=direction,half='bottom',shape='straight',waterlogged=False) if need_stair else state(registry,'minecraft:stripped_spruce_log',axis='z' if dx else 'x') if i%6==0 else 'minecraft:spruce_planks'
                    put((x,y-1,z),value)
                    for p in r['support']['cells']:
                        if tuple(p)==(x,y-1,z):continue
                        put(p,state(registry,'minecraft:stripped_oak_log',axis='x' if r['support']['kind']=='short_rock_face_corbel' else 'y') if p[1]%7 else 'minecraft:dark_oak_planks')
                for dy in (0,1,2):body.add((x,y+dy,z))
                if 'native_rock_anchor' in r['support']:supports[tuple(r['support']['native_rock_anchor'])]=r['support']['anchor_state']
                else:
                    p=tuple(r['support']['ground']);supports[p]=terrain.state(*p)
            if any(p in blocks and blocks[p]!='minecraft:air' for p in body):raise UserError('A proposed floor/support intersects planned actor headroom')
            for p in sorted(body):
                if p not in blocks:put(p,'minecraft:air')
            supports={p:v for p,v in supports.items() if p not in blocks}
            if len(allowed_cuts)>128:raise UserError('Natural step/tread adaptations exceed128cells; redesign, no broad flattening')
            # Guard only exposed sides. These short transverse knees, regularly
            # spaced masonry joints and low warm lamps are structural roles,
            # not a recolored boardwalk or a wide flattened forest platform.
            for i,r in enumerate(nodes):
                x,y,z=r['node'];ahead=nodes[min(i+1,len(nodes)-1)]['node'];behind=nodes[max(0,i-1)]['node'];dx,dz=ahead[0]-behind[0],ahead[2]-behind[2]
                sides=((0,1),(0,-1)) if abs(dx)>=abs(dz) else ((1,0),(-1,0))
                for sx,sz in sides:
                    q=x+sx,z+sz;side=terrain.column(*q);floor=(q[0],y-1,q[1]);rail=(q[0],y,q[1]);lamp=(q[0],y+1,q[1])
                    if side['kind']=='unknown':unrailed.append({'pos':list(rail),'reason':'unknown side; no imagined support'});continue
                    if side.get('surface_y',y)>=y-2:continue
                    if rail in body or floor in body:continue # adjacent route, not an open drop
                    actual=terrain.state(*rail)
                    if rail in blocks and blocks[rail]!='minecraft:air':continue
                    if actual is None or actual.split('[',1)[0] not in SAFE or rail in terrain.entities:
                        if actual is not None and (actual.split('[',1)[0] in ROCK or actual.split('[',1)[0].endswith('_log')):continue
                        unrailed.append({'pos':list(rail),'reason':'retained side obstruction; native safety/art review required'});continue
                    under=terrain.state(*floor)
                    if floor not in blocks:
                        if under is not None and under.split('[',1)[0] in SAFE:put(floor,state(registry,'minecraft:stripped_spruce_log',axis='x' if sx else 'z'))
                        elif under is not None and under.split('[',1)[0] in CUT:supports[floor]=under
                        else:unrailed.append({'pos':list(rail),'reason':'no admitted rail footing'});continue
                    # A planned AIR cell on an adjacent route is never filled.
                    if blocks.get(floor)=='minecraft:air':unrailed.append({'pos':list(rail),'reason':'retained adjacent route AIR'});continue
                    if blocks.get(rail)=='minecraft:air':blocks.pop(rail);previous.pop(rail)
                    masonry=i%7==0
                    value=state(registry,'minecraft:stone_brick_wall',east='none',north='none',south='none',west='none',up=True,waterlogged=False) if masonry else state(registry,'minecraft:spruce_fence',east=False,north=False,south=False,west=False,waterlogged=False)
                    put(rail,value);rail_count+=1
                    if masonry and lamp not in body and lamp not in blocks and terrain.state(*lamp).split('[',1)[0] in SAFE and lamp not in terrain.entities:
                        put(lamp,state(registry,'minecraft:lantern',hanging=False,waterlogged=False));lights+=1
            require_outdoor_rule(blocks,'Rooted woodland cliff-access prototype')
        sources=terrain.snapshot.sources.copy()
    except UserError as e:
        if not 'nodes' in locals() or nodes is None:raise
        failure=str(e);blocks.clear();previous.clear();search['status']='UNRESOLVED authored geometry preflight; no partial placement proposal';search['preflight_failure']=failure
    finally:
        sources=terrain.snapshot.sources.copy()
        terrain.close()
    docs={}
    if blocks:
        docs['access-DELTA.json']=payload(registry,SHA,blocks,'Rooted scenic cliff-access prototype')
        docs['actual-BEFORE-VERIFY-ONLY.json']=payload(registry,SHA,previous,'Actual saved cliff access target preimage',before=True)
        docs['native-supports-VERIFY-ONLY.json']=payload(registry,SHA,supports,'Unchanged actual ground/rock anchors, NEVER PLACE',before=True)
        begin=next(i for i,r in enumerate(nodes) if r['node']==[1016,83,-1040]);sample=nodes[begin:begin+33]
        columns={(r['node'][0]+dx,r['node'][2]+dz) for r in sample for dx in (-1,0,1) for dz in (-1,0,1)}
        low=min(r['node'][1] for r in sample)-8;high=max(r['node'][1] for r in sample)+3
        selected={p:v for p,v in blocks.items() if (p[0],p[2]) in columns and low<=p[1]<=high}
        docs['VISUAL-PROTOTYPE-DELTA.json']=payload(registry,SHA,selected,'FIRST visual gate ONLY: rooted32m western switchback/rails/lamps')
        docs['VISUAL-PROTOTYPE-BEFORE.json']=payload(registry,SHA,{p:previous[p] for p in selected},'Exact saved visual-prefix preimage',before=True)
        docs['VISUAL-PROTOTYPE-SUPPORTS.json']=payload(registry,SHA,{p:v for p,v in supports.items() if (p[0],p[2]) in columns and low-1<=p[1]<=high},'Unchanged prototype rock/ground supports, NEVER PLACE',before=True)
    detail={'format':'awft-authored-cliff-access-study:1','checkpoint_id':CHECKPOINT,'checkpoint_sha256':SHA,'source_sha256':digest(Path(__file__)),'search':search,'start':list(start),'goal':list(GOAL),'route':nodes or [],'positions':len(blocks),'rooted_supports':len(supports),'guardrails':rail_count,'warm_low_lamps':lights,'retained_or_unknown_side_review':unrailed,'ordinary_body_excavation_cells':len({tuple(p) for r in (nodes or []) for p in r.get('bounded_natural_step_cuts',[])}),'retained_existing_dirt_path_cells':sum(r.get('retained_existing_dirt_path_unchanged',False) for r in (nodes or [])),'trees_removed':0,'first_native_visual_gate':'Use only VISUAL-PROTOTYPE plans, capture actual rail/stair/rock-joint views and revise before full access propagation','cameras':[{'name':'western-toe-stair-side','feet':[1009.5,96,-1045.5],'look_at':[1017,93,-1036]},{'name':'western-toe-ascending','feet':[1016.5,86,-1042.5],'look_at':[1019,97,-1031]},{'name':'upper-stair-join','feet':[1027.5,111,-1024.5],'look_at':[1020,102,-1027]}],'sources':sources,'exclusions':custody,'native_actions':0,'walking_or_art_acceptance':False,'source_only':True}
    raw={n:(json.dumps(d,separators=(',',':'))+'\n').encode() for n,d in docs.items()};raw['study.json']=(json.dumps(detail,separators=(',',':'))+'\n').encode()
    meta={'format':'awft-cliff-access-study-receipt:1','source_sha256':digest(Path(__file__)),'search':search,'positions':len(blocks),'reserve':reserve,'files':{n:{'sha256':hashlib.sha256(v).hexdigest(),'bytes':len(v)} for n,v in raw.items()},'native_actions':0}
    raw['manifest.json']=(json.dumps(meta,indent=2)+'\n').encode()
    if sum(map(len,raw.values()))>16*1024**2:raise UserError('Finite16MiB source access exceeded')
    out=home/'staging'/('authored-cliff-access-'+str(time.time_ns()));out.mkdir()
    for n,v in raw.items():(out/n).write_bytes(v)
    return {'directory':str(out),'manifest_sha256':digest(out/'manifest.json'),'positions':len(blocks),'search':search}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--home',type=Path,required=True);print(json.dumps(prepare(p.parse_args().home),indent=2))
