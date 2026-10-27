package worldfortwo.bridge;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.mojang.serialization.Codec;
import com.mojang.serialization.DataResult;
import com.mojang.serialization.JsonOps;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.lang.invoke.MethodHandles;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.LinkOption;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.Instant;
import java.util.HexFormat;
import java.util.TreeMap;
import java.util.TreeSet;
import net.minecraft.core.Holder;
import net.minecraft.core.Registry;
import net.minecraft.core.RegistryAccess;
import net.minecraft.core.registries.Registries;
import net.minecraft.resources.RegistryOps;
import net.minecraft.resources.ResourceKey;
import net.minecraft.world.level.levelgen.DensityFunction;
import net.minecraft.world.level.levelgen.DensityFunctions;
import net.minecraft.world.level.levelgen.NoiseGeneratorSettings;

/** Explicit, read-only inspection of the exact pinned SeedGen fingerprint inputs.
 * Not an alternate fingerprint authority and never called from gameplay automatically.
 * No SeedSharing method/cache, registry bind, generation setting, seed or world is changed.
 */
public final class WorldgenFingerprintDiagnostics {
    public static final long MAX_OUTPUT_BYTES=16L*1024*1024;
    private static final long STATUS_RESERVE=64*1024;
    private static final long HOST_RESERVE=32_212_254_720L;
    private static final int MAX_ENTRIES=32768;
    private static final int MAX_JSON_BYTES=8*1024*1024;
    private static final Gson JSON=new GsonBuilder().disableHtmlEscaping().create();
    private static final String SHARING_RESOURCE="mobius/seedrenderer/net/SeedSharing.class";
    private static final String SHARING_SHA="33447b2f4f9b151501d05d6992576d0e6eaa517ffa4df30183be6bc97a4f31ec";
    private static final String CLIENT_RESOURCE="mobius/seedrenderer/dh/ClientWorldgen.class";
    private static final String CLIENT_SHA="d352c1c7fa607f2ba29eac97364eda8ed126984161386acdab693acdbebc4c19";

    private WorldgenFingerprintDiagnostics() {}

    /** Read the existing cache by its exact descriptor; never invoke get()/load()/attempt(). */
    public static Path writeLoadedClient(Path privateDirectory,String id,boolean fullEncodings)throws Throwable {
        verifyResource(CLIENT_RESOURCE,CLIENT_SHA);
        Class<?> client=Class.forName("mobius.seedrenderer.dh.ClientWorldgen",false,
            WorldgenFingerprintDiagnostics.class.getClassLoader());
        var getter=MethodHandles.privateLookupIn(client,MethodHandles.lookup())
            .findStaticGetter(client,"loaded",RegistryAccess.Frozen.class);
        RegistryAccess.Frozen access=(RegistryAccess.Frozen)getter.invokeExact();
        if(access==null)throw new IllegalStateException("SeedGen has no already-prepared cached client registry access; no load was requested");
        Path receipt=write(access,privateDirectory,id,"client_cached_registry_access",fullEncodings);
        // Dedicated code never resolves a client-only class. This entrypoint is
        // invoked only by the already authorized native client QA action.
        if(net.neoforged.fml.ModList.get().isLoaded("lithostitched")){
            Class<?> hooks=Class.forName("worldfortwo.bridge.LithostitchedSeedgenClientHooks",false,
                WorldgenFingerprintDiagnostics.class.getClassLoader());
            hooks.getMethod("writeEffectiveDiagnostic",Path.class,String.class,RegistryAccess.Frozen.class).invoke(null,privateDirectory,id,access);
        }
        return receipt;
    }

