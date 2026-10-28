package worldfortwo.bridge;
import java.util.*;
public final class BeeNestFactsProbe {
    private static int cases;
    private static void pass(Runnable r){r.run();cases++;}
    private static void refuse(Runnable r){try{r.run();}catch(IllegalStateException expected){cases++;return;}throw new AssertionError("Expected refusal");}
    private static BeeNestFacts.Occupant bee(int ticks){return new BeeNestFacts.Occupant(Set.of("id"),"minecraft:bee",ticks,600,false);}
    public static void main(String[] ignored){
        pass(()->BeeNestFacts.occupants(List.of(bee(0),bee(1)),true));
        pass(()->BeeNestFacts.occupants(List.of(bee(598),bee(0),bee(2)),true));
        pass(()->BeeNestFacts.occupants(List.of(),false));
        refuse(()->BeeNestFacts.occupants(List.of(bee(0)),true));
        refuse(()->BeeNestFacts.occupants(List.of(bee(599),bee(0)),true));
        refuse(()->BeeNestFacts.occupants(List.of(new BeeNestFacts.Occupant(Set.of("id","NoAI"),"minecraft:bee",0,600,false),bee(0)),true));
        refuse(()->BeeNestFacts.occupants(List.of(new BeeNestFacts.Occupant(Set.of("id"),"minecraft:bee",0,600,true),bee(0)),true));
        pass(()->BeeNestFacts.nest(true,true,true,true,0,false,1,true));
        refuse(()->BeeNestFacts.nest(false,true,true,true,0,false,1,true));
        refuse(()->BeeNestFacts.nest(true,false,true,true,0,false,1,true));
        refuse(()->BeeNestFacts.nest(true,true,true,false,0,false,1,true));
        refuse(()->BeeNestFacts.nest(true,true,true,true,0,true,1,true));
        refuse(()->BeeNestFacts.nest(true,true,true,true,0,false,2,true));
        UUID id=UUID.randomUUID();pass(()->BeeNestFacts.census(Map.of(id,"bee|position"),Map.of(id,"bee|position")));
        refuse(()->BeeNestFacts.census(Map.of(),Map.of(id,"bee|position")));
        refuse(()->BeeNestFacts.census(Map.of(id,"bee|old"),Map.of(id,"bee|moved")));
        System.out.println("PASS "+cases+" native bee admission/census policy cases; no Minecraft/world/native hive executed");
    }
}
