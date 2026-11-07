"""Three small lived-in exterior scenes beside the actual Native55 compounds.

Private immutable preimages and fresh native admission are mandatory. This tool
never contacts the running server, edits a save or replays an existing BE/NBT.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import time
import zipfile

from control_room.common import UserError, digest, read_json
from tools.artistic_bridge_refinement import flatten
from tools.artistic_city_planning_map import EAST, read as frozen_layout
from tools.artistic_create_substrate import verify_zinc_factory
from tools.artistic_ground_stability import natural_mount
from tools.artistic_materials import require_outdoor_rule
from tools.artistic_north_bank_east import NorthTerrain, native_payload, GROUND, SOFT, NORTH_SOFT
from tools.artistic_spawn_plaza import state
from tools.artistic_tortuga_frontages import AIR, POTS, key
from tools.artistic_zipline_catenary import reader_budget
from tools.playtest import guard

MIB = 1024**2
CHECKPOINT = '20261028T191243Z-6ad3a8'
CHECKPOINT_SHA = '0ba7ad2097fb52273a37da6a76d8fc030133b79cd26d81b97531d8d74c2546c2'
ADMITTED = 'staging/EAST-FIRST-THREE-ADMITTED55-1793224100061542000'
COMPOUNDS = {
    'east-coal': ('6768791af4173ca871f7b2b2e073fb7435c00653f368287dec0028c38c32daa6', '5f1b3eb6-e3a6-4883-ae51-9aa8bde3d0e7', 'c861c7c543a72f044970307109ce5415ac2374c4aa11c8e17008e5416ca29672'),
    'shoal-warden': ('d2c354df941c8974db5e4240a85838f6db30149787b2469277f07a53972c9d97', 'bf46b935-fcc2-494a-a3ae-1c247c2fb1c5', '3ebd0884e113c92f85766d110e689a6130922525fc79b2fe2fb8bd5e091e0e8a'),
    'thin-sail': ('b16cca5358f34fbc15939f18e17d6d45f91421af03d7da76eed1b96316b2d6e4', '75f9e3c9-3876-4097-9363-4ea9c6ef32ad', '878c706b7232f7a19f845908cda87f3015606cb91d3dd670d6026df80d9d9558'),
}
SHRUB = 'regions_unexplored:lavender_wisteria_shrub'
VOIDS = {AIR, 'minecraft:cave_air', 'minecraft:void_air'}
MAX_TARGETS = 180


def construct(registry):
    """Authored individual scenes; the surrounding buildings are not rewritten."""
    blocks, tags, objects, mounts, plants = {}, {}, [], {}, {}
    walks = ({(x, z) for x in (1357, 1358) for z in range(-1162, -1158)} |
             {(x, z) for x in (1357, 1358) for z in range(-1187, -1183)} |
             {(x, z) for x in (1377, 1378) for z in range(-1129, -1118)})

    def put(q, name, role, **props):
        value = state(registry, name, **props)
        if q in blocks and blocks[q] != value:
            raise UserError('Distinct exterior details overlap: ' + str(q))
        blocks[q] = value
        objects.append({'position': list(q), 'block': name, 'role': role})

    def root(x, y, z, kind=SHRUB):
        put((x, y, z), 'minecraft:dirt', 'small rooted native planting pocket at the actual soil height')
        if kind == SHRUB:
            for half, yy in (('lower', y+1), ('upper', y+2)):
                put((x, yy, z), kind, 'real native double-height shrub; no sapling or artificial tree', half=half)
        else:
            put((x, y+1, z), kind, 'rooted modded flower on its own literal dirt soil')
        plants[x, y, z] = kind

    def sign(q, face, lines):
        put(q, 'minecraft:dark_oak_wall_sign', 'new waxed trade sign on a new independent timber mount', facing=face, waterlogged=False)
        texts = [json.dumps(json.dumps({'text': line, 'color': 'black'})) for line in lines]
        tags[q] = '{is_waxed:1b,front_text:{messages:[' + ','.join(texts) + '],color:"black",has_glowing_text:0b}}'

    def post(x, z, lo=64, hi=67):
        for y in range(lo, hi):
            put((x, y, z), 'minecraft:stripped_dark_oak_log', 'independently founded slim task-light timber', axis='y')
        put((x, hi, z), 'minecraft:dark_oak_wood', 'small weathered post cap', axis='y')

    # Coal: the coast narrows immediately north/east. Stay on the four real dry
    # columns and leave the entire two-wide western doorway approach open.
    post(1360, -1161)
    put((1359, 67, -1161), 'minecraft:dark_oak_wood', 'short supported lantern arm', axis='x')
    put((1359, 66, -1161), 'minecraft:lantern', 'small warm light over the waiting bench', hanging=True, waterlogged=False)
    mounts[1359, 66, -1161] = (1359, 67, -1161)
    put((1359, 64, -1161), 'handcrafted:dark_oak_bench', 'chandler customer waiting perch', facing='west', shape='single', color='brown', waterlogged=False)
    put((1359, 64, -1162), 'minecraft:grindstone', 'actual hardware sharpening station, no invented stock', face='floor', facing='north')
    put((1360, 63, -1162), 'minecraft:mossy_stone_bricks', 'one small full stone potted-flower plinth on actual soil62')
    put((1360, 64, -1162), POTS[0], 'contained Sea of Thieves plumeria on the new full plinth')
    mounts[1360, 64, -1162] = (1360, 63, -1162)
    sign((1360, 65, -1162), 'north', ['East Coal', 'Hardware repair', 'Sharpen & mend', 'Please wait here'])
    mounts[1360, 65, -1162] = (1360, 65, -1161)
    root(1358, 63, -1163)
    root(1359, 62, -1163, 'regions_unexplored:blue_lupine')

    # Shoal: a two-column chart stall alongside, rather than across, the public
    # approach. A shallow 3x3 open canopy preserves three metres beneath it.
    for z in (-1187, -1185):
        for y in (64, 65, 66):
            put((1355, y, z), 'dawnoftimebuilder:charred_spruce_timber_frame_pillar', 'rooted chart-stall end post', axis='y')
    for x in (1355, 1356, 1357):
        for z in (-1187, -1186, -1185):
            put((x, 67, z), 'minecraft:dark_oak_slab', 'very small open weathered chart-stall canopy', type='bottom', waterlogged=False)
    for z in (-1187, -1185):
        put((1356, 66, z), 'mythrais:curved_corbel_dark_oak', 'supported carved knee below the little projecting canopy', facing='east', shape=0)
        mounts[1356, 66, z] = (1355, 66, z)
    put((1356, 64, -1187), 'minecraft:cartography_table', 'real pilot-chart working counter, no container contents')
    put((1356, 65, -1187), 'handcrafted:stackable_book', 'shipping ledgers on the actual full chart table', facing='east', books=3, seed=11)
    mounts[1356, 65, -1187] = (1356, 64, -1187)
    put((1355, 64, -1186), 'handcrafted:dark_oak_bench', 'pilot waiting and chart-reading perch', facing='east', shape='single', color='brown', waterlogged=False)
    put((1356, 64, -1185), 'minecraft:dark_oak_planks', 'full small display cabinet pedestal; no invented inventory')
    put((1356, 65, -1185), POTS[4], 'contained tropical red fern softens the trade counter')
    mounts[1356, 65, -1185] = (1356, 64, -1185)
    put((1356, 66, -1186), 'minecraft:lantern', 'practical chart-reading light beneath the low canopy', hanging=True, waterlogged=False)
    mounts[1356, 66, -1186] = (1356, 67, -1186)
    sign((1356, 65, -1186), 'east', ['Shoal Warden', 'Pilots & charts', 'Soundings here', 'Mind the tide'])
    # The middle post is a deliberately new supported sign backing, not an
    # existing neighbour wall or an unsupported floating wall-sign model.
    put((1355, 65, -1186), 'minecraft:dark_oak_planks', 'new full chart-sign backing between the end posts')
    mounts[1356, 65, -1186] = (1355, 65, -1186)

    # Thin Sail: one narrow mending edge leaves two complete walking columns.
    post(1379, -1123)
    for z in (-1124, -1125):
        put((1379, 67, z), 'minecraft:dark_oak_wood', 'continuous short sail-shop task-light arm', axis='z')
    put((1379, 66, -1124), 'minecraft:lantern', 'small warm sail-repair light above the narrow edge', hanging=True, waterlogged=False)
    mounts[1379, 66, -1124] = (1379, 67, -1124)
    sign((1379, 65, -1124), 'north', ['Thin Sail', 'Sail mending', 'After the storm', 'Mind the hem'])
    mounts[1379, 65, -1124] = (1379, 65, -1123)
    put((1379, 64, -1126), 'handcrafted:dark_oak_bench', 'mender waiting and hand-sewing seat', facing='west', shape='single', color='brown', waterlogged=False)
    put((1379, 64, -1127), 'minecraft:loom', 'real loom beside the sail workshop, no fake goods', facing='west')
    put((1379, 64, -1128), 'minecraft:dark_oak_planks', 'full display plinth on actual grass')
    put((1379, 65, -1128), POTS[1], 'contained pink plumeria by the mending bench')
    mounts[1379, 65, -1128] = (1379, 64, -1128)
    root(1379, 63, -1129)
    root(1379, 63, -1125, 'regions_unexplored:aster')
    require_outdoor_rule(blocks, 'Three separate muted eastern trade-edge scenes')
    return blocks, tags, walks, mounts, plants, objects


def check_preservation(blocks, walks, mounts, kept, all_main):
    if len(blocks) > MAX_TARGETS or any(not (1355 <= x <= 1379 and -1187 <= z <= -1123 or 1358 <= x <= 1360 and -1163 <= z <= -1161) for x, y, z in blocks):
        raise UserError('Finite three-compound exterior detail scope exceeded')
    collision = sorted(q for q in blocks if q in kept or (q[0], q[2]) in all_main)
    if collision:
        raise UserError('No existing compound cell, room AIR or future building floor may be overwritten: ' + str(collision[:8]))
    for x, z in walks:
        for y in (64, 65):
            if blocks.get((x, y, z), AIR) != AIR:
                raise UserError('The full two-wide visiting shoulder must retain two-high headroom')
    for q, support in mounts.items():
        if q not in blocks or support not in blocks or blocks[support] == AIR:
            raise UserError('Every lamp, sign, pot, book and corbel has a real new support')


def exact_sources(home):
    kept, refs = {}, []
    for name, (plan_sha, result_id, result_sha) in COMPOUNDS.items():
        plan = home / ADMITTED / (name + '-complete-after-VERIFY-ONLY.json')
        result = home / 'dashboard/settlement' / ('settlement-result-' + result_id + '.json')
        if digest(plan) != plan_sha or digest(result) != result_sha or Path(str(result)+'.complete').read_text().strip() != result_sha:
            raise UserError('Exact hash-marked native compound verification required')
        receipt = read_json(result)
        if receipt.get('operation') != 'verify' or receipt.get('plan_sha256') != plan_sha or receipt.get('failures') != 0 or receipt.get('error') or receipt.get('cleanup_required') or receipt.get('temporary_tickets_remaining') != 0:
            raise UserError('Do not borrow failed or partial compound acceptance')
        kept.update(flatten(read_json(plan)))
        refs.append({'compound': name, 'full_plan_sha256': plan_sha, 'terminal_sha256': result_sha, 'finished': receipt['finished']})
    return kept, refs


def prepare(home, checkpoint_id, checkpoint_sha):
    home = Path(home).resolve()
    if not home.is_relative_to(Path('D:/A World for Two/staging/world-tests').resolve()):
        raise UserError('Private owned staging home only')
    reserve = guard(4*MIB, 16*MIB)
    budgets = [reader_budget()]
    receipt = read_json(home/'dashboard/settlement/backup-receipt.json')
    if (checkpoint_id, checkpoint_sha) != (CHECKPOINT, CHECKPOINT_SHA) or receipt.get('verified') is not True or receipt.get('id') != checkpoint_id or receipt.get('sha256') != checkpoint_sha:
        raise UserError('Exact authenticated stopped6ad input required; no metadata-only rebinding')
    registry = read_json(home/'dashboard/settlement/registry.json')
    blocks, tags, walks, mounts, plants, objects = construct(registry)
    kept, native_refs = exact_sources(home)
    master = frozen_layout(home, EAST)
    all_main = {tuple(q) for row in master['buildings'] for q in row['actual_building_floor_columns_xz']}
    check_preservation(blocks, walks, mounts, kept, all_main)
    out = home/'staging'/('eastern-three-trade-greens-'+str(time.time_ns()))
    out.mkdir()
    terrain = None
    try:
        zinc = verify_zinc_factory(home)
        terrain = NorthTerrain(home, receipt, registry)
        before, supports, clearance = {}, {}, {}
        touched = {(x, z) for x, y, z in blocks}
        for x, z in sorted(touched | walks):
            # All chosen changes are next to natural floor63, except the two
            # explicit Coal pocket/plinth columns which retain actual soil62.
            top = 62 if (x, z) in {(1360, -1162), (1359, -1163)} else 63
            mount = natural_mount(terrain.state, x, z, top=top)
            last = mount.get('first_non_gravity')
            if not mount['stable'] and last and last[3] == 'create:zinc_ore':
                mount = dict(mount, stable=True, native_factory=zinc)
            if not mount['stable']:
                raise UserError('Exact dry stable substrate required; no bridging/filling water or gravity gaps: '+str((x,z,mount)))
            for xx, y, zz, value in mount['stack']:
                if (xx,y,zz) in terrain.entities:
                    raise UserError('No current BE may become a detail footing')
                supports[xx,y,zz] = value
        for i, q in enumerate(sorted(blocks)):
            current = terrain.state(*q)
            allowed = (GROUND | VOIDS | SOFT | NORTH_SOFT) if q in plants else (VOIDS | SOFT | NORTH_SOFT)
            if q in terrain.entities or current is None or 'waterlogged=true' in current or key(current) not in allowed:
                raise UserError('Preserve actual objects, water, foliage ownership, stock and BEs: '+str((q,current)))
            before[q] = current
            if i % 32 == 0:
                budgets.append(reader_budget())
        # Literal old natural cover is listed as a finite new AIR operation;
        # existing source-defined body AIR never confers demolition authority.
        retained_thresholds = []
        for x, z in sorted(walks):
            threshold = kept.get((x,64,z))
            if threshold is not None and key(threshold).endswith('_stairs') and 'half=bottom' in threshold:
                # Native55 already proved this literal doorway half-step. It
                # remains unchanged and becomes explicit current before proof,
                # rather than being cleared as if the older save were current.
                floor_y, floor = 64, threshold
                retained_thresholds.append({'position':[x,64,z],'state':threshold})
            else:
                floor_y, floor = 63, terrain.state(x,63,z)
                if floor is None or key(floor) not in GROUND or (x,63,z) in terrain.entities:
                    raise UserError('The two-wide shoulder needs actual dry full flooring63')
            before[x,floor_y,z] = floor
            supports[x,floor_y,z] = floor
            for y in (floor_y+1,floor_y+2):
                q = x,y,z
                current = kept.get(q,terrain.state(*q))
                if current is None or key(current) not in VOIDS | SOFT | NORTH_SOFT or 'waterlogged=true' in current or q in terrain.entities:
                    raise UserError('Never widen a shoulder through existing objects/source AIR/water: '+str((q,current)))
                before[q] = current
                clearance[q] = AIR
                if key(current) not in VOIDS:
                    if q in kept:
                        raise UserError('Existing native compound vegetation is not newly owned shoulder cover')
                    blocks[q] = AIR
        if len(blocks) > MAX_TARGETS:
            raise UserError('Finite180 changed-target limit exceeded')
        sources = terrain.snapshot.sources
        peak = reader_budget()
        terrain.close()
        terrain = None
        # A full context plan is verify-only: old furniture/container states are
        # protected, with absolutely no old NBT, Items or LootTables serialized.
        full = {**kept, **supports, **blocks, **clearance}
        docs = {
            'detail-PLACE-ONCE.json': native_payload(registry, blocks, checkpoint_sha, 'EAST3 — rooted trade-edge greenery, pilot stall and tiny mending scenes', tags=tags),
            'before-VERIFY-ONLY.json': native_payload(registry, before, checkpoint_sha, 'VERIFY ONLY — literal stopped targets and clear visiting shoulders'),
            'stable-supports-VERIFY-ONLY.json': native_payload(registry, supports, checkpoint_sha, 'VERIFY ONLY — unchanged dry full footing stacks'),
            'complete-after-VERIFY-ONLY.json': native_payload(registry, full, checkpoint_sha, 'VERIFY ONLY — three actual compounds plus exterior details; no old NBT replay', tags=tags),
            'normal-survival-SETTLE-ONLY.json': native_payload(registry, {q:s for q,s in blocks.items() if s != AIR}, checkpoint_sha, 'NORMAL UPDATE ONLY — new supported plants/lights/props'),
        }
        for name, doc in docs.items():
            if name != 'detail-PLACE-ONCE.json':
                doc.update(construction_forbidden=True, verification_only=True)
        ru = home/'server/mods/regions-unexplored-0.6.3-neoforge-21.1.jar'
        with zipfile.ZipFile(ru) as jar:
            shrub = jar.read('net/regions_unexplored/block/type/shrub/ShrubBlock.class')
            support_tag = jar.read('data/regions_unexplored/tags/block/supports/shrubs.json')
        if hashlib.sha256(shrub).hexdigest() != 'ac0153170c56c14785ab262f7c70a088ddb50634857b23dcd7eac4d13882f710' or json.loads(support_tag)['values'] != ['#minecraft:dirt']:
            raise UserError('Native double-height shrub anatomy/support witness changed')
        raw = {name:(json.dumps(doc,separators=(',',':'))+'\n').encode() for name,doc in docs.items()}
        manifest = {
            'format':'awft-eastern-three-trade-greens:1', 'source_sha256':digest(Path(__file__)),
            'checkpoint_id':checkpoint_id, 'checkpoint_sha256':checkpoint_sha,
            'native55_compound_proofs':native_refs, 'old_compound_context_cells':len(kept),
            'new_targets':len(blocks), 'new_signs':len(tags), 'old_BE_or_inventory_targets':0,
            'inventory_items_written':0, 'world_writes':0, 'native_actions':0,
            'scenes':['Coal: hardware sharpening, waiting bench, small task light and native flowers',
                      'Shoal: shallow open chart stall, ledgers, waiting seat and contained fern',
                      'Thin Sail: real mending loom, sewing perch and rooted/contained blossoms'],
            'objects':objects, 'literal_new_root_cells':[list(q) for q in sorted(plants)],
            'two_wide_walking_columns_xz':[list(q) for q in sorted(walks)],
            'unchanged_native55_entry_halfsteps':retained_thresholds,
            'existing_and_future_main_floor_columns_kept':len(all_main),
            'new_detail_native_supports':[{'position':list(q),'support':list(s)} for q,s in sorted(mounts.items())],
            'native_shrub_support_witness':{'jar_sha256':digest(ru),'class_sha256':hashlib.sha256(shrub).hexdigest(),'supports':['#minecraft:dirt'],'no_sapling_or_bonemeal_tree':True},
            'saved_sources':sources, 'reserve_guard':reserve, 'reader_peak_RSS_bytes':max([peak['owned_reader_rss_bytes']]+[v['owned_reader_rss_bytes'] for v in budgets]),
            'status':'SOURCE ONLY — not placed, survived, rendered or accepted',
            'required_native_order':['Current empty edit lease; human work must remain untouched', 'Verify exact BEFORE and stable supports; any drift stops', 'Place new target cells only, no old NBT/stock', 'Normal shape/survival update on new details only', 'Strict full after verification and actual street/interior view'],
            'limits':['Snapshot6ad predates Native55 compounds; exact passed Native55 geometry is an explicit immutable read-only overlay',
                      'No authority over later human or later compound edits: fresh serialized native preimage is mandatory',
                      'All actual and future building floors/rooms protected; human zipline/tubes are outside the finite eastern scope',
                      'Three small scenes do not claim the rest of Pirate City landscaped or visually approved'],
            'files':{name:{'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)} for name,data in raw.items()},
        }
        raw['manifest.json'] = (json.dumps(manifest,separators=(',',':'))+'\n').encode()
        if sum(map(len,raw.values())) > 16*MIB:
            raise UserError('Finite16MiB packet limit exceeded')
        for name, data in raw.items():
            (out/name).open('xb').write(data)
        return {'folder':str(out), 'manifest_sha256':digest(out/'manifest.json'), 'targets':len(blocks), 'files':manifest['files'], 'world_writes':0}
    except Exception as exc:
        (out/'refusal.json').open('x',encoding='utf-8').write(json.dumps({'reason':type(exc).__name__+': '+str(exc),'source_sha256':digest(Path(__file__)),'checkpoint_id':checkpoint_id,'world_writes':0})+'\n')
        raise UserError(str(exc)+'; preserved '+str(out)) from exc
    finally:
        if terrain is not None:
            terrain.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--home',type=Path,required=True)
    parser.add_argument('--checkpoint-id',required=True)
    parser.add_argument('--checkpoint-sha',required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.home,args.checkpoint_id,args.checkpoint_sha),indent=2))
