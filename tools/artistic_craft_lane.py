"""One authored, furnished south-bank craft lane joining the cottage court.

Six different small buildings, workyards and a bent lane are drawn explicitly.
Only low-level state, floor, wall and hollow-roof primitives are shared with the
new prototypes; no rejected town builder or complete house template is used.
The exact existing bridge/cottage plans are exclusion masks, including air.
"""
from __future__ import annotations

import argparse
from collections import deque
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
import subprocess

from control_room.common import UserError, digest, utcnow
from tools.artistic_street import StreetPlan, rectangle, layer, edge, GUARD, MAX_BUNDLE, MIB
from tools.artistic_cottages import framed_room, roof, window, door, stair
from tools.artistic_street_life import Life, DISPLAY_ARTIFACTS, bed_pairs
from tools.artistic_materials import require_material_rule, require_outdoor_rule


ORIGIN = (1136, 67, -1118)
STREET = ((0, 22), (10, 22), (18, 18), (26, 18), (34, 27), (42, 28), (48, 25), (52, 24))
CONNECTOR = ((-6, 24), (-5, 23), (-4, 22), (-3, 22), (-2, 22), (-1, 22))
NATURAL = {'minecraft:grass_block', 'minecraft:sand', 'minecraft:coarse_dirt', 'minecraft:rooted_dirt',
           'minecraft:dirt', 'vinery:dark_cherry_log'}


@dataclass
class Lot:
    ident: str
    name: str
    floor: int
    levels: list[set]
    plaster: tuple
    timber: str
    entry: tuple
    front: str
    flight: tuple | None
    programs: tuple


def lots():
    return [
        Lot('cobbler', 'Bramble & Buckle', 0,
            [layer((2, 9, 9, 19), remove=((2, 19), (2, 18))), layer((2, 8, 9, 19), (4, 20, 7, 20))],
            ('dawnoftimebuilder:plastered_stone', 'minecraft:white_terracotta'), 'minecraft:stripped_dark_oak_log',
            (7, 19), 'south', (8, 16), ('Leather repair bench, fitted boot display and fitting seat', 'Cobbler household and little reading bay')),
        Lot('luthier', 'Wren & Reed', -1,
            [layer((12, 5, 19, 14), (18, 6, 23, 10)), layer((12, 5, 19, 15), (18, 6, 23, 10)), rectangle(13, 5, 19, 14)],
            ('minecraft:stone_bricks', 'dawnoftimebuilder:green_plastered_stone', 'minecraft:calcite'), 'minecraft:stripped_oak_log',
            (16, 14), 'south', (18, 12), ('Real instruments, repair bench and string-making corner', 'Music practice and shared supper', 'Luthier sleeping loft')),
        Lot('potter', 'Clay & Candle', -2,
            [layer((25, 7, 32, 16), remove=((32, 16),)), layer((25, 7, 32, 16), (26, 17, 29, 17))],
            ('dawnoftimebuilder:plastered_stone', 'dawnoftimebuilder:blue_plastered_stone'), 'minecraft:stripped_birch_log',
            (28, 16), 'south', (30, 14), ('Potting worktops, clay stock, kiln and pottery shelves', 'Potter bedroom above the market')),
        Lot('glazier', 'Copper & Glass', -1,
            [layer((35, 17, 41, 25), (34, 19, 34, 22)), rectangle(35, 18, 41, 25)],
            ('minecraft:bricks', 'dawnoftimebuilder:green_plastered_stone'), 'minecraft:stripped_spruce_log',
            (38, 25), 'south', (40, 23), ('Glass fitting bench, real furnace and repair supplies', 'Small glazier home and window seat')),
        Lot('grocer', 'The Clover Pantry', 0,
            [layer((3, 26, 10, 33), remove=((3, 26),)), layer((3, 25, 10, 34), (2, 28, 2, 31))],
            ('dawnoftimebuilder:plastered_stone', 'minecraft:yellow_terracotta'), 'minecraft:stripped_oak_log',
            (7, 26), 'north', (9, 32), ('Open produce loggia, filled provision shelves and working kitchen', 'Grocer family supper and sleeping corner')),
        Lot('stoneleaf', 'The Stoneleaf Workshop', -1,
            [layer((18, 25, 26, 34), (25, 29, 28, 33), remove=((18, 25),))],
            ('minecraft:stone_bricks',), 'minecraft:stripped_spruce_log',
            (22, 25), 'north', None, ('Real stonecutter and Chipped mason table, carving benches and tools',)),
    ]


