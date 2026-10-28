package worldfortwo.performance;

import java.io.IOException;
import java.nio.file.*;
import java.nio.file.attribute.BasicFileAttributes;
import java.time.Instant;
import java.util.*;
import jdk.jfr.consumer.*;

/** Bounded retained-file reader. No attach API, recording control, game or network. */
public final class JfrSummary {
    private static final long LIMIT=64L*1024*1024,DEADLINE=30_000_000_000L;
    private static final class Stats {
        final double[] samples=new double[4096];int retained;long count;double sum,max;
        void add(double ms){
            if(!Double.isFinite(ms)||ms<0)throw new IllegalArgumentException("Invalid native duration");
            count++;sum+=ms;max=Math.max(max,ms);if(retained<samples.length)samples[retained++]=ms;
        }
        Map<String,Object> result(){
            var out=new LinkedHashMap<String,Object>();out.put("observations",count);out.put("complete_distribution",retained==count);
            out.put("mean",count==0?null:sum/count);out.put("max",count==0?null:max);out.put("sum",count==0?null:sum);
            if(count>0&&retained==count){double[] sorted=Arrays.copyOf(samples,retained);Arrays.sort(sorted);
                out.put("p50",sorted[(int)Math.ceil(count*.5)-1]);out.put("p95",sorted[(int)Math.ceil(count*.95)-1]);out.put("p99",sorted[(int)Math.ceil(count*.99)-1]);}
            return out;
        }
    }
    private static String text(RecordedEvent event,String field){
        String value=event.getString(field);if(value==null||value.length()>512)throw new IllegalArgumentException("Bounded native event label required");return value;
    }
    private static double duration(RecordedEvent event){return event.getDuration().toNanos()/1_000_000.0;}

