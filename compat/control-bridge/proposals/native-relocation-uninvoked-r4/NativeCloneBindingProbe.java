package worldfortwo.bridge;

import com.google.gson.*;
import com.mojang.brigadier.Command;
import com.mojang.brigadier.CommandDispatcher;
import com.mojang.brigadier.builder.LiteralArgumentBuilder;
import java.time.Instant;

/** Actual Brigadier/JVM lambda and production pure authority validation only. */
public final class NativeCloneBindingProbe {
    private static int assertions;
    private static void check(boolean value){assertions++;if(!value)throw new AssertionError();}
    private static void refused(Runnable action){try{action.run();throw new AssertionError("Unexpected admission");}catch(IllegalStateException expected){assertions++;}}
    private static JsonObject fixture(){
        JsonObject p=new JsonObject();p.addProperty("transaction_id",NativeRelocationSupport.Uninvoked.TX);
        p.addProperty("capsule_id","eastern22/pippins-net:room:0");p.addProperty("operation","move");
        for(String key:new String[]{"clone_invoked"})p.addProperty(key,false);
        for(String key:new String[]{"intent_written","quarantine","failed","cleanup_passed"})p.addProperty(key,true);
        for(String key:new String[]{"owned_chunk_tickets","pending_owned_futures","pending_shared_chunk_futures"})p.addProperty(key,0);
        p.addProperty("private_error","Pinned real native CloneCommands implementation required");p.addProperty("request_sha256","test-request");
        p.addProperty("finished",Instant.now().minusSeconds(2).toString());p.add("before_native_snapshots",new JsonArray());return p;
    }
    private static JsonObject review(){
        JsonObject r=new JsonObject();r.addProperty("format","awft-explicit-uninvoked-relocation-review:1");r.addProperty("approved",true);
        r.addProperty("allow_exactly_one_new_intent",true);r.addProperty("transaction_id",NativeRelocationSupport.Uninvoked.TX);
        r.addProperty("prior_intent_sha256",NativeRelocationSupport.Uninvoked.INTENT);r.addProperty("prior_quarantine_sha256",NativeRelocationSupport.Uninvoked.QUARANTINE);
        JsonObject terminal=new JsonObject();terminal.addProperty("sha256",NativeRelocationSupport.Uninvoked.TERMINAL);r.add("prior_terminal",terminal);
        r.addProperty("created",Instant.now().minusSeconds(1).toString());return r;
    }
    private static Command<String> foreign(){return Foreign.callback();}
    public static void main(String[] args){
        CommandDispatcher<String> d=new CommandDispatcher<>();
        d.register(LiteralArgumentBuilder.<String>literal("go").executes(c->1));
        d.register(LiteralArgumentBuilder.<String>literal("redirect").redirect(d.getRoot()));
        check(NativeRelocationSupport.CloneBinding.callback(d.parse("go","source"),NativeCloneBindingProbe.class).getNestHost()==NativeCloneBindingProbe.class);
        check(NativeRelocationSupport.CloneBinding.callback(d.parse("redirect go","source"),NativeCloneBindingProbe.class).getNestHost()==NativeCloneBindingProbe.class);
        refused(()->NativeRelocationSupport.CloneBinding.callback(d.parse("go trailing","source"),NativeCloneBindingProbe.class));
        refused(()->NativeRelocationSupport.CloneBinding.callback(d.parse("unknown","source"),NativeCloneBindingProbe.class));
        d.register(LiteralArgumentBuilder.<String>literal("foreign").executes(foreign()));
        refused(()->NativeRelocationSupport.CloneBinding.callback(d.parse("foreign","source"),NativeCloneBindingProbe.class));
        d.register(LiteralArgumentBuilder.<String>literal("anonymous").executes(new Command<String>(){public int run(com.mojang.brigadier.context.CommandContext<String> c){return 1;}}));
        refused(()->NativeRelocationSupport.CloneBinding.callback(d.parse("anonymous","source"),NativeCloneBindingProbe.class));
        JsonObject r=review(),p=fixture(),intent=p.deepCopy(),q=p.deepCopy();
        NativeRelocationSupport.Uninvoked.validate(r,p,intent,q,new JsonArray());assertions++;
        for(String key:new String[]{"clone_invoked","intent_written","quarantine","failed","cleanup_passed"}){
            JsonObject changed=p.deepCopy();changed.addProperty(key,!p.get(key).getAsBoolean());refused(()->NativeRelocationSupport.Uninvoked.validate(r,changed,intent,q,new JsonArray()));
        }
        for(String key:new String[]{"owned_chunk_tickets","pending_owned_futures","pending_shared_chunk_futures"}){
            JsonObject changed=p.deepCopy();changed.addProperty(key,1);refused(()->NativeRelocationSupport.Uninvoked.validate(r,changed,intent,q,new JsonArray()));
        }
        JsonObject changed=p.deepCopy();changed.addProperty("ticket_cleanup_error","retained");refused(()->NativeRelocationSupport.Uninvoked.validate(r,changed,intent,q,new JsonArray()));
        JsonArray other=new JsonArray();other.add("different native contents");refused(()->NativeRelocationSupport.Uninvoked.validate(r,p,intent,q,other));
        JsonObject stale=r.deepCopy();stale.addProperty("created",Instant.now().minusSeconds(1300).toString());refused(()->NativeRelocationSupport.Uninvoked.validate(stale,p,intent,q,new JsonArray()));
        JsonObject invoked=q.deepCopy();invoked.addProperty("clone_invoked",true);refused(()->NativeRelocationSupport.Uninvoked.validate(r,p,intent,invoked,new JsonArray()));
        JsonObject foreign=r.deepCopy();foreign.addProperty("transaction_id","different");refused(()->NativeRelocationSupport.Uninvoked.validate(foreign,p,intent,q,new JsonArray()));
        System.out.println("PASS actual Brigadier redirect/hidden-lambda admission and "+assertions+" production authority assertions; no Minecraft initialization/world/clone execution");
    }
}
final class Foreign {static Command<String> callback(){return c->1;}}
