"""Measured western residual coverage; never a subdivision or world operation.

Building counts do not certify a continuous village. This independent reader
compares exact authored main footprints with the saved one-metre north bank,
then reports literal current dry, clear residual pockets for individual design.
"""
from __future__ import annotations
import argparse
from collections import Counter,deque
import hashlib,json,time
from pathlib import Path

from control_room.common import UserError,digest,read_json
from tools.artistic_west_r2_layout import GEOGRAPHY
from tools.artistic_west_r2_study import REJECTED
from tools.artistic_west_r2_frontage import construct as frontage,key
from tools.artistic_salt_petal import construct as florist,HALL
from tools.artistic_tortuga_west_ground import mask_inputs,workspaces,PAIR_MASK
from tools.artistic_north_bank_east import NorthTerrain,GROUND,SOFT,NORTH_SOFT,AIR,preservation
from tools.artistic_bridge_refinement import flatten
from tools.artistic_zipline_catenary import reader_budget
from tools.playtest import guard

MIB=1024**2
GROUND_BUNDLE=('staging/tortuga-west-ground-1793196333621516200/manifest.json','8fc3742481193d448fe54fc1886a466358c7dcd39a028e5994d3258ef649eb45')
WEST10='staging/north-bank-western-ten-1793158436435294000/manifest.json'
WEST5='staging/north-bank-west-five-final-20261028T0200Z/manifest.json'
MANIFEST_PINS={WEST5:'7e8f392abbb71eec606cc7b2158a541d6689744cea22c125571a5214427c4254',
              'staging/artistic-captains-rest-1793170982583234800/manifest.json':'7ef14f65b0bbe56a089360ae065c7bdfef66bc8cc00d4666d60f100f134596fe',
              'staging/tortuga-trade-pair-1793195118561023300/manifest.json':'5b138ed9a5482547303ab0ef9bd2c42d2170d23d98a82ef8099af6483984ef91'}


def actual_geometry(home,manifest_relative,filename):
    """Reservation-only AIR is a mask and can never stand in for geometry."""
    if digest(home/manifest_relative)!=MANIFEST_PINS[manifest_relative]:raise UserError('Exact frozen modeled-geometry manifest required')
    manifest=read_json(home/manifest_relative);path=home/Path(manifest_relative).parent/filename
    if digest(path)!=manifest['files'][filename]['sha256']:raise UserError('Exact actual source geometry required')
    doc=read_json(path)
    if doc.get('reservation_only')or'reservation'in filename.lower():raise UserError('A prospective mask is not physical geometry')
    return flatten(doc)


def components(field):
    unseen=set(field);result=[]
    while unseen:
        q=min(unseen);unseen.remove(q);todo=deque([q]);found={q}
        while todo:
            x,z=todo.popleft()
            for p in((x-1,z),(x+1,z),(x,z-1),(x,z+1)):
                if p in unseen:unseen.remove(p);todo.append(p);found.add(p)
        result.append(found)
    return sorted(result,key=lambda r:(-len(r),min(r)))


def largest_rectangle(field):
    """An empty-patch diagnostic only, never a proposed rectangular house."""
    if not field:return None
    x0=min(x for x,z in field);x1=max(x for x,z in field)
    z0=min(z for x,z in field);z1=max(z for x,z in field)
    heights=[0]*(x1-x0+2);best=(0,None)
    for z in range(z0,z1+1):
        for i,x in enumerate(range(x0,x1+1)):heights[i]=heights[i]+1 if(x,z)in field else 0
        stack=[]
        for i,h in enumerate(heights):
            start=i
            while stack and stack[-1][1]>h:
                left,height=stack.pop();start=left;area=(i-left)*height
                if area>best[0]:best=area,[x0+left,z-height+1,x0+i-1,z]
            if not stack or stack[-1][1]<h:stack.append((start,h))
    return {'area_columns':best[0],'bounds_xz':best[1]}


