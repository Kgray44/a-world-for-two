package worldfortwo.bridge.mixin;

import net.minecraft.resources.ResourceLocation;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Pseudo;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;
import worldfortwo.bridge.DragonTextureMirror;

/** Observe the native model's final gender/layer resource without replacing it. */
@Pseudo
@Mixin(targets="com.bdc.bdd.api.model.BddDragonModel",remap=false)
public abstract class BddTextureResourceMixin {
    @Inject(method="getTextureResource(Lcom/bdc/bdd/api/entity/BddDragon;Lsoftware/bluelib/loader/renderer/base/BlueRenderer;)Lnet/minecraft/resources/ResourceLocation;",at=@At("RETURN"),require=1)
    private void awft$resourceWitness(CallbackInfoReturnable<ResourceLocation> result){
        DragonTextureMirror.checkResource(result.getReturnValue());
    }
}
