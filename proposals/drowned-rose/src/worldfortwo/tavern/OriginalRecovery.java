package worldfortwo.tavern;

import com.google.gson.*;
import java.io.ByteArrayInputStream;
import java.nio.file.*;
import java.security.MessageDigest;
import java.util.*;
import net.minecraft.nbt.*;

/** Three authenticated originals and one explicit profile repair; no general import. */
final class OriginalRecovery {
    static final UUID NIAMH=UUID.fromString("62622710-89e4-3007-82c1-4693b3818539");
    static final String NIAMH_PROFILE_SHA="3a6f083faf2ac1147b4c8e504ff4e61fe12983bbd1415107b8335c06350ae474";
    static final String ABSENCE_SHA="2f01c704298f5e0d37e057134526eb6a2c70ade6b830ffb4e2543b4ae1af0e90";
    record Source(UUID uuid,String name,String sha256){}
    static final Map<UUID,Source> SOURCES=Map.of(
        UUID.fromString("8dfc2201-e604-367f-9e34-f2577927b13f"),new Source(UUID.fromString("8dfc2201-e604-367f-9e34-f2577927b13f"),"Oona Kelp","b07c3d8c8082d59e1e6db8adb6288a88ef2fdc6db7687f6aa4095c6c8b0259e4"),
        UUID.fromString("4a494cee-f2c4-3b5c-aa06-e52b2e4bb447"),new Source(UUID.fromString("4a494cee-f2c4-3b5c-aa06-e52b2e4bb447"),"Dara Moss","b3149fb9adbbaf3fdff7d6ad18068ccc84c2f4ddc6c6e9d31d29995955964ead"),
        UUID.fromString("0ac83eb9-fa42-351e-b72a-136affeef0ba"),new Source(UUID.fromString("0ac83eb9-fa42-351e-b72a-136affeef0ba"),"Rhea Hook","95e40d2326c8f72b4383f7c015f6a274f2b54581ac859f1940c92adf07c2b87f"));

    static Source source(String uuid,String sha){
        if(!uuid.matches("[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")||!sha.matches("[0-9a-f]{64}"))
            throw new IllegalStateException("invalid_uuid_or_sha_format");
        Source source=SOURCES.get(UUID.fromString(uuid));
        if(source==null)throw new IllegalStateException("not_one_of_three_originals");
        if(!source.sha256().equals(sha))throw new IllegalStateException("original_source_hash_mismatch");
        return source;
    }
    static CompoundTag read(Path directory,Source source)throws Exception{
        Path dir=directory.toAbsolutePath().normalize();
        if(!Files.isDirectory(dir,LinkOption.NOFOLLOW_LINKS)||Files.isSymbolicLink(dir))throw new IllegalStateException("recovery_directory_missing_or_linked");
        Path file=dir.resolve(source.sha256()+".nbt");
        if(!Files.isRegularFile(file,LinkOption.NOFOLLOW_LINKS)||Files.isSymbolicLink(file)||!file.toRealPath().getParent().equals(dir.toRealPath()))
            throw new IllegalStateException("original_file_missing_or_linked");
        byte[] bytes;try(var in=Files.newInputStream(file)){bytes=in.readNBytes(8193);}
        if(bytes.length==0||bytes.length>8192)throw new IllegalStateException("original_file_exceeds_8kib");
        String actual=HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(bytes));
        if(!actual.equals(source.sha256()))throw new IllegalStateException("original_file_hash_changed");
        CompoundTag tag=NbtIo.readCompressed(new ByteArrayInputStream(bytes),NbtAccounter.create(65536));
        validate(tag,source);return tag;
    }
    static void proveAbsent(Path directory,UUID uuid)throws Exception{
        if(!SOURCES.containsKey(uuid)&&!NIAMH.equals(uuid))throw new IllegalStateException("not_one_of_four_authorized_repairs");
        Path dir=directory.toAbsolutePath().normalize(),file=dir.resolve("336ba5-census.json");
        if(!Files.isDirectory(dir,LinkOption.NOFOLLOW_LINKS)||Files.isSymbolicLink(dir)||!Files.isRegularFile(file,LinkOption.NOFOLLOW_LINKS)||Files.isSymbolicLink(file)||!file.toRealPath().getParent().equals(dir.toRealPath()))
            throw new IllegalStateException("pinned_absence_proof_missing_or_linked");
        byte[] bytes;try(var in=Files.newInputStream(file)){bytes=in.readNBytes(65537);}
        if(bytes.length>65536||!HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(bytes)).equals(ABSENCE_SHA))throw new IllegalStateException("pinned_absence_proof_changed");
        JsonObject proof=JsonParser.parseString(new String(bytes,java.nio.charset.StandardCharsets.UTF_8)).getAsJsonObject();
        boolean absent=false;for(JsonElement row:proof.getAsJsonArray("missing_tavern"))if(row.getAsJsonObject().get("uuid").getAsString().equals(uuid.toString()))absent=true;
        if(!absent||!proof.get("checkpoint_sha256").getAsString().equals("cdeaff96b090dfa559ff05e1712c69850d9764f3c6271f58f0b40cdf378a9e46"))throw new IllegalStateException("original_not_proven_absent_in336ba5");
    }
    static void profile(String uuid,String sha,JsonObject profile)throws Exception{
        if(!NIAMH.toString().equals(uuid)||!NIAMH_PROFILE_SHA.equals(sha))throw new IllegalStateException("not_pinned_niamh_profile_repair");
        if(!profile.get("id").getAsString().equals("niamh-wick")||!profile.get("name").getAsString().equals("Niamh Wick")||!profile.get("uuid").getAsString().equals(uuid)||
            !HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(profile.toString().getBytes(java.nio.charset.StandardCharsets.UTF_8))).equals(sha))
            throw new IllegalStateException("original_niamh_profile_changed");
    }
    static void validate(CompoundTag tag,Source source){
        if(!tag.getString("id").equals("easy_npc:humanoid"))throw new IllegalStateException("original_entity_type_mismatch");
        if(!tag.hasUUID("UUID")||!source.uuid().equals(tag.getUUID("UUID")))throw new IllegalStateException("original_uuid_mismatch");
        if(!tag.getString("CustomName").equals(new JsonPrimitive(source.name()).toString()))throw new IllegalStateException("original_name_mismatch");
        if(!tag.getList("Tags",8).contains(StringTag.valueOf("awft_drowned_rose")))throw new IllegalStateException("original_resident_tag_missing");
        if(tag.contains("Passengers"))throw new IllegalStateException("original_must_be_single_entity");
        if(!tag.getBoolean("PersistenceRequired")||tag.getBoolean("NoAI"))throw new IllegalStateException("original_persistence_or_ai_mismatch");
        ListTag pos=tag.getList("Pos",6);
        if(pos.size()!=3||!Double.isFinite(pos.getDouble(0))||!Double.isFinite(pos.getDouble(1))||!Double.isFinite(pos.getDouble(2))||
            !ActivityPolicy.insideTavernFootprint(pos.getDouble(0),pos.getDouble(2))||pos.getDouble(1)<65||pos.getDouble(1)>70)
            throw new IllegalStateException("original_position_outside_admitted_interior");
    }
}
