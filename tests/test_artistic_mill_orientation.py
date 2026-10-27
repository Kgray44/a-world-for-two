import copy
import unittest

from control_room.common import UserError
from tools.artistic_mill_orientation import (
    ENTRANCES, ORIGINAL_PLAN_SHA, TUBES, check_empty_tubes, corrected_documents, encoded,
)


def fixture():
    states, entities, palette, blocks = {}, {}, [], []
    for pos in TUBES:
        if pos in ENTRANCES:
            state = 'create_hypertube:hypertube_entrance[facing='+ENTRANCES[pos][0]+',locked=false,powered=false,waterlogged=false]'
            ident, versions = 'hypertube_entrance_entity', {'Connection_version': 1}
        else:
            state = 'create_hypertube:hypertube[east_west=false,north_south=true,up_down=false,waterlogged=false]'
            ident, versions = 'hypertube_entity', {'ConnectionTo_version': 1, 'ConnectionFrom_version': 1}
        if state not in palette:
            palette.append(state)
        blocks.append([*pos, palette.index(state)])
        states[pos] = state
        entities[pos] = [{'id': 'create_hypertube:'+ident, 'x': pos[0], 'y': pos[1], 'z': pos[2], 'Speed': 0.0, **versions}]
    blocks.append([1315, 70, -1000, len(palette)])
    palette.append('minecraft:chest[facing=south,type=single,waterlogged=false]')
    plan = {'format': 'awft-native-settlement:1', 'created': 'fixture', 'seed': 'synthetic', 'world_path': 'synthetic',
            'backup_sha256': 'a'*64, 'bounds': [1315, -1000, 1331, -943], 'blocks': blocks, 'palette': palette,
            'block_entities': [{'pos': [1315, 70, -1000], 'nbt': '{Items:[{Slot:0b,id:"minecraft:wheat",count:16}]}'}],
            'commands': [], 'landmarks': [], 'validation': 'original fixture'}
    manifest = {'plan_sha256': ORIGINAL_PLAN_SHA, 'placements': len(blocks), 'preconditions': len(blocks),
                'before_sha256': 'b'*64, 'checkpoint_id': 'original', 'checkpoint_sha256': 'a'*64,
                'systems': {'hypertube': {'native_links': [{'from': list(TUBES[0]), 'from_face': 'south', 'to': list(TUBES[1]), 'to_face': 'north'}]}},
                'commands': 0, 'sources': []}
    return plan, manifest, states, entities


class MillOrientationTests(unittest.TestCase):
    def corrected(self, plan, manifest, states, entities):
        return corrected_documents(plan, manifest, {'id': 'new-fixture', 'sha256': 'c'*64}, states, entities, 'd'*64)

    def test_only_two_facings_change_all_tags_and_systems_are_preserved(self):
        plan, manifest, states, entities = fixture()
        untouched = copy.deepcopy((plan, manifest, states, entities))
        result = self.corrected(plan, manifest, states, entities)
        full = result['mill-quarter.json']
        old = {tuple(row[:3]): plan['palette'][row[3]] for row in plan['blocks']}
        new = {tuple(row[:3]): full['palette'][row[3]] for row in full['blocks']}
        self.assertEqual({pos for pos in old if old[pos] != new[pos]}, set(ENTRANCES))
        self.assertEqual(full['block_entities'], plan['block_entities'])
        self.assertEqual(result['manifest.json']['systems'], manifest['systems'])
        for name in ('native-before.json', 'entrance-facing-delta.json'):
            self.assertEqual(len(result[name]['blocks']), 2)
            self.assertEqual(result[name]['block_entities'], [])
            self.assertEqual(result[name]['commands'], [])
        self.assertEqual((plan, manifest, states, entities), untouched)
        self.assertEqual(encoded(result), encoded(self.corrected(plan, manifest, states, entities)))

    def test_any_existing_or_unknown_connection_on_any_anchor_is_preserved(self):
        for pos in TUBES:
            for key in ('Connection', 'ConnectionTo', 'ConnectionFrom', 'ForeignConnection'):
                plan, manifest, states, entities = fixture()
                entities[pos][0][key] = {}
                with self.assertRaisesRegex(UserError, 'Preserve existing'):
                    self.corrected(plan, manifest, states, entities)

    def test_wrong_native_id_duplicate_be_active_power_or_derived_state_fail(self):
        for change in ('id', 'duplicate', 'speed', 'derived'):
            plan, manifest, states, entities = fixture()
            pos = TUBES[0]
            if change == 'id': entities[pos][0]['id'] = 'foreign:entrance'
            elif change == 'duplicate': entities[pos].append(copy.deepcopy(entities[pos][0]))
            elif change == 'speed': entities[pos][0]['Speed'] = 16.0
            else: states[pos] = states[pos][:-1]+',open=true]'
            with self.assertRaises(UserError): self.corrected(plan, manifest, states, entities)

    def test_old_facing_or_manifest_binding_drift_fails(self):
        plan, manifest, states, entities = fixture()
        states[TUBES[0]] = states[TUBES[0]].replace('facing=north', 'facing=south')
        with self.assertRaisesRegex(UserError, 'state differs'):
            check_empty_tubes(plan, states, entities)
        plan, manifest, states, entities = fixture()
        manifest['plan_sha256'] = 'e'*64
        with self.assertRaisesRegex(UserError, 'binding differs'):
            self.corrected(plan, manifest, states, entities)


if __name__ == '__main__':
    unittest.main()
