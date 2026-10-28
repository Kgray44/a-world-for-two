"""Actual planter-as-floor regression; no native collision acceptance."""
import unittest
from tools.artistic_north_bank_west_connections_r2 import walkable_floor,PAVED,paving
from tools.artistic_materials import require_outdoor_rule


class ActualWalkFloors(unittest.TestCase):
    def test_planter_and_furniture_are_never_street_supports(self):
        for value in ('supplementaries:planter[extended=false,waterlogged=false]',
            'minecraft:barrel[facing=up,open=false]','handcrafted:dark_oak_bench[color=none,facing=north,shape=single,waterlogged=false]',
            'minecraft:cartography_table','minecraft:grindstone[face=floor,facing=south]'):
            self.assertFalse(walkable_floor(value))
    def test_only_actual_paving_and_explicit_threshold_stairs_are_admitted(self):
        for value in PAVED:self.assertTrue(walkable_floor(value))
        self.assertTrue(walkable_floor('minecraft:stone_brick_stairs[facing=north,half=bottom,shape=straight,waterlogged=false]'))
        self.assertFalse(walkable_floor('minecraft:glass'))
    def test_real_drainage_joints_keep_the_long_lane_bounded(self):
        require_outdoor_rule({(x,63,z):paving(x,z) for x in (1072,1073) for z in range(-1280,-1200)},'R2 long actual paving')


if __name__=='__main__':unittest.main()
