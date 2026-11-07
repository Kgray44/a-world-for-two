package worldfortwo.bridge;

import com.simibubi.create.content.trains.entity.Train;
import com.simibubi.create.content.trains.schedule.Schedule;
import com.simibubi.create.content.trains.schedule.ScheduleEntry;
import com.simibubi.create.content.trains.schedule.condition.PlayerPassengerCondition;
import com.simibubi.create.content.trains.schedule.condition.ScheduledDelay;
import com.simibubi.create.content.trains.schedule.condition.ScheduleWaitCondition;
import com.simibubi.create.content.trains.schedule.destination.DestinationInstruction;
import net.minecraft.core.HolderLookup;
import net.minecraft.nbt.CompoundTag;
import java.util.ArrayList;
import java.util.List;

/** A real Create schedule value, never a command that starts or moves a train.
 * The master hands an actually configured schedule item to a genuine conductor
 * through ordinary gameplay. A completed round trip does not circulate at idle.
 */
public final class CopperWrenPassengerSchedule {
    public static final String MILL="Copper Wren Mill", ORCHARD="Rosewater Orchard Halt";
    private CopperWrenPassengerSchedule() {}

    public static Schedule roundTrip(HolderLookup.Provider registries,int passengers) {
        if(passengers<1||passengers>2)throw new IllegalArgumentException("One or two actual player passengers required");
        Schedule schedule=new Schedule();
        schedule.cyclic=false;
        // One inner condition list means AND, outer lists mean OR in Create.
        schedule.entries.add(stop(registries,MILL,passengers,false));
        schedule.entries.add(stop(registries,ORCHARD,passengers,false));
        schedule.entries.add(stop(registries,MILL,0,true));
        schedule.savedProgress=0;
        return schedule;
    }

    private static ScheduleEntry stop(HolderLookup.Provider registries,String name,int passengers,boolean exact) {
        DestinationInstruction destination=new DestinationInstruction();
        CompoundTag text=new CompoundTag();text.putString("Text",name);destination.setData(registries,text);
        PlayerPassengerCondition boarded=new PlayerPassengerCondition();
        CompoundTag count=new CompoundTag();count.putInt("Count",passengers);count.putInt("Exact",exact?0:1);
        boarded.setData(registries,count);
        ScheduledDelay dwell=new ScheduledDelay();
        CompoundTag delay=new CompoundTag();delay.putInt("Value",20);delay.putInt("TimeUnit",1);
        dwell.setData(registries,delay);
        if(!destination.getFilter().equals(name)||boarded.getTarget()!=passengers
            ||boarded.canOvershoot()==exact||dwell.totalWaitTicks()!=400)
            throw new IllegalStateException("Pinned Create schedule semantics changed");
        ScheduleEntry entry=new ScheduleEntry();entry.instruction=destination;
        entry.conditions.add(new ArrayList<ScheduleWaitCondition>(List.of(dwell,boarded)));
        return entry;
    }

    /** Read-only prerequisites; does not update conductors, schedule or speed. */
    public static void requireParkedReadyTrain(Train train) {
        if(train==null||train.invalid||train.derailed||train.graph==null||!train.doubleEnded
            ||!Double.isFinite(train.speed)||Math.abs(train.speed)>.001
            ||train.getCurrentStation()==null||!MILL.equals(train.getCurrentStation().name)
            ||!train.hasForwardConductor()||!train.hasBackwardConductor()
            ||train.carriages.size()!=1||!train.carriages.getFirst().isOnTwoBogeys()
            ||train.runtime.getSchedule()!=null)
            throw new IllegalStateException("A parked native double-ended train, both actual conductors and no previous schedule are required");
    }
}
