"""Bounded saved-land bank/contour walks proposal, never planting or native action."""
from __future__ import annotations
import argparse
from collections import Counter,deque
import hashlib,heapq,json,math,time
from pathlib import Path
from control_room.common import UserError,digest,read_json,utcnow
from tools.artistic_south_extent import ExtentTerrain,PLAZA,PLAZA_SHA
from tools.artistic_south_forest import AIR,SOFT,exclusions,buffered_columns
from tools.playtest import guard
from tools.settlement_attractions import base

MIB=1024**2;MAX_OUTPUT=16*MIB;DOMAIN=(944,-1184,1504,-752);STEP=8;ANCHOR=(1104,-1072)
INDEX='staging/south-forest-inputs-20261027T1930Z/exclusions.json'
COURT=('staging/court-bramble-context-VERIFY-ONLY-1793131918249037500/court-context-full-VERIFY-ONLY.json','4e6864e09e425130345bcd8dc16e4a45cc81b50ddfb04447cdb8f71a7b81b6c7')
BRAMBLE=('staging/bramble-retained-vines-VERIFY-ONLY-1793132113568241300/bramble-vines-full-VERIFY-ONLY.json','2b9dd47c0ef36bd113a81466c883a49b56d8268898bca289bd8e5dba497ebb08')


