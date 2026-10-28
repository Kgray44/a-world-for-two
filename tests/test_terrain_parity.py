import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from tools.terrain_parity import (REGISTRIES, SIDES, WITNESS_SIDES,
                                  compare_effective, compare_fingerprints)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


class TerrainParityTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def fingerprint(self, side, changed=False, error=False):
        entries, rows = [], [{'record': 'header', 'format': 'awft-seedgen-fingerprint-inputs:1',
                              'side': side, 'seedsharing_original_class_sha256': 'a' * 64}]
        for index, registry in enumerate(REGISTRIES):
            rows.append(dict(record='registry', registry=registry, present=True, role='keys_only' if index < 4 else 'keys_and_native_values'))
            key = 'test:terrain'
            row = dict(record='entry', registry=registry, key=key,
                       native_key_sha256=sha(key.encode()), status='key_only' if index < 4 else 'encoded')
            if index >= 4:
                row.update(value_sha256=('d' if changed and index == 5 else 'c') * 64,
                           value_bytes=12, value_hashed_by_native=True,
                           native_entry_contribution_sha256='b' * 64)
            if error and index == 5:
                row['status'] = 'native_encoding_error'
            rows.append(row)
            entries.append(row)
            rows.append(dict(record='registry_summary', registry=registry, entries=1))
        path = self.root / (side + '.worldgen.status.json')
        data = path.with_name(side + '.worldgen.jsonl')
        raw = ('\n'.join(json.dumps(r) for r in rows) + '\n').encode()
        data.write_bytes(raw)
        status = dict(format='awft-worldgen-input-status:1', side=side, complete=True, entries=6,
                      data_file=data.name, recorded_data_bytes=len(raw), data_sha256=sha(raw),
                      native_encoding_errors=int(error), native_encoding_exceptions=0,
                      encoded_values=1 if error else 2,
                      diagnostic_input_sha256=('f' if changed else 'e') * 64,
                      diagnostic_native_format_prefix=('f' if changed else 'e') * 16)
        path.write_text(json.dumps(status))
        return path

    def effective(self, side, changed=False, unknown=False, current=True):
        rows = [dict(record='private_effective_witness', lithostitched_sha256='a' * 64,
                     private_native_world_seed=918273645, not_a_fingerprint_or_acceptance_gate=True),
                dict(record='actual_current_generator', dimension='minecraft:overworld',
                     effective_surface_tree={'record': 'UNKNOWN', 'reason': 'opaque'} if unknown else {'ordered': ['stone', 'dirt' if changed else 'gravel']})]
        path = self.root / (side + '.lithostitched.status.json')
        raw = ('\n'.join(json.dumps(row) for row in rows) + '\n').encode()
        path.with_name(side + '.lithostitched.jsonl').write_bytes(raw)
        status = dict(record='witness_status', side=side, complete_export=True,
                      effective_state_coverage_complete=not unknown, unknown_effective_states=int(unknown),
                      observed_input_identities_unchanged=True, bytes=len(raw), data_sha256=sha(raw))
        status_raw = json.dumps(status).encode()
        path.write_bytes(status_raw)
        custody = dict(format='awft-native-effective-custody:1', side=side, status_file=path.name,
                       status_sha256=sha(status_raw), owner_thread_rechecked=True,
                       captured_inputs_still_current=current)
        path.with_name(side + '.lithostitched.custody.json').write_text(json.dumps(custody))
        return path

    def test_equal_names_do_not_hide_different_registered_values(self):
        result = compare_fingerprints(self.fingerprint(SIDES[0]), self.fingerprint(SIDES[1], changed=True))
        self.assertFalse(result['inputs_equal'])
        self.assertEqual(result['differing_entries'], [dict(registry=REGISTRIES[-1], key='test:terrain', difference='native_value_or_status')])
        self.assertFalse(result['strict_parity_proved'])

    def test_matching_clean_exports_are_diagnostics_only(self):
        result = compare_fingerprints(self.fingerprint(SIDES[0]), self.fingerprint(SIDES[1]))
        self.assertTrue(result['inputs_equal'])
        self.assertFalse(result['current_native_packet_acceptance_proved'])
        self.assertFalse(result['strict_parity_proved'])

    def test_matching_encoding_failures_never_equal_proof(self):
        result = compare_fingerprints(self.fingerprint(SIDES[0], error=True), self.fingerprint(SIDES[1], error=True))
        self.assertFalse(result['inputs_equal'])
        self.assertFalse(result['clean_complete_exports'])

    def test_changed_private_bytes_refuse_even_with_old_status(self):
        a, b = self.fingerprint(SIDES[0]), self.fingerprint(SIDES[1])
        b.with_name(b.name.replace('.status.json', '.jsonl')).write_bytes(b'{}\n')
        with self.assertRaises(ValueError):
            compare_fingerprints(a, b)

    def test_duplicate_json_members_refuse(self):
        a, b = self.fingerprint(SIDES[0]), self.fingerprint(SIDES[1])
        b.write_text('{"side":"a","side":"b"}')
        with self.assertRaises(ValueError):
            compare_fingerprints(a, b)

    def test_missing_value_hash_cannot_be_reported_as_matching(self):
        a, b = self.fingerprint(SIDES[0]), self.fingerprint(SIDES[1])
        data = b.with_name(b.name.replace('.status.json', '.jsonl'))
        rows = [json.loads(line) for line in data.read_bytes().splitlines()]
        for row in rows:
            if row.get('status') == 'encoded':
                row.pop('value_sha256')
        raw = ('\n'.join(json.dumps(r) for r in rows) + '\n').encode()
        data.write_bytes(raw)
        status = json.loads(b.read_bytes())
        status.update(data_sha256=sha(raw), recorded_data_bytes=len(raw))
        b.write_text(json.dumps(status))
        with self.assertRaises(ValueError):
            compare_fingerprints(a, b)

    def test_effective_rule_difference_is_retained_without_seed_disclosure(self):
        result = compare_effective(self.effective(WITNESS_SIDES[0]), self.effective(WITNESS_SIDES[1], changed=True))
        self.assertFalse(result['witnessed_state_equal'])
        self.assertEqual(result['differing_records'], [dict(record='actual_current_generator', key='minecraft:overworld')])
        self.assertNotIn('918273645', json.dumps(result))
        self.assertNotIn('stone', json.dumps(result))

    def test_identical_unknowns_and_stale_owner_custody_never_pass(self):
        for unknown, current in ((True, True), (False, False)):
            a = self.effective(WITNESS_SIDES[0], unknown=unknown, current=current)
            b = self.effective(WITNESS_SIDES[1], unknown=unknown, current=current)
            self.assertFalse(compare_effective(a, b)['witnessed_state_equal'])

    def test_effective_custody_must_bind_exact_status(self):
        a, b = self.effective(WITNESS_SIDES[0]), self.effective(WITNESS_SIDES[1])
        data = json.loads(b.read_bytes())
        data['elapsed_ms'] = 123
        b.write_text(json.dumps(data))
        with self.assertRaises(ValueError):
            compare_effective(a, b)


if __name__ == '__main__':
    unittest.main()
