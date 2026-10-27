"""Prepare an unapplied, version-neutral full integration patch and API compile.

Writes only a new private staging folder. No active source, candidate, artifact,
runtime, account, Git index or world is modified. Parent must review and apply the
whole patch as one new immutable candidate, then perform native acceptance.
"""
from pathlib import Path
import argparse
import difflib
import hashlib
import json
import os
import subprocess
import time

from control_room.common import REPO, UserError, digest, utcnow
from tools.playtest import guard
from compat.seedgen.probe_lithostitched import FILES, JDK, SOURCES


PROPOSAL = 'compat/control-bridge/proposals/'
JAVA = 'compat/control-bridge/src/worldfortwo/bridge/'
MIXINS = ('LithostitchedSeedgenAttemptMixin','LithostitchedSeedgenPacketMixin',
          'LithostitchedSeedgenWorldMixin','LithostitchedSeedgenQueueMixin')
CLIENT_SHA = 'a649bd3ce77f122d0f83ae1b37b4b303e662470f928b9bee5fbc76580805ffd4'
EXTRAS_SHA = 'f0c3e3c1ad835b80e70cb3f78359b71f107f74689523b4fb391f160ee487cfbf'
CONFIG = 'compat/control-bridge/resources/awft-bridge.mixins.json'
TOML = 'compat/control-bridge/resources/META-INF/neoforge.mods.toml'
CALLBACK = JAVA+'mixin/HybridAquaticSeedgenMixin.java'
BUILDER = 'tools/build_bridge.py'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def replace_once(text,before,after):
    if text.count(before)!=1:raise UserError('Exact active integration context changed; review and regenerate the handoff')
    return text.replace(before,after)


def contents(path):
    path=REPO/path
    if path.stat().st_size>256*1024:raise UserError('Bounded original project source required')
    return path.read_text(encoding='utf-8').replace('\r\n','\n')


def callback_patch(text):
    text=replace_once(text,'import worldfortwo.bridge.HybridAquaticSeedgenCompat;\n',
        'import worldfortwo.bridge.HybridAquaticSeedgenCompat;\nimport worldfortwo.bridge.LithostitchedSeedgenCompat;\n')
    return replace_once(text,'        if(withMods)HybridAquaticSeedgenCompat.apply(worldgen,resources,stems);',
        '        if(withMods) {\n'
        '            var currentStems=LithostitchedSeedgenCompat.currentAttemptStems(stems);\n'
        '            LithostitchedSeedgenCompat.beforeHybrid(worldgen,currentStems,wholeSet,opened,resources);\n'
        '            HybridAquaticSeedgenCompat.apply(worldgen,resources,currentStems);\n'
        '            LithostitchedSeedgenCompat.afterHybrid(worldgen);\n'
        '        }')


def builder_patch(text):
    text=replace_once(text,'    bluelib=home/',
        '    # Compile-only client signatures; never copied into the bridge artifact.\n'
        '    client_api=Path(os.environ["APPDATA"])/"PrismLauncher/libraries/net/minecraft/client/1.21.1-20240808.144430/client-1.21.1-20240808.144430-srg.jar"\n'
        '    if not client_api.is_file() or digest(client_api)!="'+CLIENT_SHA+'":\n'
        '        raise UserError("The exact installed named 1.21.1 client compile API is required")\n'
        '    jars.insert(0,client_api)\n'
        '    bluelib=home/')
    text=replace_once(text,'    api_hashes = {\n','    api_hashes = {\n'+''.join(
        '        '+repr(name)+': '+repr(expected)+',\n' for name,expected in FILES.items()))
    return replace_once(text,'    cp = os.pathsep.join(p.as_posix() for p in jars)\n',
        '    # The actual loader supplies this library; extraction is compile-only.\n'
        '    universal=libraries/"net/neoforged/neoforge/21.1.262/neoforge-21.1.262-universal.jar"\n'
        '    with zipfile.ZipFile(universal) as native:\n'
        '        member=native.getinfo("META-INF/jarjar/mixinextras-neoforge-0.5.5.jar")\n'
        '        if member.file_size!=727484:\n'
        '            raise UserError("Pinned MixinExtras compile API size differs")\n'
        '        raw=native.read(member)\n'
        '        if hashlib.sha256(raw).hexdigest()!="'+EXTRAS_SHA+'":\n'
        '            raise UserError("Pinned MixinExtras compile API differs")\n'
        '        api=api_dir/"mixinextras-neoforge-0.5.5.jar"\n'
        '        api.write_bytes(raw);jars.append(api)\n'
        '    cp = os.pathsep.join(p.as_posix() for p in jars)\n')


