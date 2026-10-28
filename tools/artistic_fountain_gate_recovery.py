"""One-lever normal sticky-gate recovery proposal; no native/world action.

The exact saved circuit is already OFF, but its retracted sticky piston left the
plug at the closed port. Do not replace that correctly phased circuit or replay
the art. Every future ON/OFF target below is prospective until native verified.
"""
from pathlib import Path
import argparse,hashlib,json,time
from control_room.common import UserError,digest,read_json,utcnow
from tools.playtest import guard
from tools.settlement_attractions import BackupWorld
from tools.artistic_spawn_plaza import payload,state,STOP_LEVER,PISTON,PLUG_OPEN,OUTLET,HEADER,WHEEL_SOURCE,JET_WITNESSES

CHECKPOINT='20261027T231434Z-a631c0'
SHA='974382f0ad39b1730ebce96fb91f154789ec1616f23d46405f136ea7bcc0cea2'
SOURCE=(1141,66,-1125);DIODE=(1138,73,-1125)
TORCHES=((1141,67,-1125),(1140,68,-1125),(1141,69,-1125),(1140,70,-1125),(1141,71,-1125),(1140,72,-1125))
WIRES=((1139,73,-1125),(1139,73,-1124),(1138,73,-1124))


def replace_property(value,name,desired):
    if '[' not in value:raise UserError('Exact existing block property required')
    key,tail=value.split('[',1);props=dict(v.split('=',1) for v in tail[:-1].split(','))
    if name not in props:raise UserError('Do not invent an absent control property')
    props[name]=str(desired).lower();return key+'['+','.join(k+'='+v for k,v in sorted(props.items()))+']'


def expected_states(registry,observed,on):
    result=dict(observed);result[STOP_LEVER]=replace_property(observed[STOP_LEVER],'powered',on)
    for n,p in enumerate(TORCHES):result[p]=replace_property(observed[p],'lit',(n%2==1) if on else (n%2==0))
    for n,p in enumerate(WIRES):result[p]=replace_property(observed[p],'power',15-n if on else 0)
    result[DIODE]=replace_property(observed[DIODE],'powered',on)
    result[PISTON]=state(registry,'minecraft:sticky_piston',extended=on,facing='north')
    result[PLUG_OPEN]=state(registry,'minecraft:piston_head',facing='north',short=False,type='sticky') if on else 'minecraft:chiseled_quartz_block'
    result[OUTLET]='minecraft:chiseled_quartz_block' if on else 'minecraft:air'
    return result


