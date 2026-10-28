package worldfortwo.bridge;

import com.google.gson.Gson;
import com.hwmods.overpressure.MovingTubeItem;
import com.hwmods.overpressure.PneumaticConnectionBlockEntity;
import com.hwmods.overpressure.PneumaticTubeBlockEntity;
import com.pedrorok.hypertube.core.connection.BezierConnection;
import com.pedrorok.hypertube.core.connection.SimpleConnection;
import com.pedrorok.hypertube.core.connection.interfaces.ITubeConnectionEntity;
import com.pedrorok.hypertube.core.travel.TravelManager;
import com.simibubi.create.Create;
import com.simibubi.create.content.kinetics.base.KineticBlockEntity;
import com.simibubi.create.content.kinetics.millstone.MillstoneBlockEntity;
import com.simibubi.create.content.processing.burner.BlazeBurnerBlockItem;
import com.simibubi.create.content.logistics.chute.ChuteBlockEntity;
import com.simibubi.create.content.logistics.depot.DepotBlockEntity;
import com.simibubi.create.content.trains.entity.CarriageContraptionEntity;
import com.simibubi.create.content.trains.entity.Train;
import com.simibubi.create.content.trains.graph.TrackGraph;
import com.simibubi.create.content.trains.graph.EdgePointType;
import com.simibubi.create.content.trains.graph.TrackNode;
import com.simibubi.create.content.trains.station.StationBlockEntity;
import com.simibubi.create.content.trains.station.GlobalStation;
import com.mojang.brigadier.arguments.StringArgumentType;
import net.minecraft.commands.Commands;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.network.chat.Component;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.Container;
import net.minecraft.world.entity.item.ItemEntity;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.storage.LevelResource;
import net.minecraft.world.phys.AABB;
import net.neoforged.fml.ModList;
import net.neoforged.fml.loading.FMLPaths;
import net.neoforged.neoforge.event.RegisterCommandsEvent;
import net.neoforged.neoforge.items.IItemHandler;
import java.nio.file.Path;
import java.time.Instant;
import java.util.*;
import java.util.function.BooleanSupplier;

/** On-demand native observations. No tick listener, tickets, loads, setters,
 * item transfers, passenger movement, lifecycle repair or acceptance promotion.
 * Parent wiring owns the coordinated read window and the receipt disk forecast.
 */
