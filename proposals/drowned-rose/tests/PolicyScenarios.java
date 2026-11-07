import java.util.*;
import worldfortwo.tavern.ActivityPolicy;

public class PolicyScenarios {
    static void require(boolean ok,String message){if(!ok)throw new AssertionError(message);}
    public static void main(String[] args){
        require(ActivityPolicy.rugTransit("minecraft:red_carpet","minecraft:air"),"central red rug must admit transit");
        require(ActivityPolicy.rugTransit("minecraft:brown_carpet","minecraft:air"),"central brown rug must admit transit");
        require(!ActivityPolicy.rugTransit("handcrafted:dark_oak_chair","minecraft:air"),"chair must never become rug transit");
        require(!ActivityPolicy.rugTransit("minecraft:red_carpet","minecraft:stone"),"blocked headroom must refuse rug transit");
        require(ActivityPolicy.insideTavernFootprint(1302.5,-1270.5),"last approved row centre must agree with movement boundary");
        require(!ActivityPolicy.insideTavernFootprint(1302.5,-1269.5),"exterior row must remain outside movement boundary");
        List<ActivityPolicy.Slot> places=new ArrayList<>();
        for(int i=0;i<18;i++)places.add(new ActivityPolicy.Slot("chair"+i,"table"+(i/3),List.of("sit","social")));
        for(int i=0;i<48;i++)places.add(new ActivityPolicy.Slot("floor"+i,"group"+(i/4),List.of("social","bar","walk","window")));
        places.add(new ActivityPolicy.Slot("stage","band",List.of("music")));
        Map<String,Integer> preferences=Map.of("sit",3,"social",6,"walk",2,"bar",3,"window",3);
        Set<UUID> uuids=new HashSet<>();Set<String> occupied=new HashSet<>();
        List<LinkedList<String>> histories=new ArrayList<>();String[] current=new String[45];
        Set<Integer> seated=new HashSet<>(),standing=new HashSet<>();Random random=new Random(8461);
        for(int i=0;i<45;i++){uuids.add(ActivityPolicy.identity("resident"+i));histories.add(new LinkedList<>());}
        require(uuids.size()==45,"stable IDs must be unique");
        require(ActivityPolicy.identity("resident0").equals(ActivityPolicy.identity("resident0")),"stable ID across process reload");
        require(ActivityPolicy.resumeDeadline(12100,12000,ActivityPolicy.identity("resident0"))==12100,"restart must preserve short unfinished activity duration");
        require(ActivityPolicy.resumeDeadline(99999,12000,ActivityPolicy.identity("resident0"))<=13200,"legacy long dwell must be capped");
        Set<Long> resumed=new HashSet<>();
        for(UUID id:uuids){long until=ActivityPolicy.resumeDeadline(11000,12000,id);require(until>=12020&&until<12620,"expired activity must resume within bounded stagger");resumed.add(until);}
        require(resumed.size()>20,"restart must not synchronize expired activity decisions");
        //45 residents compete for66 places over45,000 independent transitions.
        for(int cycle=0;cycle<1000;cycle++)for(int i=0;i<45;i++){
            if(current[i]!=null)occupied.remove(current[i]);
            var history=histories.get(i);
            var choice=ActivityPolicy.choose(random,places,occupied,history,preferences,cycle%2==0,false).orElseThrow();
            String id=choice.slot().id();require(!occupied.contains(id),"double reservation");
            require(!history.stream().limit(3).anyMatch(id::equals),"two-position loop");
            require(choice.ticks()>=200&&choice.ticks()<=1200,"activity duration bounds10–60s");
            require(!choice.activity().equals("music"),"ensemble stage must be coordinator-owned");
            if(choice.activity().equals("sit"))seated.add(i);else standing.add(i);
            current[i]=id;occupied.add(id);history.addFirst(id);while(history.size()>4)history.removeLast();
        }
        require(seated.size()==45&&standing.size()==45,"all residents must change posture/role");
        require(ActivityPolicy.choose(random,places,new HashSet<>(places.stream().map(ActivityPolicy.Slot::id).toList()),List.of(),preferences,false,false).isEmpty(),"full room must wait");
        require(ActivityPolicy.dialogue(random,List.of("one","two","three"),List.of("one"),List.of("two")).orElseThrow().equals("three"),"both dialogue histories must exclude repeats");
        require(ActivityPolicy.dialogue(random,List.of("one","two"),List.of("one"),List.of("two")).isEmpty(),"exhausted history must wait instead of repeat");
        System.out.println("PASS:45 identities,45,000 varied transitions, exclusive destinations, recent-history exclusion, bounded dwell, dialogue exclusion; synthetic policy evidence only");
    }
}
