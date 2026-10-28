"""Finite exact-binary cable route study. No native world calls or entity creation."""
from __future__ import annotations
import argparse, hashlib, json, math, subprocess, time
from pathlib import Path
from control_room.common import UserError, digest, read_json
from tools.artistic_south_extent import ExtentTerrain
from tools.artistic_south_forest import AIR
from tools.playtest import guard
import psutil

MIB=1024**2
HANG=3.5 # Derived anchor/deck feasible interval; current runtime43 is not changed.
CHECKPOINT="20261027T232720Z-8d0bc0"
CHECKPOINT_SHA="9bc10263e655b70468d9aad2a4b6787c7d50068f68b7292ef91e60757d627de8"
PROBE=Path("compat/proposals/zipline-graph-20261027T2315Z/ZiplineCurveProbe.java")
PROBE_SHA="e75f25bca0144553032afee9cbbb8c72ad62521b904fd4414216ecc84d1dce75"
# Exact block coordinates of NORTH-faced knots. These are proposed, not entities.
NODES=((1160,168,-760),(1168,159,-784),(1144,152,-840),(1128,150,-848),
       (1120,147,-864),(1120,146,-880),(1112,142,-920),(1088,132,-968),
       (1064,125,-1008),(1048,116,-1064),(1072,108,-1112),(1120,101,-1152),
       (1160,100,-1216),(1192,86,-1232),(1220,72,-1272))


def reader_budget():
    """Observed host/owned-reader ceiling; it is not a system-wide RAM quota."""
    available=psutil.virtual_memory().available
    if available <= 1536*MIB:
        raise UserError('Defer saved-MCA/probe work while available RAM is at or below1.5GiB')
    resident=psutil.Process().memory_info().rss
    if resident > 256*MIB:
        raise UserError('Owned saved-reader working set exceeds the reviewed256MiB bound')
    return {'available_bytes':available,'owned_reader_rss_bytes':resident}


def knot(block):
    if len(block)!=3 or any(type(n) is not int for n in block):raise UserError("Exact integer knot block required")
    return [block[0]+.5,block[1]+.5,block[2]+.25]


def swept_cells(points,hang=HANG):
    """Conservative union of consecutive 0.25m native samples, not a point ray."""
    if not 2<=len(points)<=321:raise UserError("Bounded complete native samples required")
    if not isinstance(hang,(int,float)) or not math.isfinite(hang) or not 2<=hang<=6:raise UserError("Explicit bounded synchronized hanging offset required")
    cells=set()
    for a,b in zip(points,points[1:]):
        if len(a)!=3 or len(b)!=3 or any(not math.isfinite(float(v)) for p in (a,b) for v in p):raise UserError("Finite native points required")
        if math.dist(a,b)>2:raise UserError("Discontinuous native curve samples")
        low=(min(a[0],b[0])-.55,min(a[1],b[1])-hang-.25,min(a[2],b[2])-.55)
        high=(max(a[0],b[0])+.55,max(a[1],b[1])-hang+1.8+.25,max(a[2],b[2])+.55)
        for x in range(math.floor(low[0]),math.ceil(high[0])):
            for y in range(math.floor(low[1]),math.ceil(high[1])):
                for z in range(math.floor(low[2]),math.ceil(high[2])):cells.add((x,y,z))
    if len(cells)>4096:raise UserError("Finite4096-cell span body envelope exceeded")
    return cells


def validate_nodes(nodes):
    if not 2<=len(nodes)<=17:raise UserError("At most16 actual local spans")
    anchors=[knot(p) for p in nodes]
    for a,b in zip(anchors,anchors[1:]):
        if not .01<=math.dist(a,b)<=80:raise UserError("Native provider span bound exceeded")
    turns=[]
    for a,b,c in zip(anchors,anchors[1:],anchors[2:]):
        u=[b[n]-a[n] for n in range(3)];v=[c[n]-b[n] for n in range(3)]
        angle=math.degrees(math.acos(max(-1,min(1,sum(u[n]*v[n] for n in range(3))/(math.dist(a,b)*math.dist(b,c))))))
        if angle>=45:raise UserError("Native graph handoff needs a turn strictly below45degrees")
        turns.append(angle)
    return anchors,turns


