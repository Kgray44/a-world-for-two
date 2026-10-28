"""Small regressions for actual retained-objects and new tiny-home geometry."""
import unittest
from unittest.mock import patch

from control_room.common import UserError
from tests.test_artistic_tortuga_pair import literal
from tools.artistic_east_tortuga_cluster import Cluster, mender
from tools.artistic_tortuga_pair import validate, world_blocks


class EasternDensityTests(unittest.TestCase):
    def test_complete_mender_has_real_stair_and_stops_before_retained_oak(self):
        r={'items':['minecraft:'+s for s in ('string','leather','paper','bread')]}
        with patch('tools.artistic_tortuga_pair.state',side_effect=literal):
            p=mender(r);validate(p)
            field=world_blocks(p)
            # Exact saved oak extent:1254..1258/Y64..72/Z−1203..−1199.
            self.assertFalse(any(1254<=x<=1258 and 64<=y<=72 and -1203<=z<=-1199 for x,y,z in field))
            self.assertEqual(len(p.stairs),4)
            self.assertTrue(any('loom' in v for v in p.blocks.values()))
            self.assertTrue(any('bed[' in v for v in p.blocks.values()))
            x,y,z=p.stairs[2];p.blocks[x,y+1,z]='minecraft:stone'
            with self.assertRaisesRegex(UserError,'staircase'):validate(p)

    def test_new_infill_flag_does_not_authorize_old_tree_or_source_human_change(self):
        q=(1256,69,-1203)
        with patch('tools.artistic_east_tortuga_cluster.state',side_effect=literal):
            for old,source in (('minecraft:oak_leaves[distance=2,persistent=false,waterlogged=false]',{}),
                    ('minecraft:short_grass',{q:'minecraft:air'})):
                p=Cluster({}, {q:old},source,{},set(),set(),set())
                with self.subTest(old=old),self.assertRaises(UserError):p.put(q,'minecraft:air',new=True)
            p=Cluster({}, {q:'minecraft:short_grass'},{},{},set(),set(),set())
            p.put(q,'minecraft:air',new=True)
            self.assertEqual(p.soft_cleared,{q:'minecraft:short_grass'})


if __name__=='__main__':
    unittest.main()
