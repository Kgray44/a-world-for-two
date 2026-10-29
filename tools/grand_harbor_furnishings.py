"""Additive furnishing correction for the six already placed harbor vessels.

This module authors details, never a replacement hull. Only explicit AIR cells
in the original design may change. Saved/current preimages and master admission
are separate requirements; an empty design cell is not proof of an empty world.
"""
from __future__ import annotations

from copy import deepcopy
import argparse
import json
from pathlib import Path

from control_room.common import UserError
from tools.grand_harbor_fleet import (
    AIR, SPECS, FleetShip, berthing, captain, circulation, companionways,
    galley_and_guns, hull, hull_seal, identifier, magazine_and_stores,
    raised_decks, rig, working_deck, canonical, sha, derrick_source_check,
)
from tools.artistic_materials import require_material_rule


POSES = {
    'golden-petrel': ((1110, 63, -1360), 1),
    'resolute-wren': ((1000, 63, -1366), 1),
    'mercy-of-the-tide': ((1230, 63, -1392), 1),
    'tern-pilot-cutter': ((1168, 63, -1338), 2),
    'salt-marigold-ketch': ((1228, 63, -1320), 0),
    'reed-fin-river-lighter': ((1336, 63, -1044), 0),
}
MAX_ADDITIONS_PER_SHIP = 1500


def _put(p, x, y, z, key, **properties):
    if p.blocks.get((x, y, z)) != AIR:
        raise UserError('Furnishing must occupy explicit unused design AIR: '+str((p.spec.key, x, y, z)))
    p.put(x, y, z, key, **properties)


def _book(p, x, y, z, books=3, seed=1, facing='east'):
    _put(p, x, y, z, 'handcrafted:stackable_book', books=books, seed=seed, facing=facing)


def _drawer(p, x, y, z, facing='east', variant=3):
    _put(p, x, y, z, 'handcrafted:dark_oak_drawer', facing=facing, shape='single', type=variant)


def _cupboard(p, x, y, z, facing='east'):
    _put(p, x, y, z, 'handcrafted:dark_oak_cupboard', facing=facing, type=1)
    _put(p, x, y+1, z, 'handcrafted:dark_oak_cupboard', facing=facing, type=2)


def _table(p, x, y, z):
    _put(p, x, y, z, 'handcrafted:dark_oak_table', color='none', shape='single', waterlogged=False)


def _bench(p, x, y, z, facing='west', color='none'):
    _put(p, x, y, z, 'handcrafted:dark_oak_bench', facing=facing,
         color=color, shape='single', waterlogged=False)


def _group(p, name, purpose, operation):
    before = dict(p.blocks)
    operation()
    changed = [list(pos) for pos, state in p.blocks.items() if state != before.get(pos)]
    if not changed:
        raise UserError('Empty furnishing group: '+name)
    return {'name': name, 'purpose': purpose, 'local_cells': sorted(changed)}


def petrel_counting_cabin(p):
    """Merchant's counting room, green upholstered sitting corner, sea stores."""
    f = p.spec.weather
    _cupboard(p, -8, f+1, 21)
    _cupboard(p, -8, f+1, 22)
    _drawer(p, -6, f+1, 22)
    _book(p, -6, f+2, 22, 4, 22)
    for x in (5, 6, 7):
        for z in (22, 23):
            _table(p, x, f+1, z)
    _book(p, 5, f+2, 22, 4, 17, 'west')
    _book(p, 6, f+2, 23, 2, 39, 'west')
    _put(p, 7, f+2, 22, 'handcrafted:terracotta_thin_pot')
    _put(p, 7, f+2, 23, 'minecraft:lantern', hanging=False, waterlogged=False)
    _bench(p, 5, f+1, 28, color='green')
    _bench(p, 5, f+1, 29, color='green')
    _put(p, 5, f+2, 27, 'handcrafted:blue_cup', facing='west', pieces=2, waterlogged=False)
    _book(p, -3, f+2, 29, 3, 53, 'south')
    _put(p, -5, f+1, 26, 'handcrafted:dark_oak_nightstand', facing='east', color='green', waterlogged=False)
    _put(p, -5, f+2, 26, 'handcrafted:terracotta_wide_pot')
    _cupboard(p, -3, f+1, 33, 'south')
    _drawer(p, -2, f+1, 33, 'south', 1)
    _book(p, -2, f+2, 33, 2, 77, 'south')
    for x in (-2, -1, 0):
        for z in (22, 23, 24):
            _put(p, x, f+1, z, 'minecraft:green_carpet')


