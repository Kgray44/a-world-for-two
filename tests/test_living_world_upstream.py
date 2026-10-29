import hashlib
import json
import tempfile
import tomllib
import unittest
from pathlib import Path
from unittest.mock import patch

from control_room.common import UserError
from tools import living_world_upstream as upstream


class UpstreamIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.districts = [{'id': 'tortuga', 'dialogue': {'gossip': ['The captain has misplaced the sea.'],
                                                      'night': ['Even the moon owes me money.']}},
                          {'id': 'rosewater', 'dialogue': {'weather': ['The rain neglected its invitation.']}}]

    def test_every_requested_mod_remains_visible_in_inventory(self):
        data = upstream.inventory()
        self.assertEqual(set(data['required_requests']), {row['id'] for row in data['mods']})
        self.assertEqual('21.1.262', data['neoforge'])
        for mod in data['mods']:
            self.assertEqual('not run', mod['runtime'])

    def test_exact_pins_and_voice_are_optional_and_creaturepals_cannot_export(self):
        files = upstream.bundle_files(self.districts)
        self.assertNotIn('mods/creaturepals.pw.toml', files)
        voice = tomllib.loads(files['mods/simple-voice-chat.pw.toml'])
        self.assertTrue(voice['option']['optional'])
        self.assertFalse(voice['option']['default'])
        for mod in upstream.inventory()['mods']:
            if mod['status'] == 'pinned-proposal-awaiting-native-validation':
                meta = tomllib.loads(upstream.packwiz_entry(mod))
                self.assertEqual(mod['hashes']['sha512'], meta['download']['hash'])
            else:
                with self.assertRaises(UserError):
                    upstream.packwiz_entry(mod)

    def test_scripted_default_does_not_enable_upstream_voice_or_rewards(self):
        config = tomllib.loads(upstream.smart_config())
        self.assertFalse(config['voice']['enabled'])
        self.assertFalse(config['requests']['enabled'])
        self.assertTrue(config['privacy']['requirePlayerOptIn'])
        self.assertTrue(config['proximity']['requirePrefix'])
        self.assertEqual('', config['ai']['model'])
        self.assertEqual('', config['ai']['apiKey'])
        self.assertLessEqual(config['ai']['maxConcurrent'], 2)
        self.assertFalse(upstream.chatting_config()['chatMessagesEnabled'])
        self.assertTrue(upstream.chatting_config()['bubblesEnabled'])

    def test_district_state_is_exclusive_despite_upstream_or_matching(self):
        result = upstream.district_dialogue(self.districts)
        for path, rows in result.items():
            district = 'tortuga' if 'tortuga' in path else 'rosewater'
            for row in rows:
                self.assertEqual(['awft_district_' + district], row['conditions']['state'])
        night = result['config/chattingvillagers/dialogue/en_us/awft_tortuga.json'][1]
        self.assertEqual(['night'], night['conditions']['timeOfDay'])
        weather = result['config/chattingvillagers/dialogue/en_us/awft_rosewater.json'][0]
        self.assertEqual(['rain', 'thunder'], weather['conditions']['weather'])

    def test_invalid_paths_duplicate_ids_and_large_dialogue_fail_before_writing(self):
        for districts in [[{'id': '../tortuga'}], [self.districts[0]] * 2,
                          [{'id': 'tortuga', 'dialogue': {'gossip': ['x' * 241]}}],
                          [{'id': 'tortuga', 'dialogue': {'gossip': ['newline\n']}}],
                          self.districts * 10]:
            with self.subTest(districts=str(districts)[:80]), self.assertRaises(UserError):
                upstream.bundle_files(districts)

    def test_export_never_overwrites_existing_output(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(upstream, 'reserve_allocation') as guard:
            root = Path(directory) / 'proposal'
            result = upstream.export_bundle(root, self.districts)
            guard.assert_called_once_with(root)
            original = (root / 'config/chattingvillagers.json').read_bytes()
            self.assertLess(result['bytes'], upstream.MAX_BUNDLE_BYTES)
            self.assertEqual(7, result['files'])
            with self.assertRaises(UserError):
                upstream.export_bundle(root, self.districts)
            self.assertEqual(original, (root / 'config/chattingvillagers.json').read_bytes())

    def test_artifact_identity_is_measured_and_mismatch_refused(self):
        raw = b'an owned synthetic artifact fixture'
        mod = {'id': 'fixture', 'size': len(raw), 'hashes': {'sha512': hashlib.sha512(raw).hexdigest()}}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'artifact.jar'
            path.write_bytes(raw)
            self.assertTrue(upstream.verify_artifact(path, mod)['verified'])
            path.write_bytes(raw.replace(b'owned', b'wrong'))
            with self.assertRaises(UserError):
                upstream.verify_artifact(path, mod)


if __name__ == '__main__':
    unittest.main()
