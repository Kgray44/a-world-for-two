"""Immutable saved-column diagnosis for the native cable READY dependency halo.

This stricter source preflight never loads/generates live chunks, changes a gate,
creates a native request, or authorizes ordinary FULL preparation. Supplementary
archives may be inspected without rebinding the canonical construction source.
"""
from __future__ import annotations

import argparse
from collections import Counter,defaultdict
import hashlib
import json
from pathlib import Path
import re
import time
import zipfile
import zlib

from control_room.common import REPO,UserError,digest,utcnow
from tools.artistic_zipline_catenary import reader_budget
from tools.playtest import guard
from tools.settlement_attractions import BackupWorld,MAX_CHUNK,NBTReader

MIB=1024**2
CONTROLLER_SHA='7e6620e1b9c8762aa68d73ff8f912823936586cb7f697b4cb3d5d7732fb1f7f0'
SURVEY_SOURCE_SHA='03dfdd21617f1cda96d505c42340d4ad844e2917ca8d7516af2076c3cf63c1ca'
METADATA_TERMINAL='chain-route-result-61abd071-12c4-4da9-8c3c-eb9b408c70dd.json'
METADATA_SHA='004e0969fabfa27e87c6365286c00a2d9e1630570f22c7de87dd118f3b69a85c'
API_REL='server/libraries/net/minecraft/server/1.21.1-20240808.144430/server-1.21.1-20240808.144430-srg.jar'
API_CLASSES={
 'net/minecraft/server/level/ChunkLevel.class':'efc53ba08d90882b37879f15b0e4375165c89ce505c18ca2f858e3cb6c310230',
 'net/minecraft/world/level/chunk/status/ChunkPyramid.class':'b76ee166276760cc2d4c8b1e210fefe446a0db71de589bdbd77647ff92dc0e7e',
 'net/minecraft/world/level/chunk/status/ChunkStatus.class':'24fb7eaf52aca64e6027887e55c4b10b75bb8ff37a50b13bd6bc56a9120cae8e',
 'net/minecraft/server/level/DistanceManager.class':'2ebf44d67c09b1ef4cb48c0e005f6e69f157d136aa11254fa75bffae8c9241e0',
 'net/minecraft/server/level/ServerChunkCache.class':'5e9ad90765ddfbcd15b8f63992a32fa1d36a2b2c513017c77ae82f4863333a99',
}


def require(value,message):
 if not value:raise UserError(message)


def packed(position):
 x,z=position;value=(x&0xffffffff)|((z&0xffffffff)<<32)
 return value if value<2**63 else value-2**64


