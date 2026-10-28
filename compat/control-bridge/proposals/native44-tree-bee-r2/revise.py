"""Additive correction of sealed bee source; no active Java or runtime mutation."""
from pathlib import Path
import argparse
import difflib
import hashlib
import importlib.util
import json
import subprocess

HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'native44-tree-bee'
PINS={'BeeNestFacts.java':'f6526edb1e97dedcfbdcecccdfa969e42c4cdee7529db261077b6782ce9ae3b1',
      'BeeNestFactsProbe.java':'079d46b55f6af1e1487e7450656ad325d6cb28198577b840b7bfcc5f1c362cf7',
      'README.md':'18973d1448a106f9b0eb3c79ea21061a6d5d50b9f9728e0e477937249b1a5384',
      'TreeBeeAudit.java':'12dac3641b71c4af83a14183f3a0ec231eba244b5683f2f172b77f3380848c87',
      'prepare_source.py':'b59bd7975e9ccb821d8f7a24c6e16e3fc84810676e4cb9fea98bb281fb3031a5',
      'source-provenance.json':'6ae0f2547ea2d1b8631cae08152af0a055a8a2eb5b264f20a3a3aa94f3dea47c'}


def replace(text,before,after):
    if text.count(before)!=1:raise ValueError('Exact sealed integration anchor changed')
    return text.replace(before,after,1)


def source_pair():
    for name,expected in PINS.items():
        if hashlib.sha256((OLD/name).read_bytes()).hexdigest()!=expected:raise ValueError('Do not alter sealed bb2fe source: '+name)
    spec=importlib.util.spec_from_file_location('sealed_bb2fe_tree_bee',OLD/'prepare_source.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    previous=module.sources();corrected=dict(previous)
    scope=previous['TreeGrowthScope.java'].decode()
    scope=replace(scope,'TreeBeeAudit.desired(original,desired,scope.allowNativeNest);',
                  '''try{TreeBeeAudit.desired(original,desired,scope.allowNativeNest);}
        catch(Throwable beeRefusal){
            IllegalStateException refused=denied(scope,"Native bee-nest admission refused");
            refused.addSuppressed(beeRefusal);throw refused;
        }''')
    support=previous['NativeTreeGrowthSupport.java'].decode()
    before='''Map<BlockPos,String> beBefore=nativeBEs();TreeGrowthScope scope=new TreeGrowthScope(level,before,writeBounds,protectedColumns,root.getY()-1,TreeBeeAudit.mayCreateNest(descriptor));
        TreeBeeAudit beeAudit=null;
        try{
            beeAudit=new TreeBeeAudit(level,before,writeBounds,scope.allowNativeNest);
            scope.hookWitness(root);'''
    after='''Map<BlockPos,String> beBefore=nativeBEs();
        TreeBeeAudit beeAudit;
        try{beeAudit=new TreeBeeAudit(level,before,writeBounds,TreeBeeAudit.mayCreateNest(descriptor));}
        catch(Throwable auditInitializationFailure){
            report.put("native_bee_audit_initialization_error",auditInitializationFailure.toString());
            report.put("this_growth_owned_setter_invoked",false);
            if(mutated||worldResidual)quarantine(auditInitializationFailure);
            throw new IllegalStateException("Native bee audit initialization failed before this growth's owned setter",auditInitializationFailure);
        }
        TreeGrowthScope scope=new TreeGrowthScope(level,before,writeBounds,protectedColumns,root.getY()-1,TreeBeeAudit.mayCreateNest(descriptor));
        try{
            scope.hookWitness(root);'''
    support=replace(support,before,after)
    corrected['TreeGrowthScope.java']=scope.encode();corrected['NativeTreeGrowthSupport.java']=support.encode()
    return previous,corrected


def materialize(output,guard=True):
    output=Path(output).resolve()
    if output.exists() or not output.is_relative_to(Path('D:/A World for Two/staging').resolve()):raise ValueError('New owned private D source-revision folder required')
    if guard:subprocess.run(['powershell.exe','-NoProfile','-File','C:/Users/kkids/AppData/Local/AeroStorageWatch/ReserveGuard.ps1','-EstimatedCBytes','0','-EstimatedDBytes',str(2*1024*1024)],check=True)
    previous,corrected=source_pair() # Pin/anchor failures occur before creating output.
    patch=[]
    for name in ('TreeGrowthScope.java','NativeTreeGrowthSupport.java'):
        patch.extend(difflib.unified_diff(previous[name].decode().splitlines(True),corrected[name].decode().splitlines(True),fromfile='sealed-bb2fe/'+name,tofile='additive-r2/'+name))
    output.mkdir()
    for name,raw in corrected.items():(output/name).write_bytes(raw)
    (output/'reviewed-diff.patch').write_text(''.join(patch))
    receipt={'status':'SOURCE_ONLY_JAVA_AND_NATIVE_GATES_PENDING','sealed_original_receipt_sha256':'bb2fe53cfe833e46c5b7ea5b568dfc6a1b8d89c78596564285c3f56cc5af229a',
             'sealed_source_pins':PINS,'changed_source_files':['TreeGrowthScope.java','NativeTreeGrowthSupport.java'],
             'files':{n:{'bytes':len(r),'sha256':hashlib.sha256(r).hexdigest()} for n,r in corrected.items()},
             'java_launched':False,'world_or_active_source_mutations':False}
    (output/'receipt.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
    return receipt


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',required=True);print(json.dumps(materialize(parser.parse_args().output)))
