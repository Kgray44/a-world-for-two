package worldfortwo.bridge;

import com.google.common.collect.Multimap;
import com.google.gson.Gson;
import java.io.*;
import java.lang.invoke.*;
import java.nio.file.*;
import java.nio.file.attribute.BasicFileAttributes;
import java.security.MessageDigest;
import java.time.Instant;
import java.util.*;
import java.util.concurrent.atomic.AtomicReference;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.packs.*;
import net.minecraft.server.packs.resources.ResourceManager;
import net.mehvahdjukaar.moonlight.api.events.EarlyPackReloadEvent;
import net.mehvahdjukaar.moonlight.api.misc.IProgressTracker;
import net.mehvahdjukaar.moonlight.api.resources.pack.DynamicResourcesProvider;
import net.neoforged.fml.ModList;
import net.neoforged.fml.loading.FMLPaths;

/** Proposal: genuine early SERVER_DATA lifecycle before SeedGen registry loading.
 * Original providers/resources/order, generation, codecs and strict checks stay native.
 * No world/server/account is created. Cache rollback is retained, never automatic.
 */
public final class MoonlightSeedgenInitialization {
    public interface GenerationObserved {}
    public interface StateObserved {}
    public interface WriteObserved {}
    public interface ProductionObserved {}
    public interface SupplementariesObserved {}
    private static final AtomicReference<Scope> ACTIVE=new AtomicReference<>();
    private static boolean poisoned;
    private static final long RESERVE=32_212_254_720L,ALLOCATION=1024L*1024*1024;
    private static final long LIMIT=MoonlightPreparationBudget.BYTE_LIMIT;
    private static final String CACHE="net.mehvahdjukaar.moonlight.api.resources.pack.CachePathPackResources";
    private static final String INTERNAL="net.mehvahdjukaar.moonlight.core.pack.DynamicResourcesInternals";
    private static final String PROVIDER="net.mehvahdjukaar.supplementaries.dynamicpack.ModServerDynamicResources";
    private static final Gson JSON=new Gson();
    private MoonlightSeedgenInitialization(){}

