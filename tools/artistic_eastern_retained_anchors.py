"""Fresh eastern rooms around four untouched existing personal/work anchors.

This is Source geometry only. Retained states are verification context, never
placement, retirement, ordinary inventory reset, or replayed block-entity NBT.
"""
from __future__ import annotations
import argparse,json,time
from copy import deepcopy
from pathlib import Path

from control_room.common import UserError,digest,read_json
from tools import artistic_eastern_compound_sprint as e
from tools.artistic_bridge_refinement import flatten
from tools.artistic_city_planning_map import EAST,read as layout
from tools.artistic_eastern_first_three_detail import exact_sources
from tools.artistic_eastern_fresh_interiors import width_review
from tools.artistic_eastern_open_wings import design,projected_geometry
from tools.artistic_fisherman_interior import snbt
from tools.artistic_materials import require_material_rule
from tools.artistic_west_r2_frontage import canonical_joins
from tools.playtest import guard

MIB=1024**2
WITNESS=('staging/retained-existing-bed-job-toolbox-STATE-WITNESS-1793235099816703300.json',
         '3273bd0b507546811209f9c7f489986c41a8ddcac533fe22fc7c39f302760bdf')
ANCHORS={
 'lantern-harbor-inn':{
  (1296,65,-1250):'minecraft:blue_bed[facing=north,occupied=false,part=head]',
  (1296,65,-1249):'minecraft:blue_bed[facing=north,occupied=false,part=foot]',
  (1300,65,-1255):'minecraft:cartography_table'},
 'ropes-pearl':{(1275,64,-1206):'create:brown_toolbox[facing=west,waterlogged=false]'}}


class RetainedCompound(e.Compound):
    """A partial-height toolbox is furnishing, not a walking-floor block."""
    def open_cell(self,q,*,floor=True):
        below=q[0],q[1]-1,q[2]
        if e.key(self.fixed.get(below,'minecraft:air')).startswith('create:')and e.key(self.fixed[below]).endswith('_toolbox'):
            return False
        return super().open_cell(q,floor=floor)


def build(registry,spec,anchors,other_columns,street,index):
    """The existing complete recipe, with local fixture-aware circulation."""
    bes={q for q,v in anchors.items()if e.key(v)!='minecraft:cartography_table'}
    p=RetainedCompound(registry,spec,{'fixed':anchors,'bes':bes,'retire':{}},other_columns,index)
    for mass in spec['masses']:
        box=p.local_box(mass);cells=e.rectangle(*box);base=mass['floor_y']-p.origin[1];stories=mass['storeys']
        offsets=mass.get('occupied_floor_offsets',[k*4 for k in range(stories)])
        if len(offsets)!=stories or offsets[0]!=0 or any(not 4<=b-a<=6 for a,b in zip(offsets,offsets[1:])):raise UserError('Exact ordinary floor levels required')
        levels=[base+k for k in offsets];top=levels[-1]+4
        p.mass_fields.append(cells);p.mass_floors.append(base);p.floor_levels.append(levels);p.top_levels.append(top)
        p.clear_new_room(cells,base,top-base)
        for level in levels+[top]:p.floor(cells,level)
        i=len(p.mass_fields)-1
        for low,high in zip(levels,levels[1:]+[top]):p.walls(cells,low+1,high,e.PANELS[(index+i)%len(e.PANELS)])
        for level in levels+[top]:p.ring(cells,level)
        for x,z in e.boundary(cells):
            along_x=(x-1,z)in cells and(x+1,z)in cells
            p.put(x,base-1,z,'minecraft:stone_bricks'if along_x else'minecraft:cobbled_deepslate',role='rooted actual perimeter plinth, no shoreline platform')
    e.fixture_backings(p);e.join_masses(p)
    for i,(mass,cells,base)in enumerate(zip(spec['masses'],p.mass_fields,p.mass_floors)):
        box=p.local_box(mass);stories=mass['storeys']
        e.grounded_entry(p,box,base,street,other_columns)
        e.select_climber(p,box,base,stories,spec['name']+' wing'+str(i+1),p.floor_levels[i])
        e.outer_windows(p,box,base,stories,i,p.floor_levels[i])
    e.reserve_circulation(p)
    for i,(mass,cells,base)in enumerate(zip(spec['masses'],p.mass_fields,p.mass_floors)):
        box=p.local_box(mass);stories=mass['storeys']
        e.ceiling_details(p,cells,base,stories,box,p.floor_levels[i])
        e.furnished_bays(p,cells,base,stories,spec['program'],i,p.floor_levels[i])
    for i,mass in enumerate(spec['masses']):
        x0,z0,x1,z1=p.local_box(mass);base=p.top_levels[i];p.active_roof_ground=p.mass_fields[i]
        geometry=e.roof_geometry(p,(x0-1,z0-1,x1+1,z1+1),base,mass['roof'])
        p.roof_sections.append({'mass':i,'actual_approved_roof_intent':mass['roof'],'geometry':geometry,'base':base});p.active_roof_ground=None
    original=dict(p.fixed);derivations=canonical_joins(p)
    for q,v in original.items():p.blocks[q]=v
    p.join_derivations=[r for r in derivations if tuple(r['position'])not in original]
    return p


