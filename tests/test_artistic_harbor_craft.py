"""Synthetic admission fixtures never qualify a native craft or a player test."""
from copy import deepcopy
import unittest
import uuid

from control_room.common import UserError
from tools.artistic_harbor_craft import (AIR, NOTCH, TENDER_POSITION, admit, boat_box,
                                         proposal, sha)


def fixture():
    blocks = {key: {} for key in (AIR, 'minecraft:spruce_planks', 'chipped:nailed_dark_oak_planks',
                                  'chipped:detailed_dark_oak_planks', 'minecraft:dark_oak_fence')}
    blocks.update({'minecraft:water': {'level': ['0']},
                   'minecraft:barrel': {'facing': ['south'], 'open': ['false']},
                   'minecraft:stripped_dark_oak_log': {'axis': ['y']},
                   'minecraft:dark_oak_log': {'axis': ['z']},
                   'minecraft:ladder': {'facing': ['west'], 'waterlogged': ['true', 'false']},
                   'minecraft:lantern': {'hanging': ['false'], 'waterlogged': ['false']}})
    registry = {'blocks': blocks, 'entities': ['smallships:cog', 'smallships:ship_part', 'minecraft:boat'],
                'seed': 'synthetic', 'world_path': 'synthetic-world'}
    survey = {'report': {'status': 'complete', 'failures': 0},
              'samples': [{'x': x, 'z': z, 'fluid': True, 'block': 'minecraft:water', 'y': 63,
                           'ground_y': 55, 'ocean_floor_y': 55, 'block_entities': [],
                           'source': 'actual generated native chunk surface'}
                          for x in range(1184, 1209, 4) for z in range(-1284, -1247, 4)]}
    previous = {**NOTCH, (1201, 64, -1260): 'minecraft:spruce_planks',
                (1197, 64, -1253): 'minecraft:spruce_planks'}
    palette = sorted(set(previous.values()))
    plan = {'format': 'awft-native-settlement:1', 'seed': 'synthetic', 'world_path': 'synthetic-world',
            'palette': palette, 'blocks': [[*pos, palette.index(state)] for pos, state in previous.items()],
            'commands': [], 'block_entities': []}
    return registry, survey, plan


