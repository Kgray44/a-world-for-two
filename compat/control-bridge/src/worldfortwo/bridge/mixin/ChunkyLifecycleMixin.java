package worldfortwo.bridge.mixin;

import worldfortwo.bridge.ControlBridge;

import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Pseudo;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

// DH 3.3.3 can first see spawn chunks before Chunky's ServerStartingEvent.
// Defer only the lazy listener registration until ServerStartedEvent. The original
// registration runs unchanged on the next chunk update; later failures still fail.
@Pseudo
@Mixin(targets = "com.seibel.distanthorizons.core.wrapperInterfaces.modAccessor.AbstractChunkyAccessor", remap = false)
public class ChunkyLifecycleMixin {
    @Inject(method = "tryRunFirstTimeSetup", at = @At("HEAD"), cancellable = true, remap = false)
    private void awftAwaitStartedServer(CallbackInfo callback) {
        if (!ControlBridge.serverStarted) callback.cancel();
    }
}
