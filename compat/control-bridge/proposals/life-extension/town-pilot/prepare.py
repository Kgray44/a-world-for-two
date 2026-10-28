"""Four exact Rose Reach LIFE sites and a two-cell genuine HOME proposal.

No executable LIFE request, world change or authority to bypass native POI,
spawn, collision, ownership, UUID, class/artifact or completed-construction gates.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import time

REPO=Path(__file__).resolve().parents[5]
sys.path.insert(0,str(REPO))
from control_room.common import UserError,digest,read_json
from tools.artistic_bridge_refinement import flatten
from tools.artistic_north_bank_east import NorthTerrain,native_payload,AIR,base,MIB
from tools.habitat_life import decode_entity_chunks
from tools.playtest import guard

SOURCE='staging/north-bank-rose-reach-1793151923325885400/prototype.json'
SOURCE_SHA='831a8e6eb1e757502328d259d0846fff14e325e8ed704dae527cd7fc90cdbc37'
SOURCE_VERIFY='dashboard/settlement/settlement-result-35a052a6-c122-4f6b-aafb-cfe09f0b1153.json'
NAMESPACE_RECIPE='staging/life-inspect-sealed-20261027T200847Z/recipe-01.json'
NAMESPACE_SHA='9809731636545398a759cd1c91cbf15c8497dfb1377dbb3a06126c7583ec12b3'
BED={(1296,65,-1250):'minecraft:blue_bed[facing=north,occupied=false,part=head]',
     (1296,65,-1249):'minecraft:blue_bed[facing=north,occupied=false,part=foot]'}


def load_town_module():
    path=Path(__file__).parent.parent/'native44-town-authority/town_authority.py'
    spec=importlib.util.spec_from_file_location('awft_town_pilot_authority',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def ref(home,path):
    path=Path(path).resolve()
    if not path.is_relative_to(home) or path.is_symlink() or not path.is_file():raise UserError('Immutable owned source reference required')
    return {'path':path.relative_to(home).as_posix(),'bytes':path.stat().st_size,'sha256':digest(path)}


def bounded(path,cap):
    path=Path(path)
    if path.is_symlink() or not path.is_file() or not 0<path.stat().st_size<=cap:raise UserError('Finite ordinary source JSON required')
    return read_json(path)


def inside(bounds,p):return all(bounds[i]<=p[i]<=bounds[i+3] for i in range(3))


def bed_delta(source,actual,entities=()):
    """The two new bed cells are unused authored AIR, never old furnishings."""
    for q in BED:
        if source.get(q)!='minecraft:air' or actual.get(q)!='minecraft:air' or q in entities:
            raise UserError('Genuine HOME addition may use only the two exact unused source AIR cells')
        below=q[0],q[1]-1,q[2]
        if below not in source or source[below]!=actual.get(below) or base(actual[below]) in AIR:
            raise UserError('Preserve exact already-authored full bed supports')
    return dict(BED)


def proposals():
    specs=(
      ('rose-reach-cat','cozys-improved-cats:improved_cat',(1311,66,-1250),[1307,64,-1256,1315,71,-1248],
       [[1311,66,-1250],[1311,66,-1251],[1311,66,-1252]],(1311,69,-1250)),
      ('rose-reach-dog','doggytalents:dog',(1326,65,-1250),[1322,63,-1256,1330,70,-1248],
       [[1326,65,-1250],[1326,65,-1251],[1326,65,-1252]],(1326,68,-1250)),
      ('lantern-lark-ribbit','ribbits:ribbit',(1296,65,-1234),[1292,63,-1238,1300,70,-1229],
       [[1296,65,-1234],[1296,65,-1233],[1296,65,-1232]],(1296,68,-1234)),
      ('gilded-compass-resident','minecraft:villager',(1298,65,-1253),[1293,63,-1258,1303,70,-1246],
       [[1298,65,-1253],[1298,65,-1252],[1298,65,-1251],[1298,65,-1250],[1297,65,-1250]],(1298,68,-1253)),
    )
    result=[]
    for name,entity,root,bounds,route,roof in specs:
        habitat={'kind':'HOME' if entity=='minecraft:villager' else 'MUSIC' if entity=='ribbits:ribbit' else 'DRY',
                 'known_bounds':bounds,'roof':list(roof)}
        if entity=='minecraft:villager':
            habitat.update(bed=[1296,65,-1250],job=[1300,65,-1255],bed_path=route,
                job_path=[[1298,65,-1253],[1298,65,-1254],[1298,65,-1255],[1299,65,-1255]])
        else:habitat['shelter_path']=route
        result.append({'name':name,'entity':entity,'feet':[root[0]+.5,root[1],root[2]+.5],
            'roam_bounds':bounds,'town_site':name,'habitat':habitat})
    return result


def source_sites(source,sites):
    module=load_town_module();entries=[]
    for site in sites:
        bounds=site['habitat']['known_bounds'];module.town_box(bounds)
        cells={q for q in source if inside(bounds,q)};standing=set()
        for key in ('bed_path','job_path','shelter_path'):
            for row in site['habitat'].get(key,[]):
                q=tuple(row);head=q[0],q[1]+1,q[2];under=q[0],q[1]-1,q[2]
                if q not in cells or head not in cells or under not in source:raise UserError('Never infer unwritten town route/body/floor authority')
                if base(source[q]) not in AIR or base(source[head]) not in AIR:raise UserError('Proposed source route crosses actual furnished geometry')
                standing.add(q)
        for key in ('roof','bed','job'):
            if key in site['habitat'] and tuple(site['habitat'][key]) not in cells:raise UserError('Town POI/shelter location was never authored')
        entries.append({'id':site['town_site'],'source_names':['rose-reach-r1b'],'species':[site['entity']],
            'known_bounds':bounds,'occupancy_cells':[list(q) for q in sorted(cells)],'standing_positions':[list(q) for q in sorted(standing)]})
    return entries


def encode(doc):return (json.dumps(doc,separators=(',',':'),ensure_ascii=False)+'\n').encode()


def prepare(home,checkpoint_id,checkpoint_sha):
    home=Path(home).resolve()
    if home.parent!=Path('D:/A World for Two/staging/world-tests').resolve():raise UserError('Exact owned private stage required')
    reserve=guard(MIB,16*MIB);receipt=read_json(home/'dashboard/settlement/backup-receipt.json')
    if receipt.get('verified') is not True or receipt.get('id')!=checkpoint_id or receipt.get('sha256')!=checkpoint_sha:raise UserError('Actual current stopped town checkpoint required')
    registry=read_json(home/'dashboard/settlement/registry.json');source_path=home/SOURCE;proof_path=home/SOURCE_VERIFY
    if digest(source_path)!=SOURCE_SHA:raise UserError('Frozen actual placed Rose Reach source required')
    original=read_json(source_path);source=flatten(original);sites=proposals()
    authority={'format':'awft-town-life-authority:1','seed':registry['seed'],'world_path':registry['world_path'],
        'source_checkpoint_sha256':original['backup_sha256'],
        'sources':[{'name':'rose-reach-r1b','kind':'AUTHORED_FULL_PLAN','plan':ref(home,source_path),'native_verify':ref(home,proof_path)}],
        'sites':source_sites(source,sites)}
    old_recipe=home/NAMESPACE_RECIPE
    if digest(old_recipe)!=NAMESPACE_SHA:raise UserError('Retain original cohort namespace provenance, never create another cohort')
    namespace=read_json(old_recipe)['population_namespace']
    terrain=NorthTerrain(home,receipt,registry);fields={};witness=[];poi=[]
    try:
        for site in sites:
            bounds=site['habitat']['known_bounds'];field={}
            for x in range(bounds[0],bounds[3]+1):
                for z in range(bounds[2],bounds[5]+1):
                    for y in range(bounds[1],bounds[4]+1):
                        q=x,y,z;state=terrain.state(*q)
                        if state is None:raise UserError('Complete FULL town habitat field required')
                        field[q]=state
            # Ordinary native collision and spawn hooks remain runtime gates;
            # this only establishes literal saved dry floors, body and cover.
            for key in ('bed_path','job_path','shelter_path'):
                for row in site['habitat'].get(key,[]):
                    q=tuple(row)
                    if base(field[q]) not in AIR or base(field[q[0],q[1]+1,q[2]]) not in AIR or base(field[q[0],q[1]-1,q[2]]) in AIR:
                        raise UserError('Actual saved town path lacks two-high empty body or footing')
            roof=tuple(site['habitat']['roof'])
            if field[roof]!=source[roof] or base(field[roof]) in AIR:raise UserError('Real authored shelter roof changed')
            fields.update(field);witness.append({'site':site['name'],'known_bounds':bounds,'cells':len(field),
                'actual_roof':{'position':list(roof),'state':field[roof]},'saved_body_floor_preflight':True,
                'native_collision_spawn_rules_POIs_AI':'NOT_RUN'})
        needed={q:terrain.state(*q) for pos in BED for q in (pos,(pos[0],pos[1]-1,pos[2]))}
        delta=bed_delta(source,needed,terrain.entities)
        name=terrain.snapshot.prefix.removesuffix('region/')+'poi/r.2.-3.mca';entry=terrain.snapshot.files.get(name)
        if entry is None or not 8192<=entry['size']<=4*MIB:raise UserError('Bounded actual saved POI member required')
        raw=terrain.snapshot.archive.read(name)
        if len(raw)!=entry['size'] or hashlib.sha256(raw).hexdigest()!=entry['sha256']:raise UserError('Actual saved POI source digest changed')
        for chunk in decode_entity_chunks(raw):
            for section in chunk.get('Sections',{}).values():
                for row in section.get('Records',[]):
                    x,y,z=row['pos']
                    if 1288<=x<=1347 and -1259<=z<=-1226:poi.append(row)
        job=[r for r in poi if r['pos']==[1300,65,-1255] and r['type']=='minecraft:cartographer' and r.get('free_tickets',0)>0]
        if len(job)!=1:raise UserError('Actual free cartographer POI missing; do not forge its profession')
        saved_sources=terrain.snapshot.sources
        poi_source={'file':'poi/r.2.-3.mca','bytes':len(raw),'sha256':entry['sha256']}
    finally:terrain.close()
    documents={'town-authority.json':authority,
        'town-sites-after-native-HOME.json':{'format':'awft-life-sites:3','seed':registry['seed'],'world_path':registry['world_path'],
            'population_namespace':namespace,'sites':sites},
        'town-three-sites-now.json':{'format':'awft-life-sites:3','seed':registry['seed'],'world_path':registry['world_path'],
            'population_namespace':namespace,'sites':sites[:3]},
        'complete-saved-town-habitat-VERIFY-ONLY.json':native_payload(registry,fields,checkpoint_sha,'VERIFY ONLY — actual complete saved town habitat fields; no seeding'),
        'genuine-HOME-before-VERIFY-ONLY.json':native_payload(registry,{q:needed[q] for q in BED},checkpoint_sha,'VERIFY ONLY — exact unused two-cell authored bed nook'),
        'genuine-HOME-two-cell-addition.json':native_payload(registry,delta,checkpoint_sha,'Two-cell genuine blue bed in existing empty ground-floor nook; no role/traits/ownership'),
        'Rose-Reach-with-genuine-HOME-VERIFY-ONLY.json':native_payload(registry,source|delta,checkpoint_sha,'VERIFY ONLY — original Rose Reach plus exactly two new bed states',tags={tuple(r['pos']):r['nbt'] for r in original['block_entities']})}
    for name,doc in documents.items():
        if 'VERIFY-ONLY' in name:doc.update(construction_forbidden=True,verification_only=True)
    raw={name:encode(doc) for name,doc in documents.items()}
    manifest={'format':'awft-town-life-pilot-source:1','checkpoint_id':checkpoint_id,'checkpoint_sha256':checkpoint_sha,
        'source_sha256':digest(Path(__file__)),'historical_actual_source_sha256':SOURCE_SHA,
        'retained_namespace_source':ref(home,old_recipe),'population_namespace':namespace,
        'town_members':4,'present_new_residents':0,'witnesses':witness,'actual_saved_POIs':poi,'poi_source':poi_source,
        'genuine_HOME':'PENDING exact2 AIR preimage/native bed placement/native HOME and free job reinspection; custom model beds are not saved HOME POIs',
        'three_pet_music_sites':'Source/FULL physical preflight only; actual class, spawn hooks, obstruction, default traits and construction approval still mandatory',
        'native_gate_sequence':'Parent verifies two-cell preimage, places real bed once, strictly verifies amended original house/source, saves fresh stopped checkpoint, regenerates v3 complete habitat/census with candidate45 class pins, native inspect then approved seed. Never infer HOME from source-only beds.',
        'Ribbit':'Actual dry music salon shelter; no water, gardener/sorcerer role, instrument item, buffs or home memory fabricated',
        'saved_sources':saved_sources,'reserve_guard':reserve,'native_actions':0,'world_writes':0,'executable_LIFE_requests':0,
        'files':{n:{'bytes':len(v),'sha256':hashlib.sha256(v).hexdigest()} for n,v in raw.items()}}
    raw['manifest.json']=encode(manifest)
    if sum(map(len,raw.values()))>16*MIB:raise UserError('Finite source-only town LIFE bundle exceeded')
    out=home/'staging'/('town-life-pilot-'+str(time.time_ns()));out.mkdir()
    for name,data in raw.items():(out/name).open('xb').write(data)
    # Validate through the sealed actual authority reader rather than a local
    # approximation of the same schema and native-proof completion contract.
    module=load_town_module()
    module.read_authority(home,registry,out/'town-authority.json',bounded,lambda h,p:ref(h,p),{s['entity'] for s in sites})
    return {'folder':str(out),'manifest_sha256':digest(out/'manifest.json'),'town_authority_sha256':digest(out/'town-authority.json'),
        'sites':4,'genuine_HOME_delta_cells':2,'actual_saved_HOME_POIs':sum(r['type']=='minecraft:home' for r in poi),
        'native_actions':0,'files':manifest['files']}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--home',type=Path,required=True)
    parser.add_argument('--checkpoint-id',required=True);parser.add_argument('--checkpoint-sha',required=True);args=parser.parse_args()
    print(json.dumps(prepare(args.home,args.checkpoint_id,args.checkpoint_sha),indent=2))
