"""Coast-first eastern Tortuga re-layout; old grid anchors do not define lots.

The output is exact source geometry/room-transfer planning, not native admission.
Original terrain/north membership is authenticated. Fresh48+ typed custody is
mandatory before any source cell, stock pod or current world object is moved.
"""
from __future__ import annotations

import argparse
from collections import Counter,deque
import hashlib
import heapq
import json
from pathlib import Path
import time

from control_room.common import UserError,digest,read_json
from tools.artistic_east_tortuga_retrofit import LEDGER,LEDGER_SHA,checked
from tools.playtest import guard


MIB=1024**2
FINE=('staging/north-bank-eastern-fine-1793150536373132600/fine-land.json','38859bebd704f09854e59fd3856703e0813e4c0354a5aa78eeb920b336c33baa')
NORTH=('staging/north-bank-residual-1793158994899675300/north-connected-columns-ONLY.json','594706123bb9ac14f447a8f95f810cf595c952f1d8edb1c6ebfba4ae54e5b103')
MAX_OUTPUT=16*MIB
VEC=((1,0),(-1,0),(0,1),(0,-1))

# A deliberately crooked connected network, not one straight road per old row.
# Coordinates are author intents: exact full two-metre dry patches are selected
# within a finite8m source radius and every such adjustment is recorded.
STREETS=(
 ('harbor-fold',[(1292,-1265),(1289,-1251),(1304,-1236),(1289,-1221),(1296,-1207),(1283,-1189),(1293,-1172),(1284,-1153),(1298,-1134),(1296,-1122)]),
 ('tideward-hem',[(1355,-1264),(1358,-1248),(1346,-1228),(1365,-1221),(1374,-1205),(1364,-1187),(1358,-1168),(1367,-1152),(1378,-1133),(1389,-1122)]),
 ('bridge-weave',[(1232,-1217),(1233,-1201),(1244,-1187),(1238,-1170),(1251,-1157),(1254,-1138),(1263,-1124)]),
 ('harbor-cross',[(1289,-1251),(1316,-1243),(1345,-1245),(1358,-1248)]),
 ('upper-fold-cross',[(1289,-1221),(1317,-1225),(1341,-1216),(1365,-1221)]),
 ('market-crook',[(1233,-1201),(1261,-1198),(1283,-1189),(1311,-1200),(1340,-1192),(1364,-1187)]),
 ('sailmaker-turn',[(1238,-1170),(1264,-1178),(1293,-1172),(1320,-1180),(1358,-1168)]),
 ('low-quay-turn',[(1254,-1138),(1274,-1145),(1298,-1134),(1324,-1148),(1350,-1137),(1378,-1133)]),
)

