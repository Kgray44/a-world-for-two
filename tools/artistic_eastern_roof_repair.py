"""Additive roof/endwall correction of exact eastern Sources; no native calls.

Legacy roof writes are traced from the retained, hash-pinned original recipe.
Only those positively authored facets are removed; stock, tagged objects,
normal rooms and entry/furniture layers remain untouched.
"""
from __future__ import annotations
import argparse,copy,importlib.util,json,math,time
from collections import defaultdict
from pathlib import Path
from unittest.mock import patch

from control_room.common import UserError,digest,read_json
from tools import artistic_eastern_compound_sprint as e
from tools.artistic_bridge_refinement import flatten
from tools.artistic_city_planning_map import EAST,read as layout
from tools.artistic_east_tortuga_retrofit import checked
from tools.artistic_eastern_direct_build import entry_body_points
from tools.artistic_eastern_first_three_detail import exact_sources
from tools.artistic_materials import require_material_rule
from tools.artistic_north_bank_east import NorthTerrain
from tools.artistic_north_rebuild_custody import decoded_chunk
from tools.artistic_eastern_urban_custody import before_sources
from tools.artistic_captains_hall import native_payload
from tools.native_relocation_request import reference
from tools.playtest import guard
from tools.eastern_city_execute import ARCH,ARCH_SHA

MIB=1024**2
LEGACY='staging/eastern-roof-legacy-03749525/legacy_compound.py'
LEGACY_SHA='03749525ba9774fa4593c96a162b1c819b3206bce8dbc66631028786056d7438'
CURRENT11=('staging/eastern-current11-native-context-1793234529159926100.json','30ab05f38ee8d479a0036e2a5e94ba155c04270beea64bfdfaf496cfa4cc133c')
FRESH36=('staging/eastern-fresh-36-width-complete-1793234231506694900/SOURCE-INDEX.json','3955153d2634c4873d89741e39ba628bb0de2b0a018965ad595bcdddac49abc1')
FUTURE25=('staging/eastern-door-pairs-corrected-SOURCE-1793236527412165900/SOURCE-INDEX.json','163e0d0d0ab0b184775c9d7af61ba4eb77dec18514fb057ffa1e4b397645f55f')
ENTRY14=('staging/eastern-current14-entry-repair-1793237214610305800/manifest.json','66faec7eafae57bf7a6e0e0dc8cf4c03f2e68d36e7cc34a983bc8a4d7c22ffa5')
AIR={'minecraft:air','minecraft:cave_air','minecraft:void_air'}


