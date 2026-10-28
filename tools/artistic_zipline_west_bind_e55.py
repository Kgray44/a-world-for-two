"""Fresh explicit stopped-checkpoint binding of unchanged western zipline v2.

No JVM, native command, current game read, geometry fit or entity creation. The
only new inventory is owner-authorized creative stock in a previously AIR cell.
"""
from __future__ import annotations
import argparse,hashlib,json,time
from pathlib import Path

from control_room.common import UserError,digest,read_json
from tools.artistic_bridge_refinement import flatten
from tools.artistic_north_bank_east import native_payload
from tools.artistic_south_extent import ExtentTerrain
from tools.artistic_south_forest import AIR,SOFT,GROUND
from tools.artistic_zipline_catenary import reader_budget,spatial_custody
from tools.artistic_materials import require_outdoor_rule,require_material_rule
from tools.artistic_rose_reach_botanical import ROSE,OTHER52
from tools.playtest import guard

MIB=1024**2
BASE='staging/zipline-west-v2-source-1793152099836099800'
MANIFEST_SHA='eba3d9d2223f110077926b79736b046713c58531e92d024ad76ed763d742a572'
GEOMETRY_SHA='339fb597c2a9e57f9bfd73be604eba1697b8a72b23ef51c99391516ffc691cf6'
NORTH=('staging/north-bank-residual-1793158994899675300/north-connected-columns-ONLY.json','594706123bb9ac14f447a8f95f810cf595c952f1d8edb1c6ebfba4ae54e5b103')
STOCK=(1101,65,-1257)
BARREL='minecraft:barrel[facing=south,open=false]'


def encoded(document):return (json.dumps(document,separators=(',',':'),ensure_ascii=False)+'\n').encode()


def geometry_digest(states):return hashlib.sha256(encoded([[*p,s] for p,s in sorted(states.items())])).hexdigest()


def new_stock_tag(actual,has_be,desired,items):
    if actual!='minecraft:air' or has_be or desired!=BARREL:raise UserError('Creative zipline stock requires a NEW exact AIR barrel target, never an existing BE/inventory')
    if items!={'minecraft:chain':14} or type(items.get('minecraft:chain')) is not int:raise UserError('Only the explicitly authorized fourteen creative construction chains may be initialized')
    name=json.dumps(json.dumps({'text':'Western zipline - creative construction chains'},separators=(',',':')))
    return '{CustomName:'+name+',Items:[{Slot:0b,id:"minecraft:chain",count:14}]}'


def check_fresh_target(pos,actual,has_be,authored):
    if actual is None or has_be or pos in authored or actual.split('[',1)[0] not in AIR|SOFT or 'waterlogged=true' in actual:
        raise UserError('Unchanged v2 target conflicts with actual FULL object/tree/BE/authored space '+str((pos,actual)))


