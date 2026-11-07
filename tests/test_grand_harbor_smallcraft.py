"""Small-vessel source checks are separate from actual Minecraft acceptance."""
import gzip
import io
import unittest

import nbtlib

from control_room.common import UserError
from tests.test_grand_harbor_fleet import registry, block_map, properties
from tools.grand_harbor_fleet import structure_nbt
from tools.grand_harbor_smallcraft import build, SMALLCRAFT_ORDER, SPECS, SmallCraft, hull, lower_hull_check


class SmallCraftTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = registry()
        cls.registry['items'] = sorted(set(cls.registry['items']) | {'minecraft:fishing_rod'})
        cls.documents = {key: build(cls.registry, key) for key in SMALLCRAFT_ORDER}

    def test_different_forms_and_rigs_preserve_two_mouth_one_river(self):
        self.assertEqual(len({tuple(d['bounds']) for d in self.documents.values()}), 3)
        self.assertEqual([len(SPECS[k].mast_positions) for k in SMALLCRAFT_ORDER], [1, 2, 0])
        self.assertEqual(sum(d['design']['berth'] == 'harbor-mouth-proposal' for d in self.documents.values()), 2)
        self.assertEqual(sum(d['design']['berth'] == 'river-proposal' for d in self.documents.values()), 1)

    def test_every_named_room_connects_to_low_boarding_landing(self):
        for key, d in self.documents.items():
            names = d['checks']['circulation']['rooms_reached']
            self.assertIn('Boarding landing', names, key)
            self.assertIn('Working deck', names, key)
            self.assertEqual(len(names), len(d['rooms']))
            self.assertEqual(d['checks']['materials']['violations'], [])
            self.assertGreater(d['checks']['lower_hull_seal']['enclosed_submerged_air_cells'], 0)

    def test_no_world_identity_runtime_commands_or_fake_sailing_entities(self):
        for d in self.documents.values():
            self.assertEqual(d['format'], 'awft-fleet-template:1')
            self.assertFalse({'seed', 'world_path', 'backup_sha256'} & d.keys())
            self.assertEqual(d['commands'], [])
            self.assertEqual(d['entities'], [])
            self.assertIsNone(d['placement_authority'])
            self.assertIn('STATIC STRUCTURE', d['design']['mobility'])

    def test_beds_doors_and_ladder_have_real_support_and_both_halves(self):
        for key, d in self.documents.items():
            cells = block_map(d)
            for (x, y, z), state in cells.items():
                props = properties(state)
                if state.split('[')[0].endswith('_bed') and props.get('part') == 'foot':
                    self.assertEqual(properties(cells[x, y, z+1]).get('part'), 'head', key)
                if state.split('[')[0].endswith('_door') and props.get('half') == 'lower':
                    self.assertEqual(properties(cells[x, y+1, z]).get('half'), 'upper', key)
                if state.startswith('minecraft:ladder'):
                    self.assertEqual(props['facing'], 'east')
                    self.assertNotEqual(cells.get((x-1, y, z), 'minecraft:air'), 'minecraft:air')

    def test_original_structure_roundtrip_has_no_entities(self):
        for d in self.documents.values():
            structure = nbtlib.File.parse(io.BytesIO(gzip.decompress(structure_nbt(d))))
            self.assertEqual(len(structure['blocks']), len(d['blocks']))
            self.assertEqual(len(structure['entities']), 0)
            self.assertEqual(int(structure['DataVersion']), 3955)

    def test_lower_shell_refuses_air_carving(self):
        p = SmallCraft(self.registry, SPECS[SMALLCRAFT_ORDER[0]])
        hull(p)
        point = next(pos for pos in p.shell_cells if pos[1] < 0)
        with self.assertRaisesRegex(UserError, 'watertight hull'):
            p.put(*point, 'minecraft:air')

    def test_unknown_design_is_refused(self):
        with self.assertRaisesRegex(UserError, 'Unknown authored'):
            build(self.registry, 'future-fantasy-ferry')

    def test_a_hole_in_submerged_side_fails_full_interior_flood(self):
        p = SmallCraft(self.registry, SPECS[SMALLCRAFT_ORDER[0]])
        hull(p)
        point = next(pos for pos in p.shell_cells if pos[1] == 0
                     and any(p.local_state(pos[0]+dx, pos[1], pos[2]+dz) == 'minecraft:air'
                             and (pos[0]+dx, pos[1], pos[2]+dz) in p.blocks
                             for dx, dz in ((-1, 0), (1, 0), (0, -1), (0, 1))))
        p.blocks.pop(point)
        with self.assertRaisesRegex(UserError, 'flood reaches'):
            lower_hull_check(p)


if __name__ == '__main__':
    unittest.main()