def wren_dispatch_cabin(p):
    """Compact red dispatch office, packet sorting desk and stern reading seat."""
    f = p.spec.weather
    _cupboard(p, -5, f+1, 21)
    _drawer(p, -5, f+1, 22, variant=1)
    _book(p, -5, f+2, 22, 4, 91)
    for z in (21, 22):
        _table(p, -3, f+1, z)
    _book(p, -3, f+2, 21, 4, 112, 'south')
    _put(p, -3, f+2, 22, 'handcrafted:terracotta_thin_pot')
    for z in (22, 23):
        _table(p, 4, f+1, z)
    _book(p, 4, f+2, 22, 2, 131, 'west')
    _put(p, 4, f+2, 23, 'minecraft:lantern', hanging=False, waterlogged=False)
    _book(p, -3, f+2, 25, 3, 151, 'south')
    _bench(p, 4, f+1, 27, color='red')
    _bench(p, 4, f+1, 28, color='red')
    _drawer(p, -2, f+1, 30, 'south')
    _book(p, -2, f+2, 30, 4, 176, 'south')
    _put(p, -1, f+1, 22, 'minecraft:lectern', facing='east', has_book=False, powered=False)
    for x in (0, 1):
        for z in (23, 24):
            _put(p, x, f+1, z, 'minecraft:red_carpet')


def mercy_relief_cabin(p):
    """Blue relief-planning saloon with linen cabinets and a long after settee."""
    f = p.spec.weather
    for z in (25, 26, 27):
        _cupboard(p, -8, f+1, z)
    for x in (4, 5, 6):
        for z in (26, 27):
            _table(p, x, f+1, z)
    _book(p, 4, f+2, 26, 4, 193, 'west')
    _book(p, 5, f+2, 27, 3, 211, 'west')
    _put(p, 6, f+2, 26, 'handcrafted:blue_plate', facing='west', pieces=2, waterlogged=False)
    _put(p, 6, f+2, 27, 'handcrafted:terracotta_thin_pot')
    _put(p, 5, f+2, 31, 'handcrafted:blue_cup', facing='west', pieces=3, waterlogged=False)
    for z in (28, 30, 31):
        _drawer(p, -6, f+1, z, variant=1)
    _put(p, -6, f+2, 28, 'chipped:bundled_white_wool')
    _put(p, -6, f+2, 30, 'handcrafted:terracotta_wide_pot')
    _book(p, -6, f+2, 31, 2, 231)
    for z in (33, 34, 35):
        _bench(p, 5, f+1, z, color='blue')
    _put(p, 4, f+1, 36, 'handcrafted:dark_oak_nightstand', facing='west', color='blue', waterlogged=False)
    _put(p, 4, f+2, 36, 'minecraft:lantern', hanging=False, waterlogged=False)
    _book(p, -3, f+2, 37, 4, 249, 'south')
    _drawer(p, -3, f+1, 41, 'south')
    _put(p, -3, f+2, 41, 'handcrafted:terracotta_thin_pot')
    for x in (-2, -1, 0):
        for z in (25, 26, 27, 28):
            _put(p, x, f+1, z, 'minecraft:blue_carpet')


