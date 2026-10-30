"""Additive Keel composition for all six conserved rooms /35 native BE points.

The original Keel and frozen38 source sets remain untouched. Source only.
"""
from __future__ import annotations
import argparse,json,time
from collections import deque
from copy import deepcopy
from pathlib import Path
from control_room.common import UserError,digest,read_json,utcnow
from tools import artistic_eastern_compound_sprint as e
from tools.artistic_north_bank_east import NorthTerrain,preservation,native_payload
from tools.artistic_create_substrate import verify_zinc_factory
from tools.artistic_fisherman_interior import snbt
from tools.playtest import guard

MIB=1024**2
ENGINE_SHA='029ff89e0c6af6e1e07fb7fc0a439e634b6805b1966056f31e3a5c266a4fcdb5'


def reachable(p):
    graph=e.walking_graph(p);roots=set()
    for entry in p.entries:
        q=tuple(entry['local']);dx,dz=e.VEC[entry['outward']];inside=q[0]-dx,q[1],q[2]-dz
        if inside in graph:roots.add(inside)
    seen=set(roots);todo=deque(roots)
    while todo:
        for q in graph[todo.popleft()]:
            if q not in seen:seen.add(q);todo.append(q)
    return graph,seen


def additional_workshop_entries(p,street):
    """Actual separate outside doors reach stock bays divided by real furniture."""
    for attempt in range(8):
        graph,seen=reachable(p);goals=[]
        for point in p.original_BE_points|p.original_functional_nonBE_points:
            mass=next(i for i,c in enumerate(p.mass_fields)if(point[0],point[2])in c)
            feet=1+max((v for v in p.floor_levels[mass]if v<point[1]),default=p.mass_floors[mass])
            if any(q[1]==feet and abs(q[0]-point[0])+abs(q[2]-point[2])<=3 for q in seen):continue
            if feet!=p.mass_floors[mass]+1:raise UserError('A conserved upper stock bay still requires a real independent vertical route')
            goals.append((point,mass,feet))
        if not goals:return
        point,mass,feet=sorted(goals)[0];candidates=[];box=p.local_box(p.spec['masses'][mass]);x0,z0,x1,z1=box
        for face,points in(('north',[(x,z0)for x in range(x0+1,x1)]),('south',[(x,z1)for x in range(x0+1,x1)]),('west',[(x0,z)for z in range(z0+1,z1)]),('east',[(x1,z)for z in range(z0+1,z1)])):
            dx,dz=e.VEC[face]
            for x,z in points:
                inner=x-dx,feet,z-dz;outside=x+dx,feet-1,z+dz
                if inner not in graph or inner in seen or not p.permitted(outside)or(outside[0],outside[2])in p.footprint:continue
                door={(x,feet,z),(x,feet+1,z)}
                if any(q in p.fixed or q in p.body or q in p.backing_points or e.key(p.blocks.get(q,'minecraft:air')).startswith('mcwwindows:')for q in door):continue
                component={inner};todo=deque([inner])
                while todo:
                    for q in graph[todo.popleft()]:
                        if q not in component:component.add(q);todo.append(q)
                if not any(q[1]==feet and abs(q[0]-point[0])+abs(q[2]-point[2])<=3 for q in component):continue
                wx,wz=outside[0]+p.origin[0],outside[2]+p.origin[2];distance=min(abs(wx-a)+abs(wz-b)for a,b in street)
                candidates.append((distance,x,z,face,inner,outside))
        if not candidates:raise UserError('No genuinely clear exterior doorway reaches the conserved separated stock bay: '+str(p.world(point)))
        distance,x,z,face,inner,outside=min(candidates);p.door(x,feet,z,face);p.reserve('Separate conserved workroom exterior entry',[inner])
        reverse={'north':'south','south':'north','east':'west','west':'east'}[face]
        p.put(*outside,'minecraft:dark_oak_stairs',facing=reverse,half='bottom',shape='straight',waterlogged=False,role='actual separate workshop half-step; no stock bay wall/furniture removed')
        dx,dz=e.VEC[face];tx,tz=(1,0)if dz else(0,1)
        for n in(-1,0,1):
            q=x+n*tx,feet+2,z+n*tz
            if q not in p.fixed and q not in p.body:p.beam(*q,'x'if tx else'z',role='expressed real timber head over an independently usable workroom door')
        p.entries[-1].update(mass_ground_floor=feet-1,outer_step=list(outside),real_street_distance_source_only=distance,reason='Conserved furniture divides stock rooms; separate real doorway instead of deleting contents')
    raise UserError('Finite eight new workroom doors exhausted without complete conserved access')


