package worldfortwo.bridge;

import java.io.IOException;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.LinkOption;
import java.nio.file.Path;
import java.nio.file.attribute.BasicFileAttributes;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.HexFormat;
import java.util.Objects;
import java.util.Set;
import java.util.TreeSet;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.packs.PackResources;
import net.minecraft.server.packs.PackType;
import net.neoforged.fml.ModList;

/** Original exact adapter: enumerate the author's native dynamic tag; never invent JSON. */
final class YungLocatePackCustody {
    static final String TYPE="com.yungnickyoung.minecraft.yungsapi.world.structure.locate.LocateReplacerDataPackResources";
    static final String JAR_SHA="375e0b2f988ab4f5bde182166c0f0b102377adc8f823660c24ade08b0b3cde56";
    static final ResourceLocation TAG=ResourceLocation.parse("c:tags/worldgen/structure/hidden_from_locator_selection.json");
    private YungLocatePackCustody(){}
    static boolean matches(PackResources pack){return pack.getClass().getName().equals(TYPE);}

    static Set<ResourceLocation> inventory(PackResources pack)throws IOException {
        var mod=ModList.get().getModContainerById("yungsapi").orElseThrow();
        if(!mod.getModInfo().getVersion().toString().equals("1.21.1-NeoForge-5.1.9"))
            throw new IOException("Exact YUNG API5.1.9 runtime resource provider required");
        return inventory(pack,ModList.get().getModFileById("yungsapi").getFile().getFilePath());
    }

    /** Separate native-file input permits an offline exact-JAR fixture, not a runtime override. */
    static Set<ResourceLocation> inventory(PackResources pack,Path jar)throws IOException {
        if(!matches(pack)||!pack.packId().equals("mod/yungsapi:locate_replacer"))
            throw new IOException("Unsupported runtime pack implementation/identity");
        var before=Files.readAttributes(jar,BasicFileAttributes.class,LinkOption.NOFOLLOW_LINKS);
        if(!before.isRegularFile()||before.isSymbolicLink()||before.size()!=413763)
            throw new IOException("Exact YUNG API artifact size/type required");
        try(InputStream input=Files.newInputStream(jar)) {
            if(!JAR_SHA.equals(hash(input,413763)))throw new IOException("Pinned YUNG API artifact differs");
        }
        var after=Files.readAttributes(jar,BasicFileAttributes.class,LinkOption.NOFOLLOW_LINKS);
        if(before.size()!=after.size()||!before.lastModifiedTime().equals(after.lastModifiedTime())
                ||!Objects.equals(before.fileKey(),after.fileKey()))throw new IOException("YUNG API artifact changed during custody");
        try(InputStream input=pack.getClass().getResourceAsStream("LocateReplacerDataPackResources.class")) {
            if(input==null||!"eb26bbbc9e71adccff0e52ec00853c9506b24f9adc83f2f6a9b78cfdbd753ebd".equals(hash(input,9656)))
                throw new IOException("Pinned native YUNG runtime pack class differs");
        }
        if(!pack.getNamespaces(PackType.SERVER_DATA).equals(Set.of("c")))
            throw new IOException("YUNG native runtime namespaces changed");
        for(String prefix:new String[]{"","tags","tags/worldgen/structure"}) {
            var found=new TreeSet<ResourceLocation>();int[] count={0};
            pack.listResources(PackType.SERVER_DATA,"c",prefix,(id,supplier)->{
                if(++count[0]>1||!id.equals(TAG)||supplier==null)
                    throw new IllegalStateException("Unexpected native YUNG runtime resource");
                found.add(id);
            });
            if(!found.equals(Set.of(TAG)))throw new IOException("Incomplete native YUNG runtime resource inventory");
        }
        if(pack.getRootResource("pack.mcmeta")==null||pack.getResource(PackType.SERVER_DATA,TAG)==null)
            throw new IOException("Native YUNG metadata/tag supplier unavailable");
        // The caller hashes these original native bytes AND every effective
        // manager stack. This singleton describes resources, not an empty pack.
        return Set.of(TAG);
    }

    private static String hash(InputStream input,int exact)throws IOException {
        try {
            MessageDigest digest=MessageDigest.getInstance("SHA-256");byte[] buffer=new byte[8192];int total=0;
            for(int size;(size=input.read(buffer))!=-1;){total+=size;if(total>exact)throw new IOException("Native YUNG custody exceeds exact byte bound");digest.update(buffer,0,size);}
            if(total!=exact)throw new IOException("Native YUNG custody input is truncated");
            return HexFormat.of().formatHex(digest.digest());
        }catch(NoSuchAlgorithmException impossible){throw new AssertionError(impossible);}
    }
}