def prepare(home,probe):
    home=Path(home).resolve();probe=Path(probe).resolve()
    if not home.is_relative_to(Path(r'D:\A World for Two\staging\world-tests')) or not probe.is_relative_to(home/'staging'):
        raise UserError('Separate private artistic home and retained offline probe required')
    result_path=probe/'result.json'
    if result_path.stat().st_size>64*1024:raise UserError('Bounded actual offline receipt required')
    receipt=json.loads(result_path.read_text())
    if receipt.get('compile_exit')!=0 or receipt.get('probe_exit')!=0:raise UserError('A passing actual API/proposal probe is required')
    if set(receipt['sources'])!=set(SOURCES):raise UserError('The complete nine-source/probe set differs')
    for name,expected in receipt['sources'].items():
        if digest(REPO/name)!=expected:raise UserError('Proposal changed after its API probe: '+name)
    active={path:contents(path) for path in (CONFIG,TOML,CALLBACK,BUILDER)}
    patched={CALLBACK:callback_patch(active[CALLBACK]),BUILDER:builder_patch(active[BUILDER])}
    config=json.loads(active[CONFIG])
    if any(name in config.get('client',[]) for name in MIXINS):raise UserError('Partial/full registration already present; do not double-apply')
    config['client']+=list(MIXINS);patched[CONFIG]=json.dumps(config,indent=2)+'\n'
    patched[TOML]=replace_once(active[TOML],'modId="seedrenderer"\ntype="optional"\nversionRange="[0.9.1]"\nside="SERVER"',
        'modId="seedrenderer"\ntype="optional"\nversionRange="[0.9.1]"\nside="BOTH"')
    if 'modId="lithostitched"' in patched[TOML]:raise UserError('Existing Lithostitched dependency needs explicit review')
    patched[TOML]+='\n[[dependencies.awft_control_bridge]]\nmodId="lithostitched"\ntype="optional"\nversionRange="[1.8.1]"\nside="CLIENT"\n'
    for name in SOURCES:
        if not name.startswith(PROPOSAL):continue
        filename=Path(name).name;target=JAVA+('mixin/' if filename[:-5] in MIXINS else '')+filename
        if (REPO/target).exists():raise UserError('Active target already exists; preserve parent source')
        patched[target]=contents(name)
    patch=''.join(''.join(difflib.unified_diff(active.get(name,'').splitlines(True),text.splitlines(True),
        fromfile='a/'+name if name in active else '/dev/null',tofile='b/'+name)) for name,text in sorted(patched.items()))
    if len(patch.encode())>1024**2:raise UserError('Finite integration patch exceeded')
    reserve=guard(16*1024**2,32*1024**2)
    work=home/'staging'/('seedgen-integration-handoff-'+str(time.time_ns()));work.mkdir();(work/'classes').mkdir()
    def write(name,raw):
        if isinstance(raw,str):raw=raw.encode('utf-8')
        if len(raw)>2*1024**2:raise UserError('Bounded handoff member exceeded')
        path=work/name;path.parent.mkdir(parents=True,exist_ok=True)
        with path.open('xb') as stream:stream.write(raw)
    write('integration.patch',patch)
    for name,text in patched.items():write('patch-tree/'+name,text)
    # Compile the exact patched existing callback and unchanged HA helper
    # against the already compiled proposal and exact installed APIs. No Main,
    # ModList spoof, fake game, full bridge build or native process is started.
    args=(probe/'javac.args').read_text().splitlines();cp=args[args.index('-classpath')+1].strip('"')
    api_cp=(probe/'classes').as_posix()+os.pathsep+cp
    write('javac.args','-proc:none\n--release\n21\n-classpath\n"'+api_cp+'"\n-d\n"'+(work/'classes').as_posix()+'"\n"'+(work/'patch-tree'/CALLBACK).as_posix()+'"\n"'+(REPO/(JAVA+'HybridAquaticSeedgenCompat.java')).as_posix()+'"\n')
    result=subprocess.run([str(JDK/'javac.exe'),'-J-Xms32m','-J-Xmx256m','-J-XX:-UsePerfData','@'+str(work/'javac.args')],cwd=work,
        capture_output=True,text=True,timeout=60,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
    write('javac.log',result.stdout+result.stderr)
    record={'format':'awft-seedgen-full-integration-handoff:1','at':utcnow(),'status':'UNAPPLIED SOURCE ONLY; NATIVE QUALIFICATION PENDING',
        'reserve':reserve,'offline_receipt_sha256':digest(result_path),'callback_compile_exit':result.returncode,
        'active_baseline_sha256':{name:digest(REPO/name) for name in active},
        'proposal_sha256':receipt['sources'],
        'handoff_support_sha256':{name:digest(REPO/name) for name in (
            PROPOSAL+'LITHOSTITCHED-SEEDGEN.md',PROPOSAL+'LITHOSTITCHED-HANDOFF.md',
            'compat/seedgen/probe_lithostitched.py','compat/seedgen/prepare_lithostitched_handoff.py',
            'compat/seedgen/test_lithostitched_handoff.py')},
        'patch_sha256':digest(work/'integration.patch'),
        'patch_tree_sha256':{name:sha(text.encode()) for name,text in patched.items()},'client_mixins':list(MIXINS),
        'lifecycle_entrypoint':JAVA+'LithostitchedSeedgenClientHooks.java',
        'compile_only':{'minecraft_named_client_sha256':CLIENT_SHA,'pinned_mods':FILES,'mixinextras':{'bytes':727484,'sha256':EXTRAS_SHA}},
        'artifact_version':'Unassigned; parent must choose a new immutable bridge/candidate. No existing binary may be overwritten.',
        'native_pending':['Actual full-loader mixin/local-capture/union visibility on both logical sides',
            'Same1,950selectedkeys/248densityencodings and every selected noise setting, original native fingerprint and effective surface/router witness',
            'Original authenticated packet acceptance, fresh input attestation, real injector/FastNoise witness and actual LOD terrain',
            'Same-world reconnect/real logout worker retirement; current-connection stale-packet refusal; restart before any other world seed'],
        'never_apply_partially':True,'world_runtime_git_mutations':0}
    write('manifest.json',json.dumps(record,indent=2)+'\n')
    return {'directory':str(work),'manifest_sha256':digest(work/'manifest.json'),'patch_sha256':record['patch_sha256'],
            'callback_compile_exit':result.returncode,'source_files':len(patched),'status':record['status']}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--home',type=Path,required=True)
    parser.add_argument('--probe',type=Path,required=True);args=parser.parse_args()
    result=prepare(args.home,args.probe);print(json.dumps(result,indent=2))
    raise SystemExit(result['callback_compile_exit'])
