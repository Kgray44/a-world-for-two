"""Original eastern Tortuga architecture on the owner's exact approved masses.

Source only. Real room contents arrive through the native mover; this producer
never replays their tags, retires a live shell, installs requests or runs a game.
"""
from __future__ import annotations
import argparse,hashlib,json,math,time
from collections import Counter,deque
from copy import deepcopy
from pathlib import Path

from control_room.common import UserError,digest,read_json,utcnow
from tools.artistic_bridge_refinement import flatten
from tools.artistic_captains_hall import rectangle,boundary,VEC
from tools.artistic_eastern_urban_block import ARCH,CORRECTED_CUSTODY
from tools.artistic_fisherman_interior import snbt
from tools.artistic_materials import require_material_rule
from tools.artistic_spawn_plaza import state
from tools.artistic_tortuga_pair import TradeHouse,hip
from tools.artistic_west_r2_frontage import canonical_joins,key
from tools.artistic_zipline_catenary import reader_budget
from tools.artistic_north_bank_east import NorthTerrain,native_payload,preservation
from tools.artistic_salt_petal import POTS
from tools.artistic_ground_stability import GRAVITY,STABLE_NATURAL
from tools.artistic_create_substrate import verify_zinc_factory
from tools.playtest import guard
from tools.settlement_attractions import properties

MIB=1024**2
LAYOUT=('staging/eastern-coast-urban-layout-1793205607174241200/urban-plan-REVIEW-ONLY.json',
        '6f24640d9efefae3340be80d34bcd0e4788f2ded695aefe03d1d6815761a12a4')
POLICY=('staging/eastern-required-policy-relocations-1793216708724099400/new-destinations-SOURCE-ONLY.json',
        '862e6e8707062908d15a6639b493d6b098257df7fa40dae90731d967b9f0fb69')
CATALOG=('staging/eastern-catalog-r5-1793219566430973900/approved98-capsules-PRIVATE.json',
         '698969e25fb001c21fb4a9b8301d96b7892d0affe9a9263369c74bba591d7fc5')
ALLOCATION=('staging/eastern-self-overlap23-disjoint-DAG-1793219467452176700/allocation-SOURCE-ONLY.json',
            '517c1dab4c9d467fe8d072d86b5fb759aab51d493b6c6b229cde43849457bf18')
FIRST_TEN=('bridge-customs','worn-book','ropes-pearl','crooked-inn','lampblack',
           'net-mender','moon-branch','moth-candle','nail-drift','tide-fish')
VOID={'minecraft:air','minecraft:cave_air','minecraft:void_air'}
FACES=('north','east','south','west')
PANELS=('minecraft:gray_terracotta','minecraft:brown_terracotta','minecraft:light_gray_terracotta')
FUNCTIONAL_NON_BE={'minecraft:'+name for name in('cartography_table','smithing_table','fletching_table','grindstone','anvil','chipped_anvil','damaged_anvil','loom','composter','crafting_table','stonecutter')}
MAX_TARGETS=18000


def checked(home,ref,cap=8*MIB):
    relative,sha=ref;p=(home/relative).absolute()
    if not p.is_relative_to(home)or p.is_symlink()or not p.is_file()or not 0<p.stat().st_size<=cap or digest(p)!=sha:
        raise UserError('Exact bounded original custody/layout required: '+str(relative))
    return read_json(p)


def contexts(home,layout):
    """Typed custody's authorship classification is stronger than an ID list."""
    manifest=checked(home,CORRECTED_CUSTODY,2*MIB)
    folder=(home/CORRECTED_CUSTODY[0]).parent
    member=manifest['files']['capsule-source-cells-FULL-READONLY-PRIVATE.jsonl']
    path=folder/'capsule-source-cells-FULL-READONLY-PRIVATE.jsonl'
    if path.is_symlink()or path.stat().st_size!=member['bytes']or digest(path)!=member['sha256']:
        raise UserError('Complete exact source-cell custody required')
    groups={};count=0
    with path.open(encoding='utf-8')as stream:
        for line in stream:
            count+=1
            if count>40000 or len(line)>8192:raise UserError('Finite typed room custody exceeded')
            row=json.loads(line)
            for ident in row['pod_ids']:groups.setdefault(ident,[]).append(row)
    policy=checked(home,POLICY,2*MIB)
    if not policy['all_floor_masses_unchanged']or policy['original_approved_floor_layout_sha256']!=LAYOUT[1]:raise UserError('Exact later owner relocation-only policy required')
    allocation=checked(home,ALLOCATION,2*MIB)
    if allocation['format']!='awft-eastern-room-allocation-addendum:5'or allocation['approved_XZ_layout_sha256']!=LAYOUT[1]or not allocation['all_155_approved_floor_mass_XZ_unchanged']or len(allocation['room_allocations'])!=98:
        raise UserError('The exact revised98-room/floor allocation is required')
    if allocation['self_source_intersections']or allocation['future_destination_intersections']or allocation['changed_bidirectional_BE_support_intersections']or len(allocation['native_move_order'])!=98:
        raise UserError('Every exact conserved room needs its disjoint source/destination and complete reviewed order')
    transfers=[]
    for row in allocation['room_allocations']:
        delta=row['translation_xyz'];transfers.append({'pod_id':row['id'],'translation_xyz':delta,
          'source_support_bounds_xyz':row['source_bounds_xyz'],'destination_support_bounds_xyz':row['destination_bounds_xyz'],
          'destination_building':row['destination_building'],'destination_mass':row['destination_mass'],
          'BE_point_transfers':[{'source':q,'destination':[q[i]+delta[i]for i in range(3)]}for q in row['expected_source_BE_positions']],
          'source_addendum_only_native_proof_still_required':True})
    catalog=checked(home,CATALOG,2*MIB)
    source_preps={r['id']:{tuple(v['position']):v['before']for v in r['source_cover_preparations']}for r in catalog['capsules']}
    result={}
    for compound in layout['buildings']:
        ident=compound['id'];moved={};bes=set();fixed={};retire={};records=[]
        for tr in transfers:
            if tr['destination_building']!=ident:continue
            pod=tr['pod_id'];delta=tr['translation_xyz'];rows=groups.get(pod)
            if not rows:raise UserError('The original complete source field has no allocated room: '+pod)
            bounds=tr['source_support_bounds_xyz'];required={(x,y,z)for x in range(bounds[0],bounds[3]+1)for y in range(bounds[1],bounds[4]+1)for z in range(bounds[2],bounds[5]+1)}
            if {tuple(r['position'])for r in rows}!=required:raise UserError('The original room field is not its exact complete allocated source box')
            be={tuple(r['destination'])for r in tr['BE_point_transfers']};bes|=be
            for row in rows:
                q=tuple(row['position'][i]+delta[i]for i in range(3));value=row['current_saved'];kind=row['classification']
                if source_preps.get(pod,{}).get(tuple(row['position']))==value:
                    if kind!='UNOWNED_CURRENT_STATE_HOLD'or key(value)not in{'minecraft:short_grass','minecraft:tall_grass','regions_unexplored:grass_sprouts'}:raise UserError('Only the exact separately reviewed ordinary cover may become source AIR before clone')
                    value='minecraft:air'
                if q in moved and moved[q]!=value:raise UserError('Two prospective conserved rooms overlap different actual states')
                moved[q]=value
                owned=kind=='EXACT_OWNED_NON_BE_SOURCE'
                architectural=key(value)in ARCH or key(value).startswith(('mcwwindows:','mcwroofs:','mythrais:roof_'))
                if q in be:fixed[q]=value
                elif owned and architectural:retire[q]=value
                elif kind=='CURRENT_SOURCE_DIFFERENCE_HOLD_NATIVE_OR_HUMAN_ORIGIN_UNPROVEN':fixed[q]=value
                elif key(value)not in VOID:
                    # An actual non-BE furnishing or unowned current object
                    # remains literal. Only separately reviewed shell retires.
                    fixed[q]=value
            records.append({'pod_id':pod,'translation_xyz':delta,'source_support_bounds_xyz':tr['source_support_bounds_xyz'],
                            'destination_support_bounds_xyz':tr['destination_support_bounds_xyz'],'native_completed_move_required':True,
                            'separately_required_native_source_cover_preparations':[{'position':list(q),'before':v,'after':'minecraft:air'}for q,v in sorted(source_preps.get(pod,{}).items())],
                            'identity_translation_not_native_move_authority':not any(delta)})
        result[ident]={'moved':moved,'fixed':fixed,'bes':bes,'retire':retire,'moves':records}
    return result,{'manifest':CORRECTED_CUSTODY,'policy_addendum':POLICY,'revised_allocation':ALLOCATION,'requires_new_native_catalogue_and_all98_actual_guards':True,
                   'complete_cells':{'relative':str(path.relative_to(home)),'sha256':member['sha256'],'bytes':member['bytes']},'rows':count}


