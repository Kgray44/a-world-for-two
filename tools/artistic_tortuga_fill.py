"""Fresh stopped-save fields and individually composed western Tortuga infill.

The old coverage/cluster recipes remain immutable. This producer reads the
current stopped checkpoint again, including the already placed headland,
Quill and gravity-safe ground work. It never restores old expected AIR over
new progress, selects lots automatically, places blocks or moves inventory.
"""
from __future__ import annotations
import argparse,hashlib,json,re,time
import math
from collections import Counter
from pathlib import Path

from control_room.common import UserError,digest,read_json
from tools.artistic_north_bank_east import NorthTerrain,native_payload,GROUND,SOFT,NORTH_SOFT,AIR as VOIDS,preservation
from tools.artistic_tortuga_west_ground import mask_inputs,path_to
from tools.artistic_west_coverage import main_fields,components,largest_rectangle
from tools.artistic_west_r2_layout import GEOGRAPHY
from tools.artistic_bridge_refinement import flatten
from tools.artistic_tortuga_frontages import RECIPES,check,key,AIR
from tools.artistic_tortuga_variants import variant,variant_of
from tools.artistic_create_substrate import verify_zinc_factory,qualified_mount
from tools.artistic_materials import require_outdoor_rule
from tools.artistic_zipline_catenary import reader_budget
from tools.playtest import guard

MIB=1024**2
MAX_FIELD_BYTES=32*MIB
MAX_BUNDLE_BYTES=48*MIB
CURRENT=(
 ('headland','staging/tortuga-headland-pair-1793199900323997200/manifest.json','e0031924fe57343bd9630e544979a92fc9e5efec06d6197c46b6279f3f443e0b','complete-after-VERIFY-ONLY.json'),
 ('quill','staging/tortuga-quill-court-1793202602131514100/manifest.json','cb3fe9a2d0e192cd4c562d8a07335daa74989b9ece21df88fd828318e04c7209','complete-after-VERIFY-ONLY.json'),
 ('ground-r2','staging/tortuga-west-ground-R2-1793203969495539000/manifest.json','84424a58479b0f99abb96b9f86ede9263015611eb31a3a3bbd7a8efc91b44247','complete-after-VERIFY-ONLY.json'),
)
BATCHES={
 'half-tide-hook':{
  'buildings':(
   {'recipe':'briny-hearth','turn':0,'name':'Soot & Scone','trade':'Bread • Supper','origin':(1117,63,-1265)},
   {'recipe':'quarter-tide','turn':2,'name':'The Half-Tide','trade':'Music • Ale • Supper','origin':(1118,63,-1253)},
  ),
  'links':(
   ('Bakehouse to tavern, turning around the retained living vegetation',((1115,-1257),(1114,-1255),(1110,-1250),(1111,-1244),(1120,-1242))),
  ),
  'design':'Two close, differently shaped occupied masses; a low long cookhouse and crooked music-house return. The two-wide hooked lane preserves the existing live vegetation; a third net-house was omitted because it would have pinched the actual walking connection.',
  'street_views':(('Bakehouse west frontage from the actual common lane',(1114.5,64,-1255.5),(1121,68,-1258)),('Half-Tide southern façade',(1120.5,64,-1241.5),(1121,68,-1248))),
 },
 'tenon-watch-hook':{
  'buildings':(
   {'recipe':'lost-tide','turn':1,'name':'The Crooked Tenon','trade':'Ship Joinery • Repairs','origin':(1039,63,-1250)},
   {'recipe':'thimble-salt','turn':2,'name':'The Tucked Pennant','trade':'Cloth • Pennants • Repairs','origin':(1051,63,-1252)},
   {'recipe':'gullwatch','turn':0,'name':'Lantern at the Bend','trade':'Lanterns • Coast Charts','origin':(1083,63,-1239)},
  ),
  'links':(
   ('Joiner and tiny pennant-maker around the actual retained stock',((1037,-1247),(1057,-1251))),
   ('Pennant-maker through the retained businesses to the lantern home',((1057,-1251),(1086,-1227))),
  ),
  'design':'A long horizontal joinery wing, opposite-facing compact pennant-maker and tall southern lantern lookout. All step around retained trades and stocks; the small shop and broad low wing meet closely rather than repeating a uniform row.',
  'street_views':(('Joiner west frontage',(1037.5,64,-1246.5),(1045,68,-1247)),('Pennant-maker east frontage',(1058.5,64,-1250.5),(1053,67,-1248)),('Lantern south frontage',(1087.5,64,-1226.5),(1086,70,-1233))),
 },
}


