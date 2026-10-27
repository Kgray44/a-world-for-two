package worldfortwo.bridge;

import com.google.gson.*;
import com.mojang.serialization.JsonOps;
import net.minecraft.network.Connection;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.network.codec.StreamCodec;
import net.minecraft.network.protocol.common.custom.CustomPacketPayload;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.server.packs.resources.ResourceManager;
import net.neoforged.fml.ModList;
import net.neoforged.fml.loading.FMLPaths;
import net.neoforged.neoforge.common.extensions.ICommonPacketListener;
import net.neoforged.neoforge.event.OnDatapackSyncEvent;
import net.neoforged.neoforge.network.PacketDistributor;
import net.neoforged.neoforge.network.event.RegisterPayloadHandlersEvent;
import net.neoforged.neoforge.network.registration.NetworkRegistry;
import software.bluelib.api.utils.variant.ParameterUtils;
import software.bluelib.loader.cache.ResourceCache;
import software.bluelib.loader.cache.variants.EntityCache;
import software.bluelib.loader.cache.variants.VariantCache;
import java.lang.reflect.Method;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.security.MessageDigest;
import java.time.Instant;
import java.util.*;
import java.util.concurrent.CompletableFuture;

/** Observes completed authoritative rendering metadata; never writes BlueLib's
 * server cache, entity variants, ownership, inventory, or resource-pack images. */
public final class DragonTextureMirror {
    private static final Gson JSON=new Gson();
    private static final int MAX_BYTES=512*1024,MAX_SPECIES=64,MAX_VARIANTS=512;
    private static final Set<String> RENDER_KEYS=Set.of("adult","child","hasGender","glowing");
    public static final CustomPacketPayload.Type<Snapshot> TYPE=new CustomPacketPayload.Type<>(ResourceLocation.fromNamespaceAndPath("awft_control_bridge","dragon_render_metadata"));
    public record Snapshot(long generation,String json) implements CustomPacketPayload {
        public static final StreamCodec<RegistryFriendlyByteBuf,Snapshot> CODEC=new StreamCodec<>() {
            public Snapshot decode(RegistryFriendlyByteBuf buf){return new Snapshot(buf.readLong(),new String(buf.readByteArray(MAX_BYTES),StandardCharsets.UTF_8));}
            public void encode(RegistryFriendlyByteBuf buf,Snapshot value){byte[] raw=value.json.getBytes(StandardCharsets.UTF_8);if(raw.length>MAX_BYTES)throw new IllegalArgumentException("Dragon metadata exceeds exact wire byte bound");buf.writeLong(value.generation);buf.writeByteArray(raw);}
        };
        public Type<? extends CustomPacketPayload> type(){return TYPE;}
    }
    private static volatile DragonTextureMirror instance;
    private Snapshot serverSnapshot;
    private MinecraftServer serverOwner;
    private Map<ResourceLocation,EntityCache> completedIdentity;
    private final Map<UUID,ServerPlayer> queuedRecipients=new LinkedHashMap<>();
    private CompletableFuture<?> pendingReload;
    private long generation,reloadSerial;
    private int queuedSyncEvents;
    private static Map<ResourceLocation,EntityCache> client=Map.of();
    private static Connection clientConnection;
    private static long clientGeneration,resourceGeneration;
    private static final Map<String,Object> witnesses=new LinkedHashMap<>();
    private static final Map<ResourceLocation,Boolean> resources=new HashMap<>();
    private static String snapshotSha="none";
    private static Method minecraftInstance,minecraftConnection,minecraftResources;

