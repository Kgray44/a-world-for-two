"""Additive gravity-safe reroute; original refused868 stays immutable.

Paths change and the unplaced fish shed gains a dry west entry, retaining its
shutter, flower and all work furnishings. Every route/mount traces its actual gravel chain to native stable
substrate; water/AIR gaps are excluded, never filled or accepted as expected AIR.
"""
from __future__ import annotations
import argparse,hashlib,json,time
from collections import Counter
from pathlib import Path
from control_room.common import UserError,digest,read_json
from tools.artistic_tortuga_west_ground import workspaces,mask_inputs,path_to,PAVERS
from tools.artistic_ground_stability import natural_mount
from tools.artistic_create_substrate import verify_zinc_factory,qualified_mount
from tools.artistic_tortuga_headland_pair import COVERAGE
from tools.artistic_west_coverage import actual_geometry
from tools.artistic_north_bank_east import NorthTerrain,native_payload,GROUND,SOFT,NORTH_SOFT,AIR as VOIDS
from tools.artistic_west_r2_frontage import key
from tools.artistic_materials import require_material_rule,require_outdoor_rule
from tools.artistic_bridge_refinement import flatten
from tools.settlement_attractions import properties
from tools.artistic_zipline_catenary import reader_budget
from tools.playtest import guard

MIB=1024**2
LOCATOR=('staging/tortuga-west-ground-REFUSED-1793196291621555700/refusal-and-readonly-ground.json','8479d4f24bf53d2163ae584a8ae4f3a4913f81ba915fc27a2a2cf7e732a0b965')
NATIVE_REFUSAL=('dashboard/settlement/settlement-result-70826192-526a-43ed-8dd3-c48226ec95a5.json','fb4f8c78f6e4289e8beb0b3a9db0f1e1f9d2f97cc9971e389bea3588ffc7b3c1')
ORIGINAL=('staging/tortuga-west-ground-1793196333621516200/manifest.json','8fc3742481193d448fe54fc1886a466358c7dcd39a028e5994d3258ef649eb45')
UNSAFE_SIX={(1000,-1276),(1002,-1277),(1003,-1278),(1004,-1278),(1004,-1276),(1004,-1275)}
DEAD_CORAL={'minecraft:dead_'+kind+suffix for kind in('tube','brain','bubble','fire','horn')for suffix in('_coral','_coral_fan')}
ALTERNATE_CORRIDOR=(996,-1288,1012,-1277)
CONNECTIONS=(
 ('Hall left porch to shared northern trade hook',[(1037,-1276),(1036,-1273),(1022,-1273),(1021,-1283),(1021,-1292)]),
 ('Hall east flank to Salt and Petal',[(1037,-1276),(1053,-1275),(1061,-1275),(1061,-1291),(1064,-1291)]),
 ('Hall and repair court toward retained W3 bend',[(1037,-1276),(1053,-1275),(1068,-1275),(1070,-1261)]),
 ('Stable West quay and tiny raised timber link',[(988,-1272),(988,-1275),(997,-1280),(1003,-1281),(1011,-1281),(1021,-1283)]),
)


def revised_workspaces(registry):
    spaces=workspaces(registry);p=spaces[0]
    # The old southern exterior shoulder ends over unsupported gravel. Use
    # the real dry west shoulder instead, not a new floor over the wet gap.
    # This is an UNPLACED-source variant, never a move of live stored items.
    shutter=p.blocks[0,2,2];plant=p.blocks[0,1,3]
    p.put(0,2,2,'minecraft:air');p.put(0,1,3,'minecraft:air')
    p.put(0,1,1,'minecraft:dark_oak_planks',role='actual grounded full-block plant sill')
    p.put(0,2,1,plant,role='same contained red fern retained on a grounded sill')
    for z in range(5):p.beam(0,4,z,'z',wood='dark_oak',role='dry west entrance actual side-rafter tie between rooted corner posts')
    p.put(0,3,2,key(shutter),**properties(shutter),role='same weathered shutter mounted high under the real side rafter')
    p.route('Actual dry west entrance',[(0,1,2),(1,1,2),(2,1,2)],kind='floor')
    p.features[p.owner]+=['Unplaced-source west entry uses literal stable ground; original shutter and plant retained above/outside human headroom','No southern boardwalk or water-gap filling to hide unstable gravel']
    return spaces


