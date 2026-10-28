package worldfortwo.bridge;

import java.util.*;

/** Pure actual-policy regression; no Minecraft server, level, entity or fake player. */
public final class HabitatLifeExtensionProbe {
    private static int passed;
    private static void yes(boolean value){if(!value)throw new AssertionError("native44 policy");passed++;}
    private static void no(Runnable action){try{action.run();throw new AssertionError("Expected native44 refusal");}catch(IllegalStateException expected){passed++;}}
    public static void main(String[] ignored){
        yes(HabitatLifePolicy.SPECIES.size()==16);
        yes(HabitatLifePolicy.SPECIES.values().stream().filter(HabitatLifePolicy.Species::enabled).count()==15);
        yes(HabitatLifePolicy.ARTIFACTS.size()==7);
        for(var row:HabitatLifePolicy.SPECIES.entrySet())if(row.getValue().enabled()){
            var p=row.getValue();yes(HabitatLifePolicy.species(row.getKey(),p.nativeClass(),p.category(),p.kind().name())==p);
        }
        var deer=HabitatLifePolicy.SPECIES.get("naturalist:deer");
        var koi=HabitatLifePolicy.SPECIES.get("crittersandcompanions:koi_fish");
        var villager=HabitatLifePolicy.SPECIES.get("minecraft:villager");
        no(()->HabitatLifePolicy.species("naturalist:dragonfly",HabitatLifePolicy.SPECIES.get("naturalist:dragonfly").nativeClass(),"ambient","AIR"));
        no(()->HabitatLifePolicy.species("fairytales:fairy","invented.Fairy","ambient","AIR"));
        no(()->HabitatLifePolicy.species("minecraft:item",villager.nativeClass(),"misc","HOME"));
        no(()->HabitatLifePolicy.species("minecraft:villager",villager.nativeClass(),"creature","HOME"));
        no(()->HabitatLifePolicy.species("crittersandcompanions:koi_fish",koi.nativeClass(),koi.category(),"DRY"));
        no(()->HabitatLifePolicy.species("crittersandcompanions:koi_fish",koi.nativeClass(),koi.category()));
        var small=new HabitatLifePolicy.Box(1000,65,-1000,1002,69,-998);
        no(()->HabitatLifePolicy.geometry(koi,small,null,false,false,0));
        var known=new HabitatLifePolicy.Box(998,62,-1002,1006,69,-994);
        var swimming=new HabitatLifePolicy.Box(1000,64,-1000,1004,65,-996);
        HabitatLifePolicy.geometry(koi,known,swimming,false,false,0);passed++;
        no(()->HabitatLifePolicy.geometry(koi,known,new HabitatLifePolicy.Box(1000,64,-1000,1004,64,-996),false,false,0));
        no(()->HabitatLifePolicy.geometry(koi,known,null,false,false,0));
        no(()->HabitatLifePolicy.geometry(deer,known,swimming,false,false,0));
        no(()->HabitatLifePolicy.geometry(villager,known,null,true,false,1));
        HabitatLifePolicy.geometry(villager,known,null,true,true,2);passed++;
        no(()->HabitatLifePolicy.known(new HabitatLifePolicy.Box(998,62,-1002,1100,99,-994)));
        HabitatLifePolicy.coordinate(1352.5,184,-615.5);passed++;
        no(()->HabitatLifePolicy.coordinate(1353,184,-615.5));
        no(()->HabitatLifePolicy.coordinate(Double.NaN,66,-1000));
        no(()->HabitatLifePolicy.coordinate(1100,66,-600));
        no(()->HabitatLifePolicy.live(true,false,true,true,false,false));
        no(()->HabitatLifePolicy.live(false,false,true,true,true,true));
        HabitatLifePolicy.live(false,false,true,false,true,true);passed++;
        no(()->HabitatLifePolicy.existing(true,false,false));
        no(()->HabitatLifePolicy.existing(false,true,true));
        yes(HabitatLifePolicy.existing(true,true,true)==HabitatLifePolicy.Existing.PRESERVE);
        no(()->HabitatLifePolicy.budget(Map.of("doggytalents:dog",2)));
        no(()->HabitatLifePolicy.budget(Map.of("naturalist:dragonfly",1)));
        Map<String,Integer> maximum=new HashMap<>();for(var row:HabitatLifePolicy.SPECIES.entrySet())if(row.getValue().enabled())maximum.put(row.getKey(),row.getValue().populationCap());
        HabitatLifePolicy.budget(maximum);passed++;
        yes(maximum.values().stream().mapToInt(Integer::intValue).sum()==64);
        yes(villager.nativeResourceSha256().size()==2);
        StringJoiner artifacts=new StringJoiner(",","[","]");
        for(var a:HabitatLifePolicy.ARTIFACTS)artifacts.add("[\""+a.modId()+"\",\""+a.filename()+"\","+a.bytes()+",\""+a.sha256()+"\"]");
        System.out.println("{\"passed\":"+passed+",\"native_game_started\":false,\"native_habitat_acceptance\":false,\"artifact_pins\":"+artifacts+"}");
    }
}