def land_graph(terrain,bounds=DOMAIN,step=STEP):
 xa,za,xb,zb=bounds
 if step!=8 or xa>xb or za>zb or ((xb-xa)//step+1)*((zb-za)//step+1)>8192:raise UserError('Finite eight-metre candidate lattice only')
 cells={(x,z):terrain.column(x,z) for x in range(xa,xb+1,step) for z in range(za,zb+1,step)}
 dry={q:r for q,r in cells.items() if r['kind']=='dry'};adj={q:[] for q in dry};edges={}
 for x,z in dry:
  for dx,dz in ((step,0),(0,step)):
   end=x+dx,z+dz
   if end not in dry:continue
   line=[(x+dx*n//step,z+dz*n//step) for n in range(step+1)]
   if all(terrain.column(*q)['kind']=='dry' for q in line):adj[x,z].append(end);adj[end].append((x,z));edges[frozenset(((x,z),end))]=line
   if time.monotonic()-terrain.started>120:raise UserError('Bounded saved bank traversal exceeded120s')
 return cells,adj,edges


def component(adj,anchor):
 if anchor not in adj:raise UserError('Reviewed dry bank anchor is absent; do not choose another shore silently')
 reached={anchor};queue=deque([anchor])
 while queue:
  for q in adj[queue.popleft()]:
   if q not in reached:reached.add(q);queue.append(q)
 return reached


def body_witness(terrain,line,protected):
 """Actual one-metre support/body columns across a three-wide gentle edge."""
 ax,az=line[0];bx,bz=line[-1];across=(0,1) if ax!=bx else (1,0);rows={};middle=[]
 for x,z in line:
  heights=[]
  for n in (-1,0,1):
   q=x+across[0]*n,z+across[1]*n
   if q in protected:return None
   row=terrain.column(*q)
   if row['kind']!='dry':return None
   g=row['surface_y'];states=[terrain.state(q[0],g+dy,q[1]) for dy in(1,2,3)]
   if any(s is None or base(s) not in AIR|SOFT or 'waterlogged=true' in s for s in states):return None
   rows[q]={'support':[q[0],g,q[1]],'ground_state':row['state'],'standing_and_headroom':states};heights.append(g)
  if max(heights)-min(heights)>1:return None
  middle.append(terrain.column(x,z)['surface_y'])
 if any(abs(a-b)>1 for a,b in zip(middle,middle[1:])) or max(middle)-min(middle)>4:return None
 return list(rows.values())


def route(adj,start,target,cost):
 pending=[(0,start)];best={start:0};previous={}
 while pending:
  score,q=heapq.heappop(pending)
  if score!=best[q]:continue
  if q==target:
   result=[q]
   while q!=start:q=previous[q];result.append(q)
   return result[::-1]
  for other in adj.get(q,[]):
   candidate=score+cost(q,other)
   if candidate<best.get(other,math.inf):best[other]=candidate;previous[other]=q;heapq.heappush(pending,(candidate,other))
 return None


def compose(terrain,protected):
 cells,land,edges=land_graph(terrain);bank=component(land,ANCHOR);walking={q:[] for q in bank if q not in protected};witnesses={}
 for pair,line in edges.items():
  a,b=sorted(pair)
  if a not in walking or b not in walking:continue
  witness=body_witness(terrain,line,protected)
  if witness is not None:walking[a].append(b);walking[b].append(a);witnesses[pair]=witness
  if time.monotonic()-terrain.started>120:raise UserError('Bounded saved walk refinement exceeded120s')
 usable={q for q,near in walking.items() if near}
 if not usable:raise UserError('No three-wide gentle saved woodland approach; native survey required')
 start=min(usable,key=lambda q:(q[0]-1080)**2+(q[1]+1072)**2);walk_component=component(walking,start)
 routes=[];reserved=set()
 for ident,name,desired in (('cliff-view-ramble','A ramble towards the cliff views',(1008,-1056)),('river-bend-walk','A quiet walk above the river bend',(1136,-1056))):
  end=min(walk_component,key=lambda q:(q[0]-desired[0])**2+(q[1]-desired[1])**2)
  nodes=route(walking,start,end,lambda a,b:8+abs(cells[a]['surface_y']-cells[b]['surface_y'])*3)
  if nodes is None or len(nodes)<3:
   routes.append({'id':ident,'name':name,'status':'PENDING finite native survey; no unsafe/fabricated fallback','desired_end':list(desired)});continue
  columns={}
  for a,b in zip(nodes,nodes[1:]):
   for row in witnesses[frozenset((a,b))]:columns[tuple(row['support'][::2])]=row
  reserved.update(columns)
  routes.append({'id':ident,'name':name,'status':'SOURCE ONLY saved support/headroom; native walking/model review pending','nodes_xz':[list(q) for q in nodes],'actual_endpoint_offset_from_composition_metres':round(math.dist(end,desired),2),'length_horizontal_metres':8*(len(nodes)-1),'width_metres':3,'exact_saved_columns':list(columns.values()),'intent':'Follow retained contours and ordinary soft ground/rock, preserve trees, no broad paving/terracing/river crossing; this is an empty walking reservation, not a construction plan'})
 # Existing open habitat pockets, never instructions to clear a new circle.
 glades=[]
 for q in sorted(bank,key=lambda q:hashlib.sha256(f'glade:{q[0]}:{q[1]}'.encode()).hexdigest()):
  if q in protected or q in reserved or cells[q].get('existing_canopy_y') is not None or cells[q]['surface_y']>100:continue
  if any(math.dist(q,tuple(v['center_xz']))<36 for v in glades):continue
  patch=[(q[0]+dx,q[1]+dz) for dx in range(-2,3) for dz in range(-2,3)]
  rows=[]
  for x,z in patch:
   row=terrain.column(x,z)
   if (x,z) in protected or (x,z) in reserved or row['kind']!='dry':break
   g=row['surface_y'];body=[terrain.state(x,g+dy,z) for dy in(1,2,3)]
   if any(s is None or base(s) not in AIR|SOFT or 'waterlogged=true' in s for s in body):break
   rows.append({'ground':[x,g,z],'state':row['state']})
  if len(rows)==25 and max(v['ground'][1] for v in rows)-min(v['ground'][1] for v in rows)<=1:
   glades.append({'center_xz':list(q),'status':'Existing saved open5x5 pocket; no clearing/spawn authority','support_columns':rows,'intent':'Small low meadow/fern edge habitat room; native fauna collision/food/AI acceptance belongs to South lane'})
  if len(glades)==4:break
 heights=[cells[q]['surface_y'] for q in bank]
 return {'candidate_domain':list(DOMAIN),'node_step':STEP,'dry_bank_anchor':list(ANCHOR),'bank_nodes_xz':[list(q) for q in sorted(bank)],'bank_sample_count':len(bank),'bank_sample_y_range':[min(heights),max(heights)],'bank_edges':'Each linked eight-metre edge is checked at every one-metre center column as actual saved dry ground; raster interior/whole growth envelopes are NOT thereby admitted','land_other_components_not_merged':len(land)-len(bank),'walk_routes':routes,'walk_columns':sorted(map(list,reserved)),'walk_columns_with_five_metre_growth_skirt':sorted(map(list,buffered_columns(reserved,5))),'existing_habitat_pockets':glades,'composition':[{'name':'Sheltered mixed woods','intent':'Dense irregular native-grown crowns outside all complete-growth exclusions; varied broadleaf species rather than rows; retain existing trees and rock.'},{'name':'Cliff-foot shade','intent':'Fern-rich mossy floor and low understory pockets below actual rock faces; no soil fill, cliff flattening or assumed passage above the observed foot.'},{'name':'River-edge fringe','intent':'Irregular damp low growth on confirmed dry support, retain reeds/water/shore; no river filling or trees growing from a map-color mask.'},{'name':'Habitat rooms','intent':'A few existing small clear pockets with dense understory edges, sufficient space for native fauna; all spawns/food/AI remain separately gated.'}],'native_survey_requests':[{'id':'southern-cliff-continuation','bounds':[1008,-832,1328,-640],'sample_step':8,'maximum_columns':1025,'maximum_chunk_addresses':273},{'id':'western-foot-continuation','bounds':[928,-1120,1024,-912],'sample_step':8,'maximum_columns':351,'maximum_chunk_addresses':98}],'growth_authority':False,'native_actions':0,'world_writes':0,'manual_or_native_trees_placed':0}


def prepare(home,checkpoint_id,checkpoint_sha):
 home=Path(home).resolve()
 if not home.is_relative_to(Path(r'D:\A World for Two\staging\world-tests')):raise UserError('Owned artistic home only')
 if checkpoint_id!='20261027T191930Z-f306da' or checkpoint_sha!='8efabed7d75aa02015ed2165ebb249c36da6e301dfd3ef8c971f0e20c9de4f5c':raise UserError('Exact reviewed immutable191930 geography only')
 reserve=guard(MIB,MAX_OUTPUT);registry=read_json(home/'dashboard/settlement/registry.json');index=read_json(home/INDEX);plans=[]
 for row in index['plans']:
  if row['name']=='Rose and Lantern Court full':row=row|{'path':str(home/COURT[0]),'sha256':COURT[1]}
  elif row['name']=='Bramble Lane full':row=row|{'path':str(home/BRAMBLE[0]),'sha256':BRAMBLE[1]}
  plans.append(row)
 protected,custody=exclusions([(row['name'],row['path'],row['sha256']) for row in plans],registry)
 plaza=read_json(home/PLAZA)
 if digest(home/PLAZA)!=PLAZA_SHA:raise UserError('Exact whole plaza reservation required')
 xa,za,xb,zb=plaza['bounds'];protected.update((x,z) for x in range(xa-5,xb+6) for z in range(za-5,zb+6));plans.append({'name':'Whole plaza/fountain/body/AIR/routes envelope','path':str(home/PLAZA),'sha256':PLAZA_SHA})
 terrain=ExtentTerrain(home,{'id':checkpoint_id,'sha256':checkpoint_sha,'verified':True},registry)
 try:result=compose(terrain,protected);sources=terrain.snapshot.sources.copy()
 finally:terrain.close()
 result.update(format='awft-south-contour-walks:1',checkpoint_id=checkpoint_id,checkpoint_sha256=checkpoint_sha,source_sha256=digest(Path(__file__)),extent_reader_sha256=digest(Path('tools/artistic_south_extent.py')),exclusion_index_source_sha256=digest(home/INDEX),exclusion_custody=custody,plaza_whole_envelope_five_metre_skirt=True,sources=sources,protected_column_count=len(protected),status='SOURCE ONLY; candidate bank/paths/habitat rooms, exact native FULL/growth/collision/visual acceptance required')
 result['final_exclusion_index']=index|{'plans':plans,'note':'Rebind current postconstruction native checkpoint before any growth. All addressed AIR/BEs/routes plus5m and entire plaza envelope protected; all four native vines and21 Bramble connector ground contexts retained. Original native behavior-witness fields preserved. Add the explicit contour-walk growth skirts before any landscape admission.'}
 raw=(json.dumps(result,separators=(',',':'),ensure_ascii=False)+'\n').encode();manifest={'format':'awft-south-contour-walks-receipt:1','created':utcnow(),'source_sha256':digest(Path(__file__)),'checkpoint_id':checkpoint_id,'checkpoint_sha256':checkpoint_sha,'bank_samples':result['bank_sample_count'],'bank_y_range':result['bank_sample_y_range'],'routes':[{'name':v['name'],'status':v['status'],'length_horizontal_metres':v.get('length_horizontal_metres')} for v in result['walk_routes']],'habitat_pockets':len(result['existing_habitat_pockets']),'proposal_sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),'reserve':reserve,'native_actions':0,'strict_landscape_acceptance':False}
 meta=(json.dumps(manifest,indent=2)+'\n').encode()
 if len(raw)+len(meta)>MAX_OUTPUT:raise UserError('Finite contour-walk output exceeded')
 out=home/'staging'/('south-contour-walks-'+str(time.time_ns()));out.mkdir();(out/'composition.json').write_bytes(raw);(out/'manifest.json').write_bytes(meta)
 return {'directory':str(out),'manifest_sha256':hashlib.sha256(meta).hexdigest(),**{k:manifest[k] for k in ('bank_samples','bank_y_range','routes','habitat_pockets','proposal_sha256')}}

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--home',required=True,type=Path);p.add_argument('--checkpoint-id',required=True);p.add_argument('--checkpoint-sha',required=True);a=p.parse_args();print(json.dumps(prepare(a.home,a.checkpoint_id,a.checkpoint_sha),indent=2))
