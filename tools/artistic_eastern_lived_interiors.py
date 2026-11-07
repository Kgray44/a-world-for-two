"""Tortuga's finite trade-specific and household furnishing Source layers.

Current buildings receive AIR-only additions. Unbuilt Source receives complete
new refs. No old inventory, block-entity NBT, world action or client operation.
"""
from __future__ import annotations
import argparse,json,math,time
from collections import deque
from copy import deepcopy
from pathlib import Path
from control_room.common import UserError,digest,read_json
from tools import artistic_eastern_compound_sprint as e
from tools.artistic_city_planning_map import EAST,read as layout
from tools.artistic_eastern_entry_repair import actual_sources,checked
from tools.artistic_materials import require_material_rule
from tools.artistic_north_bank_east import native_payload
from tools.artistic_tortuga_variants import rotated_state
from tools.playtest import guard

MIB=1024**2
FUTURE=('staging/eastern-closed-roof-endwall-source-1793240081466811100/SOURCE-INDEX.json','2eeac3cfee177ef1388e6ae5dde17e4953218651dbbada2e3b567c5f87273a34')
ENTRY=('staging/eastern-current14-entry-repair-1793237214610305800/manifest.json','66faec7eafae57bf7a6e0e0dc8cf4c03f2e68d36e7cc34a983bc8a4d7c22ffa5')
BOOK=('staging/worn-book-photo-finish-1793237530213387100/manifest.json','4bb2d449165d66952f5d497f8f21ad0adac0d63e61d18768dcf812041789ad2c')
AIR={'minecraft:air','minecraft:cave_air','minecraft:void_air'}


def full_mount(value):
    """Conservative full construction surfaces; never an inferred roof slab."""
    if value is None:return False
    name=e.key(value);tail=name.split(':')[-1]
    if name.startswith('minecraft:'):
        return tail.endswith(('_planks','_log','_wood','_terracotta'))or tail in{'stone','stone_bricks','cobblestone','cobbled_deepslate','deepslate_bricks','andesite','polished_andesite','terracotta','bricks','bookshelf'}
    return name.startswith('chipped:')and tail.endswith(('_log','_planks','bookshelf'))


def item(x,y,z,name,role,**props):return((x,y,z),name,props,role)


