"""Three fixed West shop additions through the existing Native plan pipeline.

The accepted original West models must exactly reproduce their frozen full
Source, including literal routes. Current states come only from an authenticated
stopped backup. No world command, inventory NBT, new runtime or observer exists.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import time
import tomllib
import zipfile

from control_room.common import UserError, digest, read_json, utcnow
from tools.artistic_bridge_refinement import flatten
from tools.artistic_captains_hall import native_payload
from tools.artistic_materials import require_material_rule
from tools.playtest import guard
from tools.settlement_attractions import BackupWorld
from tools.transport_create_shops import AIR, HUMAN, MIB, artifact_facts, key, state

MAX_OUTPUT = 2*MIB
SHARED_HELPER_SHA = 'd50f4641238e62fda49327ab42d3cd470c2abf923f6af45916cee9b42cab364c'
BUNDLE = 'staging/tortuga-western-spit-1793215072699978000'
MANIFEST_SHA = 'cbb7810513c9718345cff6440878508f529b3d1394aab854cd47bd3b5c5b9293'
FULL_SHA = '756f1cbc2bbe4e245237b0ec069ad8658815fdd02cb6b5d12e48cf9db9edb1eb'
FACTORIES = {
    'artistic_tortuga_western_spit.py': 'df87d2c1e4ae90ec305b3e556a75943f2ac781c7416b4724b102005d92e51658',
    'artistic_tortuga_fill.py': '842bead35183269d539c80c42e06ff732d3872a4e593af1e58e146b7c6595601',
    'artistic_tortuga_frontages.py': 'd3b0181e88535ee678471e3c60f86042e006b01403baf0a1ec33809ec2a924ba',
    'artistic_tortuga_variants.py': 'f6e2af4c5ca93659e8cdc9630e9049e6d08c142fa075ee46d2a48fba126d4e28',
}
MIXER_CLASSES = {
    'kinetics/mixer/MechanicalMixerBlock.class': 'be7cf3d73ed04f18397565005b8cd211d421bbee79ab887202a94295097a18ac',
    'kinetics/mixer/MechanicalMixerBlockEntity.class': 'cbaba0d1cc7cac2e8483e56b9ed1c0c15832ade1b33e0abb6ad07df5cea5b53b',
    'processing/basin/BasinOperatingBlockEntity.class': 'e2c0d4132b8563d77028c9a3af10725e2837366c2d982be38a53ab88cc52cfcc',
    'processing/basin/BasinBlock.class': 'dc5993774add4156689299e79942258caad53e26fbb498b5d477e488827de795',
}


def specifications(registry):
    def s(name, **props):
        return state(registry, name, **props)
    return {
        'crooked-kettle-dough': {
            'building': 'The Crooked Kettle',
            'blocks': {(1024, 64, -1307): s('create:basin', facing='down'),
                       (1024, 66, -1307): s('create:mechanical_mixer'),
                       (1025, 66, -1307): s('create:cogwheel', axis='y', waterlogged=False),
                       (1025, 65, -1307): s('create:hand_crank', facing='down', waterlogged=False)},
            'operating_feet': [(1024, 64, -1306)], 'service_air': [(1024, 65, -1307)],
            'ceiling_support': [],
            'input_output': '1 plain wheat flour +1000mB actual water ->1 real Create dough; actual returned empty bucket, no heat',
        },
        'low-water-flour': {
            'building': 'Low Water Kitchen',
            'blocks': {(1037, 64, -1266): s('create:millstone'),
                       (1037, 64, -1265): s('create:cogwheel', axis='y', waterlogged=False),
                       (1037, 65, -1265): s('create:hand_crank', facing='up', waterlogged=False)},
            'operating_feet': [(1036, 64, -1266)], 'service_air': [(1037, 65, -1266)],
            'ceiling_support': [],
            'input_output': '1 wheat ->1or3 flour +0or1 seed;16wheat ->16..48 flour (even excess over16) +0..16 seeds; record actual random yield',
        },
        'bent-spar-paper': {
            'building': 'Bent Spar Repairs',
            'blocks': {(1071, 64, -1247): s('create:depot', waterlogged=False),
                       (1071, 66, -1247): s('create:mechanical_press', facing='east'),
                       (1072, 66, -1247): s('create:hand_crank', facing='east', waterlogged=False)},
            'operating_feet': [(1073, 64, z) for z in (-1247, -1246, -1245, -1244)],
            'service_air': [(1071, 65, -1247)], 'ceiling_support': [(1071, 67, -1247)],
            'input_output': '1 actual sugar cane ->1 actual paper for ship-repair templates/orders; not sugar or a3-cane recipe',
        },
    }


def retained_models(home, registry):
    # These existing pure factories are available in Root's integrated checkout.
    # They temporarily populate only this Python process's recipe table and
    # restore it on context exit; no shared source or game state is changed.
    from tools import artistic_tortuga_western_spit as spit
    from tools.artistic_tortuga_variants import variant_of
    folder = Path(spit.__file__).parent
    for name, sha in FACTORIES.items():
        if digest(folder/name) != sha:
            raise UserError('Exact accepted West pure factory required: '+name)
    base = Path(home)/BUNDLE
    if digest(base/'manifest.json') != MANIFEST_SHA or digest(base/'complete-after-VERIFY-ONLY.json') != FULL_SHA:
        raise UserError('Frozen accepted West full Source changed')
    manifest = read_json(base/'manifest.json')
    doc = read_json(base/'complete-after-VERIFY-ONLY.json')
    if doc.get('world_path') != registry['world_path'] or str(doc.get('seed')) != str(registry['seed']):
        raise UserError('Accepted West source belongs to another actual world')
    full = flatten(doc)
    wanted = {v['building'] for v in specifications(registry).values()}
    models = {}
    with spit.source_recipes():
        for row in manifest['buildings']:
            if row['name'] not in wanted:
                continue
            raw = spit.fill.rich_workscene(spit.RECIPES[row['recipe']](registry), row['recipe'])
            p = variant_of(raw, row['recipe'], row['turn'], name=row['name'], trade=row['trade'])
            origin = row['origin']
            def world(q):
                return tuple(q[i]+origin[i] for i in range(3))
            built = {world(q): value for q, value in p.blocks.items()}
            if any(full.get(q) != value for q, value in built.items()):
                raise UserError('Reconstructed West geometry must match EVERY original full Source cell: '+row['name'])
            route = {world(tuple(q[i]+(dy if i == 1 else 0) for i in range(3)))
                     for r in p.routes for q in r['positions'] for dy in (0, 1)}
            route |= {world(tuple(r['standing_point'][i]+(dy if i == 1 else 0) for i in range(3)))
                      for r in p.rooms for dy in (0, 1)}
            mains = {(x+origin[0], z+origin[2]) for x, z in p.main[p.owner]}
            models[row['name']] = {'full': built, 'routes': route, 'main': mains,
                                   'original_model_cells': len(built), 'origin': origin,
                                   'reconstructed_recipe': row['recipe'], 'turn': row['turn']}
    if set(models) != wanted:
        raise UserError('Every named existing West building is required')
    return models


def witness_geometry(spec, model):
    new = spec['blocks']
    full, routes, main = model['full'], set(model['routes']), set(model['main'])
    interior = {(x, z) for x, z in main if all((x+dx, z+dz) in main for dx, dz in ((1,0),(-1,0),(0,1),(0,-1)))}
    if any((q[0], q[2]) not in interior for q in new):
        raise UserError('Only the literal existing interior may receive hardware; no facade/outdoor/threshold changes')
    if set(new) & routes:
        raise UserError('Keep every original working/stair/entry/visiting route mask')
    if any(full.get(q) != AIR for q in new):
        raise UserError('Only positively authored Source AIR is available; never clear old furniture')
    service = set(spec['service_air']) | {(x, y+dy, z) for x, y, z in spec['operating_feet'] for dy in (0, 1)}
    if service & set(new) or any(full.get(q) != AIR for q in service):
        raise UserError('Actual machine input/body/access volume must remain literal AIR')
    floor = {(x, 63, z) for x, _, z in set(new) | set(spec['operating_feet'])}
    support = floor | set(spec['ceiling_support'])
    if any(q not in full or key(full[q]) in {AIR, 'minecraft:water', 'minecraft:lava'} for q in support):
        raise UserError('Retain actual dry original floor and overhead backing; no floating or guessed support')
    context = routes | service | support
    for x, y, z in new:
        context.update((x+dx, y+dy, z+dz) for dx, dy, dz in ((1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1)))
    return service, support, context-set(new)


def derive(registry, name, spec, model, actual, protected, canonical_sha):
    service, support, context = witness_geometry(spec, model)
    new = spec['blocks']
    if set(actual) != set(new) | context or any(not isinstance(v, str) for v in actual.values()):
        raise UserError('Every bounded real saved target/context cell is required')
    if any(any(all(b[i] <= q[i] <= b[i+3] for i in range(3)) for b in HUMAN) for q in set(new) | context):
        raise UserError('The owner-completed zipline/Hypertube reservations remain excluded')
    if set(new) & set(protected) or any(actual[q] != AIR for q in new):
        raise UserError('A current object or saved BE holds this unit; never recreate inventories')
    if any(actual[q] != AIR for q in service):
        raise UserError('Real service/input/circulation space is obstructed')
    if any(actual[q] != model['full'][q] for q in support):
        raise UserError('Actual retained floor/ceiling differs from the accepted shop')
    # Old route masks include doors, partial stairs/slabs and carved fittings.
    # Preserve their actual states; never turn the mask into fictitious AIR or
    # claim that source metadata alone proves the pre-existing human walk.
    after = {**actual, **new}
    def plan(values, title, *, place=False):
        return native_payload(registry, values, canonical_sha, title, placement=place)
    return {
        'before-VERIFY-ONLY.json': plan(actual, name+' exact real stopped preimage and retained routes'),
        'supports-VERIFY-ONLY.json': plan({q: actual[q] for q in support}, name+' retained original floor/ceiling'),
        'additions-PROPOSAL.json': plan(new, name+' existing West interior AIR additions only', place=True),
        'normal-joins-SETTLE-ONLY.json': plan(new, name+' native new hardware attachment only'),
        'complete-after-VERIFY-ONLY.json': plan(after, name+' additions plus unchanged real routes/furniture/access'),
    }


def process_facts(create_jar, home):
    facts = artifact_facts(create_jar)
    with zipfile.ZipFile(create_jar) as archive:
        for suffix, sha in MIXER_CLASSES.items():
            raw = archive.read('com/simibubi/create/content/'+suffix)
            if hashlib.sha256(raw).hexdigest() != sha:
                raise UserError('Exact installed mixer/basin API changed')
        names = ('mixing/dough_by_mixing.json', 'pressing/sugar_cane.json')
        facts['west_recipes'] = {n: json.loads(archive.read('data/create/recipe/'+n)) for n in names}
        facts['west_recipe_sha256'] = {n: hashlib.sha256(archive.read('data/create/recipe/'+n)).hexdigest() for n in names}
    config = Path(home)/'server/config/create-server.toml'
    medium = tomllib.loads(config.read_text(encoding='utf8'))['kinetics']['stats']['mediumSpeed']
    if type(medium) not in (int, float) or not 0 < medium <= 32:
        raise UserError('Current native MEDIUM speed requirement exceeds this real32RPM hand drive')
    facts.update(mixer_class_sha256=MIXER_CLASSES, current_create_config_sha256=digest(config),
                 actual_config_medium_speed=medium, source_drive_speed_abs=32,
                 mixer_native_api='small cog with axisY, NO shaft ports, MEDIUM speed requirement; basin exactly2blocks below; side small cog driven by downward crank below',
                 gameplay_or_loaded_recipe_manager_observed=False)
    return facts


def prepare(home, checkpoint_id, checkpoint_sha, create_jar):
    home = Path(home).resolve()
    if home.parent != Path(r'D:\A World for Two\staging\world-tests').resolve() or not re.fullmatch(r'\d{8}T\d{6}Z-[a-f0-9]{6}', checkpoint_id):
        raise UserError('Only the separate declared construction source home/checkpoint is supported')
    reserve = guard(8*MIB, MAX_OUTPUT)
    receipt = read_json(home/'backups'/(checkpoint_id+'.json'))
    if receipt.get('integrity') != 'verified' or receipt.get('sha256') != checkpoint_sha:
        raise UserError('Exact verified immutable recovery required')
    native = read_json(home/'dashboard/settlement/backup-receipt.json')
    if native.get('verified') is not True or not re.fullmatch('[a-f0-9]{64}', native.get('sha256', '')):
        raise UserError('Separate canonical Native backup identity required')
    if digest(Path(state.__code__.co_filename)) != SHARED_HELPER_SHA:
        raise UserError('Keep the earlier frozen shop helper exact; do not silently bind another implementation')
    registry = read_json(home/'dashboard/settlement/registry.json')
    models = retained_models(home, registry)
    facts = process_facts(create_jar, home)
    snapshot = BackupWorld(home, {**receipt, 'id': checkpoint_id, 'verified': True}, registry)
    raw, units = {}, []
    try:
        for name, spec in specifications(registry).items():
            model = models[spec['building']]
            _, _, context = witness_geometry(spec, model)
            actual = {q: snapshot.state(q) for q in sorted(set(spec['blocks']) | context)}
            docs = derive(registry, name, spec, model, actual, snapshot.protected, native['sha256'])
            raw.update({name+'/'+n: b for n, b in docs.items()})
            units.append({'id': name, 'existing_building': spec['building'], 'original_origin': model['origin'],
                          'exact_model_cells_reproduced': model['original_model_cells'],
                          'original_route_mask_cells_retained': len(model['routes']),
                          'route_mask_is_not_an_AIR_or_old_walk_acceptance_claim': True,
                          'blocks': [[*q, v] for q, v in sorted(spec['blocks'].items())],
                          'operating_feet': spec['operating_feet'], 'input_output': spec['input_output'],
                          'new_cells': len(spec['blocks']), 'all_old_BEs_items_facades_outdoor_and_routes_preserved': True,
                          'material_rule': require_material_rule(spec['blocks'], name), 'native_operation': 'UNVERIFIED'})
        regions = list(snapshot.sources)
    finally:
        snapshot.close()
    manifest = {'format': 'awft-west-three-create-shops-SOURCE:1', 'created': utcnow(),
                'producer_sha256': digest(Path(__file__)), 'existing_shop_helper_sha256': SHARED_HELPER_SHA,
                'actual_saved_checkpoint': {'id': checkpoint_id, 'sha256': checkpoint_sha},
                'canonical_native_backup_sha256': native['sha256'],
                'accepted_west_bundle': {'path': BUNDLE, 'manifest_sha256': MANIFEST_SHA, 'full_source_sha256': FULL_SHA},
                'existing_pure_factory_sha256': FACTORIES, 'units': units, 'installed_process_facts': facts,
                'saved_region_sources': regions, 'reserve_guard': reserve,
                'files': {n: {'sha256': hashlib.sha256(b).hexdigest(), 'bytes': len(b)} for n, b in raw.items()},
                'required_order': ['Root fresh per-unit BEFORE/support', 'one additive PLACE per unit', 'native normal joins', 'strict full AFTER',
                                   'real one-item/counted-fluid process', 'actual output/inventory counts', 'real input exhausted/drive stopped',
                                   'actual walk/visual/player review', 'coordinated normal save/restart and reuse'],
                'earlier_five_source_packets_regenerated_or_modified': False,
                'facade_outdoor_inventory_or_existing_BE_writes': 0, 'supplied_goods_fluid_or_inventory_NBT': 0,
                'native_actions': 0, 'world_writes': 0, 'runtime_or_observation_framework_added': False,
                'status': 'SOURCE ONLY; per-unit native deployment, recipes, player use, counts, visuals, restart and performance remain UNVERIFIED'}
    raw['manifest.json'] = (json.dumps(manifest, separators=(',', ':'))+'\n').encode()
    if sum(map(len, raw.values())) > MAX_OUTPUT:
        raise UserError('Finite2MiB West source output exceeded')
    out = home/'staging'/('transport-create-west-'+str(time.time_ns()))
    out.mkdir()
    for name, data in raw.items():
        path = out/name
        path.parent.mkdir(exist_ok=True)
        path.open('xb').write(data)
    return {'folder': str(out), 'manifest_sha256': digest(out/'manifest.json'), 'bytes': sum(map(len, raw.values())),
            'units': len(units), 'new_cells': sum(u['new_cells'] for u in units), 'native_actions': 0, 'world_writes': 0}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--home', type=Path, required=True)
    parser.add_argument('--checkpoint-id', required=True)
    parser.add_argument('--checkpoint-sha', required=True)
    parser.add_argument('--create-jar', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.home, args.checkpoint_id, args.checkpoint_sha, args.create_jar), indent=2))
