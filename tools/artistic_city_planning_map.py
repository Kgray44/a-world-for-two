"""Draw the owner's city review plan; no world reads, edits or native commands."""
from __future__ import annotations
import argparse, base64, hashlib, html, io, json
from collections import defaultdict
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

COAST='staging/forest-expanded06-north-fine-20261028T1710Z/north-shore.json'
WEST='staging/west-owner-map-CONCEPT-1793208487635073800/concept.json'
EAST='staging/eastern-coast-urban-layout-1793205607174241200/urban-plan-REVIEW-ONLY.json'
FIELD='staging/tortuga-current-field-1793205390836332300/field-READONLY.json'
PINS={COAST:'7805a8fcc0f514cb26b222058474a2efa9f821124ee64cf52ca8ce4c3e66e2f2',
      WEST:'13ecf315c0be993ef5d37bdbe250b576808622acf66e8598f76a714ccc35b49a',
      EAST:'6f24640d9efefae3340be80d34bcd0e4788f2ded695aefe03d1d6815761a12a4',
      FIELD:'86cd8f6cc58f5c0b1b1fe7a5fabef09944f78089421cf71ab208c0184d5c7ff6'}
COLORS={'paper':'#efe8d6','ink':'#34392f','water':'#9bb7b1','ground':'#d8d0ae',
        'context':'#c4c0a4','unknown':'#e4dfcf','street':'#eee2c7','keep':'#646d59',
        'west':'#9b6e4e','east':'#b18a64','line':'#554936','infill':'#ccb28c',
        'plant':'#889875','cable':'#78523b'}

def read(home,rel):
    p=home/rel;raw=p.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=PINS[rel]:raise ValueError('Frozen map input changed: '+rel)
    return json.loads(raw)

def rows(cells):
    by=defaultdict(list)
    for x,z in set(map(tuple,cells)):by[z].append(x)
    result=[]
    for z,xs in sorted(by.items()):
        xs.sort();start=last=xs[0]
        for x in xs[1:]:
            if x!=last+1:result.append((start,z,last-start+1));start=x
            last=x
        result.append((start,z,last-start+1))
    return result

def boundary(cells):
    cells=set(map(tuple,cells));out=[]
    for x,z in cells:
        if (x,z-1)not in cells:out.append(((x,z),(x+1,z)))
        if (x+1,z)not in cells:out.append(((x+1,z),(x+1,z+1)))
        if (x,z+1)not in cells:out.append(((x+1,z+1),(x,z+1)))
        if (x-1,z)not in cells:out.append(((x,z+1),(x,z)))
    return out

def font(size,bold=False):
    return ImageFont.truetype(str(Path('C:/Windows/Fonts')/('georgiab.ttf' if bold else 'georgia.ttf')),size)

