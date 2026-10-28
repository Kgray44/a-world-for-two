package worldfortwo.living.mixin;

import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.*;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;
import tn.naizo.smartvillagers.ActivationMode;
import tn.naizo.smartvillagers.config.AiProviderType;
import tn.naizo.smartvillagers.config.SmartVillagersConfig;
import worldfortwo.living.WorldCharacters;

/** Apply the Studio's global OpenAI policy through upstream's existing asynchronous transport. */
@Mixin(value=SmartVillagersConfig.class,remap=false)
public abstract class ProviderConfigMixin {
    @Inject(method="get",at=@At("RETURN"),cancellable=true,remap=false)
    private static void awft$settings(CallbackInfoReturnable<SmartVillagersConfig.Snapshot> info){
        var base=info.getReturnValue();var settings=WorldCharacters.current.settings();
        boolean enabled=WorldCharacters.flag(settings,"external_enabled")&&WorldCharacters.text(settings,"provider").equals("openai");
        String model=enabled?WorldCharacters.limit(WorldCharacters.text(settings,"model"),120):"";
        int concurrency=Math.max(1,Math.min(2,WorldCharacters.integer(settings,"max_concurrent",2)));
        info.setReturnValue(new SmartVillagersConfig.Snapshot(
            base.proximityEnabled(),8.0,16.0,ActivationMode.PREFIX,"!",true,
            base.displayMode(),false,true,180,Math.max(3000L,base.playerCooldownMs()),12,concurrency,
            base.thinkingDelayMinTicks(),base.thinkingDelayMaxTicks(),false,
            "https://api.openai.com/v1/chat/completions",model,AiProviderType.OPENAI,120,
            "max_completion_tokens","AUTO",false,0.0,0.0,true,true,true,false,0,10,0));
    }
}