def legacy_module(home):
    path=home/LEGACY
    if digest(path)!=LEGACY_SHA:raise UserError('Exact retained old roof implementation required')
    spec=importlib.util.spec_from_file_location('awft_retained_roof_03749525',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def source_geometry(reg,source,others,street,index):
    masses=copy.deepcopy(source['masses']);spec={'id':source.get('id',source.get('building_id')),'name':source['name'],
        'program':source.get('program','charts'),'masses':masses,'actual_building_floor_columns_xz':source['approved_ground_floor_columns_xz']}
    # Program affects furniture only; the original literal furniture is loaded
    # back below. This run reconstructs underlying walls/floors before ANY roof.
    with patch.object(e,'roof_geometry',return_value='deferred original roof'):
        p=e.build(reg,spec,{'fixed':{},'bes':set(),'retire':{}},others,street,index)
    if tuple(p.origin)!=tuple(source['origin']):raise UserError('Exact original Source coordinate frame required')
    return p


def correct_geometry(reg,source,field,others,street,index,legacy,open_masses=(),extra_retained=None):
    p=source_geometry(reg,source,others,street,index);underlying=dict(p.blocks)
    traced=copy.copy(p);traced.blocks=dict(underlying);traced.roles=dict(p.roles);traced.tags={};traced.details=list(p.details)
    traced.suppressed=copy.copy(p.suppressed);writes=set();original_put=traced.put
    def record(x,y,z,material,**props):
        done=original_put(x,y,z,material,**props)
        if done:writes.add((x,y,z))
        return done
    traced.put=record
    for section in source['roof_sections']:
        mass=source['masses'][section['mass']];x0,z0,x1,z1=p.local_box(mass)
        traced.active_roof_ground=traced.mass_fields[section['mass']]
        legacy.roof_geometry(traced,(x0-1,z0-1,x1+1,z1+1),section['base'],section['actual_approved_roof_intent'])
    current={p.local(q):v for q,v in field.items()};p.blocks=dict(current);p.roles={q:'exact current Source context'for q in current};p.tags={}
    p.rooms=copy.deepcopy(source['rooms']);p.routes=copy.deepcopy(source['routes']);p.entries=copy.deepcopy(source['entries'])
    p.body=set()
    for r in p.routes:
        for q in r['feet_local']:
            x,y,z=map(math.floor,q);p.body.update(((x,y,z),(x,y+1,z)))
    p.entry_door_states=e.intended_entry_states(reg,p.entries)
    p.entry_clearance_points={p.local(q)for q in entry_body_points(source)}
    p.fixed={}
    for q in source.get('preserved_fixed_native_states',[]):
        point=p.local(tuple(q['position']));p.fixed[point]=current[point]
    for room in p.rooms:
        for obj in room['actual_objects']:
            q=tuple(obj['position'])
            if q in current:p.fixed[q]=current[q]
    for row in source.get('new_tags_ONLY',[]):
        q=p.local(tuple(row.get('position',row.get('pos'))))
        if q in current:p.fixed[q]=current[q]
    for q,v in(extra_retained or{}).items():p.fixed[p.local(q)]=v
    # Existing open market bays are independent structures with their own
    # four literal masonry feet. Their solid model/body remains read-only.
    for mass in open_masses:
        a,b,c,d=mass['bounds_xz'];floor=mass['floor_y']
        for q,v in current.items():
            wx,wy,wz=p.world(q)
            if a<=wx<=c and b<=wz<=d and floor-1<=wy<=floor+6 and e.key(v)not in AIR:p.fixed[q]=v
    removed=[];retained=[]
    for q in sorted(writes):
        if q not in current or q in p.fixed or q in p.body:continue
        if e.key(current[q])!=e.key(traced.blocks[q]):
            retained.append(p.world(q));continue
        replacement=underlying.get(q,'minecraft:air')
        if current[q]!=replacement:p.blocks[q]=replacement;removed.append(p.world(q))
    p.roof_volume_details=[];p.endwall_relief=[];p.roof_sections=[]
    for section in source['roof_sections']:
        i=section['mass'];mass=source['masses'][i];x0,z0,x1,z1=p.local_box(mass);p.active_roof_ground=p.mass_fields[i]
        geometry=e.roof_geometry(p,(x0-1,z0-1,x1+1,z1+1),section['base'],section['actual_approved_roof_intent'])
        p.roof_sections.append({**section,'geometry':geometry})
    p.active_roof_ground=None
    # Only NEW joins are derived. Actual retained objects and their native
    # properties remain literal, including the separately repaired real doors.
    from tools.artistic_west_r2_frontage import canonical_joins
    fixed=dict(p.fixed);canonical_joins(p)
    for q,v in fixed.items():p.blocks[q]=v
    full={p.world(q):v for q,v in p.blocks.items()}
    if any(full.get(p.world(q))!=v for q,v in fixed.items()):raise UserError('No existing furnishing or stock may change')
    material=require_material_rule(full,p.name+' closed roofs and modeled endwalls')
    # Add exactly those original independent porch outlines as root domains;
    # they are not invented normal rooms and never waive room-width checks.
    for mass in open_masses:
        a,b,c,d=mass['bounds_xz'];cells={p.local_xz((x,z))for x in range(a,c+1)for z in range(b,d+1)}
        p.mass_fields.append(cells);p.mass_floors.append(mass['floor_y']-p.origin[1])
    scene_proof=e.validate(p)
    changed={q:v for q,v in full.items()if field.get(q)!=v}
    return full,changed,{'legacy_facet_cells_replaced':len(removed),'different_current_objects_retained':len(retained),
        'roof_volumes':p.roof_volume_details,'endwall_bays':p.endwall_relief,'complete_material_rule':material,
        'old_and_new_tags_unchanged':True,'retained_independent_open_bay_root_domains':len(open_masses),
        'additional_saved_objects_retained_without_writes':[list(q)for q in(extra_retained or{})],
        'source_rooting_routes_and_scene_integrity':scene_proof,'native_art_and_collision_acceptance':False}


def prepare(home,recovery_id,*,only=None,extra_context=()):
    home=Path(home).resolve();reserve=guard(4*MIB,32*MIB);reg=read_json(home/'dashboard/settlement/registry.json')
    companion=read_json(home/'backups'/(recovery_id+'.json'))
    if companion.get('integrity')!='verified':raise UserError('Actual verified stopped snapshot required')
    receipt={'id':recovery_id,'sha256':companion['sha256'],'verified':True};backup=read_json(home/'dashboard/settlement/backup-receipt.json')['sha256']
    master=layout(home,EAST);specs={r['id']:r for r in master['buildings']};order={r['id']:i for i,r in enumerate(master['buildings'])};allcols={r['id']:set(map(tuple,r['actual_building_floor_columns_xz']))for r in master['buildings']if r['masses']}
    street={tuple(q)for r in master['street_network']for q in r['all_walk_columns_xz']};core,_=e.preservation(home,reg)
    oldindex=checked(home/ARCH,ARCH_SHA,2*MIB);fresh=checked(home/FRESH36[0],FRESH36[1],2*MIB)
    sources={r['id']:r['files']['SOURCE-ONLY']for r in oldindex['compounds']if r['id']in('east-coal','shoal-warden','thin-sail')}
    current=checked(home/CURRENT11[0],CURRENT11[1],2*MIB);freshrows={r['id']:r for r in fresh['compounds']}
    sources.update({r['id']:freshrows[r['id']]['files']['SOURCE-ONLY']for r in current['entries']})
    future=checked(home/FUTURE25[0],FUTURE25[1],2*MIB)
    for r in future['compounds']:sources[r['id']]=r['files']['SOURCE-ONLY']
    entry=checked(home/ENTRY14[0],ENTRY14[1],2*MIB);global_current={};entry_after=entry['files']['current14-complete-AFTER']
    global_current.update(flatten(checked(home/entry_after['path'],entry_after['sha256'],8*MIB)))
    for path,sha in extra_context:global_current.update(flatten(checked(Path(path),sha,8*MIB)))
    legacy=legacy_module(home);out=home/'staging'/('eastern-closed-roof-endwall-source-'+str(time.time_ns()));out.mkdir();records=[];held=[];prospective={};wanted=set()
    for ident,ref in sources.items():
        if only and ident not in only:continue
        try:
            s=checked(home/ref['path'],ref['sha256'],8*MIB);field={tuple(q[:3]):q[3]for q in s['complete_expected_state_context_ONLY']}
            actual=ident in{r['id']for r in current['entries']}or ident in('east-coal','shoal-warden','thin-sail')
            if actual:field.update({q:v for q,v in global_current.items()if q in field})
            others=set().union(*(v for k,v in allcols.items()if k!=ident))|core
            open_indices={r['original_mass']for r in s.get('actual_open_projection_features',[])}
            open_masses=[specs[ident]['masses'][i]for i in sorted(open_indices)]
            full,changes,proof=correct_geometry(reg,s,field,others,street,order[ident],legacy,open_masses)
            prospective[ident]=(ref,s,field,full,changes,proof,actual,open_masses)
            if actual:wanted.update(changes)
        except(UserError,ValueError)as error:held.append({'id':ident,'reason':str(error),'no_native_action':True})
    # One bounded snapshot field read covers all actual corrective targets.
    terrain=NorthTerrain(home,receipt,reg);before={};bes={};start=time.monotonic()
    try:
        groups=defaultdict(list)
        for q in wanted:groups[q[0]//16,q[2]//16].append(q)
        for(cx,cz),points in sorted(groups.items()):
            for q in points:
                value=global_current.get(q)
                if value is None:value=terrain.state(*q)
                if value is None:raise UserError('Unknown/nonFULL cannot become roof AIR')
                before[q]=value
            terrain.chunk(cx,cz)
            doc=decoded_chunk(terrain.snapshot.regions[cx//32,cz//32],cx,cz)
            for tag in doc.get('block_entities',[]):
                q=tuple(int(tag[k])for k in('x','y','z'))
                if q not in wanted:continue
                saved=terrain.state(*q)
                # Two earlier native fields can positively prove the old
                # archive container was replaced by a DIFFERENT block. Never
                # treat a missing current field as proof of BE absence.
                if q in global_current and e.key(global_current[q])!=e.key(saved):continue
                bes[q]=saved
            if time.monotonic()-start>90:raise UserError('Finite90s roof preimage read bound')
        archive_refs=terrain.snapshot.sources
    finally:terrain.close()
    written=0
    def emit(name,doc):
        nonlocal written
        raw=(json.dumps(doc,separators=(',',':'))+'\n').encode();written+=len(raw)
        if written>32*MIB:raise UserError('Finite32MiB corrective output exceeded')
        p=out/(name+'.json');p.open('xb').write(raw);return reference(home,p)
    def native(name,field):
        d=json.loads(native_payload(reg,field,backup,name));d.update(verification_only=True,construction_forbidden=True,actual_saved_checkpoint=receipt);d['block_entities']=[]
        return emit(name,d)
    for ident,(ref,s,field,full,changes,proof,actual,open_masses)in prospective.items():
        extra={q:bes[q]for q in changes.keys()&bes.keys()}if actual else{}
        if extra:
            field={**field,**extra};others=set().union(*(v for k,v in allcols.items()if k!=ident))|core
            full,changes,proof=correct_geometry(reg,s,field,others,street,order[ident],legacy,open_masses,extra)
            if changes.keys()&extra.keys():raise UserError('No existing saved object may enter roof writes')
        derived=copy.deepcopy(s);derived['complete_expected_state_context_ONLY']=[[*q,v]for q,v in sorted(full.items())]
        # For future construction the full fresh Source remains a full Source;
        # personal anchors are still read-only and excluded by the direct adapter.
        fixed={tuple(v['position'])for v in s.get('preserved_fixed_native_states',[])}
        derived['blocks_PROSPECTIVE_DELTA']=[[*q,v]for q,v in sorted(full.items())if q not in fixed]
        derived['roof_endwall_correction']={'original_source':ref,'legacy_recipe_sha256':LEGACY_SHA,'new_recipe_sha256':digest(Path(e.__file__)),'proof':proof,'native_actions':0}
        files={'SOURCE-ONLY':emit(ident+'-SOURCE-ONLY',derived)}
        if actual:
            files.update(before=native(ident+'-roof-BEFORE',{**{q:before[q]for q in changes},**extra}),delta=native(ident+'-roof-DELTA',changes),
                settle=native(ident+'-roof-normal-settle',{q:v for q,v in changes.items()if e.key(v)not in AIR}),after=native(ident+'-roof-complete-AFTER',full))
        records.append({'id':ident,'actual_preexisting':actual,'files':files,'changed_targets':len(changes),'roof_proof':proof,'source_only_not_native_acceptance':True})
    index={'format':'awft-eastern-closed-roof-endwall-correction:1','compounds':records,'held':held,'fresh_direct_construction':True,
        'entry14_source_context':ENTRY14,'extra_current_context':[{'path':str(p),'sha256':s}for p,s in extra_context],
        'actual_saved_checkpoint':receipt,'archive_sources':archive_refs,'actual_before_is_prospective_until_fresh_native_verify':True,
        'source_sha256':digest(Path(__file__)),'reserve_guard':reserve,'native_actions':0,'construction_forbidden':True}
    ref=emit('SOURCE-INDEX',index)
    return {'folder':str(out),'index_sha256':ref['sha256'],'ready':len(records),'held':held,'current14_ready':sum(r['actual_preexisting']for r in records),'remaining25_ready':sum(not r['actual_preexisting']for r in records)}


def compose_shared_roofs(home,roof_index,roof_sha,furnished_index,furnished_sha):
    """Explicit eight shared eave details; no room/furniture or tag changes."""
    from tools.artistic_eastern_direct_build import require_physical_entries
    from tools.artistic_spawn_plaza import state
    home=Path(home).resolve();guard(2*MIB,32*MIB)
    roofs=checked(Path(roof_index),roof_sha,4*MIB);rich=checked(Path(furnished_index),furnished_sha,4*MIB)
    reg=read_json(home/'dashboard/settlement/registry.json');rows=[copy.deepcopy(r)for r in roofs['compounds']if r['actual_preexisting']]+[copy.deepcopy(r)for r in rich['compounds']]
    docs={r['id']:copy.deepcopy(checked(home/r['files']['SOURCE-ONLY']['path'],r['files']['SOURCE-ONLY']['sha256'],8*MIB))for r in rows}
    fields={k:{tuple(q[:3]):q[3]for q in d['complete_expected_state_context_ONLY']}for k,d in docs.items()}
    original={k:dict(v)for k,v in fields.items()};floors={};bodies={};tagged={}
    for ident,d in docs.items():
        floors[ident]={(x,z)for b in(m['bounds_xz']for m in d['masses'])for x in range(b[0],b[2]+1)for z in range(b[1],b[3]+1)}
        bodies[ident]=entry_body_points(d)
        for r in d['routes']:
            for v in r['feet_local']:
                x,y,z=(math.floor(v[k]+d['origin'][k])for k in range(3));bodies[ident].update(((x,y,z),(x,y+1,z)))
        tagged[ident]={tuple(r.get('position',r.get('pos')))for r in d.get('new_tags_ONLY',[])}|{tuple(r['position'])for r in d.get('preserved_fixed_native_states',[])}
    pairs=[('bridge-customs','bridge-cooper'),('copper-bell','tide-broker'),('tide-fish','marrow-side'),
        ('moon-branch','moth-candle'),('bridge-cooper','willow-door'),('anchor-dice','bay-kettle'),
        ('lantern-cod','navy-blue'),('navy-blue','quarter-jack')]
    records=[]
    def assign(a,b,q,value,detail):
        if any((q[0],q[2])in floors[k]or q in bodies[k]or q in tagged[k]for k in(a,b)):raise UserError('Shared eave cannot enter a room/body/tag/anchor: '+str((a,b,q)))
        before=[fields[a].get(q,'minecraft:air'),fields[b].get(q,'minecraft:air')]
        fields[a][q]=value;fields[b][q]=value
        records.append({'buildings':[a,b],'position':list(q),'before':before,'shared_state':value,'structural_detail':detail,'outside_both_actual_mass_and_walking_bodies':True})
    for a,b in pairs:
        for q in sorted(fields[a].keys()&fields[b].keys()):
            va,vb=fields[a][q],fields[b][q]
            if va==vb or e.key(va)in AIR or e.key(vb)in AIR:continue
            assign(a,b,q,va,'one explicit retained shared cornice/knee/window-box or corner join; duplicate overlapping component omitted')
    # Opposite roof toes meet in a level, dark mineral-lined valley, carried
    # by a continuous full timber tie; they never occupy two incompatible
    # slopes in one block. The exact lines are outside both room envelopes.
    valleys=[('bridge-customs','bridge-cooper','x',-1214,1217,1230,68),
        ('copper-bell','tide-broker','z',1328,-1229,-1216,72),
        ('tide-fish','marrow-side','z',1357,-1206,-1202,72)]
    for a,b,axis,fixed,low,high,y in valleys:
        for c in range(low,high+1):
            x,z=(c,fixed)if axis=='x'else(fixed,c)
            for yy in(y-1,y):
                q=x,yy,z
                if q not in fields[a]or q not in fields[b]or any(e.key(fields[k][q])in AIR for k in(a,b)):continue
                if yy==y:value=state(reg,'minecraft:polished_deepslate_slab'if axis=='x'else'minecraft:polished_blackstone_slab',type='top',waterlogged=False)
                else:value=state(reg,'chipped:reinforced_dark_oak_log'if axis=='x'else'chipped:edged_stripped_dark_oak_log',axis=axis)
                assign(a,b,q,value,'shared closed roof-valley cap with a full bearing tie; existing native slab model, no water/physics claim')
    assign('navy-blue','quarter-jack',(1325,68,-1152),state(reg,'minecraft:spruce_slab',type='top',waterlogged=False),
        'intentional full UP-face planter sill: preserved Monstera atY69 must not float over a bottom slab')
    out=home/'staging'/('eastern-shared-roofs-rich-source-'+str(time.time_ns()));out.mkdir();output=[];written=0
    for row in rows:
        ident=row['id'];d=docs[ident];f=fields[ident];before=original[ident]
        if any(f.get(q)!=before.get(q)for q in tagged[ident]):raise UserError('Shared framing changed a literal tag or human anchor')
        proof=require_material_rule(f,d['name']+' final shared roof details and rich interiors')
        d['complete_expected_state_context_ONLY']=[[*q,v]for q,v in sorted(f.items())]
        anchors={tuple(r['position'])for r in d.get('preserved_fixed_native_states',[])}
        d['blocks_PROSPECTIVE_DELTA']=[[*q,v]for q,v in sorted(f.items())if q not in anchors]
        d['shared_roof_details']={'records':[r for r in records if ident in r['buildings']],
            'only_owned_exterior_joint_cells_changed':True,'all_tags_and_room_furnishing_unchanged':True,'material_rule':proof}
        require_physical_entries(d)
        raw=(json.dumps(d,separators=(',',':'))+'\n').encode();written+=len(raw)
        if written>32*MIB:raise UserError('Finite32MiB shared Source bound')
        p=out/(ident+'-SOURCE-ONLY.json');p.open('xb').write(raw)
        output.append({'id':ident,'actual_preexisting':row.get('actual_preexisting',False),'fresh_direct_construction':not row.get('actual_preexisting',False),
            'files':{'SOURCE-ONLY':reference(home,p)},'width_review':d.get('width_review'),
            'shared_detail_changes':sum(f.get(q)!=before.get(q)for q in f.keys()|before.keys())})
    index={'format':'awft-shared-roof-rich-eastern-SOURCE:1','fresh_direct_construction':True,'compounds':output,'held':[],
        'roof_index':reference(home,Path(roof_index)),'rich_interiors_index':reference(home,Path(furnished_index)),
        'explicit_shared_roof_details':records,'world_writes':0,'native_actions':0,'construction_forbidden':True}
    p=out/'SOURCE-INDEX.json';p.open('x',encoding='utf8').write(json.dumps(index,separators=(',',':'))+'\n')
    return {'folder':str(out),'index_sha256':digest(p),'current14':14,'future25':25,'shared_detail_records':len(records),'native_actions':0}


def prepare_current14(home,shared_index,shared_sha,furniture_index,furniture_sha,recovery_id):
    """One ordinary corrective field from a fresh saved snapshot, no NBT writes."""
    home=Path(home).resolve();reserve=guard(4*MIB,16*MIB);reg=read_json(home/'dashboard/settlement/registry.json')
    companion=read_json(home/'backups'/(recovery_id+'.json'))
    if companion.get('integrity')!='verified':raise UserError('Verified fresh current recovery required')
    receipt={'id':recovery_id,'sha256':companion['sha256'],'verified':True};backup=read_json(home/'dashboard/settlement/backup-receipt.json')['sha256']
    shared=checked(Path(shared_index),shared_sha,4*MIB);furn=checked(Path(furniture_index),furniture_sha,4*MIB)
    roofs=checked(home/'staging/eastern-closed-roof-endwall-source-1793240081466811100/SOURCE-INDEX.json','2eeac3cfee177ef1388e6ae5dde17e4953218651dbbada2e3b567c5f87273a34',4*MIB)
    oldroof={r['id']:r for r in roofs['compounds']};sources={};desired={};candidates=set();body=set();floor=set()
    for row in shared['compounds']:
        if not row.get('actual_preexisting'):continue
        ident=row['id'];s=checked(home/row['files']['SOURCE-ONLY']['path'],row['files']['SOURCE-ONLY']['sha256'],8*MIB);sources[ident]=s
        f={tuple(q[:3]):q[3]for q in s['complete_expected_state_context_ONLY']}
        for q,v in f.items():
            if q not in desired or e.key(desired[q])in AIR or e.key(v)not in AIR:desired[q]=v
        delta=oldroof[ident]['files']['delta'];candidates.update(flatten(checked(home/delta['path'],delta['sha256'],MIB)))
        candidates.update(tuple(r['position'])for r in s.get('shared_roof_details',{}).get('records',[]))
        body.update(entry_body_points(s))
        for route in s['routes']:
            for q in route['feet_local']:
                x,y,z=(math.floor(q[k]+s['origin'][k])for k in range(3));body.update(((x,y,z),(x,y+1,z)))
        floor.update((x,z)for m in s['masses']for x in range(m['bounds_xz'][0],m['bounds_xz'][2]+1)for z in range(m['bounds_xz'][1],m['bounds_xz'][3]+1))
    furniture={};support={}
    def append_air_plan(path,sha):
        doc=checked(home/path,sha,4*MIB)
        if doc.get('block_entities'):raise UserError('This ordinary corrective packet never suppresses or writes supplied NBT')
        for q,v in flatten(doc).items():
            if q in furniture and furniture[q]!=v:raise UserError('Two furnishing layers conflict')
            furniture[q]=v
    for row in furn['compounds']:
        refs=row['files'];r=refs['AIR-only-DELTA'];append_air_plan(r['path'],r['sha256'])
        r=refs['retained-supports'];support.update(flatten(checked(home/r['path'],r['sha256'],4*MIB)))
    append_air_plan('staging/worn-book-photo-finish-1793237530213387100/bookshop-AIR-only-DELTA.json','efe1c51fdfb4045b8d3f355b80c628e5e85670b891001fafd5a26898f8cbc93f')
    support.update(flatten(checked(home/'staging/worn-book-photo-finish-1793237530213387100/retained-mounts-BEFORE.json','bc9b0fff0ae6b537764cb495b8763240fa78b1b8273e2bf59580bba72c787e89',MIB)))
    for q,v in furniture.items():
        if q in candidates and desired.get(q)!=v:raise UserError('Roof/furniture genuinely conflict: '+str(q))
        desired[q]=v
    candidates.update(furniture);wanted=set(desired)|set(candidates)|set(support)
    if len(wanted)>90000:raise UserError('Finite90K current corrective snapshot field exceeded')
    terrain=NorthTerrain(home,receipt,reg);actual={};bes=set();start=time.monotonic();groups=defaultdict(list)
    try:
        for q in wanted:groups[q[0]//16,q[2]//16].append(q)
        for(cx,cz),points in sorted(groups.items()):
            for q in points:
                value=terrain.state(*q)
                if value is None:raise UserError('No current roof field from UNKNOWN/nonFULL')
                actual[q]=value
            doc=decoded_chunk(terrain.snapshot.regions[cx//32,cz//32],cx,cz)
            bes.update(tuple(int(tag[k])for k in('x','y','z'))for tag in doc.get('block_entities',[]))
            if time.monotonic()-start>90:raise UserError('Finite90s current saved field exceeded')
        archive_refs=terrain.snapshot.sources
    finally:terrain.close()
    if bes&candidates:raise UserError('An actual current saved BE entered a corrective write: '+str(sorted(bes&candidates)[:8]))
    if any(e.key(actual[q])not in AIR for q in furniture):raise UserError('Current furnishing target is occupied; never fit an arbitrary current object')
    changes={q:desired[q]for q in candidates if actual[q]!=desired[q]}
    after={q:changes.get(q,v)for q,v in actual.items()}
    for q,v in support.items():
        if after[q]!=v:raise UserError('Retained/future fixture support differs after real combined field: '+str(q))
    protected={q:v for q,v in after.items()if e.key(v)not in AIR or(q[0],q[2])in floor or q in body}
    out=home/'staging'/('eastern14-roof-rich-current-'+str(time.time_ns()));out.mkdir();files={}
    for name,field in [('before',{q:actual[q]for q in candidates|support.keys()}),('delta',changes),
        ('settle',{q:v for q,v in changes.items()if e.key(v)not in AIR}),('after',after),('prerequisite-after',changes),('protected-after',protected)]:
        doc=json.loads(native_payload(reg,field,backup,'SOURCE current14 closed roofs and distinct interiors '+name));doc.update(verification_only=True,construction_forbidden=True,actual_saved_checkpoint=receipt);doc['block_entities']=[]
        path=out/(name+'.json');path.open('x',encoding='utf8').write(json.dumps(doc,separators=(',',':'))+'\n');files[name]=reference(home,path)
    preserve={'format':'awft-fresh-direct-eastern-ordinary-batch:1','compounds':[{'id':'current14-closed-and-rich','held':False,'files':{'after':files['protected-after']}}],
        'forecast_not_actual_native_proof':True,'required_native_verify_before_future25':files['prerequisite-after']}
    path=out/'prospective14-preservation-manifest.json';path.open('x',encoding='utf8').write(json.dumps(preserve,separators=(',',':'))+'\n');files['preservation-manifest']=reference(home,path)
    manifest={'format':'awft-current14-ordinary-roof-rich-correction:1','actual_saved_checkpoint':receipt,'files':files,
        'shared_source_index':reference(home,Path(shared_index)),'rich14_source_index':reference(home,Path(furniture_index)),
        'roof_and_shared_target_cells':len(candidates)-len(furniture),'new_AIR_only_furnishings':len(furniture),
        'write_targets':len(changes),'complete_after_points':len(after),'actual_current_saved_BE_write_intersections':0,
        'all_untargeted_actual_states_preserved':True,'NBT_or_inventory_writes':0,'archive_sources':archive_refs,
        'reserve_guard':reserve,'construction_forbidden':True,'native_actions':0}
    path=out/'manifest.json';path.open('x',encoding='utf8').write(json.dumps(manifest,separators=(',',':'))+'\n')
    return {'folder':str(out),'manifest_sha256':digest(path),'write_targets':len(changes),'furnishing_cells':len(furniture),'complete_after':len(after),'files':files,'native_actions':0}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--home',type=Path,required=True);p.add_argument('--recovery-id',required=True);p.add_argument('--ids',nargs='*');a=p.parse_args()
    print(json.dumps(prepare(a.home,a.recovery_id,only=set(a.ids)if a.ids else None),indent=2))
