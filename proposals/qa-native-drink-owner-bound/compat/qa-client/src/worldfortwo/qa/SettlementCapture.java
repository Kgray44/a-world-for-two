package worldfortwo.qa;

import com.google.gson.*;
import net.minecraft.client.Minecraft;
import net.minecraft.client.Screenshot;
import net.minecraft.client.gui.screens.ConnectScreen;
import net.minecraft.client.gui.screens.DisconnectedScreen;
import net.minecraft.client.gui.screens.TitleScreen;
import net.minecraft.client.multiplayer.ServerData;
import net.minecraft.client.multiplayer.resolver.ServerAddress;
import net.minecraft.core.registries.Registries;
import net.minecraft.resources.ResourceKey;
import net.minecraft.resources.ResourceLocation;
import net.neoforged.api.distmarker.Dist;
import net.neoforged.fml.common.Mod;
import net.neoforged.neoforge.common.NeoForge;
import net.neoforged.neoforge.client.event.RenderFrameEvent;
import java.lang.invoke.MethodHandles;
import java.lang.invoke.MethodType;
import java.nio.file.*;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.time.Instant;
import java.util.*;

/** Test-only native framebuffer capture. Never distributed as a gameplay mod.
 * No OS input, account access, custom renderer, camera movement or server bypass.
 */
