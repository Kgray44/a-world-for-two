import unittest

from control_room.common import UserError
from tools.settlement_south import Lot, SouthPlan, valid_walk_node, walk_route


class SouthBankCustodyTests(unittest.TestCase):
    def plan(self, *, completed=(), protected=()):
        registry = {'blocks': {'minecraft:air': {}, 'minecraft:stone': {},
                               'minecraft:oak_planks': {}},
                    'items': [], 'entities': [], 'seed': '42', 'world_path': 'world'}
        survey = {'samples': [{'x': x, 'z': z, 'y': 70, 'ground_y': 70,
                               'block_entities': list(protected)}
                              for x in range(864, 925, 4)
                              for z in range(-1140, -1075, 4)]}
        return SouthPlan(registry, survey, 'a'*64, completed)

    def test_completed_air_clearance_is_as_protected_as_a_wall(self):
        original = {'palette': ['minecraft:air'], 'blocks': [[880, 71, -1120, 0]]}
        p = self.plan(completed=[('b'*64, original)])
        with self.assertRaises(UserError):
            p.put(880, 71, -1120, 'minecraft:oak_planks')
        self.assertEqual(p.blocks, {})
        # A matching state is retained in the world and omitted from the delta.
        p.put(880, 71, -1120, 'minecraft:air')
        self.assertEqual(p.blocks, {})

    def test_deep_container_survives_without_banning_the_surface_column(self):
        p = self.plan(protected=[(886, -40, -1102)])
        lot = p.fit(Lot('Surface cottage', 881, -1108, 11, 9, 'cottage'))
        self.assertEqual((lot['x'], lot['z'], lot['floor']), (881, -1108, 70))
        p.put(886, 70, -1102, 'minecraft:stone')
        with self.assertRaises(UserError):
            p.put(886, -40, -1102, 'minecraft:air')

    def test_tree_inclusive_or_coarse_surveys_cannot_drive_construction(self):
        p = self.plan()
        samples = list(p.samples.values())
        samples[0] = {key: value for key, value in samples[0].items() if key != 'ground_y'}
        with self.assertRaises(UserError):
            SouthPlan(p.registry, {'samples': samples}, 'a'*64, [])
        coarse = [{'x': x, 'z': z, 'y': 70, 'ground_y': 70}
                  for x in (872, 880, 888) for z in (-1128, -1120, -1112)]
        with self.assertRaises(UserError):
            SouthPlan(p.registry, {'samples': coarse}, 'a'*64, [])

    def test_walking_search_respects_porch_signs_and_native_inventory_positions(self):
        p = self.plan()
        p.porch_details.add((881, -1120))
        self.assertFalse(valid_walk_node(p, (880, 70, -1120)))
        q = self.plan()
        q.tags[881, 71, -1120] = '{Items:[]}'
        self.assertFalse(valid_walk_node(q, (880, 70, -1120)))

    def test_hill_route_uses_cardinal_single_step_grades(self):
        p = self.plan()
        route = walk_route(p, (880, 70, -1120), (892, 76, -1120), 'Synthetic graded walk')
        self.assertEqual(route[0], (880, 70, -1120))
        self.assertEqual(route[-1], (892, 76, -1120))
        for before, after in zip(route, route[1:]):
            self.assertEqual(abs(before[0]-after[0])+abs(before[2]-after[2]), 1)
            self.assertLessEqual(abs(before[1]-after[1]), 1)
        self.assertFalse(p.commands)

    def test_blocked_endpoint_is_refused_instead_of_erasing_a_previous_build(self):
        original = {'palette': ['minecraft:stone'], 'blocks': [[880, 70, -1120, 0]]}
        p = self.plan(completed=[('b'*64, original)])
        with self.assertRaises(UserError):
            walk_route(p, (880, 70, -1120), (892, 70, -1120), 'Blocked walk')
        self.assertEqual(p.blocks, {})


if __name__ == '__main__':
    unittest.main()
