package worldfortwo.bridge;

import java.util.*;
import java.util.concurrent.CompletableFuture;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.ListTag;
import net.minecraft.world.level.ChunkPos;

/** Offline pure transaction boundaries; no synthetic Level or tree generator. */
public final class DensePatchTransactionProbe {
    public static void main(String[] args) {
        int permitted=0;
        for(int bits=0;bits<512;bits++){
            boolean[] v=new boolean[9];for(int b=0;b<9;b++)v[b]=(bits&(1<<b))!=0;
            boolean allowed=TreeGrowthScope.foliageOverlap(v[0],v[1],v[2],v[3],v[4],v[5],v[6],v[7],v[8]);
            if(allowed){permitted++;if(bits!=35)throw new AssertionError("Log/BE/fluid or unapproved overlap accepted: "+bits);}
        }
        if(permitted!=1)throw new AssertionError("Exact native leaves-only overlap missing");
        var nbt=new CompoundTag();nbt.putInt("DataVersion",3955);nbt.putInt("xPos",5);nbt.putInt("zPos",-7);
        nbt.putString("Status","minecraft:full");nbt.putBoolean("isLightOn",true);
        var sections=new ListTag();var section=new CompoundTag();section.putByte("Y",(byte)0);sections.add(section);nbt.put("sections",sections);
        NativeTreePatchReadiness.validate(new ChunkPos(5,-7),nbt);
        for(String broken:List.of("version","coordinates","status","lighting","retrogen","sections")){
            var invalid=nbt.copy();switch(broken){
                case "version"->invalid.putInt("DataVersion",0);case "coordinates"->invalid.putInt("xPos",6);
                case "status"->invalid.putString("Status","minecraft:noise");case "lighting"->invalid.putBoolean("isLightOn",false);
                case "retrogen"->invalid.put("below_zero_retrogen",new CompoundTag());case "sections"->invalid.put("sections",new ListTag());
            }
            try{NativeTreePatchReadiness.validate(new ChunkPos(5,-7),invalid);throw new AssertionError("Unknown storage accepted: "+broken);}
            catch(IllegalStateException expected){}
        }
        var io=new HashMap<String,CompletableFuture<String>>();var future=new CompletableFuture<String>();io.put("owned-read",future);
        if(NativeTreePatchReadiness.drainCompleted(io)||io.size()!=1)throw new AssertionError("Unfinished storage future abandoned");
        future.completeExceptionally(new IllegalStateException("owned IO refusal"));
        if(!NativeTreePatchReadiness.drainCompleted(io)||!io.isEmpty())throw new AssertionError("Completed failed IO leaked");
        var before=new LinkedHashMap<String,String>();
        before.put("root","grass");before.put("old-leaf","birch-leaf");before.put("old-trunk","birch-log");
        var current=new HashMap<>(before);
        PreMutationFieldCheck.requireUnchanged(before,current::get,d->{throw new AssertionError("unexpected drift");});
        current.put("old-leaf","new-native-leaf");boolean[] rejected={false};
        try{PreMutationFieldCheck.requireUnchanged(before,current::get,d->{rejected[0]=d.position().equals("old-leaf")&&d.expected().equals("birch-leaf");});throw new AssertionError("drift accepted");}
        catch(PreMutationFieldCheck.DriftDetected expected){if(!rejected[0])throw new AssertionError("typed drift missing");}
        var failures=new ArrayList<String>();
        var restored=TreeGrowthScope.captureThenRestore(()->{failures.add("capture");throw new IllegalStateException("broken archive");},()->failures.add("exact-restore"));
        if(!restored.exactRestored()||restored.captureFailure()==null||!failures.equals(List.of("capture","exact-restore")))throw new AssertionError("capture failure skipped rollback");
        var uncertain=TreeGrowthScope.captureThenRestore(()->{},()->{throw new IllegalStateException("BE changed");});
        if(uncertain.exactRestored()||uncertain.restoreFailure()==null)throw new AssertionError("uncertain recovery accepted");
        System.out.println("PASS512 foliage boundary combinations; persisted NBT/version/coordinate/status/light/retrogen/section refusals; pending IO cleanup; typed full-field drift and failed-capture/restore boundaries. Offline pure helpers only; no native tree, loaded-tag, density or world acceptance.");
    }
}
