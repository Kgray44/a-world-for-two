package worldfortwo.bridge;

import com.google.gson.*;
import com.pedrorok.hypertube.blocks.ActionTubeBlock;
import com.pedrorok.hypertube.blocks.HyperEntranceBlock;
import com.pedrorok.hypertube.blocks.TubePathBlock;
import com.pedrorok.hypertube.blocks.blockentities.TubePathBlockEntity;
import com.pedrorok.hypertube.blocks.blockentities.parent.ActionTubeBlockEntity;
import com.pedrorok.hypertube.core.collision.TubeCollision;
import com.pedrorok.hypertube.core.connection.BezierConnection;
import com.pedrorok.hypertube.core.connection.SimpleConnection;
import com.pedrorok.hypertube.core.connection.interfaces.ITubeConnectionEntity;
import com.pedrorok.hypertube.core.smarttube.ITubeAttachment;
import com.pedrorok.hypertube.core.smarttube.RedstoneDetectorAttachment;
import com.pedrorok.hypertube.items.TubeAttachmentItem;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.Container;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.block.state.properties.BlockStateProperties;
import net.minecraft.world.level.storage.LevelResource;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.shapes.BooleanOp;
import net.minecraft.world.phys.shapes.Shapes;
import java.nio.ByteBuffer;
import java.nio.channels.FileChannel;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.security.MessageDigest;
import java.time.Instant;
import java.util.*;

/** Isolated resume-only collaborator, no second command/tick listener.
 * No link setter, water placement, copied BE NBT, fake/null-player item use,
 * manufactured stack, forced entrance state, item refund or entity movement.
 */
