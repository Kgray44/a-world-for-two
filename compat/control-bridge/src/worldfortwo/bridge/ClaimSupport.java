package worldfortwo.bridge;

import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.MinecraftServer;
import net.minecraft.world.level.ChunkPos;
import java.lang.reflect.Method;
import java.time.Instant;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.stream.Stream;

/** Read-only OPAC 0.33.0 public API adapter. It never queries Minecraft chunks. */
public final class ClaimSupport {
    private static final Set<String> DIMENSIONS = Set.of("minecraft:overworld", "minecraft:the_nether", "minecraft:the_end");
    private static final int MAXIMUM = 2048;
    private Api api;
    private long sampled;
    private Map<String, Object> cached;

    private static final class Api {
        final Method get, manager, players, dimensions, lists, claim, positions, owner, forced, name, color;
        Api() throws ReflectiveOperationException {
            Class<?> entry = Class.forName("xaero.pac.common.server.api.OpenPACServerAPI");
            Class<?> claims = Class.forName("xaero.pac.common.server.claims.api.IServerClaimsManagerAPI");
            Class<?> player = Class.forName("xaero.pac.common.server.claims.player.api.IServerPlayerClaimInfoAPI");
            Class<?> dimension = Class.forName("xaero.pac.common.claims.player.api.IPlayerDimensionClaimsAPI");
            Class<?> list = Class.forName("xaero.pac.common.claims.player.api.IPlayerClaimPosListAPI");
            Class<?> state = Class.forName("xaero.pac.common.claims.player.api.IPlayerChunkClaimAPI");
            get = entry.getMethod("get", MinecraftServer.class);
            manager = entry.getMethod("getServerClaimsManager");
            players = claims.getMethod("getPlayerInfoStream");
            dimensions = player.getMethod("getStream");
            lists = dimension.getMethod("getStream");
            claim = list.getMethod("getClaimState");
            positions = list.getMethod("getStream");
            owner = state.getMethod("getPlayerId");
            forced = state.getMethod("isForceloadable");
            name = claims.getMethod("getFullName", state, ResourceLocation.class, boolean.class);
            color = claims.getMethod("getColor", state, ResourceLocation.class);
        }
    }

    public Map<String, Object> snapshot(MinecraftServer server) {
        long now = System.nanoTime();
        if (cached != null && now - sampled < 30_000_000_000L) return cached;
        Map<String, Object> result = new LinkedHashMap<>();
        List<Map<String, Object>> items = new ArrayList<>();
        result.put("at", Instant.now().toString());
        result.put("source", "Read-only Open Parties and Claims 0.33.0 public server API; claims do not imply loaded chunks.");
        boolean truncated = false;
        long begin = System.nanoTime();
        try {
            if (api == null) api = new Api();
            Object manager = api.manager.invoke(api.get.invoke(null, server));
            long deadline = System.nanoTime() + 5_000_000;
            int owners = 0;
            outer: try (Stream<?> players = (Stream<?>) api.players.invoke(manager)) {
                var playerIterator = players.iterator();
                while (playerIterator.hasNext()) {
                    if (++owners > 64 || System.nanoTime() > deadline) { truncated = true; break; }
                    Object player = playerIterator.next();
                    try (Stream<?> dimensions = (Stream<?>) api.dimensions.invoke(player)) {
                        var dimensionIterator = dimensions.iterator();
                        int dimensionCount = 0;
                        while (dimensionIterator.hasNext()) {
                            if (++dimensionCount > 128 || System.nanoTime() > deadline) { truncated = true; break outer; }
                            var dimensionEntry = (Map.Entry<?, ?>) dimensionIterator.next();
                            ResourceLocation dimension = (ResourceLocation) dimensionEntry.getKey();
                            if (!DIMENSIONS.contains(dimension.toString())) continue;
                            try (Stream<?> lists = (Stream<?>) api.lists.invoke(dimensionEntry.getValue())) {
                                var listIterator = lists.iterator();
                                int listCount = 0;
                                while (listIterator.hasNext()) {
                                    if (++listCount > 128 || System.nanoTime() > deadline) { truncated = true; break outer; }
                                    Object list = listIterator.next(), state = api.claim.invoke(list);
                                    String owner = api.owner.invoke(state).toString();
                                    String name = ((Component) api.name.invoke(manager, state, dimension, true)).getString().replaceAll("\\p{Cntrl}", "");
                                    if (name.length() > 80) name = name.substring(0, 80);
                                    String color = String.format("#%06x", ((Number) api.color.invoke(manager, state, dimension)).intValue() & 0xffffff);
                                    boolean forced = Boolean.TRUE.equals(api.forced.invoke(state));
                                    try (Stream<?> positions = (Stream<?>) api.positions.invoke(list)) {
                                        var positionIterator = positions.iterator();
                                        while (positionIterator.hasNext()) {
                                            if (items.size() >= MAXIMUM || (items.size() % 32 == 0 && System.nanoTime() > deadline)) { truncated = true; break outer; }
                                            ChunkPos pos = (ChunkPos) positionIterator.next();
                                            if (Math.abs((long) pos.x) > 1_875_000 || Math.abs((long) pos.z) > 1_875_000) continue;
                                            items.add(Map.of("dimension", dimension.toString(), "chunk_x", pos.x, "chunk_z", pos.z,
                                                "owner", owner, "name", name, "color", color, "forceloadable", forced));
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
            result.put("available", true);
        } catch (ReflectiveOperationException | LinkageError | RuntimeException error) {
            items.clear();
            result.put("available", false);
            Throwable cause = error.getCause() == null ? error : error.getCause();
            String message = cause.getClass().getSimpleName() + ": " + String.valueOf(cause.getMessage());
            result.put("unavailable", message.substring(0, Math.min(300, message.length())));
        }
        result.put("items", items);
        result.put("truncated", truncated);
        result.put("measurement_ms", Math.round((System.nanoTime() - begin) / 100.0) / 10000.0);
        sampled = now;
        cached = result;
        return result;
    }
}
