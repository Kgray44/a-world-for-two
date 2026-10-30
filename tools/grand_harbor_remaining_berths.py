"""Saved6ad3a8 census for the two remaining major-ship construction dependencies.

This is source-only coordination. No server/client/world/clearing action exists.
Rejected berths never produce PLACE files. Plant proposals are nonexecutable.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

from control_room.common import UserError, digest, read_json
from tools.grand_harbor_fleet import build, canonical, identifier
from tools.grand_harbor_berth import (
    AIR, AIR_STATES, WATER, HOME, bounds,
    camera_batch, nearby_quay, probe_cells,
    protections, rotate_point, rotated_state,
)
from tools.playtest import guard
from tools.settlement_attractions import BackupWorld


FLEET_SHA = 'fe4251af7c032257e15f90a428defb5c523bb51fea8bd09a37db43066958119a'
CHECKPOINT = '20261028T191243Z-6ad3a8'
CHECKPOINT_SHA = '0ba7ad2097fb52273a37da6a76d8fc030133b79cd26d81b97531d8d74c2546c2'
OLD_STUDY_CHECKPOINT = '20261028T180051Z-30624d'
OLD_STUDY_SHA = '3cb269d28ae1ccbac882a44d35277d82c83582274abad2f1cf3b41566d3e9b24'
REGISTRY_SHA = '8cfa5ae77e20b8b5c1730b2928c55156557ebecb7e84480142088bda04ef92c4'
REGISTRY = 'staging/fleet-registry-provenance-8cfa5ae7/registry-original.json'
WREN = 'staging/fleet-berth-wren-9d0b486aae22282e'
WREN_MANIFEST_SHA = '308a2a1cdf8dc4821639a3ba56af4608b3c08e26570b2bb76347673a1e276eb0'
PROTECTION_HELPER_SHA = 'f61f45913a9d60846bdd6a9d04e6f4a049cfdd0129f1a3d6fc2fec4612cc7984'
PROTECTION_HELPER_COMMIT = '8c0ceac28ddaad6f806e427c99432bcb072c189a'
ROLES = ('golden-petrel', 'mercy-of-the-tide')
POSES = {'golden-petrel': ((1110, 63, -1344), 1), 'mercy-of-the-tide': ((1230, 63, -1376), 1)}
MAX_OUTPUT, MAX_READS = 32*1024**2, 200_000
# Explicit known IDs only. Actual presence and exact properties are checked too.
MARINE_IDS = {'minecraft:kelp', 'minecraft:kelp_plant', 'minecraft:seagrass',
              'minecraft:tall_seagrass', 'hybrid_aquatic:delesseria',
              'hybrid_aquatic:delesseria_plant'}
FIRST_REFUSALS = {
    'golden-petrel': [
        (-1344, (1075, 57, -1348), 'hybrid_aquatic:delesseria[age=24]'),
        (-1360, (1076, 57, -1354), 'hybrid_aquatic:delesseria_plant'),
        (-1376, (1079, 54, -1372), 'minecraft:kelp_plant'),
        (-1392, (1088, 53, -1390), 'hybrid_aquatic:delesseria_plant'),
        (-1408, (1089, 53, -1409), 'minecraft:kelp[age=23]'),
        (-1424, (1076, 62, -1429), 'lootr:lootr_barrel[facing=west,open=false]')],
    'mercy-of-the-tide': [
        (-1376, (1187, 57, -1379), 'minecraft:kelp[age=24]'),
        (-1392, (1190, 55, -1387), 'hybrid_aquatic:delesseria_plant'),
        (-1408, (1191, 54, -1403), 'minecraft:kelp_plant'),
        (-1424, (1216, 53, -1421), 'minecraft:kelp_plant'),
        (-1440, (1216, 52, -1441), 'hybrid_aquatic:delesseria_plant'),
        (-1456, (1207, 52, -1457), 'hybrid_aquatic:delesseria_plant')],
}


def checked_checkpoint(receipt):
    if (receipt.get('id') != CHECKPOINT or receipt.get('sha256') != CHECKPOINT_SHA
            or receipt.get('verified') is not True):
        raise UserError('Exact verified6ad3a8 checkpoint required;306 observations are separate')


def native_plan(registry, field, name, *, tags=(), verify=True):
    """New authenticated checkpoint binding, independent of Wren's fixed proof."""
    palette = sorted(set(field.values()))
    index, box = {state: n for n, state in enumerate(palette)}, bounds(field)
    return {'format': 'awft-native-settlement:1', 'name': name,
            'seed': registry['seed'], 'world_path': registry['world_path'],
            'backup_sha256': CHECKPOINT_SHA, 'bounds': [box[0], box[2], box[3], box[5]],
            'palette': palette, 'blocks': [[*p, index[s]] for p, s in sorted(field.items())],
            'block_entities': list(tags), 'commands': [], 'landmarks': [],
            'verification_only': verify, 'construction_forbidden': verify,
            'validation': 'Saved6ad3a8 source only with historical authoring registry; current native palette/before/entity verification pending'}


