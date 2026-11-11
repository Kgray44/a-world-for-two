"""Prepare the existing rail's native-GUI repair, without mill/tube recovery.

Immutable saved inputs only. Outputs are verification/source artifacts, never a
placement admission, stock authoring, NativeJournal terminal or live command.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path
import re

from control_room.common import REPO, UserError, digest, utcnow
from tools.artistic_quay_prototype import bounded, write_bundle
from tools.playtest import guard
from tools.settlement_attractions import BackupWorld
from tools.transport_conductor_overlay import BURNERS, CONTROLS, SEATS, verify_api
from tools.transport_saved_inputs import verification_plan

MIB = 1024**2
MILL = (1332, 71, -994)
HALT = (1332, 71, -942)
OLD_BOGEYS = ((1336, 70, -992), (1336, 70, -986))
NEW_BOGEYS = ((1336, 70, -993), (1336, 70, -987))
BOGEY = 'create:small_bogey[axis=z,waterlogged=false]'
AIR = 'minecraft:air'
FRAME = frozenset((x, y, z) for x in range(1335, 1338)
                  for y in range(70, 76) for z in range(-993, -984))
SHELL = frozenset((x, y, z) for x in range(1334, 1339)
                  for y in range(69, 77) for z in range(-994, -983))
TRACKS = frozenset((1336, 69, z) for z in range(-997, -935))
ENDS = frozenset(((1336, 69, -998), (1336, 69, -935)))
TARGETS = SHELL | TRACKS | ENDS | {MILL, HALT}


def _track(state):
    key = state.split('[', 1)[0]
    return key == 'create:track' or key.startswith('railways:track_')


def derive(registry, states, checkpoint_sha):
    """Closed rail-only masks; unknown/human changes are held, never normalized."""
    if set(states) != TARGETS or len(states) != 495:
        raise UserError('Exactly495 existing rail/frame/shell/station/termination targets required')
    if not re.fullmatch('[a-f0-9]{64}', checkpoint_sha):
        raise UserError('Exact immutable source checkpoint SHA required')
    if any(not isinstance(state, str) for state in states.values()):
        raise UserError('Actual saved block states required')
    if any(not _track(states[p]) for p in TRACKS) or any(_track(states[p]) for p in ENDS):
        raise UserError('Retain the62 existing tracks and both actual non-track termination cells')
    if any(states[p] != BOGEY for p in OLD_BOGEYS):
        raise UserError('Original bogeys changed; preserve actual human work and requalify this batch')
    if any(states[p] != AIR for p in NEW_BOGEYS + BURNERS):
        raise UserError('New bogey/conductor cells are occupied; no destructive native placement')
    if any(states[p] != 'create:blue_seat[waterlogged=false]' for p in SEATS):
        raise UserError('Preserve all three original seats')
    conductor = {}
    for p, old, new in zip(CONTROLS, ('north', 'south'), ('south', 'north')):
        expected = f'create:controls[facing={old},open=false,virtual=false,waterlogged=false]'
        if states[p] != expected:
            raise UserError('Controls changed; preserve native configuration and requalify')
        conductor[p] = f'create:controls[facing={new},open=false,virtual=false,waterlogged=false]'
    for p, facing in zip(BURNERS, ('north', 'south')):
        conductor[p] = f'create:blaze_burner[blaze=smouldering,facing={facing}]'
    for p in (MILL, HALT):
        if not states[p].startswith('create:track_station[') or 'assembling=false' not in states[p]:
            raise UserError('Existing non-assembling station state changed; no train/point replacement')
    corrected = {p: AIR for p in OLD_BOGEYS}
    corrected.update({p: BOGEY for p in NEW_BOGEYS})
    ready = dict(states)
    ready.update(corrected)
    ready.update(conductor)
    ready[MILL] = ready[MILL].replace('assembling=false', 'assembling=true')
    def plan(values, name):
        return verification_plan(registry, values, checkpoint_sha, name)
    return {
        'rail-before-VERIFY-ONLY.json': plan(states, 'VERIFY ONLY saved rail-only495; no mill/tube preimage'),
        'bogey-repair-after-GUI-VERIFY-ONLY.json': plan(corrected, 'VERIFY ONLY ordinary GUI repair; NEVER generic placement or BE replay'),
        'conductor-after-GUI-VERIFY-ONLY.json': plan(conductor, 'VERIFY ONLY real filled-item placement and native control rotation'),
        'assembly-ready-after-GUI-VERIFY-ONLY.json': plan(ready, 'VERIFY ONLY corrected rail after genuine UI naming/mode/material work'),
        'native-GUI-repair.json': {
            'format': 'awft-rail-only-native-gui-repair:1',
            'native_actions': 0, 'world_writes': 0, 'world_write_authority': False,
            'live_human_editing_authorized': False,
            'native_block_entity_NBT_replay': False,
            'legacy7941_resume_replayed': False,
            'legacy_isValidBogeyOffset_is_existing_bogey_check': False,
            'source_original_target_distances': [2, 8],
            'source_original_native_scanner_offsets': [1, 7],
            'corrected_native_scanner_offsets': [0, 6],
            'native_first_bogey_offset_required': 0,
            'pinned_station_class_sha256': '5dba7eecfc4e58e38d0e84483934e8742ef9f6ef81f58a15ed2754242bd0435f',
            'pinned_small_bogey_loot_sha256': '35577fdea8952a46407aa902001dbdaf5eba0ed61ddee68fec6a745dbcb003a3',
            'bogey_native_GUI_operations': [
                {'remove_actual_bogey': list(old), 'place_on_actual_track': [new[0], 69, new[2]],
                 'resulting_upright_bogey': list(new)}
                for old, new in zip(OLD_BOGEYS, NEW_BOGEYS)
            ],
            'material_custody': {
                'ordinary_survival_removal_expected_casings': 2,
                'actual_collected_casings_required': 2,
                'actual_native_placement_debits_required': 2,
                'creative_break_or_placement_proves_debit': False,
                'global_loot_modifiers_and_actual_counts_require_observation': True,
                'preserve_actual_bogey_style_and_nonposition_BE_state': True,
                'genuine_filled_burner_debit_required': 2,
                'no_stock_or_recipe_product_created_by_package': True,
            },
            'assembly': {
                'station': list(MILL), 'existing_target': [1336, 69, -994],
                'direction': 'south', 'station_target_or_UUID_changed': False,
                'station_names_required': ['Copper Wren Mill', 'Rosewater Orchard Halt'],
                'entry_mode': 'genuine normal station UI; no null/fake ServerPlayer or forged internal fields',
                'track_click_pitch': 'nonnegative/downward for upright Y70; negative pitch may place below track',
                'new_Y70_targets_must_be_actual_AIR': True,
                'native_trackClicked_destroys_occupied_destination': True,
                'glue_box_inclusive': [[1335, 70, -993], [1337, 75, -985]],
                'ordinary_UI_assembly_required': True,
                'runtime_readiness': 'actual new train UUID, one carriage/two bogeys/three seats/both conductors/parked station; source is not a result',
            },
            'human_boundary': {
                'tube_and_zipline_cells_targeted': 0,
                'mill_inputs_power_or_inventories_targeted': 0,
                'rail_chunks_shared_with_human_network': True,
                'handover_gate': 'Human ends editing; master preserves fresh checkpoint and authenticates actual rail/BE/item state before new exclusive execution lease',
                'changed_bogeys_controls_stations_or_occupied_AIR': 'Hold only this batch, preserve actual human modifications, inspect and reconcile; never replay old source',
            },
            'acceptance': {k: 'UNVERIFIED' for k in ('native_assembly', 'movement', 'boarding', 'schedule', 'multiplayer', 'restart', 'performance', 'owner')},
        },
    }


def prepare(home, checkpoint_id, checkpoint_sha, output, create_jar):
    home = Path(home).resolve()
    output = Path(output).absolute()
    local = (REPO / '.local').absolute()
    if (home.parent != Path(r'D:\A World for Two\staging\world-tests')
            or output.parent != local or output.exists() or output.is_symlink() or output.is_junction()
            or local.resolve() != local):
        raise UserError('Exact private source home and new immediate owned.local output required')
    if not re.fullmatch(r'\d{8}T\d{6}Z-[a-f0-9]{6}', checkpoint_id):
        raise UserError('Explicit retained source checkpoint required')
    receipt = bounded(home / 'backups' / (checkpoint_id + '.json'))
    if receipt.get('integrity') != 'verified' or receipt.get('sha256') != checkpoint_sha:
        raise UserError('Actual verified retained archive identity differs')
    registry = bounded(home / 'dashboard/settlement/registry.json', 16 * MIB)
    if Path(registry['world_path']).resolve() != home / 'world/RosewaterArtistic':
        raise UserError('Exact construction-world source identity required')
    api = verify_api(create_jar)
    reserve = guard(8 * MIB, 0)
    snapshot = BackupWorld(home, {'id': checkpoint_id, 'sha256': checkpoint_sha, 'verified': True}, registry)
    try:
        states = {p: snapshot.state(p) for p in sorted(TARGETS)}
        docs = derive(registry, states, checkpoint_sha)
        protected = sorted(set(states) & snapshot.protected)
        if any(p in snapshot.protected for p in NEW_BOGEYS + BURNERS):
            raise UserError('Preserve an actual BE at an intended AIR destination')
        sources = deepcopy(snapshot.sources)
    finally:
        snapshot.close()
    manifest = {
        'format': 'awft-rail-only-source-package:1', 'created': utcnow(),
        'source_sha256': digest(Path(__file__)), 'checkpoint_id': checkpoint_id,
        'checkpoint_sha256': checkpoint_sha, 'native_API': api,
        'targets': len(states), 'chunks': sorted({(p[0] // 16, p[2] // 16) for p in states}),
        'saved_BE_positions_preserved': [list(p) for p in protected],
        'saved_sources': sources, 'native_actions': 0, 'world_writes': 0,
        'native_proofs_or_markers_created': 0, 'stock_created': 0,
        'human_session_ended': False, 'execution_authorized': False,
        'maximum_source_output_bytes': MIB, 'storage_guard': reserve,
        'scope': 'Train-only source package; saved source is not current native/human acceptance. Both drives remain subject to30GiB monitoring, not an OS quota.',
    }
    encoded = {name: (json.dumps(value, separators=(',', ':')) + '\n').encode()
               for name, value in docs.items()}
    preview = dict(manifest)
    preview['files'] = {name: {'bytes': len(raw), 'sha256': '0' * 64}
                        for name, raw in encoded.items()}
    if sum(map(len, encoded.values())) + len((json.dumps(preview, indent=2) + '\n').encode()) > MIB:
        raise UserError('Rail-only source package exceeds its1MiB output allocation')
    return write_bundle(output, docs, manifest)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('home', 'output', 'create-jar'):
        parser.add_argument('--' + key, type=Path, required=True)
    parser.add_argument('--checkpoint-id', required=True)
    parser.add_argument('--checkpoint-sha', required=True)
    print(json.dumps(prepare(**vars(parser.parse_args())), indent=2))