class CraftPlan(StreetPlan):
    def __init__(self, registry, survey, exclusions, origin=ORIGIN):
        super().__init__(registry, origin)
        self.mask, self.mask_provenance = {}, []
        self.existing_block_entities = set()
        self.connector_overrides = set()
        self.path_cells = set()
        self.path_heights = {}
        self.terrain = {}
        self.wet_samples = [row for row in survey['samples'] if row['fluid']]
        self.survey = [row for row in survey['samples'] if not row['fluid'] and row['block'] in NATURAL]
        if len(self.survey) < 30:
            raise UserError('Craft lane requires its actual dry native terrain profile')
        for name, plan, sha in exclusions:
            if plan['world_path'] != registry['world_path'] or plan['seed'] != registry['seed']:
                raise UserError('Existing exclusion belongs to another actual staging world')
            self.mask_provenance.append({'name': name, 'sha256': sha, 'entries': len(plan['blocks'])})
            for x, y, z, index in plan['blocks']:
                self.mask.setdefault((x, y, z), []).append((name, plan['palette'][index]))
            self.existing_block_entities.update(tuple(row['pos']) for row in plan.get('block_entities', []))
        self.connector_columns = {(x, z+n) for x, z in CONNECTOR for n in (0, 1)}

    def ground(self, x, z):
        if (x, z) not in self.terrain:
            wx, wz = self.origin[0]+x, self.origin[2]+z
            if any((row['x']-wx)**2+(row['z']-wz)**2 <= 8 for row in self.wet_samples):
                raise UserError('Craft footprint approaches a confirmed native water sample')
            nearest = sorted(self.survey, key=lambda r: (r['x']-wx)**2+(r['z']-wz)**2)[:4]
            if len(nearest) != 4 or any(abs(r['x']-wx) > 12 or abs(r['z']-wz) > 12 for r in nearest):
                raise UserError('Craft geometry escaped its sampled natural land envelope')
            weights = [1/max(.25, (r['x']-wx)**2+(r['z']-wz)**2) for r in nearest]
            y = round(sum(r.get('ground_y', r['y'])*w for r, w in zip(nearest, weights))/sum(weights))-self.origin[1]
            if not -4 <= y <= 0:
                raise UserError('Unexpected craft-lane ground slope; no automatic flattening')
            self.terrain[x, z] = y
        return self.terrain[x, z]

    def put(self, x, y, z, key, *, priority=50, **props):
        if not (-8 <= x <= 53 and 0 <= z <= 37 and -5 <= y <= 23):
            raise UserError('Craft lane escaped its finite authored envelope')
        pos = x, y, z
        if priority < self.priority.get(pos, -1):
            return
        world = tuple(pos[i]+self.origin[i] for i in range(3))
        if world in self.existing_block_entities:
            raise UserError('Craft geometry overlaps a protected existing native block entity')
        for name, existing in self.mask.get(world, []):
            allowed = name == 'cottage' and existing == 'minecraft:air' and (x, z) in self.connector_columns and -3 <= y <= 3
            if not allowed:
                raise UserError('Craft geometry collides with exact existing '+name+' at '+str(world))
            self.connector_overrides.add(world)
        self.blocks[pos] = self.state(key, **props)
        self.priority[pos], self.owners[pos] = priority, self.zone
        self.tags.pop(pos, None)
        if key != 'minecraft:air':
            self.uses.setdefault(key.split(':')[0], set()).add(self.zone)
        if len(self.blocks) > 70_000:
            raise UserError('Craft plan exceeded its finite placement budget')

    def clear_footprint(self, cells, bottom, top):
        for x, z in cells:
            self.ground(x, z)
            for y in range(bottom+1, top+1):
                self.put(x, y, z, 'minecraft:air', priority=0)

    def serialize(self, backup):
        native = super().serialize(backup)
        ox, oy, oz = self.origin
        native.update(name='Bramble Lane — authored south-bank craft district', bounds=[ox-8, oz, ox+53, oz+37])
        return native


def house(p, lot):
    p.zone = lot.name
    cells = set.union(*lot.levels)
    minx, maxx = min(x for x, z in cells), max(x for x, z in cells)
    minz, maxz = min(z for x, z in cells), max(z for x, z in cells)
    p.clear_footprint(rectangle(minx-1, minz-1, maxx+1, maxz+1), lot.floor, lot.floor+len(lot.levels)*4+6)
    for x, z in lot.levels[0]:
        for y in range(-4, lot.floor):
            key = 'minecraft:chiseled_stone_bricks' if (x-minx) % 8 == 0 and (z-minz) % 8 == 0 else 'minecraft:polished_andesite' if (z-minz) % 8 == 0 else 'minecraft:cobbled_deepslate' if (x-minx) % 4 == 0 else 'minecraft:stone_bricks'
            if y == -1:
                key = {'minecraft:polished_andesite':'minecraft:smooth_stone', 'minecraft:cobbled_deepslate':'minecraft:polished_deepslate', 'minecraft:stone_bricks':'minecraft:mossy_stone_bricks'}.get(key,key)
            p.put(x, y, z, key, priority=20)
    for level, outline in enumerate(lot.levels):
        f = lot.floor+level*4
        framed_room(p, outline, f, lot.plaster[level], lot.timber)
        p.rooms.append({'building': lot.ident, 'level': level, 'local_floor_y': f,
                        'program': lot.programs[level], 'outline': [list(v) for v in sorted(outline)]})
        if lot.flight and level < len(lot.levels)-1:
            stair(p, lot.flight[0], lot.flight[1], f, lot.ident+'-'+str(level))
    p.floor(lot.levels[-1], lot.floor+len(lot.levels)*4)
    door(p, lot.entry[0], lot.floor, lot.entry[1], 'north' if lot.front == 'south' else 'south', 'dark_oak')
    # Each facade is drawn separately below; these are not repeated window rows.
    p.lots.append({'id': lot.ident, 'name': lot.name, 'door': [lot.entry[0], lot.floor, lot.entry[1]], 'rooms': list(lot.programs)})


