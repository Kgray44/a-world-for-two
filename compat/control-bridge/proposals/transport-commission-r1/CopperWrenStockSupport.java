package worldfortwo.bridge;

import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import com.google.gson.JsonPrimitive;
import com.google.gson.Gson;
import com.google.gson.stream.JsonReader;
import com.google.gson.stream.JsonToken;
import com.mojang.brigadier.arguments.StringArgumentType;
import net.minecraft.commands.Commands;
import net.minecraft.network.chat.Component;
import net.minecraft.server.MinecraftServer;
import net.minecraft.world.level.storage.LevelResource;
import net.neoforged.fml.ModList;
import net.neoforged.neoforge.event.RegisterCommandsEvent;
import java.io.StringReader;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.LinkOption;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.time.Instant;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.HexFormat;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;

/** Optional synchronous fixed-stock adapter. No tick listener, chunk request,
 * simulation wake, process/client control or arbitrary item/command operation.
 * External exclusive-write/creative-authoring authorization remains master-owned.
 */
public final class CopperWrenStockSupport {
    private static final String BOOT=UUID.randomUUID().toString();
    private static final String UUID_TEXT="[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}";
    private static final Map<String,Class<?>> CLASSES=Map.of(
        "adapter_class_sha256",CopperWrenStockSupport.class,"construction_class_sha256",CopperWrenConstructionStock.class,
        "schedule_item_class_sha256",CopperWrenScheduleItem.class,"station_names_class_sha256",CopperWrenStationNames.class,
        "passenger_factory_class_sha256",CopperWrenPassengerSchedule.class,"journal_class_sha256",NativeJournal.class);
    private static final Set<String> COMMON=Set.of("format","operation","created","home","world","candidate","bridge","pack_sha256",
        "bridge_jar_sha256","backup_id","backup_sha256","backup_receipt_sha256","creative_authoring",
        "adapter_class_sha256","construction_class_sha256","schedule_item_class_sha256","station_names_class_sha256",
        "passenger_factory_class_sha256","journal_class_sha256");
    private final String candidate,bridge;
    private final ArtisticEngineeringSupport.Interlock interlock;
    private ArtisticEngineeringSupport.Lease lease;
    private boolean publicationBlocked;

    public CopperWrenStockSupport(String candidate,String bridge,ArtisticEngineeringSupport.Interlock interlock) {
        if(!candidate.matches("0\\.1\\.0-candidate\\.\\d+")||!bridge.matches("0\\.6\\.\\d+")||interlock==null)
            throw new IllegalArgumentException("Exact parent candidate/bridge and real shared interlock required");
        this.candidate=candidate;this.bridge=bridge;this.interlock=interlock;
    }

    public void commands(RegisterCommandsEvent event) {
        var root=Commands.literal("awftcopperstock").requires(s->s.getEntity()==null&&s.hasPermission(4)&&s.getServer().getPort()==25575);
        for(String operation:List.of("inspect","supply"))root.then(Commands.literal(operation)
            .then(Commands.argument("bundle",StringArgumentType.word()).then(Commands.argument("sha",StringArgumentType.word())
                .executes(c->{boolean ok=run(c.getSource().getServer(),operation,StringArgumentType.getString(c,"bundle"),StringArgumentType.getString(c,"sha"));
                    if(ok)c.getSource().sendSuccess(()->Component.literal("Copper Wren stock native terminal published; operation="+operation),true);
                    else c.getSource().sendFailure(Component.literal("Copper Wren stock refused/failed; preserve actual terminal, ledger and inventory"));return ok?1:0;}))));
        event.getDispatcher().register(root);
    }

