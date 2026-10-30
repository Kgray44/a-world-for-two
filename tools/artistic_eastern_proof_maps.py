"""Proof-led whole-city maps for real eastern additions, never proposed houses.

Retains all old eastern roofs until a separate real retirement overlay exists.
"""
from pathlib import Path
import argparse,hashlib,json
from PIL import Image,ImageDraw
from control_room.common import UserError,digest,read_json
from tools.artistic_city_planning_map import COAST,PINS,read,rows,boundary,COLORS,font
from tools.artistic_bridge_refinement import flatten
from tools.playtest import guard

MIB=1024**2
LAYOUT=('staging/eastern-coast-urban-layout-1793205607174241200/urban-plan-REVIEW-ONLY.json','6f24640d9efefae3340be80d34bcd0e4788f2ded695aefe03d1d6815761a12a4')
REFINEMENT=('staging/west15-shells-1793218803041549500/manifest.json','52669f6d5ae92e82a18c1577a99a56e2648fc2dc570a3ff8b33987659b404f42')
AIR={'minecraft:air','minecraft:cave_air','minecraft:void_air','minecraft:water'}


def roof(doc):return{(x,z)for(x,y,z),s in flatten(doc).items()if y>=67 and s.split('[',1)[0]not in AIR}


def prepare(home,earlier,refinements,native_results,output):
    reserve=guard(32*MIB,0);home=Path(home).resolve();output=Path(output).absolute()
    if output.exists():raise UserError('Preserve every earlier progress map')
    coast=read(home,COAST);layout_path=home/LAYOUT[0]
    if digest(layout_path)!=LAYOUT[1]:raise UserError('Exact approved plan required for source-only outlines')
    layout=read_json(layout_path);old_records=read_json(Path(earlier));refined_records=read_json(Path(refinements));new_records=read_json(Path(native_results));marked=[]
    for marker in(home/'dashboard/settlement').glob('settlement-result-*.json.complete'):
        path=marker.with_suffix('')
        if path.is_symlink()or not path.is_file()or not 0<path.stat().st_size<=MIB:continue
        raw=path.read_bytes();sha=hashlib.sha256(raw).hexdigest()
        if sha==marker.read_text().strip():marked.append((path,sha,json.loads(raw)))
    def genuine(result,plan):
        if(result.get('operation')!='verify'or result.get('plan_sha256')!=digest(plan)or result.get('failures')!=0 or result.get('cleanup_required')is not False or result.get('temporary_tickets_remaining')!=0 or result.get('pending_shared_chunk_futures')!=0 or result.get('error')or result.get('ticket_cleanup_error')or not result.get('finished')):raise UserError('Actual clean full Native verify, not source or partial operation, required')
        matches=[(p,s)for p,s,d in marked if d==result]
        if len(matches)!=1:raise UserError('One unique genuine hash-marked native terminal required')
        p,s=matches[0];return{'path':p.relative_to(home).as_posix(),'sha256':s,'plan_sha256':digest(plan),'finished':result['finished']}
    western=set();old_proofs=[]
    for row in old_records:
        folder=home/'staging'/row['source'];plan=folder/'complete-after-VERIFY-ONLY.json';old_proofs.append(genuine(row['native_proof'],plan));western|=roof(read_json(folder/'cluster-PROPOSAL.json'))
    if old_records[-1]['cumulative_added_buildings']!=36:raise UserError('The current36 western additions are required')
    refined=set();refproofs=[];manifest=home/REFINEMENT[0]
    if digest(manifest)!=REFINEMENT[1]or sum(r['existing_buildings_refined']for r in refined_records)!=15:raise UserError('Exactly15 real refinements required')
    for row in refined_records:
        plan=manifest.parent/('west15-'+str(row['group'])+'-full-VERIFY-ONLY.json');terminal=home/row['native_full_verification']['path']
        if digest(terminal)!=row['native_full_verification']['sha256']:raise UserError('Refinement terminal differs')
        refproofs.append(genuine(read_json(terminal),plan));refined|=roof(read_json(plan))
    additions=[]
    for ident in('east-coal','shoal-warden','thin-sail'):
        actual=[r for r in new_records if r.get('building')==ident and r.get('action')=='verify'and r.get('plan')==ident+'-complete-after-VERIFY-ONLY.json']
        if len(actual)!=1:raise UserError('Exactly one actual complete verification per eastern building required')
        row=actual[0];plan=Path(row['actual_plan']).resolve()
        if not plan.is_relative_to(home/'staging')or plan.is_symlink():raise UserError('Owned actual Native after document required')
        proof=genuine(row['result'],plan);additions.append({'id':ident,'proof':proof,'roof':roof(read_json(plan))})
    x0,z0,x1,z1=coast['bounds_xz'];width,height=x1-x0+1,z1-z0+1
    if not 1<=width<=460 or not 1<=height<=390:raise UserError('Finite full-site map bound required')
    base=Image.new('RGB',(width,height),COLORS['unknown']);pixels=base.load();old=set()
    for x,z,code,y in coast['samples']:
        pixels[x-x0,z-z0]=tuple(bytes.fromhex(COLORS[{1:'water',2:'ground',3:'context'}.get(code,'unknown')][1:]))
        if code==3 and y is not None and y>=67 and z<-1115:old.add((x,z))
    output.mkdir(parents=True);prior=set();built=set();receipts=[]
    for index,batch in enumerate(additions,1):
        image=Image.new('RGB',(2480,2180),COLORS['paper']);draw=ImageDraw.Draw(image);scale,left,top=5,95,190
        image.paste(base.resize((width*scale,height*scale),Image.Resampling.NEAREST),(left,top))
        def point(q):return left+(q[0]-x0)*scale,top+(q[1]-z0)*scale
        def area(cells,color,edge=None):
            for x,z,n in rows(cells):
                a,b=point((x,z)),point((x+n,z+1));draw.rectangle((a[0],a[1],b[0]-1,b[1]-1),fill=color)
            if edge:
                for a,b in boundary(cells):draw.line([point(a),point(b)],fill=edge,width=2)
        area(old,'#8b8d7f');area(western,'#5c6255');area(refined,'#9b6e4e','#554936');area(prior,'#467f59','#174d32')
        built.add(batch['id'])
        for building in layout['buildings']:
            if building['id']in built:continue
            for mass in building['masses']:
                a,z,b,w=mass['bounds_xz'];lo,hi=point((a,z)),point((b+1,w+1))
                draw.rectangle((lo[0],lo[1],hi[0]-1,hi[1]-1),outline='#d6a367',width=1)
        area(batch['roof'],'#37a260','#125533')
        xs=[p[0]for p in batch['roof']];zs=[p[1]for p in batch['roof']];a=point((min(xs)-2,min(zs)-2));b=point((max(xs)+3,max(zs)+3));draw.rectangle((a[0],a[1],b[0],b[1]),outline='#d59b2d',width=5)
        draw.text((95,36),'PIRATE CITY · EAST ADDITION '+str(index),font=font(45,True),fill=COLORS['ink'])
        draw.text((98,103),f'{batch["id"].replace("-"," ").title()} built · {36+index} new buildings +15 existing buildings refined',font=font(28),fill=COLORS['ink'])
        draw.text((98,149),'Full north bank · North up · E outlines are approved future footprints, not current buildings',font=font(24),fill=COLORS['ink'])
        draw.text((2380,40),'N',font=font(33,True),fill=COLORS['ink']);draw.line((2400,135,2400,95),fill=COLORS['ink'],width=4);draw.polygon(((2400,86),(2391,102),(2409,102)),fill=COLORS['ink'])
        for x,color,label in[(95,'#8b8d7f','Old E grid still present'),(650,'#5c6255','36 new West'),(1110,'#9b6e4e','15 refined'),(1530,'#37a260','This E addition'),(2000,'#d6a367','Future outline')]:
            draw.rectangle((x,2060,x+25,2085),fill=color);draw.text((x+38,2057),label,font=font(22),fill=COLORS['ink'])
        draw.text((95,2110),'Schematic from authentic saved coast + completed Native proofs. No old E roofs retired; actual Minecraft art review pending.',font=font(21),fill=COLORS['ink'])
        path=output/f'east-addition-{index:02d}-overhead.png';image.save(path,optimize=True);prior|=batch['roof']
        receipts.append({'addition':index,'building':batch['id'],'image':path.name,'image_sha256':digest(path),'actual_new_west_buildings':36,'actual_refined_old_buildings':15,'actual_new_east_buildings':index,'current_native_proof':batch['proof'],'prior_west_proofs':old_proofs,'refinement_proofs':refproofs,'baseline_coast_sha256':PINS[COAST],'approved_future_layout_sha256':LAYOUT[1],'old_E_roof_cells_subtracted':0,'source_plans_displayed_as_current':False,'artistic_acceptance':False,'world_writes':0})
    (output/'map-receipts.json').write_text(json.dumps(receipts,indent=2)+'\n',encoding='utf8')
    return{'output':str(output),'maps':[str(output/r['image'])for r in receipts],'map_receipts_sha256':digest(output/'map-receipts.json'),'old_E_roofs_subtracted':0,'native_actions':0,'world_writes':0,'storage_guard':reserve}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in('home','earlier','refinements','native-results','output'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();print(json.dumps(prepare(a.home,a.earlier,a.refinements,a.native_results,a.output),indent=2))