def architecture(p):
    by = {lot.ident: lot for lot in lots()}
    for lot in by.values():
        house(p, lot)
    a = by['cobbler'];p.zone = a.name
    for f, z, x in ((0, 19, 3), (4, 20, 4)):
        window(p, x, f, z, 'south', 'dark_oak')
    window(p, 2, 0, 11, 'west', 'oak');window(p, 2, 4, 11, 'west', 'oak')
    roof(p, (1, 7, 10, 15), 'z', (0,1,2,3,4,4,3,2,1,0), 8, 'mcwroofs:dark_oak_roof', 'minecraft:white_terracotta', a.timber)
    roof(p, (2, 14, 10, 21), 'x', (0,1,2,3,3,2,1,0), 7, 'mcwroofs:brown_terracotta_roof', 'minecraft:white_terracotta', a.timber)
    for x in (4, 7):
        p.put(x, 3, 20, 'minecraft:dark_oak_stairs', priority=70, facing='north', half='top', shape='straight', waterlogged=False)
    a=by['luthier'];p.zone=a.name
    for f, z, x in ((-1,14,13),(3,15,13),(7,14,14)):
        window(p,x,f,z,'south','oak')
    window(p,19,-1,7,'east','oak');window(p,12,3,8,'west','oak')
    roof(p,(12,4,20,12),'z',(0,1,2,3,4,3,2,1,0),11,'mcwroofs:green_terracotta_roof','minecraft:calcite',a.timber)
    roof(p,(12,10,20,16),'x',(0,1,2,3,2,1,0),10,'mcwroofs:white_terracotta_roof','minecraft:calcite',a.timber)
    roof(p,(18,5,24,11),'x',(0,1,2,3,2,1,0),7,'mcwroofs:dark_oak_roof','dawnoftimebuilder:green_plastered_stone',a.timber)
    a=by['potter'];p.zone=a.name
    window(p,26,-2,16,'south');window(p,26,2,17,'south');window(p,25,-2,10,'west','oak')
    roof(p,(24,6,33,14),'z',(0,1,2,3,3,3,3,2,1,0),6,'mcwroofs:bricks_roof','dawnoftimebuilder:blue_plastered_stone',a.timber)
    roof(p,(25,12,33,18),'x',(0,1,2,3,2,1,0),5,'mcwroofs:white_terracotta_roof','dawnoftimebuilder:blue_plastered_stone',a.timber)
    a=by['glazier'];p.zone=a.name
    window(p,35,-1,25,'south','dark_oak');window(p,36,3,25,'south','oak');window(p,41,-1,19,'east','oak')
    roof(p,(34,17,42,25),'z',(0,1,2,3,4,3,2,1,0),7,'mcwroofs:stone_bricks_roof','dawnoftimebuilder:green_plastered_stone',a.timber)
    roof(p,(35,22,42,26),'x',(0,1,2,1,0),6,'mcwroofs:brown_terracotta_roof','dawnoftimebuilder:green_plastered_stone',a.timber)
    a=by['grocer'];p.zone=a.name
    window(p,4,0,26,'north','oak');window(p,4,4,25,'north','oak');window(p,10,4,29,'east')
    roof(p,(2,24,11,32),'z',(0,1,2,3,4,4,3,2,1,0),8,'mcwroofs:dark_oak_roof','minecraft:yellow_terracotta',a.timber)
    roof(p,(3,30,11,35),'x',(0,1,2,2,1,0),7,'mcwroofs:green_terracotta_roof','minecraft:yellow_terracotta',a.timber)
    # An actual open produce bay beside the door has slender timber jambs.
    for x in (4,5):
        for y in (1,2):
            p.put(x,y,26,'minecraft:air',priority=90)
    a=by['stoneleaf'];p.zone=a.name
    window(p,19,-1,25,'north','dark_oak');window(p,26,-1,27,'east','oak')
    roof(p,(17,24,26,32),'z',(0,1,2,3,3,3,3,2,1,0),3,'mcwroofs:spruce_roof','minecraft:stone_bricks',a.timber)
    roof(p,(18,30,26,35),'x',(0,1,2,2,1,0),2,'mcwroofs:brown_terracotta_roof','minecraft:stone_bricks',a.timber)
    roof(p,(25,28,29,34),'z',(0,1,2,1,0),3,'mcwroofs:white_terracotta_roof','minecraft:stone_bricks',a.timber)


