package worldfortwo.bridge;

import com.google.gson.Gson;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.security.MessageDigest;
import java.util.*;

/** Immutable terminal receipts survive Windows readers of the progress file. */
final class NativeJournal {
    private static final Gson JSON=new Gson();
    static void progress(Path directory,String name,Map<String,Object> report)throws Exception{
        Path target=directory.resolve(name),temporary=directory.resolve(name+".tmp");
        Files.createDirectories(directory);Files.writeString(temporary,JSON.toJson(report));
        try{Files.move(temporary,target,StandardCopyOption.REPLACE_EXISTING,StandardCopyOption.ATOMIC_MOVE);}
        catch(AccessDeniedException error){
            // A viewer may omit FILE_SHARE_DELETE. Keep the mechanism running;
            // the immutable terminal receipt is authoritative, not this view.
            report.put("progress_publication_warning",error.toString());
        }
    }
    static void terminal(Path directory,String family,Map<String,Object> report)throws Exception{
        Files.createDirectories(directory);
        byte[] raw=JSON.toJson(report).getBytes(StandardCharsets.UTF_8);
        if(raw.length>8*1024*1024)throw new IllegalStateException("Native receipt exceeds its bound");
        Path target=directory.resolve(family+"-result-"+UUID.randomUUID()+".json");
        Files.write(target,raw,StandardOpenOption.CREATE_NEW,StandardOpenOption.WRITE);
        // Published only after the JSON handle closes. Neither file is replaced.
        String sha=HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(raw));
        Files.writeString(target.resolveSibling(target.getFileName()+".complete"),sha,
            StandardOpenOption.CREATE_NEW,StandardOpenOption.WRITE);
    }
}
