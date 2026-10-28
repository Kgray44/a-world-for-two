import unittest
from control_room.common import UserError
from tools.artistic_fountain_intake_settle import EXPECTED, INTAKE, INPUT_PIPE, exact_pair


class FountainIntakeNeighborBoundaryTests(unittest.TestCase):
    def test_exact_existing_pair_keeps_the_real_pipe_BE(self):
        self.assertEqual(exact_pair(dict(EXPECTED), {INPUT_PIPE}), EXPECTED)

    def test_no_different_flow_or_pipe_connection_can_be_admitted(self):
        for pos, value in ((INTAKE, 'minecraft:water[level=8]'),
                           (INPUT_PIPE, EXPECTED[INPUT_PIPE].replace('down=true', 'down=false'))):
            observed = dict(EXPECTED);observed[pos] = value
            with self.subTest(pos=pos), self.assertRaises(UserError):exact_pair(observed, {INPUT_PIPE})

    def test_no_header_or_control_target_can_enter_the_pair(self):
        observed = dict(EXPECTED);observed[(1138, 73, -1129)] = 'minecraft:air'
        with self.assertRaises(UserError):exact_pair(observed, {INPUT_PIPE})

    def test_missing_pipe_BE_or_unexpected_intake_BE_refuses(self):
        for protected in (set(), {INTAKE, INPUT_PIPE}):
            with self.subTest(protected=protected), self.assertRaises(UserError):exact_pair(dict(EXPECTED), protected)
