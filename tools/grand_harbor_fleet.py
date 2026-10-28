"""Original, world-neutral harbor vessels. This module never contacts Minecraft.

X is athwartships, Z increases aft, and local Y=0 is the waterline. Exports are
authoring templates, deliberately not executable native settlement plans. The
master owns world selection, current-state admission and every placement.
"""
from __future__ import annotations

import argparse
from collections import deque
from dataclasses import asdict, dataclass
import gzip
import hashlib
import io
import json
import math
from pathlib import Path
import subprocess

import nbtlib

from control_room.common import UserError
from tools.artistic_ship import (
    AIR, ArtisticShip, SEAL_BLOCKS, TIMBER_FINISH, build as build_lark, interpolate,
)
from tools.artistic_materials import require_material_rule
from tools.settlement import Plan


MAX_SHIP_CELLS = 180_000
MAX_EXPORT_BYTES = 32 * 1024**2
RESERVE_GUARD = Path(r'C:\Users\kkids\AppData\Local\AeroStorageWatch\ReserveGuard.ps1')
FLEET_ORDER = ('rosewater-lark', 'golden-petrel', 'resolute-wren', 'mercy-of-the-tide')
SMALLCRAFT_KEYS = ('tern-pilot-cutter', 'salt-marigold-ketch', 'reed-fin-river-lighter')
ALL_VESSELS = FLEET_ORDER + SMALLCRAFT_KEYS
TIMBERS = ('chipped:detailed_dark_oak_planks', 'chipped:nailed_dark_oak_planks',
           'chipped:stacked_dark_oak_planks', 'chipped:vertical_dark_oak_planks',
           'chipped:detailed_spruce_planks')
REFERENCES = (
    {'url': 'https://www.rmg.co.uk/collections/objects/rmgc-object-83146',
     'use': '1756 Liverpool proposal: fine entry, waterline stations, sheer and tumblehome; not a traced replica'},
    {'url': 'https://kaapskil.nl/en/discover/collection-highlights/fluyt-ship-cross-section/',
     'use': 'Seventeenth-century fluyt: broad cargo body, pear-shaped stern, three masts and small crew; minimal armament'},
    {'url': 'https://catalogs.marinersmuseum.org/object/CL6374',
     'use': 'Brooking, c.1750: two-masted armed brig, square fore rig and after driver; comparative silhouette'},
    {'url': 'https://ussconstitutionmuseum.org/2016/07/14/decks/',
     'use': 'Comparative late-eighteenth-century deck functions, beams and knees, not identical plans'},
    {'url': 'https://educators.ussconstitutionmuseum.org/image/hammock-arrangement/',
     'use': 'David Steel 1794 hammock organization; compact berthing and clear service lanes'},
)


@dataclass(frozen=True)
class ShipSpec:
    key: str
    name: str
    role: str
    period: str
    berth: str
    sail_state: str
    stations: tuple
    decks: tuple  # hold, berth, gun/shelter, weather, quarterdeck
    tumblehome: float
    fore_end: int
    quarter_start: int
    mast_positions: tuple
    mast_heights: tuple
    gun_stations: tuple
    accent: str
    cargo: str
    galley_side: int
    berth_stations: tuple
    stern: str

    @property
    def fore(self):
        return self.stations[0][0]

    @property
    def aft(self):
        return self.stations[-1][0]

    @property
    def keel(self):
        return self.decks[0] - 1

    @property
    def weather(self):
        return self.decks[3]


SPECS = {
    'golden-petrel': ShipSpec(
        'golden-petrel', 'Golden Petrel', 'Baltic grain fluyt and victualler',
        'c.1690-1720 interpretation', 'dockside', 'furled',
        ((-37, .4), (-34, 2.5), (-30, 5.5), (-24, 8.7), (-17, 10.5),
         (-7, 11.7), (5, 11.9), (16, 11.4), (25, 9.9), (31, 7.8), (36, 5.1)),
        (-7, -2, 3, 8, 14), .68, -25, 20,
        (-23, 1, 25), (53, 60, 44), (-15, 11), 'green', 'grain', -1,
        (-17, -11, -5), 'pear'),
    'resolute-wren': ShipSpec(
        'resolute-wren', 'Resolute Wren', 'Fast dispatch brig and harbor escort',
        'c.1750-1780 interpretation', 'dockside', 'furled',
        ((-33, .3), (-30, 2.4), (-26, 4.9), (-21, 7.0), (-13, 8.8),
         (-3, 9.1), (9, 8.8), (19, 7.8), (26, 6.0), (32, 4.0)),
        (-5, -1, 3, 7, 11), .86, -23, 19,
        (-18, 12), (44, 50), (-17, -11, -5, 1, 7, 13), 'red', 'dispatch', 1,
        (-16, -10, -4, 2), 'low-counter'),
    'mercy-of-the-tide': ShipSpec(
        'mercy-of-the-tide', 'Mercy of the Tide', 'Ocean storeship and relief transport',
        'c.1730-1760 interpretation', 'dockside', 'hanging-dry',
        ((-44, .4), (-41, 2.2), (-37, 4.9), (-31, 8.0), (-23, 10.6),
         (-12, 12.1), (1, 12.3), (15, 11.8), (27, 10.2), (36, 7.8), (44, 5.4)),
        (-8, -3, 2, 7, 13), .81, -29, 24,
        (-28, 0, 29), (58, 67, 49), (-25, -17, -9, 9, 17), 'blue', 'relief', -1,
        (-24, -18, -12, -6, 13), 'gallery'),
}


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False)+'\n').encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def identifier(state):
    return state.split('[', 1)[0]


