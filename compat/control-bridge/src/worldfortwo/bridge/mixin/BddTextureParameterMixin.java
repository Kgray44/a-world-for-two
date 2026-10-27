package worldfortwo.bridge.mixin;

import com.google.gson.JsonElement;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.entity.Entity;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Pseudo;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Redirect;
import software.bluelib.api.utils.variant.ParameterUtils;
import worldfortwo.bridge.DragonTextureMirror;

/** Only the three texture-path lookups on the existing rendered dragon. */
@Pseudo
@Mixin(targets="com.bdc.bdd.api.entity.core_classes.BddBaseDragon",remap=false)
public abstract class BddTextureParameterMixin {
    @Redirect(method="getDragonLocation",at=@At(value="INVOKE",target="Lcom/bdc/bdd/api/entity/core_classes/BddBaseDragon;getParameterDataForVariant(Lnet/minecraft/resources/ResourceLocation;Ljava/lang/String;Ljava/lang/String;)Lcom/google/gson/JsonElement;"),require=3)
    private JsonElement awft$renderMetadata(ResourceLocation species,String variant,String key){
        JsonElement original=ParameterUtils.getParameterDataForVariant(species,variant,key,species.getPath());
        if(!((Entity)(Object)this).level().isClientSide())return original;
        return DragonTextureMirror.textureParameter(species,variant,key,original);
    }
}