@Mod(value="awft_settlement_qa",dist=Dist.CLIENT)
public final class SettlementCapture {
    private final Gson json=new Gson();
    private final Set<String> completed=new HashSet<>();
    private long nextCheck;
    private int captures;
    private int worldgenExports;
    private boolean busy;
    private long renderedFrames;
    private String readyCaptureKey;
    private long readyCaptureFrame;
    private NativeXaeroView mapView;
    private PendingMapCapture pendingMapCapture;
    private NpcClientSnapshot npcSnapshots;
    private static final Set<String> MAP_ACTIONS=Set.of("map-open","map-view","map-status","map-capture","map-close");
    private static final class PendingMapCapture {
        final String id;
        final MapCaptureGate gate;
        final long started=System.nanoTime();
        PendingMapCapture(String id,MapCaptureGate.Target target) { this.id=id;gate=new MapCaptureGate(target); }
    }
    private NativeDrinkCapture drinkCaptures;
    public SettlementCapture(){NeoForge.EVENT_BUS.addListener(this::frame);}
    private void frame(RenderFrameEvent.Post event){
        renderedFrames++;
        if(!busy && drinkCaptures!=null && drinkCaptures.pending()) {
            NativeDrinkCapture.Result result=drinkCaptures.frame(Minecraft.getInstance(),renderedFrames);
            if(result!=null) {
                if(result.capture())captureNativeDrink(Minecraft.getInstance(),result);
                else try { finishMap(result.qa(),result.id(),result.receipt()); }
                catch(Exception failure) { completed.add(result.id());System.err.println("AWFT QA drink terminal receipt: "+failure); }
            }
        }
        if(busy || System.nanoTime()<nextCheck)return;
        nextCheck=System.nanoTime()+1_000_000_000L;
        Minecraft mc=Minecraft.getInstance();Path root=mc.gameDirectory.toPath().toAbsolutePath().normalize();
        Path qa=root.resolve("awft-qa");
        try{
            Path owner=root.getParent().resolve("awft-owned.json"),auth=qa.resolve("authorization.json"),request=qa.resolve("request.json");
            if(!Files.isRegularFile(owner) || !Files.isRegularFile(auth) || !Files.isRegularFile(request))return;
            if(Files.isSymbolicLink(qa) || Files.isSymbolicLink(auth) || Files.isSymbolicLink(request) || Files.size(auth)>4096 || Files.size(request)>4096)return;
            JsonObject ownership=JsonParser.parseString(Files.readString(owner)).getAsJsonObject();
            if(!ownership.get("format").getAsString().equals("awft-owned-client:1"))return;
            JsonObject authorization=JsonParser.parseString(Files.readString(auth)).getAsJsonObject();
            Instant expires=Instant.parse(authorization.get("expires").getAsString());
            if(expires.isBefore(Instant.now()) || expires.isAfter(Instant.now().plusSeconds(8*3600)))return;
            JsonObject command=JsonParser.parseString(Files.readString(request)).getAsJsonObject();
            if(!command.get("nonce").getAsString().equals(authorization.get("nonce").getAsString()))return;
            String id=command.get("id").getAsString();
            if(!id.matches("[a-z0-9][a-z0-9-]{0,63}") || completed.contains(id))return;
            String server=authorization.has("server")?authorization.get("server").getAsString():"127.0.0.1:25565";
            if(!Set.of("127.0.0.1:25565","127.0.0.1:25575").contains(server)
                    || !mc.getUser().getProfileId().toString().equals("32650cdf-2aaa-4f47-bb27-42ef0d1249fd"))return;
            String action=command.get("action").getAsString();
            if(npcSnapshots!=null && !action.equals("npc-client-snapshot"))npcSnapshots.cancel();
            if(pendingMapCapture!=null && pendingMapCapture.id.equals(id) && !action.equals("map-capture")) {
                failMap(qa,id,action,new IllegalArgumentException("A pending capture ID cannot be reused for another action"));return;
            }
            if(pendingMapCapture!=null && !pendingMapCapture.id.equals(id))
                cancelPendingMap(qa,"An explicitly authorized different request superseded the pending map capture");
            if(command.get("action").getAsString().equals("quit")){
                completed.add(id);write(qa.resolve(id+".json"),Map.of("at",Instant.now().toString(),"action","normal Minecraft stop",
                    "map_view_restoration",restoreMapForExit(mc)));mc.stop();return;
            }
            // Private staging only: ordinary game connection/disconnection APIs.
            // No credentials, input injection, public endpoint or server bypass.
            if(command.get("action").getAsString().equals("connect") && server.equals("127.0.0.1:25575")){
                // A title screen can already exist behind the startup overlay.
                // Leave the request pending until native loading has finished
                // and an actual disconnected menu is ready; no elapsed-time guess.
                if(!mc.isGameLoadFinished() || mc.getOverlay()!=null
                        || !(mc.screen instanceof TitleScreen || mc.screen instanceof DisconnectedScreen)
                        || mc.level!=null || mc.player!=null || mc.getConnection()!=null)return;
                completed.add(id);
                write(qa.resolve(id+".json"),Map.of("at",Instant.now().toString(),"action","normal authenticated staging connection requested; server login is separate evidence",
                        "native_game_load_finished",true,"startup_overlay_absent",true,"ready_menu",mc.screen.getClass().getName()));
                ConnectScreen.startConnecting(mc.screen,mc,ServerAddress.parseString(server),new ServerData("Owned artistic staging",server,ServerData.Type.OTHER),false,null);return;
            }
            if(mc.player==null || mc.level==null || mc.getCurrentServer()==null)return;
            if(!mc.getCurrentServer().ip.equals(server)
                    || !mc.player.getUUID().toString().equals("32650cdf-2aaa-4f47-bb27-42ef0d1249fd"))return;
            // Map actions require the same authenticated owner/nonce above and
            // the exact helper-owned native GuiMap. No ordinary screen guard is
            // relaxed: the existing actions still reject every open screen.
            if(MAP_ACTIONS.contains(action)) { mapAction(mc,root,qa,id,server,action,command);return; }
            if(action.equals("disconnect") && server.equals("127.0.0.1:25575") && mapView!=null && mapView.owns(mc)) {
                completed.add(id);write(qa.resolve(id+".json"),Map.of("at",Instant.now().toString(),"action","normal staging disconnect",
                    "map_view_restoration",restoreMapForExit(mc)));mc.disconnect(new TitleScreen());return;
            }
            if(mc.screen!=null)return;
            if(action.equals("capture-on-native-drink")) {
                if(!server.equals("127.0.0.1:25575") || !mc.isGameLoadFinished() || mc.getOverlay()!=null)return;
                if(Files.exists(qa.resolve(id+".json"),LinkOption.NOFOLLOW_LINKS)
                        || Files.exists(qa.resolve(id+".complete"),LinkOption.NOFOLLOW_LINKS)) { completed.add(id);return; }
                try {
                    if(captures>=96)throw new IllegalStateException("Shared96-frame capture limit exhausted");
                    if(drinkCaptures==null)drinkCaptures=new NativeDrinkCapture(()->renderedFrames+1);
                    drinkCaptures.arm(mc,root,qa,id,command,expires);
                } catch(Exception failure) { failMap(qa,id,action,failure); }
                return;
            }
            if(action.equals("npc-client-snapshot")) {
                if(!server.equals("127.0.0.1:25575") || !mc.isGameLoadFinished() || mc.getOverlay()!=null)return;
                if(Files.exists(qa.resolve(id+".json"),LinkOption.NOFOLLOW_LINKS)
                        || Files.exists(qa.resolve(id+".complete"),LinkOption.NOFOLLOW_LINKS)) { completed.add(id);return; }
                try {
                    if(npcSnapshots==null)npcSnapshots=new NpcClientSnapshot();
                    Map<String,Object> result=npcSnapshots.poll(mc,id,command.getAsJsonArray("uuids"),expires,server,renderedFrames);
                    if(result!=null)finishMap(qa,id,result);
                } catch(Exception failure) { if(npcSnapshots!=null)npcSnapshots.cancel();failMap(qa,id,action,failure); }
                return;
            }
            if(command.get("action").getAsString().equals("worldgen-export") && server.equals("127.0.0.1:25575")){
                if(!mc.isGameLoadFinished() || mc.getOverlay()!=null)return;
                completed.add(id);
                if(worldgenExports>=1){write(qa.resolve(id+".json"),Map.of("at",Instant.now().toString(),"action","worldgen export refused","error","One bounded worldgen export is permitted per QA launch"));return;}
                worldgenExports++;
                boolean full=command.has("full_encodings") && command.get("full_encodings").getAsBoolean();
                try {
                    Path directory=qa.resolve("worldgen-inputs");
                    if(!Files.exists(directory,LinkOption.NOFOLLOW_LINKS))Files.createDirectory(directory);
                    Class<?> diagnostics=Class.forName("worldfortwo.bridge.WorldgenFingerprintDiagnostics",false,SettlementCapture.class.getClassLoader());
                    var export=MethodHandles.publicLookup().findStatic(diagnostics,"writeLoadedClient",
                        MethodType.methodType(Path.class,Path.class,String.class,boolean.class));
                    Path receipt=(Path)export.invokeExact(directory,id,full);
                    write(qa.resolve(id+".json"),Map.of("at",Instant.now().toString(),"action","read-only cached client worldgen input export",
                        "status_receipt",receipt.getFileName().toString(),"full_encodings",full,"note","Inspect the immutable diagnostic status; export is not fingerprint acceptance"));
                } catch(Throwable failure) {
                    if(failure instanceof VirtualMachineError || failure instanceof ThreadDeath)throw (Error)failure;
                    String message=String.valueOf(failure.getMessage());
                    if(message.length()>1024)message=message.substring(0,1024)+" [truncated]";
                    write(qa.resolve(id+".json"),Map.of("at",Instant.now().toString(),"action","worldgen export failed",
                        "error_type",failure.getClass().getName(),"error",message,"note","Failed outputs remain private; no automatic retry or worldgen load was requested"));
                }
                return;
            }
            if(command.get("action").getAsString().equals("disconnect") && server.equals("127.0.0.1:25575")){
                completed.add(id);write(qa.resolve(id+".json"),Map.of("at",Instant.now().toString(),"action","normal staging disconnect"));mc.disconnect(new TitleScreen());return;
            }
            if(command.get("action").getAsString().equals("lighting") && server.equals("127.0.0.1:25575")){
                int daytime=command.get("daytime").getAsInt();if(daytime<0 || daytime>=24000)return;
                completed.add(id);mc.player.connection.sendCommand("time set "+daytime);
                mc.player.connection.sendCommand("weather clear");mc.player.connection.sendCommand("gamerule doDaylightCycle false");mc.player.connection.sendCommand("gamerule doWeatherCycle false");
                write(qa.resolve(id+".json"),Map.of("at",Instant.now().toString(),"action","normal operator lighting commands sent","daytime",daytime));return;
            }
            if(command.get("action").getAsString().equals("pose")){
                // Normal authenticated commands. Server OP permission is still
                // enforced; only this player and the surveyed area are allowed.
                JsonArray pose=command.getAsJsonArray("position");
                double x=pose.get(0).getAsDouble(),y=pose.get(1).getAsDouble(),z=pose.get(2).getAsDouble();
                float yaw=command.get("yaw").getAsFloat(),pitch=command.get("pitch").getAsFloat();
                // The authorized south-shore forest extends to the cliff foot
                // near z=-616; the zipline starts at z=-760. Keep the surveyed
                // private area finite while allowing native review of both.
                if(!Double.isFinite(x+y+z+yaw+pitch) || x<800 || x>1600 || z< -1800 || z> -560 || y<48 || y>220 || Math.abs(yaw)>360 || Math.abs(pitch)>90)return;
                String mode=command.get("gamemode").getAsString();if(!mode.equals("spectator") && !mode.equals("survival"))return;
                completed.add(id);mc.options.hideGui=mode.equals("spectator");mc.options.pauseOnLostFocus=false;
                mc.player.connection.sendCommand("gamemode "+mode);
                mc.player.connection.sendCommand("tp @s "+x+" "+y+" "+z+" "+yaw+" "+pitch);
                write(qa.resolve(id+".json"),Map.of("at",Instant.now().toString(),"action","normal authenticated native commands sent; position must be verified before capture"));return;
            }
            if(!command.get("action").getAsString().equals("capture") || captures>=96)return;
            if(command.has("not_before") && Instant.now().isBefore(Instant.parse(command.get("not_before").getAsString())))return;
            JsonArray position=command.getAsJsonArray("expected_position");
            double dx=mc.player.getX()-position.get(0).getAsDouble(),dy=mc.player.getY()-position.get(1).getAsDouble(),dz=mc.player.getZ()-position.get(2).getAsDouble();
            if(dx*dx+dy*dy+dz*dz>9)return;
            // A teleport receipt proves the actor moved, not that the client
            // received its native chunks. DH terrain alone cannot qualify a
            // building screenshot. These are read-only client cache checks;
            // no chunk request, world generation or fallback renderer is used.
            JsonArray look=command.has("expected_look_at")?command.getAsJsonArray("expected_look_at"):position;
            if(!nativeViewChunksPresent(mc,position) || !nativeViewChunksPresent(mc,look)) {
                readyCaptureKey=null;return;
            }
            String readyKey=id+position+look;
            if(!readyKey.equals(readyCaptureKey)) { readyCaptureKey=readyKey;readyCaptureFrame=renderedFrames;return; }
            if(renderedFrames-readyCaptureFrame<30)return;
            if(root.getRoot().toFile().getUsableSpace()<32_212_254_720L+128*1024*1024L)return;
            if((long)mc.getMainRenderTarget().width*mc.getMainRenderTarget().height>8_388_608L)return;
            busy=true;captures++;completed.add(id);
            Map<String,Object> receipt=new LinkedHashMap<>();
            receipt.put("at",Instant.now().toString());receipt.put("evidence","Actual native Minecraft framebuffer; extra test-only capture helper installed");
            receipt.put("position",List.of(mc.player.getX(),mc.player.getY(),mc.player.getZ()));
            receipt.put("native_camera_and_target_chunk_neighborhoods_present",true);
            receipt.put("rendered_frames_after_native_chunk_readiness",renderedFrames-readyCaptureFrame);
            receipt.put("server",server);receipt.put("yaw",mc.player.getYRot());receipt.put("pitch",mc.player.getXRot());receipt.put("dimension",mc.level.dimension().location().toString());receipt.put("fps",mc.getFps());
            Screenshot.grab(mc.gameDirectory,"awft-qa-"+id+".png",mc.getMainRenderTarget(),message->{
                try{receipt.put("native_result",message.getString());write(qa.resolve(id+".json"),receipt);}catch(Exception error){System.err.println("AWFT QA capture receipt: "+error);}finally{busy=false;}
            });
        }catch(Exception error){System.err.println("AWFT QA capture: "+error.getClass().getSimpleName()+": "+error.getMessage());}
    }