def road_floor(x):
    return 0 if x <= 11 else -1


def pave(p, label, points, *, floor=None, width=2):
    p.zone = 'Bramble Lane, market courts and authored garden edges'
    cells = set()
    house_cells = set.union(*(lot.levels[0] for lot in lots()))
    for (ax, az), (bx, bz) in zip(points, points[1:]):
        count = max(abs(bx-ax), abs(bz-az))
        across = (0,1) if abs(bx-ax) >= abs(bz-az) else (1,0)
        for i in range(count+1):
            x,z = round(ax+(bx-ax)*i/max(1,count)),round(az+(bz-az)*i/max(1,count))
            for n in range(width):
                xx,zz=x+across[0]*n,z+across[1]*n
                f=road_floor(xx) if floor is None else floor
                if (xx,zz) in house_cells:
                    continue
                ground=p.ground(xx,zz)
                for y in range(min(ground-1,f-1),f):
                    key='minecraft:cobbled_deepslate' if xx in (0,8,17,26,35,44) else 'minecraft:stone'
                    p.put(xx,y,zz,key,priority=20)
                key='minecraft:polished_andesite' if xx in (0,8,17,26,35,44) or zz in (17,26,35) else 'minecraft:gravel'
                p.put(xx,f,zz,key,priority=30)
                for dy in (1,2,3):p.put(xx,f+dy,zz,'minecraft:air',priority=90)
                cells.add((xx,zz,f));p.path_cells.add((xx,zz));p.path_heights[xx,zz]=f
    for x,z,f in cells:p.walk(label,[(x,z)],f)


def paths(p):
    pave(p,'cottage-air-only-authorized-connector',CONNECTOR+((0,22),),floor=0)
    pave(p,'winding-craft-lane',STREET,width=3)
    for lot in lots():
        x,z=lot.entry
        # Individually fitted short thresholds rather than long lot driveways.
        targets={'cobbler':(7,22),'luthier':(16,19),'potter':(28,19),'glazier':(38,27),'grocer':(7,23),'stoneleaf':(22,20)}
        tx,tz=targets[lot.ident]
        step=1 if tz>z else -1
        pave(p,lot.ident+'-threshold',[(x,z+step),(tx,tz)],floor=road_floor(x))
        if lot.floor != road_floor(x):
            p.zone=lot.name
            p.put(x,road_floor(x),z+step,'minecraft:stone_brick_stairs',priority=101,
                  facing='south' if lot.front=='south' else 'north',half='bottom',shape='straight',waterlogged=False)
    for z in (22,23,24):
        p.put(11,0,z,'minecraft:stone_brick_stairs',priority=101,facing='west',half='bottom',shape='straight',waterlogged=False)
    # The side approach meets the existing bascule step at world1189,-1093;
    # every original bridge block and its clearance air remain untouched.
    pave(p,'existing-bascule-side-approach',[(42,27),(48,25),(52,24)],floor=-1)


class CraftLife(Life):
    def scene(self, ident, title, intent):
        self.p.zone=next((v.name for v in lots() if v.ident==ident),'Bramble Lane, market courts and authored garden edges')
        self.name_group(title,intent)

    def shelf(self,x,y,z,facing,item,title):
        dx,dz={'east':(-1,0),'west':(1,0),'north':(0,1),'south':(0,-1)}[facing]
        backing=self.p.blocks.get((x+dx,y,z+dz),'minecraft:air').split('[',1)[0]
        if backing.startswith('dawnoftimebuilder:') and backing.endswith('plastered_stone') or backing=='minecraft:stripped_birch_log':
            self.inventory((x,y,z),'supplementaries:item_shelf',[item],title,slots=1,facing=facing,waterlogged=False)
        else:super().shelf(x,y,z,facing,item,title)

    def light(self,x,y,z):
        self.put(x,y,z,'minecraft:lantern',hanging=True,waterlogged=False)
        support=next((yy for yy in range(y+1,y+7) if self.p.blocks.get((x,yy,z),'minecraft:air')!='minecraft:air'),None)
        if support is None:raise UserError('Craft lantern has no actual roof/ceiling support')
        for yy in range(y+1,support):self.put(x,yy,z,'minecraft:chain',axis='y',waterlogged=False)

    def bed(self,x,f,z,wood='spruce',color='green'):
        for part,zz in (('head',z),('foot',z+1)):
            self.put(x,f+1,zz,'handcrafted:'+wood+'_fancy_bed',facing='north',part=part,color=color,shape='single',occupied=False)


