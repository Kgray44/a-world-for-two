"""Synthetic temp-file packet gates; no native receipt or marker is written in H."""
from copy import deepcopy
from datetime import datetime,timezone,timedelta
import json
import os
from pathlib import Path
import tempfile
import subprocess
import unittest
from unittest.mock import patch
import zipfile

from control_room.common import UserError
from tools.transport_stock_request import CLASSES,LEDGER,prepare,sha


class StockRequestTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='awft-synthetic-stock-request-')
        self.root=Path(self.temp.name);self.staging=self.root/'staging/world-tests';self.home=self.staging/'SYNTHETIC'
        self.world=self.home/'world/RosewaterArtistic';self.world.mkdir(parents=True)
        for folder in ('server/mods','packwiz','dashboard/settlement'):(self.home/folder).mkdir(parents=True)
        self.output_root=self.root/'owned-repo/.local';self.output_root.mkdir(parents=True)
        self.patches=[patch('tools.transport_stock_request.STAGING_ROOT',self.staging),
                      patch('tools.transport_stock_request.OUTPUT_ROOT',self.output_root),
                      patch('tools.transport_stock_request.guard',return_value={'allowed':True,'synthetic_test':True})]
        for value in self.patches:value.start()
        self.now=datetime(2026,10,28,20,0,tzinfo=timezone.utc);self.pack='a'*64
        self.write('dashboard/artistic-owner.json',{'format':'awft-artistic-stage:1','home':str(self.home)})
        self.write('dashboard/settings.json',{'permanent_world':False,'port':25575})
        self.write('packwiz/active.json',{'version':'0.1.0-candidate.99','pack_sha256':self.pack})
        self.write('dashboard/settlement/backup-receipt.json',{'id':'20261028T191243Z-6ad3a8','sha256':'b'*64,'verified':True})
        self.jar=self.home/'server/mods/awft-control-bridge-0.6.99.jar';self.jar_fixture()
        self.inspect_path=self.home/'dashboard/settlement/copper-stock-result-00000000-0000-0000-0000-000000000001.json'
        self.prior={'format':'awft-native-copper-stock:1','operation':'inspect','status':'inspected actual starter; no stock authored',
                    'cleanup_passed':True,'lease_acquired':True,'lease_released':True,'cleanup_errors':[],
                    'world_mutated':False,'temporary_tickets_remaining':0,'pending_shared_chunk_futures':0,
                    'at':self.now.isoformat(),'world':str(self.world),'candidate':'0.1.0-candidate.99','bridge':'0.6.99',
                    'bridge_jar_sha256':self.jar_sha,'pack_sha256':self.pack,'artifact_class_sha256':self.classes,
                    'backup_receipt_sha256':sha((self.home/'dashboard/settlement/backup-receipt.json').read_bytes()),
                    'boot_id':'00000000-0000-0000-0000-000000000002','pid':1234,'process_started':'2026-10-28T19:00:00Z',
                    'native_stock':{'position':[1313,68,-994],'all27_native_snbt':['']*27}}
        self.prior['native_stock']['all27_native_snbt'][0]='{count:16,id:"minecraft:wheat"}'
        self.terminal(self.prior)
        self.metrics={'format':'awft-metrics:1','at':self.now.isoformat(),'pid':1234,'process_started':'2026-10-28T19:00:00Z','players':{}}
        self.write('dashboard/server-metrics.json',self.metrics)

    def tearDown(self):
        for value in reversed(self.patches):value.stop()
        self.temp.cleanup()

    def write(self,relative,value):
        path=self.home/relative;path.write_text(json.dumps(value,separators=(',',':')));return path

    def jar_fixture(self,skip=None):
        self.classes={}
        with zipfile.ZipFile(self.jar,'w') as archive:
            for key,name in CLASSES.items():
                if name==skip:continue
                raw=b'\xca\xfe\xba\xbeSYNTHETIC_FIXTURE_ONLY '+name.encode();self.classes[key]=sha(raw)
                archive.writestr('worldfortwo/bridge/'+name+'.class',raw)
        self.jar_sha=sha(self.jar.read_bytes())
        self.write('server/installed.json',{'pack_version':'0.1.0-candidate.99','pack_sha256':self.pack,'files':{self.jar.name:self.jar_sha}})

    def terminal(self,value):
        raw=json.dumps(value,separators=(',',':')).encode();self.inspect_path.write_bytes(raw)
        Path(str(self.inspect_path)+'.complete').write_bytes(sha(raw).encode())

    def prepare(self,operation='inspect',name='source-r1',**changes):
        kwargs={'expected_bridge_sha256':self.jar_sha,'now':self.now}
        if operation=='supply':kwargs.update(inspection_path=self.inspect_path,creative_authoring=True)
        kwargs.update(changes)
        return prepare(self.home,operation,self.output_root/name,**kwargs)

    def test_inspect_prepares_exact_packet_without_publishing_or_touching_home(self):
        before={p:p.read_bytes() for p in self.home.rglob('*') if p.is_file()}
        result=self.prepare();raw=Path(result['source_packet']).read_bytes();packet=json.loads(raw)
        self.assertEqual(sha(raw),result['source_packet_sha256']);self.assertEqual(packet['operation'],'inspect')
        self.assertFalse(packet['creative_authoring']);self.assertIn('created',packet)
        self.assertFalse(result['native_request_published']);self.assertFalse(result['native_command_executed'])
        self.assertFalse(Path(result['native_request_destination']).parent.exists())
        self.assertEqual(before,{p:p.read_bytes() for p in self.home.rglob('*') if p.is_file()})

    def test_supply_requires_explicit_authoring_and_genuine_same_jvm_inspection(self):
        with self.assertRaises(UserError):self.prepare('supply',creative_authoring=False)
        result=self.prepare('supply');packet=json.loads(Path(result['source_packet']).read_bytes())
        self.assertTrue(packet['creative_authoring']);self.assertEqual(packet['inspection_sha256'],sha(self.inspect_path.read_bytes()))
        self.assertEqual(packet['inspection_path'],self.inspect_path.relative_to(self.home).as_posix())

    def test_unknown_or_missing_deployed_adapter_and_wrong_jar_pin_refuse(self):
        with self.assertRaises(UserError):self.prepare(expected_bridge_sha256='0'*64)
        self.jar_fixture(skip='CopperWrenStockSupport')
        with self.assertRaises(UserError):self.prepare()

    def test_active_installed_pack_or_private_home_mismatch_refuses(self):
        self.write('packwiz/active.json',{'version':'0.1.0-candidate.100','pack_sha256':self.pack})
        with self.assertRaises(UserError):self.prepare()
        self.write('packwiz/active.json',{'version':'0.1.0-candidate.99','pack_sha256':self.pack})
        self.write('dashboard/settings.json',{'permanent_world':True,'port':25565})
        with self.assertRaises(UserError):self.prepare()

    def test_changed_current_backup_cannot_reuse_prior_native_inspection(self):
        self.write('dashboard/settlement/backup-receipt.json',{'id':'20261028T191243Z-6ad3a8','sha256':'c'*64,'verified':True})
        with self.assertRaises(UserError):self.prepare('supply')

    def test_inspection_stale_future_unclean_or_mutating_cannot_admit_supply(self):
        variants=[{'at':(self.now-timedelta(seconds=61)).isoformat()}, {'at':(self.now+timedelta(seconds=1)).isoformat()},
                  {'cleanup_passed':False},{'lease_acquired':False},{'lease_released':False},{'cleanup_errors':['failed']},
                  {'world_mutated':True},{'pack_sha256':'d'*64},{'error':'retained native failure'}]
        for changes in variants:
            with self.subTest(changes=changes):
                value=deepcopy(self.prior);value.update(changes);self.terminal(value)
                with self.assertRaises(UserError):self.prepare('supply')

    def test_other_or_stale_jvm_metrics_or_player_arrival_refuses(self):
        for changes in ({'pid':9999},{'process_started':'2026-10-28T19:30:00Z'},
                        {'at':(self.now-timedelta(seconds=16)).isoformat()},{'players':{'SYNTHETIC_PLAYER':{}}}):
            self.write('dashboard/server-metrics.json',self.metrics|changes)
            with self.assertRaises(UserError):self.prepare('supply')

    def test_marker_tamper_and_duplicate_json_keys_are_not_native_custody(self):
        Path(str(self.inspect_path)+'.complete').write_bytes(b'0'*64)
        with self.assertRaises(UserError):self.prepare('supply')
        raw=json.dumps(self.prior,separators=(',',':')).encode();raw=b'{"operation":"supply",'+raw[1:]
        self.inspect_path.write_bytes(raw);Path(str(self.inspect_path)+'.complete').write_bytes(sha(raw).encode())
        with self.assertRaises(UserError):self.prepare('supply')

    def test_partial_stock_ledger_cannot_be_bypassed_by_a_new_output_name(self):
        ledger=self.world/LEDGER;ledger.mkdir(parents=True);(ledger/'intent.json').write_text('{"SYNTHETIC":true}')
        for name in ('nonce-one','nonce-two'):
            with self.assertRaises(UserError):self.prepare('supply',name=name)

    def test_missing_occupied_or_wrong_position_inventory_refuses(self):
        for change in ('occupied','missing','wrong_position'):
            value=deepcopy(self.prior)
            if change=='occupied':value['native_stock']['all27_native_snbt'][4]='{id:"minecraft:diamond"}'
            elif change=='missing':value['native_stock']['all27_native_snbt'].pop()
            else:value['native_stock']['position']=[0,0,0]
            self.terminal(value)
            with self.assertRaises(UserError):self.prepare('supply')

    def test_copied_inspection_or_native_dashboard_output_is_not_allowed(self):
        copy=self.home/'dashboard'/self.inspect_path.name;copy.write_bytes(self.inspect_path.read_bytes())
        with self.assertRaises(UserError):self.prepare('supply',inspection_path=copy)
        with self.assertRaises(UserError):prepare(self.home,'inspect',self.home/'dashboard/settlement/forbidden',expected_bridge_sha256=self.jar_sha,now=self.now)

    def test_redirected_native_file_is_refused_without_following_it(self):
        owner=self.home/'dashboard/artistic-owner.json';outside=self.root/'outside-owner.json';outside.write_bytes(owner.read_bytes());owner.unlink()
        try:owner.symlink_to(outside)
        except OSError:self.skipTest('Host does not grant symbolic-link creation for this synthetic temp fixture')
        with self.assertRaises(UserError):self.prepare()

    @unittest.skipUnless(os.name=='nt','Windows junction policy fixture')
    def test_windows_junction_journal_is_refused(self):
        source=self.home/'dashboard';moved=self.root/'owned-junction-fixture'
        self.assertTrue(source.resolve().is_relative_to(self.root.resolve()));self.assertTrue(moved.parent==self.root)
        source.rename(moved)
        process=subprocess.run(['cmd','/d','/c','mklink','/J',str(source),str(moved)],capture_output=True,text=True,
                               timeout=5,creationflags=subprocess.CREATE_NO_WINDOW)
        if process.returncode:
            moved.rename(source);self.skipTest('Host denied a synthetic temp junction')
        try:
            self.assertTrue(source.is_junction());self.assertEqual(source.resolve(),moved.resolve())
            with self.assertRaises(UserError):self.prepare()
        finally:
            self.assertEqual(source.resolve(),moved.resolve());os.rmdir(source);moved.rename(source)

    def test_existing_source_output_and_existing_native_bundle_are_never_overwritten(self):
        result=self.prepare()
        with self.assertRaises(UserError):self.prepare()
        destination=Path(result['native_request_destination']);destination.parent.mkdir()
        destination.write_text('SYNTHETIC_EXISTING_IMMUTABLE_REQUEST')
        with self.assertRaises(UserError):self.prepare(name='different-output')


if __name__=='__main__':unittest.main()
