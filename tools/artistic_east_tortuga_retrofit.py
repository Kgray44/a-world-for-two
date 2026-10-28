"""One custody-bound eastern Tortuga correction; never a 37-house repaint.

Preserves actual furniture, inventories, later progress and all walking bodies.
Only exact unchanged, explicitly owned non-BE shell cells can be replaced.
Private typed-NBT evidence and construction-forbidden native plans stay on D:.
"""
from __future__ import annotations

import argparse
from collections import Counter, deque
import hashlib
import json
from pathlib import Path
import time

from control_room.common import UserError, digest, read_json
from tools.artistic_bridge_refinement import flatten
from tools.artistic_captains_hall import native_payload
from tools.artistic_maritime_depth import admit_owner, key
from tools.artistic_materials import require_material_rule
from tools.artistic_north_rebuild_custody import decoded_chunk, typed
from tools.artistic_north_bank_east import preservation
from tools.artistic_spawn_plaza import state
from tools.artistic_tortuga_pair import TradeHouse, hip
from tools.playtest import guard
from tools.settlement_attractions import BackupWorld


MIB=1024**2
AIR='minecraft:air'
VOID={AIR,'minecraft:cave_air','minecraft:void_air'}
ID='compass-bend/seabird-ledger'
ORIGIN=(1233,64,-1211)
LEDGER='staging/north52-custody-READONLY-1793169553762422700'
LEDGER_SHA='8f547a983c4894f4b9102da7315772b203842a3da91766c217d9243c95531d5d'
SOURCE='staging/north-bank-compass-bend-1793156177505399400'
SOURCE_MANIFEST_SHA='c39bc9304e532798f9a18a4caf950b2500c3e35b2ea391175b7758ebe1a3e6fa'
SOURCE_SHA='cc83762b5e3e8476dc2e26ade1d84c21bca545e937d64938cbf0f43afa393b1e'
SOURCE_BEFORE_SHA='a3e85f50cc0e0b785b230d9f7dcd7eea4dd812b02bb16aa29821a1b898e92783'
CELL_SHA='7023ff91fa2328a8da65e3f2a231c8c609994100e65634ab8a52ad42fa21dc99'
BE_SHA='307b9e73f130f52ada5bf4ac236346aa7bdeb940b5a6b66d884c9eeb85d97718'
EXACT='SOURCE_EXACT_UNCHANGED_GEOMETRY'
JOIN='SAME_ID_STATE_DELTA_NATIVE_SHAPE_OR_HUMAN_ORIGIN_UNPROVEN_PRESERVE'
FRAME={'minecraft:bricks','minecraft:stripped_spruce_log','minecraft:stripped_dark_oak_log',
       'dawnoftimebuilder:blue_plastered_stone','minecraft:stone_brick_slab'}


def local(q):return tuple(q[i]-ORIGIN[i] for i in range(3))
def world(q):return tuple(q[i]+ORIGIN[i] for i in range(3))
def inside(q):return 1232<=q[0]<=1242 and -1212<=q[2]<=-1202


def checked(path,sha,maximum):
    path=Path(path)
    if path.is_symlink() or not path.is_file() or not 0<path.stat().st_size<=maximum or digest(path)!=sha:
        raise UserError('Exact bounded custody/source bytes required: '+path.name)
    return read_json(path)