def translated(document, registry, role, origin, rotation):
    """Role-aware fixed-template translation, without spoofing Wren's KEY guard."""
    if (role not in ROLES or document.get('key') != role or document.get('format') != 'awft-fleet-template:1'
            or len(origin) != 3 or any(type(v) is not int for v in origin) or origin[1] != 63
            or type(rotation) is not int or rotation not in range(4)):
        raise UserError('One exact remaining role, integer seaY63 and quarter turn required')
    palette = [rotated_state(state, registry, rotation) for state in document['palette']]
    field = {rotate_point(row[:3], origin, rotation): palette[row[3]] for row in document['blocks']}
    if not 0 < len(field) <= 40_000 or len(field) != len(document['blocks']):
        raise UserError('Finite unique role geometry required')
    tags = [{'pos': list(rotate_point(row['pos'], origin, rotation)), 'nbt': row['nbt']}
            for row in document['block_entities']]
    return field, tags


def required_probe(document, origin, rotation):
    water, air, detail = probe_cells(document)
    bx, _, bz = next(f for f in document['design']['fittings'] if f['kind'] == 'boarding interface')['local_floor']
    # Full boat body/headroom over the first eight outward travel blocks plus
    # berth clearance; two source-water layers below the63 water surface.
    departure = {(x, y, z) for x in range(bx+2, bx+12) for y in range(-2, 4)
                 for z in range(bz-2, bz+3)}
    water.update(p for p in departure if p[1] < 0)
    air.update(p for p in departure if p[1] >= 0)
    probe = {rotate_point(p, origin, rotation): WATER for p in water}
    probe.update({rotate_point(p, origin, rotation): AIR for p in air})
    detail.update(local_departure_bounds=bounds(departure), outward_departure_blocks=8,
                  water_layers_below_surface=2, world_probe_bounds=bounds(probe))
    return probe, detail


def classify(state, pos, registry, has_be=False):
    if state is None:
        return 'UNKNOWN'
    if has_be:
        return 'BLOCK_ENTITY_PRESERVE'
    if state in AIR_STATES:
        return 'AIR'
    if state == WATER:
        return 'SOURCE_WATER'
    key = identifier(state)
    if key in MARINE_IDS and key in registry['blocks'] and pos[1] < 63:
        try:
            rotated_state(state, registry, 0)
            return 'MARINE_VEGETATION'
        except UserError:
            pass
    return 'NON_SOURCE_WATER' if key == 'minecraft:water' else 'HARD_TERRAIN_OR_STRUCTURE'


