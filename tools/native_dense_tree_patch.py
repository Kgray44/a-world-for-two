"""Bind reviewed finite dense native-tree sources; never submit a native command.

No candidate, class hash, eligibility measurement or parent authority is invented.
The native implementation captures a NEW complete field for each root itself.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
import zipfile

from control_room.common import UserError,digest,read_json,utcnow
from tools.artistic_bridge_topside_inspection import current_pack,owned_regular
from tools.playtest import guard

MIB=1024**2
CLASSES={'native_class_sha256':'NativeTreePatchSupport','native_scope_sha256':'TreeGrowthScope',
         'native_guard_sha256':'mixin/NativeTreeGrowthGuardMixin','bee_audit_sha256':'TreeBeeAudit',
         'bee_facts_sha256':'BeeNestFacts','pre_mutation_field_check_sha256':'PreMutationFieldCheck',
         'native_readiness_sha256':'NativeTreePatchReadiness'}
MEMBERS=('plan','protection','eligible_land','prior_root_custody','patch_authority')


def reference(home,path,cap=16*MIB):
    path=owned_regular(home,path,cap)
    return {'path':path.relative_to(home).as_posix(),'bytes':path.stat().st_size,'sha256':digest(path)}


def genuine_inspect(home,path,plan_sha,checkpoint,candidate,bridge,native,root_ids):
    ref=reference(home,path,2*MIB);row=read_json(path)
    marker=owned_regular(home,Path(str(path)+'.complete'),128)
    if marker.read_text().strip()!=ref['sha256']:
        raise UserError('Actual immutable native INSPECT marker differs')
    wanted={'operation':'inspect','plan_sha256':plan_sha,'checkpoint_sha256':checkpoint,
            'candidate':candidate,'bridge':bridge,'native_class_sha256':native,'failures':0,
            'cleanup_passed':True,'world_recovery_required':False,'temporary_tickets_remaining':0,'pending_shared_futures':0,
            'root_count':len(root_ids)}
    if any(row.get(k)!=v for k,v in wanted.items())or row.get('error'):
        raise UserError('Complete clean actual current-class INSPECT is required before grow')
    from datetime import datetime,timezone
    try:age=(datetime.now(timezone.utc)-datetime.fromisoformat(row['finished'].replace('Z','+00:00'))).total_seconds()
    except(ValueError,KeyError,TypeError)as error:raise UserError('Real native INSPECT completion time required')from error
    roots=row.get('roots',[])
    if (not -30<=age<=1800 or len(roots)!=len(root_ids)
            or {r.get('root_id')for r in roots}!=set(root_ids)
            or any(r.get('status')!='CURRENT_NATIVE_FIELD_CAPTURED_NO_MUTATION'for r in roots)):
        raise UserError('Current complete per-root native INSPECT has expired or differs')
    return ref


def bind(home,source,source_sha,candidate,bridge,jar_sha,operation='inspect',native_inspect=None):
    home=Path(home).absolute();source=Path(source).absolute()
    if home.resolve()!=home or home.parent!=Path('D:/A World for Two/staging/world-tests'):
        raise UserError('Exact owned private artistic stage required')
    if operation not in('inspect','grow')or not re.fullmatch(r'\d+\.\d+\.\d+',bridge)or not re.fullmatch(r'[a-f0-9]{64}',jar_sha):
        raise UserError('Explicit operation and genuine compiled native identities required')
    source_ref=reference(home,source,2*MIB)
    if source_ref['sha256']!=source_sha:raise UserError('Reviewed immutable patch source differs')
    doc=read_json(source);current_path=home/'dashboard/settlement/backup-receipt.json'
    current=read_json(owned_regular(home,current_path,8192));owner=read_json(owned_regular(home,home/'dashboard/artistic-owner.json',65536))
    if (doc.get('format')!='awft-tree-patch-source-bundle:1' or current.get('verified')is not True
            or doc.get('checkpoint_sha256')!=current.get('sha256')or doc.get('checkpoint_id')!=current.get('id')
            or owner.get('format')!='awft-artistic-stage:1'or Path(owner.get('home','')).resolve()!=home):
        raise UserError('Actual current owned checkpoint and reviewed patch source required')
    if (home/'dashboard/settlement/tree-growth-quarantine.json').exists():
        raise UserError('Retain native tree quarantine; no request or automatic retry')
    release,pack=current_pack(home,candidate)
    installed=read_json(owned_regular(home,home/'server/installed.json',2*MIB))
    jar=owned_regular(home,home/'server/mods'/('awft-control-bridge-'+bridge+'.jar'),32*MIB)
    if digest(jar)!=jar_sha or installed.get('files',{}).get(jar.name)!=jar_sha:
        raise UserError('Exact actual installed compiled helper differs')
    pins={}
    with zipfile.ZipFile(jar)as archive:
        for key,name in CLASSES.items():
            member='worldfortwo/bridge/'+name+'.class'
            if member not in archive.namelist():raise UserError('Actual installed helper does not contain the new patch API; no placeholder class hashes')
            if not 0<archive.getinfo(member).file_size<=256*1024:raise UserError('Finite actual native class required')
            pins[key]=hashlib.sha256(archive.read(member)).hexdigest()
    refs={}
    for key in MEMBERS:
        facts=doc.get(key,{})
        if not isinstance(facts.get('path'),str)or '\\'in facts['path']or Path(facts['path']).is_absolute()or '..'in Path(facts['path']).parts:
            raise UserError('Owned immutable source member path required')
        path=source.parent/facts['path'];ref=reference(home,path)
        if ref['bytes']!=facts.get('bytes')or ref['sha256']!=facts.get('sha256'):
            raise UserError('Exact patch source member differs: '+key)
        refs[key]=ref
    plan=read_json(home/refs['plan']['path']);roots=plan.get('roots',[])
    if (plan.get('format')!='awft-native-tree-patch-plan:1'or not 1<=len(roots)<=32
            or len({r.get('id')for r in roots})!=len(roots)):
        raise UserError('A finite unique reviewed1..32 root patch is required')
    if operation=='grow':
        if native_inspect is None:raise UserError('A real native INSPECT is required; this producer cannot create one')
        refs['native_inspect']=genuine_inspect(home,Path(native_inspect).absolute(),refs['plan']['sha256'],current['sha256'],candidate,bridge,pins['native_class_sha256'],[r['id']for r in roots])
    request={'format':'awft-native-tree-patch:1','allowed_operation':operation,'candidate_version':candidate,
             'bridge_version':bridge,'pack_sha256':pack,'checkpoint_sha256':current['sha256'],
             'current_backup':reference(home,current_path,8192),**pins,**refs}
    raw=(json.dumps(request,separators=(',',':'))+'\n').encode();sha=hashlib.sha256(raw).hexdigest()
    output=home/'dashboard/settlement'/('treepatch-'+sha[:16])
    if output.exists():raise UserError('Preserve the existing request; no automatic unchanged retry')
    reserve=guard(0,4*MIB)
    receipt={'format':'awft-native-patch-request-owner:1','created':utcnow(),'request_sha256':sha,'source':source_ref,
             'source_generator_sha256':digest(Path(__file__)),'actual_helper':reference(home,jar,32*MIB),'actual_pack':reference(home,release,MIB),
             'native_runtime_proved_by_reading_installed_JAR':False,'native_actions':0,'world_writes':0,'reserve_guard':reserve,
             'parent_native_writer_preflight':{'C_bytes':32*MIB,'D_bytes':640*MIB,'ReserveGuard_required_before_native_operation':True},
             'next':'Parent types the explicit local console command; grow captures and checks every root again'}
    output.mkdir();(output/'request.json').write_bytes(raw);(output/'ownership.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    return {'output':str(output),'request_sha256':sha,'typed_command':'awfttreepatch '+operation+' '+output.name+' '+sha,'native_actions':0}


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--home',required=True);parser.add_argument('--source',required=True)
    parser.add_argument('--source-sha',required=True);parser.add_argument('--candidate',required=True);parser.add_argument('--bridge',required=True)
    parser.add_argument('--jar-sha',required=True);parser.add_argument('--operation',choices=('inspect','grow'),default='inspect');parser.add_argument('--native-inspect')
    args=parser.parse_args();print(json.dumps(bind(args.home,args.source,args.source_sha,args.candidate,args.bridge,args.jar_sha,args.operation,args.native_inspect),indent=2))
