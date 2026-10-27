package worldfortwo.bridge;

import com.mojang.serialization.Lifecycle;
import java.lang.invoke.MethodHandles;
import java.lang.invoke.MethodType;
import java.nio.file.Path;
import java.util.List;
import java.util.Map;
import java.util.zip.ZipFile;
import net.minecraft.core.Holder;
import net.minecraft.core.MappedRegistry;
import net.minecraft.core.Registry;
import net.minecraft.core.RegistryAccess;
import net.minecraft.core.registries.Registries;
import net.minecraft.data.registries.VanillaRegistries;
import net.minecraft.resources.RegistryOps;
import net.minecraft.resources.ResourceKey;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.packs.resources.ResourceManager;
import net.minecraft.world.level.biome.Biomes;
import net.minecraft.world.level.biome.FixedBiomeSource;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.dimension.BuiltinDimensionTypes;
import net.minecraft.world.level.dimension.LevelStem;
import net.minecraft.world.level.levelgen.DensityFunction;
import net.minecraft.world.level.levelgen.DensityFunctions;
import net.minecraft.world.level.levelgen.NoiseBasedChunkGenerator;
import net.minecraft.world.level.levelgen.NoiseGeneratorSettings;
import net.minecraft.world.level.levelgen.NoiseRouter;
import net.minecraft.world.level.levelgen.NoiseSettings;
import net.minecraft.world.level.levelgen.SurfaceRules;
import net.minecraft.world.level.levelgen.presets.WorldPreset;
import net.minecraft.world.level.levelgen.presets.WorldPresets;
import org.objectweb.asm.ClassReader;
import org.objectweb.asm.Opcodes;
import org.objectweb.asm.Type;
import org.objectweb.asm.tree.ClassNode;
import org.objectweb.asm.tree.MethodInsnNode;
import org.objectweb.asm.tree.MethodNode;
import org.objectweb.asm.tree.VarInsnNode;
import org.objectweb.asm.tree.analysis.Analyzer;
import org.objectweb.asm.tree.analysis.BasicInterpreter;
import org.objectweb.asm.tree.analysis.BasicValue;

/** Offline interoperation fixture. It never constructs a MinecraftServer or opens a world. */
public final class HybridAquaticSeedgenProbe {
    public static void main(String[] args)throws Throwable {
        tables(Path.of(args[0]),Path.of(args[1]));
        net.minecraft.SharedConstants.tryDetectVersion();
        net.minecraft.server.Bootstrap.bootStrap();
        for(boolean follows:List.of(true,false))orchestration(follows);
        System.out.println("PASS actual Minecraft frozen holders, ordered wrappers, both trench branches, record preservation, current normal-preset fallback and stale-holder refusal");
        if(args.length<3 || !args[2].equals("--native")) {
            System.out.println("Native HA helper execution NOT RUN: requires initialized NeoForge ModList. Strict paired fingerprint acceptance remains pending.");return;
        }
        nativeHelpers();
    }

