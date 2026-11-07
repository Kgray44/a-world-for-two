"""Saved6ad3a8-only study for three original static small vessels; no native calls.

Candidates are a short deliberate list derived from saved river/mouth sections.
No missing chunk, marine plant, ice, structure or inventory is replaced. Passing
saved checks does not authorize deployment or supply a current native registry.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
from pathlib import Path
import re

from control_room.common import UserError, digest, read_json
from tools.grand_harbor_fleet import AIR, canonical, capture_recipe, identifier
from tools.grand_harbor_smallcraft import SMALLCRAFT_ORDER, build as build_small
from tools.grand_harbor_berth import (
    HOME, AIR_STATES, WATER, bounds, native_plan as _native_plan,
    protections, probe_cells as major_probe_cells, rotate_point, rotated_state,
)
from tools.playtest import guard
from tools.settlement_attractions import BackupWorld


FLEET_SHA = 'fe4251af7c032257e15f90a428defb5c523bb51fea8bd09a37db43066958119a'
SMALL_SHA = '26b3ccb68473a185df827a6e0f2d3c583b6386ca836788c8bf978422976bd362'
REGISTRY_SHA = '8cfa5ae77e20b8b5c1730b2928c55156557ebecb7e84480142088bda04ef92c4'
BERTH_HELPER_SHA = 'f61f45913a9d60846bdd6a9d04e6f4a049cfdd0129f1a3d6fc2fec4612cc7984'
WREN_DIR = 'staging/fleet-berth-wren-9d0b486aae22282e'
WREN_PINS = {
    'placement.json': '4115e860fc9fd685ec468cf7b2ab5b81837dfdefda22364703c817d64c44b6c3',
    'under-keel-load-VERIFY-ONLY.json': '66cc6a29175c7891a89a8a3e5ed48a20e96cd3edf8ed67cc95ff11854b1df5ce',
}
MAX_OUTPUT = 32*1024**2
CHECKPOINT = '20261028T191243Z-6ad3a8'
CHECKPOINT_SHA = '0ba7ad2097fb52273a37da6a76d8fc030133b79cd26d81b97531d8d74c2546c2'

# At most four deliberately reasoned poses. No generated grid/parameter sweep.
CANDIDATES = {
    'tern-pilot-cutter': (
        ((1168, 63, -1314), 2, 'West mouth water; boarding faces west away from the open center lane'),
        ((1168, 63, -1294), 2, 'Closer western mouth approach if the outer position conflicts with conditional Petrel rig'),
        ((1152, 63, -1292), 2, 'Western mouth pocket outside the native cog departure reserve'),
        ((1168, 63, -1338), 2, 'Outer mouth seaward of the scattered saved ice; exact conditional Petrel masks still govern'),
    ),
    'salt-marigold-ketch': (
        ((1228, 63, -1320), 0, 'Eastern mouth water, north of the spit; boarding faces the eastern waterfront'),
        ((1244, 63, -1320), 0, 'Separate eastern mouth pocket if the first site meets the spit/shallows'),
    ),
    'reed-fin-river-lighter': (
        ((1291, 63, -1092), 3, 'North/east bank side of the actual diagonal river bend, beyond the bridge sweep'),
        ((1288, 63, -1088), 3, 'Inner bend alternative, still north/east of the saved center-channel line'),
        ((1304, 63, -1064), 0, 'East-bank lower bend, boarding toward the bank and outside the castle/mill source masks'),
        ((1274, 63, -1098), 0, 'Western edge of the upper bend, away from the main bridge sweep'),
    ),
}


class SavedAdmissionError(UserError):
    def __init__(self, details):
        self.details = details
        super().__init__('Saved smallcraft berth refused: '+str(details['first_failures'][:3]))


def native_plan(registry, field, name, *, tags=(), verify=True):
    plan = _native_plan(registry, field, name, tags=tags, verify=verify)
    # Own pin is independent of the concurrently requalified Wren module.
    plan['backup_sha256'] = CHECKPOINT_SHA
    return plan


def translated(document, registry, origin, rotation):
    if (document.get('format') != 'awft-fleet-template:1' or document.get('key') not in SMALLCRAFT_ORDER or
            len(origin) != 3 or any(type(v) is not int for v in origin) or origin[1] != 63 or
            type(rotation) is not int or rotation not in range(4)):
        raise UserError('Exact smallcraft template and integer sea63 quarter-turn pose required')
    palette = [rotated_state(state, registry, rotation) for state in document['palette']]
    field = {rotate_point(row[:3], origin, rotation): palette[row[3]] for row in document['blocks']}
    if not 0 < len(field) <= 10_000 or len(field) != len(document['blocks']):
        raise UserError('Bounded unique smallcraft target field required')
    tags = [{'pos': list(rotate_point(row['pos'], origin, rotation)), 'nbt': row['nbt']}
            for row in document['block_entities']]
    return field, tags


def probe_cells(document):
    bottom = {}
    for x, y, z, i in document['blocks']:
        if y <= 0 and identifier(document['palette'][i]) not in AIR_STATES:
            bottom[x, z] = min(y, bottom.get((x, z), y))
    water = {(x, y-down, z) for (x, z), y in bottom.items() for down in (1, 2)}
    count = len(water)
    bx, _, bz = next(f for f in document['design']['fittings'] if f['kind'] == 'boarding interface')['local_floor']
    # The backed return ladder occupies bx+2: keep the craft approach outside it.
    approach = {(x, y, z) for x in range(bx+3, bx+6) for y in range(-2, 4)
                for z in range(bz-2, bz+3)}
    water.update(p for p in approach if p[1] < 0)
    air = {p for p in approach if p[1] >= 0}
    return water, air, {'two_block_under_keel_margin': True, 'under_keel_water_cells': count,
                        'local_boarding_approach_bounds': bounds(approach)}


def inspect_candidate(document, registry, snapshot, origin, rotation, protected=()):
    field, tags = translated(document, registry, origin, rotation)
    water, air, details = probe_cells(document)
    required = {rotate_point(p, origin, rotation): WATER for p in water}
    required.update({rotate_point(p, origin, rotation): AIR for p in air})
    if any(field[p] != required[p] for p in field.keys() & required.keys()):
        raise UserError('Smallcraft enters its own under-keel or boarding probe')
    protected = set(protected)
    before, failures, counts = {}, [], Counter()
    for pos in sorted(field.keys() | required.keys()):
        reason, state = None, None
        if pos in protected:
            reason = 'protected mask or navigation/sweep reservation'
        try:
            state = snapshot.state(pos)
        except UserError as exc:
            reason = 'unknown unavailable saved chunk: '+str(exc)
        if reason is None:
            if state is None:
                reason = 'unknown saved target is never AIR'
            elif pos in snapshot.protected:
                reason = 'saved block entity must be preserved'
            elif state not in AIR_STATES | {WATER}:
                reason = 'occupied/natural/ice/non-source-water target must be preserved'
            elif pos in required and state != required[pos]:
                reason = 'exact water/air support probe differs'
        if reason:
            counts[reason] += 1
            if len(failures) < 64:
                failures.append({'pos': list(pos), 'state': state, 'reason': reason})
        elif state is not None:
            before[pos] = state
    details.update(world_authored_bounds=bounds(field), world_probe_bounds=bounds(required),
                   authored_positions=len(field), complete_mask_positions=len(field.keys() | required.keys()),
                   failures_by_reason=dict(counts), first_failures=failures)
    if counts:
        raise SavedAdmissionError(details)
    details.update(total_preimage_cells=len(before), saved_state_histogram=dict(Counter(before.values())),
                   exact_protected_overlaps=0, saved_block_entities=0)
    return field, tags, before, required, details


def navigation_masks():
    # Conservative navigable center reservations, derived from saved water rows.
    boxes = [(1182, 58, -1344, 1208, 96, -1248),
             (1175, 58, -1186, 1240, 96, -1102)]
    field = {p for x1, y1, z1, x2, y2, z2 in boxes
             for x in range(x1, x2+1) for y in range(y1, y2+1) for z in range(z1, z2+1)
             for p in [(x, y, z)]}
    center = ((1260, -1104), (1262, -1096), (1272, -1088), (1286, -1080), (1290, -1072), (1312, -1064))
    for (ax, az), (bx, bz) in zip(center, center[1:]):
        steps = max(abs(bx-ax), abs(bz-az))
        for n in range(steps+1):
            x, z = round(ax+(bx-ax)*n/steps), round(az+(bz-az)*n/steps)
            field.update((x+dx, y, z+dz) for dx in range(-4, 5) for dz in range(-4, 5) for y in range(59, 83))
    return field, {'mouth_and_bridge_boxes': boxes, 'saved_river_centerline_xz': center,
                   'river_lane_half_width': 4, 'status': 'Conservative SOURCE reservation; actual navigation/collision remains untested'}


def exact_masks(home, registry):
    protected, records = protections(home, registry)
    for name, pin in WREN_PINS.items():
        path = home/WREN_DIR/name
        if digest(path) != pin:
            raise UserError('Frozen master Wren source mask changed')
        doc = read_json(path)
        mask = {tuple(row[:3]) for row in doc['blocks']}
        protected.update(mask)
        records.append({'name': 'Master Wren '+name, 'path': str(path), 'sha256': pin,
                        'positions': len(mask), 'bounds': bounds(mask)})
    # Conditional original-layout majors remain protected even though plants
    # currently refuse their placement. Never consume those possible berths.
    from tools.grand_harbor_fleet import build as build_major
    for key, origin in (('golden-petrel', (1110, 63, -1344)), ('mercy-of-the-tide', (1230, 63, -1376))):
        doc = build_major(registry, key)
        water, air, _ = major_probe_cells(doc)
        mask = {rotate_point(row[:3], origin, 1) for row in doc['blocks']}
        mask.update(rotate_point(p, origin, 1) for p in water | air)
        protected.update(mask)
        records.append({'name': key+' CONDITIONAL original berth', 'origin': list(origin), 'rotation': 1,
                        'template_sha256': hashlib.sha256(canonical(doc)).hexdigest(),
                        'positions': len(mask), 'bounds': bounds(mask), 'placement_approval': False})
    # Preserve the old craft contract's body/departure masks and proposed landing.
    folder = home/'staging/artistic-harbor-craft-7800cfbe7a4a0796'
    manifest = read_json(folder/'manifest.json')
    for name in ('expected-before.json', 'water-air-verify-only.json'):
        path, pin = folder/name, manifest['documents'][name]['sha256']
        if digest(path) != pin:
            raise UserError('Existing cog/tender admission source mask changed')
        doc = read_json(path)
        mask = {tuple(row[:3]) for row in doc['blocks']}
        protected.update(mask)
        records.append({'name': 'Existing cog/tender '+name, 'path': str(path), 'sha256': pin,
                        'positions': len(mask), 'bounds': bounds(mask)})
    lane, lane_record = navigation_masks()
    protected.update(lane)
    records.append(dict(lane_record, name='Source navigation lane reservation', positions=len(lane)))
    return protected, records


def camera_batch(document, origin, rotation):
    recipe = capture_recipe(document)
    for room in document['rooms']:
        x, y, z = room['local_anchor']
        recipe['local_views'].append({'name': room['name'], 'feet': [x+.5, y+1, z+.5], 'look_at': [x-2, y+2, z+4]})
    views, used = [], set()
    for row in recipe['local_views']:
        name = re.sub('[^a-z0-9]+', '-', row['name'].lower()).strip('-')
        if name in used:
            continue
        if not name or len(name) > 43:
            raise UserError('Bounded unique smallcraft camera labels required')
        used.add(name)
        views.append({'name': name, 'feet': list(rotate_point(row['feet'], origin, rotation)),
                      'look_at': list(rotate_point(row['look_at'], origin, rotation))})
    return {'world_views': views, 'origin': list(origin), 'rotation': rotation,
            'actual_capture': 'Master only; new immutable lower-case capture prefix; totalprefix-name<=58',
            'status': 'SOURCE CAMERA RECIPE; no image or client operation'}


def prepare(home=HOME, output=None):
    home = Path(home).resolve()
    if home != HOME.resolve():
        raise UserError('Saved6ad3a8 study binds only the existing construction home')
    for name, pin in (('grand_harbor_fleet.py', FLEET_SHA), ('grand_harbor_smallcraft.py', SMALL_SHA),
                      ('grand_harbor_berth.py', BERTH_HELPER_SHA)):
        if digest(Path(__file__).with_name(name)) != pin:
            raise UserError('Frozen fleet/smallcraft source changed')
    reg_path = home/'staging/fleet-registry-provenance-8cfa5ae7/registry-original.json'
    if digest(reg_path) != REGISTRY_SHA:
        raise UserError('Historical property registry source changed')
    registry = read_json(reg_path)
    snapshot = BackupWorld(home, {'id': CHECKPOINT, 'sha256': CHECKPOINT_SHA, 'verified': True}, registry)
    protected, records = exact_masks(home, registry)
    files, studies, selected, profile = {}, {}, [], []
    try:
        for z in (-1344, -1328, -1312, -1296, -1280):
            profile.append({'row_z': z, 'y': 62, 'samples': [[x, snapshot.state((x, 62, z))] for x in range(1120, 1273, 8)]})
        for z in (-1104, -1096, -1088, -1080, -1072, -1064):
            profile.append({'row_z': z, 'y': 62, 'samples': [[x, snapshot.state((x, 62, z))] for x in range(1224, 1345, 4)]})
        for key in SMALLCRAFT_ORDER:
            doc, attempts = build_small(registry, key), []
            for origin, rotation, why in CANDIDATES[key]:
                attempt = {'origin': list(origin), 'rotation': rotation, 'reasoned_pose': why}
                try:
                    field, tags, before, probe, detail = inspect_candidate(doc, registry, snapshot, origin, rotation, protected)
                except SavedAdmissionError as exc:
                    attempts.append(dict(attempt, status='REFUSED; no placement files', saved_admission=exc.details))
                    continue
                attempts.append(dict(attempt, status='SAVED CANDIDATE ONLY', saved_admission=detail))
                documents = {
                    key+'/current-before-VERIFY-ONLY.json': native_plan(registry, before, key+' saved6ad3a8 BEFORE VERIFY ONLY'),
                    key+'/under-keel-boarding-VERIFY-ONLY.json': native_plan(registry, probe, key+' keel/boarding VERIFY ONLY'),
                    key+'/placement.json': native_plan(registry, field, key+' original static structure', tags=tags, verify=False),
                    key+'/complete-after-VERIFY-ONLY.json': native_plan(registry, {**before, **field}, key+' complete AFTER VERIFY ONLY', tags=tags),
                    key+'/camera-recipe.json': camera_batch(doc, origin, rotation),
                }
                files.update({name: canonical(value) for name, value in documents.items()})
                # Full authored AIR and probe masks exclude later small craft.
                protected.update(before)
                selected.append({'key': key, 'origin': list(origin), 'rotation': rotation,
                                 'world_authored_bounds': bounds(field), 'full_mask_bounds': bounds(before),
                                 'complete_mask_positions': len(before), 'dock_interface': 'UNCONNECTED; ship-owned landing only'})
                break
            studies[key] = attempts
        sources = snapshot.sources[:]
    finally:
        snapshot.close()
    record = {'format': 'awft-smallcraft-saved-berths:1', 'checkpoint_id': CHECKPOINT,
              'checkpoint_sha256': CHECKPOINT_SHA, 'fleet_source_sha256': FLEET_SHA,
              'smallcraft_source_sha256': SMALL_SHA, 'study_source_sha256': digest(Path(__file__)),
              'imported_berth_helper_sha256': BERTH_HELPER_SHA,
              'historical_registry_sha256': REGISTRY_SHA,
              'registry_status': 'Historical bridge0.6.29 property export; current native installed-palette proof PENDING MASTER',
              'studies': studies, 'selected_saved_candidates': selected, 'protected_sources': records,
              'fresh_saved_surface_profiles': profile,
              'saved_region_sources': sources, 'files': {n: {'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)} for n, raw in files.items()},
              'world_writes': 0, 'native_calls': 0, 'entities_or_UUIDs_created': 0,
              'status': 'SAVED SOURCE STUDY ONLY; exact current native palette, before/support/AABBs and master lease required',
              'integration': 'No quay/town/terrain/ice/plant/structure/BE changes. Preserve all original history and conditional major berths. Master native VERIFY BEFORE/support, inspect actual occupancy, place exact admitted hash only, settle/VERIFY AFTER, then actual camera and walking/return-ladder checks.',
              'multiplayer_restart_performance': 'UNVERIFIED',
              'monitoring': '30GiB separately on both drives; monitoring does not constrain external apps or existing writers'}
    identity = hashlib.sha256(canonical(record)).hexdigest()
    output = Path(output).resolve() if output else home/'staging'/('fleet-smallcraft-'+identity[:16])
    if not output.is_relative_to(home/'staging') or not output.name.startswith('fleet-smallcraft-') or output.exists():
        raise UserError('Unique owned fleet-smallcraft output required')
    files['manifest.json'] = canonical(record)
    if sum(map(len, files.values())) > MAX_OUTPUT:
        raise UserError('Combined smallcraft study exceeds32MiB allocation')
    guard(0, MAX_OUTPUT)
    output.mkdir(parents=True, exist_ok=False)
    for name, raw in files.items():
        path = output/name
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as stream:
            stream.write(raw)
    return {'directory': str(output), 'manifest_sha256': digest(output/'manifest.json'),
            'selected_saved_candidates': selected, 'refused_candidates': sum(sum(a['status'].startswith('REFUSED') for a in rows) for rows in studies.values()),
            'total_bytes': sum(map(len, files.values())), 'native_calls': 0, 'world_writes': 0}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--home', type=Path, default=HOME)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    import json
    print(json.dumps(prepare(args.home, args.output)))
