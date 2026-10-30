"""Finite ordinary pre-MOVE supports from the already approved39 structures.

No native calls, invented beams, inventory changes or catalogue changes. Unknown,
human/stock, own-source and future-room conflicts remain explicit dependencies.
"""
from __future__ import annotations
import argparse,json,time
from pathlib import Path
from control_room.common import UserError,digest,read_json
from tools.artistic_east_tortuga_retrofit import checked
from tools.artistic_eastern_urban_custody import canonical
from tools.artistic_bridge_refinement import flatten
from tools.artistic_captains_hall import native_payload
from tools.native_relocation_request import reference
from tools.native_eastern_relocation_r7 import CATALOG,CATALOG_SHA
from tools.eastern_city_execute import ARCH,ARCH_SHA,PACKET,PACKET_SHA
from tools.playtest import guard
from tools.settlement_attractions import properties

MIB=1024**2
VEC={'north':(0,0,-1),'south':(0,0,1),'east':(1,0,0),'west':(-1,0,0)}
AIR={'minecraft:air','minecraft:cave_air','minecraft:void_air'}
def inside(q,b):return all(b[k]<=q[k]<=b[k+3]for k in range(3))

def outside_backings(source,translation,bounds,explicit):
    """Only copied fixtures need pre-MOVE supports, never future props over AIR."""
    needed={}
    for p,state in source.items():
        ident=state.split('[',1)[0]
        if ident in AIR:continue
        q=tuple(p[k]+translation[k]for k in range(3));props=properties(state);supports=set(explicit.get(q,set()))
        if ident=='minecraft:lantern':supports.add((q[0],q[1]+(1 if props.get('hanging')=='true'else-1),q[2]))
        elif ident.startswith('minecraft:')and ident.endswith('_wall_sign')and props.get('facing')in VEC:
            v=VEC[props['facing']];supports.add(tuple(q[k]-v[k]for k in range(3)))
        for support in supports:
            if not inside(support,bounds):needed.setdefault(support,[]).append({'fixture_position':list(q),'copied_fixture_state':state,'source_support_position':[support[k]-translation[k]for k in range(3)]})
    return needed

def ordered_dependencies(base,records):
    remaining={k:set(v)for k,v in base.items()}
    for r in records:remaining[r['capsule_id']].update(r['required_conserved_source_or_destination_ids'])
    result=[]
    while remaining:
        ready=sorted(k for k,v in remaining.items()if not v)
        if not ready:break
        for k in ready:result.append(k);remaining.pop(k)
        for v in remaining.values():v.difference_update(ready)
    return result,{k:sorted(v)for k,v in remaining.items()}

