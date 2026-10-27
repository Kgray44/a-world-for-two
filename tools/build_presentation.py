"""Reproducible client-only presentation glue, compiled against the pinned client."""
from __future__ import annotations

import os
import subprocess
import zipfile
from pathlib import Path

from control_room.common import REPO, UserError, digest

PRESENTATION_VERSION = '0.2.2'


def build(home, destination, storage):
    storage.reserve(16 * 1024 * 1024, destination)
    if destination.exists():
        raise UserError('Presentation output already exists; use a fresh owned directory')
    prism_libraries = Path(os.environ['APPDATA']) / 'PrismLauncher/libraries'
    named = prism_libraries / 'net/minecraft/client/1.21.1-20240808.144430/client-1.21.1-20240808.144430-srg.jar'
    if not named.is_file():
        raise UserError('Prepare the pinned NeoForge 1.21.1 client before compiling its presentation helper')
    work = destination.parent / 'compile-presentation'
    classes = work / 'classes'
    classes.mkdir(parents=True)
    libraries = home / 'server/libraries'
    jars = [named] + sorted(libraries.rglob('*.jar'))
    cp = os.pathsep.join(p.as_posix() for p in jars)
    source = REPO / 'compat/client-presentation'
    sources = sorted((source / 'src').rglob('*.java'))
    args = work / 'javac.args'
    args.write_text('-proc:none\n--release\n21\n-classpath\n"' + cp + '"\n-d\n"' + classes.as_posix() + '"\n' + '\n'.join('"' + p.as_posix() + '"' for p in sources) + '\n', encoding='utf-8')
    compiler = Path(r'C:\Program Files\Java\jdk-21.0.10\bin\javac.exe')
    result = subprocess.run([str(compiler), '-J-Xmx128m', '-J-XX:ActiveProcessorCount=2', '@' + str(args)],
                            capture_output=True, text=True, timeout=60,
                            creationflags=(subprocess.CREATE_NO_WINDOW | subprocess.BELOW_NORMAL_PRIORITY_CLASS)
                            if os.name == 'nt' else 0)
    (work / 'javac.log').write_text(result.stdout + result.stderr, encoding='utf-8')
    if result.returncode:
        raise UserError('Client presentation compilation failed: ' + result.stderr[:3000])
    with zipfile.ZipFile(destination, 'x', zipfile.ZIP_DEFLATED) as archive:
        for root in (classes, source / 'resources'):
            for path in sorted(root.rglob('*')):
                if path.is_file():
                    entry = zipfile.ZipInfo(path.relative_to(root).as_posix(), (2026, 1, 1, 0, 0, 0))
                    entry.compress_type = zipfile.ZIP_DEFLATED
                    archive.writestr(entry, path.read_bytes())
    return {'project_id':'awft:client-presentation', 'slug':'awft-client-presentation', 'name':'A World for Two Presentation',
        'version_id':PRESENTATION_VERSION, 'version':PRESENTATION_VERSION, 'provider':'local-build', 'release_type':'candidate',
        'filename':destination.name, 'url':'https://github.com/Kgray44/a-world-for-two/releases/download/compat-0.1.0/' + destination.name,
        'size':destination.stat().st_size, 'hashes':{'sha256':digest(destination)}, 'side':'client', 'kind':'mod',
        'request':None, 'world_sensitive':False, 'optional':False, 'default':True, 'dependencies':[],
        'license':{'id':'MIT'}, 'source':'https://github.com/Kgray44/a-world-for-two',
        'selection_reason':'Owned native menu toolbar, cinematic arbitration, bounded client measurements and Small Ships remote-config lifecycle correction. No world renderer or player movement.',
        'status':'Integrated but awaiting runtime validation', 'validation':{'metadata':'pass','jar':'pending','runtime':'not run'}}
