"""Measure a genuine closed natural walking loop without paving or clearing.

The original four walking branches are retained. This joins two nearby west
ends over literal saved dry terrain; failure stays unresolved without fallback.
"""
from __future__ import annotations
import argparse
import hashlib
import heapq
import json
from pathlib import Path

from control_room.common import UserError,digest,read_json,utcnow
from tools.artistic_bridge_refinement import encoded
from tools.artistic_first_life_requests48 import CHECKPOINT,CHECKPOINT_SHA,checkpoint
from tools.artistic_forest_understory import settlement_plan
from tools.artistic_south_extent import ExtentTerrain
from tools.artistic_south_forest import AIR,SOFT,buffered_columns
from tools.artistic_zipline_catenary import reader_budget
from tools.playtest import guard
from tools.settlement_attractions import base

NODES=((1072,-1072),(1064,-1072),(1064,-1080),(1056,-1080),(1048,-1080),
       (1048,-1072),(1048,-1064),(1056,-1064),(1064,-1064),(1072,-1064),(1072,-1072))
NEW_LINK=((1048,-1072),(1048,-1064),(1056,-1064))
V2='staging/zipline-west-v2-source-1793152099836099800/all-v2-RESERVATION-ONLY.json'
V2_SHA='92ea594836795a61e00f5cc32290d49d1d47b9fd6eb55aeefc99d527acf8854d'


def line(a,b):
    if len(a)!=2 or len(b)!=2 or any(type(v)is not int for v in (*a,*b)):
        raise UserError('Literal two-dimensional route vertices required')
    if (a[0]==b[0])==(a[1]==b[1]):raise UserError('Distinct orthogonal route segment required')
    length=abs(a[0]-b[0])+abs(a[1]-b[1])
    if length>32:raise UserError('Bounded short measured route segment required')
    dx=(b[0]>a[0])-(b[0]<a[0]);dz=(b[1]>a[1])-(b[1]<a[1])
    return [(a[0]+n*dx,a[1]+n*dz)for n in range(length+1)]


def measure(terrain,nodes,keepout):
    if len(nodes)<5 or nodes[0]!=nodes[-1] or len(set(nodes[:-1]))!=len(nodes)-1:
        raise UserError('A simple explicitly closed loop is required; a branch is not a loop')
    return measure_edges(terrain,nodes,keepout)


def measure_edges(terrain,nodes,keepout):
    field={};center=[];length=0;supports=[]
    for a,b in zip(nodes,nodes[1:]):
        points=line(a,b);across=(0,1)if a[0]!=b[0]else(1,0);last=None
        length+=len(points)-1
        for x,z in points:
            heights=[]
            for side in (-1,0,1):
                xx,zz=x+across[0]*side,z+across[1]*side;column=terrain.column(xx,zz)
                if column.get('kind')!='dry':raise UserError('Retain non-dry/unknown/occupied actual loop support')
                g=column['surface_y'];heights.append(g);support=(xx,g,zz)
                states={support:column['state']}
                for dy in (1,2,3):
                    p=(xx,g+dy,zz);value=terrain.state(*p)
                    if value is None or base(value)not in AIR|SOFT:raise UserError('Retain actual loop obstruction; do not clear or assume AIR')
                    states[p]=value
                if states.keys()&terrain.entities or states.keys()&keepout:
                    raise UserError('Preserve every actual BE and exact future cable/frame/body voxel')
                field.update(states);supports.append(support)
            if max(heights)-min(heights)>1 or last is not None and abs(heights[1]-last)>1:
                raise UserError(f'Literal three-wide slope/step exceeds one block at {(x,z)}: ground={heights}, previous={last}')
            last=heights[1];center.append([x,last+1,z])
    return field,center,supports,length


def contour_link(terrain,keepout):
    """Follow actual small-scale contours; never lower the slope requirement."""
    start=(1048,-1072);goal=(1056,-1064)
    retained=set()
    for a,b in zip(NODES[:6],NODES[1:6]):retained.update(line(a,b))
    for a,b in zip(NODES[7:],NODES[8:]):retained.update(line(a,b))
    retained-={start,goal};queue=[(0,0,start,None)];best={start:0};previous={};refusals=[];expanded=0
    while queue:
        _,cost,p,heading=heapq.heappop(queue)
        if cost!=best[p]:continue
        if p==goal:
            route=[p]
            while p!=start:p=previous[p];route.append(p)
            return route[::-1],{'bounded_domain':[1045,-1075,1060,-1061],'expanded_nodes':expanded,
                'read_only_source_refusals':refusals,'original_straight_link_rejected':'Ground step71 to73 at1048,-1067; no clearing/flattening or gate relaxation'}
        expanded+=1
        if expanded>256:break
        for direction in ((1,0),(0,1),(-1,0),(0,-1)):
            other=(p[0]+direction[0],p[1]+direction[1])
            if not(1045<=other[0]<=1060 and -1075<=other[1]<=-1061)or other in retained:continue
            try:measure_edges(terrain,(p,other),keepout)
            except UserError as error:
                if len(refusals)<32:refusals.append({'edge':[p,other],'reason':str(error)})
                continue
            score=cost+1+(0.15 if heading is not None and heading!=direction else 0)
            if score<best.get(other,float('inf')):
                best[other]=score;previous[other]=p
                heuristic=abs(goal[0]-other[0])+abs(goal[1]-other[1])
                heapq.heappush(queue,(score+heuristic,score,other,direction))
    raise UserError('No finite actual three-wide contour closing link; preserve the original branch-only status')


