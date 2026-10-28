"""Compare genuine sampler receipts without promoting partial evidence to a pass."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import statistics
import zipfile
from pathlib import Path

from control_room.common import REPO, UserError, read_json, write_json
from tools.worldgen_refinement import SPACING


def distribution(values):
    values = sorted(values)
    if not values:
        return {'n': 0, 'median': None, 'p95': None, 'max': None}
    return {'n': len(values), 'median': round(statistics.median(values), 3),
            'p95': round(values[math.ceil(len(values)*.95)-1], 3), 'max': round(values[-1], 3)}


def chunk_map(report):
    result = {}
    for chunk in report['chunks']:
        point = tuple(chunk['chunk'])
        if len(point) != 2 or point in result:
            raise UserError('Duplicate or invalid observed chunk coordinate')
        result[point] = chunk
    return result


def starts(report):
    result = {}
    for chunk in report['chunks']:
        for structure in chunk['actual_saved_starts']:
            key = (structure['id'], *structure['start_chunk'])
            if key in result and result[key] != structure:
                raise UserError('Conflicting observations of the same structure start')
            result[key] = structure
    return result


def intersects(a, b):
    return all(a[i] <= b[i+3] and b[i] <= a[i+3] for i in range(3))


def suspicious_piece_overlaps(report):
    structures = sorted(starts(report).items())
    result = []
    for i, (left, a) in enumerate(structures):
        for right, b in structures[i+1:]:
            if not intersects(a['box'], b['box']):
                continue
            if any(intersects(p, q) for p in a['piece_boxes'] for q in b['piece_boxes']):
                result.append({'left': left, 'right': right})
    return result


def registry_changes(before, after):
    old = {row['id']: row for row in before['registry']}
    new = {row['id']: row for row in after['registry']}
    if old.keys() != new.keys():
        raise UserError('Loaded structure-set inventories differ')
    changes = []
    for key in sorted(old):
        if old[key] == new[key]:
            continue
        if key not in SPACING:
            raise UserError('Unexpected native registry change: ' + key)
        expected = copy.deepcopy(old[key])
        p = expected['encoded']['placement']
        if p['spacing'] != SPACING[key][0]:
            raise UserError('Unexpected baseline native spacing: ' + key)
        p['spacing'] = SPACING[key][1]
        if expected != new[key]:
            raise UserError('Native change exceeds the reviewed spacing: ' + key)
        changes.append(key)
    if set(changes) != set(SPACING):
        raise UserError('Not every selected native spacing change was loaded')
    return changes


def check_report(report, arm, phase, class_sha256):
    if (report.get('format') != 'awft-native-worldgen-survey:1' or
        report.get('status') != 'OBSERVATIONS_COMPLETE_NORMAL_STOP_AND_RESTART_STILL_REQUIRED' or
        report.get('arm') != arm or report.get('phase') != phase or
        report.get('qa_class_sha256') != class_sha256):
        raise UserError('Missing, incomplete or differently bound native receipt')
    if (report.get('min_y'), report.get('height')) != (-64, 384):
        raise UserError('Observed dimension height changed')
    if not report.get('seed_sha256'):
        raise UserError('Missing saved-seed binding')


def compare(baseline, updated, baseline_restart, updated_restart, class_sha256):
    reports = [(baseline, 'baseline', 'full'), (updated, 'updated', 'full'),
               (baseline_restart, 'baseline', 'restart'), (updated_restart, 'updated', 'restart')]
    for report, arm, phase in reports:
        check_report(report, arm, phase, class_sha256)
    if len({r['seed_sha256'] for r, _, _ in reports}) != 1:
        raise UserError('A/B or restart seed differs')
    changed = registry_changes(baseline, updated)
    # A restart may not quietly change even a nonselected registry entry.
    if baseline['registry'] != baseline_restart['registry'] or updated['registry'] != updated_restart['registry']:
        raise UserError('Loaded registry changed across restart')
    maps = [chunk_map(r) for r, _, _ in reports]
    if not maps[0] or any(m.keys() != maps[0].keys() for m in maps[1:]):
        raise UserError('A/B and restart workloads must contain the same complete chunk coordinate set')
    arms = {}
    for report, arm, _ in reports[:2]:
        restart = baseline_restart if arm == 'baseline' else updated_restart
        before_chunks, after_chunks = chunk_map(report), chunk_map(restart)
        altered = [p for p in before_chunks if any(before_chunks[p].get(key) != after_chunks[p].get(key)
                   for key in ('block_states_sha256', 'world_surface', 'ocean_floor', 'actual_saved_starts'))]
        counts = {}
        for key in starts(report):
            counts[key[0]] = counts.get(key[0], 0) + 1
        arms[arm] = {'requested_full_chunks': len(before_chunks), 'actual_saved_structure_starts': counts,
            'full_chunk_acquisition_ms': distribution([c['full_chunk_wall_nanoseconds']/1e6 for c in report['chunks']]),
            'observer_processing_ms': distribution([c['observation_processing_nanoseconds']/1e6 for c in report['chunks']]),
            'observed_tick_ms_including_instrumentation': distribution([n/1e6 for n in report['observed_tick_nanoseconds']]),
            'observed_ticks_over_50ms_including_instrumentation': sum(n>50e6 for n in report['observed_tick_nanoseconds']),
            'restart_content_differences_require_review': altered,
            'potential_piece_box_overlaps_require_review': suspicious_piece_overlaps(report)}
    return {'format': 'awft-native-worldgen-comparison:1', 'status': 'MEASURED_REQUIRES_ACCEPTANCE_REVIEW',
        'native_registry_changes': changed, 'arms': arms,
        'unproved': ['Fresh versus preexisting FULL status requires offline pre-generation inventory.',
                    'Normal stop, process/descendant exit and port release require orchestration receipts.',
                    'Biome/landform representativeness requires review of actual coordinates and biomes.',
                    'Piece bounding-box intersections are candidates for block-level inspection, not proven collisions.',
                    'Entrances, terrain cuts and dramatic landmark quality require actual native visual inspection.',
                    'A single instrumented pair does not establish sustained or multiplayer performance.',
                    'Explored-chunk frontier protection and strict DH/SeedGen parity remain separate gates.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('baseline', 'updated', 'baseline-restart', 'updated-restart', 'qa-jar', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    with zipfile.ZipFile(args.qa_jar) as archive:
        raw = archive.read('worldfortwo/worldgenqa/WorldgenSurvey.class')
    result = compare(*(read_json(getattr(args, key)) for key in
        ('baseline', 'updated', 'baseline_restart', 'updated_restart')), hashlib.sha256(raw).hexdigest())
    output = args.output.resolve()
    if output.exists() or not output.is_relative_to(REPO / 'evidence/worldgen'):
        parser.error('Use a new result file under this checkout/evidence/worldgen')
    from tools.playtest import guard
    guard(8 * 1024**2, 0)
    write_json(output, result)
    print(json.dumps({'output': str(output), 'status': result['status']}))


if __name__ == '__main__':
    main()