def furnishings(d):
    d.scene('cobbler','Bramble & Buckle is a leather workshop','A long fitted repair counter, actual leather/shears/boots displays, fitting seat, cupboard, lamp, rug and upstairs household form a specific tiny trade.')
    for z in (13,14,15):d.counter(3,0,z,'east','dark_oak')
    for z,item in ((13,'minecraft:leather'),(14,'minecraft:shears'),(15,'minecraft:leather_boots')):d.shelf(3,2,z,'east',item,'Cobbler repairs')
    d.put(4,1,15,'chipped:carpenters_table',facing='east',model='main')
    d.put(4,1,16,'chipped:carpenters_table',facing='east',model='side')
    d.chair(5,0,14,'west','dark_oak');d.put(3,1,17,'handcrafted:dark_oak_cupboard',facing='east',type='2')
    d.light(6,3,12);d.bed(4,4,10,'dark_oak');d.counter(3,4,15,'east','dark_oak');d.candle(3,6,15)
    d.table(5,4,17,'dark_oak');d.chair(6,4,17,'west','dark_oak');d.put(5,6,17,'handcrafted:stackable_book',books=3,facing='south',seed=34);d.light(6,7,12)
    d.scene('luthier','A tiny workshop full of music','An actual playable lute and string/wood samples are on real shelves; repair benches and a practice seat fill the room. Sleeping and supper rooms make the tall shop inhabited.')
    for z in (7,8,9):d.counter(13,-1,z,'east','oak')
    for z,item in ((7,'immersive_melodies:lute'),(8,'minecraft:string'),(9,'minecraft:stick')):d.shelf(13,1,z,'east',item,'Wren & Reed repair display')
    d.table(15,-1,7,'oak');d.put(15,1,7,'handcrafted:stackable_book',books=2,facing='south',seed=19)
    d.chair(15,-1,8,'north','oak');d.put(21,0,8,'minecraft:crafting_table');d.counter(22,-1,9,'north','oak');d.candle(22,1,9);d.light(16,2,10)
    d.table(15,3,8,'oak');d.chair(14,3,8,'east','oak');d.put(15,5,8,'handcrafted:wood_plate',pieces=3,facing='south',waterlogged=False)
    d.counter(13,3,11,'east','oak');d.put(13,5,11,'handcrafted:blue_glazed_medium_pot');d.light(16,6,10)
    d.bed(15,7,7,'oak','yellow');d.put(14,8,11,'handcrafted:oak_cupboard',facing='east',type='2');d.light(16,10,10)
    d.scene('potter','Clay & Candle makes and sells real pottery','A clay bench, filled material displays, modelled pots, kiln, water, samples and a stool occupy the little shop, with a private sleeping corner above.')
    for z in (9,10,11):d.counter(26,-2,z,'east','birch','calcite')
    d.shelf(26,0,9,'east','minecraft:clay_ball','Clay ready for throwing');d.put(26,0,10,'handcrafted:blue_glazed_medium_pot');d.put(26,0,11,'handcrafted:terracotta_thin_pot')
    d.put(28,-1,8,'minecraft:furnace',facing='south',lit=False);d.put(29,-1,8,'minecraft:water_cauldron',level=3)
    d.table(28,-2,11,'birch');d.chair(27,-2,11,'east','birch');d.light(28,1,12)
    d.bed(27,2,9,'birch','blue');d.put(26,3,13,'handcrafted:birch_cupboard',facing='east',type='1');d.candle(26,4,13);d.light(28,5,12)
    d.scene('glazier','Copper & Glass repairs lamps and windows','A fitted glass bench, real furnace, sand/glass/copper item shelves, workshop desk and bright sample pottery establish the repair trade without pretending to be a powered factory.')
    for z in (19,20,21):d.counter(35,-1,z,'east','spruce','calcite')
    for z,item in ((19,'minecraft:glass'),(20,'minecraft:copper_ingot'),(21,'minecraft:lantern')):d.shelf(35,1,z,'east',item,'Glazier repair materials')
    d.put(38,0,18,'minecraft:furnace',facing='south',lit=False);d.chair(38,-1,21,'west');d.light(38,2,22)
    d.bed(37,3,19,'spruce');d.counter(36,3,23,'east');d.put(36,5,23,'handcrafted:stackable_book',books=2,facing='east',seed=51);d.light(38,6,22)
    d.scene('grocer','The Clover Pantry is ready for market morning','The open loggia has a produce counter, actual bowl/bread/honey shelves, pantry stock, kitchen and a family apartment rather than an empty ground-floor hall.')
    for x in (4,5):d.counter(x,0,27,'north','oak','calcite')
    for z in (29,30):d.counter(4,0,z,'east','oak')
    d.shelf(4,2,29,'east','minecraft:bread','Daily bread');d.shelf(4,2,30,'east','minecraft:honey_bottle','Orchard honey')
    d.put(6,1,32,'farmersdelight:stove',facing='north',lit=True);d.barrel(4,0,32,'Clover Pantry provisions',['minecraft:apple','minecraft:carrot','minecraft:potato']);d.light(6,3,30)
    d.bed(5,4,30,'oak','yellow');d.table(5,4,27,'oak');d.chair(6,4,27,'west','oak');d.put(5,6,27,'handcrafted:wood_plate',pieces=3,facing='south',waterlogged=False);d.light(6,7,29)
    d.scene('stoneleaf','A mason and carpenter share the workyard','A real native stonecutter, two-part Chipped mason table, repair bench, actual tool displays, carved samples and short lean-to supply detailed useful work rather than fake machinery.')
    for z in (28,29):d.counter(19,-1,z,'east')
    d.shelf(19,1,28,'east','minecraft:stone_pickaxe','Stoneleaf tools');d.shelf(19,1,29,'east','minecraft:brick','Brick sample')
    d.put(24,0,27,'minecraft:stonecutter',facing='north');d.put(25,0,31,'chipped:mason_table',facing='north',model='main');d.put(26,0,31,'chipped:mason_table',facing='north',model='side')
    d.table(21,-1,31);d.chair(22,-1,31,'west');d.put(21,1,31,'handcrafted:stackable_book',books=2,facing='north',seed=12);d.light(22,2,30)
    d.scene(None,'Small market and shared workyard stories','Two thin canvas awnings, flower boxes, actual crops, rope, tool baskets, compact wheelbarrow, lit side pockets and trade signs enrich close frontages without taking the two-wide walking route.')
    for x,z,color in ((26,23,'green'),(32,19,'brown')):
        for xx in range(x-1,x+2):
            d.put(xx,-1,z,'minecraft:stone_bricks')
            d.counter(xx,-1,z,'south','spruce')
            for zz in (z-1,z):
                d.put(xx,3,zz,'supplementaries:awning_'+color,facing='south',bottom=False,slanted=zz==z,waterlogged=False)
        d.put(x,1,z,'handcrafted:terracotta_medium_pot')
        d.put(x-1,1,z,'handcrafted:wood_plate',pieces=3,facing='south',waterlogged=False)
        for xx in (x-1,x+1):
            d.put(xx,-1,z-1,'minecraft:stone_bricks')
            for y in (0,1,2):d.put(xx,y,z-1,'minecraft:spruce_fence',waterlogged=False)
    d.put(29,0,24,'mcwholidays:hay_wheelbarrow',facing='south')
    d.barrel(28,-1,21,'Market garden produce',['minecraft:beetroot','minecraft:carrot','minecraft:apple'])
    for x,z in ((1,25),(13,18),(20,22),(34,30),(44,31)):
        g=d.p.ground(x,z)
        d.put(x,g,z,'minecraft:mossy_stone_bricks')
        d.put(x,g+1,z,'mcwlights:covered_garden_light',lit=True,powered=False)
    for lot in lots():
        d.p.zone=lot.name
        x=lot.entry[0]
        upper=lot.levels[1] if len(lot.levels)>1 else lot.levels[0]
        frontz=(max(z for xx,z in upper if xx==x) if lot.front=='south' else min(z for xx,z in upper if xx==x))
        y=lot.floor+6 if len(lot.levels)>1 else lot.floor+3
        sign_lines={'cobbler':['Bramble','& Buckle','Leather repair'],'luthier':['Wren & Reed','Instruments','& repair'],
                    'potter':['Clay & Candle','Pottery','& wax'],'glazier':['Copper & Glass','Lamp repair','& windows'],
                    'grocer':['The Clover','Pantry','Fresh provisions'],'stoneleaf':['The Stoneleaf','Workshop','Stone & timber']}
        d.p.sign(x,y,frontz+(1 if lot.front=='south' else -1),sign_lines[lot.ident],lot.front)
    for ident,x,f,z,face in (('cobbler',3,0,20,'south'),('luthier',13,-1,15,'south'),('potter',26,-2,17,'south')):
        d.p.zone=next(lot.name for lot in lots() if lot.ident==ident)
        d.inventory((x,f+1,z),'supplementaries:flower_box',['minecraft:allium','minecraft:azure_bluet','minecraft:poppy'],
                    'Flowers at the '+ident+' window',slots=3,face='wall',facing=face,light_level=0,waterlogged=False)


