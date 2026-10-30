package worldfortwo.bridge;

import java.io.IOException;
import java.lang.invoke.MethodHandles;
import java.lang.invoke.MethodType;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.util.HexFormat;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.TreeSet;
import java.util.concurrent.TimeUnit;
import net.mehvahdjukaar.moonlight.api.resources.pack.InMemoryPackResources;
import net.mehvahdjukaar.moonlight.api.resources.pack.PackGenerationStrategy;
import net.minecraft.SharedConstants;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.Bootstrap;
import net.minecraft.server.packs.PackLocationInfo;
import net.minecraft.server.packs.PackResources;
import net.minecraft.server.packs.PackType;
import net.minecraft.server.packs.PathPackResources;
import net.minecraft.server.packs.repository.PackSource;
import net.minecraft.server.packs.resources.IoSupplier;
import net.minecraft.server.packs.resources.MultiPackResourceManager;

/** Offline real-provider fixtures only. No loader,event,Level,accounts or network. */
public final class MoonlightMemoryPackProbe {
    private static Path moonlight,amendments;
    private static final ResourceLocation ID=ResourceLocation.parse("amendments:recipes/custody_probe.json");
    private static PackLocationInfo info(String id){return new PackLocationInfo(id,Component.literal(id),PackSource.BUILT_IN,Optional.empty());}
    private static byte[] bytes(String value){return value.getBytes(StandardCharsets.UTF_8);}
    private static void check(boolean value,String reason){if(!value)throw new AssertionError(reason);}
    private static InMemoryPackResources nativePack(String id,PackType kind) {
        return (InMemoryPackResources)PackGenerationStrategy.REGEN_ON_EVERY_RELOAD.createPackResources(info(id),kind);
    }
    private static InMemoryPackResources fixture() {
        var pack=nativePack(MoonlightInMemoryPackCustody.PACK,PackType.SERVER_DATA);
        pack.addNamespaces("amendments","declared_empty_namespace");
        pack.addResource(ID,bytes("{\"original\":1}"));
        pack.addResource(ResourceLocation.parse("amendments:root.json"),bytes("{\"root\":true}"));
        pack.addRootResource("metadata/nested.txt",bytes("literal native root bytes"));
        return pack;
    }
    private static MoonlightInMemoryPackCustody.View inspect(PackResources pack)throws IOException {
        return MoonlightInMemoryPackCustody.inspect(pack,moonlight,amendments,System.nanoTime()+TimeUnit.SECONDS.toNanos(60));
    }
    private static String proof(InMemoryPackResources pack)throws Throwable {
        var view=inspect(pack);Class<?> type=Class.forName("worldfortwo.bridge.LithostitchedSeedgenResources$Accumulator");
        var lookup=MethodHandles.privateLookupIn(type,MethodHandles.lookup());
        Object out=lookup.findConstructor(type,MethodType.methodType(void.class)).invoke();var ids=new TreeSet<ResourceLocation>();
        MethodHandles.privateLookupIn(LithostitchedSeedgenResources.class,MethodHandles.lookup())
            .findStatic(LithostitchedSeedgenResources.class,"memoryInventory",MethodType.methodType(void.class,
                PackResources.class,MoonlightInMemoryPackCustody.View.class,type,TreeSet.class)).invoke(pack,view,out,ids);
        var hashResource=lookup.findVirtual(type,"resource",MethodType.methodType(void.class,String.class,IoSupplier.class));
        for(var id:ids)hashResource.invoke(out,id.toString(),LithostitchedSeedgenResources.selected(pack,id,java.util.Set.of(),List.of()));
        view.unchanged();MessageDigest digest=(MessageDigest)lookup.findGetter(type,"digest",MessageDigest.class).invoke(out);
        return HexFormat.of().formatHex(digest.digest());
    }
    @FunctionalInterface interface Action {void run()throws Throwable;}
    private static void refused(Action action,String reason)throws Throwable {
        try{action.run();}catch(IOException expected){return;}
        throw new AssertionError("Custody must refuse: "+reason);
    }
    @SuppressWarnings("unchecked")
    public static void main(String[] args)throws Throwable {
        moonlight=Path.of(args[0]);amendments=Path.of(args[1]);SharedConstants.tryDetectVersion();Bootstrap.bootStrap();
        var pack=fixture();var first=inspect(pack);
        check(first.ids().size()==2&&first.rootNames().size()==1,"Complete original data/root key inventory");
        String baseline=proof(pack);check(baseline.equals(proof(pack)),"Stable repeat byte attestation");
        pack.addResource(ID,bytes("{\"original\":2}"));
        refused(first::unchanged,"Same-ID byte replacement");check(!baseline.equals(proof(pack)),"Selected original byte changes alter existing accumulator digest");
        var rootView=inspect(pack);pack.addRootResource("metadata/nested.txt",bytes("changed original root bytes"));
        refused(rootView::unchanged,"Original root byte change");
        var raw=fixture();var lookup=MethodHandles.privateLookupIn(InMemoryPackResources.class,MethodHandles.lookup());
        var map=(Map<ResourceLocation,byte[]>)lookup.findGetter(InMemoryPackResources.class,"resources",Map.class).invoke(raw);
        var rawView=inspect(raw);map.get(ID)[0]^=1;
        refused(rawView::unchanged,"In-place native byte-array mutation");
        var stale=fixture();var staleMap=(Map<ResourceLocation,byte[]>)lookup.findGetter(InMemoryPackResources.class,"resources",Map.class).invoke(stale);
        staleMap.put(ResourceLocation.parse("amendments:recipes/unindexed.json"),bytes("{}"));
        refused(()->inspect(stale),"Raw memory member omitted by native search trie");
        var wrong=nativePack("unreviewed:memory",PackType.SERVER_DATA);
        refused(()->inspect(wrong),"Unknown provider identity");
        var client=nativePack(MoonlightInMemoryPackCustody.PACK,PackType.CLIENT_RESOURCES);
        refused(()->inspect(client),"Wrong actual pack type");
        var child=new InMemoryPackResources(info(MoonlightInMemoryPackCustody.PACK),PackType.SERVER_DATA){};
        refused(()->inspect(child),"Unknown native subclass");
        var empty=nativePack(MoonlightInMemoryPackCustody.PACK,PackType.SERVER_DATA);
        empty.addNamespaces("declared_empty_namespace");
        check(inspect(empty).ids().isEmpty(),"Genuine empty map/list/get custody; no empty inference");
        var metadata=fixture();
        check(metadata.getRootResource("pack.mcmeta")==null,"Native absent root metadata is measured,not invented");
        ((net.minecraft.network.chat.MutableComponent)metadata.getMetadataSection(
            net.minecraft.server.packs.metadata.pack.PackMetadataSection.TYPE).description()).append(" changed");
        refused(()->inspect(metadata),"Changed actual native metadata object");
        byte[] changed=Files.readAllBytes(amendments);changed[0]^=1;Path bad=Path.of("changed-amendments.jar");Files.write(bad,changed);
        refused(()->MoonlightInMemoryPackCustody.inspect(fixture(),moonlight,bad,System.nanoTime()+TimeUnit.SECONDS.toNanos(60)),"Changed exact producer JAR");
        Path root=Path.of("overlay");Files.createDirectories(root.resolve("data/amendments/recipes"));
        Files.writeString(root.resolve("data/amendments/recipes/custody_probe.json"),"{\"override\":true}");
        var original=fixture();var overlay=new PathPackResources(info("fixture-overlay"),root);
        try(var manager=new MultiPackResourceManager(PackType.SERVER_DATA,List.of(original,overlay))) {
            var stack=manager.getResourceStack(ID);
            check(stack.size()==2&&stack.get(0).sourcePackId().equals(MoonlightInMemoryPackCustody.PACK)
                &&stack.get(1).sourcePackId().equals("fixture-overlay"),"Actual native complete override stack ordering retained");
        }
        System.out.println("PASS actual pinned native memory provider: raw/list/get/root coverage,stable/same-ID byte sensitivity,in-place mutation,stale trie,wrong ID/type/subclass/corrupt producer refusals,genuine empty proof and real effective override stack. No loader,event,Level,world,network or terrain-parity claim.");
    }
}
