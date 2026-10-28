"""Explicit structural bays, path cross-drains and garden divisions after r3.

This is a separate delta against the exact placed r3. The architectural grid is
declared before checking observations: 8-metre construction bays have transverse
joints, court paving has matching drainage bands, and garden beds have narrow
earth divisions. No facing trick, random recoloring, inventory replay or world
operation is used. The owner still has to judge the actual appearance.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

from control_room.common import UserError, digest, utcnow
from tools.artistic_materials import require_outdoor_rule
from tools.artistic_street import designs, GUARD, MAX_BUNDLE, MIB
from tools.artistic_street_life import construct as lived_in, check as life_check, native_delta as life_delta
from tools.artistic_street_details import Details


R3_SHA = '30c727fc31104a457dd98123c1010a664cd0dd995ba77f3c67f83187860d0325'
X_JOINTS = (8, 17, 26, 35, 44, 53)
Z_JOINTS = (8, 17, 26, 35)


def construct(registry):
    original = lived_in(registry)
    d = Details(original.p)
    building_names = {b.name for b in designs()}
    changes = {}
    for pos, state in d.base.blocks.items():
        x, y, z = pos
        if d.base.owners[pos] in building_names or pos in d.protected:
            continue
        key = state.split('[', 1)[0]
        xjoint, zjoint = x in X_JOINTS, z in Z_JOINTS
        if not (xjoint or zjoint):
            continue
        if key == 'minecraft:stone':
            replacement = 'minecraft:chiseled_stone_bricks' if xjoint and zjoint else 'minecraft:deepslate_bricks' if xjoint else 'minecraft:packed_mud'
        elif key in ('minecraft:andesite', 'minecraft:cobblestone', 'minecraft:stone_bricks'):
            replacement = 'minecraft:chiseled_stone_bricks' if xjoint and zjoint else 'minecraft:polished_andesite' if xjoint else 'minecraft:mossy_cobblestone'
        elif key == 'minecraft:grass_block':
            replacement = 'minecraft:gravel' if xjoint and zjoint else 'minecraft:coarse_dirt' if xjoint else 'minecraft:rooted_dirt'
        else:
            continue
        d.p.zone = d.base.owners[pos]
        d.put(*pos, replacement)
        changes[pos] = {'before': state, 'after': replacement,
                        'purpose': 'buried construction joint' if key == 'minecraft:stone' else 'garden bed division' if key == 'minecraft:grass_block' else 'masonry cross-drain / quay bay joint'}
    # Original life checks still examine the complete furnished geometry.
    original.p = d.p
    checks = life_check(original)
    require_outdoor_rule(d.p.blocks,'authored street surfaces')
    return d, changes, checks


def prepare(home, registry_path, r3_path, output, backup_sha):
    home, output = Path(home).resolve(), Path(output).resolve()
    if home.drive.upper() != 'D:' or not output.is_relative_to(home/'staging') or output.exists():
        raise UserError('Use a NEW private bounded D: staging folder')
    if not re.fullmatch('[0-9a-f]{64}', backup_sha) or digest(Path(r3_path)) != R3_SHA:
        raise UserError('Exact placed r3 and reviewed current staging backup required')
    if max(Path(registry_path).stat().st_size, Path(r3_path).stat().st_size) > 8*MIB:
        raise UserError('Surface input exceeds finite read bound')
    registry = json.loads(Path(registry_path).read_text(encoding='utf-8'))
    previous = json.loads(Path(r3_path).read_text(encoding='utf-8'))
    if not Path(registry['world_path']).resolve().is_relative_to(home/'staging') or previous['world_path'] != registry['world_path'] or previous['seed'] != registry['seed']:
        raise UserError('Exact private staging world required')
    expected, _ = life_delta(lived_in(registry), backup_sha)
    decode = lambda p: {(x, y, z): p['palette'][i] for x, y, z, i in p['blocks']}
    if decode(expected) != decode(previous) or expected['block_entities'] != previous['block_entities']:
        raise UserError('Frozen r3 source no longer matches its exact placed delta')
    guard = subprocess.run(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(GUARD), '-EstimatedCBytes', '0', '-EstimatedDBytes', str(MAX_BUNDLE)], capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW, check=False)
    reserve = json.loads(guard.stdout)
    if guard.returncode or not reserve.get('allowed'):
        raise UserError('Reserve guard refused bounded surface bundle')
    d, changes, checks = construct(registry)
    if not 0 < len(changes) <= 6_000:
        raise UserError('Surface delta exceeded its finite scope')
    native = d.p.serialize(backup_sha)
    ox, oy, oz = d.p.origin
    native['blocks'] = [row for row in native['blocks'] if (row[0]-ox, row[1]-oy, row[2]-oz) in changes]
    native.update(name='Signal Lane — outdoor construction bays and cross-drains r4', baseline_sha256=R3_SHA, block_entities=[], landmarks=[])
    data = (json.dumps(native, ensure_ascii=False, separators=(',', ':'))+'\n').encode()
    sha = hashlib.sha256(data).hexdigest()
    manifest = {'format': 'awft-street-surface-joints:4', 'created': utcnow(), 'prototype_only': True,
        'source_sha256': digest(Path(__file__)), 'baseline_r3_sha256': R3_SHA, 'plan_sha256': sha,
        'reviewed_staging_backup_sha256': backup_sha, 'placements': len(changes), 'block_entities_replayed': 0,
        'declared_x_joint_stations': list(X_JOINTS), 'declared_z_joint_stations': list(Z_JOINTS),
        'outdoor_material_rule': require_outdoor_rule(d.p.blocks,'authored street surfaces'), 'complete_building_rules': checks['materials'],
        'furniture_and_circulation_checks': checks, 'storage_guard': reserve,
        'changes': [{'local': list(p)}|v for p, v in sorted(changes.items())],
        'visual_status': 'Pending actual native review of outdoor paving and garden composition; no artistic acceptance inferred'}
    receipt = (json.dumps(manifest, sort_keys=True, indent=2)+'\n').encode()
    if len(data)+len(receipt) > MAX_BUNDLE:
        raise UserError('Surface bundle exceeds finite allocation')
    output.mkdir(parents=True, exist_ok=False)
    path = output/('signal-lane-surface-r4-'+sha[:16]+'.json')
    path.write_bytes(data)
    (output/'manifest.json').write_bytes(receipt)
    return {'plan': str(path), 'sha256': sha, 'placements': len(changes), 'native_visual_review': 'pending'}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--home', type=Path, default=Path(r'D:\A World for Two'))
    p.add_argument('--registry', type=Path, required=True)
    p.add_argument('--r3', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--backup-sha256', required=True)
    a = p.parse_args()
    print(json.dumps(prepare(a.home, a.registry, a.r3, a.output, a.backup_sha256), indent=2))
