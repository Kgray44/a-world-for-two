"""Portable saved-admission checks, never native/world/player acceptance."""
import unittest

from control_room.common import UserError
from tests.test_grand_harbor_fleet import registry
from tools.grand_harbor_smallcraft import SMALLCRAFT_ORDER, build
from tools.grand_harbor_smallcraft_berths import (
    AIR, WATER, CHECKPOINT, CHECKPOINT_SHA, CANDIDATES, SavedAdmissionError,
    inspect_candidate, translated, native_plan, camera_batch,
)


class Snapshot:
    def __init__(self, override=None, protected=()):
        self.override, self.protected = override or {}, set(protected)

    def state(self, pos):
        return self.override.get(pos, WATER if pos[1] < 63 else AIR)


class SmallcraftBerthTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = registry()
        cls.registry['items'] = sorted(set(cls.registry['items']) | {'minecraft:fishing_rod'})
        cls.documents = {key: build(cls.registry, key) for key in SMALLCRAFT_ORDER}

    def test_deliberate_candidate_list_is_finite_and_checkpoint_is_current(self):
        self.assertEqual(CHECKPOINT, '20261028T191243Z-6ad3a8')
        for poses in CANDIDATES.values():
            self.assertLessEqual(len(poses), 4)
            for origin, rotation, why in poses:
                self.assertEqual(origin[1], 63)
                self.assertIn(rotation, range(4))
                self.assertTrue(why)

    def test_clear_saved_source_yields_full_before_support_after_and_camera_masks(self):
        for key, doc in self.documents.items():
            origin, rotation, _ = CANDIDATES[key][0]
            field, tags, before, probe, detail = inspect_candidate(doc, self.registry, Snapshot(), origin, rotation)
            self.assertTrue(field.keys() <= before.keys())
            self.assertTrue(probe.keys() <= before.keys())
            self.assertEqual(detail['failures_by_reason'], {})
            self.assertTrue(detail['two_block_under_keel_margin'])
            plan = native_plan(self.registry, before, 'Synthetic fixture BEFORE')
            self.assertEqual(plan['backup_sha256'], CHECKPOINT_SHA)
            self.assertEqual(plan['commands'], [])
            self.assertTrue(plan['verification_only'])
            self.assertTrue(plan['construction_forbidden'])
            views = camera_batch(doc, origin, rotation)['world_views']
            self.assertTrue({'bow', 'stern', 'broadside', 'elevated', 'deck'} <= {v['name'] for v in views})

    def test_ice_marine_vegetation_structure_and_flowing_water_are_preserved(self):
        doc = self.documents['tern-pilot-cutter']
        origin, rotation, _ = CANDIDATES[doc['key']][0]
        field, _ = translated(doc, self.registry, origin, rotation)
        target = next(iter(field))
        for state in ('minecraft:ice', 'minecraft:seagrass', 'minecraft:stone', 'minecraft:water[level=1]'):
            with self.subTest(state=state), self.assertRaises(SavedAdmissionError):
                inspect_candidate(doc, self.registry, Snapshot({target: state}), origin, rotation)

    def test_missing_chunk_and_unknown_cell_are_never_air(self):
        doc = self.documents['tern-pilot-cutter']
        origin, rotation, _ = CANDIDATES[doc['key']][0]
        class Missing(Snapshot):
            def state(self, pos):
                raise UserError('No FULL saved chunk')
        with self.assertRaises(SavedAdmissionError) as result:
            inspect_candidate(doc, self.registry, Missing(), origin, rotation)
        self.assertTrue(any('unknown' in k for k in result.exception.details['failures_by_reason']))
        field, _ = translated(doc, self.registry, origin, rotation)
        with self.assertRaises(SavedAdmissionError):
            inspect_candidate(doc, self.registry, Snapshot({next(iter(field)): None}), origin, rotation)

    def test_saved_inventory_and_reserved_air_sweep_refuse_placement(self):
        doc = self.documents['salt-marigold-ketch']
        origin, rotation, _ = CANDIDATES[doc['key']][0]
        field, _ = translated(doc, self.registry, origin, rotation)
        target = next(iter(field))
        with self.assertRaises(SavedAdmissionError) as inv:
            inspect_candidate(doc, self.registry, Snapshot(protected=[target]), origin, rotation)
        self.assertIn('saved block entity must be preserved', inv.exception.details['failures_by_reason'])
        with self.assertRaises(SavedAdmissionError) as reserved:
            inspect_candidate(doc, self.registry, Snapshot(), origin, rotation, [target])
        self.assertIn('protected mask or navigation/sweep reservation', reserved.exception.details['failures_by_reason'])

    def test_selected_smallcraft_full_before_and_probe_masks_exclude_each_other(self):
        doc = self.documents['reed-fin-river-lighter']
        origin, rotation, _ = CANDIDATES[doc['key']][0]
        _, _, first, _, _ = inspect_candidate(doc, self.registry, Snapshot(), origin, rotation)
        with self.assertRaises(SavedAdmissionError):
            inspect_candidate(doc, self.registry, Snapshot(), origin, rotation, first)

    def test_water_probe_is_strict_and_does_not_allow_air_below_keel(self):
        doc = self.documents['tern-pilot-cutter']
        origin, rotation, _ = CANDIDATES[doc['key']][0]
        _, _, _, probe, _ = inspect_candidate(doc, self.registry, Snapshot(), origin, rotation)
        target = next(p for p, state in probe.items() if state == WATER)
        with self.assertRaises(SavedAdmissionError) as result:
            inspect_candidate(doc, self.registry, Snapshot({target: AIR}), origin, rotation)
        self.assertIn('exact water/air support probe differs', result.exception.details['failures_by_reason'])


if __name__ == '__main__':
    unittest.main()