def officers_and_personal_gear(p):
    s = p.spec
    f, aft = s.decks[1], s.aft-15
    _drawer(p, -5, f+1, aft+4)
    _book(p, -5, f+2, aft+4, 2, 47)
    _put(p, 4, f+1, aft+4, 'handcrafted:dark_oak_nightstand', facing='west', color=s.accent, waterlogged=False)
    _put(p, 4, f+2, aft+4, 'handcrafted:terracotta_thin_pot')
    _book(p, -2, f+2, aft+3, 3, 68, 'south')
    _put(p, -2, f+2, aft+4, 'handcrafted:blue_plate', facing='south', pieces=2, waterlogged=False)
    _drawer(p, -4, f+1, aft+7)
    _book(p, -4, f+2, aft+7, 4, 89)
    # Each watch gets bedside objects, away from the continuous central lane.
    x = -4 if s.key == 'resolute-wren' else -5
    for index, z in enumerate(s.berth_stations):
        _drawer(p, x, f+1, z, variant=1+(index % 3))
        if index % 2:
            _put(p, x, f+2, z, 'handcrafted:blue_cup', facing='east', pieces=1, waterlogged=False)
        else:
            _book(p, x, f+2, z, 1+index % 3, 101+index*13)
    if s.cargo == 'relief':
        _drawer(p, -5, f+1, 20)
        _put(p, -5, f+2, 20, 'chipped:bundled_white_wool')
        _table(p, -3, f+1, 20)
        _put(p, -3, f+2, 20, 'handcrafted:terracotta_wide_pot')
        _book(p, -3, f+2, 18, 2, 223)


def hold_workshops_and_cargo(p):
    s = p.spec
    f, fz = s.decks[0], s.fore+19
    if s.cargo in ('grain', 'relief'):
        cargo = 'minecraft:hay_block' if s.cargo == 'grain' else 'chipped:spruce_crate'
        props = {'axis': 'y'} if s.cargo == 'grain' else {'facing': 'up', 'open': False}
        # Terrace the existing piles; do not alter a single original cargo cell.
        original = dict(p.blocks)
        for (x, y, z), state in sorted(original.items()):
            if y != f+1 or identifier(state) != cargo or x not in (-5, -4):
                continue
            if original.get((x, f+2, z)) == AIR:
                _put(p, x, f+2, z, cargo, **props)
            if x == -5 and z % 2 == 0 and original.get((x, f+3, z)) == AIR:
                _put(p, x, f+3, z, cargo, **props)
    else:
        for z in range(s.fore+24, s.aft-22, 8):
            if identifier(p.blocks.get((-3, f+1, z), '')) != 'minecraft:cartography_table':
                continue  # The after bay is occupied by the original companionway.
            _book(p, -3, f+2, z, 4, 140+z, 'east')
            _drawer(p, -5, f+2, z, variant=1)
            _book(p, -5, f+3, z, 2, 170+z)
    # Folded canvas and spar rack accompany the original stocked repair chest.
    rack_y = f+1
    for z in (fz-2, fz-1, fz, fz+1):
        _put(p, 4, rack_y, z, 'minecraft:stripped_spruce_log', axis='z')
    _put(p, 4, rack_y+1, fz-2, 'minecraft:stripped_spruce_log', axis='z')
    _put(p, 4, rack_y+1, fz-1, 'minecraft:stripped_spruce_log', axis='z')
    for z in (fz+1, fz+2):
        _put(p, -4, f+1, z, 'chipped:bundled_white_wool')
    _put(p, -4, f+2, fz+1, 'chipped:bundled_white_wool')
    _put(p, -5, f+2 if s.cargo == 'dispatch' else f+1, fz+2,
         'supplementaries:sack', open=False, waterlogged=False)


def existing_model(registry, key):
    """Reconstruct the exact already-placed source, without a new placement."""
    if key in SPECS:
        p = FleetShip(registry, SPECS[key])
        for operation in (hull, raised_decks, magazine_and_stores, berthing,
                          galley_and_guns, captain, working_deck, companionways, rig):
            operation(p)
        return p
    if key not in POSES:
        raise UserError('Furnishing correction is limited to the six placed vessels')
    from tools import grand_harbor_smallcraft as small
    p = small.SmallCraft(registry, small.SPECS[key])
    for operation in (small.hull, small.boarding, small.cabin, small.equipment, small.rig):
        operation(p)
    return p


