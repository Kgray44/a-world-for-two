"""Prepare world-specific Lumiera camera scenes without activating or moving players.

The first-join scene stays near the permanent plaza. Castle, port and individual
ship replays have separate nearby-player preconditions, because Lumiera's camera
packet does not stream distant world chunks. All output stays in owned staging.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import subprocess
import time
import zipfile
from pathlib import Path

from control_room.common import Layout, REPO, UserError, atomic_write, digest, read_json, utcnow
from control_room.storage import Storage
from tools.settlement_live import native_read


LUMIERA_FILE = 'lumiera-neoforge-1.21.1-1.0.0-alpha.1.jar'
LUMIERA_SHA256 = 'dadfcaab4fe335792f84b18d0f7d7ab499d54128c92f44cd25584aeff3f398d9'
CASTLE_SHA = '67f1bd76c75e2c66e4dd6586bb1546a52f20b3d39b00bb37227c00b0a8d1f8d5'
CORE_SHA = '45e88a165ed60ce438ec5d87094ed476faeebdaa68693ae6d1835a11eeea6aeb'
PORT_SHA = '3bcc8f6bdfaf4d4ff44805e9fc5e5dee1b5b8b07d50916dba04af20a67ba72ba'
DRAWBRIDGE_SHA = 'cc2bd89a14d86fc1de2236e5a4f92ca523d911bc128fcf96f91c1e6101fb8b69'
SOUTH_SHA = '08b57f7489876add7477597a09d12315b8dbfbe2b8edf87eefee5bc87a7e4371'
ACCESS_SHA = 'e31b6d4782283b66219c551c3a345bb361ecafa0ab313340e0a767322beaa908'
SHIP_SHAS = {
    'rosewater-resolute': 'c612729b69ef8d3a71faf1f56996b6ab6cd57c68adbe8fbb7c0cfbeb8e5fbc84',
    'amberwake': 'f3fdaea349ea101e0e1868d4522505e2302c0971e439de5279e0f58f7a0ef115',
    'nightingales-debt': '8552b39eca0f40eb9ab4a4357b223e52939a49fd7714ae28fc7cc5208938d235',
    'sea-lavender': '3d7129b42b6dcee83c860a0db9bfbfcdbab1c7183c31c5bef6d0c3a99042fdd7',
}
FIRST_JOIN = 'awft:settlement_intro'
SPAWN = (1120.5, 67.0, -1130.5)
MAX_OUTPUT = 16 * 1024**2
JDK = Path(r'C:\Program Files\Java\jdk-21.0.10\bin')


def look_rotation(position, target, previous=None):
    dx, dy, dz = (target[n]-position[n] for n in range(3))
    if dx*dx+dz*dz < .000001:
        yaw = previous if previous is not None else 0.0
    else:
        yaw = math.degrees(math.atan2(-dx, dz))
    if previous is not None:
        yaw = previous+(yaw-previous+180) % 360-180
    pitch = -math.degrees(math.atan2(dy, math.hypot(dx, dz)))
    return {'yaw': round(yaw, 5), 'pitch': round(pitch, 5), 'roll': 0.0}


def interpolate_track(knots, step=.5):
    """Author smooth positions into dense native LINEAR points, avoiding overshoot.

    Timed cubic Hermite interpolation is an offline authoring step. Minecraft and
    Lumiera still perform all actual camera playback. Every resulting straight
    segment is included in the block-clearance and view-envelope checks.
    """
    def tangent(index, column):
        if index in (0, len(knots)-1):
            return [0.0]*3
        before, after = knots[index-1], knots[index+1]
        return [(after[column][n]-before[column][n])/(after[0]-before[0]) for n in range(3)]
    times = sorted({round(n*step, 6) for n in range(round(knots[-1][0]/step)+1)}
                   | {row[0] for row in knots})
    samples = []
    index = 0
    previous_yaw = None
    for at in times:
        while index+1 < len(knots)-1 and at > knots[index+1][0]:
            index += 1
        first, last = knots[index], knots[index+1]
        span = last[0]-first[0]
        u = (at-first[0])/span
        h00, h10, h01, h11 = 2*u**3-3*u**2+1, u**3-2*u*u+u, -2*u**3+3*u*u, u**3-u*u
        values = []
        for column in (1,2):
            a, b = tangent(index,column), tangent(index+1,column)
            values.append([h00*first[column][n]+h10*span*a[n]+h01*last[column][n]+h11*span*b[n]
                           for n in range(3)])
        position, target = values
        rotation = look_rotation(position,target,previous_yaw)
        previous_yaw = rotation['yaw']
        fov = first[3]+(last[3]-first[3])*(u*u*(3-2*u))
        samples.append({'time':at,'pos':dict(zip(('x','y','z'),(round(v,5) for v in position))),
                        'rot':rotation,'fov':round(fov,4),'pathType':'linear',
                        'posTime':'linear','rotTime':'linear','fovTime':'linear'})
    return samples


def scene(ident, title, knots, player_center, features, *, first_join=False):
    duration = round(knots[-1][0]*20)
    if not (300 <= duration <= 500 if first_join else 100 <= duration <= 600):
        raise UserError('Cinematic length exceeds its reviewed limit')
    frames = interpolate_track(knots)
    center_x, center_y, center_z = player_center
    camera_range = max(math.hypot(p['pos']['x']-center_x,p['pos']['z']-center_z) for p in frames)
    target_range = max(math.hypot(row[2][0]-center_x,row[2][2]-center_z) for row in knots)
    radius = 4 if first_join else 16
    if max(camera_range,target_range)+radius > 91:
        raise UserError('Camera or look target exceeds the conservative six-chunk envelope: '+ident)
    data = {'schema':1,'id':ident,'duration_ticks':duration,'camera_position_mode':'absolute',
            'settings':{'fade_in':True,'fade_out':True,'hide_ui':True,'letterbox':True,
                        'fade_duration_ticks':12,'letterbox_duration_ticks':10},
            'keyframes':frames,'events':[
                {'tick':4,'type':'lumiera:play_sound','sound':'minecraft:block.amethyst_block.chime',
                 'source':'ambient','volume':.15,'pitch':.9,'relative_to_camera':True},
                {'tick':max(30,duration-150),'type':'lumiera:show_text','text':title,
                 'preset':'TITLE','duration':90},
            ]}
    contract = {'id':ident,'duration_seconds':duration/20,'features':list(features),
                'first_join_candidate':first_join,'dimension':'minecraft:overworld',
                'player_center':list(player_center),'maximum_player_horizontal_distance':radius,
                'maximum_player_vertical_distance':16,
                'minimum_server_view_distance_chunks':6,'minimum_client_render_distance_chunks':6,
                'maximum_camera_horizontal_distance_from_center':round(camera_range,3),
                'maximum_look_target_distance_from_center':round(target_range,3),
                'nearby_playback_only':True,'automatic_location_trigger_enabled':False,
                'settings_are_recommendations_only':True,
                'real_render_and_packet_coverage':'pending',
                'camera_mode':'ABSOLUTE; native camera only, no player teleport'}
    return data, contract


def scenes(vessels):
    result = []
    result.append(scene(FIRST_JOIN,'A World for Two',[
        (0,(1154,109,-1160),(1155,76,-1090),70),
        (3,(1176,103,-1134),(1165,77,-1083),66),
        (6,(1175,99,-1102),(1165,76,-1083),64),
        (9,(1148,103,-1078),(1096,74,-1056),68),
        (12,(1103,103,-1072),(1120,71,-1120),68),
        (15,(1072,101,-1118),(1120,73,-1130),68),
        (18,(1090,98,-1172),(1170,78,-1190),70),
        (21,(1127,86,-1168),(1120,69,-1130),67),
        (23.5,(1120.5,68.62,-1130.5),(1120.5,68.62,-1110.5),70),
        (24,(1120.5,68.62,-1130.5),(1120.5,68.62,-1110.5),70),
    ],SPAWN,['Actual cottage','Garden-facing village view','Welcome plaza','Near-bank pirate-port approach'],first_join=True))
    result.append(scene('awft:rosewater_castle_tour','Rosewater Castle',[
        (0,(1185,116,-1041),(1211,84,-1008),67),
        (4,(1216,127,-1040),(1248,94,-1007),66),
        (8,(1270,132,-1020),(1224,91,-990),69),
        (12,(1282,128,-971),(1220,84,-973),70),
        (16,(1247,113,-938),(1218,85,-986),67),
        (20,(1205,109,-954),(1211,85,-1008),68),
    ],(1221,68,-996),['Preserved keep','Library and ballroom wings','Tall observatory',
                     'Rose Court','Gardens and southern gate']))
    result.append(scene('awft:lanternwater_port_tour','Lanternwater',[
        (0,(1080,105,-1205),(1145,77,-1202),70),
        (4,(1105,110,-1265),(1158,77,-1206),67),
        (8,(1160,111,-1267),(1170,77,-1220),68),
        (12,(1175,105,-1220),(1138,77,-1203),67),
        (16,(1144,99,-1183),(1133,76,-1225),70),
        (18,(1128,96,-1210),(1145,76,-1210),70),
    ],(1120,66,-1218),['Actual pirate quarter','Tavern and waterfront','Quays and finger-pier approach']))
    for vessel in vessels:
        spec = vessel['ship']
        cx,cz = spec['center']; beam,length = spec['beam'],spec['length']
        top = max(y for x,y,z,i in vessel['_plan']['blocks'])
        side = beam/2+22
        ident = 'awft:'+spec['slug'].replace('-','_')+'_tour'
        result.append(scene(ident,spec['name'],[
            (0,(cx-side,top+7,cz-length/2-9),(cx,79,cz-12),68),
            (4,(cx-side-2,top+2,cz-length/4),(cx,76,cz),67),
            (8,(cx-side-2,top+5,cz+length/4),(cx,78,cz+12),66),
            (12,(cx,top+13,cz+length/2+12),(cx,78,cz+10),69),
            (18,(cx+side-1,top+10,cz+8),(cx,84,cz),68),
        ],(cx,vessel['deck_levels']['main']+1,cz),
           [spec['role'],spec['sail_state']+' original rig','Hull and cabin exterior','Deck silhouette']))
    return result


def require_plan(path, expected=None):
    if not path.is_file() or path.stat().st_size > 32*1024**2:
        raise UserError('A bounded construction plan is missing: '+path.name)
    if expected is not None and digest(path) != expected:
        raise UserError('A construction plan hash changed: '+path.name)
    data = read_json(path)
    if data.get('format') != 'awft-native-settlement:1':
        raise UserError('Unsupported construction geometry: '+path.name)
    return data


def verified_geometry(directory, metadata, expected, receipt_name):
    """Bind reviewed plan bytes to their successful archived native check.

    A prepared aggregate is not deployment authority. The source remains a plan,
    and its historical native check does not establish present graphics, movement
    or traversal. Sharing reads keep these inspections safe for Windows writers.
    """
    directory = Path(directory).resolve()
    if metadata.get('sha256') != expected or not isinstance(metadata.get('path'), str):
        raise UserError('A prepared geometry entry differs from the reviewed placed plan')
    path = Path(metadata['path']).resolve()
    if not path.is_relative_to(directory):
        raise UserError('Cinematic geometry must stay in the owned settlement directory')
    plan = require_plan(path, expected)
    if Path(receipt_name).name != receipt_name:
        raise UserError('Native geometry receipt must be an owned filename')
    receipt_path = directory/receipt_name
    proof = native_read(receipt_path, {})
    if (proof.get('operation') != 'verify' or proof.get('plan_sha256') != expected
        or proof.get('failures') != 0 or proof.get('error') or not proof.get('finished')
        or proof.get('blocks') != len(plan['blocks'])):
        raise UserError('No exact successful native verification for cinematic geometry: '+path.name)
    source = {'file': path.name, 'sha256': expected, 'blocks': len(plan['blocks']),
              'native_verification': {'finished': proof['finished'], 'failures': 0,
                                      'receipt_sha256': digest(receipt_path)},
              'note': 'Reviewed construction bytes matched their archived native block/inventory check; current rendering and traversal remain separate'}
    return plan, source


def final_harbor_geometry(directory, harbor):
    """Final access manifest is authoritative; the aggregate's old access is ignored."""
    directory = Path(directory)
    vessels = harbor.get('vessels', [])
    if (len(vessels) != 4 or {v.get('ship', {}).get('slug') for v in vessels} != set(SHIP_SHAS)):
        raise UserError('The four distinct reviewed final harbor vessels are required')
    bindings = []
    for vessel in vessels:
        slug = vessel['ship']['slug']
        expected = SHIP_SHAS[slug]
        plan, source = verified_geometry(directory, vessel, expected,
                                        'ship-'+slug+'-'+expected[:12]+'-verify.json')
        vessel['_plan'] = plan
        bindings.append((plan, source))
    # Earlier aggregate manifests retain an obsolete 4,036-position access entry.
    # Never fall back to it if the final 4,148-position deployed delta is absent.
    access = native_read(directory/'grand-harbor-access-final.json', {})
    bindings.append(verified_geometry(directory, access, ACCESS_SHA,
                                     'grand-harbor-access-'+ACCESS_SHA[:12]+'-verify.json'))
    return vessels, bindings


