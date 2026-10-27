import copy
import json
from pathlib import Path
import unittest

from control_room.common import UserError
from tools.artistic_street import building_material_checks, planned_clearance
from tools.artistic_street_details import construct, delta_native, lane_width, verify_baseline


class StreetDetailTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = json.loads((Path(__file__).parent/'fixtures'/'artistic_street_registry.json').read_text())
        cls.d = construct(cls.registry)

    def test_delta_cannot_replay_or_modify_original_stock_and_signs(self):
        native, changed = delta_native(self.d, 'a'*64)
        self.assertFalse(changed & self.d.protected)
        self.assertEqual(6, len(native['block_entities']))
        for pos, nbt in self.d.base.tags.items():
            self.assertEqual(nbt, self.d.p.tags[pos])
            self.assertEqual(self.d.base.blocks[pos], self.d.p.blocks[pos])
        ox, oy, oz = self.d.p.origin
        emitted = {(x-ox, y-oy, z-oz) for x, y, z, state in native['blocks']}
        self.assertEqual(changed, emitted)
        self.assertFalse(emitted & self.d.protected)

    def test_strict_complete_building_and_route_checks_still_pass(self):
        self.assertEqual(10, len(building_material_checks(self.d.p)))
        self.assertEqual([], planned_clearance(self.d.p)['blocked'])
        self.assertTrue(lane_width(self.d)['minimum_two_cells'])

    def test_protected_inventory_write_is_rejected(self):
        d = copy.deepcopy(self.d)
        pos = next(iter(d.protected))
        with self.assertRaisesRegex(UserError, 'existing stocked/sign'):
            d.air(*pos)

    def test_one_changed_baseline_block_is_not_silently_rebound(self):
        native = self.d.base.serialize('a'*64)
        verify_baseline(self.d, native, self.d.p.origin)
        native['blocks'][0][1] += 1
        with self.assertRaisesRegex(UserError, 'immutable placed plan'):
            verify_baseline(self.d, native, self.d.p.origin)


if __name__ == '__main__':
    unittest.main()
