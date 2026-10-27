import unittest

from control_room.common import UserError
from tools.settlement_castle import BOUNDS, CastlePlan, basin, passage, stairs


def fixture(*, original=(), protected=(), other=()):
    registry = {'blocks': {
        'minecraft:air': {}, 'minecraft:stone': {}, 'minecraft:stone_bricks': {},
        'minecraft:quartz_block': {}, 'chipped:tiled_calcite': {},
        'chipped:small_calcite_bricks': {}, 'minecraft:chest': {},
        'minecraft:water': {'level': [str(n) for n in range(16)]},
        'minecraft:quartz_stairs': {'facing': ['north','east','south','west'],
            'half': ['bottom','top'], 'shape': ['straight'], 'waterlogged': ['false','true']},
    }, 'items': [], 'entities': [], 'seed': '42', 'world_path': 'world'}
    survey = {'samples': [{'x': x, 'z': z, 'y': 66, 'ground_y': 66,
                          'block_entities': list(protected)}
                         for x in (1180,1184,1188,1192,1196,1200)
                         for z in (-1016,-1012,-1008,-1004,-1000)]}
    def master(rows):
        palette = sorted({state for pos, state in rows})
        return {'palette':palette,'blocks':[[*pos,palette.index(state)] for pos,state in rows],
                'block_entities':[]}
    completed = [('core',master(original))]
    if other:
        completed.append(('other-completed-build',master(other)))
    return CastlePlan(registry,survey,survey,'a'*64,completed)


class CastlePreservationTests(unittest.TestCase):
    def test_only_original_castle_masonry_may_be_adapted_and_records_previous_state(self):
        pos=(1193,70,-1008)
        p=fixture(original=[(pos,'minecraft:stone_bricks')])
        p.put(*pos,'chipped:small_calcite_bricks')
        self.assertEqual(p.adaptations[pos]['previous'],'minecraft:stone_bricks')
        self.assertEqual(p.fixed[pos],'minecraft:stone_bricks')
        # An identical looking block outside the castle is an unrelated building.
        outside=(1180,70,-1008)
        p=fixture(original=[(outside,'minecraft:stone_bricks')])
        with self.assertRaises(UserError):
            p.put(*outside,'minecraft:air')

    def test_prior_inventory_and_other_construction_cannot_be_cleared(self):
        pos=(1193,70,-1008)
        for p in (fixture(original=[(pos,'minecraft:chest')]),
                  fixture(original=[(pos,'minecraft:stone_bricks')],protected=[pos]),
                  fixture(original=[(pos,'minecraft:stone_bricks')],other=[(pos,'minecraft:stone_bricks')])):
            with self.assertRaises(UserError):
                p.put(*pos,'minecraft:air')
            self.assertEqual(p.blocks,{})

    def test_returning_to_original_air_removes_an_intermediate_design_block(self):
        pos=(1193,70,-1008)
        p=fixture(original=[(pos,'minecraft:air')])
        p.put(*pos,'minecraft:stone_bricks')
        p.put(*pos,'minecraft:air')
        self.assertEqual(p.effective(pos),'minecraft:air')
        self.assertNotIn(pos,p.blocks)
        self.assertNotIn(pos,p.adaptations)

    def test_actual_castle_bounds_and_unknown_properties_are_enforced(self):
        p=fixture()
        for pos in ((BOUNDS[0]-1,70,-1008),(1193,133,-1008),(1193,47,-1008)):
            with self.assertRaises(UserError):
                p.put(*pos,'minecraft:stone')
        with self.assertRaises(UserError):
            p.put(1193,70,-1008,'minecraft:stone',facing='north')

    def test_route_verification_catches_furnishing_added_after_a_clear_passage(self):
        p=fixture()
        passage(p,'A real corridor',(1180,67,-1008),(1184,67,-1008),width=1)
        p.validate()
        p.put(1182,69,-1008,'minecraft:stone')
        with self.assertRaisesRegex(UserError,'Blocked headroom'):
            p.validate()

    def test_flight_has_connected_steps_and_two_blocks_of_headroom(self):
        p=fixture()
        passage(p,'Bottom landing',(1180,67,-1008),(1181,67,-1008),width=1)
        stairs(p,'A fitted stair',1182,67,-1008,5,'east',width=1)
        p.validate()
        p.put(1185,72,-1008,'minecraft:stone')
        with self.assertRaisesRegex(UserError,'Blocked headroom'):
            p.validate()

    def test_water_feature_must_retain_all_sides_and_a_bottom(self):
        p=fixture()
        basin(p,'Sealed reflecting pool',(1180,-1012,1186,-1004),67)
        p.validate()
        p.put(1180,66,-1008,'minecraft:air')
        with self.assertRaisesRegex(UserError,'uncontained edge'):
            p.validate()


if __name__=='__main__':
    unittest.main()
