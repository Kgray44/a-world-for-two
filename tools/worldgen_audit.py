"""Read-only pinned resource audit and explicitly synthetic placement comparison.

Never opens a save for writing, starts Minecraft, or treats grid candidates as
generated structures. Native generated packs and registration hooks remain a
separate runtime authority.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import math
import re
import statistics
import zipfile
from pathlib import Path

from control_room.common import REPO, UserError, digest, read_json, write_json
from tools.worldgen_refinement import BASE, PROFILE, read_resource, refine, verified_jar

RESOURCE = re.compile(r'data/([^/]+)/(worldgen/(?:structure_set|structure|biome)|tags/worldgen/biome)/(.+)\.json$')
WINDOWS = ((-2048, -2048), (-2048, 1536), (1536, -2048), (1536, 1536),
           (-256, -256), (3840, -256), (-256, 3840), (-4352, -256))


def identifier(key):
    return key if ':' in key else 'minecraft:' + key


class ResourceIndex:
    def __init__(self):
        self.resources = {}
        self.sources = {}
        self.shadows = []

    def add(self, relative, data, source):
        match = RESOURCE.fullmatch(relative)
        if not match:
            return
        key = (match[2], match[1] + ':' + match[3])
        if key[0] == 'tags/worldgen/biome':
            values = [] if data.get('replace') else list(self.resources.get(key, {}).get('values', []))
            data = dict(data, values=values + data.get('values', []))
        elif key in self.resources:
            self.shadows.append({'kind': key[0], 'key': key[1], 'before': self.sources[key], 'after': source})
        self.resources[key], self.sources[key] = data, source

    def archive(self, path, source, prefix=''):
        with zipfile.ZipFile(path) as archive:
            for name in sorted(archive.namelist()):
                if not name.startswith(prefix):
                    continue
                relative = name[len(prefix):]
                if RESOURCE.fullmatch(relative):
                    self.add(relative, read_resource(archive, name), source)

    def folder(self, path, source):
        for member in sorted(Path(path).rglob('*.json')):
            relative = member.relative_to(path).as_posix()
            if RESOURCE.fullmatch(relative):
                self.add(relative, json.loads(member.read_bytes()), source)

    def biomes(self, value, stack=()):
        result, missing = set(), set()
        values = value if isinstance(value, list) else [value]
        for entry in values:
            required = not isinstance(entry, dict) or entry.get('required', True)
            key = entry['id'] if isinstance(entry, dict) else entry
            if not isinstance(key, str):
                raise UserError('Invalid biome reference')
            if key.startswith('#'):
                tag = identifier(key[1:])
                if tag in stack:
                    raise UserError('Biome tag cycle: ' + ' -> '.join((*stack, tag)))
                data = self.resources.get(('tags/worldgen/biome', tag))
                if data is None:
                    if required:
                        missing.add('#' + tag)
                else:
                    found, absent = self.biomes(data['values'], (*stack, tag))
                    result.update(found)
                    missing.update(absent)
            else:
                key = identifier(key)
                if ('worldgen/biome', key) in self.resources:
                    result.add(key)
                elif required:
                    missing.add(key)
        return result, missing


def load_index(home, overlay=None, repo=REPO):
    lock = read_json(repo / 'catalog/lock.json')
    index, artifacts = ResourceIndex(), []
    native = Path(home) / 'server/libraries/net/minecraft/server/1.21.1-20240808.144430/server-1.21.1-20240808.144430-extra.jar'
    if not native.is_file():
        raise UserError('Installed vanilla 1.21.1 data is required for tag resolution')
    index.archive(native, 'minecraft:1.21.1')
    artifacts.append({'slug': 'minecraft-data', 'sha256': digest(native), 'size': native.stat().st_size})
    cache, tectonic = Path(home) / 'caches/mods', None
    for mod in lock['mods']:
        if mod['kind'] != 'mod' or mod.get('default') is False:
            continue
        path = cache / mod['filename']
        if not path.is_file():
            raise UserError('Missing pinned audit input: ' + mod['slug'])
        with zipfile.ZipFile(path) as archive:
            relevant = any(RESOURCE.fullmatch(n) for n in archive.namelist())
        if relevant or mod['slug'] == 'tectonic':
            path = verified_jar(cache, mod)
            artifacts.append({'slug': mod['slug'], 'version': mod['version'], 'side': mod['side'],
                              'sha256': digest(path), 'size': path.stat().st_size})
            index.archive(path, mod['slug'])
        if mod['slug'] == 'tectonic':
            tectonic = path
    if tectonic is not None:
        index.archive(tectonic, 'tectonic:builtin', 'resourcepacks/tectonic/')
    index.folder(repo / BASE, 'awft:baseline-integration')
    if overlay:
        index.folder(Path(overlay) / 'datapack', PROFILE)
    return index, artifacts


def compatibility(index):
    rows, missing_structures = [], []
    for (kind, key), data in sorted(index.resources.items()):
        if kind != 'worldgen/structure_set':
            continue
        members = []
        for item in data['structures']:
            name = identifier(item['structure'])
            structure = index.resources.get(('worldgen/structure', name))
            if structure is None:
                missing_structures.append({'set': key, 'structure': name})
                continue
            biomes, missing = index.biomes(structure['biomes'])
            members.append({'id': name, 'biome_count': len(biomes),
                'biome_namespaces': dict(sorted(collections.Counter(b.split(':')[0] for b in biomes).items())),
                'required_biome_references_unresolved': sorted(missing),
                'terrain_adaptation': structure.get('terrain_adaptation'),
                'height_projection': structure.get('project_start_to_heightmap'),
                'max_distance_from_center': structure.get('max_distance_from_center')})
        rows.append({'key': key, 'source': index.sources[(kind, key)],
                     'placement': data['placement'], 'members': members})
    edges = {r['key']: r['placement'].get('exclusion_zone', {}).get('other_set') for r in rows}
    unresolved = [{'set': k, 'other_set': v} for k, v in edges.items() if v and v not in edges]
    for start in edges:
        seen, node = set(), start
        while node:
            if node in seen:
                raise UserError('Structure exclusion cycle: ' + start)
            seen.add(node)
            node = edges.get(node)
    return {'tier': 'static pinned resource/biome-tag resolution; no native registration or terrain proof',
        'structure_sets': rows, 'unresolved_structure_references': missing_structures,
        'unresolved_exclusion_targets': unresolved,
        'resource_shadowing': index.shadows,
        'boundary': 'Runtime-generated packs, overlays, load order and registry hooks require native verification.'}


class JavaRandom:
    """Minecraft LegacyRandomSource's Java 48-bit LCG, for grid sampling only."""
    def __init__(self, seed):
        self.state = (seed ^ 0x5DEECE66D) & ((1 << 48) - 1)

    def bits(self, count):
        self.state = (self.state * 0x5DEECE66D + 11) & ((1 << 48) - 1)
        return self.state >> (48 - count)

    def next_int(self, bound):
        if type(bound) is not int or not 0 < bound <= 0x7fffffff:
            raise UserError('Invalid Java random bound')
        if bound & (bound - 1) == 0:
            return (bound * self.bits(31)) >> 31
        while True:
            value = self.bits(31)
            result = value % bound
            if value - result + bound - 1 < 1 << 31:
                return result


