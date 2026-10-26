from copy import deepcopy
from unittest.mock import patch

from control_room.chunks import validate
from control_room.client_metrics import ClientMetrics
from control_room.common import utcnow,write_json
from test_safety import Fixture


class DiagnosticAuthorityTests(Fixture):
    def test_missing_or_stale_tick_is_never_a_fresh_idle_sample(self):
        from tools.live_samples import fresh_tick
        for value in (None, '', {}, 'not a timestamp', '2020-01-01T00:00:00Z'):
            self.assertFalse(fresh_tick(value))
        self.assertTrue(fresh_tick(utcnow()))

    def sample(self):
        counters={key:0 for key in ('visible_holders','full_chunks','block_ticking','entity_ticking','holders_examined','pending_unloads','vanilla_forced_chunks','ticket_positions')}
        counters['details']={'sources':[],'ticket_levels':{},'truncated':True,'measurement_ms':1.2,
            'mod_owners':{'owners':[{'controller':'example:machine','kind':'block','owner':'BlockPos{x=1, y=64, z=2}','ticking':True,'chunks':9}]}}
        return {'at':utcnow(),'dimensions':{'minecraft:overworld':counters},'spawn_chunk_radius':2}

    def test_partial_diagnostics_and_mod_ownership_remain_explicit(self):
        sample=validate(self.sample())
        details=sample['dimensions']['minecraft:overworld']['details']
        self.assertTrue(details['truncated'])
        self.assertEqual(details['mod_owners']['owners'][0]['controller'],'example:machine')
        self.assertEqual(details['mod_owners']['owners'][0]['chunks'],9)

    def test_diagnostics_reject_unbounded_and_nonfinite_measurements(self):
        for key,bad in [('measurement_ms',float('nan')),('sources',[{}]*65)]:
            sample=self.sample();sample['dimensions']['minecraft:overworld']['details'][key]=bad
            with self.assertRaises(ValueError):validate(sample)
        sample=self.sample();sample['dimensions']['minecraft:overworld']['visible_holders']=True
        with self.assertRaises(ValueError):validate(sample)
        sample=self.sample();sample['dimensions']['minecraft:overworld']['details']['mod_owners']['owners']*=65
        with self.assertRaises(ValueError):validate(sample)

    def test_stale_or_unowned_client_data_cannot_be_reported_as_live(self):
        instance=self.layout.home/'instances/AWFT_Test'
        metric=instance/'.minecraft/awft-client-metrics.json'
        write_json(metric,{'format':'awft-client-metrics:1','at':'2000-01-01T00:00:00Z','pid':123})
        collector=ClientMetrics(self.layout)
        with patch('control_room.client_metrics.psutil.Process') as process:
            self.assertEqual(collector.collect(),[])
            process.assert_not_called()
            write_json(instance/'awft-owned.json',{'format':'awft-owned-client:1','root':str(instance)})
            self.assertEqual(collector.collect(),[])
            process.assert_not_called()
