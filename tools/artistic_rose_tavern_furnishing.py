"""Original human-scale Drowned Rose furnishing/light proposal; no world calls.

Uses actual native photos as the critique and an authenticated stopped backup as
the only preimage. Existing inventories/default block entities are never replayed.
"""
from __future__ import annotations

import argparse
from collections import deque
import hashlib
import json
from pathlib import Path
import time

from control_room.backups import Backups
from control_room.common import Layout, UserError, digest, read_json, utcnow
from tools.artistic_maritime_depth import admit_owner, key, states
from tools.artistic_materials import require_material_rule
from tools.artistic_pirate_spit import tag_snbt
from tools.playtest import guard
from tools.settlement_attractions import BackupWorld


AIR='minecraft:air';VOID={AIR,'minecraft:cave_air','minecraft:void_air'}
MAX_OUTPUT=16*1024**2
BASE='staging/artistic-pirate-spit-byte-slots-1793124362042040500/drowned-rose-VERIFY-ONLY.json'
BASE_SHA='f646d9ed046f603dc4e55c3f564949dba3a45be733dbd8c88ebba9cf48d85486'
DEPTH='staging/artistic-maritime-depth-1793125315305851100/drowned-rose-depth.json'
DEPTH_SHA='be443dbe28d6608a9348a58dcfb8b4b2766eea54ce47a690314f22f5c08b3b98'
SPIT_MANIFEST='staging/artistic-pirate-spit-byte-slots-1793124362042040500/manifest.json'
BOUNDS=(1288,65,-1289,1311,72,-1270)
FLOOR_LAMPS=((1297,-1288),(1306,-1288),(1308,-1282),(1307,-1278),
             (1306,-1271),(1296,-1271),(1300,-1276),(1300,-1282),(1290,-1281))
PHOTO_CRITIQUE=(
    {'name':'rose-tavern-bar','sha256':'20a7638f1e57b8ee71293446f534325a5c242d7acf2cc7e7a15a0d1e6a20efa2','feet':[1303.5,65,-1271.5],'look_at':[1295,67,-1278]},
    {'name':'rose-tavern-capstan','sha256':'a13c81556df66e22324ff0d9009c227f5952f59deffff8c1eb8423fc895bfe58','feet':[1303.5,65,-1283.5],'look_at':[1302,74,-1279]},
    {'name':'rose-tavern-front','sha256':'d7ceabcc9b3451c9d38af330d1102e5550d7fa6b731a64d1ce6c542c6ab71219','feet':[1302.5,64,-1263.5],'look_at':[1302,75,-1269]},
)


