package worldfortwo.bridge;

import com.mojang.serialization.Lifecycle;
import java.nio.file.Path;
import java.nio.file.Files;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.zip.ZipFile;
import net.minecraft.core.Holder;
import net.minecraft.core.MappedRegistry;
import net.minecraft.core.Registry;
import net.minecraft.core.RegistryAccess;
import net.minecraft.core.registries.Registries;
import net.minecraft.data.registries.VanillaRegistries;
import net.minecraft.resources.ResourceKey;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.level.biome.Biomes;
import net.minecraft.world.level.biome.FixedBiomeSource;
import net.minecraft.world.level.dimension.BuiltinDimensionTypes;
import net.minecraft.world.level.dimension.LevelStem;
import net.minecraft.world.level.levelgen.DensityFunction;
import net.minecraft.world.level.levelgen.DensityFunctions;
import net.minecraft.world.level.levelgen.NoiseBasedChunkGenerator;
import net.minecraft.world.level.levelgen.NoiseGeneratorSettings;
import net.minecraft.world.level.levelgen.NoiseRouter;
import net.minecraft.world.level.levelgen.presets.WorldPreset;
import net.minecraft.world.level.levelgen.presets.WorldPresets;
import org.objectweb.asm.ClassReader;
import org.objectweb.asm.Opcodes;
import org.objectweb.asm.tree.ClassNode;
import org.objectweb.asm.tree.MethodInsnNode;
import org.objectweb.asm.tree.MethodNode;
import org.objectweb.asm.tree.FieldInsnNode;

