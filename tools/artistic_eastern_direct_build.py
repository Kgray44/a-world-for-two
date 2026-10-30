"""Ordinary fresh East build packets after the explicit owner discard override.

No mover, installed request, console call, world edit or default-stock capture.
Uses existing awftbuild place/verify/settle and its genuine native tag loader.
"""
from __future__ import annotations
import argparse,json,time,math
from pathlib import Path
from collections import defaultdict
from control_room.common import UserError,digest,read_json,utcnow
from tools.artistic_east_tortuga_retrofit import checked
from tools.artistic_bridge_refinement import flatten
from tools.artistic_captains_hall import native_payload
from tools.native_eastern_relocation_r7 import CATALOG,CATALOG_SHA
from tools.native_eastern_relocation import CLASSES
from tools.eastern_city_execute import ARCH,ARCH_SHA,PACKET,PACKET_SHA
from tools.artistic_north_bank_east import NorthTerrain
from tools.artistic_north_rebuild_custody import decoded_chunk
from tools.artistic_eastern_urban_custody import OVERLAYS,PRIVATE_ANCHORS,before_sources
from tools.native_relocation_request import reference
from tools.playtest import guard
from tools.settlement_attractions import properties

MIB=1024**2
EXEMPT={'east-coal','shoal-warden','thin-sail'}
AIR={'minecraft:air','minecraft:cave_air','minecraft:void_air'}
HUMAN=[(1088,58,-1270,1174,196,-744),(1324,62,-1003,1338,90,-931)]
CORE=[(1224,-64,-1264,1283,319,-1221),(1288,-64,-1290,1312,319,-1267),
      (1282,-64,-1337,1309,319,-1297),(1314,-64,-1349,1334,319,-1316)]
def inside(q,b):return all(b[k]<=q[k]<=b[k+3]for k in range(3))
def key(s):return s.split('[',1)[0]

def entry_body_points(source):
    vectors={'north':(0,-1),'south':(0,1),'east':(1,0),'west':(-1,0)}
    result=set()
    for entry in source.get('entries',[]):
        q=tuple(source['origin'][k]+entry['local'][k]for k in range(3));dx,dz=vectors[entry['outward']]
        result.update((q[0]+sign*dx,q[1]+dy,q[2]+sign*dz)for sign in(-1,1)for dy in(0,1))
    return result

def require_physical_entries(source,field=None):
    """Metadata cannot authorize a threshold whose two blocks are windows."""
    if field is None:field={tuple(v[:3]):v[3]for v in source['complete_expected_state_context_ONLY']}
    opposite={'north':'south','south':'north','east':'west','west':'east'}
    entries=source.get('entries',[])
    if not entries:raise UserError('A fresh normal building needs actual two-part exterior doors')
    for entry in entries:
        lower=tuple(source['origin'][k]+entry['local'][k]for k in range(3))
        values=[field.get((lower[0],lower[1]+dy,lower[2]),'minecraft:air')for dy in(0,1)]
        props=[properties(v)for v in values]
        if(not key(values[0]).endswith('_door')or key(values[0])!=key(values[1])
            or [p.get('half')for p in props]!=['lower','upper']
            or any(p.get('facing')!=opposite.get(entry.get('outward'))for p in props)
            or props[0].get('hinge')!=props[1].get('hinge')):
            raise UserError('Physical entry is not its intended real door pair: '+str((source.get('id'),lower,values)))
    obstructed=[q for q in entry_body_points(source)if key(field.get(q,'minecraft:air'))not in AIR]
    if obstructed:raise UserError('A facade fitting blocks the actual entry landing/headroom: '+str((source.get('id'),sorted(obstructed))))
    return len(entries)