def read_custody(home):
    root=home/LEDGER;manifest=checked(root/'manifest.json',LEDGER_SHA,2*MIB)
    if manifest['rejected_house_count']!=52 or manifest['current_BE_count']!=727:
        raise UserError('Bind the whole reviewed52-house/727-BE custody baseline')
    selected=next((v for v in manifest['houses'] if v['id']==ID),None)
    if selected is None:raise UserError('The actual named eastern house is absent')
    rows={};bes={};count=0
    for filename,sha,maximum in (('cells-READONLY.jsonl',CELL_SHA,48*MIB),('block-entities-FULL-TYPED-PRIVATE.jsonl',BE_SHA,2*MIB)):
        path=root/filename
        if path.is_symlink() or path.stat().st_size>maximum or digest(path)!=sha or manifest['files'][filename]!={'sha256':sha,'bytes':path.stat().st_size}:
            raise UserError('Complete private custody journal bytes changed')
        with path.open(encoding='utf-8') as stream:
            for line in stream:
                if len(line)>2*MIB:raise UserError('Finite typed custody row exceeded')
                row=json.loads(line);q=tuple(row['position']);count+=1
                if inside(q):
                    target=rows if filename.startswith('cells') else bes
                    if q in target:raise UserError('Duplicate custody position')
                    target[q]=row
    if len(rows)!=2047 or len(bes)!=15 or count>130000:
        raise UserError('The selected exact house/skirt custody field changed')
    return manifest,selected,rows,bes


def shell_replacement_allowed(q,old,new,source,ledger,protected,walk):
    """A saved match is necessary, never permission to erase a container."""
    if q in protected or q in walk:
        raise UserError('Preserve an actual BE, its support, fixture or walking body: '+str(q))
    row=ledger.get(q)
    if key(old) in VOID:
        if old!=source.get(q,old) or row and row['classification']!='SOURCE_AIR_CLEARANCE_ONLY':
            raise UserError('An old source AIR target gained later progress; preserve it')
        return 'EXACT_CURRENT_AIR_ADDITION'
    if row is None or row['classification']!=EXACT or old!=row['actual_saved'] or old!=source.get(q):
        raise UserError('Only positively owned unchanged NON-BE geometry may be replaced: '+str((q,old)))
    material=key(old)
    if not (material.startswith('mcwroofs:') or material in FRAME or material.startswith('mcwwindows:')):
        raise UserError('A source match does not authorize removing furniture, a bed, plant or station')
    return 'EXACT_UNCHANGED_OWNED_ARCHITECTURE'


class Retrofit(TradeHouse):
    def __init__(self,registry,before,source,ledger,protected,walk):
        super().__init__(registry,'The Seabird Ledger — Tortuga correction',ORIGIN)
        self.blocks={local(q):v for q,v in before.items()}
        self.before=dict(before);self.source=source;self.ledger=ledger
        self.protected=protected;self.walk=walk;self.edits={};self.origins={};self.retained=[]

    def put(self,x,y,z,material,*,role='original 3D Tortuga correction',**props):
        if not -2<=x<=10 or not -1<=z<=12 or not 0<=y<=16:raise UserError('The one eastern correction escaped its finite bounds')
        q=world((x,y,z));value=state(self.registry,material,**props)
        if q not in self.before:raise UserError('Every new projection needs its actual current FULL preimage first')
        old=self.before[q]
        if value==self.blocks.get((x,y,z),old):return
        origin=shell_replacement_allowed(q,old,value,self.source,self.ledger,self.protected,self.walk)
        self.blocks[x,y,z]=value;self.edits[q]=value;self.origins[q]={'reason':origin,'role':role,'old':old,'new':value}