    public static synchronized void initialize(PackType type,List<PackResources> opened,ResourceManager manager)throws Throwable {
        if(!ModList.get().isLoaded("moonlight"))return;
        if(poisoned)throw new IOException("Previous native Moonlight preparation failed; preserve evidence and restart client");
        if(type!=PackType.SERVER_DATA||opened.isEmpty()||opened.size()>512)
            throw new IOException("Bounded original SERVER_DATA pack list required");
        List<PackResources> actual=manager.listPacks().toList();
        if(!same(actual,opened))throw new IOException("Use the actual native opened pack order");
        MoonlightInitializationPins.verify();
        ClassLoader loader=MoonlightSeedgenInitialization.class.getClassLoader();
        Class<?> internal=Class.forName(INTERNAL,false,loader);
        Class<?> sink=Class.forName("net.mehvahdjukaar.moonlight.api.resources.pack.ResourceSink",false,loader);
        if(!GenerationObserved.class.isAssignableFrom(DynamicResourcesProvider.class)
                ||!StateObserved.class.isAssignableFrom(internal)||!ProductionObserved.class.isAssignableFrom(sink))
            throw new IOException("Required native failure/state/production observers absent");
        var lookup=MethodHandles.privateLookupIn(internal,MethodHandles.lookup());
        Multimap<?,?> all=(Multimap<?,?>)lookup.findStaticGetter(internal,"PROVIDERS",Multimap.class).invoke();
        @SuppressWarnings("unchecked") Collection<DynamicResourcesProvider> providers=
                List.copyOf(((Multimap<PackType,DynamicResourcesProvider>)all).get(type));
        if(providers.size()!=1)throw new IOException("Review additional actual server-data providers before initialization");
        DynamicResourcesProvider provider=providers.iterator().next();
        PackResources pack=provider.getPackResources();
        if(!provider.getClass().getName().equals(PROVIDER)||!SupplementariesObserved.class.isAssignableFrom(provider.getClass())||provider.getPackType()!=type
                ||!provider.getName().toString().equals("supplementaries:generated_pack")
                ||!pack.getClass().getName().equals(CACHE)||!pack.packId().equals("supplementaries:generated_pack")
                ||!opened.stream().anyMatch(value->value==pack)||!WriteObserved.class.isAssignableFrom(pack.getClass()))
            throw new IOException("Exact registered selected native provider/resource identity required");
        MethodHandle debug=MethodHandles.privateLookupIn(DynamicResourcesProvider.class,MethodHandles.lookup())
                .findVirtual(DynamicResourcesProvider.class,"generateDebugResources",MethodType.methodType(boolean.class));
        if((boolean)debug.invoke(provider))throw new IOException("Asynchronous native debug dumps require separate custody; not admitted");
        var system=java.lang.management.ManagementFactory.getOperatingSystemMXBean();
        if(!(system instanceof com.sun.management.OperatingSystemMXBean os)||os.getFreeMemorySize()<1024L*1024*1024)
            throw new IOException("Insufficient host memory for native dynamic-data initialization");
        Class<?> base=pack.getClass().getSuperclass();
        Path root=(Path)MethodHandles.privateLookupIn(base,MethodHandles.lookup()).findGetter(base,"path",Path.class).invoke(pack);
        Path configured=FMLPaths.GAMEDIR.get().toAbsolutePath().normalize();
        Path game=configured.toRealPath(),cache=game.resolve("dynamic-data-pack-cache");
        if(Files.exists(cache,LinkOption.NOFOLLOW_LINKS))ordinary(cache);
        if(root==null||(!root.toAbsolutePath().normalize().equals(cache.resolve("supplementaries-generated_pack"))
                &&!root.toAbsolutePath().normalize().equals(configured.resolve("dynamic-data-pack-cache/supplementaries-generated_pack"))))
            throw new IOException("Exact native dynamic-data cache root required");
        long block=Files.getFileStore(game).getBlockSize();
        if(block<=0||block>65536)throw new IOException("Reviewed allocation block bound required");
        for(Path drive:List.of(Path.of("C:/"),Path.of("D:/"),game))if(Files.exists(drive)){
            long extra=Files.getFileStore(drive).equals(Files.getFileStore(game))?ALLOCATION:0;
            if(Files.getFileStore(drive).getUsableSpace()<RESERVE+extra)throw new IOException("Host reserve unavailable for bounded native cache preparation");
        }
        Path privateRoot=game.resolve("awft-private");directory(privateRoot);
        MoonlightPreparationGate.requireClear(privateRoot);
        Path folder=privateRoot.resolve("moonlight-"+Long.toUnsignedString(System.nanoTime()));Files.createDirectory(folder);
        Scope scope=new Scope(pack,provider,opened,manager,folder,root);
        Map<String,Object> receipt=new LinkedHashMap<>();receipt.put("format","awft-native-moonlight-preparation:1");
        receipt.put("at",Instant.now().toString());receipt.put("strict_parity_proved",false);
        receipt.put("native_phase_completed",false);receipt.put("maximum_additional_bytes",ALLOCATION);
        byte[] marker=JSON.toJson(Map.of("format","awft-moonlight-preparation-pending:1","backup",folder.getFileName().toString(),
                "strict_parity_proved",false,"automatic_restore_or_retry",false)).getBytes(java.nio.charset.StandardCharsets.UTF_8);
        try{
            receipt.put("cache_previously_present",Files.exists(cache,LinkOption.NOFOLLOW_LINKS));
            if(Files.exists(cache,LinkOption.NOFOLLOW_LINKS))backup(cache,folder.resolve("before"),scope.budget);
            // The old hash may still match after a partially failed regeneration.
            // Persist an independent gate before ANY native preparation side effect.
            MoonlightPreparationGate pending=MoonlightPreparationGate.create(privateRoot,marker);
            if(!ACTIVE.compareAndSet(null,scope))throw new IOException("Native resource preparation is already active");
            IProgressTracker.Tree tree=IProgressTracker.createTree(1);
            IProgressTracker progress=count->{
                if(count!=1)throw scope.refuse("Exact reviewed Supplementaries single generation task required");
                IProgressTracker.Task task=tree.subtask(count);scope.task(task);return task;
            };
            var dispatch=lookup.findStatic(internal,"lambda$init$2",MethodType.methodType(void.class,EarlyPackReloadEvent.class));
            // Exact native refreshState -> prepare -> filtered reload -> state commit.
            // Native exceptions that are normally logged/absorbed are observed below.
            dispatch.invoke(new EarlyPackReloadEvent(opened,manager,type,progress));
            scope.verify();
            if(!same(manager.listPacks().toList(),opened))throw scope.refuse("Native opened resources changed during preparation");
            pending.complete();
            receipt.put("native_phase_completed",true);
        }catch(Throwable failure){
            poisoned=true;receipt.put("failure_class",failure.getClass().getName());
            receipt.put("failure","Native preparation refused; retain original cache backup and partial output; no retry or automatic restoration");
            throw failure;
        }finally{
            ACTIVE.compareAndSet(scope,null);
            receipt.put("written_resources",scope.writes.size());receipt.put("written_bytes_accounted",scope.budget.written());
            receipt.put("produced_bytes_accounted",scope.budget.produced());receipt.put("elapsed_ms",(System.nanoTime()-scope.started)/1_000_000L);
            Files.writeString(folder.resolve("receipt.json"),JSON.toJson(receipt),StandardOpenOption.CREATE_NEW);
        }
    }

