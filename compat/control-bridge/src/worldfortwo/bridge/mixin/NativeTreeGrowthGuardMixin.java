package worldfortwo.bridge.mixin;

import net.minecraft.core.BlockPos;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.material.FluidState;
import net.minecraft.world.level.block.entity.BlockEntity;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;
import worldfortwo.bridge.TreeGrowthScope;

/** PROPOSAL: dedicated-server only; active solely in a leased tree call. */
@Mixin(value=Level.class,priority=2500)
public abstract class NativeTreeGrowthGuardMixin {
    @Inject(method="getBlockState(Lnet/minecraft/core/BlockPos;)Lnet/minecraft/world/level/block/state/BlockState;",at=@At("HEAD"),require=1)
    private void awftTreeRead(BlockPos pos,CallbackInfoReturnable<BlockState> ci){TreeGrowthScope.read((Level)(Object)this,pos);}
    @Inject(method="getFluidState(Lnet/minecraft/core/BlockPos;)Lnet/minecraft/world/level/material/FluidState;",at=@At("HEAD"),require=1)
    private void awftTreeFluid(BlockPos pos,CallbackInfoReturnable<FluidState> ci){TreeGrowthScope.read((Level)(Object)this,pos);}
    @Inject(method="getBlockEntity(Lnet/minecraft/core/BlockPos;)Lnet/minecraft/world/level/block/entity/BlockEntity;",at=@At("HEAD"),require=1)
    private void awftTreeBE(BlockPos pos,CallbackInfoReturnable<BlockEntity> ci){TreeGrowthScope.read((Level)(Object)this,pos);}
    @Inject(method="setBlock(Lnet/minecraft/core/BlockPos;Lnet/minecraft/world/level/block/state/BlockState;II)Z",at=@At("HEAD"),require=1)
    private void awftTreeWrite(BlockPos pos,BlockState state,int flags,int depth,CallbackInfoReturnable<Boolean> ci){TreeGrowthScope.write((Level)(Object)this,pos,state);}
}
