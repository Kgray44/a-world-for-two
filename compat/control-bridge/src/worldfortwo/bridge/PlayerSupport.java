package worldfortwo.bridge;

import com.mojang.authlib.GameProfile;
import com.mojang.brigadier.arguments.BoolArgumentType;
import com.mojang.brigadier.arguments.IntegerArgumentType;
import com.mojang.brigadier.arguments.StringArgumentType;
import net.minecraft.commands.Commands;
import net.minecraft.core.BlockPos;
import net.minecraft.network.chat.Component;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.server.players.ServerOpListEntry;
import net.minecraft.world.level.EmptyBlockGetter;
import net.minecraft.world.level.levelgen.Heightmap;
import net.neoforged.neoforge.event.RegisterCommandsEvent;
import java.time.Instant;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.UUID;

/** Local admin telemetry. Surface pixels come only from chunks already loaded. */
public final class PlayerSupport {
    private static final int WIDTH = 32, STEP = 4;
    private final Map<UUID, Map<String, Object>> maps = new LinkedHashMap<>();
    private final ArrayDeque<Tile> queue = new ArrayDeque<>();
    private long nextRefresh;
    private double lastWorkMs;
    private static final class Tile {
        final UUID player; final ServerLevel level; final int x, z;
        final int[] pixels = new int[WIDTH * WIDTH];
        int cursor;
        Tile(ServerPlayer player) {
            this.player = player.getUUID(); this.level = player.serverLevel();
            x = Math.floorDiv(player.getBlockX(), STEP) * STEP - WIDTH * STEP / 2;
            z = Math.floorDiv(player.getBlockZ(), STEP) * STEP - WIDTH * STEP / 2;
            Arrays.fill(pixels, -1);
        }
    }

    public void commands(RegisterCommandsEvent event) {
        // Only the local server console can use this helper. In-game permissions
        // keep vanilla's native semantics and cannot call the admin bridge.
        event.getDispatcher().register(Commands.literal("awft")
            .requires(source -> source.getEntity() == null && source.hasPermission(4))
            .then(Commands.literal("permissions")
                .then(Commands.argument("name", StringArgumentType.word())
                    .then(Commands.argument("uuid", StringArgumentType.word())
                        .then(Commands.argument("level", IntegerArgumentType.integer(0, 4))
                            .then(Commands.argument("bypass", BoolArgumentType.bool()).executes(context -> {
                                String name = StringArgumentType.getString(context, "name");
                                if (!name.matches("[A-Za-z0-9_]{1,16}")) return 0;
                                UUID uuid = UUID.fromString(StringArgumentType.getString(context, "uuid"));
                                int level = IntegerArgumentType.getInteger(context, "level");
                                boolean bypass = BoolArgumentType.getBool(context, "bypass");
                                MinecraftServer server = context.getSource().getServer();
                                GameProfile profile = new GameProfile(uuid, name);
                                var ops = server.getPlayerList().getOps();
                                if (level == 0) ops.remove(profile);
                                else ops.add(new ServerOpListEntry(profile, level, bypass));
                                try { ops.save(); }
                                catch (java.io.IOException error) {
                                    context.getSource().sendFailure(Component.literal("AWFT permission save failed: " + error.getMessage()));
                                    return 0;
                                }
                                ServerPlayer online = server.getPlayerList().getPlayer(uuid);
                                if (online != null) server.getPlayerList().sendPlayerPermissionLevel(online);
                                context.getSource().sendSuccess(() -> Component.literal("AWFT permissions saved for " + name + ": level " + level), true);
                                return 1;
                            })))))));
    }

    public void tick(MinecraftServer server, long tickNanos) {
        if (tickNanos > 50_000_000L) return; // Yield map work on an expensive tick.
        long started = System.nanoTime();
        if (queue.isEmpty() && started >= nextRefresh) {
            var online = server.getPlayerList().getPlayers();
            var ids = online.stream().map(ServerPlayer::getUUID).toList();
            maps.keySet().retainAll(ids);
            for (ServerPlayer player : online.stream().limit(8).toList()) queue.add(new Tile(player));
            nextRefresh = started + 10_000_000_000L;
        }
        int remaining = 48; // Global work budget, shared by every player.
        while (!queue.isEmpty() && remaining-- > 0 && System.nanoTime() - started < 750_000L) {
            Tile tile = queue.peek();
            if (server.getPlayerList().getPlayer(tile.player) == null) { queue.remove(); continue; }
            int index = tile.cursor++, x = tile.x + index % WIDTH * STEP, z = tile.z + index / WIDTH * STEP;
            // getChunkNow never loads or generates a chunk. Unknown pixels stay -1.
            var chunk = tile.level.getChunkSource().getChunkNow(Math.floorDiv(x, 16), Math.floorDiv(z, 16));
            if (chunk != null) {
                int y = chunk.getHeight(Heightmap.Types.WORLD_SURFACE, Math.floorMod(x, 16), Math.floorMod(z, 16));
                var state = chunk.getBlockState(new BlockPos(x, y, z));
                tile.pixels[index] = state.getMapColor(EmptyBlockGetter.INSTANCE, BlockPos.ZERO).col;
            }
            if (tile.cursor == tile.pixels.length) {
                Map<String, Object> map = new LinkedHashMap<>();
                map.put("at", Instant.now().toString());
                map.put("dimension", tile.level.dimension().location().toString());
                map.put("origin_x", tile.x); map.put("origin_z", tile.z);
                map.put("width", WIDTH); map.put("height", WIDTH); map.put("blocks_per_pixel", STEP);
                map.put("pixels", tile.pixels);
                map.put("source", "Actual loaded-chunk surface block map colors; north is up. No world generation.");
                maps.put(tile.player, map); queue.remove();
            }
        }
        lastWorkMs = (System.nanoTime() - started) / 1_000_000.0;
    }

    public Map<String, Object> snapshot(MinecraftServer server) {
        Map<String, Object> players = new LinkedHashMap<>();
        for (ServerPlayer player : server.getPlayerList().getPlayers().stream().limit(8).toList()) {
            Map<String, Object> data = new LinkedHashMap<>();
            data.put("name", player.getGameProfile().getName()); data.put("uuid", player.getUUID().toString());
            data.put("dimension", player.serverLevel().dimension().location().toString());
            data.put("x", player.getX()); data.put("y", player.getY()); data.put("z", player.getZ());
            data.put("yaw", player.getYRot()); data.put("health", player.getHealth());
            data.put("food", player.getFoodData().getFoodLevel()); data.put("xp_level", player.experienceLevel);
            data.put("game_mode", player.gameMode.getGameModeForPlayer().getName());
            if (maps.containsKey(player.getUUID())) data.put("map", maps.get(player.getUUID()));
            players.put(player.getUUID().toString(), data);
        }
        return players;
    }
    public double lastWorkMs() { return lastWorkMs; }
}
