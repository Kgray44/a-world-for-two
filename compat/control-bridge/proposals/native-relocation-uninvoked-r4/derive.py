"""Additive native callback admission and ONE explicitly reviewed uninvoked intent.

Preserves the R3 source and every real ledger. No world/API operation is run.
"""
from pathlib import Path
import hashlib

ROOT=Path(__file__).resolve().parent
BASE=ROOT.parent/'native-relocation-envelope-r3/NativeRelocationSupport.java'
EXPECTED='90a015a2ad5b2608a7ba9c69429f935eb4961b53d73caf0e850e2a9856043a5d'

METHODS=r'''
    /** Resolve only the actual registered vanilla callback, before any intent. */
    static final class CloneBinding {
        static Class<?> callback(com.mojang.brigadier.ParseResults<?> parsed,Class<?> host){
            if(parsed.getReader().canRead())throw new IllegalStateException("Native clone command has unconsumed input");
            var context=parsed.getContext();com.mojang.brigadier.Command<?> selected=null;int depth=0;
            while(context!=null){
                if(++depth>8)throw new IllegalStateException("Bounded command context chain required");
                var command=context.getCommand();
                if(command!=null){if(selected!=null&&selected!=command)throw new IllegalStateException("Ambiguous native clone callbacks");selected=command;}
                context=context.getChild();
            }
            if(selected==null)throw new IllegalStateException("No selected real native clone callback");
            Class<?> c=selected.getClass();
            if(!c.getName().startsWith(host.getName()+"$$Lambda")||!c.isSynthetic()||!c.isHidden()
                ||c.getNestHost()!=host||c.getClassLoader()!=host.getClassLoader()||c.getModule()!=host.getModule())
                throw new IllegalStateException("Pinned real native CloneCommands callback/module/loader/nest required");
            return c;
        }
    }
    private com.mojang.brigadier.ParseResults<net.minecraft.commands.CommandSourceStack> nativeClone(MinecraftServer server)throws Exception{
        String command="clone "+LOW.getX()+" "+LOW.getY()+" "+LOW.getZ()+" "+HIGH.getX()+" "+HIGH.getY()+" "+HIGH.getZ()+" "+DEST.getX()+" "+DEST.getY()+" "+DEST.getZ()+" replace move";
        var console=server.createCommandSourceStack().withLevel(level).withSuppressedOutput();
        if(console.getEntity()!=null||!console.hasPermission(4))throw new IllegalStateException("Real permission4 native console only");
        if(!classHash(CloneCommands.class).equals(request.get("vanilla_clone_class_sha256").getAsString()))throw new IllegalStateException("Actual native clone host bytes changed");
        var parsed=server.getCommands().getDispatcher().parse(command,console);Class<?> callback=CloneBinding.callback(parsed,CloneCommands.class);
        Map<String,Object> binding=new LinkedHashMap<>();binding.put("class",callback.getName());binding.put("module",callback.getModule().getName());
        binding.put("loader_class",callback.getClassLoader()==null?"bootstrap":callback.getClassLoader().getClass().getName());
        binding.put("nest_host",callback.getNestHost().getName());binding.put("hidden",callback.isHidden());binding.put("synthetic",callback.isSynthetic());
        report.put("actual_native_clone_callback",binding);return parsed;
    }
    private JsonObject exactRef(JsonObject ref,int max)throws Exception{
        byte[] raw=bytes(owned(ref.get("path").getAsString()),max);
        if(raw.length!=ref.get("bytes").getAsInt()||!sha(raw).equals(ref.get("sha256").getAsString()))throw new IllegalStateException("Exact nested evidence changed");
        return JsonParser.parseString(new String(raw,StandardCharsets.UTF_8)).getAsJsonObject();
    }
    static final class Uninvoked {
        static final String TX="537132d7dc65e7758179b56109d518e8990cc422222b48f163a77a953178249b";
        static final String TERMINAL="36bc9697b81bf0c7ca760a1cfbc3178eeef151f3d507741199d8049d7f5a159b";
        static final String INTENT="a29842d7a1be6dd8f1ce557cd2d2daa0467539f7fce20059c09a8f8280a76bdd";
        static final String QUARANTINE="38723688b0abb171264e938a7ff79b47cd44c757a95431ed5c31e7a271bedf50";
        static void validate(JsonObject review,JsonObject prior,JsonObject intent,JsonObject quarantine,JsonArray fresh){
            if(!review.get("format").getAsString().equals("awft-explicit-uninvoked-relocation-review:1")||!review.get("approved").getAsBoolean()
                ||!review.get("allow_exactly_one_new_intent").getAsBoolean()||!review.get("transaction_id").getAsString().equals(TX)
                ||!review.get("prior_intent_sha256").getAsString().equals(INTENT)||!review.get("prior_quarantine_sha256").getAsString().equals(QUARANTINE)
                ||!review.getAsJsonObject("prior_terminal").get("sha256").getAsString().equals(TERMINAL))throw new IllegalStateException("Explicit exact uninvoked transaction review required");
            if(!prior.get("transaction_id").getAsString().equals(TX)||!intent.get("transaction_id").getAsString().equals(TX)
                ||!prior.get("capsule_id").getAsString().equals("eastern22/pippins-net:room:0")||!prior.get("operation").getAsString().equals("move")
                ||prior.get("clone_invoked").getAsBoolean()||!prior.get("intent_written").getAsBoolean()||!prior.get("quarantine").getAsBoolean()
                ||!prior.get("failed").getAsBoolean()||!prior.get("cleanup_passed").getAsBoolean()
                ||prior.get("owned_chunk_tickets").getAsInt()!=0||prior.get("pending_owned_futures").getAsInt()!=0||prior.get("pending_shared_chunk_futures").getAsInt()!=0
                ||prior.has("ticket_cleanup_error")||prior.has("lease_cleanup_error")
                ||!prior.get("private_error").getAsString().equals("Pinned real native CloneCommands implementation required")
                ||quarantine.get("clone_invoked").getAsBoolean()||!quarantine.get("request_sha256").equals(prior.get("request_sha256"))
                ||!intent.get("request_sha256").equals(prior.get("request_sha256")))throw new IllegalStateException("Only the proven never-invoked callback-admission failure is resolvable");
            if(!prior.getAsJsonArray("before_native_snapshots").equals(fresh)||!intent.getAsJsonArray("before_native_snapshots").equals(fresh))
                throw new IllegalStateException("Fresh real native full data/slots/components differ from original uninvoked intent");
            Instant created=Instant.parse(review.get("created").getAsString()),finished=Instant.parse(prior.get("finished").getAsString());
            if(created.isAfter(Instant.now())||created.isBefore(finished)||created.isBefore(Instant.now().minusSeconds(1200)))throw new IllegalStateException("Fresh explicit review ordering required");
        }
    }
    private JsonObject uninvokedResolution(JsonArray before)throws Exception{
        boolean prior=Files.exists(ledger.resolve("intent.json"),LinkOption.NOFOLLOW_LINKS)||Files.exists(ledger.resolve("quarantine.json"),LinkOption.NOFOLLOW_LINKS);
        if(Files.exists(ledger.resolve("completed.json"),LinkOption.NOFOLLOW_LINKS))throw new IllegalStateException("Completed transaction never replays");
        if(!prior){if(request.has("uninvoked_resolution_review"))throw new IllegalStateException("No original uninvoked intent for this review");return null;}
        if(!request.has("uninvoked_resolution_review")||!report.get("transaction_id").equals(Uninvoked.TX))throw new IllegalStateException("Existing intent/quarantine retained; no automatic replay");
        for(String name:List.of("uninvoked-resolution.json","intent-after-uninvoked-resolution.json","quarantine-after-uninvoked-resolution.json"))
            if(Files.exists(ledger.resolve(name),LinkOption.NOFOLLOW_LINKS))throw new IllegalStateException("One reviewed resolution already attempted; no second attempt");
        JsonObject review=ref("uninvoked_resolution_review",65536),terminal=exactRef(review.getAsJsonObject("prior_terminal"),1048576);
        Path terminalPath=owned(review.getAsJsonObject("prior_terminal").get("path").getAsString());
        if(!new String(bytes(terminalPath.resolveSibling(terminalPath.getFileName()+".complete"),128),StandardCharsets.UTF_8).trim().equals(Uninvoked.TERMINAL)
            ||!sha(bytes(ledger.resolve("intent.json"),1048576)).equals(Uninvoked.INTENT)||!sha(bytes(ledger.resolve("quarantine.json"),1048576)).equals(Uninvoked.QUARANTINE))
            throw new IllegalStateException("Original immutable uninvoked ledger/terminal differs");
        Uninvoked.validate(review,terminal,read(ledger.resolve("intent.json"),1048576),read(ledger.resolve("quarantine.json"),1048576),before);
        report.put("uninvoked_resolution_review_sha256",request.getAsJsonObject("uninvoked_resolution_review").get("sha256").getAsString());
        report.put("prior_uninvoked_intent_preserved",true);return review;
    }
    private static String activeIntent(JsonObject done){
        String name=done.has("active_intent_file")?done.get("active_intent_file").getAsString():"intent.json";
        if(!name.equals("intent.json")&&!name.equals("intent-after-uninvoked-resolution.json"))throw new IllegalStateException("Unknown durable intent filename");return name;
    }
'''

