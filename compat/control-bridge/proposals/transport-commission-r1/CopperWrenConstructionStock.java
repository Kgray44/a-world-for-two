package worldfortwo.bridge;

import com.google.gson.Gson;
import com.google.gson.JsonObject;
import com.pedrorok.hypertube.core.smarttube.RedstoneDetectorAttachment;
import com.pedrorok.hypertube.items.TubeAttachmentItem;
import com.simibubi.create.AllItems;
import com.simibubi.create.content.processing.burner.BlazeBurnerBlockItem;
import com.simibubi.create.content.trains.schedule.ScheduleItem;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import java.nio.file.Files;
import java.nio.file.LinkOption;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/** Optional fixed creative-construction hardware supply, never processing output.
 * No command hook: parent must explicitly admit creative authoring, authenticate
 * request/artifact/checkpoint/native inventory, own a valid lease and journal it.
 */
public final class CopperWrenConstructionStock {
    private static final Gson JSON=new Gson();
    private static final String DETECTOR="create_hypertube:redstone_detector_tube_attachment";
    private static final String BURNER="create:blaze_burner",SCHEDULE="create:schedule";
    private static final List<String> IDS=List.of(DETECTOR,BURNER,SCHEDULE);
    private static final int[] COUNTS={2,2,1};
    private CopperWrenConstructionStock() {}

    private static Item registered(String id) {
        ResourceLocation key=ResourceLocation.parse(id);
        if(!BuiltInRegistries.ITEM.containsKey(key))throw new IllegalStateException("Actual registered construction hardware unavailable: "+id);
        return BuiltInRegistries.ITEM.get(key);
    }

    private static void hardware(ServerLevel world,ItemStack stack,int index) {
        String id=BuiltInRegistries.ITEM.getKey(stack.getItem()).toString();
        if(!id.equals(IDS.get(index))||stack.getItem()!=registered(id)||stack.getCount()!=COUNTS[index]
            ||!stack.getComponentsPatch().isEmpty())throw new IllegalStateException("Actual plain fixed hardware identity/count differs");
        if(index==0) {
            if(!(stack.getItem() instanceof TubeAttachmentItem item))throw new IllegalStateException("Actual detector attachment item class required");
            var attachment=item.getTubeAttachment();
            if(attachment==null||attachment.getClass()!=RedstoneDetectorAttachment.class
                ||!attachment.getId().equals("redstone_input")||attachment.emitRedstoneSignal()
                ||attachment.getItemStack().getItem()!=stack.getItem())
                throw new IllegalStateException("Actual registered WEST input detector getter differs");
        } else if(index==1) {
            if(!(stack.getItem() instanceof BlazeBurnerBlockItem burner)||!burner.hasCapturedBlaze())
                throw new IllegalStateException("Actual registered FILLED burner getter required; no actor or captured NBT substitution");
        } else if(stack.getItem()!=AllItems.SCHEDULE.get()||!(stack.getItem() instanceof ScheduleItem)
            ||ScheduleItem.getSchedule(world.registryAccess(),stack)!=null)
            throw new IllegalStateException("Actual registered blank schedule item required");
    }

    private static JsonObject row(ServerLevel world,ItemStack stack,int index) {
        hardware(world,stack,index);JsonObject row=new JsonObject();row.addProperty("slot",index+3);
        row.addProperty("item",BuiltInRegistries.ITEM.getKey(stack.getItem()).toString());row.addProperty("count",stack.getCount());
        row.addProperty("native_item_class",stack.getItem().getClass().getName());
        row.addProperty("native_components",stack.getComponentsPatch().toString());
        row.addProperty("native_stack_snbt",stack.save(world.registryAccess()).toString());
        row.addProperty("native_has_captured_blaze",stack.getItem() instanceof BlazeBurnerBlockItem burner&&burner.hasCapturedBlaze());
        if(stack.getItem() instanceof TubeAttachmentItem item) {
            row.addProperty("native_attachment_class",item.getTubeAttachment().getClass().getName());
            row.addProperty("native_attachment_id",item.getTubeAttachment().getId());
        }
        return row;
    }