def spatial_custody(cells):
    """Conservative source envelopes, distinct from native moving collisions.

    The bridge rotates about X: its moving leaves cannot leave their X range.
    The complete guarded source bounds include the fixed bank rooms/towers and
    a more generous vertical extent than the55degree leaf arc. The flagship is
    the complete declared local hull/rig bounds transformed at1140/63/-1450.
    """
    envelopes = {
        'complete bascules/fixed banks plus conservative X-axis sweep':
            (1174, 38, -1208, 1233, 104, -1080),
        'stationary historical flagship including retained mast/rig allowance':
            (1117, 55, -1518, 1164, 136, -1400),
    }
    for name, (xa, ya, za, xb, yb, zb) in envelopes.items():
        if any(xa <= x < xb and ya <= y < yb and za <= z < zb for x, y, z in cells):
            raise UserError('Proposed cable/frame enters a retained source envelope: '+name)
    return {'source_envelopes': envelopes, 'source_spatial_intersections': 0,
            'source_sha256': {name: digest(Path(name)) for name in (
                'tools/artistic_bascules.py', 'tools/artistic_bridge_refinement.py',
                'tools/settlement_drawbridge.py', 'tools/artistic_ship.py')},
            'bridge_open_angle': 55, 'retained_flagship_upper_allowance_y': 136,
            'native_dynamic_collision_acceptance': False,
            'universal_vessel_clearance_or_static_ship_mobility': False}


def native_curves(home,out,nodes):
    if digest(PROBE)!=PROBE_SHA:raise UserError("Exact reviewed actual-binary curve probe required")
    args_path=home/"staging/zipline-graph-api-probe-20261027T2319Z/javac.args"
    args=args_path.read_text(encoding="utf-8").splitlines();cp=args[args.index("-classpath")+1].strip('"')
    classes=out/"classes";classes.mkdir()
    compile_args=["-proc:none","-implicit:none","--release","21","-classpath",cp,"-d",str(classes),str(PROBE.resolve())]
    argfile=out/"javac.args";argfile.write_text("\n".join('"'+a.replace('\\','/')+'"' if (' ' in a or ';' in a) else a for a in compile_args)+"\n",encoding="utf-8")
    build=subprocess.run(["javac","-J-Xmx256m","-J-XX:-UsePerfData","@"+str(argfile)],capture_output=True,timeout=30)
    if len(build.stdout)+len(build.stderr)>MIB:raise UserError("Finite compiler output exceeded")
    (out/"compile.log").write_bytes(build.stdout+build.stderr)
    if build.returncode:raise UserError("Actual binary curve probe compilation failed; log retained")
    anchors,turns=validate_nodes(nodes)
    request={"segments":[{"label":str(i),"a":a,"b":b,"slack":16} for i,(a,b) in enumerate(zip(anchors,anchors[1:]))]}
    src=out/"curve-input.json";src.write_text(json.dumps(request,separators=(',',':'))+"\n",encoding="utf-8")
    result=subprocess.run(["java","-Xmx256m","-XX:-UsePerfData","-classpath",str(classes)+";"+cp,"worldfortwo.presentation.ZiplineCurveProbe",str(src)],capture_output=True,timeout=30)
    (out/"curve.stderr.log").write_bytes(result.stderr[:MIB])
    if len(result.stdout)>MIB or len(result.stderr)>MIB or result.returncode:raise UserError("Exact native curve evaluation failed or exceeded finite output; failure retained")
    data=json.loads(result.stdout)
    if data.get("actual_pinned_ChainCable_math") is not True or data.get("worlds_or_entities_created")!=0 or data.get("native_world_route_acceptance") is not False or len(data.get("segments",[]))!=len(nodes)-1:raise UserError("Actual-binary curve result contract differs")
    (out/"native-curves.json").write_bytes(result.stdout)
    return data,turns


