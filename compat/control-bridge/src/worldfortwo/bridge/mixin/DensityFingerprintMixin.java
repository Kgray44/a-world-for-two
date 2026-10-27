package worldfortwo.bridge.mixin;

import com.mojang.serialization.Codec;
import net.minecraft.world.level.levelgen.DensityFunction;
import net.minecraft.world.level.levelgen.DensityFunctions;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Redirect;
import worldfortwo.bridge.SeedgenFingerprintCodec;

/** Keep SeedSharing's original bytecode: rewriting its client methods is invalid on a server. */
@Mixin(DensityFunction.class)
public interface DensityFingerprintMixin {
    @Redirect(method="<clinit>",at=@At(value="FIELD",
        target="Lnet/minecraft/world/level/levelgen/DensityFunctions;DIRECT_CODEC:Lcom/mojang/serialization/Codec;"),require=1)
    private static Codec<DensityFunction> awftGuardFingerprintEncoding(){
        return SeedgenFingerprintCodec.guarded(DensityFunctions.DIRECT_CODEC);
    }
}
