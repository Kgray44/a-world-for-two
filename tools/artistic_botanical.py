"""Original rooted botanical scene components; no native placement or LIFE spawn.

The owner reference is private, unchanged and never emitted as project artwork.
Every component needs actual FULL saved states, exact native palette properties,
an explicit architectural owner and current route/mechanism/view reservations.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Callable
import argparse
import hashlib
import json
from pathlib import Path
import time

from control_room.common import UserError, digest, read_json
from tools.artistic_materials import require_material_rule, require_outdoor_rule
from tools.artistic_spawn_plaza import state

REFERENCE_SHA256 = '0be4ca5acd81e4ce02749ffab1d190ab58e2f50644d9736890041e7b57e6aaab'
AIR = {'minecraft:air', 'minecraft:cave_air', 'minecraft:void_air'}
SOIL = {'minecraft:grass_block', 'minecraft:dirt', 'minecraft:coarse_dirt',
        'minecraft:rooted_dirt', 'minecraft:podzol', 'minecraft:moss_block'}
# These are literal vanilla full blocks with sturdy faces. Unknown mod shapes,
# glass, fancy windows, trapdoors, walls, slabs and inventories never qualify.
STURDY = SOIL | {'minecraft:stone', 'minecraft:stone_bricks', 'minecraft:bricks',
                 'minecraft:mossy_stone_bricks', 'minecraft:chiseled_stone_bricks',
                 'minecraft:cobblestone', 'minecraft:mossy_cobblestone',
                 'minecraft:polished_andesite', 'minecraft:andesite'}
STURDY |= {'minecraft:' + wood + suffix for wood in
           ('oak', 'spruce', 'dark_oak', 'birch', 'cherry', 'mangrove')
           for suffix in ('_log', '_wood', '_planks')}
STURDY |= {'minecraft:stripped_' + wood + suffix for wood in
           ('oak', 'spruce', 'dark_oak', 'birch', 'cherry', 'mangrove')
           for suffix in ('_log', '_wood')}
STURDY |= {'minecraft:' + colour + suffix for colour in
           ('white', 'light_gray', 'gray', 'black', 'brown', 'red', 'orange', 'yellow',
            'lime', 'green', 'cyan', 'light_blue', 'blue', 'purple', 'magenta', 'pink')
           for suffix in ('_concrete', '_terracotta', '_wool')}
STURDY |= {'minecraft:quartz_block', 'minecraft:quartz_bricks', 'minecraft:quartz_pillar',
           'minecraft:calcite', 'minecraft:terracotta', 'minecraft:deepslate_bricks',
           'minecraft:polished_deepslate', 'minecraft:polished_blackstone_bricks'}
FACES = {'north': (0, 0, -1), 'south': (0, 0, 1),
         'west': (-1, 0, 0), 'east': (1, 0, 0)}
OPPOSITE = {'north': 'south', 'south': 'north', 'east': 'west', 'west': 'east'}
FLOWERS = ('regions_unexplored:aster', 'minecraft:cornflower',
           'regions_unexplored:pink_lupine', 'minecraft:allium',
           'regions_unexplored:felicia_daisy', 'minecraft:oxeye_daisy')
POTS = ('minecraft:potted_flowering_azalea_bush', 'minecraft:potted_azalea_bush',
        'minecraft:potted_cornflower', 'minecraft:potted_allium',
        'minecraft:potted_cherry_sapling')


def key(value):
    return value.split('[', 1)[0] if isinstance(value, str) else None


def plus(a, b, scale=1):
    return tuple(a[n] + scale * b[n] for n in range(3))


def point(value):
    if len(value) != 3 or any(type(n) is not int for n in value) or not -64 <= value[1] <= 320 or \
            abs(value[0]) > 250000 or abs(value[2]) > 250000:
        raise UserError('An exact finite integer botanical position is required')
    return tuple(value)


@dataclass
class Garden:
    registry: dict
    current: Callable[[tuple[int, int, int]], str | None]
    saved_bes: set
    reserved_body: set
    excluded_columns: set
    blocks: dict = field(default_factory=dict)
    previous: dict = field(default_factory=dict)
    roots: dict = field(default_factory=dict)
    owners: dict = field(default_factory=dict)
    scenes: list = field(default_factory=list)

    def actual(self, pos):
        pos = point(pos)
        value = self.current(pos)
        if value is None:
            raise UserError('Unknown/non-FULL saved botanical cell: ' + str(pos))
        return value

    def root(self, pos, *, soil=False):
        pos = point(pos)
        actual = self.actual(pos)
        if key(actual) not in (SOIL if soil else STURDY) or pos in self.saved_bes:
            raise UserError('A measured sturdy botanical root is required: ' + str((pos, actual)))
        self.roots[pos] = actual
        return actual

    def put(self, owner, pos, name, **properties):
        pos = point(pos)
        if not isinstance(owner, str) or not owner:
            raise UserError('Explicit whole-building botanical owner required')
        actual = self.actual(pos)  # FULL chunk read also discovers its saved BEs.
        if pos in self.saved_bes or pos in self.reserved_body or (pos[0], pos[2]) in self.excluded_columns:
            raise UserError('Preserve a BE, route, mechanism, view or whole-crown exclusion')
        if pos in self.blocks or key(actual) not in AIR:
            raise UserError('New botanical targets must be actual empty saved cells, without replay')
        value = state(self.registry, name, **properties)
        self.previous[pos] = actual
        self.blocks[pos] = value
        self.owners[pos] = owner
        if len(self.blocks) > 8192:
            raise UserError('Finite8192-cell botanical batch exceeded')

    def atomic(self, label, owner, action):
        """Refused scenes cannot leave a half planter in the output."""
        keys = set(self.blocks), set(self.roots)
        try:
            action()
        except Exception:
            for pos in set(self.blocks) - keys[0]:
                for table in (self.blocks, self.previous, self.owners):
                    table.pop(pos, None)
            for pos in set(self.roots) - keys[1]:
                self.roots.pop(pos, None)
            raise
        self.scenes.append({'label': label, 'owner': owner,
                            'new_cells': len(set(self.blocks) - keys[0]),
                            'new_root_witnesses': len(set(self.roots) - keys[1])})


def window_tray(garden, owner, wall_base, face, *, palette=FLOWERS[:3]):
    """Three flower pockets below a window, attached through real corbels.

    wall_base is the actual wall behind the soil row, two metres below the
    lowest window block. Nothing is placed at window height or in its view ray.
    """
    normal = FACES[face]
    tangent = (1, 0, 0) if normal[2] else (0, 0, 1)
    if len(palette) != 3 or any(name not in FLOWERS for name in palette):
        raise UserError('An authored three-flower tray palette is required')

    def action():
        for n in (-1, 0, 1):
            wall = plus(wall_base, tangent, n)
            garden.root(wall)
            garden.root(plus(wall, (0, -1, 0)))
            soil = plus(wall, normal)
            bracket = plus(soil, (0, -1, 0))
            garden.put(owner, bracket, 'minecraft:spruce_stairs', facing=OPPOSITE[face],
                       half='top', shape='straight', waterlogged=False)
            garden.put(owner, soil, 'minecraft:coarse_dirt')
            garden.put(owner, plus(soil, normal), 'minecraft:spruce_trapdoor',
                       facing=face, half='bottom', open=True, powered=False, waterlogged=False)
            garden.put(owner, plus(soil, (0, 1, 0)), palette[n + 1])
        # Short end cheeks close the tray; the source never copies an inventory.
        for n in (-2, 2):
            garden.put(owner, plus(plus(wall_base, tangent, n), normal),
                       'minecraft:dark_oak_trapdoor', facing='east' if normal[2] and n < 0 else
                       'west' if normal[2] else 'south' if n < 0 else 'north',
                       half='bottom', open=True, powered=False, waterlogged=False)

    garden.atomic('supported flowering window tray', owner, action)


def wall_climber(garden, owner, lower, face, *, height=6):
    if not 2 <= height <= 9:
        raise UserError('Authored wall climber height must remain2..9')
    normal = FACES[face]

    def action():
        garden.root(plus(lower, (0, -1, 0)))
        for dy in range(height):
            pos = plus(lower, (0, dy, 0))
            garden.root(plus(pos, normal, -1))
            flags = {name: False for name in ('north', 'south', 'east', 'west', 'up')}
            flags[OPPOSITE[face]] = True
            garden.put(owner, pos, 'minecraft:vine', **flags)

    garden.atomic('ground-to-eave supported climber', owner, action)


def wall_hanging_climber(garden, owner, lower, face, *, height=6):
    """Native side-attached ivy; every segment has a real full wall support.

    A wall vine does not need an invented floor block beneath its lowest leaf.
    This is explicitly hanging ivy, never a claim of a planted ground root.
    The stricter ground-rooted component above remains unchanged.
    """
    if not 2 <= height <= 9:
        raise UserError('Authored hanging ivy height must remain2..9')
    normal = FACES[face]

    def action():
        for dy in range(height):
            pos = plus(lower, (0, dy, 0))
            garden.root(plus(pos, normal, -1))
            flags = {name: False for name in ('north', 'south', 'east', 'west', 'up')}
            flags[OPPOSITE[face]] = True
            garden.put(owner, pos, 'minecraft:vine', **flags)

    garden.atomic('native wall-attached hanging ivy with every segment rooted to masonry/timber', owner, action)


def glowberry_pendant(garden, owner, top, *, length=3):
    if not 1 <= length <= 4:
        raise UserError('Short authored glowberry pendant only')

    def action():
        garden.root(plus(top, (0, 1, 0)))
        for n in range(length):
            pos = plus(top, (0, -n, 0))
            if n == length - 1:
                garden.put(owner, pos, 'minecraft:cave_vines', age=25, berries=True)
            else:
                garden.put(owner, pos, 'minecraft:cave_vines_plant', berries=n == 0)

    garden.atomic('warm rooted glowberry pendant', owner, action)


def berry_bracket(garden, owner, wall, face, *, length=3):
    """A rooted two-log eave bracket supplies a real new pendant attachment.

    The lower knee bears into a second saved wall block. Vines hang from the
    outboard log, not through the knee or from a floating decoration.
    """
    if not 1 <= length <= 4:
        raise UserError('A short explicit berry bracket is required')
    normal = FACES[face]

    def action():
        garden.root(wall)
        garden.root(plus(wall, (0, -1, 0)))
        axis = 'z' if normal[2] else 'x'
        for n in (1, 2):
            garden.put(owner, plus(wall, normal, n), 'minecraft:dark_oak_log', axis=axis)
        garden.put(owner, plus(plus(wall, normal), (0, -1, 0)),
                   'minecraft:spruce_stairs', facing=OPPOSITE[face],
                   half='top', shape='straight', waterlogged=False)
        for n in range(1, length + 1):
            pos = plus(plus(wall, normal, 2), (0, -n, 0))
            if n == length:
                garden.put(owner, pos, 'minecraft:cave_vines', age=25, berries=True)
            else:
                garden.put(owner, pos, 'minecraft:cave_vines_plant', berries=n == 1)

    garden.atomic('carved wall-rooted timber berry bracket', owner, action)


def potted_cluster(garden, owner, positions, *, palette=POTS[:3]):
    if not 1 <= len(positions) <= 3 or len(positions) != len(palette) or any(p not in POTS for p in palette):
        raise UserError('A small distinct inert pot grouping is required')

    def action():
        for pos, plant in zip(positions, palette):
            garden.root(plus(pos, (0, -1, 0)))
            garden.put(owner, pos, plant)

    garden.atomic('inert flowering pots at a human-scale threshold', owner, action)


def hedge_pocket(garden, owner, lower, face):
    tangent = (1, 0, 0) if FACES[face][2] else (0, 0, 1)

    def action():
        for n, name in enumerate(('mcwfences:azalea_hedge', 'mcwfences:flowering_azalea_hedge',
                                   'mcwfences:cherry_hedge')):
            pos = plus(lower, tangent, n)
            garden.root(plus(pos, (0, -1, 0)), soil=True)
            flags = {direction: False for direction in FACES}
            if n:
                flags['west' if tangent[0] else 'north'] = True
            if n < 2:
                flags['east' if tangent[0] else 'south'] = True
            garden.put(owner, pos, name, waterlogged=False, **flags)

    garden.atomic('three rooted hedge species around a garden pocket', owner, action)


def meadow_pocket(garden, owner, lower):
    # Unequal offsets leave negative space and a distinct view into the pocket.
    pattern = ((0, 0, FLOWERS[0]), (1, 0, FLOWERS[1]), (2, 1, FLOWERS[2]),
               (0, 2, FLOWERS[4]), (1, 2, 'minecraft:fern'))

    def action():
        for dx, dz, name in pattern:
            pos = plus(lower, (dx, 0, dz))
            garden.root(plus(pos, (0, -1, 0)), soil=True)
            garden.put(owner, pos, name)

    garden.atomic('asymmetric flower and fern garden floor', owner, action)


def cherry_bough(garden, owner, lower, face):
    """A deliberately shaped leafy timber arch, not a leaf-cube or fake tree.

    lower is beside the walking route. The branch begins four metres above
    that floor; route, window, sign and view reservations still have authority.
    """
    along = FACES[face]
    across = (1, 0, 0) if along[2] else (0, 0, 1)
    axis = 'z' if along[2] else 'x'

    def action():
        garden.root(plus(lower, (0, -1, 0)))
        logs = set()
        for dy in range(3):
            pos = plus(lower, (0, dy, 0)); logs.add(pos)
            garden.put(owner, pos, 'minecraft:stripped_dark_oak_log', axis='y')
        collar = plus(lower, (0, 3, 0)); logs.add(collar)
        garden.put(owner, collar, 'chipped:carved_stripped_dark_oak_log', axis='y')
        for n in range(5):
            pos = plus(plus(lower, (0, 4, 0)), along, n); logs.add(pos)
            garden.put(owner, pos, 'minecraft:dark_oak_log', axis=axis)
        # Crown silhouette is hand-authored in narrow staggered layers.
        # No filled volume or repeated cuboid foliage stamp is used.
        pattern = ((1, 5, 0, False), (2, 5, 0, False), (3, 5, 0, False),
                   (4, 5, 0, True), (2, 5, -1, True), (2, 5, 1, True),
                   (3, 5, 1, False), (4, 5, 1, True), (3, 6, 0, True),
                   (2, 6, 0, False), (1, 4, -1, True), (4, 4, -1, False))
        leaves = {}
        for forward, dy, side, green in pattern:
            pos = plus(plus(plus(lower, along, forward), (0, dy, 0)), across, side)
            leaves[pos] = 'minecraft:flowering_azalea_leaves' if green else 'minecraft:cherry_leaves'
        queue = deque((pos, 0) for pos in logs); distance = dict.fromkeys(logs, 0)
        while queue:
            pos, value = queue.popleft()
            for vector in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
                other = plus(pos, vector)
                if other in leaves and other not in distance and value < 6:
                    distance[other] = value + 1; queue.append((other, value + 1))
        if leaves.keys() - distance.keys():
            raise UserError('Every authored leaf must have a real connected native-log support path')
        for pos, name in leaves.items():
            garden.put(owner, pos, name, distance=distance[pos], persistent=True, waterlogged=False)

    garden.atomic('rooted sculpted cherry and flowering-azalea arch', owner, action)


def check_authored_owners(garden, original_by_owner):
    """Complete source-owned buildings, not a count of planted decorations."""
    checks = []
    for owner in sorted(set(garden.owners.values())):
        if owner not in original_by_owner:
            raise UserError('Missing exact whole-building authored material basis: ' + owner)
        whole = dict(original_by_owner[owner])
        whole.update({pos: value for pos, value in garden.blocks.items() if garden.owners[pos] == owner})
        checks.append(require_material_rule(whole, owner + ' complete botanical depth composite'))
    return checks, require_outdoor_rule(garden.blocks, 'All new authored botanical work')


def palette_proof(registry):
    """Exact native schemas used by the original components, not slug guesses."""
    names = set(FLOWERS) | set(POTS) | {'minecraft:fern', 'minecraft:vine',
        'minecraft:cave_vines', 'minecraft:cave_vines_plant', 'minecraft:coarse_dirt',
        'minecraft:spruce_stairs', 'minecraft:spruce_trapdoor', 'minecraft:dark_oak_trapdoor',
        'mcwfences:azalea_hedge', 'mcwfences:flowering_azalea_hedge', 'mcwfences:cherry_hedge',
        'minecraft:stripped_dark_oak_log', 'minecraft:dark_oak_log',
        'chipped:carved_stripped_dark_oak_log', 'minecraft:cherry_leaves',
        'minecraft:flowering_azalea_leaves'}
    missing = names - registry['blocks'].keys()
    if missing:
        raise UserError('Selected botanical native palette is incomplete: ' + str(sorted(missing)))
    return {name: registry['blocks'][name] for name in sorted(names)}


COMPONENTS = {'window_tray': window_tray, 'wall_climber': wall_climber,
              'wall_hanging_climber': wall_hanging_climber,
              'glowberry_pendant': glowberry_pendant, 'potted_cluster': potted_cluster,
              'hedge_pocket': hedge_pocket, 'meadow_pocket': meadow_pocket,
              'cherry_bough': cherry_bough, 'berry_bracket': berry_bracket}
REQUIRED_MASKS = {'current_fountain_whole_crown', 'bridge_and_machine_sweeps',
                  'zipline_flight_and_frames', 'walking_and_working_bodies',
                  'windows_signs_doors_and_views'}


def source_candidates(owner, authored, *, limit=12):
    """Compose distinct facade scenes from actual authored window/beam geometry.

    These remain candidates. In particular, an omitted source cell does not
    prove saved AIR, soil, a sturdy face, or placement authority. prepare()
    independently checks every target/root against the current FULL archive.
    """
    if not authored or not 1 <= limit <= 24:
        raise UserError('A finite exact authored building basis is required')
    xs = [p[0] for p in authored]; zs = [p[2] for p in authored]
    cx, cz = (min(xs) + max(xs)) / 2, (min(zs) + max(zs)) / 2
    candidates, selected = [], []

    def empty(pos):
        return key(authored.get(pos, 'minecraft:air')) in AIR

    def spaced(pos, distance=6):
        return all(sum((pos[n] - q[n])**2 for n in range(3)) >= distance**2 for q in selected)

    # Lowest row of each real fancy window only; never cover the window block.
    windows = sorted(p for p, value in authored.items() if
        ('window' in key(value) or key(value).endswith(('glass', 'glass_pane'))) and
        not ('window' in key(authored.get(plus(p, (0, -1, 0)), 'minecraft:air')) or
             key(authored.get(plus(p, (0, -1, 0)), 'minecraft:air')).endswith(('glass', 'glass_pane'))))
    for window in windows:
        if not spaced(window):
            continue
        faces = sorted(FACES, key=lambda face: -((window[0] - cx) * FACES[face][0] +
                                                 (window[2] - cz) * FACES[face][2]))
        for face in faces:
            normal = FACES[face]; tangent = (1, 0, 0) if normal[2] else (0, 0, 1)
            wall = plus(window, (0, -2, 0))
            roots = [plus(plus(wall, tangent, n), (0, dy, 0)) for n in (-1, 0, 1) for dy in (-1, 0)]
            if not all(key(authored.get(q)) in STURDY for q in roots):
                continue
            targets = [plus(plus(plus(wall, tangent, n), normal), (0, dy, 0))
                       for n in (-1, 0, 1) for dy in (-1, 0, 1)]
            targets += [plus(plus(wall, tangent, n), normal, 2) for n in (-1, 0, 1)]
            targets += [plus(plus(wall, tangent, n), normal) for n in (-2, 2)]
            if not all(empty(q) for q in targets):
                continue
            candidates.append({'label': owner + ' flowering bay ' + str(window),
                'owner': owner, 'kind': 'window_tray', 'args': {'wall_base': list(wall), 'face': face},
                'source_window': list(window), 'saved_admission': 'PENDING exact current FULL roots/targets/masks'})
            selected.append(window)
            break
        if len(candidates) >= min(4, limit):
            break
    # An exposed full timber underside is a genuine pendant attachment, never
    # an invented rooftop float or an automatically hung string of lamps.
    for root, value in sorted(authored.items()):
        if len(candidates) >= min(7, limit):
            break
        if key(value) not in STURDY or '_log' not in key(value) or not spaced(root, 7):
            continue
        top = plus(root, (0, -1, 0))
        if all(empty(plus(top, (0, -n, 0))) for n in range(3)):
            candidates.append({'label': owner + ' sheltered berry pendant ' + str(root),
                'owner': owner, 'kind': 'glowberry_pendant', 'args': {'top': list(top), 'length': 3},
                'saved_admission': 'PENDING exact current FULL sturdy underside and flight/view masks'})
            selected.append(root)
    # Long exposed outer piers can host supported ivy. Short decorative ribs
    # and windows interrupt this selection rather than being painted over.
    for wall, value in sorted(authored.items()):
        if len(candidates) >= limit:
            break
        if key(value) not in STURDY or not spaced(wall, 7):
            continue
        for face, normal in FACES.items():
            if (wall[0] - cx) * normal[0] + (wall[2] - cz) * normal[2] <= 0:
                continue
            lower = plus(wall, normal)
            if all(key(authored.get(plus(wall, (0, n, 0)))) in STURDY and
                   empty(plus(lower, (0, n, 0))) for n in range(6)):
                candidates.append({'label': owner + ' rooted outer pier climber ' + str(wall),
                    'owner': owner, 'kind': 'wall_climber',
                    'args': {'lower': list(lower), 'face': face, 'height': 6},
                    'saved_admission': 'PENDING current FULL ground/wall and protected openings'})
                selected.append(wall)
                break
    return candidates


def checked_member(home, row, budget):
    path = (home / row['path']).resolve()
    if not path.is_relative_to(home / 'staging') or not 0 < path.stat().st_size <= budget:
        raise UserError('Exact bounded private botanical source member required')
    if digest(path) != row['sha256']:
        raise UserError('Botanical source member changed')
    return path


def field(plan, registry):
    if plan.get('format') != 'awft-native-settlement:1' or any(
            str(plan.get(k)) != str(registry[k]) for k in ('seed', 'world_path')):
        raise UserError('Exact current-world authored botanical basis required')
    if not 0 < len(plan.get('blocks', [])) <= 150000:
        raise UserError('Finite authored botanical member exceeded')
    return {tuple(row[:3]): plan['palette'][row[3]] for row in plan['blocks']}


def prepare(home, recipe_path, recipe_sha256, output):
    """Prepare an explicit reviewed composition, preserving every refused scene.

    A recipe supplies exact current owner composites and five distinct masks.
    This routine never discovers arbitrary new rooms or treats map colours as
    native ground. No automatic world action follows a successful preparation.
    """
    from tools.artistic_south_extent import ExtentTerrain
    from tools.artistic_spawn_plaza import payload
    from tools.playtest import guard

    home, recipe_path, output = (Path(p).resolve() for p in (home, recipe_path, output))
    if not home.is_relative_to(Path(r'D:/A World for Two/staging/world-tests')) or \
            output.exists() or not output.is_relative_to(home / 'staging'):
        raise UserError('A NEW owned private botanical proposal folder is required')
    if not recipe_path.is_relative_to(home / 'staging') or recipe_path.stat().st_size > 1024**2 or \
            digest(recipe_path) != recipe_sha256:
        raise UserError('Exact bounded reviewed botanical scene recipe required')
    reserve = guard(1024**2, 16 * 1024**2)
    recipe = read_json(recipe_path)
    receipt = read_json(home / 'dashboard/settlement/backup-receipt.json')
    if recipe.get('format') != 'awft-original-botanical-composition:1' or \
            recipe.get('reference_sha256') != REFERENCE_SHA256 or receipt.get('verified') is not True or \
            (recipe.get('checkpoint_id'), recipe.get('checkpoint_sha256')) != (receipt['id'], receipt['sha256']):
        raise UserError('Bind the exact current stopped archive and unmodified private reference')
    scenes = recipe.get('scenes', [])
    if not 1 <= len(scenes) <= 256:
        raise UserError('Finite explicit1..256-scene composition required')
    masks = recipe.get('masks', [])
    if {row['role'] for row in masks} != REQUIRED_MASKS or len(masks) != len(REQUIRED_MASKS):
        raise UserError('All five current botanical custody masks are mandatory')
    registry = read_json(home / 'dashboard/settlement/registry.json')
    palette = palette_proof(registry)
    reserved, excluded, source_proof = set(), set(), []
    for row in masks:
        path = checked_member(home, row, 4 * 1024**2)
        doc = read_json(path)
        if doc.get('backup_sha256') != receipt['sha256']:
            raise UserError('Rebind every botanical reservation to the exact current saved checkpoint')
        positions = field(doc, registry)
        reserved.update(positions)
        if row['role'] == 'current_fountain_whole_crown':
            for x, _, z in positions:
                excluded.update((x + dx, z + dz) for dx in range(-5, 6) for dz in range(-5, 6))
        source_proof.append({'role': row['role'], 'sha256': row['sha256'], 'cells': len(positions)})
    owners = {}
    owner_sources = recipe.get('owners', [])
    if not 1 <= len(owner_sources) <= 64 or len({r['name'] for r in owner_sources}) != len(owner_sources):
        raise UserError('Finite distinct actual architectural owners required')
    total_bytes = sum((home / row['path']).stat().st_size for owner in owner_sources for row in owner['members'])
    if total_bytes > 64 * 1024**2:
        raise UserError('Finite64MiB authored source budget exceeded')
    for owner in owner_sources:
        combined = {}
        if not 1 <= len(owner['members']) <= 12:
            raise UserError('Explicit ordered complete owner source stack required')
        for row in owner['members']:
            path = checked_member(home, row, 16 * 1024**2)
            combined.update(field(read_json(path), registry))
            source_proof.append({'owner': owner['name'], 'sha256': row['sha256']})
        if len(combined) > 150000:
            raise UserError('Finite complete authored owner exceeded')
        owners[owner['name']] = combined
    terrain = ExtentTerrain(home, receipt, registry)
    garden = Garden(registry, lambda pos: terrain.state(*pos), terrain.entities, reserved, excluded)
    refusals = []
    try:
        for index, scene in enumerate(scenes):
            if time.monotonic() - terrain.started > 60:
                raise UserError('Finite60-second botanical preparation expired')
            if scene.get('owner') not in owners or scene.get('kind') not in COMPONENTS:
                raise UserError('Unknown botanical owner/component must be reviewed, not exempted')
            try:
                COMPONENTS[scene['kind']](garden, scene['owner'], **scene['args'])
            except UserError as error:
                refusals.append({'scene_index': index, 'label': scene.get('label'),
                                 'reason': str(error), 'partial_cells_retained': False})
        if not garden.blocks:
            raise UserError('No actual current scene was admitted; do not emit an empty planting pass')
        checks, outdoor = check_authored_owners(garden, owners)
        sources = terrain.snapshot.sources.copy()
    finally:
        terrain.close()
    docs = {'botanical-DELTA.json': payload(registry, receipt['sha256'], garden.blocks,
            'SOURCE PROPOSAL ONLY layered botanical art; native visual approval required'),
            'botanical-actual-BEFORE-VERIFY-ONLY.json': payload(registry, receipt['sha256'],
            garden.previous | garden.roots, 'VERIFY ONLY exact botanical targets and unchanged roots', before=True),
            'retained-roots-VERIFY-ONLY.json': payload(registry, receipt['sha256'], garden.roots,
            'VERIFY ONLY actual native sturdy botanical attachments', before=True)}
    docs['botanical-DELTA.json']['construction_forbidden'] = True
    raw = {name: (json.dumps(doc, separators=(',', ':')) + '\n').encode() for name, doc in docs.items()}
    manifest = {'format': 'awft-original-botanical-proposal:1', 'source_sha256': digest(Path(__file__)),
        'checkpoint_id': receipt['id'], 'checkpoint_sha256': receipt['sha256'],
        'private_reference_sha256': REFERENCE_SHA256, 'reference_copied_or_modified': False,
        'recipe_sha256': recipe_sha256, 'scenes': garden.scenes, 'refused_scenes': refusals,
        'selected_scene_count': len(scenes), 'complete_selected_composition': not refusals,
        'targets': len(garden.blocks), 'unchanged_root_witnesses': len(garden.roots),
        'native_palette': palette, 'owner_material_checks': checks, 'outdoor_material_check': outdoor,
        'custody': source_proof, 'saved_sources': sources, 'reserve': reserve,
        'native_actions': 0, 'entities_or_native_trees_created': 0, 'old_BEs_or_inventories_changed': 0,
        'native_player_or_camera_acceptance': False, 'propagation_authority': False,
        'files': {name: {'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)} for name, data in raw.items()}}
    raw['manifest.json'] = (json.dumps(manifest, indent=2) + '\n').encode()
    if sum(map(len, raw.values())) > 16 * 1024**2:
        raise UserError('Finite16MiB botanical output exceeded')
    output.mkdir()
    for name, data in raw.items():
        (output / name).write_bytes(data)
    return {'directory': str(output), 'manifest_sha256': digest(output / 'manifest.json'),
            'targets': len(garden.blocks), 'admitted_scenes': len(garden.scenes), 'refusals': refusals}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('home', 'recipe', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--recipe-sha256', required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.home, args.recipe, args.recipe_sha256, args.output), indent=2))
