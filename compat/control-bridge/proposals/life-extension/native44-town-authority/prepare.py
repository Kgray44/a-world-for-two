"""Prepare private v2 habitat inspection/seed inputs from an immutable FULL save.

Never installs a request or invokes Minecraft. Sites are individually reviewed
world positions, not the 64 symbolic slots and not a rectangular forest fill.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import math
import sys
import uuid
from pathlib import Path

REPO = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(REPO))
from control_room.common import UserError, digest, read_json
from tools.artistic_bridge_refinement import encoded
from tools.habitat_life import census
from tools.playtest import guard
from tools.settlement_attractions import BackupWorld, base
sys.path.insert(0,str(Path(__file__).resolve().parent))
import town_authority as town

MIB = 1024**2
CURATION = 'be41097fb361a62fb5b60cc93d33958a8a896048dbacdca72e6c87de8abe74d9'
R5_COORDS = 'e376a4e7c40fd51e26c7b983d05599d8e688bd27c3532d8c130bfdf4bdb41491'
KINDS = {'naturalist:deer':'DRY', 'naturalist:bird':'AIR', 'naturalist:butterfly':'AIR', 'naturalist:firefly':'AIR',
         'naturalist:duck':'SHORE', 'crittersandcompanions:shima_enaga':'AIR', 'crittersandcompanions:ladybug':'AIR',
         'crittersandcompanions:dragonfly':'AIR', 'crittersandcompanions:koi_fish':'WATER', 'fishofthieves:pondie':'WATER',
         'cozys-improved-cats:improved_cat':'DRY', 'doggytalents:dog':'DRY', 'minecraft:villager':'HOME',
         'ribbits:ribbit':'MUSIC', 'minecraft:allay':'AIR'}


def bounded(path, maximum):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or not 0 < path.stat().st_size <= maximum:
        raise UserError('Bounded ordinary owned proposal input required')
    return read_json(path)


def owned(home, path):
    path = Path(path).resolve()
    if not path.is_relative_to(home.resolve()) or not path.is_file() or path.is_symlink():
        raise UserError('All native references must remain inside this owned private stage')
    return {'path':path.relative_to(home.resolve()).as_posix(), 'bytes':path.stat().st_size, 'sha256':digest(path)}


def box(bounds):
    if len(bounds) != 6 or any(type(v) is not int for v in bounds) or any(bounds[i] > bounds[i+3] for i in range(3)):
        raise UserError('Six literal finite habitat bounds required')
    volume = (bounds[3]-bounds[0]+1)*(bounds[4]-bounds[1]+1)*(bounds[5]-bounds[2]+1)
    if not 125 <= volume <= 4096 or bounds[0] < 904 or bounds[3] > 1360 or bounds[2] < -1208 or bounds[5] > -608 or bounds[1] < -64 or bounds[4] > 319:
        raise UserError('Complete finite native44 FULL habitat volume required; dry45 cannot substitute')
    if any(bounds[i+3]-bounds[i]+1 < 5 for i in range(3)):
        raise UserError('Native44 requires five-block minimum known dimensions')
    return volume


def inside(bounds, pos):
    return all(bounds[i] <= pos[i] <= bounds[i+3] for i in range(3))


def points(bounds):
    for x in range(bounds[0],bounds[3]+1):
        for z in range(bounds[2],bounds[5]+1):
            for y in range(bounds[1],bounds[4]+1):
                yield x,y,z


def protection(home, registry, r5_path, safety_path):
    r5 = bounded(r5_path,8*MIB); safety = bounded(safety_path,2*MIB)
    if any(str(r5.get(k)) != str(registry[k]) or str(safety.get(k)) != str(registry[k]) for k in ('seed','world_path')):
        raise UserError('Exact current world protection required')
    xyz = sorted({tuple(row[:3]) for row in r5['blocks']})
    if hashlib.sha256(json.dumps(xyz,separators=(',',':')).encode()).hexdigest() != R5_COORDS:
        raise UserError('Complete independently frozen R5 reservation changed; do not trim it')
    columns = set()
    def add(x,z,margin):
        columns.update((x+dx,z+dz) for dx in range(-margin,margin+1) for dz in range(-margin,margin+1))
        if len(columns) > 200000: raise UserError('Finite reviewed protection required')
    for x,y,z in xyz: add(x,z,5)
    if safety.get('format') != 'awft-life-safety-index:1' or safety.get('includes_current_motion_navigation_and_future_cable') is not True:
        raise UserError('Explicit complete navigation/motion/future-cable safety index required')
    sources = safety.get('sources',[])
    if not 1 <= len(sources) <= 32: raise UserError('Finite native protection source references required')
    cable = False
    for ref in sources:
        path = home/ref['path']; actual = owned(home,path)
        if actual != {k:ref[k] for k in ('path','bytes','sha256')}: raise UserError('Exact safety source bytes changed')
        doc = bounded(path,16*MIB)
        if doc.get('format') == 'awft-prospective-growth-exclusion:1':
            if doc.get('whole_crown_extra_skirt_metres',0) < 5: raise UserError('Retain complete future-cable skirt')
            for x,z in doc['all_growth_excluded_columns_xz']: add(x,z,0)
            cable = True
        elif doc.get('format') == 'awft-native-settlement:1':
            if any(str(doc.get(k)) != str(registry[k]) for k in ('seed','world_path')): raise UserError('Foreign mechanism exclusion')
            for x,y,z,*tail in doc['blocks']: add(x,z,5)
            for row in doc.get('block_entities',[]): add(row['pos'][0],row['pos'][2],5)
        else: raise UserError('Unknown exclusion format; X/Z reservations are not invented AIR blocks')
    if not cable: raise UserError('Future cable/station reservation must be explicit')
    return columns


def members(sites, data, registry, bank, snapshot, protected, towns=None):
    if sites.get('format') != 'awft-life-sites:3' or any(str(sites.get(k)) != str(registry[k]) for k in ('seed','world_path')):
        raise UserError('Exact individually reviewed sites for this world required')
    namespace = uuid.UUID(sites['population_namespace']); profiles = {r['entity']:r for r in data['species']}
    nodes = {tuple(p) for p in bank['bank_nodes_xz']}; result = []; names = set(); total = 0
    if not 1 <= len(sites['sites']) <= 16: raise UserError('One explicitly reviewed batch contains1..16 individual sites')
    for site in sites['sites']:
        is_town='town_site' in site
        if is_town==('bank_anchor' in site):raise UserError('Exactly one typed town or woodland authority required')
        if set(site) != {'name','entity','feet','roam_bounds','habitat',('town_site' if is_town else 'bank_anchor')}:
            raise UserError('No owner/NoAI/profession/NBT/native-success fields accepted')
        name, key, feet, habitat = (site[k] for k in ('name','entity','feet','habitat'))
        if not isinstance(name,str) or name in names or not 1 <= len(name) <= 64 or key not in KINDS:
            raise UserError('Distinct stable individual identity from the15 enabled species required')
        names.add(name); profile = profiles[key]
        if habitat.get('kind') != KINDS[key]: raise UserError('Exact native habitat kind required')
        allowed = {'kind','known_bounds'}
        if KINDS[key] in ('WATER','SHORE'): allowed.add('water_bounds')
        if KINDS[key] == 'SHORE': allowed.add('shore_path')
        if KINDS[key] == 'HOME': allowed.update(('bed','job','roof','bed_path','job_path'))
        if KINDS[key] == 'MUSIC' or key in ('doggytalents:dog','cozys-improved-cats:improved_cat'): allowed.update(('roof','shelter_path'))
        if set(habitat) != allowed: raise UserError('No forged traits or extra habitat authority accepted')
        bounds = habitat['known_bounds']; count = town.town_box(bounds) if is_town else box(bounds); total += count
        if total > 32768 or len(feet) != 3 or not all(isinstance(v,(int,float)) and not isinstance(v,bool) for v in feet) or not inside(bounds,feet):
            raise UserError('Finite literal habitat/body preimage required')
        if not all(math.isfinite(v) for v in feet) or not 48<=feet[1]<=240:raise UserError('Finite native habitat coordinate required')
        if is_town:
            if abs(feet[0])>30000000 or abs(feet[2])>30000000:raise UserError('Finite native town coordinate required')
        elif not 912<=math.floor(feet[0])<=1352 or not -1200<=math.floor(feet[2])<=-616:raise UserError('Outside actual woodland study')
        source=town.member(towns or {},site,feet,bounds) if is_town else None
        anchor=None
        if not is_town:
            anchor=tuple(site['bank_anchor'])
            if anchor not in nodes or abs(anchor[0]-feet[0])>16 or abs(anchor[1]-feet[2])>16:raise UserError('Actual connected-bank anchor required; rectangle is not authority')
            snapshot.chunk(anchor[0]//16,anchor[1]//16)
        preimage = []
        for pos in points(bounds):
            state = snapshot.state(pos)
            if state is None: raise UserError('Unknown saved habitat cell cannot be AIR')
            preimage.append([*pos,state])
        occupied = {(math.floor(feet[0])+dx,math.floor(feet[2])+dz) for dx in (-1,0,1) for dz in (-1,0,1)}
        if 'water_bounds' in habitat:
            water = habitat['water_bounds']
            if len(water) != 6 or any(type(v) is not int for v in water) or any(water[i] > water[i+3] for i in range(3)) or not inside(bounds,water[:3]) or not inside(bounds,water[3:]):
                raise UserError('Literal proved swimming volume required')
            span = 5 if KINDS[key] == 'WATER' else 3
            if water[3]-water[0]+1 < span or water[5]-water[2]+1 < span or water[4]-water[1]+1 < 2 or not inside(bounds,[water[0]-1,water[1],water[2]-1]) or not inside(bounds,[water[3]+1,water[4]+1,water[5]+1]):
                raise UserError('Complete swimming and real surface/refuge perimeter required; dry45 cannot admit fish')
            for pos in points(water):
                if snapshot.state(pos) != 'minecraft:water[level=0]':
                    raise UserError('Conservative saved preflight requires literal source water, not a heightmap depth or waterlogged block')
                if source is not None:town.cell(source,pos)
                occupied.add((pos[0],pos[2]))
        for route_key in ('shore_path','bed_path','job_path','shelter_path'):
            if route_key in habitat and not 1 <= len(habitat[route_key]) <= 64: raise UserError('Bounded explicit actual route required')
            for pos in habitat.get(route_key,[]):
                if len(pos) != 3 or any(type(v) is not int for v in pos) or not inside(bounds,pos): raise UserError('Actual full-field route required')
                if source is not None:town.route(source,pos)
                occupied.update((pos[0]+dx,pos[2]+dz) for dx in (-1,0,1) for dz in (-1,0,1))
        for keypoint in ('roof','bed','job'):
            if keypoint in habitat:
                pos=habitat[keypoint]
                if len(pos) != 3 or any(type(v) is not int for v in pos) or not inside(bounds,[v-1 for v in pos]) or not inside(bounds,[v+1 for v in pos]): raise UserError('Complete literal shelter/POI witness required')
                if source is not None:town.cell(source,pos)
        if occupied & protected: raise UserError('Retain R5/plumbing/views, machine/navigation and future cable protection')
        identity = str(uuid.uuid5(namespace,'awft-life:'+name+':'+key)); tag = 'awft_life_'+hashlib.sha256((str(namespace)+':'+name+':'+key).encode()).hexdigest()[:24]
        result.append({'uuid':identity,'entity':key,'native_class':profile['native_class'],'native_MobCategory':profile['native_category'],
                       'member_tag':tag,'feet':feet,'roam_bounds':site['roam_bounds'],'source_group_id':name,'preimage':preimage,
                       'habitat':habitat,**({'town_site':site['town_site']} if is_town else {'bank_anchor':list(anchor)})})
    if len({tuple(row['feet']) for row in result}) != len(result): raise UserError('Actual individual body positions must differ')
    return str(namespace), result


def _prepare(home, output, native_classes, candidate, bridge, woodland, r5_mask, safety_index, sites=None,
            retained_recipe=None, operation='inspect', life_ready=None, native_verify=None, town_authority=None):
    home,output = Path(home).resolve(),Path(output).resolve()
    if home.parent != Path('D:/A World for Two/staging/world-tests').resolve() or output.exists() or not output.is_relative_to(home/'staging'):
        raise UserError('New owned private-stage output required')
    if operation not in ('inspect','seed') or operation == 'seed' and (not life_ready or not native_verify):
        raise UserError('Explicit inspect or fully evidenced seed operation required')
    reserve = guard(2*MIB,32*MIB); registry = bounded(home/'dashboard/settlement/registry.json',8*MIB)
    if Path(registry['world_path']).resolve() != home/'world/RosewaterArtistic': raise UserError('Exact private artistic save required')
    checkpoint = bounded(home/'dashboard/settlement/backup-receipt.json',4096)
    if checkpoint.get('verified') is not True: raise UserError('Verified stopped checkpoint required')
    curation_path = Path(__file__).resolve().parent.parent/'species-habitats.json'
    if digest(curation_path) != CURATION: raise UserError('Frozen16-profile curation changed')
    data = bounded(curation_path,256*1024); bank = bounded(woodland,4*MIB)
    protected = protection(home,registry,r5_mask,safety_index)
    town_doc,towns=town.read_authority(home,registry,town_authority,bounded,owned,KINDS)
    snapshot = BackupWorld(home,checkpoint,registry)
    try:
        if retained_recipe:
            recipe = bounded(retained_recipe,8*MIB)
            if recipe.get('format') != 'awft-habitat-life-recipe:3': raise UserError('Retain exact v2 recipe; v1 cannot silently upgrade')
            for row in recipe['members']:
                if row['entity'] not in KINDS: raise UserError('Unreviewed retained species')
                for x,y,z,state in row['preimage']:
                    if snapshot.state((x,y,z))!=state:raise UserError('Current stopped FULL habitat differs; preserve original resident/intent, no silent recipe replacement')
        else:
            if sites is None: raise UserError('Individually reviewed current sites required')
            namespace,residents = members(bounded(sites,256*1024),data,registry,bank,snapshot,protected,towns)
            recipe = {'format':'awft-habitat-life-recipe:3','seed':registry['seed'],'world_path':registry['world_path'],'dimension':'minecraft:overworld',
                      'population_namespace':namespace,'members':residents,'copied_entity_NBT':False,'curation_sha256':CURATION,
                      'source_woodland_proposal_sha256':digest(Path(woodland)),'r5_reservation_sha256':digest(Path(r5_mask)),'safety_index_sha256':digest(Path(safety_index))}
        if any('town_site' in row for row in recipe['members']):
            if town_doc is None:raise UserError('Actual typed authored-town authority required')
            authority_sha=digest(Path(town_authority))
            if retained_recipe and (recipe.get('town_authority_sha256')!=authority_sha or recipe.get('town_authority_source_checkpoint_sha256')!=town_doc['source_checkpoint_sha256']):raise UserError('Retained town authority must remain byte-identical for durable identity')
            recipe.update(town_authority_sha256=authority_sha,town_authority_source_checkpoint_sha256=town_doc['source_checkpoint_sha256'])
        raw_recipe = encoded(recipe); recipe_sha = hashlib.sha256(raw_recipe).hexdigest()
        census_doc = census(snapshot,recipe['members'],recipe['population_namespace'],recipe_sha)
        saved_sources = snapshot.sources
    finally: snapshot.close()
    field = {}
    for row in recipe['members']:
        for x,y,z,state in row['preimage']:
            if (x,y,z) in field and field[x,y,z] != state: raise UserError('Conflicting habitat witnesses')
            field[x,y,z] = state
    palette = sorted(set(field.values())); indices = {s:n for n,s in enumerate(palette)}
    native_plan = {'format':'awft-native-settlement:1','name':'VERIFY ONLY exact native44 habitat fields','seed':registry['seed'],'world_path':registry['world_path'],
                   'backup_sha256':checkpoint['sha256'],'palette':palette,'blocks':[[*p,indices[s]] for p,s in sorted(field.items())],
                   'block_entities':[],'commands':[],'landmarks':[],'construction_forbidden':True,'verification_only':True}
    docs = {'recipe.json':raw_recipe,'uuid-census.json':encoded(census_doc),'habitat-VERIFY-ONLY.json':encoded(native_plan)}
    def newref(name): return {'path':(output/name).relative_to(home).as_posix(),'bytes':len(docs[name]),'sha256':hashlib.sha256(docs[name]).hexdigest()}
    classes = Path(native_classes)/'worldfortwo/bridge'
    for filename in ('NativeHabitatLifeSupport.class','HabitatLifePolicy.class','TownLifeAuthority.class'):
        path=classes/filename
        if path.is_symlink() or not path.is_file() or not 0 < path.stat().st_size <= 256*1024: raise UserError('Bounded actual final-candidate compiled LIFE classes required')
    request = {'format':'awft-native-habitat-life:3','allowed_operation':operation,'candidate_version':candidate,'bridge_version':bridge,'neoforge_version':'21.1.262',
               'native_class_sha256':digest(classes/'NativeHabitatLifeSupport.class'),'native_policy_sha256':digest(classes/'HabitatLifePolicy.class'),'native_town_authority_sha256':digest(classes/'TownLifeAuthority.class'),
               'checkpoint_sha256':checkpoint['sha256'],'current_backup':owned(home,home/'dashboard/settlement/backup-receipt.json'),
               'pack_sha256':bounded(home/'packwiz/active.json',65536)['pack_sha256'],'recipe':newref('recipe.json'),'uuid_census':newref('uuid-census.json'),
               'source_woodland_proposal_sha256':recipe['source_woodland_proposal_sha256'],'woodland':owned(home,woodland),
               'r5_reservation':owned(home,r5_mask),'safety_index':owned(home,safety_index)}
    if 'town_authority_sha256' in recipe:request['town_authority']=owned(home,town_authority)
    if operation == 'seed':
        if not life_ready or not native_verify: raise UserError('Actual completed construction/habitat approval and native verification required')
        ready = bounded(life_ready,128*1024); verify = bounded(native_verify,512*1024)
        if ready.get('checkpoint_sha256') != checkpoint['sha256'] or recipe_sha not in ready.get('approved_recipe_sha256s',[]) or any(ready.get(k) is not True for k in ('construction_complete','functional_commissioning_complete','visual_corrections_reviewed','habitat_plan_reviewed')):
            raise UserError('Exact current completed construction/art/habitat approval required')
        if verify.get('operation') != 'verify' or verify.get('failures') != 0 or verify.get('plan_sha256') != newref('habitat-VERIFY-ONLY.json')['sha256'] or verify.get('error') or verify.get('temporary_tickets_remaining',0) != 0:
            raise UserError('Exact actual successful habitat verification required')
        complete=Path(native_verify).with_name(Path(native_verify).name+'.complete')
        if not complete.is_file() or complete.stat().st_size > 128 or complete.read_text().strip() != digest(Path(native_verify)):
            raise UserError('Immutable actual native completion digest required')
        if verify.get('status') != 'verified actual block identities, orientation, block entities and supplied inventories' or verify.get('blocks') != len(field) or verify.get('cleanup_passed',True) is not True or verify.get('cleanup_required',False) or verify.get('pending_shared_chunk_futures',0):
            raise UserError('Exact full-plan verification and actual cleanup required')
        done=datetime.datetime.fromisoformat(verify['finished']);now=datetime.datetime.now(datetime.timezone.utc)
        if done.tzinfo is None or not now-datetime.timedelta(minutes=30) <= done <= now: raise UserError('Fresh actual native verification required')
        request.update(life_ready=owned(home,life_ready),native_habitat_verify=owned(home,native_verify),habitat_plan=newref('habitat-VERIFY-ONLY.json'),habitat_plan_sha256=newref('habitat-VERIFY-ONLY.json')['sha256'])
    elif operation != 'inspect': raise UserError('Only explicit inspect or seed mode supported')
    raw = encoded(request); request_sha = hashlib.sha256(raw).hexdigest(); bundle = 'life-'+request_sha[:16]; docs[bundle+'/request.json'] = raw
    docs['manifest.json'] = encoded({'format':'awft-native44-life-preparation:1','operation':operation,'checkpoint_id':checkpoint['id'],'checkpoint_sha256':checkpoint['sha256'],
                                   'recipe_sha256':recipe_sha,'request_sha256':request_sha,'bundle':bundle,'members':len(recipe['members']),'habitat_cells':len(field),
                                   'saved_sources':saved_sources,'source_sha256':digest(Path(__file__)),'reserve_guard':reserve,'installed':False,'native_actions':False,
                                   'construction_and_native_AI_acceptance':False,'command_only_after_parent_review':f'awftlife {operation} {bundle} {request_sha}',
                                   'files':{n:{'bytes':len(r),'sha256':hashlib.sha256(r).hexdigest()} for n,r in docs.items()}})
    if sum(map(len,docs.values())) > 32*MIB: raise UserError('Bounded preparation output exceeded')
    output.mkdir(parents=True,exist_ok=False)
    for name,raw in docs.items():
        path=output/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
    return {'output':str(output),'bundle':bundle,'request_sha256':request_sha,'operation':operation,'native_actions':False}


def prepare(**arguments):
    try:
        return _prepare(**arguments)
    except Exception as failure:
        home,output = Path(arguments['home']).resolve(),Path(arguments['output']).resolve()
        if home.parent == Path('D:/A World for Two/staging/world-tests').resolve() and output.is_relative_to(home/'staging') and not output.exists():
            reserve = guard(0,65536);output.mkdir(parents=True,exist_ok=False)
            (output/'failed-receipt.json').write_bytes(encoded({'status':'FAILED_NATIVE44_PREPARATION','error':str(failure),'native_actions':False,
                                                              'world_or_ledger_writes':False,'source_sha256':digest(Path(__file__)),'reserve_guard':reserve}))
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('home','output','native-classes','woodland','r5-mask','safety-index'): parser.add_argument('--'+name,type=Path,required=True)
    for name in ('sites','retained-recipe','life-ready','native-verify','town-authority'): parser.add_argument('--'+name,type=Path)
    parser.add_argument('--candidate',required=True);parser.add_argument('--bridge',required=True)
    parser.add_argument('--operation',choices=('inspect','seed'),default='inspect')
    print(json.dumps(prepare(**vars(parser.parse_args())),indent=2))
