"""Natural support, preserved-tree and actual four-cell grade regressions.

These fixtures exercise source admission. They do not replace native collision,
normal stair joins, a genuine walk or visual acceptance.
"""
import unittest

from control_room.common import UserError
from tools.artistic_north_bank_west_court_routes import (
    harbor_stairs, compatible_surfaces as west_grade, walkable_floor as west_floor,
)
from tools.artistic_north_bank_east_shore_routes import (
    compatible_surfaces as east_grade, walkable_floor as east_floor,
)


class SavedStairField:
    def __init__(self):
        self.entities=set()
        self.blocks={(x,63,z):'minecraft:grass_block[snowy=false]'
                     for x in (1220,1221) for z in (-1261,-1260)}
        for x in (1220,1221):
            for z,ys in ((-1261,range(64,68)),(-1260,range(64,69))):
                for y in ys:self.blocks[x,y,z]='minecraft:air'

    def state(self,*q):return self.blocks.get(q)


class AdditionalDryRoutes(unittest.TestCase):
    def test_real_two_rise_stairs_preserve_every_original_support(self):
        t=SavedStairField();snapshot=dict(t.blocks)
        placed,before,supports=harbor_stairs(t,{},set())
        self.assertEqual(t.blocks,snapshot)
        self.assertTrue(all(q[1]==63 for q in supports))
        self.assertFalse(set(placed)&set(supports))
        self.assertEqual(before,{q:snapshot[q] for q in placed})
        for x in (1220,1221):
            self.assertIn('stairs[facing=south',placed[x,64,-1261])
            self.assertIn('stairs[facing=south',placed[x,65,-1260])
            self.assertEqual(placed[x,64,-1260],'minecraft:stone_bricks')

    def test_tree_water_unknown_and_saved_be_refuse_before_any_change(self):
        for obstruction in ('minecraft:oak_leaves[distance=1,persistent=false,waterlogged=false]',
                            'minecraft:water[level=0]',None):
            with self.subTest(obstruction=obstruction):
                t=SavedStairField();t.blocks[1220,65,-1261]=obstruction;before=dict(t.blocks)
                with self.assertRaises(UserError):harbor_stairs(t,{},set())
                self.assertEqual(t.blocks,before)
        t=SavedStairField();t.entities.add((1220,65,-1261))
        with self.assertRaises(UserError):harbor_stairs(t,{},set())

    def test_authored_air_cable_and_water_support_are_not_free_targets(self):
        t=SavedStairField()
        with self.assertRaises(UserError):harbor_stairs(t,{(1220,64,-1261):'minecraft:air'},set())
        with self.assertRaises(UserError):harbor_stairs(t,{}, {(1220,64,-1261)})
        t.blocks[1220,63,-1261]='minecraft:water[level=0]'
        with self.assertRaises(UserError):harbor_stairs(t,{},set())

    def test_two_wide_grade_has_no_hidden_cliff_or_teleport(self):
        for grade in (west_grade,east_grade):
            self.assertTrue(grade((63,63,63,63),(63,63,64,64)))
            self.assertTrue(grade((63,63,64,64),(64,64,65,65)))
            self.assertFalse(grade((63,63,63,63),(65,65,65,65)))
            self.assertFalse(grade((63,65,63,65),(63,65,63,65)))
            self.assertFalse(grade((63,),(63,)))

    def test_retained_furniture_cannot_be_a_public_lane_endpoint(self):
        for floor in (west_floor,east_floor):
            self.assertTrue(floor('minecraft:polished_andesite'))
            self.assertFalse(floor('supplementaries:planter[extended=false,waterlogged=false]'))
            self.assertFalse(floor('minecraft:barrel[facing=up,open=false]'))
            self.assertFalse(floor('handcrafted:dark_oak_bench[color=none,facing=north,shape=single,waterlogged=false]'))


if __name__=='__main__':unittest.main()
