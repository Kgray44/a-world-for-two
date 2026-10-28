package worldfortwo.bridge;

import com.google.gson.*;
import java.util.*;

/** Pure synthetic quota fixtures; creates no measurement, entity, Level or authority. */
public final class LifeScaleBudgetProbe {
    private static JsonObject authority(){
        JsonObject a=new JsonObject();a.addProperty("format","awft-owner-scaled-life-budget:1");
        a.addProperty("authorization_basis","EXPLICIT_OWNER_POPULATION_SCALE");a.addProperty("population_namespace","fixture-only");
        a.addProperty("curation_sha256",HabitatLifePolicy.CURATION_SHA256);a.addProperty("maximum_residents",4000);a.addProperty("cohort_maximum",64);
        a.addProperty("normal_native_AI_required",true);a.addProperty("count_retained_intents_toward_global_budget",true);
        a.addProperty("preserved_population_identity_sha256","0".repeat(64));
        JsonObject species=new JsonObject();species.addProperty("naturalist:bird",4000);a.add("per_species_caps",species);
        JsonObject kinds=new JsonObject();for(String kind:List.of("DRY","AIR","SHORE","WATER","HOME","MUSIC"))kinds.addProperty(kind,256);a.add("per_32m_habitat_kind_caps",kinds);return a;
    }
    private static JsonObject ramp(int limit){
        JsonObject r=new JsonObject();r.addProperty("format","awft-reviewed-life-population-ramp:1");r.addProperty("checkpoint_sha256","checkpoint-fixture");
        r.addProperty("recipe_sha256","recipe-fixture");r.addProperty("population_budget_sha256","budget-fixture");r.addProperty("maximum_total_after_cohort",limit);
        r.addProperty("native_AI_and_resource_measurements_reviewed",true);
        JsonArray refs=new JsonArray();JsonObject placeholder=new JsonObject();placeholder.addProperty("fixture_not_actual_native_evidence",true);refs.add(placeholder);r.add("native_measurement_refs",refs);return r;
    }
    private static ScaledLifeBudget policy(JsonObject a,JsonObject r){return new ScaledLifeBudget(a,r,"fixture-only",HabitatLifePolicy.CURATION_SHA256,"checkpoint-fixture","recipe-fixture","budget-fixture");}
    private static void refused(Runnable action){try{action.run();throw new AssertionError("Invalid scale admitted");}catch(IllegalStateException|ArithmeticException expected){}}
    public static void main(String[] args){
        refused(()->HabitatLifePolicy.budget(Map.of("naturalist:bird",65)));
        var budget=policy(authority(),ramp(4000));Map<String,Integer> distributed=new HashMap<>();
        for(int i=0;i<1000;i++)distributed.put(ScaledLifeBudget.habitat("AIR",i*32,0),4);
        budget.check(Map.of("naturalist:bird",4000),distributed);
        refused(()->budget.check(Map.of("naturalist:bird",4001),distributed));
        refused(()->budget.check(Map.of("naturalist:bird",257),Map.of("AIR|0|0",257)));
        refused(()->policy(authority(),ramp(128)).check(Map.of("naturalist:bird",129),Map.of("AIR|0|0",129)));
        JsonObject missingMeasurements=ramp(4000);missingMeasurements.add("native_measurement_refs",new JsonArray());refused(()->policy(authority(),missingMeasurements));
        JsonObject noAI=authority();noAI.addProperty("normal_native_AI_required",false);refused(()->policy(noAI,ramp(4000)));
        JsonObject fractional=authority();fractional.addProperty("maximum_residents",4000.5);refused(()->policy(fractional,ramp(4000)));
        JsonObject disabled=authority();disabled.getAsJsonObject("per_species_caps").addProperty("naturalist:dragonfly",4000);refused(()->policy(disabled,ramp(4000)));
        refused(()->ScaledLifeBudget.habitat("AIR",Double.POSITIVE_INFINITY,0));
        System.out.println("PASS explicit4000 versus legacy64; cohort configuration; global/species/local/ramp/measurement/AI/type limits. Synthetic policy fixtures only; no real budget authority, native measurement, entity, world or performance acceptance.");
    }
}
