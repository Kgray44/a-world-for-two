"""Original shallow secondary ceiling/lodge depth. Private proposals, no world calls."""
from __future__ import annotations
import argparse
from collections import deque
import hashlib,json,time
from pathlib import Path
from control_room.backups import Backups
from control_room.common import Layout,UserError,digest,read_json,utcnow
from tools.artistic_depth_castle_mill import INPUTS,decode
from tools.artistic_maritime_depth import admit_owner
from tools.artistic_materials import require_material_rule,require_outdoor_rule
from tools.playtest import guard
from tools.settlement_attractions import BackupWorld,base,properties

AIR='minecraft:air';VOID={AIR,'minecraft:cave_air','minecraft:void_air'};MAX_OUTPUT=16*1024**2
SOURCES=(
 ('castle','artistic-castle-depth-native-parts-20261027T1905Z/castle-depth-native-verify-only.json','ebcd5224821ef8dc425f167314a267f9c66772270900728bf11536b986fb6e2a'),
 ('bridge','bridge-tower-native-settle-20261027T1823Z/full-verification.json','5500bf6e11c36d4b0dca9bcdeac555b3bf9b600db8763c80d091c1e0194317b0'),
)
ENVELOPES={
 'gallery':(1258,90,-1037,1263,91,-1032),
 'kitchen':(1281,80,-1034,1285,81,-1030),
 'workshop':(1237,80,-1039,1243,81,-1035),
 'north-lodge':(1211,71,-1201,1215,76,-1200),
 'south-lodge':(1211,71,-1096,1215,76,-1095),
}
NICHE_CELLS={(x,y,c-4) for c in (-1196,-1091) for x in (1212,1214) for y in (72,73)}
NEIGHBORS=((1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1))


class Secondary:
 def __init__(self,registry,snapshot,originals,fixed=(),routes=()):
  self.registry,self.snapshot,self.originals=registry,snapshot,originals
  self.blocks={};self.before={};self.groups={};self.supports={};self.features={};self.brackets=[];self.group='gallery';self.fixed=set(fixed)
  for route in routes:
   x,y,z=route['point']
   self.fixed.update((x+dx,y+dy,z+dz) for dx in (-1,0,1) for dz in (-1,0,1) for dy in (-1,0,1,2))
  for states in originals.values():
   self.fixed.update(pos for pos,value in states.items() if base(value).startswith(('create:','create_hypertube:','overpressure:','handcrafted:','mcwwindows:','mcwdoors:')) or base(value) in {'minecraft:chain','minecraft:lantern','minecraft:lever','minecraft:stone_button','minecraft:chest','minecraft:barrel'})
 def state(self,name,**props):
  schema=self.registry['blocks'].get(name)
  if schema is None or any(str(v).lower() not in schema.get(k,()) for k,v in props.items()):raise UserError('Exact native secondary fitting/property required: '+name)
  return name+('['+','.join(k+'='+str(v).lower() for k,v in sorted(props.items()))+']' if props else '')
 def at(self,pos):return self.blocks[pos] if pos in self.blocks else self.snapshot.state(pos)
 def put(self,x,y,z,name,*,niche=False,**props):
  pos=x,y,z;box=ENVELOPES[self.group]
  if any(type(v) is not int for v in pos) or not all(box[n]<=pos[n]<=box[n+3] for n in range(3)):raise UserError('Escaped exact secondary feature envelope')
  if x<=1204 and -1200<=z<=-1080:raise UserError('Keep river, moving-leaf and machinery clearance')
  old=self.snapshot.state(pos)
  if pos in self.fixed or pos in self.snapshot.protected:raise UserError('Preserve saved fixture, BE, inventory, route or control')
  if niche:
   if pos not in NICHE_CELLS or base(old)!='minecraft:white_terracotta':raise UserError('Only exact blank plaster cells may become blind half-depth niches')
   if not name.endswith('_stairs') or props.get('facing')!='south':raise UserError('A blind niche retains its inward solid half-wall')
  elif base(old) not in VOID:raise UserError('New relief requires actual saved air; do not assume outside or erase construction')
  value=self.state(name,**props)
  if pos in self.blocks and self.blocks[pos]!=value:raise UserError('Two secondary features conflict')
  self.blocks[pos]=value;self.before[pos]=old;self.groups.setdefault(self.group,set()).add(pos)
  if len(self.blocks)>500:raise UserError('Split this small physical-depth proposal')
 def stairs(self,x,y,z,name,facing,*,half='top',niche=False):self.put(x,y,z,name,facing=facing,half=half,shape='straight',waterlogged=False,niche=niche)
 def slab(self,x,y,z,name):self.put(x,y,z,name,type='top',waterlogged=False)
 def corbel(self,x,y,z,face):
  self.put(x,y,z,'mythrais:small_curved_corbel_dark_oak',facing=face,shape=0);self.brackets.append(((x,y,z),(x,y+1,z)))
 def column(self,x,y,z,part):
  props={'colour':0,'facing':'north'}
  if part!='middle':props['mirrored']=False
  self.put(x,y,z,'mythrais:decorated_column_'+part+'_small_dark_oak',**props)


