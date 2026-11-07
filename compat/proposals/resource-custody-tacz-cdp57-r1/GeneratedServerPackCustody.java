package worldfortwo.bridge;

import java.io.IOException;
import java.io.InputStream;
import java.lang.invoke.MethodHandles;
import java.nio.file.Files;
import java.nio.file.LinkOption;
import java.nio.file.Path;
import java.nio.file.attribute.BasicFileAttributes;
import java.security.MessageDigest;
import java.util.ArrayList;
import java.util.Collection;
import java.util.HexFormat;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.TreeMap;
import java.util.TreeSet;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.packs.FilePackResources;
import net.minecraft.server.packs.PackResources;
import net.minecraft.server.packs.PackType;
import net.minecraft.server.packs.PathPackResources;
import net.minecraft.server.packs.metadata.pack.PackMetadataSection;
import net.minecraft.server.packs.resources.IoSupplier;
import net.neoforged.fml.ModList;
import net.neoforged.neoforgespi.locating.IModFile;

/** Two exact native provider views. No resource bytes are invented and no pack is closed. */
final class GeneratedServerPackCustody {
    static final String TACZ = "com.tacz.guns.resource.GunPackLoader$1";
    static final String DELEGATING = "com.tacz.guns.resource.DelegatingPackResources";
    static final String RUNTIME = "plus.dragons.createdragonsplus.data.runtime.RuntimePackResources";
    private static final int MAX = 262144;
    private GeneratedServerPackCustody() {}

    static boolean tacz(PackResources pack) { return pack.getClass().getName().equals(TACZ); }
    static boolean runtime(PackResources pack) { return pack.getClass().getName().equals(RUNTIME); }
    static TaczView inspectTacz(PackResources pack,long deadline)throws IOException {
        return inspectTacz(pack,ModList.get().getModFileById("tacz").getFile().getFilePath(),deadline);
    }
    static RuntimeView inspectRuntime(PackResources pack,long deadline)throws IOException {
        return inspectRuntime(pack,ModList.get().getModFileById("create_dragons_plus").getFile().getFilePath(),deadline);
    }

    /** The package-private archive overloads are offline fixture inputs, never runtime overrides. */
    static TaczView inspectTacz(PackResources pack,Path jar,long deadline)throws IOException {
        if(!tacz(pack)||!pack.packId().equals("tacz_resources")||!pack.getClass().getSuperclass().getName().equals(DELEGATING))
            throw new IOException("Unexpected native TaCZ provider identity");
        var witness=pin(jar,57247579L,"fa3a09f15265a4065a566960a8deab315f6c601a5f9a542840b362d455dd5470",deadline);
        pinClass(pack.getClass(),1953,"7f89daa15ca67c03b087eee47bab9197541f7feb9bf2b377db8df7fbb727d4cb",deadline);
        pinClass(pack.getClass().getSuperclass(),8443,"a6d18d66b7f25f41e6fab7cd4956d4afb750f4254557f12dcbdbc286a3f15bf3",deadline);
        return new TaczView(pack,witness,deadline);
    }
    static RuntimeView inspectRuntime(PackResources pack,Path jar,long deadline)throws IOException {
        if(!runtime(pack))throw new IOException("Unexpected native runtime provider identity");
        var witness=pin(jar,1085674L,"37f05a6775bbe811fe8c2833fa6289a1c704d0b25bdd5f239d343a5c6f62ed8a",deadline);
        pinClass(pack.getClass(),14620,"05098526debde24c618391bd8c1eeaa3b285eeff290371aeedfc0602d532a244",deadline);
        return new RuntimeView(pack,witness,deadline);
    }

    static final class TaczView {
        final PackResources pack; final List<PackResources> children; final Set<String> namespaces;
        final String metadata; final FileWitness file; final long deadline;
        TaczView(PackResources pack,FileWitness file,long deadline)throws IOException {
            this.pack=pack;this.file=file;this.deadline=deadline;
            children=children();namespaces=Set.copyOf(pack.getNamespaces(PackType.SERVER_DATA));metadata=metadata(pack);
            var union=new TreeSet<String>();for(var child:children)union.addAll(child.getNamespaces(PackType.SERVER_DATA));
            if(!union.equals(namespaces))throw new IOException("Native TaCZ child namespace union differs");
        }
        private List<PackResources> children()throws IOException {
            check(deadline);
            try {
                Object result=pack.getClass().getSuperclass().getMethod("getChildren").invoke(pack);
                if(!(result instanceof Collection<?> values)||values.size()>512)
                    throw new IOException("Bounded native TaCZ ordered children required");
                var copy=new ArrayList<PackResources>();
                for(Object value:values) {
                    if(!(value instanceof PackResources child)||(child.getClass()!=PathPackResources.class&&child.getClass()!=FilePackResources.class))
                        throw new IOException("Native TaCZ factory produced an unknown child type");
                    copy.add(child);
                }
                return List.copyOf(copy);
            } catch(ReflectiveOperationException failure){throw new IOException("Native TaCZ getChildren API unavailable",failure);}
        }
        void unchanged()throws IOException {
            check(deadline);file.unchanged();var now=children();
            if(now.size()!=children.size())throw new IOException("Native TaCZ child count changed during custody");
            for(int n=0;n<now.size();n++)if(now.get(n)!=children.get(n))throw new IOException("Native TaCZ child order/identity changed");
            if(!namespaces.equals(pack.getNamespaces(PackType.SERVER_DATA))||!metadata.equals(metadata(pack)))
                throw new IOException("Native TaCZ namespace/metadata changed during custody");
        }
    }