    /** Parent wiring must pass the actual server.registryAccess(), not an exported approximation. */
    public static Path write(RegistryAccess access,Path privateDirectory,String id,String side,
        boolean fullEncodings)throws IOException {
        if(access==null)throw new IllegalArgumentException("Actual registry access is required");
        if(!id.matches("[a-z0-9][a-z0-9-]{0,63}"))throw new IllegalArgumentException("Unique diagnostic id required");
        if(!side.equals("client_cached_registry_access")&&!side.equals("server_registry_access"))
            throw new IllegalArgumentException("Exact diagnostic side required");
        verifyResource(SHARING_RESOURCE,SHARING_SHA);
        Path directory=privateDirectory.toAbsolutePath().normalize();
        requirePrivateDirectory(directory);
        requireSpace(directory);
        var ops=RegistryOps.create(JsonOps.INSTANCE,access);
        requireDiagnosticScope(ops);
        Path lines=directory.resolve(id+".worldgen.jsonl"),status=directory.resolve(id+".worldgen.status.json");
        if(Files.exists(lines,LinkOption.NOFOLLOW_LINKS)||Files.exists(status,LinkOption.NOFOLLOW_LINKS))
            throw new IOException("Refusing to replace an earlier diagnostic or failure receipt");
        JsonObject terminal=new JsonObject();
        terminal.addProperty("format","awft-worldgen-input-status:1");
        terminal.addProperty("at",Instant.now().toString());
        terminal.addProperty("side",side);
        terminal.addProperty("data_file",lines.getFileName().toString());
        terminal.addProperty("full_encodings",fullEncodings);
        terminal.addProperty("max_output_bytes",MAX_OUTPUT_BYTES);
        terminal.addProperty("native_fingerprint_method_or_cache_invoked",false);
        Accumulator counts=new Accumulator();
        // Acquire ownership before the guarded export; a CREATE_NEW failure must
        // not publish a status that claims someone else's existing data file.
        BoundedOutput out=new BoundedOutput(Files.newOutputStream(lines,StandardOpenOption.CREATE_NEW,StandardOpenOption.WRITE),MAX_OUTPUT_BYTES-STATUS_RESERVE);
        boolean complete=false;
        try {
            JsonObject header=new JsonObject();
            header.addProperty("record","header");header.addProperty("format","awft-seedgen-fingerprint-inputs:1");
            header.addProperty("side",side);header.addProperty("at",Instant.now().toString());
            header.addProperty("seedgen","0.9.1 for Minecraft1.21.1 NeoForge");
            header.addProperty("seedsharing_original_class_sha256",SHARING_SHA);
            header.addProperty("value_encoding","Native DIRECT_CODEC + RegistryOps(JsonOps, actual access); exact diagnostic-only transparent-root scope");
            header.addProperty("json_byte_order","JsonElement.toString() UTF-8, unchanged insertion order");
            header.addProperty("full_encodings",fullEncodings);
            line(out,header);
            keyOnly(access,Registries.BIOME,counts,out);
            keyOnly(access,Registries.PLACED_FEATURE,counts,out);
            keyOnly(access,Registries.NOISE,counts,out);
            keyOnly(access,Registries.MULTI_NOISE_BIOME_SOURCE_PARAMETER_LIST,counts,out);
            values(access,Registries.NOISE_SETTINGS,NoiseGeneratorSettings.DIRECT_CODEC,ops,fullEncodings,counts,out);
            values(access,Registries.DENSITY_FUNCTION,DensityFunction.DIRECT_CODEC,ops,fullEncodings,counts,out);
            complete=true;
        } catch(Exception|LinkageError failure) {
            terminal.add("export_failure",failure(failure));
        } finally {
            try{out.close();}catch(IOException closeFailure){complete=false;out.ioFailure=true;terminal.add("close_failure",failure(closeFailure));}
            terminal.addProperty("recorded_data_bytes",out.bytes);
            if(!out.ioFailure)terminal.addProperty("data_sha256",out.sha());
            else terminal.addProperty("data_hash_status","unavailable after output write/close failure; preserve the file as incomplete");
            terminal.addProperty("complete",complete);
            terminal.addProperty("entries",counts.entries);
            terminal.addProperty("encoded_values",counts.encoded);
            terminal.addProperty("native_encoding_errors",counts.errors);
            terminal.addProperty("native_encoding_exceptions",counts.exceptions);
            terminal.addProperty("elapsed_ms",(System.nanoTime()-counts.started)/1_000_000L);
            if(complete&&counts.exceptions==0){
                String whole=hex(counts.whole.digest());
                terminal.addProperty("diagnostic_input_sha256",whole);
                terminal.addProperty("diagnostic_native_format_prefix",whole.substring(0,16));
                terminal.addProperty("digest_coverage",counts.errors==0?"all native encoded inputs":"native key-only contribution retained for each unencodable value; failures preserved");
            } else terminal.addProperty("digest_coverage","incomplete; an exception would abort native computePrint");
            byte[] receipt=JSON.toJson(terminal).getBytes(StandardCharsets.UTF_8);
            if(receipt.length>STATUS_RESERVE)throw new IOException("Finite status receipt bound exceeded");
            Files.write(status,receipt,StandardOpenOption.CREATE_NEW,StandardOpenOption.WRITE);
        }
        return status;
    }

    /** This exact frame is the ONLY proposed extra guard scope; parent must review/wire it. */
    private static <T> DataResult<JsonElement> encodeFingerprintValue(Codec<T> codec,
        RegistryOps<JsonElement> ops,T value) {
        return codec.encodeStart(ops,value);
    }

