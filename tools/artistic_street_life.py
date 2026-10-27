"""Authored, lived-in trade rooms and alley stories after actual R2 inspection.

The r1/r2 plans are immutable inputs. Only a fresh delta is emitted, with no
existing inventory or sign replay. Filled shelves and flower boxes use the
actual pinned Moonlight ItemDisplayTile -> ContainerHelper inventory codec.
This source is not native render, walking, NPC or artistic acceptance evidence.
"""
from __future__ import annotations

import argparse
from collections import deque
import hashlib
import json
from pathlib import Path
import re
import subprocess

from control_room.common import UserError, digest, utcnow
from tools.artistic_street import designs, planned_clearance, building_material_checks, GUARD, MAX_BUNDLE, MIB
from tools.artistic_street_details import Details, ORIGIN, BASELINE_SHA, construct as r2, delta_native as r2_delta, verify_baseline, lane_width


R2_SHA = '4b3ff835cd60c18e5042d3bc96ae5c11884fb60f1be5260bfe90830f614ff415'
DISPLAY_ARTIFACTS = {
    'supplementaries-1.21.1-4.0.2-neoforge.jar': '2c2e0c98e0cc21874d8b2130bc773a2a5a6cadd854b9c8163d0e1f32e2ddffb0',
    'moonlight-1.21.1-3.7.2-neoforge.jar': '4a9f15108607cc70273f8a0b6eb24e1e99af8eef44bc3ae8681767ca7ce21b0f',
}
MAX_NEW_BE = 64


class Life(Details):
    def __init__(self, base):
        super().__init__(base)
        self.original_tagged = set(base.tags)
        # Some functional original blocks have default/empty inventories and no
        # authored NBT entry. Protect them as well; do not reset live contents.
        for pos, state in base.blocks.items():
            key = state.split('[', 1)[0]
            if key in ('minecraft:chest', 'minecraft:barrel', 'minecraft:furnace', 'minecraft:brewing_stand') or key.startswith('farmersdelight:'):
                self.protected.add(pos)
        self.new_entities = {}
        self.rooms_to_check = []
        self.supports = []

    def scene(self, ident, title, intent):
        self.p.zone = next(b.name for b in designs() if b.ident == ident) if ident else 'Shared alley and courtyard stories'
        self.name_group(title, intent)

    def put(self, x, y, z, key, **props):
        if key != 'minecraft:air' and ((x, y, z) in self.safe_bodies or (x, y-1, z) in self.safe_bodies):
            raise UserError('Detail would obstruct a preserved room/stair route: '+str((x, y, z)))
        if key.startswith('handcrafted:') and any(word in key for word in ('_pot', '_plate', 'stackable_book')):
            below = self.p.blocks.get((x, y-1, z), 'minecraft:air').split('[', 1)[0]
            if below == 'minecraft:air' or below.startswith(('mcwwindows:', 'mcwdoors:')):
                raise UserError('Trade clutter has no actual supporting furniture: '+str((x, y, z, key)))
        super().put(x, y, z, key, **props)

    def inventory(self, pos, key, items, title, *, slots, **props):
        if len(self.new_entities) >= MAX_NEW_BE:
            raise UserError('Lived-in detail exceeds its finite new-BE budget')
        if not 0 < len(items) <= slots or any(item not in self.p.registry['items'] for item in items):
            raise UserError('Display content does not fit its actual native item slots')
        if pos in self.protected or pos in self.new_entities:
            raise UserError('A new display overlaps a protected or existing inventory')
        self.put(*pos, key, **props)
        entries = ','.join('{Slot:'+str(i)+'b,id:'+json.dumps(item)+',count:1}' for i, item in enumerate(items))
        self.p.tags[pos] = '{CustomName:'+json.dumps(json.dumps({'text': title}))+',Items:['+entries+']}'
        self.new_entities[pos] = {'block': key, 'items': list(items), 'title': title,
                                  'purpose': self.group, 'slots': slots}

    def shelf(self, x, y, z, facing, item, title):
        dx, dz = {'east': (-1, 0), 'west': (1, 0), 'north': (0, 1), 'south': (0, -1)}[facing]
        backing = self.p.blocks.get((x+dx, y, z+dz), 'minecraft:air').split('[', 1)[0]
        full = {'minecraft:bricks', 'minecraft:stone_bricks', 'minecraft:calcite', 'minecraft:bookshelf',
                'minecraft:white_terracotta', 'minecraft:cyan_terracotta', 'minecraft:yellow_terracotta',
                'minecraft:green_terracotta', 'minecraft:light_gray_terracotta',
                'minecraft:stripped_spruce_log', 'minecraft:stripped_dark_oak_log', 'minecraft:stripped_oak_log'}
        if backing not in full:
            raise UserError('Wall display has no actual full backing: '+str((x, y, z, backing)))
        self.inventory((x, y, z), 'supplementaries:item_shelf', [item], title,
                       slots=1, facing=facing, waterlogged=False)
        self.supports.append({'fixture': [x, y, z], 'support': [x+dx, y, z+dz], 'type': 'full wall backing'})

    def counter(self, x, floor, z, facing='east', wood='spruce', top='dark_oak_planks'):
        self.put(x, floor+1, z, 'handcrafted:'+wood+'_counter', facing=facing, counter=top, type='1')

    def barrel(self, x, floor, z, title, items):
        self.inventory((x, floor+1, z), 'minecraft:barrel', items, title,
                       slots=27, facing='up', open=False)

    def candle(self, x, y, z, facing='east', wall=False):
        if wall:
            dx, dz = {'east': (-1, 0), 'west': (1, 0), 'north': (0, 1), 'south': (0, -1)}[facing]
            support = self.p.blocks.get((x+dx, y, z+dz), 'minecraft:air')
        else:
            support = self.p.blocks.get((x, y-1, z), 'minecraft:air')
        if support == 'minecraft:air':
            raise UserError('Candle has no actual wall or tabletop support')
        self.put(x, y, z, 'supplementaries:candle_holder', candles=2,
                 face='wall' if wall else 'floor', facing=facing, lit=True, waterlogged=False)

    def rug(self, x1, z1, x2, z2, floor, color):
        for x in range(x1, x2+1):
            for z in range(z1, z2+1):
                self.put(x, floor+1, z, 'minecraft:'+color+'_carpet')

    def table(self, x, floor, z, wood='spruce'):
        self.put(x, floor+1, z, 'handcrafted:'+wood+'_table',
                 color='none', shape='single', waterlogged=False)

    def chair(self, x, floor, z, facing, wood='spruce'):
        self.put(x, floor+1, z, 'handcrafted:'+wood+'_chair',
                 facing=facing, color='none', waterlogged=False)

    def room_goal(self, ident, floor, goal):
        self.rooms_to_check.append((ident, floor, goal))


