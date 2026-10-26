package worldfortwo.bridge;

import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.levelgen.Heightmap;
import net.minecraft.world.phys.AABB;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.Map;

/** Searches only an already requested destination chunk. Never loads neighbors. */
public final class SafeLanding {
    public record Result(BlockPos position, int columns, Map<String, Integer> refusals) {}
    private record Column(int x, int z, int distance) {}
    private SafeLanding() {}

    public static Result find(ServerLevel level, ServerPlayer player, int x, int z, Number requestedY, String mode) {
        if (!mode.equals("surface") && !mode.equals("near-y")) throw new IllegalArgumentException("Unknown landing mode");
        if (mode.equals("near-y") && requestedY == null) throw new IllegalArgumentException("Choose a destination Y coordinate");
        if (level.dimensionType().hasCeiling() && mode.equals("surface"))
            throw new IllegalArgumentException("Choose a known safe Y coordinate in the Nether; the roof is not a landing surface");
        int chunkX = x >> 4, chunkZ = z >> 4;
        ArrayList<Column> columns = new ArrayList<>();
        for (int dx = -8; dx <= 8; dx++) for (int dz = -8; dz <= 8; dz++) {
            int bx = x + dx, bz = z + dz, distance = dx * dx + dz * dz;
            // A one-block margin keeps all nine safety columns inside this chunk.
            if (distance <= 64 && bx >> 4 == chunkX && bz >> 4 == chunkZ
                    && (bx & 15) >= 1 && (bx & 15) <= 14 && (bz & 15) >= 1 && (bz & 15) <= 14)
                columns.add(new Column(bx, bz, distance));
        }
        columns.sort(Comparator.comparingInt(Column::distance));
        Map<String, Integer> refusals = new LinkedHashMap<>();
        int examined = 0;
        for (Column column : columns) {
            examined++;
            int y = mode.equals("surface") ? level.getHeight(Heightmap.Types.MOTION_BLOCKING_NO_LEAVES, column.x(), column.z())
                : (int) Math.floor(requestedY.doubleValue());
            // Surface height comes from this column, not a structure bounding-box center.
            int range = mode.equals("surface") ? 2 : 8;
            for (int offset = 0; offset <= range; offset++) for (int sign : offset == 0 ? new int[]{1} : new int[]{1, -1}) {
                BlockPos feet = new BlockPos(column.x(), y + offset * sign, column.z());
                String reason = refusal(level, player, feet);
                if (reason == null) return new Result(feet, examined, refusals);
                refusals.merge(reason, 1, Integer::sum);
            }
        }
        return new Result(null, examined, refusals);
    }

    static String refusal(ServerLevel level, ServerPlayer player, BlockPos feet) {
        if (feet.getY() < level.getMinBuildHeight() + 1 || feet.getY() > level.getMaxBuildHeight() - 2
                || level.dimensionType().hasCeiling() && feet.getY() >= 127) return "height limit";
        AABB box = new AABB(feet.getX() + .2, feet.getY(), feet.getZ() + .2, feet.getX() + .8, feet.getY() + 1.8, feet.getZ() + .8);
        if (!level.getWorldBorder().isWithinBounds(box)) return "world border";
        var floor = level.getBlockState(feet.below());
        if (!floor.isFaceSturdy(level, feet.below(), Direction.UP)) return "no solid floor";
        if (!level.getBlockState(feet).isAir() || !level.getBlockState(feet.above()).isAir()) return "blocked headroom";
        for (int dx = -1; dx <= 1; dx++) for (int dz = -1; dz <= 1; dz++) {
            BlockPos near = feet.offset(dx, 0, dz);
            if (level.getChunkSource().getChunkNow(near.getX() >> 4, near.getZ() >> 4) == null) return "unloaded safety area";
            for (int dy = -1; dy <= 1; dy++) {
                var block = level.getBlockState(near.offset(0, dy, 0));
                if (!block.getFluidState().isEmpty()) return "water or lava";
                if (block.is(Blocks.FIRE) || block.is(Blocks.SOUL_FIRE) || block.is(Blocks.CACTUS) || block.is(Blocks.MAGMA_BLOCK)
                        || block.is(Blocks.CAMPFIRE) || block.is(Blocks.SOUL_CAMPFIRE) || block.is(Blocks.POWDER_SNOW)) return "nearby hazard";
            }
        }
        return level.noCollision(player, box) ? null : "entity or block collision";
    }
}
