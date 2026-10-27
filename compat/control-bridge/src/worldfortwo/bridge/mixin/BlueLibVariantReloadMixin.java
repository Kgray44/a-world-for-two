package worldfortwo.bridge.mixin;

import net.minecraft.server.MinecraftServer;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Pseudo;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;
import worldfortwo.bridge.DragonTextureMirror;
import java.util.List;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.Executor;

/** Observe actual pinned asynchronous cache completion, never replace its future. */
@Pseudo
@Mixin(targets="software.bluelib.loader.cache.ResourceCache$Server",remap=false)
public abstract class BlueLibVariantReloadMixin {
    @Inject(method="reload(Ljava/util/List;Lnet/minecraft/server/MinecraftServer;Ljava/util/concurrent/Executor;Ljava/util/concurrent/Executor;)Ljava/util/concurrent/CompletableFuture;",at=@At("RETURN"),require=1)
    private static void awft$completedVariants(List<?> providers,MinecraftServer server,Executor background,Executor apply,CallbackInfoReturnable<CompletableFuture<Void>> result){
        DragonTextureMirror.trackReload(server,result.getReturnValue());
    }
}