def decorate(registry, key):
    """Return an enriched source model plus its finite, additive-only delta."""
    p = existing_model(registry, key)
    before, old_tags = dict(p.blocks), deepcopy(p.tags)
    rooms = deepcopy(p.rooms)
    groups = []
    if key in SPECS:
        cabins = {'golden-petrel': petrel_counting_cabin,
                  'resolute-wren': wren_dispatch_cabin,
                  'mercy-of-the-tide': mercy_relief_cabin}
        groups.append(_group(p, 'Distinct captain and working saloon',
                             {'golden-petrel': 'Merchant ledgers, cargo accounts, green sitting area and sea cabinets',
                              'resolute-wren': 'Compact red dispatch office, packet desks and stern reading bench',
                              'mercy-of-the-tide': 'Blue relief-planning table, linen cabinets and larger after settee'}[key],
                             lambda: cabins[key](p)))
        groups.append(_group(p, 'Wardroom, officers and watch belongings',
                             'Individual storage, table settings and books beside the existing berths',
                             lambda: officers_and_personal_gear(p)))
        groups.append(_group(p, 'Cargo terraces and sailmaker workshop',
                             'Role-specific stowage, folded canvas and layered spare spars; central passage retained',
                             lambda: hold_workshops_and_cargo(p)))
        from tools.grand_harbor_deck_furnishings import decorate as deck_details
        deck = deck_details(p)
        groups.extend(deck if isinstance(deck, list) else
                      [{'name': value, 'purpose': value} for value in deck['visual_groups']])
        checks = {'circulation': circulation(p), 'lower_hull_seal': hull_seal(p),
                  'cargo_derrick': derrick_source_check(p),
                  'materials': require_material_rule(p.blocks, p.spec.name+' furnished vessel')}
    else:
        from tools.grand_harbor_smallcraft_furnishings import decorate as small_details
        small = small_details(p)
        groups.extend([{'name': value, 'purpose': value} for value in small['visual_groups']])
        from tools.grand_harbor_smallcraft import circulation as small_circulation, lower_hull_check
        checks = {'circulation': small_circulation(p), 'lower_hull_seal': lower_hull_check(p)}
    delta = {pos: state for pos, state in p.blocks.items() if state != before.get(pos)}
    if not 0 < len(delta) <= MAX_ADDITIONS_PER_SHIP:
        raise UserError('Furnishing delta is empty or exceeds its finite limit')
    if any(before.get(pos) != AIR or state == AIR for pos, state in delta.items()):
        raise UserError('Furnishing correction attempted to overwrite cargo, hull, or unknown space')
    if set(before) != set(p.blocks):
        raise UserError('Furnishing correction must retain the original explicit design footprint')
    if any(p.blocks.get(pos) != state for pos, state in before.items() if state != AIR):
        raise UserError('An original non-AIR block was removed or changed')
    if any(p.tags.get(pos) != nbt for pos, nbt in old_tags.items()):
        raise UserError('An original inventory tag was removed or changed')
    if p.rooms != rooms or p.commands:
        raise UserError('Detail pass must retain room anchors and issue no commands')
    if set(delta) & p.hatch_clearance:
        raise UserError('Detail pass entered a reserved hatch/companionway clearance')
    if any(identifier(state).startswith('createbigcannons:') or identifier(state) in {
            'minecraft:tnt', 'minecraft:fire', 'minecraft:lava', 'minecraft:water'}
           for state in delta.values()):
        raise UserError('Furnishing correction must not add a weapon, fluid or firing mechanism')
    # Every recipe uses standing furniture, supported table objects or cargo.
    # No extra free-floating ornament is admitted by an implied-air fallback.
    unsupported = [pos for pos in delta if p.blocks.get((pos[0], pos[1]-1, pos[2]), AIR) == AIR]
    if unsupported:
        raise UserError('A new furnishing lacks its standing support: '+str(unsupported[:6]))
    new_tags = {pos: nbt for pos, nbt in p.tags.items() if pos not in old_tags}
    if set(new_tags)-set(delta):
        raise UserError('New tags must belong only to newly added fixtures')
    return p, {'format': 'awft-fleet-furnishing-delta:1', 'key': key,
               'origin': list(POSES[key][0]), 'rotation': POSES[key][1],
               'groups': groups, 'delta': delta, 'new_tags': new_tags,
               'before_design': before, 'original_tags': old_tags, 'checks': checks,
               'mercy_dryness_dependency': key == 'mercy-of-the-tide',
               'native_deployment': 'NOT RUN', 'visual_owner_acceptance': 'NOT ACCEPTED'}


