package worldfortwo.bridge;

import java.io.IOException;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.CompletableFuture;

/** Exercises the actual cleanup tail without constructing Level, entities or a controller. */
public final class BridgeCleanupProbe {
    private static int checks;
    private static void require(boolean okay,String why){if(!okay)throw new AssertionError(why);checks++;}
    public static void main(String[] args)throws Exception{
        var tail=new RetainedBridgeGlueInspection.CleanupTail();
        var future=new CompletableFuture<Void>();
        List<CompletableFuture<?>> pending=new ArrayList<>();pending.add(future);
        boolean[] held={true};int[] closes={0};List<String> calls=new ArrayList<>();
        RetainedBridgeGlueInspection.CleanupAttempt close=()->{closes[0]++;held[0]=false;};
        long unfinished=RetainedBridgeGlueInspection.CleanupTail.unfinished(pending);
        RetainedBridgeGlueInspection.CleanupTail.closeLeaseWhenReady(0,unfinished,close);
        require(unfinished==1&&held[0]&&closes[0]==0,"Pending shared future must hold lease");
        require(!tail.publish(false,()->calls.add("terminal-pending"),()->calls.add("progress")),"Pending resource receipt cannot end busy state");
        require(calls.equals(List.of("terminal-pending","progress")),"Immutable terminal must precede progress");
        tail.publish(false,()->{throw new AssertionError("No per-tick duplicate pending terminal");},()->calls.add("progress"));
        require(!future.isCancelled(),"Cleanup must not cancel shared futures");

        future.complete(null);unfinished=RetainedBridgeGlueInspection.CleanupTail.unfinished(pending);
        RetainedBridgeGlueInspection.CleanupTail.closeLeaseWhenReady(1,unfinished,close);
        require(unfinished==0&&held[0]&&closes[0]==0,"Failed ticket release must keep lease");
        boolean leaseFailed=false;
        try{RetainedBridgeGlueInspection.CleanupTail.closeLeaseWhenReady(0,unfinished,()->{throw new IOException("fixture lease close failure");});}
        catch(IOException expected){leaseFailed=true;}
        require(leaseFailed&&held[0],"Lease-close failure must remain owned for next tick");
        RetainedBridgeGlueInspection.CleanupTail.closeLeaseWhenReady(0,unfinished,close);
        require(!held[0]&&closes[0]==1,"Next cleanup tick must close once after real completion");
        require(tail.publish(true,()->calls.add("terminal-clean"),()->calls.add("progress")),"Only clean immutable publication may end busy state");
        require(calls.subList(calls.size()-2,calls.size()).equals(List.of("terminal-clean","progress")),"Final clean terminal must precede progress");

        var blocked=new RetainedBridgeGlueInspection.CleanupTail();int[] attempts={0};
        require(!blocked.publish(true,()->{attempts[0]++;throw new IOException("fixture terminal failure");},()->calls.add("progress")),"Failed immutable publication must retain busy");
        require(!blocked.publish(true,()->{attempts[0]++;},()->calls.add("progress"))&&attempts[0]==1,"Blocked publication must not spam immutable receipts each tick");
        blocked.retryReceipt();
        require(blocked.publish(true,()->attempts[0]++,()->{throw new IOException("fixture progress failure");}),"Progress failure must not suppress a clean immutable result");
        require(attempts[0]==2&&blocked.cleanPublished,"Explicit retry must publish the authoritative result");

        var failedFuture=new CompletableFuture<Void>();failedFuture.completeExceptionally(new IOException("fixture load failure"));
        require(RetainedBridgeGlueInspection.CleanupTail.unfinished(List.of(failedFuture))==0,"Exceptional completed future owns no pending work");
        System.out.println("PASS bridge cleanup fixtures="+checks+"; no Level/entity/world/controller constructed");
    }
}
