package worldfortwo.bridge;

import java.io.IOException;
import java.io.InputStream;
import java.io.UncheckedIOException;
import java.lang.invoke.MethodHandles;
import java.lang.invoke.MethodHandle;
import java.lang.invoke.MethodType;
import java.nio.ByteBuffer;
import java.nio.charset.StandardCharsets;
import java.nio.file.Path;
import java.nio.file.Files;
import java.nio.file.LinkOption;
import java.nio.file.NoSuchFileException;
import java.nio.file.FileVisitResult;
import java.nio.file.SimpleFileVisitor;
import java.nio.file.attribute.BasicFileAttributes;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.ArrayList;
import java.util.HexFormat;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;
import java.util.TreeSet;
import java.util.zip.ZipFile;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.FileUtil;
import net.minecraft.server.packs.PackResources;
import net.minecraft.server.packs.PackType;
import net.minecraft.server.packs.PathPackResources;
import net.minecraft.server.packs.FilePackResources;
import net.minecraft.server.packs.CompositePackResources;
import net.minecraft.server.packs.VanillaPackResources;
import net.minecraft.server.packs.resources.IoSupplier;
import net.minecraft.server.packs.resources.ResourceManager;
import net.neoforged.neoforge.resource.EmptyPackResources;

/** Original bounded byte attestation. No JSON normalization, registry edit or pack close. */
public final class LithostitchedSeedgenResources {
    private static final int MAX_PACKS=512,MAX_ENTRIES=262144,MAX_TEXT=4096,MAX_VISITS=1048576,MAX_HASH_VISITS=MAX_VISITS;
    private static final long MAX_HASH_WORK_BYTES=2L*1024*1024*1024,MAX_RESOURCE=32L*1024*1024;
    public record Attestation(List<String> orderedPacks,String sha256,int entries,long bytes) { // entries and bytes retain their legacy ABI names for hash visits and cumulative streamed payload hash work; neither is logical retained size.
        public Attestation {orderedPacks=List.copyOf(orderedPacks);}
    }
    private LithostitchedSeedgenResources(){}
    record Inventory(TreeSet<ResourceLocation> ids,Map<ResourceLocation,Boolean> readable){
        Inventory {ids=new TreeSet<>(ids);readable=Map.copyOf(readable);}
    }
    public static Attestation capture(List<PackResources> opened,ResourceManager resources)throws IOException {
        if(opened.isEmpty()||opened.size()>MAX_PACKS)throw new IOException("Bounded opened server-data packs required");
        Accumulator out=new Accumulator();var identities=new ArrayList<String>();var allIds=new TreeSet<ResourceLocation>();logPackHeaders(opened);
        out.text("awft-native-server-data:3");out.number(opened.size());
        for(int index=0;index<opened.size();index++) {
            PackResources pack=opened.get(index);String identity=pack.packId();out.openedIndex=index;out.packContext=identity;
            identities.add(identity);out.number(index);out.text(identity);out.text(pack.getClass().getName());
            var inventory=inventory(pack,out,0);allIds.addAll(inventory.ids());
            requireDistinctIds(allIds.size());out.distinctIds=allIds.size();
        }
        // Bind the actual effective manager, including stack order/filter results,
        // instead of assuming raw opened packs describe every selected overlay.
        var effective=resources.listPacks().toList();
        if(effective.size()>MAX_PACKS)throw new IOException("Bounded effective pack count exceeded");
        if(effective.size()!=opened.size())throw new IOException("Effective server-data packs differ from opened inventory");
        for(int n=0;n<effective.size();n++)if(effective.get(n)!=opened.get(n))throw new IOException("Effective native pack order/identity differs from opened inventory");
        out.text("effective-packs");out.number(effective.size());
        for(var pack:effective){out.text(pack.packId());out.text(pack.getClass().getName());}
        report(out,"opened-pack-inventory-complete");out.phase="effective-override-stacks";out.openedIndex=-1;out.packContext="effective-manager";out.rootIds=-1;out.text("effective-stacks");out.number(allIds.size());
        for(var id:allIds) {
            var stack=resources.getResourceStack(id);
            out.text(id.toString());out.number(stack.size());
            if(stack.size()>MAX_PACKS)throw new IOException("Bounded native override stack exceeded");
            for(var resource:stack) {
                out.packContext=resource.sourcePackId();out.text(resource.sourcePackId());
                out.resource(id.toString(),resource::open);
            }
        }
        report(out,"effective-override-stacks-complete");out.phase="generated-final-stability";for(var view:out.cachedViews)view.unchanged();for(var view:out.memoryViews)view.unchanged();for(var view:out.taczViews)view.unchanged();for(var view:out.runtimeViews)runtimeUnchanged(view,out);for(var view:out.createViews)createUnchanged(view,out);report(out,"capture-complete");
        return new Attestation(identities,HexFormat.of().formatHex(out.digest.digest()),out.entries,out.bytes);
    }
    /** The native listing is cross-checked against a strict finite root walk:
     * PathPackResources.listPath logs some I/O failures and may return partially.
     * The independent walk throws on those failures; final selected bytes still
     * come through the real PackResources.getResource. No pack is closed here. */
    @SuppressWarnings("unchecked")
    private static Inventory inventory(PackResources pack,Accumulator out,int depth,PackResources parent)throws IOException {
        if(depth>16||++out.packs>MAX_PACKS)throw new IOException("Bounded complete pack structure exceeded");out.packContext=pack.packId();out.rootIds=-1;
        var ids=new TreeSet<ResourceLocation>();var rawNames=new TreeSet<String>();
        var readable=new TreeMap<ResourceLocation,Boolean>();var childInventories=new ArrayList<Inventory>();int[] visits={0};
        PackResources.ResourceOutput collect=(id,supplier)->{
            if(++visits[0]>MAX_ENTRIES||System.nanoTime()-out.deadline>=0)
                throw new IllegalStateException("Bounded native root inventory exceeded");
            ids.add(id);
        };
        try {
            Class<?> type=pack.getClass();
            // One exact native dynamic provider is inventoried through its own API.
            var runtimeIds=YungLocatePackCustody.matches(pack)?YungLocatePackCustody.inventory(pack):null;
            var moonlight=MoonlightCachePackCustody.matches(pack)?MoonlightCachePackCustody.inspect(pack):null;
            if(moonlight!=null)out.cachedViews.add(moonlight);var memory=MoonlightInMemoryPackCustody.matches(pack)?MoonlightInMemoryPackCustody.inspect(pack,out.deadline):null;if(memory!=null)out.memoryViews.add(memory);var delegating=GeneratedServerPackCustody.tacz(pack)?GeneratedServerPackCustody.inspectTacz(pack,out.deadline):null;var generated=GeneratedServerPackCustody.runtime(pack)?GeneratedServerPackCustody.inspectRuntime(pack,out.deadline):null;if(delegating!=null)out.taczViews.add(delegating);if(generated!=null)out.runtimeViews.add(generated);var create=CreateDynamicPackCustody.matches(pack)?CreateDynamicPackCustody.inspect(pack,out.deadline):null;if(create!=null)out.createViews.add(create);
            // An unknown subclass could override any listed/read resource method.
            if(type!=PathPackResources.class&&type!=VanillaPackResources.class&&type!=CompositePackResources.class
                    &&type!=FilePackResources.class&&type!=EmptyPackResources.class&&runtimeIds==null&&moonlight==null&&memory==null&&delegating==null&&generated==null&&create==null)
                throw new IOException("Unsupported actual PackResources implementation: "+type.getName()+" pack="+pack.packId());
            // Check that a file-backed native pack is actually open, rather than
            // allowing its logged failed-open path to masquerade as an empty pack.
            ZipFile zip=null;
            if(type==FilePackResources.class) {
                Object access=Roots.ZIP_ACCESS.invoke(pack);zip=(ZipFile)Roots.ZIP_OPEN.invoke(access);
                if(zip==null||zip.size()>MAX_VISITS)throw new IOException("Native file pack is unavailable or exceeds finite entry custody");
            }
            var namespaces=new TreeSet<>(pack.getNamespaces(PackType.SERVER_DATA));
            if(namespaces.size()>4096)throw new IOException("Bounded namespace count exceeded");
            out.text("pack-structure");out.text(pack.packId());out.text(pack.getClass().getName());out.number(namespaces.size());
            for(String namespace:namespaces)out.text(namespace);
            out.resource("pack.mcmeta",pack.getRootResource("pack.mcmeta"));
            if(type==PathPackResources.class) {
                Path root=(Path)Roots.PATH.invoke(pack);
                try{if(!declaredEmptyTectonicOverlay(pack,parent,root,out))requireDirectory(root);}catch(IOException failure){throw new IOException("Exact native pack root refusal: pack="+pack.packId()+" class="+pack.getClass().getName()+" root="+root+" filesystem="+root.getFileSystem().getClass().getName()+" parent="+(parent==null?"none":parent.packId()+"/"+parent.getClass().getName())+" cause="+failure.getMessage(),failure);}
                Path data=root.resolve("data");
                if(!namespaces.equals(pathNamespaces(data,out)))throw new IOException("Native path namespace inventory is incomplete");
                for(String namespace:namespaces)ids.addAll(pathIds(namespace,data.resolve(namespace),out,rawNames));
            }else if(type==VanillaPackResources.class) {
                var paths=(Map<PackType,List<Path>>)Roots.VANILLA.invoke(pack);
                List<Path> selected=paths.getOrDefault(PackType.SERVER_DATA,List.of());
                if(selected.size()>64)throw new IOException("Bounded vanilla server-data roots exceeded");
                out.number(selected.size());
                for(String namespace:namespaces)for(int rootIndex=0;rootIndex<selected.size();rootIndex++) {
                    out.text("vanilla-native-root");out.number(rootIndex);
                    ids.addAll(pathIds(namespace,selected.get(rootIndex).resolve(namespace),out,rawNames));
                }
            }else if(type==CompositePackResources.class||delegating!=null) {
                PackResources primary=delegating==null?(PackResources)Roots.PRIMARY.invoke(pack):null;
                var children=delegating==null?(List<PackResources>)Roots.STACK.invoke(pack):delegating.children;
                // Native constructor's stack is reversed overlays followed by
                // the exact primary. Do not count/hash the primary twice.
                if(delegating==null&&(children.isEmpty()||children.size()>MAX_PACKS||children.getLast()!=primary))
                    throw new IOException("Pinned composite primary/overlay topology changed");
                out.number(children.size());if(delegating!=null){out.text("native-TaCZ-ordered-children:1");out.text(delegating.metadata);}
                for(var child:children){Inventory childInventory=inventory(child,out,depth+1,pack);childInventories.add(childInventory);ids.addAll(childInventory.ids());}
                // Empty namespace directories are legal, so check the full
                // native child namespace union, not only namespaces with files.
                var childNamespaces=new TreeSet<String>();
                for(var child:children)childNamespaces.addAll(child.getNamespaces(PackType.SERVER_DATA));
                if(!namespaces.equals(childNamespaces))throw new IOException("Composite namespace inventory changed during capture");
            }else if(type==FilePackResources.class) {
                String prefix=(String)Roots.ZIP_PREFIX.invoke(pack);
                var expected=fileIds(zip,prefix,out,rawNames);
                var expectedNamespaces=fileNamespaces(zip,prefix,out);
                if(!namespaces.equals(expectedNamespaces))throw new IOException("Native file namespace inventory is incomplete");
                // FilePackResources also appends '/' to its query, so the empty
                // query produces a double slash. Enumerate exact ZIP members,
                // cross-check real nonempty top-level native prefixes, and read
                // namespace-root files through native getResource directly.
                var directories=new TreeMap<String,TreeSet<String>>();var nested=new TreeSet<ResourceLocation>();
                for(var id:expected) {
                    int split=id.getPath().indexOf('/');
                    if(split>=0) {
                        String dir=id.getPath().substring(0,split);
                        if(dir.isEmpty()||dir.equals(".")||dir.equals(".."))throw new IOException("Native ZIP resource prefix requires separate custody");
                        directories.computeIfAbsent(id.getNamespace(),ignored->new TreeSet<>()).add(dir);nested.add(id);
                    }
                }
                for(var entry:directories.entrySet())for(String dir:entry.getValue())pack.listResources(PackType.SERVER_DATA,entry.getKey(),dir,collect);
                if(!ids.equals(nested))throw new IOException("Native file resource inventory is incomplete");
                ids.addAll(expected);
            }else if(create!=null){createInventory(create,out,ids);}else if(generated!=null){runtimeInventory(generated,out,ids);}else if(moonlight!=null||memory!=null) {
                if(moonlight!=null)moonlightInventory(pack,moonlight,out,ids,rawNames);else memoryInventory(pack,memory,out,ids);
            }else if(runtimeIds!=null) {
                ids.addAll(runtimeIds);
            }else if(type==EmptyPackResources.class) {
                // Exact pinned NeoForge class has no namespaces/resources/filters.
                try(InputStream input=EmptyPackResources.class.getResourceAsStream("EmptyPackResources.class")) {
                    if(input==null)throw new IOException("Pinned empty native pack class resource unavailable");
                    byte[] raw=input.readNBytes(3470);
                    if(raw.length!=3469||!HexFormat.of().formatHex(sha().digest(raw)).equals("62f39fc4733c8b708cafa61703f2dd2d131acd25216d5905a271c9b5cd09f5c6"))
                        throw new IOException("Pinned empty native pack implementation changed");
                }
                if(!namespaces.isEmpty())throw new IOException("Native empty pack unexpectedly supplies namespaces");
            }
            if(ids.size()>MAX_ENTRIES)throw new IOException("Bounded native pack inventory exceeded");out.packContext=pack.packId();out.rootIds=ids.size();
            // Every real child is hashed before its Composite winner. A fully
            // masked child-byte change must still refuse the fresh seed load.
            out.text("selected-native-resources");out.number(ids.size());
            for(var id:ids) {
                var source=selected(pack,id,rawNames,childInventories);
                boolean parserRejected=FileUtil.decomposePath(id.getPath()).error().isPresent();
                readable.put(id,source!=null);
                out.text("native-selected-readability");out.text(id.toString());out.number(parserRejected?1:0);out.number(source==null?0:1);
                String selectedHash=out.resource(id.toString(),source);if(generated!=null&&!java.util.Objects.equals(generated.selectedHashes.get(id),selectedHash))throw new IOException("Native runtime listed/selected bytes differ");if(create!=null&&!java.util.Objects.equals(create.selectedHashes.get(id),selectedHash))throw new IOException("Native Create original/selected bytes differ");
            }
            if(moonlight!=null)moonlight.unchanged();if(memory!=null)memory.unchanged();if(delegating!=null)delegating.unchanged();if(generated!=null)runtimeUnchanged(generated,out);if(create!=null)createUnchanged(create,out);
            return new Inventory(ids,Map.copyOf(readable));
        }catch(IOException failure){throw failure;}
        catch(UncheckedIOException failure){throw failure.getCause();}
        catch(VirtualMachineError|ThreadDeath failure){throw failure;}
        catch(Throwable failure){throw new IOException("Exact native pack root inventory failed",failure);}
    }
    /** A null native lookup is data, not permission to hide a missing resource.
     * Only an exact authenticated raw member rejected by the native path grammar
     * may be unavailable. A Composite must prove ALL its selected children
     * unavailable; a readable child or absent child proof refuses its null. */
    static boolean attestedNativeAbsence(Class<?> type,ResourceLocation id,Set<String> rawNames,List<Inventory> children) {
        if(FileUtil.decomposePath(id.getPath()).error().isEmpty())return false;
        if(type==CompositePackResources.class||type.getName().equals(GeneratedServerPackCustody.TACZ)) {
            boolean member=false;
            for(var child:children)if(child.ids().contains(id)) {
                Boolean state=child.readable().get(id);
                if(state==null||state)return false;
                member=true;
            }
            return member;
        }
        return (type==PathPackResources.class||type==VanillaPackResources.class||type==FilePackResources.class)
            &&rawNames.contains(id.getNamespace()+"/"+id.getPath());
    }
    static IoSupplier<InputStream> selected(PackResources pack,ResourceLocation id,Set<String> rawNames,List<Inventory> children)throws IOException {
        var source=pack.getResource(PackType.SERVER_DATA,id);
        if(source==null&&!attestedNativeAbsence(pack.getClass(),id,rawNames,children))
            throw new IOException("Enumerated native pack resource is unavailable: pack="+pack.packId()+" class="+pack.getClass().getName()+" id="+id);
        return source;
    }
    /** Strict folder bytes plus the exact original cached provider's public API.
     * Manually declared empty namespaces are legal; undisclosed raw namespaces,
     * a partial/stale native trie or a missing selected resource are not. */
    private static void moonlightInventory(PackResources pack,MoonlightCachePackCustody.View view,
            Accumulator out,TreeSet<ResourceLocation> ids,TreeSet<String> rawNames)throws IOException {
        out.text("moonlight-cached-folder:1");out.text(view.delegate.getClass().getName());
        out.text(PackType.SERVER_DATA.name());
        out.number(view.rootBytes.size());
        for(String name:new TreeSet<>(view.rootBytes.keySet())){
            var source=pack.getRootResource(name.split("/",-1));
            if(source==null)throw new IOException("Original Moonlight root resource disappeared");
            out.resource("moonlight-root/"+name,source);
        }
        Path data=view.root.resolve("data");
        var actualNamespaces=pathNamespaces(data,out);
        if(!view.namespaces.containsAll(actualNamespaces))throw new IOException("Moonlight raw data has undisclosed namespaces");
        for(String namespace:new TreeSet<>(view.namespaces))
            ids.addAll(pathIds(namespace,data.resolve(namespace),out,rawNames));
        var found=new TreeSet<ResourceLocation>();int[] visits={0};
        PackResources.ResourceOutput collect=(id,supplier)->{
            if(++visits[0]>MAX_ENTRIES||System.nanoTime()-out.deadline>=0||supplier==null||!found.add(id))
                throw new IllegalStateException("Moonlight native resource enumeration is duplicate/partial/unbounded");
        };
        if(view.delegate.getClass()==PathPackResources.class){
            var cachedNamespaces=new TreeSet<>(view.delegate.getNamespaces(PackType.SERVER_DATA));
            if(!cachedNamespaces.equals(actualNamespaces))throw new IOException("Moonlight native path namespaces changed");
            // Normal PathPackResources uses nonempty prefixes. Root-level files
            // are still independently walked/hashed and read by getResource.
            var dirs=new TreeMap<String,TreeSet<String>>();var nested=new TreeSet<ResourceLocation>();
            for(var id:ids){int split=id.getPath().indexOf('/');if(split>=0){
                String prefix=id.getPath().substring(0,split);
                if(prefix.isEmpty()||prefix.equals(".")||prefix.equals(".."))throw new IOException("Moonlight native path prefix requires separate custody");
                dirs.computeIfAbsent(id.getNamespace(),ignored->new TreeSet<>()).add(prefix);nested.add(id);
            }}
            for(var entry:dirs.entrySet())for(String prefix:entry.getValue())
                pack.listResources(PackType.SERVER_DATA,entry.getKey(),prefix,collect);
            if(!found.equals(nested))throw new IOException("Moonlight original path resource inventory is incomplete");
        }else{
            // The pinned wrapper owns its namespace set. Its FastSearch
            // delegate reports an empty namespace set even for populated
            // indices; that method is not the wrapper's namespace authority.
            // Exact original list/get coverage below must still equal EVERY
            // independently walked native ID, so a stale trie still refuses.
            for(String namespace:new TreeSet<>(view.namespaces))
                pack.listResources(PackType.SERVER_DATA,namespace,"",collect);
            if(!found.equals(ids))throw new IOException("Moonlight original cached trie is stale or incomplete");
        }
        view.unchanged();
    }
    private static BasicFileAttributes attributes(Path path)throws IOException {
        try{return Files.readAttributes(path,BasicFileAttributes.class,LinkOption.NOFOLLOW_LINKS);}
        catch(NoSuchFileException absent){return null;}
    }
    private static void requireDirectory(Path path)throws IOException {
        var value=attributes(path);
        if(value==null||!value.isDirectory()||value.isSymbolicLink())throw new IOException("Exact native pack root must be an available directory");
    }
    private static TreeSet<String> pathNamespaces(Path data,Accumulator out)throws IOException {
        var names=new TreeSet<String>();var value=attributes(data);
        if(value==null)return names;
        if(!value.isDirectory()||value.isSymbolicLink())throw new IOException("Native data root is not a regular directory");
        try(var entries=Files.newDirectoryStream(data)) {
            for(Path child:entries) {
                out.visit();String name=child.getFileName().toString();
                if(ResourceLocation.isValidNamespace(name))names.add(name);
                if(names.size()>4096)throw new IOException("Bounded native path namespace count exceeded");
            }
        }
        return names;
    }
    private static TreeSet<ResourceLocation> pathIds(String namespace,Path root,Accumulator out,TreeSet<String> rawNames)throws IOException {
        var expected=new TreeSet<ResourceLocation>();var rawFiles=new TreeMap<String,Path>();var value=attributes(root);
        if(value==null)return expected; // Vanilla legitimately has sparse roots.
        if(!value.isDirectory()||value.isSymbolicLink())throw new IOException("Native namespace root is not a regular directory");
        Files.walkFileTree(root,java.util.Set.of(),128,new SimpleFileVisitor<Path>() {
            @Override public FileVisitResult preVisitDirectory(Path dir,BasicFileAttributes attrs)throws IOException {
                out.visit();return FileVisitResult.CONTINUE;
            }
            @Override public FileVisitResult visitFile(Path file,BasicFileAttributes attrs)throws IOException {
                out.visit();
                if(attrs.isSymbolicLink())throw new IOException("Symbolic native server-data resource requires separate custody");
                if(attrs.isDirectory())throw new IOException("Native server-data tree exceeds finite depth");
                if(attrs.isRegularFile()) {
                    String name=String.join("/",java.util.stream.StreamSupport.stream(root.relativize(file).spliterator(),false).map(Path::toString).toList());
                    if(rawFiles.put(name,file)!=null||rawFiles.size()>MAX_ENTRIES)
                        throw new IOException("Bounded exact native raw-file inventory exceeded");
                    var id=ResourceLocation.tryBuild(namespace,name);
                    if(id!=null)expected.add(id);
                    if(expected.size()>MAX_ENTRIES)throw new IOException("Bounded native path resource count exceeded");
                }
                return FileVisitResult.CONTINUE;
            }
            @Override public FileVisitResult visitFileFailed(Path file,IOException failure)throws IOException {throw failure;}
            @Override public FileVisitResult postVisitDirectory(Path dir,IOException failure)throws IOException {
                if(failure!=null)throw failure;return FileVisitResult.CONTINUE;
            }
        });
        var nativeIds=new TreeSet<ResourceLocation>();
        PathPackResources.listPath(namespace,root,List.of(),(id,supplier)->{
            if(nativeIds.size()>=MAX_ENTRIES||System.nanoTime()-out.deadline>=0)
                throw new IllegalStateException("Native root listing exceeded finite custody");
            nativeIds.add(id);
        });
        if(!expected.equals(nativeIds))throw new IOException("Native path resource enumeration was partial or changed during capture");
        // Directory iteration order is not a native overlay order. Sort exact
        // relative spellings within EACH ordered root; never change the names.
        out.text("ordered-raw-path-members");out.number(rawFiles.size());
        for(var entry:rawFiles.entrySet()) {
            String name=entry.getKey();rawNames.add(namespace+"/"+name);
            raw(out,namespace+"/"+name,name,()->Files.newInputStream(entry.getValue()));
        }
        return expected;
    }
    private static String filePrefix(String prefix)throws IOException {
        if(prefix==null||prefix.length()>MAX_TEXT||prefix.startsWith("/")||prefix.contains("\\")
                ||java.util.Arrays.stream(prefix.split("/",-1)).anyMatch(part->part.equals("..")||part.equals(".")))
            throw new IOException("Native file pack prefix exceeds exact custody");
        return prefix.isEmpty()?"data/":prefix+"/data/";
    }
    private static TreeSet<ResourceLocation> fileIds(ZipFile zip,String prefix,Accumulator out,TreeSet<String> rawNames)throws IOException {
        String start=filePrefix(prefix);var result=new TreeSet<ResourceLocation>();var entries=zip.entries();
        while(entries.hasMoreElements()) {
            out.visit();var entry=entries.nextElement();String name=entry.getName();
            if(!entry.isDirectory()&&name.startsWith(start)) {
                String relative=name.substring(start.length());int split=relative.indexOf('/');
                if(!rawNames.add(relative))throw new IOException("Ambiguous duplicate raw ZIP member requires separate custody");
                raw(out,relative,split>=0?relative.substring(split+1):relative,()->zip.getInputStream(entry));
                if(split>=0) {
                    var id=ResourceLocation.tryBuild(relative.substring(0,split),relative.substring(split+1));
                    if(id!=null)result.add(id);
                    if(result.size()>MAX_ENTRIES)throw new IOException("Bounded native file resource count exceeded");
                }
            }
        }
        return result;
    }
    /** Exact bytes from an already admitted root/ZIP member, including metadata
     * whose original spelling the native resource path grammar cannot serve.
     * No lowercasing, filtering, fallback lookup or JSON normalization occurs. */
    private static void raw(Accumulator out,String exactName,String resourcePath,IoSupplier<InputStream> source)throws IOException {
        out.text("raw-server-data-file");out.text(exactName);
        var grammar=FileUtil.decomposePath(resourcePath);
        out.number(grammar.error().isPresent()?1:0);
        if(grammar.error().isPresent())out.text(grammar.error().get().message());
        out.resource("raw/"+exactName,source);
    }
    private static TreeSet<String> fileNamespaces(ZipFile zip,String prefix,Accumulator out)throws IOException {
        String start=filePrefix(prefix);var result=new TreeSet<String>();var entries=zip.entries();
        while(entries.hasMoreElements()) {
            out.visit();String name=entries.nextElement().getName();
            String namespace=FilePackResources.extractNamespace(start,name);
            if(!namespace.isEmpty()&&ResourceLocation.isValidNamespace(namespace))result.add(namespace);
            if(result.size()>4096)throw new IOException("Bounded native file namespace count exceeded");
        }
        return result;
    }
    private static final class Roots {
        static final MethodHandle PATH=get(PathPackResources.class,"root",Path.class);
        static final MethodHandle VANILLA=get(VanillaPackResources.class,"pathsForType",Map.class);
        static final MethodHandle PRIMARY=get(CompositePackResources.class,"primaryPackResources",PackResources.class);
        static final MethodHandle STACK=get(CompositePackResources.class,"packResourcesStack",List.class);
        static final Class<?> ZIP_TYPE=zipType();
        static final MethodHandle ZIP_ACCESS=get(FilePackResources.class,"zipFileAccess",ZIP_TYPE);
        static final MethodHandle ZIP_PREFIX=get(FilePackResources.class,"prefix",String.class);
        static final MethodHandle ZIP_OPEN=zipOpen();
        private static Class<?> zipType() {
            try{return Class.forName("net.minecraft.server.packs.FilePackResources$SharedZipFileAccess",false,FilePackResources.class.getClassLoader());}
            catch(ClassNotFoundException failure){throw new ExceptionInInitializerError(failure);}
        }
        private static MethodHandle zipOpen() {
            try{return MethodHandles.privateLookupIn(ZIP_TYPE,MethodHandles.lookup()).findVirtual(ZIP_TYPE,"getOrCreateZipFile",MethodType.methodType(ZipFile.class));}
            catch(ReflectiveOperationException failure){throw new ExceptionInInitializerError(failure);}
        }
        private static MethodHandle get(Class<?> owner,String name,Class<?> type) {
            try{return MethodHandles.privateLookupIn(owner,MethodHandles.lookup()).findGetter(owner,name,type);}
            catch(ReflectiveOperationException failure){throw new ExceptionInInitializerError(failure);}
        }
    }
    private static final class Accumulator {
        final ArrayList<MoonlightCachePackCustody.View> cachedViews=new ArrayList<>();final ArrayList<MoonlightInMemoryPackCustody.View> memoryViews=new ArrayList<>();final ArrayList<GeneratedServerPackCustody.TaczView> taczViews=new ArrayList<>();final ArrayList<GeneratedServerPackCustody.RuntimeView> runtimeViews=new ArrayList<>();final ArrayList<CreateDynamicPackCustody.View> createViews=new ArrayList<>();
        final MessageDigest digest=sha();final long deadline=System.nanoTime()+java.util.concurrent.TimeUnit.SECONDS.toNanos(60);long bytes;int entries,packs,visits;String phase="opened-pack-inventory",packContext="none";int distinctIds,rootIds=-1,openedIndex=-1;
        void visit()throws IOException {
            if(++visits>MAX_VISITS||System.nanoTime()-deadline>=0)throw counterFailure(this,"Native server-data inventory exceeded its finite traversal bound","<traversal>");
        }
        void number(long value){digest.update(ByteBuffer.allocate(Long.BYTES).putLong(value).array());}
        void text(String value)throws IOException {
            if(System.nanoTime()-deadline>=0)throw counterFailure(this,"Native server-data attestation exceeded its finite deadline","<text-or-read>");
            if(value==null||value.length()>MAX_TEXT)throw new IOException("Bounded native resource identity exceeded");
            byte[] raw=value.getBytes(StandardCharsets.UTF_8);number(raw.length);digest.update(raw);
        }
        String resource(String identity,IoSupplier<InputStream> source)throws IOException {
            if(++entries>MAX_HASH_VISITS)throw counterFailure(this,"Bounded complete resource hash-visit count exceeded",identity);
            text(identity);number(source==null?0:1);if(source==null)return null;
            MessageDigest content=sha();long size=0;byte[] buffer=new byte[65536];
            try(InputStream stream=source.get()) {
                if(stream==null)throw new IOException("Native resource supplier returned null");
                for(int n;(n=stream.read(buffer))!=-1;) {
                    size+=n;bytes+=n;
                    if(System.nanoTime()-deadline>=0)throw counterFailure(this,"Native server-data attestation exceeded its finite deadline","<text-or-read>");
                    if(size>MAX_RESOURCE||bytes>MAX_HASH_WORK_BYTES)throw counterFailure(this,(size>MAX_RESOURCE?"Bounded server-data per-resource size exceeded":"Bounded cumulative server-data hash-read work exceeded")+"; resourceBytes="+size+" resourceLimit="+MAX_RESOURCE,identity);
                    content.update(buffer,0,n);
                }
            }
            byte[] value=content.digest();number(size);digest.update(value);return HexFormat.of().formatHex(value);
        }
    }
    /** Exact native memory storage was independently cross-checked with list/get.
     * Feed every original root and selected data byte into the SAME accumulator;
     * effective manager stacks and both end-of-capture checks remain unchanged. */
    private static void memoryInventory(PackResources pack,MoonlightInMemoryPackCustody.View view,
            Accumulator out,TreeSet<ResourceLocation> ids)throws IOException {
        out.text("moonlight-memory-map:1");out.text(PackType.SERVER_DATA.name());
        out.number(view.hidden()?1:0);
        out.text("native-PackMetadataSection");out.text("message.moonlight.runtime");
        out.number(view.packFormat());out.number(0); // exact native supportedFormats.empty
        out.number(view.rootNames().size());
        for(String name:new TreeSet<>(view.rootNames())) {
            var source=pack.getRootResource(name.split("/",-1));
            if(source==null)throw new IOException("Native Moonlight memory root disappeared");
            out.resource("moonlight-memory-root/"+name,source);
        }
        ids.addAll(view.ids());view.unchanged();
    }
    private static MessageDigest sha(){try{return MessageDigest.getInstance("SHA-256");}catch(NoSuchAlgorithmException impossible){throw new AssertionError(impossible);}}
    /** Log every actual opened identity before the first provider-specific traversal. */
    private static void logPackHeaders(List<PackResources> packs)throws IOException {
        int total=0;
        for(var pack:packs) {
            if(pack==null||pack.packId()==null||pack.packId().length()>MAX_TEXT||pack.getClass().getName().length()>MAX_TEXT)
                throw new IOException("Bounded opened native pack headers required");
            total+=pack.packId().length()+pack.getClass().getName().length();
            if(total>131072)throw new IOException("Bounded complete native pack header text exceeded");
        }
        var log=org.slf4j.LoggerFactory.getLogger("AWFT-SeedGen-Pack-Custody");
        for(int n=0;n<packs.size();n++)log.info("Opened SERVER_DATA pack [{}] id={} class={}",n,packs.get(n).packId(),packs.get(n).getClass().getName());
    }
    /** Hash complete native map bytes, then cross-check the original native list/get API. */
    private static void runtimeInventory(GeneratedServerPackCustody.RuntimeView view,Accumulator out,TreeSet<ResourceLocation> ids)throws IOException {
        out.text("native-CDP-runtime-map:1");out.text(view.metadata);out.number(view.raw().size());
        for(var entry:new TreeMap<>(view.raw()).entrySet())
            view.rawHashes.put(entry.getKey(),out.resource("native-runtime-raw/"+entry.getKey(),entry.getValue()));
        ids.addAll(view.ids());
        for(var id:ids)view.selectedHashes.put(id,out.resource("native-runtime-listed/"+id,view.listed(id)));
        view.unchanged();
    }
    private static void runtimeUnchanged(GeneratedServerPackCustody.RuntimeView view,Accumulator out)throws IOException {
        view.unchanged();
        for(var entry:view.rawHashes.entrySet()) {
            String actual=out.resource("native-runtime-stable/"+entry.getKey(),view.raw().get(entry.getKey()));
            if(!java.util.Objects.equals(entry.getValue(),actual))throw new IOException("Native runtime bytes changed during custody");
        }
        view.unchanged();
    }
    /** Complete Create map bytes, including namespace-root files the native empty query misses. */
    private static void createInventory(CreateDynamicPackCustody.View view,Accumulator out,TreeSet<ResourceLocation> ids)throws IOException {
        out.text("native-Create-dynamic-map:1");out.text(view.metadata);out.number(view.raw().size());
        for(var entry:new TreeMap<>(view.raw()).entrySet())
            view.rawHashes.put(entry.getKey(),out.resource("native-Create-raw/"+entry.getKey(),entry.getValue()));
        ids.addAll(view.ids());
        for(var id:ids)view.selectedHashes.put(id,out.resource("native-Create-original/"+id,view.listedOrDirect(id)));
        view.unchanged();
    }
    private static void createUnchanged(CreateDynamicPackCustody.View view,Accumulator out)throws IOException {
        view.unchanged();
        for(var entry:view.rawHashes.entrySet()) {
            String actual=out.resource("native-Create-stable/"+entry.getKey(),view.raw().get(entry.getKey()));
            if(!java.util.Objects.equals(entry.getValue(),actual))throw new IOException("Native Create bytes changed during custody");
        }
        view.unchanged();
    }

