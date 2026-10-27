"""Read-only pinned BDD/BlueLib asset and class-identity evidence, no game launch.

Prints a sanitized report only. No extraction, install, texture aliases or entity
NBT reads/writes. The bytecode interpretation is documented separately; constant
pool references alone are not a runtime cache-state witness.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
import zipfile
from pathlib import Path


BDD_SHA256 = '456cbab81fb3762cc2a981fa60eb545c22c9587602c8e4275b7d87e6f2f41e60'
BLUE_SHA256 = 'efcbc58b6f0f06062f4c8c937e049b21be3fab37f76285dd5078b6a927cc486b'
SPECIES = {'nightfury': 'nightfury', 'terrible_terror': 'terrible_terror'}
MAX_JAR = 32 * 1024**2


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def identified(path, expected):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or not 1 <= path.stat().st_size <= MAX_JAR:
        raise ValueError('Missing, linked or oversized pinned input')
    with path.open('rb') as stream:
        raw = stream.read(MAX_JAR + 1)
    if len(raw) > MAX_JAR or sha(raw) != expected:
        raise ValueError('Exact installed input differs from the investigated pin')
    return {'file': path.name, 'bytes': len(raw), 'sha256': expected}


def utf8_constants(raw):
    """Inspect JVM constant pool strings without loading a Java/game class."""
    if len(raw) > 512 * 1024 or raw[:4] != b'\xca\xfe\xba\xbe':
        raise ValueError('Unbounded or invalid class file')
    count = int.from_bytes(raw[8:10], 'big'); offset = 10; index = 1; values = set()
    sizes = {3: 4, 4: 4, 5: 8, 6: 8, 7: 2, 8: 2, 9: 4, 10: 4,
             11: 4, 12: 4, 15: 3, 16: 2, 17: 4, 18: 4, 19: 2, 20: 2}
    while index < count:
        if offset >= len(raw):
            raise ValueError('Truncated class constant pool')
        tag = raw[offset]; offset += 1
        if tag == 1:
            if offset + 2 > len(raw):
                raise ValueError('Truncated UTF8 constant')
            size = int.from_bytes(raw[offset:offset + 2], 'big'); offset += 2
            values.add(raw[offset:offset + size].decode('utf-8', 'replace')); offset += size
        elif tag in sizes:
            offset += sizes[tag]
            if tag in (5, 6):
                index += 1
        else:
            raise ValueError('Unknown class constant-pool tag')
        if offset > len(raw):
            raise ValueError('Truncated class constant pool')
        index += 1
    return values


def class_identity(archive, name):
    info = archive.getinfo(name)
    if info.file_size > 512 * 1024:
        raise ValueError('Unbounded class entry')
    raw = archive.read(info)
    return {'class': name, 'sha256': sha(raw), 'bytes': len(raw)}, utf8_constants(raw)


def null_failure_counts(path):
    path = Path(path)
    if not path.is_file() or path.stat().st_size > 16 * 1024**2:
        raise ValueError('Missing or oversized client log')
    counts = dict.fromkeys(SPECIES, 0)
    with path.open('r', encoding='utf-8', errors='replace') as stream:
        for line in stream:
            for species in counts:
                if 'Failed to load texture:' in line and f'bdd:dragons/{species}/male/null_male.png' in line:
                    counts[species] += 1
    return counts


def investigate(server_jar, client_jar, bluelib_jar, client_log=None):
    server = identified(server_jar, BDD_SHA256); client = identified(client_jar, BDD_SHA256)
    blue = identified(bluelib_jar, BLUE_SHA256)
    result = {'format': 'awft-dragon-texture-investigation:1',
              'tier': 'Pinned asset/metadata/class inspection; no native runtime cache witness or visual acceptance',
              'server_bdd': server, 'client_bdd': client, 'bluelib': blue,
              'client_server_bdd_identical': server['sha256'] == client['sha256'],
              'licenses': {'bdd': 'All rights reserved; no third-party bytes copied', 'bluelib': 'MIT'},
              'official_bluelib_source_commit': '2c1c373ea8ffc4aeec10234fc1a1ff2eaafd07ae',
              'assets': {}, 'classes': []}
    with zipfile.ZipFile(server_jar) as archive:
        names = set(archive.namelist())
        for species, variant in SPECIES.items():
            metadata = json.loads(archive.read(f'data/bdd/dragons/{species}/{variant}.json'))
            row = metadata[variant][0]
            # Original default metadata identifies these real resources. This is
            # an existence check, not a replacement for variant-aware rendering.
            stem = row['adult'].split('/')[-1]
            real = f'assets/bdd/dragons/{species}/male/{stem}_male.png'
            missing = f'assets/bdd/dragons/{species}/male/null_male.png'
            png = archive.read(real)
            if png[:8] != b'\x89PNG\r\n\x1a\n':
                raise ValueError('The original default texture is not a PNG')
            result['assets'][species] = {'requested_missing': missing, 'requested_exists': missing in names,
                'default_original_exists': real in names, 'default_original_file': real,
                'default_original_sha256': sha(png),
                'default_original_dimensions': list(struct.unpack('>II', png[16:24])),
                'installed_species_pngs': sum(n.startswith(f'assets/bdd/dragons/{species}/') and n.endswith('.png') for n in names),
                'default_has_adult_and_child_metadata': isinstance(row.get('adult'), str) and isinstance(row.get('child'), str)}
        for name in ('com/bdc/bdd/api/entity/core_classes/BddBaseDragon.class',
                     'com/bdc/bdd/api/model/BddDragonModel.class'):
            identity, _ = class_identity(archive, name); result['classes'].append(identity)
        # A bounded reference census supports the manual javap/source finding:
        # BDD has no compiled ResourceCache.Server/EntityCache synchronization path.
        references = []
        for info in archive.infolist():
            if info.filename.endswith('.class'):
                _, constants = class_identity(archive, info.filename)
                if any(s in constants for s in ('software/bluelib/loader/cache/ResourceCache$Server',
                                               'software/bluelib/loader/cache/variants/EntityCache')):
                    references.append(info.filename)
        result['bdd_variant_cache_class_references'] = references
    with zipfile.ZipFile(bluelib_jar) as archive:
        for name in ('software/bluelib/api/utils/variant/ParameterUtils.class',
                     'software/bluelib/loader/cache/ResourceCache$Server.class',
                     'software/bluelib/net/messages/client/variant/VariantsPacket.class',
                     'software/bluelib/BlueLib.class'):
            identity, constants = class_identity(archive, name)
            identity['reference_evidence'] = sorted(c for c in constants if c in (
                'software/bluelib/loader/cache/ResourceCache$Server', 'getVariants', 'VARIANTS',
                'java/util/Collections', 'emptyMap', 'allVariants', 'Ljava/util/Set;',
                'software/bluelib/net/messages/client/loader/ControllerCachePacket'))
            result['classes'].append(identity)
    if client_log:
        result['observed_missing_texture_warnings'] = null_failure_counts(client_log)
    result['world_or_entity_changes'] = 0
    result['deployed_fix'] = False
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('server-jar', 'client-jar', 'bluelib-jar'):
        parser.add_argument('--' + key, type=Path, required=True)
    parser.add_argument('--client-log', type=Path)
    print(json.dumps(investigate(**vars(parser.parse_args())), indent=2))
