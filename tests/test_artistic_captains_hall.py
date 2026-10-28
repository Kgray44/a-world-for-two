"""Pure proposal/safety tests; actual art and interaction require Minecraft."""
import json
import unittest

from control_room.common import UserError
from tools.artistic_captains_hall import (
    AIR, Hall, admit_saved_target, build, native_payload, validate,
)


class Props(dict):
    def __contains__(self, name):
        return True

    def __getitem__(self, name):
        return [str(v) for v in range(17)] + ['true', 'false', 'x', 'y', 'z',
            'north', 'south', 'east', 'west', 'bottom', 'top', 'straight', 'single',
            'brown', 'gray', 'none', 'andesite', 'lower', 'upper', 'left', 'right',
            'head', 'foot', 'locked', 'switched_0', 'tray']

    def get(self, name, default=None):
        return self[name]


class Blocks(dict):
    def get(self, name, default=None):
        return Props()


def registry():
    # Synthetic properties isolate structure/ownership tests. Actual prepare()
    # separately resolves every state against the native exported registry.
    return {'blocks': Blocks(), 'items': ['minecraft:' + n for n in (
        'bread', 'potato', 'coal', 'cod', 'string', 'paper')],
        'seed': 'synthetic', 'world_path': 'synthetic-only'}


class CaptainsHallTests(unittest.TestCase):
    def test_one_composed_hall_has_rooted_levels_and_real_stair_headroom(self):
        p = build(registry())
        proof = validate(p)
        self.assertEqual(proof['solid_positions'], proof['rooted_solid_positions'])
        self.assertEqual(proof['rooms'], 4)
        self.assertEqual(proof['warm_lights'], 11)
        for pos in p.body:
            self.assertEqual(p.blocks[pos], AIR)
        self.assertNotEqual(p.blocks[8, 12, 12], AIR)  # no open gable/eaves gap
        self.assertEqual(p.blocks[13, 1, 10].split('[')[0], 'minecraft:dark_oak_stairs')

    def test_real_stair_overhead_obstruction_refuses(self):
        p = build(registry())
        p.blocks[13, 5, 7] = 'minecraft:stone'
        with self.assertRaisesRegex(UserError, 'stair has blocked headroom'):
            validate(p)

    def test_facade_cannot_silently_fill_reserved_walk(self):
        p = build(registry())
        with self.assertRaisesRegex(UserError, 'walking route'):
            p.put(6, 1, 8, 'minecraft:stone', replace=True)

    def test_natural_hollow_has_no_new_foundation_or_water_fill(self):
        p = build(registry())
        for x in (8, 9):  # actual1042/1043,Z−1277: known air below old gravel
            self.assertNotIn((x, 16), p.footprint)
            self.assertNotIn((x, 0, 16), p.blocks)
        self.assertTrue(all(not value.startswith('minecraft:water[') for value in p.blocks.values()))
        self.assertIn((3, 1, 16), p.body)  # left exit, on measured stable terrain

    def test_saved_before_requires_real_dry_ground_and_preserves_unknown_objects(self):
        pos = (1042, 63, -1285)
        admit_saved_target(pos, 'minecraft:gravel', protected=False, foundation=True, below='minecraft:stone')
        for beneath in ('minecraft:water[level=0]', AIR):
            with self.subTest(beneath=beneath), self.assertRaises(UserError):
                admit_saved_target(pos, 'minecraft:gravel', protected=False, foundation=True, below=beneath)
        for old, protected in (('minecraft:barrel', False), (AIR, True), ('minecraft:oak_log', False)):
            with self.subTest(old=old, protected=protected), self.assertRaises(UserError):
                admit_saved_target((1042, 64, -1285), old, protected=protected, foundation=False)

    def test_verification_members_cannot_be_replayed_and_tags_are_literal_snbt(self):
        r = registry(); p = build(r)
        blocks = {(x + 1034, y + 63, z - 1293): value for (x, y, z), value in p.blocks.items()}
        tags = {(x + 1034, y + 63, z - 1293): value for (x, y, z), value in p.tags.items()}
        row = json.loads(native_payload(r, blocks, 'a' * 64, 'Synthetic verify', tags=tags))
        self.assertTrue(row['construction_forbidden'])
        self.assertEqual(len(row['bounds']), 4)
        self.assertFalse(row['commands'])
        self.assertTrue(all(isinstance(be['nbt'], str) for be in row['block_entities']))
        barrel = next(be['nbt'] for be in row['block_entities'] if 'Items' in be['nbt'])
        self.assertIn('"Slot":0b', barrel)
        self.assertIn('"count":', barrel)
        self.assertFalse(json.loads(native_payload(r, blocks, 'a' * 64, 'Synthetic new proposal', placement=True))['construction_forbidden'])


if __name__ == '__main__':
    unittest.main()
