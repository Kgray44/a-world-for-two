package worldfortwo.presentation;

import com.evandev.connectiblechains.entity.ChainKnotEntity;
import com.evandev.connectiblechains.entity.Chainable;
import com.evandev.zipline.Cable;
import com.evandev.zipline.Cables;
import com.evandev.zipline.compat.connectiblechains.ChainCable;
import java.util.*;
import java.util.concurrent.atomic.AtomicBoolean;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.Vec3;

/** Client-only registration, before Zipline.init. Uses only real loaded links.
 * It does not create entities, read unloaded chunks, send packets or move riders.
 * Native ZiplineLogic keeps ownership of movement, collision, braking and turns.
 */
public final class LoadedChainGraphProvider {
    public static final double MAX_SPAN=80.0;
    private static final int MAX_KNOTS=128,MAX_EDGES=256,MAX_EXITS=8;
    private static final AtomicBoolean REGISTERED=new AtomicBoolean();
    private LoadedChainGraphProvider(){}

    public static void registerOnce(){
        if(REGISTERED.compareAndSet(false,true))Cables.registerProvider(LoadedChainGraphProvider::nearest);
    }

    private static List<ChainKnotEntity> nearby(Level level,Vec3 pos,double radius){
        var found=level.getEntitiesOfClass(ChainKnotEntity.class,new AABB(pos,pos).inflate(radius),e->!e.isRemoved());
        if(found.size()>MAX_KNOTS)return List.of();
        found.sort(Comparator.comparing(e->e.getUUID().toString()));return found;
    }

    private static SortedMap<String,Span> edges(Level level,List<ChainKnotEntity> knots,ChainKnotEntity shared){
        SortedMap<String,Span> result=new TreeMap<>();
        for(ChainKnotEntity owner:knots){
            if(owner.level()!=level||owner.isRemoved())continue;
            for(Chainable.ChainData link:new ArrayList<>(owner.getChainDataSet())){
                if(!(owner.getChainHolder(link) instanceof ChainKnotEntity other)||other.isRemoved()||other.level()!=level)continue;
                if(shared!=null&&owner!=shared&&other!=shared)continue;
                double length=owner.position().distanceTo(other.position());float slack=link.getSlack();
                if(!Double.isFinite(length)||length<0.01||length>MAX_SPAN||!Float.isFinite(slack)||slack<=0||slack>512)continue;
                Span span=new Span(level,owner,other,slack);
                if(span.isValid())result.putIfAbsent(span.id,span);
                if(result.size()>MAX_EDGES)return new TreeMap<>();
            }
        }
        return result;
    }

    private static Cable nearest(Level level,Vec3 point,double maximumDistanceSquared){
        if(level==null||point==null||!Double.isFinite(maximumDistanceSquared)||maximumDistanceSquared<=0||maximumDistanceSquared>64)return null;
        Cable best=null;double distance=maximumDistanceSquared;
        for(Span span:edges(level,nearby(level,point,MAX_SPAN+Math.sqrt(distance)+1),null).values()){
            double d=span.getClosestPoint(point).distanceToSqr(point);
            if(d<distance){distance=d;best=span;}
        }
        return best;
    }

    private static final class Span implements Cable {
        private final Level level;
        private final ChainKnotEntity owner,other,low,high;
        private final float slack;
        private final ChainCable nativeCurve;
        private final String id;

        Span(Level level,ChainKnotEntity owner,ChainKnotEntity other,float slack){
            this.level=level;this.owner=owner;this.other=other;this.slack=slack;
            this.low=owner.getY()>other.getY()?other:owner;this.high=low==owner?other:owner;
            nativeCurve=ChainCable.from(owner,other,slack);
            String a=owner.getUUID().toString(),b=other.getUUID().toString();id=a.compareTo(b)<0?a+":"+b:b+":"+a;
        }
        @Override public double getProgress(Vec3 pos){return nativeCurve.getProgress(pos);}
        @Override public Vec3 getPoint(double progress){return nativeCurve.getPoint(progress);}
        @Override public Vec3 getClosestPoint(Vec3 pos){return nativeCurve.getClosestPoint(pos);}
        @Override public Vec3 direction(double progress){return nativeCurve.direction(progress);}
        @Override public double length(){return nativeCurve.length();}
        @Override public boolean isValid(){
            if(owner.isRemoved()||other.isRemoved()||owner.level()!=level||other.level()!=level||length()>MAX_SPAN)return false;
            Chainable.ChainData actual=owner.getChainData(other);
            return actual!=null&&actual.isAlive()&&owner.getChainHolder(actual)==other&&Float.compare(actual.getSlack(),slack)==0
                &&nativeCurve.from().distanceToSqr(low.position())<1e-10&&nativeCurve.to().distanceToSqr(high.position())<1e-10;
        }
        @Override public Collection<Cable> getNext(boolean forward){
            if(!isValid())return List.of();
            ChainKnotEntity shared=forward?high:low;
            List<Cable> exits=new ArrayList<>();
            for(Span next:edges(level,nearby(level,shared.position(),MAX_SPAN+1),shared).values()){
                if(!equals(next)&&next.isValid())exits.add(next);
                if(exits.size()>MAX_EXITS)return List.of();
            }
            return List.copyOf(exits);
        }
        @Override public boolean equals(Object other){return other instanceof Span span&&level==span.level&&id.equals(span.id);}
        @Override public int hashCode(){return 31*System.identityHashCode(level)+id.hashCode();}
    }
}
