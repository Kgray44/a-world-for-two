package worldfortwo.qa;

import com.google.gson.*;
import de.markusbordihn.easynpc.entity.easynpc.EasyNPC;
import net.minecraft.client.Minecraft;
import net.minecraft.client.model.HumanoidModel;
import net.minecraft.client.model.geom.ModelPart;
import net.minecraft.client.multiplayer.ClientLevel;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.item.UseAnim;
import net.neoforged.neoforge.client.event.RenderLivingEvent;
import net.neoforged.neoforge.common.NeoForge;
import java.nio.file.*;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.*;
import java.util.function.LongSupplier;

/** One finite observer of an already-rendered native DRINK; never changes an entity. */
public final class NativeDrinkCapture {
    private static final UUID OWNER=UUID.fromString("32650cdf-2aaa-4f47-bb27-42ef0d1249fd");
    private static final String ACTION="capture-on-native-drink",SERVER="127.0.0.1:25575";
    private final LongSupplier currentFrame;
    private Pending pending;
    private int requests;
    public record Result(String id,Path qa,boolean capture,Map<String,Object> receipt) {}
    private static final class Pending {
        final String id,nonce,requestBytes;
        final UUID target;
        final Instant expires;
        final ClientLevel level;
        final Path root,qa;
        final double[] position,look;
        final long deadline,started=System.nanoTime();
        final int seconds;
        long readySince=-1,armedFrame=-1,observedFrame=-1,nextSearch;
        boolean armed;
        Mob targetMob;
        Map<String,Object> observed;
        Pending(Minecraft mc,Path root,Path qa,String id,String nonce,String bytes,UUID target,
                Instant expires,double[] position,double[] look,int seconds) {
            this.id=id;this.nonce=nonce;requestBytes=bytes;this.target=target;this.expires=expires;
            level=mc.level;this.root=root;this.qa=qa;this.position=position;this.look=look;
            this.seconds=seconds;deadline=started+seconds*1_000_000_000L;
        }
    }
    public NativeDrinkCapture(LongSupplier frame){currentFrame=frame;NeoForge.EVENT_BUS.addListener(this::rendered);}
    public boolean pending(){return pending!=null;}

    public void arm(Minecraft mc,Path root,Path qa,String id,JsonObject command,Instant expires) throws Exception {
        if(pending!=null){if(!pending.id.equals(id))throw new IllegalStateException("Another drink observation is pending");return;}
        if(requests>=2)throw new IllegalStateException("Two native drink observations per launch exhausted");
        if(!command.keySet().equals(Set.of("id","nonce","action","uuid","expected_position","expected_look_at","timeout_seconds")))
            throw new IllegalArgumentException("Exactly one UUID, existing view guards and a finite timeout are required");
        int seconds=command.get("timeout_seconds").getAsBigDecimal().intValueExact();
        if(seconds<1||seconds>60)throw new IllegalArgumentException("Native drink observation must be1..60 seconds");
        UUID target=UUID.fromString(command.get("uuid").getAsString());
        double[] position=point(command.getAsJsonArray("expected_position")),look=point(command.getAsJsonArray("expected_look_at"));
        String bytes=read(qa.resolve("request.json"));
        if(!JsonParser.parseString(bytes).getAsJsonObject().equals(command))throw new IllegalStateException("Request changed before arming");
        Pending p=new Pending(mc,root,qa,id,command.get("nonce").getAsString(),bytes,target,expires,position,look,seconds);
        authority(mc,p);requests++;pending=p;
    }

