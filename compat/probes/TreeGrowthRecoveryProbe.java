package worldfortwo.bridge;

/** Actual compiled recovery orchestration only; never constructs or starts a Minecraft level. */
public final class TreeGrowthRecoveryProbe {
    private static int passed;
    private static void require(boolean value){if(!value)throw new AssertionError("tree recovery contract");passed++;}
    public static void main(String[] ignored){
        int[] calls={0,0};
        var normal=TreeGrowthScope.captureThenRestore(()->calls[0]++,()->calls[1]++);
        require(normal.exactRestored()&&normal.captureFailure()==null&&calls[0]==1&&calls[1]==1);
        RuntimeException capture=new IllegalStateException("snapshot failed after writes");
        var noSnapshot=TreeGrowthScope.captureThenRestore(()->{throw capture;},()->calls[1]++);
        require(noSnapshot.exactRestored()&&noSnapshot.captureFailure()==capture&&calls[1]==2);
        AssertionError captureError=new AssertionError("native BE capture linkage/error");
        var noBE=TreeGrowthScope.captureThenRestore(()->{throw captureError;},()->calls[1]++);
        require(noBE.exactRestored()&&noBE.captureFailure()==captureError&&calls[1]==3);
        RuntimeException restoration=new IllegalStateException("restoration failed");
        var residual=TreeGrowthScope.captureThenRestore(()->calls[0]++,()->{throw restoration;});
        require(!residual.exactRestored()&&residual.restoreFailure()==restoration);
        var both=TreeGrowthScope.captureThenRestore(()->{throw capture;},()->{throw restoration;});
        require(!both.exactRestored()&&both.captureFailure()==capture&&both.restoreFailure()==restoration);
        LinkageError restoreError=new LinkageError("setter unavailable");
        var unavailable=TreeGrowthScope.captureThenRestore(()->{},()->{throw restoreError;});
        require(!unavailable.exactRestored()&&unavailable.restoreFailure()==restoreError);
        System.out.println("{\"passed\":"+passed+",\"native_game_started\":false,\"native_world_constructed\":false}");
    }
}
