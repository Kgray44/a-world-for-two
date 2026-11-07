package worldfortwo.bridge;

import com.google.gson.*;
import java.nio.file.*;
import java.security.MessageDigest;
import java.util.*;
import net.minecraft.core.BlockPos;
import net.minecraft.nbt.*;

/** Actual pinned private handles + real NBT/player-file read gates, no entity. */
public final class ToolboxCustodyProbe {
    private static int assertions;
    private static final String CHECKPOINT="fixture-checkpoint";
    private static String sha(byte[] b)throws Exception{return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(b));}
    private static JsonObject audit(Path file)throws Exception{
        JsonObject a=new JsonObject();a.addProperty("format","awft-toolbox-saved-player-custody:1");a.addProperty("checkpoint_sha256",CHECKPOINT);
        a.addProperty("actual_full_typed_source_unchanged",true);a.addProperty("native_initialized_UUID_already_saved",true);a.addProperty("eight_native_saved_filters",true);a.addProperty("matching_saved_links",0);
        JsonArray point=new JsonArray();point.add(1);point.add(2);point.add(3);a.add("toolbox_source_position",point);a.addProperty("source_catalog_sha256","db5e0fa730575ad9b0fd166dd4d52273a5105832d66636d1ca3098693199adf7");
        JsonObject p=new JsonObject();p.addProperty("file_name",file.getFileName().toString());byte[] raw=Files.readAllBytes(file);p.addProperty("bytes",raw.length);p.addProperty("sha256",sha(raw));
        JsonArray rows=new JsonArray();rows.add(p);a.add("current_player_profiles",rows);return a;
    }
    @FunctionalInterface private interface Action{void run()throws Exception;}
    private static void refused(Action action)throws Exception{try{action.run();throw new AssertionError("Unexpected admission");}catch(IllegalStateException expected){assertions++;}}
    private static void verify(Path root,JsonObject a)throws Exception{NativeToolboxCustody.profiles(root,a,CHECKPOINT,new BlockPos(1,2,3),new BlockPos(4,5,6));}
    private static void write(Path file,boolean linked,int[] position)throws Exception{
        CompoundTag doc=new CompoundTag();doc.putString("fixture_role","Original offline probe only; no account/world installation");
        if(linked){CompoundTag table=new CompoundTag(),entry=new CompoundTag(),persistent=new CompoundTag();entry.putIntArray("Pos",position);entry.putInt("Slot",0);table.put("0",entry);persistent.put("CreateToolboxData",table);doc.put("NeoForgeData",persistent);}
        NbtIo.writeCompressed(doc,file);
    }
    public static void main(String[] args)throws Exception{
        if(args.length!=1)throw new IllegalArgumentException("Fresh owned fixture directory only");
        Path root=Path.of(args[0]).toAbsolutePath().normalize();Files.createDirectory(root);Path dir=Files.createDirectory(root.resolve("playerdata"));Path file=dir.resolve("00000000-0000-0000-0000-000000000001.dat");
        Class.forName("worldfortwo.bridge.NativeToolboxCustody",true,ToolboxCustodyProbe.class.getClassLoader());assertions++;
        write(file,false,null);JsonObject good=audit(file);verify(root,good);assertions++;
        JsonObject changed=good.deepCopy();changed.getAsJsonArray("current_player_profiles").get(0).getAsJsonObject().addProperty("sha256","wrong");refused(()->verify(root,changed));
        Path extra=dir.resolve("00000000-0000-0000-0000-000000000002.dat");Files.copy(file,extra);refused(()->verify(root,good));Files.delete(extra);
        write(file,true,new int[]{1,2,3});JsonObject linkedSource=audit(file);refused(()->verify(root,linkedSource));
        write(file,true,new int[]{4,5,6});JsonObject linkedDestination=audit(file);refused(()->verify(root,linkedDestination));
        write(file,true,new int[]{7,8,9});verify(root,audit(file));assertions++;
        JsonObject missing=audit(file);missing.addProperty("checkpoint_sha256","foreign");refused(()->verify(root,missing));
        System.out.println("PASS exact pinned typed private handles and "+assertions+" real native NBT/profile custody assertions; no Minecraft world/entity/inventory constructed");
    }
}
