"""Stage current artistic-world Lumiera scenes; never activate or move players.

Geometry hashes and a verified stopped-world backup are required. The backup is
read only to check the entire camera polyline, including natural terrain. Scene
contracts require nearby players; they do not pretend to load distant chunks.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import time
import zipfile
from pathlib import Path

from control_room.common import Layout, REPO, UserError, atomic_write, digest, read_json, utcnow
from control_room.storage import Storage
from tools.settlement_attractions import BackupWorld
from tools.settlement_cinematic import LUMIERA_FILE, LUMIERA_SHA256, native_probe, scene

FIRST_JOIN = 'awft:rose_lantern_arrival'
SPAWN = (1120.5, 68, -1093.5)
MAX_OUTPUT = 16 * 1024**2


def scenes():
    """Three authored local sequences; no tour across unstreamed districts."""
    return [
        scene(FIRST_JOIN, 'Our little corner of an endless world', [
            (0, (1088, 112, -1101), (1108, 77, -1106), 62),
            (3, (1104, 113, -1138), (1107, 77, -1105), 64),
            (6, (1138, 114, -1142), (1151, 74, -1100), 64),
            (9, (1166, 114, -1148), (1174, 73, -1102), 66),
            (12, (1176, 112, -1150), (1190, 72, -1136), 65),
            (14.5, (1150, 105, -1125), (1120.5, 73, -1093.5), 66),
            (16.5, (1120.5, 88, -1093.5), (1120.5, 72, -1080.5), 68),
            (18, (1120.5, 69.62, -1093.5), (1120.5, 69.62, -1080.5), 70),
        ], SPAWN, ['Rose & Lantern cottage and garden', 'Bramble Lane craft households',
                   'Near-bank mechanical drawbridge', 'Courtyard eye-height return'], first_join=True),
        scene('awft:rosewater_palace_replay', 'Rosewater Palace', [
            (0, (1210, 160, -1042), (1249, 100, -1017), 65),
            (4, (1246, 166, -1063), (1265, 106, -1022), 65),
            (8, (1308, 162, -1036), (1267, 107, -1014), 67),
            (12, (1312, 158, -982), (1253, 96, -1002), 67),
            (16, (1260, 155, -966), (1249, 92, -1008), 68),
        ], (1260, 74, -1010), ['Current palace wings, rose court and observatory']),
        scene('awft:rosewater_lark_replay', 'Rosewater Lark', [
            (0, (1103, 91, -1487), (1141, 83, -1470), 66),
            (4, (1100, 96, -1455), (1140, 80, -1445), 66),
            (8, (1104, 110, -1418), (1140, 83, -1431), 66),
            (12, (1136, 150, -1395), (1140, 90, -1450), 68),
            (16, (1176, 148, -1453), (1140, 96, -1450), 68),
            (18, (1176, 123, -1477), (1140, 78, -1460), 66),
        ], (1140, 70, -1450), ['Actual curved hull, distinct rig and lived-in working deck']),
    ]


def saved_clearance(document, snapshot):
    """Conservative .7-block clearance from real saved block cubes, at <=.25m."""
    checked = 0
    states = {}
    for first, last in zip(document['keyframes'], document['keyframes'][1:]):
        a = [first['pos'][k] for k in ('x', 'y', 'z')]
        b = [last['pos'][k] for k in ('x', 'y', 'z')]
        count = max(1, math.ceil(math.dist(a, b)*4))
        for n in range(count+1):
            point = [a[j]+(b[j]-a[j])*n/count for j in range(3)]
            base = [math.floor(v) for v in point]
            checked += 1
            for x in range(base[0]-1, base[0]+2):
                for y in range(base[1]-1, base[1]+2):
                    for z in range(base[2]-1, base[2]+2):
                        pos = x, y, z
                        distance = math.sqrt(sum(max(low-value, 0, value-low-1)**2 for value, low in zip(point, pos)))
                        if distance >= .7:
                            continue
                        if pos not in states:
                            if len(states) >= 100000:
                                raise UserError('Camera saved-state allocation exceeds its finite bound')
                            states[pos] = snapshot.state(pos).split('[')[0]
                        if states[pos] not in ('minecraft:air', 'minecraft:cave_air', 'minecraft:void_air'):
                            raise UserError('Camera intersects saved construction/terrain: '+document['id']+' '+str(pos))
    return {'sampled_positions': checked, 'saved_cells_checked': len(states), 'spacing_max': .25,
            'required_cube_clearance': .7, 'status': 'PASS exact stopped-backup block cubes',
            'dynamic_entities_and_render_occlusion': 'unverified'}


def prepare(home, bindings):
    layout = Layout(Path(home))
    owner = read_json(layout.state/'artistic-owner.json', {})
    backup = read_json(layout.state/'settlement/backup-receipt.json', {})
    registry = read_json(layout.state/'settlement/registry.json', {})
    if (owner.get('format') != 'awft-artistic-stage:1' or owner.get('owner_source') != str(REPO)
            or Path(owner.get('home', '')).resolve() != layout.home
            or not backup.get('verified') or owner.get('backup_sha256') != backup.get('sha256')
            or not Path(registry.get('world_path', '')).resolve().is_relative_to(layout.world)):
        raise UserError('Use the explicitly owned artistic staging world and verified current checkpoint')
    staging = next((p for p in layout.home.parents if p.name == 'staging'), None)
    if staging is None or len(bindings) > 16 or not {'cottage', 'craft_lane', 'drawbridge', 'palace', 'ship'} <= {r[0] for r in bindings}:
        raise UserError('Bind all five current artistic districts within the isolated staging tree')
    if len({r[0] for r in bindings}) != len(bindings):
        raise UserError('Geometry binding labels must be unique')
    sources = []
    for role, filename, expected in bindings:
        path = Path(filename).resolve()
        if (not re.fullmatch('[a-z_0-9-]{1,64}', role) or not re.fullmatch('[a-f0-9]{64}', expected)
                or not path.is_relative_to(staging) or not path.is_file() or path.stat().st_size > 16*1024**2
                or digest(path) != expected):
            raise UserError('An exact bounded artistic geometry binding changed')
        data = read_json(path)
        if (data.get('format') != 'awft-native-settlement:1' or data.get('seed') != registry['seed']
                or data.get('world_path') != registry['world_path']):
            raise UserError('Cinematic geometry mixes worlds')
        sources.append({'role': role, 'file': path.name, 'sha256': expected, 'blocks': len(data['blocks']),
                        'scope': 'Bound authoring reference; actual camera clearance reads the verified saved world'})
    jar = layout.server/'mods'/LUMIERA_FILE
    if not jar.is_file() or digest(jar) != LUMIERA_SHA256:
        raise UserError('Exact pinned Lumiera alpha.1 required')
    prepared = scenes()
    documents, contracts = {}, []
    snapshot = BackupWorld(layout.home, backup, registry)
    try:
        for document, contract in prepared:
            contract['structural_preflight'] = saved_clearance(document, snapshot)
            name = 'data/awft/cutscenes/'+document['id'].split(':')[1]+'.json'
            documents[name] = (json.dumps(document, indent=2)+'\n').encode()
            contract['scene_sha256'] = hashlib.sha256(documents[name]).hexdigest()
            contracts.append(contract)
        saved_sources = snapshot.sources
    finally:
        snapshot.close()
    final = prepared[0][0]['keyframes'][-1]
    if final['pos'] != dict(zip(('x', 'y', 'z'), (1120.5, 69.62, -1093.5))):
        raise UserError('Arrival must end at the current spawn eye height')
    documents['pack.mcmeta'] = (json.dumps({'pack': {'pack_format': 48,
        'description': 'A World for Two - current Rosewater artistic camera scenes'}})+'\n').encode()
    if sum(map(len, documents.values())) > 1024**2:
        raise UserError('Camera documents exceed their bounded payload')
    identity = hashlib.sha256(b''.join(n.encode()+b'\0'+v for n, v in sorted(documents.items()))).hexdigest()
    output = layout.staging/('artistic-cinematics-'+identity[:16]+'-'+str(time.time_ns()))
    Storage(layout).reserve(MAX_OUTPUT, target=output)
    output.mkdir()
    path = output/'awft-settlement-cinematic.zip'
    with zipfile.ZipFile(path, 'x', zipfile.ZIP_DEFLATED) as archive:
        for name, value in sorted(documents.items()):
            item = zipfile.ZipInfo(name, (2026, 1, 1, 0, 0, 0)); item.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(item, value)
            atomic_write(output/'datapack'/name, value)
    atomic_write(output/'cinematics.json', json.dumps({'enabled': True, 'first_join': True,
        'intro_scene': FIRST_JOIN, 'triggers': []}, indent=2)+'\n')
    manifest = {'format': 'awft-settlement-cinematic:1', 'at': utcnow(), 'identity': identity,
        'source_sha256': digest(Path(__file__)), 'backup_id': backup['id'], 'backup_sha256': backup['sha256'],
        'lumiera': {'file': LUMIERA_FILE, 'sha256': LUMIERA_SHA256}, 'datapack': path.name,
        'datapack_sha256': digest(path), 'scenes': contracts, 'geometry_sources': sources,
        'saved_clearance_sources': saved_sources, 'recommended_first_join_scene': FIRST_JOIN,
        'spawn_feet': list(SPAWN), 'settings_file': 'cinematics.json',
        'settings_sha256': digest(output/'cinematics.json'), 'activation': 'Not performed',
        'history_policy': 'Preserve cinematic-first-joins.json; never reset returning players automatically',
        'playback_preconditions': 'Correct dimension and nearby player centers required; contracts do not implement runtime proximity guards',
        'performance': 'No chunk tickets, forced loads, actors, world commands or distance changes',
        'native_format_probe': 'pending', 'acceptance': 'Native packets, chunk coverage, real visibility, skip and control return unverified'}
    atomic_write(output/'manifest.json', json.dumps(manifest, indent=2)+'\n')
    return {'directory': str(output), 'datapack_sha256': digest(path),
            'manifest_sha256': digest(output/'manifest.json'), 'first_join': FIRST_JOIN, 'activation': 'Not performed'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--home', type=Path, required=True)
    parser.add_argument('--geometry', nargs=3, action='append', metavar=('ROLE', 'PATH', 'SHA256'))
    parser.add_argument('--native-probe', type=Path)
    args = parser.parse_args()
    result = native_probe(args.home, args.native_probe) if args.native_probe else prepare(args.home, args.geometry or [])
    print(json.dumps(result))
