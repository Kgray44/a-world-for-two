package worldfortwo.living.mixin;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.*;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.npc.AbstractVillager;
import io.github.draysus.chattingvillagers.VillagerContext;
import worldfortwo.living.WorldCharacters;
@Mixin(value=VillagerContext.class,remap=false)
public abstract class AmbientContextMixin {
    @Inject(method="read",at=@At("RETURN"),remap=false)
    private static void awft$district(ServerLevel level,AbstractVillager villager,int radius,CallbackInfoReturnable<VillagerContext> info){
        String district=WorldCharacters.current.district(villager.getUUID(),level.dimension().location().toString(),villager.getX(),villager.getY(),villager.getZ());
        if(!district.isBlank())info.getReturnValue().states.add("awft_district_"+district);
        var profile=WorldCharacters.current.profile(villager.getUUID());
        if(WorldCharacters.current.enabled(profile))info.getReturnValue().states.add("awft_npc_"+WorldCharacters.text(profile,"id"));
    }
}
