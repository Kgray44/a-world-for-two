"""Botanical components against tiny explicit state/shape fixtures, no world."""
from unittest import TestCase

from control_room.common import UserError
from tools.artistic_botanical import (Garden, FLOWERS, POTS, berry_bracket, cherry_bough,
    check_authored_owners, glowberry_pendant, hedge_pocket, meadow_pocket,
    palette_proof, potted_cluster, source_candidates, wall_climber, wall_hanging_climber, window_tray)


def registry():
    blocks = {name: {} for name in (*FLOWERS, *POTS, 'minecraft:fern', 'minecraft:coarse_dirt')}
    for name in ('minecraft:stripped_dark_oak_log', 'minecraft:dark_oak_log',
                 'chipped:carved_stripped_dark_oak_log'):
        blocks[name] = {'axis': ['x', 'y', 'z']}
    blocks['minecraft:vine'] = {key: ['true', 'false'] for key in ('east', 'west', 'north', 'south', 'up')}
    blocks['minecraft:cave_vines'] = {'age': [str(n) for n in range(26)], 'berries': ['true', 'false']}
    blocks['minecraft:cave_vines_plant'] = {'berries': ['true', 'false']}
    blocks['minecraft:spruce_stairs'] = {'facing': ['east', 'west', 'north', 'south'],
        'half': ['top'], 'shape': ['straight'], 'waterlogged': ['false']}
    for name in ('minecraft:spruce_trapdoor', 'minecraft:dark_oak_trapdoor'):
        blocks[name] = {'facing': ['east', 'west', 'north', 'south'], 'half': ['bottom'],
                        'open': ['true'], 'powered': ['false'], 'waterlogged': ['false']}
    for name in ('mcwfences:azalea_hedge', 'mcwfences:flowering_azalea_hedge', 'mcwfences:cherry_hedge'):
        blocks[name] = {key: ['true', 'false'] for key in ('east', 'west', 'north', 'south', 'waterlogged')}
    for name in ('minecraft:cherry_leaves', 'minecraft:flowering_azalea_leaves'):
        blocks[name] = {'distance': [str(n) for n in range(1, 8)], 'persistent': ['true'], 'waterlogged': ['false']}
    return {'blocks': blocks}


def garden(actual=None, reserved=None, bes=None):
    actual = actual or {}
    return Garden(registry(), lambda pos: actual.get(pos, 'minecraft:air'),
                  bes or set(), reserved or set(), set())


