"""Bind the reviewed first eight habitats to the installed v3 LIFE controller.

Only private requests are written. Native inspection and a current full habitat
verification remain mandatory before the separately invoked seed binder.
"""
from __future__ import annotations

import argparse
from collections import Counter
import datetime as dt
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import time
import zipfile

from control_room.common import UserError, digest, read_json, utcnow
from tools.artistic_bridge_refinement import encoded
from tools.artistic_dense_canopies import entity_positions
from tools.artistic_first_life_cohort import (
    CURATION, CURATION_SHA, TREE_FIELDS, TREE_FIELDS_SHA, actual_tree_bees,
    habitat_field, identity, retained_population,
)
from tools.artistic_native_tree_pilot import BANK, BANK_MANIFEST_SHA, protected_columns
from tools.habitat_life import census
from tools.playtest import guard
from tools.settlement_attractions import BackupWorld

MIB = 1024**2
CHECKPOINT = '20261028T073257Z-31e541'
CHECKPOINT_SHA = 'da5ef61fbd1153509ac0b722228045285739667ccb82f6076caa9cd031a4deff'
COHORT = 'staging/first-living-cohort-source-1793174205972795300'
COHORT_SHA = 'b498b28c4b9ce6e0c84afcbf7c8076f1f47b8f9847ed2dd219ab73c7f3e3f699'
R5 = 'staging/artistic-fountain-centerpiece-r5-wet-reset-20261027T2255Z/forest-reservation-ONLY.json'
R5_SHA = 'c3914908a029ce58ee55124016933f8aa8a850b300da6c269076253b30a9ff3b'
RESOLUTION = 'staging/tree09-PARENT-REVIEW-RESOLVED-1793195120736011800/decision.json'
PROPOSAL = 'compat/control-bridge/proposals/life-extension/native44-town-authority'
EXTRA_SAFETY = (
    ('Current complete bascule, towers and admitted topside',
     'staging/bridge-moving106-ADMITTED47-1793168856089689000/complete-after-VERIFY-ONLY.json',
     'c58c1680b7d8330e6e5196de5d01af6f200b22082a6c0d5f5bb9aa2cb65b3868'),
    ('Rosebridge', 'staging/prototype-rosebridge-9c9b37cea97a69d9/prototype.json',
     '9c9b37cea97a69d9f510bfed83b70c072793ebc35fed175ce50b3355506a51f2'),
    ('Actual R5 sculpture, pool and machinery',
     'staging/artistic-fountain-r5-ACTUAL-DRY45-1793155163050141000/plaza.json',
     'ce85c167a6c3e831bdbb33996d17352c6902329858b4f65d8349ac222f1942be'),
    ('Original complete R5 routes and service envelope', R5, R5_SHA),
    ('Watermill machinery and working routes',
     'staging/artistic-engineering-r2-1793106029261770100/mill-quarter.json',
     '181e2191572846967c41e77bf5b406d0dddcc484488aa60d6725728ba651b199'),
    ('Complete western v2 flight, frames, stations and cliff approach',
     'staging/zipline-west-v2-source-1793152099836099800/future-v2-growth-and-construction-reservation.json',
     '72ad9665eb2e5b75d54cf3acee6ad4b012f7b82b62ab5547115bc7d1e69af9a0'),
)


def ordinary(home, path, cap=16*MIB):
    home = Path(home).resolve(); path = Path(path).absolute()
    if not path.is_relative_to(home): raise UserError('Reference must stay inside the owned stage')
    for part in (path, *path.parents):
        if part.is_symlink(): raise UserError('Linked reference ancestry is not authority')
        if part == home: break
    if not path.is_file() or not 0 < path.stat().st_size <= cap:
        raise UserError('Bounded ordinary reference required')
    return path


def ref(home, path, cap=16*MIB):
    path = ordinary(home, path, cap)
    return {'path': path.relative_to(Path(home).resolve()).as_posix(),
            'bytes': path.stat().st_size, 'sha256': digest(path)}


def checked(home, path, sha, cap=16*MIB):
    path = ordinary(home, path, cap)
    if digest(path) != sha: raise UserError('Immutable source digest differs')
    return read_json(path)


