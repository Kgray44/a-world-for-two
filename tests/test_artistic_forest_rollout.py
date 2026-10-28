import unittest

from tools import artistic_forest_rollout as forest


class ForestRolloutTests(unittest.TestCase):
    def bank(self):
        samples = []
        for x in range(0, 65, 8):
            for z in range(-8, 9, 8):
                samples.append({'x': x, 'z': z, 'kind': 'dry',
                    'surface_y': 65+(8 if x == 0 and z == -8 else 0), 'existing_canopy_y': None})
        return {'saved_samples': samples,
            'composition_zones': {'river_fringe': [[8, 65, 0], [56, 65, 0]], 'protected': [], 'rock_or_nonsoil': []}}

    def test_selects_measured_gentle_ground_instead_of_nearest_cliff(self):
        rows = forest.candidates(self.bank(), {'relative_write_bounds': [-3, -5, -3, 3, 11, 3]}, (8, 0), set())
        self.assertEqual(rows[0], (56, 66, 0))

    def test_protected_full_read_perimeter_is_not_truncated_for_a_candidate(self):
        rows = forest.candidates(self.bank(), {'relative_write_bounds': [-3, -5, -3, 3, 11, 3]}, (8, 0), {(67, 0)})
        self.assertNotIn((56, 66, 0), rows)

    def test_complete_known_field_and_five_metre_skirt_reserved(self):
        columns = forest.reserved_plot_columns([{'known_bounds': [10, 60, 20, 12, 90, 22]}])
        self.assertIn((5, 15), columns)
        self.assertIn((17, 27), columns)
        self.assertNotIn((18, 27), columns)

    def test_the_follow_on_species_add_to_the_three_pilot_without_replacing_them(self):
        selected = [r[2] for r in forest.INTENTS]
        self.assertEqual(len(set(selected)), 6)
        self.assertEqual(len(set(selected) | {p[1] for p in forest.pilot.PLOTS}), 9)


if __name__ == '__main__':
    unittest.main()
