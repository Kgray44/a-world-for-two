package worldfortwo.bridge.mixin;

import com.llamalad7.mixinextras.injector.wrapmethod.WrapMethod;
import com.llamalad7.mixinextras.injector.wrapoperation.Operation;
import mobius.seedrenderer.dh.WorldBasis;
import net.minecraft.resources.ResourceKey;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.level.Level;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Pseudo;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;
import worldfortwo.bridge.LithostitchedSeedgenCompat;

/** Client-only required guard. An FP-only adapter cannot authorize wrong biomes. */
@Pseudo
@Mixin(targets="mobius.seedrenderer.dh.WorldBasis",remap=false)
public abstract class LithostitchedSeedgenWorldMixin implements LithostitchedSeedgenCompat.SeededBasisGuard {
    @WrapMethod(method="fromSeed(Lnet/minecraft/resources/ResourceKey;JLnet/minecraft/resources/ResourceLocation;)Lmobius/seedrenderer/dh/WorldBasis;",remap=false)
    private static WorldBasis awft$preparePacketBasis(ResourceKey<Level> dimension,long seed,ResourceLocation type,Operation<WorldBasis> original) {
        return LithostitchedSeedgenCompat.withAcceptedSeed(dimension,seed,type,()->original.call(dimension,seed,type));
    }
    @Inject(method="fromSeed(Lnet/minecraft/resources/ResourceKey;JLnet/minecraft/resources/ResourceLocation;)Lmobius/seedrenderer/dh/WorldBasis;",
        at=@At("HEAD"),remap=false,require=1)
    private static void awft$seededBiomes(ResourceKey<Level> dimension,long seed,ResourceLocation type,CallbackInfoReturnable<?> result) {
        LithostitchedSeedgenCompat.requireSeededBasis(dimension,seed,type);
    }
}
