package worldfortwo.qa;

import com.volcanicmg.maphorizons.client.Diagnostics;
import com.volcanicmg.maphorizons.client.ShareFetch;
import java.lang.invoke.MethodHandle;
import java.lang.invoke.MethodHandles;
import java.lang.invoke.MethodType;
import java.lang.invoke.VarHandle;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Objects;
import java.util.UUID;
import net.minecraft.client.Minecraft;
import net.minecraft.resources.ResourceKey;
import net.minecraft.world.level.Level;
import xaero.map.MapProcessor;
import xaero.map.WorldMapSession;
import xaero.map.gui.GuiMap;
import xaero.map.world.MapDimension;
import xaero.map.world.MapWorld;

/** Test-only native map view. No event listener, Mod entrypoint, renderer or file writer.
 * Invoke only AFTER the parent's existing nonce/owner/request/lifecycle checks.
 * These exact named accesses are pinned to Xaero World Map 1.47.0. Native use pending.
 */
public final class NativeXaeroView {
    public static final String WORLD_MAP_SHA256 = "6a42b6f01bd96b496e5fcc07d4541bad1a699d9ec8ad58ad40d5dcfe23a7d4c7";
    private static final VarHandle CAMERA_X, CAMERA_Z, RESET, DESTINATION, ATTACHED, DEST_SCALE, SCALE, SCREEN_SCALE;
    private static final MethodHandle CHANGE_ZOOM;
    static {
        try {
            var lookup = MethodHandles.privateLookupIn(GuiMap.class, MethodHandles.lookup());
            CAMERA_X = lookup.findVarHandle(GuiMap.class, "cameraX", double.class);
            CAMERA_Z = lookup.findVarHandle(GuiMap.class, "cameraZ", double.class);
            RESET = lookup.findVarHandle(GuiMap.class, "shouldResetCameraPos", boolean.class);
            DESTINATION = lookup.findVarHandle(GuiMap.class, "cameraDestination", int[].class);
            ATTACHED = lookup.findStaticVarHandle(GuiMap.class, "attachedCamera", boolean.class);
            DEST_SCALE = lookup.findStaticVarHandle(GuiMap.class, "destScale", double.class);
            SCALE = lookup.findVarHandle(GuiMap.class, "scale", double.class);
            SCREEN_SCALE = lookup.findVarHandle(GuiMap.class, "screenScale", double.class);
            CHANGE_ZOOM = lookup.findVirtual(GuiMap.class, "changeZoom", MethodType.methodType(void.class, double.class, int.class));
        } catch (ReflectiveOperationException e) { throw new ExceptionInInitializerError(e); }
    }

    private final UUID owner;
    private GuiMap screen;
    private WorldMapSession session;
    private MapWorld world;
    private ResourceKey<Level> requestedDimension, previousDimension;
    private boolean previousAttached;
    private double previousZoom;
    private int openings;

    public NativeXaeroView(UUID owner) { this.owner = Objects.requireNonNull(owner); }

    public boolean owns(Minecraft mc) {
        return screen!=null && mc.screen==screen && mc.isSameThread() && mc.isGameLoadFinished()
            && mc.getOverlay()==null && mc.player!=null && mc.level!=null && mc.getConnection()!=null
            && mc.getCurrentServer()!=null && "127.0.0.1:25575".equals(mc.getCurrentServer().ip)
            && owner.equals(mc.getUser().getProfileId()) && owner.equals(mc.player.getUUID())
            && WorldMapSession.getCurrentSession()==session && session.isUsable()
            && session.getMapProcessor().getMapWorld()==world;
    }

    private void requireOwner(Minecraft mc) {
        if (!mc.isSameThread() || !mc.isGameLoadFinished() || mc.getOverlay() != null
                || mc.player == null || mc.level == null || mc.getConnection() == null
                || mc.getCurrentServer() == null || !"127.0.0.1:25575".equals(mc.getCurrentServer().ip)
                || !owner.equals(mc.getUser().getProfileId()) || !owner.equals(mc.player.getUUID()))
            throw new IllegalStateException("Ready, authenticated owner on loopback staging is required");
    }

    private GuiMap requireOpen(Minecraft mc) {
        requireOwner(mc);
        if (screen == null || mc.screen != screen || WorldMapSession.getCurrentSession() != session
                || !session.isUsable() || session.getMapProcessor().getMapWorld() != world)
            throw new IllegalStateException("The exact owned map screen/session is no longer active");
        return screen;
    }

