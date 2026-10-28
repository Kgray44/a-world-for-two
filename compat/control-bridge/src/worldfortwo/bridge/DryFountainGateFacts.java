package worldfortwo.bridge;

/** Only the three coherent dry states of this one owned sticky gate.
 * No moving block, source, entity or world object is changed by this policy.
 */
public final class DryFountainGateFacts {
    public enum Cell { AIR, QUARTZ, STICKY_HEAD, OTHER }
    public enum Baseline { ALREADY_PARKED, DETACHED_PLUG, STABLE_ON }

    public static Baseline classify(boolean extended,boolean powered,Cell open,Cell port,boolean moving){
        if(moving)throw new IllegalStateException("Fresh stable dry gate required; preserve moving block evidence");
        if(!extended&&!powered&&open==Cell.QUARTZ&&port==Cell.AIR)return Baseline.ALREADY_PARKED;
        if(!extended&&!powered&&open==Cell.AIR&&port==Cell.QUARTZ)return Baseline.DETACHED_PLUG;
        if(extended&&powered&&open==Cell.STICKY_HEAD&&port==Cell.QUARTZ)return Baseline.STABLE_ON;
        throw new IllegalStateException("Unknown dry gate arrangement; do not move or replace its plug");
    }
    private DryFountainGateFacts(){}
}
