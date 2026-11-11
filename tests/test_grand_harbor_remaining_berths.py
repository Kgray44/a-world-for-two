"""Portable remaining-berth census tests; not native or gameplay evidence."""
from copy import deepcopy
import unittest

from control_room.common import UserError
from tests.test_grand_harbor_fleet import registry, properties
from tools.grand_harbor_fleet import build
from tools.grand_harbor_remaining_berths import (
    AIR, WATER, CHECKPOINT, CHECKPOINT_SHA, OLD_STUDY_CHECKPOINT, OLD_STUDY_SHA,
    ROLES, POSES, checked_checkpoint, classify, census, native_plan, translated, required_probe,
)


class SavedFixture:
    def __init__(self, override=None, block_entities=()):
        self.override, self.protected = override or {}, set(block_entities)

    def state(self, pos):
        return self.override.get(pos, WATER if pos[1] < 63 else AIR)


class RemainingBerthTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = registry()
        for name in ('minecraft:kelp', 'hybrid_aquatic:delesseria'):
            cls.registry['blocks'][name] = {'age': [str(i) for i in range(26)]}
        for name in ('minecraft:kelp_plant', 'minecraft:seagrass', 'hybrid_aquatic:delesseria_plant'):
            cls.registry['blocks'][name] = {}
        cls.documents = {role: build(cls.registry, role) for role in ROLES}

    def first_field(self, role=ROLES[0]):
        return translated(self.documents[role], self.registry, role, *POSES[role])[0]

    def test_role_translation_rotates_geometry_and_axes_without_wren_key_spoof(self):
        role = ROLES[0]
        field, tags = translated(self.documents[role], self.registry, role, (1110, 63, -1344), 1)
        self.assertEqual(len(field), len(self.documents[role]['blocks']))
        for original, tag in zip(self.documents[role]['block_entities'], tags):
            x, y, z = original['pos']
            self.assertEqual(tag['pos'], [1110-z, 63+y, -1344+x])
        wrong = deepcopy(self.documents[role])
        wrong['key'] = 'resolute-wren'
        with self.assertRaisesRegex(UserError, 'exact remaining role'):
            translated(wrong, self.registry, role, *POSES[role])

    def test_passing_fixture_covers_every_target_and_full_depth_departure_probe(self):
        for role in ROLES:
            field, tags, before, probe, report, proposal = census(
                self.documents[role], self.registry, SavedFixture(), role, *POSES[role])
            self.assertTrue(report['strict_saved_admission_passed'])
            self.assertEqual(set(before), set(field)|set(probe))
            self.assertEqual(report['detail']['outward_departure_blocks'], 8)
            self.assertEqual(report['detail']['water_layers_below_surface'], 2)
            self.assertTrue(report['detail']['two_block_under_keel_saved_verified'])
            self.assertFalse(report['detail']['current_native_clearance_verified'])
            self.assertEqual(proposal['count'], 0)

    def test_exact_plants_are_unapproved_nonexecutable_water_proposals(self):
        role = ROLES[0]
        positions = [p for p in self.first_field() if p[1] == 62][:3]
        actual = dict(zip(positions, ('minecraft:kelp[age=24]', 'hybrid_aquatic:delesseria_plant', 'minecraft:seagrass')))
        _, _, before, _, report, proposal = census(
            self.documents[role], self.registry, SavedFixture(actual), role, *POSES[role])
        self.assertFalse(report['strict_saved_admission_passed'])
        self.assertFalse(report['detail']['current_native_clearance_verified'])
        self.assertEqual(proposal['count'], 3)
        self.assertTrue(proposal['not_executable'])
        self.assertIs(proposal['approved'], False)
        self.assertIsNone(proposal['approval'])
        self.assertEqual(proposal['commands'], [])
        self.assertEqual(proposal['world_writes'], 0)
        for row in proposal['cells']:
            self.assertEqual(before[tuple(row['pos'])], row['before_state'])
            self.assertEqual(row['proposed_after_state'], WATER)
        self.assertEqual(len(proposal['exact_cells_sha256']), 64)

    def test_hard_blocks_be_non_source_water_and_unknown_stay_separate(self):
        role = ROLES[1]
        positions = [p for p in self.first_field(role) if p[1] == 62][:4]
        actual = dict(zip(positions, ('minecraft:stone', 'minecraft:barrel[facing=west,open=false]',
                                      'minecraft:water[level=1]', None)))
        result = census(self.documents[role], self.registry,
                        SavedFixture(actual, block_entities=[positions[1]]), role, *POSES[role])
        report, proposal = result[-2:]
        self.assertFalse(report['strict_saved_admission_passed'])
        counts = report['detail']['classification_counts']
        for kind in ('HARD_TERRAIN_OR_STRUCTURE', 'BLOCK_ENTITY_PRESERVE', 'NON_SOURCE_WATER', 'UNKNOWN'):
            self.assertEqual(counts[kind], 1)
        self.assertEqual(proposal['count'], 0)
        self.assertEqual(report['unknown'][0]['pos'], list(positions[3]))

    def test_protected_wren_and_other_role_air_masks_independently_refuse(self):
        role = ROLES[0]
        positions = list(self.first_field())[:3]
        report = census(self.documents[role], self.registry, SavedFixture(), role, *POSES[role],
                        protected=[positions[0]], wren=[positions[1]], other_role=[positions[2]])[-2]
        self.assertFalse(report['strict_saved_admission_passed'])
        for key in ('protected_source_cells', 'wren_reserved_cells', 'other_role_reserved_cells'):
            self.assertEqual(report['detail'][key], 1)

    def test_unknown_chunks_are_recorded_and_never_assumed_air(self):
        class Missing(SavedFixture):
            def state(self, pos):
                raise UserError('No generated saved chunk')
        role = ROLES[0]
        result = census(self.documents[role], self.registry, Missing(), role, *POSES[role])
        self.assertEqual(result[2], {})
        self.assertFalse(result[-2]['strict_saved_admission_passed'])
        self.assertEqual(len(result[-2]['unknown']), result[-2]['detail']['target_and_probe_cells'])

    def test_native_checkpoint_binding_rejects306_or_unverified_receipts(self):
        checked_checkpoint({'id': CHECKPOINT, 'sha256': CHECKPOINT_SHA, 'verified': True})
        for bad in ({'id': OLD_STUDY_CHECKPOINT, 'sha256': OLD_STUDY_SHA, 'verified': True},
                    {'id': CHECKPOINT, 'sha256': CHECKPOINT_SHA, 'verified': False}):
            with self.assertRaisesRegex(UserError, 'verified6ad3a8'):
                checked_checkpoint(bad)
        before = native_plan(self.registry, {(0, 62, 0): WATER}, 'Fixture VERIFY')
        self.assertEqual(before['backup_sha256'], CHECKPOINT_SHA)
        self.assertTrue(before['verification_only'])
        self.assertTrue(before['construction_forbidden'])

    def test_no_broad_aquatic_namespace_or_above_water_replacement_allowlist(self):
        self.assertEqual(classify('hybrid_aquatic:other_plant', (0, 62, 0), self.registry), 'HARD_TERRAIN_OR_STRUCTURE')
        self.assertEqual(classify('minecraft:kelp[age=24]', (0, 63, 0), self.registry), 'HARD_TERRAIN_OR_STRUCTURE')
        self.assertEqual(classify('minecraft:kelp[age=99]', (0, 62, 0), self.registry), 'HARD_TERRAIN_OR_STRUCTURE')


if __name__ == '__main__':
    unittest.main()