    static final class RuntimeView {
        final PackResources pack; final FileWitness file; final long deadline; final Snapshot snapshot;
        final String metadata; final TreeMap<ResourceLocation,String> selectedHashes=new TreeMap<>();
        final TreeMap<String,String> rawHashes=new TreeMap<>();
        RuntimeView(PackResources pack,FileWitness file,long deadline)throws IOException {
            this.pack=pack;this.file=file;this.deadline=deadline;
            metadata=metadata(pack);snapshot=snapshot();
        }
        Set<ResourceLocation> ids(){return snapshot.ids.keySet();}
        Map<String,IoSupplier<InputStream>> raw(){return snapshot.raw;}
        IoSupplier<InputStream> listed(ResourceLocation id){return snapshot.ids.get(id);}
        void unchanged()throws IOException {
            check(deadline);file.unchanged();Snapshot next=snapshot();
            if(!snapshot.equals(next)||!metadata.equals(metadata(pack)))
                throw new IOException("Native runtime map/list/metadata changed during custody");
        }
        @SuppressWarnings("unchecked")
        private Snapshot snapshot()throws IOException {
            check(deadline);
            try {
                var lookup=MethodHandles.privateLookupIn(pack.getClass(),MethodHandles.lookup());
                var stored=(Map<?,?>)lookup.findGetter(pack.getClass(),"resources",Map.class).invoke(pack);
                var modFile=(IModFile)lookup.findGetter(pack.getClass(),"file",IModFile.class).invoke(pack);
                var type=(PackType)lookup.findGetter(pack.getClass(),"type",PackType.class).invoke(pack);
                if(type!=PackType.SERVER_DATA||stored==null||stored.size()>MAX)
                    throw new IOException("Bounded native SERVER_DATA runtime storage required");
                Path root=modFile.findResource(""); // exact native PackOutput constructor root
                Path dataRoot=modFile.findResource(PackType.SERVER_DATA.getDirectory());
                var raw=new TreeMap<String,IoSupplier<InputStream>>();
                var ids=new TreeMap<ResourceLocation,IoSupplier<InputStream>>();var namespaces=new TreeSet<String>();
                var members=new ArrayList<Map.Entry<Path,IoSupplier<InputStream>>>();
                for(var entry:stored.entrySet()) {
                    check(deadline);
                    if(!(entry.getKey() instanceof Path path)||!(entry.getValue() instanceof IoSupplier<?> supplier)
                        ||!path.normalize().equals(path)||!path.startsWith(root))
                        throw new IOException("Native runtime member is outside its exact mod root");
                    String relative=root.relativize(path).toString().replace('\\','/');
                    if(relative.length()>4096||raw.putIfAbsent(relative,(IoSupplier<InputStream>)supplier)!=null)
                        throw new IOException("Ambiguous/bounded native runtime raw member");
                    members.add(Map.entry(path,(IoSupplier<InputStream>)supplier));
                    // Exact pinned native getNamespaces uses all stored keys,
                    // including root icons, relative to the type directory.
                    // Do not silently filter its declared '..' namespace.
                    String namespace=dataRoot.relativize(path).getName(0).toString();
                    if(ResourceLocation.isValidNamespace(namespace))namespaces.add(namespace);
                }
                if(namespaces.size()>4096)throw new IOException("Bounded native runtime namespaces required");
                if(raw.size()!=stored.size()||!namespaces.equals(new TreeSet<>(pack.getNamespaces(PackType.SERVER_DATA))))
                    throw new IOException("Native runtime namespace/map inventory is incomplete");
                // Resolve each namespace through the SAME native mod-file API
                // used by list/get. Its filesystem controls '..' normalization;
                // preserving that behavior avoids invented or hidden resources.
                for(String namespace:namespaces) {
                    Path prefix=modFile.findResource(PackType.SERVER_DATA.getDirectory(),namespace);
                    for(var member:members) {
                        check(deadline);
                        if(!member.getKey().startsWith(prefix))continue;
                        String tail=prefix.relativize(member.getKey()).toString().replace('\\','/');
                        var id=ResourceLocation.tryBuild(namespace,tail);
                        if(id!=null&&ids.putIfAbsent(id,member.getValue())!=null)
                            throw new IOException("Duplicate native runtime logical resource");
                    }
                }
                var listed=new TreeMap<ResourceLocation,IoSupplier<InputStream>>();int[] visits={0};
                for(String namespace:namespaces)pack.listResources(PackType.SERVER_DATA,namespace,"",(id,supplier)->{
                    if(++visits[0]>MAX||System.nanoTime()-deadline>=0||id==null||supplier==null
                        ||!id.getNamespace().equals(namespace)||listed.putIfAbsent(id,supplier)!=null)
                        throw new IllegalStateException("Ambiguous/bounded native runtime listing");
                });
                if(!listed.equals(ids))throw new IOException("Native runtime raw map/list inventory differs");
                for(var entry:ids.entrySet())if(pack.getResource(PackType.SERVER_DATA,entry.getKey())!=entry.getValue())
                    throw new IOException("Native runtime list/get selected supplier differs");
                return new Snapshot(Map.copyOf(raw),Map.copyOf(ids),Set.copyOf(namespaces));
            }catch(IOException failure){throw failure;}
            catch(VirtualMachineError|ThreadDeath failure){throw failure;}
            catch(Throwable failure){throw new IOException("Pinned native runtime map API failed",failure);}
        }
    }
    private record Snapshot(Map<String,IoSupplier<InputStream>> raw,Map<ResourceLocation,IoSupplier<InputStream>> ids,Set<String> namespaces){}