class Furnishing:
    def __init__(self,registry,snapshot,base,protected=(),routes=()):
        self.registry,self.snapshot,self.base=registry,snapshot,dict(base)
        self.protected=set(protected);self.routes=list(routes)
        self.clearance={(x,y+dy,z) for row in self.routes for x,y,z in row['floor_cells'] for dy in (1,2)}
        # Keep a two-wide main walking lane and the actual stair approach.
        self.clearance.update((x,y,z) for x in (1302,1303) for z in range(-1284,-1269) for y in (65,66))
        self.clearance.update((x,y,z) for x in (1307,1308,1309) for z in (-1271,-1270) for y in (66,67))
        self.blocks,self.before,self.tags={},{},{}
        self.scenes=[];self.lights=[];self.supports={};self.seat_approaches=[]

    def at(self,pos):return self.blocks[pos] if pos in self.blocks else self.snapshot.state(pos)

    def column(self,x,y,z,part,facing):
        props={'colour':0,'facing':facing}
        if part!='middle':props['mirrored']=False
        self.put(x,y,z,'mythrais:decorated_column_'+part+'_small_dark_oak',**props)

    def state(self,value,**props):
        native=self.registry['blocks'].get(value)
        if native is None:raise UserError('Missing actual furnishing block: '+value)
        for name,choice in props.items():
            if name not in native or str(choice).lower() not in native[name]:
                raise UserError('Unsupported native furnishing state: '+value+' '+name)
        return value+('['+','.join(name+'='+str(choice).lower() for name,choice in sorted(props.items()))+']' if props else '')

    def put(self,x,y,z,value,**props):
        pos=x,y,z
        if any(type(n) is not int for n in pos) or not all(BOUNDS[n]<=pos[n]<=BOUNDS[n+3] for n in range(3)):
            raise UserError('Furnishing exceeds the small interior envelope')
        if pos in self.clearance:raise UserError('Keep central, service, gallery and stair body space: '+str(pos))
        old=self.snapshot.state(pos)
        if pos in self.protected or pos in self.snapshot.protected:
            raise UserError('An existing tagged/default block entity is immutable: '+str(pos))
        if key(old) not in VOID:
            raise UserError('Do not replace existing furniture, fixtures, roof, glazing or stock: '+str(pos)+' '+key(old))
        after=self.state(value,**props)
        if pos in self.blocks and self.blocks[pos]!=after:raise UserError('Two furnishing scenes overlap: '+str(pos))
        self.blocks[pos]=after;self.before[pos]=old
        if len(self.blocks)>900:raise UserError('Split this small furnishing proposal')

    def support(self,pos):
        value=self.at(pos)
        if key(value) in VOID|{'minecraft:water'}:raise UserError('A new small fitting has no real support: '+str(pos))
        if pos not in self.blocks:self.supports[pos]=value

    def stand(self,x,y,z):
        self.support((x,y-1,z));self.put(x,y,z,'chipped:detailed_dark_oak_planks')

    def lamp(self,x,y,z,*,hanging=False):
        self.support((x,y+1 if hanging else y-1,z))
        self.put(x,y,z,'minecraft:lantern',hanging=hanging,waterlogged=False)
        self.lights.append({'pos':[x,y,z],'native_block':'minecraft:lantern','kind':'compact warm lantern','measured_light':'PENDING actual native review'})

    def chair(self,x,y,z,facing,color='brown'):
        self.support((x,y-1,z));self.put(x,y,z,'handcrafted:dark_oak_chair',facing=facing,color=color,waterlogged=False)

    def table(self,x,y,z):
        self.support((x,y-1,z));self.put(x,y,z,'handcrafted:dark_oak_table',color='none',shape='single',waterlogged=False)

    def drink(self,x,y,z):
        self.support((x,y-1,z));self.put(x,y,z,'supplementaries:goblet',light_level=0,waterlogged=False)

    def candle(self,x,y,z):
        self.support((x,y-1,z));self.put(x,y,z,'supplementaries:candle_holder',candles=3,face='floor',facing='north',lit=True,waterlogged=False)

    def shelf(self,x,y,z,facing):
        dx,dz={'east':(-1,0),'west':(1,0),'north':(0,1),'south':(0,-1)}[facing]
        self.support((x+dx,y,z+dz))
        self.put(x,y,z,'handcrafted:dark_oak_shelf',facing=facing,shape='single',type=2)

    def sign(self,x,y,z,facing,lines):
        dx,dz={'east':(-1,0),'west':(1,0),'north':(0,1),'south':(0,-1)}[facing]
        self.support((x+dx,y,z+dz))
        self.put(x,y,z,'minecraft:dark_oak_wall_sign',facing=facing,waterlogged=False)
        self.tags[x,y,z]={'front_text':{'messages':[json.dumps({'text':line},ensure_ascii=False,separators=(',',':')) for line in lines],
                                      'color':'white','has_glowing_text':True},'is_waxed':True}

    def scene(self,name,features,approaches):
        self.scenes.append({'name':name,'features':features,'approaches':[list(pos) for pos in approaches]})
        self.seat_approaches.extend(approaches)


