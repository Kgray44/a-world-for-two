"""Additive four-compound split-level composition for five reviewed room lifts.

Preserves frozen38 geometry/history and every actual retained object. No runtime.
"""
from __future__ import annotations
import argparse,json,time
from copy import deepcopy
from collections import deque
from pathlib import Path
from control_room.common import UserError,digest,read_json,utcnow
from tools import artistic_eastern_compound_sprint as e
from tools.artistic_north_bank_east import NorthTerrain,preservation,native_payload
from tools.artistic_create_substrate import verify_zinc_factory
from tools.artistic_fisherman_interior import snbt
from tools.playtest import guard

MIB=1024**2
NEW=('staging/eastern-floor-clearance-1793225532335615700/allocation-SOURCE-ONLY.json','ad2d190159c0913c84b1585494067060da1b76a32c0da862ba44bfd8b0f4b87b')
ENGINE_SHA='029ff89e0c6af6e1e07fb7fc0a439e634b6805b1966056f31e3a5c266a4fcdb5'
IDS=('worn-book','lampblack','navy-blue','keel-store')


def moved_stock(home,layout):
    stock,custody=e.contexts(home,layout);old=e.checked(home,e.ALLOCATION,2*MIB);new=e.checked(home,NEW,2*MIB)
    if not new['all_155_approved_floor_mass_XZ_unchanged']or len(new['room_allocations'])!=98 or len(new['native_move_order'])!=98:raise UserError('Exact source-only complete98 revised allocation required')
    before={r['id']:r for r in old['room_allocations']};after={r['id']:r for r in new['room_allocations']};changes=[]
    for ident,row in after.items():
        prior=before[ident]
        if row['source_bounds_xyz']!=prior['source_bounds_xyz']:raise UserError('No actual source capture may be resized')
        if row['destination_bounds_xyz']==prior['destination_bounds_xyz']:continue
        if row['destination_building']!=prior['destination_building']or row['destination_mass']!=prior['destination_mass']or row['destination_building']not in IDS:raise UserError('Only same-mass five room-height corrections allowed')
        delta=[row['destination_bounds_xyz'][i]-prior['destination_bounds_xyz'][i]for i in range(3)]
        if delta[0]or delta[2]or delta[1]not in(1,4):raise UserError('No horizontal/allocation shape changes enter the height layer')
        changes.append(ident);state=stock[row['destination_building']];a=prior['destination_bounds_xyz']
        inside=lambda q:all(a[i]<=q[i]<=a[i+3]for i in range(3))
        shift=lambda q:tuple(q[i]+delta[i]for i in range(3))
        for name in('moved','fixed','retire'):
            part={q:v for q,v in state[name].items()if inside(q)}
            for q in part:del state[name][q]
            for q,v in part.items():
                if shift(q)in state[name]:raise UserError('Revised exact room states collide')
                state[name][shift(q)]=v
        part={q for q in state['bes']if inside(q)};state['bes'].difference_update(part);state['bes'].update(shift(q)for q in part)
        for record in state['moves']:
            if record['pod_id']==ident:record.update(translation_xyz=row['translation_xyz'],destination_support_bounds_xyz=row['destination_bounds_xyz'])
    if len(changes)!=5 or new['prior_allocation_sha256']!=e.ALLOCATION[1]:raise UserError('Exactly five lifted rows on the reviewed prior allocation required')
    custody=deepcopy(custody);custody['revised_allocation']=NEW;return stock,custody,old,new


class LevelCompound(e.Compound):
    def __init__(self,registry,spec,stock,others,index,lower):
        super().__init__(registry,spec,stock,others,index);self.lower=lower;self.declared={};self.base_levels=[]
        for i,mass in enumerate(spec['masses']):
            cells=e.rectangle(*self.local_box(mass));base=mass['floor_y']-self.origin[1];levels=[base+v for v in mass.get('occupied_floor_offsets',[k*4 for k in range(mass['storeys'])])];self.base_levels.append(levels)
            for x,z in cells:
                local=list(levels)
                for zone in lower:
                    if zone['mass']==i and(x,z)in zone['cells']:local[-1]=zone['level']
                self.declared[x,z]=sorted(local)

    def open_cell(self,q,*,floor=True):
        if floor and(q[0],q[2])in self.declared and q[1]-1 not in self.declared[q[0],q[2]]:return False
        return super().open_cell(q,floor=floor)

    def floor_under(self,q):return max((v for v in self.declared.get((q[0],q[2]),[])if v<q[1]),default=0)