def split_fields(full,anchors,tags):
    """Keep exact anchor context, exclude it from every mutating Source row."""
    if any(full.get(q)!=v for q,v in anchors.items()):raise UserError('An existing anchor state changed or disappeared')
    if any(tuple(r['position'])in anchors for r in tags):raise UserError('No new tag may touch a retained actual anchor')
    return dict(full),{q:v for q,v in full.items()if q not in anchors}


def prepare(home):
    home=Path(home).resolve()
    if not home.is_relative_to(Path('D:/A World for Two/staging/world-tests').resolve()):raise UserError('Owned private Source output only')
    reserve=guard(4*MIB,16*MIB);wpath=home/WITNESS[0]
    if wpath.stat().st_size>64*1024 or digest(wpath)!=WITNESS[1]:raise UserError('The exact finite saved four-state witness is required')
    witness=read_json(wpath);states=flatten(witness)
    if states!={q:v for a in ANCHORS.values()for q,v in a.items()}:raise UserError('Saved state witness differs from reviewed retained anchors')
    reg=read_json(home/'dashboard/settlement/registry.json');master=layout(home,EAST);specs={r['id']:r for r in master['buildings']if r['masses']}
    all_fields={k:set(map(tuple,b['actual_building_floor_columns_xz']))for k,b in specs.items()};street={tuple(q)for r in master['street_network']for q in r['all_walk_columns_xz']}
    core,_=e.preservation(home,reg);kept,actual_refs=exact_sources(home)
    out=home/'staging'/('eastern-retained-anchors-source-'+str(time.time_ns()));out.mkdir();records=[];total=0
    for ident,anchors in ANCHORS.items():
        spec,projections,changes=design(specs[ident])
        others=set().union(*(v for k,v in all_fields.items()if k!=ident))|core
        p=build(reg,spec,anchors,others,street,list(specs).index(ident));proof=e.validate(p);width=width_review(p)
        full={p.world(q):v for q,v in p.blocks.items()};tags=[{'position':list(p.world(q)),'nbt':snbt(v)}for q,v in sorted(p.tags.items())if p.world(q)not in kept]
        extra,features,feature_visits=projected_geometry(reg,projections,spec['program'])
        protected={p.world(q)for q in p.body|p.route_floor_points|p.backing_points|set(p.fixed)}
        for q,v in extra.items():
            if q in kept or(q[0],q[2])in core or((q[0],q[2])in others and(q[0],q[2])not in all_fields[ident]):continue
            if q in protected or(q in full and e.key(full[q])not in e.VOID):continue
            full[q]=v
        for x,y,z in feature_visits:
            if any(e.key(full.get((x,y+h,z),'minecraft:air'))not in e.VOID for h in(0,1))or e.key(full.get((x,y-1,z),'minecraft:air'))in e.VOID:
                raise UserError('A real open trade bay lacks clear supported visiting space')
        visits=[]
        for q,v in anchors.items():
            level=q[1]if e.key(v)!='create:brown_toolbox'else q[1]+1
            candidates=[s for s in p.body if s[1]+p.origin[1]==level and abs(s[0]+p.origin[0]-q[0])+abs(s[2]+p.origin[2]-q[2])==1 and p.open_cell(s)]
            if not candidates:raise UserError('Existing furnishing lacks a literal adjacent connected clear visiting point')
            point=min(candidates);visits.append({'anchor':list(q),'feet_world':list(p.world(point)),'actual_native_use_pending':True})
            if e.key(v)=='create:brown_toolbox':
                if p.local((q[0],q[1]+1,q[2]))in p.body:raise UserError('A partial-height toolbox must not become walking support')
                if any(e.key(full.get((q[0],q[1]+h,q[2]),'minecraft:air'))not in e.VOID for h in(1,2)):raise UserError('Toolbox upper access must remain clear')
        for q in tuple(full):
            if q in kept:
                if full[q]!=kept[q]and(q[0],q[2])in all_fields[ident]:raise UserError('Retained-anchor design conflicts with actual exempt eastern compound')
                del full[q]
        complete,delta=split_fields(full,anchors,tags);material=require_material_rule(complete,p.name+' complete retained-anchor design')
        retained=[{'position':list(q),'state':v,'read_only':True,'never_place_retire_reset_or_load_NBT':True}for q,v in sorted(anchors.items())]
        source={'format':'awft-eastern-fresh-direct-SOURCE:3','id':ident,'building_id':ident,'name':p.name,'origin':list(p.origin),
          'fresh_direct_construction':True,'width_review':width,'complete_expected_state_context_ONLY':[[*q,v]for q,v in sorted(complete.items())],
          'blocks_PROSPECTIVE_DELTA':[[*q,v]for q,v in sorted(delta.items())],'new_tags_ONLY':tags,
          'preserved_fixed_native_states':retained,'retained_native_BE_positions':[list(q)for q,v in sorted(anchors.items())if e.key(v)!='minecraft:cartography_table'],
          'retained_anchor_visiting_points':visits,'required_explicit_adapter_retention':True,
          'masses':spec['masses'],'approved_ground_floor_columns_xz':spec['actual_building_floor_columns_xz'],'rooms':p.rooms,'routes':p.routes,'entries':p.entries,
          'actual_open_projection_features':features,'open_projection_visiting_positions_world':feature_visits,
          'supports':p.supports,'roof_sections':p.roof_sections,'actual_geometric_redesigns':changes,'geometry_proof':proof,'complete_material_rule':material,
          'saved_retained_state_witness':{'path':WITNESS[0],'sha256':WITNESS[1],'actual_saved_checkpoint':witness['actual_saved_checkpoint']},
          'actual3_native_proofs':actual_refs,'actual_current_preimage_provided':False,'old_tags_or_items_written':0,'native_actions':0,'world_writes':0,'construction_forbidden':True,
          'source_sha256':digest(Path(__file__)),'required_next_gates':['Current actual14eastern context and human mechanism protection; independent fresh Native before',
          'Adapter must omit all preserved_fixed_native_states from place/retire/reset/settle and all tag loads; exact states readonly in after',
          'Existing native tags/inventory/ownership remain untouched, no saved NBT supplied','Root native support/place/normal/full and actual walk/use/art review']}
        raw=(json.dumps(source,separators=(',',':'))+'\n').encode();total+=len(raw)
        if total>16*MIB:raise UserError('Finite16MiB Source output exceeded')
        path=out/(ident+'-SOURCE-ONLY.json');path.open('xb').write(raw)
        records.append({'id':ident,'name':p.name,'files':{'SOURCE-ONLY':{'path':path.relative_to(home).as_posix(),'sha256':digest(path),'bytes':len(raw)}},
          'fresh_direct_construction':True,'width_review':{'hard_minimum_3_passed':True,'comfortable_target':5},'counts':{'full_context':len(complete),'prospective_targets':len(delta),'retained_points':len(anchors),'furnished_floor_scenes':len(p.rooms)},'required_explicit_adapter_retention':True})
    index={'format':'awft-eastern-fresh-width-source-index:1','fresh_direct_construction':True,'compounds':records,'held':[],
      'source_sha256':digest(Path(__file__)),'saved_retained_state_witness_sha256':WITNESS[1],'native_actions':0,'world_writes':0,'construction_forbidden':True,'reserve_guard':reserve}
    path=out/'SOURCE-INDEX.json';path.open('x',encoding='utf8').write(json.dumps(index,indent=2)+'\n')
    return {'folder':str(out),'index_sha256':digest(path),'compounds':records,'native_actions':0,'world_writes':0}


if __name__=='__main__':
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('--home',type=Path,required=True);v=a.parse_args();print(json.dumps(prepare(v.home),indent=2))
