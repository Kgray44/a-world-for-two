package worldfortwo.bridge.mixin;

import com.llamalad7.mixinextras.injector.wrapoperation.Operation;
import com.llamalad7.mixinextras.injector.wrapoperation.WrapOperation;
import com.llamalad7.mixinextras.sugar.Local;
import java.util.List;
import net.minecraft.server.packs.PackResources;
import net.minecraft.server.packs.PackType;
import net.minecraft.server.packs.resources.MultiPackResourceManager;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Pseudo;
import org.spongepowered.asm.mixin.injection.At;
import worldfortwo.bridge.MoonlightSeedgenInitialization;

/** Immediately after opening the original manager, before RegistryDataLoader. */
@Pseudo
@Mixin(targets="mobius.seedrenderer.dh.ClientWorldgen",remap=false)
public abstract class MoonlightSeedgenResourcesMixin {
    @WrapOperation(method="attempt(ZZ)Lnet/minecraft/core/RegistryAccess$Frozen;",
        at=@At(value="NEW",target="net/minecraft/server/packs/resources/MultiPackResourceManager",remap=false),
        remap=false,require=1,expect=1,allow=1)
    private static MultiPackResourceManager awft$earlyServerData(PackType type,List<PackResources> opened,
            Operation<MultiPackResourceManager> original,@Local(argsOnly=true,ordinal=0) boolean withMods)throws Throwable {
        MultiPackResourceManager manager=original.call(type,opened);
        try{if(withMods)MoonlightSeedgenInitialization.initialize(type,opened,manager);return manager;}
        catch(Throwable failure){
            // Constructor result has not been assigned to SeedGen's try-with-resources yet.
            try{manager.close();}catch(Throwable close){failure.addSuppressed(close);}throw failure;
        }
    }
}
