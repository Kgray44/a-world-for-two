"""Reproducible client-only presentation glue, compiled against the pinned client."""
from __future__ import annotations

import os
import hashlib
import subprocess
import zipfile
from pathlib import Path

from control_room.common import REPO, UserError, digest

PRESENTATION_VERSION = '0.2.3'


def zipline_apis(home):
    """Exact compile-only APIs. No third-party class enters the owned JAR."""
    pins = (
        ('zipline-1.5.3+1.21.1-neoforge.jar', 89295,
         '47db8340965b18aefc3d809af9fecc9e0e0a05a01da59e40bf66cca135c91ed182fbb46ee249682e56ffb46c22723491b48827a34ee75d01dd7a3c8045cee334'),
        ('connectiblechains-2.4.4+1.21.1-neoforge.jar', 293575,
         'c09a3a354a26ce0dc511c2364332975222fae8515101f524de5e724f3a191eb75ffb4f381b8c78907f885d7a7e86f1ce7b883d56921fb5f31709466446efe00a'),
    )
    result = []
    for filename, size, expected in pins:
        path = Path(home)/'caches/mods'/filename
        if (not path.is_file() or path.is_symlink() or path.stat().st_size != size
                or hashlib.sha512(path.read_bytes()).hexdigest() != expected):
            raise UserError('Exact pinned compile-only zipline API is required: '+filename)
        result.append(path)
    return result


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
    jars = [named] + zipline_apis(home) + sorted(libraries.rglob('*.jar'))
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
        'selection_reason':'Owned native menu toolbar, cinematic arbitration, bounded client measurements, Small Ships remote-config lifecycle correction and real loaded-chain handoff provider. Native ZiplineLogic retains rider movement and collision.',
        'status':'Integrated but awaiting runtime validation', 'validation':{'metadata':'pass','jar':'pending','runtime':'not run'}}
