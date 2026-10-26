package worldfortwo.bridge;

import com.google.gson.Gson;
import com.google.gson.reflect.TypeToken;
import com.mojang.brigadier.arguments.StringArgumentType;
import net.minecraft.commands.Commands;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerPlayer;
import net.neoforged.fml.loading.FMLPaths;
import net.neoforged.neoforge.event.RegisterCommandsEvent;
import net.neoforged.neoforge.event.entity.player.PlayerEvent;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.time.Instant;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

/** Uses Lumiera's commands and native registry; never moves the real player. */
public final class CinematicSupport {
    private static final Gson JSON = new Gson();
    private record Pending(int due, int expires) {}
    private final Map<UUID, Pending> pending = new LinkedHashMap<>();
    private final Map<UUID, Integer> activeUntil = new LinkedHashMap<>();
    private final Map<UUID, String> lastPosition = new LinkedHashMap<>();
    private final Map<String, Boolean> inside = new LinkedHashMap<>();
    private final Map<String, Integer> cooldown = new LinkedHashMap<>();
    private final List<Map<String, Object>> executions = new ArrayList<>();
    private Map<String, Object> config = Map.of("enabled", true, "first_join", true, "intro_scene", "awft:intro");
    private Map<String, String> seen = new LinkedHashMap<>();
    private boolean loaded;
    private long checked;
    private String configurationError;
    private static Path state() { return FMLPaths.GAMEDIR.get().resolve("../dashboard").normalize(); }

