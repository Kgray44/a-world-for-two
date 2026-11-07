"""Meaningful no-overwrite and shaft/input-clearance checks for fixed shop work."""
from copy import deepcopy
import json
import unittest

from control_room.common import UserError
from tools import transport_create_shops as shop


SCHEMAS = {
    'create:mechanical_press': {'facing': ['north', 'east', 'south', 'west']},
    'create:depot': {'waterlogged': ['false', 'true']},
    'create:hand_crank': {'facing': ['north', 'east', 'south', 'west', 'up', 'down'], 'waterlogged': ['false', 'true']},
    'create:millstone': {},
    'create:cogwheel': {'axis': ['x', 'y', 'z'], 'waterlogged': ['false', 'true']},
    'create:mechanical_saw': {'facing': ['up', 'down', 'north', 'south', 'east', 'west'], 'axis_along_first': ['true', 'false'], 'flipped': ['true', 'false']},
    'minecraft:blast_furnace': {'facing': ['north', 'south', 'east', 'west'], 'lit': ['false', 'true']},
    'minecraft:barrel': {'facing': ['up', 'down', 'north', 'south', 'east', 'west'], 'open': ['false', 'true']},
    'minecraft:bell': {'attachment': ['single_wall'], 'facing': ['south'], 'powered': ['false', 'true']},
    'minecraft:wall_torch': {'facing': ['south']},
    'minecraft:cauldron': {}, 'minecraft:polished_andesite': {}, 'minecraft:polished_blackstone_bricks': {},
}


def fixture(spec):
    positions = set(spec['blocks']) | set(spec['extra_air']) | set(spec['wall_supports'])
    positions |= {(x, y+dy, z) for x, y, z in spec['stands'] for dy in (0, 1)}
    positions |= {(x, 64, z) for x, _, z in set(spec['blocks']) | set(spec['stands'])}
    full = {q: shop.AIR for q in positions}
    for q in positions:
        if q[1] == 64 or q in spec['wall_supports']:
            full[q] = 'minecraft:spruce_planks'
    source = {'origin': [0, 0, 0], 'routes': [{'feet_local': [list(spec['stands'][0])]}],
              'rooms': [], 'complete_expected_state_context_ONLY': [[*q, s] for q, s in full.items()]}
    _, _, _, context = shop.witnesses(spec, source)
    actual = {q: full.get(q, shop.AIR) for q in set(spec['blocks']) | context}
    return source, actual


class ShopSourceTests(unittest.TestCase):
    def setUp(self):
        self.registry = {'seed': 7, 'world_path': 'D:/test/world', 'blocks': SCHEMAS}
        self.specs = shop.shops(self.registry)

    def derive(self, name, source=None, actual=None, protected=()):
        spec = self.specs[name]
        f, a = fixture(spec)
        return shop.derive(self.registry, name, spec, source or f, actual or a, protected, 'a'*64)

    def test_native_geometry_keeps_open_input_and_valid_side_shaft_axes(self):
        forge = self.specs['pelican-forge']['blocks']
        self.assertEqual(forge[1357, 67, -1127], 'create:mechanical_press[facing=east]')
        self.assertEqual(forge[1358, 67, -1127], 'create:hand_crank[facing=east,waterlogged=false]')
        self.assertEqual(forge[1357, 65, -1127], 'create:depot[waterlogged=false]')
        mill = self.specs['harbor-chair']['blocks']
        self.assertNotIn((1290, 66, -1123), mill)
        self.assertEqual(mill[1291, 65, -1123], 'create:cogwheel[axis=y,waterlogged=false]')
        self.assertEqual(mill[1291, 66, -1123], 'create:hand_crank[facing=up,waterlogged=false]')
        saw = self.specs['sandbar']['blocks']
        self.assertEqual(saw[1280, 65, -1159], 'create:mechanical_saw[axis_along_first=true,facing=up,flipped=false]')

    def test_small_deltas_have_no_inventory_tags_or_executable_commands(self):
        self.assertEqual(sum(len(s['blocks']) for s in self.specs.values()), 29)
        for name, spec in self.specs.items():
            docs = self.derive(name)
            for filename, raw in docs.items():
                plan = json.loads(raw)
                self.assertEqual(plan['commands'], [])
                self.assertEqual(plan['block_entities'], [])
                self.assertEqual(plan['construction_forbidden'], filename != 'additions-PROPOSAL.json')
            plan = json.loads(docs['additions-PROPOSAL.json'])
            self.assertEqual(len(plan['blocks']), len(spec['blocks']))

    def test_changed_current_object_or_air_named_block_entity_is_never_cleared(self):
        for name, spec in self.specs.items():
            source, actual = fixture(spec)
            q = next(iter(spec['blocks']))
            changed = dict(actual)
            changed[q] = 'minecraft:chest[facing=north,type=single,waterlogged=false]'
            with self.assertRaises(UserError):
                self.derive(name, source, changed)
            with self.assertRaises(UserError):
                self.derive(name, source, actual, [q])

    def test_obstructed_walk_and_item_space_or_changed_floor_hold_that_shop(self):
        for name, spec in self.specs.items():
            source, actual = fixture(spec)
            for q in (spec['stands'][0], spec['extra_air'][0], (spec['stands'][0][0], 64, spec['stands'][0][2])):
                changed = dict(actual)
                changed[q] = 'minecraft:stone'
                with self.assertRaises(UserError):
                    self.derive(name, source, changed)

    def test_old_source_furniture_and_routes_never_become_construction_authority(self):
        for name, spec in self.specs.items():
            source, actual = fixture(spec)
            q = next(iter(spec['blocks']))
            occupied = deepcopy(source)
            next(r for r in occupied['complete_expected_state_context_ONLY'] if tuple(r[:3]) == q)[3] = 'minecraft:barrel'
            with self.assertRaises(UserError):
                self.derive(name, occupied, actual)
            route = deepcopy(source)
            route['routes'].append({'feet_local': [list(q)]})
            with self.assertRaises(UserError):
                self.derive(name, route, actual)

    def test_missing_saved_target_and_incomplete_native_schema_refuse(self):
        source, actual = fixture(self.specs['pelican-forge'])
        actual.pop(next(iter(actual)))
        with self.assertRaises(UserError):
            self.derive('pelican-forge', source, actual)
        with self.assertRaises(UserError):
            shop.state(self.registry, 'create:hand_crank', facing='up')
        with self.assertRaises(UserError):
            shop.state(self.registry, 'create:hand_crank', facing='diagonal', waterlogged=False)


if __name__ == '__main__':
    unittest.main()
