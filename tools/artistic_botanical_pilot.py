"""Exact original layered-façade pilot; masks remain construction reservations.

The prototype concerns the Drowned Rose's retained rear/side façades. It cannot
authorize a whole-town rollout, nor cover the separately reserved new oriels.
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

from control_room.common import UserError, digest, read_json
from tools import artistic_botanical as botanical
from tools.artistic_bridge_refinement import flatten
from tools.artistic_forest_understory import settlement_plan
from tools.artistic_south_extent import ExtentTerrain
from tools.playtest import guard

OWNER = 'Drowned Rose retained façades'
OWNERS = (
    ('staging/artistic-pirate-spit-byte-slots-1793124362042040500/drowned-rose-VERIFY-ONLY.json',
     'f646d9ed046f603dc4e55c3f564949dba3a45be733dbd8c88ebba9cf48d85486'),
    ('staging/artistic-maritime-depth-1793125315305851100/drowned-rose-depth.json',
     'be443dbe28d6608a9348a58dcfb8b4b2766eea54ce47a690314f22f5c08b3b98'),
    ('staging/artistic-rose-furnishing-1793129631429439500/furnishing.json',
     '7a4dd44e355b29d9587e6f609e12ce054139dd6565e58367cc371d0c221effe3'),
    ('staging/rose-exterior-ADMITTED-native45-20261028T0315Z/complete-after-VERIFY-ONLY.json',
     '9c5ea8f01eac12f44997e548586e919381785e7d848f775733233af16d5d97e6'),
)
FUTURE_ORIEL = ('staging/drowned-rose-exterior-oriels-20261028T0240Z/future-exterior-reservation-ONLY.json',
                'b34a82dd771829479d837bdf595a47beabb517d9f1d104d1288b34b16cc250f2')
V2 = ('staging/zipline-west-v2-source-1793152099836099800/all-v2-RESERVATION-ONLY.json',
      '92ea594836795a61e00f5cc32290d49d1d47b9fd6eb55aeefc99d527acf8854d')
FNT = ('staging/artistic-fountain-centerpiece-r5-wet-reset-20261027T2255Z/forest-reservation-ONLY.json',
       'c3914908a029ce58ee55124016933f8aa8a850b300da6c269076253b30a9ff3b')
INDEX = ('staging/south-contour-walks-metadata-r2-1793133317004398500/exclusions-final-r2.json',
         '4aae243035f6d9887ce145a974b8de6cbbee8b909ec4306091042fe62c9c32d9')


def checked(home, ref, cap=16*1024**2):
    path = (home/ref[0]).resolve()
    if not path.is_relative_to(home/'staging') or path.is_symlink() or not 0 < path.stat().st_size <= cap or digest(path) != ref[1]:
        raise UserError('Exact original botanical pilot source differs')
    return read_json(path)


def recipe(home, output):
    home, output = Path(home).resolve(), Path(output).resolve()
    if output.exists() or not output.is_relative_to(home/'staging'):
        raise UserError('New owned botanical recipe folder required')
    reserve = guard(1024**2, 8*1024**2)
    registry = read_json(home/'dashboard/settlement/registry.json')
    checkpoint = read_json(home/'dashboard/settlement/backup-receipt.json')
    if checkpoint.get('verified') is not True:
        raise UserError('Verified stopped source archive required')
    authored = {}
    for ref in OWNERS:
        doc = checked(home, ref)
        if any(str(doc[k]) != str(registry[k]) for k in ('seed', 'world_path')):
            raise UserError('Original botanical owner world differs')
        authored.update(flatten(doc))
    masks, docs, custody = {}, {}, []
    masks['current_fountain_whole_crown'] = flatten(checked(home, FNT))
    custody.append({'role': 'current_fountain_whole_crown', 'source': FNT,
                    'meaning': 'Complete original prospective geometry/AIR/arrival mask retained as keepout, not a world-state proof'})
    mechanisms = {}
    index = checked(home, INDEX, 2*1024**2)
    for ref in index['plans']:
        if ref['name'] in ('Bascule and towers full', 'Watermill full', 'Watermill R3', 'Watermill geometric depth and future oriels'):
            path = Path(ref['path'])
            if not path.resolve().is_relative_to(home) or digest(path) != ref['sha256']:
                raise UserError('Retained machine source changed')
            mechanisms.update(flatten(read_json(path)))
            custody.append({'role': 'bridge_and_machine_sweeps', 'source_sha256': ref['sha256'], 'name': ref['name']})
    masks['bridge_and_machine_sweeps'] = mechanisms
    masks['zipline_flight_and_frames'] = flatten(checked(home, V2))
    custody.append({'role': 'zipline_flight_and_frames', 'source': V2, 'meaning': 'Unbuilt actual-v2 frame/flight/construction reservation, not observed AIR'})
    # The pilot is attached to this exact owner only. Its authored interior AIR,
    # doors and existing BE positions are protected; no room/passage is planted.
    work = {p: value for p, value in authored.items() if botanical.key(value) in botanical.AIR}
    for ref in OWNERS:
        for be in checked(home, ref).get('block_entities', []):
            work[tuple(be['pos'])] = 'minecraft:air'
    windows = {}
    for p, value in authored.items():
        key = botanical.key(value)
        if any(word in key for word in ('window', 'glass', 'sign', 'door')):
            windows[p] = value
            # Actual authored window height stays visible. Trays below the sill
            # and separated wall piers retain their own attachment checks.
            for face in botanical.FACES.values():
                for distance in (1, 2):
                    q = botanical.plus(p, face, distance)
                    windows[q] = 'minecraft:air'
                    if 'door' in key:
                        work[q] = 'minecraft:air'
                        work[botanical.plus(q, (0, 1, 0))] = 'minecraft:air'
    windows.update(flatten(checked(home, FUTURE_ORIEL)))
    custody.append({'role': 'windows_signs_doors_and_views', 'source': FUTURE_ORIEL,
                    'meaning': 'Separate new clerestory/oriel geometry and view space protected; never planted over'})
    masks['walking_and_working_bodies'] = work
    masks['windows_signs_doors_and_views'] = windows
    mask_refs = []
    for role in sorted(botanical.REQUIRED_MASKS):
        mask = settlement_plan(registry, checkpoint, masks[role], 'RESERVATION ONLY scoped botanical pilot '+role)
        mask.update(reservation_only=True, not_an_observed_AIR_plan=True,
                    authority_scope=OWNER, cannot_authorize_whole_town_propagation=True)
        raw = (json.dumps(mask, separators=(',', ':'))+'\n').encode()
        name = role+'-RESERVATION-ONLY.json'
        docs[name] = raw
        mask_refs.append({'role': role, 'path': (output/name).relative_to(home).as_posix(), 'sha256': hashlib.sha256(raw).hexdigest()})
    scenes = botanical.source_candidates(OWNER, authored, limit=16)
    for row in scenes:
        if row['kind'] == 'wall_climber':
            row['kind'] = 'wall_hanging_climber'
            row['label'] += ' (real side attachment; no invented ground root)'
    # Additional original explicit paired window pockets; duplicates will refuse
    # atomically rather than replay or overwrite a previously admitted scene.
    for x in (1295, 1304):
        scenes.insert(0, {'label': 'Rear cottage-window flowering ledge '+str(x), 'owner': OWNER,
            'kind': 'window_tray', 'args': {'wall_base': [x, 66, -1290], 'face': 'north'}})
    for wall in ([1291, 73, -1290], [1308, 73, -1290]):
        scenes.append({'label': 'Supported berry-lit rear eave '+str(wall), 'owner': OWNER,
            'kind': 'berry_bracket', 'args': {'wall': wall, 'face': 'north', 'length': 3}})
    # Authored corner fittings are selected against literal saved roots/targets,
    # not guessed from a silhouette or inserted through a fancy window.
    center = (1301.5, -1279.5)
    fittings = []
    for p, value in sorted(authored.items()):
        if not 69 <= p[1] <= 75 or botanical.key(value) not in botanical.STURDY:
            continue
        for face, normal in botanical.FACES.items():
            if (p[0]-center[0])*normal[0]+(p[2]-center[1])*normal[2] < 7:
                continue
            if any(q['kind'] == 'berry_bracket' and math_dist(q['args']['wall'], p) < 6 for q in fittings):
                continue
            fittings.append({'label': 'Measured sheltered timber berry fitting '+str(p), 'owner': OWNER,
                             'kind': 'berry_bracket', 'args': {'wall': list(p), 'face': face, 'length': 3}})
            if len(fittings) >= 32:
                break
        if len(fittings) >= 32:
            break
    scenes += fittings
    terrain = ExtentTerrain(home, checkpoint, registry)
    reserved = set().union(*(set(values) for values in masks.values()))
    excluded = {(x+dx, z+dz) for x, _, z in masks['current_fountain_whole_crown']
                for dx in range(-5, 6) for dz in range(-5, 6)}
    garden = botanical.Garden(registry, lambda p: terrain.state(*p), terrain.entities, reserved, excluded)
    selected, refusals = [], []
    try:
        for scene in scenes:
            if len(selected) >= 12:
                break
            if scene['kind'] == 'berry_bracket' and sum(s['kind'] == 'berry_bracket' for s in selected) >= 2:
                continue
            try:
                botanical.COMPONENTS[scene['kind']](garden, OWNER, **scene['args'])
            except UserError as error:
                refusals.append({'label': scene['label'], 'reason': str(error), 'partial_cells_retained': False})
                continue
            selected.append(scene)
        botanical.check_authored_owners(garden, {OWNER: authored})
        if any(not (1283 <= p[0] <= 1320 and -1296 <= p[2] <= -1263 and 60 <= p[1] <= 90) for p in garden.blocks):
            raise UserError('Scoped botanical scene escaped its reviewed owner exterior')
        # These are conservative retained envelopes, not a claimed native moving
        # collision proof. This owner is spatially separate from both.
        from tools.artistic_zipline_catenary import spatial_custody
        spatial_custody(garden.blocks)
    finally:
        terrain.close()
    if not selected:
        raise UserError('No measured layered botanical scene survived source admission')
    scenes = selected
    document = {'format': 'awft-original-botanical-composition:1', 'checkpoint_id': checkpoint['id'],
        'checkpoint_sha256': checkpoint['sha256'], 'reference_sha256': botanical.REFERENCE_SHA256,
        'owners': [{'name': OWNER, 'members': [{'path': path, 'sha256': sha} for path, sha in OWNERS]}],
        'masks': mask_refs, 'scenes': scenes, 'authority_scope': 'One layered-façade visual prototype; all other town owners require their own complete source/masks',
        'mask_source_custody': custody, 'retained_preselection_refusals': refusals,
        'actual_saved_preselection_is_not_native_survival_or_art_acceptance': True,
        'native_actions': 0, 'reference_asset_copied': False}
    docs['recipe-REVIEW-ONLY.json'] = (json.dumps(document, separators=(',', ':'))+'\n').encode()
    docs['manifest.json'] = (json.dumps({'format': 'awft-layered-botanical-pilot-recipe:1',
        'source_sha256': digest(Path(__file__)), 'checkpoint_id': checkpoint['id'], 'checkpoint_sha256': checkpoint['sha256'],
        'reserve_guard': reserve, 'selected_scenes': len(scenes), 'native_actions': 0,
        'files': {name: {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()} for name, raw in docs.items()}},
        separators=(',', ':'))+'\n').encode()
    if sum(map(len, docs.values())) > 8*1024**2:
        raise UserError('Finite original botanical recipe budget exceeded')
    output.mkdir(parents=True, exist_ok=False)
    for name, raw in docs.items():
        (output/name).write_bytes(raw)
    return output/'recipe-REVIEW-ONLY.json', hashlib.sha256(docs['recipe-REVIEW-ONLY.json']).hexdigest()


def math_dist(a, b):
    return sum((x-y)**2 for x, y in zip(a, b))**.5


def prepare(home):
    home = Path(home).resolve()
    stamp = str(time.time_ns())
    path, sha = recipe(home, home/'staging'/('layered-botanical-recipe-'+stamp))
    return botanical.prepare(home, path, sha, home/'staging'/('layered-botanical-native-source-'+stamp))
