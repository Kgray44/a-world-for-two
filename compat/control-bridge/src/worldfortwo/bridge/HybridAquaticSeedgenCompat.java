package worldfortwo.bridge;

import com.google.gson.JsonElement;
import com.google.gson.JsonParser;
import com.mojang.serialization.Codec;
import com.mojang.serialization.JsonOps;
import java.io.InputStream;
import java.io.Reader;
import java.lang.invoke.MethodHandle;
import java.lang.invoke.MethodHandles;
import java.lang.invoke.MethodType;
import java.lang.reflect.RecordComponent;
import java.nio.file.Files;
import java.security.MessageDigest;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.HexFormat;
import java.util.Iterator;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;
import java.util.WeakHashMap;
import net.minecraft.core.Holder;
import net.minecraft.core.Registry;
import net.minecraft.core.RegistryAccess;
import net.minecraft.core.registries.Registries;
import net.minecraft.resources.FileToIdConverter;
import net.minecraft.resources.RegistryOps;
import net.minecraft.resources.ResourceKey;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.packs.resources.ResourceManager;
import net.minecraft.world.level.dimension.LevelStem;
import net.minecraft.world.level.levelgen.DensityFunction;
import net.minecraft.world.level.levelgen.DensityFunctions;
import net.minecraft.world.level.levelgen.NoiseBasedChunkGenerator;
import net.minecraft.world.level.levelgen.NoiseGeneratorSettings;
import net.minecraft.world.level.levelgen.NoiseRouter;
import net.minecraft.world.level.levelgen.presets.WorldPresets;
import net.neoforged.fml.ModList;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/** Apply Hybrid Aquatic's installed terrain definitions to SeedGen's private registries.
 * The native codec, marker visitor, trench loader and holder invoker are reused.
 * No server object, world file, fingerprint codec or comparison is changed.
 * This is original interoperation code; no third-party code or assets are bundled.
 */
public final class HybridAquaticSeedgenCompat {
    private static final Logger LOG=LoggerFactory.getLogger("AWFT-SeedGen-HybridAquatic");
    private static final String PREFIX="dev.hybridlabs.aquatic.world.gen.densityfunction.";
    private static final String SHA512="c71f952db5416b019007c71175c151c443a1724acce20e1a0ed7be9e4c88a68061b5cf18d57625414941928e5a21ac1f141ca922cc45ff627ecad9039e5f2a2b";
    private static final Map<RegistryAccess,Boolean> APPLIED=new WeakHashMap<>();

    private HybridAquaticSeedgenCompat() {}

    public static synchronized void apply(RegistryAccess.Frozen access,ResourceManager resources,Registry<LevelStem> stems) {
        if (!ModList.get().isLoaded("hybrid_aquatic") || APPLIED.containsKey(access)) return;
        try {
            var mod=ModList.get().getModContainerById("hybrid_aquatic").orElseThrow();
            var file=ModList.get().getModFileById("hybrid_aquatic").getFile().getFilePath();
            if (!"1.7.4".equals(mod.getModInfo().getVersion().toString()) || Files.size(file)!=7338389L)
                throw new IllegalStateException("Hybrid Aquatic SeedGen adapter requires the exact 1.7.4 artifact");
            MessageDigest hash=MessageDigest.getInstance("SHA-512");
            try(InputStream stream=Files.newInputStream(file)) {
                byte[] buffer=new byte[8192];for(int n;(n=stream.read(buffer))!=-1;)hash.update(buffer,0,n);
            }
            if(!SHA512.equals(HexFormat.of().formatHex(hash.digest())))
                throw new IllegalStateException("Pinned Hybrid Aquatic terrain artifact digest differs");
            if(stems==null)throw new IllegalStateException("SeedGen dimension definitions are unavailable for native Hybrid Aquatic terrain");
            Report report=applyNative(access,resources,currentOverworld(access,stems),new NativeBindings());
            APPLIED.put(access,Boolean.TRUE);
            LOG.info("SeedGen applied native Hybrid Aquatic terrain: {} wrapper(s), trench router {}, offset referenced {}",
                report.wrappers(),report.trench(),report.followsOffset());
        } catch(Throwable failure) { throw propagate(failure); }
    }

    record WrapperTarget(ResourceLocation source,ResourceLocation target,DensityFunction value) {}
    record Report(int wrappers,boolean trench,boolean followsOffset) {}

