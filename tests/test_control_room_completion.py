"""Synthetic concurrency, restart and evidence-boundary regressions; no Minecraft JVM."""
import json
import threading
import time
from unittest.mock import Mock, patch

from control_room.atlas import Atlas
from control_room.common import UserError, read_json, utcnow, write_json
from control_room.jobs import HISTORY_BYTES, Jobs
from control_room.metrics import Metrics
from control_room.web import Application
from test_safety import Fixture


class AtlasInventoryTests(Fixture):
    def setUp(self):
        super().setUp()
        self.players = Mock()
        self.players.snapshot.return_value = {'members': []}
        self.metrics = Mock()
        self.metrics.latest.return_value = {}
        self.atlas = Atlas(self.layout, self.storage, self.server, self.players, self.metrics)
        self.addCleanup(self.atlas.close)

    def completed(self, force=False):
        self.atlas.cache(force=force)
        self.atlas._inventory_worker.join(3)
        self.assertFalse(self.atlas._inventory_worker.is_alive())
        return self.atlas.cache()

    def test_first_scan_is_unknown_and_concurrent_requests_do_not_wait_or_spawn_more_workers(self):
        entered, release = threading.Event(), threading.Event()
        self.addCleanup(release.set)
        def delayed(epoch):
            entered.set()
            release.wait(3)
        with patch.object(self.atlas, '_measure_cache', side_effect=delayed) as scan:
            first = self.atlas.cache()
            self.assertTrue(entered.wait(1))
            self.assertIsNone(first['bytes'])
            self.assertFalse(first['current'])
            readers = [threading.Thread(target=self.atlas.snapshot) for _ in range(12)]
            for reader in readers:
                reader.start()
            for reader in readers:
                reader.join(1)
                self.assertFalse(reader.is_alive(), 'Atlas GET waited for its inventory scan')
            self.assertEqual(scan.call_count, 1)
            release.set()
            self.atlas._inventory_worker.join(1)

    def test_inventory_is_timestamped_and_subsecond_tile_change_invalidates_revision(self):
        tile = self.atlas.root / 'minecraft_overworld/3/0_0.png'
        tile.parent.mkdir(parents=True)
        tile.write_bytes(b'metadata-only test fixture')
        before = self.completed()
        self.assertEqual(before['bytes'], tile.stat().st_size)
        self.assertEqual(before['tiles'], 1)
        self.assertTrue(before['current'])
        self.assertTrue(before['measured_at'])
        tile.write_bytes(b'changed test tile')
        after = self.completed(force=True)
        self.assertNotEqual(before['revision'], after['revision'])
        self.assertEqual(self.atlas.cache()['measured_at'], after['measured_at'])

    def test_failed_inventory_retains_original_time_and_pauses_rendering(self):
        before = self.completed()
        with patch('control_room.atlas.contained', side_effect=UserError('linked fixture')):
            failed = self.completed(force=True)
        self.assertFalse(failed['current'])
        self.assertEqual(failed['measured_at'], before['measured_at'])
        self.assertEqual(failed['scan_error'], 'linked fixture')
        self.atlas.monitor({})
        self.assertTrue(read_json(self.layout.state / 'atlas-control.json')['paused'])

    def test_close_prevents_worker_publication_and_new_scans(self):
        self.completed()
        before = dict(self.atlas._cache)
        self.atlas.close()
        with patch.object(self.atlas, '_measure_cache') as scan:
            self.assertFalse(self.atlas.cache(force=True)['current'])
            scan.assert_not_called()
        self.assertEqual(before, self.atlas._cache)

    def test_storage_refresh_never_runs_a_recursive_scan_on_the_request_thread(self):
        app = Application.__new__(Application)
        for name in ('metrics', 'mods', 'players', 'backups', 'atlas', 'cinematics', 'settings', 'jobs', 'graphics', 'installer'):
            setattr(app, name, Mock())
        app.storage = Mock()
        app.get('/api/storage', {'refresh': ['1']})
        app.storage.snapshot.assert_called_once_with(live=True, refresh=True)
        app.storage.breakdown.assert_not_called()

    def test_old_claim_cache_expires_independently_of_a_fresh_bridge(self):
        metrics = Metrics(self.layout, self.storage, Mock())
        now = time.time()
        old = dict(at=utcnow(), available=True, items=[{'owner': 'synthetic'}])
        with patch('control_room.metrics.time.time', return_value=now + 46):
            metrics._latest = dict(at=now+46, bridge_at=now+46, player_roster_at=now+46,
                                   players={}, bridge_capabilities=[], atlas_claims=old)
            value = metrics.latest()
        self.assertTrue(value['freshness']['bridge']['current'])
        self.assertFalse(value['atlas_claims']['available'])
        self.assertEqual(value['atlas_claims']['items'], [])
        self.assertEqual(value['last_known']['atlas_claims'], old)
        self.assertTrue(metrics._latest['atlas_claims']['available'])

    def test_successful_teleport_history_contains_only_returned_native_results(self):
        who = dict(name='TestPlayer', uuid='11111111-1111-4111-8111-111111111111', online=True, capabilities=['safe_teleport'])
        self.players.details.return_value = who
        point = dict(dimension='minecraft:overworld', x=12, y=70, z=34, landing='near-y')
        previous = dict(dimension='minecraft:overworld', x=0, y=65, z=0)
        console = Mock()
        def result(command):
            ident = command.split()[-1]
            write_json(self.layout.state / f'atlas-requests/{ident}.result.json',
                       dict(id=ident, status='complete', previous=previous, destination=point, at=utcnow()))
        console._write.side_effect = result
        self.atlas.server = console
        self.atlas.teleport('TestPlayer', point, confirmed=True)
        history = read_json(self.layout.state / 'atlas-return-history.json')
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]['previous'], previous)
        self.assertEqual(history[0]['destination'], point)
        # No pending/refused request creates a successful return record.
        console._write.side_effect = lambda command: write_json(
            self.layout.state / f'atlas-requests/{command.split()[-1]}.result.json',
            dict(status='refused', error='Synthetic unsafe destination'))
        with self.assertRaisesRegex(UserError, 'unsafe destination'):
            self.atlas.teleport('TestPlayer', point, confirmed=True)
        self.assertEqual(read_json(self.layout.state / 'atlas-return-history.json'), history)


