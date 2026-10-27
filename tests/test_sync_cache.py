"""Event-driven overview checks; no real server, game, restart or network access."""
from __future__ import annotations

import os
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from control_room.common import Layout, digest, write_json
from control_room.mod_manager import ModManager, SYNC_MAX_FILES, SYNC_TTL_SECONDS, _file_signature
from control_room.web import Application


class OverviewSyncTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='awft-sync-test-')
        self.addCleanup(temporary.cleanup)
        self.layout = Layout(Path(temporary.name))
        self.layout.create()
        self.release = self.layout.releases / 'test-1'
        self.release.mkdir()
        self.pack = self.release / 'pack.toml'
        self.pack.write_bytes(b'name = "test"\n')
        write_json(self.release / 'lock.json', {
            'version': 'test-1', 'minecraft': '1.21.1', 'neoforge': '21.1.262',
            'release_status': 'fixture', 'mods': []})
        write_json(self.layout.home / 'packwiz/active.json', {'version': 'test-1'})
        (self.layout.server / 'mods').mkdir()
        self.jar = self.layout.server / 'mods/sample.jar'
        self.jar.write_bytes(b'original fixture')
        self.receipt = {'pack_sha256': digest(self.pack), 'files': {'sample.jar': digest(self.jar)}}
        write_json(self.layout.server / 'installed.json', self.receipt)
        self.manager = ModManager(self.layout, Mock(), Mock(), Mock())
        self.cache = self.manager._overview_integrity
        self.addCleanup(self.manager.close)
        self.now = 1000.0
        self.cache.clock = lambda: self.now
        self.real_verify = self.cache._verify

    def wait_idle(self):
        with self.cache._condition:
            self.assertTrue(self.cache._condition.wait_for(
                lambda: self.cache._attempt_signature is not None
                and not self.cache._busy and self.cache._pending is None, timeout=5),
                'The one owned background worker did not reach its checkpoint')

    def finish_initial(self):
        initial = self.manager.overview_sync()
        self.assertFalse(initial['server_integrity']['current'])
        self.wait_idle()
        verified = self.manager.overview_sync()
        self.assertEqual(verified['server_integrity']['status'], 'verified')
        return verified

    def block_scan(self, after_hash=False):
        entered, release = threading.Event(), threading.Event()
        self.addCleanup(release.set)
        calls = []
        def verify(snapshot):
            calls.append(threading.get_ident())
            result = self.real_verify(snapshot) if after_hash else None
            entered.set()
            if not release.wait(5):
                raise RuntimeError('Test controller did not release the bounded scan')
            return result if after_hash else self.real_verify(snapshot)
        self.cache._verify = verify
        return entered, release, calls

    def application(self):
        app = Application.__new__(Application)
        app.layout, app.mods, app.token = self.layout, self.manager, 'fixture'
        for name in ('storage', 'server', 'settings', 'metrics', 'backups', 'installer',
                     'players', 'atlas', 'cinematics', 'graphics', 'playit', 'jobs'):
            setattr(app, name, Mock())
        app.backups.list.return_value = []
        app.server.snapshot.return_value = {'state': 'offline'}
        app.server.running.return_value = False
        app.installer.preflight.return_value = {'java_version': '21'}
        app.active_test = lambda: None
        return app

    def test_actual_overview_returns_while_hashing_is_blocked(self):
        entered, release, calls = self.block_scan()
        self.manager.overview_sync()
        self.assertTrue(entered.wait(5))
        returned, answers = threading.Event(), []
        def request():
            try:
                answers.append(self.application().overview())
            finally:
                returned.set()
        with patch('control_room.mod_manager.verify_installed', side_effect=AssertionError('Polling used strict hashing')):
            worker = threading.Thread(target=request)
            worker.start()
            self.assertTrue(returned.wait(5), 'Overview waited on the blocked full verifier')
            worker.join(5)
        self.assertFalse(release.is_set())
        self.assertEqual(answers[0]['sync']['server_integrity']['status'], 'checking')
        self.assertFalse(answers[0]['sync']['server_integrity']['current'])
        self.assertEqual(len(calls), 1)
        release.set(); self.wait_idle()

    def test_concurrent_polls_share_exactly_one_worker_and_no_pending_queue(self):
        entered, release, calls = self.block_scan()
        self.manager.overview_sync(); self.assertTrue(entered.wait(5))
        owner = self.cache._worker
        workers = [threading.Thread(target=self.manager.overview_sync) for _ in range(20)]
        for worker in workers: worker.start()
        for worker in workers:
            worker.join(5); self.assertFalse(worker.is_alive())
        self.assertIs(self.cache._worker, owner)
        self.assertIsNone(self.cache._pending)
        self.assertEqual(len(calls), 1)
        release.set(); self.wait_idle()
        for _ in range(10):
            self.assertTrue(self.manager.overview_sync()['server_integrity']['current'])
        self.assertEqual(len(calls), 1)
        self.assertIs(self.cache._worker, owner)

    def test_fresh_observation_has_exact_provenance_and_original_time(self):
        result = self.finish_initial()
        info = result['server_integrity']
        self.assertEqual(result['server'], 'matches')
        self.assertEqual(info['age_seconds'], 0)
        self.assertEqual(info['last_verified_provenance']['pack_sha256'], digest(self.pack))
        self.assertEqual(info['last_verified_provenance']['installed_receipt_sha256'], digest(self.layout.server / 'installed.json'))
        self.assertEqual(info['last_verified_provenance']['expected_files'], 1)
        self.assertEqual(info['current_inventory_signature'], info['last_verified_provenance']['inventory_signature'])
        self.now += 3
        repeated = self.manager.overview_sync()['server_integrity']
        self.assertEqual(repeated['last_verified_at'], info['last_verified_at'])
        self.assertEqual(repeated['age_seconds'], 3)

    def test_expiry_is_unknown_while_rechecking_and_never_extends_a_match(self):
        initial = self.finish_initial()['server_integrity']
        entered, release, calls = self.block_scan()
        self.now += SYNC_TTL_SECONDS
        result = self.manager.overview_sync()
        self.assertFalse(result['server_integrity']['current'])
        self.assertNotEqual(result['server'], 'matches')
        self.assertEqual(result['server_integrity']['last_verified_at'], initial['last_verified_at'])
        self.assertEqual(result['server_integrity']['age_seconds'], SYNC_TTL_SECONDS)
        self.assertTrue(entered.wait(5)); self.assertEqual(len(calls), 1)
        release.set(); self.wait_idle()
        self.assertTrue(self.manager.overview_sync()['server_integrity']['current'])

    def test_same_size_tampering_invalidates_by_stat_then_real_hash_fails(self):
        self.finish_initial()
        before = self.jar.stat()
        self.jar.write_bytes(b'tampered fixture')
        self.assertEqual(self.jar.stat().st_size, before.st_size)
        os.utime(self.jar, ns=(before.st_atime_ns, before.st_mtime_ns + 2_000_000_000))
        entered, release, _ = self.block_scan()
        waiting = self.manager.overview_sync()
        self.assertFalse(waiting['server_integrity']['current'])
        self.assertNotEqual(waiting['server'], 'matches')
        self.assertTrue(entered.wait(5)); release.set(); self.wait_idle()
        result = self.manager.overview_sync()
        self.assertEqual(result['server_integrity']['status'], 'differs')
        self.assertIn('Missing or modified server file: sample.jar', result['server_integrity']['errors'])

    def test_receipt_and_manifest_content_invalidate_without_jar_change(self):
        self.finish_initial()
        self.receipt['pack_sha256'] = '0' * 64
        write_json(self.layout.server / 'installed.json', self.receipt)
        self.assertFalse(self.manager.overview_sync()['server_integrity']['current'])
        self.wait_idle()
        self.assertEqual(self.manager.overview_sync()['server_integrity']['status'], 'differs')
        self.pack.write_bytes(b'name = "other"\n')
        self.assertFalse(self.manager.overview_sync()['server_integrity']['current'])
        self.wait_idle()
        self.assertEqual(self.manager.overview_sync()['server_integrity']['status'], 'differs')

    def test_metadata_indistinguishable_edit_cannot_extend_match_beyond_ttl(self):
        # Model a filesystem whose creation/change field cannot distinguish this
        # same-size edit with restored mtime. Real byte hashing must still catch it.
        def limited_metadata(info):
            return _file_signature(info)[:5] + (0,)
        with patch('control_room.mod_manager._file_signature', side_effect=limited_metadata):
            initial = self.finish_initial()
            before = self.jar.stat()
            self.jar.write_bytes(b'tampered fixture')
            os.utime(self.jar, ns=(before.st_atime_ns, before.st_mtime_ns))
            early = self.manager.overview_sync()
            self.assertTrue(early['server_integrity']['current'])
            self.assertEqual(early['server_integrity']['last_verified_at'], initial['server_integrity']['last_verified_at'])
            self.now += SYNC_TTL_SECONDS
            expired = self.manager.overview_sync()
            self.assertFalse(expired['server_integrity']['current'])
            self.assertNotEqual(expired['server'], 'matches')
            self.wait_idle()
            self.assertEqual(self.manager.overview_sync()['server_integrity']['status'], 'differs')

    def test_actual_streaming_verifier_honors_stop_and_deadline(self):
        snapshot = self.manager._overview_snapshot()
        self.cache._stop.set()
        with self.assertRaises(InterruptedError):
            self.real_verify(snapshot)
        self.cache._stop.clear()
        with patch('control_room.mod_manager.time.monotonic', side_effect=[0, 121]):
            with self.assertRaises(TimeoutError):
                self.real_verify(snapshot)

    def test_added_and_missing_files_do_not_inherit_cached_integrity(self):
        self.finish_initial()
        (self.layout.server / 'mods/unexpected.jar').write_bytes(b'foreign')
        self.assertFalse(self.manager.overview_sync()['server_integrity']['current'])
        self.wait_idle()
        self.assertIn('Server contains an unexpected mod inventory', self.manager.overview_sync()['server_integrity']['errors'])
        self.jar.unlink()
        self.assertFalse(self.manager.overview_sync()['server_integrity']['current'])
        self.wait_idle()
        self.assertIn('Missing or modified server file: sample.jar', self.manager.overview_sync()['server_integrity']['errors'])

    def test_changed_inventory_during_hash_discards_success_instead_of_publishing(self):
        entered, release, _ = self.block_scan(after_hash=True)
        self.manager.overview_sync(); self.assertTrue(entered.wait(5))
        self.receipt['at'] = 'changed after all bytes hashed'
        write_json(self.layout.server / 'installed.json', self.receipt)
        release.set(); self.wait_idle()
        with self.cache._condition:
            self.assertIsNone(self.cache._result)
            self.assertIn('result discarded', self.cache._error)
        checking = self.manager.overview_sync()
        self.assertIsNone(checking['server_integrity']['last_verified_at'])
        self.assertFalse(checking['server_integrity']['current'])
        self.wait_idle()

    def test_scan_error_has_backoff_and_never_becomes_a_match(self):
        failing = Mock(side_effect=OSError('fixture access refused'))
        self.cache._verify = failing
        self.manager.overview_sync(); self.wait_idle()
        for _ in range(5):
            result = self.manager.overview_sync()
            self.assertEqual(result['server_integrity']['status'], 'error')
            self.assertFalse(result['server_integrity']['current'])
            self.assertNotEqual(result['server'], 'matches')
        self.assertEqual(failing.call_count, 1)
        self.now += SYNC_TTL_SECONDS
        self.cache._verify = self.real_verify
        self.manager.overview_sync(); self.wait_idle()
        self.assertEqual(self.manager.overview_sync()['server'], 'matches')

    def test_unbounded_receipt_is_unknown_and_never_starts_a_worker(self):
        self.receipt['files'] = {'item' + str(n) + '.jar': '0' * 64 for n in range(SYNC_MAX_FILES + 1)}
        write_json(self.layout.server / 'installed.json', self.receipt)
        result = self.manager.overview_sync()
        self.assertEqual(result['server_integrity']['status'], 'error')
        self.assertFalse(result['server_integrity']['current'])
        self.assertIsNone(self.cache._worker)

    def test_slow_failure_gets_a_full_backoff_from_completion(self):
        self.finish_initial()
        entered, release = threading.Event(), threading.Event()
        self.addCleanup(release.set)
        calls = []
        def fail_slowly(snapshot):
            calls.append(threading.get_ident())
            entered.set()
            if not release.wait(5):
                raise RuntimeError('Test did not release its slow scan')
            raise TimeoutError('Controlled failure after a simulated 120-second scan')
        self.cache._verify = fail_slowly
        self.now += SYNC_TTL_SECONDS
        self.manager.overview_sync(); self.assertTrue(entered.wait(5))
        self.now += 120
        release.set(); self.wait_idle()
        failed = self.manager.overview_sync()['server_integrity']
        self.assertEqual(failed['status'], 'error')
        self.assertFalse(failed['current'])
        self.assertEqual(failed['retry_after_seconds'], SYNC_TTL_SECONDS)
        self.assertIsNotNone(failed['last_attempt_finished_at'])
        self.cache._verify = self.real_verify
        for _ in range(19):
            self.now += 3
            self.assertEqual(self.manager.overview_sync()['server_integrity']['status'], 'error')
        self.assertEqual(len(calls), 1)
        self.assertEqual(self.manager.overview_sync()['server_integrity']['retry_after_seconds'], 3)
        self.now += 3
        checking = self.manager.overview_sync()['server_integrity']
        self.assertEqual(checking['status'], 'checking')
        self.assertFalse(checking['current'])
        self.wait_idle()
        self.assertEqual(self.manager.overview_sync()['server'], 'matches')

    def test_close_cancels_one_owned_worker_and_refuses_future_scans(self):
        entered = threading.Event()
        def wait_for_close(snapshot):
            entered.set()
            if not self.cache._stop.wait(5):
                raise RuntimeError('Close did not signal the worker')
            return []
        self.cache._verify = wait_for_close
        self.manager.overview_sync(); self.assertTrue(entered.wait(5))
        owner = self.cache._worker
        self.application().close()
        self.assertFalse(owner.is_alive())
        self.assertIsNone(self.cache._result)
        result = self.manager.overview_sync()
        self.assertEqual(result['server_integrity']['status'], 'closed')
        self.assertFalse(result['server_integrity']['current'])
        self.assertIs(self.cache._worker, owner)

    def test_explicit_sync_and_health_ignore_a_fresh_display_match(self):
        self.finish_initial()
        app = self.application()
        with patch('control_room.mod_manager.verify_installed', return_value=['strict failure']) as strict:
            self.assertEqual(app.get('/api/sync', {})['server'], 'not installed or differs')
            strict.assert_called_once_with(self.layout)
        with patch('control_room.web.verify_installed', return_value=['health failure']) as strict, patch('control_room.web.validate_pack', return_value=[]):
            self.assertEqual(app.health()['server_errors'], ['health failure'])
            strict.assert_called_once_with(self.layout)


if __name__ == '__main__':
    unittest.main()
