package worldfortwo.bridge;

import java.util.*;

/** Bounded collection-only probe of the production scope; no Level/server is created. */
public final class TreeGrowthScopeGridProbe {
    private static long equalCalls;
    private record GridKey(long value) implements Comparable<GridKey> {
        public int hashCode(){return Long.hashCode(value);}
        public boolean equals(Object other){equalCalls++;return other instanceof GridKey key&&key.value==value;}
        public int compareTo(GridKey other){return Long.compare(value,other.value);}
    }
    private static void check(boolean condition,String message){if(!condition)throw new AssertionError(message);}
    private static void unsupported(Runnable action){try{action.run();throw new AssertionError("Mutable snapshot");}catch(UnsupportedOperationException expected){}}
    private static void nullRejected(Runnable action){try{action.run();throw new AssertionError("Null accepted");}catch(NullPointerException expected){}}
    public static void main(String[] args){
        check(Runtime.getRuntime().availableProcessors()<=2,"CPU bound absent");
        check(Runtime.getRuntime().maxMemory()<=256L*1024*1024,"Heap bound absent");
        Set<GridKey> small=new HashSet<>();
        for(int x=0;x<32;x++)for(int z=-32;z<0;z++)small.add(new GridKey(TreeGrowthScope.column(x,z)));
        equalCalls=0;long oldStarted=System.nanoTime();Set<GridKey> old=Set.copyOf(small);
        long oldNanos=System.nanoTime()-oldStarted,oldEquals=equalCalls;
        check(old.getClass().getName().equals("java.util.ImmutableCollections$SetN"),"Expected Java21 SetN not observed");
        check(oldEquals>small.size()*100L,"Small regular grid did not demonstrate pathological linear probing");
        equalCalls=0;Set<GridKey> fixedSmall=TreeGrowthScope.snapshotSet(small);long fixedEquals=equalCalls;
        check(fixedSmall.equals(small),"Small snapshot membership differs");
        check(fixedEquals*8<oldEquals,"Hash-backed collision handling not observed");
        Map<GridKey,Integer> smallMap=new HashMap<>();for(GridKey key:small)smallMap.put(key,1);
        equalCalls=0;Map<GridKey,Integer> oldMap=Map.copyOf(smallMap);long oldMapEquals=equalCalls;
        check(oldMap.getClass().getName().equals("java.util.ImmutableCollections$MapN"),"Expected Java21 MapN not observed");
        equalCalls=0;Map<GridKey,Integer> fixedSmallMap=TreeGrowthScope.snapshotMap(smallMap);long fixedMapEquals=equalCalls;
        check(fixedSmallMap.equals(smallMap),"Small map snapshot differs");
        check(oldMapEquals>small.size()*100L&&fixedMapEquals*8<oldMapEquals,"Map grid clustering/collision handling not observed");

        Set<Long> source=new HashSet<>();Map<Long,Integer> sourceMap=new HashMap<>();
        for(int x=800;x<1312;x++)for(int z=-1408;z<-1152;z++){
            long key=TreeGrowthScope.column(x,z);source.add(key);sourceMap.put(key,x+z);
        }
        check(source.size()==131072,"Large regular grid differs");
        long started=System.nanoTime();
        Set<Long> snapshot=TreeGrowthScope.snapshotSet(source);
        Map<Long,Integer> snapshotMap=TreeGrowthScope.snapshotMap(sourceMap);
        for(long key:source){check(snapshot.contains(key),"Protected column missing");check(snapshotMap.get(key).equals(sourceMap.get(key)),"Preimage value differs");}
        check(!snapshot.contains(TreeGrowthScope.column(799,-1408)),"Foreign column accepted");
        check(!snapshotMap.containsKey(TreeGrowthScope.column(1312,-1152)),"Foreign preimage accepted");
        long elapsed=System.nanoTime()-started;
        check(elapsed<10_000_000_000L,"Large production snapshots exceeded finite10s envelope");
        source.clear();sourceMap.clear();
        check(snapshot.size()==131072&&snapshotMap.size()==131072,"Snapshots alias caller collections");
        unsupported(()->snapshot.add(0L));unsupported(()->snapshot.remove(snapshot.iterator().next()));
        unsupported(()->snapshot.iterator().remove());
        unsupported(()->snapshotMap.put(0L,0));unsupported(()->snapshotMap.clear());
        unsupported(()->snapshotMap.entrySet().iterator().next().setValue(0));
        Set<Long> badSet=new HashSet<>();badSet.add(null);nullRejected(()->TreeGrowthScope.snapshotSet(badSet));
        Map<Long,Integer> badKey=new HashMap<>();badKey.put(null,1);nullRejected(()->TreeGrowthScope.snapshotMap(badKey));
        Map<Long,Integer> badValue=new HashMap<>();badValue.put(1L,null);nullRejected(()->TreeGrowthScope.snapshotMap(badValue));
        nullRejected(()->TreeGrowthScope.snapshotSet(null));nullRejected(()->TreeGrowthScope.snapshotMap(null));
        check(TreeGrowthScope.snapshotSet(Set.of()).isEmpty(),"Empty protection changed");
        check(TreeGrowthScope.snapshotMap(Map.of()).isEmpty(),"Empty preimage changed");
        System.out.printf(Locale.ROOT,"{\"passed\":true,\"small_grid\":1024,\"old_setn_equals\":%d,\"hash_snapshot_equals\":%d,\"old_mapn_equals\":%d,\"hash_map_snapshot_equals\":%d,\"old_small_ms\":%.3f,\"large_grid\":131072,\"production_copy_and_membership_ms\":%.3f,\"max_heap_bytes\":%d,\"processors\":%d,\"native_world_actions\":false}%n",oldEquals,fixedEquals,oldMapEquals,fixedMapEquals,oldNanos/1e6,elapsed/1e6,Runtime.getRuntime().maxMemory(),Runtime.getRuntime().availableProcessors());
    }
}
