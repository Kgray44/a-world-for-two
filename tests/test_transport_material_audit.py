"""Synthetic file-custody fixtures only; never native material/gameplay proof."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from control_room.common import UserError
from tests.test_transport_commission import item,observation,processed,store
from tools.transport_material_audit import (
    ATTACHMENT_CLASS,ENTRANCES,ITEM,MANIFEST_SHA,PARTIAL_SHA,PLAN_SHA,STOCK,SUCCESS,
    derive_equipment_debits,plain_stack,sha,
)
from tools.transport_commission import reconcile_logistics


def encoded(value):
    return json.dumps(value,separators=(',',':')).encode()


def stock(values):
    def snbt(value):
        if value is None:return ''
        name,count=value
        return '{'+('count:'+str(count)+',' if count!=1 else '')+'id:"'+name+'"}'
    return {'position':STOCK,'slots':[{'slot':n,'native_stack_snbt':snbt(value)}for n,value in enumerate(values)]}


class MaterialAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='awft-synthetic-materials-')
        self.root=Path(self.temp.name)/'staging/world-tests';self.home=self.root/'fixture'
        self.world=self.home/'world/RosewaterArtistic';self.world.mkdir(parents=True)
        self.patch=patch('tools.transport_material_audit.STAGING_ROOT',self.root);self.patch.start()
        self.dashboard=self.home/'dashboard/settlement';self.dashboard.mkdir(parents=True)
        mods=self.home/'server/mods';mods.mkdir(parents=True)
        self.jar=mods/'awft-control-bridge-0.6.37.jar'
        self.classes={name:('SYNTHETIC '+name).encode()for name in ('ArtisticEngineeringSupport','NativeMillResumeAttachments','TransportObservationSupport')}
        with zipfile.ZipFile(self.jar,'w')as archive:
            for name,raw in self.classes.items():archive.writestr('worldfortwo/bridge/'+name+'.class',raw)
        self.jar_sha=sha(self.jar.read_bytes())
        self.identity={'native_class_sha256':sha(self.classes['ArtisticEngineeringSupport']),
                       'native_attachment_class_sha256':sha(self.classes['NativeMillResumeAttachments'])}
        self.initial=[None]*27;self.initial[:4]=[('minecraft:wheat',16),('minecraft:iron_ingot',4),('create:wrench',1),(ITEM,2)]
        self.contract=sha(('awft:mill-resume:1\n'+str(self.world)+'\n'+PLAN_SHA+'\n'+PARTIAL_SHA+'\n'+MANIFEST_SHA+'\n').encode())
        self.ledger=self.world/'data/awft-mill-resume'/self.contract;self.ledger.mkdir(parents=True)
        expected=list(self.initial)
        self.records={}
        for n in (0,1):
            after=list(expected);after[3]=(ITEM,1) if n==0 else None
            intent={'format':'awft-mill-real-attachment-intent:1','contract_sha256':self.contract,'index':n,
                    'item':ITEM,'amount':1,'slot':3,'expected_removed_native_snbt':stock([(ITEM,1)]+[None]*26)['slots'][0]['native_stack_snbt'],
                    'entrance':ENTRANCES[n],'face':'west','before_stock':stock(expected),'expected_after_stock':stock(after)}
            self.durable(f'west-{n}.intent.json',intent)
            debit={'intent_sha256':sha(encoded(intent)),'actual_removed_native_snbt':intent['expected_removed_native_snbt'],'after_stock':stock(after)}
            self.durable(f'west-{n}.debit.json',debit)
            done={'debit_sha256':sha(encoded(debit)),'native_attachment_id':'redstone_input','native_attachment_class':ATTACHMENT_CLASS,
                  'finished':f'2026-10-28T18:00:0{n+2}Z'}
            self.durable(f'west-{n}.admitted.json',done);expected=after
        fed=list(expected);fed[0]=None;fed[1]=('minecraft:iron_ingot',3)
        self.durable('feed.intent.json',{'stage':'feed','started':'2026-10-28T18:00:10Z','actual_stock_before':stock(expected),'expected_stock_after':stock(fed)})
        self.durable('feed.completed.json',{'stage':'feed','finished':'2026-10-28T18:00:11Z','native_callback_returned':True})
        self.durable('assembly.intent.json',{'stage':'assembly','started':'2026-10-28T18:00:40Z','actual_stock_before':stock(fed),'expected_stock_after':stock(fed)})
        self.durable('assembly.completed.json',{'stage':'assembly','finished':'2026-10-28T18:00:41Z','native_callback_returned':True})
        before=observation();after=processed()
        for snapshot in (before,after):
            snapshot.update(world=str(self.world),candidate='0.1.0-candidate.51',bridge='0.6.37')
            store(snapshot,'starter').update(position=STOCK,slots=27)
        store(before,'starter')['items']=[item('minecraft:wheat',16),item('minecraft:iron_ingot',4,1),item('create:wrench',1,2),item(ITEM,2,3)]
        store(after,'starter')['items']=[item('minecraft:iron_ingot',3,1),item('create:wrench',1,2)]
        self.before=self.native('transport-observation',1,before);self.after=self.native('transport-observation',2,after)
        inspection=dict(self.identity,operation='inspect',cleanup_passed=True,remaining_owned_tickets=0,
                        candidate=before['candidate'],bridge=before['bridge'],resume_contract_sha256=self.contract,
                        finished='2026-10-28T17:59:59Z',native_resume_stock=stock(self.initial))
        inspection_path=self.native('artistic-mill',3,inspection)
        plan_path=self.home/'staging/fixture-source/plan.json';plan_path.parent.mkdir(parents=True);plan_path.write_bytes(encoded({'world_path':str(self.world)}))
        request=dict(self.identity,format='awft-artistic-mill-resume:1',intended_operation='resume',
                     candidate_version=before['candidate'],bridge_version=before['bridge'],bridge_jar_sha256=self.jar_sha,
                     plan=self.ref(plan_path),native_inventory_inspection=self.ref(inspection_path))
        request_raw=encoded(request);request_sha=sha(request_raw)
        request_path=self.dashboard/('mill-resume-'+request_sha[:16])/'request.json';request_path.parent.mkdir();request_path.write_bytes(request_raw)
        manual=[{'position':p,'west_detector':True,'native_attachment_id':'redstone_input','native_input_faces':['west'],
                 'west_signal':15,'lever_powered':True,'native_powered_memory':True,'native_manual_locked':True,'native_output_power':0}for p in ENTRANCES]
        terminal=dict(self.identity,operation='resume',status=SUCCESS,cleanup_passed=True,remaining_owned_tickets=0,cleanup_errors=[],
                      actual_wheat_feed_performed=True,actual_mill_dispatch_and_press_passed=True,native_entrances_manual_sneak_mode=True,
                      actual_test_input={'wheat':16,'iron_ingot':1},candidate=before['candidate'],bridge=before['bridge'],
                      started='2026-10-28T18:00:01Z',finished='2026-10-28T18:00:50Z',request_sha256=request_sha,
                      resume_contract_sha256=self.contract,native_resume_stock=stock(self.initial),native_manual_input_readback=manual)
        self.terminal=self.native('artistic-mill',4,terminal)

    def tearDown(self):
        self.patch.stop();self.temp.cleanup()

    def durable(self,name,value):
        self.records[name]=deepcopy(value);(self.ledger/name).write_bytes(encoded(value)+b'\n')

    def native(self,family,index,value):
        path=self.dashboard/f'{family}-result-00000000-0000-0000-0000-{index:012x}.json'
        raw=encoded(value);path.write_bytes(raw);Path(str(path)+'.complete').write_bytes(sha(raw).encode());return path

    def ref(self,path):
        raw=path.read_bytes();return {'path':path.relative_to(self.home).as_posix(),'bytes':len(raw),'sha256':sha(raw)}

    def audit(self):
        return derive_equipment_debits(self.home,self.before,self.after,self.terminal,expected_bridge_sha256=self.jar_sha)

    def test_derives_only_two_equipment_debits_without_editing_native_files(self):
        prior={p:p.read_bytes()for p in (self.before,self.after,self.terminal,*self.ledger.iterdir())}
        witness=self.audit()
        self.assertEqual(witness['equipment_debits'],{ITEM:2});self.assertEqual(len(witness['installations']),2)
        self.assertEqual(witness['native_actions'],0);self.assertFalse(witness['input_observations_modified'])
        self.assertEqual(len(witness['durable_record_sha256_without_lf']),10)
        self.assertEqual(prior,{p:p.read_bytes()for p in prior})

    def test_exact_installed_equipment_explains_loss_without_weakening_recipe_audit(self):
        before=json.loads(self.before.read_bytes());after=json.loads(self.after.read_bytes())
        self.assertFalse(reconcile_logistics(before,after)['passed'])
        witness=self.audit()
        result=reconcile_logistics(before,after,equipment_witness=witness)
        self.assertTrue(result['passed']);self.assertEqual(result['actual_item_deltas'][ITEM],-2)
        after['cargo']['stores'][0]['items'].append(item('minecraft:diamond',1,8))
        with self.assertRaisesRegex(UserError,'exact native observations'):
            reconcile_logistics(before,after,equipment_witness=witness)

    def test_witness_cannot_explain_a_different_item_or_a_missing_equipment_debit(self):
        before=json.loads(self.before.read_bytes());after=json.loads(self.after.read_bytes())
        witness=self.audit();witness['equipment_debits']={'minecraft:diamond':2}
        with self.assertRaises(UserError):reconcile_logistics(before,after,equipment_witness=witness)
        store(after,'starter')['items'].append(item(ITEM,2,3))
        self.native('transport-observation',2,after)
        with self.assertRaises(UserError):self.audit()

    def test_plain_snbt_default_count_and_components_boundaries(self):
        self.assertEqual(plain_stack('{id:"minecraft:wheat"}'),('minecraft:wheat',1))
        self.assertEqual(plain_stack('{count:16,id:"minecraft:wheat"}'),('minecraft:wheat',16))
        for bad in ('{id:"minecraft:wheat",components:{}}','{count:1b,id:"minecraft:wheat"}',
                    '{count:0,id:"minecraft:wheat"}','{id:"minecraft:wheat",id:"minecraft:diamond"}'):
            with self.assertRaises(UserError):plain_stack(bad)

    def test_missing_or_unexpected_durable_record_refuses_partial_recovery(self):
        path=self.ledger/'feed.completed.json';raw=path.read_bytes();path.unlink()
        with self.assertRaises(UserError):self.audit()
        path.write_bytes(raw);(self.ledger/'foreign.intent.json').write_bytes(b'{}\n')
        with self.assertRaises(UserError):self.audit()

    def test_raw_json_hash_chain_is_not_recomputed_from_a_lossy_parse(self):
        path=self.ledger/'west-0.intent.json'
        path.write_bytes(json.dumps(self.records[path.name],indent=2).encode()+b'\n')
        with self.assertRaisesRegex(UserError,'byte chain'):self.audit()

    def test_unrelated_inventory_change_and_wrong_attachment_item_refuse(self):
        intent=deepcopy(self.records['west-0.intent.json']);intent['expected_after_stock']['slots'][2]['native_stack_snbt']='{count:2,id:"create:wrench"}'
        self.durable('west-0.intent.json',intent)
        with self.assertRaises(UserError):self.audit()
        intent['item']='minecraft:diamond';self.durable('west-0.intent.json',intent)
        with self.assertRaises(UserError):self.audit()

    def test_wrong_manual_mode_or_feed_chronology_refuses(self):
        terminal=json.loads(self.terminal.read_bytes());terminal['native_manual_input_readback'][0]['native_manual_locked']=False
        self.native('artistic-mill',4,terminal)
        with self.assertRaises(UserError):self.audit()
        terminal['native_manual_input_readback'][0]['native_manual_locked']=True;self.native('artistic-mill',4,terminal)
        feed=deepcopy(self.records['feed.intent.json']);feed['started']='2026-10-28T18:00:01Z';self.durable('feed.intent.json',feed)
        with self.assertRaises(UserError):self.audit()

    def test_observation_marker_or_actual_deployed_jar_change_refuses(self):
        marker=Path(str(self.before)+'.complete');prior=marker.read_bytes();marker.write_bytes(b'0'*64)
        with self.assertRaises(UserError):self.audit()
        marker.write_bytes(prior);self.jar.write_bytes(self.jar.read_bytes()+b'changed')
        with self.assertRaises(UserError):self.audit()

    def test_unpublished_hash_fields_are_optional_but_if_present_must_match(self):
        before=json.loads(self.before.read_bytes());before['native_attachment_class_sha256']='0'*64
        self.native('transport-observation',1,before)
        with self.assertRaises(UserError):self.audit()

    def test_success_label_cleanup_and_spanning_jvm_identity_are_mandatory(self):
        terminal=json.loads(self.terminal.read_bytes());terminal['cleanup_passed']=False;self.native('artistic-mill',4,terminal)
        with self.assertRaises(UserError):self.audit()
        terminal['cleanup_passed']=True;self.native('artistic-mill',4,terminal)
        after=json.loads(self.after.read_bytes());after['pid']=9999;self.native('transport-observation',2,after)
        with self.assertRaises(UserError):self.audit()

    def test_a_copied_terminal_outside_the_native_dashboard_is_not_canonical(self):
        copied=self.home/'staging'/self.terminal.name;copied.parent.mkdir(exist_ok=True);copied.write_bytes(self.terminal.read_bytes())
        Path(str(copied)+'.complete').write_bytes(sha(copied.read_bytes()).encode())
        with self.assertRaises(UserError):derive_equipment_debits(self.home,self.before,self.after,copied,expected_bridge_sha256=self.jar_sha)


if __name__=='__main__':unittest.main()
