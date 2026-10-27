"""Screenshot-driven, inventory-preserving r1 to r2 street detail delta.

The exact r1 plan remains immutable. This source makes a complete proposed r2
composition in memory, checks it, and serializes only the explicitly changed
positions and NEW hanging signs. It never replays the existing stocked/sign BEs.
Native placement and actual graphical review are separate parent-owned steps.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
import re
import subprocess

from control_room.common import UserError, digest, utcnow
from tools.artistic_street import (construct as street, designs, planned_clearance,
    building_material_checks, edge, street_z, grade, GUARD, MAX_BUNDLE, MIB)


BASELINE_SHA = 'dc9b34f400e1f40b40a713f91fca6b8fb5591fd1b9aeefc9c6680a17e61a826d'
ORIGIN = (1224, 65, -1264)


class Details:
    def __init__(self, base):
        self.base, self.p = base, copy.deepcopy(base)
        self.groups = []
        self.protected = set(base.tags)
        self.new_signs = set()
        self.group = 'Screenshot composition correction'
        self.safe_bodies = set(base.navigation)
        for row in base.routes:
            for x, y, z in row['local_player_feet']:
                self.safe_bodies.add((int(x), int(y), int(z)))

    def put(self, x, y, z, key, **props):
        if (x, y, z) in self.protected:
            raise UserError('Detail would alter an existing stocked/sign block entity')
        self.p.put(x, y, z, key, priority=200, **props)

    def air(self, x, y, z):
        self.put(x, y, z, 'minecraft:air')

    def name_group(self, title, intent):
        self.group = title
        self.groups.append({'name': title, 'intent': intent})

    def light(self, x, y, z, facing):
        if (x, y, z) in self.safe_bodies or (x, y-1, z) in self.safe_bodies:
            raise UserError('A proposed light intersects reserved player headroom')
        self.put(x, y, z, 'mcwlights:chain_wall_lantern', facing=facing)

    def hanging_sign(self, x, y, z, lines, rotation=0):
        if (x, y+1, z) not in self.p.blocks or self.p.blocks[x, y+1, z] == 'minecraft:air':
            raise UserError('A trade sign lacks its authored overhead support')
        self.put(x, y, z, 'minecraft:dark_oak_hanging_sign', attached=False,
                 rotation=rotation, waterlogged=False)
        messages = [json.dumps(json.dumps({'text': text, 'color': 'black'}))
                    for text in (lines+['']*4)[:4]]
        self.p.tags[x, y, z] = '{is_waxed:1b,front_text:{messages:['+','.join(messages)+'],color:"black",has_glowing_text:0b}}'
        self.new_signs.add((x, y, z))


def sky_breaks(d):
    d.name_group('West lane sky breaks', 'Recess the two opposing upper projections visible in the actual west-lane capture; retain the winding street and all interiors/storage.')
    base, p = d.base, d.p
    chandler = next(b for b in designs() if b.ident == 'chandler')
    p.zone = chandler.name
    # Move the chandler's third-storey front back one metre. The source roof's
    # exact end section is moved inward; angles and materials are not guessed.
    end = {(x, y): state for (x, y, z), state in base.blocks.items()
           if z == 21 and y >= 12 and base.owners[x, y, z] == chandler.name}
    for pos, state in list(base.blocks.items()):
        x, y, z = pos
        if base.owners[pos] == chandler.name and z in (21, 22) and y >= 8:
            d.air(x, y, z)
    for x in range(1, 11):
        for y in range(12, 18):
            d.air(x, y, 20)
            state = end.get((x, y), 'minecraft:air')
            key, _, suffix = state.partition('[')
            properties = dict(part.split('=') for part in suffix.rstrip(']').split(',')) if suffix else {}
            d.put(x, y, 20, key, **properties)
    for x in range(4, 8):
        for y in range(9, 12):
            d.put(x, y, 20, chandler.timber if x == 7 else 'minecraft:calcite',
                  **({'axis': 'y'} if x == 7 else {}))
    # Bookbinder: retire only the front upper bay and its lowest projecting
    # eave, keeping the real room floor and stocked chests farther inside.
    book = next(b for b in designs() if b.ident == 'bookbinder')
    p.zone = book.name
    for pos, state in list(base.blocks.items()):
        x, y, z = pos
        if base.owners[pos] == book.name and z in (22, 23) and y >= 5:
            d.air(x, y, z)
    for x in range(5, 9):
        for y in range(6, 9):
            d.put(x, y, 24, book.timber if x == 8 else 'minecraft:calcite',
                  **({'axis': 'y'} if x == 8 else {}))
    for x in range(3, 12):
        d.put(x, 9, 24, 'minecraft:dark_oak_slab', type='bottom', waterlogged=False)


def warm_joinery(d):
    d.name_group('Coherent joinery', 'Replace the isolated bright corner caps seen in all three actual captures with warm timber joint keys, preserving the architectural breaks required by the owner.')
    floors = {b.name: b.base for b in designs()}
    for pos, state in list(d.p.blocks.items()):
        owner = d.p.owners[pos]
        if owner in floors and pos[1] >= floors[owner]+4 and state == 'minecraft:polished_andesite':
            d.p.zone = owner
            d.put(*pos, 'minecraft:stripped_dark_oak_wood', axis='x')


def pane(d, x, floor, z, facing, width=3, wood='oak', height=2):
    dx, dz = (1, 0) if facing in ('north', 'south') else (0, 1)
    for n in range(width):
        for j in range(height):
            d.put(x+dx*n, floor+2+j, z+dz*n, 'mcwwindows:'+wood+'_pane_window',
                  facing=facing, part='below' if j == 0 else 'above', windowstate='closed')


def flower_sill(d, x, floor, z, facing, width=3):
    dx, dz = (1, 0) if facing in ('north', 'south') else (0, 1)
    ox, oz = {'north': (0, -1), 'south': (0, 1), 'west': (-1, 0), 'east': (1, 0)}[facing]
    flowers = ('minecraft:potted_azalea_bush', 'minecraft:potted_allium', 'minecraft:potted_fern')
    for n in range(width):
        xx, zz = x+dx*n+ox, z+dz*n+oz
        d.put(xx, floor+1, zz, 'minecraft:spruce_trapdoor',
              facing=facing, half='top', open=False, powered=False, waterlogged=False)
        d.put(xx, floor+2, zz, flowers[n % len(flowers)])


def broad_windows(d):
    d.name_group('Broad inhabited windows', 'Replace rear/quay slit openings and selected front panels with actual composed two- and three-wide Macaw pane windows, warm room light and planted sills.')
    for b in designs():
        d.p.zone = b.name
        wood = 'spruce' if b.ident in ('bookbinder', 'sailmaker', 'keeper') else 'oak'
        for level, cells in enumerate(b.levels):
            floor = b.base+level*4
            minx, maxx = min(x for x, z in cells), max(x for x, z in cells)
            back = min(z for x, z in cells) if b.front == 'south' else max(z for x, z in cells)
            facing = 'north' if b.front == 'south' else 'south'
            # One legible wide bay beats two unrelated tiny slits. A long inn
            # frontage gets a second bay on the old side wing.
            starts = [minx+2]+([maxx-3] if maxx-minx >= 10 else [])
            for wx in starts:
                if all((wx+n, back) in cells for n in range(3)):
                    pane(d, wx, floor, back, facing, 3, wood)
                    if level:
                        flower_sill(d, wx, floor, back, facing)
                    ix, iz = wx+1, back+(1 if facing == 'north' else -1)
                    if (ix, floor+3, iz) not in d.safe_bodies and (ix, floor+2, iz) not in d.safe_bodies:
                        d.put(ix, floor+3, iz, 'minecraft:lantern', hanging=True, waterlogged=False)
            if level:
                # Recessed large windows on the street side, distinct from the
                # ground-floor projecting displays. Trimmed west bays use the
                # new facade position rather than their retired old protrusion.
                wx = minx+2
                row = [z for x, z in cells if x == wx]
                front = max(row) if b.front == 'south' else min(row)
                if b.ident == 'chandler' and level == 2:
                    front = 20
                if b.ident == 'bookbinder' and level == 1:
                    front = 24
                if all((wx+n, front) in cells for n in range(3)):
                    pane(d, wx, floor, front, b.front, 3, wood)
                    # Sills are shallow, planted accents. They do not extend
                    # another full upper floor over the narrow lane.
                    flower_sill(d, wx, floor, front, b.front, 2)


def display(d, b, x, z, width=3, facing='south', contents='books'):
    d.p.zone = b.name
    floor = b.base
    outward = 1 if facing == 'south' else -1
    # The clear glass front projects one metre; its two thin pane sides show the
    # depth. Sill and hood have separate horizontal construction roles.
    for xx in range(x, x+width):
        d.put(xx, floor, z+outward, 'minecraft:spruce_slab', type='top', waterlogged=False)
        for dy in (1, 2):
            d.put(xx, floor+dy, z, 'minecraft:air')
            d.put(xx, floor+dy, z+outward, 'mcwwindows:oak_four_window',
                  facing=facing, windowstate='closed')
        if (xx, floor+3, z+outward) not in d.protected:
            d.put(xx, floor+3, z+outward, 'minecraft:dark_oak_slab', type='bottom', waterlogged=False)
    for xx in (x, x+width-1):
        for dy in (1, 2):
            if (xx, floor+dy, z) not in d.protected:
                d.put(xx, floor+dy, z, 'mcwwindows:oak_four_window',
                      facing='west' if xx == x else 'east', windowstate='closed')
    # Merchandise is a real decorative block inside the glazing, never empty
    # display text. It is intentionally below the full-size room ceiling.
    key = {'books': 'handcrafted:stackable_book', 'herbs': 'minecraft:potted_fern',
           'pots': 'handcrafted:terracotta_medium_pot', 'lamps': 'minecraft:lantern'}[contents]
    xx, zz = x+width//2, z-outward
    if (xx, floor+1, zz) not in d.safe_bodies and (xx, floor+1, zz) not in d.protected:
        props = {'books': 3, 'facing': facing, 'seed': 31} if contents == 'books' else (
            {'hanging': False, 'waterlogged': False} if contents == 'lamps' else {})
        d.put(xx, floor+1, zz, key, **props)
    if (x, floor+3, z-outward) not in d.safe_bodies:
        d.put(x, floor+3, z-outward, 'minecraft:lantern', hanging=True, waterlogged=False)


def shopfronts(d):
    d.name_group('Purposeful projecting shopfronts', 'Small glazed display bays expose the chandler, bookbinder and apothecary trades. Two-wide route checks prevent the display and light fittings from turning the lane into an obstacle course.')
    by = {b.ident: b for b in designs()}
    display(d, by['chandler'], 4, 19, 2, 'south', 'lamps')
    display(d, by['bookbinder'], 8, 25, 2, 'north', 'books')
    display(d, by['apothecary'], 17, 24, 2, 'north', 'herbs')
    # Existing full wool slabs become thin supported fabric awnings, breaking
    # the bulky canopy underside visible from the west lane.
    for b in designs():
        d.p.zone = b.name
        if b.ident not in ('chandler', 'fishmonger', 'bookbinder', 'inn'):
            continue
        for pos, state in list(d.base.blocks.items()):
            if d.base.owners[pos] == b.name and state in ('minecraft:white_wool', 'minecraft:brown_wool'):
                d.air(*pos)
        row = [z for x, z in b.levels[0] if x == b.door_x]
        front = max(row) if b.front == 'south' else min(row)
        step = 1 if b.front == 'south' else -1
        for x in range(b.door_x, b.door_x+3):
            pos = x, b.base+3, front+step
            if pos not in d.protected:
                d.put(*pos, 'supplementaries:awning_green' if b.ident in ('bookbinder', 'chandler') else 'supplementaries:awning_brown',
                      bottom=False, facing=b.front, slanted=True, waterlogged=False)


def paved_thresholds(d):
    d.name_group('Continuous door thresholds', 'Replace the isolated bare grass strips visible at the shop doors with narrow authored frontage paving and drainage joints; retain the street bends.')
    for b in designs():
        d.p.zone = 'Shared threshold paving'
        cells = b.levels[0]
        for x in sorted({x for x, z in cells}):
            row = [z for xx, z in cells if xx == x]
            front = max(row) if b.front == 'south' else min(row)
            end = street_z(x)
            step = 1 if end > front else -1
            for z in range(front+step, end, step):
                y = grade(x)
                old = d.p.blocks.get((x, y, z), '')
                if old == 'minecraft:grass_block':
                    d.put(x, y, z, 'minecraft:stone_bricks' if abs(z-front) == 1 else 'minecraft:andesite')


def lamps_and_signs(d):
    d.name_group('Warm lantern pools and trade signs', 'Warm local light, recognisable shop names and a pair of overhead chains supply visible activity layers without entities or background machines.')
    by = {b.ident: b for b in designs()}
    lights = [('chandler', 9, 3, 20, 'south'), ('sailmaker', 19, 3, 18, 'south'),
              ('inn', 28, 3, 16, 'south'), ('fishmonger', 42, 3, 17, 'east'),
              ('harbormaster', 53, 4, 21, 'south'), ('bookbinder', 10, 4, 24, 'north'),
              ('apothecary', 20, 3, 23, 'north'), ('archhouse', 24, 3, 23, 'north'),
              ('lodging', 44, 3, 25, 'north'), ('keeper', 55, 4, 28, 'north')]
    for ident, x, y, z, facing in lights:
        d.p.zone = by[ident].name
        d.light(x, y, z, facing)
    for ident, x, y, z, words, rotation in (
        ('chandler', 8, 3, 20, ['LAMPS', '& ROPE'], 0),
        ('bookbinder', 9, 4, 24, ['INK &', 'BRAMBLE'], 8),
        ('inn', 26, 3, 16, ["WREN'S", 'WAKE'], 0),
        ('fishmonger', 41, 3, 19, ['TIDE &', 'SCALE'], 0),
        ('harbormaster', 52, 4, 21, ['HARBOR', 'OFFICE'], 0),
        ('apothecary', 19, 3, 23, ['ROSEMARY', '& REMEDIES'], 8)):
        d.p.zone = by[ident].name
        d.hanging_sign(x, y, z, words, rotation)
    d.p.zone = 'Shared lane lighting'
    for x, y, z1, z2 in ((17, 9, 18, 21), (41, 5, 20, 23)):
        for z in range(z1, z2+1):
            d.put(x, y, z, 'minecraft:chain', axis='z', waterlogged=False)
        d.put(x, y-1, (z1+z2)//2, 'mcwlights:chain_lantern', hanging=True, waterlogged=False)


def vines(d, ident, x, floor, z, facing, length=3):
    b = next(b for b in designs() if b.ident == ident)
    d.p.zone = b.name
    for y in range(floor+1, floor+1+length):
        props = {'north': False, 'east': False, 'south': False, 'west': False, 'up': False}
        props[{'north': 'south', 'south': 'north', 'west': 'east', 'east': 'west'}[facing]] = True
        d.put(x, y, z, 'minecraft:vine', **props)


def court_and_balcony(d):
    d.name_group('Courtyard and upper balcony', 'A useful side balcony and shaded tea bench add quiet discoveries off the busy lane. Planting frames existing openings instead of concealing weak walls.')
    inn = next(b for b in designs() if b.ident == 'inn')
    d.p.zone = inn.name
    for x in range(29, 33):
        for z in (13, 14):
            d.put(x, 4, z, 'minecraft:stripped_oak_wood' if x == 31 else 'minecraft:spruce_planks',
                  **({'axis': 'z'} if x == 31 else {}))
    for x in range(29, 33):
        d.put(x, 5, 14, 'mcwfences:dark_oak_picket_fence', waterlogged=False)
    for x in (29, 32):
        d.put(x, 5, 13, 'mcwfences:dark_oak_picket_fence', waterlogged=False)
        d.put(x, 3, 13, 'minecraft:dark_oak_stairs', facing='north', half='top', shape='straight', waterlogged=False)
    for half, y in (('lower', 5), ('upper', 6)):
        d.put(30, y, 12, 'mcwdoors:dark_oak_cottage_door', facing='north', half=half, hinge='left', open=False, powered=False)
    d.put(32, 5, 14, 'minecraft:stripped_spruce_wood', axis='y')
    d.put(32, 6, 14, 'minecraft:potted_azalea_bush')
    d.p.walk('inn-balcony', [(30, 12), (30, 13), (31, 13)], 4)
    vines(d, 'bookbinder', 3, 5, 23, 'north', 3)
    vines(d, 'chandler', 9, 8, 21, 'south', 3)
    vines(d, 'apothecary', 12, 4, 26, 'west', 3)
    vines(d, 'archhouse', 24, 4, 22, 'north', 3)
    d.p.zone = 'Needle Court and courtyard passage'
    for x, z in ((27, 26), (29, 32)):
        d.put(x, 3, z, 'mcwlights:chain_lantern', hanging=True, waterlogged=False)
    for x, z, facing in ((29, 39, 'east'), (31, 39, 'west')):
        d.put(x, 1, z, 'handcrafted:spruce_chair', facing=facing,
              color='none', waterlogged=False)
    d.put(30, 1, 39, 'handcrafted:spruce_table', color='none', shape='single', waterlogged=False)
    d.put(30, 2, 39, 'handcrafted:terracotta_plate', facing='north', pieces=2, waterlogged=False)
    for x, z in ((29, 40), (33, 40)):
        d.put(x, 1, z, 'handcrafted:terracotta_medium_pot')


def lane_width(d):
    """Require a full two-cell wide body corridor at each authored street column."""
    rows, blocked = [], []
    for x in range(60):
        feet = (1 if x == 44 else grade(x))+1
        cz = street_z(x)
        clear = [z for z in range(cz-2, cz+3) if all(d.p.blocks.get((x, feet+dy, z), 'minecraft:air') == 'minecraft:air'
                  for dy in (0, 1))]
        pairs = [(z, z+1) for z in clear if z+1 in clear]
        if not pairs:
            blocked.append({'x': x, 'clear_z': clear})
        else:
            chosen = min(pairs, key=lambda pair: abs(sum(pair)/2-cz))
            rows.append({'x': x, 'clear_z': list(chosen), 'player_feet_y': feet})
    if blocked:
        raise UserError('Detail would remove the two-wide lane: '+str(blocked[:12]))
    return {'minimum_two_cells': True, 'columns': rows,
            'scope': 'Planned full body cells at each X column; actual native walking still required.'}


def construct(registry, origin=ORIGIN):
    d = Details(street(registry, origin))
    sky_breaks(d)
    warm_joinery(d)
    broad_windows(d)
    shopfronts(d)
    paved_thresholds(d)
    lamps_and_signs(d)
    court_and_balcony(d)
    return d


def delta_native(d, backup_sha256):
    changed = {pos for pos, state in d.p.blocks.items() if d.base.blocks.get(pos) != state}
    if changed & d.protected:
        raise UserError('Delta intersects existing stocked/sign block entities')
    if not 0 < len(changed) <= 12_000:
        raise UserError('Visual detail delta escaped its small finite scope')
    native = d.p.serialize(backup_sha256)
    ox, oy, oz = d.p.origin
    native['blocks'] = [row for row in native['blocks'] if (row[0]-ox, row[1]-oy, row[2]-oz) in changed]
    native['block_entities'] = [row for row in native['block_entities']
        if tuple(row['pos'][i]-d.p.origin[i] for i in range(3)) in d.new_signs]
    native['name'] = 'Signal Lane — screenshot-driven visual detail r2 (delta only)'
    native['landmarks'] = []
    native['baseline_sha256'] = BASELINE_SHA
    return native, changed


def verify_baseline(d, baseline, origin):
    ox, oy, oz = origin
    expected = {(x-ox, y-oy, z-oz): baseline['palette'][i] for x, y, z, i in baseline['blocks']}
    if expected != d.base.blocks:
        raise UserError('Frozen r1 source geometry no longer matches its immutable placed plan')


def prepare(home, registry_path, baseline_path, destination, backup_sha256, origin=ORIGIN):
    home, destination = Path(home).resolve(), Path(destination).resolve()
    if home.drive.upper() != 'D:' or not destination.is_relative_to(home/'staging') or destination.exists():
        raise UserError('Use a NEW bounded private D: staging output')
    if not re.fullmatch('[0-9a-f]{64}', backup_sha256):
        raise UserError('The actual reviewed current staging backup SHA-256 is required')
    if Path(registry_path).stat().st_size > 8*MIB or Path(baseline_path).stat().st_size > 4*MIB:
        raise UserError('Detail input exceeds its finite read bound')
    if digest(Path(baseline_path)) != BASELINE_SHA:
        raise UserError('This delta binds the exact immutable placed r1 plan only')
    registry = json.loads(Path(registry_path).read_text(encoding='utf-8'))
    baseline = json.loads(Path(baseline_path).read_text(encoding='utf-8'))
    if not Path(registry['world_path']).resolve().is_relative_to(home/'staging'):
        raise UserError('Private staging world required; official world refused')
    if registry['world_path'] != baseline['world_path'] or registry['seed'] != baseline['seed']:
        raise UserError('Detail inputs belong to different native staging worlds')
    guard = subprocess.run(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(GUARD),
        '-EstimatedCBytes', '0', '-EstimatedDBytes', str(MAX_BUNDLE)], capture_output=True, text=True,
        creationflags=subprocess.CREATE_NO_WINDOW, check=False)
    reserve = json.loads(guard.stdout)
    if guard.returncode or not reserve.get('allowed'):
        raise UserError('Reserve guard refused the bounded visual detail output')
    d = construct(registry, origin)
    verify_baseline(d, baseline, origin)
    clear = planned_clearance(d.p)
    if clear['blocked']:
        raise UserError('Detail obstructs a reserved walking cell: '+str(clear['blocked'][:12]))
    materials, width = building_material_checks(d.p), lane_width(d)
    native, changed = delta_native(d, backup_sha256)
    data = (json.dumps(native, ensure_ascii=False, separators=(',', ':'))+'\n').encode()
    sha = hashlib.sha256(data).hexdigest()
    before = [{'local': list(pos), 'before': d.base.blocks.get(pos, 'minecraft:air'), 'after': d.p.blocks[pos]}
              for pos in sorted(changed)]
    manifest = {'format': 'awft-artistic-street-detail:2', 'created': utcnow(), 'prototype_only': True,
        'baseline_sha256': BASELINE_SHA, 'plan_sha256': sha, 'source_sha256': digest(Path(__file__)),
        'registry_sha256': digest(Path(registry_path)), 'reviewed_staging_backup_sha256': backup_sha256,
        'origin': list(origin), 'changed_positions': len(changed), 'new_hanging_signs': len(d.new_signs),
        'existing_stocked_and_sign_BEs_preserved': len(d.protected), 'existing_BEs_replayed': 0,
        'groups': d.groups, 'material_checks': materials, 'planned_clearance': clear, 'two_wide_lane': width,
        'expected_changes': before, 'storage_guard': reserve,
        'visual_inputs': ['after-r1/street-west.png', 'after-r1/inn-bend.png', 'after-r1/quay-frontage.png'],
        'visual_status': 'UNVERIFIED r2: genuine native screenshots, lighting and walking review pending',
        'owner_acceptance': 'not inferred', 'entity_commands': 0}
    rendered = (json.dumps(manifest, sort_keys=True, indent=2)+'\n').encode()
    if len(data)+len(rendered) > MAX_BUNDLE:
        raise UserError('Detail bundle exceeded its finite allocation')
    destination.mkdir(parents=True, exist_ok=False)
    path = destination/('signal-lane-detail-r2-'+sha[:16]+'.json')
    path.write_bytes(data)
    (destination/'manifest.json').write_bytes(rendered)
    return {'plan': str(path), 'sha256': sha, 'changed_positions': len(changed),
            'new_hanging_signs': len(d.new_signs), 'existing_BEs_replayed': 0, 'native_visual_review': 'pending'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--home', type=Path, default=Path(r'D:\A World for Two'))
    parser.add_argument('--registry', type=Path, required=True)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--backup-sha256', required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.home, args.registry, args.baseline, args.output, args.backup_sha256), indent=2))
