package worldfortwo.materialprobe;

import com.google.gson.Gson;
import com.google.gson.JsonParser;
import java.nio.file.*;
import java.security.MessageDigest;
import java.time.Instant;
import java.util.*;
import net.minecraft.client.Minecraft;
import net.minecraft.client.renderer.texture.TextureAtlas;
import net.minecraft.client.renderer.texture.TextureAtlasSprite;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.world.phys.BlockHitResult;
import net.neoforged.api.distmarker.Dist;
import net.neoforged.fml.common.Mod;
import net.neoforged.neoforge.common.NeoForge;
import net.neoforged.neoforge.client.event.RenderFrameEvent;
import net.irisshaders.iris.pbr.texture.PBRAtlasTexture;
import net.irisshaders.iris.pbr.texture.PBRTextureManager;

/** Opt-in, test-only resource/atlas observation; never creates textures or edits a world. */
@Mod(value="awft_material_probe", dist=Dist.CLIENT)
public final class MaterialProbe {
    private long next;
    private final Gson gson=new Gson();
    private static final List<String> SPRITES=List.of("oak_log","oak_log_top","grass_block_top",
        "grass_block_side","grass_block_side_overlay","stone_bricks");
    public MaterialProbe(){NeoForge.EVENT_BUS.addListener(this::frame);}
    private void frame(RenderFrameEvent.Post event){
        long now=System.nanoTime();if(now<next)return;next=now+10_000_000_000L;
        Minecraft mc=Minecraft.getInstance();
        if(mc.level==null||mc.player==null||mc.getOverlay()!=null)return;
        try {
            Path game=mc.gameDirectory.toPath().toRealPath(),instance=game.getParent();
            if(!instance.getFileName().toString().matches("AWFT_Check_\\d{8}_\\d{6}"))return;
            Path request=game.resolve("awft-material-probe.request.json"),owner=instance.resolve("awft-owned.json");
            if(!Files.isRegularFile(request)||Files.size(request)>4096||!Files.isRegularFile(owner)||Files.size(owner)>1048576)return;
            var r=JsonParser.parseString(Files.readString(request)).getAsJsonObject();
            var o=JsonParser.parseString(Files.readString(owner)).getAsJsonObject();
            if(!r.get("format").getAsString().equals("awft-material-probe:1")
                ||!r.get("root").getAsString().equals(instance.toString())
                ||!o.get("format").getAsString().equals("awft-owned-client:1")
                ||!o.get("root").getAsString().equals(instance.toString()))return;
            Map<String,Object> report=new LinkedHashMap<>();
            report.put("at",Instant.now().toString());report.put("pid",ProcessHandle.current().pid());
            report.put("scope","Read-only resource and existing Iris atlas observation, not visual acceptance");
            var atlas=mc.getModelManager().getAtlas(TextureAtlas.LOCATION_BLOCKS);
            var holder=PBRTextureManager.INSTANCE.getHolder(atlas.getId());
            var normal=holder==null?null:holder.normalTexture();
            report.put("base_atlas_id",atlas.getId());
            report.put("normal_texture_class",normal==null?"absent":normal.getClass().getName());
            if(mc.hitResult instanceof BlockHitResult hit)report.put("target_block",
                BuiltInRegistries.BLOCK.getKey(mc.level.getBlockState(hit.getBlockPos()).getBlock()).toString());
            List<Map<String,Object>> rows=new ArrayList<>();
            for(String name:SPRITES){
                Map<String,Object> row=new LinkedHashMap<>();row.put("sprite",name);
                TextureAtlasSprite base=atlas.getSprite(ResourceLocation.withDefaultNamespace("block/"+name));
                row.put("base_sprite",base.contents().name().toString());
                row.put("base_size",List.of(base.contents().width(),base.contents().height()));
                if(normal instanceof PBRAtlasTexture pbr){
                    TextureAtlasSprite sprite=pbr.getSprite(ResourceLocation.withDefaultNamespace("block/"+name));
                    if(sprite==null)sprite=pbr.getSprite(ResourceLocation.withDefaultNamespace("block/"+name+"_n"));
                    row.put("normal_sprite_present",sprite!=null);
                    if(sprite!=null){row.put("normal_sprite",sprite.contents().name().toString());
                        row.put("normal_size",List.of(sprite.contents().width(),sprite.contents().height()));}
                }else row.put("normal_sprite_present",false);
                for(String suffix:List.of("","_n")){
                    var resource=mc.getResourceManager().getResource(ResourceLocation.withDefaultNamespace("textures/block/"+name+suffix+".png"));
                    String key=suffix.isEmpty()?"albedo":"normal";
                    if(resource.isPresent()){
                        row.put(key+"_pack",resource.get().sourcePackId());
                        try(var in=resource.get().open()){
                            byte[] bytes=in.readNBytes(1048577);if(bytes.length>1048576)throw new IllegalStateException("Probe PNG bound exceeded");
                            row.put(key+"_sha256",HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(bytes)));
                        }
                    }else row.put(key+"_pack","absent");
                }
                rows.add(row);
            }
            report.put("sprites",rows);
            Path output=game.resolve("awft-material-probe.json"),temp=game.resolve("awft-material-probe.json.tmp");
            String text=gson.toJson(report);if(text.length()>32768)throw new IllegalStateException("Probe receipt bound exceeded");
            Files.writeString(temp,text);Files.move(temp,output,StandardCopyOption.REPLACE_EXISTING,StandardCopyOption.ATOMIC_MOVE);
            if(r.has("exit_after_sample")&&r.get("exit_after_sample").getAsBoolean())mc.stop();
        }catch(Exception error){System.err.println("AWFT material probe: "+error.getClass().getSimpleName()+": "+error.getMessage());}
    }
}
