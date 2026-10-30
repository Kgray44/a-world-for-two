package worldfortwo.bridge;

import com.google.gson.Gson;
import com.google.gson.JsonObject;
import com.simibubi.create.Create;
import com.simibubi.create.content.trains.graph.EdgePointType;
import com.simibubi.create.content.trains.graph.TrackGraph;
import com.simibubi.create.content.trains.graph.TrackNode;
import com.simibubi.create.content.trains.station.GlobalStation;
import com.simibubi.create.content.trains.station.StationBlockEntity;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.level.storage.LevelResource;
import java.nio.ByteBuffer;
import java.nio.channels.FileChannel;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.time.Instant;
import java.util.ArrayDeque;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.UUID;

/** Station preflight and finite ledger utilities, no naming mutator.
 * Pinned updateName discovers its graph through world reads; use the ordinary
 * native UI in a separately coordinated window rather than claim a zero-load call.
 * No command, tick hook, ticket, track setter or raw block-entity NBT.
 * Parent authenticates expected identities from its fresh native observation and
 * owns request/JAR/checkpoint admission, ReserveGuard and immutable NativeJournal.
 */
public final class CopperWrenStationNames {
    private static final Gson JSON=new Gson();
    static final BlockPos MILL=new BlockPos(1332,71,-994),HALT=new BlockPos(1332,71,-942);
    private CopperWrenStationNames() {}

    public record Expected(UUID graph,UUID mill,UUID halt,Direction.AxisDirection millDirection,Direction.AxisDirection haltDirection) {
        public Expected {
            if(graph==null||mill==null||halt==null||mill.equals(halt)||millDirection==null||haltDirection==null)
                throw new IllegalArgumentException("Distinct actual graph/station identities and directions required");
        }
    }

    static Path gate(ServerLevel world,ArtisticEngineeringSupport.Lease lease)throws Exception {
        var server=world.getServer();
        if(!server.isSameThread()||lease==null||!lease.valid()||world!=server.overworld()
            ||server.getPort()!=25575||!server.getPlayerList().getPlayers().isEmpty())
            throw new IllegalStateException("Master's exclusive valid empty-world/server-thread lease required");
        Path root=server.getWorldPath(LevelResource.ROOT).toRealPath();
        Path staging=Path.of("D:/A World for Two/staging/world-tests").toRealPath();
        if(!root.startsWith(staging)||root.getNameCount()!=staging.getNameCount()+3
            ||!root.getParent().getFileName().toString().equals("world")||!root.getFileName().toString().equals("RosewaterArtistic"))
            throw new IllegalStateException("Exact private construction save required");
        return root;
    }

    static void durable(ServerLevel world,ArtisticEngineeringSupport.Lease lease,Path file,JsonObject record)throws Exception {
        Path root=gate(world,lease);
        if(!file.toAbsolutePath().normalize().startsWith(root.resolve("data")))throw new IllegalStateException("Owned durable rail ledger required");
        for(Path p=file.getParent();!p.equals(root);p=p.getParent())
            if(Files.exists(p)&&(Files.isSymbolicLink(p)||!p.toRealPath().equals(p.toAbsolutePath().normalize())))
                throw new IllegalStateException("Redirected rail ledger refused");
        byte[] bytes=(JSON.toJson(record)+"\n").getBytes(StandardCharsets.UTF_8);
        if(bytes.length>128*1024)throw new IllegalStateException("Finite rail ledger row exceeded");
        Files.createDirectories(file.getParent());
        try(FileChannel out=FileChannel.open(file,StandardOpenOption.CREATE_NEW,StandardOpenOption.WRITE)) {
            ByteBuffer data=ByteBuffer.wrap(bytes);while(data.hasRemaining())out.write(data);out.force(true);
        }
    }

    static JsonObject record(String stage,String request) {
        if(request==null||!request.matches("[a-f0-9]{64}"))throw new IllegalArgumentException("Exact admitted request digest required");
        JsonObject value=new JsonObject();value.addProperty("format","awft-copper-wren-rail-action:1");
        value.addProperty("stage",stage);value.addProperty("request_sha256",request);value.addProperty("at",Instant.now().toString());return value;
    }

    private static StationBlockEntity station(ServerLevel world,BlockPos position,UUID identity,
            Direction.AxisDirection direction,TrackGraph graph,String name) {
        BlockPos target=new BlockPos(1336,69,position.getZ());
        var chunk=world.getChunkSource().getChunkNow(position.getX()>>4,position.getZ()>>4);
        if(chunk==null
            ||world.getChunkSource().getChunkNow(target.getX()>>4,target.getZ()>>4)==null
            ||!(chunk.getBlockEntities().get(position) instanceof StationBlockEntity be))
            throw new IllegalStateException("Existing native station and target chunks must already be loaded");
        GlobalStation point=be.getStation();
        if(point==null||!point.getId().equals(identity)||graph.getPoint(EdgePointType.STATION,identity)!=point
            ||!point.name.equals(name)||point.assembling||!be.edgePoint.getGlobalPosition().equals(target)
            ||be.edgePoint.getTargetDirection()!=direction||!be.edgePoint.hasValidTrack())
            throw new IllegalStateException("Exact native station/name/target/direction/graph preimage differs");
        return be;
    }

