package worldfortwo.bridge;

import java.io.InputStream;
import java.lang.invoke.MethodHandles;
import java.lang.invoke.MethodType;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.util.HexFormat;
import java.util.List;
import java.util.Optional;
import net.minecraft.network.chat.Component;
import net.minecraft.server.packs.PackLocationInfo;
import net.minecraft.server.packs.PackResources;
import net.minecraft.server.packs.PackSelectionConfig;
import net.minecraft.server.packs.PackType;
import net.minecraft.server.packs.PathPackResources;
import net.minecraft.server.packs.repository.Pack;
import net.minecraft.server.packs.repository.PackSource;
import net.neoforged.fml.ModList;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/** Match the server's selected built-in terrain pack priority after raw mod roots.
 * The original Tectonic data and native metadata/conditional-overlay factory are used.
 * No fingerprint, registry codec, refusal, terrain function or server state is changed.
 */
public final class SeedgenTectonicResources {
    private static final Logger LOG = LoggerFactory.getLogger("AWFT-SeedGen-Resources");
    private static final String SHA512 = "e07b9cb54f078b7bf74c925c5cebd6643f0b4c210b8f94474e68659b69468ece7d61432f70eafe7abaa1dfa798e4638aad297987c121dc127588c2623b7f7a81";
    private SeedgenTectonicResources() {}

    public static void append(List<PackResources> opened) {
        if (!ModList.get().isLoaded("tectonic")) return;
        var info = ModList.get().getModFileById("tectonic");
        var mod = ModList.get().getModContainerById("tectonic").orElseThrow();
        if (!"3.0.28".equals(mod.getModInfo().getVersion().toString()))
            throw new IllegalStateException("SeedGen terrain adapter requires pinned Tectonic 3.0.28");
        try {
            Path archive = info.getFile().getFilePath();
            if (Files.size(archive) != 451757L)
                throw new IllegalStateException("Pinned Tectonic archive size differs");
            MessageDigest digest = MessageDigest.getInstance("SHA-512");
            try (InputStream stream = Files.newInputStream(archive)) {
                byte[] buffer = new byte[8192];
                for (int size; (size = stream.read(buffer)) != -1;) digest.update(buffer, 0, size);
            }
            if (!SHA512.equals(HexFormat.of().formatHex(digest.digest())))
                throw new IllegalStateException("Pinned Tectonic archive digest differs");
            if (!enabled()) return;
            if (orderExisting(opened)) return;
            Path root = info.getFile().findResource("resourcepacks/tectonic");
            // Identical factory, ID, selection and metadata loading to TectonicNeoforge.
            Pack pack = Pack.readMetaAndCreate(
                new PackLocationInfo("tectonic", Component.literal("Tectonic"), PackSource.BUILT_IN, Optional.empty()),
                new PathPackResources.PathResourcesSupplier(root), PackType.SERVER_DATA,
                new PackSelectionConfig(true, Pack.Position.TOP, false));
            if (pack == null) throw new IllegalStateException("Native Tectonic built-in metadata was rejected");
            opened.add(pack.open());
            LOG.info("SeedGen loaded pinned native Tectonic built-in terrain resources after mod roots and before explicit data packs");
        } catch (RuntimeException | LinkageError failure) {
            throw failure;
        } catch (Throwable failure) {
            // Do not hide VM failures behind SeedGen's recoverable loading fallback.
            if (failure instanceof Error error) throw error;
            throw new IllegalStateException("Cannot load exact native Tectonic terrain resources", failure);
        }
    }

    private static boolean orderExisting(List<PackResources> opened) {
        List<PackResources> existing = opened.stream().filter(pack -> pack.packId().equals("tectonic")).toList();
        if (existing.size() > 1)
            throw new IllegalStateException("Multiple native Tectonic packs prevent exact terrain resource ordering");
        if (existing.isEmpty()) return false;
        // Retain this exact native resource/overlays. SeedGen appended conflicting
        // raw Terralith data after it; the server selects tectonic after mod_data.
        PackResources nativePack = existing.getFirst();
        int previousIndex = opened.indexOf(nativePack);
        opened.remove(previousIndex);
        opened.add(nativePack);
        LOG.info("SeedGen ordered the existing pinned native Tectonic pack after raw mod roots and before explicit data packs ({} -> {})", previousIndex, opened.size() - 1);
        return true;
    }

    private static boolean enabled() throws Throwable {
        var lookup = MethodHandles.publicLookup();
        Class<?> tectonic = Class.forName("dev.worldgen.tectonic.Tectonic");
        Class<?> holder = Class.forName("dev.worldgen.apollib.config.ApollibConfigHolder");
        Class<?> copyable = Class.forName("dev.worldgen.apollib.config.ApollibCopyable");
        Class<?> state = Class.forName("dev.worldgen.tectonic.config.ConfigState");
        Object config = lookup.findStaticGetter(tectonic, "CONFIG", holder).invoke();
        Object values = lookup.findVirtual(holder, "getState", MethodType.methodType(copyable)).invoke(config);
        return (boolean) lookup.findVirtual(state, "enabled", MethodType.methodType(boolean.class)).invoke(values);
    }
}
