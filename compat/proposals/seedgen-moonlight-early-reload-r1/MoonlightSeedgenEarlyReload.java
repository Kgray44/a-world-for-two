package worldfortwo.bridge;

import java.io.IOException;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.LinkOption;
import java.nio.file.Path;
import java.nio.file.attribute.BasicFileAttributes;
import java.security.MessageDigest;
import java.util.HexFormat;
import java.util.List;
import java.util.Objects;
import java.util.concurrent.atomic.AtomicBoolean;
import net.mehvahdjukaar.moonlight.api.misc.IProgressTracker;
import net.mehvahdjukaar.moonlight.api.platform.PlatHelper;
import net.mehvahdjukaar.moonlight.core.misc.ReloadInstanceWrapper;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.packs.PackResources;
import net.minecraft.server.packs.PackType;
import net.minecraft.server.packs.resources.ResourceManager;
import net.neoforged.api.distmarker.Dist;
import net.neoforged.fml.ModList;
import net.neoforged.fml.loading.FMLEnvironment;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/** Original compatibility call into Moonlight's ordinary early data reload.
 * Invoke after the native manager is constructed, before its first registry read.
 * This may perform Moonlight's normal cache generation; it is not a read-only probe.
 */
public final class MoonlightSeedgenEarlyReload {
    private static final Logger LOG=LoggerFactory.getLogger("AWFT-SeedGen-Moonlight");
    private static final AtomicBoolean ACTIVE=new AtomicBoolean();
    private static final int MAX_PACKS=512;
    private MoonlightSeedgenEarlyReload(){}

    public static void prepare(boolean withMods,ResourceManager resources,List<PackResources> opened) {
        if(!withMods)return;
        if(FMLEnvironment.dist!=Dist.CLIENT)
            throw new IllegalStateException("Moonlight SeedGen early reload is client-only");
        if(!ACTIVE.compareAndSet(false,true))
            throw new IllegalStateException("Concurrent/reentrant Moonlight SeedGen reload refused");
        try {
            var selected=selected(resources,opened);
            PackResources generated=null;
            for(PackResources pack:selected) {
                boolean type=MoonlightCachePackCustody.matches(pack);
                boolean id=MoonlightCachePackCustody.PACK.equals(pack.packId());
                if(type!=id)throw new IOException("Unreviewed Moonlight cached class/pack identity");
                if(type) {
                    if(generated!=null)throw new IOException("Duplicate Moonlight generated pack");
                    generated=pack;
                }
            }
            // No selected reviewed provider means there is no cache to prepare.
            // The later complete resource attestation still checks every pack.
            if(generated==null)return;
            artifact("moonlight",2299162,MoonlightCachePackCustody.JAR_SHA);
            artifact("seedrenderer",1355029,"58469f92f7cf13ff3c2928659ce1a57d7d05314b30e0779cb187b6fbfdb43b4e");
            pin(ReloadInstanceWrapper.class,6448,"83a3f999f0d4887d8765e4164b7bef559d5e33eaee239db44e05280278e047b8");
            pin(IProgressTracker.class,674,"d7559cb9ba6bd8e8cdf2cb14cfd1c0070babb89912685be9a2bab8ff61ac6daa");
            pinName("net.mehvahdjukaar.moonlight.api.misc.IProgressTracker$Tree",2536,"50843ca1717b784f802e355396849f0a868afbf5af0396c7baa9b0f03c3f0443");
            pinName("net.mehvahdjukaar.moonlight.api.events.EarlyPackReloadEvent",2949,"e9f735ea63a99cc9557897068307a9beb68a4bda9722e6cc2598777e14351d12");
            pinName("net.mehvahdjukaar.moonlight.core.pack.DynamicResourcesInternals",10683,"1bfae9472a04ff12b6880e33ca09f8147ebc3f16c875d45fd89af6f5e67b47a2");
            pinName("net.mehvahdjukaar.moonlight.api.resources.pack.DynamicResourcesProvider",15293,"10ddb6444a49129f51dbc60b18790451a743f62038525a9e0bed7c61641ac229");
            pinName("net.mehvahdjukaar.moonlight.api.resources.pack.GlobalCachedStrategy",9554,"99c1ce4e8dd3f4cd62b42f2075025571bee6b18a57c6fe84d14399ac8e8c3075");
            pinResource(ReloadInstanceWrapper.class,"net/mehvahdjukaar/moonlight/core/mixins/WorldLoaderMixin.class",4070,"db6ae46336727ad3709d2e1869930aea0ceeff5d126920affe2f1a32596827ef");
            pinName("mobius.seedrenderer.dh.ClientWorldgen",18546,"d352c1c7fa607f2ba29eac97364eda8ed126984161386acdab693acdbebc4c19");

            // The ordinary WorldLoader hook requires this selected native token
            // and completed mod initialization. Refuse rather than inventing
            // readiness or waiting/retrying while initialization is in progress.
            if(PlatHelper.isInitializing()||resources.getResource(
                    ResourceLocation.fromNamespaceAndPath("moonlight","moonlight/token.json")).isEmpty())
                throw new IOException("Normal Moonlight early data reload eligibility is not ready");

            // Exact normal entry: refresh native strategy -> provider prepare ->
            // reload/generation -> native commit. No direct delegate writes,
            // directory-presence readiness inference, cache copying or retry.
            ReloadInstanceWrapper.executeEarlyReloadBlocking(
                PackType.SERVER_DATA,resources,IProgressTracker.createTree(1));
            samePacks(selected,selected(resources,opened));
            var view=MoonlightCachePackCustody.inspect(generated);
            view.unchanged();
            LOG.info("SeedGen completed native Moonlight early SERVER_DATA reload before registry reads; strict resource/fingerprint qualification remains required");
        }catch(VirtualMachineError|ThreadDeath failure){throw failure;}
        catch(Throwable failure){throw new IllegalStateException("Native Moonlight SeedGen early data reload failed; no empty-cache substitute",failure);}
        finally{ACTIVE.set(false);}
    }

