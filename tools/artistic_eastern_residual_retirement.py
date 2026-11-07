"""Ordinary retirement proposals for measured old AI remnants outside city39.

Reads authenticated stopped MCA members only. Emits the existing settlement
before / Items-empty / AIR / normal / after plans; never invokes the game.
"""
from __future__ import annotations
import argparse,hashlib,json,time,zipfile
from collections import Counter,defaultdict
from pathlib import Path
import nbtlib

from control_room.common import UserError,digest,read_json
from tools.artistic_bridge_refinement import flatten
from tools.artistic_captains_hall import native_payload
from tools.artistic_east_tortuga_retrofit import checked
from tools.artistic_eastern_direct_build import AIR,CORE,HUMAN,inside
from tools.artistic_eastern_urban_custody import before_sources,PRIVATE_ANCHORS
from tools.artistic_north_bank_east import NorthTerrain
from tools.artistic_north_rebuild_custody import BATCHES,decoded_chunk,typed,inventory_facts
from tools.native_eastern_relocation import CLASSES
from tools.native_relocation_request import reference
from tools.playtest import guard
from tools.settlement_attractions import properties

MIB=1024**2
COMPLETION='staging/east-city58-execution-1793245885314381500/NATIVE25-COMPLETE-SEALED.json'
COMPLETION_SHA='e878b6caf3327d783446aa6701c5d3406e0b3f4d1f2c6d1d64f1fa9969b9da08'
CURRENT14='staging/east-city58-execution-1793245066812072500/CURRENT-CLERESTORY-COMPLETE.json'
DIRECTIONS=((1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1))


def key(value):return value.split('[',1)[0]


def source_relation(old,current):
    """Retirement provenance, not permission to normalize a native state."""
    if current is None:return 'HOLD_UNKNOWN'
    if key(current)in AIR:return 'ALREADY_AIR'
    if key(old)!=key(current):return 'HOLD_CHANGED_IDENTITY'
    if 'waterlogged=true'in current or key(current)in('minecraft:water','minecraft:lava'):return 'HOLD_FLUID'
    if old==current:return 'EXACT_AUTHORED_STATE'
    a,b=properties(old),properties(current);different={k for k in a.keys()|b.keys()if a.get(k)!=b.get(k)};ident=key(old)
    if ident in('mcwroofs:red_terracotta_roof','mcwroofs:dark_oak_roof','mcwroofs:stone_bricks_roof')and different=={'shape'}:
        return 'NATIVE_ROOF_CONNECTION'
    if ident=='dawnoftimebuilder:spruce_support_slab'and different=={'pillar_connection'}:return 'NATIVE_PILLAR_CONNECTION'
    if ident=='minecraft:dark_oak_fence'and different<={'north','south','east','west'}:return 'NATIVE_FENCE_CONNECTION'
    if(ident=='handcrafted:spruce_nightstand'and all(b.get(k)==v for k,v in a.items())
        and set(b)-set(a)<={'color','waterlogged'}and b.get('color')=='none'and b.get('waterlogged')=='false'):
        return 'PINNED_DEFAULT_PROPERTIES_OMITTED_BY_ORIGINAL_SOURCE'
    return 'HOLD_UNPROVEN_STATE_CHANGE'


def component_value(value):
    # Component JSON is parsed only to compare old authored text with its
    # normal serialized representation. No tag/state is rewritten or loaded.
    if isinstance(value,nbtlib.String):
        try:
            result=json.loads(str(value))
            if isinstance(result,dict)and set(result)=={'text'}and isinstance(result['text'],str):return result['text']
            return result
        except (ValueError,TypeError):return str(value)
    return typed(value)


