package worldfortwo.qa;

import com.google.gson.JsonArray;
import de.markusbordihn.easynpc.entity.easynpc.EasyNPC;
import immersive_melodies.Common;
import immersive_melodies.Config;
import immersive_melodies.client.MelodyProgress;
import immersive_melodies.client.MelodyProgressManager;
import immersive_melodies.item.InstrumentItem;
import net.minecraft.client.Minecraft;
import net.minecraft.client.model.HumanoidModel;
import net.minecraft.client.model.geom.ModelPart;
import net.minecraft.client.multiplayer.ClientLevel;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.item.ItemStack;
import net.neoforged.neoforge.client.event.RenderLivingEvent;
import net.neoforged.neoforge.common.NeoForge;
import java.lang.invoke.MethodHandles;
import java.lang.invoke.VarHandle;
import java.time.Instant;
import java.util.*;

/** One bounded read of existing NPC/music state; no AI/model/item changes. */
public final class NpcClientSnapshot {
    private static final UUID OWNER=UUID.fromString("32650cdf-2aaa-4f47-bb27-42ef0d1249fd");
    private static final int MAX_ENTITIES=4096, MAX_REQUESTS=16;
    private Pending pending;
    private int requests;

    private static final class Pending {
        final String id,server;
        final Set<UUID> targets;
        final Instant expires;
        final ClientLevel level;
        final long frame,deadline=System.nanoTime()+10_000_000_000L;
        final Map<UUID,Map<String,Object>> rendered=new HashMap<>();
        Pending(String id,String server,Set<UUID> targets,Instant expires,ClientLevel level,long frame) {
            this.id=id;this.server=server;this.targets=targets;this.expires=expires;this.level=level;this.frame=frame;
        }
    }

    public NpcClientSnapshot(){NeoForge.EVENT_BUS.addListener(this::rendered);}
    public void cancel(){pending=null;}

    private boolean valid(Minecraft mc,Pending p) {
        return p!=null && Instant.now().isBefore(p.expires) && System.nanoTime()<p.deadline
            && mc.level==p.level && mc.player!=null && OWNER.equals(mc.player.getUUID())
            && OWNER.equals(mc.getUser().getProfileId()) && mc.getCurrentServer()!=null
            && p.server.equals(mc.getCurrentServer().ip) && p.server.equals("127.0.0.1:25575")
            && mc.isGameLoadFinished() && mc.getOverlay()==null && mc.screen==null;
    }

    public Map<String,Object> poll(Minecraft mc,String id,JsonArray input,Instant expires,String server,long frame) {
        if(input==null || input.size()<1 || input.size()>5)throw new IllegalArgumentException("Specify one to five distinct NPC UUIDs");
        Set<UUID> targets=new LinkedHashSet<>();
        for(var value:input)if(!targets.add(UUID.fromString(value.getAsString())))throw new IllegalArgumentException("Duplicate target UUID");
        if(pending==null || !pending.id.equals(id)) {
            if(requests>=MAX_REQUESTS)throw new IllegalStateException("Sixteen NPC snapshots per launch exhausted");
            Pending p=new Pending(id,server,targets,expires,mc.level,frame);
            if(!valid(mc,p))throw new IllegalStateException("Ready authenticated staging session required");
            requests++;pending=p;return null;
        }
        Pending p=pending;
        if(!p.targets.equals(targets))throw new IllegalArgumentException("Targets changed under the same request ID");
        if(!valid(mc,p)){pending=null;throw new IllegalStateException("Snapshot authority/session expired or changed");}
        if(frame<=p.frame)return null;
        Map<UUID,Entity> found=new HashMap<>();int scanned=0;boolean limited=false;
        for(Entity e:mc.level.entitiesForRendering()) {
            if(scanned>=MAX_ENTITIES){limited=true;break;}
            scanned++;if(targets.contains(e.getUUID()))found.put(e.getUUID(),e);
        }
        List<Map<String,Object>> entities=new ArrayList<>();
        for(UUID target:targets) {
            Entity e=found.get(target);
            Map<String,Object> row=new LinkedHashMap<>();row.put("uuid",target.toString());
            if(e==null)row.put("client_entity_status",limited?"not found in bounded scan; remaining entities not searched":"not present in existing client entity collection");
            else {
                row.putAll(entity(mc,e));
                Map<String,Object> render=p.rendered.get(target);
                row.put("render_observation",render==null?Map.of("status","not rendered while armed; no forced render or renderer construction"):render);
            }
            entities.add(row);
        }
        Map<String,Object> result=new LinkedHashMap<>();
        result.put("at",Instant.now().toString());result.put("action","npc-client-snapshot");
        result.put("server",server);result.put("dimension",mc.level.dimension().location().toString());
        result.put("client_game_time",mc.level.getGameTime());result.put("scanned_entities",scanned);result.put("scan_limit",MAX_ENTITIES);result.put("scan_limited",limited);
        result.put("camera_position",List.of(mc.gameRenderer.getMainCamera().getPosition().x,mc.gameRenderer.getMainCamera().getPosition().y,mc.gameRenderer.getMainCamera().getPosition().z));
        result.put("master_volume",mc.options.getSoundSourceVolume(SoundSource.MASTER));result.put("neutral_volume",mc.options.getSoundSourceVolume(SoundSource.NEUTRAL));
        result.put("entities",entities);
        result.put("evidence_limit","Existing client state and attributed RenderLivingEvent.Post observations only. Post-event model fields may already be restored by a renderer; angles are not framebuffer proof, audio playback proof, or server persistence evidence.");
        pending=null;return result;
    }

