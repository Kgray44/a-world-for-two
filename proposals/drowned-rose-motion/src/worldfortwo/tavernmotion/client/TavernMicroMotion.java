package worldfortwo.tavernmotion.client;

import de.markusbordihn.easynpc.client.model.EasyNPCModelManager;
import de.markusbordihn.easynpc.data.model.ModelAnimationBehavior;
import de.markusbordihn.easynpc.data.model.ModelPartType;
import de.markusbordihn.easynpc.data.model.ModelPose;
import de.markusbordihn.easynpc.entity.easynpc.EasyNPC;
import earth.terrarium.handcrafted.common.entities.Seat;
import net.minecraft.client.Minecraft;
import net.minecraft.client.model.PlayerModel;
import net.minecraft.client.model.geom.ModelPart;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.util.Mth;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.player.Player;

/** Small, render-only offsets after EasyNPC's ordinary pose/arm setup. */
public final class TavernMicroMotion {
    private static final double TAU = Math.PI * 2;

    private TavernMicroMotion() {}

    private static boolean tavernSkin(EasyNPC<?> npc) {
        ResourceLocation skin = npc.getEasyNPCSkinData().getSkinDataEntry().texture();
        return skin != null && skin.getNamespace().equals("awft_tavern")
                && skin.getPath().startsWith("textures/entity/");
    }

    /**
     * Final PlayerModel pose, including when EasyNPC cancels its superclass's
     * vanilla setup at HEAD. This must run after PlayerModel copies clothing.
     */
    public static void seatedPose(EasyNPC<?> npc, PlayerModel<?> model) {
        if (npc == null || model == null || !tavernSkin(npc)) return;
        Mob entity = npc.getMob();
        if (entity == null || !entity.level().isClientSide() || !entity.isAlive()
                || !(entity.getVehicle() instanceof Seat seat)) return;

        // Exact vanilla HumanoidModel riding-leg rotations. Do not touch hand,
        // arm, head or instrument rotations, even while drinking or performing.
        model.riding = true;
        model.crouching = false;
        model.rightLeg.xRot = -1.4137167F;
        model.rightLeg.yRot = (float) Math.PI / 10;
        model.rightLeg.zRot = (float) Math.PI / 40;
        model.leftLeg.xRot = -1.4137167F;
        model.leftLeg.yRot = -(float) Math.PI / 10;
        model.leftLeg.zRot = -(float) Math.PI / 40;

        // Handcrafted seats use the player's native VEHICLE attachment. EasyNPC
        // humanoids have a default feet attachment instead. Account for that
        // difference in MODEL pixels only, never by moving the real passenger.
        // Use initial pivots so repeated model calls cannot accumulate lowering.
        float lower = (float) (16 * (Player.DEFAULT_VEHICLE_ATTACHMENT.y
                - entity.getVehicleAttachmentPoint(seat).y));
        seatedHeight(model.head, lower);
        seatedHeight(model.hat, lower);
        seatedHeight(model.body, lower);
        seatedHeight(model.leftArm, lower);
        seatedHeight(model.rightArm, lower);
        seatedHeight(model.leftLeg, lower);
        seatedHeight(model.rightLeg, lower);
        model.hat.copyFrom(model.head);
        model.jacket.copyFrom(model.body);
        model.leftSleeve.copyFrom(model.leftArm);
        model.rightSleeve.copyFrom(model.rightArm);
        model.leftPants.copyFrom(model.leftLeg);
        model.rightPants.copyFrom(model.rightLeg);
    }

    private static void seatedHeight(ModelPart part, float lower) {
        part.y = part.getInitialPose().y + lower;
    }

    public static void apply(EasyNPC<?> npc, EasyNPCModelManager model) {
        if (npc == null || model == null) return;
        Mob entity = npc.getMob();
        if (entity == null || !entity.level().isClientSide() || !entity.isAlive()
                || entity.isSleeping()) return;

        // SkinDataEntry is synced. Vanilla scoreboard tags are not a reliable
        // client selector; do not depend on getTags() or names visible on screen.
        if (!tavernSkin(npc)) return;

        var data = npc.getEasyNPCModelData();
        if (data == null || data.getModelPose() == ModelPose.CUSTOM
                || data.getModelAnimationBehavior() == ModelAnimationBehavior.NONE
                || data.getModelAnimationRequest().isPresent()) return;

        boolean seated = entity.getVehicle() instanceof Seat;
        if (entity.isPassenger() && !seated) return;
        if (!seated && !entity.onGround()) return;

        // Respect native instrument, potion, equipment and active hand poses.
        // This pass never resets/replaces either arm or item animation.
        if (entity.isUsingItem() || entity.swinging
                || !entity.getMainHandItem().isEmpty()
                || !entity.getOffhandItem().isEmpty()) return;

        float still = seated ? 1 : Mth.clamp(1 - entity.walkAnimation.speed() * 10, 0, 1);
        if (still <= 0) return;

        ModelPart head = model.getModelPart(ModelPartType.HEAD);
        ModelPart body = model.getModelPart(ModelPartType.BODY);
        ModelPart left = model.getModelPart(ModelPartType.LEFT_ARM);
        ModelPart right = model.getModelPart(ModelPartType.RIGHT_ARM);
        if (head == null || body == null || left == null || right == null) return;

        int salt = entity.getUUID().hashCode() & 0x7fffffff;
        double phase = (salt % 4093) * TAU / 4093;
        double ticks = entity.level().getGameTime()
                + Minecraft.getInstance().getTimer().getGameTimeDeltaPartialTick(false);
        double breath = Math.sin(ticks * TAU / (94 + salt % 23) + phase);
        double shift = .65 * Math.sin(ticks * TAU / (246 + salt % 89) + phase)
                + .35 * Math.sin(ticks * TAU / (367 + salt % 131) + phase * 1.7);
        double glance = Math.sin(ticks * TAU / (184 + salt % 83) + phase * .7);
        double settle = pulse(ticks + salt % 997, 169 + salt % 97, 58);
        double gesture = pulse(ticks + salt % 1597, 539 + salt % 241, 76);

        // No position/vehicle/collision/AI changes. The real Handcrafted seat
        // keeps its riding pose; legs, hips, feet and root transforms stay intact.
        body.zRot += still * (float) ((seated ? .012 : .019) * shift);
        body.xRot += still * (float) (.003 * breath + (seated ? .024 * settle : .009 * gesture));
        head.yRot += still * (float) (.035 * glance);
        head.xRot += still * (float) (.009 * breath - .016 * settle);
        head.zRot -= still * (float) (.009 * shift);
        left.zRot += still * (float) (.012 * breath + .014 * shift);
        right.zRot -= still * (float) (.012 * breath + .014 * shift);
        left.xRot += still * (float) ((seated ? .035 : .018) * settle);
        right.xRot -= still * (float) (.11 * gesture);

        ModelPart hat = model.getModelPart(ModelPartType.HAT);
        if (hat != null) hat.copyFrom(head);
        // PlayerModel copies sleeves/jacket/pants after its HumanoidModel setup.
        // Also retain EasyNPC's own visibility/hat synchronization contract.
        model.syncModelParts(data);
    }

    /** Smooth, zero-slope boundaries: no per-tick random pose jumps. */
    private static double pulse(double ticks, double period, double duration) {
        double local = ticks % period;
        if (local < 0) local += period;
        if (local >= duration) return 0;
        double value = Math.sin(Math.PI * local / duration);
        return value * value;
    }
}