def construct(p):
    # Human eye-level pools, separate from the preserved high capstan lights.
    for x,z in FLOOR_LAMPS:p.stand(x,65,z);p.lamp(x,66,z)
    p.support((1293,69,-1281));p.put(1293,68,-1281,'minecraft:chain',axis='y',waterlogged=False);p.lamp(1293,67,-1281,hanging=True)

    # Three-piece irregular common table: separated real tables joined by a
    # stable top slab. They do not rely on guessed automatic table-join states.
    for z in (-1279,-1277):p.table(1298,65,z);p.drink(1298,66,z)
    p.put(1298,65,-1278,'minecraft:dark_oak_slab',type='top',waterlogged=False)
    p.put(1298,66,-1278,'farmersdelight:roast_chicken_block',facing='south',servings=4)
    for x,facing in ((1297,'east'),(1299,'west')):
        for z in (-1279,-1277):p.chair(x,65,z,facing,'green' if x==1297 else 'red')
    # Two slender, carved posts and three short lintels make a little social
    # room under the giant nave without concealing the high chandelier.
    for x in (1296,1300):
        for y,part in ((65,'lower'),(66,'middle'),(67,'upper')):
            p.column(x,y,-1279,part,'south')
    for x in range(1296,1301):
        p.put(x,68,-1279,'mythrais:slim_lintel_dark_oak',facing='south',half='bottom',shape='straight',waterlogged=False)
    p.put(1298,67,-1279,'mythrais:single_gothic_arch_upper_dark_oak',colour=0,facing='south',shape=0)
    p.scene('Returning crews supper table',['Four actual colored chairs, two wood tables and a flush serving leaf','Real four-serving roast, drink goblets, low nearby lanterns and slender carved Mythrais frame'],
            [(1296,64,-1277),(1300,64,-1277),(1298,64,-1276)])

    # A cushioned conversation bay under the existing gallery coffers.
    p.table(1308,65,-1284)
    p.put(1309,65,-1284,'handcrafted:dark_oak_side_table',facing='south',color='none',waterlogged=False)
    p.put(1308,66,-1284,'farmersdelight:rice_roll_medley_block',facing='west',servings=8)
    p.drink(1309,66,-1284)
    p.put(1310,65,-1284,'handcrafted:dark_oak_couch',facing='west',color='red',shape='single',waterlogged=False)
    p.put(1310,65,-1286,'handcrafted:dark_oak_bench',facing='west',color='green',shape='single',waterlogged=False)
    p.chair(1307,65,-1284,'east','green')
    p.put(1311,68,-1283,'mythrais:small_curved_corbel_dark_oak',facing='west',shape=0)
    p.put(1311,68,-1285,'mythrais:gothic_corbel_single_dark_oak',facing='west',shape=0)
    p.scene('Lanterns beneath the lancets',['Asymmetric red couch, separate green bench and facing chair','Shared supper platter, drinks, carved reveal brackets and existing overhead coffers'],
            [(1307,64,-1283),(1309,64,-1282),(1310,64,-1285)])

    # Existing front table keeps every old block. Add two real seats and a
    # small light on an already-present side table only where saved air permits.
    p.chair(1306,65,-1274,'west','red');p.chair(1305,65,-1275,'south','green')
    p.candle(1304,66,-1274)
    p.scene('The first-round table',['Existing table/chair/goblet retained, two extra seats and warm three-candle side light','A comfortable small group opposite the entrance, clear of the gallery stair'],
            [(1306,64,-1273),(1305,64,-1276)])

    # Full-height barback composition: posts, low carved bases, bottles/books,
    # higher wall shelves and a readable chalk notice. Service aisle x1294 stays.
    for z in (-1279,-1273):
        for y,part in ((65,'lower'),(66,'middle'),(67,'upper')):
            p.column(1292,y,z,part,'east')
    for z in (-1278,-1276,-1274):
        p.stand(1292,65,z)
        if z!=-1278:p.shelf(1292,68,z,'east')
    p.put(1292,66,-1278,'lfpirates:ship_in_bottle',facing='east',waterlogged=False)
    p.put(1292,66,-1276,'handcrafted:stackable_book',books=3,facing='east',seed=4)
    p.drink(1292,66,-1274)
    p.put(1292,69,-1276,'handcrafted:stackable_book',books=2,facing='east',seed=12)
    p.put(1292,69,-1274,'lfpirates:ship_in_bottle',facing='east',waterlogged=False)
    p.stand(1292,65,-1275);p.lamp(1292,66,-1275)
    p.sign(1292,67,-1275,'east',('THE ROSE','Supper & songs','Catch at dusk','Mind the tide'))
    p.scene('The Rose barback',['Carved Mythrais post ends, low paneled display bases and high shelves','Ship models, logbooks, goblet and readable small glowing-ink notice; original pantry/chart stock untouched'],
            [(1293,64,-1276),(1293,64,-1278)])

    # Music and salvage trophies beside, never on, the actual piano/lectern.
    p.stand(1307,65,-1288);p.put(1307,66,-1288,'chipped:crossed_dark_oak_planks')
    p.put(1307,67,-1288,'minecraft:skeleton_skull',rotation=8,powered=False,waterlogged=False)
    p.support((1306,64,-1287));p.put(1306,65,-1287,'handcrafted:dark_oak_side_table',facing='west',color='none',waterlogged=False)
    p.put(1306,66,-1287,'handcrafted:stackable_book',books=2,facing='west',seed=6)
    p.sign(1307,67,-1289,'south',('NIGHT WATCH','Songs at dusk','Charts & tales','Piano clear!'))
    p.scene('The night-watch music corner',['Preserved playable piano/lectern and existing stage seating','Small captain-skull/logbook display, readable notice and nearby low warm lantern'],
            [(1306,64,-1286),(1307,64,-1287)])

    # Separate warm gallery corners. They do not depend on a huge ceiling lamp.
    for x,z in ((1296,-1284),(1310,-1283)):
        p.stand(x,70,z);p.lamp(x,71,z)
    p.table(1295,70,-1283);p.put(1295,71,-1283,'handcrafted:stackable_book',books=3,facing='east',seed=7)
    p.chair(1294,70,-1283,'east','green')
    p.scene('The west gallery reading pocket',['Small warm lamp, real book table and extra upholstered chair','Retained couches, globe and chart barrel nearby'],[(1296,69,-1283)])
    p.scene('The east gallery corner',['Separate compact warm lamp beside the retained gallery table','Keep the gallery crossing and stair arrival open'],[(1309,69,-1283)])
    return p


