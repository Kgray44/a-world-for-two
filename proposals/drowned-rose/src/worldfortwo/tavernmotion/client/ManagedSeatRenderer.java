package worldfortwo.tavernmotion.client;

import net.minecraft.client.renderer.entity.NoopRenderer;
import net.neoforged.api.distmarker.Dist;
import net.neoforged.fml.common.EventBusSubscriber;
import net.neoforged.bus.api.SubscribeEvent;
import net.neoforged.neoforge.client.event.EntityRenderersEvent;
import worldfortwo.tavern.ManagedSeat;

/** The native chair remains the visible furnishing; only its passenger renders. */
@EventBusSubscriber(modid="awft_tavern",bus=EventBusSubscriber.Bus.MOD,value=Dist.CLIENT)
public final class ManagedSeatRenderer {
    @SubscribeEvent public static void register(EntityRenderersEvent.RegisterRenderers event){
        event.registerEntityRenderer(ManagedSeat.TYPE.get(),NoopRenderer::new);
    }
}
