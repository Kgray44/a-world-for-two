"""Unified98 one-archive SOURCE preparation for the approved eastern relocation pipeline.

All exports are construction-forbidden. Full native source verification,
inspection, one once-only MOVE and actual conservation are Root-only actions.
Ordinary shell/floor proposals may never overwrite an unmoved capsule or BE.
"""
from __future__ import annotations
import argparse,json,hashlib,time
from collections import defaultdict,Counter
from pathlib import Path
import nbtlib
from control_room.common import UserError,digest,read_json
from tools.artistic_captains_hall import native_payload
from tools.artistic_bridge_refinement import flatten
from tools.artistic_east_tortuga_retrofit import checked,with_exact_be_tags
from tools.artistic_eastern_move_blueprint import cells,GROUND
from tools.artistic_eastern_urban_custody import before_sources,canonical
from tools.artistic_maritime_depth import admit_owner
from tools.artistic_north_rebuild_custody import decoded_chunk
from tools.artistic_zipline_catenary import reader_budget
from tools.native_eastern_relocation import PIPPIN
from tools.native_eastern_relocation import LAYOUT
from tools.native_eastern_relocation_r7 import CATALOG_SHA as SEALED_CATALOG_SHA,CATALOG
from tools.native_eastern_relocation_current import cover_history
from tools.playtest import guard
from tools.settlement_attractions import BackupWorld,unpack_section,properties

MIB=1024**2
MAX_OUTPUT=32*MIB
AIR={'minecraft:air','minecraft:cave_air','minecraft:void_air'}
STURDY=GROUND|{'minecraft:dark_oak_planks','minecraft:spruce_planks','minecraft:oak_planks','minecraft:stripped_dark_oak_log','minecraft:stripped_spruce_log','minecraft:stripped_spruce_wood','chipped:cross_laced_spruce_planks'}
TEMPORARY_NONFALLING={'minecraft:dark_oak_planks','minecraft:spruce_planks','minecraft:oak_planks','minecraft:stripped_dark_oak_log','minecraft:stripped_spruce_log','minecraft:stripped_spruce_wood','minecraft:stone','minecraft:stone_bricks','minecraft:cobblestone','minecraft:polished_andesite','chipped:cross_laced_spruce_planks'}


def state_matches(authored,actual):
    return authored.split('[',1)[0]==actual.split('[',1)[0] and all(properties(actual).get(k)==v for k,v in properties(authored).items())


def topo(rows,dependencies):
    remain=set(rows);ordered=[]
    while remain:
        ready=[i for i in remain if not(dependencies[i]&remain)]
        if not ready:return ordered,sorted(remain)
        ready.sort(key=lambda i:(-rows[i]['destination_bounds_xyz'][1],i));i=ready[0];ordered.append(i);remain.remove(i)
    return ordered,[]


