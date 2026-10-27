import copy
import json
from pathlib import Path
import unittest

from control_room.common import UserError
from tools.artistic_bascules import build
from tools.artistic_bridge_refinement import (
    AIR, BUTTONS, CAMERAS, LEAVES, Refinement, articulated_leaves, construct,
    flatten, leaf_name, payload, validate,
)


class BridgeRefinementTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = json.loads((Path(__file__).parent/'fixtures/artistic_bridge_refinement_registry.json').read_text())
        cls.registry.update(seed='synthetic', world_path='synthetic-world')
        old = build(cls.registry, 'a'*64)
        palette = sorted(set(old.blocks.values()))
        cls.master = {'format': 'awft-native-settlement:1', 'created': 'synthetic',
                      'seed': 'synthetic', 'world_path': 'synthetic-world', 'backup_sha256': 'a'*64,
                      'bounds': [1179, -1202, 1228, -1082], 'palette': palette,
                      'blocks': [[*pos, palette.index(state)] for pos, state in sorted(old.blocks.items())],
                      'block_entities': [{'pos': list(pos), 'nbt': value} for pos, value in old.tags.items()],
                      'commands': [], 'landmarks': []}

    def test_structural_change_halves_deck_thickness_and_removes_high_T_caps(self):
        p = construct(self.registry, self.master)
        proof = validate(p)
        self.assertGreater(len(proof['moving']), 1000)
        self.assertGreater(len(proof['fixed']), 2000)
        self.assertTrue(all(not row['violations'] for row in proof['material_checks']))
        for name, pivot, direction, length in LEAVES:
            for x in range(1187, 1199):
                self.assertEqual(p.blocks[x, 70, pivot], p.original[x, 70, pivot])
                self.assertIn('type=top', p.blocks[x, 70, pivot+direction])
            self.assertTrue(all(state == AIR for pos, state in p.blocks.items()
                                if leaf_name(pos) == name and pos[1] == 74))
            self.assertLess(sum(leaf_name(pos) == name and pos[1] > 70 and state != AIR for pos, state in p.blocks.items()),
                            sum(leaf_name(pos) == name and pos[1] > 70 and state != AIR for pos, state in p.original.items()))

    def test_every_real_control_and_existing_BE_payload_is_preserved(self):
        original = copy.deepcopy(self.master)
        p = construct(self.registry, self.master)
        self.assertEqual(p.tags, self.master['block_entities'])
        self.assertTrue(all(p.blocks[pos] == p.original[pos] for pos in p.protected))
        self.assertTrue(all(p.blocks[pos].startswith('minecraft:stone_button[') for pos in BUTTONS))
        self.assertEqual(self.master, original)
        for states in (validate(p)['moving'], validate(p)['fixed']):
            delta = payload(self.master, states, 'b'*64, 'synthetic proposal')
            self.assertEqual(delta['commands'], [])
            self.assertEqual(delta['block_entities'], [])

    def test_foreign_authored_air_and_saved_BE_inside_change_area_are_refused(self):
        pos = (1179, 71, -1178)
        exclusion = {'palette': [AIR], 'blocks': [[*pos, 0]]}
        with self.assertRaisesRegex(UserError, 'fixed rosebridge|authored footprint'):
            construct(self.registry, self.master, [exclusion])
        changed = copy.deepcopy(self.master)
        changed['block_entities'].append({'pos': [1187, 73, -1165], 'nbt': '{CustomName:"preserve"}'})
        with self.assertRaisesRegex(UserError, 'Preserve exact native'):
            articulated_leaves(Refinement(self.registry, changed))

    def test_obstructed_moving_corridor_and_changed_root_attachment_fail(self):
        for pos, state in (((1190, 71, -1160), 'minecraft:stone_bricks'),
                           ((1198, 70, -1172), 'minecraft:spruce_slab[type=top,waterlogged=false]')):
            p = construct(self.registry, self.master)
            p.blocks[pos] = state
            with self.assertRaisesRegex(UserError, 'corridor|attachment'):
                validate(p)

    def test_comparison_pose_is_bound_to_real_prior_frame_without_native_claim(self):
        camera = CAMERAS[0]
        self.assertEqual(camera['feet'], [1168, 64, -1144])
        self.assertEqual(camera['yaw'], -90.0)
        self.assertAlmostEqual(camera['pitch'], -16.4466)
        self.assertEqual(len(camera['reference_image_sha256']), 64)

    def test_paired_native_windows_use_increasing_axis_right_then_left(self):
        from tools.settlement_attractions import properties
        p = construct(self.registry, self.master)
        checked = 0
        for z in (-1178, -1110):
            for side in (1179, 1186):
                for y in (78, 79):
                    self.assertTrue(properties(p.blocks[side, y, z-1])['part'].endswith('_r'))
                    self.assertTrue(properties(p.blocks[side, y, z])['part'].endswith('_l'))
                    checked += 2
            for y in (72, 73, 78, 79):
                self.assertTrue(properties(p.blocks[1182, y, z-4])['part'].endswith('_r'))
                self.assertTrue(properties(p.blocks[1183, y, z-4])['part'].endswith('_l'))
                checked += 2
        self.assertEqual(checked, 32)


if __name__ == '__main__':
    unittest.main()