class DurableJobsTests(Fixture):
    def jobs(self):
        return Jobs(self.layout.state / 'jobs.json', self.storage)

    def test_success_and_actionable_failure_survive_backend_restart_without_replay(self):
        jobs = self.jobs()
        jobs.submit('Complete', lambda notify: {'saved': True})
        def failure(notify):
            notify('Reached a safe checkpoint')
            raise UserError('Expected fixture refusal')
        jobs.submit('Refuse', failure)
        jobs.close()
        reopened = self.jobs()
        self.addCleanup(reopened.close)
        rows = reopened.list()
        self.assertEqual({row['status'] for row in rows}, {'complete', 'failed'})
        self.assertEqual(next(r for r in rows if r['status'] == 'failed')['error'], 'Expected fixture refusal')
        rows[0]['messages'].append('browser mutation')
        self.assertNotIn('browser mutation', reopened.list()[0]['messages'])

    def test_abrupt_restart_marks_running_tasks_interrupted_and_never_successful(self):
        path = self.layout.state / 'jobs.json'
        write_json(path, [dict(id='a'*32, title='Restore', status='running', created=utcnow(), messages=[], result=None, error=None)])
        reopened = self.jobs()
        self.addCleanup(reopened.close)
        row = reopened.list()[0]
        self.assertEqual(row['status'], 'interrupted')
        self.assertIn('not replayed', row['error'])
        self.assertIsNone(row['result'])
        self.assertEqual(read_json(path)[0]['status'], 'interrupted')

    def test_unexpected_errors_and_result_secrets_are_not_exposed(self):
        jobs = self.jobs()
        def unexpected(notify):
            raise RuntimeError('password=private-value')
        def success(notify):
            notify('authorization: Bearer private-value')
            return {'access_token': 'private-value', 'note': 'secret=private-value'}
        jobs.submit('Unexpected', unexpected)
        jobs.submit('Success', success)
        jobs.close()
        encoded = json.dumps(jobs.list())
        self.assertNotIn('private-value', encoded)
        self.assertIn('RuntimeError', encoded)
        self.assertIn('[redacted]', encoded)

    def test_closed_queue_refuses_new_work_and_journal_remains_bounded(self):
        jobs = self.jobs()
        for index in range(55):
            jobs.submit(str(index), lambda notify: 'x' * 100000)
            # Wait for this lightweight task, rather than filling its four-task queue.
            deadline = time.monotonic() + 2
            while any(row['status'] in ('queued', 'running') for row in jobs.list()) and time.monotonic() < deadline:
                time.sleep(.005)
        jobs.close()
        self.assertLessEqual(len(jobs.list()), 50)
        self.assertLessEqual((self.layout.state / 'jobs.json').stat().st_size, HISTORY_BYTES)
        with self.assertRaisesRegex(UserError, 'closing'):
            jobs.submit('Too late', lambda notify: None)

    def test_corrupt_history_is_preserved_without_silent_reset(self):
        path = self.layout.state / 'jobs.json'
        original = b'{corrupt history receipt'
        path.write_bytes(original)
        with self.assertRaisesRegex(UserError, 'preserve|Preserve'):
            self.jobs()
        self.assertEqual(path.read_bytes(), original)

    def test_failed_journal_checkpoint_prevents_task_execution(self):
        storage = Mock()
        storage.checkpoint.side_effect = [UserError('Reserve reached'), UserError('Reserve reached')]
        jobs = Jobs(self.layout.state / 'jobs.json', storage)
        action = Mock()
        jobs.submit('Must not start', action)
        jobs.close()
        action.assert_not_called()
        self.assertEqual(jobs.list()[0]['status'], 'failed')
        self.assertIn('history_warning', jobs.list()[0])

    def test_slow_journal_guard_never_holds_the_dashboard_state_lock(self):
        entered, release = threading.Event(), threading.Event()
        self.addCleanup(release.set)
        storage = Mock()
        def checkpoint(*args):
            entered.set()
            release.wait(3)
        storage.checkpoint.side_effect = checkpoint
        jobs = Jobs(self.layout.state / 'jobs.json', storage)
        action = Mock()
        jobs.submit('Waiting at reserve guard', action)
        self.assertTrue(entered.wait(1))
        readers = [threading.Thread(target=jobs.list) for _ in range(6)]
        for reader in readers:
            reader.start()
        for reader in readers:
            reader.join(.5)
            self.assertFalse(reader.is_alive(), 'Task list waited on journal reserve/IO')
        action.assert_not_called()
        release.set()
        jobs.close()
