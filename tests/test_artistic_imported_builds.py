import base64
import copy
import json
from pathlib import Path
import unittest

from control_room.common import UserError
from tools.artistic_imported_builds import (architectural_details, ordinary_tree,
    safe_tavern_furnishings, snbt)
from tools.artistic_materials import require_material_rule


class AuthoredImportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry=json.loads((Path(__file__).parent/'fixtures/import_adapter_registry.json').read_text('utf-8'))

    def test_structural_bays_keep_every_position_axis_and_cubic_shape_without_facing_evasion(self):
        geometry={(x,y,z):{'Name':'minecraft:spruce_log','Properties':{'axis':'x' if x%2 else 'z'}}
                  for x in range(12) for y in range(18) for z in range(12)}
        preserved=copy.deepcopy(geometry)
        result,changes,_=architectural_details(geometry,'tavern',self.registry)
        self.assertEqual(geometry,preserved)
        self.assertEqual(set(result),set(geometry))
        self.assertTrue(changes)
        from tools.structure_import import state_string
        require_material_rule({p:state_string(v) for p,v in result.items()},'Original synthetic timber fixture')
        self.assertTrue(all(v['Properties']['axis']==geometry[p]['Properties']['axis'] for p,v in result.items()))

    def test_exact_shelf_substitutions_keep_position_facing_and_reject_powered_future_networks(self):
        source={(1,4,2):{'Name':'minecraft:spruce_shelf','Properties':{
            'side_chain':'unconnected','waterlogged':'false','powered':'false','facing':'west'}}}
        result,changes,pending=architectural_details(source,'shop',self.registry)
        self.assertEqual(result[1,4,2],{'Name':'handcrafted:spruce_shelf','Properties':{'facing':'west','type':'1'}})
        self.assertEqual((len(changes),len(pending)),(1,1))
        source[1,4,2]['Properties']['powered']='true'
        with self.assertRaises(UserError):architectural_details(source,'shop',self.registry)

    def test_original_apertures_stay_glazed_with_a_separate_clerestory_frame(self):
        source={(x,y,8):{'Name':'minecraft:white_stained_glass'} for x in range(13,17) for y in range(10,14)}
        result,_,_=architectural_details(source,'shop',self.registry)
        self.assertEqual(set(result),set(source))
        self.assertTrue(all(v['Name'].startswith('mcwwindows:') for v in result.values()))
        self.assertEqual({result[x,13,8]['Name'] for x in range(13,17)}, {'mcwwindows:stripped_spruce_log_four_window'})

    def test_literal_profiles_and_banners_preserve_details_without_source_commands(self):
        texture=base64.b64encode(json.dumps({'textures':{'SKIN':{'url':
            'http://textures.minecraft.net/texture/'+'a'*64}}}).encode()).decode()
        head={'id':'Skull','SkullType':3,'Owner':{'Id':'12345678-1234-1234-1234-123456789012',
              'Properties':{'textures':[{'Value':texture}],'Signature':[{'Value':'unused old metadata'}]}}}
        banner={'id':'Banner','Base':15,'Patterns':[{'Pattern':'sku','Color':0}]}
        geometry={(0,0,0):{'Name':'minecraft:player_head'},(1,0,0):{'Name':'minecraft:white_banner'}}
        tags,ledger=safe_tavern_furnishings({(0,0,0):head,(1,0,0):banner},geometry)
        self.assertIn(texture,tags[0,0,0]);self.assertIn('[I;',tags[0,0,0])
        self.assertIn('minecraft:skull',tags[1,0,0]);self.assertIn('black',tags[1,0,0])
        self.assertNotIn('unused old metadata',tags[0,0,0])
        self.assertEqual(ledger[0]['legacy_profile_properties_retained_in_original_only'],['Signature'])
        for field in ('Command','LootTable'):
            bad=copy.deepcopy(head);bad[field]='anything'
            with self.assertRaises(UserError):safe_tavern_furnishings({(0,0,0):bad},geometry)
        bad=copy.deepcopy(head);bad['Owner']['Properties']['textures'][0]['Value']=base64.b64encode(
            json.dumps({'textures':{'SKIN':{'url':'https://example.com/anything'}}}).encode()).decode()
        with self.assertRaises(UserError):safe_tavern_furnishings({(0,0,0):bad},geometry)
        self.assertEqual(snbt({'text':'"; arbitrary text'}),'{"text":"\\\"; arbitrary text"}')

    def test_ordinary_tree_scope_does_not_admit_other_wood_or_bee_nests(self):
        for key in ('minecraft:oak_leaves','regions_unexplored:willow_log'):
            self.assertTrue(ordinary_tree(key))
        for key in ('minecraft:bee_nest','handcrafted:oak_cupboard','minecraft:stripped_oak_log','other:willow_log'):
            self.assertFalse(ordinary_tree(key))


if __name__=='__main__':unittest.main()
