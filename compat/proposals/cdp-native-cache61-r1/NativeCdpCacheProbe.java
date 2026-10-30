package worldfortwo.bridge;

import java.io.ByteArrayInputStream;
import java.io.InputStream;
import java.lang.reflect.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.Path;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicBoolean;
import com.google.common.hash.HashCode;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.packs.PackResources;
import net.minecraft.server.packs.PackType;
import net.minecraft.server.packs.resources.IoSupplier;
import net.neoforged.neoforgespi.locating.IModFile;
import org.objectweb.asm.*;
import org.objectweb.asm.tree.*;

/** Actual pinned native HashMap writer, actual production transform; no game or world. */
public final class NativeCdpCacheProbe {
    private static final int THREADS=8,PER_THREAD=256,ROUNDS=24;
    private static final Path ROOT=Path.of("native-cdp-field").toAbsolutePath();
    private static final HashCode HASH=HashCode.fromInt(1);
    private static final sun.misc.Unsafe UNSAFE;
    static{try{Field f=sun.misc.Unsafe.class.getDeclaredField("theUnsafe");f.setAccessible(true);UNSAFE=(sun.misc.Unsafe)f.get(null);}catch(Exception e){throw new ExceptionInInitializerError(e);}}
    public static void main(String[] args)throws Exception {
        var origin=NativeCdpCacheProbe.class.getClassLoader().getResource(CdpRuntimeCacheWritePlugin.RESOURCE);
        byte[] original;try(InputStream in=Objects.requireNonNull(origin).openStream()){original=in.readAllBytes();}
        ClassNode node=new ClassNode();new ClassReader(original).accept(node,0);
        String witness=CdpRuntimeCacheWritePlugin.repairExact(node,origin);
        ClassWriter output=new ClassWriter(ClassWriter.COMPUTE_MAXS);node.accept(output);byte[] fixed=output.toByteArray();
        Class<?> old=Class.forName(CdpRuntimeCacheWritePlugin.TARGET),changed=new ClassLoader(NativeCdpCacheProbe.class.getClassLoader()){
            Class<?> define(){return defineClass(CdpRuntimeCacheWritePlugin.TARGET,fixed,0,fixed.length);}
        }.define();
        int corruptRound=0,oldReported=-1,oldIterated=-1,oldReachable=-1;
        for(int round=1;round<=ROUNDS;round++){
            var map=new HashMap<Path,IoSupplier<InputStream>>();Object pack=pack(old,map);writeRound(pack,round);
            int iterated=new HashSet<>(map.keySet()).size(),reachable=reachable(map,round);
            if(map.size()!=THREADS*PER_THREAD+1||iterated!=THREADS*PER_THREAD+1||reachable!=THREADS*PER_THREAD){corruptRound=round;oldReported=map.size();oldIterated=iterated;oldReachable=reachable;break;}
        }
        if(corruptRound==0)throw new AssertionError("Bounded actual-native HashMap race did not reproduce; retain inconclusive result, do not increase trials automatically");
        int verified=0;
        for(int round=1;round<=ROUNDS;round++){
            var map=new HashMap<Path,IoSupplier<InputStream>>();PackResources pack=(PackResources)pack(changed,map);writeRound(pack,round);
            if(map.size()!=THREADS*PER_THREAD+1||new HashSet<>(map.keySet()).size()!=THREADS*PER_THREAD+1||reachable(map,round)!=THREADS*PER_THREAD)
                throw new AssertionError("Fixed native writer lost entries");
            if(!pack.getNamespaces(PackType.SERVER_DATA).equals(Set.of("..","demo")))throw new AssertionError("Native namespaces changed");
            var listed=new HashMap<ResourceLocation,IoSupplier<InputStream>>();pack.listResources(PackType.SERVER_DATA,"demo","",listed::put);
            if(listed.size()!=THREADS*PER_THREAD)throw new AssertionError("Native listing incomplete");
            for(int t=0;t<THREADS;t++)for(int i=0;i<PER_THREAD;i++){
                var id=ResourceLocation.parse("demo:recipe/"+name(round,t,i)+".json");var selected=pack.getResource(PackType.SERVER_DATA,id);
                if(selected==null||selected!=listed.get(id))throw new AssertionError("Native list/get supplier changed");
                try(var in=selected.get()){if(!Arrays.equals(in.readAllBytes(),bytes(round,t,i)))throw new AssertionError("Native bytes changed");}verified++;
            }
        }
        var observed=new MonitorMap();Object pack=pack(changed,observed);Method write=writer(pack);observed.check=true;
        write.invoke(pack,path(0,0,0),new byte[]{1},HASH);if(!observed.held.get())throw new AssertionError("Wrong monitor");
        observed.fail=true;try{write.invoke(pack,path(0,0,1),new byte[]{2},HASH);throw new AssertionError("Native exception suppressed");}
        catch(InvocationTargetException expected){if(!(expected.getCause() instanceof IllegalArgumentException))throw expected;}
        if(Thread.holdsLock(observed))throw new AssertionError("Map monitor leaked on failure");
        Thread other=new Thread(()->{synchronized(observed){observed.reacquired.set(true);}});other.start();other.join(2000);
        if(other.isAlive()||!observed.reacquired.get())throw new AssertionError("Other thread cannot acquire map after failure");
        ClassNode modified=new ClassNode();new ClassReader(original).accept(modified,0);
        modified.methods.stream().filter(m->m.name.equals("writeIfNeeded")).findFirst().orElseThrow().instructions.insert(new InsnNode(Opcodes.NOP));
        try{CdpRuntimeCacheWritePlugin.repairExact(modified,origin);throw new AssertionError("Modified native body accepted");}catch(IllegalStateException expected){}
        System.out.println("PROBE_RESULT {\"passed\":true,\"native_old_HashMap_corruption_observed\":true,\"old_round\":"+corruptRound+",\"old_reported_size\":"+oldReported+",\"old_iterated_entries\":"+oldIterated+",\"old_reachable_resources\":"+oldReachable+",\"fixed_rounds\":"+ROUNDS+",\"native_supplier_bytes_verified\":"+verified+",\"existing_map_monitor_verified\":true,\"exception_and_unlock_verified\":true,\"modified_method_refused\":true,\"world_started\":false}");
        System.out.println("METHOD_WITNESS "+witness);
    }
    private static Object pack(Class<?> type,Map<Path,IoSupplier<InputStream>> map)throws Exception {
        Object object=UNSAFE.allocateInstance(type);
        IModFile file=(IModFile)Proxy.newProxyInstance(IModFile.class.getClassLoader(),new Class<?>[]{IModFile.class},(p,m,a)->{
            if(m.getName().equals("findResource")){Path result=ROOT;for(String part:(String[])a[0])result=result.resolve(part);return result;}
            if(m.getName().equals("toString"))return "offline actual native cache fixture";throw new UnsupportedOperationException(m.getName());});
        for(Field f:type.getDeclaredFields())if(!Modifier.isStatic(f.getModifiers())){
            if(f.getName().equals("resources")){f.setAccessible(true);f.set(object,map);}
            if(f.getName().equals("file")){f.setAccessible(true);f.set(object,file);}
            if(f.getName().equals("type")){f.setAccessible(true);f.set(object,PackType.SERVER_DATA);}
        }
        map.put(ROOT.resolve("icon.png"),()->new ByteArrayInputStream(new byte[]{8}));return object;
    }
    private static Method writer(Object pack)throws Exception{return pack.getClass().getMethod("writeIfNeeded",Path.class,byte[].class,HashCode.class);}
    private static String name(int r,int t,int i){return "r"+r+"t"+t+"n"+i;}
    private static Path path(int r,int t,int i){return ROOT.resolve("data/demo/recipe/"+name(r,t,i)+".json");}
    private static byte[] bytes(int r,int t,int i){return ("native-"+name(r,t,i)).getBytes(StandardCharsets.UTF_8);}
    private static int reachable(Map<Path,?> map,int r){int n=0;for(int t=0;t<THREADS;t++)for(int i=0;i<PER_THREAD;i++)if(map.get(path(r,t,i))!=null)n++;return n;}
    private static void writeRound(Object pack,int round)throws Exception {
        Method writer=writer(pack);CountDownLatch ready=new CountDownLatch(THREADS),start=new CountDownLatch(1);
        ExecutorService executor=Executors.newFixedThreadPool(THREADS,r->{Thread t=new Thread(r,"bounded-native-cdp-writer");t.setDaemon(true);return t;});
        List<Future<?>> pending=new ArrayList<>();
        try{
            for(int t=0;t<THREADS;t++){final int thread=t;pending.add(executor.submit(()->{ready.countDown();try{start.await();for(int i=0;i<PER_THREAD;i++)writer.invoke(pack,path(round,thread,i),bytes(round,thread,i),HASH);}catch(Exception failure){throw new RuntimeException(failure);}}));}
            if(!ready.await(5,TimeUnit.SECONDS))throw new AssertionError("Fixture workers did not start");start.countDown();for(Future<?> future:pending)future.get(10,TimeUnit.SECONDS);
        }finally{start.countDown();executor.shutdownNow();if(!executor.awaitTermination(2,TimeUnit.SECONDS))throw new AssertionError("Owned fixture workers did not terminate");}
    }
    private static final class MonitorMap extends HashMap<Path,IoSupplier<InputStream>> {
        boolean check,fail;final AtomicBoolean held=new AtomicBoolean(),reacquired=new AtomicBoolean();
        @Override public IoSupplier<InputStream> put(Path key,IoSupplier<InputStream> value){if(check){if(!Thread.holdsLock(this))throw new AssertionError("Native writer did not lock resources map");held.set(true);if(fail)throw new IllegalArgumentException("actual native put exception fixture");}return super.put(key,value);}
    }
}
