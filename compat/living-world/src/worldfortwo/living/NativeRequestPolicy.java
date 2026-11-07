package worldfortwo.living;

import com.google.gson.*;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.*;

/** A per-request overlay for upstream's synchronous request construction only. */
public final class NativeRequestPolicy {
    public static final String ENDPOINT="https://api.openai.com/v1/chat/completions";
    private static final ThreadLocal<Policy> CURRENT=new ThreadLocal<>();
    private NativeRequestPolicy(){}
    public record Policy(String model,String reasoningEffort,boolean reasoningSupported,int responseTokens,
                         int timeoutSeconds,Double temperature,double inputRate,double outputRate,Capture capture){}
    public static Policy current(){return CURRENT.get();}
    public static final class Scope implements AutoCloseable {
        private Scope(Policy policy){if(CURRENT.get()!=null)throw new IllegalStateException("Nested character request policy");CURRENT.set(policy);}
        public void close(){CURRENT.remove();}
    }
    public static Scope enter(Policy policy){return new Scope(Objects.requireNonNull(policy));}
    public static String dedicatedKey(){String key=System.getenv("SMARTVILLAGERS_API_KEY");return key==null?"":key.trim();}
    public static boolean credentialPresent(){return !dedicatedKey().isEmpty();}
    public static String credentialFingerprint(){
        if(!credentialPresent())return null;
        try{return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(dedicatedKey().getBytes(StandardCharsets.UTF_8)));}
        catch(Exception ignored){return null;}
    }
    private static boolean inherit(String value){return value.isBlank()||value.equalsIgnoreCase("global")||value.equalsIgnoreCase("scripted");}
    private static int bounded(JsonObject object,String key,int fallback,int low,int high){return Math.max(low,Math.min(high,WorldCharacters.integer(object,key,fallback)));}
    private static double rate(JsonObject object,String key){
        try{double value=object.get(key).getAsDouble();if(Double.isFinite(value)&&value>0&&value<=10000)return value;}catch(Exception ignored){}
        throw new IllegalArgumentException("Verified model pricing unavailable");
    }
    private static boolean contains(JsonArray array,String value){for(JsonElement item:array)if(item.isJsonPrimitive()&&item.getAsString().equals(value))return true;return false;}
    private static String effort(JsonObject model,String requested){
        var supported=WorldCharacters.array(model,"reasoning_efforts");
        if(contains(supported,requested))return requested;
        // Official Sol does not accept none; the documented lowest reasoning level is low.
        if(requested.equals("none")&&contains(supported,"low"))return "low";
        throw new IllegalArgumentException("Reasoning setting is not supported by the verified model");
    }
    public static Policy select(WorldCharacters config,String character){
        JsonObject settings=config.settings(),verification=config.providerVerification();
        if(!WorldCharacters.flag(settings,"external_enabled")||!WorldCharacters.text(settings,"provider").equals("openai")
                ||!ENDPOINT.equals(WorldCharacters.text(settings,"endpoint"))||!WorldCharacters.flag(verification,"verified")
                ||!ENDPOINT.equals(WorldCharacters.text(verification,"endpoint")))throw new IllegalArgumentException("Current OpenAI connection is not verified");
        String globalModel=WorldCharacters.text(settings,"model");
        if(globalModel.isBlank()||!globalModel.equals(WorldCharacters.text(verification,"model")))throw new IllegalArgumentException("Global model verification differs");
        JsonObject policies=WorldCharacters.object(verification,"model_policies");
        JsonObject globalPolicy=WorldCharacters.object(policies,globalModel);
        String globalEffort=effort(globalPolicy,WorldCharacters.text(settings,"reasoning_effort"));
        int globalTokens=bounded(settings,"response_tokens",120,32,2048);
        if(!globalEffort.equals(WorldCharacters.text(verification,"reasoning_effort"))
                ||globalTokens!=WorldCharacters.integer(verification,"response_tokens",-1))throw new IllegalArgumentException("Generation settings need a fresh connection check");
        JsonObject profile=character==null?null:config.profileById(character),ai=WorldCharacters.object(profile,"ai");
        if(character!=null&&(!config.enabled(profile)||!WorldCharacters.flag(ai,"enabled")))throw new IllegalArgumentException("Character AI is disabled");
        String override=WorldCharacters.text(ai,"model"),model=inherit(override)?globalModel:override;
        JsonObject selected=WorldCharacters.object(policies,model);
        if(!WorldCharacters.flag(selected,"verified")||!model.equals(WorldCharacters.text(selected,"model"))
                ||!ENDPOINT.equals(WorldCharacters.text(selected,"endpoint")))throw new IllegalArgumentException("Character model has not passed a connection check");
        String requested=WorldCharacters.text(ai,"reasoning_effort");
        if(inherit(requested))requested=WorldCharacters.text(settings,"reasoning_effort");
        String selectedEffort=effort(selected,requested);
        boolean reasoningSupported=WorldCharacters.flag(selected,"reasoning_supported");
        if(!reasoningSupported&&!selectedEffort.equals("none"))throw new IllegalArgumentException("Model reasoning support is unverified");
        int tokens=Math.min(globalTokens,bounded(ai,"max_response_tokens",globalTokens,32,2048));
        Double temperature=null;
        if(WorldCharacters.flag(selected,"temperature_supported")&&selectedEffort.equals("none")){
            try{double value=ai.has("temperature")?ai.get("temperature").getAsDouble():.7;
                if(Double.isFinite(value)&&value>=0&&value<=1)temperature=value;
            }catch(Exception ignored){}
        }
        return new Policy(model,selectedEffort,reasoningSupported,tokens,bounded(settings,"timeout_seconds",15,5,60),temperature,
            rate(selected,"input_usd_per_million"),rate(selected,"output_usd_per_million"),character==null?null:new Capture());
    }
    public static JsonObject providerState(){
        JsonObject value=new JsonObject();value.addProperty("provider","openai");value.addProperty("credential_configured",credentialPresent());
        value.addProperty("credential_fingerprint",credentialFingerprint());
        try{var policy=select(WorldCharacters.current,null);value.addProperty("model",policy.model());value.addProperty("verification_current",true);}
        catch(Exception ignored){value.add("model",JsonNull.INSTANCE);value.addProperty("verification_current",false);}
        return value;
    }
    public static String applyBody(String original){
        Policy policy=current();if(policy==null)return original;
        return applyBody(original,policy);
    }
    private static String applyBody(String original,Policy policy){
        JsonObject body=JsonParser.parseString(original).getAsJsonObject();
        body.addProperty("model",policy.model());body.remove("max_tokens");body.addProperty("max_completion_tokens",policy.responseTokens());
        body.remove("reasoning_effort");if(policy.reasoningSupported())body.addProperty("reasoning_effort",policy.reasoningEffort());
        body.remove("temperature");body.remove("top_p");body.remove("logprobs");
        if(policy.temperature()!=null)body.addProperty("temperature",policy.temperature());
        body.addProperty("store",false);return body.toString();
    }
    public static int reservationBytes(Policy policy,String system,String user){
        JsonObject body=new JsonObject();body.addProperty("model",policy.model());body.addProperty("stream",false);
        JsonArray messages=new JsonArray();
        for(String role:List.of("system","user")){
            JsonObject message=new JsonObject();message.addProperty("role",role);message.addProperty("content",role.equals("system")?system:user);messages.add(message);
        }
        body.add("messages",messages);
        // Pinned PromptBuilder has already serialized ALL bounded exchanges in system.
        // Count escaped UTF-8 JSON too, then over-reserve framing/special tokens.
        return applyBody(body.toString(),policy).getBytes(StandardCharsets.UTF_8).length+2048;
    }
    /** Only safe transport metadata is retained; bodies, replies and headers never are. */
    public static final class Capture {
        private final String id=UUID.randomUUID().toString().replace("-","");
        private final long started=System.nanoTime();
        private boolean dispatched,deadline,observed;
        private JsonObject values=new JsonObject();
        public String id(){return id;}
        public synchronized void dispatched(){dispatched=true;}
        public synchronized void deadline(){deadline=true;}
        public synchronized boolean wasDispatched(){return dispatched;}
        public synchronized boolean observed(){return observed;}
        private static Long count(JsonObject object,String name){
            try{JsonElement value=object.get(name);if(value==null||!value.isJsonPrimitive()||!value.getAsJsonPrimitive().isNumber())return null;
                double number=value.getAsDouble();if(Double.isFinite(number)&&number>=0&&number<=10000000&&number==Math.rint(number))return (long)number;
            }catch(Exception ignored){}return null;
        }
        public synchronized void observe(int status,String body){
            observed=true;values.addProperty("http_status",status);values.addProperty("latency_ms",Math.max(0,(System.nanoTime()-started)/1000000));
            values.addProperty("status",status>=200&&status<300?"ok":"provider_error");
            if(body==null||body.length()>1024*1024)return;
            try{
                JsonObject response=JsonParser.parseString(body).getAsJsonObject();
                String model=WorldCharacters.text(response,"model");
                if(model.matches("[A-Za-z0-9][A-Za-z0-9._:-]{0,119}"))values.addProperty("model",model);
                JsonObject raw=WorldCharacters.object(response,"usage"),usage=new JsonObject();
                for(String key:List.of("prompt_tokens","completion_tokens","total_tokens")){Long count=count(raw,key);if(count!=null)usage.addProperty(key,count);}
                Long cached=count(WorldCharacters.object(raw,"prompt_tokens_details"),"cached_tokens");if(cached!=null)usage.addProperty("cached_tokens",cached);
                Long reasoning=count(WorldCharacters.object(raw,"completion_tokens_details"),"reasoning_tokens");if(reasoning!=null)usage.addProperty("reasoning_tokens",reasoning);
                if(usage.has("prompt_tokens")&&usage.has("completion_tokens")&&usage.has("total_tokens")
                        &&usage.get("prompt_tokens").getAsLong()+usage.get("completion_tokens").getAsLong()==usage.get("total_tokens").getAsLong()
                        &&(!usage.has("cached_tokens")||usage.get("cached_tokens").getAsLong()<=usage.get("prompt_tokens").getAsLong())
                        &&(!usage.has("reasoning_tokens")||usage.get("reasoning_tokens").getAsLong()<=usage.get("completion_tokens").getAsLong()))values.add("usage",usage);
            }catch(Exception ignored){}
        }
        public synchronized JsonObject snapshot(String terminal){
            JsonObject copy=values.deepCopy();copy.addProperty("dispatched",dispatched);copy.addProperty("usage_available",copy.has("usage"));
            copy.addProperty("status",terminal);
            if(deadline)copy.addProperty("delivery_status","deadline");
            if(!copy.has("latency_ms"))copy.addProperty("latency_ms",Math.max(0,(System.nanoTime()-started)/1000000));
            return copy;
        }
    }
}
