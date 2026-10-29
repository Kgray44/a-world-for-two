"""Small upper casements above lower attached roofs; source geometry only.

A neighbouring ground footprint is not a wall at every height. Keep the lower
party wall, its real roof and all furnishings; glaze only a genuinely exposed
upper panel, with shutters attached to retained solid cheeks.
"""
from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
import math

from control_room.common import UserError
from tools.artistic_eastern_direct_build import entry_body_points, require_physical_entries
from tools.artistic_materials import require_material_rule

AIR={'minecraft:air','minecraft:cave_air','minecraft:void_air'}
PANELS={'minecraft:brown_terracotta','minecraft:gray_terracotta','minecraft:light_gray_terracotta'}
VECTORS={'north':(0,-1),'south':(0,1),'west':(-1,0),'east':(1,0)}


def key(value):
    return value.split('[',1)[0]


def field(source):
    return {tuple(row[:3]):row[3] for row in source['complete_expected_state_context_ONLY']}


def body_points(source):
    result=entry_body_points(source)
    for route in source.get('routes',[]):
        for row in route['feet_local']:
            x,y,z=(math.floor(row[k]+source['origin'][k]) for k in range(3))
            result.update(((x,y,z),(x,y+1,z)))
    return result


def exposed_casements(source, own, other_solids, other_columns, all_body):
    """Exact panel/roof geometry, never absence of a saved-world object.

    Returned outside cells still require actual saved and fresh native before
    proofs. The source-only geometry test does not fabricate world AIR.
    """
    changes={};details=[];used=set();other_top={}
    for x,y,z in other_solids:other_top[x,z]=max(y,other_top.get((x,z),-1024))
    fixed={tuple(row.get('position',row.get('pos'))) for row in source.get('new_tags_ONLY',[])}
    fixed.update(tuple(row['position']) for row in source.get('preserved_fixed_native_states',[]))
    roof_tops={row['mass']:source['origin'][1]+row['base'] for row in source['roof_sections']}
    ceilings={}
    for row in source['width_review']['floors']:
        ceilings[row['mass'],row['floor']]=roof_tops[row['mass']]
    for row in source['width_review']['floors']:
        if row['floor']==0:continue
        mass=row['mass'];level=row['feet_y']-1;top=ceilings[mass,row['floor']]
        later=[r['feet_y']-1 for r in source['width_review']['floors'] if r['mass']==mass and r['feet_y']-1>level]
        if later:top=min(later)
        x0,z0,x1,z1=source['masses'][mass]['bounds_xz']
        for face,(dx,dz) in VECTORS.items():
            horizontal=bool(dz);lo,hi=(x0+1,x1-1) if horizontal else(z0+1,z1-1)
            def wall(c,y):
                return (c,y,z0 if face=='north' else z1) if horizontal else(x0 if face=='west' else x1,y,c)
            for y in (level+1,level+2):
                if y+1>=top:continue
                eligible=[]
                for c in range(lo,hi):
                    panes=[wall(c+n,y+h) for n in(0,1) for h in(0,1)]
                    outside=[(q[0]+dx,q[1],q[2]+dz) for q in panes]
                    if any(key(own.get(q,'minecraft:air')) not in PANELS for q in panes):continue
                    if any(q in fixed or q in all_body or q in used or q in other_solids for q in panes+outside):continue
                    if any(key(own.get(q,'minecraft:air')) not in AIR for q in outside):continue
                    # This pass addresses exactly the attached-footprint case.
                    if not all((q[0],q[2]) in other_columns for q in outside):continue
                    # A roof or higher wall at this exact neighbouring column
                    # excludes the entire opening, not only its first voxel.
                    if any(other_top.get((q[0],q[2]),-1024)>=y for q in outside):continue
                    if any(abs(c-old)<4 for old in eligible):continue
                    eligible.append(c)
                for c in eligible:
                    panes=[wall(c+n,y+h) for n in(0,1) for h in(0,1)]
                    if any(q in used for q in panes):continue
                    local={q:f'mcwwindows:dark_oak_four_window[facing={face},windowstate=locked]' for q in panes}
                    # Two real projecting shutters attach to the unchanged
                    # panel/post cheeks, never to AIR or a neighbouring roof.
                    tx,tz=(1,0) if horizontal else(0,1)
                    for n,hinge in((-1,'left'),(2,'right')):
                        for h in(0,1):
                            back=wall(c+n,y+h);q=back[0]+dx,back[1],back[2]+dz
                            if(key(own.get(back,'minecraft:air')) not in PANELS|{'minecraft:stripped_dark_oak_log'}
                                or key(own.get(q,'minecraft:air')) not in AIR or q in other_solids or q in all_body or q in fixed):continue
                            local[q]=f'mcwwindows:dark_oak_louvered_shutter[facing={face},hinge={hinge},open=true]'
                    # The hood is a literal one-block projection from the
                    # retained full floor/ceiling tie above the window.
                    for n in(-1,0,1,2):
                        back=wall(c+n,y+2);q=back[0]+dx,back[1],back[2]+dz
                        if(key(own.get(back,'minecraft:air')) in AIR or key(own.get(q,'minecraft:air')) not in AIR
                            or q in other_solids or q in all_body or q in fixed):continue
                        local[q]=('chipped:reinforced_dark_oak_log[axis=x]' if tx
                            else 'chipped:edged_stripped_dark_oak_log[axis=z]')
                    if any(q in changes and changes[q]!=v for q,v in local.items()):raise UserError('Two explicit upper casements conflict')
                    changes.update(local);used.update(panes)
                    details.append({'mass':mass,'face':face,'floor_y':level,'window_lower':list(wall(c,y)),
                        'panes':4,'projecting_shutter_cells':sum('shutter' in v for v in local.values()),
                        'retained_lower_party_wall_and_adjacent_roof':True,'native_acceptance':False})
    return changes,details


