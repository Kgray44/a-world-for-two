"""Coastal gravel must end at real stable ground, not water or a gap."""
import unittest
from tools.artistic_ground_stability import natural_mount


class GroundStabilityTests(unittest.TestCase):
    def test_two_visibly_solid_gravel_cells_over_source_water_refuse(self):
        cells={63:'minecraft:gravel',62:'minecraft:gravel',61:'minecraft:water[level=0]',60:'minecraft:stone'}
        result=natural_mount(lambda x,y,z:cells.get(y),1000,-1276)
        self.assertFalse(result['stable'])
        self.assertEqual(result['first_non_gravity'][1],61)
        self.assertEqual(len(result['stack']),2)

    def test_entire_gravel_chain_to_qualified_native_ore_is_retained(self):
        cells={62:'minecraft:gravel',61:'minecraft:gravel',60:'minecraft:gravel',59:'minecraft:iron_ore'}
        result=natural_mount(lambda x,y,z:cells.get(y),0,0)
        self.assertTrue(result['stable'])
        self.assertEqual(result['gravity_cells'],3)
        self.assertEqual([row[1]for row in result['stack']],[62,61,60,59])

    def test_unknown_gap_unqualified_mod_and_finite_bottom_fail_closed(self):
        for end in(None,'minecraft:air','example:possibly_falling_chalk'):
            self.assertFalse(natural_mount(lambda x,y,z:'minecraft:gravel'if y==62 else end,0,0)['stable'])
        result=natural_mount(lambda x,y,z:'minecraft:gravel',0,0,top=62,bottom=60)
        self.assertFalse(result['stable']);self.assertEqual(len(result['stack']),3)
        with self.assertRaises(ValueError):natural_mount(lambda*x:'minecraft:stone',0,0,top=70)


if __name__=='__main__':unittest.main()
