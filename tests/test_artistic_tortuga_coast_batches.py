"""Occupied long/wide/narrow models and bounded source-only registration."""
import json
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

from tools.artistic_tortuga_frontages import RECIPES,check,AIR,key
from tools.artistic_tortuga_variants import variant_of
from tools.artistic_tortuga_coast_batches import EXTRA,BATCHES,source_recipes,batch_map
from tools.artistic_tortuga_fill import modeled


class TortugaCoastBatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry=json.loads((Path(__file__).parent/'fixtures/tortuga_fill_registry.json').read_text())

    def test_three_original_proportions_have_real_workstations_homes_and_supported_scenes(self):
        dimensions=[];rooms=[]
        for name,factory in EXTRA.items():
            p=factory(self.registry);proof=check(p);cells=p.main[p.owner]
            dimensions.append((max(x for x,z in cells)-min(x for x,z in cells)+1,max(z for x,z in cells)-min(z for x,z in cells)+1))
            rooms.append(proof['rooms'])
            self.assertEqual(proof['material']['violations'],[])
            self.assertTrue(any(key(s).endswith('_bed')for s in p.blocks.values()))
            self.assertTrue(any(key(s)in('minecraft:loom','minecraft:crafting_table','minecraft:furnace','minecraft:smoker')for s in p.blocks.values()))
            self.assertFalse(any('Items:'in tag or'Owner:'in tag for tag in p.tags.values()))
            for turn in range(4):check(variant_of(factory(self.registry),name,turn))
        self.assertIn((8,18),dimensions)
        self.assertIn((13,8),dimensions)
        self.assertIn((5,10),dimensions)
        self.assertEqual(sorted(rooms),[2,3,4])

    def test_new_recipe_registration_restores_originals_even_on_failure(self):
        before=dict(RECIPES)
        with self.assertRaisesRegex(RuntimeError,'deliberate source failure'):
            with source_recipes():
                self.assertEqual(set(RECIPES)-set(before),set(EXTRA))
                raise RuntimeError('deliberate source failure')
        self.assertEqual(RECIPES,before)

    def test_small_quay_shop_keeps_its_casement_knees_above_the_real_two_high_body(self):
        p=variant_of(EXTRA['coast-kettle-loft'](self.registry),'coast-kettle-loft',2)
        for z in range(10):
            for y in(1,2):self.assertEqual(p.blocks.get((5,y,z),AIR),AIR)
        self.assertTrue(any(key(s)=='mythrais:curved_corbel_dark_oak'and q[0]==5 and q[1]==3 for q,s in p.blocks.items()))
        self.assertEqual(p.entries[0]['outward'],'east')
        self.assertTrue(all(tuple(q)in p.blocks for r in p.routes for q in r['positions']))

    def test_batch_maps_are_valid_explicit_source_schematics_with_actual_main_outlines(self):
        with source_recipes():
            for name,definition in BATCHES.items():
                states,tags,buildings,main=modeled(self.registry,definition)
                self.assertLess(len(states)+2048,12000)
                manifest={'batch':name,'buildings':buildings,'routes':[],'main_columns':len(main),'lane_columns':0}
                field={'eligible_columns_READONLY':[],'two_high_walk_columns_READONLY':[]}
                data=batch_map(manifest,field)
                root=ET.fromstring(data)
                self.assertIn('NOT A NATIVE SCREENSHOT',data.decode())
                self.assertGreaterEqual(len(root.findall('{http://www.w3.org/2000/svg}rect')),len(main))


if __name__=='__main__':unittest.main()
