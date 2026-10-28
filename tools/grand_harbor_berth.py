"""One exact saved306 Wren berth/batch for master integration, no world actions."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
from pathlib import Path
import re

from control_room.common import UserError, digest, read_json
from tools.artistic_ship import ArtisticShip
from tools.grand_harbor_fleet import AIR, build, canonical, capture_recipe, identifier
from tools.playtest import guard
from tools.settlement_attractions import BackupWorld


CHECKPOINT = '20261028T180051Z-30624d'
CHECKPOINT_SHA = '3cb269d28ae1ccbac882a44d35277d82c83582274abad2f1cf3b41566d3e9b24'
FLEET_COMMIT = 'cec9f378f17f8a7a58c265cafe124a7dbceae623'
HOME = Path(r'D:\A World for Two\staging\world-tests\20261027T053650Z-artistic')
ORIGIN, ROTATION, KEY = (1000, 63, -1366), 1, 'resolute-wren'
MAX_OUTPUT, MAX_SOURCE_BYTES = 32*1024**2, 64*1024**2
WATER = 'minecraft:water[level=0]'
AIR_STATES = {AIR, 'minecraft:cave_air', 'minecraft:void_air'}


def checked_checkpoint(receipt, checkpoint_id=CHECKPOINT, checkpoint_sha=CHECKPOINT_SHA):
    if (checkpoint_id != CHECKPOINT or checkpoint_sha != CHECKPOINT_SHA or
            receipt.get('verified') is not True or receipt.get('id') != CHECKPOINT or
            receipt.get('sha256') != CHECKPOINT_SHA):
        raise UserError('Exact current verified306 checkpoint required; no stale binding')


def rotate_point(point, origin, rotation):
    x, y, z = point
    for _ in range(rotation):
        x, z = -z, x
    return origin[0]+x, origin[1]+y, origin[2]+z


def rotated_state(state, registry, rotation):
    key = identifier(state)
    props = dict(part.split('=') for part in state.split('[', 1)[1][:-1].split(',')) if '[' in state else {}
    # Existing strict helper handles facing/axis, directional rope keys and
    # sixteen-way signs. Five-way globe rotation remains its own native enum.
    return ArtisticShip(registry, (0, 0, 0), rotation).state(key, **props)


def translated(document, registry, origin, rotation):
    if (len(origin) != 3 or any(type(v) is not int for v in origin) or origin[1] != 63 or
            type(rotation) is not int or rotation not in range(4) or
            document.get('key') != KEY or document.get('format') != 'awft-fleet-template:1'):
        raise UserError('One Wren template, integer seaY63 and quarter-turn rotation required')
    palette = [rotated_state(s, registry, rotation) for s in document['palette']]
    field = {rotate_point(row[:3], origin, rotation): palette[row[3]] for row in document['blocks']}
    if not 0 < len(field) <= 40_000 or len(field) != len(document['blocks']):
        raise UserError('Finite unique Wren target field required')
    tags = [{'pos': list(rotate_point(row['pos'], origin, rotation)), 'nbt': row['nbt']}
            for row in document['block_entities']]
    return field, tags


def bounds(field):
    return [min(p[i] for p in field) for i in range(3)]+[max(p[i] for p in field) for i in range(3)]


def native_plan(registry, field, name, *, tags=(), verify=True):
    palette = sorted(set(field.values()))
    indices, box = {s: i for i, s in enumerate(palette)}, bounds(field)
    return {'format': 'awft-native-settlement:1', 'name': name,
            'seed': registry['seed'], 'world_path': registry['world_path'],
            'backup_sha256': CHECKPOINT_SHA, 'bounds': [box[0], box[2], box[3], box[5]],
            'palette': palette, 'blocks': [[*p, indices[s]] for p, s in sorted(field.items())],
            'block_entities': list(tags), 'commands': [], 'landmarks': [],
            'verification_only': verify, 'construction_forbidden': verify,
            'validation': 'Master only. Fresh native before/support/entity admission required; saved checks grant no write authority.'}


def probe_cells(document):
    """Two source-water cells below each submerged column, plus load/boat space."""
    bottom = {}
    for x, y, z, index in document['blocks']:
        if y <= 0 and identifier(document['palette'][index]) not in AIR_STATES:
            bottom[x, z] = min(y, bottom.get((x, z), y))
    water = {(x, y-dy, z) for (x, z), y in bottom.items() for dy in (1, 2)}
    count = len(water)
    fittings = document['design']['fittings']
    derrick = next(f for f in fittings if f['kind'] == 'stopped cargo derrick')
    x1, y1, z1, x2, y2, z2 = derrick['load_sweep_bounds']
    load = {(x, y, z) for x in range(x1, x2+1) for y in range(y1, y2+1) for z in range(z1, z2+1)}
    bx, _, bz = next(f for f in fittings if f['kind'] == 'boarding interface')['local_floor']
    approach = {(x, y, z) for x in range(bx+2, bx+5) for z in range(bz-2, bz+3) for y in range(-2, 4)}
    water.update(pos for pos in approach if pos[1] < 0)
    air = load | {pos for pos in approach if pos[1] >= 0}
    return water, air, {'under_keel_water_cells': count, 'two_block_under_keel_margin': True,
                        'local_load_bounds': list(derrick['load_sweep_bounds']),
                        'local_boarding_approach_bounds': bounds(approach)}


def inspect_candidate(document, registry, snapshot, origin, rotation, protected=()):
    field, tags = translated(document, registry, origin, rotation)
    protected = set(protected)
    water, air, detail = probe_cells(document)
    required = {rotate_point(p, origin, rotation): WATER for p in water}
    required.update({rotate_point(p, origin, rotation): AIR for p in air})
    bad = [p for p in set(field) & set(required) if identifier(field[p]) not in AIR_STATES]
    if bad:
        raise UserError('Structure enters its load/boarding/under-keel probe: '+str(bad[:3]))
    before = {}
    for pos in sorted(set(field) | set(required)):
        if pos in protected:
            raise UserError('Exact protected source mask intersects candidate: '+str(pos))
        try:
            state = snapshot.state(pos)
        except UserError as exc:
            raise UserError('Unknown/unavailable saved target remains unqualified: '+str(pos)+' '+str(exc)) from exc
        if state is None:
            raise UserError('Unknown saved target is never AIR: '+str(pos))
        if pos in snapshot.protected:
            raise UserError('Saved block entity must be preserved: '+str(pos))
        if state not in AIR_STATES | {WATER}:
            raise UserError('Occupied/natural non-source-water target must be preserved: '+str((pos, state)))
        if pos in required and state != required[pos]:
            raise UserError('Exact water/air support probe differs: '+str((pos, state, required[pos])))
        before[pos] = state
    detail.update(world_under_keel_and_load_bounds=bounds(required), world_authored_bounds=bounds(field),
                  authored_positions=len(field), authored_AIR_positions=sum(identifier(s) in AIR_STATES for s in field.values()),
                  total_preimage_cells=len(before), saved_state_histogram=dict(Counter(before.values())),
                  saved_block_entities=0, exact_protected_mask_overlaps=0)
    return field, tags, before, required, detail


def protections(home, registry):
    """Pinned town/quay/hull/bridge and exact flight masks, including their AIR."""
    from tools.artistic_maritime_depth import BASES
    from tools.artistic_north_rebuild_custody import BATCHES
    from tools.artistic_whole_bank_forest import INDEX, INDEX_SHA
    from tools.artistic_zipline_west import FUTURE_BRIDGE, FUTURE_BRIDGE_SHA
    paths = [(name, home/rel, pin) for name, (rel, pin) in BASES.items()]
    paths += [(name, home/rel/source, pin) for name, rel, source, pin, *_ in BATCHES]
    index_path = home/INDEX
    if digest(index_path) != INDEX_SHA:
        raise UserError('Protected architecture index changed')
    paths += [(row['name'], Path(row['path']), row['sha256']) for row in read_json(index_path)['plans']]
    paths += [('Future bridge exact sweep/walk', home/FUTURE_BRIDGE, FUTURE_BRIDGE_SHA),
              ('Western zipline full flight/station mask',
               home/'staging/zipline-west-v2-source-1793152099836099800/all-v2-RESERVATION-ONLY.json',
               '92ea594836795a61e00f5cc32290d49d1d47b9fd6eb55aeefc99d527acf8854d')]
    protected, records, allocated = set(), [], 0
    for name, path, pin in paths:
        if not path.is_file() or not 0 < path.stat().st_size <= 16*1024**2 or digest(path) != pin:
            raise UserError('Exact protected source unavailable/changed: '+name)
        allocated += path.stat().st_size
        if allocated > MAX_SOURCE_BYTES:
            raise UserError('Protected source read allocation exceeded')
        doc = read_json(path)
        doc = doc.get('physical_plan', doc)
        if doc.get('world_path') != registry['world_path'] or str(doc.get('seed')) != str(registry['seed']):
            raise UserError('Protected source belongs to another world: '+name)
        positions = {tuple(row[:3]) for row in doc['blocks']}
        positions.update(tuple(row['pos']) for row in doc.get('block_entities', []))
        protected.update(positions)
        records.append({'name': name, 'path': str(path), 'sha256': pin, 'positions': len(positions),
                        'bounds': bounds(positions), 'AIR_and_BE_masks_retained': True})
    return protected, records


def nearby_quay(snapshot, landing, authored, radius=24):
    """Bounded actual floor search, without treating ice or bare terrain as a quay."""
    x, y, z = landing
    found, states = [], Counter()
    for xx in range(x-radius, x+radius+1):
        for zz in range(z-radius, z+radius+1):
            if (xx-x)**2+(zz-z)**2 > radius**2:
                continue
            for yy in range(62, 68):
                pos = xx, yy, zz
                old = snapshot.state(pos)
                states[identifier(old)] += 1
                material = identifier(old)
                floor = (material in {'minecraft:stone', 'minecraft:stone_bricks', 'minecraft:andesite',
                                      'minecraft:cobblestone', 'minecraft:smooth_stone'} or
                         material.endswith(('_planks', '_log', '_wood', '_stairs')) or
                         material.endswith('_slab') and 'type=double' in old)
                if pos not in authored or pos in snapshot.protected or not floor:
                    continue
                if all(snapshot.state((xx, yy+dy, zz)) in AIR_STATES for dy in (1, 2)):
                    found.append((abs(xx-x)+abs(zz-z)+abs(yy-y), pos, old))
    found.sort()
    return {'radius_blocks': radius, 'floor_Y_range': [62, 67], 'landing': list(landing),
            'observed_saved_blocks': dict(states),
            'nearest_authored_clear_floor': {'distance_manhattan': found[0][0], 'pos': list(found[0][1]), 'state': found[0][2]} if found else None,
            'already_docked': False,
            'interface_proposal': 'Master must select a surveyed shore/finger-pier endpoint and approve a separate short gangway to this ship landing. This package authors no quay/pier or connecting gangway.'}


def camera_batch(document, origin=ORIGIN, rotation=ROTATION):
    views = capture_recipe(document)
    local = [dict(row, original_label=row['name']) for row in views['local_views']
             if row['name'] in {'bow', 'stern', 'broadside', 'elevated', 'deck'}]
    for room in document['rooms']:
        x, y, z = room['local_anchor']
        local.append({'name': room['name'], 'original_label': room['name'],
                      'feet': [x+.5, y+1, z+.5], 'look_at': [x-3, y+2, z+6]})
    fittings = document['design']['fittings']
    derrick = next(f for f in fittings if f['kind'] == 'stopped cargo derrick')
    cx, cy, cz = derrick['local_control']
    local.append({'name': 'shipboard derrick', 'original_label': 'Shipboard cargo derrick and operator approach',
                  'feet': [cx+4, cy+1, cz+3], 'look_at': derrick['pulley']})
    bx, by, bz = next(f for f in fittings if f['kind'] == 'boarding interface')['local_floor']
    local.append({'name': 'boarding and skiff approach', 'original_label': 'Boarding stair, return ladder and skiff approach',
                  'feet': [bx+5, by+4, bz+5], 'look_at': [bx+.5, by+1, bz+.5]})
    used = set()
    for row in local:
        slug = re.sub('[^a-z0-9]+', '-', row['name'].lower().replace("'", '')).strip('-')
        if not slug or slug in used or len(slug) > 44:
            raise UserError('Unique short lower-case capture slugs required')
        used.add(slug)
        row['name'] = slug
    views.update(local_views=local,
                 world_views=[{'name': row['name'], 'original_label': row['original_label'],
                               'feet': list(rotate_point(row['feet'], origin, rotation)),
                               'look_at': list(rotate_point(row['look_at'], origin, rotation))}
                              for row in local], origin=list(origin), rotation=rotation,
                 maximum_unique_prefix_characters=58-max(map(len, used))-1,
                 actual_capture='Master only; use a new short lower-case hyphen prefix. Combined prefix-name <=58characters.')
    return views


def prepare(home=HOME, output=None, *, expected_fleet_sha256=None):
    home = Path(home).resolve()
    if home != HOME.resolve():
        raise UserError('This single sprint berth binds only the existing construction home')
    source = Path(__file__).with_name('grand_harbor_fleet.py')
    if not re.fullmatch('[a-f0-9]{64}', str(expected_fleet_sha256)) or digest(source) != expected_fleet_sha256:
        raise UserError('Exact final parent-approved fleet source SHA256 required')
    receipt = read_json(home/'dashboard/settlement/backup-receipt.json', {})
    checked_checkpoint(receipt)
    registry_path = home/'dashboard/settlement/registry.json'
    registry_sha = digest(registry_path)
    registry = read_json(registry_path)
    if Path(registry['world_path']).resolve() != home/'world/RosewaterArtistic':
        raise UserError('Current construction save identity differs')
    doc = build(registry, KEY)
    protected, protected_sources = protections(home, registry)
    snapshot = BackupWorld(home, receipt, registry)
    try:
        field, tags, before, probe, detail = inspect_candidate(doc, registry, snapshot, ORIGIN, ROTATION, protected)
        landing = next(f for f in doc['design']['fittings'] if f['kind'] == 'boarding interface')['local_floor']
        quay = nearby_quay(snapshot, rotate_point(landing, ORIGIN, ROTATION), protected)
        sources = snapshot.sources[:]
    finally:
        snapshot.close()
    if digest(source) != expected_fleet_sha256 or digest(registry_path) != registry_sha:
        raise UserError('Fleet source changed during binding; preserve inputs and requalify')
    checked_checkpoint(read_json(home/'dashboard/settlement/backup-receipt.json', {}))
    placing = native_plan(registry, field, 'Resolute Wren one-hull placement', tags=tags, verify=False)
    old = native_plan(registry, before, 'Resolute Wren exact306 current-before VERIFY ONLY')
    support = native_plan(registry, probe, 'Resolute Wren under-keel/load/boarding VERIFY ONLY')
    after = native_plan(registry, {**before, **field}, 'Resolute Wren complete after VERIFY ONLY', tags=tags)
    views = camera_batch(doc)
    files = {'placement.json': canonical(placing), 'current-before-VERIFY-ONLY.json': canonical(old),
             'under-keel-load-VERIFY-ONLY.json': canonical(support),
             'complete-after-VERIFY-ONLY.json': canonical(after), 'camera-recipe.json': canonical(views)}
    identity = hashlib.sha256(canonical({'template': doc, 'origin': ORIGIN, 'rotation': ROTATION,
                                         'checkpoint_sha256': CHECKPOINT_SHA})).hexdigest()
    output = Path(output).resolve() if output else home/'staging'/('fleet-berth-wren-'+identity[:16])
    if not output.is_relative_to(home/'staging') or not output.name.startswith('fleet-berth-') or output.exists():
        raise UserError('A unique owned fleet-berth staging output is required')
    manifest = {'format': 'awft-one-fleet-berth:1', 'vessel': KEY, 'origin': list(ORIGIN), 'rotation': ROTATION,
                'source_sha256': digest(Path(__file__)), 'fleet_source_sha256': expected_fleet_sha256,
                'fleet_geometry_commit': FLEET_COMMIT,
                'smallcraft_source_sha256': digest(Path(__file__).with_name('grand_harbor_smallcraft.py')),
                'strict_native_helpers_sha256': {'artistic_ship.py': digest(Path(__file__).with_name('artistic_ship.py')),
                                                 'settlement.py': digest(Path(__file__).with_name('settlement.py'))},
                'template_sha256': hashlib.sha256(canonical(doc)).hexdigest(), 'registry_sha256': registry_sha,
                'checkpoint_id': CHECKPOINT, 'checkpoint_sha256': CHECKPOINT_SHA,
                'saved_admission': detail, 'nearby_quay': quay, 'protected_sources': protected_sources,
                'saved_region_sources': sources,
                'preserved_historical_reference_conflict': {'origin': [1000, 63, -1350], 'rotation': 1,
                                                          'pos': [1012, 62, -1343], 'state': 'minecraft:ice',
                                                          'resolution': 'Separate16-block seaward candidate; no ice clearing'},
                'files': {name: {'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)} for name, raw in files.items()},
                'native_actions': 0, 'world_writes': 0, 'entities_created': 0,
                'status': 'SAVED SOURCE CANDIDATE ONLY; master current native reverify and deployment required',
                'integration': ['Keep master lease and player exclusion current',
                                'Native VERIFY exact current-before and under-keel/load plans',
                                'Query current entity AABBs for hull/rig/boarding/load; saved block checks do not census entities',
                                'Master places exact hashed placement.json only after all admissions pass',
                                'Settle and native VERIFY complete-after, including inventories and all authored states',
                                'Actual cameras/walking/cannon/hoist tests, controlled restart and two-player review remain required'],
                'quay_change': 'NONE. Ship-owned landing only; candidate is not connected to a current quay.',
                'runtime_visual_multiplayer_restart_performance': 'UNVERIFIED',
                'monitoring': 'Separate-drive30GiB guard is monitoring, not an OS quota or limit on external writers'}
    files['manifest.json'] = canonical(manifest)
    if sum(len(raw) for raw in files.values()) > MAX_OUTPUT:
        raise UserError('Combined one-hull batch exceeds32MiB allocation')
    guard(0, MAX_OUTPUT)
    output.mkdir(parents=True, exist_ok=False)
    for name, raw in files.items():
        with (output/name).open('xb') as stream:
            stream.write(raw)
    return {'directory': str(output), 'manifest_sha256': digest(output/'manifest.json'),
            'origin': list(ORIGIN), 'rotation': ROTATION, 'saved_admission': detail,
            'nearby_quay': quay, 'world_writes': 0}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--home', type=Path, default=HOME)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--fleet-source-sha256', required=True)
    args = parser.parse_args()
    import json
    print(json.dumps(prepare(args.home, args.output, expected_fleet_sha256=args.fleet_source_sha256)))