    private static void requireDiagnosticScope(RegistryOps<JsonElement> ops) {
        DensityFunction value=DensityFunctions.constant(0.125);
        DensityFunction root=new DensityFunctions.HolderHolder(Holder.direct(value));
        var ordinary=encodeFingerprintValue(DensityFunction.DIRECT_CODEC,ops,value).result();
        var transparent=encodeFingerprintValue(DensityFunction.DIRECT_CODEC,ops,root).result();
        if(ordinary.isEmpty()||transparent.isEmpty()||!ordinary.get().equals(transparent.get()))
            throw new IllegalStateException("The reviewed diagnostic-only transparent-root codec scope is not installed; export refused");
    }

    @SuppressWarnings({"unchecked","rawtypes"})
    private static void keyOnly(RegistryAccess access,ResourceKey<? extends Registry<?>> key,
        Accumulator counts,BoundedOutput out)throws IOException {
        Registry<?> registry=(Registry<?>)access.registry((ResourceKey)key).orElse(null);
        String name=key.location().toString();
        var group=digest();
        JsonObject heading=group(name,"keys_only",registry!=null);line(out,heading);
        TreeSet<String> sorted=new TreeSet<>();
        if(registry!=null)for(var item:registry.registryKeySet()){
            checkKey(item.location().toString());
            if(sorted.size()>=MAX_ENTRIES)throw new IOException("Finite registry key count exceeded");
            sorted.add(item.location().toString());
        }
        for(String item:sorted){
            counts.next();byte[] keyBytes=item.getBytes(StandardCharsets.UTF_8);
            counts.whole.update(keyBytes);group.update(keyBytes);
            JsonObject row=entry(name,item,"key_only");
            row.addProperty("native_key_sha256",hash(keyBytes));line(out,row);
        }
        JsonObject end=group(name,"keys_only",registry!=null);end.addProperty("record","registry_summary");
        end.addProperty("entries",sorted.size());end.addProperty("native_contribution_sha256",hex(group.digest()));line(out,end);
    }

    private static <T> void values(RegistryAccess access,ResourceKey<? extends Registry<T>> key,
        Codec<T> codec,RegistryOps<JsonElement> ops,boolean full,Accumulator counts,BoundedOutput out)throws IOException {
        Registry<T> registry=access.registry(key).orElse(null);
        String name=key.location().toString();
        MessageDigest group=digest();int ok=0,errors=0,exceptions=0;
        line(out,group(name,"keys_and_native_values",registry!=null));
        TreeMap<String,T> sorted=new TreeMap<>();
        if(registry!=null)try(var holders=registry.holders()){
            var iterator=holders.iterator();
            while(iterator.hasNext()){
                var holder=iterator.next();String item=holder.key().location().toString();checkKey(item);
                if(sorted.size()>=MAX_ENTRIES)throw new IOException("Finite registry value count exceeded");
                sorted.put(item,holder.value());
            }
        }
        for(var item:sorted.entrySet()){
            counts.next();byte[] keyBytes=item.getKey().getBytes(StandardCharsets.UTF_8);
            counts.whole.update(keyBytes);group.update(keyBytes);
            JsonObject row=entry(name,item.getKey(),"pending");row.addProperty("native_key_sha256",hash(keyBytes));
            try {
                DataResult<JsonElement> result=encodeFingerprintValue(codec,ops,item.getValue());
                var encoded=result.result();
                if(result.error().isPresent())row.addProperty("native_error",boundedMessage(result.error().get().message()));
                if(encoded.isEmpty()){
                    row.addProperty("status","native_encoding_error");row.addProperty("value_hashed_by_native",false);
                    if(result.error().isEmpty())row.addProperty("native_error","no reason given");
                    errors++;counts.errors++;
                } else {
                    byte[] json=encoded.get().toString().getBytes(StandardCharsets.UTF_8);
                    if(json.length>MAX_JSON_BYTES)throw new OutputBound("Encoded value exceeds the finite per-entry diagnostic bound");
                    counts.whole.update(json);group.update(json);ok++;counts.encoded++;
                    row.addProperty("status","encoded");row.addProperty("value_bytes",json.length);
                    row.addProperty("value_sha256",hash(json));row.addProperty("value_hashed_by_native",true);
                    MessageDigest contribution=digest();contribution.update(keyBytes);contribution.update(json);
                    row.addProperty("native_entry_contribution_sha256",hex(contribution.digest()));
                    if(full)row.add("encoding",encoded.get());
                }
            } catch(OutputBound bound){throw bound;}
            catch(Exception|LinkageError failure){
                row.addProperty("status","native_encoding_exception");row.addProperty("native_compute_print_would_abort",true);
                row.add("exception",failure(failure));exceptions++;counts.exceptions++;
            }
            line(out,row);
        }
        JsonObject end=group(name,"keys_and_native_values",registry!=null);end.addProperty("record","registry_summary");
        end.addProperty("entries",sorted.size());end.addProperty("encoded",ok);end.addProperty("encoding_errors",errors);end.addProperty("exceptions",exceptions);
        if(exceptions==0)end.addProperty("native_contribution_sha256",hex(group.digest()));
        line(out,end);
    }

