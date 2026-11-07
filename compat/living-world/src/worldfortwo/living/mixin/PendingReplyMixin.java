package worldfortwo.living.mixin;

import org.spongepowered.asm.mixin.*;
import org.spongepowered.asm.mixin.injection.*;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;
import net.minecraft.server.MinecraftServer;
import tn.naizo.smartvillagers.display.ResponseDispatcher;
import tn.naizo.smartvillagers.schedule.PendingResponseQueue;
import tn.naizo.smartvillagers.schedule.ReplyDelayQueue;
import tn.naizo.smartvillagers.session.ConversationLockManager;
import tn.naizo.smartvillagers.session.ConversationSessionManager;
import worldfortwo.living.*;

@Mixin(value=PendingResponseQueue.PendingResponse.class,remap=false)
public abstract class PendingReplyMixin implements ReplyBindingAccess {
    @Shadow @Final private ReplyDelayQueue.Task task;
    public ReplyBinding awft$binding(){return ((ReplyBindingAccess)(Object)task).awft$binding();}
    public void awft$bind(ReplyBinding binding){((ReplyBindingAccess)(Object)task).awft$bind(binding);}

    @Inject(method="deliver",at=@At("HEAD"),cancellable=true,remap=false)
    private static void awft$currentReply(ReplyDelayQueue.Task task,MinecraftServer server,ResponseDispatcher dispatcher,
                                         ConversationSessionManager sessions,ConversationLockManager locks,CallbackInfo info){
        ReplyBinding binding=((ReplyBindingAccess)(Object)task).awft$binding();
        if(binding==null||!binding.current(server)){
            // Native's ordinary drop path releases this exact villager/player lock.
            // Cancel before dispatch, memory writes, session touch or afterDelivery.
            locks.unlock(task.villagerId,task.playerId);
            info.cancel();
        }
    }
}
