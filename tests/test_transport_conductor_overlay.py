"""Synthetic conductor geometry/material gates, never native conductor proof."""
from copy import deepcopy
import unittest

from control_room.common import UserError
from tools.transport_conductor_overlay import (
    BOGEYS, BURNERS, CONTROLS, ITEM_CLASS, SEATS, proposal_from_plan, qualify_materials,
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
