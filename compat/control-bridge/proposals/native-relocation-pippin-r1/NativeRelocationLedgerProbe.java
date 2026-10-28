package worldfortwo.bridge;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.Arrays;

/** Actual production durable primitive; owned files only, no Minecraft bootstrap. */
public final class NativeRelocationLedgerProbe {
    private static void require(boolean ok,String reason){if(!ok)throw new AssertionError(reason);}
    public static void main(String[] args)throws Exception{
        if(args.length!=1)throw new IllegalArgumentException("One owned fixture directory required");
        Path root=Path.of(args[0]).toAbsolutePath().normalize();
        if(!root.startsWith(Path.of("D:/A World for Two/staging").toAbsolutePath().normalize())||!root.getFileName().toString().startsWith("native-relocation-ledger-fixture-"))throw new IllegalArgumentException("No world/user files in this fixture");
        Files.createDirectory(root);byte[] first="{\"phase\":\"intent\"}\n".getBytes(StandardCharsets.UTF_8);
        Path intent=root.resolve("intent.json");NativeRelocationSupport.Ledger.create(intent,first);
        require(Arrays.equals(Files.readAllBytes(intent),first),"Durable bytes differ");
        boolean executed=false,refused=false;
        try{NativeRelocationSupport.Ledger.create(intent,"different".getBytes(StandardCharsets.UTF_8));executed=true;}
        catch(FileAlreadyExistsException expected){refused=true;}
        require(refused&&!executed&&Arrays.equals(Files.readAllBytes(intent),first),"An existing once-only intent was replayed/overwritten");
        Path partial=root.resolve("interrupted.intent");NativeRelocationSupport.Ledger.create(partial,new byte[]{123});
        refused=false;try{NativeRelocationSupport.Ledger.create(partial,first);}catch(FileAlreadyExistsException expected){refused=true;}
        require(refused&&Files.size(partial)==1,"An interrupted malformed intent was silently repaired");
        Path tooBig=root.resolve("oversize");refused=false;
        try{NativeRelocationSupport.Ledger.create(tooBig,new byte[1048577]);}catch(IllegalStateException expected){refused=true;}
        require(refused&&!Files.exists(tooBig),"Finite byte gate was bypassed");
        Path empty=root.resolve("empty");refused=false;
        try{NativeRelocationSupport.Ledger.create(empty,new byte[0]);}catch(IllegalStateException expected){refused=true;}
        require(refused&&!Files.exists(empty),"An empty intent was accepted");
        System.out.println("PASS actual CREATE_NEW+force durable bytes; existing/partial intents never replayed; finite oversized/empty refusals; no Minecraft operation");
    }
}