def prepare(home,nodes=NODES,*,reuse_frozen_curve=False,checkpoint_id=CHECKPOINT,checkpoint_sha=CHECKPOINT_SHA):
    home=Path(home).resolve()
    if not home.is_relative_to(Path(r"D:/A World for Two/staging/world-tests")):raise UserError("Owned saved-stage only")
    if tuple(nodes[-1])==(1220,72,-1272):raise UserError("Unbuilt routev1 is superseded; use the new western-town route, not the old endpoint")
    reserve=guard(MIB,16*MIB);reader_budget()
    out=home/"staging"/("zipline-native-catenary-study-"+str(time.time_ns()));out.mkdir()
    if reuse_frozen_curve:
        source=home/CURVE_EVIDENCE
        if digest(source/"manifest.json")!=CURVE_MANIFEST_SHA:raise UserError("Exact original native-binary curve receipt required")
        proof=read_json(source/"manifest.json")
        for name in ("native-curves.json","curve-input.json","saved-body-envelope.json"):
            row=proof["files"][name];path=source/name
            if path.stat().st_size!=row["bytes"]or digest(path)!=row["sha256"]:raise UserError("Original exact curve proof member changed")
        original=read_json(source/"saved-body-envelope.json")
        if original["nodes"]!=[list(q)for q in nodes]or original["probe_source_sha256"]!=PROBE_SHA:raise UserError("Reuse only the exact same native curve positions/probe")
        curves=read_json(source/"native-curves.json");_,turns=validate_nodes(nodes)
        for name in ("native-curves.json","curve-input.json"):(out/name).write_bytes((source/name).read_bytes())
        (out/"curve-reuse-provenance.json").write_text(json.dumps({"original_manifest_sha256":CURVE_MANIFEST_SHA,"native_curve_bytes_unchanged":True,"new_java_processes":0,"new_hang_offset":HANG,"old_hang_offset":original["hang_offset"]},indent=2)+"\n",encoding="utf-8")
    else:curves,turns=native_curves(home,out,nodes)
    registry=read_json(home/"dashboard/settlement/registry.json")
    terrain=ExtentTerrain(home,{"id":checkpoint_id,"sha256":checkpoint_sha,"verified":True},registry)
    try:
        segments=[];union=set()
        for i,row in enumerate(curves["segments"]):
            reader_budget()
            cells=swept_cells(row["points"]);union.update(cells);blockers=[];unknown=[]
            for q in sorted(cells):
                state=terrain.state(*q)
                if state is None:unknown.append(list(q))
                elif state.split('[')[0] not in AIR:blockers.append({"position":list(q),"state":state})
            segments.append({"index":i,"knot_blocks":[list(nodes[i]),list(nodes[i+1])],"length_3d":row["length"],"saved_envelope_cells":len(cells),"blockers":blockers,"unknown":unknown,"saved_conservative_AIR_pass":not blockers and not unknown})
        result={"format":"awft-proposed-native-catenary-saved-body:1","checkpoint_id":checkpoint_id,"checkpoint_sha256":checkpoint_sha,"nodes":[list(p) for p in nodes],"segments":segments,"actual_pinned_native_curve":True,"slack":16,"hang_offset":HANG,"player_width":.6,"player_height":1.8,"safety_margin":.25,"consecutive_sample_sweeps":True,"unique_saved_cells":len(union),"turn_degrees":turns,"all_saved_AIR_clear":all(s["saved_conservative_AIR_pass"] for s in segments),"native_world_collision_acceptance":False,"ride_or_remote_knot_loading_acceptance":False,"post_geometry_authority":False,"source_only":True,"reserve":reserve,"sources":terrain.snapshot.sources.copy(),"probe_source_sha256":PROBE_SHA,"curve_output_sha256":digest(out/"native-curves.json")}
    finally:terrain.close()
    raw=(json.dumps(result,separators=(',',':'))+"\n").encode()
    if len(raw)>4*MIB:raise UserError("Finite4MiB saved envelope output exceeded")
    (out/"saved-body-envelope.json").write_bytes(raw)
    meta={"format":"awft-proposed-cable-body-receipt:1","source_sha256":digest(Path(__file__)),"evidence_sha256":hashlib.sha256(raw).hexdigest(),"segments":len(segments),"all_saved_AIR_clear":result["all_saved_AIR_clear"],"native_actions":0,"world_writes":0,"files":{p.name:{"sha256":digest(p),"bytes":p.stat().st_size} for p in out.iterdir() if p.is_file()}}
    manifest=(json.dumps(meta,indent=2)+"\n").encode();(out/"manifest.json").write_bytes(manifest)
    return {"directory":str(out),"manifest_sha256":hashlib.sha256(manifest).hexdigest(),"all_saved_AIR_clear":result["all_saved_AIR_clear"],"segment_results":[{"index":s["index"],"blockers":len(s["blockers"]),"unknown":len(s["unknown"])} for s in segments]}


