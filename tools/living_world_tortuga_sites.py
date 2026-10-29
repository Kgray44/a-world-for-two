"""Ten small source-only fit-outs inside the completed eastern city.

Reads only the coordinator-pinned authored plans and their native receipts.
No world, runtime, provider, spawn, request-installation or shared-source writes.
Master must rebind the proposed AIR preimage to its fresh checkpoint and perform
native placement/habitat/POI checks. Unknown source cells are never assumed AIR.
"""
from __future__ import annotations

import argparse
from collections import deque
import hashlib
import json
from pathlib import Path

from control_room.common import UserError
from living_world.cast import ROLES
from tools.living_world_cast import encoded, read


SEALED = 'staging/east-city58-execution-1793245885314381500/NATIVE25-COMPLETE-SEALED.json'
SEALED_SHA = 'e878b6caf3327d783446aa6701c5d3406e0b3f4d1f2c6d1d64f1fa9969b9da08'
FOURTEEN = 'staging/eastern-attached-clerestories-1793244651287380500/complete14-AFTER.json'
FOURTEEN_SHA = 'cabcc4ba94b1d7ed201730b313b808546e88a1d6965eff62d1276a9fc3339fd3'
LAYOUT = 'staging/eastern-coast-urban-layout-1793205607174241200/urban-plan-REVIEW-ONLY.json'
LAYOUT_SHA = '6f24640d9efefae3340be80d34bcd0e4788f2ded695aefe03d1d6815761a12a4'
PREMISES = {
    'barnacle-bill': 'anchor-dice', 'old-finn': 'tide-fish',
    'captain-blackthorn': 'tide-broker', 'mara-keel': 'sandbar',
    'steward-pembroke': 'bridge-customs', 'librarian-elm': 'worn-book',
    'captain-thimble': 'shoal-warden', 'poppy-green': 'river-stone',
    'foreman-rivet': 'pelican-forge', 'mercy-tide': 'old-rum',
}
AIR = {'minecraft:air', 'minecraft:cave_air', 'minecraft:void_air'}
DIRECTIONS = {'north': (0, -1), 'east': (1, 0), 'south': (0, 1), 'west': (-1, 0)}


def base(state):
    return (state or '').split('[', 1)[0]


def solid(state):
    key = base(state)
    return key.startswith('minecraft:') and (key.endswith(('_planks', '_log', '_wood')) or key in {
        'minecraft:stone', 'minecraft:stone_bricks', 'minecraft:bricks', 'minecraft:polished_andesite',
        'minecraft:andesite', 'minecraft:cobblestone', 'minecraft:calcite', 'minecraft:terracotta'})


def adjacent(p):
    x, y, z = p
    return [(x + dx, y, z + dz) for dx, dz in DIRECTIONS.values()]


def checked(home, relative, sha, cap=8 * 1024**2):
    path = home / relative
    if Path(relative).is_absolute() or '..' in Path(relative).parts:
        raise UserError('Owned source reference required')
    doc, ref = read(path, cap)
    if ref['sha256'] != sha:
        raise UserError('Pinned completed source differs: ' + relative)
    return doc, dict(ref, path=relative)


def cells(plan):
    field = {tuple(row[:3]): plan['palette'][row[3]] for row in plan['blocks']}
    if len(field) != len(plan['blocks']):
        raise UserError('Duplicate source cells')
    return field


