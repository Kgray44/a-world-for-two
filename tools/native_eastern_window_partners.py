"""Exact first-three MCW architectural context; no native actions or inventory."""
from __future__ import annotations
import argparse,hashlib,json,time
from pathlib import Path
from control_room.common import UserError,digest,read_json
from tools.artistic_captains_hall import native_payload
from tools.artistic_eastern_urban_custody import canonical
from tools.native_eastern_relocation_r5 import CATALOG,CATALOG_SHA
from tools.artistic_east_tortuga_retrofit import checked
from tools.native_relocation_request import reference,native_proof
from tools.playtest import guard
from tools.settlement_attractions import BackupWorld

MIB=1024**2
SOURCE_ID='20261028T191243Z-6ad3a8'
SOURCE_SHA='0ba7ad2097fb52273a37da6a76d8fc030133b79cd26d81b97531d8d74c2546c2'
GROUPS={
 'pippin':{'id':'eastern22/pippins-net:room:0','source':[(1243,66,-1184),(1243,67,-1184)],'target':[(1230,66,-1184),(1230,67,-1184)],
           'expected':['mcwwindows:dark_oak_plank_window[facing=east,part=bot_l]','mcwwindows:dark_oak_plank_window[facing=east,part=top_l]'],
           'other':{(1230,66,-1185):'mcwwindows:dark_oak_plank_window[facing=east,part=bot_r]',(1230,67,-1185):'mcwwindows:dark_oak_plank_window[facing=east,part=top_r]'}},
 'tea':{'id':'rose-reach/tea:room:1','source':[(1295,70,-1239),(1295,71,-1239),(1296,70,-1239),(1296,71,-1239)],'target':[(1226,66,-1213),(1226,67,-1213),(1227,66,-1213),(1227,67,-1213)],
        'expected':['mcwwindows:dark_oak_plank_window[facing=north,part=bot_r]','mcwwindows:dark_oak_plank_window[facing=north,part=top_r]','mcwwindows:dark_oak_plank_window[facing=north,part=bot_l]','mcwwindows:dark_oak_plank_window[facing=north,part=top_l]'],
        'other':{}}}

def prepare(home):
    home=Path(home).resolve();reserve=guard(MIB,2*MIB);registry=read_json(home/'dashboard/settlement/registry.json');current=read_json(home/'dashboard/settlement/backup-receipt.json')
    cat=checked(home/CATALOG,CATALOG_SHA,2*MIB);source={'id':SOURCE_ID,'sha256':SOURCE_SHA,'verified':True};snapshot=None;observed={}
    try:
        snapshot=BackupWorld(home,source,registry)
        for group in GROUPS.values():
            for q,expected in zip(group['source'],group['expected']):
                if snapshot.state(q)!=expected or q in snapshot.protected:raise UserError('Exact actual saved original non-BE partner differs')
            for q in group['target']:
                if snapshot.state(q)!='minecraft:air' or q in snapshot.protected:raise UserError('Actual6ad target was not BE-free AIR')
                if any(all(r['destination_bounds_xyz'][i]<=q[i]<=r['destination_bounds_xyz'][i+3] for i in range(3)) for r in cat['capsules']):raise UserError('Partner conflicts with a future capsule AIR requirement')
                observed[q]='minecraft:air'
    finally:
        if snapshot:snapshot.close()
    out=home/'staging'/('first3-native-window-partners-'+str(time.time_ns()));out.mkdir();results={}
    for label,g in GROUPS.items():
        targets=dict(zip(g['target'],g['expected']));joined={**targets,**g['other']};files={}
        fields={'before-VERIFY-ONLY.json':{q:observed[q] for q in targets},'partners-DELTA-SOURCE-ONLY.json':targets,'joined-four-VERIFY-ONLY.json':joined}
        for suffix,field in fields.items():
            p=out/(label+'-'+suffix);p.write_bytes(native_payload(registry,field,current['sha256'],'HISTORICAL6ad input / FORECAST native joined window ONLY; fresh actual before + normal shapes required, no inventory'));files[suffix]=reference(home,p)
        results[label]={'capsule_id':g['id'],'files':files,'source_positions':list(map(list,g['source'])),'target_positions':list(map(list,g['target'])),
            'source_actual6ad_states':g['expected'],'future_capsule_intersections':0,'BE_and_inventory_targets':0,
            'native_derivation':'Pinned MCW2.4.2 ConnectedWindow.updateShape→WindowState recomputes native neighbor parts; four expected fields exactly translate the actual original quad. This is not a native after-observation.',
            'gate':'Source DELTA remains forbidden. Root fresh native AIR proof, admitted normal placement, normal settle and joined-four strict verification; Pippin remains quarantined until separate actual fulltag/allslot audit/current custody record'}
    record={'format':'awft-first3-window-context-source:1','historical_actual_backup_id':SOURCE_ID,'historical_actual_backup_sha256':SOURCE_SHA,'admission_checkpoint_sha256':current['sha256'],
        'catalog_sha256':CATALOG_SHA,'groups':results,'bent_needle_external_context':[],'source_sha256':digest(Path(__file__)),'native_actions':0,'construction_forbidden':True,'reserve_guard':reserve}
    p=out/'manifest.json';p.write_bytes(canonical(record)+b'\n');return {'folder':str(out),'manifest_sha256':digest(p),'groups':results,'native_actions':0}

def admit(home,manifest_path,manifest_sha,group,before_proof,before_sha):
    home=Path(home).resolve();guard(MIB,MIB);doc=checked(Path(manifest_path),manifest_sha,MIB);g=doc['groups'][group]
    before=g['files']['before-VERIFY-ONLY.json'];after=g['files']['partners-DELTA-SOURCE-ONLY.json'];native_proof(home,before_proof,before_sha,before['sha256'],len(g['target_positions']))
    raw=checked(home/after['path'],after['sha256'],MIB)
    if raw.get('block_entities'):raise UserError('No BE or inventory target allowed')
    current=read_json(home/'dashboard/settlement/backup-receipt.json')
    if raw['backup_sha256']!=current['sha256']:raise UserError('Actual current checkpoint binding required')
    raw.update(verification_only=False,construction_forbidden=False,name='ADMITTED exact non-BE MCW architectural partners after real native AIR proof')
    raw['source_before_proof']=reference(home,Path(before_proof));out=home/'staging'/('admitted-window-partners-'+str(time.time_ns()));out.mkdir();p=out/'DELTA.json';p.write_bytes(canonical(raw)+b'\n')
    return {'folder':str(out),'path':str(p),'sha256':digest(p),'native_actions':0}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--home',type=Path,required=True);a=p.parse_args();print(json.dumps(prepare(a.home),indent=2))
