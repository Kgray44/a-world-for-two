package worldfortwo.taverndrinking.client;

import de.markusbordihn.easynpc.entity.easynpc.EasyNPC;
import net.minecraft.client.Minecraft;
import net.minecraft.client.model.PlayerModel;
import net.minecraft.client.model.geom.ModelPart;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.util.Mth;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.entity.HumanoidArm;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.UseAnim;

/** Visual sip only while the native entity is genuinely using a DRINK item. */
public final class TavernDrinkingPose {
    private TavernDrinkingPose() {}

    public static void apply(EasyNPC<?> npc, PlayerModel<?> model) {
        if (npc == null || model == null) return;
        Mob entity = npc.getMob();
        if (entity == null || !entity.level().isClientSide() || !entity.isAlive()
                || !entity.isUsingItem()) return;
        ResourceLocation skin = npc.getEasyNPCSkinData().getSkinDataEntry().texture();
        if (skin == null || !skin.getNamespace().equals("awft_tavern")
                || !skin.getPath().startsWith("textures/entity/")) return;

        ItemStack drink = entity.getUseItem();
        if (drink.isEmpty() || drink.getUseAnimation() != UseAnim.DRINK) return;
        int duration = drink.getUseDuration(entity);
        int remaining = entity.getUseItemRemainingTicks();
        if (duration <= 0 || remaining <= 0) return;

        float partial = Minecraft.getInstance().getTimer().getGameTimeDeltaPartialTick(false);
        float elapsed = Math.max(0, duration - remaining + partial);
        float envelope = Math.min(elapsed / 6, (remaining - partial) / 6);
        float blend = Mth.clamp(envelope, 0, 1);
        blend = blend * blend * (3 - 2 * blend);

        boolean right = (entity.getMainArm() == HumanoidArm.RIGHT)
                == (entity.getUsedItemHand() == InteractionHand.MAIN_HAND);
        ModelPart arm = right ? model.rightArm : model.leftArm;
        float side = right ? 1 : -1;
        float sip = (float) Math.sin(elapsed * .42) * .025F;

        // EasyNPC's ordinary third-person hand attachment follows this real
        // arm. Only the using arm changes: no item substitution, fake use state,
        // seat/root/leg movement, inventory mutation or instrument animation.
        arm.xRot = Mth.lerp(blend, arm.xRot, -1.85F + model.head.xRot * .8F + sip);
        arm.yRot = Mth.lerp(blend, arm.yRot, model.head.yRot + side * .18F);
        arm.zRot = Mth.lerp(blend, arm.zRot, side * .08F);
        (right ? model.rightSleeve : model.leftSleeve).copyFrom(arm);
    }
}
