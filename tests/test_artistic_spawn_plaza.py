"""Bounded source semantics; these do not simulate native fluid/redstone ticks."""
import json
from pathlib import Path
import unittest

from control_room.common import UserError
from tools.artistic_spawn_plaza import (
    AIR, CREATE_SHA, HEADER, JET_WITNESSES, OUTLET, PISTON, PLUG_OPEN,
    PUMP, SPAWN, STOP_LEVER, WHEEL_SOURCE, WHEEL_BAFFLE, construct, key, state, validate,
)


REGISTRY = json.loads((Path(__file__).parent/'fixtures/spawn_plaza_registry.json').read_text())


class SourceSnapshot:
    """Synthetic stepped soil and explicit obstacles, not an emulated game."""
    def __init__(self, obstacles=None, protected=()):
        self.obstacles = obstacles or {}
        self.protected = set(protected)

    def state(self, pos):
        if pos in self.obstacles:
            return self.obstacles[pos]
        x, y, z = pos
        ground = 63 if x >= 1144 and z <= -1128 else 65 if x <= 1128 and z <= -1128 else 64
        return 'minecraft:grass_block' if y == ground else 'minecraft:dirt' if y < ground else AIR


class SpawnPlazaTests(unittest.TestCase):
    def make(self):
        return construct(REGISTRY, SourceSnapshot())

    def test_real_native_schemas_and_dry_commissioning_endpoints(self):
        p = self.make()
        proof = validate(p)
        self.assertEqual(REGISTRY['create_jar_sha256'], CREATE_SHA)
        self.assertEqual(REGISTRY['mechanical_pump_range'], 16)
        self.assertEqual(proof['source_to_header_edges_including_intake'], 16)
        self.assertEqual(p.at(HEADER), AIR)
        self.assertEqual(p.at(WHEEL_SOURCE), AIR)
        self.assertTrue(all(p.at(v) == AIR for v in JET_WITNESSES))
        self.assertIn('facing=east', p.at(PUMP))
        self.assertTrue(all(pos[1] == 65 for pos, s in p.blocks.items() if key(s) == 'minecraft:water'))
        self.assertFalse(proof['artistic_acceptance'])

    def test_the_single_wheel_source_cannot_feed_both_tangential_faces(self):
        p = self.make()
        self.assertEqual(key(p.at(WHEEL_BAFFLE)), 'rechiseled:quartz_block_chiseled_pillar')
        self.assertTrue(all(key(p.at(pos)) not in {AIR, 'minecraft:water'} for pos in
                        [(1144, 69, -1131), (1146, 69, -1131), (1145, 69, -1132)]))
        self.assertTrue(all(p.at((1145, y, -1131)) == AIR for y in range(64, 70)))
        p.blocks[WHEEL_BAFFLE] = AIR
        with self.assertRaisesRegex(UserError, 'opposing wheel-face'):
            validate(p)

    def test_layered_coves_and_supported_crown_are_actual_shape_changes(self):
        p = self.make()
        self.assertEqual(key(p.at((1137, 66, -1128))), 'minecraft:quartz_stairs')
        self.assertIn('half=top', p.at((1137, 66, -1128)))
        self.assertEqual(key(p.at((1137, 67, -1128))), 'dawnoftimebuilder:marble_coffer_slab')
        self.assertEqual(key(p.at((1136, 68, -1128))), 'mythrais:corbel_scroll_centre_stone')
        for x in (1137, 1139):
            self.assertEqual(key(p.at((x, 75, -1130))), 'supplementaries:statue')
            self.assertEqual(key(p.at((x, 74, -1130))), 'minecraft:waxed_cut_copper')
            self.assertEqual(key(p.at((x, 73, -1130))), 'minecraft:waxed_weathered_cut_copper')
            self.assertEqual(key(p.at((x, 72, -1129))), 'mythrais:cloverleaf_column_capital_stone')

    def test_gate_travel_and_normal_stop_lever_cannot_be_removed_or_reoriented(self):
        p = self.make()
        self.assertIn('facing=east', p.at(STOP_LEVER))
        self.assertEqual(key(p.at(PLUG_OPEN)), 'minecraft:chiseled_quartz_block')
        p.blocks[PISTON] = state(REGISTRY, 'minecraft:sticky_piston', facing='south', extended=False)
        with self.assertRaisesRegex(UserError, 'north-facing'):
            validate(p)
        p = self.make()
        p.blocks[OUTLET] = 'minecraft:quartz_bricks'
        with self.assertRaisesRegex(UserError, 'one-block travel'):
            validate(p)
        p = self.make()
        self.assertIn('facing=south', p.at((1138, 73, -1125)))
        self.assertEqual(key(p.at((1138, 73, -1124))), 'minecraft:redstone_wire')
        p.blocks[1138, 73, -1125] = state(REGISTRY, 'minecraft:repeater', facing='north',
                                         delay=1, locked=False, powered=False)
        with self.assertRaisesRegex(UserError, 'south input'):
            validate(p)

    def test_seeded_header_or_upper_jet_cannot_substitute_for_pumped_flow(self):
        p = self.make()
        p.blocks[HEADER] = state(REGISTRY, 'minecraft:water', level=0)
        with self.assertRaisesRegex(UserError, 'remain dry'):
            validate(p)
        p = self.make()
        p.blocks[1138, 70, -1128] = state(REGISTRY, 'minecraft:water', level=0)
        with self.assertRaisesRegex(UserError, 'No header, jet'):
            validate(p)

    def test_existing_block_entity_or_non_natural_object_is_never_overwritten(self):
        with self.assertRaisesRegex(UserError, 'saved plaza block entity'):
            construct(REGISTRY, SourceSnapshot(protected={HEADER}))
        with self.assertRaisesRegex(UserError, 'retained object'):
            construct(REGISTRY, SourceSnapshot(obstacles={HEADER: 'minecraft:chest'}))

    def test_neighboring_explicit_air_and_unknown_models_fail_closed(self):
        with self.assertRaisesRegex(UserError, 'neighboring composition'):
            construct(REGISTRY, SourceSnapshot(), excluded={(1134, 65, -1110): AIR})
        with self.assertRaisesRegex(UserError, 'Unsupported native'):
            state(REGISTRY, 'invented:beautiful_fountain')
        with self.assertRaisesRegex(UserError, 'Unsupported native'):
            state(REGISTRY, 'minecraft:quartz_stairs', facing='up')

    def test_routes_pipe_range_and_spawn_arrival_are_semantic_gates(self):
        p = self.make()
        self.assertEqual(p.routes[SPAWN[0], SPAWN[2]], SPAWN[1]-1)
        p.blocks[1147, 66, -1127] = 'minecraft:quartz_bricks'
        with self.assertRaisesRegex(UserError, 'protected route'):
            validate(p)
        p = self.make()
        p.pipe_nodes.remove((1142, 70, -1129))
        with self.assertRaisesRegex(UserError, 'disconnected'):
            validate(p)

    def test_complete_material_rule_rejects_a_reintroduced_uniform_panel(self):
        p = self.make()
        for x in range(1124, 1128):
            for z in range(-1137, -1133):
                p.blocks[x, 76, z] = 'minecraft:quartz_bricks'
        with self.assertRaisesRegex(ValueError, 'material run rule failed'):
            validate(p)


if __name__ == '__main__':
    unittest.main()
