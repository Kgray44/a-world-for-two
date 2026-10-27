"""Authored Lanternwater bascules: open water, slender timber leaves and bank rooms.

The old proven kinetic coordinates are retained as engineering interfaces, while
all architecture is newly authored. This emits private plans, never fake motion.
"""
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path

from control_room.common import UserError, read_json, digest, utcnow
from .settlement import Plan
from .artistic_materials import require_material_rule
from .settlement_drawbridge import placed_systems, placed_radios, clearance_estimate
from .playtest import guard


AIR='minecraft:air'
STONE=('chipped:small_stone_bricks','chipped:etched_stone_bricks',
       'chipped:small_andesite_bricks','chipped:carved_stone',
       'minecraft:stone_bricks','chipped:engraved_stone',
       'minecraft:polished_andesite','minecraft:chiseled_stone_bricks')


class Bascule(Plan):
    def __init__(self, registry, backup):
        self.registry=registry; self.native=registry['blocks']; self.backup=backup
        self.cx,self.cz=1193,-1144;self.rotation=0
        self.blocks={};self.tags={};self.protected=set();self.commands=[]
        self.landmarks=[];self.features=[];self.uses={};self.zone='Lanternwater bascules'
        self.groups={};self.cameras=[]

    def world(self,x,z):return x,z

    def state(self,key,**properties):
        if key not in self.native or properties.keys()-self.native[key].keys():
            raise UserError('Unregistered bascule state: '+key+' '+str(properties))
        return super().state(key,**properties)

    def put(self,x,y,z,key,**properties):
        if not 1174<=x<=1232 or not -1208<=z<=-1081 or not 55<=y<=94:
            raise UserError('Bascule escaped its reviewed bank/channel envelope')
        super().put(x,y,z,key,**properties)
        self.groups.setdefault(self.zone,set()).add((x,y,z))

    def ashlar(self,x,y,z):
        # Dressed corner joints and four-course string courses, with related
        # stone tones. These are deliberate construction seams, never noise.
        return STONE[(1 if x%4==0 else 0)+(2 if y%4==0 else 0)+(4 if z%4==0 else 0)]

    def stone(self,x,y,z):self.put(x,y,z,self.ashlar(x,y,z))

    def stair(self,x,y,z,key='minecraft:stone_brick_stairs',facing='south',half='bottom'):
        self.put(x,y,z,key,facing=facing,half=half,shape='straight',waterlogged=False)

    def wood_floor(self,x,y,z):
        if x%4==0:key='chipped:boxed_spruce_planks' if z%9 else 'chipped:nailed_dark_oak_planks'
        else:key='minecraft:spruce_planks' if z%9 else 'chipped:stacked_dark_oak_planks'
        self.put(x,y,z,key)

    def paving(self,x,y,z):
        keys=('minecraft:polished_andesite','chipped:carved_stone',
              'chipped:etched_stone_bricks','minecraft:chiseled_stone_bricks')
        self.put(x,y,z,keys[(1 if x%4==0 else 0)+(2 if z%7==0 else 0)])

    def lamp(self,x,y,z,hanging=False):
        self.put(x,y,z,'minecraft:lantern',hanging=hanging,waterlogged=False)


def moving_leaf(p,pivot,direction,length):
    p.zone=('North' if direction==1 else 'South')+' timber leaf'
    for n in range(length):
        z=pivot+direction*n
        # Deliberate seven-row transverse joints and three-board deck bays.
        for x in range(1187,1199):
            seam=(x-1187)%4==3
            if n%7==0:key='chipped:nailed_dark_oak_planks' if seam else 'chipped:stacked_dark_oak_planks'
            else:key='chipped:boxed_spruce_planks' if seam else 'minecraft:dark_oak_planks'
            p.put(x,70,z,key)
            if n%7==0:
                p.put(x,69,z,'chipped:detailed_dark_oak_planks' if seam else 'minecraft:dark_oak_log',**({} if seam else {'axis':'x'}))
        for x in (1187,1198):
            if n%7==0:
                for y in range(71,74):p.put(x,y,z,'minecraft:stripped_dark_oak_log',axis='y')
                p.put(x,74,z,'minecraft:dark_oak_slab',type='bottom',waterlogged=False)
            else:
                p.put(x,71,z,'minecraft:dark_oak_fence',waterlogged=False)
                # Low repeated V-bracing, with open views through each panel.
                level=72+(1 if n%7 in (1,5,6) else 0)
                p.put(x,level,z,'minecraft:dark_oak_stairs',facing='north' if n%7<4 else 'south',half='top',shape='straight',waterlogged=False)
        # The central traffic strip stays free of chains, posts and furniture.
        for x in range(1188,1198):
            for y in range(71,75):p.put(x,y,z,AIR)
    # All art that moves fits inside the reviewed glue envelope, including caps.