def main_fields(home,registry):
    fields={};refs=[]
    five=read_json(home/WEST5)
    for name,row in five['lots'].items():
        geometry=actual_geometry(home,WEST5,name+'-PROPOSAL.json')
        cells={(r['support'][0],r['support'][2])for r in row['actual_dry']['actual_dry_columns']}
        if any((x,64,z)not in geometry or key(geometry[x,64,z])in AIR for x,z in cells):
            raise UserError('Original five main/doorstep footprint lacks exact source floor')
        fields['current rejected '+name]=cells
    ten=read_json(home/WEST10)
    for row in ten['lots']:fields['current rejected '+row['id']]={tuple(q)for q in row['main_footprint']}
    p=frontage(registry)
    for name,cells in p.main.items():fields['current W3 '+name]={(x+p.origin[0],z+p.origin[2])for x,z in cells}
    # The literal full hall floor is the main footprint. No bounding rectangle
    # counts the retained porch hollow or its roof-only overhang as built land.
    hall_manifest='staging/artistic-captains-rest-1793170982583234800/manifest.json'
    fields['current Captain’s Rest']={(x,z)for(x,y,z),s in actual_geometry(home,hall_manifest,'captains-rest-PROPOSAL.json').items()if y==63 and key(s)not in AIR}
    p=florist(registry);fields['future Salt & Petal']={(x+p.origin[0],z+p.origin[2])for cells in p.main.values()for x,z in cells}
    pair_manifest='staging/tortuga-trade-pair-1793195118561023300/manifest.json'
    pair={}
    for name in('crooked-iron','sounding-line'):pair.update(actual_geometry(home,pair_manifest,name+'-PROPOSAL.json'))
    fields['future trade pair']={(x,z)for(x,y,z),s in pair.items()if y==63 and key(s)not in AIR}
    for p in workspaces(registry):fields['future '+p.owner]={(x+p.origin[0],z+p.origin[2])for x,z in p.main[p.owner]}
    for rel in(WEST5,WEST10,HALL[0],PAIR_MASK[0]):refs.append({'relative':rel,'sha256':digest(home/rel)})
    return fields,refs


