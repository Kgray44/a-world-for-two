"""Synthetic observation-audit fixtures, never actual KG/Sera gameplay evidence."""
from copy import deepcopy
import json
import math
import unittest

from control_room.common import UserError
from tools.transport_commission import MILL, ORCHARD
from tools.transport_passenger_audit import (
    ENTRANCES, SCOPE, STATIONS, train_round_trip, tube_round_trip,
)
from tests.test_transport_commission import observation

PLAYERS = ['00000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000002']
TRAIN = '00000000-0000-0000-0000-000000000003'
GRAPH = '00000000-0000-0000-0000-000000000004'


def native_schedule():
    entries = []
    for name, count, exact in ((MILL, 2, 1), (ORCHARD, 2, 1), (MILL, 0, 0)):
        entries.append('{Instruction:{Id:"create:destination",Data:{Text:'+json.dumps(name)+'}},'
                       'Conditions:[[{Id:"create:delay",Data:{Value:20,TimeUnit:1}},'
                       '{Id:"create:player_count",Data:{Count:'+str(count)+',Exact:'+str(exact)+'}}]]}')
    return '{Cyclic:0b,Entries:['+','.join(entries)+']}'


def capture(n, z, *, train=None, tube=False, ground=True):
    row = observation()
    row.update(at=f'2026-10-28T18:{n:02}:00Z', game_time=100+n*1200,
               train_position_scope=deepcopy(SCOPE), trains=[])
    row['players'] = [{'uuid':player, 'name':'SYNTHETIC-'+str(i), 'position':[1331,71,z],
                       'chunk':[83,math.floor(z/16)], 'dimension':'minecraft:overworld',
                       'health':20, 'on_ground':ground, 'train_uuid':train,
                       'hypertube_native_travel':tube} for i,player in enumerate(PLAYERS)]
    row['tube_links'] = [{'uuid':f'00000000-0000-0000-0000-{n+20:012x}',
                          'from':[1331,71,-991+8*n], 'to':[1331,71,-983+8*n],
                          'distance':8, 'available':True, 'stored_reciprocal':True} for n in range(6)]
    return row


def train_fixture():
    rows = []
    for n, (z, station, speed, entry) in enumerate(((-994,MILL,0,0),(-994,MILL,0,0),
            (-970,None,.2,1),(-942,ORCHARD,0,1),(-970,None,-.2,2),(-994,MILL,0,2),(-994,MILL,0,0))):
        row = capture(n, z, train=TRAIN if 1<=n<=5 else None)
        row['track_graph'] = {'status':'station_nodes_connected','graph_id':GRAPH}
        row['stations'] = [{'position':position, 'name':name, 'available':True,
                             'valid_track':True, 'station_point':True, 'graph_id':GRAPH,
                             'station_uuid':f'00000000-0000-0000-0000-{i+10:012x}',
                             'present_train':TRAIN if name==station else None}
                            for i,(position,name) in enumerate(zip(STATIONS,(MILL,ORCHARD)))]
        row['trains'] = [{'uuid':TRAIN, 'position':[1336,71,z], 'speed':speed,
                          'station':station,'invalid':False,'derailed':False,'double_ended':True,
                          'forward_conductor':True,'backward_conductor':True,'carriages':1,
                          'seats':[3],'graph_id':GRAPH,'schedule_present':True,'schedule_cyclic':False,
                          'schedule_entry':entry,'schedule_completed':n==6,'schedule_paused':n==6,
                          'native_schedule_snbt':native_schedule(),'player_passengers':2 if 1<=n<=5 else 0}]
        rows.append(row)
    return rows


def tube_fixture():
    return [capture(n,z,tube=n in (1,2,5,6),ground=n not in (1,2,5,6))
            for n,z in enumerate((-991,-980,-950,-943,-943,-950,-980,-991))]