def lighter_soffits(d):
    d.scene(None, 'Thinner jetties and a lighter covered alley', 'Reduce the full-block boxed soffits seen in real R2 screenshots while preserving the exact upstairs floor surface and solid nodes above hanging fixtures.')
    changed = 0
    for b in designs():
        d.p.zone = b.name
        candidates = set()
        for level in range(1, len(b.levels)):
            floor = b.base+level*4
            candidates |= {(x, floor, z) for x, z in b.levels[level]-b.levels[level-1]}
        if b.ident == 'archhouse':
            candidates |= {(x, 4, z) for x in range(27, 30) for z in range(24, 33)}
        for pos in sorted(candidates):
            x, y, z = pos
            below = d.p.blocks.get((x, y-1, z), '').split('[', 1)[0]
            if below in ('minecraft:lantern', 'minecraft:dark_oak_hanging_sign',
                          'mcwlights:chain_lantern', 'minecraft:chain'):
                continue
            key = d.p.blocks.get(pos, '').split('[', 1)[0]
            slab = {'minecraft:spruce_planks': 'minecraft:spruce_slab',
                    'minecraft:dark_oak_planks': 'minecraft:dark_oak_slab',
                    'minecraft:stripped_oak_wood': 'minecraft:oak_slab'}.get(key)
            if slab:
                d.put(*pos, slab, type='top', waterlogged=False)
                changed += 1
            elif key == 'minecraft:dark_oak_wood':
                d.put(*pos, 'minecraft:dark_oak_stairs', facing='east' if x == min(q[0] for q in b.levels[0]) else 'west',
                      half='top', shape='straight', waterlogged=False)
                changed += 1
    d.groups[-1]['thinned_floor_edges'] = changed
    d.groups[-1]['upper_walking_surface_unchanged'] = True


