"""Read requested original schematics without executing their contents.

This module decodes source geometry only. Placement, terrain adaptation, native
neighbor joins, material rules, inventory conversion and visual review remain
separate gates. No source entity, scheduled tick or command is executed.
"""
from __future__ import annotations

import gzip
import math
from pathlib import Path
import re

from control_room.common import UserError
from tools.settlement_attractions import NBTReader

MAX_COMPRESSED = 8 * 1024**2
MAX_DECODED = 8 * 1024**2  # Same bound as the shared strict NBT reader.
# These two requested builds are below 50,000 cells. Keep the decoded Python
# geometry finite rather than admitting an arbitrary downloaded megastructure.
MAX_VOLUME = 128 * 1024


def read_source(path):
    path = Path(path)
    if not path.is_file() or not 0 < path.stat().st_size <= MAX_COMPRESSED:
        raise UserError('The original structure exceeds the bounded compressed input')
    try:
        with gzip.open(path, 'rb') as stream:
            raw = stream.read(MAX_DECODED + 1)
    except (OSError, EOFError) as exc:
        raise UserError('The original is not a complete gzip NBT structure') from exc
    if len(raw) > MAX_DECODED:
        raise UserError('Structure decompression exceeds the finite bound')
    try:
        return NBTReader(raw).read()
    except (UnicodeError, ValueError) as exc:
        raise UserError('Malformed original structure NBT') from exc


def checked_size(values):
    if len(values) != 3 or any(type(v) is not int or v == 0 or abs(v) > 512 for v in values):
        raise UserError('Three finite nonzero integer structure dimensions required')
    if math.prod(abs(v) for v in values) > MAX_VOLUME:
        raise UserError('Split this structure into a bounded import')
    return tuple(abs(v) for v in values)


