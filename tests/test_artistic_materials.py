"""The owner's one-axis design exception, not a visual-quality acceptance test."""
import unittest

from tools.artistic_materials import (
    material_runs, material_run_report, require_material_rule, require_outdoor_rule,
)


class MaterialPolicy(unittest.TestCase):
    def test_long_three_high_fence_and_roof_edge_are_allowed_and_reported(self):
        for name, block in [('fence', 'minecraft:spruce_fence'),
                            ('roof edge', 'minecraft:dark_oak_stairs[facing=north]')]:
            cells = {(x, y, 0): block for x in range(120) for y in range(3)}
            result = require_material_rule(cells, name)
            self.assertEqual(material_runs(cells), [])
            self.assertEqual(result['one_axis_runs_for_visual_review'][0]['long_runs']['x']['length'], 120)
            self.assertIn('native visual inspection', result['artistic_quality'])

    def test_uniform_four_by_four_wall_still_fails(self):
        cells = {(x, y, 0): 'minecraft:oak_planks' for x in range(4) for y in range(4)}
        with self.assertRaisesRegex(ValueError, 'material run rule'):
            require_material_rule(cells, 'plain wall')

    def test_changing_block_facing_cannot_hide_a_uniform_panel(self):
        cells = {(x, y, 0): 'minecraft:oak_log[axis='+('x' if x%2 else 'y')+']'
                 for x in range(4) for y in range(4)}
        self.assertTrue(material_runs(cells))

    def test_long_outdoor_border_is_allowed_but_broad_plain_field_is_not(self):
        border = {(x, 0, z): 'minecraft:stone_bricks' for x in range(100) for z in range(3)}
        require_outdoor_rule(border, 'quay edge')
        field = {(x, 0, z): 'minecraft:stone_bricks' for x in range(10) for z in range(10)}
        with self.assertRaisesRegex(ValueError, 'outdoor multi-axis'):
            require_outdoor_rule(field, 'plain square')

    def test_air_water_and_small_runs_are_not_material_break_violations(self):
        cells = {(x, 0, 0): 'minecraft:water[level=0]' for x in range(100)}
        cells.update({(0, y, 1): 'minecraft:oak_planks' for y in range(3)})
        self.assertEqual(material_run_report(cells), [])


if __name__ == '__main__':
    unittest.main()