class BotanicalContracts(TestCase):
    def test_window_tray_has_actual_wall_roots_and_no_window_height_targets(self):
        walls = {(x, y, 0): 'minecraft:spruce_planks' for x in (-1, 0, 1) for y in (64, 65)}
        g = garden(walls)
        window_tray(g, 'house', (0, 65, 0), 'south')
        self.assertEqual(len(g.blocks), 14)
        self.assertEqual(len(g.roots), 6)
        self.assertTrue(all(pos[1] < 67 for pos in g.blocks))
        self.assertEqual(g.blocks[(0, 65, 1)], 'minecraft:coarse_dirt')

    def test_fancy_window_or_unknown_shape_is_never_a_sturdy_root(self):
        for name in ('mcwwindows:spruce_four_window', 'minecraft:glass', None):
            g = garden({(0, 64, 0): name})
            with self.assertRaises(UserError):
                potted_cluster(g, 'house', [(0, 65, 0)], palette=[POTS[0]])
            self.assertFalse(g.blocks)

    def test_atomic_scene_refusal_keeps_no_half_tray_or_hidden_root_witness(self):
        walls = {(x, y, 0): 'minecraft:spruce_planks' for x in (-1, 0, 1) for y in (64, 65)}
        g = garden(walls, reserved={(1, 66, 1)})
        with self.assertRaises(UserError):
            window_tray(g, 'house', (0, 65, 0), 'south')
        self.assertFalse(g.blocks); self.assertFalse(g.previous); self.assertFalse(g.roots)

    def test_wall_climber_checks_every_full_wall_face_and_ground_root(self):
        actual = {(0, y, 0): 'minecraft:stone_bricks' for y in range(65, 71)}
        actual[(0, 64, 1)] = 'minecraft:grass_block'
        g = garden(actual); wall_climber(g, 'house', (0, 65, 1), 'south')
        self.assertEqual(len(g.blocks), 6)
        self.assertTrue(all('north=true' in value for value in g.blocks.values()))
        actual[(0, 68, 0)] = 'minecraft:glass'
        g = garden(actual)
        with self.assertRaises(UserError):
            wall_climber(g, 'house', (0, 65, 1), 'south')
        self.assertFalse(g.blocks)

    def test_glowberry_chain_is_attached_above_and_has_a_mature_tip(self):
        g = garden({(0, 71, 0): 'minecraft:oak_log[axis=x]'})
        glowberry_pendant(g, 'house', (0, 70, 0), length=3)
        self.assertEqual(g.blocks[(0, 68, 0)], 'minecraft:cave_vines[age=25,berries=true]')
        with self.assertRaises(UserError):
            glowberry_pendant(garden(), 'house', (0, 70, 0))

    def test_hanging_ivy_uses_real_side_support_without_inventing_a_ground_root(self):
        actual = {(0, y, 0): 'minecraft:stone_bricks' for y in range(65, 71)}
        g = garden(actual)
        wall_hanging_climber(g, 'house', (0, 65, 1), 'south')
        self.assertEqual(len(g.blocks), 6)
        self.assertNotIn((0, 64, 1), g.roots)
        self.assertTrue(all('north=true' in value for value in g.blocks.values()))
        actual[(0, 68, 0)] = 'minecraft:glass'
        g = garden(actual)
        with self.assertRaises(UserError):
            wall_hanging_climber(g, 'house', (0, 65, 1), 'south')
        self.assertFalse(g.blocks)

    def test_new_berry_bracket_has_two_saved_wall_roots_and_clear_outboard_vines(self):
        g = garden({(0, 73, 0): 'minecraft:dark_oak_planks',
                    (0, 72, 0): 'minecraft:dark_oak_planks'})
        berry_bracket(g, 'house', (0, 73, 0), 'south')
        self.assertEqual(len(g.roots), 2)
        self.assertEqual(g.blocks[(0, 73, 2)], 'minecraft:dark_oak_log[axis=z]')
        self.assertEqual(g.blocks[(0, 70, 2)], 'minecraft:cave_vines[age=25,berries=true]')
        self.assertFalse((0, 71, 1) in g.blocks)
        g = garden({(0, 73, 0): 'minecraft:dark_oak_planks',
                    (0, 72, 0): 'minecraft:dark_oak_planks'}, reserved={(0, 71, 2)})
        with self.assertRaises(UserError):
            berry_bracket(g, 'house', (0, 73, 0), 'south')
        self.assertFalse(g.blocks)

    def test_sculpted_crown_has_real_log_paths_and_authored_material_checks(self):
        g = garden({(0, 64, 0): 'minecraft:grass_block'})
        cherry_bough(g, 'arch', (0, 65, 0), 'east')
        leaves = [value for value in g.blocks.values() if '_leaves[' in value]
        self.assertEqual(len(leaves), 12)
        self.assertTrue(all('persistent=true' in value and 'distance=7' not in value for value in leaves))
        checks, outdoor = check_authored_owners(g, {'arch': {}})
        self.assertEqual(checks[0]['violations'], []); self.assertEqual(outdoor['violations'], [])

    def test_hedges_and_meadow_do_not_treat_roof_or_stone_as_soil(self):
        actual = {(x, 64, z): 'minecraft:grass_block' for x in range(3) for z in range(3)}
        g = garden(actual); hedge_pocket(g, 'garden', (0, 65, 0), 'south')
        self.assertEqual(len(g.blocks), 3)
        g = garden(actual); meadow_pocket(g, 'garden', (0, 65, 0))
        self.assertEqual(len(g.blocks), 5)
        with self.assertRaises(UserError):
            hedge_pocket(garden({(0, 64, 0): 'minecraft:stone'}), 'garden', (0, 65, 0), 'south')

    def test_existing_inventory_and_missing_whole_owner_never_become_exemptions(self):
        g = garden({(0, 64, 0): 'minecraft:stone'}, bes={(0, 65, 0)})
        with self.assertRaises(UserError):
            potted_cluster(g, 'house', [(0, 65, 0)], palette=[POTS[0]])
        g = garden({(0, 64, 0): 'minecraft:stone'})
        potted_cluster(g, 'house', [(0, 65, 0)], palette=[POTS[0]])
        with self.assertRaises(UserError):
            check_authored_owners(g, {})
        self.assertTrue(palette_proof(registry()))

    def test_json_position_arrays_are_supported_but_noninteger_positions_refuse(self):
        g = garden({(0, 64, 0): 'minecraft:stone'})
        potted_cluster(g, 'house', [[0, 65, 0]], palette=[POTS[0]])
        self.assertIn((0, 65, 0), g.blocks)
        with self.assertRaises(UserError):
            potted_cluster(garden(), 'house', [[0, 65.0, 0]], palette=[POTS[0]])

    def test_source_composer_uses_real_window_support_and_retains_pending_status(self):
        wall = {(x, y, 0): 'minecraft:spruce_planks' for x in (-1, 0, 1) for y in (64, 65)}
        wall[(0, 67, 0)] = 'mcwwindows:spruce_four_window'
        result = source_candidates('house', wall, limit=4)
        trays = [r for r in result if r['kind'] == 'window_tray']
        self.assertEqual(len(trays), 1)
        self.assertIn('PENDING', trays[0]['saved_admission'])
        wall[(0, 65, 0)] = 'minecraft:glass'
        self.assertFalse([r for r in source_candidates('house', wall, limit=4) if r['kind'] == 'window_tray'])
