import unittest
from control_room.common import UserError
from tools.artistic_woodland_loop48 import NODES,line,measure,contour_link


class FlatTerrain:
    entities=set()
    def column(self,x,z):return {'kind':'dry','surface_y':0,'state':'minecraft:grass_block[snowy=false]'}
    def state(self,x,y,z):return 'minecraft:air'if y>0 else'minecraft:grass_block[snowy=false]'


class WoodlandLoop48Tests(unittest.TestCase):
    def test_closed_loop_has_literal_body_and_eighty_metres(self):
        field,center,supports,length=measure(FlatTerrain(),NODES,set())
        self.assertEqual(80,length);self.assertTrue(supports)
        self.assertTrue(all((x,1,z)in field and(x,3,z)in field for x,y,z in supports))

    def test_open_branch_cannot_be_labelled_a_loop(self):
        with self.assertRaises(UserError):measure(FlatTerrain(),NODES[:-1],set())
        with self.assertRaises(UserError):line((0,0),(1,1))

    def test_exact_future_flight_voxel_or_BE_is_preserved(self):
        with self.assertRaises(UserError):measure(FlatTerrain(),NODES,{(1072,2,-1072)})
        terrain=FlatTerrain();terrain.entities={(1072,0,-1072)}
        with self.assertRaises(UserError):measure(terrain,NODES,set())

    def test_contour_link_keeps_actual_endpoints_and_one_block_steps(self):
        route,derivation=contour_link(FlatTerrain(),set())
        self.assertEqual((1048,-1072),route[0]);self.assertEqual((1056,-1064),route[-1])
        self.assertEqual(16,len(route)-1)
        self.assertTrue(all(abs(a[0]-b[0])+abs(a[1]-b[1])==1 for a,b in zip(route,route[1:])))
        self.assertLessEqual(derivation['expanded_nodes'],256)


if __name__=='__main__':unittest.main()
