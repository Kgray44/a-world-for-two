"""Synthetic timing arithmetic and provenance rejection, not real TPS evidence."""
import json
import unittest
from control_room.common import UserError
from tools.transport_performance import sample_row,summarize,timestamp


def raw(at='2026-10-28T18:00:05Z',**changes):
    value={'format':'awft-metrics:1','at':at,'pid':1234,'process_started':'2026-10-28T17:00:00Z',
           'tps':20.,'mspt':4.,'ticks_sampled':100,'interval_ms':5000.,'players':{}}
    value.update(changes);return json.dumps(value).encode()


def row(at='2026-10-28T18:00:05Z',**changes):
    return sample_row(raw(at,**changes),now=timestamp(at),pid=1234,started='2026-10-28T17:00:00Z')


class TransportPerformanceTests(unittest.TestCase):
    def test_tick_weighting_uses_real_counts_and_interval_wall_time(self):
        result=summarize([row(),row('2026-10-28T18:00:15Z',tps=10.,mspt=20.,ticks_sampled=100,interval_ms=10000.)])
        self.assertAlmostEqual(result['aggregate_tps'],200/15)
        self.assertEqual(result['tick_weighted_mean_mspt'],12.)
        self.assertEqual(result['worst_interval_mean_mspt'],20.)
        self.assertIn('not per-tick percentiles',result['limits'])

    def test_duplicate_and_overlapping_intervals_refuse(self):
        with self.assertRaises(UserError):summarize([row(),row()])
        with self.assertRaises(UserError):summarize([row(),row('2026-10-28T18:00:06Z')])

    def test_stale_future_and_other_process_samples_refuse(self):
        for now,body in [(timestamp('2026-10-28T18:00:30Z'),raw()),(timestamp('2026-10-28T18:00:00Z'),raw()),
                         (timestamp('2026-10-28T18:00:05Z'),raw(pid=5678))]:
            with self.assertRaises(UserError):sample_row(body,now=now,pid=1234,started='2026-10-28T17:00:00Z')

    def test_missing_roster_nonfinite_and_inconsistent_timing_refuse(self):
        for changes in ({'players':None},{'tps':float('nan')},{'mspt':float('inf')},
                        {'tps':19.},{'ticks_sampled':0},{'ticks_sampled':True}):
            with self.assertRaises(UserError):row(**changes)

    def test_roster_change_is_reported_without_inventing_a_controlled_window(self):
        result=summarize([row(),row('2026-10-28T18:00:10Z',players={'synthetic-player':{}})])
        self.assertFalse(result['player_rosters_stable'])


if __name__=='__main__':unittest.main()
