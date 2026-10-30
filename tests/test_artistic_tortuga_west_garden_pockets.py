import json
from pathlib import Path
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

from control_room.common import UserError
from tools import artistic_tortuga_west_garden_pockets as g
from tools.artistic_tortuga_frontages import AIR,key


class WestGardenPocketTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry=json.loads((Path(__file__).parent/'fixtures/tortuga_west_garden_registry.json').read_text())

    def test_every_selected_shrub_has_real_lower_upper_and_literal_root_soil(self):
        states,objects,walks,roots,contexts,proofs=g.construct(self.registry)
        self.assertEqual(len(roots),67)
        for x,z in roots:
            self.assertEqual(states[x,63,z],'minecraft:dirt')
            lower=states[x,64,z]
            if key(lower)in g.SHRUBS:
                self.assertIn('half=lower',lower)
                self.assertEqual(states[x,65,z],key(lower)+'[half=upper]')
        self.assertFalse(roots&walks)
        self.assertTrue(all(968<=x<=1099 for x,y,z in states))

    def test_two_distinct_complete_shelters_have_clear_supported_two_wide_body(self):
        fingerprints=[]
        for lean in(False,True):
            p,proof,outside=g.shelter(self.registry,(0,63,0),lean=lean)
            self.assertEqual(proof['violations'],[])
            self.assertEqual(len(outside),4)
            for r in p.routes:
                self.assertEqual(len({q[0]for q in r['positions']}),2)
                for x,y,z in r['positions']:
                    self.assertNotEqual(p.blocks.get((x,y-1,z),AIR),AIR)
                    self.assertTrue(all(p.blocks.get((x,y+h,z),AIR)==AIR for h in(0,1)))
            for q,s in p.blocks.items():
                if key(s)in g.POTTED:self.assertNotEqual(p.blocks.get((q[0],q[1]-1,q[2]),AIR),AIR)
            fingerprints.append(tuple(sorted(p.blocks.items())))
        self.assertNotEqual(*fingerprints)

    def test_contained_greens_and_small_rooted_shrubs_are_not_tree_or_auto_planter_recipes(self):
        states,*_=g.construct(self.registry)
        ids={key(s)for s in states.values()}
        self.assertTrue(set(g.SHRUBS)<=ids)
        self.assertFalse(any(n.endswith(('_sapling','_leaves'))or n=='supplementaries:planter'for n in ids))
        self.assertTrue(any(n.startswith('fishofthieves:potted_')for n in ids))
        self.assertIn('handcrafted:dark_oak_bench',ids)

    def test_exact_soft_cover_clear_is_only_for_an_explicit_new_air_target(self):
        cover='supplementaries:barnacles[down=true,east=false,north=false,south=false,up=false,waterlogged=false,west=false]'
        self.assertTrue(g.own_shelter_walk_before(cover,AIR))
        self.assertFalse(g.own_shelter_walk_before(cover,None))
        self.assertFalse(g.own_shelter_walk_before(cover.replace('waterlogged=false','waterlogged=true'),AIR))
        self.assertFalse(g.own_shelter_walk_before('minecraft:barrel[facing=up,open=false]',AIR))
        self.assertFalse(g.own_shelter_walk_before(None,AIR))
        self.assertTrue(g.own_shelter_walk_before(AIR,None))

    def test_map_is_valid_explicitly_source_only_and_does_not_invent_land(self):
        s,o,w,r,c,p=g.construct(self.registry)
        raw=g.garden_map(s,r,w,c,{'retained_source_main_footprints':{}})
        ET.fromstring(raw)
        self.assertIn(b'SOURCE PLANNING ONLY',raw)
        self.assertIn(b'Not a Native screenshot',raw)
        self.assertIn(b'Blank areas confer no dry-ground',raw)

    def test_memory_refusal_stops_before_any_archive_or_private_world_access(self):
        with patch.object(g,'guard',return_value={'allowed':True}),patch.object(g,'reader_budget',side_effect=UserError('memory refused')),patch.object(g.narrow.fill,'private_home')as private:
            with self.assertRaisesRegex(UserError,'memory refused'):g.prepare('unused','unused','unused')
            private.assert_not_called()
