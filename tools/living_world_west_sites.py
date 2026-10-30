"""Small western LIFE source cohort; no game, runtime or profile mutation.

Reuses the existing immutable-backup reader, HOME chooser and LIFE identities.
All existing beds/jobs/BEs are excluded from assignment. The master lane must
rebind the current native habitat/POI/census and ordinary spawn gates. Insect and
bird starting positions are inspect-only until those normal spawn rules pass.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import time

from control_room.common import UserError
from tools.artistic_bridge_refinement import flatten
from tools.artistic_first_life_cohort import identity
from tools.living_world_cast import encoded, read
from tools.living_world_tortuga_sites import AIR, LAYOUT, LAYOUT_SHA, base, checked, choose, native_plan
from tools.settlement_attractions import BackupWorld


CHECKPOINT = {'id': '20261029T052317Z-89312d',
              'sha256': 'ab64b9e7b4fa0e5dad2b77deb41a6ee8344ad46c6d522a4ef2048116d7e1017a', 'verified': True}
ORIGINAL = ('staging/west15-shells-1793218803041549500/manifest.json', '52669f6d5ae92e82a18c1577a99a56e2648fc2dc570a3ff8b33987659b404f42')
NEW = ('staging/tortuga-western-spit-1793215072699978000/manifest.json', 'cbb7810513c9718345cff6440878508f529b3d1394aab854cd47bd3b5c5b9293')
COMPLETED = ('staging/west-nineteen-native51-1793216062191851100/actual-results.json', '658383fe0a4edff9cf6f88c1e005c10a625a7dec3b056525146a0bae96a747fd')
FIELD = ('staging/tortuga-narrow-workrooms-1793219506153531200/field-READONLY.json', 'e59a92bbec943588438782c8ed7fdd4ebacc80f422861766e709e2a5aa1b8880')
ZIP = ('staging/zipline-west-v2-source-1793152099836099800/all-v2-RESERVATION-ONLY.json', '92ea594836795a61e00f5cc32290d49d1d47b9fd6eb55aeefc99d527acf8854d')
STREET = ('staging/west-street-stock-SNBT-fixed-20261028T0317Z/future-walk-furniture-reservation-ONLY.json', '59e708726681c29ef962f632f3572369ec1db0299d58e11b454b6259b09be905')
GREENERY = ('staging/WEST-GROUND-LUSH63-EXECUTION-1793239356433478800/ACTUAL-COMPLETED.json', '79da89c5dc3e03999e633aa5e5402e8d664135fe602d038c1b32618fb6ba9bd1')
NAMESPACE = ('staging/life-inspect-sealed-20261027T200847Z/recipe-01.json', '9809731636545398a759cd1c91cbf15c8497dfb1377dbb3a06126c7583ec12b3')
RIVER_BIOMES = {'minecraft:river', 'regions_unexplored:cold_river'}
HOMES = (
    ('copper-crust-cook', 'western-ten/baker', 'minecraft:smoker', 'minecraft:butcher'),
    ('bent-page-librarian', 'western-ten/bookbinder', 'minecraft:lectern', 'minecraft:librarian'),
    ('two-tides-chart-keeper', 'western-ten/mariner', 'minecraft:cartography_table', 'minecraft:cartographer'),
    ('crooked-kettle-cook', 'The Crooked Kettle', 'minecraft:smoker', 'minecraft:butcher'),
    ('bent-spar-toolsmith', 'Bent Spar Repairs', 'minecraft:smithing_table', 'minecraft:toolsmith'),
    ('seated-needle-mender', 'The Seated Needle', 'minecraft:loom', 'minecraft:shepherd'),
)


def biome(section, x, y, z):
    """Vanilla 4x4x4 non-crossing biome palette, with strict saved bounds."""
    values = section.get('biomes', {})
    palette = values.get('palette', [])
    if not 1 <= len(palette) <= 64:
        raise UserError('Missing bounded actual saved biome palette')
    index = 0
    if len(palette) > 1:
        bits = (len(palette) - 1).bit_length(); per_long = 64 // bits
        data = values.get('data', [])
        if len(data) != (64 + per_long - 1) // per_long:
            raise UserError('Incomplete saved biome data')
        ordinal = ((y & 15) // 4) * 16 + ((z & 15) // 4) * 4 + (x & 15) // 4
        index = (data[ordinal // per_long] >> ((ordinal % per_long) * bits)) & ((1 << bits) - 1)
    if index >= len(palette):
        raise UserError('Saved biome index outside palette')
    return palette[index]


def volume(snapshot, bounds):
    x0, y0, z0, x1, y1, z1 = bounds
    if (x1-x0+1) * (y1-y0+1) * (z1-z0+1) > 16000:
        raise UserError('Split the bounded source room/field')
    result = {(x, y, z): snapshot.state((x, y, z)) for x in range(x0, x1 + 1)
              for y in range(y0, y1 + 1) for z in range(z0, z1 + 1)}
    if any(v is None for v in result.values()):
        raise UserError('Unknown saved cells cannot become AIR')
    return result


def district_body(current, columns):
    """Propose only the missing geographic marker; never replace owner bounds."""
    if current.get('bounds'):
        return None
    return {'id':'tortuga','bounds':{'dimension':'minecraft:overworld',
            'min_x':min(x for x,z in columns),'max_x':max(x for x,z in columns),
            'min_y':48,'max_y':100,'min_z':min(z for x,z in columns),'max_z':max(z for x,z in columns)}}


def river(snapshot, x, z, blocked):
    bounds = [x-3, 59, z-3, x+3, 66, z+3]
    field = volume(snapshot, bounds)
    if any((xx, zz) in blocked for xx in range(x-3, x+4) for zz in range(z-3, z+4)):
        raise UserError('Retain buildings, routes and transport near water')
    observed = Counter()
    for xx in range(x-2, x+3):
        for zz in range(z-2, z+3):
            for y in (61, 62):
                if field[xx, y, zz] != 'minecraft:water[level=0]':
                    raise UserError('Actual connected two-deep source water required')
                b = biome(snapshot.chunk(xx//16, zz//16).get(y//16, {}), xx, y, zz)
                if b not in RIVER_BIOMES:
                    raise UserError('This freshwater candidate must actually be in a river biome')
                observed[b] += 1
            if field[xx, 63, zz] not in AIR:
                raise UserError('Actual unobstructed water surface/refuge required')
    return {'feet': [x+.5, 61.25, z+.5], 'roam_bounds': [x-2, 61, z-2, x+3, 63, z+3],
            'habitat': {'kind': 'WATER', 'known_bounds': bounds, 'water_bounds': [x-2, 61, z-2, x+2, 62, z+2]},
            'saved_source_water_cells': 50, 'saved_water_biomes': dict(observed)}, field


def prepare(home, output):
    home, output = Path(home).absolute(), Path(output).absolute()
    if output.exists() or output.parent != home/'staging':
        raise UserError('Use a new private source staging folder')
    start = time.monotonic()
    refs = {}
    def source(key, ref):
        doc, refs[key] = checked(home, *ref)
        return doc
    old, new = source('west15', ORIGINAL), source('west36_subset', NEW)
    completed = source('actual_west19', COMPLETED)
    if not any(r.get('action') == 'verify' and r.get('plan') == 'complete-after-VERIFY-ONLY.json'
               and r['result'].get('failures') == 0 for r in completed):
        raise UserError('Retain actual completed western construction results')
    layout = source('private_anchor_custody', (LAYOUT, LAYOUT_SHA))
    footprints = source('western_footprints', FIELD)
    zip_plan, street = source('zipline_reservation', ZIP), source('public_walks', STREET)
    greenery = source('actual_planting', GREENERY)
    population = source('existing_population_namespace', NAMESPACE)
    namespace = population['population_namespace']
    curation, cref = read(Path(__file__).resolve().parents[1]/'compat/control-bridge/proposals/life-extension/species-habitats.json', 1024**2)
    if cref['sha256'] != 'be41097fb361a62fb5b60cc93d33958a8a896048dbacdca72e6c87de8abe74d9':
        raise UserError('Exact existing species curation required')
    species = {p['entity']: p for p in curation['species']}
    main = {tuple(p) for rows in footprints['retained_source_main_footprints'].values() for p in rows}
    # A geographic identity envelope is not a fence, chunk ticket or habitat
    # proof. Ordinary villagers/animals may leave their initial small field.
    roam = [min(x for x,z in main)-16, 48, min(z for x,z in main)-16,
            max(x for x,z in main)+17, 100, max(z for x,z in main)+17]
    transport = {(x+dx, z+dz) for x, y, z in flatten(zip_plan) if y <= 67 for dx in (-1,0,1) for dz in (-1,0,1)}
    for x, z in ((1100,-1256),(1064,-1248),(1048,-1232)):
        transport.update((x+dx,z+dz) for dx in range(-5,6) for dz in range(-6,7))
    walks = {(x,z) for x,y,z in flatten(street) if 64 <= y <= 66}
    private = {tuple(r['position']) for r in layout['current_unowned_or_private_BEs_held_in_place']}
    for room in layout['retained_in_place_private_anchor_Inn_room_capsules']:
        a,b,c,d,e,f = room['source_support_bounds_xyz']
        private.update((x,y,z) for x in range(a,d+1) for y in range(b,e+1) for z in range(c,f+1))
    anchors = set(map(tuple, layout['private_human_bed_job_anchors_retained_in_place']))
    registry, registry_ref = read(home/'dashboard/settlement/registry.json', 8*1024**2)
    files, sites, held = {}, [], []
    output.mkdir()
    source_plan = dict(seed=registry['seed'], world_path=registry['world_path'], backup_sha256=CHECKPOINT['sha256'])
    def emit(name, values, verify):
        if not values:
            return
        raw = encoded(native_plan(source_plan, values, 'SOURCE WEST LIFE '+name, verify))
        if sum(v['bytes'] for v in files.values()) + len(raw) > 16*1024**2:
            raise UserError('Source-only output exceeds16MiB')
        (output/name).write_bytes(raw); files[name] = {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
    def add(key, entity, result, field, delta, **extra):
        profile = species[entity]
        row = {'name': 'ordinary-west-'+key, 'entity': entity, 'native_class': profile['native_class'],
               'native_MobCategory': profile['native_category'], 'town_site': 'west-life-'+key, **result, **extra}
        known = result['habitat']['known_bounds']
        row['roam_bounds'] = [min(roam[0],known[0]-16), min(roam[1],known[1]), min(roam[2],known[2]-16),
                              max(roam[3],known[3]+17), max(roam[4],known[4]+1), max(roam[5],known[5]+17)]
        row['roam_bounds_role'] = 'Source city outline plus one chunk identity margin only; no AI clipping and no habitat authority outside the complete known field'
        row.update(identity(namespace, row))
        row['preseed_actual_census_native_admission_and_behavior'] = 'PENDING'
        if any(field[p] not in AIR or p in snapshot.protected or p in private for p in delta):
            raise UserError('Dedicated new fixtures need exact AIR and no saved BE/private ownership')
        emit(key+'-AIR-before.json', {p: field[p] for p in delta}, True)
        emit(key+'-fitout-PROPOSAL.json', delta, False)
        emit(key+'-habitat-after-VERIFY-ONLY.json', field | delta, True)
        row['new_AIR_only_blocks'] = len(delta); sites.append(row)
    snapshot = BackupWorld(home, CHECKPOINT, registry)
    try:
        for key, premise, station, profession in HOMES:
            try:
                item = next((r for r in old['houses'] if r['id'] == premise), None)
                if item is None:
                    item = next(r for r in new['buildings'] if r['name'] == premise)
                columns = set(map(tuple, item.get('main_footprint', item.get('main_columns_xz'))))
                field = volume(snapshot, [min(x for x,z in columns)-2, 62, min(z for x,z in columns)-2,
                                          max(x for x,z in columns)+2, 82, max(z for x,z in columns)+2])
                # Dedicated new beds/jobs only: never consume a player or old
                # resident's apparently free bed, workstation or block entity.
                blocked = private | snapshot.protected | {p for p,s in field.items()
                    if base(s).endswith('_bed') or base(s) == station or (p[0],p[2]) in anchors}
                result = choose(field, columns, station, blocked)
                delta, known = result.pop('delta'), result.pop('known')
                if any((p[0],p[2]) in transport for p in delta):
                    raise UserError('Preserve live transport/mechanism approaches')
                add(key, 'minecraft:villager', result, {p:field[p] for p in known}, delta,
                    premise=item['name'], expected_vanilla_profession=profession, required_job_block=station,
                    ordinary_resident_not_new_named_Studio_character=True)
            except (UserError, KeyError, StopIteration) as error:
                held.append({'id':key, 'reason':str(error)})
        # These anchors were located in this exact authenticated saved archive.
        # Do not treat a coast, heightmap or a freshwater-themed name as water.
        for key, entity, x, z in [('river-koi','crittersandcompanions:koi_fish',968,-1250),
                                   ('river-pondie','fishofthieves:pondie',968,-1240)]:
            try:
                result, field = river(snapshot, x, z, main | transport | walks)
                add(key, entity, result, field, {}, native_navigation_predators_and_spawn_rules='PENDING')
            except UserError as error:
                held.append({'id':key, 'reason':str(error)})
        for key, entity, xyz in [('leaf-ladybug','crittersandcompanions:ladybug',(995,72,-1267)),
                                 ('leaf-bird','naturalist:bird',(1019,70,-1298))]:
            try:
                x,y,z = xyz
                if (x,z) in main | transport | walks:
                    raise UserError('Keep urban flight outside rooms/transport/walks')
                bounds = [x-3,y-5,z-3,x+3,y+5,z+3]; field = volume(snapshot,bounds)
                if any(field[x+dx,yy,z+dz] not in AIR for dx in range(-1,2) for dz in range(-1,2) for yy in range(y,y+4)):
                    raise UserError('Actual unobstructed native flight volume required')
                if any(snapshot.state((x,yy,z)) not in AIR for yy in range(y,85)):
                    raise UserError('Retain an actual outdoor flight space, not a roofed room')
                leaves = sum(base(v).endswith('_leaves') for v in field.values())
                if leaves < 3:
                    raise UserError('Actual retained leafy habitat required')
                result = {'feet':[x+.5,y,z+.5], 'roam_bounds':[x-2,y-1,z-2,x+3,y+4,z+3],
                          'habitat':{'kind':'AIR','known_bounds':bounds}, 'saved_retained_leaf_cells':leaves}
                add(key, entity, result, field, {}, inspect_only_until_ordinary_native_spawn_rules_pass=True,
                    limitation='Elevated air beside actual foliage; no forced spawn, artificial grass, clearing or NoAI. Hold if native placement rules refuse.')
            except UserError as error:
                held.append({'id':key,'reason':str(error)})
        if time.monotonic()-start > 90 or len(snapshot.chunks) > 128:
            raise UserError('Bounded saved-source read exceeded; retain partial receipts for review')
        saved_refs = snapshot.sources.copy()
    finally:
        snapshot.close()
    report = {'format':'awft-west-life-source-candidates:1','source_only':True,'observed_saved_checkpoint':CHECKPOINT,
              'sources':refs,'registry_source':registry_ref,'actual_saved_region_sources':saved_refs,
              'population_namespace':namespace,'sites':sites,'held':held,'files':files,
              'named_ten_sites_or_character_profiles_changed':False,'existing_seven_and_all_retained_intents_preserved':True,
              'total_new_fixture_blocks':sum(s['new_AIR_only_blocks'] for s in sites),
              'suggested_batches':[{'ids':[r[0] for r in HOMES[:3]],'maximum_new':3},
                                    {'ids':[r[0] for r in HOMES[3:]],'maximum_new':3},
                                    {'ids':['river-koi','river-pondie'],'maximum_new':2},
                                    {'ids':['leaf-ladybug','leaf-bird'],'maximum_new':2,'inspect_only':True}],
              'budgets':'Use existing v4 current global/per-species/per32m/ramp budgets including retained identities.56 is first target, not a project cap or another56.',
              'world_runtime_config_pack_client_JAR_or_profile_writes':0,'native_spawn_or_gameplay_acceptance':False,
              'next':'Master rebinds fresh source/Native preimages,≤4 actual town authority sources per batch, actual UUID/predator/navigation/POI and normal spawn inspect before seed. Ambient scripted only; no external provider.'}
    characters, _ = read(home/'dashboard/characters/registry.json',8*1024**2)
    tortuga = next(d for d in characters['config']['districts'] if d['id']=='tortuga')
    city_columns = main | {tuple(p) for b in layout['buildings'] if b.get('masses') for p in b['actual_building_floor_columns_xz']}
    proposed = district_body(tortuga,city_columns)
    (output/'tortuga-ambient-bounds-PROPOSAL.json').write_bytes(encoded({
        'source_only':True,'existing_bounds':tortuga.get('bounds'),'preserve_existing_bounds':proposed is None,
        'existing_endpoint':'/api/characters/district','body_without_fresh_expected_revision':proposed,
        'knowledge_dialogue_names_and_models_changed':False,'runtime_installed':False,
        'purpose':'Unbound ordinary villagers need geographic Tortuga markers for existing curated ambient dialogue.',
        'next':'Root reviews actual district overlap, supplies fresh expected revision, saves only id/bounds through existing endpoint and Apply/hash; no world or spawn authority.'}))
    report['ordinary_ambient_bounds_proposal']='tortuga-ambient-bounds-PROPOSAL.json'
    (output/'west-cohort-SOURCE-ONLY.json').write_bytes(encoded(report))
    return {'output':str(output),'candidates':len(sites),'held':held,'new_AIR_only_blocks':report['total_new_fixture_blocks']}


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--home',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();print(json.dumps(prepare(args.home,args.output),indent=2))
