"""Light pure admission fixtures. No JVM, game, native commands or MCA reader."""
import copy
from datetime import datetime,timezone,timedelta
import unittest
from contract import (qualify_partial,qualify_preimage,require_resume_stock,composite,COUNT)
from prepare import current_proof

def plan(cells):
    palette=sorted(set(cells.values()));return {'world_path':'private-fixture','seed':'fixture',
        'palette':palette,'blocks':[[*p,palette.index(v)] for p,v in cells.items()], 'commands':[],'block_entities':[]}

def field():
    fillers=[(1331,71,z) for n in range(6) for z in range(-990+n*8,-983+n*8)]
    expected={p:'minecraft:air' for p in fillers};expected.update({(x,73,-1001):'minecraft:air' for x in range(1306,1309)})
    expected[1311,72,-1000]='minecraft:oak_stairs[facing=east,half=bottom]'
    expected[1331,71,-991]='create_hypertube:hypertube_entrance[facing=south,locked=false,powered=false,waterlogged=false]'
    expected[1331,71,-943]='create_hypertube:hypertube_entrance[facing=north,locked=false,powered=false,waterlogged=false]'
    current=expected.copy();current.update({p:'create_hypertube:tube_path' for p in fillers});current.update({(x,73,-1001):'minecraft:water[level=0]' for x in range(1306,1309)})
    return expected,current,{'systems':{'hypertube':{'native_collision_cells':[list(p) for p in fillers]}}}

def partial():
    return {'phase':'WAIT_MODE','actual_wheat_feed_performed':False,'train_created':False,'cleanup_passed':True,'remaining_owned_tickets':0,
        'native_tube_links':[{'uuid':'fixture-'+str(n),'from':[1331,71,-991+n*8],'to':[1331,71,-983+n*8],'native_collision_cells':7,'native_filler_owner_and_shape_verified':True,'native_distance':8.0} for n in range(6)]}

def inspection():
    return {'operation':'inspect','cleanup_passed':True,'remaining_owned_tickets':0,'missing_owned_detectors':2,'actual_detector_stock':2,'actual_wheat_stock':16,'actual_single_16_wheat_stack':True,'actual_iron_stock':4,
        'native_resume_stock':{'position':[1313,68,-994],'slots':[{'slot':n,'native_stack_snbt':'fixture'} for n in range(27)]}}

class Admission(unittest.TestCase):
    def test_retained_native_field_is_recognized_without_replay(self):
        a,b,m=field();self.assertEqual(qualify_preimage(plan(a),plan(b),m)['retained_filler_cells'],42)
    def test_a_missing_filler_refuses(self):
        a,b,m=field();b[next(iter(a))]='minecraft:air'
        with self.assertRaises(ValueError):qualify_preimage(plan(a),plan(b),m)
    def test_foreign_identity_is_not_accepted_as_dynamic(self):
        a,b,m=field();b[1311,72,-1000]='minecraft:stone'
        with self.assertRaises(ValueError):qualify_preimage(plan(a),plan(b),m)
    def test_water_does_not_escape_authored_hydraulic_air(self):
        a,b,m=field();a[1312,72,-1000]='minecraft:air';b[1312,72,-1000]='minecraft:water[level=0]'
        with self.assertRaises(ValueError):qualify_preimage(plan(a),plan(b),m)
    def test_orientation_is_preserved(self):
        a,b,m=field();b[1311,72,-1000]='minecraft:oak_stairs[facing=west,half=bottom]'
        with self.assertRaises(ValueError):qualify_preimage(plan(a),plan(b),m)
    def test_unknown_lock_memory_is_not_toggled(self):
        a,b,m=field();b[1331,71,-991]='create_hypertube:hypertube_entrance[facing=south,locked=true,powered=false,waterlogged=false]'
        with self.assertRaises(ValueError):qualify_preimage(plan(a),plan(b),m)
    def test_changed_source_bytes_never_become_a_new_accepted_pin(self):
        with self.assertRaises(ValueError):composite([b'{}',b'{}',b'{}'])
    def test_partial_requires_unfed_clean_exact_six_links(self):
        value=partial();qualify_partial(value)
        for key,replacement in [('actual_wheat_feed_performed',True),('remaining_owned_tickets',1),('train_created',True)]:
            changed=copy.deepcopy(value);changed[key]=replacement
            with self.assertRaises(ValueError):qualify_partial(changed)
        value['native_tube_links'][3]['to'][2]+=1
        with self.assertRaises(ValueError):qualify_partial(value)
    def test_detector_items_must_really_exist(self):
        value=inspection();require_resume_stock(value);value['actual_detector_stock']=1
        with self.assertRaises(ValueError):require_resume_stock(value)
    def test_current_full_inventory_snapshot_is_required(self):
        value=inspection();value['native_resume_stock']['slots'].pop()
        with self.assertRaises(ValueError):require_resume_stock(value)
    def test_partial_attach_only_requires_remaining_real_items(self):
        value=inspection();value['missing_owned_detectors']=1;value['actual_detector_stock']=1;require_resume_stock(value)
    def test_fresh_native_proof_cannot_be_synthetic_or_stale(self):
        now=datetime.now(timezone.utc);value={'operation':'verify','plan_sha256':'a'*64,'blocks':COUNT,'failures':0,'status':'verified actual block identities, orientation, block entities and supplied inventories','started':(now-timedelta(seconds=3)).isoformat(),'finished':now.isoformat()}
        current_proof(value,'a'*64,now=now)
        value['finished']=(now-timedelta(minutes=21)).isoformat()
        with self.assertRaises(ValueError):current_proof(value,'a'*64,now=now)

if __name__=='__main__':unittest.main()