# New programs/positions deliberately differ from the37 former9×9 lots.
# Each is a compound of several unequal short/long/wide low/tall roof masses.
SEEDS=(
 ('lantern-harbor-inn','Lantern Harbor Inn',(1298,-1253),'inn',3),
 ('copper-kettle','Copper Kettle Chandlery',(1317,-1258),'hardware',2),
 ('gullhorn','Gullhorn Pilot House',(1354,-1261),'pilot',2),
 ('bent-gull','The Bent Gull Quayside',(1346,-1247),'galley',2),
 ('tin-whistle','Tin Whistle House',(1324,-1243),'music',3),
 ('pepper-fold','Pepper Fold Rooms',(1296,-1236),'galley',2),
 ('copper-bell','Copper Bell Bindery',(1312,-1226),'archive',2),
 ('tide-broker','Tide Broker’s House',(1340,-1227),'charts',3),
 ('salt-mason','Salt Mason’s Yard',(1363,-1216),'hardware',1),
 ('bridge-customs','The Crooked Customs',(1238,-1210),'charts',2),
 ('worn-book','The Worn Book',(1255,-1215),'archive',3),
 ('ropes-pearl','Ropes & Pearl',(1275,-1210),'cloth',2),
 ('crooked-inn','Crooked Lantern Rooms',(1298,-1215),'inn',3),
 ('keel-store','Keel Store & Galley',(1323,-1211),'galley',2),
 ('marrow-side','Marrow Side Cloth House',(1345,-1209),'cloth',2),
 ('shoal-warden','Shoal Warden’s Quay',(1370,-1202),'pilot',2),
 ('bridge-cooper','Bridge Cooperage',(1232,-1195),'cooper',2),
 ('lampblack','Lampblack Court',(1249,-1194),'hardware',3),
 ('net-mender','Net Mender’s Hall',(1270,-1190),'cloth',2),
 ('moon-branch','Moon Branch Rooms',(1294,-1195),'inn',3),
 ('moth-candle','Moth & Candle',(1314,-1191),'hardware',2),
 ('nail-drift','Nail & Drift',(1338,-1188),'cooper',1),
 ('tide-fish','Tidefish Hall',(1361,-1187),'fish',2),
 ('willow-door','Willow Door House',(1238,-1179),'galley',2),
 ('anchor-dice','Anchor & Dice',(1258,-1174),'inn',3),
 ('crooked-row','Crooked Row Outfitters',(1282,-1175),'cloth',2),
 ('lantern-cod','Lantern Cod Galley',(1302,-1179),'fish',1),
 ('sail-fool','The Sailor’s Folly',(1325,-1170),'music',3),
 ('old-rum','Old Rum Warehouse',(1350,-1174),'warehouse',2),
 ('east-coal','East Coal Chandlery',(1362,-1157),'hardware',1),
 ('bay-kettle','Bay Kettle Rooms',(1247,-1157),'galley',2),
 ('sandbar','Sandbar Carpenter',(1265,-1153),'cooper',2),
 ('foxtail','Foxtail House',(1288,-1155),'inn',3),
 ('navy-blue','Navy Blue Tailor',(1313,-1159),'cloth',2),
 ('quarter-jack','Quarter Jack’s Hall',(1336,-1150),'music',3),
 ('cook-snap','Cook & Snap',(1360,-1142),'fish',2),
 ('thin-sail','Thin Sail Lookout',(1384,-1125),'pilot',1),
 ('river-stone','River Stone Rooms',(1260,-1135),'inn',2),
 ('harbor-chair','Harbor Chair & Cup',(1283,-1129),'galley',2),
 ('white-clam','White Clam Warehouse',(1308,-1130),'warehouse',1),
 ('split-shell','Split Shell House',(1333,-1127),'cooper',2),
 ('pelican-forge','Pelican Forge',(1355,-1122),'hardware',2),
)


def adjacent(p):return ((p[0]+dx,p[1]+dz) for dx,dz in VEC)
def patch(p):return {(p[0]+dx,p[1]+dz) for dx in (0,1) for dz in (0,1)}
def distance(a,b):return abs(a[0]-b[0])+abs(a[1]-b[1])


def nearest(intent,valid,maximum,label):
    options=[p for p in valid if distance(p,intent)<=maximum]
    if not options:raise UserError('No source-qualified actual dry position within the finite intent radius: '+label+' '+str(intent))
    return min(options,key=lambda p:(distance(p,intent),p))


def astar(start,goal,valid):
    queue=[(distance(start,goal),0,start)];cost={start:0};parent={};examined=0
    while queue:
        _,g,p=heapq.heappop(queue)
        if g!=cost[p]:continue
        examined+=1
        if examined>60000:raise UserError('Finite exact dry two-metre path search exceeded')
        if p==goal:
            out=[p]
            while p!=start:p=parent[p];out.append(p)
            return list(reversed(out))
        for q in adjacent(p):
            if q not in valid:continue
            # A small preference for few turns makes native2m routes legible,
            # while the authored waypoints provide the deliberate town bends.
            turn=int(p in parent and (q[0]-p[0],q[1]-p[1])!=(p[0]-parent[p][0],p[1]-parent[p][1]))
            ng=g+10+turn
            if ng<cost.get(q,10**9):cost[q]=ng;parent[q]=p;heapq.heappush(queue,(ng+10*distance(q,goal),ng,q))
    raise UserError('No complete source-qualified dry2m connection: '+str((start,goal)))


def largest_rectangle(cells,max_width=14,max_depth=25,min_width=4,min_depth=5):
    if not cells:return None
    xs=[p[0] for p in cells];zs=[p[1] for p in cells];x0,x1=min(xs),max(xs);z0,z1=min(zs),max(zs)
    heights={x:0 for x in range(x0,x1+1)};best=None
    for z in range(z0,z1+1):
        for x in heights:heights[x]=heights[x]+1 if (x,z) in cells else 0
        for left in range(x0,x1+1):
            h=max_depth
            for right in range(left,min(x1,left+max_width-1)+1):
                h=min(h,heights[right]);w=right-left+1
                if w<min_width or h<min_depth:continue
                box=(left,z-h+1,right,z);score=w*h
                if best is None or (score,-abs(w-h),box)>(best[0],best[1],best[2]):best=(score,-abs(w-h),box)
    return None if best is None else best[2]