    interface Bindings {
        List<WrapperTarget> wrappers(ResourceManager resources,RegistryOps<JsonElement> ops)throws Throwable;
        DensityFunction substitute(DensityFunction original,DensityFunction node)throws Throwable;
        DensityFunction terrainFunction(Registry<DensityFunction> registry,NoiseRouter router,ResourceKey<DensityFunction> key)throws Throwable;
        boolean readsOffset(DensityFunction root,RegistryAccess access)throws Throwable;
        void bind(Holder.Reference<?> reference,Object value)throws Throwable;
        ResourceKey<DensityFunction> carver();
        ResourceKey<DensityFunction> cleanupCarver();
        ResourceKey<DensityFunction> biomeDepth();
    }

    /** Separate orchestration seam for the offline fixture; production uses NativeBindings only. */
    static Report applyNative(RegistryAccess.Frozen access,ResourceManager resources,LevelStem overworld,Bindings nativeApi)throws Throwable {
        if(overworld!=null && overworld.generator() instanceof NoiseBasedChunkGenerator selected
                && selected.generatorSettings() instanceof Holder.Reference<NoiseGeneratorSettings> reference
                && access.registryOrThrow(Registries.NOISE_SETTINGS).getHolder(reference.key()).orElse(null)!=reference)
            throw new IllegalStateException("SeedGen dimension settings do not belong to its current private registries");
        Registry<DensityFunction> density=access.registryOrThrow(Registries.DENSITY_FUNCTION);
        RegistryOps<JsonElement> ops=RegistryOps.create(JsonOps.INSTANCE,access);
        List<WrapperTarget> wrappers=nativeApi.wrappers(resources,ops);
        for(WrapperTarget wrapper:wrappers) {
            Holder.Reference<DensityFunction> reference=density.getHolder(ResourceKey.create(Registries.DENSITY_FUNCTION,wrapper.target())).orElseThrow(
                ()->new IllegalStateException("Native Hybrid Aquatic wrapper target is missing: "+wrapper.source()));
            DensityFunction original=reference.value();
            DensityFunction result=wrapper.value().mapAll(node->{
                try{return nativeApi.substitute(original,node);}catch(Throwable failure){throw propagate(failure);}
            });
            nativeApi.bind(reference,result);
        }
        if(overworld==null || !(overworld.generator() instanceof NoiseBasedChunkGenerator generator))
            return new Report(wrappers.size(),false,false);
        if(!(generator.generatorSettings() instanceof Holder.Reference<NoiseGeneratorSettings> reference)) {
            LOG.warn("SeedGen Overworld noise settings are not registered; native Hybrid Aquatic trench guard retained");
            return new Report(wrappers.size(),false,false);
        }
        // The separately loaded stems must refer to this same registry load,
        // never stale static stems left behind by a failed dimension attempt.
        if(access.registryOrThrow(Registries.NOISE_SETTINGS).getHolder(reference.key()).orElse(null)!=reference)
            throw new IllegalStateException("SeedGen dimension settings do not belong to its current private registries");
        NoiseGeneratorSettings original=reference.value();NoiseRouter router=original.noiseRouter();
        boolean follows=nativeApi.readsOffset(router.finalDensity(),access);
        DensityFunction carver=nativeApi.terrainFunction(density,router,follows?nativeApi.cleanupCarver():nativeApi.carver());
        Map<String,Object> changes=new TreeMap<>();
        changes.put("initialDensityWithoutJaggedness",DensityFunctions.min(router.initialDensityWithoutJaggedness(),carver));
        changes.put("finalDensity",DensityFunctions.min(router.finalDensity(),carver));
        if(!follows)changes.put("depth",DensityFunctions.min(router.depth(),nativeApi.terrainFunction(density,router,nativeApi.biomeDepth())));
        NoiseRouter carved=replaceRecord(router,changes);
        nativeApi.bind(reference,replaceRecord(original,Map.of("noiseRouter",carved)));
        return new Report(wrappers.size(),true,follows);
    }