def replace_once(s,old,new):
    if s.count(old)!=1:raise RuntimeError('Expected exactly one source site: '+old[:90])
    return s.replace(old,new)

def derive():
    raw=BASE.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=EXPECTED:raise RuntimeError('Frozen R3 bytes differ')
    s=raw.decode().replace('\r\n','\n')
    s=replace_once(s,'    private String capsuleId;','    private String capsuleId;\n    private String intentName="intent.json";')
    s=replace_once(s,'!classHash(RuntimeTags.class).equals(request.get("runtime_tags_class_sha256").getAsString())', '!classHash(RuntimeTags.class).equals(request.get("runtime_tags_class_sha256").getAsString())||!classHash(CloneBinding.class).equals(request.get("clone_binding_class_sha256").getAsString())||!classHash(Uninvoked.class).equals(request.get("uninvoked_class_sha256").getAsString())')
    s=replace_once(s,'    private void atomic(MinecraftServer server)throws Exception{',METHODS+'\n    private void atomic(MinecraftServer server)throws Exception{')
    s=replace_once(s,'if(!done.get("transaction_id").getAsString().equals(key)||!done.get("intent_sha256").getAsString().equals(sha(bytes(path.resolve("intent.json"),1048576))))','if(!done.get("transaction_id").getAsString().equals(key)||!done.get("intent_sha256").getAsString().equals(sha(bytes(path.resolve(activeIntent(done)),1048576))))')
    s=replace_once(s,'sha(bytes(ledger.resolve("intent.json"),1048576))))throw new IllegalStateException("Foreign/mismatched durable completion and original intent")','sha(bytes(ledger.resolve(activeIntent(done)),1048576))))throw new IllegalStateException("Foreign/mismatched durable completion and original intent")')
    old='            if(Files.exists(ledger.resolve("intent.json"),LinkOption.NOFOLLOW_LINKS)||Files.exists(ledger.resolve("completed.json"),LinkOption.NOFOLLOW_LINKS)||Files.exists(ledger.resolve("quarantine.json"),LinkOption.NOFOLLOW_LINKS))throw new IllegalStateException("A durable move intent already exists; never replay or automatically repair");\n'
    s=replace_once(s,old,'')
    s=replace_once(s,'            report.put("before_native_snapshots",before);','            report.put("before_native_snapshots",before);\n            JsonObject resolution=uninvokedResolution(before);var parsed=nativeClone(server);')
    s=replace_once(s,'            intentAttempted=true;durable(ledger.resolve("intent.json"),intent);intentWritten=true;','''            intentName=resolution==null?"intent.json":"intent-after-uninvoked-resolution.json";
            intent.addProperty("active_intent_file",intentName);if(resolution!=null)uninvokedResolution(before);intentAttempted=true;
            if(resolution!=null){JsonObject record=new JsonObject();record.addProperty("format","awft-native-uninvoked-intent-resolution:1");record.addProperty("transaction_id",Uninvoked.TX);
                record.addProperty("created",Instant.now().toString());record.add("explicit_review",request.get("uninvoked_resolution_review").deepCopy());record.addProperty("original_intent_sha256",Uninvoked.INTENT);
                record.addProperty("original_quarantine_sha256",Uninvoked.QUARANTINE);record.addProperty("prior_terminal_sha256",Uninvoked.TERMINAL);record.addProperty("fresh_inspection_sha256",request.getAsJsonObject("native_inspect").get("sha256").getAsString());
                record.add("fresh_native_snapshots",before);durable(ledger.resolve("uninvoked-resolution.json"),record);intent.addProperty("uninvoked_resolution_sha256",sha(bytes(ledger.resolve("uninvoked-resolution.json"),1048576)));}
            durable(ledger.resolve(intentName),intent);intentWritten=true;''')
    a=s.index('            String command="clone ',s.index('    private void atomic('));b=s.index('            cloneInvoked=true;',a)
    s=s[:a]+s[b:]
    s=replace_once(s,'done.addProperty("intent_sha256",sha(bytes(ledger.resolve("intent.json"),1048576)));','done.addProperty("intent_sha256",sha(bytes(ledger.resolve(intentName),1048576)));')
    s=replace_once(s,'durable(ledger.resolve("quarantine.json"),q);','durable(ledger.resolve(intentName.equals("intent.json")?"quarantine.json":"quarantine-after-uninvoked-resolution.json"),q);')
    s=replace_once(s,'        action=op;running=true;','        intentName="intent.json";action=op;running=true;')
    (ROOT/'NativeRelocationSupport.java').write_text(s,encoding='utf8',newline='\n')
    print(hashlib.sha256((ROOT/'NativeRelocationSupport.java').read_bytes()).hexdigest())

if __name__=='__main__':derive()