def rich_workscene(p,recipe):
    """Explicit new-recipe additions prompted by the real empty-wall image.

    These positions are for NEW variants only, never a furniture replay over
    the placed originals. Every object takes literal source AIR and a real
    backing/surface; the original furniture, route and wall geometry survive.
    """
    def new(x,y,z,name,*,role,**props):
        if p.blocks.get((x,y,z),AIR)!=AIR:raise UserError('A new authored workscene must not overwrite furniture or architecture: '+str((recipe,x,y,z)))
        p.put(x,y,z,name,role=role,**props)
    def shelf(x,y,z,face,story,*,books=False,top=True):
        dx,dz={'north':(0,-1),'east':(1,0),'south':(0,1),'west':(-1,0)}[face]
        if p.blocks.get((x-dx,y,z-dz),AIR)==AIR:raise UserError('Actual workscene shelf needs real backing')
        new(x,y,z,'handcrafted:dark_oak_shelf',facing=face,shape='single',type=3,role=story)
        p.supports.append({'detail':[x,y,z],'support':[x-dx,y,z-dz],'role':story})
        if top:new(x,y+1,z,'handcrafted:stackable_book'if books else'handcrafted:wood_cup',
            **({'facing':face,'books':3,'seed':7}if books else{'facing':face,'pieces':3,'waterlogged':False}),role=story+' — actual models on shelf')
    if recipe=='briny-hearth':
        new(3,1,1,'handcrafted:dark_oak_drawer',facing='south',shape='single',type=2,role='baker’s low order-slip drawer beside the flour pantry')
        new(3,2,1,'handcrafted:terracotta_bowl',facing='south',pieces=3,waterlogged=False,role='mixing bowls over the order-slip drawer')
        shelf(6,2,6,'west','cookhouse side-wall service vessels')
        new(3,3,1,'minecraft:lantern',hanging=True,waterlogged=False,role='small practical order-counter task lantern')
        p.supports.append({'detail':[3,3,1],'support':[3,4,1],'role':'order light attached to the actual occupied floor above'})
    elif recipe=='quarter-tide':
        new(1,1,5,'farmersdelight:dark_oak_cabinet',facing='east',open=False,role='small native-default supper-service cabinet, no invented contents')
        shelf(1,2,5,'east','tavern’s shelf of ordinary serving cups')
        shelf(7,2,4,'west','music-house bills and supper-account ledgers',books=True)
        new(7,3,5,'mcwlights:tavern_wall_lantern',facing='west',role='warm small service-return wall light')
        p.supports.append({'detail':[7,3,5],'support':[8,3,5],'role':'service lantern mounted to the real lower side wall'})
    elif recipe=='netmender':
        new(1,1,3,'handcrafted:dark_oak_drawer',facing='east',shape='single',type=2,role='net-worker’s real small cork and order drawer')
        new(1,2,3,'handcrafted:terracotta_bowl',facing='east',pieces=3,waterlogged=False,role='cork and fitting-sorting vessels above the drawer')
        shelf(1,2,5,'east','net patterns and repair-account shelf',books=True)
        new(6,3,4,'mcwlights:tavern_wall_lantern',facing='west',role='small warm tackle-bench task light')
        p.supports.append({'detail':[6,3,4],'support':[7,3,4],'role':'tackle light mounted on the actual outer wall'})
    elif recipe=='lost-tide':
        new(2,1,7,'farmersdelight:dark_oak_cabinet',facing='north',open=False,role='real floor-mounted cupboard below the original fitting-ledger shelf')
        for y in(1,2,3):new(2,y,8,'minecraft:stripped_dark_oak_log',axis='y',role='grounded backing post for the ship-plan shelf and ledger rack')
        p.supports.append({'detail':[2,2,7],'support':[2,2,8],'role':'original new-recipe ledger shelf now has its actual grounded backing'})
        shelf(1,2,5,'east','joiner’s plans and repair records',books=True)
        new(2,3,1,'mcwlights:tavern_wall_lantern',facing='south',role='small practical ship-plan task light')
        p.supports.append({'detail':[2,3,1],'support':[2,3,0],'role':'plan light mounted on the actual shaped north wall'})
    elif recipe=='gullwatch':
        new(1,1,6,'handcrafted:dark_oak_drawer',facing='east',shape='single',type=2,role='low coast-watch repair drawers beneath the actual wide side casement')
        new(1,2,6,'handcrafted:terracotta_bowl',facing='east',pieces=3,waterlogged=False,role='ordinary fitting-sort bowls on the drawer top')
        shelf(1,2,7,'east','lantern keeper’s order-note rack under its actual ceiling joist',books=True,top=False)
        new(2,3,1,'mcwlights:tavern_wall_lantern',facing='south',role='warm fitting-shop north-wall task light')
        p.supports.append({'detail':[2,3,1],'support':[2,3,0],'role':'fitting light on the real closed north wall'})
    elif recipe=='needlewake':
        new(1,1,5,'farmersdelight:dark_oak_cabinet',facing='east',open=False,role='native-default tailoring patterns and cloth cabinet')
        new(1,2,5,'handcrafted:terracotta_bowl',facing='east',pieces=3,waterlogged=False,role='small vessels of notions above the cutting-side cabinet')
        shelf(1,2,7,'east','properly backed order rack below the low workshop ceiling',books=True,top=False)
        new(3,3,1,'mcwlights:tavern_wall_lantern',facing='south',role='small warm sewing/preparation task light')
        p.supports.append({'detail':[3,3,1],'support':[3,3,0],'role':'sewing light on the actual shaped front wall'})
    p.features.setdefault(p.owner,[]).append('Explicit new workscene wall storage/task light; no old furniture, container NBT or routes removed')
    return p


