import json
from pathlib import Path
import unittest
from unittest.mock import patch

from control_room.common import UserError
from tools import artistic_tortuga_west_narrow_workrooms as n
from tools.artistic_tortuga_frontages import RECIPES,AIR,key,check


class NarrowWorkroomTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry=json.loads((Path(__file__).parent/'fixtures/tortuga_fill_registry.json').read_text())

    def test_four_actual_working_floors_fit_the_literal_unequal_narrow_footprints(self):
        with n.source_recipes():states,tags,buildings,mains=n.fill.modeled(self.registry,n.BATCH)
        self.assertEqual((len(buildings),len(mains)),(4,240))
        self.assertEqual(sum(len(b['rooms'])for b in buildings),8)
        self.assertTrue(all(b['proof']['storeys']==1 for b in buildings))
        self.assertEqual(len({tuple(b['origin'])for b in buildings}),4)
        self.assertTrue(all(968<=x<=1099 for x,y,z in states))
        self.assertTrue(all(not ('Items' in v or 'Owner' in v)for v in tags.values()))

    def test_display_and_door_have_actual_recesses_inside_founded_main_mass(self):
        p=n.EXTRA['narrow-long-splice'](self.registry);main=p.main[p.owner]
        self.assertTrue(key(p.blocks[1,1,3]).startswith('mcwwindows:'))
        self.assertEqual(p.blocks[0,1,4],AIR)
        self.assertIn((0,4),main)
        self.assertNotEqual(p.blocks[0,0,3],AIR)
        self.assertTrue(key(p.blocks[0,1,3]).startswith(('fishofthieves:potted_','minecraft:potted_')))
        e=p.entries[0];self.assertEqual(e['door'],[2,1,4]);self.assertEqual(e['outside_step'],[3,0,4])
        self.assertIn((3,4),main)
        self.assertTrue(key(p.blocks[2,1,4]).endswith('_door'))
        self.assertEqual(p.blocks[3,1,4],AIR)

    def test_each_distinct_trade_has_real_station_counter_and_surviving_supported_task_lights(self):
        stations={'narrow-long-splice':'minecraft:loom','narrow-folded-jack':'minecraft:loom','narrow-bent-crate':'minecraft:stonecutter','narrow-last-kettle':'minecraft:smoker'}
        fields=[]
        for recipe,station in stations.items():
            p=n.EXTRA[recipe](self.registry);proof=check(p);ids={key(s)for s in p.blocks.values()}
            self.assertIn(station,ids);self.assertIn('handcrafted:dark_oak_counter',ids);self.assertIn('minecraft:lantern',ids)
            self.assertTrue(proof['material']['violations']==[])
            self.assertTrue(all(p.blocks.get(tuple(r['support']),AIR)!=AIR for r in p.supports))
            fields.append(tuple(sorted(p.blocks.items())))
        self.assertEqual(len(set(fields)),4)

    def test_new_recipe_context_cannot_replace_or_leak_into_frozen_registry(self):
        before=dict(RECIPES)
        with n.source_recipes():self.assertTrue(set(n.EXTRA)<=set(RECIPES))
        self.assertEqual(RECIPES,before)
        with self.assertRaisesRegex(RuntimeError,'fixture'):
            with n.source_recipes():raise RuntimeError('fixture')
        self.assertEqual(RECIPES,before)

    def test_memory_refusal_ends_before_archive_or_world_path_work(self):
        with patch.object(n,'guard',return_value={'allowed':True}),patch.object(n,'reader_budget',side_effect=UserError('memory gate')),patch.object(n.fill,'private_home')as private:
            with self.assertRaisesRegex(UserError,'memory gate'):n.prepare('unused','unused','unused','unused','unused')
            private.assert_not_called()
