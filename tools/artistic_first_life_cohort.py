"""Source-only first living cohort for accepted old town and measured woodland.

Reuses the existing v3 LIFE engine/namespace. No request is installed, readiness
invented, entity spawned, ownership changed or private living NBT copied.
"""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import time
import uuid
import zipfile

from control_room.common import UserError, digest, read_json, utcnow
from tools.artistic_bridge_refinement import encoded
from tools.artistic_dense_canopies import entity_positions
from tools.artistic_forest_understory import settlement_plan
from tools.artistic_maritime_depth import admit_owner
from tools.artistic_native_tree_pilot import BANK, BANK_MANIFEST_SHA, checked, protected_columns
from tools.habitat_life import census
from tools.playtest import guard
from tools.settlement_attractions import BackupWorld, base


MIB = 1024**2
MAX_SECONDS = 120
MAX_OUTPUT = 16 * MIB
CURATION = 'compat/control-bridge/proposals/life-extension/species-habitats.json'
CURATION_SHA = 'be41097fb361a62fb5b60cc93d33958a8a896048dbacdca72e6c87de8abe74d9'
NAMESPACE_SOURCE = 'staging/life-inspect-sealed-20261027T200847Z/recipe-01.json'
NAMESPACE_SOURCE_SHA = '9809731636545398a759cd1c91cbf15c8497dfb1377dbb3a06126c7583ec12b3'
OLD_SITES = 'staging/woodland-habitats-source-r3-1793157192288102700/woodland-sites-REVIEW-ONLY.json'
OLD_SITES_SHA = '08e4397741d2253528bebc7dddca89d8276a840bdd9e1af8ca3ee530e8c5dfc8'
TREE_FIELDS = 'staging/forest47-frozen-custody-20261028T0643Z/future-native-fields-RESERVATION-ONLY.json'
TREE_FIELDS_SHA = '8f8aa4cdf7c45618761c6a524858e0f8419e9af6bf4352c26c39c61eca538376'
TAVERN = 'staging/artistic-pirate-spit-byte-slots-1793124362042040500/drowned-rose-VERIFY-ONLY.json'
TAVERN_SHA = 'f646d9ed046f603dc4e55c3f564949dba3a45be733dbd8c88ebba9cf48d85486'
TAVERN_PROOF = 'dashboard/settlement/settlement-result-bff9b3a4-f48e-4272-a824-4787b3e70f3e.json'
TAVERN_PROOF_SHA = 'e22dbb9cbbc5fe392607bcb6ba9892d9a463e1a0d968495093d62bf198912886'
NET = 'staging/artistic-pirate-spit-byte-slots-1793124362042040500/ninth-knot.json'
NET_SHA = '731cd08a444a8b8360484856703558de39d7fd58f9ad4e7d99f7383b19adf834'
NET_PROOF = 'dashboard/settlement/settlement-result-4afaa6be-21ba-4d40-98de-be0f6df97676.json'
NET_PROOF_SHA = '23afa29e47029e1aa626ac6b60955ac7c5c09b3aed8382690621c18bba3906d6'
GROWTH = 'staging/native28-ROOT-reviewed47-1793170167699538800/actual-outcomes.json'
GROWTH_SHA = 'eae94f1e1a4728e3de18ba9616f994da4d28952746697360b165a4fee77ffe75'
AIR = {'minecraft:air', 'minecraft:cave_air', 'minecraft:void_air'}
SOFT = {'minecraft:short_grass', 'minecraft:tall_grass', 'minecraft:fern', 'minecraft:large_fern',
        'regions_unexplored:grass_sprouts', 'minecraft:dandelion', 'minecraft:poppy',
        'minecraft:cornflower', 'minecraft:oxeye_daisy', 'minecraft:allium', 'minecraft:azure_bluet',
        'minecraft:lily_of_the_valley', 'minecraft:blue_orchid'}
