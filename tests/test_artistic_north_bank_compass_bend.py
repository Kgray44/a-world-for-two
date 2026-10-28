"""Authored geometry and preservation checks, not native/art acceptance."""
import json
from pathlib import Path
import unittest

from control_room.common import UserError
from tools.artistic_north_bank_compass_bend import (HOUSES,SETBACKS,construct,check,
    lane_paver,EastPlan)


class CompassBend(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry=json.loads((Path(__file__).parent/'fixtures/artistic_north_bank_compass_registry.json').read_text())
        cls.field={'samples':[{'x':x,'z':z,'kind':'dry','surface_y':63,'state':'minecraft:grass_block'}
            for x in range(1217,1393) for z in range(-1296,-1119)],'protected_columns_xz':[],'saved_BEs':[]}
        cls.plan=construct(cls.registry,cls.field)

    def test_all_eight_are_modeled_and_inhabited_not_plot_labels(self):
        proof=check(self.plan)
        self.assertEqual((proof['buildings'],proof['rooms']),(8,20))
        self.assertGreaterEqual(proof['furnishing_models'],370)
        self.assertTrue(all(r['furnishing_objects']>=15 for r in self.plan.rooms))
        self.assertFalse(proof['native_or_visual_acceptance'])

    def test_three_upper_massings_are_actually_set_back(self):
        for ident in SETBACKS:
            rooms=[r for r in self.plan.rooms if r['building']==ident]
            self.assertLess(len(rooms[-1]['floor_cells']),len(rooms[0]['floor_cells']))
            self.assertIn('gallery_door',rooms[-1])

    def test_real_native_modded_depth_and_ceiling_models_are_present(self):
        values=list(self.plan.blocks.values())
        self.assertTrue(any(v.startswith('mythrais:small_curved_corbel_') for v in values))
        self.assertTrue(any(v.startswith('dawnoftimebuilder:spruce_support_slab') for v in values))
        self.assertTrue(any(v.startswith('mcwwindows:dark_oak_plank_window') for v in values))
        self.assertTrue(any(v.startswith('mythrais:roof_up_67_') for v in values))

    def test_complete_building_and_outdoor_material_rules(self):
        proof=check(self.plan)
        self.assertEqual(len(proof['complete_buildings_3_9']),8)
        self.assertTrue(proof['outdoor_max9'])

    def test_existing_junction_is_verified_without_replaying_it(self):
        p=EastPlan(self.registry,{'samples':[{'x':1,'z':2,'surface_y':63,'kind':'retained_object','state':'minecraft:cobblestone'}],
            'saved_BEs':[],'protected_columns_xz':[]})
        p.prior={(1,63,2):'minecraft:cobblestone',(1,64,2):'minecraft:air',(1,65,2):'minecraft:air'};p.retained={}
        self.assertEqual(lane_paver(p,1,2),(1,63,2))
        self.assertEqual(p.blocks,{})
        self.assertEqual(p.retained,p.prior)

    def test_a_foreign_retained_object_is_never_a_junction(self):
        p=EastPlan(self.registry,{'samples':[{'x':1,'z':2,'surface_y':63,'kind':'water','state':'minecraft:water'}],
            'saved_BEs':[],'protected_columns_xz':[]});p.prior={};p.retained={}
        with self.assertRaises(UserError):lane_paver(p,1,2)

    def test_native_living_plants_are_contained_and_not_saplings(self):
        plants=[v.split('[',1)[0] for v in self.plan.blocks.values() if 'potted_' in v]
        self.assertGreaterEqual(len(plants),25)
        self.assertGreaterEqual(len(set(plants)),3)
        self.assertFalse(any('sapling' in v for v in self.plan.blocks.values()))


if __name__=='__main__':unittest.main()
