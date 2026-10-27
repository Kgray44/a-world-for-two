package worldfortwo.bridge;

import dev.worldgen.lithostitched.api.worldgen.util.NoiseRouterTarget;
import dev.worldgen.lithostitched.impl.LithostitchedInternalHooks;
import dev.worldgen.lithostitched.impl.worldgen.modifier.ModifierManager;
import dev.worldgen.lithostitched.mixin.common.NoiseGeneratorSettingsAccessor;
import dev.worldgen.lithostitched.worldgen.modifier.WrapNoiseRouterModifier;
import dev.worldgen.lithostitched.worldgen.surface.SurfaceRuleManager;
import java.io.InputStream;
import java.lang.invoke.MethodHandle;
import java.lang.invoke.MethodHandles;
import java.lang.invoke.MethodType;
import java.lang.invoke.VarHandle;
import java.nio.file.Files;
import java.security.MessageDigest;
import java.util.HexFormat;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.WeakHashMap;
import java.util.concurrent.ExecutorService;
import java.util.function.Supplier;
import java.util.stream.Stream;
import net.minecraft.core.Holder;
import net.minecraft.core.Registry;
import net.minecraft.core.RegistryAccess;
import net.minecraft.core.registries.Registries;
import net.minecraft.resources.ResourceKey;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.packs.PackResources;
import net.minecraft.server.packs.resources.ResourceManager;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.dimension.LevelStem;
import net.minecraft.world.level.levelgen.DensityFunction;
import net.minecraft.world.level.levelgen.NoiseBasedChunkGenerator;
import net.minecraft.world.level.levelgen.NoiseGeneratorSettings;
import net.minecraft.world.level.levelgen.NoiseRouter;
import net.minecraft.world.level.levelgen.presets.WorldPresets;
import net.neoforged.fml.ModList;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/** Original client orchestration of pinned native load hooks and authenticated-seed setup.
 * Proposal only: never substitutes encoded values or changes a native fingerprint gate.
 * An accepted packet triggers one fresh native load in the real server hook order.
 */
