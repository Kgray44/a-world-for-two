package worldfortwo.tavernmotion.mixin;

import de.markusbordihn.easynpc.client.model.EasyNPCModel;
import de.markusbordihn.easynpc.client.model.EasyNPCModelManager;
import de.markusbordihn.easynpc.entity.easynpc.EasyNPC;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;
import worldfortwo.tavernmotion.client.TavernMicroMotion;

/** Hooks EasyNPC itself after its pose setup, rather than racing vanilla mixins. */
@Mixin(value = EasyNPCModel.class, remap = false)
public abstract class EasyNPCModelMotionMixin {
    @Inject(method = "setupAnimationEnd", at = @At("RETURN"), require = 1, remap = false)
    private static void awft$subtleTavernIdle(EasyNPC<?> npc,
            EasyNPCModelManager model, CallbackInfo ci) {
        TavernMicroMotion.apply(npc, model);
    }
}