    // The sole admitted absent root is a declaration in this exact pinned native archive.
    private static final String TECTONIC_EMPTY_ARCHIVE_SHA="cf188c70e7dd94f6e3a81cef9fe99f1151f13217809f7576aaedb0c3e6547ae1";
    private static final String TECTONIC_EMPTY_META_SHA="201909f97c52ab64836b97f535d91bb4e38fc9e4681b6304188e36f9fdfccd1d";
    private static final String TECTONIC_META="resourcepacks/tectonic/pack.mcmeta";
    private static Inventory inventory(PackResources pack,Accumulator out,int depth)throws IOException {
        return inventory(pack,out,depth,null);
    }
    private static boolean declaredEmptyTectonicOverlay(PackResources pack,PackResources parent,Path root,Accumulator out)throws Throwable {
        if(parent==null||parent.getClass()!=CompositePackResources.class||!parent.packId().equals("tectonic")
                ||pack.getClass()!=PathPackResources.class||!pack.packId().equals("tectonic"))return false;
        var primary=(PackResources)Roots.PRIMARY.invoke(parent);
        if(primary.getClass()!=PathPackResources.class)return false;
        Path base=(Path)Roots.PATH.invoke(primary);
        if(!root.equals(base.resolve("intentionally_empty"))||attributes(root)!=null)return false;
        if(!net.neoforged.fml.ModList.get().isLoaded("tectonic"))return false;
        var file=net.neoforged.fml.ModList.get().getModFileById("tectonic").getFile();
        attestDeclaredEmptyTectonicOverlay(pack,parent,file.getFilePath(),file.findResource("resourcepacks/tectonic"));
        out.text("pinned-native-Tectonic-declared-empty-overlay:1");out.text(TECTONIC_EMPTY_ARCHIVE_SHA);
        out.text(TECTONIC_EMPTY_META_SHA);out.text("resourcepacks/tectonic/intentionally_empty");out.number(0);
        org.slf4j.LoggerFactory.getLogger("AWFT-SeedGen-Resources").info(
            "Attested exact native declared-empty overlay: parent={} class={} root={} archive={} members=0; all other missing roots still refuse",
            parent.packId(),pack.getClass().getName(),root,TECTONIC_EMPTY_ARCHIVE_SHA);
        return true;
    }
    /** Package-private actual-API fixture overload; runtime paths come only from the pinned ModList file. */
    @SuppressWarnings("unchecked")
    static void attestDeclaredEmptyTectonicOverlay(PackResources child,PackResources parent,Path archive,Path expectedBase)throws Throwable {
        if(parent==null||parent.getClass()!=CompositePackResources.class||child.getClass()!=PathPackResources.class
                ||!parent.packId().equals("tectonic")||!child.packId().equals("tectonic"))
            throw new IOException("Exact native Tectonic parent/child identities required");
        var primary=(PackResources)Roots.PRIMARY.invoke(parent);var stack=(List<PackResources>)Roots.STACK.invoke(parent);
        if(primary.getClass()!=PathPackResources.class||!primary.packId().equals("tectonic")||stack.size()<2
                ||stack.size()>MAX_PACKS||stack.getLast()!=primary)throw new IOException("Exact native Tectonic primary/overlay topology required");
        Path primaryRoot=(Path)Roots.PATH.invoke(primary),root=(Path)Roots.PATH.invoke(child);
        if(!primaryRoot.equals(expectedBase)||!root.equals(expectedBase.resolve("intentionally_empty"))||attributes(root)!=null)
            throw new IOException("Only exact absent native Tectonic intentionally_empty root is admitted");
        requireDirectory(primaryRoot);int exact=0;var identities=new java.util.IdentityHashMap<PackResources,Boolean>();
        for(var member:stack){
            if(member.getClass()!=PathPackResources.class||!member.packId().equals("tectonic")||identities.put(member,true)!=null)
                throw new IOException("Native Tectonic child topology changed");
            Path memberRoot=(Path)Roots.PATH.invoke(member);
            if(!memberRoot.startsWith(expectedBase)||!memberRoot.normalize().equals(memberRoot))throw new IOException("Native Tectonic child escapes its exact root");
            if(memberRoot.equals(root)){exact++;if(member!=child)throw new IOException("Native Tectonic empty child identity changed");}
        }
        if(exact!=1)throw new IOException("Native Tectonic empty child must occur once");
        if(net.minecraft.SharedConstants.getCurrentVersion().getPackVersion(PackType.SERVER_DATA)!=48)
            throw new IOException("Exact Minecraft1.21.1 server-data format48 required");
        var before=attributes(archive);
        if(before==null||!before.isRegularFile()||before.isSymbolicLink()||before.size()!=451757L)
            throw new IOException("Pinned Tectonic3.0.28 archive required");
        byte[] bytes;try(InputStream in=Files.newInputStream(archive)){bytes=in.readNBytes(451758);}
        if(bytes.length!=451757||!hashBytes(bytes).equals(TECTONIC_EMPTY_ARCHIVE_SHA))throw new IOException("Pinned Tectonic archive digest differs");
        byte[] metadata;
        try(ZipFile zip=new ZipFile(archive.toFile())){
            if(zip.size()>MAX_VISITS)throw new IOException("Tectonic archive inventory exceeds finite custody");
            var entries=zip.entries();while(entries.hasMoreElements()){
                String name=entries.nextElement().getName();
                if(name.equals("resourcepacks/tectonic/intentionally_empty")||name.startsWith("resourcepacks/tectonic/intentionally_empty/"))
                    throw new IOException("Declared-empty Tectonic overlay contains an archive member");
            }
            var entry=zip.getEntry(TECTONIC_META);
            if(entry==null||entry.getSize()!=3878)throw new IOException("Exact Tectonic built-in metadata required");
            try(InputStream in=zip.getInputStream(entry)){metadata=in.readNBytes(3879);}
        }
        if(metadata.length!=3878||!hashBytes(metadata).equals(TECTONIC_EMPTY_META_SHA))throw new IOException("Pinned Tectonic overlay metadata differs");
        var json=com.google.gson.JsonParser.parseString(new String(metadata,StandardCharsets.UTF_8)).getAsJsonObject();int declarations=0;
        for(var value:json.getAsJsonObject("overlays").getAsJsonArray("entries")){
            var row=value.getAsJsonObject();if(!row.get("directory").getAsString().equals("intentionally_empty"))continue;declarations++;
            var formats=row.getAsJsonArray("formats");
            if(formats.size()!=2||formats.get(0).getAsInt()!=1||formats.get(1).getAsInt()!=999||row.get("min_format").getAsInt()!=1
                    ||row.get("max_format").getAsInt()!=999||row.has("conditions")||row.has("neoforge:conditions"))
                throw new IOException("Exact unconditional format48 empty-overlay declaration required");
        }
        if(declarations!=1)throw new IOException("Unique native Tectonic empty-overlay declaration required");
        var source=primary.getRootResource("pack.mcmeta");
        if(source==null)throw new IOException("Native Tectonic primary metadata disappeared");
        try(InputStream in=source.get()){if(!java.util.Arrays.equals(metadata,in.readNBytes(3879)))throw new IOException("Native Tectonic primary metadata differs from archive");}
        if(!child.getNamespaces(PackType.SERVER_DATA).isEmpty()||child.getRootResource("pack.mcmeta")!=null||child.getRootResource("icon.png")!=null)
            throw new IOException("Native declared-empty child supplies unexpected namespaces/root bytes");
        var namespaces=new TreeSet<>(parent.getNamespaces(PackType.SERVER_DATA));
        if(namespaces.size()>4096)throw new IOException("Bounded native Tectonic parent namespaces required");
        for(String namespace:namespaces){
            child.listResources(PackType.SERVER_DATA,namespace,"",(id,supplier)->{throw new IllegalStateException("Native declared-empty child listed a resource");});
            if(child.getResource(PackType.SERVER_DATA,ResourceLocation.fromNamespaceAndPath(namespace,"awft_declared_empty_readback"))!=null)
                throw new IOException("Native declared-empty child supplied selected bytes");
        }
        var after=attributes(archive);
        if(after==null||after.size()!=before.size()||!after.lastModifiedTime().equals(before.lastModifiedTime())
                ||!java.util.Objects.equals(after.fileKey(),before.fileKey())||attributes(root)!=null)
            throw new IOException("Pinned Tectonic archive/absent-root witness changed during capture");
    }
    private static String hashBytes(byte[] bytes){return HexFormat.of().formatHex(sha().digest(bytes));}
    /** Distinct inventory cardinality has its original bound, independent of repeated byte hashing. */
    private static void requireDistinctIds(int count)throws IOException {
        if(count>MAX_ENTRIES)throw new IOException("Bounded whole server-data resource inventory exceeded; distinctIds="+count+" distinctLimit="+MAX_ENTRIES);
    }
    private static String counterFacts(Accumulator out) {
        return "phase="+out.phase+" hashVisits="+out.entries+" hashVisitLimit="+MAX_HASH_VISITS
            +" distinctIdsAtCompletedPackBoundary="+out.distinctIds+" distinctLimit="+MAX_ENTRIES
            +" currentRootIds="+out.rootIds+" traversalVisits="+out.visits+" traversalLimit="+MAX_VISITS
            +" hashReadWorkBytes="+out.bytes+" hashReadWorkLimit="+MAX_HASH_WORK_BYTES+" inventoryCalls="+out.packs+" inventoryLimit="+MAX_PACKS+" openedIndex="+out.openedIndex+" pack="+boundedDiagnostic(out.packContext);
    }
    private static String boundedDiagnostic(String value) {
        if(value==null)return "null";return value.length()>256?value.substring(0,256)+"...":value;
    }
    private static IOException counterFailure(Accumulator out,String reason,String identity) {
        return new IOException(reason+"; "+counterFacts(out)+" resource="+boundedDiagnostic(identity));
    }
    private static void report(Accumulator out,String event) {
        org.slf4j.LoggerFactory.getLogger("AWFT-SeedGen-Pack-Custody").info("SERVER_DATA custody {} {}",event,counterFacts(out));
    }
}