def v3():
    root = Path(__file__).resolve().parents[1] / PROPOSAL
    sys.path.insert(0, str(root))
    spec = importlib.util.spec_from_file_location('awft_retained_v3_prepare', root/'prepare.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def runtime(home):
    active = read_json(ordinary(home, home/'packwiz/active.json', 65536))
    installed = read_json(ordinary(home, home/'server/installed.json', MIB))
    candidate, bridge = '0.1.0-candidate.48', '0.6.34'
    pack = '0e5775d8d22771e97b34b5b9f508af7baf001e6371d80588315ef08261eeed0b'
    release = ordinary(home, home/'packwiz/releases'/candidate/'pack.toml', MIB)
    jar = ordinary(home, home/'server/mods'/('awft-control-bridge-'+bridge+'.jar'), MIB)
    if (active.get('version'), installed.get('pack_version'), active.get('pack_sha256'),
            installed.get('pack_sha256'), digest(release)) != (candidate, candidate, pack, pack, pack):
        raise UserError('Actual installed48 pack/release custody differs')
    if jar.stat().st_size != 584264 or digest(jar) != '071fe778b27c9450c6a9a7b602825ee2ff19bfcdba9f23ba3cb24302bd6b4b1d' or installed['files'].get(jar.name) != digest(jar):
        raise UserError('Actual installed48 LIFE helper differs')
    pins = {}
    with zipfile.ZipFile(jar) as archive:
        for key, name in (('native_class_sha256', 'NativeHabitatLifeSupport'),
                          ('native_policy_sha256', 'HabitatLifePolicy'),
                          ('native_town_authority_sha256', 'TownLifeAuthority')):
            member = 'worldfortwo/bridge/'+name+'.class'
            if not 0 < archive.getinfo(member).file_size <= 256*1024:
                raise UserError('Bounded actual native class required')
            pins[key] = hashlib.sha256(archive.read(member)).hexdigest()
    return {'candidate_version': candidate, 'bridge_version': bridge, 'pack_sha256': pack,
            'neoforge_version': '21.1.262', **pins}


def checkpoint(home):
    value = read_json(ordinary(home, home/'dashboard/settlement/backup-receipt.json', 8192))
    if (value.get('id'), value.get('sha256'), value.get('verified')) != (CHECKPOINT, CHECKPOINT_SHA, True):
        raise UserError('This reviewed first8 bundle requires the exact current31 checkpoint')
    if (home/'dashboard/settlement/tree-growth-quarantine.json').exists():
        raise UserError('Retain active quarantine; no LIFE request admission')
    decision = read_json(ordinary(home, home/RESOLUTION, 65536))
    if (decision.get('checkpoint', {}).get('sha256') != CHECKPOINT_SHA
            or decision.get('saved_full_field_cells_verified') != 29160
            or decision.get('world_BEs_entities_or_inventories_written') != 0
            or decision.get('failed_plot_retry_authority') is not False):
        raise UserError('The actual parent residual review decision is required')
    return value


def complete_receipt(home, path, maximum=512*1024):
    path = ordinary(home, path, maximum); sha = digest(path)
    marker = ordinary(home, Path(str(path)+'.complete'), 128)
    if marker.read_text().strip() != sha: raise UserError('Actual immutable native completion marker differs')
    return read_json(path), ref(home, path, maximum)


def clean_native(value):
    if (value.get('failures') != 0 or value.get('error') or value.get('cleanup_required') is not False
            or value.get('temporary_tickets_remaining') != 0
            or value.get('pending_shared_chunk_futures', value.get('pending_shared_futures')) != 0
            or value.get('ticket_cleanup_error') or value.get('cleanup_errors', [])):
        raise UserError('Actual complete native cleanup and zero failures are required')
    done = dt.datetime.fromisoformat(value['finished']); now = dt.datetime.now(dt.timezone.utc)
    if done.tzinfo is None or not now-dt.timedelta(minutes=30) <= done <= now:
        raise UserError('Fresh actual native proof required')


def validate_seed_proofs(verify, inspection, inspect_request, recipe_sha, habitat_sha, members):
    clean_native(verify); clean_native(inspection)
    if (verify.get('operation') != 'verify' or verify.get('plan_sha256') != habitat_sha
            or verify.get('blocks') != 3242
            or verify.get('status') != 'verified actual block identities, orientation, block entities and supplied inventories'):
        raise UserError('Exact actual complete3242 habitat verification required')
    if (inspection.get('operation') != 'inspect' or inspection.get('request_sha256') != inspect_request
            or inspection.get('recipe_sha256') != recipe_sha or inspection.get('members') != 8
            or inspection.get('status') != 'native habitats inspected; no resident or ledger writes'
            or inspection.get('cleanup_passed') is not True
            or inspection.get('spawned') != 0 or inspection.get('intents_written') != 0
            or inspection.get('population_authorities_written') != 0
            or inspection.get('world_or_ledger_write_attempted') is not False
            or inspection.get('entity_add_attempted') is not False
            or inspection.get('NoAI_or_ownership_writes') != 0):
        raise UserError('Exact marked successful native first8 inspection required before seed')
    observed = inspection.get('observations', [])
    expected = {(r['uuid'], r['entity'], r['native_class']) for r in members}
    actual = {(r.get('uuid'), r.get('type'), r.get('native_class')) for r in observed}
    if len(observed) != 8 or actual != expected or any(r.get('new_habitat_currently_admissible') is not True or r.get('spawned') is not False for r in observed):
        raise UserError('All eight real native habitat observations are required')


def write_output(home, output, documents, manifest):
    output = Path(output).absolute()
    if output.parent != home/'staging' or output.exists() or output.parent.is_symlink():
        raise UserError('A new immediate private staging folder is required')
    raw = {name: encoded(value) for name, value in documents.items()}
    manifest['files'] = {n: {'bytes':len(b), 'sha256':hashlib.sha256(b).hexdigest()} for n,b in raw.items()}
    raw['manifest.json'] = encoded(manifest)
    if sum(map(len,raw.values())) > 16*MIB: raise UserError('Finite private LIFE output exceeded')
    output.mkdir(exist_ok=False)
    for name, data in raw.items():
        path = output/name; path.parent.mkdir(exist_ok=True, parents=True); path.write_bytes(data)
    return {'output':str(output), 'manifest_sha256':digest(output/'manifest.json'), **{k:manifest[k] for k in ('bundle','request_sha256','command_after_parent_review')}}


def prepare(home, output):
    home = Path(home).resolve(); output = Path(output).absolute()
    if home.parent != Path('D:/A World for Two/staging/world-tests').resolve(): raise UserError('Owned private artistic stage required')
    reserve = guard(4*MIB,16*MIB); current = checkpoint(home); pins = runtime(home)
    registry = read_json(home/'dashboard/settlement/registry.json'); root=Path(__file__).resolve().parents[1]
    cohort = checked(home, home/COHORT/'manifest.json', COHORT_SHA, MIB)
    for name, info in cohort['files'].items():
        if ref(home, home/COHORT/name) != {'path':str(Path(COHORT)/name).replace('\\','/'), **info}:
            raise UserError('Exact frozen first8 source files required')
    sites = read_json(home/COHORT/'first-cohort-sites-REVIEW-ONLY.json')
    if len(sites['sites']) != 8 or sites['population_namespace'] != '2d5e0218-c2f7-49c3-b9cd-a90a6a673a69':
        raise UserError('Retain exactly the original eight identities and one namespace')
    data = read_json(root/CURATION)
    if digest(root/CURATION) != CURATION_SHA: raise UserError('Reviewed native species curation differs')
    source = v3(); protected, protection_custody, bank = protected_columns(home, registry)
    safety_sources=[]
    for name, path, sha in EXTRA_SAFETY:
        checked(home,home/path,sha); safety_sources.append({'name':name,**ref(home,home/path)})
    safety={'format':'awft-life-safety-index:1','seed':registry['seed'],'world_path':registry['world_path'],
        'includes_current_motion_navigation_and_future_cable':True,'sources':safety_sources,
        'scope':'Actual complete mechanical/navigation footprints plus unchanged full R5/v2 route reservations; no world changes or terrain AIR claims'}
    # The native and frozen v3 producer apply these same protection semantics.
    # Save the new index only after full independent review below; an in-memory
    # equivalent computes the exact same protected columns without a side file.
    native_protected=set()
    def add(x,z,n): native_protected.update((x+dx,z+dz) for dx in range(-n,n+1) for dz in range(-n,n+1))
    r5=checked(home,home/R5,R5_SHA)
    r5xyz=sorted({tuple(r[:3]) for r in r5['blocks']})
    if hashlib.sha256(json.dumps(r5xyz,separators=(',',':')).encode()).hexdigest()!=source.R5_COORDS:
        raise UserError('Retain the complete independently pinned R5 coordinate reservation')
    for x,y,z in r5xyz:add(x,z,5)
    for entry in safety_sources:
        doc=read_json(home/entry['path'])
        if doc['format']=='awft-prospective-growth-exclusion:1':
            if doc.get('whole_crown_extra_skirt_metres',0)<5:raise UserError('Whole future cable crown skirt required')
            for x,z in doc['all_growth_excluded_columns_xz']:add(x,z,0)
        else:
            for x,y,z,*_ in doc['blocks']:add(x,z,5)
            for row in doc.get('block_entities',[]):add(row['pos'][0],row['pos'][2],5)
    if len(native_protected)>200000:raise UserError('Native protection table bound exceeded')
    town_path=home/COHORT/'accepted-old-spit-town-authority.json'
    town_doc,towns=source.town.read_authority(home,registry,town_path,source.bounded,lambda h,p:ref(h,p),source.KINDS)
    snapshot=BackupWorld(home,current,registry); review=[]; started=time.monotonic()
    try:
        entities,_=entity_positions(snapshot); tree=checked(home,home/TREE_FIELDS,TREE_FIELDS_SHA,4*MIB)
        tree_columns=set(map(tuple,tree['all_growth_excluded_columns_xz'])); field={}
        for site in sites['sites']:
            if time.monotonic()-started>120:raise UserError('Bounded independent eight-habitat review expired')
            cells,fact=habitat_field(snapshot,site,entities,tree_columns,protected,town='town_site'in site)
            field.update(cells); review.append({'site':site['name'],**fact})
        namespace,members=source.members(sites,data,registry,bank,snapshot,native_protected,towns)
        original=read_json(home/COHORT/'complete-habitat-field-VERIFY-ONLY.json')
        expected={tuple(r[:3]):original['palette'][r[3]] for r in original['blocks']}
        if field!=expected or len(field)!=3242:raise UserError('Preserve all3242 exact saved habitat source cells')
        profiles={r['entity']:r for r in data['species']}
        population=retained_population(snapshot,namespace,sites['sites'],profiles)
        bee=actual_tree_bees(home,snapshot)
        if bee['tree_quarantine_present'] or bee['actual_new_stored_bee_slots'] or bee['actual_new_nests']:
            raise UserError('Current reviewed tree/bee/recovery authority is not ready')
        recipe={'format':'awft-habitat-life-recipe:3','seed':registry['seed'],'world_path':registry['world_path'],
            'dimension':'minecraft:overworld','population_namespace':namespace,'members':members,
            'copied_entity_NBT':False,'curation_sha256':CURATION_SHA,
            'source_woodland_proposal_sha256':hashlib.sha256(encoded(bank)).hexdigest(),
            'r5_reservation_sha256':R5_SHA,'safety_index_sha256':hashlib.sha256(encoded(safety)).hexdigest(),
            'town_authority_sha256':digest(town_path),'town_authority_source_checkpoint_sha256':town_doc['source_checkpoint_sha256']}
        bank_manifest=checked(home,home/BANK/'manifest.json',BANK_MANIFEST_SHA,MIB)
        bank_path=home/BANK/'composition.json'
        if digest(bank_path)!=bank_manifest['proposal_sha256']:raise UserError('Exact actual bank component authority required')
        recipe['source_woodland_proposal_sha256']=digest(bank_path)
        recipe_sha=hashlib.sha256(encoded(recipe)).hexdigest()
        census_doc=census(snapshot,members,CHECKPOINT_SHA,recipe_sha)
        if not census_doc['all_requested_UUID_absent']:raise UserError('An existing requested UUID is not replacement authority')
        saved_sources=snapshot.sources.copy()
    finally:snapshot.close()
    def newref(name,value):return {'path':(output/name).relative_to(home).as_posix(),'bytes':len(encoded(value)),'sha256':hashlib.sha256(encoded(value)).hexdigest()}
    readiness={'format':'awft-life-bare-habitat-readiness:1','checkpoint_sha256':CHECKPOINT_SHA,
        'reviewer':'castle_detail acting under Root explicit delegated BARE8-HABITATS-ONLY review',
        'reviewed_at':utcnow(),'approved_recipe_sha256s':[recipe_sha],
        'scope':'Only the exact eight saved known habitat fields and their typed shelter/shore routes; no unfinished construction or mechanism within these individual fields',
        'construction_complete':True,'functional_commissioning_complete':True,
        'visual_corrections_reviewed':True,'habitat_plan_reviewed':True,
        'flags_apply_only_to_exact_bare_habitat_fields':True,'whole_town_or_forest_complete':False,
        'owner_art_approval_claimed':False,'native_canopy_or_spawn_or_behavior_acceptance':False,
        'actual_native_inspection_and_FULL_preimage_still_required':True}
    request={'format':'awft-native-habitat-life:3','allowed_operation':'inspect',**pins,
        'checkpoint_sha256':CHECKPOINT_SHA,'current_backup':ref(home,home/'dashboard/settlement/backup-receipt.json'),
        'recipe':newref('recipe.json',recipe),'uuid_census':newref('uuid-census.json',census_doc),
        'source_woodland_proposal_sha256':recipe['source_woodland_proposal_sha256'],'woodland':ref(home,bank_path),
        'r5_reservation':ref(home,home/R5),'safety_index':newref('safety-index.json',safety),
        'town_authority':ref(home,town_path)}
    request_sha=hashlib.sha256(encoded(request)).hexdigest(); bundle='life-'+request_sha[:16]
    documents={'recipe.json':recipe,'uuid-census.json':census_doc,'habitat-VERIFY-ONLY.json':original,
        'safety-index.json':safety,'BARE8-only-readiness.json':readiness,bundle+'/request.json':request,
        'independent-saved-review.json':{'checkpoint_sha256':CHECKPOINT_SHA,'source_manifest_sha256':COHORT_SHA,
            'sites':review,'saved_sources':saved_sources,'full_known_cells':len(field),
            'retained_population':population,'eight_tree_native_bee_reconciliation':bee,
            'parent_tree09_resolution':ref(home,home/RESOLUTION),'native_protected_columns':len(native_protected),
            'no_native_actions_or_ledger_writes':True}}
    return write_output(home,output,documents,{'format':'awft-first8-life48-inspection-preparation:1',
        'created':utcnow(),'source_sha256':digest(Path(__file__)),'checkpoint_id':CHECKPOINT,
        'checkpoint_sha256':CHECKPOINT_SHA,'recipe_sha256':recipe_sha,'request_sha256':request_sha,'bundle':bundle,
        'operation':'inspect','members':8,'habitat_cells':3242,'native_actions':0,'installed':False,
        'seed_request_created':False,'current_runtime':pins,'reserve_guard':reserve,
        'command_after_parent_review':f'awftlife inspect {bundle} {request_sha}'})


def seed(home, prepared, output, native_verify, native_inspect):
    home=Path(home).resolve(); prepared=Path(prepared).resolve(); output=Path(output).absolute()
    reserve=guard(MIB,4*MIB);checkpoint(home);pins=runtime(home)
    manifest=read_json(ordinary(home,prepared/'manifest.json',MIB))
    if manifest.get('format')!='awft-first8-life48-inspection-preparation:1':raise UserError('Exact reviewed first8 preparation required')
    for name,info in manifest['files'].items():
        actual=ref(home,prepared/name)
        if actual['sha256']!=info['sha256'] or actual['bytes']!=info['bytes']:raise UserError('Prepared inspection inputs changed')
    old=read_json(prepared/manifest['bundle']/'request.json');recipe=read_json(prepared/'recipe.json')
    if any(old.get(k)!=v for k,v in pins.items()):raise UserError('Retain actual same48 controller and pack')
    verify,verify_ref=complete_receipt(home,native_verify)
    inspection,inspect_ref=complete_receipt(home,native_inspect)
    habitat=ref(home,prepared/'habitat-VERIFY-ONLY.json')
    validate_seed_proofs(verify,inspection,manifest['request_sha256'],manifest['recipe_sha256'],habitat['sha256'],recipe['members'])
    request={**old,'allowed_operation':'seed','life_ready':ref(home,prepared/'BARE8-only-readiness.json'),
        'native_habitat_verify':verify_ref,'habitat_plan':habitat,'habitat_plan_sha256':habitat['sha256']}
    sha=hashlib.sha256(encoded(request)).hexdigest();bundle='life-'+sha[:16]
    return write_output(home,output,{bundle+'/request.json':request,'genuine-native-seed-gates.json':{
        'habitat_verify':verify_ref,'native_inspect':inspect_ref,'native_actions_by_producer':0}},
        {'format':'awft-first8-life48-seed-preparation:1','created':utcnow(),'source_sha256':digest(Path(__file__)),
         'operation':'seed','checkpoint_sha256':CHECKPOINT_SHA,'recipe_sha256':manifest['recipe_sha256'],
         'bundle':bundle,'request_sha256':sha,'members':8,'native_actions':0,'installed':False,'reserve_guard':reserve,
         'command_after_parent_review':f'awftlife seed {bundle} {sha}'})


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation',choices=('inspect','seed'));parser.add_argument('--home',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    for name in ('prepared','native-verify','native-inspect'):parser.add_argument('--'+name,type=Path)
    args=parser.parse_args()
    if args.operation=='inspect':result=prepare(args.home,args.output)
    else:
        if not all((args.prepared,args.native_verify,args.native_inspect)):parser.error('seed needs prepared and both genuine native proofs')
        result=seed(args.home,args.prepared,args.output,args.native_verify,args.native_inspect)
    print(json.dumps(result,indent=2))