    private static void need(boolean value,String message) {if(!value)throw new IllegalStateException(message);}
    private static String sha(byte[] raw)throws Exception{return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(raw));}
    private static String text(JsonObject value,String key) {need(value.has(key)&&value.get(key).isJsonPrimitive()&&value.get(key).getAsJsonPrimitive().isString(),"Exact string field required: "+key);return value.get(key).getAsString();}
    private static boolean flag(JsonObject value,String key) {need(value.has(key)&&value.get(key).isJsonPrimitive()&&value.get(key).getAsJsonPrimitive().isBoolean(),"Exact boolean field required: "+key);return value.get(key).getAsBoolean();}
    private static byte[] read(Path home,String relative,int cap)throws Exception {
        need(!relative.contains("\\")&&!relative.contains(":")&&!Path.of(relative).isAbsolute(),"Owned forward-slash relative file required");
        Path file=home.resolve(relative).toAbsolutePath().normalize();need(file.startsWith(home)&&!relative.contains(".."),"Owned regular file only");
        for(Path p=file;!p.equals(home);p=p.getParent())need(!Files.isSymbolicLink(p)&&p.toRealPath().equals(p.toAbsolutePath().normalize()),"Redirected native custody refused");
        need(Files.isRegularFile(file,LinkOption.NOFOLLOW_LINKS)&&Files.size(file)>0&&Files.size(file)<=cap,"Closed bounded regular native file required");
        try(var in=Files.newInputStream(file)){byte[] raw=in.readNBytes(cap+1);need(raw.length<=cap,"Native file grew beyond bound");return raw;}
    }
    private static JsonObject object(byte[] raw){return JsonParser.parseString(new String(raw,StandardCharsets.UTF_8)).getAsJsonObject();}
    private static JsonObject packet(byte[] raw)throws Exception {
        JsonObject value=new JsonObject();Set<String> seen=new HashSet<>();
        try(JsonReader in=new JsonReader(new StringReader(new String(raw,StandardCharsets.UTF_8)))) {
            in.setLenient(false);in.beginObject();while(in.hasNext()) {
                String key=in.nextName();need(seen.add(key),"Duplicate typed packet field");
                if(in.peek()==JsonToken.STRING)value.add(key,new JsonPrimitive(in.nextString()));
                else if(in.peek()==JsonToken.BOOLEAN)value.add(key,new JsonPrimitive(in.nextBoolean()));
                else throw new IllegalStateException("Flat string/boolean stock packet only");
            }in.endObject();need(in.peek()==JsonToken.END_DOCUMENT,"Trailing packet data refused");
        }return value;
    }

    private static Path journal(Path home)throws Exception {
        Path directory=home.resolve("dashboard/settlement");
        for(Path p=directory;;p=p.getParent()) {
            need(Files.isDirectory(p,LinkOption.NOFOLLOW_LINKS)&&!Files.isSymbolicLink(p)
                &&p.toRealPath().equals(p.toAbsolutePath().normalize()),"Existing canonical nonredirected native journal ancestry required");
            if(p.equals(home))break;
        }
        return directory;
    }
    private static void privateSettings(Path home)throws Exception {
        JsonObject owner=object(read(home,"dashboard/artistic-owner.json",65536));
        JsonObject settings=object(read(home,"dashboard/settings.json",65536));
        need(text(owner,"format").equals("awft-artistic-stage:1")&&text(owner,"home").equals(home.toString())
            &&!flag(settings,"permanent_world")&&settings.get("port").getAsJsonPrimitive().isNumber()
            &&settings.get("port").getAsString().equals("25575"),"Actual owned private settings/port required");
    }
    private static void status(Path home,Map<String,Object> report,boolean terminalPublished)throws Exception {
        Path directory=journal(home);
        for(String name:List.of("copper-stock-status.json","copper-stock-status.json.tmp")) {
            Path file=directory.resolve(name);
            if(Files.exists(file,LinkOption.NOFOLLOW_LINKS))need(Files.isRegularFile(file,LinkOption.NOFOLLOW_LINKS)
                &&!Files.isSymbolicLink(file)&&file.toRealPath().equals(file.toAbsolutePath().normalize())&&Files.size(file)<=128*1024,
                "Existing native stock status/temporary file is redirected or unbounded");
        }
        Map<String,Object> view=new LinkedHashMap<>(report);view.put("diagnostic_only",true);view.put("terminal_published",terminalPublished);
        need(new Gson().toJson(view).getBytes(StandardCharsets.UTF_8).length<=128*1024,"Bounded native stock diagnostic required");
        NativeJournal.progress(directory,"copper-stock-status.json",view);
    }

    private Map<String,String> artifacts(Path home,JsonObject request)throws Exception {
        need(candidate.equals(text(request,"candidate"))&&bridge.equals(text(request,"bridge"))
            &&ModList.get().getModContainerById("awft_control_bridge").orElseThrow().getModInfo().getVersion().toString().equals(bridge),"Actual parent/loaded bridge identity differs");
        JsonObject active=object(read(home,"packwiz/active.json",65536)),installed=object(read(home,"server/installed.json",128*1024));
        String pack=text(request,"pack_sha256");need(pack.matches("[a-f0-9]{64}")&&candidate.equals(text(active,"version"))
            &&candidate.equals(text(installed,"pack_version"))&&pack.equals(text(active,"pack_sha256"))&&pack.equals(text(installed,"pack_sha256")),"Actual active/installed pack identity differs");
        String name="awft-control-bridge-"+bridge+".jar",jarSha=text(request,"bridge_jar_sha256");
        need(jarSha.matches("[a-f0-9]{64}")&&jarSha.equals(sha(read(home,"server/mods/"+name,2*1024*1024)))
            &&jarSha.equals(text(installed.getAsJsonObject("files"),name)),"Actual installed bridge JAR identity differs");
        Map<String,String> result=new LinkedHashMap<>();
        for(var entry:CLASSES.entrySet())try(var in=entry.getValue().getResourceAsStream(entry.getValue().getSimpleName()+".class")) {
            need(in!=null,"Actual loaded stock collaborator unavailable");byte[] code=in.readNBytes(256*1024+1);
            need(code.length>0&&code.length<=256*1024,"Bounded native stock class required");String hash=sha(code);
            need(hash.equals(text(request,entry.getKey())),"Actual loaded stock collaborator differs: "+entry.getKey());result.put(entry.getKey(),hash);
        }return result;
    }

    private void backup(Path home,JsonObject request)throws Exception {
        byte[] raw=read(home,"dashboard/settlement/backup-receipt.json",4096);JsonObject receipt=object(raw);
        need(flag(receipt,"verified")&&text(request,"backup_receipt_sha256").equals(sha(raw))
            &&text(request,"backup_id").equals(text(receipt,"id"))&&text(request,"backup_sha256").equals(text(receipt,"sha256"))
            &&text(receipt,"id").matches("\\d{8}T\\d{6}Z-[a-f0-9]{6}")&&text(receipt,"sha256").matches("[a-f0-9]{64}"),"Exact current canonical verified backup receipt required");
    }

    private List<String> inspection(Path home,Path world,JsonObject request,Map<String,String> classes)throws Exception {
        String relative=text(request,"inspection_path"),expected=text(request,"inspection_sha256");
        need(relative.matches("dashboard/settlement/copper-stock-result-"+UUID_TEXT+"\\.json")&&expected.matches("[a-f0-9]{64}"),"Canonical genuine stock inspection reference required");
        byte[] raw=read(home,relative,128*1024);need(expected.equals(sha(raw))
            &&expected.equals(new String(read(home,relative+".complete",64),StandardCharsets.US_ASCII)),"Exact native inspection and completion marker required");
        JsonObject prior=object(raw);Instant at=Instant.parse(text(prior,"at")),now=Instant.now();
        need(text(prior,"format").equals("awft-native-copper-stock:1")&&text(prior,"operation").equals("inspect")
            &&text(prior,"status").equals("inspected actual starter; no stock authored")&&!prior.has("error")
            &&flag(prior,"cleanup_passed")&&flag(prior,"lease_acquired")&&flag(prior,"lease_released")&&!flag(prior,"world_mutated")
            &&prior.getAsJsonArray("cleanup_errors").isEmpty()
            &&prior.get("temporary_tickets_remaining").getAsInt()==0&&prior.get("pending_shared_chunk_futures").getAsInt()==0,
            "Successful clean genuine native stock inspection required");
        need(!at.isAfter(now)&&!at.isBefore(now.minusSeconds(60))&&text(prior,"boot_id").equals(BOOT)
            &&prior.get("pid").getAsJsonPrimitive().isNumber()&&prior.get("pid").getAsString().equals(Long.toString(ProcessHandle.current().pid()))
            &&text(prior,"process_started").equals(ProcessHandle.current().info().startInstant().orElseThrow().toString())
            &&text(prior,"world").equals(world.toString())&&text(prior,"candidate").equals(candidate)&&text(prior,"bridge").equals(bridge)
            &&text(prior,"bridge_jar_sha256").equals(text(request,"bridge_jar_sha256"))
            &&text(prior,"pack_sha256").equals(text(request,"pack_sha256"))
            &&text(prior,"backup_receipt_sha256").equals(text(request,"backup_receipt_sha256"))
            &&prior.getAsJsonObject("artifact_class_sha256").equals(new com.google.gson.Gson().toJsonTree(classes)),
            "Fresh same-JVM/world/backup/artifact native inspection required");
        var stock=prior.getAsJsonObject("native_stock");
        need(stock.getAsJsonArray("position").equals(new com.google.gson.Gson().toJsonTree(List.of(1313,68,-994))),"Exact actual starter position required");
        var rows=stock.getAsJsonArray("all27_native_snbt");need(rows.size()==27,"Actual all27 native stock slots required");
        List<String> result=new ArrayList<>();for(var row:rows){need(row.isJsonPrimitive()&&row.getAsJsonPrimitive().isString()&&row.getAsString().length()<=2048,"Bounded native stock SNBT required");result.add(row.getAsString());}
        return result;
    }

    private boolean run(MinecraftServer server,String operation,String bundle,String expected) {
        if(lease!=null||publicationBlocked) {
            System.err.println("AWFT copper-stock adapter blocked; preserve actual lease/stock/publication state; no automatic cleanup or operation retry");
            return false;
        }
        Map<String,Object> report=new LinkedHashMap<>();Path home=null;boolean passed=false,journalAdmitted=false;
        report.put("format","awft-native-copper-stock:1");report.put("started",Instant.now().toString());report.put("operation",operation);
        report.put("request_sha256",expected);report.put("candidate",candidate);report.put("bridge",bridge);
        report.put("boot_id",BOOT);report.put("pid",ProcessHandle.current().pid());
        report.put("process_started",ProcessHandle.current().info().startInstant().orElseThrow().toString());
        report.put("world_mutated",false);report.put("world_mutation_possible",false);report.put("lease_acquired",false);
        try {
            need(server.isSameThread()&&server.getPlayerList().getPlayers().isEmpty()&&server.getPort()==25575&&lease==null&&!publicationBlocked,"Master coordinated empty-world server thread required; no blocked/ongoing stock operation");
            Path world=server.getWorldPath(LevelResource.ROOT).toRealPath(),staging=Path.of("D:/A World for Two/staging/world-tests").toRealPath();
            need(world.startsWith(staging)&&world.getNameCount()==staging.getNameCount()+3&&world.getFileName().toString().equals("RosewaterArtistic")
                &&world.getParent().getFileName().toString().equals("world"),"Exact private construction world required");
            home=world.getParent().getParent();report.put("world",world.toString());
            privateSettings(home);journal(home);journalAdmitted=true;
            need(expected.matches("[a-f0-9]{64}")&&bundle.equals("copper-stock-"+expected.substring(0,16)),"Exact immutable stock bundle/digest required");
            byte[] raw=read(home,"dashboard/settlement/"+bundle+"/request.json",65536);need(expected.equals(sha(raw)),"Exact stock request bytes required");
            JsonObject request=packet(raw);Set<String> keys=new HashSet<>(COMMON);if(operation.equals("supply")){keys.add("inspection_path");keys.add("inspection_sha256");}
            need(request.keySet().equals(keys)&&text(request,"format").equals("awft-copper-stock-request:1")&&text(request,"operation").equals(operation)
                &&text(request,"home").equals(home.toString())&&text(request,"world").equals(world.toString())
                &&flag(request,"creative_authoring")==operation.equals("supply"),"Closed fixed stock packet and explicit supply-only creative admission required");
            Instant created=Instant.parse(text(request,"created")),now=Instant.now();
            need(!created.isAfter(now)&&!created.isBefore(now.minusSeconds(120)),"Fresh120second stock packet required");
            Map<String,String> classes=artifacts(home,request);backup(home,request);report.put("artifact_class_sha256",classes);
            report.put("bridge_jar_sha256",text(request,"bridge_jar_sha256"));report.put("pack_sha256",text(request,"pack_sha256"));
            report.put("backup_id",text(request,"backup_id"));report.put("backup_sha256",text(request,"backup_sha256"));report.put("backup_receipt_sha256",text(request,"backup_receipt_sha256"));
            List<String> before=operation.equals("supply")?inspection(home,world,request,classes):null;
            lease=interlock.acquire("copper-wren-fixed-stock-"+operation,false);need(lease!=null&&lease.valid(),"Actual master shared maintenance lease required");report.put("lease_acquired",true);
            CopperWrenStationNames.gate(server.overworld(),lease);
            if(operation.equals("inspect"))report.put("native_stock",CopperWrenScheduleItem.inspectStarter(server.overworld(),lease,expected));
            else {
                report.put("inspection_sha256",text(request,"inspection_sha256"));
                report.put("native_stock",CopperWrenConstructionStock.supplyFixedHardware(server.overworld(),lease,true,before,expected,
                    ()->report.put("world_mutation_possible",true),report));report.put("world_mutated",true);
            }
            report.put("status",operation.equals("inspect")?"inspected actual starter; no stock authored":"fixed creative hardware supplied; operational acceptance pending");passed=true;
        } catch(Exception|LinkageError error){
            report.put("error",error.toString());report.put("status","stock operation refused/failed; actual stock and durable intents retained");
            if(Boolean.TRUE.equals(report.get("world_mutation_possible"))&&!Boolean.TRUE.equals(report.get("world_mutated"))) {
                report.remove("world_mutated");report.put("world_mutation_outcome","UNKNOWN: ledger/stock mutation may have started; inspect actual state");
            }
        }
        List<String> cleanup=new ArrayList<>();
        if(lease!=null) {
            try{lease.close();}catch(Exception error){cleanup.add(error.toString());}
            try{if(!lease.valid())lease=null;else cleanup.add("Actual shared lease remains valid after close");}
                catch(Exception error){cleanup.add("Actual lease state unavailable: "+error);}
        }
        boolean clean=lease==null&&cleanup.isEmpty();report.put("lease_released",lease==null);report.put("cleanup_passed",clean);
        report.put("cleanup_errors",cleanup);report.put("temporary_tickets_remaining",0);report.put("pending_shared_chunk_futures",0);
        report.put("direct_helper_tickets_added",0);report.put("simulation_wakes",0);report.put("at",Instant.now().toString());report.put("finished",report.get("at"));
        if(!clean){report.put("status","cleanup required; preserve actual shared lease and stock");passed=false;}
        boolean published=false;report.put("publication_blocked",publicationBlocked);
        if(journalAdmitted) {
            try{status(home,report,false);}catch(Exception error){report.put("status_publication_error",error.toString());}
            try {
                need(new Gson().toJson(report).getBytes(StandardCharsets.UTF_8).length<=128*1024,"Bounded native stock terminal required");
                NativeJournal.terminal(journal(home),"copper-stock",report);published=true;
            } catch(Exception error) {
                publicationBlocked=true;report.put("publication_blocked",true);report.put("terminal_publication_error",error.toString());
                System.err.println("AWFT copper-stock terminal publication failed; no retry/marker fabrication: "+error
                    +" actual owned lease released="+(lease==null)+" owned tickets=0 pending futures=0 world mutation possible="+report.get("world_mutation_possible"));passed=false;
            }
            try{status(home,report,published);}catch(Exception error){System.err.println("AWFT copper-stock diagnostic publication refused: "+error);}
        } else System.err.println("AWFT copper-stock no journal publication: private context/directory was not admitted; actual owned lease released="+(lease==null));
        return passed&&published;
    }
}
