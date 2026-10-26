package worldfortwo.bridge;

import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ChunkResult;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.GameRules;
import net.minecraft.world.level.chunk.LevelChunk;
import worldfortwo.bridge.mixin.ChunkMapAccess;
import worldfortwo.bridge.mixin.DistanceManagerAccess;
import java.time.Instant;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.lang.reflect.Field;

/** Read-only in-memory ticket diagnostics. No chunk queries, loads, or generation. */
public final class ChunkDiagnostics {
    private long next;
    private Map<String, Object> last = Map.of();
    private Field controllerId, ticketOwner;
    public void invalidate() { next = 0; }
    public Map<String, Object> snapshot(MinecraftServer server) {
        long now = System.nanoTime();
        if (now < next) return last;
        next = now + 30_000_000_000L;
        try { return measure(server); }
        catch (Throwable error) {
            last = Map.of("at", Instant.now().toString(), "unavailable", error.getClass().getSimpleName() + ": " + String.valueOf(error.getMessage()));
            return last;
        }
    }
    private Map<String, Object> measure(MinecraftServer server) {
        Map<String, Object> dimensions = new LinkedHashMap<>();
        for (ServerLevel level : server.getAllLevels()) {
            long begin = System.nanoTime();
            var cache = level.getChunkSource();
            var chunks = ((ChunkMapAccess) cache.chunkMap).awftVisibleChunks();
            var distance = cache.chunkMap.getDistanceManager();
            var tickets = ((DistanceManagerAccess) distance).awftTickets();
            int full = 0, blockTicking = 0, entityTicking = 0, examined = 0, ticketCount = 0;
            boolean truncated = false;
            Map<String, Integer> levels = new LinkedHashMap<>();
            Map<String, Map<String, Object>> sources = new LinkedHashMap<>();
            for (var entry : chunks.long2ObjectEntrySet()) {
                var holder = entry.getValue();
                ChunkResult<LevelChunk> loaded = holder.getFullChunkFuture().getNow(null);
                if (loaded != null && loaded.isSuccess()) full++;
                if (holder.getTickingChunk() != null && distance.inBlockTickingRange(entry.getLongKey())) blockTicking++;
                var entity = holder.getEntityTickingChunkFuture().getNow(null);
                if (entity != null && entity.isSuccess() && distance.inEntityTickingRange(entry.getLongKey())) entityTicking++;
                levels.merge(String.valueOf(holder.getTicketLevel()), 1, Integer::sum);
                examined++;
                if (examined >= 50000 || (examined % 64 == 0 && System.nanoTime() - begin > 5_000_000)) { truncated = true; break; }
            }
            outer: for (var entry : tickets.long2ObjectEntrySet()) for (var ticket : entry.getValue()) {
                String type = ticket.getType().toString();
                if (!sources.containsKey(type) && sources.size() >= 64) { truncated = true; break outer; }
                var source = sources.computeIfAbsent(type, unused -> {
                    Map<String, Object> row = new LinkedHashMap<>(); row.put("type", type); row.put("tickets", 0); row.put("examples", new ArrayList<>()); return row;
                });
                source.put("tickets", ((Integer) source.get("tickets")) + 1);
                @SuppressWarnings("unchecked") List<Map<String, Object>> examples = (List<Map<String, Object>>) source.get("examples");
                if (examples.size() < 3) {
                    ChunkPos position = new ChunkPos(entry.getLongKey());
                    String description = ticket.toString();
                    examples.add(Map.of("chunk_x", position.x, "chunk_z", position.z, "level", ticket.getTicketLevel(), "description", description.substring(0, Math.min(240, description.length()))));
                }
                ticketCount++;
                if (ticketCount >= 50000 || (ticketCount % 64 == 0 && System.nanoTime() - begin > 5_000_000)) { truncated = true; break outer; }
            }
            var details = new LinkedHashMap<String, Object>();
            details.put("sources", new ArrayList<>(sources.values())); details.put("ticket_levels", levels);
            details.put("truncated", truncated); details.put("mod_owners", modOwners(level));
            details.put("measurement_ms", (System.nanoTime() - begin) / 1_000_000.0);
            dimensions.put(level.dimension().location().toString(), Map.of("visible_holders", chunks.size(), "full_chunks", full,
                "block_ticking", blockTicking, "entity_ticking", entityTicking, "holders_examined", examined,
                "pending_unloads", ((ChunkMapAccess) cache.chunkMap).awftPendingUnloads().size(),
                "vanilla_forced_chunks", level.getForcedChunks().size(), "ticket_positions", tickets.size(),
                "details", details));
        }
        last = Map.of("at", Instant.now().toString(), "dimensions", dimensions,
            "spawn_chunk_radius", server.overworld().getGameRules().getInt(GameRules.RULE_SPAWN_CHUNK_RADIUS),
            "source", "Read-only Minecraft 1.21.1 visible holders, completed chunk futures, distance-manager ticking ranges and direct tickets. Ticket influence overlaps neighboring chunks; direct ticket counts are not an exclusive per-chunk attribution.");
        return last;
    }
    private Map<String, Object> modOwners(ServerLevel level) {
        List<Map<String, Object>> owners = new ArrayList<>();
        boolean truncated = false;
        try {
            var saved = level.getDataStorage().get(net.minecraft.world.level.ForcedChunksSavedData.factory(), "chunks");
            if (saved == null) return Map.of("owners", owners, "truncated", false);
            long deadline = System.nanoTime() + 2_000_000;
            for (String kind : List.of("Block", "Entity")) {
                // NeoForge adds these methods to Minecraft's saved-data class.
                Object tracker = saved.getClass().getMethod("get" + kind + "ForcedChunks").invoke(saved);
                var trackerClass = Class.forName("net.neoforged.neoforge.common.world.chunk.ForcedChunkManager$TicketTracker");
                for (String method : List.of("getChunks", "getTickingChunks")) {
                    Map<?, ?> entries = (Map<?, ?>) trackerClass.getMethod(method).invoke(tracker);
                    for (var entry : entries.entrySet()) {
                        if (owners.size() >= 64 || System.nanoTime() > deadline) { truncated = true; break; }
                        Object key = entry.getKey();
                        if (controllerId == null) {
                            controllerId = key.getClass().getDeclaredField("id"); controllerId.setAccessible(true);
                            ticketOwner = key.getClass().getDeclaredField("owner"); ticketOwner.setAccessible(true);
                        }
                        String owner = String.valueOf(ticketOwner.get(key));
                        owners.add(Map.of("controller", String.valueOf(controllerId.get(key)), "kind", kind.toLowerCase(),
                            "owner", owner.substring(0, Math.min(120, owner.length())), "ticking", method.equals("getTickingChunks"),
                            "chunks", ((it.unimi.dsi.fastutil.longs.LongSet) entry.getValue()).size()));
                    }
                }
            }
            return Map.of("owners", owners, "truncated", truncated);
        } catch (Throwable error) {
            return Map.of("owners", owners, "truncated", truncated, "unavailable", error.getClass().getSimpleName() + ": " + String.valueOf(error.getMessage()));
        }
    }
}
