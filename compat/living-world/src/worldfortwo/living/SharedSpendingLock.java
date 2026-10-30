package worldfortwo.living;

import java.nio.channels.FileChannel;
import java.nio.channels.FileLock;
import java.nio.file.*;

/** Byte-zero OS lock shared with the dashboard's msvcrt.LK_NBLCK lock. */
public final class SharedSpendingLock implements AutoCloseable {
    private final FileChannel channel;
    private final FileLock lock;
    private SharedSpendingLock(FileChannel channel,FileLock lock){this.channel=channel;this.lock=lock;}
    public static SharedSpendingLock acquire(Path path)throws Exception{
        FileChannel channel=FileChannel.open(path,StandardOpenOption.CREATE,StandardOpenOption.READ,StandardOpenOption.WRITE);
        try{FileLock lock=channel.tryLock(0,1,false);if(lock==null)throw new IllegalStateException("Shared AI allowance busy");return new SharedSpendingLock(channel,lock);}
        catch(Exception error){channel.close();throw error;}
    }
    public void close()throws Exception{try{lock.release();}finally{channel.close();}}
}
