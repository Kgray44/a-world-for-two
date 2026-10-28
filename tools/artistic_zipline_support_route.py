"""Dry modest support-route study; no chain, native call, clearing or world edit."""
from pathlib import Path
import argparse,hashlib,heapq,json,math,time
from control_room.common import UserError,digest,read_json
from tools.artistic_south_extent import ExtentTerrain
from tools.artistic_whole_bank_forest import protection
from tools.artistic_zipline_geography import station_site
from tools.playtest import guard

MIB=1024**2;BOUNDS=(1040,-1296,1408,-640);START=(1160,-760);END=(1220,-1272)
CHECKPOINT='20261027T232720Z-8d0bc0';CHECKPOINT_SHA='9bc10263e655b70468d9aad2a4b6787c7d50068f68b7292ef91e60757d627de8'
FIRST_PROOF='staging/zipline-first-catenary-20261027T2338Z/saved-air-envelope.json'
FIRST_PROOF_SHA='4d9c7d511b4d196d3eb8afe4d80e02324c0b45448e6d186623e46f9743c11105'


def first_edge_proof(home):
    path=home/FIRST_PROOF
    if path.stat().st_size>1024**2 or digest(path)!=FIRST_PROOF_SHA:raise UserError('Exact reviewed single-edge native-API/saved-air evidence required')
    row=read_json(path)
    if row.get('checkpoint_sha256')!=CHECKPOINT_SHA or row.get('source_all_swept_cells_are_air') is not True or row.get('blockers')!=[] or row.get('unique_saved_cells')!=301 or row.get('hang_offset')!=3.0 or row.get('player_width')!=.6 or row.get('player_height')!=1.8 or row.get('safety_margin')!=.25 or row.get('native_player_collision_or_ride_acceptance') is not False:raise UserError('Reviewed first edge proof changed scope')
    return {'source_clear_exact_native_API_saved_air_only':True,'evidence_sha256':FIRST_PROOF_SHA,'saved_swept_cells':301,'actual_native_catenary_player_and_vessel_acceptance':False,'scope':'ONLY launch0 NORTH knot(1160.5,168.5,-759.75) to NORTH knot(1168.5,159.5,-783.75); not a global clearance proxy reduction'}


def turn_ok(a,b,c):
    u=tuple(b[i]-a[i] for i in range(3));v=tuple(c[i]-b[i] for i in range(3));norm=math.sqrt(sum(x*x for x in u)*sum(x*x for x in v))
    return norm>0 and sum(u[i]*v[i] for i in range(3))/norm>math.cos(math.radians(45))


def reference_clear(terrain,a,b,refusal=None):
    """Conservative screening only; exact native catenary/AABB remains separate."""
    n=math.ceil(math.dist(a,b));minimum=math.inf;water_minimum=math.inf
    for i in range(n+1):
        t=i/max(1,n);x=a[0]+t*(b[0]-a[0]);z=a[2]+t*(b[2]-a[2]);y=a[1]+t*(b[1]-a[1])
        for dx,dz in ((0,0),(1,0),(-1,0),(0,1),(0,-1)):
            row=terrain.column(math.floor(x)+dx,math.floor(z)+dz)
            if row['kind']=='unknown':
                if refusal is not None:refusal.update(reason='unknown exact saved column',xz=[row['x'],row['z']],actual_native_curve_failure=False)
                return None
            top=row.get('visible',[row.get('surface_y')])[0]
            if top is None or y-top<6:
                if refusal is not None:refusal.update(reason='conservative straight6m screen, NOT native curve/AABB',xz=[row['x'],row['z']],straight_y=round(y,3),saved_highest_y=top,clearance=round(y-top,3) if top is not None else None,actual_native_curve_failure=False)
                return None
            minimum=min(minimum,y-top)
            if row['kind']=='water' and row['surface_y']<=63:
                # Actual surveyed maritime river is at sea surfaceY62. Highland
                # runnels atY136–140 are not a route for ocean-going vessels;
                # they retain the same player/curve screening, not a fictitious
                #24m vessel-navigation demand. No physical collision is waived.
                water_minimum=min(water_minimum,y-row['surface_y'])
                #24m navigation requirement +2m provisional sag allowance.
                if y-row['surface_y']<26:
                    if refusal is not None:refusal.update(reason='straight26m navigation screen, NOT actual vessel collision',xz=[row['x'],row['z']],straight_y=round(y,3),water_y=row['surface_y'],clearance=round(y-row['surface_y'],3),actual_native_curve_failure=False)
                    return None
    return {'straight_minimum_clearance':round(minimum,3),'straight_minimum_water_clearance':round(water_minimum,3) if math.isfinite(water_minimum) else None,'exact_native_catenary_player_and_vessel_acceptance':False}


