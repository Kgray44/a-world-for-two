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
import java.util.TreeMap;
import java.util.TreeSet;
import java.util.zip.ZipFile;
import net.minecraft.resources.ResourceLocation;
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
    private static final int MAX_PACKS=512,MAX_ENTRIES=262144,MAX_TEXT=4096,MAX_VISITS=1048576;
    private static final long MAX_BYTES=512L*1024*1024,MAX_RESOURCE=32L*1024*1024;
    public record Attestation(List<String> orderedPacks,String sha256,int entries,long bytes) {
        public Attestation {orderedPacks=List.copyOf(orderedPacks);}
    }
    private LithostitchedSeedgenResources(){}
    public static Attestation capture(List<PackResources> opened,ResourceManager resources)throws IOException {
        if(opened.isEmpty()||opened.size()>MAX_PACKS)throw new IOException("Bounded opened server-data packs required");
        Accumulator out=new Accumulator();var identities=new ArrayList<String>();var allIds=new TreeSet<ResourceLocation>();
        out.text("awft-native-server-data:2");out.number(opened.size());
        for(int index=0;index<opened.size();index++) {
            PackResources pack=opened.get(index);String identity=pack.packId();
            identities.add(identity);out.number(index);out.text(identity);out.text(pack.getClass().getName());
            var ids=inventory(pack,out,0);allIds.addAll(ids);
            if(allIds.size()>MAX_ENTRIES)throw new IOException("Bounded whole server-data resource inventory exceeded");
        }
        // Bind the actual effective manager, including stack order/filter results,
        // instead of assuming raw opened packs describe every selected overlay.
        var effective=resources.listPacks().toList();
        if(effective.size()>MAX_PACKS)throw new IOException("Bounded effective pack count exceeded");
        if(effective.size()!=opened.size())throw new IOException("Effective server-data packs differ from opened inventory");
        for(int n=0;n<effective.size();n++)if(effective.get(n)!=opened.get(n))throw new IOException("Effective native pack order/identity differs from opened inventory");
        out.text("effective-packs");out.number(effective.size());
        for(var pack:effective){out.text(pack.packId());out.text(pack.getClass().getName());}
        out.text("effective-stacks");out.number(allIds.size());
        for(var id:allIds) {
            var stack=resources.getResourceStack(id);
            out.text(id.toString());out.number(stack.size());
            if(stack.size()>MAX_PACKS)throw new IOException("Bounded native override stack exceeded");
            for(var resource:stack) {
                out.text(resource.sourcePackId());
                out.resource(id.toString(),resource::open);
            }
        }
        return new Attestation(identities,HexFormat.of().formatHex(out.digest.digest()),out.entries,out.bytes);
    }
    /** The native listing is cross-checked against a strict finite root walk:
     * PathPackResources.listPath logs some I/O failures and may return partially.
     * The independent walk throws on those failures; final selected bytes still
     * come through the real PackResources.getResource. No pack is closed here. */
    @SuppressWarnings("unchecked")
    private static TreeSet<ResourceLocation> inventory(PackResources pack,Accumulator out,int depth)throws IOException {
        if(depth>16||++out.packs>MAX_PACKS)throw new IOException("Bounded complete pack structure exceeded");
        var ids=new TreeSet<ResourceLocation>();int[] visits={0};
        PackResources.ResourceOutput collect=(id,supplier)->{
            if(++visits[0]>MAX_ENTRIES||System.nanoTime()-out.deadline>=0)
                throw new IllegalStateException("Bounded native root inventory exceeded");
            ids.add(id);
        };
        try {
            Class<?> type=pack.getClass();
            // An unknown subclass could override any listed/read resource method.
            if(type!=PathPackResources.class&&type!=VanillaPackResources.class&&type!=CompositePackResources.class
                    &&type!=FilePackResources.class&&type!=EmptyPackResources.class)
                throw new IOException("Unsupported actual PackResources implementation: "+type.getName());
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
                requireDirectory(root);
                Path data=root.resolve("data");
                if(!namespaces.equals(pathNamespaces(data,out)))throw new IOException("Native path namespace inventory is incomplete");
                for(String namespace:namespaces)ids.addAll(pathIds(namespace,data.resolve(namespace),out));
            }else if(type==VanillaPackResources.class) {
                var paths=(Map<PackType,List<Path>>)Roots.VANILLA.invoke(pack);
                List<Path> selected=paths.getOrDefault(PackType.SERVER_DATA,List.of());
                if(selected.size()>64)throw new IOException("Bounded vanilla server-data roots exceeded");
                out.number(selected.size());
                for(String namespace:namespaces)for(Path root:selected)ids.addAll(pathIds(namespace,root.resolve(namespace),out));
            }else if(type==CompositePackResources.class) {
                PackResources primary=(PackResources)Roots.PRIMARY.invoke(pack);
                var children=(List<PackResources>)Roots.STACK.invoke(pack);
                // Native constructor's stack is reversed overlays followed by
                // the exact primary. Do not count/hash the primary twice.
                if(children.isEmpty()||children.size()>MAX_PACKS||children.getLast()!=primary)
                    throw new IOException("Pinned composite primary/overlay topology changed");
                out.number(children.size());
                for(var child:children)ids.addAll(inventory(child,out,depth+1));
                // Empty namespace directories are legal, so check the full
                // native child namespace union, not only namespaces with files.
                var childNamespaces=new TreeSet<String>();
                for(var child:children)childNamespaces.addAll(child.getNamespaces(PackType.SERVER_DATA));
                if(!namespaces.equals(childNamespaces))throw new IOException("Composite namespace inventory changed during capture");
            }else if(type==FilePackResources.class) {
                String prefix=(String)Roots.ZIP_PREFIX.invoke(pack);
                var expected=fileIds(zip,prefix,out);
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
            if(ids.size()>MAX_ENTRIES)throw new IOException("Bounded native pack inventory exceeded");
            // Every real child is hashed before its Composite winner. A fully
            // masked child-byte change must still refuse the fresh seed load.
            out.text("selected-native-resources");out.number(ids.size());
            for(var id:ids) {
                var source=pack.getResource(PackType.SERVER_DATA,id);
                if(source==null)throw new IOException("Enumerated native pack resource is unavailable");
                out.resource(id.toString(),source);
            }
            return ids;
        }catch(IOException failure){throw failure;}
        catch(UncheckedIOException failure){throw failure.getCause();}
        catch(VirtualMachineError|ThreadDeath failure){throw failure;}
        catch(Throwable failure){throw new IOException("Exact native pack root inventory failed",failure);}
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
    private static TreeSet<ResourceLocation> pathIds(String namespace,Path root,Accumulator out)throws IOException {
        var expected=new TreeSet<ResourceLocation>();var value=attributes(root);
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
        return expected;
    }
    private static String filePrefix(String prefix)throws IOException {
        if(prefix==null||prefix.length()>MAX_TEXT||prefix.startsWith("/")||prefix.contains("\\")
                ||java.util.Arrays.stream(prefix.split("/",-1)).anyMatch(part->part.equals("..")||part.equals(".")))
            throw new IOException("Native file pack prefix exceeds exact custody");
        return prefix.isEmpty()?"data/":prefix+"/data/";
    }
    private static TreeSet<ResourceLocation> fileIds(ZipFile zip,String prefix,Accumulator out)throws IOException {
        String start=filePrefix(prefix);var result=new TreeSet<ResourceLocation>();var entries=zip.entries();
        while(entries.hasMoreElements()) {
            out.visit();var entry=entries.nextElement();String name=entry.getName();
            if(!entry.isDirectory()&&name.startsWith(start)) {
                String relative=name.substring(start.length());int split=relative.indexOf('/');
                if(split>=0) {
                    var id=ResourceLocation.tryBuild(relative.substring(0,split),relative.substring(split+1));
                    if(id!=null)result.add(id);
                    if(result.size()>MAX_ENTRIES)throw new IOException("Bounded native file resource count exceeded");
                }
            }
        }
        return result;
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
        final MessageDigest digest=sha();final long deadline=System.nanoTime()+java.util.concurrent.TimeUnit.SECONDS.toNanos(60);long bytes;int entries,packs,visits;
        void visit()throws IOException {
            if(++visits>MAX_VISITS||System.nanoTime()-deadline>=0)throw new IOException("Native server-data inventory exceeded its finite traversal bound");
        }
        void number(long value){digest.update(ByteBuffer.allocate(Long.BYTES).putLong(value).array());}
        void text(String value)throws IOException {
            if(System.nanoTime()-deadline>=0)throw new IOException("Native server-data attestation exceeded its finite deadline");
            if(value==null||value.length()>MAX_TEXT)throw new IOException("Bounded native resource identity exceeded");
            byte[] raw=value.getBytes(StandardCharsets.UTF_8);number(raw.length);digest.update(raw);
        }
        void resource(String identity,IoSupplier<InputStream> source)throws IOException {
            if(++entries>MAX_ENTRIES)throw new IOException("Bounded complete resource count exceeded");
            text(identity);number(source==null?0:1);if(source==null)return;
            MessageDigest content=sha();long size=0;byte[] buffer=new byte[65536];
            try(InputStream stream=source.get()) {
                if(stream==null)throw new IOException("Native resource supplier returned null");
                for(int n;(n=stream.read(buffer))!=-1;) {
                    size+=n;bytes+=n;
                    if(System.nanoTime()-deadline>=0)throw new IOException("Native server-data attestation exceeded its finite deadline");
                    if(size>MAX_RESOURCE||bytes>MAX_BYTES)throw new IOException("Bounded complete server-data byte attestation exceeded");
                    content.update(buffer,0,n);
                }
            }
            number(size);digest.update(content.digest());
        }
    }
    private static MessageDigest sha(){try{return MessageDigest.getInstance("SHA-256");}catch(NoSuchAlgorithmException impossible){throw new AssertionError(impossible);}}
}
