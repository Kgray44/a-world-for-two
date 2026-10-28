"""Bounded saved dry infill study, not houses, art acceptance or world authority.

The western waterline and bridge arm belong to this lane. Actual source fields
and the cable's reserved three-dimensional body take precedence over empty map
pixels. Each failed field is retained, never widened into fabricated dry land.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from control_room.common import UserError,digest,utcnow
from tools.artistic_bridge_refinement import flatten
from tools.artistic_north_bank_east import NorthTerrain,dry_footprint,preservation
from tools.artistic_north_bank_west import ZIPLINE_MASK,ZIPLINE_MASK_SHA
from tools.artistic_quay_prototype import WEST,WEST_SHA,KINDS,bounded,context,member,write_bundle
from tools.artistic_west_quay_streets import SOFT
from tools.playtest import guard
from tools.settlement_attractions import base

STREET='staging/west-crooked-street-furniture-0d7-20261028T0306Z'
STREET_SHA='f077698ff67446d37fa81e4e593e42f4d1aec08f1aa8c15f8315a17c39be38a9'
# Deliberate differently sized/stepped programs, not a repeated subdivision.
LOTS=(
 ('saltmaker',(995,-1275),(8,9),'chamfer','A low salt-and-copper work wing with a taller seaward watch room'),
 ('sailmaker',(1004,-1262),(7,8),'L','A narrow loft and irregular covered sail court'),
 ('ropewalk-home',(1019,-1243),(7,8),'chamfer','A small hanging upper bay with a side workshop entrance'),
 ('ferryman',(1038,-1240),(5,8),'notch','A thin stepped wharf cottage with deeply modeled end gable'),
 ('apothecary',(1052,-1241),(8,8),'L','A curved glazed herb shop and sheltered rear household'),
 ('baker',(1063,-1240),(8,8),'chamfer','A warm bakery with a projecting oven wing and eaved service court'),
 ('stargazer',(1094,-1239),(8,8),'notch','A small mariner home with a carved upper chart alcove'),
 ('weaver',(1111,-1238),(9,9),'L','A colored textile court and real wrapping sleeping gallery'),
 ('mariner',(1136,-1220),(8,8),'chamfer','A paired-pitch home following the narrow bridge-arm lane'),
 ('bookbinder',(1151,-1218),(8,8),'notch','A close-set bookseller with a recessed porch and upper reading oriel'),
 ('soup-kitchen',(1165,-1222),(8,8),'L','A small public galley, carved street porch and private loft'),
 ('fish-curer',(1107,-1268),(8,10),'chamfer','A waters-edge smokehouse and small sheltered merchant room'),
)


def main_cells(origin,size,shape):
    ox,oz=origin;w,d=size;cells={(x,z)for x in range(w)for z in range(d)}
    if shape=='chamfer':cells-={(0,0),(w-1,0),(0,d-1),(w-1,d-1)}
    elif shape=='L':cells-={(x,z)for x in range(w-3,w)for z in range(d-3,d)}
    elif shape=='notch':cells-={(0,z)for z in range(2,5)}
    else:raise UserError('Explicit original silhouette required')
    return {(ox+x,oz+z)for x,z in cells}


def prepare(home,output):
    reserve=guard(2*1024**2,8*1024**2);home,output,current,registry=context(home,output)
    protected,old_sources=preservation(home,registry);urban={}
    source=bounded(home/WEST/'manifest.json')
    if digest(home/WEST/'manifest.json')!=WEST_SHA:raise UserError('Preserve exact current five source shops')
    for k in KINDS:urban.update(flatten(member(home/WEST,source,k+'-PROPOSAL.json')))
    street=bounded(home/STREET/'manifest.json')
    if digest(home/STREET/'manifest.json')!=STREET_SHA:raise UserError('Preserve exact connected street source')
    urban.update(flatten(member(home/STREET,street,'street-and-furniture-PROPOSAL.json')))
    urban.update(flatten(member(home/STREET,street,'future-walk-furniture-reservation-ONLY.json')))
    zipline_path=home/ZIPLINE_MASK
    if digest(zipline_path)!=ZIPLINE_MASK_SHA:raise UserError('Preserve exact future west cable body')
    cable=set(flatten(bounded(zipline_path)));urban_cols={(x,z)for x,y,z in urban}
    terrain=NorthTerrain(home,current,registry);lots=[];good={};sources=[]
    try:
        for name,origin,size,shape,composition in LOTS:
            cells=main_cells(origin,size,shape);row={'id':name,'origin_xz':list(origin),'size':list(size),'silhouette':shape,'composition':composition,'status':'UNQUALIFIED'}
            try:
                if any(x>1216 for x,z in cells):raise UserError('Retain the agreed eastern source boundary')
                dry=dry_footprint(terrain,cells,protected|urban_cols,max_relief=2);floor=dry['floor_y']
                #14-high conservative envelope is a site-design study, not the
                # actual collision hull of an unbuilt roof or proof no alternative fits.
                skirt={(x+dx,z+dz)for x,z in cells for dx,dz in((0,0),(-1,0),(1,0),(0,-1),(0,1))}
                before={}
                for x,z in skirt:
                    for y in range(floor,floor+14):
                        q=x,y,z
                        if q in urban or q in cable or(x,z)in protected:raise UserError('Keep current authored routes/architecture or real future frame/cable envelope: '+str(q))
                        value=terrain.state(*q)
                        if value is None or base(value)not in SOFT or 'waterlogged=true'in value or q in terrain.entities:raise UserError('Preserve actual tree/water/BE/object in conservative future field: '+str((q,value)))
                        before[q]=value
                row.update(status='EXACT DRY SITE FIELD ONLY',floor_y=floor,main_cells_xz=[list(q)for q in sorted(cells)],dry=dry,
                           actual_clear_envelope_cells=len(before),native_or_artistic_acceptance=False,house_or_street_geometry_authored=False)
                good[name]=before
            except UserError as error:row.update(status='REFUSED conservative candidate field',reason=str(error),alternative_house_shapes_or_sites_not_ruled_out=True)
            lots.append(row);terrain.check()
        sources=terrain.snapshot.sources.copy()
    finally:terrain.close()
    if bounded(home/'dashboard/settlement/backup-receipt.json').get('sha256')!=current['sha256']:raise UserError('Checkpoint advanced during source study')
    return write_bundle(output,{}, {'format':'awft-west-dry-infill-study:1','created':utcnow(),'source_sha256':digest(Path(__file__)),
        'checkpoint_id':current['id'],'checkpoint_sha256':current['sha256'],'lots':lots,'accepted_old_sources':old_sources,'street_source_sha256':STREET_SHA,
        'prospective_cable_sha256':ZIPLINE_MASK_SHA,'saved_sources':sources,'native_actions':0,'world_writes':0,'construction_forbidden':True,'storage_guard':reserve,
        'scope':'Only exact dry support/full-air conservative design fields. Every unique complete3D house/interior, route connection, nativebefore and actual art remains to author/review; no repeated house template or water platform is admitted.'})


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('home','output'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();print(json.dumps(prepare(a.home,a.output),indent=2))
