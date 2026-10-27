package worldfortwo.bridge;

import net.neoforged.api.distmarker.Dist;
import net.neoforged.bus.api.IEventBus;
import net.neoforged.fml.common.Mod;
import net.neoforged.neoforge.client.event.ClientPlayerNetworkEvent;
import net.neoforged.neoforge.client.event.ClientTickEvent;
import net.neoforged.neoforge.common.NeoForge;
import net.minecraft.client.Minecraft;
import java.nio.file.Path;
import java.util.LinkedHashMap;
import net.minecraft.core.registries.Registries;
import net.minecraft.resources.ResourceKey;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.chunk.ChunkGenerator;

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

    /** Explicit private QA diagnostic; no automatic gameplay export. */
    public static void writeEffectiveDiagnostic(Path directory,String id,net.minecraft.core.RegistryAccess.Frozen expected)throws Throwable {
        Minecraft client=Minecraft.getInstance();if(!client.isSameThread())throw new IllegalStateException("Capture actual client inputs on its owner thread");
        var capture=LithostitchedSeedgenCompat.captureDiagnostic();
        if(capture.registry()!=expected)throw new IllegalStateException("Native cached registry changed after the codec export; preserve both generations separately");
        var generators=new LinkedHashMap<ResourceKey<Level>,ChunkGenerator>();
        for(var entry:capture.stems().entrySet())generators.put(ResourceKey.create(Registries.DIMENSION,entry.getKey().location()),entry.getValue().generator());
        NativeWorldgenWitnessTask.start(capture.registry(),generators,directory,id,"current_selected_client_stems",
            client::execute,()->client.isSameThread()&&LithostitchedSeedgenCompat.diagnosticStillCurrent(capture));
    }
}
