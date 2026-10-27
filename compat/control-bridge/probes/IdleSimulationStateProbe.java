package worldfortwo.bridge;

/** Expected cases derived from the pinned patched ServerLevel.tick branch,
 * not an actual level/ticker execution or reflective-getter acceptance test.
 */
public final class IdleSimulationStateProbe {
    private static int checks;
    private static void expect(String expected,int players,Boolean forced,Integer counter) {
        checks++;String actual=IdleSimulationState.eligibility(players,forced,counter);
        if(!expected.equals(actual))throw new AssertionError("Expected "+expected+" for "+players+","+forced+","+counter+" but got "+actual);
    }
    public static void main(String[] args) {
        expect("eligible",0,false,0);
        expect("eligible",0,false,299);
        expect("suspended",0,false,300);
        expect("suspended",0,false,301);
        expect("eligible",1,false,900);
        expect("eligible",0,true,900);
        expect("eligible",1,null,null);
        expect("eligible",0,true,null);
        expect("unknown",0,false,null);
        expect("unknown",0,null,0);
        expect("unknown",0,null,null);
        // Preserve Java's native signed counter behavior; do not invent a clamp.
        expect("eligible",0,false,Integer.MIN_VALUE);
        expect("suspended",0,false,Integer.MAX_VALUE);
        boolean rejected=false;
        try{IdleSimulationState.eligibility(-1,false,0);}catch(IllegalArgumentException expected){rejected=true;}
        checks++;if(!rejected)throw new AssertionError("Impossible player count accepted");
        System.out.println("IDLE_SIMULATION_BRANCH_CHECKS="+checks+" PASS; no native level or getter executed");
    }
}
