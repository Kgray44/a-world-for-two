package worldfortwo.tavern;

import java.io.IOException;
import java.io.InterruptedIOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.Locale;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicBoolean;

/** One bounded latest snapshot, no history; disk work never blocks server ticks. */
final class StatusWriter implements AutoCloseable {
    final ExecutorService io=Executors.newSingleThreadExecutor(r->{Thread t=new Thread(r,"awft-tavern-status");t.setDaemon(true);return t;});
    final AtomicBoolean busy=new AtomicBoolean();
    volatile String error="";
    long guardedAt;
    void write(Path destination,String json){
        byte[] bytes=json.getBytes(StandardCharsets.UTF_8);
        if(bytes.length>128*1024||!busy.compareAndSet(false,true))return;
        io.submit(()->{try{
            Path dir=destination.toAbsolutePath().normalize().getParent();
            if(Files.isSymbolicLink(dir)||Files.isSymbolicLink(destination))throw new IllegalStateException("Refuse linked status destination");
            if(System.getProperty("os.name").toLowerCase(Locale.ROOT).contains("windows")){
                for(String drive:new String[]{"C:\\","D:\\"})if(Files.getFileStore(Path.of(drive)).getUsableSpace()-1048576<=32212254720L)throw new IllegalStateException("Storage reserve reached");
                if(guardedAt==0||System.nanoTime()-guardedAt>TimeUnit.MINUTES.toNanos(5)){
                    String root=destination.toAbsolutePath().getRoot().toString().toUpperCase(Locale.ROOT);
                    if(!root.equals("C:\\")&&!root.equals("D:\\"))throw new IllegalStateException("Unknown status allocation drive");
                    Process guard=new ProcessBuilder("powershell.exe","-NoProfile","-NonInteractive","-WindowStyle","Hidden","-ExecutionPolicy","Bypass","-File","C:\\Users\\kkids\\AppData\\Local\\AeroStorageWatch\\ReserveGuard.ps1","-EstimatedCBytes",root.equals("C:\\")?"1048576":"0","-EstimatedDBytes",root.equals("D:\\")?"1048576":"0").redirectErrorStream(true).redirectOutput(ProcessBuilder.Redirect.DISCARD).start();
                    if(!guard.waitFor(15,TimeUnit.SECONDS)){guard.destroyForcibly();throw new IllegalStateException("Storage guard timeout");}
                    if(guard.exitValue()!=0)throw new IllegalStateException("Storage guard refused status writer");
                    guardedAt=System.nanoTime();
                }
            }
            Files.createDirectories(dir);Path tmp=dir.resolve("status.json.tmp");
            if(Files.isSymbolicLink(tmp))throw new IllegalStateException("Refuse linked status temporary file");
            Files.write(tmp,bytes,StandardOpenOption.CREATE,StandardOpenOption.TRUNCATE_EXISTING);
            publish(tmp,destination);error="";
        }catch(Exception e){error=e.toString();}finally{busy.set(false);}});
    }
    /** Windows readers can briefly deny replacement while omitting delete sharing. */
    static void publish(Path tmp,Path destination)throws IOException{
        for(int attempt=0;;attempt++){
            try{
                Files.move(tmp,destination,StandardCopyOption.ATOMIC_MOVE,StandardCopyOption.REPLACE_EXISTING);
                return;
            }catch(AccessDeniedException denied){
                if(attempt>=5)throw denied;
                try{TimeUnit.MILLISECONDS.sleep(25L<<attempt);}
                catch(InterruptedException interrupted){
                    Thread.currentThread().interrupt();
                    throw new InterruptedIOException("Interrupted while retrying atomic status publication");
                }
            }
        }
    }
    @Override public void close(){io.shutdownNow();}
}
