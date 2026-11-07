package worldfortwo.tavernmotion.mixin;

import de.markusbordihn.easynpc.entity.easynpc.EasyNPC;
import net.minecraft.client.model.PlayerModel;
import net.minecraft.world.entity.LivingEntity;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Pseudo;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;
import worldfortwo.taverndrinking.client.TavernDrinkingPose;
import worldfortwo.tavernmotion.client.TavernMicroMotion;
import worldfortwo.tavernmotion.client.TavernInstrumentPose;

/** Optional final pose after Smooth1.1.0's actual NPC shadow-pose overwrite. */
@Pseudo
@Mixin(targets=TavernMicroMotion.SMOOTH_NPC_MODEL,remap=false)
public abstract class TavernSmoothNpcModelMixin {
    @Inject(method="setupAnim(Lnet/minecraft/world/entity/LivingEntity;FFFFF)V",
            at=@At("TAIL"),require=1,remap=false)
    private void awft$afterSmoothNpcPose(LivingEntity entity,float limbSwing,
            float limbSwingAmount,float ageInTicks,float netHeadYaw,
            float headPitch,CallbackInfo ci){
        if(entity instanceof EasyNPC<?> npc){
            PlayerModel<?> model=(PlayerModel<?>)(Object)this;
            TavernMicroMotion.seatedPose(npc,model);
            TavernMicroMotion.applyAfterSmooth(npc,model);
            TavernInstrumentPose.apply(npc,model);
            TavernDrinkingPose.apply(npc,model);
        }
    }
}
