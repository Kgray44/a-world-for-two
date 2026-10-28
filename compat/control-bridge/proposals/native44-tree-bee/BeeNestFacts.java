package worldfortwo.bridge;

import java.util.*;

/** Original admission facts only; no hive/entity NBT is constructed or altered. */
public final class BeeNestFacts {
    public record Occupant(Set<String> entityKeys,String id,int ticks,int minimumTicks,boolean hasUuid) {}
    public static void occupants(List<Occupant> values,boolean complete){
        if(values.size()>3||complete&&values.size()<2)throw new IllegalStateException("Only the native 2..3-occupant feature outcome is accepted");
        for(Occupant value:values)if(!value.entityKeys.equals(Set.of("id"))||!value.id.equals("minecraft:bee")
            ||value.hasUuid||value.ticks<0||value.ticks>598||value.minimumTicks!=600)
            throw new IllegalStateException("Native-created default bee records only; no copied UUID, owner, traits or inventory");
    }
    public static void nest(boolean originalAir,boolean attempted,boolean exactBlock,boolean exactEntity,int honey,boolean fireNearby,int count,boolean complete){
        if(!originalAir||!attempted||!exactBlock||!exactEntity||honey!=0||fireNearby||count<0||count>1)
            throw new IllegalStateException("Only one exact newly native-created bee nest on original owned AIR is eligible");
    }
    public static void census(Map<UUID,String> before,Map<UUID,String> after){
        if(!before.equals(after))throw new IllegalStateException("Live entity census changed during synchronous growth/removal; quarantine, do not delete or invent bees");
    }
    private BeeNestFacts(){}
}
