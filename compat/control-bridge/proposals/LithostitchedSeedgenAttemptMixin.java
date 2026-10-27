package worldfortwo.bridge.mixin;

import com.llamalad7.mixinextras.injector.wrapmethod.WrapMethod;
import com.llamalad7.mixinextras.injector.wrapoperation.Operation;
import java.util.List;
import net.minecraft.core.Registry;
import net.minecraft.core.RegistryAccess;
import net.minecraft.world.level.dimension.LevelStem;
import org.objectweb.asm.Opcodes;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Pseudo;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Redirect;
import worldfortwo.bridge.LithostitchedSeedgenCompat;
import worldfortwo.bridge.LithostitchedSeedgenLoadScope;

@Pseudo
@Mixin(targets="mobius.seedrenderer.dh.ClientWorldgen",remap=false)
public abstract class LithostitchedSeedgenAttemptMixin implements LithostitchedSeedgenCompat.IsolatedAttemptGuard {
    private static final String ATTEMPT="attempt(ZZ)Lnet/minecraft/core/RegistryAccess$Frozen;";
    @WrapMethod(method=ATTEMPT,remap=false)
    private static RegistryAccess.Frozen awft$privateAttempt(boolean mods,boolean wholeSet,Operation<RegistryAccess.Frozen> original) {
        return LithostitchedSeedgenCompat.isolateAttempt(mods,()->original.call(mods,wholeSet));
    }
    @Redirect(method=ATTEMPT,at=@At(value="FIELD",target="Lmobius/seedrenderer/dh/ClientWorldgen;stems:Lnet/minecraft/core/Registry;",opcode=Opcodes.PUTSTATIC,remap=false),remap=false,require=1)
    private static void awft$captureStems(Registry<LevelStem> value){LithostitchedSeedgenLoadScope.writeStems(value);}
    @Redirect(method=ATTEMPT,at=@At(value="FIELD",target="Lmobius/seedrenderer/dh/ClientWorldgen;stems:Lnet/minecraft/core/Registry;",opcode=Opcodes.GETSTATIC,remap=false),remap=false,require=1)
    private static Registry<LevelStem> awft$currentStems(){return LithostitchedSeedgenLoadScope.readStems();}
    @Redirect(method=ATTEMPT,at=@At(value="FIELD",target="Lmobius/seedrenderer/dh/ClientWorldgen;dataPackNames:Ljava/util/List;",opcode=Opcodes.PUTSTATIC,remap=false),remap=false,require=1)
    private static void awft$capturePackNames(List<String> value){LithostitchedSeedgenLoadScope.writeNames(value);}
}
