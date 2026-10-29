"""Generate/compile one diagnostics-only proposal without editing active sources.

No Minecraft process, downloaded code, world, runtime installation or network is
started. The caller must run ReserveGuard with an8MiB C:/0D: bound first.
"""
from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time


BASE_SHA256 = 'b5e97f965a11d73c3db3f7514b2b01bf75b742e9546dd99d773c203757465d52'
TARGET = 'compat/control-bridge/src/worldfortwo/bridge/HarborCraftSupport.java'
METHODS = '''    // Failure-only bounded diagnostics. These observations never admit a craft.
    private static Map<String,Object> custodyStamp(DiskStamp stamp) {
        if(stamp==null)return null;
        return Map.of("bytes",stamp.bytes(),"modified",stamp.modified().toString(),"header_sha256",stamp.offsets());
    }
    private static List<Map<String,Object>> custodyDelta(List<DiskStamp> before,List<DiskStamp> after) {
        Map<String,DiskStamp> old=new TreeMap<>(),now=new TreeMap<>();
        for(DiskStamp stamp:before)old.put(stamp.path().getFileName().toString(),stamp);
        for(DiskStamp stamp:after)now.put(stamp.path().getFileName().toString(),stamp);
        Set<String> names=new TreeSet<>(old.keySet());names.addAll(now.keySet());
        List<Map<String,Object>> changes=new ArrayList<>();
        for(String name:names){DiskStamp a=old.get(name),b=now.get(name);if(Objects.equals(a,b))continue;
            Map<String,Object> row=new LinkedHashMap<>();row.put("path",name);
            row.put("change",a==null?"added":b==null?"removed":"changed");
            row.put("before",custodyStamp(a));row.put("after",custodyStamp(b));changes.add(row);
            if(changes.size()>=64)break;}
        return changes;
    }
    private void recordCustodyChange(Store store,List<DiskStamp> current,PendingUuidSnapshot pending) {
        Map<String,Object> diagnostic=new LinkedHashMap<>();
        diagnostic.put("dimension",store.dimension.dimension().location().toString());
        diagnostic.put("files_before",store.files.size());diagnostic.put("files_after",current.size());
        diagnostic.put("maximum_file_changes",64);diagnostic.put("changes",custodyDelta(store.files,current));
        diagnostic.put("pending_snapshot",Map.of("pending_count",pending.chunks().size(),"chunks",pending.chunks(),
            "regions",pending.regions(),"maximum_chunks",MAX_STORAGE_CHUNKS));
        report.put("custody_change",diagnostic);
    }

'''
OLD = '        for(Store store:stores){if(!store.files.equals(diskFiles(store.path,new LinkedHashSet<>())))throw new IllegalStateException("Persistent entity region custody changed; no creation performed");'
NEW = '''        for(Store store:stores){List<DiskStamp> current=diskFiles(store.path,new LinkedHashSet<>());
            if(!store.files.equals(current)){recordCustodyChange(store,current,pendingSnapshots.get(store));throw new IllegalStateException("Persistent entity region custody changed; no creation performed");}'''