def census(document, registry, snapshot, role, origin, rotation, protected=(), wren=(), other_role=()):
    field, tags = translated(document, registry, role, origin, rotation)
    probe, detail = required_probe(document, origin, rotation)
    protected, wren, other_role = set(protected), set(wren), set(other_role)
    before, observations, plants, unknown = {}, [], [], []
    counts, states = Counter(), Counter()
    for pos in sorted(set(field) | set(probe)):
        error = None
        try:
            state = snapshot.state(pos)
        except UserError as exc:
            state, error = None, str(exc)
        kind = classify(state, pos, registry, pos in snapshot.protected)
        counts[kind] += 1
        if state is not None:
            before[pos] = state
            states[state] += 1
        else:
            unknown.append({'pos': list(pos), 'reason': error or 'No saved state; never substitute AIR'})
        flags = {'protected_source': pos in protected, 'wren_reserved': pos in wren,
                 'other_role_reserved': pos in other_role}
        probe_mismatch = pos in probe and state != probe[pos]
        if kind not in {'AIR', 'SOURCE_WATER'} or any(flags.values()) or probe_mismatch:
            observations.append({'pos': list(pos), 'saved_state': state, 'classification': kind,
                                 'required_probe_state': probe.get(pos), 'probe_mismatch': probe_mismatch,
                                 'authored_target': pos in field, 'clearance_probe': pos in probe,
                                 'desired_source_state': field.get(pos),
                                 'flags': flags, 'block_entity': pos in snapshot.protected})
        if kind == 'MARINE_VEGETATION':
            plants.append({'pos': list(pos), 'before_state': state, 'proposed_after_state': WATER,
                           'protected_flags': flags, 'contains_block_entity': False,
                           'review_only_no_permission': True})
    overlap = {'protected_source_cells': sum(p in protected for p in set(field)|set(probe)),
               'wren_reserved_cells': sum(p in wren for p in set(field)|set(probe)),
               'other_role_reserved_cells': sum(p in other_role for p in set(field)|set(probe))}
    source_probe_conflicts = [list(p) for p in set(field)&set(probe) if identifier(field[p]) not in AIR_STATES]
    passed = not observations and not source_probe_conflicts
    bottom = {}
    for x, y, z, index in document['blocks']:
        if y <= 0 and identifier(document['palette'][index]) not in AIR_STATES:
            bottom[x, z] = min(y, bottom.get((x, z), y))
    keel = {rotate_point((x, y-down, z), origin, rotation) for (x, z), y in bottom.items() for down in (1, 2)}
    detail.pop('two_block_under_keel_margin', None)
    detail.update(two_block_under_keel_margin_required=True,
                  two_block_under_keel_saved_verified=all(before.get(p) == WATER for p in keel),
                  complete_saved_probe_verified=all(before.get(p) == state for p, state in probe.items()),
                  current_native_clearance_verified=False)
    for kind in ('AIR', 'SOURCE_WATER', 'MARINE_VEGETATION', 'HARD_TERRAIN_OR_STRUCTURE',
                 'BLOCK_ENTITY_PRESERVE', 'NON_SOURCE_WATER', 'UNKNOWN'):
        counts.setdefault(kind, 0)
    detail.update(world_authored_bounds=bounds(field), authored_positions=len(field),
                  target_and_probe_cells=len(set(field)|set(probe)), known_saved_cells=len(before),
                  classification_counts=dict(counts), exact_saved_state_counts=dict(states), **overlap,
                  source_solid_probe_conflicts=source_probe_conflicts,
                  marine_vegetation_cells=len(plants), marine_bounds=bounds([r['pos'] for r in plants]) if plants else None)
    report = {'format': 'awft-remaining-harbor-census:1', 'role': role, 'origin': list(origin), 'rotation': rotation,
              'strict_saved_admission_passed': passed, 'detail': detail, 'obstructions': observations,
              'unknown': unknown, 'all_positions_censused': True,
              'native_actions': 0, 'clearing_approval': None, 'placement_authority': None,
              'status': 'SAVED SOURCE ONLY; current native palette/before/entity verification pending'}
    proposal = {'format': 'awft-unapproved-marine-vegetation-proposal:1', 'role': role,
                'not_executable': True, 'approved': False, 'approval': None, 'world_writes': 0,
                'native_actions': 0, 'commands': [], 'replacement': WATER, 'cells': plants,
                'count': len(plants), 'bounds': detail['marine_bounds'],
                'exact_cells_sha256': hashlib.sha256(canonical(plants)).hexdigest(),
                'native_ids': sorted({identifier(r['before_state']) for r in plants}),
                'conditions': ['Owner/master must explicitly approve any plant handling before a native plan exists',
                               'Protected masks, existing BEs/inventories and hard terrain remain independent blockers',
                               'Fresh native exact plant-before and current source-water/body/entity checks required',
                               'No approval is inferred from this record or from the absence of other blockers']}
    return field, tags, before, probe, report, proposal


def wren_reservation(home):
    folder = home/WREN
    if digest(folder/'manifest.json') != WREN_MANIFEST_SHA:
        raise UserError('Exact final first-Wren manifest required')
    manifest = read_json(folder/'manifest.json')
    reserved, records = set(), []
    for name in ('placement.json', 'under-keel-load-VERIFY-ONLY.json'):
        path, expected = folder/name, manifest['files'][name]
        if digest(path) != expected['sha256'] or path.stat().st_size != expected['bytes']:
            raise UserError('First Wren reservation source differs')
        doc = read_json(path)
        reserved.update(tuple(row[:3]) for row in doc['blocks'])
        records.append({'path': str(path), **expected, 'positions': len(doc['blocks'])})
    return reserved, {'manifest_sha256': WREN_MANIFEST_SHA, 'files': records, 'reserved_cells': len(reserved)}