def bank_support(p,north):
    p.zone=('North' if north else 'South')+' cutwater and terrace'
    za,zb=(-1185,-1173) if north else (-1115,-1103)
    # Shaped abutment shoulders: narrow below, widening towards the deck.
    for y in range(60,70):
        width=4 if y<64 else 6 if y<67 else 7
        for z in range(za,zb+1):
            for x in range(1193-width,1193+width+1):
                if (abs(x-1193)>=width and z in (za,zb)) or (y<65 and (z-za)%7 in (3,4) and abs(x-1193)<width):continue
                p.stone(x,y,z)
    # A paved approach landing with projecting river overlooks and carved piers.
    for z in range(za,zb+1):
        for x in range(1186,1201):
            p.paving(x,70,z)
            for y in range(71,75):p.put(x,y,z,AIR)
        for x in (1186,1200):
            if (z-za)%4==0:
                p.stone(x,71,z);p.put(x,72,z,'minecraft:chiseled_stone_bricks')
                p.put(x,73,z,'minecraft:stone_brick_slab',type='double' if (z-za)%8==0 else 'bottom',waterlogged=False)
                if (z-za)%8==0:p.lamp(x,74,z)
            else:p.put(x,71,z,'minecraft:stone_brick_wall',waterlogged=False)
    # Recessed arch faces, visibly deeper than a flat textured pedestal.
    for x in (1185,1201):
        for zc in (za+3,za+9):
            # The smaller upstream bridge owns this shared branch arch face.
            if not north and x==1201 and zc==za+9:continue
            for z in range(zc-1,zc+2):
                for y in range(63,68):p.put(x,y,z,AIR)
            for dz in (-2,2):
                for y in range(62,68):p.stone(x,y,zc+dz)
            p.stair(x,68,zc-1,facing='south',half='top');p.stone(x,68,zc)
            p.stair(x,68,zc+1,facing='north',half='top')
    # Bank stairs rise only six blocks; stone terraces flank them with seating.
    start=-1202 if north else -1102
    for n in range(18):
        z=start+n
        y=min(70,64+n//2) if north else max(64,70-n//2)
        for x in range(1189,1198):
            for py in range(max(60,y-3),y):p.stone(x,py,z)
            if n>=12:p.paving(x,y,z)
            else:p.stair(x,y,z,facing='south' if north else 'north')
            for py in range(y+1,y+4):p.put(x,py,z,AIR)
    gardens=[(1181,za+2),(1181,zb-2),(1206,za+2),(1206,zb-2)]
    if not north:gardens[-1]=(1219,-1083)
    for x,z in gardens:
        for dx in range(-1,2):
            for dz in range(-1,2):p.stone(x+dx,68,z+dz)
        p.put(x,69,z,'supplementaries:planter',extended=False,waterlogged=False)
        p.put(x,70,z,'minecraft:flowering_azalea')
        p.put(x-2,69,z,'handcrafted:dark_oak_bench',facing='west',color='none',shape='single',waterlogged=False)
    if not north:
        for z in range(-1107,-1102):
            for y in range(71,75):p.put(1200,y,z,AIR)


def native_power(p,pivot):
    p.zone='Bank water power and visible gearing'
    # The exact proven water-wheel and two diagonal 2:1 gear reductions.
    for x in range(1223,1228):
        for y in range(65,73):
            for z in range(pivot-3,pivot+4):
                if x in (1223,1227) or z in (pivot-3,pivot+3) or y==65:p.stone(x,y,z)
                else:p.put(x,y,z,AIR)
    p.put(1225,68,pivot,'create:water_wheel',facing='west')
    p.put(1225,71,pivot-1,'minecraft:water')
    for x in range(1222,1225):p.put(x,68,pivot,'create:shaft',axis='x',waterlogged=False)
    p.put(1223,68,pivot,'create:andesite_encased_shaft',axis='x')
    p.put(1221,68,pivot,'create:cogwheel',axis='x',waterlogged=False)
    p.put(1221,69,pivot-1,'create:large_cogwheel',axis='x',waterlogged=False)
    for x in range(1216,1221):p.put(x,69,pivot-1,'create:shaft',axis='x',waterlogged=False)
    p.put(1215,69,pivot-1,'create:cogwheel',axis='x',waterlogged=False)
    p.put(1215,70,pivot,'create:large_cogwheel',axis='x',waterlogged=False)
    for x in range(1204,1215):
        p.put(x,70,pivot,'create:andesite_encased_shaft' if x==1209 else 'create:shaft',axis='x',**({} if x==1209 else {'waterlogged':False}))
    p.put(1203,70,pivot,'create:sequenced_gearshift',axis='x',vertical=False,state=0)
    for x in (1200,1201,1202):p.put(x,70,pivot,'create:shaft',axis='x',waterlogged=False)
    p.put(1199,70,pivot,'create:mechanical_bearing',facing='west')
    p.put(1203,71,pivot,'create:redstone_link',receiver=True,powered=False,facing='up')
    p.tag(1203,71,pivot,'{Transmitter:0b,FrequencyFirst:{id:"minecraft:compass",count:1},FrequencyLast:{id:"minecraft:iron_nugget",count:1}}')
    for x in range(1202,1229):
        p.wood_floor(x,66,pivot-4)
        if (x-1202)%4==0:p.stone(x,67,pivot-5)
        else:p.put(x,67,pivot-5,'minecraft:iron_bars',waterlogged=False)
    for x in (1204,1212,1228):
        p.put(x,67,pivot-4,'minecraft:barrel',facing='up',open=False)
        p.lamp(x,68,pivot-4)


def lodge(p,x,z,name):
    p.zone=name
    # A small chamfered bank pavilion with oriel, actual doors and layered roof.
    cells={(dx,dz) for dx in range(-3,4) for dz in range(-4,5)
           if not(abs(dx)==3 and abs(dz)==4)}
    for dx,dz in cells:
        wx,wz=x+dx,z+dz
        for y in range(64,70):p.stone(wx,y,wz)
        p.wood_floor(wx,70,wz)
        edge=any((dx+ox,dz+oz) not in cells for ox,oz in ((1,0),(-1,0),(0,1),(0,-1)))
        for y in range(71,77):
            if not edge:p.put(wx,y,wz,AIR)
            elif y==74:
                if abs(dz)==4:p.put(wx,y,wz,'minecraft:dark_oak_log',axis='x')
                else:p.put(wx,y,wz,'chipped:nailed_dark_oak_planks')
            elif ((abs(dx)==3 and dz%3==0) or (abs(dz)==4 and dx in (-2,0,2))):
                p.put(wx,y,wz,'minecraft:stripped_spruce_log',axis='y')
            else:p.put(wx,y,wz,'minecraft:white_terracotta')
    for y,half in ((71,'lower'),(72,'upper')):
        p.put(x, y,z+4,'mcwdoors:dark_oak_classic_door',facing='south',half=half,hinge='left',open=False,powered=False)
    for side in (-3,3):
        for dz in (-1,0,1):
            for dy,row in ((72,'bot'),(73,'top')):
                p.put(x+side,dy,z+dz,'mcwwindows:dark_oak_plank_window',facing='east',part=row+'_'+{-1:'r',0:'m',1:'l'}[dz])
        # Native parapets derive filled state from actual flower data. Do not
        # claim an unfilled planter has flowers merely by setting its state.
        p.put(x+side,71,z,'mcwwindows:dark_oak_log_parapet',facing='west' if side<0 else 'east',part='empty')
    for n in range(5):
        for dx,face in ((-4+n,'east'),(4-n,'west')):
            for dz in range(-5,6):
                # Two real copper bands divide the long timber roof.
                key='mcwroofs:dark_oak_roof' if dz not in (-2,2) else 'minecraft:weathered_cut_copper_stairs'
                if key.startswith('mcw'):p.put(x+dx,77+n,z+dz,key,facing=face,half='bottom',shape='straight')
                else:p.stair(x+dx,77+n,z+dz,key,face)
        if n:
            for dz in (-4,4):
                for dx in range(-4+n,5-n):
                    p.put(x+dx,76+n,z+dz,'chipped:boxed_dark_oak_planks' if dx%3==0 else 'minecraft:white_terracotta')
    # Furnishings serve the bridge operator, with a distinct rest corner.
    p.put(x-2,71,z-2,'handcrafted:dark_oak_desk',facing='south',**({'type':'1'} if 'type' in p.native.get('handcrafted:dark_oak_desk',{}) else {}))
    p.put(x-2,72,z-2,'minecraft:flower_pot')
    p.put(x-2,71,z,'handcrafted:dark_oak_chair',facing='north',color='none')
    p.put(x+2,71,z-2,'minecraft:barrel',facing='south',open=False)
    p.put(x+2,72,z-2,'minecraft:candle',candles=3,lit=True,waterlogged=False)
    p.put(x,71,z-3,'minecraft:cartography_table')
    p.put(x+1,71,z+1,'handcrafted:dark_oak_bench',facing='west',color='none',shape='single',waterlogged=False)
    p.lamp(x,76,z,True)
    # A real supported signpost, not a standing sign suspended beside the wall.
    p.stone(x+1,69,z+5)
    for py in (70,71):p.put(x+1,py,z+5,'minecraft:dark_oak_fence',waterlogged=False)
    p.sign(x+1,72,z+5,[name,'Lanternwater crossing','Two 55 degree leaves','Keep the channel clear'])


def control_balcony(p,z):
    p.zone='Carved control overlook and waiting nook'
    for x in range(1180,1186):
        for dz in range(-3,4):
            # Stepped corbels support a small balcony, keeping the water below
            # open between them rather than filling it with a building.
            p.paving(x,70,z+dz)
            if abs(dz)==3:
                for py in range(67,70):
                    if x>=1183-(py-67):p.stone(x,py,z+dz)
            if x==1180 or abs(dz)==3:
                if (x+dz)%3==0:p.stone(x,71,z+dz)
                else:p.put(x,71,z+dz,'minecraft:stone_brick_wall',waterlogged=False)
    p.stone(1182,71,z);p.stone(1182,72,z)
    p.put(1182,73,z,'minecraft:stone_button',face='floor',facing='north',powered=False)
    p.put(1183,72,z,'create:redstone_link',receiver=False,powered=False,facing='east')
    p.tag(1183,72,z,'{Transmitter:1b,FrequencyFirst:{id:"minecraft:compass",count:1},FrequencyLast:{id:"minecraft:iron_nugget",count:1}}')
    p.put(1181,71,z-2,'handcrafted:dark_oak_bench',facing='east',color='none',shape='single',waterlogged=False)
    p.stone(1184,71,z+2);p.lamp(1184,72,z+2)
    p.stone(1181,70,z+2)
    p.put(1181,71,z+2,'minecraft:dark_oak_fence',waterlogged=False)
    p.sign(1181,72,z+2,['DRAWBRIDGE CONTROL','Press once to open','Wait for both leaves','Press again to close'])


def build(registry,backup):
    p=Bascule(registry,backup)
    # Explicitly clear only the moving envelope over the open channel.
    p.zone='Moving-channel clearance'
    p.box(1187,69,-1172,1198,76,-1116,AIR)
    moving_leaf(p,-1172,1,29);moving_leaf(p,-1116,-1,28)
    bank_support(p,True);bank_support(p,False)
    native_power(p,-1172);native_power(p,-1116)
    lodge(p,1213,-1196,'North bridgekeeper')
    lodge(p,1213,-1091,'South signal room')
    for z in (-1178,-1110):control_balcony(p,z)
    p.landmark('Lanternwater drawbridge',1193,71,-1144,'transport',
        ['Original authored architecture','Two native Create bascules','55 degree opening','Open navigation channel'])
    p.cameras=[{'name':'water-approach','feet':[1168,64,-1144],'target':[1193,73,-1144]},
        {'name':'road-approach','feet':[1193,71,-1183],'target':[1193,73,-1138]},
        {'name':'river-quarter','feet':[1165,83,-1187],'target':[1196,72,-1148]},
        {'name':'bank-machinery','feet':[1221,70,-1183],'target':[1207,70,-1172]},
        {'name':'bridgekeeper','feet':[1213,71,-1194],'target':[1211,73,-1198]}]
    return p


def prepare(home):
    home=Path(home).resolve(); folder=home/'dashboard/settlement'
    if not home.is_relative_to(Path(r'D:\A World for Two\staging\world-tests')):
        raise UserError('This original prototype is private staging only')
    guard(1024**2,16*1024**2)
    registry=read_json(folder/'registry.json'); backup=read_json(folder/'backup-receipt.json')
    p=build(registry,backup['sha256'])
    check=require_material_rule(p.blocks,'Complete Lanternwater bridge and both bank lodges')
    output=home/'staging'/('authored-bascules-'+str(__import__('time').time_ns()))
    output.mkdir(parents=True,exist_ok=False)
    result=p.save(output/'prototype.json')
    manifest=result | {'created':utcnow(),'source_sha256':digest(Path(__file__)),
        'material_rule':check,'cameras':p.cameras,'systems':placed_systems(55),'radios':placed_radios(),
        'buttons':[[1182,73,-1178],[1182,73,-1110]],'groups':{k:len(v) for k,v in p.groups.items()},
        'clearance_estimate':clearance_estimate(55),'boat_clearance':'UNVERIFIED native collision envelope',
        'acceptance':'Actual native screenshots and functional commissioning pending; not inferred from source checks'}
    # Moving caps extend one block above the historical engineering envelope.
    for system in manifest['systems']:system['glue_max'][1]=74
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result),flush=True)
    return output


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--home',required=True,type=Path)
    prepare(parser.parse_args().home)
