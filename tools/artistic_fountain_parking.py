"""Prepare a fresh dry-gate before field and its separately evidenced request.

No server command, piston/fluid edit or historical checkpoint replay is made.
The actual native helper compares every state again before normal lever use.
"""
from __future__ import annotations
import argparse
import datetime as dt
import json
from pathlib import Path
import re
import tomllib
import zipfile

from control_room.common import Layout, REPO, UserError, digest, read_json, utcnow
from control_room.server import Server
from control_room.storage import Storage
from tools.artistic_fountain_commission import document, evidence, instant, owned, sha, STATUS
from tools.artistic_spawn_plaza import (
    HEADER, OUTLET, PISTON, PLUG_OPEN, STOP_LEVER, PUMP, WHEEL, WHEEL_SOURCE,
    JET_WITNESSES, payload,
)
from tools.playtest import guard
from tools.settlement_attractions import BackupWorld

INTAKE = (1139,65,-1129)
DIODE = (1138,73,-1125)
POSITIONS = frozenset((HEADER,OUTLET,PISTON,PLUG_OPEN,STOP_LEVER,PUMP,WHEEL,WHEEL_SOURCE,INTAKE,DIODE,*JET_WITNESSES))
CANDIDATE = '0.1.0-candidate.45'
BRIDGE = '0.6.31'
MIB = 1024**2


def state(value):
    if not isinstance(value,str) or not value:
        raise UserError('Literal current native block state required')
    name,sep,tail=value.partition('[')
    if not sep:return name,{}
    if not tail.endswith(']'):
        raise UserError('Malformed native state')
    try:props=dict(piece.split('=',1) for piece in tail[:-1].split(','))
    except ValueError as exc:raise UserError('Malformed native property') from exc
    return name,props


def classify(observed):
    """Conservative saved preflight, not a piston/circuit simulation."""
    if set(observed)!=POSITIONS:
        raise UserError('Exactly14 owned current cells required')
    if any(observed[p]!='minecraft:air' for p in (HEADER,WHEEL_SOURCE,*JET_WITNESSES)):
        raise UserError('Preserve wet sources/flows; this action only parks an already dry gate')
    intake=state(observed[INTAKE])
    if intake not in (('minecraft:water',{'level':'0'}),
            ('create:fluid_pipe',{'down':'true','east':'false','north':'false','south':'false','up':'true','waterlogged':'true','west':'false'})):
        raise UserError('Preserve the original open source-water intake or its exact observed native pipe predecessor')
    for p,name,facing in ((WHEEL,'create:water_wheel','west'),(PUMP,'create:mechanical_pump','east')):
        key,props=state(observed[p])
        if key!=name or props.get('facing')!=facing:
            raise UserError('Preserve the real oriented wheel and pump')
    lever,lp=state(observed[STOP_LEVER]);piston,pp=state(observed[PISTON]);diode,dp=state(observed[DIODE])
    if (lever!='minecraft:lever' or lp.get('face')!='wall' or lp.get('facing')!='east'
            or piston!='minecraft:sticky_piston' or pp.get('facing')!='north'
            or diode!='minecraft:repeater' or dp.get('facing')!='south' or dp.get('locked')!='false'
            or dp.get('delay')!='1'):
        raise UserError('Only this existing native gate and normal controls are admitted')
    arrangements={
        ('false','false','minecraft:chiseled_quartz_block','minecraft:air'):'ALREADY_PARKED',
        ('false','false','minecraft:air','minecraft:chiseled_quartz_block'):'DETACHED_PLUG',
        ('true','true','minecraft:piston_head[facing=north,short=false,type=sticky]','minecraft:chiseled_quartz_block'):'STABLE_ON',
    }
    baseline=arrangements.get((pp.get('extended'),lp.get('powered'),observed[PLUG_OPEN],observed[OUTLET]))
    if not baseline or dp.get('powered')!=lp.get('powered'):
        raise UserError('Fresh coherent stable dry gate required; preserve moving/unknown state')
    return baseline


