"""Read-only saved ownership/custody ledger for the rejected 52 north houses.

It never emits a demolition, restoration, relocation or inventory placement plan.
Full typed NBT stays in a private bounded D: receipt, never in Git. A source match
is evidence of origin, not authority to discard a block, container or player item.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import io
import json
import math
from pathlib import Path
import time
import zlib

import nbtlib

from control_room.common import UserError, digest, read_json
from tools.artistic_bridge_refinement import flatten
from tools.artistic_north_bank_east import preservation
from tools.artistic_zipline_catenary import reader_budget
from tools.playtest import guard
from tools.settlement_attractions import BackupWorld, unpack_section, properties

MIB=1024**2
MAX_RAW=128*MIB
MAX_CHUNK=16*MIB
MAX_OUTPUT=48*MIB
MAX_BE=2*MIB
MAX_SECONDS=180
REGIONS={(1,-3),(2,-3)}
AIR={'minecraft:air','minecraft:cave_air','minecraft:void_air'}

# Exact frozen original source + its ORIGINAL preimage. Later native rebinding
# receipts do not erase these origins or pretend to own unrelated later changes.
BATCHES=(
 ('rose-reach','staging/north-bank-rose-reach-1793151923325885400','prototype.json','831a8e6eb1e757502328d259d0846fff14e325e8ed704dae527cd7fc90cdbc37','before-VERIFY-ONLY.json','8398c8767d1eb3ddc1b91c7989223986c1ec9186c08d378825aa36606705200a',7),
 ('compass-bend','staging/north-bank-compass-bend-1793156177505399400','prototype.json','cc83762b5e3e8476dc2e26ade1d84c21bca545e937d64938cbf0f43afa393b1e','before-VERIFY-ONLY.json','a3e85f50cc0e0b785b230d9f7dcd7eea4dd812b02bb16aa29821a1b898e92783',8),
 ('eastern22','staging/north-bank-eastern22-1793157301590833400','prototype.json','956b58ce5a68a008fb7e3e099962c3f51712af604072a77fd2f81d6b7668375c','before-VERIFY-ONLY.json','d3f055d6f1635a60e2d68e56c526bb25ff7f8636f43cabb65092565f69af47c9',22),
 ('western-ten','staging/north-bank-western-ten-1793158436435294000','prototype.json','e8c8b3c74175d49c0d512abfcdac0d7e84a7d39f31ee92e8ad352755f2f7e2ef','before-VERIFY-ONLY.json','754d71b3bacf236c31e4547d03bdb890ba70771c8d98cb7440af9a979e8d13b3',10),
 ('west-shipwright','staging/north-bank-west-five-final-20261028T0200Z','shipwright-PROPOSAL.json','66e6a346d5e4758f907e71fefc6d22db09cfe4baaac1dfc4951b59750e7121c2','shipwright-before.json','b51970bc0d4305f37339dfa111049d9420b54b4b395979c92caf2e923909512d',1),
 ('west-smith','staging/north-bank-west-five-final-20261028T0200Z','smith-PROPOSAL.json','f45f06899adc59c3ee85cc2b573029d325ca5d5ec1e3cb5346f64d7fc87d312e','smith-before.json','2a5627fef935b140ddd8bad09de7a0cdf26d2685d8a41fff3395615e627092e2',1),
 ('west-armoury','staging/north-bank-west-five-final-20261028T0200Z','armoury-PROPOSAL.json','035f3b76ec1e991c6907fde1745c7aa3255d1ae2fd6f881df0be9262e24517c2','armoury-before.json','30b16ade2432b9727e5b890aa52e5a23b1bca2cd10e721a251e629b8c555d458',1),
 ('west-tavern','staging/north-bank-west-five-final-20261028T0200Z','tavern-PROPOSAL.json','373f02622aa30f42d07bab76b3e4a2aadf522b0f29bca637abe9d72feeae8458','tavern-before.json','52653da8317414555de707483784bdc362c93b29b2331e9350e9c1e9a8f339a6',1),
 ('west-florist','staging/north-bank-west-five-final-20261028T0200Z','florist-PROPOSAL.json','2b5058dbc498f5c63bad69e0694c9c6fbc9625a5933c4aa7e28cc8d80ebc7a8a','florist-before.json','dbf425481322579e1962c16fb87e761acdfc3be6c892c41ea65b04b51a257e15',1),
)


def base(s):return s.split('[',1)[0]


def typed(tag,*,depth=0,budget=None):
    """Lossless tag kinds, including numeric widths and empty list subtype."""
    if budget is None:budget=[0]
    budget[0]+=1
    if depth>40 or budget[0]>100000:raise UserError('Bounded individual BE NBT exceeded')
    kind=type(tag).__name__
    if isinstance(tag,nbtlib.Compound):
        value={str(k):typed(v,depth=depth+1,budget=budget) for k,v in tag.items()}
    elif isinstance(tag,nbtlib.List):
        return {'tag':'List','subtype':tag.subtype.__name__,'value':[typed(v,depth=depth+1,budget=budget) for v in tag]}
    elif isinstance(tag,(nbtlib.ByteArray,nbtlib.IntArray,nbtlib.LongArray)):
        value=[int(v) for v in tag]
    elif isinstance(tag,nbtlib.String):value=str(tag)
    elif isinstance(tag,(nbtlib.Float,nbtlib.Double)):
        number=float(tag);value=number if math.isfinite(number) else repr(number)
    elif isinstance(tag,(nbtlib.Byte,nbtlib.Short,nbtlib.Int,nbtlib.Long)):value=int(tag)
    else:raise UserError('Unknown typed NBT class; do not flatten or discard it: '+kind)
    return {'tag':kind,'value':value}


def typed_subset(expected,actual):
    if type(expected)!=type(actual):return False
    if isinstance(expected,nbtlib.Compound):
        return all(k in actual and typed_subset(v,actual[k]) for k,v in expected.items())
    if isinstance(expected,nbtlib.List):
        return expected.subtype is actual.subtype and len(expected)==len(actual) and all(typed_subset(a,b) for a,b in zip(expected,actual))
    return typed(expected)==typed(actual)


def inventory_facts(be):
    """Stored NBT facts only. No absence of an Items key proves runtime empty."""
    relevant=[];loot=[];records=[]
    def visit(node,path):
        if isinstance(node,nbtlib.Compound):
            for k,v in node.items():
                next_path=path+[str(k)];low=str(k).lower().replace('_','')
                if any(s in low for s in ('item','inventory','storage','container','loot')):
                    relevant.append({'path':next_path,'tag':type(v).__name__,'sha256':hashlib.sha256(json.dumps(typed(v),sort_keys=True,separators=(',',':')).encode()).hexdigest()})
                if 'loot' in low:loot.append({'path':next_path,'typed_value':typed(v)})
                visit(v,next_path)
            if 'id' in node and any(k in node for k in ('count','Count')):
                count_key='count' if 'count' in node else 'Count'
                records.append({'path':path,'id':str(node['id']),'count':int(node[count_key]),
                    'count_tag':type(node[count_key]).__name__,'slot':int(node['Slot']) if 'Slot' in node else None,
                    'slot_tag':type(node['Slot']).__name__ if 'Slot' in node else None,
                    'full_stack_typed_sha256':hashlib.sha256(json.dumps(typed(node),sort_keys=True,separators=(',',':')).encode()).hexdigest()})
        elif isinstance(node,nbtlib.List):
            for n,v in enumerate(node):visit(v,path+[n])
    visit(be,[])
    return {'saved_inventory_like_fields':relevant,'saved_item_records':records,'unresolved_loot_fields':loot,
            'stored_records_are_not_a_native_slot_census':True,
            'native_container_instance_class_slots_and_all_components':'PENDING actual read-only runtime inspection; no assumption from BE id or missing Items',
            'may_delete_or_recreate':False}


def classify(expected,before,actual,*,is_be=False,protected=False):
    """Conservative origin tiers; none of these tiers authorize demolition."""
    if protected:return 'ACCEPTED_ORIGINAL_PROTECTION_PRESERVE'
    if is_be:return 'CURRENT_BLOCK_ENTITY_PRESERVE_FULL_TYPED_CUSTODY'
    if actual==expected:
        return 'SOURCE_AIR_CLEARANCE_ONLY' if base(expected) in AIR else 'SOURCE_EXACT_UNCHANGED_GEOMETRY'
    if base(actual)!=base(expected):return 'MATERIAL_OR_AIR_DELTA_POSSIBLE_HUMAN_OR_OTHER_WORK_PRESERVE'
    wanted,seen=properties(expected),properties(actual)
    if all(seen.get(k)==v for k,v in wanted.items()):return 'SOURCE_EXPLICIT_PROPERTIES_MATCH_NATIVE_UNSPECIFIED_PROPERTIES_REMAIN'
    return 'SAME_ID_STATE_DELTA_NATIVE_SHAPE_OR_HUMAN_ORIGIN_UNPROVEN_PRESERVE'


class BoundedWriter:
    def __init__(self,path,shared):self.stream=path.open('xb');self.shared=shared
    def line(self,value):
        data=(json.dumps(value,separators=(',',':'),ensure_ascii=False)+'\n').encode()
        self.shared[0]+=len(data)
        if self.shared[0]>MAX_OUTPUT:raise UserError('Finite custody output limit exceeded; partials retained')
        self.stream.write(data)
    def close(self):self.stream.close()


def decoded_chunk(raw,cx,cz):
    header=((cz&31)*32+(cx&31))*4;location=int.from_bytes(raw[header:header+4],'big');sector,count=location>>8,location&255
    if sector<2 or not count or (sector+count)*4096>((len(raw)+4095)//4096)*4096:raise UserError('Missing saved custody chunk')
    offset=sector*4096
    if offset+5>len(raw):raise UserError('Truncated chunk header')
    length=int.from_bytes(raw[offset:offset+4],'big')
    if not 1<length<=count*4096-4 or offset+4+length>len(raw):raise UserError('Truncated custody chunk record')
    compression=raw[offset+4];packed=raw[offset+5:offset+4+length]
    if compression==3:decoded=packed
    elif compression in (1,2):
        z=zlib.decompressobj(31 if compression==1 else 15);decoded=z.decompress(packed,MAX_CHUNK+1)
        if len(decoded)>MAX_CHUNK or z.unconsumed_tail or z.unused_data or not z.eof:raise UserError('Bounded typed NBT decompression refused')
    else:raise UserError('Unsupported/external MCA compression')
    if len(decoded)>MAX_CHUNK:raise UserError('Typed custody chunk allocation exceeded')
    doc=nbtlib.File.parse(io.BytesIO(decoded))
    if (int(doc['xPos']),int(doc['zPos']))!=(cx,cz) or str(doc.get('Status','')) not in ('minecraft:full','full'):raise UserError('Custody requires exact saved FULL chunk coordinates')
    return doc


def load_batches(home):
    expected={};before={};tags={};before_tags={};owners=defaultdict(set);houses=[];custody=[]
    for batch,rel,source,sha,prior,prior_sha,count in BATCHES:
        folder=home/rel
        for name,pin in ((source,sha),(prior,prior_sha)):
            if not 0<(folder/name).stat().st_size<=4*MIB or digest(folder/name)!=pin:raise UserError('Exact frozen rejected source/preimage required: '+batch+' '+name)
        plan=read_json(folder/source);old=read_json(folder/prior);field=flatten(plan);old_field=flatten(old)
        if not set(field)<=set(old_field):raise UserError('Original complete before must cover every addressed source target')
        manifest=read_json(folder/'manifest.json')
        lots=manifest.get('buildings',manifest.get('lots'))
        if isinstance(lots,dict):
            ident=batch.removeprefix('west-');row=lots[ident];rows=[{'id':ident,'name':ident,'main_footprint':[[r['support'][0],r['support'][2]] for r in row['actual_dry']['actual_dry_columns']],
                'floor_y':row['origin'][1],'storeys':4,'association':'exact named shop source; actual geometry heights from the full source'}]
        else:rows=lots
        if len(rows)!=count:raise UserError('Exact52 declared house association required')
        for row in rows:
            houses.append({'id':batch+'/'+row['id'],'name':row['name'],'batch':batch,'main_footprint':row['main_footprint'],
                'floor_y':row['floor_y'],'storeys':row.get('storeys'),'classification':'REJECTED_ART_ONLY; current items/human progress retain authority',
                'source_only_association':row.get('association','Exact manifest main outline; shared streets/roof skirts are batch-common, not automatically exclusive house property')})
        for q,s in field.items():
            if q in expected and expected[q]!=s:raise UserError('Conflicting rejected source ownership; review instead of selecting a winner')
            expected[q]=s;before.setdefault(q,old_field[q]);owners[q].add(batch)
        for row in plan.get('block_entities',[]):tags[tuple(row['pos'])]=nbtlib.parse_nbt(row['nbt'])
        for row in old.get('block_entities',[]):before_tags[tuple(row['pos'])]=nbtlib.parse_nbt(row['nbt'])
        custody.append({'batch':batch,'source':rel+'/'+source,'source_sha256':sha,'original_before':rel+'/'+prior,'original_before_sha256':prior_sha,'manifest_sha256':digest(folder/'manifest.json'),'houses':count})
    if len(houses)!=52:raise UserError('The rejected scope must remain37east+15west, exactly52houses')
    return expected,before,tags,before_tags,owners,houses,custody


def prepare(home,checkpoint_id,checkpoint_sha):
    home=Path(home).resolve();reserve=guard(4*MIB,64*MIB);budgets=[reader_budget()]
    if home.parent!=Path('D:/A World for Two/staging/world-tests').resolve():raise UserError('Private artistic stopped archive only')
    receipt=read_json(home/'dashboard/settlement/backup-receipt.json')
    if receipt.get('verified') is not True or (receipt.get('id'),receipt.get('sha256'))!=(checkpoint_id,checkpoint_sha) or 'stopped' not in receipt.get('scope','').lower():raise UserError('Current explicitly verified stopped custody snapshot required')
    registry=read_json(home/'dashboard/settlement/registry.json')
    if Path(registry['world_path']).name!='RosewaterArtistic':raise UserError('Never audit a different world as if it owned this source')
    expected,before,tags,before_tags,owners,houses,custody=load_batches(home)
    protected,accepted=preservation(home,registry)
    for house in houses:house['_columns']=set(map(tuple,house['main_footprint']));house['_stats']=Counter();house['_bes']=[]
    columns=defaultdict(list)
    for house in houses:
        for q in house['_columns']:columns[q].append(house['id'])
    by_chunk=defaultdict(list)
    for q in expected:
        cx,cz=q[0]//16,q[2]//16
        if (cx//32,cz//32) not in REGIONS:raise UserError('The52-source ledger escaped its two authenticated regions')
        by_chunk[cx,cz].append(q)
    out=home/'staging'/('north52-custody-READONLY-'+str(time.time_ns()));out.mkdir();shared=[0]
    cells=BoundedWriter(out/'cells-READONLY.jsonl',shared);bes=BoundedWriter(out/'block-entities-FULL-TYPED-PRIVATE.jsonl',shared)
    stats=Counter();be_stats=Counter();inventory=Counter();unresolved_loot=0;extra_BEs=0;source_count=0;started=time.monotonic();snapshot=None;success=False
    try:
        snapshot=BackupWorld(home,receipt,registry)
        for rx,rz in sorted(REGIONS):
            name=snapshot.prefix+f'r.{rx}.{rz}.mca';entry=snapshot.files.get(name)
            if not entry or not 8192<=entry['size']<=MAX_RAW or snapshot.archive.getinfo(name).file_size!=entry['size']:raise UserError('Bounded authenticated north region required')
            raw=snapshot.archive.read(name)
            if hashlib.sha256(raw).hexdigest()!=entry['sha256']:raise UserError('Stopped MCA digest mismatch')
            snapshot.regions[rx,rz]=raw;source_count+=len(raw)
            if source_count>MAX_RAW:raise UserError('128MiB total immutable MCA cap exceeded')
            snapshot.sources.append({'file':Path(name).name,'sha256':entry['sha256'],'bytes':len(raw),'role':'Exact stopped FULL ownership/typed-NBT census; private only'})
        for cx,cz in sorted(by_chunk):
            doc=decoded_chunk(snapshot.regions[cx//32,cz//32],cx,cz);sections={int(s['Y']):s for s in doc.get('sections',[])}
            be_field={(int(v['x']),int(v['y']),int(v['z'])):v for v in doc.get('block_entities',[])}
            def actual(q):
                x,y,z=q;section=sections.get(y//16)
                return unpack_section(section,x,y,z) if section is not None else 'minecraft:air'
            for q in sorted(by_chunk[cx,cz]):
                now=actual(q);category=classify(expected[q],before[q],now,is_be=q in be_field,protected=(q[0],q[2]) in protected)
                stats[category]+=1;associated=columns.get((q[0],q[2]),[])
                for house in houses:
                    if house['id'] in associated:house['_stats'][category]+=1
                cells.line({'position':list(q),'source_batches':sorted(owners[q]),'main_outline_associations':associated or ['BATCH_COMMON_OR_SKIRT_NOT_EXCLUSIVE'],
                    'expected_original_source':expected[q],'original_before':before[q],'actual_saved':now,'classification':category,'demolition_authorized':False})
            for q,be in sorted(be_field.items()):
                associated=columns.get((q[0],q[2]),[])
                # Whole touched chunks are not property. Preserve near-house
                # extra BEs as advisory custody only, never borrow accepted town.
                if q not in expected and not associated:continue
                saved=typed(be);encoded=json.dumps(saved,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
                if len(encoded)>MAX_BE:raise UserError('Individual typedBE2MiB cap exceeded')
                facts=inventory_facts(be);ident=str(be.get('id','UNKNOWN'));be_stats[ident]+=1
                for row in facts['saved_item_records']:inventory[row['id']]+=row['count']
                unresolved_loot+=len(facts['unresolved_loot_fields']);extra_BEs+=int(q not in expected)
                original=tags.get(q);prior=before_tags.get(q)
                bes.line({'position':list(q),'saved_block':actual(q),'saved_BE_id':ident,'source_batches':sorted(owners.get(q,())),
                    'main_outline_associations':associated,'within_source_address':q in expected,'accepted_original_protection':(q[0],q[2]) in protected,
                    'actual_full_typed_NBT':saved,'actual_full_typed_NBT_sha256':hashlib.sha256(encoded).hexdigest(),
                    'original_authored_subset_typed_NBT':typed(original) if original is not None else None,
                    'original_before_typed_NBT':typed(prior) if prior is not None else None,
                    'authored_subset_exact_typed_match':typed_subset(original,be) if original is not None else None,
                    'NBT_difference_is_not_automatically_human_change':True,'inventory_facts':facts,
                    'action':'RETAIN IN PLACE; no loss/duplication; native class/slot/component inspection and real custody required before any future move'})
                for house in houses:
                    if house['id'] in associated:house['_bes'].append(list(q))
            del doc,sections,be_field
            budgets.append(reader_budget())
            if time.monotonic()-started>MAX_SECONDS:raise UserError('Finite custody180s cap reached; partial evidence retained')
        success=True
    finally:
        cells.close();bes.close()
        if snapshot is not None:sources=snapshot.sources;snapshot.close()
        else:sources=[]
        if not success:
            (out/'FAILED-READONLY.json').open('x').write(json.dumps({'status':'FAILED_PARTIAL_READONLY; never teardown authority','checkpoint_id':checkpoint_id,'checkpoint_sha256':checkpoint_sha,'source_sha256':digest(Path(__file__)),'output_bytes':shared[0],'native_actions':0,'world_writes':0,'inventory_writes':0,'partials_preserved':True},indent=2)+'\n')
    for house in houses:
        house['core_classification_counts']=dict(house.pop('_stats'));house['current_BE_positions_in_main_columns']=house.pop('_bes');house.pop('_columns')
    summary={'format':'awft-rejected-north52-readonly-custody:1','checkpoint_id':checkpoint_id,'checkpoint_sha256':checkpoint_sha,'source_sha256':digest(Path(__file__)),
        'rejected_house_count':52,'east':37,'west':15,'source_addresses':len(expected),'geometry_classification_counts':dict(stats),'current_BE_count':sum(be_stats.values()),
        'saved_BE_ids':dict(be_stats),'extra_BE_inside_main_columns':extra_BEs,'saved_item_record_counts_not_a_native_slot_census':dict(inventory),'unresolved_saved_loot_fields':unresolved_loot,
        'frozen_rejected_source_custody':custody,'accepted_original_custody':accepted,'houses':houses,'raw_saved_sources':sources,
        'reserve_guard':reserve,'reader_peak_observed_RSS_bytes':max(b['owned_reader_rss_bytes'] for b in budgets),'output_bytes':shared[0],
        'files':{n:{'sha256':digest(out/n),'bytes':(out/n).stat().st_size} for n in ('cells-READONLY.jsonl','block-entities-FULL-TYPED-PRIVATE.jsonl')},
        'next_gates':['Parent reviews exact stock/owner/unknown changes before choosing a small rebuild transaction','Refresh actual native Container class/slot/allItemStack component custody without generating loot','Retain anchors in place in redesigned interiors or use a separately reviewed lossless real inventory transfer','Fresh native before and human-progress check immediately before any admitted small demolition or move'],
        'forbidden':['No blanket restore of original before','No source match treated as demolition authority','No saved-NBT copying to duplicate existing stock','No Items-absent treated as empty','No accepted old town, W3, zipline or player-progress deletion'],
        'native_actions':0,'world_writes':0,'inventory_writes':0,'demolition_or_relocation_plan_emitted':False,
        'limits':['The stopped snapshot is finite evidence, not current runtime inventory authority','Explicit-property matches leave omitted native defaults unresolved','State deltas can be normal neighbor derivation or human/other work; they remain preserved','Saved BE identifiers and NBT do not prove a runtime Container instance/size','All typed NBT and player/item components remain private, never commit these outputs']}
    data=(json.dumps(summary,indent=2,ensure_ascii=False)+'\n').encode()
    if shared[0]+len(data)>MAX_OUTPUT:raise UserError('Final summary allocation exceeded; partials remain')
    (out/'manifest.json').open('xb').write(data)
    return {'folder':str(out),'manifest_sha256':digest(out/'manifest.json'),'houses':52,'source_addresses':len(expected),'BEs':sum(be_stats.values()),'saved_item_record_counts':dict(inventory),'unresolved_loot_fields':unresolved_loot,'classifications':dict(stats),'native_actions':0}


if __name__=='__main__':
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('--home',type=Path,required=True);a.add_argument('--checkpoint-id',required=True);a.add_argument('--checkpoint-sha',required=True);args=a.parse_args()
    print(json.dumps(prepare(args.home,args.checkpoint_id,args.checkpoint_sha),indent=2))