/** Offline native API/registry contract only. No ModList, MinecraftServer or world is fabricated. */
public final class LithostitchedSeedgenProbe {
    public static void main(String[] args)throws Exception {
        tables(Path.of(args[0]),Path.of(args[1]));
        net.minecraft.SharedConstants.tryDetectVersion();
        net.minecraft.server.Bootstrap.bootStrap();
        currentDimensions();router();resources();scope();lifecycle();packetLifecycle();nativeHandles();surfaceCodecSemantics();
        System.out.println("PASS offline current normal dimensions, exact holder custody, explicit custom retention and all15 router fields");
        System.out.println("Native modifier/injector execution, transformed mixin gates, authenticated seed publication and strict paired acceptance NOT RUN");
    }
    static ClassNode read(Path jar,String name)throws Exception {
        try(ZipFile zip=new ZipFile(jar.toFile())){
            ClassNode value=new ClassNode();new ClassReader(zip.getInputStream(zip.getEntry(name+".class"))).accept(value,0);return value;
        }
    }
    static MethodNode method(ClassNode type,String name,String descriptor) {
        var selected=type.methods.stream().filter(m->m.name.equals(name)&&m.desc.equals(descriptor)).toList();
        if(selected.size()!=1)throw new AssertionError("Pinned native descriptor differs: "+type.name+"."+name+descriptor);
        return selected.getFirst();
    }
    static void tables(Path litho,Path seedgen)throws Exception {
        String core="dev/worldgen/lithostitched/",reg="Lnet/minecraft/core/RegistryAccess;",stems="Lnet/minecraft/core/Registry;";
        var main=method(read(litho,core+"impl/LithostitchedInternalHooks"),"applyModifiersAndInjections","("+reg+stems+"J)V");
        var phase=new ArrayList<String>();
        for(var instruction:main.instructions)if(instruction instanceof MethodInsnNode call){
            if(call.name.equals("applyModifiers")||call.name.equals("applySurfaceRules")||call.name.equals("applyBiomeInjectors")||call.name.equals("bind"))phase.add(call.name);
        }
        if(!phase.equals(List.of("applyModifiers","applySurfaceRules","applyBiomeInjectors","bind")))throw new AssertionError("Native seeded phase order changed");
        method(read(litho,core+"impl/worldgen/modifier/ModifierManager"),"applyModifiers","("+reg+stems+")V");
        method(read(litho,core+"worldgen/surface/SurfaceRuleManager"),"applySurfaceRules","("+reg+stems+")V");
        var chunk=read(litho,core+"mixin/common/ChunkMapMixin");
        var wrapper=chunk.methods.stream().filter(m->m.name.equals("wrapNoiseRouter")).findFirst().orElseThrow();
        int wraps=0,setters=0;
        for(var instruction:wrapper.instructions)if(instruction instanceof MethodInsnNode call){
            if(call.name.equals("modifyDensityFunction"))wraps++;
            if(call.name.equals("setNoiseRouter"))setters++;
        }
        if(wraps!=15||setters!=1)throw new AssertionError("Native ChunkMap router hook changed");
        var access=read(seedgen,"mobius/seedrenderer/dh/ClientWorldgen");
        for(String name:List.of("loaded","stems","dataPackNames")){
            var field=access.fields.stream().filter(f->f.name.equals(name)).findFirst().orElseThrow();
            if((field.access&(Opcodes.ACC_STATIC|Opcodes.ACC_VOLATILE))!=(Opcodes.ACC_STATIC|Opcodes.ACC_VOLATILE))throw new AssertionError("Native cache publication flags changed");
        }
        var attempt=method(access,"attempt","(ZZ)Lnet/minecraft/core/RegistryAccess$Frozen;");
        if((attempt.access&(Opcodes.ACC_STATIC|Opcodes.ACC_PRIVATE))!=(Opcodes.ACC_STATIC|Opcodes.ACC_PRIVATE))throw new AssertionError("Native attempt access changed");
        int stemWrites=0,stemReads=0,nameWrites=0;
        for(var instruction:attempt.instructions)if(instruction instanceof FieldInsnNode field&&field.owner.equals(access.name)) {
            if(field.name.equals("stems")&&field.getOpcode()==Opcodes.PUTSTATIC)stemWrites++;
            if(field.name.equals("stems")&&field.getOpcode()==Opcodes.GETSTATIC)stemReads++;
            if(field.name.equals("dataPackNames")&&field.getOpcode()==Opcodes.PUTSTATIC)nameWrites++;
            if(field.name.equals("loaded")&&field.getOpcode()==Opcodes.PUTSTATIC)throw new AssertionError("Native attempt now writes the loaded registry");
        }
        if(stemWrites!=1||stemReads!=1||nameWrites!=1)throw new AssertionError("Scoped cache redirect topology changed");
        method(read(seedgen,"mobius/seedrenderer/dh/ClientTerrain"),"queueFor","(Lnet/minecraft/client/multiplayer/ClientLevel;)Lmobius/seedrenderer/dh/SeedRetrievalQueue;");
        var onWorld=method(read(seedgen,"mobius/seedrenderer/net/SeedSharing"),"onWorld","(Lmobius/seedrenderer/net/SeedShare$World;)V");
        int builds=0;
        for(var instruction:onWorld.instructions)if(instruction instanceof MethodInsnNode call&&call.owner.equals("mobius/seedrenderer/dh/WorldBasis")&&call.name.equals("fromSeed"))builds++;
        if(builds!=1)throw new AssertionError("Authenticated native basis call topology changed");
        method(read(seedgen,"mobius/seedrenderer/dh/WorldBasis"),"fromSeed","(Lnet/minecraft/resources/ResourceKey;JLnet/minecraft/resources/ResourceLocation;)Lmobius/seedrenderer/dh/WorldBasis;");
        var payload=method(read(seedgen,"mobius/seedrenderer/neoforge/SeedGenNeoForge"),"lambda$onRegisterPayloads$0",
            "(Lmobius/seedrenderer/neoforge/SeedGenPayloads$SharedWorld;Lnet/neoforged/neoforge/network/handling/IPayloadContext;)V");
        int offers=0,contextReads=0;
        for(var instruction:payload.instructions) {
            if(instruction instanceof MethodInsnNode call&&call.owner.equals("mobius/seedrenderer/net/SeedSharing")&&call.name.equals("onWorld"))offers++;
            if(instruction instanceof org.objectweb.asm.tree.VarInsnNode variable&&variable.var==1&&variable.getOpcode()==Opcodes.ALOAD)contextReads++;
        }
        if(offers!=1||contextReads!=0)throw new AssertionError("Pinned native payload context/dispatch topology changed");
        var fast=method(read(litho,core+"api/worldgen/densityfunction/fastnoise/FastNoiseConfig"),"bind","(J)V");
        int nativeSeedSetters=0;
        for(var instruction:fast.instructions)if(instruction instanceof MethodInsnNode call&&call.owner.endsWith("/FNL")&&call.name.equals("SetSeed")&&call.desc.equals("(I)V"))nativeSeedSetters++;
        if(nativeSeedSetters!=1)throw new AssertionError("Pinned native FastNoise actual-seed binding changed");
        System.out.println("PASS installed bytecode: modifier/surface/injector/fast-noise order,15 router calls, exact private native attempt and volatile cache fields, one authenticated basis call");
    }
    static void currentDimensions() {
        var vanilla=VanillaRegistries.createLookup();
        var noise=new MappedRegistry<NoiseGeneratorSettings>(Registries.NOISE_SETTINGS,Lifecycle.stable());
        var entries=new LinkedHashMap<ResourceKey<LevelStem>,LevelStem>();
        var names=List.of(LevelStem.OVERWORLD,LevelStem.NETHER,LevelStem.END);
        var settings=List.of(NoiseGeneratorSettings.OVERWORLD,NoiseGeneratorSettings.NETHER,NoiseGeneratorSettings.END);
        var types=List.of(BuiltinDimensionTypes.OVERWORLD,BuiltinDimensionTypes.NETHER,BuiltinDimensionTypes.END);
        var biomes=List.of(Biomes.PLAINS,Biomes.NETHER_WASTES,Biomes.END_HIGHLANDS);
        for(int n=0;n<3;n++){
            var holder=Registry.registerForHolder(noise,settings.get(n),vanilla.lookupOrThrow(Registries.NOISE_SETTINGS).getOrThrow(settings.get(n)).value());
            var generator=new NoiseBasedChunkGenerator(new FixedBiomeSource(vanilla.lookupOrThrow(Registries.BIOME).getOrThrow(biomes.get(n))),holder);
            entries.put(names.get(n),new LevelStem(vanilla.lookupOrThrow(Registries.DIMENSION_TYPE).getOrThrow(types.get(n)),generator));
        }
        var presets=new MappedRegistry<WorldPreset>(Registries.WORLD_PRESET,Lifecycle.stable());
        Registry.register(presets,WorldPresets.NORMAL,new WorldPreset(entries));
        var actual=new RegistryAccess.ImmutableRegistryAccess(List.of(noise,presets)).freeze();
        var empty=new MappedRegistry<LevelStem>(Registries.LEVEL_STEM,Lifecycle.stable());empty.freeze();
        Registry<LevelStem> selected=LithostitchedSeedgenCompat.selectDimensions(actual,empty);
        if(selected.size()!=3||actual.registry(Registries.LEVEL_STEM).isPresent())throw new AssertionError("Empty definitions did not use native current normal bake");
        for(var entry:entries.entrySet())if(selected.get(entry.getKey())!=entry.getValue())throw new AssertionError("Current preset dimension object was copied/rebound");
        var view=LithostitchedSeedgenCompat.withDimensions(actual,selected);
        if(view.registryOrThrow(Registries.NOISE_SETTINGS)!=noise||view.registryOrThrow(Registries.WORLD_PRESET)!=presets
                ||view.registryOrThrow(Registries.LEVEL_STEM)!=selected)throw new AssertionError("Delegating registry view replaced unrelated objects");
        var custom=new MappedRegistry<LevelStem>(Registries.LEVEL_STEM,Lifecycle.stable());
        var customKey=ResourceKey.create(Registries.LEVEL_STEM,ResourceLocation.parse("fixture:custom"));
        var overworld=entries.get(LevelStem.OVERWORLD);
        var customStem=new LevelStem(overworld.type(),new NoiseBasedChunkGenerator(overworld.generator().getBiomeSource(),noise.getHolderOrThrow(NoiseGeneratorSettings.OVERWORLD)));
        Registry.register(custom,customKey,customStem);custom.freeze();
        if(LithostitchedSeedgenCompat.selectDimensions(actual,custom).get(customKey)!=customStem)throw new AssertionError("Explicit custom dimension lost");
        var stale=new MappedRegistry<NoiseGeneratorSettings>(Registries.NOISE_SETTINGS,Lifecycle.stable());
        var foreign=Registry.registerForHolder(stale,NoiseGeneratorSettings.OVERWORLD,noise.get(NoiseGeneratorSettings.OVERWORLD));stale.freeze();
        var bad=new MappedRegistry<LevelStem>(Registries.LEVEL_STEM,Lifecycle.stable());
        var old=entries.get(LevelStem.OVERWORLD);
        Registry.register(bad,LevelStem.OVERWORLD,new LevelStem(old.type(),new NoiseBasedChunkGenerator(old.generator().getBiomeSource(),foreign)));bad.freeze();
        try{LithostitchedSeedgenCompat.selectDimensions(actual,bad);throw new AssertionError("Stale dimension holder admitted");}
        catch(IllegalStateException expected){if(!expected.getMessage().contains("current private load"))throw expected;}
        var direct=new MappedRegistry<LevelStem>(Registries.LEVEL_STEM,Lifecycle.stable());
        Registry.register(direct,LevelStem.OVERWORLD,new LevelStem(old.type(),new NoiseBasedChunkGenerator(old.generator().getBiomeSource(),Holder.direct(foreign.value()))));direct.freeze();
        try{LithostitchedSeedgenCompat.selectDimensions(actual,direct);throw new AssertionError("Unregistered dimension holder admitted");}
        catch(IllegalStateException expected){if(!expected.getMessage().contains("current private load"))throw expected;}
    }
    static void router() {
        DensityFunction[] f=new DensityFunction[15];for(int n=0;n<f.length;n++)f[n]=DensityFunctions.constant((n+1)/10.0);
        var original=new NoiseRouter(f[0],f[1],f[2],f[3],f[4],f[5],f[6],f[7],f[8],f[9],f[10],f[11],f[12],f[13],f[14]);
        int[] count={0};
        var mapped=LithostitchedSeedgenCompat.mapRouter(original,(index,value)->{
            if(value!=f[index]||index!=count[0]++)throw new AssertionError("Router component order changed");
            return index==1?DensityFunctions.add(value,DensityFunctions.constant(.25)):value;
        });
        if(count[0]!=15||mapped.fluidLevelFloodednessNoise()==original.fluidLevelFloodednessNoise())throw new AssertionError("Floodedness not mapped");
        try{
            for(var component:NoiseRouter.class.getRecordComponents())if(!component.getName().equals("fluidLevelFloodednessNoise")
                    &&component.getAccessor().invoke(original)!=component.getAccessor().invoke(mapped))throw new AssertionError("Unrelated/HA-modified router field replaced");
        }catch(ReflectiveOperationException error){throw new AssertionError(error);}
    }
    static void scope() {
        var stems=new MappedRegistry<LevelStem>(Registries.LEVEL_STEM,Lifecycle.stable());stems.freeze();
        for(boolean fail:List.of(false,true)) {
            try(var scope=LithostitchedSeedgenLoadScope.enter()) {
                LithostitchedSeedgenLoadScope.writeNames(List.of("same-filename.zip"));
                LithostitchedSeedgenLoadScope.writeStems(stems);
                if(LithostitchedSeedgenLoadScope.readStems()!=stems||scope.stems()!=stems)throw new AssertionError("Native scope lost exact current stems");
                if(fail)throw new IllegalArgumentException("fixture failure");
            }catch(IllegalArgumentException expected){if(!fail)throw expected;}
            try{LithostitchedSeedgenLoadScope.current();throw new AssertionError("Attempt scope leaked after return/throw");}
            catch(IllegalStateException expected){}
        }
        try(var scope=LithostitchedSeedgenLoadScope.enter()) {
            try{scope.requireComplete();throw new AssertionError("Partial cache admitted");}catch(IllegalStateException expected){}
            try{LithostitchedSeedgenLoadScope.readStems();throw new AssertionError("Old static read admitted");}catch(IllegalStateException expected){}
            try{LithostitchedSeedgenLoadScope.enter();throw new AssertionError("Reentrant scope admitted");}catch(IllegalStateException expected){}
            var names=new ArrayList<>(List.of("original.zip"));LithostitchedSeedgenLoadScope.writeNames(names);LithostitchedSeedgenLoadScope.writeStems(stems);
            names.set(0,"mutated.zip");
            if(!scope.names().equals(List.of("original.zip")))throw new AssertionError("Native pack-name metadata was not captured immutably");
            try{LithostitchedSeedgenLoadScope.writeNames(List.of("again.zip"));throw new AssertionError("Repeated native name write admitted");}catch(IllegalStateException expected){}
            try{LithostitchedSeedgenLoadScope.writeStems(stems);throw new AssertionError("Repeated native stem write admitted");}catch(IllegalStateException expected){}
        }
        System.out.println("PASS scoped native metadata custody/throw cleanup and exact one-write/one-read installed topology; native transformed redirects still pending");
    }
    static void resources()throws Exception {
        Path a=Path.of("resource-a"),b=Path.of("resource-b");
        Files.createDirectories(a.resolve("data/fixture/lithostitched/biome_injector"));
        Files.createDirectories(b.resolve("data/fixture/lithostitched/biome_injector"));
        String meta="{\"pack\":{\"pack_format\":48,\"description\":\"offline custody\"}}";
        Files.writeString(a.resolve("pack.mcmeta"),meta);Files.writeString(b.resolve("pack.mcmeta"),meta);
        Path ar=a.resolve("data/fixture/lithostitched/biome_injector/ocean.json"),br=b.resolve("data/fixture/lithostitched/biome_injector/ocean.json");
        Files.writeString(ar,"{\"threshold\":0.4}");Files.writeString(br,"{\"threshold\":0.7}");
        var first=pathPack(a,"same-filename");var second=pathPack(b,"override");
        var initial=attest(List.of(first,second));
        if(initial.bytes()<Files.size(ar)+Files.size(br)||initial.entries()<6)throw new AssertionError("Path-backed resources silently omitted");
        Files.writeString(ar,"{\"threshold\":0.5}");
        if(initial.equals(attest(List.of(first,second))))throw new AssertionError("Same-ID injector content change admitted");
        var unchanged=attest(List.of(first,second));
        if(!unchanged.equals(attest(List.of(first,second))))throw new AssertionError("Identical native inventory is nondeterministic");
        if(unchanged.equals(attest(List.of(second,first))))throw new AssertionError("Override stack order change admitted");
        Files.writeString(a.resolve("pack.mcmeta"),"{\"pack\":{\"pack_format\":48,\"description\":\"changed\"},\"filter\":{\"block\":[{\"namespace\":\"fixture\"}]}}");
        if(unchanged.equals(attest(List.of(first,second))))throw new AssertionError("Root filter metadata change admitted");
        Files.writeString(a.resolve("pack.mcmeta"),meta);
        var composite=new net.minecraft.server.packs.CompositePackResources(first,List.of(second));
        var overlaid=attest(List.of(composite));
        try(var stream=composite.getResource(net.minecraft.server.packs.PackType.SERVER_DATA,ResourceLocation.parse("fixture:lithostitched/biome_injector/ocean.json")).get()) {
            if(!new String(stream.readAllBytes(),StandardCharsets.UTF_8).equals("{\"threshold\":0.7}"))throw new AssertionError("Fixture did not actually mask primary content");
        }
        Files.writeString(ar,"{\"threshold\":0.6}");
        if(overlaid.equals(attest(List.of(composite))))throw new AssertionError("Fully masked composite child-byte change admitted");
        var unknown=new net.minecraft.server.packs.PathPackResources(first.location(),a){};
        refusedResources(List.of(unknown),"Unsupported actual PackResources implementation");
        Path broken=Path.of("resource-not-a-directory");Files.createDirectory(broken);Files.writeString(broken.resolve("data"),"not a directory");
        refusedResources(List.of(pathPack(broken,"invalid-native-data-root")),"not a regular directory");
        fileResources(meta);
        System.out.println("PASS actual native Path/File/Composite resources: nonempty roots, same-ID and masked-child byte changes, order/filter metadata, unknown subclass, invalid root, corrupt ZIP and finite member cap");
    }
    static void fileResources(String meta)throws Exception {
        Path zip=Path.of("resource.zip");
        try(var stream=new java.util.zip.ZipOutputStream(Files.newOutputStream(zip))) {
            zipMember(stream,"pack.mcmeta",meta.getBytes(StandardCharsets.UTF_8));
            zipMember(stream,"data/fixture/lithostitched/biome_injector/ocean.json","{\"threshold\":0.8}".getBytes(StandardCharsets.UTF_8));
            zipMember(stream,"overlay/data/fixture/lithostitched/biome_injector/ocean.json","{\"threshold\":0.9}".getBytes(StandardCharsets.UTF_8));
        }
        var info=new net.minecraft.server.packs.PackLocationInfo("native-zip",net.minecraft.network.chat.Component.literal("native-zip"),net.minecraft.server.packs.repository.PackSource.DEFAULT,java.util.Optional.empty());
        var supplier=new net.minecraft.server.packs.FilePackResources.FileResourcesSupplier(zip);
        try(var opened=supplier.openPrimary(info)) {
            var result=attest(List.of(opened));
            if(result.bytes()<meta.length()+17||result.entries()<3)throw new AssertionError("Native ZIP data omitted");
        }
        Path invalid=Path.of("resource-corrupt.zip");Files.writeString(invalid,"not a zip");
        var invalidPack=new net.minecraft.server.packs.FilePackResources.FileResourcesSupplier(invalid).openPrimary(info);
        refusedResources(List.of(invalidPack),"unavailable");
        Path large=Path.of("resource-bounded.zip");
        try(var stream=new java.util.zip.ZipOutputStream(Files.newOutputStream(large))) {
            zipMember(stream,"pack.mcmeta",meta.getBytes(StandardCharsets.UTF_8));
            stream.putNextEntry(new java.util.zip.ZipEntry("data/fixture/large.bin"));
            byte[] zero=new byte[65536];for(int n=0;n<513;n++)stream.write(zero);stream.closeEntry();
        }
        var largePack=new net.minecraft.server.packs.FilePackResources.FileResourcesSupplier(large).openPrimary(info);
        refusedResources(List.of(largePack),"byte attestation exceeded");
    }
    static void zipMember(java.util.zip.ZipOutputStream output,String name,byte[] content)throws Exception {
        output.putNextEntry(new java.util.zip.ZipEntry(name));output.write(content);output.closeEntry();
    }
    static void refusedResources(List<net.minecraft.server.packs.PackResources> packs,String message)throws Exception {
        try{attest(packs);throw new AssertionError("Untrusted resource custody admitted: "+message);}
        catch(java.io.IOException expected){if(!expected.getMessage().contains(message))throw expected;}
    }
    static net.minecraft.server.packs.PathPackResources pathPack(Path root,String id) {
        return new net.minecraft.server.packs.PathPackResources(new net.minecraft.server.packs.PackLocationInfo(id,net.minecraft.network.chat.Component.literal(id),net.minecraft.server.packs.repository.PackSource.DEFAULT,java.util.Optional.empty()),root);
    }
    static LithostitchedSeedgenResources.Attestation attest(List<net.minecraft.server.packs.PackResources> packs)throws Exception {
        // Native manager closes only no-op PathPackResources in this fixture.
        try(var manager=new net.minecraft.server.packs.resources.MultiPackResourceManager(net.minecraft.server.packs.PackType.SERVER_DATA,packs)) {
            return LithostitchedSeedgenResources.capture(packs,manager);
        }
    }
    static void lifecycle()throws Exception {
        var gate=new LithostitchedSeedgenConnectionGate();
        gate.prepare(41,0,false);gate.open(41,41);
        var queues=new java.util.concurrent.ConcurrentHashMap<String,String>();
        var entered=new java.util.concurrent.CountDownLatch(1);var release=new java.util.concurrent.CountDownLatch(1);
        var cleaned=new java.util.concurrent.atomic.AtomicBoolean();var error=new java.util.concurrent.atomic.AtomicReference<Throwable>();
        Thread reader=new Thread(()->{
            try {gate.admit(()->41,()->{entered.countDown();await(release);queues.put("old-basis","old-queue");return "queue";});}
            catch(Throwable failure){error.set(failure);}
        },"offline-old-basis-reader");reader.setDaemon(true);reader.start();
        if(!entered.await(2,java.util.concurrent.TimeUnit.SECONDS))throw new AssertionError("Race reader did not enter");
        Thread logout=new Thread(()->{try{gate.logout(()->{queues.clear();cleaned.set(true);return List.of();});}catch(Throwable failure){error.set(failure);}},"offline-logout");
        logout.setDaemon(true);logout.start();
        long until=System.nanoTime()+java.util.concurrent.TimeUnit.SECONDS.toNanos(2);
        while(logout.getState()!=Thread.State.BLOCKED&&!cleaned.get()&&System.nanoTime()-until<0)Thread.onSpinWait();
        try {
            if(logout.getState()!=Thread.State.BLOCKED||cleaned.get())throw new AssertionError("Logout did not wait for whole captured-basis operation");
        }finally{release.countDown();}
        reader.join(2000);logout.join(2000);
        if(reader.isAlive()||logout.isAlive()||error.get()!=null||!queues.isEmpty())throw new AssertionError("Old basis repopulated a logged-out queue map",error.get());
        if(gate.admit(()->41,()->{queues.put("late","queue");return "bad";})!=null||!queues.isEmpty())throw new AssertionError("Post-logout admission remained open");
        gate.prepare(41,41,false);gate.open(41,41);gate.requirePermit(41,41,false);
        try{gate.prepare(42,41,false);throw new AssertionError("Different process seed admitted");}catch(IllegalStateException expected){}
        if(!gate.failed())throw new AssertionError("Different seed refusal was not sticky");
        var changed=new LithostitchedSeedgenConnectionGate();changed.prepare(41,0,false);changed.open(41,41);changed.logout(List::of);
        try{changed.prepare(41,99,false);throw new AssertionError("Integrated/foreign global seed change admitted");}catch(IllegalStateException expected){}
        var firstForeign=new LithostitchedSeedgenConnectionGate();
        try{firstForeign.prepare(41,99,false);throw new AssertionError("First remote overwrote a foreign native seed");}catch(IllegalStateException expected){}
        var time=new java.util.concurrent.atomic.AtomicLong();var stubbornGate=new LithostitchedSeedgenConnectionGate(time::get);
        stubbornGate.prepare(41,0,false);stubbornGate.open(41,41);
        var running=new java.util.concurrent.CountDownLatch(1);var finish=new java.util.concurrent.CountDownLatch(1);
        var executor=java.util.concurrent.Executors.newSingleThreadExecutor(task->{Thread thread=new Thread(task,"offline-stubborn-queue");thread.setDaemon(true);return thread;});
        executor.submit(()->{running.countDown();while(finish.getCount()!=0)try{finish.await();}catch(InterruptedException ignored){}});
        if(!running.await(2,java.util.concurrent.TimeUnit.SECONDS))throw new AssertionError("Owned executor did not start");
        try {
            stubbornGate.logout(()->{executor.shutdownNow();return List.of(executor);});
            if(executor.isTerminated())throw new AssertionError("Fixture executor unexpectedly terminated");
            try{stubbornGate.requireReady();throw new AssertionError("shutdownNow was treated as terminated");}catch(IllegalStateException expected){}
            time.set(java.util.concurrent.TimeUnit.SECONDS.toNanos(29));
            stubbornGate.logout(List::of);
            time.set(java.util.concurrent.TimeUnit.SECONDS.toNanos(31));stubbornGate.poll();
            if(!stubbornGate.failed())throw new AssertionError("Unterminated owned worker timeout was not sticky");
        }finally{finish.countDown();executor.shutdownNow();if(!executor.awaitTermination(2,java.util.concurrent.TimeUnit.SECONDS))throw new AssertionError("Offline fixture failed to release owned thread");}
        try{stubbornGate.prepare(41,41,false);throw new AssertionError("Timeout was hidden after late termination");}catch(IllegalStateException expected){}
        System.out.println("PASS original lifecycle policy: whole-operation logout race, same-seed reconnect, persistent different-seed/global-seed refusal, actual executor termination and sticky timeout; external DH drain not claimed");
    }
    static void await(java.util.concurrent.CountDownLatch latch) {
        try{if(!latch.await(2,java.util.concurrent.TimeUnit.SECONDS))throw new AssertionError("Offline race deadline");}
        catch(InterruptedException failure){Thread.currentThread().interrupt();throw new AssertionError(failure);}
    }
    static void packetLifecycle()throws Exception {
        var gate=new LithostitchedSeedgenConnectionGate();Object old=new Object(),current=new Object();
        var shared=new java.util.concurrent.ConcurrentHashMap<String,String>();var calls=new java.util.concurrent.atomic.AtomicInteger();
        gate.prepare(41,0,false);gate.open(41,41);gate.logout(()->{shared.clear();return List.of();});
        gate.packet(old,null,false,()->{calls.incrementAndGet();shared.put("late","bad");return null;});
        gate.packet(old,current,true,()->{calls.incrementAndGet();shared.put("old-connection","bad");return null;});
        gate.packet(current,current,false,()->{calls.incrementAndGet();return null;});
        if(calls.get()!=0||!shared.isEmpty()||gate.failed())throw new AssertionError("Stale/dead packet reopened state or poisoned a new connection");
        gate.prepare(41,41,false);gate.open(41,41);
        var basisReady=new java.util.concurrent.CountDownLatch(1);var releasePut=new java.util.concurrent.CountDownLatch(1);
        var cleaned=new java.util.concurrent.atomic.AtomicBoolean();var error=new java.util.concurrent.atomic.AtomicReference<Throwable>();
        Thread offer=new Thread(()->{try{gate.packet(current,current,true,()->{basisReady.countDown();await(releasePut);shared.put("original-onWorld-put","basis");return null;});}catch(Throwable failure){error.set(failure);}},"offline-packet-body");
        offer.setDaemon(true);offer.start();
        if(!basisReady.await(2,java.util.concurrent.TimeUnit.SECONDS))throw new AssertionError("Original packet body did not reach post-basis gap");
        Thread logout=new Thread(()->{try{gate.logout(()->{shared.clear();cleaned.set(true);return List.of();});}catch(Throwable failure){error.set(failure);}},"offline-packet-logout");
        logout.setDaemon(true);logout.start();
        long until=System.nanoTime()+java.util.concurrent.TimeUnit.SECONDS.toNanos(2);
        while(logout.getState()!=Thread.State.BLOCKED&&!cleaned.get()&&System.nanoTime()-until<0)Thread.onSpinWait();
        try{if(logout.getState()!=Thread.State.BLOCKED||cleaned.get())throw new AssertionError("Logout did not cover original post-fromSeed SHARED.put");}
        finally{releasePut.countDown();}
        offer.join(2000);logout.join(2000);
        if(offer.isAlive()||logout.isAlive()||error.get()!=null||!shared.isEmpty()||!cleaned.get())throw new AssertionError("Original onWorld put escaped logout custody",error.get());
        System.out.println("PASS original packet lifecycle: stale/dead/current listener identity and whole-onWorld post-basis put/logout race; actual native payload mixin still pending");
    }
    static void nativeHandles()throws Exception {
        // Construct the actual production typed handle table, never invoke its
        // client singleton, cache getters, native attempt or network methods.
        Class<?> type=Class.forName("worldfortwo.bridge.LithostitchedSeedgenCompat$ClientAccess",false,LithostitchedSeedgenProbe.class.getClassLoader());
        try {
            Object table=java.lang.invoke.MethodHandles.privateLookupIn(type,java.lang.invoke.MethodHandles.lookup())
                .findConstructor(type,java.lang.invoke.MethodType.methodType(void.class)).invoke();
            if(table==null)throw new AssertionError("Native symbol table was not created");
        }catch(Throwable failure){if(failure instanceof Error error)throw error;throw new Exception("Exact installed native typed handles failed",failure);}
        System.out.println("PASS actual installed typed MethodHandle/VarHandle resolution for cache, private attempt/queues, worker, Minecraft listener/thread and Connection liveness; no handle invoked, native union loader pending");
    }
    @SuppressWarnings("unchecked")
    static void surfaceCodecSemantics()throws Exception {
        var original=net.minecraft.world.level.levelgen.SurfaceRules.state(net.minecraft.world.level.block.Blocks.STONE.defaultBlockState());
        var a=new dev.worldgen.lithostitched.impl.worldgen.surface.rule.TransientMergedRule(List.of(net.minecraft.world.level.levelgen.SurfaceRules.state(net.minecraft.world.level.block.Blocks.DIRT.defaultBlockState())),original);
        var b=new dev.worldgen.lithostitched.impl.worldgen.surface.rule.TransientMergedRule(List.of(net.minecraft.world.level.levelgen.SurfaceRules.state(net.minecraft.world.level.block.Blocks.GRAVEL.defaultBlockState())),original);
        var codec=dev.worldgen.lithostitched.impl.worldgen.surface.rule.TransientMergedRule.CODEC.codec();
        var encodedA=codec.encodeStart(com.mojang.serialization.JsonOps.INSTANCE,a).getOrThrow();
        var encodedB=codec.encodeStart(com.mojang.serialization.JsonOps.INSTANCE,b).getOrThrow();
        if(!encodedA.equals(encodedB)||!encodedA.getAsJsonObject().has("original_source"))throw new AssertionError("Pinned native merged-surface codec semantics changed");
        Object ruleA=((java.util.function.Function<Object,Object>)(Object)a).apply(null);
        Object ruleB=((java.util.function.Function<Object,Object>)(Object)b).apply(null);
        try {
            Class<?> rule=Class.forName("net.minecraft.world.level.levelgen.SurfaceRules$SurfaceRule");
            var apply=java.lang.invoke.MethodHandles.privateLookupIn(rule,java.lang.invoke.MethodHandles.lookup()).findVirtual(rule,"tryApply",
                java.lang.invoke.MethodType.methodType(net.minecraft.world.level.block.state.BlockState.class,int.class,int.class,int.class));
            Object stateA=apply.invoke(ruleA,0,0,0),stateB=apply.invoke(ruleB,0,0,0);
            if(stateA.equals(stateB))throw new AssertionError("Different native effective merged rules unexpectedly agreed");
        }catch(Throwable failure){if(failure instanceof Error error)throw error;throw new Exception("Native constant surface-rule witness failed",failure);}
        System.out.println("PASS actual native merged surface codec counterexample: identical original_source encoding can have different effective rule results; strict FP alone cannot establish effective surface parity");
    }
}