    static LevelStem currentOverworld(RegistryAccess.Frozen access,Registry<LevelStem> stems) {
        LevelStem explicit=stems.get(LevelStem.OVERWORLD);
        if(explicit!=null)return explicit;
        // Normal vanilla dimensions come from WORLD_PRESET, so an otherwise
        // successful DIMENSION_REGISTRIES load can legitimately contain zero.
        // The owner world is verified normal/minecraft:overworld. Do not bind
        // values from a prior attempt's stems or assume another world preset.
        LevelStem normal=WorldPresets.getNormalOverworld(access);
        if(!(normal.generator() instanceof NoiseBasedChunkGenerator generator)
                || !(generator.generatorSettings() instanceof Holder.Reference<NoiseGeneratorSettings> reference)
                || !reference.key().equals(NoiseGeneratorSettings.OVERWORLD)
                || access.registryOrThrow(Registries.NOISE_SETTINGS).getHolder(reference.key()).orElse(null)!=reference)
            throw new IllegalStateException("Current normal preset does not supply the verified registered Overworld settings");
        LOG.info("SeedGen uses its current registered normal-preset Overworld for native Hybrid Aquatic terrain; no explicit dimension definition");
        return normal;
    }

    /** Copy all Minecraft record components, overriding only explicitly named fields. */
    static <T>T replaceRecord(T original,Map<String,Object> changes)throws ReflectiveOperationException {
        RecordComponent[] components=original.getClass().getRecordComponents();
        if(components==null)throw new IllegalArgumentException("Native terrain definition is not the expected Minecraft record");
        Set<String> pending=new HashSet<>(changes.keySet());Class<?>[] types=new Class<?>[components.length];Object[] values=new Object[components.length];
        for(int i=0;i<components.length;i++) {
            var component=components[i];types[i]=component.getType();
            values[i]=pending.remove(component.getName())?changes.get(component.getName()):component.getAccessor().invoke(original);
        }
        if(!pending.isEmpty())throw new IllegalArgumentException("Unknown Minecraft terrain record components: "+pending);
        @SuppressWarnings("unchecked")T result=(T)original.getClass().getDeclaredConstructor(types).newInstance(values);return result;
    }

    /** All mod-specific decoding and node substitution call the pinned installed mod. */
    static class NativeBindings implements Bindings {
        private final FileToIdConverter files;
        private final Codec<?> wrapperCodec;
        private final MethodHandle target,wrapped,substitute,load,strings,iterator,bind;
        private final Object trench;
        private final ResourceLocation offset;
        private final ResourceKey<DensityFunction> carver,cleanup,depth;

        @SuppressWarnings("unchecked")NativeBindings()throws Throwable {
            Class<?> wrappers=Class.forName(PREFIX+"DensityFunctionWrappers");
            Class<?> specification=Class.forName(wrappers.getName()+"$Wrapper");
            var wrapperLookup=MethodHandles.privateLookupIn(wrappers,MethodHandles.lookup());
            files=(FileToIdConverter)wrapperLookup.findStaticGetter(wrappers,"WRAPPER_FILES",FileToIdConverter.class).invoke();
            Object companion=specification.getField("Companion").get(null);
            wrapperCodec=(Codec<?>)companion.getClass().getMethod("getCODEC").invoke(companion);
            target=MethodHandles.publicLookup().findVirtual(specification,"getTargetFunction",MethodType.methodType(ResourceLocation.class));
            wrapped=MethodHandles.publicLookup().findVirtual(specification,"getWrapperFunction",MethodType.methodType(Holder.class));
            substitute=wrapperLookup.findStatic(wrappers,"apply$lambda$4$lambda$3",MethodType.methodType(DensityFunction.class,DensityFunction.class,DensityFunction.class));
            Class<?> trenchClass=Class.forName(PREFIX+"TrenchCarver");
            var trenchLookup=MethodHandles.privateLookupIn(trenchClass,MethodHandles.lookup());
            trench=trenchClass.getField("INSTANCE").get(null);
            load=trenchLookup.findStatic(trenchClass,"apply$load",MethodType.methodType(DensityFunction.class,Registry.class,NoiseRouter.class,ResourceKey.class));
            Class<?> sequence=Class.forName("kotlin.sequences.Sequence");
            strings=trenchLookup.findVirtual(trenchClass,"strings",MethodType.methodType(sequence,JsonElement.class));
            iterator=MethodHandles.publicLookup().findVirtual(sequence,"iterator",MethodType.methodType(Iterator.class));
            offset=(ResourceLocation)trenchLookup.findStaticGetter(trenchClass,"VANILLA_OFFSET",ResourceLocation.class).invoke();
            carver=(ResourceKey<DensityFunction>)trenchLookup.findStaticGetter(trenchClass,"CARVER",ResourceKey.class).invoke();
            cleanup=(ResourceKey<DensityFunction>)trenchLookup.findStaticGetter(trenchClass,"CLEANUP_CARVER",ResourceKey.class).invoke();
            depth=(ResourceKey<DensityFunction>)trenchLookup.findStaticGetter(trenchClass,"BIOME_DEPTH",ResourceKey.class).invoke();
            Class<?> invoker=Class.forName("dev.hybridlabs.aquatic.mixin.HolderReferenceInvoker");
            bind=MethodHandles.publicLookup().findVirtual(invoker,"hybridAquatic$bindValue",MethodType.methodType(void.class,Object.class));
        }

