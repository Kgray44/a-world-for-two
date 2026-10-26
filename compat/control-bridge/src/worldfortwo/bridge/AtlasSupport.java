package worldfortwo.bridge;

import com.google.gson.Gson;
import com.google.gson.reflect.TypeToken;
import com.mojang.brigadier.arguments.StringArgumentType;
import net.minecraft.commands.Commands;
import net.minecraft.core.BlockPos;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.core.registries.Registries;
import net.minecraft.resources.ResourceKey;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.TamableAnimal;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.levelgen.Heightmap;
import net.minecraft.world.phys.AABB;
import net.neoforged.fml.loading.FMLPaths;
import net.neoforged.neoforge.event.RegisterCommandsEvent;
import net.neoforged.neoforge.event.entity.EntityJoinLevelEvent;
import net.neoforged.neoforge.event.entity.EntityLeaveLevelEvent;
import net.neoforged.neoforge.event.entity.living.LivingDeathEvent;
import net.neoforged.neoforge.event.entity.player.PlayerInteractEvent;
import net.neoforged.neoforge.event.level.ChunkEvent;
import java.lang.management.ManagementFactory;
import java.lang.ref.WeakReference;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Collection;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;

/** Event-based known-location index and explicitly requested, bounded teleports. */
public final class AtlasSupport {
    private static final Gson JSON = new Gson();
    private final Map<UUID, WeakReference<Entity>> tracked = new LinkedHashMap<>();
    private final Map<String, Map<String, Object>> known = new LinkedHashMap<>();
    private final Map<UUID, Long> lastTeleport = new LinkedHashMap<>();
    private final ClaimSupport claims = new ClaimSupport();
    private boolean indexLoaded, indexFull, overloaded, indexDirty;
    private long lastCpu, lastCpuAt;
    private static Path state() { return FMLPaths.GAMEDIR.get().resolve("../dashboard").normalize(); }
    private static boolean mapped(ServerLevel level) {
        String id = level.dimension().location().toString();
        return Set.of("minecraft:overworld", "minecraft:the_nether", "minecraft:the_end").contains(id);
    }
    private synchronized void loadIndex() {
        if (indexLoaded) return;
        indexLoaded = true;
        Path file = state().resolve("bridge-atlas-index.json");
        try {
            if (Files.isRegularFile(file) && Files.size(file) < 1024 * 1024) {
                Map<String, Map<String, Object>> saved = JSON.fromJson(Files.readString(file), new TypeToken<Map<String, Map<String, Object>>>() {}.getType());
                if (saved != null && saved.size() <= 2000) known.putAll(saved);
            }
        } catch (Exception error) { System.err.println("AWFT atlas index read: " + error.getMessage()); }
    }
    private synchronized void remember(Map<String, Object> value) {
        loadIndex();
        String id = (String) value.get("id");
        if (known.size() >= 2000 && !known.containsKey(id)) { indexFull = true; return; }
        Map<String, Object> previous = known.get(id);
        if ("structure".equals(value.get("kind"))) {
            value.put("last_seen", value.get("at"));
            if (previous != null && previous.containsKey("at")) value.put("at", previous.get("at"));
        }
        known.put(id, value);
        indexDirty = true;
    }
    private Map<String, Object> location(String id, String name, String kind, ServerLevel level, double x, double y, double z) {
        Map<String, Object> value = new LinkedHashMap<>();
        name = name.replaceAll("\\p{Cntrl}", "");
        value.put("id", id); value.put("name", name.length() > 80 ? name.substring(0, 80) : name);
        value.put("kind", kind); value.put("dimension", level.dimension().location().toString());
        value.put("x", x); value.put("y", y); value.put("z", z); value.put("at", Instant.now().toString());
        return value;
    }
    public void chunk(ChunkEvent.Load event) {
        if (!(event.getLevel() instanceof ServerLevel level) || !mapped(level)) return;
        // Inspect starts in this loaded chunk only. No locate search or chunk generation.
        var registry = level.registryAccess().registryOrThrow(Registries.STRUCTURE);
        event.getChunk().getAllStarts().forEach((structure, start) -> {
            if (!start.isValid()) return;
            var pos = start.getBoundingBox().getCenter();
            String type = String.valueOf(registry.getKey(structure));
            String id = "structure:" + level.dimension().location() + ":" + type + ":" + start.getChunkPos().toLong();
            var value = location(id, type, "structure", level, pos.getX(), pos.getY(), pos.getZ());
            value.put("type", type);
            value.put("evidence", "Valid structure start in an actually loaded/generated chunk; visitation is not inferred.");
            remember(value);
        });
    }
    private void track(Entity entity) {
        if (!(entity.level() instanceof ServerLevel level) || !mapped(level) || entity instanceof ServerPlayer) return;
        if (tracked.size() < 256 || tracked.containsKey(entity.getUUID())) tracked.put(entity.getUUID(), new WeakReference<>(entity));
    }
    public void joined(EntityJoinLevelEvent event) {
        var entity = event.getEntity();
        String type = BuiltInRegistries.ENTITY_TYPE.getKey(entity.getType()).toString();
        if (entity instanceof TamableAnimal || entity.hasCustomName() || type.contains("ship") || type.contains("contraption") || type.startsWith("whaleborne:")) track(entity);
    }
    public void interacted(PlayerInteractEvent.EntityInteract event) { track(event.getTarget()); }
    public void left(EntityLeaveLevelEvent event) {
        Entity entity = event.getEntity();
        if (tracked.containsKey(entity.getUUID()) && entity.level() instanceof ServerLevel level && mapped(level))
            remember(location("entity:" + entity.getUUID(), entity.getDisplayName().getString(), "known object", level, entity.getX(), entity.getY(), entity.getZ()));
        tracked.remove(entity.getUUID());
    }
    public void died(LivingDeathEvent event) {
        if (!(event.getEntity() instanceof ServerPlayer player) || !mapped(player.serverLevel())) return;
        remember(location("death:" + player.getUUID() + ":" + System.currentTimeMillis(), player.getGameProfile().getName() + " death", "death", player.serverLevel(), player.getX(), player.getY(), player.getZ()));
    }
    public void commands(RegisterCommandsEvent event) {
        event.getDispatcher().register(Commands.literal("awft")
            .requires(source -> source.getEntity() == null && source.hasPermission(4))
            .then(Commands.literal("teleport").then(Commands.argument("request", StringArgumentType.word()).executes(context -> {
                String id = StringArgumentType.getString(context, "request");
                if (!id.matches("[a-f0-9]{32}")) return 0;
                teleport(context.getSource().getServer(), id);
                return 1;
            }))));
    }
    private void teleport(MinecraftServer server, String id) {
        Path request = state().resolve("atlas-requests/" + id + ".json");
        Path result = state().resolve("atlas-requests/" + id + ".result.json");
        if (Files.exists(result)) return; // Idempotent: never replay a completed request.
        Map<String, Object> response = new LinkedHashMap<>();
        try {
            if (!Files.isRegularFile(request) || Files.size(request) > 8192) throw new IllegalArgumentException("Missing or oversized teleport request");
            Map<String, Object> data = JSON.fromJson(Files.readString(request), new TypeToken<Map<String, Object>>() {}.getType());
            long age = System.currentTimeMillis() - Instant.parse((String) data.get("at")).toEpochMilli();
            if (!id.equals(data.get("id")) || age < 0 || age > 30_000) throw new IllegalArgumentException("Teleport request expired");
            UUID uuid = UUID.fromString((String) data.get("uuid"));
            ServerPlayer player = server.getPlayerList().getPlayer(uuid);
            if (player == null || !player.getGameProfile().getName().equals(data.get("name"))) throw new IllegalArgumentException("The selected player is no longer online");
            if (player.isDeadOrDying() || player.isSleeping() || player.isPassenger()) throw new IllegalArgumentException("Leave the vehicle, bed, or death screen before teleporting");
            if (System.currentTimeMillis() - lastTeleport.getOrDefault(uuid, 0L) < 5000) throw new IllegalArgumentException("Wait five seconds between teleports");
            Path returns = state().resolve("atlas-returns.json");
            Map<String, Map<String, Object>> previous = new LinkedHashMap<>();
            if (Files.exists(returns) && Files.size(returns) < 65536) previous.putAll(JSON.fromJson(Files.readString(returns), new TypeToken<Map<String, Map<String, Object>>>() {}.getType()));
            @SuppressWarnings("unchecked") Map<String, Object> dest = (Map<String, Object>) data.get("destination");
            if (Boolean.TRUE.equals(dest.get("return"))) dest = previous.get(uuid.toString());
            if (dest == null) throw new IllegalArgumentException("No previous position is saved for this player");
            ResourceLocation dimension = ResourceLocation.parse((String) dest.get("dimension"));
            ServerLevel level = server.getLevel(ResourceKey.create(Registries.DIMENSION, dimension));
            if (level == null || !mapped(level)) throw new IllegalArgumentException("Destination dimension is unavailable");
            double x = ((Number) dest.get("x")).doubleValue(), z = ((Number) dest.get("z")).doubleValue();
            if (!Double.isFinite(x) || !Double.isFinite(z) || Math.abs(x) > 29_999_984 || Math.abs(z) > 29_999_984) throw new IllegalArgumentException("Destination exceeds world limits");
            int bx = (int) Math.floor(x), bz = (int) Math.floor(z);
            if (!level.getWorldBorder().isWithinBounds(new BlockPos(bx, 64, bz))) throw new IllegalArgumentException("Destination is outside the world border");
            // Only this explicit administrator action may load one destination chunk.
            level.getChunk(bx >> 4, bz >> 4);
            Number requestedY = (Number) dest.get("y");
            if (requestedY != null && (!Double.isFinite(requestedY.doubleValue()) || requestedY.doubleValue() < level.getMinBuildHeight() + 1 || requestedY.doubleValue() > level.getMaxBuildHeight() - 2))
                throw new IllegalArgumentException("Destination height is outside this dimension");
            String landingMode = dest.get("landing") instanceof String value ? value : requestedY == null ? "surface" : "near-y";
            SafeLanding.Result landing = SafeLanding.find(level, player, bx, bz, requestedY, landingMode);
            response.put("landing_mode", landingMode); response.put("columns_checked", landing.columns()); response.put("safety_refusals", landing.refusals());
            BlockPos safe = landing.position();
            if (safe == null) throw new IllegalArgumentException("No safe dry landing within eight horizontal blocks inside the destination chunk. Checks: " + landing.refusals()
                + (landingMode.equals("near-y") ? ". Try surface landing for an outdoor map location." : ". Choose a nearby land tile; water, lava and obstructed ground remain unsafe."));
            var old = location("return:" + uuid, player.getGameProfile().getName(), "return", player.serverLevel(), player.getX(), player.getY(), player.getZ());
            previous.put(uuid.toString(), old); write(returns, previous);
            player.teleportTo(level, safe.getX() + .5, safe.getY(), safe.getZ() + .5, Set.of(), player.getYRot(), player.getXRot());
            player.fallDistance = 0; player.setDeltaMovement(net.minecraft.world.phys.Vec3.ZERO);
            lastTeleport.put(uuid, System.currentTimeMillis());
            response.put("status", "complete"); response.put("destination", location(id, "Validated destination", "teleport", level, safe.getX() + .5, safe.getY(), safe.getZ() + .5));
            response.put("previous", old); response.put("destination_chunk_requests", 1);
        } catch (Exception error) { response.put("status", "refused"); response.put("error", error.getMessage() == null ? error.getClass().getSimpleName() : error.getMessage()); }
        response.put("at", Instant.now().toString());
        try { write(result, response); } catch (Exception error) { System.err.println("AWFT teleport result: " + error.getMessage()); }
    }
    private static void write(Path path, Object value) throws java.io.IOException {
        Files.createDirectories(path.getParent());
        Path temporary = path.resolveSibling(path.getFileName() + ".tmp");
        Files.writeString(temporary, JSON.toJson(value));
        Files.move(temporary, path, StandardCopyOption.REPLACE_EXISTING, StandardCopyOption.ATOMIC_MOVE);
    }
    public synchronized Map<String, Object> snapshot(MinecraftServer server, double mspt) {
        loadIndex();
        List<Map<String, Object>> objects = new ArrayList<>();
        tracked.entrySet().removeIf(entry -> entry.getValue().get() == null || entry.getValue().get().isRemoved());
        for (var reference : tracked.values()) {
            Entity entity = reference.get();
            if (entity == null || !(entity.level() instanceof ServerLevel level) || !mapped(level)) continue;
            boolean pet = entity instanceof TamableAnimal animal && animal.isTame();
            String type = BuiltInRegistries.ENTITY_TYPE.getKey(entity.getType()).toString();
            boolean vehicle = type.contains("ship") || type.contains("contraption") || type.startsWith("whaleborne:");
            if (!pet && !vehicle && !entity.hasCustomName()) continue;
            var value = location("entity:" + entity.getUUID(), entity.getDisplayName().getString(), pet ? "pet" : vehicle ? "vehicle" : "named entity", level, entity.getX(), entity.getY(), entity.getZ());
            value.put("type", type); value.put("yaw", entity.getYRot()); value.put("state", "loaded"); objects.add(value);
        }
        try { if (indexDirty) { write(state().resolve("bridge-atlas-index.json"), known); indexDirty = false; } }
        catch (Exception error) { System.err.println("AWFT atlas index save: " + error.getMessage()); }
        return Map.of("objects", objects, "locations", new ArrayList<>(known.values()), "index_full", indexFull, "renderer", renderer(mspt), "claims", claims.snapshot(server));
    }
    private Map<String, Object> renderer(double mspt) {
        Map<String, Object> result = new LinkedHashMap<>();
        try {
            Map<String, Object> controls = Map.of();
            Path file = state().resolve("atlas-control.json");
            if (Files.exists(file) && Files.size(file) < 8192) controls = JSON.fromJson(Files.readString(file), new TypeToken<Map<String, Object>>() {}.getType());
            if (mspt > 45) overloaded = true; else if (mspt < 35) overloaded = false;
            boolean pause = Boolean.TRUE.equals(controls.get("paused")) || overloaded;
            Object api = Class.forName("xyz.jpenilla.squaremap.api.SquaremapProvider").getMethod("get").invoke(null);
            Collection<?> worlds = (Collection<?>) Class.forName("xyz.jpenilla.squaremap.api.Squaremap").getMethod("mapWorlds").invoke(api);
            int queue = 0;
            Class<?> mapWorld = Class.forName("xyz.jpenilla.squaremap.common.data.MapWorldInternal");
            var modified = mapWorld.getDeclaredField("modifiedChunks"); modified.setAccessible(true);
            int budget = controls.get("chunks_per_interval") instanceof Number n ? Math.max(1, Math.min(64, n.intValue())) : 32;
            for (Object world : worlds) {
                Object manager = mapWorld.getMethod("renderManager").invoke(world);
                manager.getClass().getMethod("pauseRenders", boolean.class).invoke(manager, pause);
                Object config = mapWorld.getMethod("config").invoke(world);
                config.getClass().getField("BACKGROUND_RENDER_MAX_CHUNKS_PER_INTERVAL").setInt(config, budget);
                queue += ((Collection<?>) modified.get(world)).size();
            }
            result.put("paused", pause); result.put("overloaded", overloaded); result.put("queued_chunks", queue); result.put("worlds", worlds.size()); result.put("chunks_per_interval", budget);
            var threads = ManagementFactory.getThreadMXBean();
            if (threads.isThreadCpuTimeSupported() && !threads.isThreadCpuTimeEnabled()) threads.setThreadCpuTimeEnabled(true);
            long cpu = 0, now = System.nanoTime();
            for (long id : threads.getAllThreadIds()) {
                var info = threads.getThreadInfo(id);
                if (info != null && info.getThreadName().toLowerCase().contains("squaremap")) cpu += Math.max(0, threads.getThreadCpuTime(id));
            }
            if (lastCpuAt != 0 && cpu >= lastCpu) result.put("cpu_percent_one_core", (cpu - lastCpu) * 100.0 / (now - lastCpuAt));
            lastCpu = cpu; lastCpuAt = now;
            result.put("source", "Pinned squaremap 1.3.2 API/internal queue adapter and JVM thread CPU counters");
        } catch (Throwable error) { result.put("unavailable", error.getClass().getSimpleName() + ": " + String.valueOf(error.getMessage())); }
        return result;
    }
}