PROBE = '''package worldfortwo.bridge;
import java.lang.reflect.*;
import java.nio.file.Path;
import java.nio.file.attribute.FileTime;
import java.util.*;
public final class CustodyDiagnosticProbe {
    private static void require(boolean value,String label){if(!value)throw new AssertionError(label);}
    public static void main(String[] args)throws Exception {
        Class<?> owner=Class.forName("worldfortwo.bridge.HarborCraftSupport");
        Class<?> stamp=Class.forName("worldfortwo.bridge.HarborCraftSupport$DiskStamp");
        Constructor<?> ctor=stamp.getDeclaredConstructor(Path.class,long.class,FileTime.class,String.class);ctor.setAccessible(true);
        Method delta=owner.getDeclaredMethod("custodyDelta",List.class,List.class);delta.setAccessible(true);
        Object a=ctor.newInstance(Path.of("entities/r.0.0.mca"),8192L,FileTime.fromMillis(1),"a");
        Object b=ctor.newInstance(Path.of("entities/r.0.0.mca"),12288L,FileTime.fromMillis(2),"b");
        Object empty=ctor.newInstance(Path.of("entities/r.1.0.mca"),0L,FileTime.fromMillis(2),"empty");
        require(((List<?>)delta.invoke(null,List.of(a),List.of(a))).isEmpty(),"unchanged");
        List<?> changed=(List<?>)delta.invoke(null,List.of(a),List.of(b));
        require(changed.size()==1&&((Map<?,?>)changed.get(0)).get("change").equals("changed"),"changed row");
        Map<?,?> fields=(Map<?,?>)((Map<?,?>)changed.get(0)).get("after");
        require(fields.get("bytes").equals(12288L)&&fields.get("header_sha256").equals("b")&&fields.get("modified")!=null,"fields");
        Object mtime=ctor.newInstance(Path.of("entities/r.0.0.mca"),8192L,FileTime.fromMillis(2),"a");
        Object header=ctor.newInstance(Path.of("entities/r.0.0.mca"),8192L,FileTime.fromMillis(1),"b");
        require(((List<?>)delta.invoke(null,List.of(a),List.of(mtime))).size()==1,"mtime-only refusal detail");
        require(((List<?>)delta.invoke(null,List.of(a),List.of(header))).size()==1,"header-only refusal detail");
        List<?> added=(List<?>)delta.invoke(null,List.of(a),List.of(a,empty));
        require(added.size()==1&&((Map<?,?>)added.get(0)).get("change").equals("added")&&((Map<?,?>)added.get(0)).get("before")==null,"added placeholder");
        List<?> removed=(List<?>)delta.invoke(null,List.of(a),List.of());
        require(removed.size()==1&&((Map<?,?>)removed.get(0)).get("change").equals("removed")&&((Map<?,?>)removed.get(0)).get("after")==null,"removed");
        List<Object> many=new ArrayList<>();for(int i=0;i<80;i++)many.add(ctor.newInstance(Path.of("entities/r."+i+".0.mca"),0L,FileTime.fromMillis(i),"x"));
        require(((List<?>)delta.invoke(null,List.of(),many)).size()==64,"finite cap");
        System.out.println("PASS: unchanged, changed bytes/mtime/header, mtime-only, header-only, added zero-byte placeholder, removed,64-row cap; no Minecraft world or runtime");
    }
}
'''


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--primary', type=Path, required=True)
    parser.add_argument('--cached-javac-args', type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    source = args.primary/TARGET
    if digest(source) != BASE_SHA256:
        raise SystemExit('Exact reviewed base source changed; rebase proposal before use')
    text = source.read_text(encoding='utf-8')
    anchor = '    private void commit(MinecraftServer server)throws Exception {'
    if text.count(OLD) != 1 or text.count(anchor) != 1:
        raise SystemExit('Expected custody refusal anchor differs')
    proposed = text.replace(anchor, METHODS+anchor).replace(OLD, NEW)
    # Extend the existing same-tick mailbox result, without adding futures,
    # waits or cancellation/resource obligations on the refusal path.
    substitutions = (
        ('    @SuppressWarnings({"unchecked","rawtypes"})\n    private static CompletableFuture<Map<UUID,Integer>> pendingUuidCounts',
         '    private record PendingUuidSnapshot(Map<UUID,Integer> counts,List<List<Integer>> chunks,Set<String> regions){}\n    @SuppressWarnings({"unchecked","rawtypes"})\n    private static CompletableFuture<PendingUuidSnapshot> pendingUuidCounts'),
        ('Supplier<Either<Map<UUID,Integer>,Exception>> query=', 'Supplier<Either<PendingUuidSnapshot,Exception>> query='),
        ('                return Either.left(counts);',
         '                List<List<Integer>> keys=new ArrayList<>();Set<String> regions=new TreeSet<>();\n                for(ChunkPos pos:writes.keySet()){keys.add(List.of(pos.x,pos.z));regions.add("r."+Math.floorDiv(pos.x,32)+"."+Math.floorDiv(pos.z,32)+".mca");}\n                return Either.left(new PendingUuidSnapshot(counts,keys,regions));'),
        ('Map<Store,CompletableFuture<Map<UUID,Integer>>> fresh=', 'Map<Store,CompletableFuture<PendingUuidSnapshot>> fresh='),
        ('        for(var item:fresh.entrySet())for(var count:item.getValue().get(5,TimeUnit.MILLISECONDS).entrySet())queued.put(count.getKey().toString(),queued.get(count.getKey().toString())+count.getValue());',
         '        Map<Store,PendingUuidSnapshot> pendingSnapshots=new LinkedHashMap<>();\n        for(var item:fresh.entrySet()){PendingUuidSnapshot pending=item.getValue().get(5,TimeUnit.MILLISECONDS);pendingSnapshots.put(item.getKey(),pending);\n            for(var count:pending.counts().entrySet())queued.put(count.getKey().toString(),queued.get(count.getKey().toString())+count.getValue());}'),
    )
    for old, new in substitutions:
        if proposed.count(old) != 1:
            raise SystemExit('Exact pending-snapshot anchor differs')
        proposed = proposed.replace(old, new)
    patch = ''.join(difflib.unified_diff(text.splitlines(True), proposed.splitlines(True),
                    fromfile='a/'+TARGET, tofile='b/'+TARGET))
    work = root/'.local'/('probe-'+str(time.time_ns()))
    work.mkdir(parents=True, exist_ok=False)
    for name in ('HarborCraftSupport.patch', 'verification.json'):
        if (root/name).exists():
            (work/('prior-'+name)).write_bytes((root/name).read_bytes())
    (root/'HarborCraftSupport.patch').write_text(patch, encoding='utf-8', newline='\n')
    java = work/'src/worldfortwo/bridge/HarborCraftSupport.java'
    java.parent.mkdir(parents=True)
    java.write_text(proposed, encoding='utf-8', newline='\n')
    probe = java.with_name('CustodyDiagnosticProbe.java')
    probe.write_text(PROBE, encoding='utf-8', newline='\n')
    cached = args.cached_javac_args.read_text(encoding='utf-8').splitlines()
    cp = cached[cached.index('-classpath')+1].strip('"')
    cached_classes = args.cached_javac_args.parent/'classes'
    if not (cached_classes/'worldfortwo/bridge/NativeJournal.class').is_file():
        raise SystemExit('Exact prior named compile classes unavailable')
    # Reuse cached compile-only APIs/classes; never extract/download/install.
    cp = str(cached_classes)+os.pathsep+cp
    classes = work/'classes'
    classes.mkdir()
    argfile = work/'javac.args'
    argfile.write_text('-proc:none\n--release\n21\n-classpath\n"'+cp.replace('\\','/')+'"\n-d\n"'+classes.as_posix()+'"\n"'+java.as_posix()+'"\n"'+probe.as_posix()+'"\n')
    jdk = Path(r'C:\Program Files\Java\jdk-21.0.10\bin')
    flags = subprocess.CREATE_NO_WINDOW | subprocess.BELOW_NORMAL_PRIORITY_CLASS if os.name == 'nt' else 0
    compiled = subprocess.run([str(jdk/'javac.exe'), '-J-Xmx256m', '-J-XX:ActiveProcessorCount=2', '@'+str(argfile)],
                              capture_output=True, text=True, timeout=60, creationflags=flags)
    (work/'javac.log').write_text(compiled.stdout+compiled.stderr)
    receipt = {'format': 'awft-fleet-custody-diagnostics-probe:1', 'base_source_sha256': BASE_SHA256,
               'proposed_source_sha256': digest(java), 'patch_sha256': digest(root/'HarborCraftSupport.patch'),
               'cached_javac_args_sha256': digest(args.cached_javac_args), 'javac_exit_code': compiled.returncode,
               'active_source_changed': False, 'native_world_operations': 0, 'runtime_installations': 0}
    if compiled.returncode == 0:
        ran = subprocess.run([str(jdk/'java.exe'), '-Xmx128m', '-XX:ActiveProcessorCount=2', '-XX:-UsePerfData',
                              '-classpath', str(classes)+os.pathsep+cp, 'worldfortwo.bridge.CustodyDiagnosticProbe'],
                             capture_output=True, text=True, timeout=30, creationflags=flags)
        (work/'probe.log').write_text(ran.stdout+ran.stderr)
        receipt.update(probe_exit_code=ran.returncode, probe_stdout=ran.stdout.strip())
    (root/'verification.json').write_text(json.dumps(receipt, indent=2)+'\n')
    print(json.dumps(receipt))
    if compiled.returncode:
        print(compiled.stderr[:4000])
    raise SystemExit(compiled.returncode or receipt.get('probe_exit_code', 1))


if __name__ == '__main__':
    main()