def grid_candidates(seed, placement, origin, width=512):
    if placement.get('type') != 'minecraft:random_spread' or placement.get('frequency', 1) != 1:
        raise UserError('Synthetic comparison only supports unconditional vanilla random-spread grids')
    spacing, separation, salt = (placement[k] for k in ('spacing', 'separation', 'salt'))
    if not 0 <= separation < spacing <= 4096 or not 1 <= width <= 1024:
        raise UserError('Unbounded grid comparison')
    spread = placement.get('spread_type', 'linear')
    if spread not in ('linear', 'triangular'):
        raise UserError('Unreviewed spread algorithm')
    x0, z0 = origin
    points = []
    for rx in range(x0 // spacing, (x0 + width - 1) // spacing + 1):
        for rz in range(z0 // spacing, (z0 + width - 1) // spacing + 1):
            random = JavaRandom(rx * 341873128712 + rz * 132897987541 + seed + salt)
            def offset():
                first = random.next_int(spacing - separation)
                return first if spread == 'linear' else (first + random.next_int(spacing - separation)) // 2
            x, z = rx * spacing + offset(), rz * spacing + offset()
            if x0 <= x < x0 + width and z0 <= z < z0 + width:
                points.append((x, z))
    return sorted(points)


def nearest(points):
    if len(points) < 2:
        return {'min_chunks': None, 'median_chunks': None}
    distances = [min(math.dist(p, q) for q in points if p != q) for p in points]
    return {'min_chunks': round(min(distances), 3), 'median_chunks': round(statistics.median(distances), 3)}


def compare_grids(seed, repo=REPO):
    rows = read_json(repo / 'catalog/worldgen-policy.json')['placements']
    result = []
    for row in rows:
        key, before = row['structure_set'], row['after']
        if before.get('type') != 'minecraft:random_spread' or before.get('frequency', 1) != 1:
            continue
        after = refine(key, {'placement': before})['placement']
        windows = []
        for origin in WINDOWS:
            old, new = grid_candidates(seed, before, origin), grid_candidates(seed, after, origin)
            windows.append({'origin_chunks': origin, 'width_chunks': 512,
                'baseline_candidates': len(old), 'updated_candidates': len(new),
                'baseline_nearest': nearest(old), 'updated_nearest': nearest(new)})
        old_count = sum(w['baseline_candidates'] for w in windows)
        new_count = sum(w['updated_candidates'] for w in windows)
        result.append({'key': key, 'changed': before != after, 'before': before, 'after': after,
            'baseline_candidates': old_count, 'updated_candidates': new_count,
            'sampled_change_percent': round(100 * (new_count / old_count - 1), 3) if old_count else None,
            'asymptotic_opportunity_change_percent': round(100 * ((before['spacing']/after['spacing'])**2 - 1), 3),
            'windows': windows})
    return {'format': 'awft-worldgen-grid-comparison:1',
        'tier': 'SYNTHETIC_GRID_CANDIDATES_NOT_GENERATED_STRUCTURES',
        'seed_sha256': hashlib.sha256(str(seed).encode()).hexdigest(),
        'sampling': 'Eight fixed nonoverlapping 512x512-chunk geometric windows, including negative coordinates.',
        'omitted': ['Biome and height eligibility', 'frequency-reduced/custom placements',
                    'exclusion-zone rejection', 'native registration hooks', 'actual pieces and terrain fit'],
        'rows': result}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--home', type=Path, default=Path(r'D:\A World for Two'))
    parser.add_argument('--overlay', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--seed-from', type=Path, help='Read only the saved WorldGenSettings seed')
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists() or not output.is_relative_to(REPO / 'evidence/worldgen'):
        parser.error('Use a new file inside this checkout/evidence/worldgen')
    from tools.playtest import guard
    guard(8 * 1024**2, 0)
    index, pins = load_index(args.home, args.overlay)
    result = {'artifacts': pins, 'compatibility': compatibility(index)}
    if args.seed_from:
        import nbtlib
        seed = int(nbtlib.load(args.seed_from)['Data']['WorldGenSettings']['seed'])
        result['grid_comparison'] = compare_grids(seed)
    write_json(output, result)
    print(json.dumps({'static_structure_sets': len(result['compatibility']['structure_sets']),
                      'output': str(output), 'tier': result['compatibility']['tier']}))


if __name__ == '__main__':
    main()