    private static JsonObject group(String name,String role,boolean present){JsonObject x=new JsonObject();x.addProperty("record","registry");x.addProperty("registry",name);x.addProperty("role",role);x.addProperty("present",present);return x;}
    private static JsonObject entry(String registry,String key,String status){JsonObject x=new JsonObject();x.addProperty("record","entry");x.addProperty("registry",registry);x.addProperty("key",key);x.addProperty("status",status);return x;}
    private static void line(BoundedOutput out,JsonObject value)throws IOException {out.write((JSON.toJson(value)+"\n").getBytes(StandardCharsets.UTF_8));}
    private static String boundedMessage(String value){return value.length()>8192?value.substring(0,8192)+" [diagnostic message truncated; sha256="+hash(value.getBytes(StandardCharsets.UTF_8))+"]":value;}
    private static JsonObject failure(Throwable value){JsonObject x=new JsonObject();x.addProperty("type",value.getClass().getName());x.addProperty("message",boundedMessage(String.valueOf(value.getMessage())));if(value.getCause()!=null){x.addProperty("cause_type",value.getCause().getClass().getName());x.addProperty("cause_message",boundedMessage(String.valueOf(value.getCause().getMessage())));}return x;}
    private static void checkKey(String key)throws IOException {if(key.length()>1024)throw new IOException("Finite registry id bound exceeded");}
    private static MessageDigest digest(){try{return MessageDigest.getInstance("SHA-256");}catch(NoSuchAlgorithmException impossible){throw new AssertionError(impossible);}}
    private static String hex(byte[] bytes){return HexFormat.of().formatHex(bytes);}
    private static String hash(byte[] bytes){return hex(digest().digest(bytes));}
    private static void verifyResource(String resource,String expected)throws IOException {
        try(InputStream in=WorldgenFingerprintDiagnostics.class.getClassLoader().getResourceAsStream(resource)){
            if(in==null)throw new IOException("Pinned SeedGen class resource unavailable");
            byte[] bytes=in.readNBytes(262145);
            if(bytes.length>262144||!expected.equals(hash(bytes)))throw new IOException("Pinned SeedGen class resource differs: "+resource);
        }
    }
    private static void requirePrivateDirectory(Path directory)throws IOException {
        if(!directory.isAbsolute()||!Files.isDirectory(directory,LinkOption.NOFOLLOW_LINKS))throw new IOException("An existing owned private output directory is required");
        for(Path part=directory;part!=null;part=part.getParent())if(Files.isSymbolicLink(part))throw new IOException("Diagnostic output must not traverse a symbolic link");
    }
    private static void requireSpace(Path directory)throws IOException {
        if(Files.getFileStore(directory).getUsableSpace()<HOST_RESERVE+MAX_OUTPUT_BYTES)throw new IOException("Diagnostic output would breach the host reserve");
        for(String drive:new String[]{"C:\\","D:\\"}){Path root=Path.of(drive);if(Files.exists(root)&&Files.getFileStore(root).getUsableSpace()<HOST_RESERVE)throw new IOException("Host reserve is unavailable on "+drive);}
    }
    private static final class Accumulator {
        final MessageDigest whole=digest();final long started=System.nanoTime();int entries,encoded,errors,exceptions;
        void next()throws IOException {if(++entries>MAX_ENTRIES)throw new IOException("Finite total entry count exceeded");if(System.nanoTime()-started>20_000_000_000L)throw new IOException("Diagnostic cooperative time bound exceeded between entries");}
    }
    private static final class OutputBound extends IOException {OutputBound(String message){super(message);}}
    private static final class BoundedOutput extends OutputStream {
        final OutputStream delegate;final long limit;final MessageDigest digest=digest();long bytes;boolean ioFailure;
        BoundedOutput(OutputStream delegate,long limit){this.delegate=delegate;this.limit=limit;}
        @Override public void write(int value)throws IOException {write(new byte[]{(byte)value});}
        @Override public void write(byte[] value,int offset,int length)throws IOException {if(length>limit-bytes)throw new OutputBound("Finite 16 MiB export bound reached; existing complete lines are preserved");try{delegate.write(value,offset,length);}catch(IOException failure){ioFailure=true;throw failure;}digest.update(value,offset,length);bytes+=length;}
        @Override public void close()throws IOException {delegate.close();}
        String sha(){return hex(digest.digest());}
    }
}
