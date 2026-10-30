"""Whole-city maps for actually completed refinements, never proposed buildings."""
from pathlib import Path
import argparse, hashlib, json
from PIL import Image, ImageDraw
from tools.artistic_city_planning_map import COAST, PINS, read, rows, boundary, COLORS, font
from tools.artistic_bridge_refinement import flatten
from tools.playtest import guard


def prepare(home, manifest, manifest_sha, native_results, additions, output):
    guard(16 * 1024**2, 0)
    home, manifest, output = Path(home), Path(manifest), Path(output)
    if output.exists() or hashlib.sha256(manifest.read_bytes()).hexdigest() != manifest_sha:
        raise ValueError('New output and exact frozen refinement source required')
    source = json.loads(manifest.read_bytes())
    records = json.loads(Path(native_results).read_bytes())
    earlier = json.loads(Path(additions).read_bytes())
    if source['format'] != 'awft-west15-owned-shell-correction:1' or len(source['bundles']) != 3:
        raise ValueError('Exactly the reviewed three five-house refinements required')
    marked = {}
    for marker in (home / 'dashboard/settlement').glob('settlement-result-*.json.complete'):
        path = marker.with_suffix('')
        raw = path.read_bytes()
        sha = hashlib.sha256(raw).hexdigest()
        if sha == marker.read_text().strip():
            marked[sha] = (path, json.loads(raw))

    def genuine(result, plan_sha):
        if (result.get('operation') != 'verify' or result.get('plan_sha256') != plan_sha
                or result.get('failures') != 0 or result.get('cleanup_required') is not False
                or result.get('error') or not result.get('finished')):
            raise ValueError('Clean actual complete native verification required')
        found = [(sha, p) for sha, (p, data) in marked.items() if data == result]
        if len(found) != 1:
            raise ValueError('One genuine hash-marked terminal required')
        sha, path = found[0]
        return {'path': path.relative_to(home).as_posix(), 'sha256': sha,
                'plan_sha256': plan_sha, 'finished': result['finished']}

    new_roofs = set()
    for row in earlier:
        folder = home / 'staging' / row['source']
        after = folder / 'complete-after-VERIFY-ONLY.json'
        sha = hashlib.sha256(after.read_bytes()).hexdigest()
        genuine(row['native_proof'], sha)
        new_roofs |= {(x, z) for (x, y, z), state in flatten(json.loads(after.read_bytes())).items()
                      if y >= 67 and state.split('[', 1)[0] not in ('minecraft:air', 'minecraft:cave_air', 'minecraft:water')}
    coast = read(home, COAST)
    x0, z0, x1, z1 = coast['bounds_xz']
    width, height = x1 - x0 + 1, z1 - z0 + 1
    base = Image.new('RGB', (width, height), COLORS['unknown'])
    pix, old = base.load(), set()
    for x, z, code, y in coast['samples']:
        pix[x-x0, z-z0] = tuple(bytes.fromhex(COLORS[{1: 'water', 2: 'ground', 3: 'context'}.get(code, 'unknown')][1:]))
        if code == 3 and y is not None and y >= 67 and z < -1115:
            old.add((x, z))
    output.mkdir(parents=True)
    prior, receipts = set(), []
    for group in source['bundles']:
        index = group['group']
        filename = 'west15-' + str(index) + '-full-VERIFY-ONLY.json'
        full = manifest.parent / filename
        raw = full.read_bytes()
        sha = hashlib.sha256(raw).hexdigest()
        if sha != source['files'][filename]['sha256']:
            raise ValueError('Frozen full-after document changed')
        checks = [r for r in records if r['group'] == index and r['action'] == 'verify' and r['plan'] == filename]
        if len(checks) != 1:
            raise ValueError('Exactly one actual successful group verification required')
        proof = genuine(checks[0]['result'], sha)
        roof = {(x, z) for (x, y, z), state in flatten(json.loads(raw)).items()
                if y >= 67 and state.split('[', 1)[0] not in ('minecraft:air', 'minecraft:cave_air', 'minecraft:water')}
        image = Image.new('RGB', (2480, 2180), COLORS['paper'])
        draw = ImageDraw.Draw(image)
        scale, left, top = 5, 95, 190
        image.paste(base.resize((width*scale, height*scale), Image.Resampling.NEAREST), (left, top))
        def point(q): return left+(q[0]-x0)*scale, top+(q[1]-z0)*scale
        def area(cells, color, edge=None):
            for x, z, n in rows(cells):
                a, b = point((x, z)), point((x+n, z+1))
                draw.rectangle((a[0], a[1], b[0]-1, b[1]-1), fill=color)
            if edge:
                for a, b in boundary(cells): draw.line([point(a), point(b)], fill=edge, width=2)
        area(old, '#8b8d7f')
        area(new_roofs, '#5c6255')
        area(prior, '#9b6e4e', '#554936')
        area(roof, '#467f59', '#174d32')
        draw.text((95, 36), 'PIRATE CITY · WESTERN REFINEMENT ' + str(index), font=font(44, True), fill=COLORS['ink'])
        draw.text((98, 104), '5 existing buildings refined · 32 earlier new buildings retained', font=font(29), fill=COLORS['ink'])
        draw.text((98, 150), 'Full north-bank site · North up · Current refinement green', font=font(25), fill=COLORS['ink'])
        draw.text((2380, 40), 'N', font=font(33, True), fill=COLORS['ink'])
        draw.line((2400, 135, 2400, 95), fill=COLORS['ink'], width=4)
        draw.polygon(((2400, 86), (2391, 102), (2409, 102)), fill=COLORS['ink'])
        for x, color, label in [(95, '#8b8d7f', 'Earlier saved buildings'), (730, '#5c6255', '32 new buildings'),
                                 (1330, '#9b6e4e', 'Prior refinements'), (1880, '#467f59', 'This refinement')]:
            draw.rectangle((x, 2060, x+26, 2086), fill=color)
            draw.text((x+40, 2058), label, font=font(23), fill=COLORS['ink'])
        draw.text((95, 2110), 'Schematic from saved coast and genuine completed native checks; actual Minecraft artistic review is separate.', font=font(22), fill=COLORS['ink'])
        path = output / ('refinement-' + str(index).zfill(2) + '-overhead.png')
        image.save(path, optimize=True)
        receipts.append({'group': index, 'existing_buildings_refined': 5, 'new_buildings': 0,
                         'image': path.name, 'image_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                         'source_manifest_sha256': manifest_sha, 'baseline_coast_sha256': PINS[COAST],
                         'native_full_verification': proof, 'artistic_acceptance': False})
        prior |= roof
    (output/'map-receipts.json').write_text(json.dumps(receipts, indent=2)+'\n', encoding='utf8')
    return {'output': str(output), 'maps': [r['image'] for r in receipts], 'refined_buildings': 15, 'world_writes': 0}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('home', 'manifest', 'native-results', 'additions', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--manifest-sha', required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.home, args.manifest, args.manifest_sha, args.native_results, args.additions, args.output)))