def fixture_backings(p):
    for q,value in sorted(p.fixed.items()):
        ident=e.key(value);props=e.properties(value)
        if ident.split(':',1)[-1].startswith('potted_'):
            below=q[0],q[1]-1,q[2]
            if e.key(p.blocks.get(below,'minecraft:air'))in e.VOID:
                for y in range(p.floor_under(q)+1,q[1]):
                    if(q[0],y,q[2])in p.fixed:raise UserError('A real conserved planter backing cannot replace another furnishing')
                    p.put(q[0],y,q[2],'minecraft:dark_oak_planks',role='real rooted planter sill on its actual split-level floor');p.backing_points.add((q[0],y,q[2]))
            p.supports.append((q,below));continue
        if not(ident.endswith('_wall_sign')or ident=='supplementaries:item_shelf'or ident.endswith('_shelf')or ident.startswith('mcwlights:')):continue
        face=props.get('facing')
        if face not in e.VEC:continue
        dx,dz=e.VEC[face];back=q[0]-dx,q[1],q[2]-dz
        if e.key(p.blocks.get(back,'minecraft:air'))in e.VOID:
            rail=None;base=p.floor_under(back)
            if back[1]-base>=3:
                structural={*e.PANELS,'minecraft:stripped_dark_oak_log','minecraft:dark_oak_planks','minecraft:spruce_planks','chipped:reinforced_dark_oak_log','chipped:edged_stripped_dark_oak_log'}
                for vx,vz in((-1,0),(1,0),(0,-1),(0,1)):
                    path=[]
                    for n in range(9):
                        t=back[0]+n*vx,back[1],back[2]+n*vz
                        if not p.permitted(t)or t in p.fixed or t in p.body:break
                        if e.key(p.blocks.get(t,'minecraft:air'))in structural:
                            rail=(path,'x'if vx else'z');break
                        path.append(t)
                    if rail:break
            if rail:
                for t in rail[0]:p.beam(*t,rail[1],role='real short overhead wall-light rail rooted in the new room frame');p.backing_points.add(t)
            else:
                for y in range(base+1,q[1]+1):
                    t=back[0],y,back[2]
                    if t not in p.fixed:p.beam(*t,('x'if dz else'z')if y==base+1 else'y',role='actual rooted backing and transverse shoe tied to the correct room floor');p.backing_points.add(t)
        p.backing_points.add(back);p.supports.append((q,back))


def floor_plate(p,cells,level):
    x0=min(x for x,z in cells)
    for x,z in sorted(cells):
        if level not in p.declared[x,z]:continue
        if(x,z-1)not in cells or(x,z+1)not in cells:p.put(x,level,z,'minecraft:dark_oak_planks',role='actual split-level transverse end board')
        elif(x-1,z)not in cells or(x+1,z)not in cells:p.put(x,level,z,'minecraft:stripped_spruce_wood',axis='z',role='actual floor-edge sleeper')
        elif(x-x0)%4==0:p.put(x,level,z,'chipped:cross_laced_spruce_planks',role='physical narrow longitudinal floor joist')
        else:p.put(x,level,z,'minecraft:spruce_planks',role='weathered three-wide floorboards at the correct literal room height')


