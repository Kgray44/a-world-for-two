"""The established flat Tortuga diagram style, from saved surface and placed geometry."""
from pathlib import Path
import hashlib,json,math
from PIL import Image,ImageDraw,ImageFont
from collections import defaultdict

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[2]
HOME=Path(r'D:\A World for Two\staging\world-tests\20261027T053650Z-artistic')
INV=HOME/'staging/Tortuga-completed-building-inventory-SOURCE-FINAL-1793293819653515300/building-inventory-SOURCE.json'
PAPER='#efe8d6';INK='#34392f';WATER='#9bb7b1';GROUND='#d8d0ae';CONTEXT='#8b8d7f';BUILT='#467f59';EDGE='#174d32';GREEN='#33704c';PAVERS='#a18462';SHIP='#9b6e4e'
sources=[]
def read(p):
    raw=p.read_bytes();sources.append({'path':str(p.relative_to(HOME)) if p.is_relative_to(HOME)else p.name,'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)})
    return json.loads(raw)
def font(n,b=False):return ImageFont.truetype('C:/Windows/Fonts/'+('georgiab.ttf'if b else'georgia.ttf'),n)
def flatten(doc):
    literal=doc.get('complete_expected_state_context_ONLY',doc.get('blocks_PROSPECTIVE_DELTA'))
    if isinstance(literal,list):return {(r[0],r[1],r[2]):r[3]for r in literal if len(r)==4 and isinstance(r[3],str)}
    return {(r[0],r[1],r[2]):doc['palette'][r[3]]for r in doc.get('blocks',[])}
cache={}
def roof(p,min_y=67):
    if(p,min_y)not in cache:cache[p,min_y]={(x,z)for(x,y,z),s in flatten(read(p)).items()if y>=min_y and s.split('[',1)[0]not in('minecraft:air','minecraft:cave_air','minecraft:void_air','minecraft:water')}
    return cache[p,min_y]
def rows(cells):
    by=defaultdict(list)
    for x,z in cells:by[z].append(x)
    for z,xs in by.items():
        xs=sorted(set(xs));a=b=xs[0]
        for x in xs[1:]:
            if x!=b+1:yield a,z,b-a+1;a=x
            b=x
        yield a,z,b-a+1
inv=read(INV);newcity=set();retained=set()
for r in inv['properties']:
    source=r['geometry_source'];p=HOME/source.get('path',source.get('complete_original_plan',{}).get('path',''))
    target=newcity if r['district']in('east39','west36_new')else retained
    try:
        cells=roof(p)
        if not cells:raise ValueError('Inventory-only source; use actual property footprint')
        target.update(cells)
    except (FileNotFoundError,KeyError,TypeError,ValueError):
        for x,z,n in r['ground_footprint']['rows']:target.update((a,z)for a in range(x,x+n))

ground=set();green=set()
completed=read(HOME/'staging/WEST-GROUND-LUSH63-EXECUTION-1793239356433478800/ACTUAL-COMPLETED.json')
for r in completed['results']:
    if r['operation']!='place':continue
    p=HOME/r['plan'];d=read(p)
    if hashlib.sha256(p.read_bytes()).hexdigest()!=r['plan_sha256']:raise ValueError('Exact actual ground/lush plan differs')
    target=green if r['step']in(3,6)else ground
    target.update((x,z)for(x,y,z),s in flatten(d).items()if s.split('[',1)[0]not in('minecraft:air','minecraft:water'))

ships=[
 ('Rosewater Lark',(1140,-1450),'staging/artistic-ship-2c8c6d503fe92246/prototype.json'),
 ('Resolute Wren',(1000,-1366),'staging/fleet-wren55-execution-1793225953291708100/wren-ADMITTED-PLACE-ONCE.json'),
 ('Golden Petrel',(1110,-1360),'staging/fleet63-three-ships-execution-1793234569364722600/golden-petrel-ship-ADMITTED-PLACE-ONCE.json'),
 ('Mercy of the Tide',(1230,-1392),'staging/fleet63-three-ships-execution-1793234569364722600/mercy-of-the-tide-ship-ADMITTED-PLACE-ONCE.json'),
 ('Tern',(1167,-1335),'staging/fleet-wren55-execution-1793225953291708100/tern-pilot-cutter-ADMITTED-PLACE-ONCE.json'),
 ('Salt Marigold',(1229,-1323),'staging/fleet-wren55-execution-1793225953291708100/salt-marigold-ketch-ADMITTED-PLACE-ONCE.json'),
 ('Reed Fin',(1336,-1044),'staging/fleet63-three-ships-execution-1793234569364722600/reed-ADMITTED-PLACE-ONCE.json')]
shipcells=set()
for name,xy,p in ships:shipcells.update(roof(HOME/p,62))
context=set()
for p in ['staging/prototype-castle-palace-e6ffcde57520b8cb/prototype.json','staging/prototype-rosebridge-9c9b37cea97a69d9/prototype.json','staging/bridge-tower-native-settle-20261027T1823Z/full-verification.json','staging/artistic-engineering-r2-1793106029261770100/mill-quarter.json','staging/artistic-fountain-centerpiece-r5-20261027T2109Z/plaza.json']:
    context.update(roof(HOME/p,63))

base=Image.open(OUT/'surface-data.png').convert('RGB');assert base.size==(556,861)
surface=read(OUT/'surface-data.json')
zipfile=OUT/'zipline-actual.json'
zipdata=read(zipfile)if zipfile.exists()else None
def make(name,bounds,scale,title,subtitle,whole):
    x0,z0,x1,z1=bounds;w,h=x1-x0+1,z1-z0+1;L,T=95,190;W,H=w*scale+190,h*scale+365
    im=Image.new('RGB',(W,H),PAPER);d=ImageDraw.Draw(im)
    crop=base.crop((x0-900,z0+1540,x1-900+1,z1+1540+1));im.paste(crop.resize((w*scale,h*scale),Image.Resampling.NEAREST),(L,T))
    def pt(q):return L+(q[0]-x0)*scale,T+(q[1]-z0)*scale
    def area(cells,color,edge=None):
        clipped={(x,z)for x,z in cells if x0<=x<=x1 and z0<=z<=z1}
        for x,z,n in rows(clipped):
            a,b=pt((x,z)),pt((x+n,z+1));d.rectangle((a[0],a[1],b[0]-1,b[1]-1),fill=color)
        if edge:
            for x,z in clipped:
                for dx,dz,a,b in [(0,-1,(x,z),(x+1,z)),(1,0,(x+1,z),(x+1,z+1)),(0,1,(x+1,z+1),(x,z+1)),(-1,0,(x,z+1),(x,z))]:
                    if(x+dx,z+dz)not in clipped:d.line((pt(a),pt(b)),fill=edge,width=1)
    area(ground,PAVERS);area(green,GREEN);area(context,CONTEXT);area(retained,CONTEXT);area(newcity,BUILT,EDGE);area(shipcells,SHIP,'#554936')
    d.text((95,29),title,font=font(45,True),fill=INK);d.text((98,91),subtitle,font=font(28),fill=INK)
    d.text((98,134),'118 Tortuga properties · 39 East / 36 new West · ground, greenery and retained landmarks',font=font(23),fill=INK)
    d.text((W-130,40),'N',font=font(33,True),fill=INK);d.line((W-110,135,W-110,95),fill=INK,width=4);d.polygon(((W-110,86),(W-119,102),(W-101,102)),fill=INK)
    def label(text,x,z,dx=0,dy=0,n=20):
        if not(x0<=x<=x1 and z0<=z<=z1):return
        p=pt((x,z));q=(p[0]+dx,p[1]+dy)
        if dx or dy:d.line((p,q),fill=INK,width=1)
        d.text(q,text,font=font(n,True),fill=INK,stroke_width=2,stroke_fill=PAPER,anchor='mm')
    labels=[('West Tortuga',1047,-1250,0,35),('Original district',1250,-1244,0,-5),('East Tortuga',1330,-1184,0,0),("Captain's Rest",1046,-1285,-5,-27),('Drowned Rose',1300,-1279,0,16),("Fisherman's shop",1324,-1332,15,-15),('Lantern Harbor Inn',1298,-1252,18,-17),('Pelican Forge',1363,-1126,0,17)]
    for a,x,z,dx,dy in labels:label(a,x,z,dx,dy,20 if whole else 23)
    if zipdata:
        points=zipdata.get('nodes_xz',zipdata.get('points_xz',[]))
        if points:
            overlay=Image.new('RGBA',(w*scale,h*scale),(0,0,0,0));od=ImageDraw.Draw(overlay)
            points_local=[((q[0]-x0)*scale,(q[1]-z0)*scale)for q in points]
            od.line(points_local,fill='#78523b',width=4)
            for a in points_local:od.ellipse((a[0]-4,a[1]-4,a[0]+4,a[1]+4),fill='#78523b',outline=PAPER,width=1)
            im.paste(overlay,(L,T),overlay)
            if whole:
                label('KG zipline · 15 anchors / 14 spans',points[len(points)//2][0],points[len(points)//2][1],-40,0,21)
                label('Cliff station',points[0][0],points[0][1],60,0,21)
            label('Zipline landing',points[-1][0],points[-1][1],15,24,21)
    if whole:
        for a,(x,z),p in ships:label(a,x,z,0,-25,18)
        for a,x,z,dx,dy in [('Drawbridge',1193,-1144,-65,5),('White Rosebridge',1248,-1104,0,25),('Fountain',1138,-1128,-25,-30),('South town',1135,-1096,-10,40),('Rosewater Castle',1233,-1004,0,30),('Watermill',1320,-973,-30,-25),('Hypertubes',1331,-943,42,25)]:label(a,x,z,dx,dy,21)
        for z in(-991,-943):
            a=pt((1331,z));d.rectangle((a[0]-5,a[1]-5,a[0]+5,a[1]+5),fill='#d6a367',outline=INK,width=1)
    legend_y=T+h*scale+24
    items=[(CONTEXT,'Retained / landmarks'),(BUILT,'Completed city'),(PAVERS,'Ground treatments'),(GREEN,'Greenery'),(SHIP,'Seven vessel structures')]
    avail=W-190;chunk=avail/len(items)
    for i,(color,text)in enumerate(items):
        xx=95+i*chunk;d.rectangle((xx,legend_y,xx+25,legend_y+25),fill=color);d.text((xx+36,legend_y-3),text,font=font(19 if whole else 21),fill=INK)
    d.text((95,legend_y+48),'Saved-world / receipt-based schematic · North up · 30 October 2026',font=font(21),fill=INK)
    d.text((95,legend_y+80),'Real placed geometry; not a Minecraft screenshot, live actor map or artistic acceptance.',font=font(20),fill=INK)
    d.text((95,legend_y+112),'LIFE introductions: 124 villagers · 246 wildlife · 45 tavern patrons (not live map positions)',font=font(20),fill=INK)
    name=OUT/(name+'.png');im.save(name,optimize=True)
    return {'image':name.name,'sha256':hashlib.sha256(name.read_bytes()).hexdigest(),'bounds_xz':bounds,'pixels_per_block':scale,'world_writes':0}
maps=[make('tortuga-current-overhead',[940,-1430,1420,-1090],5,'TORTUGA · FULL CITY','Entire north bank, original district, western and eastern quarters',False),make('whole-build-current-overhead',[900,-1540,1455,-680],3,'ROSEWATER · ENTIRE BUILD','Tortuga, south town, castle, fountain, bridges, transport and fleet',True)]
(OUT/'map-evidence.json').write_text(json.dumps({'style_reference':'docs/plans/tortuga-east-progress-20261029-verified/east-addition-39-pelican-forge-overhead.png','maps':maps,'surface':surface,'geometry_sources':sources,'zipline_actual':bool(zipdata),'world_writes':0},indent=2)+'\n',encoding='utf-8')
print(json.dumps({'maps':maps,'geometry_columns':{'new_city':len(newcity),'retained':len(retained),'ground':len(ground),'greenery':len(green),'vessels':len(shipcells),'context':len(context)}}))
