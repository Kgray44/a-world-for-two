import unittest

from control_room.common import UserError
from tools.artistic_fountain_runoff_cleanup import TARGETS, BEFORE_STATE, exact_runoff


class FountainRunoffBoundaryTests(unittest.TestCase):
    def field(self):
        base = {p: 'minecraft:air' for p in TARGETS}
        base[(1138, 73, -1129)] = 'minecraft:air'  # retained header
        actual = dict(base);actual.update({p: BEFORE_STATE for p in TARGETS})
        return base, actual

    def test_only_exact_two_falling_cells_reach_the_delta(self):
        base, actual = self.field()
        self.assertEqual(exact_runoff(base, actual, set()), {p: BEFORE_STATE for p in TARGETS})

    def test_sources_other_flow_levels_and_missing_runoff_refuse(self):
        for value in ('minecraft:water[level=0]', 'minecraft:water[level=7]', 'minecraft:air'):
            base, actual = self.field();actual[next(iter(TARGETS))] = value
            with self.subTest(value=value), self.assertRaises(UserError):
                exact_runoff(base, actual, set())

    def test_a_foreign_header_change_or_unknown_field_refuses(self):
        base, actual = self.field();actual[(1138, 73, -1129)] = 'minecraft:water[level=0]'
        with self.assertRaises(UserError):exact_runoff(base, actual, set())
        base, actual = self.field();actual.pop((1138, 73, -1129))
        with self.assertRaises(UserError):exact_runoff(base, actual, set())

    def test_any_target_BE_is_preserved(self):
        base, actual = self.field()
        with self.assertRaises(UserError):exact_runoff(base, actual, {next(iter(TARGETS))})

    def test_observed_noncritical_native_joins_are_retained_but_critical_changes_refuse(self):
        base, actual = self.field();q = (1136, 66, -1130)
        base[q] = 'dawnoftimebuilder:marble_sided_column[facing=west,vertical_connection=both,waterlogged=false]'
        actual[q] = 'dawnoftimebuilder:marble_sided_column[facing=west,vertical_connection=above,waterlogged=false]'
        self.assertEqual(set(exact_runoff(base, actual, set())), TARGETS)
        actual[q] = actual[q].replace('facing=west', 'facing=east')
        with self.assertRaises(UserError):exact_runoff(base, actual, set())
