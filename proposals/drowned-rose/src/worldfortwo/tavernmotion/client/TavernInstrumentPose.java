package worldfortwo.tavernmotion.client;

import de.markusbordihn.easynpc.entity.easynpc.EasyNPC;
import immersive_melodies.client.animation.EntityModelAnimator;
import immersive_melodies.client.animation.accessors.ArmsAndHeadAccessor;
import immersive_melodies.item.InstrumentItem;
import net.minecraft.client.model.PlayerModel;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.item.ItemStack;

/** Restore the real instrument's own animator after Smooth's NPC shadow pose. */
public final class TavernInstrumentPose {
    private TavernInstrumentPose() {}

    public static void apply(EasyNPC<?> npc,PlayerModel<?> model){
        if(npc==null||model==null)return;
        Mob entity=npc.getMob();
        if(entity==null||!entity.level().isClientSide()||!entity.isAlive()
            ||entity.isUsingItem())return;
        ResourceLocation skin=npc.getEasyNPCSkinData().getSkinDataEntry().texture();
        if(skin==null||!skin.getNamespace().equals("awft_tavern")
            ||!skin.getPath().startsWith("textures/entity/"))return;
        for(ItemStack held:entity.getHandSlots()){
            if(!(held.getItem() instanceof InstrumentItem instrument)||!instrument.isPlaying(held))continue;
            // This is native rendering, including its normal visual envelope.
            // It neither plays notes nor writes item/playback/world state.
            EntityModelAnimator.setAngles(new ArmsAndHeadAccessor<>(entity,
                model.head,model.hat,model.leftArm,model.rightArm));
            model.leftSleeve.copyFrom(model.leftArm);
            model.rightSleeve.copyFrom(model.rightArm);
            model.hat.copyFrom(model.head);
            return;
        }
    }
}
