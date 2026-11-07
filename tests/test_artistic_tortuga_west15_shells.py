"""Muted coherent roof planes and custody-safe real gable depth."""
import json
from pathlib import Path
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

from control_room.common import UserError
from tools import artistic_tortuga_west15_shells as shells
from tools.artistic_spawn_plaza import state
from tools.artistic_tortuga_frontages import AIR,key
from tools.settlement_attractions import properties


class West15ShellTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root=Path(__file__).parent/'fixtures'
        cls.registry=json.loads((root/'tortuga_fill_registry.json').read_text())
        cls.registry['blocks'].update(json.loads((root/'tortuga_west15_extra_registry.json').read_text())['blocks'])

    def test_periodic_bright_main_courses_become_one_coherent_muted_plane(self):
        roof={}
        for z in range(9):
            family='stone_bricks'if z==7 else'bricks'
            roof[0,10,z]='mcwroofs:'+family+'_roof[facing=east,half=bottom,shape=straight]'
        changes,roles,recipe=shells.palette_recipe(self.registry,roof,{'id':'western-ten/sailmaker','floor_y':0})
        self.assertEqual({key(changes[q])for q in roof},{'mcwroofs:dark_oak_roof'})
        self.assertTrue(all(properties(changes[q])==properties(roof[q])for q in roof))
        self.assertEqual(recipe['dominant_slope_axis'],'ew')

    def test_cross_gable_and_whole_hip_end_faces_have_distinct_muted_families(self):
        roof={(0,10,0):'mcwroofs:dark_oak_roof[facing=east,half=bottom,shape=straight]',
              (0,10,1):'mcwroofs:dark_oak_roof[facing=east,half=bottom,shape=straight]',
              (1,11,1):'mcwroofs:red_terracotta_roof[facing=north,half=bottom,shape=straight]'}
        edits,_,_=shells.palette_recipe(self.registry,roof,{'id':'western-ten/apothecary','floor_y':0})
        self.assertNotIn((0,10,0),edits)
        self.assertEqual(key(edits[1,11,1]),'mcwroofs:spruce_roof')
        hip={(0,10,z):'mcwroofs:brown_terracotta_roof[facing=east,half=bottom,shape=straight]'for z in range(4)}
        edits,_,_=shells.palette_recipe(self.registry,hip,{'id':'western-ten/baker','floor_y':0})
        self.assertEqual([key(edits[0,10,z])for z in range(4)],['mcwroofs:spruce_roof','mcwroofs:dark_oak_roof','mcwroofs:dark_oak_roof','mcwroofs:spruce_roof'])

    def test_original_copper_stair_geometry_survives_the_quiet_roof_replacement(self):
        q=(0,9,0);old='minecraft:oxidized_cut_copper_stairs[facing=west,half=bottom,shape=outer_left,waterlogged=false]'
        edits,_,_=shells.palette_recipe(self.registry,{q:old},{'id':'west-smith/smith','floor_y':0})
        self.assertEqual(key(edits[q]),'minecraft:spruce_stairs')
        self.assertEqual(properties(edits[q]),properties(old))

    def test_only_independently_proved_native_ridge_part_delta_can_admit_source_surface(self):
        expected='mcwroofs:dark_oak_top_roof[part=switched_0]'
        current='mcwroofs:dark_oak_top_roof[part=end90]'
        self.assertEqual(shells.owned_surface_origin(expected,expected,None),'EXACT_ORIGINAL_SOURCE_STATE')
        self.assertEqual(shells.owned_surface_origin(expected,current,current),'EXACT_PRIMARY_ID_AND_INDEPENDENT_PINNED_NATIVE_RIDGE_PART')
        self.assertIsNone(shells.owned_surface_origin(expected,current,expected))
        self.assertIsNone(shells.owned_surface_origin(expected,'mcwroofs:spruce_top_roof[part=end90]','mcwroofs:spruce_top_roof[part=end90]'))
        stairs='minecraft:dark_oak_stairs[facing=east,half=bottom,shape=straight,waterlogged=false]'
        changed=stairs.replace('straight','outer_left')
        self.assertIsNone(shells.owned_surface_origin(stairs,changed,changed))

    def test_native_base_corner_uses_same_half_other_material_and_candidate_side_veto(self):
        roof=lambda wood,face,half='bottom':'mcwroofs:'+wood+'_roof[facing='+face+',half='+half+',shape=straight]'
        centre=(0,10,0);mask={centre:roof('dark_oak','north'),(0,10,-1):roof('spruce','west')}
        self.assertEqual(shells.native_base_shape(mask,centre),'outer_left')
        # Native canTakeShape compares this eastern side to the FRONT
        # spruce/west roof; using the centre/north would be incorrect.
        mask[1,10,0]=roof('red_terracotta','west')
        self.assertEqual(shells.native_base_shape(mask,centre),'straight')
        mask[1,10,0]=roof('red_terracotta','north')
        self.assertEqual(shells.native_base_shape(mask,centre),'outer_left')
        mask[0,10,-1]=roof('spruce','west','top')
        self.assertEqual(shells.native_base_shape(mask,centre),'straight')
        mask={centre:roof('dark_oak','north'),(0,10,1):roof('bricks','east')}
        self.assertEqual(shells.native_base_shape(mask,centre),'inner_right')

    def test_base_shape_ownership_is_independent_exact_and_not_a_blanket_state_waiver(self):
        expected='mcwroofs:red_terracotta_roof[facing=north,half=bottom,shape=straight]'
        actual=expected.replace('straight','outer_left')
        self.assertIn('INDEPENDENT_PINNED_NATIVE_BASE_ROOF_SHAPE',shells.owned_surface_origin(expected,actual,actual))
        self.assertIsNone(shells.owned_surface_origin(expected,actual,expected))
        changed=actual.replace('north','south')
        self.assertIsNone(shells.owned_surface_origin(expected,changed,changed))
        changed=actual.replace('red_terracotta','spruce')
        self.assertIsNone(shells.owned_surface_origin(expected,changed,changed))

    def test_carving_requires_exact_opaque_source_and_refuses_fragile_support_or_blocked_cells(self):
        q=(1,10,0);roof=(1,9,1)
        original={q:'minecraft:brown_terracotta',roof:'mcwroofs:dark_oak_roof[facing=east,half=bottom,shape=straight]'}
        house={'id':'western-ten/example','floor_y':0,'main_footprint':[[x,z]for x in range(3)for z in range(3)]}
        current=dict(original)
        getter=lambda p:current.get(p,AIR)
        edits,feature=shells.carved_gable(self.registry,original,house,getter,set(),dict(original),{})
        self.assertEqual(set(edits),{q})
        self.assertEqual(key(edits[q]),'minecraft:spruce_stairs')
        self.assertEqual(properties(edits[q])['half'],'top')
        self.assertEqual(current,original)
        self.assertFalse(shells.carved_gable(self.registry,original,house,getter,{q},dict(original),{})[0])
        current[1,9,0]='minecraft:lantern[hanging=true,waterlogged=false]'
        self.assertFalse(shells.carved_gable(self.registry,original,house,getter,set(),dict(original),{})[0])
        current=dict(original);current[q]='minecraft:stone_bricks'
        self.assertFalse(shells.carved_gable(self.registry,original,house,getter,set(),dict(original),{})[0])

    def test_source_map_is_explicitly_planning_and_never_a_native_photo(self):
        group=[{'name':'Sample & Stock','main_footprint':[[0,0],[1,0],[0,1],[1,1]]}]
        raw=shells.correction_map(group,{(0,7,0):'minecraft:stone_bricks'})
        ET.fromstring(raw)
        self.assertIn(b'PLANNING ONLY',raw)
        self.assertIn(b'not a native screenshot',raw)
        self.assertIn(b'No inventory relocation',raw)

    def test_real_hip_crest_changes_only_exact_owned_roof_blocks_and_refuses_blocked_stock(self):
        original={(0,12,z):'mcwroofs:dark_oak_top_roof[part=switched_0]'for z in range(4)}
        current=dict(original);getter=lambda q:current.get(q,AIR)
        house={'id':'western-ten/baker','floor_y':0}
        edits,feature=shells.raised_hip_ridge(self.registry,original,house,getter,set(),dict(original),{})
        self.assertEqual(len(edits),2)
        self.assertTrue(all(key(v)=='minecraft:stripped_dark_oak_log'for v in edits.values()))
        self.assertEqual(current,original)
        self.assertFalse(shells.raised_hip_ridge(self.registry,original,house,getter,set(original),dict(original),{})[0])

    def test_resource_refusal_stops_before_saved_home_or_world_work(self):
        with patch.object(shells,'guard',return_value={'allowed':True}),patch.object(shells,'reader_budget',side_effect=UserError('memory refused')),patch.object(shells.fill,'private_home')as home:
            with self.assertRaisesRegex(UserError,'memory refused'):shells.prepare('unused','unused','unused')
            home.assert_not_called()


if __name__=='__main__':unittest.main()