def load_geometry(home):
    directory = Path(home)/'dashboard/settlement'
    bindings = []
    fixed = [
        ('master-'+CORE_SHA+'.json', CORE_SHA, 'core-verification-pass.json'),
        ('pirate-port-master-'+PORT_SHA+'.json', PORT_SHA, 'pirate-port-verification-pass.json'),
        ('drawbridge-master-'+DRAWBRIDGE_SHA+'.json', DRAWBRIDGE_SHA, 'drawbridge-block-verification.json'),
        ('rosewater-castle-plan-'+CASTLE_SHA+'.json', CASTLE_SHA, 'rosewater-castle-'+CASTLE_SHA[:12]+'-verify.json'),
        ('south-bank-plan.json', SOUTH_SHA, 'south-bank-'+SOUTH_SHA[:12]+'-verify-shared-read.json'),
    ]
    for filename, expected, receipt in fixed:
        bindings.append(verified_geometry(directory, {'path': str((directory/filename).resolve()), 'sha256': expected}, expected, receipt))
    harbor = native_read(directory/'grand-harbor-prepared-final.json', {})
    vessels, harbor_bindings = final_harbor_geometry(directory, harbor)
    bindings.extend(harbor_bindings)
    if len(bindings) != 10:
        raise UserError('Expected ten reviewed deployed geometry sources')
    sources = []
    solid = set()
    world = None
    for plan, source in bindings:
        identity = plan.get('world_path'),plan.get('seed')
        if world is None:
            world = identity
        elif identity != world:
            raise UserError('Camera geometry mixes distinct permanent worlds')
        palette = plan['palette']
        for x,y,z,index in plan['blocks']:
            if palette[index].split('[')[0] in ('minecraft:air','minecraft:water'):
                solid.discard((x,y,z))
            else:
                solid.add((x,y,z))
        sources.append(source)
    return solid,vessels,sources