def context(home):
    home=Path(home).absolute()
    if home.parent!=Path(r'D:\A World for Two\staging\world-tests'):
        raise UserError('An immediate owned private stage is required')
    owned(home,home,regular=False)
    owner,_=document(home,'dashboard/artistic-owner.json',65536)
    settings,_=document(home,'dashboard/settings.json',65536)
    registry,_=document(home,'dashboard/settlement/registry.json',8*MIB)
    checkpoint,_=document(home,'dashboard/settlement/backup-receipt.json',4096)
    if (owner.get('format')!='awft-artistic-stage:1' or Path(owner.get('home','')).absolute()!=home
            or settings.get('permanent_world') is not False or settings.get('port')!=25575
            or owner.get('minecraft_port')!=25575 or checkpoint.get('verified') is not True
            or Path(registry.get('world_path','')).absolute()!=home/'world/RosewaterArtistic'):
        raise UserError('Exact private world, owner, port and current verified checkpoint required')
    owned(home,home/'world/RosewaterArtistic',regular=False)
    return home,owner,registry,checkpoint


def write_new(folder,files):
    if folder.exists() or folder.is_symlink() or sum(len(raw) for raw in files.values())>256*1024:
        raise UserError('A new bounded immutable gate output is required')
    folder.mkdir()
    for name,raw in files.items():
        with (folder/name).open('xb') as stream:stream.write(raw)


def prepare_before(home,output):
    home,owner,registry,checkpoint=context(home)
    output=Path(output).absolute()
    if output.parent!=home/'staging':
        raise UserError('New immediate private staging output required')
    owned(home,output.parent,regular=False)
    if Server(Layout(home),Storage(Layout(home))).running():
        raise UserError('Finish the owner visit and take a fresh normal stopped checkpoint first')
    reserve=guard(MIB,MIB)
    snapshot=BackupWorld(home,checkpoint,registry)
    try:
        observed={p:snapshot.state(p) for p in sorted(POSITIONS)}
        if any(p in snapshot.protected for p in POSITIONS-{WHEEL,PUMP,INTAKE}):
            raise UserError('Preserve unexpected gate BEs, including historical moving pistons')
        baseline=classify(observed);sources=snapshot.sources.copy()
    finally:snapshot.close()
    plan=payload(registry,checkpoint['sha256'],observed,'ACTUAL current stable dry gate before normal parking',before=True)
    raw=(json.dumps(plan,separators=(',',':'))+'\n').encode()
    receipt={'format':'awft-current-dry-gate-before:1','created':utcnow(),'checkpoint':checkpoint,
             'actual_saved_baseline':baseline,'saved_sources':sources,'storage_guard':reserve,
             'plan_sha256':sha(raw),'native_actions':0,'world_writes':0,
             'note':'14 exact saved states; native helper must independently prove current dynamic states and zero RPM'}
    write_new(output,{'before.json':raw,'receipt.json':(json.dumps(receipt,indent=2)+'\n').encode()})
    return {'before':str(output/'before.json'),'sha256':sha(raw),'baseline':baseline,'native_actions':0}


def check_proof(proof,expected,now):
    if (proof.get('operation')!='verify' or proof.get('status')!=STATUS or proof.get('plan_sha256')!=expected
            or type(proof.get('blocks')) is not int or proof['blocks']!=14 or proof.get('cleanup_required') is not False or 'error' in proof):
        raise UserError('Actual complete clean14-state native verification required')
    for key in ('failures','temporary_tickets_remaining','pending_shared_chunk_futures'):
        if type(proof.get(key)) is not int or proof[key]!=0:raise UserError('Retain unresolved native failure or cleanup')
    if 'cleanup_failures' in proof and (type(proof['cleanup_failures']) is not int or proof['cleanup_failures']!=0):
        raise UserError('Native cleanup failure remains')
    start,finish=instant(proof.get('started')),instant(proof.get('finished'))
    if start>finish or finish>now or now-finish>dt.timedelta(minutes=30):
        raise UserError('Fresh native gate proof required')


