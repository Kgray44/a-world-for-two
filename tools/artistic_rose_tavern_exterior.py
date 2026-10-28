"""Two carved, truly projecting clerestory bays for the Drowned Rose.

Original exterior delta only. The complete accepted saved interior, sign, roof,
existing recessed windows, workstations, containers and ground routes stay put.
No native actions are performed by this source producer.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

from control_room.common import UserError,digest,utcnow
from tools.artistic_bridge_refinement import flatten
from tools.artistic_quay_prototype import bounded,context,write_bundle
from tools.artistic_materials import require_material_rule,require_outdoor_rule
from tools.artistic_spawn_plaza import payload,state
from tools.settlement_attractions import BackupWorld,base
from tools.playtest import guard

MIB=1024**2
BASES=(
 ('staging/artistic-pirate-spit-byte-slots-1793124362042040500/drowned-rose-VERIFY-ONLY.json','f646d9ed046f603dc4e55c3f564949dba3a45be733dbd8c88ebba9cf48d85486'),
 ('staging/artistic-maritime-depth-1793125315305851100/drowned-rose-depth.json','be443dbe28d6608a9348a58dcfb8b4b2766eea54ce47a690314f22f5c08b3b98'),
 ('staging/artistic-rose-furnishing-1793129631429439500/furnishing.json','7a4dd44e355b29d9587e6f609e12ce054139dd6565e58367cc371d0c221effe3'),
)
BAYS=((1295,1297),(1307,1309))
AIR='minecraft:air'


def design(registry):
    delta={};apertures=set();features=[]
    def put(x,y,z,name,**p):
        q=x,y,z;v=state(registry,name,**p)
        if q in delta and delta[q]!=v:raise UserError('Two exterior details conflict: '+str(q))
        delta[q]=v
    for first,last in BAYS:
        # Only the three-wide original green panel between retained timber
        # piers is opened. There is no cut in the accepted interior or roof.
        for x in range(first,last+1):
            for y in range(74,77):
                put(x,y,-1269,AIR);apertures.add((x,y,-1269))
                put(x,y,-1268,AIR)
                put(x,y,-1267,'mcwwindows:blackstone_brick_gothic',facing='south',open=False,
                    part='bottom'if y==74 else'top'if y==76 else'middle')
        # A true two-block-deep bay has side glazing, a supported timber floor,
        # carved outer jambs and a narrow modeled limestone/coppered hood.
        for x in range(first-1,last+2):
            for z in (-1268,-1267):
                put(x,73,z,'chipped:detailed_dark_oak_planks')
            put(x,77,-1267,'dawnoftimebuilder:limestone_bricks_edge',facing='south',half='top',shape='straight',waterlogged=False)
        for x in range(first,last+1):
            put(x,77,-1268,'minecraft:waxed_oxidized_cut_copper_slab',type='bottom',waterlogged=False)
        for x,face in ((first-1,'west'),(last+1,'east')):
            put(x,72,-1268,'mythrais:curved_corbel_dark_oak',facing='south',shape=0)
            for y in range(74,77):
                put(x,y,-1268,'mcwwindows:blackstone_brick_gothic',facing=face,open=False,
                    part='bottom'if y==74 else'top'if y==76 else'middle')
                part='lower'if y==74 else'upper'if y==76 else'middle'
                props={'facing':'south','colour':0}
                if part!='middle':props['mirrored']=False
                put(x,y,-1267,'mythrais:decorated_column_'+part+'_small_dark_oak',**props)
        features.append({'window_span':[first,last],'original_green_panel_z':-1269,'front_glazing_z':-1267,
                         'projection_blocks':2,'floor_y':73,'aperture_y':[74,76],
                         'composition':'Triple gothic lights, real glazed cheeks, carved timber floor/corbels/jambs, molded limestone brow and aged-copper rear cap; upper clerestory, not an invented accessible balcony'})
    return delta,apertures,features


def check_delta(original,delta,apertures,protected=()):
    for q,v in delta.items():
        if q in protected:raise UserError('Preserve every native furnishing/light/container BE')
        if q[2] < -1269 or q[1] < 72:
            raise UserError('Existing interior, sign and ground-level route are immutable')
        expected='minecraft:green_terracotta' if q in apertures else AIR
        if original.get(q)!=expected:
            raise UserError('Preserve original piers, roof, recessed window or existing exterior object: '+str((q,original.get(q))))
        if q in apertures and v!=AIR:raise UserError('The true window opening must be real AIR')
    return True


def model_envelopes(home):
    """Read actual pinned Mythrais models; export envelopes/hashes, not assets."""
    jars=list((home/'server/mods').glob('mythrais-*.jar'))
    if len(jars)!=1 or jars[0].stat().st_size>128*MIB:raise UserError('Exactly one bounded installed Mythrais JAR required')
    names=('curved_corbel_dark_oak','decorated_column_lower_small_dark_oak','decorated_column_middle_small_dark_oak','decorated_column_upper_small_dark_oak')
    result=[]
    with zipfile.ZipFile(jars[0])as archive:
        for name in names:
            bp='assets/mythrais/blockstates/'+name+'.json';raw=archive.read(bp)
            if len(raw)>MIB:raise UserError('Bounded blockstate metadata required')
            variants=json.loads(raw)['variants'];key=next(k for k in variants if 'facing=south'in k and ('shape='not in k or 'shape=0'in k) and ('mirrored='not in k or 'mirrored=false'in k) and ('colour='not in k or 'colour=0'in k))
            ref=variants[key];ref=ref[0]if isinstance(ref,list)else ref
            if ref.get('x',0)!=0 or ref.get('y',0)!=0:raise UserError('Review rotated southern model envelope explicitly')
            mp='assets/mythrais/models/'+ref['model'].split(':',1)[1]+'.json';model_raw=archive.read(mp)
            if len(model_raw)>MIB:raise UserError('Bounded original model metadata required')
            model=json.loads(model_raw);elements=model.get('elements',[])
            if not elements or len(elements)>512 or model.get('parent'):raise UserError('Review inherited or unbounded model geometry before claiming its envelope')
            lower=[min(min(e['from'][i],e['to'][i])for e in elements)for i in range(3)]
            upper=[max(max(e['from'][i],e['to'][i])for e in elements)for i in range(3)]
            # Small rotated carved elements can exceed this axis-aligned source
            # box slightly. The real native collision/art review remains a gate.
            if any(a < -4 or b > 20 for a,b in zip(lower,upper)):
                raise UserError('This decorative model exceeds its reviewed small one-voxel envelope')
            result.append({'block_id':'mythrais:'+name,'variant':key,'model':ref['model'],'model_sha256':hashlib.sha256(model_raw).hexdigest(),
                           'unrotated_element_bounds_in_sixteenths':[lower,upper],'element_count':len(elements),
                           'native_shape_or_art_acceptance':False})
    return {'installed_jar':jars[0].name,'sha256':digest(jars[0]),'models':result}


def prepare(home,output):
    reserve=guard(4*MIB,16*MIB);home,output,current,registry=context(home,output)
    coordinates=set();refs=[]
    for relative,expected in BASES:
        p=home/relative;d=bounded(p)
        if digest(p)!=expected:raise UserError('Exact accepted complete Drowned Rose source required')
        coordinates.update(flatten(d));refs.append({'relative':relative,'sha256':expected})
    models=model_envelopes(home);delta,apertures,features=design(registry)
    snapshot=BackupWorld(home,current,registry)
    try:
        # Every supplied original interior/furnishing/roof position is read from
        # the actual save, not restored from an old sparse conceptual template.
        original={q:snapshot.state(q)for q in coordinates|set(delta)}
        check_delta(original,delta,apertures,snapshot.protected)
        composite=dict(original);composite.update(delta)
        checks=[require_material_rule(composite,'COMPLETE Drowned Rose current interior/roof plus new oriels'),require_outdoor_rule(composite,'Complete ornate tavern exterior')]
        protected=[list(q)for q in sorted(snapshot.protected)if q in original]
        sources=snapshot.sources.copy()
    finally:snapshot.close()
    docs={'before-VERIFY-ONLY.json':payload(registry,current['sha256'],{q:original[q]for q in delta},'VERIFY ONLY exact original panels/AIR before Drowned Rose exterior correction',before=True),
          'exterior-PROPOSAL.json':payload(registry,current['sha256'],delta,'PROPOSAL ONLY Drowned Rose carved clerestory bays; accepted interior untouched'),
          'complete-after-VERIFY-ONLY.json':payload(registry,current['sha256'],composite,'VERIFY ONLY complete actual Drowned Rose plus exterior bays',before=True),
          'future-exterior-reservation-ONLY.json':payload(registry,current['sha256'],{q:AIR for q in delta},'RESERVATION ONLY future oriels, not observedAIR',before=True)}
    docs['exterior-PROPOSAL.json']['construction_forbidden']=True
    if bounded(home/'dashboard/settlement/backup-receipt.json').get('sha256')!=current['sha256']:raise UserError('Current checkpoint changed during the exact exterior read')
    return write_bundle(output,docs,{'format':'awft-drowned-rose-exterior:1','created':utcnow(),'source_sha256':digest(Path(__file__)),
        'checkpoint_id':current['id'],'checkpoint_sha256':current['sha256'],'original_sources':refs,'features':features,'actual_models':models,
        'targets':len(delta),'real_green_panel_aperture_cells':len(apertures),'unchanged_actual_BE_positions':protected,
        'interior_changes':0,'roof_changes':0,'existing_windows_or_sign_changes':0,'route_changes':0,'source_checks':checks,'saved_sources':sources,
        'construction_forbidden':True,'world_writes':0,'native_actions':0,'storage_guard':reserve,
        'next_gate':'Root current native BEFORE then explicitly admit exact delta once, normal joins, strict complete saved interior/roof/exterior verification; actual front/side/inside daylight/night review before acceptance'})


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('home','output'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();print(json.dumps(prepare(a.home,a.output),indent=2))