def prepare(home,checkpoint_id,checkpoint_sha):
    home=Path(home).resolve();reserve=guard(8*MIB,32*MIB)
    if home.parent!=Path('D:/A World for Two/staging/world-tests').resolve():raise UserError('Private artistic coverage reader only')
    try:budgets=[reader_budget()]
    except UserError as exc:
        out=home/'staging'/('tortuga-west-coverage-REFUSED-'+str(time.time_ns()));out.mkdir()
        refusal={'checkpoint_requested':checkpoint_id,'checkpoint_sha256_requested':checkpoint_sha,'reader_opened':False,'native_actions':0,'world_writes':0,
                 'reason':str(exc),'guard':reserve,'source_sha256':digest(Path(__file__)),'further_reader_work_performed':False}
        (out/'refusal.json').open('x',encoding='utf-8').write(json.dumps(refusal,separators=(',',':'))+'\n')
        raise UserError(str(exc)+'; immutable refusal preserved '+str(out))from exc
    receipt=read_json(home/'dashboard/settlement/backup-receipt.json')
    if receipt.get('verified')is not True or(receipt.get('id'),receipt.get('sha256'))!=(checkpoint_id,checkpoint_sha)or'stopped'not in receipt.get('scope','').lower():raise UserError('Exact current stopped checkpoint required')
    if digest(home/GEOGRAPHY[0])!=GEOGRAPHY[1]or digest(home/GROUND_BUNDLE[0])!=GROUND_BUNDLE[1]:raise UserError('Preserve original measured bank and frozen ground source')
    geography=read_json(home/GEOGRAPHY[0]);north={tuple(r['xz'])for r in geography['columns']if r['north_connected']}
    registry=read_json(home/'dashboard/settlement/registry.json');keep,forest,refs=mask_inputs(home)
    inherited,heritage=preservation(home,registry)
    fields,footprints=main_fields(home,registry)
    ground=read_json(home/GROUND_BUNDLE[0]);walks={tuple(q)for r in ground['routes']for q in r['cells_xz']}
    current_main=set().union(*(v for k,v in fields.items()if k.startswith('current ')))
    future_main=set().union(*(v for k,v in fields.items()if k.startswith('future ')))
    projected=current_main|future_main
    protected={(x,z)for x,y,z in keep if 62<=y<=86}|inherited|forest|walks
    protected|=future_main
    terrain=NorthTerrain(home,receipt,registry);eligible={};kind_counts=Counter();refused=Counter();started=time.monotonic()
    try:
        for i,(x,z)in enumerate(sorted(north,key=lambda p:(p[0]//16,p[1]//16,p[0],p[1]))):
            col=terrain.column(x,z);kind_counts[col['kind']]+=1
            if(x,z)in protected:refused['current_or_future_authored_mask']+=1;continue
            if col['kind']!='dry'or col['surface_y']not in(62,63):refused['not_literal_low_dry_ground']+=1;continue
            support=terrain.state(x,62,z)
            if support is None or key(support)not in GROUND:refused['no_literal_solid_under_floor63']+=1;continue
            states=[terrain.state(x,y,z)for y in range(63,85)]
            if any(s is None or'waterlogged=true'in s for s in states):refused['unknown_or_waterlogged']+=1;continue
            if key(states[0])not in GROUND|AIR|SOFT|NORTH_SOFT or any(key(s)not in AIR|SOFT|NORTH_SOFT for s in states[1:]):refused['retained_object_or_canopy_in_body']+=1;continue
            if any((x,y,z)in terrain.entities for y in range(62,85)):refused['block_entity']+=1;continue
            eligible[x,z]={'soil_y':col['surface_y'],'ground_state':col['state'],'floor63_before':states[0],'solid_support62':support}
            if i%512==0:
                budgets.append(reader_budget())
                if time.monotonic()-started>120:raise UserError('Finite residual-land reader exceeded120s')
        sources=terrain.snapshot.sources
    finally:terrain.close()
    pockets=components(eligible);patches=[]
    for n,cells in enumerate(pockets):
        # Every listed anchor has its full 7x7 literal dry/clear field; it is
        # not a grid subdivision, automatic lot or silhouette approval.
        anchors=[]
        for x,z in sorted(cells):
            if all((x+dx,z+dz)in cells for dx in range(7)for dz in range(7)):anchors.append((x,z))
        patches.append({'id':n,'columns':len(cells),'bounds_xz':[min(x for x,z in cells),min(z for x,z in cells),max(x for x,z in cells),max(z for x,z in cells)],
                        'largest_all_clear_rectangle_DIAGNOSTIC_ONLY':largest_rectangle(cells),'full_7x7_lower_left_anchors':[list(q)for q in anchors],
                        'requires_individual_irregular_design_and_native_preimage':True})
    data={'format':'awft-western-residual-coverage:1','checkpoint_id':checkpoint_id,'checkpoint_sha256':checkpoint_sha,'source_sha256':digest(Path(__file__)),
          'north_bank_locator':{'relative':GEOGRAPHY[0],'sha256':GEOGRAPHY[1],'historical_only':True},'north_connected_locator_columns':len(north),
          'current_saved_surface_kinds':dict(kind_counts),'exact_current_authored_main_union_columns':len(current_main&north),
          'current_plus_frozen_future_main_union_columns':len(projected&north),'current_main_percent_of_measured_bank':round(100*len(current_main&north)/len(north),3),
          'current_and_future_main_percent_of_measured_bank':round(100*len(projected&north)/len(north),3),
          'footprints':{k:{'columns':len(v),'main_cells_xz':[list(q)for q in sorted(v)]}for k,v in fields.items()},
          'purposeful_two_wide_future_walk_columns':len(walks),'eligible_literal_low_dry_clear_columns':len(eligible),'excluded_column_reasons':dict(refused),
          'residual_pockets':patches,'eligible_columns_READONLY':[[*q,v['soil_y'],v['ground_state'],v['floor63_before'],v['solid_support62']]for q,v in sorted(eligible.items())],
          'source_custody':refs+footprints+heritage,'raw_saved_sources':sources,'reserve_guard':reserve,'reader_peak_RSS_bytes':max(r['owned_reader_rss_bytes']for r in budgets),
          'artistic_brief':'Whole north bank one tightly connected muted Tortuga village; deliberate2–4m lanes and small5–8m courts, not empty neighborhood lawns',
          'status':'INCOMPLETE COVERAGE: residual measured fields require actual linked, individually authored buildings and native images; counts are diagnostics, not artistic acceptance',
          'native_actions':0,'world_writes':0,'demolition_or_inventory_authority':False,'not_a_native_plan':True,
          'limits':['The historical bank locator is only a measured geographic limit, not fresh bank or dry-plot authority','Eligible fields pass literal stopped-save dry/support/body/BE checks only; current native before proof remains required','Current rejected15 are retained and counted, not approved aesthetically or cleared for demolition','Not every residual cell should become a building: true coast clearances, flight, lanes, courts, routes and model envelopes remain required']}
    raw=(json.dumps(data,separators=(',',':'))+'\n').encode()
    if len(raw)>32*MIB:raise UserError('Finite32MiB coverage proposal exceeded')
    out=home/'staging'/('tortuga-west-residual-coverage-'+str(time.time_ns()));out.mkdir();(out/'coverage-READONLY.json').open('xb').write(raw)
    return {'folder':str(out),'sha256':digest(out/'coverage-READONLY.json'),'north_columns':len(north),'current_main_columns':len(current_main&north),'future_plus_current_main_columns':len(projected&north),'eligible_columns':len(eligible),'residual_pockets':len(patches),'pockets_with_7x7_fields':sum(bool(r['full_7x7_lower_left_anchors'])for r in patches),'native_actions':0}


if __name__=='__main__':
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('--home',type=Path,required=True);a.add_argument('--checkpoint-id',required=True);a.add_argument('--checkpoint-sha',required=True);args=a.parse_args();print(json.dumps(prepare(args.home,args.checkpoint_id,args.checkpoint_sha),indent=2))
