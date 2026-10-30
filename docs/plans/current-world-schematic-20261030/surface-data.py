"""Bounded immutable-snapshot surface map, no world writes or native commands."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[3]))
import json,zipfile,hashlib,zlib,time,math
from collections import Counter
from PIL import Image
from tools.settlement_attractions import NBTReader,unpack_section
OUT=Path(__file__).resolve().parent
SRC=Path(r'D:\A World for Two\staging\world-tests\20261027T053650Z-artistic\backups\20261030T155547Z-096bdd.zip')
EXPECTED='82cf88ee5bbea9616767109506739e73c6b04492bcc4adc9b90860bb4f10ac09'
BOUNDS=(900,-1540,1455,-680)
COLORS={'water':'#9bb7b1','ground':'#d8d0ae','context':'#c4c0a4','greenery':'#33704c','unknown':'#e4dfcf'}
def sha(raw):return hashlib.sha256(raw).hexdigest()
h=hashlib.sha256()
with SRC.open('rb') as f:
 while raw:=f.read(1024*1024):h.update(raw)
assert h.hexdigest()==EXPECTED
x0,z0,x1,z1=BOUNDS
im=Image.new('RGB',(x1-x0+1,z1-z0+1),COLORS['unknown']);px=im.load()
counts=Counter();regions=[];failed=[];chunks=0;started=time.monotonic()
AIR={'minecraft:air','minecraft:cave_air','minecraft:void_air'}
NATURAL={'stone','dirt','grass_block','coarse_dirt','rooted_dirt','podzol','mycelium','mud','packed_mud','sand','red_sand','sandstone','red_sandstone','gravel','clay','andesite','granite','diorite','calcite','tuff','deepslate','bedrock','snow','snow_block','powder_snow','ice','packed_ice','blue_ice','dripstone_block','moss_block'}
VEG=('leaves','sapling','grass','flower','bush','petal','fern','vine','lily','roots','tendril','mushroom','berry','berries','orchid','tulip','dandelion','poppy','allium','azalea','peony','sunflower','lilac','bamboo','cattail','reed','hedge','lavender','clover','rose','lotus','wisteria','blossom','seagrass','kelp','cane','moss_carpet')
def classify(s):
 b=s.split('[',1)[0];ns,_,name=b.partition(':')
 if b in AIR:return 'unknown'
 if b in ('minecraft:water','minecraft:ice','minecraft:packed_ice','minecraft:blue_ice'):return 'water'
 if name in NATURAL or name.endswith('_ore'):return 'ground'
 if name=='bamboo_block' or {'planks','stairs','slab','door','trapdoor','roof','beam','log','wood','fence','gate','window','shutter','pillar','post','bricks','panel','sign','bookshelf','cabinet','shelf','table','chair','bench','crate','barrel','chest','counter','bed','lantern','lamp','wall','ladder','railing'}.intersection(name.split('_')):return 'context'
 if any(t in name for t in VEG):return 'greenery'
 if ns in ('regions_unexplored','biomesoplenty') and any(t in name for t in ('dirt','soil','rock','stone','silt','sand','peat','chalk')):return 'ground'
 return 'context'
with zipfile.ZipFile(SRC) as a:
 mf=json.loads(a.read('awft-backup.json'));files={r['path']:r for r in mf['files']}
 for rx in range(x0//512,x1//512+1):
  for rz in range(z0//512,z1//512+1):
   name=f'world/RosewaterArtistic/region/r.{rx}.{rz}.mca'
   rec=files.get(name)
   if not rec:continue
   raw=a.read(name);assert len(raw)==rec['size'] and sha(raw)==rec['sha256']
   regions.append({'region':[rx,rz],'sha256':rec['sha256'],'bytes':len(raw)})
   for cz in range(max(z0//16,rz*32),min(z1//16,rz*32+31)+1):
    for cx in range(max(x0//16,rx*32),min(x1//16,rx*32+31)+1):
     idx=((cz&31)*32+(cx&31))*4;loc=int.from_bytes(raw[idx:idx+4],'big');o=(loc>>8)*4096
     if not loc or o+5>len(raw):continue
     try:
      ln=int.from_bytes(raw[o:o+4],'big');comp=raw[o+4];packed=raw[o+5:o+4+ln]
      if comp==2:d=zlib.decompress(packed)
      elif comp==1:d=zlib.decompress(packed,31)
      elif comp==3:d=packed
      else:raise ValueError('Unsupported compression')
      c=NBTReader(d).read()
      if (c.get('xPos'),c.get('zPos'))!=(cx,cz) or c.get('Status') not in ('minecraft:full','full'):continue
      heights=c.get('Heightmaps',{}).get('WORLD_SURFACE');sections={s['Y']:s for s in c.get('sections',[])}
      if not heights:continue
      # Minecraft 1.21.1 has 384 blocks; heightmap stores 9-bit noncrossing words.
      bits=9;per=64//bits;mask=(1<<bits)-1;min_y=c.get('yPos',-4)*16
      for lz in range(16):
       z=cz*16+lz
       if not z0<=z<=z1:continue
       for lx in range(16):
        x=cx*16+lx
        if not x0<=x<=x1:continue
        n=lz*16+lx;y=((heights[n//per]>>((n%per)*bits))&mask)+min_y-1
        state=unpack_section(sections.get(y//16,{}),x,y,z)
        # Ignore the seasonal snow cap so planted/architectural surfaces remain readable.
        if state.split('[',1)[0]=='minecraft:snow':
         y-=1;state=unpack_section(sections.get(y//16,{}),x,y,z)
        key=classify(state);px[x-x0,z-z0]=tuple(bytes.fromhex(COLORS[key][1:]));counts[key]+=1
      chunks+=1
     except Exception as e:failed.append({'chunk':[cx,cz],'reason':type(e).__name__+':'+str(e)[:120]})
im.save(OUT/'surface-data.png',optimize=True)
counts['unknown']=(x1-x0+1)*(z1-z0+1)-sum(v for k,v in counts.items() if k!='unknown')
proof={'format':'awft-immutable-top-surface-map:1','bounds_xz':BOUNDS,'pixels_per_block':1,'north_up':True,'checkpoint':'20261030T155547Z-096bdd','checkpoint_sha256':EXPECTED,'checkpoint_at':'2026-10-30T15:55:54.404825+00:00','world_save_not_modified':True,'native_commands':0,'method':'Saved WORLD_SURFACE heightmap, exact block at highest surface, seasonal snow layer omitted; category is block-name based, not construction ownership. Current player changes after checkpoint are not included.','colors':COLORS,'regions':regions,'full_chunks_read':chunks,'columns_by_category':dict(counts),'failed_chunks':failed,'png_sha256':sha((OUT/'surface-data.png').read_bytes()),'elapsed_seconds':round(time.monotonic()-started,3)}
(OUT/'surface-data.json').write_text(json.dumps(proof,indent=2)+'\n')
print(json.dumps({k:proof[k] for k in ('full_chunks_read','columns_by_category','png_sha256','elapsed_seconds')}))
