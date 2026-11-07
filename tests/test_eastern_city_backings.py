import unittest

from tools.eastern_city_backings import outside_backings, ordered_dependencies


class EasternCityBackingsTests(unittest.TestCase):
    def test_new_final_fixture_over_captured_air_is_not_copied(self):
        result = outside_backings({(0, 3, 0): 'minecraft:air'}, [10, 64, 10],
                                  [10, 64, 10, 11, 67, 11],
                                  {(10, 67, 10): {(10, 68, 10)}})
        self.assertEqual(result, {})

    def test_real_hanging_lantern_requires_literal_external_ceiling(self):
        result = outside_backings({(0, 3, 0): 'minecraft:lantern[hanging=true,waterlogged=false]'},
                                  [10, 64, 10], [10, 64, 10, 11, 67, 11], {})
        self.assertEqual(set(result), {(10, 68, 10)})
        self.assertEqual(result[(10, 68, 10)][0]['source_support_position'], [0, 4, 0])

    def test_internal_floor_and_external_wall_support_are_distinct(self):
        source = {(0, 1, 0): 'minecraft:lantern[hanging=false,waterlogged=false]',
                  (0, 2, 0): 'minecraft:spruce_wall_sign[facing=east,waterlogged=false]'}
        result = outside_backings(source, [10, 64, 10], [10, 64, 10, 11, 67, 11], {})
        self.assertEqual(set(result), {(9, 66, 10)})

    def test_backing_dependencies_cannot_silently_create_cycle(self):
        base = {'a': [], 'b': ['a'], 'c': []}
        records = [{'capsule_id': 'a', 'required_conserved_source_or_destination_ids': ['b']}]
        ordered, holds = ordered_dependencies(base, records)
        self.assertEqual(ordered, ['c'])
        self.assertEqual(holds, {'a': ['b'], 'b': ['a']})


if __name__ == '__main__':
    unittest.main()
