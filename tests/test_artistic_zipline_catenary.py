"""Small geometry gates; no archive, game, network, or private fixture reads."""
from unittest import TestCase
from unittest.mock import patch
from types import SimpleNamespace

from control_room.common import UserError
from tools.artistic_zipline_catenary import HANG, MIB, NODES, frame, knot, reader_budget, spatial_custody, swept_cells, validate_nodes


class Terrain:
    entities = set()

    def __init__(self, blocked=None, water=False):
        self.blocked = blocked or {}
        self.water = water

    def column(self, x, z):
        return {'kind': 'water' if self.water else 'dry', 'surface_y': 64,
                'state': 'minecraft:grass_block'}

    def state(self, x, y, z):
        return self.blocked.get((x, y, z), 'minecraft:air' if y > 64 else 'minecraft:stone')


def registry():
    blocks = {name: {} for name in ('minecraft:stone_bricks', 'minecraft:chiseled_stone_bricks')}
    for name in ('minecraft:stripped_spruce_log', 'minecraft:stripped_dark_oak_log',
                 'minecraft:dark_oak_log', 'chipped:reinforced_stripped_spruce_log'):
        blocks[name] = {'axis': ['x', 'y', 'z']}
    blocks['minecraft:lantern'] = {'hanging': ['true', 'false'], 'waterlogged': ['false']}
    blocks['minecraft:spruce_fence'] = {key: ['true', 'false'] for key in
                                      ('north', 'south', 'east', 'west', 'waterlogged')}
    blocks['minecraft:dark_oak_stairs'] = {'facing': ['north', 'east', 'south', 'west'],
                                         'half': ['top'], 'shape': ['straight'],
                                         'waterlogged': ['false']}
    blocks['minecraft:weathered_cut_copper_stairs'] = blocks['minecraft:dark_oak_stairs']
    blocks['minecraft:chain'] = {'axis': ['y'], 'waterlogged': ['false']}
    return {'blocks': blocks}


class CatenaryContracts(TestCase):
    def test_exact_north_face_and_local_span_turn_contract(self):
        self.assertEqual(knot((1220, 72, -1272)), [1220.5, 72.5, -1271.75])
        anchors, angles = validate_nodes(NODES)
        self.assertEqual(len(anchors), 15)
        self.assertTrue(all(angle < 45 for angle in angles))
        with self.assertRaises(UserError):
            validate_nodes(((0, 10, 0), (81, 10, 0)))
        with self.assertRaises(UserError):
            validate_nodes(((0, 10, 0), (10, 10, 0), (20, 10, 10)))

    def test_continuous_sweep_covers_the_space_between_samples(self):
        cells = swept_cells([[.9, 10.9, -.1], [1.15, 10.9, -.1]])
        self.assertIn((0, 7, -1), cells)
        self.assertIn((1, 8, 0), cells)
        self.assertNotIn((0, 10, 0), cells)
        with self.assertRaises(UserError):
            swept_cells([[0, 10, 0], [3, 10, 0]])
        with self.assertRaises(UserError):
            swept_cells([[0, 10, 0], [float('nan'), 10, 0]])

    def test_steep_native_endpoint_excerpt_catches_old_anchor_intrusion(self):
        # Sanitized numeric excerpt of the actual pinned ChainCable output.
        # This tests our AABB calculation, not a replacement native API test.
        points = [[1168.5, 159.90000000596046, -783.75],
                  [1168.4259259259259, 159.9631838019047, -783.5277777777778],
                  [1168.351851851852, 160.02673879756514, -783.3055555555555],
                  [1168.2777777777778, 160.09066512596942, -783.0833333333334],
                  [1168.2037037037037, 160.15496292092266, -782.8611111111111],
                  [1168.1296296296296, 160.21963231700732, -782.6388888888889],
                  [1168.0555555555557, 160.2846734495838, -782.4166666666666]]
        self.assertIn((1168, 159, -784), swept_cells(points, 3.0))
        self.assertNotIn((1168, 159, -784), swept_cells(points, HANG))
        self.assertGreater(168.90000000596046 - HANG - .25, 165)

    def test_frame_keeps_measured_roots_and_separate_clear_flight(self):
        blocks, roots, proof = frame(registry(), Terrain(), (0, 96, 0), set(), set(), 'fixture')
        self.assertTrue(roots)
        self.assertTrue(all(p[1] == 64 for p in roots))
        self.assertFalse(blocks.keys() & roots.keys())
        self.assertEqual(proof['material_rule']['violations'], [])
        self.assertIn((0, 96, 0), blocks)

    def test_water_and_saved_be_are_not_footing_exceptions(self):
        with self.assertRaises(UserError):
            frame(registry(), Terrain(water=True), (0, 96, 0), set(), set(), 'water')
        terrain = Terrain()
        terrain.entities = {(x, 66, z) for x, z in
                            [(-2, 0), (2, 0), (-3, 0), (3, 0), (-4, 0), (4, 0),
                             (0, -2), (0, 2), (0, -3), (0, 3), (0, -4), (0, 4)]}
        with self.assertRaises(UserError):
            frame(registry(), terrain, (0, 96, 0), set(), set(), 'BE')

    def test_frame_cannot_erase_or_cover_exact_reserved_player_body(self):
        with self.assertRaises(UserError):
            frame(registry(), Terrain(), (0, 96, 0), {(0, 96, 0)}, set(), 'flight')
        with self.assertRaises(UserError):
            frame(registry(), Terrain(), (0, 96, 0), set(), {(0, 0)}, 'protected')

    def test_bridge_and_retained_mast_are_real_spatial_exclusions_not_boat_acceptance(self):
        for cell in ((1193, 95, -1150), (1140, 130, -1450)):
            with self.assertRaises(UserError):
                spatial_custody({cell})
        proof = spatial_custody({(1159, 99, -1215)})
        self.assertEqual(proof['source_spatial_intersections'], 0)
        self.assertFalse(proof['native_dynamic_collision_acceptance'])
        self.assertFalse(proof['universal_vessel_clearance_or_static_ship_mobility'])

    def test_reader_defers_at_exact_host_boundary_and_above_owned_memory_bound(self):
        with patch('tools.artistic_zipline_catenary.psutil.virtual_memory',
                   return_value=SimpleNamespace(available=1536*MIB)):
            with self.assertRaises(UserError):
                reader_budget()
        with patch('tools.artistic_zipline_catenary.psutil.virtual_memory',
                   return_value=SimpleNamespace(available=2048*MIB)), \
             patch('tools.artistic_zipline_catenary.psutil.Process',
                   return_value=SimpleNamespace(memory_info=lambda: SimpleNamespace(rss=257*MIB))):
            with self.assertRaises(UserError):
                reader_budget()
