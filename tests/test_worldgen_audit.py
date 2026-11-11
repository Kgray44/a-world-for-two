import unittest

from control_room.common import UserError
from tools.worldgen_audit import JavaRandom, ResourceIndex, grid_candidates


class WorldgenAuditTests(unittest.TestCase):
    def test_java_random_known_values_and_large_rejection_bound(self):
        random = JavaRandom(0)
        self.assertEqual([random.next_int(100) for _ in range(5)], [60, 48, 29, 47, 15])
        random = JavaRandom(0)
        self.assertEqual([random.next_int(1073741825) for _ in range(3)],
                         [516548029, 663681053, 251269761])

    def test_negative_grid_edges_use_floor_division(self):
        placement = {'type': 'minecraft:random_spread', 'spacing': 80,
                     'separation': 40, 'salt': 7}
        points = grid_candidates(-12345678912345, placement, (-256, -256))
        self.assertEqual(points, grid_candidates(-12345678912345, placement, (-256, -256)))
        self.assertTrue(all(-256 <= x < 256 and -256 <= z < 256 for x, z in points))
        self.assertTrue(any(x < 0 and z < 0 for x, z in points))
        self.assertEqual(len({(x // 80, z // 80) for x, z in points}), len(points))

    def test_custom_and_frequency_reduced_grids_are_not_misrepresented(self):
        for placement in ({'type': 'moogs_structures:advanced_random_spread'},
                          {'type': 'minecraft:random_spread', 'frequency': .5}):
            with self.assertRaises(UserError):
                grid_candidates(1, placement, (0, 0))

    def test_required_optional_nested_and_replace_tags(self):
        index = ResourceIndex()
        index.add('data/regions_unexplored/worldgen/biome/bayou.json', {}, 'ru')
        index.add('data/c/tags/worldgen/biome/is_swamp.json',
                  {'values': ['regions_unexplored:bayou', {'id': 'missing:optional', 'required': False}]}, 'ru')
        index.add('data/awft/tags/worldgen/biome/swamp.json',
                  {'values': ['#c:is_swamp', 'missing:required']}, 'awft')
        self.assertEqual(index.biomes('#awft:swamp'),
                         ({'regions_unexplored:bayou'}, {'missing:required'}))
        index.add('data/c/tags/worldgen/biome/is_swamp.json', {'replace': True, 'values': []}, 'new')
        self.assertEqual(index.biomes('#c:is_swamp'), (set(), set()))

    def test_cycle_fails_instead_of_claiming_biome_coverage(self):
        index = ResourceIndex()
        index.add('data/a/tags/worldgen/biome/a.json', {'values': ['#a:b']}, 'a')
        index.add('data/a/tags/worldgen/biome/b.json', {'values': ['#a:a']}, 'a')
        with self.assertRaises(UserError):
            index.biomes('#a:a')


if __name__ == '__main__':
    unittest.main()
