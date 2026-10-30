"""Width-correct fresh rooms with genuinely open, small trade projections.

Narrow former enclosed wings are physically redesigned, not renamed bedrooms.
All outputs are prospective Source; actual3E and human/current authority remain
separate mandatory native admission gates.
"""
from __future__ import annotations
import argparse,json,time
from copy import deepcopy
from pathlib import Path

from control_room.common import UserError,digest,read_json
from tools import artistic_eastern_compound_sprint as e
from tools.artistic_city_planning_map import EAST,read as layout
from tools.artistic_eastern_first_three_detail import exact_sources
from tools.artistic_eastern_fresh_interiors import width_review,BUILT
from tools.artistic_fisherman_interior import snbt
from tools.artistic_materials import require_material_rule
from tools.artistic_tortuga_variants import rotated_state
from tools.artistic_west_r2_frontage import Frontage,canonical_joins,rect
from tools.playtest import guard

MIB=1024**2
NEXT=('worn-book','bridge-customs','crooked-inn','lampblack','moon-branch','nail-drift','bridge-cooper','keel-store')


def design(spec):
    new=deepcopy(spec);rooms=[];projections=[];changes=[]
    for i,mass in enumerate(spec['masses']):
        a,b,c,d=mass['bounds_xz'];width=min(c-a-1,d-b-1);area=(c-a-1)*(d-b-1)
        if width<3:
            projections.append(dict(deepcopy(mass),original_mass=i))
            changes.append({'original_mass':i,'before':'narrow enclosed occupied wing','after':'separate genuinely open trade bays, each at most6m long; no bedroom/normal-room claim'})
            continue
        m=deepcopy(mass)
        if i and width<=4 and area<=24 and m['storeys']>1:
            m['storeys']=1;m.pop('occupied_floor_offsets',None)
            changes.append({'original_mass':i,'before':'tiny multi-storey annex requiring stair through most floor','after':'one-storey real normal workroom with full3x3 core; household remains in broad main house'})
        rooms.append(m)
    if not rooms:raise UserError('Every compound needs a real broad enclosed primary room')
    new['masses']=rooms
    new['actual_building_floor_columns_xz']=[list(q)for q in sorted(set().union(*(e.rectangle(*m['bounds_xz'])for m in rooms)))]
    return new,projections,changes


