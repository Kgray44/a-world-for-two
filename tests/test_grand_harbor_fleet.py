"""Design regressions and refusal paths; none of these is live game evidence."""
from copy import deepcopy
import gzip
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import nbtlib

from control_room.common import UserError
from tests.test_artistic_ship import registry as lark_registry
import tools.grand_harbor_fleet as fleet


def registry():
    r = lark_registry()
    blocks = r['blocks']
    # Additional property enums copied from the actual candidate49 registry.
    for color in ('green', 'red', 'white'):
        blocks['minecraft:'+color+'_bed'] = deepcopy(blocks['minecraft:blue_bed'])
        blocks['minecraft:'+color+'_wool'] = {}
    for timber in ('birch', 'spruce'):
        blocks['minecraft:'+timber+'_trapdoor'] = deepcopy(blocks['minecraft:oak_trapdoor'])
    blocks['minecraft:oak_door'] = deepcopy(blocks['minecraft:dark_oak_door'])
    blocks['minecraft:stone_bricks'] = {}
    blocks['supplementaries:globe'] = {
        'facing': ['north', 'south', 'west', 'east'], 'powered': ['true', 'false'],
        'rotation': ['0', '1', '2', '3', '4'], 'waterlogged': ['true', 'false'],
    }
    r['items'] = sorted(set(r['items']) | {
        'minecraft:water_bucket', 'minecraft:paper', 'minecraft:honey_bottle',
        'minecraft:wheat', 'minecraft:emerald', 'minecraft:leather', 'minecraft:poppy',
    })
    return r


def block_map(doc):
    return {tuple(row[:3]): doc['palette'][row[3]] for row in doc['blocks']}


def properties(state):
    return dict(pair.split('=') for pair in state.split('[', 1)[1][:-1].split(',')) if '[' in state else {}


class FleetGeometryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = registry()
        cls.documents = {key: fleet.build(cls.registry, key) for key in fleet.FLEET_ORDER}

    def test_layout_retains_one_offshore_two_furled_and_one_dockside_drying(self):
        designs = [d['design'] for d in self.documents.values()]
        self.assertEqual(sum(d['berth'] == 'offshore' for d in designs), 1)
        self.assertEqual(sum(d['berth'] == 'dockside' and d['sail_state'] == 'furled' for d in designs), 2)
        self.assertEqual(sum(d['berth'] == 'dockside' and d['sail_state'] == 'hanging-dry' for d in designs), 1)
        self.assertEqual(len({tuple(d['bounds']) for d in self.documents.values()}), 4)
        self.assertEqual([len(fleet.SPECS[k].mast_positions) for k in fleet.SPECS], [3, 2, 3])
        self.assertEqual([len(self.documents[k]['guns']) for k in fleet.FLEET_ORDER], [28, 4, 12, 10])

    def test_required_rooms_are_reachable_and_lower_hulls_seal(self):
        for key in fleet.SPECS:
            d = self.documents[key]
            names = set(d['checks']['circulation']['rooms_reached'])
            self.assertTrue({"Captain's cabin", 'Officer and lieutenant accommodation', 'Wardroom',
                             'Crew berthing', 'Crew mess', 'Galley', 'Gun deck', 'Cargo hold',
                             'Powder magazine', 'Sail and rope storage', 'Tender boarding landing'} <= names, key)
            self.assertGreater(d['checks']['lower_hull_seal']['shell_cells'], 0)
            self.assertEqual(d['checks']['materials']['violations'], [])
            self.assertTrue(d['checks']['rope_attachments']['anchored_source_graph'])
            self.assertEqual(d['checks']['circulation']['native_collision_walking_and_multiplayer'], 'UNVERIFIED')

    def test_source_templates_contain_no_world_identity_or_runtime_authority(self):
        for d in self.documents.values():
            self.assertEqual(d['format'], 'awft-fleet-template:1')
            self.assertFalse({'seed', 'world_path', 'backup_sha256'} & d.keys())
            self.assertEqual(d['commands'], [])
            self.assertEqual(d['entities'], [])
            self.assertIsNone(d['placement_authority'])
            for gun in d['guns']:
                self.assertIs(gun['loaded'], False)
                self.assertIs(gun['assembled'], False)

    def test_beds_and_doors_retain_both_oriented_halves(self):
        offsets = {'south': (0, 0, 1), 'north': (0, 0, -1), 'east': (1, 0, 0), 'west': (-1, 0, 0)}
        for key, d in self.documents.items():
            cells = block_map(d)
            for pos, state in cells.items():
                props = properties(state)
                material = fleet.identifier(state)
                if material.endswith('_bed') and props.get('part') == 'foot':
                    head = tuple(a+b for a, b in zip(pos, offsets[props['facing']]))
                    self.assertEqual(fleet.identifier(cells.get(head, '')), material, (key, pos))
                    self.assertEqual(properties(cells[head]).get('part'), 'head')
                if material.endswith('_door') and props.get('half') == 'lower':
                    upper = pos[0], pos[1]+1, pos[2]
                    self.assertEqual(fleet.identifier(cells.get(upper, '')), material, (key, pos))
                    self.assertEqual(properties(cells[upper]).get('half'), 'upper')

    def test_authored_inventory_tags_parse_and_contain_no_ammunition(self):
        for d in self.documents.values():
            for row in d['block_entities']:
                tag = nbtlib.parse_nbt(row['nbt'])
                for item in tag.get('Items', []):
                    self.assertNotIn(str(item['id']), {'minecraft:tnt', 'minecraft:gunpowder', 'minecraft:fire_charge'})
                    if str(item['id']).startswith('createbigcannons:'):
                        self.assertIn(str(item['id']), {'createbigcannons:worm'})

    def test_capture_recipes_require_real_images_without_creating_them(self):
        for d in self.documents.values():
            recipe = fleet.capture_recipe(d)
            self.assertTrue({'bow', 'stern', 'broadside', 'elevated', 'deck'} <= {v['name'] for v in recipe['local_views']})
            self.assertIn('no image generated', recipe['status'])

    def test_original_nbt_roundtrip_preserves_every_state_position_and_inventory(self):
        d = self.documents['mercy-of-the-tide']
        raw = fleet.structure_nbt(d)
        decoded = nbtlib.File.parse(io.BytesIO(gzip.decompress(raw)))
        self.assertEqual(int(decoded['DataVersion']), 3955)
        self.assertEqual(len(decoded['entities']), 0)
        self.assertEqual(len(decoded['blocks']), len(d['blocks']))
        for original, row in zip(d['blocks'], decoded['blocks']):
            self.assertEqual([int(v)+lo for v, lo in zip(row['pos'], d['bounds'][:3])], original[:3])
            self.assertEqual(int(row['state']), original[3])
        actual_tags = {tuple(int(v)+lo for v, lo in zip(row['pos'], d['bounds'][:3])): row['nbt']
                       for row in decoded['blocks'] if 'nbt' in row}
        for original in d['block_entities']:
            self.assertEqual(actual_tags[tuple(original['pos'])], nbtlib.parse_nbt(original['nbt']))
        self.assertEqual(raw, fleet.structure_nbt(d))

    def test_hull_shell_cannot_be_carved_for_furniture(self):
        p = fleet.FleetShip(self.registry, fleet.SPECS['resolute-wren'])
        fleet.hull(p)
        pos = next(pos for pos in p.shell_cells if pos[1] < 0)
        with self.assertRaisesRegex(UserError, 'watertight hull'):
            p.put(*pos, fleet.AIR)

    def test_blocked_entry_fails_walk_graph(self):
        p = fleet.FleetShip(self.registry, fleet.SPECS['resolute-wren'])
        p.blocks = block_map(self.documents['resolute-wren'])
        p.rooms = self.documents['resolute-wren']['rooms']
        x, y, z = p.entry
        p.put(x, y+1, z, 'minecraft:stone_bricks')
        with self.assertRaisesRegex(UserError, 'entry is not clear'):
            fleet.circulation(p)

    def test_missing_native_block_refuses_design(self):
        r = deepcopy(self.registry)
        del r['blocks']['farm_and_charm:rope']
        with self.assertRaisesRegex(UserError, 'registered block'):
            fleet.build(r, 'resolute-wren')


class FleetExportTests(unittest.TestCase):
    def test_export_never_overwrites_an_existing_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root/'registry.json'
            source.write_text(json.dumps(registry()))
            with patch.object(fleet.subprocess, 'run') as guard:
                with self.assertRaisesRegex(UserError, 'immutable'):
                    fleet.export(source, root)
                guard.assert_not_called()

    def test_refused_reserve_creates_no_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source, output = root/'registry.json', root/'export'
            source.write_text(json.dumps(registry()))
            result = type('Guard', (), {'returncode': 0, 'stdout': '{"allowed":false}'})()
            with patch.object(fleet, 'build', return_value={'design': {}, 'bounds': [0]*6, 'rooms': [], 'key': 'resolute-wren'}), \
                    patch.object(fleet, 'structure_nbt', return_value=b'fixture'), \
                    patch.object(fleet.subprocess, 'run', return_value=result):
                with self.assertRaisesRegex(UserError, 'passing ReserveGuard'):
                    fleet.export(source, output, ['resolute-wren'])
            self.assertFalse(output.exists())


if __name__ == '__main__':
    unittest.main()