def construct(p):
 # A light gallery cassette: shaped perimeter, carved joint/corner bosses,
 # central shallow plaster panel, and retained higher recesses between them.
 p.group='gallery'
 for x in (1258,1263):
  for z in range(-1037,-1031):
   if z in (-1037,-1032):p.put(x,91,z,'chipped:tiled_calcite')
   elif z==-1035:p.put(x,91,z,'minecraft:chiseled_quartz_block')
   else:p.stairs(x,91,z,'dawnoftimebuilder:limestone_bricks_stairs','east' if x==1258 else 'west')
 for z in (-1037,-1032):
  for x in range(1259,1263):
   if x==1260:p.put(x,91,z,'minecraft:chiseled_quartz_block')
   else:p.stairs(x,91,z,'dawnoftimebuilder:limestone_bricks_stairs','south' if z==-1037 else 'north')
 for x in (1260,1261):
  for z in (-1035,-1034):p.slab(x,91,z,'minecraft:smooth_quartz_slab')
 for x,face in ((1258,'east'),(1263,'west')):p.corbel(x,90,-1035,face)
 p.features[p.group]='Light molded cassette: stair undercuts, four carved corner bosses, intentional mid-joints, shallow central panel and higher open recesses; retained upper floor untouched.'

 # The kitchen uses three compact practical joists. Its original chain hangs
 # between bands and is never moved, shortened, retagged or counted as new work.
 p.group='kitchen'
 for z in (-1034,-1032,-1030):
  for x in range(1281,1286):
   if x==1283:p.put(x,81,z,'chipped:carved_stripped_spruce_log',axis='x')
   elif x in (1281,1285):p.put(x,81,z,'chipped:boxed_spruce_planks')
   else:p.slab(x,81,z,'minecraft:spruce_slab')
 for x,face in ((1281,'east'),(1285,'west')):
  for z in (-1034,-1030):p.corbel(x,80,z,face)
 p.features[p.group]='Three shallow workroom joists with actual central scarf joints and small rooted end brackets, around the unchanged hanging light chain.'

 # A craftsman's ladder cassette: two longitudinal molded timbers, short
 # transverse blocking, darker joint collars and two restrained side braces.
 p.group='workshop'
 for x in (1238,1242):
  for z in range(-1039,-1034):
   if z==-1037:p.put(x,81,z,'chipped:carved_stripped_spruce_log',axis='z')
   else:p.stairs(x,81,z,'minecraft:spruce_stairs','east' if x==1238 else 'west')
 for z in (-1039,-1035):
  for x in range(1239,1242):p.slab(x,81,z,'minecraft:dark_oak_slab')
 for x,face in ((1238,'east'),(1242,'west')):p.corbel(x,80,-1037,face)
 p.features[p.group]='Paired longitudinal workshop ribs and short cross-blocking, leaving a higher central working bay rather than copying the royal coffer.'

 p.group='north-lodge';center=-1196
 for x in (1211,1215):
  p.corbel(x,71,center-5,'north')
  for y,part in ((72,'lower'),(73,'middle'),(74,'upper')):p.column(x,y,center-5,part)
 for x in range(1211,1216):
  if x==1213:p.put(x,75,center-5,'chipped:carved_stripped_spruce_log',axis='x')
  else:p.put(x,75,center-5,'mythrais:slim_lintel_dark_oak',facing='north',half='bottom',shape='straight',waterlogged=False)
 for x in (1212,1214):
  p.stairs(x,72,center-4,'minecraft:dark_oak_stairs','south',half='bottom',niche=True)
  p.stairs(x,73,center-4,'minecraft:dark_oak_stairs','south',niche=True)
 p.features[p.group]='Carved engaged rear timber surround with wall-rooted narrow supports, jointed cornice and paired real half-block blind alcoves; corner framing and interior retained.'

 p.group='south-lodge';center=-1091
 for x in (1211,1215):p.corbel(x,74,center-5,'north')
 for x in range(1211,1216):
  if x==1213:p.put(x,75,center-5,'chipped:crossed_dark_oak_planks')
  else:p.put(x,75,center-5,'minecraft:dark_oak_slab',type='bottom',waterlogged=False)
 for x in (1212,1214):
  p.stairs(x,72,center-4,'minecraft:spruce_stairs','south',half='bottom',niche=True)
  p.stairs(x,73,center-4,'minecraft:spruce_stairs','south',niche=True)
  p.put(x,71,center-5,'chipped:boxed_spruce_planks')
 p.features[p.group]='Lower practical signal-store recesses with separate projecting sill blocks and a restrained supported timber awning; a distinct rear composition rather than duplicated posts.'
 return p