def rectangle(box):return {(x,z) for x in range(box[0],box[2]+1) for z in range(box[1],box[3]+1)}


def grow_parcels(land,roads,seeds,fixed):
    available=land-roads;claimed={};queue=[];scores={}
    for index,row in enumerate(seeds):
        p=tuple(row['exact_seed'])
        if p not in available:raise UserError('New compound seed must occupy real dry non-street land')
        score=(0,index)
        if score<scores.get(p,(10**12,10**12)):
            scores[p]=score;heapq.heappush(queue,(0,index,p))
    for p,index in fixed.items():
        if p not in available:raise UserError('A retained private anchor conflicts with a street/water/accepted original')
        scores[p]=(0,index);heapq.heappush(queue,(0,index,p))
    pops=0
    while queue:
        score,index,p=heapq.heappop(queue);pops+=1
        if pops>400000:raise UserError('Finite coast-parcel growth exceeded')
        if p not in available or p in fixed and fixed[p]!=index:continue
        if scores.get(p)!=(score,index):continue
        if p in claimed:continue
        claimed[p]=index
        # Each explicitly authored program has different long/wide bias. Roads
        # and coast determine parcel edges, not the original nine-block boxes.
        long_x=(index%3)==0;wx,wz=(8,11) if long_x else (11,8) if index%3==1 else (10,10)
        for q in adjacent(p):
            if q not in available or q in claimed or q in fixed and fixed[q]!=index:continue
            step=wx if q[0]!=p[0] else wz;candidate=(score+step,index)
            if candidate<scores.get(q,(10**12,10**12)):
                scores[q]=candidate;heapq.heappush(queue,(score+step,index,q))
    parcels=[{p for p,k in claimed.items() if k==i} for i in range(len(seeds))]
    return parcels,available-set(claimed)


def masses(cells,typology,pin=False):
    remaining=set(cells);out=[]
    if pin:
        forced=(1293,-1258,1303,-1246)
        if not rectangle(forced)<=remaining:raise UserError('The actual private bed/job anchors need a complete larger Inn room, not a shifted or cropped point')
        out.append({'bounds_xz':list(forced),'storeys':3,'role':'native private-anchor inn core','roof':'offset halfhip'});remaining-=rectangle(forced)
    for n in range(10):
        box=largest_rectangle(remaining,max_width=15 if n%2 else 12,max_depth=25 if n%3 else 19,min_width=5 if n==0 else 3,min_depth=7 if n==0 else 4)
        if box is None:break
        out.append({'bounds_xz':list(box),'storeys':max(1,typology-(1 if n and n%2 else 0)),
            'role':'primary inhabited/trade mass' if not out else 'attached unequal furnished room/wing',
            'roof':('weathered hipped clay','low side-hung dark shingle','offset halfhip','cross-gabled slate')[n%4]})
        remaining-=rectangle(box)
    return out,remaining


