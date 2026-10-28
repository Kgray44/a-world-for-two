"""Offline pinned Minecraft spacing-API vectors. No loader, server, mods or save."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import time
from pathlib import Path

from control_room.common import REPO, UserError, digest, write_json
from tools.worldgen_audit import grid_candidates


def run(home, output):
    from tools.playtest import guard
    output = Path(output).resolve()
    if output.exists() or not output.is_relative_to(REPO / 'evidence/worldgen'):
        raise UserError('Use a new offline-probe receipt under evidence/worldgen')
    reserve = guard(2 * 1024**2, 8 * 1024**2)
    home = Path(home)
    work = home / 'staging/worldgen-grid-probes' / str(time.time_ns())
    work.mkdir(parents=True)
    classes, temporary = work / 'classes', work / 'tmp'
    classes.mkdir()
    temporary.mkdir()
    library = home / 'server/libraries'
    named = library / 'net/minecraft/server/1.21.1-20240808.144430/server-1.21.1-20240808.144430-srg.jar'
    expected = '26ca9c40d7e1681190b428583c38816852218e78df3f8bdb60a59a78503aec71'
    if digest(named) != expected:
        raise UserError('Pinned Minecraft spacing API differs')
    jars = [named] + [p for p in sorted(library.rglob('*.jar')) if p != named]
    cp = os.pathsep.join(p.as_posix() for p in jars)
    source = REPO / 'compat/worldgen-qa/probes/RandomSpreadMathProbe.java'
    args = work / 'javac.args'
    args.write_text('-proc:none\n--release\n21\n-classpath\n"' + cp + '"\n-d\n"' +
                    classes.as_posix() + '"\n"' + source.as_posix() + '"\n', encoding='utf8')
    java = Path(r'C:\Program Files\Java\jdk-21.0.10\bin')
    flags = subprocess.CREATE_NO_WINDOW | subprocess.BELOW_NORMAL_PRIORITY_CLASS
    result = subprocess.run([str(java / 'javac.exe'), '-J-Xmx192m', '-J-XX:ActiveProcessorCount=1',
        '@' + str(args)], capture_output=True, text=True, timeout=60, creationflags=flags)
    (work / 'javac.log').write_text(result.stdout + result.stderr, encoding='utf8')
    receipt = {'format': 'awft-offline-engine-spacing-api:1',
        'tier': 'OFFLINE_ENGINE_RNG_SPREAD_PRIMITIVES_NOT_FULL_PLACEMENT_OR_WORLD_GENERATION',
        'invoked_native_methods': ['WorldgenRandom.setLargeFeatureWithSalt', 'RandomSpreadType.evaluate'],
        'full_placement_constructor': 'NOT RUN; the original offline full-API attempt requires Minecraft Bootstrap',
        'compile_exit_code': result.returncode, 'reserve': reserve,
        'source_sha256': digest(source), 'minecraft_srg_sha256': expected,
        'server_started': False, 'mods_loaded': False, 'worlds_opened': 0,
        'heap_limit_mib': 192, 'cpu_count': 1}
    if result.returncode:
        write_json(output, dict(receipt, status='COMPILE_FAILED_PRESERVED'))
        raise UserError('Spacing API probe compile failed: ' + result.stderr[:2000])
    args = work / 'java.args'
    args.write_text('-Xms32m\n-Xmx192m\n-XX:ActiveProcessorCount=1\n"-Djava.io.tmpdir=' + temporary.as_posix() +
        '"\n-classpath\n"' + classes.as_posix() + os.pathsep + cp + '"\nRandomSpreadMathProbe\n', encoding='utf8')
    result = subprocess.run([str(java / 'java.exe'), '@' + str(args)], capture_output=True, text=True,
                            timeout=60, creationflags=flags, cwd=work)
    (work / 'java.log').write_text(result.stdout + result.stderr, encoding='utf8')
    receipt['api_process_exit_code'] = result.returncode
    if result.returncode:
        write_json(output, dict(receipt, status='OFFLINE_API_EXECUTION_FAILED_PRESERVED'))
        raise UserError('Offline API probe failed; private diagnostics retained: ' + result.stderr[:2000])
    vectors = [line[len('AWFT_GRID '):] for line in result.stdout.splitlines() if line.startswith('AWFT_GRID ')]
    mismatches = []
    for line in vectors:
        seed, spacing, separation, salt, spread, x, z, expected_x, expected_z = line.split(',')
        placement = {'type': 'minecraft:random_spread', 'spacing': int(spacing),
                     'separation': int(separation), 'salt': int(salt), 'spread_type': spread}
        point = int(expected_x), int(expected_z)
        if grid_candidates(int(seed), placement, point, 1) != [point]:
            mismatches.append(line)
    receipt.update(vector_count=len(vectors), expected_vectors=1440, mismatch_count=len(mismatches),
        mismatches=mismatches, vector_output_sha256=hashlib.sha256(('\n'.join(vectors)+'\n').encode()).hexdigest(),
        coverage=['six baseline/proposed spacing profiles', 'linear and triangular spread',
                  'five synthetic seeds including signed-long extremes', 'four salts including signed-int maximum',
                  'negative regions and world-border-scale chunk coordinates'])
    receipt['status'] = 'PASS' if len(vectors) == 1440 and not mismatches else 'FAILED_VECTORS_PRESERVED'
    write_json(output, receipt)
    if receipt['status'] != 'PASS':
        raise UserError('Offline engine vectors differ from the grid sampler')
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--home', type=Path, default=Path(r'D:\A World for Two'))
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = run(args.home, args.output)
    print(json.dumps({k: result[k] for k in ('status', 'vector_count', 'mismatch_count', 'server_started')}))


if __name__ == '__main__':
    main()
