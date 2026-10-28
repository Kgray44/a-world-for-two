"""Western exact source geometry, not native collision/render/acceptance."""
import json
from pathlib import Path
import unittest
from control_room.common import UserError
from tools.artistic_north_bank_west_infills import construct,RESERVE,WestPlan,furniture
from tools.artistic_materials import require_material_rule,require_outdoor_rule


class WesternInfill(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry=json.loads((Path(__file__).parent/'fixtures/artistic_north_bank_west_infill_registry.json').read_text())
        a,b,c,d=RESERVE
        cls.field={'samples':[{'x':x,'z':z,'kind':'dry','surface_y':63,'state':'minecraft:gravel'} for x in range(a,c+1) for z in range(b,d+1)],
            'saved_BEs':[],'protected_columns_xz':[]}
        cls.plan=construct(cls.registry,cls.field)
    def test_ten_actual_inhabited_houses_are_not_field_labels(self):
        self.assertEqual(len(self.plan.lots),10);self.assertEqual(len(self.plan.rooms),19)
        self.assertGreaterEqual(len(self.plan.fixtures),190)
        self.assertTrue(all(r['furnishing_objects']>=5 for r in self.plan.rooms))
    def test_complete_furnished_houses_and_all_outdoor_models_obey_rule(self):
        for r in self.plan.lots:require_material_rule({q:s for q,s in self.plan.blocks.items() if self.plan.owners[q]==r['name']},r['name'])
        require_outdoor_rule(self.plan.blocks,'whole western source')
    def test_shore_entrances_face_real_inland_access(self):
        self.assertEqual(next(r for r in self.plan.lots if r['id']=='fish-curer')['front'],'west')
        self.assertEqual(next(r for r in self.plan.lots if r['id']=='mariner')['front'],'north')
    def test_unsupported_optional_furniture_is_absent_not_floating(self):
        p=WestPlan(self.registry,self.field)
        self.assertFalse(furniture(p,(1039,65,-1237),'minecraft:potted_cornflower',support=(1039,64,-1237)))
        self.assertEqual(p.blocks,{})
    def test_water_main_footprint_still_refused(self):
        f=dict(self.field);f['samples']=[dict(r,kind='water',state='minecraft:water[level=0]') if (r['x'],r['z'])==(1007,-1259) else r for r in self.field['samples']]
        with self.assertRaises(UserError):construct(self.registry,f)
    def test_north_recess_has_real_clear_upper_stair_exit(self):
        p=self.plan
        for q in ((1008,69,-1261),(1008,70,-1261),(1007,69,-1261),(1007,70,-1261)):
            self.assertEqual(p.blocks[q],'minecraft:air')
        self.assertTrue(p.blocks[1008,68,-1261].startswith('minecraft:spruce_stairs['))


if __name__=='__main__':unittest.main()
