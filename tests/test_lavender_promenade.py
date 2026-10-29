"""Synthetic safety/geometry fixtures; never stand in for native or art review."""
import unittest

from control_room.common import UserError
from tools.artistic_lavender_promenade import Promenade, GRAPE, build, validate


def registry():
    plain = ('chipped:calcite_bricks chipped:bordered_calcite chipped:checkered_calcite_tiles '
             'chipped:tiled_calcite chipped:carved_purpur_block chipped:purpur_block_pillar '
             'chipped:purpur_block_mini_tiles chipped:purpur_block_bricks chipped:pink_terracotta_tiles '
             'chipped:tiled_purpur_block chipped:carved_amethyst_block chipped:purpur_block_scales '
             'chipped:blank_calcite_carving chipped:pink_terracotta_tile minecraft:air minecraft:dirt '
             'minecraft:azalea minecraft:flowering_azalea regions_unexplored:purple_lupine minecraft:potted_allium')
    blocks={v:{} for v in plain.split()}
    stairs={'facing':['north','south','east','west'],'half':['top','bottom'],
            'shape':['straight','inner_left','inner_right','outer_left','outer_right'],
            'waterlogged':['true','false']}
    blocks.update({k:stairs for k in ('minecraft:purpur_stairs','create:cut_calcite_stairs')})
    blocks.update({k:{'axis':['x','y','z']} for k in ('chipped:ornate_purpur_block_pillar','chipped:pink_terracotta_pillar')})
    blocks.update({'minecraft:purpur_slab':{'type':['top','bottom','double'],'waterlogged':['true','false']},
                   'minecraft:chain':{'axis':['x','y','z'],'waterlogged':['true','false']},
                   'minecraft:end_rod':{'facing':['up','down']},'minecraft:lilac':{'half':['lower','upper']},
                   'minecraft:flowering_azalea_leaves':{'distance':[str(v) for v in range(1,8)],'persistent':['true','false'],'waterlogged':['true','false']},
                   'minecraft:cave_vines_plant':{'berries':['true','false']},
                   'minecraft:cave_vines':{'age':[str(v) for v in range(26)],'berries':['true','false']},
                   'handcrafted:cherry_bench':{'facing':['east'],'color':['pink'],'shape':['single'],'waterlogged':['false']},
                   'handcrafted:cherry_side_table':{'facing':['east'],'color':['pink'],'waterlogged':['false']}})
    return {'blocks':blocks}


class Snapshot:
    def __init__(self):self.protected=set();self.overrides={GRAPE:'vinery:white_grape_bush[age=3]'}
    def state(self,p):
        if p in self.overrides:return self.overrides[p]
        x,y,z=p;f=65 if z<=-967 else 66
        return 'minecraft:grass_block[snowy=false]' if y==f else 'minecraft:dirt' if y<f else 'minecraft:air'


class PromenadeTests(unittest.TestCase):
    def make(self):return build(Promenade(registry(),Snapshot()))

    def test_full_scale_and_both_supported_roof_sides(self):
        p=self.make();c=validate(p)
        self.assertEqual((c['length_m'],c['paired_columns'],c['white_pendants']),(45,9,24))
        self.assertGreaterEqual(min(v['clear_blocks_below'] for v in p.pendants),4)
        self.assertEqual(c['bay_intervals_m'],[5,6,5,5,5,5,5,6])
        self.assertEqual(p.retained[GRAPE],'vinery:white_grape_bush[age=3]')

    def test_saved_water_and_native_inventory_refuse_construction(self):
        for state,be in (('minecraft:water[level=0]',False),('minecraft:air',True)):
            s=Snapshot();q=(1292,65,-990);s.overrides[q]=state
            if be:s.protected.add(q)
            with self.subTest(state=state,be=be),self.assertRaises(UserError):
                build(Promenade(registry(),s))

    def test_existing_route_and_clearance_are_exact_read_only_context(self):
        s=Snapshot();q=(1296,65,-990);s.overrides[q]='minecraft:gravel'
        walk={q:'minecraft:gravel',(1296,66,-990):'minecraft:air'}
        p=build(Promenade(registry(),s,walk=walk));validate(p)
        self.assertNotIn(q,p.blocks);self.assertEqual(p.retained[q],'minecraft:gravel')
        s=Snapshot();s.overrides[q]='minecraft:chest[facing=north,type=single,waterlogged=false]'
        with self.assertRaisesRegex(UserError,'interface changed'):
            build(Promenade(registry(),s,walk=walk))

    def test_protected_castle_room_air_is_not_buildable_space(self):
        with self.assertRaisesRegex(UserError,'Preserve castle'):
            build(Promenade(registry(),Snapshot(),protected={(1294,78,-980)}))

    def test_missing_attachment_and_one_sided_support_fail(self):
        p=self.make();x,y,z=p.pendants[0]['attachment'];p.blocks.pop((x,y-1,z))
        with self.assertRaisesRegex(UserError,'attachment'):validate(p)
        p=self.make();p.blocks.pop((1300,70,-995))
        with self.assertRaisesRegex(UserError,'support column'):validate(p)

    def test_disconnected_ornament_and_body_obstruction_fail(self):
        p=self.make();p.put(1303,80,-996,'chipped:carved_amethyst_block')
        with self.assertRaisesRegex(UserError,'Unconnected'):validate(p)
        p=self.make();p.put(1294,68,-980,'chipped:carved_amethyst_block')
        with self.assertRaisesRegex(UserError,'corridor obstruction'):validate(p)

    def test_remove_source_only_plant_does_not_leave_it_in_place_delta(self):
        p=Promenade(registry(),Snapshot());q=(1285,68,-980)
        p.put(*q,'minecraft:azalea');p.put(*q,'minecraft:air')
        self.assertNotIn(q,p.blocks);self.assertNotIn(q,p.before)
        self.assertEqual(p.retained[q],'minecraft:air')


if __name__=='__main__':unittest.main()
