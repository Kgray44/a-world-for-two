"""Compare retained native worldgen evidence without granting generation authority.

Input encodings and seed-bearing effective witnesses stay private. Output contains
only names, difference counts and receipt hashes. No game, registry or cache loads.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re


MAX_DATA = 16 * 1024 * 1024
REGISTRIES = (
    'minecraft:worldgen/biome', 'minecraft:worldgen/placed_feature',
    'minecraft:worldgen/noise', 'minecraft:worldgen/multi_noise_biome_source_parameter_list',
    'minecraft:worldgen/noise_settings', 'minecraft:worldgen/density_function',
)
SIDES = ('server_registry_access', 'client_cached_registry_access')
WITNESS_SIDES = ('actual_server_levels', 'current_selected_client_stems')


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate JSON member in private evidence')
        result[key] = value
    return result


def _json(raw):
    return json.loads(raw, object_pairs_hook=_object,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError('Nonfinite JSON')))


def _read(path, maximum):
    path = Path(path)
    if path.is_symlink() or path.is_junction() or not path.is_file() or path.stat().st_size > maximum:
        raise ValueError('Finite ordinary evidence file required')
    with path.open('rb') as stream:
        raw = stream.read(maximum + 1)
    if len(raw) > maximum:
        raise ValueError('Evidence grew beyond its bound')
    return raw


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _digest(value):
    return isinstance(value, str) and re.fullmatch('[a-f0-9]{64}', value) is not None


def _bound_data(status_path, suffix, byte_field):
    path = Path(status_path)
    status_raw = _read(path, 65536)
    status = _json(status_raw)
    if not isinstance(status, dict):
        raise ValueError('Native status object required')
    if not path.name.endswith(suffix + '.status.json'):
        raise ValueError('Exact native status filename required')
    data_path = path.with_name(path.name.removesuffix('.status.json') + '.jsonl')
    raw = _read(data_path, MAX_DATA)
    if status.get('data_sha256') != _sha(raw) or status.get(byte_field) != len(raw):
        raise ValueError('Native data bytes do not match the retained status receipt')
    rows = [_json(line) for line in raw.splitlines()]
    if not rows or len(rows) > 32784 or any(not isinstance(row, dict) for row in rows):
        raise ValueError('Finite native record set required')
    return status, rows, _sha(status_raw)


def load_fingerprint(path, side):
    status, rows, receipt_sha = _bound_data(path, '.worldgen', 'recorded_data_bytes')
    if status.get('format') != 'awft-worldgen-input-status:1' or status.get('side') != side:
        raise ValueError('Native fingerprint export format/side differs')
    if rows[0].get('format') != 'awft-seedgen-fingerprint-inputs:1' or rows[0].get('side') != side:
        raise ValueError('Native fingerprint header differs')
    if status.get('data_file') != Path(path).name.removesuffix('.status.json') + '.jsonl':
        raise ValueError('Native data filename differs')
    entries, groups, summaries = {}, {}, {}
    for row in rows[1:]:
        record = row.get('record')
        if record in ('registry', 'registry_summary'):
            group = groups if record == 'registry' else summaries
            key = row.get('registry')
            if key not in REGISTRIES or key in group:
                raise ValueError('Unknown/duplicate native registry record')
            group[key] = row
        elif record == 'entry':
            key = (row.get('registry'), row.get('key'))
            if key[0] not in REGISTRIES or not isinstance(key[1], str) or key in entries:
                raise ValueError('Unknown/duplicate native entry')
            if row.get('native_key_sha256') != _sha(key[1].encode()):
                raise ValueError('Native key digest differs')
            if row.get('status') == 'encoded' and (
                    not _digest(row.get('value_sha256')) or not _digest(row.get('native_entry_contribution_sha256'))
                    or row.get('value_hashed_by_native') is not True
                    or type(row.get('value_bytes')) is not int or row['value_bytes'] <= 0):
                raise ValueError('Native encoded-value evidence is incomplete')
            entries[key] = row
        else:
            raise ValueError('Unknown native record type')
    complete = (status.get('complete') is True and set(groups) == set(REGISTRIES)
                and set(summaries) == set(REGISTRIES) and status.get('entries') == len(entries))
    for key, row in summaries.items():
        if row.get('entries') != sum(reg == key for reg, _ in entries):
            raise ValueError('Native registry summary entry count differs')
    clean = (complete and status.get('native_encoding_errors') == 0
             and status.get('native_encoding_exceptions') == 0
             and status.get('encoded_values') == sum(row.get('status') == 'encoded' for row in entries.values())
             and _digest(status.get('diagnostic_input_sha256'))
             and status.get('diagnostic_native_format_prefix') == status['diagnostic_input_sha256'][:16]
             and all(row.get('present') is True for row in groups.values())
             and all(row.get('status') == ('key_only' if key[0] in REGISTRIES[:4] else 'encoded')
                     for key, row in entries.items()))
    return dict(status=status, entries=entries, groups=groups, clean=clean, receipt_sha=receipt_sha,
                original_class=rows[0].get('seedsharing_original_class_sha256'))


def compare_fingerprints(server, client):
    a, b = load_fingerprint(server, SIDES[0]), load_fingerprint(client, SIDES[1])
    different = []
    for key in sorted(a['entries'].keys() | b['entries'].keys()):
        left, right = a['entries'].get(key), b['entries'].get(key)
        fields = ('status', 'native_key_sha256', 'value_sha256', 'value_bytes',
                  'value_hashed_by_native', 'native_entry_contribution_sha256')
        if left is None or right is None or any(left.get(f) != right.get(f) for f in fields):
            different.append({'registry': key[0], 'key': key[1],
                              'difference': 'client_only' if left is None else 'server_only' if right is None else 'native_value_or_status'})
    group_equal = all(a['groups'].get(k) == b['groups'].get(k) for k in REGISTRIES)
    original_equal = _digest(a['original_class']) and a['original_class'] == b['original_class']
    equal = (a['clean'] and b['clean'] and original_equal and group_equal and not different
             and bool(a['status'].get('diagnostic_input_sha256'))
             and a['status'].get('diagnostic_input_sha256') == b['status'].get('diagnostic_input_sha256'))
    return {'format': 'awft-worldgen-comparison:1', 'inputs_equal': bool(equal),
            'strict_parity_proved': False, 'current_native_packet_acceptance_proved': False,
            'clean_complete_exports': a['clean'] and b['clean'],
            'original_seedsharing_class_equal': original_equal,
            'entry_counts': [len(a['entries']), len(b['entries'])],
            'native_format_prefixes': [a['status'].get('diagnostic_native_format_prefix'), b['status'].get('diagnostic_native_format_prefix')],
            'differing_entries': different, 'status_sha256': [a['receipt_sha'], b['receipt_sha']],
            'boundary': 'Diagnostic input comparison only. Current candidate/process/connection provenance, original strict native packet acceptance, effective-state parity and actual terrain remain required.'}


def _unknown(value):
    if isinstance(value, dict):
        return value.get('record') == 'UNKNOWN' or any(_unknown(v) for v in value.values())
    return isinstance(value, list) and any(_unknown(v) for v in value)


def load_effective(path, side):
    status, rows, receipt_sha = _bound_data(path, '.lithostitched', 'bytes')
    if status.get('record') != 'witness_status' or status.get('side') != side:
        raise ValueError('Native effective witness status/side differs')
    if rows[0].get('record') != 'private_effective_witness':
        raise ValueError('Native private witness header differs')
    custody_path = Path(path).with_name(Path(path).name.removesuffix('.status.json') + '.custody.json')
    custody = _json(_read(custody_path, 65536))
    if (custody.get('format') != 'awft-native-effective-custody:1' or custody.get('side') != side
            or custody.get('status_file') != Path(path).name or custody.get('status_sha256') != receipt_sha):
        raise ValueError('Native owner-thread custody does not bind this status')
    records = {}
    for row in rows[1:]:
        kind = row.get('record')
        key = (kind, row.get('dimension') if kind == 'actual_current_generator' else row.get('current_registry_key'))
        if kind not in ('actual_current_generator', 'fast_noise_native_state') or not isinstance(key[1], str) or key in records:
            raise ValueError('Unknown/duplicate effective witness record')
        records[key] = row
    clean = (status.get('complete_export') is True and status.get('effective_state_coverage_complete') is True
             and status.get('unknown_effective_states') == 0 and not _unknown(rows)
             and status.get('observed_input_identities_unchanged') is True
             and custody.get('owner_thread_rechecked') is True
             and custody.get('captured_inputs_still_current') is True and not custody.get('worker_failure_class')
             and any(k[0] == 'actual_current_generator' for k in records))
    return rows[0], records, clean, receipt_sha


def compare_effective(server, client):
    a, ar, ac, ash = load_effective(server, WITNESS_SIDES[0])
    b, br, bc, bsh = load_effective(client, WITNESS_SIDES[1])
    # Private seeds, effective rule order, router state and climate indices are
    # compared in memory. Neither encodings, seed values nor seed hashes escape.
    differences = [{'record': kind, 'key': key} for kind, key in sorted(ar.keys() | br.keys())
                   if ar.get((kind, key)) != br.get((kind, key))]
    return {'format': 'awft-effective-worldgen-comparison:1',
            'witnessed_state_equal': ac and bc and a == b and not differences,
            'clean_current_custody_at_capture': ac and bc,
            'private_header_equal': a == b, 'differing_records': differences,
            'status_sha256': [ash, bsh], 'strict_parity_proved': False,
            'boundary': 'Equality covers exported observations at capture. It does not prove graphs immutable, current packet acceptance or generated terrain fidelity.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('kind', choices=('fingerprint', 'effective'))
    parser.add_argument('--server', required=True, type=Path)
    parser.add_argument('--client', required=True, type=Path)
    args = parser.parse_args()
    result = (compare_fingerprints if args.kind == 'fingerprint' else compare_effective)(args.server, args.client)
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result.get('inputs_equal', result.get('witnessed_state_equal')) else 2)