def correct_entry_sources(home,index,index_sha,generator_sha):
    """Derive only overwritten door pairs; keep composed geometry and tags."""
    from copy import deepcopy
    from tools import artistic_eastern_compound_sprint as architecture
    from tools.artistic_materials import require_material_rule
    home=Path(home).resolve();guard(MIB,32*MIB)
    if digest(Path(architecture.__file__))!=generator_sha:raise UserError('The exact reviewed entry-reserving generator must be frozen first')
    original=checked(Path(index),index_sha,2*MIB);result=deepcopy(original)
    registry=read_json(home/'dashboard/settlement/registry.json')
    out=home/'staging'/('eastern-door-pairs-corrected-SOURCE-'+str(time.time_ns()));out.mkdir()
    changes=[];written=0
    for row in result['compounds']:
        ref=row['files']['SOURCE-ONLY'];source=deepcopy(checked(home/ref['path'],ref['sha256'],8*MIB))
        full={tuple(v[:3]):v[3]for v in source['complete_expected_state_context_ONLY']}
        prospective={tuple(v[:3]):v[3]for v in source['blocks_PROSPECTIVE_DELTA']}
        retained={tuple(v['position'])for v in source.get('preserved_fixed_native_states',[])}
        tagged={tuple(v.get('position',v.get('pos')))for v in source.get('new_tags_ONLY',[])}
        local=[]
        for q,expected in architecture.intended_entry_states(registry,source['entries'],source['origin']).items():
            if full.get(q)==expected:continue
            if(key(full.get(q,'minecraft:air'))!='mcwwindows:dark_oak_four_window'or prospective.get(q)!=full[q]
                or q in retained or q in tagged):raise UserError('Door-only correction must not fit unrelated geometry, retained objects or tags: '+str(q))
            local.append({'position':list(q),'before':full[q],'after':expected,'role':'restore literal intended lower/upper door'})
            full[q]=expected;prospective[q]=expected
        for q in sorted(entry_body_points(source)):
            if key(full.get(q,'minecraft:air'))in AIR:continue
            if(key(full[q])not in{'mythrais:curved_corbel_dark_oak','fishofthieves:potted_white_plumeria'}
                or prospective.get(q)!=full[q]or q in retained or q in tagged):raise UserError('Only the positively authored low facade fitting may leave entry headroom: '+str(q))
            local.append({'position':list(q),'before':full[q],'after':'minecraft:air','role':'remove overlapping casement fitting from actual entry body'})
            full[q]='minecraft:air';prospective[q]='minecraft:air'
        source['complete_expected_state_context_ONLY']=[[*q,v]for q,v in sorted(full.items())]
        source['blocks_PROSPECTIVE_DELTA']=[[*q,v]for q,v in sorted(prospective.items())]
        require_physical_entries(source)
        material=require_material_rule(full,source.get('name',row['id'])+' door-only correction')
        source['entry_only_derivation']={'original_source':ref,'generator_sha256':generator_sha,
            'adapter_sha256':digest(Path(__file__)),'changed_cells':local,'all_other_states_tags_routes_stock_and_retained_anchors_unchanged':True,
            'physical_door_pairs_checked':len(source['entries']),'complete_material_rule':material,'native_actions':0}
        raw=(json.dumps(source,separators=(',',':'))+'\n').encode();written+=len(raw)
        if written>32*MIB:raise UserError('Finite32MiB door Source bound exceeded')
        path=out/(row['id']+'-SOURCE-ONLY.json');path.open('xb').write(raw);row['files']['SOURCE-ONLY']=reference(home,path)
        changes.append({'id':row['id'],'changed_cells':len(local),'physical_entry_pairs':len(source['entries'])})
    result.update(format='awft-remaining25-real-door-pairs-SOURCE:1',entry_correction_only=True,
        original_composed_source_index=reference(home,Path(index)),entry_reserving_generator_sha256=generator_sha,
        door_corrections=changes,native_actions=0,construction_forbidden=True)
    path=out/'SOURCE-INDEX.json';path.open('x',encoding='utf8').write(json.dumps(result,separators=(',',':'))+'\n')
    return {'folder':str(out),'index_sha256':digest(path),'compounds':len(changes),
        'changed_cells':sum(r['changed_cells']for r in changes),'physical_entry_pairs':sum(r['physical_entry_pairs']for r in changes),'native_actions':0}

