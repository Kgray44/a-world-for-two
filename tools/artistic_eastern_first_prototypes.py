"""Exact zero-capture eastern prototypes and bounded literal dry foundations.

Writes review/admission artifacts only. Never calls a game or changes a world.
"""
from __future__ import annotations
import argparse,json,time
from copy import deepcopy
from pathlib import Path
from control_room.common import UserError,digest,read_json,utcnow
from tools.artistic_bridge_refinement import flatten
from tools.artistic_captains_hall import rectangle,boundary
from tools.artistic_eastern_compound_sprint import checked,key,VOID
from tools.artistic_ground_stability import STABLE_NATURAL,GRAVITY
from tools.artistic_materials import require_material_rule
from tools.artistic_north_bank_east import NorthTerrain,native_payload
from tools.artistic_quay_prototype import context,bounded,member,same_world,fresh_proof,write_bundle
from tools.playtest import guard
from tools.artistic_zipline_catenary import reader_budget

MIB=1024**2
RANK=('staging/eastern-first-three-ranking-1793223652407637600/ranking-SOURCE-ONLY.json','2adab799ed704b631cf9f950adad03098816045115574eb28519856dd9daa525')
ALLOWED=('east-coal','shoal-warden','thin-sail')
SOFT={'minecraft:short_grass','minecraft:tall_grass','regions_unexplored:grass_sprouts','supplementaries:barnacles'}
MANMADE={'minecraft:'+s for s in('stone_bricks','mossy_stone_bricks','chiseled_stone_bricks','cobblestone','mossy_cobblestone','polished_andesite','cobbled_deepslate','spruce_planks','dark_oak_planks','oak_planks','stripped_spruce_wood')}


def profile(lookup,x,z,plinth_y,*,depth=16):
    """Start BELOW the authored plinth; stop only in actual non-falling ground."""
    if not 1<=depth<=24 or not-47<=plinth_y<=80:raise UserError('Finite reviewed below-plinth profile only')
    stack=[];fills=[]
    for y in range(plinth_y-1,plinth_y-depth-1,-1):
        value=lookup(x,y,z)
        if value is None:raise UserError('Unknown underlying profile is not a footing')
        ident=key(value);stack.append((x,y,z,value))
        if'waterlogged=true'in value or ident in('minecraft:water','minecraft:lava'):raise UserError('No open-water/flooded prototype foundation authority')
        if ident in STABLE_NATURAL:return{'stack':stack,'fill_positions':fills,'natural_terminal':stack[-1],'depth':len(stack)}
        if ident in VOID or ident in SOFT:fills.append((x,y,z));continue
        if ident in GRAVITY or ident in MANMADE:continue
        raise UserError('Unqualified underlying block/current structure is held: '+value)
    raise UserError('No actual natural ground within finite foundation depth')


