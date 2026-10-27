"""Original terrain-fitted Lakeside Homestead templates and exact native construction plans.

No invented mod registry IDs: all material and state choices are checked against
the running server's registry export. These files are templates, not deployment proof.
"""
from __future__ import annotations

import argparse
import json
import math
import random
import re
import statistics
import uuid
from pathlib import Path

from control_room.common import Layout, REPO, UserError, atomic_write, digest, read_json, write_json, utcnow
from control_room.storage import Storage, GiB


class Plan:
    def __init__(self, registry, survey, center, backup, rotation=0):
        self.registry=registry
        self.native=registry['blocks']
        self.samples={(p['x'],p['z']):p for p in survey['samples']}
        self.protected={tuple(p) for row in survey['samples'] for p in row.get('block_entities',[])}
        self.step=min(abs(a-b) for a,b in zip(sorted({p[0] for p in self.samples}),sorted({p[0] for p in self.samples})[1:]))
        self.origin=min(p[0] for p in self.samples),min(p[1] for p in self.samples)
        self.cx,self.cz=center
        self.rotation=rotation%4
        self.backup=backup
        self.blocks={}
        self.tags={}
        self.commands=[]
        self.landmarks=[]
        self.features=[]
        self.zone='Welcome plaza'
        self.uses={}
        self.rng=random.Random(7344)

    def world(self,x,z):
        for _ in range(self.rotation):x,z=-z,x
        return self.cx+x,self.cz+z

    def height(self,x,z):
        x,z=self.world(x,z)
        ox,oz=self.origin
        gx=ox+math.floor((x-ox)/self.step)*self.step;gz=oz+math.floor((z-oz)/self.step)*self.step
        closest=[p for p in [(gx,gz),(gx+self.step,gz),(gx,gz+self.step),(gx+self.step,gz+self.step)] if p in self.samples]
        if not closest:closest=sorted(self.samples,key=lambda p:(p[0]-x)**2+(p[1]-z)**2)[:4]
        closest.sort(key=lambda p:(p[0]-x)**2+(p[1]-z)**2)
        if not closest:raise UserError('Actual terrain survey is required')
        if closest[0]==(x,z):return self.samples[closest[0]].get('ground_y',self.samples[closest[0]]['y'])
        weights=[1/max(.5,math.hypot(px-x,pz-z))**2 for px,pz in closest]
        return round(sum(self.samples[p].get('ground_y',self.samples[p]['y'])*w for p,w in zip(closest,weights))/sum(weights))

    def choose(self,*ids):
        for key in ids:
            if key in self.native:return key
        raise UserError('None of the requested actual block choices exists: '+', '.join(ids))

    def find(self,namespace,*words):
        matches=[key for key in self.native if key.startswith(namespace+':') and all(word in key.split(':')[1] for word in words)]
        return min(matches,key=lambda k:(len(k),k)) if matches else None

    def state(self,key,**properties):
        if key not in self.native:raise UserError('Unregistered block '+key)
        actual=self.native[key]
        selected={}
        for name,value in properties.items():
            value=str(value).lower()
            if name not in actual:continue
            if name=='facing' and value in ('north','east','south','west'):
                values=['north','east','south','west'];value=values[(values.index(value)+self.rotation)%4]
            if name=='axis' and self.rotation%2 and value in ('x','z'):value='z' if value=='x' else 'x'
            # This export lists enum display values; the server's exact native
            # property parser validates serialized spelling before any placement.
            if value not in [str(v).lower() for v in actual[name]]:raise UserError('Unregistered state '+key+' '+name+'='+value)
            selected[name]=value
        return key+('['+','.join(k+'='+v for k,v in sorted(selected.items()))+']' if selected else '')

    def put(self,x,y,z,key,**properties):
        if not -64<=y<320:raise UserError('A template exceeded the existing world height')
        wx,wz=self.world(x,z)
        if abs(wx-self.cx)>256 or abs(wz-self.cz)>256:raise UserError('Template exceeded the reviewed 512-block footprint')
        self.blocks[wx,y,wz]=self.state(key,**properties)
        self.tags.pop((wx,y,wz),None)
        if key!='minecraft:air':self.uses.setdefault(key.split(':')[0],set()).add(self.zone)
        if len(self.blocks)>550_000:raise UserError('Split construction into bounded neighborhoods')

    def box(self,x1,y1,z1,x2,y2,z2,key,**properties):
        for x in range(min(x1,x2),max(x1,x2)+1):
            for z in range(min(z1,z2),max(z1,z2)+1):
                for y in range(min(y1,y2),max(y1,y2)+1):self.put(x,y,z,key,**properties)

    def tag(self,x,y,z,nbt):
        self.tags[self.world(x,z)[0],y,self.world(x,z)[1]]=nbt

    def sign(self,x,y,z,lines):
        self.put(x,y,z,'minecraft:oak_sign',rotation=8,waterlogged=False)
        messages=[json.dumps(json.dumps({'text':line,'color':'dark_green'},ensure_ascii=False)) for line in (lines+['']*4)[:4]]
        self.tag(x,y,z,'{is_waxed:1b,front_text:{messages:['+','.join(messages)+'],color:"brown",has_glowing_text:0b}}')

    def chest(self,x,y,z,title,items=()):
        self.put(x,y,z,'minecraft:chest',facing='south',type='single',waterlogged=False)
        entries=[]
        for i,item in enumerate(items):
            if item not in self.registry['items']:raise UserError('Unregistered actual item '+item)
            entries.append('{Slot:'+str(i)+'b,id:'+json.dumps(item)+',count:1}')
            self.uses.setdefault(item.split(':')[0],set()).add(self.zone)
        self.tag(x,y,z,'{CustomName:'+json.dumps(json.dumps({'text':title}))+',Items:['+','.join(entries)+']}')

    def entity(self,kind,x,y,z,name,extra=''):
        if kind not in self.registry['entities']:raise UserError('Unregistered actual entity '+kind)
        if self.registry.get('entity_categories',{}).get(kind)=='monster':raise UserError('Hostile showcase entities belong outside the settlement')
        wx,wz=self.world(x,z)
        ident=uuid.uuid5(uuid.NAMESPACE_URL,'awft:'+self.registry['seed']+':'+name)
        integers=[int.from_bytes(ident.bytes[n:n+4],'big',signed=True) for n in range(0,16,4)]
        nbt='{UUID:[I;'+','.join(map(str,integers))+'],CustomName:'+json.dumps(json.dumps({'text':name})) + ',PersistenceRequired:1b'+extra+'}'
        self.commands.append(f'summon {kind} {wx+.5} {y} {wz+.5} '+nbt)
        self.uses.setdefault(kind.split(':')[0],set()).add(self.zone)

    def landmark(self,name,x,y,z,category,features):
        self.zone=name
        wx,wz=self.world(x,z)
        self.landmarks.append({'name':name,'dimension':'minecraft:overworld','x':wx,'y':y,'z':wz,'category':category,'features':features})

    def lantern(self,x,y,z):
        self.put(x,y,z,'minecraft:stone_bricks')
        self.box(x,y+1,z,x,y+3,z,'minecraft:spruce_fence')
        self.put(x,y+4,z,'minecraft:lantern',hanging=False,waterlogged=False)

    def platform(self,x,z,w,d,y):
        for px in range(x,x+w):
            for pz in range(z,z+d):
                ground=self.height(px,pz)-1
                for py in range(max(ground-1,y-10),y):self.put(px,py,pz,'minecraft:stone_bricks' if px in (x,x+w-1) or pz in (z,z+d-1) else 'minecraft:stone')
                self.put(px,y,pz,'minecraft:spruce_planks')

    def house(self,name,x,z,w,d,stories=1,roof='minecraft:dark_oak_stairs',category='Homes'):
        y=round(statistics.median(self.height(px,pz) for px,pz in [(x,z),(x+w-1,z),(x,z+d-1),(x+w-1,z+d-1),(x+w//2,z+d//2)]))
        self.landmark(name,x+w//2,y+1,z+d//2,category,['Detailed timber-frame exterior','Furnished interior'])
        self.platform(x,z,w,d,y)
        h=stories*5
        self.box(x-1,y+1,z-1,x+w,y+h+w//2+3,z+d,'minecraft:air')
        for py in range(1,h+1):
            for px in range(w):
                material='minecraft:stripped_spruce_log' if px%5==0 or px==w-1 or py%5==0 else 'minecraft:calcite'
                for pz in (0,d-1):self.put(x+px,y+py,z+pz,material,axis='x' if py%5==0 else 'y')
            for pz in range(1,d-1):
                material='minecraft:stripped_spruce_log' if pz%5==0 or py%5==0 else 'minecraft:calcite'
                for px in (0,w-1):self.put(x+px,y+py,z+pz,material,axis='z' if py%5==0 else 'y')
        for story in range(stories):
            if story:self.box(x+1,y+story*5,z+1,x+w-2,y+story*5,z+d-2,'minecraft:spruce_planks')
            for px in range(2,w-2,5):
                for pz in (0,d-1):
                    for oy in (2,3):self.box(x+px,y+story*5+oy,z+pz,x+min(w-2,px+1),y+story*5+oy,z+pz,'minecraft:glass_pane')
                    self.put(x+px,y+story*5+1,z+pz,'minecraft:spruce_trapdoor',facing='south' if pz else 'north',half='top',open=True)
            for pz in range(2,d-2,5):
                for px in (0,w-1):
                    for oy in (2,3):self.put(x+px,y+story*5+oy,z+pz,'minecraft:glass_pane')
            self.put(x+w//2,y+story*5+4,z+d//2,'minecraft:lantern',hanging=True,waterlogged=False)
        self.box(x+1,y+h,z+1,x+w-2,y+h,z+d-2,'minecraft:spruce_planks')
        for offset in range((w+2)//2+1):
            for px,facing in ((x-1+offset,'east'),(x+w-offset,'west')):
                self.box(px,y+h+1+offset,z-1,px,y+h+1+offset,z+d,roof,facing=facing,half='bottom',shape='straight',waterlogged=False)
                if offset>0:
                    for pz in (z,z+d-1):self.box(px,y+h+1,pz,px,y+h+offset,pz,'minecraft:spruce_planks')
        doorx=x+w//2
        for part,py in [('lower',y+1),('upper',y+2)]:self.put(doorx,py,z+d-1,'minecraft:oak_door',facing='north',half=part,hinge='left',open=False,powered=False)
        self.box(doorx-1,y,z+d,doorx+1,y,z+d+2,'minecraft:stone_bricks')
        self.lantern(x+1,y,z+d+2);self.lantern(x+w-2,y,z+d+2)
        self.sign(doorx+2,y+1,z+d+1,[name,'The Lakeside','Homestead'])
        self.put(x+2,y+1,z+2,'minecraft:crafting_table')
        self.put(x+3,y+1,z+2,'minecraft:furnace',facing='south',lit=False)
        if stories>1:
            for n in range(5):
                self.put(x+w-3,y+1+n,z+2+n,'minecraft:spruce_stairs',facing='south',half='bottom',shape='straight',waterlogged=False)
                self.box(x+w-3,y+2+n,z+2+n,x+w-3,y+5+n,z+2+n,'minecraft:air')
        return y

    def save(self,path):
        collisions=self.protected & self.blocks.keys()
        if collisions:raise UserError('The plan intersects existing block entities; relocate the affected footprint: '+str(sorted(collisions)[:20]))
        palette=sorted(set(self.blocks.values()));indices={s:i for i,s in enumerate(palette)}
        blocks=[[x,y,z,indices[s]] for (x,y,z),s in sorted(self.blocks.items(),key=lambda kv:(kv[0][0]//16,kv[0][2]//16,kv[0][1],kv[0][0],kv[0][2]))]
        output={'format':'awft-native-settlement:1','name':'The Lakeside Homestead','created':utcnow(),
                'seed':self.registry['seed'],'world_path':self.registry['world_path'],'backup_sha256':self.backup,
                'bounds':[min(p[0] for p in self.blocks),min(p[2] for p in self.blocks),max(p[0] for p in self.blocks),max(p[2] for p in self.blocks)],
                'palette':palette,'blocks':blocks,'block_entities':[{'pos':list(p),'nbt':tag} for p,tag in self.tags.items()],
                'commands':self.commands,'landmarks':self.landmarks,
                'coverage':{key:sorted(values) for key,values in self.uses.items()},
                'validation':'Templates generated from actual native registry IDs. Placement, functionality and visual acceptance remain pending.'}
        atomic_write(path,json.dumps(output,separators=(',',':'),ensure_ascii=False)+'\n')
        if path.stat().st_size>32*1024**2:raise UserError('Split the neighborhood plan before native admission')
        return {'path':str(path),'sha256':digest(path),'blocks':len(blocks),'palette':len(palette),'block_entities':len(self.tags),'landmarks':len(self.landmarks)}


def furniture(plan,key,x,y,z,**properties):
    if key and key in plan.native:plan.put(x,y,z,key,**properties)


def beds(plan,x,y,z,color='red',kind='minecraft'):
    key='minecraft:'+color+'_bed' if kind=='minecraft' else plan.choose('multibeds:classic','minecraft:'+color+'_bed')
    plan.put(x,y,z,key,facing='north',part='foot',occupied=False,waterlogged=False)
    plan.put(x,y,z-1,key,facing='north',part='head',occupied=False,waterlogged=False)


def kitchen(plan,x,y,z):
    for ox in range(9):
        material='farmersdelight:spruce_cabinet' if ox%3 else 'handcrafted:spruce_counter'
        furniture(plan,material,x+ox,y,z,facing='south')
    furniture(plan,'farmersdelight:stove',x+2,y,z,facing='south',lit=True)
    furniture(plan,'farmersdelight:cooking_pot',x+2,y+1,z,facing='south')
    furniture(plan,'farmersdelight:cutting_board',x+4,y+1,z)
    furniture(plan,'farm_and_charm:mincer',x+6,y+1,z,facing='south')
    furniture(plan,'farm_and_charm:roaster',x+8,y+1,z,facing='south')
    furniture(plan,'kaleidoscope_cookery:chopping_board',x+1,y+1,z)
    tea=plan.find('kaleidoscope_cookery','tea')
    furniture(plan,tea,x+5,y+1,z)
    plan.chest(x,y,z+2,'Kitchen pantry',tuple(k for k in ('farmersdelight:iron_knife','farmersdelight:cabbage','farmersdelight:tomato','farm_and_charm:barley','minecraft:wheat','minecraft:carrot') if k in plan.registry['items']))


def cottage(plan):
    x,z,w,d=-60,-48,31,23
    y=plan.house('The Lakeside Cottage',x,z,w,d,2)
    kitchen(plan,x+2,y+1,z+2)
    plan.box(x+1,y+1,z+10,x+12,y+4,z+10,'minecraft:oak_planks')
    plan.box(x+6,y+1,z+10,x+7,y+2,z+10,'minecraft:air')
    for ox in range(2,6):
        furniture(plan,'handcrafted:spruce_table',x+ox,y+1,z+7)
        furniture(plan,'handcrafted:spruce_chair',x+ox,y+1,z+6,facing='south')
        furniture(plan,'handcrafted:spruce_chair',x+ox,y+1,z+8,facing='north')
    plan.box(x+2,y+1,z+14,x+6,y+4,z+15,'minecraft:stone_bricks')
    plan.box(x+3,y+1,z+15,x+5,y+2,z+15,'minecraft:air')
    plan.put(x+4,y+1,z+15,'minecraft:campfire',lit=True,signal_fire=False,waterlogged=False,facing='south')
    plan.box(x+3,y+4,z+14,x+5,y+20,z+15,'minecraft:bricks')
    furniture(plan,'handcrafted:spruce_couch',x+4,y+1,z+19,facing='north')
    furniture(plan,'handcrafted:spruce_couch',x+5,y+1,z+19,facing='north')
    furniture(plan,'handcrafted:spruce_side_table',x+7,y+1,z+18)
    furniture(plan,'supplementaries:book_pile',x+7,y+2,z+18)
    for pz in range(z+12,z+19):plan.put(x+13,y+1,pz,'minecraft:bookshelf')
    furniture(plan,'xercamusic:piano',x+18,y+1,z+4,facing='south')
    furniture(plan,'handcrafted:spruce_bench',x+18,y+1,z+6,facing='north')
    furniture(plan,'xercamusic:music_box',x+21,y+1,z+4)
    furniture(plan,'exposure:lightroom',x+18,y+1,z+12)
    camera=next((k for k in plan.registry['items'] if k=='exposure:camera'),None)
    if camera:plan.chest(x+19,y+1,z+12,'Photography and memories',[camera])
    for px in (x+18,x+20,x+22):
        furniture(plan,'sophisticatedbackpacks:iron_backpack',px,y+1,z+19,facing='south')
    for px in (x+3,x+5):beds(plan,px,y+6,z+4,'red',kind='multibeds')
    beds(plan,x+19,y+6,z+4,'white')
    plan.box(x+11,y+6,z+1,x+11,y+9,z+10,'minecraft:oak_planks')
    plan.box(x+11,y+6,z+8,x+11,y+7,z+8,'minecraft:air')
    furniture(plan,'handcrafted:spruce_desk',x+5,y+6,z+15,facing='north')
    furniture(plan,'handcrafted:spruce_chair',x+5,y+6,z+16,facing='north')
    plan.box(x+12,y+5,z+d,x+23,y+5,z+d+4,'minecraft:spruce_planks')
    for px in range(x+12,x+24):plan.put(px,y+6,z+d+4,'minecraft:spruce_fence')
    for px in (x+12,x+23):plan.box(px,y+1,z+d+4,px,y+4,z+d+4,'minecraft:stripped_spruce_log',axis='y')
    plan.put(x+18,y+6,z+d-1,'minecraft:air');plan.put(x+18,y+7,z+d-1,'minecraft:air')
    furniture(plan,'handcrafted:spruce_chair',x+15,y+6,z+d+2,facing='south')
    return y


def plaza(plan):
    y=plan.height(0,0)
    plan.landmark('Welcome Home',0,y+1,0,'Welcome',['Official spawn plaza','Fountain','Seating','Optional village tour'])
    for x in range(-15,16):
        for z in range(-15,16):
            radius=math.hypot(x,z)
            if radius>15:continue
            for py in range(min(y-1,plan.height(x,z)-1),y):plan.put(x,py,z,'minecraft:stone')
            plan.put(x,y,z,'minecraft:polished_andesite' if radius>13 or abs(x)<2 or abs(z)<2 else 'minecraft:stone_bricks')
            plan.box(x,y+1,z,x,y+5,z,'minecraft:air')
    for x in range(-4,5):
        for z in range(-4,5):
            distance=math.hypot(x,z)
            if distance<4.5:plan.put(x,y,z,'minecraft:stone_bricks')
            if distance<3.5:plan.put(x,y+1,z,'minecraft:water')
            elif distance<4.5:plan.put(x,y+1,z,'minecraft:stone_bricks')
    plan.box(0,y+1,0,0,y+4,0,'minecraft:chiseled_stone_bricks')
    plan.put(0,y+5,0,'minecraft:sea_lantern')
    for x,z in [(-11,-8),(11,-8),(-11,8),(11,8)]:plan.lantern(x,y,z)
    for x,z in [(-10,0),(9,0),(0,-11)]:furniture(plan,'handcrafted:spruce_bench',x,y+1,z,facing='south')
    plan.sign(6,y+1,7,['A World for Two','Welcome Home','KG & Sera','Follow the lanterns'])
    plan.sign(-7,y+1,8,['Optional village tour','Cottage - Gardens','Castle - Workshop','Station - Harbor'])
    plan.spawn=(0,y+1,10)
    return y


def path(plan,a,b,width=3):
    ax,az=a;bx,bz=b
    length=max(1,round(math.hypot(bx-ax,bz-az)))
    for i in range(length+1):
        t=i/length
        x=round(ax+(bx-ax)*t+math.sin(t*math.pi)*2);z=round(az+(bz-az)*t)
        y=plan.height(x,z)-1
        for ox in range(-width//2+1,width//2+1):
            for oz in range(-width//2+1,width//2+1):
                plan.put(x+ox,y,z+oz,'minecraft:gravel' if plan.rng.random()<.18 else 'minecraft:cobblestone')
                plan.box(x+ox,y+1,z+oz,x+ox,y+3,z+oz,'minecraft:air')
        if i%18==0:plan.lantern(x+3,y,z)


def gardens(plan):
    x,z=24,-64;y=plan.height(x,z)
    plan.landmark('Sunlit Gardens and Vineyard',x,y+1,z,'Gardens',['Crop garden','Orchard','Vinery','Picnic area'])
    for row in range(5):
        for n in range(24):
            px,pz=x+n,z+row*4
            py=plan.height(px,pz)-1
            plan.put(px,py,pz,'minecraft:farmland',moisture=7)
            crop=['minecraft:wheat','minecraft:carrots','minecraft:potatoes','farmersdelight:cabbages','farmersdelight:tomatoes'][row]
            if crop not in plan.native:crop='minecraft:wheat'
            props=plan.native[crop];age=max(map(int,props.get('age',['0'])))
            plan.put(px,py+1,pz,crop,age=age)
            if row%2==0:plan.put(px,py,pz+1,'minecraft:water')
    for px in range(26,53,9):
        for pz in (-84,-96):
            py=plan.height(px,pz)
            plan.box(px,py,pz,px,py+4,pz,plan.choose('vinery:apple_log','minecraft:oak_log'),axis='y')
            for ox in range(-2,3):
                for oz in range(-2,3):
                    if abs(ox)+abs(oz)<=3:plan.put(px+ox,py+4,pz+oz,plan.choose('vinery:apple_leaves','minecraft:oak_leaves'),persistent=True)
    for px in range(24,50,5):
        py=plan.height(px,-77)
        furniture(plan,'vinery:spruce_lattice',px,py,-77)
        grape=plan.find('vinery','grapevine')
        furniture(plan,grape,px,py+1,-77)
    py=plan.height(12,-34)
    plan.put(12,py,-34,'minecraft:campfire',lit=True,waterlogged=False,signal_fire=False)
    for px,pz in [(9,-34),(15,-34),(12,-37)]:furniture(plan,'handcrafted:spruce_bench',px,py,pz,facing='south')


def greenhouse(plan):
    x,z,w,d=58,-84,17,27;y=plan.height(x+w//2,z+d//2)
    plan.landmark('The Glasshouse',x+w//2,y+1,z+d//2,'Gardens',['Greenhouse','Flower nursery','Seasonal farming'])
    plan.platform(x,z,w,d,y)
    plan.box(x,y+1,z,x+w-1,y+7,z+d-1,'minecraft:air')
    for px in range(w):
        for pz in (0,d-1):plan.box(x+px,y+1,z+pz,x+px,y+5,z+pz,'minecraft:glass' if px%4 else 'minecraft:stripped_oak_log')
    for pz in range(d):
        for px in (0,w-1):plan.box(x+px,y+1,z+pz,x+px,y+5,z+pz,'minecraft:glass' if pz%4 else 'minecraft:stripped_oak_log')
    for offset in range(w//2+1):
        for px in (x+offset,x+w-1-offset):plan.box(px,y+6+offset//2,z,px,y+6+offset//2,z+d-1,'minecraft:glass')
    for px in range(x+2,x+w-2):
        if px%4==0:continue
        for pz in range(z+2,z+d-2):
            plan.put(px,y,pz,'minecraft:dirt')
            if pz%3==0:plan.put(px,y+1,pz,plan.rng.choice(['minecraft:cornflower','minecraft:oxeye_daisy','minecraft:lily_of_the_valley']))
    plan.box(x+w//2,y+1,z+d-1,x+w//2,y+2,z+d-1,'minecraft:air')
    plan.sign(x+w//2+2,y+1,z+d,['The Glasshouse','Flowers, seedlings','& quiet mornings'])


def castle(plan):
    x,z,w,d=-112,-130,43,37;y=plan.height(x+w//2,z+d//2)
    plan.landmark('Rosewater Castle',x+w//2,y+1,z+d//2,'Castle',['Explorable castle','Throne hall','Royal suite','Rose and fairy gardens'])
    plan.platform(x,z,w,d,y)
    plan.box(x,y+1,z,x+w-1,y+16,z+d-1,'minecraft:air')
    for px in range(w):
        for pz in (0,d-1):
            plan.box(x+px,y+1,z+pz,x+px,y+8,z+pz,'minecraft:stone_bricks')
            if px%2==0:plan.put(x+px,y+9,z+pz,'minecraft:stone_brick_wall')
    for pz in range(d):
        for px in (0,w-1):
            plan.box(x+px,y+1,z+pz,x+px,y+8,z+pz,'minecraft:stone_bricks')
            if pz%2==0:plan.put(x+px,y+9,z+pz,'minecraft:stone_brick_wall')
    for cx,cz in [(x+3,z+3),(x+w-4,z+3),(x+3,z+d-4),(x+w-4,z+d-4)]:
        for ox in range(-5,6):
            for oz in range(-5,6):
                radius=math.hypot(ox,oz)
                if radius>5.3:continue
                plan.box(cx+ox,y+1,cz+oz,cx+ox,y+18,cz+oz,'minecraft:stone_bricks' if radius>4 else 'minecraft:air')
                for py in (y+6,y+12,y+18):plan.put(cx+ox,py,cz+oz,'minecraft:stone_bricks')
        for offset in range(7):
            rr=5.5-offset*.8
            for ox in range(-6,7):
                for oz in range(-6,7):
                    if math.hypot(ox,oz)<=rr:plan.put(cx+ox,y+19+offset,cz+oz,'minecraft:dark_prismarine')
        plan.put(cx,y+26,cz,'minecraft:lightning_rod',facing='up',waterlogged=False,powered=False)
        for py in (y+4,y+10,y+16):plan.put(cx,y+py-y,cz+5,'minecraft:glass_pane')
    hallx,hallz=x+11,z+5
    for px in range(hallx,hallx+21):
        for pz in range(hallz,hallz+21):
            plan.put(px,y,pz,'minecraft:polished_diorite')
            if px in (hallx,hallx+20) or pz in (hallz,hallz+20):plan.box(px,y+1,pz,px,y+13,pz,'minecraft:calcite')
    plan.box(hallx+1,y+7,hallz+1,hallx+19,y+7,hallz+19,'minecraft:birch_planks')
    plan.box(hallx+1,y+14,hallz+1,hallx+19,y+14,hallz+19,'minecraft:birch_planks')
    for ox in range(12):
        for px,facing in ((hallx-1+ox,'east'),(hallx+21-ox,'west')):plan.box(px,y+15+ox,hallz-1,px,y+15+ox,hallz+21,'minecraft:dark_prismarine_stairs',facing=facing,half='bottom',shape='straight',waterlogged=False)
    for px in range(hallx+3,hallx+20,4):
        for py in (y+3,y+9):plan.box(px,py,hallz+20,px+1,py+2,hallz+20,'minecraft:glass_pane')
    plan.box(hallx+9,y+1,hallz+20,hallx+11,y+4,hallz+20,'minecraft:air')
    plan.box(x+w//2-2,y+1,z+d-1,x+w//2+2,y+5,z+d-1,'minecraft:air')
    throne=plan.find('mythrais','throne') or plan.find('handcrafted','spruce','chair')
    for px in (hallx+8,hallx+12):furniture(plan,throne,px,y+1,hallz+3,facing='south')
    for pz in range(hallz+4,hallz+20):plan.box(hallx+9,y+1,pz,hallx+11,y+1,pz,'minecraft:red_carpet')
    beds(plan,hallx+4,y+8,hallz+5,'purple',kind='multibeds')
    for pz in range(hallz+9,hallz+17):plan.put(hallx+18,y+8,pz,'minecraft:bookshelf')
    furniture(plan,'xercamusic:piano',hallx+12,y+8,hallz+6,facing='south')
    for px in range(x+12,x+w-12,4):
        for pz in range(z+d-9,z+d-2,3):
            plan.put(px,y+1,pz,'minecraft:rose_bush',half='lower');plan.put(px,y+2,pz,'minecraft:rose_bush',half='upper')
    furniture(plan,'fairytales:fairy_connection_table',x+9,y+1,z+d-9)
    for px in (hallx+4,hallx+16):
        for pz in (hallz+5,hallz+16):plan.put(px,y+6,pz,'minecraft:lantern',hanging=True,waterlogged=False)
    for px in (hallx+5,hallx+15):plan.lantern(px,y,hallz+23)
    plan.sign(x+w//2+4,y+1,z+d+1,['Rosewater Castle','Royal rooms upstairs','Fairy and rose garden','A peaceful retreat'])


def barn(plan):
    x,z=78,-63;y=plan.house('Bramble Barn and Stable',x,z,21,19,1,category='Animals')
    furniture(plan,'farm_and_charm:feeding_trough',x+3,y+1,z+5)
    furniture(plan,'farm_and_charm:chicken_coop',x+14,y+1,z+5)
    furniture(plan,'farm_and_charm:pet_bowl',x+5,y+1,z+7)
    for px in range(x+2,x+19,4):plan.put(px,y+1,z+12,'minecraft:hay_block',axis='y')
    for px in range(x-1,x+25):
        for pz in (z+22,z+37):plan.put(px,plan.height(px,pz),pz,'minecraft:oak_fence')
    for pz in range(z+22,z+38):
        for px in (x-1,x+24):plan.put(px,plan.height(px,pz),pz,'minecraft:oak_fence')
    for kind,px,pz,name in [('minecraft:cow',x+5,z+27,'Clover'),('minecraft:cow',x+9,z+27,'Buttercup'),('minecraft:sheep',x+14,z+28,'Cloud'),('minecraft:horse',x+5,z+8,'Willow'),('minecraft:chicken',x+16,z+8,'Pip')]:plan.entity(kind,px,max(y+1,plan.height(px,pz)),pz,name)
    plan.chest(x+2,y+1,z+3,'Animal care',tuple(k for k in ('farm_and_charm:dog_food','minecraft:wheat','minecraft:carrot','minecraft:lead','minecraft:name_tag','doggytalents:training_treat') if k in plan.registry['items']))


def giant_tree(plan):
    x,z=-138,-45;y=plan.height(x,z)
    plan.landmark('The Lantern Tree',x,y+20,z,'Nature',['Giant tree','Treehouse','Photography overlook','Hanging bridges'])
    # Original sculpted landmark. The actual Giant Tree mod's growth items are supplied below.
    for py in range(35):
        r=2 if py<20 else 1
        for ox in range(-r,r+1):
            for oz in range(-r,r+1):
                if ox*ox+oz*oz<=r*r+1:plan.put(x+ox,y+py,z+oz,'minecraft:oak_log',axis='y')
    for angle,height in [(0,20),(1.5,26),(3,24),(4.5,29)]:
        for n in range(13):
            px=x+round(math.cos(angle)*n);pz=z+round(math.sin(angle)*n)
            plan.put(px,y+height+n//3,pz,'minecraft:oak_log',axis='x' if abs(math.cos(angle))>.5 else 'z')
        cx=x+round(math.cos(angle)*10);cz=z+round(math.sin(angle)*10)
        for ox in range(-9,10):
            for oz in range(-9,10):
                for oy in range(-3,4):
                    if (ox/9)**2+(oz/9)**2+(oy/4)**2<1:plan.put(cx+ox,y+height+4+oy,cz+oz,'minecraft:oak_leaves',persistent=True,distance=1)
    for px in range(x-8,x+9):
        for pz in range(z-8,z+9):
            if math.hypot(px-x,pz-z)<9 and abs(px-x)+abs(pz-z)>4:plan.put(px,y+17,pz,'minecraft:oak_planks')
    for n in range(36):
        ring=[(-5+i,-5) for i in range(10)]+[(5,-5+i) for i in range(10)]+[(5-i,5) for i in range(10)]+[(-5,5-i) for i in range(10)]
        px,pz=ring[n%len(ring)]
        plan.put(x+px,y+n//2,z+pz,'minecraft:oak_slab',type='bottom' if n%2==0 else 'top',waterlogged=False)
    for ox,oz in [(-7,0),(7,0),(0,-7),(0,7)]:
        plan.put(x+ox,y+18,z+oz,'minecraft:oak_fence');plan.put(x+ox,y+19,z+oz,'minecraft:lantern',hanging=False,waterlogged=False)
    plan.chest(x+4,y+18,z+4,'Giant Tree and observation supplies',tuple(k for k in plan.registry['items'] if k.startswith('gianttree:'))[:12])
    plan.sign(x+6,y+1,z+7,['The Lantern Tree','Hand-sculpted landmark','Grow your own with','the Giant Tree supplies'])


def harbor(plan):
    y=64
    plan.landmark('Lanternwater Harbor',0,y+1,112,'Harbor',['Fishing pier','Sailing ship berth','Shipyard','Treasure and diving supplies'])
    for z in range(18,145):
        for x in range(-3,4):plan.put(x,y,z,'minecraft:spruce_planks')
        if z%12==0:
            for x in (-3,3):
                plan.box(x,y-12,z,x,y+1,z,'minecraft:stripped_spruce_log',axis='y')
                plan.put(x,y+2,z,'minecraft:lantern',hanging=False,waterlogged=False)
    for x in range(-25,26):
        for z in range(108,115):plan.put(x,y,z,'minecraft:spruce_planks')
        if x%8==0:
            for z in (108,114):plan.box(x,y-12,z,x,y+1,z,'minecraft:stripped_spruce_log',axis='y')
    for x,z in [(-23,110),(22,110)]:
        furniture(plan,'aquaculture:worm_farm',x,y+1,z)
        furniture(plan,'smallships:dockyard',x+1,y+1,z,facing='north')
    items=tuple(k for k in plan.registry['items'] if k.startswith(('aquaculture:','fishofthieves:','oceansdelight:')) and any(word in k for word in ('fishing_rod','tackle_box','bait','knife')))
    plan.chest(-22,y+1,112,'Sea of Thieves fishing',items[:18])
    items=tuple(k for k in plan.registry['items'] if k.startswith(('smallships:','hybrid_aquatic:')) and any(word in k for word in ('sail','cog','galley','brigg','diving','mask','fin','sloop')))
    plan.chest(21,y+1,112,'Ships and diving equipment',items[:18])
    plan.sign(4,y+1,95,['Lanternwater Harbor','Ships, fishing, diving','& distant adventures'])
    x,z=37,117
    plan.landmark('The Lighthouse',x,y+1,z,'Harbor',['Navigation beacon','Scenic viewpoint'])
    for py in range(24):
        radius=4 if py<19 else 5
        for ox in range(-radius,radius+1):
            for oz in range(-radius,radius+1):
                distance=math.hypot(ox,oz)
                if distance<=radius:plan.put(x+ox,y+py,z+oz,('minecraft:red_terracotta' if py//4%2 else 'minecraft:calcite') if distance>=radius-1 or py in (0,18) else 'minecraft:air')
    plan.box(x-2,y+20,z-2,x+2,y+22,z+2,'minecraft:glass')
    plan.put(x,y+21,z,'minecraft:sea_lantern')
    plan.box(x-5,y+24,z-5,x+5,y+24,z+5,'minecraft:dark_oak_slab',type='bottom',waterlogged=False)
    plan.box(25,y,114,37,y,118,'minecraft:spruce_planks')
    for py in range(y+1,y+20):plan.put(x+2,py,z+2,'minecraft:ladder',facing='west',waterlogged=False)
    for px in range(x-2,x+3):
        for pz in range(z-2,z+3):plan.box(px,y+20,pz,px,y+22,pz,'minecraft:air')
    plan.put(x,y+21,z,'minecraft:sea_lantern')


def engineering(plan):
    x,z=-92,18;y=plan.house('Waterwheel Works',x,z,25,23,1,category='Engineering')
    # A water-powered shaft line, clutch and press. The lever starts in the stop position.
    wx,wz=x-5,z+9
    plan.box(wx-2,y-1,wz-2,wx+2,y+6,wz+2,'minecraft:stone_bricks')
    plan.box(wx-1,y+1,wz-1,wx+1,y+5,wz+1,'minecraft:air')
    plan.put(wx,y+3,wz,'create:water_wheel',facing='west')
    plan.put(wx,y+6,wz-1,'minecraft:water')
    for px in range(wx+1,x+17):plan.put(px,y+3,wz,'create:shaft',axis='x',waterlogged=False)
    plan.put(x+8,y+3,wz,'create:clutch',axis='x',powered=True)
    plan.put(x+8,y+3,wz+1,'minecraft:stone_bricks')
    plan.put(x+8,y+4,wz+1,'minecraft:lever',face='floor',facing='north',powered=True)
    plan.put(x+17,y+3,wz,'create:mechanical_press',facing='north')
    plan.put(x+17,y+1,wz,'create:depot',waterlogged=False)
    plan.sign(x+10,y+1,wz+4,['Waterwheel press','Lever: start / stop','Place an ingot on','the depot to press'])
    plan.put(x+20,y+1,z+3,'create:millstone')
    plan.put(x+18,y+1,z+3,'create:mechanical_arm',facing='north')
    plan.put(x+18,y+1,z+5,'create:basin')
    furniture(plan,'sliceanddice:slicer',x+20,y+1,z+6,facing='south')
    furniture(plan,plan.find('createaddition','rolling_mill'),x+5,y+1,z+3,facing='south')
    furniture(plan,plan.find('createdeco','workshop'),x+4,y+1,z+17)
    for n in range(4):plan.put(x+3,y+2+n,z+15,'create:chute',facing='down',waterlogged=False)
    plan.chest(x+3,y+1,z+15,'Native chutes: vertical logistics',['minecraft:wheat'])
    plan.sign(x+5,y+1,z+15,['Native Create Chutes','Vertical and diagonal','item transport','No extra pipe mod'])
    plan.put(x+4,y+1,z+8,'overpressure:item_pump',facing='east',waterlogged=False)
    for n in range(5,14):plan.put(x+n,y+1,z+8,'overpressure:pneumatic_tube',east=True,west=True,has_connection=True,waterlogged=False)
    plan.chest(x+14,y+1,z+8,'Pneumatic delivery')
    plan.chest(x+3,y+1,z+8,'Pneumatic supply',['minecraft:iron_ingot','minecraft:wheat'])
    plan.sign(x+12,y+1,z+11,['Pneumatic logistics','Overpressure network','Commissioning checks','before regular use'])
    hyz=z+30
    for px in range(x+7,x+50):
        plan.put(px,y,hyz,'minecraft:smooth_stone')
        plan.put(px,y+1,hyz,'create_hypertube:hypertube',east_west=True,north_south=False,up_down=False,connected=True,waterlogged=False)
    for px,facing in [(x+6,'west'),(x+50,'east')]:
        plan.put(px,y+1,hyz,'create_hypertube:hypertube_entrance',facing=facing,open=True,locked=False,power=15,powered=True,waterlogged=False)
        plan.put(px,y,hyz,'minecraft:redstone_block')
    plan.landmark('Copperway Hypertube',x+7,y+1,hyz,'Transport',['Player transport','Multiple chunk boundaries','Two powered entrances'])
    items=tuple(k for k in plan.registry['items'] if k.startswith(('create:','createaddition:','create_dragons_plus:')) and any(w in k for w in ('wrench','goggle','sand_paper','crafting_blueprint')))
    plan.chest(x+3,y+1,z+3,'Engineering tools',items[:18])


def station(plan):
    x,z=57,27;y=plan.house('Rosewater Railway Station',x,z,23,19,1,category='Transport')
    railx=x+30
    rail_y=max(plan.height(railx,pz) for pz in range(0,96,8))+1
    plan.landmark('Scenic Railway',railx,rail_y+1,34,'Transport',['Create track','Passenger and cargo platforms','Steam n Rails details'])
    for pz in range(0,112):
        for px in range(railx-2,railx+3):
            plan.put(px,rail_y-1,pz,'minecraft:stone_bricks')
            if pz%12<3:plan.box(px,max(45,plan.height(px,pz)-6),pz,px,rail_y-2,pz,'minecraft:stone_bricks')
        plan.box(railx,rail_y,pz,railx,rail_y+5,pz,'minecraft:air')
        plan.put(railx,rail_y,pz,'create:track',shape='zo',waterlogged=False)
    for px in range(x+20,railx):
        for pz in range(z-3,z+26):plan.put(px,rail_y,pz,'minecraft:spruce_planks')
    for pz in range(z-2,z+23,8):plan.lantern(railx-2,rail_y,pz)
    for pz in (z+2,z+10):furniture(plan,'handcrafted:spruce_bench',x+20,rail_y+1,pz,facing='east')
    furniture(plan,'create:track_station',railx-1,rail_y+1,z+8,facing='east')
    plan.chest(x+3,y+1,z+3,'Railway operations',tuple(k for k in plan.registry['items'] if k.startswith(('create:','railways:')) and any(w in k for w in ('schedule','conductor','whistle','signal','station','train_controls')))[:18])
    plan.sign(railx-3,rail_y+1,z+23,['Scenic Railway','Passenger platform','Train commissioning','and route checks'])


def village_life(plan):
    for name,x,z,w,d in [('The Lantern and Anchor',-51,35,21,19),('Letters and Little Things',28,6,17,15),('The Makers Guild',26,-25,21,17),('The Sea Glass Gallery',-48,3,19,15)]:
        y=plan.house(name,x,z,w,d,1,category='Village')
        if 'Anchor' in name:
            kitchen(plan,x+2,y+1,z+2)
            for pz in (z+7,z+12):
                furniture(plan,'handcrafted:spruce_table',x+10,y+1,pz)
                furniture(plan,'handcrafted:spruce_chair',x+9,y+1,pz,facing='east')
            for px in range(x+2,x+6):furniture(plan,'vinery:spruce_wine_rack_big',px,y+1,z+14)
            furniture(plan,'vinery:apple_press',x+15,y+1,z+3)
        elif 'Letters' in name:
            furniture(plan,'envelope:mailbox',x+2,y+1,z+3,facing='south')
            for px in range(x+4,x+10,2):furniture(plan,'envelope:spruce_pigeonhole',px,y+1,z+3,facing='south')
            plan.chest(x+3,y+1,z+7,'Letters and notes',tuple(k for k in plan.registry['items'] if any(ns in k for ns in ('yours','postit','post_it','envelope:')) and any(w in k for w in ('letter','post','paper','pen','package')))[:18])
        elif 'Makers' in name:
            for i,namespace in enumerate(['chipped','rechiseled','framedblocks','domum_ornamentum']):
                block=plan.find(namespace,'workbench') or plan.find(namespace,'table') or plan.find(namespace,'chisel')
                furniture(plan,block,x+2+i*4,y+1,z+3)
            items=tuple(k for k in plan.registry['items'] if k.startswith(('buildinggadgets2:','constructionwand:','effortlessbuilding:','structurize:','framedblocks:')) and any(w in k for w in ('gadget','wand','hammer','tool','chisel')))
            plan.chest(x+3,y+1,z+8,'Advanced building tools',items[:18])
        else:
            furniture(plan,'exposure:lightroom',x+2,y+1,z+3)
            furniture(plan,'xercamusic:piano',x+7,y+1,z+3,facing='south')
            items=tuple(k for k in plan.registry['items'] if k.startswith(('immersive_melodies:','xercamusic:','exposure:','music_disc_maker:')) and any(w in k for w in ('flute','violin','camera','film','sheet','disc','guitar')))
            plan.chest(x+3,y+1,z+8,'Music and memories',items[:18])


def wildlife(plan):
    plan.zone='Gardens and woodland habitats'
    choices=[('naturalist:hedgehog',14,-18,'Bramble'),('naturalist:duck',18,-12,'Puddle'),('crittersandcompanions:otter',20,-10,'Pebble'),('ribbits:ribbit',-18,-20,'Reed'),('minecraft:cat',-40,-24,'Marmalade')]
    for kind,x,z,name in choices:
        if kind in plan.registry['entities']:plan.entity(kind,x,plan.height(x,z),z,name)
    plan.landmark('Reed and Puddle Pond',18,plan.height(18,-12),-12,'Nature',['Small animal habitat','Cozy wildlife'])


def build(home,phase='core',center=(1120,-1120),rotation=2):
    layout=Layout(home);storage=Storage(layout);storage.reserve(64*1024**2)
    directory=layout.state/'settlement'
    status=read_json(directory/'status.json',{})
    if status.get('status')=='running':raise UserError('Let the current native operation finish before replacing its plan')
    registry=read_json(directory/'registry.json')
    survey=read_json(directory/'survey.json')
    backup=read_json(directory/'backup-receipt.json')
    if not backup.get('verified'):raise UserError('A complete verified pre-construction backup is required')
    if not Path(registry['world_path']).resolve().is_relative_to(layout.world):raise UserError('The native registry report belongs to a different world')
    plan=Plan(registry,survey,center,backup['sha256'],rotation)
    # Winding connecting paths precede buildings, which retain their own thresholds.
    for target in [(-44,-24),(-90,-92),(32,-45),(65,-55),(87,-42),(-125,-40),(0,35)]:path(plan,(0,0),target)
    plaza(plan);cottage(plan);gardens(plan);greenhouse(plan);castle(plan);barn(plan);giant_tree(plan);harbor(plan)
    if phase=='complete':
        engineering(plan);station(plan);village_life(plan);wildlife(plan)
    sx,sy,sz=plan.spawn;wx,wz=plan.world(sx,sz)
    plan.commands += [f'setworldspawn {wx} {sy} {wz} 180','gamerule spawnRadius 0']
    target=directory/'plan.json'
    if target.exists():
        previous=directory/('plan-'+digest(target)+'.json')
        if not previous.exists():target.rename(previous)
        else:raise UserError('The previous plan already has an immutable copy; choose a new phase revision')
    result=plan.save(target)
    result.update(phase=phase,spawn={'x':wx,'y':sy,'z':wz},status='generated from actual registries and terrain; not yet installed')
    write_json(directory/'plan-manifest.json',result)
    print(json.dumps(result),flush=True)
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--home',type=Path,default=Path(r'D:\A World for Two'))
    parser.add_argument('--phase',choices=('core','complete'),default='core')
    args=parser.parse_args();build(args.home,args.phase)
