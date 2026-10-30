package worldfortwo.qa;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Arrays;

/** Exercises the actual bounded reader only. No Minecraft, images, or Native calls. */
public final class DrinkCaptureFilesProbe {
    private static int checks,linkChecks;
    private interface Read { void run() throws Exception; }
    private static void check(boolean ok,String message) {
        checks++;if(!ok)throw new AssertionError(message);
    }
    private static void rejected(Read read,String message) throws Exception {
        boolean failed=false;
        try{read.run();}catch(Exception expected){failed=true;}
        check(failed,message);
    }
    private static Path bytes(Path root,String name,int count) throws Exception {
        byte[] value=new byte[count];Arrays.fill(value,(byte)'a');
        return Files.write(root.resolve(name),value);
    }
    public static void main(String[] args) throws Exception {
        Path root=Files.createTempDirectory("awft-drink-file-bound-");
        try {
            check(DrinkCaptureFiles.OWNER_MAX_BYTES==65536,"owner bound is64KiB");
            check(DrinkCaptureFiles.SMALL_MAX_BYTES==4096,"auth/request bound stays4KiB");
            String owner="{\"format\":\"awft-owned-client:1\",\"padding\":\""+"a".repeat(38407)+"\"}";
            Path actualSize=Files.writeString(root.resolve("owner38452.json"),owner,StandardCharsets.UTF_8);
            // Build an exact38452-byte synthetic marker; no real authorization data is read.
            if(Files.size(actualSize)!=38452) {
                int delta=(int)(38452-Files.size(actualSize));
                owner=owner.replace("a".repeat(38407),"a".repeat(38407+delta));
                Files.writeString(actualSize,owner,StandardCharsets.UTF_8);
            }
            check(Files.size(actualSize)==38452,"reproduce real marker byte length");
            check(DrinkCaptureFiles.readOwner(actualSize).equals(owner),"real-sized owner marker accepted intact");
            rejected(()->DrinkCaptureFiles.readSmall(actualSize),"same oversized auth/request still rejected");
            Path exactOwner=bytes(root,"owner-exact",65536),largeOwner=bytes(root,"owner-large",65537);
            check(DrinkCaptureFiles.readOwner(exactOwner).length()==65536,"owner boundary inclusive");
            rejected(()->DrinkCaptureFiles.readOwner(largeOwner),"owner one byte over rejected");
            Path exactSmall=bytes(root,"small-exact",4096),largeSmall=bytes(root,"small-large",4097);
            check(DrinkCaptureFiles.readSmall(exactSmall).length()==4096,"small boundary inclusive");
            rejected(()->DrinkCaptureFiles.readSmall(largeSmall),"auth/request one byte over rejected");
            check(DrinkCaptureFiles.readSmall(bytes(root,"auth285",285)).length()==285,"current auth-sized input accepted");
            check(DrinkCaptureFiles.readSmall(bytes(root,"request340",340)).length()==340,"current request-sized input accepted");
            Path unicode=Files.writeString(root.resolve("unicode"),"é".repeat(2049),StandardCharsets.UTF_8);
            rejected(()->DrinkCaptureFiles.readSmall(unicode),"small bound counts bytes, not characters");
            Path malformed=Files.write(root.resolve("malformed"),new byte[]{(byte)0xc3,(byte)0x28});
            rejected(()->DrinkCaptureFiles.readOwner(malformed),"owner malformed UTF8 rejected");
            rejected(()->DrinkCaptureFiles.readSmall(malformed),"auth/request malformed UTF8 rejected");
            rejected(()->DrinkCaptureFiles.readOwner(root.resolve("missing")),"missing owner rejected");
            rejected(()->DrinkCaptureFiles.readSmall(root),"directory rejected");
            Path link=root.resolve("linked-owner");
            try {
                Files.createSymbolicLink(link,actualSize);
                rejected(()->DrinkCaptureFiles.readOwner(link),"linked owner rejected");
                rejected(()->DrinkCaptureFiles.readSmall(link),"linked auth/request rejected");
                linkChecks=2;
            }catch(UnsupportedOperationException|java.nio.file.FileSystemException unsupported) {
                System.out.println("LINK_FIXTURES_UNAVAILABLE="+unsupported.getClass().getSimpleName());
            }
            System.out.println("DRINK_FILE_BOUND_CHECKS="+checks+" PASS; link_checks="+linkChecks+"; no native/game/image actions");
        } finally {
            try(var paths=Files.list(root)) {
                for(Path path:paths.toList())Files.delete(path);
            }
            Files.delete(root);
        }
    }
}