def chandler(d):
    d.scene('chandler', 'The chandler is a real lamp-and-rope shop', 'A fitted wall bench, actual lamp/rope/shears displays, hanging line, customer ledger table and supply corner replace the empty table-and-barrel room seen in the real capture.')
    for z in (12, 13, 14):
        d.counter(3, 0, z)
    for z, item, title in ((12, 'minecraft:lantern', 'A repaired dock lantern'),
                           (13, 'minecraft:shears', 'Line-cutting shears'),
                           (14, 'supplementaries:rope', 'Spare hemp line')):
        d.shelf(3, 2, z, 'east', item, title)
    d.put(4, 3, 14, 'supplementaries:rope', up=True, down=True, knot=False,
          north=False, south=False, east=False, west=False, waterlogged=False)
    d.put(4, 2, 14, 'supplementaries:rope', up=True, down=False, knot=False,
          north=False, south=False, east=False, west=False, waterlogged=False)
    d.put(5, 2, 12, 'handcrafted:stackable_book', books=2, facing='south', seed=19)
    d.chair(6, 0, 12, 'west')
    d.counter(8, 0, 10, 'west')
    d.counter(8, 0, 11, 'west')
    d.shelf(8, 2, 10, 'west', 'minecraft:candle', 'Lamp wicks and wax')
    d.candle(8, 2, 11)
    d.put(8, 1, 9, 'handcrafted:spruce_cupboard', facing='west', type='1')
    d.room_goal('chandler', 0, (6, 13))
    d.scene('chandler', 'Family kitchen above the lamp shop', 'A proper small kitchen and shared table explain who lives upstairs, with food storage, crockery and a two-place sleeping nook above.')
    for z in (12, 13):
        d.counter(3, 4, z)
    d.put(3, 5, 14, 'farmersdelight:stove', facing='east', lit=True)
    d.put(3, 6, 12, 'handcrafted:terracotta_plate', facing='east', pieces=3, waterlogged=False)
    d.shelf(3, 6, 13, 'east', 'minecraft:bowl', 'Daily bowls')
    d.barrel(8, 4, 10, 'Chandler family pantry', ['minecraft:bread', 'minecraft:apple', 'minecraft:carrot'])
    d.chair(6, 4, 12, 'west')
    d.put(5, 6, 12, 'handcrafted:wood_plate', facing='south', pieces=2, waterlogged=False)
    for x, shape in ((4, 'left'), (5, 'right')):
        for part, z in (('head', 10), ('foot', 11)):
            d.put(x, 9, z, 'handcrafted:spruce_fancy_bed',
                  facing='north', occupied=False, part=part, color='green', shape=shape)
    d.rug(4, 14, 6, 15, 8, 'green')
    d.put(3, 9, 14, 'handcrafted:spruce_cupboard', facing='east', type='2')
    d.put(5, 10, 12, 'handcrafted:stackable_book', books=2, facing='south', seed=11)
    d.room_goal('chandler', 4, (6, 13))
    d.room_goal('chandler', 8, (6, 13))


def sailmaker(d):
    d.scene('sailmaker', 'Seven Stitches cutting loft', 'Canvas, shears, a working loom, long cutting table and hanging cord give the tall sailmaker a specific craft instead of anonymous storage.')
    for z in (10, 11, 12):
        d.counter(12, 0, z)
    for z, item in ((10, 'farmersdelight:canvas'), (11, 'minecraft:shears'), (12, 'minecraft:string')):
        d.shelf(12, 2, z, 'east', item, 'Sailmaker supplies')
    d.table(14, 0, 9)
    d.table(14, 0, 11)
    d.put(14, 2, 9, 'farmersdelight:canvas_rug')
    d.put(14, 2, 10, 'farmersdelight:canvas_rug')
    d.put(14, 2, 11, 'handcrafted:stackable_book', books=1, facing='east', seed=7)
    d.put(15, 1, 8, 'minecraft:loom', facing='south')
    d.put(13, 3, 12, 'supplementaries:rope', up=True, down=True, knot=False,
          north=False, south=False, east=False, west=False, waterlogged=False)
    d.put(13, 2, 12, 'supplementaries:rope', up=True, down=False, knot=False,
          north=False, south=False, east=False, west=False, waterlogged=False)
    d.room_goal('sailmaker', 0, (15, 12))
    # The crew floor is deliberately communal; the top is a separate small room.
    d.scene('sailmaker', 'Crew lodging and repaired clothes', 'Two distinct real sleeping places, a shared sea chest and a canvas-working corner fill the upper crew loft.')
    for x in (13, 14):
        for part, z in (('head', 8), ('foot', 9)):
            d.put(x, 9, z, 'minecraft:light_gray_bed', facing='north', part=part, occupied=False)
    d.barrel(12, 8, 12, 'Crew linen and mending', ['farmersdelight:canvas', 'minecraft:string', 'minecraft:white_wool'])
    d.put(14, 10, 10, 'handcrafted:stackable_book', books=2, facing='south', seed=9)
    d.rug(13, 12, 15, 13, 12, 'brown')


