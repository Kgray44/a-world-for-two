package worldfortwo.bridge.mixin;

import net.minecraft.resources.ResourceLocation;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Pseudo;
import org.spongepowered.asm.mixin.injection.*;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;
import worldfortwo.bridge.MoonlightSeedgenInitialization;

@Pseudo
@Mixin(targets="net.mehvahdjukaar.moonlight.api.resources.pack.ResourceSink",remap=false)
public abstract class MoonlightSinkObserverMixin implements MoonlightSeedgenInitialization.ProductionObserved {
    @Inject(method="addBytes(Lnet/minecraft/resources/ResourceLocation;[B)V",at=@At("HEAD"),remap=false,require=1,expect=1,allow=1)
    private void awft$boundedProduction(ResourceLocation id,byte[] bytes,CallbackInfo ci){MoonlightSeedgenInitialization.produced(bytes);}

    @Inject(method={"addJson(Lnet/minecraft/resources/ResourceLocation;Lcom/google/gson/JsonElement;)V","addJsonUnlessPresent","addTextureIfNotPresent(Lnet/minecraft/server/packs/resources/ResourceManager;Lnet/minecraft/resources/ResourceLocation;Ljava/util/function/Supplier;)V","addTextureUnlessPresent"},
        at=@At(value="INVOKE",target="Lorg/apache/logging/log4j/Logger;error(Ljava/lang/String;Ljava/lang/Object;Ljava/lang/Object;)V"),remap=false,require=4,expect=4,allow=4)
    private void awft$sinkFailure(CallbackInfo ci){MoonlightSeedgenInitialization.resourceFailed();}

    @Inject(method="addAndCloseTexture(Lnet/minecraft/resources/ResourceLocation;Lnet/mehvahdjukaar/moonlight/api/resources/textures/TextureImage;Z)V",
        at=@At(value="INVOKE",target="Lorg/apache/logging/log4j/Logger;warn(Ljava/lang/String;Ljava/lang/Object;Ljava/lang/Object;Ljava/lang/Object;)V"),remap=false,require=1,expect=1,allow=1)
    private void awft$sinkTextureFailure(CallbackInfo ci){MoonlightSeedgenInitialization.resourceFailed();}
}
