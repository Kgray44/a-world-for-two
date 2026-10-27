"""Finite source custody/physical-relief checks, never native artistic proof."""
import json
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch
from control_room.common import UserError
from tools.artistic_secondary_depth import AIR,ENVELOPES,Secondary,payload,prepare,validate


class Snapshot:
 def __init__(self,blocks=None,protected=()):self.blocks=dict(blocks or {});self.protected=set(protected)
 def state(self,pos):return self.blocks.get(pos,AIR)


def fixture(blocks=None,protected=(),originals=None,routes=()):
 registry={'seed':'synthetic-only','world_path':'synthetic-only','blocks':{
  AIR:{},'minecraft:stone':{},'minecraft:white_terracotta':{},'minecraft:chain':{},
  'minecraft:dark_oak_stairs':{'facing':['north','south','east','west'],'half':['top','bottom'],'shape':['straight'],'waterlogged':['false']},
  'minecraft:dark_oak_slab':{'type':['top','bottom','double'],'waterlogged':['false']},
  'mythrais:slim_lintel_dark_oak':{'facing':['north','south','east','west'],'half':['top','bottom'],'shape':['straight'],'waterlogged':['false']},
  'mythrais:small_curved_corbel_dark_oak':{'facing':['north','east'],'shape':['0']},
 }}
 return Secondary(registry,Snapshot(blocks,protected),originals or {'castle':{},'bridge':{}},routes=routes)


