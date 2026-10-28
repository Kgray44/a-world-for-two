"""Synthetic receipt boundaries only; no native receipt or authority is created."""
from copy import deepcopy
from datetime import datetime,timedelta,timezone
import unittest
from control_room.common import UserError
from tools.artistic_bridge_topside_admission import check_inspection
from tools.artistic_bridge_topside_custody import BOXES


class BridgeTopsideAdmissionReceiptTests(unittest.TestCase):
    def setUp(self):
        self.now=datetime.now(timezone.utc);self.sha='a'*64
        self.request={'candidate':'0.1.0-candidate.47','bridge':'0.6.33'}
        self.checkpoint={'id':'synthetic-checkpoint','sha256':'b'*64}
        self.census={'glues':[{'uuid':name,'entity_id':'create:super_glue','bounds':list(box),
            'canonical_nbt':[10,{'fixture':[3,1]}],'canonical_nbt_sha256':'c'*64}for name,box in BOXES.items()]}
        glues=[{'uuid':r['uuid'],'native_class':'com.simibubi.create.content.contraptions.glue.SuperGlueEntity',
                'bounds':r['bounds'],'canonical_nbt':r['canonical_nbt'],'canonical_nbt_sha256':r['canonical_nbt_sha256']}for r in self.census['glues']]
        closed=[{'bearing':[1199,70,z],'angle':0,'running':False,'sequencer_idle':True,'input_rpm':8,'wheel_rpm':-8}for z in(-1172,-1116)]
        self.before=(self.now-timedelta(seconds=3)).isoformat()
        self.proof={'operation':'inspect-retained-current-glue','native_custody_passed':True,
            'new_glue_or_motion_authority':False,'no_native_geometry_entity_inventory_glue_control_writes':True,
            'request_sha256':self.sha,'candidate':self.request['candidate'],'bridge':self.request['bridge'],
            'checkpoint_id':self.checkpoint['id'],'checkpoint_sha256':self.checkpoint['sha256'],
            'strict_preimage_states':106,'cleanup_required':False,'ticket_release_failures':[],
            'temporary_tickets_remaining':0,'pending_shared_chunk_futures':0,
            'started':(self.now-timedelta(seconds=2)).isoformat(),'finished':(self.now-timedelta(seconds=1)).isoformat(),
            'glues':glues,'loaded_glue_uuids':list(BOXES),'closed_before':closed,'closed_after':deepcopy(closed)}
    def check(self,value):
        return check_inspection(value,self.request,self.sha,self.census,self.checkpoint,self.before,now=self.now)
    def test_actual_schema_has_no_invented_failures_or_cleanup_passed_requirement(self):
        self.assertNotIn('failures',self.proof);self.assertNotIn('cleanup_passed',self.proof)
        self.assertIs(self.check(self.proof),self.proof)
    def test_failed_unpublished_or_pending_receipt_refuses(self):
        for key,value in (('native_custody_passed',False),('cleanup_required',True),('pending_shared_chunk_futures',1),
                          ('journal_error','blocked'),('receipt_blocked',True),('new_glue_or_motion_authority',True)):
            row=deepcopy(self.proof);row[key]=value
            with self.subTest(key=key),self.assertRaises(UserError):self.check(row)
    def test_changed_uuid_aabb_or_complete_typed_NBT_refuses(self):
        for key,value in (('uuid','foreign'),('bounds',[0]*6),('canonical_nbt',[10,{'fixture':[4,1]}])):
            row=deepcopy(self.proof);row['glues'][0][key]=value
            with self.subTest(key=key),self.assertRaises(UserError):self.check(row)
    def test_exact_current_request_and_checkpoint_required(self):
        for key in ('request_sha256','checkpoint_sha256','candidate','bridge'):
            row=deepcopy(self.proof);row[key]='different'
            with self.subTest(key=key),self.assertRaises(UserError):self.check(row)
    def test_closed_native_readiness_must_survive_before_and_after(self):
        for key,value in (('running',True),('angle',55),('sequencer_idle',False),('input_rpm',0)):
            row=deepcopy(self.proof);row['closed_after'][0][key]=value
            with self.subTest(key=key),self.assertRaises(UserError):self.check(row)
    def test_fresh_ordered_native_timestamps_required(self):
        row=deepcopy(self.proof);row['finished']=(self.now-timedelta(minutes=10)).isoformat()
        with self.assertRaises(UserError):self.check(row)
        row=deepcopy(self.proof);row['started']=(self.now-timedelta(seconds=4)).isoformat()
        with self.assertRaises(UserError):self.check(row)
