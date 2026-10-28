"""Original western-town v2 cable/stations. Private source plans, no world calls."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import time

from control_room.common import UserError, digest, read_json
from tools.artistic_materials import require_material_rule, require_outdoor_rule
from tools.artistic_south_extent import ExtentTerrain
from tools.artistic_south_forest import AIR, SOFT, GROUND, buffered_columns, exclusions
from tools.artistic_spawn_plaza import payload, state
from tools.artistic_whole_bank_forest import protection
from tools.artistic_zipline_catenary import frame, reader_budget, spatial_custody, swept_cells, validate_nodes
from tools.playtest import guard

MIB = 1024**2
ROUTE_ID = 'rosewater-cliff-western-town-v2'
CHECKPOINT = '20261028T010427Z-93f113'
CHECKPOINT_SHA = 'ec13e5399acd12d65290f70663b381d68103b45287e9421dedbc1ac62d86afac'
CURVES = 'staging/zipline-west-v2-native-five-1793150026298262400'
CURVES_SHA = '0926752bfa034c7599c47832df7d40932a26822f8cc9c9d42ade2cd3f8c783ea'
NODES = ((1160,168,-760),(1168,159,-784),(1144,152,-840),(1128,150,-848),
         (1120,147,-864),(1120,146,-880),(1112,142,-920),(1088,132,-968),
         (1064,125,-1008),(1048,116,-1064),(1056,108,-1112),(1048,100,-1176),
         (1048,91,-1232),(1064,86,-1248),(1100,72,-1256))
STOCK = (1101,65,-1257)  # Prospective EMPTY new barrel;14-chain tag is a later owned source revision.
HANG = 3.5
FUTURE_BRIDGE = 'staging/artistic-bridge-topside-20261028T0128Z/future-reservation-ONLY.json'
FUTURE_BRIDGE_SHA = 'd6d6963d437d89824b012274b06f6b36600c82ca4acc1fe713e0ab4a3a3a657c'


def pavilion(registry, terrain, center, protected, label, *, anchor_xz=None, floor_y=None):
    """Compact asymmetric4x5 open pavilion with a South boarding balcony/flight notch.

    A real lower deck and stepped catch landing remain below the rider. The
    side ladder reaches the rear balcony; the departing central flight stays
    open instead of pushing a descending rider through a front deck.
    """
    cx, cz = center
    ax, az = anchor_xz or center
    if az!=cz or abs(ax-cx)>1:
        raise UserError('Only one measured sideways shelter offset is admitted; knots remain exact')
    columns = []
    for dx in range(-1,3):
        for dz in range(-2,3):
            if (cx+dx,cz+dz) in protected:
                raise UserError('Preserve an existing architectural/crown exclusion at station')
            row = terrain.column(cx+dx,cz+dz)
            if row['kind'] != 'dry' or row['state'].split('[')[0] not in GROUND:
                raise UserError('Every station footing needs actual dry natural ground')
            columns.append(row)
    floor = max(row['surface_y'] for row in columns)+1 if floor_y is None else floor_y
    if max(row['surface_y'] for row in columns)>floor or floor-min(row['surface_y'] for row in columns)>4:
        raise UserError('Station needs a modest rooted natural terrace, not a terrain platform')
    roots = {(row['x'],row['surface_y'],row['z']):row['state'] for row in columns}
    blocks = {}

    def put(dx,dy,dz,name,**props):
        buttress = label=='cliff' and dx==3 and dz==-2
        if not (-1<=dx<=2 or buttress) or not -2<=dz<=2 or not -4<=dy<=12:
            raise UserError('Station escaped its compact measured4x5 envelope')
        blocks[cx+dx,floor+dy,cz+dz] = state(registry,name,**props)

    for dx in range(-1,3):
        for dz in range(-2,3):
            # Sparse construction preserves existing canopy in unused open
            # volume. Required flight/entry bodies are admitted separately.
            name = 'chipped:boxed_spruce_planks' if dx==0 else 'minecraft:dark_oak_planks' if dz==0 else 'minecraft:spruce_planks'
            # An actual soil/rock cell already at the deck's block height has
            # the same walking top as our boards. Retain that exact cell;
            # a small natural contour is not permission to flatten the site.
            if (cx+dx,floor,cz+dz) not in roots:
                put(dx,0,dz,name)
            if dz in (1,2):
                put(dx,4,dz,'chipped:boxed_dark_oak_planks' if dx==0 else 'minecraft:dark_oak_planks')
    put(ax-cx,0,2,'minecraft:spruce_stairs',facing='north',half='bottom',shape='straight',waterlogged=False)
    for dx in (-1,2):
        for dz in (-2,2):
            # The front-right cliff bay is a real cantilever between the
            # continuous North crossbeam and East chord, rooted through the
            # other three posts. A fourth post would enter the departing line.
            if label=='cliff' and (dx,dz)==(2,-2):continue
            px=dx
            ground = next(row['surface_y'] for row in columns if row['x']==cx+dx and row['z']==cz+dz)
            for y in range(ground+1,floor):
                put(px,y-floor,dz,'minecraft:stone_bricks' if y%2 else 'minecraft:andesite')
            for dy in range(1,8):
                put(px,dy,dz,'chipped:carved_stripped_spruce_log' if dy==4 else 'minecraft:stripped_spruce_log',axis='y')
            put(px,8,dz,'minecraft:dark_oak_stairs',facing='east' if dx<0 else 'west',half='top',shape='straight',waterlogged=False)
    # The balcony is South of the real knot. A three-wide notch and two low
    # catch steps replace the old raised front deck; no collision is bypassed.
    for step,dz in enumerate(range(-2,2),1):
        for dy in range(1,step):
            put(0,dy,dz,'minecraft:dark_oak_planks')
        put(0,step,dz,'minecraft:spruce_stairs',facing='south',half='bottom',shape='straight',waterlogged=False)
    for dx in (0,1):
        put(dx,5,2,'minecraft:spruce_fence',north=False,south=False,east=dx==0,west=dx==1,waterlogged=False)
    for dy in (1,2,3):
        put(2,dy,1,'chipped:reinforced_stripped_spruce_log',axis='y')
    for dy in range(1,5):
        put(1,dy,1,'minecraft:ladder',facing='west',waterlogged=False)
    put(1,5,1,'minecraft:spruce_trapdoor',facing='west',half='bottom',open=True,powered=False,waterlogged=False)
    # Human-scale equipment stories below the flight and clear of the entry.
    put(-1,1,0,'handcrafted:dark_oak_shelf',facing='west',shape='single',type='2')
    put(-1,2,0,'handcrafted:stackable_book',facing='west',books=2,seed=7)
    put(-1,3,-1,'mcwwindows:dark_oak_louvered_shutter',facing='south',hinge='left',open=True)
    put(1,1,-1,'minecraft:barrel',facing='south',open=False)
    put(1,2,-1,'handcrafted:wood_cup',facing='south',pieces=1,waterlogged=False)
    put(2,1,0,'minecraft:spruce_stairs',facing='west',half='bottom',shape='straight',waterlogged=False)
    put(-1,2,-1,'mcwlights:covered_wall_lantern',facing='south')
    if label=='cliff':
        put(1,2,2,'mcwlights:covered_wall_lantern',facing='west')
    else:
        put(2,2,-1,'mcwlights:covered_wall_lantern',facing='south')
    # Roof framing carries the fence knot from above. Actual staggered coffers
    # sit above the rider's buffered head, not inside the flight notch.
    for dz in (-2,0,2):
        for dx in range(-1,3):
            put(dx,9,dz,'minecraft:dark_oak_log',axis='x')
    for dx in (-1,2):
        for dz in range(-2,3):
            put(dx,9,dz,'minecraft:stripped_dark_oak_log',axis='z')
    for dz in (-1,1):
        for dx in (0,1):
            put(dx,9,dz,'minecraft:dark_oak_trapdoor',facing='north',half='top',open=False,powered=False,waterlogged=False)
    for dz in range(-2,3):
        put(0,11,dz,'minecraft:dark_oak_log',axis='z')
        put(-1,10,dz,'minecraft:dark_oak_planks')
        put(-1,11,dz,'minecraft:dark_oak_stairs',facing='east',half='bottom',shape='straight',waterlogged=False)
        put(1,11,dz,'minecraft:dark_oak_stairs',facing='west',half='bottom',shape='straight',waterlogged=False)
        put(2,10,dz,'minecraft:dark_oak_stairs',facing='west',half='bottom',shape='straight',waterlogged=False)
        put(0,12,dz,'minecraft:dark_oak_slab',type='bottom',waterlogged=False)
    for dz in (-2,0,2):
        put(0,10,dz,'minecraft:dark_oak_log',axis='y')
    put(ax-cx,8,0,'minecraft:spruce_fence',north=False,south=False,east=False,west=False,waterlogged=False)
    # Exact unoccupied walking/boarding volumes, without clearing a whole box.
    for dx,dz in ((0,2),(1,2)):
        for dy in range(1,4):
            if (cx+dx,floor+dy,cz+dz) not in blocks:
                put(dx,dy,dz,'minecraft:air')
    for dx,dz in ((0,1),):
        for dy in range(5,8):
            if (cx+dx,floor+dy,cz+dz) not in blocks:
                put(dx,dy,dz,'minecraft:air')
    before = dict(roots)
    for pos in blocks:
        actual = terrain.state(*pos)
        if actual is None or actual.split('[')[0] not in AIR|SOFT or pos in terrain.entities:
            raise UserError('Retain every saved station object/tree/BE: '+str((pos,actual)))
        before[pos] = actual
    threshold = {}; entry_shoes=[]
    for dx in (-1,0,1):
        row = terrain.column(ax+dx,cz+3)
        if row['kind']!='dry' or not floor-2<=row['surface_y']<=floor-1 or row['state'].split('[')[0] not in GROUND:
            raise UserError('Actual dry entry needs at most one rooted shoe, never a terrain platform')
        root=ax+dx,row['surface_y'],cz+3
        roots[root]=row['state'];threshold[root]=row['state']
        if row['surface_y']==floor-2:
            shoe=ax+dx,floor-1,cz+3;actual=terrain.state(*shoe)
            if actual is None or actual.split('[')[0] not in AIR|SOFT or shoe in terrain.entities:
                raise UserError('Retain a saved entry-shoe obstruction')
            blocks[shoe]=state(registry,'minecraft:spruce_planks');before[shoe]=actual
            entry_shoes.append(list(shoe))
        for dy in range(3):
            q = ax+dx,floor+dy,cz+3
            actual = terrain.state(*q)
            if actual is None or actual.split('[')[0] not in AIR|SOFT or q in terrain.entities:
                raise UserError('Retain a threshold obstruction; no fake safe arrival')
            threshold[q] = actual
    check = require_material_rule(blocks,label+' complete4x5 pavilion')
    support_check=station_connections(blocks,roots,label)
    roles = {'label':label,'footprint':[cx-1,cz-2,cx+2,cz+2],
        'floor_block_y':floor,'raised_South_deck_block_y':floor+4,
        'north_anchor_block':[ax,floor+8,cz],'face':'north','hang_offset':HANG,
        'shelter_center_xz':[cx,cz],'retained_canopy_sideways_offset':cx-ax,
        'cliff_front_bay':'supported three-post cantilever; no rider-obstructing front-right post' if label=='cliff' else 'four rooted corner posts',
        'exterior_arrival_feet':[ax+.5,floor,cz+3.5],
        'actual_saved_threshold':[[*pos,value] for pos,value in sorted(threshold.items())],
        'new_single_block_rooted_entry_shoes':entry_shoes,
        'side_ladder':[[cx+1,floor+dy,cz+1] for dy in range(1,5)],
        'new_barrel_empty_source':[cx+1,floor+1,cz-1],
        'native_boarding_walking_and_fall_safety':'PENDING actual player test',
        'material_check':check,'source_support_connectivity':support_check}
    return blocks,before,roots,threshold,roles


def occupied_cells(blocks):
    """Conservative block-space source guard, distinct from native Level shapes.

    Native vanilla fences/walls extend above their addressed unit cell. Include
    that extra cell instead of pretending their collision height is one metre.
    """
    cells=set()
    for pos,value in blocks.items():
        name=value.split('[')[0]
        if name in AIR:continue
        cells.add(pos)
        if name.startswith('minecraft:') and name.endswith(('_fence','_wall')):
            cells.add((pos[0],pos[1]+1,pos[2]))
    return cells


def station_connections(blocks,roots,label):
    """Actual source connections, not a structural engineering/Level claim."""
    structural={q for q,v in blocks.items() if v.split('[')[0].endswith(('_log','_planks','_stairs','_slab')) or v.split('[')[0]in('minecraft:stone_bricks','minecraft:andesite')}
    reached=set(roots);pending=list(roots)
    while pending:
        x,y,z=pending.pop()
        for other in ((x-1,y,z),(x+1,y,z),(x,y-1,z),(x,y+1,z),(x,y,z-1),(x,y,z+1)):
            if other in structural and other not in reached:reached.add(other);pending.append(other)
    if structural-reached:raise UserError('A source roof/frame member is not joined to retained ground: '+str(sorted(structural-reached)[:5]))
    for pos,value in blocks.items():
        name=value.split('[')[0];x,y,z=pos
        if name=='minecraft:ladder':
            support=blocks.get((x+1,y,z),'minecraft:air').split('[')[0]
            if not(support.endswith(('_log','_planks'))):raise UserError('Actual West ladder needs an East structural backing')
        if name=='mcwlights:covered_wall_lantern':
            support=(x+1,y,z)if'facing=west'in value else(x,y,z-1)
            if support not in structural:raise UserError('A wall lantern needs a real authored structural attachment')
    return {'label':label,'all_structural_members_connected_to_actual_retained_roots':True,
            'ridge_has_actual_ridgebeam_and_kingposts':True,'actual_ladder_and_lamp_supports':True,
            'native_support_survival_shapes_and_engineering_acceptance':False}


def prepare(home,checkpoint_id=CHECKPOINT,checkpoint_sha=CHECKPOINT_SHA):
    home = Path(home).resolve()
    if not home.is_relative_to(Path(r'D:/A World for Two/staging/world-tests')):
        raise UserError('Owned private saved-stage only')
    reserve = guard(MIB,16*MIB); budgets=[reader_budget()]
    receipt = read_json(home/'dashboard/settlement/backup-receipt.json')
    if receipt.get('verified') is not True or (receipt['id'],receipt['sha256'])!=(checkpoint_id,checkpoint_sha):
        raise UserError('Exact current stopped checkpoint required for westernv2')
    curves_dir = home/CURVES
    if digest(curves_dir/'manifest.json')!=CURVES_SHA:
        raise UserError('Exact native v2 curve provenance required')
    origin = read_json(curves_dir/'manifest.json')
    if origin['nodes']!=[list(q) for q in NODES] or origin['hang_offset_proposed']!=HANG:
        raise UserError('Native curve source geometry differs')
    for name,row in origin['files'].items():
        p=curves_dir/name
        if p.stat().st_size!=row['bytes'] or digest(p)!=row['sha256']:
            raise UserError('Exact v2 native curve member changed')
    curves = read_json(curves_dir/'all-native-curves.json')['segments']
    if len(curves)!=14:raise UserError('Exactly fourteen native v2 spans required')
    validate_nodes(NODES)
    registry = read_json(home/'dashboard/settlement/registry.json')
    protected,custody = protection(home,registry)
    extra,extra_custody=exclusions([('FUTURE UNPLACED bridge topside/tenwide walk',home/FUTURE_BRIDGE,FUTURE_BRIDGE_SHA)],registry)
    protected.update(extra);custody.extend(extra_custody)
    terrain = ExtentTerrain(home,receipt,registry)
    body=set(); body_rows=[]; geometry={}; preimages={}; roots={}; roles={}; failure=None
    try:
        for i,row in enumerate(curves):
            budgets.append(reader_budget()); cells=swept_cells(row['points'],HANG); body.update(cells)
            blocked=[]; unknown=[]
            for q in sorted(cells):
                actual=terrain.state(*q)
                if actual is None:unknown.append(list(q))
                elif actual.split('[')[0] not in AIR:blocked.append({'position':list(q),'state':actual})
            body_rows.append({'index':i,'length':row['length'],'cells':len(cells),'blockers':blocked,'unknown':unknown})
        if any(row['blockers'] or row['unknown'] for row in body_rows):
            raise UserError('V2 actual saved body is obstructed or unknown; no physical clearance authority')
        for i,block in enumerate(NODES[1:-1],1):
            budgets.append(reader_budget())
            cells,kept,details=frame(registry,terrain,block,body,protected,'Westernv2 portal '+str(i))
            geometry['portal-'+str(i)]=cells
            preimages['portal-'+str(i)]={q:terrain.state(*q) for q in cells}|kept
            roots.update(kept); roles['portal-'+str(i)]=details
        for name,center,node in (('cliff',(1160,-760),NODES[0]),('western-town',(1100,-1256),NODES[-1])):
            cells,before,kept,threshold,details=pavilion(registry,terrain,center,protected,name,anchor_xz=(node[0],node[2]),floor_y=node[1]-8)
            if details['north_anchor_block']!=list(node):raise UserError('Measured station anchor does not match actual v2 native curve')
            geometry[name]=cells;preimages[name]=before|threshold;roots.update(kept);roles[name]=details
        approach_path=home/'staging/authored-cliff-access-1793145392670034300/access-DELTA.json'
        if digest(approach_path)!='1f33c7527c74c83fd579c36f9e4b8382c45cacaefeecc622c6bf5799ca7b649e':raise UserError('Exact unplaced authored cliff approach source required')
        approach=read_json(approach_path)
        shared=(1160,159,-757)
        expected=[approach['palette'][row[3]]for row in approach['blocks']if tuple(row[:3])==shared]
        if expected!=[geometry['cliff'].get(shared)]:raise UserError('Cliff station entry must agree exactly with the authored access join')
        roles['cliff']['shared_unplaced_approach_source']={'sha256':digest(approach_path),'join_block':list(shared),'same_desired_state':expected[0],'native_approach_walking_acceptance':False,'placement_order':'Combine shared join once or rebind preimage after first owned placement; no blind replay'}
        all_blocks={}
        for name,cells in geometry.items():
            if any(q in all_blocks and all_blocks[q]!=v for q,v in cells.items()):
                raise UserError('Physical v2 components overlap with different states')
            all_blocks.update(cells)
        occupied=occupied_cells(all_blocks)
        intersections=sorted(body&occupied)
        if intersections:raise UserError('Actual authored v2 geometry intersects native rider body: '+str(intersections[:12]))
        navigation=spatial_custody(body|occupied)
        outdoor=require_outdoor_rule(all_blocks,'All authored westernv2 stations and portal work')
        actual_body={q:terrain.state(*q) for q in body}
        cameras=[]
        for label,poses,target in (
            ('western-town-facade',((1105.5,67,-1249.5),(1093.5,68,-1250.5)),(1100.5,69,-1256)),
            ('cliff-side',((1166.5,174,-754.5),(1153.5,174,-755.5)),(1160.5,166,-760)),
            ('south-bank-rigging',((1038.5,91,-1172.5),(1038.5,98,-1166.5)),(1048.5,90,-1176)),
            ('cliff-boarding',((1160.5,165,-758.5),),(1160.5,168.9,-759.75))):
            for feet in poses:
                sample={(x,y,z) for x in range(math.floor(feet[0]-.3),math.ceil(feet[0]+.3))
                        for y in range(math.floor(feet[1]),math.ceil(feet[1]+1.8))
                        for z in range(math.floor(feet[2]-.3),math.ceil(feet[2]+.3))}
                if all(q not in occupied and terrain.state(*q) is not None and terrain.state(*q).split('[')[0] in AIR for q in sample):
                    cameras.append({'name':label,'feet':list(feet),'target':list(target),'source_saved_and_planned_body_AIR':True,'native_camera_or_walk_acceptance':False});break
        source_inputs=terrain.snapshot.sources.copy()
    except UserError as error:
        failure=str(error); source_inputs=terrain.snapshot.sources.copy()
    finally:
        terrain.close()
    out=home/'staging'/('zipline-west-v2-source-'+str(time.time_ns()));out.mkdir()
    proof={'format':'awft-western-v2-native-curve-physical-source:1','route_id':ROUTE_ID,
        'checkpoint_id':checkpoint_id,'checkpoint_sha256':checkpoint_sha,'nodes':[list(q) for q in NODES],
        'faces':['north']*15,'slack':16,'hang_offset':HANG,
        'all_saved_AIR_clear':len(body_rows)==14 and not any(r['blockers'] or r['unknown'] for r in body_rows),
        'physical_frames_clear':failure is None,'native_ride_acceptance':False,
        'clearance_model':'Exact binary catenary and swept player body against actual saved FULL block cells and authored block occupancy, including2highvanilla fences/walls. Actual native Level/mod shapes remain unproved.',
        'body_segments':body_rows,'physical_failure':failure,'native_curve_manifest_sha256':CURVES_SHA,
        'native_actions':0,'world_writes':0,'source_only':True,'sources':source_inputs}
    raw={'physical-frame-source.json':(json.dumps(proof,separators=(',',':'))+'\n').encode()}
    if failure is None:
        canonical=(json.dumps([[*q,v] for q,v in sorted(all_blocks.items())],separators=(',',':'))+'\n').encode()
        geometry_sha=hashlib.sha256(canonical).hexdigest()
        proof['source_geometry_sha256']=geometry_sha
        raw['physical-frame-source.json']=(json.dumps(proof,separators=(',',':'))+'\n').encode()
        for name,cells in geometry.items():
            doc=payload(registry,checkpoint_sha,cells,'PROPOSAL ONLY '+ROUTE_ID+' '+name)
            doc['construction_forbidden']=True
            raw[name+'-DELTA.json']=(json.dumps(doc,separators=(',',':'))+'\n').encode()
            raw[name+'-BEFORE-VERIFY-ONLY.json']=(json.dumps(payload(registry,checkpoint_sha,preimages[name],
                'VERIFY ONLY actual saved '+ROUTE_ID+' '+name,before=True),separators=(',',':'))+'\n').encode()
        for name,cells in (('all-retained-roots',roots),('flight-reservation',actual_body)):
            raw[name+'-VERIFY-ONLY.json']=(json.dumps(payload(registry,checkpoint_sha,cells,
                'VERIFY/RESERVATION ONLY '+ROUTE_ID+' '+name,before=True),separators=(',',':'))+'\n').encode()
        station_mask={q:'minecraft:air' for name in ('cliff','western-town') for q in geometry[name]}
        for name in ('cliff','western-town'):
            station_mask.update({tuple(row[:3]):'minecraft:air' for row in roles[name]['actual_saved_threshold']})
        raw['station-reservation-ONLY.json']=(json.dumps(payload(registry,checkpoint_sha,station_mask,
            'RESERVATION ONLY v2 full pavilions/entry bodies',before=True),separators=(',',':'))+'\n').encode()
        wire_work=set()
        for row in curves:
            points=row['points']
            for a,b in zip(points,points[1:]):
                for x in range(math.floor(min(a[0],b[0])-.55),math.ceil(max(a[0],b[0])+.55)):
                    for y in range(math.floor(min(a[1],b[1])-.5),math.ceil(max(a[1],b[1])+.5)):
                        for z in range(math.floor(min(a[2],b[2])-.55),math.ceil(max(a[2],b[2])+.55)):
                            wire_work.add((x,y,z))
        planned_approach={(row[0],row[2]) for row in approach['blocks']}
        construction=body|wire_work|all_blocks.keys()|station_mask.keys()
        reserved_columns=buffered_columns({(x,z) for x,y,z in construction}|planned_approach,5)
        reservation={'format':'awft-prospective-growth-exclusion:1','route_id':ROUTE_ID,
            'checkpoint_id':checkpoint_id,'checkpoint_sha256':checkpoint_sha,
            'source_geometry_sha256':geometry_sha,'native_curve_manifest_sha256':CURVES_SHA,
            'supersedes_unbuilt_v1_reservation_sha256':'35838845b4872bb8be59034782a73e56b299a7e6d02f1015af51aa7d803208bf',
            'native_plan':False,'native_actions':0,'growth_authority':False,
            'all_growth_excluded_columns_xz':[list(q) for q in sorted(reserved_columns)],
            'whole_crown_extra_skirt_metres':5,
            'construction_reserved_xyz':[list(q) for q in sorted(construction)],
            'wire_work_reservation_is_not_an_observed_AIR_or_rendered_line_claim':True,
            'retained_approach_source_sha256':digest(approach_path),
            'warning':'Prospective custody only; includes intentional native knot/headstock attachment cells. Actual ride, native shapes and camera approval remain pending.'}
        raw['future-v2-growth-and-construction-reservation.json']=(json.dumps(reservation,separators=(',',':'))+'\n').encode()
        native_mask=payload(registry,checkpoint_sha,{q:'minecraft:air' for q in construction},
            'RESERVATION ONLY v2 all architecture/flight/cable work; states are NOT observed AIR',before=True)
        native_mask.update(reservation_only=True,not_an_observed_AIR_plan=True)
        raw['all-v2-RESERVATION-ONLY.json']=(json.dumps(native_mask,separators=(',',':'))+'\n').encode()
        report={'route_id':ROUTE_ID,'nodes':[list(q) for q in NODES],'faces':['north']*15,
            'slack':16,'hang_offset_required':HANG,'stock_prospective_empty_block':list(STOCK),
            'stock_chain_items_created':0,'future_real_chain_cost':14,
            'roles':roles,'source_navigation':navigation,'outdoor_material_check':outdoor,
            'spans_over_48m':[{'index':i,'length':row['length']} for i,row in enumerate(curves) if row['length']>48],
            'maximum_engine_span':80,'real_bidirectional_restart_loading_and_camera_acceptance':False,
            'source_geometry_sha256':geometry_sha,
            'component_geometry_sha256':{name:hashlib.sha256((json.dumps([[*q,v] for q,v in sorted(cells.items())],separators=(',',':'))+'\n').encode()).hexdigest() for name,cells in geometry.items()},
            'cameras':cameras,'first_prototype_before_propagation':True}
        raw['source-roles-and-config.json']=(json.dumps(report,indent=2)+'\n').encode()
    manifest={'format':'awft-western-v2-private-proposal-manifest:1','route_id':ROUTE_ID,
        'checkpoint_id':checkpoint_id,'checkpoint_sha256':checkpoint_sha,'source_sha256':digest(Path(__file__)),
        'frame_kernel_sha256':digest(Path('tools/artistic_zipline_catenary.py')),
        'physical_pass':failure is None,'failure':failure,'targets':sum(len(x) for x in geometry.values()),
        'protected_architecture_and_future_R5':custody,'reserve':reserve,
        'owned_reader_observed_max_rss_bytes':max(row['owned_reader_rss_bytes'] for row in budgets),
        'RAM_and_storage_checks_are_monitoring_not_systemwide_quotas':True,
        'native_actions':0,'world_writes':0,'new_JVMs':0,
        'files':{name:{'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)} for name,data in raw.items()}}
    raw['manifest.json']=(json.dumps(manifest,indent=2)+'\n').encode()
    if sum(map(len,raw.values()))>16*MIB:raise UserError('Finite16MiB westernv2 output exceeded')
    for name,data in raw.items():(out/name).write_bytes(data)
    return {'directory':str(out),'manifest_sha256':digest(out/'manifest.json'),
        'physical_pass':failure is None,'failure':failure,'body_cells':len(body),
        'source_geometry_targets':manifest['targets']}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--home',type=Path,required=True)
    p.add_argument('--checkpoint-id',default=CHECKPOINT);p.add_argument('--checkpoint-sha256',default=CHECKPOINT_SHA)
    a=p.parse_args();print(json.dumps(prepare(a.home,a.checkpoint_id,a.checkpoint_sha256),indent=2))
