package worldfortwo.bridge;

/** Pure Java fixture; no Minecraft bootstrap or simulated native acceptance. */
public final class HabitatLifePolicyProbe {
    private static int passed;
    private static void yes(boolean value){if(!value)throw new AssertionError("Policy assertion failed");passed++;}
    private static void refuses(Runnable action){try{action.run();}catch(IllegalStateException expected){passed++;return;}throw new AssertionError("Unsafe policy was accepted");}
    public static void main(String[] args){
        var deer=HabitatLifePolicy.SPECIES.get("naturalist:deer");
        yes(HabitatLifePolicy.species("naturalist:deer",deer.nativeClass(),deer.category()).equals(deer));
        refuses(()->HabitatLifePolicy.species("naturalist:bear",deer.nativeClass(),deer.category()));
        refuses(()->HabitatLifePolicy.species("naturalist:deer","foreign.Class",deer.category()));
        refuses(()->HabitatLifePolicy.species("naturalist:deer",deer.nativeClass(),"monster"));
        yes(HabitatLifePolicy.existing(false,false,false)==HabitatLifePolicy.Existing.NEW);
        yes(HabitatLifePolicy.existing(true,true,true)==HabitatLifePolicy.Existing.PRESERVE);
        refuses(()->HabitatLifePolicy.existing(true,false,false));
        refuses(()->HabitatLifePolicy.existing(false,true,true));
        refuses(()->HabitatLifePolicy.existing(true,true,false));
        HabitatLifePolicy.live(false,false,true,true,false,false);passed++;
        HabitatLifePolicy.live(false,false,true,false,true,true);passed++; // ordinary adopted pet retained
        refuses(()->HabitatLifePolicy.live(true,false,true,false,false,false));
        refuses(()->HabitatLifePolicy.live(false,true,true,false,false,false));
        refuses(()->HabitatLifePolicy.live(false,false,false,false,false,false));
        refuses(()->HabitatLifePolicy.live(false,false,true,true,true,true));
        HabitatLifePolicy.coordinate(1100.5,66,-1050.5);passed++;
        refuses(()->HabitatLifePolicy.coordinate(Double.NaN,66,-1050));
        refuses(()->HabitatLifePolicy.coordinate(1100,Double.POSITIVE_INFINITY,-1050));
        refuses(()->HabitatLifePolicy.coordinate(0,66,-1050));
        System.out.println("{\"passed\":"+passed+",\"native_game_started\":false,\"native_behavior_acceptance\":false}");
    }
}