public final class LithostitchedSeedgenCompat {
    private static final Logger LOG=LoggerFactory.getLogger("AWFT-SeedGen-Lithostitched");
    private static final String JAR_SHA="e0da669fa5facc61a09b9b7bae21b322993de1fcd1eb05787adffb7309598cca";
    private static final String SEEDGEN_SHA="58469f92f7cf13ff3c2928659ce1a57d7d05314b30e0779cb187b6fbfdb43b4e";
    private static final Map<String,String> PINS=Map.ofEntries(
        Map.entry("dev/worldgen/lithostitched/impl/worldgen/modifier/ModifierManager.class","30f4ff11fee6a349e765e389024fd204a54821550009894c8b785f79dc4bdb67"),
        Map.entry("dev/worldgen/lithostitched/worldgen/surface/SurfaceRuleManager.class","a472fc886a1f7602b4a789b484d9fbec4ff8e8d95e16ed9b0cc9b70a5e8c9931"),
        Map.entry("dev/worldgen/lithostitched/worldgen/modifier/WrapNoiseRouterModifier.class","eb9a095f01412d92a69564dbca6625a7fea9a1fd9afd1d4f18cc454fd63a3d85"),
        Map.entry("dev/worldgen/lithostitched/mixin/common/ChunkMapMixin.class","ef2aa84e5d32706ddc2e913a357c265067f963f3767f8a48d2fb2485c53eb962"),
        Map.entry("dev/worldgen/lithostitched/impl/LithostitchedInternalHooks.class","1ee0a688cd669b4827ed4f97a212447a11bc016d3f9324c74d0828ee63c74dae"),
        Map.entry("dev/worldgen/lithostitched/api/worldgen/util/NoiseRouterTarget.class","dc21d3c5df9fba836df0d33239e3852b405cb26c6d98f47ac0acca60a52c2072"),
        Map.entry("dev/worldgen/lithostitched/mixin/common/NoiseGeneratorSettingsAccessor.class","216af225e3f92eb8f865831f87e24d758bcb77647832ba948827f10b94be6c50"),
        Map.entry("dev/worldgen/lithostitched/impl/worldgen/surface/rule/TransientMergedRule.class","19b82e92c870cdd8d715293491322f2417a12004342eb1ccb9daeba0a99de97d"),
        Map.entry("dev/worldgen/lithostitched/api/worldgen/densityfunction/fastnoise/FastNoiseConfig.class","b67f80f8fa5182939ad313f19258557747f79aff3020f30478b9023e1fcb6221"),
        Map.entry("dev/worldgen/lithostitched/impl/worldgen/densityfunction/FastNoiseDensityFunction.class","8bb76893ac190e3de6c0ef146cc1630c77cefac4ed976f7b919f779b94fecdde"),
        Map.entry("mobius/seedrenderer/dh/ClientWorldgen.class","d352c1c7fa607f2ba29eac97364eda8ed126984161386acdab693acdbebc4c19"),
        Map.entry("mobius/seedrenderer/dh/ClientTerrain.class","b132d1330daeeab8e16e660e40b8c40ec12d1ed8c8add404346eb904e26662f7"),
        Map.entry("mobius/seedrenderer/dh/SeedRetrievalQueue.class","798745e930511c70ea608181c3a708e98556a64e25470e5f351886932e2f92ed"),
        Map.entry("mobius/seedrenderer/net/SeedSharing.class","33447b2f4f9b151501d05d6992576d0e6eaa517ffa4df30183be6bc97a4f31ec"),
        Map.entry("mobius/seedrenderer/dh/WorldBasis.class","109e6f3f03bad956af3cbc6e7f30128e4a784bf75e26698e300f3bca814bd892"),
        Map.entry("mobius/seedrenderer/neoforge/SeedGenNeoForge.class","f2a251767374ca3c23ac092141deab8fe43ae3a7e97fd6765a17c22e6a320f96"));
    private static final Map<RegistryAccess,Session> SESSIONS=new WeakHashMap<>();
    private static final ThreadLocal<SeedContext> REBUILD=new ThreadLocal<>();
    private static final ThreadLocal<Permit> PERMIT=new ThreadLocal<>();
    private static final ThreadLocal<Object> PACKET_LISTENER=new ThreadLocal<>();
    private static boolean lifecycleHookInstalled;
    private static final LithostitchedSeedgenConnectionGate CONNECTION=new LithostitchedSeedgenConnectionGate();
    private static boolean failedSeededLoad;
    /** Implemented by the required fromSeed guard mixin, not an authorization token. */
    public interface SeededBasisGuard {}
    public interface IsolatedAttemptGuard {}
    public interface QueueAdmissionGuard {}
    public interface AuthenticatedPacketGuard {}
    private enum Phase { PREPARING, BEFORE_HYBRID, FINISHED, FAILED }
    private static final class Session {
        final Registry<LevelStem> dimensions;
        final Map<String,Member> members;
        final boolean wholeSet;
        final Long seed;
        final LithostitchedSeedgenResources.Attestation resources;
        final List<String> packNames;
        Phase phase=Phase.PREPARING;
        Session(Registry<LevelStem> dimensions,Map<String,Member> members,boolean wholeSet,Long seed,LithostitchedSeedgenResources.Attestation resources){
            this.dimensions=dimensions;this.members=members;this.wholeSet=wholeSet;this.seed=seed;this.resources=resources;
            this.packNames=LithostitchedSeedgenLoadScope.current().names();}
    }
    private static final class SeedContext {
        final long seed;
        Session session;
        List<String> packNames;
        SeedContext(long seed){this.seed=seed;}
    }
    private record Permit(RegistryAccess.Frozen registry,ResourceKey<Level> dimension,long seed,ResourceLocation type){}
    private record Member(Registry<?> registry,Set<ResourceLocation> keys){}
    private LithostitchedSeedgenCompat(){}

