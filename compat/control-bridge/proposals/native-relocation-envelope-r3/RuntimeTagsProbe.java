package worldfortwo.bridge;
import net.minecraft.nbt.*;

/** Real NBT classes and production derivation, no world/bootstrap. */
public final class RuntimeTagsProbe {
    private static void require(boolean yes,String reason){if(!yes)throw new AssertionError(reason);}
    private static void refuse(CompoundTag raw,CompoundTag actual){boolean no=false;try{NativeRelocationSupport.RuntimeTags.expected(raw,actual);}catch(IllegalStateException expected){no=true;}require(no,"Invalid storage/collision admitted");}
    public static void main(String[] args){
        CompoundTag raw=new CompoundTag();raw.putString("id","test:container");raw.putInt("x",1237);raw.putByte("keepPacked",(byte)0);raw.putLong("unknown_custom_value",7L);
        CompoundTag nested=new CompoundTag();nested.putByte("Slot",(byte)3);nested.putInt("count",4);raw.put("unrelated_nested_data",nested);
        CompoundTag actual=raw.copy();actual.remove("keepPacked");CompoundTag expected=NativeRelocationSupport.RuntimeTags.expected(raw,actual);
        require(expected.equals(actual)&&expected!=raw&&raw.contains("keepPacked",Tag.TAG_BYTE),"Raw authority mutated or runtime expectation changed");
        require(expected.get("unknown_custom_value").getId()==Tag.TAG_LONG&&expected.getCompound("unrelated_nested_data").get("Slot").getId()==Tag.TAG_BYTE,"Unrelated typed data normalized");
        CompoundTag x=raw.copy();x.putByte("keepPacked",(byte)1);refuse(x,actual);
        x=raw.copy();x.putInt("keepPacked",0);refuse(x,actual);
        x=raw.copy();x.putString("keepPacked","false");refuse(x,actual);
        x=actual.copy();x.putByte("keepPacked",(byte)0);refuse(raw,x);
        CompoundTag absent=actual.copy();require(NativeRelocationSupport.RuntimeTags.expected(absent,actual).equals(absent),"Absent field caused other filtering");
        CompoundTag different=actual.copy();different.putInt("unknown_custom_value",7);require(!NativeRelocationSupport.RuntimeTags.expected(raw,different).equals(different),"Unrelated typed mismatch hidden");
        System.out.println("PASS actual typed Bytefalse envelope only; immutable raw/unknown/nested widths; true/int/string/collision refusals; unrelated native mismatch retained; no world calls");
    }
}
