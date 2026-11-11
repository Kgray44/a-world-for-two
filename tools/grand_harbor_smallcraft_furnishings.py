"""Distinct smallcraft furnishing additions, restricted to original authored AIR.

The caller supplies a fully built local SmallCraft and owns patch/export/native
admission. This module never replays a hull, moves stock or contacts Minecraft.
"""
from __future__ import annotations

from copy import deepcopy

from control_room.common import UserError
from tools.artistic_materials import require_material_rule
from tools.grand_harbor_fleet import AIR, circulation


# Fixed small original-AIR groups, deliberately different for each vessel.
TARGETS = {
    'tern-pilot-cutter': {(2, 2, 7), (2, 3, 7), (2, 2, 8), (2, 2, 9),
                         (-2, 2, 7), (-2, 3, 7), (-2, 2, -5), (-2, 2, -2), (-2, 3, -2)},
    'salt-marigold-ketch': {(-3, 2, -5), (-3, 3, -5), (-3, 2, 1), (3, 2, -5), (3, 3, -5),
                           (-3, 2, -2), (-3, 3, -2), (2, 2, 8), (2, 2, 10), (2, 3, 10), (-2, 3, -3)},
    'reed-fin-river-lighter': {(2, 2, -5), (2, 2, -4), (2, 2, -3), (-2, 2, -2), (-2, 2, 0),
                              (-2, 2, 2), (2, 2, 4), (2, 2, 5), (2, 2, 6), (2, 2, 7), (-1, 2, -2)},
}


