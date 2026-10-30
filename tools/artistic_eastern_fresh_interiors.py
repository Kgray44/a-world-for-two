"""Fresh direct eastern interiors: three-block hard width, five preferred.

No old room/capture/stock is replayed. Already-built eastern compounds are
protected. Outputs remain SOURCE until Root's fresh actual admission.
"""
from __future__ import annotations
import argparse,json,time
from copy import deepcopy
from pathlib import Path

from control_room.common import UserError,digest,read_json
from tools import artistic_eastern_compound_sprint as e
from tools.artistic_city_planning_map import EAST,read as layout
from tools.artistic_eastern_first_three_detail import exact_sources
from tools.artistic_fisherman_interior import snbt
from tools.playtest import guard

MIB=1024**2
BUILT={'east-coal','shoal-warden','thin-sail'}
FIRST=('lantern-harbor-inn','net-mender','white-clam','copper-bell','tide-fish','worn-book','crooked-row')


def structural(value):
    name=e.key(value);tail=name.split(':')[-1]
    if name.startswith(('chipped:','mcwwindows:','mcwroofs:','mythrais:curved_corbel')):return True
    if name.startswith('dawnoftimebuilder:'):return not any(n in tail for n in('pot','cup','chair','table','footstool'))
    stones={'stone','cobblestone','mossy_cobblestone','andesite','polished_andesite','diorite','polished_diorite','granite','polished_granite','calcite','terracotta','stone_bricks','mossy_stone_bricks','cobbled_deepslate','deepslate_bricks','tuff','bricks','ladder'}
    return name.startswith('minecraft:')and(tail in stones or tail.endswith(('_log','_wood','_planks','_slab','_stairs','_terracotta','_wall')))


def width_review(p):
    floors=[]
    def run(q,c,dx,dz):
        n=1
        for sign in(-1,1):
            x,z=q
            while(x+sign*dx,z+sign*dz)in c:x+=sign*dx;z+=sign*dz;n+=1
        return n
    for i,cells in enumerate(p.mass_fields):
        inner=cells-e.boundary(cells)
        box=p.local_box(p.spec['masses'][i]);nominal=min(box[2]-box[0]-1,box[3]-box[1]-1)
        if nominal<3:raise UserError('Enclosed normal wing below3 must be physically widened/merged/redesigned; mass '+str(i))
        for f,level in enumerate(p.floor_levels[i]):
            feet=level+1
            free={q for q in inner if not any(structural(p.blocks.get((q[0],y,q[1]),'minecraft:air'))for y in(feet,feet+1))}
            spans={q:min(run(q,free,1,0),run(q,free,0,1))for q in free}
            small={q for q,v in spans.items()if v<3};stair_points=[]
            for route in p.vertical:
                if 'stair'not in route.get('kind','')and'ladder'not in route.get('kind',''):continue
                points=route.get('blocks',route.get('shaft',[]))
                if points and min(q[1]for q in points)-1<=feet<=max(q[1]for q in points)+2:stair_points+=points
            permitted={q for q in small if any(abs(q[0]-s[0])+abs(q[1]-s[2])<=2 for s in stair_points)}
            if small-permitted:raise UserError('Normal structural width below3 outside literal stair feature: '+str((i,f,sorted(small-permitted)[:8])))
            normal=free-permitted
            anchors=[(x,z)for x,z in sorted(normal)if all((x+dx,z+dz)in normal for dx in(0,1,2)for dz in(0,1,2))]
            if not anchors:raise UserError('An ordinary room needs a real3x3 clear core; a stair exception cannot consume the whole wing')
            floors.append({'mass':i,'floor':f,'feet_y':p.origin[1]+feet,'nominal_clear_width':nominal,
              'normal_block_grid_minimum':min(spans[q]for q in normal),'comfortable5_reached_everywhere':all(spans[q]>=5 for q in normal),
              'compact3_or4_design_judgment':any(spans[q]<5 for q in normal),'clear3x3_anchor_world':[anchors[0][0]+p.origin[0],p.origin[1]+feet,anchors[0][1]+p.origin[2]],
              'specific_stair_exception_cells_world':[[x+p.origin[0],p.origin[1]+feet,z+p.origin[2]]for x,z in sorted(permitted)]})
    return {'hard_minimum_3_passed':True,'comfortable_target':5,'five_is_not_universal_hard_constraint':True,
      'method':'Actual two-high Source structural voxel mask, furniture separate; exact normal-room run widths, bounded literal stair/ladder exceptions, real3x3 core per normal floor',
      'floors':floors,'native_collision_walk_and_art_pending':True}


