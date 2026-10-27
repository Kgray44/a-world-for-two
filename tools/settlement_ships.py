"""Original, surveyed age-of-sail architecture, never a physics-assembled ship.

This module prepares separate immutable construction plans. It does not contact
the server or replace the current native plan. Placement, wet-hull inspection,
hoist commissioning, restart checks and shader review remain separate operations.
"""
from __future__ import annotations

import argparse
import collections
import dataclasses
import json
import math
from pathlib import Path

from control_room.common import Layout, UserError, digest, read_json, write_json, utcnow
from control_room.storage import Storage
from tools.settlement import Plan


FIXED_MASTERS = (
    'master-45e88a165ed60ce438ec5d87094ed476faeebdaa68693ae6d1835a11eeea6aeb.json',
    'pirate-port-master-3bcc8f6bdfaf4d4ff44805e9fc5e5dee1b5b8b07d50916dba04af20a67ba72ba.json',
    'drawbridge-master-cc2bd89a14d86fc1de2236e5a4f92ca523d911bc128fcf96f91c1e6101fb8b69.json',
)
AIR = 'minecraft:air'
RESERVE = (950, -1515, 1300, -1242)


@dataclasses.dataclass(frozen=True)
class Vessel:
    slug: str
    name: str
    role: str
    center: tuple[int, int]
    length: int
    beam: int
    draft: int
    accent: str
    sail_state: str
    masts: tuple[tuple[int, int], ...]
    gun_spacing: int
    berth_rows: int
    offshore: bool = False


VESSELS = (
    Vessel('rosewater-resolute', 'The Rosewater Resolute', 'Offshore flagship',
           (1140, -1450), 79, 23, 8, 'blue', 'partly-unfurled',
           ((-25, 39), (0, 46), (24, 34)), 8, 4, True),
    Vessel('amberwake', 'The Amberwake', 'Full-beamed merchantman',
           (1000, -1350), 63, 21, 7, 'yellow', 'furled',
           ((-18, 33), (5, 39), (23, 26)), 11, 2),
    Vessel('nightingales-debt', "The Nightingale's Debt", 'Lean corsair',
           (1110, -1344), 57, 17, 7, 'red', 'furled',
           ((-16, 35), (10, 39)), 7, 3),
    Vessel('sea-lavender', 'The Sea Lavender', 'Coastal dispatch escort',
           (1230, -1376), 49, 17, 6, 'cyan', 'loose-drying',
           ((-12, 30), (10, 35)), 9, 2),
)


