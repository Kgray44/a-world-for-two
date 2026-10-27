package worldfortwo.bridge.mixin;

import com.mojang.serialization.Codec;
import net.minecraft.world.level.levelgen.DensityFunction;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Pseudo;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Redirect;
import worldfortwo.bridge.SeedgenFingerprintCodec;

/** Exact SeedGen 0.9.1 interop; the original author JAR is never rewritten. */
@Pseudo
@Mixin(targets = "mobius.seedrenderer.net.SeedSharing", remap = false)
public class SeedgenFingerprintMixin {
    @Redirect(method = "computePrint", at = @At(value = "FIELD",
        target = "Lnet/minecraft/world/level/levelgen/DensityFunction;DIRECT_CODEC:Lcom/mojang/serialization/Codec;"),
        remap = false, require = 1)
    private static Codec<DensityFunction> awftEncodeActualDensityValue() {
        return SeedgenFingerprintCodec.codec();
    }
}
