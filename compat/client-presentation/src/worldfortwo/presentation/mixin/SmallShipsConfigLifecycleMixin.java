package worldfortwo.presentation.mixin;

import worldfortwo.presentation.SmallShipsConfigLifecycle;

import net.neoforged.fml.event.config.ModConfigEvent;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Pseudo;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

/** Remote SERVER configs have values, but no local TOML file to migrate. */
@Pseudo
@Mixin(targets = "com.talhanation.smallships.neoforge.common.CommonModBus", remap = false)
public class SmallShipsConfigLifecycleMixin {
    @Inject(method = "initRegisterConfigs(Lnet/neoforged/fml/event/config/ModConfigEvent;)V",
            at = @At("HEAD"), cancellable = true, remap = false)
    private static void awftKeepAppliedRemoteConfig(ModConfigEvent event, CallbackInfo callback) {
        if (SmallShipsConfigLifecycle.skipFileCallback(event)) callback.cancel();
    }
}