    private void load() {
        if (!loaded) {
            loaded = true;
            try {
                Path file = state().resolve("cinematic-first-joins.json");
                if (Files.exists(file) && Files.size(file) < 65536) {
                    Map<String, String> saved = JSON.fromJson(Files.readString(file), new TypeToken<Map<String, String>>() {}.getType());
                    if (saved != null && saved.size() <= 128) seen.putAll(saved);
                }
            } catch (Exception error) { configurationError = error.toString(); }
        }
        if (System.currentTimeMillis() - checked < 5000) return;
        checked = System.currentTimeMillis();
        Path file = state().resolve("cinematics.json");
        try {
            if (Files.exists(file)) {
                if (Files.size(file) > 65536) throw new IllegalArgumentException("Cinematic settings exceed 64 KiB");
                Map<String, Object> next = JSON.fromJson(Files.readString(file), new TypeToken<Map<String, Object>>() {}.getType());
                if (next == null || !(next.get("enabled") instanceof Boolean) || !(next.get("first_join") instanceof Boolean)) throw new IllegalArgumentException("Invalid cinematic settings");
                config = next;
            }
            configurationError = null;
        } catch (Exception error) { configurationError = error.toString(); config = Map.of("enabled", false, "first_join", false); }
    }
    public void joined(PlayerEvent.PlayerLoggedInEvent event) {
        if (event.getEntity() instanceof ServerPlayer player) {
            load();
            if (!seen.containsKey(player.getUUID().toString())) {
                int now = player.getServer().getTickCount();
                pending.put(player.getUUID(), new Pending(now + 100, now + 600));
            }
        }
    }
    public void left(PlayerEvent.PlayerLoggedOutEvent event) {
        UUID id = event.getEntity().getUUID();
        pending.remove(id); activeUntil.remove(id); lastPosition.remove(id);
        inside.keySet().removeIf(key -> key.startsWith(id.toString()));
        cooldown.keySet().removeIf(key -> key.startsWith(id.toString()));
    }
    private static boolean safe(ServerPlayer p) {
        return p.isAlive() && !p.isSleeping() && !p.isPassenger() && !p.isInWaterOrBubble() && !p.isInLava() && !p.isOnFire() && p.hurtTime == 0 && p.onGround();
    }
    private static Map<?, ?> registry() throws Exception {
        return (Map<?, ?>) Class.forName("dev.tysontheember.lumiera.cinematics.CinematicsRegistry").getMethod("all").invoke(null);
    }
    private int play(MinecraftServer server, ServerPlayer player, String scene, String reason) throws Exception {
        if (!Boolean.TRUE.equals(config.get("enabled"))) throw new IllegalArgumentException("Server-triggered cinematics are disabled");
        if (scene == null || !scene.matches("[a-z0-9_.-]+:[a-z0-9_/.-]+")) throw new IllegalArgumentException("Invalid scene identifier");
        if (!safe(player)) throw new IllegalArgumentException("The player must be safely standing, outside a vehicle, water, fire, or combat");
        Object cutscene = registry().get(ResourceLocation.parse(scene));
        if (cutscene == null) throw new IllegalArgumentException("Lumiera did not load this scene: " + scene);
        int duration = cutscene.getClass().getField("durationTicks").getInt(cutscene);
        if (duration < 1 || duration > 1200) throw new IllegalArgumentException("Server-triggered scenes must last at most one minute");
        int result = server.getCommands().getDispatcher().execute("lumiera cutscene play " + scene + " " + player.getGameProfile().getName(), server.createCommandSourceStack());
        if (result <= 0) throw new IllegalStateException("Lumiera refused the play command; inspect the console");
        activeUntil.put(player.getUUID(), server.getTickCount() + duration + 20);
        record(player.getGameProfile().getName(), scene, reason, "command accepted; client playback is not an acknowledgement");
        return duration;
    }
    public void tick(MinecraftServer server) {
        if (server.getTickCount() % 20 != 0) return;
        load();
        int now = server.getTickCount();
        for (var entry : new ArrayList<>(pending.entrySet())) {
            if (entry.getValue().due > now) continue;
            ServerPlayer player = server.getPlayerList().getPlayer(entry.getKey());
            if (player == null || entry.getValue().expires < now || !Boolean.TRUE.equals(config.get("first_join")) || !Boolean.TRUE.equals(config.get("enabled"))) { pending.remove(entry.getKey()); continue; }
            if (!safe(player)) continue;
            pending.remove(entry.getKey());
            String scene = String.valueOf(config.getOrDefault("intro_scene", "awft:intro"));
            try {
                if (seen.size() >= 128) throw new IllegalStateException("First-join history is full");
                play(server, player, scene, "first join");
                seen.put(player.getUUID().toString(), Instant.now().toString());
                write(state().resolve("cinematic-first-joins.json"), seen);
            } catch (Exception error) { record(player.getGameProfile().getName(), scene, "first join", "error: " + error.getMessage()); }
        }
        if (!Boolean.TRUE.equals(config.get("enabled"))) return;
        Object raw = config.get("triggers");
        if (!(raw instanceof List<?> triggers) || triggers.size() > 64) return;
        for (ServerPlayer player : server.getPlayerList().getPlayers()) {
            if (!safe(player) || activeUntil.getOrDefault(player.getUUID(), 0) > now) continue;
            String position = player.serverLevel().dimension().location() + ":" + player.blockPosition();
            if (position.equals(lastPosition.put(player.getUUID(), position))) continue;
            for (Object value : triggers) {
                if (!(value instanceof Map<?, ?> t) || !Boolean.TRUE.equals(t.get("enabled"))) continue;
                try {
                    String key = player.getUUID() + ":" + t.get("id");
                    double x = ((Number) t.get("x")).doubleValue(), z = ((Number) t.get("z")).doubleValue(), radius = ((Number) t.get("radius")).doubleValue();
                    if (!Double.isFinite(x) || !Double.isFinite(z) || !Double.isFinite(radius) || radius < 16 || radius > 128) continue;
                    boolean within = player.serverLevel().dimension().location().toString().equals(t.get("dimension")) && Math.pow(player.getX() - x, 2) + Math.pow(player.getZ() - z, 2) <= radius * radius;
                    if (t.get("y") instanceof Number height) within &= Double.isFinite(height.doubleValue()) && Math.abs(player.getY() - height.doubleValue()) <= radius;
                    boolean was = Boolean.TRUE.equals(inside.put(key, within));
                    if (!within || was || cooldown.getOrDefault(key, 0) > now) continue;
                    play(server, player, (String) t.get("scene"), "location trigger");
                    cooldown.put(key, now + 12000); // At least ten minutes between repeats.
                    break;
                } catch (Exception error) { record(player.getGameProfile().getName(), String.valueOf(t.get("scene")), "location trigger", "error: " + error.getMessage()); }
            }
        }
    }
    private void record(String player, String scene, String reason, String status) {
        executions.add(Map.of("at", Instant.now().toString(), "player", player, "scene", scene, "reason", reason, "status", status == null ? "unknown error" : status.substring(0, Math.min(300, status.length()))));
        if (executions.size() > 50) executions.remove(0);
        try { write(state().resolve("cinematic-executions.json"), executions); } catch (Exception error) { System.err.println("AWFT cinematic journal: " + error.getMessage()); }
    }
    public void commands(RegisterCommandsEvent event) {
        event.getDispatcher().register(Commands.literal("awft").requires(source -> source.getEntity() == null && source.hasPermission(4))
            .then(Commands.literal("cinematic").then(Commands.argument("request", StringArgumentType.word()).executes(context -> {
                String id = StringArgumentType.getString(context, "request");
                if (id.matches("[a-f0-9]{32}")) request(context.getSource().getServer(), id);
                return 1;
            }))));
    }
    private void request(MinecraftServer server, String id) {
        Path output = state().resolve("cinematic-requests/" + id + ".result.json");
        if (Files.exists(output)) return;
        Map<String, Object> result = new LinkedHashMap<>();
        try {
            load();
            Path input = state().resolve("cinematic-requests/" + id + ".json");
            if (!Files.isRegularFile(input) || Files.size(input) > 8192) throw new IllegalArgumentException("Missing or oversized request");
            Map<String, Object> data = JSON.fromJson(Files.readString(input), new TypeToken<Map<String, Object>>() {}.getType());
            long age = System.currentTimeMillis() - Instant.parse((String) data.get("at")).toEpochMilli();
            if (!id.equals(data.get("id")) || age < 0 || age > 30000) throw new IllegalArgumentException("Cinematic request expired");
            ServerPlayer player = server.getPlayerList().getPlayer(UUID.fromString((String) data.get("uuid")));
            if (player == null) throw new IllegalArgumentException("Selected player is offline");
            String action = (String) data.get("action");
            if ("play".equals(action)) play(server, player, (String) data.get("scene"), "Control Room replay");
            else if ("stop".equals(action) || "skip".equals(action)) {
                int accepted = server.getCommands().getDispatcher().execute("lumiera stop " + player.getGameProfile().getName(), server.createCommandSourceStack());
                if (accepted <= 0) throw new IllegalStateException("Lumiera refused the stop command");
                activeUntil.remove(player.getUUID());
                record(player.getGameProfile().getName(), "current", "Control Room", "stop command accepted");
            } else throw new IllegalArgumentException("Unsupported cinematic action");
            result.put("status", "command accepted");
        } catch (Exception error) { result.put("status", "refused"); result.put("error", String.valueOf(error.getMessage())); }
        result.put("at", Instant.now().toString());
        try { write(output, result); } catch (Exception error) { System.err.println("AWFT cinematic result: " + error.getMessage()); }
    }
    public Map<String, Object> snapshot(MinecraftServer server) {
        load();
        Map<String, Object> result = new LinkedHashMap<>();
        List<Map<String, Object>> scenes = new ArrayList<>();
        try {
            for (var entry : registry().entrySet()) {
                if (scenes.size() >= 64) break;
                Object scene = entry.getValue();
                scenes.add(Map.of("id", entry.getKey().toString(), "duration_ticks", scene.getClass().getField("durationTicks").getInt(scene),
                    "camera_mode", scene.getClass().getField("cameraPositionMode").get(scene).toString(), "events", ((List<?>) scene.getClass().getField("events").get(scene)).size()));
            }
            result.put("available", true);
        } catch (Exception error) { result.put("available", false); result.put("error", String.valueOf(error.getMessage())); }
        result.put("scenes", scenes); result.put("first_joins", seen); result.put("executions", executions);
        if (configurationError != null) result.put("configuration_error", configurationError);
        return result;
    }
    private static void write(Path path, Object value) throws Exception {
        Files.createDirectories(path.getParent()); Path temporary = path.resolveSibling(path.getFileName() + ".tmp");
        Files.writeString(temporary, JSON.toJson(value)); Files.move(temporary, path, StandardCopyOption.REPLACE_EXISTING, StandardCopyOption.ATOMIC_MOVE);
    }
}
