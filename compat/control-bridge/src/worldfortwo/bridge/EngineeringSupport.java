package worldfortwo.bridge;

import com.google.gson.*;
import com.mojang.brigadier.arguments.IntegerArgumentType;
import com.mojang.brigadier.arguments.StringArgumentType;
import net.minecraft.commands.Commands;
import net.minecraft.core.BlockPos;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.network.chat.Component;
import net.minecraft.nbt.Tag;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.TicketType;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.ButtonBlock;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.storage.LevelResource;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.Vec3;
import net.minecraft.world.item.ItemStack;
import net.minecraft.resources.ResourceLocation;
import net.neoforged.fml.loading.FMLPaths;
import net.neoforged.neoforge.event.RegisterCommandsEvent;

import java.lang.reflect.Field;
import java.nio.file.*;
import java.security.MessageDigest;
import java.time.Instant;
import java.util.*;

/** Bounded commissioning of owner-authored Create systems, through their real native APIs.
 * Never fabricates RPM, changes kinetic speed, teleports a player or animates a fake bridge.
 * Operational power, gearing, radio links, sequencers and bearings remain Create's own.
 */
public final class EngineeringSupport {
    private static final Gson JSON=new Gson();
    private static final TicketType<ChunkPos> TICKET=TicketType.create("awft_commission",Comparator.comparingLong(ChunkPos::toLong));
    private final Path directory=FMLPaths.GAMEDIR.get().resolve("../dashboard/settlement").toAbsolutePath().normalize();
    private final List<ChunkPos> tickets=new ArrayList<>();
    private final Map<String,Object> report=new LinkedHashMap<>();
    private final List<Object> observations=new ArrayList<>();
    private ServerLevel level;
    private JsonObject plan;
    private String mode="idle";
    private int phase, elapsed, phaseTicks, cycles, readySamples;
    private long nextWrite;

    public void commands(RegisterCommandsEvent event){
        var root=Commands.literal("awftengine").requires(s->s.getEntity()==null && s.hasPermission(4));
        for(String action:List.of("setup","commission","close"))root.then(Commands.literal(action)
            .then(Commands.argument("sha256",StringArgumentType.word()).executes(c->{
                try {admit(c.getSource().getServer(),action,StringArgumentType.getString(c,"sha256"));return 1;}
                catch(Exception error){throw new RuntimeException(error);}
            })));
        root.then(Commands.literal("inspect").then(Commands.argument("x",IntegerArgumentType.integer(-25000000,25000000))
            .then(Commands.argument("y",IntegerArgumentType.integer(-64,319))
            .then(Commands.argument("z",IntegerArgumentType.integer(-25000000,25000000)).executes(c->{
                try {
                    ServerLevel world=c.getSource().getServer().overworld();
                    BlockPos pos=new BlockPos(IntegerArgumentType.getInteger(c,"x"),IntegerArgumentType.getInteger(c,"y"),IntegerArgumentType.getInteger(c,"z"));
                    if(world.getChunkSource().getChunkNow(pos.getX()>>4,pos.getZ()>>4)==null)throw new IllegalStateException("Inspect only loaded chunks");
                    write("engineering-inspection.json",inspect(world,pos));
                    c.getSource().sendSuccess(()->Component.literal("AWFT native engineering inspection saved"),true);return 1;
                }catch(Exception error){throw new RuntimeException(error);}
            })))));
        root.then(Commands.literal("status").executes(c->{c.getSource().sendSuccess(()->Component.literal(JSON.toJson(report)),true);return 1;}));
        root.then(Commands.literal("cancel").executes(c->{
            finish(mode.equals("cleanup_required")?"explicit temporary-ticket cleanup retry; native mechanisms preserved":"cancelled; native mechanisms and work preserved");
            return 1;
        }));
        event.getDispatcher().register(root);
    }

