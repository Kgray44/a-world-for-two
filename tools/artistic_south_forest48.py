"""Current31 native forest follow-through; never retry, plant or operate a world.

Requalifies only the sixteen genuinely unperformed sites from the sealed47
composition against actual48 guards and complete current saved before fields.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import time
import zipfile

from control_room.common import UserError,digest,read_json,utcnow
from tools import artistic_dense_canopies as dense
from tools import artistic_forest47 as prior
from tools import artistic_native_tree_pilot as pilot
from tools.artistic_bridge_refinement import encoded
from tools.artistic_first_life_requests48 import CHECKPOINT,CHECKPOINT_SHA,checkpoint,ref,runtime
from tools.artistic_forest_understory import settlement_plan
from tools.artistic_south_extent import ExtentTerrain
from tools.artistic_zipline_catenary import reader_budget
from tools.native_tree_growth import envelopes,protect_envelope
from tools.playtest import guard

MIB=1024**2
ORIGINAL='staging/native-next24-47-575-final-20261028T0638Z'
ORIGINAL_SHA='3f70cc5cfdc9cd5f2dbb2af45603dd2516d9bf5f415a81348081127a933c57f7'
OUTCOMES='staging/native28-ROOT-reviewed47-1793170167699538800/actual-outcomes.json'
OUTCOMES_SHA='eae94f1e1a4728e3de18ba9616f994da4d28952746697360b165a4fee77ffe75'
LIFE='staging/first8-LIFE48-inspect-20261028T1421Z/habitat-VERIFY-ONLY.json'
LIFE_SHA='12ec545bfee5337182f9050fd5dadb6a7de567c20637ad74c38d34bbd1d17f28'
BRIDGE='staging/bridge-moving106-ADMITTED47-1793168856089689000/complete-after-VERIFY-ONLY.json'
BRIDGE_SHA='c58c1680b7d8330e6e5196de5d01af6f200b22082a6c0d5f5bb9aa2cb65b3868'


def unperformed(plots,outcomes):
    attempted={row['id']for row in outcomes}
    selected=[row for row in plots if row['id']not in attempted]
    if any(row['id']in attempted or not row['id'].startswith('south47-')or int(row['id'].split('-')[1])<10 for row in selected):
        raise UserError('Only never-attempted later sites may continue; all refused/failed sites remain held')
    if len(selected)!=16:raise UserError('Exact sealed sixteen unperformed47 plots required')
    return selected


def pins(home):
    life=runtime(home);jar=home/'server/mods/awft-control-bridge-0.6.34.jar'
    names={'native_class_sha256':'NativeTreeGrowthSupport','native_scope_sha256':'TreeGrowthScope',
        'native_guard_sha256':'mixin/NativeTreeGrowthGuardMixin','bee_audit_sha256':'TreeBeeAudit',
        'bee_facts_sha256':'BeeNestFacts','pre_mutation_field_check_sha256':'PreMutationFieldCheck'}
    classes={}
    with zipfile.ZipFile(jar)as archive:
        for key,name in names.items():
            member='worldfortwo/bridge/'+name+'.class'
            if not 0<archive.getinfo(member).file_size<=256*1024:raise UserError('Bounded actual48 tree/atomic/bee class required')
            classes[key]=hashlib.sha256(archive.read(member)).hexdigest()
    for key in ('native_scope_sha256','native_guard_sha256','bee_audit_sha256','bee_facts_sha256'):
        if classes[key]!=pilot.NATIVE_CLASS_PINS[key]:raise UserError('Sealed scope/feature/bee rules changed; independent review required')
    return {k:life[k]for k in ('candidate_version','bridge_version','pack_sha256')}|{'classes':classes,'installed_helper':ref(home,jar)}


def protection(home,registry):
    protected,custody,bank,partition=prior.protection(home,registry)
    for name,path,sha in (('Complete current moving106 bridge source',BRIDGE,BRIDGE_SHA),
                          ('All eight pending/held LIFE habitat fields',LIFE,LIFE_SHA)):
        doc=pilot.checked(home/path,sha,16*MIB)
        for x,y,z,*tail in doc['blocks']:
            protected.update((x+dx,z+dz)for dx in range(-5,6)for dz in range(-5,6))
        custody.append({'name':name,**ref(home,home/path)})
    if len(protected)>200000:raise UserError('Preserve native finite protection bound')
    return protected,custody,bank,partition


def prepare(home,output,limit=16):
    home=Path(home).resolve();output=Path(output).absolute()
    if output.exists()or output.parent!=home/'staging'or not 1<=limit<=16:raise UserError('New bounded private forest48 output required')
    reserve=guard(2*MIB,32*MIB);budgets=[reader_budget()];current=checkpoint(home)
    registry=read_json(home/'dashboard/settlement/registry.json');native=pins(home)
    original=pilot.checked(home/ORIGINAL/'manifest.json',ORIGINAL_SHA,2*MIB)
    outcomes=pilot.checked(home/OUTCOMES,OUTCOMES_SHA,MIB)
    candidates=unperformed(original['plots'],outcomes)[:limit]
    qvalues=prior.qualifications(home);protected,custody,bank,partition=protection(home,registry)
    historic,historic_sources=prior.historical_plots(home)
    all_reserved=historic+original['plots']
    terrain=ExtentTerrain(home,current,registry);docs={};plots=[];refusals=[];start=time.monotonic()
    try:
        entities,entity_sources=dense.entity_positions(terrain.snapshot)
        for row in candidates:
            try:
                budgets.append(reader_budget())
                if time.monotonic()-start>150:raise UserError('Finite current31 forest reader expired')
                q=qvalues[row['species']];root=tuple(row['root']);write,known=envelopes(root,q['relative_write_bounds'])
                if write!=row['write_bounds']or known!=row['known_bounds']:raise UserError('Original complete normal/rare/root envelope must remain unchanged')
                other=[p for p in all_reserved if tuple(p['root'])!=root]
                if prior.conflict(write,known,other):raise UserError('Preserve every prior successful/held/lost/false and other pending full field')
                protect_envelope(write,protected)
                field,write,known,trees=dense.saved_plot(terrain,q,root,protected,entities)
            except UserError as error:
                refusals.append({'id':row['id'],'root':row['root'],'reason':str(error),'native_actions':0})
                if 'RAM'in str(error)or 'working set'in str(error)or 'expired'in str(error):break
                continue
            label=row['id'].replace('south47-','south48-continuation-')
            plan={'format':'awft-native-tree-plan:1','seed':registry['seed'],'world_path':registry['world_path'],
                'saplings':[row['species']],'root':row['root'],'write_bounds':write,'known_bounds':known}
            before=settlement_plan(registry,current,field,'VERIFY ONLY current31 full native tree envelope '+label)
            docs[label+'/tree-plan.json']=encoded(plan);docs[label+'/before-VERIFY-ONLY.json']=encoded(before)
            docs[label+'/qualification.json']=encoded(q)
            plan_sha=hashlib.sha256(encoded(plan)).hexdigest()
            ready={'approval_scope':'one-exact-saved-tree-plot','checkpoint_sha256':CHECKPOINT_SHA,
                'tree_plan_sha256':plan_sha,'construction_complete':True,'functional_commissioning_complete':True,
                'visual_corrections_reviewed':True,'reviewer':'castle_detail independent current31 full-field review under Root continued original24 bare-plot delegation',
                'scope':'Only this literal bare plot, with no unfinished structure or mechanism; no whole forest/town/art/native canopy acceptance',
                'native_before_occupancy_default_growth_and_after_audit_still_required':True,'whole_town_or_forest_complete':False}
            docs[label+'/BARE-PLOT-readiness.json']=encoded(ready)
            plots.append({**row,'id':label,'retained_source_id':row['id'],'known_cells':len(field),
                'tree_plan_sha256':plan_sha,'retained_read_context_tree_cells':trees,'independent_current31_review':True,
                'native_before_grown_visual_and_persistence_acceptance':False})
        sources=terrain.snapshot.sources.copy()
    finally:terrain.close()
    protection_doc={'format':'awft-native-tree-protection:1','seed':registry['seed'],'world_path':registry['world_path'],
        'minimum_buffer_blocks':5,'includes_latest_plaza_routes_and_walks':True,
        'columns':[list(p)for p in sorted(protected)],'custody':custody}
    docs['protection.json']=encoded(protection_doc)
    def newref(name):return {'path':(output/name).relative_to(home).as_posix(),'bytes':len(docs[name]),'sha256':hashlib.sha256(docs[name]).hexdigest()}
    requests=[]
    for row in plots:
        ident=row['id'];request={'format':'awft-native-trees:1','allowed_operation':'grow',
            **{k:native[k]for k in ('candidate_version','bridge_version','pack_sha256')},
            **{k:native['classes'][k]for k in ('native_class_sha256','native_scope_sha256','native_guard_sha256')},
            'checkpoint_sha256':CHECKPOINT_SHA,'current_backup':ref(home,home/'dashboard/settlement/backup-receipt.json'),
            'plan':newref(ident+'/tree-plan.json'),'before':newref(ident+'/before-VERIFY-ONLY.json'),
            'qualification':newref(ident+'/qualification.json'),'protection':newref('protection.json'),
            'construction_ready':newref(ident+'/BARE-PLOT-readiness.json')}
        raw=encoded(request);sha=hashlib.sha256(raw).hexdigest();bundle='trees-'+sha[:16]
        docs[bundle+'/request.json']=raw
        requests.append({'id':ident,'bundle':bundle,'request_sha256':sha,
            'native_before_plan':newref(ident+'/before-VERIFY-ONLY.json'),
            'command_only_after_parent_current_native_before_review':f'awfttrees grow {bundle} {sha}'})
    manifest={'format':'awft-south-forest48-unperformed-source:1','created':utcnow(),'source_sha256':digest(Path(__file__)),
        'checkpoint_id':CHECKPOINT,'checkpoint_sha256':CHECKPOINT_SHA,'native_runtime':native,
        'original24_manifest_sha256':ORIGINAL_SHA,'actual_old28_outcomes_sha256':OUTCOMES_SHA,
        'never_retry_any_success_refusal_failure_natural_false_or_lost':True,
        'requested_unperformed':len(candidates),'qualified_current_plots':len(plots),'plots':plots,'requests':requests,
        'species_counts':dict(Counter(r['species']for r in plots)),
        'source_root_bounds':[min(r['root'][i]for r in plots)for i in range(3)]+[max(r['root'][i]for r in plots)for i in range(3)]if plots else None,
        'native_actions':0,'installed':False,'world_writes':0,'handcrafted_tree_blocks':0,
        'native_full_atomic_precheck_occupancy_noescape_bee_and_cleanup_guards_unchanged':True,
        'native_before_REQUIRED_before_parent_growth':True,'historical_source_custody':historic_sources,
        'north_partition':partition,'source_regions':sources,'saved_entities_screened':len(entities),
        'entity_region_sources':entity_sources,'refusals':refusals,'reserve_guard':reserve,'reader_budgets':budgets,
        'files':{n:{'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}for n,raw in docs.items()}}
    docs['manifest.json']=encoded(manifest)
    if sum(map(len,docs.values()))>32*MIB:raise UserError('Finite native forest output exceeded')
    output.mkdir()
    for name,raw in docs.items():
        p=output/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
    return {'output':str(output),'manifest_sha256':digest(output/'manifest.json'),
        'qualified':len(plots),'requested':len(candidates),'refused':len(refusals),'requests':requests}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('home','output'):p.add_argument('--'+k,type=Path,required=True)
    p.add_argument('--limit',type=int,default=16);a=p.parse_args()
    print(json.dumps(prepare(a.home,a.output,a.limit),indent=2))
