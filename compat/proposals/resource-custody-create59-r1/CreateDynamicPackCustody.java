package worldfortwo.bridge;

import java.io.IOException;
import java.io.InputStream;
import java.lang.invoke.MethodHandles;
import java.nio.file.Files;
import java.nio.file.LinkOption;
import java.nio.file.Path;
import java.nio.file.attribute.BasicFileAttributes;
import java.security.MessageDigest;
import java.util.HexFormat;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.TreeMap;
import java.util.TreeSet;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.packs.PackResources;
import net.minecraft.server.packs.PackType;
import net.minecraft.server.packs.metadata.pack.PackMetadataSection;
import net.minecraft.server.packs.resources.IoSupplier;
import net.neoforged.fml.ModList;

/** Exact original view of Create's native generated string-to-supplier map. */
final class CreateDynamicPackCustody {
    static final String TYPE="com.simibubi.create.foundation.pack.DynamicPack";
    private static final int MAX=262144;
    private CreateDynamicPackCustody(){}
    static boolean matches(PackResources pack){return pack.getClass().getName().equals(TYPE);}
    static View inspect(PackResources pack,long deadline)throws IOException {
        return inspect(pack,ModList.get().getModFileById("create").getFile().getFilePath(),deadline);
    }
    /** Separate exact archive input supports the offline fixture, never a runtime override. */
    static View inspect(PackResources pack,Path jar,long deadline)throws IOException {
        if(!matches(pack)||!pack.packId().equals("create:dynamic_data"))throw new IOException("Unexpected native Create dynamic pack");
        var before=Files.readAttributes(jar,BasicFileAttributes.class,LinkOption.NOFOLLOW_LINKS);
        if(!before.isRegularFile()||before.isSymbolicLink()||before.size()!=19123767)
            throw new IOException("Exact Create6.0.10 artifact required");
        try(InputStream input=Files.newInputStream(jar)) {
            if(!"ef87fe5709f1ba1f5b8bb20a2925b5afb4669e178fd6d8bf10c167759eefe37a".equals(hash(input,19123767,deadline)))
                throw new IOException("Pinned Create producer artifact differs");
        }
        try(InputStream input=pack.getClass().getResourceAsStream("/"+TYPE.replace('.','/')+".class")) {
            if(input==null||!"db86ed4b328d60434ef23c35b87766a5acc456d50209b04f317967da04e40efd".equals(hash(input,10226,deadline)))
                throw new IOException("Pinned native Create DynamicPack class differs");
        }
        var view=new View(pack,jar,before,deadline);view.unchanged();return view;
    }

