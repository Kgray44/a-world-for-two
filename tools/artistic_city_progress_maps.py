"""Full-site progress maps from a saved baseline and genuine native additions."""
from pathlib import Path
import argparse,collections,hashlib,json,time
from PIL import Image,ImageDraw,ImageFont
from tools.artistic_city_planning_map import COAST,PINS,read,rows,boundary,COLORS,font
from tools.artistic_bridge_refinement import flatten
from tools.playtest import guard

def prepare(home,native_results,output):
    guard(16*1024**2,0);home=Path(home);output=Path(output)
    if output.exists():raise ValueError('Preserve each prior progress-map snapshot')
    records=json.loads(Path(native_results).read_bytes());coast=read(home,COAST)
    sources=list(dict.fromkeys(r['source']for r in records));assert 1<=len(sources)<=128 and len(records)<=2048
    batches=[]
    for source in sources:
        p=home/'staging'/source;mf=json.loads((p/'manifest.json').read_bytes())
        after=p/'complete-after-VERIFY-ONLY.json';expected=hashlib.sha256(after.read_bytes()).hexdigest()
        proof=[r['result']for r in records if r['source']==source and r['action']=='verify' and r['plan']=='complete-after-VERIFY-ONLY.json']
        assert len(proof)==1 and proof[0]['plan_sha256']==expected and proof[0]['failures']==0 and not proof[0].get('error') and proof[0]['cleanup_required'] is False
        matches=[]
        for marker in (home/'dashboard/settlement').glob('settlement-result-*.json.complete'):
            terminal=marker.with_suffix('')
            raw=terminal.read_bytes()
            if hashlib.sha256(raw).hexdigest()!=marker.read_text().strip():continue
            if json.loads(raw)==proof[0]:matches.append(terminal)
        assert len(matches)==1, 'Actual unique hash-marked native terminal required'
        states=flatten(json.loads((p/'cluster-PROPOSAL.json').read_bytes()))
        roof={(x,z)for (x,y,z),s in states.items()if y>=67 and s.split('[',1)[0]not in ('minecraft:air','minecraft:cave_air','minecraft:water')}
        batches.append({'source':source,'roof':roof,'buildings':len(mf['buildings']),'verified':proof[0]['finished'],'proof':proof[0],'after_sha256':expected})
    output.mkdir(parents=True);x0,z0,x1,z1=coast['bounds_xz'];w=x1-x0+1;h=z1-z0+1
    baseline=Image.new('RGB',(w,h),COLORS['unknown']);px=baseline.load();old=set()
    for x,z,code,y in coast['samples']:
        px[x-x0,z-z0]=tuple(bytes.fromhex(COLORS[{1:'water',2:'ground',3:'context'}.get(code,'unknown')][1:]))
        if code==3 and y is not None and y>=67 and z<-1115:old.add((x,z))
    previous=set();receipts=[]
    for index,batch in enumerate(batches,1):
        image=Image.new('RGB',(2480,2180),COLORS['paper']);draw=ImageDraw.Draw(image);scale=5;left=95;top=190
        image.paste(baseline.resize((w*scale,h*scale),Image.Resampling.NEAREST),(left,top))
        def pt(p):return left+(p[0]-x0)*scale,top+(p[1]-z0)*scale
        def area(cells,color,edge=None):
            for x,z,n in rows(cells):
                a,b=pt((x,z)),pt((x+n,z+1));draw.rectangle((a[0],a[1],b[0]-1,b[1]-1),fill=color)
            if edge:
                for a,b in boundary(cells):draw.line([pt(a),pt(b)],fill=edge,width=2)
        area(old-previous-batch['roof'],'#8b8d7f')
        area(previous,'#5c6255','#414a3e');area(batch['roof'],'#467f59','#174d32')
        xs=[p[0]for p in batch['roof']];zs=[p[1]for p in batch['roof']];a=pt((min(xs)-3,min(zs)-3));b=pt((max(xs)+4,max(zs)+4))
        draw.rectangle((a[0],a[1],b[0],b[1]),outline='#d59b2d',width=6)
        draw.text((95,36),f'PIRATE CITY · ADDITION {index}',font=font(49,True),fill=COLORS['ink'])
        draw.text((98,104),f'{batch["buildings"]} newly placed buildings · {sum(b["buildings"]for b in batches[:index])} added since the approved plan',font=font(29),fill=COLORS['ink'])
        draw.text((98,150),'Full north-bank site · North up · Existing gray / this addition green',font=font(25),fill=COLORS['ink'])
        draw.text((2380,40),'N',font=font(33,True),fill=COLORS['ink'])
        draw.line((2400,135,2400,95),fill=COLORS['ink'],width=4)
        draw.polygon(((2400,86),(2391,102),(2409,102)),fill=COLORS['ink'])
        yy=2060
        draw.rectangle((95,yy,125,yy+26),fill='#8b8d7f');draw.text((140,yy-2),'Existing saved roofs and built features',font=font(24),fill=COLORS['ink'])
        draw.rectangle((845,yy,875,yy+26),fill='#5c6255');draw.text((890,yy-2),'Earlier verified additions',font=font(24),fill=COLORS['ink'])
        draw.rectangle((1455,yy,1485,yy+26),fill='#467f59');draw.text((1500,yy-2),'New in this addition',font=font(24),fill=COLORS['ink'])
        draw.text((95,2110),'Schematic overhead: authenticated saved baseline + completed native placement. Artistic screenshots follow separately.',font=font(22),fill=COLORS['ink'])
        file=output/f'addition-{index:02d}-overhead.png';image.save(file,optimize=True)
        receipts.append({'addition':index,'new_buildings':batch['buildings'],'cumulative_added_buildings':sum(b['buildings']for b in batches[:index]),'image':file.name,'image_sha256':hashlib.sha256(file.read_bytes()).hexdigest(),'source':batch['source'],'after_plan_sha256':batch['after_sha256'],'native_finished':batch['verified'],'native_proof':batch['proof'],'baseline_coast_sha256':PINS[COAST],'evidence':'Schematic current/new roof-coverage map; no proposed future buildings are represented as current','artistic_acceptance':False})
        previous|=batch['roof']
    (output/'map-receipts.json').write_text(json.dumps(receipts,indent=2)+'\n')
    print(json.dumps({'output':str(output),'maps':[r['image']for r in receipts],'new_actual_buildings':sum(b['buildings']for b in batches),'world_writes':0}))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--home',type=Path,required=True);p.add_argument('--native-results',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();prepare(a.home,a.native_results,a.output)