def clearance(document,solid):
    """Check the complete native linear camera polyline against known block cubes."""
    checked = 0
    closest = float('inf')
    for first,last in zip(document['keyframes'],document['keyframes'][1:]):
        a=[first['pos'][key] for key in ('x','y','z')]
        b=[last['pos'][key] for key in ('x','y','z')]
        count=max(1,math.ceil(math.dist(a,b)*4))
        for n in range(count+1):
            point=[a[j]+(b[j]-a[j])*n/count for j in range(3)]
            ix,iy,iz=(math.floor(v) for v in point)
            checked+=1
            for x in range(ix-2,ix+3):
                for y in range(iy-2,iy+3):
                    for z in range(iz-2,iz+3):
                        if (x,y,z) not in solid:
                            continue
                        distance=math.sqrt(sum(max(low-value,0,value-(low+1))**2
                                               for value,low in zip(point,(x,y,z))))
                        closest=min(closest,distance)
                        if distance < .7:
                            raise UserError('Camera intersects known construction in '+document['id']+
                                            ' near '+str(tuple(round(v,2) for v in point)))
    return {'sampled_positions':checked,'segment_spacing_max_blocks':.25,
            'minimum_required_cube_clearance':.7,
            'nearest_cube_within_checked_neighborhood':None if not math.isfinite(closest) else round(closest,4),
            'known_construction_collision':'pass',
            'native_block_model_shape_and_natural_terrain':'pending',
            'rendered_visibility_and_occlusion':'pending'}


