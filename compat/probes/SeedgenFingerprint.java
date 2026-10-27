import com.mojang.serialization.JsonOps;
import net.minecraft.core.Holder;
import net.minecraft.world.level.levelgen.DensityFunction;
import net.minecraft.world.level.levelgen.DensityFunctions;
import worldfortwo.bridge.SeedgenFingerprintCodec;

public class SeedgenFingerprint {
    public static void main(String[] args) {
        net.minecraft.SharedConstants.tryDetectVersion();
        net.minecraft.server.Bootstrap.bootStrap();
        DensityFunction original = DensityFunctions.constant(0.25);
        DensityFunction wrapped = new DensityFunctions.HolderHolder(Holder.direct(original));
        DensityFunction twice = new DensityFunctions.HolderHolder(Holder.direct(wrapped));
        var codec = SeedgenFingerprintCodec.codec();
        var expected = codec.encodeStart(JsonOps.INSTANCE, original).getOrThrow();
        if (!expected.equals(codec.encodeStart(JsonOps.INSTANCE, wrapped).getOrThrow())
            || !expected.equals(codec.encodeStart(JsonOps.INSTANCE, twice).getOrThrow()))
            throw new AssertionError("Equivalent density reference changed its encoding");
        if (SeedgenFingerprintCodec.value(twice).compute(new DensityFunction.SinglePointContext(7, 80, 9)) != 0.25)
            throw new AssertionError("Density computation changed");
        DensityFunction excessive = original;
        for (int i = 0; i < 65; i++) excessive = new DensityFunctions.HolderHolder(Holder.direct(excessive));
        try {
            SeedgenFingerprintCodec.value(excessive);
            throw new AssertionError("Excessive references were accepted");
        } catch (IllegalArgumentException expectedFailure) { }
        System.out.println("Actual Minecraft codec probe passed: direct, one reference, two references, calculation, excessive-reference refusal.");
    }
}
