"""Prospective structural width contracts, not native collision/art acceptance."""
from types import SimpleNamespace
import unittest

from control_room.common import UserError
from tools.artistic_eastern_fresh_interiors import width_review
from tools.artistic_eastern_open_wings import design


def room(width,depth,blocks=None,vertical=None):
    box=(0,0,width-1,depth-1)
    return SimpleNamespace(
        mass_fields=[{(x,z)for x in range(width)for z in range(depth)}],
        spec={'masses':[{'bounds_xz':box}]},local_box=lambda m:m['bounds_xz'],
        origin=(0,0,0),floor_levels=[[0]],blocks=blocks or{},vertical=vertical or[])


class FutureInteriorWidthTests(unittest.TestCase):
    def test_compact_three_is_hard_pass_while_five_remains_a_target(self):
        proof=width_review(room(5,5))
        self.assertTrue(proof['hard_minimum_3_passed'])
        self.assertEqual(proof['comfortable_target'],5)
        self.assertTrue(proof['floors'][0]['compact3_or4_design_judgment'])

    def test_long_two_wide_enclosed_room_cannot_be_called_service(self):
        with self.assertRaisesRegex(UserError,'below3'):
            width_review(room(4,18))

    def test_stair_exception_cannot_consume_a_tiny_regular_room(self):
        model=room(5,5,{(1,1,1):'minecraft:dark_oak_stairs[facing=south,half=bottom,shape=straight,waterlogged=false]'},
                   [{'kind':'native ordinary stair','blocks':[[1,1,1],[1,2,2]]}])
        with self.assertRaisesRegex(UserError,'real3x3 clear core'):
            width_review(model)

    def test_an_unrelated_pillar_cannot_borrow_the_stair_exception(self):
        with self.assertRaisesRegex(UserError,'outside literal stair feature'):
            width_review(room(5,8,{(1,1,1):'minecraft:stripped_dark_oak_log[axis=y]'}))

    def test_narrow_wing_is_removed_from_normal_rooms_not_renamed(self):
        original={'masses':[{'bounds_xz':[0,0,8,11],'storeys':2},
                            {'bounds_xz':[9,0,11,7],'storeys':2}]}
        new,features,changes=design(original)
        self.assertEqual(len(new['masses']),1)
        self.assertEqual(len(features),1)
        self.assertEqual(features[0]['original_mass'],1)
        self.assertEqual(len(original['masses']),2)
        self.assertIn('open trade bays',changes[0]['after'])


if __name__=='__main__':
    unittest.main()