def prepare(home,ids=FIRST):
    home=Path(home).resolve()
    if not home.is_relative_to(Path('D:/A World for Two/staging/world-tests').resolve()):raise UserError('Owned private Source output only')
    reserve=guard(4*MIB,64*MIB);reg=read_json(home/'dashboard/settlement/registry.json');master=layout(home,EAST)
    specs={b['id']:deepcopy(b)for b in master['buildings']if b['masses']}
    if not 1<=len(ids)<=12 or len(set(ids))!=len(ids)or set(ids)-set(specs)or set(ids)&BUILT:raise UserError('Explicit finite unbuilt-only Source subset required')
    all_fields={k:set(map(tuple,b['actual_building_floor_columns_xz']))for k,b in specs.items()};street={tuple(q)for r in master['street_network']for q in r['all_walk_columns_xz']}
    kept,actual_refs=exact_sources(home);core,core_refs=e.preservation(home,reg)
    out=home/'staging'/('eastern-fresh-width-source-'+str(time.time_ns()));out.mkdir();records=[];held=[];written=0
    for ident in ids:
        try:
            spec=specs[ident];others=set().union(*(v for k,v in all_fields.items()if k!=ident))|core
            p=e.build(reg,spec,{'fixed':{},'bes':set(),'retire':{}},others,street,list(specs).index(ident))
            proof=e.validate(p);width=width_review(p);full={p.world(q):v for q,v in p.blocks.items()};omitted=[]
            for q in tuple(full):
                if q not in kept:continue
                if(q[0],q[2])in all_fields[ident]and full[q]!=kept[q]:raise UserError('New main mass conflicts with an actual exempt eastern cell')
                omitted.append(list(q));del full[q]
            tags=[{'position':list(p.world(q)),'nbt':snbt(v)}for q,v in sorted(p.tags.items())if p.world(q)not in kept]
            record={'format':'awft-eastern-fresh-direct-SOURCE:1','id':ident,'building_id':ident,'name':p.name,'origin':list(p.origin),
              'fresh_direct_construction':True,'owner_override':'Old generated furnished room relocation/capture constraints released; only genuinely new default furniture/tags, no old saved NBT replay',
              'width_review':width,'masses':spec['masses'],'approved_ground_floor_columns_xz':spec['actual_building_floor_columns_xz'],
              'complete_expected_state_context_ONLY':[[*q,v]for q,v in sorted(full.items())],'blocks_PROSPECTIVE_DELTA':[[*q,v]for q,v in sorted(full.items())],
              'new_tags_ONLY':tags,'retained_native_BE_positions':[],'preserved_fixed_native_states':[],'required_native_completed_moves':[],
              'rooms':p.rooms,'routes':p.routes,'entries':p.entries,'supports':p.supports,'roof_sections':p.roof_sections,'geometry_proof':proof,
              'accepted3_cells_omitted_not_written':omitted,'actual3_native_proofs':actual_refs,'actual_current_preimage_provided':False,
              'old_tags_or_items_written':0,'native_actions':0,'world_writes':0,'construction_forbidden':True,
              'source_sha256':digest(Path(__file__)),'required_next_gates':['Grand fresh actual current field/retirement of owner-released AI rooms only','Actual3E/core/northlandmarks/human mechanisms/playerdata unchanged','Root exact Native before/support/place/normal/full and actual views']}
            data=(json.dumps(record,separators=(',',':'))+'\n').encode();written+=len(data)
            if written>64*MIB:raise UserError('Finite64MiB Source output exceeded')
            name=ident+'-SOURCE-ONLY.json';(out/name).open('xb').write(data)
            records.append({'id':ident,'name':p.name,'files':{'SOURCE-ONLY':{'path':(out/name).relative_to(home).as_posix(),'sha256':digest(out/name),'bytes':len(data)}},'counts':{'masses':len(spec['masses']),'rooms':len(p.rooms),'blocks':len(full),'new_tags':len(tags)},'fresh_direct_construction':True,'width_review':{'hard_minimum_3_passed':True,'comfortable_target':5}})
        except (UserError,ValueError)as ex:held.append({'id':ident,'reason':str(ex),'architecture_emitted':False})
    index={'format':'awft-eastern-fresh-width-source-index:1','fresh_direct_construction':True,'source_sha256':digest(Path(__file__)),'approved_layout':e.LAYOUT,'actual_exempt':sorted(BUILT),
      'compounds':records,'held':held,'world_writes':0,'native_actions':0,'construction_forbidden':True,'no_actual_before_or_demolition_authority':True,'reserve_guard':reserve}
    (out/'SOURCE-INDEX.json').open('x',encoding='utf-8').write(json.dumps(index,indent=2)+'\n')
    return {'folder':str(out),'index_sha256':digest(out/'SOURCE-INDEX.json'),'ready':[r['id']for r in records],'held':held}


if __name__=='__main__':
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('--home',type=Path,required=True);a.add_argument('--ids',nargs='+',default=list(FIRST));v=a.parse_args();print(json.dumps(prepare(v.home,tuple(v.ids)),indent=2))
