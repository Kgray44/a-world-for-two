"""Stage a bounded watermill, pneumatic dispatch, player tube and passenger shuttle.

This authoring tool reads immutable verified backups, never the open world. It
does not execute commands, launch Minecraft, assemble a train or install a plan.
Fresh native before-state verification and functional commissioning are required.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import re
import struct
import tomllib
import uuid
import zipfile
import zlib
from collections import Counter
from pathlib import Path, PurePosixPath

from control_room.common import Layout, UserError, atomic_write, digest, read_json, utcnow
from control_room.storage import Storage
from tools.settlement_detail import base, load_context


AIR = 'minecraft:air'
BOUNDS = (1292, -1030, 1320, -904)
DETAIL_INDEX_SHA = 'd0926cb2a2ddab006cc046b7429817937303eb4e69e977d67773cf774854a357'
MAX_OUTPUT = 32 * 1024**2
MAX_POSITIONS = 45000
MAX_CHUNK = 8 * 1024**2
MAX_REGION = 32 * 1024**2
MOD_FILES = ('create-1.21.1-6.0.10.jar', 'overpressure-0.1.7.4.jar',
             'create_hypertube-0.6.0-NEOFORGE.jar', 'railways-0.2.1+neoforge-mc1.21.1.jar')
MOD_SHAS = ('ef87fe5709f1ba1f5b8bb20a2925b5afb4669e178fd6d8bf10c167759eefe37a',
            '9c03c26bc50c637dbe1d8b9e19e9c10218687c61d335b36588f11e54805c4cf7',
            '7bdb8979c7ff7d3b29f7a23771b6ae4870a6dcb7ce2e4a3214fdd6059aacace8',
            'b7636c8b1b0352ed1a130dfe67f8bb574e2fc08803ed1cda4d3ea00505193914')
NATURAL = {'minecraft:'+k for k in ('air','cave_air','void_air','grass_block','dirt',
           'coarse_dirt','rooted_dirt','stone','granite','diorite','andesite','gravel',
           'sand','sandstone','clay','short_grass','tall_grass','fern','large_fern',
           'dandelion','poppy','cornflower','azure_bluet','oxeye_daisy','allium',
           'pink_petals','snow','snow_block','dead_bush')}
NATURAL.update({'minecraft:'+k for k in ('water','coal_ore','copper_ore','iron_ore','lapis_ore')})
VEGETATION = {'regions_unexplored:grass_sprouts','farm_and_charm:wild_carrots',
              'farm_and_charm:wild_barley','farm_and_charm:wild_corn',
              'vinery:white_grape_bush','vinery:red_grape_bush'}
NATURAL.update(VEGETATION | {'create:zinc_ore'})


class NBTReader:
    """Small bounded big-endian NBT reader; no runtime package dependency."""
    def __init__(self, raw):
        if len(raw) > MAX_CHUNK:
            raise UserError('NBT exceeds the bounded chunk allocation')
        self.data = io.BytesIO(raw)
        self.nodes = 0

    def take(self, n):
        if n < 0 or n > MAX_CHUNK:
            raise UserError('Invalid NBT byte length')
        value = self.data.read(n)
        if len(value) != n:
            raise UserError('Truncated NBT')
        return value

    def number(self, code):
        return struct.unpack('>'+code, self.take(struct.calcsize(code)))[0]

    def string(self):
        return self.take(self.number('H')).decode('utf-8', errors='strict')

    def value(self, kind, depth=0):
        self.nodes += 1
        if depth > 48 or self.nodes > 300000:
            raise UserError('NBT nesting/node limit exceeded')
        if kind in (1,2,3,4,5,6):
            return self.number({1:'b',2:'h',3:'i',4:'q',5:'f',6:'d'}[kind])
        if kind == 8:
            return self.string()
        if kind in (7,11,12):
            count = self.number('i')
            size, code = {7:(1,'b'),11:(4,'i'),12:(8,'q')}[kind]
            if count < 0 or count*size > MAX_CHUNK:
                raise UserError('Invalid NBT array length')
            return list(struct.unpack('>'+str(count)+code, self.take(count*size)))
        if kind == 9:
            subtype, count = self.number('B'), self.number('i')
            if count < 0 or count > 100000 or count and subtype == 0:
                raise UserError('Invalid NBT list')
            return [self.value(subtype,depth+1) for _ in range(count)]
        if kind == 10:
            result = {}
            while True:
                child = self.number('B')
                if child == 0:
                    return result
                name = self.string()
                if name in result:
                    raise UserError('Duplicate NBT compound key')
                result[name] = self.value(child,depth+1)
        raise UserError('Unsupported NBT tag '+str(kind))

    def read(self):
        if self.number('B') != 10:
            raise UserError('A chunk must be a named NBT compound')
        self.string()
        value = self.value(10)
        if self.data.read(1):
            raise UserError('Trailing bytes after chunk NBT')
        return value


def unpack_section(section, x, y, z):
    states = section.get('block_states')
    if not states:
        return AIR
    palette = states.get('palette', [])
    if not 1 <= len(palette) <= 4096:
        raise UserError('Invalid saved block palette')
    index = 0
    if len(palette) > 1:
        bits = max(4,(len(palette)-1).bit_length())
        per_long = 64//bits
        values = states.get('data', [])
        if len(values) != math.ceil(4096/per_long):
            raise UserError('Invalid modern non-crossing block-state array')
        ordinal = (y&15)*256+(z&15)*16+(x&15)
        index = (values[ordinal//per_long] >> ((ordinal%per_long)*bits)) & ((1<<bits)-1)
    if index >= len(palette):
        raise UserError('Saved block palette index is invalid')
    row = palette[index]
    props = row.get('Properties', {})
    return row['Name']+('['+','.join(k+'='+str(v) for k,v in sorted(props.items()))+']' if props else '')


class BackupWorld:
    """Read only authenticated ZIP region entries; never extract or open live files."""
    def __init__(self, home, receipt, registry):
        home = Path(home)
        ident = receipt.get('id','')
        if not re.fullmatch(r'\d{8}T\d{6}Z-[a-f0-9]{6}', ident) or not receipt.get('verified'):
            raise UserError('A verified, explicitly identified backup is required')
        path = home/'backups'/(ident+'.zip')
        if digest(path) != receipt.get('sha256'):
            raise UserError('The immutable backup ZIP digest differs')
        companion = read_json(path.with_suffix('.json'))
        if companion.get('integrity') != 'verified' or companion.get('sha256') != receipt['sha256']:
            raise UserError('The backup companion receipt differs')
        self.archive = zipfile.ZipFile(path)
        if self.archive.getinfo('awft-backup.json').file_size > 8*1024**2:
            raise UserError('The backup manifest is too large')
        manifest = json.loads(self.archive.read('awft-backup.json'))
        if manifest.get('format') != 1:
            raise UserError('Unsupported backup format')
        self.files = {row['path']:row for row in manifest['files']}
        if len(self.files) != len(manifest['files']):
            raise UserError('Duplicate immutable backup entries')
        try:
            relative = Path(registry['world_path']).resolve().relative_to(home.resolve()).as_posix()
        except ValueError as exc:
            raise UserError('Registry world is outside the owned home') from exc
        self.prefix = relative+'/region/'
        self.regions, self.chunks, self.sources, self.protected = {}, {}, [], set()
        name=relative+'/level.dat';record=self.files.get(name)
        if not record or not 0 < record['size'] < 1024**2:
            raise UserError('No bounded saved world identity in the immutable backup')
        level_raw=self.archive.read(name)
        if hashlib.sha256(level_raw).hexdigest()!=record['sha256']:
            raise UserError('The saved world identity digest differs')
        decoder=zlib.decompressobj(31)
        decoded=decoder.decompress(level_raw,MAX_CHUNK+1)
        if len(decoded)>MAX_CHUNK or decoder.unconsumed_tail or not decoder.eof:
            raise UserError('The saved world identity exceeds its allocation')
        data=NBTReader(decoded).read().get('Data',{})
        if data.get('DataVersion')!=3955 or str(data.get('WorldGenSettings',{}).get('seed'))!=str(registry['seed']):
            raise UserError('The retained backup is not the registry world on Minecraft 1.21.1')
        self.sources.append({'file':'level.dat','sha256':record['sha256'],
                             'role':'Saved world seed/version matches current native registry; values remain private'})

    def close(self):
        self.archive.close()

    def chunk(self, cx, cz):
        key = (cx,cz)
        if key in self.chunks:
            return self.chunks[key]
        region = (cx//32,cz//32)
        if region not in self.regions:
            if len(self.regions) >= 4:
                raise UserError('The authoring site crosses too many bounded regions')
            name = self.prefix+f'r.{region[0]}.{region[1]}.mca'
            record = self.files.get(name)
            if not record or not 8192 <= record['size'] <= MAX_REGION:
                raise UserError('No bounded generated region in the retained backup: '+name)
            if self.archive.getinfo(name).file_size != record['size']:
                raise UserError('Region entry size differs')
            raw = self.archive.read(name)
            if hashlib.sha256(raw).hexdigest() != record['sha256']:
                raise UserError('Region entry content digest differs')
            self.regions[region] = raw
            self.sources.append({'file':PurePosixPath(name).name,'sha256':record['sha256'],
                                 'bytes':record['size'],'role':'Read-only saved block-state preimage'})
        raw = self.regions[region]
        header = ((cz&31)*32+(cx&31))*4
        location = int.from_bytes(raw[header:header+4],'big')
        sector, count = location>>8, location&255
        # RegionFile.write writes the complete compressed record, not the
        # unused tail of its last allocated sector. A crash preservation may
        # therefore lack padding while still containing an intact FULL chunk.
        # Admit only that final partial sector, never missing record bytes.
        rounded_end = ((len(raw)+4095)//4096)*4096
        if sector < 2 or not count or (sector+count)*4096 > rounded_end or sector*4096+5 > len(raw):
            raise UserError('The retained backup has no generated chunk '+str(key))
        offset = sector*4096
        length = int.from_bytes(raw[offset:offset+4],'big')
        if not 1 < length <= count*4096-4 or offset+4+length > len(raw):
            raise UserError('Invalid saved chunk length')
        compression, packed = raw[offset+4], raw[offset+5:offset+4+length]
        if compression not in (1,2,3):
            raise UserError('Unsupported or externally stored chunk compression')
        if compression == 3:
            decoded = packed
        else:
            decompressor = zlib.decompressobj(31 if compression == 1 else 15)
            decoded = decompressor.decompress(packed,MAX_CHUNK+1)
            if len(decoded) > MAX_CHUNK or decompressor.unconsumed_tail or decompressor.unused_data or not decompressor.eof:
                raise UserError('Compressed chunk exceeds its allocation or is truncated')
        document = NBTReader(decoded).read()
        if (document.get('xPos'),document.get('zPos')) != key or document.get('Status') not in ('minecraft:full','full'):
            raise UserError('Saved chunk coordinates/status differ from a fully generated site')
        for row in document.get('block_entities', []):
            self.protected.add((row['x'],row['y'],row['z']))
        self.chunks[key] = {row['Y']:row for row in document.get('sections', [])}
        return self.chunks[key]

    def state(self, pos):
        x,y,z = pos
        sections = self.chunk(x//16,z//16)
        return unpack_section(sections.get(y//16,{}),x,y,z)


class AttractionPlan:
    def __init__(self, ctx, snapshot):
        self.ctx, self.snapshot = ctx, snapshot
        self.blocks, self.previous, self.tags, self.clearance = {}, {}, {}, {}
        self.routes, self.features, self.systems = [], [], {}
        self.reserved = set(ctx.previous) | ctx.protected | ctx.headroom | ctx.immutable
        self.group = 'Copperway setting'

    def state(self, key, **properties):
        if key not in self.ctx.registry['blocks']:
            raise UserError('Unregistered actual block '+key)
        native = self.ctx.registry['blocks'][key]
        for k,v in properties.items():
            if k not in native or str(v).lower() not in native[k]:
                raise UserError('Unregistered exact property '+key+' '+k+'='+str(v))
        return key+('['+','.join(k+'='+str(v).lower() for k,v in sorted(properties.items()))+']' if properties else '')

    def put(self, x, y, z, key, *, replace=False, **properties):
        pos = (x,y,z)
        if not BOUNDS[0] <= x <= BOUNDS[2] or not BOUNDS[1] <= z <= BOUNDS[3] or not 56 <= y <= 88:
            raise UserError('Attraction exceeds its bounded reviewed site: '+str(pos))
        if pos in self.reserved:
            raise UserError('Completed construction/access is fixed: '+str(pos))
        old = self.snapshot.state(pos)
        if pos in self.snapshot.protected or base(old) not in NATURAL:
            raise UserError('Preserve non-natural saved blocks and block entities: '+str(pos)+' '+old)
        state = self.state(key,**properties)
        current = self.blocks.get(pos)
        if current is not None and current != AIR and current != state and not replace:
            raise UserError('Attraction features overlap without an explicit adaptation: '+str(pos)+' '+current+' -> '+state)
        self.blocks[pos] = state
        self.previous[pos] = old
        self.tags.pop(pos,None)
        if len(self.blocks) > MAX_POSITIONS:
            raise UserError('Split the bounded attraction plan')

    def box(self,x1,y1,z1,x2,y2,z2,key,**properties):
        for x in range(min(x1,x2),max(x1,x2)+1):
            for y in range(min(y1,y2),max(y1,y2)+1):
                for z in range(min(z1,z2),max(z1,z2)+1):
                    self.put(x,y,z,key,**properties)

    def ground(self,x,z):
        # Exact saved natural surface, never a survey height containing buildings.
        for y in range(76,55,-1):
            key = base(self.snapshot.state((x,y,z)))
            if key not in VEGETATION | {'minecraft:air','minecraft:cave_air','minecraft:short_grass','minecraft:tall_grass',
                           'minecraft:fern','minecraft:large_fern','minecraft:snow','minecraft:dandelion','minecraft:poppy','minecraft:water'}:
                if key not in NATURAL:
                    raise UserError('An unreviewed saved structure/plant occupies the new site: '+str((x,y,z))+' '+key)
                return y
        raise UserError('The site is deeper than the bounded foundation')

    def floor(self,x1,z1,x2,z2,y,material='minecraft:spruce_planks'):
        for x in range(x1,x2+1):
            for z in range(z1,z2+1):
                ground = self.ground(x,z)
                if ground > y+1 or y-ground > 10:
                    raise UserError('Relocate rather than cut terrain or build a tall artificial pedestal')
                for py in range(min(ground,y)-1,y):
                    self.put(x,py,z,'minecraft:stone_bricks')
                self.put(x,y,z,material)
                self.box(x,y+1,z,x,max(y+4,ground+2),z,AIR)

    def inventory(self,pos,title,items=()):
        x,y,z = pos
        self.put(x,y,z,'minecraft:chest',facing='south',type='single',waterlogged=False)
        rows=[]
        for slot,(key,count) in enumerate(items):
            if key not in self.ctx.registry['items'] or not 1 <= count <= 64:
                raise UserError('Invalid real starter inventory item')
            rows.append('{Slot:'+str(slot)+'b,id:'+json.dumps(key)+',count:'+str(count)+'}')
        self.tags[pos] = '{CustomName:'+json.dumps(json.dumps({'text':title}))+',Items:['+','.join(rows)+']}'

    def sign(self,pos,lines):
        x,y,z = pos
        self.put(x,y,z,'minecraft:oak_sign',rotation=8,waterlogged=False)
        messages = [json.dumps(json.dumps({'text':line,'color':'dark_green'})) for line in (lines+['']*4)[:4]]
        self.tags[pos] = '{is_waxed:1b,front_text:{messages:['+','.join(messages)+'],color:"brown",has_glowing_text:0b}}'

    def walking_route(self,name,points):
        for x,y,z in points:
            for dy in (0,1):
                pos = (x,y+dy,z)
                state = self.blocks.get(pos,self.snapshot.state(pos))
                if base(state) not in {'minecraft:air','minecraft:oak_door'}:
                    raise UserError('A walking route has blocked headroom: '+name+' '+str(pos)+' '+state)
                if pos not in self.blocks:
                    self.clearance[pos] = state
            support = (x,y-1,z)
            state = self.blocks.get(support,self.snapshot.state(support))
            if base(state) in {'minecraft:air','minecraft:cave_air','minecraft:water'}:
                raise UserError('A walking route has no solid support: '+name+' '+str(support))
            if support not in self.blocks:
                self.clearance[support] = state
        self.routes.append({'name':name,'standing_positions':[list(p) for p in points]})


def shelter(p,x1,z1,x2,z2,floor):
    p.floor(x1,z1,x2,z2,floor)
    p.box(x1,floor+1,z1,x2,floor+10,z2,AIR)
    for x in range(x1,x2+1):
        for z in (z1,z2):
            for y in range(floor+1,floor+7):
                if x in (x1,x2) or y==floor+6:
                    p.put(x,y,z,'minecraft:stripped_spruce_log',axis='y')
                else:
                    p.put(x,y,z,'minecraft:calcite')
    for z in range(z1+1,z2):
        for x in (x1,x2):
            p.box(x,floor+1,z,x,floor+6,z,'minecraft:stripped_spruce_log' if (z-z1)%5==0 else 'minecraft:calcite')
    for offset in range((x2-x1)//2+1):
        for x,facing in ((x1+offset,'east'),(x2-offset,'west')):
            if x1 <= x <= x2:
                p.box(x,floor+7+offset,z1-1,x,floor+7+offset,z2+1,'minecraft:dark_prismarine_stairs',
                      facing=facing,half='bottom',shape='straight',waterlogged=False)
                if offset:
                    for z in (z1,z2):
                        p.box(x,floor+7,z,x,floor+6+offset,z,'minecraft:spruce_planks')
    # A front entrance and paired recessed windows give the mill a distinct rhythm.
    for dx in (0,1):
        x=x1+2+dx
        for half,y in (('lower',floor+1),('upper',floor+2)):
            p.put(x,y,z2,'minecraft:oak_door',replace=True,facing='north',half=half,
                  hinge='left' if dx==0 else 'right',open=False,powered=False)
    for z in range(z1+3,z2-1,5):
        for x in (x1,x2):
            p.box(x,floor+2,z,x,floor+3,z+1,'minecraft:glass',replace=True)
    for x in (x1+1,x2-1):
        p.put(x,floor+5,z2-1,'minecraft:lantern',hanging=True,waterlogged=False)


def workshop(p):
    p.group='Copperway Watermill and dispatch'
    shelter(p,1298,-1011,1309,-991,68)
    p.floor(1292,-1024,1300,-1015,70)
    p.box(1292,71,-1024,1300,78,-1015,AIR)
    # The open dispatch arcade has unequal bays and a raised teal canopy.
    for x,z in ((1292,-1024),(1300,-1024),(1292,-1015),(1300,-1015)):
        p.box(x,71,z,x,75,z,'minecraft:stripped_spruce_log',axis='y')
    p.box(1292,76,-1024,1300,76,-1015,'minecraft:dark_prismarine_slab',type='bottom',waterlogged=False)
    p.put(1295,71,-1020,'minecraft:stone_bricks')
    p.inventory((1295,72,-1020),'Flour dispatch — pneumatic output')
    p.sign((1297,71,-1017),['Copperway dispatch','Flour arrives here','From our watermill','No idle chunk tickets'])
    p.floor(1292,-1005,1297,-999,68,'minecraft:stone_bricks')
    p.box(1292,69,-1005,1296,75,-999,AIR)
    # Three coaxial native small wheels; the sealed waterfall is separate from
    # the initially stopped, dry installation and admitted only at commissioning.
    p.box(1292,68,-1004,1296,68,-1000,'minecraft:stone_bricks',replace=True)
    for x in (1292,1296):
        p.box(x,69,-1004,x,74,-1000,'minecraft:glass')
    p.box(1293,69,-1004,1295,74,-1004,'minecraft:stone_bricks')
    p.box(1293,69,-1000,1295,74,-1000,'minecraft:stone_bricks')
    for x in (1293,1294,1295):
        p.put(x,71,-1002,'create:water_wheel',facing='west')
    for x in range(1296,1307):
        p.put(x,71,-1002,'create:shaft',replace=True,axis='x',waterlogged=False)
    # A full casing closes the hydraulic wall while carrying the shaft through.
    p.put(1296,71,-1002,'create:andesite_encased_shaft',replace=True,axis='x')
    p.put(1297,71,-1002,'create:clutch',replace=True,axis='x',powered=True)
    p.put(1297,71,-1001,'minecraft:stone_bricks')
    p.put(1297,72,-1001,'minecraft:lever',face='floor',facing='north',powered=True)
    p.put(1300,71,-1002,'create:cogwheel',replace=True,axis='x',waterlogged=False)
    p.put(1302,71,-1002,'create:gearbox',replace=True,axis='z')
    p.put(1302,72,-1002,'create:millstone')
    p.put(1302,73,-1002,'create:chute',facing='down',shape='normal',waterlogged=False)
    p.put(1302,74,-1002,'minecraft:hopper',facing='down',enabled=True)
    p.inventory((1302,75,-1002),'Grain input — empty until commissioning')
    p.put(1307,71,-1002,'create:mechanical_press',facing='north')
    p.put(1307,69,-1002,'create:depot',waterlogged=False)
    p.inventory((1303,69,-1008),'Watermill starter kit',
                [('minecraft:wheat',16),('minecraft:iron_ingot',16),('create:wrench',1)])
    p.sign((1305,69,-1007),['Watermill workshop','Lever ON = stopped','Wheat upstairs','Ingot on depot'])
    # Gallery access reaches the high grain hopper without crossing rotating parts.
    for n in range(4):
        p.put(1308,69+n,-997-n,'minecraft:spruce_stairs',facing='north',half='bottom',shape='straight',waterlogged=False)
    p.box(1308,72,-1003,1308,72,-1001,'minecraft:spruce_planks')
    p.box(1304,72,-1006,1308,72,-1004,'minecraft:spruce_planks')
    for x in range(1304,1309):
        p.put(x,73,-1006,'minecraft:spruce_fence')
    # Native cog meshing turns the directional item pump. Extract faces away
    # from the millstone inventory; insertion faces toward the dispatch chest.
    p.put(1301,72,-1002,'overpressure:pneumatic_connection',facing='west',arrow_facing='west',mode='extract',powered=False)
    p.tags[(1301,72,-1002)]='{filter:{id:"create:wheat_flour",count:1}}'
    p.put(1300,72,-1002,'overpressure:item_pump',facing='west',waterlogged=False)
    for x in range(1297,1300):
        p.put(x,72,-1002,'overpressure:pneumatic_tube',replace=True,east=True,west=x!=1297,
              north=x==1297,waterlogged=False)
    for z in range(-1017,-1002):
        p.put(1297,72,z,'overpressure:pneumatic_tube',north=z!=-1017,south=True,
              west=z==-1017,waterlogged=False)
    p.put(1296,72,-1017,'overpressure:pneumatic_tube',east=True,west=True,waterlogged=False)
    p.put(1295,72,-1017,'overpressure:pneumatic_tube',east=True,north=True,waterlogged=False)
    p.put(1295,72,-1018,'overpressure:pneumatic_tube',north=True,south=True,waterlogged=False)
    p.put(1295,72,-1019,'overpressure:pneumatic_connection',facing='north',arrow_facing='north',mode='insert',powered=False)
    p.box(1299,77,-1008,1300,84,-1007,'minecraft:bricks',replace=True)
    p.box(1299,85,-1008,1300,85,-1007,'minecraft:stone_brick_slab',type='bottom',waterlogged=False)
    p.systems['watermill']={'wheels':[[x,71,-1002] for x in (1293,1294,1295)],
        'water_sources':[[x,74,-1003] for x in (1293,1294,1295)],'clutch':[1297,71,-1002],
        'stop_lever':[1297,72,-1001],'initial_lever_powered':True,'main_axis':'x',
        'millstone':[1302,72,-1002],'gearbox':[1302,71,-1002],'gearbox_axis':'z',
        'grain_chest':[1302,75,-1002],'press':[1307,71,-1002],'depot':[1307,69,-1002],
        'starter_chest':[1303,69,-1008], 'recipes':['create:milling/wheat','create:pressing/iron_ingot'],
        'initial_water':'Dry — fill only after containment, native filter and stop-control checks',
        'claim':'Geometric/native-API candidate; actual RPM, stress and recipes unproved'}
    p.systems['pneumatic']={'extractor':[1301,72,-1002],'extract_facing':'west',
        'filter':'create:wheat_flour','pump':[1300,72,-1002],'drive_cog':[1300,71,-1002],
        'pump_axis':'x','pump_facing':'west','inserter':[1295,72,-1019],
        'insert_facing':'north','output_chest':[1295,72,-1020],
        'packagers_only_required':False,'native_filter_api':'PneumaticConnectionBlockEntity.setFilter(ItemStack)',
        'filter_nbt':'Pinned native read fallback key filter; no fabricated routing/RPM fields'}


def transport(p):
    p.group='Copperway passenger transport'
    # Separate walking bypass, independent from tube and moving rail envelope.
    p.floor(1307,-990,1309,-931,68,'minecraft:stone_bricks')
    p.floor(1298,-990,1309,-988,68,'minecraft:stone_bricks')
    p.floor(1292,-942,1309,-940,68,'minecraft:stone_bricks')
    # Two native 30-block Bezier spans use a genuine midpoint anchor. The mod's
    # maximum single span is 40; a row of visual tube blocks is not a connection.
    p.floor(1310,-998,1312,-932,68,'minecraft:stone_bricks')
    p.put(1311,69,-965,'create_hypertube:hypertube',north_south=True,east_west=False,
          up_down=False,waterlogged=False)
    for z,facing in ((-995,'north'),(-935,'south')):
        p.put(1311,69,z,'create_hypertube:hypertube_entrance',facing=facing,locked=False,powered=False,waterlogged=False)
        p.put(1310,69,z,'minecraft:stone_bricks')
        p.put(1310,70,z,'minecraft:lever',face='floor',facing='east',powered=False)
        p.sign((1312,69,z),['Copperway player tube','16 RPM to enter','Lever: sneak entry','Walkway stays open'])
    # Rail formation is level but follows exact retained terrain foundations.
    p.floor(1314,-1012,1318,-910,68,'minecraft:stone_bricks')
    p.box(1315,69,-1012,1317,76,-910,AIR)
    for z in range(-1012,-909):
        p.put(1316,69,z,'railways:track_spruce',shape='zo',turn=False,waterlogged=False)
    for z in (-1012,-910):
        p.box(1315,70,z,1317,71,z,'minecraft:dark_oak_planks')
    for z1,z2 in ((-1010,-1000),(-930,-919)):
        p.floor(1310,z1,1314,z2,70)
        # Track-facing platform edge remains a two-block clear passenger route.
        for x,z in ((1310,z1),(1310,z2)):
            p.box(x,71,z,x,74,z,'minecraft:stripped_spruce_log',axis='y')
        p.box(1310,75,z1,1313,75,z2,'minecraft:dark_prismarine_slab',type='bottom',waterlogged=False)
        p.put(1310,74,(z1+z2)//2,'minecraft:lantern',hanging=True,waterlogged=False)
    # The second stop has a useful destination: an open garden-view tea shelter,
    # with a glazed rooflight and seats, rather than an otherwise empty platform.
    p.floor(1302,-928,1309,-920,70)
    for x in (1302,1309):
        for z in (-928,-920):
            p.box(x,71,z,x,75,z,'minecraft:stripped_spruce_log',axis='y')
    p.box(1302,76,-928,1309,76,-920,'minecraft:dark_prismarine_slab',type='bottom',waterlogged=False)
    p.box(1305,76,-925,1307,76,-923,'minecraft:glass',replace=True)
    for x in (1303,1304,1305):
        p.put(x,71,-927,'handcrafted:spruce_bench',facing='south',color='blue',
              shape='left' if x==1303 else 'right' if x==1305 else 'middle',waterlogged=False)
    for x in (1303,1308):
        p.put(x,71,-921,'minecraft:bricks')
        p.put(x,72,-921,'minecraft:potted_pink_tulip')
    p.put(1306,75,-921,'minecraft:lantern',hanging=True,waterlogged=False)
    for x1,x2,first,last,facing in ((1312,1313,-998,-999,'north'),(1308,1309,-931,-930,'south')):
        p.floor(x1,min(first,last),x2,max(first,last),68,'minecraft:stone_bricks')
        p.box(x1,69,last,x2,69,last,'minecraft:stone_bricks')
        for z,y in ((first,69),(last,70)):
            p.box(x1,y,z,x2,y,z,'minecraft:spruce_stairs',replace=True,facing=facing,half='bottom',shape='straight',waterlogged=False)
            p.box(x1,y+1,z,x2,y+3,z,AIR,replace=True)
    stations=[]
    for name,z,positive in (('Copperway Watermill',-1006,True),('Rosewater Garden Halt',-924,False)):
        pos=(1312,71,z);target=(1316,69,z)
        p.put(*pos,'create:track_station',assembling=False,waterlogged=False)
        ident=uuid.uuid5(uuid.NAMESPACE_URL,'awft:copperway:'+p.ctx.registry['seed']+':'+name)
        ints=[int.from_bytes(ident.bytes[n:n+4],'big',signed=True) for n in range(0,16,4)]
        p.tags[pos]='{Id:[I;'+','.join(map(str,ints))+'],TargetTrack:[I;4,-2,0],Ortho:1b,TargetDirection:'+('1b' if positive else '0b')+'}'
        stations.append({'name':name,'position':list(pos),'target_track':list(target),
                         'native_target_relative':[4,-2,0],'target_direction_positive':positive,'id':str(ident)})
        p.sign((1310,71,z+1),[name,'Passenger shuttle','Driver at either end','Board only when stopped'])
    p.inventory((1310,71,-1008),'Copperway railway operations',
                [('create:wrench',1),('create:super_glue',1),('create:schedule',1)])
    # A two-bogey original open observation carriage. Only this bounding box may
    # be glued; rails, platforms, tube and station blocks are never captured.
    p.box(1315,71,-1005,1317,71,-997,'minecraft:spruce_planks')
    for z in (-1004,-998):
        p.put(1316,70,z,'create:small_bogey',axis='z',waterlogged=False)
    for x in (1315,1317):
        for z in (-1005,-997):
            p.box(x,72,z,x,74,z,'minecraft:spruce_fence')
    p.box(1315,75,-1005,1317,75,-997,'minecraft:dark_prismarine_slab',type='bottom',waterlogged=False)
    for z in (-1005,-997):
        p.put(1316,72,z,'create:controls',facing='north' if z==-1005 else 'south',open=False,virtual=False,waterlogged=False)
    for z in (-1003,-1001,-999):
        p.put(1316,72,z,'create:blue_seat',waterlogged=False)
    p.put(1315,71,-1002,'minecraft:spruce_stairs',replace=True,
          facing='east',half='bottom',shape='straight',waterlogged=False)
    # An actual 2:1 large-to-small cog pair supplies the two 16-RPM entrance
    # cogs. The common stop lever isolates this drive along with the workshop.
    p.box(1309,64,-1004,1314,64,-999,'minecraft:stone_bricks')
    p.box(1309,65,-1004,1314,67,-999,AIR,replace=True)
    p.box(1310,68,-1004,1314,69,-999,AIR,replace=True)
    for x in (1308,1309,1310):
        p.put(x,71,-1002,'create:shaft',replace=True,axis='x',waterlogged=False)
    p.put(1311,71,-1002,'create:gearbox',axis='z')
    for y in range(67,71):
        p.put(1311,y,-1002,'create:shaft',replace=True,axis='y',waterlogged=False)
    p.put(1311,66,-1002,'create:gearbox',axis='x')
    p.put(1311,66,-1001,'create:large_cogwheel',axis='z',waterlogged=False)
    p.put(1312,67,-1001,'create:cogwheel',axis='z',waterlogged=False)
    for z in range(-1000,-934):
        p.put(1312,67,z,'create:shaft',replace=True,axis='z',waterlogged=False)
    for z in (-995,-935):
        for x,y in ((1312,67),(1311,67),(1311,68)):
            p.put(x,y,z,'create:cogwheel',replace=True,axis='z',waterlogged=False)
    p.box(1314,65,-1003,1314,69,-1003,'minecraft:stone_bricks')
    for y in range(65,70):
        p.put(1313,y,-1003,'minecraft:ladder',facing='west',waterlogged=False)
    p.put(1313,70,-1003,'minecraft:spruce_trapdoor',replace=True,facing='west',half='top',open=False,powered=False,waterlogged=False)
    p.sign((1312,71,-1001),['Tube drive service','STOP main drive','Before opening hatch','Native 2:1 gearing'])
    p.systems['hypertube']={'entrances':[[1311,69,-995],[1311,69,-935]],
        'route_extent_blocks_including_entrances':61,'midpoint_anchor':[1311,69,-965],
        'native_span_lengths':[30,30],'maximum_native_span':40,'chunk_boundaries':4,
        'minimum_entrance_rpm':16,'large_cog':[1311,66,-1001],'speedup_small_cog':[1312,67,-1001],
        'gear_ratio':2,'buried_drive_start':[1312,67,-1001],'buried_drive_end':[1312,67,-935],
        'entrance_drive_cogs':[[1311,68,-995],[1311,68,-935]],'service_hatch':[1313,70,-1003],
        'clear_egress_standing':[[1311,69,z] for z in (-998,-997,-996,-934,-933,-932)],
        'manual_entry_mode_levers':[[1310,70,-995],[1310,70,-935]],
        'power_semantics':'Real 16+ RPM required. LOCKED selects sneak-to-enter; it is not an emergency stop. Main clutch stops the drive.',
        'native_connection_state':'Not initialized by block placement. The native connection API must create two bounded Bezier spans and TubeFiller collision cells.',
        'native_links':[{'from':[1311,69,-995],'from_face':'south','to':[1311,69,-965],'to_face':'north'},
                        {'from':[1311,69,-965],'from_face':'south','to':[1311,69,-935],'to_face':'north'}],
        'native_link_api':['SimpleConnection(BlockPos, Direction, float)',
            'BezierConnection(SimpleConnection, SimpleConnection)',
            'BezierConnection.getValidation().valid()', 'TubeUtils.checkBlockCollision(Level, BezierConnection)',
            'TubeCollision.occupiedVolume(bezier.getBezierPoints(level, fromPos))',
            'ITubeConnectionEntity.setConnection(connection, face)',
            'ITubeConnectionEntity.getConnections(); TubeBlockEntity.sync()'],
        'native_write_envelope':[1310,69,-994,1312,70,-936],
        'native_link_admission':'Calculate native collision cells before writing; every new TubeFiller target must be exact preverified air in this envelope, excluding the fixed midpoint anchor, levers and signs. Abort outside it.',
        'claim':'Native block and geometry candidate; player round trips/crossings unproved'}
    p.systems['railway']={'track_start':[1316,69,-1012],'track_end':[1316,69,-910],
        'track_blocks':103,'station_distance_blocks':82,'stations':stations,
        'carriage_glue_min':[1315,70,-1005],'carriage_glue_max':[1317,75,-997],
        'bogeys':[[1316,70,-1004],[1316,70,-998]],'bogey_axis':'z','seats':3,
        'controls':[[1316,72,-1005],[1316,72,-997]],'initially_assembled':False,
        'operations_chest':[1310,71,-1008],
        'operation':'On-demand manually driven bidirectional shuttle; no continuous schedule or forced loading',
        'native_assembly_api':['StationBlockEntity.tryEnterAssemblyMode()',
            'StationBlockEntity.refreshAssemblyInfo()','StationBlockEntity.isValidBogeyOffset(int)',
            'StationBlockEntity.assemble(UUID)','StationBlockEntity.exitAssemblyMode()'],
        'claim':'Actual native track/station/carriage candidate; graph, glue, assembly and driving unproved'}
    p.walking_route('Continuous workshop to garden walking bypass',[(1308,69,z) for z in range(-990,-932)])
    p.walking_route('Mill front door access',[(x,69,-989) for x in range(1300,1309)]+[(1300,69,-990),(1300,69,-991),(1300,69,-992)])
    p.walking_route('Mill operating aisle',[(1305,69,z) for z in range(-1005,-992)])
    for name,zs in (('Tube north safe egress',(-998,-997,-996)),('Tube south safe egress',(-934,-933,-932))):
        p.walking_route(name,[(1311,69,z) for z in zs])
    for name,zs in (('Watermill rail boarding',range(-1009,-1000)),('Garden rail boarding',range(-929,-919))):
        p.walking_route(name,[(1313,71,z) for z in zs])
    p.walking_route('Garden-view shelter access',[(x,71,-922) for x in range(1306,1315)])


def properties(state):
    if '[' not in state:
        return {}
    return dict(pair.split('=',1) for pair in state.split('[',1)[1][:-1].split(','))


def validate_systems(p):
    """Check real spatial contracts; this cannot substitute for native execution."""
    def require(pos,key,**props):
        state=p.blocks.get(tuple(pos),'')
        if base(state)!=key or any(properties(state).get(k)!=str(v).lower() for k,v in props.items()):
            raise UserError('Broken physical system component at '+str(pos)+': expected '+key+' '+str(props))
    for x in (1293,1294,1295):
        require((x,71,-1002),'create:water_wheel',facing='west')
        require((x,74,-1003),AIR)
    for x in range(1292,1297):
        for z in range(-1004,-999):
            require((x,68,z),'minecraft:stone_bricks')
    for x in (1292,1296):
        for y in range(69,75):
            for z in range(-1004,-999):
                require((x,y,z),'create:andesite_encased_shaft' if (x,y,z)==(1296,71,-1002) else 'minecraft:glass')
    for z in (-1004,-1000):
        for x in (1293,1294,1295):
            for y in range(69,75):
                require((x,y,z),'minecraft:stone_bricks')
    special={1296:'create:andesite_encased_shaft',1297:'create:clutch',1300:'create:cogwheel',1302:'create:gearbox'}
    for x in range(1296,1307):
        require((x,71,-1002),special.get(x,'create:shaft'),axis='z' if x==1302 else 'x')
    require((1297,72,-1001),'minecraft:lever',powered=True)
    require((1302,72,-1002),'create:millstone')
    require((1307,71,-1002),'create:mechanical_press',facing='north')
    require((1307,69,-1002),'create:depot')
    require((1300,72,-1002),'overpressure:item_pump',facing='west')
    require((1301,72,-1002),'overpressure:pneumatic_connection',mode='extract',facing='west')
    require((1295,72,-1019),'overpressure:pneumatic_connection',mode='insert',facing='north')
    require((1295,72,-1020),'minecraft:chest')
    require((1295,71,-1020),'minecraft:stone_bricks')
    if 'create:wheat_flour' not in p.tags.get((1301,72,-1002),''):
        raise UserError('The flour extractor lacks its actual native filter')
    for pos in ((1302,75,-1002),(1295,72,-1020)):
        if not p.tags.get(pos,'').endswith('Items:[]}'):
            raise UserError('Powered inventories must start empty; starter goods stay separate')
    directions={'north':(0,0,-1),'south':(0,0,1),'east':(1,0,0),'west':(-1,0,0),'up':(0,1,0),'down':(0,-1,0)}
    nodes={pos:s for pos,s in p.blocks.items() if base(s).startswith('overpressure:')}
    edges={}
    for pos,state in nodes.items():
        attrs=properties(state);key=base(state)
        faces=[k for k in directions if attrs.get(k)=='true'] if key.endswith('pneumatic_tube') else [attrs['facing']] if key.endswith('item_pump') or attrs.get('mode')=='extract' else []
        edges[pos]=[]
        for face in faces:
            delta=directions[face];neighbor=tuple(pos[n]+delta[n] for n in range(3))
            if neighbor not in nodes:
                raise UserError('A pneumatic branch points at no actual route component: '+str(pos)+' '+face)
            edges[pos].append(neighbor)
    seen=set();queue=[(1301,72,-1002)]
    while queue:
        pos=queue.pop()
        if pos not in seen:
            seen.add(pos);queue.extend(edges[pos])
    if seen!=set(nodes) or (1295,72,-1019) not in seen:
        raise UserError('The actual filtered flour route is disconnected')
    for z in range(-995,-934):
        if z in (-995,-935):
            require((1311,69,z),'create_hypertube:hypertube_entrance',facing='north' if z==-995 else 'south',locked=False,powered=False)
        elif z==-965:
            require((1311,69,z),'create_hypertube:hypertube',north_south=True)
        else:
            require((1311,69,z),AIR)
    require((1311,71,-1002),'create:gearbox',axis='z')
    require((1311,66,-1002),'create:gearbox',axis='x')
    require((1311,66,-1001),'create:large_cogwheel',axis='z')
    require((1312,67,-1001),'create:cogwheel',axis='z')
    for z in range(-1000,-934):
        require((1312,67,z),'create:cogwheel' if z in (-995,-935) else 'create:shaft',axis='z')
    for z in (-995,-935):
        for y in (67,68):
            require((1311,y,z),'create:cogwheel',axis='z')
    for z in range(-1012,-909):
        require((1316,69,z),'railways:track_spruce',shape='zo')
    for station in p.systems['railway']['stations']:
        require(station['position'],'create:track_station')
        require(station['target_track'],'railways:track_spruce',shape='zo')
        if 'TargetTrack:[I;4,-2,0]' not in p.tags.get(tuple(station['position']),''):
            raise UserError('A station lacks its exact native relative rail target')
    for z in (-1004,-998):
        require((1316,70,z),'create:small_bogey',axis='z')
    for z in (-1005,-997):
        require((1316,72,z),'create:controls',facing='north' if z==-1005 else 'south')
    for z in range(-1011,-910):
        if -1005<=z<=-997:
            continue
        for x in (1315,1316,1317):
            for y in range(70,76):
                require((x,y,z),AIR)
    for route in p.routes:
        for x,y,z in route['standing_positions']:
            for dy in (0,1):
                pos=(x,y+dy,z);state=p.blocks.get(pos,p.snapshot.state(pos))
                if base(state) not in {AIR,'minecraft:oak_door'}:
                    raise UserError('A documented approach was subsequently obstructed: '+route['name'])
    return {'kinetic_path':'3 wheels → sealed shaft → stopped clutch → driven cog + X/Y gearbox + press',
            'pneumatic_route_nodes':len(nodes),'hypertube_route_extent_blocks':61,
            'hypertube_native_anchor_blocks':3,'hypertube_native_links_required':2,
            'entrance_minimum_rpm':16,'entrance_drive_ratio':2,'track_blocks':103,
            'stations':2,'bogeys':2,'routes':len(p.routes),'native_execution':'Pending'}


def load(home):
    ctx=load_context(home)
    directory=Path(home)/'dashboard/settlement'
    index=directory/'detail-pass-d0926cb2a2ddab00/index.json'
    if digest(index) != DETAIL_INDEX_SHA:
        raise UserError('The five completed architectural deltas differ')
    for row in read_json(index)['districts']:
        file=index.parent/row['plan_file']
        if file.parent!=index.parent or digest(file)!=row['plan_sha256']:
            raise UserError('A completed detail source differs')
        doc=read_json(file)
        ctx.previous.update({(x,y,z):doc['palette'][i] for x,y,z,i in doc['blocks']})
        ctx.protected.update(tuple(r['pos']) for r in doc['block_entities'])
        ctx.sources.append({'file':file.name,'sha256':row['plan_sha256'],'role':'Completed detail exclusion'})
    cfg=Path(home)/'server/config/overpressure-common.toml'
    if not re.search(r'^\s*packagersOnly\s*=\s*false\s*$',cfg.read_text(),re.M):
        raise UserError('This complementary millstone route requires the actual packagersOnly=false config')
    ctx.sources.append({'file':cfg.name,'sha256':digest(cfg),'role':'Actual pneumatic inventory policy'})
    cfg=Path(home)/'server/config/create_hypertube-server.toml'
    if tomllib.loads(cfg.read_text()).get('Collision Settings',{}).get('tubeCollision') is not True:
        raise UserError('This functional tube candidate requires the actual native solid collision setting')
    ctx.sources.append({'file':cfg.name,'sha256':digest(cfg),'role':'Actual native tube collision/stress policy'})
    cfg=Path(home)/'server/config/create-server.toml'
    ctx.sources.append({'file':cfg.name,'sha256':digest(cfg),'role':'Actual kinetic stress/capacity policy; runtime measurements still required'})
    for name,sha in zip(MOD_FILES,MOD_SHAS):
        file=Path(home)/'server/mods'/name
        if not file.is_file() or digest(file)!=sha:
            raise UserError('The native API candidate requires exact installed file '+name)
        ctx.sources.append({'file':name,'sha256':sha,'role':'Read-only pinned native API/recipe evidence'})
    return ctx


def construct(ctx,snapshot):
    p=AttractionPlan(ctx,snapshot)
    workshop(p);transport(p)
    if p.reserved & p.blocks.keys() or snapshot.protected & p.blocks.keys():
        raise UserError('The completed build or a saved block entity would be changed')
    validate_systems(p)
    return p


def payload(p,states,name,at,*,tags=False):
    palette=sorted(set(states.values()));indices={s:i for i,s in enumerate(palette)}
    return {'format':'awft-native-settlement:1','name':name,'created':at,
        'seed':p.ctx.registry['seed'],'world_path':p.ctx.registry['world_path'],
        'backup_sha256':p.ctx.backup['sha256'],
        'bounds':[min(q[0] for q in states),min(q[2] for q in states),max(q[0] for q in states),max(q[2] for q in states)],
        'palette':palette,'blocks':[[x,y,z,indices[s]] for (x,y,z),s in sorted(states.items(),key=lambda r:(r[0][0]//16,r[0][2]//16,r[0][1],r[0][0],r[0][2]))],
        'block_entities':[{'pos':list(pos),'nbt':nbt} for pos,nbt in sorted(p.tags.items())] if tags else [],
        'commands':[],'landmarks':[{'name':'Copperway Watermill and Garden Railway','dimension':'minecraft:overworld',
                                  'x':1305,'y':69,'z':-989,'category':'Engineering','features':list(p.systems)}],
        'coverage':{'create':['Watermill, milling, pressing and passenger railway'],
                    'overpressure':['Filtered flour dispatch'],
                    'create_hypertube':['Parallel player route'],'railways':['Spruce passenger track']},
        'validation':'Private source/backup preflight only; fresh native before/after, functional and restart proof required'}


def prepare(home,destination=None,*,dry_run=False):
    layout=Layout(Path(home));ctx=load(layout.home)
    snapshot=BackupWorld(layout.home,ctx.backup,ctx.registry)
    try:
        p=construct(ctx,snapshot)
        counts=dict(sorted(Counter(base(s) for s in p.blocks.values()).items()))
        if dry_run:
            return {'placements':len(p.blocks),'block_entities':len(p.tags),'bounds':list(BOUNDS),
                    'block_counts':counts,'systems':p.systems,'routes':len(p.routes),
                    'saved_chunks_read':len(snapshot.chunks),'sources':snapshot.sources,
                    'native_activation':'Not performed'}
        at=utcnow();documents={}
        def encode(name,doc):
            raw=(json.dumps(doc,separators=(',',':'),ensure_ascii=False)+'\n').encode()
            documents[name]=raw
            return hashlib.sha256(raw).hexdigest()
        plan=payload(p,p.blocks,'Copperway functional attractions — dry installation',at,tags=True)
        sha=encode('attractions.json',plan)
        expected=dict(p.previous);expected.update(p.clearance)
        before_sha=encode('attractions-preconditions.json',payload(p,expected,'VERIFY ONLY — retained backup states for every attraction target and route',at))
        # Separate water source activation preserves dry initial inventory checks.
        activation={tuple(pos):p.state('minecraft:water',level=0) for pos in p.systems['watermill']['water_sources']}
        activation_sha=encode('water-activation.json',payload(p,activation,'COMMISSION ONLY — three contained waterfall sources',at))
        activate_before_sha=encode('water-activation-preconditions.json',payload(p,{pos:AIR for pos in activation},'VERIFY ONLY — dry water source cells',at))
        manifest={'format':'awft-settlement-attractions:1','at':at,'backup_id':ctx.backup['id'],
            'backup_sha256':ctx.backup['sha256'],'source_sha256':digest(Path(__file__)),
            'plan_file':'attractions.json','plan_sha256':sha,'placements':len(p.blocks),'bounds':plan['bounds'],
            'preconditions_file':'attractions-preconditions.json','preconditions_sha256':before_sha,
            'precondition_positions':len(expected),'block_entities':len(p.tags),'block_counts':counts,
            'water_activation_file':'water-activation.json','water_activation_sha256':activation_sha,
            'water_activation_preconditions_file':'water-activation-preconditions.json',
            'water_activation_preconditions_sha256':activate_before_sha,'water_source_positions':list(map(list,activation)),
            'expected_previous':[{'position':list(pos),'previous':p.previous[pos],'replacement':new} for pos,new in sorted(p.blocks.items())],
            'source_preflight':validate_systems(p),
            'natural_replacement_counts':dict(sorted(Counter(base(old) for pos,old in p.previous.items() if base(old)!=base(p.blocks[pos])).items())),
            'systems':p.systems,'routes':p.routes,'provenance':ctx.sources+snapshot.sources,
            'protected_existing_entities':len(ctx.protected|snapshot.protected),
            'completed_positions_fixed':len(ctx.previous),'protected_route_cells':len(ctx.headroom),
            'entity_summons':0,'commands':0,'new_forced_chunks':0,
            'native_admission_order':['Rebind current verified backup by rerunning this tool if receipt changes',
                'Empty server; verify exact before plan with zero failures; abort rather than clearing differences',
                'Place dry attraction plan; verify blocks/orientations/starter inventory; inspect routes and containment',
                'Native-read extractor filter and station targets; commission actual glued carriage and station graph',
                'Validate both native 30-block Hypertube curves and their exact air-only collision write sets before creating native connection objects',
                'Verify dry activation cells, add waterfall sources, inspect real flow/stress/RPM and stop lever',
                'Run milling, pressing, flour routing, tube round trips, train route and emergency-stop checks',
                'Save/restart and repeat functionality; refresh map; client/3D acceptance remains separate'],
            'native_verification_limits':'Current samePlacement checks block identities and selected orientation properties; it does not prove tube flags, station targets, filters, energy, pathfinding, inventory transfer or train assembly',
            'required_native_reads':['Actual KineticBlockEntity speed/stress/capacity while STOP and RUN',
                'PneumaticConnectionBlockEntity.getFilter() and actual chest/item counts',
                'StationBlockEntity.edgePoint.hasValidTrack(), getGlobalPosition(), getTargetDirection(), getStation()',
                'Native carriage/train UUID and bogey count; graph route and bidirectional drive receipts',
                'Native Hypertube reciprocal connections, curve validation/collision cells, real entrance RPM >=16, mode state and actual player positions before/after boundary crossings'],
            'status':'Source/staging only; no native placement, functional commissioning, persistence or visual acceptance'}
        encode('manifest.json',manifest)
        total=sum(map(len,documents.values()))
        if total>MAX_OUTPUT:
            raise UserError('The complete audit bundle exceeds its guarded maximum allocation')
        identity=hashlib.sha256(documents['manifest.json']).hexdigest()
        output=(layout.state/'settlement'/('attractions-'+identity[:16]) if destination is None else Path(destination).resolve())
        if not output.resolve().is_relative_to((layout.state/'settlement').resolve()) or output.exists():
            raise UserError('Use a fresh private settlement staging directory; preserve all older evidence')
        Storage(layout).reserve(MAX_OUTPUT,target=output)
        output.mkdir(parents=True)
        for name,raw in documents.items():
            atomic_write(output/name,raw)
        return {'manifest':str(output/'manifest.json'),'manifest_sha256':identity,'plan_sha256':sha,
                'preconditions_sha256':before_sha,'placements':len(p.blocks),'bytes':total,
                'native_activation':'Not performed'}
    finally:
        snapshot.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--home',type=Path,default=Path(r'D:\A World for Two'))
    parser.add_argument('--destination',type=Path)
    parser.add_argument('--dry-run',action='store_true')
    args=parser.parse_args()
    print(json.dumps(prepare(args.home,args.destination,dry_run=args.dry_run),indent=2))
