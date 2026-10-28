package worldfortwo.presentation;

import com.google.gson.Gson;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.components.AbstractWidget;
import net.minecraft.client.gui.screens.TitleScreen;
import net.neoforged.api.distmarker.Dist;
import net.neoforged.bus.api.EventPriority;
import net.neoforged.fml.common.Mod;
import net.neoforged.fml.ModList;
import net.neoforged.neoforge.common.NeoForge;
import net.neoforged.neoforge.client.event.ClientTickEvent;
import net.neoforged.neoforge.client.event.InputEvent;
import net.neoforged.neoforge.client.event.RenderFrameEvent;
import net.neoforged.neoforge.client.event.ScreenEvent;
import java.lang.management.ManagementFactory;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.nio.file.Files;
import java.nio.file.StandardCopyOption;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** Local presentation glue; never changes world contents or moves a player. */
@Mod(value="awft_client_presentation", dist=Dist.CLIENT)
public final class Presentation {
    private final Gson json = new Gson();
    private final double[] frames = new double[4096];
    private int frameCount, frameCursor;
    private long lastFrame, nextSample;
    private String camera = "player", integrationError;
    private final List<Map<String, String>> cameraEvents = new ArrayList<>();
    private final Map<String, Method> methods = new LinkedHashMap<>();
    private Object sequencer;
    private Field activeCutscene;
    private boolean initialized;