def prepare(home,output):
    reserve=guard(2*MIB,16*MIB);home,output,current,registry=context(home,output)
    rank=checked(home,RANK,2*MIB)
    if(rank['ready_no_source_holds_or_future_context_conflicts'],rank['reviewed_safe_source_rows'])!=(3,37):raise UserError('Exact independent three-compound prerequisite ranking required')
    selected={r['building_id']:r for r in rank['ranked']if r['building_id']in ALLOWED}
    if set(selected)!=set(ALLOWED):raise UserError('Only the exact zero-capture three are admitted here')
    terrain=NorthTerrain(home,current,registry);documents={};records=[];combined_before={};combined_after={};began=time.monotonic()
    try:
        for ident in ALLOWED:
            row=selected[ident]
            if row['prerequisite_capture_count']or row['old_skin_groups']or not row['all_prerequisites_within_safe37_and_context_clear']:raise UserError('No room-move or old-skin dependency may enter this prototype')
            rr=row['files']['SOURCE-ONLY'];source=checked(home,(rr['path'],rr['sha256']),8*MIB)
            rr=row['files']['architecture-PROSPECTIVE-FORBIDDEN'];architecture=checked(home,(rr['path'],rr['sha256']),4*MIB)
            if source['retained_native_BE_positions']or source['required_native_completed_moves']or source['required_original_source_captures_before_architecture']:raise UserError('These prototypes have no conserved room/BE work to bypass')
            if source['actual_current_archive_checkpoint_sha256']!=current['sha256']:raise UserError('Current archive must genuinely match these frozen source fields')
            field=flatten(architecture);full={tuple(v[:3]):v[3]for v in source['complete_expected_state_context_ONLY']}
            before={};supports={};foundation={};profiles=[]
            for q in field:
                value=terrain.state(*q)
                if value is None:raise UserError('Unknown actual prototype target')
                if q in terrain.entities:raise UserError('Actual BE in a new zero-capture target; never overwrite it')
                before[q]=value
                if q[1]>=64 and key(value)not in VOID|SOFT:raise UserError('Unexpected current non-cover object in the actual new prototype volume: '+str((q,value)))
            for m in source['masses']:
                cells=rectangle(*m['bounds_xz']);plinth=m['floor_y']-1
                for x,z in sorted(boundary(cells)):
                    result=profile(terrain.state,x,z,plinth)
                    for xx,y,zz,value in result['stack']:
                        q=xx,y,zz
                        if q in terrain.entities:raise UserError('An actual BE cannot be a foundation profile or target')
                        supports[q]=value
                    along_x=(x-1,z)in cells and(x+1,z)in cells
                    for q in result['fill_positions']:
                        distance=plinth-q[1]
                        material=('minecraft:chiseled_stone_bricks'if along_x else'minecraft:cracked_deepslate_bricks')if distance%3==0 else('minecraft:stone_bricks'if along_x else'minecraft:cobbled_deepslate')
                        foundation[q]=material
                    profiles.append({'column':[x,z],'proposed_plinth_y':plinth,**result})
            if set(field)&set(foundation):raise UserError('Foundation must stay strictly below the unchanged authored plinth')
            field.update(foundation);full.update(foundation)
            before.update({q:supports[q]for q in foundation});witnesses={q:v for q,v in supports.items()if q not in field}
            expected={**witnesses,**full};observed={**supports,**before}
            if any(q in combined_before and combined_before[q]!=v for q,v in observed.items()):raise UserError('Conflicting exact current prototype fields')
            combined_before.update(observed);combined_after.update(expected)
            material=require_material_rule(full,ident+' complete frozen architecture plus narrow literal piers')
            delta=native_payload(registry,field,current['sha256'],'PROPOSED exact '+ident+' zero-capture architecture and narrow dry piers')
            delta.update(block_entities=deepcopy(architecture['block_entities']),construction_forbidden=True,verification_only=True)
            after=native_payload(registry,expected,current['sha256'],'VERIFY complete '+ident+' architecture plus retained actual foundation witnesses')
            after.update(block_entities=deepcopy(architecture['block_entities']),construction_forbidden=True,verification_only=True)
            settle=native_payload(registry,field,current['sha256'],'NORMAL SETTLE ONLY exact '+ident+' new blocks; never native inventory replay')
            settle.update(construction_forbidden=True,verification_only=True)
            documents[ident+'-PENDING-NATIVE.json']=delta;documents[ident+'-complete-after-VERIFY-ONLY.json']=after;documents[ident+'-NORMAL-SETTLE-ONLY.json']=settle
            documents[ident+'-supports-VERIFY-ONLY.json']=dict(native_payload(registry,supports,current['sha256'],'Actual saved below-plinth profiles for '+ident),construction_forbidden=True,verification_only=True)
            records.append({'id':ident,'frozen_architecture':row['files']['SOURCE-ONLY'],'frozen_architecture_targets':len(flatten(architecture)),'foundation_targets':len(foundation),'targets':len(field),'actual_underlying_profile_columns':len(profiles),'profiles':profiles,'all_profiles_terminate_in_actual_nonfalling_natural_ground':True,'all_old_and_current_BE_targets':0,'material_rule':material,'furnished_floors':len(source['rooms']),'mass_count':len(source['masses'])})
            reader_budget()
            if time.monotonic()-began>90:raise UserError('Finite90s prototype preparation exceeded')
        documents['before-targets-supports-VERIFY-ONLY.json']=dict(native_payload(registry,combined_before,current['sha256'],'Exact ACTUAL saved three-prototype targets plus complete underlying dry support profiles'),construction_forbidden=True,verification_only=True)
        documents['complete-three-after-VERIFY-ONLY.json']=dict(native_payload(registry,combined_after,current['sha256'],'VERIFY all three source architectures and retained actual dry support profiles'),construction_forbidden=True,verification_only=True)
        sources=terrain.snapshot.sources
    finally:terrain.close()
    return write_bundle(output,documents,{'format':'awft-eastern-zero-capture-native-prototypes:1','created':utcnow(),'source_sha256':digest(Path(__file__)),'checkpoint_id':current['id'],'checkpoint_sha256':current['sha256'],'rank':{'path':RANK[0],'sha256':RANK[1]},'records':records,'before_count':len(combined_before),'expected_after_count':len(combined_after),'world_writes':0,'native_actions':0,'construction_forbidden':True,'archive_sources':sources,'storage_guard':reserve,'next_gate':'Real fresh native complete BEFORE -> exact new private binder -> Root PLACE once/normal joins/full after and actual views. No conservation shortcut or old inventory replay.'})


