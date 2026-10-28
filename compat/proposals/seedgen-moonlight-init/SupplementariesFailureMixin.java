package worldfortwo.bridge.mixin;

import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Pseudo;
import org.spongepowered.asm.mixin.injection.*;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;
import worldfortwo.bridge.MoonlightSeedgenInitialization;

@Pseudo
@Mixin(targets="net.mehvahdjukaar.supplementaries.dynamicpack.ModServerDynamicResources",remap=false)
public abstract class SupplementariesFailureMixin implements MoonlightSeedgenInitialization.SupplementariesObserved {
    @Inject(method={"lambda$addSignPostRecipes$2","lambda$addCannonBoatRecipes$1"},
        at=@At(value="INVOKE",target="Lorg/apache/logging/log4j/Logger;error(Ljava/lang/String;Ljava/lang/Object;Ljava/lang/Object;)V"),remap=false,require=2,expect=2,allow=2)
    private static void awft$recipeFailure(CallbackInfo ci){MoonlightSeedgenInitialization.resourceFailed();}
}