public final class NativeMillResumeAttachments {
    public static final String ITEM="create_hypertube:redstone_detector_tube_attachment",ID="redstone_input";
    private static final Gson JSON=new Gson();
    private static final BlockPos STOCK=new BlockPos(1313,68,-994);
    private static final List<BlockPos> ENTRANCES=List.of(new BlockPos(1331,71,-991),new BlockPos(1331,71,-943));
    private final ServerLevel level;
    private final ArtisticEngineeringSupport.Lease lease;
    private final Set<BlockPos> admittedFillers;
    private final JsonObject partial;
    private final JsonObject initialStock;
    private final Container stock;
    private final Path ledger;
    private final String stableContract;
    private final boolean inspection;
    private final Runnable mutation;
    private final Map<String,Object> report;
    private String originalLinks;
    public NativeMillResumeAttachments(ServerLevel level,ArtisticEngineeringSupport.Lease lease,Set<BlockPos> admittedFillers,
            JsonObject partial,JsonObject inventoryProof,String stableContract,boolean inspection,Runnable mutation,Map<String,Object> report)throws Exception{
        this.level=level;this.lease=lease;this.admittedFillers=Set.copyOf(admittedFillers);this.partial=partial.deepCopy();this.inspection=inspection;this.mutation=mutation;this.report=report;this.stableContract=stableContract;
        if(!stableContract.matches("[a-f0-9]{64}"))throw new IllegalStateException("Exact stable mill-resume contract required");
        Path world=level.getServer().getWorldPath(LevelResource.ROOT).toRealPath();
        Path staging=Path.of("D:/A World for Two/staging/world-tests").toRealPath();
        if(!world.startsWith(staging)||world.getNameCount()!=staging.getNameCount()+3||!world.getParent().getFileName().toString().equals("world")||!world.getFileName().toString().equals("RosewaterArtistic")||level.getServer().getPort()!=25575)throw new IllegalStateException("Exact private artistic staging ancestry only");
        ledger=world.resolve("data/awft-mill-resume/"+stableContract);
        for(Path p=ledger;p!=null&&!p.equals(world);p=p.getParent())if(Files.exists(p,LinkOption.NOFOLLOW_LINKS)&&(Files.isSymbolicLink(p)||!p.toRealPath().equals(p.toAbsolutePath().normalize())))throw new IllegalStateException("No redirected resume ledger");
        if(!(level.getBlockEntity(STOCK) instanceof Container actual)||actual.getContainerSize()!=27)throw new IllegalStateException("Exact existing single starter chest required");stock=actual;
        check();initialStock=snapshot(copies());report.put("native_resume_stock",initialStock.deepCopy());
        if(!inspection&&(inventoryProof==null||!inventoryProof.equals(initialStock)))throw new IllegalStateException("Actual current native inventory snapshot differs; no item debit permitted");
        if(!partial.get("phase").getAsString().equals("WAIT_MODE")||partial.get("actual_wheat_feed_performed").getAsBoolean()||partial.get("train_created").getAsBoolean()
            ||partial.getAsJsonArray("native_tube_links").size()!=6||!partial.get("cleanup_passed").getAsBoolean()||partial.get("remaining_owned_tickets").getAsInt()!=0)throw new IllegalStateException("Only the retained clean six-link pre-feed WAIT_MODE failure is resumable");
        if(!inspection&&(Files.exists(ledger.resolve("feed.intent.json"))||Files.exists(ledger.resolve("assembly.intent.json"))))throw new IllegalStateException("A later-phase intent exists; preserve it for a new exact phase-specific recovery, never replay feed/assembly");
    }
    private static String sha(String value)throws Exception{return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(value.getBytes(StandardCharsets.UTF_8)));}
    private void check(){if(!level.getServer().isSameThread()||lease==null||!lease.valid()||!level.getServer().getPlayerList().getPlayers().isEmpty()||level.getBlockEntity(STOCK)!=stock)throw new IllegalStateException("Fresh shared lease/server-thread/empty-world/exact-container ownership required");}
    private List<ItemStack> copies(){List<ItemStack> out=new ArrayList<>();for(int i=0;i<stock.getContainerSize();i++)out.add(stock.getItem(i).copy());return out;}
    private JsonObject snapshot(List<ItemStack> stacks){JsonObject out=new JsonObject();out.add("position",JSON.toJsonTree(List.of(STOCK.getX(),STOCK.getY(),STOCK.getZ())));JsonArray slots=new JsonArray();
        for(int n=0;n<stacks.size();n++){ItemStack stack=stacks.get(n);JsonObject row=new JsonObject();row.addProperty("slot",n);row.addProperty("native_stack_snbt",stack.isEmpty()?"":stack.save(level.registryAccess()).toString());if(row.get("native_stack_snbt").getAsString().length()>2048)throw new IllegalStateException("Bounded ordinary starter stock required");slots.add(row);}out.add("slots",slots);return out;}
    private static String item(ItemStack stack){return stack.isEmpty()?"minecraft:air":BuiltInRegistries.ITEM.getKey(stack.getItem()).toString();}
    private int count(String id){int count=0;for(int n=0;n<stock.getContainerSize();n++)if(item(stock.getItem(n)).equals(id))count+=stock.getItem(n).getCount();return count;}
    private ActionTubeBlockEntity entrance(BlockPos p){if(!(level.getBlockState(p).getBlock() instanceof HyperEntranceBlock)||!(level.getBlockEntity(p) instanceof ActionTubeBlockEntity be))throw new IllegalStateException("Exact existing native entrance required");return be;}
    private boolean detector(ITubeAttachment value){return value!=null&&value.getClass()==RedstoneDetectorAttachment.class&&value.getId().equals(ID)&&!value.emitRedstoneSignal()&&item(value.getItemStack()).equals(ITEM);}
    private Path file(int index,String stage){return ledger.resolve("west-"+index+"."+stage+".json");}
    private JsonObject read(Path file)throws Exception{if(Files.isSymbolicLink(file)||!Files.isRegularFile(file,LinkOption.NOFOLLOW_LINKS)||Files.size(file)>65536)throw new IllegalStateException("Bounded exact resume ledger row required");return JsonParser.parseString(Files.readString(file)).getAsJsonObject();}
    private void durable(Path path,JsonObject value)throws Exception{check();mutation.run();Files.createDirectories(ledger);byte[] raw=(JSON.toJson(value)+"\n").getBytes(StandardCharsets.UTF_8);if(raw.length>65536)throw new IllegalStateException("Resume ledger row exceeds finite bound");try(FileChannel file=FileChannel.open(path,StandardOpenOption.CREATE_NEW,StandardOpenOption.WRITE)){ByteBuffer bytes=ByteBuffer.wrap(raw);while(bytes.hasRemaining())file.write(bytes);file.force(true);}}
    private void committed(int index,ActionTubeBlockEntity be)throws Exception{
        if(!Files.isRegularFile(file(index,"admitted"))||!Files.isRegularFile(file(index,"debit"))||!Files.isRegularFile(file(index,"intent")))throw new IllegalStateException("Existing attachment lacks this durable actual debit/admission; preserve unknown state");
        JsonObject intent=read(file(index,"intent")),debit=read(file(index,"debit")),done=read(file(index,"admitted"));
        if(!intent.get("contract_sha256").getAsString().equals(stableContract)||intent.get("index").getAsInt()!=index||!intent.getAsJsonArray("entrance").equals(JSON.toJsonTree(List.of(ENTRANCES.get(index).getX(),ENTRANCES.get(index).getY(),ENTRANCES.get(index).getZ())))||!intent.get("face").getAsString().equals("west")
            ||!intent.get("item").getAsString().equals(ITEM)||intent.get("amount").getAsInt()!=1||!debit.get("intent_sha256").getAsString().equals(sha(JSON.toJson(intent)))||!debit.get("actual_removed_native_snbt").equals(intent.get("expected_removed_native_snbt"))||!debit.get("after_stock").equals(intent.get("expected_after_stock"))
            ||!done.get("debit_sha256").getAsString().equals(sha(JSON.toJson(debit)))||!done.get("native_attachment_id").getAsString().equals(ID)||!done.get("native_attachment_class").getAsString().equals(RedstoneDetectorAttachment.class.getName())||!detector(be.getTubeAttachment(Direction.WEST))||be.getTubeAttachments().size()!=1)throw new IllegalStateException("Native committed attachment/real-item custody differs");
    }
    private void unchangedStock()throws Exception{int last=Files.isRegularFile(file(1,"admitted"))?1:Files.isRegularFile(file(0,"admitted"))?0:-1;JsonObject expected=last<0?initialStock:read(file(last,"debit")).getAsJsonObject("after_stock");if(!expected.equals(snapshot(copies())))throw new IllegalStateException("Actual starter inventory changed outside the admitted real debit; preserve current custody");}
    /** Read-only. Never calls setConnection or recreates a Bezier/filler. */
    public List<Map<String,Object>> retainedLinks()throws Exception{
        check();List<Map<String,Object>> rows=new ArrayList<>();Set<BlockPos> allFillers=new HashSet<>();
        for(int n=0;n<6;n++){
            JsonObject record=partial.getAsJsonArray("native_tube_links").get(n).getAsJsonObject();BlockPos a=new BlockPos(1331,71,-991+n*8),b=a.south(8);
            if(!(level.getBlockEntity(a) instanceof ITubeConnectionEntity from)||!(level.getBlockEntity(b) instanceof ITubeConnectionEntity to))throw new IllegalStateException("Retained native tube endpoint missing");
            var forward=from.getConnectionInDirection(Direction.SOUTH);var backward=to.getConnectionInDirection(Direction.NORTH);
            if(!(forward instanceof BezierConnection curve)||!(backward instanceof SimpleConnection back)||!curve.getUuid().toString().equals(record.get("uuid").getAsString())
                ||!curve.getFromPos().pos().equals(a)||!curve.getToPos().pos().equals(b)||curve.getFromPos().direction()!=Direction.SOUTH||curve.getToPos().direction()!=Direction.SOUTH
                ||!Float.isFinite(curve.getFromPos().offset())||!Float.isFinite(curve.getToPos().offset())||!Float.isFinite(back.offset())
                ||Math.abs(curve.getFromPos().offset()-from.getConnectionOffsetOnDirection(Direction.SOUTH))>.000001||Math.abs(curve.getToPos().offset()+to.getConnectionOffsetOnDirection(Direction.NORTH))>.000001
                ||!back.pos().equals(a)||back.direction()!=Direction.SOUTH||Math.abs(back.offset()-curve.getFromPos().offset())>.000001||!Double.isFinite(curve.distance())||Math.abs(curve.distance()-8)>.000001||!curve.getValidation().valid())throw new IllegalStateException("Retained legitimate reciprocal native Bezier identity/endpoints changed; never reconnect");
            int expected=n==0?1:2;if(from.getConnections().size()!=expected||n==5&&to.getConnections().size()!=1)throw new IllegalStateException("Unknown/extra native tube link preserved");
            var points=curve.getBezierPoints(level,a);Set<BlockPos> fillers=new HashSet<>();
            for(BlockPos cell:TubeCollision.occupiedVolume(points)){
                if(cell.equals(a)||cell.equals(b))continue;
                if(!admittedFillers.contains(cell)||!allFillers.add(cell)||!level.getEntities((Entity)null,new AABB(cell)).isEmpty()
                    ||!(level.getBlockState(cell).getBlock() instanceof TubePathBlock)||!(level.getBlockEntity(cell) instanceof TubePathBlockEntity actual)||!a.equals(actual.owner()))throw new IllegalStateException("Retained native filler/empty travel corridor differs");
                TubePathBlockEntity expectedShape=new TubePathBlockEntity(actual.getType(),cell,actual.getBlockState());expectedShape.bind(a,TubeCollision.boxes(points,cell));
                if(actual.shape().isEmpty()||Shapes.joinIsNotEmpty(actual.shape(),expectedShape.shape(),BooleanOp.NOT_SAME))throw new IllegalStateException("Retained native collision shape differs; no path rewrite");fillers.add(cell);
            }
            if(fillers.size()!=record.get("native_collision_cells").getAsInt())throw new IllegalStateException("Exact retained collision count differs");
            rows.add(Map.of("uuid",curve.getUuid().toString(),"from",List.of(a.getX(),a.getY(),a.getZ()),"to",List.of(b.getX(),b.getY(),b.getZ()),"native_collision_cells",fillers.size(),"existing_link_preserved",true));
        }
        String fingerprint=JSON.toJson(rows);if(originalLinks==null)originalLinks=fingerprint;else if(!originalLinks.equals(fingerprint))throw new IllegalStateException("Native links changed during attachment work");report.put("retained_native_tube_links",rows);return rows;
    }
    public void preflight(boolean driveStopped,boolean stationsReady)throws Exception{
        check();retainedLinks();int missing=0;
        for(int n=0;n<2;n++){
            BlockPos p=ENTRANCES.get(n);ActionTubeBlockEntity be=entrance(p);BlockState state=level.getBlockState(p);BlockPos lever=p.west();BlockState input=level.getBlockState(lever);
            if(!(state.getBlock() instanceof ActionTubeBlock block)||!block.canPlaceAttachment(state,level,p,Direction.WEST)||!input.is(Blocks.LEVER)
                ||input.getValue(BlockStateProperties.ATTACH_FACE)!=net.minecraft.world.level.block.state.properties.AttachFace.FLOOR||input.getValue(BlockStateProperties.HORIZONTAL_FACING)!=Direction.EAST
                ||!level.getEntities((Entity)null,new AABB(p).inflate(2)).isEmpty())throw new IllegalStateException("Exact supported WEST lever face and empty native entrance required");
            if(be.hasAnyTubeAttachment())committed(n,be);else{if(Files.exists(file(n,"intent")))throw new IllegalStateException("Partial/uncertain attachment intent retained; explicit reconciliation required");missing++;}
        }
        int latest=Files.isRegularFile(file(1,"admitted"))?1:Files.isRegularFile(file(0,"admitted"))?0:-1;
        if(latest>=0&&!read(file(latest,"debit")).getAsJsonObject("after_stock").equals(snapshot(copies())))throw new IllegalStateException("Inventory changed after a prior admitted debit; explicit custody reconciliation required");
        report.put("actual_detector_stock",count(ITEM));report.put("missing_owned_detectors",missing);report.put("actual_wheat_stock",count("minecraft:wheat"));report.put("actual_iron_stock",count("minecraft:iron_ingot"));
        boolean wheatStack=false;for(ItemStack value:copies())if(item(value).equals("minecraft:wheat")&&value.getCount()==16)wheatStack=true;report.put("actual_single_16_wheat_stack",wheatStack);
        if(!inspection&&(!driveStopped||!stationsReady||count(ITEM)<missing||count("minecraft:wheat")!=16||!wheatStack||count("minecraft:iron_ingot")<1))throw new IllegalStateException("Stopped real stations, one untouched16-wheat stack and real detector/iron stock required before resume");
    }
    public void installOne(int index)throws Exception{
        check();if(inspection||index<0||index>1)throw new IllegalStateException("Only admitted finite resume can debit/attach");unchangedStock();if(index==1)committed(0,entrance(ENTRANCES.get(0)));retainedLinks();BlockPos pos=ENTRANCES.get(index);ActionTubeBlockEntity be=entrance(pos);
        if(be.hasAnyTubeAttachment()){committed(index,be);return;}if(Files.exists(file(index,"intent")))throw new IllegalStateException("Unresolved debit/add intent must never replay");
        BlockState state=level.getBlockState(pos);if(!(state.getBlock() instanceof ActionTubeBlock block)||!block.canPlaceAttachment(state,level,pos,Direction.WEST))throw new IllegalStateException("Native WEST attachment face refused");
        int slot=-1;ITubeAttachment attachment=null;
        for(int n=0;n<stock.getContainerSize();n++){ItemStack stack=stock.getItem(n);if(item(stack).equals(ITEM)&&stack.getItem() instanceof TubeAttachmentItem nativeItem){ITubeAttachment value=nativeItem.getTubeAttachment();if(!detector(value))throw new IllegalStateException("Actual stocked attachment is not the registered input detector");slot=n;attachment=value;break;}}
        if(slot<0)throw new IllegalStateException("No real stocked detector to debit");List<ItemStack> before=copies();JsonObject beforeJson=snapshot(before);ItemStack expectedItem=before.get(slot).copy();expectedItem.setCount(1);List<ItemStack> expectedAfter=new ArrayList<>();for(ItemStack stack:before)expectedAfter.add(stack.copy());expectedAfter.get(slot).shrink(1);JsonObject afterJson=snapshot(expectedAfter);
        JsonObject intent=new JsonObject();intent.addProperty("format","awft-mill-real-attachment-intent:1");intent.addProperty("contract_sha256",stableContract);intent.addProperty("index",index);intent.addProperty("item",ITEM);intent.addProperty("amount",1);intent.addProperty("slot",slot);intent.addProperty("expected_removed_native_snbt",expectedItem.save(level.registryAccess()).toString());intent.add("entrance",JSON.toJsonTree(List.of(pos.getX(),pos.getY(),pos.getZ())));intent.addProperty("face","west");intent.add("before_stock",beforeJson);intent.add("expected_after_stock",afterJson);durable(file(index,"intent"),intent);
        report.put("resume_inventory_mutation_possible",true);mutation.run();ItemStack removed=stock.removeItem(slot,1);stock.setChanged();
        if(!ItemStack.matches(removed,expectedItem)||!snapshot(copies()).equals(afterJson))throw new IllegalStateException("Real debit readback differs; retain intent and actual inventory, no refund/retry");
        JsonObject debit=new JsonObject();debit.addProperty("intent_sha256",sha(JSON.toJson(intent)));debit.addProperty("actual_removed_native_snbt",removed.save(level.registryAccess()).toString());debit.add("after_stock",afterJson);durable(file(index,"debit"),debit);
        // This is the native BE API used by the real item, after the real debit.
        // Do not call Item.useOn with a null/fake player and do not forge its NBT.
        be.addTubeAttachment(Direction.WEST,attachment);
        if(!detector(be.getTubeAttachment(Direction.WEST))||be.getTubeAttachments().size()!=1||!snapshot(copies()).equals(afterJson))throw new IllegalStateException("Native attachment/inventory readback differs; partial receipt retained");retainedLinks();
        JsonObject done=new JsonObject();done.addProperty("debit_sha256",sha(JSON.toJson(debit)));done.addProperty("native_attachment_id",be.getTubeAttachment(Direction.WEST).getId());done.addProperty("native_attachment_class",be.getTubeAttachment(Direction.WEST).getClass().getName());done.addProperty("finished",Instant.now().toString());durable(file(index,"admitted"),done);
    }
    public void notifyManual()throws Exception{
        check();if(inspection)throw new IllegalStateException("Inspection never changes a lever");unchangedStock();
        for(int n=0;n<2;n++){BlockPos p=ENTRANCES.get(n);ActionTubeBlockEntity be=entrance(p);committed(n,be);BlockState state=level.getBlockState(p);boolean locked=state.getValue(HyperEntranceBlock.LOCKED),powered=state.getValue(ActionTubeBlock.POWERED);
            if(locked!=powered)throw new IllegalStateException("Unexpected native lock/input memory pair; do not toggle toward a guessed state");
            BlockPos lever=p.west();BlockState input=level.getBlockState(lever);if(!input.is(Blocks.LEVER))throw new IllegalStateException("Owned real input lever missing");mutation.run();
            if(!input.getValue(BlockStateProperties.POWERED)&&!level.setBlock(lever,input.setValue(BlockStateProperties.POWERED,true),3))throw new IllegalStateException("Normal real lever ON transition refused");
            level.updateNeighborsAt(lever,input.getBlock()); // Native WEST neighbor event, not a direct entrance-state setter.
        }
    }
    public boolean manualReady()throws Exception{
        check();retainedLinks();boolean ready=true;List<Map<String,Object>> rows=new ArrayList<>();
        for(int n=0;n<2;n++){BlockPos p=ENTRANCES.get(n);ActionTubeBlockEntity be=entrance(p);BlockState state=level.getBlockState(p);ITubeAttachment value=be.getTubeAttachment(Direction.WEST);int signal=level.getSignal(p.west(),Direction.WEST);
            boolean detector=detector(value),locked=state.getValue(HyperEntranceBlock.LOCKED),powered=state.getValue(ActionTubeBlock.POWERED),nonEmit=be.getAttachmentDirectionsNoEmit().equals(List.of(Direction.WEST));boolean lever=level.getBlockState(p.west()).getValue(BlockStateProperties.POWERED);
            rows.add(Map.of("position",List.of(p.getX(),p.getY(),p.getZ()),"west_detector",detector,"native_attachment_id",value==null?"none":value.getId(),"native_input_faces",be.getAttachmentDirectionsNoEmit().stream().map(Direction::getSerializedName).toList(),"west_signal",signal,"lever_powered",lever,"native_powered_memory",powered,"native_manual_locked",locked,"native_output_power",state.getValue(ActionTubeBlock.POWER)));
            ready&=detector&&locked&&powered&&nonEmit&&lever&&signal>0&&state.getValue(ActionTubeBlock.POWER)==0;
        }report.put("native_manual_input_readback",rows);return ready;
    }
    public void intent(String stage)throws Exception{check();if(inspection||!Set.of("feed","assembly").contains(stage))throw new IllegalStateException("Only one admitted feed/assembly transition");if(stage.equals("feed"))unchangedStock();List<ItemStack> after=copies();if(stage.equals("feed")){int wheat=-1,iron=-1;for(int n=0;n<after.size();n++){ItemStack s=after.get(n);if(item(s).equals("minecraft:wheat")&&s.getCount()==16)wheat=n;if(item(s).equals("minecraft:iron_ingot")&&s.getCount()>=1)iron=n;}if(wheat<0||iron<0)throw new IllegalStateException("Actual feed slots changed before intent");after.get(wheat).shrink(16);after.get(iron).shrink(1);}JsonObject value=new JsonObject();value.addProperty("stage",stage);value.addProperty("started",Instant.now().toString());value.add("actual_stock_before",snapshot(copies()));value.add("expected_stock_after",snapshot(after));durable(ledger.resolve(stage+".intent.json"),value);report.put(stage+"_may_have_started",true);}
    public void completed(String stage)throws Exception{check();if(!Set.of("feed","assembly").contains(stage)||!read(ledger.resolve(stage+".intent.json")).getAsJsonObject("expected_stock_after").equals(snapshot(copies())))throw new IllegalStateException("Actual native callback inventory debit differs; preserve intent");JsonObject value=new JsonObject();value.addProperty("stage",stage);value.addProperty("finished",Instant.now().toString());value.addProperty("native_callback_returned",true);durable(ledger.resolve(stage+".completed.json"),value);}
}
