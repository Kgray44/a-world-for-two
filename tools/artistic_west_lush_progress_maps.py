"""Six proof-led Tortuga overlays on the existing current14-East city diagram.

No native calls, save reads, future-plan promotion or new city design. Private
plans are read locally; only rendered diagrams and sanitized proof hashes leave.
"""
from pathlib import Path
import argparse,json
from PIL import Image,ImageDraw

from control_room.common import UserError,digest,read_json
from tools.artistic_city_planning_map import COAST,PINS,read,rows,COLORS,font
from tools.artistic_bridge_refinement import flatten
from tools.playtest import guard

MIB=1024**2
BASE='docs/plans/city-progress-20261029-fresh-eleven'
BASE_IMAGE_SHA='7d491c6a5049d7d6d2bdcd4d8304e1faf1797fa826a0096f64c153cca078dbac'
BASE_RECEIPT_SHA='9d16a268cf9932bb4469722b1204e6beb90894d99b86065740d25f2bd84a8744'
COMPLETE_SHA='79da89c5dc3e03999e633aa5e5402e8d664135fe602d038c1b32618fb6ba9bd1'
LABELS=('Worn masonry · first alley','Outdoor gravel replaced · first alley',
        'Rooted and climbing greenery · first alley','Worn masonry · wider West',
        'Outdoor gravel replaced · wider West','Layered greenery · whole eligible West')


def checked(home,relative,sha):
    path=(home/relative).resolve()
    if not path.is_relative_to(home)or path.is_symlink()or not path.is_file()or path.stat().st_size>4*MIB or digest(path)!=sha:
        raise UserError('Exact bounded owned native proof/plan required')
    return read_json(path)


