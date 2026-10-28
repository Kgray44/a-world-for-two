"""Regression for the observed long uninterrupted drainage-line failure."""
import unittest
from tools.artistic_north_bank_west_connections import paving
from tools.artistic_materials import require_outdoor_rule


class PavingJoints(unittest.TestCase):
    def test_long_north_south_drain_has_real_cross_joint_breaks(self):
        blocks={(x,63,z):paving(x,z) for x in (1072,1073) for z in range(-1280,-1200)}
        require_outdoor_rule(blocks,'eighty-metre two-wide north-south lane')
    def test_long_east_west_lane_has_real_bay_breaks(self):
        blocks={(x,63,z):paving(x,z) for x in range(1000,1160) for z in (-1257,-1256)}
        require_outdoor_rule(blocks,'long east-west quay lane')
    def test_crossing_material_is_an_actual_junction_not_facing_noise(self):
        self.assertNotEqual(paving(1072,-1248),paving(1072,-1247))
        self.assertNotEqual(paving(1072,-1247),paving(1073,-1247))


if __name__=='__main__':unittest.main()