def tavern(d):
    d.scene('inn', "The Wren's Wake is a small public house", 'A short bar with actual drink displays, lit candles, a side-wing dining group and a real take-and-play lute create recognizable tavern activity without idle musicians or fake machinery.')
    for x in (23, 24, 25):
        d.counter(x, 0, 10, 'south', 'dark_oak')
    for z, item, title in ((11, 'minecraft:honey_bottle', 'Honey drinks'),
                           (12, 'minecraft:glass_bottle', 'Clean bottles')):
        d.shelf(22, 2, z, 'east', item, title)
    d.candle(24, 2, 10)
    d.put(24, 2, 11, 'handcrafted:terracotta_plate', facing='south', pieces=3, waterlogged=False)
    d.table(29, 0, 9, 'dark_oak')
    d.chair(28, 0, 9, 'east', 'dark_oak')
    d.chair(30, 0, 9, 'west', 'dark_oak')
    d.put(29, 2, 9, 'handcrafted:wood_plate', facing='south', pieces=2, waterlogged=False)
    d.shelf(31, 2, 9, 'west', 'immersive_melodies:lute', 'A lute for the evening')
    d.barrel(30, 0, 8, 'Tavern larder', ['minecraft:bread', 'minecraft:baked_potato', 'minecraft:honey_bottle'])
    d.room_goal('inn', 0, (28, 10))
    d.scene('inn', 'A small dining salon above the tavern', 'Upper tables face the side balcony; a reading lamp and guest supplies make the upper inn more than a single bed.')
    d.table(29, 4, 9, 'dark_oak')
    d.chair(28, 4, 9, 'east', 'dark_oak')
    d.chair(30, 4, 9, 'west', 'dark_oak')
    d.candle(29, 6, 9)
    d.put(24, 6, 11, 'handcrafted:stackable_book', books=2, facing='east', seed=22)
    d.barrel(22, 8, 11, 'Guest linen', ['minecraft:white_wool', 'minecraft:book'])


def bookshop(d):
    d.scene('bookbinder', 'Ink & Bramble binding room', 'Low wall libraries, real paper/ink/book displays, a binding desk and a tucked-away window reading corner make the shop and upstairs room distinct.')
    for z in (28, 29, 30):
        for y in (2, 3):
            d.put(4, y, z, 'minecraft:bookshelf')
    for z, item in ((27, 'minecraft:paper'), (28, 'minecraft:ink_sac')):
        d.shelf(9, 3, z, 'west', item, 'Bookbinding materials')
    d.table(5, 1, 32)
    d.put(5, 3, 32, 'handcrafted:stackable_book', books=3, facing='east', seed=14)
    d.chair(6, 1, 32, 'west')
    d.put(6, 3, 29, 'handcrafted:stackable_book', books=2, facing='east', seed=16)
    d.room_goal('bookbinder', 1, (7, 31))
    d.scene('bookbinder', 'Reading room with a lived-in book nook', 'Books, two window-side chairs and a reading table fill the upper room while keeping its bed and sea chest intact.')
    d.table(7, 5, 26)
    d.chair(6, 5, 26, 'east')
    d.chair(7, 5, 25, 'south')
    d.put(7, 7, 26, 'handcrafted:stackable_book', books=3, facing='north', seed=31)
    d.candle(6, 7, 27)


def apothecary(d):
    d.scene('apothecary', 'The Glass Rosemary working herbalist', 'Filled ingredient shelves, pottery, a narrow mixing bench and a water-and-brewing corner create a specific small shop rather than another generic table.')
    for z in (25, 26):
        d.counter(14, 0, z, 'east', 'oak', 'calcite')
    # The side bay gives real full backing to these ingredient displays.
    for z, item in ((28, 'minecraft:allium'), (29, 'minecraft:glass_bottle'), (30, 'minecraft:wheat_seeds')):
        d.shelf(13, 2, z, 'east', item, 'Rosemary ingredients')
    d.put(14, 2, 25, 'handcrafted:blue_glazed_thin_pot')
    d.put(15, 2, 28, 'handcrafted:terracotta_medium_pot')
    d.put(16, 1, 28, 'handcrafted:oak_side_table')
    d.candle(16, 2, 28)
    d.barrel(16, 0, 33, 'Herbalist seed and paper stores', ['minecraft:wheat_seeds', 'minecraft:paper', 'minecraft:bone_meal'])
    d.room_goal('apothecary', 0, (16, 29))
    d.scene('apothecary', 'Herbalist kitchen and bedroom', 'A small fitted kitchen and writing corner continue the household above the trade; the bedroom receives warm textiles and a bedside object.')
    d.counter(14, 4, 30, 'east', 'oak')
    d.put(14, 5, 31, 'farmersdelight:stove', facing='east', lit=True)
    d.put(15, 6, 27, 'handcrafted:wood_plate', facing='north', pieces=2, waterlogged=False)
    d.rug(14, 29, 16, 30, 8, 'green')
    d.put(15, 9, 27, 'handcrafted:oak_side_table')
    d.put(15, 10, 27, 'handcrafted:terracotta_thin_pot')


