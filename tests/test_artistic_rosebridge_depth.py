import copy
import unittest

from control_room.common import UserError
from tools.artistic_bridge_refinement import flatten
from tools.artistic_landmarks import bridge_deck,world_point
from tools.artistic_rosebridge_depth import STATIONS,construct
from tools.settlement_attractions import properties


class RoseCrossingDepthTests(unittest.TestCase):
    def setUp(self):
        self.registry={'blocks':{'minecraft:smooth_quartz_stairs':{
            'facing':['north','south','east','west'],'half':['bottom','top'],
            'shape':['straight','inner_left','inner_right','outer_left','outer_right'],
            'waterlogged':['true','false']}}}
        cells={}
        for station in STATIONS:
            for side in (-5,5):
                for y in (bridge_deck(station)-2,bridge_deck(station)-1):
                    cells[tuple(world_point((side,y,station),(1248,-1104),1,90))]='chipped:small_calcite_bricks'
        self.sentinels={(1248,64,-1104):'minecraft:water[level=0]',
                        (1248,75,-1104):'minecraft:stone_brick_stairs[facing=east,half=bottom,shape=straight,waterlogged=false]',
                        (1248,76,-1109):'minecraft:stone_brick_wall',
                        (1268,74,-1111):'handcrafted:dark_oak_bench',
                        (1203,70,-1116):'create:sequenced_gearshift'}
        cells.update(self.sentinels);palette=sorted(set(cells.values()))
        self.baseline={'palette':palette,'blocks':[[*p,palette.index(s)] for p,s in sorted(cells.items())],
                       'block_entities':[{'pos':[1203,70,-1116],'nbt':'{Instructions:[]}'}]}

    def test_exact_twenty_existing_voxels_with_solid_inward_back_half_and_unchanged_rest(self):
        baseline=copy.deepcopy(self.baseline);p=construct(self.registry,self.baseline)
        self.assertEqual(self.baseline,baseline)
        self.assertEqual(len(p['changed']),20)
        self.assertEqual(set(p['blocks']),set(flatten(baseline)))
        for pos,state in self.sentinels.items():self.assertEqual(p['blocks'][pos],state)
        for pair in p['pairs']:
            a,b=map(tuple,pair['two_cells']);lo,hi=properties(p['blocks'][a]),properties(p['blocks'][b])
            self.assertEqual((lo['half'],hi['half']),('bottom','top'))
            self.assertEqual(lo['facing'],hi['facing'])
            self.assertEqual(lo['facing'],'south' if a[2]==-1109 else 'north')
        self.assertTrue(all(not row['violations'] for row in p['material_checks']))

    def test_a_water_or_tagged_target_is_refused_instead_of_expanding_the_allowed_region(self):
        p=construct(self.registry,self.baseline);target=next(iter(p['changed']))
        changed=copy.deepcopy(self.baseline);changed['palette'].append('minecraft:water[level=0]')
        next(row for row in changed['blocks'] if tuple(row[:3])==target)[3]=len(changed['palette'])-1
        with self.assertRaisesRegex(UserError,'unreviewed fascia'):construct(self.registry,changed)
        changed=copy.deepcopy(self.baseline);changed['block_entities'].append({'pos':list(target),'nbt':'{}'})
        with self.assertRaisesRegex(UserError,'fixture'):construct(self.registry,changed)

    def test_unknown_native_state_schema_fails_closed(self):
        registry=copy.deepcopy(self.registry);registry['blocks']['minecraft:smooth_quartz_stairs']['half']=['bottom']
        with self.assertRaisesRegex(UserError,'native pale'):construct(registry,self.baseline)


if __name__=='__main__':unittest.main()
