package worldfortwo.bridge.mixin;

import com.google.gson.JsonElement;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.packs.resources.Resource;
import net.minecraft.server.packs.resources.ResourceManager;
import java.io.IOException;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Pseudo;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Redirect;
import software.bluelib.api.utils.variant.ParameterUtils;
import worldfortwo.bridge.DragonTextureMirror;

/** The native glow layer has a separate parameter lookup before selecting its mask. */
@Pseudo
@Mixin(targets="com.bdc.bdd.api.render.layer.DragonGlowLayer",remap=false)
public abstract class BddGlowParameterMixin {
    @Redirect(method="render(Lsoftware/bluelib/loader/renderer/context/IRenderContext;)V",at=@At(value="INVOKE",target="Lcom/bdc/bdd/api/entity/BddDragon;getParameterDataForVariant(Lnet/minecraft/resources/ResourceLocation;Ljava/lang/String;Ljava/lang/String;)Lcom/google/gson/JsonElement;"),require=1)
    private JsonElement awft$glowMetadata(ResourceLocation species,String variant,String key){
        JsonElement original=ParameterUtils.getParameterDataForVariant(species,variant,key,species.getPath());
        return DragonTextureMirror.textureParameter(species,variant,key,original);
    }
    @Redirect(method="render(Lsoftware/bluelib/loader/renderer/context/IRenderContext;)V",at=@At(value="INVOKE",target="Lnet/minecraft/server/packs/resources/ResourceManager;getResourceOrThrow(Lnet/minecraft/resources/ResourceLocation;)Lnet/minecraft/server/packs/resources/Resource;"),require=1)
    private Resource awft$nativeGlowResource(ResourceManager manager,ResourceLocation resource)throws IOException{
        DragonTextureMirror.checkResource(manager,resource);
        return manager.getResourceOrThrow(resource);
    }
}
