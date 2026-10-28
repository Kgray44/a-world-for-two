import unittest

from control_room.common import UserError
from tools import artistic_woodland_habitats as life


class HabitatSave:
    def __init__(self, changes=None, unknown=None, shore=False):
        self.changes = changes or {}
        self.unknown = unknown
        self.shore = shore

    def column(self, x, z):
        if self.shore:
            if x <= 0:
                return {'kind': 'water', 'surface_y': 62, 'state': 'minecraft:water[level=0]'}
            return {'kind': 'dry', 'surface_y': 63 if x <= 2 else 64, 'state': 'minecraft:sand'}
        return {'kind': 'dry', 'surface_y': 65, 'state': 'minecraft:grass_block[snowy=false]'}

    def state(self, x, y, z):
        p = x, y, z
        if p == self.unknown:
            return None
        if p in self.changes:
            return self.changes[p]
        if self.shore:
            if x <= 0:
                return 'minecraft:water[level=0]' if 60 <= y <= 62 else 'minecraft:air'
            return 'minecraft:sand' if y == (63 if x <= 2 else 64) else 'minecraft:air'
        return 'minecraft:grass_block[snowy=false]' if y == 65 else 'minecraft:air'


class WoodlandHabitatTests(unittest.TestCase):
    def test_complete_actual_field_not_a_45_cell_dry_proxy(self):
        site, field, nature = life.dry_site(HabitatSave(), (0, 0), 'AIR', 'grass', set())
        self.assertEqual(len(field), 392)
        self.assertEqual(site['feet'], [.5, 66, .5])
        self.assertGreater(nature['grass'], 0)

    def test_unknown_far_perimeter_and_current_controls_refuse(self):
        with self.assertRaisesRegex(UserError, 'saved FULL'):
            life.dry_site(HabitatSave(unknown=(3, 71, 3)), (0, 0), 'AIR', 'grass', set())
        with self.assertRaisesRegex(UserError, 'mechanisms'):
            life.dry_site(HabitatSave(), (0, 0), 'DRY', 'grass', {(2, 2)})

    def test_unplanted_future_leaf_or_flower_habitat_is_not_claimed_present(self):
        for nature in ('leaves', 'flowers'):
            with self.subTest(nature=nature), self.assertRaisesRegex(UserError, 'not present'):
                life.dry_site(HabitatSave(), (0, 0), 'AIR', nature, set())
        changes = {(-3, 69, z): 'minecraft:oak_leaves[distance=1,persistent=false,waterlogged=false]' for z in (-1, 0, 1)}
        _, _, facts = life.dry_site(HabitatSave(changes), (0, 0), 'AIR', 'leaves', set())
        self.assertEqual(facts['leaves'], 3)

    def test_retained_body_obstruction_is_not_deleted(self):
        with self.assertRaisesRegex(UserError, 'Retained object'):
            life.dry_site(HabitatSave({(1, 67, 1): 'minecraft:oak_log[axis=y]'}), (0, 0), 'AIR', 'grass', set())

    def test_real_three_step_shore_exit_and_source_water_preserved(self):
        site, field, reeds = life.shore_site(HabitatSave(shore=True), -1, 0, set(), {(0, 0), (8, 0)})
        self.assertEqual(len(site['habitat']['shore_path']), 3)
        self.assertEqual(site['habitat']['water_bounds'], [-2, 61, -1, 0, 62, 1])
        self.assertEqual(reeds, 0)
        for a, b in zip(site['habitat']['shore_path'], site['habitat']['shore_path'][1:]):
            self.assertLessEqual(abs(a[1]-b[1]), 1)
        self.assertTrue(all(value is not None for value in field.values()))

    def test_disabled_naturalist_dragonfly_is_not_used_as_the_selected_mod_alias(self):
        chosen = {row[1] for row in life.INTENTS}
        self.assertIn('crittersandcompanions:dragonfly', chosen)
        self.assertNotIn('naturalist:dragonfly', chosen)


if __name__ == '__main__':
    unittest.main()