def stock_hold(tag,authored):
    """Do not mistake added personal stock or written content for AI default."""
    facts=inventory_facts(tag)
    if facts['unresolved_loot_fields']:return 'Unresolved native loot field'
    for name in('Owner','owner','OwnerUUID','owner_uuid','connectedPlayers','ConnectedPlayers','ForgeCaps','neoforge:attachments'):
        if name=='neoforge:attachments'and str(tag.get('id'))=='minecraft:sign':
            attachment=tag.get(name)
            if(isinstance(attachment,nbtlib.Compound)and set(attachment)=={'supplementaries:antique_ink'}
                and type(attachment['supplementaries:antique_ink'])is nbtlib.Byte and int(attachment['supplementaries:antique_ink'])==0):continue
        if tag.get(name)and(authored is None or name not in authored or typed(tag[name])!=typed(authored[name])):return 'Unowned/personal persistent data: '+name
    if tag.get('Book'):
        if authored is None or not authored.get('Book')or typed(tag['Book'])!=typed(authored['Book']):return 'Non-default lectern/written-book content'
    if tag.get('Items'):
        if authored is None or 'Items'not in authored or typed(tag['Items'])!=typed(authored['Items']):return 'Current item stacks/components differ from original authored stock'
    if tag.get('CustomName'):
        if authored is None or not authored.get('CustomName')or component_value(tag['CustomName'])!=component_value(authored['CustomName']):return 'Changed or unowned actual container name'
    if str(tag.get('id'))=='minecraft:sign':
        if authored is None:return 'No original authored sign text'
        if bool(tag.get('is_waxed',0))!=bool(authored.get('is_waxed',0)):return 'Changed actual sign wax state'
        for side in('front_text','back_text'):
            actual=tag.get(side,{});expected=authored.get(side,{})
            if(str(actual.get('color','black'))!=str(expected.get('color','black'))
                or bool(actual.get('has_glowing_text',0))!=bool(expected.get('has_glowing_text',0))):return 'Changed actual sign color/glow'
            def messages(part):
                color=str(part.get('color','black'));result=[]
                for raw in part.get('messages',[]):
                    value=component_value(raw)
                    if isinstance(value,dict)and value.get('color')==color:
                        value={k:v for k,v in value.items()if k!='color'}
                        if set(value)=={'text'}:value=value['text']
                    result.append(value)
                return result or ['']*4
            if messages(actual)!=messages(expected):return 'Changed actual sign messages'
    return None


def primary_pins(home):
    rows=[]
    for name,classes in(
        ('mcw-roofs-2.3.2-mc1.21.1neoforge.jar',('com.mcwroofs.kikoz.objects.roofs.RoofBlock',)),
        ('dawnoftimebuilder-neoforge-1.21.1-1.6.8.jar',('org.dawnoftime.dawnoftime.block.templates.SupportSlabBlock','org.dawnoftime.dawnoftime.block.IBlockPillar')),
        ('handcrafted-neoforge-1.21.1-4.0.3.jar',('earth.terrarium.handcrafted.common.blocks.NightstandBlock','earth.terrarium.handcrafted.common.blocks.SimpleTableBlock'))):
        jar=home/'server/mods'/name
        with zipfile.ZipFile(jar)as z:
            for klass in classes:
                raw=z.read(klass.replace('.','/')+'.class');rows.append({'jar':name,'jar_sha256':digest(jar),'class':klass,'class_sha256':hashlib.sha256(raw).hexdigest()})
    jar=home/'server/mods/supplementaries-1.21.1-4.0.2-neoforge.jar'
    with zipfile.ZipFile(jar)as z:
        for klass in('net.mehvahdjukaar.supplementaries.platform.CapabilityHandler','net.mehvahdjukaar.supplementaries.platform.CapabilityHandler$AntiquableAttachment'):
            raw=z.read(klass.replace('.','/')+'.class');rows.append({'jar':jar.name,'jar_sha256':digest(jar),'class':klass,'class_sha256':hashlib.sha256(raw).hexdigest(),
                'default_attachment_rule':'antique_ink supplier constructs AntiquableAttachment(false); accept only exact Byte0, no other attachments'})
    installed=read_json(home/'server/installed.json');version=installed['neoforge'];patched=home/f'server/libraries/net/neoforged/neoforge/{version}/neoforge-{version}-server.jar'
    games=list((home/'server/libraries/net/minecraft/server').rglob('*-srg.jar'))
    if len(games)!=1:raise UserError('Exact installed native base game required')
    entry='net/minecraft/world/level/block/FenceBlock.class'
    with zipfile.ZipFile(patched)as z:override=entry in z.namelist()
    jar=patched if override else games[0]
    with zipfile.ZipFile(jar)as z:raw=z.read(entry)
    rows.append({'jar':jar.name,'jar_sha256':digest(jar),'class':'net.minecraft.world.level.block.FenceBlock','class_sha256':hashlib.sha256(raw).hexdigest()})
    entry='net/minecraft/world/level/chunk/LevelChunk.class'
    with zipfile.ZipFile(patched)as z:override=entry in z.namelist()
    jar=patched if override else games[0]
    with zipfile.ZipFile(jar)as z:raw=z.read(entry)
    rows.append({'jar':jar.name,'jar_sha256':digest(jar),'class':'net.minecraft.world.level.chunk.LevelChunk','class_sha256':hashlib.sha256(raw).hexdigest(),
        'storage_envelope_rule':'getBlockEntityNbtForSaving adds keepPacked:0b to saved normal BE; saveWithFullMetadata does not'})
    return rows