    private static String metadata(PackResources pack)throws IOException {
        var section=pack.getMetadataSection(PackMetadataSection.TYPE);
        if(section==null)throw new IOException("Native synthetic PackMetadataSection is unavailable");
        String json=PackMetadataSection.TYPE.toJson(section).toString();
        if(json.length()>4096)throw new IOException("Bounded native pack metadata required");
        return json;
    }
    private record FileWitness(Path path,BasicFileAttributes before) {
        void unchanged()throws IOException {
            var after=Files.readAttributes(path,BasicFileAttributes.class,LinkOption.NOFOLLOW_LINKS);
            if(!after.isRegularFile()||after.isSymbolicLink()||before.size()!=after.size()
                ||!before.lastModifiedTime().equals(after.lastModifiedTime())||!Objects.equals(before.fileKey(),after.fileKey()))
                throw new IOException("Pinned generated-pack producer changed during custody");
        }
    }
    private static FileWitness pin(Path jar,long size,String expected,long deadline)throws IOException {
        var attrs=Files.readAttributes(jar,BasicFileAttributes.class,LinkOption.NOFOLLOW_LINKS);
        if(!attrs.isRegularFile()||attrs.isSymbolicLink()||attrs.size()!=size)
            throw new IOException("Exact generated-pack producer artifact required");
        try(InputStream input=Files.newInputStream(jar)) {
            if(!expected.equals(hash(input,size,deadline)))throw new IOException("Generated-pack producer artifact differs");
        }
        var witness=new FileWitness(jar,attrs);witness.unchanged();return witness;
    }
    private static void pinClass(Class<?> type,int size,String expected,long deadline)throws IOException {
        try(InputStream input=type.getResourceAsStream("/"+type.getName().replace('.','/')+".class")) {
            if(input==null||!expected.equals(hash(input,size,deadline)))throw new IOException("Pinned native generated-pack class differs");
        }
    }
    private static String hash(InputStream input,long size,long deadline)throws IOException {
        try {
            MessageDigest digest=MessageDigest.getInstance("SHA-256");byte[] bytes=new byte[65536];long total=0;
            for(int n;(n=input.read(bytes))!=-1;){check(deadline);total+=n;if(total>size)throw new IOException("Generated-pack custody byte bound exceeded");digest.update(bytes,0,n);}
            if(total!=size)throw new IOException("Truncated generated-pack custody input");
            return HexFormat.of().formatHex(digest.digest());
        }catch(java.security.NoSuchAlgorithmException impossible){throw new AssertionError(impossible);}
    }
    private static void check(long deadline)throws IOException {
        if(System.nanoTime()-deadline>=0)throw new IOException("Generated-pack custody exceeded the shared finite deadline");
    }
}
