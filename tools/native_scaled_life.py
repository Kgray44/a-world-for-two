"""Finite64-member LIFE source census/binding; no native command or entity writes."""
from __future__ import annotations
from collections import Counter
from pathlib import Path
import hashlib,json,math,re,zipfile
from control_room.common import UserError,digest,read_json,utcnow
from tools.artistic_bridge_topside_inspection import current_pack,owned_regular
from tools.habitat_life import decode_entity_chunks,entity_rows,entity_uuid,MAX_ENTITY_REGIONS,MAX_ENTITY_BYTES
from tools.native_dense_tree_patch import reference
from tools.playtest import guard
from tools.artistic_zipline_catenary import reader_budget

MIB=1024**2
CLASSES={'native_class_sha256':'NativeHabitatLifeSupport','native_policy_sha256':'HabitatLifePolicy',
         'native_town_authority_sha256':'TownLifeAuthority','native_scale_policy_sha256':'ScaledLifeBudget'}
MEMBERS=('recipe','woodland','r5_reservation','safety_index','uuid_census','habitat_census','population_budget','population_ramp')


def census(snapshot,members,checkpoint_sha,recipe_sha):
    """Actual all-dimension saved UUID collision check plus ALL-entity tile counts.

    Uses the existing strict typed/decompressed region reader. It exports only
    requested identities and aggregate counts, never unrelated UUIDs/raw NBT.
    """
    wanted={row['uuid']:row for row in members}
    if len(wanted)!=len(members)or not 1<=len(wanted)<=64:raise UserError('Finite unique1..64-member cohort required')
    tiles={(math.floor(row['feet'][0])//32,math.floor(row['feet'][2])//32)for row in members}
    prefix=snapshot.prefix.removesuffix('region/')
    names=[name for name in snapshot.files if name.startswith(prefix)and re.search(r'/entities/r\.-?\d+\.-?\d+\.mca$',name)]
    if len(names)>MAX_ENTITY_REGIONS or sum(snapshot.files[name]['size']for name in names)>MAX_ENTITY_BYTES:
        raise UserError('Complete current saved entity census exceeds finite64-region/64MiB budget')
    found={};counts=Counter();sources=[];total=0
    for name in sorted(names):
        record=snapshot.files[name]
        if (record['size']!=0 and not 8192<=record['size']<=32*MIB)or snapshot.archive.getinfo(name).file_size!=record['size']:
            raise UserError('Exact bounded saved entity region required')
        raw=snapshot.archive.read(name)
        if hashlib.sha256(raw).hexdigest()!=record['sha256']:raise UserError('Actual saved entity region digest differs')
        relative=name[len(prefix):]
        dimension='minecraft:overworld'if relative.startswith('entities/')else'minecraft:the_nether'if relative.startswith('DIM-1/')else'minecraft:the_end'if relative.startswith('DIM1/')else'other_saved_dimension'
        match=re.fullmatch(r'r\.(-?\d+)\.(-?\d+)\.mca',Path(name).name)
        if match is None:raise UserError('Exact saved entity region filename required')
        for document in decode_entity_chunks(raw,tuple(map(int,match.groups()))):
            for root in document['Entities']:
                for entity in entity_rows(root):
                    total+=1
                    if total>100000:raise UserError('Bounded full-world entity census exceeded')
                    p=entity.get('Pos')
                    if not isinstance(p,list)or len(p)!=3 or any(type(v)not in(int,float)or not math.isfinite(v)for v in p):
                        raise UserError('Uncertain native entity position prevents habitat counting')
                    tile=math.floor(p[0])//32,math.floor(p[2])//32
                    if dimension=='minecraft:overworld'and tile in tiles:counts[tile]+=1
                    ident=entity_uuid(entity)
                    if ident not in wanted:continue
                    if ident in found:raise UserError('Requested UUID occurs more than once; preserve both')
                    tags=entity.get('Tags',[]);member=wanted[ident]
                    found[ident]={'uuid':ident,'present':True,'entity':entity.get('id'),'position':p,'dimension':dimension,
                                  'expected_tags_present':all(tag in tags for tag in('awft_life',member['member_tag']))}
        sources.append({'file':relative,'bytes':len(raw),'sha256':record['sha256']})
    for name in snapshot.files:
        if name.startswith(prefix+'playerdata/')and name.endswith('.dat')and Path(name).stem in wanted:
            raise UserError('A requested actor UUID belongs to a saved player')
    common={'checkpoint_sha256':checkpoint_sha,'recipe_sha256':recipe_sha,'all_world_entity_regions_scanned':True,
            'saved_entity_records_inspected':total,'sources':sources,'unrelated_UUIDs_or_raw_entity_NBT_exported':False}
    return ({'format':'awft-stopped-world-uuid-census:1',**common,'matching_requested_UUIDs':len(found),
             'all_requested_UUID_absent':not found,'members':[found.get(ident,{'uuid':ident,'present':False})for ident in sorted(wanted)]},
            {'format':'awft-stopped-world-habitat-census:1',**common,
             'tiles':[{'tile_xz':list(tile),'saved_entity_count':counts[tile]}for tile in sorted(tiles)],
             'count_kind':'All serialized entities/passengers in each requested overworld32m tile; deliberately conservative, not only managed animals'})


def bind(home,source,source_sha,candidate,bridge,jar_sha,operation='inspect',native_inspect=None):
    reader_budget()
    home,source=Path(home).absolute(),Path(source).absolute()
    if home.resolve()!=home or home.parent!=Path('D:/A World for Two/staging/world-tests')or operation not in('inspect','seed'):
        raise UserError('Exact owned private stage and explicit LIFE operation required')
    source_ref=reference(home,source,2*MIB)
    if source_ref['sha256']!=source_sha:raise UserError('Exact reviewed cohort source differs')
    doc=read_json(source);checkpoint_path=home/'dashboard/settlement/backup-receipt.json';current=read_json(owned_regular(home,checkpoint_path,8192))
    owner=read_json(owned_regular(home,home/'dashboard/artistic-owner.json',65536))
    if (doc.get('format')!='awft-scaled-life-cohort-source:1'or current.get('verified')is not True
            or(doc.get('checkpoint_id'),doc.get('checkpoint_sha256'))!=(current.get('id'),current.get('sha256'))
            or owner.get('format')!='awft-artistic-stage:1'or Path(owner.get('home','')).resolve()!=home):
        raise UserError('Current exact checkpoint/owned reviewed cohort source required')
    if(home/'dashboard/settlement/tree-growth-quarantine.json').exists():raise UserError('Retain unresolved tree quarantine; no new LIFE binding')
    release,pack=current_pack(home,candidate);installed=read_json(owned_regular(home,home/'server/installed.json',2*MIB))
    if not re.fullmatch(r'\d+\.\d+\.\d+',bridge)or not re.fullmatch(r'[a-f0-9]{64}',jar_sha):raise UserError('Explicit actual compiled helper pins required')
    jar=owned_regular(home,home/'server/mods'/('awft-control-bridge-'+bridge+'.jar'),32*MIB)
    if digest(jar)!=jar_sha or installed.get('files',{}).get(jar.name)!=jar_sha:raise UserError('Actual installed helper differs')
    pins={}
    with zipfile.ZipFile(jar)as archive:
        for key,name in CLASSES.items():
            entry='worldfortwo/bridge/'+name+'.class'
            if entry not in archive.namelist()or not 0<archive.getinfo(entry).file_size<=256*1024:
                raise UserError('The genuine new installed scale API is absent; no fabricated class pins')
            pins[key]=hashlib.sha256(archive.read(entry)).hexdigest()
    refs={}
    keys=list(MEMBERS)+(['town_authority']if'town_authority'in doc else[])+(['life_ready','native_habitat_verify','habitat_plan']if operation=='seed'else[])
    for key in keys:
        row=doc.get(key,{})
        if not isinstance(row.get('path'),str)or Path(row['path']).is_absolute()or'..'in Path(row['path']).parts or'\\'in row['path']:
            raise UserError('Bounded owned immutable cohort member path required')
        path=source.parent/row['path'];ref=reference(home,path,32*MIB)
        if(ref['bytes'],ref['sha256'])!=(row.get('bytes'),row.get('sha256')):raise UserError('Exact cohort source member differs: '+key)
        refs[key]=ref
    recipe=read_json(home/refs['recipe']['path']);members=recipe.get('members',[])
    if recipe.get('format')!='awft-habitat-life-recipe:4'or not 1<=len(members)<=64:
        raise UserError('An explicit v4 finite1..64-member recipe is required')
    if operation=='seed':
        if native_inspect is None:raise UserError('Real matching native INSPECT is required before seeding')
        proof_path=owned_regular(home,Path(native_inspect).absolute(),512*1024);proof=read_json(proof_path)
        if (owned_regular(home,Path(str(proof_path)+'.complete'),128).read_text().strip()!=digest(proof_path)
                or proof.get('operation')!='inspect'or proof.get('recipe_sha256')!=refs['recipe']['sha256']
                or proof.get('failures')!=0 or proof.get('cleanup_passed')is not True or proof.get('spawned')!=0
                or proof.get('members')!=len(members)or proof.get('candidate')!=candidate or proof.get('bridge')!=bridge or proof.get('error')):
            raise UserError('Complete actual clean no-spawn INSPECT of this recipe is required')
        from datetime import datetime,timezone
        try:age=(datetime.now(timezone.utc)-datetime.fromisoformat(proof['finished'].replace('Z','+00:00'))).total_seconds()
        except(ValueError,KeyError,TypeError)as error:raise UserError('Actual native INSPECT completion time required')from error
        inspected_request=proof.get('request_sha256')
        if not -30<=age<=1800 or not isinstance(inspected_request,str)or not re.fullmatch(r'[a-f0-9]{64}',inspected_request):
            raise UserError('Current marked native INSPECT is missing or expired')
        inspected_path=owned_regular(home,home/'dashboard/settlement'/('life-'+inspected_request[:16])/'request.json',128*1024)
        inspected=read_json(inspected_path)
        if (digest(inspected_path)!=inspected_request or inspected.get('format')!='awft-native-habitat-life:4'
                or inspected.get('allowed_operation')!='inspect'or inspected.get('candidate_version')!=candidate
                or inspected.get('bridge_version')!=bridge or inspected.get('pack_sha256')!=pack
                or inspected.get('checkpoint_sha256')!=current['sha256']
                or any(inspected.get(k)!=v for k,v in pins.items())
                or inspected.get('recipe',{}).get('sha256')!=refs['recipe']['sha256']):
            raise UserError('Native INSPECT did not run this actual current helper/recipe/checkpoint')
        refs['native_inspect']=reference(home,proof_path,512*1024)
        from tools.artistic_quay_prototype import fresh_proof
        habitat=read_json(home/refs['habitat_plan']['path'])
        fresh_proof(home/refs['native_habitat_verify']['path'],refs['habitat_plan']['sha256'],len(habitat['blocks']))
    request={'format':'awft-native-habitat-life:4','allowed_operation':operation,'candidate_version':candidate,'bridge_version':bridge,
             'pack_sha256':pack,'neoforge_version':'21.1.262','checkpoint_sha256':current['sha256'],'current_backup':reference(home,checkpoint_path,8192),
             'source_woodland_proposal_sha256':refs['woodland']['sha256'],**pins,**refs}
    if operation=='seed':request['habitat_plan_sha256']=refs['habitat_plan']['sha256']
    raw=(json.dumps(request,separators=(',',':'))+'\n').encode();sha=hashlib.sha256(raw).hexdigest();output=home/'dashboard/settlement'/('life-'+sha[:16])
    if output.exists():raise UserError('Preserve existing request/intents; no automatic replay')
    reserve=guard(0,4*MIB);output.mkdir();(output/'request.json').write_bytes(raw)
    (output/'ownership.json').write_text(json.dumps({'format':'awft-scaled-life-request-owner:1','created':utcnow(),'source':source_ref,
        'actual_helper':reference(home,jar,32*MIB),'actual_pack':reference(home,release,MIB),'request_sha256':sha,'reserve_guard':reserve,
        'native_actions':0,'world_or_entity_writes':0,'NoAI_or_ownership_writes':0,'native_performance_acceptance':False},indent=2)+'\n',encoding='utf-8')
    return {'output':str(output),'request_sha256':sha,'typed_command':'awftlife '+operation+' '+output.name+' '+sha,'native_actions':0}


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--home',required=True);parser.add_argument('--source',required=True)
    parser.add_argument('--source-sha',required=True);parser.add_argument('--candidate',required=True);parser.add_argument('--bridge',required=True)
    parser.add_argument('--jar-sha',required=True);parser.add_argument('--operation',choices=('inspect','seed'),default='inspect');parser.add_argument('--native-inspect')
    args=parser.parse_args();print(json.dumps(bind(args.home,args.source,args.source_sha,args.candidate,args.bridge,args.jar_sha,args.operation,args.native_inspect),indent=2))