def prepare(home,destination=None):
    """Stage a ZIP and manifest only. No world/config writes and no activation."""
    layout=Layout(Path(home))
    jar=layout.server/'mods'/LUMIERA_FILE
    if not jar.is_file() or digest(jar)!=LUMIERA_SHA256:
        raise UserError('The exact investigated Lumiera alpha.1 JAR is required')
    solid,vessels,sources=load_geometry(layout.home)
    prepared=scenes(vessels)
    documents={}
    contracts=[]
    for document,contract in prepared:
        contract['structural_preflight']=clearance(document,solid)
        relative='data/awft/cutscenes/'+document['id'].split(':')[1]+'.json'
        documents[relative]=(json.dumps(document,indent=2,ensure_ascii=False)+'\n').encode()
        contract['scene_sha256']=hashlib.sha256(documents[relative]).hexdigest()
        contracts.append(contract)
    documents['pack.mcmeta']=(json.dumps({'pack':{'pack_format':48,
        'description':'A World for Two: world-specific settlement camera tours'}})+'\n').encode()
    identity=hashlib.sha256(b''.join(name.encode()+b'\0'+raw for name,raw in sorted(documents.items()))).hexdigest()
    output=(layout.staging/('settlement-cinematic-'+identity[:16]) if destination is None else Path(destination).resolve())
    if not output.resolve().is_relative_to(layout.staging.resolve()) or output.suffix:
        raise UserError('Cinematic outputs must use an owned staging directory')
    if output.exists():
        raise UserError('Preserve the existing cinematic staging receipt; use a fresh output directory')
    Storage(layout).reserve(MAX_OUTPUT,target=output)
    output.mkdir(parents=True)
    zip_path=output/'awft-settlement-cinematic.zip'
    with zipfile.ZipFile(zip_path,'x',zipfile.ZIP_DEFLATED) as archive:
        for relative,raw in sorted(documents.items()):
            item=zipfile.ZipInfo(relative,(2026,1,1,0,0,0));item.compress_type=zipfile.ZIP_DEFLATED
            archive.writestr(item,raw)
            atomic_write(output/'datapack'/relative,raw)
    manifest={'format':'awft-settlement-cinematic:1','at':utcnow(),'identity':identity,
              'lumiera':{'file':LUMIERA_FILE,'sha256':LUMIERA_SHA256,'version':'1.0.0-alpha.1'},
              'datapack':zip_path.name,'datapack_sha256':digest(zip_path),'scenes':contracts,
              'geometry_sources':sources,'geometry_source_count':len(sources),'source_sha256':digest(Path(__file__)),
              'recommended_first_join_scene':FIRST_JOIN,'activation':'Not performed',
              'native_format_probe':'pending','server_registry_reload':'pending',
              'history_policy':'Preserve cinematic-first-joins.json unchanged',
              'full_castle_to_offshore_first_join_tour':'Not provided: native six-chunk coverage is insufficient',
              'dh_seedgen_building_visibility':'Unverified; never assumed',
              'performance':'No chunk tickets, forceloads, actors, world commands or global distance changes',
              'acceptance':'Native parse, server loading, actual client coverage, skip/return and shader refinement remain pending'}
    atomic_write(output/'manifest.json',json.dumps(manifest,indent=2,ensure_ascii=False)+'\n')
    return {'directory':str(output),'datapack':str(zip_path),'sha256':digest(zip_path),
            'scenes':len(contracts),'first_join':FIRST_JOIN,'activation':'Not performed'}


