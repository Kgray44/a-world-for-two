"""Credential and provider policy regressions. No external API or game is called."""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock, patch

from control_room.character_secrets import CredentialStore, PREFIX, server_environment
from control_room.characters import Characters, OPENAI_ENDPOINT, UserError, validate_settings
from control_room.common import Layout

KEY = 'sk-synthetic-owner-test-credential-1234567890'


class ProviderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='awft-provider-')
        self.layout = Layout(Path(self.temp.name) / 'runtime')
        self.layout.create()
        self.service = Characters(self.layout, Mock())
        self.service.credentials = CredentialStore(self.layout, Mock(), root=Path(self.temp.name) / 'outside-runtime-secrets')

    def tearDown(self):
        self.service.close()
        self.temp.cleanup()

    def settings(self, **changes):
        return self.service.settings({'changes': changes, 'expected': self.service.snapshot()['revision']})

    def configure(self):
        self.settings(model='gpt-6-luna', reasoning_effort='none', input_usd_per_million=.1, output_usd_per_million=.5)

    def connection(self, model=None):
        body = {'expected': self.service.snapshot()['revision'], 'external_opt_in': True}
        if model:
            body['model'] = model
        return self.service.test_connection(body)

    def test_actual_windows_user_bound_dpapi_roundtrip_is_outside_runtime_and_not_plaintext(self):
        if os.name != 'nt':
            self.skipTest('Actual Windows user-bound DPAPI is host-specific')
        self.service.credentials.save(KEY)
        path = self.service.credentials.path
        raw = path.read_bytes()
        self.assertTrue(raw.startswith(PREFIX))
        self.assertNotIn(KEY.encode(), raw)
        self.assertFalse(path.is_relative_to(self.layout.home))
        key, source = self.service.credentials.load({})
        self.assertEqual(KEY, key)
        self.assertEqual('windows_user_store', source)
        different_home = Layout(Path(self.temp.name) / 'different-runtime')
        other = CredentialStore(different_home, root=self.service.credentials.root)
        # Entropy and path are bound to the exact runtime identity.
        self.assertEqual(('', 'not_configured'), other.load({}))

    def test_credential_entry_never_returns_or_persists_plaintext_and_disables_old_policies(self):
        self.configure()
        with patch.dict(os.environ, {'SMARTVILLAGERS_API_KEY': ''}), patch('control_room.character_secrets._crypt',
                side_effect=lambda raw, entropy, decrypt=False: KEY.encode() if decrypt else b'opaque-dpapi-fixture'):
            result = self.service.credential({'api_key': KEY, 'expected': self.service.snapshot()['revision']})
            self.assertTrue(result['credential_configured'])
            self.assertTrue(result['restart_required'])
            self.assertFalse(self.service.snapshot()['settings']['external_enabled'])
            exported = self.service.export_configuration()
            self.assertNotIn(KEY, json.dumps(result))
            self.assertNotIn(KEY, self.service.path.read_text())
            self.assertNotIn(KEY, json.dumps(exported))
            self.assertNotIn(KEY, json.dumps(self.service.snapshot()))
            self.assertFalse(any(self.layout.server.rglob('*.dpapi')))

    def test_environment_managed_key_rejects_ignored_replacement_and_ambient_is_never_discovered(self):
        with patch.dict(os.environ, {'SMARTVILLAGERS_API_KEY': KEY}), patch.object(self.service.credentials, 'save') as save:
            with self.assertRaisesRegex(UserError, 'already manages'):
                self.service.credential({'api_key': 'another-synthetic-credential', 'expected': self.service.snapshot()['revision']})
            save.assert_not_called()
        self.assertEqual(('', 'not_configured'), self.service.credentials.load({'OPENAI_API_KEY': KEY}))
        with self.assertRaisesRegex(UserError, 'ambient API keys'):
            validate_settings({'key_env': 'OPENAI_API_KEY'})

    def test_unavailable_protection_has_no_plaintext_fallback(self):
        with patch('control_room.character_secrets._crypt', side_effect=UserError('DPAPI unavailable')):
            with self.assertRaises(UserError):
                self.service.credentials.save(KEY)
        self.assertFalse(self.service.credentials.path.exists())

    def test_scripted_startup_survives_missing_or_corrupt_credentials_and_removes_ambient_key(self):
        with patch('control_room.character_secrets.CredentialStore.load', side_effect=UserError('protected credential unavailable')):
            environment = server_environment(self.layout, {'OPENAI_API_KEY': KEY, 'UNRELATED': 'kept'})
        self.assertNotIn('OPENAI_API_KEY', environment)
        self.assertNotIn('SMARTVILLAGERS_API_KEY', environment)
        self.assertEqual('kept', environment['UNRELATED'])
        with patch('control_room.character_secrets.CredentialStore.load', return_value=(KEY, 'windows_user_store')):
            environment = server_environment(self.layout, {'OPENAI_API_KEY': 'ambient-unused', 'UNRELATED': 'kept'})
        self.assertEqual(KEY, environment['SMARTVILLAGERS_API_KEY'])
        self.assertNotIn('OPENAI_API_KEY', environment)

    def test_current_connection_verification_is_required_and_no_display_or_save_calls_api(self):
        with patch.dict(os.environ, {'SMARTVILLAGERS_API_KEY': KEY}), patch.object(self.service, '_provider') as provider, patch.object(self.service, '_models') as models:
            self.configure()
            self.service.snapshot()
            with self.assertRaisesRegex(UserError, 'Test Connection'):
                self.settings(external_enabled=True)
            provider.assert_not_called()
            models.assert_not_called()
            with self.assertRaisesRegex(UserError, 'Explicitly authorize'):
                self.service.test_connection({'expected': self.service.snapshot()['revision']})

    def test_context_free_connection_records_real_returned_counts_and_safe_status(self):
        with patch.dict(os.environ, {'SMARTVILLAGERS_API_KEY': KEY}), patch.object(self.service, '_models', return_value=['gpt-6-luna']), patch.object(
                self.service, '_provider', return_value=('OK', {'prompt_tokens': 18, 'completion_tokens': 2, 'total_tokens': 20})) as request:
            self.configure()
            result = self.connection()
            self.assertTrue(result['verified'])
            self.assertTrue(result['connection_current'])
            self.assertEqual({'input': 18, 'output': 2, 'total': 20}, result['usage']['counts'])
            prompt, message = request.call_args.args[3:5]
            self.assertNotIn('Barnacle', prompt + message)
            self.assertNotIn('Tortuga', prompt + message)
            self.assertNotIn(KEY, prompt + message)
            self.settings(external_enabled=True)
            status = self.service.provider_status()
            self.assertTrue(status['verified'])
            self.assertTrue(status['external_enabled'])
            self.assertEqual(20, status['usage']['measured_counts']['total'])
            self.assertIsNone(status['usage']['actual_cost_usd'])
            self.assertEqual('connection_test', status['last_successful_call']['kind'])
            self.assertNotIn(KEY, json.dumps(status))
            exported = self.service.export_configuration()
            self.assertTrue(exported['provider_verification']['verified'])
            self.assertNotIn('credential_signature', json.dumps(exported))

    def test_multiple_tested_models_are_retained_with_sol_rates_and_safe_low_effort(self):
        with patch.dict(os.environ, {'SMARTVILLAGERS_API_KEY': KEY}), patch.object(self.service, '_models', return_value=['gpt-6-luna', 'gpt-6.1-sol']), patch.object(
                self.service, '_provider', return_value=('OK', {'prompt_tokens': 10, 'completion_tokens': 2, 'total_tokens': 12})):
            self.configure()
            self.assertTrue(self.connection()['verified'])
            self.assertTrue(self.connection('gpt-6.1-sol')['verified'])
            exported = self.service.export_configuration()
            self.assertEqual('gpt-6-luna', exported['settings']['model'])
            policies = exported['provider_verification']['model_policies']
            self.assertEqual({'gpt-6-luna', 'gpt-6.1-sol'}, set(policies))
            self.assertEqual('low', policies['gpt-6.1-sol']['reasoning_effort'])
            self.assertEqual(2, policies['gpt-6.1-sol']['input_usd_per_million'])
            self.assertEqual(10, policies['gpt-6.1-sol']['output_usd_per_million'])
            self.assertFalse(policies['gpt-6.1-sol']['temperature_supported'])

    def test_custom_account_accepted_model_is_supported_without_invented_reasoning_support(self):
        with patch.dict(os.environ, {'SMARTVILLAGERS_API_KEY': KEY}), patch.object(self.service, '_models', return_value=[]), patch.object(
                self.service, '_provider', return_value=('OK', {'total_tokens': 5})):
            self.settings(model='owner-custom-model', input_usd_per_million=1, output_usd_per_million=2)
            result = self.connection()
            self.assertTrue(result['verified'])
            self.assertFalse(result['model_listed'])
            policy = self.service.export_configuration()['provider_verification']['model_policies']['owner-custom-model']
            self.assertFalse(policy['reasoning_supported'])
            self.assertFalse(policy['temperature_supported'])

    def test_credential_or_request_policy_change_invalidates_enable_and_keeps_fallback(self):
        with patch.dict(os.environ, {'SMARTVILLAGERS_API_KEY': KEY}), patch.object(self.service, '_models', return_value=['gpt-6-luna']), patch.object(self.service, '_provider', return_value=('OK', {})):
            self.configure()
            self.connection()
            self.settings(external_enabled=True)
            self.settings(response_tokens=256)
            self.assertFalse(self.service.snapshot()['settings']['external_enabled'])
            self.assertFalse(self.service.snapshot()['settings']['connection_verified'])
        with patch.dict(os.environ, {'SMARTVILLAGERS_API_KEY': 'a-different-dedicated-owner-credential'}):
            self.assertEqual([], self.service.snapshot()['settings']['verified_models'])

    def test_provider_failure_is_sanitized_and_does_not_verify_or_retry(self):
        with patch.dict(os.environ, {'SMARTVILLAGERS_API_KEY': KEY}), patch.object(self.service, '_models', side_effect=TimeoutError(KEY)) as models, patch.object(self.service, '_provider') as provider:
            self.configure()
            result = self.connection()
            self.assertFalse(result['verified'])
            self.assertNotIn(KEY, json.dumps(result))
            self.assertNotIn(KEY, json.dumps(self.service.provider_status()))
            self.assertEqual(1, models.call_count)
            provider.assert_not_called()
            self.assertFalse(self.service.snapshot()['settings']['connection_verified'])

    def test_rpm_and_daily_allowances_are_persistent_and_disable_external_on_daily_exhaustion(self):
        with patch.dict(os.environ, {'SMARTVILLAGERS_API_KEY': KEY}), patch.object(self.service, '_models', return_value=['gpt-6-luna']), patch.object(self.service, '_provider', return_value=('OK', {})) as provider:
            self.configure()
            self.settings(requests_per_day=1)
            self.assertTrue(self.connection()['verified'])
            self.settings(external_enabled=True)
            second = self.connection()
            self.assertFalse(second['verified'])
            self.assertIn('Daily', second['diagnostic'])
            self.assertFalse(self.service.snapshot()['settings']['external_enabled'])
            self.assertIn('Daily', self.service.provider_status()['auto_disabled_reason'])
            self.assertEqual(1, provider.call_count)

    def test_shared_native_reservation_limits_preview_spending_without_resetting_old_charges(self):
        with patch.dict(os.environ, {'SMARTVILLAGERS_API_KEY': KEY}), patch.object(self.service, '_models', return_value=['gpt-6-luna']), patch.object(self.service, '_provider', return_value=('OK', {'total_tokens': 5})) as provider:
            self.configure()
            self.connection()
            self.settings(external_enabled=True, daily_budget_usd=.001)
            path = self.service.folder / 'native-budget.json'
            ledger = json.loads(path.read_text())
            old_preview = ledger['preview_reserved_usd']
            ledger.update(day=datetime.now(timezone.utc).date().isoformat(), reserved_usd=.001 - old_preview - .000001,
                          day_requests=1, requests=[], day_usage={'prompt_tokens': 10, 'completion_tokens': 1, 'total_tokens': 11})
            path.write_text(json.dumps(ledger))
            result = self.connection()
            self.assertFalse(result['verified'])
            self.assertIn('budget', result['diagnostic'])
            self.assertEqual(1, provider.call_count)
            retained = json.loads(path.read_text())
            self.assertEqual(ledger['reserved_usd'], retained['reserved_usd'])
            self.assertEqual(old_preview, retained['preview_reserved_usd'])
            self.assertFalse(self.service.snapshot()['settings']['external_enabled'])
            status = self.service.provider_status()
            self.assertAlmostEqual(old_preview + ledger['reserved_usd'], status['usage']['reserved_cost_today_usd'])
            self.assertEqual(16, status['usage']['measured_counts']['total'])

    def test_shared_spending_lock_is_nonblocking_and_prevents_an_unrecorded_call(self):
        with patch.dict(os.environ, {'SMARTVILLAGERS_API_KEY': KEY}), patch.object(self.service, '_models') as models, patch.object(self.service, '_provider') as provider:
            self.configure()
            with self.service._spending_lock():
                result = self.connection()
            self.assertFalse(result['verified'])
            self.assertIn('ledger', result['diagnostic'])
            models.assert_not_called()
            provider.assert_not_called()

    def test_prior_preview_charges_seed_shared_summary_without_refund(self):
        with patch.dict(os.environ, {'SMARTVILLAGERS_API_KEY': KEY}), patch.object(self.service, '_models', return_value=['gpt-6-luna']), patch.object(self.service, '_provider', return_value=('OK', {})):
            self.configure()
            self.connection()
            path = self.service.folder / 'native-budget.json'
            ledger = json.loads(path.read_text())
            old = ledger['preview_reserved_usd']
            for key in list(ledger):
                if key.startswith('preview_'):
                    del ledger[key]
            path.write_text(json.dumps(ledger))
            self.assertTrue(self.connection()['verified'])
            migrated = json.loads(path.read_text())
            self.assertEqual(2, migrated['preview_day_requests'])
            self.assertGreater(migrated['preview_reserved_usd'], old)

    def test_runtime_external_flag_is_fail_closed_until_current_updated_adapter(self):
        with patch.dict(os.environ, {'SMARTVILLAGERS_API_KEY': KEY}), patch.object(self.service, '_models', return_value=['gpt-6-luna']), patch.object(self.service, '_provider', return_value=('OK', {})):
            self.configure()
            self.connection()
            self.settings(external_enabled=True)
            self.assertFalse(self.service.export_configuration()['settings']['external_enabled'])
            result = self.service.apply(self.service.snapshot()['revision'])
            self.assertFalse(result['external_enabled'])
            self.assertIn('Apply again', result['note'])
            self.assertTrue(self.service.snapshot()['settings']['external_enabled'], 'Desired settings must be retained')
            native = {'current': True, 'characters': [], 'adapter_version': '0.2.0',
                      'capabilities': ['generation_policy', 'verified_model_gate', 'per_character_model', 'returned_usage'],
                      'provider': {'credential_configured': True, 'credential_fingerprint': self.service._credential_signature(KEY)}}
            with patch.object(self.service, '_native', return_value=native):
                self.assertTrue(self.service.export_configuration()['settings']['external_enabled'])
                self.assertTrue(self.service.snapshot()['capabilities']['runtime']['per_npc_model'])
                self.assertNotIn(self.service._credential_signature(KEY), json.dumps(self.service.provider_status()))
                native['provider']['credential_fingerprint'] = '0' * 64
                self.assertFalse(self.service.export_configuration()['settings']['external_enabled'])
                self.assertTrue(self.service.provider_status()['restart_required'])

    def test_provider_status_merges_sanitized_native_outcomes_using_recorded_start_times(self):
        self.configure()
        now = time.time()
        state = self.service._read()
        state['provider_status']['last_successful_call'] = {
            'at': datetime.fromtimestamp(now - 30, timezone.utc).isoformat(), 'model': 'gpt-6-luna',
            'kind': 'connection_test', 'counts': {'total': 3}, 'latency_ms': 10}
        self.service._write(state)
        rows = [
            {'at': (now - 20) * 1000, 'latency_ms': 400, 'model': 'gpt-6.1-sol', 'status': 'ok',
             'dispatched': True, 'usage': {'prompt_tokens': 10, 'completion_tokens': 5, 'total_tokens': 15},
             'raw_error': KEY, 'reply': 'Private test content must not be returned'},
            {'at': (now - 10) * 1000, 'latency_ms': 15000, 'requested_model': 'gpt-6-luna', 'status': 'deadline',
             'dispatched': True, 'raw_error': KEY}]
        ledger = {'format': 'awft-native-ai-usage:2', 'day': datetime.now(timezone.utc).date().isoformat(),
                  'day_requests': 2, 'day_dispatched': 2, 'reserved_usd': .001, 'requests': rows}
        path = self.service.folder / 'native-budget.json'
        path.write_text(json.dumps(ledger))
        native = {'current': True, 'characters': [], 'adapter_version': '0.2.0', 'capabilities': ['returned_usage']}
        with patch.object(self.service, '_native', return_value=native):
            status = self.service.provider_status()
            self.assertEqual('minecraft', status['last_successful_call']['kind'])
            self.assertEqual('gpt-6.1-sol', status['last_successful_call']['model'])
            self.assertEqual(15, status['last_successful_call']['counts']['total'])
            self.assertIn('start time', status['last_successful_call']['time_basis'])
            self.assertEqual('minecraft_deadline', status['last_error']['code'])
            self.assertNotIn(KEY, json.dumps(status))
            self.assertNotIn('Private test content', json.dumps(status))
            rows.append({'at': (now - 5) * 1000, 'latency_ms': 300, 'model': 'gpt-6-luna', 'status': 'ok', 'dispatched': True})
            path.write_text(json.dumps(ledger))
            self.assertIsNone(self.service.provider_status()['last_error'], 'A later successful recorded request clears the older error state')

    def test_stale_native_or_undispatched_success_cannot_become_last_successful_call(self):
        self.configure()
        ledger = {'format': 'awft-native-ai-usage:2', 'day': datetime.now(timezone.utc).date().isoformat(),
                  'requests': [{'at': time.time() * 1000, 'latency_ms': 10, 'model': 'gpt-6-luna',
                                'status': 'ok', 'dispatched': False}]}
        (self.service.folder / 'native-budget.json').write_text(json.dumps(ledger))
        native = {'current': True, 'characters': [], 'capabilities': ['returned_usage']}
        with patch.object(self.service, '_native', return_value=native):
            self.assertIsNone(self.service.provider_status()['last_successful_call'])
            ledger['requests'][0]['dispatched'] = True
            (self.service.folder / 'native-budget.json').write_text(json.dumps(ledger))
            native['current'] = False
            status = self.service.provider_status()
            self.assertIsNone(status['last_successful_call'])
            self.assertFalse(status['native_usage']['available'])

    def test_openai_payload_sends_temperature_only_when_supported_and_never_for_reasoning_modes(self):
        response = Mock()
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        response.read.return_value = json.dumps({'model': 'gpt-6-luna', 'choices': [{'message': {'content': 'OK'}}], 'usage': {'total_tokens': 7}}).encode()
        opener = Mock()
        opener.open.return_value = response
        with patch('control_room.characters.urllib.request.build_opener', return_value=opener):
            settings = validate_settings({'model': 'gpt-6-luna'})
            policy = self.service._model_policy(settings, 'gpt-6-luna')
            self.service._provider('openai', 'gpt-6-luna', KEY, 'test', 'OK', {'max_response_tokens': 120, 'temperature': .7, '_policy': policy}, 3)
            body = json.loads(opener.open.call_args.args[0].data)
            self.assertEqual('none', body['reasoning_effort'])
            self.assertEqual(.7, body['temperature'])
            policy['reasoning_effort'] = 'low'
            self.service._provider('openai', 'gpt-6-luna', KEY, 'test', 'OK', {'max_response_tokens': 120, 'temperature': .7, '_policy': policy}, 3)
            self.assertNotIn('temperature', json.loads(opener.open.call_args.args[0].data))
            self.assertEqual(OPENAI_ENDPOINT, opener.open.call_args.args[0].full_url)


if __name__ == '__main__':
    unittest.main()