def assign_pods(pods,buildings):
    slots=[]
    for b in buildings:
        for mi,m in enumerate(b['masses']):
            if b['id']=='lantern-harbor-inn' and mi==0:continue
            for floor in range(m['storeys']):slots.append({'building':b['id'],'mass_index':mi,'floor_index':floor,'box':m['bounds_xz'],'used':set()})
    result=[];held=[]
    for pod in sorted(pods,key=lambda p:(-len(p['records']),p['id'])):
        box=pod['source_support_bounds_xyz'];w,d=box[3]-box[0]+1,box[5]-box[2]+1;choice=None
        # Exact source capsule positions fit a real rectangular room in the new
        # irregular compound, with cardinal orientation unchanged initially.
        for slot in slots:
            b=slot['box']
            for x in range(b[0]+1,b[2]-w+1):
                for z in range(b[1]+1,b[3]-d+1):
                    footprint={(xx,zz) for xx in range(x,x+w) for zz in range(z,z+d)}
                    if footprint&slot['used']:continue
                    score=distance((x,z),(box[0],box[2]))
                    candidate=(score,slot['building'],slot['mass_index'],slot['floor_index'],x,z,slot,footprint)
                    if choice is None or candidate[:6]<choice[:6]:choice=candidate
        if choice is None:held.append({'pod_id':pod['id'],'reason':'No complete actual room capsule fit; do not erase source or invent smaller bounds'});continue
        _,bid,mi,floor,x,z,slot,footprint=choice;slot['used']|=footprint
        building=next(b for b in buildings if b['id']==bid)
        dy=building['masses'][mi]['floor_y']+4*floor-box[1];dx,dz=x-box[0],z-box[2]
        result.append({'pod_id':pod['id'],'destination_building':bid,'destination_mass':mi,'destination_floor':floor,
            'source_support_bounds_xyz':box,'translation_xyz':[dx,dy,dz],'rotation':'NONE',
            'destination_support_bounds_xyz':[box[0]+dx,box[1]+dy,box[2]+dz,box[3]+dx,box[4]+dy,box[5]+dz],
            'BE_point_transfers':[{'source':r['source_position'],'destination':[r['source_position'][0]+dx,r['source_position'][1]+dy,r['source_position'][2]+dz],
                'current_full_typed_NBT_sha256':r['current_full_typed_NBT_sha256']} for r in pod['records']],
            'execution':'FORBIDDEN pending exact fresh source/destination FULL/native class/slots/components/custody and native capture/restore receipt'})
    return result,held


def transaction_order(transfers,pods,current_rows):
    """Expose actual occupied-destination dependencies; never silently overwrite."""
    owner={}
    for pod in pods:
        for r in pod['records']:
            q=tuple(r['source_position'])
            if q in owner:raise UserError('One current BE is claimed by two room capsules')
            owner[q]=pod['id']
    moved={r['pod_id'] for r in transfers};graph={};details=[]
    for row in transfers:
        b=row['destination_support_bounds_xyz'];dependencies=set();self_overlap=[]
        for actual in current_rows:
            q=actual['position']
            if not all(b[i]<=q[i]<=b[i+3] for i in range(3)):continue
            source=owner.get(tuple(q))
            if source==row['pod_id']:self_overlap.append(q);continue
            if source not in moved:raise UserError('A new room overlaps a held/private/accepted current BE; redesign its destination')
            dependencies.add(source)
        graph[row['pod_id']]=dependencies
        details.append({'pod_id':row['pod_id'],'required_completed_move_ids':sorted(dependencies),
            'current_own_source_BE_intersections_require_atomic_native_capture_removal':self_overlap})
    remaining={k:set(v) for k,v in graph.items()};order=[]
    while remaining:
        ready=sorted(k for k,v in remaining.items() if not v)
        if not ready:raise UserError('The room transfer graph has an occupied-destination cycle; no automatic escrow or source deletion')
        order.extend(ready)
        for k in ready:remaining.pop(k)
        for v in remaining.values():v.difference_update(ready)
    return order,details