class Compound(TradeHouse):
    def __init__(self,registry,spec,stock,other_columns,index):
        self.spec=spec;self.index=index
        xs=[q[0]for q in spec['actual_building_floor_columns_xz']];zs=[q[1]for q in spec['actual_building_floor_columns_xz']]
        origin=(min(xs),min(m['floor_y']for m in spec['masses']),min(zs))
        super().__init__(registry,spec['name'],origin)
        self.footprint={self.local_xz(q)for q in spec['actual_building_floor_columns_xz']}
        self.fixed={self.local(q):s for q,s in stock['fixed'].items()}
        self.blocks=dict(self.fixed);self.roles={q:'Exact conserved furnishing/BE/current difference — never written by architecture'for q in self.fixed}
        self.original_BE_points={self.local(q)for q in stock['bes']}
        self.original_functional_nonBE_points={q for q,v in self.fixed.items()if key(v)in FUNCTIONAL_NON_BE}
        self.retire={self.local(q):s for q,s in stock['retire'].items()}
        self.other_columns={self.local_xz(q)for q in other_columns}
        self.max_x=max(x for x,z in self.footprint);self.max_z=max(z for x,z in self.footprint)
        self.suppressed=Counter();self.vertical=[];self.scene_points=[];self.roof_sections=[]
        self.backing_points=set()
        self.route_floor_points=set()
        self.mass_fields=[];self.mass_floors=[];self.floor_levels=[];self.top_levels=[];self.fixed_doors=[]
        self.entry_door_states={};self.entry_clearance_points=set();self.entry_threshold_points=set()
        self.active_roof_ground=None
        for q,value in self.fixed.items():
            if key(value).endswith('_door')and properties(value).get('half')=='lower':self.fixed_doors.append(q)

    def local(self,q):return tuple(q[i]-self.origin[i]for i in range(3))
    def world(self,q):return tuple(q[i]+self.origin[i]for i in range(3))
    def local_xz(self,q):return q[0]-self.origin[0],q[1]-self.origin[2]

    def permitted(self,q):
        x,y,z=q
        if not(-2<=x<=self.max_x+2 and -1<=y<=25 and -2<=z<=self.max_z+2):raise UserError('Finite exact compound envelope exceeded')
        if(x,z)in self.other_columns and(x,z)not in self.footprint:return False
        return True

    def put(self,x,y,z,material,*,role='authored compound architecture',**props):
        q=x,y,z;value=state(self.registry,material,**props)
        if not self.permitted(q):self.suppressed['projection_into_other_approved_compound']+=1;return False
        if q in self.entry_door_states and value!=self.entry_door_states[q]:
            self.suppressed['preserved_real_new_entry_door']+=1;return False
        if q in self.entry_clearance_points and material not in VOID:
            self.suppressed['preserved_real_new_entry_leaf_clearance']+=1;return False
        if q in self.entry_threshold_points and value!=self.blocks.get(q):
            self.suppressed['preserved_real_new_entry_threshold']+=1;return False
        if q in self.fixed:
            if value!=self.fixed[q]:self.suppressed['preserved_actual_native_furnishing_or_current_difference']+=1
            return False
        if q in self.backing_points and value!=self.blocks.get(q):
            self.suppressed['preserved_new_rooted_fixture_or_ladder_backing']+=1;return False
        if q in self.route_floor_points and value!=self.blocks.get(q):
            self.suppressed['preserved_literal_reserved_route_floor']+=1;return False
        if q in self.body and self.active_roof_ground is not None and(x,z)not in self.active_roof_ground:
            self.suppressed['new_annex_roof_abuts_higher_connected_room_headroom']+=1;return False
        if q in self.body and material not in VOID and not material.endswith('_door'):
            raise UserError('Do not block the actual new walking body: '+str((self.name,q,material)))
        self.blocks[q]=value;self.roles[q]=role;self.tags.pop(q,None)
        if len(self.blocks)>MAX_TARGETS:raise UserError('Finite18K single compound exceeded')
        return True

    def reserve(self,title,cells,*,stairs=False):
        cells=list(cells)
        for x,y,z in cells:
            for yy in(y,y+1):
                q=x,yy,z;value=self.blocks.get(q,'minecraft:air')
                if q in self.fixed and key(value)not in VOID and not key(value).endswith('_door'):
                    raise UserError('A new route cannot erase an inherited real fixture or unknown difference')
                if not key(value).endswith('_door'):self.put(*q,'minecraft:air',role='actual two-high new room passage')
                self.body.add(q)
            if key(self.blocks.get((x,y-1,z),'minecraft:air'))in VOID:raise UserError('Reserve only a literal supported visiting route')
            self.route_floor_points.add((x,y-1,z))
        self.routes.append({'name':title,'feet_local':[list(q)for q in cells],'kind':'stairs'if stairs else'floor'})

    def clear_new_room(self,cells,base,height):
        for x,z in cells:
            for y in range(base+1,base+height):
                if(x,y,z)not in self.fixed:self.put(x,y,z,'minecraft:air',role='explicit post-retirement new occupied room')

    def open_cell(self,q,*,floor=True):
        x,y,z=q
        if any(key(self.blocks.get((x,y+h,z),'minecraft:air'))not in VOID and not key(self.blocks.get((x,y+h,z),'minecraft:air')).endswith('_door')for h in(0,1)):return False
        if floor and key(self.blocks.get((x,y-1,z),'minecraft:air'))in VOID:return False
        return True

    def local_box(self,m):
        a,b,c,d=m['bounds_xz'];return a-self.origin[0],b-self.origin[2],c-self.origin[0],d-self.origin[2]


