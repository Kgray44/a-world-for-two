package worldfortwo.bridge;

import java.util.Arrays;
import java.util.LinkedHashMap;
import java.util.Map;

/** Complete bounded tick-event window, with gaps measured separately from work.
 * Does not infer native tick spikes from a five-second average. No game API.
 */
public final class TickWindow {
    private final long[] work = new long[4096], gaps = new long[4096];
    private int count, gapCount;
    private long seen, gapSeen, sum, gapSum, maximum, gapMaximum;
    private long over50, over100, over250, gapOver100, lastStart;

    public void started(long now) {
        if (lastStart != 0 && now >= lastStart) {
            long value = now - lastStart;
            gapSeen++; gapSum += value; gapMaximum = Math.max(gapMaximum, value);
            if (value > 100_000_000L) gapOver100++;
            if (gapCount < gaps.length) gaps[gapCount++] = value;
        }
        lastStart = now;
    }

    public void finished(long nanos) {
        if (nanos < 0) throw new IllegalArgumentException("Negative tick work interval");
        seen++; sum += nanos; maximum = Math.max(maximum, nanos);
        if (nanos > 50_000_000L) over50++;
        if (nanos > 100_000_000L) over100++;
        if (nanos > 250_000_000L) over250++;
        if (count < work.length) work[count++] = nanos;
    }

    public Map<String,Object> snapshotAndReset() {
        var result = new LinkedHashMap<String,Object>();
        result.put("format", "awft-tick-window:1");
        result.put("work_ms", summary(work,count,seen,sum,maximum));
        result.put("start_gap_ms", summary(gaps,gapCount,gapSeen,gapSum,gapMaximum));
        result.put("work_over_50ms", over50); result.put("work_over_100ms", over100);
        result.put("work_over_250ms", over250); result.put("start_gaps_over_100ms", gapOver100);
        result.put("scope", "Native Pre-to-Post event work and consecutive Pre gaps. Gaps include pacing, GC and scheduling; no cause is inferred.");
        count=gapCount=0; seen=gapSeen=sum=gapSum=maximum=gapMaximum=0;
        over50=over100=over250=gapOver100=0;
        // Keep lastStart: the next window must include a stall spanning export.
        return result;
    }

    public void resetLifecycle() { snapshotAndReset(); lastStart=0; }

    private static Map<String,Object> summary(long[] values,int count,long seen,long sum,long maximum) {
        var out = new LinkedHashMap<String,Object>();
        out.put("observations",seen); out.put("retained_samples",count);
        out.put("complete_distribution",seen==count);
        out.put("mean",seen==0?null:sum/1_000_000.0/seen);
        out.put("max",seen==0?null:maximum/1_000_000.0);
        // Overflow retains the exact count/sum/max/threshold counts. A truncated
        // distribution must never be advertised as a full-window percentile.
        if (seen>0 && seen==count) {
            long[] sorted=Arrays.copyOf(values,count); Arrays.sort(sorted);
            out.put("p50",percentile(sorted,.50)); out.put("p95",percentile(sorted,.95));
            out.put("p99",percentile(sorted,.99));
        }
        return out;
    }

    private static double percentile(long[] sorted,double fraction) {
        return sorted[Math.max(0,(int)Math.ceil(sorted.length*fraction)-1)]/1_000_000.0;
    }
}
