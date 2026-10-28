"""Tiny authored-stair invariants, no private archive or native game calls."""
from unittest import TestCase
from tools.artistic_cliff_access import stair_search


class Ground:
    def __init__(self,rows=None,states=None):self.rows=rows or {};self.states=states or {};self.entities=set()
    def column(self,x,z):return {'x':x,'z':z,'kind':'dry','surface_y':64,'state':'minecraft:grass_block'}|self.rows.get((x,z),{})
    def state(self,x,y,z):
        row=self.column(x,z)
        return self.states.get((x,y,z),row['state'] if y==row['surface_y'] else 'minecraft:stone' if y<row['surface_y'] else 'minecraft:air')


class CliffAccessContracts(TestCase):
    def test_normal_rooted_walk_has_no_excavation_or_generated_support(self):
        nodes,report=stair_search(Ground(),set(),(1080,65,-1072),(1082,65,-1072),max_nodes=30)
        self.assertIsNotNone(nodes);self.assertEqual(len(nodes),3)
        self.assertTrue(all(r['support']['kind']=='native_ground' and not r['bounded_natural_step_cuts'] for r in nodes))

    def test_existing_dirt_path_is_read_only_walkable_not_a_clear_order(self):
        t=Ground({(1081,-1072):{'kind':'retained_object','state':'minecraft:dirt_path'}})
        nodes,_=stair_search(t,set(),(1080,65,-1072),(1082,65,-1072),max_nodes=30)
        self.assertTrue(nodes[1]['retained_existing_dirt_path_unchanged'])
        self.assertFalse(nodes[1]['bounded_natural_step_cuts'])

    def test_two_cell_shallow_rock_step_allowed_but_deeper_cut_is_not(self):
        t=Ground({(1081,-1072):{'surface_y':66}})
        nodes,_=stair_search(t,set(),(1080,65,-1072),(1081,65,-1072),max_nodes=30)
        self.assertEqual(len(nodes[-1]['bounded_natural_step_cuts']),2)
        self.assertEqual(nodes[-1]['support']['kind'],'shallow_fitted_ground_steps')
        nodes,_=stair_search(t,set(),(1080,65,-1072),(1081,64,-1072),max_nodes=30)
        self.assertIsNone(nodes)

    def test_tree_ore_and_saved_BE_are_not_a_terrain_cut_exception(self):
        for value in ('minecraft:oak_log[axis=y]','minecraft:oak_leaves[distance=1,persistent=false]','minecraft:iron_ore'):
            t=Ground({(1081,-1072):{'surface_y':66}},states={(1081,65,-1072):value})
            self.assertIsNone(stair_search(t,set(),(1080,65,-1072),(1081,65,-1072),max_nodes=30)[0])

    def test_earlier_route_body_cannot_receive_new_pier_or_floor(self):
        prior={(1081,66,-1072),(1081,67,-1072),(1081,68,-1072)}
        self.assertIsNone(stair_search(Ground(),set(),(1080,65,-1072),(1081,68,-1072),max_nodes=30,prior_body=prior)[0])

    def test_protected_architecture_cannot_become_scenic_step(self):
        self.assertIsNone(stair_search(Ground(),{(1081,-1072)},(1080,65,-1072),(1081,65,-1072),max_nodes=30)[0])
