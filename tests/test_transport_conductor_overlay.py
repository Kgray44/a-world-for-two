"""Synthetic conductor geometry/material gates, never native conductor proof."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from control_room.common import UserError
from tools.transport_conductor_overlay import (
    BOGEYS, BURNERS, CONTROLS, GEOMETRY_SHA, ITEM_CLASS, SEATS, load_source, proposal_from_plan, qualify_materials,
)


def source():
    values = {(x,60,-1000):'minecraft:air' for x in range(7941)}
    for p, facing in zip(CONTROLS, ('north','south')):
        values[p] = f'create:controls[facing={facing},open=false,virtual=false,waterlogged=false]'
    for p in BURNERS:values[p]='minecraft:air'
    for p in SEATS:values[p]='create:blue_seat[waterlogged=false]'
    for p in BOGEYS:values[p]='create:small_bogey[axis=z,waterlogged=false]'
    for p in sorted(values)[:len(values)-7941]:del values[p]
    palette=sorted(set(values.values()));indices={state:n for n,state in enumerate(palette)}
    return {'seed':'synthetic','world_path':'synthetic-fixture-world','backup_sha256':'0'*64,
            'construction_forbidden':True,'verification_only':True,
            'palette':palette,'blocks':[[*p,indices[state]]for p,state in sorted(values.items())],
            'commands':[],'block_entities':[]}


def materials():
    slots=[{'slot':n,'empty':True}for n in range(27)]
    slots[3]={'slot':3,'empty':False,'item':'create:blaze_burner','count':2,'components':{},
              'native_item_class':ITEM_CLASS,'has_captured_blaze':True}
    return {'format':'awft-native-conductor-materials:1','native_item_getters_observed':True,'slots':slots}


class ConductorOverlayTests(unittest.TestCase):
    def write_source(self,folder,*,checkpoint='1'*64,geometry=GEOMETRY_SHA):
        plan=source();plan['backup_sha256']=checkpoint
        raw=json.dumps(plan).encode();(folder/'mill-current7941-VERIFY-ONLY.json').write_bytes(raw)
        manifest={'format':'awft-transport-saved-inputs:1','checkpoint_id':'synthetic-new-checkpoint','checkpoint_sha256':checkpoint,
                  'mill_preimage':{'targets':7941,'retained_filler_cells':42,'source_geometry_sha256':geometry},
                  'files':{'mill-current7941-VERIFY-ONLY.json':{'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}}}
        encoded=json.dumps(manifest).encode();(folder/'manifest.json').write_bytes(encoded)
        return hashlib.sha256(encoded).hexdigest()

    def test_new_checkpoint_requires_its_explicit_manifest_and_actual_plan_bytes(self):
        with tempfile.TemporaryDirectory()as name:
            folder=Path(name);sha=self.write_source(folder)
            plan,manifest,_=load_source(folder,sha)
            self.assertEqual(plan['backup_sha256'],'1'*64)
            self.assertEqual(manifest['checkpoint_id'],'synthetic-new-checkpoint')
            with self.assertRaises(UserError):load_source(folder,'0'*64)
            path=folder/'mill-current7941-VERIFY-ONLY.json';path.write_bytes(path.read_bytes()+b' ')
            with self.assertRaises(UserError):load_source(folder,sha)

    def test_unknown_geometry_cannot_be_adopted_under_a_new_source_digest(self):
        with tempfile.TemporaryDirectory()as name:
            folder=Path(name);sha=self.write_source(folder,geometry='f'*64)
            with self.assertRaises(UserError):load_source(folder,sha)

    def test_different_checkpoint_labels_cannot_rebind_existing_plan(self):
        with tempfile.TemporaryDirectory()as name:
            folder=Path(name);self.write_source(folder)
            path=folder/'manifest.json';manifest=json.loads(path.read_bytes());manifest['checkpoint_sha256']='2'*64
            raw=json.dumps(manifest).encode();path.write_bytes(raw)
            with self.assertRaises(UserError):load_source(folder,hashlib.sha256(raw).hexdigest())

    def test_four_cell_block_conductors_keep_three_passenger_seats_and_two_bogeys(self):
        result=proposal_from_plan(source(),{'runtime_exercised':False})
        before=result['before'];after=result['after_proposal'];keep=result['preserve']
        self.assertEqual(len(before['blocks']),4);self.assertEqual(len(after['blocks']),4)
        self.assertEqual(len(keep['blocks']),5)
        for plan in (before,after,keep):
            self.assertTrue(plan['construction_forbidden']);self.assertTrue(plan['verification_only'])
            self.assertEqual(plan['commands'],[]);self.assertEqual(plan['block_entities'],[])
        self.assertFalse(result['world_write_authority']);self.assertEqual(result['material_debits'],0)
        self.assertFalse(result['recovery_boundary']['existing_resume_accepts_overlay'])
        self.assertEqual(result['recovery_boundary']['passenger_seats_after'],3)
        self.assertEqual(result['recovery_boundary']['native_block_conductors_expected_after'],2)
        self.assertTrue(all(state=='PENDING'for state in result['acceptance'].values()))

    def test_preimage_drift_does_not_get_normalized(self):
        for replacement in ('minecraft:stone','create:blaze_burner[blaze=none,facing=north]'):
            plan=source();index=next(n for n,row in enumerate(plan['blocks'])if tuple(row[:3])==BURNERS[0])
            plan['palette'].append(replacement);plan['blocks'][index][3]=len(plan['palette'])-1
            with self.assertRaises(UserError):proposal_from_plan(plan,{})
        plan=source();plan['construction_forbidden']=False
        with self.assertRaises(UserError):proposal_from_plan(plan,{})

    def test_two_actual_filled_items_create_only_a_proposed_debit(self):
        snapshot=materials();original=deepcopy(snapshot);result=qualify_materials(snapshot)
        self.assertEqual(result['proposed_debits'],[{'slot':3,'count':2}])
        self.assertEqual(result['native_debits_performed'],0);self.assertEqual(snapshot,original)
        self.assertEqual(len(result['all27_before_slots']),27)

    def test_empty_or_one_burner_cannot_supply_two_conductors(self):
        for item, count, captured in (('create:empty_blaze_burner',2,False),('create:blaze_burner',1,True),('create:blaze_burner',2,False)):
            snapshot=materials();snapshot['slots'][3].update(item=item,count=count,has_captured_blaze=captured)
            with self.assertRaises(UserError):qualify_materials(snapshot)

    def test_forged_per_stack_capture_data_cannot_replace_native_item_getter(self):
        snapshot=materials();snapshot['slots'][3]['components']={'minecraft:block_entity_data':{'capturedBlaze':True}}
        with self.assertRaises(UserError):qualify_materials(snapshot)
        snapshot=materials();snapshot['slots'][3]['native_item_class']='fixture:fake'
        with self.assertRaises(UserError):qualify_materials(snapshot)

    def test_full_slot_custody_refuses_partial_duplicate_or_ambiguous_empty_slots(self):
        snapshot=materials();snapshot['slots'].pop()
        with self.assertRaises(UserError):qualify_materials(snapshot)
        snapshot=materials();snapshot['slots'][4]=deepcopy(snapshot['slots'][3])
        with self.assertRaises(UserError):qualify_materials(snapshot)
        snapshot=materials();snapshot['slots'][4]['item']='minecraft:diamond'
        with self.assertRaises(UserError):qualify_materials(snapshot)


if __name__=='__main__':unittest.main()