CURVE_EVIDENCE="staging/zipline-native-catenary-study-1793146468987836700"
CURVE_MANIFEST_SHA="0903a25ba2366e3d75e05105c8d10e7823cbe77d9060ebc1b21d22d4de5e5d75"


def frame(registry,terrain,block,body,protected,label):
    """A rooted timber portal with joined collars and a clear hanging flight."""
    from tools.artistic_spawn_plaza import state
    from tools.artistic_south_forest import GROUND,SOFT
    from tools.artistic_materials import require_material_rule
    x,y,z=block;failures=[]
    choices=((2,2),(3,3),(4,4),(2,3),(3,2),(2,4),(4,2),(2,5),(5,2),(3,4),(4,3))
    # Unequal rooted legs can straddle a retained native path without putting
    # a post on it. The longest continuous headstock remains at most9blocks.
    for left,right in choices:
      for axis in (0,2):
        radius=max(left,right)
        blocks={};roots={};valid=True;ornaments=[];omitted_ornaments=[]
        def ornament(name,cells):
            for q in cells:
                actual=terrain.state(*q)
                if (q[0],q[2])in protected or q in body or q in terrain.entities or actual is None or actual.split('[')[0]not in AIR|SOFT:
                    omitted_ornaments.append({'name':name,'reason':'retained site context or exact flight; core frame unchanged','position':list(q),'actual_saved_state':actual})
                    return
            blocks.update(cells);ornaments.append(name)
        for side in (-1,1):
            reach=left if side<0 else right
            dx,dz=(side*reach,0) if axis==0 else (0,side*reach)
            xx,zz=x+dx,z+dz;row=terrain.column(xx,zz)
            if (xx,zz) in protected or row['kind']!='dry' or row['state'].split('[')[0]not in GROUND or not 1<=y-row['surface_y']<=64:
                valid=False;break
            root=(xx,row['surface_y'],zz);roots[root]=row['state']
            for yy in range(root[1]+1,y+2):
                pos=xx,yy,zz;actual=terrain.state(*pos)
                if pos in body or actual is None or actual.split('[')[0]not in AIR|SOFT or pos in terrain.entities:
                    valid=False;break
                # Deliberate full join collars break the long structural upright.
                material='chipped:reinforced_stripped_spruce_log' if (yy-root[1])%4==0 else 'minecraft:stripped_spruce_log'
                blocks[pos]=state(registry,material,axis='y')
            if not valid:break
            blocks[xx,root[1]+1,zz]=state(registry,'minecraft:stone_bricks')
            # A real outboard tensioner hangs under a joined timber outrigger.
            # It is native chain block geometry, not a decorative loose item or
            # an uncreated Connectible Chains link.
            ox,oz=(xx+side,zz)if axis==0 else(xx,zz+side)
            tensioner={(ox,y+1,oz):state(registry,'minecraft:dark_oak_log',axis='x'if axis==0 else'z')}
            for yy in range(y-2,y+1):
                tensioner[ox,yy,oz]=state(registry,'minecraft:chain',axis='y',waterlogged=False)
            ornament('joined outboard native-chain tensioner '+str(side),tensioner)
            # Layered copper knee plates deliberately project from the two
            # collars rather than painting the full height with another stripe.
            for yy in (root[1]+3,y-3):
                plate={(ox,yy,oz):state(registry,'minecraft:weathered_cut_copper_stairs',
                    facing=('west'if side<0 else'east')if axis==0 else('north'if side<0 else'south'),
                    half='top',shape='straight',waterlogged=False)}
                ornament('copper collar knee '+str((side,yy)),plate)
            # A warm real lamp is seated on an actual outboard masonry shoe.
            lx,lz=xx+(side if axis==0 else 0),zz+(side if axis==2 else 0)
            support=terrain.column(lx,lz)
            if (lx,lz)not in protected and support['kind']=='dry' and support['state'].split('[')[0]in GROUND and abs(support['surface_y']-root[1])<=2:
                shoe=(lx,support['surface_y']+1,lz);lamp=(lx,support['surface_y']+2,lz)
                if all(q not in body and terrain.state(*q)is not None and terrain.state(*q).split('[')[0]in AIR|SOFT for q in (shoe,lamp)):
                    roots[lx,support['surface_y'],lz]=support['state']
                    blocks[shoe]=state(registry,'minecraft:chiseled_stone_bricks')
                    blocks[lamp]=state(registry,'minecraft:lantern',hanging=False,waterlogged=False)
        if not valid:failures.append({'axis':axis,'radius':radius,'reason':'actual root/body/soft-state/protection gate'});continue
        # Real transverse headstock carries the hanging native fence knot.
        for offset in range(-left,right+1):
            pos=(x+offset,y+1,z)if axis==0 else(x,y+1,z+offset)
            blocks[pos]=state(registry,'minecraft:stripped_dark_oak_log',axis='x'if axis==0 else'z')
        blocks[block]=state(registry,'minecraft:spruce_fence',north=False,south=False,east=False,west=False,waterlogged=False)
        # Periodic lower tie beams are retained only where the exact flight is
        # elsewhere. They are real connected structural ties, not random bands.
        common=max(q[1]for q in roots)
        omitted=[]
        for yy in range(common+5,y-3,6):
            line=[(x+o,yy,z)if axis==0 else(x,yy,z+o)for o in range(-left,right+1)]
            if any(q in body for q in line):omitted.append(yy);continue
            for q in line:blocks[q]=state(registry,'minecraft:dark_oak_log',axis='x'if axis==0 else'z')
        # Actual cap knees are outside the upper central hanging body.
        for side in (-1,1):
            reach=left if side<0 else right
            q=(x+side*(reach-1),y,z)if axis==0 else(x,y,z+side*(reach-1))
            if q not in body:
                blocks[q]=state(registry,'minecraft:dark_oak_stairs',facing=('east'if side<0 else'west')if axis==0 else('south'if side<0 else'north'),half='top',shape='straight',waterlogged=False)
        conflict=[]
        for q in blocks:
            actual=terrain.state(*q)
            if (q[0],q[2])in protected or q in body or q in terrain.entities or actual is None or actual.split('[')[0]not in AIR|SOFT:conflict.append(q)
        if conflict:failures.append({'axis':axis,'radius':radius,'reason':'actual exact full frame collision/protection','first':list(conflict[0])});continue
        check=require_material_rule(blocks,label+' complete rooted portal')
        features=['rooted masonry shoes','joined timber collars','full transverse headstock']+ornaments
        if any(v.startswith('minecraft:lantern[')for v in blocks.values()):features.append('low warm lamps')
        return blocks,roots,{'label':label,'anchor_block':list(block),'actual_NORTH_knot':knot(block),'support_axis':'x'if axis==0 else'z','radius':radius,'left_right_reaches':[left,right],'existing_paths_never_footing_targets':True,'retained_roots':[list(q)for q in sorted(roots)],'height_above_highest_root':y-common,'max_vertical_wood_run':3,'features':features,'optional_decor_omissions_preserving_context':omitted_ornaments,'deliberate_missing_tie_levels_for_flight':omitted,'material_rule':check,'no_climbing_or_boarding_access_claim':True,'rejected_frame_choices':failures}
    raise UserError('No actual dry rooted frame clear of flight/protected cells: '+str((label,failures)))


