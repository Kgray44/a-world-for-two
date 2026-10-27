"""Bounded offline proposal/API contracts; no game, server, native world or ModList spoof."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import subprocess
import time
import zipfile

from control_room.common import REPO, UserError, digest, utcnow
from tools.playtest import guard

JDK=Path(r'C:\Program Files\Java\jdk-21.0.10\bin')
FILES={
 'lithostitched-1.8.1-neoforge-21.1.jar':'e0da669fa5facc61a09b9b7bae21b322993de1fcd1eb05787adffb7309598cca',
 'Distant Horizons SeedGen 0.9.1 for 1.21.1 NeoForge.jar':'58469f92f7cf13ff3c2928659ce1a57d7d05314b30e0779cb187b6fbfdb43b4e',
}
SOURCES=['compat/control-bridge/proposals/LithostitchedSeedgenCompat.java',
 'compat/control-bridge/proposals/LithostitchedSeedgenPacketMixin.java',
 'compat/control-bridge/proposals/LithostitchedSeedgenWorldMixin.java',
 'compat/control-bridge/proposals/LithostitchedSeedgenAttemptMixin.java',
 'compat/control-bridge/proposals/LithostitchedSeedgenQueueMixin.java',
 'compat/control-bridge/proposals/LithostitchedSeedgenClientHooks.java',
 'compat/control-bridge/proposals/LithostitchedSeedgenResources.java',
 'compat/control-bridge/proposals/LithostitchedSeedgenLoadScope.java',
 'compat/control-bridge/proposals/LithostitchedSeedgenConnectionGate.java',
 'compat/seedgen/LithostitchedSeedgenProbe.java']


def run(home):
 home=Path(home).resolve()
 if not home.is_relative_to(Path(r'D:\A World for Two\staging\world-tests')):raise UserError('Separate owned artistic runtime only')
 for name,sha in FILES.items():
  if digest(home/'server/mods'/name)!=sha:raise UserError('Pinned API differs: '+name)
 admission=guard(16*1024**2,32*1024**2)
 work=home/'staging'/('seedgen-lithostitched-offline-'+str(time.time_ns()));work.mkdir();(work/'classes').mkdir()
 libraries=home/'server/libraries';named=sorted((libraries/'net/minecraft/server').rglob('*-srg.jar'))
 if len(named)!=1:raise UserError('One exact named Minecraft API required')
 client=Path(os.environ['APPDATA'])/'PrismLauncher/libraries/net/minecraft/client/1.21.1-20240808.144430/client-1.21.1-20240808.144430-srg.jar'
 if not client.is_file():raise UserError('Exact installed named client API required for typed client lifecycle mixins')
 launch=libraries/'net/neoforged/neoforge/21.1.262/win_args.txt'
 if not launch.is_file() or launch.stat().st_size>128*1024:raise UserError('Bounded installed dependency list required')
 lines=launch.read_text().splitlines();legacy=[v.split('=',1)[1] for v in lines if v.startswith('-DlegacyClassPath=')];modules=[v[3:] for v in lines if v.startswith('-p ')]
 if len(legacy)!=1 or len(modules)!=1:raise UserError('Unambiguous installed dependencies required')
 dependencies=[]
 for relative in (modules[0]+';'+legacy[0]).split(';'):
  path=(home/'server'/relative).resolve()
  if not path.is_relative_to(libraries.resolve()) or not path.is_file():raise UserError('Dependency escaped owned libraries')
  dependencies.append(path)
 extra=named[0].with_name(named[0].name.replace('-srg.jar','-extra.jar'))
 universal=libraries/'net/neoforged/neoforge/21.1.262/neoforge-21.1.262-universal.jar'
 with zipfile.ZipFile(universal) as archive:
  member=archive.getinfo('META-INF/jarjar/mixinextras-neoforge-0.5.5.jar')
  if member.file_size!=727484:raise UserError('Pinned native MixinExtras compile API size differs')
  raw=archive.read(member)
  if hashlib.sha256(raw).hexdigest()!='f0c3e3c1ad835b80e70cb3f78359b71f107f74689523b4fb391f160ee487cfbf':raise UserError('Pinned native MixinExtras API differs')
  mixinextras=work/'mixinextras-neoforge-0.5.5.jar'
  with mixinextras.open('xb') as stream:stream.write(raw)
 jars=list(dict.fromkeys([client,*named,extra,universal,mixinextras,*dependencies,*sorted((home/'server/mods').glob('*.jar'))]))
 cp=os.pathsep.join(p.as_posix() for p in jars)
 def write(name,text):
  raw=text.encode()
  if len(raw)>2*1024**2:raise UserError('Bounded offline output exceeded')
  with (work/name).open('xb') as stream:stream.write(raw)
 def invoke(binary,args,log):
  try:result=subprocess.run([str(JDK/binary),*args],cwd=work,capture_output=True,text=True,timeout=60,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
  except subprocess.TimeoutExpired:
   write(log,'TIMEOUT: offline child killed; preserve failed stage\n');raise
  write(log,result.stdout+result.stderr);return result.returncode
 write('javac.args','-proc:none\n--release\n21\n-classpath\n"'+cp+'"\n-d\n"'+(work/'classes').as_posix()+'"\n'+'\n'.join('"'+(REPO/name).as_posix()+'"' for name in SOURCES)+'\n')
 receipt={'format':'awft-lithostitched-offline:2','at':utcnow(),'reserve':admission,'sources':{n:digest(REPO/n) for n in SOURCES},'pinned_api':FILES,'named_client_api_sha256':digest(client)}
 receipt['compile_exit']=invoke('javac.exe',['-J-Xms32m','-J-Xmx256m','-J-XX:-UsePerfData','@'+str(work/'javac.args')],'javac.log')
 if not receipt['compile_exit']:
  write('java.args','-Xms32M\n-Xmx384M\n-XX:-UsePerfData\n"-Djava.io.tmpdir='+work.as_posix()+'"\n"-XX:ErrorFile='+(work/'hs_err_pid%p.log').as_posix()+'"\n-classpath\n"'+(work/'classes').as_posix()+os.pathsep+cp+'"\nworldfortwo.bridge.LithostitchedSeedgenProbe\n'+'\n'.join('"'+(home/'server/mods'/n).as_posix()+'"' for n in FILES)+'\n')
  receipt['probe_exit']=invoke('java.exe',['@'+str(work/'java.args')],'probe.log')
 receipt['status']='PASS offline contracts only' if not receipt['compile_exit'] and not receipt.get('probe_exit',1) else 'FAIL preserve private stage'
 receipt['native_execution']='NOT RUN: actual transformed native managers, packet acceptance, fresh-cache publication and paired FP remain pending'
 write('result.json',json.dumps(receipt,indent=2)+'\n')
 return {'directory':str(work),'status':receipt['status'],'result_sha256':digest(work/'result.json'),'compile_exit':receipt['compile_exit'],'probe_exit':receipt.get('probe_exit')}


if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--home',required=True,type=Path)
 result=run(p.parse_args().home);print(json.dumps(result,indent=2))
 raise SystemExit(0 if result['status'].startswith('PASS') else 1)
