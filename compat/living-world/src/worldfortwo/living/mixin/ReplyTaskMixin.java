package worldfortwo.living.mixin;

import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Unique;
import tn.naizo.smartvillagers.schedule.ReplyDelayQueue;
import worldfortwo.living.*;

@Mixin(value=ReplyDelayQueue.Task.class,remap=false)
public abstract class ReplyTaskMixin implements ReplyBindingAccess {
    @Unique private ReplyBinding awft$replyBinding;
    public ReplyBinding awft$binding(){return awft$replyBinding;}
    public void awft$bind(ReplyBinding binding){awft$replyBinding=binding;}
}
