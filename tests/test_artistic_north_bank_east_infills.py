"""Complete original infill source checks, separate from rendering/native QA."""
import json
from pathlib import Path
import unittest

from control_room.common import UserError
from tools.artistic_north_bank_east_infills import construct,check,merge,EastPlan,rotate_point,INTENTS
from tools.settlement_attractions import properties


class EasternInfill(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry=json.loads((Path(__file__).parent/'fixtures/artistic_north_bank_infill_registry.json').read_text())
        cls.field={'samples':[{'x':x,'z':z,'kind':'dry','surface_y':63,'state':'minecraft:grass_block'}
            for x in range(1217,1393) for z in range(-1296,-1119)],'saved_BEs':[],'protected_columns_xz':[]}
        cls.plan=construct(cls.registry,cls.field,{})

    def test_all22_are_furnished_geometry_not_future_labels(self):
        result=check(self.plan)
        self.assertEqual((result['fully_modeled_buildings'],result['inhabited_rooms']),(22,55))
        self.assertGreaterEqual(result['actual_furnishing_models'],1100)
        self.assertGreaterEqual(min(r['furnishing_objects'] for r in self.plan.rooms),15)
        self.assertFalse(result['native_or_art_acceptance'])

    def test_complete_buildings_and_whole_streets_obey_material_limits(self):
        result=check(self.plan)
        self.assertEqual(len(result['material_checks']),22)
        self.assertTrue(result['outdoor_max9'])

    def test_north_and_east_houses_rotate_actual_rooms_and_doors(self):
        for expected in INTENTS:
            actual=next(r for r in self.plan.lots if r['id']==expected.ident)
            self.assertEqual(actual['front'],expected.face)
            self.assertEqual(actual['source_room_rotation_degrees'],180 if expected.face in ('north','east') else 0)
            x,y,z=actual['door'];state=self.plan.blocks[x,y,z]
            self.assertIn('door',state)
            facing=properties(state)['facing']
            self.assertEqual(facing,{'north':'south','south':'north','east':'west','west':'east'}[expected.face])

    def test_native_window_axis_is_not_rotated_to_an_unsupported_value(self):
        windows=[properties(v) for v in self.plan.blocks.values() if v.startswith('mcwwindows:dark_oak_plank_window[')]
        self.assertGreater(len(windows),100)
        self.assertTrue(all(r['facing'] in ('north','east') for r in windows))

    def test_halfturn_is_an_exact_involution(self):
        center=(1301,-1186)
        for point in ((1298,65,-1190),(1304,79,-1181)):
            self.assertEqual(rotate_point(rotate_point(point,center,2),center,2),point)

    def test_two_foreign_structural_solids_cannot_merge(self):
        a=EastPlan(self.registry,self.field);b=EastPlan(self.registry,self.field);q=(1300,65,-1180)
        a.blocks[q]='minecraft:bricks';b.blocks[q]='minecraft:stone_bricks';b.owners[q]='other';b.priority[q]=50
        with self.assertRaises(UserError):merge(a,b)


if __name__=='__main__':unittest.main()
