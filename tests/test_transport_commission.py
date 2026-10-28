"""Synthetic arithmetic/custody checks; these do not qualify Minecraft gameplay."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import importlib.util
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from unittest.mock import Mock

from control_room.common import Layout, REPO, UserError, write_json
from tools.transport_commission import (
    FORMAT, ROLES, construction_contract, read_observation,
    reconcile_logistics, reconcile_restart,
)
from tools.transport_saved_inputs import _inventory, complete_body, verification_plan
from tools.transport_chain_bind import native_terminal


def item(name, count, slot=0, *, components='{}', plain=True):
    return {'slot': slot, 'item': name, 'count': count, 'components': components, 'plain': plain}


def observation():
    stores = [{'role': role, 'available': True, 'items': []} for role in sorted(ROLES)]
    result = {'format': FORMAT, 'at': '2026-10-28T18:00:00Z', 'boot_id': 'synthetic-boot-a',
              'candidate': '0.1.0-candidate.50', 'bridge': '0.6.36', 'world': 'synthetic-fixture-world',
              'game_time': 100, 'world_mutated': False, 'owned_tickets': 0, 'players': [],
              'pid':1234,'process_started':'2026-10-28T17:00:00Z',
              'cargo': {'scope': 'copper_wren_fixed_v1', 'complete': True,
                        'dropped_query_complete': True, 'aliased_transit_objects': False,
                        'stores': stores, 'dropped': [], 'extractor_filter': {'item': 'create:wheat_flour'}}}
    store(result, 'starter')['items'] = [item('minecraft:wheat',16), item('minecraft:iron_ingot',4,1),
                                       item('create:wrench',1,2,components='{damage:4}',plain=False)]
    return result


def store(snapshot, role):
    return next(row for row in snapshot['cargo']['stores'] if row['role'] == role)


def processed(flour=24, seeds=3):
    result = observation()
    result.update(at='2026-10-28T18:01:00Z', game_time=1300)
    store(result,'starter')['items'] = [item('minecraft:iron_ingot',3,1),
                                       item('create:wrench',1,2,components='{damage:4}',plain=False)]
    store(result,'dispatch')['items'] = [item('create:wheat_flour',flour)]
    store(result,'depot')['items'] = [item('create:iron_sheet',1)]
    store(result,'mill_output')['items'] = [item('minecraft:wheat_seeds',seeds)] if seeds else []
    return result


def persisted():
    result = processed()
    result['track_graph'] = {'status':'station_nodes_connected'}
    result['stations'] = [{'position':[1332,71,-994],'name':'Copper Wren Mill','present_train':'train-fixture','station_point':True,'valid_track':True,'station_uuid':'station-fixture-1'},
                          {'position':[1332,71,-942],'name':'Rosewater Orchard Halt','present_train':None,'station_point':True,'valid_track':True,'station_uuid':'station-fixture-2'}]
    result['trains'] = [{'uuid':'train-fixture','graph_id':'graph-fixture','carriages':1,'seats':[5],
                         'double_ended':True,'schedule_present':True,'schedule_cyclic':False,
                         'invalid':False,'derailed':False,'speed':0,'forward_conductor':True,'backward_conductor':True,
                         'schedule_entry':2,'schedule_paused':True,'schedule_completed':True,'native_schedule_snbt':'synthetic-schedule',
                         'schedule_condition_progress':[],'schedule_condition_context':[]}]
    result['tube_links'] = [{'uuid':f'synthetic-{n}','from':[1331,71,-991+8*n],
                             'to':[1331,71,-983+8*n],'distance':8,'stored_reciprocal':True} for n in range(6)]
    return result


class TransportArithmeticTests(unittest.TestCase):
    def test_real_recipe_variation_not_a_fixed_fictitious_yield(self):
        for flour, seeds in ((16,0),(24,3),(48,16)):
            self.assertTrue(reconcile_logistics(observation(),processed(flour,seeds))['passed'])

    def test_duplicate_product_or_impossible_stochastic_yield_fails(self):
        for flour, seeds in ((15,0),(17,0),(50,3),(24,17)):
            self.assertFalse(reconcile_logistics(observation(),processed(flour,seeds))['passed'])
        after = processed()
        store(after,'depot')['items'][0]['count'] = 2
        self.assertFalse(reconcile_logistics(observation(),after)['passed'])

    def test_unrelated_components_and_counts_are_conserved(self):
        after = processed()
        store(after,'starter')['items'][1]['components'] = '{damage:0}'
        self.assertFalse(reconcile_logistics(observation(),after)['passed'])

    def test_a_moving_or_lost_item_cannot_pass_from_output_count_alone(self):
        after = processed()
        store(after,'chute')['items'] = [item('minecraft:wheat',1)]
        self.assertFalse(reconcile_logistics(observation(),after)['passed'])
        after = processed()
        next(row for row in after['cargo']['stores'] if row['role'].startswith('tube:'))['in_transit'] = True
        self.assertFalse(reconcile_logistics(observation(),after)['passed'])
        after = processed()
        store(after,'mill_output')['items'].append(item('create:wheat_flour',2,1))
        self.assertFalse(reconcile_logistics(observation(),after)['passed'])

    def test_missing_duplicate_and_aliased_scope_refuses(self):
        for mutation in ('missing','duplicate','alias','unloaded'):
            after = processed()
            if mutation == 'missing':after['cargo']['stores'].pop()
            if mutation == 'duplicate':after['cargo']['stores'][-1] = deepcopy(after['cargo']['stores'][0])
            if mutation == 'alias':after['cargo']['aliased_transit_objects'] = True
            if mutation == 'unloaded':after['cargo']['dropped_query_complete'] = False
            with self.assertRaises(UserError):reconcile_logistics(observation(),after)

    def test_player_external_transfer_window_and_identity_changes_refuse(self):
        for field, value in (('players',[{'name':'fixture-player'}]),('world','another-world'),
                             ('boot_id','another-jvm'),('at','2026-10-28T18:00:00Z')):
            after = processed();after[field] = value
            with self.assertRaises(UserError):reconcile_logistics(observation(),after)

    def test_filter_template_is_not_counted_as_goods(self):
        before,after = observation(),processed()
        before['cargo']['extractor_filter']['count'] = 1
        after['cargo']['extractor_filter']['count'] = 1
        audit = reconcile_logistics(before,after)
        self.assertEqual(audit['actual_dispatch_flour_delta'],24)
        self.assertEqual(audit['actual_item_deltas']['create:wheat_flour'],24)

    def test_nonplain_recipe_inputs_require_separate_contract(self):
        before = observation();store(before,'starter')['items'][0]['plain'] = False
        with self.assertRaises(UserError):reconcile_logistics(before,processed())

    def test_dropped_inventory_prevents_a_no_loss_claim(self):
        after = processed();after['cargo']['dropped'] = [{'entity_uuid':'synthetic-drop','items':[item('minecraft:stone',1)]}]
        self.assertFalse(reconcile_logistics(observation(),after)['passed'])


class TransportPersistenceTests(unittest.TestCase):
    def test_new_session_preserves_native_ids_and_inventory_totals(self):
        before = persisted();after = deepcopy(before)
        after.update(boot_id='synthetic-boot-b',at='2026-10-28T18:02:00Z',game_time=1320,pid=5678,process_started='2026-10-28T18:01:30Z')
        self.assertTrue(reconcile_restart(before,after)['passed'])

    def test_saving_twice_in_one_jvm_is_not_restart_evidence(self):
        before = persisted();after = deepcopy(before);after['at'] = '2026-10-28T18:02:00Z'
        with self.assertRaises(UserError):reconcile_restart(before,after)

    def test_missing_link_or_recreated_train_cannot_pass(self):
        before = persisted();after = deepcopy(before)
        after.update(boot_id='synthetic-boot-b',at='2026-10-28T18:02:00Z',pid=5678,process_started='2026-10-28T18:01:30Z')
        after['trains'][0]['uuid'] = 'replacement'
        self.assertFalse(reconcile_restart(before,after)['passed'])
        after['tube_links'].pop()
        with self.assertRaises(UserError):reconcile_restart(before,after)

    def test_relabelled_session_or_duplicate_uuid_cannot_prove_restart(self):
        before=persisted();after=deepcopy(before)
        after.update(boot_id='synthetic-boot-b',at='2026-10-28T18:02:00Z')
        with self.assertRaises(UserError):reconcile_restart(before,after)
        after.update(pid=5678,process_started='2026-10-28T18:01:30Z')
        after['tube_links'][1]['uuid']=after['tube_links'][0]['uuid']
        with self.assertRaises(UserError):reconcile_restart(before,after)

    def test_changed_schedule_conductors_and_null_graph_fail_parked_restart(self):
        for field,value in [('schedule_entry',99),('forward_conductor',False),('native_schedule_snbt','changed'),('graph_id',None)]:
            before=persisted();after=deepcopy(before)
            after.update(boot_id='synthetic-boot-b',at='2026-10-28T18:02:00Z',pid=5678,process_started='2026-10-28T18:01:30Z')
            after['trains'][0][field]=value
            self.assertFalse(reconcile_restart(before,after)['passed'])


class TransportCustodyTests(unittest.TestCase):
    def test_chain_binding_only_accepts_canonical_owned_native_terminals(self):
        with tempfile.TemporaryDirectory()as folder:
            home=Path(folder).resolve();native=home/'dashboard/settlement';native.mkdir(parents=True)
            good=native/'settlement-result-12345678-abcd-abcd-abcd-1234567890ab.json';good.write_text('{}')
            self.assertEqual(native_terminal(home,good),good)
            copied=home/good.name;copied.write_text('{}')
            with self.assertRaises(UserError):native_terminal(home,copied)
            renamed=native/'invented-native-proof.json';renamed.write_text('{}')
            with self.assertRaises(UserError):native_terminal(home,renamed)

    def test_chain_binding_refuses_non_json_empty_terminal(self):
        with tempfile.TemporaryDirectory()as folder:
            home=Path(folder).resolve();native=home/'dashboard/settlement';native.mkdir(parents=True)
            good=native/'settlement-result-12345678-abcd-abcd-abcd-1234567890ab.json';good.write_bytes(b'')
            with self.assertRaises(UserError):native_terminal(home,good)

    def test_marker_tamper_and_duplicate_json_keys_are_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'observation.json';raw=json.dumps(observation()).encode();path.write_bytes(raw)
            marker=Path(str(path)+'.complete');marker.write_text(hashlib.sha256(raw).hexdigest())
            self.assertEqual(read_observation(path)[0]['format'],FORMAT)
            path.write_bytes(raw+b' ')
            with self.assertRaises(UserError):read_observation(path)
            raw=b'{"format":"a","format":"b"}';path.write_bytes(raw);marker.write_text(hashlib.sha256(raw).hexdigest())
            with self.assertRaises(UserError):read_observation(path)

    def test_both_conductor_seats_fit_inside_existing_carriage(self):
        plan=construction_contract();self.assertFalse(plan['world_write_authority'])
        railway=plan['railway'];changes=railway['conductor_overlay']
        controls={tuple(row['position']):row['proposed_facing'] for row in changes if 'proposed_facing'in row}
        seats=[tuple(row['position']) for row in changes if row.get('proposed_block')=='create:blue_seat']
        for seat in seats:
            control=next(p for p in controls if abs(p[2]-seat[2])==1)
            self.assertEqual(controls[control],'south' if control[2]<seat[2] else 'north')
            self.assertTrue(1335<=seat[0]<=1337 and 70<=seat[1]<=75 and -993<=seat[2]<=-985)
        self.assertEqual(len(railway['retained_passenger_seats']),3)
        self.assertTrue(all(value=='PENDING' for value in plan['acceptance'].values()))

    def test_verification_plans_refuse_generic_placement(self):
        registry={'seed':'synthetic','world_path':'synthetic'}
        plan=verification_plan(registry,{(1,2,3):'minecraft:air'},'0'*64,'test')
        self.assertTrue(plan['construction_forbidden']);self.assertTrue(plan['verification_only'])
        self.assertEqual(plan['block_entities'],[]);self.assertEqual(plan['commands'],[])

    def test_unknown_or_blocked_body_never_emits_a_smaller_clearance_plan(self):
        body=set(range(5607));clear={'body':body,'blocked':[],'unknown':[],'frame_intersections':[]}
        self.assertTrue(complete_body(body,clear,clear))
        for field,value in [('body',set(range(5606))),('blocked',[{'position':[1,2,3]}]),('unknown',[[1,2,3]]),('frame_intersections',[(1,2,3)])]:
            changed=deepcopy(clear);changed[field]=value
            self.assertFalse(complete_body(body,clear,changed))

    def test_saved_inventory_preserves_components_and_does_not_treat_loot_as_empty(self):
        terrain=SimpleNamespace(state=lambda *p:'minecraft:chest',snapshot=SimpleNamespace(regions={(2,-2):b'fixture'}))
        chest={'id':'minecraft:chest','x':1313,'y':68,'z':-994,
               'Items':[{'Slot':2,'id':'create:wrench','count':1,'components':{'minecraft:damage':4}}]}
        with patch('tools.transport_saved_inputs.chunk_document',return_value=({'block_entities':[chest]},'a'*64)):
            value=_inventory(terrain,(1313,68,-994),'minecraft:chest')
            self.assertEqual(len(value['slots']),27)
            self.assertEqual(value['slots'][2]['saved_item_nbt']['components'],{'minecraft:damage':4})
            self.assertIsNone(value['slots'][3]['saved_item_nbt'])
            chest['LootTable']='fixture:unresolved'
            with self.assertRaises(UserError):_inventory(terrain,(1313,68,-994),'minecraft:chest')


class TransportConsoleProposalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path=REPO/'compat/control-bridge/proposals/transport-commission-r1/console_revision.py'
        spec=importlib.util.spec_from_file_location('transport_console_revision',path)
        cls.revision=importlib.util.module_from_spec(spec);spec.loader.exec_module(cls.revision)
        source=(REPO/'control_room/server.py').read_text(encoding='utf8')
        revised=source if 'awftmill (inspect|resume) mill-resume-'in source else cls.revision.server_revision(source)
        namespace={'__name__':'control_room.transport_proposal','__package__':'control_room'}
        exec(compile(revised,'<transport-console-proposal>','exec'),namespace)
        cls.proposed_server=namespace['Server']

    def test_private_resume_correct_bundle_confirmation_and_inspection(self):
        with tempfile.TemporaryDirectory()as folder:
            layout=Layout(Path(folder));layout.create()
            layout.save_settings({'permanent_world':False,'port':25575})
            write_json(layout.state/'artistic-owner.json',{'format':'awft-artistic-stage:1','home':str(layout.home)})
            server=self.proposed_server.__new__(self.proposed_server);server.layout=layout;server._write=Mock()
            resume='awftmill resume mill-resume-'+'e'*16+' '+'e'*64
            with self.assertRaises(UserError):server.command(resume)
            server.command(resume,confirmed=True)
            server.command(resume.replace(' resume ',' inspect '))
            self.assertEqual(server._write.call_count,2)
            for bad in (resume.replace('mill-resume-','mill-commission-'),resume+' extra',resume+'\nstop',
                        resume.replace(' resume ',' commission '),resume.replace('mill-resume-','../')):
                with self.assertRaises(UserError):server.command(bad,confirmed=True)
            for settings in ({'permanent_world':True,'port':25575},{'permanent_world':False,'port':25565}):
                layout.save_settings(settings)
                with self.assertRaises(UserError):server.command(resume,confirmed=True)
                with self.assertRaises(UserError):server.command(resume.replace(' resume ',' inspect '))

    def test_proposal_refuses_changed_context_and_updates_existing_safety_fixtures(self):
        with self.assertRaises(ValueError):self.revision.server_revision('unrelated source')
        source=(REPO/'tests/test_safety.py').read_text(encoding='utf8')
        revised=source if 'def test_retained_mill_resume_requires_confirmation_and_typed_bundle'in source else self.revision.tests_revision(source)
        compile(revised,'<transport-proposed-safety-tests>','exec')
        self.assertIn('test_retained_mill_resume_requires_confirmation_and_typed_bundle',revised)


if __name__=='__main__':unittest.main()