def prepare(home):
    home=Path(home).resolve();reserve=guard(2*MIB,8*MIB);cat=checked(home/CATALOG,CATALOG_SHA,2*MIB);index=checked(home/ARCH,ARCH_SHA,2*MIB)
    registry=read_json(home/'dashboard/settlement/registry.json');cp=read_json(home/'dashboard/settlement/backup-receipt.json');human=read_json(home/'dashboard/human-construction-session.json',{}).get('human_regions',[])
    rows={r['id']:r for r in cat['capsules']};bybuilding={r['id']:r for r in index['compounds']};records=[];out=home/'staging'/('eastern-approved-outside-backings-'+str(time.time_ns()));out.mkdir()
    global_BE=set();global_fixed={};documents={}
    for building,br in bybuilding.items():
        rr=br['files']['SOURCE-ONLY'];doc=checked(home/rr['path'],rr['sha256'],8*MIB);documents[building]=doc
        global_BE.update(tuple(v.get('position',v.get('pos',[])))for v in doc.get('new_tags_ONLY',[]))
        for value in doc.get('preserved_fixed_native_states',doc.get('fixed_native_states',[])):
            q=tuple(value['position']);state=value['state']
            if q in global_fixed and global_fixed[q]!=state:raise UserError('Conflicting final fixed native states')
            global_fixed[q]=state
    for r in rows.values():
        d=r['translation_xyz'];doc=checked(home/r['source_original']['path'],r['source_original']['sha256'],MIB)
        global_BE.update(tuple(tag['pos'][k]+d[k]for k in range(3))for tag in doc['block_entities'])
    for building,br in bybuilding.items():
        rr=br['files']['SOURCE-ONLY'];doc=documents[building];full={tuple(q[:3]):q[3]for q in doc['complete_expected_state_context_ONLY']};origin=doc['origin']
        cr=br['files']['actual-current-blockstates-VERIFY-ONLY'];historical=flatten(checked(home/cr['path'],cr['sha256'],8*MIB))
        explicit={}
        for point,back in doc.get('supports',[]):
            q=tuple(point[k]+origin[k]for k in range(3));b=tuple(back[k]+origin[k]for k in range(3));explicit.setdefault(q,set()).add(b)
        for r in rows.values():
            if r['destination_building']!=building:continue
            src=checked(home/r['source_original']['path'],r['source_original']['sha256'],MIB);d=r['translation_xyz'];source=flatten(src);b=r['destination_bounds_xyz'];needed=outside_backings(source,d,b,explicit)
            if not needed:continue
            targets={};before={};retained={};entries=[];requires=set();holds=[]
            for q,fixtures in sorted(needed.items()):
                desired=full.get(q);entry={'position':list(q),'approved_final_state':desired,'fixtures':fixtures,'historical6ad_state':historical.get(q),'holds':[]}
                if desired is None or desired.startswith(('minecraft:air','minecraft:cave_air','minecraft:void_air','minecraft:water','minecraft:lava')):entry['holds'].append('No approved solid backing at this point; do not invent one')
                if q in global_BE:entry['holds'].append('Actual/future inventory or newBE point; no structural overwrite')
                if q in global_fixed:
                    if desired!=global_fixed[q]:entry['holds'].append('Literal retained furnishing/function state must not be changed')
                    else:entry['retained_fixed_state_verify_only']=True
                if any(inside(q,x['bounds_xyz'])for x in human):entry['holds'].append('Human zipline/tube reservation wins')
                for owner,other in rows.items():
                    if inside(q,other['source_bounds_xyz']):
                        if owner==r['id']:entry['holds'].append('Own source will be cleared by MOVE; this support cannot survive the native operation')
                        else:requires.add(owner)
                    if owner!=r['id']and inside(q,other['destination_bounds_xyz']):
                        requires.add(owner);entry.setdefault('requires_other_destination_custody_first',[]).append(owner)
                if historical.get(q)is None:entry['holds'].append('No historical before at this point; current native observation required')
                if entry['holds']:holds.append(entry)
                elif entry.get('retained_fixed_state_verify_only'):retained[q]=desired
                else:targets[q]=desired;before[q]=historical[q]
                entries.append(entry)
            files={}
            if targets:
                for label,field in [('historical-before-EXPECTED-ONLY',before),('approved-backing-SOURCE-DELTA',targets),('approved-backing-after-VERIFY-ONLY',targets)]:
                    p=out/(f'{len(records):03d}-'+label+'.json');p.write_bytes(native_payload(registry,field,cp['sha256'],'FORBIDDEN exact approved final outside-capsule backing '+label+'; fresh Native before and current ownership required'));files[label]=reference(home,p)
            if retained:
                p=out/(f'{len(records):03d}-retained-fixed-backing-VERIFY-ONLY.json');p.write_bytes(native_payload(registry,retained,cp['sha256'],'Read-only retained literal fixture support; no replacement authority'));files['retained-fixed-backing-VERIFY-ONLY']=reference(home,p)
            records.append({'capsule_id':r['id'],'building_id':building,'approved_source':rr,'backings':entries,'files':files,'required_conserved_source_or_destination_ids':sorted(requires),
                'holds':holds,'native_actions':0,'construction_forbidden':True,'gates':['Never replay any existing intent/quarantine; Bent/Pippin current repair is a separate explicit Root action',
                'Every affected original full source captured/conserved; any intersected other future destination mustalreadybeconserved',
                'No preservedBE/functionalfixture/human-route overwrite; exact fresh current native before',
                'Parent-admit ordinary backing beforeMOVE; strict Nativeafter; real fixture stability/full tags remain mandatory']})
    manifest=checked(home/PACKET,PACKET_SHA,2*MIB);pipeline=checked((home/PACKET).parent/'pipeline-SOURCE-ONLY.json',manifest['pipeline_sha256'],16*MIB)
    order,cycles=ordered_dependencies({r['capsule_id']:r['required_preceding_native_captures']for r in pipeline['room_assessments']},records)
    payload={'format':'awft-approved-eastern-outside-capsule-backing-source:1','catalog_sha256':CATALOG_SHA,'architecture_index_sha256':ARCH_SHA,'checkpoint_sha256':cp['sha256'],
        'records':records,'source_sha256':digest(Path(__file__)),'ordinary_target_cells':sum(len(flatten(read_json(home/r['files']['approved-backing-SOURCE-DELTA']['path'])))for r in records if 'approved-backing-SOURCE-DELTA'in r['files']),
        'retained_fixed_verify_cells':sum(len(flatten(read_json(home/r['files']['retained-fixed-backing-VERIFY-ONLY']['path'])))for r in records if 'retained-fixed-backing-VERIFY-ONLY'in r['files']),
        'topological_with_backing_custody':order,'additional_dependency_cycle_holds':cycles,
        'explicit_hold_points':sum(len(r['holds'])for r in records),'no_invented_geometry_or_NBT':True,'native_actions':0,'construction_forbidden':True,'reserve_guard':reserve}
    p=out/'backing-protocol-SOURCE-ONLY.json';p.write_bytes(canonical(payload)+b'\n');return {'folder':str(out),'sha256':digest(p),'rooms':len(records),'cells':payload['ordinary_target_cells'],'retained_read_only':payload['retained_fixed_verify_cells'],'holds':payload['explicit_hold_points'],'dependency_cycles':len(cycles),'native_actions':0}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--home',type=Path,required=True);a=p.parse_args();print(json.dumps(prepare(a.home),indent=2))
