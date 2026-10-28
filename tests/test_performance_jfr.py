import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools.performance_jfr import run


ROOT = Path(__file__).resolve().parents[1]
HOME = Path('D:/A World for Two/staging/world-tests/20261027T053650Z-artistic')


class RetainedJfrTests(unittest.TestCase):
    def test_synthetic_receipt_does_not_grant_native_acceptance_and_binds_sources(self):
        proof = json.loads((ROOT/'evidence/performance/jfr-reader-synthetic-20261028.json').read_text())
        self.assertIs(proof['native_gameplay_qualified'], False)
        self.assertIs(proof['strict_parity_proved'], False)
        receipt = proof['receipt']
        self.assertIs(receipt['synthetic_only'], True)
        self.assertIs(receipt['minecraft_or_attach_actions'], False)
        self.assertTrue(receipt['passed'])
        self.assertEqual(receipt['compile_exit'], 0)
        self.assertEqual(receipt['fixture_exit'], 0)
        for name, sha in receipt['source_sha256'].items():
            self.assertEqual(hashlib.sha256((ROOT/'compat/performance'/name).read_bytes()).hexdigest(), sha)

    def test_conflicting_modes_or_foreign_inputs_refuse_before_any_jdk_process(self):
        with patch('tools.performance_jfr.guard') as guard, patch('tools.performance_jfr.subprocess.run') as process:
            with self.assertRaisesRegex(ValueError, 'Choose'):
                run(HOME)
            with self.assertRaisesRegex(ValueError, 'Choose'):
                run(HOME, recording=Path('anything.jfr'), self_test=True)
            with tempfile.TemporaryDirectory() as folder:
                recording = Path(folder)/'foreign.jfr'
                recording.write_bytes(b'not a native recording')
                with self.assertRaisesRegex(ValueError, 'expected native PID'):
                    run(HOME, recording=recording, pid=0, process_start_ms=1)
                with self.assertRaisesRegex(ValueError, 'private construction home'):
                    run(HOME, recording=recording, pid=123, process_start_ms=1)
            guard.assert_not_called()
            process.assert_not_called()


if __name__ == '__main__':
    unittest.main()