def split_link(p,zone):
    low=zone['level'];high=p.base_levels[zone['mass']][-1];cells=zone['cells'];candidates=[]
    if high-low!=1:raise UserError('Each recessed retained room needs exactly one ordinary riser')
    for x,z in sorted(e.boundary(cells)):
        for face,(dx,dz)in e.VEC.items():
            step=x,low+1,z;landing=x+dx,high+1,z+dz
            if(x+dx,z+dz)in cells or not p.open_cell(landing):continue
            approaches=[(x+ax,low+1,z+az)for ax,az in((-dx,-dz),(-dz,dx),(dz,-dx))if(x+ax,z+az)in cells and p.open_cell((x+ax,low+1,z+az))]
            touched={step,(x,low+2,z),(x,low+3,z),landing,(landing[0],landing[1]+1,landing[2])}
            if any(q in p.fixed or q in p.body or q in p.backing_points for q in touched)or not approaches:continue
            candidates.append((abs(x-(min(a for a,b in cells)+max(a for a,b in cells))/2)+abs(z-(min(b for a,b in cells)+max(b for a,b in cells))/2),x,z,face,landing,approaches[0]))
    if not candidates:raise UserError('No real one-riser retained-room link fits without erasing inventory/headroom')
    _,x,z,face,landing,approach=min(candidates);step=x,low+1,z
    p.put(*step,'minecraft:dark_oak_stairs',facing=face,half='bottom',shape='straight',waterlogged=False,role='actual one-riser transition from preserved lower room to raised loft')
    for y in(low+2,low+3):p.put(x,y,z,'minecraft:air',role='literal headroom over the real split-level stair');p.body.add((x,y,z))
    p.stairs.append(step);p.reserve('Retained lower room stair approach',[approach]);p.reserve('Raised gallery stair arrival',[landing]);p.vertical.append({'kind':'native ordinary stair','risers':1,'blocks':[list(step)],'lower_approach':list(approach),'landing':list(landing),'lower_room_capsule':zone['room_id']})


def reserve_circulation(p):
    graph=e.walking_graph(p);roots=[]
    for entry in p.entries:
        q=tuple(entry['local']);dx,dz=e.VEC[entry['outward']];r=q[0]-dx,q[1],q[2]-dz
        if r in graph:roots.append(r)
    parents={q:None for q in roots};todo=deque(roots)
    while todo:
        q=todo.popleft()
        for r in sorted(graph[q]):
            if r not in parents:parents[r]=q;todo.append(r)
    if not roots:raise UserError('A split-level compound requires an actual exterior entry')
    goals=[]
    for i,cells in enumerate(p.mass_fields):
        for level in p.floor_levels[i]:
            nodes=[q for q in parents if q[1]==level+1 and(q[0],q[2])in cells]
            if not nodes:raise UserError('An actual split-level floor zone has no ordinary connected route: '+str((p.name,i,level)))
            cx=sum(x for x,z in cells)/len(cells);cz=sum(z for x,z in cells)/len(cells);goals.append(min(nodes,key=lambda q:(abs(q[0]-cx)+abs(q[2]-cz),q)))
    for point in p.original_BE_points|p.original_functional_nonBE_points:
        feet=p.floor_under(point)+1;nodes=[q for q in parents if q[1]==feet and abs(q[0]-point[0])+abs(q[2]-point[2])<=3]
        if not nodes:raise UserError('Conserved furniture lacks an actual connected split-level visiting point: '+str(p.world(point)))
        goals.append(min(nodes,key=lambda q:(abs(q[0]-point[0])+abs(q[2]-point[2]),q)))
    paths=set()
    for q in goals:
        while q is not None:paths.add(q);q=parents[q]
    p.reserve('Literal connected split-level rooms and every retained native work/inventory point',sorted(paths));p.circulation={'reachable_floor_nodes_before_new_furniture':len(parents),'reserved_supported_feet':len(paths),'mass_floor_visiting_points':[list(q)for q in goals],'source_only_native_use_pending':True}


def windows(p,box,mass_index):
    x0,z0,x1,z1=box;stories=p.spec['masses'][mass_index]['storeys']
    for floor in range(stories):
        for face,points in(('north',[(x,z0)for x in range(x0+2,x1-1,4)]),('south',[(x,z1)for x in range(x0+1,x1-1,4)]),('west',[(x0,z)for z in range(z0+2,z1-1,4)]),('east',[(x1,z)for z in range(z0+1,z1-1,4)])):
            dx,dz=e.VEC[face];tx,tz=(1,0)if dz else(0,1)
            for x,z in points:
                if(x+dx,z+dz)in p.footprint:continue
                level=p.declared[x,z][floor];width=1 if min(x1-x0,z1-z0)<4 else 2
                if any(p.declared.get((x+n*tx,z+n*tz),[])[floor:floor+1]!=[level]for n in range(width)):width=1
                y=level+1;targets=[(x+n*tx,y+h,z+n*tz)for n in range(width)for h in(0,1)]
                if any(q in p.fixed or q in p.body or q in p.backing_points for q in targets):continue
                projected=[(x+n*tx+dx,y+2,z+n*tz+dz)for n in range(-1,width+1)]+[(x+n*tx+dx,y+1,z+n*tz+dz)for n in(-1,width)]
                if any(not p.permitted(q)or q in p.body for q in projected):continue
                p.casement(x,y,z,face,width=width,height=2)