class ArtisticHarborCraft(unittest.TestCase):
    def setUp(self):
        self.registry, self.survey, self.previous = fixture()
        self.data, self.before, self.clearance = proposal(self.registry, self.survey, self.previous, 'a'*64)
        self.contract = self.data['admission']

    def observations(self, phase='cog-create'):
        contract = self.contract
        selected = contract['requests']['smallships:cog' if phase.startswith('cog-') else 'minecraft:boat']
        snapshot = {'format': 'awft-native-artistic-craft-occupancy:1', 'game_time': 50,
                    'contract_sha256': sha(contract), 'world_binding': contract['world_binding'],
                    'dimension': 'minecraft:overworld', 'all_target_chunks_entity_ready': True,
                    'regions_scanned': contract['phases'][phase], 'entities': []}
        blocks = {'format': 'awft-native-artistic-craft-blocks:1', 'game_time': 50,
                  'status': 'complete', 'operation': 'verify', 'all_target_chunks_full': True,
                  'failures': 0, 'sha256': contract['required_water_air_sha256'],
                  'world_binding': contract['world_binding']}
        custody = {'format': 'awft-native-artistic-craft-custody:1', 'game_time': 50,
                   'world_binding': contract['world_binding'], 'loaded_and_persistent_entity_storage_complete': True,
                   'uuid': selected, 'matches': 0 if phase.endswith('-create') else 1}
        return snapshot, blocks, custody

    def test_genuine_entities_are_typed_requests_not_commands(self):
        self.assertEqual(self.data['physical_plan']['commands'], [])
        self.assertEqual(self.before['commands'], [])
        self.assertEqual(self.clearance['commands'], [])
        requests = self.data['entity_requests']
        self.assertEqual([row['entity'] for row in requests], ['smallships:cog', 'minecraft:boat'])
        self.assertIn('Sail:{State:0b,Color:"white",SailHealth:100f}', requests[0]['nbt_snbt'])
        self.assertIn('locked:0b,Items:[]', requests[0]['nbt_snbt'])
        self.assertNotIn('Invulnerable', requests[0]['nbt_snbt'])
        self.assertEqual(sha(self.clearance), self.contract['required_water_air_sha256'])
        self.assertEqual(len({row['uuid'] for row in requests}), 2)

    def test_only_reviewed_old_deck_cells_change(self):
        result = self.data['physical_plan']
        blocks = {(x, y, z): result['palette'][i] for x, y, z, i in result['blocks']}
        self.assertEqual({pos: blocks[pos] for pos in NOTCH}, {pos: AIR for pos in NOTCH})
        previous = {(x, y, z) for x, y, z, i in self.previous['blocks']}
        self.assertEqual(previous & blocks.keys(), NOTCH.keys())
        self.assertIn((1199, 64, -1262), blocks)
        self.assertIn((1196, 64, -1253), blocks)
        self.assertEqual(self.data['native_world_mutations'], 0)

    def test_changed_corner_and_protected_inventory_refuse(self):
        changed = deepcopy(self.previous)
        changed['palette'][changed['palette'].index('minecraft:spruce_planks')] = 'minecraft:barrel'
        with self.assertRaises(UserError):
            proposal(self.registry, self.survey, changed, 'a'*64)
        protected = deepcopy(self.previous)
        protected['block_entities'] = [{'pos': [1200, 65, -1261], 'nbt': '{}'}]
        with self.assertRaisesRegex(UserError, 'block entity'):
            proposal(self.registry, self.survey, protected, 'a'*64)

    def test_shallows_and_missing_departure_soundings_refuse(self):
        for kind in ('shallow', 'missing'):
            changed = deepcopy(self.survey)
            if kind == 'shallow':
                for row in changed['samples']:
                    row['ocean_floor_y'] = 62
            else:
                changed['samples'] = [row for row in changed['samples'] if row['z'] >= -1276]
            with self.assertRaises(UserError):
                proposal(self.registry, changed, self.previous, 'a'*64)

    def test_wrong_world_unknown_entity_and_native_id_refuse(self):
        other = deepcopy(self.previous)
        other['world_path'] = 'other-world'
        with self.assertRaises(UserError):
            proposal(self.registry, self.survey, other, 'a'*64)
        native = deepcopy(self.registry)
        native['entities'].remove('smallships:cog')
        with self.assertRaises(UserError):
            proposal(native, self.survey, self.previous, 'a'*64)

    def test_empty_complete_same_tick_fixture_can_pass(self):
        s, b, c = self.observations()
        self.assertEqual(admit(self.contract, s, b, c, 'cog-create', 50)['game_time'], 50)

    def test_each_freshness_identity_and_coverage_gate_is_required(self):
        for target, key, value in ((0, 'game_time', 49), (0, 'world_binding', 'wrong'),
                                    (0, 'contract_sha256', 'wrong'), (0, 'regions_scanned', ['cog-berth']),
                                    (0, 'all_target_chunks_entity_ready', False), (1, 'game_time', 49),
                                    (1, 'sha256', 'wrong'), (1, 'failures', 1), (1, 'operation', 'place'),
                                    (2, 'game_time', 49), (2, 'matches', 1),
                                    (2, 'loaded_and_persistent_entity_storage_complete', False)):
            with self.subTest(key=key, target=target):
                values = list(self.observations())
                values[target][key] = value
                with self.assertRaises(UserError):
                    admit(self.contract, *values, 'cog-create', 50)

    def test_pets_items_and_boats_block_even_with_empty_uuid_custody(self):
        for kind in ('minecraft:wolf', 'minecraft:item', 'minecraft:boat', 'smallships:cog'):
            s, b, c = self.observations()
            s['entities'] = [{'entity': kind, 'uuid': str(uuid.uuid4()),
                              'bounds': [1196, 63, -1265, 1197, 64, -1264]}]
            with self.subTest(kind=kind), self.assertRaises(UserError):
                admit(self.contract, s, b, c, 'cog-create', 50)

    def test_departure_requires_actual_cog_and_only_native_multipart_children(self):
        s, b, c = self.observations('cog-depart')
        with self.assertRaises(UserError):
            admit(self.contract, s, b, c, 'cog-depart', 50)
        entity = {'entity': 'smallships:cog', 'uuid': c['uuid'], 'bounds': [1196, 63, -1265, 1197, 64, -1264]}
        s['entities'] = [entity, {'entity': 'smallships:ship_part', 'uuid': str(uuid.uuid4()),
                                 'native_parent_uuid': c['uuid'], 'bounds': entity['bounds']}]
        admit(self.contract, s, b, c, 'cog-depart', 50)
        s['entities'][1]['entity'] = 'minecraft:wolf'
        with self.assertRaises(UserError):
            admit(self.contract, s, b, c, 'cog-depart', 50)

    def test_actual_boat_dimensions_and_separate_tender_departure(self):
        box = boat_box()
        self.assertAlmostEqual(box[3]-box[0], 1.375)
        self.assertAlmostEqual(box[4]-box[1], .5625)
        self.assertEqual(self.data['entity_requests'][1]['position'], list(TENDER_POSITION))
        s, b, c = self.observations('tender-depart')
        s['entities'] = [{'entity': 'minecraft:boat', 'uuid': c['uuid'], 'bounds': list(box)}]
        admit(self.contract, s, b, c, 'tender-depart', 50)
        s['entities'].append({'entity': 'minecraft:item', 'uuid': str(uuid.uuid4()), 'bounds': list(box)})
        with self.assertRaises(UserError):
            admit(self.contract, s, b, c, 'tender-depart', 50)


if __name__ == '__main__':
    unittest.main()
