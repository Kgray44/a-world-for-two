"""Tiny pure saved-land contracts; no native runtime, MCA or growth actions."""
from unittest import TestCase
import time
from tools.artistic_whole_bank_forest import exact_graph, cliffs, walking, fine_hiking_line, SOILS, DOMAIN, CHECKPOINT_SHA
from tools.artistic_forest_walks import component


class Ground:
    def __init__(self,changes=None,states=None):self.changes=changes or {};self.states=states or {};self.started=time.monotonic()
    def column(self,x,z):return {'x':x,'z':z,'kind':'dry','surface_y':64,'state':'minecraft:grass_block'}|self.changes.get((x,z),{})
    def state(self,x,y,z):return self.states.get((x,y,z),'minecraft:air')
    def check(self):pass


class WholeBankContracts(TestCase):
    def test_one_metre_water_gap_never_merges_opposite_riverbank(self):
        wire=Ground({(4,0):{'kind':'water'}})
        _,graph,edges=exact_graph(wire,(0,0,8,0))
        self.assertEqual(component(graph,(0,0)),{(0,0)})
        self.assertEqual(edges,{})

    def test_nonfull_gap_remains_unknown_instead_of_native_generation(self):
        _,graph,edges=exact_graph(Ground({(7,0):{'kind':'unknown'}}),(0,0,8,0))
        self.assertFalse(graph[(0,0)]);self.assertFalse(edges)

    def test_unaligned_or_oversized_graph_refuses(self):
        for bounds in ((1,0,8,8),(8,0,0,0),(0,0,8192,8192)):
            with self.assertRaisesRegex(Exception,'Finite aligned'):exact_graph(Ground(),bounds)

    def test_cliff_is_a_full_actual_profile_with_direction_and_lower_point(self):
        wire=Ground({(x,0):{'surface_y':64+2*x} for x in range(9)})
        _,graph,edges=exact_graph(wire,(0,0,8,0));rows=cliffs(wire,edges,component(graph,(0,0)))
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['lower_observed_ground'],[0,64,0])
        self.assertEqual(rows[0]['higher_observed_ground'],[8,80,0])
        self.assertEqual(len(rows[0]['one_metre_ground_profile']),9)

    def test_rock_cliff_does_not_become_walkable_or_receive_terrain_fill(self):
        wire=Ground({(x,0):{'surface_y':64+2*x} for x in range(9)})
        cells,graph,edges=exact_graph(wire,(0,0,8,0))
        with self.assertRaisesRegex(Exception,'No actual saved'):walking(wire,cells,edges,component(graph,(0,0)),set())

    def test_protected_air_and_body_width_block_a_path(self):
        for wire,protected in ((Ground(),{(4,1)}),(Ground({(4,-1):{'kind':'water'}}),set()),(Ground(states={(4,66,1):'minecraft:oak_log[axis=y]'}),set())):
            cells,graph,edges=exact_graph(wire,(0,0,8,0))
            with self.assertRaisesRegex(Exception,'No actual saved'):walking(wire,cells,edges,component(graph,(0,0)),protected)

    def test_soil_candidate_does_not_erase_rock_or_claim_growth(self):
        self.assertIn('minecraft:grass_block',SOILS);self.assertNotIn('minecraft:stone',SOILS)
        self.assertNotIn('minecraft:water',SOILS)
        self.assertLessEqual(((DOMAIN[2]-DOMAIN[0])//8+1)*((DOMAIN[3]-DOMAIN[1])//8+1),8192)
        self.assertEqual(CHECKPOINT_SHA,'b8495b677653c31077036faad10f553b432dcb173cd8964c8bb48e4674bd35f7')

    def test_fine_hike_is_named_narrow_and_preserves_each_actual_step(self):
        wire=Ground({(1,0):{'surface_y':65},(2,0):{'surface_y':66}})
        result=fine_hiking_line(wire,(0,0),(2,0),set(),(0,0,2,0))
        self.assertEqual(result['horizontal_metres'],2);self.assertEqual(result['maximum_actual_step'],1)
        self.assertEqual(result['width_columns'],1);self.assertEqual(result['body_height'],2)
        self.assertFalse(result['native_walking']);self.assertIn('not a3wide',result['status'])

    def test_fine_hike_does_not_fill_water_or_invent_steps_across_two_block_cliff(self):
        for changes in ({(1,0):{'kind':'water'}},{(1,0):{'surface_y':66}}):
            result=fine_hiking_line(Ground(changes),(0,0),(2,0),set(),(0,0,2,0))
            self.assertTrue(result['status'].startswith('UNRESOLVED'));self.assertNotIn('nodes_xz',result)

    def test_fine_hike_preserves_protected_cells_and_real_two_high_body(self):
        cases=((Ground(),{(1,0)}),(Ground(states={(1,66,0):'minecraft:oak_leaves[distance=1,persistent=false]'}),set()))
        for wire,protected in cases:
            result=fine_hiking_line(wire,(0,0),(2,0),protected,(0,0,2,0))
            self.assertTrue(result['status'].startswith('UNRESOLVED'))

    def test_fine_hike_budget_returns_unknown_not_a_shorter_fake_route(self):
        result=fine_hiking_line(Ground(),(0,0),(2,0),set(),(0,0,2,0),max_nodes=0)
        self.assertIn('exhausted',result['status']);self.assertNotIn('nodes_xz',result)
