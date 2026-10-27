package worldfortwo.bridge.mixin;

import com.llamalad7.mixinextras.injector.wrapmethod.WrapMethod;
import com.llamalad7.mixinextras.injector.wrapoperation.Operation;
import mobius.seedrenderer.dh.SeedRetrievalQueue;
import net.minecraft.client.multiplayer.ClientLevel;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Pseudo;
import worldfortwo.bridge.LithostitchedSeedgenCompat;

/** Whole operation serialization closes the sharedBasis-before-QUEUES-lock race. */
@Pseudo
@Mixin(targets="mobius.seedrenderer.dh.ClientTerrain",remap=false)
public abstract class LithostitchedSeedgenQueueMixin implements LithostitchedSeedgenCompat.QueueAdmissionGuard {
    @WrapMethod(method="queueFor(Lnet/minecraft/client/multiplayer/ClientLevel;)Lmobius/seedrenderer/dh/SeedRetrievalQueue;",remap=false)
    private static SeedRetrievalQueue awft$connectedQueue(ClientLevel level,Operation<SeedRetrievalQueue> original) {
        return LithostitchedSeedgenCompat.withQueueAdmission(()->original.call(level));
    }
}
