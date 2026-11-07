"""Bounded MIT Diorama native-model repair; upstream artifact remains intact."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import zipfile
from pathlib import Path

from control_room.common import REPO, UserError, digest, write_json
from tools.playtest import guard

UPSTREAM_SHA512 = 'e19c3f4a97eb5ed1941beeabb500fa8fda2d5602ede6ff6d6d5c77bb670b4ae686fc4d4b574434f638bdab8007b75531c87e2e07789fb003e75813c925e9a772'
VERSION = '0.7.0+awft.1-neoforge-1.21.1'
CLASSES = ('dev/diorama/bake/BlockLooks.class', 'dev/diorama/bake/BlockLooks$LegacyPart.class')


def build(source, output, libraries):
    source, output, libraries = Path(source), Path(output), Path(libraries)
    if source.stat().st_size != 924656 or digest(source, 'sha512') != UPSTREAM_SHA512:
        raise UserError('Diorama repair requires the exact reviewed official 0.7.0 NeoForge 1.21.1 JAR')
    if output.exists():
        raise UserError('Preserve an existing build; choose a new output directory')
    guard(1024 * 1024, 8 * 1024 * 1024)
    output.mkdir(parents=True)
    jars = [libraries / f'org/ow2/asm/{name}/9.10.1/{name}-9.10.1.jar' for name in ('asm', 'asm-tree')]
    if not all(p.is_file() for p in jars):
        raise UserError('Reviewed ASM 9.10.1 libraries are required')
    cp = os.pathsep.join(map(str, jars))
    jdk = Path(r'C:\Program Files\Java\jdk-21.0.10\bin')
    flags = {'capture_output': True, 'text': True, 'timeout': 60,
             'creationflags': subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0}
    subprocess.run([str(jdk/'javac.exe'), '--release', '21', '-cp', cp, '-d', str(output),
                    str(REPO/'compat/diorama/NativeModels.java')], check=True, **flags)
    replacements = {}
    with zipfile.ZipFile(source) as original:
        for index, name in enumerate(CLASSES):
            before, after = output/f'before-{index}.class', output/f'after-{index}.class'
            before.write_bytes(original.read(name))
            subprocess.run([str(jdk/'java.exe'), '-cp', str(output)+os.pathsep+cp, 'NativeModels',
                            str(before), str(after)], check=True, **flags)
            replacements[name] = after.read_bytes()
        meta = original.read('META-INF/neoforge.mods.toml').decode()
        if meta.count('version = "0.7.0+neoforge-1.21.1"') != 1:
            raise UserError('Diorama descriptor changed; review the repair again')
        replacements['META-INF/neoforge.mods.toml'] = meta.replace('version = "0.7.0+neoforge-1.21.1"', 'version = "'+VERSION+'"').encode()
        destination = output / ('diorama-'+VERSION+'.jar')
        provenance = {'upstream_sha512': UPSTREAM_SHA512, 'upstream_source': 'https://github.com/SunkenInTime/diorama/tree/v0.7.0',
            'version': VERSION, 'changed_entries': list(replacements), 'license': 'MIT; original LICENSE_diorama retained unchanged',
            'reason': 'Call NeoForge model-data-aware quad and particle APIs with ModelData.EMPTY and all render layers. Preserve existing fallbacks; no world/player logic or other class changes.'}
        with zipfile.ZipFile(destination, 'x') as result:
            for info in original.infolist():
                result.writestr(info, replacements.get(info.filename, original.read(info)))
            result.writestr(zipfile.ZipInfo('META-INF/awft-diorama-repair.json', (2026,1,1,0,0,0)), json.dumps(provenance, indent=2))
    with zipfile.ZipFile(source) as original, zipfile.ZipFile(destination) as result:
        if result.testzip(): raise UserError('Corrupt repaired JAR')
        for name in original.namelist():
            if name not in replacements and original.read(name) != result.read(name):
                raise UserError('Unrequested upstream entry changed')
    provenance.update(filename=destination.name, sha256=digest(destination), size=destination.stat().st_size,
                      runtime='not run; do not promote from a successful build alone')
    write_json(output/'provenance.json', provenance)
    return provenance


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--libraries', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.source, args.output, args.libraries), indent=2))
