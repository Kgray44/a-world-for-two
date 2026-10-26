"""World-generation code/data must exist on both ends of SeedGen prediction."""
from control_room.common import REPO, digest, utcnow, write_json

WORLDGEN = frozenset((
    'aztec-ruins', 'castle-shift', 'embers-castles-and-keeps', 'epic-structures-jungle-temples',
    'moogs-structure-lib', 'mtr-moogs-temples-reimagined', 'when-dungeons-arise',
    'yungs-better-desert-temples', 'yungs-better-jungle-temples',
))
EXPLANATION = 'Installed on both sides because SeedGen requires matching world-generation mods and custom registry codecs on the client, including otherwise server-only structure mods.'


def apply(items, selection, cache):
    rows = []
    for item in items:
        if item['slug'] not in WORLDGEN:
            continue
        path = cache / item['filename']
        if path.stat().st_size != item['size'] or any(digest(path, name) != value for name, value in item['hashes'].items()):
            raise ValueError('SeedGen worldgen source differs from its exact pin: ' + item['slug'])
        item['side'] = 'both'
        if EXPLANATION not in item['selection_reason']:
            item['selection_reason'] += ' ' + EXPLANATION
        for choice in selection['mods']:
            if choice['project'] in (item['project_id'], item['slug']):
                choice['side'] = 'both'
                choice['reason'] = item['selection_reason']
        rows.append({'slug': item['slug'], 'version': item['version'], 'sha256': digest(path), 'side': 'both'})
    if {row['slug'] for row in rows} != WORLDGEN:
        raise ValueError('SeedGen matching-worldgen policy is missing an exact candidate')
    write_json(REPO / 'catalog/seedgen-worldgen.json', {
        'at': utcnow(), 'authority': 'https://modrinth.com/mod/distant-horizons-seedgen',
        'reason': EXPLANATION, 'mods': rows,
        'observed_failure': 'Candidate.9 client registry loading failed on missing YUNG/Moog placement codecs and structure definitions, then SeedGen reported a vanilla fallback.',
        'boundary': 'This corrects the installation prerequisite. A new client runtime must prove modded worldgen loading, server agreement and distant-terrain fidelity. No SeedGen JAR is modified.'})
    return items
