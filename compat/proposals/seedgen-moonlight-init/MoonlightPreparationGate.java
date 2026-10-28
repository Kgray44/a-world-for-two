package worldfortwo.bridge;

import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.channels.FileChannel;
import java.nio.file.*;
import java.nio.file.attribute.BasicFileAttributes;
import java.util.Arrays;
import java.util.Objects;

/** A failed native preparation remains blocked across later client launches. */
final class MoonlightPreparationGate {
    private static final String NAME="moonlight-native-preparation.pending";
    private final Path path;private final byte[] token;
    private MoonlightPreparationGate(Path path,byte[] token){this.path=path;this.token=token.clone();}
    static void requireClear(Path directory)throws IOException {
        if(Files.exists(directory.resolve(NAME),LinkOption.NOFOLLOW_LINKS))
            throw new IOException("Unresolved native Moonlight preparation; owner must review retained backup before another attempt");
    }
    static MoonlightPreparationGate create(Path directory,byte[] token)throws IOException {
        if(token==null||token.length==0||token.length>2048)throw new IOException("Bounded preparation marker required");
        Path path=directory.resolve(NAME);
        try(FileChannel out=FileChannel.open(path,StandardOpenOption.CREATE_NEW,StandardOpenOption.WRITE)){
            ByteBuffer data=ByteBuffer.wrap(token);while(data.hasRemaining())out.write(data);out.force(true);
        }
        return new MoonlightPreparationGate(path,token);
    }
    void complete()throws IOException {
        var before=Files.readAttributes(path,BasicFileAttributes.class,LinkOption.NOFOLLOW_LINKS);
        if(!before.isRegularFile()||before.isSymbolicLink()||before.isOther()||before.size()!=token.length)
            throw new IOException("Owned preparation gate changed");
        byte[] bytes=Files.readAllBytes(path);
        var after=Files.readAttributes(path,BasicFileAttributes.class,LinkOption.NOFOLLOW_LINKS);
        if(!Arrays.equals(bytes,token)||!after.isRegularFile()||after.isSymbolicLink()||after.isOther()
                ||!Objects.equals(before.fileKey(),after.fileKey())||before.size()!=after.size()
                ||!before.lastModifiedTime().equals(after.lastModifiedTime()))throw new IOException("Owned preparation gate changed");
        Files.delete(path); // Only the exact owned marker. No cache or backup deletion/restoration.
    }
}
