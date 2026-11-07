package worldfortwo.bridge;

import java.io.ByteArrayInputStream;
import java.lang.reflect.Field;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Proxy;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.Optional;
import java.util.TreeSet;
import java.util.concurrent.ConcurrentHashMap;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.packs.PackLocationInfo;
import net.minecraft.server.packs.PackResources;
import net.minecraft.server.packs.PackType;
import net.minecraft.server.packs.PathPackResources;
import net.minecraft.server.packs.metadata.pack.PackMetadataSection;
import net.minecraft.server.packs.repository.PackSource;
import net.minecraft.server.packs.resources.IoSupplier;
import net.neoforged.neoforgespi.locating.IModFile;

/** Controlled storage inputs exercise actual pinned provider methods; no mod bootstrap or world. */
public final class GeneratedPackProbe {
    public static void main(String[] args)throws Exception {
        if(args.length!=3)throw new IllegalArgumentException("TaCZ archive, CDP archive and owned fixture directory required");
        Path root=Path.of(args[2]).toAbsolutePath();Files.createDirectories(root);
        // The native component codec requires vanilla's static registries. This
        // initializes no server/client/world and invokes no terrain generator.
        net.minecraft.SharedConstants.tryDetectVersion();
        net.minecraft.server.Bootstrap.bootStrap();
        long deadline=System.nanoTime()+java.util.concurrent.TimeUnit.SECONDS.toNanos(40);
        Path a=root.resolve("child-a"),b=root.resolve("child-b");
        Path relative=Path.of("data/demo/worldgen/noise/test.json");
        Files.createDirectories(a.resolve(relative).getParent());Files.createDirectories(b.resolve(relative).getParent());
        Files.writeString(a.resolve(relative),"first native child",StandardCharsets.UTF_8);
        Files.writeString(b.resolve(relative),"masked native child",StandardCharsets.UTF_8);
        PackResources childA=new PathPackResources(location("first"),a),childB=new PathPackResources(location("second"),b);
        Class<?> anonymous=Class.forName(GeneratedServerPackCustody.TACZ);
        var constructor=anonymous.getDeclaredConstructors()[0];constructor.setAccessible(true);
        var metadata=new PackMetadataSection(Component.literal("native fixture metadata"),48,Optional.empty());
        PackResources tacz=(PackResources)constructor.newInstance(null,location("tacz_resources"),metadata,List.of(childA,childB));
        var tv=GeneratedServerPackCustody.inspectTacz(tacz,Path.of(args[0]),deadline);
        var id=ResourceLocation.parse("demo:worldgen/noise/test.json");
        if(!text(tacz.getResource(PackType.SERVER_DATA,id)).equals("first native child")
            ||!text(tv.children.get(1).getResource(PackType.SERVER_DATA,id)).equals("masked native child"))
            throw new AssertionError("Native first-readable override or masked child lost");
        if(tacz.getRootResource("pack.mcmeta")!=null||!tv.metadata.contains("native fixture metadata"))
            throw new AssertionError("Synthetic native metadata not preserved separately from absent raw root");
        tv.unchanged();
        Field delegates=anonymous.getSuperclass().getDeclaredField("delegates");delegates.setAccessible(true);
        Object ordered=delegates.get(tacz);delegates.set(tacz,List.of(childB,childA));
        expectFailure(tv::unchanged,"changed native child order");delegates.set(tacz,ordered);tv.unchanged();
        Field packMeta=anonymous.getSuperclass().getDeclaredField("packMeta");packMeta.setAccessible(true);
        packMeta.set(tacz,new PackMetadataSection(Component.literal("changed metadata"),48,Optional.empty()));
        expectFailure(tv::unchanged,"changed synthetic metadata");packMeta.set(tacz,metadata);tv.unchanged();

        Class<?> runtimeType=Class.forName(GeneratedServerPackCustody.RUNTIME);
        Field unsafeField=sun.misc.Unsafe.class.getDeclaredField("theUnsafe");unsafeField.setAccessible(true);
        Object runtime=((sun.misc.Unsafe)unsafeField.get(null)).allocateInstance(runtimeType);
        Path virtual=root.resolve("virtual-root");
        IModFile file=(IModFile)Proxy.newProxyInstance(IModFile.class.getClassLoader(),new Class<?>[]{IModFile.class},(proxy,method,values)->{
            if(method.getName().equals("findResource")){
                Path selected=virtual;for(String segment:(String[])values[0])selected=selected.resolve(segment);return selected;
            }
            if(method.getName().equals("getFilePath"))return virtual;
            if(method.getName().equals("toString"))return "owned native API fixture";
            throw new UnsupportedOperationException("Unexpected fixture native method "+method.getName());
        });
        var storage=new ConcurrentHashMap<Path,IoSupplier<java.io.InputStream>>();
        byte[] bytes="native generated recipe".getBytes(StandardCharsets.UTF_8);
        storage.put(virtual.resolve("data/demo/recipe/a.json"),()->new ByteArrayInputStream(bytes));
        storage.put(virtual.resolve("data/demo/invalid name.json"),()->new ByteArrayInputStream(new byte[]{7}));
        storage.put(virtual.resolve("pack.mcmeta"),()->new ByteArrayInputStream(new byte[]{8}));
        for(Field field:runtimeType.getDeclaredFields()) {
            if(java.lang.reflect.Modifier.isStatic(field.getModifiers()))continue;
            field.setAccessible(true);
            if(field.getName().equals("resources"))field.set(runtime,storage);
            else if(field.getName().equals("file"))field.set(runtime,file);
            else if(field.getName().equals("type"))field.set(runtime,PackType.SERVER_DATA);
            else if(field.getType()==PackLocationInfo.class)field.set(runtime,location("create_dragons_plus:runtime"));
            else if(field.getType()==PackMetadataSection.class)field.set(runtime,metadata);
        }
        var view=GeneratedServerPackCustody.inspectRuntime((PackResources)runtime,Path.of(args[1]),deadline);
        if(view.raw().size()!=3||view.ids().size()!=1)throw new AssertionError("Invalid/raw/root native members were dropped from custody");
        Class<?> accumulatorType=Class.forName("worldfortwo.bridge.LithostitchedSeedgenResources$Accumulator");
        var ac=accumulatorType.getDeclaredConstructor();ac.setAccessible(true);Object accumulator=ac.newInstance();
        var inventory=LithostitchedSeedgenResources.class.getDeclaredMethod("runtimeInventory",GeneratedServerPackCustody.RuntimeView.class,accumulatorType,TreeSet.class);inventory.setAccessible(true);
        var unchanged=LithostitchedSeedgenResources.class.getDeclaredMethod("runtimeUnchanged",GeneratedServerPackCustody.RuntimeView.class,accumulatorType);unchanged.setAccessible(true);
        var ids=new TreeSet<ResourceLocation>();inventory.invoke(null,view,accumulator,ids);unchanged.invoke(null,view,accumulator);
        if(!ids.equals(view.ids()))throw new AssertionError("Runtime native inventory incomplete");
        bytes[0]^=1;
        expectFailure(()->unchanged.invoke(null,view,accumulator),"same-supplier generated bytes changed");bytes[0]^=1;
        unchanged.invoke(null,view,accumulator);
        storage.put(virtual.resolve("data/demo/recipe/later.json"),()->new ByteArrayInputStream(new byte[]{9}));
        expectFailure(view::unchanged,"runtime list/map changed");
        childA.close();childB.close();
        System.out.println("PROBE_RESULT {\"actual_native_tacz_first_child\":true,\"masked_child_retained\":true,\"ordered_child_change_refused\":true,\"synthetic_metadata_change_refused\":true,\"native_runtime_list_get_map_agree\":true,\"all_raw_including_invalid_and_root\":3,\"same_supplier_byte_change_refused\":true,\"runtime_map_change_refused\":true,\"world_started\":false}");
    }
    private static PackLocationInfo location(String id){return new PackLocationInfo(id,Component.literal(id),PackSource.BUILT_IN,Optional.empty());}
    private static String text(IoSupplier<java.io.InputStream> supplier)throws Exception {
        if(supplier==null)throw new AssertionError("Native supplier absent");
        try(var input=supplier.get()){return new String(input.readAllBytes(),StandardCharsets.UTF_8);}
    }
    @FunctionalInterface private interface Checked {void run()throws Exception;}
    private static void expectFailure(Checked operation,String description)throws Exception {
        try{operation.run();throw new AssertionError("Accepted "+description);}
        catch(java.io.IOException expected){}
        catch(InvocationTargetException expected){if(!(expected.getCause() instanceof java.io.IOException))throw expected;}
    }
}
