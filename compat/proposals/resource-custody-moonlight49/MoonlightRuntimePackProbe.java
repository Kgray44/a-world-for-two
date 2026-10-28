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
import java.util.Set;
import java.util.TreeMap;
import java.util.TreeSet;
import net.mehvahdjukaar.moonlight.api.resources.pack.AbstractCachedEditableResources;
import net.mehvahdjukaar.moonlight.api.resources.pack.CachePathPackResources;
import net.mehvahdjukaar.moonlight.api.resources.pack.FastSearchPathPackResources;
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

/** Offline real resource-class fixture; no loader, world, accounts or network. */
public final class MoonlightRuntimePackProbe {
    record Proof(Set<ResourceLocation> ids,String digest,Map<String,String> selectedBytes){}
    private static void check(boolean value,String reason){if(!value)throw new AssertionError(reason);}
    private static PackLocationInfo info(String id){return new PackLocationInfo(id,Component.literal(id),PackSource.BUILT_IN,Optional.empty());}
    private static void wire(CachePathPackResources pack,PackResources delegate)throws Throwable {
        // Fixture-only object graph wiring. Production NEVER writes these
        // fields or invokes initializeIfValid/commitChanges. This constructs
        // exactly the two delegate alternatives proven by pinned bytecode,
        // without starting Moonlight's loader-bound config pipeline.
        MethodHandles.privateLookupIn(AbstractCachedEditableResources.class,MethodHandles.lookup())
            .findSetter(AbstractCachedEditableResources.class,"cachedResources",PackResources.class).invoke(pack,delegate);
    }
    private static CachePathPackResources fixture(Path root,boolean fast)throws Throwable {
        var location=info(MoonlightCachePackCustody.PACK);
        var pack=new CachePathPackResources(location,PackType.SERVER_DATA,root);
        pack.addNamespaces("supplementaries","declared_empty_namespace");
        pack.addRootResource("pack.mcmeta","{\"pack\":{\"pack_format\":48,\"description\":\"original offline fixture\"}}".getBytes(StandardCharsets.UTF_8));
        wire(pack,fast?new FastSearchPathPackResources(location,root,PackType.SERVER_DATA):new PathPackResources(location,root));
        return pack;
    }
    private static Proof inventory(CachePathPackResources pack,Path jar)throws Throwable {
        var view=MoonlightCachePackCustody.inspect(pack,jar);
        Class<?> counter=Class.forName("worldfortwo.bridge.LithostitchedSeedgenResources$Accumulator");
        var lookup=MethodHandles.privateLookupIn(counter,MethodHandles.lookup());
        Object accumulator=lookup.findConstructor(counter,MethodType.methodType(void.class)).invoke();
        var ids=new TreeSet<ResourceLocation>();var raw=new TreeSet<String>();
        MethodHandles.privateLookupIn(LithostitchedSeedgenResources.class,MethodHandles.lookup())
            .findStatic(LithostitchedSeedgenResources.class,"moonlightInventory",MethodType.methodType(void.class,
                PackResources.class,MoonlightCachePackCustody.View.class,counter,TreeSet.class,TreeSet.class))
            .invoke(pack,view,accumulator,ids,raw);
        var selected=new TreeMap<String,String>();
        var hashResource=lookup.findVirtual(counter,"resource",MethodType.methodType(void.class,String.class,IoSupplier.class));
        for(var id:ids){
            var supplier=LithostitchedSeedgenResources.selected(pack,id,raw,List.of());
            hashResource.invoke(accumulator,id.toString(),supplier);
            try(var input=supplier.get()){selected.put(id.toString(),new String(input.readAllBytes(),StandardCharsets.UTF_8));}
        }
        view.unchanged();
        MessageDigest digest=(MessageDigest)lookup.findGetter(counter,"digest",MessageDigest.class).invoke(accumulator);
        return new Proof(Set.copyOf(ids),HexFormat.of().formatHex(digest.digest()),Map.copyOf(selected));
    }
    @FunctionalInterface interface Action {void run()throws Throwable;}
    private static void refused(Action action,String reason)throws Throwable {
        try{action.run();throw new AssertionError("Unexpected custody admission: "+reason);}
        catch(IOException expected){}
    }
    public static void main(String[] args)throws Throwable {
        Path jar=Path.of(args[0]);SharedConstants.tryDetectVersion();Bootstrap.bootStrap();
        Path root=Path.of("ordinary-cache");Files.createDirectories(root.resolve("data/supplementaries/worldgen"));
        Path json=root.resolve("data/supplementaries/worldgen/fixture.json");
        Files.writeString(json,"{\"value\":1}");Files.writeString(root.resolve("data/supplementaries/root.json"),"{\"root\":true}");
        for(boolean fast:new boolean[]{false,true}){
            CachePathPackResources pack=fixture(root,fast);
            if(fast){
                var observed=MoonlightCachePackCustody.inspect(pack,jar);
                check(observed.namespaces.contains("supplementaries")&&observed.delegate.getNamespaces(PackType.SERVER_DATA).isEmpty(),
                    "Pinned wrapper namespace authority is independent of the internal FastSearch empty namespace report");
            }
            Proof first=inventory(pack,jar);
            check(first.ids().equals(Set.of(ResourceLocation.parse("supplementaries:worldgen/fixture.json"),ResourceLocation.parse("supplementaries:root.json"))),"Exact native complete inventory");
            check(first.equals(inventory(pack,jar)),"Stable original bytes remain deterministic");
            Files.writeString(json,"{\"value\":2}");
            Proof changed=inventory(pack,jar);
            check(!first.digest().equals(changed.digest()),"Same-ID original file byte change must affect custody");
            check(changed.selectedBytes().get("supplementaries:worldgen/fixture.json").equals("{\"value\":2}"),"Original provider getResource supplies actual changed bytes");
            Files.writeString(json,"{\"value\":1}");
            var view=MoonlightCachePackCustody.inspect(pack,jar);
            pack.addRootResource("pack.mcmeta","changed original metadata bytes".getBytes(StandardCharsets.UTF_8));
            refused(view::unchanged,"Original root resource mutation");
            view=MoonlightCachePackCustody.inspect(pack,jar);
            wire(pack,new PathPackResources(info(MoonlightCachePackCustody.PACK),root));
            var changedView=view;refused(changedView::unchanged,"Delegate replaced during capture");
        }
        var fast=fixture(root,true);Files.writeString(root.resolve("data/supplementaries/worldgen/added.json"),"{}");
        refused(()->inventory(fast,jar),"Native stale/partial search trie");
        var uninitialized=new CachePathPackResources(info(MoonlightCachePackCustody.PACK),PackType.SERVER_DATA,root);
        refused(()->MoonlightCachePackCustody.inspect(uninitialized,jar),"Uninitialized provider must not masquerade as empty");
        Path emptyRoot=Path.of("genuine-empty-cache");Files.createDirectory(emptyRoot);
        var empty=fixture(emptyRoot,true);
        check(inventory(empty,jar).ids().isEmpty(),"Initialized ordinary empty cache is proved empty by real walk/list/get coverage, not by skipping the provider");
        var unknown=new CachePathPackResources(info(MoonlightCachePackCustody.PACK),PackType.SERVER_DATA,root){};
        refused(()->MoonlightCachePackCustody.inspect(unknown,jar),"Unknown subclass");
        var wrongId=new CachePathPackResources(info("unreviewed:provider"),PackType.SERVER_DATA,root);
        refused(()->MoonlightCachePackCustody.inspect(wrongId,jar),"Unreviewed provider identity");
        byte[] bad=Files.readAllBytes(jar);bad[0]^=1;Path corrupt=Path.of("changed-provider.jar");Files.write(corrupt,bad);
        refused(()->MoonlightCachePackCustody.inspect(fixture(root,false),corrupt),"Changed exact JAR");
        Path overlayRoot=Path.of("overlay");Files.createDirectories(overlayRoot.resolve("data/supplementaries/worldgen"));
        Files.writeString(overlayRoot.resolve("data/supplementaries/worldgen/fixture.json"),"{\"override\":true}");
        var cache=fixture(root,false);var overlay=new PathPackResources(info("fixture-overlay"),overlayRoot);
        try(var manager=new MultiPackResourceManager(PackType.SERVER_DATA,List.of(cache,overlay))){
            check(manager.listPacks().toList().equals(List.of(cache,overlay)),"Real effective pack manager retains actual ordered objects");
            var stack=manager.getResourceStack(ResourceLocation.parse("supplementaries:worldgen/fixture.json"));
            check(stack.size()==2&&stack.get(0).sourcePackId().equals(MoonlightCachePackCustody.PACK)&&stack.get(1).sourcePackId().equals("fixture-overlay"),"Original native override stack ordering");
        }
        System.out.println("PASS actual Moonlight cached wrapper with both native delegates: exact original inventory/root metadata/selected bytes, same-ID byte sensitivity, stable repeat, genuine initialized empty inventory, original effective order, stale index/changed delegate/uninitialized/unknown subclass/wrong identity/corrupt JAR refusals. Fixture wiring only; no ModList, game, Level, network or native parity acceptance.");
    }
}