def ceilings(p):
    for i,cells in enumerate(p.mass_fields):
        x0,z0,x1,z1=p.local_box(p.spec['masses'][i])
        for x,z in sorted(cells):
            if not x0<x<x1 or not z0<z<z1:continue
            levels=p.declared[x,z]
            for n,level in enumerate(levels):
                ceiling=(levels[n+1]if n+1<len(levels)else p.top_levels[i])-1;q=x,ceiling,z
                if(z-z0)%4==2 and q not in p.fixed and q not in p.body:p.slab(*q,'mangrove',role='actual coffer rib following the real stepped underside of each floor')
        for level in p.floor_levels[i]:
            candidates=[(x,z)for x,z in cells if level in p.declared[x,z]and x0<x<x1 and z0<z<z1]
            if not candidates:continue
            for x,z in sorted(candidates,key=lambda q:(abs(q[0]-(x0+x1)/2)+abs(q[1]-(z0+z1)/2),q)):
                levels=p.declared[x,z];n=levels.index(level);ceiling=(levels[n+1]if n+1<len(levels)else p.top_levels[i])-1;q=x,ceiling,z;back=x,ceiling+1,z
                if q in p.fixed or q in p.body or e.key(p.blocks.get(back,'minecraft:air'))in e.VOID:continue
                p.put(*q,'minecraft:lantern',hanging=True,waterlogged=False,role='small warm source lamp mounted to the real split-level ceiling');p.supports.append((q,back));break


def build(registry,spec,stock,others,street,index,lower):
    p=LevelCompound(registry,spec,stock,others,index,lower)
    for i,mass in enumerate(spec['masses']):
        box=p.local_box(mass);cells=e.rectangle(*box);base=mass['floor_y']-p.origin[1];levels=p.base_levels[i];top=levels[-1]+4
        p.mass_fields.append(cells);p.mass_floors.append(base);p.floor_levels.append(list(levels));p.top_levels.append(top);p.clear_new_room(cells,base,top-base)
        for level in sorted(set(v for x,z in cells for v in p.declared[x,z])):floor_plate(p,cells,level)
        p.floor(cells,top)
        for low,high in zip(levels,levels[1:]+[top]):p.walls(cells,low+1,high,e.PANELS[(index+i)%len(e.PANELS)])
        for level in levels+[top]:p.ring(cells,level)
        for x,z in e.boundary(cells):p.put(x,base-1,z,'minecraft:stone_bricks'if(x-1,z)in cells and(x+1,z)in cells else'minecraft:cobbled_deepslate',role='unchanged narrow actual approved-mass foundation plinth')
    for zone in lower:p.backing_points.update((x,zone['level'],z)for x,z in zone['cells'])
    fixture_backings(p);e.join_masses(p)
    for zone in lower:
        split_link(p,zone)
        visits=[(x,zone['level']+1,z)for x,z in sorted(zone['cells'])if p.open_cell((x,zone['level']+1,z))]
        p.reserve('Conserved lower-room clear floor and actual new one-step approach',visits)
        # These are real retained-room head cells, also above low native
        # furniture. A main loft flight cannot claim a landing on its bed or
        # shelf merely because the old helper sees a non-AIR block below it.
        for x,z in zone['cells']:
            q=x,zone['level']+2,z
            if q not in p.fixed and e.key(p.blocks.get(q,'minecraft:air'))in e.VOID:p.body.add(q)
    for i,mass in enumerate(spec['masses']):
        box=p.local_box(mass);base=p.mass_floors[i];e.grounded_entry(p,box,base,street,others)
        allbe=p.original_BE_points;allfunction=p.original_functional_nonBE_points
        # Main flights serve the raised gallery; the separately modeled real
        # one-riser links serve retained lower rooms. All goals are restored
        # before the strict whole-compound final circulation check.
        excluded={q for q in allbe|allfunction if any((q[0],q[2])in z['cells']and q[1]>z['level']for z in lower)}
        p.original_BE_points=allbe-excluded;p.original_functional_nonBE_points=allfunction-excluded
        try:e.select_climber(p,box,base,mass['storeys'],p.name+' actual gallery flight'+str(i+1),p.base_levels[i])
        finally:p.original_BE_points=allbe;p.original_functional_nonBE_points=allfunction
        windows(p,box,i)
    for i,cells in enumerate(p.mass_fields):p.floor_levels[i]=sorted(set(v for q in cells for v in p.declared[q]))
    reserve_circulation(p);ceilings(p)
    for i,mass in enumerate(spec['masses']):e.furnished_bays(p,p.mass_fields[i],p.mass_floors[i],mass['storeys'],spec['program'],i,p.floor_levels[i])
    for i,mass in enumerate(spec['masses']):
        x0,z0,x1,z1=p.local_box(mass);p.active_roof_ground=p.mass_fields[i];geometry=e.roof_geometry(p,(x0-1,z0-1,x1+1,z1+1),p.top_levels[i],mass['roof']);p.roof_sections.append({'mass':i,'actual_approved_roof_intent':mass['roof'],'geometry':geometry,'base':p.top_levels[i]});p.active_roof_ground=None
    original=dict(p.fixed);derivations=e.canonical_joins(p);p.blocks.update(original);p.join_derivations=[r for r in derivations if tuple(r['position'])not in original];return p


