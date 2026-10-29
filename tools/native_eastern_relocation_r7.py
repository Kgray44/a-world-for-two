"""Exact additive98 request producer, real typed inventory roles, no installation."""
from __future__ import annotations
import argparse,hashlib,json,time,tomllib,zipfile
from pathlib import Path
import nbtlib
from control_room.common import UserError,read_json,utcnow,digest
from tools.artistic_east_tortuga_retrofit import checked
from tools.artistic_east_tortuga_retrofit import with_exact_be_tags
from tools.artistic_bridge_refinement import flatten
from tools.artistic_captains_hall import native_payload
from tools.artistic_eastern_urban_custody import CHECKPOINT_SHA,canonical
from tools.artistic_maritime_depth import admit_owner
from tools.native_eastern_relocation import CLASSES,LAYOUT,checked_row,prepare_geometry,transaction
from tools.native_eastern_relocation_r4 import seal as seal_r4
from tools.native_relocation_request import class_hash,reference,native_proof
from tools.playtest import guard

MIB=1024**2
CATALOG_SHA='879c7a3894df08e541c083b4a0a8bfb75bc7fd6b3017e8898befe4c7ceefaf14'
CATALOG='staging/eastern-final-floor-catalog-1793225720648710600/approved98-capsules-PRIVATE.json'
TOOLBOX='compass-bend/shared-repair-court:room:0'
CREATE='create-1.21.1-6.0.10.jar'
CREATE_SHA='ef87fe5709f1ba1f5b8bb20a2925b5afb4669e178fd6d8bf10c167759eefe37a'

def geometry(home,ident):return prepare_geometry(home,Path(home)/CATALOG,CATALOG_SHA,ident)

def audit_geometry(home,ident):
    """Historical expected definitions for READ-ONLY after-move inspection only.

    These are explicitly not observations of a current source/destination. The
    native audit obtains actual states/full tags itself and cannot execute clone.
    """
    home=Path(home).resolve();reserve=guard(MIB,2*MIB);catalog=checked(home/CATALOG,CATALOG_SHA,2*MIB);row=checked_row(catalog,ident)
    receipt=read_json(home/'dashboard/settlement/backup-receipt.json');registry=read_json(home/'dashboard/settlement/registry.json');admit_owner(home,read_json(home/'dashboard/artistic-owner.json'),receipt,receipt['id'],receipt['sha256'])
    original=checked(home/row['source_original']['path'],row['source_original']['sha256'],MIB);support=checked(home/row['supports_original']['path'],row['supports_original']['sha256'],MIB)
    field=flatten(original);a,b=row['source_bounds_xyz'],row['destination_bounds_xyz']
    for prep in row['source_cover_preparations']:field[tuple(prep['position'])]='minecraft:air'
    tags={tuple(v['pos']):nbtlib.parse_nbt(v['nbt']) for v in original['block_entities']}
    from tools.artistic_eastern_move_blueprint import cells
    fields={'source-prepared-FUTURE-VERIFY-ONLY.json':(field,tags),'destination-empty-FUTURE-VERIFY-ONLY.json':({q:'minecraft:air' for q in cells(b)},{}),'retained-supports-VERIFY-ONLY.json':(flatten(support),{})}
    out=home/'staging'/('quarantined-capsule-audit-definitions-'+str(time.time_ns()));out.mkdir();files={}
    for name,(states,objects) in fields.items():
        p=out/name;p.write_bytes(with_exact_be_tags(native_payload(registry,states,receipt['sha256'],'HISTORICAL expected identity definitions ONLY for read-only quarantined custody audit; NOT actual before/current source'),objects));files[name]=reference(home,p)
    gm={'format':'awft-approved-capsule-geometry:2','capsule_id':ident,'catalog':reference(home,home/CATALOG),'checkpoint_id':receipt['id'],'checkpoint_sha256':receipt['sha256'],
        'operation_role':'READ-ONLY QUARANTINE AUDIT; historical expected room definitions, no current-source-before claim','original_source':row['source_original'],'original_destination':row['destination_original'],
        'files':files,'current_native_before_proved':False,'construction_forbidden':True,'native_actions':0,'reserve_guard':reserve}
    p=out/'manifest.json';p.write_bytes(canonical(gm)+b'\n');return {'folder':str(out),'manifest_sha256':digest(p),'native_actions':0}

