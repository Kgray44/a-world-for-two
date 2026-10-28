"""Prepare small native LIFE inspect/seed requests; never install or execute them.

Reads only an exact stopped backup and retained original woodland proposal.
No account data, copied entity NBT, arbitrary commands, ownership or NoAI fields.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import struct
import uuid
import zlib

from control_room.common import UserError,digest,read_json
from tools.artistic_bridge_refinement import encoded,payload
from tools.artistic_south_forest import Terrain,STUDY,LIFE,buffered_columns
from tools.playtest import guard
from tools.settlement_attractions import MAX_CHUNK,NBTReader

MIB=1024**2
MAX_OUTPUT=16*MIB
MAX_ENTITY_REGIONS=64
MAX_ENTITY_BYTES=64*MIB
OFFSETS=((-2,-2),(2,2),(-2,2),(2,-2),(0,0))
POLICY={key:value for key,value in LIFE.items() if key in (
    'naturalist:deer','naturalist:bird','naturalist:butterfly','naturalist:firefly')}


def entity_uuid(row):
    value=row.get('UUID')
    if value is not None:
        if not isinstance(value,list) or len(value)!=4 or any(type(n) is not int or not -(2**31)<=n<2**31 for n in value):
            raise UserError('Malformed saved entity UUID; do not claim a complete census')
        return str(uuid.UUID(bytes=struct.pack('>4i',*value)))
    if 'UUIDMost' in row and 'UUIDLeast' in row:
        return str(uuid.UUID(bytes=struct.pack('>2q',row['UUIDMost'],row['UUIDLeast'])))
    return None


def entity_rows(row,depth=0):
    if depth>16:raise UserError('Saved passenger nesting exceeds the finite census')
    yield row
    for child in row.get('Passengers',[]):yield from entity_rows(child,depth+1)


def decode_entity_chunks(raw,expected_region=None):
    if not raw:return  # Authenticated zero-byte region contains no serialized entities.
    if not 8192<=len(raw)<=32*MIB:raise UserError('Unbounded saved entity region')
    for ordinal in range(1024):
        location=int.from_bytes(raw[ordinal*4:ordinal*4+4],'big');sector,count=location>>8,location&255
        if not sector and not count:continue
        # RegionFile writes the real record buffer, not necessarily the unused
        # end of its final allocated sector. Missing record bytes remain fatal.
        rounded_end=((len(raw)+4095)//4096)*4096
        if sector<2 or not count or (sector+count)*4096>rounded_end or sector*4096+5>len(raw):raise UserError('Invalid saved entity region sectors')
        offset=sector*4096;length=int.from_bytes(raw[offset:offset+4],'big')
        if not 1<length<=count*4096-4 or offset+4+length>len(raw):raise UserError('Invalid saved entity region payload')
        mode=raw[offset+4];packed=raw[offset+5:offset+4+length]
        if mode not in (1,2,3):raise UserError('External/unknown entity compression is not a complete census')
        if mode==3:decoded=packed
        else:
            decoder=zlib.decompressobj(31 if mode==1 else 15)
            try:decoded=decoder.decompress(packed,MAX_CHUNK+1)
            except zlib.error as failure:raise UserError('Invalid saved entity compression') from failure
            if decoder.unconsumed_tail or decoder.unused_data or not decoder.eof:raise UserError('Saved entity chunk exceeds allocation, is truncated or has trailing compressed data')
        if len(decoded)>MAX_CHUNK:raise UserError('Saved entity chunk exceeds finite decoded allocation')
        document=NBTReader(decoded).read();position=document.get('Position');version=document.get('DataVersion')
        if (not isinstance(position,list) or len(position)!=2 or any(type(v) is not int for v in position)
                or ((position[1]&31)*32+(position[0]&31))!=ordinal):
            raise UserError('Saved entity chunk Position differs from its region header')
        if expected_region is not None and (position[0]//32,position[1]//32)!=tuple(expected_region):
            raise UserError('Saved entity chunk Position belongs to a different region')
        if type(version) is not int or not 0<version<=3955:
            raise UserError('Unknown/future saved entity DataVersion for pinned Minecraft1.21.1')
        roots=document.get('Entities')
        if not isinstance(roots,list) or len(roots)>1024 or any(not isinstance(row,dict) for row in roots):
            raise UserError('Missing/malformed saved entity list is not an empty census')
        yield document


def census(snapshot,members,checkpoint_sha,recipe_sha):
    """All actual-world saved entity regions, including nested passengers/dimensions."""
    prefix=snapshot.prefix.removesuffix('region/');wanted={row['uuid']:row for row in members}
    if len(wanted)!=len(members) or not 1<=len(wanted)<=16:raise UserError('A census batch has 1..16 unique UUIDs')
    names=[name for name in snapshot.files if name.startswith(prefix) and re.search(r'/entities/r\.-?\d+\.-?\d+\.mca$',name)]
    if len(names)>MAX_ENTITY_REGIONS or sum(snapshot.files[name]['size'] for name in names)>MAX_ENTITY_BYTES:
        raise UserError('The whole-world saved entity census exceeds its finite read allocation')
    found={};sources=[];count=0
    for name in sorted(names):
        record=snapshot.files[name]
        if (record['size']!=0 and not 8192<=record['size']<=32*MIB) or snapshot.archive.getinfo(name).file_size!=record['size']:
            raise UserError('Unbounded or changed saved entity region')
        raw=snapshot.archive.read(name)
        if hashlib.sha256(raw).hexdigest()!=record['sha256']:raise UserError('Saved entity region digest differs')
        relative=name[len(prefix):];dimension=('minecraft:the_nether' if relative.startswith('DIM-1/') else
            'minecraft:the_end' if relative.startswith('DIM1/') else 'minecraft:overworld' if relative.startswith('entities/') else 'other_saved_dimension')
        region_match=re.fullmatch(r'r\.(-?\d+)\.(-?\d+)\.mca',Path(name).name)
        if region_match is None:raise UserError('Exact saved entity region filename required')
        for document in decode_entity_chunks(raw,tuple(map(int,region_match.groups()))):
            roots=document.get('Entities',[])
            if not isinstance(roots,list) or len(roots)>1024:raise UserError('Unbounded saved entity list')
            for root in roots:
                for row in entity_rows(root):
                    count+=1
                    if count>100000:raise UserError('Saved entity census exceeds finite entity bound')
                    ident=entity_uuid(row)
                    if ident not in wanted:continue
                    if ident in found:raise UserError('Requested UUID occurs more than once in the stopped world; never replace either')
                    member=wanted[ident];position=row.get('Pos')
                    if not isinstance(position,list) or len(position)!=3 or any(type(v) not in (int,float) or not math.isfinite(v) for v in position):raise UserError('Saved resident position is not finite')
                    tags=row.get('Tags',[])
                    found[ident]={'uuid':ident,'present':True,'entity':row.get('id'), 'position':position,'dimension':dimension,
                        'expected_tags_present':all(tag in tags for tag in ('awft_life',member['member_tag'])),
                        'decoded_entity_evidence_sha256':hashlib.sha256(encoded(row)).hexdigest()}
        sources.append({'file':relative,'bytes':len(raw),'sha256':record['sha256'],'empty_no_serialized_payload':not raw})
    # Player UUIDs are part of the namespace collision check, without publishing
    # unrelated account identifiers or reading their private inventory payloads.
    for name in snapshot.files:
        if name.startswith(prefix+'playerdata/') and name.endswith('.dat'):
            ident=Path(name).stem
            if ident in wanted:raise UserError('A requested resident UUID is a saved player UUID')
    return {'format':'awft-stopped-world-uuid-census:1','checkpoint_sha256':checkpoint_sha,'recipe_sha256':recipe_sha,
            'all_world_entity_regions_scanned':True,'saved_entity_records_inspected':count,
            'matching_requested_UUIDs':len(found),'all_requested_UUID_absent':not found,
            'members':[found.get(ident,{'uuid':ident,'present':False}) for ident in sorted(wanted)],
            'sources':sources,'unrelated_UUIDs_or_raw_entity_NBT_exported':False}


def members_for_group(group,terrain):
    entity=group['entity']
    if entity not in POLICY:raise UserError('A species needs explicit pinned native policy review before seeding')
    category,limit,cls,_=POLICY[entity]
    if group['native_MobCategory']!=category or group['native_class']!='com.crispytwig.naturalist.world.entity.animal.'+cls:
        raise UserError('Original native species identity/classification differs')
    if len(group['members'])!=limit or limit>len(OFFSETS):raise UserError('Original finite group limit differs')
    cx,cz=group['habitat_center_xz'];result=[]
    for member,(dx,dz) in zip(group['members'],OFFSETS):
        ident=str(uuid.UUID(member['uuid']));x,z=cx+dx,cz+dz;ground=terrain.column(x,z)
        if ground['kind']!='dry':raise UserError('Actual LIFE member footing is wet, retained or unknown')
        y=ground['surface_y']+1;before=[]
        for xx in range(x-1,x+2):
            for zz in range(z-1,z+2):
                for yy in range(y-1,y+4):
                    state=terrain.state(xx,yy,zz)
                    if state is None:raise UserError('Every current footing/body witness cell must be known')
                    before.append([xx,yy,zz,state])
        result.append({'uuid':ident,'entity':entity,'native_class':group['native_class'],'native_MobCategory':category,
            'member_tag':'awft_life_'+hashlib.sha256(ident.encode()).hexdigest()[:24],
            'feet':[x+.5,y,z+.5],'roam_bounds':[STUDY[0],48,STUDY[1],STUDY[2]+1,191,STUDY[3]+1],
            'source_group_id':group['id'],'preimage':before})
    return result


def make_recipes(proposal,registry,terrain):
    groups=proposal.get('resident_groups',[])
    if not 1<=len(groups)<=32:raise UserError('Finite original resident groups required')
    recipes=[]
    for start in range(0,len(groups),2):
        members=[]
        for group in groups[start:start+2]:members.extend(members_for_group(group,terrain))
        if not 1<=len(members)<=16 or len({r['uuid'] for r in members})!=len(members):raise UserError('Finite unique native batch required')
        recipes.append({'format':'awft-habitat-life-recipe:1','population_namespace':proposal['population_namespace'],
            'seed':registry['seed'],'world_path':registry['world_path'],'dimension':'minecraft:overworld',
            'members':sorted(members,key=lambda row:row['uuid']),'copied_entity_NBT':False,
            'behavior_acceptance':'Not claimed; real players and later observation required'})
    if len({r['uuid'] for p in recipes for r in p['members']})!=sum(len(p['members']) for p in recipes):raise UserError('Cross-batch UUID duplication')
    return recipes


def ref(home,path):
    path=Path(path).resolve();home=Path(home).resolve()
    if not path.is_relative_to(home) or not path.is_file() or path.is_symlink():raise UserError('Owned ordinary input reference required')
    return {'path':path.relative_to(home).as_posix(),'bytes':path.stat().st_size,'sha256':digest(path)}


def final_plaza_clear(proposal,mask,registry):
    if any(str(mask.get(key))!=str(registry[key]) for key in ('seed','world_path')):
        raise UserError('The exact final plaza mask belongs to a different world')
    columns={(row[0],row[2]) for row in mask['blocks']};skirt=buffered_columns(columns,5)
    if any((row[0],row[2]) in skirt for row in proposal['proposed_geometry']):
        raise UserError('Final plaza/AIR/plumbing skirt conflicts with the proposed forest; no silent trimming')


def _prepare(home,proposal_path,output,checkpoint_id,checkpoint_sha,candidate,bridge,neoforge,native_classes,
            mode='inspect',plaza_mask=None,life_ready=None,native_verify=None,habitat_plan_sha=None,retained_recipes=None):
    home,output,proposal_path,native_classes=map(lambda p:Path(p).resolve(),(home,output,proposal_path,native_classes))
    if output.exists() or not output.is_relative_to(home/'staging'):raise UserError('New private LIFE output required; no dashboard installation')
    reserve=guard(2*MIB,MAX_OUTPUT);registry=read_json(home/'dashboard/settlement/registry.json')
    checkpoint=read_json(home/'dashboard/settlement/backup-receipt.json')
    if checkpoint.get('verified') is not True or checkpoint.get('id')!=checkpoint_id or checkpoint.get('sha256')!=checkpoint_sha:raise UserError('Exact current stopped checkpoint required')
    if not 0<proposal_path.stat().st_size<=MAX_OUTPUT:raise UserError('Bounded original woodland proposal required')
    proposal=read_json(proposal_path)
    if mode not in ('inspect','seed'):raise UserError('Only inspect or seed supported')
    if mode=='seed':
        if not all((plaza_mask,life_ready,native_verify,habitat_plan_sha)):raise UserError('Final exact plaza, LIFE approval and native habitat verification are required for seeding')
        if not 0<Path(plaza_mask).stat().st_size<=8*MIB or not 0<Path(life_ready).stat().st_size<=128*1024:raise UserError('Bounded exact final plaza/approval required')
        mask=read_json(Path(plaza_mask));final_plaza_clear(proposal,mask,registry)
        approval=read_json(Path(life_ready))
        if any(approval.get(key) is not True for key in ('construction_complete','functional_commissioning_complete','visual_corrections_reviewed','habitat_plan_reviewed')):raise UserError('Construction/function/art must complete before LIFE')
    helper=native_classes/'worldfortwo/bridge/NativeHabitatLifeSupport.class';policy=native_classes/'worldfortwo/bridge/HabitatLifePolicy.class'
    for file in (helper,policy):
        if not file.is_file() or not 0<file.stat().st_size<=256*1024:raise UserError('Actual privately compiled helper/policy class inputs required')
    terrain=Terrain(home,checkpoint,registry)
    documents={};requests=[]
    try:
        if retained_recipes:
            prior=Path(retained_recipes);manifest=read_json(prior/'manifest.json');recipes=[]
            for name,info in sorted(manifest['files'].items()):
                if not re.fullmatch(r'recipe-\d{2}\.json',name):continue
                path=prior/name
                if path.stat().st_size!=info['bytes'] or digest(path)!=info['sha256']:raise UserError('Retained population recipe changed; never reassign existing UUIDs')
                recipe=read_json(path)
                if recipe['world_path']!=registry['world_path'] or recipe['seed']!=registry['seed'] or recipe['population_namespace']!=proposal['population_namespace']:raise UserError('Retained recipe belongs to another world/population')
                recipes.append(recipe)
            if not recipes:raise UserError('No original immutable population recipes retained')
        else:
            recipes=make_recipes(proposal,registry,terrain)
            for recipe in recipes:recipe['source_woodland_proposal_sha256']=digest(proposal_path)
        habitat={}
        for recipe in recipes:
            for member in recipe['members']:
                for x,y,z,state in member['preimage']:
                    pos=x,y,z
                    if pos in habitat and habitat[pos]!=state:raise UserError('Two native footing/headroom witnesses disagree')
                    habitat[pos]=state
        template={'format':'awft-native-settlement:1','seed':registry['seed'],'world_path':registry['world_path'],
            'backup_sha256':checkpoint_sha,'palette':[],'blocks':[],'block_entities':[],'commands':[],'landmarks':[]}
        habitat_plan=payload(template,habitat,checkpoint_sha,'VERIFY ONLY - exact initial LIFE footing and body preimages')
        habitat_plan.update(construction_forbidden=True,verification_only=True)
        documents['habitat-native-VERIFY-ONLY.json']=encoded(habitat_plan)
        actual_habitat_sha=hashlib.sha256(documents['habitat-native-VERIFY-ONLY.json']).hexdigest()
        if mode=='seed' and habitat_plan_sha!=actual_habitat_sha:raise UserError('Native verification must bind this exact generated combined footing/headroom plan')
        for n,recipe in enumerate(recipes):
            raw=encoded(recipe);recipe_sha=hashlib.sha256(raw).hexdigest();recipe_name=f'recipe-{n+1:02}.json';census_name=f'census-{n+1:02}.json'
            documents[recipe_name]=raw;documents[census_name]=encoded(census(terrain.snapshot,recipe['members'],checkpoint_sha,recipe_sha))
            def newref(name):return {'path':(output/name).relative_to(home).as_posix(),'bytes':len(documents[name]),'sha256':hashlib.sha256(documents[name]).hexdigest()}
            request={'format':'awft-native-habitat-life:1','allowed_operation':mode,'candidate_version':candidate,'bridge_version':bridge,'neoforge_version':neoforge,
                'source_woodland_proposal_sha256':recipe['source_woodland_proposal_sha256'],
                'native_class_sha256':digest(helper),'native_policy_sha256':digest(policy),'pack_sha256':read_json(home/'packwiz/active.json')['pack_sha256'],
                'checkpoint_sha256':checkpoint_sha,'current_backup':ref(home,home/'dashboard/settlement/backup-receipt.json'),
                'recipe':newref(recipe_name),'uuid_census':newref(census_name)}
            if mode=='seed':
                approval=read_json(Path(life_ready))
                if approval.get('checkpoint_sha256')!=checkpoint_sha or recipe_sha not in approval.get('approved_recipe_sha256s',[]):raise UserError('Each seed approval must bind its exact batch recipe and current checkpoint')
                request.update(life_ready=ref(home,life_ready),native_habitat_verify=ref(home,native_verify),habitat_plan_sha256=habitat_plan_sha,habitat_plan=newref('habitat-native-VERIFY-ONLY.json'))
            raw=encoded(request);sha=hashlib.sha256(raw).hexdigest();name='life-'+sha[:16];documents[name+'/request.json']=raw
            requests.append({'bundle':name,'sha256':sha,'allowed_operation':mode,'members':len(recipe['members']),
                'command_after_parent_review_and_explicit_install':f'awftlife {mode} {name} {sha}'})
    finally:terrain.close()
    manifest={'format':'awft-private-life-preparation:1','source_sha256':digest(Path(__file__)),'original_proposal_sha256':digest(proposal_path),
        'checkpoint_id':checkpoint_id,'checkpoint_sha256':checkpoint_sha,'requests':requests,'native_actions':False,'world_or_entity_writes':False,
        'plaza_exact_mask_pending':plaza_mask is None,'native_runtime_linkage_and_behavior_pending':True,'reserve_guard':reserve,
        'files':{name:{'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()} for name,raw in documents.items()}}
    documents['manifest.json']=encoded(manifest)
    if sum(map(len,documents.values()))>MAX_OUTPUT:raise UserError('Private LIFE artifacts exceed finite output budget')
    output.mkdir(parents=True,exist_ok=False)
    for name,raw in documents.items():
        path=output/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
    return {'output':str(output),'requests':requests,'members':sum(r['members'] for r in requests),'native_actions':False}


def prepare(home,proposal_path,output,checkpoint_id,checkpoint_sha,candidate,bridge,neoforge,native_classes,
            mode='inspect',plaza_mask=None,life_ready=None,native_verify=None,habitat_plan_sha=None,retained_recipes=None):
    arguments=locals().copy()
    try:return _prepare(**arguments)
    except Exception as error:
        # Preserve failed independent attempts without overwriting prior output
        # or writing outside the private staging ownership boundary.
        parent,target=Path(home).resolve(),Path(output).resolve()
        if target.is_relative_to(parent/'staging') and not target.exists():
            reserve=guard(0,65536);target.mkdir(parents=True,exist_ok=False)
            (target/'failed-receipt.json').write_bytes(encoded({'status':'FAILED_PREPARATION','error':str(error),
                'exception_type':type(error).__name__,'source_sha256':digest(Path(__file__)),
                'checkpoint_id':checkpoint_id,'checkpoint_sha256':checkpoint_sha,
                'native_actions':False,'world_or_entity_writes':False,'reserve_guard':reserve}))
        raise


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ('home','proposal-path','output','native-classes'):parser.add_argument('--'+key,type=Path,required=True)
    for key in ('checkpoint-id','checkpoint-sha','candidate','bridge','neoforge'):parser.add_argument('--'+key,required=True)
    parser.add_argument('--mode',choices=('inspect','seed'),default='inspect')
    for key in ('plaza-mask','life-ready','native-verify'):parser.add_argument('--'+key,type=Path)
    parser.add_argument('--retained-recipes',type=Path)
    parser.add_argument('--habitat-plan-sha')
    print(json.dumps(prepare(**vars(parser.parse_args())),indent=2))