    private void rendered(RenderLivingEvent.Post<?,?> event) {
        Pending p=pending;Minecraft mc=Minecraft.getInstance();
        if(!valid(mc,p))return;
        Entity e=event.getEntity();UUID id=e.getUUID();
        if(!p.targets.contains(id) || p.rendered.containsKey(id))return;
        Map<String,Object> row=new LinkedHashMap<>();
        row.put("status","observed actual RenderLivingEvent.Post");row.put("at",Instant.now().toString());
        row.put("entity_id",e.getId());row.put("entity_class",e.getClass().getName());
        row.put("renderer_class",event.getRenderer().getClass().getName());
        Object model=event.getRenderer().getModel();row.put("model_class",model.getClass().getName());
        row.put("entity_is_passenger",e.isPassenger());row.put("vehicle_id",e.getVehicle()==null?null:e.getVehicle().getId());
        if(model instanceof HumanoidModel<?> h) {
            row.put("model_riding",h.riding);row.put("model_crouching",h.crouching);
            row.put("left_arm_pose",h.leftArmPose.name());row.put("right_arm_pose",h.rightArmPose.name());
            row.put("parts",Map.of("head",part(h.head),"body",part(h.body),"left_arm",part(h.leftArm),"right_arm",part(h.rightArm),"left_leg",part(h.leftLeg),"right_leg",part(h.rightLeg)));
        }else row.put("humanoid_parts","not a HumanoidModel; no assumptions made");
        row.put("measurement_stage","Post event only; no model fields written and no draw-equivalence claimed");p.rendered.put(id,row);
    }

    private static Object number(float v){return Float.isFinite(v)?v:"non-finite";}
    private static Map<String,Object> part(ModelPart p) {
        return Map.of("x",number(p.x),"y",number(p.y),"z",number(p.z),"xRot",number(p.xRot),"yRot",number(p.yRot),"zRot",number(p.zRot),"visible",p.visible);
    }

    private static Map<String,Object> entity(Minecraft mc,Entity e) {
        Map<String,Object> row=new LinkedHashMap<>();row.put("client_entity_status","present");row.put("entity_id",e.getId());
        row.put("entity_class",e.getClass().getName());row.put("entity_type",BuiltInRegistries.ENTITY_TYPE.getKey(e.getType()).toString());
        row.put("position",List.of(e.getX(),e.getY(),e.getZ()));row.put("pose",e.getPose().name());row.put("is_passenger",e.isPassenger());
        row.put("camera_distance",mc.gameRenderer.getMainCamera().getPosition().distanceTo(e.position()));
        Entity v=e.getVehicle();
        row.put("vehicle",v==null?null:Map.of("id",v.getId(),"type",BuiltInRegistries.ENTITY_TYPE.getKey(v.getType()).toString(),"class",v.getClass().getName(),"position",List.of(v.getX(),v.getY(),v.getZ())));
        if(!(e instanceof EasyNPC<?> npc)){row.put("easy_npc",false);return row;}
        row.put("easy_npc",true);Mob m=npc.getMob();row.put("npc_mob_same_entity",m==e);row.put("npc_mob_class",m.getClass().getName());row.put("npc_mob_uuid",m.getUUID().toString());
        row.put("is_using_item",m.isUsingItem());row.put("used_hand",m.getUsedItemHand().name());row.put("use_remaining_ticks",m.getUseItemRemainingTicks());row.put("ticks_using_item",m.getTicksUsingItem());
        row.put("main_arm",m.getMainArm().name());row.put("main_hand",hand(m,m.getMainHandItem()));row.put("off_hand",hand(m,m.getOffhandItem()));row.put("active_use_item",hand(m,m.getUseItem()));
        var skin=npc.getEasyNPCSkinData().getSkinDataEntry();
        row.put("skin",skin==null?null:Map.of("type",String.valueOf(skin.type()),"texture",String.valueOf(skin.texture())));
        var model=npc.getEasyNPCModelData();Map<String,Object> pose=new LinkedHashMap<>();
        pose.put("pose",String.valueOf(model.getModelPose()));pose.put("pose_name",String.valueOf(model.getModelPoseName()));pose.put("model_type",String.valueOf(model.getModelType()));
        pose.put("default_pose",String.valueOf(model.getDefaultPose()));pose.put("animation_behavior",String.valueOf(model.getModelAnimationBehavior()));pose.put("animation_request_present",model.getModelAnimationRequest().isPresent());
        pose.put("can_use_main_hand",model.canUseMainHand());pose.put("can_use_off_hand",model.canUseOffHand());row.put("easy_npc_model",pose);
        row.put("immersive_melodies",music(m));return row;
    }