    /** Called on EVERY RenderFrameEvent.Post, before the old one-second request poll. */
    public Result frame(Minecraft mc,long frame) {
        Pending p=pending;if(p==null)return null;
        try {
            authority(mc,p);
            if(System.nanoTime()>=p.deadline)throw new IllegalStateException("Finite native DRINK observation expired; no frame captured");
            if(!viewReady(mc,p)) {p.armed=false;p.readySince=-1;p.armedFrame=-1;p.observed=null;return null;}
            if(p.readySince<0)p.readySince=frame;
            if(frame-p.readySince<30)return null;
            if(!p.armed)p.armedFrame=frame;
            p.armed=true;
            // The rendered observer ran during THIS native frame. No30-frame delay follows DRINK.
            if(p.observed==null||p.observedFrame!=frame)return null;
            Mob mob=p.targetMob;
            if(mob==null||!mob.isUsingItem()||mob.getUseItem().isEmpty()||mob.getUseItem().getUseAnimation()!=UseAnim.DRINK
                    ||mob.getTicksUsingItem()<8||mob.getUseItemRemainingTicks()<=0)return null;
            Map<String,Object> receipt=new LinkedHashMap<>();
            receipt.put("at",Instant.now().toString());receipt.put("action",ACTION);receipt.put("server",SERVER);
            receipt.put("target_uuid",p.target.toString());receipt.put("dimension",mc.level.dimension().location().toString());
            receipt.put("position",List.of(mc.player.getX(),mc.player.getY(),mc.player.getZ()));
            var camera=mc.gameRenderer.getMainCamera().getPosition();receipt.put("camera_position",List.of(camera.x,camera.y,camera.z));
            receipt.put("yaw",mc.player.getYRot());receipt.put("pitch",mc.player.getXRot());receipt.put("fps",mc.getFps());
            receipt.put("frame",frame);receipt.put("native_drink_render_frame",p.observedFrame);
            receipt.put("ready_frames_before_arming",p.armedFrame-p.readySince);receipt.put("required_prearm_frames",30);
            receipt.put("ready_frames_at_capture",frame-p.readySince);receipt.put("frames_since_arming",frame-p.armedFrame);
            receipt.put("trigger_predicate","actual native DRINK; elapsed ticks>=8; remaining ticks>0; observed and captured in the same native frame");
            receipt.put("timeout_seconds",p.seconds);receipt.put("elapsed_ms",(System.nanoTime()-p.started)/1_000_000.0);
            receipt.put("native_camera_and_target_chunk_neighborhoods_present",true);receipt.put("native_drink_observation",p.observed);
            receipt.put("evidence","Actual named native DRINK observed in RenderLivingEvent.Post; framebuffer requested in the same RenderFrameEvent.Post");
            receipt.put("evidence_limit","The saved PNG requires real visual review. Post-event model fields can already be restored; no mouth alignment, heard audio, schedule or multiplayer acceptance is inferred.");
            pending=null;return new Result(p.id,p.qa,true,receipt);
        } catch(Exception failure) {
            pending=null;return new Result(p.id,p.qa,false,Map.of("at",Instant.now().toString(),"action",ACTION,"status","failed","error_type",failure.getClass().getName(),"error",safe(failure),"note","Unique observation complete; no screenshot and no automatic retry"));
        }
    }

    private void rendered(RenderLivingEvent.Post<?,?> event) {
        Pending p=pending;if(p==null||!p.armed||System.nanoTime()>=p.deadline||Instant.now().isAfter(p.expires))return;
        Minecraft mc=Minecraft.getInstance();Entity e=event.getEntity();
        if(mc.level!=p.level||mc.screen!=null||!e.getUUID().equals(p.target)||!(e instanceof EasyNPC<?> npc))return;
        Mob m=npc.getMob();
        if(m!=e||!m.isAlive()||!m.isUsingItem()||m.getUseItem().isEmpty()||m.getUseItem().getUseAnimation()!=UseAnim.DRINK
                ||m.getTicksUsingItem()<8||m.getUseItemRemainingTicks()<=0)return;
        p.targetMob=m;Map<String,Object> r=new LinkedHashMap<>();
        r.put("at",Instant.now().toString());r.put("uuid",e.getUUID().toString());r.put("entity_id",e.getId());
        r.put("entity_type",BuiltInRegistries.ENTITY_TYPE.getKey(e.getType()).toString());r.put("entity_class",e.getClass().getName());
        r.put("position",List.of(e.getX(),e.getY(),e.getZ()));r.put("pose",e.getPose().name());r.put("is_passenger",e.isPassenger());
        r.put("is_using_item",true);r.put("used_hand",m.getUsedItemHand().name());r.put("main_arm",m.getMainArm().name());
        r.put("active_use_item",BuiltInRegistries.ITEM.getKey(m.getUseItem().getItem()).toString());
        r.put("active_use_item_class",m.getUseItem().getItem().getClass().getName());r.put("use_animation","DRINK");
        r.put("ticks_using_item",m.getTicksUsingItem());r.put("use_remaining_ticks",m.getUseItemRemainingTicks());r.put("native_use_duration",m.getUseItem().getUseDuration(m));
        r.put("renderer_class",event.getRenderer().getClass().getName());Object model=event.getRenderer().getModel();r.put("model_class",model.getClass().getName());
        var md=npc.getEasyNPCModelData();r.put("easy_npc_pose",String.valueOf(md.getModelPose()));r.put("easy_npc_pose_name",String.valueOf(md.getModelPoseName()));
        if(model instanceof HumanoidModel<?> h){r.put("model_riding",h.riding);r.put("left_arm_pose",h.leftArmPose.name());r.put("right_arm_pose",h.rightArmPose.name());r.put("parts",Map.of("head",part(h.head),"body",part(h.body),"left_arm",part(h.leftArm),"right_arm",part(h.rightArm)));}
        p.observed=r;p.observedFrame=currentFrame.getAsLong();
    }