def bind(home,geometry_manifest,geometry_sha,bridge_jar,review,review_sha,proofs,*,action='inspect',inspection=None,inspection_sha=None,toolbox_audit=None,toolbox_audit_sha=None,resolution_review=None,resolution_review_sha=None,quarantined_terminal=None,quarantined_terminal_sha=None,native_custody_audit=None,native_custody_audit_sha=None,custody_review=None,custody_review_sha=None):
    home=Path(home).resolve();reserve=guard(MIB,4*MIB);catalog=checked(home/CATALOG,CATALOG_SHA,2*MIB);gm=checked(Path(geometry_manifest),geometry_sha,MIB)
    ident=gm['capsule_id'];row=checked_row(catalog,ident)
    if gm['catalog']['sha256']!=CATALOG_SHA:raise UserError('Current geometry belongs to a different catalogue')
    receipt=read_json(home/'dashboard/settlement/backup-receipt.json');admit_owner(home,read_json(home/'dashboard/artistic-owner.json'),receipt,receipt['id'],receipt['sha256'])
    if gm['checkpoint_sha256']!=receipt['sha256']:raise UserError('Actual current checkpoint geometry required')
    approved=checked(Path(review),review_sha,65536)
    if approved.get('format')!='awft-owner-city-plan-review:1' or approved.get('approved') is not True or approved.get('eastern_layout_sha256')!=LAYOUT[1] or 'approved-north-bank-city-rebuild' not in approved.get('allowed_operations',[]):raise UserError('Actual city-map approval required')
    active=read_json(home/'packwiz/active.json');installed=read_json(home/'server/installed.json')
    if active['version']!=installed['pack_version'] or active['pack_sha256']!=installed['pack_sha256']:raise UserError('Actual installed candidate differs')
    games=list((home/'server/libraries/net/minecraft/server').rglob('*-srg.jar'))
    if len(games)!=1:raise UserError('One actual base game archive required')
    game=games[0];bridge_jar=Path(bridge_jar)
    with zipfile.ZipFile(bridge_jar) as z:metadata=tomllib.loads(z.read('META-INF/neoforge.mods.toml').decode());bridge=next(r['version'] for r in metadata['mods'] if r['modId']=='awft_control_bridge')
    registry=read_json(home/'dashboard/settlement/registry.json');req={'format':'awft-native-approved-capsule-relocation:2','created':utcnow(),
        'candidate_version':active['version'],'bridge_version':bridge,'pack_sha256':active['pack_sha256'],'capsule_id':ident,
        'native_class_sha256':class_hash(bridge_jar,'worldfortwo.bridge.NativeRelocationSupport'),'ledger_class_sha256':class_hash(bridge_jar,'worldfortwo.bridge.NativeRelocationSupport$Ledger'),
        'catalog_class_sha256':class_hash(bridge_jar,'worldfortwo.bridge.NativeRelocationSupport$Capsules'),'toolbox_custody_class_sha256':class_hash(bridge_jar,'worldfortwo.bridge.NativeToolboxCustody'),
        'quarantined_evidence_class_sha256':class_hash(bridge_jar,'worldfortwo.bridge.NativeRelocationSupport$Quarantined'),
        'vanilla_clone_class_sha256':class_hash(game,'net.minecraft.server.commands.CloneCommands'),'seed':registry['seed'],'world_path':registry['world_path'],
        'backup_sha256':receipt['sha256'],'current_backup':reference(home,home/'dashboard/settlement/backup-receipt.json'),
        'baseline_capture_backup_sha256':CHECKPOINT_SHA,'catalog':reference(home,home/CATALOG),'original_source':row['source_original'],'original_destination':row['destination_original'],
        'owner_city_plan_review':reference(home,Path(review)),'eastern_layout_sha256':LAYOUT[1],'transaction_id':transaction(home,ident,row['translation_xyz'])}
    folder=Path(geometry_manifest).resolve().parent
    names=('source-prepared-FUTURE-VERIFY-ONLY.json','destination-empty-FUTURE-VERIFY-ONLY.json','retained-supports-VERIFY-ONLY.json')
    for key,name,count in zip(('source_geometry','destination_geometry','destination_supports'),names,(row['cells'],row['cells'],row['support_cells'])):
        rec=gm['files'][name];member=home/rec['path'];checked(member,rec['sha256'],MIB);req[key]=reference(home,member)
        if action not in ('inspect-moved','inspect-quarantined','record-conserved'):
            path,sha=proofs[key];req[{'source_geometry':'source_native_verify','destination_geometry':'destination_native_verify','destination_supports':'supports_native_verify'}[key]]=native_proof(home,path,sha,rec['sha256'],count)
    plan=read_json(home/req['source_geometry']['path']);pins=[]
    for r in plan['block_entities']:
        data=nbtlib.parse_nbt(r['nbt']);kind=str(data['id'])
        if kind=='create:toolbox':archive,klass,container=CREATE,'com.simibubi.create.content.equipment.toolbox.ToolboxBlockEntity',False
        elif kind in CLASSES:archive,klass,container=CLASSES[kind]
        else:raise UserError('Unknown actual native inventory role')
        jar=game if archive=='GAME' else home/'server/mods'/archive
        pin={'source_position':r['pos'],'BE_id':kind,'class':klass,'class_sha256':class_hash(jar,klass),'Container':container}
        if kind=='create:toolbox':pin['IItemHandler']=True
        pins.append(pin)
    req['BE_class_pins']=pins
    if ident==TOOLBOX:
        if toolbox_audit is None:raise UserError('Toolbox requires a complete current saved-player audit and real native gates')
        audit=checked(Path(toolbox_audit),toolbox_audit_sha,65536)
        if audit.get('format')!='awft-toolbox-saved-player-custody:1' or audit.get('checkpoint_sha256')!=receipt['sha256'] or audit.get('matching_saved_links')!=0:raise UserError('Exact current saved toolbox/profile authority required')
        req['toolbox_saved_player_custody']=reference(home,Path(toolbox_audit));create=home/'server/mods'/CREATE
        if digest(create)!=CREATE_SHA:raise UserError('Exact pinned Create artifact required')
        nf=home/f"server/libraries/net/neoforged/neoforge/{installed['neoforge']}/neoforge-{installed['neoforge']}-universal.jar"
        classes={name:class_hash(create,'com.simibubi.create.content.equipment.toolbox.'+name) for name in ('ToolboxBlockEntity','ToolboxInventory','ToolboxBlock','ToolboxHandler')}
        api={'com.simibubi.create.content.equipment.toolbox.'+name:sha for name,sha in classes.items()}
        for name in ('ItemStackHandler','IItemHandler'):api['net.neoforged.neoforge.items.'+name]=class_hash(nf,'net.neoforged.neoforge.items.'+name)
        api['net.createmod.catnip.nbt.NBTHelper']=class_hash(create,'net.createmod.catnip.nbt.NBTHelper');req['toolbox_api_class_sha256']=api
    elif toolbox_audit is not None:raise UserError('Foreign toolbox authority on a different room')
    if action=='move':
        inspected=checked(Path(inspection),inspection_sha,MIB)
        if inspected.get('operation')!='inspect' or inspected.get('cleanup_passed') is not True or inspected.get('clone_invoked') is not False or inspected.get('capsule_id')!=ident or inspected.get('status')!='inspected exact current native source/destination; no move':raise UserError('Actual current clean exact native inspection required')
        req['native_inspect']=reference(home,Path(inspection))
    elif action in ('inspect-quarantined','record-conserved'):
        if not gm.get('operation_role','').startswith('READ-ONLY QUARANTINE AUDIT'):raise UserError('Explicit historical-definition audit role required; no fake current source proof')
        prior=checked(Path(quarantined_terminal),quarantined_terminal_sha,MIB)
        if prior.get('operation')!='move' or prior.get('clone_invoked') is not True or prior.get('failed') is not True or prior.get('quarantine') is not True or prior.get('cleanup_passed') is not True or prior.get('transaction_id')!=req['transaction_id']:raise UserError('Exact actually invoked failed marked move is required for read-only audit')
        req['quarantined_move_terminal']=reference(home,Path(quarantined_terminal))
        if action=='record-conserved':
            actual=checked(Path(native_custody_audit),native_custody_audit_sha,MIB);permission=checked(Path(custody_review),custody_review_sha,65536)
            if actual.get('operation')!='inspect-quarantined' or actual.get('native_content_conservation_passed') is not True or actual.get('source_AIR_passed') is not True or actual.get('destination_state_differences') or actual.get('destination_survival_failures'):raise UserError('Actual independent complete native custody must pass first')
            if permission.get('format')!='awft-explicit-independent-custody-review:1' or permission.get('approved') is not True or permission.get('allow_record_current_custody_only') is not True or permission.get('transaction_id')!=req['transaction_id']:raise UserError('Separate actual Root review is required; producer cannot approve')
            req['native_custody_audit']=reference(home,Path(native_custody_audit));req['custody_resolution_review']=reference(home,Path(custody_review))
    elif action not in ('inspect','inspect-moved'):raise UserError('Only typed inspect/move/inspect-moved/inspect-quarantined')
    raw=canonical(req)+b'\n';sha=hashlib.sha256(raw).hexdigest();out=home/'staging'/('relocation-'+sha[:16]+'-R5-PRESEAL-'+str(time.time_ns()));out.mkdir();(out/'request.json').write_bytes(raw)
    result=seal_r4(home,out/'request.json',sha,bridge_jar,review=resolution_review,review_sha=resolution_review_sha)
    result.update(catalog_sha256=CATALOG_SHA,source_sha256=digest(Path(__file__)),reserve_guard=reserve);return result

_bind_without_window_pin=bind
def bind(home,*args,**kwargs):
    prior=_bind_without_window_pin(home,*args,**kwargs)
    bridge=kwargs.get('bridge_jar',args[2] if len(args)>2 else None)
    if bridge is None:raise UserError('Exact actual bridge archive required')
    from tools.native_eastern_relocation_r6 import seal
    return seal(home,Path(prior['folder'])/'request.json',prior['request_sha256'],bridge)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--home',type=Path,required=True);p.add_argument('--geometry',required=True);a=p.parse_args();print(json.dumps(geometry(a.home,a.geometry),indent=2))