def validate(p):
 if set(p.blocks)!=set(p.before) or set(p.blocks)&p.fixed or set(p.blocks)&p.snapshot.protected:raise UserError('Existing protected state entered the proposal')
 material={}
 for kind,original in p.originals.items():
  composed=dict(original);composed.update({q:v for q,v in p.blocks.items() if (q[2]>-1080)==(kind=='castle')})
  material[kind]=require_material_rule(composed,'Complete '+kind+' with secondary relief')
  require_outdoor_rule(composed,'Complete authored '+kind+' with secondary relief')
 rooted=set();queue=deque()
 for q in p.blocks:
  for d in NEIGHBORS:
   n=tuple(a+b for a,b in zip(q,d))
   if n not in p.blocks:
    old=p.snapshot.state(n)
    if base(old) not in VOID|{'minecraft:water','minecraft:lava'}:rooted.add(q);p.supports[n]=old;queue.append(q);break
 while queue:
  q=queue.popleft()
  for d in NEIGHBORS:
   n=tuple(a+b for a,b in zip(q,d))
   if n in p.blocks and n not in rooted:rooted.add(n);queue.append(n)
 if rooted!=set(p.blocks):raise UserError('Secondary relief has no retained face-connected structural support')
 for bracket,support in p.brackets:
  value=p.at(support)
  if base(value) in VOID or base(value).endswith('_slab') and properties(value).get('type')=='top':raise UserError('A bracket must meet the actual beam underside; no half-block floating gap')
 for pos,value in p.blocks.items():
  def stairlike(state):
   schema=p.registry['blocks'].get(base(state),{})
   return 'straight' in schema.get('shape',()) and 'top' in schema.get('half',()) and 'facing' in schema
  if not stairlike(value):continue
  own=properties(value)
  for dx,dz in ((1,0),(-1,0),(0,1),(0,-1)):
   neighbor=p.at((pos[0]+dx,pos[1],pos[2]+dz));other=properties(neighbor)
   if stairlike(neighbor) and own.get('half')==other.get('half') and (own.get('facing') in ('north','south'))!=(other.get('facing') in ('north','south')):raise UserError('Native perpendicular stair join requires explicit authored/native review')
 if set(p.groups)!=set(ENVELOPES):raise UserError('An audited room or rear face is missing')
 return {'whole_composite_material_checks':material,'positions':len(p.blocks),'new_saved_air_relief':sum(base(v) in VOID for v in p.before.values()),'blind_niche_wall_cells':sum(base(v) not in VOID for v in p.before.values()),'all_saved_BEs_preserved':True,'old_inventory_tags_replayed':0,'entity_commands':0,'rooted_geometry':len(rooted),'brackets_without_half_block_gap':len(p.brackets),'new_perpendicular_stair_join_candidates':0,'actual_native_models_joins_and_art':'PENDING actual settled state, same-room/facade graphical views and normal walking'}


def payload(registry,backup_sha,blocks,name):
 palette=sorted(set(blocks.values()));index={v:i for i,v in enumerate(palette)}
 return {'format':'awft-native-settlement:1','name':name,'created':utcnow(),'seed':registry['seed'],'world_path':registry['world_path'],'backup_sha256':backup_sha,'bounds':[min(q[0] for q in blocks),min(q[2] for q in blocks),max(q[0] for q in blocks),max(q[2] for q in blocks)],'palette':palette,'blocks':[[*q,index[v]] for q,v in sorted(blocks.items())],'block_entities':[],'commands':[],'landmarks':[]}