def modeled(registry,definition):
    states={};tags={};buildings=[];mains=set()
    for row in definition['buildings']:
        source=rich_workscene(RECIPES[row['recipe']](registry),row['recipe'])
        p=variant_of(source,row['recipe'],row['turn'],name=row['name'],trade=row['trade'])
        proof=check(p);origin=tuple(row['origin'])
        world={tuple(q[i]+origin[i]for i in range(3)):s for q,s in p.blocks.items()}
        collisions=[q for q,s in world.items()if q in states and not(s==AIR and states[q]==AIR)]
        if collisions:raise UserError('Actual authored masses/casements collide; change composition: '+str((row['name'],collisions[:6])))
        states.update(world);tags.update({tuple(q[i]+origin[i]for i in range(3)):v for q,v in p.tags.items()})
        fields={(x+origin[0],z+origin[2])for x,z in p.main[p.owner]};mains|=fields
        views=[]
        for room in p.rooms:
            q=room['standing_point'];objects=[]
            for prop in p.props:
                obj=tuple(prop['position']);value=p.blocks.get(obj,AIR);ident=key(value)
                if obj[1]not in(room['floor']+1,room['floor']+2)or ident!=prop['block']:continue
                if not ident.startswith(('handcrafted:','farmersdelight:','minecraft:crafting_table','minecraft:loom','minecraft:cartography_table','minecraft:stonecutter','minecraft:smoker','minecraft:furnace','minecraft:barrel')):continue
                distance=math.dist((q[0]+.5,q[1]+1.6,q[2]+.5),(obj[0]+.5,obj[1]+.6,obj[2]+.5))
                if 2<=distance<=6:objects.append((0 if ident.startswith('minecraft:')else 1,distance,obj,prop['role']))
            if not objects:raise UserError('An actual furnished scene needs a modeled task/furniture target, not a blank-wall camera')
            _,_,obj,story=min(objects)
            views.append({'name':row['name']+' — '+room['name'],'feet':[q[i]+origin[i]+(.5 if i in(0,2)else 0)for i in range(3)],
               'look_at':[obj[0]+origin[0]+.5,obj[1]+origin[1]+.6,obj[2]+origin[2]+.5],'actual_source_object':p.blocks[obj],'story':story})
        buildings.append({**row,'proof':proof,'main_columns_xz':[list(q)for q in sorted(fields)],'variant':p.variant_provenance,'scene_views':views,
          'rooms':[{**r,'world_standing_point':[r['standing_point'][i]+origin[i]for i in range(3)]}for r in p.rooms],
          'entries':[{**r,'world_door':[r['door'][i]+origin[i]for i in range(3)],'world_threshold':[r['outside_step'][i]+origin[i]for i in range(3)]}for r in p.entries]})
    return states,tags,buildings,mains


