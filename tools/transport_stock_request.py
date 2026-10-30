"""Prepare a fixed-stock packet in an owned source folder; never publish or run it.

Master must separately authorize/copy the exact packet into its native command
directory and execute the returned typed command under the real exclusive lease.
No native receipt, marker, item, process or world mutation is generated here.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import re
from uuid import UUID
import zipfile

from control_room.common import REPO, UserError
from tools.playtest import guard
from tools.transport_commission import _time
from tools.transport_material_audit import _json, _regular

STAGING_ROOT = Path(r'D:\A World for Two\staging\world-tests')
OUTPUT_ROOT = REPO/'.local'
CLASSES = {
    'adapter_class_sha256':'CopperWrenStockSupport',
    'construction_class_sha256':'CopperWrenConstructionStock',
    'schedule_item_class_sha256':'CopperWrenScheduleItem',
    'station_names_class_sha256':'CopperWrenStationNames',
    'passenger_factory_class_sha256':'CopperWrenPassengerSchedule',
    'journal_class_sha256':'NativeJournal',
}
LEDGER = 'data/awft-copper-wren-construction-stock-r1'
UUID_TEXT = r'[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}'


def need(value, message):
    if not value:
        raise UserError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read(home, relative, cap=65536):
    return _regular(home,home/relative,cap)


def environment(home, expected_bridge_sha256):
    home=Path(home).absolute()
    need(home.parent==STAGING_ROOT.resolve(strict=True) and home.resolve(strict=True)==home,
         'Exact private construction home ancestry required')
    world=home/'world/RosewaterArtistic'
    need(world.is_dir() and world.resolve(strict=True)==world,'Canonical actual construction world required')
    owner=_json(read(home,'dashboard/artistic-owner.json'))
    settings=_json(read(home,'dashboard/settings.json'))
    need(owner.get('format')=='awft-artistic-stage:1' and owner.get('home')==str(home)
         and settings.get('permanent_world') is False and type(settings.get('port')) is int and settings['port']==25575,
         'Owned private artistic home/port required')
    active=_json(read(home,'packwiz/active.json'))
    installed=_json(read(home,'server/installed.json',128*1024))
    candidate=active.get('version','');pack=active.get('pack_sha256','')
    need(re.fullmatch(r'0\.1\.0-candidate\.\d+',candidate) and re.fullmatch('[a-f0-9]{64}',pack)
         and installed.get('pack_version')==candidate and installed.get('pack_sha256')==pack,
         'Exact actual active/installed candidate pack required')
    need(re.fullmatch('[a-f0-9]{64}',expected_bridge_sha256 or ''),'Master-deployed bridge SHA required; no automatic adoption')
    jars=list((home/'server/mods').glob('awft-control-bridge-*.jar'))
    need(len(jars)==1,'Exactly one installed bridge JAR required')
    match=re.fullmatch(r'awft-control-bridge-(0\.6\.\d+)\.jar',jars[0].name)
    need(match is not None,'Exact installed bridge identity required')
    raw=_regular(home,jars[0],2*1024**2)
    need(sha(raw)==expected_bridge_sha256 and installed.get('files',{}).get(jars[0].name)==expected_bridge_sha256,
         'Actual installed bridge bytes differ from the master-deployed pin')
    classes={}
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        for key,name in CLASSES.items():
            member='worldfortwo/bridge/'+name+'.class'
            need(archive.namelist().count(member)==1,'Actual installed stock adapter/collaborator unavailable or duplicated: '+name)
            need(0<archive.getinfo(member).file_size<=256*1024,'Bounded installed native class required')
            with archive.open(member) as stream:
                code=stream.read(256*1024+1)
            need(len(code)<=256*1024 and code.startswith(b'\xca\xfe\xba\xbe'),'Actual native class bytes required')
            classes[key]=sha(code)
    backup_raw=read(home,'dashboard/settlement/backup-receipt.json',4096)
    backup=_json(backup_raw)
    need(backup.get('verified') is True and re.fullmatch(r'\d{8}T\d{6}Z-[a-f0-9]{6}',backup.get('id',''))
         and re.fullmatch('[a-f0-9]{64}',backup.get('sha256','')),'Exact current canonical verified backup required')
    return home,world,candidate,match[1],pack,classes,backup,sha(backup_raw)


def inspection(home, world, path, *, candidate, bridge, pack, bridge_sha, classes, backup_sha, now):
    path=Path(path).absolute()
    need(path.parent==home/'dashboard/settlement' and re.fullmatch('copper-stock-result-'+UUID_TEXT+r'\.json',path.name),
         'Canonical actual native stock inspection required')
    raw=_regular(home,path,128*1024);digest=sha(raw)
    need(_regular(home,Path(str(path)+'.complete'),64)==digest.encode(),'Exact immutable native inspection marker required')
    prior=_json(raw)
    need(prior.get('format')=='awft-native-copper-stock:1' and prior.get('operation')=='inspect'
         and prior.get('status')=='inspected actual starter; no stock authored' and 'error' not in prior
         and prior.get('cleanup_passed') is True and prior.get('lease_acquired') is True
         and prior.get('lease_released') is True and prior.get('cleanup_errors')==[]
         and prior.get('world_mutated') is False and prior.get('temporary_tickets_remaining')==0
         and prior.get('pending_shared_chunk_futures')==0,'Successful clean genuine native stock inspection required')
    need(0<=(now-_time(prior.get('at'))).total_seconds()<=60,'Native stock inspection expired or is future-dated')
    need(prior.get('world')==str(world) and prior.get('candidate')==candidate and prior.get('bridge')==bridge
         and prior.get('pack_sha256')==pack and prior.get('bridge_jar_sha256')==bridge_sha and prior.get('artifact_class_sha256')==classes
         and prior.get('backup_receipt_sha256')==backup_sha,'Inspection world/artifact/current-backup identity differs')
    try:
        need(str(UUID(prior.get('boot_id')))==prior.get('boot_id'),'Actual native inspection boot UUID required')
    except (ValueError,TypeError,AttributeError) as error:
        raise UserError('Actual native inspection boot UUID required') from error
    metrics=_json(read(home,'dashboard/server-metrics.json',2*1024**2))
    need(metrics.get('format')=='awft-metrics:1' and type(metrics.get('pid')) is int and metrics['pid']>0
         and type(prior.get('pid')) is int
         and metrics['pid']==prior.get('pid') and metrics.get('process_started')==prior.get('process_started')
         and isinstance(metrics.get('players'),dict) and not metrics['players']
         and 0<=(now-_time(metrics.get('at'))).total_seconds()<=15,
         'Fresh empty-roster telemetry from the same actual JVM required')
    need(_time(prior['process_started'])<=_time(prior['at']),'Inspection cannot predate its actual process')
    stock=prior.get('native_stock',{});rows=stock.get('all27_native_snbt')
    need(stock.get('position')==[1313,68,-994] and isinstance(rows,list) and len(rows)==27
         and all(isinstance(row,str) and len(row)<=2048 for row in rows)
         and rows[3:6]==['','',''],'Actual all27-slot stock and genuinely empty hardware slots required')
    return path.relative_to(home).as_posix(),digest


def prepare(home,operation,output,*,expected_bridge_sha256,inspection_path=None,creative_authoring=False,now=None):
    need(operation in ('inspect','supply'),'Only fixed inspect/supply packets are supported')
    need(type(creative_authoring) is bool and creative_authoring==(operation=='supply'),
         'Explicit creative-authoring admission is required for supply only')
    need((inspection_path is not None)==(operation=='supply'),'Supply requires its genuine inspection; inspect takes none')
    home,world,candidate,bridge,pack,classes,backup,backup_raw_sha=environment(home,expected_bridge_sha256)
    now=now or datetime.now(timezone.utc)
    need(now.tzinfo is not None,'Actual timezone-aware request time required')
    packet=dict(format='awft-copper-stock-request:1',operation=operation,home=str(home),world=str(world),
                candidate=candidate,bridge=bridge,pack_sha256=pack,bridge_jar_sha256=expected_bridge_sha256,
                backup_id=backup['id'],backup_sha256=backup['sha256'],backup_receipt_sha256=backup_raw_sha,
                creative_authoring=creative_authoring,created=now.isoformat(),**classes)
    if operation=='supply':
        need(not os.path.lexists(world/LEDGER),'Existing fixed stock ledger forbids restock, partial replay or a nonce retry')
        relative,digest=inspection(home,world,inspection_path,candidate=candidate,bridge=bridge,pack=pack,bridge_sha=expected_bridge_sha256,
                                   classes=classes,backup_sha=backup_raw_sha,now=now)
        packet.update(inspection_path=relative,inspection_sha256=digest)
    raw=(json.dumps(packet,sort_keys=True,separators=(',',':'))+'\n').encode()
    need(len(raw)<=65536,'Closed bounded typed stock packet required')
    digest=sha(raw);destination=home/'dashboard/settlement'/('copper-stock-'+digest[:16])/'request.json'
    need(not os.path.lexists(destination.parent),'Existing immutable native stock bundle refuses automatic replay')
    output=Path(output).absolute()
    source_root=OUTPUT_ROOT.absolute()
    need(source_root.resolve()==source_root and not source_root.is_symlink() and not source_root.is_junction()
         and output.parent==source_root and not os.path.lexists(output),
         'New immediate owned .local source folder required; producer never publishes to native dashboard')
    reserve=guard(8*1024**2,0)
    manifest={'format':'awft-copper-stock-source-request:1','source_packet_sha256':digest,'source_packet':'request.json',
              'native_request_destination':str(destination),'typed_console_command':'awftcopperstock '+operation+' copper-stock-'+digest[:16]+' '+digest,
              'native_request_published':False,'native_command_executed':False,'native_actions':0,'world_writes':0,'storage_guard':reserve,
              'requires':'Master separately authorizes exact creative supply/write lease, copies packet with CREATE_NEW and runs typed command. Marker custody is not provenance by itself.'}
    metadata=(json.dumps(manifest,indent=2)+'\n').encode();need(len(metadata)<=16384,'Bounded source manifest required')
    output.parent.mkdir(exist_ok=True);output.mkdir()
    with (output/'request.json').open('xb') as stream:stream.write(raw)
    with (output/'manifest.json').open('xb') as stream:stream.write(metadata)
    return manifest|{'prepared':str(output),'source_packet':str(output/'request.json')}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation',choices=('inspect','supply'));parser.add_argument('--home',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True);parser.add_argument('--bridge-jar-sha256',required=True)
    parser.add_argument('--inspection',type=Path);parser.add_argument('--creative-authoring',action='store_true')
    args=parser.parse_args();print(json.dumps(prepare(args.home,args.operation,args.output,expected_bridge_sha256=args.bridge_jar_sha256,
          inspection_path=args.inspection,creative_authoring=args.creative_authoring),indent=2))
