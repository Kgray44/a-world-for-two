"""Profile-selected source architecture; no native terrain/render acceptance."""
import json
from pathlib import Path
import unittest
from control_room.common import UserError
from tools.artistic_north_bank_shore_profiles import build_one,COURTS,SHORE_BOUNDS
from tools.artistic_materials import require_material_rule


QUALIFIED={'caper-rose','beacon-book','brine-harp','goldfinch-steps','palm-fold','otter-pantry','gannet-home',
    'tide-spool','vetch-window','pearl-linen','willow-quill','coral-bell','rosy-keel','tern-tail'}


class ProfiledShore(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry=json.loads((Path(__file__).parent/'fixtures/artistic_north_bank_quay_registry.json').read_text())
        a,b,c,d=SHORE_BOUNDS
        cls.field={'samples':[{'x':x,'z':z,'kind':'dry','surface_y':63,'state':'minecraft:gravel'} for x in range(a,c+1) for z in range(b,d+1)],
            'saved_BEs':[],'protected_columns_xz':[]}
    def test_all_fourteen_qualified_compositions_have_complete_rooms_and_materials(self):
        for row in COURTS:
            if row[0] not in QUALIFIED:continue
            p=build_one(self.registry,self.field,row)
            self.assertEqual(len(p.rooms),2)
            self.assertTrue(all(r['furnishing_objects']>=6 for r in p.rooms))
            require_material_rule(p.blocks,row[1])
    def test_no_flammable_house_can_borrow_a_clear_surface_near_lava(self):
        row=next(r for r in COURTS if r[0]=='vetch-window');ox,oz=row[2];hot=ox+9,oz+3
        f=dict(self.field);f['samples']=[dict(p,kind='water',state='minecraft:lava[level=0]') if (p['x'],p['z'])==hot else p for p in self.field['samples']]
        with self.assertRaises(UserError):build_one(self.registry,f,row)
    def test_centres_and_names_are_separate_original_source_programs(self):
        self.assertEqual(len(COURTS),18)
        self.assertEqual(len({r[0] for r in COURTS}),18)
        self.assertEqual(len({r[2] for r in COURTS}),18)


if __name__=='__main__':unittest.main()
