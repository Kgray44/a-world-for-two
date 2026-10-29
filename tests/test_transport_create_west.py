"""West-only placement custody, real service space and mixer-drive checks."""
import json
import unittest

from control_room.common import UserError
from tests.test_transport_create_shops import SCHEMAS
from tools import transport_create_west as west


def fixture(spec):
    new = spec['blocks']
    service = set(spec['service_air']) | {(x, y+dy, z) for x, y, z in spec['operating_feet'] for dy in (0, 1)}
    floor = {(x, 63, z) for x, _, z in set(new) | set(spec['operating_feet'])}
    full = {q: west.AIR for q in set(new) | service}
    full.update({q: 'minecraft:spruce_planks' for q in floor | set(spec['ceiling_support'])})
    xs = [q[0] for q in full]
    zs = [q[2] for q in full]
    door = (min(xs)-2, 64, min(zs))
    route = {door, (door[0], 65, door[2])}
    full[door] = 'minecraft:oak_door[facing=north,half=lower,hinge=left,open=false,powered=false]'
    full[door[0], 65, door[2]] = 'minecraft:dark_oak_slab[type=top,waterlogged=false]'
    model = {'full': full, 'routes': route,
             'main': {(x, z) for x in range(min(xs)-3, max(xs)+4) for z in range(min(zs)-3, max(zs)+4)}}
    _, _, context = west.witness_geometry(spec, model)
    actual = {q: full.get(q, west.AIR) for q in set(new) | context}
    return model, actual


class WestShopTests(unittest.TestCase):
    def setUp(self):
        self.registry = {'seed': 7, 'world_path': 'D:/test/world', 'blocks': {
            **SCHEMAS, 'create:mechanical_mixer': {},
            'create:basin': {'facing': ['down', 'north', 'south', 'east', 'west']},
        }}
        self.specs = west.specifications(self.registry)

    def derive(self, name, actual=None, protected=(), model=None):
        spec = self.specs[name]
        m, a = fixture(spec)
        return west.derive(self.registry, name, spec, m if model is None else model,
                           a if actual is None else actual, protected, 'a'*64)

    def test_three_distinct_existing_west_rooms_have_ten_additive_cells(self):
        self.assertEqual(len({s['building'] for s in self.specs.values()}), 3)
        self.assertEqual(sum(len(s['blocks']) for s in self.specs.values()), 10)
        cells = [q for spec in self.specs.values() for q in spec['blocks']]
        self.assertEqual(len(cells), len(set(cells)))
        self.assertTrue(all(990 <= q[0] < 1088 for q in cells))

    def test_mixer_uses_native_side_small_cog_and_downward_crank_not_shaft_port(self):
        blocks = self.specs['crooked-kettle-dough']['blocks']
        self.assertEqual(blocks[1024, 64, -1307], 'create:basin[facing=down]')
        self.assertEqual(blocks[1024, 66, -1307], 'create:mechanical_mixer')
        self.assertEqual(blocks[1025, 66, -1307], 'create:cogwheel[axis=y,waterlogged=false]')
        self.assertEqual(blocks[1025, 65, -1307], 'create:hand_crank[facing=down,waterlogged=false]')
        self.assertNotIn((1024, 65, -1307), blocks)
        self.assertNotIn((1024, 67, -1307), blocks)

    def test_original_door_partial_shape_and_inventory_context_are_never_replaced_by_air(self):
        for name, spec in self.specs.items():
            model, actual = fixture(spec)
            docs = self.derive(name)
            after = json.loads(docs['complete-after-VERIFY-ONLY.json'])
            field = {tuple(r[:3]): after['palette'][r[3]] for r in after['blocks']}
            for q in model['routes']:
                self.assertEqual(field[q], actual[q])
                self.assertNotEqual(field[q], west.AIR)
                proposal = json.loads(docs['additions-PROPOSAL.json'])
                self.assertNotIn(q, {tuple(r[:3]) for r in proposal['blocks']})

    def test_new_service_access_blockage_and_air_named_saved_be_refuse(self):
        for name, spec in self.specs.items():
            model, actual = fixture(spec)
            for q in (next(iter(spec['blocks'])), spec['operating_feet'][0]):
                changed = dict(actual)
                changed[q] = 'minecraft:barrel[facing=up,open=false]'
                with self.assertRaises(UserError):
                    self.derive(name, changed)
            with self.assertRaises(UserError):
                self.derive(name, protected=[next(iter(spec['blocks']))])

    def test_changed_real_floor_or_press_ceiling_never_gets_filled_or_recolored(self):
        for name, spec in self.specs.items():
            model, actual = fixture(spec)
            _, supports, _ = west.witness_geometry(spec, model)
            for q in supports:
                changed = dict(actual)
                changed[q] = 'minecraft:water[level=0]'
                with self.assertRaises(UserError):
                    self.derive(name, changed)

    def test_route_or_facade_intersection_cannot_be_waived_for_a_machine(self):
        name = 'low-water-flour'
        spec = self.specs[name]
        model, actual = fixture(spec)
        q = next(iter(spec['blocks']))
        model['routes'].add(q)
        with self.assertRaises(UserError):
            self.derive(name, model=model)
        model, actual = fixture(spec)
        model['main'].remove((q[0]-1, q[2]))
        with self.assertRaises(UserError):
            self.derive(name, model=model)

    def test_native_plans_have_no_stock_fluid_or_inventory_tags_and_only_one_place_role(self):
        for name in self.specs:
            for filename, raw in self.derive(name).items():
                plan = json.loads(raw)
                self.assertEqual(plan['commands'], [])
                self.assertEqual(plan['block_entities'], [])
                self.assertNotIn('minecraft:water[level=0]', plan['palette'])
                self.assertEqual(plan['construction_forbidden'], filename != 'additions-PROPOSAL.json')

    def test_missing_saved_context_does_not_become_assumed_air(self):
        for name, spec in self.specs.items():
            _, actual = fixture(spec)
            actual.pop(next(iter(actual)))
            with self.assertRaises(UserError):
                self.derive(name, actual)


if __name__ == '__main__':
    unittest.main()
