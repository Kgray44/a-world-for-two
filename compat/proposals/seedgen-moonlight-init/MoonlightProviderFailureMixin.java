package worldfortwo.bridge.mixin;

import net.mehvahdjukaar.moonlight.api.misc.IProgressTracker;
import net.mehvahdjukaar.moonlight.api.resources.pack.ResourceSink;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Pseudo;
import org.spongepowered.asm.mixin.injection.*;
import org.spongepowered.asm.mixin.injection.callback.*;
import worldfortwo.bridge.MoonlightSeedgenInitialization;

/** Observe native failures that Moonlight otherwise logs and absorbs. */
@Pseudo
@Mixin(targets="net.mehvahdjukaar.moonlight.api.resources.pack.DynamicResourcesProvider",remap=false)
public abstract class MoonlightProviderFailureMixin implements MoonlightSeedgenInitialization.GenerationObserved {
    @Inject(method="reload",at=@At(value="INVOKE",target="Lorg/apache/logging/log4j/Logger;error(Ljava/lang/String;Ljava/lang/Object;Ljava/lang/Object;)V"),remap=false,require=1,expect=1,allow=1)
    private void awft$reloadFailure(CallbackInfo ci){MoonlightSeedgenInitialization.generationFailed(this);}

    @Inject(method="runGenerationPipeline",at=@At(value="INVOKE",target="Lorg/apache/logging/log4j/Logger;error(Ljava/lang/String;Ljava/lang/Throwable;)V"),remap=false,require=2,expect=2,allow=2)
    private void awft$pipelineFailure(CallbackInfo ci){MoonlightSeedgenInitialization.generationFailed(this);}

    @Inject(method="lambda$runGenerationPipeline$2",at=@At("HEAD"),remap=false,require=1,expect=1,allow=1)
    private static void awft$taskFailure(IProgressTracker.Task task,ResourceSink sink,Throwable failure,CallbackInfoReturnable<ResourceSink> ci){
        MoonlightSeedgenInitialization.taskFailed(task,failure);
    }
}