def coastal_trades(d):
    d.scene('fishmonger', 'Tide & Scale fish counter', 'Real fish item displays, a scale-like work table, a water corner and small produce crates tell a coastal household story.')
    for z in (12, 13):
        d.counter(41, 0, z, 'west', 'oak', 'smooth_stone')
    d.shelf(41, 2, 12, 'west', 'minecraft:cod', 'Morning cod')
    d.shelf(41, 2, 13, 'west', 'minecraft:salmon', 'Salmon for supper')
    d.put(38, 2, 15, 'handcrafted:terracotta_plate', facing='north', pieces=2, waterlogged=False)
    d.put(38, 1, 12, 'minecraft:water_cauldron', level=3)
    d.barrel(38, 0, 16, 'Fishmonger pantry', ['minecraft:kelp', 'minecraft:bread', 'minecraft:dried_kelp'])
    d.room_goal('fishmonger', 0, (38, 14))
    d.scene('harbormaster', 'A chart office with actual navigation tools', 'A fitted chart desk, compass and clock displays, paper files and a guest chair make this a working harbor office.')
    for z in (12, 13):
        d.counter(47, 1, z)
    d.shelf(47, 3, 12, 'east', 'minecraft:compass', 'Harbor compass')
    d.shelf(47, 3, 13, 'east', 'minecraft:clock', 'Tide watch')
    d.table(49, 1, 15)
    d.put(49, 3, 15, 'handcrafted:stackable_book', books=3, facing='south', seed=43)
    d.chair(50, 1, 15, 'west')
    d.barrel(48, 1, 18, 'Cargo manifests', ['minecraft:paper', 'minecraft:map', 'minecraft:feather'])
    d.room_goal('harbormaster', 1, (49, 16))


def homes(d):
    d.scene('lodging', 'The Blue Thread crew kitchen', 'A shared food counter, actual linen chest and a second sleeping place make the sailors lodging plausible for more than one person.')
    for z in (29, 30):
        d.counter(38, 0, z, 'east', 'oak')
    d.shelf(38, 2, 29, 'east', 'minecraft:bowl', 'Crew bowls')
    d.shelf(38, 2, 30, 'east', 'minecraft:bread', 'Bread for the crew')
    d.put(40, 2, 29, 'handcrafted:wood_plate', facing='south', pieces=2, waterlogged=False)
    d.barrel(39, 0, 33, 'Crew linen', ['minecraft:white_wool', 'minecraft:string'])
    for part, z in (('head', 28), ('foot', 29)):
        d.put(40, 5, z, 'minecraft:light_blue_bed', facing='north', part=part, occupied=False)
    d.rug(39, 32, 41, 33, 4, 'light_blue')
    d.room_goal('lodging', 0, (40, 31))
    d.scene('keeper', 'Rose Compass studio and home', 'Paint-like glazed pots, actual brush and paper displays, a desk and a window-side sitting group make the tall home belong to a specific person.')
    for z in (31, 32):
        d.counter(49, 1, z, 'east', 'oak', 'calcite')
    d.shelf(49, 3, 31, 'east', 'minecraft:brush', 'Studio brush')
    d.shelf(49, 3, 32, 'east', 'minecraft:paper', 'Sketch paper')
    d.put(51, 3, 31, 'handcrafted:blue_glazed_thin_pot')
    d.chair(52, 1, 31, 'west', 'oak')
    d.put(50, 2, 34, 'handcrafted:oak_desk', facing='east', color='none', waterlogged=False)
    d.room_goal('keeper', 1, (51, 32))
    d.counter(49, 9, 30, 'east', 'oak')
    d.put(49, 11, 30, 'handcrafted:white_glazed_medium_pot')
    d.rug(50, 33, 52, 34, 13, 'pink')


