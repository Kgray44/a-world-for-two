package worldfortwo.bridge;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.level.GameRules;
import net.neoforged.fml.common.Mod;
import net.neoforged.fml.loading.FMLPaths;
import net.neoforged.neoforge.common.NeoForge;
import net.neoforged.neoforge.event.server.ServerStartedEvent;
import net.neoforged.neoforge.event.server.ServerStoppedEvent;
import net.neoforged.neoforge.event.server.ServerStoppingEvent;
import net.neoforged.bus.api.IEventBus;
import net.neoforged.neoforge.event.tick.ServerTickEvent;
import java.lang.management.ManagementFactory;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.Map;

@Mod("awft_control_bridge")
public class ControlBridge {
    public static volatile boolean serverStarted = false;
    private static final Gson GSON = new GsonBuilder().create();
    private long beforeTick, lastSample = System.nanoTime(), tickNanos;
    private int ticks;
    private final PlayerSupport playerSupport = new PlayerSupport();
    private final AtlasSupport atlasSupport = new AtlasSupport();
    private final CinematicSupport cinematicSupport = new CinematicSupport();
    private final ChunkDiagnostics chunkDiagnostics = new ChunkDiagnostics();
    private final SettlementSupport settlementSupport = new SettlementSupport();
    private final EngineeringSupport engineeringSupport = new EngineeringSupport();
    private String operationOwner;
    private long operationGeneration;
    private final AttractionSupport attractionSupport=new AttractionSupport("0.1.0-candidate.38","0.6.24",this::acquire);
    private final HarborCraftSupport harborCraftSupport=new HarborCraftSupport("0.1.0-candidate.38","0.6.24",this::acquire);
    private final ArtisticEngineeringSupport artisticEngineeringSupport=new ArtisticEngineeringSupport("0.1.0-candidate.38","0.6.24",this::acquire);
    private final DragonTextureMirror dragonTextureMirror=new DragonTextureMirror();

    private final class WorldLease implements AttractionSupport.Lease,HarborCraftSupport.Lease,ArtisticEngineeringSupport.Lease {
        private final String owner;private final long generation;private boolean closed;
        WorldLease(String owner,long generation){this.owner=owner;this.generation=generation;}
        public boolean valid(){return !closed && generation==operationGeneration && owner.equals(operationOwner);}
        public void close(){if(closed)return;if(valid())operationOwner=null;closed=true;}
    }
    private WorldLease acquire(String owner,boolean temporarySimulation){
        if(operationOwner!=null || settlementSupport.busy() || engineeringSupport.busy())
            throw new IllegalStateException("Another native world operation or pending cleanup owns the world");
        operationOwner=owner;return new WorldLease(owner,++operationGeneration);
    }