def decorate(p):
    """Add original furnishings; preserve every original non-AIR state and tag."""
    key = p.spec.key
    if key not in TARGETS:
        raise UserError('Only the three original smallcraft have a furnishing recipe')
    # Capture once, before any addition. Absent/unwritten cells are never AIR.
    baseline, original_tags = dict(p.blocks), deepcopy(p.tags)
    original_commands = list(p.commands)
    original_rooms = deepcopy(p.rooms)
    reserved = set(getattr(p, 'hatch_clearance', ())) | set(getattr(p, 'route_clearance', ()))
    for room in original_rooms:
        x, y, z = room['local_anchor']
        reserved.update((x, y+n, z) for n in (1, 2))
    # Preserve the original central working lane and the entire starboard gate.
    reserved.update((x, y, z) for x in (0, 1) for y in (2, 3)
                    for z in range(p.spec.fore, p.spec.aft+1))
    reserved.update((x, y, z) for x in range(2, 9) for y in (2, 3, 4) for z in (0, 1))
    for pos in TARGETS[key]:
        if baseline.get(pos) != AIR or pos in original_tags or pos in reserved:
            raise UserError('Furnishings require original authored AIR outside existing tags/routes: '+str(pos))

    touched = set()

    def put(pos, block, **props):
        if pos not in TARGETS[key]:
            raise UserError('Furnishing escaped its fixed original-AIR cells')
        p.put(*pos, block, **props)
        touched.add(pos)

    def chest(pos, title, items, facing):
        # All inventories here belong to NEW original-AIR containers. Reorient
        # only this new chest and restore its own newly authored tag afterward.
        p.chest(*pos, title, items)
        tag = p.tags[pos]
        put(pos, 'minecraft:chest', facing=facing, type='single', waterlogged=False)
        p.tag(*pos, tag)

    def sign(pos, lines):
        p.sign(*pos, lines)
        touched.add(pos)

    if key == 'tern-pilot-cutter':
        put((2, 2, 7), 'minecraft:cartography_table')
        put((2, 3, 7), 'supplementaries:hourglass', facing='north', light_level=0, waterlogged=False)
        put((2, 2, 8), 'handcrafted:dark_oak_cupboard', facing='west', type=1)
        chest((2, 2, 9), 'Tern - pilot log and spare glasses',
              ['minecraft:spyglass', 'minecraft:compass', 'minecraft:writable_book', 'minecraft:paper', 'minecraft:feather'], 'west')
        put((-2, 2, 7), 'minecraft:barrel', facing='up', open=False)
        put((-2, 3, 7), 'minecraft:candle', candles=2, lit=True, waterlogged=False)
        chest((-2, 2, -5), 'Tern - sounding line and repair spares',
              ['minecraft:lead', 'minecraft:string', 'minecraft:iron_axe', 'minecraft:oak_planks'], 'east')
        put((-2, 2, -2), 'minecraft:barrel', facing='east', open=False)
        sign((-2, 3, -2), ['TERN', 'Pilot on duty', 'Tides and shoals', 'Log in the cuddy'])
        groups = [
            'Starboard pilot chart station with a supported hourglass and cupboard',
            'New labelled pilot-log and spyglass chest facing the cabin passage',
            'Berth-side cask and supported twin candles beside the retained original berth',
            'Foredeck sounding/repair chest, service cask and pilot-duty sign',
        ]
    elif key == 'salt-marigold-ketch':
        put((-3, 2, -5), 'minecraft:crafting_table')
        put((-3, 3, -5), 'farmersdelight:cutting_board', facing='east', waterlogged=False)
        chest((-3, 2, 1), 'Salt Marigold - hooks, line and fish preparation',
              ['minecraft:fishing_rod', 'minecraft:string', 'minecraft:shears', 'farmersdelight:iron_knife'], 'east')
        put((3, 2, -5), 'chipped:spruce_crate', facing='up', open=False)
        put((3, 3, -5), 'minecraft:hay_block', axis='y')
        put((-3, 2, -2), 'minecraft:barrel', facing='east', open=False)
        put((-3, 3, -2), 'chipped:bundled_white_wool')
        chest((2, 2, 8), 'Salt Marigold - dry pantry',
              ['minecraft:bowl', 'minecraft:cooked_cod', 'minecraft:dried_kelp', 'minecraft:carrot'], 'west')
        put((2, 2, 10), 'minecraft:barrel', facing='up', open=False)
        put((2, 3, 10), 'farmersdelight:cooking_pot', facing='west', waterlogged=False)
        sign((-2, 3, -3), ['SALT MARIGOLD', 'Lines mended here', 'Fish to port', 'Dry stores aft'])
        groups = [
            'Port fish-preparation bench with supported cutting board and new tackle/knife chest',
            'Separate forward provision crate and hay load, leaving the original rig and lane intact',
            'Canvas folded over a service cask beside the retained fishing barrels',
            'Sheltered dry-pantry chest and cold cooking pot supported by a full cask',
            'Net-mending sign above a retained original barrel, with its state and stock unchanged',
        ]
    else:
        put((2, 2, -5), 'minecraft:hay_block', axis='y')
        put((2, 2, -4), 'chipped:spruce_crate', facing='up', open=False)
        put((2, 2, -3), 'minecraft:barrel', facing='north', open=False)
        put((-2, 2, -2), 'minecraft:crafting_table')
        chest((-2, 2, 0), 'Reed Fin - sweep and hull repair spares',
              ['minecraft:iron_axe', 'minecraft:oak_planks', 'minecraft:string', 'minecraft:stick'], 'east')
        put((-2, 2, 2), 'chipped:bundled_white_wool')
        put((2, 2, 4), 'minecraft:stripped_spruce_log', axis='z')
        put((2, 2, 5), 'minecraft:stripped_spruce_log', axis='z')
        chest((2, 2, 6), 'Reed Fin - river tallies and soundings',
              ['minecraft:compass', 'minecraft:map', 'minecraft:writable_book', 'minecraft:clock'], 'west')
        put((2, 2, 7), 'minecraft:cartography_table')
        sign((-1, 2, -2), ['REED FIN', 'Upstream freight', 'Spare line to port', 'River charts aft'])
        groups = [
            'Varied forward river freight: hay, crate and a crosswise cask',
            'Port repair work surface and new labelled spare-line/tool chest beside the retained sweeps',
            'Separate folded canvas and two lengths of repair timber in original deck AIR',
            'After river-chart table and navigation/tally chest facing the working lane',
            'Low freight-and-repair sign with the central route and original cargo preserved',
        ]

    if touched != TARGETS[key]:
        raise UserError('The fixed furnishing recipe did not cover exactly its reviewed cells')
    if set(p.blocks) != set(baseline):
        raise UserError('Furnishings must not consume any UNWRITTEN cell')
    if any(p.blocks[pos] != state for pos, state in baseline.items() if state != AIR):
        raise UserError('Furnishings changed an original non-AIR state')
    if any(p.tags.get(pos) != tag for pos, tag in original_tags.items()):
        raise UserError('Furnishings changed original stock or block-entity tags')
    if p.commands != original_commands or p.rooms != original_rooms:
        raise UserError('Furnishings must preserve original commands and room anchors')
    route = circulation(p)
    materials = require_material_rule(p.blocks, p.spec.name+' furnished smallcraft')
    return {'vessel': key, 'visual_groups': groups, 'new_original_AIR_cells': len(touched),
            'original_non_AIR_and_tags_unchanged': True, 'circulation': route, 'materials': materials,
            'entities_or_commands_added': 0, 'native_visual_and_functional_acceptance': 'UNVERIFIED'}