def prepare(home,output):
    home=Path(home).resolve();output=Path(output).absolute()
    if output.exists()or output.parent!=home/'staging':raise UserError('New immediate private loop witness required')
    reserve=guard(1024**2,4*1024**2);budget=reader_budget();current=checkpoint(home)
    registry=read_json(home/'dashboard/settlement/registry.json')
    mask=home/V2
    if digest(mask)!=V2_SHA:raise UserError('Preserve exact complete western v2 flight/physical construction mask')
    keepout={tuple(r[:3])for r in read_json(mask)['blocks']}
    terrain=ExtentTerrain(home,current,registry)
    try:
        actual_link,derivation=contour_link(terrain,keepout)
        actual_nodes=(*NODES[:6],*actual_link[1:],*NODES[8:])
        field,center,supports,length=measure(terrain,actual_nodes,keepout)
        link,_,_,new_length=measure_open_link(terrain,keepout,actual_link)
        sources=terrain.snapshot.sources.copy()
    finally:terrain.close()
    docs={'closed-loop-current31-VERIFY-ONLY.json':settlement_plan(registry,current,field,'VERIFY ONLY natural closed woodland loop support and body'),
        'closing-link-current31-VERIFY-ONLY.json':settlement_plan(registry,current,link,'VERIFY ONLY two short natural closing edges, no clearing'),
        'walk-composition-REVIEW-ONLY.json':{'format':'awft-native-woodland-loop-source:1','checkpoint_sha256':CHECKPOINT_SHA,
            'loop_nodes_xz':actual_nodes,'loop_horizontal_metres':length,'natural_closing_link':actual_link,
            'contour_derivation':derivation,
            'new_closing_link_horizontal_metres':new_length,'three_wide_source_witnesses':len(set(supports)),
            'source_actor_feet_centerline':center,'closed_graph_cycle_actual_saved_support':True,
            'no_paving_clearing_terraforming_or_world_writes':True,'native_actual_walk_and_visual_acceptance':False},
        'growth-reservation-ONLY.json':{'format':'awft-woodland-walk-growth-exclusion:1','seed':registry['seed'],
            'world_path':registry['world_path'],'checkpoint_sha256':CHECKPOINT_SHA,'construction_forbidden':True,
            'whole_growth_skirt_metres':5,'reserved_columns_xz':[list(p)for p in sorted(buffered_columns({(p[0],p[2])for p in field},5))],
            'native_plan':False,'no_observed_AIR_inferred_from_columns':True}}
    raw={n:encoded(d)for n,d in docs.items()}
    manifest={'format':'awft-closed-natural-woodland-loop48:1','created':utcnow(),'source_sha256':digest(Path(__file__)),
        'checkpoint_id':CHECKPOINT,'checkpoint_sha256':CHECKPOINT_SHA,'source_metres':length,'new_closing_metres':new_length,
        'literal_support_and_body_cells':len(field),'native_actions':0,'world_writes':0,'paving_placed':0,
        'current31_sources':sources,'reserve_guard':reserve,'reader_budget':budget,
        'files':{n:{'bytes':len(d),'sha256':hashlib.sha256(d).hexdigest()}for n,d in raw.items()}}
    raw['manifest.json']=encoded(manifest)
    if sum(map(len,raw.values()))>4*1024**2:raise UserError('Finite loop witness allocation exceeded')
    output.mkdir()
    for n,d in raw.items():(output/n).write_bytes(d)
    return {'output':str(output),'manifest_sha256':digest(output/'manifest.json'),'source_loop_metres':length,'native_actions':0}


def measure_open_link(terrain,keepout,nodes=NEW_LINK):
    # Exactly the same support/body checks, without falsely labelling an open
    # connection as an independent loop or adding guessed side geometry.
    return measure_edges(terrain,nodes,keepout)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('home','output'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args()
    try:result=prepare(a.home,a.output)
    except Exception as error:
        h=Path(a.home).resolve();out=Path(a.output).absolute()
        if out.parent==h/'staging'and not out.exists():
            reserve=guard(0,65536);out.mkdir()
            (out/'failed-source-receipt.json').write_bytes(encoded({'status':'FAILED_SAVED_LOOP_SOURCE',
                'created':utcnow(),'error':str(error),'source_sha256':digest(Path(__file__)),
                'checkpoint_sha256':CHECKPOINT_SHA,'native_actions':0,'world_writes':0,'reserve_guard':reserve}))
        raise
    print(json.dumps(result,indent=2))