def rear_oriel(p):
    """One genuine two-block upper projection with openable room access."""
    mass=p.spec['masses'][0];x0,z0,x1,z1=p.local_box(mass);floor=p.floor_levels[0][1];choice=None
    for face in('south','east','west','north'):
        dx,dz=e.VEC[face];tx,tz=(1,0)if dz else(0,1);lo,hi=(x0,x1)if dz else(z0,z1)
        for middle in sorted(range(lo+2,hi-2),key=lambda x:(abs(x-(lo+hi)/2),x)):
            anchor=(middle,z1 if dz>0 else z0)if dz else(x1 if dx>0 else x0,middle)
            at=lambda n,d:(anchor[0]+n*tx+d*dx,anchor[1]+n*tz+d*dz)
            columns=[at(n,d)for n in range(-1,3)for d in(1,2)]
            targets={(x,y,z)for x,z in columns for y in range(floor,floor+4)}|{(at(n,0)[0],y,at(n,0)[1])for n in(0,1)for y in(floor+1,floor+2)}
            backs=[(at(n,0)[0],floor-1,at(n,0)[1])for n in(-1,2)]
            if any(e.key(p.blocks.get(q,'minecraft:air'))in e.VOID for q in backs):continue
            if not any(not p.permitted(q)or q in p.fixed or q in p.backing_points for q in targets):choice=face,at,columns;break
        if choice:break
    if choice is None:raise UserError('No rear oriel fits without altering a conserved fixture backing or model boundary')
    face,at,columns=choice
    floorwood='minecraft:dark_oak_planks'if face in('north','south')else'minecraft:spruce_planks'
    for x,z in columns:p.put(x,floor,z,floorwood,role='actual upper oriel floor projecting from the retained room floor')
    for n in(-1,2):
        for d in(1,2):
            x,z=at(n,d)
            for y in(floor+1,floor+2):p.beam(x,y,z,'y',role='real vertical oriel corner frame')
    for n in(0,1):
        for y in(floor+1,floor+2):
            x,z=at(n,0);p.put(x,y,z,'minecraft:air',role='actual two-high opening from upper room into the oriel')
            x,z=at(n,1);p.put(x,y,z,'minecraft:air',role='literal accessible upper oriel pocket')
            x,z=at(n,2);p.put(x,y,z,'mcwwindows:dark_oak_four_window',facing=face,windowstate='locked',role='real deep rear oriel glazing')
    for x,z in columns:p.slab(x,floor+3,z,'dark_oak',role='layered supported upper oriel cornice')
    for n in(-1,2):
        x,z=at(n,1);back=at(n,0);p.put(x,floor-1,z,'mythrais:curved_corbel_dark_oak',facing=face,shape=0,role='actual carved corbel supporting the upper bay floor');p.supports.append(((x,floor-1,z),(back[0],floor-1,back[1])))
    p.reserve('Literal upper room to projecting rear oriel',[(at(n,d)[0],floor+1,at(n,d)[1])for n in(0,1)for d in(0,1)])
    p.details.append({'kind':'genuine accessible two-block rear oriel','new_ground_columns':0,'floor':floor,'outward':face,'local_columns':[list(q)for q in columns]})