    private void captureNativeDrink(Minecraft mc,NativeDrinkCapture.Result result) {
        String id=result.id();Path root=mc.gameDirectory.toPath().toAbsolutePath().normalize();
        String filename="awft-qa-"+id+".png";Path png=root.resolve("screenshots").resolve(filename);
        try {
            if(captures>=96 || (long)mc.getMainRenderTarget().width*mc.getMainRenderTarget().height>8_388_608L)
                throw new IllegalStateException("Existing framebuffer limits exhausted");
            if(root.getRoot().toFile().getUsableSpace()<32_212_254_720L+128*1024*1024L
                    || Path.of("C:\\").toFile().getUsableSpace()<32_212_254_720L)
                throw new IllegalStateException("Existing host storage reserve prevents a framebuffer");
            if(Files.exists(png,LinkOption.NOFOLLOW_LINKS))throw new FileAlreadyExistsException(filename);
            busy=true;captures++;completed.add(id);
            Map<String,Object> receipt=new LinkedHashMap<>(result.receipt());
            Screenshot.grab(mc.gameDirectory,filename,mc.getMainRenderTarget(),message->{
                try {
                    receipt.put("native_result",message.getString());
                    if(!Files.isRegularFile(png,LinkOption.NOFOLLOW_LINKS)||Files.isSymbolicLink(png)||Files.size(png)<8||Files.size(png)>64*1024*1024L)
                        throw new IllegalStateException("Native screenshot was not saved within its finite bound");
                    byte[] signature=new byte[]{(byte)137,80,78,71,13,10,26,10};
                    MessageDigest hash=MessageDigest.getInstance("SHA-256");long bytes=0;
                    try(var in=Files.newInputStream(png)) {
                        byte[] first=in.readNBytes(8);if(!Arrays.equals(first,signature))throw new IllegalStateException("Native result is not a PNG");hash.update(first);bytes=first.length;
                        byte[] block=new byte[65536];int count;while((count=in.read(block))!=-1){bytes+=count;if(bytes>64*1024*1024L)throw new IllegalStateException("PNG grew beyond bound");hash.update(block,0,count);}
                    }
                    receipt.put("status","native drink frame saved; visual acceptance pending");receipt.put("png","screenshots/"+filename);
                    receipt.put("png_bytes",bytes);receipt.put("png_sha256",HexFormat.of().formatHex(hash.digest()));
                    mc.execute(()->{
                        try {writeNew(result.qa().resolve(id+".json"),receipt);}
                        catch(Exception failure){failMap(result.qa(),id,"capture-on-native-drink",failure);}
                        finally{busy=false;}
                    });
                } catch(Exception failure) {mc.execute(()->{busy=false;failMap(result.qa(),id,"capture-on-native-drink",failure);});}
            });
        } catch(Exception failure) {busy=false;failMap(result.qa(),id,"capture-on-native-drink",failure);}
    }

