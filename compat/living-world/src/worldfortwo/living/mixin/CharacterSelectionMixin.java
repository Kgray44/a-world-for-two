package worldfortwo.living.mixin;
import java.util.List;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.*;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;
import tn.naizo.smartvillagers.chat.*;
import worldfortwo.living.WorldCharacters;
@Mixin(value=VillagerSelector.class,remap=false)
public abstract class CharacterSelectionMixin {
    @Inject(method="findCandidates",at=@At("RETURN"),cancellable=true,remap=false)
    private static void awft$namedOnly(CallbackInfoReturnable<List<VillagerCandidate>> info){
        info.setReturnValue(info.getReturnValue().stream().filter(c->WorldCharacters.current.enabled(WorldCharacters.current.profile(c.villager().getUUID()))).toList());
    }
}
