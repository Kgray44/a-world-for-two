package worldfortwo.tavern;

import java.util.UUID;
import earth.terrarium.handcrafted.common.entities.Seat;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.registries.Registries;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.MobCategory;
import net.minecraft.world.entity.vehicle.DismountHelper;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.Vec3;
import net.neoforged.neoforge.registries.DeferredHolder;
import net.neoforged.neoforge.registries.DeferredRegister;

/** Saveable managed vehicle retaining Handcrafted's native chair behavior. */
public final class ManagedSeat extends Seat {
    public static final DeferredRegister<EntityType<?>> TYPES=DeferredRegister.create(Registries.ENTITY_TYPE,"awft_tavern");
    public static final DeferredHolder<EntityType<?>,EntityType<ManagedSeat>> TYPE=TYPES.register("persistent_seat",
        ()->EntityType.Builder.<ManagedSeat>of(ManagedSeat::new,MobCategory.MISC).sized(1,1)
            .clientTrackingRange(8).updateInterval(20).fireImmune().noSummon().build("awft_tavern:persistent_seat"));
    private UUID resident;
    private int emptyTicks;
    private LivingEntity leavingPassenger;
    private Vec3 reviewedExit;

    public ManagedSeat(EntityType<? extends ManagedSeat> type,Level level){
        // Native constructor installs its WrappedLevelCallBack. The ordinary
        // setPos/load callback derives native private shape from SittableBlock;
        // Passenger attachment, facing and ticking retain Handcrafted's code.
        super(type,level);
    }

    static ManagedSeat at(Level level,BlockPos pos,Direction facing,UUID owner){
        ManagedSeat seat=new ManagedSeat(TYPE.get(),level);seat.resident=owner;
        seat.setYRot(facing.toYRot());seat.setPos(pos.getX()+.5,pos.getY(),pos.getZ()+.5);
        return seat;
    }

    /** Read-only native floor/body preflight; the adapter checks survey/reservations. */
    Vec3 nativeExit(LivingEntity passenger,BlockPos approach){
        if(level().isClientSide()||isRemoved()||passenger.getVehicle()!=this
            ||resident==null||!resident.equals(passenger.getUUID())
            ||!level().hasChunkAt(approach))return null;
        Vec3 target=DismountHelper.findSafeDismountLocation(passenger.getType(),level(),approach,false);
        if(target==null)return null;
        // Preserve Handcrafted's native dismount lift, with no generic seat-center fallback.
        target=target.add(0,.25,0);
        if(!BlockPos.containing(target).equals(approach))return null;
        AABB body=passenger.getBoundingBox().move(target.subtract(passenger.position()));
        if(!level().noCollision(passenger,body)
            ||!level().getEntitiesOfClass(LivingEntity.class,body.inflate(.1),other->other!=passenger).isEmpty())return null;
        return target;
    }

    /** One synchronous native stopRiding call after the caller's reviewed preflight. */
    boolean dismount(LivingEntity passenger,Vec3 target){
        if(passenger.getVehicle()!=this||target==null)return false;
        leavingPassenger=passenger;reviewedExit=target;
        try{passenger.stopRiding();return !passenger.isPassenger();}
        finally{leavingPassenger=null;reviewedExit=null;}
    }

    @Override public Vec3 getDismountLocationForPassenger(LivingEntity passenger){
        // LivingEntity.stopRiding invokes this on the original vehicle before
        // its normal dismountTo. No entity coordinate write is added here.
        if(passenger==leavingPassenger&&reviewedExit!=null)return reviewedExit;
        return super.getDismountLocationForPassenger(passenger);
    }

    @Override protected void readAdditionalSaveData(CompoundTag tag){
        super.readAdditionalSaveData(tag);resident=tag.hasUUID("awft_resident")?tag.getUUID("awft_resident"):null;
    }
    @Override protected void addAdditionalSaveData(CompoundTag tag){
        super.addAdditionalSaveData(tag);if(resident!=null)tag.putUUID("awft_resident",resident);
    }
    @Override public void tick(){
        super.tick();
        if(level().isClientSide()||isRemoved())return;
        if(!SITTING_POSITIONS.containsEntry(level().dimension(),blockPosition()))SITTING_POSITIONS.put(level().dimension(),blockPosition());
        if(getPassengers().isEmpty()){if(++emptyTicks>20)removeSeat();}else emptyTicks=0;
    }
    public UUID resident(){return resident;}
}