def small_bay(registry,width,length,program,variant,*,horizontal=False):
    p=Frontage(registry,(0,0,0));p.owner='Open '+program+' trade projection';cells=rect(0,0,width-1,length-1)
    p.floor(cells,0)
    for x,z in cells:
        for y in(1,2,3):p.put(x,y,z,'minecraft:air')
    for x,z in((0,0),(width-1,0),(0,length-1),(width-1,length-1)):
        p.put(x,-1,z,'minecraft:cobbled_deepslate',role='small actual masonry foot beneath the open frame')
        for y in(1,2,3):p.put(x,y,z,'dawnoftimebuilder:charred_spruce_timber_frame_pillar',axis='y',role='three-high rooted open trade-bay corner')
    for z in(0,length-1):
        for x in range(width):p.put(x,4,z,'minecraft:stripped_dark_oak_log'if x==width-1 else'minecraft:dark_oak_wood',axis='y'if x==width-1 else'x',role='supported shallow end tie with a real upright corner cap')
    roof='minecraft:deepslate_tile_stairs'if horizontal else'minecraft:polished_blackstone_brick_stairs'
    cap='minecraft:deepslate_tile_slab'if horizontal else'minecraft:polished_blackstone_brick_slab'
    ridge='chipped:nailed_spruce_log'if horizontal else'chipped:nailed_dark_oak_log'
    if variant%3==0:
        for x in range(width):
            for z in range(length):p.put(x,4+x//2,z,roof,facing='east',half='bottom',shape='straight',waterlogged=False,role='quiet continuous charcoal lean-to roof over a tiny open trade bay')
    elif variant%3==1:
        for z in range(length):
            for x in range(width):
                if x in(0,width-1):p.put(x,4,z,roof,facing='east'if x==0 else'west',half='bottom',shape='straight',waterlogged=False,role='short continuous charcoal open-bay pitched eave')
                else:
                    p.put(x,4,z,ridge,axis='z',role='real full ridge support tied to the end frame')
                    p.put(x,5,z,cap,type='bottom',waterlogged=False,role='shallow true small ridge cap')
    else:
        for z in(0,length-1):
            for x in range(1,width-1):p.put(x,3,z,'minecraft:brown_wool'if z==0 else'minecraft:dark_oak_slab',**({}if z==0 else{'type':'top','waterlogged':False}),role='small muted canvas back pennant or a shallow opposite tie')
    path=[(1,1,z)for z in range(2,length-1)];p.reserve('Open exterior trade-bay visiting path',path)
    station={'charts':'minecraft:cartography_table','archive':'minecraft:cartography_table','cloth':'minecraft:loom','hardware':'minecraft:smithing_table','cooper':'minecraft:crafting_table','fish':'minecraft:crafting_table','inn':'minecraft:crafting_table'}.get(program,'minecraft:crafting_table')
    p.put(1,1,1,station,**({'facing':'south'}if station=='minecraft:loom'else{}),role='real ordinary working station; no invented inventory')
    p.put(width-1,1,1,('fishofthieves:potted_white_plumeria','fishofthieves:potted_tropical_red_fern','regions_unexplored:potted_blue_lupine')[variant%3],role='real contained small trade-counter greenery on full deck')
    p.put(0,1,length-2,'handcrafted:dark_oak_bench',facing='east',shape='single',color='brown',waterlogged=False,role='small work/rest perch facing the open frontage')
    p.put(1,3,length-1,'minecraft:lantern',hanging=True,waterlogged=False,role='small warm task light supported by the actual end tie')
    canonical_joins(p);require_material_rule(p.blocks,p.owner+' complete independent floor/frame/roof')
    return p


def projected_geometry(registry,masses,program):
    field={};records=[];visits=[]
    for n,m in enumerate(masses):
        a,b,c,d=m['bounds_xz'];floor=m['floor_y'];horizontal=c-a>d-b;short=d-b+1 if horizontal else c-a+1;long=c-a+1 if horizontal else d-b+1
        start=0;bay=0
        while long-start>=4:
            length=min((4,6,5)[(n+bay)%3],long-start)
            if long-start-length in(1,2,3):length=min(6,long-start)
            p=small_bay(registry,short,length,program,n+bay,horizontal=horizontal)
            def point(q):
                x,y,z=q
                return(a+start+length-1-z,floor+y,b+x)if horizontal else(a+x,floor+y,b+start+z)
            turn=1 if horizontal else 0
            # Former tall enclosed slivers really become low open features.
            # Explicit AIR clears their prospective volume; Root's current
            # owner-released-AI retirement remains an independent authority.
            for x in range(a,c+1):
                for z in range(b,d+1):
                    for y in range(floor+1,floor+min(24,m['storeys']*4+7)):
                        field.setdefault((x,y,z),'minecraft:air')
            for q,v in p.blocks.items():field[point(q)]=rotated_state(registry,v,turn)
            # Floorboards/joists follow the same WORLD axes as the main rooms,
            # not a rotated color pattern. Real edge sleepers and transverse
            # joists keep coherent construction seams at their actual joints.
            deck={point((x,0,z))for x,z in rect(0,0,short-1,length-1)}
            for x,y,z in deck:
                if(x,y,z-1)not in deck or(x,y,z+1)not in deck:name='minecraft:dark_oak_planks';props={}
                elif(x-1,y,z)not in deck or(x+1,y,z)not in deck:name='minecraft:stripped_spruce_wood';props={'axis':'z'}
                elif x%4==0:name='chipped:cross_laced_spruce_planks';props={}
                else:name='minecraft:spruce_planks';props={}
                field[x,y,z]=e.state(registry,name,**props)
            vs=[list(point(q))for q in p.routes[0]['positions']];visits+=vs
            records.append({'original_mass':m['original_mass'],'bay':bay,'kind':('open roofed work porch','open small pitched market bay','open canvas trade frame')[(n+bay)%3],
              'outside_dimensions':[short,length],'maximum_length':6,'open_sides_at_least':2,'enclosed_normal_room':False,'bedroom':False,'visitor_feet_world':vs,'station':program,'new_contained_plants':1})
            start+=length+1;bay+=1
    return field,records,visits


def prepare(home,ids=NEXT):
    home=Path(home).resolve()
    if not home.is_relative_to(Path('D:/A World for Two/staging/world-tests').resolve()):raise UserError('Owned private Source only')
    reserve=guard(4*MIB,64*MIB);reg=read_json(home/'dashboard/settlement/registry.json');master=layout(home,EAST);specs={b['id']:b for b in master['buildings']if b['masses']}
    if not 1<=len(ids)<=12 or set(ids)&BUILT or set(ids)-set(specs):raise UserError('Finite unbuilt-only batch')
    all_fields={k:set(map(tuple,b['actual_building_floor_columns_xz']))for k,b in specs.items()};street={tuple(q)for r in master['street_network']for q in r['all_walk_columns_xz']};kept,actual_refs=exact_sources(home);core,core_refs=e.preservation(home,reg)
    out=home/'staging'/('eastern-fresh-open-wings-'+str(time.time_ns()));out.mkdir();records=[];held=[];written=0
    for ident in ids:
        try:
            spec,projection_masses,changes=design(specs[ident]);others=set().union(*(v for k,v in all_fields.items()if k!=ident))|core
            p=e.build(reg,spec,{'fixed':{},'bes':set(),'retire':{}},others,street,list(specs).index(ident));proof=e.validate(p);width=width_review(p)
            full={p.world(q):v for q,v in p.blocks.items()};extra,features,visits=projected_geometry(reg,projection_masses,spec['program']);suppressed=[]
            protected={p.world(q)for q in p.body|p.route_floor_points|p.backing_points}
            for q,v in extra.items():
                if q in kept or(q[0],q[2])in core or((q[0],q[2])in others and(q[0],q[2])not in all_fields[ident]):continue
                if q in protected or(q in full and e.key(full[q])not in e.VOID):
                    if full.get(q)!=v:suppressed.append(list(q))
                    continue
                full[q]=v
            for q in tuple(full):
                if q in kept:
                    if(q[0],q[2])in set(map(tuple,spec['actual_building_floor_columns_xz']))and full[q]!=kept[q]:raise UserError('Main room conflicts with actual exempt East3')
                    del full[q]
            # A Source feature's real visiting body cannot be occupied by a
            # roof/body from an adjacent higher room. Hold, never fake a route.
            for x,y,z in visits:
                if any(e.key(full.get((x,y+h,z),'minecraft:air'))not in e.VOID for h in(0,1))or e.key(full.get((x,y-1,z),'minecraft:air'))in e.VOID:raise UserError('Open trade bay lacks an actual clear founded visiting point')
            tags=[{'position':list(p.world(q)),'nbt':snbt(v)}for q,v in sorted(p.tags.items())if p.world(q)not in kept]
            material=require_material_rule(full,p.name+' complete normal rooms and real open projections')
            source={'format':'awft-eastern-fresh-direct-SOURCE:2','id':ident,'building_id':ident,'name':p.name,'origin':list(p.origin),'fresh_direct_construction':True,'width_review':width,
              'complete_expected_state_context_ONLY':[[*q,v]for q,v in sorted(full.items())],'blocks_PROSPECTIVE_DELTA':[[*q,v]for q,v in sorted(full.items())],'new_tags_ONLY':tags,
              'masses':spec['masses'],'approved_ground_floor_columns_xz':spec['actual_building_floor_columns_xz'],'original_approved_ground_mass_count':len(specs[ident]['masses']),
              'actual_open_projection_features':features,'open_projection_visiting_positions_world':visits,'actual_geometric_redesigns':changes,'room_geometry_has_not_been_renamed_to_waive_width':True,
              'rooms':p.rooms,'routes':p.routes,'entries':p.entries,'supports':p.supports,'roof_sections':p.roof_sections,'geometry_proof':proof,'complete_material_rule':material,
              'preserved_fixed_native_states':[],'retained_native_BE_positions':[],'required_native_completed_moves':[],'old_tags_or_items_written':0,
              'actual3_native_proofs':actual_refs,'actual_current_preimage_provided':False,'normal_room_routes_and_roofs_retained_over_projections':len(suppressed),
              'native_actions':0,'world_writes':0,'construction_forbidden':True,'source_sha256':digest(Path(__file__)),
              'required_next_gates':['Actual recovery snapshot and current human/core/landmark/mechanism exclusion','Owner-released old AI rooms only; no old stock replay/capture requirement','Root fresh native before/retire/place/settle/full','Real exterior/interior/open-feature visual and ordinary use review']}
            raw=(json.dumps(source,separators=(',',':'))+'\n').encode();written+=len(raw)
            if written>64*MIB:raise UserError('Finite64MiB batch output')
            name=ident+'-SOURCE-ONLY.json';(out/name).open('xb').write(raw);records.append({'id':ident,'files':{'SOURCE-ONLY':{'path':(out/name).relative_to(home).as_posix(),'sha256':digest(out/name),'bytes':len(raw)}},'fresh_direct_construction':True,'width_review':{'hard_minimum_3_passed':True,'comfortable_target':5},'counts':{'rooms':len(p.rooms),'open_projections':len(features),'blocks':len(full)}})
        except(UserError,ValueError)as ex:held.append({'id':ident,'reason':str(ex),'architecture_emitted':False})
    index={'format':'awft-eastern-fresh-width-source-index:1','fresh_direct_construction':True,'source_sha256':digest(Path(__file__)),'actual_exempt':sorted(BUILT),'compounds':records,'held':held,'native_actions':0,'world_writes':0,'construction_forbidden':True,'reserve_guard':reserve}
    (out/'SOURCE-INDEX.json').open('x',encoding='utf-8').write(json.dumps(index,indent=2)+'\n');return{'folder':str(out),'index_sha256':digest(out/'SOURCE-INDEX.json'),'ready':[r['id']for r in records],'held':held}


if __name__=='__main__':
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('--home',type=Path,required=True);a.add_argument('--ids',nargs='+',default=list(NEXT));v=a.parse_args();print(json.dumps(prepare(v.home,tuple(v.ids)),indent=2))
