"""Original bounds analysis for the exact native43 sapling descriptors.

This computes coordinate envelopes; it never implements, selects, runs, retries or
copies a tree generator. Actual native growth and the existing guard stay separate.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess
import zipfile

HERE = Path(__file__).resolve().parent
TERMINAL_SHA = '8c767ba8505846eeb4e305d4691e853cd48461d3d7ff5591f9dbfa45c44a3cc5'
MAX_KNOWN = 131072


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read_small(path, cap):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or not 0 < path.stat().st_size <= cap:
        raise ValueError('Bounded ordinary input required')
    return path.read_bytes()


def volume(box):
    if len(box) != 6 or any(type(v) is not int for v in box) or any(box[i] > box[i+3] for i in range(3)):
        raise ValueError('Six finite ordered integer bounds required')
    return math.prod(box[i+3]-box[i]+1 for i in range(3))


def union(boxes):
    return [min(b[i] for b in boxes) for i in range(3)] + [max(b[i+3] for b in boxes) for i in range(3)]


def maximum_height(trunk):
    if trunk['type'] == 'regions_unexplored:aspen':
        if trunk['bend_chance'] != 0.0:
            raise ValueError('Bent Aspen trunk is not this reviewed descriptor')
        return trunk['height']['max_inclusive']
    return trunk['base_height'] + trunk['height_rand_a'] + trunk['height_rand_b']


def feature_bounds(feature):
    """Conservative complete direct-write bounds, with explicit native read minima.

    All providers and control flow are separately bound by the exact descriptor.
    These formulas describe the reviewed algorithms, rather than generating blocks.
    """
    codec = feature['actual_codec']
    kind, config = codec['type'], codec['config']
    bees = False
    facts = []
    if kind == 'regions_unexplored:sakura_tree':
        height = config['minimum_size'] + config['size_variation'] - 1
        # Twelve limb cases: anchors <=3 horizontal, +3 vertical; canopy
        # middle <=3 horizontal at anchor+1, caps <=2 at anchor+0/+2.
        # Base roots start one below a +/-1 base, make at most3 iterations;
        # their native log helper can additionally change grass immediately below.
        box = [-6, -4, -6, 6, height+5, 6]
        bees = True
        facts = ['all12 limb cases and both leaf blobs', 'three root iterations plus soil below',
                 'native internal 1/20 bee-nest branch; not suppressed']
    elif kind == 'regions_unexplored:aspen_tree':
        height = config['minimum_size'] + config['size_variation'] - 1
        # Tallest native fork adds3 above last trunk; its leaf blob adds3.
        # Fork displacement1 + blob radius2. Root rd is2 or3 inclusive;
        # lowest possible log is-3 and its soil check/write is-4.
        box = [-3, -4, -3, 3, height+6, 3]
        facts = ['all3 fork cases, four rotations and random side stem',
                 'rd2/3 inclusive roots plus soil below', 'radius3 ground litter, y-height+1 setter']
    elif kind == 'regions_unexplored:larch_tree':
        height = config['minimum_size'] + config['size_variation'] - 1
        # placeTop calls Short then Long, never XLong. Long offset2 plus
        # directional blob extension2. Top's two cases reach height+3.
        # Roots rd4/5 inclusive start at0; final soil write may reach-6.
        box = [-4, -6, -4, 4, height+3, 4]
        facts = ['reachable Short/Long canopy only; XLong is not called',
                 'both top cases +3; all four directional blobs', 'rd4/5 inclusive roots plus soil below']
    elif kind == 'minecraft:tree':
        trunk, foliage = config['trunk_placer'], config['foliage_placer']
        height = maximum_height(trunk)
        if trunk['type'] == 'minecraft:fancy_trunk_placer':
            # Native L=height+2; treeShape <=L/4; random factor <1.328.
            # Ceil includes both coordinate floors and a floating-point margin.
            # makeLimb interpolates between endpoints and cannot leave their box.
            radial = math.ceil(1.328*(height+2)/4 + .5)
            if foliage['type'] == 'regions_unexplored:sakura':
                radius, top = radial+2, height-3+2
                facts.append('Sakura leaf blob radius2, +2; configured radius/flower chance do not add writes in actual method')
            elif foliage['type'] == 'minecraft:fancy_foliage_placer':
                radius, top = radial+foliage['radius']+1, height-3+foliage['offset']
                facts.append('Fancy leaf rows radius+1, offset through offset-height inclusive')
            else:
                raise ValueError('Unreviewed fancy foliage')
            box = [-radius, -1, -radius, radius, top, radius]
            facts += ['Fancy native L=H+2; radial ceil(1.328*L/4+.5)',
                      'all limb interpolation stays between endpoints; vertical clearance checks reach H+2']
        elif foliage['type'] == 'regions_unexplored:aspen':
            box = [-2, -4, -2, 2, height+2, 2]
            facts += ['bend chance exactly0; attachment atH', 'foliage radius2/-1..+2',
                      'conservative lower bound-4 also covers branch emptiness reads']
        elif foliage['type'] == 'regions_unexplored:maple':
            box = [-3, -1, -3, 3, height+1, 3]
            facts += ['straight attachmentH; Maple foliage max radius2 and top+1',
                      'group branches one cell only; radius3 ground litter dominates horizontal extent']
        elif foliage['type'] == 'regions_unexplored:fancy_pine':
            box = [-3, -1, -3, 3, height+2+foliage['offset']['max_inclusive'], 3]
            facts += ['both FancyPine cases including radius3/maxDistance4 row',
                      'native offset0/1 applied once; branch leaf fans extend at most2']
        elif foliage['type'] == 'minecraft:spruce_foliage_placer':
            radius = foliage['radius']['max_inclusive']
            box = [-radius, -1, -radius, radius, height+foliage['offset']['max_inclusive'], radius]
            facts += ['native Spruce row radius never exceeds sampled radius3',
                      'all offset1/2 and trunk-height1/2 cases; branch leaf fans max2']
        else:
            raise ValueError('Unreviewed native foliage algorithm')
        for decorator in config['decorators']:
            name = decorator['type']
            if name == 'minecraft:beehive':
                bees = True
                facts.append('native one-cell nest next to a real log, 2..3 native occupant records')
            elif name == 'regions_unexplored:place_on_ground':
                # Lowest native trunk/root positions can include dirt at-1.
                # Silver-birch root depths are handled in the custom branch.
                if decorator['radius'] != 3 or decorator['height'] != 1:
                    raise ValueError('Unreviewed ground litter range')
                facts.append('ground litter minY+-1 then above(), radius3; no ground flattening')
            elif name == 'regions_unexplored:random_branch':
                facts.append('all native BranchModes; no-leaf fan1, leaf fan2; down-read budget included by known perimeter')
            elif name == 'regions_unexplored:group_branch':
                if 'leaves_provider' in decorator:
                    raise ValueError('This reviewed group branch has no leaf fan')
            else:
                raise ValueError('Unreviewed native decorator')
    else:
        raise ValueError('Unreviewed native feature')
    return {'direct_bounds': box, 'native_bee_nest_possible': bees, 'derivation': facts}


def artifact_proof(ru_jar, patched_jar, named_jar):
    provenance = json.loads(read_small(HERE/'source-provenance.json', 128*1024))
    ru_raw = read_small(ru_jar, 8*1024*1024)
    if len(ru_raw) != provenance['ru_jar_bytes'] or sha(ru_raw) != provenance['ru_jar_sha256']:
        raise ValueError('Exact pinned RU artifact required')
    result = {}
    with zipfile.ZipFile(ru_jar) as ru, zipfile.ZipFile(patched_jar) as patched, zipfile.ZipFile(named_jar) as named:
        for row in provenance['pinned_ru_classes'] + provenance['pinned_native_classes']:
            entry = row['class'].replace('.', '/')+'.class'
            jar = ru if row in provenance['pinned_ru_classes'] else (patched if entry in patched.namelist() else named)
            raw = jar.read(entry)
            if len(raw) != row['bytes'] or sha(raw) != row['sha256']:
                raise ValueError('Pinned native algorithm resource changed: '+row['class'])
            result[row['class']] = sha(raw)
    return result


def qualify(terminal, sapling, resources):
    frozen = json.loads(read_small(HERE/'native-descriptors.json', 128*1024))
    provenance = json.loads(read_small(HERE/'source-provenance.json', 128*1024))
    expected = {v['class']: v['sha256'] for v in provenance['pinned_ru_classes']+provenance['pinned_native_classes']}
    if resources != expected:
        raise ValueError('Complete exact native class-resource proof required')
    if sapling not in frozen['native_descriptors']:
        raise ValueError('Sapling not in actual describe palette')
    if (terminal.get('native_descriptors', {}).get(sapling) != frozen['native_descriptors'][sapling]
        or terminal.get('native_descriptor_sha256s', {}).get(sapling) != frozen['native_descriptor_sha256s'][sapling]):
        raise ValueError('Every actual primary, secondary and flower role must remain exact')
    descriptor = terminal['native_descriptors'][sapling]
    if set(descriptor['roles'].values()) != set(descriptor['features']):
        raise ValueError('Reachable role closure differs from feature inventory')
    variants = {key: feature_bounds(value) for key, value in descriptor['features'].items()}
    direct = union([v['direct_bounds'] for v in variants.values()])
    # TreeFeature.updateLeaves writes only within its encapsulated placement box.
    # StructureTemplate.updateShapeAtEdge explicitly visits a cell and one adjacent
    # cell; allow one extra cell on each side. Custom features use ordinary flag2.
    write = [v-1 if i < 3 else v+1 for i, v in enumerate(direct)]
    known = [write[0]-8, write[1]-2, write[2]-8, write[3]+8, write[4]+4, write[5]+8]
    if volume(known) > MAX_KNOWN:
        raise ValueError('Complete known envelope exceeds existing controller budget')
    derivation = {'sapling': sapling, 'native_descriptor_sha256': frozen['native_descriptor_sha256s'][sapling],
                  'roles': descriptor['roles'], 'variants': variants, 'direct_union': direct,
                  'relative_write_bounds': write, 'relative_known_bounds': known,
                  'known_cells': volume(known), 'algorithm_resources': resources,
                  'provenance_sha256': sha((HERE/'source-provenance.json').read_bytes()),
                  'recipe_source_sha256': sha(Path(__file__).read_bytes()),
                  'boundary_policy': 'Normal side effects outside the reviewed write/known field remain latched failure; never silently accepted'}
    return {'format': 'awft-native-tree-qualification:1', 'sapling': sapling,
            'native_descriptor_sha256': frozen['native_descriptor_sha256s'][sapling],
            'all_reachable_features_reviewed': True, 'derivation_sha256': sha(canonical(derivation)),
            'relative_write_bounds': write, 'derivation': derivation,
            'native_bee_nest_possible': any(v['native_bee_nest_possible'] for v in variants.values()),
            'growth_authorized': False, 'native_growth_tested': False,
            'bee_policy': 'Active43 preserves old BEs but lacks species-specific new-BE validation; reviewed native bee admission/restoration is required before growth, no variant retry/suppression'}


def prepare(args):
    output = Path(args.output).resolve()
    root = Path('D:/A World for Two/staging').resolve()
    if output.exists() or not output.is_relative_to(root):
        raise ValueError('New owned D staging output required')
    subprocess.run(['powershell.exe', '-NoProfile', '-File', 'C:/Users/kkids/AppData/Local/AeroStorageWatch/ReserveGuard.ps1',
                    '-EstimatedCBytes', '0', '-EstimatedDBytes', str(2*1024*1024)], check=True)
    raw = read_small(args.describe, 2*1024*1024)
    if sha(raw) != TERMINAL_SHA:
        raise ValueError('Exact actual43 successful describe receipt required')
    terminal = json.loads(raw)
    if (terminal.get('operation') != 'describe' or terminal.get('failures') != 0 or not terminal.get('cleanup_passed')
        or terminal.get('temporary_tickets_remaining') != 0 or terminal.get('world_mutated_after_restoration') is not False):
        raise ValueError('Describe must be clean and non-mutating')
    resources = artifact_proof(args.ru, args.patched, args.named)
    rows = [qualify(terminal, sapling, resources) for sapling in sorted(terminal['native_descriptors'])]
    output.mkdir()
    for row in rows:
        name = row['sapling'].replace(':', '--')+'.json'
        (output/name).write_text(json.dumps(row, indent=2, sort_keys=True)+'\n', encoding='utf-8')
    receipt = {'format': 'awft-native-tree-envelope-receipt:1', 'actual_describe_sha256': sha(raw),
               'qualification_count': len(rows), 'native_growth_or_world_actions': False,
               'files': {f.name: {'bytes': f.stat().st_size, 'sha256': sha(f.read_bytes())} for f in sorted(output.glob('*.json'))}}
    (output/'receipt.json').write_text(json.dumps(receipt, indent=2, sort_keys=True)+'\n', encoding='utf-8')
    print(json.dumps(receipt))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('describe', 'ru', 'patched', 'named', 'output'):
        parser.add_argument('--'+key, required=True)
    prepare(parser.parse_args())