    private static boolean nativeViewChunksPresent(Minecraft mc,JsonArray point) {
        if(point.size()!=3)return false;
        double x=point.get(0).getAsDouble(),y=point.get(1).getAsDouble(),z=point.get(2).getAsDouble();
        if(!Double.isFinite(x+y+z) || x<800 || x>1600 || z< -1800 || z> -560 || y<48 || y>320)return false;
        int cx=Math.floorDiv((int)Math.floor(x),16),cz=Math.floorDiv((int)Math.floor(z),16);
        for(int ox=-1;ox<=1;ox++)for(int oz=-1;oz<=1;oz++)
            if(!mc.level.getChunkSource().hasChunk(cx+ox,cz+oz))return false;
        return true;
    }

    private void mapAction(Minecraft mc,Path root,Path qa,String id,String server,String action,JsonObject command) {
        try {
            // Preserve immutable receipts across launches as well as this
            // launch's completed set. Never reuse a screenshot's name.
            if(Files.exists(qa.resolve(id+".json"),LinkOption.NOFOLLOW_LINKS)
                    || Files.exists(qa.resolve(id+".complete"),LinkOption.NOFOLLOW_LINKS)) { completed.add(id);return; }
            if(!server.equals("127.0.0.1:25575"))throw new IllegalStateException("Native map QA is staging-loopback only");
            if(pendingMapCapture!=null && pendingMapCapture.id.equals(id) && !action.equals("map-capture"))
                throw new IllegalArgumentException("A pending map capture ID cannot be reused for another action");
            Map<String,Object> result;
            switch(action) {
                case "map-open" -> {
                    if(mapView==null)mapView=new NativeXaeroView(mc.getUser().getProfileId());
                    var dim=ResourceKey.create(Registries.DIMENSION,ResourceLocation.parse(command.get("dimension").getAsString()));
                    result=mapView.open(mc,dim);
                }
                case "map-view" -> {
                    if(mapView==null)throw new IllegalStateException("An explicitly opened native map is required");
                    JsonArray center=command.getAsJsonArray("center");
                    if(center.size()!=2)throw new IllegalArgumentException("Map center requires X and Z");
                    result=mapView.setView(mc,center.get(0).getAsDouble(),center.get(1).getAsDouble(),command.get("zoom").getAsDouble());
                }
                case "map-status" -> {
                    if(mapView==null)throw new IllegalStateException("An explicitly opened native map is required");
                    result=mapView.snapshot(mc);
                }
                case "map-close" -> {
                    if(mapView==null)throw new IllegalStateException("An explicitly opened native map is required");
                    result=mapView.close(mc);
                }
                case "map-capture" -> {
                    mapCapture(mc,root,qa,id,command);return;
                }
                default -> throw new IllegalArgumentException("Unsupported explicit map action");
            }
            finishMap(qa,id,Map.of("at",Instant.now().toString(),"action",action,"native_result",result,
                "note","Native UI state only; actual painting, coarse-source provenance, permissions and performance require separate evidence"));
        } catch(Throwable failure) {
            if(failure instanceof VirtualMachineError || failure instanceof ThreadDeath)throw (Error)failure;
            failMap(qa,id,action,failure);
        }
    }

