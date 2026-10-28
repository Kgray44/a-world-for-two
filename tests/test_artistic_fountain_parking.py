"""Saved-state/request admission only; no fluid or piston simulation."""
import datetime as dt
import unittest
from control_room.common import UserError
from tools import artistic_fountain_parking as gate

NOW=dt.datetime(2026,10,28,tzinfo=dt.timezone.utc)


def observed(kind='ALREADY_PARKED'):
    rows={p:'minecraft:air' for p in gate.POSITIONS}
    rows[gate.INTAKE]='create:fluid_pipe[down=true,east=false,north=false,south=false,up=true,waterlogged=true,west=false]'
    rows[gate.WHEEL]='create:water_wheel[facing=west,waterlogged=false]'
    rows[gate.PUMP]='create:mechanical_pump[facing=east,waterlogged=false]'
    on=kind=='STABLE_ON';flag=str(on).lower()
    rows[gate.STOP_LEVER]='minecraft:lever[face=wall,facing=east,powered='+flag+']'
    rows[gate.PISTON]='minecraft:sticky_piston[extended='+flag+',facing=north]'
    rows[gate.DIODE]='minecraft:repeater[delay=1,facing=south,locked=false,powered='+flag+']'
    rows[gate.PLUG_OPEN]=('minecraft:chiseled_quartz_block' if kind=='ALREADY_PARKED' else
                          'minecraft:piston_head[facing=north,short=false,type=sticky]' if on else 'minecraft:air')
    rows[gate.OUTLET]='minecraft:air' if kind=='ALREADY_PARKED' else 'minecraft:chiseled_quartz_block'
    return rows


def proof():
    return {'operation':'verify','status':gate.STATUS,'plan_sha256':'a'*64,'blocks':14,
            'cleanup_required':False,'failures':0,'temporary_tickets_remaining':0,'pending_shared_chunk_futures':0,
            'started':(NOW-dt.timedelta(seconds=2)).isoformat(),'finished':(NOW-dt.timedelta(seconds=1)).isoformat()}


class FountainParkingTests(unittest.TestCase):
    def test_three_coherent_saved_baselines_are_distinguished(self):
        for kind in ('ALREADY_PARKED','DETACHED_PLUG','STABLE_ON'):
            with self.subTest(kind=kind):self.assertEqual(gate.classify(observed(kind)),kind)

    def test_wet_sources_jets_and_lost_intake_refuse_any_parking(self):
        for pos in (gate.HEADER,gate.WHEEL_SOURCE,*gate.JET_WITNESSES):
            rows=observed();rows[pos]='minecraft:water[level=0]'
            with self.subTest(pos=pos),self.assertRaises(UserError):gate.classify(rows)
        rows=observed();rows[gate.INTAKE]='minecraft:air'
        with self.assertRaises(UserError):gate.classify(rows)

    def test_moving_or_unknown_plug_is_not_silently_replaced(self):
        for value in ('minecraft:moving_piston[facing=north,type=sticky]','minecraft:stone',
                      'minecraft:piston_head[facing=south,short=false,type=sticky]'):
            rows=observed('STABLE_ON');rows[gate.PLUG_OPEN]=value
            with self.subTest(value=value),self.assertRaises(UserError):gate.classify(rows)

    def test_orientations_locked_controls_and_transient_state_are_not_admitted(self):
        for pos,value in ((gate.WHEEL,'create:water_wheel[facing=east,waterlogged=false]'),
                          (gate.PUMP,'create:mechanical_pump[facing=west,waterlogged=false]'),
                          (gate.STOP_LEVER,'minecraft:lever[face=floor,facing=east,powered=false]'),
                          (gate.DIODE,'minecraft:repeater[delay=1,facing=south,locked=true,powered=false]'),
                          (gate.DIODE,'minecraft:repeater[delay=1,facing=south,locked=false,powered=true]')):
            rows=observed();rows[pos]=value
            with self.subTest(pos=pos,value=value),self.assertRaises(UserError):gate.classify(rows)
        rows=observed('STABLE_ON');rows[gate.PISTON]='minecraft:sticky_piston[extended=false,facing=north]'
        with self.assertRaises(UserError):gate.classify(rows)

    def test_unknown_or_duplicate_coverage_cannot_supply_the_before_field(self):
        rows=observed();rows.pop(gate.WHEEL)
        with self.assertRaises(UserError):gate.classify(rows)
        rows=observed();rows[(0,0,0)]='minecraft:air'
        with self.assertRaises(UserError):gate.classify(rows)

    def test_only_a_fresh_complete_native_journal_result_can_bind_a_request(self):
        gate.check_proof(proof(),'a'*64,NOW)
        for field,value in (('operation','place'),('blocks',13),('blocks',True),('plan_sha256','b'*64),
                            ('failures',1),('failures',False),('cleanup_required',True),
                            ('temporary_tickets_remaining',1),('pending_shared_chunk_futures',1),('error',None),
                            ('finished',(NOW-dt.timedelta(minutes=31)).isoformat())):
            record=proof();record[field]=value
            with self.subTest(field=field),self.assertRaises(UserError):gate.check_proof(record,'a'*64,NOW)
