"""Bounded current-fourteen entry corrections from genuine Native after proofs.

No operation is sent. Existing inventories/tags are never loaded. Only original
intended door halves and positively identified low threshold fittings may change.
"""
from __future__ import annotations
import argparse,json,time
from pathlib import Path
from control_room.common import UserError,digest,read_json
from tools.artistic_bridge_refinement import flatten
from tools.artistic_eastern_compound_sprint import intended_entry_states,key
from tools.artistic_north_bank_east import native_payload
from tools.playtest import guard

MIB=1024**2
OLD_INDEX='staging/eastern39-architecture-source-index-1793227833374305600/architecture39-SOURCE-INDEX.json'
FRESH_INDEX='staging/eastern-fresh-36-width-complete-1793234231506694900/SOURCE-INDEX.json'
OLD_JOB='staging/EAST-FIRST-THREE-ADMITTED55-1793224100061542000'
OLD_PROOFS={
 'east-coal':('5f1b3eb6-e3a6-4883-ae51-9aa8bde3d0e7','c861c7c543a72f044970307109ce5415ac2374c4aa11c8e17008e5416ca29672'),
 'shoal-warden':('bf46b935-fcc2-494a-a3ae-1c247c2fb1c5','3ebd0884e113c92f85766d110e689a6130922525fc79b2fe2fb8bd5e091e0e8a'),
 'thin-sail':('75f9e3c9-3876-4097-9363-4ea9c6ef32ad','878c706b7232f7a19f845908cda87f3015606cb91d3dd670d6026df80d9d9558')}
JOBS={
 'staging/east-city58-execution-1793233659515228700':('white-clam','copper-bell','tide-fish'),
 'staging/east-city58-execution-1793233960767490700':('worn-book','bridge-customs','crooked-inn','lampblack','moon-branch','nail-drift'),
 'staging/east-city58-execution-1793234305341844600':('bridge-cooper','keel-store')}
LOW_FITTINGS={'mythrais:curved_corbel_dark_oak','fishofthieves:potted_white_plumeria'}


def checked(path,sha=None,cap=8*MIB):
    if path.is_symlink()or not path.is_file()or not 0<path.stat().st_size<=cap or(sha and digest(path)!=sha):raise UserError('Exact finite immutable Source/proof required: '+str(path))
    return read_json(path)


def complete_proof(home,path,sha):
    d=checked(path,sha,MIB)
    if path.with_name(path.name+'.complete').read_text().strip()!=sha or d.get('operation')!='verify'or d.get('failures')!=0 or d.get('cleanup_required')is not False or d.get('temporary_tickets_remaining')!=0 or d.get('pending_shared_chunk_futures')!=0 or d.get('error')or d.get('ticket_cleanup_error'):
        raise UserError('Genuine complete clean Native verification required')
    return d


def actual_sources(home):
    """Return Source metadata plus actual COMPOSED verified fields, not forecasts."""
    old=checked(home/OLD_INDEX);fresh=checked(home/FRESH_INDEX);rows={r['id']:r for r in old['compounds']};rows.update({r['id']:r for r in fresh['compounds']})
    result=[];original=checked(home/OLD_JOB/'actual-native-results.json')
    for ident,(uid,sha)in OLD_PROOFS.items():
        p=home/'dashboard/settlement'/('settlement-result-'+uid+'.json');proof=complete_proof(home,p,sha)
        row=next(r for r in original if r['building']==ident and r['action']=='verify');plan=Path(row['actual_plan']);doc=checked(plan,proof['plan_sha256']);field=flatten(doc)
        if len(field)!=proof['blocks']:raise UserError('Actual original-three full field count mismatch')
        ref=rows[ident]['files']['SOURCE-ONLY'];s=checked(home/ref['path'],ref['sha256'])
        result.append((ident,s,field,{'proof_path':p.relative_to(home).as_posix(),'proof_sha256':sha,'plan_path':plan.relative_to(home).as_posix(),'plan_sha256':proof['plan_sha256'],'finished':proof['finished'],'source':ref}))
    for relative,ids in JOBS.items():
        job=home/relative;intents=list(job.glob('*.intent.json'))
        if len(intents)>150:raise UserError('Finite actual job intent bound exceeded')
        for ident in ids:
            built=checked(job/(ident+'-DIRECT-BUILT.json'));ref=built['actual_complete_native_after'];p=home/ref['path'];proof=complete_proof(home,p,ref['sha256'])
            matches=[checked(q)for q in intents if checked(q).get('plan',{}).get('sha256')==proof['plan_sha256']]
            if len(matches)!=1:raise UserError('Exactly one actual immutable full-after intent required')
            pr=matches[0]['plan'];plan=home/pr['path'];doc=checked(plan,proof['plan_sha256']);field=flatten(doc)
            if len(field)!=proof['blocks']:raise UserError('Actual full composed field count mismatch')
            sr=rows[ident]['files']['SOURCE-ONLY'];s=checked(home/sr['path'],sr['sha256'])
            result.append((ident,s,field,{'proof_path':ref['path'],'proof_sha256':ref['sha256'],'plan_path':pr['path'],'plan_sha256':proof['plan_sha256'],'finished':proof['finished'],'source':sr}))
    return sorted(result,key=lambda r:r[3]['finished'])