PROBE_SOURCE = r'''
import com.google.gson.*;
import dev.tysontheember.lumiera.cinematics.*;
import dev.tysontheember.lumiera.cinematics.event.BuiltinEventParsers;
import net.minecraft.resources.ResourceLocation;
import java.nio.file.*;
public class SettlementSceneProbe {
  public static void main(String[] args) throws Exception {
    net.minecraft.SharedConstants.tryDetectVersion();
    net.minecraft.server.Bootstrap.bootStrap();
    BuiltinEventParsers.registerAll();
    for (String arg:args) {
      var json=JsonParser.parseString(Files.readString(Path.of(arg))).getAsJsonObject();
      var id=ResourceLocation.parse(json.get("id").getAsString());
      var scene=CinematicJsonParser.parseCutscene(id,json,"cutscenes",CinematicsRegistry::parseEvent).toCutscene();
      var expected=json.getAsJsonArray("keyframes");
      if(scene.durationTicks!=json.get("duration_ticks").getAsInt() || scene.events.size()!=2
          || scene.cameraPositionMode!=CinematicCutscene.CameraPositionMode.ABSOLUTE
          || scene.cameraPath==null || scene.cameraPath.getPoints().size()!=expected.size()
          || scene.cameraPath.getLength()!=scene.durationTicks)
        throw new IllegalStateException("Native scene metadata changed: "+id);
      for(int n=0;n<expected.size();n++) {
        var point=scene.cameraPath.getPoints().get(n);
        var source=expected.get(n).getAsJsonObject();
        var p=source.getAsJsonObject("pos");var r=source.getAsJsonObject("rot");
        if(Math.abs(point.getPos().x-p.get("x").getAsFloat())>.002
            || Math.abs(point.getPos().y-p.get("y").getAsFloat())>.002
            || Math.abs(point.getPos().z-p.get("z").getAsFloat())>.002
            || Math.abs(point.getRot().x-r.get("pitch").getAsFloat())>.002
            || Math.abs(point.getRot().y-r.get("yaw").getAsFloat())>.002
            || Math.abs(point.getFov()-source.get("fov").getAsFloat())>.002
            || !point.getPathInterpolator().name().equals("LINEAR"))
          throw new IllegalStateException("Native keyframe fields changed: "+id+" point "+n);
      }
      var roundtrip=CinematicCutscene.fromNBT(scene.toNBT());
      if(roundtrip.durationTicks!=scene.durationTicks || roundtrip.events.size()!=scene.events.size()
          || roundtrip.cameraPath.getPoints().size()!=expected.size()
          || roundtrip.cameraPositionMode!=scene.cameraPositionMode)
        throw new IllegalStateException("Server packet NBT roundtrip failed: "+id);
      System.out.println("AWFT_SCENE_PASS "+id+" ticks="+scene.durationTicks+" points="+expected.size()+" events="+scene.events.size()+" mode="+scene.cameraPositionMode);
    }
  }
}
'''


