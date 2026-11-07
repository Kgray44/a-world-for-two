import copy
import hashlib
import json
from pathlib import Path
import unittest

from control_room.common import UserError
from tools import artistic_tortuga_west_garden_pockets as g
from tools.artistic_tortuga_frontages import AIR,key


class InnerGardenContinuationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        folder=Path(__file__).parent/'fixtures'
        cls.registry=json.loads((folder/'tortuga_west_garden_registry.json').read_text())
        cls.registry['blocks'].update(json.loads((folder/'tortuga_inner_garden_additions.json').read_text())['blocks'])
        cls.recipe_path=Path(__file__).parents[1]/'proposals/inner-west-gardens/lantern-courts.json'
        cls.design,_=g.inner_recipe(cls.recipe_path)

    def test_original_west_recipe_geometry_objects_walks_and_material_proofs_are_unchanged(self):
        s,o,w,r,c,p=g.construct(self.registry)
        payload={'states':[[*q,s[q]]for q in sorted(s)],'objects':o,'walks':[list(q)for q in sorted(w)],'roots':[list(q)for q in sorted(r)],'contexts':c,'proof':p}
        actual=hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        self.assertEqual(actual,'b5b9b93487aaa003cc358935d9de9716dea62e27f8f0c80022ecc0061d870811')
        svg=g.garden_map(s,r,w,c,{'retained_source_main_footprints':{}})
        self.assertEqual(hashlib.sha256(svg).hexdigest(),'3e21499e8d81fcb97fa032bdb37a30e8b7504f260977035e55d907bcdab92d09')

    def test_inner_plants_keep_native_pairs_soil_and_clear_visiting_columns(self):
        s,o,w,r,c,p=g.construct_inner(self.registry,self.design)
        self.assertEqual(len(r),56)
        self.assertFalse(r&w)
        self.assertTrue(all(1100<=x<=1185 for x,y,z in s))
        self.assertTrue(all(1100<=x<=1185 for x,z in w))
        for x,z in r:
            self.assertEqual(s[x,63,z],'minecraft:dirt')
            if key(s[x,64,z])in g.SHRUBS:self.assertEqual(s[x,65,z],key(s[x,64,z])+'[half=upper]')
        self.assertTrue(all(not proof['violations']for proof in p))

    def test_actual_entry_bends_orthogonally_around_the_refused_water_column(self):
        s,o,w,r,c,p=g.construct_inner(self.registry,self.design)
        self.assertNotIn((1136,-1205),w)
        self.assertIn((1138,-1205),w)
        for x in(1136,1137,1138):
            self.assertEqual(s[x,63,-1206],'minecraft:dark_oak_stairs[facing=north,half=bottom,shape=straight,waterlogged=false]')
        bad=copy.deepcopy(self.design);bad['shelters'][0]['entry_centres']=[[1136,-1207],[1137,-1206]]
        with self.assertRaisesRegex(UserError,'adjacent orthogonal'):g.construct_inner(self.registry,bad)

    def test_bridge_approach_has_no_data_or_constructor_authority(self):
        bad=copy.deepcopy(self.design);bad['potted_plinths'].append({'name':'forbidden','xz':[1186,-1200],'family':0})
        with self.assertRaisesRegex(UserError,'bridge approach'):g.construct_inner(self.registry,bad)

    def test_potted_markers_have_real_full_foundations(self):
        s,*_=g.construct_inner(self.registry,self.design)
        for row in self.design['potted_plinths']:
            x,z=row['xz'];self.assertNotEqual(s.get((x,63,z),AIR),AIR)
            self.assertEqual(key(s[x,64,z]),g.POTTED[row['family']])
