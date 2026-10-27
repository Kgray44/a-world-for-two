import copy
import json
from pathlib import Path
import unittest

from control_room.common import UserError
from tools.artistic_bascules import build
from tools.artistic_bridge_refinement import construct as bridge, leaf_name
from tools.artistic_bridge_towers import AIR, CENTERS, Towers, construct, validate
from tools.settlement_attractions import base, properties


class TowerDepthTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixtures = Path(__file__).parent/'fixtures'
        cls.registry = json.loads((fixtures/'artistic_bridge_refinement_registry.json').read_text())
        cls.registry['blocks'].update(json.loads((fixtures/'artistic_bridge_towers_registry.json').read_text())['blocks'])
        cls.registry.update(seed='synthetic', world_path='synthetic-world')
        old = build(cls.registry, 'a'*64)
        states = sorted(set(old.blocks.values()))
        master = {'format': 'awft-native-settlement:1', 'created': 'synthetic', 'seed': 'synthetic',
                  'world_path': 'synthetic-world', 'backup_sha256': 'a'*64, 'bounds': [1177, -1202, 1230, -1082],
                  'palette': states, 'blocks': [[*pos, states.index(state)] for pos, state in sorted(old.blocks.items())],
                  'block_entities': [{'pos': list(pos), 'nbt': tag} for pos, tag in old.tags.items()], 'commands': [], 'landmarks': []}
        future = bridge(cls.registry, master)
        states = sorted(set(future.blocks.values())); indices = {state: i for i, state in enumerate(states)}
        cls.full = dict(master, palette=states, blocks=[[*pos, indices[state]] for pos, state in sorted(future.blocks.items())],
                        block_entities=future.tags)

    def test_actual_bays_recesses_and_distinct_open_roofs_are_geometry_changes(self):
        p = construct(self.registry, self.full)
        north, south = CENTERS
        for center in CENTERS:
            for y in (72, 73, 78, 79):
                self.assertEqual(p.blocks[1182, y, center-4], AIR)
                self.assertEqual(base(p.blocks[1182, y, center-5]), 'mcwwindows:dark_oak_plank_window')
                self.assertTrue(properties(p.blocks[1182, y, center-5])['part'].endswith('_r'))
                self.assertTrue(properties(p.blocks[1183, y, center-5])['part'].endswith('_l'))
            self.assertIn('support_beam', p.blocks[1181, 75, center-2])
            self.assertIn('support_beam', p.blocks[1184, 81, center+2])
        self.assertEqual(p.blocks[1182, 91, north], AIR)
        self.assertEqual(p.blocks[1182, 92, north], AIR)
        self.assertIn('roof_peak', p.blocks[1182, 95, north])
        self.assertIn('roof_cap', p.blocks[1182, 90, south])
        self.assertEqual(base(p.blocks[1178, 79, south+2]), 'minecraft:bell')
        self.assertEqual(properties(p.blocks[1178, 79, south+2])['attachment'], 'ceiling')
        self.assertNotEqual(p.blocks[1178, 80, south+2], AIR)

    def test_machinery_moving_leaves_stairs_headroom_and_BE_payloads_are_exact(self):
        original = copy.deepcopy(self.full)
        p = construct(self.registry, self.full)
        for pos in p.protected:
            self.assertEqual(p.blocks.get(pos, AIR), p.original.get(pos, AIR))
        self.assertTrue(all(p.blocks[pos] == state for pos, state in p.original.items() if leaf_name(pos)))
        self.assertEqual(self.full, original)
        self.assertTrue(all(not row['violations'] for row in validate(p)['material_checks']))

    def test_bank_recesses_replace_known_solid_cells_without_extending_into_river(self):
        p = construct(self.registry, self.full)
        for pos in p.bank_mask:
            self.assertNotEqual(p.original[pos], AIR)
            self.assertEqual(base(p.blocks[pos]), 'minecraft:stone_brick_stairs')
            self.assertGreaterEqual(pos[1], 65)
        for pos, state in validate(p)['changed'].items():
            if pos[0] >= 1187 and pos not in p.bank_mask:
                self.assertEqual(state, AIR)

    def test_unreviewed_BE_unknown_palette_and_leaf_mutation_fail(self):
        changed = copy.deepcopy(self.full)
        changed['block_entities'].append({'pos': [1182, 72, CENTERS[0]-5], 'nbt': '{CustomName:"preserve"}'})
        with self.assertRaisesRegex(UserError, 'Preserve exact'):
            construct(self.registry, changed)
        registry = copy.deepcopy(self.registry)
        registry['blocks'].pop('mythrais:roof_up_67_copper')
        with self.assertRaisesRegex(UserError, 'Unregistered native'):
            construct(registry, self.full)
        p = construct(self.registry, self.full)
        p.blocks[1190, 70, -1168] = 'minecraft:stone_bricks'
        with self.assertRaisesRegex(UserError, 'machinery|moving'):
            validate(p)

    def test_large_flat_material_plane_cannot_be_hidden_by_orientation(self):
        p = construct(self.registry, self.full)
        for x in range(1180, 1184):
            for z in range(CENTERS[0]-2, CENTERS[0]+2):
                p.blocks[x, 89, z] = 'minecraft:oak_planks'
        with self.assertRaisesRegex(ValueError, 'material run rule'):
            validate(p)


if __name__ == '__main__':
    unittest.main()
