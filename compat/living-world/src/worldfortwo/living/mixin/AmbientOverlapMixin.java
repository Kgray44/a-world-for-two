package worldfortwo.living.mixin;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.Unique;
import org.spongepowered.asm.mixin.injection.*;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;
import net.minecraft.ChatFormatting;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.npc.AbstractVillager;
import net.minecraft.nbt.CompoundTag;
import io.github.draysus.chattingvillagers.ChattingVillagers;
import io.github.draysus.chattingvillagers.ModConfig;
import io.github.draysus.chattingvillagers.PlayerPrefs;
import tn.naizo.smartvillagers.SmartVillagers;
import worldfortwo.living.WorldCharacters;
import worldfortwo.living.AmbientBudget;
import java.util.ArrayList;
import java.util.UUID;
@Mixin(value=ChattingVillagers.class,remap=false)
public abstract class AmbientOverlapMixin {
    @Shadow private ModConfig config;
    @Unique private final AmbientBudget awft$budget=new AmbientBudget();
    // Exact 1.21.1 vanilla: clamp(renderDistance/8,1,2.5) * entityDistanceScaling(.5..5).
    @Unique private static final double AWFT_MAX_VANILLA_VIEW_SCALE=12.5;
    @Inject(method="isExcluded",at=@At("HEAD"),cancellable=true,remap=false)
    private void awft$busy(AbstractVillager villager,CallbackInfoReturnable<Boolean> info){
        var profile=WorldCharacters.current.profile(villager.getUUID());
        if(profile!=null&&(!WorldCharacters.current.enabled(profile)||SmartVillagers.conversations().locks().owner(villager.getUUID()).isPresent()))info.setReturnValue(true);
    }
    @Inject(method="sendVillagerLine",at=@At("HEAD"),cancellable=true,remap=false)
    private void awft$cooldown(MinecraftServer server,ServerLevel level,AbstractVillager villager,String text,double radius,long tick,PlayerPrefs prefs,CallbackInfoReturnable<Integer> info){
        if(!WorldCharacters.current.ambientReady(villager.getUUID(),tick)){info.setReturnValue(0);return;}
        var profile=WorldCharacters.current.profile(villager.getUUID());
        boolean bubbles=config.bubblesEnabled&&(profile==null||WorldCharacters.flag(WorldCharacters.object(profile,"voice"),"bubbles"));
        if(!bubbles){if(!config.chatMessagesEnabled)info.setReturnValue(0);return;}
        if(text==null||text.isBlank()||!Double.isFinite(radius)||radius<0){info.setReturnValue(0);return;}
        // Exact native callers pass the squared speech radius. Shared displays may be rendered
        // beyond the intended speech radius by client view-scale; include that envelope.
        double audienceRadius=Math.sqrt(radius)*AWFT_MAX_VANILLA_VIEW_SCALE+4.0;
        double audienceSquared=audienceRadius*audienceRadius;
        ArrayList<UUID> observers=new ArrayList<>();boolean nativeListener=false;
        for(var player:server.getPlayerList().getPlayers()){
            if(player.level()!=level)continue;
            double distance=player.distanceToSqr(villager);
            if(distance<=radius)nativeListener=true;
            if(distance>audienceSquared)continue;
            // Native PlayerPrefs only guards chat messages; suppress the whole shared
            // bubble when any present potential observer opted out.
            if(!prefs.isEnabled(player.getUUID())){info.setReturnValue(0);return;}
            observers.add(player.getUUID());
        }
        if(!nativeListener||!awft$budget.admit(villager.getUUID(),observers,tick,
                Math.max(1,config.bubbleLifetimeTicks),config.maxMessagesPerPlayerPerMinute))info.setReturnValue(0);
    }
    @Inject(method="sendVillagerLine",at=@At("RETURN"),remap=false)
    private void awft$charge(MinecraftServer server,ServerLevel level,AbstractVillager villager,String text,double radius,long tick,PlayerPrefs prefs,CallbackInfoReturnable<Integer> info){
        if(info.getReturnValue()>0)WorldCharacters.current.ambientSent(villager.getUUID(),tick);
    }
    @Inject(method="spawnBubble",at=@At("HEAD"),cancellable=true,remap=false)
    private void awft$bubbles(ServerLevel level,AbstractVillager villager,String text,ChatFormatting color,long tick,CallbackInfo info){
        var profile=WorldCharacters.current.profile(villager.getUUID());
        if(profile!=null&&!WorldCharacters.flag(WorldCharacters.object(profile,"voice"),"bubbles"))info.cancel();
    }
    @ModifyArg(method="spawnBubble",at=@At(value="INVOKE",target="Lnet/minecraft/world/entity/EntityType;loadEntityRecursive(Lnet/minecraft/nbt/CompoundTag;Lnet/minecraft/world/level/Level;Ljava/util/function/Function;)Lnet/minecraft/world/entity/Entity;"),index=0,remap=false)
    private CompoundTag awft$visibility(CompoundTag tag){
        // Display's default 1.0 means 64*viewScale blocks. Tie its base range to the
        // configured native speech radius; this is a global setting, not per NPC.
        tag.putFloat("view_range",(float)(Math.max(0,config.radius)/64.0));return tag;
    }
    @Redirect(method="spawnBubble",at=@At(value="INVOKE",target="Lnet/minecraft/server/level/ServerLevel;addFreshEntity(Lnet/minecraft/world/entity/Entity;)Z"),remap=false)
    private boolean awft$created(ServerLevel receiver,Entity display,ServerLevel level,AbstractVillager villager,String text,ChatFormatting color,long tick){
        boolean added=receiver.addFreshEntity(display);
        if(!added)awft$budget.release(villager.getUUID(),tick);
        return added;
    }
    @Inject(method="onServerStopping",at=@At("RETURN"),remap=false)
    private void awft$clearBudget(CallbackInfo info){awft$budget.clear();}
    @Inject(method="villagerName",at=@At("HEAD"),cancellable=true,remap=false)
    private void awft$name(AbstractVillager villager,CallbackInfoReturnable<String> info){
        var profile=WorldCharacters.current.profile(villager.getUUID());
        if(WorldCharacters.current.enabled(profile))info.setReturnValue(WorldCharacters.limit(WorldCharacters.text(profile,"name"),64));
    }
}