def prepare(home,output):
    from tools.playtest import guard
    guard(32*1024**2,0)
    home=Path(home);output=Path(output)
    if output.exists():raise ValueError('Preserve the previous review drawing')
    coast,west,east,field=[read(home,p)for p in (COAST,WEST,EAST,FIELD)]
    if len({d.get('checkpoint_sha256',d.get('current_stopped_checkpoint_sha256')) for d in (coast,west,east,field)})!=1:
        raise ValueError('The drawn inputs must describe the same current checkpoint')
    bounds=coast['bounds_xz'];x0,z0,x1,z1=bounds;ww=x1-x0+1;hh=z1-z0+1
    ground=Image.new('RGB',(ww,hh),COLORS['unknown']);pixels=ground.load()
    for x,z,code,y in coast['samples']:
        pixels[x-x0,z-z0]=tuple(bytes.fromhex(COLORS[{1:'water',2:'ground',3:'context'}.get(code,'unknown')][1:]))
    groups=[]
    for b in west['proposed_buildings']:
        groups.append({'id':b['id'],'name':b['name'],'kind':'west','cells':b['cells_xz'],'purpose':b['purpose'],'state':'Proposed layout concept'})
    for i,b in enumerate(east['buildings'],1):
        cells=b['actual_building_floor_columns_xz']
        if cells:groups.append({'id':f'E-{i:02d}','name':b['name'],'kind':'east','cells':cells,'purpose':b['program'],'state':'Proposed unequal building and room footprints'})
    for b in west['retained_or_modeled_context']:
        groups.append({'id':'KEEP','name':b['name'].replace('current ','').replace('retained ','').replace('future ',''),
                       'kind':'keep' if not b['name'].startswith('future ')else 'west','cells':b['cells_xz'],
                       'purpose':'Existing landmark / retained prototype' if not b['name'].startswith('future ')else'Prepared building concept','state':'Review context; no new artistic acceptance'})
    for b in west['already_modeled_five']:
        groups.append({'id':'NEW','name':b['name'],'kind':'west','cells':b['cells_xz'],'purpose':b.get('purpose','Home and workshop'),'state':'Prepared individual building; not yet placed'})
    streets=set()
    for line in west['crooked_alley_lines']:
        for s in line['segments']:
            for x,z in s['centerline_xz']:streets.update((x+dx,z+dz)for dx in (0,1)for dz in (0,1))
    for s in east['street_network']:streets.update(map(tuple,s['all_walk_columns_xz']))
    # These are actual previously placed small boardwalk columns, not a guessed crossing.
    streets.update((x,z)for x in range(1003,1013)for z in (-1281,-1280))
    all_floor=set().union(*(set(map(tuple,g['cells']))for g in groups))
    natural_north={(x,z)for x,y,z in coast['current_natural_north_component_xzy']}
    # Draw unscheduled shorefront as an explicitly different layout zone. It must
    # never masquerade as a finished or physically modeled building footprint.
    shore_residual={p for p in natural_north-all_floor-streets if p[1]<-1120}
    image=Image.new('RGB',(2900,2500),COLORS['paper']);d=ImageDraw.Draw(image)
    left,top,scale=95,215,5.5
    def point(p):return (round(left+(p[0]-x0)*scale),round(top+(p[1]-z0)*scale))
    scaled=ground.resize((round(ww*scale),round(hh*scale)),Image.Resampling.NEAREST)
    image.paste(scaled,(left,top))
    plotw,ploth=scaled.size
    svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="2900" height="2500" viewBox="0 0 2900 2500"><title>Pirate City — whole north-bank planning review</title><desc>Measured Minecraft shoreline with proposed dense west and east building layouts, narrow alleys, retained landmarks, bridge and western zipline landing. City rebuilding is held for owner review. This is a planning drawing, not a screenshot or finished-world claim.</desc><rect width="2900" height="2500" fill="{COLORS["paper"]}"/>']
    buf=io.BytesIO();scaled.save(buf,format='PNG')
    svg.append(f'<image x="{left}" y="{top}" width="{plotw}" height="{ploth}" href="data:image/png;base64,{base64.b64encode(buf.getvalue()).decode()}"/>')
    def text(pos,value,size=28,fill=None,bold=False,anchor=None):
        fill=fill or COLORS['ink'];d.text(pos,value,font=font(size,bold),fill=fill,anchor=anchor)
        x,y=pos;svg.append(f'<text x="{x}" y="{y+size}" font-family="Georgia,serif" font-size="{size}" fill="{fill}" font-weight="{700 if bold else 400}">{html.escape(value)}</text>')
    def line(points,color,width=2,dash=None):
        ps=[point(p)for p in points];d.line(ps,fill=color,width=max(1,round(width)))
        svg.append(f'<polyline points="'+ ' '.join(f'{x},{y}'for x,y in ps)+f'" fill="none" stroke="{color}" stroke-width="{width}"'+(f' stroke-dasharray="{dash}"'if dash else'')+'/>')
    def area(cells,color,outline=False,title=''):
        cells=set(map(tuple,cells));path=[]
        for x,z,w in rows(cells):
            a,b=point((x,z)),point((x+w,z+1));d.rectangle([a,(b[0]-1,b[1]-1)],fill=color)
            path.append(f'M{a[0]} {a[1]}h{b[0]-a[0]}v{b[1]-a[1]}h{a[0]-b[0]}z')
        svg.append(f'<g><title>{html.escape(title)}</title><path d="'+''.join(path)+f'" fill="{color}"/>')
        if outline:
            edges=boundary(cells);sp=[]
            for a,b in edges:
                p,q=point(a),point(b);d.line([p,q],fill=COLORS['line'],width=2);sp.append(f'M{p[0]} {p[1]}L{q[0]} {q[1]}')
            svg.append('<path d="'+''.join(sp)+f'" fill="none" stroke="{COLORS["line"]}" stroke-width="1.4"/>')
        svg.append('</g>')
    # The residual is a shorefront infill zone, not paving and not counted as houses.
    area(shore_residual,COLORS['infill'],title='Waterfront infill area: additional compact building footprints still to detail')
    area(streets,COLORS['street'],title='Narrow working alleys, generally two blocks wide; stepped links still to fit')
    for g in groups:area(g['cells'],COLORS[g['kind']],True,g['id']+' · '+g['name']+' · '+g['purpose']+' · '+g['state'])
    # Individual unequal roof/room masses remain visible inside an attached block.
    for b in east['buildings']:
        for mass in b['masses']:
            ax,az,bx,bz=mass['bounds_xz']
            line([(ax,az),(bx+1,az),(bx+1,bz+1),(ax,bz+1),(ax,az)],'#795f45',1.2)
    # Retain the real river navigation corridor and drawbridge location.
    bridge={(x,z)for x in range(1187,1200)for z in range(-1172,-1114)}
    area(bridge,'#9d8d66',True,'Existing mechanical drawbridge — clear river channel below')
    cable=[(1064,-1008),(1048,-1064),(1056,-1112),(1048,-1176),(1048,-1232),(1064,-1248),(1100,-1256)]
    for a,b in zip(cable,cable[1:]):
        for i in range(0,20,2):line([(a[0]+(b[0]-a[0])*i/20,a[1]+(b[1]-a[1])*i/20),(a[0]+(b[0]-a[0])*(i+1)/20,a[1]+(b[1]-a[1])*(i+1)/20)],COLORS['cable'],3)
    # Compact numbered leaders keep the actual city readable.
    landmarks=[('1','Captain’s Rest tavern',(1040,-1285),(976,-1335)),
               ('2','Salt & Petal flower shop',(1062,-1297),(1038,-1352)),
               ('3','Western zipline landing',(1100,-1256),(1106,-1350)),
               ('4','Narrow working alleys',min(streets,key=lambda p:abs(p[0]-1087)+abs(p[1]+1259)),(1057,-1168)),
               ('5','Fish shop & shipwright waterfront',(1322,-1329),(1295,-1370)),
               ('6','Lantern Harbor Inn',(1298,-1253),(1338,-1315)),
               ('7','East market & workshops',(1350,-1210),(1360,-1150)),
               ('8','Mechanical drawbridge',(1193,-1143),(1215,-1090))]
    labels=[]
    for num,name,p,l in landmarks:
        line([p,l],COLORS['line'],1.6);cx,cy=point(p);r=17
        d.ellipse((cx-r,cy-r,cx+r,cy+r),fill=COLORS['paper'],outline=COLORS['ink'],width=2)
        d.text((cx,cy),num,font=font(22,True),fill=COLORS['ink'],anchor='mm')
        svg.append(f'<circle cx="{cx}" cy="{cy}" r="17" fill="{COLORS["paper"]}" stroke="{COLORS["ink"]}"/><text x="{cx}" y="{cy+8}" text-anchor="middle" font-family="Georgia" font-size="22" fill="{COLORS["ink"]}">{num}</text>')
        tx,ty=point(l);text((tx,ty),num+'  '+name,25,bold=True);labels.append({'number':num,'name':name,'xz':p})
    text((95,42),'ROSEWATER · PIRATE CITY',54,bold=True)
    text((98,112),'Whole north-bank planning map  /  DRAFT FOR YOUR REVIEW',27)
    text((98,157),'Buildings fill the districts; crooked narrow alleys connect them. The river stays open.',25)
    text(point((1143,-1343)),'OPEN SEA / HARBOR',28)
    text(point((1091,-1187)),'CLEAR RIVER CHANNEL',25)
    text(point((1122,-1055)),'SOUTH BANK · FOREST WORK CONTINUES',27)
    # Compass and a true block scale use the same measured map scale.
    nx,ny=2740,99;d.polygon([(nx,ny-42),(nx-13,ny+17),(nx,ny+7),(nx+13,ny+17)],fill=COLORS['ink']);text((2719,19),'N',30,bold=True)
    bx,by=point((985,-1034));d.line([(bx,by),(bx+round(50*scale),by)],fill=COLORS['ink'],width=4)
    for v in (0,25,50):d.line([(bx+round(v*scale),by-8),(bx+round(v*scale),by+8)],fill=COLORS['ink'],width=3)
    text((bx,by+12),'0                  25                  50 blocks',22)
    legend_y=2390
    for i,(key,label)in enumerate([('keep','Retained landmarks / existing context'),('west','West proposed building plots'),('east','East proposed building footprints'),('street','Narrow alleys'),('infill','Shorefront infill still to detail')]):
        xx=95+(i%3)*900;yy=legend_y+(i//3)*44;d.rectangle((xx,yy,xx+28,yy+24),fill=COLORS[key],outline=COLORS['line']);text((xx+42,yy-2),label,23)
    # Bottom notes are deliberately separate from the footprint drawing.
    text((95,2320),'Muted timber, stone and clay palette throughout; map colors distinguish planning layers.',24)
    text((95,2356),'Planning drawing only. Unresolved stepped links and shorefront infill need refinement before rebuilding.',23)
    svg.append('</svg>');output.mkdir(parents=True)
    image.save(output/'pirate-city-overhead-v1.png',optimize=True)
    image.save(output/'pirate-city-overhead-v1.webp',quality=88,method=6)
    (output/'pirate-city-overhead-v1.svg').write_text(''.join(svg),encoding='utf8')
    # A compact transparent source makes review revisions auditable without any seed,
    # world files, player data, native inventories or construction authority.
    doc={'format':'awft-city-layout-review:1','city_rebuild_held_for_owner_review':True,
         'world_mutations':0,'north_up':True,'bounds_xz':bounds,
         'sources':{p:PINS[p]for p in PINS},'landmarks':labels,
         'building_groups':groups,'streets_xz':[list(p)for p in sorted(streets)],
         'remaining_shorefront_infill_columns':len(shore_residual),
         'scope':'Whole measured north-bank overview. West concept plots and east floor masses are proposed, not finished native buildings. Tan infill areas are not paving or completed houses.',
         'unresolved_west_links':west['unresolved_concept_connections']}
    (output/'review-plan.json').write_text(json.dumps(doc,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf8')
    print(json.dumps({'output':str(output),'building_groups':len(groups),'png_bytes':(output/'pirate-city-overhead-v1.png').stat().st_size,'svg_bytes':(output/'pirate-city-overhead-v1.svg').stat().st_size,'world_writes':0}))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--home',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();prepare(a.home,a.output)
