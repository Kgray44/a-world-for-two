"""Portable source bind/refusal tests; no actual world or native acceptance."""
from copy import deepcopy
import unittest

from control_room.common import UserError
from tests.test_grand_harbor_fleet import properties, registry
from tools.grand_harbor_fleet import build
from tools.grand_harbor_berth import (
    AIR, WATER, CHECKPOINT, CHECKPOINT_SHA, ORIGIN, ROTATION, KEY,
    checked_checkpoint, inspect_candidate, native_plan, rotate_point, rotated_state, translated, camera_batch,
)


class SavedFixture:
    def __init__(self, override=None, blocked=()):
        self.override = override or {}
        self.protected = set(blocked)

    def state(self, pos):
        return self.override.get(pos, WATER if pos[1] < 63 else AIR)


class FleetBerthTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = registry()
        cls.document = build(cls.registry, KEY)

    def test_quarter_turns_rotate_positions_about_waterline_origin(self):
        point = (3, -2, -5)
        self.assertEqual(rotate_point(point, (1000, 63, -1366), 0), (1003, 61, -1371))
        self.assertEqual(rotate_point(point, (1000, 63, -1366), 1), (1005, 61, -1363))
        self.assertEqual(rotate_point(point, (1000, 63, -1366), 2), (997, 61, -1361))
        self.assertEqual(rotate_point(point, (1000, 63, -1366), 3), (995, 61, -1369))

    def test_native_facing_axis_rope_keys_and_sign_rotation(self):
        self.assertEqual(properties(rotated_state('minecraft:ladder[facing=north,waterlogged=false]', self.registry, 1))['facing'], 'east')
        self.assertEqual(properties(rotated_state('minecraft:dark_oak_log[axis=x]', self.registry, 1))['axis'], 'z')
        rope = 'farm_and_charm:rope[north=true,east=false,south=false,west=true,up=true,down=false]'
        p = properties(rotated_state(rope, self.registry, 1))
        self.assertEqual((p['north'], p['east'], p['south'], p['west']), ('true', 'true', 'false', 'false'))
        self.assertEqual(properties(rotated_state('minecraft:oak_sign[rotation=8,waterlogged=false]', self.registry, 1))['rotation'], '12')

    def test_translated_inventory_tags_follow_the_exact_block_positions(self):
        field, tags = translated(self.document, self.registry, ORIGIN, ROTATION)
        self.assertEqual(len(field), len(self.document['blocks']))
        for old, tag in zip(self.document['block_entities'], tags):
            self.assertEqual(tuple(tag['pos']), rotate_point(old['pos'], ORIGIN, ROTATION))
            self.assertEqual(tag['nbt'], old['nbt'])
            self.assertIn(tuple(tag['pos']), field)

    def test_saved_clearance_yields_complete_before_probe_and_full_after(self):
        field, tags, before, probe, detail = inspect_candidate(self.document, self.registry, SavedFixture(), ORIGIN, ROTATION)
        self.assertTrue(set(field) <= set(before))
        self.assertTrue(set(probe) <= set(before))
        self.assertTrue(detail['two_block_under_keel_margin'])
        old = native_plan(self.registry, before, 'Fixture BEFORE')
        self.assertTrue(old['verification_only'])
        self.assertTrue(old['construction_forbidden'])
        self.assertEqual(old['commands'], [])
        self.assertEqual(old['block_entities'], [])
        after = native_plan(self.registry, {**before, **field}, 'Fixture AFTER', tags=tags)
        self.assertEqual(after['block_entities'], tags)
        self.assertEqual(after['backup_sha256'], CHECKPOINT_SHA)

    def test_ice_inventory_unknown_and_non_source_water_are_refused(self):
        field, _ = translated(self.document, self.registry, ORIGIN, ROTATION)
        target = next(iter(field))
        for state in ('minecraft:ice', 'minecraft:chest[facing=north,type=single,waterlogged=false]', None,
                      'minecraft:water[level=1]'):
            with self.subTest(state=state), self.assertRaises(UserError):
                inspect_candidate(self.document, self.registry, SavedFixture({target: state}), ORIGIN, ROTATION)
        with self.assertRaisesRegex(UserError, 'block entity'):
            inspect_candidate(self.document, self.registry, SavedFixture(blocked=[target]), ORIGIN, ROTATION)

    def test_missing_generated_chunk_is_not_substituted_with_air(self):
        class UnknownChunk(SavedFixture):
            def state(self, pos):
                raise UserError('The retained backup has no generated chunk')
        with self.assertRaisesRegex(UserError, 'Unknown/unavailable'):
            inspect_candidate(self.document, self.registry, UnknownChunk(), ORIGIN, ROTATION)

    def test_exact_protected_air_cell_blocks_the_candidate(self):
        field, _ = translated(self.document, self.registry, ORIGIN, ROTATION)
        target = next(iter(field))
        with self.assertRaisesRegex(UserError, 'protected source mask'):
            inspect_candidate(self.document, self.registry, SavedFixture(), ORIGIN, ROTATION, [target])

    def test_stale_unverified_or_different_checkpoint_is_refused(self):
        good = {'id': CHECKPOINT, 'sha256': CHECKPOINT_SHA, 'verified': True}
        checked_checkpoint(good)
        for key, value in (('id', '20261028T161905Z-06e1e7'), ('sha256', '0'*64), ('verified', False)):
            with self.subTest(key=key), self.assertRaisesRegex(UserError, 'verified6ad3a8'):
                checked_checkpoint(good | {key: value})
        with self.assertRaisesRegex(UserError, 'verified6ad3a8'):
            checked_checkpoint({'id': '20261028T180051Z-30624d',
                                'sha256': '3cb269d28ae1ccbac882a44d35277d82c83582274abad2f1cf3b41566d3e9b24',
                                'verified': True})

    def test_wrong_template_or_non_integer_origin_is_refused(self):
        wrong = deepcopy(self.document)
        wrong['key'] = 'rosewater-lark'
        with self.assertRaisesRegex(UserError, 'One Wren'):
            translated(wrong, self.registry, ORIGIN, ROTATION)
        with self.assertRaisesRegex(UserError, 'One Wren'):
            translated(self.document, self.registry, (1000, 63.0, -1366), ROTATION)

    def test_actual_capture_slugs_cover_all_compartments_derrick_and_boarding(self):
        recipe = camera_batch(self.document)
        labels = {row['original_label'] for row in recipe['world_views']}
        self.assertTrue({room['name'] for room in self.document['rooms']} <= labels)
        names = [row['name'] for row in recipe['world_views']]
        self.assertEqual(len(names), len(set(names)))
        for name in names:
            self.assertRegex(name, '^[a-z0-9]+(-[a-z0-9]+)*$')
            self.assertLessEqual(len('wren-r1-'+name), 58)
        self.assertIn('shipboard-derrick', names)
        self.assertIn('boarding-and-skiff-approach', names)


if __name__ == '__main__':
    unittest.main()
