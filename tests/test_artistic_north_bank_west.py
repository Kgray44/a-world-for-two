"""Original local shop/route constraints, not native construction acceptance."""
import json
from pathlib import Path
import unittest

from control_room.common import UserError
from tools import artistic_north_bank_west as art

REGISTRY=json.loads((Path(__file__).parent/'fixtures/north_bank_west_registry.json').read_text())


class WestQuayTests(unittest.TestCase):
    def test_five_distinct_complete_programs_have_connected_source_interiors(self):
        plans=art.local_plans(REGISTRY)
        self.assertEqual(set(plans),{'florist','smith','armoury','shipwright','tavern'})
        shapes={tuple(sorted(p.main))for p,_ in plans.values()}
        self.assertEqual(len(shapes),5)
        for kind,(p,proof)in plans.items():
            with self.subTest(kind=kind):
                self.assertTrue(proof['source_entry_to_room_and_work_access'])
                self.assertGreater(proof['source_walk_nodes'],20)
                self.assertFalse(proof['native_visual_collision_or_interaction_acceptance'])
                self.assertTrue(p.tags)
                self.assertTrue(all('Items:[]'in tag for tag in p.tags.values()))

    def test_fancy_modded_windows_have_physical_sills_brows_and_carved_supports(self):
        for kind,fn in art.DESIGNS.items():
            p=fn(REGISTRY);ids={art.key(v)for v in p.blocks.values()}
            with self.subTest(kind=kind):
                self.assertTrue(any(k.startswith('mcwwindows:')for k in ids))
                self.assertIn('mythrais:curved_corbel_dark_oak',ids)
                self.assertIn('dawnoftimebuilder:limestone_bricks_edge',ids)
                self.assertTrue(p.overhangs)
                self.assertTrue(any(x<0 or z<0 or x>=p.width or z>=p.depth for x,y,z in p.blocks))

    def test_normal_half_step_entries_and_loft_holes_cannot_be_replaced_by_air(self):
        p=art.florist(REGISTRY);q=p.entries[0]
        self.assertIn('spruce_stairs',p.blocks[q]);self.assertIn('facing=south',p.blocks[q])
        p.blocks[q]=art.AIR
        with self.assertRaisesRegex(UserError,'no actual floor'):art.validate(p)
        p=art.armoury(REGISTRY);x,y,z=p.stairs[0];p.blocks[x,y+1,z]='minecraft:gold_block'
        with self.assertRaisesRegex(UserError,'two-high route'):art.validate(p)

    def test_declared_door_position_is_not_a_blanket_collision_exception(self):
        p=art.shipwright(REGISTRY);q=(2,1,8)
        self.assertIn(q,p.doors);p.blocks[q]='minecraft:gold_block'
        with self.assertRaisesRegex(UserError,'two-high route'):art.validate(p)

    def test_complete_material_rule_includes_upper_roof_and_furniture(self):
        p=art.tavern(REGISTRY)
        for x in range(4):
            for y in range(10,14):p.blocks[x,y,4]='minecraft:gold_block'
        with self.assertRaisesRegex(ValueError,'material run rule failed'):art.validate(p)

    def test_wall_lights_need_actual_solid_backing(self):
        p=art.smith(REGISTRY);_,support=p.lights[0];p.blocks[support]=art.AIR
        with self.assertRaisesRegex(UserError,'no real solid backing'):art.validate(p)

    def test_rotations_preserve_native_directions_axes_and_whole_geometry(self):
        value='minecraft:stripped_oak_log[axis=z]'
        self.assertEqual(art.rotate_state(REGISTRY,value,1),'minecraft:stripped_oak_log[axis=x]')
        stair='minecraft:spruce_stairs[facing=south,half=bottom,shape=straight,waterlogged=false]'
        self.assertIn('facing=north',art.rotate_state(REGISTRY,stair,2))
        globe='supplementaries:globe_sepia[facing=north,powered=false,rotation=4,waterlogged=false]'
        self.assertIn('facing=south',art.rotate_state(REGISTRY,globe,2))
        self.assertIn('rotation=4',art.rotate_state(REGISTRY,globe,2))
        x,z,w,d=-1,5,9,8
        for _ in range(4):x,z=art.rotate_xz(x,z,w,d,1);w,d=d,w
        self.assertEqual((x,z),(-1,5))
        for kind,fn in art.DESIGNS.items():
            p=fn(REGISTRY);world=art.world_blocks(p,(100,200),64,2)
            with self.subTest(kind=kind):self.assertEqual(len(world),len(p.blocks))

    def test_ordinary_chosen_programs_are_functional_blocks_without_claimed_residents(self):
        expectations={'florist':'chipped:botanist_workbench','smith':'minecraft:smithing_table','armoury':'minecraft:smithing_table',
                      'shipwright':'chipped:carpenters_table','tavern':'farmersdelight:cooking_pot'}
        for kind,required in expectations.items():
            p=art.DESIGNS[kind](REGISTRY)
            with self.subTest(kind=kind):self.assertIn(required,{art.key(v)for v in p.blocks.values()})


if __name__=='__main__':unittest.main()
