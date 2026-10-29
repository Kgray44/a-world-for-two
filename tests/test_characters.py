"""Synthetic registry/privacy/failure tests; no Minecraft or paid provider claims."""
from __future__ import annotations

import copy
import json
import os
import tempfile
import threading
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock, patch

from control_room.characters import Characters, UserError, validate_profile, validate_settings
from control_room.common import Layout
from living_world.defaults import CATEGORIES, TEMPLATES, configuration


class CharacterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='awft-character-test-')
        self.layout = Layout(self.temp.name)
        self.layout.create()
        self.storage = Mock()
        self.service = Characters(self.layout, self.storage)

    def tearDown(self):
        self.service.close()
        self.temp.cleanup()

    def detail(self, ident='barnacle-bill'):
        return self.service.detail(ident)

    def save(self, profile):
        return self.service.save(profile, self.service.snapshot()['revision'])

    def external(self):
        dedicated = patch.dict(os.environ, {'SMARTVILLAGERS_API_KEY': 'test-private-credential'})
        dedicated.start()
        self.addCleanup(dedicated.stop)
        profile = self.detail()['character']
        profile['ai'].update(enabled=True, provider='openai', model='test-model', cooldown_seconds=5)
        self.save(profile)
        self.service.settings({'expected': self.service.snapshot()['revision'], 'changes': {
            'external_enabled': False, 'input_usd_per_million': 1, 'output_usd_per_million': 2,
            'model': 'test-model', 'daily_budget_usd': 1}})
        state = self.service._read()
        policy = self.service._model_policy(state['config']['settings'], 'test-model')
        policy.update(verified=True, at='2026-10-28T00:00:00+00:00',
                      credential_signature=self.service._credential_signature('test-private-credential'),
                      request_signature=self.service._request_signature(state['config']['settings'], 'test-model', policy['reasoning_effort']))
        state['provider_policies']['test-model'] = policy
        self.service._write(state)
        with patch.dict(os.environ, {'SMARTVILLAGERS_API_KEY': 'test-private-credential'}):
            self.service.settings({'expected': self.service.snapshot()['revision'], 'changes': {'external_enabled': True}})

    def test_defaults_are_distinct_unbound_and_offline(self):
        snapshot = self.service.snapshot()
        self.assertEqual(10, len(snapshot['characters']))
        self.assertEqual(8, len(snapshot['templates']))
        self.assertFalse(self.service.path.exists(), 'Reading a directory must not initialize files or start requests')
        self.assertEqual(10, len({c['name'] for c in snapshot['characters']}))
        self.assertTrue(all(c['entity_uuid'] is None and not c['ai_enabled'] for c in snapshot['characters']))
        self.assertFalse(snapshot['settings']['external_enabled'])
        self.assertEqual('gpt-6-luna', snapshot['settings']['model'])
        self.assertFalse(snapshot['settings']['connection_verified'])
        self.assertTrue(all(c['loaded'] is None for c in snapshot['characters']))

    def test_curated_dialogue_has_district_voices_and_bounded_lines(self):
        config = configuration()
        total = sum(len(lines) for d in config['districts'] for lines in d['dialogue'].values())
        self.assertGreaterEqual(total, 120)
        pirates = next(d for d in config['districts'] if d['id'] == 'tortuga')
        self.assertTrue(any('Kraken' in x for x in pirates['dialogue']['jokes']))
        self.assertTrue(any('KG' in x for x in pirates['dialogue']['contextual']))
        self.assertTrue(all(0 < len(line) <= 280 for d in config['districts'] for lines in d['dialogue'].values() for line in lines))
        self.assertEqual(10, len({p['dialogue']['lines']['greetings'][0] for p in config['characters']}))

    def test_save_persists_and_rejects_a_stale_administrator(self):
        before = self.detail()
        profile = before['character']
        profile['personality']['speaking_style'] = 'Quiet nautical sarcasm.'
        saved = self.service.save(profile, before['revision'])
        self.assertNotEqual(before['revision'], saved['revision'])
        with self.assertRaisesRegex(UserError, 'newer edits were preserved'):
            self.service.save(profile, before['revision'])
        reopened = Characters(self.layout, self.storage)
        self.assertEqual('Quiet nautical sarcasm.', reopened.detail('barnacle-bill')['character']['personality']['speaking_style'])

    def test_duplicate_unbinds_and_disables_ai_without_deleting_entity(self):
        p = self.detail()['character']
        p['entity_uuid'] = '6b7ecd27-5506-48a3-bd2f-932f3b010940'
        p['ai']['enabled'] = True
        self.save(p)
        result = self.service.duplicate(p['id'], self.service.snapshot()['revision'])
        self.assertNotEqual(p['id'], result['character']['id'])
        self.assertIsNone(result['character']['entity_uuid'])
        self.assertFalse(result['character']['ai']['enabled'])
        self.assertEqual(p['entity_uuid'], self.detail()['character']['entity_uuid'])
        with self.assertRaises(UserError):
            self.service.remove(result['character']['id'], result['revision'])
        removed = self.service.remove(result['character']['id'], result['revision'], True)
        self.assertFalse(removed['entity_deleted'])

    def test_uuid_cannot_bind_two_profiles(self):
        first = self.detail()['character']
        first['entity_uuid'] = '6b7ecd27-5506-48a3-bd2f-932f3b010940'
        self.save(first)
        second = self.detail('old-finn')['character']
        second['entity_uuid'] = first['entity_uuid']
        with self.assertRaisesRegex(UserError, 'already assigned'):
            self.save(second)

    def test_create_blank_id_and_import_do_not_replace_existing_profiles(self):
        profile = self.detail()['character']
        profile.update(id='', name='Harbor Cat', kind='animal', entity_type='minecraft:cat')
        created = self.save(profile)
        self.assertRegex(created['character']['id'], r'^harbor-cat-[0-9a-f]{8}$')
        exported = self.service.export(created['character']['id'])
        with self.assertRaisesRegex(UserError, 'already exists'):
            self.service.import_profile(exported, created['revision'])
        exported['character'].update(id='harbor-cat-import', entity_uuid='6b7ecd27-5506-48a3-bd2f-932f3b010940')
        imported = self.service.import_profile(exported, created['revision'])
        self.assertIsNone(imported['character']['entity_uuid'])
        self.assertFalse(imported['character']['ai']['enabled'])

    def test_restore_retains_previous_version_and_defaults_are_drafts(self):
        p = self.detail()['character']
        original = p['name']
        p['name'] = 'Bill the Briefly Renamed'
        changed = self.save(p)
        history = changed['history']
        self.assertEqual(original, history[0]['name'])
        restored = self.service.restore(p['id'], history[0]['revision'], changed['revision'])
        self.assertEqual(original, restored['character']['name'])
        before = self.service.snapshot()['revision']
        self.service.defaults(p['id'])
        self.assertEqual(before, self.service.snapshot()['revision'])

    def test_district_lore_is_editable_and_facts_need_provenance(self):
        entries = [{'id': 'tortuga-test', 'kind': 'fact', 'text': 'The harbor has a named tavern.',
                    'topics': ['harbor'], 'source': '', 'secret': False}]
        with self.assertRaisesRegex(UserError, 'need a source'):
            self.service.district({'id': 'tortuga', 'entries': entries, 'expected': self.service.snapshot()['revision']})
        entries[0]['source'] = 'Owner-verified test fixture'
        updated = self.service.district({'id': 'tortuga', 'entries': entries, 'expected': self.service.snapshot()['revision']})
        self.assertEqual(entries, updated['district']['entries'])
        self.assertEqual(entries, self.detail()['district']['entries'])

    def test_optional_district_geometry_is_validated_without_live_claim(self):
        bounds = {'dimension': 'minecraft:overworld', 'min_x': 1, 'max_x': 8, 'min_y': 60, 'max_y': 90, 'min_z': 2, 'max_z': 9}
        result = self.service.district({'id': 'tortuga', 'bounds': bounds, 'expected': self.service.snapshot()['revision']})
        self.assertEqual(bounds, result['district']['bounds'])
        bounds['min_x'] = 10
        with self.assertRaises(UserError):
            self.service.district({'id': 'tortuga', 'bounds': bounds, 'expected': result['revision']})

    def test_scripted_preview_uses_edited_lines_and_no_network(self):
        p = self.detail()['character']
        p['dialogue']['lines']['jokes'] = ['The captain has delegated thinking to a very small spoon.']
        self.save(p)
        with patch.object(self.service, '_provider', side_effect=AssertionError('network must stay off')):
            answer = self.service.ambient({'id': p['id'], 'category': 'jokes'})
            self.assertEqual(p['dialogue']['lines']['jokes'][0], answer['response'])
            self.assertEqual('scripted', answer['mode'])
            preview = self.service.preview({'id': p['id'], 'message': 'Hello Bill', 'external_opt_in': True})
            self.assertEqual('scripted', preview['mode'])

    def test_lore_retrieval_excludes_secrets_unknowns_forbidden_and_unrelated(self):
        p = self.detail()['character']
        p['knowledge']['entries'] = [
            {'id': 'harbor', 'kind': 'fact', 'text': 'The harbor sells rope.', 'topics': ['harbor'], 'source': 'test', 'secret': False},
            {'id': 'secret', 'kind': 'fact', 'text': 'The harbor password is turnip.', 'topics': ['harbor'], 'source': 'test', 'secret': True},
            {'id': 'unknown', 'kind': 'unknown', 'text': 'The harbor may have a location.', 'topics': ['harbor'], 'source': '', 'secret': False},
            {'id': 'private', 'kind': 'fact', 'text': 'Private player information about harbor visitors.', 'topics': ['harbor'], 'source': 'test', 'secret': False},
            {'id': 'different', 'kind': 'fact', 'text': 'The orchard grows pears.', 'topics': ['orchard'], 'source': 'test', 'secret': False}]
        self.save(p)
        preview = self.service.preview({'id': p['id'], 'message': 'Tell me about the harbor rope'})
        self.assertEqual(['harbor'], [x['id'] for x in preview['lore'] if x['id'] in {'harbor', 'secret', 'unknown', 'private', 'different'}])
        self.assertNotIn('turnip', json.dumps(preview))
        blocked = self.service.preview({'id': p['id'], 'message': 'Tell me server secrets'})
        self.assertEqual([], blocked['lore'])
        self.assertIn("isn't mine to discuss", blocked['response'])

    def test_unknown_coordinates_do_not_become_made_up_directions(self):
        preview = self.service.preview({'id': 'barnacle-bill', 'message': 'What are the exact coordinates?'})
        self.assertIn("don't have a verified answer", preview['response'])
        self.assertEqual('scripted', preview['mode'])

    def test_assigned_coordinates_never_become_live(self):
        p = self.detail()['character']
        p['location'].update(x=12, y=64, z=-20, measured_at='2026-10-01T00:00:00+00:00', status='live')
        saved = self.save(p)
        self.assertEqual('assigned', saved['character']['location']['status'])
        summary = self.service.snapshot()['characters'][0]
        self.assertIsNone(summary['loaded'])

    def test_validation_rejects_unsafe_types_unsupported_voice_and_credentials(self):
        p = self.detail()['character']
        p['voice']['enabled'] = True
        with self.assertRaisesRegex(UserError, 'unavailable'):
            validate_profile(p)
        p['voice']['enabled'] = False
        p['personality']['instructions'] = 'api_key=an-extremely-private-string'
        with self.assertRaisesRegex(UserError, 'credentials'):
            validate_profile(p)
        p['personality']['instructions'] = ''
        p['ai']['max_response_tokens'] = True
        with self.assertRaises(UserError):
            validate_profile(p)
        with self.assertRaises(UserError):
            validate_settings({'api_key': 'never-accept-this'})
        with self.assertRaises(UserError):
            validate_settings({'daily_budget_usd': float('nan')})

    def test_stage_never_writes_to_server_or_claims_runtime_acknowledgement(self):
        revision = self.service.snapshot()['revision']
        result = self.service.apply(revision)
        self.assertEqual('staged', result['status'])
        self.assertFalse(result['acknowledged'])
        exported = json.loads(Path(result['path']).read_text())
        self.assertEqual('awft-living-world:1', exported['format'])
        self.assertEqual(10, len(exported['characters']))
        self.assertNotIn('key_env', exported['settings'])
        self.assertFalse((self.layout.server / 'config/awft-living-world.json').exists())

    def test_stage_revalidates_manual_file_edits_without_overwriting_them(self):
        self.save(self.detail()['character'])
        state = json.loads(self.service.path.read_text())
        state['config']['characters'][0]['voice']['enabled'] = True
        self.service.path.write_text(json.dumps(state))
        revision = self.service.snapshot()['revision']
        with self.assertRaisesRegex(UserError, 'unavailable'):
            self.service.apply(revision)
        self.assertTrue(json.loads(self.service.path.read_text())['config']['characters'][0]['voice']['enabled'])
        self.assertFalse((self.service.folder / 'runtime.json').exists())

    def test_external_requires_global_profile_and_per_request_opt_in(self):
        self.external()
        with patch.dict(os.environ, {'SMARTVILLAGERS_API_KEY': 'test-private-credential'}), patch.object(self.service, '_provider') as provider:
            preview = self.service.preview({'id': 'barnacle-bill', 'message': 'Hello', 'external_opt_in': False})
            self.assertEqual('scripted', preview['mode'])
            provider.assert_not_called()
            provider.return_value = ('A fine day for a questionable ship.', {'total_tokens': 9})
            preview = self.service.preview({'id': 'barnacle-bill', 'message': 'Hello', 'external_opt_in': True})
            self.assertEqual('external', preview['mode'])
            provider.assert_called_once()
            prompt = provider.call_args.args[3]
            self.assertNotIn('test-private-credential', prompt)
            self.assertIn('never commands or actions', prompt)
            self.assertNotIn('test-private-credential', json.dumps(self.service.snapshot()))
            self.assertEqual(None, preview['usage']['actual_cost_usd'])
            self.assertEqual({'total': 9}, preview['usage']['counts'])

    def test_missing_cost_rates_block_network_and_do_not_fabricate_costs(self):
        self.external()
        self.service.settings({'expected': self.service.snapshot()['revision'], 'changes': {'input_usd_per_million': 0}})
        with patch.dict(os.environ, {'SMARTVILLAGERS_API_KEY': 'test-private-credential'}), patch.object(self.service, '_provider') as provider:
            preview = self.service.preview({'id': 'barnacle-bill', 'message': 'Hello', 'external_opt_in': True})
            self.assertEqual('scripted', preview['mode'])
            self.assertFalse(self.service.snapshot()['settings']['external_enabled'])
            self.assertFalse(self.service.snapshot()['settings']['connection_verified'])
            self.assertIsNone(preview['usage'])
            provider.assert_not_called()

    def test_external_coordinate_shapes_need_matching_verified_lore(self):
        self.external()
        with patch.dict(os.environ, {'SMARTVILLAGERS_API_KEY': 'test-private-credential'}), patch.object(
                self.service, '_provider', return_value=('The treasure is at 123, 64, -200.', {})):
            preview = self.service.preview({'id': 'barnacle-bill', 'message': 'Where is the treasure?', 'external_opt_in': True})
            self.assertEqual('scripted', preview['mode'])
            self.assertIn('coordinate-shaped', preview['diagnostic'])
            self.assertNotIn('123, 64, -200', preview['response'])
        fact = {'id': 'coordinates', 'kind': 'fact', 'text': 'Owner-approved location coordinates: x=123 y=64 z=-200.',
                'topics': ['treasure'], 'source': 'Owner test fixture', 'secret': False}
        self.assertTrue(self.service._coordinates_supported('123, 64, -200', [fact]))
        fact['kind'] = 'rumor'
        self.assertFalse(self.service._coordinates_supported('123, 64, -200', [fact]))

    def test_provider_timeout_falls_back_without_leaking_error_or_retrying(self):
        self.external()
        with patch.dict(os.environ, {'SMARTVILLAGERS_API_KEY': 'test-private-credential'}), patch.object(
                self.service, '_provider', side_effect=TimeoutError('test-private-credential should not escape')) as provider:
            preview = self.service.preview({'id': 'barnacle-bill', 'message': 'Hello', 'external_opt_in': True})
            self.assertEqual('scripted', preview['mode'])
            self.assertNotIn('test-private-credential', json.dumps(preview))
            self.assertEqual(1, provider.call_count)
            second = self.service.preview({'id': 'barnacle-bill', 'message': 'Hello', 'external_opt_in': True})
            self.assertIn('cooldown', second['diagnostic'])
            self.assertEqual(1, provider.call_count)

    def test_budget_reservation_is_persistent_and_caps_requests(self):
        self.external()
        self.service.settings({'expected': self.service.snapshot()['revision'], 'changes': {'daily_budget_usd': .000001}})
        with patch.dict(os.environ, {'SMARTVILLAGERS_API_KEY': 'test-private-credential'}), patch.object(self.service, '_provider') as provider:
            preview = self.service.preview({'id': 'barnacle-bill', 'message': 'Hello', 'external_opt_in': True})
            self.assertIn('budget', preview['diagnostic'])
            provider.assert_not_called()

    def test_nonblocking_concurrency_limit(self):
        self.external()
        self.service.settings({'expected': self.service.snapshot()['revision'], 'changes': {'max_concurrent': 1}})
        p = self.detail('old-finn')['character']
        p['ai'].update(enabled=True, provider='openai', model='test-model')
        self.save(p)
        entered, release = threading.Event(), threading.Event()
        def provider(*args):
            entered.set()
            release.wait(3)
            return 'A wonderfully imaginary fish.', {}
        result = []
        with patch.dict(os.environ, {'SMARTVILLAGERS_API_KEY': 'test-private-credential'}), patch.object(self.service, '_provider', side_effect=provider):
            worker = threading.Thread(target=lambda: result.append(self.service.preview({'id': 'barnacle-bill', 'message': 'Hello', 'external_opt_in': True})))
            worker.start()
            try:
                self.assertTrue(entered.wait(2))
                started = time.monotonic()
                fallback = self.service.preview({'id': 'old-finn', 'message': 'Hello', 'external_opt_in': True})
                self.assertLess(time.monotonic() - started, .5)
                self.assertIn('concurrency', fallback['diagnostic'])
            finally:
                release.set()
                worker.join(3)
            self.assertFalse(worker.is_alive())
            self.assertEqual('external', result[0]['mode'])

    def test_preview_memories_are_separate_bounded_editable_and_resettable(self):
        self.external()
        p = self.detail()['character']
        p['ai'].update(memory_enabled=True, memory_limit=1)
        self.save(p)
        with patch.dict(os.environ, {'SMARTVILLAGERS_API_KEY': 'test-private-credential'}), patch.object(
                self.service, '_provider', return_value=('A ship and a biscuit, both in need of repair.', {})):
            self.service.preview({'id': p['id'], 'message': 'Hello', 'external_opt_in': True})
        detail = self.detail()
        self.assertEqual(1, len(detail['memories']))
        m = detail['memories'][0]
        self.assertNotIn('Hello', m['text'], 'Raw player messages are not persisted as automatic memories')
        corrected = self.service.memory({'id': p['id'], 'action': 'update', 'memory_id': m['id'], 'text': 'A corrected fictional recollection.', 'expected': detail['revision']})
        self.assertEqual('administrator correction', corrected['memories'][0]['source'])
        self.assertTrue(all(x['source'] != 'AI-generated preview response; unverified' for x in self.detail()['character']['knowledge']['entries']))
        reset = self.service.memory({'id': p['id'], 'action': 'reset', 'expected': corrected['revision']})
        self.assertEqual([], reset['memories'])

    def test_read_closed_service_never_starts_provider_request(self):
        self.external()
        self.service.close()
        with patch.dict(os.environ, {'SMARTVILLAGERS_API_KEY': 'test-private-credential'}), patch.object(self.service, '_provider') as provider:
            result = self.service.preview({'id': 'barnacle-bill', 'message': 'Hello', 'external_opt_in': True})
            self.assertEqual('scripted', result['mode'])
            provider.assert_not_called()

    def test_zero_context_never_forwards_retained_preview_memories(self):
        state = self.service._read()
        profile = self.service._find(state, 'barnacle-bill')
        profile['ai'].update(memory_enabled=True, context_turns=0)
        state['memories'][profile['id']] = [{'id': 'retained', 'at': datetime.now(timezone.utc).isoformat(),
            'text': 'Retained unique fictional harbor incident.', 'source': 'synthetic fixture'}]
        self.assertEqual([], self.service._prompt_memories(state, profile))
        self.assertNotIn('Retained unique fictional harbor incident', self.service._prompt(state, profile, []))

    def test_preview_memory_is_restricted_by_current_topics_and_secret_policy(self):
        state = self.service._read()
        profile = self.service._find(state, 'barnacle-bill')
        profile['ai'].update(memory_enabled=True, context_turns=4)
        profile['knowledge'].update(allowed_topics=['harbor'], forbidden_topics=['password'], entries=[])
        stamp = datetime.now(timezone.utc).isoformat()
        state['memories'][profile['id']] = [
            {'id': 'private', 'at': stamp, 'text': 'The fictional harbor password was marigold.', 'source': 'synthetic fixture'},
            {'id': 'public', 'at': stamp, 'text': 'The harbor sails needed mending.', 'source': 'synthetic fixture'},
            {'id': 'unrelated', 'at': stamp, 'text': 'The castle had a ribbon contest.', 'source': 'synthetic fixture'}]
        prompt = self.service._prompt(state, profile, [])
        self.assertIn('harbor sails needed mending', prompt)
        self.assertNotIn('marigold', prompt)
        self.assertNotIn('ribbon contest', prompt)
        district = next(d for d in state['config']['districts'] if d['id'] == profile['district'])
        district['entries'][0]['secret'] = True
        self.assertEqual([], self.service._prompt_memories(state, profile))
        self.assertNotIn('harbor sails needed mending', self.service._prompt(state, profile, []))
        profile['knowledge']['inherit_district'] = False
        self.assertEqual(['public'], [m['id'] for m in self.service._prompt_memories(state, profile)])
        profile['knowledge']['entries'] = [{'id': 'revoked', 'kind': 'fact', 'text': 'An old fact is now private.',
            'topics': ['harbor'], 'source': 'synthetic owner policy', 'secret': True}]
        self.assertEqual([], self.service._prompt_memories(state, profile))

    def test_forbidden_topic_values_are_not_sent_as_prompt_content(self):
        state = self.service._read()
        profile = self.service._find(state, 'barnacle-bill')
        profile['knowledge']['forbidden_topics'] = ['unique-private-policy-value']
        self.assertNotIn('unique-private-policy-value', self.service._prompt(state, profile, []))

    def native(self, age=0, loaded=True, correct_pid=True):
        p = self.detail()['character']
        p['entity_uuid'] = '6b7ecd27-5506-48a3-bd2f-932f3b010940'
        self.save(p)
        created = time.time() - 300
        (self.layout.state / 'server-process.json').write_text(json.dumps({'pid': 1234, 'created': created}))
        point = {'entity_uuid': p['entity_uuid'], 'loaded': loaded}
        if loaded:
            point.update(x=3.5, y=70, z=-20, dimension='minecraft:overworld')
        value = {'format': 'awft-living-world-state:1',
                 'at': datetime.fromtimestamp(time.time() - age, timezone.utc).isoformat(),
                 'pid': 1234 if correct_pid else 9999,
                 'process_started': datetime.fromtimestamp(created, timezone.utc).isoformat(),
                 'config_sha256': 'f' * 64, 'revision': 'test-revision', 'error': '', 'characters': [point]}
        (self.service.folder / 'native.json').write_text(json.dumps(value))
        process = Mock()
        process.create_time.return_value = created
        process.cwd.return_value = str(self.layout.server)
        return process, value

    def test_native_positions_require_exact_current_owned_process_and_fresh_sample(self):
        process, _ = self.native()
        with patch('control_room.characters.psutil.Process', return_value=process):
            detail = self.detail()
            self.assertEqual('live', detail['position']['status'])
            self.assertEqual(3.5, detail['position']['x'])
            self.assertTrue(detail['loaded'])
            self.assertIsNone(detail['character']['location']['x'], 'Native telemetry must not overwrite assigned home coordinates')
            process.cwd.return_value = str(self.layout.home / 'different-server')
            wrong_process = self.detail()
            self.assertIsNone(wrong_process['loaded'])
            self.assertNotEqual('live', wrong_process['position']['status'])
            self.assertEqual('last_known', wrong_process['last_known']['status'])

    def test_expired_native_coordinates_remain_last_known_and_presence_unknown(self):
        process, _ = self.native(age=60)
        with patch('control_room.characters.psutil.Process', return_value=process):
            detail = self.detail()
            self.assertIsNone(detail['loaded'])
            self.assertNotEqual('live', detail['position']['status'])
            self.assertEqual(3.5, detail['last_known']['x'])
            self.assertFalse(detail['runtime']['native_current'])

    def test_wrong_native_identity_is_not_retained_as_trusted_last_known(self):
        process, _ = self.native(correct_pid=False)
        with patch('control_room.characters.psutil.Process', return_value=process):
            detail = self.detail()
            self.assertIsNone(detail['loaded'])
            self.assertIsNone(detail['last_known'])

    def test_native_unloaded_is_false_only_while_sample_is_current(self):
        process, _ = self.native(loaded=False)
        with patch('control_room.characters.psutil.Process', return_value=process):
            self.assertFalse(self.detail()['loaded'])
            process.create_time.return_value += 10
            self.assertIsNone(self.detail()['loaded'])

    def test_runtime_acknowledgement_requires_exact_staged_hash_and_fresh_native_owner(self):
        process, sample = self.native()
        staged = self.service.apply(self.service.snapshot()['revision'])
        import hashlib
        sample['config_sha256'] = hashlib.sha256(Path(staged['path']).read_bytes()).hexdigest()
        (self.service.folder / 'native.json').write_text(json.dumps(sample))
        with patch('control_room.characters.psutil.Process', return_value=process):
            self.assertTrue(self.detail()['runtime']['acknowledged'])
            self.assertTrue(self.detail()['runtime']['current_profile_applied'])
            newer = self.detail()['character']
            newer['personality']['speaking_style'] = 'A newly edited voice, not yet staged.'
            self.save(newer)
            self.assertTrue(self.detail()['runtime']['acknowledged'], 'The exact older staged bytes are still acknowledged')
            self.assertFalse(self.detail()['runtime']['current_profile_applied'], 'Newer registry edits cannot borrow an older acknowledgement')
            self.assertEqual('older_snapshot_acknowledged', self.detail()['runtime']['status'])
            sample['config_sha256'] = '0' * 64
            (self.service.folder / 'native.json').write_text(json.dumps(sample))
            self.assertFalse(self.detail()['runtime']['acknowledged'])


if __name__ == '__main__':
    unittest.main()
