"""Two existing intake states and normal neighbor completion, never PLACE.

Private proposals only. A genuine fresh native BEFORE2 is mandatory before the
parent can admit normal settling. No server command or live-world action runs.
"""
from __future__ import annotations
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path

from control_room.common import REPO, UserError, digest, utcnow
from tools.artistic_bridge_refinement import flatten
from tools.artistic_fountain_centerpiece import block_entities
from tools.artistic_fountain_runoff_cleanup import CHECKPOINT, authority
from tools.artistic_quay_prototype import bounded, context, fresh_proof, member, same_world, write_bundle
from tools.artistic_spawn_plaza import payload
from tools.playtest import guard
from tools.settlement_attractions import BackupWorld

MIB = 1024**2
INTAKE = (1139, 65, -1129)
INPUT_PIPE = (1139, 66, -1129)
EXPECTED = {INTAKE: 'minecraft:water[level=0]',
    INPUT_PIPE: 'create:fluid_pipe[down=true,east=true,north=false,south=false,up=false,waterlogged=false,west=false]'}
SETTLE_SOURCE = REPO/'compat/control-bridge/src/worldfortwo/bridge/SettlementSupport.java'


def exact_pair(observed, protected):
    if observed != EXPECTED:
        raise UserError('Only the exact existing source water0 and complete input-pipe state are admitted')
    if INTAKE in protected or INPUT_PIPE not in protected:
        raise UserError('Preserve the actual water/no-BE and retained input-pipe BE topology')
    return dict(observed)