class SecondaryDepthCustody(TestCase):
 def test_unknown_native_fitting_and_property_refuse(self):
  p=fixture()
  for name,props in (('imaginary:perfect_coffer',{}),('minecraft:stone',{'facing':'north'})):
   with self.subTest(name=name),self.assertRaisesRegex(UserError,'Exact native'):
    p.put(1258,91,-1037,name,**props)

 def test_default_or_tagged_be_is_immutable_even_when_saved_cell_is_air(self):
  p=fixture(protected={(1258,91,-1037)})
  with self.assertRaisesRegex(UserError,'Preserve saved fixture'):
   p.put(1258,91,-1037,'minecraft:stone')

 def test_original_chain_and_its_native_position_are_preserved(self):
  pos=(1283,81,-1033);original={'castle':{pos:'minecraft:chain'},'bridge':{}}
  p=fixture({pos:'minecraft:chain'},originals=original);p.group='kitchen'
  with self.assertRaisesRegex(UserError,'Preserve saved fixture'):
   p.put(*pos,'minecraft:stone')
  self.assertEqual(p.originals,original)

 def test_retained_stair_and_route_body_are_hard_exclusions(self):
  p=fixture(routes=[{'point':[1259,90,-1035]}])
  with self.assertRaisesRegex(UserError,'route or control'):
   p.put(1258,91,-1035,'minecraft:stone')

 def test_facade_outside_is_observed_not_assumed_air(self):
  for old in ('minecraft:water','minecraft:stone'):
   pos=(1211,75,-1201);p=fixture({pos:old});p.group='north-lodge'
   with self.subTest(old=old),self.assertRaisesRegex(UserError,'actual saved air'):
    p.put(*pos,'minecraft:stone')

 def test_only_the_eight_exact_blank_plaster_cells_can_be_recessed(self):
  p=fixture({(1213,72,-1200):'minecraft:white_terracotta'});p.group='north-lodge'
  with self.assertRaisesRegex(UserError,'Only exact blank plaster'):
   p.stairs(1213,72,-1200,'minecraft:dark_oak_stairs','south',niche=True)
  pos=(1212,72,-1200);p=fixture({pos:'minecraft:stone'});p.group='north-lodge'
  with self.assertRaisesRegex(UserError,'Only exact blank plaster'):
   p.stairs(*pos,'minecraft:dark_oak_stairs','south',niche=True)

 def test_blind_niche_retains_the_inward_half_wall_and_original_preimage(self):
  pos=(1212,72,-1200);old={pos:'minecraft:white_terracotta'}
  p=fixture(old,originals={'castle':{},'bridge':dict(old)});p.group='north-lodge'
  with self.assertRaisesRegex(UserError,'inward solid half-wall'):
   p.stairs(*pos,'minecraft:dark_oak_stairs','north',niche=True)
  p.stairs(*pos,'minecraft:dark_oak_stairs','south',half='bottom',niche=True)
  self.assertEqual(p.before,old);self.assertEqual(p.snapshot.blocks,old)
  self.assertEqual(p.originals['bridge'],old);self.assertIn('facing=south',p.blocks[pos])

 def test_moving_bridge_guard_survives_an_accidentally_widened_art_box(self):
  p=fixture();p.group='north-lodge'
  with patch.dict(ENVELOPES,{'north-lodge':(1187,71,-1201,1215,76,-1100)}):
   with self.assertRaisesRegex(UserError,'moving-leaf and machinery'):
    p.put(1193,72,-1160,'minecraft:stone')

 def test_bracket_under_top_slab_refuses_the_real_half_block_gap(self):
  root=(1258,92,-1035);p=fixture({root:'minecraft:stone'})
  p.corbel(1258,90,-1035,'east');p.slab(1258,91,-1035,'minecraft:dark_oak_slab')
  with self.assertRaisesRegex(UserError,'half-block floating gap'):validate(p)

 def test_new_perpendicular_native_stair_join_needs_explicit_review(self):
  roots={(1260,92,-1036):'minecraft:stone',(1261,92,-1036):'minecraft:stone'}
  p=fixture(roots);p.stairs(1260,91,-1036,'minecraft:dark_oak_stairs','south');p.stairs(1261,91,-1036,'minecraft:dark_oak_stairs','east')
  with self.assertRaisesRegex(UserError,'perpendicular stair join'):validate(p)

 def test_whole_predecessor_participates_in_material_rule(self):
  old={(x,91,-1036):'minecraft:stone' for x in range(1250,1259)}
  p=fixture(old,originals={'castle':dict(old),'bridge':{}});p.put(1259,91,-1036,'minecraft:stone')
  with self.assertRaisesRegex(ValueError,'Complete castle'):validate(p)

 def test_stairlike_mod_profile_is_not_ignored_because_of_its_name(self):
  old={(1211,75,-1200):'minecraft:stone',(1212,75,-1200):'minecraft:stone'}
  p=fixture(old);p.group='north-lodge'
  p.put(1211,75,-1201,'mythrais:slim_lintel_dark_oak',facing='north',half='top',shape='straight',waterlogged=False)
  p.stairs(1212,75,-1201,'minecraft:dark_oak_stairs','east')
  with self.assertRaisesRegex(UserError,'perpendicular stair join'):validate(p)

 def test_floating_cluster_does_not_count_as_real_ceiling_relief(self):
  p=fixture();p.put(1258,90,-1035,'minecraft:stone')
  with self.assertRaisesRegex(UserError,'structural support'):validate(p)

 def test_payload_keeps_exact_target_pair_and_replays_no_old_tags_or_commands(self):
  pos=(1212,72,-1200);p=fixture({pos:'minecraft:white_terracotta'});p.group='north-lodge'
  p.stairs(*pos,'minecraft:dark_oak_stairs','south',niche=True)
  before=payload(p.registry,'f'*64,p.before,'synthetic before');after=payload(p.registry,'f'*64,p.blocks,'synthetic after')
  self.assertEqual([v[:3] for v in before['blocks']],[v[:3] for v in after['blocks']])
  self.assertEqual(after['block_entities'],[]);self.assertEqual(after['commands'],[])
  self.assertNotEqual(before['palette'],after['palette']);json.dumps(after)

 def test_official_home_refuses_before_any_saved_world_access(self):
  with self.assertRaisesRegex(UserError,'Owned artistic staging home only'):
   prepare(Path(r'D:\A World for Two'),'fictional','f'*64)
