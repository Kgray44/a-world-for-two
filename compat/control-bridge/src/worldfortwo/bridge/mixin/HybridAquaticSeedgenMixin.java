package worldfortwo.bridge.mixin;

import java.util.List;
import net.minecraft.core.Registry;
import net.minecraft.core.RegistryAccess;
import net.minecraft.server.packs.PackResources;
import net.minecraft.server.packs.repository.PackRepository;
import net.minecraft.server.packs.resources.CloseableResourceManager;
import net.minecraft.world.level.dimension.LevelStem;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Pseudo;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;
import org.spongepowered.asm.mixin.injection.callback.LocalCapture;
import worldfortwo.bridge.HybridAquaticSeedgenCompat;
import worldfortwo.bridge.LithostitchedSeedgenCompat;

/** Client-only: resources and dimension holders are live just before normal close. */
@Pseudo
@Mixin(targets="mobius.seedrenderer.dh.ClientWorldgen",remap=false)
public abstract class HybridAquaticSeedgenMixin {
    @Shadow(remap=false)private static Registry<LevelStem> stems;

    @Inject(method="attempt(ZZ)Lnet/minecraft/core/RegistryAccess$Frozen;",
        at=@At(value="INVOKE",target="Lnet/minecraft/server/packs/resources/CloseableResourceManager;close()V",ordinal=0,remap=false),
        locals=LocalCapture.CAPTURE_FAILHARD,remap=false,require=1)
    private static void awft$nativeOceanTerrain(boolean withMods,boolean wholeSet,
        CallbackInfoReturnable<RegistryAccess.Frozen> result,long startedAt,
        PackRepository packs,List<PackResources> opened,int modPacks,int dataPacks,List<String> names,
        CloseableResourceManager resources,RegistryAccess.Frozen builtIn,List<?> everything,List<?> dynamic,
        RegistryAccess.Frozen worldgen,int defined,RegistryAccess.Frozen returned) {
        if(withMods) {
            var currentStems=LithostitchedSeedgenCompat.currentAttemptStems(stems);
            LithostitchedSeedgenCompat.beforeHybrid(worldgen,currentStems,wholeSet,opened,resources);
            HybridAquaticSeedgenCompat.apply(worldgen,resources,currentStems);
            LithostitchedSeedgenCompat.afterHybrid(worldgen);
        }
    }
}
