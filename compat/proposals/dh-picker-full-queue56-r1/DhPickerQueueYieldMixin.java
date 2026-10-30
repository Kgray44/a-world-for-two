package worldfortwo.bridge.mixin;

import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Pseudo;

/** The original plugin changes only one attested native branch; no upstream body is copied. */
@Pseudo
@Mixin(targets="com.seibel.distanthorizons.core.util.threading.PriorityTaskPicker", remap=false)
public abstract class DhPickerQueueYieldMixin {}
