"""Pure tiny geography/route contracts; no native, MCA, planting or account calls."""
from pathlib import Path
from unittest import TestCase
import time
from tools.artistic_forest_walks import body_witness,component,land_graph,prepare,route
from tools.artistic_south_extent import REGIONS,MAX_RAW,cliff_bands


class Terrain:
 def __init__(self,columns=None,states=None):self.columns=columns or {};self.states=states or {};self.started=time.monotonic()
 def column(self,x,z):return {'x':x,'z':z,'kind':'dry','surface_y':64,'state':'minecraft:grass_block'}|self.columns.get((x,z),{})
 def state(self,x,y,z):return self.states.get((x,y,z),'minecraft:air')


class ForestWalkContracts(TestCase):
 def test_narrow_water_between_dry_coarse_nodes_never_connects_banks(self):
  t=Terrain({(4,0):{'kind':'water'}});cells,adj,edges=land_graph(t,(0,0,8,0))
  self.assertEqual(set(cells),{(0,0),(8,0)});self.assertEqual(component(adj,(0,0)),{(0,0)})
  self.assertEqual(edges,{})

 def test_nonfull_unknown_in_between_is_not_a_dry_link(self):
  t=Terrain({(7,0):{'kind':'unknown'}});_,adj,_=land_graph(t,(0,0,8,0))
  self.assertEqual(adj[(0,0)],[])

 def test_missing_reviewed_anchor_cannot_silently_choose_another_shore(self):
  with self.assertRaisesRegex(Exception,'anchor is absent'):component({(8,0):[]},(0,0))

 def test_candidate_grid_has_an_exact_finite_node_budget(self):
  with self.assertRaisesRegex(Exception,'Finite eight-metre'):land_graph(Terrain(),(0,0,8192,8192))
  with self.assertRaisesRegex(Exception,'Finite eight-metre'):land_graph(Terrain(),(8,0,0,8))

 def test_full_width_checks_water_not_only_centerline(self):
  t=Terrain({(4,1):{'kind':'water'}})
  self.assertIsNone(body_witness(t,[(x,0) for x in range(9)],set()))

 def test_protected_air_architecture_and_route_skirts_are_not_land_permissions(self):
  self.assertIsNone(body_witness(Terrain(),[(x,0) for x in range(9)],{(3,-1)}))

 def test_existing_trunk_or_low_leaf_is_not_cleared_to_invent_a_walk(self):
  for value in ('minecraft:oak_log[axis=y]','minecraft:oak_leaves[distance=1,persistent=false,waterlogged=false]'):
   self.assertIsNone(body_witness(Terrain(states={(5,66,-1):value}),[(x,0) for x in range(9)],set()))

 def test_three_high_body_is_inspected_above_each_actual_ground(self):
  self.assertIsNone(body_witness(Terrain(states={(8,67,0):'minecraft:stone'}),[(x,0) for x in range(9)],set()))
  rows=body_witness(Terrain(),[(x,0) for x in range(9)],set())
  self.assertEqual(len(rows),27);self.assertTrue(all(len(v['standing_and_headroom'])==3 for v in rows))

 def test_steep_or_uneven_ground_does_not_receive_a_flattening_fallback(self):
  self.assertIsNone(body_witness(Terrain({(4,0):{'surface_y':67}}),[(x,0) for x in range(9)],set()))

 def test_path_search_keeps_disconnected_targets_pending(self):
  adj={(0,0):[(8,0)],(8,0):[(0,0)],(24,0):[]}
  self.assertIsNone(route(adj,(0,0),(24,0),lambda a,b:8))
  self.assertEqual(route(adj,(0,0),(8,0),lambda a,b:8),[(0,0),(8,0)])

 def test_cliff_observation_does_not_bridge_unknown_profile_samples(self):
  rows=[{'x':1008,'z':z,'kind':kind,'surface_y':height} for z,kind,height in ((-1040,'dry',88),(-1036,'unknown',None),(-1032,'dry',113),(-1028,'dry',123))]
  self.assertEqual(cliff_bands(rows),[])
  rows=[{'x':1008,'z':-1040+4*n,'kind':'dry','surface_y':y} for n,y in enumerate((88,97,113,123))]
  bands=cliff_bands(rows);self.assertEqual(len(bands),1);self.assertEqual(bands[0]['observed_low_y'],88)
  self.assertIn('denser survey',bands[0]['meaning'])

 def test_six_specific_regions_and128mib_bound_are_explicit(self):
  self.assertEqual(set(REGIONS),{(x,z) for x in (1,2) for z in (-3,-2,-1)})
  self.assertEqual(MAX_RAW,128*1024**2)

 def test_official_home_refuses_before_source_or_world_reads(self):
  with self.assertRaisesRegex(Exception,'Owned artistic home only'):prepare(Path(r'D:\A World for Two'),'fictional','f'*64)