    private static void connected(TrackGraph graph,GlobalStation first,GlobalStation last) {
        if(graph.getNodes().size()>1024)throw new IllegalStateException("Finite native graph-node census exceeded");
        if(first.edgeLocation==null||last.edgeLocation==null)throw new IllegalStateException("Existing station edge locations required");
        TrackNode begin=graph.locateNode(first.edgeLocation.getFirst()),end=graph.locateNode(last.edgeLocation.getFirst());
        if(begin==null||end==null)throw new IllegalStateException("Existing station graph nodes required");
        Set<TrackNode> seen=new HashSet<>();ArrayDeque<TrackNode> todo=new ArrayDeque<>();todo.add(begin);
        while(!todo.isEmpty()) {
            TrackNode node=todo.remove();if(!seen.add(node))continue;
            if(seen.size()>1024||todo.size()>2048)throw new IllegalStateException("Finite graph walk incomplete");
            if(node==end)return;
            var links=graph.getConnectionsFrom(node);
            if(links!=null) {
                if(links.size()>1024)throw new IllegalStateException("Finite native graph-edge census exceeded");
                for(TrackNode next:links.keySet())if(!seen.contains(next)) {
                    if(todo.size()>=2048)throw new IllegalStateException("Finite native graph frontier exceeded");todo.add(next);
                }
            }
        }
        throw new IllegalStateException("Native station graph is disconnected");
    }

    private static void uniqueDestinationNames(TrackGraph graph,GlobalStation mill,GlobalStation halt) {
        var points=graph.getPoints(EdgePointType.STATION);
        if(points.size()>128)throw new IllegalStateException("Finite native station-name census exceeded");
        for(GlobalStation point:points) {
            if(point==null||point.name==null)throw new IllegalStateException("Unknown native station name");
            if((point.name.equals(CopperWrenPassengerSchedule.MILL)&&point!=mill)
                ||(point.name.equals(CopperWrenPassengerSchedule.ORCHARD)&&point!=halt))
                throw new IllegalStateException("Another native station object matches a passenger destination name");
        }
    }

    static TrackGraph namedGraph(ServerLevel world,ArtisticEngineeringSupport.Lease lease,Expected expected)throws Exception {
        gate(world,lease);TrackGraph graph=Create.RAILWAYS.trackNetworks.get(expected.graph());
        if(graph==null||Create.RAILWAYS.trackNetworks.size()>128||Create.RAILWAYS.trains.size()>128)
            throw new IllegalStateException("Existing bounded native station graph required");
        var first=station(world,MILL,expected.mill(),expected.millDirection(),graph,CopperWrenPassengerSchedule.MILL);
        var last=station(world,HALT,expected.halt(),expected.haltDirection(),graph,CopperWrenPassengerSchedule.ORCHARD);
        uniqueDestinationNames(graph,first.getStation(),last.getStation());
        connected(graph,first.getStation(),last.getStation());return graph;
    }

    /** Both old names must still be Track Station. This does not rename them. */
    public static JsonObject inspectForManualRename(ServerLevel world,ArtisticEngineeringSupport.Lease lease,Expected expected,
            String request)throws Exception {
        gate(world,lease);TrackGraph graph=Create.RAILWAYS.trackNetworks.get(expected.graph());
        if(graph==null||Create.RAILWAYS.trains.size()>128)throw new IllegalStateException("Existing bounded native graph required");
        for(var train:Create.RAILWAYS.trains.values())if(train.graph==graph
            &&(!Double.isFinite(train.speed)||Math.abs(train.speed)>.001||train.runtime.getSchedule()!=null))
            throw new IllegalStateException("Do not rename stations used by moving or scheduled trains");
        StationBlockEntity first=station(world,MILL,expected.mill(),expected.millDirection(),graph,"Track Station");
        StationBlockEntity last=station(world,HALT,expected.halt(),expected.haltDirection(),graph,"Track Station");
        GlobalStation a=first.getStation(),b=last.getStation();uniqueDestinationNames(graph,a,b);connected(graph,a,b);
        JsonObject intent=record("names.preflight_only",request);intent.addProperty("graph_uuid",expected.graph().toString());
        intent.addProperty("mill_station_uuid",expected.mill().toString());intent.addProperty("halt_station_uuid",expected.halt().toString());
        intent.addProperty("old_name","Track Station");intent.addProperty("mill_name",CopperWrenPassengerSchedule.MILL);
        intent.addProperty("halt_name",CopperWrenPassengerSchedule.ORCHARD);
        intent.addProperty("mill_target_direction",first.edgePoint.getTargetDirection().name());
        intent.addProperty("halt_target_direction",last.edgePoint.getTargetDirection().name());
        intent.add("mill_target",JSON.toJsonTree(List.of(1336,69,-994)));intent.add("halt_target",JSON.toJsonTree(List.of(1336,69,-942)));
        intent.add("actual_names",JSON.toJsonTree(List.of(a.name,b.name)));
        intent.addProperty("status","manual native station UI rename required; no mutator provided");
        intent.addProperty("native_updateName_calls",0);intent.addProperty("chunk_tickets_added",0);
        intent.addProperty("train_schedule_applied",false);return intent;
    }
}
