package worldfortwo.living.mixin;
import java.util.UUID;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.*;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;
import tn.naizo.smartvillagers.villager.VillagerMemory;
import worldfortwo.living.WorldCharacters;
@Mixin(value=VillagerMemory.class,remap=false)
public abstract class MemoryMixin {
    @Inject(method="remember",at=@At("HEAD"),cancellable=true,remap=false)
    private void awft$optIn(UUID player,String message,String reply,CallbackInfo info){
        if(!WorldCharacters.memoryEnabled(this))info.cancel();
    }
}