def packets(registry, key):
    """Existing native BEFORE / delta / normal settle / AFTER, all unadmitted.

    Expected preimages come from the placed source, not a new saved-world claim.
    The master must obtain genuine current native BEFORE/support receipts and
    admit only these new cells. No existing inventory NBT is replayed.
    """
    from tools.grand_harbor_berth import rotate_point, rotated_state
    from tools.grand_harbor_remaining_berths import native_plan, CHECKPOINT_SHA
    p, detail = decorate(registry, key)
    old, delta = detail['before_design'], detail['delta']
    margin = set(delta)
    for x, y, z in delta:
        margin.update((x+dx, y+dy, z+dz) for dx, dy, dz in
                      ((-1, 0, 0), (1, 0, 0), (0, -1, 0), (0, 1, 0), (0, 0, -1), (0, 0, 1)))
    margin.update(p.hatch_clearance)
    for room in p.rooms:
        x, y, z = room['local_anchor']
        margin.update((x, y+n, z) for n in (0, 1, 2))
    # Existing fixtures are read-only retention observations, never PLACE tags.
    margin.update(detail['original_tags'])
    local_before = {pos: old[pos] for pos in margin if pos in old}
    origin, rotation = POSES[key]

    def world(field):
        return {rotate_point(pos, origin, rotation): rotated_state(state, registry, rotation)
                for pos, state in field.items()}

    before, change = world(local_before), world(delta)
    tags = [{'pos': list(rotate_point(pos, origin, rotation)), 'nbt': nbt}
            for pos, nbt in sorted(detail['new_tags'].items())]
    prefix = p.spec.name+' furnishings '
    files = {
        'before-VERIFY-ONLY.json': native_plan(registry, before, prefix+'SOURCE EXPECTED current BEFORE'),
        'retained-supports-VERIFY-ONLY.json': native_plan(registry, {pos: value for pos, value in before.items() if pos not in change},
                                                       prefix+'retained supports and passages'),
        'delta-PROPOSED-NOT-ADMITTED.json': native_plan(registry, change, prefix+'ADDITIVE ONLY NOT ADMITTED', tags=tags),
        'normal-joins-SETTLE-ONLY.json': native_plan(registry, before | change, prefix+'normal neighbor reconciliation'),
        'complete-after-VERIFY-ONLY.json': native_plan(registry, before | change, prefix+'complete target and retained-margin AFTER', tags=tags),
    }
    for name, document in files.items():
        document['validation'] = 'SOURCE EXPECTATIONS ONLY; current native BEFORE, palette, support and entity admission required'
        document['mercy_dryness_dependency'] = detail['mercy_dryness_dependency']
        if name == 'normal-joins-SETTLE-ONLY.json':
            document['normal_neighbor_updates_only'] = True
    local = {'format': detail['format'], 'key': key, 'origin': list(origin), 'rotation': rotation,
             'groups': detail['groups'], 'checks': detail['checks'],
             'delta': [{'pos': list(pos), 'state': state} for pos, state in sorted(delta.items())],
             'new_block_entities': [{'pos': list(pos), 'nbt': nbt} for pos, nbt in sorted(detail['new_tags'].items())],
             'retained_original_explicit_tags': [list(pos) for pos in sorted(detail['original_tags'])],
             'source_non_AIR_and_original_tags_unchanged': True,
             'mercy_dryness_dependency': detail['mercy_dryness_dependency'],
             'canonical_native_backup_binding': CHECKPOINT_SHA,
             'saved_current_preimages': 'NOT CLAIMED; no all-six checkpoint supplied',
             'native_deployment': 'NOT RUN', 'visual_owner_acceptance': 'NOT ACCEPTED',
             'world_writes': 0, 'commands': [], 'entities': []}
    files['source-detail.json'] = local
    return files