def prepare(home):
    home=Path(home).resolve()
    if not home.is_relative_to(Path('D:/A World for Two/staging/world-tests').resolve()):raise UserError('Private artistic Source only')
    reserve=guard(4*MIB,32*MIB);reg=read_json(home/'dashboard/settlement/registry.json');receipt=read_json(home/'dashboard/settlement/backup-receipt.json')
    actual=actual_sources(home);current={};refs=[]
    for _,_,field,ref in actual:current.update(field);refs.append(ref)
    delta={};details=[];unknown_outer=[]
    for ident,s,field,ref in actual:
        expected=intended_entry_states(reg,s['entries'],s['origin']);changes=[];threshold=[]
        for entry in s['entries']:
            pair=intended_entry_states(reg,[entry],s['origin'])
            if any(q not in current for q in pair):raise UserError('The actual full Native field omits an intended entry pair')
            if any(current[q]!=v for q,v in pair.items()):
                if any(key(current[q])!='mcwdoors:dark_oak_cottage_door'and not key(current[q]).startswith('mcwwindows:')for q in pair):raise UserError('A door repair may not overwrite an unrelated existing block')
                for q,v in pair.items():delta[q]=v;changes.append({'position':list(q),'before':current[q],'after':v})
            outside=entry['outer_step'];x,y,z=(outside[k]+s['origin'][k]for k in range(3))
            for h in(1,2):
                q=x,y+h,z;value=current.get(q)
                if value is None:unknown_outer.append({'building':ident,'position':list(q),'reason':'Outside the actual verified field; no inferred AIR/grass clearing authority'});continue
                if key(value)in LOW_FITTINGS:
                    delta[q]='minecraft:air';threshold.append({'position':list(q),'before':value,'after':'minecraft:air'})
                elif key(value)not in('minecraft:air','minecraft:cave_air','minecraft:void_air'):
                    unknown_outer.append({'building':ident,'position':list(q),'current_verified_state':value,'reason':'Unrelated threshold state requires specific review; not cleared'})
        details.append({'building':ident,'intended_pairs':len(expected)//2,'door_half_changes':changes,'exact_low_threshold_fittings_removed':threshold,'proof':ref})
    if not delta or len(delta)>180:raise UserError('Finite reviewed actual-fourteen door/threshold repair bound')
    before={q:current[q]for q in delta};after=current|delta
    # Four-window blocks have no derived PART property. Never invent a window
    # part update or weaken any original block/orientation expectations.
    affected_windows={q:v for q,v in after.items()if key(v).startswith('mcwwindows:')and any(abs(q[0]-r[0])+abs(q[1]-r[1])+abs(q[2]-r[2])==1 for r in delta)}
    if any('part='in v for v in affected_windows.values()):raise UserError('A connected-window PART family needs its pinned full-mask derivation before emission')
    settle={q:v for q,v in delta.items()if key(v)!='minecraft:air'}|affected_windows
    out=home/'staging'/('eastern-current14-entry-repair-'+str(time.time_ns()));out.mkdir();files={}
    for name,field in [('entry-BEFORE',before),('entry-and-low-fitting-DELTA',delta),('entry-normal-settle',settle),('current14-complete-AFTER',after)]:
        doc=native_payload(reg,field,receipt['sha256'],'SOURCE ONLY paired real entry correction — '+name);doc.update(construction_forbidden=True,verification_only=True,block_entities=[],commands=[])
        p=out/(name+'.json');p.open('x',encoding='utf8').write(json.dumps(doc,separators=(',',':'))+'\n');files[name]={'path':p.relative_to(home).as_posix(),'sha256':digest(p),'bytes':p.stat().st_size}
    manifest={'format':'awft-current14-real-entry-repair-SOURCE:1','files':files,'actual_native_proofs':refs,'by_building':details,'unknown_or_unrelated_outer_threshold_cells':unknown_outer,
      'counts':{'actual_compounds':len(actual),'door_half_changes':sum(len(r['door_half_changes'])for r in details),'low_threshold_fittings':sum(len(r['exact_low_threshold_fittings_removed'])for r in details),'targets':len(delta),'unchanged_neighbor_windows_normally_settled':len(affected_windows),'connected_window_part_updates':0,'complete_after_cells':len(after)},
      'source_sha256':digest(Path(__file__)),'generator_source_sha256':digest(Path('tools/artistic_eastern_compound_sprint.py')),
      'actual_current_preimage_not_claimed':True,'new_tags':0,'existing_inventory_or_NBT_touched':0,'world_writes':0,'native_actions':0,'construction_forbidden':True,'reserve_guard':reserve,
      'required_next_gates':['Root fresh current Native unchanged before while empty and exclusive','Admit only exact sparse door/fitting delta, no inventory/tag replay','Normal neighbor settle, strict complete14 after and actual entry/use/render review','Unknown natural cover sampled and separately admitted; no guessed grass clear']}
    p=out/'manifest.json';p.open('x',encoding='utf8').write(json.dumps(manifest,indent=2)+'\n')
    if sum(q.stat().st_size for q in out.iterdir())>32*MIB:raise UserError('Finite32MiB repair Source allocation exceeded')
    return {'folder':str(out),'manifest_sha256':digest(p),'counts':manifest['counts'],'files':files,'unknown_outer':len(unknown_outer),'world_writes':0,'native_actions':0}


if __name__=='__main__':
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('--home',type=Path,required=True);v=a.parse_args();print(json.dumps(prepare(v.home),indent=2))
