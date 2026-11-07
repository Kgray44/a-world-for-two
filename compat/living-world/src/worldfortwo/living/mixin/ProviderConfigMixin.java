package worldfortwo.living.mixin;

import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.*;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;
import tn.naizo.smartvillagers.ActivationMode;
import tn.naizo.smartvillagers.config.AiProviderType;
import tn.naizo.smartvillagers.config.SmartVillagersConfig;
import worldfortwo.living.WorldCharacters;
import worldfortwo.living.NativeRequestPolicy;

/** Apply the Studio's global OpenAI policy through upstream's existing asynchronous transport. */
@Mixin(value=SmartVillagersConfig.class,remap=false)
public abstract class ProviderConfigMixin {
    @Inject(method="get",at=@At("RETURN"),cancellable=true,remap=false)
    private static void awft$settings(CallbackInfoReturnable<SmartVillagersConfig.Snapshot> info){
        var base=info.getReturnValue();var settings=WorldCharacters.current.settings();
        var policy=NativeRequestPolicy.current();
        if(policy==null)try{policy=NativeRequestPolicy.select(WorldCharacters.current,null);}catch(Exception ignored){}
        if(!NativeRequestPolicy.credentialPresent())policy=null;
        String model=policy==null?"":policy.model();
        int tokens=policy==null?120:policy.responseTokens();
        int concurrency=Math.max(1,Math.min(2,WorldCharacters.integer(settings,"max_concurrent",2)));
        info.setReturnValue(new SmartVillagersConfig.Snapshot(
            base.proximityEnabled(),8.0,16.0,ActivationMode.PREFIX,"!",true,
            base.displayMode(),false,true,180,Math.max(3000L,base.playerCooldownMs()),Math.max(1,Math.min(60,WorldCharacters.integer(settings,"requests_per_minute",6))),concurrency,
            base.thinkingDelayMinTicks(),base.thinkingDelayMaxTicks(),false,
            NativeRequestPolicy.ENDPOINT,model,AiProviderType.OPENAI,tokens,
            "max_completion_tokens","AUTO",false,0.0,0.0,true,true,true,false,0,10,0));
    }
}
