import worldfortwo.living.RequestSlots;
import java.util.concurrent.*;

/** Actual asynchronous ownership checks, without Minecraft or a provider. */
public final class RequestSlotsSelfTest {
    private static void require(boolean value){if(!value)throw new AssertionError("Request ownership differs");}
    public static void main(String[] args)throws Exception{
        RequestSlots<String> slots=new RequestSlots<>();
        require(slots.acquire(2)==null);slots.open();
        var queued=slots.acquire(2);var network=slots.acquire(2);
        require(queued!=null&&network!=null&&slots.acquire(2)==null&&network.start());
        require(!network.start());
        ThreadPoolExecutor worker=new ThreadPoolExecutor(1,1,0,TimeUnit.SECONDS,new ArrayBlockingQueue<>(2));
        CountDownLatch occupied=new CountDownLatch(1),release=new CountDownLatch(1);
        worker.execute(()->{occupied.countDown();try{release.await();}catch(InterruptedException ignored){}});
        require(occupied.await(2,TimeUnit.SECONDS));
        worker.execute(()->queued.complete("must never run"));
        slots.close("server stopping");worker.shutdownNow();release.countDown();
        require(queued.future().get(1,TimeUnit.SECONDS).equals("server stopping"));
        require(network.future().get(1,TimeUnit.SECONDS).equals("server stopping"));
        require(!queued.start()&&slots.active()==1);
        slots.open();var fresh=slots.acquire(2);require(fresh!=null&&slots.acquire(2)==null);
        network.complete("late upstream completion");network.complete("duplicate completion");
        require(network.future().join().equals("server stopping")&&slots.active()==1);
        fresh.complete("fresh response");require(slots.active()==0);
        var overdue=slots.acquire(1);require(overdue!=null&&overdue.start());
        CompletableFuture<String> upstream=new CompletableFuture<>();
        upstream.whenComplete((answer,failure)->{overdue.networkFinished();overdue.complete(answer);});
        overdue.timeout("logical deadline");
        require(overdue.future().join().equals("logical deadline")&&!upstream.isDone()&&slots.active()==1&&slots.acquire(1)==null);
        slots.close("restart");slots.open();require(slots.active()==1&&slots.acquire(1)==null);
        upstream.complete("late actual provider completion");
        require(slots.active()==0&&overdue.future().join().equals("logical deadline"));
        var awaitingServer=slots.acquire(1);require(awaitingServer!=null&&awaitingServer.start());
        awaitingServer.networkFinished();require(slots.active()==0&&!awaitingServer.future().isDone());
        slots.close("server executor stopped before delivery");
        require(awaitingServer.future().join().equals("server executor stopped before delivery"));
        slots.close("stop");require(worker.awaitTermination(2,TimeUnit.SECONDS));
        // Every racing close/start must settle once and release all capacity.
        for(int i=0;i<100;i++){
            slots.open();var request=slots.acquire(1);require(request!=null);
            Thread starter=new Thread(()->{if(request.start())request.complete("response");});
            starter.start();slots.close("stopped");starter.join(2000);
            require(!starter.isAlive()&&request.future().isDone()&&slots.active()==0);
        }
        System.out.println("Request slot shutdown, physical capacity and race checks passed.");
    }
}
