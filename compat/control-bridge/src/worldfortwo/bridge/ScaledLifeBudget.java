package worldfortwo.bridge;

import com.google.gson.*;
import java.util.*;

/** Explicit owner-authorized scale; legacy HabitatLifePolicy remains64.
 * No entity factory, world setter, ownership, profession or AI switch exists here.
 */
public final class ScaledLifeBudget {
    public static final int GLOBAL_MAXIMUM=4000,COHORT_MAXIMUM=64;
    private final JsonObject authority;
    private final Map<String,Integer> species,habitats;
    private final int ramp;

    public ScaledLifeBudget(JsonObject authority,JsonObject rampAuthority,String namespace,String curation,
            String checkpoint,String recipe,String budgetSha){
        this.authority=authority.deepCopy();
        if(!authority.get("format").getAsString().equals("awft-owner-scaled-life-budget:1")
            ||!authority.get("authorization_basis").getAsString().equals("EXPLICIT_OWNER_POPULATION_SCALE")
            ||!authority.get("population_namespace").getAsString().equals(namespace)
            ||!authority.get("curation_sha256").getAsString().equals(curation)
            ||integer(authority,"maximum_residents")!=GLOBAL_MAXIMUM
            ||integer(authority,"cohort_maximum")!=COHORT_MAXIMUM
            ||!flag(authority,"normal_native_AI_required")
            ||!flag(authority,"count_retained_intents_toward_global_budget")
            ||!authority.get("preserved_population_identity_sha256").getAsString().matches("[a-f0-9]{64}"))
            throw new IllegalStateException("Exact explicit4000/native-AI/64-cohort authority required");
        species=caps(authority.getAsJsonObject("per_species_caps"),GLOBAL_MAXIMUM);
        habitats=caps(authority.getAsJsonObject("per_32m_habitat_kind_caps"),256);
        if(!habitats.keySet().equals(Set.of("DRY","AIR","SHORE","WATER","HOME","MUSIC")))
            throw new IllegalStateException("Explicit per-habitat kind limits required");
        for(String id:species.keySet()){
            HabitatLifePolicy.Species selected=HabitatLifePolicy.SPECIES.get(id);
            if(selected==null||!selected.enabled())throw new IllegalStateException("Scale does not admit an unreviewed/disabled species: "+id);
        }
        if(!rampAuthority.get("format").getAsString().equals("awft-reviewed-life-population-ramp:1")
            ||!rampAuthority.get("checkpoint_sha256").getAsString().equals(checkpoint)
            ||!rampAuthority.get("recipe_sha256").getAsString().equals(recipe)
            ||!rampAuthority.get("population_budget_sha256").getAsString().equals(budgetSha))
            throw new IllegalStateException("Every cohort must bind its exact current staged-ramp review");
        ramp=integer(rampAuthority,"maximum_total_after_cohort");
        if(!Set.of(128,512,1024,2048,4000).contains(ramp))throw new IllegalStateException("Finite128/512/1024/2048/4000 population ramp required");
        if(ramp>128&&(!flag(rampAuthority,"native_AI_and_resource_measurements_reviewed")
            ||rampAuthority.getAsJsonArray("native_measurement_refs").isEmpty()))
            throw new IllegalStateException("Larger ramps need genuine native AI/resource measurement references; no synthetic benchmark claim");
    }
    private static int integer(JsonObject value,String key){return value.get(key).getAsBigDecimal().intValueExact();}
    private static boolean flag(JsonObject value,String key){return value.get(key).isJsonPrimitive()&&value.get(key).getAsJsonPrimitive().isBoolean()&&value.get(key).getAsBoolean();}
    private static Map<String,Integer> caps(JsonObject values,int maximum){
        Map<String,Integer> result=new TreeMap<>();
        if(values.size()<1||values.size()>32)throw new IllegalStateException("Finite explicit population limits required");
        values.asMap().forEach((key,value)->{int n=value.getAsBigDecimal().intValueExact();if(n<1||n>maximum)throw new IllegalStateException("Invalid population cap");result.put(key,n);});
        return Collections.unmodifiableMap(result);
    }
    public JsonObject identity(){return authority.deepCopy();}
    public String originalIdentitySha(){return authority.get("preserved_population_identity_sha256").getAsString();}
    public int ramp(){return ramp;}
    public int habitatCap(String kind){Integer cap=habitats.get(kind);if(cap==null)throw new IllegalStateException("Typed habitat kind required");return cap;}
    public static String habitat(String kind,double x,double z){
        if(!Set.of("DRY","AIR","SHORE","WATER","HOME","MUSIC").contains(kind)||!Double.isFinite(x)||!Double.isFinite(z)||Math.abs(x)>30000000||Math.abs(z)>30000000)
            throw new IllegalStateException("Typed finite actual habitat position required");
        return kind+"|"+Math.floorDiv((int)Math.floor(x),32)+"|"+Math.floorDiv((int)Math.floor(z),32);
    }
    public void check(Map<String,Integer> counts,Map<String,Integer> habitatCounts){
        int total=0;
        for(var row:counts.entrySet()){
            int n=row.getValue();Integer cap=species.get(row.getKey());
            if(n<0||cap==null||n>cap)throw new IllegalStateException("Explicit scaled per-species cap exceeded");
            total=Math.addExact(total,n);
        }
        if(total>GLOBAL_MAXIMUM||total>ramp)throw new IllegalStateException("Retained intents plus requested cohort exceed the explicit global/current-ramp budget");
        for(var row:habitatCounts.entrySet()){
            String[] p=row.getKey().split("\\|",-1);Integer limit=p.length==3?habitats.get(p[0]):null;
            if(limit==null||row.getValue()<0||row.getValue()>limit)throw new IllegalStateException("Actual32m habitat occupancy cap exceeded");
        }
    }
}
