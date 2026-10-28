"""Original source constraints; these do not simulate native fluid/redstone ticks."""
import json
from pathlib import Path
import unittest

from control_room.common import UserError
from tools.artistic_fountain_centerpiece import (
    AIR,CURB,FULL_WHITE,HEADER,INTAKE_PIPE,JET_WITNESSES,MARS,OUTPUT_PATH,
    STOP_LEVER,WATER_CROSS,WHEEL_SOURCE,admit_checkpoint_mode,compose,has_items,key,normal_owned_copper_aging,post_reset_precondition,state,validate,
)
from tools.artistic_spawn_plaza import construct

REGISTRY=json.loads((Path(__file__).parent/'fixtures/fountain_centerpiece_registry.json').read_text())


class SyntheticSoil:
    """Only a source fixture; not saved-world or game evidence."""
    protected=set()
    def state(self,pos):
        x,y,z=pos
        ground=63 if x>=1144 and z<=-1128 else 65 if x<=1128 and z<=-1128 else 64
        return 'minecraft:grass_block' if y==ground else 'minecraft:dirt' if y<ground else AIR


class FountainCenterpieceTests(unittest.TestCase):
    def make(self):
        baseline=construct(REGISTRY,SyntheticSoil())
        return compose(REGISTRY,baseline.blocks,baseline.routes)

    def test_complete_figure_is_supported_and_old_antenna_is_removed(self):
        p=self.make()
        for n in range(3):
            self.assertEqual(p.blocks[1138,75+n,-1129],state(REGISTRY,MARS,
                facing='west',multiblock=str(n),waterlogged=False))
        self.assertEqual(key(p.blocks[1138,74,-1129]),'minecraft:chiseled_quartz_block')
        self.assertFalse(any('single_lancet_arch_upper' in s for pos,s in p.blocks.items()
                             if 1133<=pos[0]<=1143 and pos[1]>=71))
        self.assertIn('PENDING',validate(p)['native_model_flow_collision_and_art_acceptance'])

    def test_single_outlets_have_real_full_backing_at_both_sides(self):
        p=self.make();seals=set(FULL_WHITE)|{'create:encased_fluid_pipe'}
        self.assertEqual(len(CURB),12);self.assertEqual(len(WATER_CROSS),9)
        for pos in CURB:self.assertIn(key(p.blocks[pos]),seals)
        for dx,dz in ((1,0),(-1,0),(0,1),(0,-1)):
            tip=(1138+2*dx,70,-1128+2*dz)
            self.assertEqual(p.blocks[tip],AIR)
            self.assertEqual(p.blocks[1138+3*dx,70,-1128+3*dz],AIR)
            for sign in (-1,1):
                self.assertIn(key(p.blocks[tip[0]+sign*dz,70,tip[2]+sign*dx]),seals)
        victim=next(iter(CURB));p.blocks[victim]=state(REGISTRY,'minecraft:smooth_quartz_slab',type='top',waterlogged=False)
        with self.assertRaisesRegex(UserError,'full non-waterloggable backing'):validate(p)

    def test_side_feed_is_bounded_and_cannot_join_the_intake(self):
        p=self.make()
        self.assertEqual(validate(p)['pump_to_header_edges'],13)
        self.assertTrue(all(sum(abs(a[i]-INTAKE_PIPE[i]) for i in range(3))>1 for a in OUTPUT_PATH))
        self.assertEqual(key(p.blocks[OUTPUT_PATH[-1]]),'create:encased_fluid_pipe')
        self.assertIn('west=true',p.blocks[OUTPUT_PATH[-1]])
        self.assertNotIn('waterlogged=',p.blocks[OUTPUT_PATH[-1]])
        self.assertTrue(all(pos[1]==65 for pos,s in p.blocks.items() if key(s)=='minecraft:water'))
        self.assertEqual(p.blocks[HEADER],AIR)

    def test_current_manual_control_and_public_body_routes_are_retained(self):
        p=self.make()
        for pos in p.fixed:self.assertEqual(p.blocks[pos],p.base[pos])
        self.assertIn('facing=south',p.blocks[1138,73,-1125])
        self.assertIn('powered=false',p.blocks[STOP_LEVER])
        for (x,z),floor in p.routes.items():
            self.assertTrue(all(p.blocks.get((x,y,z),AIR)==AIR for y in (floor+1,floor+2)))
        p.blocks[JET_WITNESSES[0]]='minecraft:quartz_bricks'
        with self.assertRaisesRegex(UserError,'narrow ribbons'):validate(p)

    def test_enclosed_header_does_not_open_a_second_water_room(self):
        p=self.make();pos=(1137,73,-1129)
        self.assertNotEqual(p.blocks[pos],AIR)
        self.assertTrue(all(p.blocks[1138,y,-1128]==AIR for y in (71,72)))
        p.blocks[pos]=AIR
        with self.assertRaisesRegex(UserError,'sealed side walls'):validate(p)

    def test_complete_material_rule_still_rejects_a_flat_uniform_panel(self):
        p=self.make()
        for x in range(1123,1127):
            for z in range(-1137,-1133):p.blocks[x,78,z]='minecraft:quartz_bricks'
        with self.assertRaisesRegex(ValueError,'material run rule failed'):validate(p)

    def test_saved_wet_observation_and_prospective_drain_are_distinct(self):
        pos=(1137,70,-1128);wet=state(REGISTRY,'minecraft:water',level=3)
        self.assertEqual(post_reset_precondition(pos,wet,{pos:AIR}),AIR)
        self.assertEqual(wet,'minecraft:water[level=3]')
        self.assertEqual(post_reset_precondition(pos,wet,{pos:wet}),wet)
        with self.assertRaisesRegex(UserError,'outside normal fountain flow'):
            post_reset_precondition(pos,'minecraft:chest',{pos:AIR})
        with self.assertRaisesRegex(UserError,'not saved air/soft'):
            post_reset_precondition(pos,'minecraft:chest',{})

    def test_transport_caches_do_not_authorize_destroying_inventory_or_named_stock(self):
        self.assertFalse(has_items({'id':'create:fluid_pipe','Flow':{'Pull':True},'Items':[]}))
        self.assertTrue(has_items({'Items':[{'id':'minecraft:diamond','count':1}]}))
        self.assertTrue(has_items({'nested':{'item':{'id':'minecraft:diamond','Count':1}}}))
        self.assertTrue(has_items({'CustomName':'Captain’s keepsake'}))
        self.assertTrue(has_items({'LootTable':'minecraft:chests/buried_treasure'}))

    def test_saved_owned_trim_may_age_without_authorizing_waxing_or_foreign_replacement(self):
        pos=(1123,65,-1131);base={pos:'minecraft:cut_copper'}
        for actual in ('minecraft:exposed_cut_copper','minecraft:weathered_cut_copper','minecraft:oxidized_cut_copper'):
            self.assertEqual(post_reset_precondition(pos,actual,base),actual)
        for actual in ('minecraft:waxed_cut_copper','minecraft:copper_block','minecraft:exposed_cut_copper_slab[type=bottom,waterlogged=false]'):
            with self.assertRaisesRegex(UserError,'outside normal fountain flow'):
                post_reset_precondition(pos,actual,base)
        self.assertFalse(normal_owned_copper_aging('minecraft:weathered_cut_copper','minecraft:cut_copper'))

    def test_dry_mode_refuses_a_wet_checkpoint_or_prospective_air(self):
        p=self.make();base=p.base
        observed={pos:base[pos] for pos in p.fixed|set(JET_WITNESSES)}
        pos=(1137,70,-1128);dry={pos:AIR}
        admit_checkpoint_mode(REGISTRY,base,observed,dry,dry,dry_checkpoint=True)
        observed[HEADER]=state(REGISTRY,'minecraft:water',level=0)
        with self.assertRaisesRegex(UserError,'FRESH actual dry checkpoint'):
            admit_checkpoint_mode(REGISTRY,base,observed,dry,dry,dry_checkpoint=True)
        observed[HEADER]=AIR
        with self.assertRaisesRegex(UserError,'prospective fluid drainage'):
            admit_checkpoint_mode(REGISTRY,base,observed,{pos:state(REGISTRY,'minecraft:water',level=8)},dry,dry_checkpoint=True)
        observed[HEADER]=observed[WHEEL_SOURCE]=state(REGISTRY,'minecraft:water',level=0)
        observed[STOP_LEVER]=state(REGISTRY,'minecraft:lever',face='wall',facing='east',powered=True)
        observed[1138,73,-1125]=state(REGISTRY,'minecraft:repeater',facing='north',delay=1,locked=False,powered=False)
        admit_checkpoint_mode(REGISTRY,base,observed,{pos:state(REGISTRY,'minecraft:water',level=8)},dry,dry_checkpoint=False)


if __name__=='__main__':unittest.main()