def prepare(home,output):
    reserve=guard(2*MIB,32*MIB);home=Path(home).resolve();output=Path(output).absolute()
    if digest(Path(e.__file__))!=ENGINE_SHA or output.exists()or output.parent!=home/'staging':raise UserError('Frozen38 engine and new owned output required')
    registry=read_json(home/'dashboard/settlement/registry.json');layout=e.checked(home,e.LAYOUT);stock,custody,old,new=moved_stock(home,layout);oldrows={r['id']:r for r in old['room_allocations']};specs={r['id']:deepcopy(r)for r in layout['buildings']if r['actual_building_floor_columns_xz']};fields={k:set(map(tuple,r['actual_building_floor_columns_xz']))for k,r in specs.items()};protected,protected_refs=preservation(home,registry);streets={tuple(q)for r in layout['street_network']for q in r['all_walk_columns_xz']};cp=read_json(home/'dashboard/settlement/backup-receipt.json');terrain=NorthTerrain(home,cp,registry);docs={};results=[];holds=[]
    try:
        for ident in IDS:
            spec=specs[ident];primary=spec['masses'][0];primary['occupied_floor_offsets']=[0,4,9]if ident in('worn-book','lampblack')else[0,5]
            if ident=='navy-blue':spec['masses'][1]['storeys']=2
            origin=(min(x for x,z in fields[ident]),64,min(z for x,z in fields[ident]));lower=[]
            for row in new['room_allocations']:
                if row['destination_building']!=ident or row['destination_mass']!=0:continue
                prior=oldrows[row['id']];b=row['destination_bounds_xyz'];oldtop=72 if ident in('worn-book','lampblack')else 68
                if b==prior['destination_bounds_xyz']and b[1]==oldtop:
                    lower.append({'mass':0,'level':b[1]-64,'cells':{(x-origin[0],z-origin[2])for x in range(b[0],b[3]+1)for z in range(b[2],b[5]+1)},'room_id':row['id']})
            try:p=build(registry,spec,stock[ident],set().union(*(v for k,v in fields.items()if k!=ident))|protected,streets,list(specs).index(ident),lower);proof=e.validate(p)
            except(UserError,ValueError)as exc:holds.append({'id':ident,'reason':str(exc),'emitted':False});continue
            before,supports,actual=e.current_archive_field(terrain,p,verify_zinc_factory(home));delta={p.world(q):v for q,v in p.blocks.items()if q not in p.fixed};full={p.world(q):v for q,v in p.blocks.items()};tags={p.world(q):snbt(v)for q,v in p.tags.items()};needed=[]
            for r in new['room_allocations']:
                b=r['source_bounds_xyz']
                if any(all(b[i]<=q[i]<=b[i+3]for i in range(3))for q in delta):needed.append(r['id'])
            for suffix,field,label,newtags in [('before-current-VERIFY-ONLY',before,'ACTUAL current stopped states only; not future after conservation',{}),('supports-current-VERIFY-ONLY',supports,'ACTUAL stopped support profiles only',{}),('architecture-PROSPECTIVE-FORBIDDEN',delta,'PROSPECTIVE five-height split-level correction only after actual custody',tags),('full-after-PROSPECTIVE-VERIFY-ONLY',full,'PROSPECTIVE complete split-level state context; retained old NBT never replayed',tags),('normal-joins-PROSPECTIVE-ONLY',{q:v for q,v in delta.items()if e.key(v)not in e.VOID},'PROSPECTIVE normal native joins of new architecture only',{})]:
                doc=native_payload(registry,field,cp['sha256'],label,tags=newtags);doc.update(construction_forbidden=True,verification_only=True,prospective_not_observed=not suffix.startswith(('before','supports')));docs[ident+'-'+suffix+'.json']=doc
            docs[ident+'-SOURCE-ONLY.json']={'format':'awft-eastern-five-height-compound-SOURCE-ONLY:1','id':ident,'origin':list(p.origin),'masses':spec['masses'],'floor_cells':[[x,z,v]for(x,z),levels in sorted(p.declared.items())for v in levels],'blocks_PROSPECTIVE_DELTA':[[*q,v]for q,v in sorted(delta.items())],'complete_expected_state_context_ONLY':[[*q,v]for q,v in sorted(full.items())],'preserved_fixed_native_states':[{'position':list(p.world(q)),'state':v}for q,v in sorted(p.fixed.items())],'retained_BE_positions':[list(p.world(q))for q in sorted(p.original_BE_points)],'required_native_completed_moves':stock[ident]['moves'],'required_original_source_captures_before_architecture':sorted(needed),'required_owned_NONBE_shell_retirements':[{'position':list(p.world(q)),'exact_old_state':v}for q,v in sorted(p.retire.items())],'proof':proof,'rooms':p.rooms,'routes':p.routes,'entries':p.entries,'actual_current_archive':actual,'native_actions':0,'construction_forbidden':True,'old_tags_or_items_written':0}
            results.append({'id':ident,'masses':len(spec['masses']),'furnished_floor_zones':len(p.rooms),'retained_BEs':len(p.original_BE_points),'targets':len(delta),'vertical_routes':p.vertical,'preserved_lower_room_ids':[r['room_id']for r in lower]})
        sources=terrain.snapshot.sources
    finally:terrain.close()
    output.mkdir();files={}
    for name,doc in docs.items():
        raw=(json.dumps(doc,separators=(',',':'))+'\n').encode();(output/name).write_bytes(raw);files[name]={'bytes':len(raw),'sha256':digest(output/name)}
    manifest={'format':'awft-eastern-five-height-source-bundle:1','created':utcnow(),'source_sha256':digest(Path(__file__)),'engine_sha256':ENGINE_SHA,'allocation':{'path':NEW[0],'sha256':NEW[1]},'checkpoint_id':cp['id'],'checkpoint_sha256':cp['sha256'],'custody':custody,'results':results,'held':holds,'files':files,'protected_models':protected_refs,'archive_sources':sources,'reserve_guard':reserve,'source_only':True,'construction_forbidden':True,'native_actions':0,'world_writes':0,'requires_new_catalogue_no_intent_and_all_current_native_custody_and_admission_gates':True}
    (output/'manifest.json').write_text(json.dumps(manifest,separators=(',',':'))+'\n',encoding='utf8');return{'folder':str(output),'manifest_sha256':digest(output/'manifest.json'),'ready':len(results),'held':holds,'native_actions':0}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--home',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();print(json.dumps(prepare(a.home,a.output),indent=2))
