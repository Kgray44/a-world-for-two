package worldfortwo.bridge.mixin;

import java.nio.file.Path;
import java.util.List;
import net.minecraft.core.RegistryAccess;
import net.minecraft.server.packs.PackResources;
import net.minecraft.server.packs.repository.PackRepository;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Pseudo;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;
import org.spongepowered.asm.mixin.injection.callback.LocalCapture;
import worldfortwo.bridge.SeedgenTectonicResources;

/** Exact local table of the pinned SeedGen 0.9.1 loader; only registered on clients. */
@Pseudo
@Mixin(targets="mobius.seedrenderer.dh.ClientWorldgen", remap=false)
public abstract class SeedgenTectonicResourcesMixin {
    @Inject(method="attempt(ZZ)Lnet/minecraft/core/RegistryAccess$Frozen;", at=@At(value="INVOKE",
        target="Ljava/nio/file/Files;createDirectories(Ljava/nio/file/Path;[Ljava/nio/file/attribute/FileAttribute;)Ljava/nio/file/Path;",
        remap=false), locals=LocalCapture.CAPTURE_FAILHARD, remap=false, require=1)
    private static void awft$nativeTerrainPack(boolean withMods, boolean wholeSet,
        CallbackInfoReturnable<RegistryAccess.Frozen> result, long startedAt,
        PackRepository repository, List<PackResources> opened, int modPacks,
        int dataPacks, List<String> names, Path folder) {
        if (withMods) SeedgenTectonicResources.append(opened);
    }
}