class FleetShip(ArtisticShip):
    """Reuse strict native state helpers and proven rope family, not hull geometry."""

    def __init__(self, registry, spec):
        super().__init__(registry, (0, 0, 0), 0)
        self.spec = spec
        self.zone = spec.name
        self.entry = (3, spec.weather, 0)
        self.route_clearance = set()
        self.emergency_ladder = []
        self.fittings = []

    def top(self, z):
        s = self.spec
        return round(interpolate(((s.fore, s.weather+3), (s.fore_end, s.weather),
                                  (s.quarter_start-3, s.weather), (s.aft, s.weather+4)), z))

    def width(self, z, y):
        s = self.spec
        if not s.fore <= z <= s.aft or not s.keel <= y <= max(self.top(z)+1, s.decks[4]+1):
            return -1
        if y < -3 and (z < s.fore+round((-y-3)*1.2) or z > s.aft-round((-y-3)*1.2)):
            return -1
        section = ((s.keel, .16), (s.keel+1, .49), (s.keel+2, .74),
                   (-3, .97), (0, 1.0), (s.weather, .89), (s.decks[4]+1, s.tumblehome))
        return max(0, round(interpolate(s.stations, z)*interpolate(section, y)))

    def put(self, x, y, z, key, **properties):
        s = self.spec
        if (any(type(v) is not int for v in (x, y, z)) or
                not (-34 <= x <= 34 and s.keel <= y <= 76 and s.fore-26 <= z <= s.aft+8)):
            raise UserError('Fleet structure exceeded its finite local envelope: '+str((x, y, z)))
        # Board lengths, strake seams and frame heads have distinct timber roles.
        # No random recoloring, and orientation never counts as a material break.
        if key in ('minecraft:birch_planks', 'minecraft:spruce_planks', 'minecraft:dark_oak_planks'):
            if z % 8 == 0:
                key = ('minecraft:dark_oak_log' if y % 8 == 0 else 'minecraft:oak_wood') if x % 8 == 0 else ('minecraft:oak_log' if y % 4 == 0 else 'minecraft:stripped_birch_log')
                properties = {'axis': 'x'}
            elif y % 4 == 0 and key != 'minecraft:birch_planks':
                key = 'minecraft:stripped_oak_wood' if x % 4 == 0 else 'minecraft:dark_oak_log'
                properties = {'axis': 'z'}
            elif x % 4 == 0:
                key, properties = 'minecraft:oak_planks', {}
        elif key in ('minecraft:stripped_dark_oak_log', 'minecraft:stripped_spruce_log', 'minecraft:dark_oak_log'):
            axis = properties.get('axis', 'y')
            coordinate = {'x': x, 'y': y, 'z': z}[axis]
            key = ('minecraft:stripped_spruce_log' if axis == 'y' else 'minecraft:dark_oak_log' if coordinate % 8 == 0 else
                   {'x': 'minecraft:stripped_dark_oak_log', 'y': 'minecraft:stripped_spruce_log', 'z': 'minecraft:stripped_oak_log'}[axis])
            properties = {'axis': axis}
        elif key in ('minecraft:dark_oak_slab', 'minecraft:spruce_slab'):
            if z % 8 == 0:
                key = 'minecraft:jungle_slab' if x % 8 == 0 else 'minecraft:spruce_slab'
            else:
                key = 'minecraft:oak_slab' if x % 4 == 0 else 'minecraft:dark_oak_slab'
        elif key == 'minecraft:dark_oak_stairs' and z % 8 == 0:
            key = 'minecraft:oak_stairs'
        if key in TIMBER_FINISH:
            key, properties = TIMBER_FINISH[key], {}
        if (x, y, z) in self.shell_cells and y <= 0 and key not in SEAL_BLOCKS:
            raise UserError('Interior fitting would open the watertight hull: '+str((x, y, z)))
        Plan.put(self, x, y, z, key, **properties)
        if len(self.blocks) > MAX_SHIP_CELLS:
            raise UserError('Split the bounded ship authoring template')

    def bed(self, x, floor, z, color='blue'):
        for dz, part in ((0, 'foot'), (1, 'head')):
            self.put(x, floor+1, z+dz, 'minecraft:'+color+'_bed', facing='south', part=part, occupied=False)

    def doorway(self, z, floor, width):
        self.box(-width, floor+1, z, width, floor+3, z, 'minecraft:dark_oak_planks')
        for x in (2, 3):
            for dy, half in ((1, 'lower'), (2, 'upper')):
                self.put(x, floor+dy, z, 'minecraft:oak_door', facing='south', half=half,
                         hinge='left' if x == 2 else 'right', open=False, powered=False)

    def floor_lamp(self, x, floor, z):
        self.put(x, floor+1, z, 'minecraft:dark_oak_fence')
        self.put(x, floor+2, z, 'minecraft:lantern', hanging=False, waterlogged=False)

    def inboard(self, preferred, y, z):
        """Fit a locker inside this station's bilge without replacing its shell."""
        side = -1 if preferred < 0 else 1
        x = preferred
        while abs(x) and (abs(x) >= self.width(z, y) or (x, y, z) in self.shell_cells):
            x -= side
        if preferred > 0 and x < 4:
            raise UserError('Station is too narrow for a locker outside the service lane')
        return x


def hull(p):
    s = p.spec
    for z in range(s.fore, s.aft+1):
        for y in range(s.keel, p.top(z)+2):
            w = p.width(z, y)
            for x in range(-w, w+1):
                exposed = abs(x) == w or any(abs(x) > p.width(z+dz, y+dy)
                                             for dy, dz in ((-1, 0), (0, -1), (0, 1)))
                if exposed:
                    p.put(x, y, z, 'minecraft:dark_oak_planks' if y <= 1 else 'minecraft:spruce_planks')
                    if y <= 0:
                        p.shell_cells.add((x, y, z))
                elif y in s.decks[:4]:
                    p.put(x, y, z, 'minecraft:spruce_planks')
                else:
                    p.put(x, y, z, AIR)
        for side in (-1, 1):
            for y in (p.top(z)-2, p.top(z)+1):
                w = p.width(z, y)
                if w > 0:
                    p.put(side*w, y, z, 'minecraft:dark_oak_stairs', facing='west' if side < 0 else 'east',
                          half='top', shape='straight', waterlogged=False)
            w = p.width(z, p.top(z)+1)
            if w > 0:
                p.put(side*w, p.top(z)+2, z, 'minecraft:dark_oak_slab', type='bottom', waterlogged=False)
    # Raked stem and gammoned bowsprit; the underwater entry ends before the beak.
    p.spar((0, -2, s.fore+3), (0, s.weather+5, s.fore-4))
    p.spar((0, s.weather+3, s.fore+7), (0, s.weather+12, s.fore-23), 'minecraft:stripped_spruce_log')
    for side in (-1, 1):
        p.spar((side*3, s.weather+2, s.fore+6), (side, s.weather+4, s.fore-5))
        p.spar((side*3, s.weather+2, s.fore+6), (side*3, s.weather+6, s.fore+6))
        p.spar((side, s.weather+4, s.fore-5), (side, s.weather+8, s.fore-5))
        p.rope((side*3, s.weather+6, s.fore+6), (side, s.weather+8, s.fore-5))
    p.rope((0, -1, s.fore+3), (0, s.weather+11, s.fore-22))
    # Belowdeck beams and knees leave two full blocks of headroom.
    for ceiling in s.decks[1:4]:
        for z in range(s.fore+13, s.aft-7, 7):
            w = p.width(z, ceiling-1)-1
            p.box(-w, ceiling-1, z, w, ceiling-1, z, 'minecraft:dark_oak_log', axis='x')
            for side in (-1, 1):
                p.put(side*(w-1), ceiling-2, z, 'minecraft:dark_oak_stairs',
                      facing='west' if side > 0 else 'east', half='top', shape='straight', waterlogged=False)