def bind(home,prepared,prepared_sha,native_before,output):
    reserve=guard(2*MIB,16*MIB);home,output,current,registry=context(home,output)
    prepared=Path(prepared).resolve();native_before=Path(native_before).resolve()
    if prepared.parent!=home/'staging'or not native_before.is_relative_to(home/'dashboard/settlement'):raise UserError('Owned prepared source/native proof only')
    data=bounded(prepared/'manifest.json')
    if digest(prepared/'manifest.json')!=prepared_sha or data['format']!='awft-eastern-zero-capture-native-prototypes:1':raise UserError('Exact prepared prototype manifest required')
    if(data['checkpoint_id'],data['checkpoint_sha256'])!=(current['id'],current['sha256']):raise UserError('Current authentic stopped checkpoint differs')
    before=member(prepared,data,'before-targets-supports-VERIFY-ONLY.json');same_world(before,registry)
    if before.get('block_entities')or before.get('commands')or not before.get('construction_forbidden'):raise UserError('Only exact empty-BE no-command native BEFORE authority')
    proof,marker=fresh_proof(native_before,digest(prepared/'before-targets-supports-VERIFY-ONLY.json'),len(before['blocks']))
    beforefield=flatten(before);documents={}
    if{r['id']for r in data['records']}!=set(ALLOWED):raise UserError('No extra architecture may enter this admission')
    for row in data['records']:
        ident=row['id'];pending=member(prepared,data,ident+'-PENDING-NATIVE.json');after=member(prepared,data,ident+'-complete-after-VERIFY-ONLY.json');settle=member(prepared,data,ident+'-NORMAL-SETTLE-ONLY.json')
        for doc in(pending,after,settle):
            same_world(doc,registry)
            if doc.get('backup_sha256')!=current['sha256']or doc.get('commands')or doc.get('construction_forbidden')is not True:raise UserError('No stale or command geometry admission')
        field=flatten(pending);afterfield=flatten(after)
        if not field or not set(field)<=set(beforefield)or any(afterfield.get(q)!=v for q,v in field.items()):raise UserError('Exact complete after field required')
        admitted=deepcopy(pending);admitted.pop('construction_forbidden',None);admitted.pop('verification_only',None);admitted['name']='ADMITTED ONCE exact reviewed zero-capture prototype '+ident
        documents[ident+'-PLACE-ONCE.json']=admitted;documents[ident+'-NORMAL-SETTLE-ONLY.json']=settle;documents[ident+'-complete-after-VERIFY-ONLY.json']=after
    documents['complete-three-after-VERIFY-ONLY.json']=member(prepared,data,'complete-three-after-VERIFY-ONLY.json')
    return write_bundle(output,documents,{'format':'awft-admitted-eastern-zero-capture-prototypes:1','created':utcnow(),'source_sha256':digest(Path(__file__)),'checkpoint_id':current['id'],'checkpoint_sha256':current['sha256'],'prepared_relative':prepared.relative_to(home).as_posix(),'prepared_sha256':prepared_sha,'actual_native_before':{'path':native_before.relative_to(home).as_posix(),'sha256':digest(native_before),'marker_sha256':digest(marker),'finished':proof['finished']},'records':[{k:v for k,v in r.items()if k!='profiles'}for r in data['records']],'world_writes':0,'native_actions':0,'storage_guard':reserve,'next_gate':'Root exact PLACE once each, normal settle, per-prototype and whole strict verification, genuine day/night/interior/ordinary use review'})


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='action',required=True)
    a=sub.add_parser('prepare');a.add_argument('--home',required=True,type=Path);a.add_argument('--output',required=True,type=Path)
    a=sub.add_parser('bind')
    for name in('home','prepared','native-before','output'):a.add_argument('--'+name,required=True,type=Path)
    a.add_argument('--prepared-sha',required=True)
    args=p.parse_args();result=prepare(args.home,args.output)if args.action=='prepare'else bind(args.home,args.prepared,args.prepared_sha,args.native_before,args.output)
    print(json.dumps(result,indent=2))
