"""Build a test-only read-only material probe; never install or launch it."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import zipfile

from control_room.common import REPO, UserError, digest, read_json
from tools.playtest import guard


def build(client, libraries, output):
    client, libraries, output = Path(client).resolve(), Path(libraries).resolve(), Path(output).resolve()
    owner = read_json(client/'awft-owned.json', {})
    if (owner.get('format') != 'awft-owned-client:1' or owner.get('root') != str(client)
            or not client.name.startswith('AWFT_Check_')):
        raise UserError('An explicitly owned test client is required')
    pin = next(m for m in read_json(REPO/'catalog/lock.json')['mods'] if m['slug'] == 'iris')
    iris = client/'.minecraft/mods'/pin['filename']
    if pin['version'] != '1.8.14-beta.1+1.21.1-neoforge' or any(digest(iris, k) != v for k,v in pin['hashes'].items()):
        raise UserError('Exact pinned Iris API required')
    named = Path(os.environ['APPDATA'])/'PrismLauncher/libraries/net/minecraft/client/1.21.1-20240808.144430/client-1.21.1-20240808.144430-srg.jar'
    if not named.is_file() or output.exists():
        raise UserError('Existing named client and a new build directory required')
    jars = [named, iris] + sorted(libraries.rglob('*.jar'))
    if len(jars) > 1000: raise UserError('Compile classpath exceeds its bound')
    guard(16*1024**2, 16*1024**2)
    output.mkdir(parents=True); classes=output/'classes'; classes.mkdir()
    cp = os.pathsep.join(p.as_posix() for p in jars)
    args=output/'javac.args'
    args.write_text('-proc:none\n--release\n21\n-classpath\n"'+cp+'"\n-d\n"'+classes.as_posix()+'"\n"'+(REPO/'compat/material-probe/MaterialProbe.java').as_posix()+'"\n')
    result=subprocess.run([r'C:\Program Files\Java\jdk-21.0.10\bin\javac.exe','-J-Xmx128m','@'+str(args)],capture_output=True,text=True,timeout=60,creationflags=subprocess.CREATE_NO_WINDOW)
    (output/'javac.log').write_text(result.stdout+result.stderr)
    if result.returncode: raise UserError(result.stderr[:3000])
    jar=output/'awft-material-probe-0.1.0.jar'
    meta='modLoader="javafml"\nloaderVersion="[4,)"\nlicense="MIT"\n[[mods]]\nmodId="awft_material_probe"\nversion="0.1.0"\ndisplayName="AWFT isolated material probe"\ndisplayTest="IGNORE_ALL_VERSION"\n'
    with zipfile.ZipFile(jar,'x',zipfile.ZIP_DEFLATED) as z:
        for p in classes.rglob('*.class'): z.write(p,p.relative_to(classes).as_posix())
        z.writestr('META-INF/neoforge.mods.toml',meta)
    (output/'awft-material-probe.request.json').write_text(json.dumps({'format':'awft-material-probe:1','root':str(client)},indent=2)+'\n')
    result={'filename':jar.name,'size':jar.stat().st_size,'sha256':digest(jar),'runtime':'not run; test-only, never a release dependency'}
    (output/'build-receipt.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--client',type=Path,required=True);p.add_argument('--libraries',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();print(json.dumps(build(a.client,a.libraries,a.output),indent=2))
