"""Seal the exact native MCW witness on an otherwise unchanged R5 request.

This creates a NEW private request only. It never installs or invokes one.
"""
from __future__ import annotations
import argparse,hashlib,json,time
from pathlib import Path
from control_room.common import UserError,digest
from tools.artistic_east_tortuga_retrofit import checked
from tools.artistic_eastern_urban_custody import canonical
from tools.native_relocation_request import class_hash
from tools.native_eastern_relocation_r5 import bind as bind_r5
from tools.playtest import guard

MIB=1024**2

def seal(home,request_path,request_sha,bridge_jar):
    home=Path(home).resolve();reserve=guard(MIB,MIB)
    request=checked(Path(request_path),request_sha,131072)
    if request.get('format')!='awft-native-approved-capsule-relocation:2':
        raise UserError('Exact already sealed R5 relocation request required')
    actual=class_hash(Path(bridge_jar),'worldfortwo.bridge.NativeRelocationSupport')
    if request.get('native_class_sha256')!=actual:
        raise UserError('Original request must already bind the actual R6 main helper')
    witness=class_hash(Path(bridge_jar),'worldfortwo.bridge.NativeWindowStateWitness')
    if 'native_window_witness_class_sha256' in request:
        raise UserError('Refuse resealing an already witnessed request')
    request['native_window_witness_class_sha256']=witness
    raw=canonical(request)+b'\n';sha=hashlib.sha256(raw).hexdigest()
    out=home/'staging'/('relocation-'+sha[:16]+'-R6-SOURCE-'+str(time.time_ns()));out.mkdir()
    (out/'request.json').write_bytes(raw)
    manifest={'format':'awft-approved-relocation-request-source:6','request_sha256':sha,
        'source_sha256':digest(Path(__file__)),'runtime_bundle_name':'relocation-'+sha[:16],
        'capsule_id':request['capsule_id'],'native_window_witness_class_sha256':witness,
        'prior_sealed_request_sha256':request_sha,'request_installed':False,'native_actions':0,
        'reserve_guard':reserve}
    (out/'manifest.json').write_bytes(canonical(manifest)+b'\n')
    return {'folder':str(out),**manifest}

def bind(home,*args,**kwargs):
    prior=bind_r5(home,*args,**kwargs)
    bridge=kwargs.get('bridge_jar',args[2] if len(args)>2 else None)
    if bridge is None:raise UserError('Exact actual bridge archive required')
    result=seal(home,Path(prior['folder'])/'request.json',prior['request_sha256'],bridge)
    result['prior_r5_folder']=prior['folder']
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('home','request','bridge'):p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--request-sha',required=True);a=p.parse_args()
    print(json.dumps(seal(a.home,a.request,a.request_sha,a.bridge),indent=2))
