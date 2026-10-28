from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from tools.performance import (MASTER, capture, describe, directory_size, native_snapshot,
                               summarize, validate_window)
from tools.performance_handoff import patched_bridge


NOW = 1_800_000_000


def iso(value):
    return datetime.fromtimestamp(value, timezone.utc).isoformat()


class PerformanceCaptureTests(unittest.TestCase):
    def test_percentiles_use_observations_and_do_not_erase_a_spike(self):
        stats = describe([1] * 99 + [600])
        self.assertEqual(stats['max'], 600)
        self.assertEqual(stats['p95'], 1)
        self.assertLess(stats['mean'], 7)
        self.assertEqual(describe([None, float('nan')]), {'samples': 0})

    def test_20tps_does_not_create_missing_tick_spike_evidence(self):
        result = summarize([{'server': {'tps': 20, 'mspt': 5},
                             'host': {'memory_available_bytes': 100}}])
        self.assertIsNone(result['tick_spike_observations']['max_work_ms'])
        self.assertIsNone(result['tick_spike_observations']['over_50ms'])

    def test_menu_frames_stay_separate_and_no_pooled_percentile_is_invented(self):
        rows = []
        for screen, maximum in [('game', 20), ('VideoSettingsScreen', 44000)]:
            rows.append({'client': {'fps': 60, 'focused': True, 'in_world': True, 'screen': screen,
                                    'frame_interval_ms': {'max': maximum, 'p95': 16.7}},
                         'host': {'memory_available_bytes': 100}})
        result = summarize(rows)
        self.assertEqual(result['focused_gameplay_client_snapshots'], 1)
        self.assertEqual(result['sampled_client_frame_windows']['worst_retained_frame_ms'], 20)
        self.assertEqual(result['all_client_states_worst_retained_frame_ms'], 44000)
        self.assertIsInstance(result['sampled_client_frame_windows']['global_frame_percentiles'], str)

    def test_window_expires_and_cannot_substitute_another_save(self):
        window = dict(format='awft-passive-performance-window:1', coordinator_chat=MASTER,
                      operation='passive-telemetry', workload='idle', configuration='shaders-off',
                      begins_at=iso(NOW - 10), expires_at=iso(NOW + 120), candidate='candidate-test',
                      pack_sha256='a' * 64,
                      server_home=r'D:\A World for Two\staging\world-tests\20261027T053650Z-artistic',
                      client_root=r'D:\A World for Two\instances\AWFT_Check_20261026_214756')
        self.assertEqual(validate_window(window, NOW), NOW + 120)
        with self.assertRaises(ValueError):
            validate_window(window, NOW + 120)
        window['server_home'] = r'D:\A World for Two'
        with self.assertRaises(ValueError):
            validate_window(window, NOW)

    def test_stale_or_borrowed_native_process_is_refused(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / 'native.json'
            data = dict(format='awft-metrics:1', pid=42, process_started=iso(NOW-60),
                        at=iso(NOW), heap_used=100, heap_max=200, tps=20, mspt=1)
            path.write_text(json.dumps(data))
            process = Mock()
            process.create_time.return_value = NOW - 60
            process.name.return_value = 'java.exe'
            process.cwd.return_value = root
            process.memory_info.return_value = Mock(rss=123)
            process.cpu_times.return_value = (1, 2)
            process.io_counters.return_value = Mock(_asdict=lambda: {})
            expected = dict(pid=42, created=NOW-60, cwd=root)
            with patch('tools.performance.psutil.Process', return_value=process):
                self.assertEqual(native_snapshot(path, expected, 'server', NOW)['rss_bytes'], 123)
                with self.assertRaises(ValueError):
                    native_snapshot(path, expected, 'server', NOW+16)
                process.create_time.return_value = NOW - 30
                with self.assertRaises(ValueError):
                    native_snapshot(path, expected, 'server', NOW)

    def test_bounded_size_scan_marks_partial_instead_of_a_fictional_cache_size(self):
        with tempfile.TemporaryDirectory() as root:
            for i in range(3):
                (Path(root) / str(i)).write_bytes(b'ab')
            self.assertEqual(directory_size(root)['logical_bytes_including_wal'], 6)
            result = directory_size(root, max_entries=1)
            self.assertFalse(result['complete'])
            self.assertNotIn('logical_bytes_including_wal', result)

    def test_bridge_handoff_refuses_missing_or_already_applied_anchors(self):
        with self.assertRaises(ValueError):
            patched_bridge('')
        root = Path(__file__).resolve().parents[1]
        original = (root / 'compat/control-bridge/src/worldfortwo/bridge/ControlBridge.java').read_text()
        patched = patched_bridge(original)
        self.assertIn('performanceTicks.finished(now - beforeTick)', patched)
        with self.assertRaises(ValueError):
            patched_bridge(patched)

    def test_server_only_capture_deduplicates_without_launching_a_client(self):
        # A synthetic recorder fixture, never a real Minecraft measurement.
        with tempfile.TemporaryDirectory() as root:
            home, client = Path(root) / 'home', Path(root) / 'client'
            (home / 'staging').mkdir(parents=True)
            window = dict(server_home=str(home), client_root=str(client), candidate='test-only',
                          pack_sha256='a' * 64, workload='synthetic idle fixture', configuration='fixture',
                          processes={'server': dict(pid=42, created=NOW-60, cwd=str(home / 'server'))})
            clock = [100.0]
            def read(path, *args):
                return window if Path(path).name == 'window.json' else dict(version='test-only', pack_sha256='a' * 64)
            with patch('tools.performance.json_file', side_effect=read), \
                    patch('tools.performance.validate_window', return_value=NOW+120), \
                    patch('tools.performance.time.time', return_value=NOW), \
                    patch('tools.performance.time.monotonic', side_effect=lambda: clock[0]), \
                    patch('tools.performance.time.sleep', side_effect=lambda delay: clock.__setitem__(0, clock[0]+delay)), \
                    patch('tools.performance.guard', return_value={'allowed': True}), \
                    patch('tools.performance.PagingCounters') as paging, \
                    patch('tools.performance.memory_pressure', return_value={'available': False}), \
                    patch('tools.performance.gpu_sample', return_value={'available': False}), \
                    patch('tools.performance.config_hashes', return_value={'fixture': 'b'*64}), \
                    patch('tools.performance.psutil.virtual_memory', return_value=Mock(total=1000, available=500)), \
                    patch('tools.performance.psutil.disk_usage', return_value=Mock(free=10**12)), \
                    patch('tools.performance.native_snapshot', return_value={'at': iso(NOW), 'tps': 20, 'mspt': 1}) as native:
                paging.return_value.sample.return_value = {'available': False}
                result = capture('window.json', seconds=2)
            self.assertEqual(native.call_count, 2)
            self.assertEqual(result['summary']['native_server_snapshots'], 1)
            self.assertEqual(result['summary']['native_client_snapshots'], 0)
            receipt = json.loads((Path(result['directory']) / 'result.json').read_bytes())
            self.assertFalse(receipt['client_recording_requested'])


if __name__ == '__main__':
    unittest.main()