def prepare(home,checkpoint_id,checkpoint_sha):
    home=Path(home).resolve();reserve=guard(MIB,8*MIB);started=time.monotonic()
    if home.parent!=Path('D:/A World for Two/staging/world-tests').resolve():raise UserError('Owned artistic private home required')
    receipt=read_json(home/'dashboard/settlement/backup-receipt.json')
    if receipt.get('verified') is not True or (receipt.get('id'),receipt.get('sha256'))!=(checkpoint_id,checkpoint_sha) or 'stopped' not in receipt.get('scope','').lower():raise UserError('Explicit exact current verified STOPPED checkpoint required; no live/crash fallback')
    out=home/'staging'/('zipline-west-v2-current-binding-'+str(time.time_ns()));out.mkdir()
    terrain=None;budgets=[];sources=[]
    try:
        budgets.append(reader_budget())
        registry=read_json(home/'dashboard/settlement/registry.json');base=home/BASE
        if 'minecraft:chain' not in registry['items']:raise UserError('The actual native chain item is unavailable')
        if digest(base/'manifest.json')!=MANIFEST_SHA:raise UserError('Exact original frozen v2 manifest changed')
        manifest=read_json(base/'manifest.json');roles=read_json(base/'source-roles-and-config.json');components={};all_states={}
        for filename,ref in manifest['files'].items():
            p=base/filename
            if not 0<p.stat().st_size<=MIB or digest(p)!=ref['sha256']:raise UserError('A frozen v2 source member changed')
        for component,sha in roles['component_geometry_sha256'].items():
            document=read_json(base/(component+'-DELTA.json'))
            if any(str(document[k])!=str(registry[k]) for k in ('seed','world_path')):raise UserError('Original v2 source belongs to another private world')
            values=flatten(document)
            if geometry_digest(values)!=sha or set(all_states)&set(values):raise UserError('Exact disjoint component geometry changed')
            components[component]=values;all_states.update(values)
        if len(all_states)!=1163 or geometry_digest(all_states)!=GEOMETRY_SHA or all_states.get(STOCK)!=BARREL:raise UserError('The1163-target v2 physical geometry or new stock location changed')
        authored=set();overlay_custody=[]
        for rel,sha in (ROSE,*OTHER52):
            p=home/rel
            if digest(p)!=sha:raise UserError('Exact retained town/52-house source changed')
            values=flatten(read_json(p));authored.update(set(values)&set(all_states))
            overlay_custody.append({'path':rel,'sha256':sha,'all_original_AIR_and_solids_considered':True})
        if authored:raise UserError('Original1163geometry intersects retained town source; no fitting or house movement allowed '+str(sorted(authored)[:8]))
        spatial=spatial_custody(all_states)
        if digest(home/NORTH[0])!=NORTH[1]:raise UserError('Exact historical northern village partition changed')
        north=set(map(tuple,read_json(home/NORTH[0])['connected_columns_xz']))
        terrain=ExtentTerrain(home,receipt,registry);before={};roots={};walk={};flight={};water_checks=[]
        for i,(p,desired) in enumerate(sorted(all_states.items())):
            actual=terrain.state(*p);check_fresh_target(p,actual,p in terrain.entities,authored);before[p]=actual
            if i%256==0:budgets.append(reader_budget())
            if time.monotonic()-started>120:raise UserError('Finite source reader exceeded120s; no retry/generation fallback')
        stock_tag=new_stock_tag(before[STOCK],STOCK in terrain.entities,all_states[STOCK],{'minecraft:chain':14})
        expected_roots=flatten(read_json(base/'all-retained-roots-VERIFY-ONLY.json'))
        for p,expected in expected_roots.items():
            actual=terrain.state(*p);column=terrain.column(p[0],p[2])
            if actual!=expected or p in terrain.entities or column['kind']!='dry' or column['surface_y']!=p[1] or actual.split('[',1)[0] not in GROUND:raise UserError('Retained exact dry support changed or is below water/canopy '+str((p,actual)))
            roots[p]=actual;water_checks.append({'support':list(p),'literal_actual_dry_surface':True,'historical_bank_class':'NORTH_CONNECTED' if (p[0],p[2]) in north else 'NOT_IN_NORTH_MASK_no_SOUTH_inference'})
        for label in ('cliff','western-town'):
            for row in roles['roles'][label]['actual_saved_threshold']:
                p=tuple(row[:3]);actual=terrain.state(*p)
                if actual!=row[3] or p in terrain.entities:raise UserError('Original station dry threshold/body changed; no source-only safe arrival claim')
                walk[p]=actual
        for p,expected in flatten(read_json(base/'flight-reservation-VERIFY-ONLY.json')).items():
            actual=terrain.state(*p)
            if actual is None or actual.split('[',1)[0] not in AIR or p in terrain.entities:raise UserError('Native-curve rider body is obstructed/unknown in the new checkpoint '+str((p,actual)))
            flight[p]=actual
        for component,values in components.items():require_material_rule(values,'Unchanged complete '+component)
        require_outdoor_rule(all_states,'Unchanged complete v2 physical architecture')
        budgets.append(reader_budget());sources=terrain.snapshot.sources
        documents={'physical1163-PROPOSAL.json':native_payload(registry,all_states,checkpoint_sha,'Unchanged western v2 physical1163; NEW creative14-chain barrel only',tags={STOCK:stock_tag}),
            'physical1163-before-VERIFY-ONLY.json':native_payload(registry,before,checkpoint_sha,'VERIFY ONLY fresh exact stopped physical preimages; no inventory overwrite'),
            'retained-dry-roots-VERIFY-ONLY.json':native_payload(registry,roots,checkpoint_sha,'VERIFY ONLY actual unchanged dry supports; no water/terrain fill'),
            'retained-entry-and-walk-VERIFY-ONLY.json':native_payload(registry,walk,checkpoint_sha,'VERIFY ONLY unchanged actual station thresholds/body; native walk still pending'),
            'fresh-flight-AIR-VERIFY-ONLY.json':native_payload(registry,flight,checkpoint_sha,'VERIFY ONLY actual FULL rider body AIR; not native dynamic collision acceptance'),
            'stock-before-AIR-VERIFY-ONLY.json':native_payload(registry,{STOCK:before[STOCK]},checkpoint_sha,'VERIFY ONLY new stock cell must still be AIR and BE-free'),
            'physical1163-after-with14stock-VERIFY-ONLY.json':native_payload(registry,all_states,checkpoint_sha,'VERIFY ONLY geometry plus fresh14chain inventory BEFORE future R4 debits',tags={STOCK:stock_tag}),
            'physical1163-geometry-VERIFY-ONLY.json':native_payload(registry,all_states,checkpoint_sha,'VERIFY ONLY same geometry without restocking; post-R4 inventory belongs to its real ledger')}
        raw={n:encoded(d) for n,d in documents.items()}
        report={'format':'awft-western-v2-current-checkpoint-binding:1','source_sha256':digest(Path(__file__)),'checkpoint_id':checkpoint_id,'checkpoint_sha256':checkpoint_sha,
            'original_manifest_sha256':MANIFEST_SHA,'unchanged_physical_geometry_sha256':geometry_digest(all_states),'targets':len(all_states),'components':list(components),
            'stock':{'position':list(STOCK),'before':'minecraft:air','saved_BE_present':False,'items':[{'slot':0,'id':'minecraft:chain','count':14}],
                'authority':'Owner-explicit CREATIVE CONSTRUCTION stock, not crafted or consumed','old_inventory_copied_or_modified':False,'initialization_once_only':True,
                'future_real_R4_cost':14,'future_native_UUID_knots':15,'R4_native_debit_or_graph_acceptance':False},
            'retained_support_count':len(roots),'station_threshold_cells':len(walk),'literal_fresh_flight_AIR_cells':len(flight),'dry_footing_water_exclusion_witnesses':water_checks,
            'northern_partition':{'path':NORTH[0],'sha256':NORTH[1],'meaning':'Historical preservation partition only; fresh exact dry supports above are authoritative, absence does not mean SOUTH'},
            'retained_town_source_custody':overlay_custody,'retained_source_intersections':0,'source_navigation_envelopes':spatial,'saved_sources':sources,
            'reader_peak_observed_RSS':max(b['owned_reader_rss_bytes'] for b in budgets),'reader_RAM_and_reserve_guards_are_not_OS_quotas':True,'reserve_guard':reserve,
            'native_actions':0,'world_writes':0,'new_JVMs':0,'native_graph_ride_survival_or_art_acceptance':False,
            'mandatory_later_gates':['KG must finish; exclusive empty private maintenance lease and fresh real native before/BE-absence/support/body checks','Place the1163-source once; verify actual stock14 before any R4 action','R4 must debit14 actual native items and create exactly15 actual owned UUID knots; no preexisting inventory overwritten','Normal support/state joins, bidirectional transfer, restart loading and real rider/fall-safety/art checks','After debit, never replay the placement or the with14stock verification as a restock operation'],
            'QA_limit':'Current QA0.1.6 pose maxZ-800 cannot view cliff startZ-760 or whole forest toZ-616. A separate strictly bounded QA0.1.7 proposal is required; no hot install or player motion here.',
            'files':{n:{'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)} for n,b in raw.items()}}
        raw['manifest.json']=encoded(report)
        if sum(map(len,raw.values()))>8*MIB:raise UserError('Finite current zipline binding output exceeded')
        for n,b in raw.items():(out/n).open('xb').write(b)
        return {'folder':str(out),'manifest_sha256':digest(out/'manifest.json'),'targets':len(all_states),'roots':len(roots),'flight_AIR':len(flight),'files':report['files'],'native_actions':0}
    except Exception as error:
        (out/'REFUSED.json').write_bytes(encoded({'format':'awft-zipline-binding-refusal:1','checkpoint_id':checkpoint_id,'checkpoint_sha256':checkpoint_sha,'reason':str(error),'native_actions':0,'no_geometry_adjustment_or_retry':True,'reserve_guard':reserve}))
        raise UserError('Unchanged zipline source refused; preserved '+str(out/'REFUSED.json')+': '+str(error)) from error
    finally:
        if terrain is not None:terrain.close()


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--home',type=Path,required=True);p.add_argument('--checkpoint-id',required=True);p.add_argument('--checkpoint-sha',required=True);a=p.parse_args();print(json.dumps(prepare(a.home,a.checkpoint_id,a.checkpoint_sha),indent=2))
