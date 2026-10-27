package worldfortwo.presentation;

import net.neoforged.fml.config.ModConfig;
import net.neoforged.fml.event.config.ModConfigEvent;

/** Restricts Small Ships' disk migration callback to configs backed by a file. */
public final class SmallShipsConfigLifecycle {
    private SmallShipsConfigLifecycle() {}

    public static boolean skipFileCallback(ModConfigEvent event) {
        ModConfig config = event.getConfig();
        if (!"smallships".equals(config.getModId())) return false;
        if (event instanceof ModConfigEvent.Unloading) return true;
        if (!(event instanceof ModConfigEvent.Loading || event instanceof ModConfigEvent.Reloading)
                || config.getType() != ModConfig.Type.SERVER) return false;

        var loaded = config.getLoadedConfig();
        if (loaded == null) return false;
        try {
            // A missing file still has a path and must reach the original callback.
            config.getFullPath();
            return false;
        } catch (IllegalStateException error) {
            // Pinned FML 4.0.45 has no public ILoadedConfig.path() API. Match only
            // its exact path-null failure, without logging the remote config data.
            // An API change or an unrelated failure must remain visible.
            String expected = "Cannot call getFullPath() on non-file config "
                    + loaded + " at path " + config.getFileName();
            if (error.getClass() != IllegalStateException.class
                    || config.getLoadedConfig() != loaded || !expected.equals(error.getMessage())) throw error;
            var trace = error.getStackTrace();
            if (trace.length == 0 || !ModConfig.class.getName().equals(trace[0].getClassName())
                    || !"getFullPath".equals(trace[0].getMethodName())) throw error;
            // ModConfig.setConfig already called spec.acceptConfig before this
            // event. The bundled Forge adapter corrects values and resets caches.
            // Skip only Small Ships' subsequent attempt to parse/migrate a file.
            return true;
        }
    }
}
