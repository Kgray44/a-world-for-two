package worldfortwo.bridge.mixin;

import net.minecraft.server.level.ServerChunkCache;
import net.minecraft.server.level.ChunkResult;
import net.minecraft.world.level.chunk.ChunkAccess;
import net.minecraft.world.level.chunk.status.ChunkStatus;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.gen.Invoker;
import java.util.concurrent.CompletableFuture;

/** Public getChunkFuture performs a managed wait on the server thread; this method only queues. */
@Mixin(ServerChunkCache.class)
public interface ChunkCacheAccess {
    @Invoker("getChunkFutureMainThread")
    CompletableFuture<ChunkResult<ChunkAccess>> awftQueueChunk(int x,int z,ChunkStatus status,boolean create);
}
