"""Create an immutable request for the parent's real-level import helper.

This writes a small request only. It never copies a JAR, starts a server, places
geometry, issues the returned console command or spawns any entity.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import zipfile

sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from control_room.common import UserError, digest, read_json, utcnow
from tools.artistic_imported_builds import ORIGINALS
from tools.playtest import guard

SOURCE_SHA={'tavern':'e09d9d47685a36efd485bd11510c4ff65acc128d9e7ce0feb0b363e33006543c',
            'shop':'b6e7e85a3747abdaf510752e2b95d7bd98d21eda685ec4dd7d443e992e38022f'}
BEFORE_SHA={'tavern':'1d76f2c6e586eda8cd13703ad804c8cecce973115202c5ccf17756db8e541bb3',
            'shop':'79e0543773de1eb44c4d6c8f7d16b86dc73c078ff540e7fa85e1535a3a43de6f'}


def prepare(home,source,kind,before_proof,placement_proof,bridge_jar,candidate,bridge_version,
            plan=None,preimage=None):
    home,source,before_proof,placement_proof,bridge_jar=(Path(p).resolve() for p in
        (home,source,before_proof,placement_proof,bridge_jar))
    if kind not in ORIGINALS or not home.is_relative_to(Path(r'D:\A World for Two\staging\world-tests')):
        raise UserError('One exact original and an owned private artistic home are required')
    source_plan=source/(kind+'-adapted.json');source_before=source/(kind+'-native-before.json')
    plan=Path(plan).resolve() if plan else source_plan
    preimage=Path(preimage).resolve() if preimage else source_before
    def ref(path,cap):
        if not path.is_relative_to(home) or not path.is_file() or not 0<path.stat().st_size<=cap:
            raise UserError('A finite owned existing evidence file is required')
        return {'path':path.relative_to(home).as_posix(),'bytes':path.stat().st_size,'sha256':digest(path)}
    if digest(source_plan)!=SOURCE_SHA[kind] or digest(source_before)!=BEFORE_SHA[kind]:
        raise UserError('The exact frozen original source and saved preimage are required')
    checkpoint=home/'dashboard/settlement/backup-receipt.json';receipt=read_json(checkpoint)
    if receipt.get('verified') is not True:raise UserError('Verified current checkpoint required')
    for immutable,current in ((source_plan,plan),(source_before,preimage)):
        expected=read_json(immutable);expected['backup_sha256']=receipt['sha256']
        if read_json(current)!=expected:
            raise UserError('A current native plan may change only checkpoint binding')
    for path,operation,target in ((before_proof,'verify',preimage),(placement_proof,'place',plan)):
        value=read_json(path);marker=path.with_name(path.name+'.complete')
        if (not marker.is_file() or marker.stat().st_size>128 or marker.read_text('utf-8').strip()!=digest(path)
                or value.get('operation')!=operation or value.get('plan_sha256')!=digest(target)
                or value.get('failures')!=0 or value.get('error') or value.get('blocks')!=len(read_json(plan)['blocks'])):
            raise UserError('Exact completed native preimage and placement receipts are required')
    if not bridge_jar.is_relative_to(home/'server/mods') or bridge_jar.stat().st_size>4*1024**2:
        raise UserError('The actual bounded installed candidate bridge JAR is required')
    with zipfile.ZipFile(bridge_jar) as archive:
        info=archive.getinfo('worldfortwo/bridge/NativeImportJoins.class')
        if info.file_size>256*1024:raise UserError('Native helper class exceeds bound')
        native_class=hashlib.sha256(archive.read(info)).hexdigest()
    request={'format':'awft-native-import-joins:1','created':utcnow(),'kind':kind,
        'candidate_version':candidate,'bridge_version':bridge_version,'native_class_sha256':native_class,
        'source_plan':ref(source_plan,4*1024**2),'source_preimage':ref(source_before,4*1024**2),
        'plan':ref(plan,4*1024**2),'preimage_plan':ref(preimage,4*1024**2),
        'current_backup':ref(checkpoint,4096),'native_before':ref(before_proof,512*1024),
        'native_placement':ref(placement_proof,512*1024)}
    raw=(json.dumps(request,separators=(',',':'),ensure_ascii=False)+'\n').encode()
    if len(raw)>128*1024:raise UserError('Immutable request exceeds finite bound')
    sha=hashlib.sha256(raw).hexdigest();name='import-joins-'+sha[:16]
    output=home/'dashboard/settlement'/name
    if output.exists():raise UserError('New immutable request directory required')
    guard(0,1024*1024)
    output.mkdir();(output/'request.json').write_bytes(raw)
    return {'request':str(output/'request.json'),'request_sha256':sha,
            'console_command':'awftimport settle '+name+' '+sha,
            'native_action':'NOT EXECUTED. Parent-controlled actual staging admission only.'}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('home','source','before-proof','placement-proof','bridge-jar'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--kind',choices=tuple(ORIGINALS),required=True)
    p.add_argument('--candidate',required=True);p.add_argument('--bridge-version',required=True)
    p.add_argument('--plan',type=Path);p.add_argument('--preimage',type=Path)
    a=p.parse_args()
    print(json.dumps(prepare(a.home,a.source,a.kind,a.before_proof,a.placement_proof,a.bridge_jar,
                            a.candidate,a.bridge_version,a.plan,a.preimage),indent=2))