SOIL = {'minecraft:grass_block', 'minecraft:dirt', 'minecraft:rooted_dirt', 'minecraft:podzol',
        'minecraft:coarse_dirt', 'minecraft:moss_block'}
HELD_NAMES = {'woodland-flower-butterfly', 'woodland-reed-dragonfly', 'woodland-quiet-allay'}


def points(bounds):
    for x in range(bounds[0], bounds[3] + 1):
        for z in range(bounds[2], bounds[5] + 1):
            for y in range(bounds[1], bounds[4] + 1):
                yield x, y, z


def columns(bounds):
    return {(x, z) for x in range(bounds[0], bounds[3] + 1) for z in range(bounds[2], bounds[5] + 1)}


def near(bounds, position, margin):
    return all(bounds[i] - margin <= position[i] <= bounds[i + 3] + margin for i in range(3))


def source_clear(value):
    # The pinned1.21.1 SnowLayerBlock uses SHAPE_BY_LAYER[layers-1]; index0
    # is Shapes.empty(). Do not broaden this to thicker snow or arbitrary mods.
    return base(value) in AIR | SOFT or value == 'minecraft:snow[layers=1]'


def identity(namespace, site):
    name, kind = site['name'], site['entity']
    return {'uuid': str(uuid.uuid5(uuid.UUID(namespace), 'awft-life:' + name + ':' + kind)),
        'entity': kind, 'member_tag': 'awft_life_' + hashlib.sha256((namespace + ':' + name + ':' + kind).encode()).hexdigest()[:24]}


def checked_source_apis(home):
    """Only pinned source-screen semantics; actual factory/shape gates still run."""
    root=home.parents[2]
    cat=root/'caches/mods/cozys-improved-cats-2.1.0-neoforge-1.21.1.jar'
    if cat.stat().st_size!=2154897 or digest(cat)!='a459cf81b1a0f9f33e1e9d0c141b162c99c9c71cacc774cb04f139ed92df54c1':
        raise UserError('Exact pinned improved-cat type registration is required')
    cases=((cat,'net/cozy/cozysimprovedcats/entity/ModEntities.class','8e3bfa3163119e75536de6c0b4a29f4f116e4f885bb94f453965ad12911d93a0'),
        (root/'server/libraries/net/minecraft/server/1.21.1-20240808.144430/server-1.21.1-20240808.144430-srg.jar',
         'net/minecraft/world/level/block/SnowLayerBlock.class','21bc5dc3ee8c8be7fba01f91c5175215416b4ce6418d3071fafac98f60339512'))
    facts=[]
    for path,member,sha in cases:
        if not 0<path.stat().st_size<=32*MIB:raise UserError('Bounded pinned source API required')
        with zipfile.ZipFile(path) as archive:
            if archive.getinfo(member).file_size>128*1024 or hashlib.sha256(archive.read(member)).hexdigest()!=sha:
                raise UserError('Exact source-screen class differs')
        facts.append({'archive':path.name,'class':member,'class_sha256':sha})
    return {'classes':facts,'pinned_improved_cat_registration_dimensions':[0.6,0.85],
        'snow_one_layer':'Native getCollisionShape indexes Shapes.empty at layers-1=0; thicker layers are not admitted by the source screen',
        'live_factory_dimensions_and_native_collision':'PENDING, never replaced by these source screens'}


