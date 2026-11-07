"""Saved river source refusal and biome decoding; no gameplay acceptance."""
from copy import deepcopy
import unittest

from control_room.common import UserError
from tools.living_world_west_sites import biome, district_body, river


class SavedRiver:
    def __init__(self):
        self.states = {}
        self.biomes = {'palette':['minecraft:river']}

    def state(self, p):
        return self.states.get(p, 'minecraft:water[level=0]' if p[1] in (61,62) else 'minecraft:air')

    def chunk(self, x, z):
        return {3:{'biomes':self.biomes}}


class WestSourceTests(unittest.TestCase):
    def test_district_draft_preserves_existing_owner_bounds_and_lore(self):
        current={'id':'tortuga','dialogue':{'jokes':['Owner line']},'entries':[]}
        original=deepcopy(current)
        body=district_body(current,{(983,-1313),(1392,-1122)})
        self.assertEqual(set(body),{'id','bounds'})
        self.assertEqual(body['bounds']['min_x'],983)
        self.assertEqual(current,original)
        current['bounds']={'dimension':'minecraft:overworld','min_x':1}
        self.assertIsNone(district_body(current,{(983,-1313)}))

    def test_complete_river_field_is_not_inferred_from_one_water_column(self):
        saved = SavedRiver()
        result, field = river(saved, 100, -200, set())
        self.assertEqual(result['saved_source_water_cells'], 50)
        self.assertEqual(result['saved_water_biomes'], {'minecraft:river':50})
        self.assertEqual(len(field), 392)
        for value in ('minecraft:air','minecraft:water[level=1]',None):
            bad = SavedRiver(); bad.states[102,61,-198] = value
            with self.assertRaises(UserError):
                river(bad,100,-200,set())

    def test_beach_navigational_mask_and_obstructed_surface_refuse(self):
        saved = SavedRiver(); saved.biomes = {'palette':['terralith:gravel_beach']}
        with self.assertRaises(UserError):
            river(saved,100,-200,set())
        with self.assertRaises(UserError):
            river(SavedRiver(),100,-200,{(103,-200)})
        saved=SavedRiver();saved.states[100,63,-200]='minecraft:oak_slab[type=bottom,waterlogged=false]'
        with self.assertRaises(UserError):
            river(saved,100,-200,set())

    def test_saved_biome_uses_all_three_axes_and_refuses_truncation(self):
        # A three-entry palette has32 values per long. The last y/z/x cell
        # belongs in the second long, not a default/first palette entry.
        section={'biomes':{'palette':['terralith:gravel_beach','minecraft:river','regions_unexplored:cold_river'],
                           'data':[0, 2 << 62]}}
        original=deepcopy(section)
        self.assertEqual(biome(section,15,15,15),'regions_unexplored:cold_river')
        self.assertEqual(biome(section,0,0,0),'terralith:gravel_beach')
        self.assertEqual(section,original)
        section['biomes']['data'].pop()
        with self.assertRaises(UserError):
            biome(section,15,15,15)


if __name__=='__main__':
    unittest.main()