def validate(p):
    composite={pos:p.snapshot.state(pos) for pos in p.base};composite.update(p.blocks)
    material=require_material_rule(composite,'Drowned Rose complete furnished/depth composite')
    for pos in p.clearance:
        if pos in p.blocks:raise UserError('Final furnishing obstructs retained circulation')
    # A coarse rooted-voxel proof supplements each lamp/table's direct support
    # check. Native model collision, survival and join shape remain separate.
    rooted=set();queue=deque();steps=((1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1))
    for pos in p.blocks:
        for step in steps:
            neighbor=tuple(a+b for a,b in zip(pos,step))
            if neighbor not in p.blocks:
                value=p.snapshot.state(neighbor)
                if key(value) not in VOID|{'minecraft:water','minecraft:lava'}:
                    rooted.add(pos);p.supports[neighbor]=value;queue.append(pos);break
    while queue:
        pos=queue.popleft()
        for step in steps:
            neighbor=tuple(a+b for a,b in zip(pos,step))
            if neighbor in p.blocks and neighbor not in rooted:rooted.add(neighbor);queue.append(neighbor)
    if rooted!=set(p.blocks):raise UserError('A new fitting cluster has no retained voxel support path')
    # Every vignette has an actual two-high adjacent approach. This checks the
    # final furnishings, not a route observation made before adding chairs.
    for x,floor,z in p.seat_approaches:
        if key(p.at((x,floor,z))) in VOID|{'minecraft:water'}:raise UserError('Scene approach lacks retained floor')
        for dy in (1,2):
            if key(p.at((x,floor+dy,z))) not in VOID|{'minecraft:red_carpet','minecraft:brown_carpet'}:
                raise UserError('Final chair/display blocks an intimate scene approach: '+str((x,floor+dy,z)))
    if any(key(p.blocks.get(tuple(row['pos']),AIR))!='minecraft:lantern' for row in p.lights):raise UserError('Light metadata must refer to an actual new lantern')
    if len([row for row in p.lights if row['pos'][1]<=68])<10:raise UserError('The high capstan cannot count as new human-level lighting')
    if any(key(p.blocks.get(pos,AIR))!='minecraft:dark_oak_wall_sign' for pos in p.tags):raise UserError('Only newly placed notice signs receive new explicit tags')
    if any('Items' in json.dumps(tag) for tag in p.tags.values()):raise UserError('This furnishing pass never adds/replays inventory data')
    return {'material':material,'new_positions':len(p.blocks),'new_notice_tags':len(p.tags),
            'existing_block_entity_tags_replayed':0,'low_warm_lanterns':sum(row['pos'][1]<=68 for row in p.lights),'gallery_corner_lanterns':sum(row['pos'][1]>=70 for row in p.lights),
            'voxel_rooted_new_fittings':len(rooted),'retained_support_cells':len(p.supports),
            'native_fitting_survival_shapes_seating_and_light_levels':'PENDING real settled/native visual and walking review',
            'entities':0,'commands':0,'native_lighting_and_artistic_acceptance':'PENDING actual same-shader floor/night views and walking'}


def payload(p,blocks,name,backup_sha,*,tags=False):
    palette=sorted(set(blocks.values()));look={value:n for n,value in enumerate(palette)}
    row={'format':'awft-native-settlement:1','name':name,'created':utcnow(),'seed':p.registry['seed'],
         'world_path':p.registry['world_path'],'backup_sha256':backup_sha,
         'bounds':[min(x for x,y,z in blocks),min(z for x,y,z in blocks),max(x for x,y,z in blocks),max(z for x,y,z in blocks)],
         'palette':palette,'blocks':[[*pos,look[value]] for pos,value in sorted(blocks.items())],
         'block_entities':[{'pos':list(pos),'nbt':tag_snbt(tag)} for pos,tag in sorted(p.tags.items())] if tags else [],
         'commands':[],'landmarks':[]}
    return (json.dumps(row,separators=(',',':'),ensure_ascii=False)+'\n').encode()