    public Presentation() {
        registerZiplineGraph();
        NeoForge.EVENT_BUS.addListener(EventPriority.HIGHEST, this::tick);
        NeoForge.EVENT_BUS.addListener(this::frame);
        NeoForge.EVENT_BUS.addListener(this::key);
    }
    private static void registerZiplineGraph() {
        if(!ModList.get().isLoaded("zipline")||!ModList.get().isLoaded("connectiblechains"))return;
        // FML4.0.45 waits on dependency constructor futures. The optional BEFORE
        // metadata makes this run before Zipline.init registers its stock curve.
        // Keep optional API classes out of this entrypoint's eager linkage.
        try {
            Class.forName("worldfortwo.presentation.LoadedChainGraphProvider",true,Presentation.class.getClassLoader())
                .getMethod("registerOnce").invoke(null);
        } catch(ReflectiveOperationException|LinkageError error) {
            throw new IllegalStateException("Pinned native chain handoff registration failed",error);
        }
    }
    public static void layoutControl(AbstractWidget control) {
        if (!(Minecraft.getInstance().screen instanceof TitleScreen title)) return;
        // Keep each original widget and its action, tooltip, and keyboard support.
        // Wide primary controls and FancyMenu's editor toolbar are untouched.
        int index = 0;
        for (var child : title.children()) if (child instanceof AbstractWidget widget && widget.visible
                && widget.getWidth() == widget.getHeight() && widget.getWidth() >= 16 && widget.getWidth() <= 24) {
            if (index >= 8) break;
            if (widget == control) {
                widget.setSize(18, 18);
                widget.setX(20 + index * 24);
                widget.setY(title.height - 28);
                return;
            }
            index++;
        }
    }
    private void initialize() throws Exception {
        if (initialized) return;
        bind("ambientActive", "com.ambientcamera.client.AmbientCameraClient", "isActive");
        bind("ambientStop", "com.ambientcamera.client.AmbientCameraClient", "markActivity");
        bind("respawn", "net.gamev.cinematic_respawn.client.RespawnCinematicController", "isActive");
        bind("respawnTransition", "net.gamev.cinematic_respawn.client.RespawnCinematicController", "isCameraTransitionActive");
        bind("interaction", "dev.dyslexic.cinematic.client.Scene", "active");
        Class<?> type = Class.forName("dev.tysontheember.lumiera.cinematics.CinematicsSequencer");
        sequencer = type.getField("INSTANCE").get(null);
        // The pinned alpha exposes cleanup commands but no public activity query.
        // Read only this exact field; an incompatible version disables idle shots.
        activeCutscene = type.getDeclaredField("activeCutscene");
        activeCutscene.setAccessible(true);
        methods.put("sceneAbort", type.getMethod("requestAbort"));
        methods.put("sceneSkip", type.getMethod("requestSkip"));
        initialized = true;
    }
    private void bind(String key, String type, String name) throws Exception {
        methods.put(key, Class.forName(type).getMethod(name));
    }
    private boolean active(String key) throws Exception { return Boolean.TRUE.equals(methods.get(key).invoke(null)); }
    private boolean sceneActive() throws Exception { return activeCutscene.get(sequencer) != null; }
    private void tick(ClientTickEvent.Pre event) {
        Minecraft mc = Minecraft.getInstance();
        try {
            initialize();
            boolean scene = sceneActive(), respawn = active("respawn") || active("respawnTransition"), interaction = active("interaction");
            var player = mc.player;
            boolean danger = player == null || !player.isAlive() || player.isPassenger() || player.isSleeping()
                || player.isInWaterOrBubble() || player.isInLava() || player.isOnFire() || player.hurtTime > 0
                || !player.onGround() || mc.screen != null;
            // Death and an actively used crafting scene take priority over an intro.
            if (scene && (respawn || interaction || player == null || !player.isAlive() || player.isPassenger()
                    || player.isInWaterOrBubble() || player.isInLava() || player.isOnFire() || player.hurtTime > 0)) {
                methods.get("sceneAbort").invoke(sequencer);
            }
            if (danger || scene || respawn || interaction) methods.get("ambientStop").invoke(null);
            String next = respawn ? "respawn" : interaction ? "interaction" : scene ? "lumiera" : active("ambientActive") ? "ambient" : "player";
            if (!next.equals(camera)) {
                cameraEvents.add(Map.of("at", Instant.now().toString(), "from", camera, "to", next));
                if (cameraEvents.size() > 50) cameraEvents.remove(0);
                camera = next;
            }
            integrationError = null;
        } catch (Throwable error) {
            integrationError = error.getClass().getSimpleName() + ": " + String.valueOf(error.getMessage());
            try { Class.forName("com.ambientcamera.client.AmbientCameraClient").getMethod("markActivity").invoke(null); }
            catch (Throwable ignored) { /* Native mod remains responsible for its own cleanup. */ }
        }
        long now = System.nanoTime();
        if (now >= nextSample) { nextSample = now + 5_000_000_000L; sample(mc); }
    }
    private void key(InputEvent.Key event) {
        // Escape uses Lumiera's cleanup path; no direct camera or player mutation.
        if (event.getKey() != 256 || event.getAction() != 1 || !initialized) return;
        try { if (sceneActive()) methods.get("sceneSkip").invoke(sequencer); }
        catch (Throwable error) { integrationError = "Skip failed: " + error.getClass().getSimpleName(); }
    }
    private void frame(RenderFrameEvent.Post event) {
        long now = System.nanoTime();
        if (lastFrame != 0) {
            frames[frameCursor] = (now - lastFrame) / 1_000_000.0;
            frameCursor = (frameCursor + 1) % frames.length;
            frameCount = Math.min(frames.length, frameCount + 1);
        }
        lastFrame = now;
    }
    private void sample(Minecraft mc) {
        Map<String, Object> data = new LinkedHashMap<>();
        var runtime = ManagementFactory.getRuntimeMXBean();
        var heap = ManagementFactory.getMemoryMXBean().getHeapMemoryUsage();
        data.put("format", "awft-client-metrics:1"); data.put("at", Instant.now().toString());
        data.put("pid", ProcessHandle.current().pid()); data.put("process_started", Instant.ofEpochMilli(runtime.getStartTime()).toString());
        data.put("fps", mc.getFps()); data.put("focused", mc.isWindowActive());
        data.put("heap_used", heap.getUsed()); data.put("heap_max", heap.getMax());
        data.put("in_world", mc.level != null && mc.player != null);
        data.put("screen", mc.screen == null ? "game" : mc.screen.getClass().getSimpleName());
        data.put("camera", camera); data.put("camera_events", cameraEvents);
        if (integrationError != null) data.put("integration_error", integrationError.substring(0, Math.min(300, integrationError.length())));
        if (mc.player != null) data.put("player", Map.of("uuid", mc.player.getUUID().toString(), "dimension", mc.player.level().dimension().location().toString(),
            "x", mc.player.getX(), "y", mc.player.getY(), "z", mc.player.getZ(), "riding", mc.player.isPassenger(), "alive", mc.player.isAlive()));
        if (frameCount > 0) {
            double[] sorted = Arrays.copyOf(frames, frameCount); Arrays.sort(sorted);
            data.put("frame_interval_ms", Map.of("samples", frameCount, "mean", Arrays.stream(sorted).average().orElse(0),
                "p50", sorted[(frameCount - 1) / 2], "p95", sorted[(int) Math.floor((frameCount - 1) * .95)], "max", sorted[frameCount - 1]));
        }
        frameCount = frameCursor = 0;
        // Only one bounded snapshot and its atomic temporary file; no growing log.
        try {
            var output = mc.gameDirectory.toPath().resolve("awft-client-metrics.json");
            var temporary = output.resolveSibling("awft-client-metrics.json.tmp");
            Files.writeString(temporary, json.toJson(data));
            Files.move(temporary, output, StandardCopyOption.REPLACE_EXISTING, StandardCopyOption.ATOMIC_MOVE);
        } catch (Exception error) { System.err.println("AWFT local client measurements: " + error.getClass().getSimpleName()); }
    }
}
