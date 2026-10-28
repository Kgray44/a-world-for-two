import json
from pathlib import Path
import unittest

from control_room.common import UserError
from tools.artistic_west_r2_refine import AIR,construct,check,key


class WestPhotoRefinementTests(unittest.TestCase):
    def setUp(self):
        self.d=construct(json.loads((Path(__file__).parent/'fixtures/west_r2_refine_registry.json').read_text()))

    def test_actual_depth_opens_old_wall_into_one_metre_projecting_glazing(self):
        self.assertEqual(check(self.d)['targets'],48)
        for x in (12,13):
            for y in (9,10,11):
                old=self.d.world((x,y,3));front=self.d.world((x,y,2))
                self.assertNotEqual(self.d.original[old],AIR)
                self.assertEqual(self.d.blocks[old],AIR)
                self.assertEqual(key(self.d.blocks[front]),'mcwwindows:dark_oak_plank_window')
        roof={q:s for q,s in self.d.original.items() if key(s).startswith('mcwroofs:')}
        self.assertFalse(set(roof)&set(self.d.blocks))

    def test_task_lights_and_contained_plants_keep_real_support_and_headroom(self):
        lamps=[q for q,s in self.d.blocks.items() if key(s)=='minecraft:lantern']
        self.assertEqual(len(lamps),2)
        for x,y,z in lamps:
            self.assertNotEqual(self.d.original.get((x,y+1,z),AIR),AIR)
            self.assertIn('hanging=true',self.d.blocks[x,y,z])
        pots=[s for s in self.d.blocks.values() if key(s).startswith('minecraft:potted_')]
        self.assertEqual(len(pots),4)
        self.assertFalse(any('sapling' in s or 'vine' in s for s in self.d.blocks.values()))
        row=self.d.supports[0];self.d.blocks[tuple(row['backing'])]=AIR
        with self.assertRaisesRegex(UserError,'No real structural support'):check(self.d)

    def test_existing_stock_furniture_and_routes_cannot_be_replaced(self):
        with self.assertRaisesRegex(UserError,'Never replace W3 furniture'):
            self.d.put(1,1,3,AIR,'incorrect attempt to erase the existing shop counter')
        self.d.blocks[self.d.world((3,1,6))]='minecraft:potted_fern'
        with self.assertRaisesRegex(UserError,'may obstruct the actual route'):check(self.d)


if __name__=='__main__':unittest.main()
