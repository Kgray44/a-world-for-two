package worldfortwo.bridge;

import com.google.gson.Gson;
import com.google.gson.JsonObject;
import com.simibubi.create.AllDataComponents;
import com.simibubi.create.AllItems;
import com.simibubi.create.Create;
import com.simibubi.create.content.trains.schedule.ScheduleItem;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.ChestBlock;
import net.minecraft.world.level.block.entity.ChestBlockEntity;
import net.minecraft.world.level.block.state.properties.ChestType;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.UUID;

/** Configure one actual stocked blank item, never spawn/copy/apply a schedule. */
public final class CopperWrenScheduleItem {
    private static final Gson JSON=new Gson();
    private static final BlockPos STARTER=new BlockPos(1313,68,-994);
    private CopperWrenScheduleItem() {}

    static ChestBlockEntity starter(ServerLevel world) {
        var chunk=world.getChunkSource().getChunkNow(STARTER.getX()>>4,STARTER.getZ()>>4);
        if(chunk==null)
            throw new IllegalStateException("Starter chunk must already be loaded");
        var state=chunk.getBlockState(STARTER);
        if(!state.is(Blocks.CHEST)||state.getValue(ChestBlock.TYPE)!=ChestType.SINGLE
            ||!(chunk.getBlockEntities().get(STARTER) instanceof ChestBlockEntity stock)
            ||stock.getClass()!=ChestBlockEntity.class||stock.getContainerSize()!=27||stock.getLootTable()!=null)
            throw new IllegalStateException("Exact single vanilla chest without a pending loot table required before any item read");
        // setChanged() notifies output-signal neighbors. Its vanilla comparator
        // callbacks may read farther or remove unsupported blocks. Admit only an
        // already-loaded two-block horizontal footprint with no such comparator.
        for(Direction direction:Direction.Plane.HORIZONTAL)for(int distance=1;distance<=2;distance++) {
            BlockPos position=STARTER.relative(direction,distance);
            var neighbor=world.getChunkSource().getChunkNow(position.getX()>>4,position.getZ()>>4);
            if(neighbor==null)
                throw new IllegalStateException("Stock output-signal callback footprint must already be loaded");
            if(neighbor.getBlockState(position).is(Blocks.COMPARATOR))
                throw new IllegalStateException("Comparator callback in the stock footprint requires separate admission");
        }
        return stock;
    }

    static List<String> inventory(ServerLevel world,ChestBlockEntity stock) {
        if(starter(world)!=stock)throw new IllegalStateException("Actual non-loot starter chest changed before item reads");
        List<String> rows=new ArrayList<>();
        for(int n=0;n<27;n++) {
            ItemStack item=stock.getItem(n);String value=item.isEmpty()?"":item.save(world.registryAccess()).toString();
            if(value.length()>2048)throw new IllegalStateException("Finite ordinary starter stock required");rows.add(value);
        }
        return rows;
    }

    /** Parent publishes this actual all-slot readback through its native journal;
     * callers must not invent SNBT from a sparse or historical inventory view.
     */
    public static JsonObject inspectStarter(ServerLevel world,ArtisticEngineeringSupport.Lease lease,String request)throws Exception {
        CopperWrenStationNames.gate(world,lease);
        ChestBlockEntity stock=starter(world);
        JsonObject read=CopperWrenStationNames.record("starter.inspection_only",request);
        read.add("position",JSON.toJsonTree(List.of(STARTER.getX(),STARTER.getY(),STARTER.getZ())));
        read.add("all27_native_snbt",JSON.toJsonTree(inventory(world,stock)));read.addProperty("world_mutated",false);
        read.addProperty("chunk_tickets_added",0);return read;
    }

