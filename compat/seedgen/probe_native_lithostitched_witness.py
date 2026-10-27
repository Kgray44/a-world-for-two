"""Finite offline actual-API witness probe; never starts Minecraft or touches worlds."""
from pathlib import Path
import argparse,hashlib,json,os,subprocess,time,zipfile
from control_room.common import REPO,UserError,digest,utcnow
from tools.playtest import guard

JDK=Path(r'C:\Program Files\Java\jdk-21.0.10\bin')
SOURCES=['compat/control-bridge/proposals/NativeLithostitchedWitness.java','compat/seedgen/NativeLithostitchedWitnessProbe.java']

def run(home):
 home=Path(home).resolve()
 if not home.is_relative_to(Path(r'D:\A World for Two\staging\world-tests')):raise UserError('Owned private staging only')
 litho=home/'server/mods/lithostitched-1.8.1-neoforge-21.1.jar'
 if digest(litho)!='e0da669fa5facc61a09b9b7bae21b322993de1fcd1eb05787adffb7309598cca':raise UserError('Pinned original Lithostitched differs')
 reserve=guard(1024**2,32*1024**2);work=home/'staging'/('lithostitched-witness-offline-'+str(time.time_ns()));work.mkdir();(work/'classes').mkdir()
 libraries=home/'server/libraries';named=sorted((libraries/'net/minecraft/server').rglob('*-srg.jar'))
 if len(named)!=1:raise UserError('One actual named server API required')
 launch=(libraries/'net/neoforged/neoforge/21.1.262/win_args.txt').read_text().splitlines()
 legacy=[v.split('=',1)[1] for v in launch if v.startswith('-DlegacyClassPath=')];modules=[v[3:] for v in launch if v.startswith('-p ')]
 if len(legacy)!=1 or len(modules)!=1:raise UserError('Exact installed dependency list required')
 deps=[]
 for relative in (modules[0]+';'+legacy[0]).split(';'):
  path=(home/'server'/relative).resolve()
  if not path.is_relative_to(libraries.resolve()) or not path.is_file():raise UserError('Dependency escaped libraries')
  deps.append(path)
 with zipfile.ZipFile(litho) as archive:
  info=archive.getinfo('META-INF/jarjar/apollib-1.2.0-neoforge-21.1.jar')
  if info.file_size!=110989:raise UserError('Exact finite nested Apollib API required')
  apollib=work/'apollib-1.2.0-neoforge-21.1.jar'
  with apollib.open('xb') as stream:stream.write(archive.read(info))
 cp=os.pathsep.join(p.as_posix() for p in dict.fromkeys([*named,named[0].with_name(named[0].name.replace('-srg.jar','-extra.jar')),*deps,litho,apollib]))
 def write(name,text):
  if len(text.encode())>2*1024**2:raise UserError('Finite probe output exceeded')
  with (work/name).open('x',encoding='utf-8') as stream:stream.write(text)
 def invoke(binary,args,name):
  try:r=subprocess.run([str(JDK/binary),*args],cwd=work,capture_output=True,text=True,timeout=60,creationflags=subprocess.CREATE_NO_WINDOW)
  except subprocess.TimeoutExpired:write(name,'TIMEOUT: owned offline process terminated; preserve failed probe\n');raise
  write(name,r.stdout+r.stderr);return r.returncode
 write('javac.args','-proc:none\n--release\n21\n-classpath\n"'+cp+'"\n-d\n"'+(work/'classes').as_posix()+'"\n'+'\n'.join('"'+(REPO/n).as_posix()+'"' for n in SOURCES))
 receipt={'at':utcnow(),'reserve':reserve,'sources':{n:digest(REPO/n) for n in SOURCES},'lithostitched_sha256':digest(litho)}
 receipt['compile_exit']=invoke('javac.exe',['-J-Xmx256m','-J-XX:-UsePerfData','@'+str(work/'javac.args')],'javac.log')
 if not receipt['compile_exit']:
  write('java.args','-Xms32m\n-Xmx256m\n-XX:-UsePerfData\n"-Djava.io.tmpdir='+work.as_posix()+'"\n"-XX:ErrorFile='+(work/'hs_err_pid%p.log').as_posix()+'"\n-classpath\n"'+(work/'classes').as_posix()+os.pathsep+cp+'"\nworldfortwo.bridge.NativeLithostitchedWitnessProbe\n')
  receipt['probe_exit']=invoke('java.exe',['@'+str(work/'java.args')],'probe.log')
 receipt['status']='PASS offline actual APIs only' if receipt['compile_exit']==receipt.get('probe_exit')==0 else 'FAIL preserved'
 write('result.json',json.dumps(receipt,indent=2)+'\n');return {'directory':str(work),'status':receipt['status'],'result_sha256':digest(work/'result.json')}
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--home',type=Path,required=True);print(json.dumps(run(p.parse_args().home),indent=2))