def derive(sources, columns, *, include=None):
    """Compose independent occupied heights once across the exact final city."""
    fields={ident:field(source) for ident,source in sources.items()}
    occupied={ident:{q:v for q,v in value.items() if key(v) not in AIR} for ident,value in fields.items()}
    all_body=set().union(*(body_points(s) for s in sources.values()))
    results={};proof={}
    for ident,source in sources.items():
        if include is not None and ident not in include:continue
        other={q:v for k,value in occupied.items() if k!=ident for q,v in value.items()}
        other_columns=set().union(*(value for k,value in columns.items() if k!=ident))
        additions,details=exposed_casements(source,fields[ident],other,other_columns,all_body)
        if not additions:continue
        full={**fields[ident],**additions};copy=deepcopy(source)
        copy['complete_expected_state_context_ONLY']=[[*q,v] for q,v in sorted(full.items())]
        prospective={tuple(r[:3]):r[3] for r in source['blocks_PROSPECTIVE_DELTA']};prospective.update(additions)
        copy['blocks_PROSPECTIVE_DELTA']=[[*q,v] for q,v in sorted(prospective.items())]
        require_physical_entries(copy)
        material=require_material_rule(full,source['name']+' exposed upper casements')
        copy['attached_roof_clerestory_correction']={'details':details,'cells':[[*q,v] for q,v in sorted(additions.items())],
            'lower_shared_walls_roofs_tags_furniture_and_entry_routes_unchanged':True,
            'material_rule':material,'world_writes':0,'native_actions':0}
        results[ident]=copy;proof[ident]={'cells':len(additions),'windows':details}
    return results,proof