def prepare(home):
    home=Path(home).resolve();reserve=guard(2*MIB,MAX_OUTPUT);budgets=[reader_budget()];began=time.monotonic()
    receipt=read_json(home/'dashboard/settlement/backup-receipt.json');registry=read_json(home/'dashboard/settlement/registry.json')
    admit_owner(home,read_json(home/'dashboard/artistic-owner.json'),receipt,receipt['id'],receipt['sha256'])
    catalog=checked(home/CATALOG,SEALED_CATALOG_SHA,2*MIB);rows={r['id']:r for r in catalog['capsules']};layout=checked(home/LAYOUT[0],LAYOUT[1],8*MIB)
    houses,authored,_,ownership_refs,_=before_sources(home);wanted=set(authored);source_owners=defaultdict(set);future_be=defaultdict(set);source_be_owner={};prepared={}
    for r in rows.values():
        sp=cells(r['source_bounds_xyz']);dp=cells(r['destination_bounds_xyz']);b=r['destination_bounds_xyz'];support={(x,b[1]-1,z) for x in range(b[0],b[3]+1) for z in range(b[2],b[5]+1)}
        wanted|=sp|dp|support
        for q in sp:source_owners[q].add(r['id'])
        doc=checked(home/r['source_original']['path'],r['source_original']['sha256'],MIB);d=r['translation_xyz']
        for be in doc['block_entities']:
            q=tuple(be['pos']);source_be_owner[q]=r['id'];future_be[tuple(q[i]+d[i] for i in range(3))].add(r['id'])
        prepared[r['id']]=(sp,dp,support,doc)
        for q,state in flatten(doc).items():
            if state.startswith('mcwwindows:'):
                for dx,dy,dz in ((1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1)):
                    neighbor=(q[0]+dx,q[1]+dy,q[2]+dz);wanted.add(neighbor);wanted.add(tuple(neighbor[i]+r['translation_xyz'][i] for i in range(3)))
    if len(wanted)>240000:raise UserError('Finite shared eastern field exceeds200k cells')
    grouped=defaultdict(list)
    for q in wanted:grouped[q[0]//16,q[2]//16].append(q)
    snapshot=None;saved={};bes={}
    try:
        snapshot=BackupWorld(home,receipt,registry);name=snapshot.prefix+'r.2.-3.mca';meta=snapshot.files[name]
        if not 8192<=meta['size']<=48*MIB:raise UserError('One finite authenticated MCA')
        raw=snapshot.archive.read(name)
        if hashlib.sha256(raw).hexdigest()!=meta['sha256']:raise UserError('Saved shared field identity differs')
        for (cx,cz),positions in sorted(grouped.items()):
            doc=decoded_chunk(raw,cx,cz);sections={int(s['Y']):s for s in doc.get('sections',[])}
            for q in positions:saved[q]=unpack_section(sections.get(q[1]//16,{}),*q)
            for be in doc.get('block_entities',[]):
                q=tuple(int(be[k]) for k in ('x','y','z'))
                if q in wanted:bes[q]=be
            del doc,sections;budgets.append(reader_budget())
            if time.monotonic()-began>120:raise UserError('Bounded shared saved-field read exceeded120seconds')
        region={'file':name.rsplit('/',1)[-1],'sha256':meta['sha256'],'bytes':len(raw)}
    finally:
        if snapshot:snapshot.close()
    # Actual point-in-time Native50 cover history authorizes exactly these AIR
    # differences, never a broad source baseline change.
    cover_history(home)
    deps={i:set(r['dependencies']) for i,r in rows.items()};support_order_edges=[];support_current_be_edges=[]
    for ident,r in rows.items():
        support=prepared[ident][2]
        for q in support:
            for lower in future_be.get(q,()):
                if lower!=ident:deps[lower].add(ident);support_order_edges.append([ident,lower])
            if q in source_be_owner and source_be_owner[q]!=ident:deps[ident].add(source_be_owner[q]);support_current_be_edges.append([source_be_owner[q],ident])
    ordered,cycles=topo(rows,deps);out=home/'staging'/('eastern98-ordinary-pipeline-'+str(time.time_ns()));out.mkdir();written=0
    def write(name,data):
        nonlocal written
        written+=len(data)
        if written>MAX_OUTPUT:raise UserError('Finite output exceeded; partial source artifacts retained')
        (out/name).open('xb').write(data);return {'path':(out/name).relative_to(home).as_posix(),'bytes':len(data),'sha256':digest(out/name)}
    def payload(name,field,tags=None):return with_exact_be_tags(native_payload(registry,field,receipt['sha256'],name),tags or {})
    assessments=[];known_skin={q:saved[q] for q,s in authored.items() if q in saved and s.split('[',1)[0] not in AIR and q not in bes and s.split('[',1)[0]==saved[q].split('[',1)[0]}
    future_capsule_columns=set().union(*(v[1] for v in prepared.values()))
    private_anchor={(1296,65,-1250),(1296,65,-1249),(1300,65,-1255)}
    retained_pending_boxes=[r['source_support_bounds_xyz'] for r in layout['retained_in_place_private_anchor_Inn_room_capsules']]
    pending_private=set()  # All three former private rooms now have real captured destinations; actual native custody still gates retirement
    # Latest owner requires these to MOVE, not stay as an accepted grid house.
    # Until that genuine new destination exists, no ordinary deletion substitutes
    # for preserving/moving the actual bed, POI and room contents.
    ghost={q:'minecraft:air' for q in known_skin if saved[q].split('[',1)[0] not in AIR and q not in future_capsule_columns and q not in private_anchor and q not in pending_private}
    ghost_before={q:saved[q] for q in ghost};shared=[{'position':list(q),'actual':saved[q],'capsules':sorted(ids)} for q,ids in source_owners.items() if len(ids)>1 and saved[q].split('[',1)[0] not in AIR]
    virtual=dict(saved);virtual_bes=dict(bes)
    for index,ident in enumerate(ordered+cycles):
        r=rows[ident];sp,dp,support,original=prepared[ident];tags={q:virtual_bes[q] for q in sp if q in virtual_bes};sf={q:virtual[q] for q in sp};df={q:virtual[q] for q in dp};pf={q:virtual[q] for q in support}
        src_covers={tuple(v['position']):v['before'] for v in r['source_cover_preparations']};dst_covers={tuple(v['position']):v['before'] for v in r['destination_cover_preparations']}
        source_preps={q:'minecraft:air' for q,s in src_covers.items() if sf[q]==s};dest_preps={q:'minecraft:air' for q,s in dst_covers.items() if df[q]==s and q not in bes}
        source_target=dict(flatten(original));expected_tags={tuple(v['pos']):nbtlib.parse_nbt(v['nbt']) for v in original['block_entities']}
        for q in src_covers:source_target[q]='minecraft:air'
        blockers=Counter();requires=set(deps[ident]);retire={};held=[];plane={};source_restore=[];temporary_release={};floor_source_holds=[]
        for q,s in df.items():
            if s.split('[',1)[0] in AIR:continue
            if q in virtual_bes:
                owner=source_be_owner.get(q)
                if owner:requires.add(owner);blockers['await_actual_captured_inventory_move']+=1
                else:blockers['accepted_private_or_unknown_BE_HOLD']+=1;held.append(list(q))
            elif q in dest_preps:blockers['exact_ordinary_cover_prep']+=1
            elif q in known_skin:
                retire[q]='minecraft:air';requires|=source_owners.get(q,set());blockers['owned_old_skin_after_custody']+=1
            else:blockers['unowned_nonAIR_HOLD']+=1;held.append(list(q))
        for q,s in pf.items():
            if q in virtual_bes:
                blockers['current_BE_in_support_plane_HOLD']+=1
            elif s.split('[',1)[0] not in STURDY or properties(s).get('waterlogged')=='true':
                # Explicit prospective ceiling/joist plane, wholly below the
                # already-approved destination mass floor. Before/addition is
                # ordinary geometry only; no inventory overwrite is supplied.
                b=r['destination_bounds_xyz'];house=next(h for h in layout['buildings'] if h['id']==r['destination_building']);m=house['masses'][r['destination_mass']]
                floor_inside=m['bounds_xz'][0]<=q[0]<=m['bounds_xz'][2] and m['bounds_xz'][1]<=q[2]<=m['bounds_xz'][3]
                if floor_inside and (s.split('[',1)[0] in AIR or q in known_skin):
                    plane[q]='minecraft:stripped_spruce_log[axis=x]' if (q[2]-b[2])%4==0 else 'minecraft:spruce_planks';requires|=source_owners.get(q,set());blockers['approved_mass_floor_support_patch']+=1
                else:blockers['unknown_or_wet_foundation_HOLD']+=1
            if future_be.get(q):blockers['do_upper_move_before_lower_BE_at_same_support_plane']+=1
        for q in sp:
            if len(source_owners[q])>1 and saved[q].split('[',1)[0] not in AIR:source_restore.append({'position':list(q),'known_nonBE_structure':saved[q],'other_captures':sorted(source_owners[q]-{ident}),'gate':'If earlier native MOVE cleared this shared support, a separately reviewed structural-only restoration with actual AIR-before is required; never replay a prior MOVE'})
        # A temporary full-face construction support may not corrupt a later
        # room's captured AIR. Release only below a copied ordinary full cube;
        # otherwise that support write remains held for the pending capture.
        for q in plane:
            if q in sp and source_target[q]!=plane[q]:
                floor_source_holds.append({'position':list(q),'requires_native_source_captures':[ident],'reason':'Destination support patch changes OWN immutable source; no operation admitted until genuine allocation/height correction'})
                continue
            pending=source_owners.get(q,set())-set(ordered[:index])-{ident}
            if not pending:continue
            above=(q[0],q[1]+1,q[2]);source_above=tuple(above[i]-r['translation_xyz'][i] for i in range(3))
            above_state=source_target.get(source_above,'minecraft:air')
            if pf[q].split('[',1)[0] in AIR and above_state.split('[',1)[0] in TEMPORARY_NONFALLING and source_above not in expected_tags:
                temporary_release[q]=pf[q]
            else:floor_source_holds.append({'position':list(q),'requires_native_source_captures':sorted(pending),'reason':'Support write changes an uncaptured full source; no safe ordinary-full-cube release proved'})
        released_owners=set().union(*(source_owners.get(q,set()) for q in temporary_release)) if temporary_release else set()
        for owner in released_owners:
            if owner not in deps[ident] and not any(owner in source_owners.get(q,set()) for q in plane if q not in temporary_release):requires.discard(owner)
        window_context=[]
        for p,state in source_target.items():
            if not state.startswith('mcwwindows:'):continue
            for dx,dy,dz in ((1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1)):
                q=(p[0]+dx,p[1]+dy,p[2]+dz)
                if q in sp:continue
                neighbor=virtual[q]
                if neighbor.split('[',1)[0]!=state.split('[',1)[0] or properties(neighbor).get('facing')!=properties(state).get('facing'):continue
                target=tuple(q[i]+r['translation_xyz'][i] for i in range(3));seen=virtual[target]
                window_context.append({'source_context':list(q),'source_state':neighbor,'destination_context':list(target),'forecast_destination_state':seen,
                    'matching_block_facing_in_forecast':seen.split('[',1)[0]==neighbor.split('[',1)[0] and properties(seen).get('facing')==properties(neighbor).get('facing'),
                    'new_partner_automatic_placement':False,'gate':'Root must independently fit/admit/verify real non-BE partners. Native helper repeats current block/facing/BE/fluid checks BEFORE intent; no part/survival relaxation'})
        files={}
        restore={q:s for q,s in source_target.items() if sf[q]!=s and sf[q].split('[',1)[0] in AIR and s.split('[',1)[0] not in AIR and q not in expected_tags}
        fields=(('source-current-before',sf,tags),('source-prepared-FUTURE',source_target,expected_tags),('destination-current-before',df,{q:virtual_bes[q] for q in dp if q in virtual_bes}),('destination-empty-FUTURE',{q:'minecraft:air' for q in dp},{}),('supports-current-before',pf,{q:virtual_bes[q] for q in support if q in virtual_bes}))
        for label,field,tag in fields:files[label]=write(f'{index:03d}-{label}.json',payload('SOURCE '+ident+' '+label+'; actual/future role explicit; NEVER replay inventory',field,tag))
        future_support=dict(pf);future_support.update(plane)
        files['supports-prepared-FUTURE']=write(f'{index:03d}-supports-prepared-FUTURE.json',payload('PROSPECTIVE support plane AFTER all prerequisite captures/floor patch; never claimed observed',future_support))
        gm={'format':'awft-approved-capsule-geometry:2','capsule_id':ident,'catalog':{'path':CATALOG,'sha256':SEALED_CATALOG_SHA,'bytes':(home/CATALOG).stat().st_size},'checkpoint_id':receipt['id'],'checkpoint_sha256':receipt['sha256'],'files':{'source-prepared-FUTURE-VERIFY-ONLY.json':files['source-prepared-FUTURE'],'destination-empty-FUTURE-VERIFY-ONLY.json':files['destination-empty-FUTURE'],'retained-supports-VERIFY-ONLY.json':files['supports-prepared-FUTURE']},'operation_role':'FORECAST after explicitly listed ordinary preparations and real prerequisite native captures; all live native before proofs STILL REQUIRED','native_actions':0,'current_native_before_proved':False}
        geometry_ref=write(f'{index:03d}-geometry-manifest.json',canonical(gm)+b'\n')
        for label,field in (('source-cover-DELTA',source_preps),('source-shared-structure-DELTA',restore),('destination-cover-DELTA',dest_preps),('owned-skin-DELTA',retire),('support-plane-DELTA',plane)):
            if field:
                files[label+'-before']=write(f'{index:03d}-{label}-before.json',payload('FORECAST expected before after listed prior real captures; fresh actual native proof REQUIRED',{q:virtual[q] for q in field}))
                files[label]=write(f'{index:03d}-{label}.json',payload('FORBIDDEN prospective ordinary structure only; require all custody/native before gates',field))
        if temporary_release:
            files['temporary-support-release-before']=write(f'{index:03d}-temporary-support-release-before.json',payload('FORECAST own temporary support AFTER genuine clean custody and before any later source capture',{q:plane[q] for q in temporary_release}))
            files['temporary-support-release-DELTA']=write(f'{index:03d}-temporary-support-release-DELTA.json',payload('FORBIDDEN conditional temporary support release: actual copied ordinary full cube above, zero BE targets, fresh live before and actual custody required',temporary_release))
            files['permanent-support-after-all-captures-DELTA']=write(f'{index:03d}-permanent-support-after-all-captures-DELTA.json',payload('FORBIDDEN permanent original mass-floor support only AFTER every affected source captured; before new wrapper/decor; fresh native before required',{q:plane[q] for q in temporary_release}))
        # Simulate explicit proposed operations only to define the NEXT row's
        # expected before. This is not a claim any native operation occurred.
        for operation in (source_preps,restore,dest_preps,retire,plane):virtual.update(operation)
        for q in sp:virtual[q]='minecraft:air';virtual_bes.pop(q,None)
        delta=r['translation_xyz']
        for q,s in source_target.items():virtual[tuple(q[i]+delta[i] for i in range(3))]=s
        import copy
        for q,tag in expected_tags.items():
            target=tuple(q[i]+delta[i] for i in range(3));moved=copy.deepcopy(tag)
            for key,value in zip(('x','y','z'),target):moved[key]=nbtlib.Int(value)
            virtual_bes[target]=moved
        virtual.update(temporary_release)
        poi_ids={'minecraft:cartography_table','minecraft:smithing_table','minecraft:fletching_table','minecraft:grindstone','minecraft:anvil','minecraft:chipped_anvil','minecraft:damaged_anvil','minecraft:loom','minecraft:composter','minecraft:crafting_table','minecraft:stonecutter','minecraft:enchanting_table'}
        utility=[{'position':[q[i]+r['translation_xyz'][i] for i in range(3)],'state':state} for q,state in source_target.items() if state.split('[',1)[0] in poi_ids]
        assessments.append({'capsule_id':ident,'rank':index,'supported_inventory_role':r['supported'],'original_catalog_holds':r['holds'],'required_preceding_native_captures':sorted(requires-{ident}),
            'classification_counts':dict(blockers),'unknown_held_positions_first':held[:16],'exact_shared_nonBE_support_followup':source_restore,
            'new_support_plane_never_overwrites_BE':True,'geometry_manifest':geometry_ref,'existing_invoked_transaction_never_move_again':ident==PIPPIN,
            'conditional_temporary_support_release_cells':len(temporary_release),'additional_floor_source_holds':floor_source_holds,'external_MCW_window_context':window_context,'preserve_translated_nonBE_functional_points':utility,
            'files':files,'native_before_inspection_move_conservation':'NOT RUN','automatic_execution':False})
    uncaptured_BE={q for q in bes if q not in source_be_owner}
    protected_uncaptured_supports={(q[0]+x,q[1]+y,q[2]+z) for q in uncaptured_BE for x in range(-1,2) for y in range(-1,2) for z in range(-1,2)}
    ghost_held_unknown_supports=[q for q in ghost if q in protected_uncaptured_supports]
    ghost={q:'minecraft:air' for q in ghost if virtual[q].split('[',1)[0] not in AIR and q not in virtual_bes and q not in protected_uncaptured_supports}
    ghost_before={q:virtual[q] for q in ghost}
    if ghost:
        ghostrefs={'before':write('old-grid-skin-before-VERIFY-ONLY.json',payload('Actual saved positively owned unchanged old non-BE skin only; no BE target',ghost_before)),
            'retire':write('old-grid-skin-retirement-SOURCE-ONLY.json',payload('PROSPECTIVE old grid ghost-shell removal only after required complete native inventory custody; future moved-capsule volumes excluded',ghost))}
    else:ghostrefs={}
    # A per-house gate prevents an ordinary roof/skin operation from discarding
    # the still-occupied source of a different transfer/compound.
    groups=defaultdict(dict);group_gates={};house_columns=[]
    for h in houses:
        cols={tuple(p) for p in h.get('main_footprint',[])}
        expanded={(x+dx,z+dz) for x,z in cols for dx in (-1,0,1) for dz in (-1,0,1)}
        house_columns.append((h,expanded))
    for q in ghost:
        owners=[h['id'] for h,cols in house_columns if (q[0],q[2]) in cols and h['floor_y']-1<=q[1]<=h['floor_y']+4*h.get('storeys',1)+8]
        needed=set(source_owners.get(q,set()))
        for owner in owners:needed|={ident for ident in rows if ident.rsplit(':room:',1)[0]==owner}
        label='|'.join(sorted(owners)) or 'owned-eastern-shared-ground'
        groups[label][q]='minecraft:air';group_gates.setdefault(label,set()).update(needed)
    skin_batches=[]
    for index,(label,field) in enumerate(sorted(groups.items())):
        bef=write(f'skin-{index:02d}-before-VERIFY-ONLY.json',payload('FORECAST old owned NONBE skin after ALL required real captures; NOT observed',{q:virtual[q] for q in field}))
        delta=write(f'skin-{index:02d}-retire-SOURCE-ONLY.json',payload('Prospective old grid skin retirement ONLY after all listed real native captures, no BE target',field))
        skin_batches.append({'group':label,'cells':len(field),'required_completed_native_capsules':sorted(group_gates[label]),'before':bef,'delta':delta,
            'live_refresh_required':'After completed moves, re-read CURRENT stopped archive, omit actual AIR and every actual/moved/new authored BE/geometry. Never replay these historical before states.',
            'construction_forbidden':True})
    result={'format':'awft-eastern-serial-relocation-and-retirement-pipeline:1','checkpoint_id':receipt['id'],'checkpoint_sha256':receipt['sha256'],'catalog_sha256':SEALED_CATALOG_SHA,
        'source_sha256':digest(Path(__file__)),'catalogue_is_immutable':True,'source_capsules':98,'supported_inventory_capsules':98,'topological_with_upper_before_lower_support_priority':ordered,'conditional_cycle_holds':cycles,
        'additional_floor_order_edges':sorted(set(map(tuple,support_order_edges))),'additional_current_support_BE_edges':sorted(set(map(tuple,support_current_be_edges))),
        'room_assessments':assessments,'shared_source_nonAIR_cells':shared,'old_ghost_skin_cells_excluding_future_capsule_volumes':len(ghost),'old_skin_files':ghostrefs,
        'held_skin_supports_near_uncaptured_current_BE':list(map(list,ghost_held_unknown_supports)),
        'all_before_fields_are':'FORECAST after explicit prerequisite real operations, NOT observed current state; each requires fresh actual native verification',
        'old_skin_gate':'Root must prove every affected original-house capsule conserved before its shell retirement. No unmoved capsule/BE/private anchor/accepted original is removal authority; current differences are held.',
        'old_skin_batches':skin_batches,'temporary_pending_private_relocation_cells_excluded':len(pending_private),
        'source_ownership_refs':ownership_refs,'actual_saved_BE_count_in_shared_field':len(bes),'actual_saved_field_cells':len(saved),'one_archived_region':region,'reader_peak_RSS':max(v['owned_reader_rss_bytes'] for v in budgets),
        'remaining_live_gates':['All98 must pass fresh actual native state/fulltag/slot/model/empty-source and same-tick admission','Toolbox requires native32-slot/filter/UUID/actual+saved link proof','Pippin already invoked53: read-only audit + independent reviewed custody only; NEVER another MOVE','BoundaryMCW partners need ordinary architecture proof before any move intent'],
        'runner_outline':['1 ROOT-only latest checkpoint/pack/class/source proof and no actual players/other native owner','2 Verify real current SOURCE and target/preparation fields; never replay stale snapshot data','3 Complete prerequisite once-only native captures; ordinary skin/floor preparations require actual before and scoped authorization','4 Native full verify SOURCE/empty DEST/sturdy SUPPORTS -> exact helper INSPECT -> one separately bound MOVE','5 Keep real clean conservation terminal; any error/uncertain/intent QUARANTINE stops that capsule, never auto-retry','6 Upper-first support ordering protects lower stock. Classified cycles/unknown foundations/shared structural state are explicit holds','7 After affected old inventories conserved, retire owned old ghost skin; build new muted compound architecture, preserve all moved actual BE/Items','8 Real full native verify/collision/doors/stairs/normal restart and framebuffer views before acceptance'],
        'construction_forbidden':True,'native_actions':0,'world_writes':0,'reserve_guard':reserve}
    write('pipeline-SOURCE-ONLY.json',canonical(result)+b'\n');manifest={'format':'awft-eastern-bulk-pipeline-bundle:1','pipeline_sha256':digest(out/'pipeline-SOURCE-ONLY.json'),'files':{p.name:{'sha256':digest(p),'bytes':p.stat().st_size} for p in out.iterdir()},'output_bytes':written,'native_actions':0}
    (out/'manifest.json').write_bytes(canonical(manifest)+b'\n');return {'folder':str(out),'manifest_sha256':digest(out/'manifest.json'),'pipeline_sha256':manifest['pipeline_sha256'],'rooms':len(assessments),'ordered':len(ordered),'cycles':cycles,'old_skin_cells':len(ghost),'bytes':written}


def bind_row(home,manifest_path,manifest_sha,ident,bridge_jar,owner_review,owner_review_sha,proofs,*,action='inspect',**kwargs):
    """No MCA read, request installation or native action: Root supplies proofs."""
    home=Path(home).resolve();manifest=checked(Path(manifest_path),manifest_sha,2*MIB);folder=Path(manifest_path).resolve().parent
    pipeline=checked(folder/'pipeline-SOURCE-ONLY.json',manifest['pipeline_sha256'],16*MIB)
    if pipeline['catalog_sha256']!=SEALED_CATALOG_SHA or pipeline['source_capsules']!=98:raise UserError('Exact reviewed98 packet required')
    chosen=[r for r in pipeline['room_assessments'] if r['capsule_id']==ident]
    if len(chosen)!=1:raise UserError('One exact packet row required')
    row=chosen[0]
    if ident==PIPPIN and action in ('inspect','move'):raise UserError('Pippin was actually invoked53; NEVER MOVE again. Use read-only quarantine audit and independent current custody record')
    if row['additional_floor_source_holds']:raise UserError('Ordinary support source conflicts are held; no implicit source alteration')
    from tools.native_eastern_relocation_r7 import bind
    gm=row['geometry_manifest'];return bind(home,home/gm['path'],gm['sha256'],bridge_jar,owner_review,owner_review_sha,proofs,action=action,**kwargs)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--home',type=Path,required=True);a=p.parse_args();print(json.dumps(prepare(a.home),indent=2))