def prepare_request(home,before,native_verify):
    home,owner,registry,checkpoint=context(home)
    plan,before_ref=document(home,before,65536)
    proof_path=owned(home,native_verify)
    if proof_path.parent!=home/'dashboard/settlement' or not re.fullmatch(r'settlement-result-[a-f0-9-]{36}\.json',proof_path.name):
        raise UserError('Actual owned native journal proof required')
    proof,proof_ref=document(home,proof_path,65536);check_proof(proof,before_ref['sha256'],dt.datetime.now(dt.timezone.utc))
    _,marker,marker_ref=evidence(home,proof_path.with_name(proof_path.name+'.complete'),128)
    if marker.decode('ascii').strip()!=proof_ref['sha256']:
        raise UserError('Actual completion digest differs')
    if (plan.get('format')!='awft-native-settlement:1' or plan.get('backup_sha256')!=checkpoint['sha256']
            or str(plan.get('seed'))!=str(registry['seed']) or plan.get('world_path')!=registry['world_path']
            or plan.get('verification_only') is not True or plan.get('construction_forbidden') is not True
            or plan.get('commands')!=[] or plan.get('block_entities')!=[] or len(plan.get('blocks',[]))!=14):
        raise UserError('Only the current stopped verification-only field is admitted')
    observed={tuple(row[:3]):plan['palette'][row[3]] for row in plan['blocks']}
    classify(observed)
    active,_=document(home,'packwiz/active.json',65536);installed,_=document(home,'server/installed.json',MIB)
    lock_path=REPO/'catalog/lock.json'
    if not 0<lock_path.stat().st_size<=2*MIB:raise UserError('Bounded parent-built catalog required')
    lock=read_json(lock_path);pack_sha=digest(REPO/'packwiz/pack.toml')
    selected=[r for r in lock['mods'] if r['slug']=='awft-control-bridge']
    if (lock.get('version')!=CANDIDATE or len(selected)!=1 or selected[0]['version']!=BRIDGE
            or active.get('version')!=CANDIDATE or installed.get('pack_version')!=CANDIDATE
            or any(d.get('pack_sha256')!=pack_sha for d in (active,installed,owner))):
        raise UserError('The exact parent-built current45 candidate must be installed first')
    bridge=selected[0];jar_sha=bridge['hashes']['sha256']
    if installed.get('files',{}).get(bridge['filename'])!=jar_sha:
        raise UserError('Actual installed bridge custody differs')
    jar,_,jar_ref=evidence(home,'server/mods/'+bridge['filename'],4*MIB,jar_sha)
    with zipfile.ZipFile(jar) as archive:
        name='worldfortwo/bridge/NativeFountainSupport.class'
        if not 0<archive.getinfo(name).file_size<256*1024:raise UserError('Bounded actual helper required')
        native_sha=sha(archive.read(name))
        if not 0<archive.getinfo('META-INF/neoforge.mods.toml').file_size<=65536:
            raise UserError('Bounded actual bridge descriptor required')
        meta=tomllib.loads(archive.read('META-INF/neoforge.mods.toml').decode())
        if not any(r.get('modId')=='awft_control_bridge' and r.get('version')==BRIDGE for r in meta.get('mods',[])):
            raise UserError('Actual bridge descriptor differs')
    request={'format':'awft-native-fountain:1','candidate':CANDIDATE,'bridge':BRIDGE,'pack_sha256':pack_sha,
             'seed':str(registry['seed']),'world_path':registry['world_path'],'backup_sha256':checkpoint['sha256'],
             'native_class_sha256':native_sha,'park_gate_before':before_ref,'park_gate_native_verify':proof_ref}
    raw=(json.dumps(request,separators=(',',':'))+'\n').encode();request_sha=sha(raw)
    folder=home/'dashboard/settlement'/('fountain-'+request_sha[:16]);reserve=guard(MIB,MIB)
    owned(home,folder.parent,regular=False)
    check_proof(document(home,proof_path,65536,proof_ref['sha256'])[0],before_ref['sha256'],dt.datetime.now(dt.timezone.utc))
    evidence(home,before,65536,before_ref['sha256'])
    receipt={'format':'awft-current-dry-gate-request:1','created':utcnow(),'producer_sha256':digest(Path(__file__)),
             'request_sha256':request_sha,'native_completion':marker_ref,'installed_bridge':jar_ref,
             'reserve':reserve,'world_writes':0,'native_actions':0,'authority':'Request only; parent must invoke the private typed park-gate action separately'}
    write_new(folder,{'request.json':raw,'ownership-receipt.json':(json.dumps(receipt,indent=2)+'\n').encode()})
    return {'bundle':folder.name,'sha256':request_sha,'native_actions':0,'world_writes':0}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--home',type=Path,required=True)
    commands=parser.add_subparsers(dest='action',required=True)
    before=commands.add_parser('before');before.add_argument('--output',type=Path,required=True)
    binding=commands.add_parser('request');binding.add_argument('--before',type=Path,required=True);binding.add_argument('--native-verify',type=Path,required=True)
    args=parser.parse_args()
    result=prepare_before(args.home,args.output) if args.action=='before' else prepare_request(args.home,args.before,args.native_verify)
    print(json.dumps(result))
