package worldfortwo.bridge;

import com.mojang.datafixers.util.Either;
import com.yungnickyoung.minecraft.yungsapi.world.structure.locate.LocateReplacerDataPackResources;
import com.yungnickyoung.minecraft.yungsapi.world.structure.locate.LocateReplacerImpl;
import java.lang.invoke.MethodHandles;
import java.lang.invoke.MethodType;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Set;
import net.minecraft.SharedConstants;
import net.minecraft.core.registries.Registries;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceKey;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.Bootstrap;
import net.minecraft.server.packs.PackResources;
import net.minecraft.server.packs.PackType;

/** Original isolated actual-API fixture: no modloader, Level, account or network. */
public final class YungRuntimePackProbe {
    private static void check(boolean condition,String reason){if(!condition)throw new AssertionError(reason);}
    public static void main(String[] args)throws Throwable {
        Path jar=Path.of(args[0]);
        SharedConstants.tryDetectVersion();Bootstrap.bootStrap();
        Class<?> type=LocateReplacerDataPackResources.class;
        var constructor=MethodHandles.privateLookupIn(type,MethodHandles.lookup()).findConstructor(type,MethodType.methodType(void.class))
            .asType(MethodType.methodType(PackResources.class));
        PackResources pack=(PackResources)constructor.invokeExact();
        check(YungLocatePackCustody.inventory(pack,jar).equals(Set.of(YungLocatePackCustody.TAG)),"Exact original native singleton inventory");
        byte[] metadata;
        try(var stream=pack.getRootResource("pack.mcmeta").get()) {metadata=stream.readNBytes(1024*1024+1);}
        check(metadata.length>0&&metadata.length<=1024*1024,"Bounded original native metadata bytes");
        String before;
        try(var stream=pack.getResource(PackType.SERVER_DATA,YungLocatePackCustody.TAG).get()) {before=new String(stream.readAllBytes(),java.nio.charset.StandardCharsets.UTF_8);}
        // Mutation is ONLY in this isolated JVM's original native registration
        // map. It proves the actual provider's dynamic bytes are not discarded.
        LocateReplacerImpl.INSTANCE.registerRemoval(Either.left(ResourceKey.create(Registries.STRUCTURE,
            ResourceLocation.parse("minecraft:desert_pyramid"))),Component.literal("original isolated fixture"),()->true);
        String changed;
        try(var stream=pack.getResource(PackType.SERVER_DATA,YungLocatePackCustody.TAG).get()) {changed=new String(stream.readAllBytes(),java.nio.charset.StandardCharsets.UTF_8);}
        check(!before.equals(changed)&&changed.contains("minecraft:desert_pyramid"),"Native dynamic resource content must change");
        check(YungLocatePackCustody.inventory(pack,jar).equals(Set.of(YungLocatePackCustody.TAG)),"Native dynamic content keeps exact inventory");
        var unknown=new LocateReplacerDataPackResources(){};
        check(!YungLocatePackCustody.matches(unknown),"Unknown subclass refuses");
        try {YungLocatePackCustody.inventory(unknown,jar);throw new AssertionError("Unknown subclass admitted");}
        catch(java.io.IOException expected){}
        byte[] corrupt=Files.readAllBytes(jar);corrupt[0]^=1;Path bad=Path.of("changed-provider.jar");Files.write(bad,corrupt);
        try {YungLocatePackCustody.inventory(pack,bad);throw new AssertionError("Changed artifact admitted");}
        catch(java.io.IOException expected){}
        System.out.println("PASS exact native YUNG singleton and original metadata bytes; original dynamic bytes change; unknown subclass and changed JAR refuse. No native world or loader executed.");
        System.out.println("metadata_sha256="+sha(metadata)+"; native_tag_before_sha256="+sha(before.getBytes(java.nio.charset.StandardCharsets.UTF_8))+"; native_tag_changed_sha256="+sha(changed.getBytes(java.nio.charset.StandardCharsets.UTF_8)));
    }
    private static String sha(byte[] raw)throws Exception{return java.util.HexFormat.of().formatHex(java.security.MessageDigest.getInstance("SHA-256").digest(raw));}
}