def completed_city_fields(home):
    seal=checked(home/COMPLETION,COMPLETION_SHA,2*MIB);protected={};refs=[]
    first=read_json(home/CURRENT14);record=next(r for r in first['records']if r['phase']=='cooper24-full14-after')
    records=[record]+[{'actual_terminal':r['actual_complete_native_after']}for r in seal['results']]
    intents={}
    folder=(home/COMPLETION).parent
    for p in folder.glob('*.intent.json'):
        d=read_json(p)
        if d['operation']=='verify':intents[d['plan']['sha256']]=d['plan']
    for record in records:
        nr=record['actual_terminal'];p=home/nr['path'];native=checked(p,nr['sha256'],MIB)
        if(p.with_name(p.name+'.complete').read_text().strip()!=nr['sha256']or native.get('operation')!='verify'
            or native.get('failures')!=0 or native.get('cleanup_required')is not False
            or native.get('temporary_tickets_remaining')!=0 or native.get('pending_shared_chunk_futures')!=0):raise UserError('Actual clean city-field proof required')
        plan=record.get('plan')or intents[native['plan_sha256']];d=checked(home/plan['path'],plan['sha256'],8*MIB)
        if native['plan_sha256']!=plan['sha256']or native['blocks']!=len(d['blocks']):raise UserError('Actual city proof/field binding differs')
        protected.update(flatten(d));refs.append({'plan':plan,'actual_native_verify':nr})
    if len(seal['results'])!=25 or len(refs)!=26:raise UserError('Exact fourteen-plus-twenty-five city protection required')
    return protected,refs


