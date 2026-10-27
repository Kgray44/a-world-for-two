package worldfortwo.bridge.mixin;

import net.minecraft.core.RegistryAccess;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Pseudo;
import org.spongepowered.asm.mixin.gen.Invoker;

/** A direct invoker avoids resolving unrelated client-only method signatures by reflection. */
@Pseudo
@Mixin(targets="mobius.seedrenderer.net.SeedSharing",remap=false)
public interface SeedgenFingerprintAccess {
    @Invoker(value="computePrint",remap=false)
    static String awftFingerprint(RegistryAccess registries){throw new IllegalStateException("SeedGen invoker was not transformed");}
}
