import worldfortwo.bridge.DryFountainGateFacts;

/** Pure compiled state policy, not Minecraft piston or hydraulic evidence. */
public final class DryFountainGateProbe {
    public static void main(String[] args){
        int accepted=0,refused=0;
        for(boolean extended:new boolean[]{false,true})for(boolean powered:new boolean[]{false,true})
            for(var open:DryFountainGateFacts.Cell.values())for(var port:DryFountainGateFacts.Cell.values())
                for(boolean moving:new boolean[]{false,true}){
                    boolean parked=!moving&&!extended&&!powered&&open==DryFountainGateFacts.Cell.QUARTZ&&port==DryFountainGateFacts.Cell.AIR;
                    boolean orphan=!moving&&!extended&&!powered&&open==DryFountainGateFacts.Cell.AIR&&port==DryFountainGateFacts.Cell.QUARTZ;
                    boolean on=!moving&&extended&&powered&&open==DryFountainGateFacts.Cell.STICKY_HEAD&&port==DryFountainGateFacts.Cell.QUARTZ;
                    try{
                        var result=DryFountainGateFacts.classify(extended,powered,open,port,moving);
                        if(!(parked||orphan||on))throw new AssertionError("Ambiguous or moving state accepted");
                        var expected=parked?DryFountainGateFacts.Baseline.ALREADY_PARKED:orphan?DryFountainGateFacts.Baseline.DETACHED_PLUG:DryFountainGateFacts.Baseline.STABLE_ON;
                        if(result!=expected)throw new AssertionError("Wrong admitted baseline");accepted++;
                    }catch(IllegalStateException refusal){if(parked||orphan||on)throw new AssertionError("A coherent owned dry baseline was refused",refusal);refused++;}
                }
        if(accepted!=3||refused!=125)throw new AssertionError("Incomplete state policy");
        System.out.println("PASS:3 coherent dry baselines;125 ambiguous/moving combinations refused; no native world created");
    }
}
