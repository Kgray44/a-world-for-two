"""Finite temporary source fixtures; no public URL or native installer execution."""
from pathlib import Path
import hashlib
import json
import sys
import tempfile
import tomllib
import unittest

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
from control_room.pack import generate_pack
from tools.build_packwiz_supervisor import release_inventory

FIXTURES = Path(sys.argv.pop(1)) if len(sys.argv) > 1 else None


class InventoryTests(unittest.TestCase):
    def setUp(self):
        if FIXTURES:
            FIXTURES.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=FIXTURES)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.pack = self.root/'packwiz'
        self.lock_path = self.root/'lock.json'
        self.items = []
        for slug, kind, side in (('required', 'mod', 'both'), ('essential', 'mod', 'client'),
                                 ('server-only', 'mod', 'server'), ('warm-shader', 'shader', 'client')):
            self.items.append({'slug': slug, 'kind': kind, 'side': side, 'project_id': slug,
                               'version_id': 'v1-'+slug, 'name': slug, 'filename': slug+'.jar',
                               'url': 'https://example.invalid/'+slug+'.jar', 'size': 7,
                               'hashes': {'sha256': hashlib.sha256(b'fixture').hexdigest()},
                               'dependencies': [], 'optional': slug == 'essential',
                               'default': slug != 'essential', 'selection_reason': 'Synthetic fixture'})
        self.lock = {'version': '0.1.0-candidate.35', 'neoforge': '21.1.262', 'mods': self.items}
        (self.pack/'config/paxi/datapacks/fixture').mkdir(parents=True)
        (self.pack/'config/paxi/datapacks/fixture/pack.mcmeta').write_text('{"fixture":true}')
        self.refresh()

    def refresh(self):
        self.lock_path.write_text(json.dumps(self.lock), encoding='utf-8')
        generate_pack(self.pack, self.lock)

    def test_complete_original_chain_is_deterministic_and_includes_raw_and_wrong_side(self):
        raw, receipt = release_inventory(self.pack, self.lock_path)
        self.assertEqual(receipt['entries'], 5)
        self.assertEqual(receipt['raw_entries'], 1)
        self.assertEqual(receipt['metadata_entries'], 4)
        self.assertEqual((raw, receipt), release_inventory(self.pack, self.lock_path))
        self.assertIn(b'mods/server-only.pw.toml', raw)
        self.assertIn(b'config/paxi/datapacks/fixture/pack.mcmeta', raw)
        self.assertIn(b'/releases/0.1.0-candidate.35/pack.toml', raw)

    def test_changed_raw_configuration_cannot_become_a_trusted_inventory(self):
        (self.pack/'config/paxi/datapacks/fixture/pack.mcmeta').write_text('tamper')
        with self.assertRaisesRegex(ValueError, 'hash mismatch'):
            release_inventory(self.pack, self.lock_path)

    def test_missing_locked_artifact_or_unindexed_configuration_refuses(self):
        (self.pack/'mods/required.pw.toml').unlink()
        with self.assertRaises(ValueError):
            release_inventory(self.pack, self.lock_path)
        self.refresh()
        (self.pack/'config/unindexed.json').write_text('{}')
        with self.assertRaisesRegex(ValueError, 'inventory differs'):
            release_inventory(self.pack, self.lock_path)

    def test_gui_optional_default_is_checked_independently_of_old_validator(self):
        path = self.pack/'mods/essential.pw.toml'
        path.write_text(path.read_text().replace('default = false', 'default = true'))
        # Rebind the index/pack hashes while retaining the explicit lock policy.
        index = self.pack/'index.toml'
        rows = tomllib.loads(index.read_text())['files']
        for row in rows:
            if row['file'] == 'mods/essential.pw.toml':
                row['hash'] = hashlib.sha256(path.read_bytes()).hexdigest()
        index.write_text('hash-format = "sha256"\n'+''.join(
            '\n[[files]]\nfile = '+json.dumps(row['file'])+'\nhash = '+json.dumps(row['hash'])
            +'\nmetafile = '+str(row['metafile']).lower()+'\n' for row in rows))
        manifest = self.pack/'pack.toml'
        old = manifest.read_text()
        import re
        manifest.write_text(re.sub(r'hash = "[a-f0-9]{64}"', 'hash = "'+hashlib.sha256(index.read_bytes()).hexdigest()+'"', old))
        with self.assertRaisesRegex(ValueError, 'optional policy differs'):
            release_inventory(self.pack, self.lock_path)

    def test_unreviewed_optional_or_essential_on_even_when_consistent_refuses(self):
        self.items[1]['default'] = True
        self.refresh()
        with self.assertRaisesRegex(ValueError, 'GUI default-off'):
            release_inventory(self.pack, self.lock_path)
        self.items[1]['default'] = False
        self.items[0]['optional'] = True
        self.refresh()
        with self.assertRaisesRegex(ValueError, 'GUI default-off'):
            release_inventory(self.pack, self.lock_path)

    def test_no_strong_pin_or_incomplete_index_refuses(self):
        self.items[0]['hashes'] = {'sha1': 'a'*40}
        self.refresh()
        with self.assertRaisesRegex(ValueError, 'strong download hash'):
            release_inventory(self.pack, self.lock_path)

    def test_duplicate_case_ambiguous_artifacts_refuse(self):
        self.items[0]['filename'] = 'ESSENTIAL.jar'
        self.refresh()
        with self.assertRaisesRegex(ValueError, 'Duplicate filename'):
            release_inventory(self.pack, self.lock_path)


if __name__ == '__main__':
    unittest.main(verbosity=2)