    static final class View {
        final PackResources pack;final Path jar;final BasicFileAttributes file;final long deadline;
        final Snapshot snapshot;final String metadata;
        final TreeMap<String,String> rawHashes=new TreeMap<>();
        final TreeMap<ResourceLocation,String> selectedHashes=new TreeMap<>();
        View(PackResources pack,Path jar,BasicFileAttributes file,long deadline)throws IOException {
            this.pack=pack;this.jar=jar;this.file=file;this.deadline=deadline;
            snapshot=snapshot();metadata=metadata();
        }
        Map<String,IoSupplier<InputStream>> raw(){return snapshot.raw;}
        Set<ResourceLocation> ids(){return snapshot.ids.keySet();}
        IoSupplier<InputStream> listedOrDirect(ResourceLocation id){return snapshot.ids.get(id);}
        void unchanged()throws IOException {
            check(deadline);var next=Files.readAttributes(jar,BasicFileAttributes.class,LinkOption.NOFOLLOW_LINKS);
            if(!next.isRegularFile()||next.isSymbolicLink()||file.size()!=next.size()
                ||!file.lastModifiedTime().equals(next.lastModifiedTime())||!Objects.equals(file.fileKey(),next.fileKey()))
                throw new IOException("Create producer changed during native custody");
            if(!snapshot.equals(snapshot())||!metadata.equals(metadata()))throw new IOException("Create native map/list/metadata changed during custody");
        }
        private String metadata()throws IOException {
            var section=pack.getMetadataSection(PackMetadataSection.TYPE);
            if(section==null)throw new IOException("Native Create PackMetadataSection is unavailable");
            String result=PackMetadataSection.TYPE.toJson(section).toString();
            if(result.length()>4096)throw new IOException("Bounded native Create metadata required");
            return result;
        }
        @SuppressWarnings("unchecked")
        private Snapshot snapshot()throws IOException {
            check(deadline);
            try {
                var lookup=MethodHandles.privateLookupIn(pack.getClass(),MethodHandles.lookup());
                var stored=(Map<?,?>)lookup.findGetter(pack.getClass(),"files",Map.class).invoke(pack);
                var type=(PackType)lookup.findGetter(pack.getClass(),"packType",PackType.class).invoke(pack);
                if(type!=PackType.SERVER_DATA||stored==null||stored.size()>MAX)throw new IOException("Bounded native Create SERVER_DATA storage required");
                var raw=new TreeMap<String,IoSupplier<InputStream>>();var ids=new TreeMap<ResourceLocation,IoSupplier<InputStream>>();
                var namespaces=new TreeSet<String>();var prefixes=new TreeMap<String,TreeSet<String>>();var nested=new TreeMap<ResourceLocation,IoSupplier<InputStream>>();
                for(var entry:stored.entrySet()) {
                    check(deadline);
                    if(!(entry.getKey() instanceof String name)||name.length()>4096||!(entry.getValue() instanceof IoSupplier<?> supplier))
                        throw new IOException("Unexpected native Create raw member");
                    if(raw.putIfAbsent(name,(IoSupplier<InputStream>)supplier)!=null)throw new IOException("Duplicate native Create raw member");
                    if(!name.startsWith("data/"))continue;
                    String relative=name.substring(5);int slash=relative.indexOf('/');if(slash<0)continue;
                    String namespace=relative.substring(0,slash),path=relative.substring(slash+1);namespaces.add(namespace);
                    var id=ResourceLocation.tryBuild(namespace,path);
                    if(id==null)continue; // original raw bytes remain mandatory even where no native ID exists
                    if(ids.putIfAbsent(id,(IoSupplier<InputStream>)supplier)!=null)throw new IOException("Duplicate native Create logical member");
                    int directory=path.indexOf('/');
                    if(directory>=0) {
                        String prefix=path.substring(0,directory);
                        if(prefix.isEmpty()||prefix.equals(".")||prefix.equals(".."))throw new IOException("Create native prefix requires separate exact custody");
                        prefixes.computeIfAbsent(namespace,ignored->new TreeSet<>()).add(prefix);nested.put(id,(IoSupplier<InputStream>)supplier);
                    }
                }
                if(raw.size()!=stored.size()||namespaces.size()>4096||!namespaces.equals(new TreeSet<>(pack.getNamespaces(PackType.SERVER_DATA))))
                    throw new IOException("Native Create namespace/raw inventory is incomplete");
                // Native listResources appends '/' even for the empty prefix.
                // Query only real nonempty directories; prove namespace-root
                // files independently from the exact raw map plus native get.
                var listed=new TreeMap<ResourceLocation,IoSupplier<InputStream>>();int[] visits={0};
                for(var entry:prefixes.entrySet())for(String prefix:entry.getValue())
                    pack.listResources(PackType.SERVER_DATA,entry.getKey(),prefix,(id,supplier)->{
                        if(++visits[0]>MAX||System.nanoTime()-deadline>=0||id==null||supplier==null||listed.putIfAbsent(id,supplier)!=null)
                            throw new IllegalStateException("Ambiguous/bounded native Create listing");
                    });
                if(!listed.equals(nested))throw new IOException("Native Create nonempty-prefix inventory differs from raw map");
                for(var entry:ids.entrySet())if(pack.getResource(PackType.SERVER_DATA,entry.getKey())!=entry.getValue())
                    throw new IOException("Native Create selected supplier differs from original raw/list source");
                return new Snapshot(Map.copyOf(raw),Map.copyOf(ids),Set.copyOf(namespaces));
            }catch(IOException failure){throw failure;}
            catch(VirtualMachineError|ThreadDeath failure){throw failure;}
            catch(Throwable failure){throw new IOException("Pinned native Create map API failed",failure);}
        }
    }
    private record Snapshot(Map<String,IoSupplier<InputStream>> raw,Map<ResourceLocation,IoSupplier<InputStream>> ids,Set<String> namespaces){}
    private static String hash(InputStream input,int exact,long deadline)throws IOException {
        try {
            MessageDigest digest=MessageDigest.getInstance("SHA-256");byte[] bytes=new byte[65536];int total=0;
            for(int n;(n=input.read(bytes))!=-1;){check(deadline);total+=n;if(total>exact)throw new IOException("Create custody input exceeds its exact bound");digest.update(bytes,0,n);}
            if(total!=exact)throw new IOException("Create custody input is truncated");return HexFormat.of().formatHex(digest.digest());
        }catch(java.security.NoSuchAlgorithmException impossible){throw new AssertionError(impossible);}
    }
    private static void check(long deadline)throws IOException {
        if(System.nanoTime()-deadline>=0)throw new IOException("Create custody exceeded the original aggregate deadline");
    }
}
