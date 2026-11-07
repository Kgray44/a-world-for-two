"""Design regressions and refusal paths; none of these is live game evidence."""
from copy import deepcopy
import gzip
import io
import json
from pathlib import Path, PureWindowsPath
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
    # Additional enums from the frozen native1.21.1 export (bridge0.6.29).
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

    def test_mess_ration_locker_survives_bulkheads_and_companionways(self):
        for key in fleet.SPECS:
            names = {json.loads(str(nbtlib.parse_nbt(row['nbt'])['CustomName']))['text']
                     for row in self.documents[key]['block_entities']
                     if 'CustomName' in nbtlib.parse_nbt(row['nbt'])}
            self.assertIn('Mess utensils and rations', names, key)

    def test_waterline_fittings_do_not_create_a_raised_water_source(self):
        for key in fleet.SPECS:
            d = self.documents[key]
            for (_, y, _), state in block_map(d).items():
                if y >= 0:
                    self.assertNotEqual(properties(state).get('waterlogged'), 'true', key)

    def test_new_manual_controls_have_support_on_their_pinned_opposite_face(self):
        back = {'north': (0, 0, 1), 'south': (0, 0, -1), 'east': (-1, 0, 0),
                'west': (1, 0, 0), 'up': (0, -1, 0), 'down': (0, 1, 0)}
        for key in fleet.SPECS:
            cells = block_map(self.documents[key])
            for pos, state in cells.items():
                if fleet.identifier(state) in {'create:hand_crank', 'create:copper_valve_handle'}:
                    neighbor = tuple(a+b for a, b in zip(pos, back[properties(state)['facing']]))
                    self.assertNotEqual(cells.get(neighbor, fleet.AIR), fleet.AIR, (key, pos))

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

    def test_wrong_crank_face_and_load_obstruction_refuse_derrick(self):
        doc = self.documents['resolute-wren']
        for defect in ('crank', 'load'):
            with self.subTest(defect=defect):
                p = fleet.FleetShip(self.registry, fleet.SPECS['resolute-wren'])
                p.blocks = block_map(doc)
                p.fittings = deepcopy(doc['design']['fittings'])
                fitting = next(row for row in p.fittings if row['kind'] == 'stopped cargo derrick')
                if defect == 'crank':
                    p.put(*fitting['local_control'], 'create:hand_crank', facing='west', waterlogged=False)
                else:
                    x, y, z = fitting['load_sweep_bounds'][:3]
                    p.put(x, y, z, 'minecraft:stone_bricks')
                with self.assertRaises(UserError):
                    fleet.derrick_source_check(p)

    def test_a_ladder_without_its_backing_is_refused(self):
        doc = self.documents['resolute-wren']
        p = fleet.FleetShip(self.registry, fleet.SPECS['resolute-wren'])
        p.blocks = block_map(doc)
        p.rooms = doc['rooms']
        x, y, z = doc['design']['emergency_ladder'][2]
        p.put(x+1, y, z, fleet.AIR)
        with self.assertRaisesRegex(UserError, 'ladder lacks full-block backing'):
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
            original_resolve = Path.resolve
            def destination_drive(path, *args, **kwargs):
                # This test targets the AERO guard, independent of CI's /tmp drive.
                # Keep every real read/existence check and all exporter gates intact.
                return PureWindowsPath('D:/awft-guard-fixture') if path == output else original_resolve(path, *args, **kwargs)
            with patch.object(fleet, 'build', return_value={'design': {}, 'bounds': [0]*6, 'rooms': [], 'key': 'resolute-wren'}), \
                    patch.object(fleet, 'structure_nbt', return_value=b'fixture'), \
                    patch.object(Path, 'resolve', destination_drive), \
                    patch.object(fleet.subprocess, 'run', return_value=result) as guard:
                with self.assertRaisesRegex(UserError, 'passing ReserveGuard'):
                    fleet.export(source, output, ['resolute-wren'])
                guard.assert_called_once()
                arguments = guard.call_args.args[0]
                self.assertEqual(arguments[arguments.index('-EstimatedCBytes')+1], '0')
                self.assertEqual(arguments[arguments.index('-EstimatedDBytes')+1], str(fleet.MAX_EXPORT_BYTES))
            self.assertFalse(output.exists())


if __name__ == '__main__':
    unittest.main()
