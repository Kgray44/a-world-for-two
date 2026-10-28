package worldfortwo.bridge;

import java.util.Map;

/** Pure admission rules shared by the proposed native helper and small probes. */
public final class HabitatLifePolicy {
    public record Species(String nativeClass,String category) {}
    public enum Existing { NEW, PRESERVE }
    public static final Map<String,Species> SPECIES=Map.of(
        "naturalist:deer",new Species("com.crispytwig.naturalist.world.entity.animal.deer.Deer","creature"),
        "naturalist:bird",new Species("com.crispytwig.naturalist.world.entity.animal.bird.Bird","creature"),
        "naturalist:butterfly",new Species("com.crispytwig.naturalist.world.entity.animal.butterfly.Butterfly","ambient"),
        "naturalist:firefly",new Species("com.crispytwig.naturalist.world.entity.animal.firefly.Firefly","ambient"));
    public static Species species(String id,String nativeClass,String category){
        Species value=SPECIES.get(id);
        if(value==null||!value.nativeClass.equals(nativeClass)||!value.category.equals(category))
            throw new IllegalStateException("Unreviewed species/class/category: "+id);
        return value;
    }
    public static Existing existing(boolean ledgerIntent,boolean loadedUUID,boolean exactIdentity){
        if(loadedUUID){
            if(!ledgerIntent||!exactIdentity)throw new IllegalStateException("Existing UUID is not an exact admitted resident; preserve it");
            return Existing.PRESERVE;
        }
        if(ledgerIntent)throw new IllegalStateException("Prior intent but UUID not loaded: interrupted or wandering resident; never duplicate");
        return Existing.NEW;
    }
    public static void live(boolean noAI,boolean passenger,boolean alive,boolean newborn,boolean tamed,boolean hasOwner){
        if(noAI||passenger||!alive)throw new IllegalStateException("Actual resident AI/life/passenger state is unsuitable");
        if(newborn&&(tamed||hasOwner))throw new IllegalStateException("New residents must retain ordinary untamed/unowned defaults");
        // Existing normal-gameplay ownership is observed, never overwritten.
    }
    public static void coordinate(double x,double y,double z){
        if(!Double.isFinite(x)||!Double.isFinite(y)||!Double.isFinite(z)||x<900||x>1536||z< -1536||z> -768||y<48||y>192)
            throw new IllegalStateException("Finite owned settlement habitat coordinates required");
    }
    private HabitatLifePolicy(){}
}
