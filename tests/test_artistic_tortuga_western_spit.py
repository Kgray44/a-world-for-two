"""Occupied geometry, source custody and fail-closed producer policy."""
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from control_room.common import UserError
from tools import artistic_tortuga_western_spit as spit
from tools import artistic_tortuga_frontages as originals
from tools.artistic_tortuga_variants import variant_of
from tools.artistic_tortuga_fill import modeled


class WesternSpitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.registry=json.loads((Path(__file__).parent/'fixtures/tortuga_fill_registry.json').read_text())

    def test_new_small_models_have_real_circulation_and_materials_in_four_orientations(self):
        for name,factory in spit.EXTRA.items():
            for turn in range(4):
                p=variant_of(factory(self.registry),name,turn)
                proof=originals.check(p)
                self.assertEqual(proof['material']['violations'],[])
                self.assertTrue(p.entries)
                self.assertFalse(any('Items:'in nbt or'Owner:'in nbt for nbt in p.tags.values()))
                self.assertTrue(p.supports)

    def test_recessing_changes_only_new_models_and_keeps_original_function_globals(self):
        door=originals.door
        before=originals.RECIPES['mugs-mending'](self.registry).blocks
        p=spit.recessed_original(self.registry,'mugs-mending')
        self.assertIs(originals.door,door)
        self.assertEqual(originals.RECIPES['mugs-mending'](self.registry).blocks,before)
        entry=p.entries[0]
        self.assertEqual(entry['door'],[4,1,1])
        self.assertEqual(entry['outside_step'],[4,0,0])
        self.assertEqual(originals.key(p.blocks[4,1,1]),'mcwdoors:dark_oak_cottage_door')
        self.assertEqual(p.blocks[4,1,0],originals.AIR)

    def test_recipe_context_restores_all_maps_after_an_owned_failure(self):
        before=dict(originals.RECIPES)
        with self.assertRaisesRegex(RuntimeError,'owned source failure'):
            with spit.source_recipes():
                self.assertTrue(set(spit.EXTRA)<=set(originals.RECIPES))
                raise RuntimeError('owned source failure')
        self.assertEqual(originals.RECIPES,before)

    def test_real_current_pavers_are_never_replaced_or_called_new_ownership(self):
        paver='chipped:small_stone_bricks'
        self.assertIsNone(spit.public_floor_write(paver,paver,None,{'x'}))
        self.assertIsNone(spit.public_floor_write('minecraft:cobblestone','minecraft:cobblestone','minecraft:cobblestone',{'x'}))
        self.assertEqual(spit.public_floor_write('minecraft:gravel','minecraft:gravel',None,{'x'}),'minecraft:andesite')
        for value in(None,'minecraft:water','minecraft:lava','minecraft:oak_slab[type=bottom,waterlogged=true]'):
            with self.assertRaises(UserError):spit.public_floor_write(value,value,None,{'z'})
        with self.assertRaisesRegex(UserError,'AIR reservation'):
            spit.public_floor_write(originals.AIR,originals.AIR,originals.AIR,{'z'})
        with self.assertRaisesRegex(UserError,'Observed public paver changed'):
            spit.public_floor_write(paver,'minecraft:gravel',None,{'x'})

    def test_resource_refusal_stops_before_any_home_or_reader_work(self):
        with patch.object(spit,'guard',return_value={'allowed':True}),patch.object(spit,'reader_budget',side_effect=UserError('memory refused')),patch.object(spit.fill,'private_home')as home:
            with self.assertRaisesRegex(UserError,'memory refused'):spit.prepare('unused','unused','unused','unused','unused')
            home.assert_not_called()
        with patch.object(spit,'guard',side_effect=UserError('reserve refused')),patch.object(spit,'reader_budget')as reader:
            with self.assertRaisesRegex(UserError,'reserve refused'):spit.prepare('unused','unused','unused','unused','unused')
            reader.assert_not_called()

    def test_ten_buildings_have_varied_main_shapes_and_actual_task_camera_targets(self):
        with spit.source_recipes():
            states,tags,buildings,mains=modeled(self.registry,spit.BATCHES['western-spit-ten'])
        self.assertEqual(len(buildings),10)
        self.assertEqual(len(mains),514)
        self.assertEqual(sum(len(b['rooms'])for b in buildings),22)
        self.assertLess(len(states)+2048,12000)
        self.assertTrue(all(968<=q[0]<=1099 for q in states))
        self.assertEqual(len({b['recipe']for b in buildings}),10)
        for b in buildings:
            self.assertEqual(len(b['scene_views']),len(b['rooms']))
            self.assertTrue(all(v['actual_source_object']for v in b['scene_views']))
        homes=[b for b in buildings if any(originals.key(s).endswith('_bed')and(x,z)in set(map(tuple,b['main_columns_xz']))for(x,y,z),s in states.items())]
        self.assertEqual(len(homes),8)
        for recipe in('spit-lantern-annex','spit-fitting-annex'):
            p=spit.EXTRA[recipe](self.registry)
            self.assertEqual(len(p.levels[p.owner]),1)
            self.assertTrue(all(r['floor']==0 for r in p.rooms))
            self.assertFalse(any(originals.key(s).endswith('_bed')for s in p.blocks.values()))


if __name__=='__main__':unittest.main()
