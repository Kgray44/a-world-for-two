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
                atomic(STATE.resolve("adapter.json"),"{\"format\":\"awft-living-world-adapter:1\",\"version\":\"0.1.0\"}");
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
        value.addProperty("pid",ProcessHandle.current().pid());value.addProperty("process_started",ProcessHandle.current().info().startInstant().orElse(Instant.EPOCH).toString());
        value.addProperty("config_sha256",hash);value.addProperty("revision",WorldCharacters.current.revision());value.addProperty("error",error);value.add("characters",characters);
        writing=true;
        try{io.execute(()->{try{atomic(STATE.resolve("native.json"),GSON.toJson(value));}catch(Exception ignored){}finally{writing=false;}});}
        catch(RejectedExecutionException ignored){writing=false;}
    }
    /** Persist a conservative maximum charge before reusing upstream's asynchronous transport. */
    public static CompletableFuture<AiResponse> request(AiProvider provider,AiRequest request,MinecraftServer server,String character,BooleanSupplier stillAllowed){
        ExecutorService owned=io;if(owned==null)return CompletableFuture.completedFuture(AiResponse.failure("Character service unavailable"));
        int cap=Math.max(1,Math.min(2,WorldCharacters.integer(WorldCharacters.current.settings(),"max_concurrent",2)));
        var lease=requests.acquire(cap);
        if(lease==null)return CompletableFuture.completedFuture(AiResponse.failure("Character concurrency limit; scripted fallback"));
        CompletableFuture<AiResponse> result=lease.future();
        long epoch=lifecycle;
        try{owned.execute(()->{
            try{
                JsonObject settings=WorldCharacters.current.settings();
                double input=settings.has("input_usd_per_million")?settings.get("input_usd_per_million").getAsDouble():0;
                double output=settings.has("output_usd_per_million")?settings.get("output_usd_per_million").getAsDouble():0;
                double budget=settings.has("daily_budget_usd")?settings.get("daily_budget_usd").getAsDouble():0;
                if(!(input>0&&output>0&&budget>0&&Double.isFinite(input)&&Double.isFinite(output)&&Double.isFinite(budget)))throw new IllegalStateException();
                Path ledger=STATE.resolve("native-budget.json");JsonObject usage=new JsonObject();
                safePath(ledger);
                if(Files.exists(ledger)){
                    if(Files.size(ledger)>8192)throw new IllegalStateException();usage=JsonParser.parseString(Files.readString(ledger)).getAsJsonObject();
                }
                String day=java.time.LocalDate.now(java.time.ZoneOffset.UTC).toString();
                double charged=day.equals(WorldCharacters.text(usage,"day"))?usage.get("reserved_usd").getAsDouble():0;
                // Context is capped below 10k characters; charge UTF-8 bytes plus generous message overhead.
                int inputBound=PromptBuilder.buildSystemPrompt(request.context()).getBytes(StandardCharsets.UTF_8).length+request.playerMessage().getBytes(StandardCharsets.UTF_8).length+2048;
                int outputBound=tn.naizo.smartvillagers.config.SmartVillagersConfig.get().maxTokens();
                if(outputBound<1||outputBound>512)throw new IllegalStateException();
                double cost=(inputBound*input+outputBound*output)/1000000.0;
                if(!Double.isFinite(charged)||charged<0||charged+cost>budget)throw new IllegalStateException();
                JsonArray recent=new JsonArray();long now=System.currentTimeMillis(),latest=0;int individual=0;
                for(JsonElement item:WorldCharacters.array(usage,"requests")){
                    JsonObject row=item.getAsJsonObject();long at=row.get("at").getAsLong();
                    if(now-at>=3600000L)continue;if(at>now+2000L)throw new IllegalStateException();
                    recent.add(row);if(character.equals(WorldCharacters.text(row,"character"))){individual++;latest=Math.max(latest,at);}
                }
                JsonObject profile=WorldCharacters.current.profileById(character),ai=WorldCharacters.object(profile,"ai");
                if(recent.size()>=Math.max(1,Math.min(60,WorldCharacters.integer(settings,"requests_per_hour",24)))||individual>=Math.max(1,Math.min(60,WorldCharacters.integer(ai,"requests_per_hour",12)))||latest>0&&now-latest<Math.max(5,WorldCharacters.integer(ai,"cooldown_seconds",20))*1000L)throw new IllegalStateException();
                JsonObject attempt=new JsonObject();attempt.addProperty("character",character);attempt.addProperty("at",now);recent.add(attempt);
                usage.add("requests",recent);usage.addProperty("day",day);usage.addProperty("reserved_usd",charged+cost);atomic(ledger,GSON.toJson(usage));
                // Recheck loaded entities, consent and the exact configuration on the server executor
                // after disk admission, immediately before upstream's nonblocking sendAsync call.
                server.execute(()->{
                    try{
                    if(io!=owned||lifecycle!=epoch||!stillAllowed.getAsBoolean()){lease.complete(AiResponse.failure("Conversation no longer active; scripted fallback"));return;}
                    if(!lease.start()){lease.complete(AiResponse.failure("Conversation cancelled before provider dispatch"));return;}
                    var upstream=provider.complete(request);
                    // Never mutate the provider future with orTimeout: a logical deadline
                    // is not proof that its underlying HTTP exchange has terminated.
                    CompletableFuture.delayedExecutor(30,TimeUnit.SECONDS).execute(()->lease.timeout(AiResponse.failure("Provider response deadline; scripted fallback")));
                    upstream.whenComplete((answer,failure)->{
                        lease.networkFinished();
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
}
