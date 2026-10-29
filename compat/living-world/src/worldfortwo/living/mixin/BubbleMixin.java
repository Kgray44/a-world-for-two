package worldfortwo.living.mixin;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.*;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;
import net.minecraft.world.entity.npc.Villager;
import tn.naizo.smartvillagers.display.SpeechBubbles;
import worldfortwo.living.WorldCharacters;
@Mixin(value=SpeechBubbles.class,remap=false)
public abstract class BubbleMixin {
    @Inject(method="thinking",at=@At("HEAD"),cancellable=true,remap=false)
    private static void awft$thinking(Villager villager,String name,CallbackInfo info){
        var p=WorldCharacters.current.profile(villager.getUUID());
        if(p!=null&&!WorldCharacters.flag(WorldCharacters.object(p,"voice"),"bubbles"))info.cancel();
    }
    @Inject(method="say",at=@At("HEAD"),cancellable=true,remap=false)
    private static void awft$say(Villager villager,String name,String text,CallbackInfo info){
        var p=WorldCharacters.current.profile(villager.getUUID());
        if(p!=null&&!WorldCharacters.flag(WorldCharacters.object(p,"voice"),"bubbles"))info.cancel();
    }
}