def prepare(home,completion,output):
    reserve=guard(32*MIB,0);home=Path(home).resolve();output=Path(output).absolute()
    if output.exists():raise UserError('Retain every prior map output')
    completion=Path(completion).resolve()
    if not completion.is_relative_to(home/'staging')or digest(completion)!=COMPLETE_SHA:
        raise UserError('Exact all-six genuinely completed native record required')
    data=read_json(completion)
    if data.get('steps')!=6 or len(data.get('results',[]))!=30:raise UserError('All30 real operation records required')
    baseline=Path(BASE);receipt=baseline/'map-receipts.json'
    if digest(receipt)!=BASE_RECEIPT_SHA:raise UserError('Existing14-East map receipt differs')
    old=read_json(receipt)[-1];image_path=baseline/old['image']
    if(old.get('actual_E_compounds_at_milestone')!=14 or old.get('remaining_unbuilt_E')!=25
            or old.get('total_nonempty_E')!=39 or digest(image_path)!=BASE_IMAGE_SHA):
        raise UserError('Keep current14 versus pending25 truthful')
    coast=read(home,COAST);x0,z0,x1,z1=coast['bounds_xz'];left,top,scale=95,190,5
    base=Image.open(image_path).convert('RGB')
    if base.size!=(2480,2180):raise UserError('Existing full-site diagram frame changed')
    # Normalize only the previous diagram's last-addition highlight class. The
    # existing Native geometry, partial retirement and future outlines stay.
    pixels=base.load()
    for yy in range(top,top+(z1-z0+1)*scale):
        for xx in range(left,left+(x1-x0+1)*scale):
            if pixels[xx,yy]==(213,155,45):pixels[xx,yy]=(23,77,50)
            elif pixels[xx,yy]==(55,162,96):pixels[xx,yy]=(70,127,89)
    phases=[]
    for step in range(1,7):
        records=[r for r in data['results']if r['step']==step]
        if {r['operation']for r in records}!={'verify-before','place','settle','verify','map'}:
            raise UserError('Every phase needs before/place/normal-settle/after/map')
        proof=[];states=None
        for row in records:
            terminal=checked(home,row['terminal']['path'],row['terminal']['sha256'])
            p=home/row['terminal']['path'];marker=p.with_name(p.name+'.complete')
            if marker.read_text().strip()!=row['terminal']['sha256']:raise UserError('Native completion marker differs')
            if(terminal.get('plan_sha256')!=row['plan_sha256']or not terminal.get('finished')or terminal.get('failures',0)
                    or terminal.get('error')or terminal.get('cleanup_required')is not False
                    or terminal.get('temporary_tickets_remaining')!=0 or terminal.get('pending_shared_chunk_futures')!=0):
                raise UserError('Only genuinely completed and resource-clean native work may be drawn')
            plan=checked(home,row['plan'],row['plan_sha256'])
            if row['operation']=='place':states=flatten(plan)
            proof.append({'operation':row['operation'],'terminal_sha256':row['terminal']['sha256'],
                'plan_sha256':row['plan_sha256'],'finished':terminal['finished'],
                'failures':0,'cleanup_required':False,'temporary_tickets_remaining':0,'pending_shared_chunk_futures':0})
        if not states:raise UserError('Actual placed geometry is missing')
        phases.append((states,proof))
    output.mkdir(parents=True);ground={};green={};receipts=[];ground_total=green_total=0
    def point(p):return left+(p[0]-x0)*scale,top+(p[1]-z0)*scale
    def paint(draw,cells,color):
        for x,z,n in rows(cells):
            a,b=point((x,z)),point((x+n,z+1));draw.rectangle((a[0],a[1],b[0]-1,b[1]-1),fill=color)
    for step,(states,proofs)in enumerate(phases,1):
        if step in(3,6):green.update(states);green_total+=len(states)
        else:ground.update(states);ground_total+=len(states)
        roots={(x,z)for(x,y,z),v in green.items()if y==63}
        foliage={(x,z)for(x,y,z),v in green.items()if y>63}
        image=base.copy();draw=ImageDraw.Draw(image)
        paint(draw,{(x,z)for x,y,z in ground}-roots,'#a18462')
        paint(draw,roots,'#91ac70');paint(draw,foliage,'#33704c')
        draw.rectangle((0,0,2479,184),fill=COLORS['paper'])
        draw.text((95,29),f'TORTUGA · WEST PASS {step}/6',font=font(45,True),fill=COLORS['ink'])
        draw.text((98,91),LABELS[step-1],font=font(28),fill=COLORS['ink'])
        draw.text((98,134),f'{ground_total:,} ground cells · {green_total:,} greenery targets · East14 built /25 pending',font=font(24),fill=COLORS['ink'])
        draw.text((2380,40),'N',font=font(33,True),fill=COLORS['ink'])
        draw.line((2400,135,2400,95),fill=COLORS['ink'],width=4);draw.polygon(((2400,86),(2391,102),(2409,102)),fill=COLORS['ink'])
        draw.rectangle((0,2045,2479,2179),fill=COLORS['paper'])
        for xx,color,label in((95,'#8b8d7f','Retained structures'),(560,'#467f59','East: built14'),
                (970,'#d6a367','Pending25'),(1310,'#a18462','New pavers'),(1700,'#33704c','New planted layers')):
            draw.rectangle((xx,2060,xx+26,2086),fill=color);draw.text((xx+38,2057),label,font=font(22),fill=COLORS['ink'])
        draw.text((95,2100),'Receipt-based progress diagram, NOT a Minecraft screenshot or live terrain survey. North up.',font=font(22),fill=COLORS['ink'])
        draw.text((95,2135),'Existing buildings, inventories, river and human transport retained. Eye-level art and restart review remain separate.',font=font(21),fill=COLORS['ink'])
        name=f'tortuga-west-pass-{step:02d}-overhead.png';image.save(output/name,optimize=True)
        receipts.append({'pass':step,'title':'TORTUGA','phase':LABELS[step-1],'image':name,'image_sha256':digest(output/name),
            'actual_ground_cells_cumulative':ground_total,'actual_greenery_targets_cumulative':green_total,
            'actual_grass_soil_pockets_cumulative':len(roots),'actual_east_compounds':14,'pending_east_compounds':25,
            'actual_native_proofs':proofs,'baseline_image_sha256':BASE_IMAGE_SHA,'baseline_receipt_sha256':BASE_RECEIPT_SHA,
            'baseline_coast_sha256':PINS[COAST],'native_completion_record_sha256':COMPLETE_SHA,
            'geometry_frame':{'x0':x0,'z0':z0,'left':left,'top':top,'pixels_per_block':scale},
            'representation':'Schematic work coverage; existing14-East geometry/verified partial old-surface retirement and25 pending outlines preserved from the previous proven map',
            'source_plans_relabelled_as_current':False,'artistic_acceptance':False,'world_writes':0,'native_actions':0})
    (output/'map-receipts.json').write_text(json.dumps(receipts,indent=2)+'\n',encoding='utf-8')
    return{'output':str(output),'images':[r['image']for r in receipts],'receipt_sha256':digest(output/'map-receipts.json'),
        'source_sha256':digest(Path(__file__)),'reserve_guard':reserve,'native_actions':0}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for n in('home','completion','output'):parser.add_argument('--'+n,type=Path,required=True)
    a=parser.parse_args();print(json.dumps(prepare(a.home,a.completion,a.output),indent=2))