def prepare(home):
    home=Path(home).resolve()
    if not home.is_relative_to(Path(r'D:\A World for Two\staging\world-tests')):raise UserError('Owned private artistic staging only')
    reserve=guard(1024**2,1024**2);registry=read_json(home/'dashboard/settlement/registry.json')
    observed_positions={STOP_LEVER,SOURCE,DIODE,PISTON,PLUG_OPEN,OUTLET,HEADER,WHEEL_SOURCE,*TORCHES,*WIRES,*JET_WITNESSES}
    snapshot=BackupWorld(home,{'id':CHECKPOINT,'sha256':SHA,'verified':True},registry)
    try:
        observed={p:snapshot.state(p) for p in sorted(observed_positions)}
        if any(p in snapshot.protected for p in observed_positions):raise UserError('Retain every actual native BE; recovery only permits one ordinary lever')
        if observed[STOP_LEVER]!=state(registry,'minecraft:lever',face='wall',facing='east',powered=False) or observed[SOURCE]!='minecraft:chiseled_quartz_block':raise UserError('Exact actual OFF lever and attached source required')
        if observed[PISTON]!=state(registry,'minecraft:sticky_piston',extended=False,facing='north') or observed[PLUG_OPEN]!='minecraft:air' or observed[OUTLET]!='minecraft:chiseled_quartz_block':raise UserError('Only the proved retracted-piston/detached-port-plug state is admitted')
        if 'facing=south' not in observed[DIODE] or 'powered=false' not in observed[DIODE]:raise UserError('Do not replace a currently correct south-facing OFF diode')
        if any('lit='+str(n%2==0).lower() not in observed[p] for n,p in enumerate(TORCHES)) or any('power=0' not in observed[p] for p in WIRES):raise UserError('The exact already-correct six-stage OFF parity is required')
        if any(observed[p]!='minecraft:air' for p in (HEADER,WHEEL_SOURCE,*JET_WITNESSES)):raise UserError('Only current naturally drained high header/source/jets can recover')
        sources=snapshot.sources.copy()
    finally:snapshot.close()
    on=expected_states(registry,observed,True);off=expected_states(registry,observed,False)
    docs={'actual-off-orphaned-BEFORE-VERIFY-ONLY.json':payload(registry,SHA,observed,'OBSERVED OFF/retracted piston with detached port plug',before=True)}
    for label,target in (('ON',on),('OFF',off)):
        docs[label+'-ONE-LEVER-DELTA.json']=payload(registry,SHA,{STOP_LEVER:target[STOP_LEVER]},label+' desired ONE ordinary lever only')
        settle=payload(registry,SHA,{STOP_LEVER:target[STOP_LEVER],SOURCE:observed[SOURCE]},label+' SETTLE ONLY normal lever plus attached-source notifications',before=True)
        settle['allowed_reviewed_operations']=['settle','verify'];settle['not_a_placement_plan']=True
        docs[label+'-NOTIFY-SETTLE-ONLY.json']=settle
        verify=payload(registry,SHA,target,label+' PROSPECTIVE stable actual gate/torch/dry-state verification',before=True)
        verify.update(prospective_expected_states=True,observed_until_actual_native_verify=False)
        verify['existing_awftbuild_verifier_scope']='Structural identity/orientation only. Independent fresh native/saved properties MUST prove lit/power/extended; do not treat these desired values as measured.'
        docs[label+'-STABLE-VERIFY-ONLY.json']=verify
    raw={name:(json.dumps(doc,separators=(',',':'))+'\n').encode() for name,doc in docs.items()}
    manifest={'format':'awft-one-lever-sticky-recovery:1','created':utcnow(),'source_sha256':digest(Path(__file__)),'checkpoint_id':CHECKPOINT,'checkpoint_sha256':SHA,'reserve':reserve,'saved_sources':sources,'actual_observed_diagnosis':'OFF parity and retracted piston; detached ordinary plug at closed port. No current feedback or extended piston is asserted. Exact cause of prior detachment remains unproved.','only_place_target':list(STOP_LEVER),'direct_piston_plug_source_header_BE_kinetic_or_inventory_writes':0,'stages':[{'step':1,'operation':'verify','file':'actual-off-orphaned-BEFORE-VERIFY-ONLY.json','gate':'Fresh native exact comparison0failures/cleanup before changing lever'},{'step':2,'operation':'place','file':'ON-ONE-LEVER-DELTA.json'},{'step':3,'operation':'settle','file':'ON-NOTIFY-SETTLE-ONLY.json','gate':'Normal notifications at lever and attached-source block; no direct circuit-state replacement'},{'step':4,'operation':'verify','file':'ON-STABLE-VERIFY-ONLY.json','gate':'Prospective until0failures native actual extended piston/sticky head/port plug/6torch parity'},{'step':5,'operation':'hold','minimum_actual_native_game_ticks':20,'gate':'Native game/tick witness REQUIRED, followed by another ON strictverify. Wall-clock sleeping alone is not this proof.'},{'step':6,'operation':'place','file':'OFF-ONE-LEVER-DELTA.json','gate':'Only after BOTH stable ON native proofs and>=20gt hold'},{'step':7,'operation':'settle','file':'OFF-NOTIFY-SETTLE-ONLY.json'},{'step':8,'operation':'verify','file':'OFF-STABLE-VERIFY-ONLY.json','gate':'Actual retracted piston, returned plug at OPEN, portAIR, six-stage OFF parity and all high fluidsAIR; require second proof after>=20gt'}],'failure_policy':'Preserve partial state/receipts; stop. Never replay blind or directly move the piston/head/plug. A fresh dry stopped checkpoint precedes R5 art generation.','native_actions':0,'native_recovery_acceptance':False,'files':{n:{'sha256':hashlib.sha256(v).hexdigest(),'bytes':len(v)} for n,v in raw.items()}}
    manifest['proof_scope_correction']={'structural_verify_is_not_dynamic_state_proof':True,'independent_dynamic_properties_required':['all6torches lit','all3dust power','diode powered','piston extended'],'server_tick_events_are_not_moving_BE_progress':True,'actual_dimension_BE_tick_or_real_player_wake_required':True,'retained_native_failure':'Actual43 ON showed moving_piston after100server ticks with empty dimension; immutable prior bundle/failure retained'}
    manifest['stages'][3]['gate']='Structural native comparison plus INDEPENDENT current lit/power/extended observations; native moving-piston BE must actually finish'
    manifest['stages'][4]['gate']='Native server-tick interval>=20 plus actual dimension/BE progress, followed by structural AND independent dynamic-property proof; wall-clock sleep alone insufficient'
    manifest['stages'][7]['gate']='Actual returned plug/port identities plus independent OFF parity/extended properties; second structural+property proof after>=20native ticks with actual BE progress'
    raw['manifest.json']=(json.dumps(manifest,indent=2)+'\n').encode()
    if sum(map(len,raw.values()))>1024**2:raise UserError('Finite1MiB one-lever source output exceeded')
    out=home/'staging'/('fountain-one-lever-recovery-'+str(time.time_ns()));out.mkdir()
    for n,v in raw.items():(out/n).write_bytes(v)
    return {'directory':str(out),'manifest_sha256':digest(out/'manifest.json'),'place_target_count':1,'observed_positions':len(observed),'files':manifest['files'],'native_actions':0}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--home',type=Path,required=True)
    print(json.dumps(prepare(p.parse_args().home),indent=2))
