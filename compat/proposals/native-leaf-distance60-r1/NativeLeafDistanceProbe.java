package worldfortwo.bridge;
import net.minecraft.SharedConstants;
import net.minecraft.server.Bootstrap;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.LeavesBlock;
import net.minecraft.world.level.block.state.BlockState;
public final class NativeLeafDistanceProbe {
 static int checks;static void check(boolean v){checks++;if(!v)throw new AssertionError("leaf-distance boundary "+checks);}
 static boolean ok(boolean mode,BlockState a,BlockState b){return TreeGrowthScope.naturalLeafDistanceOnly(mode,a,b);}
 public static void main(String[]args){
  SharedConstants.tryDetectVersion();Bootstrap.bootStrap();
  BlockState a=Blocks.DARK_OAK_LEAVES.defaultBlockState().setValue(LeavesBlock.DISTANCE,4).setValue(LeavesBlock.PERSISTENT,false).setValue(LeavesBlock.WATERLOGGED,false);
  BlockState b=a.setValue(LeavesBlock.DISTANCE,3);
  check(ok(true,a,b));check(!ok(false,a,b));check(!ok(true,a,a));
  check(ok(true,a.setValue(LeavesBlock.DISTANCE,1),a.setValue(LeavesBlock.DISTANCE,7)));
  check(ok(true,a.setValue(LeavesBlock.DISTANCE,7),a.setValue(LeavesBlock.DISTANCE,1)));
  check(!ok(true,a,Blocks.BIRCH_LEAVES.defaultBlockState().setValue(LeavesBlock.DISTANCE,3)));
  check(!ok(true,a.setValue(LeavesBlock.PERSISTENT,true),b));
  check(!ok(true,a,b.setValue(LeavesBlock.PERSISTENT,true)));
  check(!ok(true,a.setValue(LeavesBlock.PERSISTENT,true),b.setValue(LeavesBlock.PERSISTENT,true)));
  check(!ok(true,a,b.setValue(LeavesBlock.WATERLOGGED,true)));
  check(!ok(true,a.setValue(LeavesBlock.WATERLOGGED,true),b.setValue(LeavesBlock.WATERLOGGED,true)));
  check(!ok(true,a,Blocks.OAK_LOG.defaultBlockState()));check(!ok(true,Blocks.OAK_LOG.defaultBlockState(),b));
  check(!ok(true,a,Blocks.AIR.defaultBlockState()));check(!ok(true,null,b));check(!ok(true,a,null));
  check(a.getValue(LeavesBlock.DISTANCE)==4&&b.getValue(LeavesBlock.DISTANCE)==3);
  boolean invalid=false;try{a.setValue(LeavesBlock.DISTANCE,0);}catch(IllegalArgumentException expected){invalid=true;}check(invalid);
  invalid=false;try{a.setValue(LeavesBlock.DISTANCE,8);}catch(IllegalArgumentException expected){invalid=true;}check(invalid);
  check(!TreeGrowthScope.ownedPreplantedPermission(true,false,true,true,false,false,false,true,false,false));
  System.out.println("{\"native_leaf_state_checks\":"+checks+",\"passed\":true,\"vanilla_registry_bootstrap\":true,\"world_started\":false}");
 }
}
