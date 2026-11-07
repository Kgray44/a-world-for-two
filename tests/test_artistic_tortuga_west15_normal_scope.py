import unittest
from control_room.common import UserError
from tools.artistic_tortuga_west15_normal_scope import normal_scope,validate_ridges


class West15NormalScopeTests(unittest.TestCase):
    def test_neighbor_ridge_is_selected_even_when_it_is_not_a_placement_target(self):
        a=(0,10,0);b=(0,10,1)
        full={a:'mcwroofs:dark_oak_top_roof[part=top_end_180]',b:'mcwroofs:dark_oak_top_roof[part=top_end_0]'}
        self.assertEqual(set(normal_scope(full,{a:full[a]},set())),{a,b})
        self.assertEqual(len(validate_ridges(full)),2)

    def test_full_expected_part_is_not_replaced_with_an_observed_stale_endcap(self):
        field={(0,10,z):'mcwroofs:spruce_top_roof[part='+part+']'for z,part in((-1,'top_end_180'),(0,'switched_0'),(1,'top_end_0'))}
        self.assertEqual(len(validate_ridges(field)),3)
        field[0,10,0]='mcwroofs:spruce_top_roof[part=top_end_0]'
        with self.assertRaises(UserError):validate_ridges(field)

    def test_existing_block_entities_cannot_enter_the_normal_update_scope(self):
        be=(0,1,0);window=(2,2,0);full={be:'minecraft:barrel[facing=up,open=false]',window:'mcwwindows:dark_oak_plank_window[facing=north,part=base]'}
        self.assertEqual(normal_scope(full,full,{be}),{window:full[window]})