public final class TransportObservationSupport {
    private static final Gson JSON=new Gson();
    private static final String BOOT=UUID.randomUUID().toString();
    private static final int GRAPH_LIMIT=1024,ITEM_LIMIT=512;
    private static final BlockPos MILL=new BlockPos(1332,71,-994),HALT=new BlockPos(1332,71,-942);
    private final String candidate,bridge;
    private final BooleanSupplier readWindow;
    public TransportObservationSupport(String candidate,String bridge,BooleanSupplier readWindow) {
        this.candidate=Objects.requireNonNull(candidate);this.bridge=Objects.requireNonNull(bridge);
        this.readWindow=Objects.requireNonNull(readWindow);
    }
    public void commands(RegisterCommandsEvent event) {
        event.getDispatcher().register(Commands.literal("awfttransport")
            .requires(s->s.getEntity()==null&&s.hasPermission(4))
            .then(Commands.literal("snapshot").then(Commands.argument("label",StringArgumentType.word()).executes(c->{
                String label=StringArgumentType.getString(c,"label");
                if(!label.matches("[a-z0-9_-]{1,32}"))throw new IllegalArgumentException("Finite observation label required");
                MinecraftServer server=c.getSource().getServer();
                Map<String,Object> report=capture(server,label);
                Path directory=FMLPaths.GAMEDIR.get().resolve("../dashboard/settlement").toAbsolutePath().normalize();
                try{NativeJournal.terminal(directory,"transport-observation",report);}
                catch(Exception e){throw new IllegalStateException("Observation receipt failed; no world mutation",e);}
                c.getSource().sendSuccess(()->Component.literal(JSON.toJson(report)),false);return 1;
            }))));
    }
    private static List<Integer> xyz(BlockPos p){return List.of(p.getX(),p.getY(),p.getZ());}
    private static boolean loaded(ServerLevel world,BlockPos p){return world.getChunkSource().getChunkNow(p.getX()>>4,p.getZ()>>4)!=null;}
    private static Map<String,Object> stack(ItemStack value,int slot) {
        String components=value.getComponentsPatch().toString();
        if(components.length()>4096)throw new IllegalStateException("Stack components exceed finite observation bound");
        return Map.of("slot",slot,"item",BuiltInRegistries.ITEM.getKey(value.getItem()).toString(),
            "count",value.getCount(),"components",components,"plain",value.getComponentsPatch().isEmpty(),
            "native_item_class",value.getItem().getClass().getName(),
            "has_captured_blaze",value.getItem() instanceof BlazeBurnerBlockItem burner&&burner.hasCapturedBlaze());
    }
    private static List<Map<String,Object>> items(IItemHandler inventory) {
        if(inventory.getSlots()>54)throw new IllegalStateException("Unexpected inventory size");
        List<Map<String,Object>> rows=new ArrayList<>();
        for(int n=0;n<inventory.getSlots();n++)if(!inventory.getStackInSlot(n).isEmpty())rows.add(stack(inventory.getStackInSlot(n),n));
        return rows;
    }
    private static Map<String,Object> container(ServerLevel world,String role,BlockPos p) {
        if(!loaded(world,p)||!(world.getBlockEntity(p) instanceof Container inventory)||inventory.getContainerSize()!=27&&inventory.getContainerSize()!=5)
            return Map.of("role",role,"position",xyz(p),"available",false);
        List<Map<String,Object>> rows=new ArrayList<>();
        for(int n=0;n<inventory.getContainerSize();n++)if(!inventory.getItem(n).isEmpty())rows.add(stack(inventory.getItem(n),n));
        return Map.of("role",role,"position",xyz(p),"available",true,"slots",inventory.getContainerSize(),"items",rows);
    }
    private static Map<String,Object> cargo(ServerLevel world) {
        List<Map<String,Object>> stores=new ArrayList<>();
        stores.add(container(world,"starter",new BlockPos(1313,68,-994)));
        stores.add(container(world,"grain",new BlockPos(1315,74,-1000)));
        stores.add(container(world,"hopper",new BlockPos(1315,73,-1000)));
        stores.add(container(world,"dispatch",new BlockPos(1311,68,-1008)));
        BlockPos mill=new BlockPos(1315,71,-1000),chute=new BlockPos(1315,72,-1000),depot=new BlockPos(1320,68,-1000);
        if(loaded(world,mill)&&world.getBlockEntity(mill) instanceof MillstoneBlockEntity be){
            stores.add(Map.of("role","mill_input","position",xyz(mill),"available",true,"items",items(be.inputInv)));
            stores.add(Map.of("role","mill_output","position",xyz(mill),"available",true,"items",items(be.outputInv)));
        }else for(String role:List.of("mill_input","mill_output"))stores.add(Map.of("role",role,"position",xyz(mill),"available",false));
        if(loaded(world,chute)&&world.getBlockEntity(chute) instanceof ChuteBlockEntity be)
            stores.add(Map.of("role","chute","position",xyz(chute),"available",true,"items",be.getItem().isEmpty()?List.of():List.of(stack(be.getItem(),0))));
        else stores.add(Map.of("role","chute","position",xyz(chute),"available",false));
        if(loaded(world,depot)&&world.getBlockEntity(depot) instanceof DepotBlockEntity be)
            stores.add(Map.of("role","depot","position",xyz(depot),"available",true,"items",be.getHeldItem().isEmpty()?List.of():List.of(stack(be.getHeldItem(),0))));
        else stores.add(Map.of("role","depot","position",xyz(depot),"available",false));
        List<BlockPos> tubes=new ArrayList<>(List.of(new BlockPos(1312,71,-1000)));
        for(int z=-1000;z>=-1007;z--)tubes.add(new BlockPos(1311,71,z));
        tubes.add(new BlockPos(1311,70,-1007));tubes.add(new BlockPos(1311,69,-1007));
        Set<MovingTubeItem> moving=Collections.newSetFromMap(new IdentityHashMap<>());boolean aliased=false;
        for(BlockPos p:tubes){
            String role="tube:"+p.getX()+","+p.getY()+","+p.getZ();
            if(!loaded(world,p)||!(world.getBlockEntity(p) instanceof PneumaticTubeBlockEntity be)){
                stores.add(Map.of("role",role,"position",xyz(p),"available",false));continue;
            }
            MovingTubeItem value=be.getMovingItem();List<Map<String,Object>> rows=new ArrayList<>();
            if(value!=null){if(!moving.add(value))aliased=true;else if(!value.stack.isEmpty())rows.add(stack(value.stack,0));}
            Map<String,Object> row=new LinkedHashMap<>();row.put("role",role);row.put("position",xyz(p));row.put("available",true);row.put("items",rows);
            row.put("in_transit",value!=null);if(value!=null){row.put("animation_id",value.animationId);row.put("path_index",value.pathIndex);row.put("waiting_at_destination",value.waitingAtDestination);}
            stores.add(row);
        }
        boolean entityScope=true;
        for(int x=1304>>4;x<=1321>>4;x++)for(int z=-1010>>4;z<=-993>>4;z++){
            long key=net.minecraft.world.level.ChunkPos.asLong(x,z);
            entityScope &= world.getChunkSource().getChunkNow(x,z)!=null&&world.areEntitiesLoaded(key);
        }
        List<Map<String,Object>> dropped=new ArrayList<>();
        if(entityScope)for(ItemEntity entity:world.getEntitiesOfClass(ItemEntity.class,new AABB(1304,66,-1010,1322,77,-992))){
            if(dropped.size()>=ITEM_LIMIT)throw new IllegalStateException("Too many dropped items to observe without truncation");
            dropped.add(Map.of("entity_uuid",entity.getUUID().toString(),"items",List.of(stack(entity.getItem(),0))));
        }
        BlockPos extractor=new BlockPos(1314,71,-1000);Map<String,Object> filter;
        if(loaded(world,extractor)&&world.getBlockEntity(extractor) instanceof PneumaticConnectionBlockEntity be)
            filter=Map.of("available",true,"item",be.getFilter().isEmpty()?"minecraft:air":BuiltInRegistries.ITEM.getKey(be.getFilter().getItem()).toString(),"counted_as_goods",false);
        else filter=Map.of("available",false,"counted_as_goods",false);
        return Map.of("scope","copper_wren_fixed_v1","complete",entityScope&&!aliased&&stores.stream().allMatch(s->Boolean.TRUE.equals(s.get("available"))),
            "stores",stores,"dropped",dropped,"dropped_query_complete",entityScope,"aliased_transit_objects",aliased,"extractor_filter",filter);
    }
    private static Map<String,Object> station(ServerLevel world,BlockPos p) {
        if(!loaded(world,p)||!(world.getBlockEntity(p) instanceof StationBlockEntity be))return Map.of("position",xyz(p),"available",false);
        var point=be.getStation();TrackGraph network=stationGraph(point);
        Map<String,Object> row=new LinkedHashMap<>();row.put("position",xyz(p));row.put("available",true);
        row.put("target",xyz(be.edgePoint.getGlobalPosition()));row.put("direction",be.edgePoint.getTargetDirection().name());
        row.put("valid_track",loaded(world,be.edgePoint.getGlobalPosition())&&be.edgePoint.hasValidTrack());row.put("station_point",point!=null);
        row.put("station_uuid",point==null?null:point.getId().toString());
        row.put("name",point==null?null:point.name);row.put("graph_id",network==null?null:network.id.toString());
        row.put("present_train",point==null||point.getPresentTrain()==null?null:point.getPresentTrain().id.toString());return row;
    }
    private static TrackGraph stationGraph(GlobalStation station) {
        if(station==null||Create.RAILWAYS.trackNetworks.size()>128)return null;
        for(TrackGraph network:Create.RAILWAYS.trackNetworks.values())
            if(network.getPoint(EdgePointType.STATION,station.getId())==station)return network;
        return null;
    }
    private static Map<String,Object> graph(ServerLevel world) {
        if(!loaded(world,MILL)||!loaded(world,HALT)||!(world.getBlockEntity(MILL) instanceof StationBlockEntity a)||!(world.getBlockEntity(HALT) instanceof StationBlockEntity b))return Map.of("status","unavailable");
        GlobalStation first=a.getStation(),last=b.getStation();TrackGraph network=stationGraph(first);
        if(network==null||network!=stationGraph(last)||first.edgeLocation==null||last.edgeLocation==null)return Map.of("status","stations_have_no_shared_graph");
        // Traverse only existing graph memory. Native determineGraphLocation()
        // walks world blocks and can synchronously load a remote chunk.
        TrackNode start=network.locateNode(first.edgeLocation.getFirst()),end=network.locateNode(last.edgeLocation.getFirst());
        if(start==null||end==null)return Map.of("status","native_edge_node_missing");
        Set<TrackNode> seen=new HashSet<>();ArrayDeque<TrackNode> todo=new ArrayDeque<>();todo.add(start);
        while(!todo.isEmpty()){
            TrackNode node=todo.remove();if(!seen.add(node))continue;
            if(seen.size()>GRAPH_LIMIT)return Map.of("status","bounded_graph_walk_incomplete","visited",seen.size());
            if(node==end)return Map.of("status","station_nodes_connected","graph_id",network.id.toString(),"visited",seen.size());
            var links=network.getConnectionsFrom(node);if(links!=null)for(TrackNode next:links.keySet())if(!seen.contains(next))todo.add(next);
            if(todo.size()>GRAPH_LIMIT*2)return Map.of("status","bounded_graph_walk_incomplete","visited",seen.size());
        }
        return Map.of("status","station_nodes_disconnected","visited",seen.size());
    }
    private static List<Map<String,Object>> tubes(ServerLevel world) {
        List<Map<String,Object>> links=new ArrayList<>();
        for(int n=0;n<6;n++){
            BlockPos a=new BlockPos(1331,71,-991+8*n),b=a.south(8);
            if(!loaded(world,a)||!loaded(world,b)||!(world.getBlockEntity(a) instanceof ITubeConnectionEntity from)||!(world.getBlockEntity(b) instanceof ITubeConnectionEntity to)){
                links.add(Map.of("from",xyz(a),"to",xyz(b),"available",false));continue;
            }
            var front=from.getConnectionInDirection(Direction.SOUTH);var back=to.getConnectionInDirection(Direction.NORTH);
            boolean reciprocal=front instanceof BezierConnection curve&&back instanceof SimpleConnection reverse
                &&curve.getFromPos().pos().equals(a)&&curve.getToPos().pos().equals(b)&&reverse.pos().equals(a)
                &&curve.getFromPos().direction()==Direction.SOUTH&&curve.getToPos().direction()==Direction.SOUTH&&reverse.direction()==Direction.SOUTH
                &&Float.isFinite(reverse.offset())&&Math.abs(reverse.offset()-curve.getFromPos().offset())<.000001&&curve.getValidation().valid();
            Map<String,Object> row=new LinkedHashMap<>();row.put("from",xyz(a));row.put("to",xyz(b));row.put("available",true);row.put("stored_reciprocal",reciprocal);
            if(front instanceof BezierConnection curve){row.put("uuid",curve.getUuid().toString());row.put("distance",curve.distance());}
            links.add(row);
        }return links;
    }
    public Map<String,Object> capture(MinecraftServer server,String label) {
        if(!server.isSameThread()||!readWindow.getAsBoolean())throw new IllegalStateException("Master-coordinated native read window required");
        if(!ModList.get().getModContainerById("awft_control_bridge").orElseThrow().getModInfo().getVersion().toString().equals(bridge))
            throw new IllegalStateException("Actual running bridge version differs");
        ServerLevel world=server.overworld();Map<String,Object> report=new LinkedHashMap<>();
        report.put("format","awft-native-transport-observation:1");report.put("label",label);report.put("at",Instant.now().toString());
        report.put("boot_id",BOOT);report.put("pid",ProcessHandle.current().pid());
        report.put("process_started",ProcessHandle.current().info().startInstant().orElseThrow().toString());
        report.put("candidate",candidate);report.put("bridge",bridge);
        report.put("world",server.getWorldPath(LevelResource.ROOT).toAbsolutePath().normalize().toString());report.put("game_time",world.getGameTime());
        List<Map<String,Object>> players=new ArrayList<>();
        for(var player:server.getPlayerList().getPlayers()){
            var vehicle=player.getRootVehicle();Map<String,Object> row=new LinkedHashMap<>();
            row.put("uuid",player.getUUID().toString());row.put("name",player.getGameProfile().getName());row.put("dimension",player.level().dimension().location().toString());
            row.put("position",List.of(player.getX(),player.getY(),player.getZ()));row.put("chunk",List.of(player.chunkPosition().x,player.chunkPosition().z));
            row.put("on_ground",player.onGround());row.put("health",player.getHealth());row.put("hypertube_native_travel",TravelManager.hasHyperTubeData(player));
            row.put("train_uuid",vehicle instanceof CarriageContraptionEntity carriage&&carriage.trainId!=null?carriage.trainId.toString():null);players.add(row);
        }report.put("players",players);
        List<Map<String,Object>> trains=new ArrayList<>();
        if(Create.RAILWAYS.trains.size()>128)throw new IllegalStateException("Train observation bound exceeded");
        for(Train train:Create.RAILWAYS.trains.values()){
            var position=train.getPositionInDimension(world.dimension());if(position.isEmpty())continue;BlockPos p=position.get();
            if(p.getX()<1288||p.getX()>1350||p.getZ()< -1020||p.getZ()> -910)continue;
            Map<String,Object> row=new LinkedHashMap<>();row.put("uuid",train.id.toString());row.put("position",xyz(p));row.put("speed",train.speed);
            row.put("invalid",train.invalid);row.put("derailed",train.derailed);row.put("double_ended",train.doubleEnded);row.put("graph_id",train.graph==null?null:train.graph.id.toString());
            row.put("station",train.getCurrentStation()==null?null:train.getCurrentStation().name);row.put("player_passengers",train.countPlayerPassengers());
            row.put("forward_conductor",train.hasForwardConductor());row.put("backward_conductor",train.hasBackwardConductor());
            row.put("carriages",train.carriages.size());row.put("schedule_present",train.runtime.getSchedule()!=null);row.put("schedule_paused",train.runtime.paused);row.put("schedule_completed",train.runtime.completed);
            row.put("schedule_entry",train.runtime.currentEntry);row.put("schedule_cyclic",train.runtime.getSchedule()!=null&&train.runtime.getSchedule().cyclic);
            String schedule=train.runtime.getSchedule()==null?"":train.runtime.getSchedule().write(world.registryAccess()).toString();
            if(schedule.length()>16384)throw new IllegalStateException("Native schedule exceeds finite observation bound");
            row.put("native_schedule_snbt",schedule);
            row.put("schedule_condition_progress",List.copyOf(train.runtime.conditionProgress));
            List<String> context=train.runtime.conditionContext.stream().map(Object::toString).toList();
            if(context.stream().mapToInt(String::length).sum()>16384)throw new IllegalStateException("Native condition context exceeds finite observation bound");
            row.put("schedule_condition_context",context);
            List<Integer> seats=new ArrayList<>();for(var carriage:train.carriages){var entity=carriage.anyAvailableEntity();seats.add(entity==null||entity.getContraption()==null?-1:entity.getContraption().getSeats().size());}row.put("seats",seats);trains.add(row);
        }report.put("trains",trains);report.put("stations",List.of(station(world,MILL),station(world,HALT)));report.put("track_graph",graph(world));report.put("tube_links",tubes(world));
        List<Map<String,Object>> drives=new ArrayList<>();for(BlockPos p:List.of(new BlockPos(1315,71,-1000),new BlockPos(1320,70,-1000),new BlockPos(1313,71,-1000),new BlockPos(1331,71,-991),new BlockPos(1331,71,-943))){
            if(loaded(world,p)&&world.getBlockEntity(p) instanceof KineticBlockEntity be)drives.add(Map.of("position",xyz(p),"available",true,"rpm",be.getSpeed(),"overstressed",be.isOverStressed(),"needs_update",be.needsSpeedUpdate(),"block_state",world.getBlockState(p).toString()));
            else drives.add(Map.of("position",xyz(p),"available",false));
        }report.put("drives",drives);report.put("cargo",cargo(world));
        report.put("limits","Point observations only. No zipline client tracking/braking, ride continuity, safety, native filler shape, performance delta or owner acceptance is inferred.");
        report.put("world_mutated",false);report.put("owned_tickets",0);return report;
    }
}