    public static void generationFailed(Object provider){Scope s=ACTIVE.get();if(s!=null&&s.provider==provider)s.budget.fail("Native generation logged a failure");}
    public static void resourceFailed(){Scope s=ACTIVE.get();if(s!=null)s.budget.fail("Native resource production logged a failure");}
    public static void taskFailed(Object task,Throwable failure){Scope s=ACTIVE.get();if(s!=null&&failure!=null&&s.owns(task))s.budget.fail("Native generation task failed");}
    public static void beforeStateCommit()throws IOException{Scope s=ACTIVE.get();if(s!=null)s.verify();}
    public static void produced(byte[] bytes){Scope s=ACTIVE.get();if(s!=null)s.production(bytes);}
    public static void beforeWrite(Object pack,ResourceLocation id,byte[] bytes){Scope s=ACTIVE.get();if(s!=null&&s.pack==pack)s.write(id,bytes);}

    private record Stamp(int bytes,String sha){}
    private static final class Scope {
        final PackResources pack;final Object provider;final List<PackResources> opened;final ResourceManager manager;
        final Path folder,cacheRoot;final Set<String> namespaces;final long started=System.nanoTime();
        final MoonlightPreparationBudget budget=new MoonlightPreparationBudget(started);
        final Set<Object> tasks=Collections.newSetFromMap(new IdentityHashMap<>());
        final Map<ResourceLocation,Stamp>writes=new LinkedHashMap<>();
        Scope(PackResources pack,Object provider,List<PackResources> opened,ResourceManager manager,Path folder,Path cacheRoot){
            this.pack=pack;this.provider=provider;this.opened=List.copyOf(opened);this.manager=manager;this.folder=folder;
            this.cacheRoot=cacheRoot;
            this.namespaces=Set.copyOf(pack.getNamespaces(PackType.SERVER_DATA));
        }
        synchronized void task(Object task){tasks.add(task);}
        synchronized boolean owns(Object task){return tasks.contains(task);}
        synchronized IllegalStateException refuse(String reason){return budget.refuse(reason);}
        synchronized void check(){budget.check(System.nanoTime());}
        synchronized void production(byte[] bytes){budget.produce(bytes==null?-1:bytes.length,System.nanoTime());}
        synchronized void write(ResourceLocation id,byte[] bytes){
            budget.write(id==null?null:id.toString(),bytes==null?-1:bytes.length,System.nanoTime());
            try{
                // Observe safety before the original native writer creates directories/files.
                Path target=cacheRoot.resolve("data").resolve(id.getNamespace()).resolve(id.getPath());
                Path walk=cacheRoot.getParent();
                if(Files.exists(walk,LinkOption.NOFOLLOW_LINKS))ordinary(walk);
                for(Path part:walk.relativize(target)){
                    walk=walk.resolve(part);
                    if(Files.exists(walk,LinkOption.NOFOLLOW_LINKS)){
                        var a=Files.readAttributes(walk,BasicFileAttributes.class,LinkOption.NOFOLLOW_LINKS);
                        if(a.isOther()||a.isSymbolicLink()||(!walk.equals(target)&&!a.isDirectory())
                                ||(walk.equals(target)&&!a.isRegularFile()))throw new IOException("Ordinary native cache output required");
                    }
                }
            }catch(IOException failure){throw refuse("Native cache output path custody failed");}
            writes.put(id,new Stamp(bytes.length,sha(bytes)));
        }
        synchronized void verify()throws IOException{
            check();
            if(!namespaces.equals(pack.getNamespaces(PackType.SERVER_DATA)))throw refuse("Native namespaces changed after the manager was constructed");
            // This existing strict view never manufactures empty resources.
            MoonlightCachePackCustody.inspect(pack).unchanged();
            for(var entry:writes.entrySet()){
                var supplier=pack.getResource(PackType.SERVER_DATA,entry.getKey());
                if(supplier==null)throw refuse("A native produced resource was not published");
                try(InputStream in=supplier.get()){
                    byte[] raw=in.readNBytes(entry.getValue().bytes+1);
                    if(raw.length!=entry.getValue().bytes||!sha(raw).equals(entry.getValue().sha))throw refuse("Native produced and readable bytes differ");
                }
            }
            // Full original raw/selected/effective attestation, before global cache state publication.
            LithostitchedSeedgenResources.capture(opened,manager);
            check();
        }
    }

