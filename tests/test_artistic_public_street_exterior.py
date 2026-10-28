"""Geometry/support and preservation boundaries; no invented native art proof."""
import json
from pathlib import Path
import unittest
from control_room.common import UserError
from tools.artistic_materials import require_material_rule,require_outdoor_rule
from tools.artistic_rose_tavern_exterior import design,check_delta
from tools.artistic_west_quay_streets import furniture,paving,current_house_expectation,SMITH_OLD,SMITH_NATIVE
from tools.settlement_attractions import base,properties
from tools.showcase_coverage import SNBT
from tools.artistic_street_stock_nbt_fix import correct_tags,STOCK


class PublicStreetExteriorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r=json.loads((Path(__file__).parent/'fixtures/quay_street_exterior_registry.json').read_text())

    def test_paving_has_structural_short_joints_rather_than_unbounded_strips(self):
        blocks={(x,0,z):paving(x,z)for x in range(25)for z in range(25)}
        require_material_rule(blocks,'crossed short-jointed source paving')
        require_outdoor_rule(blocks,'bounded modeled paving')
        self.assertEqual(len(set(blocks.values())),3)

    def test_hanging_lights_have_real_bottom_support_and_carved_rooted_bays(self):
        p=furniture(self.r)
        self.assertEqual(len(p.parts),6)
        for(x,y,z),v in p.blocks.items():
            if base(v)=='minecraft:lantern'and properties(v).get('hanging')=='true':
                above=p.blocks[x,y+1,z]
                self.assertTrue(base(above).endswith('_slab'))
                self.assertEqual(properties(above)['type'],'bottom')
        for value in p.parts.values():require_material_rule(value,'complete public furniture')
        self.assertTrue(all(isinstance(row['nbt'],str)and SNBT(row['nbt']).read()['Items']==[]for row in p.tags))

    def test_oriels_have_real_apertures_cheeks_and_two_blocks_of_depth(self):
        delta,apertures,features=design(self.r)
        self.assertEqual(len(apertures),18);self.assertEqual(len(features),2)
        self.assertTrue(all(q[2]>=-1269 and q[1]>=72 for q in delta))
        self.assertTrue(all(delta[q]=='minecraft:air'for q in apertures))
        self.assertTrue(any(q[2]==-1267 and base(v)=='mcwwindows:blackstone_brick_gothic' for q,v in delta.items()))
        require_material_rule(delta,'complete twin oriel delta')

    def test_accepted_roof_pier_or_BE_preimage_cannot_be_silently_replaced(self):
        delta,apertures,_=design(self.r)
        old={q:'minecraft:green_terracotta'if q in apertures else'minecraft:air'for q in delta}
        check_delta(old,delta,apertures)
        q=next(iter(apertures));old[q]='chipped:detailed_dark_oak_planks'
        with self.assertRaises(UserError):check_delta(old,delta,apertures)
        old[q]='minecraft:green_terracotta'
        with self.assertRaises(UserError):check_delta(old,delta,apertures,{q})

    def test_only_the_five_real_prior_smith_wall_derivations_are_canonical(self):
        q=(1048,68,-1267)
        self.assertEqual(current_house_expectation(q,SMITH_OLD),SMITH_NATIVE[q])
        self.assertEqual(current_house_expectation((1047,68,-1267),SMITH_OLD),SMITH_OLD)
        with self.assertRaises(UserError):current_house_expectation(q,SMITH_OLD.replace('waterlogged=false','waterlogged=true'))

    def test_native_stock_adapter_changes_only_two_snbt_representations(self):
        old={'palette':['minecraft:air'],'blocks':[[1,2,3,0]],'block_entities':[
            {'pos':list(q),'nbt':{'id':'minecraft:barrel','Items':[],'CustomName':json.dumps({'text':'A named workbox — unchanged'})}}for q in sorted(STOCK)]}
        new=correct_tags(old)
        self.assertEqual(new['palette'],old['palette']);self.assertEqual(new['blocks'],old['blocks'])
        for a,b in zip(old['block_entities'],new['block_entities']):
            self.assertIsInstance(a['nbt'],dict);self.assertIsInstance(b['nbt'],str)
            self.assertEqual(SNBT(b['nbt']).read(),a['nbt'])

    def test_stock_adapter_refuses_old_or_nonempty_or_foreign_container_intent(self):
        rows=[{'pos':list(q),'nbt':{'id':'minecraft:barrel','Items':[],'CustomName':'{"text":"Work"}'}}for q in sorted(STOCK)]
        rows[0]['nbt']['Items']=[{'Slot':0,'id':'minecraft:diamond','count':1}]
        with self.assertRaises(UserError):correct_tags({'block_entities':rows})
        rows[0]['nbt']['Items']=[];rows[0]['pos'][0]+=1
        with self.assertRaises(UserError):correct_tags({'block_entities':rows})


if __name__=='__main__':unittest.main()
