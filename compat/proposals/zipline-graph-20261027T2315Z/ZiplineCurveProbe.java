package worldfortwo.presentation;

import com.evandev.zipline.compat.connectiblechains.ChainCable;
import com.google.gson.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import net.minecraft.world.phys.Vec3;

/** Bounded actual-binary curve evaluation at PROPOSED numeric knot positions.
 * No fake Level/entity/player. It does not certify a native-world route.
 */
public final class ZiplineCurveProbe {
    private static Vec3 point(JsonArray p){
        if(p.size()!=3)throw new IllegalArgumentException("Three coordinates required");
        Vec3 result=new Vec3(p.get(0).getAsDouble(),p.get(1).getAsDouble(),p.get(2).getAsDouble());
        if(!Double.isFinite(result.x)||!Double.isFinite(result.y)||!Double.isFinite(result.z)
            ||Math.abs(result.x)>250000||Math.abs(result.z)>250000||result.y<-64||result.y>320)throw new IllegalArgumentException("Finite proposed knot envelope required");
        return result;
    }
    public static void main(String[] args)throws Exception{
        Path input=Path.of(args[0]);if(Files.size(input)>65536)throw new IllegalArgumentException("Finite curve input required");
        JsonArray segments=JsonParser.parseString(Files.readString(input,StandardCharsets.UTF_8)).getAsJsonObject().getAsJsonArray("segments");
        if(segments.size()<1||segments.size()>16)throw new IllegalArgumentException("At most16 proposed segments");
        JsonObject result=new JsonObject();JsonArray output=new JsonArray();result.add("segments",output);
        for(JsonElement element:segments){JsonObject in=element.getAsJsonObject();Vec3 a=point(in.getAsJsonArray("a")),b=point(in.getAsJsonArray("b"));
            if(a.y>b.y){Vec3 temporary=a;a=b;b=temporary;}
            Vec3 delta=b.subtract(a);double length=delta.length(),slack=in.get("slack").getAsDouble();
            if(length<0.01||length>80||!Double.isFinite(slack)||slack<=0||slack>512)throw new IllegalArgumentException("Bounded actual local span/slack required");
            ChainCable nativeCurve=new ChainCable(a,b,delta,delta.normalize(),length,slack);
            JsonObject row=new JsonObject();row.addProperty("label",in.get("label").getAsString());row.addProperty("length",length);row.addProperty("slack",slack);JsonArray points=new JsonArray();
            int count=(int)Math.ceil(length*4);
            for(int n=0;n<=count;n++){Vec3 p=nativeCurve.getPoint((double)n/count);JsonArray v=new JsonArray();v.add(p.x);v.add(p.y);v.add(p.z);points.add(v);}
            row.add("points",points);output.add(row);
        }
        result.addProperty("actual_pinned_ChainCable_math",true);result.addProperty("worlds_or_entities_created",0);result.addProperty("native_world_route_acceptance",false);
        System.out.println(new Gson().toJson(result));
    }
}
