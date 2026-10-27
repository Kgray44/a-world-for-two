package worldfortwo.bridge.mixin;

import com.llamalad7.mixinextras.injector.wrapoperation.Operation;
import com.llamalad7.mixinextras.injector.wrapoperation.WrapOperation;
import com.llamalad7.mixinextras.sugar.Local;
import mobius.seedrenderer.net.SeedShare;
import net.minecraft.client.Minecraft;
import net.neoforged.neoforge.network.handling.IPayloadContext;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Pseudo;
import org.spongepowered.asm.mixin.injection.At;
import worldfortwo.bridge.LithostitchedSeedgenCompat;

/** Client-only current-connection custody across the WHOLE original onWorld. */
@Pseudo
@Mixin(targets="mobius.seedrenderer.neoforge.SeedGenNeoForge",remap=false)
public abstract class LithostitchedSeedgenPacketMixin implements LithostitchedSeedgenCompat.AuthenticatedPacketGuard {
    @WrapOperation(method="lambda$onRegisterPayloads$0(Lmobius/seedrenderer/neoforge/SeedGenPayloads$SharedWorld;Lnet/neoforged/neoforge/network/handling/IPayloadContext;)V",
        at=@At(value="INVOKE",target="Lmobius/seedrenderer/net/SeedSharing;onWorld(Lmobius/seedrenderer/net/SeedShare$World;)V",remap=false),
        remap=false,require=1)
    private static void awft$currentConnection(SeedShare.World world,Operation<Void> original,@Local(argsOnly=true) IPayloadContext context) {
        var current=Minecraft.getInstance().getConnection();Object offered=context.listener();
        boolean live=current!=null&&offered==current&&context.connection()==current.getConnection()&&current.getConnection().isConnected();
        LithostitchedSeedgenCompat.withPacketContext(offered,current,live,()->original.call(world));
    }
}
