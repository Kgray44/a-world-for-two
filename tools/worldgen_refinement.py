"""Build a review-only worldgen overlay, never an installed pack or a world.

The retained candidate.11 density-reduction policy is the baseline. The existing
master proposal changes four statically reviewed quiet-discovery sets by about
9--11% in grid opportunities. These counts are not generated structures.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import zipfile
from pathlib import Path

from control_room.common import REPO, UserError, digest, read_json, write_json

PROFILE = 'awft-worldgen-four-set-v1'
BASE = 'packwiz/config/paxi/datapacks/awft-integration'
# Match the master's pre-existing template-reviewed proposal. The broader
# precoordination experiment is retained under an explicit HOLD, never selected.
SPACING = {
    'castleshift:castle': (96, 92),
    **{'archaeology_ruins:' + name: (80, 76) for name in (
        'adoberuins', 'mudpotterruin', 'mudschoolruin')},
}
# Biome eligibility findings are reported separately. Changing eligibility would
# confound the spacing A/B and expand the reviewed content/terrain scope.
BIOMES = {}
BIOME_TAGS = {}
TERRAIN_FILES = ('config/tectonic.json', 'config/seedgen.json',
                 'config/DistantHorizons.toml')


def encoded(value):
    return (json.dumps(value, indent=2, ensure_ascii=False) + '\n').encode('utf8')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def resource_path(key, kind):
    if not re.fullmatch(r'[a-z0-9_.-]+:[a-z0-9_./-]+', key) or '..' in key:
        raise UserError('Invalid reviewed resource identifier')
    namespace, name = key.split(':')
    return f'data/{namespace}/worldgen/{kind}/{name}.json'


def refine(key, baseline):
    result = copy.deepcopy(baseline)
    if key in SPACING:
        before, after = SPACING[key]
        placement = result['placement']
        if placement.get('type') != 'minecraft:random_spread' or placement.get('spacing') != before:
            raise UserError('Minor-site baseline drift: ' + key)
        if type(placement.get('separation')) is not int or not 0 <= placement['separation'] < after:
            raise UserError('Invalid preserved minimum separation: ' + key)
        placement['spacing'] = after
    return result


def read_resource(archive, name):
    info = archive.getinfo(name)
    if info.file_size > 256 * 1024:
        raise UserError('Worldgen metadata exceeds the bounded reader')
    raw = archive.read(info).decode('utf-8-sig')
    # Some pinned authors ship whole-line comments and trailing commas. Native
    # Minecraft uses a lenient reader. Do not strip // inside JSON string values.
    raw = re.sub(r'(?m)^\s*//[^\n]*$', '', raw)
    raw = re.sub(r',\s*([}\]])', r'\1', raw)
    return json.loads(raw)


def verified_jar(cache, mod):
    path = cache / mod['filename']
    if not path.is_file() or path.stat().st_size != mod['size'] or any(
        digest(path, algorithm) != expected for algorithm, expected in mod['hashes'].items()
    ):
        raise UserError('Exact worldgen source artifact differs: ' + mod['slug'])
    return path


def build_overlay(home, output, repo=REPO):
    """Write one new review directory. Existing output or installed paths fail."""
    from tools.playtest import guard
    output, repo, home = Path(output).resolve(), Path(repo).resolve(), Path(home).resolve()
    if output.exists() or output == repo or output.is_relative_to(home):
        raise UserError('Use a new review output outside every managed runtime')
    if not output.is_relative_to(repo / 'proposals'):
        raise UserError('Worldgen proposals must remain inside this checkout/proposals')
    guard(8 * 1024**2, 0)
    lock = read_json(repo / 'catalog/lock.json')
    proposal = read_json(repo / 'proposals/future-structure-frequency/proposal.json')
    for relative, expected in proposal['canonical_structure_set_inputs'].items():
        if digest(repo / relative) != expected:
            raise UserError('Master proposal baseline changed: ' + relative)
    if digest(repo / 'tools/worldgen_policy.py') != proposal['generator_before_sha256']:
        raise UserError('Master proposal generator baseline changed')
    if {r['structure_set']: (r['before_spacing_chunks'], r['after_spacing_chunks'])
        for r in proposal['changes']} != SPACING:
        raise UserError('Master proposal and generated overlay disagree')
    policy = read_json(repo / 'catalog/worldgen-policy.json')
    rows = {row['structure_set']: row for row in policy['placements']}
    if not SPACING.keys() <= rows.keys():
        raise UserError('The baseline does not contain every reviewed minor site')
    cache = home / 'caches/mods'
    mods = {m['slug']: m for m in lock['mods']}
    payload, changes, pins = {}, [], {}
    for key in sorted(SPACING):
        row = rows[key]
        path = resource_path(key, 'structure_set')
        before_raw = (repo / BASE / path).read_bytes()
        before = json.loads(before_raw)
        if before['placement'] != row['after']:
            raise UserError('Tracked placement and baseline policy disagree: ' + key)
        after = refine(key, before)
        payload[path] = encoded(after)
        changes.append({'resource': path, 'key': key, 'kind': 'minor-site spacing',
                        'before_sha256': sha(before_raw), 'after_sha256': sha(payload[path]),
                        'before': before['placement'], 'after': after['placement']})
        pins[row['project']] = mods[row['project']]
    for key, group in sorted(BIOMES.items()):
        row = rows[key]
        mod = mods[row['project']]
        path = resource_path(key, 'structure')
        with zipfile.ZipFile(verified_jar(cache, mod)) as archive:
            before = read_resource(archive, path)
        if (repo / BASE / path).exists():
            raise UserError('Existing structure override requires a fresh review: ' + key)
        after = copy.deepcopy(before)
        after['biomes'] = '#awft:minor_ruins/' + group
        payload[path] = encoded(after)
        changes.append({'resource': path, 'key': key, 'kind': 'minor-site biome eligibility',
                        'before_resource_sha256': sha(encoded(before)),
                        'before': before['biomes'], 'after': after['biomes'],
                        'after_sha256': sha(payload[path])})
    for group, values in BIOME_TAGS.items():
        payload[f'data/awft/tags/worldgen/biome/minor_ruins/{group}.json'] = encoded({
            'replace': False, 'values': [({'id': v, 'required': False} if v.startswith('#') else v)
                                       for v in values]})
    payload['pack.mcmeta'] = encoded({'pack': {'pack_format': 48,
        'description': 'AWFT modest-v1 future-terrain review overlay; not deployment approval'}})
    pin_rows = []
    for slug, mod in sorted(pins.items()):
        jar = verified_jar(cache, mod)
        pin_rows.append({'slug': slug, 'version': mod['version'], 'size': mod['size'],
                         'sha256': digest(jar), 'side': mod['side']})
    manifest = {'format': PROFILE, 'status': 'PROPOSED_NOT_DEPLOYED',
        'baseline_pack_version': lock['version'],
        'baseline_pack_sha256': digest(repo / 'packwiz/pack.toml'),
        'baseline_policy_sha256': digest(repo / 'catalog/worldgen-policy.json'),
        'terrain_inputs_unchanged': {path: digest(repo / 'packwiz' / path) for path in TERRAIN_FILES},
        'changed_structure_sets': len(SPACING), 'preserved_baseline_sets': len(rows) - len(SPACING),
        'biome_eligibility_updates': len(BIOMES), 'source_artifacts': pin_rows,
        'changes': changes,
        'files': {path: {'sha256': sha(raw), 'size': len(raw)} for path, raw in sorted(payload.items())},
        'limits': ['No worlds, level seed, dimension height, loot, templates or existing chunks are edited.',
                   'All nonselected landmark placements, separation, salts and exclusion radii are preserved.',
                   'Tag membership is eligibility, not proof of terrain fit or native generation.',
                   'Shared Packwiz manifests and live installations require master integration.',
                   'Native biome, structure, terrain, timing, restart and frontier checks remain required.']}
    # All validation completes before the first output write.
    output.mkdir(parents=True)
    for relative, raw in payload.items():
        path = output / 'datapack' / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    write_json(output / 'manifest.json', manifest)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--home', type=Path, default=Path(r'D:\A World for Two'))
    parser.add_argument('--output', type=Path, default=REPO / 'proposals/worldgen-four-set-v1')
    args = parser.parse_args()
    result = build_overlay(args.home, args.output)
    print(json.dumps({key: result[key] for key in ('status', 'changed_structure_sets',
                                                  'preserved_baseline_sets', 'biome_eligibility_updates')}))


if __name__ == '__main__':
    main()
