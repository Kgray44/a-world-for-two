"""Expanded immutable south-shore geography and contour-walk study; no native calls.

Only six named saved MCA ZIP members are admitted. No live regions, LOD-derived
ground, world generation, trees, entities or construction are touched.
"""
from __future__ import annotations
import argparse
from collections import Counter,OrderedDict
import hashlib,json,time,zlib
from pathlib import Path
from control_room.common import UserError,digest,read_json,utcnow
from tools.artistic_south_forest import Terrain,MAX_CACHED_CHUNKS
from tools.playtest import guard
from tools.settlement_attractions import BackupWorld,MAX_CHUNK,NBTReader

MIB=1024**2;MAX_RAW=128*MIB;MAX_OUTPUT=16*MIB
REGIONS=tuple((x,z) for x in (1,2) for z in (-3,-2,-1))
BOUNDS=(512,-1536,1535,-1);STEP=16
PROFILE_X=(1008,1104,1200,1296,1392)
PLAZA='staging/artistic-spawn-plaza-r2-20261027T2002Z/forest-reservation-ONLY.json'
PLAZA_SHA='f2d9de880cd144b65e4ec2fe48acccf50bd8a7c43aee1b1a88417d3df12bc6c4'


class ExtentTerrain(Terrain):
 def __init__(self,home,receipt,registry):
  self.snapshot=BackupWorld(home,receipt,registry);self.key=None;self.blocks={};self.entities=set();self.unknown={};self.cache=OrderedDict();self.columns=OrderedDict()
  self.statuses={};self.decoded=0;self.started=time.monotonic();self.raw_bytes=0
  records=[]
  for rx,rz in REGIONS:
   name=self.snapshot.prefix+f'r.{rx}.{rz}.mca';record=self.snapshot.files.get(name)
   if not record or not 8192<=record['size']<=MAX_RAW:raise UserError('One exact saved region unavailable; do not substitute a neighboring member')
   if self.snapshot.archive.getinfo(name).file_size!=record['size']:raise UserError('Region ZIP/index sizes differ')
   records.append(((rx,rz),name,record))
  if sum(r['size'] for _,_,r in records)>MAX_RAW:raise UserError('Six-region raw128MiB allocation exceeded')
  for key,name,record in records:
   raw=self.snapshot.archive.read(name)
   if hashlib.sha256(raw).hexdigest()!=record['sha256']:raise UserError('Exact immutable region digest differs')
   self.snapshot.regions[key]=raw;self.raw_bytes+=len(raw);self.snapshot.sources.append({'file':Path(name).name,'sha256':record['sha256'],'bytes':len(raw),'role':'Explicit six-member expanded geography; no other MCA member admitted'})
 def chunk(self,cx,cz):
  key=cx,cz
  if key==self.key:return None if key in self.unknown else self.blocks
  if key in self.cache:
   self.key=key;self.blocks=self.cache.pop(key);self.cache[key]=self.blocks;return self.blocks
  if key in self.unknown:self.key=key;self.blocks={};return None
  self.key=key;self.blocks={}
  region=cx//32,cz//32
  if region not in REGIONS:self.unknown[key]='outside six admitted regions';return None
  raw=self.snapshot.regions[region];head=((cz&31)*32+(cx&31))*4;location=int.from_bytes(raw[head:head+4],'big');sector,count=location>>8,location&255
  if sector==count==0:self.unknown[key]='not saved/generated';self.statuses[key]='missing';return None
  if sector<2 or not count or (sector+count)*4096>len(raw):raise UserError('Malformed saved region sector')
  offset=sector*4096;length=int.from_bytes(raw[offset:offset+4],'big')
  if not 1<length<=count*4096-4:raise UserError('Malformed saved chunk length')
  mode,packed=raw[offset+4],raw[offset+5:offset+4+length]
  if mode not in (1,2,3):raise UserError('External/unsupported compression requires separate review')
  if mode==3:decoded=packed
  else:
   decoder=zlib.decompressobj(31 if mode==1 else 15);decoded=decoder.decompress(packed,MAX_CHUNK+1)
   if decoder.unconsumed_tail or not decoder.eof:raise UserError('Truncated or over-bound saved chunk')
  if len(decoded)>MAX_CHUNK:raise UserError('Finite decoded chunk exceeded')
  document=NBTReader(decoded).read();self.decoded+=1
  if (document.get('xPos'),document.get('zPos'))!=key:raise UserError('Saved chunk coordinate mismatch')
  status=document.get('Status');self.statuses[key]=status
  if status not in ('full','minecraft:full'):self.unknown[key]='saved non-FULL '+str(status);return None
  self.blocks={row['Y']:row for row in document.get('sections',[])};self.entities.update((row['x'],row['y'],row['z']) for row in document.get('block_entities',[]))
  self.cache[key]=self.blocks
  if len(self.cache)>MAX_CACHED_CHUNKS:self.cache.popitem(last=False)
  return self.blocks