def prepare(home,checkpoint_id,checkpoint_sha):
 home=Path(home).resolve()
 if not home.is_relative_to(Path(r'D:\A World for Two\staging\world-tests')):raise UserError('Owned artistic staging home only')
 receipt=read_json(home/'dashboard/settlement/backup-receipt.json');owner=read_json(home/'dashboard/artistic-owner.json')
 admit_owner(home,owner,receipt,checkpoint_id,checkpoint_sha)
 backups=Backups(Layout(home),None,None);archive=backups.path(checkpoint_id)
 if digest(archive)!=checkpoint_sha:raise UserError('Stopped checkpoint bytes differ')
 members,total=backups.verify_archive(archive)
 if total>512*1024**2 or len(members['files'])>4096:raise UserError('Finite saved input exceeded')
 registry_path=home/'dashboard/settlement/registry.json';registry=read_json(registry_path);originals={'castle':{},'bridge':{}};fixed=set();inputs=[]
 records=[('castle',name,sha) for name,sha in INPUTS['castle']]+list(SOURCES)
 for kind,relative,sha in records:
  path=home/'staging'/relative
  if path.stat().st_size>16*1024**2 or digest(path)!=sha:raise UserError('Exact authored/native-corrected predecessor required')
  plan=read_json(path)
  if any(plan[k]!=registry[k] for k in ('seed','world_path')):raise UserError('Wrong source world')
  originals[kind].update(decode(plan));fixed.update(tuple(row['pos']) for row in plan['block_entities']);inputs.append({'kind':kind,'file':relative,'sha256':sha})
 routes=read_json(home/'staging/prototype-castle-palace-e6ffcde57520b8cb/manifest.json')['world_routes']
 snapshot=BackupWorld(home,receipt,registry)
 try:
  # Actual current full composites, including normal native joins; no source
  # placeholder is silently adopted as a current saved-world observation.
  originals={kind:{q:snapshot.state(q) for q in old} for kind,old in originals.items()}
  p=construct(Secondary(registry,snapshot,originals,fixed,routes));proof=validate(p);outputs={};groups=[]
  for group,positions in p.groups.items():
   after={q:p.blocks[q] for q in positions};before={q:p.before[q] for q in positions}
   for suffix,blocks in (('depth',after),('before-VERIFY-ONLY',before)):
    outputs[group+'-'+suffix+'.json']=(json.dumps(payload(registry,checkpoint_sha,blocks,group+' '+suffix),ensure_ascii=False,separators=(',',':'))+'\n').encode()
   groups.append({'name':group,'positions':len(positions),'feature':p.features[group],'bounds':list(ENVELOPES[group])})
  outputs['supports-VERIFY-ONLY.json']=(json.dumps(payload(registry,checkpoint_sha,p.supports,'Retained support/ceiling/facade structure - VERIFY ONLY'),separators=(',',':'))+'\n').encode()
  cameras=[]
  for name,(xa,ya,za,xb,yb,zb) in ENVELOPES.items():
   if 'lodge' in name:cameras.append({'name':name+'-rear-quarter','feet':[(xa+xb)/2+2.5,73,za-6.5],'look_at':[(xa+xb)/2+.5,73.5,zb],'mode':'planned free-camera pose; no walking claim'})
   else:
    floor=82 if name=='gallery' else 72
    options=[(x,z) for x in range(xa,xb+1) for z in range(za,zb+1) if base(snapshot.state((x,floor,z))) not in VOID|{'minecraft:water'} and base(snapshot.state((x,floor+1,z))) in VOID|{'minecraft:pink_carpet'} and base(snapshot.state((x,floor+2,z))) in VOID]
    if not options:raise UserError('No actual clear room camera approach')
    x,z=min(options,key=lambda q:abs(q[0]-(xa+xb)/2)+abs(q[1]-(za+zb)/2))
    cameras.append({'name':name+'-ceiling-upward','feet':[x+.5,floor+1.1,z+.5],'look_at':[(xa+xb)/2+.5,yb+.5,(za+zb)/2+.5],'mode':'saved-voxel clear proposed pose; native collision/visual review pending'})
  manifest={'format':'awft-secondary-depth:1','status':'STAGED source/preimage only; native placement, survival/joins and actual artistic acceptance pending','checkpoint_id':checkpoint_id,'checkpoint_sha256':checkpoint_sha,'source_sha256':digest(Path(__file__)),'registry_sha256':digest(registry_path),'inputs':inputs,'sources':snapshot.sources,'proof':proof,'groups':groups,'cameras':cameras,'bracket_contacts':[{'bracket':list(q),'beam_underside_voxel':list(support),'native_model_contact_pending':True} for q,support in p.brackets],'new_geometry_writes_to_world':0,'block_entity_tags_replayed':0,'verification_only_files':[n for n in outputs if 'VERIFY-ONLY' in n],'files':{n:{'sha256':hashlib.sha256(v).hexdigest(),'bytes':len(v)} for n,v in outputs.items()}}
  outputs['manifest.json']=(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n').encode()
  if sum(map(len,outputs.values()))>MAX_OUTPUT:raise UserError('Finite secondary proposal output exceeded')
  guard(1024**2,MAX_OUTPUT);folder=home/'staging'/('artistic-secondary-depth-'+str(time.time_ns()));folder.mkdir()
  for name,raw in outputs.items():
   with (folder/name).open('xb') as stream:stream.write(raw)
  return {'directory':str(folder),'manifest_sha256':digest(folder/'manifest.json'),'proof':proof,'groups':groups}
 finally:snapshot.close()

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--home',required=True,type=Path);p.add_argument('--checkpoint-id',required=True);p.add_argument('--checkpoint-sha',required=True);a=p.parse_args();print(json.dumps(prepare(a.home,a.checkpoint_id,a.checkpoint_sha),indent=2))