    /** Call immediately BEFORE HybridAquaticSeedgenCompat.apply, with live current load. */
    public static synchronized void beforeHybrid(RegistryAccess.Frozen actual,Registry<LevelStem> explicit,boolean wholeSet,
            List<PackResources> opened,ResourceManager resources) {
        if(!ModList.get().isLoaded("lithostitched"))return;
        Session session=SESSIONS.get(actual);
        if(session!=null){
            if(session.phase==Phase.BEFORE_HYBRID||session.phase==Phase.FINISHED)return;
            throw new IllegalStateException("Do not retry a partial/reentrant native Lithostitched application");
        }
        try {
            guardArtifact();
            Class<?> basis=Class.forName("mobius.seedrenderer.dh.WorldBasis",false,LithostitchedSeedgenCompat.class.getClassLoader());
            if(!SeededBasisGuard.class.isAssignableFrom(basis))
                throw new IllegalStateException("Required native fromSeed guard mixin is absent; refuse fingerprint-only initialization");
            Class<?> worldgen=Class.forName("mobius.seedrenderer.dh.ClientWorldgen",false,LithostitchedSeedgenCompat.class.getClassLoader());
            Class<?> terrain=Class.forName("mobius.seedrenderer.dh.ClientTerrain",false,LithostitchedSeedgenCompat.class.getClassLoader());
            Class<?> payloads=Class.forName("mobius.seedrenderer.neoforge.SeedGenNeoForge",false,LithostitchedSeedgenCompat.class.getClassLoader());
            if(!IsolatedAttemptGuard.class.isAssignableFrom(worldgen)||!QueueAdmissionGuard.class.isAssignableFrom(terrain)
                    ||!AuthenticatedPacketGuard.class.isAssignableFrom(payloads)||!lifecycleHookInstalled)
                throw new IllegalStateException("Required attempt/queue/logout lifecycle guards are absent");
            if(explicit!=LithostitchedSeedgenLoadScope.readStems())
                throw new IllegalStateException("Callback must use currentAttemptStems rather than the unpublished static cache");
            Registry<LevelStem> selected=selectDimensions(actual,explicit);
            SeedContext rebuilding=REBUILD.get();
            var attestation=LithostitchedSeedgenResources.capture(opened,resources);
            session=new Session(selected,captureMembers(actual),wholeSet,rebuilding==null?null:rebuilding.seed,attestation);
            SESSIONS.put(actual,session);if(rebuilding!=null)rebuilding.session=session;
            RegistryAccess view=withDimensions(actual,selected);
            // Exact native startup order; native predicates/events/configuration
            // were already loaded by the same installed resource pipeline.
            if(rebuilding==null){
                ModifierManager.applyModifiers(view,selected);
                SurfaceRuleManager.applySurfaceRules(view,selected);
            }else{
                // Real authenticated seed, before HA: this native hook runs
                // modifiers, surfaces, biome injectors, then FastNoise binding.
                LithostitchedInternalHooks.applyModifiersAndInjections(view,selected,rebuilding.seed);
            }
            verifyMembers(actual,session.members);
            verifyCurrentHolders(actual,selected);
            session.phase=Phase.BEFORE_HYBRID;
            LOG.info("SeedGen applied native Lithostitched startup phase for {} current dimension(s); authenticated seed phase {}",selected.size(),rebuilding!=null);
        }catch(Throwable failure){if(session!=null)session.phase=Phase.FAILED;throw propagate(failure);}
    }

    /** Existing callback's @Shadow read is outside the redirected native method. */
    public static Registry<LevelStem> currentAttemptStems(Registry<LevelStem> unpublishedStatic) {
        return LithostitchedSeedgenLoadScope.readStems();
    }

    /** Whole native attempt scope. No partial native cache fields escape a failed load. */
    public static synchronized RegistryAccess.Frozen isolateAttempt(boolean mods,Supplier<RegistryAccess.Frozen> original) {
        try(var scope=LithostitchedSeedgenLoadScope.enter()) {
            RegistryAccess.Frozen result=original.get();
            if(result==null)return null;
            scope.requireComplete();Session session=SESSIONS.get(result);SeedContext rebuild=REBUILD.get();
            Registry<LevelStem> selected=scope.stems();
            if(mods&&ModList.get().isLoaded("lithostitched")) {
                if(session==null||session.phase!=Phase.FINISHED)throw new IllegalStateException("Native attempt returned before all guarded callbacks finished");
                selected=session.dimensions;
            }
            if(rebuild!=null) {
                if(!mods||rebuild.session!=session)throw new IllegalStateException("Authenticated native attempt cannot publish fallback data");
                rebuild.packNames=scope.names();
            }else{
                new ClientAccess().publishMetadata(selected,scope.names());
            }
            return result;
        }catch(Throwable failure){if(REBUILD.get()!=null)failedSeededLoad=true;throw propagate(failure);}
    }