        public List<WrapperTarget> wrappers(ResourceManager resources,RegistryOps<JsonElement> ops)throws Throwable {
            var selected=new TreeMap<>(files.listMatchingResources(resources));
            if(selected.size()>64)throw new IllegalStateException("Hybrid Aquatic wrapper metadata exceeds the bounded adapter");
            List<WrapperTarget> result=new ArrayList<>();int total=0;
            for(var entry:selected.entrySet()) {
                StringBuilder text=new StringBuilder();
                try(Reader reader=entry.getValue().openAsReader()) {
                    char[] buffer=new char[4096];for(int n;(n=reader.read(buffer))!=-1;) {
                        total+=n;if(total>1024*1024)throw new IllegalStateException("Native wrapper metadata exceeds one MiB");text.append(buffer,0,n);
                    }
                }
                Object value=wrapperCodec.parse(ops,JsonParser.parseString(text.toString())).getOrThrow();
                result.add(new WrapperTarget(files.fileToId(entry.getKey()),(ResourceLocation)target.invoke(value),
                    (DensityFunction)((Holder<?>)wrapped.invoke(value)).value()));
            }
            return List.copyOf(result);
        }
        public DensityFunction substitute(DensityFunction original,DensityFunction node)throws Throwable {return (DensityFunction)substitute.invokeExact(original,node);}
        public DensityFunction terrainFunction(Registry<DensityFunction> registry,NoiseRouter router,ResourceKey<DensityFunction> key)throws Throwable {return (DensityFunction)load.invokeExact((Registry)registry,router,(ResourceKey)key);}
        public void bind(Holder.Reference<?> reference,Object value)throws Throwable {bind.invoke(reference,value);}
        public ResourceKey<DensityFunction> carver(){return carver;}
        public ResourceKey<DensityFunction> cleanupCarver(){return cleanup;}
        public ResourceKey<DensityFunction> biomeDepth(){return depth;}

        public boolean readsOffset(DensityFunction root,RegistryAccess access)throws Throwable {
            RegistryOps<JsonElement> ops=RegistryOps.create(JsonOps.INSTANCE,access);
            Registry<DensityFunction> registry=access.registryOrThrow(Registries.DENSITY_FUNCTION);
            Set<ResourceLocation> visited=new HashSet<>();ArrayDeque<DensityFunction> queue=new ArrayDeque<>();queue.add(root);
            while(!queue.isEmpty()) {
                var encoded=DensityFunction.HOLDER_HELPER_CODEC.encodeStart(ops,queue.remove()).result();
                if(encoded.isEmpty())continue; // Same native reads() result guard; fingerprint encoding is untouched.
                Iterator<?> values=(Iterator<?>)iterator.invoke(strings.invoke(trench,encoded.get()));
                while(values.hasNext()) {
                    ResourceLocation id=ResourceLocation.tryParse((String)values.next());if(id==null)continue;
                    if(id.equals(offset))return true;
                    if(visited.add(id)) {
                        if(visited.size()>65536)throw new IllegalStateException("Native terrain reference graph exceeds the bounded adapter");
                        DensityFunction next=registry.get(id);if(next!=null)queue.add(next);
                    }
                }
            }
            return false;
        }
    }

    private static RuntimeException propagate(Throwable failure) {
        if(failure instanceof Error error)throw error;
        if(failure instanceof RuntimeException runtime)return runtime;
        return new IllegalStateException("Cannot apply the exact native Hybrid Aquatic terrain definitions",failure);
    }
}
