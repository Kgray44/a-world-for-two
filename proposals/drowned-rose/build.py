"""Compile a candidate using installed Java21/NeoForge APIs. Never install/launch."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import zipfile

HERE=Path(__file__).resolve().parent
PINS={
 'easy_npc-neoforge-1.21.1-7.17.1.jar':'e3f93183a92de47ba0c2ed5bdab8f31a4c1df0c2a29c93c1815c2a50df7ff5a609c8de6aad84e593b3291115f5d184bc75d4b3b8e03c0ac8e02508eff52b8a3e',
 'easy_npc_config_ui-neoforge-1.21.1-7.17.1.jar':'3880f9769a5ae1928527bb76f8d00c08eac9040169e7584115b3caf2e28ed845eb3a1b0f88cfe36935471f52a11a0617b8ee395e39d2d3dcb06c04751312824a',
 'immersive_melodies-neoforge-0.8.0+1.21.1.jar':'79bf2f8dccb5b0db017f77956d73721d54e093416ebe4785f378515fc791ca9a2098d1039d6045c96e2f2c1eac7806de775b7ae84ab9b1b15e68adebebaeaff1',
 'handcrafted-neoforge-1.21.1-4.0.3.jar':'4ff5fb2aa9582b886d03f647fe9b8c12a828d29a1787e9c9b463be18192ea798e6a4ac83479623042791bce0bacbf6e3e2c2e9ef086640aeeb6970d3404e7ee4',
 'resourcefullib-neoforge-1.21-3.0.12.jar':'a9d20e345faa9bcb297bd95ac9524205834804d1bb13518397dd4f7f62b352b08c3339ee7f7870d3669078ceeb33d5c31ea527aecce4b31d62ec1ff7d8b562c8',
 'FarmersDelight-1.21.1-1.3.4.jar':'1f6f8796469f747cff36f477b4f589a3d69613882399f9ee7f86db36c7bca9aa4828731f43db15dc6c7f5a4c1bbe3d4092a232e8cef010b09cec0581848fda90',
}

def build(home,dependencies,prepared,output):
    if output.exists():raise ValueError('Fresh output directory required')
    output.mkdir(parents=True);classes=output/'classes';classes.mkdir()
    apis=[]
    for name,sha in PINS.items():
        f=dependencies/name
        if not f.exists():f=home/'server/mods'/name
        if hashlib.sha512(f.read_bytes()).hexdigest()!=sha:raise ValueError('Pinned API differs: '+name)
        apis.append(f)
    libraries=home/'server/libraries'
    client=Path(os.environ['APPDATA'])/'PrismLauncher/libraries/net/minecraft/client/1.21.1-20240808.144430/client-1.21.1-20240808.144430-srg.jar'
    if hashlib.sha256(client.read_bytes()).hexdigest()!='a649bd3ce77f122d0f83ae1b37b4b303e662470f928b9bee5fbc76580805ffd4':raise ValueError('Named client compiler API changed')
    jars=[client,*libraries.rglob('*-srg.jar'),*apis,*libraries.rglob('*.jar'),*home.joinpath('server/mods').glob('*handcrafted*.jar'),*home.joinpath('server/mods').glob('*resourcefullib*.jar')]
    args=['--release','21','-proc:none','-encoding','UTF-8','-classpath',
          '"'+os.pathsep.join(str(p).replace('\\','/')for p in jars)+'"','-d','"'+str(classes).replace('\\','/')+'"',
          *['"'+str(p).replace('\\','/')+'"' for p in HERE.joinpath('src').rglob('*.java')]]
    (output/'javac.args').write_text('\n'.join(args))
    p=subprocess.run([r'C:\Program Files\Java\jdk-21.0.10\bin\javac.exe','-J-Xmx256m','@'+str(output/'javac.args')],capture_output=True,text=True,timeout=60,creationflags=subprocess.CREATE_NO_WINDOW)
    (output/'compiler.txt').write_text(p.stdout+p.stderr)
    if p.returncode:raise ValueError(p.stderr[:9000])
    artifact=output/'awft-tavern-0.1.14.jar'
    with zipfile.ZipFile(artifact,'x',zipfile.ZIP_DEFLATED) as z:
        entry=zipfile.ZipInfo('LICENSE-awft-tavern.txt',(2026,10,29,0,0,0));entry.compress_type=zipfile.ZIP_DEFLATED;z.writestr(entry,(HERE/'LICENSE-MIT.txt').read_bytes())
        for root in [classes,HERE/'resources',prepared/'resources']:
            for f in sorted(root.rglob('*')):
                if f.is_file():
                    entry=zipfile.ZipInfo(f.relative_to(root).as_posix(),(2026,10,29,0,0,0));entry.compress_type=zipfile.ZIP_DEFLATED;z.writestr(entry,f.read_bytes())
    receipt={'artifact':str(artifact),'bytes':artifact.stat().st_size,'sha256':hashlib.sha256(artifact.read_bytes()).hexdigest(),
             'compiled_java':21,'installed':False,'game_acceptance':False,'compile_api_sha512':PINS,
             'source_sha256':{str(p.relative_to(HERE)):hashlib.sha256(p.read_bytes()).hexdigest()for p in sorted(HERE.rglob('*'))if p.is_file()and'__pycache__'not in p.parts}}
    (output/'build-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for arg in ['home','dependencies','prepared','output']:p.add_argument('--'+arg,type=Path,required=True)
    a=p.parse_args();build(a.home,a.dependencies,a.prepared,a.output)
