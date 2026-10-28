package worldfortwo.bridge;

import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import net.minecraft.core.BlockPos;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.ListTag;
import net.minecraft.nbt.Tag;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.level.block.BeehiveBlock;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.BaseEntityBlock;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.entity.BlockEntityType;
import net.minecraft.world.level.block.entity.BeehiveBlockEntity;
import net.minecraft.world.level.block.state.BlockBehaviour;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.AABB;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.*;

/** ISOLATED proposal. Read-only audit around one existing synchronous native grow.
 * It never creates/edits/releases a bee, clears a hive, changes old inventories,
 * drops blocks, runs a tick, retries a variant or removes an existing entity.
 */
public final class TreeBeeAudit {
    private final ServerLevel level;
    private final Map<BlockPos,BlockState> before;
    private final AABB write;
    private final Map<UUID,String> entitiesBefore;
    private final Map<BlockPos,String> blockEntitiesBefore;
    private final boolean allowNativeNest;
    private static final int MAX_ENTITIES=8192;
    public TreeBeeAudit(ServerLevel level,Map<BlockPos,BlockState> before,AABB write,boolean allowNativeNest)throws Exception{
        this(level,before,write,allowNativeNest,false);
    }
    /** Dense patches may read/preserve existing BEs; scoped setters cannot touch
     * them and the complete exact before/after BE census must remain equal. */
    public TreeBeeAudit(ServerLevel level,Map<BlockPos,BlockState> before,AABB write,boolean allowNativeNest,boolean preserveExistingBEsInWrite)throws Exception{
        if(!level.getServer().isSameThread()||before.isEmpty()||before.size()>131072)throw new IllegalStateException("One exact synchronous known plot required");
        this.level=level;this.before=TreeGrowthScope.snapshotMap(before);this.write=write;this.allowNativeNest=allowNativeNest;
        pin(BeehiveBlock.class,"b2a511db000ff13ce4eaaf409d8b4157ea01af6c2df7da4e31f6e73002e89f48");
        pin(BeehiveBlockEntity.class,"153db1fec0f4f93b70bf11e544c07c57a592b3e0b6d6f2733f2dd7f264017faf");
        pin(BeehiveBlockEntity.Occupant.class,"57ab26140449c9468466f2ad84654bf389e118e383aea2f5f921837b2fd5bf1b");
        pin(Class.forName("net.minecraft.world.level.block.entity.BeehiveBlockEntity$BeeData",false,BeehiveBlockEntity.class.getClassLoader()),"740d1c8a29c12ca7bb553d2403a65a794056a67a157f585b80f7c76d0366fb3d");
        pin(BaseEntityBlock.class,"94825efc82ec63c95930ab4cda9218a630cca4f2e1dd77aef14473ee9d4ec072");
        pin(BlockBehaviour.class,"9d4b517d48afdaa2183e345ec25ae97efe0f0346b9f4add1de1dbb2f46d863b0");
        entitiesBefore=census();blockEntitiesBefore=blockEntities();
        for(BlockPos p:blockEntitiesBefore.keySet())if(inside(p)&&!preserveExistingBEsInWrite)throw new IllegalStateException("Preserve every old BE inside a growth field");
    }
    private static String sha(byte[] bytes)throws Exception{return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(bytes));}
    private static void pin(Class<?> type,String expected)throws Exception{
        String name=type.getName().substring(type.getName().lastIndexOf('.')+1)+".class";
        try(InputStream in=type.getResourceAsStream(name)){
            if(in==null)throw new IllegalStateException("Actual bee/removal class resource absent");byte[] bytes=in.readNBytes(128*1024+1);
            if(bytes.length>128*1024||!sha(bytes).equals(expected))throw new IllegalStateException("Pinned native bee/removal implementation differs: "+type.getName());
        }
    }
    private boolean inside(BlockPos p){return write.contains(p.getX()+.5,p.getY()+.5,p.getZ()+.5);}
    private Map<UUID,String> census(){
        if(!level.getServer().isSameThread())throw new IllegalStateException("Native census must remain on the server thread");
        Map<UUID,String> result=new TreeMap<>();
        for(Entity entity:level.getAllEntities()){
            String value=BuiltInRegistries.ENTITY_TYPE.getKey(entity.getType())+"|"+entity.getClass().getName()+"|"+entity.position()+"|"+entity.isRemoved();
            if(result.put(entity.getUUID(),value)!=null||result.size()>MAX_ENTITIES)throw new IllegalStateException("Duplicate/unbounded loaded native entity census");
        }
        return result;
    }
    private Map<BlockPos,String> blockEntities(){
        Map<BlockPos,String> values=new LinkedHashMap<>();
        for(BlockPos p:before.keySet()){
            BlockEntity be=level.getBlockEntity(p);if(be==null)continue;
            String text=be.saveWithFullMetadata(level.registryAccess()).toString();
            if(text.length()>65536||values.size()>=256)throw new IllegalStateException("Bounded native BE audit required");
            values.put(p.immutable(),text);
        }
        return values;
    }
    /** Called by the scoped setter before a desired BE state is first written. */
    public static void desired(BlockState original,BlockState desired,boolean allowNativeNest){
        if(desired.hasBlockEntity()&&(!allowNativeNest||!original.isAir()||desired.getBlock()!=Blocks.BEE_NEST
            ||desired.getValue(BeehiveBlock.HONEY_LEVEL)!=0))throw new IllegalStateException("Only qualified native bee-nest BE creation on original AIR is permitted");
    }
    public static boolean mayCreateNest(JsonObject descriptor){
        for(JsonElement entry:descriptor.getAsJsonObject("features").asMap().values()){
            JsonObject codec=entry.getAsJsonObject().getAsJsonObject("actual_codec");
            if(codec.get("type").getAsString().equals("regions_unexplored:sakura_tree"))return true;
            JsonObject config=codec.getAsJsonObject("config");
            if(config.has("decorators"))for(JsonElement decorator:config.getAsJsonArray("decorators"))
                if(decorator.getAsJsonObject().get("type").getAsString().equals("minecraft:beehive"))return true;
        }
        return false;
    }
    private List<Map<String,Object>> audit(Set<BlockPos> attempted,boolean complete)throws Exception{
        BeeNestFacts.census(entitiesBefore,census());Map<BlockPos,String> after=blockEntities();
        if(complete)for(BlockPos p:before.keySet())if(level.getBlockState(p).hasBlockEntity()&&!after.containsKey(p))
            throw new IllegalStateException("A native BE state lacks its actual entity; do not claim a completed hive");
        for(var old:blockEntitiesBefore.entrySet())if(!Objects.equals(old.getValue(),after.get(old.getKey())))throw new IllegalStateException("Preserve old native BE/inventory bytes");
        List<Map<String,Object>> nests=new ArrayList<>();
        for(var entry:after.entrySet())if(!blockEntitiesBefore.containsKey(entry.getKey())){
            BlockPos p=entry.getKey();BlockEntity actual=level.getBlockEntity(p);BlockState state=level.getBlockState(p);
            boolean exact=actual!=null&&actual.getClass()==BeehiveBlockEntity.class&&actual.getType()==BlockEntityType.BEEHIVE;
            BeeNestFacts.nest(allowNativeNest&&before.get(p).isAir(),inside(p)&&attempted.contains(p),state.getBlock()==Blocks.BEE_NEST,
                exact,state.hasProperty(BeehiveBlock.HONEY_LEVEL)?state.getValue(BeehiveBlock.HONEY_LEVEL):-1,
                exact&&((BeehiveBlockEntity)actual).isFireNearby(),nests.size()+1,complete);
            CompoundTag nbt=actual.saveWithFullMetadata(level.registryAccess());
            Set<String> allowed=Set.of("id","x","y","z","bees","components");
            if(!allowed.containsAll(nbt.getAllKeys())||!nbt.getString("id").equals("minecraft:beehive")
                ||nbt.getInt("x")!=p.getX()||nbt.getInt("y")!=p.getY()||nbt.getInt("z")!=p.getZ()
                ||nbt.contains("components")&&!nbt.getCompound("components").isEmpty())throw new IllegalStateException("Unexpected native bee-nest metadata/components");
            ListTag bees=nbt.getList("bees",Tag.TAG_COMPOUND);List<BeeNestFacts.Occupant> facts=new ArrayList<>();
            for(Tag item:bees){
                CompoundTag bee=(CompoundTag)item;
                if(!bee.getAllKeys().equals(Set.of("entity_data","ticks_in_hive","min_ticks_in_hive")))throw new IllegalStateException("Unexpected native occupant fields");
                CompoundTag data=bee.getCompound("entity_data");
                facts.add(new BeeNestFacts.Occupant(Set.copyOf(data.getAllKeys()),data.getString("id"),bee.getInt("ticks_in_hive"),bee.getInt("min_ticks_in_hive"),data.hasUUID("UUID")));
            }
            BeeNestFacts.occupants(facts,complete);
            if(((BeehiveBlockEntity)actual).getOccupantCount()!=facts.size())throw new IllegalStateException("Actual native stored count differs from codec readback");
            nests.add(Map.of("position",List.of(p.getX(),p.getY(),p.getZ()),"native_block","minecraft:bee_nest","native_BE_class",actual.getClass().getName(),
                "native_BE_sha256",sha(nbt.toString().getBytes(StandardCharsets.UTF_8)),"native_occupants",facts.size(),"native_occupant_UUIDs_present",0,
                "future_UUIDs","Native occupant.create records contain only entity id; real UUID is generated on later native release, not fabricated here"));
        }
        return List.copyOf(nests);
    }
    public Map<String,Object> success(Set<BlockPos> attempted)throws Exception{
        List<Map<String,Object>> nests=audit(attempted,true);int occupants=nests.stream().mapToInt(n->(Integer)n.get("native_occupants")).sum();
        return Map.of("native_new_nests",nests,"native_new_stored_bee_slots",occupants,"new_live_entity_UUIDs",List.of(),
            "loaded_entity_census_unchanged",true,"existing_native_BE_bytes_unchanged",true,"ordinary_bee_AI_release_and_restart_observed",false);
    }
    /** If an unknown BE or released live entity exists, refuse automatic removal. */
    public void beforeRollback(Set<BlockPos> attempted)throws Exception{audit(attempted,false);}
    /** Called inside restoration's try, before any clean-world latch is cleared. */
    public void restored(){
        BeeNestFacts.census(entitiesBefore,census());
        if(!blockEntitiesBefore.equals(blockEntities()))throw new IllegalStateException("Native hive removal left changed BE data; retain quarantine");
    }
}