def cliff_bands(profile):
 """Observed steep height bands, not a guessed continuous cliff polygon."""
 groups=[];current=[]
 for a,b in zip(profile,profile[1:]):
  valid=all(v.get('kind')=='dry' and 'surface_y' in v for v in (a,b))
  steep=valid and abs(a['surface_y']-b['surface_y'])>=6
  if steep:
   if not current:current.append(a)
   current.append(b)
  elif current:
   if max(v['surface_y'] for v in current)-min(v['surface_y'] for v in current)>=12:groups.append(current)
   current=[]
 if current and max(v['surface_y'] for v in current)-min(v['surface_y'] for v in current)>=12:groups.append(current)
 return [{'x':rows[0]['x'],'sample_z_bounds':[rows[0]['z'],rows[-1]['z']],'observed_low_y':min(v['surface_y'] for v in rows),'observed_high_y':max(v['surface_y'] for v in rows),'lowest_observed_dry_points':[[v['x'],v['surface_y'],v['z']] for v in rows if v['surface_y']==min(w['surface_y'] for w in rows)],'meaning':'Exact saved profile samples only; the foot/continuation between transects needs denser survey'} for rows in groups]


def study(terrain):
 cells=[]
 for x in range(BOUNDS[0],BOUNDS[2]+1,STEP):
  for z in range(BOUNDS[1],BOUNDS[3]+1,STEP):
   if time.monotonic()-terrain.started>120:raise UserError('Bounded geography reader exceeded120s; no generation/retry fallback')
   cells.append(terrain.column(x,z))
 profiles=[]
 for x in PROFILE_X:
  rows=[terrain.column(x,z) for z in range(-1184,-255,4)]
  profiles.append({'x':x,'step':4,'samples':rows,'steep_bands':cliff_bands(rows)})
 dry=[v['surface_y'] for v in cells if v['kind']=='dry']
 rows=[]
 for z in range(-1184,-255,32):
  selected=[v for v in cells if v['z']==z];land=[v for v in selected if v['kind']=='dry']
  rows.append({'z':z,'counts':dict(Counter(v['kind'] for v in selected)),'dry_x_intervals_sampled':intervals([v['x'] for v in land],STEP),'dry_y_range':[min(v['surface_y'] for v in land),max(v['surface_y'] for v in land)] if land else None})
 return {'format':'awft-expanded-saved-south-extent:1','bounds':list(BOUNDS),'coarse_step':STEP,'samples':cells,'profiles':profiles,'counts':dict(Counter(v['kind'] for v in cells)),'dry_height_range':[min(dry),max(dry)] if dry else None,'cross_rows':rows,'unknown_chunks':[[*key,reason] for key,reason in sorted(terrain.unknown.items())],'saved_status_counts':dict(Counter(terrain.statuses.values())),'raw_MCA_members':len(terrain.snapshot.regions),'raw_MCA_bytes':terrain.raw_bytes,'sources':terrain.snapshot.sources,'saved_BEs':[list(v) for v in sorted(terrain.entities)],'limitations':['Only actual saved FULL chunk block columns classify land/water; missing and non-FULL remain unknown','Coarse samples and transects do not establish every shoreline/root/growth-envelope cell','No LOD, map colors, guessed rectangle, planted tree, native call, live region or world write used','Steep bands are observations, not authority to flatten cliffs or extend forest across river']}


def intervals(values,step):
 rows=[]
 for v in sorted(set(values)):
  if not rows or v>rows[-1][1]+step:rows.append([v,v])
  else:rows[-1][1]=v
 return rows


