package worldfortwo.bridge;

import java.util.Map;

public final class TickWindowProbe {
    @SuppressWarnings("unchecked")
    private static Map<String,Object> part(Map<String,Object> sample,String key) {
        return (Map<String,Object>)sample.get(key);
    }
    private static void require(boolean condition) { if(!condition)throw new AssertionError("Tick-window regression"); }
    public static void main(String[] args) {
        var window=new TickWindow();
        for(int i=0;i<100;i++){window.started(1L+i*50_000_000L);window.finished(i==99?600_000_000L:1_000_000L);}
        var sample=window.snapshotAndReset();var work=part(sample,"work_ms");
        require(work.get("max").equals(600.0)&&work.get("p99").equals(1.0));
        require(sample.get("work_over_50ms").equals(1L)&&sample.get("work_over_250ms").equals(1L));
        window.started(1L+99*50_000_000L+700_000_000L);window.finished(2_000_000L);
        sample=window.snapshotAndReset();
        require(part(sample,"start_gap_ms").get("max").equals(700.0));
        require(part(sample,"work_ms").get("max").equals(2.0));
        window.resetLifecycle();window.started(8_000_000_000L);window.finished(0);
        require(part(window.snapshotAndReset(),"start_gap_ms").get("observations").equals(0L));
        for(int i=0;i<4097;i++)window.finished(1_000_000L);
        sample=window.snapshotAndReset();work=part(sample,"work_ms");
        require(work.get("observations").equals(4097L)&&work.get("complete_distribution").equals(false));
        require(!work.containsKey("p99")&&work.get("max").equals(1.0));
        require(part(window.snapshotAndReset(),"work_ms").get("mean")==null);
        try {window.finished(-1);throw new AssertionError("Negative work accepted");}catch(IllegalArgumentException expected){}
        System.out.println("PASS synthetic tick windows: hidden spike, boundary stall, lifecycle reset, overflow, empty and negative intervals. No Minecraft benchmark.");
    }
}