    static ClassNode read(Path archive,String name)throws Exception {
        try(ZipFile zip=new ZipFile(archive.toFile())) {
            ClassNode node=new ClassNode();new ClassReader(zip.getInputStream(zip.getEntry(name+".class"))).accept(node,0);return node;
        }
    }
    static MethodNode method(ClassNode owner,String name,String descriptor) {
        var selected=owner.methods.stream().filter(m->m.name.equals(name)&&m.desc.equals(descriptor)).toList();
        if(selected.size()!=1)throw new AssertionError("Pinned native method differs: "+owner.name+"."+name+descriptor);return selected.getFirst();
    }
    static void tables(Path hybrid,Path seedgen)throws Exception {
        String density="Lnet/minecraft/world/level/levelgen/DensityFunction;";
        var wrapper=read(hybrid,"dev/hybridlabs/aquatic/world/gen/densityfunction/DensityFunctionWrappers");
        method(wrapper,"apply$lambda$4$lambda$3","("+density+density+")"+density);
        method(read(hybrid,wrapper.name+"$Wrapper$Companion"),"getCODEC","()Lcom/mojang/serialization/Codec;");
        var trench=read(hybrid,"dev/hybridlabs/aquatic/world/gen/densityfunction/TrenchCarver");
        method(trench,"apply$load","(Lnet/minecraft/core/Registry;Lnet/minecraft/world/level/levelgen/NoiseRouter;Lnet/minecraft/resources/ResourceKey;)"+density);
        method(trench,"strings","(Lcom/google/gson/JsonElement;)Lkotlin/sequences/Sequence;");
        var invoker=read(hybrid,"dev/hybridlabs/aquatic/mixin/HolderReferenceInvoker");
        method(invoker,"hybridAquatic$bindValue","(Ljava/lang/Object;)V");
        var server=method(read(hybrid,"dev/hybridlabs/aquatic/mixin/MinecraftServerMixin"),"modifyWorldgen",
            "(Lorg/spongepowered/asm/mixin/injection/callback/CallbackInfo;)V");
        var order=new java.util.ArrayList<String>();
        for(var instruction:server.instructions)if(instruction instanceof MethodInsnNode call && call.name.equals("apply"))order.add(call.owner);
        if(!order.equals(List.of(wrapper.name,trench.name)))throw new AssertionError("Native server wrapper/trench order changed");
        var target=read(seedgen,"mobius/seedrenderer/dh/ClientWorldgen");
        var attempt=method(target,"attempt","(ZZ)Lnet/minecraft/core/RegistryAccess$Frozen;");
        var analyzer=new Analyzer<BasicValue>(new BasicInterpreter(Opcodes.ASM9) {
            @Override public BasicValue newValue(Type type) {
                if(type!=null && (type.getSort()==Type.OBJECT || type.getSort()==Type.ARRAY))return new BasicValue(type);
                return super.newValue(type);
            }
        });
        var frames=analyzer.analyze(target.name,attempt);int closes=0;
        for(int i=0;i<attempt.instructions.size();i++) {
            var instruction=attempt.instructions.get(i);
            if(instruction instanceof MethodInsnNode call && call.owner.equals("net/minecraft/server/packs/resources/CloseableResourceManager") && call.name.equals("close")) {
                if(closes++!=0)continue;
                var frame=frames[i];
                if(!frame.getLocal(9).getType().getInternalName().equals("net/minecraft/server/packs/resources/MultiPackResourceManager")
                        && !frame.getLocal(9).getType().getInternalName().equals("net/minecraft/server/packs/resources/CloseableResourceManager"))
                    throw new AssertionError("Resource-manager injection local differs");
                for(int slot:new int[]{10,13,15})if(!frame.getLocal(slot).getType().getInternalName().equals("net/minecraft/core/RegistryAccess$Frozen"))
                    throw new AssertionError("Registry injection local differs at "+slot);
                if(!(instruction.getPrevious() instanceof VarInsnNode load) || load.var!=9)throw new AssertionError("Normal close no longer loads live resources");
            }
        }
        if(closes!=2)throw new AssertionError("Normal/exception close topology changed");
        System.out.println("PASS exact installed HA private API descriptors and SeedGen normal-close injection frame, including live registry/resource locals");
    }

    static DensityFunction c(double value){return DensityFunctions.constant(value);}
    static final ResourceLocation OFFSET=ResourceLocation.parse("minecraft:overworld/offset");
    static ResourceKey<DensityFunction> key(String name){return ResourceKey.create(Registries.DENSITY_FUNCTION,ResourceLocation.parse("fixture:"+name));}
    static NoiseRouter router() {
        return new NoiseRouter(c(.1),c(.2),c(.3),c(.4),c(.5),c(.6),c(.7),c(.8),c(.9),c(1),c(1.1),c(1.2),c(1.3),c(1.4),c(1.5));
    }
    static void bind(Holder.Reference<?> reference,Object value)throws Throwable {
        MethodHandles.privateLookupIn(Holder.Reference.class,MethodHandles.lookup())
            .findVirtual(Holder.Reference.class,"bindValue",MethodType.methodType(void.class,Object.class)).invoke(reference,value);
    }
    static double at(DensityFunction function){return function.compute(new DensityFunction.SinglePointContext(0,64,0));}