    public DragonTextureMirror(){instance=this;}
    private static boolean supported(){
        var mods=ModList.get();
        return mods.isLoaded("bdd")&&mods.isLoaded("bluelib")
            &&mods.getModContainerById("bdd").orElseThrow().getModInfo().getVersion().toString().equals("1.3.0-alpha")
            &&mods.getModContainerById("bluelib").orElseThrow().getModInfo().getVersion().toString().equals("2.4.3");
    }
    public void payloads(RegisterPayloadHandlersEvent event){
        event.registrar("1").optional().playToClient(TYPE,Snapshot.CODEC,(data,context)->{
            Connection connection=context.connection();
            context.enqueueWork(()->{
                if(!currentConnection(connection))return;
                try{accept(data,connection);}
                catch(Exception error){clearClient();System.err.println("AWFT dragon metadata refused: "+error);}
            });
        });
    }
    public void sync(OnDatapackSyncEvent event){
        if(!supported())return;
        // BlueLib clears/loads asynchronously on this event. Actual future
        // completion, not event priority or a guessed delay, permits publication.
        queuedSyncEvents=Math.min(queuedSyncEvents+1,1024);
        MinecraftServer server=event.getPlayerList().getServer();
        event.getRelevantPlayers().forEach(player->{if(queuedRecipients.size()<64||queuedRecipients.containsKey(player.getUUID()))queuedRecipients.put(player.getUUID(),player);});
        // A completed startup snapshot may precede login/channel negotiation.
        // Replay only a genuinely completed still-current cache, never the
        // temporary empty map installed at the beginning of another reload.
        if(serverOwner==server&&pendingReload==null&&serverSnapshot!=null
                &&completedIdentity==ResourceCache.Server.getVariants())sendCompleted(server,serverSnapshot);
    }
    public static void trackReload(MinecraftServer server,CompletableFuture<?> completed){
        DragonTextureMirror mirror=instance;
        if(mirror==null||completed==null||!supported())return;
        if(!server.isSameThread()){server.execute(()->trackReload(server,completed));return;}
        mirror.serverOwner=server;mirror.pendingReload=completed;long token=++mirror.reloadSerial;
        completed.whenComplete((ignored,error)->server.execute(()->{
            if(instance!=mirror||mirror.serverOwner!=server||mirror.reloadSerial!=token||mirror.pendingReload!=completed)return;
            mirror.pendingReload=null;mirror.publishCompleted(server,error);
        }));
    }
    private void publishCompleted(MinecraftServer server,Throwable failure){
        try{
            JsonObject root=new JsonObject();int variants=0;
            if(failure==null){
                Map<ResourceLocation,EntityCache> actual=ResourceCache.Server.getVariants();
                for(var row:actual.entrySet()){
                    if(!row.getKey().getNamespace().equals("bdd"))continue;
                    if(root.size()>=MAX_SPECIES||(variants+=row.getValue().variants().size())>MAX_VARIANTS)throw new IllegalStateException("BDD species/variant bound exceeded");
                    Map<String,VariantCache> rendering=new LinkedHashMap<>();
                    for(String name:row.getValue().variants().keySet()){
                        if(name.length()>128)throw new IllegalStateException("BDD variant name exceeds bound");
                        JsonArray parameters=new JsonArray();
                        for(String key:RENDER_KEYS){
                            // BDD's exact native default-parameter resolution for
                            // an EXISTING authoritative variant, never a new name.
                            JsonElement value=ParameterUtils.getParameterDataForVariant(row.getKey(),name,key,row.getKey().getPath());
                            if(value!=null&&!value.isJsonNull()){
                                if(!value.isJsonPrimitive())throw new IllegalStateException("Native render parameter is not scalar");
                                JsonObject parameter=new JsonObject();parameter.add(key,value.deepCopy());parameters.add(parameter);
                            }
                        }
                        rendering.put(name,new VariantCache(parameters));
                    }
                    root.add(row.getKey().toString(),EntityCache.CODEC.encodeStart(JsonOps.INSTANCE,new EntityCache(row.getValue().formatVersion(),rendering)).getOrThrow());
                }
            }
            String json=JSON.toJson(root);if(json.getBytes(StandardCharsets.UTF_8).length>MAX_BYTES)throw new IllegalStateException("BDD payload allocation exceeded");
            serverSnapshot=new Snapshot(++generation,json);completedIdentity=ResourceCache.Server.getVariants();
            int sent=sendCompleted(server,serverSnapshot);
            System.out.println("AWFT completed dragon metadata: species="+root.size()+", variants="+variants+", generation="+generation+", recipients="+sent+", queued_sync_events="+queuedSyncEvents+", reload_failed="+(failure!=null));
            queuedSyncEvents=0;
            if(failure!=null)System.err.println("AWFT BlueLib reload failed; explicit empty render snapshot published: "+failure);
        }catch(Exception error){
            serverSnapshot=null;completedIdentity=null;System.err.println("AWFT authoritative dragon snapshot unavailable: "+error);
            // Rejecting a generation must not silently retain an older reload.
            Snapshot unavailable=new Snapshot(++generation,"{}");
            sendCompleted(server,unavailable);
        }
    }
    private int sendCompleted(MinecraftServer server,Snapshot snapshot){
        Map<UUID,ServerPlayer> recipients=new LinkedHashMap<>(queuedRecipients);
        for(var player:server.getPlayerList().getPlayers())recipients.put(player.getUUID(),player);
        int sent=0;
        for(var player:recipients.values())try{
            // The actual NeoForge listener implements this injected interface;
            // the named vanilla compile class deliberately lacks that patch.
            if(NetworkRegistry.hasChannel((ICommonPacketListener)(Object)player.connection,TYPE.id())){
                PacketDistributor.sendToPlayer(player,snapshot);queuedRecipients.remove(player.getUUID());sent++;
            }
        }catch(Exception error){queuedRecipients.remove(player.getUUID());System.err.println("AWFT dragon recipient unavailable: "+error);}
        return sent;
    }
    public void stopped(){serverSnapshot=null;completedIdentity=null;queuedRecipients.clear();serverOwner=null;pendingReload=null;reloadSerial++;generation=0;queuedSyncEvents=0;}
    private static Object minecraft()throws Exception{
        if(minecraftInstance==null){Class<?> type=Class.forName("net.minecraft.client.Minecraft");minecraftInstance=type.getMethod("getInstance");minecraftConnection=type.getMethod("getConnection");minecraftResources=type.getMethod("getResourceManager");}
        return minecraftInstance.invoke(null);
    }
    private static boolean currentConnection(Connection connection){
        if(connection==null||!connection.isConnected())return false;
        try{Object game=minecraft();return minecraftConnection.invoke(game)==connection.getPacketListener();}
        catch(Exception error){return false;}
    }
    static Map<ResourceLocation,EntityCache> decodeSnapshot(Snapshot snapshot){
        if(snapshot.generation<=0||snapshot.json.getBytes(StandardCharsets.UTF_8).length>MAX_BYTES)throw new IllegalArgumentException("Invalid dragon generation/size");
        JsonObject root=JsonParser.parseString(snapshot.json).getAsJsonObject();if(root.size()>MAX_SPECIES)throw new IllegalArgumentException("Too many BDD species");
        Map<ResourceLocation,EntityCache> next=new LinkedHashMap<>();int count=0;
        for(var row:root.entrySet()){
            ResourceLocation key=ResourceLocation.parse(row.getKey());if(!key.getNamespace().equals("bdd"))throw new IllegalArgumentException("Non-BDD metadata refused");
            EntityCache decoded=EntityCache.CODEC.parse(JsonOps.INSTANCE,row.getValue()).getOrThrow();
            if(decoded.formatVersion().length()>64||(count+=decoded.variants().size())>MAX_VARIANTS)throw new IllegalArgumentException("BDD identity/count bound exceeded");
            Map<String,VariantCache> variants=new LinkedHashMap<>();
            for(var variant:decoded.variants().entrySet()){
                JsonArray original=variant.getValue().parameters();if(variant.getKey().length()>128||original==null||original.size()>RENDER_KEYS.size())throw new IllegalArgumentException("Variant render parameters exceed bound");
                Set<String> names=new HashSet<>();
                for(JsonElement parameter:original){if(!parameter.isJsonObject()||parameter.getAsJsonObject().size()!=1)throw new IllegalArgumentException("Only exact scalar render parameters allowed");
                    for(var value:parameter.getAsJsonObject().entrySet())if(!RENDER_KEYS.contains(value.getKey())||!names.add(value.getKey())||!value.getValue().isJsonPrimitive())throw new IllegalArgumentException("Unknown/duplicate/non-scalar rendering parameter");}
                variants.put(variant.getKey(),new VariantCache(original.deepCopy()));
            }
            next.put(key,new EntityCache(decoded.formatVersion(),Map.copyOf(variants)));
        }
        return Map.copyOf(next);
    }
    private static void accept(Snapshot snapshot,Connection connection)throws Exception{
        if(!currentConnection(connection))return;
        if(clientConnection==connection&&snapshot.generation<clientGeneration)return;
        Map<ResourceLocation,EntityCache> next=decodeSnapshot(snapshot);
        client=next;clientConnection=connection;clientGeneration=snapshot.generation;
        snapshotSha=HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(snapshot.json.getBytes(StandardCharsets.UTF_8)));
        witnesses.clear();resources.clear();int count=next.values().stream().mapToInt(entity->entity.variants().size()).sum();
        witness("snapshot",Map.of("species",next.size(),"variants",count,"generation",clientGeneration,"cache_isolated",true));
    }
    public static JsonElement textureParameter(ResourceLocation species,String variant,String key,JsonElement original){
        if(original!=null&&!original.isJsonNull())return original;
        if(!RENDER_KEYS.contains(key)||!currentConnection(clientConnection)||!species.getNamespace().equals("bdd"))return original;
        EntityCache entity=client.get(species);VariantCache actual=entity==null?null:entity.variants().get(variant);JsonElement value=actual==null?null:actual.getParameter(key);
        String id=species+"/"+variant+"/"+key;
        if(!witnesses.containsKey(id))witness(id,Map.of("original_parameter_missing",true,"authoritative_species",entity!=null,"existing_synced_variant",variant,"authoritative_variant",actual!=null,"parameter_present",value!=null&&!value.isJsonNull()));
        return value==null||value.isJsonNull()?original:value.deepCopy();
    }
    public static void checkResource(ResourceLocation resource){
        if(resource==null||resources.containsKey(resource)||resources.size()>=2048)return;
        try{
            Object game=minecraft();checkResource((ResourceManager)minecraftResources.invoke(game),resource);
        }catch(Exception error){witness("resource-check-unavailable",Map.of("error",error.toString()));}
    }
    public static void checkResource(ResourceManager manager,ResourceLocation resource){
        if(resource==null||resources.containsKey(resource)||resources.size()>=2048)return;
        var value=manager.getResource(resource);boolean exists=value.isPresent();resources.put(resource,exists);
        witness("resource:"+resource,Map.of("resource",resource.toString(),"exists",exists,"source_pack",value.map(r->r.sourcePackId()).orElse("none"),"replacement",false,"resource_generation",resourceGeneration));
    }
    public static void clearResources(){
        resources.clear();resourceGeneration++;
        witnesses.keySet().removeIf(key->key.startsWith("resource:")||key.equals("resource-check-unavailable")||key.startsWith("resource-reload:"));
        witness("resource-reload:"+resourceGeneration,Map.of("resource_generation",resourceGeneration));
    }
    public static void clearClient(){client=Map.of();clientConnection=null;clientGeneration=0;resources.clear();witnesses.clear();snapshotSha="none";resourceGeneration++;}
    private static void witness(String key,Object value){
        if(witnesses.size()>=256||witnesses.containsKey(key))return;witnesses.put(key,value);
        try{
            Path path=FMLPaths.GAMEDIR.get().resolve("logs/awft-dragon-render.json");Files.createDirectories(path.getParent());Path temp=path.resolveSibling(path.getFileName()+".tmp");
            Files.writeString(temp,JSON.toJson(Map.of("format","awft-dragon-render:1","at",Instant.now().toString(),"generation",clientGeneration,"resource_generation",resourceGeneration,"metadata_sha256",snapshotSha,"witnesses",witnesses,"entity_or_variant_writes",0,"texture_aliases",0)));
            Files.move(temp,path,StandardCopyOption.REPLACE_EXISTING,StandardCopyOption.ATOMIC_MOVE);
        }catch(Exception error){System.err.println("AWFT dragon render witness: "+error);}
    }
}
