package worldfortwo.bridge.mixin;

import it.unimi.dsi.fastutil.longs.Long2ObjectOpenHashMap;
import net.minecraft.server.level.DistanceManager;
import net.minecraft.server.level.Ticket;
import net.minecraft.util.SortedArraySet;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.gen.Accessor;

@Mixin(value = DistanceManager.class, remap = false)
public interface DistanceManagerAccess {
    @Accessor("tickets") Long2ObjectOpenHashMap<SortedArraySet<Ticket<?>>> awftTickets();
}