def design(p):
    # Remove only confirmed original roof/bands/gable above the unchanged
    # furnished top ceiling. Four differing native support joints stay exact.
    removed=[]
    for q,old in sorted(p.before.items()):
        if not inside(q) or q[1]<72 or q in p.protected:continue
        name=key(old)
        roof=name.startswith('mcwroofs:')
        gable=q[1]>72 and name in FRAME
        if roof or gable:
            row=p.ledger.get(q)
            if row and row['classification']==EXACT and old==p.source.get(q):
                p.put(*local(q),AIR,role='remove only exact owned bright roof bands/original gable');removed.append(q)
    # The full hipped roof is one quiet weathered clay composition; its four
    # faces, diagonal seams and deep rafters replace periodic light stripes.
    # Existing unproven support-cap deltas and original loggia hood are held.
    held={local(q) for q,row in p.ledger.items() if row['classification']==JOIN}
    hood={(x,8,9) for x in (3,4,5)}
    class Roof:
        def __init__(self,parent):self.parent=parent;self.blocks=parent.blocks;self.details=parent.details
        def put(self,x,y,z,name,**props):
            if (x,y,z) in held|hood:
                self.parent.retained.append({'local':[x,y,z],'reason':'Preserve exact existing support/loggia cap; no attribution of state delta'})
                return
            self.parent.put(x,y,z,name,**props)
        def slab(self,x,y,z,wood='dark_oak',role='rooted shallow roof detail'):
            self.put(x,y,z,'minecraft:'+wood+'_slab',type='top',waterlogged=False,role=role)
    hip(Roof(p),(-1,-1,9,9),8,'brown_terracotta')
    # Retain all furniture/backing neighborhoods. Muted full masonry replaces
    # only the remaining original bright plaster panels outside those holds.
    for q,old in sorted(p.before.items()):
        if key(old)=='dawnoftimebuilder:blue_plastered_stone' and 69<=q[1]<=71:
            if q in p.protected:continue
            p.put(*local(q),'minecraft:cyan_terracotta',role='recessed weathered slate/teal plaster panel')
    # A genuinely glazed WEST oriel with clear reveals. It is a window nook,
    # not a claim that the old tiny loggia is a traversable extra room.
    for z in (1,2):
        for y in (5,6):p.put(0,y,z,AIR,role='owned old wall opening below the retained interior lamp backing')
        p.slab(-1,4,z,'dark_oak',role='projecting solid oriel sill')
        for y in (5,6):p.put(-1,y,z,'mcwwindows:dark_oak_four_window',facing='west',windowstate='locked',role='real deep glazed west oriel')
    for z in (0,3):
        for y in (4,5,6):p.beam(-1,y,z,'y',role='carved oriel cheek returned to actual wall')
        p.put(-1,3,z,'mythrais:curved_corbel_dark_oak',facing='west',shape=0,role='rooted actual oriel knee')
    for z in range(0,4):p.beam(-1,7,z,'z',role='continuous supported oriel head below the old roof')
    # A deep asymmetrical sheltered forecourt, on the RETAINED real paving.
    # No platform replaces the existing three-wide approach or ground route.
    for x in (2,7):
        p.put(x,0,11,'minecraft:stone_bricks',role='one real porch-post shoe on untouched dry paving')
        for y in range(1,5):p.beam(x,y,11,'y',role='weathered tall porch standard')
        for z in (9,10,11):p.beam(x,4,z,'z',role='genuine porch return bearer')
        p.put(x,3,10,'mythrais:curved_corbel_dark_oak',facing='south',shape=0,role='deep porch knee and actual carved shadow')
    for x in range(2,8):p.beam(x,4,11,'x',role='heavy continuous forecourt front crossbeam')
    for x in range(1,9):
        for z in (10,11):p.slab(x,5,z,'spruce',role='quiet shallow porch roof under the retained loggia')
    for x in (2,7):p.lamp(x,3,12,'south')
    # The actual grass, planted edges and every original flower/pot remain.
    # The independent botanical LIFE pass is not simulated by replacing them.
    p.details.append({'kind':'source preservation','old_roof_or_gable_cells_removed':len(removed),
        'unchanged_furnished_storeys':2,'original_door_stair_later_progress_and_all_BE_NBT':'retained, never replayed',
        'street':'Existing ground-height three-wide approach and primary lane remain exact'})
    return p


def with_exact_be_tags(raw,bes):
    value=json.loads(raw)
    value['block_entities']=[{'pos':list(q),'nbt':be.snbt()} for q,be in sorted(bes.items())]
    return (json.dumps(value,separators=(',',':'))+'\n').encode()