    /** Constructs the same native screen as Xaero's normal keyDown path.
     * Selecting a map dimension is not a player teleport. Unknown dimensions fail.
     */
    public Map<String, Object> open(Minecraft mc, ResourceKey<Level> dimension) {
        requireOwner(mc);
        // The player may have closed the map normally. Never restore or close an
        // unrelated screen/session merely because an old helper reference exists.
        if(screen!=null && mc.screen!=screen) { screen=null;session=null;world=null; }
        if (screen != null || mc.screen != null || openings >= 12)
            throw new IllegalStateException("No other UI may be open; at most 12 map openings per helper");
        var active = WorldMapSession.getCurrentSession();
        if (active == null || !active.isUsable()) throw new IllegalStateException("Xaero session unavailable");
        MapProcessor processor = active.getMapProcessor();
        MapWorld mapWorld = processor.getMapWorld();
        if (!processor.isMapWorldUsable() || mapWorld == null || mapWorld.getDimension(dimension) == null)
            throw new IllegalArgumentException("Requested dimension is absent from the existing Xaero session");
        session = active; world = mapWorld; requestedDimension = dimension;
        previousDimension = world.getCustomDimensionId();
        previousAttached = (boolean) ATTACHED.get(); previousZoom = (double) DEST_SCALE.get();
        try {
            world.setCustomDimensionId(dimension.equals(mc.level.dimension()) ? null : dimension);
            processor.checkForWorldUpdate(); // Same path as the native dimension toggle.
            screen = new GuiMap(null, null, processor, mc.getCameraEntity());
            mc.setScreen(screen); openings++;
            return snapshot(mc);
        } catch(RuntimeException | Error failure) {
            // A failed constructor/init must not leave our temporary selection.
            // Roll back only while the same authenticated native session remains.
            if(WorldMapSession.getCurrentSession()==session && processor.getMapWorld()==world
                    && (mc.screen==null || mc.screen==screen)) {
                try {
                    ATTACHED.set(previousAttached); DEST_SCALE.set(previousZoom);
                    world.setCustomDimensionId(previousDimension);processor.checkForWorldUpdate();
                    if(screen!=null && mc.screen==screen)mc.setScreen(null);
                } catch(RuntimeException | Error cleanup) { failure.addSuppressed(cleanup); }
            }
            screen=null;session=null;world=null;throw failure;
        }
    }

    /** An explicitly requested view change, never a recurring camera override.
     * Native changeZoom applies the author's bounds/animation; mode 1 is button-style
     * center zoom rather than pointer-anchored scrolling. No world or discovery call.
     */
    public Map<String, Object> setView(Minecraft mc, double x, double z, double zoom) throws Throwable {
        GuiMap map = requireOpen(mc);
        MapDimension viewed = map.getDimensionOnInit();
        if (viewed == null || !requestedDimension.equals(viewed.getDimId())
                || !requestedDimension.equals(world.getCurrentDimensionId())
                || map.getMapProcessor().isWaitingForWorldUpdate())
            throw new IllegalStateException("Native requested map dimension has not become ready");
        if (!Double.isFinite(x) || !Double.isFinite(z) || !Double.isFinite(zoom)
                || Math.abs(x) > 29_999_000 || Math.abs(z) > 29_999_000 || zoom < .0625 || zoom > 16)
            throw new IllegalArgumentException("Bounded finite center and native conservative zoom required");
        double old = (double) DEST_SCALE.get();
        if (!(old > 0) || !Double.isFinite(old)) throw new IllegalStateException("Native zoom unavailable");
        double steps = Math.log(zoom / old) / Math.log(1.2);
        CHANGE_ZOOM.invokeExact(map, steps, 1);
        ATTACHED.set(false); RESET.set(map, false); DESTINATION.set(map, (int[]) null);
        CAMERA_X.set(map, x); CAMERA_Z.set(map, z);
        return snapshot(mc);
    }

    /** Reads actual native values; caller must wait for observed readiness, not sleep.
     * Record two separately rendered observations before a screenshot and require
     * exact requested dimension, center tolerance and converged getUserScale().
     */
    public Map<String, Object> snapshot(Minecraft mc) {
        GuiMap map = requireOpen(mc);
        var result = new LinkedHashMap<String, Object>();
        var viewed = map.getDimensionOnInit();
        result.put("screen_class", map.getClass().getName());
        result.put("requested_dimension", requestedDimension.location().toString());
        result.put("actual_view_dimension", viewed == null ? "unavailable" : viewed.getDimId().location().toString());
        result.put("dimension_ready", viewed != null && requestedDimension.equals(viewed.getDimId())
            && requestedDimension.equals(world.getCurrentDimensionId()) && !map.getMapProcessor().isWaitingForWorldUpdate());
        result.put("camera_x", (double) CAMERA_X.get(map)); result.put("camera_z", (double) CAMERA_Z.get(map));
        result.put("user_scale", map.getUserScale()); result.put("target_scale", (double) DEST_SCALE.get());
        result.put("render_scale", (double) SCALE.get(map)); result.put("screen_scale", (double) SCREEN_SCALE.get(map));
        result.put("ui_width", map.width); result.put("ui_height", map.height);
        result.put("player_dimension", mc.level.dimension().location().toString());
        result.put("player_chunk_x", mc.player.chunkPosition().x); result.put("player_chunk_z", mc.player.chunkPosition().z);
        result.put("maphorizons_diagnostics", Diagnostics.summary());
        result.put("native_share_fetch_enabled", ShareFetch.enabled());
        result.put("note", "View state only; painting, provenance, permissions and performance require independent evidence");
        return result;
    }

    /** Restores only this view's temporary selection/zoom state. Never closes another UI. */
    public Map<String,Object> close(Minecraft mc) {
        GuiMap map = requireOpen(mc);
        Map<String,Object> before=snapshot(mc);
        // Closing restores the exact previous target, independent of modifier
        // keys. It does not alter another map screen's live animation.
        DEST_SCALE.set(previousZoom);ATTACHED.set(previousAttached);world.setCustomDimensionId(previousDimension);
        map.getMapProcessor().checkForWorldUpdate(); mc.setScreen(null);
        screen = null; session = null; world = null;
        return Map.of("status","owned temporary native map view restored and closed","last_native_view",before);
    }
}
