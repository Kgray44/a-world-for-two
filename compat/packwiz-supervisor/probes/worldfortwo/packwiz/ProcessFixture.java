package worldfortwo.packwiz;

import java.nio.file.*;
import java.util.*;

/** Original finite fake child ONLY. Not bundled, no network/installer/game/UI. */
public final class ProcessFixture {
    public static void main(String[] args)throws Exception{
        String mode=args[0];Path custody=Path.of(args[1]);
        if(mode.equals("leaf"))try{Files.writeString(custody,"pid="+ProcessHandle.current().pid()+"\nstart="+ProcessHandle.current().info().startInstant().orElseThrow()+"\n",StandardOpenOption.CREATE_NEW);}catch(FileAlreadyExistsException recordedByParent){}
        if(mode.equals("success")){System.out.println("Finished successfully!");return;}
        if(mode.equals("failure")){System.out.println("Finished successfully!");System.exit(7);}
        if(mode.equals("overflow")){
            byte[] bytes=new byte[16384];Arrays.fill(bytes,(byte)'x');for(int n=0;n<270;n++){System.out.write(bytes);System.out.flush();}
        }
        if(mode.equals("descendant")){
            Path java=Path.of(System.getProperty("java.home"),"bin",System.getProperty("os.name").startsWith("Windows")?"javaw.exe":"java");
            Process child=new ProcessBuilder(java.toString(),"-Xmx32m","-XX:ActiveProcessorCount=1","-Djava.awt.headless=true","-cp",System.getProperty("java.class.path"),ProcessFixture.class.getName(),"leaf",custody.toString()).inheritIO().start();
            try{Files.writeString(custody,"pid="+child.pid()+"\nstart="+child.info().startInstant().orElseThrow()+"\n",StandardOpenOption.CREATE_NEW);}catch(FileAlreadyExistsException recordedByChild){}
        }
        System.out.println("ORIGINAL_FAKE_CHILD_READY");System.out.flush();Thread.sleep(15000);
    }
}
