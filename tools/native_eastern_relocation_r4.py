"""Seal new compiled callback guards and an optional explicit uninvoked review.

No runtime installation, ledger mutation, native command or approval fabrication.
"""
from __future__ import annotations
import argparse,hashlib,json,time
from pathlib import Path
from control_room.common import UserError,digest
from tools.artistic_east_tortuga_retrofit import checked
from tools.artistic_eastern_urban_custody import canonical
from tools.native_relocation_request import class_hash,reference
from tools.native_eastern_relocation_r3 import seal as seal_r3
from tools.playtest import guard

MIB=1024**2
TX='537132d7dc65e7758179b56109d518e8990cc422222b48f163a77a953178249b'
TERMINAL='36bc9697b81bf0c7ca760a1cfbc3178eeef151f3d507741199d8049d7f5a159b'
INTENT='a29842d7a1be6dd8f1ce557cd2d2daa0467539f7fce20059c09a8f8280a76bdd'
QUARANTINE='38723688b0abb171264e938a7ff79b47cd44c757a95431ed5c31e7a271bedf50'

def seal(home,request_path,request_sha,bridge_jar,*,review=None,review_sha=None):
    home=Path(home).resolve();reserve=guard(MIB,4*MIB)
    prior=seal_r3(home,request_path,request_sha,bridge_jar)
    req=checked(Path(prior['folder'])/'request.json',prior['request_sha256'],131072)
    for field,name in [('clone_binding_class_sha256','CloneBinding'),('uninvoked_class_sha256','Uninvoked')]:
        req[field]=class_hash(Path(bridge_jar),'worldfortwo.bridge.NativeRelocationSupport$'+name)
    if review is not None:
        data=checked(Path(review),review_sha,65536)
        if (data.get('format')!='awft-explicit-uninvoked-relocation-review:1' or data.get('approved') is not True
            or data.get('allow_exactly_one_new_intent') is not True or data.get('transaction_id')!=TX
            or req['transaction_id']!=TX or data.get('prior_intent_sha256')!=INTENT or data.get('prior_quarantine_sha256')!=QUARANTINE
            or data.get('prior_terminal',{}).get('sha256')!=TERMINAL):
            raise UserError('Exact separately reviewed original uninvoked transaction is required')
        old=data['prior_terminal'];checked(home/old['path'],TERMINAL,MIB)
        req['uninvoked_resolution_review']=reference(home,Path(review))
    raw=canonical(req)+b'\n';sha=hashlib.sha256(raw).hexdigest();out=home/'staging'/('relocation-'+sha[:16]+'-R4-SOURCE-'+str(time.time_ns()));out.mkdir()
    (out/'request.json').write_bytes(raw)
    manifest={'format':'awft-approved-relocation-request-source:4','request_sha256':sha,'source_sha256':digest(Path(__file__)),
        'runtime_bundle_name':'relocation-'+sha[:16],'capsule_id':req['capsule_id'],'explicit_uninvoked_review_present':review is not None,
        'request_installed':False,'native_actions':0,'reserve_guard':reserve}
    (out/'manifest.json').write_bytes(canonical(manifest)+b'\n');return {'folder':str(out),**manifest}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('home','request','bridge','review'):p.add_argument('--'+k,type=Path,required=k!='review')
    p.add_argument('--request-sha',required=True);p.add_argument('--review-sha');a=p.parse_args()
    print(json.dumps(seal(a.home,a.request,a.request_sha,a.bridge,review=a.review,review_sha=a.review_sha),indent=2))
