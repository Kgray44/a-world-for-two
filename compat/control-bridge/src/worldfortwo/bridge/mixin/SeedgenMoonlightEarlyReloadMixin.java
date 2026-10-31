package worldfortwo.bridge.mixin;

import java.util.List;
import net.minecraft.core.RegistryAccess;
import net.minecraft.server.packs.PackResources;
import net.minecraft.server.packs.repository.PackRepository;
import net.minecraft.server.packs.resources.CloseableResourceManager;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Pseudo;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;
import org.spongepowered.asm.mixin.injection.callback.LocalCapture;
import worldfortwo.bridge.MoonlightSeedgenEarlyReload;

/** Pinned SeedGen0.9.1 local table, after manager construction and before registries.
 * Register only in awft-bridge.mixins.json's CLIENT list.
 */
@Pseudo
@Mixin(targets="mobius.seedrenderer.dh.ClientWorldgen",remap=false)
public abstract class SeedgenMoonlightEarlyReloadMixin {
    @Inject(method="attempt(ZZ)Lnet/minecraft/core/RegistryAccess$Frozen;",
        at=@At(value="INVOKE",target="Lnet/minecraft/core/RegistryAccess;fromRegistryOfRegistries(Lnet/minecraft/core/Registry;)Lnet/minecraft/core/RegistryAccess$Frozen;",remap=false),
        locals=LocalCapture.CAPTURE_FAILHARD,remap=false,require=1)
    private static void awft$earlyNativeData(boolean withMods,boolean wholeSet,
        CallbackInfoReturnable<RegistryAccess.Frozen> result,long startedAt,
        PackRepository repository,List<PackResources> opened,int modPacks,int dataPacks,
        List<String> names,CloseableResourceManager resources) {
        MoonlightSeedgenEarlyReload.prepare(withMods,resources,opened);
    }
}
