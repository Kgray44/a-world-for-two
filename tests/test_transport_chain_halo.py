"""Synthetic radius/typed-NBT diagnostics; no generation or native READY proof."""
import struct
import unittest

from control_room.common import UserError
from tests.test_artistic_chain_route_request import region
from tools.artistic_chain_route_request_r4 import NODES
from tools.transport_chain_halo import classify,derive_columns,generation_proposal,read_chunk,survey_proposal


def metadata():
 return {'full_level':33,'ticket_level':31,'native_max_level':44,'ticket_reach':13,
         'loading_full_dependency_radius':1,'extra_light_neighbor_ring':1,'derived_radius':14,'required_read_columns':2002}


def nbt(cx,cz,status='minecraft:full',light=True,version=3955,section_kind=10):
 def name(s):
  raw=s.encode();return struct.pack('>H',len(raw))+raw
 raw=b'\x0a\x00\x00'+b'\x03'+name('DataVersion')+struct.pack('>i',version)
 raw+=b'\x03'+name('xPos')+struct.pack('>i',cx)+b'\x03'+name('zPos')+struct.pack('>i',cz)
 raw+=b'\x08'+name('Status')+name(status)+b'\x09'+name('sections')+bytes([section_kind])+struct.pack('>i',1)
 raw+=b'\x00'if section_kind==10 else struct.pack('>i',0)
 if light:raw+=b'\x01'+name('isLightOn')+b'\x01'
 return raw+b'\x00'


class CableHaloTests(unittest.TestCase):
 def test_native_ticket_and_light_formula_requires_exact2002_columns(self):
  centers,positions,radius=derive_columns(NODES,metadata())
  self.assertEqual((len(centers),len(positions),radius),(15,2002,14));self.assertEqual(positions[0],(54,-93))

 def test_changed_or_guessed_api_metadata_refuses(self):
  for key,value in [('native_max_level',43),('ticket_reach',11),('derived_radius',2),('loading_full_dependency_radius',0),('required_read_columns',217)]:
   data=metadata();data[key]=value
   with self.assertRaises(UserError):derive_columns(NODES,data)

 def test_real_region_nbt_types_and_full_light_flags_qualify_only_the_source(self):
  document,kinds,lists,_=read_chunk(region(54,-93,nbt(54,-93)),54,-93)
  self.assertEqual(classify(document,kinds,lists,(54,-93))['failed'],[])
  self.assertEqual(kinds['DataVersion'],3);self.assertEqual(lists['sections'],10)

 def test_biomes_and_missing_light_explain_the_actual_first_refusal(self):
  document,kinds,lists,_=read_chunk(region(54,-93,nbt(54,-93,'minecraft:biomes',False)),54,-93)
  self.assertEqual(classify(document,kinds,lists,(54,-93))['failed'],['non_FULL','lighting'])

 def test_absent_saved_column_is_unknown_and_not_an_air_or_full_default(self):
  with self.assertRaisesRegex(UserError,'ABSENT'):read_chunk(bytes(8192),54,-93)

 def test_version_coordinate_sections_and_retrogen_are_independent_failures(self):
  document,kinds,lists,_=read_chunk(region(54,-93,nbt(54,-93,version=3954,section_kind=3)),54,-93)
  document['below_zero_retrogen']={};document['xPos']=53
  self.assertEqual(set(classify(document,kinds,lists,(54,-93))['failed']),{'version','coordinate','sections','retrogen'})

 def test_numeric_value_does_not_substitute_for_required_int_tag_type(self):
  document,kinds,lists,_=read_chunk(region(54,-93,nbt(54,-93)),54,-93);kinds['DataVersion']=2
  self.assertIn('version',classify(document,kinds,lists,(54,-93))['failed'])

 def test_float_lighting_flags_follow_native_floor_without_guessing_extremes(self):
  document,kinds,lists,_=read_chunk(region(54,-93,nbt(54,-93)),54,-93)
  for kind in (5,6):
   kinds['isLightOn']=kind
   for value,qualified in ((-255.5,False),(-.5,True),(256.,False),(1.,True)):
    document['isLightOn']=value
    self.assertEqual('lighting'not in classify(document,kinds,lists,(54,-93))['failed'],qualified)
   for value in (float('nan'),float('inf'),2**32):
    document['isLightOn']=value
    with self.assertRaises(UserError):classify(document,kinds,lists,(54,-93))

 def test_finite_generation_dependency_count_does_not_authorize_or_bound_disk(self):
  _,halo,_=derive_columns(NODES,metadata())
  proposal=generation_proposal([{'chunk':[54,-93],'failed':['non_FULL']}],halo,metadata())
  self.assertEqual(proposal['generation_dependency_radius'],11)
  self.assertEqual(proposal['generation_dependency_columns_union'],23**2)
  self.assertFalse(proposal['authorization']);self.assertEqual(proposal['native_actions'],0)
  self.assertTrue(proposal['disk_allocation_upper_bound'].startswith('UNKNOWN'))

 def test_survey_groups_include_all_nine_ticket_centers_and_their_full_neighbors(self):
  _,halo,_=derive_columns(NODES,metadata());targets=[{'chunk':[54,-93],'failed':['non_FULL','lighting']}]
  proposal=survey_proposal(targets,halo,metadata());self.assertEqual(proposal['group_count'],1)
  group=proposal['groups'][0]
  self.assertEqual(len(group['sample_ticket_centers']),9);self.assertEqual(len(group['requested_FULL_true_columns']),25)
  self.assertEqual(group['generation_dependency_columns'],729);self.assertEqual(group['ticket_light_envelope_columns'],961)
  self.assertEqual(proposal['whole_model_columns_union'],961);self.assertFalse(proposal['authorization'])
  self.assertIn([54,-93],group['requested_FULL_true_columns'])

 def test_corrupt_or_unknown_columns_do_not_receive_an_ordinary_survey_recommendation(self):
  _,halo,_=derive_columns(NODES,metadata())
  for failure in ('absent','invalid_record','version','retrogen'):
   proposal=survey_proposal([{'chunk':[54,-93],'failed':[failure]}],halo,metadata())
   self.assertEqual(proposal['groups'],[]);self.assertFalse(proposal['authorization'])


if __name__=='__main__':unittest.main()
