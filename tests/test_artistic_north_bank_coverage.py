import unittest
from tools.artistic_north_bank_coverage import components,remaining_profiles


class CoverageSubset(unittest.TestCase):
    def test_complete_model_skirt_is_excluded_even_at_the_far_profile_edge(self):
        # Centre10 has9x11 extent6..14/5..15. A model at15,15 still
        # reserves14,15. Checking only its centre would approve a collision.
        self.assertEqual(remaining_profiles([(10,10),(40,10)],{(15,15)}),[(40,10)])

    def test_actual_air_reservations_are_indistinguishable_from_solids_here(self):
        self.assertEqual(remaining_profiles([(10,10)],{(10,10)}),[])

    def test_diagonal_land_patches_are_not_merged_through_a_missing_column(self):
        self.assertEqual(sorted(map(len,components({(0,0),(1,0),(2,1)}))),[1,2])


if __name__=='__main__':unittest.main()