def choose(field, columns, station, forbidden=None):
    forbidden = set(forbidden or ())
    free = {p for p, s in field.items() if (p[0], p[2]) in columns and s in AIR
            and p not in forbidden and (p[0], p[1] + 1, p[2]) not in forbidden
            and field.get((p[0], p[1] + 1, p[2])) in AIR and solid(field.get((p[0], p[1] - 1, p[2])))}
    old_beds = []
    for p, s in sorted(field.items()):
        if not base(s).endswith('_bed') or 'part=head' not in s:
            continue
        facing = next((f for f in DIRECTIONS if 'facing=' + f in s), None)
        if facing:
            dx, dz = DIRECTIONS[facing]; foot = p[0] - dx, p[1], p[2] - dz
            if p not in forbidden and foot not in forbidden and base(field.get(foot)) == base(s) and 'part=foot' in field[foot]:
                old_beds.append((p, foot, {}))
    # Prefer existing beds; only add supported two-part beds to exact source AIR.
    bed_options = list(old_beds)
    edges = sorted(free, key=lambda p: (sum(n in free for n in adjacent(p)), p))
    for foot in edges:
        for facing, (dx, dz) in DIRECTIONS.items():
            head = foot[0] + dx, foot[1], foot[2] + dz
            if head in free:
                bed_options.append((head, foot, {head: f'minecraft:blue_bed[facing={facing},occupied=false,part=head]',
                                                foot: f'minecraft:blue_bed[facing={facing},occupied=false,part=foot]'}))
    existing_jobs = [p for p, s in sorted(field.items()) if base(s) == station and (p[0], p[2]) in columns and p not in forbidden]
    for head, foot, bed_delta in bed_options:
        near = sorted((p for p in free if p[1] == head[1] and p not in (head, foot)
                       and sum(n in free for n in adjacent(p)) >= 2),
                      key=lambda p: (sum(abs(p[i] - head[i]) for i in (0, 2)), p))[:48]
        for job in [p for p in existing_jobs if p[1] == head[1]] + near:
            delta = dict(bed_delta)
            if job not in existing_jobs:
                props = {'minecraft:smoker': '[facing=south,lit=false]', 'minecraft:barrel': '[facing=up,open=false]',
                         'minecraft:lectern': '[facing=south,has_book=false,powered=false]',
                         'minecraft:grindstone': '[face=floor,facing=south]', 'minecraft:composter': '[level=0]'}.get(station, '')
                delta[job] = station + props
            walkable = free - set(delta)
            starts = sorted(set(adjacent(head) + adjacent(foot)) & walkable)
            for start in starts:
                parent, queue = {start: None}, deque([start])
                goal = None
                while queue:
                    p = queue.popleft()
                    if sum(abs(p[i] - job[i]) for i in range(3)) <= 1:
                        goal = p; break
                    for n in adjacent(p):
                        if n in walkable and n not in parent:
                            parent[n] = p; queue.append(n)
                if goal is None:
                    continue
                route = []
                while goal is not None:
                    route.append(goal); goal = parent[goal]
                route.reverse()
                if len(route) > 64:
                    continue
                roofs = [(start[0] + dx, start[1] + dy, start[2] + dz) for dy in range(3, 9)
                         for dx, dz in [(0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)]
                         if solid(field.get((start[0] + dx, start[1] + dy, start[2] + dz)))
                         or base(field.get((start[0] + dx, start[1] + dy, start[2] + dz))).endswith(('_stairs', '_slab'))]
                for roof in roofs:
                    points = [head, foot, job, roof] + route
                    low = [min(p[i] for p in points) - 1 for i in range(3)]
                    high = [max(p[i] for p in points) + (2 if i == 1 else 1) for i in range(3)]
                    for i in range(3):
                        while high[i] - low[i] + 1 < 5:
                            low[i] -= 1
                    known = [(x, y, z) for x in range(low[0], high[0] + 1)
                             for y in range(low[1], high[1] + 1) for z in range(low[2], high[2] + 1)]
                    if len(known) > 4096 or any(p not in field for p in known):
                        continue
                    # AIR-only additions must not sever a previously connected room.
                    before = {p for p in free if p[1] == start[1]}
                    def reach(nodes):
                        seen, q = {start}, deque([start])
                        while q:
                            for n in adjacent(q.popleft()):
                                if n in nodes and n not in seen:
                                    seen.add(n); q.append(n)
                        return seen
                    if not reach(before) - set(delta) <= reach(walkable):
                        continue
                    return {'feet': [start[0] + .5, start[1], start[2] + .5],
                            'roam_bounds': [low[0], low[1], low[2], high[0] + 1, high[1] + 1, high[2] + 1],
                            'habitat': {'kind': 'HOME', 'known_bounds': low + high, 'bed': list(head), 'job': list(job),
                                        'roof': list(roof), 'bed_path': [list(start)], 'job_path': [list(p) for p in route]},
                            'delta': delta, 'known': known, 'existing_bed': not bed_delta,
                            'existing_job': job in existing_jobs, 'own_room_connected_after_fitout': True}
    raise UserError('No source-complete HOME/compatible job/roof/connected AIR-only fit-out found in this premise')


def native_plan(source, field, title, verify):
    palette = sorted(set(field.values())); indexes = {s: i for i, s in enumerate(palette)}
    return {'format': 'awft-native-settlement:1', 'name': title, 'seed': source['seed'], 'world_path': source['world_path'],
            'backup_sha256': source['backup_sha256'], 'bounds': [min(p[0] for p in field), min(p[2] for p in field), max(p[0] for p in field), max(p[2] for p in field)],
            'palette': palette, 'blocks': [[*p, indexes[s]] for p, s in sorted(field.items())], 'block_entities': [],
            'commands': [], 'landmarks': [], 'verification_only': verify, 'construction_forbidden': True}


