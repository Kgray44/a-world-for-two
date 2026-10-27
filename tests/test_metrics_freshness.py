"""A cached sample must expire at response time without becoming a disconnect."""
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from control_room.common import GiB, Layout, UserError, read_json, write_json
from control_room.metrics import MAX_AGE_SECONDS, Metrics, measurement_freshness
from control_room.players import Players
from control_room.server import Server
from control_room.web import Application


NOW = 1_800_000_000
WHO = {'uuid': '11111111-1111-4111-8111-111111111111', 'name': 'HarborPlayer'}


def iso(value):
    return datetime.fromtimestamp(value, timezone.utc).isoformat()


class MetricsFreshnessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='awft-metrics-freshness-')
        self.addCleanup(self.temp.cleanup)
        self.layout = Layout(Path(self.temp.name))
        self.layout.create()
        self.storage = Mock()
        self.server = Mock(identity={'pid': 42, 'created': NOW-60})
        self.metrics = Metrics(self.layout, self.storage, self.server)

    def sample(self):
        return {'at': NOW, 'tick_at': iso(NOW), 'bridge_at': iso(NOW), 'player_roster_at': iso(NOW),
                'tick_source': 'Owned NeoForge server bridge: tick events and JVM management beans',
                'tps': 20, 'mspt': 9.5, 'host_cpu': 25, 'host_memory_percent': 60,
                'host_memory_available': 5*GiB, 'server_cpu': 10, 'server_rss': 6*GiB,
                'heap_used': 4*GiB, 'heap_max': 8*GiB, 'loaded_chunks': 500, 'entities': 200,
                'dimensions': {'minecraft:overworld': {'loaded_chunks': 500, 'entities': 200}},
                'gc_collections': 2, 'gc_collection_ms': 8, 'gc_pause_ms': 3,
                'players': {WHO['uuid']: {**WHO, 'x': 1, 'y': 65, 'z': 3}},
                'bridge_capabilities': ['player_locations', 'safe_teleport'],
                'atlas_objects': [{'name': 'Moving object'}], 'cinematics': {'available': True},
                'chunk_diagnostics': {'at': iso(NOW), 'dimensions': {'minecraft:overworld': {}}},
                'unavailable': {}, 'alerts': [],
                'clients': [{'instance': 'Owned', 'player': 'KG', 'pid': 70, 'at': iso(NOW),
                             'rss': 3*GiB, 'cpu_percent_host': 10, 'fps': 60,
                             'heap_used': 2*GiB, 'heap_max': 6*GiB,
                             'focused': True, 'in_world': True, 'screen': 'Game', 'camera': 'first person',
                             'frame_interval_ms': {'samples': 5, 'mean': 16, 'p50': 16, 'p95': 18, 'max': 20}}]}

    def latest(self, now=NOW):
        with patch('control_room.metrics.time.time', return_value=now):
            return self.metrics.latest()

    def test_current_view_is_isolated_and_does_not_probe_or_mutate_raw_sample(self):
        raw = self.sample()
        self.metrics._latest = raw
        current = self.latest()
        self.assertEqual(current['tps'], 20)
        self.assertEqual(current['players_online'], 1)
        self.assertTrue(current['freshness']['bridge']['current'])
        self.assertEqual(current['last_known'], {})
        current['players'][WHO['uuid']]['x'] = 999
        current['clients'][0]['fps'] = 2
        self.assertEqual(raw['players'][WHO['uuid']]['x'], 1)
        self.assertEqual(raw['clients'][0]['fps'], 60)
        self.assertNotIn('freshness', raw)
        self.server.probe.assert_not_called()
        self.server.snapshot.assert_not_called()

    def test_cache_expiry_hides_old_live_fields_and_preserves_last_measured_values(self):
        raw = self.sample()
        before = deepcopy(raw)
        self.metrics._latest = raw
        for age in (21, 46):
            with self.subTest(age=age):
                current = self.latest(NOW+age)
                self.assertIsNone(current['tps'])
                self.assertIsNone(current['mspt'])
                self.assertIsNone(current['tick_at'])
                self.assertIsNone(current['server_rss'])
                self.assertIsNone(current['players'])
                self.assertIsNone(current['players_online'])
                self.assertFalse(current['players_available'])
                self.assertEqual(current['at'], NOW)
                self.assertEqual(current['tick_measured_at'], iso(NOW))
                self.assertEqual(current['last_known']['tick']['tps'], 20)
                self.assertEqual(current['last_known']['bridge']['players'], raw['players'])
                self.assertEqual(current['last_known']['snapshot']['server_rss'], 6*GiB)
                self.assertEqual(current['clients'][0]['last_known']['game']['fps'], 60)
                self.assertIsNone(current['clients'][0]['fps'])
                self.assertIsNone(current['clients'][0]['rss'])
                self.assertIsNone(current['clients'][0]['in_world'])
                self.assertEqual(current['freshness']['snapshot']['age_seconds'], age)
        self.assertEqual(raw, before)

    def test_old_bridge_does_not_erase_fresh_process_or_console_tick_measurements(self):
        raw = self.sample()
        raw.update(bridge_at=iso(NOW-21), tick_source='NeoForge console')
        self.metrics._latest = raw
        current = self.latest()
        self.assertEqual(current['tps'], 20)
        self.assertEqual(current['server_rss'], 6*GiB)
        self.assertEqual(current['host_memory_available'], 5*GiB)
        self.assertIsNone(current['heap_used'])
        self.assertIsNone(current['loaded_chunks'])
        self.assertIsNone(current['players'])
        self.assertIsNone(current['players_online'])
        self.assertEqual(current['bridge_age_seconds'], 21)
        self.assertEqual(current['bridge_capabilities'], [])
        self.assertEqual(current['atlas_objects'], [])
        self.assertEqual(current['cinematics'], {})
        self.assertIn('unavailable', current['chunk_diagnostics'])

    def test_old_tick_and_old_client_expire_independently_of_a_fresh_bridge(self):
        raw = self.sample()
        raw['tick_at'] = iso(NOW-21)
        raw['clients'][0]['at'] = iso(NOW-46)
        self.metrics._latest = raw
        current = self.latest()
        self.assertIsNone(current['tps'])
        self.assertTrue(current['players_available'])
        self.assertEqual(current['players_online'], 1)
        self.assertEqual(current['loaded_chunks'], 500)
        client = current['clients'][0]
        self.assertIsNone(client['fps'])
        self.assertIsNone(client['heap_used'])
        self.assertIsNone(client['in_world'])
        self.assertIsNone(client['focused'])
        self.assertIsNone(client['screen'])
        self.assertEqual(client['rss'], 3*GiB)
        self.assertEqual(client['cpu_percent_host'], 10)
        self.assertEqual(client['last_known']['game']['at'], iso(NOW-46))
        self.assertEqual(current['server_rss'], 6*GiB)

    def test_old_collection_cannot_be_rescued_by_an_independently_newer_timestamp(self):
        raw = self.sample()
        raw['at'] = NOW-30
        self.metrics._latest = raw
        current = self.latest()
        self.assertFalse(current['freshness']['bridge']['current'])
        self.assertIsNone(current['tick_at'])
        self.assertIsNone(current['players'])
        self.assertIsNone(current['clients'][0]['fps'])

    def test_missing_bridge_roster_is_unknown_not_an_empty_online_roster(self):
        raw = self.sample()
        raw.pop('player_roster_at')
        raw['players'] = {}
        self.metrics._latest = raw
        current = self.latest()
        self.assertTrue(current['freshness']['bridge']['current'])
        self.assertFalse(current['players_available'])
        self.assertIsNone(current['players'])
        self.assertIsNone(current['players_online'])

    def test_chunk_diagnostics_have_their_own_bounded_30_second_sampling_window(self):
        raw = self.sample()
        raw['chunk_diagnostics']['at'] = iso(NOW-30)
        self.metrics._latest = raw
        self.assertNotIn('unavailable', self.latest()['chunk_diagnostics'])
        raw['chunk_diagnostics']['at'] = iso(NOW-46)
        current = self.latest()
        self.assertIn('unavailable', current['chunk_diagnostics'])
        self.assertEqual(current['last_known']['chunk_diagnostics']['at'], iso(NOW-46))
        self.assertEqual(current['loaded_chunks'], 500)

    def test_invalid_future_and_extremely_old_ages_are_finite_and_never_current(self):
        for stamp in (None, {}, float('nan'), 'bad', iso(NOW+20), iso(NOW-10**8)):
            with self.subTest(stamp=stamp):
                value = measurement_freshness(stamp, NOW)
                self.assertFalse(value['current'])
                if value['age_seconds'] is not None:
                    self.assertGreaterEqual(value['age_seconds'], 0)
                    self.assertLessEqual(value['age_seconds'], MAX_AGE_SECONDS)
                json.dumps(value, allow_nan=False)
        self.assertEqual(measurement_freshness(iso(NOW+20), NOW)['status'], 'clock_skew')
        self.assertTrue(measurement_freshness(iso(NOW-10**8), NOW)['age_capped'])
        self.assertTrue(measurement_freshness(iso(NOW-15), NOW)['current'])
        self.assertFalse(measurement_freshness(iso(NOW-15.01), NOW)['current'])

    def test_history_and_csv_keep_the_original_measurement_after_live_view_expires(self):
        raw = self.sample()
        self.metrics._latest = raw
        with self.metrics.connect() as connection:
            connection.execute('CREATE TABLE samples (at REAL PRIMARY KEY, data TEXT NOT NULL)')
            connection.execute('INSERT INTO samples VALUES (?, ?)', (NOW, json.dumps(raw)))
        with patch('control_room.metrics.time.time', return_value=NOW+60):
            self.assertIsNone(self.metrics.latest()['tps'])
            history = self.metrics.history()
            csv = self.metrics.csv()
        self.assertEqual(history, [raw])
        self.assertIn(iso(NOW), csv)
        self.assertIn(',20,9.5,', csv)

    def test_collection_ownership_identity_and_age_gates_are_unchanged(self):
        data = {'format': 'awft-metrics:1', 'pid': 42, 'process_started': iso(NOW-60), 'at': iso(NOW),
                'tps': 20, 'mspt': 10, 'heap_used': 4*GiB, 'heap_max': 8*GiB,
                'loaded_chunks': 500, 'entities': 200, 'gc_collections': 1,
                'gc_collection_ms': 5, 'dimensions': {}, 'players': {}}
        for changes in ({}, {'pid': 43}, {'process_started': iso(NOW-80)}, {'at': iso(NOW-16)}):
            with self.subTest(changes=changes):
                write_json(self.layout.state/'server-metrics.json', data | changes)
                sample = {'at': NOW, 'players': {}, 'bridge_capabilities': [], 'unavailable': {}}
                with patch('control_room.metrics.time.time', return_value=NOW):
                    self.metrics.apply_bridge(sample, {'state': 'online', 'pid': 42})
                if changes:
                    self.assertNotIn('bridge_at', sample)
                    self.assertEqual(sample['players'], {})
                    self.assertIn('bridge_error', sample)
                else:
                    self.assertEqual(sample['bridge_at'], iso(NOW))
                    self.assertEqual(sample['loaded_chunks'], 500)

    def application(self):
        app = Application.__new__(Application)
        for name in ('mods', 'backups', 'settings', 'storage', 'players', 'atlas', 'cinematics',
                     'installer', 'jobs', 'graphics'):
            setattr(app, name, Mock())
        app.layout = self.layout
        app.token = 'synthetic-test-session'
        app.mods.active.return_value = ({'version': 'candidate-test', 'minecraft': '1.21.1',
                                        'neoforge': '21.1.262', 'mods': [], 'release_status': 'candidate'}, None)
        app.backups.list.return_value = []
        app.backups.last_schedule_error = None
        app.settings.get_properties.return_value = {}
        app.storage.snapshot.return_value = {}
        app.mods.overview_sync.return_value = {}
        app.active_test = lambda: None
        app.metrics = self.metrics
        server = Server(self.layout, self.storage)
        server.identity = {'pid': 42, 'created': NOW-60}
        server.state, server.started = 'online', NOW-30
        server.running = Mock(return_value=True)
        server.tick = {'at': iso(NOW), 'tps': 20, 'mspt': 9.5, 'source': 'Owned console'}
        server.player_info = {'players': {'online': 2, 'max': 2, 'sample': [WHO]}}
        server.player_info_at = NOW
        server.player_info_identity = 42, NOW-60
        server._last_player_info = server.player_info
        server._last_player_info_at = NOW
        app.server = server
        self.metrics._latest = self.sample()
        return app

    def test_overview_sibling_and_metrics_routes_expire_without_changing_process_status(self):
        app = self.application()
        original_tick, original_status = deepcopy(app.server.tick), deepcopy(app.server.player_info)
        for age in (21, 46):
            with self.subTest(age=age), patch('control_room.metrics.time.time', return_value=NOW+age):
                overview = app.get('/api/overview', {})
                api_metrics = app.get('/api/metrics', {})
                self.assertIsNone(api_metrics['tps'])
                self.assertIsNone(overview['metrics']['tps'])
                self.assertIsNone(overview['server']['tick']['tps'])
                self.assertIsNone(overview['server']['status'])
                self.assertEqual(overview['server']['state'], 'online')
                self.assertEqual(overview['server']['pid'], 42)
                self.assertEqual(overview['server']['uptime_seconds'], 30+age)
                self.assertEqual(overview['server']['last_known']['tick'], original_tick)
                self.assertEqual(overview['server']['last_known']['status']['measured_at'], NOW)
                self.assertEqual(overview['server']['last_known']['status']['data'], original_status)
        self.assertEqual(app.server.tick, original_tick)
        self.assertEqual(app.server.player_info, original_status)
        self.assertEqual(app.server.identity, {'pid': 42, 'created': NOW-60})

    def test_server_snapshot_independent_roster_age_and_process_identity(self):
        app = self.application()
        with patch('control_room.metrics.time.time', return_value=NOW):
            current = app.server.snapshot()
            self.assertEqual(current['status']['players']['online'], 2)
            app.server.player_info_at = NOW-21
            stale = app.server.snapshot()
            self.assertIsNone(stale['status'])
            self.assertEqual(stale['tick']['tps'], 20)
            app.server.player_info_at = NOW
            app.server.player_info_identity = 99, NOW-60
            replaced = app.server.snapshot()
            self.assertIsNone(replaced['status'])
            self.assertFalse(replaced['freshness']['player_status']['current'])
            self.assertEqual(replaced['state'], 'online')

    def test_status_poll_failure_retains_last_known_without_inferring_server_offline(self):
        app = self.application()
        app.server._last_probe = float('inf')  # No console command belongs in this test.
        with patch('control_room.server.minecraft_status', side_effect=OSError('synthetic unavailable')):
            app.server.probe()
        with patch('control_room.metrics.time.time', return_value=NOW+1):
            current = app.server.snapshot()
        self.assertIsNone(current['status'])
        self.assertEqual(current['state'], 'online')
        self.assertEqual(current['last_known']['status']['data']['players']['online'], 2)
        self.assertEqual(current['last_known']['status']['measured_at'], NOW)


class PlayerPresenceFreshnessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='awft-player-freshness-')
        self.addCleanup(self.temp.cleanup)
        self.layout = Layout(Path(self.temp.name))
        self.layout.create()
        write_json(self.layout.server/'whitelist.json', [WHO])
        self.storage, self.settings = Mock(), Mock()
        self.server = Mock()
        self.status = {'state': 'online', 'pid': 42, 'events': [],
                       'status': {'players': {'online': 2, 'max': 2}}}
        self.server.snapshot.side_effect = lambda: deepcopy(self.status)
        self.server.running.side_effect = lambda: bool(self.status.get('pid'))
        self.data = {'tick_at': iso(NOW), 'players_available': True,
                     'players': {WHO['uuid']: dict(WHO, x=10, y=65, z=-20)},
                     'bridge_capabilities': ['player_locations', 'player_permissions']}
        self.players = Players(self.layout, self.storage, self.server, self.settings, lambda: self.data)

    def detail(self):
        with patch('control_room.players.time.time', return_value=NOW):
            return self.players.details(WHO['name'])

    def test_expired_telemetry_is_unknown_and_cannot_be_used_as_live_coordinates(self):
        current = self.detail()
        self.assertIs(current['online'], True)
        self.assertEqual(current['location_state'], 'live')
        self.data['tick_at'] = iso(NOW-21)
        last = self.detail()
        self.assertIsNone(last['online'])
        self.assertEqual(last['online_state'], 'unknown')
        self.assertEqual(last['location_state'], 'last seen')
        self.assertEqual(last['location']['x'], 10)
        self.assertEqual(last['location']['at'], iso(NOW))
        self.assertEqual(last['capabilities'], [])
        with patch('control_room.players.time.time', return_value=NOW):
            snapshot = self.players.snapshot()
            self.assertIsNone(snapshot['online'])
            with self.assertRaises(UserError):
                self.players.game_action(WHO['name'], 'xp-level', 2, confirmed=True)
        self.server._write.assert_not_called()
        self.assertEqual(read_json(self.layout.state/'last-player-locations.json')[WHO['uuid']]['at'], iso(NOW))

    def test_missing_or_explicitly_unavailable_bridge_is_unknown_even_if_cached_status_says_online(self):
        for data in ({}, {'tick_at': iso(NOW), 'players_available': False, 'players': None}):
            self.data = data
            who = self.detail()
            self.assertIsNone(who['online'])
            self.assertEqual(who['online_state'], 'unknown')
            self.assertIsNone(who['location'])

    def test_fresh_complete_empty_roster_and_stopped_process_independently_prove_offline(self):
        self.data['players'] = {}
        self.assertIs(self.detail()['online'], False)
        self.data = {}
        self.status.update(state='offline', pid=None, status=None)
        who = self.detail()
        self.assertIs(who['online'], False)
        self.assertEqual(who['online_state'], 'offline')
        with patch('control_room.players.time.time', return_value=NOW):
            self.assertEqual(self.players.snapshot()['online']['online'], 0)

    def test_fresh_player_count_uses_complete_bridge_roster_not_cached_status_count(self):
        with patch('control_room.players.time.time', return_value=NOW):
            current = self.players.snapshot()
        self.assertEqual(current['online']['online'], 1)
        self.assertEqual(current['online']['sample'][0]['name'], WHO['name'])
        self.assertEqual(current['online_state'], 'current')

    def test_offline_operator_and_whitelist_edits_remain_available_without_location_telemetry(self):
        self.data = {}
        self.status.update(state='offline', pid=None, status=None)
        with patch('control_room.players.time.time', return_value=NOW):
            result = self.players.permissions(WHO['name'], 4, confirmed=True)
        self.assertEqual(result['operator_level'], 4)
        self.assertEqual(read_json(self.layout.server/'ops.json')[0]['uuid'], WHO['uuid'])
        with patch('control_room.players.profile', return_value=WHO):
            self.players.update('whitelist-remove', WHO['name'], confirmed=True)
        self.assertEqual(read_json(self.layout.server/'whitelist.json'), [])
        self.server._write.assert_not_called()

    def test_unknown_presence_does_not_bypass_live_permission_capability_gate(self):
        self.data = {}
        with patch('control_room.players.time.time', return_value=NOW):
            with self.assertRaisesRegex(UserError, 'fresh Control Bridge'):
                self.players.permissions(WHO['name'], 4, confirmed=True)
        self.server._write.assert_not_called()
        self.assertFalse((self.layout.server/'ops.json').exists())


if __name__ == '__main__':
    unittest.main()