def recipes():
    table=lambda x,z,role:item(x,0,z,'handcrafted:dark_oak_table',role,shape='single',color='none',waterlogged=False)
    chair=lambda x,z,face,role:item(x,0,z,'handcrafted:dark_oak_chair',role,facing=face,color='brown',waterlogged=False)
    book=lambda x,y,z,role:item(x,y,z,'handcrafted:stackable_book',role,facing='south',books=3,seed=17)
    shelf=[item(x,y,0,'chipped:historical_oak_bookshelf','floor-founded maritime reference and account volumes')for x in range(3)for y in(0,1,2)]
    shelf+=[item(0,0,1,'minecraft:brown_carpet','muted reference-rack browsing mat'),item(2,0,1,'minecraft:brown_carpet','muted reference-rack browsing mat')]
    dining=[table(1,1,'a real shared supper table'),chair(0,1,'east','one supper/reading seat'),chair(2,1,'west','opposite supper/reading seat'),
      item(1,1,1,'handcrafted:wood_plate','actual tableware on the supper table',facing='south',pieces=3,waterlogged=False)]
    reading=[table(1,1,'a real public browsing and reading table'),chair(0,1,'east','quiet reader seat'),chair(2,1,'west','opposite quiet reader seat'),book(1,1,1,'new maritime titles on the browsing table')]
    for target in(dining,reading):
        target.extend(item(x,0,z,'minecraft:brown_carpet','small rug edge around the real furniture group')for x,z in((0,0),(1,0),(2,0),(0,2),(1,2),(2,2)))
    writing=[item(0,0,0,'handcrafted:dark_oak_desk','actual trade-order or household correspondence desk',facing='south',color='brown',waterlogged=False),book(0,1,0,'ordinary correspondence and account books'),
      chair(0,1,'north','real writer seat'),item(2,0,0,'handcrafted:dark_oak_nightstand','small task-light stand',facing='south',color='none',waterlogged=False),
      item(2,1,0,'mcwlights:golden_low_candle_holder','small warm actual task light',lit=True),item(2,0,1,'minecraft:brown_carpet','writing-nook rug corner')]
    lounge=[item(0,0,0,'handcrafted:dark_oak_couch','a small actual upholstered household seat',facing='south',shape='single',color='green',waterlogged=False),
      item(2,0,0,'handcrafted:dark_oak_couch','separate opposite household reading seat',facing='south',shape='single',color='brown',waterlogged=False),
      table(1,2,'low household reading/supper table'),book(1,1,2,'shared household reading books'),item(0,0,2,'minecraft:brown_carpet','soft small lounge rug corner'),item(2,0,2,'minecraft:brown_carpet','soft small lounge rug corner')]
    dresser=[item(0,0,0,'handcrafted:dark_oak_cupboard','actual single household wardrobe',facing='south',type=1),
      item(2,0,0,'handcrafted:dark_oak_drawer','single household linen drawer',facing='south',shape='single',type=2),
      item(2,1,0,'fishofthieves:potted_white_plumeria','contained household window flower'),
      item(1,0,1,'minecraft:brown_carpet','little changing/linen mat')]
    kitchen=[item(0,0,0,'farmersdelight:stove','real ordinary unlit cooking stove; no invented food inventory',facing='south',lit=False),
      item(1,0,0,'minecraft:water_cauldron','real kitchen wash basin',level=3),item(2,0,0,'handcrafted:dark_oak_counter','real food-preparation counter',facing='south',counter='andesite',type=1),
      item(2,1,0,'farmersdelight:cutting_board','actual preparation board on the counter',facing='south',waterlogged=False),
      item(2,0,2,'handcrafted:dark_oak_cupboard','standing crockery cupboard',facing='north',type=1),item(2,1,2,'handcrafted:wood_bowl','real stacked kitchen vessels',facing='south',pieces=3,waterlogged=False)]
    pantry=[item(0,0,0,'minecraft:barrel','new native-default empty food-stock barrel',facing='up',open=False),
      item(0,1,0,'handcrafted:berry_jam_jar','ordinary jam-jar decorative models on full stock top',facing='south',jars=3,waterlogged=False),
      item(1,0,0,'minecraft:hay_block','actual dry provision bale',axis='y'),item(2,0,0,'handcrafted:dark_oak_cupboard','single pantry cupboard',facing='south',type=1),
      item(2,1,0,'handcrafted:terracotta_bowl','actual pantry bowls',facing='south',pieces=3,waterlogged=False)]
    navigation=[item(0,0,0,'minecraft:cartography_table','real chart-drafting and map station'),item(1,0,0,'chipped:oak_bookshelf','low navigation-reference counter'),
      item(1,1,0,'supplementaries:globe','real native rotatable navigator globe',facing='south',powered=False,rotation=0,waterlogged=False),
      item(2,0,0,'handcrafted:dark_oak_counter','navigator instrument/watch counter',facing='south',counter='dark_oak_planks',type=1),
      item(2,1,0,'supplementaries:hourglass','real ordinary watchglass',facing='up',light_level=0,waterlogged=False)]
    tools=[item(0,0,0,'minecraft:smithing_table','real tool-fitting bench'),item(2,0,0,'minecraft:anvil','real ordinary tool-repair anvil',facing='south'),
      item(0,0,2,'minecraft:grindstone','real freestanding tool-sharpening wheel',face='floor',facing='south'),
      item(2,0,2,'handcrafted:dark_oak_counter','repair-order counter',facing='north',counter='andesite',type=1),book(2,1,2,'tool orders and measurements')]
    cloth=[item(0,0,0,'minecraft:loom','real sail/cloth-pattern loom',facing='south'),item(2,0,0,'handcrafted:dark_oak_counter','cloth measuring and cutting counter',facing='south',counter='dark_oak_planks',type=1),
      book(2,1,0,'sail patterns and cloth orders'),item(0,0,2,'minecraft:brown_wool','actual muted folded cloth bale'),
      item(0,1,2,'handcrafted:wood_cup','small actual sewing-room vessels on full bale',facing='south',pieces=2,waterlogged=False)]
    cooper=[item(0,0,0,'minecraft:stonecutter','real craft cutting bench',facing='south'),item(2,0,0,'minecraft:crafting_table','real cooper/joiner workbench'),
      item(0,0,2,'minecraft:stripped_spruce_log','real short stock timber',axis='x'),item(1,0,2,'minecraft:stripped_spruce_log','real short stock timber',axis='x'),
      item(2,0,2,'handcrafted:dark_oak_counter','cooper measure/order counter',facing='north',counter='dark_oak_planks',type=1),book(2,1,2,'measurements and working account book')]
    storage=[item(x,0,0,'minecraft:barrel','new native-default empty working stock; no copied contents',facing='up',open=False)for x in(0,2)]
    storage+=[item(1,0,0,'minecraft:hay_block','dry grain/provision cargo bale',axis='y'),book(0,1,0,'shipping tally on stock top'),
      item(2,1,0,'mcwlights:golden_low_candle_holder','small cargo-account task light',lit=True)]
    fish=[item(0,0,0,'minecraft:smoker','real ordinary unlit fish-smoking station',facing='south',lit=False),item(1,0,0,'minecraft:water_cauldron','real washing basin',level=3),
      item(2,0,0,'handcrafted:dark_oak_counter','fish-preparation counter',facing='south',counter='andesite',type=1),item(2,1,0,'farmersdelight:cutting_board','actual preparation board',facing='south',waterlogged=False)]
    music=[item(0,0,0,'minecraft:jukebox','real empty ordinary jukebox; no record fabricated',has_record=False),item(2,0,0,'minecraft:note_block','real playable bass note instrument on qualified vanilla wood',instrument='bass',note=8,powered=False),
      item(1,0,2,'handcrafted:dark_oak_bench','single musician/listener seat',facing='north',shape='single',color='brown',waterlogged=False),
      item(0,0,2,'chipped:historical_oak_bookshelf','low music-score shelf'),book(0,1,2,'music scores and song books')]
    compact_books=[item(0,0,0,'chipped:oak_bookshelf','compact working reference counter'),book(0,1,0,'individual account/pattern volumes on the actual counter')]
    compact_lamp=[item(0,0,0,'handcrafted:dark_oak_nightstand','compact household/task-light stand',facing='south',color='none',waterlogged=False),item(0,1,0,'mcwlights:golden_low_candle_holder','small practical table light',lit=True)]
    compact_food=[item(0,0,0,'handcrafted:dark_oak_counter','compact actual preparation side-counter',facing='south',counter='andesite',type=1),item(0,1,0,'handcrafted:wood_bowl','real working-room vessel models',facing='south',pieces=3,waterlogged=False)]
    return {'reference':shelf,'reading':reading,'dining':dining,'writing':writing,'lounge':lounge,'dresser':dresser,'kitchen':kitchen,'pantry':pantry,'navigation':navigation,'tools':tools,'cloth':cloth,'cooper':cooper,'storage':storage,'fish':fish,'music':music,'compact_reference':compact_books,'compact_task_light':compact_lamp,'compact_preparation':compact_food}


