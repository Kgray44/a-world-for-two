package worldfortwo.living;

import java.util.*;

/** Bounded admission for present observers, independent of Minecraft and display creation.
 * Each accepted emission costs one rate token and one active-bubble slot per observer.
 * Observers arriving later are not retroactively charged: native bubbles are shared entities.
 */
public final class AmbientBudget {
    public static final long WINDOW_TICKS=1200;
    public static final int MAX_PER_MINUTE=3,MAX_SIMULTANEOUS=2;
    private static final int MAX_AUDIENCE=128,MAX_TRACKED=512;
    private record Emission(UUID speaker,long tick){}
    private record Active(Emission emission,long expires){}
    private static final class Observer {
        final ArrayDeque<Long> times=new ArrayDeque<>();
        final ArrayList<Active> active=new ArrayList<>();
        void expire(long tick){
            while(!times.isEmpty()&&tick-times.peekFirst()>=WINDOW_TICKS)times.removeFirst();
            active.removeIf(bubble->tick>=bubble.expires());
        }
    }
    private final Map<UUID,Observer> observers=new LinkedHashMap<>();
    private final Map<UUID,Long> speakers=new HashMap<>();
    private long lastTick=Long.MIN_VALUE;

    public synchronized boolean admit(UUID speaker,Collection<UUID> audience,long tick,int lifetimeTicks,int configuredLimit){
        if(speaker==null||audience==null||audience.isEmpty()||audience.size()>MAX_AUDIENCE||
           tick<0||tick<lastTick||lifetimeTicks<1||lifetimeTicks>WINDOW_TICKS||tick>Long.MAX_VALUE-lifetimeTicks)return false;
        Set<UUID> recipients=new LinkedHashSet<>(audience);
        if(recipients.contains(null))return false;
        lastTick=tick;
        observers.values().forEach(observer->observer.expire(tick));
        observers.entrySet().removeIf(entry->entry.getValue().times.isEmpty()&&entry.getValue().active.isEmpty());
        speakers.entrySet().removeIf(entry->tick-entry.getValue()>=WINDOW_TICKS);
        if(Objects.equals(speakers.get(speaker),tick))return false;
        int limit=Math.max(1,Math.min(MAX_PER_MINUTE,configuredLimit));
        long newObservers=recipients.stream().filter(id->!observers.containsKey(id)).count();
        if(observers.size()+newObservers>MAX_TRACKED||!speakers.containsKey(speaker)&&speakers.size()>=MAX_TRACKED)return false;
        // Preflight every recipient before charging any: a crowded audience is one atomic refusal.
        for(UUID id:recipients){
            Observer observer=observers.get(id);
            if(observer!=null&&(observer.times.size()>=limit||observer.active.size()>=MAX_SIMULTANEOUS))return false;
        }
        Emission emission=new Emission(speaker,tick);
        for(UUID id:recipients){
            Observer observer=observers.computeIfAbsent(id,ignored->new Observer());
            observer.times.addLast(tick);observer.active.add(new Active(emission,tick+lifetimeTicks));
        }
        speakers.put(speaker,tick);
        return true;
    }

    /** A failed native entity add frees its active slot. Rate admission remains charged. */
    public synchronized void release(UUID speaker,long tick){
        Emission emission=new Emission(speaker,tick);
        observers.values().forEach(observer->observer.active.removeIf(active->active.emission().equals(emission)));
    }
    public synchronized int emissions(UUID observer,long tick){
        Observer value=observers.get(observer);if(value==null)return 0;value.expire(tick);return value.times.size();
    }
    public synchronized int simultaneous(UUID observer,long tick){
        Observer value=observers.get(observer);if(value==null)return 0;value.expire(tick);return value.active.size();
    }
    public synchronized void clear(){observers.clear();speakers.clear();lastTick=Long.MIN_VALUE;}
}