    static void orchestration(boolean follows)throws Throwable {
        var nativeLookup=VanillaRegistries.createLookup();
        var density=new MappedRegistry<DensityFunction>(Registries.DENSITY_FUNCTION,Lifecycle.stable());
        var offset=Registry.registerForHolder(density,ResourceKey.create(Registries.DENSITY_FUNCTION,OFFSET),c(.25));
        var settings=new MappedRegistry<NoiseGeneratorSettings>(Registries.NOISE_SETTINGS,Lifecycle.stable());
        var original=new NoiseGeneratorSettings(NoiseSettings.create(-64,384,1,2),Blocks.STONE.defaultBlockState(),
            Blocks.WATER.defaultBlockState(),router(),SurfaceRules.state(Blocks.GRASS_BLOCK.defaultBlockState()),List.of(),63,false,true,true,false);
        var reference=Registry.registerForHolder(settings,NoiseGeneratorSettings.OVERWORLD,original);
        var generator=new NoiseBasedChunkGenerator(new FixedBiomeSource(nativeLookup.lookupOrThrow(Registries.BIOME).getOrThrow(Biomes.PLAINS)),reference);
        var stem=new LevelStem(nativeLookup.lookupOrThrow(Registries.DIMENSION_TYPE).getOrThrow(BuiltinDimensionTypes.OVERWORLD),generator);
        var presets=new MappedRegistry<WorldPreset>(Registries.WORLD_PRESET,Lifecycle.stable());
        Registry.register(presets,WorldPresets.NORMAL,new WorldPreset(Map.of(LevelStem.OVERWORLD,stem)));
        var access=new RegistryAccess.ImmutableRegistryAccess(List.of(density,settings,presets)).freeze();
        var emptyStems=new MappedRegistry<LevelStem>(Registries.LEVEL_STEM,Lifecycle.stable());emptyStems.freeze();
        if(HybridAquaticSeedgenCompat.currentOverworld(access,emptyStems)!=stem)throw new AssertionError("Empty dimensions did not select the CURRENT normal preset");
        DensityFunction marker=c(-999);
        DensityFunction placeholder=new DensityFunctions.HolderHolder(Holder.direct(marker));
        var bindings=new HybridAquaticSeedgenCompat.Bindings() {
            public List<HybridAquaticSeedgenCompat.WrapperTarget> wrappers(ResourceManager resources,RegistryOps<com.google.gson.JsonElement> ops) {
                return List.of(new HybridAquaticSeedgenCompat.WrapperTarget(ResourceLocation.parse("fixture:a"),OFFSET,DensityFunctions.add(placeholder,c(.5))),
                    new HybridAquaticSeedgenCompat.WrapperTarget(ResourceLocation.parse("fixture:b"),OFFSET,DensityFunctions.mul(placeholder,c(2))));
            }
            public DensityFunction substitute(DensityFunction original,DensityFunction node){
                return node instanceof DensityFunctions.HolderHolder holder && holder.function().value()==marker?original:node;
            }
            public DensityFunction terrainFunction(Registry<DensityFunction> registry,NoiseRouter router,ResourceKey<DensityFunction> id){
                if(at(offset.value())!=1.5)throw new AssertionError("Trench ran before BOTH ordered wrapper rebindings");
                return c(id.equals(cleanupCarver())?-.25:id.equals(carver())?-.5:-.75);
            }
            public boolean readsOffset(DensityFunction root,RegistryAccess registry){return follows;}
            public void bind(Holder.Reference<?> holder,Object value)throws Throwable{HybridAquaticSeedgenProbe.bind(holder,value);}
            public ResourceKey<DensityFunction> carver(){return key("carver");}
            public ResourceKey<DensityFunction> cleanupCarver(){return key("cleanup");}
            public ResourceKey<DensityFunction> biomeDepth(){return key("depth");}
        };
        var report=HybridAquaticSeedgenCompat.applyNative(access,null,stem,bindings);
        if(report.wrappers()!=2 || !report.trench() || report.followsOffset()!=follows)throw new AssertionError("Wrong operation report");
        if(settings.getHolder(NoiseGeneratorSettings.OVERWORLD).orElseThrow()!=reference || density.getHolder(ResourceKey.create(Registries.DENSITY_FUNCTION,OFFSET)).orElseThrow()!=offset)
            throw new AssertionError("Frozen registry holder identity was replaced");
        var result=reference.value();var carved=result.noiseRouter();
        if(at(carved.initialDensityWithoutJaggedness())!=(follows?-.25:-.5) || at(carved.finalDensity())!=(follows?-.25:-.5)
                || at(carved.depth())!=(follows?.9:-.75))throw new AssertionError("Trench branch changed the wrong density");
        for(var component:NoiseRouter.class.getRecordComponents()) {
            if(List.of("initialDensityWithoutJaggedness","finalDensity","depth").contains(component.getName()))continue;
            if(component.getAccessor().invoke(original.noiseRouter())!=component.getAccessor().invoke(carved))throw new AssertionError("Unrelated router component changed");
        }
        for(var component:NoiseGeneratorSettings.class.getRecordComponents()) {
            if(component.getName().equals("noiseRouter"))continue;
            if(!component.getAccessor().invoke(original).equals(component.getAccessor().invoke(result)))throw new AssertionError("Unrelated noise setting changed");
        }
        try{HybridAquaticSeedgenCompat.replaceRecord(original,Map.of("unrecognized",true));throw new AssertionError("Unknown record component accepted");}
        catch(IllegalArgumentException expected){}
        // A separately allocated registered reference with the same key is not
        // the active private registry's holder and must never be rebound.
        var foreign=new MappedRegistry<NoiseGeneratorSettings>(Registries.NOISE_SETTINGS,Lifecycle.stable());
        var stale=Registry.registerForHolder(foreign,NoiseGeneratorSettings.OVERWORLD,original);foreign.freeze();
        var staleStem=new LevelStem(stem.type(),new NoiseBasedChunkGenerator(generator.getBiomeSource(),stale));
        try{HybridAquaticSeedgenCompat.applyNative(access,null,staleStem,bindings);throw new AssertionError("Stale dimension holder accepted");}
        catch(IllegalStateException expected){if(!expected.getMessage().contains("current private registries"))throw expected;}
        if(stale.value()!=original || at(offset.value())!=1.5)throw new AssertionError("Stale settings admitted a partial mutation");
        var directStem=new LevelStem(stem.type(),new NoiseBasedChunkGenerator(generator.getBiomeSource(),Holder.direct(original)));
        var beforeGuard=reference.value();
        var direct=HybridAquaticSeedgenCompat.applyNative(access,null,directStem,bindings);
        if(direct.wrappers()!=2 || direct.trench() || reference.value()!=beforeGuard)throw new AssertionError("Native unregistered-settings guard changed");
        var absent=HybridAquaticSeedgenCompat.applyNative(access,null,null,bindings);
        if(absent.wrappers()!=2 || absent.trench() || reference.value()!=beforeGuard)throw new AssertionError("Native absent-Overworld guard changed");
    }

    static void nativeHelpers()throws Throwable {
        var nativeApi=new HybridAquaticSeedgenCompat.NativeBindings() {
            @Override public void bind(Holder.Reference<?> reference,Object value)throws Throwable {
                // Unmixed offline Minecraft has no HA invoker interface. Exercise
                // the same actual protected bindValue method only in this fixture.
                HybridAquaticSeedgenProbe.bind(reference,value);
            }
        };
        Class<?> markerClass=Class.forName("dev.hybridlabs.aquatic.world.gen.densityfunction.DensityFunctionWrappers$WrappedMarker");
        DensityFunction marker=(DensityFunction)markerClass.getField("INSTANCE").get(null);
        DensityFunction reference=new DensityFunctions.HolderHolder(Holder.direct(marker));
        DensityFunction original=DensityFunctions.constant(.25);
        if(nativeApi.substitute(original,reference)!=original)throw new AssertionError("Native marker was not replaced");
        if(nativeApi.substitute(original,original)!=original)throw new AssertionError("Native visitor changed an ordinary node");
        System.out.println("PASS pinned native Hybrid Aquatic helper loading and actual marker substitution; worldgen/paired fingerprints not tested");
    }
}
