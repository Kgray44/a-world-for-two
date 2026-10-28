package worldfortwo.bridge;

import java.io.IOException;
import java.io.InputStream;
import java.lang.invoke.MethodHandle;
import java.lang.invoke.MethodHandles;
import java.nio.file.Files;
import java.nio.file.LinkOption;
import java.nio.file.Path;
import java.nio.file.attribute.BasicFileAttributes;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.HexFormat;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.TreeMap;
import java.util.TreeSet;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.packs.PackResources;
import net.minecraft.server.packs.PackType;
import net.minecraft.server.packs.PathPackResources;
import net.neoforged.fml.ModList;

/** Exact read-only Moonlight3.7.2 cached-folder view. No initialize/commit/close. */
final class MoonlightCachePackCustody {
    record RootStamp(int bytes,String sha256){}
    static final String TYPE="net.mehvahdjukaar.moonlight.api.resources.pack.CachePathPackResources";
    static final String BASE="net.mehvahdjukaar.moonlight.api.resources.pack.AbstractCachedEditableResources";
    static final String FAST="net.mehvahdjukaar.moonlight.api.resources.pack.FastSearchPathPackResources";
    static final String PACK="supplementaries:generated_pack";
    static final String JAR_SHA="4a9f15108607cc70273f8a0b6eb24e1e99af8eef44bc3ae8681767ca7ce21b0f";
    private static final int MAX_NAMESPACES=4096,MAX_ROOT_FILES=4096,MAX_ROOT_BYTES=32*1024*1024;
    private MoonlightCachePackCustody(){}
    static boolean matches(PackResources pack){return pack.getClass().getName().equals(TYPE);}

    static View inspect(PackResources pack)throws IOException {
        var mod=ModList.get().getModContainerById("moonlight").orElseThrow();
        if(!mod.getModInfo().getVersion().toString().equals("1.21.1-3.7.2"))
            throw new IOException("Exact Moonlight3.7.2 cached provider required");
        return inspect(pack,ModList.get().getModFileById("moonlight").getFile().getFilePath());
    }

    /** Offline exact-JAR fixture entry point; not a runtime path override. */
    static View inspect(PackResources pack,Path jar)throws IOException {
        if(!matches(pack)||!pack.packId().equals(PACK))throw new IOException("Unreviewed Moonlight provider class/pack identity");
        var before=Files.readAttributes(jar,BasicFileAttributes.class,LinkOption.NOFOLLOW_LINKS);
        if(!before.isRegularFile()||before.isSymbolicLink()||before.size()!=2299162)
            throw new IOException("Exact ordinary Moonlight provider artifact required");
        try(InputStream input=Files.newInputStream(jar)){
            if(!JAR_SHA.equals(hash(input,2299162)))throw new IOException("Pinned Moonlight artifact differs");
        }
        var after=Files.readAttributes(jar,BasicFileAttributes.class,LinkOption.NOFOLLOW_LINKS);
        if(!same(before,after))throw new IOException("Moonlight artifact changed during custody");
        Class<?> type=pack.getClass(),base=type.getSuperclass();
        if(!base.getName().equals(BASE))throw new IOException("Pinned Moonlight superclass differs");
        classPin(type,5276,"17d77a2dfb8f3dca2967c2dfc4c339e74de64120b810c12cbe94f1cccef022b4");
        classPin(base,6255,"9e6203c7f19346c2fbf71e2a72563b7b336a3074b2119a99419d40d0adf4c79c");
        try{
            MethodHandle path=get(base,"path",Path.class),kind=get(base,"packType",PackType.class);
            MethodHandle cache=get(base,"cachedResources",PackResources.class),roots=get(base,"rootResources",Map.class);
            Path root=(Path)path.invoke(pack);PackType packType=(PackType)kind.invoke(pack);
            PackResources delegate=(PackResources)cache.invoke(pack);
            if(packType!=PackType.SERVER_DATA||delegate==null)throw new IOException("Moonlight server-data cache is not initialized; never infer empty");
            ordinaryDirectory(root);
            Class<?> child=delegate.getClass();Path childRoot;
            if(child==PathPackResources.class){childRoot=(Path)get(child,"root",Path.class).invoke(delegate);}
            else if(child.getName().equals(FAST)){
                classPin(child,10987,"dc65980d1bd9af4ccb052f0e90bcb9785ac0856d644d9266407c1e51969091c4");
                if((PackType)get(child,"packType",PackType.class).invoke(delegate)!=PackType.SERVER_DATA)
                    throw new IOException("Moonlight cached delegate pack type differs");
                childRoot=(Path)get(child,"root",Path.class).invoke(delegate);
            }else throw new IOException("Unreviewed Moonlight cached delegate implementation");
            ordinaryDirectory(childRoot);
            if(!root.toRealPath().equals(childRoot.toRealPath()))throw new IOException("Moonlight wrapper/delegate roots differ");
            var namespaces=namespaces(pack);
            var rootBytes=rootFiles(roots.invoke(pack));
            return new View(pack,delegate,root,root.toRealPath(),namespaces,rootBytes,path,kind,cache,roots);
        }catch(IOException failure){throw failure;}
        catch(VirtualMachineError|ThreadDeath failure){throw failure;}
        catch(Throwable failure){throw new IOException("Exact Moonlight cached provider view failed",failure);}
    }

