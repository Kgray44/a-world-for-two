"""Dormant test tools must never mistake missing player telemetry for clean idle."""
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

from control_room.common import UserError
from tools.idle_probe import admit_probe, experiment, require_idle
from tools.live_samples import fresh_players, fresh_tick, idle_window
from tools.playtest import presence_phase


NOW = 1_800_000_000


def iso(value):
    return datetime.fromtimestamp(value, timezone.utc).isoformat()


def sample(now=NOW, players=None):
    return {'at': now, 'tick_at': iso(now), 'bridge_at': iso(now),
            'player_roster_at': iso(now), 'players_available': True,
            'players': {} if players is None else players,
            'chunk_diagnostics': {'at': iso(now), 'dimensions': {
                'minecraft:overworld': {'vanilla_forced_chunks': 0}}}}


class ToolFreshnessTests(unittest.TestCase):
    def test_only_an_explicit_current_complete_roster_can_establish_empty(self):
        self.assertTrue(fresh_players(sample(), NOW))
        for key, value in [('players_available', None), ('players_available', False),
                           ('players_available', 1), ('players', None), ('player_roster_at', None)]:
            with self.subTest(key=key, value=value):
                row = sample()
                row[key] = value
                self.assertFalse(fresh_players(row, NOW))
                with self.assertRaises(UserError):
                    require_idle(row, NOW)

    def test_response_age_recheck_expires_collection_bridge_and_roster_independently(self):
        for key in ('at', 'bridge_at', 'player_roster_at'):
            row = sample()
            row[key] = NOW-21 if key == 'at' else iso(NOW-21)
            with self.subTest(key=key):
                self.assertFalse(fresh_players(row, NOW))
                self.assertEqual(presence_phase('active player gameplay', True, row, NOW),
                                 'player telemetry unavailable')
        self.assertFalse(fresh_players(sample(), NOW+46))

    def test_invalid_naive_and_future_timestamps_do_not_authorize_idle(self):
        for value in (None, {}, '2027-01-15T08:00:00', 'not a date', iso(NOW+3)):
            with self.subTest(value=value):
                self.assertFalse(fresh_tick(value, NOW))
                row = sample()
                row['player_roster_at'] = value
                self.assertFalse(fresh_players(row, NOW))

    def test_missing_observation_resets_continuous_idle_without_claiming_disconnect(self):
        row = sample(players={'person': {'name': 'Synthetic Player'}})
        ever, since = idle_window(row, False, None, 10, NOW)
        self.assertEqual((ever, since), (True, None))
        ever, since = idle_window(sample(), ever, since, 20, NOW)
        self.assertEqual((ever, since), (True, 20))
        unknown = sample()
        unknown.update(players_available=False, players=None, last_known={'players': row['players']})
        before = deepcopy(unknown)
        ever, since = idle_window(unknown, ever, since, 319, NOW)
        self.assertEqual((ever, since), (True, None))
        self.assertEqual(idle_window(sample(), ever, since, 321, NOW), (True, 321))
        self.assertEqual(unknown, before)

    def test_playtest_unknown_interrupts_all_idle_probe_phases(self):
        unknown = sample()
        unknown['players_available'] = False
        for phase in ('active player gameplay', 'post-disconnect idle',
                      'controlled nine-chunk force-load probe', 'extended idle after force-load removal'):
            self.assertEqual(presence_phase(phase, True, unknown, NOW), 'player telemetry unavailable')
        self.assertEqual(presence_phase('player telemetry unavailable', True, sample(), NOW), 'post-disconnect idle')
        self.assertEqual(presence_phase('player telemetry unavailable', False, sample(), NOW), 'startup idle; no generation probes')
        self.assertEqual(presence_phase('post-disconnect idle', True,
                                       sample(players={'person': {}}), NOW), 'active player gameplay')

    def test_force_load_requires_known_fresh_zero_baseline_as_well_as_roster(self):
        admit_probe(sample(), NOW)
        invalid = []
        for diagnostic in (None, {}, {'at': iso(NOW), 'dimensions': {}},
                           {'at': iso(NOW-46), 'dimensions': {'minecraft:overworld': {'vanilla_forced_chunks': 0}}},
                           {'at': iso(NOW), 'dimensions': {'minecraft:overworld': {}}}):
            row = sample()
            row['chunk_diagnostics'] = diagnostic
            invalid.append(row)
        forced = sample()
        forced['chunk_diagnostics']['dimensions']['minecraft:overworld']['vanilla_forced_chunks'] = 9
        invalid.append(forced)
        invalid.append(sample(players={'person': {}}))
        for row in invalid:
            with self.subTest(row=row), self.assertRaises(UserError):
                admit_probe(row, NOW)

    def run_probe(self, unknown_after=None):
        clock = [0]
        app = Mock()
        app.layout.logs = Path('synthetic-no-write')
        app.server.running.return_value = True
        def latest():
            row = sample(NOW+clock[0])
            if unknown_after is not None and clock[0] >= unknown_after:
                row.update(players_available=False, players=None,
                           bridge_error='Synthetic missing telemetry',
                           last_known={'players': {'person': {'name': 'Previously observed'}}})
            return row
        def advance(seconds):
            clock[0] += seconds
        app.metrics.latest.side_effect = latest
        with patch('tools.idle_probe.time.monotonic', side_effect=lambda: clock[0]), \
             patch('tools.idle_probe.time.time', side_effect=lambda: NOW+clock[0]), \
             patch('tools.idle_probe.time.sleep', side_effect=advance), \
             patch('tools.idle_probe.digest', return_value='synthetic-pack'), \
             patch('tools.idle_probe.write_json') as write, patch('builtins.print'):
            experiment(app)
        return app, write.call_args.args[1]

    def test_probe_never_adds_tickets_with_missing_roster_and_preserves_diagnostic(self):
        app, receipt = self.run_probe(unknown_after=0)
        app.server._write.assert_not_called()
        self.assertEqual(receipt['status'], 'incomplete; exact failure preserved')
        row = receipt['interrupted_observation']['sample']
        self.assertIsNone(row['players'])
        self.assertEqual(row['bridge_error'], 'Synthetic missing telemetry')
        self.assertIn('person', row['last_known']['players'])

    def test_probe_cleans_only_its_exact_tickets_when_roster_becomes_unknown(self):
        app, receipt = self.run_probe(unknown_after=95)
        self.assertEqual([call.args[0] for call in app.server._write.call_args_list],
                         ['forceload add 2048 2048 2080 2080', 'forceload remove 2048 2048 2080 2080'])
        self.assertEqual(len(receipt['phases']), 1)
        self.assertIn('unavailable', receipt['error'])

    def test_complete_probe_requires_continuously_observed_empty_rosters(self):
        app, receipt = self.run_probe()
        self.assertTrue(receipt['status'].startswith('completed;'))
        self.assertEqual(len(receipt['phases']), 3)
        self.assertEqual([call.args[0] for call in app.server._write.call_args_list],
                         ['forceload add 2048 2048 2080 2080', 'forceload remove 2048 2048 2080 2080'])


if __name__ == '__main__':
    unittest.main()