    private static Map<String,Object> hand(Mob mob,ItemStack stack) {
        Map<String,Object> row=new LinkedHashMap<>();row.put("empty",stack.isEmpty());row.put("count",stack.getCount());
        row.put("item",BuiltInRegistries.ITEM.getKey(stack.getItem()).toString());row.put("item_class",stack.getItem().getClass().getName());
        row.put("use_animation",stack.getUseAnimation().name());row.put("native_use_duration",stack.getUseDuration(mob));
        if(stack.getItem() instanceof InstrumentItem) {
            Map<String,Object> components=new LinkedHashMap<>();
            components.put("playing",stack.getOrDefault(InstrumentItem.PLAYING,false));
            var melody=stack.get(InstrumentItem.MELODY);components.put("melody",melody==null?null:melody.toString());
            components.put("start_time",stack.get(InstrumentItem.START_TIME));components.put("paused_time",stack.get(InstrumentItem.PAUSED_TIME));
            var tracks=stack.get(InstrumentItem.TRACKS);components.put("tracks",tracks==null?null:List.copyOf(tracks.subList(0,Math.min(32,tracks.size()))));
            components.put("tracks_truncated",tracks!=null && tracks.size()>32);row.put("instrument_components",components);
        }
        return row;
    }

    private static Map<String,Object> music(Mob m) {
        Map<String,Object> row=new LinkedHashMap<>();
        try {
            // Exact pinned field; do NOT call getProgress(), which creates entries.
            VarHandle handle=MethodHandles.privateLookupIn(MelodyProgressManager.class,MethodHandles.lookup()).findVarHandle(MelodyProgressManager.class,"progress",Map.class);
            @SuppressWarnings("unchecked") Map<Entity,MelodyProgress> existing=(Map<Entity,MelodyProgress>)handle.get(MelodyProgressManager.INSTANCE);
            MelodyProgress p=existing.get(m);row.put("existing_progress_entry",p!=null);
            if(p!=null) {
                row.put("time",p.getTime());var melody=p.getCurrentlyPlaying();row.put("currently_playing",melody==null?null:melody.toString());
                row.put("is_playing",p.isPlaying());row.put("last_note_age_ms",p.delta());row.put("current",number(p.getCurrent()));row.put("current_volume",number(p.getCurrentVolume()));row.put("current_pitch",number(p.getCurrentPitch()));
                Set<Integer> tracks=new LinkedHashSet<>();
                for(ItemStack stack:List.of(m.getMainHandItem(),m.getOffhandItem())) {
                    var list=stack.get(InstrumentItem.TRACKS);if(list!=null)for(int i=0;i<Math.min(16,list.size());i++)tracks.add(list.get(i));
                }
                Map<String,Integer> lastIndices=new LinkedHashMap<>();for(Integer track:tracks)lastIndices.put(track.toString(),p.getLastIndex(track));row.put("last_indices_for_existing_hand_tracks",lastIndices);
            }
        } catch(ReflectiveOperationException | RuntimeException failure) { row.put("progress_read_unavailable",failure.getClass().getName()); }
        row.put("sound_manager_present",Common.soundManager!=null);
        if(Common.soundManager!=null)try {row.put("native_audible",Common.soundManager.audible(m));}catch(RuntimeException failure){row.put("native_audible_unavailable",failure.getClass().getName());}
        Config c=Config.getInstance();row.put("max_audible_distance",c.maxAudibleDistance);row.put("instrument_volume_factor",number(c.instrumentVolumeFactor));row.put("auto_synchronize",c.autoSynchronize);row.put("buffer_delay",c.bufferDelay);
        String id=BuiltInRegistries.ENTITY_TYPE.getKey(m.getType()).toString();row.put("mob_instrument_factor",number(c.mobInstrumentFactors.getOrDefault(id,1F)));
        row.put("note","No playback entry created; no getMelody/cache load, tick, note, sound, play or synchronization call performed");return row;
    }
}
