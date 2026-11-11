"""Derive exactly two installed-detector debits from complete native mill custody.

This is a read-only file/quantity audit, not proof that supplied files originated
in Minecraft. Master must authenticate their provenance and deployed artifact.
No native snapshot, ledger, item, marker or acceptance result is manufactured.
"""
from __future__ import annotations

from datetime import timedelta
import hashlib
import io
import json
from pathlib import Path
import re
import zipfile

from control_room.common import UserError

STAGING_ROOT = Path(r'D:\A World for Two\staging\world-tests')
ITEM = 'create_hypertube:redstone_detector_tube_attachment'
ATTACHMENT_CLASS = 'com.pedrorok.hypertube.core.smarttube.RedstoneDetectorAttachment'
STOCK = [1313,68,-994]
ENTRANCES = ([1331,71,-991], [1331,71,-943])
PLAN_SHA = 'ceeeabfc3ed1aee751074134edccc6de9ed3b0cf4308001203a9027e952a71af'
PARTIAL_SHA = 'e4f627a9baa367a267537504d017893f64537841a0d608eef5b1b8b4925bc239'
MANIFEST_SHA = 'f4f9bd4cd1d3bc4ff100cfe9ba417b591e7e8ede23bb1b4e3c03deb7f600d2f5'
SUCCESS = 'native resumed stationary commissioning passed; actual passenger trips and restart acceptance pending'
UUID = r'[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def document_sha(document):
    return sha(json.dumps(document,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode())


def _require(condition, message):
    if not condition:
        raise UserError(message)


def _regular(home, path, cap):
    path = Path(path).absolute()
    _require('..' not in path.parts, 'No parent traversal in native custody')
    _require(path.is_relative_to(home), 'Native evidence escaped the owned home')
    for part in (path,*path.parents):
        _require(not part.is_symlink() and not part.is_junction(), 'Linked or redirected native evidence refused')
        if part == home:
            break
    _require(path.resolve(strict=True) == path and path.is_file() and 0 < path.stat().st_size <= cap,
             'Canonical bounded regular native file required')
    with path.open('rb') as stream:
        raw = stream.read(cap+1)
    _require(len(raw) <= cap, 'Native file grew beyond its bound')
    return raw


def _json(raw):
    def unique(pairs):
        result = {}
        for key,value in pairs:
            _require(key not in result, 'Duplicate native JSON keys refused')
            result[key] = value
        return result
    try:
        value = json.loads(raw,object_pairs_hook=unique)
    except (ValueError,UnicodeError) as error:
        raise UserError('Malformed native JSON') from error
    _require(isinstance(value,dict), 'Native JSON object required')
    return value


def _terminal(home, path, family):
    path = Path(path).absolute()
    _require(path.parent == home/'dashboard/settlement' and re.fullmatch(family+'-result-'+UUID+r'\.json',path.name),
             'Canonical native terminal family/path required')
    raw = _regular(home,path,2*1024**2)
    marker = _regular(home,Path(str(path)+'.complete'),64)
    _require(marker == sha(raw).encode(), 'Exact native terminal completion marker required')
    return _json(raw),sha(raw)


def _ref(home, ref, cap=2*1024**2):
    _require(isinstance(ref,dict) and set(ref)=={'path','bytes','sha256'}, 'Exact native reference fields required')
    relative = Path(ref['path'])
    _require(not relative.is_absolute() and '\\' not in ref['path'] and ':' not in ref['path'], 'Owned home-relative reference required')
    raw = _regular(home,home/relative,cap)
    _require(type(ref['bytes']) is int and len(raw)==ref['bytes'] and sha(raw)==ref['sha256'], 'Referenced native bytes differ')
    return _json(raw),home/relative,sha(raw)


def plain_stack(snbt):
    """Only plain native id/count ItemStack SNBT; unfamiliar components refuse."""
    _require(isinstance(snbt,str) and len(snbt)<=2048, 'Bounded native stack SNBT required')
    if snbt == '':
        return None
    _require(snbt.startswith('{') and snbt.endswith('}'), 'Plain ItemStack compound required')
    fields = {}
    for field in snbt[1:-1].split(','):
        match = re.fullmatch(r'\s*(id|count)\s*:\s*(.*?)\s*',field)
        _require(match is not None and match[1] not in fields, 'Unfamiliar or duplicate ItemStack SNBT; separate contract required')
        fields[match[1]] = match[2]
    _require('id' in fields and re.fullmatch(r'"[a-z0-9_.-]+:[a-z0-9_./-]+"',fields['id']) is not None,
             'Plain native item ID required')
    count = fields.get('count','1')
    _require(re.fullmatch(r'[1-9][0-9]{0,2}',count) is not None, 'Plain positive native count required')
    return fields['id'][1:-1],int(count)


def _stock(snapshot):
    _require(isinstance(snapshot,dict) and set(snapshot)=={'position','slots'} and snapshot['position']==STOCK,
             'Exact native starter snapshot required')
    rows = snapshot['slots']
    _require(isinstance(rows,list) and len(rows)==27, 'All27 native starter slots required')
    result = []
    for n,row in enumerate(rows):
        _require(isinstance(row,dict) and set(row)=={'slot','native_stack_snbt'} and type(row['slot']) is int and row['slot']==n,
                 'Ordered unique native starter slots required')
        result.append(plain_stack(row['native_stack_snbt']))
    return result


def _observed_stock(observation):
    stores = [row for row in observation['cargo']['stores'] if row.get('role')=='starter']
    _require(len(stores)==1 and stores[0].get('position')==STOCK and stores[0].get('slots')==27,
             'Actual complete observed27-slot starter inventory required')
    result = [None]*27
    for row in stores[0]['items']:
        slot = row['slot']
        _require(type(slot) is int and 0<=slot<27 and result[slot] is None and row.get('plain') is True and row.get('components')=='{}',
                 'Only unambiguous plain native starter stacks are qualified')
        result[slot] = row['item'],row['count']
    return result


def _decrease(stock, slot, item, count):
    _require(type(slot) is int and 0<=slot<27 and stock[slot] is not None
             and stock[slot][0]==item and stock[slot][1]>=count, 'Exact real debit slot/item/count differs')
    result = list(stock)
    remaining = stock[slot][1]-count
    result[slot] = (item,remaining) if remaining else None
    return result


def derive_equipment_debits(home,before_path,after_path,terminal_path,*,expected_bridge_sha256):
    """Return a separately bound equipment witness; never alter input observations."""
    from tools.transport_commission import _context, _inventory, _time
    home = Path(home).absolute()
    _require(home.parent==STAGING_ROOT.resolve() and home.resolve(strict=True)==home,
             'Exact owned private construction home ancestry required')
    world = home/'world/RosewaterArtistic'
    _require(world.resolve(strict=True)==world, 'Canonical real construction world required')
    before,before_sha = _terminal(home,before_path,'transport-observation')
    after,after_sha = _terminal(home,after_path,'transport-observation')
    _context(before,after)
    _inventory(before);_inventory(after)
    _require(before['world']==after['world']==str(world), 'Actual observation world differs from owned ledger')
    _require(_time(before['process_started'])<=_time(before['at']), 'Actual observation cannot precede its JVM start')
    terminal,terminal_sha = _terminal(home,terminal_path,'artistic-mill')
    _require(terminal.get('operation')=='resume' and terminal.get('status')==SUCCESS and 'error' not in terminal
             and terminal.get('cleanup_passed') is True and terminal.get('remaining_owned_tickets')==0
             and terminal.get('cleanup_errors')==[] and terminal.get('actual_wheat_feed_performed') is True
             and terminal.get('actual_mill_dispatch_and_press_passed') is True and terminal.get('native_entrances_manual_sneak_mode') is True
             and terminal.get('actual_test_input')=={'wheat':16,'iron_ingot':1}, 'Successful clean genuine mill resume required')
    _require(terminal.get('candidate')==before['candidate'] and terminal.get('bridge')==before['bridge'],
             'Actual resume candidate/bridge differs from observations')
    started,finished = _time(terminal['started']),_time(terminal['finished'])
    _require(_time(before['at'])<=started<finished<=_time(after['at']), 'Observations must span the ordered completed native resume')
    request_sha = terminal.get('request_sha256','')
    _require(re.fullmatch('[a-f0-9]{64}',request_sha) is not None, 'Actual native request digest required')
    request_path = home/'dashboard/settlement'/('mill-resume-'+request_sha[:16])/'request.json'
    request_raw = _regular(home,request_path,128*1024)
    _require(sha(request_raw)==request_sha, 'Canonical actual resume request bytes differ')
    request = _json(request_raw)
    _require(request.get('format')=='awft-artistic-mill-resume:1' and request.get('intended_operation')=='resume'
             and request.get('candidate_version')==before['candidate'] and request.get('bridge_version')==before['bridge'],
             'Actual native resume request identity differs')
    _require(re.fullmatch('[a-f0-9]{64}',expected_bridge_sha256) is not None
             and request.get('bridge_jar_sha256')==expected_bridge_sha256, 'Master-deployed exact bridge JAR digest required')
    jars = list((home/'server/mods').glob('awft-control-bridge-*.jar'))
    _require(len(jars)==1 and jars[0].name=='awft-control-bridge-'+before['bridge']+'.jar', 'Exact single installed native bridge required')
    jar_raw = _regular(home,jars[0],4*1024**2)
    _require(sha(jar_raw)==expected_bridge_sha256, 'Actual installed native bridge bytes changed')
    class_hashes = {}
    with zipfile.ZipFile(io.BytesIO(jar_raw)) as jar:
        for name in ('ArtisticEngineeringSupport','NativeMillResumeAttachments','TransportObservationSupport'):
            member='worldfortwo/bridge/'+name+'.class'
            _require(0<jar.getinfo(member).file_size<=256*1024, 'Bounded actual native helper class required')
            class_hashes[name]=sha(jar.read(member))
    for key,name in (('native_class_sha256','ArtisticEngineeringSupport'),('native_attachment_class_sha256','NativeMillResumeAttachments')):
        _require(terminal.get(key)==request.get(key)==class_hashes[name], 'Terminal/request/installed native class identity differs')
        for observation in (before,after):
            _require(key not in observation or observation[key]==class_hashes[name], 'Optional observed native class hash differs')
    for observation in (before,after):
        _require('bridge_jar_sha256' not in observation or observation['bridge_jar_sha256']==expected_bridge_sha256,
                 'Optional observed native JAR identity differs')
    plan,_,_ = _ref(home,request['plan'])
    _require(plan.get('world_path')==str(world), 'Request source world differs')
    contract = sha(('awft:mill-resume:1\n'+str(world)+'\n'+PLAN_SHA+'\n'+PARTIAL_SHA+'\n'+MANIFEST_SHA+'\n').encode())
    _require(terminal.get('resume_contract_sha256')==contract, 'Stable native equipment ledger contract differs')
    inspection,inspection_path,_ = _ref(home,request['native_inventory_inspection'],512*1024)
    inspected,_ = _terminal(home,inspection_path,'artistic-mill')
    _require(inspection==inspected and inspection.get('operation')=='inspect' and 'error' not in inspection
             and inspection.get('cleanup_passed') is True and inspection.get('remaining_owned_tickets')==0
             and inspection.get('candidate')==before['candidate'] and inspection.get('bridge')==before['bridge']
             and inspection.get('resume_contract_sha256')==contract and started-timedelta(seconds=1200)<=_time(inspection['finished'])<=started,
             'Actual prior clean inventory inspection required')
    for key in ('native_class_sha256','native_attachment_class_sha256'):
        _require(inspection.get(key)==terminal[key], 'Prior inventory inspection class differs')
    initial = _stock(terminal['native_resume_stock'])
    _require(initial==_observed_stock(before) and inspection.get('native_resume_stock')==terminal['native_resume_stock'],
             'Observed/native inspected initial all-slot custody differs')
    readbacks=terminal.get('native_manual_input_readback',[])
    _require(len(readbacks)==2, 'Both actual manual-mode readbacks required')
    for n,row in enumerate(readbacks):
        _require(row.get('position')==ENTRANCES[n] and row.get('west_detector') is True and row.get('native_attachment_id')=='redstone_input'
                 and row.get('native_input_faces')==['west'] and row.get('lever_powered') is True
                 and row.get('native_powered_memory') is True and row.get('native_manual_locked') is True
                 and type(row.get('west_signal')) is int and 0<row['west_signal']<=15 and row.get('native_output_power')==0,
                 'Actual WEST input/lock/manual state differs')
    ledger = world/'data/awft-mill-resume'/contract
    names={f'west-{n}.{stage}.json' for n in (0,1) for stage in ('intent','debit','admitted')}
    names.update(stage+'.'+kind+'.json' for stage in ('feed','assembly') for kind in ('intent','completed'))
    _require(ledger.is_dir() and {p.name for p in ledger.iterdir()}==names, 'Complete exact once-only equipment/feed/assembly ledger required')
    records,refs = {},{}
    for name in sorted(names):
        raw = _regular(home,ledger/name,65536)
        _require(raw.endswith(b'\n') and not raw.endswith(b'\n\n') and b'\r' not in raw, 'Exact native UTF8/LF durable JSON required')
        records[name]=_json(raw[:-1]);refs[name]=sha(raw[:-1])
    expected,latest,installations = initial,started,[]
    for n in (0,1):
        intent,debit,done=(records[f'west-{n}.{stage}.json'] for stage in ('intent','debit','admitted'))
        _require(intent.get('format')=='awft-mill-real-attachment-intent:1' and intent.get('contract_sha256')==contract
                 and type(intent.get('index')) is int and intent['index']==n and intent.get('entrance')==ENTRANCES[n]
                 and intent.get('face')=='west' and intent.get('item')==ITEM and type(intent.get('amount')) is int and intent['amount']==1,
                 'Exact native one-item WEST installation intent required')
        _require(_stock(intent['before_stock'])==expected and plain_stack(intent['expected_removed_native_snbt'])==(ITEM,1),
                 'Actual native pre-debit inventory/removed stack differs')
        expected = _decrease(expected,intent['slot'],ITEM,1)
        _require(_stock(intent['expected_after_stock'])==expected and debit.get('intent_sha256')==refs[f'west-{n}.intent.json']
                 and debit.get('actual_removed_native_snbt')==intent['expected_removed_native_snbt']
                 and debit.get('after_stock')==intent['expected_after_stock'], 'Real debit/readback/intent byte chain differs')
        _require(done.get('debit_sha256')==refs[f'west-{n}.debit.json'] and done.get('native_attachment_id')=='redstone_input'
                 and done.get('native_attachment_class')==ATTACHMENT_CLASS and latest<=_time(done['finished'])<=finished,
                 'Actual admitted attachment class/debit chain/chronology differs')
        latest=_time(done['finished'])
        installations.append({'entrance':ENTRANCES[n],'face':'west','item':ITEM,'amount':1,'slot':intent['slot']})
    feed,completed = records['feed.intent.json'],records['feed.completed.json']
    _require(feed.get('stage')=='feed' and _stock(feed['actual_stock_before'])==expected and latest<=_time(feed['started']),
             'Feed must follow both actual installed-equipment debits')
    wheat=[n for n,value in enumerate(expected) if value and value==('minecraft:wheat',16)]
    iron=[n for n,value in enumerate(expected) if value and value[0]=='minecraft:iron_ingot']
    _require(len(wheat)==1 and iron and sum(value[1] for value in expected if value and value[0]=='minecraft:wheat')==16,
             'Original actual16-wheat feed and iron stock required')
    expected=_decrease(_decrease(expected,wheat[0],'minecraft:wheat',16),iron[-1],'minecraft:iron_ingot',1)
    _require(_stock(feed['expected_stock_after'])==expected and completed.get('stage')=='feed'
             and completed.get('native_callback_returned') is True and _time(feed['started'])<=_time(completed['finished'])<=finished,
             'Genuine native feed/debit/completion differs')
    assembly,assembled=records['assembly.intent.json'],records['assembly.completed.json']
    _require(assembly.get('stage')=='assembly' and assembled.get('stage')=='assembly' and assembled.get('native_callback_returned') is True
             and _stock(assembly['actual_stock_before'])==_stock(assembly['expected_stock_after'])==expected
             and _time(completed['finished'])<=_time(assembly['started'])<=_time(assembled['finished'])<=finished
             and expected==_observed_stock(after), 'Final stock/assembly chronology does not preserve the genuine equipment and recipe debits')
    return {'format':'awft-derived-equipment-debits:1','equipment_debits':{ITEM:2},'installations':installations,
            'before_sha256':before_sha,'after_sha256':after_sha,'before_document_sha256':document_sha(before),'after_document_sha256':document_sha(after),
            'terminal_sha256':terminal_sha,'request_sha256':request_sha,'resume_contract_sha256':contract,
            'bridge_jar_sha256':expected_bridge_sha256,'actual_class_sha256':class_hashes,'durable_record_sha256_without_lf':refs,
            'world':str(world),'candidate':before['candidate'],'bridge':before['bridge'],
            'process_identity':{key:before[key] for key in ('pid','process_started','boot_id')},
            'scope':'Derived equipment debit custody only. Master authenticates native provenance/deployed artifact and exclusive runtime chronology; this does not prove travel, general loss-free RNG output, multiplayer or acceptance.',
            'native_actions':0,'world_writes':0,'input_observations_modified':False}