class PassengerAuditTests(unittest.TestCase):
    def test_observed_two_player_train_round_trip(self):
        result = train_round_trip(train_fixture(),PLAYERS)
        self.assertTrue(result['passed']);self.assertEqual(result['observed_train_uuid'],TRAIN)
        self.assertIn('Observed states only',result['evidence_scope'])

    def test_schedule_substitution_or_wrong_progress_cannot_pass(self):
        for field,value in (('native_schedule_snbt','{Cyclic:0b,Entries:[]}'),('schedule_entry',99)):
            rows=train_fixture();rows[2]['trains'][0][field]=value
            with self.assertRaises(UserError):train_round_trip(rows,PLAYERS)

    def test_changed_route_dwell_or_player_condition_cannot_pass(self):
        for old,new in (('Value:20','Value:1'),('Count:2','Count:1'),('Copper Wren Mill','Wrong Station')):
            rows=train_fixture();rows[2]['trains'][0]['native_schedule_snbt']=native_schedule().replace(old,new)
            with self.assertRaises(UserError):train_round_trip(rows,PLAYERS)

    def test_known_saved_progress_is_not_a_changed_route(self):
        rows=train_fixture();rows[4]['trains'][0]['native_schedule_snbt']=native_schedule()[:-1]+',Progress:2}'
        self.assertTrue(train_round_trip(rows,PLAYERS)['passed'])

    def test_fake_displacement_without_both_native_passengers_fails(self):
        for field,value in (('train_uuid',None),('hypertube_native_travel',True)):
            rows=train_fixture();rows[2]['players'][1][field]=value
            with self.assertRaises(UserError):train_round_trip(rows,PLAYERS)

    def test_real_named_attachment_and_final_unloading_are_required(self):
        for mutate in (lambda r:r[3]['stations'][1].update(present_train=None),
                       lambda r:r[6]['players'][1].update(train_uuid=TRAIN),
                       lambda r:r[6]['trains'][0].update(schedule_completed=False)):
            rows=train_fixture();mutate(rows)
            with self.assertRaises(UserError):train_round_trip(rows,PLAYERS)

    def test_both_tube_directions_with_native_flag_and_z_chunk_crossing(self):
        self.assertTrue(tube_round_trip(tube_fixture(),PLAYERS)['passed'])

    def test_x_only_chunk_change_cannot_prove_straight_tube_boundary(self):
        rows=tube_fixture()
        for n,x,z in ((1,1327,-989),(2,1331,-981)):
            for player in rows[n]['players']:
                player.update(position=[x,71,z],chunk=[math.floor(x/16),math.floor(z/16)])
        with self.assertRaises(UserError):tube_round_trip(rows,PLAYERS)

    def test_tube_flag_link_and_observed_arrival_health_are_required(self):
        for mutate in (lambda r:r[2]['players'][0].update(hypertube_native_travel=False),
                       lambda r:r[5]['tube_links'][0].update(stored_reciprocal=False),
                       lambda r:r[7]['players'][1].update(health=19)):
            rows=tube_fixture();mutate(rows)
            with self.assertRaises(UserError):tube_round_trip(rows,PLAYERS)

    def test_roster_replacement_process_restart_and_large_gaps_refuse(self):
        for mutate in (lambda r:r[4]['players'].pop(),lambda r:r[4].update(pid=9999),
                       lambda r:r[4].update(at='2026-10-28T18:20:00Z')):
            rows=tube_fixture();mutate(rows)
            with self.assertRaises(UserError):tube_round_trip(rows,PLAYERS)

    def test_duplicate_identity_and_nonfinite_positions_refuse(self):
        with self.assertRaises(UserError):tube_round_trip(tube_fixture(),[PLAYERS[0],PLAYERS[0]])
        rows=tube_fixture();rows[1]['players'][0]['position'][0]=float('nan')
        with self.assertRaises(UserError):tube_round_trip(rows,PLAYERS)


if __name__ == '__main__':
    unittest.main()
