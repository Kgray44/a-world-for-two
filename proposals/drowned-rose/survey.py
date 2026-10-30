"""Survey immutable saved tavern bytes. No live world or server writes."""
from __future__ import annotations

import argparse
from collections import deque
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.settlement_attractions import BackupWorld

AIR = {'minecraft:air', 'minecraft:cave_air'}
BASE = 'staging/artistic-pirate-spit-byte-slots-1793124362042040500/manifest.json'


def survey(home, ident, sha):
    registry = json.loads((home/'dashboard/settlement/registry.json').read_bytes())
    world = BackupWorld(home, {'id': ident, 'sha256': sha, 'verified': True}, registry)
    try:
        routes = json.loads((home/BASE).read_bytes())['routes']
        reserved = {(x, y+1, z) for r in routes if r['name'].startswith('Drowned Rose')
                    for x, y, z in r['floor_cells']}
        reserved.update((x,65,z) for x in (1302,1303) for z in range(-1284,-1269))
        reserved.update((x,y,z) for x in (1307,1308,1309)
                        for z in (-1271,-1270) for y in (65,66,67))
        # Interior only; do not admit exterior paving, the galley or gallery void.
        nodes, chairs, preimage = set(), [], {}
        for x in range(1293, 1311):
            for z in range(-1288, -1270):
                for y in range(64, 73):
                    preimage[x,y,z] = world.state((x,y,z))
        for x, y, z in sorted(preimage):
            if not 65 <= y <= 70:
                continue
            here = preimage[x,y,z]
            below = preimage.get((x,y-1,z), '')
            # Conservative saved geometry; native collision/path checks are still mandatory.
            full_floor = below in {'minecraft:dark_oak_planks', 'minecraft:spruce_planks',
                                  'minecraft:oak_planks', 'minecraft:stone_bricks',
                                  'chipped:boxed_dark_oak_planks',
                                  'chipped:cross_laced_dark_oak_planks',
                                  'chipped:detailed_dark_oak_planks',
                                  'chipped:crossed_dark_oak_planks'}
            if full_floor and here in AIR and preimage.get((x,y+1,z)) in AIR:
                nodes.add((x,y,z))
            if here.startswith('handcrafted:') and '_chair[' in here:
                chairs.append(((x,y,z), here))
        edges = {p: [q for q in ((p[0]+dx,p[1]+dy,p[2]+dz)
                    for dx,dz in ((1,0),(-1,0),(0,1),(0,-1)) for dy in (0,1,-1))
                    if q in nodes] for p in nodes}
        # Keep the connected component of the main room. Unsupported gallery/stairs
        # remain held until an exact native traversal survey admits them.
        start = (1304,65,-1280)
        if start not in nodes:
            raise ValueError('Saved main-room anchor changed')
        connected, queue = {start}, deque([start])
        while queue:
            for nxt in edges[queue.popleft()]:
                if nxt not in connected:
                    connected.add(nxt); queue.append(nxt)
        nodes = connected
        stage = [p for p in sorted(nodes) if p[1] == 66 and p[2] <= -1286]
        if len(stage) < 4:
            raise ValueError('Fewer than four saved stage approaches; native survey required')
        # Four independent destination cells; retain the piano and its immediate front.
        proposed_stage = [(1300,66,-1286),(1302,66,-1287),
                          (1303,66,-1286),(1305,66,-1287)]
        if not all(p in stage for p in proposed_stage):
            raise ValueError('Saved four-instrument stage clearance changed')
        stage = proposed_stage
        slots = []
        for i,p in enumerate(stage):
            slots.append({'id': f'band-{i}', 'pos':p, 'approach':p,
                          'activities':['music'], 'group':'band'})
        for p,state in chairs:
            adjacent = [q for q in nodes if q[1] == p[1] and
                        abs(q[0]-p[0])+abs(q[2]-p[2]) == 1 and q not in reserved]
            if not adjacent:
                continue
            slots.append({'id':f'chair-{len(slots)}', 'pos':p, 'approach':sorted(adjacent)[0],
                          'chair_state':state, 'activities':['sit','drink','social'],
                          'group':f'table-{p[2]//4}'})
        # Leave one empty cell between standing destinations; never idle in circulation.
        used = {tuple(v['approach']) for v in slots} | set(stage)
        for p in sorted(nodes):
            x,y,z = p
            if p in reserved or y != 65 or x == 1294 or z >= -1272:
                continue
            if any(abs(x-q[0])+abs(z-q[2]) < 2 and y == q[1] for q in used):
                continue
            group = f'conversation-{x//5}-{z//5}'
            acts = ['social','group','return','walk']
            if x <= 1296: acts += ['bar','drink']
            if x >= 1308: acts += ['window']
            if z <= -1283: acts += ['watch']
            slots.append({'id':f'floor-{len(slots)}', 'pos':p, 'approach':p,
                          'activities':acts, 'group':group})
            used.add(p)
        block_rows = [[*p,s] for p,s in sorted(preimage.items())]
        result = {'format':1, 'name':'The Drowned Rose — custom northern east tavern',
                  'checkpoint_id':ident, 'checkpoint_sha256':sha,
                  'saved_region_sources':world.sources,
                  'geometry_sha256':hashlib.sha256(json.dumps(block_rows,separators=(',',':')).encode()).hexdigest(),
                  'native_geometry_verified':False, 'spawn_admitted':False,
                  'nodes':[list(p) for p in sorted(nodes)], 'slots':slots,
                  'circulation':[list(p) for p in sorted(reserved)],
                  'preimage':block_rows,
                  'pending':['native collision and chair approach/dismount',
                             'stage sightlines and four instrument clearance',
                             'current runtime preimage matching; existing inhabitants',
                             'exclusive integration lease and fresh backup']}
        return result
    finally:
        world.close()


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--home', type=Path, required=True)
    parser.add_argument('--checkpoint-id', required=True)
    parser.add_argument('--checkpoint-sha', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args=parser.parse_args()
    result=survey(args.home,args.checkpoint_id,args.checkpoint_sha)
    raw=(json.dumps(result,indent=2)+'\n').encode()
    if len(raw)>2*1024**2 or args.output.exists():
        raise ValueError('Fresh output under 2 MiB required')
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_bytes(raw)
    print(json.dumps({'output':str(args.output),'sha256':hashlib.sha256(raw).hexdigest(),
                      'nodes':len(result['nodes']),'slots':len(result['slots']),
                      'native_verified':False}))
