"""Keep the published offline receipt bound to the exact reviewed proposal sources."""
import hashlib
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]/'compat/proposals/seedgen-moonlight-init'


class MoonlightProposalEvidenceTests(unittest.TestCase):
    def test_offline_receipt_cannot_be_reused_after_a_java_source_change(self):
        proof = json.loads((ROOT/'verification.json').read_text(encoding='utf-8'))
        receipt = proof['offline_receipt']
        sources = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in ROOT.glob('*.java')}
        self.assertEqual(receipt['source_sha256'], sources)
        self.assertTrue(receipt['passed'])
        self.assertEqual(receipt['compile_exit'], 0)
        self.assertEqual(receipt['budget_fixture_exit'], 0)

    def test_offline_compile_does_not_claim_native_parity_or_gameplay_acceptance(self):
        proof = json.loads((ROOT/'verification.json').read_text(encoding='utf-8'))
        for field in ('installed', 'runtime_qualified', 'strict_parity_proved'):
            self.assertIs(proof[field], False)
        self.assertIs(proof['offline_receipt']['native_world_actions'], False)
        self.assertIs(proof['offline_receipt']['modloader_or_mixin_execution'], False)
        self.assertIs(proof['native_api']['native_execution'], False)
        self.assertIs(proof['native_api']['strict_parity_proved'], False)
        actual = proof['native_api']['verified']
        self.assertLess(actual['manager_constructor_offset'], min(actual['registry_load_offsets']))


if __name__ == '__main__':
    unittest.main()
