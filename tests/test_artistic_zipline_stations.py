"""Original station constraints, not native climbing or ride acceptance."""
import json
from pathlib import Path
import unittest

from control_room.common import UserError
from tools.artistic_zipline_stations import AIR,admit_saved_target,key,station,validate

REGISTRY=json.loads((Path(__file__).parent/'fixtures/zipline_station_registry.json').read_text())


def synthetic_site():
    return {'center_xz':[100,200],'bounds':[99,198,101,202],'proposed_floor_y':80,
        'exact_saved_support_and_clearance':[{'support':[x,79,z]}for x in range(99,102)for z in range(198,203)]}


class ZiplineStationTests(unittest.TestCase):
    def test_supported_real_anchor_and_clear_hanging_player_corridor(self):
        b,r=station(REGISTRY,synthetic_site(),'synthetic station')
        self.assertEqual(key(b[100,88,200]),'minecraft:spruce_fence')
        self.assertEqual(key(b[100,89,200]),'minecraft:stripped_dark_oak_log')
        self.assertEqual(r['boarding_floor_y'],84);self.assertEqual(r['hang_offset_required'],3.0)
        self.assertTrue(all(b[100,y,z]==AIR for y in range(85,88)for z in range(198,203)))

    def test_ladder_has_actual_solid_backing_and_a_separate_side_hatch(self):
        b,r=station(REGISTRY,synthetic_site(),'synthetic station')
        self.assertEqual(len(r['ladder']),4)
        for p in r['ladder']:
            self.assertEqual(key(b[tuple(p)]),'minecraft:ladder')
            self.assertNotEqual(b[p[0]-1,p[1],p[2]],AIR)
        self.assertEqual(key(b[101,85,200]),'minecraft:spruce_trapdoor')
        self.assertIn('facing=east',b[101,85,200])
        b[100,81,200]=AIR
        with self.assertRaisesRegex(UserError,'solid backing'):validate(b,r,'broken backing')

    def test_ladder_hatch_cannot_be_reversed_into_a_nonclimbable_exit(self):
        b,r=station(REGISTRY,synthetic_site(),'synthetic station')
        b[101,85,200]=b[101,85,200].replace('facing=east','facing=west')
        with self.assertRaisesRegex(UserError,'same way'):validate(b,r,'reversed hatch')

    def test_compact_footings_do_not_paste_terrain_or_expand_the_site(self):
        site=synthetic_site();b,_=station(REGISTRY,site,'synthetic station')
        self.assertTrue(all(99<=x<=101 and 198<=z<=202 for x,y,z in b))
        self.assertFalse(any(y<80 for x,y,z in b))
        site['exact_saved_support_and_clearance'][0]['support'][1]=75
        with self.assertRaisesRegex(UserError,'modest rooted'):station(REGISTRY,site,'buried site')

    def test_three_dimensional_details_are_models_not_a_uniform_wall(self):
        b,_=station(REGISTRY,synthetic_site(),'synthetic station');ids={key(s)for s in b.values()}
        self.assertIn('mcwwindows:dark_oak_louvered_shutter',ids)
        self.assertIn('handcrafted:dark_oak_shelf',ids)
        self.assertIn('mcwlights:tavern_wall_lantern',ids)
        self.assertIn('minecraft:spruce_stairs',ids)
        self.assertIn('minecraft:dark_oak_trapdoor',ids)

    def test_full_material_rule_survives_all_floor_roof_and_detail_layers(self):
        b,r=station(REGISTRY,synthetic_site(),'synthetic station')
        for x in range(95,99):
            for z in range(195,199):b[x,80,z]='minecraft:dark_oak_planks'
        with self.assertRaisesRegex(ValueError,'material run rule failed'):validate(b,r,'flat added panel')

    def test_actual_preimage_gate_preserves_all_existing_trees_soil_objects_and_BEs(self):
        p=(100,80,200)
        for actual in ('minecraft:chest','minecraft:oak_leaves','minecraft:spruce_log','minecraft:grass_block'):
            with self.subTest(actual=actual),self.assertRaisesRegex(UserError,'Preserve a saved BE/tree/object'):
                admit_saved_target(p,actual,set())
        with self.assertRaises(UserError):admit_saved_target(p,AIR,{p})
        admit_saved_target(p,AIR,set());admit_saved_target(p,'minecraft:snow[layers=1]',set())


if __name__=='__main__':unittest.main()