def prepare(home,checkpoint_id,checkpoint_sha):
    home=Path(home).resolve();layout=Layout(home)
    if not home.is_relative_to(Path(r'D:\A World for Two\staging\world-tests')):raise UserError('Owned artistic staging home only')
    owner=read_json(home/'dashboard/artistic-owner.json',{});receipt=read_json(home/'dashboard/settlement/backup-receipt.json',{})
    admit_owner(home,owner,receipt,checkpoint_id,checkpoint_sha)
    backups=Backups(layout,None,None);archive=backups.path(checkpoint_id)
    if digest(archive)!=checkpoint_sha:raise UserError('Exact stopped archive bytes differ')
    index,total=backups.verify_archive(archive)
    if total>512*1024**2 or len(index['files'])>4096:raise UserError('Finite saved input exceeded')
    registry=read_json(home/'dashboard/settlement/registry.json');base={};protected=set()
    for photo in PHOTO_CRITIQUE:
        image=home/'logs/visual-review/c41-art'/(photo['name']+'.png')
        if image.stat().st_size>8*1024**2 or digest(image)!=photo['sha256']:raise UserError('Untouched native critique photograph differs')
    for relative,expected in ((BASE,BASE_SHA),(DEPTH,DEPTH_SHA)):
        path=home/relative
        if path.stat().st_size>4*1024**2 or digest(path)!=expected:raise UserError('Exact placed tavern/depth source differs')
        row=read_json(path)
        if (row['seed'],row['world_path'])!=(registry['seed'],registry['world_path']):raise UserError('Wrong native tavern world')
        base.update(states(row));protected.update(tuple(value['pos']) for value in row['block_entities'])
    routes=[row for row in read_json(home/SPIT_MANIFEST)['routes'] if row['name'].startswith('Drowned Rose')]
    snapshot=BackupWorld(home,receipt,registry)
    try:
        p=construct(Furnishing(registry,snapshot,base,protected,routes));proof=validate(p)
        outputs={'furnishing.json':payload(p,p.blocks,'The Drowned Rose — lived-in warm scenes',checkpoint_sha,tags=True),
                 'before.json':payload(p,p.before,'Exact saved air before Rose furnishings',checkpoint_sha),
                 'supports-VERIFY-ONLY.json':payload(p,p.supports,'Retained floors/walls/roof supports — VERIFY ONLY',checkpoint_sha)}
        record={'format':'awft-rose-tavern-furnishing:1','status':'STAGED SOURCE ONLY; actual lighting, seating, support and visual acceptance pending',
                'checkpoint_id':checkpoint_id,'checkpoint_sha256':checkpoint_sha,'source_sha256':digest(Path(__file__)),
                'base_sha256':BASE_SHA,'depth_sha256':DEPTH_SHA,'sources':snapshot.sources,'scenes':p.scenes,'lights':p.lights,'proof':proof,
                'native_before_photos_and_matched_cameras':PHOTO_CRITIQUE,
                'additional_proposed_cameras':[{'name':'crew-supper-close','feet':[1300.5,65,-1276.5],'look_at':[1298,66,-1278]},
                                               {'name':'lancet-booth-close','feet':[1307.5,65,-1282.5],'look_at':[1310,66,-1284]},
                                               {'name':'gallery-reading-close','feet':[1309.5,70,-1282.5],'look_at':[1295,71,-1283]}],
                'preservation':'Only exact saved air receives new furnishings. Existing default/tagged BEs, stock, roof/capstan, galleries, glazing and furniture are never replayed.',
                'verification_only_files':['supports-VERIFY-ONLY.json'],
                'native_sequence':'Verify supports and before; place new furnishing plan once; settled state/new-sign checks; actual warm floor-level, bar, booth, stage/gallery and night screenshots plus walking. No giant lamp or shader/gamma change.',
                'files':{name:{'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)} for name,raw in outputs.items()}}
        outputs['manifest.json']=(json.dumps(record,indent=2,ensure_ascii=False)+'\n').encode()
        if sum(map(len,outputs.values()))>MAX_OUTPUT:raise UserError('Small furnishing output bound exceeded')
        guard(1024**2,MAX_OUTPUT);output=home/'staging'/('artistic-rose-furnishing-'+str(time.time_ns()));output.mkdir()
        for name,raw in outputs.items():
            with (output/name).open('xb') as stream:stream.write(raw)
        return {'directory':str(output),'manifest_sha256':digest(output/'manifest.json'),'proof':proof,'files':record['files']}
    finally:snapshot.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--home',type=Path,required=True)
    parser.add_argument('--checkpoint-id',required=True);parser.add_argument('--checkpoint-sha',required=True);args=parser.parse_args()
    print(json.dumps(prepare(args.home,args.checkpoint_id,args.checkpoint_sha),indent=2))
