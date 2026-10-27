"""Authored geometry/palette safety; native appearance remains a separate gate."""
import copy
import json
from pathlib import Path
import unittest

from control_room.common import UserError
from tools.artistic_street import (StreetPlan, building_material_checks, construct,
                                    designs, planned_clearance, room_connections)


class ArtisticStreetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = json.loads((Path(__file__).parent/'fixtures'/'artistic_street_registry.json').read_text())
        cls.plan = construct(cls.registry, (1224, 65, -1264))

    def test_walk_connections_and_material_rule_cover_every_building(self):
        self.assertEqual([], planned_clearance(self.plan)['blocked'])
        self.assertEqual(10, len(building_material_checks(self.plan)))
        for b in designs():
            routes = [r for r in self.plan.routes if r['id'].startswith(b.ident+'-')]
            self.assertEqual(len(b.levels)-1, len([r for r in routes if '-stairs-' in r['id']]))
            self.assertTrue(any(r['id'] == b.ident+'-shop-circulation' for r in routes))
        self.assertEqual(10, len({tuple(sorted(b.levels[0])) for b in designs()}))

    def test_rule_rejects_a_broad_solid_slab_even_with_facing_changes(self):
        p = copy.deepcopy(self.plan)
        p.zone = designs()[0].name
        for x in range(4):
            for z in range(4):
                p.put(x+1, 28, z+1, 'minecraft:stripped_dark_oak_log', priority=200,
                      axis='x' if x % 2 else 'z')
        with self.assertRaisesRegex(ValueError, 'material run rule failed'):
            building_material_checks(p)

    def test_missing_mod_fitting_refuses_instead_of_using_plain_glass(self):
        r = copy.deepcopy(self.registry)
        del r['blocks']['mcwwindows:dark_oak_window2']
        with self.assertRaisesRegex(UserError, 'Unregistered prototype block'):
            construct(r)

    def test_obstructed_shop_entrance_is_detected_without_carving_a_bypass(self):
        p = copy.deepcopy(self.plan)
        lot = p.lots[-1]
        x, floor, z = lot['door']
        p.put(x, floor+1, z+1, 'minecraft:stone_bricks', priority=200)
        with self.assertRaisesRegex(UserError, 'No planned door-to-stair connection'):
            room_connections(p)
        self.assertEqual('minecraft:stone_bricks', p.blocks[x, floor+1, z+1])

    def test_land_only_and_native_roundtrip_are_bounded(self):
        self.assertLess(len(self.plan.blocks), 120_000)
        self.assertTrue(all(z >= 0 for x, y, z in self.plan.blocks))
        self.assertNotIn('minecraft:water', {s.split('[', 1)[0] for s in self.plan.blocks.values()})
        native = self.plan.serialize('a'*64)
        self.assertTrue(native['prototype_only'])
        self.assertEqual([], native['commands'])
        palette = native['palette']
        ox, oy, oz = self.plan.origin
        decoded = {(x-ox, y-oy, z-oz): palette[i] for x, y, z, i in native['blocks']}
        self.assertEqual(self.plan.blocks, decoded)
        self.assertEqual(len(self.plan.tags), len(native['block_entities']))


if __name__ == '__main__':
    unittest.main()
