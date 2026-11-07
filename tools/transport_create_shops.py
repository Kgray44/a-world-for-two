"""Three fixed, additive Tortuga processes for the existing Native build pipeline.

Reads an authenticated stopped save. Writes new private SOURCE proposals only;
never opens the current world, issues a command, supplies items or installs code.
The owner-completed zipline/Hypertubes and all existing furniture stay untouched.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import time
import zipfile

from control_room.common import UserError, digest, read_json, utcnow
from tools.artistic_captains_hall import native_payload
from tools.artistic_materials import require_material_rule
from tools.playtest import guard
from tools.settlement_attractions import BackupWorld

MIB = 1024**2
MAX_OUTPUT = 2*MIB
CREATE_SHA = 'ef87fe5709f1ba1f5b8bb20a2925b5afb4669e178fd6d8bf10c167759eefe37a'
SOURCE_INDEX = 'staging/eastern-attached-clerestories-1793244651287380500/SOURCE-INDEX.json'
SOURCE_INDEX_SHA = '3477c55112ef859778262412134c0f8b66843868015ebf50ade52221b77973bf'
AIR = 'minecraft:air'
HUMAN = ((1088, 58, -1270, 1174, 196, -744),
         (1324, 62, -1003, 1338, 90, -931))
CLASS_PINS = {
    'press/MechanicalPressBlock.class': '662bcda03b302a502faa30e650e64df323c79259c15cc0a61fabba3dbfba043c',
    'millstone/MillstoneBlock.class': '953ff7f295316da56b5804a6f7a1d9069915fda6e097649f0bd07441e30b8c2d',
    'crank/HandCrankBlock.class': '6a151f1368fe95ff074dd1b306b6edc3d35f91b197352b5e8bec90b43de250f3',
    'crank/HandCrankBlockEntity.class': 'e05b7f0a4a828502506d1d8490b260ad5d742dd38b7f444f18febbee6da3335c',
    'saw/SawBlock.class': '990fb5b714c255db6b9a4e007a89ee539b32fef1940013347a7b479575e7b802',
}
RECIPE_PINS = {
    'pressing/iron_ingot.json': '83dcd5e1d0b6cd76ef4801eb9291e1bf2fba3093a5a996f2079c4a789431d900',
    'milling/wheat.json': '6ec4625e516429fd78aee262bbe6e5cede71a0ba6730fcea38be0c16878faf2c',
}


def key(state):
    return state.split('[', 1)[0]


def state(registry, name, **props):
    schema = registry['blocks'].get(name)
    if schema is None or set(schema) != set(props):
        raise UserError('Use complete registered Native properties: '+name)
    values = {k: str(v).lower() for k, v in props.items()}
    if any(v not in schema[k] for k, v in values.items()):
        raise UserError('Unregistered Native property: '+name)
    return name+('['+','.join(k+'='+v for k, v in sorted(values.items()))+']' if props else '')


def artifact_facts(create_jar):
    create_jar = Path(create_jar)
    if digest(create_jar) != CREATE_SHA:
        raise UserError('Exact installed Create6.0.10 artifact required')
    with zipfile.ZipFile(create_jar) as archive:
        for suffix, sha in CLASS_PINS.items():
            raw = archive.read('com/simibubi/create/content/kinetics/'+suffix)
            if hashlib.sha256(raw).hexdigest() != sha:
                raise UserError('Pinned Native kinetic API changed: '+suffix)
        recipes = {}
        for suffix, sha in RECIPE_PINS.items():
            raw = archive.read('data/create/recipe/'+suffix)
            if hashlib.sha256(raw).hexdigest() != sha:
                raise UserError('Pinned packaged recipe changed: '+suffix)
            recipes[suffix] = json.loads(raw)
        bamboo = json.loads(archive.read('data/create/recipe/cutting/bamboo_planks.json'))
        if bamboo != {'type': 'create:cutting', 'ingredients': [{'item': 'minecraft:bamboo_planks'}],
                      'processing_time': 20, 'results': [{'id': 'minecraft:bamboo_mosaic'}]}:
            raise UserError('Do not assume a wood-cutting yield from a different recipe')
        recipes['cutting/bamboo_planks.json'] = bamboo
    return {'jar_sha256': CREATE_SHA, 'class_sha256': CLASS_PINS,
            'packaged_recipes': recipes, 'loaded_recipe_manager_observed': False}


def shops(registry):
    """Fixed human-composed locations; never search/clear the town for a fit."""
    def s(name, **props):
        return state(registry, name, **props)
    forge = {
        (1357, 67, -1127): s('create:mechanical_press', facing='east'),
        (1357, 65, -1127): s('create:depot', waterlogged=False),
        (1358, 67, -1127): s('create:hand_crank', facing='east', waterlogged=False),
        (1360, 65, -1129): s('minecraft:blast_furnace', facing='south', lit=False),
        (1355, 65, -1128): s('minecraft:barrel', facing='up', open=False),
        (1362, 65, -1127): s('minecraft:barrel', facing='up', open=False),
        (1363, 65, -1128): s('minecraft:cauldron'),
        (1355, 66, -1130): s('minecraft:bell', attachment='single_wall', facing='south', powered=False),
        (1358, 66, -1130): s('minecraft:wall_torch', facing='south'),
    }
    # A real masonry press frame and dark, closed furnace hood. No open fire,
    # artificial heat, supplied fuel, fake bellows animation or copied stock.
    for x in (1356, 1359):
        for y in (65, 66, 67):
            forge[x, y, -1127] = s('minecraft:polished_andesite')
    for x in (1359, 1361):
        for y in (65, 66):
            forge[x, y, -1129] = s('minecraft:polished_blackstone_bricks')
    forge[1360, 66, -1129] = s('minecraft:polished_blackstone_bricks')
    galley = {
        (1290, 65, -1123): s('create:millstone'),
        (1291, 65, -1123): s('create:cogwheel', axis='y', waterlogged=False),
        (1291, 66, -1123): s('create:hand_crank', facing='up', waterlogged=False),
        (1289, 65, -1123): s('minecraft:barrel', facing='up', open=False),
        (1293, 65, -1123): s('minecraft:barrel', facing='up', open=False),
    }
    joiner = {
        (1280, 65, -1159): s('create:mechanical_saw', facing='up', axis_along_first=True, flipped=False),
        (1281, 65, -1159): s('create:hand_crank', facing='east', waterlogged=False),
        (1279, 65, -1161): s('minecraft:barrel', facing='up', open=False),
        (1281, 65, -1161): s('minecraft:barrel', facing='up', open=False),
    }
    return {
        'pelican-forge': {'blocks': forge, 'stands': [(1357, 65, -1126), (1358, 65, -1126), (1360, 65, -1128)],
                         'extra_air': [(1357, 66, -1127), (1363, 66, -1128)],
                         'wall_supports': [(1355, 66, -1131), (1358, 66, -1131)],
                         'inputs_outputs': ['1 raw iron + actual furnace fuel -> 1 iron ingot',
                                            '1 iron ingot -> 1 create:iron_sheet',
                                            '1 filled water bucket -> cauldron level3 + same empty bucket'],
                         'story': 'Pelican Forge: enclosed smelting hearth, overhead hand press, real quench tub, order bell, retained anvils and sharpening/repair benches'},
        'harbor-chair': {'blocks': galley, 'stands': [(1290, 65, -1124), (1291, 65, -1124)],
                         'extra_air': [(1290, 66, -1123)], 'wall_supports': [],
                         'inputs_outputs': ['16 wheat -> 16..48 flour in even increments above16, and0..16 seeds; record actual randomized yield'],
                         'story': 'Harbor Chair & Cup: open-topped hand mill beside the existing galley, with separate new raw/finished barrels'},
        'sandbar': {'blocks': joiner, 'stands': [(1281, 65, -1158), (1279, 65, -1159)],
                    'extra_air': [(1280, 66, z) for z in range(-1161, -1156)], 'wall_supports': [],
                    'inputs_outputs': ['1 bamboo plank -> 1 bamboo mosaic; actual saw recipe20 processing ticks before speed scaling'],
                    'story': 'Sandbar Carpenter: upright real plank-pattern saw with side hand crank; collect actual ejected work before storing it'},
    }


def route_body(source):
    origin = source['origin']
    points = {tuple(origin[i]+q[i] for i in range(3))
              for route in source['routes'] for q in route.get('feet_local', [])}
    points.update(tuple(origin[i]+room['local_feet'][i] for i in range(3)) for room in source['rooms'])
    return {tuple(q[i]+(dy if i == 1 else 0) for i in range(3)) for q in points for dy in (0, 1)}


def witnesses(spec, source):
    full = {tuple(row[:3]): row[3] for row in source['complete_expected_state_context_ONLY']}
    body = route_body(source)
    if set(spec['blocks']) & body:
        raise UserError('Keep every existing room route, stair, entry and scene standing point')
    if any(full.get(q) != AIR for q in spec['blocks']):
        raise UserError('Only positively authored interior AIR may receive these additions')
    clear = set(spec['extra_air'])
    clear.update((x, y+dy, z) for x, y, z in spec['stands'] for dy in (0, 1))
    if clear & set(spec['blocks']):
        raise UserError('A machine occupies its own service/head/item clearance')
    # Entire prior route is read/verified, not emitted as a construction delta.
    clear |= body
    if any(full.get(q) != AIR for q in clear):
        raise UserError('A proposed operating stance or prior route is not literal source AIR')
    floors = {(x, 64, z) for x, _, z in set(spec['blocks']) | set(spec['stands'])}
    support = floors | set(spec['wall_supports'])
    if any(q not in full or key(full[q]) in {AIR, 'minecraft:water', 'minecraft:lava'} for q in support):
        raise UserError('Every new work position needs its real retained floor/wall')
    context = clear | support
    # Six-face context makes the normal placement/settle neighborhood explicit.
    for x, y, z in spec['blocks']:
        context.update((x+dx, y+dy, z+dz) for dx, dy, dz in
                       ((1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1)))
    return full, clear, support, context - set(spec['blocks'])


def derive(registry, name, spec, source, actual, protected, native_backup_sha):
    full, clear, support, context = witnesses(spec, source)
    targets = set(spec['blocks']) | context
    if set(actual) != targets or any(not isinstance(s, str) for s in actual.values()):
        raise UserError('Exact bounded saved targets/context required; no missing AIR guesses')
    if any(any(all(b[i] <= q[i] <= b[i+3] for i in range(3)) for b in HUMAN) for q in targets):
        raise UserError('Never enter the owner-completed tube/zipline reservations')
    if set(spec['blocks']) & set(protected):
        raise UserError('Never replace a saved block entity, even if its state says AIR')
    if any(actual[q] != AIR for q in spec['blocks']):
        raise UserError('Preserve every current object; a changed target holds this shop')
    if any(actual[q] != AIR for q in clear):
        raise UserError('Current route/headroom/input/ejection space is obstructed')
    if any(actual[q] != full[q] for q in support):
        raise UserError('Actual floor/wall differs from the retained built shop')
    complete = {**actual, **spec['blocks']}
    return {
        'before-VERIFY-ONLY.json': native_payload(registry, actual, native_backup_sha, name+' exact current predecessor and retained context'),
        'supports-VERIFY-ONLY.json': native_payload(registry, {q: actual[q] for q in support}, native_backup_sha, name+' retained real floor and backing'),
        'additions-PROPOSAL.json': native_payload(registry, spec['blocks'], native_backup_sha, spec['story'], placement=True),
        'normal-joins-SETTLE-ONLY.json': native_payload(registry, spec['blocks'], native_backup_sha, name+' new hardware normal joins only'),
        'complete-after-VERIFY-ONLY.json': native_payload(registry, complete, native_backup_sha, name+' complete additions and unchanged operating/neighbor context'),
    }


def prepare(home, checkpoint_id, checkpoint_sha, create_jar):
    home = Path(home).resolve()
    if home.parent != Path(r'D:\A World for Two\staging\world-tests').resolve():
        raise UserError('Only the declared isolated construction home is supported')
    if not re.fullmatch(r'\d{8}T\d{6}Z-[a-f0-9]{6}', checkpoint_id):
        raise UserError('Exact retained stopped checkpoint required')
    reserve = guard(8*MIB, MAX_OUTPUT)
    receipt = read_json(home/'backups'/(checkpoint_id+'.json'))
    if receipt.get('integrity') != 'verified' or receipt.get('sha256') != checkpoint_sha:
        raise UserError('Exact verified immutable source checkpoint required')
    native = read_json(home/'dashboard/settlement/backup-receipt.json')
    if native.get('verified') is not True or not re.fullmatch('[a-f0-9]{64}', native.get('sha256', '')):
        raise UserError('Retain the actual canonical Native backup identity separately')
    if digest(home/SOURCE_INDEX) != SOURCE_INDEX_SHA:
        raise UserError('The exact built39 source index is required; do not rebind older plans')
    index = read_json(home/SOURCE_INDEX)
    registry = read_json(home/'dashboard/settlement/registry.json')
    facts = artifact_facts(create_jar)
    snapshot = BackupWorld(home, {**receipt, 'id': checkpoint_id, 'verified': True}, registry)
    raw, records = {}, []
    try:
        for name, spec in shops(registry).items():
            row = next((r for r in index['compounds'] if r['id'] == name), None)
            if row is None:
                raise UserError('Missing retained built shop '+name)
            ref = row['files']['SOURCE-ONLY']
            path = (home/ref['path']).resolve()
            if not path.is_relative_to(home/'staging') or path.stat().st_size > MIB or digest(path) != ref['sha256']:
                raise UserError('Retained source file changed or escaped custody')
            source = read_json(path)
            _, _, _, context = witnesses(spec, source)
            targets = set(spec['blocks']) | context
            actual = {q: snapshot.state(q) for q in sorted(targets)}
            docs = derive(registry, name, spec, source, actual, snapshot.protected, native['sha256'])
            for filename, data in docs.items():
                raw[name+'/'+filename] = data
            records.append({'id': name, 'source': ref, 'new_cells': len(spec['blocks']),
                            'new_hardware': dict(sorted(Counter(key(s) for s in spec['blocks'].values()).items())),
                            'blocks': [[*q, s] for q, s in sorted(spec['blocks'].items())],
                            'operating_feet': spec['stands'], 'inputs_outputs': spec['inputs_outputs'],
                            'all_prior_furniture_and_routes_retained': True,
                            'new_containers_native_defaults_only': True,
                            'items_or_inventory_tags_supplied': 0,
                            'material_rule': require_material_rule(spec['blocks'], spec['story']),
                            'native_operation_and_owner_acceptance': 'UNVERIFIED'})
        saved_sources = list(snapshot.sources)
    finally:
        snapshot.close()
    manifest = {'format': 'awft-tortuga-three-create-shops-SOURCE:1', 'created': utcnow(),
                'producer_sha256': digest(Path(__file__)),
                'actual_saved_checkpoint': {'id': checkpoint_id, 'sha256': checkpoint_sha},
                'canonical_native_backup_sha256': native['sha256'],
                'canonical_identity_is_not_a_current_preimage': True,
                'retained_source_index': {'path': SOURCE_INDEX, 'sha256': SOURCE_INDEX_SHA},
                'shops': records, 'installed_artifact_facts': facts, 'saved_region_sources': saved_sources,
                'files': {n: {'sha256': hashlib.sha256(b).hexdigest(), 'bytes': len(b)} for n, b in raw.items()},
                'reserve_guard': reserve, 'native_actions': 0, 'world_writes': 0,
                'stock_or_processing_outputs_created': 0, 'new_runtime_or_observation_framework': False,
                'required_order': ['Root fresh BEFORE', 'Root retained support VERIFY', 'one additions PLACE per shop',
                                   'normal joins SETTLE', 'full AFTER', 'real one-item process and actual inventories',
                                   'batch/count proof', 'native stop/idle', 'normal save/restart and real reuse'],
                'status': 'SOURCE ONLY; no active lease, deployment, recipe-manager, kinetic, item, ride or visual acceptance',
                'owner_hypertubes_and_zipline': 'COMPLETE / OWNER ACCEPTED; preserve, never replay old7941'}
    raw['manifest.json'] = (json.dumps(manifest, ensure_ascii=False, separators=(',', ':'))+'\n').encode()
    if sum(map(len, raw.values())) > MAX_OUTPUT:
        raise UserError('Finite2MiB private source output cap exceeded')
    out = home/'staging'/('transport-create-shops-'+str(time.time_ns()))
    out.mkdir()
    for name, data in raw.items():
        target = out/name
        target.parent.mkdir(exist_ok=True)
        target.open('xb').write(data)
    return {'folder': str(out), 'manifest_sha256': digest(out/'manifest.json'),
            'bytes': sum(map(len, raw.values())), 'shops': len(records),
            'new_cells': sum(r['new_cells'] for r in records), 'native_actions': 0, 'world_writes': 0}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--home', type=Path, required=True)
    parser.add_argument('--checkpoint-id', required=True)
    parser.add_argument('--checkpoint-sha', required=True)
    parser.add_argument('--create-jar', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.home, args.checkpoint_id, args.checkpoint_sha, args.create_jar), indent=2))