def select_climber(p,box,base,storeys,title,levels=None):
    """Prefer real four-riser stairs; a narrow service ladder is an explicit fallback."""
    if storeys<2:return
    levels=list(levels or[base+k*4 for k in range(storeys)])
    if len(levels)!=storeys or levels[0]!=base or any(not 4<=b-a<=6 for a,b in zip(levels,levels[1:])):raise UserError('Exact ordinary four-to-six riser floor levels required')
    x0,z0,x1,z1=box;chosen=[]
    source_before={name:deepcopy(getattr(p,name))for name in('blocks','roles','tags','body','routes','stairs','vertical','route_floor_points')}
    for floor in range(storeys-1):
        low=levels[floor];rise=levels[floor+1]-low;flight=None
        # A one-cell-wide interior cannot pass around the real carriage or
        # upper stair opening. Give those genuine narrow wings their normal
        # attached service ladder instead of isolating half of each floor.
        if min(x1-x0,z1-z0)<=2:break
        for face in('south','north','east','west'):
            dx,dz=VEC[face]
            for x in range(x0+1,x1):
                for z in range(z0+1,z1):
                    cells=[(x+n*dx,low+1+n,z+n*dz)for n in range(rise)]
                    landing=(x+rise*dx,low+rise+1,z+rise*dz)
                    touched=set()
                    for xx,yy,zz in cells:
                        touched|={(xx,h,zz)for h in range(low+1,yy+3)}
                    touched|={landing,(landing[0],landing[1]+1,landing[2])}
                    if any(not(x0<q[0]<x1 and z0<q[2]<z1)or q in p.fixed or q in p.body or q in p.backing_points or q in p.route_floor_points for q in touched):continue
                    if key(p.blocks.get((landing[0],landing[1]-1,landing[2]),'minecraft:air'))in VOID:continue
                    approaches=[]
                    for ax,az in((-dx,-dz),(-dz,dx),(dz,-dx)):
                        q=x+ax,low+1,z+az
                        if x0<q[0]<x1 and z0<q[2]<z1 and q not in touched and p.open_cell(q):approaches.append(q)
                    if not approaches:continue
                    # Qualify BOTH real arrivals after the candidate's exact
                    # carriage/opening. An unobstructed pre-stair room is not
                    # proof that this stair reaches the entry or upper stock.
                    overlay={}
                    for xx,yy,zz in cells:
                        for h in range(low+1,yy):overlay[xx,h,zz]='minecraft:dark_oak_planks'
                        overlay[xx,yy,zz]='minecraft:dark_oak_stairs'
                        for h in(yy+1,yy+2):overlay[xx,h,zz]='minecraft:air'
                    for xx,yy,zz in[landing]+approaches:
                        for h in(yy,yy+1):overlay[xx,h,zz]='minecraft:air'
                    def walking(q):
                        xx,yy,zz=q
                        values=[overlay.get((xx,yy+h,zz),p.blocks.get((xx,yy+h,zz),'minecraft:air'))for h in(-1,0,1)]
                        return key(values[0])not in VOID and all(key(v)in VOID or key(v).endswith('_door')for v in values[1:])
                    def component(roots):
                        reachable={q for q in roots if walking(q)};todo=deque(reachable)
                        while todo:
                            q=todo.popleft()
                            for vx,vz in((1,0),(-1,0),(0,1),(0,-1)):
                                target=q[0]+vx,q[1],q[2]+vz
                                if x0<=target[0]<=x1 and z0<=target[2]<=z1 and target not in reachable and walking(target):reachable.add(target);todo.append(target)
                        return reachable
                    roots=[tuple(chosen[-1]['landing'])]if chosen else[tuple(q)for row in p.routes for q in row['feet_local']if q[1]==low+1 and x0<=q[0]<=x1 and z0<=q[2]<=z1]
                    if roots:
                        reachable=component(roots)
                        approaches=[q for q in approaches if q in reachable]
                        if not approaches:continue
                    upper=component([landing]);upper_level=levels[floor+1]
                    goals=[q for q in p.original_BE_points|p.original_functional_nonBE_points if x0<=q[0]<=x1 and z0<=q[2]<=z1 and 1+max((v for v in levels if v<q[1]),default=base)==upper_level+1]
                    if any(not any(abs(q[0]-v[0])+abs(q[2]-v[2])<=3 for v in upper)for q in goals):continue
                    flight=face,cells,landing,approaches[0];break
                if flight:break
            if flight:break
        if flight is None:break
        face,cells,landing,approach=flight
        for x,y,z in cells:
            for yy in range(low+1,y):
                if yy==low+3:p.put(x,yy,z,'minecraft:spruce_wood',axis='x'if VEC[face][0]else'z',role='actual transverse timber stringer articulating the taller stair carriage')
                else:p.put(x,yy,z,'chipped:boxed_dark_oak_planks',role='real enclosed stair carriage')
            p.put(x,y,z,'minecraft:dark_oak_stairs',facing=face,half='bottom',shape='straight',waterlogged=False,role='ordinary four-riser real interior stair')
            for yy in(y+1,y+2):p.put(x,yy,z,'minecraft:air',role='literal normal stair headroom');p.body.add((x,yy,z))
            p.stairs.append((x,y,z))
        p.reserve(title+' lower stair approach',[approach]);p.reserve(title+' upper stair landing',[landing])
        chosen.append({'kind':'native ordinary stair','risers':rise,'floor':floor,'blocks':[list(q)for q in cells],'lower_approach':list(approach),'landing':list(landing)})
    if len(chosen)==storeys-1:p.vertical.extend(chosen);return
    # This is a PURE source recipe transaction, never a world rollback. A
    # failed partial staircase must not consume the entire narrow wing and
    # make its independent normal ladder impossible.
    for name,value in source_before.items():setattr(p,name,value)
    for x,z,face in[(x,z,face)for face in FACES for x in range(x0+1,x1)for z in range(z0+1,z1)]:
        dx,dz=VEC[face];back=(x-dx,z-dz)
        if back not in boundary(rectangle(x0,z0,x1,z1)):continue
        top=levels[-1]+2;shaft={(x,y,z)for y in range(base+1,top+1)}
        if any(q in p.fixed or q in p.body or q in p.route_floor_points for q in shaft):continue
        backing={(back[0],y,back[1])for y in range(base+1,top)}
        if any(q in p.fixed or q in p.body or key(p.blocks.get(q,'minecraft:air'))in VOID for q in backing):continue
        for q in sorted(backing):
            p.put(*q,'minecraft:dark_oak_wood',axis='y',role='real continuous barked full-vanilla-timber service-ladder backing post')
            p.backing_points.add(q)
        for y in range(base+1,top):p.put(x,y,z,'minecraft:ladder',facing=face,waterlogged=False,role='real attached narrow service ladder to the complete upper floors')
        p.put(x,top,z,'minecraft:air',role='service ladder clear upper arrival head')
        p.vertical.append({'kind':'native supported service ladder','shaft':[list(q)for q in sorted(shaft)],'floor_count':storeys,'base':base,'floor_levels':levels,'source_only_native_use_pending':True})
        return
    raise UserError('No complete normal vertical access fits without touching inherited fixtures: '+title)