PROGRAMS={
 'archive':('reference','writing','reading','reference','navigation','reading','dresser'),
 'charts':('navigation','reference','writing','reading','storage','reference'),
 'pilot':('navigation','storage','writing','reading','reference','dining'),
 'hardware':('tools','storage','writing','tools','cooper','reading'),
 'galley':('kitchen','pantry','dining','kitchen','pantry','dining'),
 'inn':('writing','dining','pantry','lounge','kitchen','reading','dining'),
 'fish':('fish','storage','pantry','writing','dining','cooper'),
 'cloth':('cloth','storage','writing','cloth','reading','dresser'),
 'cooper':('cooper','storage','tools','writing','cooper','reading'),
 'warehouse':('storage','storage','writing','cooper','navigation','reading'),
 'music':('music','lounge','reference','dining','writing','music')}
UPPER=(('lounge','writing','dresser','dining','reading','pantry'),('dresser','reading','dining','lounge','writing','reference'),('writing','lounge','dining','dresser','reading','music'))


def rotate(q,turn):
    x,y,z=q
    for _ in range(turn%4):x,z=-z,x
    return x,y,z


def protected_body(source):
    result=set();origin=source['origin']
    for row in source.get('routes',[]):
        for q in row.get('feet_local',[]):
            x,y,z=(q[k]+origin[k]for k in range(3));result.update(((x,y,z),(x,y+1,z)))
    for row in source.get('geometry_proof',{}).get('vertical_routes',[]):
        for x,y,z in row.get('blocks',[]):
            for h in(1,2):result.add((x+origin[0],y+h+origin[1],z+origin[2]))
        for x,y,z in row.get('shaft',[]):result.add((x+origin[0],y+origin[1],z+origin[2]))
    return result