    private static List<PackResources> selected(ResourceManager resources,List<PackResources> opened)throws IOException {
        if(resources==null||opened==null||opened.size()>MAX_PACKS)
            throw new IOException("Bounded native SeedGen resource selection required");
        List<PackResources> actual;
        try(var stream=resources.listPacks()){actual=stream.limit(MAX_PACKS+1L).toList();}
        samePacks(opened,actual);
        return actual;
    }
    static void samePacks(List<PackResources> expected,List<PackResources> actual)throws IOException {
        if(expected.size()>MAX_PACKS||expected.size()!=actual.size())
            throw new IOException("Native SeedGen selected pack count changed");
        for(int i=0;i<expected.size();i++)
            if(expected.get(i)==null||expected.get(i)!=actual.get(i))
                throw new IOException("Native SeedGen selected pack identity/order changed");
    }
    private static void artifact(String mod,int size,String sha)throws IOException {
        var file=ModList.get().getModFileById(mod);
        if(file==null)throw new IOException("Pinned native provider missing: "+mod);
        Path path=file.getFile().getFilePath();
        var before=Files.readAttributes(path,BasicFileAttributes.class,LinkOption.NOFOLLOW_LINKS);
        if(!before.isRegularFile()||before.isSymbolicLink()||before.size()!=size)
            throw new IOException("Pinned ordinary provider artifact required: "+mod);
        try(InputStream input=Files.newInputStream(path)) {
            if(!sha.equals(hash(input,size)))throw new IOException("Pinned provider artifact differs: "+mod);
        }
        var after=Files.readAttributes(path,BasicFileAttributes.class,LinkOption.NOFOLLOW_LINKS);
        if(!after.isRegularFile()||after.isSymbolicLink()||after.size()!=before.size()
                ||!after.lastModifiedTime().equals(before.lastModifiedTime())
                ||!Objects.equals(after.fileKey(),before.fileKey()))
            throw new IOException("Native provider artifact changed during custody: "+mod);
    }
    private static void pinName(String name,int size,String sha)throws ClassNotFoundException,IOException {
        pin(Class.forName(name,false,MoonlightSeedgenEarlyReload.class.getClassLoader()),size,sha);
    }
    private static void pin(Class<?> type,int size,String sha)throws IOException {
        pinResource(type,type.getName().replace('.','/')+".class",size,sha);
    }
    private static void pinResource(Class<?> owner,String name,int size,String sha)throws IOException {
        try(InputStream input=owner.getResourceAsStream("/"+name)) {
            if(input==null||!sha.equals(hash(input,size)))
                throw new IOException("Pinned native lifecycle class resource differs: "+name);
        }
    }
    private static String hash(InputStream input,int exact)throws IOException {
        try {
            MessageDigest digest=MessageDigest.getInstance("SHA-256");byte[] buffer=new byte[8192];int total=0;
            for(int n;(n=input.read(buffer))!=-1;) {
                total+=n;if(total>exact)throw new IOException("Bounded native lifecycle artifact exceeded");
                digest.update(buffer,0,n);
            }
            if(total!=exact)throw new IOException("Native lifecycle artifact truncated");
            return HexFormat.of().formatHex(digest.digest());
        }catch(java.security.NoSuchAlgorithmException impossible){throw new AssertionError(impossible);}
    }
}
