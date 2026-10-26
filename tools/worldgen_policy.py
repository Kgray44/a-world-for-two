"""Generate bounded placement overrides from the exact reviewed structure JARs.

This changes opportunities in new chunks only. It neither searches nor edits worlds.
Exclusion zones reduce nearby candidates; they are not bounding-box collision proof.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import zipfile
from pathlib import Path

from control_room.common import REPO, Layout, digest, read_json, utcnow, write_json

SLUGS = {'epic-structures-jungle-temples', 'aztec-ruins', 'yungs-better-jungle-temples',
         'yungs-better-desert-temples', 'archaeology-ruins', 'ancient-structures',
         'philips-ruins', 'when-dungeons-arise', 'mtr-moogs-temples-reimagined', 'castle-shift'}


def placement(slug, name, original):
    p = copy.deepcopy(original)
    if 'spacing' not in p:
        return p  # Preserve stronghold rings and every unrelated placement algorithm.
    spacing, separation = p['spacing'], p['separation']
    if slug == 'epic-structures-jungle-temples':
        if name == 'epic_temple_ruin':
            spacing, separation = 80, 32
            p['exclusion_zone'] = {'other_set': 'epic:epic_temple', 'chunk_count': 12}
        else:
            p['exclusion_zone'] = {'other_set': 'betterjungletemples:jungle_temples', 'chunk_count': 16}
    elif slug == 'aztec-ruins':
        spacing, separation = (128, 64) if name == 'aztecjungletemple' else (80, 32)
        p['exclusion_zone'] = {'other_set': 'epic:epic_temple' if name == 'aztecjungletemple' else 'ruinarium:aztecjungletemple', 'chunk_count': 16}
        # The original four ruin sets all use salt 0 and near-identical grids.
        if p['salt'] == 0:
            p['salt'] = int.from_bytes(hashlib.sha256(name.encode()).digest()[:4], 'big') & 0x7fffffff
    elif slug in ('yungs-better-jungle-temples', 'yungs-better-desert-temples'):
        spacing, separation = 80, 40
    elif slug == 'archaeology-ruins':
        spacing, separation = (112, 56) if 'monument' in name else (96, 48) if any(t in name for t in ('temple', 'pyramid')) else (80, 40)
    elif slug == 'ancient-structures':
        spacing, separation = 160, 64
    elif slug == 'philips-ruins':
        spacing, separation = max(spacing, 112), max(separation, 56)
    elif slug == 'when-dungeons-arise':
        spacing, separation = (128, 64) if name == 'major_structures' else (112, 56)
    elif slug == 'mtr-moogs-temples-reimagined':
        if name != 'nether_temple':
            spacing, separation = (128, 64) if name == 'ocean_temple' else (112, 48)
        other = {'jungle_temple': 'betterjungletemples:jungle_temples', 'desert_temple': 'betterdeserttemples:desert_temples'}.get(name)
        if other:
            p['exclusion_zone'] = {'other_set': other, 'chunk_count': 16}
    elif slug == 'castle-shift':
        spacing, separation = 96, 32  # Preserve the original village exclusion.
    if not 0 <= separation < spacing <= 4096:
        raise ValueError('Invalid reviewed structure spacing')
    p.update(spacing=spacing, separation=separation)
    return p


def generate(home):
    cache = Layout(home).caches / 'mods'
    lock = read_json(REPO / 'catalog/lock.json')
    target = REPO / 'packwiz/config/paxi/datapacks/awft-integration'
    rows = []
    for mod in lock['mods']:
        if mod['slug'] not in SLUGS:
            continue
        jar = cache / mod['filename']
        if not jar.is_file() or jar.stat().st_size != mod['size'] or any(digest(jar, algorithm) != expected for algorithm, expected in mod['hashes'].items()):
            raise ValueError('Structure source hash mismatch: ' + mod['slug'])
        with zipfile.ZipFile(jar) as archive:
            for name in archive.namelist():
                match = re.fullmatch(r'data/([^/]+)/worldgen/structure_set/(.+)\.json', name)
                if not match:
                    continue
                info = archive.getinfo(name)
                if info.file_size > 128 * 1024:
                    raise ValueError('Structure metadata exceeds its bound')
                original = json.loads(re.sub(r'(?m)^\s*//.*$', '', archive.read(name).decode('utf-8-sig')))
                updated = copy.deepcopy(original)
                updated['placement'] = placement(mod['slug'], match[2], original['placement'])
                if updated == original:
                    continue
                write_json(target / name, updated)
                rows.append({'project': mod['slug'], 'version': mod['version'], 'jar_sha256': digest(jar),
                             'structure_set': match[1] + ':' + match[2], 'file': name,
                             'before': original['placement'], 'after': updated['placement']})
    write_json(REPO / 'catalog/worldgen-policy.json', {'generated': utcnow(), 'pack_version': lock['version'],
        'scope': 'Candidate new-chunk placement only. No permanent world was read, generated or changed.',
        'boundary': 'Larger spacing and directed exclusion zones reduce density. Actual terrain fit, structure overlap, loot and generation cost require disposable-world validation.',
        'placements': rows})
    print('Generated', len(rows), 'reviewed placement overrides; permanent world untouched')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--home', type=Path, default=Path(r'D:\A World for Two'))
    generate(parser.parse_args().home)
