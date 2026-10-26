package worldfortwo.bridge.mixin;

import it.unimi.dsi.fastutil.longs.Long2ObjectLinkedOpenHashMap;
import net.minecraft.server.level.ChunkHolder;
import net.minecraft.server.level.ChunkMap;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.gen.Accessor;

@Mixin(value = ChunkMap.class, remap = false)
public interface ChunkMapAccess {
    @Accessor("visibleChunkMap") Long2ObjectLinkedOpenHashMap<ChunkHolder> awftVisibleChunks();
    @Accessor("pendingUnloads") Long2ObjectLinkedOpenHashMap<ChunkHolder> awftPendingUnloads();
}
