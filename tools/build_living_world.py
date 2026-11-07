"""Compile the isolated adapter against existing named Java 21 APIs; never install it."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import zipfile
from pathlib import Path

from control_room.common import REPO, Layout, UserError, digest
from control_room.storage import Storage

PINS = {
    'smartvillagers-neoforge-1.21.1-2.0.0.jar': 'bbfbfacd7210def810dacf36352cc55f2b3169db5fa7befd90888dd9a74c1630',
    'chattingvillagers-neoforge-1.21.1-1.1.0.jar': 'a93084403db82eea6ec5069424aca0cedbf8c9592e41d4ab3658299ba34afd5a',
}


def build(home, dependencies, output, storage, jdk=Path(r'C:\Program Files\Java\jdk-21.0.10')):
    output, dependencies, home = Path(output).resolve(), Path(dependencies).resolve(), Path(home).resolve()
    if output.exists() or output.suffix != '.jar':
        raise UserError('Use a fresh adapter .jar output path')
    storage.reserve(16 * 1024**2, output)
    APIs = []
    for name, expected in PINS.items():
        file = dependencies / name
        if not file.is_file() or digest(file) != expected:
            raise UserError('Exact upstream compile artifact differs: ' + name)
        APIs.append(file)
    libraries = home / 'server/libraries'
    named = sorted(libraries.rglob('*-srg.jar'))
    if not named:
        raise UserError('Existing named Minecraft 1.21.1 compiler API is required; no installation is performed')
    client = Path(os.environ.get('APPDATA', '')) / 'PrismLauncher/libraries/net/minecraft/client/1.21.1-20240808.144430/client-1.21.1-20240808.144430-srg.jar'
    if not client.is_file() or digest(client) != 'a649bd3ce77f122d0f83ae1b37b4b303e662470f928b9bee5fbc76580805ffd4':
        raise UserError('Exact existing named Minecraft client API required for compilation only')
    APIs = [client, *named, *APIs, *sorted(libraries.rglob('*.jar'))]
    source = REPO / 'compat/living-world'
    work = output.parent / (output.stem + '-compile')
    work.mkdir(parents=True, exist_ok=False)
    classes = work / 'classes'
    classes.mkdir()
    args = work / 'javac.args'
    args.write_text('\n'.join(['--release', '21', '-proc:none', '-encoding', 'UTF-8', '-classpath',
        '"' + os.pathsep.join(str(p).replace('\\', '/') for p in APIs) + '"',
        '-d', '"' + str(classes).replace('\\', '/') + '"',
        *['"' + str(p).replace('\\', '/') + '"' for p in sorted((source/'src').rglob('*.java'))]]), encoding='utf-8')
    result = subprocess.run([str(jdk/'bin/javac.exe'), '-J-Xmx256m', '-J-XX:ActiveProcessorCount=2', '@'+str(args)],
        capture_output=True, text=True, timeout=60,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
    (work/'compiler.txt').write_text(result.stdout+result.stderr, encoding='utf-8')
    if result.returncode:
        raise UserError('Adapter compilation failed: ' + result.stderr[:5000])
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, 'x', zipfile.ZIP_DEFLATED) as archive:
        for root in [classes, source/'resources']:
            for path in sorted(root.rglob('*')):
                if path.is_file():
                    entry = zipfile.ZipInfo(path.relative_to(root).as_posix(), (2026, 10, 28, 0, 0, 0))
                    entry.compress_type = zipfile.ZIP_DEFLATED
                    archive.writestr(entry, path.read_bytes())
    storage.checkpoint(16*1024**2, output)
    return {'artifact': str(output), 'sha256': digest(output), 'bytes': output.stat().st_size,
            'evidence': 'Java 21 compilation against existing Minecraft/NeoForge and pinned mod APIs; no game launched',
            'inputs': PINS}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--home', type=Path, required=True)
    parser.add_argument('--dependencies', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args=parser.parse_args()
    print(json.dumps(build(args.home,args.dependencies,args.output,Storage(Layout(args.home))),indent=2))


if __name__=='__main__':
    main()
