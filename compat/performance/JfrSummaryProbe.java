package worldfortwo.performance;

import java.nio.file.*;
import java.lang.management.ManagementFactory;
import java.util.Map;
import jdk.jfr.*;

/** Synthetic JDK recording only. No Minecraft classes, modloader, attach or game. */
public final class JfrSummaryProbe {
    @Name("minecraft.ChunkGeneration") @StackTrace(false)
    static class Chunk extends Event {String status,level;int chunkPosX=123456,chunkPosZ=987654;}
    @Name("minecraft.ChunkRegionRead") @StackTrace(false)
    static class Read extends Event {int bytes;}
    private static void check(boolean value){if(!value)throw new AssertionError();}
    public static void main(String[] args)throws Exception {
        Path path=Path.of("synthetic.jfr");long pid=ProcessHandle.current().pid(),birth=ManagementFactory.getRuntimeMXBean().getStartTime();
        try(Recording recording=new Recording()){
            recording.enable("jdk.JVMInformation");recording.enable(Chunk.class);recording.enable(Read.class);recording.setMaxSize(8L*1024*1024);recording.start();
            for(int i=0;i<4100;i++){var event=new Chunk();event.level="minecraft:overworld";event.status="minecraft:surface";event.begin();event.end();event.commit();}
            var read=new Read();read.bytes=99;read.commit();recording.stop();recording.dump(path);
        }
        Map<String,Object> data=JfrSummary.read(path,pid,birth);
        check(Boolean.FALSE.equals(data.get("native_gameplay_qualified")));
        check(Boolean.FALSE.equals(data.get("strict_parity_proved")));
        check(data.get("native_chunk_region_read_events").equals(1L));check(data.get("native_chunk_region_read_bytes").equals(99L));
        var groups=(Map<?,?>)data.get("chunk_generation_status_duration_ms");
        var stats=(Map<?,?>)groups.get("minecraft:overworld / minecraft:surface");
        check(stats.get("observations").equals(4100L));check(Boolean.FALSE.equals(stats.get("complete_distribution")));check(!stats.containsKey("p99"));
        check(((Map<?,?>)data.get("gc_event_duration_ms")).get("max")==null);
        String json=JfrSummary.json(data);check(!json.contains("123456")&&!json.contains("987654")&&!json.contains("javaArguments"));
        try{JfrSummary.read(path,pid+1,birth);throw new AssertionError("Borrowed PID admitted");}catch(java.io.IOException expected){}
        try{JfrSummary.read(path,pid,birth+60000);throw new AssertionError("Borrowed JVM generation admitted");}catch(java.io.IOException expected){}
        Path bad=Path.of("not-a-recording.jfr");Files.writeString(bad,"bad recording");
        try{JfrSummary.read(bad,pid,birth);throw new AssertionError("Invalid JFR admitted");}catch(java.io.IOException expected){}
        Path noIdentity=Path.of("no-identity.jfr");
        try(Recording recording=new Recording()){
            recording.enable(Chunk.class);recording.start();var event=new Chunk();event.level="minecraft:overworld";event.status="minecraft:surface";event.commit();recording.stop();recording.dump(noIdentity);
        }
        try{JfrSummary.read(noIdentity,pid,birth);throw new AssertionError("Absent JVMInformation admitted");}catch(java.io.IOException expected){}
        System.out.println("PASS: synthetic status/read events, exact embedded JVM identity, missing metrics, overflow, no private coordinates");
    }
}