def prepare(home, index, index_sha, completed14, completed14_sha, recovery_id):
    """Additive ordinary field from actual14 proof and an authenticated snapshot."""
    import json,time
    from pathlib import Path
    from control_room.common import digest,read_json
    from tools.artistic_east_tortuga_retrofit import checked
    from tools.artistic_bridge_refinement import flatten
    from tools.artistic_city_planning_map import EAST,read
    from tools.artistic_captains_hall import native_payload
    from tools.artistic_north_bank_east import NorthTerrain
    from tools.artistic_north_rebuild_custody import decoded_chunk
    from tools.native_relocation_request import reference
    from tools.playtest import guard
    home=Path(home).resolve();guard(1024**2,64*1024**2)
    original=checked(Path(index),index_sha,2*1024**2)
    complete=checked(Path(completed14),completed14_sha,1024**2)
    fullref=complete['records'][-1]['plan'];proofref=complete['records'][-1]['actual_terminal']
    oldplan=checked(home/fullref['path'],fullref['sha256'],8*1024**2)
    proof=checked(home/proofref['path'],proofref['sha256'],1024**2)
    marker=(home/proofref['path']).with_name(Path(proofref['path']).name+'.complete')
    if(marker.read_text().strip()!=proofref['sha256'] or proof.get('operation')!='verify'
        or proof.get('plan_sha256')!=fullref['sha256'] or proof.get('failures')!=0
        or proof.get('blocks')!=len(oldplan['blocks']) or proof.get('cleanup_required')is not False
        or proof.get('temporary_tickets_remaining')!=0 or proof.get('pending_shared_chunk_futures')!=0
        or proof.get('error') or proof.get('ticket_cleanup_error')):raise UserError('Exact actual clean full14 verification required')
    sources={r['id']:checked(home/r['files']['SOURCE-ONLY']['path'],r['files']['SOURCE-ONLY']['sha256'],8*1024**2) for r in original['compounds']}
    columns={r['id']:set(map(tuple,r['actual_building_floor_columns_xz'])) for r in read(home,EAST)['buildings']}
    wanted={'bridge-cooper'}|{r['id']for r in original['compounds']if not r['actual_preexisting']}
    derived,details=derive(sources,columns,include=wanted)
    fields={ident:field(derived.get(ident,s)) for ident,s in sources.items()}
    solid={}
    for ident,values in fields.items():
        for q,v in values.items():
            if key(v) in AIR:continue
            if q in solid and solid[q][1]!=v:raise UserError('A new clerestory conflicts with another final building: '+str(q))
            solid[q]=ident,v
    changes={tuple(r[:3]):r[3]for r in derived['bridge-cooper']['attached_roof_clerestory_correction']['cells']}
    actual=flatten(oldplan);companion=read_json(home/'backups'/(recovery_id+'.json'))
    if companion.get('integrity')!='verified':raise UserError('Verified current stopped snapshot required')
    receipt={'id':recovery_id,'sha256':companion['sha256'],'verified':True}
    registry=read_json(home/'dashboard/settlement/registry.json');terrain=NorthTerrain(home,receipt,registry)
    baseline=dict(actual);new_points=set(changes)-set(actual);bes=set()
    try:
        for q in sorted(new_points):
            value=terrain.state(*q)
            if value is None:raise UserError('No unknown/nonFULL projected wall before')
            if key(value) not in AIR:raise UserError('A current facade projection is occupied: '+str(q))
            baseline[q]=value
        for cx,cz in {(q[0]//16,q[2]//16)for q in changes}:
            terrain.chunk(cx,cz);doc=decoded_chunk(terrain.snapshot.regions[cx//32,cz//32],cx,cz)
            bes.update(tuple(int(t[k])for k in('x','y','z'))for t in doc.get('block_entities',[]))
        archive_sources=terrain.snapshot.sources
    finally:terrain.close()
    if bes&changes.keys():raise UserError('No saved BE may enter a facade correction')
    oldfield=field(sources['bridge-cooper'])
    for q,v in changes.items():
        if q in oldfield and key(oldfield[q])not in AIR and baseline.get(q)!=oldfield[q]:raise UserError('Actual owned wall differs: '+str(q))
    after={**baseline,**changes}
    supports={(x,y,-1184):baseline[x,y,-1184]for x in range(1220,1228)for y in range(69,73)}
    out=home/'staging'/('eastern-attached-clerestories-'+str(time.time_ns()));out.mkdir();written=0
    def emit(name,doc):
        nonlocal written
        raw=(json.dumps(doc,separators=(',',':'))+'\n').encode();written+=len(raw)
        if written>32*1024**2:raise UserError('Finite32MiB clerestory output exceeded')
        path=out/(name+'.json');path.open('xb').write(raw);return reference(home,path)
    revised=deepcopy(original)
    for row in revised['compounds']:
        if row['id'] in derived:row['files']['SOURCE-ONLY']=emit(row['id']+'-SOURCE-ONLY',derived[row['id']])
    revised.update(attached_clerestories=details,prior_index=reference(home,Path(index)),native_actions=0,construction_forbidden=True)
    source_ref=emit('SOURCE-INDEX',revised)
    backup=read_json(home/'dashboard/settlement/backup-receipt.json')['sha256']
    def native(name,values):
        doc=json.loads(native_payload(registry,values,backup,'SOURCE attached-roof upper casements '+name))
        doc.update(verification_only=True,construction_forbidden=True,actual_saved_checkpoint=receipt);doc['block_entities']=[]
        return emit(name,doc)
    oldfolder=(home/fullref['path']).parent
    oldprotected=flatten(read_json(oldfolder/'protected-after.json'))
    oldlayer=flatten(read_json(oldfolder/'prerequisite-after.json'))
    files={'before':native('cooper-BEFORE',{**{q:baseline[q]for q in changes},**supports}),
        'delta':native('cooper-DELTA',changes),'settle':native('cooper-normal-settle',changes),
        'after':native('complete14-AFTER',after),'prerequisite-after':native('required-current14-plus-casements-AFTER',{**oldlayer,**changes}),
        'protected-after':native('protected14-plus-casements-AFTER',{**oldprotected,**changes})}
    preservation={'format':'awft-fresh-direct-eastern-ordinary-batch:1','compounds':[{'id':'actual14-and-proposed-upper-casements','held':False,'files':{'after':files['protected-after']}}],
        'forecast_not_actual_native_proof':True,'required_native_verify_before_future25':files['prerequisite-after']}
    files['preservation-manifest']=emit('preservation-manifest',preservation)
    manifest={'format':'awft-attached-roof-clerestory-correction:1','source_index':source_ref,'files':files,'source_changes':details,
        'actual14_completion':reference(home,Path(completed14)),'actual_saved_checkpoint':receipt,'archive_sources':archive_sources,
        'actual_current_saved_BE_write_intersections':0,'NBT_or_inventory_writes':0,'write_targets':len(changes),
        'complete_after_points':len(after),'native_actions':0,'construction_forbidden':True}
    ref=emit('manifest',manifest)
    return {'folder':str(out),'manifest_sha256':ref['sha256'],'source_index':source_ref,'files':files,'changes':details,'native_actions':0}
