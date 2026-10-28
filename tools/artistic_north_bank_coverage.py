"""Exact retained source coverage; a measured plan view, never art acceptance.

No MCA reader, current-world inspection, native action or further house builder.
The historical one-metre surface field is retained as such, with its limitations.
"""
from __future__ import annotations
import argparse,hashlib,json,time
from collections import deque
from pathlib import Path

from control_room.common import UserError,digest,read_json
from tools.artistic_bridge_refinement import flatten
from tools.playtest import guard

MIB=1024**2
FIELD=('staging/north-bank-residual-1793159933733952500/residual-study.json',
       '817e58f7314b44390d2006db38d69b0ad3c7f87227b61173ca4649cac75d46d7')
NORTH=('staging/north-bank-residual-1793158994899675300/north-connected-columns-ONLY.json',
       '594706123bb9ac14f447a8f95f810cf595c952f1d8edb1c6ebfba4ae54e5b103')
NEW=(
 ('staging/north-bank-profiled-shore-1793160211442720000/prototype.json','3a847ceee5f21ec647f4a3fbb7c5e7a00a8092a3e6c0b5135b147f277ff9fba5','additional fourteen shore houses'),
 ('staging/north-bank-west-extra-court-routes-1793161504975467000/connections.json','4cdd0d214586206c9ba6626be2e879022a0d604f91a3e89959fcfae70208372d','fourteen western connections'),
 ('staging/north-bank-east-extra-court-routes-1793161521319763800/connections.json','0a53ce1bcfbc35b8bed1a125bba478c53aa328b285ef48e2564eb906b10a5f30','six eastern connections'),
)


def profile_columns(center):
    x,z=center
    return {(x+dx,z+dz) for dx in range(-4,5) for dz in range(-5,6)}


def remaining_profiles(centres,new_geometry_columns):
    """Protect the whole footprint/model skirt, including authored AIR."""
    skirt={(x+dx,z+dz) for x,z in new_geometry_columns for dx in (-1,0,1) for dz in (-1,0,1)}
    return [tuple(q) for q in centres if not profile_columns(q)&skirt]


def components(points):
    remaining=set(points);result=[]
    while remaining:
        root=min(remaining);remaining.remove(root);todo=deque([root]);part=[]
        while todo:
            x,z=todo.popleft();part.append((x,z))
            for q in ((x-1,z),(x+1,z),(x,z-1),(x,z+1)):
                if q in remaining:remaining.remove(q);todo.append(q)
        result.append(part)
    return sorted(result,key=lambda rows:(-len(rows),rows[0]))


