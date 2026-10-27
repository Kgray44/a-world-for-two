package worldfortwo.bridge;

import net.neoforged.api.distmarker.Dist;
import net.neoforged.bus.api.IEventBus;
import net.neoforged.fml.common.Mod;
import net.neoforged.neoforge.client.event.ClientPlayerNetworkEvent;
import net.neoforged.neoforge.client.event.ClientTickEvent;
import net.neoforged.neoforge.common.NeoForge;
import net.minecraft.client.Minecraft;

/** Dedicated-safe client entrypoint. Event player/connection may legitimately be null. */
@Mod(value="awft_control_bridge",dist=Dist.CLIENT)
public final class LithostitchedSeedgenClientHooks {
    public LithostitchedSeedgenClientHooks(IEventBus modBus) {
        NeoForge.EVENT_BUS.addListener(this::left);
        NeoForge.EVENT_BUS.addListener(this::joined);
        NeoForge.EVENT_BUS.addListener(this::tick);
        LithostitchedSeedgenCompat.installLifecycleHook();
    }
    private void left(ClientPlayerNetworkEvent.LoggingOut event){LithostitchedSeedgenCompat.disconnect();}
    private void joined(ClientPlayerNetworkEvent.LoggingIn event){integrated();}
    private void tick(ClientTickEvent.Post event){integrated();LithostitchedSeedgenCompat.pollCleanup();}
    private void integrated(){if(Minecraft.getInstance().hasSingleplayerServer())LithostitchedSeedgenCompat.observedIntegratedServer();}
}
