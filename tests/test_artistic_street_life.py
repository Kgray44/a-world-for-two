import copy
import json
from pathlib import Path
import unittest

from control_room.common import UserError
from tools.artistic_street_life import construct, native_delta, check, bed_pairs


class LivedInStreetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = json.loads((Path(__file__).parent/'fixtures'/'artistic_street_registry.json').read_text())
        cls.d = construct(cls.registry)

    def test_delta_preserves_original_inventories_and_only_emits_new_displays(self):
        native, changed = native_delta(self.d, 'a'*64)
        self.assertFalse(changed & self.d.protected)
        self.assertEqual(len(self.d.new_entities), len(native['block_entities']))
        for pos, tag in self.d.base.tags.items():
            self.assertEqual(tag, self.d.p.tags[pos])
        ox, oy, oz = self.d.p.origin
        emitted = {(x-ox, y-oy, z-oz) for x, y, z, index in native['blocks']}
        self.assertEqual(changed, emitted)
        for row in native['block_entities']:
            pos = tuple(row['pos'][i]-self.d.p.origin[i] for i in range(3))
            self.assertIn(pos, self.d.new_entities)
            self.assertNotIn(pos, self.d.protected)

    def test_slot_overflow_and_floating_trade_clutter_are_rejected(self):
        d = copy.deepcopy(self.d)
        with self.assertRaisesRegex(UserError, 'actual native item slots'):
            d.inventory((60, 20, 42), 'supplementaries:item_shelf', ['minecraft:paper']*2,
                        'Invalid two-item shelf', slots=1, facing='north', waterlogged=False)
        with self.assertRaisesRegex(UserError, 'supporting furniture'):
            d.put(60, 20, 42, 'handcrafted:terracotta_medium_pot')

    def test_partial_bed_overwrite_is_detected(self):
        d = copy.deepcopy(self.d)
        pos = next(pos for pos, state in d.p.blocks.items() if '_bed[' in state and 'part=foot' in state)
        d.p.blocks[pos] = 'minecraft:air'
        with self.assertRaisesRegex(UserError, 'partially overwrote a real bed'):
            bed_pairs(d)

    def test_furniture_has_access_and_complete_material_checks_remain_strict(self):
        result = check(self.d)
        self.assertEqual(10, len(result['materials']))
        self.assertEqual([], result['planned_clearance']['blocked'])
        self.assertTrue(result['two_wide_alley'])
        self.assertTrue(result['two_wide_lane']['minimum_two_cells'])
        self.assertEqual(12, len(result['furniture_access']))
        self.assertLessEqual(len(self.d.new_entities), 64)


if __name__ == '__main__':
    unittest.main()