def hull_halfwidth(vessel: Vessel, z: int, dy: int) -> int:
    """Fine entry, full midships, rounded broad transom, and curved bilges."""
    half = vessel.length // 2
    if not -half <= z <= half or not 0 <= dy <= 14:
        return -1
    t = (z + half) / (2 * half)
    # Bow and stern are deliberately different; these are not ellipsoid shells.
    if t < .19:
        longitudinal = .08 + .92 * math.sin(t / .19 * math.pi / 2)
    elif t > .78:
        longitudinal = 1 - .36 * ((t - .78) / .22) ** 1.35
    else:
        longitudinal = 1
    section = (.14, .34, .52, .66, .79, .88, .94, .98, 1, 1, 1, .99, .97, .95, .94)[dy]
    return max(0, round(vessel.beam // 2 * longitudinal * section))


def rope_line(a, b):
    """A face-connected voxel chain, including diagonal standing rigging."""
    current = tuple(a)
    yield current
    delta = [b[i] - a[i] for i in range(3)]
    steps = max(abs(n) for n in delta)
    for n in range(1, steps + 1):
        target = tuple(round(a[i] + delta[i] * n / steps) for i in range(3))
        for axis in range(3):
            while current[axis] != target[axis]:
                move = list(current)
                move[axis] += 1 if target[axis] > current[axis] else -1
                current = tuple(move)
                yield current


class ShipPlan(Plan):
    def __init__(self, registry, survey, vessel, backup, fixed):
        super().__init__(registry, survey, vessel.center, backup)
        self.vessel = vessel
        self.fixed = fixed
        self.rooms = []
        self.routes = set()
        self.ropes = set()
        self.hatches = []
        self.guns = []
        self.depth_checks = []
        self.connections = []
        self.zone = vessel.name
        self.sea = self._sea_level()
        self.keel = self.sea - vessel.draft
        self.main = self.keel + 14
        self.deck_levels = {'hold': self.keel+2, 'berth': self.keel+6,
                            'gun': self.keel+10, 'main': self.main}

    def state(self, key, **properties):
        if key not in self.native:
            raise UserError('Unregistered maritime block ' + key)
        unknown = properties.keys() - self.native[key].keys()
        if unknown:
            raise UserError('Unregistered maritime properties: ' + key + ' ' + ','.join(sorted(unknown)))
        return super().state(key, **properties)

    def put(self, x, y, z, key, **properties):
        wx, wz = self.world(x, z)
        position = wx, y, wz
        if not (RESERVE[0] <= wx <= RESERVE[2] and RESERVE[1] <= wz <= RESERVE[3]):
            raise UserError('Maritime design exceeded its reviewed reserve: ' + str(position))
        state = self.state(key, **properties)
        if position in self.fixed:
            if self.fixed[position] == state:
                return
            raise UserError('Maritime construction intersects completed work: ' + str(position))
        if position in self.protected:
            raise UserError('Maritime construction intersects an existing block entity: ' + str(position))
        return super().put(x, y, z, key, **properties)

    def near_samples(self, x, z):
        wx, wz = self.world(x, z)
        ox, oz = self.origin
        gx = ox + math.floor((wx-ox)/self.step)*self.step
        gz = oz + math.floor((wz-oz)/self.step)*self.step
        positions = [(gx, gz), (gx+self.step, gz), (gx, gz+self.step), (gx+self.step, gz+self.step)]
        if any(position not in self.samples for position in positions):
            raise UserError('Fresh marine survey does not surround the entire requested hull: ' + str((wx, wz)))
        return [self.samples[position] for position in positions]

    def _sea_level(self):
        values = []
        half = self.vessel.length//2
        for z in range(-half, half+1, 4):
            for row in self.near_samples(0, z):
                if 'ocean_floor_y' not in row:
                    raise UserError('A fresh native marine survey with ocean_floor_y is required')
                if row.get('surface', row.get('block', '')).startswith('minecraft:water'):
                    values.append(row['y'])
                elif row['y'] - row['ocean_floor_y'] >= 3:
                    values.append(row['y'])
        if not values:
            raise UserError('Requested ship footprint has no surveyed navigable water')
        sea = collections.Counter(values).most_common(1)[0][0]
        if not 60 <= sea <= 65:
            raise UserError('Review the marine water level before building: ' + str(sea))
        return sea

    def require_depth(self):
        v = self.vessel
        # Conservative upper envelope of four surrounding soundings. No seabed
        # excavation and no inference that a coarse survey proves every voxel.
        for z in range(-v.length//2+1, v.length//2+1, 2):
            for x in range(-hull_halfwidth(v, z, 4), hull_halfwidth(v, z, 4)+1, 2):
                floor = max(row['ocean_floor_y'] for row in self.near_samples(x, z))
                first = next((dy for dy in range(15) if abs(x) <= hull_halfwidth(v, z, dy)), 15)
                bottom = self.keel+first
                if floor+1 > bottom:
                    raise UserError(f'{v.name}: shallow seabed at {self.world(x,z)}, floor={floor}, hull={bottom}; relocate the vessel')
                self.depth_checks.append({'xz': list(self.world(x,z)), 'ocean_floor_y': floor, 'lowest_hull_y': bottom})

    def rope(self, a, b):
        self.ropes.update(rope_line(a, b))

    def finish_ropes(self):
        neighbors = {'west': (-1,0,0), 'east': (1,0,0), 'down': (0,-1,0),
                     'up': (0,1,0), 'north': (0,0,-1), 'south': (0,0,1)}
        for x,y,z in sorted(self.ropes):
            wx,wz = self.world(x,z)
            existing = self.blocks.get((wx,y,wz), AIR)
            if existing != AIR:
                continue
            properties = {name: tuple((x+d[0],y+d[1],z+d[2])) in self.ropes
                          for name,d in neighbors.items()}
            self.put(x,y,z,'supplementaries:rope',knot=False,waterlogged=False,**properties)

    def room(self, name, deck, bounds, purpose, anchor):
        x1,z1,x2,z2 = bounds
        floor = self.deck_levels[deck]
        self.rooms.append({'name': name, 'deck': deck, 'floor_y': floor,
                           'local_bounds': [x1,z1,x2,z2], 'purpose': purpose,
                           'anchor': [*self.world(anchor[0],anchor[1])[:1], floor+1, self.world(anchor[0],anchor[1])[1]]})
        # Two high passage to every named space, connected to the offset main
        # longitudinal aisle. Furniture is placed before these reserved routes.
        ax,az = anchor
        for x in range(min(2,ax),max(2,ax)+1):
            self.routes.add((x,floor,az))
        for z in range(min(3,az),max(3,az)+1):
            self.routes.add((2,floor,z))

    def clear_routes(self):
        for floor in self.deck_levels.values():
            for x in range(-2,3):self.routes.add((x,floor,3))
        for x,y,z in sorted(self.routes):
            dy=y-self.keel
            if abs(x) >= hull_halfwidth(self.vessel,z,dy):
                raise UserError('A named ship room extends beyond its hull-supported deck')
            self.put(x,y,z,'minecraft:spruce_planks')
            self.box(x,y+1,z,x,y+2,z,AIR)

    def verify_circulation(self):
        """Plan geometry only; actual collision shapes are a separate native check."""
        checked=0
        for room in self.rooms:
            floor=room['floor_y']; ax,_,az=room['anchor']
            x,z=ax-self.cx,az-self.cz
            target=(2,3)
            queue=collections.deque([(x,z)]);seen={(x,z)}
            while queue:
                at=queue.popleft()
                if at==target:break
                for dx,dz in ((1,0),(-1,0),(0,1),(0,-1)):
                    nxt=at[0]+dx,at[1]+dz
                    if nxt in seen or abs(nxt[0])>self.vessel.beam//2 or abs(nxt[1])>self.vessel.length//2:
                        continue
                    wx,wz=self.world(*nxt)
                    feet=self.blocks.get((wx,floor+1,wz),AIR)
                    head=self.blocks.get((wx,floor+2,wz),AIR)
                    support=self.blocks.get((wx,floor,wz),AIR)
                    if feet==AIR and head==AIR and support!=AIR:
                        seen.add(nxt);queue.append(nxt)
            else:
                raise UserError('Disconnected room passage in '+room['name'])
            checked+=1
        return {'named_rooms_checked':checked,'method':'Full-block two-high plan corridor reachability; native shape/walking proof pending'}


def hull(p):
    v=p.vessel; half=v.length//2
    for z in range(-half,half+1):
        for dy in range(15):
            w=hull_halfwidth(v,z,dy)
            for x in range(-w,w+1):
                # Seal stepped bilges and tapered waterlines on every face. A
                # side-only outline leaves holes beneath widening hull sections.
                edge=(abs(x)==w or z in (-half,half) or dy==0 or
                      abs(x)>hull_halfwidth(v,z,dy-1) or
                      abs(x)>hull_halfwidth(v,z-1,dy) or
                      abs(x)>hull_halfwidth(v,z+1,dy))
                if edge:
                    block='minecraft:dark_oak_planks'
                    if dy in (8,12):block='minecraft:'+v.accent+'_terracotta'
                    if dy==13:block='minecraft:stripped_spruce_log'
                    p.put(x,p.keel+dy,z,block,**({'axis':'z'} if dy==13 else {}))
                elif dy in (2,6,10,14):
                    p.put(x,p.keel+dy,z,'minecraft:spruce_planks')
                else:p.put(x,p.keel+dy,z,AIR)
        # Separate wales follow the curved waterline and upper hull.
        w=hull_halfwidth(v,z,12)
        for side in (-1,1):
            p.put(side*w,p.keel+12,z,'minecraft:dark_oak_log',axis='z')
        w=hull_halfwidth(v,z,14)
        if z not in (-half,half):
            for side in (-1,1):
                p.put(side*w,p.main+1,z,'minecraft:dark_oak_fence')
    # Tapered bowsprit and supporting gammoning, clear of the forecastle route.
    for n in range(1,15 if v.offshore else 11):
        p.put(0,p.main+3+n//5,-half-n,'minecraft:stripped_dark_oak_log',axis='z')
    p.rope((0,p.main+1,-half+4),(0,p.main+5,-half-(14 if v.offshore else 10)))
    for side in (-1,1):
        for z in range(-half+5,half-4,7):
            w=hull_halfwidth(v,z,14)
            p.put(side*w,p.main+1,z,'minecraft:dark_oak_log',axis='y')
            p.put(side*w,p.main+2,z,'minecraft:lantern',hanging=False,waterlogged=False)
    # Raised stern gallery: windows and modest gilded carving, not a flat box.
    stern=half-1
    for x in range(-hull_halfwidth(v,stern,14)+1,hull_halfwidth(v,stern,14)):
        p.put(x,p.main+2,stern,'minecraft:glass_pane')
        p.put(x,p.main+3,stern,'minecraft:glass_pane')
        p.put(x,p.main+4,stern,'minecraft:dark_oak_trapdoor',facing='south',half='top',open=False,waterlogged=False)
        if x%3==0:p.put(x,p.main+1,stern,'minecraft:'+v.accent+'_terracotta')
    p.put(0,p.main+5,stern,'treasure2:skull_and_crossbones',facing='south',waterlogged=False)


def partition(p,y,z,x1,x2):
    p.box(x1,y+1,z,x2,y+3,z,'minecraft:dark_oak_planks')
    p.box(1,y+1,z,2,y+2,z,AIR)


def barrel(p,x,y,z,*,title=None,items=()):
    if title:
        p.chest(x,y,z,title,items)
    else:p.put(x,y,z,'minecraft:barrel',facing='up',open=False)


def chart_table(p,x,y,z):
    p.put(x,y,z,'minecraft:cartography_table')
    p.put(x+1,y,z,'handcrafted:dark_oak_desk',facing='south',color='none',waterlogged=False)
    p.put(x+1,y+1,z,'lfpirates:ship_in_bottle',facing='south',waterlogged=False)
    p.put(x+1,y,z+1,'handcrafted:dark_oak_chair',facing='north',color='none',waterlogged=False)


def interiors(p):
    v=p.vessel; q=v.length//2; b=v.beam//2
    hold,berth,gun,main=[p.deck_levels[k] for k in ('hold','berth','gun','main')]
    fore=-q+10; aft=q-10
    # A dedicated magazine in the narrow after hold, separated by a full bulkhead.
    magazine_z=min(aft,q-12)
    for z in range(magazine_z,magazine_z+5):
        w=hull_halfwidth(v,z,2)-1
        if w>=3:
            for x in (-w,w):barrel(p,x,hold+1,z)
    partition(p,hold,magazine_z,-hull_halfwidth(v,magazine_z,2)+1,hull_halfwidth(v,magazine_z,2)-1)
    p.sign(-2,hold+1,magazine_z-1,['Magazine','Sealed display stores','No live powder','Lantern outside only'])
    p.room('Sealed powder magazine','hold',(-3,magazine_z,3,magazine_z+4),
           'Empty safe barrels; isolated from food and galley; no TNT or gunpowder', (2,magazine_z+2))
    p.room('Ballast and cargo hold','hold',(-4,fore,4,magazine_z-2),
           'Low ballast, supply casks, sail and tool lockers; open center handling lane',(2,0))
    p.room('Food and water stores','hold',(-3,fore,3,fore+6),
           'Separate dry provisions and drinking-water casks',(2,fore+3))
    # Cargo variations produce genuinely different working interiors.
    themes={'yellow':('minecraft:hay_block','minecraft:yellow_wool','minecraft:brown_wool'),
            'red':('minecraft:red_wool','chipped:spruce_crate','minecraft:dark_oak_planks'),
            'cyan':('minecraft:cyan_wool','chipped:spruce_crate','minecraft:hay_block'),
            'blue':('chipped:spruce_crate','minecraft:blue_wool','minecraft:hay_block')}
    for z in range(fore+2,magazine_z-3,5):
        w=hull_halfwidth(v,z,2)-1
        for side in (-1,1):
            if w<3:continue
            x=side*w
            block=themes[v.accent][abs(z)//5%3]
            p.put(x,hold+1,z,block)
            if v.accent=='yellow' and w>=4:p.put(x-side,hold+1,z,block)
            if z%2:barrel(p,x,hold+2,z)
    p.chest(-3,hold+1,0,'Rope, sail and maintenance locker',
            ['minecraft:string','minecraft:white_wool','minecraft:shears','minecraft:lead'])
    p.chest(-3,hold+1,-5,'Ship carpenter: repair stores',
            ['minecraft:iron_axe','minecraft:oak_planks','minecraft:iron_nugget'])
    p.chest(-3,hold+1,fore+4,'Dry pantry',
            ['minecraft:bread','minecraft:dried_kelp','minecraft:carrot'])
    # Forward galley: cold/unlit appliances, no onboard fire or functioning hazard.
    galley_z=fore+1
    for x in range(-b+3,0):
        p.put(x,berth+1,galley_z,'farmersdelight:spruce_cabinet',facing='south')
    p.put(-b+4,berth+1,galley_z,'farmersdelight:stove',facing='south',lit=False)
    p.put(-b+4,berth+2,galley_z,'farmersdelight:cooking_pot',facing='south')
    p.put(-b+3,berth+2,galley_z,'farmersdelight:cutting_board')
    p.room('Forward galley','berth',(-b+2,fore,b-2,fore+5),
           'Cold cooking range, galley storage, preparation board and provisions',(2,fore+3))
    # Real two-part Comforts hammocks, with anchored end posts and clear aisles.
    for side in (-1,1):
        x=side*(b-3)
        for n in range(v.berth_rows):
            z=-8+n*5
            for dz in (-1,2):
                p.box(x,berth+1,z+dz,x,berth+3,z+dz,'minecraft:dark_oak_fence')
            for dz,part in ((0,'foot'),(1,'head')):
                p.put(x,berth+2,z+dz,'comforts:hammock_white',facing='south',part=part,occupied=False,waterlogged=False)
            barrel(p,x-side,berth+1,z)
    p.room('Crew hammock berths','berth',(-b+2,-10,b-2,12),
           'Suspended two-part hammocks with end posts, personal lockers and center passage',(2,-5))
    # Mess tables occupy one side for the cargo ship and both sides on the flagship.
    for side in ((-1,1) if v.offshore else (-1,)):
        x=side*(b-4)
        for z in range(10,min(aft-2,18)):
            p.put(x,berth+1,z,'handcrafted:dark_oak_table',color='none',shape='single',waterlogged=False)
            if z%2:p.put(x+side,berth+1,z,'handcrafted:dark_oak_chair',facing='west' if side>0 else 'east',color='none',waterlogged=False)
    p.room('Crew mess','berth',(-b+2,9,b-2,aft-2),
           'Bench/table eating space and communal meal stores',(2,11))
    # Officer cabins/wardroom on the after berth deck.
    partition(p,berth,aft-1,-hull_halfwidth(v,aft-1,6)+1,hull_halfwidth(v,aft-1,6)-1)
    for side in (-1,1):
        x=side*3
        p.put(x,berth+1,aft+3,'minecraft:blue_bed',facing='north',part='foot',occupied=False)
        p.put(x,berth+1,aft+2,'minecraft:blue_bed',facing='north',part='head',occupied=False)
        barrel(p,x,berth+1,aft+5)
    p.room('Officer berths and wardroom','berth',(-4,aft,4,q-4),
           'Two officer berths behind an after bulkhead, storage and planning space',(2,aft+1))
    # Genuine unloaded Create Big Cannons structural barrels, no assembled mount,
    # cartridges, projectile, firing redstone or powder stored aboard.
    first=-q+12; last=q-13
    for z in range(first,last+1,v.gun_spacing):
        width=hull_halfwidth(v,z,11)
        if width<6:continue
        for side in (-1,1):
            facing='east' if side>0 else 'west'
            x=side*(width-2)
            p.put(x,gun+1,z,'minecraft:dark_oak_slab',type='double',waterlogged=False)
            p.put(x-side,gun+1,z,'minecraft:dark_oak_slab',type='double',waterlogged=False)
            for dz in (-1,1):p.put(x-side,gun+1,z+dz,'minecraft:dark_oak_trapdoor',facing='north' if dz<0 else 'south',half='bottom',open=True,waterlogged=False)
            p.put(x-side,gun+2,z,'createbigcannons:cast_iron_cannon_end',facing=facing)
            p.put(x,gun+2,z,'createbigcannons:cast_iron_cannon_chamber',facing=facing)
            p.put(x+side,gun+2,z,'createbigcannons:cast_iron_cannon_barrel',facing=facing)
            p.put(side*width,gun+1,z,AIR)
            p.put(side*width,gun+2,z,'createbigcannons:cast_iron_cannon_barrel',facing=facing)
            p.put(side*width,gun+3,z,'minecraft:dark_oak_trapdoor',facing=facing,half='top',open=True,waterlogged=False)
            p.rope((x-side,gun+2,z-1),(side*(width-1),gun+2,z-2))
            p.guns.append({'breech': [*p.world(x-side,z)[:1],gun+2,p.world(x-side,z)[1]],'facing':facing,'loaded':False,'assembled':False})
    p.room('Broadside cannon deck','gun',(-b+1,first,b-1,last),
           'Paired unloaded broadside guns, open working lanes and restrained tackle',(2,0))
    chart_table(p,-4,gun+1,aft)
    p.chest(-4,gun+1,aft+4,'Charts and coastal dispatches',
            ['minecraft:map','minecraft:compass','minecraft:feather','minecraft:writable_book'])
    p.room('Navigation office','gun',(-5,aft-1,4,q-5),
           'Chart table, model ship, captain correspondence and navigation stores',(2,aft+1))
    # Personal storytelling, safely separated from the magazine.
    p.chest(-3,berth+1,5,'A private promise, carried over the sea',
            ['minecraft:paper','minecraft:rose_bush','minecraft:gold_nugget'])
    if v.accent=='red':
        p.put(-b+3,gun+1,-q+9,'treasure2:pirate_chest',facing='south')
    # Lighting sits high and near structural beams, not on walking routes.
    for deck in (hold,berth,gun):
        for z in range(fore+3,aft,9):
            p.put(-2,deck+3,z,'minecraft:lantern',hanging=True,waterlogged=False)
    # Distinct deck frames and visible knees.
    for deck in (berth,gun,main):
        for z in range(-q+9,q-7,7):
            w=hull_halfwidth(v,z,deck-p.keel)-1
            p.box(-w,deck-1,z,w,deck-1,z,'minecraft:dark_oak_log',axis='x')
            for side in (-1,1):
                p.put(side*(w-1),deck-2,z,'minecraft:dark_oak_stairs',facing='west' if side>0 else 'east',half='top',shape='straight',waterlogged=False)


def upperworks(p):
    v=p.vessel;q=v.length//2;b=v.beam//2;main=p.main
    aft=q-13
    # Quarterdeck above the captain's cabin, with bevelled stern corners.
    for z in range(aft,q):
        w=hull_halfwidth(v,z,14)
        p.box(-w+1,main+5,z,w-1,main+5,z,'minecraft:spruce_planks')
        for side in (-1,1):
            p.box(side*w,main+1,z,side*w,main+4,z,'minecraft:dark_oak_planks')
            p.put(side*w,main+6,z,'minecraft:dark_oak_fence')
            if z%3==0:
                p.put(side*w,main+2,z,'minecraft:glass_pane')
                p.put(side*w,main+3,z,'minecraft:glass_pane')
    partition(p,main,aft,-hull_halfwidth(v,aft,14)+1,hull_halfwidth(v,aft,14)-1)
    for side in (-1,1):
        for n in range(5):
            x=side*5;z=aft-5+n
            p.put(x,main+n+1,z,'minecraft:dark_oak_stairs',facing='south',half='bottom',shape='straight',waterlogged=False)
            p.box(x,main+n+2,z,x,main+n+3,z,AIR)
        p.box(side*5,main+5,aft,side*5,main+5,aft+1,'minecraft:spruce_planks')
    chart_table(p,-4,main+1,aft+3)
    p.put(-4,main+1,aft+8,'handcrafted:dark_oak_couch',facing='east')
    p.put(-3,main+1,aft+8,'handcrafted:dark_oak_side_table')
    p.put(-3,main+2,aft+8,'minecraft:candle',candles=2,lit=True,waterlogged=False)
    p.put(4,main+1,aft+5,'minecraft:'+('blue' if v.offshore else 'red')+'_bed',facing='south',part='foot',occupied=False)
    p.put(4,main+1,aft+6,'minecraft:'+('blue' if v.offshore else 'red')+'_bed',facing='south',part='head',occupied=False)
    p.chest(4,main+1,aft+8,'Captain: personal effects',
            ['minecraft:spyglass','minecraft:clock','minecraft:book','minecraft:amethyst_shard'])
    p.put(0,main+4,aft+5,'minecraft:lantern',hanging=True,waterlogged=False)
    p.room('Captain\'s stern cabin','main',(-b+1,aft+1,b-1,q-2),
           'Glazed stern gallery, private berth, writing desk, model ship and personal effects',(2,aft+4))
    p.room('Open weather deck','main',(-b+1,-q+6,b-1,aft-2),
           'Hatches, anchor capstan, running rigging and clear fore-and-aft passage',(2,5))
    # Wheel is a native Create valve used as an explicit unpowered wheel display.
    p.put(0,main+6,aft+1,'minecraft:dark_oak_fence')
    wheel=p.choose('create:copper_valve_handle','create:large_cogwheel')
    p.put(0,main+7,aft+1,wheel,**({'facing':'south'} if 'facing' in p.native[wheel] else {'axis':'z'}))
    p.put(-2,main+6,aft+4,'minecraft:cartography_table')
    # Forecastle platform and accessible paired steps.
    fore=-q+9
    for z in range(-q+2,fore):
        w=hull_halfwidth(v,z,14)
        p.box(-max(0,w-1),main+3,z,max(0,w-1),main+3,z,'minecraft:spruce_planks')
        for side in (-1,1):p.put(side*w,main+4,z,'minecraft:dark_oak_fence')
    for n in range(3):
        for x in (-3,3):
            p.put(x,main+n+1,fore+2-n,'minecraft:dark_oak_stairs',facing='north',half='bottom',shape='straight',waterlogged=False)
    # Capstan, maintenance props and open cargo hatch.
    p.put(0,main+1,-q+13,'minecraft:dark_oak_log',axis='y')
    p.box(-2,main+2,-q+13,2,main+2,-q+13,'minecraft:dark_oak_fence')
    p.put(-b+3,main+1,8,'chipped:spruce_crate')
    p.put(-b+3,main+2,8,'supplementaries:sack',open=False,waterlogged=False)
    p.sign(-3,main+1,aft-2,[v.name,'Hold - Crew - Guns','Quarterdeck above','Original structural ship'])
    # Two real, continuous ladder trunks with attached supporting columns.
    for x,z in ((-3,3),(3,-4)):
        backing=x-1 if x<0 else x+1
        facing='east' if x<0 else 'west'
        p.box(backing,p.keel+3,z,backing,main+1,z,'minecraft:stripped_dark_oak_log',axis='y')
        for y in range(p.keel+3,main+2):
            p.put(x,y,z,'minecraft:ladder',facing=facing,waterlogged=False)
        for floor in p.deck_levels.values():
            p.hatches.append({'position': [p.world(x,z)[0],floor,p.world(x,z)[1]],'backing': [p.world(backing,z)[0],floor,p.world(backing,z)[1]],'facing':facing})
        # Adjacent hatch square provides unobstructed landings at every deck.
        for floor in p.deck_levels.values():
            p.put(x,floor,z+1,AIR)
            p.box(x,floor+1,z+1,x,floor+2,z+1,AIR)


def rig(p):
    v=p.vessel;b=v.beam//2;q=v.length//2
    for index,(z,height) in enumerate(v.masts):
        top=p.main+height
        p.box(0,p.keel+2,z,0,top,z,'minecraft:stripped_dark_oak_log',axis='y')
        # Small fighting top, with no enormous unsupported sky platform.
        for x in range(-2,3):
            for dz in range(-1,2):p.put(x,p.main+height//2,z+dz,'minecraft:dark_oak_slab',type='top',waterlogged=False)
        for side in (-1,1):
            w=min(b-1,hull_halfwidth(v,z,14)-1)
            for dz in (-3,0,3):
                p.rope((side*w,p.main+2,z+dz),(0,top-3,z))
        # Fore/aft stays form a continuous family rather than isolated pillars.
        anchor_z=-q+3 if index==0 else v.masts[index-1][0]
        p.rope((0,top-1,z),(0,p.main+4,anchor_z))
        if index==len(v.masts)-1:p.rope((0,top-2,z),(0,p.main+6,q-3))
        yard_specs=((height-7,b+1,11),(height-18,b+3,14))
        if height>=36:yard_specs=((height-2,b-3,6),)+yard_specs
        for j,(elevation,radius,drop) in enumerate(yard_specs):
            y=p.main+elevation
            radius=max(4,radius-(2 if index==len(v.masts)-1 else 0))
            p.box(-radius,y,z,radius,y,z,'minecraft:stripped_spruce_log',axis='x')
            if v.sail_state=='furled':
                for x in range(-radius+1,radius):
                    p.put(x,y-1,z,'minecraft:white_wool')
                    if x%4==0:p.put(x,y-2,z,'minecraft:light_gray_wool')
            else:
                shown=drop if v.sail_state=='loose-drying' else max(3,round(drop*(.57 if j%2 else .45)))
                for dy in range(1,shown+1):
                    span=radius-1-round((dy/drop)**2*2)
                    for x in range(-span,span+1):
                        # Billowed canvas is a curved surface, with a scalloped
                        # foot and slight weathering, never a flat square sign.
                        if dy==shown and (abs(x)+index)%5==0:continue
                        offset=round(-2.5*math.sin((x+span)/(max(1,span*2))*math.pi)*math.sin(dy/drop*math.pi))
                        material='minecraft:white_wool' if (x+dy+index*3)%19 else 'minecraft:light_gray_wool'
                        p.put(x,y-dy,z+offset,material)
                for side in (-1,1):p.rope((side*(radius-2),y-shown,z),(side*(b-1),p.main+2,z+4))
        # Pennants on the mastheads, colour and length differ by ship.
        for n in range(1,6 if v.offshore else 4):
            p.put(n,top,z,'minecraft:'+v.accent+'_wool')
            if n<3:p.put(n,top-1,z,'minecraft:'+v.accent+'_wool')
    # Anchors remain separate small fixtures; no native anchor/ship physics loop.
    for side in (-1,1):
        x=side*(b+4);z=-q+7
        floor=max(row['ocean_floor_y'] for row in p.near_samples(x,z))
        ay=max(floor+1,p.keel-3)
        p.rope((side*(b-2),p.main+1,z+2),(x,ay+4,z))
        p.box(x,ay,z,x,ay+4,z,'minecraft:chain',axis='y',waterlogged=True)
        p.box(x-2,ay,z,x+2,ay,z,'minecraft:iron_bars')
        p.put(x-2,ay+1,z,'minecraft:iron_bars');p.put(x+2,ay+1,z,'minecraft:iron_bars')


def flagship_davits(p):
    """A native crank/pulley with a deliberately isolated small cradle.

    Its glue and actual tender lifting are commissioned separately; never glue
    the decorative giant hull, and never claim a boat is attached from geometry.
    """
    if not p.vessel.offshore:return
    b=p.vessel.beam//2;z=10;y=p.main
    for dz in (z-3,z+3):
        p.box(b-1,y+1,dz,b-1,y+10,dz,'minecraft:stripped_dark_oak_log',axis='y')
        p.box(b-1,y+10,dz,b+6,y+10,dz,'minecraft:stripped_dark_oak_log',axis='x')
        p.rope((b-1,y+10,dz),(b+6,y+6,dz))
        p.rope((b+6,y+10,dz),(b+6,y+3,dz))
    p.box(b-1,y+10,z-3,b-1,y+10,z+3,'minecraft:dark_oak_log',axis='z')
    # Real Create crank -> X shaft -> rope pulley; initial cradle is raised.
    p.put(b+2,y+8,z,'create:hand_crank',facing='west',waterlogged=False)
    for x in (b+3,b+4):p.put(x,y+8,z,'create:shaft',axis='x',waterlogged=False)
    p.put(b+5,y+8,z,'create:rope_pulley',axis='x')
    p.box(b+3,y+6,z-2,b+7,y+6,z+2,'minecraft:dark_oak_slab',type='double',waterlogged=False)
    for dz in (z-2,z+2):
        p.box(b+3,y+7,dz,b+7,y+7,dz,'minecraft:dark_oak_fence')
    # Operator walk, ladder and dry platform have no automatic loader or motor.
    p.box(b-1,y+7,z-1,b+2,y+7,z+1,'minecraft:spruce_planks')
    p.box(b-2,y+1,z+1,b-2,y+7,z+1,'minecraft:ladder',facing='west',waterlogged=False)
    p.box(b-1,y+1,z+1,b-1,y+7,z+1,'minecraft:stripped_dark_oak_log',axis='y')
    p.sign(b-3,y+1,z-2,['Tender davits','Hand-cranked tackle','Small cradle only','Lift commissioning pending'])
    # A water-level boarding ladder permits arrival by genuine boat, independent
    # of the uncommissioned lifting mechanism.
    for dy in range(p.sea,y+2):
        p.put(-b,dy,10,'minecraft:dark_oak_planks')
        p.put(-b-1,dy,10,'minecraft:ladder',facing='west',waterlogged=dy<=p.sea)
    # Clear both the outer ladder landing and the inner hull railing. The
    # latter is one block inboard because of upper-hull tumblehome.
    p.box(-b,y+1,9,-b+1,y+2,11,AIR)
    p.entity('minecraft:boat',-b-5,p.sea+.1,11,'Resolute tender - Rose',',Type:"spruce",Rotation:[180f,0f]')
    p.entity('minecraft:boat',-b-5,p.sea+.1,17,'Resolute tender - Compass',',Type:"oak",Rotation:[180f,0f]')
    p.features.append({'name':'Tender hoist','status':'Native crank and rope pulley installed; cradle glue, working lift, boat retention and restart commissioning pending',
                       'pulley':[p.world(b+5,z)[0],y+8,p.world(b+5,z)[1]],
                       'cradle_local_bounds':[b+3,y+6,z-2,b+7,y+7,z+2]})


def docked_access(p):
    if p.vessel.offshore:return
    z=p.vessel.length//2-17
    width=hull_halfwidth(p.vessel,z,14)
    dock_y=p.sea+2
    drop=p.main-dock_y
    pier_x=width+drop+3
    shore=-1247-p.cz
    # A three-wide gangway descends outward to a five-wide finger pier.
    for dz in range(z-1,z+2):
        p.box(width,p.main+1,dz,width,p.main+2,dz,AIR)
        for n in range(1,drop+1):
            x=width+n
            p.put(x,p.main-n,dz,'minecraft:dark_oak_stairs',facing='west',half='bottom',shape='straight',waterlogged=False)
            p.box(x,p.main-n+1,dz,x,p.main-n+2,dz,AIR)
        p.box(width+drop+1,dock_y,dz,pier_x+2,dock_y,dz,'minecraft:spruce_planks')
    for pz in range(z-5,shore+1):
        p.box(pier_x-2,dock_y,pz,pier_x+2,dock_y,pz,'minecraft:spruce_planks')
        if (pz-z)%9==0:
            for px in (pier_x-2,pier_x+2):
                floor=max(row['ocean_floor_y'] for row in p.near_samples(px,pz))
                if floor<dock_y:
                    p.box(px,floor+1,pz,px,dock_y-1,pz,'minecraft:stripped_dark_oak_log',axis='y')
                p.put(px,dock_y+1,pz,'minecraft:dark_oak_fence')
                p.put(px,dock_y+2,pz,'minecraft:lantern',hanging=False,waterlogged=False)
        elif abs(pz-z)>2:
            for px in (pier_x-2,pier_x+2):p.put(px,dock_y+1,pz,'minecraft:dark_oak_fence')
    # Deck ropes and mooring bollards lie outside the actual boarding opening.
    for dz in (z-5,z+5):
        p.put(pier_x-2,dock_y+1,dz,'minecraft:dark_oak_log',axis='y')
        p.rope((width,p.main+1,dz),(pier_x-2,dock_y+1,dz))
    p.sign(pier_x,dock_y+1,z-3,[p.vessel.name,'Historic ship berth','Gangway to starboard','Hold - Crew - Guns'])
    p.connections.append({'type':'Five-wide finger pier and three-wide stair gangway',
                           'shore_end':[p.world(pier_x,shore)[0],dock_y+1,-1247],
                           'ship_end':[p.world(width,z)[0],p.main+1,p.world(width,z)[1]],
                           'shared_quay_required':True})


def build_vessel(registry,survey,vessel,backup,fixed):
    p=ShipPlan(registry,survey,vessel,backup,fixed)
    p.require_depth()
    hull(p);interiors(p);upperworks(p)
    p.clear_routes()
    rig(p);flagship_davits(p);docked_access(p);p.finish_ropes()
    p.landmark(vessel.name,2,p.main+1,5,'Historic ships',
               [vessel.role, vessel.sail_state+' canvas', 'Four explorable deck levels',
                'Captain cabin, chart room, hammocks, mess, galley, cannon deck, stores and safe magazine'])
    circulation=p.verify_circulation()
    # Any planned underwater air cell next to an unplanned voxel is an opening
    # to the ocean. This catches bilge steps and accidental submerged doorways.
    for (x,y,z),state in p.blocks.items():
        if state!=AIR or y>p.sea:continue
        for dx,dy,dz in ((1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1)):
            neighbor=x+dx,y+dy,z+dz
            if neighbor not in p.blocks:
                raise UserError('Unsealed underwater ship interior: '+str((x,y,z)))
    return p,circulation


class QuayPlan(ShipPlan):
    """A small complementary harbor plan, with completed construction preserved."""
    def __init__(self,registry,survey,backup,fixed):
        super().__init__(registry,survey,Vessel('harbor-access','Grand Harbor access',
                          'Shared quay, small craft and tenders',(1120,-1370),21,7,2,
                          'brown','furled',(),10,0),backup,fixed)
        self.yielded=[]

    def connection_put(self,x,y,z,key,**properties):
        wx,wz=self.world(x,z);position=wx,y,wz
        if position in self.fixed:
            self.yielded.append({'position':list(position),'preserved':self.fixed[position]})
            return
        self.put(x,y,z,key,**properties)

    def world_put(self,x,y,z,key,**properties):
        return self.connection_put(x-self.cx,y,z-self.cz,key,**properties)

    def finish_ropes(self):
        # A mooring may end at a completed cleat/rail without replacing it.
        neighbors={'west':(-1,0,0),'east':(1,0,0),'down':(0,-1,0),
                   'up':(0,1,0),'north':(0,0,-1),'south':(0,0,1)}
        for x,y,z in sorted(self.ropes):
            wx,wz=self.world(x,z);position=wx,y,wz
            if self.blocks.get(position,self.fixed.get(position,AIR))!=AIR:continue
            properties={key:(x+d[0],y+d[1],z+d[2]) in self.ropes for key,d in neighbors.items()}
            self.put(x,y,z,'supplementaries:rope',knot=False,waterlogged=False,**properties)


def small_cutter(p,name,cx,cz,length=21,beam=7,accent='brown'):
    """A little original fishing cutter with a usable cockpit, cabin and hold."""
    q=length//2;keel=61;deck=65
    def section(z,y):
        if not -q<=z<=q or not keel<=y<=deck:return -1
        t=(z+q)/max(1,2*q)
        w=max(0,round((beam//2)*min(1,t/.22,(1.12-t)/.3)))
        return max(0,w-(2 if y==keel else 1 if y==keel+1 else 0))
    for z in range(-q,q+1):
        w=section(z,deck)
        for y in range(keel,deck+1):
            wy=section(z,y)
            # Soundings must support the little hull as well as its large peers.
            for x in range(-wy,wy+1):
                floor=max(row['ocean_floor_y'] for row in p.near_samples(cx+x-p.cx,cz+z-p.cz))
                if y<=p.sea and floor>=y:raise UserError('Small craft would cut the seabed: '+name)
                edge=(abs(x)==wy or y in (keel,deck) or z in (-q,q) or
                      abs(x)>section(z,y-1) or abs(x)>section(z-1,y) or abs(x)>section(z+1,y))
                key='minecraft:dark_oak_planks' if edge else AIR
                p.put(cx+x-p.cx,y,cz+z-p.cz,key)
        for side in (-1,1):
            if w:p.put(cx+side*w-p.cx,deck+1,cz+z-p.cz,'minecraft:dark_oak_fence')
    # Low deckhouse on the stern, with light through stern and side windows.
    for x in range(-2,3):
        for z in range(q-6,q):
            p.put(cx+x-p.cx,deck+4,cz+z-p.cz,'minecraft:dark_oak_slab',type='top',waterlogged=False)
            if abs(x)==2 or z==q-1:
                p.put(cx+x-p.cx,deck+1,cz+z-p.cz,'minecraft:'+accent+'_terracotta')
                for y in (deck+2,deck+3):p.put(cx+x-p.cx,y,cz+z-p.cz,'minecraft:glass_pane')
    p.box(cx-p.cx,deck+1,cz+q-6-p.cz,cx-p.cx,deck+2,cz+q-6-p.cz,AIR)
    p.put(cx-1-p.cx,deck+1,cz+q-3-p.cz,'minecraft:cartography_table')
    p.put(cx+1-p.cx,deck+1,cz+q-3-p.cz,'minecraft:barrel',facing='up',open=False)
    # Small working cockpit and fishing/provisions lockers.
    p.put(cx-2-p.cx,deck+1,cz-p.cz,'minecraft:barrel',facing='up',open=False)
    p.put(cx-2-p.cx,deck+1,cz-3-p.cz,'aquaculture:tackle_box',facing='east')
    p.put(cx+2-p.cx,deck+1,cz-p.cz,'minecraft:composter',level=0)
    p.put(cx+2-p.cx,deck+1,cz-3-p.cz,'minecraft:lantern',hanging=False,waterlogged=False)
    p.box(cx-p.cx,deck+1,cz-4-p.cz,cx-p.cx,deck+17,cz-4-p.cz,'minecraft:stripped_spruce_log',axis='y')
    p.box(cx-5-p.cx,deck+13,cz-4-p.cz,cx+5-p.cx,deck+13,cz-4-p.cz,'minecraft:dark_oak_log',axis='x')
    for x in range(-4,5):p.put(cx+x-p.cx,deck+12,cz-4-p.cz,'minecraft:white_wool')
    p.rope((cx-3-p.cx,deck+1,cz-4-p.cz),(cx-p.cx,deck+16,cz-4-p.cz))
    p.rope((cx+3-p.cx,deck+1,cz-4-p.cz),(cx-p.cx,deck+16,cz-4-p.cz))
    p.sign(cx+1-p.cx,deck+1,cz+2-p.cz,[name,'Fishing and stores','Original small cutter','Structural hull'])
    p.landmark(name,cx-p.cx,deck+1,cz+2-p.cz,'Harbor craft',
               ['Furnished fishing cutter','Wheelhouse and tackle','Furled working sail'])


def shared_harbor_access(registry,survey,backup,fixed):
    p=QuayPlan(registry,survey,backup,fixed);floor=65
    # A generous waterfront promenade: sparse piles, no sea filled with stone.
    for x in range(987,1260):
        for z in range(-1249,-1241):p.world_put(x,floor,z,'minecraft:spruce_planks')
        if x%9==0:
            for z in (-1249,-1242):
                ground=max(row['ocean_floor_y'] for row in p.near_samples(x-p.cx,z-p.cz))
                for y in range(ground+1,floor):p.world_put(x,y,z,'minecraft:stripped_dark_oak_log',axis='y')
                p.world_put(x,floor+1,z,'minecraft:dark_oak_log',axis='y')
                p.world_put(x,floor+2,z,'minecraft:lantern',hanging=False,waterlogged=False)
    # Preserve all original pier clearance. This crossing has a single step
    # down to the existing Y64 pier instead of erasing its floor or signs.
    for x in (1116,1124):
        for z in range(-1248,-1242):
            if (x,65,z) not in fixed and (x,64,z) not in fixed:
                p.world_put(x,65,z,AIR)
                p.world_put(x,64,z,'minecraft:dark_oak_stairs',facing='west' if x==1116 else 'east',half='bottom',shape='straight',waterlogged=False)
    for x in (1030,1060,1170,1220):
        for dx in (-1,0,1):
            for z in (-1249,-1250,-1251):p.world_put(x+dx,floor,z,'minecraft:spruce_planks')
        p.world_put(x,floor+1,-1250,'minecraft:barrel',facing='up',open=False)
        p.world_put(x+1,floor+1,-1250,'chipped:spruce_crate')
        p.world_put(x,floor+2,-1250,'supplementaries:sack',open=False,waterlogged=False)
    # The explicit ocean-edge link meets an already built boardwalk at
    # 1150,65,-1241. Existing block/air states are yielded, never overwritten.
    for x in range(1148,1153):
        for z in range(-1245,-1241):p.world_put(x,floor,z,'minecraft:spruce_planks')
    p.connections.append({'type':'Existing ocean-edge boardwalk connection',
                           'new_end':[1150,66,-1242],'existing_end':[1150,66,-1241],
                           'existing_floor':'minecraft:spruce_planks at Y65',
                           'native_walk_check_pending':True})
    # Genuine vanilla boats are interactive tender craft. They have stable UUIDs
    # via Plan.entity; no permanent mobs, combat or simulated giant-ship physics.
    for x,z,name,kind in [(1094,-1258,'Harbor tender - Rosewater','spruce'),
                           (1101,-1258,'Harbor tender - Horizon','oak'),
                           (1158,-1260,'Harbor tender - Lavender','spruce')]:
        p.entity('minecraft:boat',x-p.cx,p.sea+.1,z-p.cz,name,
                 ',Type:"'+kind+'",Rotation:[180f,0f]')
    # A usable smaller river craft in the real open channel, using the actual
    # marine survey rather than guessing a collision-free spot on land.
    river=(1128,-1206)
    nearest=min(survey['samples'],key=lambda row:(row['x']-river[0])**2+(row['z']-river[1])**2)
    if nearest.get('fluid') and nearest['block'].startswith('minecraft:water'):
        for dy in (63,64,65):
            if (river[0],dy,river[1]) in fixed and fixed[river[0],dy,river[1]]!=AIR:
                raise UserError('Reserved river-craft mooring intersects completed construction')
        p.entity('minecraft:chest_boat',river[0]-p.cx,p.sea+.1,river[1]-p.cz,
                 'River service boat - The Little Promise',',Type:"spruce",Rotation:[0f,0f]')
    else:raise UserError('Native river-craft sounding is not open water')
    small_cutter(p,'The Copper Minnow',1055,-1333,21,7,'brown')
    small_cutter(p,'The Silver Kestrel',1185,-1300,25,9,'cyan')
    # The flagship's shipboard anchors are shown stowed. Two mooring buoys have
    # their own complete ground chains and seabed anchors, so its offshore berth
    # visibly has a real mooring arrangement rather than an anchor mid-water.
    for z in (-1475,-1425):
        x=1170
        bottom=max(row['ocean_floor_y'] for dx in (-2,0,2)
                   for row in p.near_samples(x+dx-p.cx,z-p.cz))+1
        for y in range(bottom+1,p.sea+1):
            p.world_put(x,y,z,'minecraft:chain',axis='y',waterlogged=True)
        for dx in range(-2,3):p.world_put(x+dx,bottom,z,'minecraft:iron_bars')
        for dx in (-2,2):p.world_put(x+dx,bottom+1,z,'minecraft:iron_bars')
        p.world_put(x,p.sea+1,z,'minecraft:barrel',facing='up',open=False)
        for dx,dz in ((-1,0),(1,0),(0,-1),(0,1)):
            p.world_put(x+dx,p.sea,z+dz,'minecraft:white_wool')
        p.world_put(x,p.sea+2,z,'minecraft:lantern',hanging=False,waterlogged=False)
        # Endpoints include the preserved ship railing for a visible attachment.
        p.rope((1150-p.cx,70,z-p.cz),(x-p.cx,p.sea+1,z-p.cz))
    p.features.append({'name':'Resolute offshore mooring',
                       'description':'Two marked buoys, visible ship lines, continuous chains and seabed anchors',
                       'buoys':[[1170,64,-1475],[1170,64,-1425]],
                       'status':'Structural mooring; no giant-ship physics simulation'})
    p.finish_ropes()
    p.landmark('Grand Harbor Quays',1150-p.cx,66,-1245-p.cz,'Pirate port',
               ['Three deep-water finger piers','Tender landing','Two smaller fishing ships',
                'Four native tender/service boats including the river craft'])
    return p


def prepare_boarding_fix(home):
    """Six-cell access correction; never mutate an already issued ship master."""
    import hashlib
    layout=Layout(home);directory=layout.state/'settlement'
    Storage(layout).reserve(1024**2)
    registry=read_json(directory/'registry.json')
    survey=read_json(directory/'marine-survey-0.6.5.json')
    backup=read_json(directory/'backup-receipt.json',{})
    if not backup.get('verified'):raise UserError('Verified complete world backup required')
    manifests=sorted(directory.glob('ship-rosewater-resolute-*-manifest.json'),key=lambda q:q.stat().st_mtime,reverse=True)
    if not manifests:raise UserError('Prepare the original flagship first')
    manifest=read_json(manifests[0]);source=Path(manifest['path'])
    if source.resolve().parent!=directory.resolve() or digest(source)!=manifest['sha256']:
        raise UserError('Original flagship provenance failed')
    master=read_json(source)
    if master['world_path']!=registry['world_path'] or master['seed']!=registry['seed']:
        raise UserError('Original flagship belongs to a different world')
    fixed={(x,y,z):master['palette'][i] for x,y,z,i in master['blocks']}
    previous=[]
    for z in (-1441,-1440,-1439):
        if fixed.get((1130,70,z))!='minecraft:dark_oak_fence':
            raise UserError('The boarding delta is only authorized for the original three railings')
        if (1130,71,z) in fixed and fixed[1130,71,z]!=AIR:
            raise UserError('The boarding delta would erase another original furnishing')
        for y in (70,71):
            previous.append({'position':[1130,y,z],'previous':fixed.pop((1130,y,z),None)})
    p=ShipPlan(registry,survey,VESSELS[0],backup['sha256'],fixed)
    for row in previous:
        x,y,z=row['position'];p.put(x-p.cx,y,z-p.cz,AIR)
    identity=hashlib.sha256(json.dumps({'base':manifest['sha256'],'previous':previous,
                                      'backup':backup['sha256']},sort_keys=True).encode()).hexdigest()
    target=directory/f'grand-harbor-resolute-boarding-{identity}.json'
    if target.exists():result={'path':str(target),'sha256':digest(target),'blocks':6,'palette':1,'block_entities':0,'landmarks':0}
    else:result=p.save(target)
    result.update({'at':utcnow(),'original_flagship_sha256':manifest['sha256'],'expected_previous':previous,
                   'reason':'Open the inner rail between the water-level ladder landing and main deck',
                   'status':'Six-cell delta prepared; native placement and composite verification pending'})
    receipt=directory/f'grand-harbor-resolute-boarding-{identity}-manifest.json'
    if not receipt.exists():write_json(receipt,result)
    return result


def prepare_access(home):
    """Prepare only the common quay after the four immutable vessel files exist."""
    import hashlib
    layout=Layout(home);directory=layout.state/'settlement'
    Storage(layout).reserve(32*1024**2)
    registry=read_json(directory/'registry.json')
    survey_path=directory/'marine-survey-0.6.5.json'
    survey=read_json(survey_path)
    backup=read_json(directory/'backup-receipt.json',{})
    if not backup.get('verified'):raise UserError('Verified complete world backup required')
    fixed={};exclusions=[]
    for name in FIXED_MASTERS:
        source=directory/name;document=read_json(source)
        if document['world_path']!=registry['world_path'] or document['seed']!=registry['seed']:
            raise UserError('Harbor exclusion belongs to a different world')
        fixed.update({(x,y,z):document['palette'][i] for x,y,z,i in document['blocks']})
        exclusions.append({'file':source.name,'sha256':digest(source)})
    for vessel in VESSELS:
        manifests=sorted(directory.glob('ship-'+vessel.slug+'-*-manifest.json'),key=lambda path:path.stat().st_mtime,reverse=True)
        if not manifests:raise UserError('Prepare all four vessels before the common harbor quay')
        receipt=read_json(manifests[0]);source=Path(receipt['path'])
        if source.resolve().parent!=directory.resolve() or digest(source)!=receipt['sha256']:
            raise UserError('Vessel exclusion provenance failed for '+vessel.name)
        document=read_json(source)
        if document['world_path']!=registry['world_path'] or document['seed']!=registry['seed']:
            raise UserError('Vessel exclusion belongs to a different world')
        fixed.update({(x,y,z):document['palette'][i] for x,y,z,i in document['blocks']})
        exclusions.append({'file':source.name,'sha256':digest(source)})
    p=shared_harbor_access(registry,survey,backup['sha256'],fixed)
    for source in directory.glob('*survey*.json'):
        for row in read_json(source,{}).get('samples',[]):
            p.protected.update(tuple(pos) for pos in row.get('block_entities',[]))
    for source in directory.glob('terrain-before-core-*.json'):
        for row in read_json(source,{}).get('samples',[]):
            p.protected.update(tuple(pos) for pos in row.get('block_entities',[]))
    geometry=json.dumps({'blocks':sorted((list(pos),state) for pos,state in p.blocks.items()),
                         'tags':sorted((list(pos),tag) for pos,tag in p.tags.items()),
                         'commands':p.commands,'backup':backup['sha256']},separators=(',',':')).encode()
    identity=hashlib.sha256(geometry).hexdigest()
    target=directory/f'grand-harbor-access-{identity}.json'
    if target.exists():
        document=read_json(target)
        result={'path':str(target),'sha256':digest(target),'blocks':len(p.blocks),'palette':len(document['palette']),
                'block_entities':len(p.tags),'landmarks':len(p.landmarks)}
    else:result=p.save(target)
    result.update({'at':utcnow(),'geometry_sha256':identity,'exclusions':exclusions,
                   'survey_sha256':digest(survey_path),'connections':p.connections,'mooring_features':p.features,
                   'preserved_existing_quay_positions':p.yielded,'commands':len(p.commands),
                   'features':['Two original furnished smaller fishing ships',
                               'Three usable dock tenders and one usable river service boat',
                               'Common waterfront promenade and links to all three finger piers'],
                   'status':'Prepared only; native placement, actual water/collision checks and visual acceptance pending'})
    manifest=directory/f'grand-harbor-access-{identity}-manifest.json'
    if not manifest.exists():write_json(manifest,result)
    return result


def prepare(home):
    layout=Layout(home);directory=layout.state/'settlement'
    Storage(layout).reserve(96*1024**2)
    backup=read_json(directory/'backup-receipt.json',{})
    if not backup.get('verified'):raise UserError('Verified complete world backup required')
    survey_path=directory/'marine-survey-0.6.5.json'
    survey=read_json(survey_path,{})
    if not survey.get('samples'):raise UserError('Parent must provide marine-survey-0.6.5.json first')
    registry=read_json(directory/'registry.json')
    if survey.get('seed',registry['seed'])!=registry['seed']:
        raise UserError('Marine survey belongs to a different world')
    fixed={};proofs=[]
    for name in FIXED_MASTERS:
        master=read_json(directory/name)
        if master['seed']!=registry['seed'] or master['world_path']!=registry['world_path']:
            raise UserError('Construction exclusion belongs to another world')
        fixed.update({(x,y,z):master['palette'][i] for x,y,z,i in master['blocks']})
        proofs.append({'file':name,'sha256':digest(directory/name)})
    protected=set()
    for source in directory.glob('*survey*.json'):
        for row in read_json(source,{}).get('samples',[]):
            protected.update(tuple(pos) for pos in row.get('block_entities',[]))
    for source in directory.glob('terrain-before-core-*.json'):
        for row in read_json(source,{}).get('samples',[]):
            protected.update(tuple(pos) for pos in row.get('block_entities',[]))
    prepared=[]
    # Build all in memory before any output. A shallow last ship cannot leave a
    # misleading partial harbor manifest or silently change a previous plan.
    for vessel in VESSELS:
        plan,circulation=build_vessel(registry,survey,vessel,backup['sha256'],fixed)
        plan.protected.update(protected)
        collisions=plan.protected & plan.blocks.keys()
        if collisions:raise UserError('A vessel would cover an existing inventory: '+str(sorted(collisions)[:8]))
        fixed.update(plan.blocks)
        prepared.append((plan,circulation))
    results=[]
    for plan,circulation in prepared:
        # Content digest in filename gives immutable custody; avoid timestamps in
        # the identity by hashing the deterministic geometry and supplied tags.
        import hashlib
        geometry=json.dumps({'blocks':sorted((list(pos),state) for pos,state in plan.blocks.items()),
                             'tags':sorted((list(pos),tag) for pos,tag in plan.tags.items()),
                             'backup':backup['sha256']},separators=(',',':')).encode()
        identity=hashlib.sha256(geometry).hexdigest()
        target=directory/f'ship-{plan.vessel.slug}-{identity}.json'
        if target.exists():
            previous=read_json(target)
            if len(previous.get('blocks',[]))!=len(plan.blocks):raise UserError('Immutable ship plan identity collision')
            result={'path':str(target),'sha256':digest(target),'blocks':len(plan.blocks),'palette':len(previous['palette']),
                    'block_entities':len(plan.tags),'landmarks':len(plan.landmarks)}
        else:result=plan.save(target)
        result.update({'at':utcnow(),'ship':dataclasses.asdict(plan.vessel),'geometry_sha256':identity,
                       'deck_levels':plan.deck_levels,'sea_y':plan.sea,'keel_y':plan.keel,
                       'rooms':plan.rooms,'ladders_and_hatches':plan.hatches,'guns':plan.guns,
                       'features':plan.features,'connections':plan.connections,'depth_checks':plan.depth_checks,
                       'survey_sha256':digest(survey_path),'exclusions':proofs,
                       'circulation':circulation,'status':'Prepared only; no world placement or visual/functional acceptance',
                       'acceptance_pending':['Native placement and verification','Dry hull and ladder/support collision checks',
                          'Dock/gangplank connection','Tender and isolated hoist commissioning','Restart persistence',
                          'Real intended-shader exterior/interior screenshots and refinement']})
        manifest=directory/f'ship-{plan.vessel.slug}-{identity}-manifest.json'
        if not manifest.exists():write_json(manifest,result)
        results.append(result)
    return {'at':utcnow(),'vessels':results,'status':'Original vessel plans prepared; no placement performed'}


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--home',type=Path,default=Path(r'D:\A World for Two'))
    parser.add_argument('--access',action='store_true',help='Prepare the separate shared quay after the vessel files exist')
    args=parser.parse_args()
    result=prepare_access(args.home) if args.access else prepare(args.home)
    if args.access:print(json.dumps({k:result[k] for k in ('path','sha256','blocks','block_entities','commands','status')}))
    else:print(json.dumps({'status':result['status'],'vessels':[{k:r[k] for k in ('path','sha256','blocks','block_entities')} for r in result['vessels']]}))