def prepare(home,launch_index=0):
    home=Path(home).resolve()
    if not home.is_relative_to(Path(r'D:\A World for Two\staging\world-tests')):raise UserError('Owned private saved stage only')
    reserve=guard(MIB,16*MIB);registry=read_json(home/'dashboard/settlement/registry.json');protected,custody=protection(home,registry)
    if launch_index not in (0,1):raise UserError('Only two exact reviewed authored launch alternatives')
    start=(START,(1072,-856))[launch_index]
    terrain=ExtentTerrain(home,{'id':CHECKPOINT,'sha256':CHECKPOINT_SHA,'verified':True},registry)
    try:
        begun=time.monotonic();sites={}
        for x in range(BOUNDS[0],BOUNDS[2]+1,8):
            for z in range(BOUNDS[1],BOUNDS[3]+1,8):
                site=station_site(terrain,(x,z),protected,width=1,length=1)
                if site:sites[x,z]=site
                if time.monotonic()-begun>120:raise UserError('Finite120s support study expired')
        for q in (start,END):
            site=station_site(terrain,q,protected,width=3,length=5)
            if site is None:raise UserError('Exact compact endpoint is no longer admitted')
            sites[q]=site
        anchors={q:(q[0]+.5,r['proposed_floor_y']+8.5,q[1]+.25) for q,r in sites.items()}
        initial_proof=first_edge_proof(home) if launch_index==0 else None
        neighbors={q:sorted((r for r in sites if r!=q and 16<=math.dist(anchors[q],anchors[r])<=80),key=lambda r:math.dist(anchors[q],anchors[r])+math.dist(anchors[r],anchors[END]))[:40] for q in sites}
        pending=[(math.dist(anchors[start],anchors[END]),0,None,start)];cost={(None,start):0};previous={};proofs={};refusals=[];best=(math.dist(anchors[start],anchors[END]),None,start);goal=None;expanded=0
        while pending:
            _,value,prev,q=heapq.heappop(pending);key=prev,q
            if value!=cost[key]:continue
            expanded+=1
            if q==END:goal=key;break
            remaining=math.dist(anchors[q],anchors[END])
            if remaining<best[0]:best=remaining,prev,q
            if expanded>4000 or time.monotonic()-begun>120:break
            options=list(neighbors[q])
            if launch_index==0 and prev is None and q==START and (1168,-784) not in options:options.insert(0,(1168,-784))
            for other in options:
                if other not in sites:raise UserError('The exact reviewed first edge endpoint is not current dry supported geometry')
                if prev is not None and not turn_ok(anchors[prev],anchors[q],anchors[other]):continue
                edge=frozenset((q,other))
                if edge not in proofs:
                    refusal={}
                    if launch_index==0 and prev is None and q==START and other==(1168,-784):
                        if anchors[q]!=(1160.5,168.5,-759.75) or anchors[other]!=(1168.5,159.5,-783.75):raise UserError('Exact first-edge native knot positions changed')
                        proofs[edge]=initial_proof
                    else:proofs[edge]=reference_clear(terrain,anchors[q],anchors[other],refusal)
                    if refusal and len(refusals)<32:refusals.append({'from':list(anchors[q]),'to':list(anchors[other]),**refusal})
                if proofs[edge] is None:continue
                candidate=value+math.dist(anchors[q],anchors[other])+35
                nextkey=q,other
                if candidate<cost.get(nextkey,math.inf):cost[nextkey]=candidate;previous[nextkey]=key;heapq.heappush(pending,(candidate+math.dist(anchors[other],anchors[END]),candidate,q,other))
        final=goal if goal is not None else (best[1],best[2]);chain=[final[1]]
        while final in previous:final=previous[final];chain.append(final[1])
        chain.reverse();links=[]
        for a,b in zip(chain,chain[1:]):links.append({'from_xz':list(a),'to_xz':list(b),'reference_anchors':[list(anchors[a]),list(anchors[b])],'length_3d':round(math.dist(anchors[a],anchors[b]),3),'screening':proofs[frozenset((a,b))]})
        result={'format':'awft-dry-modest-zipline-support-study:1','checkpoint_id':CHECKPOINT,'checkpoint_sha256':CHECKPOINT_SHA,'bounds':list(BOUNDS),'launch_index':launch_index,'status':'SOURCE ROUTE FOUND; actual native curve/knots/access UNPROVED' if goal else 'UNRESOLVED finite conservative support graph; partial frontier is NOT a usable zipline','reaches_town':goal is not None,'candidate_open_dry_posts':len(sites),'all_qualified_dry_post_candidates':[sites[q]|{'reference_anchor':list(anchors[q])} for q in sorted(sites)],'first_screening_refusals':refusals,'expanded_direction_states':expanded,'edge_screenings':len(proofs),'best_frontier_offset_metres':round(best[0],3),'nodes':[sites[q]|{'reference_anchor':list(anchors[q])} for q in chain],'links':links,'constraints':{'max_span_3d':80,'maximum_source_anchor_above_floor':8,'turn_degrees_strictly_below':45,'screened_straight_land_clearance':6,'screened_straight_water_clearance':26,'navigation_scope':'Actual surveyed sea-level maritime river/waterY<=63; highland runnels retain normal collision/player screen','actual_native_catenary_and_player_AABB_required':True,'minimum_requested_navigation_clearance':24},'sources':terrain.snapshot.sources.copy(),'existing_architecture_and_future_R5_custody':custody,'native_actions':0,'footings_in_water':0,'trees_removed':0,'walking_access_acceptance':False,'geometry_placement_authority':False}
    finally:terrain.close()
    raw=(json.dumps(result,separators=(',',':'))+'\n').encode();meta={'format':'awft-zipline-support-study-receipt:1','source_sha256':digest(Path(__file__)),'status':result['status'],'proposal_sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),'reserve':reserve,'nodes':len(chain),'reaches_town':result['reaches_town'],'frontier_offset':result['best_frontier_offset_metres'],'source_only':True}
    m=(json.dumps(meta,indent=2)+'\n').encode()
    if len(raw)+len(m)>16*MIB:raise UserError('Finite16MiB support output exceeded')
    out=home/'staging'/('zipline-dry-support-study-'+str(time.time_ns()));out.mkdir();(out/'proposal.json').write_bytes(raw);(out/'manifest.json').write_bytes(m)
    return {'directory':str(out),'manifest_sha256':hashlib.sha256(m).hexdigest(),**{k:meta[k] for k in ('status','nodes','reaches_town','frontier_offset')}}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--home',type=Path,required=True);p.add_argument('--launch-index',type=int,choices=(0,1),default=0);a=p.parse_args();print(json.dumps(prepare(a.home,a.launch_index),indent=2))
