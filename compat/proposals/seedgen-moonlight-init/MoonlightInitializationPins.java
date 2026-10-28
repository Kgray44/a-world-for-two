package worldfortwo.bridge;

import java.io.*;
import java.nio.file.*;
import java.nio.file.attribute.BasicFileAttributes;
import java.security.MessageDigest;
import java.util.HexFormat;
import java.util.Objects;
import net.neoforged.fml.ModList;

/** Exact installed native artifacts; no downloads, alternate libraries or version ranges. */
final class MoonlightInitializationPins {
    private MoonlightInitializationPins(){}
    static void verify()throws IOException {
        jar("moonlight","1.21.1-3.7.2",2299162,"4a9f15108607cc70273f8a0b6eb24e1e99af8eef44bc3ae8681767ca7ce21b0f");
        jar("supplementaries","1.21.1-4.0.2",13840377,"2c2e0c98e0cc21874d8b2130bc773a2a5a6cadd854b9c8163d0e1f32e2ddffb0");
        jar("seedrenderer","0.9.1",1355029,"58469f92f7cf13ff3c2928659ce1a57d7d05314b30e0779cb187b6fbfdb43b4e");
    }
    private static void jar(String id,String version,int size,String sha)throws IOException {
        var mod=ModList.get().getModContainerById(id).orElseThrow();
        if(!mod.getModInfo().getVersion().toString().equals(version))throw new IOException("Exact native version required: "+id);
        Path path=ModList.get().getModFileById(id).getFile().getFilePath();
        var before=Files.readAttributes(path,BasicFileAttributes.class,LinkOption.NOFOLLOW_LINKS);
        if(!before.isRegularFile()||before.isSymbolicLink()||before.isOther()||before.size()!=size)throw new IOException("Exact ordinary native artifact required: "+id);
        try(InputStream in=Files.newInputStream(path)){
            var hash=MessageDigest.getInstance("SHA-256");long total=0;byte[] buffer=new byte[8192];
            for(int n;(n=in.read(buffer))!=-1;){if((total+=n)>size)throw new IOException("Native artifact exceeded exact size");hash.update(buffer,0,n);}
            if(total!=size||!HexFormat.of().formatHex(hash.digest()).equals(sha))throw new IOException("Native artifact differs: "+id);
        }catch(java.security.NoSuchAlgorithmException impossible){throw new AssertionError(impossible);}
        var after=Files.readAttributes(path,BasicFileAttributes.class,LinkOption.NOFOLLOW_LINKS);
        if(!after.isRegularFile()||after.isSymbolicLink()||after.isOther()||after.size()!=before.size()
                ||!after.lastModifiedTime().equals(before.lastModifiedTime())||!Objects.equals(after.fileKey(),before.fileKey()))
            throw new IOException("Native artifact changed during verification: "+id);
    }
}