def prepare(home, output):
    home, output = Path(home).absolute(), Path(output).absolute()
    if output.exists() or output.parent != home / 'staging':
        raise UserError('New private source-only staging directory required')
    sealed, sealed_ref = checked(home, SEALED, SEALED_SHA)
    fourteen, fourteen_ref = checked(home, FOURTEEN, FOURTEEN_SHA)
    layout, layout_ref = checked(home, LAYOUT, LAYOUT_SHA)
    specs = {b['id']: b for b in layout['buildings']}
    forbidden = {tuple(r['position']) for r in layout['current_unowned_or_private_BEs_held_in_place']}
    # Preserve all three typed Inn room capsules, not only the two player bed
    # halves: a free native POI is not permission to use a private player's room.
    for room in layout['retained_in_place_private_anchor_Inn_room_capsules']:
        x0, y0, z0, x1, y1, z1 = room['source_support_bounds_xyz']
        forbidden.update((x, y, z) for x in range(x0, x1 + 1) for y in range(y0, y1 + 1) for z in range(z0, z1 + 1))
    anchors = set(map(tuple, layout['private_human_bed_job_anchors_retained_in_place']))
    actual = {r['id']: r for r in sealed['results']}
    config, registry_ref = read(home / 'dashboard/characters/registry.json', 8 * 1024**2)
    profiles = {p['id']: p for p in config['config']['characters']}
    output.mkdir(); sites, held, files = [], [], {}
    for key, premise in PREMISES.items():
        try:
            if premise in actual:
                proof, proof_ref = checked(home, **dict(relative=actual[premise]['actual_complete_native_after']['path'], sha=actual[premise]['actual_complete_native_after']['sha256']))
                op = next(o for o in sealed['actual_operations'] if o['intent']['path'].endswith('-' + premise + '-complete-after.intent.json'))
                intent, _ = checked(home, op['intent']['path'], op['intent']['sha256'])
                source, source_ref = checked(home, intent['plan']['path'], intent['plan']['sha256'])
                if proof.get('failures') != 0 or proof.get('plan_sha256') != source_ref['sha256']:
                    raise UserError('Exact completed native source proof required')
            else:
                source, source_ref, proof_ref = fourteen, fourteen_ref, {'coordinator_current14_proof_required': True}
            field = cells(source)
            columns = set(map(tuple, specs[premise]['actual_building_floor_columns_xz']))
            blocked = forbidden | {p for p in field if (p[0], p[2]) in anchors}
            result = choose(field, columns, ROLES[key][3], blocked); delta = result.pop('delta'); known = result.pop('known')
            if any(field[p] not in AIR for p in delta):
                raise UserError('Fit-out may add only to exact known AIR; preserve every existing object')
            selected = {p: field[p] for p in known}
            for suffix, values, verify in [('AIR-before', {p: field[p] for p in delta}, True),
                                           ('fitout-PROPOSAL', delta, False),
                                           ('HOME-after-VERIFY-ONLY', {p: delta.get(p, s) for p, s in selected.items()}, True)]:
                if values:
                    name = key + '-' + suffix + '.json'; raw = encoded(native_plan(source, values, 'SOURCE ONLY ' + key + ' ' + suffix, verify))
                    (output / name).write_bytes(raw); files[name] = {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
            original = profiles[key]
            origin = result['habitat']['bed_path'][0]
            decor = [{'position': list(p), 'source_state': s} for p, s in sorted(field.items())
                     if (p[0], p[2]) in columns and abs(p[0] - origin[0]) + abs(p[2] - origin[2]) <= 6
                     and abs(p[1] - origin[1]) <= 2 and any(word in s for word in ('chair', 'desk', 'book', 'lantern', 'potted_', 'shelf'))][:12]
            sites.append({'name': 'character-' + key, 'character_id': key, 'display_name': original['name'],
                          'entity': 'minecraft:villager', 'town_site': 'tortuga-' + key,
                          'premise_id': premise, 'premise_name': specs[premise]['name'], **result,
                          'source': source_ref, 'source_native_proof': proof_ref,
                          'fitout_new_blocks': len(delta), 'source_existing_objects_retained': True,
                          'private_anchors_capsules_and_unknown_BE_cells_excluded': True,
                          'retained_room_furnishings': decor,
                          'profile_edits': {'district': {'before': original['district'], 'after': 'tortuga'},
                                            'home_location': {'before': original['home_location'], 'after': specs[premise]['name'] + ' — ' + original['name']}},
                          'visiting_role': original['role'] + (' visiting Tortuga; original backstory and knowledge retained' if original['district'] != 'tortuga' else ''),
                          'native_HOME_job_claims_habitat_spawn_and_gameplay_verified': False})
        except (UserError, KeyError, StopIteration) as error:
            held.append({'id': key, 'premise': premise, 'reason': str(error)})
    report = {'source_only': True, 'format': 'awft-tortuga-cast-sites:1', 'source_city25': sealed_ref,
              'source_city14': fourteen_ref, 'source_layout': layout_ref, 'current_registry_source': registry_ref,
              'sites': sites, 'held': held, 'files': files, 'world_or_runtime_writes': 0,
              'requires_fresh_master_checkpoint_rebinding_and_native_preimage': True,
              'all_ten_gameplay_acceptance': False}
    (output / 'cast-sites-SOURCE-ONLY.json').write_bytes(encoded(report))
    return {'output': str(output), 'candidates': len(sites), 'held': held, 'new_AIR_only_blocks': sum(s['fitout_new_blocks'] for s in sites)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--home', type=Path, required=True); parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(); print(json.dumps(prepare(args.home, args.output), indent=2))
