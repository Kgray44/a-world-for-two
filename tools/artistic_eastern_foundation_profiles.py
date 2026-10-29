"""Below-plinth saved profiles and exactly bounded ordinary dry pier proposals.

Unknown/wet supports stay held. No game commands, generation or terrain platform.
"""
from pathlib import Path
import argparse,json,time
from collections import Counter
from control_room.common import UserError,digest,read_json,utcnow
from tools.artistic_eastern_compound_sprint import checked,key,VOID
from tools.artistic_eastern_first_prototypes import SOFT,MANMADE
from tools.artistic_ground_stability import STABLE_NATURAL,GRAVITY
from tools.artistic_create_substrate import verify_zinc_factory,JAR_SHA,CLASS_SHA
from tools.artistic_captains_hall import rectangle,boundary
from tools.artistic_north_bank_east import NorthTerrain,native_payload
from tools.artistic_materials import require_material_rule
from tools.artistic_quay_prototype import context,write_bundle
from tools.playtest import guard

MIB=1024**2
HANDOFF=('staging/eastern-full38-handoff-r27-1793223419939610800/handoff-SOURCE-ONLY.json','1f12ea421cbd7570babe52f5cd445fbffc66b675d9cd6e3072839b5dc056a33a')


def column(lookup,x,z,plinth,zinc):
    stack=[];fill=[]
    for y in range(plinth-1,max(-65,plinth-17),-1):
        value=lookup(x,y,z)
        if value is None:raise UserError('UNKNOWN below-plinth state')
        ident=key(value);stack.append([x,y,z,value])
        if'waterlogged=true'in value or ident in('minecraft:water','minecraft:lava'):return{'status':'HELD_WATER','stack':stack,'fill_positions':[],'reason':'No ordinary dry-pier fluid replacement authority; retain exact underground water for separate review'}
        if ident in STABLE_NATURAL:return{'status':'SAVED_NONFALLING_TERMINAL','stack':stack,'fill_positions':fill,'terminal':stack[-1]}
        if ident=='create:zinc_ore':
            if(zinc.get('artifact_sha256'),zinc.get('class_sha256'),zinc.get('factory_class'))!=(JAR_SHA,CLASS_SHA,'net/minecraft/world/level/block/Block'):raise UserError('Only exact already-reviewed pinned zinc factory may qualify')
            return{'status':'SAVED_PINNED_ZINC_TERMINAL','stack':stack,'fill_positions':fill,'terminal':stack[-1],'factory_receipt':zinc}
        if ident in VOID|SOFT:fill.append((x,y,z));continue
        if ident in GRAVITY|MANMADE:continue
        return{'status':'HELD_UNQUALIFIED_BLOCK','stack':stack,'fill_positions':[],'reason':'No generic modded/non-BE solidity assumption: '+value}
    return{'status':'HELD_FINITE_DEPTH','stack':stack,'fill_positions':[],'reason':'No real qualified terminal within16 below-plinth states'}


