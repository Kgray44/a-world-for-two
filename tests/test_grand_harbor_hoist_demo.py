"""Source-only hoist refusal/dependency tests. No simulated success or game test."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from control_room.common import UserError
from tests.test_grand_harbor_fleet import registry
from tools.grand_harbor_fleet import build
from tools.grand_harbor_berth import native_plan, probe_cells, translated, rotate_point
from tools.grand_harbor_hoist_demo import (
    AIR, CHECKPOINT, CHECKPOINT_SHA, ORIGIN, ROTATION, LOAD, build_request, inspect_create, states,
)


class Snapshot:
    def __init__(self, overrides=None, protected=()):
        self.overrides, self.protected = overrides or {}, set(protected)

    def state(self, pos):
        return self.overrides.get(pos, AIR)


class HoistDemoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = registry()
        cls.template = build(cls.registry, 'resolute-wren')
        field, tags = translated(cls.template, cls.registry, ORIGIN, ROTATION)
        water, air, _ = probe_cells(cls.template)
        field.update({rotate_point(p, ORIGIN, ROTATION): 'minecraft:water[level=0]' for p in water})
        field.update({rotate_point(p, ORIGIN, ROTATION): AIR for p in air})
        cls.after = native_plan(cls.registry, field, 'Prospective fixture Wren AFTER', tags=tags)
        cls.receipt = {'id': CHECKPOINT, 'sha256': CHECKPOINT_SHA, 'verified': True}

    def request(self, **kwargs):
        return build_request(kwargs.get('registry', self.registry), kwargs.get('snapshot', Snapshot()),
                             kwargs.get('receipt', self.receipt), kwargs.get('template', self.template), kwargs.get('old_after', self.after))

    def test_one_ordinary_block_request_is_blocked_and_nonexecutable(self):
        result = self.request()
        r = result['request']
        self.assertEqual(r['prospective_payload'], [{'pos': [1013, 78, -1380], 'state': LOAD}])
        self.assertEqual(r['maximum_payload_blocks'], 1)
        self.assertTrue(r['execution_forbidden'])
        self.assertFalse(r['glue_requested'])
        self.assertEqual(r['block_entities'], [])
        self.assertEqual(r['entities_to_create'], [])
        self.assertEqual(r['UUIDs_to_allocate'], [])
        self.assertIsNone(r['authority'])
        self.assertIsNone(r['dependency']['actual_native_Wren_completion'])
        self.assertTrue(r['blockers'])
        self.assertEqual(r['runtime_motion_stop_restart_acceptance'], 'UNVERIFIED; no successful lift is claimed')
        self.assertNotIn('placement', result)

    def test_only_verify_probes_and_no_existing_inventory_or_component_writes(self):
        before = deepcopy(self.after)
        result = self.request()
        self.assertEqual(self.after, before)
        for key in ('current_original', 'prospective_support'):
            self.assertTrue(result[key]['construction_forbidden'])
            self.assertTrue(result[key]['verification_only'])
            self.assertEqual(result[key]['block_entities'], [])
            self.assertEqual(result[key]['commands'], [])
        self.assertEqual(result['preservation']['existing_Wren_BE_tags'], 9)
        self.assertEqual(result['preservation']['existing_BE_or_inventory_writes'], 0)
        self.assertEqual(result['preservation']['source_component_or_rail_writes'], 0)

    def test_changed_drive_orientation_refuses_without_repairing_it(self):
        field = states(self.after)
        field[1013, 79, -1372] = 'create:hand_crank[facing=north,waterlogged=false]'
        changed = native_plan(self.registry, field, 'Changed drive', tags=self.after['block_entities'])
        with self.assertRaisesRegex(UserError, 'orientation'):
            self.request(old_after=changed)

    def test_occupied_sweep_or_adjacent_hull_refuses(self):
        for pos in ((1013, 77, -1380), (1014, 78, -1380)):
            field = states(self.after)
            field[pos] = 'minecraft:stone'
            changed = native_plan(self.registry, field, 'Occupied fixture', tags=self.after['block_entities'])
            with self.subTest(pos=pos), self.assertRaises(UserError):
                self.request(old_after=changed)

    def test_load_outside_frozen_sweep_is_refused(self):
        template = deepcopy(self.template)
        fitting = next(f for f in template['design']['fittings'] if f['kind'] == 'stopped cargo derrick')
        fitting['load_sweep_bounds'][4] -= 2
        with self.assertRaisesRegex(UserError, 'exceeds'):
            self.request(template=template)

    def test_saved_unknown_occupied_or_be_volume_refuses(self):
        for bad in (Snapshot({(1013, 78, -1380): None}), Snapshot({(1013, 78, -1380): 'minecraft:stone'}),
                    Snapshot(protected=[(1013, 78, -1380)])):
            with self.assertRaisesRegex(UserError, 'occupied/unknown/BE'):
                self.request(snapshot=bad)

    def test_stale_checkpoint_and_wrong_be_count_refuse(self):
        with self.assertRaises(UserError):
            self.request(receipt=self.receipt | {'sha256': '0'*64})
        changed = deepcopy(self.after)
        changed['block_entities'].pop()
        with self.assertRaisesRegex(UserError, 'nine'):
            self.request(old_after=changed)

    def test_wrong_cached_dependency_never_launches_javap(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'fake.jar'
            path.write_bytes(b'not the pinned native dependency')
            with patch('tools.grand_harbor_hoist_demo.subprocess.run') as run:
                with self.assertRaisesRegex(UserError, 'Exact cached'):
                    inspect_create(path)
                run.assert_not_called()


if __name__ == '__main__':
    unittest.main()