def svg(study):
 # Original scientific diagram from saved samples, not a Minecraft screenshot.
 result=['<svg xmlns="http://www.w3.org/2000/svg" width="768" height="1152" viewBox="0 0 1024 1536"><rect width="1024" height="1536" fill="#151a20"/>']
 for v in study['samples']:
  kind=v['kind'];height=v.get('surface_y',63)
  color=('#194e78' if kind=='water' else '#6d6477' if kind=='retained_object' else '#151a20' if kind=='unknown' else f'#{min(220,60+height):02x}{min(210,100+height//2):02x}{min(160,45+height//3):02x}')
  result.append(f'<rect x="{v["x"]-512}" y="{v["z"]+1536}" width="16" height="16" fill="{color}"/>')
 result.append('<g fill="#ffffff" font-family="sans-serif" font-size="16"><text x="8" y="24">Saved FULL terrain samples; north up;16m grid; dark=unknown</text><text x="8" y="1516">X512..1535 / Z−1536..−1; map colors are NOT clearance evidence</text></g></svg>')
 return ''.join(result).encode()


def prepare(home,checkpoint_id,checkpoint_sha):
 home=Path(home).resolve()
 if not home.is_relative_to(Path(r'D:\A World for Two\staging\world-tests')):raise UserError('Owned artistic staging home only')
 if checkpoint_id!='20261027T191930Z-f306da' or checkpoint_sha!='8efabed7d75aa02015ed2165ebb249c36da6e301dfd3ef8c971f0e20c9de4f5c':raise UserError('This finite study binds the specifically reviewed immutable191930 checkpoint')
 reserve=guard(MIB,MAX_OUTPUT);registry=read_json(home/'dashboard/settlement/registry.json');receipt={'id':checkpoint_id,'sha256':checkpoint_sha,'verified':True};terrain=ExtentTerrain(home,receipt,registry)
 try:result=study(terrain)
 finally:terrain.close()
 mask=home/PLAZA
 if digest(mask)!=PLAZA_SHA:raise UserError('Exact whole plaza/AIR/routes five-metre exclusion required')
 result.update(checkpoint_id=checkpoint_id,checkpoint_sha256=checkpoint_sha,source_sha256=digest(Path(__file__)),terrain_reader_source_sha256=digest(Path('tools/artistic_south_forest.py')),plaza_mask_sha256=PLAZA_SHA,native_actions=0,world_writes=0)
 raw=(json.dumps(result,separators=(',',':'),ensure_ascii=False)+'\n').encode();diagram=svg(result)
 manifest={'format':'awft-expanded-south-geography-manifest:1','created':utcnow(),'checkpoint_id':checkpoint_id,'checkpoint_sha256':checkpoint_sha,'source_sha256':digest(Path(__file__)),'reserve':reserve,'admitted_regions':list(REGIONS),'MCA_raw_read_limit':MAX_RAW,'MCA_actual_raw_bytes':result['raw_MCA_bytes'],'counts':result['counts'],'dry_height_range':result['dry_height_range'],'cliff_profile_bands':[b for p in result['profiles'] for b in p['steep_bands']],'files':{'geography.json':{'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)},'saved-geography.svg':{'sha256':hashlib.sha256(diagram).hexdigest(),'bytes':len(diagram)}},'status':'READONLY saved extent first report; exact complete bank/cliff-foot envelope and native FULL gaps not assumed','native_actions':0}
 meta=(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n').encode()
 if len(raw)+len(diagram)+len(meta)>MAX_OUTPUT:raise UserError('Finite geography output exceeded')
 out=home/'staging'/('expanded-south-geography-'+str(time.time_ns()));out.mkdir()
 for name,data in (('geography.json',raw),('saved-geography.svg',diagram),('manifest.json',meta)):
  with (out/name).open('xb') as stream:stream.write(data)
 return {'directory':str(out),'manifest_sha256':hashlib.sha256(meta).hexdigest(),'counts':result['counts'],'dry_height_range':result['dry_height_range'],'statuses':result['saved_status_counts'],'MCA_raw_bytes':result['raw_MCA_bytes'],'cliff_bands':manifest['cliff_profile_bands']}

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--home',required=True,type=Path);p.add_argument('--checkpoint-id',required=True);p.add_argument('--checkpoint-sha',required=True);a=p.parse_args();print(json.dumps(prepare(a.home,a.checkpoint_id,a.checkpoint_sha),indent=2))
