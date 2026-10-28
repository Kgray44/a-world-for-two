"""Finite saved bank/cliff composition; never native generation, growth or LIFE.

Reads six exact MCA members from the reviewed stopped checkpoint and checks the
five real survey receipts. Sparse cells never become whole-crown admission.
"""
from __future__ import annotations
import argparse
from collections import Counter, deque
import hashlib, heapq, json, math, time
from pathlib import Path
from control_room.common import UserError, digest, read_json, utcnow
from tools.artistic_south_extent import ExtentTerrain, MAX_RAW, REGIONS
from tools.artistic_south_forest import exclusions, buffered_columns
from tools.artistic_south_forest import AIR, SOFT
from tools.artistic_forest_walks import body_witness, component, route
from tools.playtest import guard
from tools.settlement_attractions import base

MIB=1024**2
CHECKPOINT='20261027T210743Z-2ef8a3'
CHECKPOINT_SHA='b8495b677653c31077036faad10f553b432dcb173cd8964c8bb48e4674bd35f7'
SURVEYS='staging/native-south-whole-bank-survey42-1793135121241939500'
SURVEYS_SHA='f42f1f6c9a513374b5a0abc195e46c2eb74cca8cfd2c1d9a3d62ba26478f26b1'
INDEX='staging/south-contour-walks-metadata-r2-1793133317004398500/exclusions-final-r2.json'
INDEX_SHA='4aae243035f6d9887ce145a974b8de6cbbee8b909ec4306091042fe62c9c32d9'
FUTURE_R5='staging/artistic-fountain-centerpiece-r5-wet-reset-20261027T2255Z/forest-reservation-ONLY.json'
FUTURE_R5_SHA='c3914908a029ce58ee55124016933f8aa8a850b300da6c269076253b30a9ff3b'
DOMAIN=(640,-1200,1504,-608);STEP=8;ANCHOR=(1104,-1072)
MAX_OUTPUT=16*MIB;MAX_SECONDS=180;MAX_WIRE_COLUMNS=128_000
SURVEY_JOBS=(('A1',1104,-736,96),('A2',1232,-736,96),('B1',976,-1072,48),('B2',976,-1016,48),('B3',976,-960,48))
SOILS={'minecraft:'+v for v in ('grass_block','dirt','coarse_dirt','rooted_dirt','podzol','moss_block','mud','mycelium','packed_mud')}
SOILS.update({'regions_unexplored:peat_dirt','regions_unexplored:silt_dirt'})


def native_surveys(home):
    folder=home/SURVEYS
    if digest(folder/'manifest.json')!=SURVEYS_SHA:raise UserError('Exact completed five-survey manifest required')
    manifest=read_json(folder/'manifest.json');requests={r['id']:r for r in manifest['requests']}
    rows={};proofs=[];overlaps=0
    for name,x,z,radius in SURVEY_JOBS:
        path=folder/(name+'-native-survey.json');terminal=folder/(name+'-terminal.json')
        if path.stat().st_size>2*MIB or terminal.stat().st_size>64*1024 or digest(path)!=requests[name]['sha256']:raise UserError('Native survey member differs or exceeds bound')
        document=read_json(path);report=read_json(terminal);expected={(a,b) for a in range(x-radius,x+radius+1,8) for b in range(z-radius,z+radius+1,8)}
        if report.get('operation')!='survey' or report.get('status')!='complete' or report.get('cursor')!=len(expected) or report.get('failures')!=0 or report.get('cleanup_required') is not False or report.get('temporary_tickets_remaining')!=0 or report.get('pending_shared_chunk_futures')!=0:raise UserError('Native survey is incomplete or has cleanup/measurement failures')
        actual=document['samples']
        if len(actual)!=len(expected) or {(r['x'],r['z']) for r in actual}!=expected:raise UserError('Native survey square lattice differs')
        for row in actual:
            key=row['x'],row['z']
            if key in rows:
                overlaps+=1
                if any(rows[key][k]!=row[k] for k in ('y','ground_y','ocean_floor_y','block','fluid','biome')):raise UserError('Native survey overlaps disagree; no last-write-wins terrain')
            else:rows[key]=row
        proofs.append({'id':name,'command':requests[name]['command'],'columns':len(actual),'survey_sha256':digest(path),'terminal_sha256':digest(terminal),'status':'Native complete,0failures,0tickets,0shared futures'})
    if len(rows)!=1376 or overlaps!=381:raise UserError('Exact complete A/B coverage required')
    return rows,proofs