def render(record,samples,path):
    """Original technical site drawing; explicitly not native Minecraft imagery."""
    from PIL import Image,ImageDraw
    scale=6;x0,z0=1216,-1297;width=177*scale;height=178*scale
    im=Image.new('RGB',(width+410,height+95),'#15242c');d=ImageDraw.Draw(im)
    for (x,z),q in samples.items():
        c='#536c68' if q['kind']=='dry' else '#254759' if q['kind']=='water' else '#61706c'
        if q['authored_keepout']:c='#5e4939'
        xx=(x-x0)*scale;yy=(z-z0)*scale+50;d.rectangle((xx,yy,xx+scale-1,yy+scale-1),fill=c)
    colors=('#7d9194','#7b7669','#546861','#8b8272','#687577','#656c78','#8c8178','#6e7261')
    for bi,b in enumerate(record['buildings']):
        for mi,m in enumerate(b['masses']):
            a,z,c,zz=m['bounds_xz'];box=((a-x0)*scale,(z-z0)*scale+50,(c+1-x0)*scale-1,(zz+1-z0)*scale+49)
            d.rectangle(box,fill=colors[bi%len(colors)],outline='#c9be9b',width=1)
            if mi==0:d.text((box[0]+2,box[1]+2),str(bi+1),fill='#ffefbc')
    for s in record['street_network']:
        for x,z in s['all_walk_columns_xz']:
            xx=(x-x0)*scale;yy=(z-z0)*scale+50;d.rectangle((xx,yy,xx+scale-1,yy+scale-1),fill='#b7a78d')
    for x,z in record['private_human_bed_job_anchors_retained_in_place']:
        xx=(x-x0)*scale;yy=(z-z0)*scale+50;d.ellipse((xx-2,yy-2,xx+scale+1,yy+scale+1),outline='#ffff00',width=2)
    d.text((14,10),'EASTERN TORTUGA / COAST-FIRST RE-LAYOUT / SOURCE DESIGN ONLY',fill='white')
    for i,text in enumerate((f"BUILDING FLOOR: {record['building_floor_fraction_of_qualified_land']:.1%} OF KNOWN DRY LAND",
        'Actual floor rectangles; roofs and lanes excluded.',
        str(record['compounds'])+' irregular compounds / '+str(record['unequal_room_roof_masses'])+' unequal room masses',
        'Brown = accepted original district (preserved)','Tan = connected narrow crooked alleys',
        'Yellow = human bed/job retained in place','NO MOVE / CONSTRUCTION APPROVAL')):
        d.text((width+15,52+i*22),text,fill='#f3ddb0' if i==0 else '#c7d0cf')
    for i,b in enumerate(record['buildings']):d.text((width+15,219+i*18),f"{i+1:02d} {b['name']}",fill='#d8d9cf')
    d.text((10,height+62),'NORTH UP | original 1m coast; current06 saved typed custody; actual native transfer/art qualification still pending',fill='#d8d9cf')
    im.save(path,optimize=True)


def current_custody(home,path,sha):
    path=Path(path).resolve()
    if not path.is_relative_to(home/'staging') or path.name!='manifest.json':raise UserError('Explicit private current custody manifest required')
    manifest=checked(path,sha,2*MIB)
    if manifest.get('format')!='awft-current-eastern-urban-custody:1' or manifest.get('native_actions')!=0:raise UserError('Exact read-only current eastern custody required')
    receipt=read_json(home/'dashboard/settlement/backup-receipt.json')
    if receipt.get('verified') is not True or (manifest['checkpoint_id'],manifest['checkpoint_sha256'])!=(receipt['id'],receipt['sha256']):raise UserError('Current stopped checkpoint and typed custody must match')
    row=manifest['files']['room-capsules-SOURCE-ONLY.json'];capsules=checked(path.parent/'room-capsules-SOURCE-ONLY.json',row['sha256'],2*MIB)
    if (capsules['checkpoint_id'],capsules['checkpoint_sha256'])!=(manifest['checkpoint_id'],manifest['checkpoint_sha256']):raise UserError('Current room capsule identity differs')
    if len(capsules['all_current_BE_records'])!=manifest['current_saved_BE_count_in_eastern_study'] or len(capsules['pods'])!=manifest['room_capsules']:raise UserError('Current whole eastern BE/capsule set is incomplete')
    points=[tuple(r['position']) for r in capsules['all_current_BE_records']]
    if len(points)!=len(set(points)):raise UserError('Duplicate current BE custody position')
    return manifest,capsules


