"""Source/actual-model orientation boundaries, never native flow/art evidence."""
import unittest
from unittest.mock import Mock

from control_room.common import UserError
from tools import artistic_fountain_ornament47 as f


def registry():
    return {'blocks':{
        'mythrais:corbel_02_stone':{'colour':['3'],'facing':['north','east','west']},
        'mythrais:corbel_scroll_centre_travertine':{'shape':['0'],'facing':['north','east','west']},
        'mythrais:curved_frieze_travertine':{'facing':['east','west','south'],'half':['bottom'],
                                        'shape':['straight'],'waterlogged':['false']},
        'dawnoftimebuilder:marble_coffer_slab':{'type':['bottom'],'waterlogged':['false']},
        'minecraft:waxed_oxidized_cut_copper_slab':{'type':['bottom'],'waterlogged':['false']},
        'minecraft:potted_fern':{}}}


class CarvedFountainBoundaries(unittest.TestCase):
    def fixture(self):
        additions,mounts,roles=f.recipe(registry())
        source={p:f.AIR for p in additions}
        for p,mount in mounts.items():
            source[mount]=('dawnoftimebuilder:marble_coffer_slab[type=top,waterlogged=false]'
                           if p[1]>=74 else 'dawnoftimebuilder:marble')
        return source,additions,mounts,roles

    def test_small_addition_preserves_real_mechanical_and_water_volumes(self):
        source,additions,mounts,roles=self.fixture()
        self.assertEqual(len(additions),26)
        self.assertEqual(sum('potted_fern' in s for s in additions.values()),2)
        self.assertEqual(sum('copper' in s for s in additions.values()),2)
        forbidden=f.keepout(source,[(1144,65,-1125)])
        self.assertFalse(set(additions)&forbidden)
        self.assertTrue(f.validate_additions(source,additions,mounts,forbidden)
                        ['all_original_solids_and_unselected_AIR_unchanged'])
        self.assertFalse(any(p[2]>=-1127 for p in additions))

    def test_recolor_or_replacing_any_existing_cell_refuses(self):
        source,additions,mounts,_=self.fixture()
        source[next(iter(additions))]='minecraft:chiseled_quartz_block'
        with self.assertRaisesRegex(UserError,'never replace'):
            f.validate_additions(source,additions,mounts,set())

    def test_missing_retained_wall_backing_refuses(self):
        source,additions,mounts,_=self.fixture()
        source[next(iter(mounts.values()))]=f.AIR
        with self.assertRaisesRegex(UserError,'full marble'):
            f.validate_additions(source,additions,mounts,set())

    def test_a_flow_route_or_control_target_cannot_be_added(self):
        source,additions,mounts,_=self.fixture()
        with self.assertRaisesRegex(UserError,'keepout'):
            f.validate_additions(source,additions,mounts,{next(iter(additions))})

    def test_visual_boundaries_may_touch_but_not_enter_functional_voxel(self):
        self.assertFalse(f.intersects([0,1,0,1,2,1],(0,0,0)))
        self.assertTrue(f.intersects([0,.99,0,1,2,1],(0,0,0)))

    def test_pinned_frieze_facing_convention_uses_physical_backing(self):
        # Actual pinned straight-frieze variants: EAST unrotated, SOUTH Y90,
        # WEST Y180. The original model's complete backing rib is at localX16.
        obj=object.__new__(f.Models)
        variants={'facing=east,half=bottom,shape=straight':{'model':'test:rib'},
                  'facing=south,half=bottom,shape=straight':{'model':'test:rib','y':90},
                  'facing=west,half=bottom,shape=straight':{'model':'test:rib','y':180}}
        obj.get=Mock(return_value=({'variants':variants},{}))
        obj.geometry=Mock(return_value=([{'from':[14,0,0],'to':[16,16,16]}],[]))
        for outer,axis,edge in (('west',0,1),('east',0,0),('north',2,1)):
            value='mythrais:curved_frieze_travertine[facing='+f.FRIEZE_FACE[outer]+',half=bottom,shape=straight,waterlogged=false]'
            bounds=obj.summary(value)['local_visual_bounds']
            self.assertAlmostEqual(bounds[axis+3] if edge else bounds[axis],edge)


if __name__=='__main__':
    unittest.main()
