package worldfortwo.bridge;
import com.google.gson.*;
public final class QuarantinedAuditProbe {
    private static int count;
    private static void reject(JsonObject p){try{NativeRelocationSupport.Quarantined.validate(p,"tx","room");throw new AssertionError("Unexpected admission");}catch(IllegalStateException expected){count++;}}
    public static void main(String[] args){
        JsonObject p=new JsonObject();p.addProperty("transaction_id","tx");p.addProperty("capsule_id","room");p.addProperty("operation","move");
        for(String key:new String[]{"clone_invoked","intent_written","failed","quarantine","cleanup_passed"})p.addProperty(key,true);
        for(String key:new String[]{"owned_chunk_tickets","pending_owned_futures","pending_shared_chunk_futures"})p.addProperty(key,0);
        NativeRelocationSupport.Quarantined.validate(p,"tx","room");count++;
        for(String key:new String[]{"clone_invoked","intent_written","failed","quarantine","cleanup_passed"}){JsonObject q=p.deepCopy();q.addProperty(key,false);reject(q);}
        for(String key:new String[]{"owned_chunk_tickets","pending_owned_futures","pending_shared_chunk_futures"}){JsonObject q=p.deepCopy();q.addProperty(key,1);reject(q);}
        JsonObject q=p.deepCopy();q.addProperty("operation","inspect");reject(q);q=p.deepCopy();q.addProperty("transaction_id","foreign");reject(q);
        q=p.deepCopy();q.addProperty("ticket_cleanup_error","retained");reject(q);
        System.out.println("PASS "+count+" production invoked-quarantine authority checks; no clone/world/entity calls");
    }
}