    /** Call immediately AFTER HA wrappers/trench, before SeedGen can fingerprint. */
    public static synchronized void afterHybrid(RegistryAccess.Frozen actual) {
        if(!ModList.get().isLoaded("lithostitched"))return;
        Session session=SESSIONS.get(actual);
        if(session==null||session.phase==Phase.PREPARING||session.phase==Phase.FAILED)
            throw new IllegalStateException("Native Lithostitched pre-HA phase did not finish");
        if(session.phase==Phase.FINISHED)return;
        try {
            verifyCurrentHolders(actual,session.dimensions);
            RegistryAccess view=withDimensions(actual,session.dimensions);
            NoiseRouterTarget[] targets=NoiseRouterTarget.values();
            if(targets.length!=15)throw new IllegalStateException("Pinned native router target table changed");
            int applied=0;
            for(var entry:session.dimensions.entrySet()) {
                if(!(entry.getValue().generator() instanceof NoiseBasedChunkGenerator generator))continue;
                ResourceKey<Level> dimension=ResourceKey.create(Registries.DIMENSION,entry.getKey().location());
                List<WrapNoiseRouterModifier> modifiers=ModifierManager.getModifiersOfType(view,WrapNoiseRouterModifier.CODEC)
                    .stream().map(Map.Entry::getValue).filter(m->dimension.equals(m.dimension())).toList();
                if(modifiers.size()>4096)throw new IllegalStateException("Native router modifier list exceeds bounded adapter");
                if(modifiers.isEmpty())continue;
                NoiseGeneratorSettings settings=generator.generatorSettings().value();
                NoiseRouter replacement=mapRouter(settings.noiseRouter(),(index,value)->
                    WrapNoiseRouterModifier.modifyDensityFunction(targets[index],value,modifiers));
                ((NoiseGeneratorSettingsAccessor)(Object)settings).setNoiseRouter(replacement);
                applied+=modifiers.size();
            }
            verifyMembers(actual,session.members);
            verifyCurrentHolders(actual,session.dimensions);
            session.phase=Phase.FINISHED;
            LOG.info("SeedGen applied {} native dimension-filtered Lithostitched router modifier(s); authenticated seed phase {}",applied,session.seed!=null);
        }catch(Throwable failure){session.phase=Phase.FAILED;throw propagate(failure);}
    }

    /** Called ONLY by the wrapper around the original authenticated onWorld call.
     * No seed, encoded value or fingerprint is logged. No cached old registry is
     * re-modified: the exact native attempt builds a fresh current private load.
     */
    public static synchronized <T>T withAcceptedSeed(ResourceKey<Level> dimension,long seed,ResourceLocation type,Supplier<T> original) {
        if(!ModList.get().isLoaded("lithostitched"))return original.get();
        if(failedSeededLoad||REBUILD.get()!=null||PERMIT.get()!=null)
            throw new IllegalStateException("Native seeded preparation failed or is reentrant; preserve failure and restart client");
        try {
            ClientAccess api=new ClientAccess();api.requireClientThread();
            requirePacketOwner(api);
            CONNECTION.prepare(seed,LithostitchedInternalHooks.WORLD_SEED,api.integratedServer());
            RegistryAccess.Frozen current=api.loaded();Session session=SESSIONS.get(current);
            if(current==null||session==null||session.phase!=Phase.FINISHED)
                throw new IllegalStateException("No completed native provisional terrain load");
            requireDimension(session,dimension,type);
            if(session.seed==null||session.seed.longValue()!=seed){
                if(!api.sharedEmpty())throw new IllegalStateException("Native active world bases must be absent before publishing a fresh seeded load");
                String accepted=api.fingerprint(current);
                if(accepted.equals("unknown"))throw new IllegalStateException("Native provisional fingerprint is unavailable");
                SeedContext context=new SeedContext(seed);RegistryAccess.Frozen fresh;
                REBUILD.set(context);
                try{fresh=api.attempt(session.wholeSet);}finally{REBUILD.remove();}
                if(fresh==null||fresh==current||context.session==null||SESSIONS.get(fresh)!=context.session
                        ||context.session.phase!=Phase.FINISHED||context.session.seed==null)
                    throw new IllegalStateException("Exact native seeded attempt did not complete; no fallback generation");
                Session next=context.session;
                requireDimension(next,dimension,type);
                if(!sameMembers(session.members,next.members)||!session.resources.equals(next.resources)||context.packNames==null
                        ||!session.packNames.equals(context.packNames))
                    throw new IllegalStateException("Native seeded registry members or actual ordered server-data content differ from accepted load");
                // Additional strict check, never replacement of native server
                // acceptance. Invoke the original native function on fresh data.
                String rebuilt=api.fingerprint(fresh);
                if(!accepted.equals(rebuilt))
                    throw new IllegalStateException("Actual seeded terrain definitions differ from accepted native fingerprint");
                requirePacketOwner(api); // Network can close while this client-thread load runs.
                if(api.loaded()!=current)throw new IllegalStateException("Current native registry changed during preparation");
                api.publish(current,fresh,next.dimensions,context.packNames);
                current=fresh;session=next;
                LOG.info("SeedGen prepared native biome injectors and FastNoise using authenticated seed; strict native definition equality retained");
            }
            verifyCurrentHolders(current,session.dimensions);
            requirePacketOwner(api);
            CONNECTION.open(seed,LithostitchedInternalHooks.WORLD_SEED);
            PERMIT.set(new Permit(current,dimension,seed,type));
            try{return original.get();}finally{PERMIT.remove();}
        }catch(Throwable failure){failedSeededLoad=true;CONNECTION.fail();throw propagate(failure);}
    }

