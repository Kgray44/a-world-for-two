"""First tight new headland pair with an actual shared crooked walking lane.

Two different original recipes, not array replication. Source-only producer:
the parent owns current native before, placement, joins and real photo review.
"""
from __future__ import annotations
import argparse,hashlib,json,time
from pathlib import Path
from control_room.common import UserError,digest,read_json
from tools.artistic_tortuga_frontages import RECIPES,check,key,AIR
from tools.artistic_tortuga_west_ground import mask_inputs
from tools.artistic_bridge_refinement import flatten
from tools.artistic_north_bank_east import NorthTerrain,native_payload,GROUND,SOFT,NORTH_SOFT,AIR as VOIDS
from tools.artistic_materials import require_outdoor_rule
from tools.artistic_ground_stability import natural_mount
from tools.artistic_zipline_catenary import reader_budget
from tools.playtest import guard

MIB=1024**2
COVERAGE=('staging/tortuga-west-residual-coverage-1793197194074495100/coverage-READONLY.json','25447b785ddbc2f64f0b0dbb9aeed74115cc46ce20ad58030ccf026d6621b2d9')
GROUND_CONTEXT=('staging/tortuga-west-ground-1793196333621516200/full-after-and-walkclearance-VERIFY-ONLY.json','6641639a895a30e86e068b5a4171093adc90517aad92ffcc109e2086556f1274')
PARCELS=(('tideglass',(1036,63,-1310)),('thimble-salt',(1046,63,-1308)))


def construct(registry):
    states={};tags={};buildings=[];mains=set()
    for recipe,origin in PARCELS:
        p=RECIPES[recipe](registry);proof=check(p)
        world={tuple(q[i]+origin[i]for i in range(3)):s for q,s in p.blocks.items()}
        conflicts=[q for q,s in world.items()if q in states and not(s==AIR and states[q]==AIR)]
        if conflicts:raise UserError('Individually composed headland masses conflict; do not silently crop '+str(conflicts[:5]))
        states.update(world);tags.update({tuple(q[i]+origin[i]for i in range(3)):v for q,v in p.tags.items()})
        fields={(x+origin[0],z+origin[2])for x,z in p.main[p.owner]};mains|=fields
        buildings.append({'recipe':recipe,'name':p.owner,'origin':list(origin),'proof':proof,'main_columns_xz':[list(q)for q in sorted(fields)],
                          'rooms':[{**r,'world_standing_point':[r['standing_point'][i]+origin[i]for i in range(3)]}for r in p.rooms],
                          'entries':[{**r,'world_door':[r['door'][i]+origin[i]for i in range(3)],'world_threshold':[r['outside_step'][i]+origin[i]for i in range(3)]}for r in p.entries]})
    lane={(x,z)for x in(1044,1045)for z in range(-1309,-1296)}
    lane|={(x,z)for x in range(1039,1046)for z in(-1298,-1297)}
    for x,z in lane:
        if(x,z)in mains:raise UserError('Never pave across a real main footprint')
        for y in(64,65):
            if states.get((x,y,z),AIR)!=AIR:raise UserError('The real two-wide lane is pinched by an authored fixture '+str((x,y,z,states[x,y,z])))
        states[x,63,z]='minecraft:cobblestone'if z<-1298 else'chipped:small_stone_bricks'
    return states,tags,buildings,mains,lane


