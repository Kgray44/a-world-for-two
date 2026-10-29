package worldfortwo.living;

import com.google.gson.*;
import net.minecraft.commands.Commands;
import net.minecraft.commands.arguments.EntityArgument;
import net.minecraft.network.chat.Component;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.Entity;
import net.neoforged.fml.common.Mod;
import net.neoforged.fml.loading.FMLPaths;
import net.neoforged.neoforge.common.NeoForge;
import net.neoforged.neoforge.event.RegisterCommandsEvent;
import net.neoforged.neoforge.event.server.*;
import net.neoforged.neoforge.event.tick.ServerTickEvent;
import java.nio.file.*;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.time.Instant;
import java.util.*;
import java.util.concurrent.*;
import java.util.function.BooleanSupplier;
import tn.naizo.smartvillagers.ai.*;

/** Own mod: no bridge edits, no world generation, no entity spawning, no command execution. */
@Mod("awft_living_world")
public final class LivingWorld {
    private static final Gson GSON=new GsonBuilder().setPrettyPrinting().create();
    private static final Path CONFIG=FMLPaths.CONFIGDIR.get().resolve("awft-living-world.json");
    private static final Path STATE=FMLPaths.GAMEDIR.get().resolve("../dashboard/characters").normalize();
    private static volatile ExecutorService io;
    private static volatile String hash="",error="Not loaded";
    private static volatile boolean writing;
    private static long guardAt;
    private static volatile WatchService watcher;
    private static volatile Thread watchThread;
    private static volatile long lifecycle;
    private static final RequestSlots<AiResponse> requests=new RequestSlots<>();
    private long ticks;
    public LivingWorld(){
        NeoForge.EVENT_BUS.addListener(this::commands);
        NeoForge.EVENT_BUS.addListener(this::started);
        NeoForge.EVENT_BUS.addListener(this::stopped);
        NeoForge.EVENT_BUS.addListener(this::tick);
    }
    private void started(ServerStartedEvent event){
        lifecycle++;
        io=new ThreadPoolExecutor(1,1,0,TimeUnit.SECONDS,new ArrayBlockingQueue<>(4),r->{Thread t=new Thread(r,"awft-characters-io");t.setDaemon(true);return t;},new ThreadPoolExecutor.AbortPolicy());
        requests.open();
        reload(event.getServer());
        watch(event.getServer());
    }
    private void stopped(ServerStoppingEvent event){
        lifecycle++;
        ExecutorService owned=io;io=null;requests.close(AiResponse.failure("Server stopping; conversation cancelled"));if(owned!=null)owned.shutdownNow();
        WatchService ownedWatcher=watcher;watcher=null;if(ownedWatcher!=null)try{ownedWatcher.close();}catch(Exception ignored){}
        Thread ownedThread=watchThread;watchThread=null;if(ownedThread!=null)ownedThread.interrupt();
        WorldCharacters.current=new WorldCharacters(new JsonObject());hash="";error="Server stopping";
    }
    private static boolean space(long extra){
        try{for(String drive:List.of("C:\\","D:\\"))if(Files.getFileStore(Path.of(drive)).getUsableSpace()-extra<=32212254720L)return false;return true;}
        catch(Exception ignored){return false;}
    }
    private static void atomic(Path path,String value)throws Exception{
        safePath(path);
        byte[] bytes=value.getBytes(StandardCharsets.UTF_8);
        if(bytes.length>1024*1024||!space(bytes.length*2L+8192))throw new IllegalStateException("Storage reserve or file bound reached");
        if(System.nanoTime()-guardAt>TimeUnit.MINUTES.toNanos(5)||guardAt==0){
            String drive=path.toAbsolutePath().getRoot().toString().toUpperCase(Locale.ROOT);
            if(!drive.equals("C:\\")&&!drive.equals("D:\\"))throw new IllegalStateException("Unknown allocation drive");
            Process guard=new ProcessBuilder("powershell.exe","-NoProfile","-NonInteractive","-WindowStyle","Hidden","-ExecutionPolicy","Bypass","-File",
                "C:\\Users\\kkids\\AppData\\Local\\AeroStorageWatch\\ReserveGuard.ps1","-EstimatedCBytes",drive.equals("C:\\")?"4194304":"0","-EstimatedDBytes",drive.equals("D:\\")?"4194304":"0").redirectErrorStream(true).redirectOutput(ProcessBuilder.Redirect.DISCARD).start();
            if(!guard.waitFor(15,TimeUnit.SECONDS)){guard.destroyForcibly();throw new IllegalStateException("Storage guard timeout");}
            if(guard.exitValue()!=0)throw new IllegalStateException("Storage reserve guard refused allocation");
            guardAt=System.nanoTime();
        }
        Files.createDirectories(path.getParent());Path temporary=Files.createTempFile(path.getParent(),".awft-living-",".tmp");
        try{Files.write(temporary,bytes);Files.move(temporary,path,StandardCopyOption.REPLACE_EXISTING,StandardCopyOption.ATOMIC_MOVE);}
        finally{Files.deleteIfExists(temporary);}
    }
    private static void safePath(Path path)throws Exception{
        Path existing=path.toAbsolutePath().normalize();
        while(!Files.exists(existing,LinkOption.NOFOLLOW_LINKS))existing=existing.getParent();
        if(Files.isSymbolicLink(existing)||!existing.toRealPath().equals(existing))throw new IllegalStateException("Linked runtime paths refused");
    }
    /** Same byte-zero lock as the dashboard; busy admission fails without retries. */
    private static SharedSpendingLock spendingLock()throws Exception{
        Path path=STATE.resolve("spending.lock");safePath(path);
        if(!space(8192))throw new IllegalStateException("Storage reserve reached");
        Files.createDirectories(path.getParent());
        return SharedSpendingLock.acquire(path);
    }
    private static void seedPreview(JsonObject ledger,long now)throws Exception{
        String day=Instant.ofEpochMilli(now).atZone(java.time.ZoneOffset.UTC).toLocalDate().toString();
        if(day.equals(WorldCharacters.text(ledger,"preview_day")))return;
        Path registry=STATE.resolve("registry.json");safePath(registry);
        double reserved=0;long count=0;JsonArray recent=new JsonArray();
        if(Files.exists(registry)){
            if(Files.size(registry)>8*1024*1024)throw new IllegalStateException("Preview history exceeds its bound");
            byte[] raw;try(var stream=Files.newInputStream(registry)){raw=stream.readNBytes(8*1024*1024+1);}
            if(raw.length>8*1024*1024)throw new IllegalStateException("Preview history exceeds its bound");
            JsonObject state=JsonParser.parseString(new String(raw,StandardCharsets.UTF_8)).getAsJsonObject();
            for(JsonElement entry:WorldCharacters.array(state,"usage")){
                JsonObject row=entry.getAsJsonObject();double epoch=row.get("time").getAsDouble();
                double charge=row.get("reserved_usd").getAsDouble();
                if(!Double.isFinite(epoch)||epoch<0||!Double.isFinite(charge)||charge<0)throw new IllegalStateException("Preview history is invalid");
                long at=(long)(epoch*1000);String recorded=Instant.ofEpochMilli(at).atZone(java.time.ZoneOffset.UTC).toLocalDate().toString();
                if(day.equals(recorded)){reserved+=charge;count++;}
                if(now-at<86400000L){
                    String character=WorldCharacters.text(row,"id"),requestId=WorldCharacters.text(row,"request_id");
                    if(requestId.isEmpty())requestId=HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest((character+"|"+row.get("time").getAsString()).getBytes(StandardCharsets.UTF_8))).substring(0,32);
                    JsonObject safe=new JsonObject();safe.addProperty("at",at);safe.addProperty("id",requestId);
                    safe.addProperty("character",character.matches("[a-z0-9_-]{1,64}")?character:"__preview__");recent.add(safe);
                }
            }
        }
        if(!Double.isFinite(reserved))throw new IllegalStateException("Preview reservation total is invalid");
        while(recent.size()>128)recent.remove(0);
        ledger.addProperty("preview_day",day);ledger.addProperty("preview_reserved_usd",reserved);
        ledger.addProperty("preview_day_requests",count);ledger.add("preview_recent",recent);
    }
    private static void reload(MinecraftServer server){
        ExecutorService owned=io;long epoch=lifecycle;if(owned==null)return;
        try{owned.execute(()->{
            try{
                Path source=Files.exists(STATE.resolve("runtime.json"))?STATE.resolve("runtime.json"):CONFIG;
                safePath(source);
                if(Files.isSymbolicLink(source)||Files.size(source)>1024*1024)throw new IllegalArgumentException("Configuration missing or exceeds 1 MiB");
                byte[] raw;try(var stream=Files.newInputStream(source)){raw=stream.readNBytes(1024*1024+1);}
                if(raw.length>1024*1024)throw new IllegalArgumentException("Configuration exceeds 1 MiB");
                JsonObject document=JsonParser.parseString(new String(raw,StandardCharsets.UTF_8)).getAsJsonObject();
                if(!WorldCharacters.text(document,"format").equals("awft-living-world:1"))throw new IllegalArgumentException("Unknown configuration format");
                WorldCharacters next=new WorldCharacters(document);
                String digest=HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(raw));
                server.execute(()->{if(io==owned&&lifecycle==epoch){WorldCharacters.current=next;hash=digest;error="";}});
            }catch(Exception ignored){server.execute(()->{if(io==owned&&lifecycle==epoch){WorldCharacters.current=new WorldCharacters(new JsonObject());hash="";error="Configuration rejected; scripted upstream dialogue remains available";}});}
        });}catch(RejectedExecutionException ignored){error="Configuration worker busy";}
    }
    private static void watch(MinecraftServer server){
        ExecutorService owned=io;if(owned==null)return;
        try{owned.execute(()->{
            try{
                // The same guarded writer creates the directory before registering native events.
                atomic(STATE.resolve("adapter.json"),"{\"format\":\"awft-living-world-adapter:1\",\"version\":\"0.2.0\"}");
                WatchService own=FileSystems.getDefault().newWatchService();
                STATE.register(own,StandardWatchEventKinds.ENTRY_CREATE,StandardWatchEventKinds.ENTRY_MODIFY,StandardWatchEventKinds.ENTRY_DELETE);
                watcher=own;
                Thread thread=new Thread(()->{
                    try{
                        while(io!=null&&watcher==own){
                            WatchKey key=own.take();boolean changed=false;
                            for(WatchEvent<?> event:key.pollEvents())if(event.kind()==StandardWatchEventKinds.OVERFLOW||event.context().toString().equals("runtime.json"))changed=true;
                            if(!key.reset())break;if(changed)reload(server);
                        }
                    }catch(InterruptedException|ClosedWatchServiceException ignored){}
                },"awft-characters-watch");thread.setDaemon(true);watchThread=thread;thread.start();
                reload(server); // Covers a save between the first load and watcher registration.
            }catch(Exception ignored){error="Automatic apply watcher unavailable; use operator reload and verify acknowledgement";}
        });}catch(RejectedExecutionException ignored){error="Character watcher unavailable";}
    }
    private void commands(RegisterCommandsEvent event){
        event.getDispatcher().register(Commands.literal("awftcharacters").requires(s->s.hasPermission(2))
            .then(Commands.literal("reload").executes(c->{reload(c.getSource().getServer());c.getSource().sendSuccess(()->Component.literal("Character reload requested. Verify the acknowledged configuration hash in Control Room."),false);return 1;}))
            .then(Commands.literal("status").executes(c->{c.getSource().sendSuccess(()->Component.literal("Living World config "+(hash.isBlank()?error:hash)+"; bound profiles "+WorldCharacters.current.entities().size()),false);return 1;}))
            .then(Commands.literal("inspect").then(Commands.argument("entity",EntityArgument.entity()).executes(c->{Entity entity=EntityArgument.getEntity(c,"entity");c.getSource().sendSuccess(()->Component.literal("Existing entity UUID: "+entity.getUUID()+"; dimension: "+entity.level().dimension().location()+"; this command changes nothing."),false);return 1;}))));
    }
    private void tick(ServerTickEvent.Post event){
        if(++ticks%300!=0||writing||io==null)return;
        // Ten configured identities by default; direct loaded-entity lookups never request chunks.
        JsonArray characters=new JsonArray();
        for(String id:WorldCharacters.current.entities()){
            JsonObject row=new JsonObject();row.addProperty("entity_uuid",id);row.addProperty("loaded",false);
            for(ServerLevel level:event.getServer().getAllLevels()){
                Entity entity=level.getEntity(UUID.fromString(id));if(entity==null)continue;
                row.addProperty("loaded",true);row.addProperty("dimension",level.dimension().location().toString());
                row.addProperty("x",entity.getX());row.addProperty("y",entity.getY());row.addProperty("z",entity.getZ());break;
            }
            characters.add(row);
        }
        JsonObject value=new JsonObject();value.addProperty("format","awft-living-world-state:1");value.addProperty("at",Instant.now().toString());
        value.addProperty("adapter_version","0.2.0");
        JsonArray capabilities=new JsonArray();for(String capability:List.of("per_character_model","generation_policy","verified_model_gate","returned_usage"))capabilities.add(capability);
        value.add("capabilities",capabilities);
        value.addProperty("pid",ProcessHandle.current().pid());value.addProperty("process_started",ProcessHandle.current().info().startInstant().orElse(Instant.EPOCH).toString());
        value.addProperty("config_sha256",hash);value.addProperty("revision",WorldCharacters.current.revision());value.addProperty("error",error);value.add("characters",characters);
        value.add("provider",NativeRequestPolicy.providerState());
        writing=true;
        try{io.execute(()->{try{atomic(STATE.resolve("native.json"),GSON.toJson(value));}catch(Exception ignored){}finally{writing=false;}});}
        catch(RejectedExecutionException ignored){writing=false;}
    }
    /** Persist a conservative maximum charge before reusing upstream's asynchronous transport. */
    public static CompletableFuture<AiResponse> request(AiProvider provider,AiRequest request,MinecraftServer server,String character,BooleanSupplier stillAllowed){
        ExecutorService owned=io;if(owned==null)return CompletableFuture.completedFuture(AiResponse.failure("Character service unavailable"));
        WorldCharacters configuration=WorldCharacters.current;
        NativeRequestPolicy.Policy policy;
        try{
            if(!NativeRequestPolicy.credentialPresent())throw new IllegalStateException();
            policy=NativeRequestPolicy.select(configuration,character);
        }catch(Exception ignored){return CompletableFuture.completedFuture(AiResponse.failure("Dedicated credential or verified character model unavailable; scripted fallback"));}
        int cap=Math.max(1,Math.min(2,WorldCharacters.integer(WorldCharacters.current.settings(),"max_concurrent",2)));
        var lease=requests.acquire(cap);
        if(lease==null)return CompletableFuture.completedFuture(AiResponse.failure("Character concurrency limit; scripted fallback"));
        CompletableFuture<AiResponse> result=lease.future();
        long epoch=lifecycle;
        try{owned.execute(()->{
            try{
                JsonObject settings=configuration.settings();
                try(var shared=spendingLock()){
                    Path ledger=STATE.resolve("native-budget.json");JsonObject usage=new JsonObject();safePath(ledger);
                    if(Files.exists(ledger)){
                        if(Files.size(ledger)>NativeUsage.MAX_LEDGER_BYTES)throw new IllegalStateException();usage=JsonParser.parseString(Files.readString(ledger)).getAsJsonObject();
                    }
                    long now=System.currentTimeMillis();seedPreview(usage,now);
                    int inputBound=NativeRequestPolicy.reservationBytes(policy,PromptBuilder.buildSystemPrompt(request.context()),PromptBuilder.buildUserPrompt(request.playerMessage()));
                    NativeUsage.reserve(usage,policy,settings,WorldCharacters.object(configuration.profileById(character),"ai"),character,now,inputBound);
                    String reserved=GSON.toJson(usage);if(reserved.getBytes(StandardCharsets.UTF_8).length>NativeUsage.MAX_LEDGER_BYTES)throw new IllegalStateException();atomic(ledger,reserved);
                }
                // Recheck loaded entities, consent and the exact configuration on the server executor
                // after disk admission, immediately before upstream's nonblocking sendAsync call.
                server.execute(()->{
                    try{
                    if(io!=owned||lifecycle!=epoch||!stillAllowed.getAsBoolean()){lease.complete(AiResponse.failure("Conversation no longer active; scripted fallback"));return;}
                    if(!lease.start()){lease.complete(AiResponse.failure("Conversation cancelled before provider dispatch"));return;}
                    CompletableFuture<AiResponse> upstream;
                    try(var scope=NativeRequestPolicy.enter(policy)){upstream=provider.complete(request);}
                    // Never mutate the provider future with orTimeout: a logical deadline
                    // is not proof that its underlying HTTP exchange has terminated.
                    CompletableFuture.delayedExecutor(policy.timeoutSeconds(),TimeUnit.SECONDS).execute(()->{
                        if(lease.future().isDone())return;
                        policy.capture().deadline();recordUsage(owned,epoch,policy,"deadline");
                        lease.timeout(AiResponse.failure("Provider response deadline; scripted fallback"));
                    });
                    upstream.whenComplete((answer,failure)->{
                        lease.networkFinished();
                        recordUsage(owned,epoch,policy,failure==null&&answer!=null&&answer.ok()?"ok":"provider_error");
                        if(io!=owned||lifecycle!=epoch){lease.complete(AiResponse.failure("Conversation runtime ended"));return;}
                        try{server.execute(()->{
                            try{
                                if(io!=owned||lifecycle!=epoch||!stillAllowed.getAsBoolean()){lease.complete(AiResponse.failure("Conversation permission changed before response"));return;}
                                lease.complete(failure!=null?AiResponse.failure("Provider unavailable; scripted fallback"):answer);
                            }catch(Exception ignored){lease.complete(AiResponse.failure("Conversation no longer available"));}
                        });}catch(Exception ignored){lease.complete(AiResponse.failure("Conversation runtime ended"));}
                    });}catch(Exception ignored){lease.complete(AiResponse.failure("Provider unavailable; scripted fallback"));}
                });
            }catch(Exception ignored){lease.complete(AiResponse.failure("AI budget, pricing or storage gate unavailable; scripted fallback"));}
        });}catch(RejectedExecutionException ignored){lease.complete(AiResponse.failure("Character worker busy; scripted fallback"));}
        return result;
    }
    private static void recordUsage(ExecutorService owned,long epoch,NativeRequestPolicy.Policy policy,String terminal){
        if(io!=owned||lifecycle!=epoch)return;
        JsonObject observed=policy.capture().snapshot(terminal);
        try{owned.execute(()->{
            if(io!=owned||lifecycle!=epoch)return;
            try(var shared=spendingLock()){
                Path ledger=STATE.resolve("native-budget.json");safePath(ledger);
                if(!Files.isRegularFile(ledger)||Files.size(ledger)>NativeUsage.MAX_LEDGER_BYTES)return;
                JsonObject usage=JsonParser.parseString(Files.readString(ledger)).getAsJsonObject();
                NativeUsage.finish(usage,policy.capture().id(),observed);
                String data=GSON.toJson(usage);if(data.getBytes(StandardCharsets.UTF_8).length<=NativeUsage.MAX_LEDGER_BYTES)atomic(ledger,data);
            }catch(Exception ignored){/* A missing receipt remains unknown; no synthetic usage is substituted. */}
        });}catch(RejectedExecutionException ignored){/* Admission receipt remains available; returned usage may be unknown. */}
    }
}
