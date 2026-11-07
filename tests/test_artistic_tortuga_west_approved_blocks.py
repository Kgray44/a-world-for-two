"""Actual model semantics and retained public-passage admission."""
import json
from pathlib import Path
import unittest

from control_room.common import UserError
from tools import artistic_tortuga_west_approved_blocks as west
from tools.artistic_tortuga_frontages import RECIPES, AIR, check, key
from tools.artistic_tortuga_variants import variant_of
from tools.artistic_tortuga_fill import modeled


class ApprovedWestBlockTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry=json.loads((Path(__file__).parent/'fixtures/tortuga_fill_registry.json').read_text())

    def test_workrooms_are_real_occupied_models_in_every_orientation(self):
        for recipe,factory in west.EXTRA.items():
            p=factory(self.registry)
            for turn in range(4):
                rotated=variant_of(factory(self.registry),recipe,turn)
                proof=check(rotated)
                self.assertEqual(proof['material']['violations'],[])
                self.assertEqual(proof['rooms'],2)
                self.assertTrue(any(key(s).endswith('_bed')for s in rotated.blocks.values()))
                self.assertFalse(any('Items:'in s or'Owner:'in s for s in rotated.tags.values()))
            self.assertTrue(p.supports)
        loft=west.chart_loft(self.registry)
        self.assertEqual(key(loft.blocks[1,1,4]),'minecraft:cartography_table')
        self.assertEqual(key(loft.blocks[3,1,1]),'minecraft:crafting_table')
        self.assertEqual(key(loft.blocks[3,2,1]),'supplementaries:globe')
        self.assertEqual(key(loft.blocks[3,1,2]),'minecraft:barrel')
        self.assertEqual(key(loft.blocks[3,2,2]),'supplementaries:hourglass')
        self.assertEqual(key(loft.blocks[1,1,3]),'minecraft:dark_oak_planks')
        self.assertEqual(key(loft.blocks[1,2,3]),west.POTS[4])

    def test_temporary_new_keys_never_replace_or_outlive_frozen_recipes(self):
        before=dict(RECIPES)
        with self.assertRaisesRegex(RuntimeError,'owned failure'):
            with west.source_recipes():
                self.assertEqual(set(RECIPES)-set(before),set(west.EXTRA))
                with self.assertRaises(UserError):
                    with west.source_recipes():pass
                raise RuntimeError('owned failure')
        self.assertEqual(RECIPES,before)

    def test_low_shared_alley_requires_every_saved_column_and_keeps_high_brackets(self):
        rows=[[x,z,'minecraft:gravel',AIR,AIR]for x in(1081,1082)for z in range(-1233,-1228)]
        prior={(1082,66,-1232):'mythrais:curved_corbel_dark_oak[facing=west,shape=0]'}
        self.assertEqual(len(west.shared_low_walk(rows,prior)),10)
        with self.assertRaisesRegex(UserError,'FULL saved walking witness'):
            west.shared_low_walk(rows[:-1],prior)
        for obstruction in ('minecraft:barrel','minecraft:stone'):
            with self.assertRaisesRegex(UserError,'retained floor, solid'):
                west.shared_low_walk(rows,{**prior,(1082,65,-1232):obstruction})
        with self.assertRaisesRegex(UserError,'retained floor, solid'):
            west.shared_low_walk(rows,{(1082,63,-1232):'minecraft:gravel'})

    def test_recessed_tackle_door_keeps_both_alley_columns_clear_below_high_brackets(self):
        p=west.tackle_workroom(self.registry)
        self.assertEqual(p.entries[0]['door'],[6,1,7])
        self.assertEqual(p.entries[0]['outside_step'],[7,0,7])
        for x in (8,9):
            for z in range(6,9):
                self.assertNotIn((x,z),p.main[p.owner])
                for y in (1,2):self.assertEqual(p.blocks.get((x,y,z),AIR),AIR)
        self.assertEqual(key(p.blocks[8,3,6]),'mythrais:curved_corbel_dark_oak')

    def test_existing_pavers_are_verification_only_and_cannot_become_new_ownership(self):
        rows=[[x,z,'chipped:small_stone_bricks',AIR,AIR]for x,z in west.RETAINED_APPROACH['net-needle-crook']]
        values=west.retained_approach(rows,'net-needle-crook',{}, {})
        self.assertEqual(len(values),12)
        self.assertEqual(values[1018,63,-1270],'chipped:small_stone_bricks')
        with self.assertRaisesRegex(UserError,'construction delta'):
            west.retained_approach(rows,'net-needle-crook',{}, {(1018,63,-1270):'minecraft:cobblestone'})
        with self.assertRaisesRegex(UserError,'actual authored source'):
            west.retained_approach(rows,'net-needle-crook',{(1018,63,-1270):'minecraft:stone'}, {})
        with self.assertRaisesRegex(UserError,'do not invent a paver'):
            west.retained_approach(rows[:-1],'net-needle-crook',{}, {})

    def test_five_distinct_frontages_have_furnished_scene_targets_and_finite_batches(self):
        with west.source_recipes():
            names=[];main=0;rooms=0
            for batch,definition in west.BATCHES.items():
                states,tags,buildings,mains=modeled(self.registry,definition)
                self.assertLess(len(states)+2048,12000)
                main+=len(mains)
                for b in buildings:
                    names.append(b['name']);rooms+=len(b['rooms'])
                    self.assertTrue(b['entries'])
                    self.assertEqual(len(b['scene_views']),len(b['rooms']))
                    self.assertTrue(all(v['actual_source_object']for v in b['scene_views']))
            self.assertEqual(len(set(names)),5)
            self.assertEqual(main,344)
            self.assertEqual(rooms,10)


if __name__=='__main__':unittest.main()