def cooper_and_court(d):
    d.scene('archhouse', 'Needle Court cooper repair bay', 'A real fitted repair bench, shears/iron-hoop display, mending supplies and a small wheeled load occupy the side pocket while the covered passage remains two blocks clear.')
    for z in (29, 30, 31):
        d.counter(25, 0, z)
    d.shelf(25, 2, 29, 'east', 'minecraft:shears', 'Cooper repair tools')
    d.shelf(25, 2, 30, 'east', 'minecraft:iron_nugget', 'Spare iron hoops')
    d.put(25, 2, 31, 'handcrafted:terracotta_thin_pot')
    d.put(26, 1, 30, 'mcwholidays:hay_wheelbarrow', facing='south')
    d.table(26, 0, 32)
    d.put(26, 2, 32, 'handcrafted:stackable_book', books=1, facing='east', seed=13)
    d.barrel(25, 0, 32, 'Barrel repair stock', ['minecraft:stick', 'minecraft:iron_nugget', 'supplementaries:rope'])
    d.candle(25, 3, 28, wall=True)
    d.room_goal('archhouse', 0, (26, 29))
    d.scene(None, 'A small tea and potting court', 'The alley reveals planted shelves, a pair of seats, a real potting basket and flowers, with the route around the tree kept open.')
    d.put(30, 2, 39, 'handcrafted:wood_plate', facing='north', pieces=2, waterlogged=False)
    d.put(31, 1, 38, 'handcrafted:spruce_side_table')
    d.candle(31, 2, 38)
    d.put(30, 1, 37, 'handcrafted:terracotta_thick_pot')
    d.put(33, 1, 38, 'supplementaries:lunch_basket', facing='north', dyed=False,
          hanging=False, open=False, waterlogged=False)
    d.put(33, 1, 40, 'minecraft:potted_fern')
    # Low gravel patches and a threshold drain imply wear through construction,
    # not arbitrary noisy replacement of every street tile.
    for x, z in ((27, 28), (27, 29), (27, 30), (28, 33), (29, 34), (30, 35)):
        d.put(x, 0, z, 'minecraft:gravel')
    d.put(27, 1, 34, 'mcwholidays:pumpkin_wheelbarrow', facing='north')


def planted_window_boxes(d):
    d.scene(None, 'Real planted window boxes', 'Replace bulky full-block potted ledges with compact Supplementaries flower boxes holding three real flowers each. The pinned ItemDisplayTile loads these actual item slots on both sides.')
    locations = [('chandler', 4, 4, 20, 'south'), ('chandler', 4, 8, 20, 'south'),
                 ('bookbinder', 5, 5, 24, 'north'), ('inn', 23, 4, 16, 'south'),
                 ('inn', 23, 8, 16, 'south'), ('harbormaster', 47, 5, 21, 'south'),
                 ('lodging', 39, 4, 24, 'north'), ('keeper', 49, 5, 26, 'north')]
    by = {b.ident: b for b in designs()}
    for ident, x, floor, wallz, facing in locations:
        d.p.zone = by[ident].name
        oz = 1 if facing == 'south' else -1
        for xx in (x, x+1):
            for y in (floor+1, floor+2):
                state = d.p.blocks.get((xx, y, wallz+oz), '').split('[', 1)[0]
                if state == 'minecraft:spruce_trapdoor' or state.startswith('minecraft:potted_'):
                    d.air(xx, y, wallz+oz)
        xx = x+1
        backing = d.p.blocks.get((xx, floor+1, wallz), '').split('[', 1)[0]
        if backing == 'minecraft:air' or backing.startswith('mcwwindows:'):
            raise UserError('A planted box lacks a solid authored sill')
        d.inventory((xx, floor+1, wallz+oz), 'supplementaries:flower_box',
                    ['minecraft:allium', 'minecraft:cornflower', 'minecraft:azure_bluet'],
                    by[ident].name+' flowers', slots=3,
                    face='wall', facing=facing, light_level=0, waterlogged=False)
        d.supports.append({'fixture': [xx, floor+1, wallz+oz], 'support': [xx, floor+1, wallz], 'type': 'solid window sill'})


def room_access(d):
    """Conservative full-body paths to each authored furniture group's standing spot."""
    paths = []
    by = {b.ident: b for b in designs()}
    for ident, floor, goal in d.rooms_to_check:
        b = by[ident]
        level = (floor-b.base)//4
        cells = b.levels[level]
        row = next(r for r in d.p.routes if r['id'] == ident+'-landing-'+str(level))
        start = (int(row['local_player_feet'][0][0]), int(row['local_player_feet'][0][2]))
        def clear(cell):
            return cell in cells and all(d.p.blocks.get((cell[0], floor+dy, cell[1]), 'minecraft:air') == 'minecraft:air' for dy in (1, 2))
        if not clear(goal):
            raise UserError('Furnished group lacks its actual planned standing space: '+str((ident, floor, goal)))
        queue, prev = deque([start]), {start: None}
        while queue and goal not in prev:
            x, z = queue.popleft()
            for cell in ((x-1, z), (x+1, z), (x, z-1), (x, z+1)):
                if cell not in prev and clear(cell):
                    prev[cell] = (x, z)
                    queue.append(cell)
        if goal not in prev:
            raise UserError('Furnished group is cut off from its real stair landing: '+str((ident, floor, goal)))
        cells, cell = [], goal
        while cell is not None:
            cells.append(cell)
            cell = prev[cell]
        paths.append({'building': ident, 'floor': floor, 'standing_spot': list(goal), 'clear_path': [list(q) for q in cells[::-1]]})
    return paths


