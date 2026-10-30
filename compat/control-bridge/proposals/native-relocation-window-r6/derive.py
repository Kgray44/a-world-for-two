"""R6 narrow native-context state witness; frozenR5 and active55 untouched."""
from pathlib import Path
import hashlib
ROOT=Path(__file__).resolve().parent
BASE=ROOT.parent/'native-relocation-complete-r5/NativeRelocationSupport.java'
EXPECTED='04d42b4df8bd93928640d95ba52e475990d64e1fcb38af84d6c7474ac6292c58'

def change(s,old,new):
    if s.count(old)!=1:raise RuntimeError('Exact frozen R5 source site required: '+old[:90])
    return s.replace(old,new)

def derive():
    raw=BASE.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=EXPECTED:raise RuntimeError('FrozenR5 changed')
    s=raw.decode()
    s=change(s,'!classHash(NativeToolboxCustody.class).equals(request.get("toolbox_custody_class_sha256").getAsString())','!classHash(NativeToolboxCustody.class).equals(request.get("toolbox_custody_class_sha256").getAsString())||!classHash(NativeWindowStateWitness.class).equals(request.get("native_window_witness_class_sha256").getAsString())')
    s=change(s,'        String id=BuiltInRegistries.BLOCK.getKey(state.getBlock()).toString();if(!id.startsWith("mcwwindows:"))return;', '''        String id=BuiltInRegistries.BLOCK.getKey(state.getBlock()).toString();if(!id.startsWith("mcwwindows:"))return;
        if(NativeWindowStateWitness.applies(state)){
            NativeWindowStateWitness.pin(state);
            if(!report.containsKey("native_MCW_read_only_counterfactuals"))report.put("native_MCW_read_only_counterfactuals",NativeWindowStateWitness.counterfactuals(state,level.getBlockState(p),level,p));
            return;
        }''')
    old='            for(var e:source.entrySet()){BlockPos q=translated(e.getKey());if(!level.getBlockState(q).equals(e.getValue())||!level.getBlockState(q).canSurvive(level,q))throw new IllegalStateException("Native move destination full state/survival differs; retain evidence without fitting expected states");}'
    new='''            JsonArray windowWitnesses=new JsonArray();int windowsChecked=0;
            for(var e:source.entrySet()){
                BlockPos q=translated(e.getKey());BlockState original=e.getValue(),actual=level.getBlockState(q);
                if(NativeWindowStateWitness.applies(original)){
                    var derived=NativeWindowStateWitness.validate(original,actual,level,q);windowsChecked++;
                    if(!derived.expected().equals(original)){JsonObject w=derived.witness();w.add("position",JSON.toJsonTree(xyz(q)));windowWitnesses.add(w);}
                }else if(!actual.equals(original))throw new IllegalStateException("Native move destination full state differs; no unknown normalization");
                if(!actual.canSurvive(level,q))throw new IllegalStateException("Native move destination survival failed; never relaxed");
            }
            report.put("native_MCW_windows_checked",windowsChecked);report.put("native_MCW_part_derivations",windowWitnesses);'''
    s=change(s,old,new)
    # The audit separately records literal-source differences and exact native
    # contextual expectation. It never treats the observed actual part as input.
    old='            if(!dst.equals(e.getValue()))destinationDifferences.add(row.deepCopy());if(!dst.canSurvive(level,d))survivalFailures.add(row.deepCopy());'
    new='''            if(NativeWindowStateWitness.applies(e.getValue())){
                try{var nativeExpected=NativeWindowStateWitness.validate(e.getValue(),dst,level,d);row.add("exact_native_MCW_context_witness",nativeExpected.witness());}
                catch(Exception|LinkageError mismatch){row.addProperty("native_expectation_error",mismatch.getClass().getName()+": "+String.valueOf(mismatch.getMessage()));destinationDifferences.add(row.deepCopy());}
            }else if(!dst.equals(e.getValue()))destinationDifferences.add(row.deepCopy());
            if(!dst.canSurvive(level,d))survivalFailures.add(row.deepCopy());'''
    s=change(s,old,new)
    # Restart/current inspection must use the same true native full-state rule,
    # while all BE data still compares the immutable actual pre-move snapshots.
    old='                for(var e:source.entrySet())if(!level.getBlockState(translated(e.getKey())).equals(e.getValue()))throw new IllegalStateException("Moved geometry changed after completion");'
    new='''                for(var e:source.entrySet()){
                    BlockPos q=translated(e.getKey());BlockState actual=level.getBlockState(q);
                    if(NativeWindowStateWitness.applies(e.getValue()))NativeWindowStateWitness.validate(e.getValue(),actual,level,q);
                    else if(!actual.equals(e.getValue()))throw new IllegalStateException("Moved geometry changed after completion");
                }'''
    s=change(s,old,new)
    (ROOT/'NativeRelocationSupport.java').write_text(s,encoding='utf8',newline='\n');print(hashlib.sha256((ROOT/'NativeRelocationSupport.java').read_bytes()).hexdigest())

if __name__=='__main__':derive()
