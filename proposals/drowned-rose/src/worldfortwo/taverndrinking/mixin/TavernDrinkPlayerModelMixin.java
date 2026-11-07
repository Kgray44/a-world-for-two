package worldfortwo.taverndrinking.mixin;

import de.markusbordihn.easynpc.entity.easynpc.EasyNPC;
import net.minecraft.client.model.PlayerModel;
import net.minecraft.world.entity.LivingEntity;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;
import worldfortwo.taverndrinking.client.TavernDrinkingPose;
import worldfortwo.tavernmotion.client.TavernMicroMotion;

/** PlayerModel TAIL still runs when EasyNPC cancels the HumanoidModel setup. */
@Mixin(PlayerModel.class)
public abstract class TavernDrinkPlayerModelMixin {
    @Inject(method = "setupAnim(Lnet/minecraft/world/entity/LivingEntity;FFFFF)V",
            at = @At("TAIL"), require = 1)
    private void awft$nativeDrinkUse(LivingEntity entity, float limbSwing,
            float limbSwingAmount, float ageInTicks, float netHeadYaw,
            float headPitch, CallbackInfo ci) {
        if (entity instanceof EasyNPC<?> npc && !TavernMicroMotion.hasSmoothNpcTail(this)) {
            TavernDrinkingPose.apply(npc, (PlayerModel<?>) (Object) this);
        }
    }
}
