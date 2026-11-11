import net.minecraft.world.level.levelgen.structure.placement.RandomSpreadStructurePlacement;
import net.minecraft.world.level.levelgen.structure.placement.RandomSpreadType;

/** Offline engine-API vectors only: no Bootstrap, loader, mods, server or world. */
public final class RandomSpreadProbe {
    public static void main(String[] ignored) {
        long[] seeds={0L,1L,-12345678912345L,Long.MIN_VALUE,Long.MAX_VALUE};
        int[][] profiles={{80,40},{76,40},{96,32},{92,32},{141,87},{160,64}};
        int[] salts={0,7,613,Integer.MAX_VALUE};
        int[][] points={{0,0},{-1,-1},{-80,80},{-2048,1536},{1536,-2048},{1875000,-1875000}};
        for(long seed:seeds)for(int[] profile:profiles)for(int salt:salts)
            for(RandomSpreadType spread:RandomSpreadType.values())for(int[] point:points){
                var placement=new RandomSpreadStructurePlacement(profile[0],profile[1],spread,salt);
                var result=placement.getPotentialStructureChunk(seed,point[0],point[1]);
                System.out.println("AWFT_GRID "+seed+","+profile[0]+","+profile[1]+","+salt+","+
                    spread.getSerializedName()+","+point[0]+","+point[1]+","+result.x+","+result.z);
            }
    }
}
