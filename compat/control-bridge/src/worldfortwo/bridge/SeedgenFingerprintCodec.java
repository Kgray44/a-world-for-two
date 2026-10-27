package worldfortwo.bridge;

import com.mojang.serialization.Codec;
import net.minecraft.world.level.levelgen.DensityFunction;
import net.minecraft.world.level.levelgen.DensityFunctions;
import java.util.Collections;
import java.util.IdentityHashMap;
import java.util.Set;

/** Encode transparent root references by their actual value for SeedGen's digest.
 * No terrain calculation, registry value, fingerprint comparison or refusal changes.
 * Minecraft's direct dispatch codec intentionally cannot encode HolderHolder roots.
 */
public final class SeedgenFingerprintCodec {
    private SeedgenFingerprintCodec() {}

    public static DensityFunction value(DensityFunction function) {
        Set<DensityFunction> visited = Collections.newSetFromMap(new IdentityHashMap<>());
        for (int depth = 0; function instanceof DensityFunctions.HolderHolder reference; depth++) {
            if (depth >= 64 || !visited.add(function))
                throw new IllegalArgumentException("Cyclic or excessive density reference in worldgen fingerprint");
            function = reference.function().value();
        }
        return function;
    }

    public static Codec<DensityFunction> codec() {
        return DensityFunction.DIRECT_CODEC.xmap(function -> function, SeedgenFingerprintCodec::value);
    }

    public static Codec<DensityFunction> guarded(Codec<DensityFunction> original) {
        return original.xmap(function->function,function->{
            if(function instanceof DensityFunctions.HolderHolder && StackWalker.getInstance().walk(frames->frames.anyMatch(frame->
                frame.getClassName().equals("mobius.seedrenderer.net.SeedSharing") && frame.getMethodName().equals("computePrint"))))
                return value(function);
            return function;
        });
    }
}