def bed_pairs(d):
    pairs = 0
    for (x, y, z), state in d.p.blocks.items():
        key, _, raw = state.partition('[')
        if not key.endswith('_bed') or not raw:
            continue
        props = dict(part.split('=') for part in raw.rstrip(']').split(','))
        if props.get('part') not in ('head', 'foot'):
            continue
        dx, dz = {'north': (0, -1), 'south': (0, 1), 'west': (-1, 0), 'east': (1, 0)}[props['facing']]
        direction = 1 if props['part'] == 'foot' else -1
        other = d.p.blocks.get((x+dx*direction, y, z+dz*direction), '')
        expected = props|{'part': 'head' if props['part'] == 'foot' else 'foot'}
        if other != key+'['+','.join(k+'='+v for k, v in sorted(expected.items()))+']':
            raise UserError('A detail partially overwrote a real bed: '+str((x, y, z)))
        pairs += props['part'] == 'head'
    return pairs


def check(d):
    clear = planned_clearance(d.p)
    if clear['blocked']:
        raise UserError('Lived-in detail obstructed an existing route: '+str(clear['blocked'][:10]))
    for z in range(21, 36):
        for x in (28, 29):
            if any(d.p.blocks.get((x, y, z), 'minecraft:air') != 'minecraft:air' for y in (1, 2)):
                raise UserError('Cooper scene obstructed the two-wide courtyard passage')
    return {'materials': building_material_checks(d.p), 'planned_clearance': clear,
            'two_wide_lane': lane_width(d), 'two_wide_alley': True, 'furniture_access': room_access(d),
            'complete_actual_beds': bed_pairs(d)}


def construct(registry):
    d = Life(r2(registry).p)
    lighter_soffits(d)
    chandler(d)
    sailmaker(d)
    tavern(d)
    bookshop(d)
    apothecary(d)
    coastal_trades(d)
    homes(d)
    cooper_and_court(d)
    planted_window_boxes(d)
    return d


def native_delta(d, backup_sha):
    changed = {pos for pos, state in d.p.blocks.items() if d.base.blocks.get(pos) != state}
    if changed & d.protected:
        raise UserError('Lived-in delta touches an original inventory or sign')
    if not 0 < len(changed) <= 8_000:
        raise UserError('Lived-in delta escaped its finite detail scope')
    native = d.p.serialize(backup_sha)
    ox, oy, oz = d.p.origin
    native['blocks'] = [r for r in native['blocks'] if (r[0]-ox, r[1]-oy, r[2]-oz) in changed]
    native['block_entities'] = [r for r in native['block_entities']
        if tuple(r['pos'][i]-d.p.origin[i] for i in range(3)) in d.new_entities]
    native['name'] = 'Signal Lane — lived-in trade rooms and alley stories r3 (delta only)'
    native['landmarks'] = []
    native['baseline_sha256'] = R2_SHA
    return native, changed


