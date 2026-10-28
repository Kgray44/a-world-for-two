"""Original geometry/guard checks, not native bridge or shader acceptance."""
import json
from pathlib import Path
import unittest

from control_room.common import UserError
from tools import artistic_bridge_topside_ornament as art
from tools.artistic_bridge_refinement import articulated_leaves,LEAVES
from tools.artistic_spawn_plaza import state

REGISTRY=json.loads((Path(__file__).parent/'fixtures/bridge_topside_registry.json').read_text())


def scaffold():
    """Synthetic source scaffold from the prior original public leaf generator.

    This is deliberately not a read of the user's saved world or a new receipt.
    Its small fixed posts only exercise preservation, corridors and whole-composite
    material checks. Actual saved binding belongs to prepare's separate gate.
    """
    class Scaffold:
        def __init__(self):self.blocks={};self.notes=[];self.group=''
        def put(self,wx,wy,wz,name,**props):self.blocks[wx,wy,wz]=state(REGISTRY,name,**props)
        def clear(self,x,y,z):self.blocks[x,y,z]=art.AIR
        def lamp(self,x,y,z):self.put(x,y,z,'minecraft:lantern',hanging=False,waterlogged=False)
    p=Scaffold()
    for _,pivot,_,_ in LEAVES:
        for x in range(1187,1199):p.put(x,70,pivot,'chipped:nailed_dark_oak_planks'if x%4==2 else'chipped:stacked_dark_oak_planks')
    articulated_leaves(p)
    for x,z in art.POSTS:
        p.put(x,70,z,'minecraft:chiseled_stone_bricks')
        p.put(x,71,z,'chipped:small_stone_bricks')
        p.put(x,72,z,'minecraft:chiseled_stone_bricks')
        p.put(x,73,z,'minecraft:stone_brick_slab',type='double'if z==-1185 else'bottom',waterlogged=False)
        if z==-1185:p.lamp(x,74,z)
    return p.blocks


class BridgeTopsideTests(unittest.TestCase):
    def test_complete_composites_obey_material_rule_and_keep_full_walk_lane(self):
        p=art.construct(REGISTRY,scaffold());proof=art.validate(p)
        self.assertTrue(proof['unchanged_ten_wide_pedestrian_body'])
        self.assertFalse(proof['native_new_glue_cycles_restart_or_vessel_acceptance'])
        self.assertFalse(any(art.pedestrian(q)for q in p.blocks))
        self.assertEqual(len(proof['material_checks']),3)

    def test_moving_changes_use_only_exact_preexisting_states_and_top_slabs(self):
        before=scaffold();p=art.construct(REGISTRY,before)
        allowed={v for q,v in before.items()if art.moving_owner(q)}
        for q,value in p.blocks.items():
            if art.moving_owner(q):
                self.assertIn(value,allowed)
                if q[1]==70:self.assertTrue(value.endswith('[type=top,waterlogged=false]'))
        with self.assertRaisesRegex(UserError,'already-cycled'):
            p.put((1187,72,-1163),'minecraft:gold_block',owner='north')
        with self.assertRaisesRegex(UserError,'already-cycled'):
            p.put((1187,72,-1163),'create:metal_girder',owner='north',axis='x',x=False,z=True,top=False,bottom=False,waterlogged=False)

    def test_complete_root_and_nose_rows_are_preserved_at_all_heights(self):
        before=scaffold();p=art.construct(REGISTRY,before)
        for label,pivot,direction,length in LEAVES:
            for n in(0,1,length-2,length-1):
                for x in range(1187,1199):
                    for y in range(69,74):
                        q=x,y,pivot+direction*n
                        self.assertEqual(p.at(q),before.get(q,art.AIR))
            with self.assertRaisesRegex(UserError,'attachment and final nose'):
                p.put((1187,72,pivot),'minecraft:iron_bars',owner=label,north=False,south=False,east=False,west=False,waterlogged=False)

    def test_existing_lamps_and_an_actual_BE_exclusion_cannot_be_overwritten(self):
        before=scaffold();p=art.construct(REGISTRY,before)
        for q,v in before.items():
            if v.startswith('minecraft:lantern'):self.assertEqual(p.at(q),v)
        protected={(1187,72,-1161)}
        with self.assertRaisesRegex(UserError,'BE, machinery'):
            art.construct(REGISTRY,before,protected)

    def test_fixed_model_hoods_are_three_dimensional_and_outside_leaf_sweep(self):
        p=art.construct(REGISTRY,scaffold());fixed={q:v for q,v in p.blocks.items()if p.owners[q]=='fixed'}
        self.assertTrue(any(v.startswith('mythrais:corbel_scroll')for v in fixed.values()))
        self.assertTrue(any(v.startswith('dawnoftimebuilder:limestone_gargoyle')for v in fixed.values()))
        self.assertTrue(any(v.startswith('mcwlights:')for v in fixed.values()))
        self.assertTrue(all(not art.swept_glue_hits(q,label)for q in fixed for label,_,_,_ in LEAVES))
        self.assertTrue(art.swept_glue_hits((1187,72,-1172),'north'))
        self.assertFalse(art.swept_glue_hits((1186,75,-1185),'north'))

    def test_uniform_inherited_panel_cannot_hide_behind_a_small_good_delta(self):
        p=art.construct(REGISTRY,scaffold())
        for x in range(1204,1208):
            for y in range(77,81):p.original[x,y,-1189]='minecraft:gold_block'
        with self.assertRaisesRegex(ValueError,'material run rule failed'):art.validate(p)

    def test_fixed_proposal_cannot_erase_an_unrelated_saved_object(self):
        before=scaffold();before[1186,75,-1185]='minecraft:gold_block'
        with self.assertRaisesRegex(UserError,'structural cores'):
            art.construct(REGISTRY,before)


if __name__=='__main__':unittest.main()
