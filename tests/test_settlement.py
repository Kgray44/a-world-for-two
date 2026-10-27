import tempfile
import unittest
from pathlib import Path

from control_room.common import UserError
from tools.settlement import Plan
from tools.settlement_port import PortPlan


class SettlementSafetyTests(unittest.TestCase):
    def plan(self,rotation=0,protected=()):
        registry={'blocks':{'minecraft:oak_planks':{},'minecraft:air':{},
                  'minecraft:oak_stairs':{'facing':['north','east','south','west']}},
                  'items':[],'entities':['minecraft:zombie'],
                  'entity_categories':{'minecraft:zombie':'monster'},'seed':'42','world_path':'world'}
        survey={'samples':[{'x':x,'z':z,'y':70,'block_entities':list(protected)} for x in (-8,0,8) for z in (-8,0,8)]}
        return Plan(registry,survey,(0,0),'a'*64,rotation)

    def test_undocumented_registry_ids_and_state_values_are_refused(self):
        plan=self.plan()
        with self.assertRaises(UserError):plan.put(0,70,0,'invented:pretty_chair')
        with self.assertRaises(UserError):plan.put(0,70,0,'minecraft:oak_stairs',facing='inward')
        self.assertEqual(plan.blocks,{})

    def test_existing_block_entities_cannot_be_overwritten_even_by_clearance_air(self):
        plan=self.plan(protected=[(0,70,0)])
        plan.put(0,70,0,'minecraft:air')
        with tempfile.TemporaryDirectory() as folder:
            target=Path(folder)/'plan.json'
            with self.assertRaises(UserError):plan.save(target)
            self.assertFalse(target.exists())

    def test_height_and_reviewed_footprint_remain_bounded(self):
        plan=self.plan()
        for x,y,z in [(0,320,0),(0,-65,0),(257,70,0),(0,70,-257)]:
            with self.assertRaises(UserError):plan.put(x,y,z,'minecraft:oak_planks')
        self.assertEqual(plan.blocks,{})

    def test_world_rotation_keeps_material_orientation_with_position(self):
        plan=self.plan(rotation=1)
        plan.put(3,70,5,'minecraft:oak_stairs',facing='north')
        self.assertEqual(plan.blocks,{(-5,70,3):'minecraft:oak_stairs[facing=east]'})

    def test_hostile_entities_are_refused_in_the_homestead_plan(self):
        plan=self.plan()
        with self.assertRaises(UserError):plan.entity('minecraft:zombie',0,70,0,'Bad idea')
        self.assertEqual(plan.commands,[])

    def test_expansion_cannot_clear_or_replace_a_completed_core_block(self):
        original=self.plan()
        core={'palette':['minecraft:oak_planks'], 'blocks':[[0,70,0,0]]}
        port=PortPlan(original.registry, {'samples':list(original.samples.values())},
                      (0,0),'a'*64,core,rotation=0)
        # Matching construction is retained in place and omitted from the delta.
        port.put(0,70,0,'minecraft:oak_planks')
        self.assertEqual(port.blocks,{})
        with self.assertRaises(UserError):port.put(0,70,0,'minecraft:air')
        self.assertEqual(port.blocks,{})

    def test_connecting_quay_yields_to_core_without_mutating_the_core_exclusion(self):
        original=self.plan()
        core={'palette':['minecraft:oak_planks'], 'blocks':[[0,70,0,0]]}
        port=PortPlan(original.registry, {'samples':list(original.samples.values())},
                      (0,0),'a'*64,core,rotation=0)
        port.quay_put(0,70,0,'minecraft:air')
        self.assertEqual(port.fixed[(0,70,0)],'minecraft:oak_planks')
        self.assertEqual(port.blocks,{})


if __name__=='__main__':unittest.main()
