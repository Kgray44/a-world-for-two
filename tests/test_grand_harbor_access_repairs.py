"""Portable refusal/dependency tests; no native or save actions."""
from copy import deepcopy
import unittest

from control_room.common import UserError
from tests.test_grand_harbor_fleet import registry
from tools.grand_harbor_berth import native_plan
from tools.grand_harbor_access_repairs import (
    AIR, CHECKPOINT, CHECKPOINT_SHA, TIMBER, WHEEL, WHEEL_STATE, LARK_DECK,
    LARK_TARGETS, WREN_ORIGIN, WREN_ROTATION, WREN_BACKING, WREN_LADDERS,
    WREN_PLATFORM, WREN_CLEARANCE, rotate_point, build_lark_repair, build_wren_request, states,
)


def receipt():
    return {'id': CHECKPOINT, 'sha256': CHECKPOINT_SHA, 'verified': True}


class Snapshot:
    def __init__(self, field=None, protected=()):
        self.field, self.protected, self.reads = field or {}, set(protected), []

    def state(self, pos):
        self.reads.append(pos)
        return self.field.get(pos, AIR)


def old_wren(r):
    transform = lambda pos: rotate_point(pos, WREN_ORIGIN, WREN_ROTATION)
    field = {transform(WREN_PLATFORM): 'chipped:detailed_dark_oak_planks'}
    for pos in WREN_LADDERS:
        field[transform(pos)] = AIR
    for pos in WREN_CLEARANCE:
        if pos[0] == 18:
            field[transform(pos)] = 'minecraft:water[level=0]' if pos[1] < 0 else AIR
    tags = []
    for n in range(9):
        pos = (990+n, 70, -1360)
        field[pos] = 'minecraft:chest[facing=north,type=single,waterlogged=false]'
        tags.append({'pos': list(pos), 'nbt': '{Items:[{id:"minecraft:stone",count:'+str(n+1)+'}],CustomName:"kept"}'})
    return native_plan(r, field, 'Fixture old complete Wren AFTER', tags=tags)


class AccessRepairTests(unittest.TestCase):
    def setUp(self):
        self.registry = registry()
        self.lark = Snapshot({WHEEL: WHEEL_STATE, LARK_DECK: TIMBER}, [WHEEL])

    def test_lark_adds_exact_two_ordinary_blocks_and_never_writes_wheel_be(self):
        result = build_lark_repair(self.registry, self.lark, receipt())
        self.assertEqual(states(result['placement']), {p: TIMBER for p in LARK_TARGETS})
        self.assertNotIn(WHEEL, states(result['placement']))
        self.assertEqual(result['placement']['block_entities'], [])
        self.assertEqual(result['placement']['commands'], [])
        self.assertEqual(states(result['after'])[WHEEL], WHEEL_STATE)
        self.assertEqual(result['scope']['wheel_BE_writes'], 0)
        self.assertIsNone(result['scope']['authority'])
        self.assertTrue(result['before']['construction_forbidden'])

    def test_lark_occupied_be_or_missing_support_refuses(self):
        for defect in ('occupied', 'be', 'wheel_missing_be', 'deck'):
            snapshot = deepcopy(self.lark)
            if defect == 'occupied':
                snapshot.field[LARK_TARGETS[0]] = 'minecraft:stone'
            elif defect == 'be':
                snapshot.protected.add(LARK_TARGETS[1])
            elif defect == 'wheel_missing_be':
                snapshot.protected.clear()
            else:
                snapshot.field[LARK_DECK] = AIR
            with self.subTest(defect=defect), self.assertRaises(UserError):
                build_lark_repair(self.registry, snapshot, receipt())

    def test_stale_or_unverified_checkpoint_refuses_both_requests(self):
        for bad in (receipt() | {'sha256': '0'*64}, receipt() | {'verified': False}, receipt() | {'id': 'old'}):
            with self.assertRaises(UserError):
                build_lark_repair(self.registry, self.lark, bad)
            with self.assertRaises(UserError):
                build_wren_request(self.registry, Snapshot(), bad, old_wren(self.registry))

    def test_wren_ladder_rotates_south_with_connected_backing_and_no_placement(self):
        original = old_wren(self.registry)
        result = build_wren_request(self.registry, Snapshot(), receipt(), original)
        delta = {tuple(row['pos']): row['state'] for row in result['request']['delta']}
        self.assertEqual(set(delta), {(1000, 63, -1349), (1000, 63, -1348), (1000, 64, -1348)})
        self.assertEqual(delta[1000, 63, -1349], TIMBER)
        for pos in ((1000, 63, -1348), (1000, 64, -1348)):
            self.assertEqual(delta[pos], 'minecraft:ladder[facing=south,waterlogged=false]')
        self.assertTrue(result['request']['execution_forbidden'])
        self.assertIsNone(result['request']['dependency']['authoritative_native_completion'])
        self.assertEqual(result['request']['block_entities'], [])
        self.assertNotIn('placement', result)
        self.assertFalse(result['scope']['executable_placement_emitted'])
        for key in ('before', 'after', 'support', 'new_current'):
            self.assertTrue(result[key]['construction_forbidden'])

    def test_wren_keeps_all_nine_original_be_tags_without_stock_replay(self):
        original = old_wren(self.registry)
        retained = deepcopy(original)
        result = build_wren_request(self.registry, Snapshot(), receipt(), original)
        self.assertEqual(original, retained)
        self.assertEqual(result['before']['block_entities'], original['block_entities'])
        self.assertEqual(result['after']['block_entities'], original['block_entities'])
        self.assertEqual(result['scope']['existing_BE_tags_sha256'], result['scope']['prospective_after_BE_tags_sha256'])
        self.assertEqual(result['scope']['existing_BE_writes'], 0)
        self.assertEqual(result['request']['commands'], [])
        self.assertEqual(result['scope']['actual_Wren_hull_currently_present'], 'NOT ASSERTED')

    def test_wren_new_outside_cells_are_actually_read_and_occupied_or_be_refused(self):
        original = old_wren(self.registry)
        outside = rotate_point(WREN_BACKING, WREN_ORIGIN, WREN_ROTATION)
        snapshot = Snapshot()
        result = build_wren_request(self.registry, snapshot, receipt(), original)
        self.assertIn(outside, snapshot.reads)
        self.assertEqual(result['scope']['new_actual_saved_cells_read'], 3)
        for bad in (Snapshot({outside: 'minecraft:ice'}), Snapshot(protected=[outside]), Snapshot({outside: None})):
            with self.assertRaises(UserError):
                build_wren_request(self.registry, bad, receipt(), original)

    def test_wren_occupied_prospective_target_or_old_be_overlap_refuses(self):
        original = old_wren(self.registry)
        field = states(original)
        target = rotate_point(WREN_LADDERS[0], WREN_ORIGIN, WREN_ROTATION)
        field[target] = 'minecraft:stone'
        blocked = native_plan(self.registry, field, 'Blocked fixture', tags=original['block_entities'])
        with self.assertRaisesRegex(UserError, 'occupied'):
            build_wren_request(self.registry, Snapshot(), receipt(), blocked)
        original['block_entities'][0]['pos'] = list(target)
        with self.assertRaisesRegex(UserError, 'block entity'):
            build_wren_request(self.registry, Snapshot(), receipt(), original)


if __name__ == '__main__':
    unittest.main()
