import copy
import json
from pathlib import Path
import unittest

from control_room.common import UserError
from tools.artistic_cottage_life import construct, native_delta, check, access
from tools.artistic_street_life import bed_pairs


class CottageFurnishingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixtures = Path(__file__).parent/'fixtures'
        cls.d = construct(json.loads((fixtures/'artistic_street_registry.json').read_text()),
                          json.loads((fixtures/'artistic_cottage_terrain.json').read_text()))

    def test_delta_never_replays_existing_stock_and_contains_exact_new_items(self):
        native, changed = native_delta(self.d, 'a'*64)
        self.assertFalse(changed & self.d.protected)
        self.assertEqual(len(self.d.new_entities), len(native['block_entities']))
        for pos, tag in self.d.base.tags.items():
            self.assertEqual(tag, self.d.p.tags[pos])
        self.assertTrue(any('farmersdelight:skillet' in r['nbt'] for r in native['block_entities']))

    def test_stairs_remain_air_clear_and_furniture_has_room_access(self):
        result = check(self.d)
        self.assertEqual([], result['cottage']['blocked'])
        self.assertEqual(6, len(result['furnished_access']))
        self.assertEqual(4, len(result['cottage']['materials']))
        # A table blocks a standing spot; rugs are the only explicitly allowed
        # low body objects, not a generic ignore-nonair rule.
        d = copy.deepcopy(self.d)
        d.p.blocks[6, 2, 11] = 'handcrafted:oak_table'
        with self.assertRaisesRegex(UserError, 'standing space'):
            access(d)

    def test_independently_derived_bed_direction_repair_has_complete_halves(self):
        self.assertEqual(4, bed_pairs(self.d))
        self.assertIn('facing=north', self.d.p.blocks[15, 1, 29])
        self.assertIn('part=head', self.d.p.blocks[15, 1, 29])
        d = copy.deepcopy(self.d)
        d.p.blocks[15, 1, 30] = 'minecraft:air'
        with self.assertRaisesRegex(UserError, 'partially overwrote'):
            bed_pairs(d)


if __name__ == '__main__':
    unittest.main()