    public ControlBridge(IEventBus modBus) {
        settlementSupport.admissionGate(()->operationOwner==null && !engineeringSupport.busy());
        engineeringSupport.admissionGate(()->operationOwner==null && !settlementSupport.busy());
        modBus.addListener(dragonTextureMirror::payloads);
        NeoForge.EVENT_BUS.addListener(dragonTextureMirror::sync);
        NeoForge.EVENT_BUS.addListener(this::started);
        NeoForge.EVENT_BUS.addListener(this::stopped);
        NeoForge.EVENT_BUS.addListener(this::stopping);
        NeoForge.EVENT_BUS.addListener(this::before);
        NeoForge.EVENT_BUS.addListener(this::after);
        NeoForge.EVENT_BUS.addListener(playerSupport::commands);
        NeoForge.EVENT_BUS.addListener(settlementSupport::commands);
        NeoForge.EVENT_BUS.addListener(engineeringSupport::commands);
        NeoForge.EVENT_BUS.addListener(attractionSupport::commands);
        NeoForge.EVENT_BUS.addListener(harborCraftSupport::commands);
        NeoForge.EVENT_BUS.addListener(artisticEngineeringSupport::commands);
        NeoForge.EVENT_BUS.addListener(atlasSupport::commands);
        NeoForge.EVENT_BUS.addListener(atlasSupport::chunk);
        NeoForge.EVENT_BUS.addListener(atlasSupport::joined);
        NeoForge.EVENT_BUS.addListener(atlasSupport::left);
        NeoForge.EVENT_BUS.addListener(atlasSupport::interacted);
        NeoForge.EVENT_BUS.addListener(atlasSupport::died);
        NeoForge.EVENT_BUS.addListener(cinematicSupport::commands);
        NeoForge.EVENT_BUS.addListener(cinematicSupport::joined);
        NeoForge.EVENT_BUS.addListener(cinematicSupport::left);
    }
    private void stopping(ServerStoppingEvent event){
        attractionSupport.stopped();harborCraftSupport.stopped();artisticEngineeringSupport.stop();
        engineeringSupport.stopped();settlementSupport.stopped();dragonTextureMirror.stopped();
    }
    private void started(ServerStartedEvent event) {
        serverStarted = true;
        chunkDiagnostics.invalidate();
        ticks = 0; tickNanos = 0; lastSample = System.nanoTime();
        // An explicit project default, applied once to new project worlds only.
        Path marker = FMLPaths.GAMEDIR.get().resolve("../dashboard/sleep-rule-initialized").normalize();
        if (!Files.exists(marker)) {
            event.getServer().getGameRules().getRule(GameRules.RULE_PLAYERS_SLEEPING_PERCENTAGE)
                    .set(50, event.getServer());
            try { Files.createDirectories(marker.getParent()); Files.writeString(marker, Instant.now().toString()); }
            catch (Exception error) { System.err.println("AWFT sleep marker: " + error.getMessage()); }
        }
    }
    private void stopped(ServerStoppedEvent event) { serverStarted = false; }
    private void before(ServerTickEvent.Pre event) { beforeTick = System.nanoTime(); }
    private void after(ServerTickEvent.Post event) {
        long now = System.nanoTime();
        if (serverStarted) {
            playerSupport.tick(event.getServer(), now - beforeTick);
            cinematicSupport.tick(event.getServer());
            settlementSupport.tick(event.getServer());
            engineeringSupport.tick(event.getServer());
            attractionSupport.tick(event.getServer());
            harborCraftSupport.tick(event.getServer());
            artisticEngineeringSupport.tick(event.getServer());
        }
        now = System.nanoTime();
        tickNanos += now - beforeTick;
        ticks++;
        if (now - lastSample < 5_000_000_000L) return;
        MinecraftServer server = event.getServer();
        Map<String, Object> data = new LinkedHashMap<>();
        data.put("format", "awft-metrics:1");
        data.put("at", Instant.now().toString());
        data.put("pid", ProcessHandle.current().pid());
        data.put("process_started", ProcessHandle.current().info().startInstant().orElse(Instant.EPOCH).toString());
        data.put("tps", ticks * 1_000_000_000.0 / (now - lastSample));
        data.put("mspt", tickNanos / 1_000_000.0 / ticks);
        data.put("ticks_sampled", ticks);
        data.put("interval_ms", (now - lastSample) / 1_000_000.0);
        var heap = ManagementFactory.getMemoryMXBean().getHeapMemoryUsage();
        data.put("heap_used", heap.getUsed()); data.put("heap_max", heap.getMax());
        long gcCount = 0, gcMillis = 0;
        for (var gc : ManagementFactory.getGarbageCollectorMXBeans()) {
            if (gc.getCollectionCount() >= 0) gcCount += gc.getCollectionCount();
            if (gc.getCollectionTime() >= 0) gcMillis += gc.getCollectionTime();
        }
        data.put("gc_collections", gcCount); data.put("gc_collection_ms", gcMillis);
        Map<String, Object> dimensions = new LinkedHashMap<>();
        int totalChunks = 0, totalEntities = 0;
        for (ServerLevel level : server.getAllLevels()) {
            int chunks = level.getChunkSource().getLoadedChunksCount();
            int entities = 0;
            for (var entity : level.getAllEntities()) entities++;
            dimensions.put(level.dimension().location().toString(), Map.of("loaded_chunks", chunks, "entities", entities,
                "idle_simulation", IdleSimulationState.sample(level)));
            totalChunks += chunks; totalEntities += entities;
        }
        data.put("loaded_chunks", totalChunks); data.put("entities", totalEntities);
        data.put("dimensions", dimensions);
        data.put("players", playerSupport.snapshot(server));
        data.put("capabilities", java.util.List.of("player_permissions", "player_locations", "surface_minimap", "safe_teleport", "surface_teleport", "atlas_index", "cinematics"));
        data.put("atlas", atlasSupport.snapshot(server, tickNanos / 1_000_000.0 / ticks));
        data.put("cinematics", cinematicSupport.snapshot(server));
        data.put("chunk_diagnostics", chunkDiagnostics.snapshot(server));
        data.put("minimap_last_work_ms", playerSupport.lastWorkMs());
        data.put("source", "Owned NeoForge server tick events and JVM management beans");
        Path target = FMLPaths.GAMEDIR.get().resolve("../dashboard/server-metrics.json").normalize();
        try {
            Files.createDirectories(target.getParent());
            Path temporary = target.resolveSibling("server-metrics.json.tmp");
            Files.writeString(temporary, GSON.toJson(data));
            Files.move(temporary, target, StandardCopyOption.REPLACE_EXISTING, StandardCopyOption.ATOMIC_MOVE);
        } catch (Exception error) { System.err.println("AWFT metrics write failed: " + error.getMessage()); }
        ticks = 0; tickNanos = 0; lastSample = now;
    }
}