def check(d):
    blocked=[]
    allowed=('minecraft:air','mcwdoors:dark_oak_cottage_door')
    for x,y,z in d.p.navigation:
        for yy in (y,y+1):
            if d.p.blocks.get((x,yy,z),'minecraft:air').split('[',1)[0] not in allowed:blocked.append([x,yy,z])
    if blocked:raise UserError('Furnished craft lane blocks its preserved body route: '+str(blocked[:10]))
    materials=[require_material_rule({p:s for p,s in d.p.blocks.items() if d.p.owners[p]==lot.name},lot.name) for lot in lots()]
    outdoor=require_outdoor_rule(d.p.blocks,'craft lane outdoors')
    return {'materials':materials,'outdoor_material_rule':outdoor,'reserved_body_cells':len(d.p.navigation),'blocked':[],'complete_beds':bed_pairs(d),
            'continuous_cottage_to_bascule_path':lane_access(d.p),'furnished_room_access':room_access(d.p),
            'exact_exclusion_masks':d.p.mask_provenance,'reviewed_cottage_air_connector_cells':[list(p) for p in sorted(d.p.connector_overrides)],'native_walking_and_artistic_acceptance':'pending'}


def lane_access(p):
    start,goal=CONNECTOR[0],(52,24)
    queue,prev=deque([start]),{start:None}
    while queue and goal not in prev:
        x,z=queue.popleft()
        for v in ((x-1,z),(x+1,z),(x,z-1),(x,z+1)):
            if v in prev or v not in p.path_cells or abs(p.path_heights[v]-p.path_heights[x,z])>1:continue
            prev[v]=(x,z);queue.append(v)
    if goal not in prev:raise UserError('Craft road is not continuously connected from cottage to existing stair')
    route=[];v=goal
    while v is not None:route.append([v[0],p.path_heights[v],v[1]]);v=prev[v]
    return {'local_floor_path':route[::-1],'stairs_and_walking':'Source connectivity only; native walking remains pending'}


