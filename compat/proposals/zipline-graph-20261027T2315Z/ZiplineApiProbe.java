package worldfortwo.presentation;

import com.evandev.zipline.Cable;
import com.evandev.zipline.Cables;
import com.evandev.zipline.compat.connectiblechains.ChainCable;
import java.util.*;
import net.minecraft.world.phys.Vec3;

/** Standalone real pinned API probe. No Level, entity or player is created. */
public final class ZiplineApiProbe {
    private static int checks;
    private static void check(boolean pass,String why){checks++;if(!pass)throw new IllegalStateException(why);}
    private static ChainCable curve(Vec3 a,Vec3 b,double slack){
        if(a.y>b.y){Vec3 temporary=a;a=b;b=temporary;}
        Vec3 delta=b.subtract(a);return new ChainCable(a,b,delta,delta.normalize(),delta.length(),slack);
    }
    private static void close(Vec3 a,Vec3 b,String why){check(a.distanceToSqr(b)<1e-12,why);}
    public static void main(String[] args){
        boolean originalFirst=args.length>0&&args[0].equals("original-first");
        ChainCable ab=curve(new Vec3(1160.5,168,-759.5),new Vec3(1168.5,155,-824.5),16);
        ChainCable bc=curve(new Vec3(1168.5,155,-824.5),new Vec3(1175.5,142,-889.5),16);
        close(ab.getPoint(0),new Vec3(1168.5,155.40000000596046,-824.5),"Native low endpoint offset changed");
        close(ab.getPoint(1),new Vec3(1160.5,168.40000000596046,-759.5),"Native high endpoint offset changed");
        close(ab.getPoint(0),bc.getPoint(1),"Shared real-knot curves must meet exactly");
        check(ab.getNext(true).isEmpty()&&ab.getNext(false).isEmpty(),"Stock ChainCable getNext boundary changed; re-review adapter");
        check(ab.length()<80&&bc.length()<80,"Probe spans exceeded real local envelope");
        double turn=ab.direction(0).dot(bc.direction(0));check(turn>0.707,"Actual native chord turn would refuse this handoff");
        double sag=(ab.from().y+ab.to().y)/2+0.4000000059604645-ab.getPoint(0.5).y;
        check(sag>0&&sag<2,"Pinned16-slack short-span shape changed");
        ChainCable original=curve(new Vec3(0,8,0),new Vec3(0,0,32),16);
        Cable wrapper=new Cable(){
            public double getProgress(Vec3 p){return original.getProgress(p);}
            public Vec3 getPoint(double t){return original.getPoint(t);}
            public Vec3 getClosestPoint(Vec3 p){return original.getClosestPoint(p);}
            public Vec3 direction(double t){return original.direction(t);}
            public double length(){return original.length();}
            public Collection<Cable> getNext(boolean forward){return List.of(bc);}
        };
        if(originalFirst){Cables.registerProvider((unused,p,d)->original);Cables.registerProvider((unused,p,d)->wrapper);}
        else{Cables.registerProvider((unused,p,d)->wrapper);Cables.registerProvider((unused,p,d)->original);}
        Vec3 near=original.getPoint(0.5);Cable selected=Cables.getClosestCable(null,near,3);
        check(selected==(originalFirst?original:wrapper),"Pinned provider equality/ordering contract changed");
        check(wrapper.getNext(false).iterator().next()==bc,"Public Cable.getNext hook cannot deliver adjacent native curves");
        check(LoadedChainGraphProvider.MAX_SPAN==80,"Declared bounded local graph span changed");
        System.out.println("{\"checks\":"+checks+",\"provider_registered_first\":\""+(originalFirst?"stock":"wrapper")+"\",\"selected\":\""+(selected==wrapper?"wrapper":"stock")+"\",\"actual_api_midpoint_sag\":"+sag+",\"actual_api_turn_dot\":"+turn+",\"worlds_or_entities_created\":0,\"native_ride_acceptance\":false}");
    }
}
