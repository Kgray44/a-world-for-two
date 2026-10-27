package worldfortwo.packwiz;

import java.io.*;
import java.nio.file.*;
import java.time.*;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.*;

/** Real bounded original fake-child lifecycles, explicitly admitted by parent. */
public final class ProcessProbe {
    private static int checks;
    private static void check(boolean value,String reason){checks++;if(!value)throw new AssertionError(reason);}
    private static List<String> command(String mode,Path custody){
        Path java=Path.of(System.getProperty("java.home"),"bin",System.getProperty("os.name").startsWith("Windows")?"javaw.exe":"java");
        return List.of(java.toString(),"-Xmx32m","-XX:ActiveProcessorCount=1","-Djava.awt.headless=true","-cp",System.getProperty("java.class.path"),ProcessFixture.class.getName(),mode,custody.toString());
    }
    private static Properties values(Path file)throws IOException{Properties data=new Properties();try(Reader in=Files.newBufferedReader(file)){data.load(in);}return data;}
    private static void rootClosed(Path attempt)throws Exception{
        rootClosed(attempt,true);
    }
    private static void rootClosed(Path attempt,boolean requireReader)throws Exception{
        Properties state=values(attempt.resolve("process-observation.txt"));
        check(state.getProperty("root_alive").equals("false"),"Actual created root is reaped");
        long pid=Long.parseLong(state.getProperty("root_pid"));check(ProcessHandle.of(pid).map(ProcessHandle::isAlive).orElse(false)==false,"Actual root PID absent after harness returns");
        if(requireReader)check(state.getProperty("reader_alive").equals("false"),"Actual stdout capture thread closed");
    }
    private static boolean fixtureCustody(ProcessHandle child,Path custody){
        try{Properties data=values(custody);return child.pid()==Long.parseLong(data.getProperty("pid"))
            &&child.info().startInstant().map(Instant.parse(data.getProperty("start"))::equals).orElse(false);}
        catch(Exception unproved){return false;}
    }
    private static void retainedChildCleanup(Path custody)throws Exception{
        if(!Files.exists(custody))return;Properties data=values(custody);long pid=Long.parseLong(data.getProperty("pid"));Instant start=Instant.parse(data.getProperty("start"));
        Optional<ProcessHandle> current=ProcessHandle.of(pid);if(current.isEmpty()||!current.get().isAlive())return;
        ProcessHandle child=current.get();if(!child.info().startInstant().map(start::equals).orElse(false)||!fixtureCustody(child,custody))throw new IllegalStateException("Never terminate a process without exact original fixture custody");
        child.destroy();try{child.onExit().get(3,TimeUnit.SECONDS);}catch(TimeoutException timeout){child.destroyForcibly();child.onExit().get(3,TimeUnit.SECONDS);}
    }
    public static void main(String[] args)throws Exception{
        Path root=Path.of(args[0]).toAbsolutePath();Files.createDirectory(root);var mode=AttemptJournal.Mode.HEADLESS_CLI;
        for(String fixture:List.of("success","failure","timeout","overflow","descendant","unadmitted")){
            Path attempt=root.resolve(fixture),custody=root.resolve(fixture+"-owned-child.txt");
            try{
                String childMode=Set.of("descendant","unadmitted").contains(fixture)?"descendant":fixture;
                var exit=SupervisorMain.executeOwned(root,mode,command(childMode,custody),attempt,
                    fixture.equals("timeout")?Duration.ofMillis(350):Duration.ofSeconds(5),fixture.equals("descendant")?child->fixtureCustody(child,custody):child->false);
                rootClosed(attempt,!fixture.equals("unadmitted"));
                if(fixture.equals("success"))check(SupervisorMain.successfulTerminal(exit,Files.readAllBytes(attempt.resolve("process.log"))),"Actual exit0 plus complete captured terminal passes process gate");
                else if(fixture.equals("failure"))check(exit.code()==7&&!SupervisorMain.successfulTerminal(exit,Files.readAllBytes(attempt.resolve("process.log"))),"Actual native nonzero is retained, never converted to success");
                else check(exit.termination()==AttemptJournal.Termination.EXTERNALLY_STOPPED&&!SupervisorMain.successfulTerminal(exit,Files.readAllBytes(attempt.resolve("process.log"))),"Actual timeout/cap/descendant outcome fails closed");
                if(fixture.equals("overflow"))check(Files.size(attempt.resolve("process.log"))<=AttemptJournal.MAX_LOG_BYTES&&Files.exists(attempt.resolve("capture-error.txt")),"Actual over-cap output bounded and partial diagnostic retained");
                if(fixture.equals("descendant")){
                    Properties state=values(attempt.resolve("process-observation.txt"));check(state.getProperty("admitted_descendants").equals("1")&&state.getProperty("admitted_alive").equals("0")&&exit.cleanup(),"Actual identity-admitted original descendant reaped with stdout");
                }
                if(fixture.equals("unadmitted")){
                    Properties state=values(attempt.resolve("process-observation.txt"));check(state.getProperty("unadmitted_descendants").equals("1")&&!exit.cleanup(),"Unadmitted/ambiguous process outcome cannot claim cleanup or retry authority");
                    Properties child=values(custody);check(ProcessHandle.of(Long.parseLong(child.getProperty("pid"))).map(ProcessHandle::isAlive).orElse(false),"Harness preserves unadmitted child rather than killing an unrelated process");
                }
            }finally{retainedChildCleanup(custody);}
        }
        Path attempt=root.resolve("cancel"),custody=root.resolve("cancel-child.txt");AtomicReference<SupervisorMain.Exit> cancelled=new AtomicReference<>();AtomicReference<Throwable> failure=new AtomicReference<>();
        Thread caller=new Thread(()->{try{cancelled.set(SupervisorMain.executeOwned(root,mode,command("sleep",custody),attempt,Duration.ofSeconds(10),child->false));}catch(Throwable error){failure.set(error);}},"fixture-cancellation-owner");
        caller.start();long deadline=System.nanoTime()+TimeUnit.SECONDS.toNanos(4);while(!Files.exists(attempt.resolve("process.txt"))&&System.nanoTime()<deadline)Thread.sleep(10);
        caller.interrupt();caller.join(12000);check(!caller.isAlive()&&failure.get()==null&&cancelled.get()!=null,"Actual owner cancellation returns a recorded outcome");
        rootClosed(attempt);check(cancelled.get().termination()==AttemptJournal.Termination.EXTERNALLY_STOPPED&&cancelled.get().cleanup(),"Actual cancellation reaps only owned root and stdout without granting success");
        long readerDeadline=System.nanoTime()+TimeUnit.SECONDS.toNanos(3);while(Thread.getAllStackTraces().keySet().stream().anyMatch(t->t.isAlive()&&t.getName().startsWith("awft-installer-bounded-output-"))&&System.nanoTime()<readerDeadline)Thread.sleep(10);
        check(Thread.getAllStackTraces().keySet().stream().noneMatch(t->t.isAlive()&&t.getName().startsWith("awft-installer-bounded-output-")),"All fixture stdout readers reaped after explicit owned-only cleanup");
        System.out.println("PROCESS_CHECKS="+checks+" PASS; original fake children only; no Packwiz Main/network/GUI/game/Prism");
    }
}