def prepare(home,custody_path,custody_sha):
    home=Path(home).resolve();reserve=guard(2*MIB,MAX_OUTPUT);started=time.monotonic()
    if home.parent!=Path('D:/A World for Two/staging/world-tests').resolve():raise UserError('Private source-only urban plan')
    fine=checked(home/FINE[0],FINE[1],8*MIB);north=checked(home/NORTH[0],NORTH[1],MIB)
    baseline=checked(home/LEDGER/'manifest.json',LEDGER_SHA,2*MIB)
    current,capsules=current_custody(home,custody_path,custody_sha)
    legacy=[r for r in baseline['houses'] if r['batch'] in ('rose-reach','compass-bend','eastern22')]
    if len(legacy)!=37:raise UserError('The full rejected eastern37 source/custody baseline is required')
    n=set(map(tuple,north['connected_columns_xz']));samples={(r['x'],r['z']):r for r in fine['samples']}
    land={p for p,row in samples.items() if p in n and row['kind']=='dry' and not row['authored_keepout']}
    private_anchor_cells={(1296,-1250),(1296,-1249),(1300,-1255)}
    pin_halo={(x+dx,z+dz) for x,z in private_anchor_cells for dx in range(-2,3) for dz in range(-2,3)}
    forced=rectangle((1293,-1258,1303,-1246))
    road_valid={p for p in land if patch(p)<=land and not patch(p)&(pin_halo|forced)}
    roads=set();street_records=[]
    for label,intents in STREETS:
        exact=[nearest(tuple(p),road_valid,8,label) for p in intents];nodes=[]
        for a,b in zip(exact,exact[1:]):
            route=astar(a,b,road_valid);nodes.extend(route if not nodes else route[1:])
        cells=set().union(*(patch(p) for p in nodes));roads|=cells
        street_records.append({'id':label,'width':'exact2x2 dry patch sweep; ordinary turns may be3m','author_intents':intents,
            'exact_dry_waypoints':[list(p) for p in exact],'path_nodes_xz':[list(p) for p in nodes],'all_walk_columns_xz':[list(p) for p in sorted(cells)]})
    # All roads must be one connected native-sized source graph.
    if roads:
        seen={next(iter(roads))};queue=deque(seen)
        while queue:
            for q in adjacent(queue.popleft()):
                if q in roads and q not in seen:seen.add(q);queue.append(q)
        if seen!=roads:raise UserError('The exact dry urban walking network is disconnected')
    available=land-roads;seed_records=[];used=set()
    for ident,name,intent,program,storeys in SEEDS:
        p=nearest(intent,available-used,8,ident);used.add(p)
        seed_records.append({'id':ident,'name':name,'design_seed_intent':list(intent),'exact_seed':list(p),'program':program,'maximum_storeys':storeys})
    if not forced<=available:raise UserError('Private-anchor Inn core conflicts with coast/route; revise the urban design rather than move the private bed')
    parcels,unreached=grow_parcels(land,roads,seed_records,{p:0 for p in forced})
    buildings=[];built=set();residual=set()
    for i,(seed,cells) in enumerate(zip(seed_records,parcels)):
        actual,left=masses(cells,seed['maximum_storeys'],pin=i==0);covered=set().union(*(rectangle(tuple(m['bounds_xz'])) for m in actual)) if actual else set()
        for mi,m in enumerate(actual):
            columns=rectangle(tuple(m['bounds_xz']));ys=[samples[p]['surface_y'] for p in columns]
            m['natural_original_ground_y_range']=[min(ys),max(ys)];m['floor_y']=max(ys)+1
            m['foundation']='Fit actual dry columns; no coast fill or whole-plot flatten; fresh current foundation proof REQUIRED'
            if i==0 and mi==0 and m['floor_y']!=64:raise UserError('The human-anchor Inn must preserve its real current floor')
        if covered&built:raise UserError('Two new urban compounds overlap')
        built|=covered;residual|=left
        frontage={p for p in covered if any(q in roads for q in adjacent(p))}
        buildings.append({**seed,'parcel_columns_xz':[list(p) for p in sorted(cells)],'masses':actual,'actual_building_floor_columns_xz':[list(p) for p in sorted(covered)],
            'frontage_to_real_street_columns_xz':[list(p) for p in sorted(frontage)],'residual_not_counted_as_building_floor':[list(p) for p in sorted(left)],
            'individual_furnishing_and_3D_roof_window_door_body_source':'REQUIRED next; these are explicit mass footprints, not accepted native buildings'})
    retained=[p for p in capsules['pods'] if p['source_house']=='rose-reach/compass']
    pods=[p for p in capsules['pods'] if p['source_house']!='rose-reach/compass']
    if len(retained)!=3:raise UserError('All three actual private-anchor Inn floors must remain at their current positions')
    transfers,held=assign_pods(pods,buildings)
    order,dependencies=transaction_order(transfers,capsules['pods'],capsules['all_current_BE_records'])
    record={'format':'awft-eastern-coast-first-urban-layout:1','created':time.time(),'source_sha256':digest(Path(__file__)),
        'status':'SOURCE LAYOUT ONLY; old grid has no parcel authority; no native movement/construction approval',
        'original_actual1m_terrain':{'path':FINE[0],'sha256':FINE[1],'checkpoint_id':fine['checkpoint_id']},'actual_north_partition_sha256':NORTH[1],
        'original52_727BE_custody_sha256':LEDGER_SHA,'historical_custody_is_not_current_native_authority':True,
        'current_stopped_checkpoint_id':current['checkpoint_id'],'current_stopped_checkpoint_sha256':current['checkpoint_sha256'],
        'current_custody_manifest_relative':Path(custody_path).resolve().relative_to(home).as_posix(),'current_custody_manifest_sha256':custody_sha,
        'current_saved_BE_count_in_eastern_study':current['current_saved_BE_count_in_eastern_study'],
        'actual_added_E321_E1808_included_in_current_custody':True,
        'requires_new_native_current_class_all_slots_all_components_before_execution':True,
        'private_human_bed_job_anchors_retained_in_place':[list(p) for p in sorted(private_anchor_cells)],
        'qualified_dry_north_land_columns':len(land),'actual_building_floor_columns':len(built),'building_floor_fraction_of_qualified_land':len(built)/len(land),
        'street_columns':len(roads),'street_fraction_of_qualified_land':len(roads)/len(land),'building_floor_excludes_roads_roof_canopies_and_unmodeled_residual':True,
        'compounds':len(buildings),'unequal_room_roof_masses':sum(len(b['masses']) for b in buildings),'buildings':buildings,'street_network':street_records,
        'unreached_land_columns':[list(p) for p in sorted(unreached)],'unmodeled_residual_columns':[list(p) for p in sorted(residual)],
        'source_stock_pods':pods,'exact_proposed_native_pod_transfers':transfers,'held_stock_pods':held,
        'ordered_native_transfer_ids':order,'native_transfer_dependencies':dependencies,
        'retained_in_place_private_anchor_Inn_room_capsules':retained,'current_unowned_or_private_BEs_held_in_place':capsules['held_current_BEs'],
        'native_mover_contract':['Capture current actual class/all slots/all components/full typed data before ANY source removal',
            'Use bounded original native StructureTemplate/custody only; no fake actor, arbitrary NBT or lost item components',
            'Every destination FULL/air/support/entity/unknown-ownership gate must pass before a move',
            'Journal durable capsule and exact source→destination positions before placement; inspect exact postmove native instances',
            'Preserve all values except native-proven coordinate relocation; unknown fields/class/ownership HOLD, never skipped',
            'Do not clear source until destination exact conserved content receipt; no automatic missing-object reconstruction',
            'Only then retire positively owned unchanged rejected shell/old grid paving; accepted originals/private anchors remain'],
        'coast_limits':'Original source study endsX1392/Z−1120; continuation beyond is UNKNOWN, not a claim of a complete natural shore. Fresh saved extension needed before any further land is occupied.',
        'native_actions':0,'world_writes':0,'construction_forbidden':True,'relocation_execution_forbidden':True,'reserve_guard':reserve}
    raw=(json.dumps(record,separators=(',',':'),ensure_ascii=False)+'\n').encode()
    if len(raw)>MAX_OUTPUT or time.monotonic()-started>120:raise UserError('Finite urban layout/source output exceeded')
    out=home/'staging'/('eastern-coast-urban-layout-'+str(time.time_ns()));out.mkdir();(out/'urban-plan-REVIEW-ONLY.json').open('xb').write(raw)
    render(record,samples,out/'coast-first-plan-SOURCE-ONLY.png')
    manifest={'format':'awft-eastern-urban-source-layout-bundle:1','checkpoint_id':current['checkpoint_id'],'checkpoint_sha256':current['checkpoint_sha256'],
        'source_sha256':digest(Path(__file__)),'current_custody_sha256':custody_sha,'native_actions':0,'construction_forbidden':True,
        'files':{p.name:{'sha256':digest(p),'bytes':p.stat().st_size} for p in out.iterdir()}}
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    return {'folder':str(out),'manifest_sha256':digest(out/'manifest.json'),'sha256':digest(out/'urban-plan-REVIEW-ONLY.json'),'building_floor_fraction':len(built)/len(land),'compounds':len(buildings),
        'masses':record['unequal_room_roof_masses'],'stock_pods':len(pods),'fit_transfers':len(transfers),'held_pods':len(held),'native_actions':0}


if __name__=='__main__':
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('--home',type=Path,required=True)
    a.add_argument('--custody-manifest',type=Path,required=True);a.add_argument('--custody-sha256',required=True)
    args=a.parse_args();print(json.dumps(prepare(args.home,args.custody_manifest,args.custody_sha256),indent=2))
