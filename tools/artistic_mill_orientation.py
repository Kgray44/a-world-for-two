"""Prepare the exact two-facing Hypertube correction from a stopped checkpoint.

No native command, deployment, world write, BE load or connection is performed.
The full plan is a verification/admission artifact, never a placement operation.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
import zlib

from control_room.common import UserError, digest, read_json
from tools.playtest import guard
from tools.settlement_attractions import BackupWorld, MAX_CHUNK, NBTReader, base, properties

MIB = 1024**2
MAX_OUTPUT = 8*MIB
ORIGINAL_PLAN_SHA = '181e2191572846967c41e77bf5b406d0dddcc484488aa60d6725728ba651b199'
ORIGINAL_MANIFEST_SHA = '4339bb54a05d9c5a478b471db880c7d80dc1f6c0f25081824c7c54b75f49f408'
HYPERTUBE_SHA = '7bdb8979c7ff7d3b29f7a23771b6ae4870a6dcb7ce2e4a3214fdd6059aacace8'
ENTRANCES = {(1331, 71, -991): ('north', 'south'), (1331, 71, -943): ('south', 'north')}
TUBES = tuple((1331, 71, z) for z in (-991, -983, -975, -967, -959, -951, -943))
VERSION_KEYS = {'Connection_version', 'ConnectionTo_version', 'ConnectionFrom_version'}


def encoded(document):
    return (json.dumps(document, ensure_ascii=False, separators=(',', ':'))+'\n').encode('utf-8')


def sha_document(document):
    return hashlib.sha256(encoded(document)).hexdigest()


def replace_facing(state, expected, replacement):
    fields = properties(state)
    if base(state) != 'create_hypertube:hypertube_entrance' or fields.get('facing') != expected:
        raise UserError('Exact original entrance block and facing required')
    fields['facing'] = replacement
    return base(state)+'['+','.join(k+'='+str(v) for k, v in sorted(fields.items()))+']'


def check_empty_tubes(plan, saved_states, saved_entities):
    authored = {tuple(row[:3]): plan['palette'][row[3]] for row in plan['blocks']}
    witnesses = []
    for pos in TUBES:
        expected = authored.get(pos)
        actual = saved_states.get(pos)
        if expected is None or actual is None or base(actual) != base(expected):
            raise UserError('Saved native tube block identity differs: '+str(pos))
        fields, planned = properties(actual), properties(expected)
        if any(fields.get(k) != v for k, v in planned.items()):
            raise UserError('Saved native tube state differs from original R2: '+str(pos))
        # Native derived states are not authored into R2. Refuse active/unknown
        # values rather than treating an unobserved connection as an empty face.
        defaults = {'connected': 'false', 'has_block_in_front': 'false', 'open': 'false', 'power': '0'}
        if any(k not in defaults or v != defaults[k] for k, v in fields.items() if k not in planned):
            raise UserError('Unknown or active native derived tube state: '+str(pos))
        rows = saved_entities.get(pos, [])
        expected_id = 'create_hypertube:hypertube_entrance_entity' if pos in ENTRANCES else 'create_hypertube:hypertube_entity'
        if len(rows) != 1 or rows[0].get('id') != expected_id:
            raise UserError('One exact native tube BE is required: '+str(pos))
        tag = rows[0]
        if tuple(tag.get(k) for k in ('x', 'y', 'z')) != pos:
            raise UserError('Native tube BE coordinates differ')
        for key, value in tag.items():
            if 'connection' in key.lower() and (key not in VERSION_KEYS or value != 1):
                raise UserError('Preserve existing, unknown or foreign native tube connection: '+str(pos)+' '+key)
        speed = tag.get('Speed')
        if type(speed) not in (int, float) or not math.isfinite(speed) or speed != 0:
            raise UserError('A stopped native tube is required before orientation correction')
        witnesses.append({'position': list(pos), 'saved_state': actual, 'block_entity_id': expected_id,
                          'native_connection_payloads': 0, 'native_speed': speed,
                          'saved_block_entity_sha256': hashlib.sha256(json.dumps(tag, sort_keys=True, separators=(',', ':')).encode()).hexdigest()})
    return witnesses


def corrected_documents(plan, manifest, checkpoint, saved_states, saved_entities, source_sha):
    """Pure correction: only two state facings change; no BE/inventory replay."""
    if manifest['plan_sha256'] != ORIGINAL_PLAN_SHA or manifest['placements'] != len(plan['blocks']):
        raise UserError('Original R2 manifest/plan binding differs')
    if manifest.get('commands') != 0 or plan.get('commands') != []:
        raise UserError('This correction cannot admit construction commands')
    witnesses = check_empty_tubes(plan, saved_states, saved_entities)
    corrected = copy.deepcopy(plan)
    corrected['backup_sha256'] = checkpoint['sha256']
    changed = []
    for row in corrected['blocks']:
        pos = tuple(row[:3])
        if pos not in ENTRANCES:
            continue
        old_face, new_face = ENTRANCES[pos]
        before = plan['palette'][row[3]]
        after = replace_facing(before, old_face, new_face)
        if after not in corrected['palette']:
            corrected['palette'].append(after)
        row[3] = corrected['palette'].index(after)
        changed.append({'position': list(pos), 'before': before, 'after': after})
    if len(changed) != 2 or corrected['block_entities'] != plan['block_entities']:
        raise UserError('Correction must preserve every original block entity and change exactly two facings')
    # Metadata explicitly prevents confusing the complete admission artifact with
    # the separately emitted two-cell placement delta (which loads no BE data).
    corrected['validation'] = 'VERIFY ONLY - exact original R2 with two entrance facings corrected; never place this full plan'
    before_states = {pos: saved_states[pos] for pos in ENTRANCES}
    after_states = {pos: replace_facing(saved_states[pos], *ENTRANCES[pos]) for pos in ENTRANCES}
    def small(states, name):
        palette = sorted(set(states.values()))
        return {'format': plan['format'], 'name': name, 'created': plan['created'], 'seed': plan['seed'],
                'world_path': plan['world_path'], 'backup_sha256': checkpoint['sha256'],
                'bounds': [1331, -991, 1331, -943], 'palette': palette,
                'blocks': [[*pos, palette.index(value)] for pos, value in sorted(states.items())],
                'block_entities': [], 'commands': [], 'landmarks': [],
                'validation': 'STAGED ONLY; parent must verify exact preimage then place only the two-cell delta; native BE connections must remain empty'}
    before = small(before_states, 'VERIFY ONLY - two original stopped entrance facings')
    delta = small(after_states, 'PLACE ONLY TWO CELLS - native Hypertube entrance facing correction; no BE loads')
    updated = copy.deepcopy(manifest)
    updated['plan_sha256'] = sha_document(corrected)
    updated['checkpoint_id'] = checkpoint['id']
    updated['checkpoint_sha256'] = checkpoint['sha256']
    updated['status'] = 'CORRECTION STAGED ONLY - native two-cell preimage/place/full verification and commissioning pending'
    updated['orientation_correction'] = {
        'format': 'awft-mill-orientation:1', 'source_sha256': source_sha,
        'original_plan_sha256': ORIGINAL_PLAN_SHA, 'original_manifest_sha256': ORIGINAL_MANIFEST_SHA,
        'original_checkpoint_id': manifest['checkpoint_id'], 'original_checkpoint_sha256': manifest['checkpoint_sha256'],
        'historical_before_sha256_unchanged': manifest['before_sha256'],
        'checkpoint_id': checkpoint['id'], 'checkpoint_sha256': checkpoint['sha256'],
        'before_sha256': sha_document(before), 'delta_sha256': sha_document(delta),
        'changes': changed, 'saved_native_tubes': witnesses,
        'derivation': 'Pinned 0.6.0 HyperEntranceBlockEntity.getFacesConnectable exposes its FACING; the north-to-south six-span spine requires south/north entrance facings respectively',
        'hypertube_jar_sha256': HYPERTUBE_SHA, 'preserved': 'All original systems, non-facing block states, block entities, inventories, commands and historical receipts; no connection data is invented',
        'placement_scope': 'Only entrance-facing-delta.json may be placed; full mill-quarter.json is verification/admission only'}
    if updated['systems'] != manifest['systems']:
        raise UserError('Original systems changed')
    return {'native-before.json': before, 'entrance-facing-delta.json': delta,
            'mill-quarter.json': corrected, 'manifest.json': updated}


def saved_chunk(snapshot, pos):
    cx, cz = pos[0]//16, pos[2]//16
    snapshot.chunk(cx, cz)  # Existing bounded reader authenticates region/header.
    raw = snapshot.regions[cx//32, cz//32]
    head = ((cz & 31)*32+(cx & 31))*4
    offset = (int.from_bytes(raw[head:head+4], 'big') >> 8)*4096
    length = int.from_bytes(raw[offset:offset+4], 'big')
    mode, packed = raw[offset+4], raw[offset+5:offset+4+length]
    if mode == 3:
        decoded = packed
    else:
        decoder = zlib.decompressobj(31 if mode == 1 else 15)
        decoded = decoder.decompress(packed, MAX_CHUNK+1)
        if decoder.unconsumed_tail or not decoder.eof:
            raise UserError('Saved chunk decompression is truncated or exceeds its bound')
    if len(decoded) > MAX_CHUNK:
        raise UserError('Saved chunk exceeds the finite NBT bound')
    return NBTReader(decoded).read()


def prepare(home, original, registry_path, checkpoint_id, checkpoint_sha, output):
    home, original, output = map(lambda p: Path(p).resolve(), (home, original, output))
    if (not home.is_relative_to(Path(r'D:\A World for Two\staging\world-tests'))
            or not original.is_relative_to(home/'staging') or not output.is_relative_to(home/'staging') or output.exists()):
        raise UserError('Use original artistic staging inputs and a new unique output directory')
    admission = guard(4*MIB, MAX_OUTPUT)
    plan_path, manifest_path = original/'mill-quarter.json', original/'manifest.json'
    for path, expected in ((plan_path, ORIGINAL_PLAN_SHA), (manifest_path, ORIGINAL_MANIFEST_SHA)):
        if not 0 < path.stat().st_size <= 2*MIB or digest(path) != expected:
            raise UserError('Immutable original R2 artifact differs')
    checkpoint = read_json(home/'dashboard/settlement/backup-receipt.json')
    if checkpoint.get('verified') is not True or checkpoint.get('id') != checkpoint_id or checkpoint.get('sha256') != checkpoint_sha:
        raise UserError('Exact current parent-reviewed stopped checkpoint required')
    registry = read_json(registry_path)
    plan, manifest = read_json(plan_path), read_json(manifest_path)
    if any(str(plan[k]) != str(registry[k]) for k in ('seed', 'world_path')):
        raise UserError('Original plan and native registry world identity differ')
    jar = home/'server/mods/create_hypertube-0.6.0-NEOFORGE.jar'
    if digest(jar) != HYPERTUBE_SHA:
        raise UserError('The native Hypertube API artifact differs')
    snapshot = BackupWorld(home, checkpoint, registry)
    try:
        documents, states, entities = {}, {}, {}
        for pos in TUBES:
            states[pos] = snapshot.state(pos)
            key = pos[0]//16, pos[2]//16
            if key not in documents:
                documents[key] = saved_chunk(snapshot, pos)
            entities[pos] = [row for row in documents[key].get('block_entities', [])
                             if tuple(row.get(k) for k in ('x', 'y', 'z')) == pos]
        result = corrected_documents(plan, manifest, checkpoint, states, entities, digest(Path(__file__)))
        result['manifest.json']['orientation_correction']['saved_sources'] = snapshot.sources
    finally:
        snapshot.close()
    raw = {name: encoded(doc) for name, doc in result.items()}
    proof = {'format': 'awft-mill-orientation-proof:1', 'checkpoint_id': checkpoint_id,
             'checkpoint_sha256': checkpoint_sha, 'reserve_guard': admission,
             'files': {name: {'sha256': hashlib.sha256(value).hexdigest(), 'bytes': len(value)} for name, value in raw.items()},
             'changed_block_positions': 2, 'saved_native_tubes_checked': 7, 'saved_native_connection_payloads': 0,
             'world_mutated': False, 'native_actions': False,
             'next_gate': 'Parent native two-cell preimage verification, two-cell placement, full corrected verification and fresh exact commissioning admission'}
    raw['correction-receipt.json'] = encoded(proof)
    if sum(map(len, raw.values())) > MAX_OUTPUT:
        raise UserError('Correction output exceeds its finite allocation')
    output.mkdir(parents=True, exist_ok=False)
    for name, value in raw.items():
        (output/name).write_bytes(value)
    return {'output': str(output), **proof}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--home', type=Path, required=True)
    parser.add_argument('--original', type=Path, required=True)
    parser.add_argument('--registry', dest='registry_path', type=Path, required=True)
    parser.add_argument('--checkpoint-id', required=True)
    parser.add_argument('--checkpoint-sha', required=True)
    parser.add_argument('--output', type=Path, required=True)
    print(json.dumps(prepare(**vars(parser.parse_args())), indent=2))