    /** Required HEAD guard on WorldBasis.fromSeed; fingerprint equality alone is insufficient. */
    public static synchronized void requireSeededBasis(ResourceKey<Level> dimension,long seed,ResourceLocation type) {
        if(!ModList.get().isLoaded("lithostitched"))return;
        Permit permit=PERMIT.get();
        if(failedSeededLoad||permit==null||permit.seed()!=seed||!permit.dimension().equals(dimension)||!permit.type().equals(type))
            throw new IllegalStateException("Native modded biome generation requires the authenticated seed initialization path");
        try {
            ClientAccess api=new ClientAccess();
            requirePacketOwner(api);
            CONNECTION.requirePermit(seed,LithostitchedInternalHooks.WORLD_SEED,api.integratedServer());
            if(api.loaded()!=permit.registry())throw new IllegalStateException("Seeded basis does not use the current native registry");
            Session session=SESSIONS.get(permit.registry());
            if(session==null||session.phase!=Phase.FINISHED||session.seed==null||session.seed.longValue()!=seed
                    ||api.dimensions()!=session.dimensions)
                throw new IllegalStateException("Native seeded dimensions are not ready");
            verifyCurrentHolders(permit.registry(),session.dimensions);requireDimension(session,dimension,type);
        }catch(Throwable failure){throw propagate(failure);}
    }

    public static synchronized void installLifecycleHook(){lifecycleHookInstalled=true;}

    /** Read-only capture of actual caches. Never invokes load/attempt or grants
     * a generation permit; the caller is the real client owner thread. */
    public record DiagnosticCapture(RegistryAccess.Frozen registry,Registry<LevelStem> stems,Object listener){}
    public static synchronized DiagnosticCapture captureDiagnostic()throws Throwable {
        ClientAccess api=new ClientAccess();api.requireClientThread();
        RegistryAccess.Frozen actual=api.loaded();Registry<LevelStem> selected=api.dimensions();Object listener=api.listener();
        if(actual==null||selected==null||listener==null||!api.connected(listener))throw new IllegalStateException("Current connected native cache is unavailable; no new load requested");
        return new DiagnosticCapture(actual,selected,listener);
    }
    public static synchronized boolean diagnosticStillCurrent(DiagnosticCapture captured) {
        try{ClientAccess api=new ClientAccess();api.requireClientThread();return api.loaded()==captured.registry()
            && api.dimensions()==captured.stems()&&api.listener()==captured.listener()&&api.connected(captured.listener());}
        catch(Throwable failure){return false;}
    }

    /** The native payload handler supplies its original IPayloadContext listener.
     * Keep custody through the ENTIRE original onWorld, including its later
     * SHARED.put. Old queued packets are refused without reopening admission.
     * The native serverGeneration early return is still inside original.run().
     */
    public static synchronized void withPacketContext(Object offered,Object current,boolean live,Runnable original) {
        if(!ModList.get().isLoaded("lithostitched")){original.run();return;}
        CONNECTION.packet(offered,current,live,()->{
            if(PACKET_LISTENER.get()!=null)throw new IllegalStateException("Reentrant native world-share payload");
            PACKET_LISTENER.set(offered);
            try{original.run();return null;}finally{PACKET_LISTENER.remove();}
        });
    }

    private static void requirePacketOwner(ClientAccess api)throws Throwable {
        Object offered=PACKET_LISTENER.get(),current=api.listener();
        if(offered==null||offered!=current||!api.connected(current))
            throw new IllegalStateException("Native world basis requires the current live authenticated payload connection");
    }

    /** Hold this SAME monitor through the whole native queueFor, including its shared-basis read. */
    public static synchronized <T>T withQueueAdmission(Supplier<T> nativeQueueFor) {
        if(failedSeededLoad||REBUILD.get()!=null)return null;
        return CONNECTION.admit(()->LithostitchedInternalHooks.WORLD_SEED,nativeQueueFor);
    }

    /** Real client LoggingOut only; accepts null event player/connection without reading them. */
    public static synchronized void disconnect() {
        PERMIT.remove();PACKET_LISTENER.remove();
        try {
            ClientAccess api=new ClientAccess();
            // Exact native order: clear all shared bases first, then close/clear queues.
            // queueFor holds this monitor, so no captured old basis can publish after cleanup.
            CONNECTION.logout(()->{
                try{api.forgetShared();return api.closeQueues();}
                catch(Throwable failure){throw propagate(failure);}
            });
        }catch(Throwable failure){failedSeededLoad=true;CONNECTION.fail();LOG.error("Native terrain logout cleanup failed; restart client",failure);}
    }