def native_probe(home,directory):
    """Standalone real parser/NBT check; never starts a game or Minecraft server."""
    layout=Layout(Path(home));directory=Path(directory).resolve()
    if not directory.is_relative_to(layout.staging.resolve()):
        raise UserError('Probe only an owned staged cinematic')
    manifest=read_json(directory/'manifest.json',{})
    if manifest.get('format')!='awft-settlement-cinematic:1':
        raise UserError('Missing staged cinematic receipt')
    if manifest.get('datapack')!='awft-settlement-cinematic.zip' or digest(directory/manifest['datapack'])!=manifest.get('datapack_sha256'):
        raise UserError('The staged datapack changed after its hash receipt')
    jar=layout.server/'mods'/LUMIERA_FILE
    if digest(jar)!=LUMIERA_SHA256:
        raise UserError('Lumiera changed before native parsing')
    files=sorted((directory/'datapack/data/awft/cutscenes').glob('*.json'))
    if len(files)!=len(manifest['scenes']) or len(files)>16:
        raise UserError('Unexpected cinematic scene set')
    expected={row['id']:row['scene_sha256'] for row in manifest['scenes']}
    for path in files:
        if digest(path)!=expected.get(read_json(path).get('id')):
            raise UserError('Scene changed after its staged hash receipt')
    work=directory/('native-probe-'+str(time.time_ns()))
    Storage(layout).reserve(16*1024**2,target=work)
    work.mkdir()
    source=work/'SettlementSceneProbe.java';atomic_write(source,PROBE_SOURCE)
    libraries=layout.server/'libraries'
    # The installer cache also contains obsolete tool dependencies (notably
    # Guava 20). They are not the server's runtime. Use its exact pinned launch
    # list instead of putting every cached JAR on the standalone classpath.
    launch= libraries/'net/neoforged/neoforge/21.1.262/win_args.txt'
    if not launch.is_file():
        raise UserError('The exact installed NeoForge launch dependency list is required')
    lines=launch.read_text(encoding='utf-8').splitlines()
    legacy=[line.split('=',1)[1] for line in lines if line.startswith('-DlegacyClassPath=')]
    if len(legacy)!=1:
        raise UserError('The installed launch list has no unique runtime classpath')
    dependencies=[]
    for relative in legacy[0].split(';'):
        item=(layout.server/relative).resolve()
        if not item.is_relative_to(libraries.resolve()) or not item.is_file() or item.suffix!='.jar':
            raise UserError('A selected native runtime dependency is missing or outside libraries')
        dependencies.append(item)
    named=sorted((libraries/'net/minecraft/server').rglob('*-srg.jar'))
    universal=libraries/'net/neoforged/neoforge/21.1.262/neoforge-21.1.262-universal.jar'
    if len(named)!=1 or not universal.is_file():
        raise UserError('Select the exact named server and NeoForge runtime JARs before parsing')
    resources=named[0].with_name(named[0].name.replace('-srg.jar','-extra.jar'))
    if not resources.is_file():
        raise UserError('The named server needs its matching resource-only extra JAR')
    jars=list(dict.fromkeys([jar,*named,resources,universal,*dependencies]))
    cp=os.pathsep.join(str(p) for p in jars)
    args=work/'javac.args'
    atomic_write(args,'-proc:none\n--release\n21\n-classpath\n"'+cp.replace('\\','/')+'"\n-d\n"'+work.as_posix()+'"\n"'+source.as_posix()+'"\n')
    flags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0
    compiled=subprocess.run([str(JDK/'javac.exe'),'-J-XX:-UsePerfData',
                             '-J-Djava.io.tmpdir='+str(work),'@'+str(args)],cwd=work,capture_output=True,text=True,
                            timeout=45,creationflags=flags)
    atomic_write(work/'compile.log',compiled.stdout+compiled.stderr)
    if compiled.returncode:
        raise UserError('Native cinematic parser probe compilation failed; retained '+str(work))
    java_args=work/'java.args'
    atomic_write(java_args,'-Xms64M\n-Xmx384M\n-XX:-UsePerfData\n"-Djava.io.tmpdir='+work.as_posix()+'"\n-classpath\n"'+(str(work)+os.pathsep+cp).replace('\\','/')+
                 '"\nSettlementSceneProbe\n'+'\n'.join('"'+p.as_posix()+'"' for p in files)+'\n')
    run=subprocess.run([str(JDK/'java.exe'),'@'+str(java_args)],cwd=work,capture_output=True,text=True,
                       timeout=60,creationflags=flags)
    atomic_write(work/'native.log',run.stdout+run.stderr)
    # Bootstrap installs Minecraft's LoggedPrintStream, so a successful marker
    # appears after its logger prefix rather than at column zero.
    marker=re.compile(r'AWFT_SCENE_PASS ([a-z0-9_.:/-]+) ticks=(\d+) points=(\d+) events=(\d+) mode=ABSOLUTE$')
    matched=[found for row in (run.stdout+'\n'+run.stderr).splitlines() if (found:=marker.search(row))]
    passes=[found.group(0) for found in matched]
    passed=(run.returncode==0 and len(matched)==len(files)
            and {found.group(1) for found in matched}==set(expected))
    receipt={'at':utcnow(),'status':'pass' if passed else 'failed','lumiera_sha256':digest(jar),
             'datapack_sha256':manifest['datapack_sha256'],'scenes':passes,
             'compiler_exit_code':compiled.returncode,'native_exit_code':run.returncode,
             'runtime_launch_sha256':digest(launch),
             'dependency_selection':'Exact installed NeoForge legacyClassPath plus named server, matching resource extra and universal; installer cache excluded',
             'stdout_sha256':digest(work/'native.log'),
             'scope':'Real pinned parser, fields and native NBT roundtrip; no server reload, networking client or graphics proof'}
    atomic_write(work/'result.json',json.dumps(receipt,indent=2)+'\n')
    if not passed:
        raise UserError('Native cinematic parsing failed; retained '+str(work))
    return {'receipt':str(work/'result.json'),**receipt}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--home',type=Path,default=Path(r'D:\A World for Two'))
    parser.add_argument('--destination',type=Path)
    parser.add_argument('--native-probe',type=Path,metavar='PREPARED_DIRECTORY')
    args=parser.parse_args()
    result=native_probe(args.home,args.native_probe) if args.native_probe else prepare(args.home,args.destination)
    print(json.dumps(result),flush=True)