def prepare(home,output):
    reserve=guard(MIB,16*MIB);home,output,current,registry=context(home,output);handoff=checked(home,HANDOFF,2*MIB)
    if handoff['checkpoint_sha256']!=current['sha256']:raise UserError('Genuine current archive must match frozen architecture custody')
    zinc=verify_zinc_factory(home);terrain=NorthTerrain(home,current,registry);profiles=[];held=[];before={};delta={};context_states={};counts=Counter();byhouse={};began=time.monotonic()
    try:
        for row in handoff['compounds']:
            ref=row['files']['SOURCE-ONLY'];doc=checked(home,(ref['path'],ref['sha256']),8*MIB);full={tuple(v[:3]):v[3]for v in doc['complete_expected_state_context_ONLY']};house_delta={};house_profiles=[]
            for index,mass in enumerate(doc['masses']):
                cells=rectangle(*mass['bounds_xz']);plinth=mass['floor_y']-1
                for x,z in sorted(boundary(cells)):
                    result=column(terrain.state,x,z,plinth,zinc);counts[result['status']]+=1
                    record={'building':row['id'],'mass':index,'column':[x,z],'plinth_y':plinth,**result};profiles.append(record);house_profiles.append(record)
                    if any(tuple(v[:3])in terrain.entities for v in result['stack']):record['status']='HELD_ACTUAL_BE';record['fill_positions']=[];held.append(record);continue
                    if result['status'].startswith('HELD'):held.append(record);continue
                    for xx,y,zz,value in result['stack']:context_states[xx,y,zz]=value
                    plinth_material=full[x,plinth,z]
                    if plinth_material not in('minecraft:stone_bricks','minecraft:cobbled_deepslate'):raise UserError('Exact frozen structural plinth material required')
                    for q in result['fill_positions']:
                        old=terrain.state(*q)
                        if key(old)not in VOID|SOFT:raise UserError('Only exact ordinary AIR/soft dry cells may be a pier delta')
                        distance=plinth-q[1];mat=plinth_material
                        if distance%3==0:mat='minecraft:chiseled_stone_bricks'if mat=='minecraft:stone_bricks'else'minecraft:cracked_deepslate_bricks'
                        if q in delta and delta[q]!=mat:raise UserError('Conflicting approved footprint piers')
                        before[q]=old;delta[q]=mat;house_delta[q]=mat
            proof=require_material_rule({**full,**house_delta},row['id']+' complete frozen building and dry foundation delta')
            byhouse[row['id']]={'perimeter_profiles':len(house_profiles),'held_profiles':sum(r['status'].startswith('HELD')for r in house_profiles),'ordinary_dry_pier_cells':len(house_delta),'material_rule':proof,'no_main_floor_or_architecture_geometry_changes':True}
            if time.monotonic()-began>90:raise UserError('Finite90s foundation read bound exceeded')
        if not delta or len(delta)>512:raise UserError('Only a nonempty at-most512 exact ordinary dry-pier proposal')
        if any(q[1]>=64 for q in delta):raise UserError('No old room source snapshots may be modified by this subsurface proposal')
        sources=terrain.snapshot.sources
    finally:terrain.close()
    docs={'before-piers-and-retained-supports-VERIFY-ONLY.json':dict(native_payload(registry,{**context_states,**before},current['sha256'],'Actual saved dry-pier targets plus all qualified below-plinth terminal witnesses'),construction_forbidden=True,verification_only=True),
      'dry-piers-PROPOSAL.json':dict(native_payload(registry,delta,current['sha256'],'PROPOSED ordinary narrow dry piers only; no fluid/old BE/source-room edits'),construction_forbidden=True,verification_only=True),
      'dry-piers-NORMAL-SETTLE-ONLY.json':dict(native_payload(registry,delta,current['sha256'],'NORMAL SETTLE ONLY proposed dry piers after genuine native before and parent admission'),construction_forbidden=True,verification_only=True),
      'complete-piers-and-retained-supports-VERIFY-ONLY.json':dict(native_payload(registry,{**context_states,**delta},current['sha256'],'PROSPECTIVE exact dry piers and retained native profiles only; no building current-state claim'),construction_forbidden=True,verification_only=True)}
    docs['all-perimeter-profiles-READONLY.json']={'format':'awft-eastern-below-plinth-profiles:1','profiles':profiles,'held':held,'no_held_fluid_or_unknown_position_in_delta':True,'source_only':True,'native_actions':0}
    return write_bundle(output,docs,{'format':'awft-eastern-narrow-dry-foundation-source:1','created':utcnow(),'source_sha256':digest(Path(__file__)),'checkpoint_id':current['id'],'checkpoint_sha256':current['sha256'],'frozen_architecture_handoff':{'path':HANDOFF[0],'sha256':HANDOFF[1]},'by_building':byhouse,'profile_counts':dict(counts),'perimeter_profiles':len(profiles),'held_profiles':len(held),'dry_pier_targets':len(delta),'exact_pier_positions':[list(q)for q in sorted(delta)],'qualified_retained_profile_states':len(context_states),'zinc_factory_receipt':zinc,'archive_sources':sources,'source_only':True,'construction_forbidden':True,'native_actions':0,'world_writes':0,'reserve_guard':reserve,'next_gate':'Separate Root review, genuine fresh complete native BEFORE, exact typed admission and place/normal settle/strict after. Held water/modded supports remain unaccepted; no unchanged retry or whole-site foundation claim.'})


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--home',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();print(__import__('json').dumps(prepare(a.home,a.output),indent=2))
