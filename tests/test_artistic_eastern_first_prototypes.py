"""Small original footing cases; no saved/native world claims."""
import unittest
from control_room.common import UserError
from tools.artistic_eastern_first_prototypes import profile


class EasternPrototypeFootingTests(unittest.TestCase):
    def test_authored_plinth_air_is_not_mistaken_for_missing_ground_below_it(self):
        calls=[]
        def look(x,y,z):calls.append(y);return'minecraft:grass_block[snowy=false]'if y==62 else'minecraft:air'
        result=profile(look,0,0,63)
        self.assertEqual(calls,[62]);self.assertEqual(result['fill_positions'],[])

    def test_only_literal_gap_cells_are_filled_and_profile_reaches_real_ground(self):
        states={62:'minecraft:air',61:'minecraft:short_grass',60:'minecraft:dirt'}
        result=profile(lambda x,y,z:states[y],4,5,63)
        self.assertEqual(result['fill_positions'],[(4,62,5),(4,61,5)])
        self.assertEqual(result['natural_terminal'],(4,60,5,'minecraft:dirt'))

    def test_existing_solid_supports_stay_literal_and_gravity_gets_grounded(self):
        states={62:'minecraft:gravel',61:'minecraft:air',60:'minecraft:cobblestone',59:'minecraft:stone'}
        result=profile(lambda x,y,z:states[y],0,0,63)
        self.assertEqual(result['fill_positions'],[(0,61,0)])
        self.assertEqual(len(result['stack']),4)

    def test_water_unknown_and_unreviewed_blocks_refuse_without_crossing(self):
        for state in('minecraft:water[level=0]',None,'unreviewed:opaque_block'):
            with self.subTest(state=state),self.assertRaises(UserError):profile(lambda x,y,z:state,0,0,63)

    def test_finite_ground_search_never_becomes_unbounded_excavation(self):
        calls=[]
        def look(x,y,z):calls.append(y);return'minecraft:air'
        with self.assertRaises(UserError):profile(look,0,0,63,depth=4)
        self.assertEqual(calls,[62,61,60,59])


if __name__=='__main__':unittest.main()
