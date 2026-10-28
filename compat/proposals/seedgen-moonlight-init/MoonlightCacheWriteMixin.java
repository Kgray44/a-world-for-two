package worldfortwo.bridge.mixin;

import net.minecraft.resources.ResourceLocation;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Pseudo;
import org.spongepowered.asm.mixin.injection.*;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;
import worldfortwo.bridge.MoonlightSeedgenInitialization;

@Pseudo
@Mixin(targets="net.mehvahdjukaar.moonlight.api.resources.pack.CachePathPackResources",remap=false)
public abstract class MoonlightCacheWriteMixin implements MoonlightSeedgenInitialization.WriteObserved {
    @Inject(method="addResource(Lnet/minecraft/resources/ResourceLocation;[B)V",at=@At("HEAD"),remap=false,require=1,expect=1,allow=1)
    private void awft$boundedNativeWrite(ResourceLocation id,byte[] bytes,CallbackInfo ci){MoonlightSeedgenInitialization.beforeWrite(this,id,bytes);}
}
