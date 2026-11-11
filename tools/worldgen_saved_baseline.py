"""Read actual saved chunk observations from a verified historical archive only.

No Minecraft process, extraction, live-world read, or world modification. This
does not produce fresh-generation timing or an updated-profile A/B result.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import math
import re
import time
import zipfile
from pathlib import Path

from control_room.common import REPO, UserError, digest, write_json
from tools.settlement_attractions import NBTReader


def packed_value(values, index, bits):
    if not 1 <= bits <= 32 or index < 0:
        raise UserError('Invalid packed value request')
    per = 64 // bits
    if index // per >= len(values):
        raise UserError('Packed observation is truncated')
    return (int(values[index // per]) >> ((index % per) * bits)) & ((1 << bits) - 1)


def decode_record(raw, slot):
    import zlib
    if len(raw) < 8192 or not 0 <= slot < 1024:
        raise UserError('Invalid region header or chunk slot')
    location = int.from_bytes(raw[slot*4:slot*4+4], 'big')
    sector, count = location >> 8, location & 255
    if not sector:
        return None
    offset = sector * 4096
    if sector < 2 or not count or offset + 5 > len(raw):
        raise UserError('Invalid saved chunk sector')
    length = int.from_bytes(raw[offset:offset+4], 'big')
    if not 1 < length <= count * 4096 - 4 or offset + 4 + length > len(raw):
        raise UserError('Invalid saved chunk record length')
    compression = raw[offset+4]
    data = raw[offset+5:offset+4+length]
    if compression == 3:
        decoded = data
    elif compression in (1, 2):
        stream = zlib.decompressobj(31 if compression == 1 else 15)
        decoded = stream.decompress(data, 16 * 1024**2 + 1)
        if not stream.eof or stream.unused_data or stream.unconsumed_tail:
            raise UserError('Bounded complete chunk decompression refused')
    else:
        raise UserError('Unsupported/external MCA compression; preserve and investigate')
    if len(decoded) > 16 * 1024**2:
        raise UserError('Chunk NBT exceeds its bounded reader')
    return NBTReader(decoded).read(), hashlib.sha256(decoded).hexdigest()


def observe(archive_path, expected_sha256, prefix, private_output):
    if not re.fullmatch(r'world/[A-Za-z0-9_-]+/region/', prefix):
        raise UserError('A single explicit archived overworld region prefix is required')
    if digest(archive_path) != expected_sha256:
        raise UserError('Verified checkpoint digest differs')
    full, all_chunks, partial, biomes, starts, heights, pins = [], [], collections.Counter(), collections.Counter(), {}, [], []
    remaining, began = 256 * 1024**2, time.monotonic()
    with zipfile.ZipFile(archive_path) as archive:
        if archive.getinfo('awft-backup.json').file_size > 8 * 1024**2:
            raise UserError('Archive manifest exceeds its reader bound')
        manifest = json.loads(archive.read('awft-backup.json'))
        entries = {r['path']: r for r in manifest['files']}
        if len(entries) != len(manifest['files']):
            raise UserError('Duplicate checkpoint manifest paths')
        names = sorted(n for n in archive.namelist() if n.startswith(prefix) and n.endswith('.mca'))
        if not names or len(names) > 256:
            raise UserError('A bounded nonempty archived region inventory is required')
        for name in names:
            size = archive.getinfo(name).file_size
            if size > min(64 * 1024**2, remaining):
                raise UserError('Archived region allocation bound exceeded')
            remaining -= size
            raw = archive.read(name)
            if hashlib.sha256(raw).hexdigest() != entries[name]['sha256']:
                raise UserError('Region differs from its retained checkpoint manifest')
            pins.append({'member': name, 'sha256': entries[name]['sha256'], 'bytes': len(raw)})
            if not raw:
                # Preserve and identify an empty archive member explicitly. It
                # contains no allocated chunk records; do not label it a valid
                # MCA header, generated terrain, or proven native corruption.
                pins[-1]['observation'] = 'ZERO_LENGTH_MEMBER_NO_CHUNK_RECORDS_NATIVE_FILE_STATE_UNQUALIFIED'
                continue
            rx, rz = map(int, Path(name).stem.split('.')[1:])
            for slot in range(1024):
                if time.monotonic() - began > 120 or len(all_chunks) >= 32768:
                    raise UserError('Saved-chunk study reached its time/count bound')
                record = decode_record(raw, slot)
                if record is None:
                    continue
                doc, payload_sha = record
                cx, cz = rx * 32 + slot % 32, rz * 32 + slot // 32
                if (doc['xPos'], doc['zPos']) != (cx, cz):
                    raise UserError('Saved chunk coordinates disagree with their region slot')
                row = {'chunk': [cx, cz], 'saved_payload_sha256': payload_sha, 'status': doc.get('Status', 'missing')}
                all_chunks.append(row)
                if row['status'] not in ('minecraft:full', 'full'):
                    partial[row['status']] += 1
                    continue
                if len(full) >= 4096:
                    raise UserError('FULL chunk study exceeds its scope')
                full.append(row)
                sections = {s['Y']: s for s in doc.get('sections', [])}
                surface = doc.get('Heightmaps', {}).get('WORLD_SURFACE')
                if surface:
                    if len(surface) != math.ceil(256/7):
                        raise UserError('Heightmap does not match retained -64..320 dimensions')
                    for i in range(256):
                        y = packed_value(surface, i, 9) - 65
                        heights.append(y)
                        biome = sections.get(y//16, {}).get('biomes', {})
                        palette = biome.get('palette', [])
                        if not palette:
                            continue
                        ordinal = ((y & 15)//4)*16 + ((i//16)//4)*4 + (i % 16)//4
                        pi = 0 if len(palette) == 1 else packed_value(biome['data'], ordinal, max(1, (len(palette)-1).bit_length()))
                        if pi >= len(palette):
                            raise UserError('Invalid saved biome palette index')
                        biomes[palette[pi]] += 1
                for key, value in doc.get('structures', {}).get('starts', {}).items():
                    if value.get('id') != 'INVALID' and value.get('Children'):
                        starts[(key, value.get('ChunkX', cx), value.get('ChunkZ', cz))] = True
    if not full or not heights:
        raise UserError('No complete saved surface observations')
    private_output = Path(private_output)
    if private_output.exists():
        raise UserError('Never overwrite an archived observation inventory')
    private_output.mkdir(parents=True)
    raw_inventory = (json.dumps(all_chunks, separators=(',', ':')) + '\n').encode()
    if len(raw_inventory) > 8 * 1024**2:
        raise UserError('Private inventory exceeds its bounded allocation')
    (private_output / 'all-saved-chunk-inventory.json').write_bytes(raw_inventory)
    return {'format': 'awft-archived-generated-terrain-observations:1',
        'tier': 'ACTUAL_SAVED_CHUNKS_FROM_HISTORICAL_NATIVE_WORLD; NOT A FRESH GENERATION OR UPDATED A/B RUN',
        'checkpoint_id': Path(archive_path).stem, 'checkpoint_sha256': expected_sha256,
        'world_member_prefix': prefix, 'regions': pins, 'full_chunks': len(full),
        'partial_chunk_statuses': dict(partial), 'surface_columns_observed': len(heights),
        'stored_surface_height_including_trees_and_buildings': {'min': min(heights), 'max': max(heights)},
        'actual_saved_surface_biome_columns': dict(sorted(biomes.items())),
        'actual_saved_valid_structure_starts': dict(sorted(collections.Counter(k[0] for k in starts).items())),
        'private_all_chunk_inventory_sha256': hashlib.sha256(raw_inventory).hexdigest(),
        'generation_time_ms': None, 'tick_spikes': None, 'updated_profile_result': None,
        'limits': ['Historical constructed world; not pristine terrain or an unbiased representative sample.',
                   'All FULL chunks in the named archived overworld counted; other dimensions not surveyed.',
                   'No live world was opened or rewritten and no updated chunks generated.',
                   'Heightmaps include vegetation/buildings; no terrain-fit or entrance acceptance follows.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path, required=True)
    parser.add_argument('--sha256', required=True)
    parser.add_argument('--prefix', default='world/RosewaterArtistic/region/')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists() or not output.is_relative_to(REPO / 'evidence/worldgen'):
        parser.error('Use a new sanitized result under evidence/worldgen')
    from tools.playtest import guard
    guard(4 * 1024**2, 8 * 1024**2)
    private = Path(r'D:\A World for Two\staging\worldgen-archive-observations') / str(time.time_ns())
    result = observe(args.archive, args.sha256, args.prefix, private)
    result['observer_source_sha256'] = digest(Path(__file__))
    write_json(output, result)
    print(json.dumps({'full_chunks': result['full_chunks'], 'partial_chunks': sum(result['partial_chunk_statuses'].values()),
                      'output': str(output), 'private_inventory': str(private)}))


if __name__ == '__main__':
    main()
