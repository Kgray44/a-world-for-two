package worldfortwo.tavern;

import com.google.gson.*;
import com.mojang.brigadier.arguments.BoolArgumentType;
import com.mojang.brigadier.arguments.IntegerArgumentType;
import com.mojang.brigadier.arguments.StringArgumentType;
import de.markusbordihn.easynpc.entity.easynpc.EasyNPC;
import de.markusbordihn.easynpc.data.skin.SkinDataEntry;
import earth.terrarium.handcrafted.common.entities.Seat;
import immersive_melodies.item.InstrumentItem;
import immersive_melodies.resources.ServerMelodyManager;
import net.minecraft.commands.Commands;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.HolderLookup;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.ListTag;
import net.minecraft.nbt.StringTag;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.*;
import net.minecraft.world.entity.ai.attributes.Attributes;
import net.minecraft.world.item.*;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.level.saveddata.SavedData;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.block.state.properties.BlockStateProperties;
import net.minecraft.world.level.storage.LevelResource;
import net.minecraft.world.level.pathfinder.Path;
import net.minecraft.world.phys.*;
import net.neoforged.fml.common.Mod;
import net.neoforged.bus.api.IEventBus;
import net.neoforged.neoforge.common.NeoForge;
import net.neoforged.neoforge.event.RegisterCommandsEvent;
import net.neoforged.neoforge.event.entity.living.LivingIncomingDamageEvent;
import net.neoforged.neoforge.event.entity.living.LivingEntityUseItemEvent;
import net.neoforged.neoforge.event.entity.EntityJoinLevelEvent;
import net.neoforged.neoforge.event.entity.player.PlayerInteractEvent;
import net.neoforged.neoforge.event.server.ServerStoppedEvent;
import net.neoforged.neoforge.event.server.ServerStoppingEvent;
import net.neoforged.neoforge.event.tick.ServerTickEvent;
import net.neoforged.neoforge.event.tick.EntityTickEvent;

import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.security.MessageDigest;
import java.util.*;

/** Server-authoritative adapter. Loading the mod never creates population or edits blocks. */
@Mod("awft_tavern")
public final class TavernMod {
    static final ResourceLocation SONG=ResourceLocation.parse("immersive_melodies:melody/monkey_island.midi");
    static final String[] INSTRUMENTS={"vielle","lute","flute","tiny_drum"};
    static final String TAG="awft_drowned_rose";
    final Map<UUID,Resident> residents=new LinkedHashMap<>();
    final List<Location> locations=new ArrayList<>();
    final Set<BlockPos> nodes=new HashSet<>();
    final Set<BlockPos> chunkAnchors=new HashSet<>();
    final Set<BlockPos> rugTransit=new HashSet<>();
    final Map<String,Long> pathRefusalReasons=new LinkedHashMap<>();
    final Random random=new Random();
    final List<Resident> band=new ArrayList<>();
    final Map<UUID,Long> playerSpeechCooldown=new HashMap<>();
    final LinkedList<String> spoken=new LinkedList<>();
    MinecraftServer server;
    JsonObject layout;
    Ledger ledger;
    String layoutHash="";
    int cursor;
    long nextBand, performanceStart=-1, performanceEnd, gatheringDeadline;
    long decisions, paths, pathFailures, conversations, schedulerNanos;
    long recoveries;
    long gatheringFailures, completedPerformances;
    long pathsStarted, startCellEscapes;
    long seatDismounts, seatDismountWaits;
    long originalRestores, originalPreserved, originalRestoreRefusals;
    long profileReconstructions, profilePreserved, profileReconstructionRefusals;
    long drinksStarted, nativeDrinksFinished;
    String lastOriginalRestore="";
    String lastProfileReconstruction="";
    String lastBandStop="";
    SurveyedPaths surveyedPaths;
    RecoveryWindow recoveryWindow;
    boolean suspended;
    StatusWriter statusWriter;
    long nextSpeech, nextGlobalSpeech, speechEvents, speechSuppressed;
    boolean music=true, loaded, paused=true;
    String fault="Not initialized; no population spawned";

    record Location(ActivityPolicy.Slot policy,BlockPos pos,BlockPos approach,String chairState) {}
    static final class Resident {
        final UUID uuid;
        final JsonObject profile;
        final Map<String,Integer> preferences=new HashMap<>();
        final LinkedList<String> history=new LinkedList<>();
        final LinkedList<String> spoken=new LinkedList<>();
        Location destination;
        String activity="idle";
        long until, nextPath, travelDeadline;
        long durationTicks;
        long nextSip, nextSpeech, nextLook;
        boolean temporaryDrinkProp,sipInProgress;
        String lastNativeDrinkResult="";
        long drinkStarts,drinkFinishes;
        String lastPathRefusal="";
        BlockPos lastRefusedNode;
        Vec3 lastPosition;
        Vec3 lookTarget;
        long lookUntil;
        long stalledSince;
        boolean disabled, arrived;
        Resident(JsonObject p){
            profile=p;uuid=ActivityPolicy.identity(p.get("id").getAsString());
            p.getAsJsonObject("preferences").entrySet().forEach(e->preferences.put(e.getKey(),e.getValue().getAsInt()));
        }
    }

    public TavernMod(IEventBus modBus){
        ManagedSeat.TYPES.register(modBus);
        NeoForge.EVENT_BUS.addListener(this::commands);
        NeoForge.EVENT_BUS.addListener(this::tick);
        NeoForge.EVENT_BUS.addListener(this::interact);
        NeoForge.EVENT_BUS.addListener(this::protect);
        NeoForge.EVENT_BUS.addListener(this::drank);
        NeoForge.EVENT_BUS.addListener(this::joined);
        NeoForge.EVENT_BUS.addListener(this::boundary);
        NeoForge.EVENT_BUS.addListener((ServerStoppingEvent e)->{if(recoveryWindow!=null){recoveryWindow.finish("server_stopping");com.mojang.logging.LogUtils.getLogger().info("Tavern recovery stopping cleanup: {}",recoveryWindow.status());}});
        NeoForge.EVENT_BUS.addListener((ServerStoppedEvent e)->reset());
    }