def export(registry_path, output):
    """Write one bounded source packet for each already-placed vessel."""
    from tools.playtest import guard
    registry_path, output = Path(registry_path), Path(output)
    if not registry_path.is_file() or registry_path.stat().st_size > 8*1024**2:
        raise UserError('A finite native registry file is required')
    if output.exists():
        raise UserError('Choose a new immutable furnishing packet directory')
    registry = json.loads(registry_path.read_bytes())
    files, ships = {}, {}
    for key in POSES:
        documents = packets(registry, key)
        files.update({key+'/'+name: canonical(document) for name, document in documents.items()})
        detail = documents['source-detail.json']
        ships[key] = {'origin': detail['origin'], 'rotation': detail['rotation'],
                      'new_cells': len(detail['delta']), 'new_explicit_tags': len(detail['new_block_entities']),
                      'retained_original_explicit_tags': len(detail['retained_original_explicit_tags']),
                      'groups': [group['name'] for group in detail['groups']],
                      'mercy_dryness_dependency': detail['mercy_dryness_dependency']}
    sources = ('grand_harbor_furnishings.py', 'grand_harbor_deck_furnishings.py',
               'grand_harbor_smallcraft_furnishings.py', 'grand_harbor_fleet.py',
               'grand_harbor_smallcraft.py', 'grand_harbor_remaining_berths.py',
               'grand_harbor_berth.py', 'artistic_ship.py')
    manifest = {'format': 'awft-fleet-furnishing-packet:1', 'ships': ships,
                'sources': {name: sha(Path(__file__).with_name(name).read_bytes()) for name in sources},
                'registry_sha256': sha(registry_path.read_bytes()),
                'files': {name: {'bytes': len(raw), 'sha256': sha(raw)} for name, raw in files.items()},
                'admission': ['Preserve failed Mercy receipts; verify shell and dry interior separately before its detail pass',
                              'Master exclusive empty-world lease and exact current runtime identity',
                              'Genuine current native BEFORE, retained supports, new palette, BE and entity-body checks',
                              'Admit only delta; preserve original containers, inventories, hull and rig',
                              'Normal settle once, complete AFTER including new stock, actual Minecraft views and walkthrough'],
                'world_writes': 0, 'hull_replay': False, 'official_permanent_deployment': False,
                'source_readiness': 'FIVE READY FOR CURRENT NATIVE ADMISSION; MERCY HELD UNTIL HULL AND DRYNESS VERIFICATION',
                'native_deployment': 'NOT RUN', 'visual_owner_acceptance': 'NOT ACCEPTED'}
    files['manifest.json'] = canonical(manifest)
    total = sum(len(raw) for raw in files.values())
    limit = 8*1024**2
    if total > limit:
        raise UserError('Furnishing packet exceeds bounded 8 MiB allocation')
    drive = output.resolve().drive.upper()
    if drive not in ('C:', 'D:'):
        raise UserError('Measure a C: or D: destination before export')
    guard(limit if drive == 'C:' else 0, limit if drive == 'D:' else 0)
    output.mkdir(parents=True, exist_ok=False)
    for name, raw in files.items():
        path = output/name
        path.parent.mkdir(exist_ok=True)
        with path.open('xb') as stream:
            stream.write(raw)
    return {'directory': str(output.resolve()), 'bytes': total,
            'manifest_sha256': sha(files['manifest.json']), 'ships': ships, 'world_writes': 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--registry', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(export(args.registry, args.output), indent=2))
    except (UserError, OSError, ValueError) as exc:
        parser.exit(2, str(exc)+'\n')


if __name__ == '__main__':
    main()