def prepare(home,checkpoint_id,checkpoint_sha):
    home=Path(home).resolve();reserve=guard(8*MIB,64*MIB)
    if home.parent!=Path('D:/A World for Two/staging/world-tests').resolve():raise UserError('Private R2 source only')
    try:budgets=[reader_budget()]
    except UserError as exc:
        out=home/'staging'/('tortuga-west-ground-R2-REFUSED-'+str(time.time_ns()));out.mkdir()
        (out/'refusal.json').open('x',encoding='utf-8').write(json.dumps({'reason':str(exc),'reader_opened':False,'native_actions':0,'world_writes':0})+'\n')
        raise UserError(str(exc)+'; preserved '+str(out))from exc
    receipt=read_json(home/'dashboard/settlement/backup-receipt.json')
    if receipt.get('verified')is not True or(receipt.get('id'),receipt.get('sha256'))!=(checkpoint_id,checkpoint_sha)or'stopped'not in receipt.get('scope','').lower():raise UserError('Exact stopped R2 source checkpoint required')
    for rel,sha in(LOCATOR,NATIVE_REFUSAL,ORIGINAL):
        if digest(home/rel)!=sha:raise UserError('Retain exact original/failure/source locator evidence')
    source=read_json(home/LOCATOR[0])
    if(source['checkpoint_id'],source['checkpoint_sha256'])!=(checkpoint_id,checkpoint_sha):raise UserError('Locator belongs to a different stopped checkpoint')
    if len(source['qualified_columns_READONLY'])>6000:raise UserError('Finite original qualified locator exceeded')
    registry=read_json(home/'dashboard/settlement/registry.json');keep,forest,refs=mask_inputs(home)
    spaces=revised_workspaces(registry);delta={};tags={};main=set();features={}
    for p in spaces:
        require_material_rule(p.blocks,'UNCHANGED COMPLETE '+p.owner)
        for q,s in p.blocks.items():
            w=tuple(q[i]+p.origin[i]for i in range(3))
            if w in keep:raise UserError('Never move unchanged workspace into old/future source')
            delta[w]=s
        tags.update({tuple(q[i]+p.origin[i]for i in range(3)):s for q,s in p.tags.items()})
        main|={(x+p.origin[0],z+p.origin[2])for x,z in p.main[p.owner]};features[p.owner]=p.features[p.owner]
    zinc_proof=verify_zinc_factory(home)
    terrain=NorthTerrain(home,receipt,registry);free={};mounts={};rejected=[];before={};supports={};clearance={};routes=[];started=time.monotonic();coral_clearance=[];boardwalk={};board_columns=set()
    try:
        for i,row in enumerate(sorted(source['qualified_columns_READONLY'],key=lambda r:(r[0]//16,r[1]//16,r[0],r[1]))):
            x,z,old_floor,old_below,natural_y=row;floor=terrain.state(x,63,z);below=terrain.state(x,62,z)
            if floor!=old_floor or below!=old_below:raise UserError('Never silently rebind a changed saved locator cell')
            if(x,z)in UNSAFE_SIX:rejected.append({'xz':[x,z],'reason':'one of six proved source-water under unsupported gravel columns'});continue
            if(x,z)in forest or(x,z)in main:continue
            body=[terrain.state(x,y,z)for y in(64,65)]
            if any(s is None or key(s)not in VOIDS|SOFT|NORTH_SOFT or'waterlogged=true'in s for s in body):continue
            if any((x,y,z)in terrain.entities for y in(62,63,64,65)):continue
            mount=qualified_mount(terrain.state,x,z,zinc_proof)
            if not mount['stable']:rejected.append({'xz':[x,z],'reason':mount['reason'],'first_non_gravity':list(mount['first_non_gravity'])if'first_non_gravity'in mount else None});continue
            free[x,z]={'floor':floor,'body':body,'retained':key(floor)in PAVERS,'mount':mount};mounts[x,z]=mount
            if i%384==0:budgets.append(reader_budget())
            if time.monotonic()-started>90:raise UserError('Finite90s R2 substrate study exceeded')
        # A finite northern bypass may clear ordinary dry dead-coral cover,
        # not living/waterlogged coral, trees, authored plants or any BE. The
        # original locator excluded all such cover; it was never wet land.
        x0,z0,x1,z1=ALTERNATE_CORRIDOR
        for x in range(x0,x1+1):
            for z in range(z0,z1+1):
                if(x,z)in free or(x,z)in main|forest|UNSAFE_SIX:continue
                floor=terrain.state(x,63,z);body=[terrain.state(x,y,z)for y in(64,65)]
                if floor is None or key(floor)not in GROUND or any(s is None or key(s)not in VOIDS|SOFT|NORTH_SOFT|DEAD_CORAL or'waterlogged=true'in s for s in body):continue
                if any((x,y,z)in keep or(x,y,z)in terrain.entities for y in(62,63,64,65)):continue
                mount=qualified_mount(terrain.state,x,z,zinc_proof)
                if not mount['stable']:continue
                free[x,z]={'floor':floor,'body':body,'retained':False,'mount':mount};mounts[x,z]=mount
        # The failed original used a three-high/whole-column locator. Actual
        # public ground can also pass below an old eave, outside ALL old/new
        # main footprints, while retaining its exact low source AIR/pavers.
        # This finite ground-only read never relaxes a building plot rule.
        if digest(home/COVERAGE[0])!=COVERAGE[1]:raise UserError('Exact original main-footprint inventory required')
        source_main={tuple(q)for row in read_json(home/COVERAGE[0])['footprints'].values()for q in row['main_cells_xz']}
        pair_manifest='staging/tortuga-trade-pair-1793195118561023300/manifest.json'
        for stem in('crooked-iron','sounding-line'):keep.update(actual_geometry(home,pair_manifest,stem+'-PROPOSAL.json'))
        for x in range(978,1073):
            for z in range(-1310,-1249):
                if(x,z)in free or(x,z)in source_main|main|forest|UNSAFE_SIX:continue
                floor=terrain.state(x,63,z);body=[terrain.state(x,y,z)for y in(64,65)]
                if floor is None or key(floor)not in GROUND|VOIDS|PAVERS or'waterlogged=true'in floor:continue
                cover=VOIDS|SOFT|NORTH_SOFT|(DEAD_CORAL if 996<=x<=1012 and -1288<=z<=-1277 else set())
                if any(s is None or key(s)not in cover or'waterlogged=true'in s for s in body):continue
                if any((x,y,z)in terrain.entities for y in(62,63,64,65)):continue
                if(x,63,z)in keep and floor!=keep[x,63,z]:continue
                if any((x,y,z)in keep and(keep[x,y,z]!='minecraft:air'or s!='minecraft:air')for y,s in zip((64,65),body)):continue
                mount=qualified_mount(terrain.state,x,z,zinc_proof)
                if not mount['stable']:continue
                free[x,z]={'floor':floor,'body':body,'retained':key(floor)in PAVERS,'mount':mount};mounts[x,z]=mount
            if x%8==0:
                budgets.append(reader_budget())
                if time.monotonic()-started>90:raise UserError('Finite90s R2 literal public-ground study exceeded')
        # The stable two-wide ground components are genuinely disconnected.
        # A small raised wooden link spans a DIFFERENT northern cut without
        # targeting gravel63, water or any of the six native failed columns.
        # Its two ends have literal stable full substrate. Interior columns
        # are explicitly planned bridge geometry, NEVER labelled dry ground.
        for x in(1003,1004,1011,1012):
            for z in(-1281,-1280):
                if(x,z)not in free:raise UserError('Both complete2wide timber-link endpoints require qualified stable native ground')
                for xx,yy,zz,s in free[x,z]['mount']['stack']:supports[xx,yy,zz]=s
                supports[x,63,z]=terrain.state(x,63,z)
        for x in range(1003,1013):
            for z in(-1281,-1280):
                q=x,64,z;old=terrain.state(*q)
                if q in keep or q in terrain.entities or old is None or key(old)not in VOIDS|SOFT|NORTH_SOFT|DEAD_CORAL or'waterlogged=true'in old:raise UserError('Tiny link never overwrites an old structure, BE, unknown or water')
                boardwalk[q]=('minecraft:dark_oak_stairs[facing=east,half=bottom,shape=straight,waterlogged=false]'if x==1003 else
                              'minecraft:dark_oak_stairs[facing=west,half=bottom,shape=straight,waterlogged=false]'if x==1012 else'minecraft:dark_oak_planks')
                for y in(65,66):
                    value=terrain.state(x,y,z)
                    if value is None or key(value)not in VOIDS|SOFT|NORTH_SOFT or(x,y,z)in terrain.entities or(x,y,z)in keep:raise UserError('Raised timber-link headroom is not actual clear untargeted space')
                    before[x,y,z]=value;clearance[x,y,z]='minecraft:air'
                    if key(value)not in VOIDS:delta[x,y,z]='minecraft:air'
                board_columns.add((x,z))
                if(x,z)not in free:free[x,z]={'planned_bridge':True,'floor':None,'body':[],'retained':False,'mount':None}
        delta.update(boardwalk)
        used={};legs=[]
        for name,points in CONNECTIONS:
            anchors=[]
            for a,b in zip(points,points[1:]):
                try:leg=path_to(free,a,b)
                except UserError as exc:raise UserError('Stable route '+name+' '+str(a)+' -> '+str(b)+': '+str(exc))from exc
                anchors.extend(leg[:-1]);legs.append({'name':name,'from':list(a),'to':list(b),'length':len(leg)})
            anchors.append(points[-1]);cells=set()
            for x,z in anchors:cells|={(x,z),(x+1,z),(x,z+1),(x+1,z+1)}
            routes.append({'name':name,'width':2,'standing_positions':[[x+.5,65 if(x,z)in board_columns else 64,z+.5]for x,z in sorted(cells)],'cells_xz':[list(q)for q in sorted(cells)]})
            for i,(x,z)in enumerate(anchors):
                a=anchors[max(0,i-1)];b=anchors[min(len(anchors)-1,i+1)];axis='x'if abs(b[0]-a[0])>=abs(b[1]-a[1])else'z'
                for dx,dz in((0,0),(1,0),(0,1),(1,1)):used.setdefault((x+dx,z+dz),set()).add(axis)
        if set(used)&UNSAFE_SIX:raise UserError('The additive R2 must avoid all six failed columns')
        for(x,z),axes in sorted(used.items()):
            if(x,z)in board_columns:continue
            row=free[x,z]
            if not row['retained']:delta[x,63,z]='chipped:small_stone_bricks'if len(axes)>1 else'minecraft:andesite'if'x'in axes else'minecraft:cobblestone'
            else:supports[x,63,z]=row['floor']
            for y,s in zip((64,65),row['body']):
                q=x,y,z;before[q]=s;clearance[q]='minecraft:air'
                if key(s)not in VOIDS:
                    if q in keep:raise UserError('Retain shared authored walking AIR, never clear a protected target')
                    delta[q]='minecraft:air'
                    if key(s)in DEAD_CORAL:coral_clearance.append({'position':list(q),'exact_before':s,'after':'minecraft:air','scope':'Only unwaterlogged dead cover on proved stable dry bypass, outside all authored masks'})
            for xx,yy,zz,s in row['mount']['stack']:supports[xx,yy,zz]=s
        # These106 exact workspace floors stay unchanged and must pass the
        # stronger rule too, not just the rerouted street.
        for x,z in sorted(main):
            mount=qualified_mount(terrain.state,x,z,zinc_proof)
            if not mount['stable']:raise UserError('Unchanged workspace is not safely supported '+str((x,z,mount)))
            for xx,yy,zz,s in mount['stack']:supports[xx,yy,zz]=s
        for i,q in enumerate(sorted(delta,key=lambda q:(q[0]//16,q[2]//16,q[1],q[0],q[2]))):
            actual=terrain.state(*q)
            if actual is None or q in terrain.entities or key(actual)not in VOIDS|SOFT|GROUND|NORTH_SOFT|DEAD_CORAL or'waterlogged=true'in actual:raise UserError('Preserve actual current object/water/unknown/BE '+str((q,actual)))
            if q in keep:raise UserError('No current/future protected geometry may be written')
            before[q]=actual
            if i%512==0:budgets.append(reader_budget())
        sources=terrain.snapshot.sources
    except UserError as exc:
        out=home/'staging'/('tortuga-west-ground-R2-REFUSED-'+str(time.time_ns()));out.mkdir()
        diagnostic={'reason':str(exc),'checkpoint_id':checkpoint_id,'checkpoint_sha256':checkpoint_sha,'source_sha256':digest(Path(__file__)),
                    'stable_qualified_columns_READONLY':[[*q]for q in sorted(free)],'rejected_substrates':rejected,'native_actions':0,'world_writes':0,'reader_closed_by_finally':True}
        (out/'refusal.json').open('x',encoding='utf-8').write(json.dumps(diagnostic,separators=(',',':'))+'\n')
        raise UserError(str(exc)+'; preserved '+str(out))from exc
    finally:terrain.close()
    outdoor={q:s for q,s in delta.items()if(q[0],q[2])in used};rule=require_outdoor_rule(outdoor,'Entire stable crooked West R2 paths')
    full={**delta,**clearance,**supports}
    docs={'west-ground-R2-PROPOSAL.json':native_payload(registry,delta,checkpoint_sha,'TORTUGA WEST R2 — stable crooked lanes and three purposeful working sheds',tags=tags),
          'before-VERIFY-ONLY.json':native_payload(registry,before,checkpoint_sha,'VERIFY ONLY — exact R2 stopped preimage including retained two-high walking AIR'),
          'retained-stable-stacks-VERIFY-ONLY.json':native_payload(registry,supports,checkpoint_sha,'VERIFY ONLY — complete supported gravel stacks to non-falling native substrate'),
          'complete-after-VERIFY-ONLY.json':native_payload(registry,full,checkpoint_sha,'VERIFY ONLY — complete stable West R2 workspaces/paths and real two-high body',tags=tags),
          'normal-joins-SETTLE-ONLY.json':native_payload(registry,{q:s for q,s in delta.items()if key(s)not in VOIDS},checkpoint_sha,'NORMAL JOINS ONLY — stable R2, no original failed plan or inventory replay')}
    raw={}
    for n,d in docs.items():
        if n!='west-ground-R2-PROPOSAL.json':d.update(construction_forbidden=True,verification_only=True)
        raw[n]=(json.dumps(d,separators=(',',':'))+'\n').encode()
    manifest={'format':'awft-tortuga-west-ground-r2:1','checkpoint_id':checkpoint_id,'checkpoint_sha256':checkpoint_sha,'source_sha256':digest(Path(__file__)),
              'gravity_guard_source_sha256':digest(Path(__file__).with_name('artistic_ground_stability.py')),'frozen_original':ORIGINAL,'failed_native_original':NATIVE_REFUSAL,
              'original_868_modified_or_replayed':False,'original_workspace_source_sha256':digest(Path(__file__).with_name('artistic_tortuga_west_ground.py')),
              'explicit_unplaced_fish_shed_variant':'Same footprint/workfurniture; shutter raised under new side rafter, same potted fern on actual sill, west-entry aisle so no wet southern shoulder or new perimeter loop is needed',
              'workspace_scenes':features,'targets':len(delta),'path_columns':len(used),'two_wide_routes':routes,'route_legs':legs,'stable_candidate_columns':sum(not r.get('planned_bridge',False)for r in free.values()),'pinned_zinc_substrate_factory':zinc_proof,
              'explicit_new_small_boardwalk':{'floor_y':64,'actor_deck_feet_y':65,'deck_columns_xz':[list(q)for q in sorted(board_columns)],'end_stairs':[[1003,64,-1281],[1003,64,-1280],[1012,64,-1281],[1012,64,-1280]],'middle_ground_is_NOT_claimed_stable':True,'middle_gravel63_or_water_blocks_written':0,'native_stair_collision_walk_and_visual_acceptance':'PENDING'},
              'rejected_substrates':rejected,'native_failed_six_all_absent_from_targets':not any((q[0],q[2])in UNSAFE_SIX for q in delta),'exact_dry_dead_coral_clearance':coral_clearance,
              'complete_retained_stack_cells':len(supports),'all_old_future_custody':refs,'saved_sources':sources,'outdoor_rule':rule,'reserve_guard':reserve,
              'reader_peak_RSS_bytes':max(q['owned_reader_rss_bytes']for q in budgets),'files':{n:{'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}for n,b in raw.items()},
              'native_actions':0,'world_writes':0,'old_house_inventory_or_water_fill':0,'status':'NEW SOURCE/SAVED PREIMAGE ONLY; native fresh before/stable-stack checks, one placement, joins/fullverify and actual walking/images required',
              'causal_limits':['Saved unsupported gravel above source water is proved; actual native falling-entity events were not observed by this reader','Two-high clear body is not native model-overhang/collision acceptance','No current/future old stores, tags, doors or ownership are rewritten','Original failed868 and terminal70826192 stay immutable']}
    raw['manifest.json']=(json.dumps(manifest,separators=(',',':'))+'\n').encode()
    if sum(map(len,raw.values()))>64*MIB:raise UserError('Finite64MiB R2 output cap')
    out=home/'staging'/('tortuga-west-ground-R2-'+str(time.time_ns()));out.mkdir()
    for n,b in raw.items():(out/n).open('xb').write(b)
    return {'folder':str(out),'manifest_sha256':digest(out/'manifest.json'),'targets':len(delta),'path_columns':len(used),'rejected_substrates':len(rejected),'files':manifest['files'],'native_actions':0}


if __name__=='__main__':
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('--home',type=Path,required=True);a.add_argument('--checkpoint-id',required=True);a.add_argument('--checkpoint-sha',required=True);args=a.parse_args();print(json.dumps(prepare(args.home,args.checkpoint_id,args.checkpoint_sha),indent=2))
