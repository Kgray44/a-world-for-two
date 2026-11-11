"""Source-only rail partition and destructive-placement refusal tests."""
from copy import deepcopy
import unittest

from control_room.common import UserError
from tools import transport_rail_only as rail
from tools.artistic_bridge_refinement import flatten


def fixture():
    states = {p: rail.AIR for p in rail.TARGETS}
    states.update({p: 'railways:track_spruce[shape=zo,turn=false,waterlogged=false]' for p in rail.TRACKS})
    states.update({p: rail.BOGEY for p in rail.OLD_BOGEYS})
    states.update({p: 'create:blue_seat[waterlogged=false]' for p in rail.SEATS})
    for p, facing in zip(rail.CONTROLS, ('north', 'south')):
        states[p] = f'create:controls[facing={facing},open=false,virtual=false,waterlogged=false]'
    for p in (rail.MILL, rail.HALT):
        states[p] = 'create:track_station[assembling=false,waterlogged=false]'
    return states


class RailOnlySourceTests(unittest.TestCase):
    def setUp(self):
        self.registry = {'seed': 7, 'world_path': 'D:/source-fixture/world/RosewaterArtistic'}
        self.states = fixture()

    def derive(self, states=None):
        return rail.derive(self.registry, self.states if states is None else states, 'a' * 64)

    def test_closed_masks_exclude_human_tubes_mill_stock_and_power(self):
        self.assertEqual(len(rail.TARGETS), 495)
        self.assertEqual(len(rail.SHELL), 440)
        self.assertTrue(all(p[0] >= 1332 for p in rail.TARGETS))
        for p in ((1331, 71, -991), (1331, 71, -943), (1330, 71, -991),
                  (1313, 68, -994), (1310, 70, -999)):
            self.assertNotIn(p, rail.TARGETS)
        extra = dict(self.states)
        extra[(1331, 71, -991)] = 'minecraft:air'
        with self.assertRaises(UserError):
            self.derive(extra)

    def test_two_bogey_repair_preserves_station_targets_and_requires_zero_front(self):
        docs = self.derive()
        repair = flatten(docs['bogey-repair-after-GUI-VERIFY-ONLY.json'])
        self.assertEqual(set(repair), set(rail.OLD_BOGEYS + rail.NEW_BOGEYS))
        self.assertTrue(all(repair[p] == rail.AIR for p in rail.OLD_BOGEYS))
        self.assertTrue(all(repair[p] == rail.BOGEY for p in rail.NEW_BOGEYS))
        card = docs['native-GUI-repair.json']
        self.assertEqual(card['source_original_native_scanner_offsets'], [1, 7])
        self.assertEqual(card['corrected_native_scanner_offsets'], [0, 6])
        self.assertFalse(card['assembly']['station_target_or_UUID_changed'])

    def test_occupied_new_bogey_or_burner_refuses_instead_of_destroying(self):
        for p in rail.NEW_BOGEYS + rail.BURNERS:
            with self.subTest(p=p):
                actual = deepcopy(self.states)
                actual[p] = 'minecraft:chest[facing=north,type=single,waterlogged=false]'
                with self.assertRaises(UserError):
                    self.derive(actual)

    def test_changed_human_control_or_bogey_is_held(self):
        for p, state in ((rail.CONTROLS[0], 'create:controls[facing=west]'),
                         (rail.OLD_BOGEYS[0], 'create:large_bogey[axis=z,waterlogged=false]')):
            actual = dict(self.states)
            actual[p] = state
            with self.assertRaises(UserError):
                self.derive(actual)

    def test_extended_or_broken_track_needs_new_native_scope(self):
        for p, state in ((min(rail.ENDS), 'railways:track_spruce[shape=zo,turn=false,waterlogged=false]'),
                         (min(rail.TRACKS), rail.AIR)):
            actual = dict(self.states)
            actual[p] = state
            with self.assertRaises(UserError):
                self.derive(actual)

    def test_every_geometry_file_forbids_placement_and_nbt_replay(self):
        docs = self.derive()
        for name, plan in docs.items():
            if name.endswith('VERIFY-ONLY.json'):
                self.assertTrue(plan['construction_forbidden'])
                self.assertTrue(plan['verification_only'])
                self.assertEqual(plan['commands'], [])
                self.assertEqual(plan['block_entities'], [])
        card = docs['native-GUI-repair.json']
        self.assertFalse(card['world_write_authority'])
        self.assertFalse(card['live_human_editing_authorized'])
        self.assertFalse(card['native_block_entity_NBT_replay'])
        self.assertEqual(card['world_writes'], 0)
        self.assertTrue(card['material_custody']['global_loot_modifiers_and_actual_counts_require_observation'])

    def test_station_and_seat_changes_are_not_normalized(self):
        for p in (rail.MILL, rail.HALT, rail.SEATS[0]):
            actual = dict(self.states)
            actual[p] = rail.AIR
            with self.assertRaises(UserError):
                self.derive(actual)

    def test_ready_proposal_changes_only_approved_eight_cells_and_ui_mode(self):
        ready = flatten(self.derive()['assembly-ready-after-GUI-VERIFY-ONLY.json'])
        changed = {p for p, state in ready.items() if state != self.states[p]}
        self.assertEqual(changed, set(rail.OLD_BOGEYS + rail.NEW_BOGEYS + rail.CONTROLS + rail.BURNERS) | {rail.MILL})
        self.assertTrue(all(ready[p] == self.states[p] for p in rail.SEATS))


if __name__ == '__main__':
    unittest.main()
