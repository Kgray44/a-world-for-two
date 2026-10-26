package worldfortwo.bridge.mixin;

import net.neoforged.fml.event.config.ModConfigEvent;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Pseudo;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

/** Small Ships' config loader reopens a file even after FML has unloaded it. */
@Pseudo
@Mixin(targets = "com.talhanation.smallships.neoforge.common.CommonModBus", remap = false)
public class SmallShipsConfigLifecycleMixin {
    @Inject(method = "initRegisterConfigs", at = @At("HEAD"), cancellable = true, remap = false)
    private static void awftLoadOnlyAttachedConfigs(ModConfigEvent event, CallbackInfo callback) {
        // Loading and reloading retain every original correction and validation.
        // Unloading has already detached the file; there is nothing to load.
        if (event instanceof ModConfigEvent.Unloading) callback.cancel();
    }
}
