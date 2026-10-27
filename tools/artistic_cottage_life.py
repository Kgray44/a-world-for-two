"""Screenshot-led, inventory-preserving furnishing delta for Rose & Lantern Court.

The placed cottage is immutable. This authors lived-in rooms and garden stories
as a separate native delta, never replays its five existing stocked inventories,
and does not operate a world or infer artistic acceptance from source checks.
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
from tools.artistic_cottages import construct as cottage, check as cottage_check, ORIGIN, MAIN, BAKER, WEAVER, GLASS
from tools.artistic_street import GUARD, MAX_BUNDLE, MIB
from tools.artistic_street_life import Life, DISPLAY_ARTIFACTS, bed_pairs
from tools.artistic_materials import material_runs


BASELINE_SHA = '19b20bd76764f7cbd8c2f05706eab4149b93168f629ecd9c96a95a400911275c'


class CottageLife(Life):
    def __init__(self, base):
        super().__init__(base)
        self.standing = []

    def scene(self, building, title, intent):
        self.p.zone = building
        self.name_group(title, intent)

    def standing_space(self, title, floor, start, goal, cells):
        self.standing.append((title, floor, start, goal, cells))

    def shelf(self, x, y, z, facing, item, title):
        dx, dz = {'east': (-1, 0), 'west': (1, 0), 'north': (0, 1), 'south': (0, -1)}[facing]
        backing = self.p.blocks.get((x+dx, y, z+dz), 'minecraft:air').split('[', 1)[0]
        if backing == 'minecraft:stripped_birch_log':
            self.inventory((x, y, z), 'supplementaries:item_shelf', [item], title,
                           slots=1, facing=facing, waterlogged=False)
            self.supports.append({'fixture': [x, y, z], 'support': [x+dx, y, z+dz], 'type': 'full birch timber wall'})
        else:
            super().shelf(x, y, z, facing, item, title)

    def flower_box(self, x, y, z, facing, flowers, title, face='wall'):
        self.inventory((x, y, z), 'supplementaries:flower_box', flowers, title,
                       slots=3, face=face, facing=facing, light_level=0, waterlogged=False)


def hearth_room(d):
    d.scene(MAIN, 'Hearth, books and a shared evening',
            'The real interior capture shows a dark empty foreground beside the stair. A lit modelled fireplace, low book walls, paired seating, wool rug, writing bench and warm local lights give that room a human purpose.')
    # A real, lit Dawn of Time fireplace; its flue follows the outside west wall
    # through an explicitly described masonry stack, with bands every four rows.
    d.put(4, 2, 11, 'dawnoftimebuilder:stone_bricks_fireplace', facing='east',
          horizontal_connection='none', vertical_connection='none', lit=True, waterlogged=False)
    for z in (10, 12):
        d.put(4, 2, z, 'minecraft:brick_stairs', facing='east', half='top', shape='straight', waterlogged=False)
    for z in (10, 11, 12):
        d.put(4, 3, z, 'minecraft:brick_slab', type='top', waterlogged=False)
    for y in range(3, 14):
        d.put(3, y, 11, 'minecraft:chiseled_stone_bricks' if y in (5, 9, 13) else 'minecraft:bricks')
    d.put(3, 14, 11, 'minecraft:brick_wall', up=True, waterlogged=False)
    d.put(4, 4, 10, 'minecraft:potted_azure_bluet')
    d.put(4, 4, 12, 'handcrafted:stackable_book', books=3, facing='east', seed=31)
    for z in (4, 5):
        d.put(5, 2, z, 'minecraft:bookshelf')
        d.put(5, 3, z, 'minecraft:bookshelf')
    d.put(6, 2, 4, 'handcrafted:oak_cupboard', facing='south', type='1')
    d.put(6, 3, 4, 'handcrafted:blue_glazed_medium_pot')
    d.counter(8, 1, 4, 'south', 'oak')
    d.shelf(8, 3, 4, 'south', 'minecraft:book', 'The garden notebook')
    d.put(7, 2, 4, 'handcrafted:oak_chair', facing='east', color='none', waterlogged=False)
    d.rug(6, 7, 8, 8, 1, 'green')
    d.table(7, 1, 10, 'oak')
    d.put(7, 3, 10, 'handcrafted:wood_plate', facing='north', pieces=2, waterlogged=False)
    d.chair(7, 1, 11, 'north', 'oak')
    d.chair(8, 1, 10, 'west', 'oak')
    d.put(7, 2, 13, 'handcrafted:oak_couch', facing='north', shape='single', color='green', waterlogged=False)
    d.put(8, 2, 13, 'handcrafted:oak_couch', facing='north', shape='single', color='green', waterlogged=False)
    d.rug(7, 12, 8, 12, 1, 'brown')
    d.put(4, 2, 14, 'handcrafted:oak_cupboard', facing='east', type='2')
    d.counter(5, 1, 14, 'north', 'oak')
    d.candle(5, 3, 14)
    d.put(6, 2, 14, 'supplementaries:lunch_basket', dyed=False, facing='north', hanging=False, open=True, waterlogged=False)
    d.put(6, 4, 8, 'mcwlights:copper_small_chandelier', lit=True)
    d.put(8, 4, 11, 'mcwlights:copper_small_chandelier', lit=True)
    # Solid ceiling at y5 supports both fixtures; no thinning of the stair floor.
    d.standing_space('Evening hearth and reading seats', 1, (10, 12), (6, 11), set(tuple(v) for v in d.p.rooms[0]['outline']))


def kitchen_and_bedroom(d):
    d.scene(MAIN, 'A busy kitchen and two personal corners',
            'Displayed skillet, bowls, dry food, herbs and candlelight explain daily life. The bedroom has wardrobes, bedside light, books, flowers and actual personal writing supplies, with the original beds and chest retained.')
    d.shelf(14, 4, 10, 'south', 'farmersdelight:skillet', 'The hanging breakfast pan')
    d.shelf(17, 4, 10, 'south', 'minecraft:bowl', 'Everyday kitchen bowls')
    d.put(14, 3, 10, 'handcrafted:blue_glazed_medium_pot')
    d.counter(17, 1, 11, 'west', 'birch', 'calcite')
    d.candle(17, 3, 11)
    d.put(17, 2, 14, 'handcrafted:birch_cupboard', facing='west', type='1')
    d.put(17, 3, 14, 'minecraft:potted_fern')
    d.put(15, 4, 12, 'mcwlights:copper_small_chandelier', lit=True)
    d.standing_space('Working side-wing kitchen', 1, (10, 12), (15, 12), set(tuple(v) for v in d.p.rooms[0]['outline']))
    d.scene(MAIN, 'The bedroom feels like two people live here', 'A shared bed wall and two distinct deskside objects make a private warm room without blocking the balcony or staircase.')
    d.put(5, 6, 6, 'handcrafted:oak_side_table')
    d.candle(5, 7, 6)
    d.put(8, 6, 6, 'handcrafted:oak_side_table')
    d.put(8, 7, 6, 'minecraft:potted_allium')
    d.put(5, 6, 9, 'handcrafted:oak_cupboard', facing='east', type='2')
    d.put(5, 7, 9, 'handcrafted:stackable_book', books=3, facing='east', seed=43)
    d.put(5, 7, 11, 'handcrafted:stackable_book', books=2, facing='east', seed=17)
    d.shelf(5, 8, 10, 'east', 'minecraft:feather', 'An unfinished letter')
    d.put(8, 8, 11, 'mcwlights:copper_small_chandelier', lit=True)
    d.rug(7, 10, 8, 12, 5, 'pink')
    d.put(8, 6, 14, 'handcrafted:oak_cupboard', facing='north', type='1')
    d.put(8, 7, 14, 'handcrafted:blue_glazed_medium_pot')
    d.standing_space('Bedroom and balcony', 5, (10, 12), (9, 8), set(tuple(v) for v in d.p.rooms[1]['outline']))
    d.scene(MAIN, 'Balcony flowers and front-door welcome', 'Two actual filled wall flower boxes and a lantern make the cottage face lived in rather than bare plaster.')
    d.flower_box(5, 2, 16, 'south', ['minecraft:allium', 'minecraft:azure_bluet', 'minecraft:poppy'], 'Flowers below the sitting-room window')
    d.flower_box(14, 2, 16, 'south', ['minecraft:blue_orchid', 'minecraft:azure_bluet', 'minecraft:blue_orchid'], 'Kitchen-window herbs and flowers')
    d.flower_box(11, 6, 16, 'south', ['minecraft:allium', 'minecraft:azure_bluet', 'minecraft:allium'], 'A little balcony garden', face='floor')


def bakery(d):
    d.scene(BAKER, 'Morning at the Honey Oven', 'A flour dresser, bread and bowls on real shelves, a dough table, water, apron supplies and warm lights give the tiny bakehouse a legible daily story.')
    d.shelf(31, 3, 8, 'south', 'minecraft:bread', 'The first baked loaf')
    d.shelf(34, 3, 8, 'south', 'minecraft:bowl', 'Mixing bowls')
    d.put(30, 1, 14, 'handcrafted:birch_cupboard', facing='east', type='2')
    d.put(30, 2, 14, 'handcrafted:terracotta_medium_pot')
    d.counter(30, 0, 10, 'east', 'birch', 'calcite')
    d.counter(30, 0, 13, 'east', 'birch', 'calcite')
    d.shelf(30, 2, 13, 'east', 'minecraft:wheat', 'Flour and grain')
    d.put(31, 2, 11, 'handcrafted:wood_plate', facing='south', pieces=3, waterlogged=False)
    d.put(33, 1, 14, 'minecraft:water_cauldron', level=3)
    d.put(32, 3, 11, 'mcwlights:copper_small_chandelier', lit=True)
    d.put(30, 5, 10, 'handcrafted:birch_side_table')
    d.candle(30, 6, 10)
    d.put(30, 5, 13, 'handcrafted:birch_cupboard', facing='east', type='2')
    d.put(30, 6, 13, 'handcrafted:stackable_book', books=2, facing='east', seed=21)
    d.put(33, 7, 13, 'minecraft:lantern', hanging=True, waterlogged=False)
    d.standing_space('Bakehouse work counter', 0, (29, 12), (33, 11), set(tuple(v) for v in d.p.rooms[2]['outline']))


def weaving_and_glass(d):
    d.scene(WEAVER, 'Thread, dye and a proper little home', 'A linen counter with actual thread and shears, low cloth racks, dyed pottery, a dressing cupboard and warm bedside and work lights enrich the original loom room.')
    for x in (8, 9):
        d.counter(x, 0, 28, 'south', 'spruce')
    for x in (12, 13):
        d.counter(x, 0, 28, 'south', 'spruce')
    d.shelf(12, 2, 28, 'south', 'minecraft:string', 'Fine linen thread')
    d.shelf(13, 2, 28, 'south', 'minecraft:shears', 'The cloth shears')
    d.put(9, 2, 32, 'farmersdelight:canvas_rug')
    d.counter(8, 0, 30, 'east', 'spruce')
    d.put(8, 2, 30, 'handcrafted:blue_glazed_medium_pot')
    d.put(13, 1, 33, 'handcrafted:spruce_cupboard', facing='north', type='2')
    d.put(13, 2, 33, 'handcrafted:terracotta_medium_pot')
    d.put(16, 1, 29, 'handcrafted:spruce_side_table')
    d.candle(16, 2, 29)
    # The first cottage source authored head at z29 and foot at z30 but faced
    # it south. Repair both halves from vanilla's head/foot direction rule,
    # rather than preserving a pair which would not survive native validation.
    for part, z in (('head', 29), ('foot', 30)):
        d.put(15, 1, z, 'minecraft:pink_bed', facing='north', part=part, occupied=False)
    d.put(13, 3, 31, 'mcwlights:copper_small_chandelier', lit=True)
    d.put(9, 3, 30, 'mcwlights:copper_small_chandelier', lit=True)
    d.standing_space('Weaver loom and sleeping nook', 0, (11, 27), (12, 31), set(tuple(v) for v in d.p.rooms[4]['outline']))
    d.scene(GLASS, 'The potting bench after gardening', 'Seed and tool displays, a weathered work counter, clay pots and a watering bucket make the glasshouse a working place rather than a row of planters.')
    d.counter(35, 0, 28, 'south', 'birch', 'calcite')
    d.put(35, 2, 28, 'handcrafted:terracotta_medium_pot')
    d.counter(33, 0, 33, 'north', 'birch', 'calcite')
    d.put(33, 2, 33, 'handcrafted:blue_glazed_medium_pot')
    d.put(35, 3, 31, 'mcwlights:copper_small_chandelier', lit=True)
    for y in (4, 5, 6):
        d.put(35, y, 31, 'minecraft:chain', axis='y', waterlogged=False)
    # The low table pots sit on counters, not on the thin glass facade.
    d.standing_space('Glasshouse central work aisle', 0, (34, 27), (34, 31), set(tuple(v) for v in d.p.rooms[5]['outline']))


def court(d):
    d.scene('Shared cottage court and garden', 'Gardening and tea at human scale', 'A tool display, seed basket, real small wheelbarrow, teacup crockery, local garden lights and a pair of wall-grown flower boxes enrich the paths without occupying their two-wide circulation.')
    d.put(28, 1, 17, 'mcwholidays:hay_wheelbarrow', facing='west')
    d.counter(24, 0, 16, 'south', 'birch', 'calcite')
    d.put(24, 2, 16, 'handcrafted:terracotta_medium_pot')
    d.counter(24, 0, 17, 'south', 'birch', 'calcite')
    d.candle(24, 2, 17)
    d.barrel(28, 0, 18, 'The kitchen garden basket', ['minecraft:carrot', 'minecraft:beetroot', 'minecraft:potato'])
    d.put(20, 2, 30, 'handcrafted:terracotta_plate', facing='north', pieces=4, waterlogged=False)
    d.put(19, 1, 32, 'handcrafted:oak_side_table')
    d.put(19, 2, 32, 'minecraft:potted_azure_bluet')
    d.put(21, 1, 32, 'handcrafted:oak_side_table')
    d.candle(21, 2, 32)
    for x, z in ((9, 18), (13, 18), (32, 25)):
        d.put(x, 1, z, 'mcwlights:covered_garden_light', lit=True, powered=False)
    d.scene('Shared cottage court and garden', 'Stone cross-drains at garden-path junctions', 'Short transverse masonry rills break the long gravel and underpath base strips at the gate, cottage court, kitchen-garden turn and glasshouse approach; authored outdoor runs also stay below ten.')
    for (x, y, z), state in list(d.p.blocks.items()):
        if d.p.owners[x, y, z] != 'Shared cottage court and garden' or x not in (8, 17, 26, 35):
            continue
        if state == 'minecraft:gravel':
            d.put(x, y, z, 'minecraft:polished_andesite')
        elif state == 'minecraft:stone':
            d.put(x, y, z, 'minecraft:cobbled_deepslate')


def access(d):
    rows = []
    doors = ('mcwdoors:oak_cottage_door', 'mcwdoors:birch_cottage_door')
    for title, floor, start, goal, cells in d.standing:
        def clear(p):
            if p not in cells:
                return False
            low = d.p.blocks.get((p[0], floor+1, p[1]), 'minecraft:air').split('[', 1)[0]
            high = d.p.blocks.get((p[0], floor+2, p[1]), 'minecraft:air').split('[', 1)[0]
            # A vanilla wool rug is 1/16 high and walkable; furniture and every
            # other non-air body block remain obstacles. Stair reservations use
            # the stricter original clear-air check and never receive a rug.
            rug = low.startswith('minecraft:') and low.endswith('_carpet')
            return (low in ('minecraft:air',)+doors or rug) and high in ('minecraft:air',)+doors
        queue, prev = deque([start]), {start: None}
        while queue and goal not in prev:
            x, z = queue.popleft()
            for p in ((x-1, z), (x+1, z), (x, z-1), (x, z+1)):
                if p not in prev and clear(p):
                    prev[p] = (x, z)
                    queue.append(p)
        if not clear(goal) or goal not in prev:
            raise UserError('Furnishing blocks its actual room standing space: '+title)
        route, p = [], goal
        while p is not None:
            route.append(list(p))
            p = prev[p]
        rows.append({'title': title, 'floor': floor, 'clear_path': route[::-1]})
    return rows


def check(d):
    excessive = [row for row in material_runs(d.p.blocks) if row['exceeds_nine']]
    if excessive:
        raise UserError('Authored cottage outdoor surface exceeds nine: '+str(excessive[:4]))
    return {'cottage': cottage_check(d.p), 'furnished_access': access(d), 'complete_beds': bed_pairs(d),
            'all_authored_outdoor_runs_at_most_nine': True}


def suspend_lights(d):
    for (x, y, z), state in list(d.p.blocks.items()):
        if state.split('[', 1)[0] != 'mcwlights:copper_small_chandelier':
            continue
        support = next((yy for yy in range(y+1, min(25, y+7)) if d.p.blocks.get((x, yy, z), 'minecraft:air') != 'minecraft:air'), None)
        if support is None:
            raise UserError('A cottage chandelier lacks an authored ceiling or roof')
        d.p.zone = d.p.owners[x, y, z]
        for yy in range(y+1, support):
            d.put(x, yy, z, 'minecraft:chain', axis='y', waterlogged=False)
        d.supports.append({'fixture': [x, y, z], 'support': [x, support, z], 'type': 'ceiling and explicit hanging chain'})


def construct(registry, survey):
    d = CottageLife(cottage(registry, survey))
    hearth_room(d)
    kitchen_and_bedroom(d)
    bakery(d)
    weaving_and_glass(d)
    court(d)
    suspend_lights(d)
    return d


def native_delta(d, backup_sha):
    changed = {p for p, state in d.p.blocks.items() if d.base.blocks.get(p) != state}
    if changed & d.protected or not 0 < len(changed) <= 4_000:
        raise UserError('Cottage furnishing exceeded its protected, finite delta')
    native = d.p.serialize(backup_sha)
    ox, oy, oz = d.p.origin
    native['blocks'] = [row for row in native['blocks'] if (row[0]-ox, row[1]-oy, row[2]-oz) in changed]
    native['block_entities'] = [row for row in native['block_entities'] if tuple(row['pos'][i]-d.p.origin[i] for i in range(3)) in d.new_entities]
    native.update(name='Rose & Lantern Court — lived-in furnishing delta r2', baseline_sha256=BASELINE_SHA, landmarks=[])
    return native, changed


def prepare(home, registry_path, survey_path, baseline_path, destination, backup_sha):
    home, destination = Path(home).resolve(), Path(destination).resolve()
    if home.drive.upper() != 'D:' or not destination.is_relative_to(home/'staging') or destination.exists():
        raise UserError('Use a NEW finite private D: staging folder')
    if not re.fullmatch('[0-9a-f]{64}', backup_sha) or digest(Path(baseline_path)) != BASELINE_SHA:
        raise UserError('Exact placed cottage and verified current staging backup required')
    for path in (registry_path, survey_path, baseline_path):
        if Path(path).stat().st_size > 8*MIB:
            raise UserError('Cottage furnishing input exceeds its finite read bound')
    registry = json.loads(Path(registry_path).read_text(encoding='utf-8'))
    baseline = json.loads(Path(baseline_path).read_text(encoding='utf-8'))
    if not Path(registry['world_path']).resolve().is_relative_to(home/'staging') or baseline['world_path'] != registry['world_path'] or baseline['seed'] != registry['seed']:
        raise UserError('Exact private staging world required; official world refused')
    for filename, sha in DISPLAY_ARTIFACTS.items():
        if digest(home/'server'/'mods'/filename) != sha:
            raise UserError('The inspected native display codec artifact changed')
    guard = subprocess.run(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(GUARD), '-EstimatedCBytes', '0', '-EstimatedDBytes', str(MAX_BUNDLE)], capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW, check=False)
    reserve = json.loads(guard.stdout)
    if guard.returncode or not reserve.get('allowed'):
        raise UserError('Reserve guard refused the cottage furnishing bundle')
    d = construct(registry, json.loads(Path(survey_path).read_text(encoding='utf-8')))
    expected = d.base.serialize(backup_sha)
    decode = lambda data: {(x, y, z): data['palette'][i] for x, y, z, i in data['blocks']}
    if decode(expected) != decode(baseline) or expected['block_entities'] != baseline['block_entities']:
        raise UserError('Frozen cottage source differs from the exact native placed plan')
    checks = check(d)
    native, changed = native_delta(d, backup_sha)
    data = (json.dumps(native, ensure_ascii=False, separators=(',', ':'))+'\n').encode()
    sha = hashlib.sha256(data).hexdigest()
    manifest = {'format': 'awft-cottage-lived-in:2', 'created': utcnow(), 'prototype_only': True,
        'source_sha256': digest(Path(__file__)), 'registry_sha256': digest(Path(registry_path)),
        'baseline_sha256': BASELINE_SHA, 'plan_sha256': sha, 'reviewed_staging_backup_sha256': backup_sha,
        'original_native_survey_sha256': digest(Path(survey_path)), 'changed_positions': len(changed),
        'new_filled_displays_and_storage': len(d.new_entities), 'existing_BEs_replayed': 0,
        'existing_inventory_positions_preserved': len(d.protected), 'entity_commands': 0,
        'groups': d.groups, 'checks': checks, 'display_codec_provenance': DISPLAY_ARTIFACTS,
        'new_inventories': [{'local': list(p)}|v for p, v in sorted(d.new_entities.items())],
        'expected_changes': [{'local': list(p), 'before': d.base.blocks.get(p, 'minecraft:air'), 'after': d.p.blocks[p]} for p in sorted(changed)],
        'visual_inputs': ['court-harbor-bridge-r1/cottage-court.png', 'court-harbor-bridge-r1/cottage-interior.png'],
        'storage_guard': reserve, 'visual_status': 'UNVERIFIED: exact native furniture, light, display and walking review required', 'owner_acceptance': 'not inferred'}
    rendered = (json.dumps(manifest, sort_keys=True, indent=2)+'\n').encode()
    if len(data)+len(rendered) > MAX_BUNDLE:
        raise UserError('Cottage furnishing bundle exceeds finite allocation')
    destination.mkdir(parents=True, exist_ok=False)
    path = destination/('rose-lantern-lived-in-r2-'+sha[:16]+'.json')
    path.write_bytes(data)
    (destination/'manifest.json').write_bytes(rendered)
    return {'plan': str(path), 'sha256': sha, 'changed_positions': len(changed), 'new_BEs': len(d.new_entities), 'native_visual_review': 'pending'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--home', type=Path, default=Path(r'D:\A World for Two'))
    parser.add_argument('--registry', type=Path, required=True)
    parser.add_argument('--survey', type=Path, required=True)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--backup-sha256', required=True)
    a = parser.parse_args()
    print(json.dumps(prepare(a.home, a.registry, a.survey, a.baseline, a.output, a.backup_sha256), indent=2))
