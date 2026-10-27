import tempfile
import unittest
from pathlib import Path

import probe


class ReadOnlyProbeTests(unittest.TestCase):
    def test_identity_drift_fails_before_archive_or_game_access(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'different.jar';path.write_bytes(b'changed pin')
            with self.assertRaisesRegex(ValueError,'differs'):
                probe.identified(path,probe.BDD_SHA256)

    def test_class_pool_parser_refuses_truncation_and_unknown_tags(self):
        prefix=b'\xca\xfe\xba\xbe\0\0\0\x41\0\x02'
        self.assertEqual(probe.utf8_constants(prefix+b'\x01\0\x07VARIANT'),{'VARIANT'})
        for suffix in (b'\xff',b'\x01\0\x07VAR',b'\x07\0'):
            with self.subTest(suffix=suffix),self.assertRaises(ValueError):
                probe.utf8_constants(prefix+suffix)

    def test_warning_counter_excludes_stack_trace_duplicates(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'latest.log'
            path.write_text('Failed to load texture: bdd:dragons/nightfury/male/null_male.png\n'
                            'java.io.FileNotFoundException: bdd:dragons/nightfury/male/null_male.png\n')
            self.assertEqual(probe.null_failure_counts(path),{'nightfury':1,'terrible_terror':0})


if __name__=='__main__':
    unittest.main()