    /** Nonblocking observation of OWNED queue executors; external DH work is not claimed drained. */
    public static synchronized void pollCleanup() {
        CONNECTION.poll();
    }
    public static synchronized void observedIntegratedServer(){failedSeededLoad=true;CONNECTION.fail();}

    private static void requireDimension(Session session,ResourceKey<Level> dimension,ResourceLocation type) {
        LevelStem stem=session.dimensions.get(ResourceKey.create(Registries.LEVEL_STEM,dimension.location()));
        if(stem==null||!(stem.generator() instanceof NoiseBasedChunkGenerator generator)
                ||generator.generatorSettings().unwrapKey().isEmpty()
                ||!generator.generatorSettings().unwrapKey().orElseThrow().location().equals(type))
            throw new IllegalStateException("Accepted dimension/type is absent from current normal dimensions");
    }
    private static boolean sameMembers(Map<String,Member> first,Map<String,Member> second) {
        if(!first.keySet().equals(second.keySet()))return false;
        for(String key:first.keySet())if(!first.get(key).keys().equals(second.get(key).keys()))return false;
        return true;
    }

    /** Exact typed member access only; no enumeration, fake server or get/load recursion. */
    private static final class ClientAccess {
        final VarHandle loaded,stems,names;
        final MethodHandle attempt,fingerprint,shared,client,currentThread,integrated,forgetShared,forgetQueues,queues,workers,listener,network,connected;
        ClientAccess()throws ReflectiveOperationException {
            ClassLoader loader=LithostitchedSeedgenCompat.class.getClassLoader();
            Class<?> worldgen=Class.forName("mobius.seedrenderer.dh.ClientWorldgen",false,loader);
            var lookup=MethodHandles.privateLookupIn(worldgen,MethodHandles.lookup());
            loaded=lookup.findStaticVarHandle(worldgen,"loaded",RegistryAccess.Frozen.class);
            stems=lookup.findStaticVarHandle(worldgen,"stems",Registry.class);
            names=lookup.findStaticVarHandle(worldgen,"dataPackNames",List.class);
            attempt=lookup.findStatic(worldgen,"attempt",MethodType.methodType(RegistryAccess.Frozen.class,boolean.class,boolean.class));
            Class<?> sharing=Class.forName("mobius.seedrenderer.net.SeedSharing",false,loader);
            fingerprint=MethodHandles.publicLookup().findStatic(sharing,"fingerprintOf",MethodType.methodType(String.class,RegistryAccess.class));
            var sharingLookup=MethodHandles.privateLookupIn(sharing,MethodHandles.lookup());
            shared=sharingLookup.findStaticGetter(sharing,"SHARED",Map.class);
            forgetShared=sharingLookup.findStatic(sharing,"forget",MethodType.methodType(void.class));
            Class<?> terrain=Class.forName("mobius.seedrenderer.dh.ClientTerrain",false,loader);
            var terrainLookup=MethodHandles.privateLookupIn(terrain,MethodHandles.lookup());
            queues=terrainLookup.findStaticGetter(terrain,"QUEUES",Map.class);
            forgetQueues=terrainLookup.findStatic(terrain,"forget",MethodType.methodType(void.class));
            Class<?> queue=Class.forName("mobius.seedrenderer.dh.SeedRetrievalQueue",false,loader);
            workers=MethodHandles.privateLookupIn(queue,MethodHandles.lookup()).findGetter(queue,"workers",ExecutorService.class);
            Class<?> minecraft=Class.forName("net.minecraft.client.Minecraft",false,loader);
            client=MethodHandles.publicLookup().findStatic(minecraft,"getInstance",MethodType.methodType(minecraft));
            currentThread=MethodHandles.publicLookup().findVirtual(minecraft,"isSameThread",MethodType.methodType(boolean.class));
            integrated=MethodHandles.publicLookup().findVirtual(minecraft,"hasSingleplayerServer",MethodType.methodType(boolean.class));
            Class<?> packetListener=Class.forName("net.minecraft.client.multiplayer.ClientPacketListener",false,loader);
            Class<?> connection=Class.forName("net.minecraft.network.Connection",false,loader);
            listener=MethodHandles.publicLookup().findVirtual(minecraft,"getConnection",MethodType.methodType(packetListener));
            network=MethodHandles.publicLookup().findVirtual(packetListener,"getConnection",MethodType.methodType(connection));
            connected=MethodHandles.publicLookup().findVirtual(connection,"isConnected",MethodType.methodType(boolean.class));
        }
        RegistryAccess.Frozen loaded(){return (RegistryAccess.Frozen)loaded.getVolatile();}
        @SuppressWarnings("unchecked") Registry<LevelStem> dimensions(){return (Registry<LevelStem>)stems.getVolatile();}
        boolean sharedEmpty()throws Throwable {Object value=shared.invoke();return value instanceof Map<?,?> map&&map.isEmpty();}
        RegistryAccess.Frozen attempt(boolean wholeSet)throws Throwable {return (RegistryAccess.Frozen)attempt.invokeExact(true,wholeSet);}
        String fingerprint(RegistryAccess access)throws Throwable {return (String)fingerprint.invokeExact(access);}
        void requireClientThread()throws Throwable {if(!(boolean)currentThread.invoke(client.invoke()))throw new IllegalStateException("Native world basis must initialize on the client thread");}
        boolean integratedServer()throws Throwable {return (boolean)integrated.invoke(client.invoke());}
        Object listener()throws Throwable {return listener.invoke(client.invoke());}
        boolean connected(Object value)throws Throwable {return value!=null&&(boolean)connected.invoke(network.invoke(value));}
        void forgetShared()throws Throwable {forgetShared.invokeExact();}
        List<ExecutorService> closeQueues()throws Throwable {
            Object value=queues.invoke();if(!(value instanceof Map<?,?> map)||map.size()>32)throw new IllegalStateException("Bounded native terrain queue map required");
            synchronized(map) {
                var captured=new ArrayList<ExecutorService>();
                for(Object queue:map.values())captured.add((ExecutorService)workers.invoke(queue));
                forgetQueues.invokeExact();
                if(!map.isEmpty())throw new IllegalStateException("Native queue cleanup did not empty its map");
                if(captured.stream().anyMatch(worker->!worker.isShutdown()))throw new IllegalStateException("Native queue close did not request executor shutdown");
                return List.copyOf(captured);
            }
        }
        void publishMetadata(Registry<LevelStem> selected,List<String> packNames) {
            stems.setVolatile(selected);names.setVolatile(packNames);
        }
        void publish(RegistryAccess.Frozen expected,RegistryAccess.Frozen fresh,Registry<LevelStem> selected,List<String> packNames) {
            Object previousStems=stems.getVolatile(),previousNames=names.getVolatile();
            if(loaded.getVolatile()!=expected)throw new IllegalStateException("Native cached registry changed before publication");
            publishMetadata(selected,packNames);
            if(!loaded.compareAndSet(expected,fresh)) {
                stems.compareAndSet(selected,previousStems);names.compareAndSet(packNames,previousNames);
                throw new IllegalStateException("Native cached registry changed; metadata rolled back and generation refused");
            }
        }
    }