    /** Fixed slots3/4/5, fixed5items, one world ledger. The boolean is a required
     * parent admission assertion, not authorization obtained by calling this API.
     */
    public static JsonObject supplyFixedHardware(ServerLevel world,ArtisticEngineeringSupport.Lease lease,
            boolean parentAdmittedCreativeAuthoring,List<String> expectedAll27,String request,Runnable mutation,
            Map<String,Object> parentReport)throws Exception {
        if(!parentAdmittedCreativeAuthoring)throw new IllegalStateException("Explicit master creative-construction admission required");
        Path root=CopperWrenStationNames.gate(world,lease);
        var stock=CopperWrenScheduleItem.starter(world);List<String> before=CopperWrenScheduleItem.inventory(world,stock);
        if(expectedAll27==null||expectedAll27.size()!=27||!before.equals(expectedAll27))
            throw new IllegalStateException("Fresh exact all27 native starter slots required");
        for(int slot=3;slot<=5;slot++)if(!stock.getItem(slot).isEmpty()||!before.get(slot).isEmpty())
            throw new IllegalStateException("Slots3/4/5 must all be genuinely empty; never overwrite or restock");
        Path ledger=root.resolve("data/awft-copper-wren-construction-stock-r1");
        if(Files.exists(ledger,LinkOption.NOFOLLOW_LINKS))
            throw new IllegalStateException("Fixed hardware authoring ledger already exists; preserve partial stock, no nonce retry/refund");
        List<ItemStack> stacks=new ArrayList<>();List<String> expectedAfter=new ArrayList<>(before);List<JsonObject> additions=new ArrayList<>();
        for(int n=0;n<3;n++) {
            ItemStack stack=new ItemStack(registered(IDS.get(n)),COUNTS[n]);hardware(world,stack,n);
            stacks.add(stack);expectedAfter.set(n+3,stack.save(world.registryAccess()).toString());additions.add(row(world,stack,n));
        }
        JsonObject intent=CopperWrenStationNames.record("creative_hardware.intent",request);
        intent.addProperty("authoring_mode","explicit master creative construction; not recipe output or inventory conservation evidence");
        intent.add("all27_before_native_snbt",JSON.toJsonTree(before));intent.add("intended_fixed_hardware",JSON.toJsonTree(additions));
        intent.addProperty("intended_item_additions",5);intent.addProperty("actors_created",0);
        mutation.run();parentReport.put("creative_hardware_mutation_possible",true);
        CopperWrenStationNames.durable(world,lease,ledger.resolve("intent.json"),intent);
        List<String> working=new ArrayList<>(before);
        for(int n=0;n<3;n++) {
            CopperWrenStationNames.gate(world,lease);
            if(CopperWrenScheduleItem.starter(world)!=stock||!CopperWrenScheduleItem.inventory(world,stock).equals(working)
                ||!stock.getItem(n+3).isEmpty())throw new IllegalStateException("Actual chest/apron/all-slot custody changed after intent; retain partial stock");
            parentReport.put("creative_hardware_slot_mutation_may_have_started",n+3);
            stock.setItem(n+3,stacks.get(n));working.set(n+3,expectedAfter.get(n+3));
            if(!CopperWrenScheduleItem.inventory(world,stock).equals(working))
                throw new IllegalStateException("Actual hardware slot/readback differs; retain partial stock and intent");
        }
        CopperWrenStationNames.gate(world,lease);
        if(CopperWrenScheduleItem.starter(world)!=stock||!CopperWrenScheduleItem.inventory(world,stock).equals(expectedAfter))
            throw new IllegalStateException("Actual callback apron/fixed5hardware custody changed before setChanged");
        stock.setChanged();List<String> after=CopperWrenScheduleItem.inventory(world,stock);
        if(!after.equals(expectedAfter))throw new IllegalStateException("Real hardware or unrelated stock changed; preserve partial intent");
        List<JsonObject> actual=new ArrayList<>();for(int n=0;n<3;n++)actual.add(row(world,stock.getItem(n+3),n));
        JsonObject done=CopperWrenStationNames.record("creative_hardware.completed",request);
        done.add("all27_after_native_snbt",JSON.toJsonTree(after));done.add("actual_fixed_hardware",JSON.toJsonTree(actual));
        done.addProperty("actual_creative_item_additions",5);done.addProperty("items_removed",0);done.addProperty("actors_created",0);
        done.addProperty("wheat_flour_iron_or_recipe_products_created",false);done.addProperty("train_schedule_applied",false);
        done.addProperty("direct_helper_tickets_added",0);CopperWrenStationNames.durable(world,lease,ledger.resolve("completed.json"),done);
        return done;
    }
}
