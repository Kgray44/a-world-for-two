package worldfortwo.packwiz;

import com.google.gson.*;
import java.io.*;
import java.net.URI;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;

/** Actual pinned native cache serialization/reading; never runs installer Main or UI. */
public final class NativeChoicesProbe {
    private static int checks;
    private static Class<?> hashType,formatType,fileType,pathType,parentPath;
    private static Object formatCompanion,base;
    private static void check(boolean value,String reason){checks++;if(!value)throw new AssertionError(reason);}
    private static Object call(Object target,String name,Class<?>[] types,Object... values)throws Exception{return NativeChoices.call(target,name,types,values);}
    private static Object hash(String hex)throws Exception{return formatType.getMethod("fromString",String.class).invoke(call(formatCompanion,"fromName",new Class<?>[]{String.class},"sha256"),hex);}
    private static Object path(String name)throws Exception{return parentPath.getMethod("resolve",String.class).invoke(base,name);}
    private static void set(Object target,String name,Class<?> type,Object value)throws Exception{target.getClass().getMethod(name,type).invoke(target,value);}
    private static void put(Path root,String name,byte[] bytes)throws IOException{Path p=root.resolve(name);Files.createDirectories(p.getParent());Files.write(p,bytes);}
    private static void refuse(Path root,Path installer,ReleaseSpec release,String reason)throws Exception{boolean no=false;try{NativeChoices.attest(root,installer,release);}catch(Exception expected){no=true;}check(no,reason);}
    public static void main(String[] args)throws Exception{
        Path root=Path.of(args[0]).toAbsolutePath();Files.createDirectory(root);Path installer=Path.of(args[1]);
        byte[] body="native-artifact".getBytes(StandardCharsets.UTF_8),config="scene=pinned\n".getBytes(StandardCharsets.UTF_8);
        String artifactHash=AttemptJournal.sha256(body),configHash=AttemptJournal.sha256(config);
        List<ReleaseSpec.Entry> entries=List.of(
            new ReleaseSpec.Entry("mods/required.pw.toml","a".repeat(64),true,new IntegrityGate.Pin("mods/required.jar",body.length,Map.of("SHA-256",artifactHash),false,true),"both","sha256",artifactHash),
            new ReleaseSpec.Entry("mods/essential.pw.toml","b".repeat(64),true,new IntegrityGate.Pin("mods/essential.jar",body.length,Map.of("SHA-256",artifactHash),true,false),"client","sha256",artifactHash),
            new ReleaseSpec.Entry("mods/server.pw.toml","c".repeat(64),true,new IntegrityGate.Pin("mods/server.jar",body.length,Map.of("SHA-256",artifactHash),false,true),"server","sha256",artifactHash),
            new ReleaseSpec.Entry("config/scene.txt",configHash,false,new IntegrityGate.Pin("config/scene.txt",config.length,Map.of("SHA-256",configHash),false,true),"both","sha256",configHash));
        ReleaseSpec release=new ReleaseSpec("0.1.0-candidate.35",URI.create("https://kgray44.github.io/a-world-for-two/releases/0.1.0-candidate.35/pack.toml"),"d".repeat(64),"e".repeat(64),"f".repeat(64),"1".repeat(64),entries);
        Class<?> manifestType=Class.forName("link.infra.packwiz.installer.metadata.ManifestFile");
        fileType=Class.forName("link.infra.packwiz.installer.metadata.ManifestFile$File");
        hashType=Class.forName("link.infra.packwiz.installer.metadata.hash.Hash");formatType=Class.forName("link.infra.packwiz.installer.metadata.hash.HashFormat");
        formatCompanion=formatType.getField("Companion").get(null);
        pathType=Class.forName("link.infra.packwiz.installer.target.path.PackwizFilePath");parentPath=Class.forName("link.infra.packwiz.installer.target.path.PackwizPath");
        Class<?> okio=Class.forName("okio.Path");Object folder=call(okio.getField("Companion").get(null),"get",new Class<?>[]{String.class,boolean.class},root.toString(),false);
        base=pathType.getConstructor(okio,String.class).newInstance(folder,"");Object adapter=call(parentPath.getField("Companion").get(null),"adapterRelativeTo",new Class<?>[]{parentPath},base);
        Gson gson=new GsonBuilder().registerTypeAdapter(hashType,Class.forName("link.infra.packwiz.installer.metadata.hash.Hash$TypeHandler").getConstructor().newInstance())
            .registerTypeAdapter(pathType,adapter).enableComplexMapKeySerialization().create();
        Object manifest=manifestType.getConstructor().newInstance();set(manifest,"setPackFileHash",hashType,hash(release.packSha256()));set(manifest,"setIndexFileHash",hashType,hash(release.indexSha256()));
        Map<Object,Object> files=new HashMap<>();
        for(ReleaseSpec.Entry entry:entries){
            Object file=fileType.getConstructor().newInstance();set(file,"setOptional",boolean.class,entry.pin().optional());set(file,"setOptionValue",boolean.class,!entry.pin().optional());set(file,"setOnlyOtherSide",boolean.class,!entry.client());
            if(entry.client()&&!entry.pin().optional()){
                set(file,"setHash",hashType,hash(entry.metadataSha256()));if(entry.metafile())set(file,"setLinkedFileHash",hashType,hash(entry.downloadHash()));set(file,"setCachedLocation",pathType,path(entry.pin().path()));
            }
            files.put(path(entry.metadata()),file);
        }
        set(manifest,"setCachedFiles",Map.class,files);Path cache=root.resolve("packwiz.json");
        put(root,"mods/required.jar",body);put(root,"config/scene.txt",config);Files.writeString(cache,gson.toJson(manifest,manifestType));
        NativeChoices.Attestation actual=NativeChoices.attest(root,installer,release);
        check(actual.nativeCacheEntries()==4&&!actual.choices().get("mods/essential.jar"),"Actual pinned adapters attest explicit Essential-off, full index and side");
        check(IntegrityGate.verify(root,release.inventory(),actual.choices()).pass(),"Selected installed artifacts/config independently verified");
        check(Files.readString(cache).equals(gson.toJson(manifest,manifestType)),"Choice observation never rewrites cache");
        put(root,"mods/essential.jar",body);check(!IntegrityGate.verify(root,release.inventory(),actual.choices()).pass(),"Native off choice cannot conceal present optional artifact");Files.delete(root.resolve("mods/essential.jar"));
        Object optional=files.get(path("mods/essential.pw.toml"));set(optional,"setOptionValue",boolean.class,true);set(optional,"setHash",hashType,hash("b".repeat(64)));set(optional,"setLinkedFileHash",hashType,hash(artifactHash));set(optional,"setCachedLocation",pathType,path("mods/essential.jar"));
        Files.writeString(cache,gson.toJson(manifest,manifestType));actual=NativeChoices.attest(root,installer,release);check(actual.choices().get("mods/essential.jar")&&!IntegrityGate.verify(root,release.inventory(),actual.choices()).pass(),"Enabled option requires missing artifact, never inferred off");
        set(optional,"setOptionValue",boolean.class,false);set(optional,"setHash",hashType,null);set(optional,"setLinkedFileHash",hashType,null);set(optional,"setCachedLocation",pathType,null);
        set(manifest,"setPackFileHash",hashType,null);Files.writeString(cache,gson.toJson(manifest,manifestType));refuse(root,installer,release,"Ignored native errors lack completed pack identity");set(manifest,"setPackFileHash",hashType,hash(release.packSha256()));
        set(manifest,"setIndexFileHash",hashType,hash("0".repeat(64)));Files.writeString(cache,gson.toJson(manifest,manifestType));refuse(root,installer,release,"Wrong native index refuses");set(manifest,"setIndexFileHash",hashType,hash(release.indexSha256()));
        Object required=files.get(path("mods/required.pw.toml"));set(required,"setHash",hashType,hash("0".repeat(64)));Files.writeString(cache,gson.toJson(manifest,manifestType));refuse(root,installer,release,"Wrong selected metadata hash refuses");set(required,"setHash",hashType,hash("a".repeat(64)));
        set(required,"setCachedLocation",pathType,path("mods/other.jar"));Files.writeString(cache,gson.toJson(manifest,manifestType));refuse(root,installer,release,"Wrong native location refuses");set(required,"setCachedLocation",pathType,path("mods/required.jar"));
        set(required,"setOnlyOtherSide",boolean.class,true);Files.writeString(cache,gson.toJson(manifest,manifestType));refuse(root,installer,release,"Native side cannot disable client artifact");set(required,"setOnlyOtherSide",boolean.class,false);
        set(optional,"setOptional",boolean.class,false);Files.writeString(cache,gson.toJson(manifest,manifestType));refuse(root,installer,release,"Optional classification cannot replace source policy");set(optional,"setOptional",boolean.class,true);
        files.put(path("mods/untrusted.pw.toml"),fileType.getConstructor().newInstance());Files.writeString(cache,gson.toJson(manifest,manifestType));refuse(root,installer,release,"Unknown native index entries refuse");files.remove(path("mods/untrusted.pw.toml"));
        String missing=gson.toJson(manifest,manifestType).replace("\"optionValue\":false,","").replace(",\"optionValue\":false","");Files.writeString(cache,missing);
        refuse(root,installer,release,"Missing optional value natively means true, requiring complete selected provenance");
        System.out.println("NATIVE_CHOICE_CHECKS="+checks+" PASS; pinned cache API only, no installer Main/GUI/network");
    }
}