def room_access(p):
    goals={'cobbler':[(6,13),(6,12)],'luthier':[(16,10),(16,11),(17,10)],
           'potter':[(28,12),(28,12)],'glazier':[(38,22),(38,22)],
           'grocer':[(6,30),(7,30)],'stoneleaf':[(22,29)]}
    rows=[]
    for lot in lots():
        for level,cells in enumerate(lot.levels):
            f=lot.floor+level*4;goal=goals[lot.ident][level]
            if level==0:start=lot.entry
            else:
                row=next(r for r in p.routes if r['id']==lot.ident+'-'+str(level-1)+'-landing-1')
                start=(int(row['local_player_feet'][0][0]),int(row['local_player_feet'][0][2]))
            def clear(v):return v in cells and all(p.blocks.get((v[0],f+dy,v[1]),'minecraft:air').split('[',1)[0] in ('minecraft:air','mcwdoors:dark_oak_cottage_door') for dy in (1,2))
            q,prev=deque([start]),{start:None}
            while q and goal not in prev:
                x,z=q.popleft()
                for v in ((x-1,z),(x+1,z),(x,z-1),(x,z+1)):
                    if v not in prev and clear(v):prev[v]=(x,z);q.append(v)
            if not clear(goal) or goal not in prev:raise UserError('A furnished craft room is inaccessible: '+str((lot.ident,level)))
            route=[];v=goal
            while v is not None:route.append(list(v));v=prev[v]
            rows.append({'building':lot.ident,'level':level,'floor':f,'clear_path':route[::-1]})
    return rows


def construct(registry,survey,exclusions):
    p=CraftPlan(registry,survey,exclusions)
    p.zone='Bramble Lane, market courts and authored garden edges'
    # The actual profile records a Vinery cherry trunk at world1160,-1100,
    # ground66/top75. Clear its finite street-side crown envelope before any
    # authored building fills; do not leave an upper trunk suspended over a road.
    for x,z in rectangle(20,14,28,22):
        for y in range(p.ground(x,z)+1,16):p.put(x,y,z,'minecraft:air',priority=0)
    architecture(p);paths(p)
    # Real ground-floor doors and stair landings are connected before furnishing,
    # then retained as clear body reservations by the detail stage.
    for lot in lots():
        cells=lot.levels[0];start=lot.entry;goal=(lot.flight[0]-1,lot.flight[1]-4) if lot.flight else (22,28)
        def clear(v):return v in cells and all(p.blocks.get((v[0],lot.floor+dy,v[1]),'minecraft:air').split('[',1)[0] in ('minecraft:air','mcwdoors:dark_oak_cottage_door') for dy in (1,2))
        q,prev=deque([start]),{start:None}
        while q and goal not in prev:
            x,z=q.popleft()
            for v in ((x-1,z),(x+1,z),(x,z-1),(x,z+1)):
                if v not in prev and clear(v):prev[v]=(x,z);q.append(v)
        if goal not in prev:raise UserError('Craft shell has no door-to-work/stair access: '+lot.ident)
        route=[];v=goal
        while v is not None:route.append(v);v=prev[v]
        p.walk(lot.ident+'-door-to-stair',route,lot.floor)
    d=CraftLife(p);furnishings(d)
    return d


