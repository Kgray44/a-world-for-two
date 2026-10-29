"""Add only the exact native MCW interaction-flag custody read to frozen R6."""
from pathlib import Path
import hashlib

HERE=Path(__file__).resolve().parent
BASE=HERE.parent/'native-relocation-window-r6'
PINS={'NativeWindowStateWitness.java':'f43048c37747be291d3bbd48acbdb83bf4c0997fd0f66b3b2ec33960886fe36c',
      'NativeRelocationSupport.java':'cc63c079a42f502955ee9cba2a6a1d8af25669e93f36374c75e7a8f0beda5c02'}

def one(s,old,new):
    if s.count(old)!=1:raise RuntimeError('Exact frozen R6 source site required')
    return s.replace(old,new)

def derive():
    for name,sha in PINS.items():
        raw=(BASE/name).read_bytes()
        if hashlib.sha256(raw).hexdigest()!=sha:raise RuntimeError('FrozenR6 changed')
        if name=='NativeRelocationSupport.java':(HERE/name).write_bytes(raw);continue
        s=raw.decode()
        s=one(s,'import java.lang.reflect.Proxy;','import java.lang.reflect.Proxy;\nimport java.lang.invoke.MethodHandles;')
        s=one(s,'    private static void sameNonPart(BlockState original,BlockState value){','''    private static void requireNativeCalculationEnabled(BlockState original)throws Exception{
        // Exact declared member resolution only. Never enumerate native fields,
        // call its mutating setter, or change the shared Block singleton.
        Class<?> type=original.getBlock().getClass();
        var flag=MethodHandles.privateLookupIn(type,MethodHandles.lookup()).findVarHandle(type,"wasInteractedWith",boolean.class);
        if((boolean)flag.getVolatile(original.getBlock()))throw new IllegalStateException("Native MCW interaction bypass active; no contextual expectation can be proved");
    }
    private static void sameNonPart(BlockState original,BlockState value){''')
        s=one(s,'        pin(original);sameNonPart(original,actual);','        pin(original);sameNonPart(original,actual);requireNativeCalculationEnabled(original);')
        s=one(s,'        sameNonPart(original,expected);','        sameNonPart(original,expected);requireNativeCalculationEnabled(original);')
        s=one(s,'        proof.addProperty("expected_from_actual_result",false);','        proof.addProperty("native_interaction_bypass_false_before_and_after",true);\n        proof.addProperty("expected_from_actual_result",false);')
        (HERE/name).write_text(s,encoding='utf8',newline='\n')
    for name in PINS:print(name,hashlib.sha256((HERE/name).read_bytes()).hexdigest())

if __name__=='__main__':derive()
