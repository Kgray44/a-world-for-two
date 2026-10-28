"""Produce an isolated exact-base native tree/bee integration for parent review.

Never edits active/frozen source, launches Minecraft, changes a version or grows.
"""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess

HERE=Path(__file__).resolve().parent
BASE=HERE.parent/'worldfortwo/bridge'
PINS={'TreeGrowthScope.java':'d4805f3aa37a4212a9de5f4bff5a09089111b940196a3ec02cc64ccb8a674ba4',
      'NativeTreeGrowthSupport.java':'88a0b496d0e33d0ba09530cf3dff91f892e239a88b49761eb542fa3ff61d193b'}


def replace_once(text,before,after):
    if text.count(before)!=1:raise ValueError('Frozen integration anchor changed: '+before[:90])
    return text.replace(before,after,1)


def sources():
    docs={}
    for name,pin in PINS.items():
        raw=(BASE/name).read_bytes()
        if hashlib.sha256(raw).hexdigest()!=pin:raise ValueError('Frozen native43 proposal changed: '+name)
        docs[name]=raw.decode()
    scope=docs['TreeGrowthScope.java']
    scope=replace_once(scope,'final int soilY;','final int soilY;\n    final boolean allowNativeNest;')
    scope=replace_once(scope,'Set<Long> protectedColumns,int soilY){','Set<Long> protectedColumns,int soilY,boolean allowNativeNest){')
    scope=replace_once(scope,'this.soilY=soilY;','this.soilY=soilY;this.allowNativeNest=allowNativeNest;')
    scope=replace_once(scope,'scope.attempted.add(position.immutable());','TreeBeeAudit.desired(original,desired,scope.allowNativeNest);\n        scope.attempted.add(position.immutable());')
    support=docs['NativeTreeGrowthSupport.java']
    support=replace_once(support,'private void recoverGrowth(TreeGrowthScope scope,Throwable failure,Map<BlockPos,String> beBefore){',
                         'private void recoverGrowth(TreeGrowthScope scope,Throwable failure,Map<BlockPos,String> beBefore,TreeBeeAudit beeAudit){')
    support=replace_once(support,'()->{int restored=scope.restoreFailedAttempt();',
                         '()->{beeAudit.beforeRollback(scope.attempted);int restored=scope.restoreFailedAttempt();')
    support=replace_once(support,'report.put("restored_owned_cells",restored);','beeAudit.restored();report.put("restored_owned_cells",restored);')
    support=replace_once(support,'new TreeGrowthScope(level,before,writeBounds,protectedColumns,root.getY()-1);',
                         'new TreeGrowthScope(level,before,writeBounds,protectedColumns,root.getY()-1,TreeBeeAudit.mayCreateNest(descriptor));\n        TreeBeeAudit beeAudit=null;')
    support=replace_once(support,'scope.hookWitness(root);','beeAudit=new TreeBeeAudit(level,before,writeBounds,scope.allowNativeNest);\n            scope.hookWitness(root);')
    support=replace_once(support,'report.put("native_changed_log_blocks",logs);',
                         'report.put("native_bee_audit",beeAudit.success(scope.attempted));report.put("native_changed_log_blocks",logs);')
    support=replace_once(support,'recoverGrowth(scope,failure,beBefore);','recoverGrowth(scope,failure,beBefore,beeAudit);')
    return {'TreeGrowthScope.java':scope.encode(),'NativeTreeGrowthSupport.java':support.encode(),
            **{name:(HERE/name).read_bytes() for name in ('BeeNestFacts.java','TreeBeeAudit.java')}}


def prepare(output):
    output=Path(output).resolve()
    if output.exists() or not output.is_relative_to(Path('D:/A World for Two/staging').resolve()):raise ValueError('New private D staging folder required')
    subprocess.run(['powershell.exe','-NoProfile','-File','C:/Users/kkids/AppData/Local/AeroStorageWatch/ReserveGuard.ps1',
                    '-EstimatedCBytes','0','-EstimatedDBytes',str(2*1024*1024)],check=True)
    docs=sources();output.mkdir()
    for name,raw in docs.items():(output/name).write_bytes(raw)
    receipt={'status':'ISOLATED_SOURCE_ONLY_NOT_DEPLOYED','base_source_sha256':PINS,
             'files':{name:{'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()} for name,raw in docs.items()},
             'native_grow_or_hive_acceptance':False,'no_versions_or_active_source_changed':True}
    (output/'source-recipe.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
    return receipt


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',required=True)
    print(json.dumps(prepare(parser.parse_args().output)))