def prepare(home,index,index_sha,recovery_id,ids=None,preserve_manifests=(),current_context=None,current_context_sha=None,prerequisite_after=None,prerequisite_after_sha=None):
    home=Path(home).resolve();guard(2*MIB,32*MIB);registry=read_json(home/'dashboard/settlement/registry.json')
    canonical=read_json(home/'dashboard/settlement/backup-receipt.json');companion=read_json(home/'backups'/(recovery_id+'.json'))
    if companion.get('integrity')!='verified':raise UserError('A genuine verified stopped recovery is required')
    receipt={'id':recovery_id,'sha256':companion['sha256'],'verified':True}
    source_index=checked(Path(index),index_sha,2*MIB)
    if source_index.get('fresh_direct_construction')is not True:raise UserError('Only newly furnished direct Sources; original capture/room plans are superseded')
    cat=checked(home/CATALOG,CATALOG_SHA,2*MIB);old_index=checked(home/ARCH,ARCH_SHA,2*MIB)
    pm=checked(home/PACKET,PACKET_SHA,2*MIB);pipeline=checked((home/PACKET).parent/'pipeline-SOURCE-ONLY.json',pm['pipeline_sha256'],16*MIB)
    protected=set();protected_states={};protected_direct=[];owned_current={};current_ref=None;prior_layer={};prior_ref=None
    if prerequisite_after is not None:
        prior=checked(Path(prerequisite_after),prerequisite_after_sha,2*MIB)
        if prior.get('format')!='awft-native-settlement:1'or prior.get('block_entities')or not preserve_manifests:raise UserError('Exact ordinary block-only preceding layer and its physical preservation mask required')
        prior_layer=flatten(prior);prior_ref=reference(home,Path(prerequisite_after))
    for row in old_index['compounds']:
        if row['id']in EXEMPT and not prior_ref:
            r=row['files']['full-after-PROSPECTIVE-VERIFY-ONLY'];f=flatten(checked(home/r['path'],r['sha256'],MIB));protected.update(f);protected_states.update(f)
    for path,sha in preserve_manifests:
        prior=checked(Path(path),sha,2*MIB)
        if prior.get('format')!='awft-fresh-direct-eastern-ordinary-batch:1':raise UserError('Exact preceding direct source context required')
        for row in prior['compounds']:
            if row['held']:continue
            ref=row['files']['after'];f=flatten(checked(home/ref['path'],ref['sha256'],8*MIB));protected.update(f);protected_states.update(f)
        protected_direct.append(reference(home,Path(path)))
    if current_context is not None:
        ctx=checked(Path(current_context),current_context_sha,2*MIB)
        if ctx.get('format')!='awft-current-direct-structural-context:1':raise UserError('Exact previously verified direct source context required')
        complete=checked(home/'staging/eastern-fresh-36-width-complete-1793234231506694900/SOURCE-INDEX.json','3955153d2634c4873d89741e39ba628bb0de2b0a018965ad595bcdddac49abc1',2*MIB)
        geometry={r['id']:r for r in complete['compounds']}
        for e in ctx['entries']:
            ref=e['expected_structural_context_plan'];plan=checked(home/ref['path'],ref['sha256'],8*MIB);field=flatten(plan)
            r=e['actual_native_verify'];p=home/r['path'];proof=checked(p,r['sha256'],MIB)
            if(p.with_name(p.name+'.complete').read_text().strip()!=r['sha256']or proof.get('operation')!='verify'or proof.get('plan_sha256')!=ref['sha256']or proof.get('blocks')!=len(field)or proof.get('failures')!=0 or proof.get('cleanup_required')is not False or proof.get('temporary_tickets_remaining')!=0 or proof.get('pending_shared_chunk_futures')!=0 or proof.get('error')or proof.get('ticket_cleanup_error')):raise UserError('Actual complete clean structural verification must bind preceding source context')
            gr=geometry[e['id']]['files']['SOURCE-ONLY'];g=checked(home/gr['path'],gr['sha256'],8*MIB);body=entry_body_points(g)
            for route in g.get('routes',[]):
                for v in route.get('feet_local',[]):
                    x,y,z=(math.floor(v[k]+g['origin'][k])for k in range(3));body.update(((x,y,z),(x,y+1,z)))
            for q,value in field.items():
                owned_current[q]=value
                own_floor=any(b[0]<=q[0]<=b[2]and b[1]<=q[2]<=b[3]for b in(m['bounds_xz']for m in g['masses']))
                if key(value)not in AIR or own_floor or q in body:protected.add(q);protected_states[q]=value
        current_ref=reference(home,Path(current_context))
    personal=set(PRIVATE_ANCHORS)
    def keep(q):return q in protected or q in personal or any(inside(q,b)for b in HUMAN+CORE)
    groups=defaultdict(dict)
    for row in cat['capsules']:
        r=row['source_original'];groups[row['id'].split(':room:',1)[0]].update(flatten(checked(home/r['path'],r['sha256'],MIB)))
    for group in pipeline['old_skin_batches']:
        r=group['before'];groups[group['group']].update(flatten(checked(home/r['path'],r['sha256'],8*MIB)))
    for name,relative,sha,count in OVERLAYS:
        field=flatten(checked(home/relative,sha,4*MIB))
        if len(field)!=count:raise UserError('Exact actually authored old-AI overlay only')
        for owned in groups.values():
            for q in set(field)&set(owned):owned[q]=field[q]
    # Pipeline before-fields forecast an AFTER-all-moves world. They are not
    # authorship for the currently retained old grid. Use exact original placed
    # source plus its actual321/1808 overlays instead of those forecast materials.
    _,authored,_,authored_refs,_=before_sources(home)
    for owned in groups.values():
        for q in set(owned)&set(authored):owned[q]=authored[q]
    # These two genuinely invoked partial rooms are old AI work too. Their
    # failed ledgers remain untouched; the new instruction never authorizes retry.
    for ident in('eastern22/pippins-net:room:0','density/bent-needle:room:0'):
        row=next(r for r in cat['capsules']if r['id']==ident);r=row['source_original'];d=row['translation_xyz']
        groups['partial-AI/'+ident].update({tuple(q[k]+d[k]for k in range(3)):s for q,s in flatten(checked(home/r['path'],r['sha256'],MIB)).items()})
    sources=[];scope=set();source_holds=[];retained_context={}
    for row in source_index['compounds']:
        if ids and row['id']not in ids:continue
        if row['id']in EXEMPT:continue
        r=row['files']['SOURCE-ONLY'];s=checked(home/r['path'],r['sha256'],8*MIB)
        if s.get('fresh_direct_construction')is not True or s.get('width_review',{}).get('hard_minimum_3_passed')is not True:raise UserError('Fresh furnished room width>=3 is a hard source gate')
        require_physical_entries(s)
        field={tuple(v[:3]):v[3]for v in s['complete_expected_state_context_ONLY']}
        retained={};body=entry_body_points(s);existing={tuple(v['position']):v['state']for v in s.get('retained_existing_states',s.get('preserved_fixed_native_states',[]))}
        for q,value in existing.items():
            if field.get(q)!=value or any(tuple(t.get('position',t.get('pos',[])))==q for t in s.get('new_tags_ONLY',[])):raise UserError('Existing retained object needs exact state context and zero new tag replay')
            retained[q]=value;del field[q]
        for route in s.get('routes',[]):
            for v in route.get('feet_local',[]):
                x,y,z=(math.floor(v[k]+s['origin'][k])for k in range(3));body.update(((x,y,z),(x,y+1,z)))
        # Shared, identical context is retained without any block/tag replay.
        # A different proposed value at an actual earlier structure still holds.
        for q in set(field)&protected:
            prior=protected_states[q];own_floor=any(b[0]<=q[0]<=b[2]and b[1]<=q[2]<=b[3]for b in(m['bounds_xz']for m in s['masses']))
            if field[q]==prior or key(field[q])in AIR and key(prior)not in AIR and not own_floor and q not in body:
                retained[q]=prior;del field[q]
        conflicts=[q for q in field if keep(q)]
        if conflicts:
            source_holds.append({'id':row['id'],'held':True,'reason':'Preserve actual exempt/core/personal/owner work','protected_positions':[list(q)for q in conflicts]});continue
        if len(field)>20000:raise UserError('Split an ordinary compound above20000 settled targets')
        scope.update(field);sources.append((row,s,field));retained_context[row['id']]=retained
    if not 1<=len(sources)<=36:raise UserError('One finite1..36-compound owner-qualified ordinary schedule only')
    # Only the exact ready structures' construction/clearance cells. Do not
    # clear whole old houses or distant East land before its replacement is ready.
    touched={name:{q:v for q,v in field.items()if q in scope}for name,field in groups.items()if set(field)&scope}
    wanted=set(scope)
    if len(wanted)>150000:raise UserError('Finite ordinary direct target bound exceeded')
    terrain=NorthTerrain(home,receipt,registry);current={};bes={};started=time.monotonic()
    try:
        chunks=defaultdict(list)
        for q in wanted:chunks[q[0]//16,q[2]//16].append(q)
        for (cx,cz),points in sorted(chunks.items()):
            for q in points:
                v=terrain.state(*q)
                if v is None:raise UserError('UNKNOWN/FULL gap cannot become a fabricated before')
                current[q]=v
            raw=terrain.snapshot.regions[cx//32,cz//32];doc=decoded_chunk(raw,cx,cz)
            for tag in doc.get('block_entities',[]):
                q=tuple(int(tag[k])for k in('x','y','z'))
                if q in wanted:bes[q]=tag
            if time.monotonic()-started>90:raise UserError('Finite90s saved direct preimage bound')
        archive_sources=terrain.snapshot.sources
    finally:terrain.close()
    # These are known earlier owned operations bound to genuine whole-field
    # native structural proof, not a fabricated newer stopped-world snapshot.
    current.update({q:s for q,s in owned_current.items()if q in current})
    for q,value in owned_current.items():
        if key(value)in AIR:bes.pop(q,None)
    # This is explicitly a forecast AFTER the required ordinary current14
    # correction, never a fabricated stopped snapshot. The executor must
    # freshly verify the entire exact layer before resetting/retiring anything.
    for q,value in prior_layer.items():
        if q not in current:continue
        if q in bes:raise UserError('A preceding roof layer cannot silently replace a saved BE')
        current[q]=value
    retire={};reset={};reset_tags={};holds=[]
    for group,owned in touched.items():
        for q,old in owned.items():
            if keep(q)or key(old)in AIR:continue
            now=current[q]
            if key(now)in AIR:continue
            if key(now)!=key(old):holds.append({'position':list(q),'reason':'Current block identity is not this positively owned AI source','group':group});continue
            if 'waterlogged=true'in now or key(now)in('minecraft:water','minecraft:lava'):holds.append({'position':list(q),'reason':'No natural water/river replacement authority','group':group});continue
            if q in bes:
                ident=str(bes[q].get('id',''));definition=CLASSES.get(ident)
                if definition is None:holds.append({'position':list(q),'reason':'Unknown/nonstandard BE handler; retain for Root exact review','BE_id':ident});continue
                if definition[2]:reset[q]=now;reset_tags[q]='{Items:[]}'
                elif 'Items'in bes[q]or 'Book'in bes[q]:holds.append({'position':list(q),'reason':'Non-Container stored-item field requires exact ordinary native clear','BE_id':ident});continue
            retire[q]=now
    held_points={tuple(r['position'])for r in holds}
    eligible_scope=set()
    for row,s,field in sources:
        if not(set(field)&held_points)and not any(q in bes and q not in retire for q in field):eligible_scope.update(field)
    # A narrow held compound must not authorize preparing its whole bare lot.
    retire={q:v for q,v in retire.items()if q in eligible_scope}
    reset={q:v for q,v in reset.items()if q in eligible_scope};reset_tags={q:v for q,v in reset_tags.items()if q in eligible_scope}
    out=home/'staging'/('eastern-fresh-direct-'+str(time.time_ns()));out.mkdir();files={}
    def emit(name,field,tags=None):
        if not field:return None
        doc=json.loads(native_payload(registry,field,canonical['sha256'],'SOURCE ONLY '+name+'; Root fresh native admission required'))
        doc.update(construction_forbidden=True,verification_only=True,actual_saved_checkpoint=receipt,relocation_superseded_by_owner=True)
        if tags:doc['block_entities']=[{'pos':list(q),'nbt':v}for q,v in sorted(tags.items())]
        p=out/(name+'.json');p.write_text(json.dumps(doc,separators=(',',':'))+'\n',encoding='utf8');files[name]=reference(home,p);return files[name]
    emit('AI-stock-unchanged-blocks-BEFORE',reset)
    emit('AI-stock-empty-ordinary-DELTA',reset,reset_tags)
    emit('AI-stock-empty-AFTER',reset,reset_tags)
    emit('old-AI-grid-retirement-BEFORE',retire)
    emit('old-AI-grid-retirement-DELTA',{q:'minecraft:air'for q in retire})
    emit('old-AI-grid-retirement-AFTER',{q:'minecraft:air'for q in retire})
    records=list(source_holds)
    for row,s,field in sources:
        ident=row['id'];unknown_bes=[q for q in field if q in bes and q not in retire]
        local_holds=[h for h in holds if tuple(h['position'])in field]
        if unknown_bes or local_holds:
            records.append({'id':ident,'held':True,'protected_or_unreviewed_BE_positions':[list(q)for q in unknown_bes],'holds':local_holds});continue
        before={q:'minecraft:air'if q in retire else current[q]for q in field}
        tags={tuple(v.get('position',v.get('pos'))):v['nbt']for v in s.get('new_tags_ONLY',[])}
        if not set(tags)<=set(field):raise UserError('New fixture tag lies outside complete fresh structure')
        for value in tags.values():
            if not isinstance(value,str):raise UserError('Every new tag must be literal typed SNBT')
        full={**field,**retained_context[ident]}
        refs={'before':emit(ident+'-fresh-before',before),'place':emit(ident+'-fresh-full-PLACE-SOURCE',field,tags),
              'settle':emit(ident+'-fresh-normal-settle',{q:v for q,v in field.items()if key(v)not in AIR}),
              'after':emit(ident+'-fresh-complete-AFTER',full,tags)}
        existing={tuple(v['position']):v['state']for v in s.get('retained_existing_states',s.get('preserved_fixed_native_states',[]))}
        if existing:refs['retained-existing-before']=emit(ident+'-existing-objects-READONLY-BEFORE',existing)
        records.append({'id':ident,'name':row.get('name',ident),'fresh_direct_construction':True,'width_review':s['width_review'],'source':row['files']['SOURCE-ONLY'],
                        'files':refs,'targets':len(field),'new_tag_rows':len(tags),'retained_new_neighbor_context_cells':len(retained_context[ident]),'required_native_completed_moves':[],'no_original_capture_gates':True,'held':False})
    payload={'format':'awft-fresh-direct-eastern-ordinary-batch:1','created':utcnow(),'source_sha256':digest(Path(__file__)),'fresh_width_source_index':reference(home,Path(index)),
      'actual_saved_checkpoint':receipt,'native_plan_canonical_backup_sha256':canonical['sha256'],'compounds':records,'files':files,'AI_retirement_cells':len(retire),'AI_Container_reset_rows':len(reset),
      'actual_exempt_preserved':sorted(EXEMPT),'held_current_differences':holds,'protected_human_bounds':HUMAN,'original_core_north_bounds':CORE,'personal_anchor_positions':[list(q)for q in sorted(personal)],
      'archive_sources':archive_sources,'old_AI_exact_authored_sources':authored_refs,'native_actions':0,'construction_forbidden':True,'world_writes':0,'no_mover_or_clone_or_ledger_actions':True,
      'preceding_direct_source_context_preserved_without_replay':protected_direct,
      'current_context_after_owned_native_operations':current_ref,
      'required_prior_ordinary_after':prior_ref,'before_context_forecast_until_required_native_verify':bool(prior_ref),
      'order':['Fresh native unchanged-Container BEFORE, explicit ordinary sparse Items-empty load, native empty Items AFTER','Fresh native old-AI retirement BEFORE, ordinary AIR DELTA, native AIR AFTER; retain every held/personal point','Per ready compound: actual fresh before -> parent admit normal full place with NEW tags -> normal settle -> complete native after -> actual graphical review'],
      'actual_native_item_drop_or_art_acceptance_not_claimed':True}
    p=out/'manifest.json';p.write_text(json.dumps(payload,separators=(',',':'))+'\n',encoding='utf8')
    size=sum(p.stat().st_size for p in out.iterdir())
    if size>32*MIB:raise UserError('Finite32MiB output exceeded; preserve source')
    return {'folder':str(out),'manifest_sha256':digest(p),'ready':sum(not r['held']for r in records),'held_compounds':[r['id']for r in records if r['held']],'retire_cells':len(retire),'empty_Container_rows':len(reset),'held_points':len(held_points),'native_actions':0}

def execute(home,manifest,manifest_sha,lease,lease_sha):
    """One real event-bound ordinary batch, only after Root delegates a lease."""
    from copy import deepcopy
    from tools.eastern_city_execute import City,immutable
    home=Path(home).resolve();manifest=Path(manifest);m=checked(manifest,manifest_sha,2*MIB)
    if m.get('format')!='awft-fresh-direct-eastern-ordinary-batch:1'or m.get('no_mover_or_clone_or_ledger_actions')is not True:raise UserError('Exact fresh-direct ordinary source batch only')
    ready=[r for r in m['compounds']if not r['held']]
    if not ready:raise UserError('No width-qualified ready compound')
    # Check every source AND emitted complete plan before even the inventory
    # reset/retirement intent. Older frozen sources can contain windowed doors.
    for row in ready:
        src=checked(home/row['source']['path'],row['source']['sha256'],8*MIB)
        require_physical_entries(src)
        require_physical_entries(src,flatten(checked(home/row['files']['after']['path'],row['files']['after']['sha256'],8*MIB)))
    intent=manifest.parent/'ROOT-EXECUTION-INTENT.json'
    if intent.exists():raise UserError('This ordinary source batch was already attempted; preserve it, no automatic replay')
    job=City(home,lease,lease_sha);job.guard()
    immutable(intent,{'manifest_sha256':manifest_sha,'lease_sha256':lease_sha,'started':utcnow(),'once_only':True,'direct_fresh_not_relocation':True})
    results=[];applied={};applied_floor=set();applied_body=set();actual_prior=[]
    def verify(label,ref):
        p=home/ref['path'];checked(p,ref['sha256'],8*MIB);return job.step(label,'verify',p)
    def place(label,ref):
        doc=deepcopy(checked(home/ref['path'],ref['sha256'],8*MIB));doc.pop('verification_only',None);doc['construction_forbidden']=False
        doc['name']='ADMITTED owner-requested fresh AI-room replacement: '+label
        p=job.folder/(label+'-ADMITTED-PLACE.json');immutable(p,doc);return job.step(label,'place',p)
    try:
        f=m['files']
        if m.get('required_prior_ordinary_after'):verify('required-current14-ordinary-after-BEFORE-any-clearing',m['required_prior_ordinary_after'])
        for row in ready:
            if 'retained-existing-before'in row['files']:verify(row['id']+'-retained-existing-object-states',row['files']['retained-existing-before'])
        if 'AI-stock-empty-ordinary-DELTA'in f:
            verify('old-AI-stock-current-before',f['AI-stock-unchanged-blocks-BEFORE'])
            place('empty-only-owned-AI-Container-stock',f['AI-stock-empty-ordinary-DELTA'])
            verify('old-AI-Container-items-empty',f['AI-stock-empty-AFTER'])
        if 'old-AI-grid-retirement-DELTA'in f:
            verify('ready-footprints-owned-AI-before',f['old-AI-grid-retirement-BEFORE'])
            place('ready-footprints-owned-AI-retire',f['old-AI-grid-retirement-DELTA'])
            verify('ready-footprints-owned-AI-AIR',f['old-AI-grid-retirement-AFTER'])
        for row in ready:
            f=dict(row['files']);ident=row['id'];src=checked(home/row['source']['path'],row['source']['sha256'],8*MIB)
            before=flatten(checked(home/f['before']['path'],f['before']['sha256'],8*MIB));pd=checked(home/f['place']['path'],f['place']['sha256'],8*MIB);writes=flatten(pd);ad=checked(home/f['after']['path'],f['after']['sha256'],8*MIB);full=flatten(ad);own_body=entry_body_points(src)
            own_floor={(x,z)for b in(m['bounds_xz']for m in src['masses'])for x in range(b[0],b[2]+1)for z in range(b[1],b[3]+1)}
            for route in src.get('routes',[]):
                for v in route.get('feet_local',[]):
                    x,y,z=(math.floor(v[k]+src['origin'][k])for k in range(3));own_body.update(((x,y,z),(x,y+1,z)))
            retained=[]
            for q in set(writes)&set(applied):
                prior=applied[q];proposed=writes[q];before[q]=prior
                if proposed==prior:
                    del writes[q];before.pop(q,None);continue
                if key(prior)not in AIR:
                    if key(proposed)in AIR and(q[0],q[2])not in own_floor and q not in own_body:
                        full[q]=prior;retained.append(list(q));del writes[q];before.pop(q,None);continue
                    raise UserError('New nonAIR/room conflict requires an explicit exterior design merge; do not overwrite prior construction: '+str(q))
                if key(proposed)not in AIR and((q[0],q[2])in applied_floor or q in applied_body):raise UserError('A real prior room/body cannot become a neighboring projection: '+str(q))
            if applied:
                derived={}
                for label,field,tags in [('before',before,[]),('place',writes,pd['block_entities']),('after',full,ad['block_entities']),('settle',{q:s for q,s in writes.items()if key(s)not in AIR},[])]:
                    if any(tuple(t['pos'])not in field for t in tags):raise UserError('Never replay a new tag over a retained prior object')
                    doc=json.loads(native_payload(job.registry,field,job.backup,'Known current preceding owned construction '+ident+' '+label));doc.update(construction_forbidden=True,verification_only=True);doc['block_entities']=tags
                    p=job.folder/(ident+'-CURRENT-'+label+'.json');immutable(p,doc);derived[label]=reference(home,p)
                immutable(job.folder/(ident+'-current-context.json'),{'previous_actual_native_after':actual_prior,'retained_exterior_AIR_overlap_points':retained,'no_NonAIR_conflict_ignored':True});f=derived
            verify(ident+'-actual-before',f['before'])
            placed=place(ident+'-fresh-full',f['place']);job.step(ident+'-normal-shapes','settle',home/f['settle']['path'])
            after=verify(ident+'-complete-after',f['after']);p,sha=job.terminal(after,'settlement')
            mapped=job.step(ident+'-native-map','map',home/f['after']['path']);map_path,map_sha=job.terminal(mapped,'settlement')
            result={'id':ident,'actual_complete_native_after':{'path':p.relative_to(home).as_posix(),'sha256':sha},'actual_native_map_queue':{'path':map_path.relative_to(home).as_posix(),'sha256':map_sha},'targets':row['targets'],'direct_fresh_build':True,'mover_calls':0,'native_visual_acceptance':False}
            results.append(result);immutable(job.folder/(ident+'-DIRECT-BUILT.json'),result);applied.update(full);applied_floor.update(own_floor);applied_body.update(own_body);actual_prior.append(reference(home,p))
        immutable(job.folder/'DIRECT-BATCH-COMPLETE.json',{'results':results,'all_East_complete':False,'safe_lease_release_still_required':True})
        return {'folder':str(job.folder),'actually_built':results,'native_relocation_calls':0,'lease_requires_Root_safe_release':True}
    except BaseException as error:
        immutable(job.folder/'DIRECT-BATCH-STOPPED.json',{'error':str(error),'actually_built':results,'at':utcnow(),'no_automatic_replay':True});raise

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--home',type=Path,required=True);p.add_argument('--index',type=Path);p.add_argument('--index-sha');p.add_argument('--recovery-id');p.add_argument('--ids',nargs='*');p.add_argument('--preserve-manifest',action='append',default=[]);p.add_argument('--preserve-manifest-sha',action='append',default=[]);p.add_argument('--current-context',type=Path);p.add_argument('--current-context-sha');p.add_argument('--execute-manifest',type=Path);p.add_argument('--manifest-sha');p.add_argument('--lease');p.add_argument('--lease-sha');a=p.parse_args()
    if len(a.preserve_manifest)!=len(a.preserve_manifest_sha):p.error('Pair each preceding direct source manifest with its exact SHA')
    result=execute(a.home,a.execute_manifest,a.manifest_sha,a.lease,a.lease_sha)if a.execute_manifest else prepare(a.home,a.index,a.index_sha,a.recovery_id,a.ids,list(zip(a.preserve_manifest,a.preserve_manifest_sha)),a.current_context,a.current_context_sha)
    print(json.dumps(result,indent=2))
