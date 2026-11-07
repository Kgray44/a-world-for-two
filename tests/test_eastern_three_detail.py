"""Geometry/preservation contracts only; these are not native art or survival."""
import json
from pathlib import Path
import unittest

from control_room.common import UserError
from tools.artistic_eastern_first_three_detail import construct, check_preservation, AIR


class EasternThreeDetailTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = json.loads((Path(__file__).resolve().parents[1]/'proposals/eastern-three-detail/registry-properties.json').read_text())

    def setUp(self):
        self.blocks, self.tags, self.walks, self.mounts, self.plants, self.objects = construct(self.registry)

    def test_distinct_scenes_have_real_supports_and_clear_walking_body(self):
        check_preservation(self.blocks,self.walks,self.mounts,{},set())
        self.assertEqual(len(self.walks),38)
        self.assertEqual(len(self.plants),4)
        self.assertEqual(sum('bench' in v for v in self.blocks.values()),3)

    def test_authored_existing_air_is_preserved_as_strictly_as_a_wall(self):
        q=next(iter(self.blocks))
        with self.assertRaisesRegex(UserError,'existing compound cell'):
            check_preservation(self.blocks,self.walks,self.mounts,{q:AIR},set())

    def test_any_future_main_footprint_is_excluded_at_every_height(self):
        x,y,z=next(iter(self.blocks))
        with self.assertRaisesRegex(UserError,'future building floor'):
            check_preservation(self.blocks,self.walks,self.mounts,{}, {(x,z)})

    def test_a_projecting_sign_cannot_enter_two_high_walking_body(self):
        self.blocks[1378,65,-1124]='minecraft:dark_oak_wall_sign[facing=west,waterlogged=false]'
        with self.assertRaisesRegex(UserError,'two-high headroom'):
            check_preservation(self.blocks,self.walks,self.mounts,{},set())

    def test_mount_loss_refuses_instead_of_leaving_a_floating_detail(self):
        del self.blocks[self.mounts[1359,66,-1161]]
        with self.assertRaisesRegex(UserError,'real new support'):
            check_preservation(self.blocks,self.walks,self.mounts,{},set())

    def test_only_new_waxed_sign_tags_exist_no_stock_or_automatic_collectors(self):
        self.assertEqual(len(self.tags),3)
        for q,tag in self.tags.items():
            self.assertIn('wall_sign',self.blocks[q])
            self.assertIn('is_waxed:1b',tag)
            self.assertNotIn('Items',tag)
            self.assertNotIn('LootTable',tag)
        self.assertFalse(any('planter' in v or 'sapling' in v or 'hopper' in v for v in self.blocks.values()))

    def test_every_real_native_shrub_has_both_halves_on_dirt(self):
        for (x,y,z),kind in self.plants.items():
            self.assertEqual(self.blocks[x,y,z],'minecraft:dirt')
            self.assertIn(kind,self.blocks[x,y+1,z])
            if kind.endswith('_shrub'):
                self.assertIn('half=lower',self.blocks[x,y+1,z])
                self.assertIn('half=upper',self.blocks[x,y+2,z])


if __name__=='__main__':
    unittest.main()
