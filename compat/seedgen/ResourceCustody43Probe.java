package worldfortwo.bridge;

import java.io.IOException;
import java.lang.invoke.MethodHandles;
import java.lang.invoke.MethodType;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.TreeSet;
import java.util.zip.ZipEntry;
import java.util.zip.ZipOutputStream;
import net.minecraft.FileUtil;
import net.minecraft.SharedConstants;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.Bootstrap;
import net.minecraft.server.packs.CompositePackResources;
import net.minecraft.server.packs.FilePackResources;
import net.minecraft.server.packs.PackLocationInfo;
import net.minecraft.server.packs.PackResources;
import net.minecraft.server.packs.PackType;
import net.minecraft.server.packs.PathPackResources;
import net.minecraft.server.packs.VanillaPackResources;
import net.minecraft.server.packs.repository.PackSource;
import net.minecraft.server.packs.resources.MultiPackResourceManager;

/** Exact installed API fixture only; no modloader, game, downloads or world. */
public final class ResourceCustody43Probe {
    private static final String NAME="structure_config/t_and_t_ED.json";
    private static final String META="{\"pack\":{\"pack_format\":48,\"description\":\"original offline fixture\"}}";
    private static int checks;
    public static void main(String[] ignored)throws Throwable {
        SharedConstants.tryDetectVersion();Bootstrap.bootStrap();
        check(ResourceLocation.tryBuild("fixture",NAME)==null,"Named API factory must reject uppercase spelling");
        // TEST ONLY: construct the exact spelling observed in the REAL NeoForge
        // log. This does not simulate NeoForge's transformations or alter them.
        var constructor=MethodHandles.privateLookupIn(ResourceLocation.class,MethodHandles.lookup())
            .findConstructor(ResourceLocation.class,MethodType.methodType(void.class,String.class,String.class));
        ResourceLocation observed=(ResourceLocation)constructor.invokeExact("fixture",NAME);
        check(observed.getPath().equals(NAME),"Observed spelling retained exactly");
        check(FileUtil.decomposePath(NAME).error().isPresent(),"Actual FileUtil rejects observed path segment");

        Path first=makePath("path-a","raw-first"),second=makePath("path-b","raw-second");
        var a=path(first,"same-native-id");var b=path(second,"overlay");
        check(a.getResource(PackType.SERVER_DATA,observed)==null,"Actual Path native lookup returns null");
        check(LithostitchedSeedgenResources.selected(a,observed,Set.of("fixture/"+NAME),List.of())==null,"Exact raw Path witness admits only native absence");
        check(!LithostitchedSeedgenResources.attestedNativeAbsence(PathPackResources.class,observed,Set.of(),List.of()),"No raw witness refuses");
        check(!LithostitchedSeedgenResources.attestedNativeAbsence(PackResources.class,observed,Set.of("fixture/"+NAME),List.of()),"Unknown implementation refuses");
        check(LithostitchedSeedgenResources.attestedNativeAbsence(VanillaPackResources.class,observed,Set.of("fixture/"+NAME),List.of()),"Vanilla needs the same native grammar plus admitted raw member");
        var initial=attest(List.of(a));
        check(initial.equals(attest(List.of(a))),"Identical original bytes are deterministic");
        Files.writeString(first.resolve("data/fixture/"+NAME),"raw-first-changed");
        check(!initial.equals(attest(List.of(a))),"Unservable raw metadata mutation changes complete attestation");

        var composite=new CompositePackResources(a,List.of(b));
        var before=attest(List.of(composite));
        Files.writeString(first.resolve("data/fixture/"+NAME),"masked-underlay-changed-again");
        check(!before.equals(attest(List.of(composite))),"Masked child raw metadata mutation changes attestation");
        var noRead=inventory(observed,false);var yesRead=inventory(observed,true);
        check(LithostitchedSeedgenResources.selected(composite,observed,Set.of(),List.of(noRead,noRead))==null,"Composite null requires all child witnesses unreadable");
        check(!LithostitchedSeedgenResources.attestedNativeAbsence(CompositePackResources.class,observed,Set.of(),List.of(noRead,yesRead)),"Composite must not hide a readable ZIP or other child");
        check(!LithostitchedSeedgenResources.attestedNativeAbsence(CompositePackResources.class,observed,Set.of(),List.of()),"Composite absence without child membership refuses");
        var unknownRead=new LithostitchedSeedgenResources.Inventory(new TreeSet<>(Set.of(observed)),Map.of());
        check(!LithostitchedSeedgenResources.attestedNativeAbsence(CompositePackResources.class,observed,Set.of(),List.of(unknownRead)),"Missing selected-child readability proof refuses");

        ResourceLocation valid=ResourceLocation.parse("fixture:structure_config/valid.json");
        Files.delete(first.resolve("data/fixture/structure_config/valid.json"));
        try{LithostitchedSeedgenResources.selected(a,valid,Set.of("fixture/"+valid.getPath()),List.of());throw new AssertionError("Valid vanished resource admitted");}
        catch(IOException expected){check(expected.getMessage().contains("unavailable"),"Valid native missing resource refuses at production boundary");}
        check(!LithostitchedSeedgenResources.attestedNativeAbsence(CompositePackResources.class,valid,Set.of(),List.of(inventory(valid,false))),"Even forged all-unreadable child data cannot excuse valid missing path");

        Path zipA=makeZip("native-a.zip","zip-original"),zipB=makeZip("native-b.zip","zip-changed");
        LithostitchedSeedgenResources.Attestation zipInitial;
        try(var zip=new FilePackResources.FileResourcesSupplier(zipA).openPrimary(info("same-zip-id"))) {
            var nativeSource=zip.getResource(PackType.SERVER_DATA,observed);
            check(nativeSource!=null,"Actual File native lookup serves uppercase exact ZIP entry");
            try(var stream=nativeSource.get()){check(new String(stream.readAllBytes(),StandardCharsets.UTF_8).equals("zip-original"),"Actual File native bytes retained");}
            check(LithostitchedSeedgenResources.selected(zip,observed,Set.of(),List.of())!=null,"Readable ZIP path never downgraded to native absence");
            try(var manager=new MultiPackResourceManager(PackType.SERVER_DATA,List.of(zip))) {
                namedManagerGrammar(manager,observed);
                zipInitial=LithostitchedSeedgenResources.capture(List.of(zip),manager);
            }
        }
        try(var zip=new FilePackResources.FileResourcesSupplier(zipB).openPrimary(info("same-zip-id"))) {
            check(!zipInitial.equals(attest(List.of(zip))),"Exact raw uppercase ZIP entry mutation changes attestation");
        }
        try(var zip=new FilePackResources.FileResourcesSupplier(zipA).openPrimary(info("zip-overlay"))) {
            var mixed=new CompositePackResources(a,List.of(zip));
            check(LithostitchedSeedgenResources.selected(mixed,observed,Set.of(),List.of(noRead,yesRead))!=null,"Actual Composite retains readable ZIP child");
        }
        try(var manager=new MultiPackResourceManager(PackType.SERVER_DATA,List.of(a))) {
            namedManagerGrammar(manager,observed);
        }

        var subclass=new PathPackResources(info("unknown-subclass"),first){};
        try{attest(List.of(subclass));throw new AssertionError("Unknown native pack subclass admitted");}
        catch(IOException expected){check(expected.getMessage().contains("Unsupported actual"),"Unknown actual implementation still refuses");}
        Path malformed=Path.of("broken-root");Files.createDirectory(malformed);Files.writeString(malformed.resolve("data"),"not-directory");
        try{attest(List.of(path(malformed,"broken")));throw new AssertionError("Partial native data root admitted");}
        catch(IOException expected){check(expected.getMessage().contains("regular directory"),"Bad native data root still refuses");}
        check(!attest(List.of(a,b)).equals(attest(List.of(b,a))),"Actual opened pack order remains authoritative");
        System.out.println("PASS "+checks+" exact-API resource custody checks; native transformed enumeration and full strict parity remain unproved");
    }
    private static LithostitchedSeedgenResources.Inventory inventory(ResourceLocation id,boolean readable) {
        return new LithostitchedSeedgenResources.Inventory(new TreeSet<>(Set.of(id)),Map.of(id,readable));
    }
    private static void namedManagerGrammar(MultiPackResourceManager manager,ResourceLocation observed) {
        try{manager.getResourceStack(observed);throw new AssertionError("Named API unexpectedly accepted synthetic observed ID metadata location");}
        catch(net.minecraft.ResourceLocationException expected) {
            check(expected.getMessage().contains(NAME+".mcmeta"),"Untransformed effective manager rejects metadata grammar; no transformed-loader proof claimed");
        }
    }
    private static Path makePath(String name,String value)throws IOException {
        Path root=Path.of(name);Files.createDirectories(root.resolve("data/fixture/structure_config"));
        Files.writeString(root.resolve("pack.mcmeta"),META);
        Files.writeString(root.resolve("data/fixture/"+NAME),value);
        Files.writeString(root.resolve("data/fixture/structure_config/valid.json"),"{\"original\":true}");return root;
    }
    private static Path makeZip(String name,String value)throws IOException {
        Path root=Path.of(name);
        try(var zip=new ZipOutputStream(Files.newOutputStream(root))) {
            member(zip,"pack.mcmeta",META);member(zip,"data/fixture/"+NAME,value);
            member(zip,"data/fixture/structure_config/valid.json","{\"original\":true}");
        }return root;
    }
    private static void member(ZipOutputStream stream,String name,String value)throws IOException {
        stream.putNextEntry(new ZipEntry(name));stream.write(value.getBytes(StandardCharsets.UTF_8));stream.closeEntry();
    }
    private static PackLocationInfo info(String name){return new PackLocationInfo(name,Component.literal(name),PackSource.DEFAULT,Optional.empty());}
    private static PathPackResources path(Path root,String name){return new PathPackResources(info(name),root);}
    private static LithostitchedSeedgenResources.Attestation attest(List<PackResources> packs)throws IOException {
        try(var manager=new MultiPackResourceManager(PackType.SERVER_DATA,packs)){return LithostitchedSeedgenResources.capture(packs,manager);}
    }
    private static void check(boolean condition,String message){if(!condition)throw new AssertionError(message);checks++;}
}
