"""Source-only court safety/composition, not actual geography or acceptance."""
import json
from pathlib import Path
import unittest
from control_room.common import UserError
from tools.artistic_north_bank_quay_courts import build_one,COURTS,RESERVE
from tools.artistic_materials import require_material_rule


class QuayCourts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry=json.loads((Path(__file__).parent/'fixtures/artistic_north_bank_quay_registry.json').read_text())
        a,b,c,d=RESERVE
        cls.field={'samples':[{'x':x,'z':z,'kind':'dry','surface_y':63,'state':'minecraft:gravel'} for x in range(a,c+1) for z in range(b,d+1)],
            'saved_BEs':[],'protected_columns_xz':[]}
    def test_distinct_roof_and_corner_programs_are_fully_furnished(self):
        self.assertEqual(len({p[0] for p in COURTS}),12)
        self.assertGreaterEqual(len({(p[4],p[5],p[7]) for p in COURTS}),10)
        for row in COURTS:
            p=build_one(self.registry,self.field,row)
            self.assertEqual(len(p.rooms),2)
            self.assertTrue(all(r['furnishing_objects']>=6 for r in p.rooms))
            require_material_rule(p.blocks,row[1])
    def test_a_single_water_column_in_main_field_cannot_be_inferred_dry(self):
        row=COURTS[0];ox,oz=row[2];bad=ox+3,oz+3
        f=dict(self.field);f['samples']=[dict(p,kind='water',state='minecraft:water[level=0]') if (p['x'],p['z'])==bad else p for p in self.field['samples']]
        with self.assertRaises(UserError):build_one(self.registry,f,row)
    def test_saved_block_entity_is_never_replayed(self):
        row=COURTS[0];ox,oz=row[2];f=dict(self.field);f['saved_BEs']=[[ox+3,64,oz+3]]
        with self.assertRaises(UserError):build_one(self.registry,f,row)


if __name__=='__main__':unittest.main()