def prepare(home,checkpoint_id,checkpoint_sha):
    home=Path(home).resolve();reserve=guard(8*MIB,32*MIB)
    if home.parent!=Path('D:/A World for Two/staging/world-tests').resolve():raise UserError('Private headland source only')
    try:budgets=[reader_budget()]
    except UserError as exc:
        out=home/'staging'/('tortuga-headland-pair-REFUSED-'+str(time.time_ns()));out.mkdir()
        (out/'refusal.json').open('x',encoding='utf-8').write(json.dumps({'reason':str(exc),'reader_opened':False,'native_actions':0,'world_writes':0,'reserve_guard':reserve})+'\n')
        raise UserError(str(exc)+'; refused receipt preserved '+str(out))from exc
    receipt=read_json(home/'dashboard/settlement/backup-receipt.json')
    if receipt.get('verified')is not True or(receipt.get('id'),receipt.get('sha256'))!=(checkpoint_id,checkpoint_sha)or'stopped'not in receipt.get('scope','').lower():raise UserError('Exact current stopped checkpoint required')
    registry=read_json(home/'dashboard/settlement/registry.json');states,tags,buildings,mains,lane=construct(registry)
    for rel,sha in(COVERAGE,GROUND_CONTEXT):
        if digest(home/rel)!=sha:raise UserError('Frozen current residual/ground proof changed')
    coverage=read_json(home/COVERAGE[0])
    if(coverage['checkpoint_id'],coverage['checkpoint_sha256'])!=(checkpoint_id,checkpoint_sha):raise UserError('Residual-body proof is bound to another checkpoint')
    free={tuple(r[:2])for r in coverage['eligible_columns_READONLY']}
    if not mains|lane<=free:raise UserError('No guessed or interpolated plot/path footing')
    keep,forest,refs=mask_inputs(home);keep.update(flatten(read_json(home/GROUND_CONTEXT[0])))
    if any(q in keep for q in states):raise UserError('No new target may replace protected old/future source, AIR, stock or flight')
    if(mains|lane)&forest:raise UserError('Preserve whole native forest growth fields')
    terrain=NorthTerrain(home,receipt,registry);before={};supports={};clearance={};sources=[];started=time.monotonic()
    try:
        for x,z in sorted(mains|lane):
            col=terrain.column(x,z);below=terrain.state(x,62,z)
            if col['kind']!='dry'or col['surface_y']not in(62,63)or below is None or key(below)not in GROUND:raise UserError('Actual complete main/path footing is not dry and supported '+str((x,z,col)))
            mount=natural_mount(terrain.state,x,z)
            if not mount['stable']:raise UserError('Never build/pave over unsupported falling coastal material '+str((x,z,mount)))
            for xx,yy,zz,s in mount['stack']:
                if(xx,yy,zz)in terrain.entities:raise UserError('Never use an existing BE as new construction footing')
                supports[xx,yy,zz]=s
        for i,q in enumerate(sorted(states,key=lambda q:(q[0]//16,q[2]//16,q[1],q[0],q[2]))):
            old=terrain.state(*q)
            if old is None or q in terrain.entities or key(old)not in VOIDS|SOFT|GROUND|NORTH_SOFT or'waterlogged=true'in old:raise UserError('Preserve actual current object, water, unknown or BE '+str((q,old)))
            before[q]=old
            if i%512==0:budgets.append(reader_budget())
            if time.monotonic()-started>75:raise UserError('Finite75s complete headland preimage reader exceeded')
        for x,z in lane:
            for y in(64,65):
                q=x,y,z;old=terrain.state(*q)
                if old is None or key(old)not in VOIDS|SOFT|NORTH_SOFT or'waterlogged=true'in old or q in terrain.entities:raise UserError('Real shared lane body blocked '+str((q,old)))
                clearance[q]=AIR
                before[q]=old
                if key(old)not in VOIDS:states[q]=AIR
        sources=terrain.snapshot.sources
    except UserError as exc:
        out=home/'staging'/('tortuga-headland-pair-REFUSED-'+str(time.time_ns()));out.mkdir()
        (out/'refusal.json').open('x',encoding='utf-8').write(json.dumps({'reason':str(exc),'checkpoint_id':checkpoint_id,'checkpoint_sha256':checkpoint_sha,
          'source_sha256':digest(Path(__file__)),'reader_closed_by_finally':True,'native_actions':0,'world_writes':0,'partial_native_request_emitted':False})+'\n')
        raise UserError(str(exc)+'; refused receipt preserved '+str(out))from exc
    finally:terrain.close()
    outdoor={q:s for q,s in states.items()if(q[0],q[2])in lane}
    outdoor_rule=require_outdoor_rule(outdoor,'Entire crooked two-wide headland lane')
    full={**states,**supports,**clearance}
    docs={'headland-pair-PROPOSAL.json':native_payload(registry,states,checkpoint_sha,'TORTUGA — Tideglass and Thimble shared crooked headland',tags=tags),
          'before-VERIFY-ONLY.json':native_payload(registry,before,checkpoint_sha,'VERIFY ONLY — exact current dry/cover/AIR before headland pair'),
          'retained-supports-VERIFY-ONLY.json':native_payload(registry,supports,checkpoint_sha,'VERIFY ONLY — all literal dry headland footings, no water fill'),
          'complete-after-VERIFY-ONLY.json':native_payload(registry,full,checkpoint_sha,'VERIFY ONLY — complete furnished pair, real floors and shared two-high lane',tags=tags),
          'normal-joins-SETTLE-ONLY.json':native_payload(registry,{q:s for q,s in states.items()if key(s)not in VOIDS},checkpoint_sha,'NORMAL JOINS ONLY — headland pair source, no stored inventory replay')}
    raw={}
    for name,doc in docs.items():
        if name!='headland-pair-PROPOSAL.json':doc.update(construction_forbidden=True,verification_only=True)
        raw[name]=(json.dumps(doc,separators=(',',':'))+'\n').encode()
    manifest={'format':'awft-tortuga-headland-pair:1','checkpoint_id':checkpoint_id,'checkpoint_sha256':checkpoint_sha,'source_sha256':digest(Path(__file__)),'recipe_source_sha256':digest(Path(__file__).with_name('artistic_tortuga_frontages.py')),
              'buildings':buildings,'actual_main_columns':len(mains),'shared_two_wide_lane_columns':len(lane),'targets':len(states),'literal_retained_supports':len(supports),'substrate_source_sha256':digest(Path(__file__).with_name('artistic_ground_stability.py')),
              'standing_lane_columns_xz':[list(q)for q in sorted(lane)],'outdoor_rule':outdoor_rule,'existing_future_custody':refs,'raw_saved_sources':sources,
              'reserve_guard':reserve,'reader_peak_RSS_bytes':max(r['owned_reader_rss_bytes']for r in budgets),'new_default_BEs_only_no_Items_or_owner_forged':True,
              'native_cameras':[{'name':'real two-wide shared lane','feet':[1044.5,64,-1303.5],'look_at':[1048,66,-1304]},
                                {'name':'broad glass front and smaller offset neighbour','feet':[1040.5,64,-1297.5],'look_at':[1043,68,-1303]},
                                {'name':'Tideglass actual workroom','feet':[1039.5,64,-1303.5],'look_at':[1037,65,-1307]},
                                {'name':'Thimble actual working nook','feet':[1049.5,64,-1302.5],'look_at':[1047,65,-1305]},
                                {'name':'Thimble real upper home','feet':[1049.5,68,-1302.5],'look_at':[1047,69,-1304]}],
              'files':{n:{'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}for n,b in raw.items()},'native_actions':0,'world_writes':0,'old_geometry_or_inventory_removal':0,
              'limits':['Exact stopped/source only; fresh native before and support checks, placement, ordinary joins, strict full state/NBT check and actual views required','Two-high literal lane is not native model collision acceptance; glass/fixture models still need real walking','The wider western bank remains incomplete; this is one tightly composed pair, not a whole-town completion claim']}
    raw['manifest.json']=(json.dumps(manifest,separators=(',',':'))+'\n').encode()
    if sum(map(len,raw.values()))>32*MIB:raise UserError('Finite32MiB headland output cap')
    out=home/'staging'/('tortuga-headland-pair-'+str(time.time_ns()));out.mkdir()
    for n,b in raw.items():(out/n).open('xb').write(b)
    return {'folder':str(out),'manifest_sha256':digest(out/'manifest.json'),'targets':len(states),'rooms':sum(len(b['rooms'])for b in buildings),'files':manifest['files'],'native_actions':0}


if __name__=='__main__':
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('--home',type=Path,required=True);a.add_argument('--checkpoint-id',required=True);a.add_argument('--checkpoint-sha',required=True);args=a.parse_args();print(json.dumps(prepare(args.home,args.checkpoint_id,args.checkpoint_sha),indent=2))
