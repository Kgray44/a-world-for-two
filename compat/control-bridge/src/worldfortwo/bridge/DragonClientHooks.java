package worldfortwo.bridge;

import net.neoforged.api.distmarker.Dist;
import net.neoforged.bus.api.IEventBus;
import net.neoforged.fml.common.Mod;
import net.neoforged.neoforge.common.NeoForge;
import net.neoforged.neoforge.client.event.ClientPlayerNetworkEvent;
import net.neoforged.neoforge.client.event.RegisterClientReloadListenersEvent;
import net.minecraft.server.packs.resources.ResourceManagerReloadListener;

/** Client-only lifecycle. Its mirror never touches integrated-server variant data. */
@Mod(value="awft_control_bridge",dist=Dist.CLIENT)
public final class DragonClientHooks {
    public DragonClientHooks(IEventBus bus){
        NeoForge.EVENT_BUS.addListener(this::left);
        bus.addListener(this::reload);
    }
    private void left(ClientPlayerNetworkEvent.LoggingOut event){DragonTextureMirror.clearClient();}
    private void reload(RegisterClientReloadListenersEvent event){
        event.registerReloadListener((ResourceManagerReloadListener)manager->DragonTextureMirror.clearResources());
    }
}
