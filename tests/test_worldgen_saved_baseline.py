import io
import unittest
import zlib

import nbtlib

from control_room.common import UserError
from tools.worldgen_saved_baseline import decode_record, packed_value


def region_fixture(compression=2):
    output = io.BytesIO()
    nbtlib.File({'xPos': nbtlib.Int(-1), 'zPos': nbtlib.Int(-1),
                 'Status': nbtlib.String('minecraft:full')}).write(output)
    payload = zlib.compress(output.getvalue()) if compression == 2 else output.getvalue()
    raw = bytearray(12288)
    raw[4092:4096] = (513).to_bytes(4, 'big')
    raw[8192:8196] = (len(payload)+1).to_bytes(4, 'big')
    raw[8196] = compression
    raw[8197:8197+len(payload)] = payload
    return raw


class SavedWorldgenBaselineTests(unittest.TestCase):
    def test_real_compressed_fixture_and_negative_slot_are_decoded(self):
        doc, sha = decode_record(region_fixture(), 1023)
        self.assertEqual((doc['xPos'], doc['zPos']), (-1, -1))
        self.assertEqual(doc['Status'], 'minecraft:full')
        self.assertEqual(len(sha), 64)
        self.assertIsNone(decode_record(region_fixture(), 0))

    def test_external_and_truncated_records_fail_without_substitution(self):
        with self.assertRaises(UserError):
            decode_record(b'', 0)
        with self.assertRaises(UserError):
            decode_record(region_fixture(130), 1023)
        raw = region_fixture()
        raw[8192:8196] = (999999).to_bytes(4, 'big')
        with self.assertRaises(UserError):
            decode_record(raw, 1023)

    def test_modern_packed_heightmap_does_not_cross_long_boundaries(self):
        self.assertEqual(packed_value([123 << 54, 321], 6, 9), 123)
        self.assertEqual(packed_value([123 << 54, 321], 7, 9), 321)
        with self.assertRaises(UserError):
            packed_value([1], 7, 9)


if __name__ == '__main__':
    unittest.main()
