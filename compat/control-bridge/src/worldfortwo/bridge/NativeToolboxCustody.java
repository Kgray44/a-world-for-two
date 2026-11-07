package worldfortwo.bridge;

import com.google.gson.*;
import com.simibubi.create.content.equipment.toolbox.ToolboxBlock;
import com.simibubi.create.content.equipment.toolbox.ToolboxBlockEntity;
import com.simibubi.create.content.equipment.toolbox.ToolboxHandler;
import com.simibubi.create.content.equipment.toolbox.ToolboxInventory;
import java.io.*;
import java.lang.invoke.*;
import java.nio.file.*;
import java.security.MessageDigest;
import java.util.*;
import net.createmod.catnip.nbt.NBTHelper;
import net.minecraft.core.BlockPos;
import net.minecraft.nbt.*;
import net.minecraft.world.item.ItemStack;
import net.neoforged.neoforge.items.IItemHandler;
import net.neoforged.neoforge.items.ItemStackHandler;

/** Exact pinned Create6.0.10 role; no inventory/UUID/link writer or fake player. */
public final class NativeToolboxCustody {
    private static final VarHandle INVENTORY,CONNECTED,FILTERS,SETTLING,LIMITED;
    static {
        try {
            var be=MethodHandles.privateLookupIn(ToolboxBlockEntity.class,MethodHandles.lookup());
            var inv=MethodHandles.privateLookupIn(ToolboxInventory.class,MethodHandles.lookup());
            INVENTORY=be.findVarHandle(ToolboxBlockEntity.class,"inventory",ToolboxInventory.class);
            CONNECTED=be.findVarHandle(ToolboxBlockEntity.class,"connectedPlayers",Map.class);
            FILTERS=inv.findVarHandle(ToolboxInventory.class,"filters",List.class);
            SETTLING=inv.findVarHandle(ToolboxInventory.class,"settling",boolean.class);
            LIMITED=inv.findVarHandle(ToolboxInventory.class,"limitedMode",boolean.class);
        } catch(ReflectiveOperationException error){throw new ExceptionInInitializerError(error);}
    }
    @FunctionalInterface public interface StackEncoder {JsonObject encode(ItemStack stack)throws Exception;}
    private static String sha(byte[] raw)throws Exception{return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(raw));}
    private static String classHash(Class<?> c)throws Exception{
        try(InputStream in=c.getResourceAsStream("/"+c.getName().replace('.','/')+".class")){
            if(in==null)throw new IllegalStateException("Toolbox API bytes unavailable");byte[] raw=in.readNBytes(262145);
            if(raw.length==0||raw.length>262144)throw new IllegalStateException("Bounded toolbox API bytes");return sha(raw);
        }
    }
    public static void pins(JsonObject expected)throws Exception{
        List<Class<?>> classes=List.of(ToolboxBlockEntity.class,ToolboxInventory.class,ToolboxBlock.class,ToolboxHandler.class,ItemStackHandler.class,IItemHandler.class,NBTHelper.class);
        if(expected==null||expected.size()!=classes.size())throw new IllegalStateException("Complete exact toolbox native API pins required");
        for(Class<?> c:classes)if(!expected.has(c.getName())||!classHash(c).equals(expected.get(c.getName()).getAsString()))throw new IllegalStateException("Pinned native toolbox API differs: "+c.getName());
    }
    public static JsonObject capture(ToolboxBlockEntity be,StackEncoder encode)throws Exception{
        if(be.getClass()!=ToolboxBlockEntity.class||!be.isFullyInitialized()||be.getUniqueId()==null)
            throw new IllegalStateException("Already initialized native toolbox UUID required BEFORE save; never create one");
        Object value=INVENTORY.get(be);
        if(value==null||value.getClass()!=ToolboxInventory.class||!(value instanceof IItemHandler handler)||handler.getSlots()!=32)
            throw new IllegalStateException("Actual pinned32-slot native handler required");
        ToolboxInventory inventory=(ToolboxInventory)value;
        if((boolean)SETTLING.get(inventory)||(boolean)LIMITED.get(inventory))throw new IllegalStateException("Toolbox inventory has transient active operation; no settle/normalization");
        Object links=CONNECTED.get(be);
        if(!(links instanceof Map<?,?> map)||map.size()>8)throw new IllegalStateException("Bounded native toolbox connection map");
        for(var e:map.entrySet()){
            if(!(e.getKey() instanceof Integer i)||i<0||i>=8||!(e.getValue() instanceof WeakHashMap<?,?> players)||!players.isEmpty())
                throw new IllegalStateException("Actual linked players retained; normal unlink workflow required");
        }
        Object rawFilters=FILTERS.get(inventory);
        if(!(rawFilters instanceof List<?> filters)||filters.size()!=8)throw new IllegalStateException("Exact native eight filters required; never repair");
        JsonArray slots=new JsonArray(),filterRows=new JsonArray();
        for(int i=0;i<handler.getSlots();i++)slots.add(encode.encode(handler.getStackInSlot(i)));
        for(Object filter:filters){if(!(filter instanceof ItemStack item))throw new IllegalStateException("Actual native ItemStack filter required");filterRows.add(encode.encode(item));}
        JsonObject row=new JsonObject();row.addProperty("handler_class",value.getClass().getName());row.addProperty("native_slots",handler.getSlots());
        row.add("all_slots",slots);row.add("all_filters",filterRows);row.addProperty("UniqueId",be.getUniqueId().toString());row.addProperty("native_connected_players",0);
        row.addProperty("settling",false);row.addProperty("limitedMode",false);return row;
    }
    private static void checkLinks(Tag value,Set<BlockPos> forbidden,int depth,int[] count){
        if(depth>64||++count[0]>300000)throw new IllegalStateException("Bounded complete current player NBT tree");
        if(value instanceof CompoundTag compound){
            for(String key:compound.getAllKeys()){
                Tag child=compound.get(key);
                if(key.equals("CreateToolboxData")){
                    if(!(child instanceof CompoundTag table))throw new IllegalStateException("Unknown native saved toolbox table type");
                    for(String slot:table.getAllKeys()){
                        if(!(table.get(slot) instanceof CompoundTag entry)||!entry.contains("Pos"))throw new IllegalStateException("Unknown actual saved toolbox link shape");
                        Tag pos=entry.get("Pos");
                        if(!(pos instanceof IntArrayTag a&&a.getAsIntArray().length==3)&&!(pos instanceof CompoundTag p&&p.contains("X",Tag.TAG_INT)&&p.contains("Y",Tag.TAG_INT)&&p.contains("Z",Tag.TAG_INT)))
                            throw new IllegalStateException("Unknown pinned saved native toolbox position");
                        if(forbidden.contains(NBTHelper.readBlockPos(entry,"Pos")))throw new IllegalStateException("Saved player link targets source/destination toolbox; no rewrite or fake player");
                    }
                }
                if(child!=null)checkLinks(child,forbidden,depth+1,count);
            }
        }else if(value instanceof ListTag list)for(Tag child:list)checkLinks(child,forbidden,depth+1,count);
    }
    public static void profiles(Path world,JsonObject audit,String checkpoint,BlockPos source,BlockPos destination)throws Exception{
        if(!audit.get("format").getAsString().equals("awft-toolbox-saved-player-custody:1")||!audit.get("checkpoint_sha256").getAsString().equals(checkpoint)
            ||!audit.get("actual_full_typed_source_unchanged").getAsBoolean()||!audit.get("native_initialized_UUID_already_saved").getAsBoolean()
            ||!audit.get("eight_native_saved_filters").getAsBoolean()||audit.get("matching_saved_links").getAsInt()!=0)
            throw new IllegalStateException("Exact current saved toolbox/profile custody required");
        JsonArray point=audit.getAsJsonArray("toolbox_source_position");
        if(point==null||point.size()!=3||point.get(0).getAsInt()!=source.getX()||point.get(1).getAsInt()!=source.getY()||point.get(2).getAsInt()!=source.getZ()
            ||!audit.get("source_catalog_sha256").getAsString().equals("db5e0fa730575ad9b0fd166dd4d52273a5105832d66636d1ca3098693199adf7"))
            throw new IllegalStateException("Exact initialized source toolbox capture lineage required");
        JsonArray profiles=audit.getAsJsonArray("current_player_profiles");if(profiles.size()<1||profiles.size()>16)throw new IllegalStateException("Complete bounded current profile set");
        Path dir=world.resolve("playerdata");if(Files.isSymbolicLink(dir)||!dir.toRealPath().equals(dir))throw new IllegalStateException("Actual owned current player directory required");
        Map<String,JsonObject> expected=new HashMap<>();
        for(JsonElement e:profiles){JsonObject p=e.getAsJsonObject();String name=p.get("file_name").getAsString();
            if(!name.matches("[a-f0-9-]{36}\\.dat")||expected.put(name,p)!=null)throw new IllegalStateException("Exact unique native profile filenames required");}
        Set<String> found=new HashSet<>();long total=0;
        try(DirectoryStream<Path> stream=Files.newDirectoryStream(dir,"*.dat")){
            for(Path p:stream){String name=p.getFileName().toString();JsonObject proof=expected.get(name);
                if(found.size()>=16||proof==null||!found.add(name)||Files.isSymbolicLink(p)||!Files.isRegularFile(p,LinkOption.NOFOLLOW_LINKS)||!p.toRealPath().equals(p))
                    throw new IllegalStateException("Current profile set changed; preserve actual players");
                if(Files.size(p)<1||Files.size(p)>1048576)throw new IllegalStateException("Bounded actual native profile file");
                byte[] raw;try(InputStream in=Files.newInputStream(p)){raw=in.readNBytes(1048577);}
                total+=raw.length;if(raw.length!=proof.get("bytes").getAsInt()||total>8388608||!sha(raw).equals(proof.get("sha256").getAsString()))
                    throw new IllegalStateException("Actual current saved player bytes differ from authenticated snapshot");
                CompoundTag player=NbtIo.readCompressed(new ByteArrayInputStream(raw),NbtAccounter.create(4194304L));
                checkLinks(player,Set.of(source,destination),0,new int[1]);
            }
        }
        if(!found.equals(expected.keySet()))throw new IllegalStateException("Saved profile census incomplete");
    }
}
