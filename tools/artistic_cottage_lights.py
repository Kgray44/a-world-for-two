"""A separate, tiny light-scale correction after the actual furnished capture."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

from control_room.common import UserError, digest, utcnow
from tools.artistic_cottage_life import construct as furnished, check as furnished_check, native_delta as furnishing_delta
from tools.artistic_street_details import Details
from tools.artistic_street import GUARD, MAX_BUNDLE


R2_SHA = '20e33d158947363bf15ff5212f3e8c82fe3481137f8fbeae173cdd23cc7c9de9'


def construct(registry, survey):
    prior = furnished(registry, survey)
    d = Details(prior.p)
    changed = []
    for p, state in d.base.blocks.items():
        if state.split('[', 1)[0] == 'mcwlights:copper_small_chandelier':
            d.p.zone = d.base.owners[p]
            d.put(*p, 'minecraft:lantern', hanging=True, waterlogged=False)
            changed.append(p)
    prior.p = d.p
    checks = furnished_check(prior)
    return d, changed, checks


def prepare(home, registry_path, survey_path, r2_path, output, backup_sha):
    home, output = Path(home).resolve(), Path(output).resolve()
    if home.drive.upper() != 'D:' or not output.is_relative_to(home/'staging') or output.exists() or not re.fullmatch('[0-9a-f]{64}', backup_sha):
        raise UserError('NEW private D staging folder and actual current backup required')
    if digest(Path(r2_path)) != R2_SHA:
        raise UserError('Exact placed cottage furnishing r2 required')
    if any(Path(p).stat().st_size > 8*1024**2 for p in (registry_path, survey_path, r2_path)):
        raise UserError('Light input exceeds finite read bound')
    registry, survey, placed = [json.loads(Path(p).read_text(encoding='utf-8')) for p in (registry_path, survey_path, r2_path)]
    if not Path(registry['world_path']).resolve().is_relative_to(home/'staging') or placed['world_path'] != registry['world_path'] or placed['seed'] != registry['seed']:
        raise UserError('Exact private staging world required')
    expected, _ = furnishing_delta(furnished(registry, survey), backup_sha)
    decode = lambda p: {(x, y, z): p['palette'][i] for x, y, z, i in p['blocks']}
    if decode(expected) != decode(placed) or expected['block_entities'] != placed['block_entities']:
        raise UserError('Furnishing source differs from exact placed r2')
    g = subprocess.run(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(GUARD), '-EstimatedCBytes', '0', '-EstimatedDBytes', str(MAX_BUNDLE)], capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW, check=False)
    guard = json.loads(g.stdout)
    if g.returncode or not guard.get('allowed'):
        raise UserError('Reserve guard refused finite light delta')
    d, changed, checks = construct(registry, survey)
    native = d.p.serialize(backup_sha)
    ox, oy, oz = d.p.origin
    native['blocks'] = [p for p in native['blocks'] if (p[0]-ox, p[1]-oy, p[2]-oz) in changed]
    native.update(name='Rose & Lantern Court — compact supported lights r3', baseline_sha256=R2_SHA, landmarks=[], block_entities=[])
    data = (json.dumps(native, ensure_ascii=False, separators=(',', ':'))+'\n').encode()
    sha = hashlib.sha256(data).hexdigest()
    manifest = {'format': 'awft-cottage-light-scale:3', 'created': utcnow(), 'plan_sha256': sha,
        'source_sha256': digest(Path(__file__)), 'baseline_r2_sha256': R2_SHA,
        'reviewed_staging_backup_sha256': backup_sha, 'changed_positions': len(changed),
        'existing_BEs_replayed': 0, 'all_existing_ceiling_chains_retained': True,
        'cause': 'Actual Macaw small_chandelier parent has 50 elements, raw bounds [-2.74923,-1.20948,-4.6] to [18.67423,17,20.6] pixels and 32 rotated elements; the actual cottage capture confirms an oversized near-ceiling fixture in the low room.',
        'correction': 'Compact hanging vanilla lanterns at exactly the supported fixture positions; no new low fixture or brightness-compensating giant lamp.',
        'checks': checks, 'storage_guard': guard, 'visual_status': 'Pending actual native scale and light review; owner acceptance not inferred'}
    receipt = (json.dumps(manifest, sort_keys=True, indent=2)+'\n').encode()
    if len(data)+len(receipt) > MAX_BUNDLE:
        raise UserError('Light bundle exceeds finite allocation')
    output.mkdir(parents=True, exist_ok=False)
    path = output/('rose-lantern-light-r3-'+sha[:16]+'.json')
    path.write_bytes(data)
    (output/'manifest.json').write_bytes(receipt)
    return {'plan': str(path), 'sha256': sha, 'changed_positions': len(changed), 'native_visual_review': 'pending'}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('registry', 'survey', 'r2', 'output'):
        p.add_argument('--'+name, type=Path, required=True)
    p.add_argument('--home', type=Path, default=Path(r'D:\A World for Two'))
    p.add_argument('--backup-sha256', required=True)
    a = p.parse_args()
    print(json.dumps(prepare(a.home, a.registry, a.survey, a.r2, a.output, a.backup_sha256), indent=2))