    private static Map<String,Object> part(ModelPart p){return Map.of("x",finite(p.x),"y",finite(p.y),"z",finite(p.z),"xRot",finite(p.xRot),"yRot",finite(p.yRot),"zRot",finite(p.zRot));}
    private static Object finite(float value){return Float.isFinite(value)?value:"non-finite";}
    private static String safe(Exception failure){String s=String.valueOf(failure.getMessage());return s.length()>512?s.substring(0,512):s;}
    private static String read(Path path) throws Exception {
        if(!Files.isRegularFile(path,LinkOption.NOFOLLOW_LINKS)||Files.isSymbolicLink(path)||Files.size(path)>4096)throw new IllegalStateException("Regular bounded private authorization/request required");
        String value=Files.readString(path,StandardCharsets.UTF_8);
        if(value.getBytes(StandardCharsets.UTF_8).length>4096)throw new IllegalStateException("Authorization/request changed beyond bound");return value;
    }
    private static double[] point(JsonArray a){
        if(a==null||a.size()!=3)throw new IllegalArgumentException("Three expected view coordinates required");
        double[] p={a.get(0).getAsDouble(),a.get(1).getAsDouble(),a.get(2).getAsDouble()};
        if(!Double.isFinite(p[0]+p[1]+p[2])||p[0]<800||p[0]>1600||p[2]<-1800||p[2]>-560||p[1]<48||p[1]>320)throw new IllegalArgumentException("Expected view outside the existing surveyed QA area");return p;
    }
    private static void authority(Minecraft mc,Pending p) throws Exception {
        if(!Instant.now().isBefore(p.expires)||mc.level!=p.level||mc.player==null||!OWNER.equals(mc.player.getUUID())||!OWNER.equals(mc.getUser().getProfileId())||mc.getCurrentServer()==null||!SERVER.equals(mc.getCurrentServer().ip))throw new IllegalStateException("Existing authenticated staging session changed or expired");
        if(Files.isSymbolicLink(p.qa))throw new IllegalStateException("Private QA directory must not be linked");
        JsonObject owner=JsonParser.parseString(read(p.root.getParent().resolve("awft-owned.json"))).getAsJsonObject();
        if(!owner.get("format").getAsString().equals("awft-owned-client:1"))throw new IllegalStateException("Existing owned client marker required");
        JsonObject auth=JsonParser.parseString(read(p.qa.resolve("authorization.json"))).getAsJsonObject();
        if(!auth.get("nonce").getAsString().equals(p.nonce)||!Instant.parse(auth.get("expires").getAsString()).equals(p.expires)||p.expires.isAfter(Instant.now().plusSeconds(8*3600))||!auth.has("server")||!SERVER.equals(auth.get("server").getAsString()))throw new IllegalStateException("Native drink authority revoked or changed");
        if(!read(p.qa.resolve("request.json")).equals(p.requestBytes))throw new IllegalStateException("Native drink request replaced or changed");
    }
    private static boolean viewReady(Minecraft mc,Pending p){
        if(!mc.isGameLoadFinished()||mc.getOverlay()!=null||mc.screen!=null)return false;
        double dx=mc.player.getX()-p.position[0],dy=mc.player.getY()-p.position[1],dz=mc.player.getZ()-p.position[2];
        if(dx*dx+dy*dy+dz*dz>9||!chunks(mc,p.position)||!chunks(mc,p.look))return false;
        Mob target=p.targetMob;
        if(target==null||target.isRemoved()||mc.level.getEntity(target.getId())!=target){
            p.targetMob=null;if(System.nanoTime()<p.nextSearch)return false;p.nextSearch=System.nanoTime()+1_000_000_000L;
            int count=0;for(Entity e:mc.level.entitiesForRendering()){if(count++>=4096)break;if(e.getUUID().equals(p.target)&&e instanceof EasyNPC<?> npc&&npc.getMob()==e){p.targetMob=npc.getMob();break;}}
            target=p.targetMob;
        }
        if(target==null||!target.isAlive())return false;
        double x=target.getX()-p.look[0],y=target.getY()-p.look[1],z=target.getZ()-p.look[2];return x*x+y*y+z*z<=9;
    }
    private static boolean chunks(Minecraft mc,double[] p){int x=Math.floorDiv((int)Math.floor(p[0]),16),z=Math.floorDiv((int)Math.floor(p[2]),16);for(int dx=-1;dx<=1;dx++)for(int dz=-1;dz<=1;dz++)if(!mc.level.getChunkSource().hasChunk(x+dx,z+dz))return false;return true;}
}