def prepare(home):
    home=Path(home).resolve();reserve=guard(MIB,4*MIB)
    if home.parent!=Path('D:/A World for Two/staging/world-tests').resolve():raise UserError('Owned private source study only')
    for rel,sha in (FIELD,NORTH):
        if digest(home/rel)!=sha:raise UserError('Exact historical measured surface source changed')
    field=read_json(home/FIELD[0]);north=read_json(home/NORTH[0])
    if field['checkpoint_sha256']!=north['checkpoint_sha256']:raise UserError('Measured bank and field provenance differ')
    old=set();new=set();lanes=set();sources=[]
    for row in field['existing_source_custody']+field['new_source_custody']:
        relative=row.get('path',row.get('relative'));path=home/relative
        if digest(path)!=row['sha256']:raise UserError('A baseline source changed')
        old.update((x,z) for x,y,z in flatten(read_json(path)))
        sources.append({'path':relative,'sha256':row['sha256'],'status':'Historical source dependency; native placement/art not inferred'})
    for rel,sha,label in NEW:
        path=home/rel
        if digest(path)!=sha:raise UserError('Exact later geometry changed')
        cells={(x,z) for x,y,z in flatten(read_json(path))};new.update(cells)
        if 'connection' in label:lanes.update(cells)
        sources.append({'path':rel,'sha256':sha,'role':label,'status':'Frozen modeled source, not a runtime receipt'})
    remaining=remaining_profiles(field['seven_by_nine_main_plus_model_skirt_centres_xz'],new)
    patches=[]
    for part in components(remaining):
        x,z=part[len(part)//2]
        patches.append({'remaining_surface_profile_centres':len(part),'centre_bounds_xz':[min(q[0] for q in part),min(q[1] for q in part),max(q[0] for q in part),max(q[1] for q in part)],
            'representative_xz':[x,z],'complete_body_or_plot_authority':False,'status':'Historical dry9x11 surface only; no current body/tree/BE/route/native/art admission'})
    # Literal bank measurements, not an imagined screenshot permission polygon.
    x0,z0,x1,z1=field['study_bounds_xz'];scale=2
    def layer(cells,color):
        # Same literal columns, horizontally run encoded to keep the writer
        # finite; no interpolation over a missing/water/unknown column.
        rows={}
        for x,z in cells:
            if x0<=x<=x1 and z0<=z<=z1:rows.setdefault(z,set()).add(x)
        result=[]
        for z,xs in sorted(rows.items()):
            start=last=None
            for x in sorted(xs):
                if last is None:start=last=x;continue
                if x==last+1:last=x;continue
                result.append(f'<rect x="{(start-x0)*scale}" y="{(z-z0)*scale}" width="{(last-start+1)*scale}" height="2" fill="{color}"/>');start=last=x
            if last is not None:result.append(f'<rect x="{(start-x0)*scale}" y="{(z-z0)*scale}" width="{(last-start+1)*scale}" height="2" fill="{color}"/>')
        return result
    layers=[('<rect width="100%" height="100%" fill="#f7f5ee"/>')]
    for cells,color in ((north['connected_columns_xz'],'#d5dfcd'),(sorted(old),'#456e91'),(sorted(new),'#865a94'),(sorted(lanes),'#d6a543'),(remaining,'#b64138')):
        layers.extend(layer(cells,color))
    svg=(f'<svg xmlns="http://www.w3.org/2000/svg" width="{(x1-x0+1)*scale}" height="{(z1-z0+1)*scale+44}" viewBox="0 0 {(x1-x0+1)*scale} {(z1-z0+1)*scale+44}"><title>Historical measured north-bank source coverage; not a native screenshot</title>'+''.join(layers)+f'<text x="8" y="{(z1-z0+1)*scale+17}" font-size="12">SOURCE PLAN ONLY: green measured bank; blue previous source; violet additions; gold paths; red unallocated profile centres.</text><text x="8" y="{(z1-z0+1)*scale+34}" font-size="12">North up. White includes water / unmeasured / other land. No native placement, art or whole-area completion inferred.</text></svg>').encode()
    document={'format':'awft-north-bank-source-coverage:1','source_sha256':digest(Path(__file__)),
        'historical_checkpoint_id':field['checkpoint_id'],'historical_checkpoint_sha256':field['checkpoint_sha256'],
        'field_source':{'path':FIELD[0],'sha256':FIELD[1]},'north_partition_source':{'path':NORTH[0],'sha256':NORTH[1]},
        'modeled_additions_by_source_group':{'rose_reach':7,'compass_bend':8,'eastern_infills':22,'west_shops':5,'western_ten':10,'quay_courts':6,'shore_profiles':14},
        'all_source_model_count':72,'count_is_not_native_placement_or_art_acceptance':True,
        'historical_profile_centres':len(field['seven_by_nine_main_plus_model_skirt_centres_xz']),
        'remaining_unallocated_profile_centres':len(remaining),'patches':patches,'source_custody':sources,
        'limits':['The finite study rectangle is not the georeferenced circled permission polygon','Missing red centres do not prove a small courtyard or narrow gap is finished','Remaining profiles need actual current full-body, ecology, protected geometry and authored design review','No watchdog/crash snapshot is read or reclassified as a clean checkpoint','Native street walking and first-person artistic acceptance remain unverified'],
        'native_actions':0,'world_writes':0,'seed_or_raw_MCA_in_this_report':False,'reserve_guard':reserve,
        'coverage_svg':{'file':'source-coverage-NOT-NATIVE.svg','sha256':hashlib.sha256(svg).hexdigest(),'bytes':len(svg),'native_image':False}}
    raw=(json.dumps(document,separators=(',',':'))+'\n').encode()
    if len(raw)+len(svg)>4*MIB:raise UserError('Finite coverage output exceeded')
    out=home/'staging'/('north-bank-source-coverage-'+str(time.time_ns()));out.mkdir()
    (out/'coverage.json').open('xb').write(raw);(out/'source-coverage-NOT-NATIVE.svg').open('xb').write(svg)
    return {'folder':str(out),'sha256':digest(out/'coverage.json'),'remaining_surface_profiles':len(remaining),'patches':patches,'native_actions':0}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--home',type=Path,required=True);a=p.parse_args();print(json.dumps(prepare(a.home),indent=2))