def private_home(home):
    home=Path(home).resolve()
    if home.parent!=Path('D:/A World for Two/staging/world-tests').resolve():raise UserError('Private artistic source only')
    return home


def stopped(home,checkpoint_id,checkpoint_sha):
    receipt=read_json(home/'dashboard/settlement/backup-receipt.json')
    if receipt.get('verified')is not True or(receipt.get('id'),receipt.get('sha256'))!=(checkpoint_id,checkpoint_sha)or'stopped'not in receipt.get('scope','').lower():raise UserError('Exact current stopped checkpoint required; no automatic old-proof rebind')
    return receipt


def retained_context(home,registry):
    keep,forest,refs=mask_inputs(home)
    heritage,history=preservation(home,registry);refs+=history
    fields,footprints=main_fields(home,registry);refs+=footprints
    for label,relative,sha,filename in CURRENT:
        path=home/relative
        if digest(path)!=sha:raise UserError('Frozen already placed source manifest changed: '+label)
        doc=read_json(path)
        if filename not in doc['files']:raise UserError('Exact complete current source file required: '+label)
        actual=path.parent/filename
        if digest(actual)!=doc['files'][filename]['sha256']:raise UserError('Current complete source bytes changed: '+label)
        keep.update(flatten(read_json(actual)))
        refs.append({'relative':str(actual.relative_to(home)),'sha256':digest(actual),'role':'Retained complete source; never replayed or used as current observed AIR'})
        for b in doc.get('buildings',[]):fields['retained '+b['name']]={tuple(q)for q in b['main_columns_xz']}
    # These labels describe footprint provenance, not native art approval.
    all_mains=set().union(*fields.values())
    return keep,forest,heritage,fields,all_mains,refs


