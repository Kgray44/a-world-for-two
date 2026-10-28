package worldfortwo.bridge.mixin;

import java.io.IOException;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Pseudo;
import org.spongepowered.asm.mixin.injection.*;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;
import worldfortwo.bridge.MoonlightSeedgenInitialization;

@Pseudo
@Mixin(targets="net.mehvahdjukaar.moonlight.core.pack.DynamicResourcesInternals",remap=false)
public abstract class MoonlightStateCommitMixin implements MoonlightSeedgenInitialization.StateObserved {
    @Inject(method="lambda$init$2",at=@At(value="INVOKE",target="Lnet/mehvahdjukaar/moonlight/api/resources/pack/GlobalCachedStrategy;writeNewState(Lnet/minecraft/server/packs/PackType;)V"),remap=false,require=1,expect=1,allow=1)
    private static void awft$beforeStateCommit(CallbackInfo ci)throws IOException{MoonlightSeedgenInitialization.beforeStateCommit();}
}