def prepare(home,recovery_id,recovery_sha):
    home=Path(home).resolve();reserve=guard(MIB,32*MIB);started=time.monotonic();reg=read_json(home/'dashboard/settlement/registry.json')
    companion=read_json(home/'backups'/(recovery_id+'.json'))
    if companion.get('integrity')!='verified'or companion.get('sha256')!=recovery_sha:raise UserError('Exact verified post-city stopped snapshot required')
    receipt={'id':recovery_id,'sha256':recovery_sha,'verified':True};protected,city_refs=completed_city_fields(home)
    _,authored,_,old_refs,_=before_sources(home);private=PRIVATE_ANCHORS|{(1275,64,-1206)}
    candidates={q:v for q,v in authored.items()if q[1]>=64 and key(v)not in AIR and q not in protected and q not in private and not any(inside(q,b)for b in CORE+HUMAN)}
    if len(candidates)>16000:raise UserError('Finite16k old-source candidate limit exceeded')
    original_tags={}
    for _,rel,name,*_ in BATCHES[:3]:
        for row in read_json(home/rel/name).get('block_entities',[]):original_tags[tuple(row['pos'])]=nbtlib.parse_nbt(row['nbt'])
    terrain=NorthTerrain(home,receipt,reg);current={};bes={};relations={};holds=[];groups=defaultdict(list)
    try:
        for q in candidates:groups[q[0]//16,q[2]//16].append(q)
        for(cx,cz),points in sorted(groups.items()):
            for q in points:current[q]=terrain.state(*q)
            doc=decoded_chunk(terrain.snapshot.regions[cx//32,cz//32],cx,cz)
            for tag in doc.get('block_entities',[]):
                q=tuple(int(tag[k])for k in('x','y','z'))
                if q in candidates:bes[q]=tag
        retire={};reset={};variants=[]
        for q,old in sorted(candidates.items()):
            now=current[q];relation=source_relation(old,now);relations[q]=relation
            if relation.startswith('HOLD'):holds.append({'position':list(q),'reason':relation,'old_authored_state':old,'actual_saved_state':now});continue
            if relation=='ALREADY_AIR':continue
            tag=bes.get(q)
            if tag is not None:
                ident=str(tag.get('id'));definition=CLASSES.get(ident);why=stock_hold(tag,original_tags.get(q))
                if definition is None or why:holds.append({'position':list(q),'reason':why or 'Unknown native BE handler','BE_id':ident});continue
                if definition[2]:
                    if ident=='supplementaries:book_pile':holds.append({'position':list(q),'reason':'Book piles require separately reviewed physical default-drop semantics'});continue
                    reset[q]=now
            retire[q]=now
            if relation!='EXACT_AUTHORED_STATE':
                context={}
                for dx,dy,dz in DIRECTIONS:
                    v=terrain.state(q[0]+dx,q[1]+dy,q[2]+dz)
                    if v is None:raise UserError('Native-derived variant needs complete saved neighbour context')
                    context[','.join(map(str,(dx,dy,dz)))]=v
                variants.append({'position':list(q),'old_authored_state':old,'actual_saved_state':now,'classification':relation,'actual_saved_neighbour_context':context})
        # A final native readback covers every actual39 cell, not a regenerated
        # visual forecast. No protected AIR, room, object or stock enters writes.
        protected_current={};protected_groups=defaultdict(list)
        for q in protected:protected_groups[q[0]//16,q[2]//16].append(q)
        for _,points in sorted(protected_groups.items()):
            for q in points:protected_current[q]=terrain.state(*q)
        if any(v is None for v in protected_current.values()):raise UserError('Protected city snapshot has an unknown/nonFULL cell')
        adjacent={q:protected_current[q]for p in retire for d in DIRECTIONS if(q:=tuple(p[k]+d[k]for k in range(3)))in protected_current}
        if len(retire)+len(adjacent)>20000:raise UserError('Split normal neighbour target plan above20k')
        archive_refs=terrain.snapshot.sources
    finally:terrain.close()
    if time.monotonic()-started>90:raise UserError('Finite90s stopped-field proposal limit exceeded')
    out=home/'staging'/('eastern-residual-retirement-'+str(time.time_ns()));out.mkdir();written=0
    def emit(name,doc):
        nonlocal written
        raw=(json.dumps(doc,separators=(',',':'))+'\n').encode();written+=len(raw)
        if written>32*MIB:raise UserError('Finite32MiB proposal output exceeded')
        p=out/(name+'.json');p.open('xb').write(raw);return reference(home,p)
    backup=read_json(home/'dashboard/settlement/backup-receipt.json')['sha256']
    def native(name,values,tags=None,exact_tags=None):
        doc=json.loads(native_payload(reg,values,backup,'SOURCE old AI residual '+name));doc.update(verification_only=True,construction_forbidden=True,actual_saved_checkpoint=receipt);doc['block_entities']=[]
        if tags:doc['block_entities']=[{'pos':list(q),'nbt':s}for q,s in sorted(tags.items())]
        if exact_tags is not None:doc.update(exact_native_tags=True,block_entities=exact_tags)
        return emit(name,doc)
    files={}
    exact_rows=[];raw_tag_hashes=[]
    for q in sorted(retire.keys()&bes.keys()):
        tag=bes[q];expected=nbtlib.Compound(tag)
        if 'keepPacked'in expected:
            if type(expected['keepPacked'])is not nbtlib.Byte or int(expected['keepPacked'])!=0:raise UserError('Only the exact false native chunk-storage envelope may be removed')
            del expected['keepPacked']
        ident=str(tag['id']);exact_rows.append({'pos':list(q),'native_class':CLASSES[ident][1],'nbt':expected.snbt()})
        raw_tag_hashes.append({'position':list(q),'raw_saved_typed_sha256':hashlib.sha256(json.dumps(typed(tag),sort_keys=True).encode()).hexdigest(),
            'expected_native_typed_sha256':hashlib.sha256(json.dumps(typed(expected),sort_keys=True).encode()).hexdigest()})
    if exact_rows:files['all_retired_BE_exact_before']=native('all-retired-BEs-exact-native-BEFORE',{q:retire[q]for q in retire.keys()&bes.keys()},exact_tags=exact_rows)
    if reset:
        files.update(stock_before=native('stock-BEFORE',reset),stock_empty_delta=native('stock-empty-DELTA',reset,{q:'{Items:[]}'for q in reset}),stock_empty_after=native('stock-empty-AFTER',reset,{q:'{Items:[]}'for q in reset}))
    files.update(before=native('retirement-BEFORE',retire),delta=native('retirement-AIR-DELTA',{q:'minecraft:air'for q in retire}),
        settle=native('retirement-normal-neighbours',{**adjacent,**{q:'minecraft:air'for q in retire}}),
        after=native('FULL-current39-plus-retirement-AFTER',{**protected_current,**{q:'minecraft:air'for q in retire}}),
        protected39=native('actual39-protected-READONLY',protected_current))
    files['future_cleanup_mask']=emit('cleanup-RESERVATION-ONLY',{'format':'awft-exact-old-AI-cleanup-reservation:1','positions_xyz':[list(q)for q in sorted(retire)],'candidate_columns_xz':[list(q)for q in sorted({(p[0],p[2])for p in candidates})],'no_planting_or_native_authority':True})
    audit={'actual_saved_checkpoint':receipt,'old_source_refs':old_refs,'candidate_count':len(candidates),'counts':dict(Counter(relations.values())),
        'actual_saved_BE_count':len(bes),'ordinary_AI_Container_reset_rows':len(reset),'retirement_targets':len(retire),'holds':holds,'BE_storage_to_native_tag_hashes':raw_tag_hashes,
        'native_variation_records':variants,'primary_native_class_pins':primary_pins(home),
        'native_algorithm_context':{'NATIVE_ROOF_CONNECTION':'Pinned RoofBlock.updateShape(horizontal) sets SHAPE from getStairsShape with actual neighbours; FACING/HALF unchanged.',
            'NATIVE_PILLAR_CONNECTION':'Pinned SupportSlabBlock.updateShape(DOWN) calls IBlockPillar.getPillarConnectionAbove on actual below block.',
            'NATIVE_FENCE_CONNECTION':'Pinned vanilla FenceBlock.updateShape derives horizontal connection booleans from actual adjacent block/face.',
            'PINNED_DEFAULT_PROPERTIES_OMITTED_BY_ORIGINAL_SOURCE':'Pinned SimpleTableBlock constructor defaults COLOR=NONE and WATERLOGGED=false; original sparse source omitted these properties.'},
        'no_actual_tag_or_blockstate_normalization':True,'all_actual_states_remain_literal_before_values':True,'actual_protected39_cells':len(protected_current),'new_city_cells_in_write_set':0}
    files['provenance']=emit('PROVENANCE',audit)
    manifest={'format':'awft-eastern-measured-residual-retirement:1','files':files,'actual_saved_checkpoint':receipt,'source_sha256':digest(Path(__file__)),
        'canonical_native_backup_sha256':backup,'actual_completed_city_refs':city_refs,'archive_sources':archive_refs,'reserve_guard':reserve,
        'candidate_count':len(candidates),'retire_targets':len(retire),'ordinary_Container_reset_rows':len(reset),'exact_native_BE_before_rows':len(exact_rows),'held':holds,
        'protected39_full_after_points':len(protected_current)+len(retire),'normal_targets':len(adjacent)+len(retire),'native_actions':0,'construction_forbidden':True,
        'order':['Native full-class/full-tag before with exact_native_tags=true and exact expected row-count receipt required; then stock-before, ordinary sparse Items-empty delta, native empty-Items after','Native residual-before, admit AIR delta once, normal native neighbours, full actual39+AIR after, native map'],
        'no_mover_new_native_mode_or_entity_cleanup':True}
    ref=emit('manifest',manifest)
    return {'folder':str(out),'manifest_sha256':ref['sha256'],'candidates':len(candidates),'retire_targets':len(retire),'stock_rows':len(reset),'holds':holds,'native_actions':0,'counts':audit['counts']}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--home',type=Path,required=True);p.add_argument('--recovery-id',required=True);p.add_argument('--recovery-sha',required=True);a=p.parse_args()
    print(json.dumps(prepare(a.home,a.recovery_id,a.recovery_sha),indent=2))