class BoundedSaved:
    def __init__(self, snapshot):
        self.snapshot, self.reads = snapshot, 0
        self.protected = snapshot.protected

    def state(self, pos):
        self.reads += 1
        if self.reads > MAX_READS:
            raise UserError('Finite saved-only census read allocation exceeded')
        value = self.snapshot.state(pos)
        if len(self.snapshot.chunks) > 32:
            self.snapshot.chunks.pop(next(iter(self.snapshot.chunks)))
        return value


def prepare(home=HOME, output=None):
    home = Path(home).resolve()
    if home != HOME.resolve():
        raise UserError('Only the existing owned construction home is admitted')
    source = Path(__file__).with_name('grand_harbor_fleet.py')
    protection_helper = Path(__file__).with_name('grand_harbor_berth.py')
    registry_path = home/REGISTRY
    if (digest(source) != FLEET_SHA or digest(registry_path) != REGISTRY_SHA
            or digest(protection_helper) != PROTECTION_HELPER_SHA):
        raise UserError('Exact frozen fleet and retained historical registry required')
    registry = read_json(registry_path)
    if registry.get('at') != '2026-10-27T23:11:56.377525200Z':
        raise UserError('Historical registry timestamp differs; it is not a current native export')
    companion = read_json(home/'backups'/(CHECKPOINT+'.json'))
    receipt = {'id': CHECKPOINT, 'sha256': companion['sha256'], 'verified': companion['integrity'] == 'verified'}
    checked_checkpoint(receipt)
    protected, protected_sources = protections(home, registry)
    from tools.grand_harbor_berth import ADDITIONAL_CITY_PROTECTIONS, PIPPIN_COVER_POINTS
    additional_city_pins = {pin for _, _, pin in ADDITIONAL_CITY_PROTECTIONS}
    if (len(additional_city_pins) != 6 or not additional_city_pins <= {row.get('sha256') for row in protected_sources}
            or not set(PIPPIN_COVER_POINTS) <= protected):
        raise UserError('All six additional city masks and both Pippin points are required')
    wren, wren_sources = wren_reservation(home)
    documents = {role: build(registry, role) for role in ROLES}
    spaces = {}
    for role in ROLES:
        origin, rotation = POSES[role]
        field, _ = translated(documents[role], registry, role, origin, rotation)
        probe, _ = required_probe(documents[role], origin, rotation)
        spaces[role] = set(field)|set(probe)
    snapshot = BackupWorld(home, receipt, registry)
    reader, files, summaries = BoundedSaved(snapshot), {}, {}
    try:
        cover_states = [{'pos': list(pos), 'saved_state': reader.state(pos)} for pos in PIPPIN_COVER_POINTS]
        if any(row['saved_state'] != AIR for row in cover_states):
            raise UserError('New checkpoint must retain both separately cleared Pippin AIR cover points')
        for role in ROLES:
            origin, rotation = POSES[role]
            other = next(key for key in ROLES if key != role)
            field, tags, before, probe, report, proposal = census(
                documents[role], registry, reader, role, origin, rotation, protected, wren, spaces[other])
            landing = next(f for f in documents[role]['design']['fittings'] if f['kind'] == 'boarding interface')['local_floor']
            report['nearby_quay'] = nearby_quay(reader, rotate_point(landing, origin, rotation), protected)
            report['prior_finite_search_first_refusals'] = [
                {'origin': [origin[0], 63, z], 'rotation': 1, 'pos': list(pos), 'state': state,
                 'checkpoint_id': OLD_STUDY_CHECKPOINT, 'checkpoint_sha256': OLD_STUDY_SHA,
                 'evidence': 'Earlier saved306 first-refusal observation; not a complete census of that shifted pose'}
                for z, pos, state in FIRST_REFUSALS[role]]
            files[role+'-census.json'] = canonical(report)
            files[role+'-marine-vegetation-UNAPPROVED.json'] = canonical(proposal)
            files[role+'-cameras-SOURCE-ONLY.json'] = canonical(camera_batch(documents[role], origin, rotation))
            if not report['unknown']:
                old = native_plan(registry, before, role+' complete saved6ad3a8 block-state BEFORE VERIFY ONLY')
                old['inventory_custody'] = 'Existing BE data/inventories retained untouched in the authenticated archive; no inventory rewrite or slot-census claim'
                files[role+'-current-before-VERIFY-ONLY.json'] = canonical(old)
            if report['strict_saved_admission_passed']:
                files[role+'-placement.json'] = canonical(native_plan(registry, field, role, tags=tags, verify=False))
                files[role+'-support-VERIFY-ONLY.json'] = canonical(native_plan(registry, probe, role+' support VERIFY ONLY'))
                files[role+'-complete-after-VERIFY-ONLY.json'] = canonical(native_plan(registry, {**before, **field}, role+' after VERIFY ONLY', tags=tags))
            summaries[role] = {k: report[k] for k in ('origin', 'rotation', 'strict_saved_admission_passed', 'detail', 'nearby_quay')}
        sources = [row | {'role': 'Authenticated immutable6ad3a8 saved-state input; historical authoring registry, never current native proof'} for row in snapshot.sources]
    finally:
        snapshot.close()
    if (digest(source) != FLEET_SHA or digest(registry_path) != REGISTRY_SHA
            or digest(protection_helper) != PROTECTION_HELPER_SHA):
        raise UserError('Frozen source or historical registry changed while preparing census')
    manifest = {'format': 'awft-remaining-fleet-saved-dependencies:1', 'checkpoint_id': CHECKPOINT,
                'checkpoint_sha256': CHECKPOINT_SHA, 'fleet_source_sha256': FLEET_SHA,
                'source_sha256': digest(Path(__file__)), 'historical_registry': {
                    'path': str(registry_path), 'sha256': REGISTRY_SHA, 'exported': registry['at'],
                    'bridge_version': '0.6.29', 'temporal_status': 'HISTORICAL AUTHORING EXPORT; NOT CURRENT NATIVE REGISTRY'},
                'roles': summaries, 'protected_sources': protected_sources, 'wren_reservation': wren_sources,
                'protection_helper_sha256': PROTECTION_HELPER_SHA,
                'protection_helper_commit': PROTECTION_HELPER_COMMIT,
                'protected_mask_cell_count': len(protected), 'protected_source_record_count': len(protected_sources),
                'additional_city_source_pins': sorted(additional_city_pins),
                'separately_cleared_cover_cells_reread': cover_states,
                'proposed_role_masks_mutual_overlap': len(spaces[ROLES[0]] & spaces[ROLES[1]]),
                'saved_sources': sources, 'saved_state_reads': reader.reads,
                'native_palette_before_entity_visual_multiplayer_restart_performance': 'UNVERIFIED; master owns current checks',
                'pose_search': 'Stopped. Only the first historical pose of each role received this complete census.',
                'files': {name: {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()} for name, raw in files.items()},
                'native_actions': 0, 'world_writes': 0, 'clearing_approval': None,
                'monitoring': '30GiB free separately onC/D; monitoring does not constrain external apps/existing writers'}
    if sum(map(len, files.values()))+64*1024 > MAX_OUTPUT:
        raise UserError('Combined remaining-fleet source output exceeds32MiB')
    identity = hashlib.sha256(canonical({'files': manifest['files'], 'source': manifest['source_sha256'],
                                         'checkpoint': CHECKPOINT_SHA})).hexdigest()
    output = Path(output).resolve() if output else home/'staging'/('fleet-remaining-'+identity[:16])
    if not output.is_relative_to(home/'staging') or not output.name.startswith('fleet-remaining-') or output.exists():
        raise UserError('Unique owned fleet-remaining output required; immutable prior results retained')
    retained = sum(path.stat().st_size for folder in (home/'staging').glob('fleet-remaining-*')
                   if folder.is_dir() for path in folder.iterdir() if path.is_file())
    if retained+sum(map(len, files.values()))+64*1024 > MAX_OUTPUT:
        raise UserError('Combined retained and new remaining-fleet source outputs exceed32MiB')
    manifest['reserve_guard'] = guard(0, MAX_OUTPUT)
    manifest['retained_prior_source_bytes'] = retained
    files['manifest.json'] = canonical(manifest)
    output.mkdir(parents=True, exist_ok=False)
    for name, raw in files.items():
        with (output/name).open('xb') as stream:
            stream.write(raw)
    return {'directory': str(output), 'manifest_sha256': digest(output/'manifest.json'),
            'roles': summaries, 'bytes': sum(map(len, files.values())), 'world_writes': 0}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--home', type=Path, default=HOME)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    print(json.dumps(prepare(args.home, args.output)))