    private static boolean same(List<PackResources>a,List<PackResources>b){if(a.size()!=b.size())return false;for(int i=0;i<a.size();i++)if(a.get(i)!=b.get(i))return false;return true;}
    private static String sha(byte[]raw){try{return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(raw));}catch(Exception e){throw new AssertionError(e);}}
    private static void ordinary(Path path)throws IOException{var a=Files.readAttributes(path,BasicFileAttributes.class,LinkOption.NOFOLLOW_LINKS);if(!a.isDirectory()||a.isSymbolicLink()||a.isOther())throw new IOException("Ordinary native cache directory required");}
    private static void directory(Path path)throws IOException{if(Files.exists(path,LinkOption.NOFOLLOW_LINKS))ordinary(path);else Files.createDirectory(path);}
    private static void backup(Path source,Path destination,MoonlightPreparationBudget budget)throws IOException{
        Files.createDirectory(destination);long[] bytes={0};int[] entries={0};
        Files.walkFileTree(source,Set.of(),32,new SimpleFileVisitor<>(){
            public FileVisitResult preVisitDirectory(Path dir,BasicFileAttributes a)throws IOException{
                budget.check(System.nanoTime());
                if(++entries[0]>4096||a.isSymbolicLink()||a.isOther()||!dir.toRealPath().startsWith(source.toRealPath()))throw new IOException("Bounded ordinary cache backup required");
                if(!dir.equals(source))Files.createDirectory(destination.resolve(source.relativize(dir)));return FileVisitResult.CONTINUE;
            }
            public FileVisitResult visitFile(Path file,BasicFileAttributes a)throws IOException{
                budget.check(System.nanoTime());
                if(++entries[0]>4096||!a.isRegularFile()||a.isSymbolicLink()||a.isOther())throw new IOException("Bounded ordinary cache files required");
                Path target=destination.resolve(source.relativize(file));
                try(InputStream in=Files.newInputStream(file);OutputStream out=Files.newOutputStream(target,StandardOpenOption.CREATE_NEW)){
                    byte[] buffer=new byte[8192];for(int n;(n=in.read(buffer))!=-1;){budget.check(System.nanoTime());if((bytes[0]+=n)>LIMIT)throw new IOException("Cache backup allocation exceeded");out.write(buffer,0,n);}
                }
                var after=Files.readAttributes(file,BasicFileAttributes.class,LinkOption.NOFOLLOW_LINKS);
                if(after.size()!=a.size()||!after.lastModifiedTime().equals(a.lastModifiedTime())||!Objects.equals(after.fileKey(),a.fileKey()))throw new IOException("Cache changed during rollback custody");
                return FileVisitResult.CONTINUE;
            }
        });
    }
}