    private BlockPos pos(JsonArray a){
        if(a.size()!=3)throw new IllegalArgumentException("Expected one exact block position");
        int x=a.get(0).getAsInt(),y=a.get(1).getAsInt(),z=a.get(2).getAsInt();
        if(Math.abs(x)>25000000 || Math.abs(z)>25000000 || y < -64 || y>=320)throw new IllegalArgumentException("Position outside bounds");
        return new BlockPos(x,y,z);
    }
    private Object invoke(Object target,String name)throws Exception{return target.getClass().getMethod(name).invoke(target);}
    private BlockEntity required(JsonObject system,String name,String expected){
        BlockEntity entity=level.getBlockEntity(pos(system.getAsJsonArray(name)));
        if(entity==null || !entity.getClass().getName().equals(expected))throw new IllegalStateException("Expected native "+expected+" at "+name);
        return entity;
    }
    private void admit(MinecraftServer server,String action,String expected)throws Exception{
        if(!mode.equals("idle") || !tickets.isEmpty() || level!=null || !expected.matches("[a-f0-9]{64}") || !server.getPlayerList().getPlayers().isEmpty())throw new IllegalStateException("An empty server and idle commissioning tool with no pending ticket cleanup are required");
        Path source=directory.resolve("engineering-plan.json");
        if(Files.isSymbolicLink(source) || Files.size(source)>256*1024)throw new IllegalStateException("Commissioning plan exceeds bound");
        byte[] raw=Files.readAllBytes(source);
        String sha=HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(raw));
        if(!sha.equals(expected))throw new IllegalStateException("Exact commissioning-plan hash differs");
        JsonObject candidate=JsonParser.parseString(new String(raw,java.nio.charset.StandardCharsets.UTF_8)).getAsJsonObject();
        if(!candidate.get("seed").getAsString().equals(Long.toString(server.overworld().getSeed())) ||
           !Path.of(candidate.get("world_path").getAsString()).toAbsolutePath().normalize().equals(server.getWorldPath(LevelResource.ROOT).toAbsolutePath().normalize()))throw new IllegalStateException("Wrong permanent world");
        JsonObject backup=JsonParser.parseString(Files.readString(directory.resolve("backup-receipt.json"))).getAsJsonObject();
        if(!backup.get("verified").getAsBoolean() || !backup.get("sha256").getAsString().equals(candidate.get("backup_sha256").getAsString()))throw new IllegalStateException("Verified pre-construction backup required");
        String construction=candidate.get("construction_sha256").getAsString();
        if(!construction.matches("[a-f0-9]{64}"))throw new IllegalStateException("Construction proof is required");
        JsonObject proof=JsonParser.parseString(Files.readString(directory.resolve("drawbridge-block-verification.json"))).getAsJsonObject();
        if(!proof.get("plan_sha256").getAsString().equals(construction) || proof.get("failures").getAsInt()!=0 || !proof.has("finished"))throw new IllegalStateException("Exact physical construction has not passed native verification");
        JsonArray systems=candidate.getAsJsonArray("systems"),buttons=candidate.getAsJsonArray("buttons");
        if(systems.size()<1 || systems.size()>4 || buttons.size()<1 || buttons.size()>4)throw new IllegalStateException("Commissioning bound exceeded");
        Set<ChunkPos> chunks=new LinkedHashSet<>();
        for(JsonElement e:systems){
            JsonObject system=e.getAsJsonObject();
            int angle=system.get("open_angle_degrees").getAsInt();
            int signed=system.get("open_negative").getAsBoolean()?-angle:angle;
            if(angle<45 || angle>60 || candidate.get("open_angle_degrees").getAsInt()!=angle ||
               system.get("expected_open_angle").getAsInt()!=signed)throw new IllegalStateException("Reviewed opposed bridge opening must remain within 45 to 60 degrees");
            for(String key:List.of("bearing","sequencer","wheel")){BlockPos p=pos(system.getAsJsonArray(key));chunks.add(new ChunkPos(p));}
            BlockPos min=pos(system.getAsJsonArray("glue_min")),max=pos(system.getAsJsonArray("glue_max"));
            int dx=max.getX()-min.getX()+1,dy=max.getY()-min.getY()+1,dz=max.getZ()-min.getZ()+1;
            if(dx<1 || dy<1 || dz<1 || dx>64 || dy>64 || dz>64 || (long)dx*dy*dz>20000)throw new IllegalStateException("Glue exceeds one reviewed bridge leaf");
            for(int x=min.getX()>>4;x<=max.getX()>>4;x++)for(int z=min.getZ()>>4;z<=max.getZ()>>4;z++)chunks.add(new ChunkPos(x,z));
        }
        for(JsonElement b:buttons)chunks.add(new ChunkPos(pos(b.getAsJsonArray())));
        JsonArray radios=candidate.getAsJsonArray("radios");
        if(radios==null || radios.size()<2 || radios.size()>8)throw new IllegalStateException("Declare the bounded native radio controls");
        for(JsonElement r:radios){
            JsonObject radio=r.getAsJsonObject();chunks.add(new ChunkPos(pos(radio.getAsJsonArray("position"))));
            for(String slot:List.of("first","last"))if(!BuiltInRegistries.ITEM.containsKey(ResourceLocation.parse(radio.get(slot).getAsString())))throw new IllegalStateException("Unknown native radio frequency item");
        }
        if(chunks.size()>32)throw new IllegalStateException("Commissioning chunk bound exceeded");
        level=server.overworld();plan=candidate;mode=action;phase=elapsed=phaseTicks=cycles=readySamples=0;
        report.clear();observations.clear();report.put("operation",action);report.put("started",Instant.now().toString());report.put("plan_sha256",sha);report.put("status","loading temporary simulation tickets");
        // NeoForge distinguishes loading a chunk from forcing its simulation when
        // no player is nearby. Commissioning needs actual BE ticks, not just FULL
        // chunks. This flag is temporary and removed with the identical ticket.
        report.put("temporary_forced_simulation",true);report.put("temporary_tickets_released",0);
        report.put("cleanup_required",false);
        try{
            for(ChunkPos chunk:chunks){
                // Keep the identical handle even if native admission throws
                // after partially adding a ticket. Cleanup must attempt it.
                tickets.add(chunk);report.put("temporary_tickets",tickets.size());simulationTicket(chunk,true);
            }
            NativeJournal.progress(directory,"engineering-status.json",report);
        }catch(Exception error){
            report.put("error",error.toString());finish("temporary-ticket admission failed; native state preserved");throw error;
        }
    }

    private void simulationTicket(ChunkPos chunk,boolean add)throws Exception{
        Object cache=level.getChunkSource();
        cache.getClass().getMethod(add?"addRegionTicket":"removeRegionTicket",TicketType.class,ChunkPos.class,int.class,Object.class,boolean.class)
            .invoke(cache,TICKET,chunk,2,chunk,true);
    }

    private Object link(BlockEntity entity)throws Exception{
        if(entity==null || !entity.getClass().getName().equals("com.simibubi.create.content.redstone.link.RedstoneLinkBlockEntity"))throw new IllegalStateException("Expected native Create redstone link");
        Field f=entity.getClass().getDeclaredField("link");f.setAccessible(true);return f.get(entity);
    }
    private void configureRadios()throws Exception{
        for(JsonElement e:plan.getAsJsonArray("radios")){
            JsonObject radio=e.getAsJsonObject();BlockEntity entity=level.getBlockEntity(pos(radio.getAsJsonArray("position")));
            Object behaviour=link(entity);
            // Item assignment uses Create's own network lifecycle, as its wrench/UI does.
            // Direct NBT loading changes stored items without moving an initialized link
            // between frequency networks. No signal strength or kinetic speed is assigned.
            invoke(behaviour,"unload");
            for(String slot:List.of("first","last")){
                ItemStack stack=new ItemStack(BuiltInRegistries.ITEM.get(ResourceLocation.parse(radio.get(slot).getAsString())));
                behaviour.getClass().getMethod("setFrequency",boolean.class,ItemStack.class).invoke(behaviour,slot.equals("first"),stack);
            }
            invoke(behaviour,"initialize");entity.setChanged();
        }
    }

    @SuppressWarnings({"rawtypes","unchecked"})
    private void setup(JsonObject system)throws Exception{
        BlockEntity bearing=required(system,"bearing","com.simibubi.create.content.contraptions.bearing.MechanicalBearingBlockEntity");
        if(Boolean.TRUE.equals(invoke(bearing,"isRunning")))throw new IllegalStateException("Commissioning setup cannot alter a running bearing");
        BlockPos min=pos(system.getAsJsonArray("glue_min")),max=pos(system.getAsJsonArray("glue_max"));
        AABB box=new AABB(min.getX(),min.getY(),min.getZ(),max.getX()+1,max.getY()+1,max.getZ()+1);
        UUID uuid=UUID.nameUUIDFromBytes((plan.get("seed").getAsString()+":"+system.get("name").getAsString()+":glue").getBytes(java.nio.charset.StandardCharsets.UTF_8));
        Entity glue=level.getEntity(uuid);
        if(glue==null){
            Class<?> type=Class.forName("com.simibubi.create.content.contraptions.glue.SuperGlueEntity");
            glue=(Entity)type.getConstructor(Level.class,AABB.class).newInstance(level,box);glue.setUUID(uuid);
            if(!level.addFreshEntity(glue))throw new IllegalStateException("Native glue entity was refused");
        }else if(!glue.getClass().getName().equals("com.simibubi.create.content.contraptions.glue.SuperGlueEntity") || !glue.getBoundingBox().equals(box))throw new IllegalStateException("Existing glue UUID or bounds differ");
        Field field=bearing.getClass().getDeclaredField("movementMode");field.setAccessible(true);
        Object behaviour=field.get(bearing);behaviour.getClass().getMethod("setValue",int.class).invoke(behaviour,1);
        BlockEntity gear=required(system,"sequencer","com.simibubi.create.content.kinetics.transmission.sequencer.SequencedGearshiftBlockEntity");
        if(!Boolean.TRUE.equals(invoke(gear,"isIdle")))throw new IllegalStateException("Sequencer is already active");
        Class<? extends Enum> instructions=(Class<? extends Enum>)Class.forName("com.simibubi.create.content.kinetics.transmission.sequencer.SequencerInstructions");
        Class<? extends Enum> modifiers=(Class<? extends Enum>)Class.forName("com.simibubi.create.content.kinetics.transmission.sequencer.InstructionSpeedModifiers");
        Class<?> instruction=Class.forName("com.simibubi.create.content.kinetics.transmission.sequencer.Instruction");
        var ctor=instruction.getConstructor(instructions,modifiers,int.class);
        List values=(List)invoke(gear,"getInstructions");values.clear();
        boolean negative=system.get("open_negative").getAsBoolean();
        int angle=system.get("open_angle_degrees").getAsInt();
        values.add(ctor.newInstance(Enum.valueOf(instructions,"TURN_ANGLE"),Enum.valueOf(modifiers,negative?"BACK":"FORWARD"),angle));
        values.add(ctor.newInstance(Enum.valueOf(instructions,"AWAIT"),Enum.valueOf(modifiers,"FORWARD"),1));
        values.add(ctor.newInstance(Enum.valueOf(instructions,"TURN_ANGLE"),Enum.valueOf(modifiers,negative?"FORWARD":"BACK"),angle));
        values.add(ctor.newInstance(Enum.valueOf(instructions,"END"),Enum.valueOf(modifiers,"FORWARD"),1));
        bearing.setChanged();gear.setChanged();
        BlockEntity wheel=required(system,"wheel","com.simibubi.create.content.kinetics.waterwheel.WaterWheelBlockEntity");
        invoke(wheel,"determineAndApplyFlowScore");
        // Notify real block/neighbour logic; Create determines the resulting network speed.
        level.updateNeighborsAt(wheel.getBlockPos(),wheel.getBlockState().getBlock());
    }

    private Map<String,Object> inspect(ServerLevel world,BlockPos pos)throws Exception{
        Map<String,Object> row=new LinkedHashMap<>();row.put("position",List.of(pos.getX(),pos.getY(),pos.getZ()));
        row.put("block",BuiltInRegistries.BLOCK.getKey(world.getBlockState(pos).getBlock()).toString());
        row.put("state",world.getBlockState(pos).toString());row.put("at",Instant.now().toString());
        long chunk=ChunkPos.asLong(pos);
        row.put("block_ticking",world.getChunkSource().isPositionTicking(chunk));
        row.put("entity_ticking",world.isPositionEntityTicking(pos));row.put("entities_loaded",world.areEntitiesLoaded(chunk));
        BlockEntity entity=world.getBlockEntity(pos);
        if(entity!=null){
            row.put("type",entity.getClass().getName());row.put("nbt",entity.saveWithFullMetadata(world.registryAccess()).toString());
            if(entity.getClass().getName().equals("com.simibubi.create.content.kinetics.transmission.sequencer.SequencedGearshiftBlockEntity")){
                var data=entity.saveWithFullMetadata(world.registryAccess());
                var instructions=data.getList("Instructions",Tag.TAG_COMPOUND);
                int index=data.getInt("InstructionIndex");
                String type=index>=0 && index<instructions.size()?instructions.getCompound(index).getString("Type"):"IDLE";
                row.put("instruction_index",index);row.put("instruction_type",type);
                row.put("awaiting_input",type.equals("AWAIT"));row.put("previous_powered",data.getBoolean("PrevPowered"));
                if(instructions.size()==4){
                    var first=instructions.getCompound(0);var last=instructions.getCompound(2);
                    int degrees=first.getInt("Value");String modifier=first.getString("Modifier");
                    boolean negative=modifier.equals("BACK");
                    row.put("program_open_degrees",degrees);row.put("program_open_negative",negative);
                    row.put("program_reversible",degrees>=45 && degrees<=90 && first.getString("Type").equals("TURN_ANGLE") &&
                        instructions.getCompound(1).getString("Type").equals("AWAIT") && last.getString("Type").equals("TURN_ANGLE") &&
                        last.getInt("Value")==degrees && (negative || modifier.equals("FORWARD")) &&
                        last.getString("Modifier").equals(negative?"FORWARD":"BACK") && instructions.getCompound(3).getString("Type").equals("END"));
                }
            }
            for(String name:List.of("getSpeed","getGeneratedSpeed","isOverStressed","isRunning","isIdle","needsSpeedUpdate")){
                try{row.put(name,invoke(entity,name));}catch(NoSuchMethodException ignored){}
            }
            try{
                row.put("angle",entity.getClass().getMethod("getInterpolatedAngle",float.class).invoke(entity,1f));
                Object moved=invoke(entity,"getMovedContraption");
                row.put("contraption_attached",moved!=null);
                if(moved!=null){
                    if(moved instanceof Entity moving){
                        row.put("contraption_alive",moving.isAlive());row.put("contraption_ticks",moving.tickCount);
                        row.put("contraption_entity_ticking",world.isPositionEntityTicking(moving.blockPosition()));
                    }
                    Object contraption=invoke(moved,"getContraption");Map<?,?> blocks=(Map<?,?>)invoke(contraption,"getBlocks");row.put("contraption_blocks",blocks.size());
                    // Measure the actual transformed deck, not merely a bearing's angle.
                    double minY=Double.POSITIVE_INFINITY,maxY=Double.NEGATIVE_INFINITY,maxZ=-Double.MAX_VALUE,minZ=Double.MAX_VALUE;
                    for(Object key:blocks.keySet()){
                        Vec3 v=(Vec3)moved.getClass().getMethod("toGlobalVector",Vec3.class,float.class).invoke(moved,Vec3.atCenterOf((BlockPos)key),1f);
                        minY=Math.min(minY,v.y);maxY=Math.max(maxY,v.y);minZ=Math.min(minZ,v.z);maxZ=Math.max(maxZ,v.z);
                    }
                    row.put("actual_min_y",minY);row.put("actual_max_y",maxY);row.put("actual_z_bounds",List.of(minZ,maxZ));
                }
            }catch(NoSuchMethodException ignored){}
            if(entity.getClass().getName().equals("com.simibubi.create.content.redstone.link.RedstoneLinkBlockEntity")){
                Object behaviour=link(entity);
                for(String name:List.of("getNetworkKey","isListening","isAlive","getTransmittedStrength"))row.put(name,String.valueOf(invoke(behaviour,name)));
                row.put("newPosition",behaviour.getClass().getField("newPosition").get(behaviour));
                Object handler=Class.forName("com.simibubi.create.Create").getField("REDSTONE_LINK_NETWORK_HANDLER").get(null);
                Class<?> linkType=Class.forName("com.simibubi.create.content.redstone.link.IRedstoneLinkable");
                Set<?> network=(Set<?>)handler.getClass().getMethod("getNetworkOf",net.minecraft.world.level.LevelAccessor.class,linkType).invoke(handler,world,behaviour);
                List<Object> members=new ArrayList<>();
                for(Object member:network)members.add(Map.of("position",String.valueOf(invoke(member,"getLocation")),"alive",String.valueOf(invoke(member,"isAlive")),"listening",String.valueOf(invoke(member,"isListening")),"signal",String.valueOf(invoke(member,"getTransmittedStrength"))));
                row.put("native_network",members);
            }
        }
        return row;
    }
    private void pulse(int index,boolean open,boolean recovery)throws Exception{
        // Inspect again in this server tick, immediately before a real input.
        // Never leave a latched input waiting for a powerless/stressed network.
        var values=snapshot();report.put("systems",values);
        if(!position(values,open,recovery))throw new IllegalStateException("Native phase, sequencer input power or stress changed before the button input; no pulse sent");
        BlockPos pos=pos(plan.getAsJsonArray("buttons").get(index).getAsJsonArray());
        var state=level.getBlockState(pos);
        if(!(state.getBlock() instanceof ButtonBlock button))throw new IllegalStateException("The declared control is not a real button");
        if(state.getValue(ButtonBlock.POWERED))throw new IllegalStateException("Wait for the native button to release");
        button.press(state,level,pos,null);
    }
    private List<Map<String,Object>> snapshot()throws Exception{
        List<Map<String,Object>> values=new ArrayList<>();
        for(JsonElement e:plan.getAsJsonArray("systems")){
            JsonObject s=e.getAsJsonObject();Map<String,Object> v=new LinkedHashMap<>();v.put("name",s.get("name").getAsString());
            for(String key:List.of("bearing","sequencer","wheel"))v.put(key,inspect(level,pos(s.getAsJsonArray(key))));
            values.add(v);
        }
        return values;
    }
    private List<Object> radios()throws Exception{
        List<Object> values=new ArrayList<>();
        for(JsonElement e:plan.getAsJsonArray("radios"))values.add(inspect(level,pos(e.getAsJsonObject().getAsJsonArray("position"))));
        return values;
    }
    @SuppressWarnings("unchecked")
    private List<Object> unreadySystems(List<Map<String,Object>> values){
        List<Object> pending=new ArrayList<>();
        for(Map<String,Object> value:values){
            for(String key:List.of("bearing","sequencer","wheel")){
                Map<String,Object> component=(Map<String,Object>)value.get(key);
                if(!BridgePhaseGate.simulationReady(Boolean.TRUE.equals(component.get("block_ticking")),
                    Boolean.TRUE.equals(component.get("entity_ticking")),Boolean.TRUE.equals(component.get("entities_loaded")),
                    !Boolean.FALSE.equals(component.get("needsSpeedUpdate")))){
                    Map<String,Object> why=new LinkedHashMap<>();why.put("name",value.get("name"));why.put("component",key);
                    for(String field:List.of("block_ticking","entity_ticking","entities_loaded","needsSpeedUpdate"))why.put(field,component.get(field));
                    pending.add(why);
                }
            }
            Map<String,Object> bearing=(Map<String,Object>)value.get("bearing");
            if(!BridgePhaseGate.attachmentReady(Boolean.TRUE.equals(bearing.get("isRunning")),
                Boolean.TRUE.equals(bearing.get("contraption_attached")),Boolean.TRUE.equals(bearing.get("contraption_alive")),
                Boolean.TRUE.equals(bearing.get("contraption_entity_ticking")),((Number)bearing.getOrDefault("contraption_ticks",0)).intValue(),
                ((Number)bearing.getOrDefault("contraption_blocks",0)).intValue(),
                ((Number)bearing.getOrDefault("actual_min_y",Double.NaN)).doubleValue(),
                ((Number)bearing.getOrDefault("actual_max_y",Double.NaN)).doubleValue())){
                Map<String,Object> why=new LinkedHashMap<>();why.put("name",value.get("name"));why.put("component","native contraption attachment");
                for(String field:List.of("isRunning","contraption_attached","contraption_alive","contraption_entity_ticking","contraption_ticks","contraption_blocks"))why.put(field,bearing.get(field));
                pending.add(why);
            }
        }
        return pending;
    }
    @SuppressWarnings("unchecked")
    private boolean position(List<Map<String,Object>> values,boolean open,boolean recovery){
        if(values.size()!=plan.getAsJsonArray("systems").size() || !unreadySystems(values).isEmpty())return false;
        int i=0;
        for(Map<String,Object> value:values){
            JsonObject system=plan.getAsJsonArray("systems").get(i++).getAsJsonObject();
            Map<String,Object> bearing=(Map<String,Object>)value.get("bearing");
            Map<String,Object> gear=(Map<String,Object>)value.get("sequencer");
            if(!(bearing.get("angle") instanceof Number number))return false;
            double degrees=recovery?((Number)gear.getOrDefault("program_open_degrees",0)).doubleValue():system.get("open_angle_degrees").getAsDouble();
            double target=system.get("open_negative").getAsBoolean()?-degrees:degrees;
            if(open){
                if(!Boolean.TRUE.equals(gear.get("program_reversible")) ||
                   !Boolean.valueOf(system.get("open_negative").getAsBoolean()).equals(gear.get("program_open_negative")) ||
                   Math.abs(((Number)gear.getOrDefault("program_open_degrees",0)).doubleValue()-degrees)>.01)return false;
                int length=pos(system.getAsJsonArray("glue_max")).getZ()-pos(system.getAsJsonArray("glue_min")).getZ()+1;
                double minimumTop=pos(system.getAsJsonArray("bearing")).getY()+Math.max(2,(length-2)*Math.sin(Math.toRadians(degrees)))-1;
                if(((Number)bearing.getOrDefault("actual_min_y",-100)).doubleValue()<68 ||
                   ((Number)bearing.getOrDefault("actual_max_y",0)).doubleValue()<minimumTop)return false;
            }
            if(!BridgePhaseGate.ready(number.doubleValue(),target,open,Boolean.TRUE.equals(bearing.get("isRunning")),
                ((Number)bearing.getOrDefault("getSpeed",Double.NaN)).doubleValue(),
                ((Number)gear.getOrDefault("getSpeed",Double.NaN)).doubleValue(),
                !Boolean.FALSE.equals(gear.get("isOverStressed")),!Boolean.FALSE.equals(bearing.get("isOverStressed")),
                Boolean.TRUE.equals(gear.get("awaiting_input")),
                Boolean.TRUE.equals(gear.get("isIdle")),Boolean.TRUE.equals(gear.get("previous_powered")),
                ((Number)bearing.getOrDefault("contraption_blocks",0)).intValue()))return false;
        }
        for(JsonElement button:plan.getAsJsonArray("buttons"))if(level.getBlockState(pos(button.getAsJsonArray())).getValue(ButtonBlock.POWERED))return false;
        return true;
    }
    public void tick(MinecraftServer server){
        // A failed release retains its exact ChunkPos handles and ServerLevel.
        // Only an explicit console cancel retries cleanup; do not wake idle
        // simulation or publish another journal on every tick while blocked.
        if(mode.equals("idle") || mode.equals("cleanup_required"))return;
        if(!server.getPlayerList().getPlayers().isEmpty()){finish("paused because a real player joined; native state preserved");return;}
        elapsed++;phaseTicks++;
        try{
            // Vanilla suspends entity and block-entity ticks after 300 empty
            // ticks, even if custom tickets kept chunks loaded. Wake only this
            // bounded commissioning operation; normal empty-world idling resumes.
            level.resetEmptyTime();
            if(elapsed>3600)throw new IllegalStateException("Three-minute commissioning timeout; native state retained");
            if(phase==0){
                if(phaseTicks%10!=0)return;
                List<Object> pendingChunks=new ArrayList<>();
                for(ChunkPos chunk:tickets){
                    boolean full=level.getChunkSource().getChunkNow(chunk.x,chunk.z)!=null;
                    boolean blockTicking=level.getChunkSource().isPositionTicking(chunk.toLong());
                    boolean entitiesLoaded=level.areEntitiesLoaded(chunk.toLong());
                    boolean entityTicking=level.isPositionEntityTicking(new BlockPos(chunk.getMiddleBlockX(),64,chunk.getMiddleBlockZ()));
                    if(!full || !blockTicking || !entitiesLoaded || !entityTicking)pendingChunks.add(Map.of("x",chunk.x,"z",chunk.z,
                        "full",full,"block_ticking",blockTicking,"entities_loaded",entitiesLoaded,"entity_ticking",entityTicking));
                }
                // Create 6.0.10 restores Running/Angle from bearing NBT, but
                // ControlledContraptionEntity attaches itself only in its real
                // entity tick. FULL chunks and a fixed delay cannot prove that.
                List<Object> pendingSystems=new ArrayList<>();
                if(pendingChunks.isEmpty()){
                    var values=snapshot();report.put("systems",values);pendingSystems=unreadySystems(values);
                }
                boolean nativeReady=pendingChunks.isEmpty() && pendingSystems.isEmpty();
                readySamples=nativeReady?readySamples+1:0;
                report.put("native_readiness",Map.of("pending_chunks",pendingChunks,"pending_components",pendingSystems,"consecutive_ready_samples",readySamples));
                if(phaseTicks>600)throw new IllegalStateException("Native entity loading, ticking, kinetic initialization or contraption attachment did not become ready within 600 ticks; no input sent");
                if(readySamples<2){report.put("status","waiting for concrete native simulation and attachment readiness");progress();return;}
                readySamples=0;
                report.put("status","native simulation and controller attachment ready; "+mode+" in progress");
                if(mode.equals("setup")){for(JsonElement e:plan.getAsJsonArray("systems"))setup(e.getAsJsonObject());configureRadios();phase=1;phaseTicks=0;}
                else {
                    var values=snapshot();
                    observations.add(Map.of("at",Instant.now().toString(),"stage","before","systems",values,"radios",radios()));
                    if(mode.equals("close")){
                        if(position(values,false,false)){report.put("systems",values);finish("native spans already closed and idle; no input sent");return;}
                        if(!position(values,true,true))throw new IllegalStateException("Safe recovery requires both real spans stopped at the matching reversible program's AWAIT instruction");
                        pulse(1,true,true);phase=3;
                    }else{
                        if(!position(values,false,false))throw new IllegalStateException("Begin cycle checks only with closed, disassembled, idle native spans");
                        pulse(0,false,false);phase=2;
                    }
                    phaseTicks=readySamples=0;
                }
            }else if(phase==1 && phaseTicks>=60){report.put("systems",snapshot());finish("native glue and real sequencer programs configured; operation not yet accepted");return;}
            else if(phase==2 || phase==3){
                if(phaseTicks%10!=0)return;
                var values=snapshot();report.put("systems",values);
                if(phaseTicks==10 || phaseTicks==30)observations.add(Map.of("at",Instant.now().toString(),"stage","button signal","radios",radios()));
                boolean open=phase==2;
                boolean ready=phaseTicks>60 && position(values,open,false);
                readySamples=ready?readySamples+1:0;
                if(readySamples>=2){
                    observations.add(Map.of("at",Instant.now().toString(),"stage",open?"open":"closed","systems",values));
                    readySamples=0;
                    if(open){pulse(1,true,false);phase=3;phaseTicks=0;}
                    else if(mode.equals("close")){finish("native button returned both previously open spans to closed, disassembled and idle; no program or angle was fabricated");return;}
                    else {cycles++;report.put("cycles",cycles);if(cycles>=2){finish("two native button-driven open/close cycles passed at the reviewed angle; persistence and ship clearance remain separate");return;}pulse(0,false,false);phase=2;phaseTicks=0;}
                }else if(phaseTicks>1200)throw new IllegalStateException("Native "+(open?"opening":"closing")+" did not reach the required angle");
            }
            progress();
        }catch(Exception error){report.put("error",error.toString());finish("commissioning failed; exact native state and observations preserved");}
    }
    private void progress()throws Exception{
        if(System.nanoTime()>nextWrite){report.put("phase",phase);report.put("ticks",elapsed);report.put("observations",observations);NativeJournal.progress(directory,"engineering-status.json",report);nextWrite=System.nanoTime()+2_000_000_000L;}
    }
    private void finish(String status){
        report.put("status",status);report.put("finished",Instant.now().toString());report.put("observations",observations);
        int released=((Number)report.getOrDefault("temporary_tickets_released",0)).intValue();
        List<Object> failures=new ArrayList<>();
        String dimension=level==null?String.valueOf(report.getOrDefault("temporary_ticket_dimension","unavailable")):level.dimension().location().toString();
        if(!tickets.isEmpty())report.put("cleanup_attempts",((Number)report.getOrDefault("cleanup_attempts",0)).intValue()+1);
        for(Iterator<ChunkPos> pending=tickets.iterator();pending.hasNext();){
            ChunkPos chunk=pending.next();
            try{
                if(level==null)throw new IllegalStateException("The original ServerLevel is unavailable; ticket cleanup cannot be claimed");
                simulationTicket(chunk,false);pending.remove();released++;
            }catch(Exception error){
                failures.add(Map.of("x",chunk.x,"z",chunk.z,"error",error.toString()));
                System.err.println("AWFT temporary simulation release failed at "+chunk+": "+error);
            }
        }
        List<Object> remaining=new ArrayList<>();
        for(ChunkPos chunk:tickets)remaining.add(Map.of("x",chunk.x,"z",chunk.z));
        boolean cleanupRequired=!tickets.isEmpty();
        report.put("temporary_ticket_dimension",dimension);report.put("temporary_ticket_chunks_remaining",remaining);
        report.put("temporary_tickets_released",released);report.put("temporary_tickets_remaining",tickets.size());
        report.put("ticket_release_failures",failures);report.put("cleanup_required",cleanupRequired);
        if(cleanupRequired){
            report.put("status",status+"; cleanup_required: retry awftengine cancel before any new admission");
            observations.add(Map.of("at",Instant.now().toString(),"stage","temporary-ticket cleanup required","dimension",dimension,"failures",failures));
            mode="cleanup_required";
        }else{level=null;mode="idle";}
        try{NativeJournal.terminal(directory,"engineering",report);NativeJournal.progress(directory,"engineering-status.json",report);}catch(Exception error){System.err.println("AWFT engineering journal: "+error);}
    }
    private void write(String name,Object data)throws Exception{
        Files.createDirectories(directory);Path target=directory.resolve(name),temporary=directory.resolve(name+".tmp");
        Files.writeString(temporary,JSON.toJson(data));Files.move(temporary,target,StandardCopyOption.REPLACE_EXISTING,StandardCopyOption.ATOMIC_MOVE);
    }
}
