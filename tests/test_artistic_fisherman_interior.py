"""Small synthetic admission/circulation tests; native art/use is a separate gate."""
import json
import unittest

from control_room.common import UserError
from tools.artistic_fisherman_interior import (
    AIR, DOORS, Byte, Interior, construct, native_members, snbt, validate,
)


class Props(dict):
    # Deliberately synthetic. Real prepare() validates every state against the
    # actual exported registry; these tests target ownership and circulation.
    def __contains__(self, name):
        return True

    def __getitem__(self, name):
        return ['true', 'false', 'x', 'y', 'z', 'north', 'south', 'east', 'west',
                'bottom', 'top', 'straight', 'single', 'brown', 'none', 'andesite',
                'tray', '0', '1', '2', '3', '4']


class Blocks(dict):
    def get(self, name, default=None):
        return Props()


class Snapshot:
    def __init__(self):
        self.protected = set()
        self.overrides = {(1319, 74, -1330): 'minecraft:prismarine_bricks',
                          (1321, 64, -1336): 'minecraft:short_grass',
                          (1322, 64, -1334): 'minecraft:tall_grass[half=lower]',
                          (1322, 65, -1334): 'minecraft:tall_grass[half=upper]'}

    def state(self, pos):
        if pos in self.overrides:
            return self.overrides[pos]
        x, y, z = pos
        if 1319 <= x <= 1326 and -1339 <= z <= -1329 and y == 63:
            return 'minecraft:grass_block'
        if y == 62:
            return 'minecraft:dirt'
        if (x, 64, z) in DOORS and y in (64, 65):
            return 'minecraft:spruce_door[half=' + ('lower' if y == 64 else 'upper') + ']'
        if (x in (1318, 1327) or z in (-1340, -1328)) and 64 <= y <= 74:
            return 'minecraft:spruce_planks'
        return AIR


def interior(snapshot=None):
    registry = {'blocks': Blocks(), 'items': ['minecraft:' + v for v in (
        'cod', 'salmon', 'paper', 'fishing_rod', 'string', 'coal', 'potato', 'bread', 'shears', 'leather', 'flint_and_steel')] + ['farmersdelight:iron_knife'],
        'seed': 'synthetic', 'world_path': 'synthetic-only'}
    return Interior(registry, snapshot or Snapshot(), {(1318, 64, -1334): 'minecraft:spruce_planks'})


class FishermanInteriorTests(unittest.TestCase):
    def test_complete_scenes_preserve_through_aisle_and_loft_headroom(self):
        p = construct(interior())
        proof = validate(p)
        self.assertEqual(proof['old_block_entity_tags_replayed'], 0)
        self.assertEqual(len(p.scenes), 4)
        self.assertEqual(proof['warm_lanterns'], 6)
        self.assertEqual(proof['actual_workstation_blocks'], 7)
        for pos in p.body:
            self.assertEqual(p.at(pos), AIR)
        # The low stair is approached from an actual interior floor, not from
        # the original wall immediately outside a wrongly placed first step.
        for x in (1324, 1325, 1326):
            self.assertEqual(p.at((x, 64, -1339)), AIR)
        self.assertIn('facing=south', p.blocks[1325, 64, -1338])

    def test_unknown_player_object_and_old_default_be_refuse(self):
        for protect in (False, True):
            snapshot = Snapshot()
            if protect:
                snapshot.protected.add((1319, 64, -1337))
            else:
                snapshot.overrides[1319, 64, -1337] = 'minecraft:chest'
            with self.subTest(protect=protect), self.assertRaises(UserError):
                construct(interior(snapshot))

    def test_original_occupied_cell_is_not_an_interior_clearance_permission(self):
        p = interior()
        p.original[1325, 64, -1333] = 'minecraft:barrel'
        with self.assertRaisesRegex(UserError, 'Preserve every original'):
            construct(p)

    def test_existing_roof_obstruction_refuses_stair_headroom(self):
        snapshot = Snapshot()
        snapshot.overrides[1326, 72, -1332] = 'minecraft:prismarine_bricks'
        p = construct(interior(snapshot))
        with self.assertRaisesRegex(UserError, 'stair lacks measured headroom'):
            validate(p)

    def test_floor_cannot_be_raised_into_original_doors(self):
        p = interior()
        with self.assertRaises(UserError):
            p.put((1322, 64, -1339), 'minecraft:spruce_planks', floor=True)

    def test_native_station_fronts_are_not_filled_by_adjacent_furniture(self):
        p = construct(interior())
        # Smoker, wash-water and cabinet share an unobstructed real service
        # aisle; stove/pot and separate crafting bench have their own approach.
        for x, z in ((1325, -1331), (1325, -1330), (1325, -1329),
                     (1324, -1333), (1320, -1333), (1322, -1336), (1322, -1334)):
            for y in (64, 65):
                self.assertEqual(p.at((x, y, z)), AIR)

    def test_phase2_before_is_actual_explicit_phase1_air_not_old_weeds(self):
        p = construct(interior()); validate(p)
        members = {name: json.loads(raw) for name, raw in native_members(p, 'a' * 64).items()}
        def cells(name):
            row = members[name]
            return {(x, y, z): row['palette'][i] for x, y, z, i in row['blocks']}
        target = 1321, 64, -1336
        self.assertEqual(cells('initial-ALL-TARGETS-before.json')[target], 'minecraft:short_grass')
        self.assertEqual(cells('01-flush-floor-supported-loft-stair.json')[target], AIR)
        self.assertEqual(cells('02-EXPECTED-after-phase1-before-phase2.json')[target], AIR)
        self.assertIn('handcrafted:spruce_counter', cells('02-fish-counter-kitchen-cozy-loft.json')[target])
        for row in members.values():
            self.assertEqual(row['format'], 'awft-native-settlement:1')
            self.assertEqual(len(row['bounds']), 4)
            self.assertLessEqual(row['bounds'][2] - row['bounds'][0], 512)
            self.assertLessEqual(row['bounds'][3] - row['bounds'][1], 512)
            self.assertFalse(row['commands'])
            for be in row['block_entities']:
                self.assertIsInstance(be['nbt'], str)
        for name, row in members.items():
            self.assertEqual(row['construction_forbidden'], name not in (
                '01-flush-floor-supported-loft-stair.json', '02-fish-counter-kitchen-cozy-loft.json'))

    def test_literal_inventory_types_distinguish_native_container_families(self):
        p = construct(interior())
        vanilla = snbt(p.tags[1319, 64, -1335])
        board = snbt(p.tags[1321, 65, -1336])
        self.assertIn('"Slot":0b', vanilla)
        self.assertIn('"Slot":0,', board)
        self.assertNotIn('"Slot":0b', board)
        self.assertIn('"Size":1', board)
        self.assertIn('"count":1', board)
        self.assertIn('"IsItemCarved":0b', board)
        with self.assertRaises(UserError):
            snbt(Byte(128))
        with self.assertRaises(UserError):
            snbt(1.5)


if __name__ == '__main__':
    unittest.main()
