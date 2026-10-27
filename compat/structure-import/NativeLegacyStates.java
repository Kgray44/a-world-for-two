package worldfortwo.structures;

import com.google.gson.*;
import com.mojang.serialization.JsonOps;
import net.minecraft.SharedConstants;
import net.minecraft.util.datafix.DataFixers;
import net.minecraft.util.datafix.fixes.BlockStateData;
import net.minecraft.util.datafix.fixes.References;
import java.nio.file.*;
import java.util.*;

/** Read-only original adapter to the pinned Minecraft migration APIs.
 * No server, world, mod loader, downloaded executable or entity is started.
 */
public final class NativeLegacyStates {
    public static void main(String[] args) throws Exception {
        if(args.length!=2)throw new IllegalArgumentException("Unique bounded input and output paths required");
        Path input=Path.of(args[0]),output=Path.of(args[1]);
        if(!Files.isRegularFile(input)||Files.size(input)>65536||Files.exists(output))
            throw new IllegalArgumentException("Bounded input and new output required");
        SharedConstants.tryDetectVersion();
        if(!SharedConstants.getCurrentVersion().getName().equals("1.21.1"))
            throw new IllegalStateException("Only the installed Minecraft 1.21.1 API is admitted");
        JsonArray values=JsonParser.parseString(Files.readString(input)).getAsJsonArray();
        if(values.isEmpty()||values.size()>4096)throw new IllegalArgumentException("Finite unique state set required");
        int current=SharedConstants.getCurrentVersion().getDataVersion().getVersion();
        JsonObject result=new JsonObject(),states=new JsonObject();Set<Integer> seen=new HashSet<>();
        for(JsonElement value:values){
            int encoded=value.getAsInt();
            if(encoded<0||encoded>65535||!seen.add(encoded))throw new IllegalArgumentException("Invalid or repeated legacy state");
            // The native flattening table already returns the 1.13 representation.
            // Continue the official block-state migration from that schema.
            var flattened=BlockStateData.getTag(encoded);
            var modern=DataFixers.getDataFixer().update(References.BLOCK_STATE,flattened,1451,current);
            JsonElement json=modern.convert(JsonOps.INSTANCE).getValue();
            if(!json.isJsonObject()||!json.getAsJsonObject().has("Name"))
                throw new IllegalStateException("Native conversion did not return a block state");
            if(encoded/16!=0&&json.getAsJsonObject().get("Name").getAsString().equals("minecraft:air"))
                throw new IllegalStateException("A non-air legacy state resolved to air");
            states.add(Integer.toString(encoded),json);
        }
        result.addProperty("minecraft","1.21.1");result.addProperty("data_version",current);
        result.addProperty("native_flattened_schema",1451);result.add("states",states);
        byte[] bytes=(new Gson().toJson(result)+"\n").getBytes(java.nio.charset.StandardCharsets.UTF_8);
        if(bytes.length>2*1024*1024)throw new IllegalStateException("Output exceeds finite bound");
        Files.write(output,bytes,StandardOpenOption.CREATE_NEW);
        System.out.println("Native Minecraft block-state conversion completed: "+seen.size()+" states; no world opened");
    }
}
