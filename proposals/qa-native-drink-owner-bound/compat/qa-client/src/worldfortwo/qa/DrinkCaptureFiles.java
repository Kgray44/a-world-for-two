package worldfortwo.qa;

import java.nio.ByteBuffer;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.LinkOption;
import java.nio.file.Path;

/** File bounds for the existing native-drink observer, with no game interaction. */
final class DrinkCaptureFiles {
    static final int OWNER_MAX_BYTES=64*1024,SMALL_MAX_BYTES=4096;
    private DrinkCaptureFiles() {}

    static String readOwner(Path path) throws Exception {
        return read(path,OWNER_MAX_BYTES,"owner marker");
    }
    static String readSmall(Path path) throws Exception {
        return read(path,SMALL_MAX_BYTES,"private authorization/request");
    }
    private static String read(Path path,int maximum,String role) throws Exception {
        if(!Files.isRegularFile(path,LinkOption.NOFOLLOW_LINKS)||Files.isSymbolicLink(path)||Files.size(path)>maximum)
            throw new IllegalStateException("Regular bounded "+role+" required");
        byte[] raw;
        try(var stream=Files.newInputStream(path,LinkOption.NOFOLLOW_LINKS)) {
            raw=stream.readNBytes(maximum+1);
        }
        if(raw.length>maximum)throw new IllegalStateException(role+" changed beyond bound");
        // Keep Files.readString's strict UTF-8 behavior; do not replace malformed bytes.
        return StandardCharsets.UTF_8.newDecoder().decode(ByteBuffer.wrap(raw)).toString();
    }
}