def legacy_geometry(document):
    if document.get('Materials') != 'Alpha' or document.get('AddBlocks'):
        raise UserError('Only the inspected vanilla Alpha byte-ID schematic is admitted')
    dimensions = [document.get(k) for k in ('Width', 'Height', 'Length')]
    w, h, d = checked_size(dimensions)
    if any(v < 1 for v in dimensions):
        raise UserError('Legacy dimensions must be positive')
    ids, data = document.get('Blocks'), document.get('Data')
    if not isinstance(ids, list) or not isinstance(data, list) or len(ids) != w*h*d or len(data) != len(ids):
        raise UserError('Legacy block arrays do not match the declared volume')
    result = {}
    for n, (identifier, metadata) in enumerate(zip(ids, data)):
        if type(identifier) is not int or type(metadata) is not int or not -128 <= identifier <= 255:
            raise UserError('Invalid legacy block byte')
        identifier &= 255
        if not 0 <= metadata <= 15:
            raise UserError('Invalid legacy block metadata nibble')
        result[n % w, n // (w*d), n // w % d] = (identifier << 4) | metadata
    return result


def litematic_geometry(document):
    if (type(document.get('Version')) is not int or document.get('Version') != 7
            or type(document.get('SubVersion')) is not int or document.get('SubVersion') != 1):
        raise UserError('Only the inspected Litematic 7.1 format is admitted')
    regions = document.get('Regions')
    if not isinstance(regions, dict) or not 1 <= len(regions) <= 16:
        raise UserError('Finite named regions required')
    result = {}
    for region in regions.values():
        if not isinstance(region, dict) or any(not isinstance(region.get(k), dict) for k in ('Size', 'Position')):
            raise UserError('An exact sized and positioned region is required')
        if any(k not in region['Size'] or k not in region['Position'] for k in ('x', 'y', 'z')):
            raise UserError('All three signed region coordinates are required')
        signed = [region['Size'][k] for k in ('x', 'y', 'z')]
        size = checked_size(signed)
        origin = [region['Position'][k] for k in ('x', 'y', 'z')]
        if any(type(v) is not int or abs(v) > 4096 for v in origin):
            raise UserError('Finite local region origin required')
        palette, packed = region.get('BlockStatePalette'), region.get('BlockStates')
        if not isinstance(palette, list) or not 1 <= len(palette) <= 65536 or not isinstance(packed, list):
            raise UserError('Finite palette and packed block states required')
        bits = max(2, (len(palette)-1).bit_length())
        volume = math.prod(size)
        if len(result) + volume > MAX_VOLUME:
            raise UserError('Combined named regions exceed the bounded import volume')
        if len(packed) != (volume * bits + 63) // 64:
            raise UserError('Packed state length does not match the exact region')
        if any(type(v) is not int or not -(1 << 63) <= v < (1 << 63) for v in packed):
            raise UserError('Packed state words must be native signed 64-bit integers')
        words = [v & ((1 << 64)-1) for v in packed]
        mask = (1 << bits)-1
        for n in range(volume):
            word, shift = divmod(n*bits, 64)
            index = words[word] >> shift
            if shift+bits > 64:
                index |= words[word+1] << (64-shift)
            index &= mask
            if index >= len(palette):
                raise UserError('Packed block state exceeds its palette')
            local = [n % size[0], n // (size[0]*size[2]), n // size[0] % size[2]]
            pos = tuple(origin[i] + local[i] + min(0, signed[i]+1) for i in range(3))
            if pos in result:
                raise UserError('Overlapping structure regions require explicit composition')
            row = palette[index]
            state_string(row)  # Never admit arbitrary property syntax.
            result[pos] = row
    return result


def state_string(row, registry=None):
    """Encode a block-state data record, never an executable command."""
    if (not isinstance(row, dict) or set(row)-{'Name', 'Properties'}
            or not isinstance(row.get('Name'), str)
            or not re.fullmatch(r'[a-z0-9_.-]+:[a-z0-9_./-]+', row['Name'])):
        raise UserError('Invalid original block identity')
    fields = row.get('Properties', {})
    if not isinstance(fields, dict) or any(not isinstance(k, str) or not re.fullmatch(r'[a-z0-9_]+', k)
            or not isinstance(v, str) or not re.fullmatch(r'[a-z0-9_]+', v) for k, v in fields.items()):
        raise UserError('Invalid original block property data')
    if registry is not None:
        schema = registry['blocks'].get(row['Name'])
        if schema is None or any(v not in schema.get(k, ()) for k, v in fields.items()):
            raise UserError('Original state is unavailable in the actual registry: '+row['Name'])
    return row['Name']+('['+','.join(k+'='+v for k, v in sorted(fields.items()))+']' if fields else '')


DIRECTIONS = ('north', 'east', 'south', 'west')
DELTAS = {'north': (0, 0, -1), 'east': (1, 0, 0), 'south': (0, 0, 1), 'west': (-1, 0, 0)}
LEGACY_DYES = ('black', 'red', 'green', 'brown', 'blue', 'purple', 'cyan', 'light_gray',
               'gray', 'pink', 'lime', 'yellow', 'light_blue', 'magenta', 'orange', 'white')
SKULLS = ('skeleton_skull', 'wither_skeleton_skull', 'zombie_head', 'player_head', 'creeper_head', 'dragon_head')


def rotate_record(row, turns):
    """Rotate actual facings, cardinal connections, axes and standing rotations."""
    if type(turns) is not int or turns not in range(4):
        raise UserError('A bounded exact quarter-turn rotation is required')
    state_string(row)
    fields = row.get('Properties', {})
    result = {}
    for key, value in fields.items():
        name = DIRECTIONS[(DIRECTIONS.index(key)+turns) % 4] if key in DIRECTIONS else key
        if key == 'facing' and value in DIRECTIONS:
            value = DIRECTIONS[(DIRECTIONS.index(value)+turns) % 4]
        elif key == 'axis' and value in ('x', 'z') and turns % 2:
            value = 'z' if value == 'x' else 'x'
        elif key == 'rotation':
            if not value.isdecimal() or not 0 <= int(value) < 16:
                raise UserError('A valid standing block rotation is required')
            value = str((int(value)+4*turns) % 16)
        result[name] = value
    return {'Name': row['Name'], **({'Properties': result} if result else {})}


def rotate_position(pos, size, turns):
    checked_size(size)
    if (type(turns) is not int or turns not in range(4) or not isinstance(pos, (list,tuple))
            or len(pos) != 3 or any(type(v) is not int for v in pos)):
        raise UserError('Exact local position and quarter turn required')
    x, y, z = pos; w, _, d = size
    if not (0 <= x < w and 0 <= y < size[1] and 0 <= z < d):
        raise UserError('Local position escaped the source structure')
    return ((x, y, z), (d-1-z, y, x), (w-1-x, y, d-1-z), (z, y, w-1-x))[turns]


def contextual_legacy(document, native_table):
    """Use pinned native flattening plus actual paired/source NBT context.

    A numerical flattening table cannot know a door's other half or a skull's
    type/rotation. Legacy fence connections and stair shapes are unspecified;
    they are recorded for a real staging-world neighbor pass, not guessed here.
    No source entity or raw block-entity compound is emitted by this function.
    """
    from copy import deepcopy
    raw = legacy_geometry(document)
    if (native_table.get('minecraft') != '1.21.1' or native_table.get('data_version') != 3955
            or native_table.get('native_flattened_schema') != 1451):
        raise UserError('The exact native 1.21.1 flattening result is required')
    table = native_table.get('states', {})
    if set(table) != {str(v) for v in raw.values()}:
        raise UserError('Native table must cover exactly the source state set')
    tiles = {}
    for tile in document.get('TileEntities', []):
        if not isinstance(tile, dict) or any(type(tile.get(k)) is not int for k in ('x', 'y', 'z')):
            raise UserError('Invalid original block-entity position')
        pos = tuple(tile[k] for k in ('x', 'y', 'z'))
        if pos in tiles or pos not in raw:
            raise UserError('Duplicate or foreign original block entity')
        tiles[pos] = tile
    result = {}; changes = []; derived = []
    for pos, encoded in raw.items():
        row = deepcopy(table[str(encoded)])
        fields = row.setdefault('Properties', {})
        identifier, meta = encoded >> 4, encoded & 15
        before = deepcopy(row)
        if identifier in (64, 71, 193, 194, 195, 196, 197):
            lower = (pos[0], pos[1]-1, pos[2]) if meta & 8 else pos
            upper = (lower[0], lower[1]+1, lower[2])
            a, b = raw.get(lower, -1), raw.get(upper, -1)
            if a >> 4 != identifier or b >> 4 != identifier or a & 8 or not b & 8:
                raise UserError('Incomplete original two-half door')
            fields.update(facing=('east', 'south', 'west', 'north')[a & 3],
                          open='true' if a & 4 else 'false', hinge='right' if b & 1 else 'left',
                          powered='true' if b & 2 else 'false', half='upper' if meta & 8 else 'lower')
        if identifier == 144:
            tile = tiles.get(pos, {})
            if tile.get('id') != 'Skull' or type(tile.get('SkullType')) is not int or not 0 <= tile['SkullType'] < len(SKULLS):
                raise UserError('Every original skull requires its exact SkullType context')
            key = SKULLS[tile['SkullType']]
            if meta == 1:
                rotation = tile.get('Rot')
                if type(rotation) is not int or not 0 <= rotation < 16:
                    raise UserError('A floor skull requires its exact original rotation')
                row = {'Name': 'minecraft:'+key, 'Properties': {'rotation': str(rotation), 'waterlogged': 'false'}}
            elif meta in (2, 3, 4, 5):
                key = key.replace('_skull', '_wall_skull').replace('_head', '_wall_head')
                row = {'Name': 'minecraft:'+key, 'Properties': {'facing': {2:'north',3:'south',4:'west',5:'east'}[meta], 'waterlogged':'false'}}
            else:
                raise UserError('Unsupported original skull placement')
            fields = row['Properties']
        if identifier in (176, 177):
            tile = tiles.get(pos, {})
            color = tile.get('Base')
            if tile.get('id') != 'Banner' or type(color) is not int or not 0 <= color < 16:
                raise UserError('Every banner requires its original dye context')
            row['Name'] = 'minecraft:'+LEGACY_DYES[color]+('_wall_banner' if identifier == 177 else '_banner')
        if row['Name'] in ('minecraft:chest', 'minecraft:trapped_chest'):
            facing = fields['facing']; neighbors = []
            for turn, label in ((1, 'left'), (-1, 'right')):
                direction = DIRECTIONS[(DIRECTIONS.index(facing)+turn) % 4]
                delta = DELTAS[direction]
                other = tuple(pos[i]+delta[i] for i in range(3))
                neighbor = table.get(str(raw.get(other)), {})
                if neighbor.get('Name') == row['Name'] and neighbor.get('Properties', {}).get('facing') == facing:
                    neighbors.append(label)
            if len(neighbors) > 1:
                raise UserError('An ambiguous three-chest assembly requires authored adaptation')
            fields['type'] = neighbors[0] if neighbors else 'single'
        # These values in the global legacy table are placeholders, not source
        # observations. Keep them explicitly pending for real native readback.
        unspecified = set()
        if row['Name'].endswith('_fence') or row['Name'].endswith('_glass_pane'):
            unspecified.update(DIRECTIONS)
        if row['Name'].endswith('_stairs'):
            unspecified.add('shape')
        omitted = {k: fields.pop(k) for k in sorted(unspecified) if k in fields}
        if omitted:
            derived.append({'pos': list(pos), 'legacy_placeholders': omitted,
                            'requires': 'Actual staging-world native neighbor update and saved readback'})
        state_string(row)
        if row != before:
            changes.append({'pos': list(pos), 'encoded': encoded, 'before': before, 'after': deepcopy(row)})
        result[pos] = row
    for pos, encoded in raw.items():
        if encoded >> 4 == 26:
            row = result[pos]; fields = row['Properties']; delta = DELTAS[fields['facing']]
            sign = -1 if fields['part'] == 'head' else 1
            other = tuple(pos[i]+sign*delta[i] for i in range(3))
            pair = result.get(other, {})
            if (pair.get('Name') != row['Name'] or pair.get('Properties', {}).get('facing') != fields['facing']
                    or pair.get('Properties', {}).get('part') == fields['part']):
                raise UserError('Original bed direction/half context is incomplete')
    return result, tiles, {'contextual_changes': changes, 'native_connectivity_pending': derived,
                           'source_entities_excluded': len(document.get('Entities', [])),
                           'source_block_entities': len(tiles)}
