"""Prepare native-sapling describe/grow inputs; never install or execute them.

One exact qualified plot per growth request. Unknown saved chunks remain unknown;
the complete feature/physics envelope, architecture and contour walks are retained.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from collections import Counter

from control_room.common import UserError,digest,read_json
from tools.artistic_bridge_refinement import encoded
from tools.artistic_south_forest import exclusions,buffered_columns,AIR,SOFT,is_tree
from tools.playtest import guard
from tools.settlement_attractions import BackupWorld,base

MIB=1024**2
MAX_OUTPUT=32*MIB
MAX_KNOWN=131072
SAPLINGS=('minecraft:birch_sapling','regions_unexplored:magnolia_sapling','regions_unexplored:white_magnolia_sapling',
          'regions_unexplored:pink_magnolia_sapling','regions_unexplored:maple_sapling','regions_unexplored:silver_birch_sapling',
          'regions_unexplored:pine_sapling','regions_unexplored:larch_sapling','regions_unexplored:golden_larch_sapling')


def bounded_json(path,cap):
    path=Path(path)
    if not path.is_file() or path.is_symlink() or not 0<path.stat().st_size<=cap:raise UserError('Bounded ordinary tree input required: '+str(path))
    return read_json(path)


def box_volume(bounds):
    if len(bounds)!=6 or any(type(v) is not int for v in bounds):raise UserError('Six literal integer envelope coordinates required')
    if any(bounds[i]>bounds[i+3] for i in range(3)):raise UserError('Inverted tree envelope')
    return (bounds[3]-bounds[0]+1)*(bounds[4]-bounds[1]+1)*(bounds[5]-bounds[2]+1)


def envelopes(root,relative):
    if len(root)!=3 or any(type(v) is not int for v in root):raise UserError('Literal world root coordinates required')
    box_volume(relative)
    write=[relative[i]+root[i%3] for i in range(6)]
    known=[write[0]-8,write[1]-2,write[2]-8,write[3]+8,write[4]+4,write[5]+8]
    if not all(write[i]<=root[i]<=write[i+3] for i in range(3)) or known[1]<-64 or known[4]>319 or box_volume(known)>MAX_KNOWN:
        raise UserError('Reviewed envelope exceeds one finite known-plot phase; do not enlarge it until it fits')
    return write,known


def protect_envelope(write,columns):
    for x in range(write[0],write[3]+1):
        for z in range(write[2],write[5]+1):
            if (x,z) in columns:raise UserError('Complete native growth envelope conflicts with a retained building/AIR/route/plaza/walk/view skirt')


def native_plan(registry,checkpoint,field,name):
    palette=sorted(set(field.values()));index={state:n for n,state in enumerate(palette)}
    return {'format':'awft-native-settlement:1','name':name,'seed':registry['seed'],'world_path':registry['world_path'],
        'backup_sha256':checkpoint['sha256'],'palette':palette,'blocks':[[*pos,index[state]] for pos,state in sorted(field.items())],
        'block_entities':[],'commands':[],'landmarks':[],'construction_forbidden':True,'verification_only':True,
        'validation':'Literal saved before-state only; never replay placement, inventories or native-generated trees'}


def collect_known(snapshot,known,write,root):
    """Every voxel is authenticated FULL data. No surface-only gap extrapolation."""
    if box_volume(known)>MAX_KNOWN:raise UserError('Finite complete native plot required')
    field={};ground_counts=Counter()
    for x in range(known[0],known[3]+1):
        for z in range(known[2],known[5]+1):
            for y in range(known[1],known[4]+1):
                pos=x,y,z;state=snapshot.state(pos)  # Missing/non-FULL chunk errors propagate.
                if state is None:raise UserError('Unknown native plot cell is not air')
                field[pos]=state
    for x in range(write[0],write[3]+1):
        for z in range(write[2],write[5]+1):
            found=None
            for y in range(known[4],known[1]-1,-1):
                state=field[x,y,z];key=base(state)
                if key in AIR|SOFT:continue
                if is_tree(key):raise UserError('Retain existing natural canopy/trunk; choose a different native-growth plot')
                if key=='minecraft:water' or 'waterlogged=true' in state:raise UserError('Known dry growth envelope must not enter the channel or wet shore')
                found=y;ground_counts[key]+=1;break
            if found is None:raise UserError('No actual saved ground in the bounded growth column')
            if found>root[1]+2:raise UserError('Plot rises into a retained hill/obstruction; do not flatten it for a tree')
    if any(write[0]<=x<=write[3] and write[1]<=y<=write[4] and write[2]<=z<=write[5] for x,y,z in snapshot.protected):
        raise UserError('Preserve native block entity in a growth envelope')
    return field,dict(ground_counts)


def evidence_ref(home,path):
    home,path=Path(home).resolve(),Path(path).resolve()
    if not path.is_relative_to(home) or not path.is_file() or path.is_symlink():raise UserError('Owned ordinary reference required')
    return {'path':path.relative_to(home).as_posix(),'bytes':path.stat().st_size,'sha256':digest(path)}


def classes(native_classes):
    root=Path(native_classes)
    values={}
    for key,name in (('native_class_sha256','worldfortwo/bridge/NativeTreeGrowthSupport.class'),
                     ('native_scope_sha256','worldfortwo/bridge/TreeGrowthScope.class'),
                     ('native_guard_sha256','worldfortwo/bridge/mixin/NativeTreeGrowthGuardMixin.class')):
        path=root/name
        if not path.is_file() or not 0<path.stat().st_size<=256*1024:raise UserError('Actual private compiled native tree/guard classes required')
        values[key]=digest(path)
    return values


def protection(registry,index_path,composition_path,plaza_path):
    index=bounded_json(index_path,2*MIB);composition=bounded_json(composition_path,4*MIB);plaza=bounded_json(plaza_path,8*MIB)
    if any(str(plaza.get(key))!=str(registry[key]) for key in ('seed','world_path')):raise UserError('Latest final plaza mask belongs to another world')
    columns,custody=exclusions([(row['name'],row['path'],row['sha256']) for row in index['plans']],registry)
    plaza_columns={(row[0],row[2]) for row in plaza['blocks']};columns.update(buffered_columns(plaza_columns,5))
    walks=composition.get('walk_columns_with_five_metre_growth_skirt')
    if not isinstance(walks,list) or not walks:raise UserError('Retained contour-walk body/growth skirts required')
    columns.update(tuple(row) for row in walks)
    return {'format':'awft-native-tree-protection:1','seed':registry['seed'],'world_path':registry['world_path'],
        'minimum_buffer_blocks':5,'includes_latest_plaza_routes_and_walks':True,'columns':[list(p) for p in sorted(columns)],
        'source_index_sha256':digest(Path(index_path)),'source_walks_sha256':digest(Path(composition_path)),
        'latest_plaza_mask_sha256':digest(Path(plaza_path)),'custody':custody,
        'scope':'Every authored target including AIR, full latest plaza/plumbing/view mask and body-clear contour walks; no rectangle is planting authority'}


def _prepare(home,output,native_classes,candidate,bridge,mode='describe',saplings=SAPLINGS,root=None,qualification=None,
             index_path=None,composition_path=None,plaza_path=None,construction_ready=None):
    home,output=Path(home).resolve(),Path(output).resolve()
    if output.exists() or not output.is_relative_to(home/'staging'):raise UserError('A new private tree-preparation folder is required')
    reserve=guard(2*MIB,MAX_OUTPUT);registry=bounded_json(home/'dashboard/settlement/registry.json',8*MIB)
    checkpoint=bounded_json(home/'dashboard/settlement/backup-receipt.json',4096)
    if checkpoint.get('verified') is not True:raise UserError('Verified current stopped checkpoint required')
    selected=list(saplings)
    if not selected or len(selected)>9 or len(set(selected))!=len(selected) or any(v not in SAPLINGS or v not in registry['blocks'] for v in selected):raise UserError('Exact finite registered native sapling palette required')
    if mode not in ('describe','review','grow'):raise UserError('Only native describe, review or grow supported')
    plan={'format':'awft-native-tree-plan:1','seed':registry['seed'],'world_path':registry['world_path'],'saplings':selected}
    docs={};proofs={}
    if mode in ('review','grow'):
        if len(selected)!=1 or root is None or not all((qualification,index_path,composition_path,plaza_path)) or (mode=='grow' and not construction_ready):
            raise UserError('One qualified sapling/root, exact exclusions/walks/latest plaza and completed construction review required')
        q=bounded_json(qualification,128*1024)
        if q.get('all_reachable_features_reviewed') is not True or any(not re.fullmatch('[a-f0-9]{64}',str(q.get(key,''))) for key in ('derivation_sha256','native_descriptor_sha256')):
            raise UserError('Actual runtime descriptor plus independent complete native primary/rare-envelope derivation required')
        if q.get('sapling')!=selected[0]:raise UserError('Qualification is for another native sapling')
        write,known=envelopes(root,q['relative_write_bounds']);mask=protection(registry,index_path,composition_path,plaza_path)
        protect_envelope(write,{tuple(row) for row in mask['columns']})
        if mode=='grow':
            ready=bounded_json(construction_ready,128*1024)
            if any(ready.get(key) is not True for key in ('construction_complete','functional_commissioning_complete','visual_corrections_reviewed')):
                raise UserError('Native forest growth follows completed construction/function/art')
            if ready.get('checkpoint_sha256')!=checkpoint['sha256']:raise UserError('Construction review is stale')
        snapshot=BackupWorld(home,checkpoint,registry)
        try:
            field,soil=collect_known(snapshot,known,write,root);sources=snapshot.sources
        finally:snapshot.close()
        plan.update(root=list(root),write_bounds=write,known_bounds=known)
        docs['tree-before-VERIFY-ONLY.json']=encoded(native_plan(registry,checkpoint,field,'VERIFY ONLY - exact known native growth plot and read/physics perimeter'))
        docs['tree-protection.json']=encoded(mask);docs['native-qualification.json']=encoded(q)
        proofs['saved_source_regions']=sources;proofs['observed_ground_id_counts']=soil
        proofs['finite_growth_attempt_limit']=12;proofs['manual_tree_blocks_generated']=0
    docs['tree-plan.json']=encoded(plan)
    def newref(name):return {'path':(output/name).relative_to(home).as_posix(),'bytes':len(docs[name]),'sha256':hashlib.sha256(docs[name]).hexdigest()}
    request={'format':'awft-native-trees:1','allowed_operation':mode,'candidate_version':candidate,'bridge_version':bridge,
        **classes(native_classes),'checkpoint_sha256':checkpoint['sha256'],'current_backup':evidence_ref(home,home/'dashboard/settlement/backup-receipt.json'),
        'pack_sha256':bounded_json(home/'packwiz/active.json',65536)['pack_sha256'],'plan':newref('tree-plan.json')}
    if mode=='grow':
        plan_sha=hashlib.sha256(docs['tree-plan.json']).hexdigest()
        if ready.get('tree_plan_sha256')!=plan_sha:raise UserError('Construction review must bind the exact qualified tree-plan SHA, not a generic approval')
        request.update(before=newref('tree-before-VERIFY-ONLY.json'),protection=newref('tree-protection.json'),qualification=newref('native-qualification.json'),construction_ready=evidence_ref(home,construction_ready))
    raw=encoded(request);sha=hashlib.sha256(raw).hexdigest();bundle='trees-'+sha[:16]
    if mode!='review':docs[bundle+'/request.json']=raw
    manifest={'format':'awft-native-tree-preparation:1','source_sha256':digest(Path(__file__)),'checkpoint_id':checkpoint['id'],'checkpoint_sha256':checkpoint['sha256'],
        'allowed_operation':mode,'bundle':bundle if mode!='review' else None,'request_sha256':sha if mode!='review' else None,'native_actions':False,'world_or_sapling_writes':False,'installed':False,'reserve_guard':reserve,
        'qualification_is_not_visual_acceptance':True,'proofs':proofs,
        'tree_plan_sha256_for_concrete_review':hashlib.sha256(docs['tree-plan.json']).hexdigest(),
        'command_only_after_parent_review_and_explicit_install':f'awfttrees {mode} {bundle} {sha}' if mode!='review' else None,
        'files':{name:{'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()} for name,data in docs.items()}}
    docs['manifest.json']=encoded(manifest)
    if sum(map(len,docs.values()))>MAX_OUTPUT:raise UserError('Native plot evidence exceeds finite output budget')
    output.mkdir(parents=True,exist_ok=False)
    for name,data in docs.items():path=output/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
    return {'output':str(output),'bundle':bundle if mode!='review' else None,'request_sha256':sha if mode!='review' else None,'mode':mode,'native_actions':False}


def prepare(**arguments):
    try:return _prepare(**arguments)
    except Exception as error:
        home,target=Path(arguments['home']).resolve(),Path(arguments['output']).resolve()
        if target.is_relative_to(home/'staging') and not target.exists():
            reserve=guard(0,65536);target.mkdir(parents=True,exist_ok=False)
            (target/'failed-receipt.json').write_bytes(encoded({'status':'FAILED_PREPARATION','error':str(error),'source_sha256':digest(Path(__file__)),
                'native_actions':False,'world_or_sapling_writes':False,'reserve_guard':reserve}))
        raise


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('home','output','native-classes'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--candidate',required=True);p.add_argument('--bridge',required=True);p.add_argument('--mode',choices=('describe','review','grow'),default='describe')
    p.add_argument('--saplings',nargs='+',default=SAPLINGS);p.add_argument('--root',type=int,nargs=3)
    for name in ('qualification','index-path','composition-path','plaza-path','construction-ready'):p.add_argument('--'+name,type=Path)
    print(json.dumps(prepare(**vars(p.parse_args())),indent=2))