def prepare(home, registry_path, r1_path, r2_path, destination, backup_sha):
    home, destination = Path(home).resolve(), Path(destination).resolve()
    if home.drive.upper() != 'D:' or not destination.is_relative_to(home/'staging') or destination.exists():
        raise UserError('Use a NEW bounded private D: staging folder')
    if not re.fullmatch('[0-9a-f]{64}', backup_sha):
        raise UserError('The actual reviewed current staging backup SHA is required')
    for path, limit in ((registry_path, 8*MIB), (r1_path, 4*MIB), (r2_path, 4*MIB)):
        if Path(path).stat().st_size > limit:
            raise UserError('Lived-in input exceeds its finite read bound')
    if digest(Path(r1_path)) != BASELINE_SHA or digest(Path(r2_path)) != R2_SHA:
        raise UserError('Lived-in detail binds only the exact placed r1 and r2 plans')
    for filename, sha in DISPLAY_ARTIFACTS.items():
        if digest(home/'server'/'mods'/filename) != sha:
            raise UserError('The inspected native display codec artifact changed')
    registry = json.loads(Path(registry_path).read_text(encoding='utf-8'))
    if not Path(registry['world_path']).resolve().is_relative_to(home/'staging'):
        raise UserError('Private staging registry required; official world refused')
    baseline1 = json.loads(Path(r1_path).read_text(encoding='utf-8'))
    baseline2 = json.loads(Path(r2_path).read_text(encoding='utf-8'))
    if any(row['world_path'] != registry['world_path'] or row['seed'] != registry['seed'] for row in (baseline1, baseline2)):
        raise UserError('Lived-in inputs refer to different staging worlds')
    guard = subprocess.run(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(GUARD),
        '-EstimatedCBytes', '0', '-EstimatedDBytes', str(MAX_BUNDLE)], capture_output=True, text=True,
        creationflags=subprocess.CREATE_NO_WINDOW, check=False)
    reserve = json.loads(guard.stdout)
    if guard.returncode or not reserve.get('allowed'):
        raise UserError('Reserve guard refused the bounded lived-in delta')
    prior = r2(registry)
    verify_baseline(prior, baseline1, ORIGIN)
    expected2, _ = r2_delta(prior, backup_sha)
    decode = lambda row: {(x, y, z): row['palette'][i] for x, y, z, i in row['blocks']}
    if decode(expected2) != decode(baseline2) or expected2['block_entities'] != baseline2['block_entities']:
        raise UserError('Frozen r2 source no longer matches its exact placed plan')
    d = construct(registry)
    checks = check(d)
    native, changed = native_delta(d, backup_sha)
    data = (json.dumps(native, separators=(',', ':'), ensure_ascii=False)+'\n').encode()
    sha = hashlib.sha256(data).hexdigest()
    manifest = {'format': 'awft-street-lived-in:3', 'created': utcnow(), 'prototype_only': True,
        'source_sha256': digest(Path(__file__)), 'registry_sha256': digest(Path(registry_path)),
        'baseline_r1_sha256': BASELINE_SHA, 'baseline_r2_sha256': R2_SHA, 'plan_sha256': sha,
        'reviewed_staging_backup_sha256': backup_sha, 'changed_positions': len(changed),
        'new_display_and_storage_BEs': len(d.new_entities), 'existing_inventory_and_sign_positions_preserved': len(d.protected),
        'existing_BEs_replayed': 0, 'entity_commands': 0, 'groups': d.groups, 'checks': checks,
        'display_codec_provenance': {'actual_jars': DISPLAY_ARTIFACTS,
            'pinned_class_chain': 'FlowerBoxBlockTile(3 slots) / ItemShelfBlockTile(1 slot) -> Moonlight ItemDisplayTile -> vanilla ContainerHelper.loadAllItems / saveAllItems',
            'scope': 'Actual pinned class inspection; native display rendering and interaction still pending'},
        'new_inventories': [{'local': list(pos)}|info for pos, info in sorted(d.new_entities.items())],
        'fixture_supports': d.supports, 'storage_guard': reserve,
        'expected_changes': [{'local': list(pos), 'before': d.base.blocks.get(pos, 'minecraft:air'), 'after': d.p.blocks[pos]} for pos in sorted(changed)],
        'visual_inputs': ['after-r2/street-west.png', 'after-r2/inn-bend.png', 'after-r2/quay-frontage.png',
                          'after-r1/covered-alley.png', 'after-r1/chandler-interior.png'],
        'visual_status': 'UNVERIFIED r3: exact native screenshots, furniture walking, item displays and light review required',
        'owner_acceptance': 'not inferred'}
    rendered = (json.dumps(manifest, sort_keys=True, indent=2)+'\n').encode()
    if len(data)+len(rendered) > MAX_BUNDLE:
        raise UserError('Lived-in detail bundle exceeded finite allocation')
    destination.mkdir(parents=True, exist_ok=False)
    path = destination/('signal-lane-lived-in-r3-'+sha[:16]+'.json')
    path.write_bytes(data)
    (destination/'manifest.json').write_bytes(rendered)
    return {'plan': str(path), 'sha256': sha, 'changed_positions': len(changed),
            'new_BEs': len(d.new_entities), 'existing_BEs_replayed': 0, 'native_visual_review': 'pending'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--home', type=Path, default=Path(r'D:\A World for Two'))
    parser.add_argument('--registry', type=Path, required=True)
    parser.add_argument('--r1', type=Path, required=True)
    parser.add_argument('--r2', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--backup-sha256', required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.home, args.registry, args.r1, args.r2, args.output, args.backup_sha256), indent=2))
