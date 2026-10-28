package worldfortwo.living.mixin;

import java.util.List;
import java.util.concurrent.ThreadLocalRandom;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.*;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;
import io.github.draysus.chattingvillagers.DialogueManager;
import io.github.draysus.chattingvillagers.VillagerContext;
import worldfortwo.living.WorldCharacters;

/** Read the acknowledged current registry at speech selection; no file polling. */
@Mixin(value=DialogueManager.class,remap=false)
public abstract class AmbientDialogueMixin {
    private static DialogueManager.SoloLine awft$line(VillagerContext context,String excluded,boolean reaction){
        List<WorldCharacters.AmbientLine> lines=WorldCharacters.current.ambientLines(context.states,context.weather,context.timeOfDay,reaction)
            .stream().filter(line->!line.id().equals(excluded)).toList();
        if(lines.isEmpty())return null;
        var selected=lines.get(ThreadLocalRandom.current().nextInt(lines.size()));
        var line=new DialogueManager.SoloLine();line.id=selected.id();line.type=reaction?"reaction":"solo";
        line.text=selected.text();line.weight=1.0;return line;
    }
    @Inject(method="pickSolo",at=@At("HEAD"),cancellable=true,remap=false)
    private void awft$solo(VillagerContext context,String excluded,CallbackInfoReturnable<DialogueManager.SoloLine> info){
        if(WorldCharacters.current.ambientProfile(context.states)!=null)info.setReturnValue(awft$line(context,excluded,false));
    }
    @Inject(method="pickReaction",at=@At("HEAD"),cancellable=true,remap=false)
    private void awft$reaction(VillagerContext context,String excluded,CallbackInfoReturnable<DialogueManager.SoloLine> info){
        if(WorldCharacters.current.ambientProfile(context.states)!=null)info.setReturnValue(awft$line(context,excluded,true));
    }
    @Inject(method="pickTradeReaction",at=@At("HEAD"),cancellable=true,remap=false)
    private void awft$trade(VillagerContext context,CallbackInfoReturnable<DialogueManager.SoloLine> info){
        if(WorldCharacters.current.ambientProfile(context.states)!=null)info.setReturnValue(awft$line(context,"",true));
    }
    @Inject(method="pickConversation",at=@At("HEAD"),cancellable=true,remap=false)
    private void awft$conversation(VillagerContext context,CallbackInfoReturnable<DialogueManager.Conversation> info){
        if(WorldCharacters.current.ambientProfile(context.states)==null)return;
        var pair=WorldCharacters.current.ambientExchange(context.states);
        if(pair.size()!=2){info.setReturnValue(null);return;}
        var conversation=new DialogueManager.Conversation();conversation.id="awft_dynamic_exchange";conversation.type="conversation";conversation.weight=1.0;
        var a=new DialogueManager.ConversationLine();a.speaker="A";a.text=pair.get(0);
        var b=new DialogueManager.ConversationLine();b.speaker="B";b.text=pair.get(1);
        conversation.lines=List.of(a,b);info.setReturnValue(conversation);
    }
}
