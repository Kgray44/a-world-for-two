import copy
import unittest

from control_room.common import UserError
from tools.worldgen_refinement import SPACING
from tools.worldgen_results import compare, intersects


def fixture(arm, phase):
    """Synthetic source fixture only. Never written under evidence/."""
    return {'format': 'awft-native-worldgen-survey:1', 'arm': arm, 'phase': phase,
        'status': 'OBSERVATIONS_COMPLETE_NORMAL_STOP_AND_RESTART_STILL_REQUIRED',
        'qa_class_sha256': 'fixture-class', 'seed_sha256': 'fixture-seed', 'min_y': -64, 'height': 384,
        'registry': [{'id': k, 'encoded': {'placement': {'spacing': v[arm == 'updated']}}} for k, v in sorted(SPACING.items())],
        'chunks': [{'chunk': [0, 0], 'full_chunk_wall_nanoseconds': 1000000,
                    'observation_processing_nanoseconds': 2000000, 'block_states_sha256': 'fixture-blocks',
                    'world_surface': [64], 'ocean_floor': [64], 'actual_saved_starts': []}],
        'observed_tick_nanoseconds': [100000000, 20000000]}


class WorldgenResultsTests(unittest.TestCase):
    def run_comparison(self, reports=None):
        reports = reports or [fixture('baseline', 'full'), fixture('updated', 'full'),
                              fixture('baseline', 'restart'), fixture('updated', 'restart')]
        return compare(*reports, 'fixture-class')

    def test_scoped_observations_cannot_become_an_acceptance_pass(self):
        result = self.run_comparison()
        self.assertEqual(result['status'], 'MEASURED_REQUIRES_ACCEPTANCE_REVIEW')
        self.assertTrue(result['unproved'])
        self.assertEqual(result['arms']['updated']['observed_ticks_over_50ms_including_instrumentation'], 1)

    def test_restart_content_difference_is_preserved(self):
        reports = [fixture('baseline', 'full'), fixture('updated', 'full'),
                   fixture('baseline', 'restart'), fixture('updated', 'restart')]
        reports[-1]['chunks'][0]['block_states_sha256'] = 'changed'
        result = self.run_comparison(reports)
        self.assertEqual(result['arms']['updated']['restart_content_differences_require_review'], [(0, 0)])

    def test_different_seed_missing_chunk_and_unbound_class_fail_closed(self):
        for mutation in (lambda r: r[-1].update(seed_sha256='different'),
                         lambda r: r[-1].update(chunks=[]),
                         lambda r: r[-1].update(qa_class_sha256='other')):
            reports = [fixture('baseline', 'full'), fixture('updated', 'full'),
                       fixture('baseline', 'restart'), fixture('updated', 'restart')]
            mutation(reports)
            with self.assertRaises(UserError):
                self.run_comparison(reports)

    def test_unreviewed_registry_change_and_missing_selected_change_fail(self):
        reports = [fixture('baseline', 'full'), fixture('updated', 'full'),
                   fixture('baseline', 'restart'), fixture('updated', 'restart')]
        reports[1]['registry'][0]['encoded']['placement']['salt'] = 42
        with self.assertRaises(UserError):
            self.run_comparison(reports)
        reports[1]['registry'] = copy.deepcopy(reports[0]['registry'])
        with self.assertRaises(UserError):
            self.run_comparison(reports)

    def test_boxes_must_overlap_in_all_three_axes(self):
        self.assertTrue(intersects([0, 0, 0, 10, 10, 10], [10, 1, 1, 20, 2, 2]))
        self.assertFalse(intersects([0, 0, 0, 10, 10, 10], [1, 11, 1, 2, 20, 2]))


if __name__ == '__main__':
    unittest.main()
