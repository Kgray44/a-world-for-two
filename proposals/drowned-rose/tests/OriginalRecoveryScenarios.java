package worldfortwo.tavern;

import java.nio.file.*;
import java.util.*;
import net.minecraft.nbt.*;
import com.google.gson.*;

/** Native NBT/file/profile/absence gates on four exact authorized repairs; no world. */
public final class OriginalRecoveryScenarios {
    interface Attempt{void run()throws Exception;}
    static void refused(Attempt a,String reason)throws Exception{
        try{a.run();throw new AssertionError("Expected refusal:"+reason);}catch(IllegalStateException e){if(!e.getMessage().equals(reason))throw e;}
    }
    public static void main(String[] args)throws Exception{
        Path originals=Path.of(args[0]),temp=Files.createTempDirectory("awft-original-two-");
        try{
            for(var source:OriginalRecovery.SOURCES.values()){
                OriginalRecovery.source(source.uuid().toString(),source.sha256());
                Path sourceFile=originals.resolve(source.uuid()+".nbt");if(!Files.exists(sourceFile))sourceFile=Path.of(args[1]).resolve(source.uuid()+".nbt");
                Path f=temp.resolve(source.sha256()+".nbt");Files.copy(sourceFile,f);
                CompoundTag tag=OriginalRecovery.read(temp,source);
                if(!tag.getUUID("UUID").equals(source.uuid()))throw new AssertionError("Original UUID changed");
                CompoundTag bad=tag.copy();bad.putString("id","minecraft:villager");refused(()->OriginalRecovery.validate(bad,source),"original_entity_type_mismatch");
                CompoundTag wrong=tag.copy();wrong.putUUID("UUID",UUID.randomUUID());refused(()->OriginalRecovery.validate(wrong,source),"original_uuid_mismatch");
                CompoundTag unnamed=tag.copy();unnamed.putString("CustomName","\"Someone else\"");refused(()->OriginalRecovery.validate(unnamed,source),"original_name_mismatch");
                CompoundTag untagged=tag.copy();untagged.remove("Tags");refused(()->OriginalRecovery.validate(untagged,source),"original_resident_tag_missing");
                CompoundTag passenger=tag.copy();passenger.put("Passengers",new ListTag());refused(()->OriginalRecovery.validate(passenger,source),"original_must_be_single_entity");
                Files.write(f,new byte[8193]);refused(()->OriginalRecovery.read(temp,source),"original_file_exceeds_8kib");
                Files.write(f,new byte[]{1});refused(()->OriginalRecovery.read(temp,source),"original_file_hash_changed");Files.delete(f);
            }
            String uuid="8dfc2201-e604-367f-9e34-f2577927b13f",sha=OriginalRecovery.SOURCES.get(UUID.fromString(uuid)).sha256();
            refused(()->OriginalRecovery.source("../../payload",sha),"invalid_uuid_or_sha_format");
            refused(()->OriginalRecovery.source(UUID.randomUUID().toString(),sha),"not_one_of_three_originals");
            refused(()->OriginalRecovery.source(uuid,"0".repeat(64)),"original_source_hash_mismatch");
            JsonObject profile=JsonParser.parseString(Files.readString(Path.of(args[2]))).getAsJsonObject();
            OriginalRecovery.profile(OriginalRecovery.NIAMH.toString(),OriginalRecovery.NIAMH_PROFILE_SHA,profile);
            refused(()->OriginalRecovery.profile(uuid,OriginalRecovery.NIAMH_PROFILE_SHA,profile),"not_pinned_niamh_profile_repair");
            JsonObject changed=profile.deepCopy();changed.addProperty("personality","changed");
            refused(()->OriginalRecovery.profile(OriginalRecovery.NIAMH.toString(),OriginalRecovery.NIAMH_PROFILE_SHA,changed),"original_niamh_profile_changed");
            Path census=temp.resolve("336ba5-census.json");Files.copy(Path.of(args[3]),census);
            for(UUID id:OriginalRecovery.SOURCES.keySet())OriginalRecovery.proveAbsent(temp,id);
            OriginalRecovery.proveAbsent(temp,OriginalRecovery.NIAMH);
            refused(()->OriginalRecovery.proveAbsent(temp,UUID.randomUUID()),"not_one_of_four_authorized_repairs");
            Files.writeString(census,"{}");refused(()->OriginalRecovery.proveAbsent(temp,OriginalRecovery.NIAMH),"pinned_absence_proof_changed");
            System.out.println("PASS:3 exact original NBTs,1 pinned Niamh profile and pinned336ba5 absence accepted; altered UUID/hash/path/NBT/profile/proof, passengers and oversized files refused. No world inserted.");
        }finally{try(var files=Files.list(temp)){for(Path f:files.toList())Files.deleteIfExists(f);}Files.delete(temp);}
    }
}
