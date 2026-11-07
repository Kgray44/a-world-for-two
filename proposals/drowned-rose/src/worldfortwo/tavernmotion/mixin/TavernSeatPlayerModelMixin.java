package worldfortwo.tavernmotion.mixin;

import de.markusbordihn.easynpc.entity.easynpc.EasyNPC;
import net.minecraft.client.model.PlayerModel;
import net.minecraft.world.entity.LivingEntity;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;
import worldfortwo.tavernmotion.client.TavernMicroMotion;

/** The subclass TAIL survives EasyNPC cancellation inside HumanoidModel. */
@Mixin(PlayerModel.class)
public abstract class TavernSeatPlayerModelMixin {
    @Inject(method = "setupAnim(Lnet/minecraft/world/entity/LivingEntity;FFFFF)V",
            at = @At("TAIL"), require = 1)
    private void awft$actualHandcraftedSeat(LivingEntity entity, float limbSwing,
            float limbSwingAmount, float ageInTicks, float netHeadYaw,
            float headPitch, CallbackInfo ci) {
        if (entity instanceof EasyNPC<?> npc && !TavernMicroMotion.hasSmoothNpcTail(this)) {
            TavernMicroMotion.seatedPose(npc, (PlayerModel<?>) (Object) this);
        }
    }
}