    public static Map<String,Object> read(Path path,long expectedPid,long expectedStart)throws IOException {
        var before=Files.readAttributes(path,BasicFileAttributes.class,LinkOption.NOFOLLOW_LINKS);
        if(!before.isRegularFile()||before.isSymbolicLink()||before.isOther()||before.size()>LIMIT||before.size()<8||expectedPid<=0||expectedStart<=0)
            throw new IOException("Bounded ordinary recording and exact expected JVM identity required");
        var gc=new Stats();var pauses=new Stats();var regionReads=new Stats();
        var chunks=new TreeMap<String,Stats>();long reads=0,readBytes=0,events=0,jvmEvents=0;Instant first=null,last=null;
        Set<String> types=new TreeSet<>();long started=System.nanoTime();
        try(RecordingFile input=new RecordingFile(path)){
            for(var type:input.readEventTypes())if(Set.of("minecraft.ChunkGeneration","minecraft.ChunkRegionRead","jdk.GarbageCollection","jdk.GCPhasePause","jdk.FileRead","jdk.JVMInformation").contains(type.getName()))types.add(type.getName());
            while(input.hasMoreEvents()){
                if(++events>250_000||System.nanoTime()-started>DEADLINE)throw new IOException("Retained recording event/time bound exceeded");
                RecordedEvent event=input.readEvent();String type=event.getEventType().getName();
                Instant begin=event.getStartTime(),end=event.getEndTime();
                if(first==null||begin.isBefore(first))first=begin;if(last==null||end.isAfter(last))last=end;
                switch(type){
                    case "jdk.JVMInformation" -> {
                        Object raw=event.getValue("pid");long pid=raw instanceof Number n?n.longValue():Long.parseLong((String)raw);
                        long birth=event.getInstant("jvmStartTime").toEpochMilli();
                        if(pid!=expectedPid||birth<=0||Math.abs(birth-expectedStart)>2000)throw new IOException("Recording belongs to another JVM generation");
                        jvmEvents++;
                    }
                    case "minecraft.ChunkGeneration" -> {
                        // Names are the pinned Minecraft1.21.1 JFR Fields constants, not Java member names.
                        String key=text(event,"level")+" / "+text(event,"status");
                        if(!chunks.containsKey(key)&&chunks.size()>=128)throw new IOException("Native dimension/status group bound exceeded");
                        chunks.computeIfAbsent(key,k->new Stats()).add(duration(event));
                    }
                    case "jdk.GarbageCollection" -> gc.add(duration(event));
                    case "jdk.GCPhasePause" -> pauses.add(duration(event));
                    case "minecraft.ChunkRegionRead" -> {
                        long bytes=event.getInt("bytes");if(bytes<0)throw new IOException("Negative native read byte count");reads++;readBytes=Math.addExact(readBytes,bytes);
                        // Native1.21.1 commits this event immediately; it has no timed I/O scope.
                    }
                    case "jdk.FileRead" -> {
                        String file=event.getString("path");
                        if(file!=null&&file.length()<=32768&&(file.endsWith(".mca")||file.endsWith(".mcc")))regionReads.add(duration(event));
                        // Paths/coordinates/arguments/player names never appear in output.
                    }
                    default -> {}
                }
            }
        }
        var after=Files.readAttributes(path,BasicFileAttributes.class,LinkOption.NOFOLLOW_LINKS);
        if(!after.isRegularFile()||after.isSymbolicLink()||after.isOther()||before.size()!=after.size()
                ||!before.lastModifiedTime().equals(after.lastModifiedTime())||!Objects.equals(before.fileKey(),after.fileKey()))throw new IOException("Recording changed during read");
        if(jvmEvents==0)throw new IOException("Native JVMInformation provenance absent; never infer process ownership");
        var groups=new TreeMap<String,Object>();chunks.forEach((key,value)->groups.put(key,value.result()));
        var out=new LinkedHashMap<String,Object>();out.put("format","awft-retained-jfr-summary:1");out.put("complete_file_read",true);
        out.put("native_gameplay_qualified",false);out.put("strict_parity_proved",false);out.put("embedded_jvm_identity_matched",true);
        out.put("pid",expectedPid);out.put("process_started_epoch_ms",expectedStart);out.put("recording_bytes",before.size());out.put("events_read",events);
        out.put("first_observed_event",first==null?null:first.toString());out.put("last_observed_event",last==null?null:last.toString());out.put("event_types_present",types);
        out.put("chunk_generation_status_duration_ms",groups);out.put("gc_event_duration_ms",gc.result());out.put("root_gc_phase_pause_duration_ms",pauses.result());
        out.put("native_chunk_region_read_events",reads);out.put("native_chunk_region_read_bytes",readBytes);out.put("region_file_read_operation_duration_ms",regionReads.result());
        out.put("limits","Only observed enabled events. Missing events do not prove zero activity. Chunk statuses overlap and must not be summed into FULL-chunk load latency. Native ChunkRegionRead is instantaneous; file-read durations exclude decompression, queues, chunk publication and packet arrival. GC event duration may include concurrent work; only root GCPhasePause measures recorded pause scopes. No paths, coordinates or JVM arguments exported.");
        return out;
    }
    public static String json(Object value){
        if(value==null)return "null";
        if(value instanceof Boolean||value instanceof Number)return value.toString();
        if(value instanceof Map<?,?> map){var join=new StringJoiner(",","{","}");map.forEach((k,v)->join.add(json(k.toString())+":"+json(v)));return join.toString();}
        if(value instanceof Collection<?> list){var join=new StringJoiner(",","[","]");for(var item:list)join.add(json(item));return join.toString();}
        String s=value.toString();var out=new StringBuilder("\"");for(char c:s.toCharArray())switch(c){case '"'->out.append("\\\"");case '\\'->out.append("\\\\");case '\n'->out.append("\\n");case '\r'->out.append("\\r");case '\t'->out.append("\\t");default->{if(c<32)out.append(String.format("\\u%04x",(int)c));else out.append(c);}}return out.append('"').toString();
    }
    public static void main(String[] args)throws Exception {
        if(args.length!=3)throw new IllegalArgumentException("recording expected-pid expected-start-epoch-ms");
        System.out.println(json(read(Path.of(args[0]),Long.parseLong(args[1]),Long.parseLong(args[2]))));
    }
}