    /** Parent must bind the expected full-slot inventory and real train UUID from
     * fresh native custody. Ordinary gameplay hands this item to the conductor.
     */
    public static JsonObject configureBlankInStarter(ServerLevel world,ArtisticEngineeringSupport.Lease lease,
            UUID trainId,CopperWrenStationNames.Expected expectedNames,int slot,int passengers,List<String> expectedStock,String request,Runnable mutation,
            Map<String,Object> parentReport)throws Exception {
        Path root=CopperWrenStationNames.gate(world,lease);
        var graph=CopperWrenStationNames.namedGraph(world,lease,expectedNames);
        if(slot<0||slot>=27||expectedStock==null||expectedStock.size()!=27)
            throw new IllegalStateException("Actual full27-slot stock preimage required");
        ChestBlockEntity stock=starter(world);
        var train=Create.RAILWAYS.trains.get(trainId);CopperWrenPassengerSchedule.requireParkedReadyTrain(train);
        var entity=train.carriages.getFirst().anyAvailableEntity();
        var mill=graph.getPoint(com.simibubi.create.content.trains.graph.EdgePointType.STATION,expectedNames.mill());
        if(mill==null||train.graph!=graph||train.getCurrentStation()!=mill||mill.getPresentTrain()!=train
            ||train.getPositionInDimension(world.dimension()).isEmpty()||train.countPlayerPassengers()!=0
            ||entity==null||entity.isRemoved()||entity.level()!=world||entity.getContraption()==null||entity.getContraption().getSeats().size()!=3)
            throw new IllegalStateException("Actual parked empty three-seat carriage required");
        List<String> before=inventory(world,stock);
        if(!before.equals(expectedStock))throw new IllegalStateException("All27 native stock slots changed");
        ItemStack item=stock.getItem(slot);
        if(item.getCount()!=1||item.getItem()!=AllItems.SCHEDULE.get()||!item.getComponentsPatch().isEmpty()
            ||ScheduleItem.getSchedule(world.registryAccess(),item)!=null)
            throw new IllegalStateException("One genuine plain blank registered schedule item required; no component overwrite");
        String component=BuiltInRegistries.DATA_COMPONENT_TYPE.getKey(AllDataComponents.TRAIN_SCHEDULE).toString();
        if(!component.equals("create:train_schedule"))throw new IllegalStateException("Registered native schedule component differs");
        CompoundTag schedule=CopperWrenPassengerSchedule.roundTrip(world.registryAccess(),passengers).write(world.registryAccess());
        Path ledger=root.resolve("data/awft-copper-wren-schedule/"+trainId);
        if(Files.exists(ledger))throw new IllegalStateException("Prior schedule-item intent exists; preserve real inventory, no replay/refund");
        JsonObject intent=CopperWrenStationNames.record("schedule_item.intent",request);intent.addProperty("train_uuid",trainId.toString());
        intent.addProperty("graph_uuid",graph.id.toString());intent.addProperty("mill_station_uuid",expectedNames.mill().toString());
        intent.addProperty("halt_station_uuid",expectedNames.halt().toString());
        intent.addProperty("slot",slot);intent.addProperty("passengers",passengers);intent.add("all27_before_native_snbt",JSON.toJsonTree(before));
        intent.addProperty("expected_native_schedule_snbt",schedule.toString());
        mutation.run();parentReport.put("schedule_item_mutation_possible",true);
        CopperWrenStationNames.durable(world,lease,ledger.resolve("intent.json"),intent);
        CopperWrenStationNames.gate(world,lease);
        if(starter(world)!=stock||!inventory(world,stock).equals(before)||stock.getItem(slot)!=item||mill.getPresentTrain()!=train)
            throw new IllegalStateException("Exact chest/callback footprint/full stock/attachment changed after intent; preserve it");
        item.set(AllDataComponents.TRAIN_SCHEDULE,schedule.copy());stock.setChanged();
        var read=ScheduleItem.getSchedule(world.registryAccess(),stock.getItem(slot));List<String> after=inventory(world,stock);
        if(stock.getItem(slot)!=item||item.getCount()!=1||read==null||!read.write(world.registryAccess()).equals(schedule)
            ||train.runtime.getSchedule()!=null||Math.abs(train.speed)>.001)
            throw new IllegalStateException("Actual schedule item/readback changed; retain intent and real stock");
        for(int n=0;n<27;n++)if(n!=slot&&!before.get(n).equals(after.get(n)))
            throw new IllegalStateException("Unrelated starter stock changed; preserve partial record");
        JsonObject done=CopperWrenStationNames.record("schedule_item.completed",request);done.addProperty("train_uuid",trainId.toString());
        done.addProperty("slot",slot);done.add("all27_after_native_snbt",JSON.toJsonTree(after));
        done.addProperty("actual_native_schedule_snbt",read.write(world.registryAccess()).toString());
        done.addProperty("actual_registered_component",component);
        done.addProperty("items_created",0);done.addProperty("items_removed",0);done.addProperty("train_schedule_applied",false);
        done.addProperty("chunk_tickets_added",0);CopperWrenStationNames.durable(world,lease,ledger.resolve("completed.json"),done);return done;
    }
}
