"""Exactly two owned non-source runoff cells; source/private artifacts only.

No live-world reads, commands, restart, source-feed/header/control edits or NBT
writes. Future root execution needs its own actual empty-stage BEFORE admission.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import json
import math
from pathlib import Path

from control_room.common import UserError, digest, utcnow
from tools.artistic_bridge_refinement import flatten
from tools.artistic_fountain_centerpiece import block_entities
from tools.artistic_fountain_dry_binding import INTAKE, MARS, NICHE, compare_owned, parts
from tools.artistic_fountain_parking import POSITIONS, classify
from tools.artistic_materials import require_material_rule, require_outdoor_rule
from tools.artistic_quay_prototype import bounded, context, fresh_proof, member, same_world, write_bundle
from tools.artistic_spawn_plaza import AIR, PUMP, WHEEL, payload
from tools.playtest import guard
from tools.settlement_attractions import BackupWorld

MIB = 1024**2
CHECKPOINT = ('20261028T043630Z-e55a8c', '4384206f639659b09b2d332d2eb058241ca6dc15298f3808745025ed85992fac')
AUTHORITY = 'staging/artistic-fountain-r5-ACTUAL-DRY45-1793155163050141000'
AUTHORITY_SHA = '28d03159a83ba4d3f3fa7d7b58e1c559a6698ac2c2c4d447aa34b8e8f7895145'
CANONICAL_SHA = 'ce85c167a6c3e831bdbb33996d17352c6902329858b4f65d8349ac222f1942be'
TARGETS = frozenset(((1145, 67, -1131), (1145, 68, -1131)))
BEFORE_STATE = 'minecraft:water[level=8]'


def exact_runoff(canonical, observed, protected):
    if set(canonical) != set(observed):
        raise UserError('Complete canonical R5 saved field is required')
    if TARGETS & set(protected):
        raise UserError('Preserve every block entity; no cleanup target may contain one')
    if any(canonical[p] != AIR or observed[p] != BEFORE_STATE for p in TARGETS):
        raise UserError('Only these two exact falling non-source water8 states may become canonical AIR')
    for p in set(canonical) - TARGETS:
        # Identical to the existing dry binder: retain real native defaults/
        # joins and only forward copper aging, while every supplied critical
        # orientation, multiblock, fluid and control property remains exact.
        compare_owned(canonical[p], observed[p])
    return {p: observed[p] for p in sorted(TARGETS)}


def authority(home, registry):
    folder = home / AUTHORITY
    original = bounded(folder / 'manifest.json')
    if digest(folder / 'manifest.json') != AUTHORITY_SHA:
        raise UserError('Preserve the original immutable R5 authority manifest')
    plan = member(folder, original, 'plaza.json')
    if digest(folder / 'plaza.json') != CANONICAL_SHA or len(plan['blocks']) != 2532:
        raise UserError('Exact complete canonical 2532-cell R5 source required')
    same_world(plan, registry)
    return original, plan


def prepare(home, output):
    reserve = guard(2*MIB, 8*MIB)
    home, output, current, registry = context(home, output)
    if (current['id'], current['sha256']) != CHECKPOINT:
        raise UserError('This bounded repair is only the exact e55 stopped checkpoint; no silent rebind')
    _, canonical_plan = authority(home, registry)
    canonical = flatten(canonical_plan)
    expected = dict(canonical)
    # A separate actual native placement already restored this original plain
    # extractable pool source. It is retained, never recreated by this delta.
    expected[INTAKE] = 'minecraft:water[level=0]'
    snapshot = BackupWorld(home, current, registry)
    try:
        observed = {p: snapshot.state(p) for p in sorted(canonical)}
        before = exact_runoff(expected, observed, snapshot.protected)
        gate = {p: snapshot.state(p) for p in sorted(POSITIONS)}
        if classify(gate) != 'ALREADY_PARKED':
            raise UserError('Preserve the complete14 already parked actual gate')
        if any(snapshot.state(p) != AIR for p in NICHE):
            raise UserError('Preserve the already drained six lower wheel-niche cells')
        for n in range(3):
            if parts(observed[(1138, 75+n, -1129)]) != (MARS, {'facing': 'west', 'multiblock': str(n), 'waterlogged': 'false'}):
                raise UserError('Preserve every actual native statue part and its critical orientation')
        entities = block_entities(snapshot, set(canonical))
        kinetics = {}
        for p in (WHEEL, PUMP):
            tag = entities.get(p)
            value = None if tag is None else tag.get('Speed')
            if type(value) not in (int, float) or not math.isfinite(value) or value != 0:
                raise UserError('Saved real wheel/pump Speed must remain zero; no kinetic data edits')
            kinetics[','.join(map(str, p))] = {'persisted_Speed': 0, 'native_current_RPM_proved': False}
        if any(p in snapshot.protected for p in POSITIONS - {WHEEL, PUMP}):
            raise UserError('An unexpected gate BE, including a moving piston, must be preserved')
        sources = deepcopy(snapshot.sources)
    finally:
        snapshot.close()
    before_plan = payload(registry, current['sha256'], before,
                          'ACTUAL e55 only two owned falling runoff cells BEFORE', before=True)
    delta = payload(registry, current['sha256'], {p: AIR for p in TARGETS},
                    'PROPOSAL ONLY restore exactly two owned non-source runoff cells to canonical AIR')
    delta['construction_forbidden'] = True
    after = payload(registry, current['sha256'], {p: AIR for p in TARGETS},
                    'VERIFY ONLY exact two canonical AIR cells after owned runoff cleanup', before=True)
    retained_gate = payload(registry, current['sha256'], gate,
                            'RETAIN ONLY complete14 actual already parked dry gate', before=True)
    whole_after = dict(observed);whole_after.update({p: AIR for p in TARGETS})
    whole_before = payload(registry, current['sha256'], observed,
                           'VERIFY ONLY actual stopped full R5 including exactly two falling runoff cells', before=True)
    whole_after_plan = payload(registry, current['sha256'], whole_after,
                               'PROSPECTIVE VERIFY ONLY complete R5 after two AIR cells; not yet an actual dry save', before=True)
    whole_after_plan.update(prospective_only=True, actual_dry_checkpoint=False)
    derivations = [{'pos': list(p), 'authored': canonical[p], 'actual_saved': observed[p],
        'role': ('Retain the separately native-restored plain water0 intake; no write' if p == INTAKE else
                 'Observed current native defaults/joins or forward copper aging retained read-only; not historically canonical')}
        for p in sorted(observed) if p not in TARGETS and observed[p] != canonical[p]]
    checks = {'material': require_material_rule(whole_after, 'Complete retained R5 and exactly two proposed AIR cells'),
              'outdoor': require_outdoor_rule(whole_after, 'Complete observed R5 plaza after two runoff cells')}
    return write_bundle(output, {'before-two-VERIFY-ONLY.json': before_plan,
        'runoff-two-PROPOSAL-ONLY.json': delta, 'after-two-VERIFY-ONLY.json': after,
        'retained-gate14-VERIFY-ONLY.json': retained_gate, 'complete-current-R5-before-VERIFY-ONLY.json': whole_before,
        'complete-R5-prospective-after-VERIFY-ONLY.json': whole_after_plan},
        {'format': 'awft-owned-fountain-two-runoff:1', 'created': utcnow(),
         'source_sha256': digest(Path(__file__)), 'checkpoint_id': current['id'], 'checkpoint_sha256': current['sha256'],
         'canonical_R5': {'manifest_relative': AUTHORITY+'/manifest.json', 'manifest_sha256': AUTHORITY_SHA,
                          'plan_relative': AUTHORITY+'/plaza.json', 'plan_sha256': CANONICAL_SHA, 'cells': 2532},
         'only_unresolved_material_differences': [list(p) for p in sorted(TARGETS)], 'saved_sources': sources,
         'comparison': 'Existing dry-binding compare_owned/CRITICAL; separately restored plain water0 intake retained',
         'retained_actual_saved_derivations': derivations, 'checks': checks,
         'six_lower_niche_cells_preserved_AIR': True, 'all_three_actual_statue_parts_preserved': True,
         'actual_saved_gate': 'ALREADY_PARKED', 'persisted_kinetics': kinetics,
         'retained_block_entities': len(entities), 'block_entity_writes': 0, 'entity_writes': 0,
         'header_source_feed_piston_plug_control_or_NBT_writes': 0,
         'storage_guard': reserve, 'native_actions': 0, 'world_writes': 0,
         'live_entity_clearance_or_empty_server_proved': False,
         'next_gate': 'Root current empty-stage/entity-clear BEFORE2; bind only exact2 AIR; place once, normal settle, verify2+retained14; normal stop/new checkpoint, actual dry2532 binding then freshly pinned46 commission'})


def bind(home, prepared, prepared_sha, native_before, output):
    reserve = guard(2*MIB, 8*MIB)
    home, output, current, registry = context(home, output)
    prepared, native_before = Path(prepared).resolve(), Path(native_before).resolve()
    if prepared.parent != home/'staging' or native_before.parent != home/'dashboard/settlement':
        raise UserError('Owned immutable source and genuine native settlement receipt required')
    source = bounded(prepared/'manifest.json')
    if digest(prepared/'manifest.json') != prepared_sha or source.get('format') != 'awft-owned-fountain-two-runoff:1':
        raise UserError('Exact reviewed two-runoff proposal required')
    if (source.get('checkpoint_id'), source.get('checkpoint_sha256')) != CHECKPOINT or (current['id'], current['sha256']) != CHECKPOINT:
        raise UserError('Preserve exact e55 ownership; a new checkpoint needs a new reviewed proposal')
    authority(home, registry)
    before = member(prepared, source, 'before-two-VERIFY-ONLY.json')
    delta = member(prepared, source, 'runoff-two-PROPOSAL-ONLY.json')
    after = member(prepared, source, 'after-two-VERIFY-ONLY.json')
    retained = member(prepared, source, 'retained-gate14-VERIFY-ONLY.json')
    complete_before = member(prepared, source, 'complete-current-R5-before-VERIFY-ONLY.json')
    complete_after = member(prepared, source, 'complete-R5-prospective-after-VERIFY-ONLY.json')
    for doc in (before, delta, after, retained, complete_before, complete_after):
        same_world(doc, registry)
        if doc.get('backup_sha256') != CHECKPOINT[1] or doc.get('commands') != [] or doc.get('block_entities') != []:
            raise UserError('No source/control/BE/entity or command authority is admitted')
    if (flatten(before) != {p: BEFORE_STATE for p in TARGETS} or flatten(delta) != {p: AIR for p in TARGETS}
            or flatten(after) != flatten(delta) or set(flatten(retained)) != POSITIONS
            or classify(flatten(retained)) != 'ALREADY_PARKED'):
        raise UserError('Exact two falling states, two AIR targets and retained14 gate required')
    if before.get('verification_only') is not True or after.get('verification_only') is not True or delta.get('construction_forbidden') is not True:
        raise UserError('Original proposal must remain forbidden and exact native before/after read-only')
    full_before, full_after = flatten(complete_before), flatten(complete_after)
    if len(full_before) != 2532 or full_after != (full_before | {p: AIR for p in TARGETS}):
        raise UserError('Whole prospective2532 must preserve every observed cell except exactly two AIR targets')
    if complete_after.get('verification_only') is not True or complete_after.get('actual_dry_checkpoint') is not False:
        raise UserError('Prospective complete field is not an actual stopped dry binding')
    proof, marker = fresh_proof(native_before, digest(prepared/'before-two-VERIFY-ONLY.json'), 2)
    admitted = deepcopy(delta);admitted.pop('construction_forbidden')
    admitted['name'] = 'ADMITTED ONCE after actual native BEFORE2: owned non-source runoff only'
    settle = deepcopy(admitted)
    settle.update(name='NORMAL SETTLE ONLY exact admitted two AIR cells', verification_only=True,
                  construction_forbidden=True, block_entities=[])
    return write_bundle(output, {'runoff-two-PLACE-ONCE.json': admitted,
        'runoff-two-NORMAL-SETTLE-ONLY.json': settle, 'after-two-VERIFY-ONLY.json': after,
        'retained-gate14-VERIFY-ONLY.json': retained, 'complete-R5-prospective-after-VERIFY-ONLY.json': complete_after},
        {'format': 'awft-admitted-owned-fountain-two-runoff:1', 'created': utcnow(),
         'source_sha256': digest(Path(__file__)), 'checkpoint_id': current['id'], 'checkpoint_sha256': current['sha256'],
         'prepared_relative': prepared.relative_to(home).as_posix(), 'prepared_sha256': prepared_sha,
         'native_before_sha256': digest(native_before), 'native_before_complete_sha256': digest(marker),
         'native_before_finished': proof['finished'], 'canonical_R5': source['canonical_R5'],
         'targets': 2, 'header_source_feed_piston_plug_control_or_NBT_writes': 0,
         'native_actions': 0, 'world_writes': 0, 'storage_guard': reserve,
         'next_gate': 'Root place/normal-settle/verify; normal stop/new actual dry checkpoint; rebind complete canonical2532 then newly pinned46 commission'})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='action', required=True)
    p = commands.add_parser('prepare')
    for name in ('home', 'output'):p.add_argument('--'+name, type=Path, required=True)
    p = commands.add_parser('bind')
    for name in ('home', 'prepared', 'native-before', 'output'):p.add_argument('--'+name, type=Path, required=True)
    p.add_argument('--prepared-sha', required=True)
    args = parser.parse_args()
    result = (prepare(args.home, args.output) if args.action == 'prepare' else
              bind(args.home, args.prepared, args.prepared_sha, args.native_before, args.output))
    print(json.dumps(result, indent=2))
