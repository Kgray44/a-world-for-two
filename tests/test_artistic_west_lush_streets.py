"""Small source boundary checks, never a substitute for Native plant survival."""
import unittest

from control_room.common import UserError
from tools import artistic_west_lush_streets as lush


class WestLushStreetBoundaryTests(unittest.TestCase):
    def lookup(self, changes=None):
        changes=changes or {}
        def read(p):
            if p in changes:return changes[p]
            return 'minecraft:stone'if p[1]==63 else'minecraft:dirt'if p[1]<=62 else'minecraft:air'
        return read

    def test_gravel_requires_explicit_extension_and_a_real_dry_stack(self):
        read=self.lookup({(1020,63,-1270):'minecraft:gravel'})
        self.assertIsNone(lush.ground_candidate(read,1020,-1270,set(),set(),set())[0])
        field,reason=lush.ground_candidate(read,1020,-1270,set(),set(),set(),
                                          accepted_floor={'minecraft:gravel'})
        self.assertIsNone(reason)
        self.assertEqual(field[(1020,63,-1270)],'minecraft:gravel')
        self.assertEqual(field[(1020,62,-1270)],'minecraft:dirt')
        for bad in ('minecraft:water[level=0]','minecraft:air',None):
            with self.subTest(bad=bad):
                self.assertIsNone(lush.ground_candidate(self.lookup({(1020,62,-1270):bad}),
                    1020,-1270,set(),set(),set())[0])

    def test_buildings_inventory_occupied_body_and_transport_are_held(self):
        p=(1020,63,-1270)
        for main,transport,bes in (({(1020,-1270)},set(),set()),
                (set(),{(1020,-1270)},set()),(set(),set(),{p})):
            self.assertIsNone(lush.ground_candidate(self.lookup(),1020,-1270,main,transport,bes)[0])
        self.assertIsNone(lush.ground_candidate(self.lookup({(1020,65,-1270):'minecraft:lantern'}),
            1020,-1270,set(),set(),set())[0])

    def test_rooted_edge_keeps_two_literal_clear_columns_beyond_plants(self):
        args=(1020,-1270,(1,0,0),set(),set(),set(),set(),set())
        proof=lush.rooted_edge(self.lookup(),*args)
        self.assertTrue(proof)
        self.assertIn((1022,65,-1270),proof)
        self.assertIn((1020,62,-1270),proof)
        for bad in('minecraft:water[level=0]','minecraft:air',None):
            self.assertIsNone(lush.rooted_edge(self.lookup({(1020,62,-1270):bad}),*args))
        blocked=self.lookup({(1022,65,-1270):'minecraft:barrel[facing=up,open=false]'})
        self.assertIsNone(lush.rooted_edge(blocked,*args))
        self.assertIsNone(lush.rooted_edge(self.lookup(),1020,-1270,(1,0,0),
            set(),set(),{(1020,-1270)},set(),set()))
        self.assertIsNone(lush.rooted_edge(self.lookup(),1020,-1270,(1,0,0),
            set(),set(),set(),{(1020,-1270)},set()))

    def test_leaf_drape_uses_real_adjacent_log_distance(self):
        a=(1020,70,-1270);b=(1021,70,-1270)
        leaves={a:'minecraft:oak_leaves',b:'minecraft:azalea_leaves'}
        read=self.lookup({(1019,70,-1270):'minecraft:stripped_dark_oak_log[axis=y]'})
        self.assertEqual(lush.leaf_distances(leaves,read),{a:1,b:2})
        bad=self.lookup({(1019,70,-1270):'unknown:unqualified_log'})
        with self.assertRaises(UserError):lush.leaf_distances(leaves,bad)

    def test_saved_leaf_distance_is_retained_as_a_native_boundary(self):
        p=(1020,70,-1270)
        read=self.lookup({(1019,70,-1270):'minecraft:oak_leaves[distance=3,persistent=false,waterlogged=false]'})
        self.assertEqual(lush.leaf_distances({p:'minecraft:azalea_leaves'},read)[p],4)

    def test_ground_and_greenery_are_separate_source_operations(self):
        self.assertNotEqual(lush.GROUND_PACKET[1],lush.GRAVEL_PACKET[1])
        self.assertEqual(lush.FIRST,(1018,-1277,1046,-1248))
        self.assertEqual(lush.WEST[2],1185)
        self.assertNotIn('minecraft:gravel',lush.GRAY)


if __name__=='__main__':unittest.main()
