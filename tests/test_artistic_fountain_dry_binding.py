import unittest
from control_room.common import UserError
from tools.artistic_fountain_dry_binding import compare_owned


class CurrentDryFountainBindingTests(unittest.TestCase):
    def test_real_default_and_join_properties_can_be_preserved(self):
        self.assertEqual(compare_owned('handcrafted:dark_oak_side_table',
            'handcrafted:dark_oak_side_table[color=none,facing=north,waterlogged=false]'),
            'handcrafted:dark_oak_side_table[color=none,facing=north,waterlogged=false]')

    def test_current_material_or_core_state_cannot_be_forged(self):
        for wanted,actual in (
            ('minecraft:water[level=0]','minecraft:ice'),
            ('minecraft:water[level=0]','create:fluid_pipe[waterlogged=true]'),
            ('minecraft:lever[powered=false]','minecraft:lever[powered=true]'),
            ('dawnoftimebuilder:marble_statue_mars[multiblock=0]',
             'dawnoftimebuilder:marble_statue_mars[multiblock=2]')):
            with self.subTest(wanted=wanted),self.assertRaises(UserError):compare_owned(wanted,actual)


if __name__=='__main__':unittest.main()
