package worldfortwo.bridge.mixin;

import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Pseudo;

/** The pinned plugin adds only the existing resources-map monitor to its native writer. */
@Pseudo
@Mixin(targets="plus.dragons.createdragonsplus.data.runtime.RuntimePackResources",remap=false)
public abstract class CdpRuntimeCacheWriteMixin {}
