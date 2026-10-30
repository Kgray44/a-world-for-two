"""Pair genuine cable BEFORE/current FULL receipts into a review-only source set.

This tool never creates a native request in the dashboard, runs its returned argv,
issues a command, edits a save or turns a saved-state study into a native proof.
The master may run the existing gated R4 producer after reviewing the output.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re

from control_room.common import UserError, digest, utcnow
from tools.artistic_bridge_refinement import flatten
from tools.artistic_chain_route_request_r4 import clean_geometry_receipt
from tools.artistic_engineering import native_proof_times
from tools.artistic_quay_prototype import bounded, context, write_bundle
from tools.playtest import guard
from tools.transport_saved_inputs import BEFORE_SHA, HISTORICAL_SHA, ORIGINAL, _member

MIB = 1024**2
ORIGINAL_BEFORE = 'dashboard/settlement/settlement-result-8ae41c5a-3498-43c1-994b-7cebaf584d46.json'
ORIGINAL_BEFORE_SHA = 'e1d3174624d7ff71f41dc26820884be8259282075a5b32e1b65cc93fd6d73296'


def native_terminal(home, path):
    path = Path(path).resolve()
    if path.parent != home/'dashboard/settlement' or not re.fullmatch(
            r'settlement-result-[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}\.json', path.name):
        raise UserError('Use the actual canonical native terminal in the owned dashboard')
    bounded(path, 512*1024)
    return path


def bind(home, inputs, inputs_sha, study, study_sha, native_full, native_body, output):
    reserve = guard(0, 16*MIB)
    home, output, current, registry = context(home, output)
    inputs, study = Path(inputs).resolve(), Path(study).resolve()
    if inputs.parent != home/'staging' or study.parent != home/'staging':
        raise UserError('Owned immediate source folders required')
    manifest, readiness = bounded(inputs/'manifest.json'), bounded(study/'manifest.json')
    if digest(inputs/'manifest.json') != inputs_sha or digest(study/'manifest.json') != study_sha:
        raise UserError('Exact supplied source manifest digests required')
    if manifest.get('format') != 'awft-transport-saved-inputs:1' or manifest.get('historical_clear') is not True or manifest.get('current_clear') is not True or manifest.get('historical_body_air') != 5607 or manifest.get('current_body_air') != 5607:
        raise UserError('Both complete historical/current saved body qualifications required')
    if any(document.get('checkpoint_sha256') != current['sha256'] for document in (manifest, readiness)) or readiness.get('actual_saved_FULL') != 217 or readiness.get('unknown_saved_chunks') != 0 or readiness.get('saved_chain_knots') != 0:
        raise UserError('Current unchanged checkpoint,217savedFULL and zero saved knots required')
    full_name = 'zipline-current1163-VERIFY-ONLY.json'
    full = _member(inputs, manifest, full_name)
    body_name = 'zipline-current-body-VERIFY-ONLY.json'
    body = _member(inputs, manifest, body_name)
    physical = _member(inputs, manifest, 'physical-frame-source-e55-REQUALIFIED.json')
    before_path = home/ORIGINAL/'physical1163-before-VERIFY-ONLY.json'
    before = bounded(before_path)
    if digest(before_path) != BEFORE_SHA or before.get('backup_sha256') != HISTORICAL_SHA or physical.get('checkpoint_sha256') != HISTORICAL_SHA:
        raise UserError('Preserve genuine original e55 BEFORE/body baseline')
    if (set(flatten(before)) != set(flatten(full)) or len(flatten(full)) != 1163
            or full.get('backup_sha256') != current['sha256'] or full.get('construction_forbidden') is not True
            or full.get('commands') != [] or full.get('block_entities') != []
            or full.get('world_path') != registry['world_path'] or full.get('seed') != registry['seed']):
        raise UserError('Exact current placement-forbidden1163 target set/world required')
    if len(flatten(body)) != 5607 or body.get('backup_sha256') != current['sha256'] or body.get('construction_forbidden') is not True or body.get('commands') != [] or body.get('block_entities') != [] or body.get('world_path') != registry['world_path'] or body.get('seed') != registry['seed'] or any(state.split('[',1)[0] not in ('minecraft:air','minecraft:cave_air','minecraft:void_air') for state in flatten(body).values()):
        raise UserError('Complete current placement-forbidden5607 body field required')
    def reference(path):
        path = Path(path).resolve()
        bounded(path, 2*MIB)
        if not path.is_relative_to(home):
            raise UserError('Referenced source escaped the owned home')
        return {'path': path.relative_to(home).as_posix(), 'bytes': path.stat().st_size, 'sha256': digest(path)}
    old_terminal = native_terminal(home, home/ORIGINAL_BEFORE)
    new_terminal = native_terminal(home, native_full)
    body_terminal = native_terminal(home, native_body)
    if digest(old_terminal) != ORIGINAL_BEFORE_SHA:
        raise UserError('Exact original actual native BEFORE terminal changed')
    pair = {'before': reference(before_path), 'native_before': reference(old_terminal),
            'full': reference(inputs/full_name), 'native_full': reference(new_terminal)}
    old_proof = clean_geometry_receipt(home, pair['native_before'], pair['before'], 1163, False)
    new_proof = clean_geometry_receipt(home, pair['native_full'], pair['full'], 1163, True)
    body_ref, body_receipt = reference(inputs/body_name), reference(body_terminal)
    body_proof = clean_geometry_receipt(home, body_receipt, body_ref, 5607, True)
    if native_proof_times(old_proof)[1] > native_proof_times(new_proof)[0]:
        raise UserError('Current FULL cannot predate genuine original BEFORE')
    if native_proof_times(old_proof)[1] > native_proof_times(body_proof)[0]:
        raise UserError('Current body proof cannot predate genuine original BEFORE')
    # These argv are deliberately not executed. Existing R4 prepare rechecks the
    # actual installed classes/JARs/configs and creates its master-owned request.
    argv = ['python', '-B', '-m', 'tools.artistic_chain_route_request_r4', 'prepare',
            '--home', str(home), '--study-folder', str(study), '--study-sha', study_sha,
            '--physical-frame', str(inputs/'physical-frame-source-e55-REQUALIFIED.json'),
            '--geometry-sets', str(output/'geometry-sets.json'), '--operation', 'prepare-create',
            '--output', str(home/'staging'/('transport-chain-native-request-'+digest(new_terminal)[:16]))]
    if bounded(home/'dashboard/settlement/backup-receipt.json')['sha256'] != current['sha256']:
        raise UserError('Checkpoint advanced during receipt binding')
    return write_bundle(output, {'geometry-sets.json': [pair], 'master-review-invocation.json': {
        'argv': argv, 'executed': False, 'requires': 'Master exclusive runtime/write window and actual current stock/component readback'}},
        {'format': 'awft-transport-chain-paired-source:1', 'created': utcnow(),
         'source_sha256': digest(Path(__file__)), 'checkpoint_sha256': current['sha256'],
         'inputs_manifest_sha256': inputs_sha, 'study_manifest_sha256': study_sha,
         'historical_native_before_sha256': ORIGINAL_BEFORE_SHA, 'actual_native_full_sha256': digest(new_terminal),
         'actual_native_body': body_receipt, 'current_body_plan': body_ref,
         'native_requests_created': 0, 'native_actions': 0, 'world_writes': 0, 'storage_guard': reserve})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('home','inputs','study','native-full','native-body','output'):
        parser.add_argument('--'+key, type=Path, required=True)
    parser.add_argument('--inputs-sha', required=True)
    parser.add_argument('--study-sha', required=True)
    args = parser.parse_args()
    print(json.dumps(bind(args.home,args.inputs,args.inputs_sha,args.study,args.study_sha,args.native_full,args.native_body,args.output),indent=2))
