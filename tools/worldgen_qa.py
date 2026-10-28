"""Compile the release-excluded native sampler. Does not prepare/start a server."""
from __future__ import annotations

import argparse
import os
import subprocess
import time
import zipfile
from pathlib import Path

from control_room.common import REPO, UserError, digest, write_json


def build(home, output):
    from tools.playtest import guard
    home, output = Path(home).resolve(), Path(output).resolve()
    allowed = home / 'staging/worldgen-audit-builds'
    if output.exists() or not output.is_relative_to(allowed):
        raise UserError('Use a new owned compile directory under staging/worldgen-audit-builds')
    reserve = guard(2 * 1024**2, 16 * 1024**2)
    library = home / 'server/libraries'
    named = library / 'net/minecraft/server/1.21.1-20240808.144430/server-1.21.1-20240808.144430-srg.jar'
    universal = library / 'net/neoforged/neoforge/21.1.262/neoforge-21.1.262-universal.jar'
    if not named.is_file() or not universal.is_file():
        raise UserError('Exact installed Minecraft1.21.1/NeoForge21.1.262 compile APIs are required')
    jars = [named, universal] + [p for p in sorted(library.rglob('*.jar')) if p not in (named, universal)]
    compiler = Path(r'C:\Program Files\Java\jdk-21.0.10\bin\javac.exe')
    if not compiler.is_file():
        raise UserError('The pinned installed Java21.0.10 compiler is required')
    source = REPO / 'compat/worldgen-qa'
    files = sorted((source / 'src').rglob('*.java'))
    output.mkdir(parents=True)
    classes = output / 'classes'
    classes.mkdir()
    argfile = output / 'javac.args'
    argfile.write_text('-proc:none\n--release\n21\n-classpath\n"' +
        os.pathsep.join(p.as_posix() for p in jars) + '"\n-d\n"' + classes.as_posix() + '"\n' +
        '\n'.join('"' + p.as_posix() + '"' for p in files) + '\n', encoding='utf8')
    result = subprocess.run([str(compiler), '-J-Xmx256m', '-J-XX:ActiveProcessorCount=2', '@' + str(argfile)],
        capture_output=True, text=True, timeout=60,
        creationflags=subprocess.CREATE_NO_WINDOW | subprocess.BELOW_NORMAL_PRIORITY_CLASS)
    (output / 'javac.log').write_text(result.stdout + result.stderr, encoding='utf8')
    receipt = {'format': 'awft-worldgen-qa-build:1', 'compile_exit_code': result.returncode,
        'reserve': reserve, 'source_hashes': {p.relative_to(REPO).as_posix(): digest(p) for p in files},
        'api_hashes': {'minecraft-srg': digest(named), 'neoforge-universal': digest(universal)},
        'native_server_started': False, 'worlds_created': 0,
        'tier': 'exact installed API compilation only; not native execution'}
    write_json(output / 'build-receipt.json', receipt)
    if result.returncode:
        raise UserError('QA compilation failed; preserved diagnostics: ' + result.stderr[:4000])
    artifact = output / 'awft-worldgen-qa-0.1.0.jar'
    with zipfile.ZipFile(artifact, 'x', zipfile.ZIP_DEFLATED) as archive:
        for directory in (classes, source / 'resources'):
            for path in sorted(directory.rglob('*')):
                if not path.is_file():
                    continue
                entry = zipfile.ZipInfo(path.relative_to(directory).as_posix(), (2026, 1, 1, 0, 0, 0))
                entry.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(entry, path.read_bytes())
    receipt.update(jar_sha256=digest(artifact), jar_bytes=artifact.stat().st_size)
    write_json(output / 'build-receipt.json', receipt)
    return artifact, receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--home', type=Path, default=Path(r'D:\A World for Two'))
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    output = args.output or args.home / 'staging/worldgen-audit-builds' / str(time.time_ns())
    artifact, receipt = build(args.home, output)
    print(__import__('json').dumps({'artifact': str(artifact), 'sha256': receipt['jar_sha256'],
                                  'bytes': receipt['jar_bytes'], 'native_server_started': False}))


if __name__ == '__main__':
    main()