def fresh_field(home,checkpoint_id,checkpoint_sha):
    home=private_home(home);reserve=guard(8*MIB,MAX_FIELD_BYTES);budgets=[reader_budget()]
    receipt=stopped(home,checkpoint_id,checkpoint_sha)
    if digest(home/GEOGRAPHY[0])!=GEOGRAPHY[1]:raise UserError('Historical measured bank locator changed')
    north={tuple(r['xz'])for r in read_json(home/GEOGRAPHY[0])['columns']if r['north_connected']}
    registry=read_json(home/'dashboard/settlement/registry.json')
    keep,forest,heritage,fields,mains,refs=retained_context(home,registry)
    protected_xz={(x,z)for x,y,z in keep if 62<=y<=85}|heritage|forest|mains
    zinc=verify_zinc_factory(home)
    terrain=NorthTerrain(home,receipt,registry);free={};walk={};refused=Counter();began=time.monotonic()
    try:
        for n,(x,z)in enumerate(sorted(north,key=lambda q:(q[0]//16,q[1]//16,q[0],q[1]))):
            if n%256==0:budgets.append(reader_budget())
            if time.monotonic()-began>120:raise UserError('Finite120s current residual reader exceeded')
            col=terrain.column(x,z)
            floor=terrain.state(x,63,z);body=[terrain.state(x,y,z)for y in(64,65)]
            if(x,z)not in mains|heritage|forest and floor is not None and'waterlogged=true'not in floor and key(floor)in GROUND|VOIDS|{'minecraft:polished_andesite','chipped:small_stone_bricks','minecraft:cobbled_deepslate'}:
                good_body=all(v is not None and key(v)in VOIDS|SOFT|NORTH_SOFT and'waterlogged=true'not in v for v in body)
                retained_body=all((x,y,z)not in keep or(keep[x,y,z]==AIR and v==AIR)for y,v in zip((64,65),body))
                retained_floor=(x,63,z)not in keep or keep[x,63,z]==floor
                if good_body and retained_body and retained_floor and not any((x,y,z)in terrain.entities for y in(62,63,64,65)):
                    mount=qualified_mount(terrain.state,x,z,zinc)
                    if mount['stable']:walk[x,z]=[floor,*body]
            if(x,z)in protected_xz:refused['retained_current_future_source_or_route']+=1;continue
            if col['kind']!='dry'or col['surface_y']not in(62,63):refused['not_literal_low_dry_ground']+=1;continue
            states=[terrain.state(x,y,z)for y in range(63,85)]
            if any(v is None or'waterlogged=true'in v for v in states):refused['unknown_or_waterlogged']+=1;continue
            if key(states[0])not in GROUND|VOIDS|SOFT|NORTH_SOFT or any(key(v)not in VOIDS|SOFT|NORTH_SOFT for v in states[1:]):refused['current_solid_tree_or_structure']+=1;continue
            if any((x,y,z)in terrain.entities for y in range(62,85)):refused['existing_block_entity']+=1;continue
            mount=qualified_mount(terrain.state,x,z,zinc)
            if not mount['stable']:refused['first_non_gravity_substrate_not_qualified']+=1;continue
            free[x,z]=[col['surface_y'],col['state'],states[0],mount['first_non_gravity'][1],mount['first_non_gravity'][3]]
        saved=terrain.snapshot.sources
    finally:terrain.close()
    patches=[]
    for i,cells in enumerate(components(free)):
        patches.append({'id':i,'columns':len(cells),'bounds_xz':[min(x for x,z in cells),min(z for x,z in cells),max(x for x,z in cells),max(z for x,z in cells)],'largest_clear_rectangle_DIAGNOSTIC_ONLY':largest_rectangle(cells)})
    doc={'format':'awft-tortuga-fresh-field:1','checkpoint_id':checkpoint_id,'checkpoint_sha256':checkpoint_sha,'source_sha256':digest(Path(__file__)),
         'historical_locator':{'relative':GEOGRAPHY[0],'sha256':GEOGRAPHY[1],'current_authority':False},'north_locator_columns':len(north),
         'retained_current_plus_future_main_columns':len(mains&north),'retained_source_main_footprints':{name:[list(q)for q in sorted(cells)]for name,cells in fields.items()},
         'eligible_columns_READONLY':[[x,z,*values]for(x,z),values in sorted(free.items())],
         'two_high_walk_columns_READONLY':[[x,z,*values]for(x,z),values in sorted(walk.items())],
         'eligible_columns':len(free),'remaining_components':patches,'refused_columns':dict(refused),'retained_sources':refs,'raw_saved_sources':saved,
         'zinc_substrate_factory':zinc,'reserve_guard':reserve,'reader_peak_RSS_bytes':max(b['owned_reader_rss_bytes']for b in budgets),
         'native_actions':0,'world_writes':0,'new_parcel_or_density_acceptance':False,
         'limits':['A measured eligible field is not a house layout or a native placement proof','No existing source, inventory or human change may be removed','Most land must be occupied by distinct inhabited building masses; narrow purposeful lanes are not a substitute for buildings','The historic bank locator is only a geographic limit; every listed current state and native substrate was reread from this checkpoint']}
    raw=(json.dumps(doc,separators=(',',':'))+'\n').encode()
    if len(raw)>MAX_FIELD_BYTES:raise UserError('Finite32MiB current field cap exceeded')
    out=home/'staging'/('tortuga-current-field-'+str(time.time_ns()));out.mkdir();(out/'field-READONLY.json').open('xb').write(raw)
    return {'folder':str(out),'sha256':digest(out/'field-READONLY.json'),'eligible_columns':len(free),'walk_columns':len(walk),'main_columns':len(mains&north),'largest_patches':patches[:6],'native_actions':0}


def route_geometry(states,mains,walk_field,definition):
    walking={q for q in walk_field if q not in mains and all(states.get((q[0],y,q[1]),AIR)==AIR for y in(64,65))}
    lanes={};routes=[]
    for name,points in definition['links']:
        center=[]
        for a,b in zip(points,points[1:]):
            try:segment=path_to(walking,tuple(a),tuple(b))
            except UserError as exc:raise UserError(name+': '+str(exc))from exc
            center+=segment[:-1]
        center.append(tuple(points[-1]));cells=set()
        for i,(x,z)in enumerate(center):
            prev=center[max(i-1,0)];nxt=center[min(i+1,len(center)-1)]
            axis='x'if abs(nxt[0]-prev[0])>=abs(nxt[1]-prev[1])else'z'
            for dx,dz in((0,0),(1,0),(0,1),(1,1)):
                q=x+dx,z+dz;cells.add(q);lanes.setdefault(q,set()).add(axis)
        routes.append({'name':name,'width':2,'columns_xz':[list(q)for q in sorted(cells)],'center_line':[[x+.5,64,z+.5]for x,z in center]})
    return lanes,routes


def lane_materials(states,lane,name):
    # Upper eaves above an alley still belong to their individually checked
    # complete buildings. Combining orthogonal roofs from different homes
    # into a fictitious single outdoor surface would misapply that rule.
    return require_outdoor_rule({q:s for q,s in states.items()if(q[0],q[2])in lane and q[1]in(63,64,65)},name)


def prepare(home,checkpoint_id,checkpoint_sha,field_path,field_sha,batch,*,definition=None,definition_source=None):
    home=private_home(home);reserve=guard(8*MIB,MAX_BUNDLE_BYTES);budgets=[reader_budget()]
    receipt=stopped(home,checkpoint_id,checkpoint_sha);field_path=Path(field_path).resolve()
    if not field_path.is_relative_to(home/'staging')or field_path.stat().st_size>MAX_FIELD_BYTES or digest(field_path)!=field_sha:raise UserError('Exact bounded private current field required')
    field=read_json(field_path)
    if field.get('format')!='awft-tortuga-fresh-field:1'or(field.get('checkpoint_id'),field.get('checkpoint_sha256'))!=(checkpoint_id,checkpoint_sha):raise UserError('This field is historical or belongs to another checkpoint')
    if not re.fullmatch('[a-z0-9-]{1,48}',batch):raise UserError('Exact finite authored batch name required')
    if definition is None:
        if batch not in BATCHES:raise UserError('An explicit individually authored building batch is required')
        definition=BATCHES[batch];definition_source=Path(__file__)
    else:
        definition_source=Path(definition_source).resolve()
        if definition_source.parent!=Path(__file__).resolve().parent or not definition_source.is_file():raise UserError('An additive batch must name its actual repository-owned tools source')
    if not 1<=len(definition.get('buildings',()))<=12:raise UserError('A finite individually authored batch of at most12 buildings is required')
    registry=read_json(home/'dashboard/settlement/registry.json')
    states,tags,buildings,mains=modeled(registry,definition)
    free={tuple(q[:2])for q in field['eligible_columns_READONLY']}
    if not mains<=free:raise UserError('No guessed main floor in water, current object, unknown or unsupported soil: '+str(sorted(mains-free)[:12]))
    keep,forest,heritage,fields,old_mains,refs=retained_context(home,registry)
    collisions=[q for q in states if q in keep or(q[0],q[2])in heritage]
    if collisions or mains&forest:raise UserError('Preserve every old/future authored solid/AIR/BE, flight and habitat mask: '+str(collisions[:8]))
    walk_field={tuple(q[:2]):q[2:]for q in field['two_high_walk_columns_READONLY']}
    lane,routes=route_geometry(states,mains,walk_field,definition)
    if mains&set(lane):raise UserError('A lane cannot be counted in a main-building footprint')
    for(x,z),axes in lane.items():
        if(x,63,z)not in keep:
            states[x,63,z]='chipped:small_stone_bricks'if len(axes)>1 else'minecraft:andesite'if'x'in axes else'minecraft:cobblestone'
    zinc=verify_zinc_factory(home)
    terrain=NorthTerrain(home,receipt,registry);before={};supports={};clearance={};retained_air=set();began=time.monotonic()
    try:
        for x,z in sorted(mains|set(lane)):
            col=terrain.column(x,z)
            if(x,z)in mains and(col['kind']!='dry'or col['surface_y']not in(62,63)):raise UserError('Actual complete main floor is not low dry land: '+str((x,z,col)))
            mount=qualified_mount(terrain.state,x,z,zinc)
            if not mount['stable']:raise UserError('Literal stable native substrate required: '+str((x,z,mount)))
            for xx,yy,zz,value in mount['stack']:
                if(xx,yy,zz)in terrain.entities:raise UserError('Never use a current block entity as a new foundation')
                supports[xx,yy,zz]=value
            if(x,z)in lane and(x,63,z)in keep:
                current=terrain.state(x,63,z)
                if keep[x,63,z]!=current:raise UserError('Retained outdoor source floor changed; no silent overwrite')
                supports[x,63,z]=current
        for i,q in enumerate(sorted(states,key=lambda q:(q[0]//16,q[2]//16,q[1],q[0],q[2]))):
            current=terrain.state(*q)
            if current is None or q in terrain.entities or key(current)not in GROUND|VOIDS|SOFT|NORTH_SOFT or'waterlogged=true'in current:raise UserError('Preserve saved water, BE, human object, canopy or unknown: '+str((q,current)))
            before[q]=current
            if i%256==0:budgets.append(reader_budget())
            if time.monotonic()-began>90:raise UserError('Finite90s explicit-batch preimage reader exceeded')
        for x,z in lane:
            for y in(64,65):
                q=x,y,z;current=terrain.state(*q)
                if current is None or q in terrain.entities or key(current)not in VOIDS|SOFT|NORTH_SOFT or'waterlogged=true'in current:raise UserError('Actual two-wide public body is obstructed: '+str((q,current)))
                if q in keep:
                    if keep[q]!=AIR or current!=AIR:raise UserError('No lane through retained solid/fixture/flight architecture')
                    retained_air.add(q)
                elif key(current)not in VOIDS:states[q]=AIR
                before[q]=current;clearance[q]=AIR
        saved=terrain.snapshot.sources
    except UserError as exc:
        out=home/'staging'/('tortuga-fill-'+batch+'-REFUSED-'+str(time.time_ns()));out.mkdir()
        (out/'refusal.json').open('x',encoding='utf-8').write(json.dumps({'reason':str(exc),'checkpoint_id':checkpoint_id,'checkpoint_sha256':checkpoint_sha,'source_sha256':digest(Path(__file__)),'native_actions':0,'world_writes':0,'request_emitted':False})+'\n')
        raise UserError(str(exc)+'; preserved '+str(out))from exc
    finally:terrain.close()
    rule=lane_materials(states,lane,batch+' actual narrow public lanes')
    full={**states,**supports,**clearance}
    payloads={
      'cluster-PROPOSAL.json':native_payload(registry,states,checkpoint_sha,'TORTUGA '+batch+' — tightly linked inhabited masses',tags=tags),
      'before-VERIFY-ONLY.json':native_payload(registry,before,checkpoint_sha,'VERIFY ONLY — exact checkpoint targets and real public walking body'),
      'stable-supports-VERIFY-ONLY.json':native_payload(registry,supports,checkpoint_sha,'VERIFY ONLY — actual complete gravity stacks to qualified non-falling native substrate'),
      'complete-after-VERIFY-ONLY.json':native_payload(registry,full,checkpoint_sha,'VERIFY ONLY — full occupied building geometry, lights, stock defaults and true two-wide lane',tags=tags),
      'normal-joins-SETTLE-ONLY.json':native_payload(registry,{q:s for q,s in states.items()if key(s)not in VOIDS},checkpoint_sha,'NORMAL JOINS ONLY — actual new shape updates, no existing inventory replay'),
    }
    raw={}
    for name,doc in payloads.items():
        if name!='cluster-PROPOSAL.json':doc.update(construction_forbidden=True,verification_only=True)
        raw[name]=(json.dumps(doc,separators=(',',':'))+'\n').encode()
    manifest={'format':'awft-tortuga-explicit-fill:1','batch':batch,'checkpoint_id':checkpoint_id,'checkpoint_sha256':checkpoint_sha,
      'source_sha256':digest(Path(__file__)),'variant_source_sha256':digest(Path(__file__).with_name('artistic_tortuga_variants.py')),
      'original_recipe_source_sha256':digest(Path(__file__).with_name('artistic_tortuga_frontages.py')),'field_source':str(field_path.relative_to(home)),'field_sha256':field_sha,
      'definition_source':definition_source.name,'definition_source_sha256':digest(definition_source),
      'definition':definition,'buildings':buildings,'main_columns':len(mains),'lane_columns':len(lane),'routes':routes,'targets':len(states),
      'real_retained_footing_cells':len(supports),'retained_authored_walking_AIR':[list(q)for q in sorted(retained_air)],
      'retained_context_sources':refs,'raw_saved_sources':saved,'pinned_zinc_factory':zinc,'outdoor_rule':rule,'reserve_guard':reserve,
      'reader_peak_RSS_bytes':max(b['owned_reader_rss_bytes']for b in budgets),'native_actions':0,'world_writes':0,'old_inventory_or_human_progress_removed':0,
      'files':{n:{'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)}for n,b in raw.items()},
      'native_cameras':[view for b in buildings for view in b['scene_views']]+[{'name':n,'feet':list(q),'look_at':list(target),'source_only_native_render_walk_pending':True}for n,q,target in definition.get('street_views',())],
      'status':'SOURCE + EXACT STOPPED PREIMAGE ONLY; parent must fresh-native verify/place/normal-settle/full-verify and inspect actual street/interior views',
      'limits':['No replication or native visual acceptance from local geometry checks','No whole-bank coverage claim from this finite batch','New containers have actual native defaults, no Items/Owner or copied inventory','Any new current checkpoint requires a fresh field and source preimage, not an expected-AIR rebind']}
    raw['manifest.json']=(json.dumps(manifest,separators=(',',':'))+'\n').encode()
    if sum(map(len,raw.values()))>MAX_BUNDLE_BYTES:raise UserError('Finite48MiB explicit-batch cap exceeded')
    out=home/'staging'/('tortuga-fill-'+batch+'-'+str(time.time_ns()));out.mkdir()
    for name,data in raw.items():(out/name).open('xb').write(data)
    return {'folder':str(out),'manifest_sha256':digest(out/'manifest.json'),'buildings':len(buildings),'rooms':sum(len(b['rooms'])for b in buildings),'main_columns':len(mains),'lane_columns':len(lane),'targets':len(states),'files':manifest['files'],'native_actions':0}


if __name__=='__main__':
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('--home',type=Path,required=True);a.add_argument('--checkpoint-id',required=True);a.add_argument('--checkpoint-sha',required=True)
    a.add_argument('--batch',choices=BATCHES);a.add_argument('--field',type=Path);a.add_argument('--field-sha');args=a.parse_args()
    if args.batch:
        if not args.field or not args.field_sha:a.error('A batch requires the exact current --field and --field-sha')
        result=prepare(args.home,args.checkpoint_id,args.checkpoint_sha,args.field,args.field_sha,args.batch)
    else:result=fresh_field(args.home,args.checkpoint_id,args.checkpoint_sha)
    print(json.dumps(result,indent=2))
