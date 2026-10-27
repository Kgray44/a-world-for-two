"""Geometry/security checks do not award this prototype artistic acceptance."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from control_room.common import Layout, REPO, UserError, read_json, write_json
from tools.artistic_materials import material_runs
from tools.artistic_ship import (AIR, ArtisticShip, NAME, build, circulation, halfwidth,
                                 lower_hull_seal, prepare, revision_plans, sheer)


# Sanitized property-enum fixture taken from the actual 1.21.1 native registry.
# Only used block IDs/property enums appear here: no seed, player or world paths.
NATIVE_BLOCKS = {'chipped:bundled_white_wool': {},
 'chipped:detailed_dark_oak_planks': {},
 'chipped:detailed_spruce_planks': {},
 'chipped:fine_vertical_dark_oak_planks': {},
 'chipped:knitted_white_wool': {},
 'chipped:metal_ladder': {'facing': ['north', 'south', 'west', 'east'],
                          'waterlogged': ['true', 'false']},
 'chipped:nailed_dark_oak_planks': {},
 'chipped:patched_light_gray_wool': {},
 'chipped:patched_white_wool': {},
 'chipped:ribbled_white_wool': {},
 'chipped:spruce_crate': {'facing': ['north', 'east', 'south', 'west', 'up', 'down'],
                          'open': ['true', 'false']},
 'chipped:stacked_dark_oak_planks': {},
 'chipped:vertical_dark_oak_planks': {},
 'chipped:woved_white_wool': {},
 'comforts:hammock_white': {'facing': ['north', 'south', 'west', 'east'],
                            'occupied': ['true', 'false'],
                            'part': ['head', 'foot'],
                            'waterlogged': ['true', 'false']},
 'create:copper_valve_handle': {'facing': ['north', 'east', 'south', 'west', 'up', 'down'],
                                'waterlogged': ['true', 'false']},
 'create:fluid_pipe': {'down': ['true', 'false'],
                       'east': ['true', 'false'],
                       'north': ['true', 'false'],
                       'south': ['true', 'false'],
                       'up': ['true', 'false'],
                       'waterlogged': ['true', 'false'],
                       'west': ['true', 'false']},
 'create:hand_crank': {'facing': ['north', 'east', 'south', 'west', 'up', 'down'],
                       'waterlogged': ['true', 'false']},
 'create:large_cogwheel': {'axis': ['x', 'y', 'z'], 'waterlogged': ['true', 'false']},
 'create:mechanical_pump': {'facing': ['north', 'east', 'south', 'west', 'up', 'down'],
                            'waterlogged': ['true', 'false']},
 'create:rope_pulley': {'axis': ['x', 'z']},
 'create:shaft': {'axis': ['x', 'y', 'z'], 'waterlogged': ['true', 'false']},
 'createbigcannons:cast_iron_cannon_barrel': {'facing': ['north',
                                                         'east',
                                                         'south',
                                                         'west',
                                                         'up',
                                                         'down']},
 'createbigcannons:cast_iron_cannon_chamber': {'facing': ['north',
                                                          'east',
                                                          'south',
                                                          'west',
                                                          'up',
                                                          'down']},
 'createbigcannons:cast_iron_cannon_end': {'facing': ['north',
                                                      'east',
                                                      'south',
                                                      'west',
                                                      'up',
                                                      'down']},
 'farm_and_charm:rope': {'center_piece': ['true', 'false'],
                         'down': ['true', 'false'],
                         'east': ['true', 'false'],
                         'north': ['true', 'false'],
                         'rope_knot': ['true', 'false'],
                         'south': ['true', 'false'],
                         'supporting_rope_knot': ['true', 'false'],
                         'up': ['true', 'false'],
                         'west': ['true', 'false']},
 'farm_and_charm:rope_knot': {'east': ['true', 'false'],
                              'north': ['true', 'false'],
                              'south': ['true', 'false'],
                              'west': ['true', 'false']},
 'farmersdelight:cooking_pot': {'facing': ['north', 'south', 'west', 'east'],
                                'support': ['none', 'tray', 'handle'],
                                'waterlogged': ['true', 'false']},
 'farmersdelight:cutting_board': {'facing': ['north', 'south', 'west', 'east'],
                                  'waterlogged': ['true', 'false']},
 'farmersdelight:spruce_cabinet': {'facing': ['north', 'south', 'west', 'east'],
                                   'open': ['true', 'false']},
 'farmersdelight:stove': {'facing': ['north', 'south', 'west', 'east'], 'lit': ['true', 'false']},
 'handcrafted:blue_cup': {'facing': ['north', 'south', 'west', 'east'],
                          'pieces': ['1', '2', '3', '4', '5', '6'],
                          'waterlogged': ['true', 'false']},
 'handcrafted:blue_plate': {'facing': ['north', 'south', 'west', 'east'],
                            'pieces': ['1', '2', '3', '4', '5', '6'],
                            'waterlogged': ['true', 'false']},
 'handcrafted:dark_oak_bench': {'color': ['none',
                                          'white',
                                          'orange',
                                          'magenta',
                                          'light_blue',
                                          'yellow',
                                          'lime',
                                          'pink',
                                          'gray',
                                          'light_gray',
                                          'cyan',
                                          'purple',
                                          'blue',
                                          'brown',
                                          'green',
                                          'red',
                                          'black'],
                                'facing': ['north', 'south', 'west', 'east'],
                                'shape': ['single',
                                          'left',
                                          'middle',
                                          'right',
                                          'inner_left',
                                          'inner_right',
                                          'outer_left',
                                          'outer_right'],
                                'waterlogged': ['true', 'false']},
 'handcrafted:dark_oak_chair': {'color': ['none',
                                          'white',
                                          'orange',
                                          'magenta',
                                          'light_blue',
                                          'yellow',
                                          'lime',
                                          'pink',
                                          'gray',
                                          'light_gray',
                                          'cyan',
                                          'purple',
                                          'blue',
                                          'brown',
                                          'green',
                                          'red',
                                          'black'],
                                'facing': ['north', 'south', 'west', 'east'],
                                'waterlogged': ['true', 'false']},
 'handcrafted:dark_oak_couch': {'color': ['white',
                                          'orange',
                                          'magenta',
                                          'light_blue',
                                          'yellow',
                                          'lime',
                                          'pink',
                                          'gray',
                                          'light_gray',
                                          'cyan',
                                          'purple',
                                          'blue',
                                          'brown',
                                          'green',
                                          'red',
                                          'black'],
                                'facing': ['north', 'south', 'west', 'east'],
                                'shape': ['single',
                                          'left',
                                          'middle',
                                          'right',
                                          'inner_left',
                                          'inner_right',
                                          'outer_left',
                                          'outer_right'],
                                'waterlogged': ['true', 'false']},
 'handcrafted:dark_oak_cupboard': {'facing': ['north', 'south', 'west', 'east'],
                                   'type': ['1', '2']},
 'handcrafted:dark_oak_desk': {'color': ['none',
                                         'white',
                                         'orange',
                                         'magenta',
                                         'light_blue',
                                         'yellow',
                                         'lime',
                                         'pink',
                                         'gray',
                                         'light_gray',
                                         'cyan',
                                         'purple',
                                         'blue',
                                         'brown',
                                         'green',
                                         'red',
                                         'black'],
                               'facing': ['north', 'south', 'west', 'east'],
                               'waterlogged': ['true', 'false']},
 'handcrafted:dark_oak_drawer': {'facing': ['north', 'south', 'west', 'east'],
                                 'shape': ['single', 'left', 'middle', 'right'],
                                 'type': ['1', '2', '3', '4']},
 'handcrafted:dark_oak_nightstand': {'color': ['none',
                                               'white',
                                               'orange',
                                               'magenta',
                                               'light_blue',
                                               'yellow',
                                               'lime',
                                               'pink',
                                               'gray',
                                               'light_gray',
                                               'cyan',
                                               'purple',
                                               'blue',
                                               'brown',
                                               'green',
                                               'red',
                                               'black'],
                                     'facing': ['north', 'south', 'west', 'east'],
                                     'waterlogged': ['true', 'false']},
 'handcrafted:dark_oak_shelf': {'facing': ['north', 'south', 'west', 'east'],
                                'shape': ['single', 'left', 'middle', 'right'],
                                'type': ['1', '2', '3', '4', '5']},
 'handcrafted:dark_oak_side_table': {'color': ['none',
                                               'white',
                                               'orange',
                                               'magenta',
                                               'light_blue',
                                               'yellow',
                                               'lime',
                                               'pink',
                                               'gray',
                                               'light_gray',
                                               'cyan',
                                               'purple',
                                               'blue',
                                               'brown',
                                               'green',
                                               'red',
                                               'black'],
                                     'facing': ['north', 'south', 'west', 'east'],
                                     'waterlogged': ['true', 'false']},
 'handcrafted:dark_oak_table': {'color': ['none',
                                          'white',
                                          'orange',
                                          'magenta',
                                          'light_blue',
                                          'yellow',
                                          'lime',
                                          'pink',
                                          'gray',
                                          'light_gray',
                                          'cyan',
                                          'purple',
                                          'blue',
                                          'brown',
                                          'green',
                                          'red',
                                          'black'],
                                'shape': ['single',
                                          'center',
                                          'north_center',
                                          'east_center',
                                          'south_center',
                                          'west_center',
                                          'north_south_center',
                                          'east_west_center',
                                          'north_east_corner',
                                          'north_west_corner',
                                          'south_east_corner',
                                          'south_west_corner',
                                          'north_side',
                                          'east_side',
                                          'south_side',
                                          'west_side'],
                                'waterlogged': ['true', 'false']},
 'handcrafted:stackable_book': {'books': ['1', '2', '3', '4'],
                                'facing': ['north', 'south', 'west', 'east'],
                                'seed': ['1',
                                         '2',
                                         '3',
                                         '4',
                                         '5',
                                         '6',
                                         '7',
                                         '8',
                                         '9',
                                         '10',
                                         '11',
                                         '12',
                                         '13',
                                         '14',
                                         '15',
                                         '16',
                                         '17',
                                         '18',
                                         '19',
                                         '20',
                                         '21',
                                         '22',
                                         '23',
                                         '24',
                                         '25',
                                         '26',
                                         '27',
                                         '28',
                                         '29',
                                         '30',
                                         '31',
                                         '32',
                                         '33',
                                         '34',
                                         '35',
                                         '36',
                                         '37',
                                         '38',
                                         '39',
                                         '40',
                                         '41',
                                         '42',
                                         '43',
                                         '44',
                                         '45',
                                         '46',
                                         '47',
                                         '48',
                                         '49',
                                         '50',
                                         '51',
                                         '52',
                                         '53',
                                         '54',
                                         '55',
                                         '56',
                                         '57',
                                         '58',
                                         '59',
                                         '60',
                                         '61',
                                         '62',
                                         '63',
                                         '64',
                                         '65',
                                         '66',
                                         '67',
                                         '68',
                                         '69',
                                         '70',
                                         '71',
                                         '72',
                                         '73',
                                         '74',
                                         '75',
                                         '76',
                                         '77',
                                         '78',
                                         '79',
                                         '80',
                                         '81',
                                         '82',
                                         '83',
                                         '84',
                                         '85',
                                         '86',
                                         '87',
                                         '88',
                                         '89',
                                         '90',
                                         '91',
                                         '92',
                                         '93',
                                         '94',
                                         '95',
                                         '96',
                                         '97',
                                         '98',
                                         '99',
                                         '100',
                                         '101',
                                         '102',
                                         '103',
                                         '104',
                                         '105',
                                         '106',
                                         '107',
                                         '108',
                                         '109',
                                         '110',
                                         '111',
                                         '112',
                                         '113',
                                         '114',
                                         '115',
                                         '116',
                                         '117',
                                         '118',
                                         '119',
                                         '120',
                                         '121',
                                         '122',
                                         '123',
                                         '124',
                                         '125',
                                         '126',
                                         '127',
                                         '128',
                                         '129',
                                         '130',
                                         '131',
                                         '132',
                                         '133',
                                         '134',
                                         '135',
                                         '136',
                                         '137',
                                         '138',
                                         '139',
                                         '140',
                                         '141',
                                         '142',
                                         '143',
                                         '144',
                                         '145',
                                         '146',
                                         '147',
                                         '148',
                                         '149',
                                         '150',
                                         '151',
                                         '152',
                                         '153',
                                         '154',
                                         '155',
                                         '156',
                                         '157',
                                         '158',
                                         '159',
                                         '160',
                                         '161',
                                         '162',
                                         '163',
                                         '164',
                                         '165',
                                         '166',
                                         '167',
                                         '168',
                                         '169',
                                         '170',
                                         '171',
                                         '172',
                                         '173',
                                         '174',
                                         '175',
                                         '176',
                                         '177',
                                         '178',
                                         '179',
                                         '180',
                                         '181',
                                         '182',
                                         '183',
                                         '184',
                                         '185',
                                         '186',
                                         '187',
                                         '188',
                                         '189',
                                         '190',
                                         '191',
                                         '192',
                                         '193',
                                         '194',
                                         '195',
                                         '196',
                                         '197',
                                         '198',
                                         '199',
                                         '200',
                                         '201',
                                         '202',
                                         '203',
                                         '204',
                                         '205',
                                         '206',
                                         '207',
                                         '208',
                                         '209',
                                         '210',
                                         '211',
                                         '212',
                                         '213',
                                         '214',
                                         '215',
                                         '216',
                                         '217',
                                         '218',
                                         '219',
                                         '220',
                                         '221',
                                         '222',
                                         '223',
                                         '224',
                                         '225',
                                         '226',
                                         '227',
                                         '228',
                                         '229',
                                         '230',
                                         '231',
                                         '232',
                                         '233',
                                         '234',
                                         '235',
                                         '236',
                                         '237',
                                         '238',
                                         '239',
                                         '240',
                                         '241',
                                         '242',
                                         '243',
                                         '244',
                                         '245',
                                         '246',
                                         '247',
                                         '248',
                                         '249',
                                         '250',
                                         '251',
                                         '252',
                                         '253',
                                         '254',
                                         '255',
                                         '256']},
 'handcrafted:terracotta_medium_pot': {},
 'handcrafted:terracotta_thick_pot': {},
 'handcrafted:terracotta_thin_pot': {},
 'handcrafted:terracotta_wide_pot': {},
 'lfpirates:ship_in_bottle': {'facing': ['north', 'south', 'west', 'east'],
                              'waterlogged': ['true', 'false']},
 'minecraft:air': {},
 'minecraft:barrel': {'facing': ['north', 'east', 'south', 'west', 'up', 'down'],
                      'open': ['true', 'false']},
 'minecraft:bell': {'attachment': ['floor', 'ceiling', 'single_wall', 'double_wall'],
                    'facing': ['north', 'south', 'west', 'east'],
                    'powered': ['true', 'false']},
 'minecraft:birch_fence': {'east': ['true', 'false'],
                           'north': ['true', 'false'],
                           'south': ['true', 'false'],
                           'waterlogged': ['true', 'false'],
                           'west': ['true', 'false']},
 'minecraft:blue_bed': {'facing': ['north', 'south', 'west', 'east'],
                        'occupied': ['true', 'false'],
                        'part': ['head', 'foot']},
 'minecraft:blue_carpet': {},
 'minecraft:blue_terracotta': {},
 'minecraft:blue_wool': {},
 'minecraft:bookshelf': {},
 'minecraft:candle': {'candles': ['1', '2', '3', '4'],
                      'lit': ['true', 'false'],
                      'waterlogged': ['true', 'false']},
 'minecraft:cartography_table': {},
 'minecraft:chain': {'axis': ['x', 'y', 'z'], 'waterlogged': ['true', 'false']},
 'minecraft:chest': {'facing': ['north', 'south', 'west', 'east'],
                     'type': ['single', 'left', 'right'],
                     'waterlogged': ['true', 'false']},
 'minecraft:cobblestone_wall': {'east': ['none', 'low', 'tall'],
                                'north': ['none', 'low', 'tall'],
                                'south': ['none', 'low', 'tall'],
                                'up': ['true', 'false'],
                                'waterlogged': ['true', 'false'],
                                'west': ['none', 'low', 'tall']},
 'minecraft:crafting_table': {},
 'minecraft:dark_oak_door': {'facing': ['north', 'south', 'west', 'east'],
                             'half': ['upper', 'lower'],
                             'hinge': ['left', 'right'],
                             'open': ['true', 'false'],
                             'powered': ['true', 'false']},
 'minecraft:dark_oak_fence': {'east': ['true', 'false'],
                              'north': ['true', 'false'],
                              'south': ['true', 'false'],
                              'waterlogged': ['true', 'false'],
                              'west': ['true', 'false']},
 'minecraft:dark_oak_log': {'axis': ['x', 'y', 'z']},
 'minecraft:dark_oak_planks': {},
 'minecraft:dark_oak_slab': {'type': ['top', 'bottom', 'double'], 'waterlogged': ['true', 'false']},
 'minecraft:dark_oak_stairs': {'facing': ['north', 'south', 'west', 'east'],
                               'half': ['top', 'bottom'],
                               'shape': ['straight',
                                         'inner_left',
                                         'inner_right',
                                         'outer_left',
                                         'outer_right'],
                               'waterlogged': ['true', 'false']},
 'minecraft:dark_oak_trapdoor': {'facing': ['north', 'south', 'west', 'east'],
                                 'half': ['top', 'bottom'],
                                 'open': ['true', 'false'],
                                 'powered': ['true', 'false'],
                                 'waterlogged': ['true', 'false']},
 'minecraft:glass': {},
 'minecraft:gold_block': {},
 'minecraft:grindstone': {'face': ['floor', 'wall', 'ceiling'],
                          'facing': ['north', 'south', 'west', 'east']},
 'minecraft:hay_block': {'axis': ['x', 'y', 'z']},
 'minecraft:iron_bars': {'east': ['true', 'false'],
                         'north': ['true', 'false'],
                         'south': ['true', 'false'],
                         'waterlogged': ['true', 'false'],
                         'west': ['true', 'false']},
 'minecraft:jungle_slab': {'type': ['top', 'bottom', 'double'], 'waterlogged': ['true', 'false']},
 'minecraft:ladder': {'facing': ['north', 'south', 'west', 'east'],
                      'waterlogged': ['true', 'false']},
 'minecraft:lantern': {'hanging': ['true', 'false'], 'waterlogged': ['true', 'false']},
 'minecraft:oak_sign': {'rotation': ['0',
                                     '1',
                                     '2',
                                     '3',
                                     '4',
                                     '5',
                                     '6',
                                     '7',
                                     '8',
                                     '9',
                                     '10',
                                     '11',
                                     '12',
                                     '13',
                                     '14',
                                     '15'],
                        'waterlogged': ['true', 'false']},
 'minecraft:oak_slab': {'type': ['top', 'bottom', 'double'], 'waterlogged': ['true', 'false']},
 'minecraft:oak_stairs': {'facing': ['north', 'south', 'west', 'east'],
                          'half': ['top', 'bottom'],
                          'shape': ['straight',
                                    'inner_left',
                                    'inner_right',
                                    'outer_left',
                                    'outer_right'],
                          'waterlogged': ['true', 'false']},
 'minecraft:oak_trapdoor': {'facing': ['north', 'south', 'west', 'east'],
                            'half': ['top', 'bottom'],
                            'open': ['true', 'false'],
                            'powered': ['true', 'false'],
                            'waterlogged': ['true', 'false']},
 'minecraft:smooth_sandstone': {},
 'minecraft:spruce_planks': {},
 'minecraft:spruce_slab': {'type': ['top', 'bottom', 'double'], 'waterlogged': ['true', 'false']},
 'minecraft:stripped_dark_oak_log': {'axis': ['x', 'y', 'z']},
 'minecraft:stripped_oak_log': {'axis': ['x', 'y', 'z']},
 'minecraft:stripped_spruce_log': {'axis': ['x', 'y', 'z']},
 'minecraft:water_cauldron': {'boiling': ['true', 'false'], 'level': ['1', '2', '3']},
 'minecraft:white_wool': {},
 'minecraft:yellow_terracotta': {},
 'supplementaries:globe_sepia': {'facing': ['north', 'south', 'west', 'east'],
                                 'powered': ['true', 'false'],
                                 'rotation': ['0', '1', '2', '3', '4'],
                                 'waterlogged': ['true', 'false']},
 'supplementaries:hourglass': {'facing': ['north', 'east', 'south', 'west', 'up', 'down'],
                               'light_level': ['0',
                                               '1',
                                               '2',
                                               '3',
                                               '4',
                                               '5',
                                               '6',
                                               '7',
                                               '8',
                                               '9',
                                               '10',
                                               '11',
                                               '12',
                                               '13',
                                               '14',
                                               '15'],
                               'waterlogged': ['true', 'false']},
 'supplementaries:sack': {'open': ['true', 'false'], 'waterlogged': ['true', 'false']}}
ITEMS = ['create:wrench',
 'createbigcannons:worm',
 'minecraft:bowl',
 'minecraft:bread',
 'minecraft:bucket',
 'minecraft:carrot',
 'minecraft:clock',
 'minecraft:compass',
 'minecraft:cooked_cod',
 'minecraft:copper_ingot',
 'minecraft:dried_kelp',
 'minecraft:feather',
 'minecraft:iron_axe',
 'minecraft:iron_nugget',
 'minecraft:lead',
 'minecraft:map',
 'minecraft:oak_boat',
 'minecraft:oak_planks',
 'minecraft:potato',
 'minecraft:rose_bush',
 'minecraft:shears',
 'minecraft:spyglass',
 'minecraft:stick',
 'minecraft:string',
 'minecraft:white_wool',
 'minecraft:writable_book']


def registry():
    return {'blocks': deepcopy(NATIVE_BLOCKS), 'items': ITEMS[:], 'entities': [],
            'seed': 'synthetic-test-world', 'world_path': 'synthetic-staging-world'}


class ArtisticShipTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ship, cls.review = build(registry())

    def test_one_authored_hull_has_fine_entry_tumblehome_and_rising_sheer(self):
        self.assertLess(halfwidth(-42, 0), 3)
        self.assertGreater(halfwidth(0, 0), 10)
        self.assertLess(halfwidth(43, 0), 6)
        self.assertLess(halfwidth(0, 8), halfwidth(0, 0))
        self.assertGreater(sheer(-40), sheer(0))
        self.assertGreater(sheer(40), sheer(0))
        self.assertEqual(self.ship.commands, [])
        self.assertLess(len(self.ship.blocks), 180_000)
        self.assertGreaterEqual(min(pos[1] for pos in self.ship.blocks), 55)

    def test_all_named_spaces_reached_without_auto_carving_away_obstructions(self):
        self.assertEqual(self.review['rooms_reached'], len(self.ship.rooms))
        self.assertEqual({r['deck'] for r in self.ship.rooms}, {'hold', 'berth', 'gun', 'weather', 'forecastle', 'quarterdeck'})
        broken = deepcopy(self.ship)
        x, y, z = broken.rooms[0]['local_anchor']
        broken.put(x, y+1, z, 'minecraft:barrel', facing='up', open=False)
        with self.assertRaisesRegex(UserError, 'unreachable room'):
            circulation(broken)
        self.assertTrue(broken.local_state(x, y+1, z).startswith('minecraft:barrel'))

    def test_closed_lower_hull_is_not_replaced_by_cargo_and_puncture_is_detected(self):
        self.assertEqual(self.review['lower_hull_seal']['enclosed_low_deck_anchors'], 7)
        broken = deepcopy(self.ship)
        position = next(pos for pos in broken.shell_cells if pos[2] == 0 and pos[1] == -2 and pos[0] > 0)
        wx, wz = broken.world(position[0], position[2])
        broken.blocks[wx, broken.sea+position[1], wz] = AIR
        with self.assertRaisesRegex(UserError, 'does not seal'):
            lower_hull_seal(broken)
        with self.assertRaisesRegex(UserError, 'sealed lower hull'):
            self.ship.put(*position, 'minecraft:barrel', facing='up', open=False)

    def test_material_rules_include_all_decks_canvas_rigging_and_joint_collars(self):
        self.assertEqual(material_runs(self.ship.blocks), [])
        self.assertTrue(self.review['materials']['state_facing_is_not_a_material_break'])
        self.assertTrue(any('chipped:bundled_white_wool' == state for state in self.ship.blocks.values()))
        self.assertTrue(any(state.startswith('farm_and_charm:rope_knot') for state in self.ship.blocks.values()))
        self.assertFalse(any(state.startswith('supplementaries:rope') for state in self.ship.blocks.values()))

    def test_native_properties_fail_closed_and_missing_palette_is_not_substituted(self):
        p = ArtisticShip(registry())
        with self.assertRaisesRegex(UserError, 'property does not exist'):
            p.put(0, 0, 0, 'minecraft:air', invented=True)
        missing = registry()
        missing['blocks'].pop('minecraft:dark_oak_planks')
        with self.assertRaisesRegex(UserError, 'actual registered block'):
            build(missing)
        with self.assertRaises(UserError):
            p.put(1000, 0, 0, 'minecraft:air')

    def test_rope_graph_rejects_a_floating_fragment_and_keeps_one_family(self):
        p = ArtisticShip(registry())
        p.rope((2, 40, 30), (2, 44, 30))
        with self.assertRaisesRegex(UserError, 'fixed attachment'):
            p.finish_ropes()
        proof = self.review['rope_attachments']
        self.assertEqual(proof['family'], 'farm_and_charm')
        self.assertTrue(proof['native_survival_and_drop_inspection_pending'])
        self.assertEqual(len(self.ship.detail_groups), 10)

    def test_revision_preserves_original_and_accounts_for_removed_and_new_cells(self):
        old = json.loads(self.ship.encoded())
        changed = deepcopy(self.ship)
        removed = next(pos for pos, state in changed.blocks.items() if state == AIR)
        changed.blocks.pop(removed)
        # A new, bounded upper rigging cell needs an explicit actual-air check.
        fresh = (20, 130, 47)
        self.assertNotIn(fresh, self.ship.blocks)
        changed.blocks[fresh] = 'minecraft:dark_oak_planks'
        before, delta, scope = revision_plans(changed, old)
        self.assertEqual(delta.blocks[removed], AIR)
        self.assertEqual(before.blocks[fresh], AIR)
        self.assertEqual(delta.blocks[fresh], 'minecraft:dark_oak_planks')
        self.assertGreater(scope['new_positions_requiring_native_air_verification'], 0)
        self.assertIn(removed, self.ship.blocks)
        self.assertEqual(old, json.loads(self.ship.encoded()) | {'created': old['created']})
        with self.assertRaisesRegex(UserError, 'exact staging world'):
            revision_plans(changed, dict(old, world_path='different-world'))
        malformed = deepcopy(old)
        malformed['blocks'].append(malformed['blocks'][0])
        with self.assertRaisesRegex(UserError, 'invalid or duplicate'):
            revision_plans(changed, malformed)

    def test_guns_magazine_and_tender_do_not_claim_unproved_functionality(self):
        self.assertEqual(len(self.ship.guns), 28)
        self.assertTrue(all(not gun['loaded'] and not gun['assembled'] for gun in self.ship.guns))
        self.assertFalse(any('tnt' in state or 'gunpowder' in state for state in self.ship.blocks.values()))
        self.assertFalse(any('gunpowder' in tag or 'minecraft:tnt' in tag for tag in self.ship.tags.values()))
        self.assertEqual(len(self.ship.commands), 0)
        self.assertTrue(any('requires later commissioning' in row['purpose'] for row in self.ship.rooms))

    def test_r3_deck_jobs_leave_a_full_two_wide_clear_waist_and_open_cabin_headroom(self):
        for x in (3, 4):
            for z in range(-21, 24):
                floor = 10 if z >= 29 else sheer(z)
                for dy in (1, 2):
                    self.assertEqual(self.ship.local_state(x, floor+dy, z), AIR, (x, z, dy))
        self.assertTrue(self.ship.local_state(-5, 10, -18).startswith('create:large_cogwheel'))
        self.assertTrue(self.ship.local_state(-5, 11, -18).startswith('create:hand_crank'))
        self.assertEqual(self.ship.local_state(4, 10, -16), AIR)
        self.assertEqual(self.ship.local_state(0, 12, 39), AIR)
        self.assertTrue(self.ship.local_state(0, 11, 45).startswith('minecraft:dark_oak_door'))
        self.assertIn('Captain’s stern balcony', {row['name'] for row in self.ship.rooms})

    def test_rotation_preserves_geometry_and_rotates_directional_native_properties(self):
        turned, review = build(registry(), (100, 63, 200), 1)
        self.assertEqual(review['rooms_reached'], self.review['rooms_reached'])
        self.assertEqual(len(turned.blocks), len(self.ship.blocks))
        self.assertEqual(material_runs(turned.blocks), [])
        p = ArtisticShip(registry(), rotation=1)
        self.assertIn('facing=east', p.state('minecraft:ladder', facing='north', waterlogged=False))
        state = p.state('farm_and_charm:rope', north=True, east=False)
        self.assertIn('east=true', state)
        self.assertIn('south=false', state)

    def test_required_capture_views_have_actual_transformed_coordinates_and_eye_level_interiors(self):
        self.assertEqual(len(self.ship.cameras), 8)
        for pose in self.ship.cameras:
            self.assertIn('world_feet', pose)
            self.assertIn('yaw', pose)
            self.assertIn('pitch', pose)
        by_name = {row['name']: row for row in self.ship.cameras}
        self.assertEqual(by_name['gun deck']['local_position'][1], 4)
        self.assertEqual(by_name['hold']['local_position'][1], -6)
        self.assertEqual(by_name['captain cabin']['local_position'][1], 11)

    def test_serialization_names_only_this_staging_prototype_and_preserves_tags(self):
        with tempfile.TemporaryDirectory(prefix='awft-artistic-ship-') as directory:
            path = Path(directory)/'prototype.json'
            result = self.ship.save(path)
            data = read_json(path)
            self.assertEqual(data['name'], NAME)
            self.assertEqual(data['world_path'], 'synthetic-staging-world')
            self.assertEqual(result['blocks'], len(self.ship.blocks))
            self.assertEqual(len(data['block_entities']), len(self.ship.tags))
            self.assertEqual(data['commands'], [])
            self.assertIn('acceptance pending', data['validation'])

    def test_preparation_refuses_an_unowned_or_permanent_world_before_writing(self):
        with tempfile.TemporaryDirectory(prefix='awft-artistic-ship-') as directory:
            root = Path(directory)
            layout = Layout(root/'staging'/'world-tests'/'owned-artistic')
            layout.create()
            world = layout.world/'StagingWorld'
            world.mkdir()
            with patch('tools.artistic_ship.Storage') as storage:
                with self.assertRaisesRegex(UserError, 'explicitly owned'):
                    prepare(layout.home, staging_world=world, origin=(0, 63, 0))
                storage.return_value.reserve.assert_called_once()
            self.assertFalse(any(layout.staging.iterdir()))


if __name__ == '__main__':
    unittest.main()