    /** Native normal-preset bake retains explicit entries; no stale static registry. */
    static Registry<LevelStem> selectDimensions(RegistryAccess.Frozen actual,Registry<LevelStem> explicit) {
        if(explicit==null||explicit.size()>32)throw new IllegalStateException("Current bounded dimension definitions required");
        verifyCurrentHolders(actual,explicit);
        var normal=actual.registryOrThrow(Registries.WORLD_PRESET).getHolderOrThrow(WorldPresets.NORMAL).value();
        Registry<LevelStem> selected=normal.createWorldDimensions().bake(explicit).dimensions();
        if(selected.size()==0||selected.size()>32)throw new IllegalStateException("Current normal dimensions unavailable");
        verifyCurrentHolders(actual,selected);
        var overworld=selected.get(LevelStem.OVERWORLD);
        if(overworld==null||!(overworld.generator() instanceof NoiseBasedChunkGenerator generator)
                ||!generator.generatorSettings().is(NoiseGeneratorSettings.OVERWORLD))
            throw new IllegalStateException("Adapter requires the verified normal Overworld preset");
        return selected;
    }

    static void verifyCurrentHolders(RegistryAccess actual,Registry<LevelStem> selected) {
        Registry<NoiseGeneratorSettings> noise=actual.registryOrThrow(Registries.NOISE_SETTINGS);
        for(var stem:selected)if(stem.generator() instanceof NoiseBasedChunkGenerator generator) {
            if(!(generator.generatorSettings() instanceof Holder.Reference<NoiseGeneratorSettings> holder)
                    ||noise.getHolder(holder.key()).orElse(null)!=holder)
                throw new IllegalStateException("A dimension noise holder is not from the current private load");
        }
    }

