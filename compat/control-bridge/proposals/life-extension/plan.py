"""Non-executable LIFE curation plan. No world, native process or ledger writer.

This deliberately does not emit awft-habitat-life-recipe:1 or native requests.
Future integration must read native observations itself, never trust requested
NoAI/owner/profession/spawn-success fields or turn this document into authority.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
GLOBAL_BUDGET = 64


def catalog():
    source = ROOT / 'species-habitats.json'
    raw = source.read_bytes()
    if not 0 < len(raw) <= 256 * 1024:
        raise ValueError('Bounded source species catalog required')
    data = json.loads(raw)
    if data['format'] != 'awft-life-extension-species:1':
        raise ValueError('Wrong proposal format')
    return data


def propose(groups, data=None):
    """Validate only source curation/counts; never assert native habitat acceptance."""
    data = catalog() if data is None else data
    profiles = {row['entity']: row for row in data['species']}
    totals, slots, selected = {}, set(), []
    if not isinstance(groups, list) or not 1 <= len(groups) <= 32:
        raise ValueError('Finite named habitat groups required')
    for group in groups:
        if not isinstance(group, dict) or set(group) != {'slot', 'entity', 'habitat', 'count'}:
            raise ValueError('No coordinates, NBT, owners, tame state, NoAI, profession or native-result fields accepted')
        slot, key, mode, count = (group[k] for k in ('slot', 'entity', 'habitat', 'count'))
        if not isinstance(slot, str) or not re.fullmatch('[a-z][a-z0-9_-]{2,47}', slot) or slot in slots:
            raise ValueError('Distinct stable symbolic habitat slot required')
        slots.add(slot)
        profile = profiles.get(key)
        if profile is None or profile['selection'] != 'candidate_after_native_review':
            raise ValueError('Exact reviewed entity identity required; a category or fairy-like name is insufficient')
        if mode not in profile['habitats']:
            raise ValueError('This species has no reviewed habitat of that kind')
        if type(count) is not int or not 1 <= count <= profile['max_group']:
            raise ValueError('Finite species-appropriate group size required')
        totals[key] = totals.get(key, 0) + count
        if totals[key] > profile['candidate_population_cap']:
            raise ValueError('Species budget exceeded; do not add the old 57-member proposal on top')
        selected.append({**group, 'native_class': profile['native_class'], 'native_category': profile['native_category'],
                         'required_native_gates': profile['required_native_gates']})
    if sum(totals.values()) > GLOBAL_BUDGET:
        raise ValueError('Whole-population planning cap exceeded, including the original four species')
    return {'format': 'awft-life-extension-source-plan:1', 'status': 'SOURCE_PROPOSAL_NOT_A_NATIVE_RECIPE',
            'population_budget': sum(totals.values()), 'whole_population_cap': GLOBAL_BUDGET,
            'includes_original_four_species': True, 'old_R1_population_is_not_additional': True,
            'groups': selected, 'world_coordinates': None, 'UUIDs': None,
            'seed_authorized': False, 'native_spawn_or_behavior_acceptance': False,
            'must_rebind': ['actual final shore-to-cliff habitats', 'final R5 plaza/AIR/plumbing/view mask plus five metres',
                            'post-construction stopped checkpoint', 'native verified per-habitat preimages and event hooks',
                            'complete UUID census and retained population ledger']}


def verify_pins(cache, data=None):
    """Read only the exact selected artifacts; no download, extraction or native launch."""
    data = catalog() if data is None else data
    cache = Path(cache)
    checked = []
    for artifact in data['artifacts']:
        if artifact['kind'] != 'selected_mod':
            continue  # Named vanilla API is separate source evidence, never a mod cache target.
        path = cache / artifact['filename']
        if path.is_symlink() or not path.is_file() or path.stat().st_size != artifact['bytes']:
            raise ValueError('Exact cached selected artifact required: ' + artifact['filename'])
        digest = hashlib.sha512()
        with path.open('rb') as source:
            while part := source.read(1024 * 1024):
                digest.update(part)
        if digest.hexdigest() != artifact['sha512']:
            raise ValueError('Pinned artifact differs: ' + artifact['filename'])
        checked.append(artifact['filename'])
    return {'read_only_selected_artifact_pins': checked, 'native_game_started': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify-pins', type=Path)
    args = parser.parse_args()
    data = catalog()
    result = verify_pins(args.verify_pins, data) if args.verify_pins else propose(data['candidate_groups'], data)
    print(json.dumps(result, indent=2))