def prepare_frames(home,body_evidence,expected_manifest_sha256):
    raise UserError("Unbuilt v1 frame exporter is superseded; use the explicit western-town v2 producer")
    from tools.artistic_whole_bank_forest import protection
    from tools.artistic_spawn_plaza import payload
    from tools.artistic_materials import require_outdoor_rule
    home=Path(home).resolve()
    if not home.is_relative_to(Path(r"D:/A World for Two/staging/world-tests")):raise UserError("Owned saved-stage only")
    reserve=guard(MIB,16*MIB);reader_budget();evidence=Path(body_evidence).resolve()
    if not evidence.is_relative_to(home/'staging') or len(expected_manifest_sha256)!=64:raise UserError('Explicit owned exact body proof required')
    if digest(evidence/"manifest.json")!=expected_manifest_sha256:raise UserError('Exact immutable actual-binary curve receipt required')
    meta=read_json(evidence/"manifest.json")
    for name,row in meta['files'].items():
        p=evidence/name
        if p.stat().st_size!=row['bytes']or digest(p)!=row['sha256']:raise UserError('Exact curve member changed')
    curved=read_json(evidence/"native-curves.json");observed=read_json(evidence/"saved-body-envelope.json")
    if observed['nodes']!=[list(p)for p in NODES]or observed['hang_offset']!=HANG or observed['all_saved_AIR_clear']is not True:raise UserError('Complete unchanged exact-route and synchronized-hang air proof required')
    checkpoint_id,checkpoint_sha=observed['checkpoint_id'],observed['checkpoint_sha256']
    receipt=read_json(home/'dashboard/settlement/backup-receipt.json')
    if receipt.get('verified')is not True or(receipt.get('id'),receipt.get('sha256'))!=(checkpoint_id,checkpoint_sha):raise UserError('Requalify the native curve body against the exact latest stopped checkpoint before frames')
    body=set().union(*(swept_cells(r['points'])for r in curved['segments']))
    registry=read_json(home/"dashboard/settlement/registry.json");protected,custody=protection(home,registry)
    terrain=ExtentTerrain(home,{'id':checkpoint_id,'sha256':checkpoint_sha,'verified':True},registry)
    blocks={};roots={};details=[];before={};bodies={}
    try:
        for i,block in enumerate(NODES[1:-1],1):
            reader_budget()
            selected,retained,detail=frame(registry,terrain,block,body,protected,'Rigging portal '+str(i))
            if any(q in blocks and blocks[q]!=v for q,v in selected.items()):raise UserError('Distinct frame geometry overlaps')
            blocks.update(selected);roots.update(retained);details.append(detail)
        for q in blocks:
            before[q]=terrain.state(*q)
            if q in terrain.entities:raise UserError('Preserve every saved BE')
        for q in body:
            actual=terrain.state(*q)
            if actual is None or actual.split('[')[0]not in AIR:raise UserError('The exact complete body air proof no longer matches this saved checkpoint')
            bodies[q]=actual
        sources=terrain.snapshot.sources.copy()
    finally:terrain.close()
    if blocks.keys()&body:raise UserError('Authored frame intersects actual native curve/player envelope')
    navigation=spatial_custody(body|blocks.keys())
    check=require_outdoor_rule(blocks,'All authored zipline intermediate portal frames')
    prototype={q:v for q,v in blocks.items()if abs(q[0]-NODES[1][0])<=5 and abs(q[2]-NODES[1][2])<=5}
    docs={'frames-DELTA.json':payload(registry,checkpoint_sha,blocks,'PROPOSED rooted zipline portals; full route unqualified'),
          'frames-actual-BEFORE-VERIFY-ONLY.json':payload(registry,checkpoint_sha,before|roots,'VERIFY ONLY exact saved natural frame targets and retained roots',before=True),
          'roots-VERIFY-ONLY.json':payload(registry,checkpoint_sha,roots,'VERIFY ONLY retained natural dry frame supports',before=True),
          'flight-RESERVATION-ONLY.json':payload(registry,checkpoint_sha,bodies,'RESERVATION ONLY exact actual native-curve saved body AIR',before=True),
          'first-frame-VISUAL-PROTOTYPE.json':payload(registry,checkpoint_sha,prototype,'SOURCE ONLY first rooted frame visual prototype'),
          'first-frame-BEFORE-VERIFY-ONLY.json':payload(registry,checkpoint_sha,{q:before[q]for q in prototype},'VERIFY ONLY first frame targets',before=True)}
    for name in ('frames-DELTA.json','first-frame-VISUAL-PROTOTYPE.json'):docs[name]['construction_forbidden']=True
    recipe={'format':'awft-proposed-native-multispan-link-recipe:1','checkpoint_sha256':checkpoint_sha,'knot_blocks':[list(q)for q in NODES],'faces':['north']*len(NODES),'slack':16,'hang_offset_required':HANG,'maximum_adapter_span':80,'conservative_fresh_restart_preference':48,'segments_exceeding48m':[{'index':i,'length':r['length']}for i,r in enumerate(curved['segments'])if r['length']>48],'actual_bidirectional_restart_and_endpoint_loading':'PENDING; no idle forced chunks; independently observed real-rider remote knot readiness required','anchor_entities_created':0,'chain_items_consumed':0,'native_world_collision':'PENDING; source saved-AIR is distinct','route_native_placement_authority':False,'frames':details,'river_no_footings':True,'navigation':navigation}
    raw={n:(json.dumps(d,separators=(',',':'))+'\n').encode()for n,d in docs.items()};raw['native-link-recipe.json']=(json.dumps(recipe,indent=2)+'\n').encode()
    manifest={'format':'awft-rooted-zipline-frames-proposal:1','checkpoint_id':checkpoint_id,'checkpoint_sha256':checkpoint_sha,'source_sha256':digest(Path(__file__)),'curve_manifest_sha256':expected_manifest_sha256,'frame_count':len(details),'targets':len(blocks),'retained_actual_roots':len(roots),'body_saved_AIR_cells':len(body),'authored_frame_body_intersections':0,'protected_architecture_and_future_R5':custody,'outdoor_material_rule':check,'sources':sources,'reserve':reserve,'native_actions':0,'trees_removed':0,'BEs_or_inventories_changed':0,'source_visual_prototype_before_propagation':True,'files':{n:{'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)}for n,b in raw.items()}}
    raw['manifest.json']=(json.dumps(manifest,indent=2)+'\n').encode()
    if sum(map(len,raw.values()))>16*MIB:raise UserError('Finite16MiB frame output exceeded')
    out=home/'staging'/('zipline-rooted-frames-'+str(time.time_ns()));out.mkdir()
    for name,data in raw.items():(out/name).write_bytes(data)
    return {'directory':str(out),'manifest_sha256':digest(out/'manifest.json'),'targets':len(blocks),'frames':len(details),'body_cells':len(body),'frame_heights':[(r['label'],r['height_above_highest_root'])for r in details]}


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--home",type=Path,required=True);p.add_argument("--frames",action="store_true");p.add_argument("--body-evidence",type=Path);p.add_argument("--body-manifest-sha256");p.add_argument("--reuse-frozen-curve",action="store_true");p.add_argument('--checkpoint-id',default=CHECKPOINT);p.add_argument('--checkpoint-sha256',default=CHECKPOINT_SHA);a=p.parse_args()
    if a.frames and(not a.body_evidence or not a.body_manifest_sha256):p.error('--frames requires exact --body-evidence and --body-manifest-sha256')
    print(json.dumps(prepare_frames(a.home,a.body_evidence,a.body_manifest_sha256) if a.frames else prepare(a.home,reuse_frozen_curve=a.reuse_frozen_curve,checkpoint_id=a.checkpoint_id,checkpoint_sha=a.checkpoint_sha256),indent=2))
