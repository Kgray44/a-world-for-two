"""Large rooted southern planting sectors from exact current31 saved terrain.

No placement, native tree geometry, entity seeding, clearing or inventory writes.
Each sector supplies literal before/support, addition, retained support and after
plans. Parent native preflight/admission, normal joins and views remain required.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import time

from control_room.common import UserError,digest,read_json,utcnow
from tools import artistic_forest47 as prior
from tools import artistic_forest_understory as low
from tools import artistic_native_tree_pilot as pilot
from tools.artistic_bridge_refinement import encoded
from tools.artistic_first_life_requests48 import CHECKPOINT,CHECKPOINT_SHA,checkpoint,ref,complete_receipt,runtime
from tools.artistic_materials import require_outdoor_rule
from tools.artistic_south_extent import ExtentTerrain
from tools.artistic_south_forest import AIR,SOFT,buffered_columns
from tools.artistic_south_forest48 import ORIGINAL,ORIGINAL_SHA,protection
from tools.artistic_spawn_plaza import state
from tools.artistic_zipline_catenary import reader_budget
from tools.artistic_quay_prototype import fresh_proof
from tools.playtest import guard
from tools.settlement_attractions import base

MIB=1024**2
EXISTING12='staging/south-understory-native-contract0d7-1793156891473004400/prototype12-FULL-VERIFY-ONLY.json'
EXISTING12_SHA='faef97c7b71b49ff4f74ea1960c6105e3de9dd004dc3e94a2dac601e0c1e31d3'
EXISTING12_PROOF='dashboard/settlement/settlement-result-5bd9f7d9-ae54-4b0a-bcc4-bb795784bfc5.json'
MAX_SECONDS=150
PALETTES={
 'river_fringe':('minecraft:fern','regions_unexplored:aster','minecraft:blue_orchid'),
 'sheltered_footwoods':('minecraft:fern','regions_unexplored:felicia_daisy','minecraft:lily_of_the_valley'),
 'middle_mixed_woods':('minecraft:fern','minecraft:oxeye_daisy','regions_unexplored:aster'),
 'upper_ridge_woods':('regions_unexplored:blue_lupine','minecraft:cornflower','minecraft:fern'),
}


def sector(pos):
    # 480m cells leave margin for one-block lateral vine support witnesses.
    # Both axes are partitioned; the entire bank is taller than512m in Z.
    return f'sector-x{pos[0]//480}-z{pos[2]//480}'


def forbid_tree_fields(protected,plots):
    for row in plots:
        b=row['known_bounds']
        protected.update((x,z)for x in range(b[0]-5,b[3]+6)for z in range(b[2]-5,b[5]+6))


def planting_pocket(terrain,registry,center,zone,ordinal,protected,forbidden,occupied):
    blocks,roots,before,retained=low.pocket(terrain,registry,center,protected,forbidden,occupied)
    palette=PALETTES[zone]
    for number,p in enumerate(sorted(blocks)):
        # Coherent small species drifts; no single global repeating stamp.
        plant=palette[(number//5+ordinal//7)%len(palette)]
        blocks[p]=state(registry,plant)
        if plant=='minecraft:fern'and number%11==ordinal%11:
            above=(p[0],p[1]+1,p[2]);head=(p[0],p[1]+2,p[2])
            if (above not in occupied and above not in forbidden and head not in forbidden
                    and above not in terrain.entities and head not in terrain.entities
                    and base(terrain.state(*above))in AIR and base(terrain.state(*head))in AIR):
                before[above]=terrain.state(*above);before[head]=terrain.state(*head)
                blocks[p]=state(registry,'minecraft:large_fern',half='lower')
                blocks[above]=state(registry,'minecraft:large_fern',half='upper')
    return blocks,roots,before,retained


def attached_vines(terrain,registry,scene,protected,forbidden,occupied,limit=3):
    blocks,before={},{};cx,cz=scene
    for dx,dz in ((-3,0),(0,3),(3,1),(-2,-3),(2,2),(0,-4)):
        x,z=cx+dx,cz+dz
        if (x,z)in protected:continue
        col=terrain.column(x,z)
        if col.get('kind')!='dry':continue
        for dy in (2,3,4):
            p=(x,col['surface_y']+dy,z)
            if p in occupied or p in forbidden or p in terrain.entities or base(terrain.state(*p))not in AIR:continue
            for facing,(sx,sz)in (('north',(0,-1)),('south',(0,1)),('east',(1,0)),('west',(-1,0))):
                support=(x+sx,p[1],z+sz);value=terrain.state(*support)
                if value is None:raise UserError('Unknown vine support is not a valid attachment')
                key=base(value)
                if not key.endswith(('_log','_wood','_stem','_hyphae'))or support in terrain.entities:continue
                before[p]=terrain.state(*p);before[support]=value
                blocks[p]=state(registry,'minecraft:vine',**{d:d==facing for d in ('north','south','east','west','up')})
                break
            if len(blocks)>=limit:return blocks,before
    return blocks,before


def saved_walks(terrain,bank):
    """Recheck existing ordinary routes; source labels do not prove a loop."""
    facts=[];reserved=set();field={}
    for row in bank['walks']:
        nodes=row.get('nodes_xz',[]);witnesses={};refusal=None
        for a,b in zip(nodes,nodes[1:]):
            steps=max(abs(a[0]-b[0]),abs(a[1]-b[1]),1)
            across=(0,1)if a[0]!=b[0]else(1,0);heights=[]
            for n in range(steps+1):
                x=a[0]+round((b[0]-a[0])*n/steps);z=a[1]+round((b[1]-a[1])*n/steps)
                local=[]
                for side in (-1,0,1):
                    xx,zz=x+across[0]*side,z+across[1]*side;col=terrain.column(xx,zz)
                    if col.get('kind')!='dry':refusal='Retain actual non-dry or occupied route ground';break
                    g=col['surface_y'];body=[terrain.state(xx,g+dy,zz)for dy in (1,2,3)]
                    if any(s is None or base(s)not in AIR|SOFT for s in body):refusal='Retain actual route obstruction';break
                    p=(xx,g,zz);witnesses[p]=col['state'];local.append(g)
                    for dy,s in enumerate(body,1):witnesses[xx,g+dy,zz]=s
                if refusal:break
                if max(local)-min(local)>1:refusal='Actual three-wide route cross-slope exceeds one block';break
                heights.append(local[1])
            if refusal or any(abs(a-b)>1 for a,b in zip(heights,heights[1:])):
                refusal=refusal or'Actual route step exceeds one block';break
        if not refusal and nodes:
            field.update(witnesses);reserved.update((p[0],p[2])for p in witnesses)
        facts.append({'id':row['id'],'nodes_xz':nodes,'known_support_body_cells':len(witnesses),
            'saved_three_wide_current31_pass':not refusal and bool(nodes),'reason':refusal,
            'closed_walking_loop_proved':bool(nodes)and nodes[0]==nodes[-1],
            'paving_or_clearing':False,'native_actual_walking_and_art_pending':True})
    return facts,reserved,field


def prepare(home,output,pockets=224):
    home=Path(home).resolve();output=Path(output).absolute()
    if output.exists()or output.parent!=home/'staging'or not 1<=pockets<=320:raise UserError('Bounded new private botanical output required')
    reserve=guard(2*MIB,16*MIB);budgets=[reader_budget()];current=checkpoint(home)
    registry=read_json(home/'dashboard/settlement/registry.json')
    protected,custody,bank,partition=protection(home,registry)
    original=pilot.checked(home/ORIGINAL/'manifest.json',ORIGINAL_SHA,2*MIB)
    old,old_sources=prior.historical_plots(home);forbid_tree_fields(protected,old+original['plots'])
    twelve=pilot.checked(home/EXISTING12,EXISTING12_SHA,MIB)
    proof,proof_ref=complete_receipt(home,home/EXISTING12_PROOF)
    if proof.get('plan_sha256')!=EXISTING12_SHA or proof.get('operation')!='verify'or proof.get('blocks')!=12 or proof.get('failures')!=0:
        raise UserError('The twelve previously placed flora need their genuine native physical proof')
    existing={tuple(r[:3]):twelve['palette'][r[3]]for r in twelve['blocks']}
    protected.update(buffered_columns({(p[0],p[2])for p in existing},2))
    choices=[]
    for zone,rows in bank['composition_zones'].items():
        if zone not in PALETTES:continue
        for x,y,z in rows:
            if (x,z)not in protected:choices.append((x,z,zone))
    # Spread drifts throughout all connected shore/cliff-foot zones without
    # imposing straight rows. Two pockets per24m tile remain separated.
    choices.sort(key=lambda r:(((r[0]//24)*13+(r[1]//24)*7)%29,r[1],r[0]))
    terrain=ExtentTerrain(home,current,registry);blocks={};roots={};before={};scenes=[];refusals=[];tiles=Counter();started=time.monotonic()
    try:
        for p,wanted in existing.items():
            if terrain.state(*p)!=wanted:raise UserError('Preserve the actual previously placed flora; source changed')
        walk_facts,walk_columns,walk_field=saved_walks(terrain,bank)
        protected.update(buffered_columns(walk_columns,3))
        for ordinal,(x,z,zone)in enumerate(choices):
            if len(scenes)>=pockets:break
            if time.monotonic()-started>MAX_SECONDS:
                refusals.append({'status':'Finite saved reader deadline reached; remaining pockets not qualified'});break
            tile=(x//24,z//24)
            if tiles[tile]>=2:continue
            if any(math.dist((x,z),r['center_xz'])<9 for r in scenes):continue
            if len(scenes)%16==0:
                try:budgets.append(reader_budget())
                except UserError as error:refusals.append({'status':'RESOURCE_DEFERRED','reason':str(error)});break
            try:
                extra,soil,prior_field,retained=planting_pocket(terrain,registry,(x,z),zone,ordinal,protected,set(),blocks)
                vines,vine_before=attached_vines(terrain,registry,(x,z),protected,set(),blocks|extra)
                if (before.keys()|prior_field.keys())&terrain.entities:raise UserError('Preserve every existing BE/support identity')
            except UserError as error:refusals.append({'center_xz':[x,z],'reason':str(error)});continue
            blocks.update(extra);blocks.update(vines);roots.update(soil);before.update(prior_field);before.update(vine_before)
            tiles[tile]+=1
            scenes.append({'center_xz':[x,z],'zone':zone,'rooted_plant_states':len(extra),
                'supported_vine_states':len(vines),'retained_existing_context':retained})
        sources=terrain.snapshot.sources.copy()
    finally:terrain.close()
    if not blocks:raise UserError('No literal rooted botanical sector qualified; no substitute field')
    require_outdoor_rule(blocks,'Current31 low planted southern drifts and supported native vines')
    docs={};parts=[]
    for label in sorted({sector(p)for p in blocks}):
        added={p:v for p,v in blocks.items()if sector(p)==label}
        if not added:continue
        # Vine supports may be in a neighboring column, so preserve their exact
        # individual witnesses in both support-only plans when necessary.
        xz={(p[0],p[2])for p in added}
        sides={'north':(0,-1),'south':(0,1),'east':(1,0),'west':(-1,0)}
        supports=set()
        for q,value in added.items():
            if base(value)!='minecraft:vine':continue
            for side,(dx,dz)in sides.items():
                if side+'=true'in value:supports.add((q[0]+dx,q[1],q[2]+dz))
        context={p:v for p,v in before.items()if (p[0],p[2])in xz or p in supports}
        soil={p:v for p,v in roots.items()if (p[0],p[2])in xz}
        full=context|added
        names={}
        for role,values in (('BEFORE',context),('ADDITION',added),('AFTER',full),('RETAINED-SOIL',soil)):
            if not values:continue
            name=label+'-'+role+('-PROPOSAL.json'if role=='ADDITION'else'-VERIFY-ONLY.json')
            docs[name]=encoded(low.settlement_plan(registry,current,values,'South48 '+label+' '+role,role!='ADDITION'))
            names[role]=name
        parts.append({'sector':label,'plant_states':len(added),'before_cells':len(context),'after_cells':len(full),
            'native_files':names,'native_before_and_soil_then_parent_admission_REQUIRED':True})
    # Full route observations are references, never an assumed new path/loop.
    if walk_field:
        for label in sorted({sector(p)for p in walk_field}):
            f={p:v for p,v in walk_field.items()if sector(p)==label}
            if f:docs[label+'-RETAINED-WALK-BODY-VERIFY-ONLY.json']=encoded(low.settlement_plan(registry,current,f,'Retained natural walk support/body '+label))
    docs['composition-REVIEW-ONLY.json']=encoded({'format':'awft-south48-rooted-understory:1',
        'checkpoint_sha256':CHECKPOINT_SHA,'scenes':scenes,'material_counts':dict(Counter(base(v)for v in blocks.values())),
        'scene_counts_by_ecology':dict(Counter(r['zone']for r in scenes)),'routes':walk_facts,
        'future_current16_tree_fields_and_all_held_fields_preserved':True,'all_pending_LIFE_fields_preserved':True,
        'old12flora_preserved':proof_ref,'no_canopy_boxes_or_native_growth_or_animal_seeding':True,
        'world_writes':0,'native_artistic_acceptance':False})
    manifest={'format':'awft-south48-botanical-sectors-source:1','created':utcnow(),'source_sha256':digest(Path(__file__)),
        'checkpoint_id':CHECKPOINT,'checkpoint_sha256':CHECKPOINT_SHA,'requested_pockets':pockets,'qualified_pockets':len(scenes),
        'additional_plant_states':len(blocks),'supported_vine_states':sum(base(v)=='minecraft:vine'for v in blocks.values()),
        'ecology_counts':dict(Counter(r['zone']for r in scenes)),'parts':parts,
        'source_plant_bounds':[min(p[i]for p in blocks)for i in range(3)]+[max(p[i]for p in blocks)for i in range(3)],
        'actual_current_new_plant_states_placed':0,'retained_actual_flora':12,'construction_forbidden':True,
        'native_actions':0,'world_writes':0,'reserve_guard':reserve,'reader_budgets':budgets,
        'source_regions':sources,'north_partition':partition,'old_tree_source_custody':old_sources,
        'source_protection_custody':custody,'refusals':refusals,
        'files':{n:{'bytes':len(v),'sha256':hashlib.sha256(v).hexdigest()}for n,v in docs.items()}}
    docs['manifest.json']=encoded(manifest)
    if sum(map(len,docs.values()))>16*MIB:raise UserError('Finite botanical sector allocation exceeded')
    output.mkdir()
    for name,raw in docs.items():(output/name).write_bytes(raw)
    return {'output':str(output),'manifest_sha256':digest(output/'manifest.json'),
        'pockets':len(scenes),'additional_plant_states':len(blocks),'parts':parts,'native_actions':0}


def admit(home,prepared,prepared_sha,label,native_before,native_soil,output):
    """An exact small placement is reviewable only after real fresh proof."""
    home=Path(home).resolve();prepared=Path(prepared).resolve();output=Path(output).absolute()
    reserve=guard(MIB,4*MIB);checkpoint(home);pins=runtime(home)
    if output.exists()or output.parent!=home/'staging'or prepared.parent!=home/'staging':raise UserError('New owned botanical admission folder required')
    manifest=pilot.checked(prepared/'manifest.json',prepared_sha,4*MIB)
    if manifest.get('format')!='awft-south48-botanical-sectors-source:1'or manifest.get('checkpoint_sha256')!=CHECKPOINT_SHA:
        raise UserError('Exact current31 botanical sector source required')
    matches=[p for p in manifest['parts']if p['sector']==label]
    if len(matches)!=1:raise UserError('One exact qualified sector required')
    part=matches[0];documents={}
    for role,name in part['native_files'].items():
        info=manifest['files'][name];path=prepared/name
        if path.stat().st_size!=info['bytes']or digest(path)!=info['sha256']:raise UserError('Preserve frozen botanical sector geometry')
        documents[role]=read_json(path)
    proofs=[]
    for role,path in (('BEFORE',native_before),('RETAINED-SOIL',native_soil)):
        path=Path(path).absolute()
        if path.parent!=home/'dashboard/settlement':raise UserError('Actual owned native settlement terminal required')
        doc=documents[role];name=part['native_files'][role]
        proof,marker=fresh_proof(path,manifest['files'][name]['sha256'],len(doc['blocks']))
        proofs.append({'role':role,**ref(home,path),'finished':proof['finished']})
    added=documents['ADDITION']
    if added.get('block_entities')or added.get('commands'):raise UserError('No block entities, inventory or commands in this planting admission')
    added.pop('construction_forbidden',None);added['verification_only']=False
    added['admission']={'mode':'PLACE-ONCE after genuine exact target/support and retained-soil proofs',
        'source_manifest_sha256':prepared_sha,'source_sector':label,'actual_before_proofs':proofs,
        'required_after':'Normal native shape/neighbor settlement, strict complete after and retained-soil verification, real woodland views'}
    docs={'plants-PLACE-ONCE.json':encoded(added),'plants-NORMAL-SETTLE-ONLY.json':encoded(added),
          'complete-after-VERIFY-ONLY.json':encoded(documents['AFTER'])}
    receipt={'format':'awft-south48-botanical-admission:1','created':utcnow(),'checkpoint_sha256':CHECKPOINT_SHA,
        'source_manifest_sha256':prepared_sha,'sector':label,'targets':len(added['blocks']),
        'actual_native_before_proofs':proofs,'runtime':pins,'native_actions':0,'installed':False,
        'normal_neighbors_and_after_views_required':True,'reserve_guard':reserve,
        'files':{n:{'bytes':len(v),'sha256':hashlib.sha256(v).hexdigest()}for n,v in docs.items()}}
    docs['admission.json']=encoded(receipt)
    if sum(map(len,docs.values()))>4*MIB:raise UserError('Finite botanical admission exceeded')
    output.mkdir()
    for name,raw in docs.items():(output/name).write_bytes(raw)
    return {'output':str(output),'admission_sha256':digest(output/'admission.json'),'targets':len(added['blocks'])}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('operation',choices=('prepare','admit'),default='prepare',nargs='?')
    for k in ('home','output'):p.add_argument('--'+k,type=Path,required=True)
    p.add_argument('--pockets',type=int,default=224)
    for k in ('prepared','native-before','native-soil'):p.add_argument('--'+k,type=Path)
    for k in ('prepared-sha','sector'):p.add_argument('--'+k)
    a=p.parse_args()
    if a.operation=='prepare':result=prepare(a.home,a.output,a.pockets)
    else:
        if not all((a.prepared,a.prepared_sha,a.sector,a.native_before,a.native_soil)):p.error('admit needs exact source sector and both actual native proofs')
        result=admit(a.home,a.prepared,a.prepared_sha,a.sector,a.native_before,a.native_soil,a.output)
    print(json.dumps(result,indent=2))