def derive_columns(nodes,metadata):
 for key in ('full_level','ticket_level','native_max_level','ticket_reach','loading_full_dependency_radius','extra_light_neighbor_ring','derived_radius','required_read_columns'):
  require(type(metadata.get(key))is int,'Exact actual native integer metadata required')
 require(metadata['full_level']==33 and metadata['native_max_level']==44 and metadata['loading_full_dependency_radius']==1,
         'Pinned native level/loading metadata changed; independent review required')
 full=metadata['full_level'];ticket=full-2;reach=metadata['native_max_level']-ticket
 radius=max(reach+1,2+metadata['loading_full_dependency_radius']+1)
 require(metadata['ticket_level']==ticket and metadata['ticket_reach']==reach and metadata['extra_light_neighbor_ring']==1
         and metadata['derived_radius']==radius and radius<=16,'Native ticket/light halo formula differs')
 require(len(nodes)==15 and all(len(p)==3 and all(type(v)is int for v in p)for p in nodes),'Exact fifteen native endpoints required')
 centers={(x//16,z//16)for x,y,z in nodes};centers.add((1101//16,-1257//16))
 columns={(x+dx,z+dz)for x,z in centers for dx in range(-radius,radius+1)for dz in range(-radius,radius+1)}
 require(len(centers)==15 and len(columns)==metadata['required_read_columns']==2002 and len(columns)<=4096,
         'Exact finite native route halo differs')
 return centers,sorted(columns,key=packed),radius


class TypedReader(NBTReader):
 """Retain root/list tag kinds for the controller's exact contains(type) gates."""
 def value(self,kind,depth=0):
  if kind==10 and depth==0:
   result={};self.root_types={};self.list_types={}
   while True:
    child=self.number('B')
    if child==0:return result
    name=self.string();require(name not in result,'Duplicate root NBT key')
    self.root_types[name]=child
    if child==9:
     at=self.data.tell();self.list_types[name]=self.number('B');self.data.seek(at)
    result[name]=super().value(child,depth+1)
  return super().value(kind,depth)


def read_chunk(raw,cx,cz):
 require(len(raw)>=8192,'Truncated saved region header')
 at=((cz&31)*32+(cx&31))*4;location=int.from_bytes(raw[at:at+4],'big');sector,count=location>>8,location&255
 require(sector!=0,'ABSENT saved column')
 require(sector>=2 and count>0 and(sector+count)*4096<=len(raw),'Invalid saved region sector')
 at=sector*4096;length=int.from_bytes(raw[at:at+4],'big');require(1<length<=count*4096-4,'Invalid saved NBT record length')
 mode,compressed=raw[at+4],raw[at+5:at+4+length]
 if mode==3:decoded=compressed
 elif mode in(1,2):
  decoder=zlib.decompressobj(31 if mode==1 else 15);decoded=decoder.decompress(compressed,MAX_CHUNK+1)
  require(not decoder.unconsumed_tail and not decoder.unused_data and decoder.eof,'Truncated/over-bound saved compression')
 else:raise UserError('Unsupported/external saved NBT compression')
 require(len(decoded)<=MAX_CHUNK,'Decoded saved NBT allocation exceeded')
 reader=TypedReader(decoded);document=reader.read()
 return document,reader.root_types,reader.list_types,hashlib.sha256(decoded).hexdigest()


def classify(document,kinds,lists,position):
 failed=[];x,z=position
 if kinds.get('DataVersion')!=3 or document.get('DataVersion')!=3955:failed.append('version')
 if any(kinds.get(k)!=3 for k in('xPos','zPos'))or(document.get('xPos'),document.get('zPos'))!=(x,z):failed.append('coordinate')
 if kinds.get('Status')!=8 or document.get('Status')not in('full','minecraft:full'):failed.append('non_FULL')
 sections=document.get('sections',[])
 if kinds.get('sections')!=9 or lists.get('sections')!=10 or not isinstance(sections,list)or not 1<=len(sections)<=64:failed.append('sections')
 if 'below_zero_retrogen'in document:failed.append('retrogen')
 light=kinds.get('isLightOn')in(1,2,3,4,5,6)and(int(document.get('isLightOn',0))&255)!=0
 if not light:failed.append('lighting')
 return {'chunk':list(position),'classification':'UNQUALIFIED'if failed else'NBT_FLAGS_QUALIFIED','failed':failed,
         'status':document.get('Status'),'DataVersion':document.get('DataVersion'),'isLightOn':document.get('isLightOn'),
         'isLightOn_tag_type':kinds.get('isLightOn'),'sections':len(sections)if isinstance(sections,list)else None,
         'section_list_type':lists.get('sections'),'retrogen_present':'below_zero_retrogen'in document}


def generation_proposal(facts,halo,metadata):
 targets={tuple(row['chunk'])for row in facts if row['failed']}
 # Pinned ChunkLevel.<clinit> sets MAX_LEVEL=33+GENERATION_PYRAMID FULL
 # accumulatedDependencies.radius. This is a column-count envelope, not a
 # maximum disk allocation or authority to submit a generation request.
 radius=metadata['native_max_level']-metadata['full_level']
 closure={(x+dx,z+dz)for x,z in targets for dx in range(-radius,radius+1)for dz in range(-radius,radius+1)}
 return {'authorization':False,'native_actions':0,'target_columns':len(targets),'target_chunk_positions':[list(p)for p in sorted(targets,key=packed)],
         'ordinary_completion_eligible_source_flags':all(set(row['failed'])<={'non_FULL','lighting'}for row in facts),
         'generation_dependency_radius':radius,'generation_dependency_columns_union':len(closure),
         'dependency_columns_outside_readiness_halo':len(closure-set(halo)),
         'dependency_chunk_bounds':None if not closure else[min(x for x,z in closure),min(z for x,z in closure),max(x for x,z in closure),max(z for x,z in closure)],
         'disk_allocation_upper_bound':'UNKNOWN: dependency count is not a disk bound; separate enforced writer forecast/cap and master-exclusive authorization are mandatory',
         'safe_next_step':'Preserve allFULL columns and receipts. Master may review a separately bounded ordinary native completion protocol, including outside dependency custody, then normal save/new supplemental archive and a fresh full halo census. No retry, pregeneration, source relabel or weaker gate is authorized here.'}


def square(position,radius):
 return {(position[0]+dx,position[1]+dz)for dx in range(-radius,radius+1)for dz in range(-radius,radius+1)}


def survey_proposal(facts,halo,metadata):
 """Finite geometry grouping, never executable native requests or writer approval."""
 targets={tuple(row['chunk'])for row in facts if row['failed']}
 eligible=all(set(row['failed'])<={'non_FULL','lighting'}for row in facts)
 if not eligible:return {'authorization':False,'groups':[],'reason':'Absent, invalid, version, coordinate, section or retrogen failures need distinct recovery review; ordinary completion is not proposed'}
 halo=set(halo);remaining=set(targets);candidates=set()
 for position in targets:candidates.update(square(position,2))
 require(len(candidates)<=4096,'Finite survey grouping candidate envelope exceeded')
 cover={position:square(position,2)&targets for position in candidates};groups=[]
 while remaining:
  amount=max(len(values&remaining)for values in cover.values())
  ties=[position for position,values in cover.items()if len(values&remaining)==amount]
  anchor=min(ties,key=lambda p:(len(square(p,15)-halo),packed(p)))
  addressed=cover[anchor]&remaining;remaining-=addressed
  samples=square(anchor,1);full=square(anchor,2);envelope=square(anchor,15)
  groups.append({'group':len(groups)+1,'anchor_chunk':list(anchor),'survey_center_block_xz':[anchor[0]*16+8,anchor[1]*16+8],
                 'survey_radius_blocks':16,'survey_step_blocks':16,'new_unqualified_targets':[list(p)for p in sorted(addressed,key=packed)],
                 'sample_ticket_centers':[list(p)for p in sorted(samples,key=packed)],'requested_FULL_true_columns':[list(p)for p in sorted(full,key=packed)],
                 'generation_dependency_columns':27**2,'ticket_light_envelope_columns':len(envelope),
                 'ticket_light_chunk_bounds':[anchor[0]-15,anchor[1]-15,anchor[0]+15,anchor[1]+15]})
  require(len(groups)<=128,'Finite survey group count exceeded')
 centers=set();full=set()
 for group in groups:
  centers.update(map(tuple,group['sample_ticket_centers']));full.update(map(tuple,group['requested_FULL_true_columns']))
 generation=set();ticket=set()
 for position in full:generation.update(square(position,metadata['native_max_level']-metadata['full_level']))
 for position in centers:ticket.update(square(position,14))
 whole=ticket|generation
 return {'authorization':False,'native_actions':0,'target_columns':len(targets),'group_count':len(groups),'groups':groups,
         'named_server_ticket_argument_radius':1,'named_server_ticket_level':32,'conservative_ticket_plus_light_radius':14,
         'distinct_sample_ticket_centers':len(centers),'distinct_requested_FULL_true_columns':len(full),
         'all_requested_FULL_generation_dependency_columns_union':len(generation),'ticket_light_columns_union':len(ticket),
         'whole_model_columns_union':len(whole),'whole_model_columns_outside_readiness_halo':len(whole-halo),
         'whole_model_chunk_bounds':None if not whole else[min(x for x,z in whole),min(z for x,z in whole),max(x for x,z in whole),max(z for x,z in whole)],
         'whole_model_chunk_positions':[list(p)for p in sorted(whole,key=packed)],
         'limits':'Source geometry recommendation only. Each radius16/step16 survey samples9ticket centers and queues their3x3FULL(true) neighborhoods (25uniqueFULL requests). Radius14 per ticket is a conservative model; third-party behavior and disk cost remain unproved. One separately bounded master-owned group at a time, no executable request or lease. Never substitute target-only generation closure for this wider survey model.'}


def census(home,checkpoint_id,checkpoint_sha,output=None):
 home=Path(home).resolve();require(home.parent==Path(r'D:\A World for Two\staging\world-tests'),'Owned private construction home required')
 require(re.fullmatch(r'\d{8}T\d{6}Z-[a-f0-9]{6}',checkpoint_id)is not None and re.fullmatch('[a-f0-9]{64}',checkpoint_sha)is not None,
         'Explicit immutable checkpoint ID and SHA required')
 source=REPO/'compat/control-bridge/src/worldfortwo/bridge/NativeChainRouteSupport.java'
 require(digest(source)==CONTROLLER_SHA,'Pinned native controller source changed')
 require(digest(REPO/'compat/control-bridge/src/worldfortwo/bridge/SettlementSupport.java')==SURVEY_SOURCE_SHA,'Pinned native survey source changed')
 text=source.read_text();body=re.search(r'private static final int\[\]\[\] NODES=(.*?);',text,re.S)
 require(body is not None,'Exact native endpoint initializer required')
 nodes=[tuple(map(int,row))for row in re.findall(r'\{(-?\d+),(-?\d+),(-?\d+)\}',body[1])]
 proof_path=home/'dashboard/settlement'/METADATA_TERMINAL
 require(proof_path.is_file()and not proof_path.is_symlink()and proof_path.stat().st_size<=128*1024 and digest(proof_path)==METADATA_SHA,
         'Exact genuine zero-mutation native READY metadata terminal required')
 marker=Path(str(proof_path)+'.complete');require(marker.is_file()and marker.stat().st_size==64 and marker.read_text()==METADATA_SHA,'Actual native metadata terminal marker required')
 proof=json.loads(proof_path.read_bytes());metadata=proof['ready_halo']
 require(proof.get('helper_world_mutations')==0 and proof.get('temporary_tickets_remaining')==0 and proof.get('pending_shared_chunk_futures')==0,
         'Clean zero-action native metadata source required')
 centers,order,radius=derive_columns(nodes,metadata)
 api=home/API_REL;require(api.is_file()and not api.is_symlink()and api.stat().st_size<=32*MIB,'Bounded actual pinned native API archive required')
 with zipfile.ZipFile(api)as jar:
  for member,expected in API_CLASSES.items():
   require(jar.getinfo(member).file_size<=MIB and hashlib.sha256(jar.read(member)).hexdigest()==expected,'Native ticket/loading API class differs')
 receipt={'id':checkpoint_id,'sha256':checkpoint_sha,'verified':True};require((home/'backups'/(checkpoint_id+'.zip')).stat().st_size<=512*MIB,'Finite immutable archive required')
 budgets=[reader_budget()];started=time.monotonic();snapshot=BackupWorld(home,receipt,json.loads((home/'dashboard/settlement/registry.json').read_bytes()))
 groups=defaultdict(list);facts=[];regions=[];total_raw=0
 for p in order:groups[(p[0]//32,p[1]//32)].append(p)
 try:
  for (rx,rz),positions in sorted(groups.items()):
   name=snapshot.prefix+f'r.{rx}.{rz}.mca';record=snapshot.files.get(name)
   if record is None:
    facts.extend({'chunk':list(p),'classification':'ABSENT_REGION','failed':['absent']}for p in positions);continue
   require(8192<=record['size']<=64*MIB,'Unexpected saved region allocation')
   total_raw+=record['size'];require(total_raw<=128*MIB,'Saved raw region128MiB allocation exceeded')
   require(snapshot.archive.getinfo(name).file_size==record['size'],'Saved ZIP/member allocation differs')
   raw=snapshot.archive.read(name);require(len(raw)==record['size']and hashlib.sha256(raw).hexdigest()==record['sha256'],'Authenticated saved region bytes differ')
   regions.append({'member':name,'bytes':len(raw),'sha256':record['sha256']})
   for p in positions:
    try:
     doc,kinds,lists,chunk_sha=read_chunk(raw,*p);row=classify(doc,kinds,lists,p);row['chunk_nbt_sha256']=chunk_sha
    except UserError as error:
     absent='ABSENT'in str(error);row={'chunk':list(p),'classification':'ABSENT'if absent else'INVALID_RECORD','failed':['absent'if absent else'invalid_record'],'reason':str(error)}
    facts.append(row)
    if len(facts)%128==0:
     budgets.append(reader_budget());require(time.monotonic()-started<=120,'Finite120second source census expired')
   del raw
 finally:snapshot.close()
 require(len(facts)==2002,'Complete exact source halo census required');facts.sort(key=lambda row:packed(row['chunk']))
 counts=Counter(row['classification']for row in facts);statuses=Counter(row.get('status','ABSENT')for row in facts);failures=Counter(reason for row in facts for reason in row['failed'])
 report={'format':'awft-zipline-saved-radius14-diagnosis:1','created':utcnow(),'source_checkpoint':receipt,
         'controller_source_sha256':CONTROLLER_SHA,'native_api_class_sha256':API_CLASSES,'native_metadata_terminal_sha256':METADATA_SHA,
         'derivation':dict(metadata,endpoint_chunks=len(centers),columns=len(order),first_native_read_column=list(order[0])),
         'source_ready':not failures,'classification_counts':dict(counts),'saved_status_counts':dict(statuses),'failed_predicate_counts':dict(failures),
         'first_column':facts[0],'columns':facts,'region_sources':regions,'raw_region_bytes_read':total_raw,
         'elapsed_seconds':round(time.monotonic()-started,3),'observed_reader_rss_max':max(row['owned_reader_rss_bytes']for row in budgets),
         'generation_proposal':generation_proposal(facts,order,metadata),'survey_proposal':survey_proposal(facts,order,metadata),
         'survey_source_sha256':SURVEY_SOURCE_SHA,'world_writes':0,'native_actions':0,'live_persisted_reads':0,
         'limits':'Immutable archive only; source_ready is typed NBT flags, not complete native READY: native4MiB sizeInBytes is not recomputed. No live-state acceptance, canonical-source rebinding, generation, retry or gate change. Monitoring is not an OS quota.'}
 budgets.append(reader_budget());require(time.monotonic()-started<=120,'Finite120second complete source diagnosis expired')
 report['elapsed_seconds']=round(time.monotonic()-started,3);report['observed_reader_rss_max']=max(row['owned_reader_rss_bytes']for row in budgets)
 if output is not None:
  output=Path(output).absolute();allowed=(REPO/'.local').resolve()
  require(output.parent.resolve()==allowed and not output.exists(),'New owned .local diagnosis only')
  raw=(json.dumps(report,separators=(',',':'))+'\n').encode();require(len(raw)<4*MIB,'Source diagnosis4MiB output exceeded')
  report['storage_guard']=guard(4*MIB,0);raw=(json.dumps(report,separators=(',',':'))+'\n').encode();require(len(raw)<4*MIB,'Source diagnosis4MiB final output exceeded')
  output.parent.mkdir(exist_ok=True);output.open('xb').write(raw)
 return report


if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--home',type=Path,required=True);parser.add_argument('--checkpoint-id',required=True);parser.add_argument('--checkpoint-sha',required=True);parser.add_argument('--output',type=Path)
 args=parser.parse_args();report=census(args.home,args.checkpoint_id,args.checkpoint_sha,args.output)
 print(json.dumps({key:report[key]for key in('source_checkpoint','source_ready','classification_counts','saved_status_counts','failed_predicate_counts','first_column','elapsed_seconds','limits')},indent=2))
 raise SystemExit(0 if report['source_ready']else 2)
