import java.nio.file.Path;
import worldfortwo.living.SharedSpendingLock;

/** Exercises the actual source lock against Python's Windows byte lock, no game. */
public final class SpendingLockSelfTest {
    public static void main(String[] args)throws Exception{
        try(var lock=SharedSpendingLock.acquire(Path.of(args[0]))){
            System.out.println(args[1].equals("hold")?"held":"acquired");System.out.flush();
            if(args[1].equals("hold"))System.in.read();
        }catch(IllegalStateException busy){System.out.println("busy");}
    }
}
