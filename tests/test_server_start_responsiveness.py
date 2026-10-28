"""Synthetic start-preflight concurrency only; no Java or Minecraft is launched."""
import os
import tempfile
import threading
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import Mock, patch

from control_room.common import Layout, UserError, write_json
from control_room.server import Server


class StartResponsivenessTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='awft-start-lock-')
        self.addCleanup(self.temporary.cleanup)
        self.layout = Layout(Path(self.temporary.name))
        self.layout.create()
        # The on-disk fixture is deliberately unaccepted. Tests that exercise
        # later gates mock the EULA parser; no legal acceptance is written.
        (self.layout.server / 'eula.txt').write_text('eula=false\n', encoding='utf-8')
        write_json(self.layout.server / 'installed.json', {'pack_sha256': 'synthetic-pin', 'neoforge': 'synthetic-loader'})
        write_json(self.layout.home / 'packwiz/active.json', {'pack_sha256': 'synthetic-pin'})
        args = self.layout.server / 'libraries/net/neoforged/neoforge/synthetic-loader' / ('win_args.txt' if os.name == 'nt' else 'unix_args.txt')
        args.parent.mkdir(parents=True)
        args.write_text('# Synthetic fixture. Never executed.\n', encoding='utf-8')
        self.storage = Mock()
        self.server = Server(self.layout, self.storage)
        self.stack = self.enterContext(ExitStack())
        self.parse = self.stack.enter_context(patch('control_room.server.properties', return_value={'eula': 'true'}))
        self.verify = self.stack.enter_context(patch('control_room.pack.verify_installed', return_value=[]))
        self.stack.enter_context(patch('control_room.atlas.prepare_renderer'))
        self.stack.enter_context(patch('control_room.storage.tree_size', return_value=0))
        self.stack.enter_context(patch('control_room.server.shutil.which', return_value='synthetic-java'))
        self.version = self.stack.enter_context(patch('control_room.server.subprocess.run', return_value=Mock(stderr='java version "21.0.1"', stdout='')))
        self.child = Mock(pid=424242)
        self.child.poll.return_value = None
        self.popen = self.stack.enter_context(patch('control_room.server.subprocess.Popen', return_value=self.child))
        self.stack.enter_context(patch('control_room.server.psutil.Process', return_value=Mock(pid=424242, create_time=Mock(return_value=1000))))
        self.stack.enter_context(patch('control_room.server.logging.getLogger', return_value=Mock(handlers=[Mock()])))
        self.stack.enter_context(patch.object(self.server, '_reader'))

    def run_start(self, errors):
        try:
            self.server.start()
        except Exception as exc:
            errors.append(exc)

    def blocked_preflight(self, stage):
        entered, release, observed = threading.Event(), threading.Event(), threading.Event()
        errors, snapshots = [], []
        def blocked(*args, **kwargs):
            entered.set()
            release.wait(5)
            if stage == 'integrity':
                return []
            if stage == 'java':
                return Mock(stderr='java version "21.0.1"', stdout='')
        if stage == 'integrity':
            self.verify.side_effect = blocked
        elif stage == 'java':
            self.version.side_effect = blocked
        else:
            self.storage.reserve.side_effect = blocked
        writer = threading.Thread(target=self.run_start, args=(errors,))
        writer.start()
        self.assertTrue(entered.wait(2))
        def read_status():
            snapshots.append(self.server.snapshot())
            observed.set()
        reader = threading.Thread(target=read_status)
        reader.start()
        try:
            responsive = observed.wait(1)
            # Mutating operations still cannot enter while startup preflight
            # owns its full lease, even though status reads are available.
            acquired = self.layout.mutation.acquire(blocking=False)
            if acquired:
                self.layout.mutation.release()
        finally:
            release.set()
            writer.join(2)
            reader.join(2)
        self.assertTrue(responsive, stage + ' preflight blocked status reads')
        self.assertFalse(acquired, stage + ' preflight released the mutation lease')
        self.assertFalse(writer.is_alive())
        self.assertFalse(reader.is_alive())
        self.assertEqual(errors, [])
        self.assertEqual(snapshots[0]['state'], 'offline')
        self.popen.assert_called_once()

    def test_integrity_scan_does_not_block_status(self):
        self.blocked_preflight('integrity')

    def test_storage_reservation_does_not_block_status(self):
        self.blocked_preflight('storage')

    def test_java_version_probe_does_not_block_status(self):
        self.blocked_preflight('java')

    def test_concurrent_start_requests_remain_serialized_and_launch_one_child(self):
        entered, release = threading.Event(), threading.Event()
        errors = []
        def blocked(*args):
            entered.set()
            release.wait(5)
            return []
        self.verify.side_effect = blocked
        first = threading.Thread(target=self.run_start, args=(errors,))
        second = threading.Thread(target=self.run_start, args=(errors,))
        first.start()
        self.assertTrue(entered.wait(2))
        second.start()
        release.set()
        first.join(2)
        second.join(2)
        self.assertFalse(first.is_alive())
        self.assertFalse(second.is_alive())
        self.popen.assert_called_once()
        self.assertEqual(self.verify.call_count, 1)
        self.assertEqual(len(errors), 1)
        self.assertIsInstance(errors[0], UserError)
        self.assertIn('already running', str(errors[0]))

    def test_running_process_discovered_after_preflight_prevents_replacement(self):
        entered, release = threading.Event(), threading.Event()
        errors = []
        def blocked(*args):
            entered.set()
            release.wait(5)
            return []
        self.verify.side_effect = blocked
        writer = threading.Thread(target=self.run_start, args=(errors,))
        writer.start()
        self.assertTrue(entered.wait(2))
        with self.server._lock:
            self.server.process = self.child
        release.set()
        writer.join(2)
        self.assertFalse(writer.is_alive())
        self.popen.assert_not_called()
        self.assertEqual(len(errors), 1)
        self.assertIn('already running', str(errors[0]))
        self.assertIs(self.server.process, self.child)

    def test_unaccepted_eula_still_refuses_before_integrity_or_launch(self):
        self.parse.side_effect = lambda text: {'eula': 'false'}
        with self.assertRaisesRegex(UserError, 'EULA'):
            self.server.start()
        self.verify.assert_not_called()
        self.popen.assert_not_called()
        self.storage.reserve.assert_not_called()

    def test_failed_integrity_still_prevents_allocation_and_launch(self):
        self.verify.return_value = ['Synthetic artifact hash mismatch']
        with self.assertRaisesRegex(UserError, 'integrity check failed'):
            self.server.start()
        self.storage.reserve.assert_not_called()
        self.popen.assert_not_called()

    def test_reserve_refusal_still_prevents_java_probe_and_launch(self):
        self.storage.reserve.side_effect = UserError('Synthetic reserve refusal')
        with self.assertRaisesRegex(UserError, 'reserve refusal'):
            self.server.start()
        self.version.assert_not_called()
        self.popen.assert_not_called()

    def test_wrong_java_still_refuses_launch(self):
        self.version.return_value = Mock(stderr='java version "20.0.1"', stdout='')
        with self.assertRaisesRegex(UserError, 'requires Java 21'):
            self.server.start()
        self.popen.assert_not_called()

    def test_slow_notification_does_not_reacquire_status_lock(self):
        entered, release, observed = threading.Event(), threading.Event(), threading.Event()
        errors = []
        def notify(message):
            entered.set()
            release.wait(5)
        def start():
            try:
                self.server.start(notify=notify)
            except Exception as exc:
                errors.append(exc)
        writer = threading.Thread(target=start)
        writer.start()
        self.assertTrue(entered.wait(2))
        reader = threading.Thread(target=lambda: (self.server.snapshot(), observed.set()))
        reader.start()
        try:
            responsive = observed.wait(1)
        finally:
            release.set()
            writer.join(2)
            reader.join(2)
        self.assertTrue(responsive)
        self.assertEqual(errors, [])
