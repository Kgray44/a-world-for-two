package worldfortwo.living.mixin;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.*;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;
import net.minecraft.world.entity.npc.Villager;
import tn.naizo.smartvillagers.villager.*;
import worldfortwo.living.WorldCharacters;
@Mixin(value=VillagerPersona.class,remap=false)
public abstract class PersonaMixin {
    @Inject(method="from",at=@At("RETURN"),cancellable=true,remap=false)
    private static void awft$profile(Villager villager,CallbackInfoReturnable<VillagerPersona> info){
        var profile=WorldCharacters.current.profile(villager.getUUID());if(!WorldCharacters.current.enabled(profile))return;
        WorldCharacters.current.memory(VillagerAiData.get(villager).memory(),villager.getUUID());
        var p=WorldCharacters.object(profile,"personality");var base=info.getReturnValue();
        String traits=WorldCharacters.array(p,"traits").toString();
        info.setReturnValue(new VillagerPersona(WorldCharacters.limit(WorldCharacters.text(profile,"name"),64),WorldCharacters.limit(traits,500),WorldCharacters.limit(WorldCharacters.text(p,"speaking_style"),600),WorldCharacters.limit(WorldCharacters.text(p,"backstory"),1500),base.professionLabel(),base.professionKey()));
    }
}