def build(registry,spec,stock,others,street,index):
    p=e.Compound(registry,spec,stock,others,index)
    for mass in spec['masses']:
        box=p.local_box(mass);cells=e.rectangle(*box);base=mass['floor_y']-p.origin[1];levels=[base+k*4 for k in range(mass['storeys'])];top=levels[-1]+4
        p.mass_fields.append(cells);p.mass_floors.append(base);p.floor_levels.append(levels);p.top_levels.append(top);p.clear_new_room(cells,base,top-base)
        for level in levels+[top]:p.floor(cells,level)
        for low,high in zip(levels,levels[1:]+[top]):p.walls(cells,low+1,high,e.PANELS[(index+len(p.mass_fields)-1)%len(e.PANELS)])
        for level in levels+[top]:p.ring(cells,level)
        for x,z in e.boundary(cells):p.put(x,base-1,z,'minecraft:stone_bricks'if(x-1,z)in cells and(x+1,z)in cells else'minecraft:cobbled_deepslate',role='actual narrow original approved-mass plinth')
    e.fixture_backings(p);e.join_masses(p)
    for i,mass in enumerate(spec['masses']):
        box=p.local_box(mass);base=p.mass_floors[i];e.grounded_entry(p,box,base,street,others);e.select_climber(p,box,base,mass['storeys'],p.name+' wing'+str(i+1),p.floor_levels[i]);e.outer_windows(p,box,base,mass['storeys'],i,p.floor_levels[i])
    additional_workshop_entries(p,street);rear_oriel(p);e.reserve_circulation(p)
    for i,mass in enumerate(spec['masses']):
        box=p.local_box(mass);e.ceiling_details(p,p.mass_fields[i],p.mass_floors[i],mass['storeys'],box,p.floor_levels[i]);e.furnished_bays(p,p.mass_fields[i],p.mass_floors[i],mass['storeys'],spec['program'],i,p.floor_levels[i])
    for i,mass in enumerate(spec['masses']):
        x0,z0,x1,z1=p.local_box(mass);p.active_roof_ground=p.mass_fields[i];geometry=e.roof_geometry(p,(x0-1,z0-1,x1+1,z1+1),p.top_levels[i],mass['roof']);p.roof_sections.append({'mass':i,'actual_approved_roof_intent':mass['roof'],'geometry':geometry,'base':p.top_levels[i]});p.active_roof_ground=None
    old=dict(p.fixed);derivations=e.canonical_joins(p);p.blocks.update(old);p.join_derivations=[r for r in derivations if tuple(r['position'])not in old]
    return p


