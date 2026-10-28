import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from control_room.common import UserError
from tools import artistic_dense_canopies as trees


class SavedTreeField:
    def __init__(self, changes=None, unknown=None, entities=()):
        self.changes = changes or {}
        self.unknown = unknown
        self.entities = set(entities)

    def column(self, x, z):
        return {'kind': 'dry', 'surface_y': 65}

    def state(self, x, y, z):
        pos = x, y, z
        if pos == self.unknown:
            return None
        return self.changes.get(pos, 'minecraft:grass_block[snowy=false]' if y == 65 else 'minecraft:air')


class DenseCanopyTests(unittest.TestCase):
    q = {'relative_write_bounds': [-3, -5, -3, 3, 11, 3]}

    def review(self, saved, protected=(), entities=()):
        return trees.saved_plot(saved, self.q, (0, 66, 0), set(protected), list(entities))

    def test_real_tree_cells_in_read_only_perimeter_are_preserved_and_allowed(self):
        leaf = 'minecraft:oak_leaves[distance=1,persistent=false,waterlogged=false]'
        field, write, known, count = self.review(SavedTreeField({(10, 70, 0): leaf}))
        self.assertEqual(count, 1)
        self.assertEqual(field[10, 70, 0], leaf)
        self.assertGreater(10, write[3])
        self.assertLessEqual(10, known[3])

    def test_tree_or_be_inside_actual_write_volume_is_never_cleared(self):
        for saved in (SavedTreeField({(3, 70, 0): 'minecraft:oak_log[axis=y]'}),
                      SavedTreeField(entities={(3, 65, 0)})):
            with self.subTest(saved=saved), self.assertRaisesRegex(UserError, 'Retain existing tree/BE'):
                self.review(saved)

    def test_exact_north_or_future_route_column_rejects_whole_write_crown(self):
        with self.assertRaisesRegex(UserError, 'retained building/AIR/route'):
            self.review(SavedTreeField(), protected={(3, 0)})

    def test_unknown_far_read_corner_is_not_synthesized_air(self):
        with self.assertRaisesRegex(UserError, 'saved FULL'):
            self.review(SavedTreeField(unknown=(11, 81, 11)))

    def test_pig_objects_and_passengers_are_not_removed_or_ignored(self):
        with self.assertRaisesRegex(UserError, 'Saved resident/passenger/object'):
            self.review(SavedTreeField(), entities=[('minecraft:pig', (1.5, 66.0, .5))])
        field, *_ = self.review(SavedTreeField(), entities=[('minecraft:zombie', (0.0, 20.0, 0.0))])
        self.assertTrue(field)

    def test_overlapping_reads_allowed_but_write_cannot_change_another_before(self):
        a = [-11, 59, -11, 11, 81, 11]
        read2 = [5, 59, -11, 27, 81, 11]
        write2 = [13, 61, -3, 19, 77, 3]
        self.assertTrue(trees.overlap(a, read2))
        self.assertFalse(trees.overlap(a, write2))

    def test_recovery_selection_has_only_six_original_unperformed_roots(self):
        self.assertEqual([row[0] for row in trees.RESUME46_PLOTS],
                         ['copse-40', 'copse-92', 'copse-115', 'copse-158', 'copse-188', 'copse-206'])
        self.assertEqual(trees.RESUME46_PLOTS[0], ('copse-40', 'minecraft:birch_sapling', (950, 143, -905)))
        self.assertNotIn('copse-37', {row[0] for row in trees.RESUME46_PLOTS})
        self.assertTrue(all(row[1] == 'minecraft:birch_sapling' for row in trees.RESUME46_PLOTS))

    def test_recovery_never_defaults_to_the_old_precrash_checkpoint(self):
        with tempfile.TemporaryDirectory() as directory:
            home=Path(directory)
            with patch.object(trees,'guard',side_effect=AssertionError('No writer before explicit checkpoint')):
                with self.assertRaisesRegex(UserError,'explicit new verified recovery checkpoint'):
                    trees.prepare(home,home/'staging/new-source',mode='resume46')


if __name__ == '__main__':
    unittest.main()
