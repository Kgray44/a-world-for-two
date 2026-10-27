package worldfortwo.qa;

import com.google.gson.*;
import net.minecraft.client.Minecraft;
import net.minecraft.client.Screenshot;
import net.minecraft.client.gui.screens.ConnectScreen;
import net.minecraft.client.gui.screens.DisconnectedScreen;
import net.minecraft.client.gui.screens.TitleScreen;
import net.minecraft.client.multiplayer.ServerData;
import net.minecraft.client.multiplayer.resolver.ServerAddress;
import net.neoforged.api.distmarker.Dist;
import net.neoforged.fml.common.Mod;
import net.neoforged.neoforge.common.NeoForge;
import net.neoforged.neoforge.client.event.RenderFrameEvent;
import java.lang.invoke.MethodHandles;
import java.lang.invoke.MethodType;
import java.nio.file.*;
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
    public SettlementCapture(){NeoForge.EVENT_BUS.addListener(this::frame);}
    private void frame(RenderFrameEvent.Post event){
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
            if(command.get("action").getAsString().equals("quit")){
                completed.add(id);write(qa.resolve(id+".json"),Map.of("at",Instant.now().toString(),"action","normal Minecraft stop"));mc.stop();return;
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
            if(mc.player==null || mc.level==null || mc.screen!=null || mc.getCurrentServer()==null)return;
            if(!mc.getCurrentServer().ip.equals(server)
                    || !mc.player.getUUID().toString().equals("32650cdf-2aaa-4f47-bb27-42ef0d1249fd"))return;
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
                if(!Double.isFinite(x+y+z+yaw+pitch) || x<800 || x>1600 || z< -1800 || z> -800 || y<48 || y>220 || Math.abs(yaw)>360 || Math.abs(pitch)>90)return;
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
            if(root.getRoot().toFile().getUsableSpace()<32_212_254_720L+128*1024*1024L)return;
            if((long)mc.getMainRenderTarget().width*mc.getMainRenderTarget().height>8_388_608L)return;
            busy=true;captures++;completed.add(id);
            Map<String,Object> receipt=new LinkedHashMap<>();
            receipt.put("at",Instant.now().toString());receipt.put("evidence","Actual native Minecraft framebuffer; extra test-only capture helper installed");
            receipt.put("position",List.of(mc.player.getX(),mc.player.getY(),mc.player.getZ()));
            receipt.put("server",server);receipt.put("yaw",mc.player.getYRot());receipt.put("pitch",mc.player.getXRot());receipt.put("dimension",mc.level.dimension().location().toString());receipt.put("fps",mc.getFps());
            Screenshot.grab(mc.gameDirectory,"awft-qa-"+id+".png",mc.getMainRenderTarget(),message->{
                try{receipt.put("native_result",message.getString());write(qa.resolve(id+".json"),receipt);}catch(Exception error){System.err.println("AWFT QA capture receipt: "+error);}finally{busy=false;}
            });
        }catch(Exception error){System.err.println("AWFT QA capture: "+error.getClass().getSimpleName()+": "+error.getMessage());}
    }
    private void write(Path path,Object value)throws Exception{
        Path temporary=path.resolveSibling(path.getFileName()+".tmp");Files.writeString(temporary,json.toJson(value));Files.move(temporary,path,StandardCopyOption.REPLACE_EXISTING,StandardCopyOption.ATOMIC_MOVE);
    }
}
