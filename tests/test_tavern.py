"""Tavern display/control tests; no game, live backend or native command runs."""
from datetime import datetime, timezone, timedelta
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
import uuid
from unittest.mock import Mock

from control_room.common import UserError, write_json
from control_room.tavern import Tavern
from control_room.web import Application, make_handler


class TavernTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='awft-tavern-test-')
        self.addCleanup(temporary.cleanup)
        self.send_command = Mock()
        self.service = Tavern(Path(temporary.name), self.send_command)
        self.status = {
            'at': datetime.now(timezone.utc).isoformat(), 'paused': False, 'music': True,
            'suspended': True, 'runtime_accepted': False, 'fault': '',
            'residents': [
                {'id': 'mara-reef', 'uuid': '2d12b682-0be4-3a42-9f41-81831d843e81',
                 'name': 'Mara Reef', 'registered': True, 'loaded': False, 'activity': 'idle'},
                {'id': 'kit-cordage', 'uuid': 'f074e996-0439-4b8c-9d14-77fe207def3e',
                 'name': 'Kit Cordage', 'registered': True, 'loaded': True, 'activity': 'walking'}]}
        self.save_status()

    def save_status(self):
        write_json(self.service.path, self.status)

    def test_current_counts_are_separate_from_completed_life_admissions(self):
        write_json(self.service.life_path, {
            'operation': 'seed', 'finished': '2026-10-30T01:23:56Z', 'members': 5,
            'spawned': 5, 'existing_preserved': 0, 'failures': 0, 'cleanup_passed': True,
            'projected_managed_population_if_cohort_complete': 309})
        result = self.service.snapshot()
        self.assertTrue(result['current'])
        self.assertEqual(result['counts'], {'registered': 2, 'loaded': 1, 'roster': 2})
        self.assertEqual(result['life_admission']['registered_total'], 309)
        self.assertIn('not a live census', result['life_admission']['scope'])
        self.assertIn('Awaiting visual, behavior and audio', result['qualification'])
        self.assertNotIn('villagers', result['counts'])
        self.send_command.assert_not_called()

    def test_stale_and_future_reports_keep_last_counts_but_refuse_actions(self):
        for offset in (-60, 60):
            with self.subTest(offset=offset):
                self.status['at'] = (datetime.now(timezone.utc) + timedelta(seconds=offset)).isoformat()
                self.save_status()
                result = self.service.snapshot()
                self.assertFalse(result['current'])
                self.assertEqual(result['counts']['registered'], 2)
                with self.assertRaises(UserError):
                    self.service.control({'action': 'music', 'enabled': False})
        self.send_command.assert_not_called()

    def test_requested_45_patron_roster_is_visible_but_larger_reports_are_rejected(self):
        self.status['residents'] = [
            {'id': f'patron-{i}', 'uuid': str(uuid.UUID(int=i + 1)),
             'registered': True, 'loaded': True} for i in range(45)]
        self.save_status()
        self.assertEqual(self.service.snapshot()['counts'],
                         {'registered': 45, 'loaded': 45, 'roster': 45})
        self.status['residents'].append(
            {'id': 'extra-patron', 'uuid': str(uuid.UUID(int=46)),
             'registered': True, 'loaded': True})
        self.save_status()
        self.assertFalse(self.service.snapshot()['current'])
        self.assertIsNone(self.service.snapshot()['counts']['registered'])

    def test_an_unfinished_or_failed_life_projection_is_not_a_population_count(self):
        for details in ({}, {'finished': '2026-10-30T01:23:56Z', 'error': 'held'}):
            write_json(self.service.life_path, {
                'operation': 'seed', 'members': 5, 'spawned': 1, 'failures': 0,
                'cleanup_passed': True, 'projected_managed_population_if_cohort_complete': 999,
                **details})
            self.assertIsNone(self.service.snapshot()['life_admission'])

    def test_missing_oversized_and_duplicate_data_do_not_become_zero_presence(self):
        self.service.path.unlink()
        self.assertIsNone(self.service.snapshot()['counts']['loaded'])
        self.service.path.write_bytes(b' ' * (128 * 1024 + 1))
        self.assertFalse(self.service.snapshot()['current'])
        self.status['residents'][1]['uuid'] = self.status['residents'][0]['uuid']
        self.save_status()
        self.assertFalse(self.service.snapshot()['current'])
        with self.assertRaises(UserError):
            self.service.control({'action': 'suspend', 'suspended': True})
        self.send_command.assert_not_called()

    def test_controls_are_typed_confirmed_requests_not_runtime_acknowledgements(self):
        before = self.service.path.read_bytes()
        music = self.service.control({'action': 'music', 'enabled': False})
        suspend = self.service.control({'action': 'suspend', 'suspended': True})
        self.assertFalse(music['runtime_acknowledged'])
        self.assertFalse(suspend['runtime_acknowledged'])
        self.assertEqual(self.send_command.call_args_list[0].args, ('awfttavern music false',))
        self.assertEqual(self.send_command.call_args_list[1].args, ('awfttavern suspend true',))
        self.assertTrue(all(call.kwargs == {'confirmed': True} for call in self.send_command.call_args_list))
        for body in ({'action': 'music', 'enabled': 'false'}, {'action': 'suspend', 'suspended': 1},
                     {'action': 'initialize'}, {'action': 'resident', 'id': 'mara-reef\nstop'}):
            with self.assertRaises(UserError):
                self.service.control(body)
        self.assertEqual(self.send_command.call_count, 2)
        self.assertEqual(self.service.path.read_bytes(), before)

    def test_fault_allows_stopping_but_not_resuming(self):
        self.status['fault'] = 'Native path error'
        self.save_status()
        with self.assertRaises(UserError):
            self.service.control({'action': 'suspend', 'suspended': False})
        with self.assertRaises(UserError):
            self.service.control({'action': 'music', 'enabled': True})
        self.service.control({'action': 'suspend', 'suspended': True})
        self.assertEqual(self.send_command.call_count, 1)

    def test_routes_reuse_existing_origin_and_current_token_admission(self):
        app = Application.__new__(Application)
        app.tavern, app.token = self.service, 'current-fixture-token'
        self.assertEqual(app.get('/api/tavern', {})['counts']['registered'], 2)
        handler_type = make_handler(app)
        for origin, token, expected in (
                ('http://foreign.example', app.token, 403),
                ('http://localhost:8766', 'old-token', 403),
                ('http://localhost:8766', app.token, 200)):
            handler = handler_type.__new__(handler_type)
            handler.server = SimpleNamespace(server_port=8766)
            handler.client_address = ('127.0.0.1', 12345)
            body = json.dumps({'action': 'music', 'enabled': False}).encode()
            handler.headers = {'Host': 'localhost:8766', 'Origin': origin, 'X-AWFT-CSRF': token,
                               'Content-Type': 'application/json', 'Content-Length': str(len(body))}
            handler.path, handler.rfile, handler.send = '/api/tavern/control', io.BytesIO(body), Mock()
            handler.do_POST()
            self.assertEqual(handler.send.call_args.args[0], expected)
        self.assertEqual(self.send_command.call_count, 1)


if __name__ == '__main__':
    unittest.main()
