"""Slow bookkeeping cannot hold fresh owned telemetry hostage; no Minecraft JVM."""
from datetime import datetime,timezone
from pathlib import Path
import tempfile,threading,time,unittest
from unittest.mock import Mock,patch

from control_room.common import Layout,GiB,UserError
from control_room.metrics import Metrics


def iso(stamp):return datetime.fromtimestamp(stamp,timezone.utc).isoformat()


class MetricsBookkeepingTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='awft-fast-metrics-')
        self.addCleanup(self.temp.cleanup)
        self.layout=Layout(Path(self.temp.name));self.layout.create()
        self.storage=Mock()
        self.storage.snapshot.return_value={'drives':[{'free':100*GiB}],
            'breakdown':{'measured_at':'2026-10-28T00:00:00+00:00','updating':True,
                'categories':[{'key':'world','bytes':123},{'key':'caches','bytes':456}]}}
        self.server=Mock()
        self.server.snapshot.return_value={'pid':None,'state':'offline','tick':
            {'tps':None,'mspt':None,'at':None,'source':'synthetic'}}
        self.metrics=Metrics(self.layout,self.storage,self.server)
        self.addCleanup(self.metrics.close)
        with self.metrics.connect()as db:db.execute('CREATE TABLE samples(at REAL PRIMARY KEY,data TEXT NOT NULL)')
        self.metrics.clients.collect=Mock(return_value=[])
        def fresh_bridge(sample,server):
            now=iso(time.time());sample.update(bridge_at=now,player_roster_at=now,
                players={},tick_at=now,tps=20,mspt=3,loaded_chunks=50)
        self.metrics.apply_bridge=Mock(side_effect=fresh_bridge)

    def test_slow_reserve_client_and_observer_steps_do_not_block_publication_or_next_collect(self):
        for where in('reserve','client','observer'):
            with self.subTest(where=where):
                entered,release=threading.Event(),threading.Event()
                self.addCleanup(release.set)
                def blocked(*args):entered.set();release.wait(3);return []
                self.storage.checkpoint.side_effect=blocked if where=='reserve'else None
                self.metrics.clients.collect.side_effect=blocked if where=='client'else None
                self.metrics.observers=[blocked]if where=='observer'else[]
                self.metrics.collect();self.assertTrue(entered.wait(2))
                answer=[];finished=threading.Event()
                def collect_again():
                    answer.append(self.metrics.collect());finished.set()
                worker=threading.Thread(target=collect_again);started=time.perf_counter();worker.start()
                try:
                    self.assertTrue(finished.wait(1),'Fast collection waited for blocked bookkeeping')
                    worker.join(1)
                    live=self.metrics.latest()
                    self.assertTrue(live['players_available'])
                    self.assertEqual(live['players'],{})
                    self.assertLess(time.perf_counter()-started,1)
                    self.assertEqual(answer[0]['managed_sizes'],{'world':123,'caches':456})
                    self.assertEqual(answer[0]['managed_sizes_at'],'2026-10-28T00:00:00+00:00')
                    self.assertEqual(self.metrics._pending_sample['at'],answer[0]['at'])
                finally:release.set();worker.join(2)
                self.assertTrue(self.metrics._bookkeeping_idle.wait(3))
                self.assertIsNone(self.metrics._pending_sample)
                self.assertEqual(self.metrics.history()[-1]['at'],answer[0]['at'])

    def test_reserve_failure_still_prevents_history_and_observer_writes(self):
        self.storage.checkpoint.side_effect=UserError('synthetic reserve refusal')
        observe=Mock();self.metrics.observers=[observe]
        self.metrics.collect();self.assertTrue(self.metrics._bookkeeping_idle.wait(2))
        current=self.metrics.collect()
        self.assertEqual(current['bookkeeping_error'],'synthetic reserve refusal')
        self.assertTrue(self.metrics.latest()['players_available'])
        self.assertTrue(self.metrics._bookkeeping_idle.wait(2))
        observe.assert_not_called();self.assertEqual(self.metrics.history(),[])

    def test_cached_client_process_and_game_expire_independently(self):
        now=time.time()
        self.metrics._latest={'at':now,'clients':[{'at':iso(now),'process_at':now-30,
            'fps':60,'rss':2*GiB,'cpu_percent_host':4}],'unavailable':{}}
        view=self.metrics.latest()['clients'][0]
        self.assertEqual(view['fps'],60)
        self.assertIsNone(view['rss']);self.assertIsNone(view['cpu_percent_host'])
        self.assertFalse(view['process_freshness']['current'])
        self.assertEqual(view['last_known']['process']['measured_at'],now-30)


if __name__=='__main__':unittest.main()
