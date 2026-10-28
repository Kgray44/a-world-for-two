package worldfortwo.bridge;

import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.ListTag;
import net.minecraft.world.level.ChunkPos;

/** Offline actual NBT API fixtures only. No Level, entities, fake player or world. */
public final class ReadyNbtProbe {
    private static int checks;
    private static CompoundTag full(){
        CompoundTag t=new CompoundTag();t.putInt("DataVersion",3955);t.putInt("xPos",68);t.putInt("zPos",-79);t.putString("Status","minecraft:full");t.putBoolean("isLightOn",true);
        ListTag sections=new ListTag();CompoundTag section=new CompoundTag();section.putByte("Y",(byte)4);sections.add(section);t.put("sections",sections);return t;
    }
    private static void refused(CompoundTag t){
        boolean failed=false;try{NativeChainRouteSupport.ReadyNbtFacts.validate(new ChunkPos(68,-79),t);}catch(IllegalStateException expected){failed=true;}
        if(!failed)throw new AssertionError("Uncertain persisted data was accepted");checks++;
    }
    public static void main(String[] args){
        var good=NativeChainRouteSupport.ReadyNbtFacts.validate(new ChunkPos(68,-79),full());
        if(!good.get("status").equals("minecraft:full")||!good.get("light_correct").equals(true))throw new AssertionError("Actual valid NBT facts differ");checks++;
        CompoundTag t=full();t.putString("Status","minecraft:light");refused(t);
        t=full();t.putInt("DataVersion",4903);refused(t);
        t=full();t.putInt("xPos",69);refused(t);
        t=full();t.remove("sections");refused(t);
        t=full();t.putBoolean("isLightOn",false);refused(t);
        t=full();t.put("below_zero_retrogen",new CompoundTag());refused(t);
        t=full();t.putByteArray("oversize_fixture",new byte[4*1024*1024]);refused(t);
        System.out.println("PASS actual NBT API fixtures="+checks+"; no world/Level/entities constructed");
    }
}
