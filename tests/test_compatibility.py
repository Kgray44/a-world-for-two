import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from control_room.common import REPO, UserError, digest, read_json, write_json
from tools.compatibility import build_inventory, generate, render_inventory


class CompatibilityGenerationTests(unittest.TestCase):
    def fixture(self, root):
        for directory in ('catalog', 'docs', 'packwiz', 'evidence/runtime'):
            (root/directory).mkdir(parents=True)
        actual = read_json(REPO/'catalog/lock.json')
        chosen = {'cinematic-interactions', 'dh-seedgen', 'essential'}
        lock = copy.deepcopy(actual)
        lock['version'] = 'fixture.1'
        lock['mods'] = [mod for mod in lock['mods'] if mod.get('request') in chosen]
        write_json(root/'catalog/lock.json', lock)
        requests = read_json(REPO/'catalog/requests.json')
        requests['requests'] = [row for row in requests['requests']
                                if row[0] in chosen | {'pirates-n-ships', 'black-powder-age-of-sail', 'the-explorers-friend'}]
        write_json(root/'catalog/requests.json', requests)
        write_json(root/'catalog/experiments.json', read_json(REPO/'catalog/experiments.json'))
        (root/'packwiz/pack.toml').write_text('name = "Synthetic compatibility fixture"\n')
        from tools.compatibility import RUNTIME_RECEIPTS
        for filename, *_ in RUNTIME_RECEIPTS:
            (root/'evidence/runtime'/filename).write_bytes((REPO/'evidence/runtime'/filename).read_bytes())
        return lock

    def test_normal_rerun_is_complete_deterministic_and_does_not_reuse_generated_claims(self):
        with tempfile.TemporaryDirectory(prefix='awft-compatibility-') as folder:
            root = Path(folder)
            lock = self.fixture(root)
            first = generate(root)
            original_json = (root/'catalog/compatibility.json').read_bytes()
            original_markdown = (root/'docs/COMPATIBILITY.md').read_bytes()
            self.assertEqual(len(first['resolved_files']), len(lock['mods']))
            self.assertEqual(first['counts']['enabled_mod_entries'], 2)
            self.assertEqual(len(first['isolated_candidates']), 3)
            self.assertEqual(len(first['runtime_evidence']), 5)
            rows = {row['id']: row for row in first['requests']}
            self.assertFalse(rows['essential']['selected_by_default'])
            self.assertTrue(rows['cinematic-interactions']['runtime_observation']['current_file_matches_observed_pin'])
            # Generated output is never a source of authorization or acceptance.
            first['requests'][0]['status'] = 'Invented full multiplayer acceptance'
            first['runtime_evidence'].append({'claim': 'Invented acceptance'})
            write_json(root/'catalog/compatibility.json', first)
            generate(root)
            self.assertEqual((root/'catalog/compatibility.json').read_bytes(), original_json)
            self.assertEqual((root/'docs/COMPATIBILITY.md').read_bytes(), original_markdown)

    def test_changed_candidate_or_same_named_replacement_cannot_inherit_runtime_acceptance(self):
        with tempfile.TemporaryDirectory(prefix='awft-compatibility-') as folder:
            root = Path(folder)
            lock = self.fixture(root)
            generate(root)
            lock['version'] = 'fixture.2'
            mod = next(row for row in lock['mods'] if row.get('request') == 'cinematic-interactions')
            # Keep the version string: a byte-different file is still a new pin.
            mod['hashes']['sha256'] = '0'*64
            write_json(root/'catalog/lock.json', lock)
            changed = generate(root)
            row = next(row for row in changed['requests'] if row['id'] == 'cinematic-interactions')
            self.assertEqual(changed['pack_version'], 'fixture.2')
            self.assertEqual(row['status'], mod['status'])
            self.assertEqual(row['runtime'], mod['validation']['runtime'])
            self.assertFalse(row['runtime_observation']['current_file_matches_observed_pin'])
            self.assertIn('no current-pin acceptance', render_inventory(changed))
            self.assertEqual(next(v for v in changed['resolved_files'] if v.get('request') == 'cinematic-interactions')['hashes'], mod['hashes'])

    def test_changed_receipt_is_omitted_and_does_not_retain_old_observation(self):
        with tempfile.TemporaryDirectory(prefix='awft-compatibility-') as folder:
            root = Path(folder)
            self.fixture(root)
            generate(root)
            path = root/'evidence/runtime/owner-crafting-table-confirmation.json'
            path.write_bytes(path.read_bytes()+b'\n')
            changed = generate(root)
            row = next(v for v in changed['requests'] if v['id'] == 'cinematic-interactions')
            self.assertNotIn('runtime_observation', row)
            self.assertEqual(len(changed['runtime_evidence']), 4)
            self.assertEqual(len(changed['evidence_rejections']), 1)
            self.assertIn('changed immutable receipt', changed['evidence_rejections'][0]['reason'])

    def test_production_view_contains_every_request_and_every_exact_current_pin(self):
        data = build_inventory(REPO)
        lock = read_json(REPO/'catalog/lock.json')
        requests = read_json(REPO/'catalog/requests.json')['requests']
        self.assertEqual([v['id'] for v in data['requests']], [v[0] for v in requests])
        self.assertEqual(len(data['resolved_files']), len(lock['mods']))
        for resolved, source in zip(data['resolved_files'], lock['mods']):
            for key in ('project_id', 'version_id', 'version', 'filename', 'hashes', 'side', 'optional', 'default'):
                self.assertEqual(resolved.get(key), source.get(key), (source['slug'], key))
        self.assertEqual(data['counts']['enabled_mod_entries'], 197)
        self.assertEqual(len(data['requests']), 223)
        self.assertEqual(len(data['isolated_candidates']), 3)

    def test_lock_drift_is_refused_before_a_mixed_snapshot_is_published(self):
        with tempfile.TemporaryDirectory(prefix='awft-compatibility-') as folder:
            root = Path(folder)
            self.fixture(root)

            def changed_hash(path):
                return '0'*64 if Path(path).name == 'lock.json' else digest(path)

            with patch('tools.compatibility.digest', side_effect=changed_hash):
                with self.assertRaises(UserError):
                    generate(root)
            self.assertFalse((root/'catalog/compatibility.json').exists())
            self.assertFalse((root/'docs/COMPATIBILITY.md').exists())


if __name__ == '__main__':
    unittest.main()