    static final class View {
        final PackResources pack,delegate;
        final Path root,realRoot;
        final Set<String> namespaces;
        final Map<String,RootStamp> rootBytes;
        final MethodHandle path,kind,cache,roots;
        View(PackResources pack,PackResources delegate,Path root,Path realRoot,Set<String> namespaces,
             Map<String,RootStamp> rootBytes,MethodHandle path,MethodHandle kind,MethodHandle cache,MethodHandle roots){
            this.pack=pack;this.delegate=delegate;this.root=root;this.realRoot=realRoot;this.namespaces=namespaces;
            this.rootBytes=rootBytes;this.path=path;this.kind=kind;this.cache=cache;this.roots=roots;
        }
        void unchanged()throws IOException {
            try{
                ordinaryDirectory(root);
                if(cache.invoke(pack)!=delegate||kind.invoke(pack)!=PackType.SERVER_DATA
                        ||!((Path)path.invoke(pack)).toRealPath().equals(realRoot)||!root.toRealPath().equals(realRoot)
                        ||!namespaces(pack).equals(namespaces))throw new IOException("Moonlight cache changed during inventory");
                var current=rootFiles(roots.invoke(pack));
                if(!current.equals(rootBytes))throw new IOException("Moonlight root resource keys/bytes changed");
            }catch(IOException failure){throw failure;}
            catch(VirtualMachineError|ThreadDeath failure){throw failure;}
            catch(Throwable failure){throw new IOException("Moonlight cached view changed/unavailable",failure);}
        }
    }

    private static Set<String> namespaces(PackResources pack)throws IOException {
        Set<String> nativeNames=pack.getNamespaces(PackType.SERVER_DATA);
        if(nativeNames==null||nativeNames.size()>MAX_NAMESPACES)throw new IOException("Bounded actual Moonlight namespaces required");
        var result=new TreeSet<String>();
        for(String name:nativeNames)if(name==null||!ResourceLocation.isValidNamespace(name)||!result.add(name))
            throw new IOException("Invalid/duplicate Moonlight namespace");
        return Set.copyOf(result);
    }
    private static Map<String,RootStamp> rootFiles(Object value)throws IOException {
        if(!(value instanceof Map<?,?> map)||map.size()>MAX_ROOT_FILES)throw new IOException("Bounded original Moonlight root resources required");
        var result=new TreeMap<String,RootStamp>();long bytes=0;
        for(var entry:map.entrySet()){
            if(!(entry.getKey()instanceof String name)||name.length()>4096||!(entry.getValue()instanceof byte[] raw)
                    ||(bytes+=raw.length)>MAX_ROOT_BYTES||result.put(name,new RootStamp(raw.length,bytesHash(raw)))!=null)
                throw new IOException("Bounded exact Moonlight root resource bytes required");
        }
        return Map.copyOf(result);
    }
    private static String bytesHash(byte[] raw){
        try{return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(raw));}
        catch(NoSuchAlgorithmException impossible){throw new AssertionError(impossible);}
    }
    private static MethodHandle get(Class<?> owner,String name,Class<?> type)throws ReflectiveOperationException {
        return MethodHandles.privateLookupIn(owner,MethodHandles.lookup()).findGetter(owner,name,type);
    }
    private static void ordinaryDirectory(Path path)throws IOException {
        if(path==null)throw new IOException("Moonlight native cache path missing");
        var value=Files.readAttributes(path,BasicFileAttributes.class,LinkOption.NOFOLLOW_LINKS);
        if(!value.isDirectory()||value.isSymbolicLink())throw new IOException("Moonlight native cache must be an ordinary available directory");
    }
    private static void classPin(Class<?> type,int size,String sha)throws IOException {
        try(InputStream input=type.getResourceAsStream(type.getSimpleName()+".class")){
            if(input==null||!sha.equals(hash(input,size)))throw new IOException("Pinned Moonlight provider class differs: "+type.getName());
        }
    }
    private static boolean same(BasicFileAttributes a,BasicFileAttributes b){
        return b.isRegularFile()&&!b.isSymbolicLink()&&a.size()==b.size()&&a.lastModifiedTime().equals(b.lastModifiedTime())&&Objects.equals(a.fileKey(),b.fileKey());
    }
    private static String hash(InputStream input,int exact)throws IOException {
        try{
            MessageDigest digest=MessageDigest.getInstance("SHA-256");byte[] buffer=new byte[8192];int total=0;
            for(int n;(n=input.read(buffer))!=-1;){total+=n;if(total>exact)throw new IOException("Exact Moonlight custody size exceeded");digest.update(buffer,0,n);}
            if(total!=exact)throw new IOException("Pinned Moonlight custody is truncated");
            return HexFormat.of().formatHex(digest.digest());
        }catch(NoSuchAlgorithmException impossible){throw new AssertionError(impossible);}
    }
}