def prepare(home, output):
    reserve = guard(2*MIB, 8*MIB)
    home, output, current, registry = context(home, output)
    if (current['id'], current['sha256']) != CHECKPOINT:
        raise UserError('Exact e55 stopped checkpoint required; never silently rebind')
    authority(home, registry)
    snapshot = BackupWorld(home, current, registry)
    try:
        observed = exact_pair({p: snapshot.state(p) for p in EXPECTED}, snapshot.protected)
        tags = block_entities(snapshot, set(EXPECTED))
        if set(tags) != {INPUT_PIPE}:
            raise UserError('Preserve every saved BE; only the existing input-pipe BE is expected')
        be_digest = hashlib.sha256(json.dumps(tags[INPUT_PIPE], sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        sources = deepcopy(snapshot.sources)
    finally:
        snapshot.close()
    before = payload(registry, current['sha256'], observed,
        'VERIFY ONLY exact existing intake and input-pipe BEFORE normal neighbor completion', before=True)
    pending = deepcopy(before)
    pending.update(name='PENDING NATIVE BEFORE2: NORMAL SETTLE ONLY existing intake pair; never PLACE',
                   requires_fresh_native_before=True)
    after = deepcopy(before);after['name'] = 'VERIFY ONLY unchanged two intake states after ordinary neighbor completion'
    return write_bundle(output, {'before-two-VERIFY-ONLY.json': before,
        'intake-two-NORMAL-SETTLE-PENDING-NATIVE.json': pending, 'after-two-VERIFY-ONLY.json': after},
        {'format': 'awft-existing-fountain-intake-normal-neighbors:1', 'created': utcnow(),
         'source_sha256': digest(Path(__file__)), 'checkpoint_id': current['id'], 'checkpoint_sha256': current['sha256'],
         'settlement_source_sha256': digest(SETTLE_SOURCE), 'saved_sources': sources,
         'existing_input_pipe_BE_sha256': be_digest, 'input_pipe_BE_replacement_or_NBT_load': False,
         'expected_settle_BE_targets_skipped': 1,
         'normal_notification_path': 'Non-BE source-water target updateNeighborsAt notifies adjacent input-pipe BE through ordinary callbacks; BE target itself is skipped by current helper',
         'block_replacement_or_PLACE_authority': False, 'header_source_feed_piston_control_or_NBT_writes': 0,
         'cache_pressure_fix_or_pumped_function_proved': False, 'native_actions': 0, 'world_writes': 0,
         'storage_guard': reserve,
         'next_gate': 'After owner leaves: genuine current native BEFORE2, bind normal-settle-only2; retain BE-skip result, verify2. After independent runoff2 cleanup, normal stop/new checkpoint, full dry2532 binding and freshly pinned46 real commission'})


def bind(home, prepared, prepared_sha, native_before, output):
    reserve = guard(2*MIB, 8*MIB)
    home, output, current, registry = context(home, output)
    prepared, native_before = Path(prepared).resolve(), Path(native_before).resolve()
    if prepared.parent != home/'staging' or native_before.parent != home/'dashboard/settlement':
        raise UserError('Owned original proposal and genuine settlement receipt required')
    manifest = bounded(prepared/'manifest.json')
    if (digest(prepared/'manifest.json') != prepared_sha
            or manifest.get('format') != 'awft-existing-fountain-intake-normal-neighbors:1'
            or (manifest.get('checkpoint_id'), manifest.get('checkpoint_sha256')) != CHECKPOINT
            or (current['id'], current['sha256']) != CHECKPOINT
            or digest(SETTLE_SOURCE) != manifest['settlement_source_sha256']):
        raise UserError('Exact reviewed source, e55 and unchanged normal-settle implementation required')
    authority(home, registry)
    before = member(prepared, manifest, 'before-two-VERIFY-ONLY.json')
    pending = member(prepared, manifest, 'intake-two-NORMAL-SETTLE-PENDING-NATIVE.json')
    after = member(prepared, manifest, 'after-two-VERIFY-ONLY.json')
    for doc in (before, pending, after):
        same_world(doc, registry)
        if (doc.get('backup_sha256') != CHECKPOINT[1] or flatten(doc) != EXPECTED
                or doc.get('commands') != [] or doc.get('block_entities') != []
                or doc.get('verification_only') is not True or doc.get('construction_forbidden') is not True):
            raise UserError('No PLACE, source replacement, BE/NBT or foreign-target authority is admitted')
    proof, marker = fresh_proof(native_before, digest(prepared/'before-two-VERIFY-ONLY.json'), 2)
    admitted = deepcopy(pending)
    admitted.pop('requires_fresh_native_before', None)
    admitted['name'] = 'ADMITTED NORMAL SETTLE ONLY after actual native BEFORE2: preserve both existing intake states'
    return write_bundle(output, {'intake-two-NORMAL-SETTLE-ONLY.json': admitted,
        'after-two-VERIFY-ONLY.json': after},
        {'format': 'awft-admitted-existing-fountain-intake-normal-neighbors:1', 'created': utcnow(),
         'source_sha256': digest(Path(__file__)), 'checkpoint_id': current['id'], 'checkpoint_sha256': current['sha256'],
         'proposal_relative': prepared.relative_to(home).as_posix(), 'proposal_sha256': prepared_sha,
         'native_before_sha256': digest(native_before), 'native_before_complete_sha256': digest(marker),
         'native_before_finished': proof['finished'], 'normal_settle_targets': 2, 'expected_BE_targets_skipped': 1,
         'PLACE_or_explicit_block_replacement_authority': False, 'block_entity_NBT_loads': 0,
         'cache_pressure_fix_or_pumped_function_proved': False, 'native_actions': 0, 'world_writes': 0,
         'storage_guard': reserve, 'next_gate': 'Root normal-settle-only, verify unchanged2, independent runoff cleanup, normal stop/new checkpoint, dry2532 binding, fresh real commission'})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__);commands = parser.add_subparsers(dest='action', required=True)
    p = commands.add_parser('prepare')
    for name in ('home', 'output'):p.add_argument('--'+name, type=Path, required=True)
    p = commands.add_parser('bind')
    for name in ('home', 'prepared', 'native-before', 'output'):p.add_argument('--'+name, type=Path, required=True)
    p.add_argument('--prepared-sha', required=True);args = parser.parse_args()
    result = (prepare(args.home, args.output) if args.action == 'prepare' else
              bind(args.home, args.prepared, args.prepared_sha, args.native_before, args.output))
    print(json.dumps(result, indent=2))
