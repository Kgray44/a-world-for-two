package worldfortwo.bridge;

import java.util.concurrent.CountDownLatch;
import java.util.concurrent.atomic.AtomicInteger;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;

/** Synthetic admission/failure regression fixture. Never initializes a mod or Minecraft. */
public final class MoonlightBudgetProbe {
    private static void check(boolean okay){if(!okay)throw new AssertionError();}
    private static void refuses(Runnable action){try{action.run();throw new AssertionError("Unexpected admission");}catch(IllegalStateException expected){}}
    private static void gateBlocked(Path path)throws Exception {
        try{MoonlightPreparationGate.requireClear(path);throw new AssertionError("Partial output admitted on next launch");}catch(IOException expected){}
    }
    public static void main(String[] args)throws Exception {
        long limit=MoonlightPreparationBudget.BYTE_LIMIT;
        var data=new MoonlightPreparationBudget(0);
        data.write("minecraft:tags/worldgen/biome/one.json",17,0);
        data.write("minecraft:tags/worldgen/biome/one.json",19,0);
        check(data.written()==36); // Replacing the same key does not reset the cost.
        data.fail("native task failed after producing partial resources");
        refuses(()->data.check(0));refuses(()->data.write("minecraft:two.json",1,0));
        check(data.written()==36);

        var full=new MoonlightPreparationBudget(0);full.produce((int)limit,0);
        refuses(()->full.produce(1,0));check(full.produced()==limit);
        var time=new MoonlightPreparationBudget(0);
        time.check(MoonlightPreparationBudget.DEADLINE);
        refuses(()->time.check(MoonlightPreparationBudget.DEADLINE+1));
        refuses(()->time.check(0)); // Failure stays latched, even with an earlier time.
        for(String id:new String[]{"minecraft:../outside.json","minecraft:dir/../outside.json","minecraft:/absolute","minecraft:dir//bad","minecraft:a\\b","missing_namespace"}){
            var bad=new MoonlightPreparationBudget(0);refuses(()->bad.write(id,1,0));
        }
        var depth=new MoonlightPreparationBudget(0);refuses(()->depth.write("minecraft:"+"dir/".repeat(32)+"file",1,0));
        var dirs=new MoonlightPreparationBudget(0);
        for(int i=0;i<1022;i++)dirs.write("minecraft:d"+i+"/f.json",1,0);
        refuses(()->dirs.write("minecraft:one_more/f.json",1,0));
        var count=new MoonlightPreparationBudget(0);
        for(int i=0;i<4096;i++)count.write("minecraft:f"+i+".json",1,0);
        refuses(()->count.write("minecraft:one_more.json",1,0));

        var concurrent=new MoonlightPreparationBudget(System.nanoTime());
        var begin=new CountDownLatch(1);var accepted=new AtomicInteger();var rejected=new AtomicInteger();
        Thread[] workers=new Thread[8];
        for(int i=0;i<workers.length;i++)workers[i]=new Thread(()->{
            try{begin.await();for(int j=0;j<8;j++){try{concurrent.produce(1024*1024,System.nanoTime());accepted.incrementAndGet();}
                catch(IllegalStateException expected){rejected.incrementAndGet();}}}
            catch(InterruptedException failure){throw new AssertionError(failure);}
        });
        for(Thread worker:workers)worker.start();begin.countDown();for(Thread worker:workers)worker.join();
        check(accepted.get()==32&&rejected.get()==32&&concurrent.produced()==limit);
        refuses(()->concurrent.check(System.nanoTime()));
        Path gate=Path.of("fixture-gate");Files.createDirectory(gate);
        MoonlightPreparationGate.requireClear(gate);
        var owned=MoonlightPreparationGate.create(gate,new byte[]{1,2,3});
        gateBlocked(gate); // Simulates a failed operation and a later process's admission.
        try{MoonlightPreparationGate.create(gate,new byte[]{9});throw new AssertionError("Existing gate replaced");}catch(IOException expected){}
        owned.complete();MoonlightPreparationGate.requireClear(gate);
        owned=MoonlightPreparationGate.create(gate,new byte[]{1,2,3});
        Files.write(gate.resolve("moonlight-native-preparation.pending"),new byte[]{4,5,6});
        try{owned.complete();throw new AssertionError("Changed gate removed");}catch(IOException expected){}
        gateBlocked(gate);
        check(Files.readAllBytes(gate.resolve("moonlight-native-preparation.pending"))[0]==4);
        System.out.println("PASS: partial failures, replacement costs, byte/node/depth limits, deadlines, concurrent admission, persistent failure gate");
    }
}
