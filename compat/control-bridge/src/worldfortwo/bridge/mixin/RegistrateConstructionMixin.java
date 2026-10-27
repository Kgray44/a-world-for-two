package worldfortwo.bridge.mixin;

import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Pseudo;

/** No upstream method is copied or replaced. The plugin verifies and adds only
 * the native synchronized access bit to both pinned registration/callback writers.
 */
@Pseudo
@Mixin(targets="com.tterrag.registrate.AbstractRegistrate", remap=false)
public abstract class RegistrateConstructionMixin {}