def actual_tree_bees(home, snapshot):
    rows=checked(home/GROWTH,GROWTH_SHA,MIB);records=[];new_bees=0;new_nests=0
    for row in rows:
        if not row.get('status','').startswith('native sapling grown'):continue
        path=Path(row['terminal']).resolve()
        if path.parent!=(home/'dashboard/settlement').resolve() or path.stat().st_size>512*1024:
            raise UserError('Exact owned bounded tree terminal required')
        terminal=read_json(path);sha=digest(path)
        if Path(str(path)+'.complete').read_text().strip()!=sha or terminal.get('plan_sha256')!=row.get('plan_sha256') or terminal.get('cleanup_passed') is not True or terminal.get('world_recovery_required') is True:
            raise UserError('Successful tree audit has no clean immutable terminal')
        outcome_path=(path.parent/terminal['outcome_archive']).resolve()
        if outcome_path.parent!=path.parent:
            raise UserError('Tree outcome escaped its owned journal')
        outcome=checked(outcome_path,terminal['outcome_archive_sha256'],4*MIB)
        audit=terminal.get('native_bee_audit',{})
        if (outcome.get('source_plan_sha256')!=terminal['plan_sha256'] or audit.get('loaded_entity_census_unchanged') is not True
                or audit.get('existing_native_BE_bytes_unchanged') is not True or audit.get('new_live_entity_UUIDs')!=[]
                or audit.get('native_new_stored_bee_slots')!=0 or audit.get('native_new_nests')!=[]
                or outcome.get('native_be_before')!=[] or outcome.get('native_be_after')!=[]):
            raise UserError('This eight-tree zero-new-bee derivation needs a new exact hive/occupant review, never an inferred zero')
        after=outcome['native_after']['blocks']
        if not 1<=len(after)<=100000:raise UserError('Finite exact native tree after-field required')
        positions={tuple(cell[:3]) for cell in after}
        for cx,cz in {(p[0]//16,p[2]//16) for p in positions}:
            snapshot.chunk(cx,cz)
        current_BEs=positions.intersection(snapshot.protected)
        if current_BEs:
            raise UserError('A saved post-growth block entity now occupies the audited empty BE field; do not infer nest contents')
        records.append({'id':row['id'],'terminal':path.name,'terminal_sha256':sha,
            'outcome_archive':outcome_path.name,'outcome_sha256':terminal['outcome_archive_sha256'],
            'actual_new_stored_bee_slots':0,'actual_new_nests':0,'new_live_entity_UUID_count':0,
            'current_saved_BEs_in_complete_audited_after_field':0,'current_saved_known_cells':len(positions)})
    if len(records)!=8:raise UserError('Bind exactly the eight successful post47 trees; no unperformed/failed attempt is a success')
    quarantine=home/'dashboard/settlement/tree-growth-quarantine.json'
    return {'growth_batch_sha256':GROWTH_SHA,'eight_actual_audits':records,'actual_new_stored_bee_slots':new_bees,
        'actual_new_nests':new_nests,'curated_bee_members_added':0,
        'scope':'Only new bees/nests from these8 successful trees; not a count of every historic wild hive in the world',
        'tree_quarantine_present':quarantine.exists(),'quarantine_sha256':digest(quarantine) if quarantine.exists() else None,
        'native_LIFE_held_until_parent_recovery_review':True}


def retained_population(snapshot, namespace, selected, profiles):
    """A missing/unloaded old UUID never permits a second durable intent."""
    prefix=snapshot.prefix.removesuffix('region/')+'data/awft-life/'
    wanted={identity(namespace,s)['uuid'] for s in selected};counts=Counter();sources=[]
    entries=[(name,row) for name,row in snapshot.files.items() if name.startswith(prefix)]
    if len(entries)>193 or sum(row['size'] for _,row in entries)>2*MIB:
        raise UserError('Bounded complete existing LIFE ledger required')
    for name,row in entries:
        if not 0<row['size']<=8192:
            raise UserError('Unknown/partial retained LIFE intent needs review')
        raw=snapshot.archive.read(name)
        if len(raw)!=row['size'] or hashlib.sha256(raw).hexdigest()!=row['sha256']:
            raise UserError('Retained immutable LIFE ledger bytes differ')
        value=json.loads(raw);relative=name[len(prefix):]
        if relative=='population.json':
            if value.get('format')!='awft-life-world-population:2' or value.get('population_namespace')!=namespace or value.get('curation_sha256')!=CURATION_SHA or value.get('maximum_residents')!=64:
                raise UserError('Preserve unknown/foreign population authority')
        elif relative.startswith(namespace+'/') and relative.endswith(('.intent.json','.admitted.json')):
            if value.get('format')!='awft-life-world-intent:2' or value.get('population_namespace')!=namespace or value.get('entity') not in profiles:
                raise UserError('Preserve unknown retained resident intent')
            ident=value.get('uuid')
            if ident in wanted:
                raise UserError('An existing durable intent is not permission to replace or recreate its resident')
            if relative.endswith('.intent.json'):counts[value['entity']]+=1
        else:
            raise UserError('Unknown namespace/ledger data is not an empty population')
        sources.append({'file':relative,'sha256':row['sha256'],'bytes':row['size']})
    projected=counts+Counter(s['entity'] for s in selected)
    if sum(projected.values())>64 or any(n>profiles[k]['candidate_population_cap'] for k,n in projected.items()):
        raise UserError('Retained intents plus proposed animals exceed the existing policy cap')
    return {'existing_durable_intents':sum(counts.values()),'existing_species_counts':dict(counts),
        'proposed_managed_count':len(selected),'projected_managed_count':sum(projected.values()),
        'actual_native_tree_extra_bees':0,'whole_managed_cap':64,'saved_ledger_sources':sources,
        'fresh_native_ledger_and_tree_recovery_checks_still_required':True}


def habitat_field(snapshot, site, entities, tree_columns, protected, *, town=False):
    """Saved exact fields are a conservative screen, never a native spawn pass."""
    box = site['habitat']['known_bounds']
    volume = math.prod(box[i + 3] - box[i] + 1 for i in range(3))
    if not 125 <= volume <= 4096 or any(box[i + 3] - box[i] + 1 < 5 for i in range(3)):
        raise UserError('A real finite five-cell minimum full habitat box is required')
    if not town and columns(site['roam_bounds']).intersection(tree_columns):
        raise UserError('Keep first residents away from the complete active tree/read-perimeter fields')
    x, y, z = (math.floor(v) for v in site['feet'])
    field = {p: snapshot.state(p) for p in points(box)}
    if any(v is None for v in field.values()):
        raise UserError('Unknown saved habitat cells cannot become AIR')
    kind = site['habitat']['kind']
    occupied = {(xx, zz) for xx in range(x - 1, x + 2) for zz in range(z - 1, z + 2)}
    if not town and occupied.intersection(protected):
        raise UserError('Preserve actual bank/architecture/AIR/paths/fountain/cable keepouts')
    if kind in ('WATER', 'SHORE'):
        water = site['habitat']['water_bounds']
        occupied.update(columns(water))
        for p in points(water):
            if field[p] != 'minecraft:water[level=0]':
                raise UserError('Real contiguous source-water refuge is no longer present')
        for xx, zz in columns(water):
            if base(field[xx, water[4] + 1, zz]) not in AIR:
                raise UserError('Keep actual open refuge surfaces')
    if kind != 'WATER':
        # Town source masks authorize actual standing columns, not an invented
        #3x3 ownership rectangle. The real factory's FULL native AABB remains
        # mandatory. Pinned ImprovedCat EntityType dimensions are0.6×0.85.
        radius = 0 if kind == 'SHORE' or town else 1
        for xx in range(x - radius, x + radius + 1):
            for zz in range(z - radius, z + radius + 1):
                for yy in range(y, y + (4 if kind == 'AIR' else 2)):
                    if not source_clear(field[xx, yy, zz]):
                        raise UserError('Preserve an actual occupied/solid/wet body or flight core')
        if not town and kind != 'SHORE' and base(field[x, y - 1, z]) not in SOIL:
            raise UserError('Actual retained natural footing/seed ground required')
    for route in site['habitat'].get('shore_path', []) + site['habitat'].get('shelter_path', []):
        occupied.update((route[0]+dx,route[2]+dz) for dx in (-1,0,1) for dz in (-1,0,1))
        for dy in (0, 1):
            if not source_clear(field[route[0], route[1] + dy, route[2]]):
                raise UserError('A shelter/shore route is not actually body clear')
    if not town and occupied.intersection(protected):
        raise UserError('Complete actual route/swimming footprint intersects protected construction')
    # Positional admission is conservative and explicitly separate from the
    # native full-sized AABB/SpawnPlacements/EventHooks test. Never clear a mob.
    local = [(kind, pos) for kind, pos in entities if near([x-1, y, z-1, x+1, y+2, z+1], pos, 2)]
    if local:
        raise UserError('Retain existing residents/passengers/items in the source spawn neighborhood')
    water_neighbors = [(kind, pos) for kind, pos in entities if kind != 'minecraft:item' and near(box, pos, 8)] if kind == 'WATER' else []
    if water_neighbors:
        raise UserError('The first fish refuge needs an empty measured predator/occupancy neighborhood; do not remove existing creatures')
    counts = Counter(base(value) for value in field.values())
    flowers = sum(n for block, n in counts.items() if any(s in block for s in ('flower', 'daisy', 'lupine', 'aster', 'allium', 'poppy')))
    leaves = sum(n for block, n in counts.items() if block.endswith('_leaves'))
    if site['entity'] in ('crittersandcompanions:shima_enaga', 'crittersandcompanions:ladybug') and leaves < 3:
        raise UserError('Actual retained leaf/perch habitat is missing')
    return field, {'known_FULL_cells': len(field), 'actual_grass_soil_cells': sum(counts[k] for k in SOIL),
        'actual_flower_cells': flowers, 'actual_leaf_cells': leaves,
        'actual_source_water_cells': counts['minecraft:water'], 'existing_source_spawn_neighborhood': len(local),
        'native_collision_biome_light_time_spawn_rules_and_behavior': 'PENDING ordinary native STRUCTURE hooks/actual observation'}


def town_cat(snapshot, registry, entities, source, tree_columns, extra_sources=()):
    mask = {tuple(row[:3]) for row in source['blocks']}
    for additional in extra_sources:
        mask.update(tuple(row[:3]) for row in additional['blocks'])
    # The owner-approved old spit tavern is separate from rejected Rose Reach.
    standing = {p for p in mask if p[1] == 65 and (p[0],64,p[2]) in mask and (p[0],66,p[2]) in mask
        and base(snapshot.state(p)) in AIR and base(snapshot.state((p[0],66,p[2]))) in AIR
        and base(snapshot.state((p[0],64,p[2]))) not in AIR | SOFT | {'minecraft:water','minecraft:lava'}}
    candidates = sorted(standing, key=lambda p:(math.dist((p[0],p[2]),(1294,-1280)),p))[:64]
    refusals = []
    for x, y, z in candidates:
        routes = None
        for dx,dz in ((1,0),(-1,0),(0,1),(0,-1)):
            b=(x+dx,y,z+dz)
            if b not in standing:continue
            c=next(((b[0]+a,y,b[2]+c) for a,c in ((1,0),(-1,0),(0,1),(0,-1))
                if (b[0]+a,y,b[2]+c) in standing and (b[0]+a,y,b[2]+c)!=(x,y,z)),None)
            if c is not None:routes=[list((x,y,z)),list(b),list(c)];break
        if routes is None:
            continue
        roof = next(([xx,yy,zz] for yy in range(y+3,y+9) for xx in range(x-1,x+2) for zz in range(z-1,z+2)
            if (xx,yy,zz) in mask and any(word in base(snapshot.state((xx,yy,zz))) for word in ('_planks','_log','_slab','_stairs'))),None)
        if roof is None:
            continue
        box = [x-3, y-2, z-3, x+3, y+9, z+3]
        site = {'name': 'first-old-spit-sheltered-cat', 'entity': 'cozys-improved-cats:improved_cat',
            'feet': [x+.5, y, z+.5], 'roam_bounds': [x-6, y-2, z-6, x+7, y+8, z+7],
            'town_site': 'accepted-old-spit-sheltered-cat', 'habitat': {'kind': 'DRY', 'known_bounds': box,
                'roof': roof, 'shelter_path': routes}}
        try:
            field, facts = habitat_field(snapshot, site, entities, tree_columns, set(), town=True)
        except UserError as error:
            refusals.append({'feet': site['feet'], 'reason': str(error)}); continue
        occupancy = sorted(mask.intersection(field))
        route_standing = [r for r in routes if all(tuple((r[0], yy, r[2])) in mask for yy in (r[1]-1, r[1], r[1]+1))]
        return site, field, facts, {'id': site['town_site'], 'source_names': ['old-spit-tavern','old-spit-netmaker'],
            'species': [site['entity']], 'known_bounds': box, 'occupancy_cells': [list(p) for p in occupancy],
            'standing_positions': route_standing}, refusals
    raise UserError('No current accepted old-spit cat shelter with actual authored body/floor/roof and empty neighborhood')


def prepare(home, checkpoint_id, checkpoint_sha):
    home = Path(home).resolve()
    if home.parent != Path('D:/A World for Two/staging/world-tests').resolve():
        raise UserError('The first LIFE source belongs only to the owned artistic stage')
    reserve = guard(2*MIB, MAX_OUTPUT)
    current = read_json(home/'dashboard/settlement/backup-receipt.json', {})
    admit_owner(home, read_json(home/'dashboard/artistic-owner.json', {}), current, checkpoint_id, checkpoint_sha)
    registry = read_json(home/'dashboard/settlement/registry.json')
    api_facts=checked_source_apis(home)
    root = Path(__file__).resolve().parents[1]
    curation = checked(root/CURATION, CURATION_SHA, MIB)
    namespace_source = checked(home/NAMESPACE_SOURCE, NAMESPACE_SOURCE_SHA, 128*1024)
    old = checked(home/OLD_SITES, OLD_SITES_SHA, MIB)
    namespace = namespace_source['population_namespace']
    if old['population_namespace'] != namespace:
        raise UserError('Never create or combine a second LIFE population namespace')
    tree = checked(home/TREE_FIELDS, TREE_FIELDS_SHA, 4*MIB)
    tree_columns = set(map(tuple, tree['all_growth_excluded_columns_xz']))
    protected, custody, bank = protected_columns(home, registry)
    bank_nodes = set(map(tuple, bank['bank_nodes_xz']))
    profiles = {row['entity']: row for row in curation['species']}
    source = checked(home/TAVERN, TAVERN_SHA, 4*MIB)
    source_proof = checked(home/TAVERN_PROOF, TAVERN_PROOF_SHA, 512*1024)
    marker = Path(str(home/TAVERN_PROOF) + '.complete')
    if marker.read_text().strip() != TAVERN_PROOF_SHA or source_proof.get('operation') != 'verify' or source_proof.get('plan_sha256') != TAVERN_SHA or source_proof.get('failures') != 0 or source_proof.get('blocks') != len(source['blocks']):
        raise UserError('The accepted old-spit authored source needs its real exact native physical proof')
    net = checked(home/NET, NET_SHA, MIB)
    net_proof = checked(home/NET_PROOF, NET_PROOF_SHA, 512*1024)
    if Path(str(home/NET_PROOF)+'.complete').read_text().strip()!=NET_PROOF_SHA or net_proof.get('operation')!='verify' or net_proof.get('plan_sha256')!=NET_SHA or net_proof.get('blocks')!=len(net['blocks']) or net_proof.get('failures')!=0:
        raise UserError('Retain the exact accepted net-maker native physical proof')
    started = time.monotonic()
    snapshot = BackupWorld(home, current, registry)
    try:
        entities, entity_sources = entity_positions(snapshot)
        selected, fields, facts, held = [], {}, [], []
        for previous in old['sites']:
            if time.monotonic() - started > MAX_SECONDS:
                raise UserError('Finite first-cohort source reader expired')
            site = deepcopy(previous)
            if site['name'] in HELD_NAMES:
                held.append({'name': site['name'], 'entity': site['entity'], 'reason': 'Keep the first cohort outside active/future tree fields and their current roaming approaches'}); continue
            if site['entity'] not in registry['entities'] or tuple(site['bank_anchor']) not in bank_nodes:
                raise UserError('A real registered species and independently mapped south-bank anchor are required')
            try:
                field, proof = habitat_field(snapshot, site, entities, tree_columns, protected)
            except UserError as error:
                held.append({'name': site['name'], 'entity': site['entity'], 'reason': str(error)}); continue
            selected.append(site); fields.update(field); facts.append({'name': site['name'], 'entity': site['entity'], **proof})
        authority_sites = []
        try:
            cat, field, fact, authority, refusals = town_cat(snapshot, registry, entities, source, tree_columns, (net,))
            selected.append(cat); fields.update(field); facts.append({'name': cat['name'], 'entity': cat['entity'], **fact})
            authority_sites.append(authority)
            held.extend({'name': cat['name'], **row} for row in refusals)
        except UserError as error:
            held.append({'name': 'first-old-spit-sheltered-cat', 'entity': 'cozys-improved-cats:improved_cat', 'reason': str(error)})
        if not 8 <= len(selected) <= 12:
            raise UserError('The requested first cohort needs8..12 actual source sites; never pad it or silently report a smaller pilot complete')
        identities = [identity(namespace, site) for site in selected]
        raw_recipe_identity = hashlib.sha256(encoded(identities)).hexdigest()
        full_census = census(snapshot, identities, checkpoint_sha, raw_recipe_identity)
        if full_census['matching_requested_UUIDs']:
            raise UserError('Preserve any existing requested identity; never replace or silently migrate it')
        full_census['format']='awft-source-selection-uuid-census:1'
        full_census['planning_selection_sha256']=full_census.pop('recipe_sha256')
        full_census['native_recipe_not_built']=True
        caps = Counter(s['entity'] for s in selected)
        if sum(caps.values()) > 64 or any(caps[k] > profiles[k]['candidate_population_cap'] for k in caps):
            raise UserError('The one unchanged species/whole-cohort policy cap is exceeded')
        population=retained_population(snapshot,namespace,selected,profiles)
        # Actual native hive occupants are deliberately NOT inferred from the
        # absence of free-flying bee entity records. Post-growth audits remain.
        bee=actual_tree_bees(home,snapshot)
        bee.update(saved_free_flying_bee_records=sum(kind=='minecraft:bee' for kind,_ in entities),capacity_ready_for_seed=False)
        home_facts = {'bed': [[1296,65,-1250], [1296,65,-1249]], 'job': [1300,65,-1255],
            'actual_saved_states': [{'pos': p, 'state': snapshot.state(tuple(p))} for p in ([1296,65,-1250], [1296,65,-1249], [1300,65,-1255])],
            'assigned_resident_or_profession': False, 'free_native_HOME_job_tickets_and_routes': 'UNKNOWN; native inspection required',
            'authority': 'Real later progress inside rejected/rebuild territory; preserved, no automatic public HOME assignment'}
        sites = {'format': 'awft-life-sites:3', 'seed': registry['seed'], 'world_path': registry['world_path'],
            'population_namespace': namespace, 'sites': selected, 'source_only': True, 'native_spawn_acceptance': False}
        town = {'format': 'awft-town-life-authority:1', 'seed': registry['seed'], 'world_path': registry['world_path'],
            'source_checkpoint_sha256': source['backup_sha256'], 'sources': [{'name': 'old-spit-tavern', 'kind': 'AUTHORED_FULL_PLAN',
                'plan': {'path': TAVERN, 'bytes': (home/TAVERN).stat().st_size, 'sha256': TAVERN_SHA},
                'native_verify': {'path': TAVERN_PROOF, 'bytes': (home/TAVERN_PROOF).stat().st_size, 'sha256': TAVERN_PROOF_SHA}},
                {'name':'old-spit-netmaker','kind':'AUTHORED_FULL_PLAN',
                 'plan':{'path':NET,'bytes':(home/NET).stat().st_size,'sha256':NET_SHA},
                 'native_verify':{'path':NET_PROOF,'bytes':(home/NET_PROOF).stat().st_size,'sha256':NET_PROOF_SHA}}],
            'sites': authority_sites}
        documents = {'first-cohort-sites-REVIEW-ONLY.json': encoded(sites),
            'complete-habitat-field-VERIFY-ONLY.json': encoded(settlement_plan(registry, current, fields, 'VERIFY ONLY complete current first LIFE habitat fields')),
            'stopped-world-requested-UUID-census.json': encoded(full_census),
            'held-real-HOME-POI-facts.json': encoded(home_facts),
            'actual-eight-tree-bee-reconciliation.json':encoded(bee)}
        if authority_sites:
            documents['accepted-old-spit-town-authority.json'] = encoded(town)
        proof = {'format': 'awft-first-living-cohort-source:1', 'created': utcnow(), 'checkpoint_id': checkpoint_id,
            'checkpoint_sha256': checkpoint_sha, 'source_sha256': digest(Path(__file__)), 'population_namespace': namespace,
            'one_existing_v3_controller_only': True, 'curation_sha256': CURATION_SHA, 'namespace_source_sha256': NAMESPACE_SOURCE_SHA,
            'sites': len(selected), 'species_counts': dict(caps), 'source_facts': facts, 'held_or_rejected_source_candidates': held,
            'native_tree_bee_budget': bee, 'post_growth_rebinding_required': True, 'readiness_created': False,
            'retained_and_proposed_population_budget':population,
            'source_screen_native_API_provenance':api_facts,
            'normal_native_hooks': 'STRUCTURE, actual factory/AABB/medium/footing/SpawnPlacements/EventHooks/finalize; never fake/null actor or species aliases',
            'normal_AI_owner_profession_or_profile_writes': 0, 'native_actions': 0, 'world_or_ledger_writes': 0,
            'managed_cohort_cap': 64, 'full_world_saved_entity_records_inspected': full_census['saved_entity_records_inspected'],
            'saved_occupancy_scope': 'Six admitted overworld regions for positional screening; separate whole-world UUID census includes dimensions/passengers',
            'saved_entity_region_sources': entity_sources, 'current_native_FULL_fields_census_and_approval_required_before_seed': True,
            'actual_behavior_food_shelter_water_predator_roaming_and_art_acceptance': 'PENDING real native inspection and observation; no persistent artificial confinement',
            'tree_fields_sha256': TREE_FIELDS_SHA, 'safety_source_custody': custody, 'saved_block_sources': snapshot.sources,
            'reserve_guard': reserve, 'files': {name: {'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)} for name, raw in documents.items()}}
        documents['manifest.json'] = encoded(proof)
        if sum(map(len, documents.values())) > MAX_OUTPUT:
            raise UserError('First-cohort source output exceeds its finite budget')
        output = home/'staging'/('first-living-cohort-source-' + str(time.time_ns()))
        output.mkdir()
        for name, raw in documents.items():
            with (output/name).open('xb') as stream:
                stream.write(raw)
        return {'directory': str(output), 'manifest_sha256': digest(output/'manifest.json'),
            'sites': len(selected), 'species_counts': dict(caps), 'source_fields': len(fields),
            'saved_entities_inspected': full_census['saved_entity_records_inspected'], 'held': held,
            'native_actions': 0, 'spawn_readiness_created': False}
    finally:
        snapshot.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--home', type=Path, required=True)
    parser.add_argument('--checkpoint-id', required=True)
    parser.add_argument('--checkpoint-sha', required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.home, args.checkpoint_id, args.checkpoint_sha), indent=2))