def prepare(home,registry_path,survey_path,exclude_paths,output,backup_sha):
    home,output=Path(home).resolve(),Path(output).resolve()
    if home.drive.upper()!='D:' or not output.is_relative_to(home/'staging') or output.exists() or not re.fullmatch('[0-9a-f]{64}',backup_sha):
        raise UserError('NEW bounded private D staging folder and reviewed current backup required')
    if len(exclude_paths)!=3 or any(Path(p).stat().st_size>8*MIB for p in [registry_path,survey_path,*exclude_paths]):raise UserError('Three exact exclusions and finite inputs required')
    registry=json.loads(Path(registry_path).read_text(encoding='utf-8'));survey=json.loads(Path(survey_path).read_text(encoding='utf-8'))
    if survey.get('report',{}).get('status')!='complete' or survey.get('report',{}).get('failures')!=0:
        raise UserError('A complete zero-failure actual native land survey is required')
    if not Path(registry['world_path']).resolve().is_relative_to(home/'staging'):raise UserError('Private staging world required; official world refused')
    exclusions=[(name,json.loads(Path(path).read_text(encoding='utf-8')),digest(Path(path))) for name,path in zip(('cottage','bascule','rosebridge'),exclude_paths)]
    for filename,sha in DISPLAY_ARTIFACTS.items():
        if digest(home/'server'/'mods'/filename)!=sha:raise UserError('Inspected actual display codec artifact changed')
    g=subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(GUARD),'-EstimatedCBytes','0','-EstimatedDBytes',str(MAX_BUNDLE)],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW,check=False);guard=json.loads(g.stdout)
    if g.returncode or not guard.get('allowed'):raise UserError('Reserve guard refused finite craft bundle')
    d=construct(registry,survey,exclusions);checks=check(d);native=d.p.serialize(backup_sha)
    data=(json.dumps(native,ensure_ascii=False,separators=(',',':'))+'\n').encode();sha=hashlib.sha256(data).hexdigest()
    manifest={'format':'awft-authored-craft-lane:1','created':utcnow(),'prototype_only':True,'source_sha256':digest(Path(__file__)),'registry_sha256':digest(Path(registry_path)),
        'native_land_survey_sha256':digest(Path(survey_path)),'reviewed_staging_backup_sha256':backup_sha,'plan_sha256':sha,'placements':len(d.p.blocks),'block_entities':len(d.p.tags),
        'origin':list(ORIGIN),'lots':d.p.lots,'rooms':d.p.rooms,'detail_scenes':d.groups,'checks':checks,'paths':d.p.routes,'mods_used':{k:sorted(v) for k,v in d.p.uses.items()},
        'display_codec_artifacts':DISPLAY_ARTIFACTS,'storage_guard':guard,'entity_commands':0,'terrain_scope':'Only bounded buildings/roof vegetation clearances and supported paths; no whole district plinth or channel fill',
        'native_capture_positions':[{'id':'cottage-to-lane','feet':[1137,68,-1094.5],'look_at':[1152,73,-1102]},
          {'id':'potter-bend','feet':[1157,67,-1097.5],'look_at':[1164,70,-1105]},
          {'id':'glazier-and-stair','feet':[1175,67,-1090],'look_at':[1187,70,-1093]},
          {'id':'cobbler-room','feet':[1142,68,-1104],'look_at':[1139,69,-1106]}],
        'visual_status':'UNVERIFIED: actual native density, roofs, terrain joins, rooms and paths must be viewed before propagation','owner_acceptance':'not inferred'}
    receipt=(json.dumps(manifest,sort_keys=True,indent=2)+'\n').encode()
    if len(data)+len(receipt)>MAX_BUNDLE:raise UserError('Craft bundle exceeds finite allocation')
    output.mkdir(parents=True,exist_ok=False);path=output/('bramble-lane-'+sha[:16]+'.json');path.write_bytes(data);(output/'manifest.json').write_bytes(receipt)
    return {'plan':str(path),'sha256':sha,'placements':len(d.p.blocks),'block_entities':len(d.p.tags),'native_visual_review':'pending'}


if __name__=='__main__':
    a=argparse.ArgumentParser(description=__doc__)
    for name in ('registry','survey','output'):a.add_argument('--'+name,type=Path,required=True)
    a.add_argument('--exclude',type=Path,nargs=3,required=True,help='Exact cottage, bascule, rosebridge plans in this order')
    a.add_argument('--backup-sha256',required=True);a.add_argument('--home',type=Path,default=Path(r'D:\A World for Two'));v=a.parse_args()
    print(json.dumps(prepare(v.home,v.registry,v.survey,v.exclude,v.output,v.backup_sha256),indent=2))
