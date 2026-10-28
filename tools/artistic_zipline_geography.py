"""Saved-only cliff/station/corridor proposals; not chain APIs or world writes."""
from __future__ import annotations
import argparse, hashlib, json, math, time
from pathlib import Path
from control_room.common import UserError,digest,read_json,utcnow
from tools.artistic_south_extent import ExtentTerrain
from tools.artistic_south_forest import AIR,SOFT,GROUND
from tools.artistic_south_forest import buffered_columns
from tools.artistic_whole_bank_forest import CHECKPOINT,CHECKPOINT_SHA,protection
from tools.playtest import guard
from tools.settlement_attractions import base

MIB=1024**2;MAX_OUTPUT=4*MIB


def station_site(terrain,center,protected,width=3,length=5):
    x,z=center;columns=[]
    for xx in range(x-width//2,x+width//2+1):
        for zz in range(z-length//2,z+length//2+1):
            if (xx,zz) in protected:return None
            row=terrain.column(xx,zz)
            if row['kind']!='dry' or base(row['state']) not in GROUND:return None
            columns.append(row)
    floor=max(r['surface_y'] for r in columns)+1
    if floor-min(r['surface_y'] for r in columns)>4:return None
    body=[]
    for row in columns:
        states=[terrain.state(row['x'],y,row['z']) for y in range(floor,floor+12)]
        if any(s is None or base(s) not in AIR|SOFT or 'waterlogged=true' in s or base(s) in ('minecraft:bamboo','minecraft:bamboo_sapling') for s in states):return None
        if any(p[0]==row['x'] and p[2]==row['z'] for p in terrain.entities):return None
        body.append({'support':[row['x'],row['surface_y'],row['z']],'support_state':row['state'],'floor_and_twelve_high_states':states})
    return {'center_xz':list(center),'bounds':[x-width//2,z-length//2,x+width//2,z+length//2],
            'proposed_floor_y':floor,'actual_support_y_range':[min(r['surface_y'] for r in columns),floor-1],
            'exact_saved_support_and_clearance':body,'status':'SOURCE dry compact footprint; support/fittings/native art/access UNTESTED'}


def straight_corridor(terrain,a,b,margin=3):
    count=math.ceil(math.dist((a[0],a[2]),(b[0],b[2])));rows=[];blocked=[];unknown=[]
    for n in range(count+1):
        t=n/max(1,count);p=tuple(a[i]+t*(b[i]-a[i]) for i in range(3));x,z=math.floor(p[0]),math.floor(p[2]);row=terrain.column(x,z)
        if row['kind']=='unknown':unknown.append([x,z]);continue
        visible=row.get('visible');top=visible[0] if visible else row.get('surface_y')
        if top is None:unknown.append([x,z]);continue
        clearance=p[1]-top
        rows.append({'position':[round(v,3) for v in p],'saved_highest_block_y':top,'vertical_clearance':round(clearance,3)})
        if clearance<margin:blocked.append({'xyz':[round(v,3) for v in p],'highest_block_y':top,'clearance':round(clearance,3),'kind':row['kind']})
    return {'horizontal_metres':round(math.dist((a[0],a[2]),(b[0],b[2])),3),'straight_reference_only':True,
            'count':len(rows),'minimum_vertical_clearance':min((r['vertical_clearance'] for r in rows),default=None),
            'blocked_columns':len(blocked),'first_blockers':blocked[:16],'unknown_columns':len(unknown),
            'source_clear_straight_reference':not blocked and not unknown,'provider_length_sag_player_AABB_native_acceptance':False,
            'samples':rows,'warning':'Straight reference is NOT actual chain catenary, anchor endpoints or a safe native zipline proof'}


def growth_reservation(data,launch_index,landing_index):
    """Explicit prospective X/Z-only keep-out, never a fake native AIR plan."""
    if data.get('format')!='awft-saved-zipline-geography:1' or data.get('checkpoint_sha256')!=CHECKPOINT_SHA:raise UserError('Exact saved station geography required')
    launches=data['launch_candidates_highest_qualified_footprint_first'];landings=data['town_dry_landing_candidates']
    if not 0<=launch_index<len(launches) or not 0<=landing_index<len(landings):raise UserError('Explicit bounded station selection required')
    pairs=[r for r in data['straight_reference_pairs'] if r['launch_index']==launch_index and r['landing_index']==landing_index]
    if len(pairs)!=1 or not pairs[0]['reference_corridor']['source_clear_straight_reference']:raise UserError('Do not reserve a reference already obstructed or unknown as a usable route')
    pair=pairs[0];rows=pair['reference_corridor']['samples']
    if not rows or len(rows)>4096:raise UserError('Finite complete saved reference samples required')
    station_columns=set();stations=[]
    for name,site in (('cliff_launch',launches[launch_index]),('town_landing',landings[landing_index])):
        x0,z0,x1,z1=site['bounds']
        if (x1-x0+1)*(z1-z0+1)>49:raise UserError('Compact station reservation only')
        station_columns.update((x,z) for x in range(x0,x1+1) for z in range(z0,z1+1))
        stations.append({'id':name,'bounds':site['bounds'],'floor_y_proposal':site['proposed_floor_y'],'status':site['status']})
    reference_columns={(math.floor(row['position'][0]),math.floor(row['position'][2])) for row in rows}
    corridor=buffered_columns(reference_columns,4)
    skirt=buffered_columns(corridor|station_columns,5)
    if len(skirt)>20_000:raise UserError('Finite prospective growth keep-out exceeded')
    return {'format':'awft-prospective-growth-exclusion:1','name':'FUTURE UNBUILT cliff-to-pirate-town stations/cable work corridor',
            'checkpoint_sha256':CHECKPOINT_SHA,'stations':stations,'reference_anchors':pair['reference_anchors'],
            'source_pair':[launch_index,landing_index],'reference_horizontal_metres':pair['reference_corridor']['horizontal_metres'],
            'cable_work_corridor_half_width':4,'whole_crown_extra_skirt_metres':5,
            'station_columns_xz':[list(q) for q in sorted(station_columns)],
            'cable_work_corridor_columns_xz':[list(q) for q in sorted(corridor)],
            'all_growth_excluded_columns_xz':[list(q) for q in sorted(skirt)],
            'status':'PROSPECTIVE keep-out only; provider span/sag/native knot loading, actual player clearance and cliff walking access remain UNPROVED',
            'native_plan':False,'native_actions':0,'growth_authority':False,
            'warning':'No AIR states are fabricated. Root must explicitly incorporate this X/Z mask before any full-growth plot admission; change/release needs a newly reviewed source reservation.'}


def prepare_reservation(home,proposal,expected_sha256,launch,landing):
    home=Path(home).resolve();proposal=Path(proposal).resolve()
    if not home.is_relative_to(Path(r'D:\A World for Two\staging\world-tests')) or not proposal.is_relative_to(home/'staging'):raise UserError('Owned private proposal only')
    if not 0<proposal.stat().st_size<=MAX_OUTPUT or digest(proposal)!=expected_sha256:raise UserError('Exact finite immutable station proposal required')
    reserve=guard(0,MIB);result=growth_reservation(read_json(proposal),launch,landing)
    result.update(source_sha256=digest(Path(__file__)),station_proposal_sha256=expected_sha256,reserve=reserve)
    raw=(json.dumps(result,separators=(',',':'))+'\n').encode()
    if len(raw)>MIB:raise UserError('Finite1MiB metadata-only keep-out exceeded')
    out=home/'staging'/('future-zipline-growth-reservation-'+str(time.time_ns()));out.mkdir();(out/'reservation.json').write_bytes(raw)
    return {'file':str(out/'reservation.json'),'sha256':hashlib.sha256(raw).hexdigest(),'excluded_columns':len(result['all_growth_excluded_columns_xz']),'native_actions':0}


def prepare(home,forest):
    home=Path(home).resolve();forest=Path(forest).resolve()
    if not home.is_relative_to(Path(r'D:\A World for Two\staging\world-tests')) or not forest.is_relative_to(home/'staging'):raise UserError('Owned private stopped artistic staging only')
    if forest.stat().st_size>16*MIB:raise UserError('Finite saved forest proposal required')
    reserve=guard(MIB,MAX_OUTPUT);data=read_json(forest)
    if data.get('checkpoint_sha256')!=CHECKPOINT_SHA:raise UserError('Exact latest saved geography required')
    registry=read_json(home/'dashboard/settlement/registry.json');protected,custody=protection(home,registry)
    terrain=ExtentTerrain(home,{'id':CHECKPOINT,'sha256':CHECKPOINT_SHA,'verified':True},registry)
    try:
        # A real cliff launch must leave its observed HIGH side towards the LOW
        # side. The absolute183m hill maximum is not automatically a cliff edge.
        ranked=[]
        for row in data['cliff_ground_profiles']:
            high,low=row['higher_observed_ground'],row['lower_observed_ground'];toward=(1240-high[0],-1264-high[2]);drop=(low[0]-high[0],low[2]-high[2])
            if toward[0]*drop[0]+toward[1]*drop[1]>0:ranked.append(row)
        launches=[]
        for row in sorted(ranked,key=lambda v:v['higher_observed_ground'][1],reverse=True):
            high=row['higher_observed_ground'];site=station_site(terrain,(high[0],high[2]),protected)
            if site is not None:
                site.update(observed_cliff_profile=row,walking_access='UNPROVED; no passed natural access; authored approach may be required')
                launches.append(site)
            if len(launches)==4:break
        landings=[]
        for x in range(1200,1345,4):
            for z in range(-1300,-1227,4):
                site=station_site(terrain,(x,z),protected)
                if site is not None:landings.append(site)
                if time.monotonic()-terrain.started>90:raise UserError('Finite90s station geography exceeded; no oversized retry')
        # Keep different neighborhoods instead of selecting four adjacent cells.
        selected=[]
        for site in sorted(landings,key=lambda v:(v['center_xz'][0]-1240)**2+(v['center_xz'][1]+1264)**2):
            if all(math.dist(site['center_xz'],other['center_xz'])>=12 for other in selected):selected.append(site)
            if len(selected)==4:break
        pairs=[]
        for i,launch in enumerate(launches):
            for j,landing in enumerate(selected):
                a=(launch['center_xz'][0]+.5,launch['proposed_floor_y']+8,launch['center_xz'][1]+.5)
                b=(landing['center_xz'][0]+.5,landing['proposed_floor_y']+8,landing['center_xz'][1]+.5)
                proof=straight_corridor(terrain,a,b)
                pairs.append({'launch_index':i,'landing_index':j,'reference_anchors':[list(a),list(b)],'reference_corridor':proof})
                if time.monotonic()-terrain.started>90:raise UserError('Finite90s reference corridor bound exceeded')
        result={'format':'awft-saved-zipline-geography:1','created':utcnow(),'checkpoint_id':CHECKPOINT,'checkpoint_sha256':CHECKPOINT_SHA,'forest_source_sha256':digest(forest),'launch_candidates_highest_qualified_footprint_first':launches,'town_dry_landing_candidates':selected,'all_qualified_town_footprints':len(landings),'straight_reference_pairs':pairs,'exclusion_custody':custody,'sources':terrain.snapshot.sources.copy(),'status':'PROSPECTIVE compact stations/corridors; NO proven cliff walking access or cable-provider native acceptance','native_actions':0,'growth_authority':False,'existing_trees_removed':0}
    finally:terrain.close()
    raw=(json.dumps(result,separators=(',',':'))+'\n').encode()
    meta={'format':'awft-zipline-geography-receipt:1','source_sha256':digest(Path(__file__)),'checkpoint_sha256':CHECKPOINT_SHA,'reserve':reserve,'proposal_sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),'launches':[{'xz':r['center_xz'],'floor':r['proposed_floor_y']} for r in launches],'landings':[{'xz':r['center_xz'],'floor':r['proposed_floor_y']} for r in selected],'pairs':[{'launch':r['launch_index'],'landing':r['landing_index'],'horizontal_metres':r['reference_corridor']['horizontal_metres'],'straight_reference_clear':r['reference_corridor']['source_clear_straight_reference'],'minimum_clearance':r['reference_corridor']['minimum_vertical_clearance'],'blocked':r['reference_corridor']['blocked_columns'],'unknown':r['reference_corridor']['unknown_columns']} for r in pairs],'native_actions':0}
    encoded=(json.dumps(meta,indent=2)+'\n').encode()
    if len(raw)+len(encoded)>MAX_OUTPUT:raise UserError('Finite4MiB zipline geometry proposal exceeded')
    out=home/'staging'/('zipline-saved-geography-'+str(time.time_ns()));out.mkdir();(out/'proposal.json').write_bytes(raw);(out/'manifest.json').write_bytes(encoded)
    return {'directory':str(out),'manifest_sha256':hashlib.sha256(encoded).hexdigest(),**{k:meta[k] for k in ('launches','landings','pairs')}}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--home',type=Path,required=True);p.add_argument('--forest',type=Path,required=True)
    a=p.parse_args();print(json.dumps(prepare(a.home,a.forest),indent=2))