def finish(registry,source,base,program,variant=0):
    """A finite set of individually fitted trade/household clusters per floor."""
    delta={};scenes=[];protected=protected_body(source);all_roles=[];all_mounts=[];book=recipes()
    for mi,m in enumerate(source['masses']):
        x0,z0,x1,z1=m['bounds_xz'];nx=x1-x0-1;nz=z1-z0-1;short=min(nx,nz);long=max(nx,nz)
        if nx<1 or nz<1:raise UserError('A room has no actual interior')
        global_turn=0 if nx<=nz else 3
        offsets=m.get('occupied_floor_offsets',[n*4 for n in range(m['storeys'])])
        for fi,offset in enumerate(offsets):
            y=m['floor_y']+offset+1
            ceiling_y=m['floor_y']+(offsets[fi+1]if fi+1<len(offsets)else offsets[-1]+4)
            ceiling_h=ceiling_y-y-1
            def world(q):
                u,h,v=q
                return(x0+1+u,y+h,z0+1+v)if nx<=nz else(x0+1+v,y+h,z1-1-u)
            def clear(u,v,post):
                q=world((u,0,v));return all(post.get((q[0],q[1]+h,q[2]))in AIR for h in(0,1))and post.get((q[0],q[1]-1,q[2]))not in AIR|{None}
            post=base|delta;free={(u,v)for u in range(short)for v in range(long)if clear(u,v,post)}
            # Select a genuinely clear continuous three/five-wide rectangle,
            # never declare a blocked band to be a corridor. Existing stairs
            # and all original paths remain protected independently.
            rectangles=[]
            for width in([5,3]if short>=11 else[3]):
                for u in range(max(0,short-width+1)):
                    start=None
                    for v in range(long+1):
                        ok=v<long and all((a,v)in free for a in range(u,u+width))
                        if ok and start is None:start=v
                        if not ok and start is not None:
                            if v-start>=3:rectangles.append((width*(v-start),width,u,start,v-1))
                            start=None
            corridor=set()
            if rectangles:
                _,cw,cu,cv,ce=max(rectangles,key=lambda r:(r[0],-abs(r[2]+r[1]/2-short/2),r[1]))
                corridor={world((u,h,v))for u in range(cu,cu+cw)for v in range(cv,ce+1)for h in(0,1)}
                protected|=corridor
            else:cw=0
            desired=8 if short*long>=120 else 6 if short*long>=75 else 4 if short*long>=40 else 2
            sequence=list(PROGRAMS[program]if fi==0 else UPPER[(variant+mi+fi)%len(UPPER)])
            sequence+=sequence[:max(0,desired-len(sequence))]
            if short<=5:
                compact='compact_reference'if program in('archive','charts','pilot','music','cloth')and not fi else'compact_preparation'if program in('galley','inn','fish')and not fi else'compact_task_light'
                sequence=sequence[:desired]+[compact,'compact_reference',compact,'compact_task_light']
            clusters=[]
            source_roots=[]
            for row in source.get('routes',[]):
                for v in row.get('feet_local',[]):
                    q=tuple(v[k]+source['origin'][k]for k in range(3))
                    if q[1]==y and x0<q[0]<x1 and z0<q[2]<z1 and all(post.get((q[0],y+h,q[2]))in AIR for h in(0,1)):source_roots.append(q)
            def reachable(field):
                free_world={world((u,0,v))for u in range(short)for v in range(long)if clear(u,v,field)}
                roots=[q for q in source_roots if q in free_world]
                if not roots:return set()
                # Original complete circulation may connect two parts through
                # an attached mass or the real vertical route outside this
                # individual rectangle. All those original AIR paths remain
                # protected; use their actual in-room arrivals, not one
                # arbitrarily selected end of a staircase.
                todo=deque(roots);found=set(todo)
                while todo:
                    q=todo.popleft()
                    for dx,dz in((1,0),(-1,0),(0,1),(0,-1)):
                        r=q[0]+dx,y,q[2]+dz
                        if r in free_world and r not in found:found.add(r);todo.append(r)
                return found
            initial_reach=reachable(post)
            for slot,kind in enumerate(sequence[:desired+4]if short<=5 else sequence[:desired]):
                pieces=book[kind];corn=(slot+variant+mi)%4;options=[]
                for turn in range(4):
                    points=[rotate(q,turn)for q,_,_,_ in pieces];umin=min(q[0]for q in points);umax=max(q[0]for q in points);vmin=min(q[2]for q in points);vmax=max(q[2]for q in points)
                    for a in range(-umin,short-umax):
                        for b in range(-vmin,long-vmax):
                            center=a+(umin+umax)/2,b+(vmin+vmax)/2
                            target=((0,0),(short-1,long-1),(short-1,0),(0,long-1))[corn]
                            options.append((abs(center[0]-target[0])+abs(center[1]-target[1]),turn,a,b))
                chosen=None
                for _,turn,a,b in sorted(options):
                    field={};roles=[];mounts=[];bad=False
                    for q,name,props,role in pieces:
                        u,h,v=rotate(q,turn);p=world((a+u,h,b+v));value=rotated_state(registry,e.state(registry,name,**props),(turn+global_turn)%4)
                        if p in protected or p in delta or base.get(p)not in AIR:bad=True;break
                        if name=='minecraft:note_block':
                            floor=e.key((base|delta).get((p[0],p[1]-1,p[2]),'minecraft:air'))
                            if not floor.startswith('minecraft:')or not floor.endswith(('_planks','_wood','_log'))or(base|delta).get((p[0],p[1]+1,p[2]))not in AIR:
                                bad=True;break
                        opaque=name.endswith(('bookshelf','_log'))or name in('minecraft:barrel','minecraft:hay_block','minecraft:brown_wool')
                        if opaque and p[1]<=y+1:
                            for dx,dz in((1,0),(-1,0),(0,1),(0,-1)):
                                wx,wz=p[0]+dx,p[2]+dz
                                if wx not in(x0,x1)and wz not in(z0,z1):continue
                                if any(e.key(base.get((wx,y+h,wz),'minecraft:air')).startswith('mcwwindows:')for h in(0,1)):
                                    bad=True;break
                            if bad:break
                        if name.endswith('bookshelf')or name.startswith('handcrafted:')and any(t in name for t in('_table','_shelf','_bench','_cupboard','_drawer','_couch')):
                            # Native connected furniture must not accidentally
                            # turn a SINGLE model into an unqualified joint.
                            if any(e.key((base|delta).get((p[0]+dx,p[1],p[2]+dz),'minecraft:air'))==name for dx,dz in((1,0),(-1,0),(0,1),(0,-1))):bad=True;break
                        field[p]=value;roles.append({'position':list(p),'block':value,'purpose':role});mounts.append((p,(p[0],p[1]-1,p[2])))
                    if bad:continue
                    final=base|delta|field
                    if any(final.get(back)in AIR|{None}for _,back in mounts):continue
                    footprint={world((a+rotate(q,turn)[0],0,b+rotate(q,turn)[2]))for q,_,_,_ in pieces if q[1]==0}
                    visits=[]
                    for p in footprint:
                        for dx,dz in((1,0),(-1,0),(0,1),(0,-1)):
                            q=p[0]+dx,y,p[2]+dz
                            if x0<q[0]<x1 and z0<q[2]<z1 and all(final.get((q[0],y+h,q[2]))in AIR for h in(0,1))and final.get((q[0],y-1,q[2]))not in AIR|{None}:visits.append(q)
                    accessible=reachable(final)
                    visits=[q for q in visits if q in accessible]
                    if not visits or any(q not in accessible for q in initial_reach if q in protected):continue
                    # A literal supported viewing/working spot is protected
                    # from all later groups. Native use remains unproved.
                    visit=min(visits,key=lambda q:min((abs(q[0]-r[0])+abs(q[2]-r[2])for r in protected if r[1]==y),default=999))
                    chosen=field,roles,mounts,visit;break
                if chosen:
                    field,roles,mounts,visit=chosen;delta.update(field);all_roles+=roles;all_mounts+=mounts
                    protected.update(((visit[0],y,visit[2]),(visit[0],y+1,visit[2])))
                    clusters.append({'purpose':kind,'new_cells':len(field),'visitor_feet':list(visit),'objects':roles})
            # Small ordinary lights, attached to real existing ceiling blocks;
            # no giant chandelier or unsupported hanging prop.
            lights=[];ceiling=[];wall_details=[];post=base|delta
            candidates=sorted(((u,v)for u in range(short)for v in range(long)),key=lambda q:(min(abs(q[0]-short*.25),abs(q[0]-short*.75))+min(abs(q[1]-long*.25),abs(q[1]-long*.75)),q))
            for u,v in candidates:
                q=world((u,ceiling_h,v));back=world((u,ceiling_h+1,v))
                if q in protected or q in delta or base.get(q)not in AIR or not full_mount(post.get(back)):continue
                if any(abs(q[0]-r[0])+abs(q[2]-r[2])<4 for r in lights):continue
                delta[q]=e.state(registry,'minecraft:lantern',hanging=True,waterlogged=False);all_mounts.append((q,back));lights.append(q)
                all_roles.append({'position':list(q),'block':delta[q],'purpose':'small warm supported work/household ceiling light'})
                if len(lights)>=min(6,max(2,math.ceil(short*long/30))):break
            # Actual backed display shelves articulate opaque wall panels.
            # The literal supported working point remains reachable and no
            # shelf is attached to a window or to a door.
            for u,v in candidates:
                if u not in(0,short-1)and v not in(0,long-1):continue
                q=world((u,1,v));top=world((u,2,v));below=world((u,0,v))
                if any(p in protected or p in delta or base.get(p)not in AIR for p in(q,top)):continue
                if below not in reachable(base|delta):continue
                if u==0:back=world((-1,1,v));face='east'
                elif u==short-1:back=world((short,1,v));face='west'
                elif v==0:back=world((u,1,-1));face='south'
                else:back=world((u,1,long));face='north'
                value=(base|delta).get(back)
                if not full_mount(value):continue
                if any(e.key((base|delta).get((q[0]+dx,q[1],q[2]+dz),'minecraft:air'))=='handcrafted:dark_oak_shelf'for dx,dz in((1,0),(-1,0),(0,1),(0,-1))):continue
                if any(abs(q[0]-p[0])+abs(q[2]-p[2])<3 for p in wall_details):continue
                delta[q]=rotated_state(registry,e.state(registry,'handcrafted:dark_oak_shelf',facing=face,shape='single',type=3),global_turn)
                delta[top]=rotated_state(registry,e.state(registry,'handcrafted:stackable_book',facing=face,books=3,seed=1+(variant+mi*7+fi*3)%60),global_turn)
                all_mounts.extend(((q,back),(top,q)));wall_details.append(q)
                all_roles.extend(({'position':list(q),'block':delta[q],'purpose':'real opaque-wall-backed trade/household display shelf'},
                  {'position':list(top),'block':delta[top],'purpose':'individual trade records and personal book models on the fitted shelf'}))
                if len(wall_details)>=min(8,max(2,short*long//18)):break
            # Overhead end cupboards physically meet the existing ceiling;
            # long compact galleries keep their three-wide floor unobstructed.
            overhead=[]
            for u,v in candidates:
                if u not in(0,short-1)or v%5 not in(0,1,2):continue
                q=world((u,ceiling_h,v));back=world((u,ceiling_h+1,v))
                if q in protected or q in delta or base.get(q)not in AIR or not full_mount(post.get(back)):continue
                if any(abs(q[0]-p[0])+abs(q[2]-p[2])<=1 for p in lights):continue
                name='chipped:historical_oak_bookshelf'if program in('archive','charts','pilot','music')or fi else'chipped:oak_empty_bookshelf'
                would=base|delta|{q:name};too_long=False
                for dx,dy,dz in((1,0,0),(0,1,0),(0,0,1)):
                    run=1
                    for sign in(-1,1):
                        p=q
                        while e.key(would.get((p[0]+sign*dx,p[1]+sign*dy,p[2]+sign*dz),'minecraft:air'))==name:
                            p=p[0]+sign*dx,p[1]+sign*dy,p[2]+sign*dz;run+=1
                    if run>3:too_long=True
                if too_long:continue # short real cupboard modules, not a continuous new ceiling sheet
                delta[q]=e.state(registry,name);all_mounts.append((q,back));overhead.append(q)
                all_roles.append({'position':list(q),'block':delta[q],'purpose':'actual ceiling-attached overhead reference/household cubby with clear walking headroom below'})
                if len(overhead)>=min(12,max(4,short*long//12)):break
            # True shallow coffer relief directly touches the ceiling. Keep
            # individual panels short instead of creating another plain sheet.
            for u,v in candidates:
                q=world((u,ceiling_h,v));back=world((u,ceiling_h+1,v))
                if q in protected or q in delta or base.get(q)not in AIR or not full_mount(post.get(back)):continue
                if any(abs(q[0]-r[0])+abs(q[2]-r[2])<=1 for r in lights):continue
                if len(ceiling)>=min(8,max(2,short*long//20)):break
                delta[q]=e.state(registry,'minecraft:dark_oak_trapdoor',facing='north',half='top',open=False,powered=False,waterlogged=False)
                ceiling.append(q);all_mounts.append((q,back));all_roles.append({'position':list(q),'block':delta[q],'purpose':'actual one-eighth-depth fitted coffer panel touching the real ceiling'})
            scenes.append({'mass':mi,'floor':fi,'feet_y':y,'actual_ceiling_y':ceiling_y,'program':program if fi==0 else'household / study / guest use','interior_grid_area':short*long,
              'literal_wide_corridor_width':cw,'literal_wide_corridor_two_high_cells':[list(q)for q in sorted(corridor)],'clusters':clusters,'small_supported_lights':[list(q)for q in lights],'shallow_ceiling_panels':[list(q)for q in ceiling],
              'backed_wall_display_shelves':[list(q)for q in wall_details],'ceiling_attached_cubbies':[list(q)for q in overhead],
              'new_cells':sum(c['new_cells']for c in clusters)+len(lights)+len(ceiling)+2*len(wall_details)+len(overhead),'not_a_count_of_closed_rooms':True})
    final=base|delta
    if any(final.get(q)!=base.get(q)for q in protected if q in base):raise UserError('A finishing group overwrote literal existing or new reserved walking body')
    for q,back in all_mounts:
        if final.get(back)in AIR|{None}:raise UserError('A finishing prop or light lost its actual/new support')
    return delta,scenes,all_roles,all_mounts


def prepare(home,index=None,index_sha=None,mode='future'):
    home=Path(home).resolve()
    if not home.is_relative_to(Path('D:/A World for Two/staging/world-tests').resolve()):raise UserError('Private Tortuga Source output only')
    reserve=guard(8*MIB,64*MIB);reg=read_json(home/'dashboard/settlement/registry.json');master=layout(home,EAST);programs={r['id']:r['program']for r in master['buildings']if r['masses']}
    if mode=='future':
        ip=Path(index)if index else home/FUTURE[0];ih=index_sha or FUTURE[1];idx=checked(ip,ih);work=[]
        for r in idx['compounds']:
            if r.get('actual_preexisting')is True:continue
            ref=r['files']['SOURCE-ONLY'];s=checked(home/ref['path'],ref['sha256']);work.append((r,s,{tuple(v[:3]):v[3]for v in s['complete_expected_state_context_ONLY']},ref))
        if len(work)!=25:raise UserError('Exactly the remaining25 Source compounds required')
    elif mode=='current':
        actual=actual_sources(home);current={}
        for _,_,f,_ in actual:current.update(f)
        from tools.artistic_bridge_refinement import flatten
        en=checked(home/ENTRY[0],ENTRY[1]);er=en['files']['entry-and-low-fitting-DELTA'];current.update(flatten(checked(home/er['path'],er['sha256'])))
        bm=checked(home/BOOK[0],BOOK[1]);br=bm['files']['bookshop-AIR-only-DELTA'];current.update(flatten(checked(home/br['path'],br['sha256'])))
        ip=Path(index)if index else home/FUTURE[0];ih=index_sha or FUTURE[1];roof_index=checked(ip,ih)
        roof_rows={r['id']:r for r in roof_index['compounds']if r.get('actual_preexisting')is True}
        if set(roof_rows)!={r[0]for r in actual}:raise UserError('The exact current14 roof correction Source is required')
        work=[]
        for ident,old,field,ref in actual:
            rr=roof_rows[ident];sr=rr['files']['SOURCE-ONLY'];s=checked(home/sr['path'],sr['sha256'])
            expected={tuple(v[:3]):v[3]for v in s['complete_expected_state_context_ONLY']}
            dr=rr['files']['delta'];roof_delta=flatten(checked(home/dr['path'],dr['sha256']))
            base={**expected,**{q:current[q]for q in expected if q in current},**roof_delta}
            if ident=='worn-book':base.update(flatten(checked(home/br['path'],br['sha256'])))
            work.append(({'id':ident,'name':s['name'],'roof_source':sr},s,base,ref))
    else:raise UserError('Explicit future/current Source mode only')
    out=home/'staging'/('eastern-lived-interiors-'+mode+'-'+str(time.time_ns()));out.mkdir();records=[];held=[];written=0
    for n,(row,s,base,ref)in enumerate(work):
        ident=row['id']
        try:
            delta,scenes,roles,mounts=finish(reg,s,base,programs[ident],n)
            if not delta:raise UserError('No new actual AIR finishing geometry fits')
            owned={tuple(v[:3])for v in s['blocks_PROSPECTIVE_DELTA']};material=require_material_rule({q:v for q,v in(base|delta).items()if q in owned or q in delta},s['name']+' complete authored construction and new interior finish')
            if mode=='future':
                result=deepcopy(s);result['complete_expected_state_context_ONLY']=[[*q,v]for q,v in sorted((base|delta).items())]
                before_delta={tuple(v[:3]):v[3]for v in s['blocks_PROSPECTIVE_DELTA']};result['blocks_PROSPECTIVE_DELTA']=[[*q,v]for q,v in sorted((before_delta|delta).items())]
                result.update(fresh_direct_construction=True,interior_finish_source_sha256=digest(Path(__file__)),interior_finish_base_source=ref,
                  interior_finish_AIR_ONLY=[[*q,v]for q,v in sorted(delta.items())],purpose_specific_lived_in_floor_scenes=scenes,interior_finish_material_rule=material,interior_finish_support_edges=[{'object':list(q),'support':list(back)}for q,back in mounts],
                  actual_finish_native_view_and_use_pending=True,source_only=True,native_actions=0,world_writes=0)
            else:
                result={'format':'awft-current-east-living-finish-SOURCE:1','id':ident,'name':s['name'],'base_actual_native_full_proof':ref,
                  'AIR_only_delta':[[*q,v]for q,v in sorted(delta.items())],'AIR_only_before':[[*q,base[q]]for q in sorted(delta)],
                  'purpose_specific_lived_in_floor_scenes':scenes,'material_rule':material,'new_tags_ONLY':[],'source_sha256':digest(Path(__file__)),
                  'requires_current14_entry_repair':ENTRY,'requires_Worn47_first':BOOK,'construction_forbidden':True,'actual_current_before_native_verification_pending':True,'native_actions':0,'world_writes':0}
                result['requires_completed_closed_roof_correction']={'source_index':str(ip),'sha256':ih,'building_source':row['roof_source']}
                # Scope the normal-room interiors, not readonly exterior AIR
                # around neighboring compounds and not Grand's changing roof.
                scope=set(delta)
                for m in s['masses']:
                    a,b,c,d=m['bounds_xz'];floor=m['floor_y'];top=floor+m.get('occupied_floor_offsets',[v*4 for v in range(m['storeys'])])[-1]+4
                    scope.update(q for q in base if a<q[0]<c and b<q[2]<d and floor<=q[1]<=top)
                support_field={back:base[back]for _,back in mounts if back not in delta}
                full={q:base[q]for q in scope if q in base}|delta
                result['files']={}
                receipt=read_json(home/'dashboard/settlement/backup-receipt.json')
                for label,field in [('AIR-before',{q:base[q]for q in delta}),('retained-supports',support_field),('AIR-only-DELTA',delta),('normal-settle',delta),('complete-interior-after',full)]:
                    doc=native_payload(reg,field,receipt['sha256'],'SOURCE ONLY Tortuga lived-in '+ident+' — '+label)
                    doc.update(construction_forbidden=True,verification_only=True,block_entities=[],commands=[])
                    np=out/(ident+'-'+label+'.json');np.open('x',encoding='utf8').write(json.dumps(doc,separators=(',',':'))+'\n')
                    result['files'][label]={'path':np.relative_to(home).as_posix(),'sha256':digest(np),'bytes':np.stat().st_size}
                result['requires_original14_baseline_failure_resolved']=True
            raw=(json.dumps(result,separators=(',',':'))+'\n').encode();written+=len(raw)
            if written>64*MIB:raise UserError('Finite64MiB Source output cap')
            p=out/(ident+'-SOURCE-ONLY.json');p.open('xb').write(raw);source_ref={'path':p.relative_to(home).as_posix(),'sha256':digest(p),'bytes':len(raw)}
            records.append({'id':ident,'name':s['name'],'files':{'SOURCE-ONLY':source_ref,**result.get('files',{})},'fresh_direct_construction':mode=='future','width_review':s.get('width_review',{}),
              'counts':{'new_interior_cells':len(delta),'furnished_floor_scenes':len(scenes),'purpose_clusters':sum(len(v['clusters'])for v in scenes),'supported_small_lights':sum(len(v['small_supported_lights'])for v in scenes)},
              'large_floor_new_cells':[v['new_cells']for v in scenes if v['interior_grid_area']>=75]})
        except(UserError,ValueError)as ex:held.append({'id':ident,'reason':str(ex),'architecture_emitted':False})
    result={'format':'awft-eastern-fresh-width-source-index:1'if mode=='future'else'awft-current-eastern-lived-finish-source-index:1','mode':mode,'fresh_direct_construction':mode=='future',
      'compounds':records,'held':held,'source_sha256':digest(Path(__file__)),'native_actions':0,'world_writes':0,'construction_forbidden':True,'reserve_guard':reserve,
      'not_native_or_art_acceptance':True,'existing_NBT_or_inventories_replayed':0,'current14_entries_and_Worn47_required_before_current_finish':mode=='current'}
    p=out/'SOURCE-INDEX.json';p.open('x',encoding='utf8').write(json.dumps(result,indent=2)+'\n')
    return {'folder':str(out),'index_sha256':digest(p),'ready':len(records),'held':held,'new_cells':sum(v['counts']['new_interior_cells']for v in records),'records':records}


if __name__=='__main__':
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('--home',type=Path,required=True);a.add_argument('--index',type=Path);a.add_argument('--index-sha');a.add_argument('--mode',choices=('future','current'),default='future');v=a.parse_args();r=prepare(v.home,v.index,v.index_sha,v.mode);r.pop('records',None);print(json.dumps(r,indent=2))
