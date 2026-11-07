package worldfortwo.bridge;

import java.io.IOException;
import java.nio.file.FileSystems;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.security.MessageDigest;
import java.util.HexFormat;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import net.minecraft.SharedConstants;
import net.minecraft.network.chat.Component;
import net.minecraft.server.Bootstrap;
import net.minecraft.server.packs.CompositePackResources;
import net.minecraft.server.packs.PackLocationInfo;
import net.minecraft.server.packs.PackResources;
import net.minecraft.server.packs.PackType;
import net.minecraft.server.packs.PathPackResources;
import net.minecraft.server.packs.repository.PackSource;
import net.minecraft.server.packs.resources.MultiPackResourceManager;

/** Pinned actual archive and actual native pack methods; no modloader/client/server/world. */
public final class NativeTectonicEmptyOverlayProbe {
    private static int checks;
    public static void main(String[] args)throws Throwable {
        if(args.length!=2)throw new IllegalArgumentException("Pinned Tectonic archive and owned fixture directory required");
        SharedConstants.tryDetectVersion();Bootstrap.bootStrap();
        Path archive=Path.of(args[0]).toAbsolutePath(),owned=Path.of(args[1]).toAbsolutePath();Files.createDirectories(owned);
        String original=sha(Files.readAllBytes(archive));
        try(var fs=FileSystems.newFileSystem(archive,Map.of())){
            Path root=fs.getPath("/resourcepacks/tectonic"),absent=root.resolve("intentionally_empty");
            var primary=path(root,"tectonic");var empty=path(absent,"tectonic");
            var nativeComposite=new CompositePackResources(primary,List.of(empty));
            check(!Files.exists(absent),"Pinned declared-empty directory is actually absent");
            check(empty.getNamespaces(PackType.SERVER_DATA).isEmpty(),"Native empty child namespaces");
            check(empty.getRootResource("pack.mcmeta")==null,"Native empty child root metadata is absent");
            LithostitchedSeedgenResources.attestDeclaredEmptyTectonicOverlay(empty,nativeComposite,archive,root);checks++;
            // Full old behavior would fail: the now-qualified path is not a directory.
            check(!Files.isDirectory(absent),"Old blanket directory precondition rejects this real native child");
            refused(()->LithostitchedSeedgenResources.attestDeclaredEmptyTectonicOverlay(
                path(root.resolve("some_other_missing_root"),"tectonic"),nativeComposite,archive,root),"Other missing path is not excused");
            refused(()->LithostitchedSeedgenResources.attestDeclaredEmptyTectonicOverlay(
                empty,new CompositePackResources(path(root,"unknown-parent"),List.of(empty)),archive,root),"Wrong parent identity refuses");
            refused(()->LithostitchedSeedgenResources.attestDeclaredEmptyTectonicOverlay(
                empty,new CompositePackResources(primary,List.of(empty,empty)),archive,root),"Duplicate native child refuses");
            refused(()->LithostitchedSeedgenResources.attestDeclaredEmptyTectonicOverlay(
                empty,new CompositePackResources(primary,List.of()),archive,root),"Unowned child outside native topology refuses");
            refused(()->LithostitchedSeedgenResources.attestDeclaredEmptyTectonicOverlay(
                empty,nativeComposite,archive,owned.resolve("different-primary")),"Different authoritative primary root refuses");
            var subclass=new PathPackResources(info("tectonic"),absent){};
            refused(()->LithostitchedSeedgenResources.attestDeclaredEmptyTectonicOverlay(
                subclass,new CompositePackResources(primary,List.of(subclass)),archive,root),"Unknown native subclass refuses");
            Path tampered=owned.resolve("changed-pinned-archive.bin");Files.copy(archive,tampered);
            Files.write(tampered,new byte[]{1},StandardOpenOption.APPEND);
            refused(()->LithostitchedSeedgenResources.attestDeclaredEmptyTectonicOverlay(
                empty,nativeComposite,tampered,root),"Changed artifact refuses");
            // Exercise the ordinary production capture boundary for an unknown missing root.
            Path missing=owned.resolve("ordinary-missing-root");var unknown=path(missing,"unqualified-ordinary");
            try(var manager=new MultiPackResourceManager(PackType.SERVER_DATA,List.of(unknown))){
                try{LithostitchedSeedgenResources.capture(List.of(unknown),manager);throw new AssertionError("Unknown missing root became fake-empty");}
                catch(IOException expected){check(expected.getMessage().contains("Exact native pack root refusal")
                    &&expected.getMessage().contains("unqualified-ordinary")&&expected.getMessage().contains("PathPackResources")
                    &&expected.getMessage().contains(missing.toString())&&expected.getMessage().contains("parent=none"),"Unknown root still refuses with precise native facts");}
            }
        }
        check(original.equals(sha(Files.readAllBytes(archive))),"Pinned source archive remains byte-identical");
        System.out.println("PROBE_RESULT {\"passed\":true,\"checks\":"+checks+",\"exact_pinned_native_empty_child_attested\":true,\"old_missing_directory_blocker_reproduced\":true,\"unknown_missing_roots_refused\":true,\"topology_artifact_native_class_and_root_changes_refused\":true,\"precise_refusal_facts_verified\":true,\"pinned_archive_unchanged\":true,\"world_started\":false}");
    }
    private static PackLocationInfo info(String id){return new PackLocationInfo(id,Component.literal(id),PackSource.BUILT_IN,Optional.empty());}
    private static PathPackResources path(Path root,String id){return new PathPackResources(info(id),root);}
    private static void check(boolean value,String message){if(!value)throw new AssertionError(message);checks++;}
    @FunctionalInterface private interface Checked{void run()throws Throwable;}
    private static void refused(Checked action,String message)throws Throwable {
        try{action.run();throw new AssertionError(message);}catch(IOException expected){checks++;}
    }
    private static String sha(byte[] bytes)throws Exception{return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(bytes));}
}