def prepare(home,checkpoint_id,checkpoint_sha):
    home=Path(home).resolve();reserve=guard(2*MIB,16*MIB)
    if home.parent!=Path('D:/A World for Two/staging/world-tests').resolve():raise UserError('Private owned stage only')
    receipt=read_json(home/'dashboard/settlement/backup-receipt.json');registry=read_json(home/'dashboard/settlement/registry.json')
    admit_owner(home,read_json(home/'dashboard/artistic-owner.json'),receipt,checkpoint_id,checkpoint_sha)
    ledger_manifest,house,ledger,old_bes=read_custody(home)
    original_manifest=checked(home/SOURCE/'manifest.json',SOURCE_MANIFEST_SHA,4*MIB)
    source_doc=checked(home/SOURCE/'prototype.json',SOURCE_SHA,MIB)
    checked(home/SOURCE/'before-VERIFY-ONLY.json',SOURCE_BEFORE_SHA,MIB)
    if any(str(source_doc[k])!=str(registry[k]) for k in ('seed','world_path')):raise UserError('Same actual owned world source required')
    source=flatten(source_doc);footprint=set(map(tuple,house['main_footprint']))
    walk=set(map(tuple,original_manifest['walk_body_cells']))
    fixtures={tuple(v['position']) for v in original_manifest['fixtures'] if v.get('room')==house['name']}
    fixture_supports={tuple(v['support']) for v in original_manifest['supports'] if tuple(v['fixture']) in fixtures}
    snapshot=BackupWorld(home,receipt,registry);started=time.monotonic()
    try:
        # Source context plus exact current new-roof/oriel/forecourt field. No
        # all-AIR bounding cube is fabricated or written to the native world.
        wanted=set(ledger)
        wanted.update((x,y,z) for x in range(1231,1244) for z in range(-1212,-1198) for y in range(64,81))
        before={q:snapshot.state(q) for q in sorted(wanted)}
        if any(v is None for v in before.values()):raise UserError('Every planned projection/current context must be saved FULL known')
        if time.monotonic()-started>60:raise UserError('Finite current-house saved read expired')
        actual_bes={}
        for cx,cz in {(p[0]//16,p[2]//16) for p in before}:
            raw=snapshot.regions[cx//32,cz//32];doc=decoded_chunk(raw,cx,cz)
            for be in doc.get('block_entities',[]):
                q=int(be['x']),int(be['y']),int(be['z'])
                if q in before:actual_bes[q]=be
        if set(actual_bes)!=set(old_bes):raise UserError('Preserve newly added/removed BEs; this pilot needs a new explicit custody review')
        blocked=set(fixtures)|fixture_supports|set(actual_bes)
        for q in actual_bes:
            blocked.update((q[0]+dx,q[1]+dy,q[2]+dz) for dx in (-1,0,1) for dy in (-1,0,1) for dz in (-1,0,1))
        # All genuinely saved beds, including non-BE blocks, remain untouched.
        blocked.update(q for q,v in before.items() if key(v).endswith('_bed'))
        p=design(Retrofit(registry,before,source,ledger,blocked,walk))
        delta=dict(p.edits);after=dict(before);after.update(delta)
        heritage,heritage_sources=preservation(home,registry)
        if {(x,z) for x,y,z in delta}&heritage:
            raise UserError('Keep accepted Signal/Spit/imports/bridge/harbor architecture and their clearance skirt')
        zip_relative='staging/zipline-west-v2-source-1793152099836099800/all-v2-RESERVATION-ONLY.json'
        zip_sha='92ea594836795a61e00f5cc32290d49d1d47b9fd6eb55aeefc99d527acf8854d'
        zip_doc=checked(home/zip_relative,zip_sha,2*MIB)
        zip_columns={(r[0]+dx,r[2]+dz) for r in zip_doc['blocks'] for dx in range(-5,6) for dz in range(-5,6)}
        if {(x,z) for x,y,z in delta}&zip_columns:raise UserError('Retain actual complete v2 zipline/flight plus five metres')
        for q in walk.intersection(after):
            if after[q]!=before[q]:raise UserError('Do not change an existing whole-quarter walking body')
        if set(delta)&set(actual_bes):raise UserError('No old BE may be placed, cleared, moved or recreated')
        supports={}
        for q in ((1235,63,-1200),(1240,63,-1200)):
            value=snapshot.state(q)
            if key(value) not in {'minecraft:gravel','minecraft:cobblestone','minecraft:mossy_cobblestone','minecraft:stone_bricks','minecraft:grass_block','minecraft:coarse_dirt'}:
                raise UserError('A forecourt post lacks retained dry solid paving/ground')
            supports[q]=value
        for detail,backing in p.supports:
            if key(after[world(backing)]) in VOID:
                raise UserError('A new porch fitting has no real current/proposed support')
        # Face-connected structural proof for the NEW solids, rooted in the
        # retained original floor or the two independently measured post shoes.
        solid={q for q,v in after.items() if key(v) not in VOID}
        rooted={(x,64,z) for x,z in footprint if (x,64,z) in solid}
        rooted.update((x,64,z) for x,y,z in supports)
        pending=deque(rooted)
        while pending:
            q=pending.popleft()
            for d in ((1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1)):
                v=tuple(q[i]+d[i] for i in range(3))
                if v in solid and v not in rooted:rooted.add(v);pending.append(v)
        if any(q not in rooted for q,v in delta.items() if key(v) not in VOID):
            raise UserError('A new roof/oriel/porch solid lacks a path to the actual structure or dry shoe')
        material_field={q:v for q,v in after.items() if (q[0],q[2]) in footprint and q[1]>=64 or q[1]>=68 and inside(q)}
        material_field.update(delta)
        proof=require_material_rule(material_field,'Whole Seabird Ledger furnished building plus original new Tortuga roof/oriel/porch')
        be_records=[]
        for q,be in sorted(actual_bes.items()):
            data=typed(be);raw=(json.dumps(data,sort_keys=True,separators=(',',':'),ensure_ascii=False)).encode()
            be_records.append({'pos':list(q),'state':before[q],'current_full_typed_NBT':data,'current_full_typed_NBT_sha256':hashlib.sha256(raw).hexdigest(),
                'matches_historical575_typed_NBT':hashlib.sha256(raw).hexdigest()==old_bes[q]['actual_full_typed_NBT_sha256'],
                'action':'PRESERVE IN PLACE; no tag/slot/owner change; source bytes are not runtime slot acceptance'})
        outputs={
            'seabird-delta-before-VERIFY-ONLY.json':native_payload(registry,{q:before[q] for q in delta},checkpoint_sha,'Exact current before of owned NON-BE correction targets'),
            'seabird-shell-PROPOSAL.json':native_payload(registry,delta,checkpoint_sha,'One original eastern Tortuga correction; no BE or inventory replay'),
            'seabird-current-composite-before-VERIFY-ONLY.json':with_exact_be_tags(native_payload(registry,before,checkpoint_sha,'Full current house/context and retained actual BE tags; verify only'),actual_bes),
            'seabird-new-composite-VERIFY-ONLY.json':with_exact_be_tags(native_payload(registry,after,checkpoint_sha,'Full proposed eastern house/context retaining every actual BE tag'),actual_bes),
            'unchanged-post-ground-VERIFY-ONLY.json':native_payload(registry,supports,checkpoint_sha,'Actual retained dry post supports; no paving replacement'),
            'retained-BEs-FULL-TYPED-PRIVATE.json':(json.dumps({'format':'awft-retained-in-place-native-BE-custody:1','checkpoint_sha256':checkpoint_sha,'records':be_records},separators=(',',':'))+'\n').encode(),
            'owned-shell-changes-PRIVATE.json':(json.dumps({'changes':[{'pos':list(q),**v} for q,v in sorted(p.origins.items())]},separators=(',',':'))+'\n').encode()}
        mask=native_payload(registry,{q:AIR for q in after},checkpoint_sha,'Future one eastern Tortuga correction/context reservation, not observed AIR')
        mask=json.loads(mask);mask.update(reservation_only=True,not_an_observed_AIR_plan=True)
        outputs['future-solid-AIR-walk-reservation-ONLY.json']=(json.dumps(mask,separators=(',',':'))+'\n').encode()
        cameras=[{'name':'seabird-front-under-porch','feet':[1237.5,64,-1197.5],'look_at':[1237,70,-1205]},
            {'name':'seabird-west-oriel','feet':[1228.5,64,-1205.5],'look_at':[1233,71,-1208]},
            {'name':'seabird-retained-home','feet':[1237.5,69,-1206.5],'look_at':[1235,70,-1206]}]
        for row in cameras:
            x,y,z=(int(v//1) for v in row['feet']);positions=[(x,y-1,z),(x,y,z),(x,y+1,z)]
            values=[after[q] if q in after else snapshot.state(q) for q in positions]
            if key(values[0]) in VOID|{'minecraft:water','minecraft:lava'} or any(key(v) not in VOID for v in values[1:]):raise UserError('Native camera proposal lacks measured floor/body')
            row['actual_or_proposed_floor_body']=[{'pos':list(q),'state':v} for q,v in zip(positions,values)]
        record={'format':'awft-one-eastern-tortuga-retrofit:1','source_sha256':digest(Path(__file__)),'checkpoint_id':checkpoint_id,'checkpoint_sha256':checkpoint_sha,
            'status':'SOURCE ONLY; one pilot, not a37-house accepted redesign','house_id':ID,'original_manifest_sha256':SOURCE_MANIFEST_SHA,
            'original_source_sha256':SOURCE_SHA,'original_before_sha256':SOURCE_BEFORE_SHA,'full52_727BE_ledger_sha256':LEDGER_SHA,
            'ledger_cells_sha256':CELL_SHA,'ledger_typed_BEs_sha256':BE_SHA,'original_main_footprint':[list(p) for p in sorted(footprint)],
            'preserved_BEs':len(actual_bes),'existing_NBT_or_items_written':0,'preserved_full_native_BE_component_proof':'Exact current stopped typed bytes retained privately; fresh native class/slot/full-component custody remains required',
            'removed_or_replaced_only_exact_owned_nonBE':dict(Counter(v['reason'] for v in p.origins.values())),
            'accepted_original_heritage_and_clearance_sources':heritage_sources,'actual_west_v2_mask_sha256':zip_sha,
            'retained_unproven_native_joint_cells':p.retained,'native_cameras':cameras,'material_proof':proof,'design_details':p.details,
            'delta_cells':len(delta),'full_composite_cells':len(after),'whole_quarter_walk_cells_unchanged':len(walk.intersection(after)),
            'every_new_solid_structurally_rooted_in_saved_floor_or_measured_dry_post_shoe':True,
            'current_saved_sources':snapshot.sources,'native_actions':0,'world_writes':0,'no_recovery_or_demolition_of_unrelated_work':True,
            'native_gates':'Fresh current occupancy and exact full before/BE/support custody, parent admitted copy/one delta placement, ordinary neighbor settling, complete native states/NBT and real exterior/interior/roof views before wider propagation',
            'reserve_guard':reserve,'files':{name:{'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()} for name,raw in outputs.items()}}
        outputs['manifest.json']=(json.dumps(record,ensure_ascii=False,indent=2)+'\n').encode()
        if sum(map(len,outputs.values()))>16*MIB:raise UserError('One finite eastern prototype exceeded its output bound')
        guard(2*MIB,16*MIB);out=home/'staging'/('seabird-tortuga-retrofit-'+str(time.time_ns()));out.mkdir()
        for name,raw in outputs.items():
            with (out/name).open('xb') as stream:stream.write(raw)
        return {'folder':str(out),'manifest_sha256':digest(out/'manifest.json'),'delta_cells':len(delta),'composite_cells':len(after),'BEs_preserved_in_place':len(actual_bes),'native_actions':0}
    finally:snapshot.close()


if __name__=='__main__':
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('--home',type=Path,required=True);a.add_argument('--checkpoint-id',required=True);a.add_argument('--checkpoint-sha',required=True)
    args=a.parse_args();print(json.dumps(prepare(args.home,args.checkpoint_id,args.checkpoint_sha),indent=2))
