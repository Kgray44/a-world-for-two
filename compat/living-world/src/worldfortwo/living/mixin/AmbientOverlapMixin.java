package worldfortwo.living.mixin;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.*;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;
import net.minecraft.ChatFormatting;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.npc.AbstractVillager;
import io.github.draysus.chattingvillagers.ChattingVillagers;
import io.github.draysus.chattingvillagers.PlayerPrefs;
import tn.naizo.smartvillagers.SmartVillagers;
import worldfortwo.living.WorldCharacters;
@Mixin(value=ChattingVillagers.class,remap=false)
public abstract class AmbientOverlapMixin {
    @Inject(method="isExcluded",at=@At("HEAD"),cancellable=true,remap=false)
    private void awft$busy(AbstractVillager villager,CallbackInfoReturnable<Boolean> info){
        var profile=WorldCharacters.current.profile(villager.getUUID());
        if(profile!=null&&(!WorldCharacters.current.enabled(profile)||SmartVillagers.conversations().locks().owner(villager.getUUID()).isPresent()))info.setReturnValue(true);
    }
    @Inject(method="sendVillagerLine",at=@At("HEAD"),cancellable=true,remap=false)
    private void awft$cooldown(MinecraftServer server,ServerLevel level,AbstractVillager villager,String text,double radius,long tick,PlayerPrefs prefs,CallbackInfoReturnable<Integer> info){
        if(!WorldCharacters.current.ambientReady(villager.getUUID(),tick))info.setReturnValue(0);
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
    @Inject(method="villagerName",at=@At("HEAD"),cancellable=true,remap=false)
    private void awft$name(AbstractVillager villager,CallbackInfoReturnable<String> info){
        var profile=WorldCharacters.current.profile(villager.getUUID());
        if(WorldCharacters.current.enabled(profile))info.setReturnValue(WorldCharacters.limit(WorldCharacters.text(profile,"name"),64));
    }
}