def join_masses(p):
    """Two new outer walls receive real openings; conserved fixtures never move."""
    for i,a in enumerate(p.mass_fields):
        for j,b in enumerate(p.mass_fields[:i]):
            joins=[]
            for x,z in sorted(a):
                for dx,dz in((1,0),(-1,0),(0,1),(0,-1)):
                    if(x+dx,z+dz)in b:joins.append(((x,z),(x+dx,z+dz)))
            if not joins:continue
            for la in p.floor_levels[i]:
              for lb in p.floor_levels[j]:
                if abs(la-lb)>2:continue
                if la!=lb:
                    lo,hi=min(la,lb),max(la,lb);rise=hi-lo
                    linked=False
                    for a0,b0 in sorted(joins,key=lambda pair:(abs(pair[0][0]-(min(x for x,z in a)+max(x for x,z in a))/2)+abs(pair[0][1]-(min(z for x,z in a)+max(z for x,z in a))/2),pair)):
                        low,high=(a0,b0)if la<lb else(b0,a0);dx,dz=high[0]-low[0],high[1]-low[1]
                        below=(low[0]-dx,lo+1,low[1]-dz);above=(high[0]+dx,hi+1,high[1]+dz)
                        if not p.open_cell(below)or not p.open_cell(above):continue
                        touched={(low[0],y,low[1])for y in range(lo+1,hi+3)}|{(high[0],y,high[1])for y in range(hi if rise==2 else hi+1,hi+3)}
                        if any(q in p.fixed or q in p.body or q in p.backing_points or q in p.route_floor_points for q in touched):continue
                        for q in touched:p.put(*q,'minecraft:air',role='literal headroom at a staggered-floor inner joint')
                        first=(low[0],lo+1,low[1]);steps=[first]
                        if rise==2:steps.append((high[0],hi,high[1]))
                        face=next(f for f,v in VEC.items()if v==(dx,dz))
                        for q in steps:
                            p.put(*q,'minecraft:dark_oak_stairs',facing=face,half='bottom',shape='straight',waterlogged=False,role='real ordinary short stair joining unequal annex floor levels')
                            p.stairs.append(q)
                            for h in(1,2):p.body.add((q[0],q[1]+h,q[2]))
                        p.reserve('Staggered-floor lower arrival',[below]);p.reserve('Staggered-floor upper arrival',[above])
                        p.vertical.append({'kind':'native ordinary stair','risers':rise,'link_between_masses':[i,j],
                          'blocks':[list(q)for q in steps],'lower_approach':list(below),'landing':list(above)})
                        linked=True;break
                    continue
                y=la+1
                candidates=[]
                for a0,b0 in joins:
                    q=[(a0[0],yy,a0[1])for yy in(y,y+1,y+2)]+[(b0[0],yy,b0[1])for yy in(y,y+1,y+2)]
                    if any(t in p.fixed or t in p.backing_points or t in p.body for t in q):continue
                    candidates.append((a0,b0))
                if not candidates:continue
                mid=candidates[len(candidates)//2]
                for x,z in mid:
                    for yy in(y,y+1,y+2):p.put(x,yy,z,'minecraft:air',role='actual open inner joint through two unequal new masses')
                p.reserve('Open connected mass joint',[(x,y,z)for x,z in mid])


def outer_windows(p,box,base,storeys,mass_index,levels=None):
    x0,z0,x1,z1=box
    for floor,level in enumerate(levels or[base+k*4 for k in range(storeys)]):
        y=level+1
        for face,points in(
          ('north',[(x,z0)for x in range(x0+2,x1-1,4)]),('south',[(x,z1)for x in range(x0+1,x1-1,4)]),
          ('west',[(x0,z)for z in range(z0+2,z1-1,4)]),('east',[(x1,z)for z in range(z0+1,z1-1,4)])):
            dx,dz=VEC[face];tx,tz=(1,0)if dz else(0,1)
            for x,z in points:
                if(x+dx,z+dz)in p.footprint:continue # a joined inner wall is not an outside facade
                width=1 if min(x1-x0,z1-z0)<4 else 2
                window_cells=[(x+n*tx,y+h,z+n*tz)for n in range(width)for h in(0,1)]
                if any(q in p.fixed or q in p.body or q in p.backing_points or q in p.entry_door_states for q in window_cells):continue
                projected=[(x+n*tx+dx,y+2,z+n*tz+dz)for n in range(-1,width+1)]
                knees=[(x+n*tx+dx,y+1,z+n*tz+dz)for n in(-1,width)]
                if any(not p.permitted(q)or q in p.body or q in p.entry_door_states or q in p.entry_clearance_points for q in projected+knees):continue
                # Don't plant a fake window directly against an inherited
                # opaque cupboard or a real internal post.
                inside=[(a-dx,b,c-dz)for a,b,c in window_cells]
                if any(q in p.fixed and key(p.fixed[q])not in VOID and not key(p.fixed[q]).startswith('mcwwindows:')for q in inside):continue
                p.casement(x,y,z,face,width=width,height=2)
                if floor:
                    # A real projecting supported upper window-box remains
                    # above ground circulation and outside other/core models.
                    sill=(x+dx,y-2,z+dz);pot=(x+dx,y-1,z+dz)
                    if all(p.permitted(q)and q not in p.body and q not in p.fixed for q in(sill,pot)):
                        p.slab(*sill,'dark_oak',role='actual upper window-box floor attached at the room floor edge')
                        p.put(*pot,POTS[(mass_index+floor)%len(POTS)],role='contained actual modded coastal flower at an inhabited upper casement')
                        p.supports.append((pot,sill))


def grounded_entry(p,box,base,street,all_columns):
    x0,z0,x1,z1=box;choices=[];components={}
    def interior_component(start):
        if start in components:return components[start]
        seen={start};todo=deque([start])
        while todo:
            q=todo.popleft()
            for dx,dz in((1,0),(-1,0),(0,1),(0,-1)):
                target=q[0]+dx,q[1],q[2]+dz
                if x0<=target[0]<=x1 and z0<=target[2]<=z1 and target not in seen and p.open_cell(target):seen.add(target);todo.append(target)
        for q in seen:components[q]=len(seen)
        return len(seen)
    for face,points in(('north',[(x,z0)for x in range(x0+1,x1)]),('south',[(x,z1)for x in range(x0+1,x1)]),('west',[(x0,z)for z in range(z0+1,z1)]),('east',[(x1,z)for z in range(z0+1,z1)])):
        dx,dz=VEC[face]
        for x,z in points:
            inside=(x-dx,base+1,z-dz);outside=(x+dx,base,z+dz)
            door={(x,base+1,z),(x,base+2,z)}
            if door&set(p.fixed)or not p.open_cell(inside)or not p.permitted(outside):continue
            if(outside[0],outside[2])in p.footprint or(outside[0],outside[2])in p.other_columns:continue
            wx,wz=outside[0]+p.origin[0],outside[2]+p.origin[2]
            score=min((abs(wx-a)+abs(wz-b)for a,b in street),default=999)
            # Retained real cupboards can enclose a tiny facade alcove. The
            # principal door must enter the actual occupied room, not merely
            # the closest two empty cells on the street-facing wall.
            choices.append((-interior_component(inside),score,x,z,face,inside,outside))
    if not choices:raise UserError('No genuine ground entry fits the approved mass without a conserved fixture collision')
    _,street_distance,x,z,face,inside,outside=min(choices)
    p.door(x,base+1,z,face);p.reserve('Ground entry inner landing',[inside])
    expected=intended_entry_states(p.registry,[p.entries[-1]])
    if any(p.blocks.get(q)!=value for q,value in expected.items()):raise UserError('A genuine normally openable lower/upper entry could not be authored')
    p.entry_door_states.update(expected)
    p.put(*outside,'minecraft:dark_oak_stairs',facing={'north':'south','south':'north','east':'west','west':'east'}[face],half='bottom',shape='straight',waterlogged=False,role='real half-step threshold up to the approved raised floor')
    p.entry_threshold_points.add(outside)
    p.entry_clearance_points.update((outside[0],base+h,outside[2])for h in(1,2))
    # A deep header and anchored high knee create a genuine recessed portal.
    dx,dz=VEC[face];tx,tz=(1,0)if dz else(0,1)
    for n in(-1,0,1):p.beam(x+n*tx,base+4,z+n*tz,'x'if tx else'z',role='actual deep grounded portal head')
    for n in(-1,1):
        q=x+n*tx+dx,base+3,z+n*tz+dz
        if p.permitted(q):p.put(*q,'mythrais:curved_corbel_dark_oak',facing=face,shape=0,role='small carved supported entry knee')
    sx,sz=x+2*tx+dx,z+2*tz+dz;back=(sx-dx,base+3,sz-dz)
    if p.permitted((sx,base+3,sz))and(sx,base+3,sz)not in p.body and key(p.blocks.get(back,'minecraft:air'))not in VOID:
        p.sign(sx,base+3,sz,face,[p.name,p.spec['program'].title(),'Rooms & Working Trade','Tortuga waterfront'])
        p.backing_points.add(back)
    p.entries[-1].update(mass_ground_floor=base,outer_step=list(outside),real_street_distance_source_only=street_distance)


def intended_entry_states(registry,entries,origin=(0,0,0)):
    """Literal original normal door recipe, in caller-selected coordinates."""
    result={};inward={'north':'south','south':'north','west':'east','east':'west'}
    for entry in entries:
        x,y,z=entry['local'];face=inward[entry['outward']]
        for dy,half in((0,'lower'),(1,'upper')):
            q=x+origin[0],y+dy+origin[1],z+origin[2]
            value=state(registry,'mcwdoors:dark_oak_cottage_door',facing=face,half=half,hinge='left',open=False,powered=False)
            if q in result and result[q]!=value:raise UserError('Two entry recipes disagree on one physical door cell')
            result[q]=value
    return result


def audit_entry_states(registry,entries,field,origin=(0,0,0)):
    expected=intended_entry_states(registry,entries,origin)
    wrong=[q for q,v in expected.items()if field.get(q)!=v]
    if wrong:raise UserError('Entry metadata must resolve to both genuine matching door halves: '+str(wrong[:8]))
    return {'real_matching_door_pairs':len(expected)//2,'literal_lower_upper_states_checked':len(expected),'source_only_native_use_pending':True}


def room_candidates(p,cells,y):
    edge=boundary(cells);out=[]
    for x,z in sorted(cells):
        q=x,y,z
        if(x,z)in edge or q in p.fixed or q in p.body or not p.open_cell(q):continue
        # A real furnished edge bay, not an arbitrary chair in a traffic lane.
        if not any((x+dx,z+dz)in edge for dx,dz in((1,0),(-1,0),(0,1),(0,-1))):continue
        out.append(q)
    return out


def fixture_backings(p):
    """A conserved real wall fixture receives a new rooted physical backing."""
    for q,value in sorted(p.fixed.items()):
        ident=key(value);props=properties(value)
        if ident.split(':',1)[-1].startswith('potted_'):
            below=q[0],q[1]-1,q[2]
            if key(p.blocks.get(below,'minecraft:air'))in VOID:
                mass=next((i for i,c in enumerate(p.mass_fields)if(q[0],q[2])in c),None)
                if mass is None:raise UserError('A conserved planter has no actual new owned sill location')
                base=max((v for v in p.floor_levels[mass]if v<q[1]),default=p.mass_floors[mass])
                for y in range(base+1,q[1]):
                    if(q[0],y,q[2])in p.fixed:raise UserError('Do not replace an unrelated fixed state for an inherited planter')
                    p.put(q[0],y,q[2],'minecraft:dark_oak_planks',role='real new rooted planter sill beneath an unchanged conserved plant')
                    p.backing_points.add((q[0],y,q[2]))
            p.supports.append((q,below));continue
        if not(ident.endswith('_wall_sign')or ident=='supplementaries:item_shelf'or ident.endswith('_shelf')):continue
        face=props.get('facing')
        if face not in VEC:continue
        dx,dz=VEC[face];back=q[0]-dx,q[1],q[2]-dz
        if key(p.blocks.get(back,'minecraft:air'))in VOID:
            mass=next((i for i,c in enumerate(p.mass_fields)if(back[0],back[2])in c),None)
            if mass is None:raise UserError('A conserved wall fixture has no new owned structural backing location')
            base=max((v for v in p.floor_levels[mass]if v<q[1]),default=p.mass_floors[mass])
            for y in range(base+1,q[1]+1):
                if(back[0],y,back[2])not in p.fixed:
                    p.beam(back[0],y,back[2],'y',role='real rooted new backing for conserved native wall furnishing')
                    p.backing_points.add((back[0],y,back[2]))
        # A backing already supplied by the new wall is just as real and
        # necessary as a newly inserted post; later openings must retain it.
        p.backing_points.add(back)
        p.supports.append((q,back))


def walking_graph(p):
    """Discrete floor walking plus explicit ordinary vertical-route witnesses."""
    graph={}
    for cells,levels,mass in zip(p.mass_fields,p.floor_levels,p.spec['masses']):
        for level in levels:
            y=level+1
            for x,z in cells:
                q=x,y,z
                if p.open_cell(q):graph.setdefault(q,set())
    for q in graph:
        for dx,dz in((1,0),(-1,0),(0,1),(0,-1)):
            r=q[0]+dx,q[1],q[2]+dz
            if r in graph:graph[q].add(r)
    for row in p.vertical:
        if row['kind']=='native ordinary stair':
            a,b=tuple(row['lower_approach']),tuple(row['landing'])
            if a not in graph or b not in graph:raise UserError('A real stair lacks actual lower/upper walking arrivals')
            graph[a].add(b);graph[b].add(a)
        else:
            shaft=row['shaft'];x,z=shaft[0][0],shaft[0][2];ends=[]
            for level in row['floor_levels']:
                y=level+1
                neighbors=[(x+dx,y,z+dz)for dx,dz in((0,-1),(1,0),(0,1),(-1,0))if(x+dx,y,z+dz)in graph]
                if not neighbors:raise UserError('A normal service ladder needs a clear supported exit on every real floor')
                # The actual ladder column admits every clear adjacent exit,
                # including the opposite side of a narrow landing. Choosing
                # one arbitrary first neighbor would falsely disconnect an
                # otherwise ordinary enter/climb/exit path.
                ends.append(neighbors)
                for a in neighbors:
                    for b in neighbors:
                        if a!=b:graph[a].add(b)
            for lower,upper in zip(ends,ends[1:]):
                for a in lower:
                    for b in upper:graph[a].add(b);graph[b].add(a)
    return graph


def reserve_circulation(p):
    """Reserve paths before new furniture so it cannot silently trap a room."""
    graph=walking_graph(p);roots=[]
    for entry in p.entries:
        q=tuple(entry['local']);dx,dz=VEC[entry['outward']];inner=q[0]-dx,q[1],q[2]-dz
        if inner in graph:roots.append(inner)
    if not roots:raise UserError('The real entry has no inner walking support/body')
    parent={q:None for q in roots};todo=deque(roots)
    while todo:
        q=todo.popleft()
        for r in sorted(graph[q]):
            if r not in parent:parent[r]=q;todo.append(r)
    goals=[]
    for i,(cells,base,mass)in enumerate(zip(p.mass_fields,p.mass_floors,p.spec['masses'])):
        cx=sum(x for x,z in cells)/len(cells);cz=sum(z for x,z in cells)/len(cells)
        for floor,level in enumerate(p.floor_levels[i]):
            y=level+1;candidates=[q for q in parent if q[1]==y and(q[0],q[2])in cells]
            if not candidates:raise UserError('A complete approved occupied mass/floor has no ordinary connected entry/vertical access: '+str((p.name,i,floor)))
            goals.append(min(candidates,key=lambda q:(abs(q[0]-cx)+abs(q[2]-cz),q)))
    for point in p.original_BE_points|p.original_functional_nonBE_points:
        masses=[i for i,c in enumerate(p.mass_fields)if(point[0],point[2])in c]
        if not masses:raise UserError('Conserved native fixture escaped approved compound')
        base=p.mass_floors[masses[0]];feet=1+max((v for v in p.floor_levels[masses[0]]if v<point[1]),default=base)
        candidates=[q for q in parent if q[1]==feet and abs(q[0]-point[0])+abs(q[2]-point[2])<=3]
        if not candidates:raise UserError('A conserved native fixture has no connected nearby visiting point: '+str((p.name,p.world(point),feet+p.origin[1])))
        goals.append(min(candidates,key=lambda q:(abs(q[0]-point[0])+abs(q[2]-point[2]),q)))
    reserve=set()
    for goal in goals:
        q=goal
        while q is not None:reserve.add(q);q=parent[q]
    # Vertical graph edges have their own real staircase/ladder witnesses;
    # only literal same-floor head/body points are cleared/reserved here.
    p.reserve('Connected actual room and conserved-fixture visiting routes',sorted(reserve))
    p.circulation={'reachable_floor_nodes_before_new_furniture':len(parent),'reserved_supported_feet':len(reserve),
                   'mass_floor_visiting_points':[list(q)for q in goals],'source_only_native_use_pending':True}


def furnished_bays(p,cells,base,storeys,program,mass_index,levels=None):
    program_stations={'charts':('minecraft:cartography_table','minecraft:lectern'),
      'archive':('minecraft:lectern','minecraft:cartography_table'),'cloth':('minecraft:loom','minecraft:crafting_table'),
      'inn':('minecraft:smoker','minecraft:crafting_table'),'hardware':('minecraft:smithing_table','minecraft:anvil'),
      'cooper':('minecraft:crafting_table','minecraft:stonecutter'),'fish':('minecraft:smoker','minecraft:water_cauldron')}
    for floor,level in enumerate(levels or[base+k*4 for k in range(storeys)]):
        y=level+1;candidates=room_candidates(p,cells,y)
        # Separate concise, purposeful scenes in each actual wing. Existing
        # moved furnishings stay literal and reduce new stock requirements.
        selected=[]
        for q in candidates:
            if all(abs(q[0]-v[0])+abs(q[2]-v[2])>=3 for v in selected):selected.append(q)
            if len(selected)>=5:break
        if not selected:
            service_nook(p,cells,y,program,mass_index,floor)
            continue
        used=[]
        for n,q in enumerate(selected):
            x,yy,z=q
            if floor and n==0:
                # A genuine two-part plain bed, not a decorative model/POI
                # assumption. Both parts are new, supported and off routes.
                face=next((f for f in FACES if(x+VEC[f][0],yy,z+VEC[f][1])in candidates and(x+VEC[f][0],yy,z+VEC[f][1])not in p.fixed),None)
                if face:p.bed(x,yy,z,face);used.append((q,'real household bed'));continue
            if n<2:
                ident=program_stations.get(program,('minecraft:crafting_table','minecraft:barrel'))[n%2]
                props={}
                if ident in('minecraft:smoker','minecraft:furnace'):props={'facing':'south','lit':False}
                elif ident in('minecraft:loom','minecraft:stonecutter','minecraft:anvil'):props={'facing':'south'}
                elif ident=='minecraft:lectern':props={'facing':'south','has_book':False,'powered':False}
                elif ident=='minecraft:water_cauldron':props={'level':3}
                elif ident=='minecraft:barrel':props={'facing':'up','open':False}
                p.put(*q,ident,role='real '+program+' working station, ordinary native behavior',**props)
                used.append((q,'actual '+program+' work station'))
            elif n==2:
                p.put(*q,'handcrafted:dark_oak_desk',facing='south',color='brown',waterlogged=False,role='real trade-order and household writing desk')
                p.put(x,yy+1,z,'handcrafted:stackable_book',facing='south',books=3,seed=1+(mass_index*5+floor)%20,role='small real trade/household books on the actual desk')
                used.append((q,'writing desk and actual books'))
            elif n==3:
                p.put(*q,'minecraft:barrel',facing='up',open=False,role='new ordinary native-default household/trade stock, no invented contents')
                p.put(x,yy+1,z,'minecraft:potted_fern',role='contained little actual fern on the stock top');used.append((q,'native-default stock and supported plant'))
            else:
                p.put(*q,'handcrafted:dark_oak_chair',facing='north',color='brown',waterlogged=False,role='real small resting and reading chair');used.append((q,'actual resting chair'))
        # Clear visiting points face the actual modeled furniture, never a
        # blank scene or a fake copied inventory.
        standing=[(x,y,z)for x,z in sorted(cells)if(x,y,z)in p.body and p.open_cell((x,y,z))]
        if standing and used:
            target=used[0][0];point=min(standing,key=lambda q:abs(q[0]-target[0])+abs(q[2]-target[2]))
            p.rooms.append({'name':p.spec['name']+' — '+('upper household'if floor else program+' workroom')+' '+str(mass_index+1),
                            'mass':mass_index,'floor':floor,'local_feet':list(point),'actual_objects':[{'position':list(q),'purpose':role,'expected_state':p.blocks[q]}for q,role in used]})
            p.scene_points.append(point)


def service_nook(p,cells,y,program,mass_index,floor):
    """A one-cell aisle gets a real backed wall counter, never floor clutter."""
    standing=[(x,y,z)for x,z in sorted(cells)if(x,y,z)in p.body and p.open_cell((x,y,z))]
    if not standing:raise UserError('Even a tiny service floor needs an actual connected clear visiting point')
    # An already conserved real object may provide this small room's purpose.
    retained=[q for q in p.fixed if(q[0],q[2])in cells and y<=q[1]<=y+2 and key(p.fixed[q])not in VOID and not key(p.fixed[q]).endswith('_door')]
    for q in sorted(retained):
        visits=[v for v in standing if abs(v[0]-q[0])+abs(v[2]-q[2])<=2]
        if not visits:continue
        p.rooms.append({'name':p.name+' — conserved small service bay '+str(mass_index+1),'mass':mass_index,'floor':floor,
          'local_feet':list(visits[0]),'actual_objects':[{'position':list(q),'purpose':'literal conserved working/storage furnishing; actual native tags remain separate','expected_state':p.blocks[q]}]})
        p.scene_points.append(visits[0]);return
    stations={'charts':'minecraft:cartography_table','archive':'minecraft:bookshelf','cloth':'minecraft:loom',
              'inn':'minecraft:barrel','hardware':'minecraft:smithing_table','cooper':'minecraft:crafting_table','fish':'minecraft:smoker'}
    candidates=[]
    for x,z in sorted(boundary(cells)):
        for face,(dx,dz)in VEC.items():
            visit=x+dx,y,z+dz;q=x,y,z;top=x,y+1,z;back=(x-dx,y+1,z-dz);lowback=(x-dx,y,z-dz)
            if visit not in standing or (x-dx,z-dz)in cells:continue
            if any(v in p.fixed or v in p.body or v in p.backing_points for v in(q,top)):continue
            if any(key(p.blocks.get(v,'minecraft:air')).startswith(('mcwwindows:','mcwdoors:'))or key(p.blocks.get(v,'minecraft:air')).endswith('_door')for v in(q,top)):continue
            if key(p.blocks.get(q,'minecraft:air'))in VOID or key(p.blocks.get((x,y-1,z),'minecraft:air'))in VOID:continue
            if not all(p.permitted(v)and v not in p.body and(v not in p.fixed or key(p.blocks[v])not in VOID)for v in(back,lowback)):continue
            candidates.append((abs(x-(min(a for a,b in cells)+max(a for a,b in cells))/2)+abs(z-(min(b for a,b in cells)+max(b for a,b in cells))/2),x,z,face,visit,q,top,back,lowback))
    if not candidates:raise UserError('No physically backed service niche fits this tiny occupied floor without touching a route or conserved fixture')
    _,x,z,face,visit,q,top,back,lowback=min(candidates)
    for v in(lowback,back):
        if key(p.blocks.get(v,'minecraft:air'))in VOID:p.beam(*v,'y',role='actual projecting rooted back of a recessed narrow service niche')
        p.backing_points.add(v)
    ident=stations.get(program,'minecraft:crafting_table');props={}
    if ident in('minecraft:loom','minecraft:smoker'):props={'facing':face}
    if ident=='minecraft:smoker':props['lit']=False
    if ident=='minecraft:barrel':props={'facing':face,'open':False}
    p.put(*q,ident,role='actual accessible recessed '+program+' service counter, replacing only new wall infill',**props)
    p.put(*top,POTS[(mass_index+floor)%len(POTS)],role='real contained plant on the backed full-block service counter')
    p.supports.append((top,q));p.backing_points.add(q)
    p.rooms.append({'name':p.name+' — narrow '+program+' service nook '+str(mass_index+1),'mass':mass_index,'floor':floor,
      'local_feet':list(visit),'actual_objects':[{'position':list(q),'purpose':'real accessible '+program+' counter','expected_state':p.blocks[q]},
        {'position':list(top),'purpose':'contained actual plant on full-block counter','expected_state':p.blocks[top]}]})
    p.scene_points.append(visit)


def ceiling_details(p,cells,base,storeys,box,levels=None):
    x0,z0,x1,z1=box
    levels=list(levels or[base+k*4 for k in range(storeys)])
    for floor,level in enumerate(levels):
        y=levels[floor+1]-1 if floor+1<len(levels)else level+3
        for z in range(z0+2,z1,4):
            for x in range(x0+1,x1):
                if(x,y,z)not in p.fixed and(x,y,z)not in p.body:p.slab(x,y,z,'mangrove',role='visible shallow warm mahogany-toned coffer rib in a human-scale furnished room')
        for x,z in((x0+2,z0+2),(x1-2,z1-2),((x0+x1)//2,(z0+z1)//2)):
            q=x,y,z
            if x0<x<x1 and z0<z<z1 and q not in p.fixed and q not in p.body and(x,y+1,z)not in p.body and(x,y+1,z)not in p.fixed:
                if p.put(x,y+1,z,'chipped:nailed_dark_oak_log',axis='x',role='actual small ceiling light mount'):
                    p.put(x,y,z,'minecraft:lantern',hanging=True,waterlogged=False,role='small warm actual-emission room lantern')
                    p.supports.append(((x,y,z),(x,y+1,z)))


def pitched_roof(p,box,base,family,end,*,axis='x',half_hip=False):
    """Closed opposing pitches with one union skin and actual framed ends."""
    from tools.artistic_eastern_roof_volume import compose_roof
    return compose_roof(p,box,base,'offset halfhip'if half_hip else'closed gable',
        force_kind='halfhip'if half_hip else'gable',force_axis=axis,family=family)


def roof_geometry(p,box,base,intent):
    from tools.artistic_eastern_roof_volume import compose_roof,articulate_endwalls
    geometry=compose_roof(p,box,base,intent)
    x0,z0,x1,z1=box;axis='x'if x1-x0<=z1-z0 else'z'
    wall_box=x0+1,z0+1,x1-1,z1-1
    for i,mass in enumerate(p.spec['masses']):
        if p.local_box(mass)!=wall_box:continue
        if not hasattr(p,'endwall_relief'):p.endwall_relief=[]
        p.endwall_relief.extend(articulate_endwalls(p,wall_box,p.floor_levels[i],axis=axis))
        break
    return geometry


def build(registry,spec,stock,other_columns,street,index=0):
    p=Compound(registry,spec,stock,other_columns,index)
    for i,mass in enumerate(spec['masses']):
        box=p.local_box(mass);cells=rectangle(*box);base=mass['floor_y']-p.origin[1];stories=mass['storeys']
        offsets=mass.get('occupied_floor_offsets',[k*4 for k in range(stories)])
        if len(offsets)!=stories or offsets[0]!=0 or any(not 4<=b-a<=6 for a,b in zip(offsets,offsets[1:])):raise UserError('Reviewed exact floor levels required')
        levels=[base+k for k in offsets];top=levels[-1]+4
        p.mass_fields.append(cells);p.mass_floors.append(base);p.floor_levels.append(levels);p.top_levels.append(top)
        p.clear_new_room(cells,base,top-base)
        for level in levels+[top]:p.floor(cells,level)
        for low,high in zip(levels,levels[1:]+[top]):p.walls(cells,low+1,high,PANELS[(index+i)%len(PANELS)])
        for level in levels+[top]:p.ring(cells,level)
        # Only the actual building perimeter receives a rooted plinth, never
        # a broad parcel platform or shoreline fill.
        for x,z in boundary(cells):
            along_x=(x-1,z)in cells and(x+1,z)in cells
            p.put(x,base-1,z,'minecraft:stone_bricks'if along_x else'minecraft:cobbled_deepslate',role='rooted narrow actual building plinth')
    fixture_backings(p)
    join_masses(p)
    for i,(mass,cells,base)in enumerate(zip(spec['masses'],p.mass_fields,p.mass_floors)):
        box=p.local_box(mass);stories=mass['storeys']
        grounded_entry(p,box,base,street,other_columns)
        select_climber(p,box,base,stories,spec['name']+' wing'+str(i+1),p.floor_levels[i])
        outer_windows(p,box,base,stories,i,p.floor_levels[i])
    reserve_circulation(p)
    for i,(mass,cells,base)in enumerate(zip(spec['masses'],p.mass_fields,p.mass_floors)):
        box=p.local_box(mass);stories=mass['storeys']
        ceiling_details(p,cells,base,stories,box,p.floor_levels[i])
        furnished_bays(p,cells,base,stories,spec['program'],i,p.floor_levels[i])
    for i,mass in enumerate(spec['masses']):
        box=p.local_box(mass);x0,z0,x1,z1=box;base=p.top_levels[i]
        roof=mass['roof']
        p.active_roof_ground=p.mass_fields[i]
        geometry=roof_geometry(p,(x0-1,z0-1,x1+1,z1+1),base,roof)
        p.roof_sections.append({'mass':i,'actual_approved_roof_intent':roof,'geometry':geometry,'base':base})
        p.active_roof_ground=None
    # Normal native joins derive only NEW shapes; copied current native states
    # are not reinterpreted from a truncated room capsule.
    original=dict(p.fixed);derivations=canonical_joins(p)
    for q,value in original.items():p.blocks[q]=value
    p.join_derivations=[r for r in derivations if tuple(r['position'])not in original]
    return p


def validate(p):
    if any(p.blocks.get(q)!=value for q,value in p.fixed.items()):raise UserError('Conserved actual furnishing/native data state changed')
    entries=audit_entry_states(p.registry,p.entries,p.blocks)
    for q,back in p.supports:
        if key(p.blocks.get(back,'minecraft:air'))in VOID:raise UserError('Actual carved fitting/light has no literal backing')
    for q in p.body:
        value=p.blocks.get(q,'minecraft:air')
        if key(value)not in VOID and not key(value).endswith('_door'):raise UserError('Actual new walking body obstructed')
    if set(p.tags)&set(p.fixed):raise UserError('New architectural tags must never replay retained native block entities')
    graph=walking_graph(p)
    required={(i,floor)for i,mass in enumerate(p.spec['masses'])for floor in range(mass['storeys'])}
    actual={(r['mass'],r['floor'])for r in p.rooms if r.get('actual_objects')}
    if required-actual:raise UserError('Every actual occupied mass/floor needs real furnished objects, including narrow service landings')
    for room in p.rooms:
        if tuple(room['local_feet'])not in graph:raise UserError('A furnished scene has no real clear supported source visiting point')
        for obj in room['actual_objects']:
            if p.blocks.get(tuple(obj['position']))!=obj['expected_state']:raise UserError('Later geometry replaced a real furnished scene object')
    solid={q for q,v in p.blocks.items()if key(v)not in VOID}
    rooted={(x,base-1,z)for cells,base in zip(p.mass_fields,p.mass_floors)for x,z in boundary(cells)if(x,base-1,z)in solid}
    todo=deque(rooted)
    while todo:
        q=todo.popleft()
        for dx,dy,dz in((1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1)):
            r=q[0]+dx,q[1]+dy,q[2]+dz
            if r in solid and r not in rooted:rooted.add(r);todo.append(r)
    if solid-rooted:raise UserError('A source ornament/furnishing/roof is not joined to a real building plinth: '+str(sorted(solid-rooted)[:5]))
    proof=require_material_rule(p.blocks,p.name+' complete approved compound')
    return {'complete_material_rule':proof,'approved_ground_columns':len(p.footprint),'mass_count':len(p.spec['masses']),
            'furnished_scenes':len(p.rooms),'ordinary_stair_blocks':len(p.stairs),'vertical_routes':p.vertical,'actual_entry_states':entries,
            'preserved_actual_BE_positions':len(p.original_BE_points),'preserved_functional_nonBE_positions':len(p.original_functional_nonBE_points),'preserved_all_actual_fixed_states':len(p.fixed),
            'circulation':p.circulation,'all_source_solids_connected_to_proposed_plinths':True,
            'actual_substrate_after_retirement_still_required':True,'source_only':True,'native_walk_model_survival_art_acceptance':False}


def current_archive_field(terrain,p,zinc):
    """Actual stopped states remain distinct from the future moved/retired state."""
    before={};supports={};substrates=[];pending=[];began=time.monotonic()
    for i,q in enumerate(sorted((p.world(q)for q in p.blocks),key=lambda q:(q[0]//16,q[2]//16,q[1],q[0],q[2]))):
        value=terrain.state(*q)
        if value is None:raise UserError('A complete architectural target is UNKNOWN in the actual current archive')
        before[q]=value
        if i%256==0:reader_budget()
        if time.monotonic()-began>45:raise UserError('Finite45s compound current-field read exceeded')
    for i,mass in enumerate(p.spec['masses']):
        top=mass['floor_y']-1
        for x,z in sorted(p.mass_fields[i]):
            wx,wz=x+p.origin[0],z+p.origin[2];stack=[];stable=False
            for y in range(top,max(-65,top-32),-1):
                value=terrain.state(wx,y,wz)
                if value is None:raise UserError('UNKNOWN actual footing is not future dry land authority')
                stack.append((wx,y,wz,value));ident=key(value)
                if ident in GRAVITY and'waterlogged=true'not in value:continue
                stable=(ident in STABLE_NATURAL or ident=='create:zinc_ore'and zinc['factory_class']=='net/minecraft/world/level/block/Block')and'waterlogged=true'not in value
                break
            for xx,yy,zz,value in stack:supports[xx,yy,zz]=value
            row={'mass':i,'world_column':[wx,wz],'current_top':top,'first_non_gravity':list(stack[-1]),'current_literal_natural_stack_qualified':stable}
            if not stable:pending.append(row)
            substrates.append(row)
    actual_BEs=[q for q in before if q in terrain.entities]
    return before,supports,{'actual_archive_cells':len(before),'actual_BE_positions':[list(q)for q in sorted(actual_BEs)],
      'current_BE_tags_not_replayed_or_declared_complete':True,'current_footing_columns':substrates,
      'post_retirement_footing_requalification_required':True,'current_non_natural_footings_pending_review':pending,
      'actual_before_is_not_future_after_move_or_retirement':True}


def source_batch(home,output,ids=FIRST_TEN,*,checkpoint_id=None,checkpoint_sha=None):
    home=Path(home).resolve();reserve=guard(4*MIB,64*MIB);reader_budget()
    if home.parent!=Path('D:/A World for Two/staging/world-tests').resolve():raise UserError('Owned private artistic home only')
    output=Path(output).absolute()
    if output.exists()or output.parent!=home/'staging':raise UserError('New owned proposal directory only')
    layout=checked(home,LAYOUT,8*MIB);stock,custody=contexts(home,layout);registry=read_json(home/'dashboard/settlement/registry.json')
    terrain=None;cp=None;zinc=None
    if checkpoint_id is not None or checkpoint_sha is not None:
        cp=read_json(home/'dashboard/settlement/backup-receipt.json')
        if not cp.get('verified')or(cp.get('id'),cp.get('sha256'))!=(checkpoint_id,checkpoint_sha)or'stopped'not in cp.get('scope','').lower():raise UserError('Exact current authenticated stopped checkpoint required')
        terrain=NorthTerrain(home,cp,registry);zinc=verify_zinc_factory(home)
    specs={r['id']:deepcopy(r)for r in layout['buildings']if r['actual_building_floor_columns_xz']}
    allocation=checked(home,ALLOCATION,2*MIB)
    source_owners={}
    for row in allocation['room_allocations']:
        b=row['source_bounds_xyz']
        for x in range(b[0],b[3]+1):
            for y in range(b[1],b[4]+1):
                for z in range(b[2],b[5]+1):source_owners.setdefault((x,y,z),set()).add(row['id'])
    if len(source_owners)>100000:raise UserError('Finite complete original source-capture mask exceeded')
    if allocation['architecture_height_contract']['tin-whistle']['retained_room_floors']!=[64,69,74]:raise UserError('Exact reviewed Tin Whistle floor contract required')
    tin=specs['tin-whistle'];primary=tin['masses'][0]
    if(primary['floor_y'],primary['storeys'])!=(64,3):raise UserError('The raised Tin Whistle must preserve its approved three-storey ground mass')
    primary['occupied_floor_offsets']=[0,5,10];primary['reviewed_upper_ceiling_and_roof_raise']=2
    if not 1<=len(ids)<=12 or len(set(ids))!=len(ids)or set(ids)-set(specs)or'bridge-cooper'in ids:raise UserError('Explicit at most12 nonempty compounds, excluding Grand’s Keel')
    all_fields={k:set(map(tuple,b['actual_building_floor_columns_xz']))for k,b in specs.items()}
    protected_models,protected_refs=preservation(home,registry)
    if any(cells&protected_models for cells in all_fields.values()):
        # The original owner-approved ground masses must themselves remain
        # intact. Only new roof/window projections are clipped by this skirt.
        bad=[k for k,v in all_fields.items()if v&protected_models]
        raise UserError('An approved main floor now touches protected original/core model custody: '+str(bad))
    street={tuple(q)for row in layout['street_network']for q in row['all_walk_columns_xz']}
    documents={};results=[];held=[];began=time.monotonic()
    for n,ident in enumerate(ids):
        other=set().union(*(v for k,v in all_fields.items()if k!=ident))|protected_models
        try:
            p=build(registry,specs[ident],stock[ident],other,street,list(specs).index(ident));proof=validate(p)
        except (UserError,ValueError) as exc:
            held.append({'building_id':ident,'reason':str(exc),'architecture_emitted':False});continue
        delta={p.world(q):value for q,value in p.blocks.items()if q not in p.fixed}
        full={p.world(q):value for q,value in p.blocks.items()}
        actual=None
        if terrain is not None:
            try:observed,supports,actual=current_archive_field(terrain,p,zinc)
            except BaseException:terrain.close();raise
            known_source_BEs={tuple(q)for row in allocation['room_allocations']for q in row['expected_source_BE_positions']}
            actual['current_BE_positions_not_in_any_reviewed_source_capsule']=[q for q in actual['actual_BE_positions']if tuple(q)not in known_source_BEs]
            for suffix,field,label in(('actual-current-blockstates-VERIFY-ONLY',observed,'ACTUAL STOPPED CURRENT BLOCK STATES ONLY — not a future after-move baseline'),
                                       ('actual-current-supports-VERIFY-ONLY',supports,'ACTUAL STOPPED CURRENT FOOTING STACKS ONLY — requalify after real room moves/retirement')):
                doc=native_payload(registry,field,checkpoint_sha,label);doc.update(construction_forbidden=True,verification_only=True,historical_after_any_new_operation=True)
                documents[ident+'-'+suffix+'.json']=(json.dumps(doc,separators=(',',':'))+'\n').encode()
            for suffix,field,label,new_tags in(('architecture-PROSPECTIVE-FORBIDDEN',delta,'PROSPECTIVE ARCHITECTURE ONLY — requires genuine after-move/retirement native preimage',p.tags),
                                              ('full-after-PROSPECTIVE-VERIFY-ONLY',full,'PROSPECTIVE COMPLETE ARCHITECTURE STATE CONTEXT — retained native NBT requires actual independent custody',p.tags),
                                              ('normal-joins-PROSPECTIVE-ONLY',{q:v for q,v in delta.items()if key(v)not in VOID},'PROSPECTIVE NORMAL JOINS OF NEW TARGETS ONLY — no old stock replay',{})):
                tags={p.world(q):snbt(v)for q,v in new_tags.items()}
                doc=native_payload(registry,field,checkpoint_sha,label,tags=tags);doc.update(construction_forbidden=True,verification_only=True,prospective_not_observed=True,requires_after_move_retirement_actual_preimage=True)
                documents[ident+'-'+suffix+'.json']=(json.dumps(doc,separators=(',',':'))+'\n').encode()
        record={'format':'awft-eastern-compound-architecture-SOURCE-ONLY:1','building_id':ident,'name':p.name,
          'approved_layout_sha256':LAYOUT[1],'source_sha256':digest(Path(__file__)),'origin':list(p.origin),
          'status':'PROSPECTIVE SOURCE AFTER REAL CONSERVED MOVES AND OWNED OLD-SHELL RETIREMENT; NEVER ACTUAL CURRENT AIR',
          'blocks_PROSPECTIVE_DELTA':[[*q,v]for q,v in sorted(delta.items())],
          'complete_expected_state_context_ONLY':[[*q,v]for q,v in sorted(full.items())],
          'new_tags_ONLY':[{'position':list(p.world(q)),'nbt':snbt(v)}for q,v in sorted(p.tags.items())],
          'required_native_completed_moves':stock[ident]['moves'],
          'required_original_source_captures_before_architecture':sorted(set().union(*(source_owners.get(q,set())for q in delta))),
          'original_capture_scope':'Every full original room snapshot including AIR intersected by any architecture write must be captured and conserved first; incoming rooms alone are insufficient',
          'required_owned_NONBE_shell_retirements':[{'position':list(p.world(q)),'exact_old_state':v}for q,v in sorted(p.retire.items())],
          'preserved_fixed_native_states':[{'position':list(p.world(q)),'state':v}for q,v in sorted(p.fixed.items())],
          'retained_native_BE_positions':[list(p.world(q))for q in sorted(p.original_BE_points)],
          'retained_functional_nonBE_positions':[list(p.world(q))for q in sorted(p.original_functional_nonBE_points)],
          'old_tags_or_items_written':0,'unknown_current_difference_cells_written':0,
          'approved_ground_floor_columns_xz':specs[ident]['actual_building_floor_columns_xz'],'masses':specs[ident]['masses'],
          'rooms':p.rooms,'routes':p.routes,'entries':p.entries,'supports':p.supports,'roof_sections':p.roof_sections,
          'canonical_NEW_join_derivations':p.join_derivations,'preserved_state_suppressions':dict(p.suppressed),'proof':proof,
          'actual_current_archive_field':actual,'actual_current_archive_checkpoint_id':checkpoint_id,'actual_current_archive_checkpoint_sha256':checkpoint_sha,
          'construction_forbidden':True,'native_actions':0,'world_writes':0,
          'required_next_gates':['Genuine completed conserved native moves, including current full native class/slots/components',
            'Exact authorized NONBE shell retirement; no old grid left as accepted architecture',
            'Fresh genuine stopped/native after-move+retirement preimages for every DELTA/support/body cell',
            'Actual approved core/bridge/zipline/coast/current flora and living population keepouts',
            'Explicit parent admission, native placement/normal joins/full state + all retained NBT verification',
            'Actual full exterior/street/interior images and ordinary stair/door/access use; no count-based art acceptance']}
        data=(json.dumps(record,separators=(',',':'))+'\n').encode()
        if len(data)>8*MIB:raise UserError('Finite8MiB one compound source exceeded')
        name=ident+'-SOURCE-ONLY.json';documents[name]=data
        results.append({'id':ident,'targets':len(delta),'full_context':len(full),'rooms':len(p.rooms),'mass_count':len(p.spec['masses']),
                        'required_moves':len(stock[ident]['moves']),'preserved_BE_positions':len(p.original_BE_points),'source_sha256':hashlib.sha256(data).hexdigest()})
        reader_budget()
        if time.monotonic()-began>120:raise UserError('Finite120s architectural source batch expired')
    raw_sources=terrain.snapshot.sources if terrain is not None else[]
    if terrain is not None:terrain.close()
    manifest={'format':'awft-eastern-compound-source-batch:1','created':utcnow(),'source_sha256':digest(Path(__file__)),
      'layout':{'relative':LAYOUT[0],'sha256':LAYOUT[1]},'custody':custody,'requested_ids':list(ids),'results':results,'held':held,
      'scope':{'approved_nonempty_compounds':len(specs),'all_approved_masses':sum(len(s['masses'])for s in specs.values()),'full_remaining_scope_in_progress':True},
      'construction_forbidden':True,'native_actions':0,'world_writes':0,'reserve_guard':reserve,
      'actual_current_archive_checkpoint_id':checkpoint_id,'actual_current_archive_checkpoint_sha256':checkpoint_sha,'actual_archive_sources':raw_sources,
      'protected_original_and_core_model_sources':protected_refs,'protected_model_skirt_columns':len(protected_models),
      'files':{n:{'bytes':len(v),'sha256':hashlib.sha256(v).hexdigest()}for n,v in documents.items()}}
    documents['manifest.json']=(json.dumps(manifest,separators=(',',':'))+'\n').encode()
    if sum(map(len,documents.values()))>64*MIB:raise UserError('Finite64MiB source batch cap exceeded')
    output.mkdir()
    for name,data in documents.items():(output/name).open('xb').write(data)
    return {'folder':str(output),'manifest_sha256':digest(output/'manifest.json'),'compounds':len(results),'held':held,'native_actions':0}


if __name__=='__main__':
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('--home',required=True);a.add_argument('--output',required=True);a.add_argument('--ids',nargs='*');a.add_argument('--checkpoint-id');a.add_argument('--checkpoint-sha')
    args=a.parse_args();print(json.dumps(source_batch(args.home,args.output,args.ids or FIRST_TEN,checkpoint_id=args.checkpoint_id,checkpoint_sha=args.checkpoint_sha),indent=2))