    /** The managers need LEVEL_STEM. All other registry objects stay identical. */
    static RegistryAccess withDimensions(RegistryAccess actual,Registry<LevelStem> selected) {
        return new RegistryAccess.ImmutableRegistryAccess(Stream.concat(
            actual.registries().filter(r->!r.key().equals(Registries.LEVEL_STEM)),
            Stream.of(new RegistryAccess.RegistryEntry<>(Registries.LEVEL_STEM,selected))));
    }

    @FunctionalInterface interface RouterOperator {DensityFunction apply(int target,DensityFunction source);}
    static NoiseRouter mapRouter(NoiseRouter source,RouterOperator operator) {
        DensityFunction[] fields={source.barrierNoise(),source.fluidLevelFloodednessNoise(),source.fluidLevelSpreadNoise(),
            source.lavaNoise(),source.temperature(),source.vegetation(),source.continents(),source.erosion(),source.depth(),
            source.ridges(),source.initialDensityWithoutJaggedness(),source.finalDensity(),source.veinToggle(),source.veinRidged(),source.veinGap()};
        for(int n=0;n<fields.length;n++)fields[n]=java.util.Objects.requireNonNull(operator.apply(n,fields[n]));
        return new NoiseRouter(fields[0],fields[1],fields[2],fields[3],fields[4],fields[5],fields[6],fields[7],
            fields[8],fields[9],fields[10],fields[11],fields[12],fields[13],fields[14]);
    }

    private static Map<String,Member> captureMembers(RegistryAccess actual) {
        Map<String,Member> result=new LinkedHashMap<>();int count=0;
        var entries=actual.registries().toList();if(entries.size()>512)throw new IllegalStateException("Registry count exceeds bounded adapter");
        for(var entry:entries){count+=entry.value().size();if(count>65536)throw new IllegalStateException("Registry members exceed bounded adapter");
            result.put(entry.key().location().toString(),new Member(entry.value(),Set.copyOf(entry.value().keySet())));}
        return result;
    }
    private static void verifyMembers(RegistryAccess actual,Map<String,Member> before) {
        Map<String,Member> after=captureMembers(actual);
        if(!before.equals(after))throw new IllegalStateException("Native modifiers changed registry identity or member keys; preserve failed attempt");
    }

    private static void guardArtifact()throws Exception {
        var mod=ModList.get().getModContainerById("lithostitched").orElseThrow();
        var path=ModList.get().getModFileById("lithostitched").getFile().getFilePath();
        if(!"1.8.1".equals(mod.getModInfo().getVersion().toString())||Files.size(path)!=1023751L)
            throw new IllegalStateException("Exact Lithostitched 1.8.1 artifact required");
        try(InputStream stream=Files.newInputStream(path)){if(!JAR_SHA.equals(hash(stream,1023751)))throw new IllegalStateException("Pinned Lithostitched jar differs");}
        var seedgen=ModList.get().getModContainerById("seedrenderer").orElseThrow();
        var seedgenPath=ModList.get().getModFileById("seedrenderer").getFile().getFilePath();
        if(!"0.9.1".equals(seedgen.getModInfo().getVersion().toString())||Files.size(seedgenPath)!=1355029L)
            throw new IllegalStateException("Exact SeedGen 0.9.1 artifact required");
        try(InputStream stream=Files.newInputStream(seedgenPath)){if(!SEEDGEN_SHA.equals(hash(stream,1355029)))throw new IllegalStateException("Pinned SeedGen jar differs");}
        for(var entry:PINS.entrySet())try(InputStream stream=LithostitchedSeedgenCompat.class.getClassLoader().getResourceAsStream(entry.getKey())) {
            if(stream==null||!entry.getValue().equals(hash(stream,128*1024)))throw new IllegalStateException("Pinned native Lithostitched class resource differs: "+entry.getKey());
        }
    }
    private static String hash(InputStream stream,int cap)throws Exception {
        MessageDigest digest=MessageDigest.getInstance("SHA-256");byte[] buffer=new byte[8192];int total=0;
        for(int n;(n=stream.read(buffer))!=-1;){total+=n;if(total>cap)throw new IllegalStateException("Bounded native API resource exceeded");digest.update(buffer,0,n);}
        return HexFormat.of().formatHex(digest.digest());
    }
    private static RuntimeException propagate(Throwable failure) {
        if(failure instanceof Error error)throw error;
        return failure instanceof RuntimeException runtime?runtime:new IllegalStateException("Native Lithostitched client terrain initialization failed",failure);
    }
}