def raised_decks(p):
    s = p.spec
    for lo, hi, floor in ((s.fore+3, s.fore_end, s.weather+3), (s.quarter_start, s.aft-1, s.decks[4])):
        for z in range(lo, hi+1):
            w = max(1, p.width(z, floor))
            p.box(-w, floor, z, w, floor, z, 'minecraft:spruce_planks')
            for side in (-1, 1):
                p.put(side*w, floor+1, z, 'minecraft:dark_oak_fence')
    # Stern cabin beneath the quarterdeck: tapered walls and restrained windows.
    for z in range(s.quarter_start, s.aft):
        w = max(3, p.width(z, s.weather+2))
        p.box(-w+1, s.weather, z, w-1, s.weather, z, 'minecraft:dark_oak_planks')
        p.box(-w+1, s.weather+1, z, w-1, s.decks[4]-1, z, AIR)
        for side in (-1, 1):
            p.box(side*w, s.weather+1, z, side*w, s.decks[4]-1, z, 'minecraft:dark_oak_planks')
            if s.quarter_start+4 <= z <= s.aft-4 and z % 4 != 0:
                p.box(side*w, s.weather+2, z, side*w, s.weather+3, z, 'minecraft:glass')
    p.doorway(s.quarter_start, s.weather, p.width(s.quarter_start, s.weather+2)-1)
    back = s.aft-1
    w = p.width(back, s.weather+2)
    p.box(-w, s.weather+1, back, w, s.decks[4]-1, back, 'minecraft:dark_oak_planks')
    for x in range(-w+1, w):
        if x % 2 == 0:
            p.box(x, s.weather+2, back, x, s.weather+3, back, 'minecraft:glass')
        p.put(x, s.decks[4], back+1, 'minecraft:dark_oak_slab', type='top', waterlogged=False)
    if s.stern == 'pear':
        # Deep merchant body contracts into a high, narrow rounded aftercastle.
        for z in range(s.aft-9, s.aft):
            w = max(2, p.width(z, s.decks[4])//2)
            p.box(-w, s.decks[4]+1, z, w, s.decks[4]+1, z, 'minecraft:dark_oak_slab',
                  type='bottom', waterlogged=False)
    elif s.stern == 'gallery':
        for side in (-1, 1):
            for z in range(s.aft-11, s.aft-3):
                x = side*(p.width(z, s.weather+2)+1)
                p.put(x, s.weather, z, 'minecraft:dark_oak_slab', type='top', waterlogged=False)
                p.put(x, s.weather+1, z, 'minecraft:dark_oak_fence')
                p.put(x, s.weather+2, z, 'minecraft:glass')
                p.put(x, s.weather+3, z, 'minecraft:dark_oak_trapdoor', facing='west' if side < 0 else 'east',
                      half='top', open=False, powered=False, waterlogged=False)
    for side in (-1, 1):
        p.floor_lamp(side*min(w, 3), s.decks[4], s.aft-3)
    # Short, attached stairs connect both raised working platforms.
    for low, high, start, direction in ((s.weather, s.weather+3, s.fore_end+3, -1),
                                       (s.weather, s.decks[4], s.quarter_start-(s.decks[4]-s.weather), 1)):
        for n in range(1, high-low+1):
            z = start+direction*(n-1)
            for x in (4, 5):
                p.box(x, low, z, x, low+n-1, z, 'minecraft:dark_oak_planks')
                p.stair(x, low+n, z, 'south' if direction > 0 else 'north')
                p.box(x, low+n+1, z, x, low+n+2, z, AIR)
        z = start+direction*(high-low)
        p.box(4, high, z, 5, high, z, 'minecraft:spruce_planks')
        p.box(4, high+1, z, 5, high+2, z, AIR)


def magazine_and_stores(p):
    s = p.spec
    floor = s.decks[0]
    z0 = s.aft-18
    p.doorway(z0, floor, min(5, p.width(z0, floor+2)-1))
    for z in range(z0+1, s.aft-7):
        for side in (-1, 1):
            p.box(side*4, floor+1, z, side*4, floor+3, z, 'minecraft:dark_oak_planks')
    for z in range(z0+3, s.aft-9, 3):
        p.barrel(-2, floor+1, z)
        p.barrel(0, floor+1, z)
    p.room('Powder magazine', 'hold', (2, floor, z0+3), 'Separated empty casks; no powder, flame, TNT or firing circuit')
    # Cargo forms and manifests deliberately differ among the three vessels.
    for index, z in enumerate(range(s.fore+24, z0-4, 8)):
        if s.cargo == 'grain':
            for x in range(max(p.inboard(-5, floor+1, z+dz) for dz in range(3)), -2):
                for dz in range(3):
                    p.put(x, floor+1, z+dz, 'minecraft:hay_block', axis='y')
            p.box(p.inboard(-6, floor+1, z-1), floor+1, z-1, -2, floor+1, z-1, 'minecraft:birch_trapdoor',
                  facing='north', half='bottom', open=True, powered=False, waterlogged=False)
            p.barrel(p.inboard(5, floor+1, z), floor+1, z)
        elif s.cargo == 'dispatch':
            p.barrel(-4, floor+1, z)
            p.chest(-4, floor+1, z+2, 'Courier chest '+str(index+1), ['minecraft:paper', 'minecraft:compass'])
            p.put(-3, floor+1, z, 'minecraft:cartography_table')
        else:
            for x in range(max(p.inboard(-5, floor+1, z+dz) for dz in range(2)), -2):
                p.put(x, floor+1, z, 'chipped:spruce_crate', facing='up', open=False)
                p.put(x, floor+1, z+1, 'chipped:spruce_crate', facing='up', open=False)
            p.barrel(p.inboard(5, floor+1, z), floor+1, z)
            p.chest(p.inboard(-5, floor+1, z+3), floor+1, z+3, 'Relief supplies '+str(index+1), ['minecraft:bread', 'minecraft:carrot', 'minecraft:honey_bottle'])
    fz = s.fore+19
    p.chest(-3, floor+1, fz, 'Sailmaker and spare cordage', ['minecraft:string', 'minecraft:shears', 'minecraft:white_wool'])
    p.put(-3, floor+2, fz, 'chipped:bundled_white_wool')
    p.chest(p.inboard(5, floor+1, fz+2), floor+1, fz+2, 'Carpenter, cooper and fresh water', ['minecraft:iron_axe', 'minecraft:oak_planks', 'minecraft:water_bucket'])
    p.room('Cargo hold', 'hold', (2, floor, -12), 'Role-specific cargo groups with continuous working passage')
    p.room('Sail and rope storage', 'hold', (2, floor, fz+1), 'Folded canvas, sewing tools, line and repair timber')
    p.floor_lamp(-1, floor, z0-2)
    p.floor_lamp(-1, floor, -15)


def berthing(p):
    s = p.spec
    floor = s.decks[1]
    x = -5 if s.key == 'resolute-wren' else -6
    for side in (-1, 1):
        for z in s.berth_stations:
            xx = abs(x)*side
            for dz in (-1, 2):
                p.box(xx, floor+1, z+dz, xx, floor+3, z+dz, 'minecraft:dark_oak_fence')
            for dz, part in ((0, 'foot'), (1, 'head')):
                p.put(xx, floor+2, z+dz, 'comforts:hammock_white', facing='south', part=part, occupied=False, waterlogged=False)
            p.barrel(xx+(-1 if side > 0 else 1), floor+1, z+3)
    mess_z = 11 if s.key != 'mercy-of-the-tide' else -28
    for z in range(mess_z, mess_z+5):
        p.table(-4, floor+1, z)
        if z % 2:
            p.chair(-6, floor+1, z, 'east')
    p.chest(-3, floor+1, mess_z+6, 'Mess utensils and rations', ['minecraft:bowl', 'minecraft:bread', 'minecraft:cooked_cod'])
    p.room('Crew berthing', 'berth', (2, floor, -8), 'Anchored hammocks and personal lockers; watches share compact space')
    p.room('Crew mess', 'berth', (2, floor, mess_z+2), 'Laid communal table and separate ration locker')
    aft = s.aft-15
    p.doorway(aft, floor, p.width(aft, floor+2)-1)
    for z in (aft+3, aft+4):
        p.table(-2, floor+1, z)
    p.chair(-3, floor+1, aft+3, 'east')
    p.chair(0, floor+1, aft+3, 'west')
    p.chest(-3, floor+1, aft+6, 'Wardroom charts and accounts', ['minecraft:map', 'minecraft:writable_book', 'minecraft:feather'])
    p.bed(-4, floor, aft+1, s.accent)
    p.bed(5, floor, aft+5, s.accent)
    p.barrel(-4, floor+1, aft+4)
    p.barrel(5, floor+1, aft+3)
    p.room('Wardroom', 'berth', (2, floor, aft+3), 'After mess for officers with accounts, charts and table')
    p.room('Officer and lieutenant accommodation', 'berth', (3, floor, aft+6), 'Two separate berths, personal storage and a service passage')
    if s.cargo == 'relief':
        p.bed(-4, floor, 18, 'white')
        p.put(-3, floor+1, 18, 'handcrafted:dark_oak_cupboard', facing='east', type=1)
        p.chest(-4, floor+1, 21, 'Surgeon and relief locker', ['minecraft:paper', 'minecraft:honey_bottle', 'minecraft:white_wool'])
        p.room('Surgeon and relief berth', 'berth', (2, floor, 19), 'One quiet sick berth and unpowered stores cupboard')
    for z in (-19, -1, aft+3):
        p.floor_lamp(-1, floor, z)


def galley_and_guns(p):
    s = p.spec
    floor = s.decks[2]
    gz = s.fore+12
    gx = s.galley_side*5
    face = 'east' if gx < 0 else 'west'
    for dz in range(4):
        p.put(gx, floor, gz+dz, 'minecraft:stone_bricks')
        p.put(gx, floor+1, gz+dz, 'farmersdelight:spruce_cabinet', facing=face)
    p.put(gx, floor+1, gz, 'farmersdelight:stove', facing=face, lit=False)
    p.put(gx, floor+2, gz, 'farmersdelight:cooking_pot', facing=face)
    p.put(gx, floor+2, gz+3, 'farmersdelight:cutting_board')
    p.box(gx, floor+3, gz, gx, s.weather+4, gz, 'minecraft:cobblestone_wall')
    p.chest(gx, floor+1, gz+5, 'Cook and pantry', ['minecraft:bowl', 'minecraft:bread', 'minecraft:cooked_cod'])
    p.room('Galley', 'gun', (2, floor, gz+2), 'Sheltered cold range, flue, prep board and provision cabinet')
    for z in s.gun_stations:
        w = p.width(z, floor+2)
        for side in (-1, 1):
            breech = w-3
            for dx in range(4):
                p.put(side*(breech+dx), floor+1, z, 'minecraft:dark_oak_slab', type='double', waterlogged=False)
            for dx, key in enumerate(('cast_iron_cannon_end', 'cast_iron_cannon_chamber', 'cast_iron_cannon_barrel', 'cast_iron_cannon_barrel')):
                p.put(side*(breech+dx), floor+2, z, 'createbigcannons:'+key, facing='east' if side > 0 else 'west')
            for dy in (1, 3):
                p.put(side*p.width(z, floor+dy), floor+dy, z, AIR)
            p.put(side*p.width(z, floor+4), floor+4, z, 'minecraft:dark_oak_trapdoor',
                  facing='east' if side > 0 else 'west', half='top', open=False, powered=False, waterlogged=False)
            for dz in (-1, 1):
                p.put(side*(breech+1), floor+1, z+dz, 'minecraft:dark_oak_trapdoor',
                      facing='north' if dz < 0 else 'south', half='bottom', open=True, powered=False, waterlogged=False)
            p.guns.append({'side': 'port' if side < 0 else 'starboard', 'breech': [side*breech, floor+2, z],
                           'facing': 'west' if side < 0 else 'east', 'loaded': False, 'assembled': False})
    p.chest(-3, floor+1, s.quarter_start-4, 'Gunner swabs and maintenance', ['minecraft:stick', 'minecraft:iron_nugget', 'minecraft:leather'])
    p.room('Gun deck', 'gun', (2, floor, -4), 'Unloaded native guns with clear inboard service passage; no assembled or firing claim')
    for z in (-16, 1, s.aft-11):
        p.floor_lamp(-1, floor, z)


def captain(p):
    s = p.spec
    f, z = s.weather, s.quarter_start+4
    p.bed(-4, f, z, s.accent)
    for zz in range(z+4, z+7):
        p.box(-p.width(zz, f+2)+1, f+1, zz, -p.width(zz, f+2)+1, f+3, zz, 'minecraft:bookshelf')
    p.put(-3, f+1, s.aft-7, 'handcrafted:dark_oak_desk', facing='south', color='none', waterlogged=False)
    p.put(-2, f+1, s.aft-7, 'minecraft:cartography_table')
    p.put(-2, f+2, s.aft-7, 'lfpirates:ship_in_bottle', facing='north', waterlogged=False)
    p.chair(-3, f+1, s.aft-5, 'north')
    p.put(5, f+1, z+1, 'handcrafted:dark_oak_couch', facing='west', color=s.accent, shape='single', waterlogged=False)
    p.put(5, f+1, z+3, 'handcrafted:dark_oak_side_table', facing='west', color='none', waterlogged=False)
    if s.cargo == 'grain':
        p.chest(-4, f+1, z+3, 'Merchant grain tallies', ['minecraft:wheat', 'minecraft:paper', 'minecraft:emerald'])
        p.put(-1, f+1, z+3, 'supplementaries:globe', facing='north', powered=False, rotation=0, waterlogged=False)
    elif s.cargo == 'dispatch':
        p.chest(-4, f+1, z+3, 'Sealed dispatches', ['minecraft:writable_book', 'minecraft:compass', 'minecraft:spyglass'])
        p.put(-1, f+1, z+3, 'minecraft:cartography_table')
    else:
        p.chest(-4, f+1, z+3, 'Relief mission journal', ['minecraft:writable_book', 'minecraft:map', 'minecraft:poppy'])
        p.put(-1, f+1, z+3, 'handcrafted:dark_oak_cupboard', facing='south', type=1)
    p.floor_lamp(0, f, s.aft-5)
    p.room("Captain's cabin", 'weather', (2, f, z+1), 'Private berth, chart table, correspondence, window seating and ship model')
    p.box(0, s.decks[4]+1, s.quarter_start+1, 0, s.decks[4]+2, s.quarter_start+1,
          'minecraft:dark_oak_log', axis='y')
    p.put(0, s.decks[4]+1, s.quarter_start+2, 'minecraft:dark_oak_fence')
    p.put(0, s.decks[4]+2, s.quarter_start+2, 'create:copper_valve_handle', facing='south')
    p.put(-2, s.decks[4]+1, s.quarter_start+2, 'minecraft:cartography_table')
    p.room('Quarterdeck and helm', 'quarterdeck', (3, s.decks[4], s.quarter_start+2), 'Raised navigation platform with wheel and compass station')


def companionways(p):
    s = p.spec
    lo, hi = s.decks[0], s.weather
    depth = max(b-a for a, b in zip(s.decks[:3], s.decks[1:4]))
    shift = 1 if s.key == 'resolute-wren' else 0
    p.box(-5+shift, lo+1, 4, -1+shift, hi+2, 6+depth, AIR)
    for index, (lower, upper) in enumerate(zip(s.decks[:3], s.decks[1:4])):
        xs = tuple(x+shift for x in ((-5, -4) if index % 2 == 0 else (-2, -1)))
        zs = list(range(5, 5+upper-lower))
        if index % 2:
            zs.reverse()
        for n, z in enumerate(zs, 1):
            for x in xs:
                p.box(x, lower, z, x, lower+n-1, z, 'minecraft:dark_oak_planks')
                p.stair(x, lower+n, z, 'south' if index % 2 == 0 else 'north')
                p.route_clearance.update(((x, lower+n+1, z), (x, lower+n+2, z)))
    for index, floor in enumerate(s.decks[:4]):
        z = 4 if index % 2 == 0 else 5+depth
        p.box(-5+shift, floor, z, 3, floor, z, 'minecraft:spruce_planks')
        p.box(-5+shift, floor+1, z, 3, floor+2, z, AIR)
    # A separate attached ladder cannot be trapped behind the main stair flights.
    for y in range(lo+1, hi+2):
        lx = 1 if s.key == 'resolute-wren' else 6
        p.put(lx+1, y, -9, 'minecraft:stripped_dark_oak_log', axis='y')
        p.put(lx, y, -9, 'minecraft:ladder', facing='west', waterlogged=False)
        p.emergency_ladder.append([lx, y, -9])
    for pos in p.route_clearance:
        if p.local_state(*pos) != AIR:
            raise UserError('Companionway headroom is occupied: '+str(pos))


def working_deck(p):
    s = p.spec
    f = s.weather
    # Foredeck windlass, catheads, bell and two restrained anchor silhouettes.
    z = s.fore_end-3
    for x in (-3, 3):
        p.box(x, f+4, z, x, f+5, z, 'minecraft:dark_oak_log', axis='y')
    p.box(-2, f+5, z, 2, f+5, z, 'minecraft:stripped_spruce_log', axis='x')
    p.put(0, f+6, z, 'create:copper_valve_handle', facing='up')
    p.put(-3, f+4, z+2, 'minecraft:bell', facing='south', attachment='floor', powered=False)
    p.room('Forecastle and anchor handling', 'forecastle', (3, f+3, s.fore_end-2), 'Windlass, bitts, bell and catheads; mooring endpoints require master placement')
    for side in (-1, 1):
        x = side*(max(p.width(z, y) for y in range(-3, f+4))+4)
        p.spar((side*(abs(x)-3), f+3, z), (x, f+3, z))
        for y in range(-2, f+3):
            p.put(x, y, z, 'minecraft:chain', axis='y', waterlogged=y < 0)
        p.box(x-2, -2, z, x+2, -2, z, 'minecraft:iron_bars')
        p.put(x, -1, z, 'minecraft:iron_bars')
    # Hatch coamings and a closed cargo hatch leave the main lane on starboard.
    for x in range(-5, 0):
        for z in range(-4, 3):
            if x in (-5, -1) or z in (-4, 2):
                p.put(x, f+1, z, 'minecraft:spruce_trapdoor' if z in (-4, 2) else 'minecraft:dark_oak_trapdoor',
                      facing='north', half='top', open=True, powered=False, waterlogged=False)
            else:
                p.put(x, f, z, 'minecraft:oak_trapdoor', facing='north', half='top', open=False, powered=False, waterlogged=False)
    p.put(-2, f+1, -11, 'create:large_cogwheel', axis='y', waterlogged=False)
    p.put(-2, f+2, -11, 'create:hand_crank', facing='up', waterlogged=False)
    p.chest(-5, f+1, -13, 'Deck crew: line and maintenance', ['minecraft:string', 'minecraft:stick', 'minecraft:shears'])
    # The lighter sits in visible skids. It is architecture, not a usable entity.
    for z in range(12, 19):
        w = 1 if z in (12, 18) else 2
        p.box(-w, f+1, z, w, f+1, z, 'minecraft:dark_oak_slab', type='bottom', waterlogged=False)
        for side in (-1, 1):
            p.put(side*w, f+2, z, 'minecraft:oak_stairs', facing='east' if side < 0 else 'west', half='bottom', shape='straight', waterlogged=False)
    for z in (13, 17):
        p.box(-1, f+2, z, 1, f+2, z, 'minecraft:spruce_slab', type='bottom', waterlogged=False)
    # A bounded, stopped shipboard cargo derrick; no quay footprint is authored.
    hz = -13
    x = -p.width(hz, f)+1
    p.spar((x, f, hz), (x, f+12, hz))
    p.spar((x, f+12, hz), (x-7, f+10, hz))
    p.rope((x, f+11, hz), (x-6, f+10, hz))
    # One real drive axis reaches the actual lifting tip. The pinned crank's
    # shaft is opposite FACING: this crank is east of its supporting shaft.
    p.box(x-6, f+9, hz, x, f+9, hz, 'create:shaft', axis='x', waterlogged=False)
    p.put(x-7, f+9, hz, 'create:rope_pulley', axis='x')
    p.put(x+1, f+9, hz, 'create:hand_crank', facing='east', waterlogged=False)
    # Reach the manual control from an attached ladder and guarded service
    # platform. The catwalk is offset from the native descending rope/load.
    p.box(x-7, f+7, hz+3, x+1, f+7, hz+6, 'minecraft:spruce_planks')
    p.put(x, f+7, hz+2, 'minecraft:spruce_planks')
    p.box(x, f+6, hz, x, f+6, hz+2, 'minecraft:stripped_dark_oak_log', axis='z')
    for zz in (hz+3, hz+6):
        p.box(x-7, f+6, zz, x+1, f+6, zz, 'minecraft:stripped_dark_oak_log', axis='x')
    for xx in range(x-7, x+2):
        p.put(xx, f+8, hz+6, 'minecraft:birch_fence')
        if xx != x:
            p.put(xx, f+8, hz+3, 'minecraft:birch_fence')
    for zz in (hz+4, hz+5):
        p.put(x-7, f+8, zz, 'minecraft:dark_oak_fence')
        p.put(x+1, f+8, zz, 'minecraft:dark_oak_fence')
    for y in range(f+1, f+9):
        p.put(x, y, hz+1, 'minecraft:ladder', facing='south', waterlogged=False)
    p.room('Cargo derrick operator platform', 'derrick', (x, f+7, hz+4),
           'Backed ladder and guarded service catwalk reach the correctly aligned manual drive')
    p.fittings.append({'kind': 'stopped cargo derrick', 'local_control': [x+1, f+9, hz],
                       'pulley': [x-7, f+9, hz], 'drive_axis': 'x',
                       'load_sweep_bounds': [x-8, f+1, hz-1, x-6, f+8, hz+1],
                       'status': 'Unassembled/uncommissioned; master must verify native empty-load movement, stops and restart. Vanilla-boat retention is not established.'})
    # Attached two-wide boarding stair, with a low landing above the waterline.
    w = p.width(0, f)
    for z in (0, 1):
        p.box(w-1, f+1, z, w+1, f+3, z, AIR)
        p.box(3, f, z, w, f, z, 'minecraft:spruce_planks')
        for n in range(f):
            x, y = w+1+n, f-n
            p.put(x, y-1, z, 'minecraft:dark_oak_planks')
            p.stair(x, y, z, 'west')
            p.box(x, y+1, z, x, y+2, z, AIR)
            p.route_clearance.update(((x, y+1, z), (x, y+2, z)))
    p.box(w+f, 1, -1, w+f+2, 1, 2, 'minecraft:dark_oak_planks')
    p.room('Tender boarding landing', 'boarding', (w+f+1, 1, 0), 'Two-wide attached sea stair; skiff AABB and actual embarkation still require native checks')
    p.fittings.append({'kind': 'boarding interface', 'local_floor': [w+f+1, 1, 0],
                       'quay_attachment': None, 'placement_owner': 'master'})


def canvas(p, z, yard, radius, drop, drying):
    for x in range(-radius+1, radius):
        u = abs(x)/radius
        hang = max(2, round(drop*(1-.42*u*u))) if drying else 1+(abs(x) % 6 == 0)
        for down in range(1, hang+1):
            v = down/hang
            aft = round((2.8 if drying else .5)*(1-u*u)*math.sin(v*math.pi/2))
            key = ('chipped:bundled_white_wool' if down % 4 == 0 else
                   'chipped:knitted_white_wool' if x % 4 == 0 else 'minecraft:white_wool')
            p.put(x, yard-down, z+aft, key)


def rig(p):
    s = p.spec
    for index, (z, top) in enumerate(zip(s.mast_positions, s.mast_heights)):
        lower = round(top*.61)
        p.spar((0, s.decks[0], z), (0, top, z+2), 'minecraft:stripped_spruce_log')
        for y in range(s.weather+1, lower-3):
            p.put(1, y, z+round((y-s.keel)/(top-s.keel)*2), 'minecraft:dark_oak_log', axis='y')
        for y, span in ((lower, 2), (top-9, 1)):
            p.box(-span, y, z, span, y, z+2, 'minecraft:dark_oak_slab', type='top', waterlogged=False)
            p.put(0, y, z, 'minecraft:dark_oak_log', axis='x')
        # A small number of actual supported shrouds avoids the old rope curtain.
        for side in (-1, 1):
            for dz in (-3, 2):
                w = p.width(z+dz, s.weather)+(4 if index == 2 else 1)
                p.box(side*(w-2), s.weather, z+dz, side*w, s.weather, z+dz, 'minecraft:dark_oak_log', axis='x')
                p.box(side*w, s.weather+1, z+dz, side*w, s.weather+2, z+dz, 'minecraft:dark_oak_log', axis='y')
                p.rope((side*w, s.weather+2, z+dz), (side, lower+1, z+1))
        prev = s.fore-18 if index == 0 else s.mast_positions[index-1]
        endpoint_y = s.weather+10 if index == 0 else round(s.mast_heights[index-1]*.6)
        p.put(0, endpoint_y, prev, 'minecraft:dark_oak_log', axis='z')
        p.rope((0, lower+1, z+1), (0, endpoint_y, prev))
        # Mizzen is smaller and carries an after driver rather than three courses.
        mizzen = len(s.mast_positions) == 3 and index == 2
        radius = round(max(w for _, w in s.stations)*(1.02 if mizzen else 1.45 if index == 1 else 1.25))
        for tier, y in enumerate((lower-2, top-12, top-4)):
            if mizzen and tier == 0:
                continue
            r = max(4, round(radius*(1, .75, .42)[tier]))
            mz = z+round((y-s.keel)/(top-s.keel)*2)
            p.spar((-r, y, mz), (r, y, mz), 'minecraft:stripped_spruce_log')
            for side in (-1, 1):
                p.rope((side*r, y, mz), (0, min(top, y+6), mz))
            drying = s.sail_state == 'hanging-dry' and tier < 2
            canvas(p, mz, y, r, 12 if tier == 0 else 9, drying)
        if mizzen or len(s.mast_positions) == 2 and index == 1:
            aft = min(s.aft-3, z+15)
            p.spar((0, lower+3, z+1), (0, lower-4, aft), 'minecraft:stripped_spruce_log')
            if s.sail_state == 'hanging-dry':
                for zz in range(z+2, aft):
                    high = round(lower+3-(zz-z-1)*7/(aft-z-1))
                    for yy in range(s.weather+9, high):
                        p.put(1, yy, zz, 'chipped:knitted_white_wool' if zz % 4 == 0 else 'minecraft:white_wool')
            else:
                p.box(1, lower, z+2, 1, lower, min(aft, z+8), 'chipped:bundled_white_wool')
        for x in range(1, 5):
            p.put(x, top+1, z+2, 'minecraft:'+s.accent+'_wool')
    p.finish_ropes()


def circulation(p):
    """Source walk graph includes oriented stairs and interactable closed doors.

    It never treats furniture, thin rails or air as floors. Native collision and
    the route through the actual open door shapes remain independent evidence.
    """
    support = set(TIMBERS) | SEAL_BLOCKS
    support |= {'minecraft:dark_oak_stairs', 'minecraft:oak_stairs', 'minecraft:stone_bricks'}
    passable = {AIR, 'minecraft:oak_door', 'minecraft:ladder'}
    cells = {pos for pos, state in p.blocks.items() if identifier(state) in support
             and all(identifier(p.local_state(pos[0], pos[1]+n, pos[2])) in passable for n in (1, 2))}
    ladders = set()
    backing = {'north': (0, 0, 1), 'south': (0, 0, -1), 'east': (-1, 0, 0), 'west': (1, 0, 0)}
    for (x, y, z), state in p.blocks.items():
        if identifier(state) != 'minecraft:ladder':
            continue
        facing = dict(part.split('=') for part in state.split('[', 1)[1][:-1].split(','))['facing']
        dx, dy, dz = backing[facing]
        if identifier(p.local_state(x+dx, y+dy, z+dz)) not in SEAL_BLOCKS:
            raise UserError('A ship ladder lacks full-block backing: '+str((x, y, z)))
        if identifier(p.local_state(x, y+1, z)) in passable:
            ladders.add((x, y-1, z))
    cells.update(ladders)
    if p.entry not in cells:
        raise UserError('Weather-deck entry is not clear')
    reached = {p.entry}
    queue = deque(reached)
    while queue:
        x, y, z = queue.popleft()
        for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            for dy in (-1, 0, 1):
                nxt = x+dx, y+dy, z+dz
                if nxt in cells and nxt not in reached:
                    reached.add(nxt)
                    queue.append(nxt)
        for dy in (-1, 1):
            nxt = x, y+dy, z
            if nxt in cells and nxt not in reached and ((x, y, z) in ladders or nxt in ladders):
                reached.add(nxt)
                queue.append(nxt)
    missing = [r['name'] for r in p.rooms if tuple(r['local_anchor']) not in reached]
    if missing:
        raise UserError('Rooms disconnected in conservative source walk graph: '+', '.join(missing))
    return {'rooms_reached': [r['name'] for r in p.rooms], 'reachable_support_cells': len(reached),
            'method': 'Two-high structural block grid, max one-block step; doors interactable; vertical movement only on verified backed ladders',
            'native_collision_walking_and_multiplayer': 'UNVERIFIED'}


def hull_seal(p):
    s = p.spec
    bounds = (-17, s.keel-1, s.fore-2, 17, 0, s.aft+2)
    start = bounds[:3]
    queue, seen = deque([start]), {start}
    sealed = {pos for pos in p.shell_cells if identifier(p.local_state(*pos)) in SEAL_BLOCKS}
    while queue:
        pos = queue.popleft()
        for d in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
            nxt = tuple(a+b for a, b in zip(pos, d))
            if nxt in seen or nxt in sealed or any(not bounds[i] <= nxt[i] <= bounds[i+3] for i in range(3)):
                continue
            seen.add(nxt)
            queue.append(nxt)
    flooded = [r['name'] for r in p.rooms if r['local_anchor'][1] < 0
               and tuple(v+(1 if i == 1 else 0) for i, v in enumerate(r['local_anchor'])) in seen]
    if flooded:
        raise UserError('Outside flood reaches lower interior: '+', '.join(flooded))
    return {'method': 'Six-neighbor source flood below waterline against full-block protected shell',
            'native_water_updates': 'UNVERIFIED', 'shell_cells': len(sealed)}


def derrick_source_check(p):
    fitting = next(row for row in p.fittings if row['kind'] == 'stopped cargo derrick')
    cx, cy, cz = fitting['local_control']
    px, py, pz = fitting['pulley']
    if p.local_state(cx, cy, cz) != p.state('create:hand_crank', facing='east', waterlogged=False):
        raise UserError('The derrick crank must face away from its supporting shaft')
    if (cy, cz) != (py, pz) or identifier(p.local_state(px, py, pz)) != 'create:rope_pulley':
        raise UserError('The actual lifting tip must share the manual drive axis')
    for x in range(px+1, cx):
        if p.local_state(x, cy, cz) != p.state('create:shaft', axis='x', waterlogged=False):
            raise UserError('A shaft is missing between the control and lifting tip')
    x1, y1, z1, x2, y2, z2 = fitting['load_sweep_bounds']
    if any(p.local_state(x, y, z) != AIR for x in range(x1, x2+1)
           for y in range(y1, y2+1) for z in range(z1, z2+1)):
        raise UserError('Source construction intersects the reserved derrick load sweep')
    return {'aligned_manual_shaft_axis': 'x', 'crank_shaft_face': 'west',
            'reserved_load_sweep': fitting['load_sweep_bounds'], 'source_sweep_clear': True,
            'native_assembly_movement_load_retention_and_restart': 'UNVERIFIED'}


def template(p, key, design, checks):
    palette = sorted(set(p.blocks.values()))
    indices = {state: i for i, state in enumerate(palette)}
    lo = [min(v[i] for v in p.blocks) for i in range(3)]
    hi = [max(v[i] for v in p.blocks) for i in range(3)]
    return {'format': 'awft-fleet-template:1', 'key': key, 'design': design,
            'coordinate_system': 'X athwartships, Z aft, Y=0 waterline; no world coordinates',
            'bounds': lo+hi, 'palette': palette,
            'blocks': [[*pos, indices[state]] for pos, state in sorted(p.blocks.items())],
            'block_entities': [{'pos': list(pos), 'nbt': nbt} for pos, nbt in sorted(p.tags.items())],
            'rooms': p.rooms, 'guns': p.guns, 'checks': checks,
            'commands': [], 'entities': [], 'placement_authority': None,
            'status': 'SOURCE DESIGN; no native placement or graphical/gameplay acceptance'}


def build(registry, key):
    if key in SMALLCRAFT_KEYS:
        from tools.grand_harbor_smallcraft import build as build_smallcraft
        return build_smallcraft(registry, key)
    if key == 'rosewater-lark':
        p, checks = build_lark(registry)
        # Preserve the existing authored frigate, normalize its local waterline.
        p.blocks = {(x, y-63, z): state for (x, y, z), state in p.blocks.items()}
        p.tags = {(x, y-63, z): nbt for (x, y, z), nbt in p.tags.items()}
        design = {'name': 'Rosewater Lark', 'role': '28-gun offshore frigate',
                  'berth': 'offshore', 'sail_state': 'partially-unfurled-drying',
                  'basis': 'Existing original R3 frigate, retained as one design; native revision still requires current review',
                  'known_source_support_issue': {'wheel': [0, 17, 25], 'required_north_backing': [0, 17, 24],
                                                 'proposed_connected_backing': [[0, 16, 24], [0, 17, 24]],
                                                 'current_world_state': 'UNKNOWN; master exact preimage required; preserve all current overlays'}}
    elif key in SPECS:
        p = FleetShip(registry, SPECS[key])
        for operation in (hull, raised_decks, magazine_and_stores, berthing, galley_and_guns,
                          captain, working_deck, companionways, rig):
            operation(p)
        checks = {'circulation': circulation(p), 'lower_hull_seal': hull_seal(p), 'cargo_derrick': derrick_source_check(p),
                  'rope_attachments': p.rope_proof, 'materials': require_material_rule(p.blocks, p.spec.name)}
        design = asdict(p.spec)
        design['fittings'] = p.fittings
        design['emergency_ladder'] = p.emergency_ladder
    else:
        raise UserError('Unknown fleet vessel: '+str(key))
    return template(p, key, design, checks)


def capture_recipe(document):
    lo, hi = document['bounds'][:3], document['bounds'][3:]
    weather = document['design'].get('decks', [0, 0, 0, 8])[3]
    rooms = document['rooms']
    views = [
        ('bow', [0, 2, lo[2]-12], [0, 18, 0]),
        ('stern', [0, 4, hi[2]+14], [0, 15, hi[2]-15]),
        ('broadside', [hi[0]+45, 8, 0], [0, 26, 0]),
        ('elevated', [hi[0]+24, 48, lo[2]-5], [0, 18, 0]),
        ('deck', [3, weather+1, -18], [0, weather+5, 18]),
    ]
    for room in rooms:
        if any(word in room['name'].lower() for word in ('cabin', 'hold', 'berthing', 'galley', 'wardroom', 'magazine', 'gun deck')):
            x, y, z = room['local_anchor']
            views.append((room['name'], [x+.5, y+1, z+.5], [x-3, y+2, z+6]))
    return {'key': document['key'], 'local_views': [{'name': n, 'feet': p, 'look_at': t} for n, p, t in views],
            'requires': 'Master grants actual client slot and translates approved vessel origin/rotation; immutable actual Minecraft captures only',
            'status': 'CAPTURE RECIPE ONLY; no image generated'}


def structure_nbt(document):
    """Standard Minecraft structure NBT, original geometry only, no entities.

    Native Minecraft1.21.1 DataVersion3955 was confirmed in the existing save.
    This is an authored structure file, never a save/region/world export.
    The accompanying template bounds retain the offset to its waterline origin.
    """
    low, high = document['bounds'][:3], document['bounds'][3:]
    palette = []
    for state in document['palette']:
        row = {'Name': nbtlib.String(identifier(state))}
        if '[' in state:
            props = dict(part.split('=') for part in state.split('[', 1)[1][:-1].split(','))
            row['Properties'] = nbtlib.Compound({k: nbtlib.String(v) for k, v in props.items()})
        palette.append(nbtlib.Compound(row))
    tags = {tuple(row['pos']): row['nbt'] for row in document['block_entities']}
    blocks = []
    for x, y, z, index in document['blocks']:
        row = {'pos': nbtlib.List[nbtlib.Int]([v-lo for v, lo in zip((x, y, z), low)]),
               'state': nbtlib.Int(index)}
        if (x, y, z) in tags:
            row['nbt'] = nbtlib.parse_nbt(tags[x, y, z])
        blocks.append(nbtlib.Compound(row))
    structure = nbtlib.File({
        'DataVersion': nbtlib.Int(3955),
        'size': nbtlib.List[nbtlib.Int]([b-a+1 for a, b in zip(low, high)]),
        'palette': nbtlib.List[nbtlib.Compound](palette),
        'blocks': nbtlib.List[nbtlib.Compound](blocks),
        'entities': nbtlib.List[nbtlib.Compound]([]),
    })
    buffer = io.BytesIO()
    structure.write(buffer)
    raw = buffer.getvalue()
    if len(raw) > 16*1024**2:
        raise UserError('One authored structure exceeds its finite uncompressed NBT bound')
    return gzip.compress(raw, mtime=0)


def export(registry_path, output, keys=ALL_VESSELS):
    registry_path, output = Path(registry_path), Path(output)
    if not registry_path.is_file() or registry_path.stat().st_size > 8*1024**2:
        raise UserError('Use the finite actual native registry export')
    registry = json.loads(registry_path.read_bytes())
    if output.exists():
        raise UserError('Choose a new immutable export directory')
    if len(set(keys)) != len(keys) or not keys or any(k not in ALL_VESSELS for k in keys):
        raise UserError('Choose distinct known fleet vessels')
    files = {}
    for key in keys:
        doc = build(registry, key)
        files[key+'.json'] = canonical(doc)
        files[key+'-views.json'] = canonical(capture_recipe(doc))
        files[key+'.nbt'] = structure_nbt(doc)
    manifest = {'format': 'awft-grand-harbor-fleet:1', 'ships': list(keys),
                'source_sha256': sha(Path(__file__).read_bytes()),
                'dependencies': {name: sha(Path(__file__).with_name(name).read_bytes()) for name in
                                 ('artistic_ship.py', 'artistic_materials.py', 'grand_harbor_smallcraft.py', 'settlement.py')},
                'native_registry_sha256': sha(registry_path.read_bytes()),
                'files': {name: {'sha256': sha(raw), 'bytes': len(raw)} for name, raw in files.items()},
                'references': REFERENCES, 'world_writes': 0,
                'required_layout': {'offshore_partial_dry': 1, 'dockside_furled': 2, 'dockside_hanging_dry': 1},
                'placement': 'Master approval and exact current target admission required; quay/town footprints are outside this package',
                'structure_offset': 'NBT uses nonnegative coordinates. To preserve the template waterline origin, place its minimum corner at approved origin plus template bounds[0:3], with the same rotation about that waterline origin.',
                'evidence': 'Synthetic source geometry against actual registry; no current native or player acceptance'}
    files['manifest.json'] = canonical(manifest)
    allocation = sum(len(raw) for raw in files.values())
    if allocation > MAX_EXPORT_BYTES:
        raise UserError('Export exceeds its finite32 MiB allocation')
    # Reserve checks occur after size is known and before the first writer.
    drive = output.resolve().drive.upper()
    if drive not in ('C:', 'D:'):
        raise UserError('This host export requires a measured C: or D: destination')
    guard = subprocess.run(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(RESERVE_GUARD),
                            '-EstimatedCBytes', str(MAX_EXPORT_BYTES if drive == 'C:' else 0),
                            '-EstimatedDBytes', str(MAX_EXPORT_BYTES if drive == 'D:' else 0)],
                           capture_output=True, text=True, timeout=30)
    if guard.returncode:
        raise UserError('Storage reserve admission failed: '+guard.stdout.strip())
    try:
        if json.loads(guard.stdout).get('allowed') is not True:
            raise ValueError()
    except (ValueError, TypeError) as exc:
        raise UserError('No authentic passing ReserveGuard result') from exc
    output.mkdir(parents=True, exist_ok=False)
    for name, raw in files.items():
        with (output/name).open('xb') as stream:
            stream.write(raw)
    return {'directory': str(output.resolve()), 'bytes': allocation, 'ships': list(keys),
            'manifest_sha256': sha(files['manifest.json']), 'world_writes': 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--registry', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--ships', nargs='+', choices=ALL_VESSELS, default=list(ALL_VESSELS))
    args = parser.parse_args()
    print(json.dumps(export(args.registry, args.output, args.ships)))


if __name__ == '__main__':
    main()
