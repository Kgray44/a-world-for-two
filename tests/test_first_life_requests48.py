from copy import deepcopy
import datetime as dt
import unittest

from control_room.common import UserError
from tools.artistic_first_life_requests48 import validate_seed_proofs


class FirstLife48ProofTests(unittest.TestCase):
    def setUp(self):
        self.members=[{'uuid':str(n),'entity':'entity:'+str(n),'native_class':'native.'+str(n)} for n in range(8)]
        clean={'failures':0,'cleanup_required':False,'temporary_tickets_remaining':0,
               'pending_shared_chunk_futures':0,'finished':dt.datetime.now(dt.timezone.utc).isoformat()}
        self.verify={**clean,'operation':'verify','plan_sha256':'habitat','blocks':3242,
            'status':'verified actual block identities, orientation, block entities and supplied inventories'}
        self.inspect={**clean,'pending_shared_futures':0,'operation':'inspect','request_sha256':'request',
            'recipe_sha256':'recipe','members':8,'status':'native habitats inspected; no resident or ledger writes',
            'cleanup_passed':True,'spawned':0,'intents_written':0,'population_authorities_written':0,
            'world_or_ledger_write_attempted':False,'entity_add_attempted':False,'NoAI_or_ownership_writes':0,
            'observations':[{'uuid':r['uuid'],'type':r['entity'],'native_class':r['native_class'],
                'new_habitat_currently_admissible':True,'spawned':False} for r in self.members]}

    def check(self, verify=None, inspection=None):
        validate_seed_proofs(verify or self.verify,inspection or self.inspect,'request','recipe','habitat',self.members)

    def test_exact_complete_native_proofs_admit_binding_only(self):
        self.check()

    def test_schema_cleanliness_uses_real_native_futures_fields(self):
        inspect=deepcopy(self.inspect);del inspect['pending_shared_chunk_futures'];self.check(inspection=inspect)
        inspect['pending_shared_futures']=1
        with self.assertRaises(UserError):self.check(inspection=inspect)

    def test_no_inspection_admissibility_from_just_block_verification(self):
        for key,value in [('request_sha256','other'),('recipe_sha256','other'),('members',7),
                          ('spawned',1),('intents_written',1),('cleanup_passed',False),
                          ('entity_add_attempted',True),('NoAI_or_ownership_writes',1)]:
            with self.subTest(key=key):
                changed=deepcopy(self.inspect);changed[key]=value
                with self.assertRaises(UserError):self.check(inspection=changed)

    def test_missing_member_or_changed_native_class_refuses(self):
        for mode in ('missing','class'):
            changed=deepcopy(self.inspect)
            if mode=='missing':changed['observations'].pop()
            else:changed['observations'][0]['native_class']='fake.OwnerCat'
            with self.assertRaises(UserError):self.check(inspection=changed)

    def test_exact_full_field_and_freshness_required(self):
        for key,value in [('blocks',3241),('plan_sha256','another'),('temporary_tickets_remaining',1),
                          ('finished',(dt.datetime.now(dt.timezone.utc)-dt.timedelta(minutes=31)).isoformat())]:
            with self.subTest(key=key):
                changed=deepcopy(self.verify);changed[key]=value
                with self.assertRaises(UserError):self.check(verify=changed)


if __name__=='__main__':unittest.main()
