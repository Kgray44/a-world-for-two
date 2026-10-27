package worldfortwo.bridge;

import com.google.gson.Gson;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.security.MessageDigest;
import java.time.Instant;
import java.util.*;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.function.*;
import net.minecraft.core.RegistryAccess;
import net.minecraft.resources.ResourceKey;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.chunk.ChunkGenerator;

/** One owned read-only encoder worker; completion is rechecked on the game owner
 * thread. Missing custody receipts or UNKNOWN are never native parity acceptance.
 */
public final class NativeWorldgenWitnessTask {
    private static final AtomicBoolean BUSY=new AtomicBoolean();
    private static final Gson JSON=new Gson();
    private NativeWorldgenWitnessTask(){}
    public static void start(RegistryAccess actual,Map<ResourceKey<Level>,ChunkGenerator> generators,
            Path directory,String id,String side,Consumer<Runnable> ownerThread,BooleanSupplier stillCurrent){
        if(!id.matches("[a-z0-9][a-z0-9-]{0,63}")||generators.isEmpty()||generators.size()>32)
            throw new IllegalArgumentException("Bounded actual generator capture required");
        Map<ResourceKey<Level>,ChunkGenerator> captured=Map.copyOf(generators);
        Path custody=directory.resolve(id+".lithostitched.custody.json");
        if(Files.exists(custody)||!BUSY.compareAndSet(false,true))throw new IllegalStateException("An effective-state export or retained custody receipt already exists");
        Thread worker=new Thread(()->{
            Path status=null;String error=null;
            try{status=NativeLithostitchedWitness.write(actual,captured,directory,id,side);}
            catch(Throwable failure){error=failure.getClass().getName();}
            Path completed=status;String failureClass=error;
            try{ownerThread.accept(()->{
                try{
                    Map<String,Object> result=new LinkedHashMap<>();result.put("at",Instant.now().toString());
                    result.put("format","awft-native-effective-custody:1");result.put("side",side);
                    result.put("owner_thread_rechecked",true);result.put("captured_inputs_still_current",stillCurrent.getAsBoolean());
                    result.put("strict_parity_proved",false);result.put("mutable_graphs_proven_immutable",false);
                    if(failureClass!=null)result.put("worker_failure_class",failureClass);
                    if(completed!=null){if(Files.isSymbolicLink(completed)||Files.size(completed)>65536)throw new IllegalStateException("Finite regular status receipt required");
                        byte[] raw;try(var input=Files.newInputStream(completed)){raw=input.readNBytes(65537);}if(raw.length>65536)throw new IllegalStateException("Status grew beyond its finite allocation");
                        result.put("status_file",completed.getFileName().toString());result.put("status_sha256",HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(raw)));}
                    else result.put("status","failed before a native effective-state status was published; preserve all partial files");
                    Files.writeString(custody,JSON.toJson(result),StandardCharsets.UTF_8,StandardOpenOption.CREATE_NEW);
                }catch(Exception|LinkageError failure){System.err.println("AWFT effective-state custody receipt failed; no parity acceptance: "+failure.getClass().getName());}
                finally{BUSY.set(false);}
            });}catch(RuntimeException failure){BUSY.set(false);System.err.println("AWFT effective-state owner callback unavailable; no current custody receipt or parity acceptance");}
        },"AWFT-effective-worldgen-"+id);
        worker.setDaemon(true);
        try{worker.start();}catch(RuntimeException|Error failure){BUSY.set(false);throw failure;}
    }
}
