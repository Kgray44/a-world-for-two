import com.google.gson.*;
import java.util.concurrent.*;
import worldfortwo.living.*;

/** Fixture-based request-policy/usage tests. No account, provider or Minecraft runtime. */
public final class NativeApiPolicySelfTest {
    private static void check(boolean result,String reason){if(!result)throw new AssertionError(reason);}
    private static JsonObject document(){
        return JsonParser.parseString("""
          {"settings":{"external_enabled":true,"provider":"openai","endpoint":"https://api.openai.com/v1/chat/completions",
            "model":"gpt-6-luna","reasoning_effort":"none","response_tokens":240,"timeout_seconds":15,
            "requests_per_minute":2,"requests_per_hour":24,"requests_per_day":3,"daily_budget_usd":0.5},
           "provider_verification":{"verified":true,"model":"gpt-6-luna","endpoint":"https://api.openai.com/v1/chat/completions",
            "reasoning_effort":"none","response_tokens":240,"model_policies":{
             "gpt-6-luna":{"verified":true,"model":"gpt-6-luna","endpoint":"https://api.openai.com/v1/chat/completions",
               "reasoning_supported":true,"reasoning_efforts":["none","low","medium","high","xhigh","max"],
               "temperature_supported":true,"input_usd_per_million":0.1,"output_usd_per_million":0.5},
             "gpt-6.1-sol":{"verified":true,"model":"gpt-6.1-sol","endpoint":"https://api.openai.com/v1/chat/completions",
               "reasoning_supported":true,"reasoning_efforts":["low","medium","high","xhigh","max"],
               "temperature_supported":false,"input_usd_per_million":2,"output_usd_per_million":10}}},
           "characters":[{"id":"bill","enabled":true,"kind":"villager","ai":{"enabled":true,"model":"",
             "reasoning_effort":"global","temperature":0.4,"max_response_tokens":180,"requests_per_hour":12,"cooldown_seconds":5}},
             {"id":"steward","enabled":true,"kind":"villager","ai":{"enabled":true,"model":"gpt-6.1-sol",
             "max_response_tokens":120,"temperature":1,"requests_per_hour":12,"cooldown_seconds":5}}]}
          """).getAsJsonObject();
    }
    private static void refused(Runnable action){try{action.run();throw new AssertionError("Expected refusal");}catch(IllegalArgumentException|IllegalStateException expected){}}
    public static void main(String[] args)throws Exception{
        JsonObject document=document();WorldCharacters config=new WorldCharacters(document);
        var luna=NativeRequestPolicy.select(config,"bill");var sol=NativeRequestPolicy.select(config,"steward");
        check(luna.model().equals("gpt-6-luna")&&luna.reasoningEffort().equals("none")&&luna.responseTokens()==180,"Luna global fallback and profile token cap");
        check(sol.model().equals("gpt-6.1-sol")&&sol.reasoningEffort().equals("low")&&sol.responseTokens()==120,"Sol override needs its supported low effort");
        check(sol.inputRate()==2&&sol.outputRate()==10&&luna.inputRate()==0.1,"Override must reserve at its own model price");
        String original="{\"model\":\"wrong\",\"max_tokens\":1,\"temperature\":1,\"top_p\":1,\"messages\":[]}";
        try(var scope=NativeRequestPolicy.enter(sol)){
            JsonObject body=JsonParser.parseString(NativeRequestPolicy.applyBody(original)).getAsJsonObject();
            check(body.get("model").getAsString().equals("gpt-6.1-sol")&&body.get("max_completion_tokens").getAsInt()==120,"Per-request native body policy");
            check(body.get("reasoning_effort").getAsString().equals("low")&&!body.has("temperature")&&!body.has("top_p")&&!body.has("max_tokens"),"Unsupported parameters must be omitted");
            check(!body.get("store").getAsBoolean(),"Provider storage disabled");
            refused(()->NativeRequestPolicy.enter(luna));
        }
        check(NativeRequestPolicy.current()==null,"Scope cleanup");
        try{try(var scope=NativeRequestPolicy.enter(luna)){throw new IllegalStateException("fixture");}}catch(IllegalStateException ignored){}
        check(NativeRequestPolicy.current()==null,"Exception scope cleanup");
        try(var scope=NativeRequestPolicy.enter(luna)){
            check(JsonParser.parseString(NativeRequestPolicy.applyBody(original)).getAsJsonObject().get("temperature").getAsDouble()==0.4,"Only supported non-reasoning temperature");
        }
        ExecutorService workers=Executors.newFixedThreadPool(2);
        try{
            var a=workers.submit(()->{try(var scope=NativeRequestPolicy.enter(luna)){return NativeRequestPolicy.current().model();}});
            var b=workers.submit(()->{try(var scope=NativeRequestPolicy.enter(sol)){return NativeRequestPolicy.current().model();}});
            check(a.get().equals("gpt-6-luna")&&b.get().equals("gpt-6.1-sol"),"Concurrent requests cannot cross-contaminate models");
        }finally{workers.shutdownNow();}
        var bad=document.deepCopy();bad.getAsJsonArray("characters").get(1).getAsJsonObject().getAsJsonObject("ai").addProperty("model","listed-but-not-chat-tested");
        refused(()->NativeRequestPolicy.select(new WorldCharacters(bad),"steward"));
        var changed=document.deepCopy();changed.getAsJsonObject("settings").addProperty("response_tokens",512);
        refused(()->NativeRequestPolicy.select(new WorldCharacters(changed),"bill"));
        var hostile=document.deepCopy();hostile.getAsJsonObject("settings").addProperty("endpoint","https://elsewhere.invalid/chat/completions");
        refused(()->NativeRequestPolicy.select(new WorldCharacters(hostile),"bill"));
        int plain=NativeRequestPolicy.reservationBytes(luna,"short","hello");
        int history=NativeRequestPolicy.reservationBytes(luna,"Recent conversation: Player: \\\"harbor\\\"\nYou: café 船舶\n".repeat(8),"hello");
        check(history>plain+400,"Every escaped non-ASCII history byte must affect admission");

        var capture=sol.capture();capture.dispatched();capture.observe(200,"""
          {"model":"gpt-6.1-sol-verified-snapshot","choices":[{"message":{"content":"PRIVATE REPLY NEVER RETAINED"}}],
           "usage":{"prompt_tokens":12,"completion_tokens":6,"total_tokens":18,
             "prompt_tokens_details":{"cached_tokens":4},"completion_tokens_details":{"reasoning_tokens":3}}}
          """);
        var observed=capture.snapshot("ok");
        check(observed.get("usage_available").getAsBoolean()&&observed.getAsJsonObject("usage").get("reasoning_tokens").getAsInt()==3,"Actual returned counts captured");
        check(!observed.toString().contains("PRIVATE")&&!observed.toString().contains("choices"),"No reply, prompt or provider body in telemetry");
        var error=new NativeRequestPolicy.Capture();error.observe(401,"{\"error\":{\"message\":\"sk-private-secret\"}}");
        check(!error.snapshot("provider_error").get("usage_available").getAsBoolean()&&!error.snapshot("provider_error").toString().contains("sk-private"),"Error bodies must not leak");
        JsonObject ledger=new JsonObject();long now=1793232000000L;var ai=config.profileById("bill").getAsJsonObject("ai");
        NativeUsage.reserve(ledger,sol,config.settings(),ai,"bill",now,2000);
        double reserved=ledger.get("reserved_usd").getAsDouble();check(reserved==0.0052,"Sol charge must not use Luna price");
        NativeUsage.finish(ledger,capture.id(),observed);NativeUsage.finish(ledger,capture.id(),observed);
        check(ledger.get("day_dispatched").getAsLong()==1&&ledger.getAsJsonObject("day_usage").get("total_tokens").getAsLong()==18,"Repeated completion cannot duplicate real usage");
        var next=NativeRequestPolicy.select(config,"bill");NativeUsage.reserve(ledger,next,config.settings(),ai,"bill",now+6000,2000);
        refused(()->NativeUsage.reserve(ledger,NativeRequestPolicy.select(config,"bill"),config.settings(),ai,"bill",now+12000,2000));
        NativeUsage.reserve(ledger,NativeRequestPolicy.select(config,"bill"),config.settings(),ai,"bill",now+61000,2000);
        refused(()->NativeUsage.reserve(ledger,NativeRequestPolicy.select(config,"bill"),config.settings(),ai,"bill",now+122000,2000));
        var allowance=config.settings().deepCopy();allowance.addProperty("daily_budget_usd",0.000001);
        refused(()->NativeUsage.reserve(new JsonObject(),luna,allowance,ai,"bill",now,2000));
        check(ledger.get("reserved_usd").getAsDouble()>=reserved,"Measured usage does not silently refund conservative reservations");
        var corrupt=ledger.deepCopy();corrupt.addProperty("day_requests",-1);
        refused(()->NativeUsage.reserve(corrupt,luna,config.settings(),ai,"bill",now+180000,2000));
        var invalid=ledger.deepCopy();invalid.addProperty("reserved_usd",Double.NaN);
        refused(()->NativeUsage.reserve(invalid,luna,config.settings(),ai,"bill",now+180000,2000));
        JsonObject shared=new JsonObject();shared.addProperty("preview_day",ledger.get("day").getAsString());
        shared.addProperty("preview_reserved_usd",0.5);shared.addProperty("preview_day_requests",1);
        refused(()->NativeUsage.reserve(shared,luna,config.settings(),ai,"bill",now,2000));
        shared.addProperty("preview_reserved_usd",0.1);shared.addProperty("preview_day_requests",3);
        refused(()->NativeUsage.reserve(shared,luna,config.settings(),ai,"bill",now,2000));
        shared.addProperty("preview_day_requests",1);JsonArray previewRecent=new JsonArray();
        for(int i=0;i<2;i++){JsonObject row=new JsonObject();row.addProperty("at",now);row.addProperty("character","__connection_test__");previewRecent.add(row);}
        shared.add("preview_recent",previewRecent);
        refused(()->NativeUsage.reserve(shared,luna,config.settings(),ai,"bill",now,2000));
        shared.add("preview_recent",new JsonArray());NativeUsage.reserve(shared,luna,config.settings(),ai,"bill",now,2000);
        NativeUsage.finish(shared,luna.capture().id(),new JsonObject());
        check(shared.get("preview_reserved_usd").getAsDouble()==0.1&&shared.get("preview_day_requests").getAsInt()==1,"Native writes must preserve preview charges");
        System.out.println("Native model policy, generation parameters, private usage, history reservation and allowance checks passed; no provider or game request performed.");
    }
}
