package worldfortwo.bridge;

import java.util.HashSet;
import java.util.Set;

/** Small cooperative admission policy shared by the native observers and offline fixture. */
final class MoonlightPreparationBudget {
    static final long BYTE_LIMIT=32L*1024*1024,DEADLINE=60_000_000_000L;
    private final long started;
    private final Set<String> resources=new HashSet<>(),directories=new HashSet<>();
    private String failure;
    private long produced,written;
    MoonlightPreparationBudget(long now){started=now;}
    synchronized void fail(String reason){if(failure==null)failure=reason;}
    synchronized IllegalStateException refuse(String reason){fail(reason);return new IllegalStateException(failure);}
    synchronized void check(long now){
        if(failure!=null)throw new IllegalStateException(failure);
        if(now-started>DEADLINE)throw refuse("Native preparation cooperative deadline exceeded");
    }
    synchronized void produce(int bytes,long now){
        check(now);
        if(bytes<0||bytes>BYTE_LIMIT||produced>BYTE_LIMIT-bytes)throw refuse("Native produced-resource byte budget exceeded");
        produced+=bytes;
    }
    synchronized void write(String id,int bytes,long now){
        check(now);
        if(id==null||id.length()>4096||bytes<0||bytes>BYTE_LIMIT||written>BYTE_LIMIT-bytes)
            throw refuse("Native cache write budget exceeded");
        // Bound native directory allocation as well as logical data bytes.
        int colon=id.indexOf(':');
        if(colon<1||colon==id.length()-1)throw refuse("Native resource identifier required");
        String path=id.substring(colon+1);
        if(path.startsWith("/")||path.contains("\\")||path.contains("//"))throw refuse("Ordinary resource path required");
        String[] parts=path.split("/",-1);
        if(parts.length>32)throw refuse("Native resource directory depth exceeded");
        String prefix="data/"+id.substring(0,colon);
        directories.add("data");directories.add(prefix);
        for(int i=0;i<parts.length;i++){
            if(parts[i].isEmpty()||parts[i].equals(".")||parts[i].equals(".."))throw refuse("Ordinary resource path required");
            if(i<parts.length-1){prefix+="/"+parts[i];directories.add(prefix);}
        }
        resources.add(id);
        if(resources.size()>4096||directories.size()>1024)throw refuse("Native resource node budget exceeded");
        written+=bytes; // Include replacement writes; duplicate IDs do not erase cost.
    }
    synchronized long produced(){return produced;}
    synchronized long written(){return written;}
}