class Wire:
    def __init__(self,terrain):self.terrain=terrain;self.rows={};self.started=terrain.started;self.collect=True
    def check(self):
        if time.monotonic()-self.started>MAX_SECONDS:raise UserError('Finite180s saved analysis expired; preserve inputs, no generation fallback')
    def column(self,x,z):
        key=x,z
        if key not in self.rows:
            if not self.collect:return self.terrain.column(x,z)
            if len(self.rows)>=MAX_WIRE_COLUMNS:raise UserError('Finite exact column cache exhausted')
            self.rows[key]=self.terrain.column(x,z)
        return self.rows[key]
    def state(self,x,y,z):return self.terrain.state(x,y,z)
    def populate(self,bounds):
        x0,z0,x1,z1=bounds
        # Chunk order keeps the existing four-chunk decoded cache small. Only
        # grid lines, not an invented interpolation inside cells, are admitted.
        for cx in range(x0//16,x1//16+1):
            for cz in range(z0//16,z1//16+1):
                for x in range(max(x0,cx*16),min(x1,cx*16+15)+1):
                    for z in range(max(z0,cz*16),min(z1,cz*16+15)+1):
                        if x%8==0 or z%8==0:self.column(x,z)
                self.check()
        self.collect=False


def exact_graph(wire,bounds=DOMAIN):
    x0,z0,x1,z1=bounds
    if any(n%8 for n in bounds) or x0>x1 or z0>z1 or ((x1-x0)//8+1)*((z1-z0)//8+1)>8192:raise UserError('Finite aligned8m saved graph required')
    cells={(x,z):wire.column(x,z) for x in range(x0,x1+1,8) for z in range(z0,z1+1,8)}
    adj={q:[] for q,r in cells.items() if r['kind']=='dry'};edges={}
    for x,z in adj:
        for dx,dz in ((8,0),(0,8)):
            end=x+dx,z+dz
            if end not in adj:continue
            line=[(x+dx*n//8,z+dz*n//8) for n in range(9)]
            if all(wire.column(*q)['kind']=='dry' for q in line):
                adj[x,z].append(end);adj[end].append((x,z));edges[(x,z),end]=line
        wire.check()
    return cells,adj,edges


def cliffs(wire,edges,bank):
    rows=[]
    for (a,b),line in edges.items():
        if a not in bank or b not in bank:continue
        heights=[wire.column(*q)['surface_y'] for q in line]
        jumps=[abs(v-u) for u,v in zip(heights,heights[1:])]
        if max(jumps)>=4 or max(heights)-min(heights)>=8:
            low=min(range(9),key=lambda n:heights[n]);high=max(range(9),key=lambda n:heights[n])
            rows.append({'lower_observed_ground':[line[low][0],heights[low],line[low][1]],'higher_observed_ground':[line[high][0],heights[high],line[high][1]],'one_metre_ground_profile':[[x,wire.column(x,z)['surface_y'],z] for x,z in line],'maximum_single_ground_step':max(jumps),'height_relief':max(heights)-min(heights)})
    return rows


def walking(wire,cells,edges,bank,protected):
    adj={q:[] for q in bank if q not in protected};witnesses={};tested=0
    for (a,b),line in edges.items():
        if a not in adj or b not in adj:continue
        heights=[wire.column(*q)['surface_y'] for q in line]
        if max(heights)-min(heights)>4 or any(abs(v-u)>1 for u,v in zip(heights,heights[1:])):continue
        tested+=1;proof=body_witness(wire,line,protected)
        if proof is not None:adj[a].append(b);adj[b].append(a);witnesses[frozenset((a,b))]=proof
        wire.check()
    candidates=[q for q,neighbors in adj.items() if neighbors]
    if not candidates:raise UserError('No actual saved three-wide woodland approach')
    start=min(candidates,key=lambda q:(q[0]-1080)**2+(q[1]+1072)**2)
    connected=component(adj,start)
    return adj,witnesses,start,connected,tested


def compose_routes(cells,adj,witnesses,start,connected,cliff_rows):
    toes=[(r['lower_observed_ground'][0],r['lower_observed_ground'][2]) for r in cliff_rows]
    available_toes=[q for q in toes if q in connected]
    highest=max(connected,key=lambda q:(cells[q]['surface_y'],-math.dist(start,q)))
    desires=[('river-bend-loop','River-bend woodland walk',(1136,-1056)),
             ('cliff-foot-ramble','Foot-of-the-rocks ramble',min(available_toes,key=lambda q:math.dist(start,q)) if available_toes else (1008,-1056)),
             ('inland-woodland-walk','Inland woodland and ridge approach',(1232,-832)),
             ('highest-tested-access','Highest reachable tested woodland point',highest)]
    result=[];reserved=set()
    for ident,name,desired in desires:
        target=min(connected,key=lambda q:math.dist(q,desired))
        nodes=route(adj,start,target,lambda a,b:8+3*abs(cells[a]['surface_y']-cells[b]['surface_y']))
        if nodes is None or len(nodes)<3:
            result.append({'id':ident,'name':name,'status':'UNRESOLVED; no authored clearing, stair or guessed route fallback','desired_xz':list(desired)});continue
        detail={}
        for a,b in zip(nodes,nodes[1:]):
            for row in witnesses[frozenset((a,b))]:detail[tuple(row['support'][::2])]=row
        reserved.update(detail)
        result.append({'id':ident,'name':name,'status':'SAVED exact3wide/3high support only; native walking/art pending','desired_xz':list(desired),'nodes_xz':[list(q) for q in nodes],'horizontal_metres':8*(len(nodes)-1),'actual_endpoint_offset_metres':round(math.dist(target,desired),2),'ground_y_range':[min(cells[q]['surface_y'] for q in nodes),max(cells[q]['surface_y'] for q in nodes)],'exact_support_and_headroom':list(detail.values())})
    return result,reserved,highest


def fine_hiking_line(wire,start,goal,protected,bounds=DOMAIN,max_nodes=50_000):
    """A separate ONE-column/two-high natural hiking line, not a wide paved path.

    Cardinal steps must have dry support and differ by at most one actual block.
    Nothing is cut/filled; ordinary one-block ascents may require player jumping.
    This does not relabel a failed three-wide route as a passed wide nature walk.
    """
    checked={};x0,z0,x1,z1=bounds
    def ground(q):
        if q in checked:return checked[q]
        if q in protected or not x0<=q[0]<=x1 or not z0<=q[1]<=z1:checked[q]=None;return None
        row=wire.column(*q)
        if row['kind']!='dry':checked[q]=None;return None
        y=row['surface_y'];body=[wire.state(q[0],y+dy,q[1]) for dy in (1,2)]
        if any(s is None or base(s) not in AIR|SOFT or 'waterlogged=true' in s or base(s) in ('minecraft:bamboo','minecraft:bamboo_sapling') for s in body):checked[q]=None;return None
        checked[q]={'support':[q[0],y,q[1]],'ground_state':row['state'],'two_high_body':body};return checked[q]
    if ground(start) is None or ground(goal) is None:return {'status':'UNRESOLVED; exact hiking endpoint/body is obstructed','desired_xz':list(goal),'native_walking':False}
    pending=[(math.dist(start,goal),0,start)];cost={start:0};previous={};expanded=0
    while pending:
        _,value,q=heapq.heappop(pending)
        if value!=cost[q]:continue
        if q==goal:
            path=[q]
            while q!=start:q=previous[q];path.append(q)
            path.reverse();rows=[ground(q) for q in path]
            return {'status':'SAVED ONE-column/TWO-high hiking line; not a3wide nature walk; native walking/jump/art UNTESTED','width_columns':1,'body_height':2,'nodes_xz':[list(q) for q in path],'horizontal_metres':len(path)-1,'maximum_actual_step':max(abs(a['support'][1]-b['support'][1]) for a,b in zip(rows,rows[1:])) if len(rows)>1 else 0,'ground_y_range':[min(r['support'][1] for r in rows),max(r['support'][1] for r in rows)],'exact_support_and_body':rows,'expanded_nodes':expanded,'native_walking':False}
        expanded+=1
        if expanded>max_nodes:return {'status':'UNRESOLVED finite hiking search exhausted; no clearing/stair/teleport fallback','desired_xz':list(goal),'expanded_nodes':expanded,'native_walking':False}
        y=ground(q)['support'][1]
        for dx,dz in ((1,0),(-1,0),(0,1),(0,-1)):
            other=q[0]+dx,q[1]+dz;support=ground(other)
            if support is None:continue
            rise=abs(y-support['support'][1])
            if rise>1:continue
            candidate=value+1+rise*0.5
            if candidate<cost.get(other,math.inf):cost[other]=candidate;previous[other]=q;heapq.heappush(pending,(candidate+math.dist(other,goal),candidate,other))
        wire.check()
    return {'status':'UNRESOLVED; no preserved exact natural hiking connection','desired_xz':list(goal),'expanded_nodes':expanded,'native_walking':False}


def protection(home,registry):
    if digest(home/INDEX)!=INDEX_SHA or digest(home/FUTURE_R5)!=FUTURE_R5_SHA:raise UserError('Exact historical architectural index and FUTURE R5 mask required')
    index=read_json(home/INDEX);plans=[r for r in index['plans'] if r['name']!='Whole plaza/fountain/body/AIR/routes envelope']
    if sum(Path(r['path']).stat().st_size for r in plans)>128*MIB:raise UserError('Bounded architectural mask inputs exceeded')
    protected,custody=exclusions([(r['name'],r['path'],r['sha256']) for r in plans],registry)
    future=read_json(home/FUTURE_R5)
    if not future.get('construction_forbidden') or future['backup_sha256']!=CHECKPOINT_SHA:raise UserError('FUTURE R5 reservation must not become constructed fact')
    extra,proof=exclusions([('FUTURE UNPLACED R5 centerpiece/AIR/arrival',home/FUTURE_R5,FUTURE_R5_SHA)],registry)
    protected.update(extra);custody.extend(proof)
    return protected,custody


def prepare(home):
    home=Path(home).resolve()
    if not home.is_relative_to(Path(r'D:\A World for Two\staging\world-tests')):raise UserError('Owned artistic staging only')
    reserve=guard(MIB,MAX_OUTPUT);native,proofs=native_surveys(home);registry=read_json(home/'dashboard/settlement/registry.json')
    protected,custody=protection(home,registry)
    terrain=ExtentTerrain(home,{'id':CHECKPOINT,'sha256':CHECKPOINT_SHA,'verified':True},registry)
    try:
        wire=Wire(terrain);wire.populate(DOMAIN);cells,land,edges=exact_graph(wire);bank=component(land,ANCHOR)
        comparisons=[]
        for q,row in native.items():
            saved=wire.column(*q)
            if saved['kind']=='unknown':raise UserError('A completed native sample is not FULL in this exact stopped checkpoint')
            if saved['kind']=='dry' and not row['fluid'] and saved['surface_y']!=row['ground_y']-1:
                comparisons.append({'xz':list(q),'saved_kind':saved['kind'],'saved_ground':saved['surface_y'],'native_ground_feet':row['ground_y'],'meaning':'Retained point-in-time/classification difference; not normalized'})
        cliff_rows=cliffs(wire,edges,bank);walk,witnesses,start,connected,tested=walking(wire,cells,edges,bank,protected)
        routes,reserved,highest=compose_routes(cells,walk,witnesses,start,connected,cliff_rows)
        observed_high=max(bank,key=lambda q:cells[q]['surface_y'])
        foot_candidates=[r['lower_observed_ground'] for r in cliff_rows if r['lower_observed_ground'][1]>=80]
        foot=min(foot_candidates,key=lambda r:math.dist(start,(r[0],r[2]))) if foot_candidates else None
        fine_targets=[('highest-observed-cliff-hike',observed_high)]
        if foot:fine_targets.append(('actual-cliff-toe-hike',(foot[0],foot[2])))
        fine=[]
        for ident,target in fine_targets:
            line=fine_hiking_line(wire,start,target,protected);line['id']=ident;fine.append(line)
            reserved.update(tuple(q) for q in line.get('nodes_xz',[]))
        zones={'river_fringe':[],'sheltered_footwoods':[],'middle_mixed_woods':[],'upper_ridge_woods':[],'rock_or_nonsoil':[],'protected':[]}
        for q in sorted(bank):
            row=cells[q]
            key='protected' if q in protected else 'rock_or_nonsoil' if base(row['state']) not in SOILS else 'river_fringe' if row['surface_y']<=80 else 'sheltered_footwoods' if row['surface_y']<=115 else 'middle_mixed_woods' if row['surface_y']<=150 else 'upper_ridge_woods'
            zones[key].append([q[0],row['surface_y'],q[1]])
        result={'format':'awft-whole-bank-forest-composition:1','checkpoint_id':CHECKPOINT,'checkpoint_sha256':CHECKPOINT_SHA,'domain':list(DOMAIN),'node_step':8,'saved_samples':list(cells.values()),'sample_counts':dict(Counter(r['kind'] for r in cells.values())),'dry_bank_anchor':list(ANCHOR),'bank_nodes_xz':[list(q) for q in sorted(bank)],'bank_node_count':len(bank),'bank_bounds':[min(x for x,z in bank),min(z for x,z in bank),max(x for x,z in bank),max(z for x,z in bank)],'bank_ground_y_range':[min(cells[q]['surface_y'] for q in bank),max(cells[q]['surface_y'] for q in bank)],'dry_nodes_other_banks_not_merged':len(land)-len(bank),'one_metre_dry_edge_count':sum(a in bank and b in bank for a,b in edges),'actual_wire_columns_examined':len(wire.rows),'cliff_ground_profiles':cliff_rows,'native_survey_proofs':proofs,'native_saved_height_differences_retained':comparisons,'walk_start_xz':list(start),'walking_body_edges_tested':tested,'three_wide_walk_component_nodes':len(connected),'highest_tested_reachable_ground':[highest[0],cells[highest]['surface_y'],highest[1]],'highest_observed_bank_ground':[observed_high[0],cells[observed_high]['surface_y'],observed_high[1]],'walks':routes,'fine_hiking_lines':fine,'walking_columns_xz':[list(q) for q in sorted(reserved)],'walking_whole_growth_skirt_xz':[list(q) for q in sorted(buffered_columns(reserved,5))],'composition_zones':zones,'exclusion_custody':custody,'future_R5':{'path':FUTURE_R5,'sha256':FUTURE_R5_SHA,'status':'FUTURE UNPLACED, protected plus5m; never constructed evidence'},'sources':terrain.snapshot.sources.copy(),'saved_status_counts':dict(Counter(terrain.statuses.values())),'MCA_raw_bytes':terrain.raw_bytes,'unknown_chunks':[[*q,why] for q,why in sorted(terrain.unknown.items())],'saved_BEs_preserved':[list(q) for q in sorted(terrain.entities)],'native_actions':0,'growth_authority':False,'life_authority':False,'limitations':['Dry graph edges inspect every1m center column, not cell interiors or growth volumes','A land connection is not automatically a gentle or passable footpath','Native grown saplings remain default; full normal/large crowns plus8m read/physics perimeter require separate admission','Final construction, R5 placement, a fresh stopped checkpoint and all-current masks must precede LIFE','Any bank touching a study boundary is censored there, not a claimed natural end of land']}
        wire.check()
    finally:terrain.close()
    raw=(json.dumps(result,separators=(',',':'),ensure_ascii=False)+'\n').encode()
    meta={'format':'awft-whole-bank-forest-receipt:1','created':utcnow(),'status':'SAVED GEOGRAPHY AND COMPOSITION; NATIVE ART/WALK/GROWTH PENDING','source_sha256':digest(Path(__file__)),'checkpoint_id':CHECKPOINT,'checkpoint_sha256':CHECKPOINT_SHA,'reserve':reserve,'read_only_six_regions':list(REGIONS),'MCA_raw_limit':MAX_RAW,'MCA_raw_bytes':result['MCA_raw_bytes'],'proposal_sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),'bank_nodes':result['bank_node_count'],'bank_bounds':result['bank_bounds'],'bank_y_range':result['bank_ground_y_range'],'zones':{k:len(v) for k,v in zones.items()},'cliff_profiles':len(cliff_rows),'walks':[{'id':v['id'],'status':v['status'],'metres':v.get('horizontal_metres'),'endpoint_offset':v.get('actual_endpoint_offset_metres')} for v in routes],'fine_hiking_lines':[{'id':v['id'],'status':v['status'],'metres':v.get('horizontal_metres'),'height_range':v.get('ground_y_range'),'expanded':v.get('expanded_nodes')} for v in fine],'highest_tested_reachable_ground':result['highest_tested_reachable_ground'],'highest_observed_bank_ground':result['highest_observed_bank_ground'],'native_actions':0,'growth_authority':False}
    encoded=(json.dumps(meta,indent=2)+'\n').encode()
    if len(raw)+len(encoded)>MAX_OUTPUT:raise UserError('Finite16MiB composition output exceeded')
    out=home/'staging'/('whole-bank-forest-'+str(time.time_ns()));out.mkdir()
    (out/'composition.json').write_bytes(raw);(out/'manifest.json').write_bytes(encoded)
    return {'directory':str(out),'manifest_sha256':hashlib.sha256(encoded).hexdigest(),**{k:meta[k] for k in ('bank_nodes','bank_bounds','bank_y_range','zones','cliff_profiles','walks','highest_tested_reachable_ground','MCA_raw_bytes')}}


def finalize_metadata(home,source_directory,zipline_reservation,zipline_sha256):
    """Explicit metadata/exclusion join; no repeated MCA read or changed geometry."""
    home=Path(home).resolve();source_directory=Path(source_directory).resolve();zipline_reservation=Path(zipline_reservation).resolve()
    if not home.is_relative_to(Path(r'D:\A World for Two\staging\world-tests')) or any(not p.is_relative_to(home/'staging') for p in (source_directory,zipline_reservation)):raise UserError('Owned immutable staging inputs only')
    reserve=guard(0,MAX_OUTPUT);manifest=read_json(source_directory/'manifest.json');path=source_directory/'composition.json'
    if path.stat().st_size>MAX_OUTPUT or digest(path)!=manifest.get('proposal_sha256') or path.stat().st_size!=manifest.get('bytes'):raise UserError('Original saved geography differs')
    if manifest.get('checkpoint_sha256')!=CHECKPOINT_SHA or zipline_reservation.stat().st_size>MIB or digest(zipline_reservation)!=zipline_sha256:raise UserError('Exact current saved geography/finite prospective exclusion required')
    data=read_json(path);mask=read_json(zipline_reservation)
    if mask.get('format')!='awft-prospective-growth-exclusion:1' or mask.get('checkpoint_sha256')!=CHECKPOINT_SHA or mask.get('native_plan') is not False:raise UserError('Explicit unbuilt non-native zipline reservation required')
    # Keep the original measured route/geometry, but make incomplete target
    # arrival unmissable. Never claim a cliff-foot hike ended43m/190m short.
    for row in data['walks']:
        if 'actual_endpoint_offset_metres' in row:
            row['reaches_desired_target']=row['actual_endpoint_offset_metres']==0
            if not row['reaches_desired_target']:row['status']='PARTIAL saved3wide route; does NOT reach named cliff/inland target; no native walking acceptance'
    excluded={tuple(q) for q in mask['all_growth_excluded_columns_xz']};removed={}
    for name,rows in data['composition_zones'].items():
        if name=='protected':continue
        kept=[r for r in rows if (r[0],r[2]) not in excluded];removed[name]=len(rows)-len(kept);data['composition_zones'][name]=kept
    data.update(data_generator_sha256=manifest['source_sha256'],origin_manifest_sha256=digest(source_directory/'manifest.json'),
                metadata_join_source_sha256=digest(Path(__file__)),future_zipline_exclusion={'path':zipline_reservation.relative_to(home).as_posix(),'sha256':zipline_sha256,'columns':len(excluded),'status':mask['status']},zipline_removed_candidate_centres=removed,
                final_admission='PROPOSAL ONLY: R5/zipline/access still unbuilt; final native construction, all-current exclusion rebinding and growth/LIFE admission remain mandatory')
    raw=(json.dumps(data,separators=(',',':'),ensure_ascii=False)+'\n').encode()
    meta={'format':'awft-whole-bank-final-metadata:1','created':utcnow(),'checkpoint_id':CHECKPOINT,'checkpoint_sha256':CHECKPOINT_SHA,'source_directory':source_directory.relative_to(home).as_posix(),'origin_manifest_sha256':data['origin_manifest_sha256'],'data_generator_sha256':manifest['source_sha256'],'metadata_join_source_sha256':digest(Path(__file__)),'prospective_zipline_sha256':zipline_sha256,'zipline_removed_candidate_centres':removed,'proposal_sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),'reserve':reserve,'native_actions':0,'growth_authority':False,'data_or_geometry_recomputed':False}
    encoded=(json.dumps(meta,indent=2)+'\n').encode()
    if len(raw)+len(encoded)>MAX_OUTPUT:raise UserError('Finite16MiB metadata join exceeded')
    out=home/'staging'/('whole-bank-forest-final-metadata-'+str(time.time_ns()));out.mkdir();(out/'composition.json').write_bytes(raw);(out/'manifest.json').write_bytes(encoded)
    return {'directory':str(out),'manifest_sha256':hashlib.sha256(encoded).hexdigest(),'proposal_sha256':meta['proposal_sha256'],'zipline_removed_candidate_centres':removed,'native_actions':0}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--home',type=Path,required=True)
    print(json.dumps(prepare(p.parse_args().home),indent=2))