    void reset(){if(recoveryWindow!=null)recoveryWindow.finish("server_stopped");recoveryWindow=null;if(statusWriter!=null)statusWriter.close();statusWriter=null;residents.clear();locations.clear();nodes.clear();rugTransit.clear();pathRefusalReasons.clear();chunkAnchors.clear();band.clear();spoken.clear();playerSpeechCooldown.clear();loaded=false;server=null;ledger=null;layout=null;paused=true;performanceStart=-1;}
    ServerLevel level(){return server.overworld();}
    Mob mob(Resident r){return level().getEntity(r.uuid) instanceof Mob m && m.getTags().contains(TAG)?m:null;}
    static BlockPos pos(JsonArray a){return new BlockPos(a.get(0).getAsInt(),a.get(1).getAsInt(),a.get(2).getAsInt());}
    static String hash(byte[] raw)throws Exception{return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(raw));}

    void load(MinecraftServer s)throws Exception{
        if(loaded)return;
        server=s;
        java.nio.file.Path file=s.getServerDirectory().resolve("config/awft-tavern.json");
        if(!Files.isRegularFile(file)||Files.size(file)>2*1024*1024)throw new IllegalStateException("A bounded admitted saved-layout config is required");
        byte[] bytes=Files.readAllBytes(file);layoutHash=hash(bytes);
        layout=JsonParser.parseString(new String(bytes,StandardCharsets.UTF_8)).getAsJsonObject();
        if(layout.get("format").getAsInt()!=1)throw new IllegalStateException("Unknown saved survey format");
        if(!s.getWorldPath(LevelResource.ROOT).toAbsolutePath().normalize().toString().contains("RosewaterArtistic"))
            throw new IllegalStateException("Only the existing construction world is admitted");
        nodes.clear();rugTransit.clear();chunkAnchors.clear();locations.clear();residents.clear();
        for(JsonElement e:layout.getAsJsonArray("nodes"))nodes.add(pos(e.getAsJsonArray()));
        if(nodes.size()>2048||nodes.size()<30)throw new IllegalStateException("Invalid finite navigation graph");
        for(BlockPos p:nodes)if(p.getX()<1293||p.getX()>1310||p.getZ()<-1288||p.getZ()>-1271||p.getY()<65||p.getY()>70)
            throw new IllegalStateException("Graph escaped custom Drowned Rose interior");
        Map<BlockPos,String> savedStates=new HashMap<>();
        for(JsonElement e:layout.getAsJsonArray("preimage")){JsonArray row=e.getAsJsonArray();savedStates.put(pos(row),row.get(3).getAsString());}
        for(var entry:savedStates.entrySet()){
            BlockPos p=entry.getKey();
            if(p.getX()>=1293&&p.getX()<=1310&&p.getZ()>=-1288&&p.getZ()<=-1271&&p.getY()>=65&&p.getY()<=70
                &&ActivityPolicy.rugTransit(entry.getValue(),savedStates.getOrDefault(p.above(),"")))rugTransit.add(p);
        }
        // Rugs are transit cells, never new idle destinations. Retain the same
        // admitted config hash, chair reservations and Native collision checks.
        nodes.addAll(rugTransit);
        surveyedPaths=new SurveyedPaths(nodes);
        for(BlockPos p:nodes)chunkAnchors.add(new BlockPos((p.getX()>>4)<<4,65,(p.getZ()>>4)<<4));
        for(JsonElement e:layout.getAsJsonArray("slots")){
            JsonObject o=e.getAsJsonObject();List<String> acts=new ArrayList<>();o.getAsJsonArray("activities").forEach(a->acts.add(a.getAsString()));
            Location l=new Location(new ActivityPolicy.Slot(o.get("id").getAsString(),o.get("group").getAsString(),acts),pos(o.getAsJsonArray("pos")),pos(o.getAsJsonArray("approach")),o.has("chair_state")?o.get("chair_state").getAsString():"");
            if(!nodes.contains(l.approach()) || (!nodes.contains(l.pos())&&l.chairState().isEmpty()))throw new IllegalStateException("Invalid destination/approach");
            locations.add(l);
        }
        try(var in=TavernMod.class.getResourceAsStream("/roster.json")){
            if(in==null)throw new IllegalStateException("Missing roster");
            for(JsonElement e:JsonParser.parseString(new String(in.readAllBytes(),StandardCharsets.UTF_8)).getAsJsonArray()){
                Resident r=new Resident(e.getAsJsonObject());if(residents.put(r.uuid,r)!=null)throw new IllegalStateException("Duplicate identity");
            }
        }
        if(residents.size()!=45)throw new IllegalStateException("Exactly45 source identities required");
        ledger=level().getDataStorage().computeIfAbsent(new SavedData.Factory<>(Ledger::new,Ledger::read,null),"awft_drowned_rose");
        if(!ledger.layoutHash.isEmpty()&&!ledger.layoutHash.equals(layoutHash))throw new IllegalStateException("Admitted layout changed; explicit migration required");
        music=ledger.music;
        spoken.clear();spoken.addAll(readHistory(ledger.speech,"recent",24));
        nextSpeech=ledger.speech.getLong("next_ambient");nextGlobalSpeech=ledger.speech.getLong("next_global");
        for(Resident r:residents.values()){
            CompoundTag saved=ledger.data.getCompound(r.uuid.toString());
            r.disabled=saved.getBoolean("disabled");
            r.until=ActivityPolicy.resumeDeadline(saved.getLong("until"),level().getGameTime(),r.uuid);
            r.arrived=saved.getBoolean("arrived");
            r.activity=saved.contains("activity")?saved.getString("activity"):"idle";
            String destination=saved.getString("destination");
            r.destination=locations.stream().filter(l->l.policy().id().equals(destination)).findFirst().orElse(null);
            r.durationTicks=saved.contains("duration")?Math.clamp(saved.getLong("duration"),200,1200):600;
            r.spoken.addAll(readHistory(saved,"recent_dialogue",6));r.nextSpeech=saved.getLong("next_speech");
            r.temporaryDrinkProp=saved.getBoolean("temporary_drink_prop");
            if(r.destination!=null){
                r.history.add(destination);r.travelDeadline=saved.contains("travel_deadline")?saved.getLong("travel_deadline"):level().getGameTime()+1200;
                String recent=saved.getString("recent_destinations");
                if(!recent.isEmpty()){r.history.clear();for(String id:recent.split(","))if(r.history.size()<4)r.history.add(id);}
            }
            for(String act:r.preferences.keySet())if(saved.contains("weight_"+act))r.preferences.put(act,saved.getInt("weight_"+act));
        }
        band.clear();performanceStart=ledger.performanceStart;performanceEnd=ledger.performanceEnd;
        nextBand=Math.max(level().getGameTime()+200,ledger.nextBand);
        if(!ledger.bandIds.isEmpty())for(String id:ledger.bandIds.split(",")){
            Resident r=residents.get(UUID.fromString(id));if(r!=null)band.add(r);
        }
        gatheringDeadline=level().getGameTime()+1200;
        loaded=true;paused=!layout.get("spawn_admitted").getAsBoolean();
        suspended=true;fault=paused?"Source survey; explicit spawn admission required":"";
        if(statusWriter==null)statusWriter=new StatusWriter();
    }

    boolean allChunksLoaded(){for(BlockPos p:chunkAnchors)if(!level().hasChunkAt(p))return false;return true;}
    void verifyPreimage(){
        if(!allChunksLoaded())throw new IllegalStateException("All tavern chunks must already be loaded; no force loads");
        for(JsonElement e:layout.getAsJsonArray("preimage")){
            JsonArray a=e.getAsJsonArray();BlockPos p=pos(a);
            String actual=net.minecraft.commands.arguments.blocks.BlockStateParser.serialize(level().getBlockState(p));
            if(!actual.equals(a.get(3).getAsString()))throw new IllegalStateException("Saved tavern preimage changed at "+p);
        }
        if(!ServerMelodyManager.getDatapackMelodies().containsKey(SONG))throw new IllegalStateException("Exact built-in Monkey Island identifier absent");
        for(String instrument:INSTRUMENTS)if(!(BuiltInRegistries.ITEM.get(ResourceLocation.parse("immersive_melodies:"+instrument)) instanceof InstrumentItem))
            throw new IllegalStateException("Missing instrument "+instrument);
    }

    int initialize(String expected)throws Exception{
        if(!layout.get("spawn_admitted").getAsBoolean())
            throw new IllegalStateException("Source survey: explicit master spawn admission required");
        if(!expected.equals(layoutHash))throw new IllegalStateException("Exact admitted layout SHA256 required");
        verifyPreimage();
        if(!ledger.layoutHash.isEmpty()&&!ledger.layoutHash.equals(layoutHash))throw new IllegalStateException("Ledger belongs to another layout");
        List<Location> starts=locations.stream().filter(l->l.chairState().isEmpty()&&!l.policy().activities().contains("music")).toList();
        long missing=residents.values().stream().filter(r->!ledger.data.contains(r.uuid.toString())&&level().getEntity(r.uuid)==null).count();
        if(starts.size()<missing)throw new IllegalStateException("Not enough independent starts for the additive population");
        // Prepare all missing residents and reserve actual collision-free starts
        // before any entity is inserted. Never move an existing cat, bird or player.
        Map<UUID,Mob> prepared=new LinkedHashMap<>();Map<UUID,Location> starting=new LinkedHashMap<>();
        Set<String> used=new HashSet<>();List<AABB> assignedBodies=new ArrayList<>();
        for(Resident r:residents.values()){
            Entity existing=level().getEntity(r.uuid);
            if(existing!=null&&(!(existing instanceof EasyNPC<?>)||!existing.getTags().contains(TAG)))throw new IllegalStateException("UUID collision");
            if(ledger.data.contains(r.uuid.toString())||existing!=null)continue;
            Entity entity=BuiltInRegistries.ENTITY_TYPE.get(ResourceLocation.parse("easy_npc:humanoid")).create(level());
            if(!(entity instanceof Mob m)||!(entity instanceof EasyNPC<?> npc))throw new IllegalStateException("Pinned Easy NPC humanoid registry is unavailable");
            m.setUUID(r.uuid);m.addTag(TAG);m.setPersistenceRequired();m.setCanPickUpLoot(false);m.setInvulnerable(true);configure(m);
            m.setCustomName(Component.literal(r.profile.get("name").getAsString()));m.setCustomNameVisible(false);
            npc.getEasyNPCSkinData().setSkinDataEntry(SkinDataEntry.createResourceLocationSkin(ResourceLocation.parse("awft_tavern:textures/entity/"+r.profile.get("id").getAsString()+".png")));
            Location selected=null;
            for(Location candidate:starts){
                if(used.contains(candidate.policy().id())||conflicts(candidate,r))continue;
                m.moveTo(candidate.pos().getX()+.5,candidate.pos().getY(),candidate.pos().getZ()+.5,0,0);
                AABB body=m.getBoundingBox();
                if(!level().noCollision(m,body)||assignedBodies.stream().anyMatch(body::intersects)
                    ||!level().getEntitiesOfClass(LivingEntity.class,body.inflate(.2)).isEmpty())continue;
                selected=candidate;assignedBodies.add(body);used.add(candidate.policy().id());break;
            }
            if(selected==null)throw new IllegalStateException("Not enough currently collision-free starts for missing residents; no resident inserted");
            prepared.put(r.uuid,m);starting.put(r.uuid,selected);
        }
        int spawned=0;
        for(Resident r:residents.values()){
            if(ledger.data.contains(r.uuid.toString()))continue;
            Mob m=prepared.get(r.uuid);
            if(m!=null){
                if(!level().addFreshEntity(m))throw new IllegalStateException("Entity insertion failed; retain checkpoint");
                spawned++;
            }
            r.destination=starting.get(r.uuid);r.arrived=r.destination!=null;
            r.durationTicks=600;r.until=level().getGameTime()+20+random.nextInt(600);persist(r);
        }
        ledger.layoutHash=layoutHash;ledger.setDirty();return spawned;
    }

    void persist(Resident r){
        CompoundTag tag=new CompoundTag();tag.putBoolean("disabled",r.disabled);
        tag.putString("activity",r.activity);tag.putString("destination",r.destination==null?"":r.destination.policy().id());
        tag.putLong("until",r.until);tag.putString("residency","The Drowned Rose");
        tag.putLong("duration",r.durationTicks);tag.putString("recent_destinations",String.join(",",r.history));
        tag.putBoolean("arrived",r.arrived);tag.putLong("travel_deadline",r.travelDeadline);
        tag.putString("personality",r.profile.get("personality").getAsString());
        tag.put("recent_dialogue",writeHistory(r.spoken));tag.putLong("next_speech",r.nextSpeech);
        tag.putBoolean("temporary_drink_prop",r.temporaryDrinkProp);
        for(var entry:r.preferences.entrySet())tag.putInt("weight_"+entry.getKey(),entry.getValue());
        ledger.data.put(r.uuid.toString(),tag);ledger.music=music;ledger.setDirty();
    }
    static LinkedList<String> readHistory(CompoundTag tag,String key,int limit){
        LinkedList<String> out=new LinkedList<>();ListTag list=tag.getList(key,8);
        for(int i=0;i<Math.min(limit,list.size());i++){String s=list.getString(i);if(s.length()<=512)out.add(s);}return out;
    }
    static ListTag writeHistory(Collection<String> recent){ListTag list=new ListTag();recent.forEach(s->list.add(StringTag.valueOf(s)));return list;}

    boolean conflicts(Location candidate,Resident except){
        for(Resident other:residents.values())if(other!=except&&other.destination!=null){
            Location b=other.destination;
            if(candidate.pos().equals(b.pos())||candidate.approach().equals(b.approach())||candidate.pos().equals(b.approach())||candidate.approach().equals(b.pos()))return true;
        }
        return false;
    }
    Vec3 reviewedDismount(Resident r,Mob m){
        if(!(m.getVehicle() instanceof ManagedSeat seat)||!allChunksLoaded())return null;
        Location chair=locations.stream().filter(l->!l.chairState().isEmpty()&&l.pos().equals(seat.blockPosition())).findFirst().orElse(null);
        if(chair==null||!nodes.contains(chair.approach())||conflicts(chair,r))return null;
        if(!net.minecraft.commands.arguments.blocks.BlockStateParser.serialize(level().getBlockState(chair.pos())).equals(chair.chairState()))return null;
        Vec3 exit=seat.nativeExit(m,chair.approach());
        return exit!=null&&ActivityPolicy.insideTavernFootprint(exit.x,exit.z)?exit:null;
    }
    boolean stand(Resident r,Mob m){
        m.getNavigation().stop();m.stopUsingItem();m.setItemSlot(EquipmentSlot.MAINHAND,ItemStack.EMPTY);
        r.temporaryDrinkProp=false;r.sipInProgress=false;
        if(m.isPassenger()){
            Vec3 exit=reviewedDismount(r,m);
            if(exit==null||!(m.getVehicle() instanceof ManagedSeat seat)||!seat.dismount(m,exit)){
                seatDismountWaits++;r.until=level().getGameTime()+100;return false;
            }
            seatDismounts++;
        }
        r.arrived=false;return true;
    }
    void configure(Mob m){
        if(m instanceof EasyNPC<?> npc){npc.getEntityGoalSelector().removeAllGoals(g->true);npc.getEntityTargetSelector().removeAllGoals(g->true);}
        m.setCanPickUpLoot(false);m.setPersistenceRequired();
        var speed=m.getAttribute(Attributes.MOVEMENT_SPEED);
        if(speed!=null&&speed.getBaseValue()!=.25)speed.setBaseValue(.25);
        m.setSprinting(false);
    }
    void joined(EntityJoinLevelEvent event){
        if(!event.getLevel().isClientSide()&&event.getEntity() instanceof Mob m&&m.getTags().contains(TAG))configure(m);
    }
    void boundary(EntityTickEvent.Pre event){
        if(!(event.getEntity() instanceof Mob m)||m.level().isClientSide()||!m.getTags().contains(TAG))return;
        if(!loaded||paused||suspended){m.getNavigation().stop();m.setDeltaMovement(Vec3.ZERO);return;}
        Resident r=residents.get(m.getUUID());
        if(r!=null&&r.arrived&&r.lookTarget!=null&&level().getGameTime()<r.lookUntil&&!r.activity.equals("music")&&!r.activity.equals("gather"))
            m.getLookControl().setLookAt(r.lookTarget.x,r.lookTarget.y,r.lookTarget.z,8,8);
        if(m.isPassenger())return;
        Vec3 next=m.position().add(m.getDeltaMovement());
        if(!ActivityPolicy.insideTavernFootprint(next.x,next.z)){
            m.getNavigation().stop();m.setDeltaMovement(0,m.getDeltaMovement().y,0);
        }
    }
    boolean setDestination(Resident r,Mob m,Location dest,String activity,long duration){
        if(!stand(r,m))return false;
        r.destination=dest;r.activity=activity;r.durationTicks=duration;r.until=level().getGameTime()+duration;
        r.travelDeadline=level().getGameTime()+1200;r.nextPath=0;r.stalledSince=0;
        r.history.addFirst(dest.policy().id());while(r.history.size()>4)r.history.removeLast();persist(r);return true;
    }
    void decide(Resident r,Mob m,long now){
        Set<String> occupied=new HashSet<>();
        Map<String,Integer> preferences=new HashMap<>(r.preferences);
        for(Location l:locations){
            if(conflicts(l,r))occupied.add(l.policy().id());
            if(l.policy().activities().contains("social")){
                long count=residents.values().stream().filter(a->a!=r&&a.destination!=null&&a.destination.policy().group().equals(l.policy().group())).count();
                if(count>=4)occupied.add(l.policy().id());
            }
        }
        // Social preference boosts the choice when a known friend is already
        // socializing; slot occupancy and bounded groups still govern admission.
        for(JsonElement friend:r.profile.getAsJsonArray("social_preferences")){
            Resident other=residents.get(ActivityPolicy.identity(friend.getAsString()));
            if(other!=null&&other.arrived&&other.activity.equals("social"))preferences.computeIfPresent("social",(k,v)->Math.min(12,v+2));
        }
        ActivityPolicy.choose(random,locations.stream().map(Location::policy).toList(),occupied,r.history,preferences,performanceStart>=0,false)
            .ifPresentOrElse(c->{Location l=locations.stream().filter(a->a.policy().id().equals(c.slot().id())).findFirst().orElseThrow();if(setDestination(r,m,l,c.activity(),c.ticks()))decisions++;},()->r.until=now+200+random.nextInt(200));
    }
    void move(Resident r,Mob m,long now){
        Location d=r.destination;if(d==null)return;
        if(r.arrived&&m.isPassenger())return;
        Vec3 target=Vec3.atBottomCenterOf(d.approach());
        if(r.lastPosition==null||m.distanceToSqr(r.lastPosition)>.04){r.lastPosition=m.position();r.stalledSince=now;}
        if(m.distanceToSqr(target)<.4){
            m.getNavigation().stop();
            if(!d.chairState().isEmpty()&&!m.isPassenger()){
                var state=level().getBlockState(d.pos());
                boolean mounted=false;
                if(!net.minecraft.commands.arguments.blocks.BlockStateParser.serialize(state).equals(d.chairState())){r.arrived=false;r.until=now;persist(r);return;}
                if(!Seat.SITTING_POSITIONS.containsEntry(level().dimension(),d.pos()) && level().getEntitiesOfClass(LivingEntity.class,new AABB(d.pos())).stream().noneMatch(e->e!=m)){
                    Direction facing=state.getValue(BlockStateProperties.HORIZONTAL_FACING);
                    Seat seat=ManagedSeat.at(level(),d.pos(),facing,r.uuid);
                    if(seat!=null){mounted=level().addFreshEntity(seat)&&m.startRiding(seat,true);if(!mounted)seat.removeSeat();}
                }
                if(!mounted){r.arrived=false;r.until=now+20;persist(r);return;}
            }
            if(!r.arrived){r.until=now+r.durationTicks;r.arrived=true;persist(r);}
            return;
        }
        if(r.arrived){r.arrived=false;persist(r);}
        if(now>r.travelDeadline){m.getNavigation().stop();r.until=now;refused(r,"travel_timeout",null);return;}
        if(now<r.nextPath || !m.getNavigation().isDone())return;
        r.nextPath=now+100+random.nextInt(80);
        Path path=surveyedPaths.create(level(),m,d.approach());paths++;
        if(path==null){refused(r,"native_no_path",null);return;}
        if(!path.canReach()){refused(r,"native_incomplete",null);return;}
        // Defense in depth: candidate expansion was constrained before native
        // A*. Only its first cell may describe current anomalous footing, so a
        // pushed NPC can leave it naturally. Never admit another furniture cell.
        for(int i=0;i<path.getNodeCount();i++){
            BlockPos p=path.getNode(i).asBlockPos();
            if(i==0&&!nodes.contains(p)&&p.distSqr(m.blockPosition())<=2&&ActivityPolicy.insideTavernFootprint(p.getX()+.5,p.getZ()+.5)){startCellEscapes++;continue;}
            if(!nodes.contains(p)){refused(r,"outside_transit",p);return;}
        }
        if(!m.getNavigation().moveTo(path,.5)){refused(r,"native_start_failed",null);return;}
        pathsStarted++;
        r.lastPathRefusal="";r.lastRefusedNode=null;
    }
    void refused(Resident r,String reason,BlockPos node){pathFailures++;pathRefusalReasons.merge(reason,1L,Long::sum);r.lastPathRefusal=reason;r.lastRefusedNode=node;}

    Resident recoveryResident(UUID uuid,String name)throws Exception{
        if(recoveryWindow==null)throw new IllegalStateException("prepare_recovery_required");
        recoveryWindow.requireReady(paused,server.getPlayerList().getPlayers().isEmpty());
        if(!loaded||ledger==null||!layoutHash.equals("b2963d58e4dd14e542c24e2b926ddb76ead1a3a7b627a951a2fb348ca85929a4")||!ledger.layoutHash.equals(layoutHash))
            throw new IllegalStateException("original_layout_or_ledger_not_admitted");
        Resident resident=residents.get(uuid);
        if(resident==null||!ledger.data.contains(uuid.toString())||!resident.profile.get("name").getAsString().equals(name))
            throw new IllegalStateException("original_not_registered_in_existing_roster_ledger");
        if(!ManagedSeat.TYPE.get().canSerialize())throw new IllegalStateException("managed_seat_type_not_saveable");
        for(BlockPos p:chunkAnchors){
            if(!level().hasChunkAt(p))throw new IllegalStateException("original_chunk_not_full:"+p.toShortString());
            if(!level().areEntitiesLoaded(ChunkPos.asLong(p.getX()>>4,p.getZ()>>4)))throw new IllegalStateException("original_chunk_entities_not_loaded:"+p.toShortString());
        }
        OriginalRecovery.proveAbsent(server.getServerDirectory().resolve("config/awft-tavern-recovery"),uuid);
        return resident;
    }
    Entity existingRecovery(UUID uuid,String name){
        for(ServerLevel dimension:server.getAllLevels()){
            Entity existing=dimension.getEntity(uuid);
            if(existing==null)continue;
            if(!(existing instanceof EasyNPC<?>)||!existing.getTags().contains(TAG)||!BuiltInRegistries.ENTITY_TYPE.getKey(existing.getType()).toString().equals("easy_npc:humanoid")||existing.getCustomName()==null||!existing.getCustomName().getString().equals(name))
                throw new IllegalStateException("original_uuid_collision_in:"+dimension.dimension().location());
            return existing;
        }
        return null;
    }
    void recoveryBody(Entity entity){
        verifyPreimage();AABB body=entity.getBoundingBox();
        if(!level().noCollision(entity,body))throw new IllegalStateException("original_native_body_collision_at:"+entity.blockPosition().toShortString());
        if(!level().getEntitiesOfClass(LivingEntity.class,body.inflate(.1)).isEmpty())throw new IllegalStateException("original_living_entity_occupies_body_at:"+entity.blockPosition().toShortString());
    }
    String restoreOriginal(String uuid,String sha)throws Exception{
        OriginalRecovery.Source source=OriginalRecovery.source(uuid,sha);
        recoveryResident(source.uuid(),source.name());
        Entity existing=existingRecovery(source.uuid(),source.name());
        if(existing!=null){originalPreserved++;return "Original preserved: "+uuid+"; existing identity in "+existing.level().dimension().location()+"; no insertion";}
        CompoundTag original=OriginalRecovery.read(server.getServerDirectory().resolve("config/awft-tavern-recovery"),source);
        Entity entity=EntityType.loadEntityRecursive(original,level(),e->e);
        if(!(entity instanceof Mob mob)||!(entity instanceof EasyNPC<?>)||!entity.getUUID().equals(source.uuid())||!entity.getTags().contains(TAG)||
            !BuiltInRegistries.ENTITY_TYPE.getKey(entity.getType()).toString().equals("easy_npc:humanoid")||entity.getCustomName()==null||!entity.getCustomName().getString().equals(source.name()))
            throw new IllegalStateException("original_native_load_identity_mismatch");
        recoveryBody(entity);
        // Loading/preflight never inserted the object. Retain its original UUID,
        // name, skin, inventory and position; do not reset its registered ledger.
        if(!level().addFreshEntity(mob))throw new IllegalStateException("original_native_insertion_refused_retain_checkpoint");
        originalRestores++;return "Original restored: "+uuid+"; source gzip SHA256 "+sha+"; native body clear; existing ledger retained";
    }
    String reconstructMissing(String uuid,String sha)throws Exception{
        if(!uuid.equals(OriginalRecovery.NIAMH.toString())||!sha.equals(OriginalRecovery.NIAMH_PROFILE_SHA))throw new IllegalStateException("not_pinned_niamh_profile_repair");
        Resident resident=recoveryResident(OriginalRecovery.NIAMH,"Niamh Wick");
        OriginalRecovery.profile(uuid,sha,resident.profile);
        Entity existing=existingRecovery(resident.uuid,"Niamh Wick");
        if(existing!=null){profilePreserved++;return "Missing profile preserved: "+uuid+"; existing identity; no insertion";}
        Location standing=locations.stream().filter(l->l.policy().id().equals("floor-16")).findFirst().orElseThrow(()->new IllegalStateException("reviewed_floor16_missing"));
        if(!standing.pos().equals(new BlockPos(1293,65,-1288))||!standing.approach().equals(standing.pos())||!standing.chairState().isEmpty()||standing.policy().activities().contains("music")||!nodes.contains(standing.pos()))
            throw new IllegalStateException("reviewed_floor16_changed");
        if(conflicts(standing,resident))throw new IllegalStateException("reviewed_floor16_reserved");
        Entity entity=BuiltInRegistries.ENTITY_TYPE.get(ResourceLocation.parse("easy_npc:humanoid")).create(level());
        if(!(entity instanceof Mob mob)||!(entity instanceof EasyNPC<?> npc))throw new IllegalStateException("profile_native_factory_unavailable");
        if(mob.isNoAi()||!mob.getMainHandItem().isEmpty()||!mob.getOffhandItem().isEmpty())throw new IllegalStateException("profile_native_factory_defaults_unexpected");
        mob.setUUID(resident.uuid);mob.addTag(TAG);mob.setPersistenceRequired();mob.setCanPickUpLoot(false);mob.setInvulnerable(true);configure(mob);
        mob.setCustomName(Component.literal("Niamh Wick"));mob.setCustomNameVisible(false);
        npc.getEasyNPCSkinData().setSkinDataEntry(SkinDataEntry.createResourceLocationSkin(ResourceLocation.parse("awft_tavern:textures/entity/niamh-wick.png")));
        mob.moveTo(1293.5,65,-1287.5,0,0);recoveryBody(mob);
        if(!level().addFreshEntity(mob))throw new IllegalStateException("profile_native_insertion_refused_retain_checkpoint");
        profileReconstructions++;return "Missing profile reconstructed: "+uuid+"; original-profile SHA256 "+sha+"; reviewed floor-16; native defaults and empty inventory; original NBT unavailable; existing ledger retained";
    }

    void lookAndTalk(Resident r,Mob m,long now){
        if(r.destination==null||!r.arrived)return;
        if(r.activity.equals("music")||r.activity.equals("gather"))return;
        if(r.activity.equals("drink")&&now>=r.nextSip&&!m.isUsingItem()){
            ItemStack drink=m.getMainHandItem();
            if(!nativeMug(drink)){
                // Temporary social props use the existing managed-hand policy.
                // Never take player stock or overwrite unrelated held equipment.
                if(!drink.isEmpty()&&!r.temporaryDrinkProp){r.nextSip=now+240;return;}
                String id=(r.uuid.hashCode()&1)==0?"farmersdelight:apple_cider":"farmersdelight:hot_cocoa";
                drink=new ItemStack(BuiltInRegistries.ITEM.get(ResourceLocation.parse(id)));
                if(!nativeMug(drink)||drink.getUseAnimation()!=UseAnim.DRINK||drink.getUseDuration(m)!=32)throw new IllegalStateException("Installed native32-tick mug unavailable:"+id);
                m.setItemSlot(EquipmentSlot.MAINHAND,drink);
            }
            if(drink.getUseAnimation()!=UseAnim.DRINK||drink.getUseDuration(m)!=32)throw new IllegalStateException("Native mug use state changed");
            // LivingEntity handles all32 ticks, native finish/effects/count and
            // remaining container. Reuse a native still-filled result; never
            // force-shrink, finish twice or replace the native Finish result.
            m.startUsingItem(InteractionHand.MAIN_HAND);r.nextSip=now+240+random.nextInt(280);
            if(m.isUsingItem()){r.temporaryDrinkProp=true;r.sipInProgress=true;r.drinkStarts++;drinksStarted++;persist(r);}
        }
        List<Resident> group=residents.values().stream().filter(o->o!=r&&o.arrived&&o.destination!=null&&o.destination.policy().group().equals(r.destination.policy().group())&&mob(o)!=null&&mob(o).distanceToSqr(m)<25).limit(3).toList();
        if(now>=r.nextLook){
            r.nextLook=now+80+random.nextInt(120);
            if(!group.isEmpty())r.lookTarget=mob(group.get(random.nextInt(group.size()))).getEyePosition();
            else if(r.activity.equals("watch"))r.lookTarget=new Vec3(1302,67,-1286);
            else r.lookTarget=new Vec3(m.getX()+random.nextDouble()*6-3,m.getEyeY()-.3+random.nextDouble()*.6,m.getZ()+random.nextDouble()*6-3);
            r.lookUntil=now+60+random.nextInt(40);
        }
        if(group.isEmpty()||now<nextSpeech||now<r.nextSpeech||now<nextGlobalSpeech||
            !Set.of("social","group","drink","bar","sit").contains(r.activity))return;
        var listeners=level().players().stream().filter(p->p.distanceToSqr(m)<=144).toList();
        if(listeners.isEmpty())return;
        Optional<String> selected=chooseSpeech(r,now);if(selected.isEmpty())return;
        nextSpeech=now+500+random.nextInt(300);recordSpeech(r,selected.get(),now);
        Component line=Component.literal(r.profile.get("name").getAsString()+": "+selected.get());
        for(var player:listeners){player.sendSystemMessage(line);conversations++;}
        // A conversational turn gets a native glance from nearby companions.
        for(Resident other:group)if(!other.activity.equals("music")&&!other.activity.equals("gather")){other.lookTarget=m.getEyePosition();other.lookUntil=now+80;}
    }
    static boolean nativeMug(ItemStack stack){
        if(stack.isEmpty())return false;String id=BuiltInRegistries.ITEM.getKey(stack.getItem()).toString();
        return id.equals("farmersdelight:apple_cider")||id.equals("farmersdelight:hot_cocoa");
    }
    void drank(LivingEntityUseItemEvent.Finish event){
        if(!loaded||event.getEntity().level().isClientSide()||!event.getEntity().getTags().contains(TAG))return;
        Resident r=residents.get(event.getEntity().getUUID());
        if(r==null||!r.sipInProgress||!nativeMug(event.getItem()))return;
        r.sipInProgress=false;r.drinkFinishes++;nativeDrinksFinished++;
        ItemStack result=event.getResultStack();r.lastNativeDrinkResult=result.isEmpty()?"minecraft:air":BuiltInRegistries.ITEM.getKey(result.getItem()).toString();
        // Observe only. The native result stays held until the next scheduled
        // temporary-prop/activity transition; no inventory or result mutation.
    }
    Optional<String> chooseSpeech(Resident r,long now){
        if(now<r.nextSpeech||now<nextGlobalSpeech){speechSuppressed++;return Optional.empty();}
        List<String> lines=new ArrayList<>();r.profile.getAsJsonArray("dialogue").forEach(e->lines.add(e.getAsString()));
        Optional<String> line=ActivityPolicy.dialogue(random,lines,r.spoken,spoken);if(line.isEmpty())speechSuppressed++;return line;
    }
    void recordSpeech(Resident r,String line,long now){
        r.spoken.addFirst(line);while(r.spoken.size()>6)r.spoken.removeLast();
        spoken.addFirst(line);while(spoken.size()>24)spoken.removeLast();
        r.nextSpeech=now+900+random.nextInt(900);nextGlobalSpeech=now+200;speechEvents++;
        ledger.speech.put("recent",writeHistory(spoken));ledger.speech.putLong("next_ambient",nextSpeech);ledger.speech.putLong("next_global",nextGlobalSpeech);persist(r);
    }

    void ensemble(long now){
        if(!music){endBand(now);return;}
        if(performanceStart>=0){
            if(now>=performanceEnd||band.size()!=4||band.stream().anyMatch(r->r.disabled||mob(r)==null)){
                lastBandStop=now>=performanceEnd?"completed":"member_unavailable";if(now>=performanceEnd)completedPerformances++;endBand(now);
            }
            else for(int i=0;i<4;i++){
                Mob m=mob(band.get(i));ItemStack held=m.getMainHandItem();
                if(!(held.getItem() instanceof InstrumentItem)||!BuiltInRegistries.ITEM.getKey(held.getItem()).equals(ResourceLocation.parse("immersive_melodies:"+INSTRUMENTS[i]))||!SONG.equals(InstrumentItem.getMelody(held))||!held.getOrDefault(InstrumentItem.PLAYING,false)||held.getOrDefault(InstrumentItem.START_TIME,-1L)!=performanceStart){
                    ItemStack instrument=new ItemStack(BuiltInRegistries.ITEM.get(ResourceLocation.parse("immersive_melodies:"+INSTRUMENTS[i])));
                    ((InstrumentItem)instrument.getItem()).play(instrument,SONG,level(),m);instrument.set(InstrumentItem.START_TIME,performanceStart);m.setItemSlot(EquipmentSlot.MAINHAND,instrument);
                }
            }
            return;
        }
        if(!band.isEmpty()){
            if(now>gatheringDeadline||band.stream().anyMatch(r->mob(r)==null||r.disabled)){
                gatheringFailures++;lastBandStop=now>gatheringDeadline?"gather_timeout":"gather_member_unavailable";endBand(now);
                nextBand=now+200+random.nextInt(201);persistBand();return;
            }
            if(band.size()==4&&band.stream().allMatch(r->r.arrived)){
                int length=ServerMelodyManager.getMelody(SONG).getLength();
                if(length<=0){fault="Monkey Island has no valid parsed duration";endBand(now);return;}
                performanceStart=now;performanceEnd=now+(length+49)/50;
                for(int i=0;i<4;i++){
                    Resident r=band.get(i);Mob m=mob(r);
                    ItemStack instrument=new ItemStack(BuiltInRegistries.ITEM.get(ResourceLocation.parse("immersive_melodies:"+INSTRUMENTS[i])));
                    ((InstrumentItem)instrument.getItem()).play(instrument,SONG,level(),m);
                    // All calls occur on this server tick. Use only the installed public API.
                    m.setItemSlot(EquipmentSlot.MAINHAND,instrument);r.activity="music";r.until=performanceEnd+20;persist(r);
                }
                persistBand();
            }
            return;
        }
        if(now<nextBand)return;
        List<Resident> candidates=new ArrayList<>(residents.values().stream().filter(r->{Mob m=mob(r);return !r.disabled&&m!=null&&(!m.isPassenger()||reviewedDismount(r,m)!=null);}).toList());
        Collections.shuffle(candidates,random);
        if(candidates.size()<4){nextBand=now+600;return;}
        List<Location> stage=locations.stream().filter(l->l.policy().activities().contains("music")).toList();
        if(stage.size()!=4||stage.stream().anyMatch(l->conflicts(l,null))){nextBand=now+600;return;}
        for(int i=0;i<4;i++){Resident r=candidates.get(i);if(!setDestination(r,mob(r),stage.get(i),"gather",2400)){lastBandStop="gather_dismount_wait";endBand(now);return;}band.add(r);}
        gatheringDeadline=now+1200;
        persistBand();
    }
    void endBand(long now){
        if(band.isEmpty()&&performanceStart<0)return;
        for(Resident r:band){Mob m=mob(r);if(m==null||stand(r,m)){r.until=now+20+random.nextInt(300);r.activity="break";r.destination=null;}persist(r);}
        band.clear();performanceStart=-1;nextBand=now+600+random.nextInt(1201);
        persistBand();
    }
    void persistBand(){ledger.bandIds=String.join(",",band.stream().map(r->r.uuid.toString()).toList());ledger.performanceStart=performanceStart;ledger.performanceEnd=performanceEnd;ledger.nextBand=nextBand;ledger.setDirty();}

    void tick(ServerTickEvent.Post event){
        if(!loaded){
            if(event.getServer().getTickCount()%200!=0)return;
            if(!Files.isRegularFile(event.getServer().getServerDirectory().resolve("config/awft-tavern.json")))return;
            try{load(event.getServer());}catch(Exception e){fault=e.getMessage();return;}
        }
        long now=level().getGameTime();
        if(recoveryWindow!=null)recoveryWindow.poll(paused,server.getPlayerList().getPlayers().isEmpty());
        if(now%100==0&&statusWriter!=null){
            statusWriter.write(server.getServerDirectory().toAbsolutePath().getParent().resolve("dashboard/tavern/status.json"),status());
            if(!statusWriter.error.isEmpty()){fault=statusWriter.error;paused=true;}
        }
        if(paused||ledger.layoutHash.isEmpty())return;
        if(now%3!=0)return;
        long began=System.nanoTime();
        boolean nearby=level().players().stream().anyMatch(p->p.distanceToSqr(1302,66,-1279)<96*96);
        if(!nearby||!allChunksLoaded()){
            suspended=true;
            for(Resident r:residents.values()){Mob m=mob(r);if(m!=null){m.getNavigation().stop();if(!m.getMainHandItem().isEmpty())m.setItemSlot(EquipmentSlot.MAINHAND,ItemStack.EMPTY);}}
            return;
        }
        try{
            if(suspended&&performanceStart>=0&&now<performanceEnd){
                for(int i=0;i<band.size();i++){
                    Mob m=mob(band.get(i));if(m==null)continue;
                    ItemStack instrument=new ItemStack(BuiltInRegistries.ITEM.get(ResourceLocation.parse("immersive_melodies:"+INSTRUMENTS[i])));
                    ((InstrumentItem)instrument.getItem()).play(instrument,SONG,level(),m);
                    instrument.set(InstrumentItem.START_TIME,performanceStart);m.setItemSlot(EquipmentSlot.MAINHAND,instrument);
                }
            }
            suspended=false;
            ensemble(now);
            Resident r=new ArrayList<>(residents.values()).get(cursor++%residents.size());Mob m=mob(r);
            if(m==null)return;
            configure(m);
            if(r.disabled){if(stand(r,m)&&r.destination!=null){r.destination=null;persist(r);}return;}
            if(r.destination==null||(now>=r.until&&(r.arrived||now>r.travelDeadline))){if(!band.contains(r))decide(r,m,now);}
            move(r,m,now);lookAndTalk(r,m,now);
        }catch(Exception e){fault=e.toString();paused=true;for(Resident r:residents.values()){Mob m=mob(r);if(m!=null){m.getNavigation().stop();m.setItemSlot(EquipmentSlot.MAINHAND,ItemStack.EMPTY);}}}
        finally{schedulerNanos+=System.nanoTime()-began;}
    }

    void interact(PlayerInteractEvent.EntityInteract event){
        if(!loaded||event.getLevel().isClientSide()||!event.getTarget().getTags().contains(TAG))return;
        Resident r=residents.get(event.getTarget().getUUID());if(r==null)return;
        // Block the instrument pickup interaction; ordinary Easy NPC Config UI
        // is available outside these managed residents, with roster dialogue here.
        long now=level().getGameTime();
        if(now>=playerSpeechCooldown.getOrDefault(event.getEntity().getUUID(),0L)){
            playerSpeechCooldown.put(event.getEntity().getUUID(),now+200);
            Optional<String> line=chooseSpeech(r,now);
            if(line.isPresent()){
                recordSpeech(r,line.get(),now);
                event.getEntity().sendSystemMessage(Component.literal(r.profile.get("name").getAsString()+": "+line.get()));
                if(event.getTarget() instanceof Mob m&&!r.activity.equals("music")&&!r.activity.equals("gather"))m.getLookControl().setLookAt(event.getEntity(),10,10);
            }
        }
        event.setCanceled(true);
    }
    void protect(LivingIncomingDamageEvent event){if(event.getEntity().getTags().contains(TAG))event.setCanceled(true);}

    String status(){
        JsonObject root=new JsonObject();root.addProperty("at",java.time.Instant.now().toString());root.addProperty("layout_sha256",layoutHash);root.addProperty("fault",fault);root.addProperty("paused",paused);root.addProperty("music",music);
        root.addProperty("decisions",decisions);root.addProperty("path_requests",paths);root.addProperty("path_refusals",pathFailures);root.addProperty("scheduler_nanos",schedulerNanos);root.addProperty("nearby_dialogue_deliveries",conversations);
        root.addProperty("performance_start_tick",performanceStart);root.addProperty("runtime_accepted",false);
        root.addProperty("recovery_teleports",recoveries);root.addProperty("suspended",suspended);
        JsonObject reasons=new JsonObject();pathRefusalReasons.forEach(reasons::addProperty);root.add("path_refusal_reasons",reasons);
        root.addProperty("approved_rug_transit_cells",rugTransit.size());root.addProperty("next_band_tick",nextBand);root.addProperty("gathering_deadline_tick",gatheringDeadline);
        root.addProperty("adapter_version","0.1.14");root.addProperty("population_target",45);root.addProperty("speech_events",speechEvents);root.addProperty("speech_suppressed",speechSuppressed);root.addProperty("recent_global_lines",spoken.size());
        root.addProperty("drinks_started",drinksStarted);root.addProperty("native_drinks_finished",nativeDrinksFinished);
        if(recoveryWindow!=null)root.add("recovery_window",recoveryWindow.status());
        root.addProperty("path_planner","native_astar_surveyed_neighbors_cardinal");root.addProperty("paths_started",pathsStarted);root.addProperty("start_cell_escapes",startCellEscapes);
        root.addProperty("managed_seat_type_saveable",ManagedSeat.TYPE.get().canSerialize());
        root.addProperty("original_restores",originalRestores);root.addProperty("original_preserved",originalPreserved);root.addProperty("original_restore_refusals",originalRestoreRefusals);root.addProperty("last_original_restore",lastOriginalRestore);
        root.addProperty("profile_reconstructions",profileReconstructions);root.addProperty("profile_preserved",profilePreserved);root.addProperty("profile_reconstruction_refusals",profileReconstructionRefusals);root.addProperty("last_profile_reconstruction",lastProfileReconstruction);
        root.addProperty("gathering_failures",gatheringFailures);root.addProperty("completed_performances",completedPerformances);root.addProperty("last_band_stop",lastBandStop);
        root.addProperty("seat_dismounts",seatDismounts);root.addProperty("seat_dismount_waits",seatDismountWaits);
        JsonArray members=new JsonArray();band.forEach(r->members.add(r.profile.get("id").getAsString()));root.add("band_members",members);
        JsonArray actors=new JsonArray();for(Resident r:residents.values()){
            JsonObject a=new JsonObject();a.addProperty("id",r.profile.get("id").getAsString());a.addProperty("uuid",r.uuid.toString());a.addProperty("name",r.profile.get("name").getAsString());a.addProperty("loaded",mob(r)!=null);a.addProperty("disabled",r.disabled);a.addProperty("activity",!r.arrived&&r.destination!=null?"walking":r.activity);a.addProperty("next_activity",r.activity);a.addProperty("arrived",r.arrived);a.addProperty("destination",r.destination==null?"":r.destination.policy().id());a.addProperty("until_tick",r.until);a.addProperty("registered",ledger.data.contains(r.uuid.toString()));
            a.addProperty("last_path_refusal",r.lastPathRefusal);if(r.lastRefusedNode!=null)a.addProperty("last_refused_node",r.lastRefusedNode.toShortString());
            a.addProperty("recent_dialogue_count",r.spoken.size());a.addProperty("next_speech_tick",r.nextSpeech);
            a.addProperty("drink_starts",r.drinkStarts);a.addProperty("native_drink_finishes",r.drinkFinishes);a.addProperty("last_native_drink_result",r.lastNativeDrinkResult);
            Mob drinkMob=mob(r);if(drinkMob!=null){ItemStack hand=drinkMob.getMainHandItem();a.addProperty("held_item",hand.isEmpty()?"minecraft:air":BuiltInRegistries.ITEM.getKey(hand.getItem()).toString());a.addProperty("using_item",drinkMob.isUsingItem());a.addProperty("use_remaining_ticks",drinkMob.getUseItemRemainingTicks());a.addProperty("held_use_animation",hand.isEmpty()?"NONE":hand.getUseAnimation().name());}
            Mob m=mob(r);if(m!=null){JsonArray p=new JsonArray();p.add(m.getX());p.add(m.getY());p.add(m.getZ());a.add("position",p);a.addProperty("riding_seat",m.getVehicle() instanceof Seat);if(m.getVehicle() instanceof Seat seat){a.addProperty("seat_type",BuiltInRegistries.ENTITY_TYPE.getKey(seat.getType()).toString());a.addProperty("seat_saveable",seat.getType().canSerialize());if(seat instanceof ManagedSeat managed&&managed.resident()!=null)a.addProperty("seat_resident_uuid",managed.resident().toString());}var speed=m.getAttribute(Attributes.MOVEMENT_SPEED);if(speed!=null)a.addProperty("movement_speed",speed.getBaseValue());ItemStack held=m.getMainHandItem();if(held.getItem() instanceof InstrumentItem){a.addProperty("instrument",BuiltInRegistries.ITEM.getKey(held.getItem()).toString());a.addProperty("melody",InstrumentItem.getMelody(held).toString());a.addProperty("instrument_playing",held.getOrDefault(InstrumentItem.PLAYING,false));a.addProperty("instrument_start_tick",held.getOrDefault(InstrumentItem.START_TIME,-1L));}}actors.add(a);
        }root.add("residents",actors);return root.toString();
    }
    void commands(RegisterCommandsEvent event){
        event.getDispatcher().register(Commands.literal("awfttavern").requires(s->s.hasPermission(2))
            .then(Commands.literal("status").executes(c->{c.getSource().sendSuccess(()->Component.literal(loaded?status():fault),false);return 1;}))
            .then(Commands.literal("prepare-recovery").executes(c->{try{
                load(c.getSource().getServer());
                if(!paused||!server.getPlayerList().getPlayers().isEmpty())throw new IllegalStateException("recovery_requires_paused_scheduler_and_empty_server");
                if(!ledger.layoutHash.equals(layoutHash)||!layoutHash.equals("b2963d58e4dd14e542c24e2b926ddb76ead1a3a7b627a951a2fb348ca85929a4"))throw new IllegalStateException("recovery_layout_ledger_not_admitted");
                for(UUID id:OriginalRecovery.SOURCES.keySet()){if(!residents.containsKey(id)||!ledger.data.contains(id.toString()))throw new IllegalStateException("original_registered_identity_missing");OriginalRecovery.proveAbsent(server.getServerDirectory().resolve("config/awft-tavern-recovery"),id);}
                if(!residents.containsKey(OriginalRecovery.NIAMH)||!ledger.data.contains(OriginalRecovery.NIAMH.toString()))throw new IllegalStateException("niamh_registered_identity_missing");
                OriginalRecovery.proveAbsent(server.getServerDirectory().resolve("config/awft-tavern-recovery"),OriginalRecovery.NIAMH);
                if(recoveryWindow==null)recoveryWindow=new RecoveryWindow(level());recoveryWindow.start(paused,true);
                c.getSource().sendSuccess(()->Component.literal("Recovery prepare: "+recoveryWindow.status()),false);return 1;
            }catch(Exception e){if(recoveryWindow!=null&&recoveryWindow.active)recoveryWindow.fault("prepare_refused:"+e.getMessage());c.getSource().sendFailure(Component.literal("Recovery prepare refused: "+e.getMessage()));return 0;}}))
            .then(Commands.literal("finish-recovery").executes(c->{if(recoveryWindow==null){c.getSource().sendSuccess(()->Component.literal("Recovery finish: no owned window or tickets"),false);return 1;}recoveryWindow.finish("operator_finish");c.getSource().sendSuccess(()->Component.literal("Recovery finish: "+recoveryWindow.status()),false);return 1;}))
            .then(Commands.literal("restore-original").then(Commands.argument("uuid",StringArgumentType.word()).then(Commands.argument("gzip_sha256",StringArgumentType.word()).executes(c->{
                try{load(c.getSource().getServer());lastOriginalRestore=restoreOriginal(StringArgumentType.getString(c,"uuid"),StringArgumentType.getString(c,"gzip_sha256"));c.getSource().sendSuccess(()->Component.literal(lastOriginalRestore),false);return lastOriginalRestore.startsWith("Original restored:")?1:0;}
                catch(Exception e){if(recoveryWindow!=null&&recoveryWindow.active)recoveryWindow.fault("original_command_refused:"+e.getMessage());originalRestoreRefusals++;lastOriginalRestore="Original refused: "+e.getMessage();c.getSource().sendFailure(Component.literal(lastOriginalRestore));return 0;}
            }))))
            .then(Commands.literal("reconstruct-missing").then(Commands.argument("uuid",StringArgumentType.word()).then(Commands.argument("profile_sha256",StringArgumentType.word()).executes(c->{
                try{load(c.getSource().getServer());lastProfileReconstruction=reconstructMissing(StringArgumentType.getString(c,"uuid"),StringArgumentType.getString(c,"profile_sha256"));c.getSource().sendSuccess(()->Component.literal(lastProfileReconstruction),false);return lastProfileReconstruction.startsWith("Missing profile reconstructed:")?1:0;}
                catch(Exception e){if(recoveryWindow!=null&&recoveryWindow.active)recoveryWindow.fault("profile_command_refused:"+e.getMessage());profileReconstructionRefusals++;lastProfileReconstruction="Missing profile refused: "+e.getMessage();c.getSource().sendFailure(Component.literal(lastProfileReconstruction));return 0;}
            }))))
            .then(Commands.literal("suspend").then(Commands.argument("suspended",BoolArgumentType.bool()).executes(c->{
                if(!loaded)return 0;boolean stop=BoolArgumentType.getBool(c,"suspended");
                if(!stop&&!layout.get("spawn_admitted").getAsBoolean())return 0;
                paused=stop;
                if(stop)for(Resident r:residents.values()){Mob m=mob(r);if(m!=null){m.getNavigation().stop();m.stopUsingItem();m.setItemSlot(EquipmentSlot.MAINHAND,ItemStack.EMPTY);}}
                c.getSource().sendSuccess(()->Component.literal(stop?"Tavern scheduler suspended; entities and residency retained":"Tavern scheduler resumed; runtime acceptance remains pending"),false);return 1;
            })))
            .then(Commands.literal("inspect").executes(c->{try{load(c.getSource().getServer());verifyPreimage();c.getSource().sendSuccess(()->Component.literal("Exact saved preimage matches; native paths, seat geometry, audio and runtime acceptance remain pending. Layout SHA256: "+layoutHash),false);return 1;}catch(Exception e){c.getSource().sendFailure(Component.literal(e.toString()));return 0;}}))
            .then(Commands.literal("initialize").then(Commands.argument("layout_sha256",StringArgumentType.word()).executes(c->{
                try{load(c.getSource().getServer());int n=initialize(StringArgumentType.getString(c,"layout_sha256"));c.getSource().sendSuccess(()->Component.literal("New residents: "+n+"; acceptance pending"),false);return n;}
                catch(Exception e){c.getSource().sendFailure(Component.literal(e.toString()));return 0;}})))
            .then(Commands.literal("music").then(Commands.argument("enabled",BoolArgumentType.bool()).executes(c->{if(!loaded)return 0;music=BoolArgumentType.getBool(c,"enabled");ledger.music=music;ledger.setDirty();if(!music)endBand(level().getGameTime());else if(band.isEmpty()&&performanceStart<0){nextBand=level().getGameTime()+20;persistBand();}return 1;})))
            .then(Commands.literal("resident").then(Commands.argument("id",StringArgumentType.word())
                .then(Commands.literal("recover").executes(c->{
                    if(!loaded||paused)return 0;Resident r=residents.get(ActivityPolicy.identity(StringArgumentType.getString(c,"id")));if(r==null)return 0;
                    Mob m=mob(r);long now=level().getGameTime();
                    if(m==null||r.destination==null||r.arrived||r.lastPosition==null||now-r.stalledSince<600)return 0;
                    if(level().players().stream().anyMatch(p->p.distanceToSqr(m)<32*32||p.hasLineOfSight(m)))return 0;
                    BlockPos dest=r.destination.approach();
                    if(!level().hasChunkAt(dest)||!level().getBlockState(dest).isAir()||!level().getBlockState(dest.above()).isAir())return 0;
                    Vec3 target=Vec3.atBottomCenterOf(dest);
                    if(level().players().stream().anyMatch(p->p.distanceToSqr(target)<32*32)||!level().noCollision(m,m.getBoundingBox().move(target.subtract(m.position()))))return 0;
                    if(!stand(r,m))return 0;m.moveTo(target.x,target.y,target.z,m.getYRot(),0);r.stalledSince=now;recoveries++;return 1;
                }))
                .then(Commands.literal("enabled").then(Commands.argument("enabled",BoolArgumentType.bool()).executes(c->{Resident r=residents.get(ActivityPolicy.identity(StringArgumentType.getString(c,"id")));if(r==null)return 0;r.disabled=!BoolArgumentType.getBool(c,"enabled");if(r.disabled){if(band.contains(r))endBand(level().getGameTime());Mob m=mob(r);if(m==null||stand(r,m))r.destination=null;}persist(r);return 1;})))
                .then(Commands.literal("weight").then(Commands.argument("activity",StringArgumentType.word()).then(Commands.argument("weight",IntegerArgumentType.integer(1,12)).executes(c->{Resident r=residents.get(ActivityPolicy.identity(StringArgumentType.getString(c,"id")));String act=StringArgumentType.getString(c,"activity");if(r==null||!r.preferences.containsKey(act))return 0;r.preferences.put(act,IntegerArgumentType.getInteger(c,"weight"));persist(r);return 1;})))))));
    }

    public static final class Ledger extends SavedData {
        CompoundTag data=new CompoundTag(),speech=new CompoundTag();String layoutHash="";boolean music=true;
        String bandIds="";long performanceStart=-1,performanceEnd,nextBand;
        static Ledger read(CompoundTag n,HolderLookup.Provider lookup){Ledger l=new Ledger();l.data=n.getCompound("residents");l.speech=n.getCompound("speech");l.layoutHash=n.getString("layout_sha256");l.music=n.getBoolean("music");l.bandIds=n.getString("band_ids");l.performanceStart=n.contains("performance_start")?n.getLong("performance_start"):-1;l.performanceEnd=n.getLong("performance_end");l.nextBand=n.getLong("next_band");return l;}
        @Override public CompoundTag save(CompoundTag n,HolderLookup.Provider lookup){n.put("residents",data);n.put("speech",speech);n.putString("layout_sha256",layoutHash);n.putBoolean("music",music);n.putString("band_ids",bandIds);n.putLong("performance_start",performanceStart);n.putLong("performance_end",performanceEnd);n.putLong("next_band",nextBand);return n;}
    }
}