    private void mapCapture(Minecraft mc,Path root,Path qa,String id,JsonObject command) throws Exception {
        if(mapView==null)throw new IllegalStateException("An explicitly opened native map is required");
        if(captures>=96)throw new IllegalStateException("The shared 96-framebuffer capture limit is exhausted");
        if(command.has("not_before") && Instant.now().isBefore(Instant.parse(command.get("not_before").getAsString())))return;
        JsonArray center=command.getAsJsonArray("expected_center");
        if(center.size()!=2)throw new IllegalArgumentException("Expected map center requires X and Z");
        var target=new MapCaptureGate.Target(command.get("expected_dimension").getAsString(),center.get(0).getAsDouble(),
            center.get(1).getAsDouble(),command.get("expected_zoom").getAsDouble());
        if(pendingMapCapture==null)pendingMapCapture=new PendingMapCapture(id,target);
        if(!pendingMapCapture.id.equals(id) || !pendingMapCapture.gate.target().equals(target))
            throw new IllegalArgumentException("A pending capture ID cannot change its expected view");
        if(System.nanoTime()-pendingMapCapture.started>=60_000_000_000L)
            throw new IllegalStateException("Bounded map capture readiness expired: "+pendingMapCapture.gate.lastReason());
        if(root.getRoot().toFile().getUsableSpace()<32_212_254_720L+128*1024*1024L
                || Path.of("C:\\").toFile().getUsableSpace()<32_212_254_720L)
            throw new IllegalStateException("The host storage reserve does not permit another framebuffer capture");
        if((long)mc.getMainRenderTarget().width*mc.getMainRenderTarget().height>8_388_608L)
            throw new IllegalStateException("The native framebuffer exceeds 8 megapixels");
        Map<String,Object> actual=mapView.snapshot(mc);
        var observation=new MapCaptureGate.Observation(renderedFrames,(String)actual.get("actual_view_dimension"),
            Boolean.TRUE.equals(actual.get("dimension_ready")),(double)actual.get("camera_x"),(double)actual.get("camera_z"),
            (double)actual.get("user_scale"),(double)actual.get("target_scale"));
        MapCaptureGate.Evidence proof=pendingMapCapture.gate.consider(observation);
        if(proof==null)return;
        String filename="awft-qa-"+id+".png";
        if(Files.exists(root.resolve("screenshots").resolve(filename),LinkOption.NOFOLLOW_LINKS))
            throw new FileAlreadyExistsException("The requested screenshot name already exists");
        Map<String,Object> receipt=new LinkedHashMap<>();
        receipt.put("at",Instant.now().toString());receipt.put("action","map-capture");receipt.put("server","127.0.0.1:25575");
        receipt.put("evidence","Actual native Minecraft framebuffer request with the exact owned Xaero screen; inspect native_result and the resulting PNG");
        receipt.put("native_map_view",actual);receipt.put("expected_map_view",target);receipt.put("rendered_readiness",proof);
        receipt.put("fps",mc.getFps());receipt.put("note","View readiness is not terrain painting, coarse-only source, exploration, SeedGen parity or performance acceptance");
        busy=true;captures++;completed.add(id);pendingMapCapture=null;
        try {
            Screenshot.grab(mc.gameDirectory,filename,mc.getMainRenderTarget(),message->{
                try { receipt.put("native_result",message.getString());writeNew(qa.resolve(id+".json"),receipt); }
                catch(Exception failure) { System.err.println("AWFT QA immutable map receipt: "+failure); }
                finally { busy=false; }
            });
        } catch(RuntimeException | Error failure) { busy=false;throw failure; }
    }

