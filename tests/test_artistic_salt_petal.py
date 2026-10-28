import json
from pathlib import Path
import unittest
from control_room.common import UserError
from tools.artistic_salt_petal import NAME,construct,check,key


class SaltPetalSourceTests(unittest.TestCase):
    def setUp(self):
        self.p=construct(json.loads((Path(__file__).parent/'fixtures/salt_petal_registry.json').read_text()))

    def test_one_hooked_shop_and_attached_house_are_three_real_scenes(self):
        proof=check(self.p)
        self.assertEqual(proof['rooms'],3)
        self.assertEqual(len(self.p.main),1)
        self.assertIn((12,2),self.p.main[NAME])
        self.assertIn((7,11),self.p.main[NAME])
        self.assertNotIn((0,0),self.p.main[NAME])
        for z in range(2,6):
            for y in (1,2,3):
                self.assertNotIn(key(self.p.blocks[11,y,z]),{'minecraft:gray_terracotta','minecraft:stripped_dark_oak_log'})
                self.assertEqual(key(self.p.blocks[12,y,z]),'mcwwindows:dark_oak_plank_window')
            self.assertEqual(self.p.blocks[11,3,z],'minecraft:air')
        self.assertTrue(any(r['kind']=='stairs' for r in self.p.routes))

    def test_lush_real_contained_plants_and_practical_work_objects(self):
        plants=[(q,s) for q,s in self.p.blocks.items() if key(s).startswith(('minecraft:potted_','fishofthieves:potted_'))]
        self.assertEqual(len(plants),16)
        self.assertGreaterEqual(sum(key(s).startswith('fishofthieves:') for q,s in plants),8)
        self.assertEqual(sum(key(s)=='minecraft:lantern' for s in self.p.blocks.values()),4)
        self.assertTrue({'minecraft:water_cauldron','minecraft:crafting_table','farmersdelight:cutting_board'}<={key(s) for s in self.p.blocks.values()})
        self.assertFalse(any('Items:' in nbt or 'NoAI' in nbt or 'Owner' in nbt for nbt in self.p.tags.values()))

    def test_real_base_feet_and_roof_tie_support_the_modeled_detail(self):
        for x in (8,10):self.assertEqual(key(self.p.blocks[x,0,12]),'minecraft:stone_bricks')
        for x in range(1,7):self.assertEqual(self.p.blocks[x,8,4],'minecraft:dark_oak_planks')
        self.assertEqual(check(self.p)['material_rule']['violations'],[])
        self.p.blocks[9,1,8]='minecraft:potted_fern'
        with self.assertRaisesRegex(UserError,'human circulation'):check(self.p)

    def test_no_floating_plant_acceptance(self):
        plant=next(q for q,s in self.p.blocks.items() if key(s).startswith('fishofthieves:potted_'))
        x,y,z=plant;self.p.blocks[x,y-1,z]='minecraft:air'
        with self.assertRaisesRegex(UserError,'plant pot requires its actual'):check(self.p)

    def test_circulation_cannot_erase_the_declared_real_door(self):
        x,y,z=self.p.entries[0]['door']
        self.assertTrue(key(self.p.blocks[x,y,z]).endswith('_door'))
        self.assertTrue(key(self.p.blocks[x,y+1,z]).endswith('_door'))
        self.p.blocks[x,y,z]='minecraft:air'
        with self.assertRaisesRegex(UserError,'retain both native halves'):check(self.p)


if __name__=='__main__':unittest.main()