def prepare(home,output):
    reserve=guard(2*MIB,32*MIB);home=Path(home).resolve();output=Path(output).absolute()
    if digest(Path(e.__file__))!=ENGINE_SHA:raise UserError('Preserve frozen38 source engine')
    if output.exists()or output.parent!=home/'staging':raise UserError('New owned source folder only')
    registry=read_json(home/'dashboard/settlement/registry.json');layout=e.checked(home,e.LAYOUT);stock,custody=e.contexts(home,layout);specs={r['id']:deepcopy(r)for r in layout['buildings']if r['actual_building_floor_columns_xz']};spec=specs['bridge-cooper'];fields={k:set(map(tuple,r['actual_building_floor_columns_xz']))for k,r in specs.items()};protected,protected_refs=preservation(home,registry)
    streets={tuple(q)for r in layout['street_network']for q in r['all_walk_columns_xz']};p=build(registry,spec,stock['bridge-cooper'],set().union(*(v for k,v in fields.items()if k!='bridge-cooper'))|protected,streets,list(specs).index('bridge-cooper'));proof=e.validate(p)
    if len(p.original_BE_points)!=35 or len(p.spec['masses'])!=3 or len(p.footprint)!=408:raise UserError('Exact35 stock points/3masses/408 ground columns required')
    cp=read_json(home/'dashboard/settlement/backup-receipt.json');terrain=NorthTerrain(home,cp,registry)
    try:before,supports,actual=e.current_archive_field(terrain,p,verify_zinc_factory(home));sources=terrain.snapshot.sources
    finally:terrain.close()
    delta={p.world(q):v for q,v in p.blocks.items()if q not in p.fixed};full={p.world(q):v for q,v in p.blocks.items()};tags={p.world(q):snbt(v)for q,v in p.tags.items()};allocation=e.checked(home,e.ALLOCATION,2*MIB);source_ids=set()
    for r in allocation['room_allocations']:
        b=r['source_bounds_xyz']
        if any(all(b[i]<=q[i]<=b[i+3]for i in range(3))for q in delta):source_ids.add(r['id'])
    docs={'before-current-VERIFY-ONLY.json':native_payload(registry,before,cp['sha256'],'ACTUAL stopped Keel target states only; not future after-move AIR'),'supports-current-VERIFY-ONLY.json':native_payload(registry,supports,cp['sha256'],'ACTUAL stopped Keel underlying current support profiles'),'architecture-PROSPECTIVE-FORBIDDEN.json':native_payload(registry,delta,cp['sha256'],'PROSPECTIVE Keel35 architecture only after real six-room conservation',tags=tags),'full-after-PROSPECTIVE-VERIFY-ONLY.json':native_payload(registry,full,cp['sha256'],'PROSPECTIVE Keel35 complete expected states, never retained tag replay',tags=tags),'normal-joins-PROSPECTIVE-ONLY.json':native_payload(registry,{q:v for q,v in delta.items()if e.key(v)not in e.VOID},cp['sha256'],'PROSPECTIVE normal joins of new Keel architecture only')}
    record={'format':'awft-keel35-architecture-adaptation-SOURCE-ONLY:1','created':utcnow(),'checkpoint_id':cp['id'],'checkpoint_sha256':cp['sha256'],'engine_sha256':ENGINE_SHA,'source_sha256':digest(Path(__file__)),'custody':custody,'masses':spec['masses'],'origin':list(p.origin),'blocks_PROSPECTIVE_DELTA':[[*q,v]for q,v in sorted(delta.items())],'complete_expected_state_context_ONLY':[[*q,v]for q,v in sorted(full.items())],'fixed_native_states':[{'position':list(p.world(q)),'state':v}for q,v in sorted(p.fixed.items())],'retained_BE_positions':[list(p.world(q))for q in sorted(p.original_BE_points)],'required_native_completed_moves':stock['bridge-cooper']['moves'],'required_original_source_captures_before_architecture':sorted(source_ids),'required_owned_NONBE_shell_retirements':[{'position':list(p.world(q)),'exact_old_state':v}for q,v in sorted(p.retire.items())],'proof':proof,'rooms':p.rooms,'routes':p.routes,'entries':p.entries,'details':p.details,'actual_current_archive':actual,'protected_models':protected_refs,'native_actions':0,'world_writes':0,'construction_forbidden':True,'old_tags_or_items_written':0,'all_after_move_preimages_native_fullNBT_normal_use_and_real_views_pending':True}
    output.mkdir();members={}
    for name,doc in docs.items():
        doc.update(construction_forbidden=True,verification_only=True)
        if name not in('before-current-VERIFY-ONLY.json','supports-current-VERIFY-ONLY.json'):doc['prospective_not_observed']=True
        data=(json.dumps(doc,separators=(',',':'))+'\n').encode();(output/name).write_bytes(data);members[name]={'bytes':len(data),'sha256':digest(output/name)}
    path=output/'keel35-SOURCE-ONLY.json';path.write_text(json.dumps(record,separators=(',',':'))+'\n',encoding='utf8');members[path.name]={'bytes':path.stat().st_size,'sha256':digest(path)}
    manifest={'format':'awft-keel35-source-bundle:1','created':utcnow(),'source_sha256':digest(Path(__file__)),'engine_sha256':ENGINE_SHA,'checkpoint_id':cp['id'],'checkpoint_sha256':cp['sha256'],'files':members,'archive_sources':sources,'storage_guard':reserve,'native_actions':0,'world_writes':0,'construction_forbidden':True,'source_coverage':{'masses':3,'ground_columns':408,'retained_BEs':35,'furnished_floors':len(p.rooms),'new_targets':len(delta)}}
    (output/'manifest.json').write_text(json.dumps(manifest,separators=(',',':'))+'\n',encoding='utf8');return{'folder':str(output),'manifest_sha256':digest(output/'manifest.json'),'coverage':manifest['source_coverage'],'native_actions':0}


if __name__=='__main__':
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('--home',required=True,type=Path);a.add_argument('--output',required=True,type=Path);v=a.parse_args();print(json.dumps(prepare(v.home,v.output),indent=2))