    private void finishMap(Path qa,String id,Object value) throws Exception {
        completed.add(id);
        if(pendingMapCapture!=null && pendingMapCapture.id.equals(id))pendingMapCapture=null;
        writeNew(qa.resolve(id+".json"),value);
    }
    private void failMap(Path qa,String id,String action,Throwable failure) {
        completed.add(id);
        if(pendingMapCapture!=null && pendingMapCapture.id.equals(id))pendingMapCapture=null;
        String message=String.valueOf(failure.getMessage());if(message.length()>1024)message=message.substring(0,1024)+" [truncated]";
        try { writeNew(qa.resolve(id+".json"),Map.of("at",Instant.now().toString(),"action",action,"status","failed",
            "error_type",failure.getClass().getName(),"error",message,"note","This unique request is complete; no automatic retry")); }
        catch(Exception receiptError) { System.err.println("AWFT QA terminal map failure receipt: "+receiptError); }
    }
    private void cancelPendingMap(Path qa,String reason) {
        PendingMapCapture previous=pendingMapCapture;pendingMapCapture=null;
        if(previous!=null)failMap(qa,previous.id,"map-capture",new IllegalStateException(reason));
    }
    private Map<String,Object> restoreMapForExit(Minecraft mc) {
        if(mapView==null || !mapView.owns(mc))return Map.of("status","no exact safe owned map to restore");
        try { return mapView.close(mc); }
        catch(Throwable failure) {
            if(failure instanceof VirtualMachineError || failure instanceof ThreadDeath)throw (Error)failure;
            return Map.of("status","restoration failed; normal disconnect/shutdown still requested","error_type",failure.getClass().getName());
        }
    }
    private void writeNew(Path path,Object value) throws Exception {
        byte[] raw=json.toJson(value).getBytes(StandardCharsets.UTF_8);
        if(raw.length>65536)throw new IllegalStateException("Map QA receipt exceeds its bounded size");
        if(path.getRoot().toFile().getUsableSpace()<32_212_254_720L+1024*1024L
                || Path.of("C:\\").toFile().getUsableSpace()<32_212_254_720L)
            throw new IllegalStateException("Storage reserve prevents writing a private failure receipt");
        Path seal=path.resolveSibling(path.getFileName().toString().replaceFirst("\\.json$","")+".complete");
        if(Files.exists(path,LinkOption.NOFOLLOW_LINKS) || Files.exists(seal,LinkOption.NOFOLLOW_LINKS))throw new FileAlreadyExistsException(path.toString());
        Files.write(path,raw,StandardOpenOption.CREATE_NEW,StandardOpenOption.WRITE);
        Files.writeString(seal,HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(raw))+"\n",StandardOpenOption.CREATE_NEW,StandardOpenOption.WRITE);
    }
    private void write(Path path,Object value)throws Exception{
        Path temporary=path.resolveSibling(path.getFileName()+".tmp");Files.writeString(temporary,json.toJson(value));Files.move(temporary,path,StandardCopyOption.REPLACE_EXISTING,StandardCopyOption.ATOMIC_MOVE);
    }
}
